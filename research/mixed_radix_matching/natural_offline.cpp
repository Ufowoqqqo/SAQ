#include "pair_matching.hpp"

#include "../structured_2d/dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/index_io.h>
#include <openssl/sha.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <sstream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <sys/resource.h>
#include <time.h>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t kRowsPerSplit = 8192;
constexpr std::size_t kDimensions = 128;
constexpr int kBits = 8;

using Pair = std::pair<std::size_t, std::size_t>;

struct Timer {
    timespec cpu{};
    std::chrono::steady_clock::time_point wall;

    Timer() : wall(std::chrono::steady_clock::now()) {
        if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu) != 0)
            throw std::runtime_error("process CPU clock");
    }
};

std::pair<double, double> elapsed(const Timer& timer) {
    timespec current{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &current) != 0)
        throw std::runtime_error("process CPU clock");
    const double cpu = current.tv_sec - timer.cpu.tv_sec +
            (current.tv_nsec - timer.cpu.tv_nsec) * 1e-9;
    const double wall = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - timer.wall).count();
    return {cpu, wall};
}

std::uint64_t peak_rss_bytes() {
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0)
        throw std::runtime_error("getrusage");
    return static_cast<std::uint64_t>(usage.ru_maxrss) * 1024;
}

void append_u64(std::vector<std::uint8_t>& bytes, std::uint64_t value) {
    for (std::size_t offset = 0; offset < 8; ++offset)
        bytes.push_back(static_cast<std::uint8_t>(value >> (8 * offset)));
}

std::array<unsigned char, SHA256_DIGEST_LENGTH> row_hash(
        std::string_view dataset, std::size_t nlist, std::size_t row) {
    std::vector<std::uint8_t> bytes(dataset.begin(), dataset.end());
    append_u64(bytes, nlist);
    append_u64(bytes, row);
    append_u64(bytes, 20260724);
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    if (::SHA256(bytes.data(), bytes.size(), digest.data()) == nullptr)
        throw std::runtime_error("matching SHA-256");
    return digest;
}

std::vector<std::size_t> select_rows(
        std::string_view dataset, std::size_t nlist, std::size_t row_count) {
    struct Entry {
        std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
        std::size_t row = 0;
    };
    const std::size_t selected = 2 * kRowsPerSplit;
    if (row_count < selected) throw std::invalid_argument("too few learn rows");
    std::vector<Entry> entries(row_count);
    for (std::size_t row = 0; row < row_count; ++row)
        entries[row] = {row_hash(dataset, nlist, row), row};
    const auto less = [](const Entry& left, const Entry& right) {
        return left.hash != right.hash
                ? left.hash < right.hash
                : left.row < right.row;
    };
    std::partial_sort(
            entries.begin(), entries.begin() + selected,
            entries.end(), less);
    std::vector<std::size_t> result(selected);
    for (std::size_t index = 0; index < selected; ++index)
        result[index] = entries[index].row;
    return result;
}

std::vector<float> residual_rows(
        std::span<const float> learn,
        std::span<const std::uint32_t> assignments,
        std::span<const float> centroids,
        std::span<const std::size_t> rows) {
    if (learn.size() != assignments.size() * kDimensions ||
        centroids.empty() || centroids.size() % kDimensions != 0 ||
        rows.size() != kRowsPerSplit)
        throw std::invalid_argument("matching residual shape");
    std::vector<float> residuals(rows.size() * kDimensions);
    for (std::size_t index = 0; index < rows.size(); ++index) {
        const std::size_t row = rows[index];
        if (row >= assignments.size() ||
            assignments[row] >= centroids.size() / kDimensions)
            throw std::out_of_range("matching selected row");
        const float* center = centroids.data() +
                static_cast<std::size_t>(assignments[row]) * kDimensions;
        for (std::size_t dimension = 0; dimension < kDimensions; ++dimension)
            residuals[index * kDimensions + dimension] =
                    learn[row * kDimensions + dimension] - center[dimension];
    }
    return residuals;
}

std::vector<Pair> adjacent_pairs() {
    std::vector<Pair> result;
    result.reserve(kDimensions / 2);
    for (std::size_t first = 0; first < kDimensions; first += 2)
        result.emplace_back(first, first + 1);
    return result;
}

std::size_t overlap(
        const std::vector<Pair>& first,
        const std::vector<Pair>& second) {
    std::size_t count = 0;
    for (const Pair& pair : first)
        count += std::find(second.begin(), second.end(), pair) != second.end();
    return count;
}

mixedradix::matching::Result solve_with_networkx(
        const std::vector<mixedradix::matching::WeightedEdge>& edges,
        const std::filesystem::path& output_dir,
        const std::string& stem) {
    const auto input_path = output_dir / (stem + "_edges.tsv");
    const auto output_path = output_dir / (stem + "_matching.tsv");
    std::ofstream edge_output(input_path);
    edge_output << "vertices\tfirst\tsecond\tweight\n";
    for (const auto& edge : edges)
        edge_output << kDimensions << '\t' << edge.first << '\t'
                    << edge.second << '\t' << std::setprecision(17)
                    << edge.weight << '\n';
    edge_output.close();
    if (!edge_output) throw std::runtime_error("write matching edges");

    const std::string command =
            "python research/mixed_radix_matching/solve_matching.py " +
            input_path.string() + " " + output_path.string();
    if (std::system(command.c_str()) != 0)
        throw std::runtime_error("NetworkX matching failed");

    std::ifstream matched(output_path);
    std::string label;
    mixedradix::matching::Result result;
    if (!(matched >> label >> result.objective_rounding_bound) ||
        label != "rounding_bound")
        throw std::runtime_error("matching result bound");
    std::string first_header, second_header;
    if (!(matched >> first_header >> second_header) ||
        first_header != "first" || second_header != "second")
        throw std::runtime_error("matching result header");
    std::size_t first = 0, second = 0;
    while (matched >> first >> second) result.pairs.emplace_back(first, second);
    if (!matched.eof() || result.pairs.size() != kDimensions / 2)
        throw std::runtime_error("matching result rows");
    std::vector<bool> used(kDimensions, false);
    for (const auto& pair : result.pairs) {
        if (pair.first >= pair.second || pair.second >= kDimensions ||
            used[pair.first] || used[pair.second])
            throw std::runtime_error("matching result partition");
        used[pair.first] = used[pair.second] = true;
        const auto edge = std::find_if(
                edges.begin(), edges.end(), [&](const auto& candidate) {
                    return candidate.first == pair.first &&
                           candidate.second == pair.second;
                });
        if (edge == edges.end()) throw std::runtime_error("matched edge absent");
        result.weight += edge->weight;
    }
    if (!std::all_of(used.begin(), used.end(), [](bool value) { return value; }))
        throw std::runtime_error("matching result incomplete");
    return result;
}

double heldout_pair_sse(
        std::span<const float> heldout, const Pair& pair,
        const a4or::Allocation& allocation,
        const a4orb::Curves& curves) {
    const auto& first_centers =
            curves.coordinates[pair.first][allocation.k1 - 1].centers;
    const auto& second_centers =
            curves.coordinates[pair.second][allocation.k2 - 1].centers;
    if (first_centers.size() != allocation.k1 ||
        second_centers.size() != allocation.k2)
        throw std::runtime_error("matching center count");

    const auto nearest_squared = [](double value,
                                    const std::vector<float>& centers) {
        if (!std::is_sorted(centers.begin(), centers.end()))
            throw std::runtime_error("unsorted scalar centers");
        const auto upper = std::lower_bound(
                centers.begin(), centers.end(), value,
                [](float center, double target) {
                    return static_cast<double>(center) < target;
                });
        if (upper == centers.begin()) {
            const double delta = value - *upper;
            return delta * delta;
        }
        if (upper == centers.end()) {
            const double delta = value - centers.back();
            return delta * delta;
        }
        const double upper_delta = value - *upper;
        const double lower_delta = value - *std::prev(upper);
        return std::min(
                upper_delta * upper_delta,
                lower_delta * lower_delta);
    };

    double sum = 0;
    double correction = 0;
    for (std::size_t row = 0; row < kRowsPerSplit; ++row) {
        for (const auto coordinate : {pair.first, pair.second}) {
            const auto& centers = coordinate == pair.first
                    ? first_centers : second_centers;
            const double value = heldout[row * kDimensions + coordinate];
            const double best = nearest_squared(value, centers);
            const double next = sum + best;
            if (std::fabs(sum) >= std::fabs(best))
                correction += (sum - next) + best;
            else
                correction += (best - next) + sum;
            sum = next;
        }
    }
    return sum + correction;
}

struct PlanResult {
    std::string name;
    bool dyadic = false;
    std::vector<Pair> pairs;
    std::vector<a4or::Allocation> allocations;
    std::vector<double> heldout_group_sse;
    double fit_sse = 0;
    double heldout_sse = 0;
};

PlanResult evaluate_plan(
        std::string name, bool dyadic, std::vector<Pair> pairs,
        const a4orb::Curves& curves, std::span<const float> heldout) {
    PlanResult result{
            std::move(name), dyadic, std::move(pairs), {}, {}, 0, 0};
    result.allocations.reserve(result.pairs.size());
    result.heldout_group_sse.reserve(result.pairs.size());
    for (const Pair& pair : result.pairs) {
        const auto allocation = a4or::allocate_pair(
                curves.coordinates[pair.first],
                curves.coordinates[pair.second], kBits, dyadic);
        result.fit_sse += allocation.sse;
        const double group_sse = heldout_pair_sse(
                heldout, pair, allocation, curves);
        result.heldout_sse += group_sse;
        result.allocations.push_back(allocation);
        result.heldout_group_sse.push_back(group_sse);
    }
    return result;
}

void run_cell(
        const std::filesystem::path& root,
        const std::string& dataset, std::size_t nlist,
        const std::filesystem::path& output_dir,
        std::ofstream& summary, std::ofstream& pairs,
        std::ofstream& resources) {
    const Timer timer;
    const bool sift = dataset == "sift";
    const std::size_t learn_rows = sift ? 100000 : 500000;
    const std::string dataset_id = sift ? "SIFT1M" : "GIST1M";
    std::cerr << "start " << dataset_id << " nlist=" << nlist << '\n';
    const auto view = root / (sift ? "sift" : "gist_head128");
    const auto nlist_dir = view / ("nlist_" + std::to_string(nlist));

    structured2d::admission::FvecsReader reader(
            view / "learn_pca.fvecs", learn_rows, kDimensions);
    const auto learn = structured2d::admission::read_all(reader);
    const auto assignments = structured2d::admission::read_u32(
            nlist_dir / "learn_assignments.u32", learn_rows);
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index((nlist_dir / "coarse.faiss").c_str()));
    auto* coarse = dynamic_cast<faiss::IndexFlatL2*>(coarse_owner.get());
    if (coarse == nullptr || coarse->d != kDimensions ||
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("matching coarse index");

    const auto selected = select_rows(dataset_id, nlist, learn_rows);
    const auto fit = residual_rows(
            learn, assignments,
            std::span<const float>(coarse->get_xb(), nlist * kDimensions),
            std::span<const std::size_t>(selected).first(kRowsPerSplit));
    const auto heldout = residual_rows(
            learn, assignments,
            std::span<const float>(coarse->get_xb(), nlist * kDimensions),
            std::span<const std::size_t>(selected).subspan(kRowsPerSplit));
    std::cerr << "  residual panels ready\n";
    const auto curves = a4orb::fit_curves(fit, 1024);
    std::cerr << "  scalar curves ready\n";

    const auto adjacent = adjacent_pairs();
    const auto a_edges = mixedradix::matching::allocation_edges(
            curves, kBits, false);
    std::cerr << "  arbitrary edges ready\n";
    const auto a_flex = solve_with_networkx(
            a_edges, output_dir,
            dataset + "_" + std::to_string(nlist) + "_A");
    std::cerr << "  arbitrary matching ready\n";
    const auto d_edges = mixedradix::matching::allocation_edges(
            curves, kBits, true);
    std::cerr << "  dyadic edges ready\n";
    const auto d_flex = solve_with_networkx(
            d_edges, output_dir,
            dataset + "_" + std::to_string(nlist) + "_D");
    std::cerr << "  dyadic matching ready\n";

    const std::vector<PlanResult> plans = {
            evaluate_plan("A_adj", false, adjacent, curves, heldout),
            evaluate_plan("D_adj", true, adjacent, curves, heldout),
            evaluate_plan("A_flex", false, a_flex.pairs, curves, heldout),
            evaluate_plan("D_on_A", true, a_flex.pairs, curves, heldout),
            evaluate_plan("A_on_D", false, d_flex.pairs, curves, heldout),
            evaluate_plan("D_flex", true, d_flex.pairs, curves, heldout)};
    std::cerr << "  held-out plans ready\n";

    const std::size_t a_adjacent = overlap(a_flex.pairs, adjacent);
    const std::size_t d_adjacent = overlap(d_flex.pairs, adjacent);
    const std::size_t a_d_overlap = overlap(a_flex.pairs, d_flex.pairs);
    for (const auto& plan : plans) {
        summary << dataset_id << '\t' << nlist << '\t' << plan.name << '\t'
                << std::setprecision(17) << plan.fit_sse << '\t'
                << plan.heldout_sse << '\t'
                << plan.heldout_sse /
                           (kRowsPerSplit * kDimensions) << '\t'
                << a_adjacent << '\t' << d_adjacent << '\t'
                << a_d_overlap << '\t'
                << a_flex.objective_rounding_bound << '\t'
                << d_flex.objective_rounding_bound << '\n';
        for (std::size_t group = 0; group < plan.pairs.size(); ++group) {
            const auto [first, second] = plan.pairs[group];
            const auto& allocation = plan.allocations[group];
            pairs << dataset_id << '\t' << nlist << '\t' << plan.name << '\t'
                  << group << '\t' << first << '\t' << second << '\t'
                  << allocation.k1 << '\t' << allocation.k2 << '\t'
                  << allocation.used_states << '\t'
                  << std::setprecision(17) << allocation.sse << '\t'
                  << plan.heldout_group_sse[group] << '\n';
        }
    }
    const auto [cpu, wall] = elapsed(timer);
    resources << dataset_id << '\t' << nlist << '\t'
              << std::setprecision(17) << cpu << '\t' << wall << '\t'
              << peak_rss_bytes() << '\n';
    summary.flush();
    pairs.flush();
    resources.flush();
    std::cerr << "done " << dataset_id << " nlist=" << nlist
              << " cpu=" << cpu << " wall=" << wall << '\n';
}

void run(
        const std::filesystem::path& root,
        const std::filesystem::path& output) {
    if (std::filesystem::exists(output))
        throw std::invalid_argument("matching output exists");
    std::filesystem::create_directories(output);
    std::ofstream summary(output / "summary.tsv");
    std::ofstream pairs(output / "pairs.tsv");
    std::ofstream resources(output / "resources.tsv");
    summary << "dataset\tnlist\tplan\tfit_sse\theldout_sse"
               "\theldout_mse\ta_adjacent_pairs\td_adjacent_pairs"
               "\ta_d_pair_overlap\ta_matching_rounding_bound"
               "\td_matching_rounding_bound\n";
    pairs << "dataset\tnlist\tplan\tgroup\tdim1\tdim2\tk1\tk2"
             "\tused_states\tfit_sse\theldout_sse\n";
    resources << "dataset\tnlist\tcpu_seconds\twall_seconds"
                 "\tpeak_rss_bytes\n";
    for (const std::string dataset : {"sift", "gist"})
        for (std::size_t nlist : {1024U, 4096U})
            run_cell(root, dataset, nlist, output,
                     summary, pairs, resources);
    if (!summary || !pairs || !resources)
        throw std::runtime_error("write matching diagnostic");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4 || std::string(argv[3]) != "frozen")
            throw std::invalid_argument(
                    "usage: mixed_radix_natural_matching "
                    "<admission-root> <output-dir> frozen");
        run(argv[1], argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "mixed_radix_natural_matching: "
                  << error.what() << '\n';
        return 1;
    }
}

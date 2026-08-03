#include "pair_matching.hpp"

#include "../mixed_radix_query/mixed_index.hpp"
#include "../structured_2d/dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/index_io.h>
#include <openssl/sha.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <sys/resource.h>
#include <time.h>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t kDimensions = 128;
constexpr std::size_t kFitRows = 8192;
constexpr std::size_t kBaseRows = 1000000;
constexpr std::size_t kNlist = 4096;
constexpr int kBits = 8;

double cpu_seconds() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return value.tv_sec + value.tv_nsec * 1e-9;
}

std::uint64_t peak_rss_bytes() {
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0)
        throw std::runtime_error("getrusage");
    return static_cast<std::uint64_t>(usage.ru_maxrss) * 1024;
}

struct Timer {
    double cpu = cpu_seconds();
    std::chrono::steady_clock::time_point wall =
            std::chrono::steady_clock::now();
};

std::pair<double, double> elapsed(const Timer& timer) {
    return {
            cpu_seconds() - timer.cpu,
            std::chrono::duration<double>(
                    std::chrono::steady_clock::now() - timer.wall).count()};
}

void append_u64(std::vector<std::uint8_t>& bytes, std::uint64_t value) {
    for (std::size_t offset = 0; offset < 8; ++offset)
        bytes.push_back(static_cast<std::uint8_t>(value >> (8 * offset)));
}

std::array<unsigned char, SHA256_DIGEST_LENGTH> row_hash(
        std::string_view dataset, std::size_t row) {
    std::vector<std::uint8_t> bytes(dataset.begin(), dataset.end());
    append_u64(bytes, kNlist);
    append_u64(bytes, row);
    append_u64(bytes, 20260724);
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    if (::SHA256(bytes.data(), bytes.size(), digest.data()) == nullptr)
        throw std::runtime_error("matched builder SHA-256");
    return digest;
}

std::vector<std::size_t> select_rows(
        std::string_view dataset, std::size_t row_count) {
    struct Entry {
        std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
        std::size_t row = 0;
    };
    if (row_count < kFitRows) throw std::invalid_argument("fit row count");
    std::vector<Entry> entries(row_count);
    for (std::size_t row = 0; row < row_count; ++row)
        entries[row] = {row_hash(dataset, row), row};
    const auto less = [](const Entry& left, const Entry& right) {
        return left.hash != right.hash
                ? left.hash < right.hash
                : left.row < right.row;
    };
    std::partial_sort(
            entries.begin(), entries.begin() + kFitRows,
            entries.end(), less);
    std::vector<std::size_t> rows(kFitRows);
    for (std::size_t index = 0; index < kFitRows; ++index)
        rows[index] = entries[index].row;
    return rows;
}

std::vector<float> fit_residuals(
        std::span<const float> learn,
        std::span<const std::uint32_t> assignments,
        std::span<const float> centroids,
        std::span<const std::size_t> rows) {
    if (learn.size() != assignments.size() * kDimensions ||
        centroids.size() != kNlist * kDimensions ||
        rows.size() != kFitRows)
        throw std::invalid_argument("matched fit shape");
    std::vector<float> fit(kFitRows * kDimensions);
    for (std::size_t index = 0; index < kFitRows; ++index) {
        const std::size_t row = rows[index];
        if (row >= assignments.size() || assignments[row] >= kNlist)
            throw std::out_of_range("matched fit row");
        const float* center = centroids.data() +
                static_cast<std::size_t>(assignments[row]) * kDimensions;
        for (std::size_t dimension = 0; dimension < kDimensions; ++dimension)
            fit[index * kDimensions + dimension] =
                    learn[row * kDimensions + dimension] - center[dimension];
    }
    return fit;
}

std::vector<std::string> split(std::string_view line) {
    std::vector<std::string> fields;
    std::size_t begin = 0;
    while (true) {
        const std::size_t end = line.find('\t', begin);
        fields.emplace_back(line.substr(begin, end - begin));
        if (end == std::string_view::npos) return fields;
        begin = end + 1;
    }
}

std::vector<std::pair<std::size_t, std::size_t>> read_pairs(
        const std::filesystem::path& path,
        const std::string& dataset, const std::string& plan) {
    std::ifstream input(path);
    std::string line;
    if (!std::getline(input, line) ||
        line != "dataset\tnlist\tplan\tgroup\tdim1\tdim2\tk1\tk2"
                "\tused_states\tfit_sse\theldout_sse")
        throw std::runtime_error("offline pair table header");
    std::vector<std::pair<std::size_t, std::size_t>> pairs(64);
    std::vector<bool> found(64, false);
    while (std::getline(input, line)) {
        const auto fields = split(line);
        if (fields.size() != 11 || fields[0] != dataset ||
            std::stoull(fields[1]) != kNlist || fields[2] != plan)
            continue;
        const std::size_t group = std::stoull(fields[3]);
        if (group >= pairs.size() || found[group])
            throw std::runtime_error("offline pair table group");
        pairs[group] = {std::stoull(fields[4]), std::stoull(fields[5])};
        found[group] = true;
    }
    if (!input.eof() || !std::all_of(found.begin(), found.end(),
                                     [](bool value) { return value; }))
        throw std::runtime_error("offline pair table incomplete");
    return pairs;
}

mixedradix::Pairing pairing_of(
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs) {
    mixedradix::Pairing result;
    result.coordinates.reserve(2 * pairs.size());
    for (const auto& [first, second] : pairs) {
        result.coordinates.push_back(static_cast<std::uint16_t>(first));
        result.coordinates.push_back(static_cast<std::uint16_t>(second));
    }
    mixedradix::validate_pairing(result);
    return result;
}

void build_arm(
        const std::string& arm, bool dyadic,
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs,
        const a4orb::Curves& curves, faiss::IndexFlatL2& coarse,
        std::span<const float> base,
        std::span<const std::uint32_t> assignments,
        const std::filesystem::path& output_dir,
        std::ofstream& resources) {
    const auto pairing = pairing_of(pairs);
    const auto model = mixedradix::matching::allocate_paired_model(
            curves, pairs, kBits, dyadic);
    const auto path = output_dir / (arm + ".faiss");
    if (std::filesystem::exists(path))
        throw std::invalid_argument("matched arm output exists");

    const Timer build_timer;
    auto index = mixedradix::build_index(
            coarse, base, assignments, model, pairing);
    const auto [build_cpu, build_wall] = elapsed(build_timer);
    const Timer write_timer;
    faiss::write_index(index.get(), path.c_str());
    const auto matched = mixedradix::MatchedShape{
            pairing, mixedradix::shape_of(model)};
    mixedradix::write_matched_shape(
            path.string() + ".matched.u16", matched);
    const auto [write_cpu, write_wall] = elapsed(write_timer);

    std::unique_ptr<faiss::Index> loaded_owner(
            faiss::read_index(path.c_str()));
    const auto* loaded = dynamic_cast<const faiss::IndexIVFPQ*>(
            loaded_owner.get());
    if (loaded == nullptr || loaded->pq.centroids != index->pq.centroids)
        throw std::runtime_error("matched index load parity");
    const auto loaded_shape = mixedradix::read_matched_shape(
            path.string() + ".matched.u16");
    if (loaded_shape.pairing.coordinates != pairing.coordinates ||
        loaded_shape.shape.radices != matched.shape.radices ||
        loaded_shape.shape.used_states != matched.shape.used_states)
        throw std::runtime_error("matched sidecar load parity");
    mixedradix::validate_codes(*loaded, matched.shape);

    resources << arm << '\t' << std::setprecision(17)
              << build_cpu << '\t' << build_wall << '\t'
              << write_cpu << '\t' << write_wall << '\t'
              << std::filesystem::file_size(path) << '\t'
              << std::filesystem::file_size(
                         path.string() + ".matched.u16") << '\t'
              << peak_rss_bytes() << '\n';
    std::cerr << "built " << arm << " cpu=" << build_cpu
              << " wall=" << build_wall << '\n';
}

std::vector<std::pair<std::size_t, std::size_t>> adjacent_pairs() {
    std::vector<std::pair<std::size_t, std::size_t>> pairs;
    pairs.reserve(kDimensions / 2);
    for (std::size_t dimension = 0; dimension < kDimensions;
         dimension += 2)
        pairs.emplace_back(dimension, dimension + 1);
    return pairs;
}

void write_pair_plan(
        std::ofstream& output, const std::string& dataset,
        const std::string& arm,
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs,
        const a4orb::Curves& curves) {
    (void)pairing_of(pairs);
    for (std::size_t group = 0; group < pairs.size(); ++group) {
        const auto [first, second] = pairs[group];
        const auto allocation = a4or::allocate_pair(
                curves.coordinates[first], curves.coordinates[second],
                kBits, true);
        output << dataset << '\t' << arm << '\t' << group << '\t'
               << first << '\t' << second << '\t'
               << std::setprecision(17)
               << curves.coordinates[first][0].sse << '\t'
               << curves.coordinates[second][0].sse << '\t'
               << allocation.k1 << '\t' << allocation.k2 << '\t'
               << allocation.sse << '\n';
    }
}

void run(
        const std::string& dataset,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pair_table,
        const std::filesystem::path& output_dir,
        const std::string& mode) {
    const bool sift = dataset == "sift";
    if (!sift && dataset != "gist")
        throw std::invalid_argument("matched dataset");
    const std::string dataset_id = sift ? "SIFT1M" : "GIST1M";
    const std::size_t learn_rows = sift ? 100000 : 500000;
    const auto view = admission_root / (sift ? "sift" : "gist_head128");
    const auto nlist_dir = view / "nlist_4096";
    std::filesystem::create_directories(output_dir);

    structured2d::admission::FvecsReader learn_reader(
            view / "learn_pca.fvecs", learn_rows, kDimensions);
    const auto learn = structured2d::admission::read_all(learn_reader);
    const auto learn_assignments = structured2d::admission::read_u32(
            nlist_dir / "learn_assignments.u32", learn_rows);
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index((nlist_dir / "coarse.faiss").c_str()));
    auto* coarse = dynamic_cast<faiss::IndexFlatL2*>(coarse_owner.get());
    if (coarse == nullptr || coarse->d != kDimensions ||
        coarse->ntotal != kNlist)
        throw std::runtime_error("matched coarse index");
    const auto fit = fit_residuals(
            learn, learn_assignments,
            std::span<const float>(
                    coarse->get_xb(), kNlist * kDimensions),
            select_rows(dataset_id, learn_rows));
    const Timer fit_timer;
    const auto curves = a4orb::fit_curves(fit, 1024);
    const auto [fit_cpu, fit_wall] = elapsed(fit_timer);

    structured2d::admission::FvecsReader base_reader(
            view / "base_pca.fvecs", kBaseRows, kDimensions);
    const auto base = structured2d::admission::read_all(base_reader);
    const auto base_assignments = structured2d::admission::read_u32(
            nlist_dir / "base_assignments.u32", kBaseRows);
    const auto d_pairs = read_pairs(pair_table, dataset_id, "D_flex");

    std::ofstream resources(output_dir / "build_resources.tsv");
    resources << "arm\tbuild_cpu_seconds\tbuild_wall_seconds"
                 "\twrite_cpu_seconds\twrite_wall_seconds"
                 "\tindex_bytes\tsidecar_bytes\tpeak_rss_bytes\n";
    if (mode == "frozen") {
        const auto a_pairs = read_pairs(
                pair_table, dataset_id, "A_flex");
        build_arm("A_FLEX", false, a_pairs, curves, *coarse,
                  base, base_assignments, output_dir, resources);
        build_arm("D_ON_A", true, a_pairs, curves, *coarse,
                  base, base_assignments, output_dir, resources);
        build_arm("D_FLEX", true, d_pairs, curves, *coarse,
                  base, base_assignments, output_dir, resources);
    } else if (mode == "closest-baseline-v1") {
        struct Plan {
            std::string arm;
            std::vector<std::pair<std::size_t, std::size_t>> pairs;
        };
        std::vector<Plan> plans;
        plans.push_back({"D_MWM", d_pairs});
        plans.push_back({
                "D_EA",
                mixedradix::matching::eigenvalue_allocation_pairs(curves)});
        constexpr std::uint64_t seeds[] = {
                2026080301ULL, 2026080302ULL, 2026080303ULL};
        for (std::size_t index = 0; index < std::size(seeds); ++index)
            plans.push_back({
                    "D_RANDOM_" + std::to_string(index),
                    mixedradix::matching::random_pairs(
                            kDimensions, seeds[index])});
        plans.push_back({"D_ADJ", adjacent_pairs()});

        std::ofstream pair_output(output_dir / "pairings.tsv");
        pair_output << "dataset\tarm\tgroup\tdim1\tdim2"
                       "\tvariance_proxy1\tvariance_proxy2"
                       "\tk1\tk2\tfit_sse\n";
        for (const auto& plan : plans) {
            write_pair_plan(
                    pair_output, dataset_id, plan.arm,
                    plan.pairs, curves);
            build_arm(plan.arm, true, plan.pairs, curves, *coarse,
                      base, base_assignments, output_dir, resources);
        }
        if (!pair_output)
            throw std::runtime_error("closest pairing output");
    } else {
        throw std::invalid_argument("matched builder mode");
    }
    resources << "SHARED_FIT\t" << std::setprecision(17)
              << fit_cpu << '\t' << fit_wall
              << "\t0\t0\t0\t0\t" << peak_rss_bytes() << '\n';
    if (!resources) throw std::runtime_error("matched resources output");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6 ||
            (std::string(argv[5]) != "frozen" &&
             std::string(argv[5]) != "closest-baseline-v1"))
            throw std::invalid_argument(
                    "usage: mixed_radix_build_matched_arms "
                    "<sift|gist> <admission-root> <pair-table> "
                    "<output-dir> <frozen|closest-baseline-v1>");
        run(argv[1], argv[2], argv[3], argv[4], argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "mixed_radix_build_matched_arms: "
                  << error.what() << '\n';
        return 1;
    }
}

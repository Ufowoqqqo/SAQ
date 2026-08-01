#include "mixed_index.hpp"

#include "../structured_2d/synthetic_timing.hpp"

#include <faiss/IndexFlat.h>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kRows = 8192;
constexpr std::size_t kDimensions = 128;
constexpr std::size_t kGroups = 64;
constexpr std::size_t kHistogramBins = 1024;
constexpr std::size_t kDuplicates = 100;
constexpr std::size_t kTopK = 100;

struct Scenario {
    const char* name;
    int bits;
    std::size_t k1;
    std::size_t k2;
    bool positive;
};

struct Result {
    Scenario scenario{};
    a4or::Allocation arbitrary{};
    a4or::Allocation dyadic{};
    std::size_t prototypes = 0;
    std::size_t arbitrary_collisions = 0;
    std::size_t dyadic_collisions = 0;
    double arbitrary_recall = 0;
    double dyadic_recall = 0;
    std::uint64_t arbitrary_hash = 0;
    std::uint64_t dyadic_hash = 0;
    bool pass = false;
};

float level_value(std::size_t label, std::size_t levels) {
    return static_cast<float>(
            static_cast<std::int64_t>(2 * label) -
            static_cast<std::int64_t>(levels - 1));
}

std::size_t level_for_bin(std::size_t bin, std::size_t levels) {
    const std::size_t small = kHistogramBins / levels;
    const std::size_t large_levels = kHistogramBins % levels;
    const std::size_t large_width = small + 1;
    const std::size_t large_bins = large_levels * large_width;
    if (bin < large_bins) return bin / large_width;
    return large_levels + (bin - large_bins) / small;
}

std::size_t training_level(
        std::size_t row, std::size_t coordinate,
        std::size_t levels) {
    // Every coordinate is a permutation of 1,024 whole eight-row bins. This
    // makes each discrete marginal exact under the production rank histogram.
    const std::size_t multiplier = 2 * coordinate + 1;
    const std::size_t offset =
            static_cast<std::size_t>(a4or::splitmix64(
                    0x53594e5448455449ULL ^ coordinate)) &
            (kRows - 1);
    const std::size_t rank =
            (row * multiplier + offset) & (kRows - 1);
    return level_for_bin(rank / (kRows / kHistogramBins), levels);
}

std::vector<float> training_panel(const Scenario& scenario) {
    const std::size_t null_levels =
            std::size_t{1} << (scenario.bits / 2);
    std::vector<float> result(kRows * kDimensions);
    for (std::size_t row = 0; row < kRows; ++row) {
        for (std::size_t coordinate = 0;
             coordinate < kDimensions; ++coordinate) {
            const std::size_t levels =
                    coordinate == 0 ? scenario.k1 :
                    coordinate == 1 ? scenario.k2 : null_levels;
            result[row * kDimensions + coordinate] = level_value(
                    training_level(row, coordinate, levels), levels);
        }
    }
    return result;
}

std::vector<float> prototype(
        const Scenario& scenario, std::size_t z1, std::size_t z2) {
    const std::size_t null_levels =
            std::size_t{1} << (scenario.bits / 2);
    std::vector<float> result(kDimensions, level_value(0, null_levels));
    result[0] = level_value(z1, scenario.k1);
    result[1] = level_value(z2, scenario.k2);
    return result;
}

std::vector<float> base_vectors(const Scenario& scenario) {
    std::vector<float> result;
    result.reserve(
            scenario.k1 * scenario.k2 * kDuplicates * kDimensions);
    for (std::size_t z2 = 0; z2 < scenario.k2; ++z2)
        for (std::size_t z1 = 0; z1 < scenario.k1; ++z1) {
            const auto point = prototype(scenario, z1, z2);
            for (std::size_t copy = 0; copy < kDuplicates; ++copy)
                result.insert(result.end(), point.begin(), point.end());
        }
    return result;
}

std::size_t code_collisions(
        const Scenario& scenario, const a4orb::Model& model) {
    std::set<std::vector<std::uint8_t>> unique;
    for (std::size_t z2 = 0; z2 < scenario.k2; ++z2)
        for (std::size_t z1 = 0; z1 < scenario.k1; ++z1)
            unique.insert(mixedradix::encode_residual(
                    prototype(scenario, z1, z2), model));
    return scenario.k1 * scenario.k2 - unique.size();
}

struct SearchResult {
    double recall = 0;
    std::uint64_t hash = 0;
};

SearchResult search(
        const Scenario& scenario, const a4orb::Model& model,
        std::span<const float> base) {
    faiss::IndexFlatL2 coarse(kDimensions);
    std::vector<float> centroid(kDimensions, 0);
    coarse.add(1, centroid.data());
    const std::size_t base_rows = base.size() / kDimensions;
    std::vector<std::uint32_t> assignments(base_rows, 0);
    auto index = mixedradix::build_index(
            coarse, base, assignments, model);
    const auto shape = mixedradix::shape_of(model);
    const std::array<faiss::idx_t, 1> lists{0};
    std::vector<structured2d::admission::TopKResult> results;
    results.reserve(scenario.k1 * scenario.k2);
    double recall_sum = 0;
    std::size_t prototype_id = 0;
    for (std::size_t z2 = 0; z2 < scenario.k2; ++z2)
        for (std::size_t z1 = 0; z1 < scenario.k1;
             ++z1, ++prototype_id) {
            const auto query = prototype(scenario, z1, z2);
            auto result =
                    structured2d::admission::search_mixed_radix_lists(
                            *index, shape.radices, shape.used_states,
                            query, centroid, kDimensions, kDimensions,
                            lists, kTopK);
            std::size_t correct = 0;
            const faiss::idx_t first =
                    static_cast<faiss::idx_t>(prototype_id * kDuplicates);
            const faiss::idx_t last = first + kDuplicates;
            for (const faiss::idx_t id : result.ids)
                correct += id >= first && id < last;
            recall_sum += static_cast<double>(correct) / kTopK;
            results.push_back(std::move(result));
        }
    return {
            recall_sum / static_cast<double>(results.size()),
            structured2d::admission::hash_topk(results),
    };
}

Result run(const Scenario& scenario) {
    const auto training = training_panel(scenario);
    const auto curves = a4orb::fit_curves(training, kHistogramBins);
    auto arbitrary = a4orb::allocate_scalar(curves, scenario.bits, false);
    auto dyadic = a4orb::allocate_scalar(curves, scenario.bits, true);
    const auto arbitrary_allocation = a4or::allocate_pair(
            curves.coordinates[0], curves.coordinates[1],
            scenario.bits, false);
    const auto dyadic_allocation = a4or::allocate_pair(
            curves.coordinates[0], curves.coordinates[1],
            scenario.bits, true);
    const auto base = base_vectors(scenario);
    const auto arbitrary_search = search(scenario, arbitrary, base);
    const auto dyadic_search = search(scenario, dyadic, base);
    Result result{
            scenario,
            arbitrary_allocation,
            dyadic_allocation,
            scenario.k1 * scenario.k2,
            code_collisions(scenario, arbitrary),
            code_collisions(scenario, dyadic),
            arbitrary_search.recall,
            dyadic_search.recall,
            arbitrary_search.hash,
            dyadic_search.hash,
            false,
    };
    const bool common =
            result.arbitrary.k1 == scenario.k1 &&
            result.arbitrary.k2 == scenario.k2 &&
            result.arbitrary_collisions == 0 &&
            result.arbitrary_recall == 1.0;
    result.pass = scenario.positive
            ? common && result.dyadic_recall < 1.0 &&
                    result.arbitrary_hash != result.dyadic_hash
            : common && result.dyadic.k1 == scenario.k1 &&
                    result.dyadic.k2 == scenario.k2 &&
                    result.dyadic_collisions == 0 &&
                    result.dyadic_recall == 1.0 &&
                    result.arbitrary_hash == result.dyadic_hash;
    return result;
}

void write(
        const std::filesystem::path& path,
        const std::vector<Result>& results) {
    std::ofstream output(path, std::ios::trunc);
    if (!output) throw std::runtime_error("open witness output");
    output << "scenario\tbits\ttarget_k1\ttarget_k2\tpositive"
              "\ta_k1\ta_k2\ta_used\ta_sse"
              "\td_k1\td_k2\td_used\td_sse"
              "\tprototypes\ta_code_collisions\td_code_collisions"
              "\ta_recall_at_100\td_recall_at_100"
              "\ta_output_hash\td_output_hash\tranking_equal\tdecision\n";
    output << std::setprecision(17);
    for (const auto& result : results)
        output << result.scenario.name << '\t'
               << result.scenario.bits << '\t'
               << result.scenario.k1 << '\t'
               << result.scenario.k2 << '\t'
               << result.scenario.positive << '\t'
               << result.arbitrary.k1 << '\t'
               << result.arbitrary.k2 << '\t'
               << result.arbitrary.used_states << '\t'
               << result.arbitrary.sse << '\t'
               << result.dyadic.k1 << '\t'
               << result.dyadic.k2 << '\t'
               << result.dyadic.used_states << '\t'
               << result.dyadic.sse << '\t'
               << result.prototypes << '\t'
               << result.arbitrary_collisions << '\t'
               << result.dyadic_collisions << '\t'
               << result.arbitrary_recall << '\t'
               << result.dyadic_recall << '\t'
               << std::hex << result.arbitrary_hash << '\t'
               << result.dyadic_hash << std::dec << '\t'
               << (result.arbitrary_hash == result.dyadic_hash) << '\t'
               << (result.pass ? "PASS" : "FAIL") << '\n';
    if (!output) throw std::runtime_error("write witness output");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2)
            throw std::invalid_argument(
                    "usage: mixed_radix_synthetic_witness <output.tsv>");
        const std::array<Scenario, 4> scenarios{{
                {"positive_b4_3x5", 4, 3, 5, true},
                {"null_b4_4x4", 4, 4, 4, false},
                {"positive_b8_15x17", 8, 15, 17, true},
                {"null_b8_16x16", 8, 16, 16, false},
        }};
        std::vector<Result> results;
        for (const auto& scenario : scenarios) {
            std::cerr << "RUN " << scenario.name << '\n';
            results.push_back(run(scenario));
        }
        write(argv[1], results);
        const bool passed = std::all_of(
                results.begin(), results.end(),
                [](const Result& result) { return result.pass; });
        std::cout << (passed ? "PASS" : "FAIL") << '\n';
        return passed ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << "mixed_radix_synthetic_witness: "
                  << error.what() << '\n';
        return 1;
    }
}

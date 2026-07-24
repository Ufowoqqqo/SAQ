#include "admission.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

using namespace structured2d::admission;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void registry_test() {
    require(frozen_nprobes(1024) ==
                    std::vector<std::size_t>{
                            1, 2, 4, 8, 16, 32, 64, 128, 256},
            "nlist 1024 probes");
    require(frozen_nprobes(4096) ==
                    std::vector<std::size_t>{
                            4, 8, 16, 32, 64, 128, 256, 512, 1024},
            "nlist 4096 probes");
    require(forced_arms(Dataset::Sift1M, 32).size() == 11,
            "SIFT 32-byte arms");
    require(forced_arms(Dataset::Gist1M, 32).size() == 11,
            "GIST 32-byte arms");
    require(forced_arms(Dataset::Sift1M, 64).size() == 11,
            "SIFT 64-byte arms");
    require(forced_arms(Dataset::Gist1M, 64).size() == 8,
            "GIST 64-byte arms");
    require(contextual_pool(Dataset::Sift1M).size() == 20,
            "SIFT context pool");
    require(contextual_pool(Dataset::Gist1M).size() == 20,
            "GIST context pool");

    for (const Dataset dataset :
         {Dataset::Sift1M, Dataset::Gist1M}) {
        for (const int budget : {32, 64}) {
            const auto arms = forced_arms(dataset, budget);
            for (std::size_t index = 1; index < arms.size(); ++index)
                require(arms[index - 1].id < arms[index].id,
                        "ASCII arm order");
        }
    }
}

void context_selection_test() {
    const auto specs = contextual_pool(Dataset::Sift1M);
    std::vector<SerializedArm> pool;
    for (const auto& spec : specs) {
        double bytes = spec.average_bits > 0
                ? 8 * spec.average_bits
                : 10.0 * spec.bits;
        pool.push_back({
                spec,
                static_cast<std::uint64_t>(bytes * 1000) + 5000,
                1000,
                4000});
    }
    const auto saq = select_context_slots(
            pool, Backend::Saq, 32, 1000);
    require(saq.lower != nullptr && saq.upper != nullptr,
            "SAQ bracket");
    require(method_bytes_per_vector(*saq.lower, 1000) == 32,
            "SAQ lower");
    require(method_bytes_per_vector(*saq.upper, 1000) == 36,
            "SAQ upper");

    const auto rabitq = select_context_slots(
            pool, Backend::RaBitQ, 32, 1000);
    require(rabitq.lower != nullptr && rabitq.upper != nullptr,
            "RaBitQ bracket");
    require(rabitq.lower->spec.backend == Backend::RaBitQ,
            "non-FastScan exact-byte tie");
}

void distribution_test() {
    const std::vector<std::uint64_t> sizes{10, 300, 2000, 9000};
    const std::vector<std::uint32_t> lists{
            0, 1, 2, 3,
            3, 2, 1, 0};
    const auto result = candidate_distribution(
            sizes, lists, 2, 4);
    require(result.candidates_per_query.minimum == 11310 &&
                    result.candidates_per_query.maximum == 11310,
            "candidate totals");
    require(result.padded_candidates_per_query.minimum == 11392 &&
                    result.padded_candidates_per_query.maximum == 11392,
            "padded candidate totals");
    require(result.selected_list_sizes.minimum == 10 &&
                    result.selected_list_sizes.maximum == 9000,
            "list quantiles");
    require(result.selected_list_fractions.below_256 == 0.25 &&
                    result.selected_list_fractions.from_256_to_1023 == 0.25 &&
                    result.selected_list_fractions.from_1024_to_8191 == 0.25 &&
                    result.selected_list_fractions.at_least_8192 == 0.25,
            "unweighted bins");
    require(
            std::fabs(
                    result.candidate_weighted_list_fractions.at_least_8192 -
                    18000.0 / 22620) < 1e-12,
            "candidate-weighted bins");
}

void projection_test() {
    const std::vector<TimingSample> samples{
            {"A", Dataset::Sift1M, 1024, 32, 1,
             TimingMode::SingleThread, 0.64, 64},
            {"A", Dataset::Sift1M, 1024, 32, 1,
             TimingMode::Batch12, 0.32, 64},
            {"B", Dataset::Gist1M, 4096, 64, 4,
             TimingMode::SingleThread, 1.28, 64},
            {"B", Dataset::Gist1M, 4096, 64, 4,
             TimingMode::Batch12, 0.64, 64}};
    const auto result = project_cpu(3600, samples);
    const double expected_query =
            1.25 * ((0.64 + 0.32) / 64 * 10000 * 7 +
                    (1.28 + 0.64) / 64 * 1000 * 7);
    require(std::fabs(
                    result.projected_query_cpu_seconds -
                    expected_query) < 1e-9,
            "projection formula");
    require(result.total_cpu_seconds ==
                    result.measured_build_cpu_seconds +
                            result.projected_query_cpu_seconds,
            "projection total");
    require(result.within_64_cpu_hours, "projection cap");
}

void seed_test() {
    const auto first = synthetic_seed_words(Dataset::Sift1M, 0);
    require(first == synthetic_seed_words(Dataset::Sift1M, 0),
            "seed replay");
    require(first != synthetic_seed_words(Dataset::Sift1M, 1),
            "query separation");
    require(first != synthetic_seed_words(Dataset::Gist1M, 0),
            "dataset separation");
}

}  // namespace

int main() {
    try {
        registry_test();
        context_selection_test();
        distribution_test();
        projection_test();
        seed_test();
        std::cout << "PASS structured_2d_admission_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace structured2d::admission {

enum class Dataset { Sift1M, Gist1M };

enum class Backend {
    S128,
    D128,
    V128,
    IvfFlat,
    Pq128,
    Opq128,
    IvfPq,
    OpqIvfPq,
    IvfPqFastScan,
    Saq,
    Caq,
    RaBitQ,
    RaBitQFastScan,
};

struct ArmSpec {
    std::string id;
    Backend backend{};
    int budget_bytes = 0;
    int subquantizers = 0;
    int bits = 0;
    double average_bits = 0;
};

std::vector<std::size_t> frozen_nprobes(std::size_t nlist);
std::vector<ArmSpec> forced_arms(Dataset dataset, int budget_bytes);
std::vector<ArmSpec> contextual_pool(Dataset dataset);

struct SerializedArm {
    ArmSpec spec;
    std::uint64_t complete_bytes = 0;
    std::uint64_t common_coarse_bytes = 0;
    std::uint64_t common_id_bytes = 0;
};

double method_bytes_per_vector(
        const SerializedArm& arm, std::uint64_t database_rows);

struct ContextSelection {
    const SerializedArm* lower = nullptr;
    const SerializedArm* upper = nullptr;
};

ContextSelection select_context_slots(
        std::span<const SerializedArm> pool, Backend family,
        int target_bytes, std::uint64_t database_rows);

struct Quantiles {
    double minimum = 0;
    double p10 = 0;
    double p25 = 0;
    double median = 0;
    double p75 = 0;
    double p90 = 0;
    double p95 = 0;
    double p99 = 0;
    double maximum = 0;
};

struct SizeBins {
    double below_256 = 0;
    double from_256_to_1023 = 0;
    double from_1024_to_8191 = 0;
    double at_least_8192 = 0;
};

struct CandidateDistribution {
    Quantiles candidates_per_query;
    Quantiles padded_candidates_per_query;
    Quantiles selected_list_sizes;
    SizeBins query_fractions;
    SizeBins selected_list_fractions;
    SizeBins candidate_weighted_list_fractions;
};

CandidateDistribution candidate_distribution(
        std::span<const std::uint64_t> list_sizes,
        std::span<const std::uint32_t> selected_lists,
        std::size_t queries, std::size_t nprobe);

enum class TimingMode { SingleThread, Batch12 };

struct TimingSample {
    std::string arm_id;
    Dataset dataset{};
    std::size_t nlist = 0;
    int budget_bytes = 0;
    std::size_t nprobe = 0;
    TimingMode mode{};
    double cpu_seconds = 0;
    std::size_t synthetic_queries = 0;
};

struct Projection {
    double measured_build_cpu_seconds = 0;
    double projected_query_cpu_seconds = 0;
    double total_cpu_seconds = 0;
    bool within_64_cpu_hours = false;
};

std::size_t official_query_count(Dataset dataset);
Projection project_cpu(
        double measured_build_cpu_seconds,
        std::span<const TimingSample> samples);

std::array<std::uint64_t, 4> synthetic_seed_words(
        Dataset dataset, std::uint64_t query_index);

}  // namespace structured2d::admission

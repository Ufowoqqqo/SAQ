#include "admission.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <tuple>

namespace structured2d::admission {
namespace {

bool is_context_family(Backend backend, Backend family) {
    if (family == Backend::RaBitQ)
        return backend == Backend::RaBitQ ||
                backend == Backend::RaBitQFastScan;
    return backend == family;
}

int backend_tie_rank(Backend backend) {
    return backend == Backend::RaBitQFastScan ? 1 : 0;
}

SizeBins fractions(
        std::span<const std::uint64_t> values,
        std::span<const std::uint64_t> weights) {
    if (values.empty() ||
        (!weights.empty() && weights.size() != values.size()))
        throw std::invalid_argument("size-bin inputs");
    long double denominator = 0;
    std::array<long double, 4> totals{};
    for (std::size_t index = 0; index < values.size(); ++index) {
        const std::uint64_t weight =
                weights.empty() ? 1 : weights[index];
        denominator += weight;
        const std::size_t bin = values[index] < 256
                ? 0
                : values[index] < 1024
                ? 1
                : values[index] < 8192 ? 2 : 3;
        totals[bin] += weight;
    }
    if (denominator == 0)
        throw std::invalid_argument("empty size-bin weight");
    return {
            static_cast<double>(totals[0] / denominator),
            static_cast<double>(totals[1] / denominator),
            static_cast<double>(totals[2] / denominator),
            static_cast<double>(totals[3] / denominator)};
}

double quantile(
        const std::vector<std::uint64_t>& sorted, double probability) {
    if (sorted.empty() || probability < 0 || probability > 1)
        throw std::invalid_argument("quantile input");
    const double position = probability * (sorted.size() - 1);
    const std::size_t lower = static_cast<std::size_t>(position);
    const std::size_t upper =
            std::min(lower + 1, sorted.size() - 1);
    const double fraction = position - lower;
    return sorted[lower] +
            fraction * (sorted[upper] - sorted[lower]);
}

Quantiles quantiles(std::vector<std::uint64_t> values) {
    std::sort(values.begin(), values.end());
    return {
            quantile(values, 0),
            quantile(values, 0.10),
            quantile(values, 0.25),
            quantile(values, 0.50),
            quantile(values, 0.75),
            quantile(values, 0.90),
            quantile(values, 0.95),
            quantile(values, 0.99),
            quantile(values, 1)};
}

std::uint64_t splitmix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

}  // namespace

std::vector<std::size_t> frozen_nprobes(std::size_t nlist) {
    if (nlist == 1024)
        return {1, 2, 4, 8, 16, 32, 64, 128, 256};
    if (nlist == 4096)
        return {4, 8, 16, 32, 64, 128, 256, 512, 1024};
    throw std::invalid_argument("frozen nlist");
}

std::vector<ArmSpec> forced_arms(
        Dataset dataset, int budget_bytes) {
    if (budget_bytes != 32 && budget_bytes != 64)
        throw std::invalid_argument("frozen code budget");
    std::vector<ArmSpec> arms{
            {"S128", Backend::S128, budget_bytes, 64,
             budget_bytes == 32 ? 4 : 8, 0},
            {"D128", Backend::D128, budget_bytes, 64,
             budget_bytes == 32 ? 4 : 8, 0},
            {"V128", Backend::V128, budget_bytes, 64,
             budget_bytes == 32 ? 4 : 8, 0},
            {"IVFFLAT", Backend::IvfFlat, budget_bytes, 0, 0, 0}};
    if (budget_bytes == 32) {
        arms.insert(
                arms.end(),
                {{"PQ128_M32X8", Backend::Pq128, 32, 32, 8, 0},
                 {"OPQ128_M32X8", Backend::Opq128, 32, 32, 8, 0},
                 {"PQFULL_M32X8", Backend::IvfPq, 32, 32, 8, 0},
                 {"OPQFULL_M32X8", Backend::OpqIvfPq, 32, 32, 8, 0},
                 {"PQFULL_M64X4", Backend::IvfPq, 32, 64, 4, 0},
                 {"OPQFULL_M64X4", Backend::OpqIvfPq, 32, 64, 4, 0},
                 {"PQFSFULL_M64X4",
                  Backend::IvfPqFastScan, 32, 64, 4, 0}});
    } else {
        arms.insert(
                arms.end(),
                {{"PQ128_M64X8", Backend::Pq128, 64, 64, 8, 0},
                 {"OPQ128_M64X8", Backend::Opq128, 64, 64, 8, 0},
                 {"PQFULL_M64X8", Backend::IvfPq, 64, 64, 8, 0},
                 {"OPQFULL_M64X8", Backend::OpqIvfPq, 64, 64, 8, 0}});
        if (dataset == Dataset::Sift1M)
            arms.insert(
                    arms.end(),
                    {{"PQFULL_M128X4", Backend::IvfPq, 64, 128, 4, 0},
                     {"OPQFULL_M128X4",
                      Backend::OpqIvfPq, 64, 128, 4, 0},
                     {"PQFSFULL_M128X4",
                      Backend::IvfPqFastScan, 64, 128, 4, 0}});
    }
    std::sort(
            arms.begin(), arms.end(),
            [](const ArmSpec& left, const ArmSpec& right) {
                return left.id < right.id;
            });
    return arms;
}

std::vector<ArmSpec> contextual_pool(Dataset dataset) {
    const std::vector<double> rates = dataset == Dataset::Sift1M
            ? std::vector<double>{1.5, 2, 2.5, 3.5, 4, 4.5}
            : std::vector<double>{
                      0.2, 4.0 / 15, 1.0 / 3, 0.4,
                      8.0 / 15, 2.0 / 3};
    std::vector<ArmSpec> result;
    for (std::size_t index = 0; index < rates.size(); ++index) {
        result.push_back({
                "SAQ_RATE_" + std::to_string(index),
                Backend::Saq, 0, 0, 0, rates[index]});
        result.push_back({
                "CAQ_RATE_" + std::to_string(index),
                Backend::Caq, 0, 0, 0, rates[index]});
    }
    for (int bits = 1; bits <= 4; ++bits) {
        result.push_back({
                "RABITQ_B" + std::to_string(bits),
                Backend::RaBitQ, 0, 0, bits, 0});
        result.push_back({
                "RABITQFS_B" + std::to_string(bits),
                Backend::RaBitQFastScan, 0, 0, bits, 0});
    }
    std::sort(
            result.begin(), result.end(),
            [](const ArmSpec& left, const ArmSpec& right) {
                return left.id < right.id;
            });
    return result;
}

double method_bytes_per_vector(
        const SerializedArm& arm, std::uint64_t database_rows) {
    if (database_rows == 0 ||
        arm.complete_bytes <
                arm.common_coarse_bytes + arm.common_id_bytes)
        throw std::invalid_argument("method byte accounting");
    return static_cast<double>(
                   arm.complete_bytes - arm.common_coarse_bytes -
                   arm.common_id_bytes) /
            database_rows;
}

ContextSelection select_context_slots(
        std::span<const SerializedArm> pool, Backend family,
        int target_bytes, std::uint64_t database_rows) {
    if ((family != Backend::Saq && family != Backend::Caq &&
         family != Backend::RaBitQ) ||
        (target_bytes != 32 && target_bytes != 64))
        throw std::invalid_argument("context selection");
    ContextSelection result;
    const auto tie = [](const SerializedArm& arm) {
        return std::tuple{
                arm.spec.average_bits > 0
                        ? arm.spec.average_bits
                        : static_cast<double>(arm.spec.bits),
                backend_tie_rank(arm.spec.backend),
                arm.spec.id};
    };
    for (const auto& arm : pool) {
        if (!is_context_family(arm.spec.backend, family)) continue;
        const double bytes =
                method_bytes_per_vector(arm, database_rows);
        if (bytes <= target_bytes) {
            if (result.lower == nullptr ||
                bytes > method_bytes_per_vector(
                                *result.lower, database_rows) ||
                (bytes == method_bytes_per_vector(
                                  *result.lower, database_rows) &&
                 tie(arm) < tie(*result.lower)))
                result.lower = &arm;
        } else if (
                result.upper == nullptr ||
                bytes < method_bytes_per_vector(
                                *result.upper, database_rows) ||
                (bytes == method_bytes_per_vector(
                                  *result.upper, database_rows) &&
                 tie(arm) < tie(*result.upper))) {
            result.upper = &arm;
        }
    }
    return result;
}

CandidateDistribution candidate_distribution(
        std::span<const std::uint64_t> list_sizes,
        std::span<const std::uint32_t> selected_lists,
        std::size_t queries, std::size_t nprobe) {
    if (list_sizes.empty() || queries == 0 || nprobe == 0 ||
        selected_lists.size() != queries * nprobe)
        throw std::invalid_argument("candidate distribution shape");
    std::vector<std::uint64_t> per_query(queries);
    std::vector<std::uint64_t> padded_per_query(queries);
    std::vector<std::uint64_t> per_list;
    per_list.reserve(selected_lists.size());
    for (std::size_t query = 0; query < queries; ++query) {
        for (std::size_t probe = 0; probe < nprobe; ++probe) {
            const std::uint32_t list =
                    selected_lists[query * nprobe + probe];
            if (list >= list_sizes.size())
                throw std::out_of_range("selected list");
            const std::uint64_t size = list_sizes[list];
            per_query[query] += size;
            padded_per_query[query] +=
                    ((size + 31) / 32) * 32;
            per_list.push_back(size);
        }
    }
    return {
            quantiles(per_query),
            quantiles(padded_per_query),
            quantiles(per_list),
            fractions(per_query, {}),
            fractions(per_list, {}),
            fractions(per_list, per_list)};
}

std::size_t official_query_count(Dataset dataset) {
    return dataset == Dataset::Sift1M ? 10000 : 1000;
}

Projection project_cpu(
        double measured_build_cpu_seconds,
        std::span<const TimingSample> samples) {
    if (!std::isfinite(measured_build_cpu_seconds) ||
        measured_build_cpu_seconds < 0 || samples.empty())
        throw std::invalid_argument("CPU projection input");
    long double projected = 0;
    for (const auto& sample : samples) {
        if (sample.synthetic_queries != 64 ||
            !std::isfinite(sample.cpu_seconds) ||
            sample.cpu_seconds <= 0)
            throw std::invalid_argument("CPU timing sample");
        const long double cpu_per_query =
                sample.cpu_seconds / sample.synthetic_queries;
        projected += 1.25L * cpu_per_query *
                official_query_count(sample.dataset) * 7;
    }
    Projection result;
    result.measured_build_cpu_seconds = measured_build_cpu_seconds;
    result.projected_query_cpu_seconds =
            static_cast<double>(projected);
    result.total_cpu_seconds =
            measured_build_cpu_seconds +
            result.projected_query_cpu_seconds;
    result.within_64_cpu_hours =
            result.total_cpu_seconds <= 64 * 3600.0;
    return result;
}

std::array<std::uint64_t, 4> synthetic_seed_words(
        Dataset dataset, std::uint64_t query_index) {
    const std::uint64_t dataset_tag =
            dataset == Dataset::Sift1M
            ? 0x53494654314dULL
            : 0x47495354314dULL;
    const std::uint64_t base =
            20260724ULL ^ dataset_tag ^
            (query_index * 0x9e3779b97f4a7c15ULL);
    return {
            splitmix64(base),
            splitmix64(base + 1),
            splitmix64(base + 2),
            splitmix64(base + 3)};
}

}  // namespace structured2d::admission

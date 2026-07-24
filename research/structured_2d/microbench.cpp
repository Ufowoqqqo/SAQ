#include "microbench.hpp"

#include "compact.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <ctime>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace structured2d {
namespace {

constexpr std::size_t kRows = a4orb::kRowsPerSplit;
constexpr std::size_t kGroups = a4orb::kGroups;
constexpr std::size_t kDimensions = a4orb::kPanelDimensions;

void require_word_bits(int word_bits) {
    if (!supported_word_bits(word_bits))
        throw std::invalid_argument("word bits must be B4 or B8");
}

bool representation_valid(const NativeBenchmark& benchmark) {
    return supported_word_bits(benchmark.word_bits) &&
            benchmark.compact_table_violations == 0 &&
            benchmark.scan_tolerance_violations == 0 &&
            benchmark.expanded_direct_match &&
            benchmark.shared_codes_reused &&
            std::isfinite(benchmark.max_compact_table_difference) &&
            std::isfinite(benchmark.max_scan_difference) &&
            benchmark.payload_bytes ==
                    payload_bytes_per_candidate(benchmark.word_bits);
}

struct ClockSample {
    std::uint64_t cpu_ns = 0;
    std::chrono::steady_clock::time_point wall;
};

struct Elapsed {
    std::uint64_t cpu_ns = 0;
    std::uint64_t wall_ns = 0;
};

std::uint64_t process_cpu_ns() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return static_cast<std::uint64_t>(value.tv_sec) * 1000000000ULL +
            static_cast<std::uint64_t>(value.tv_nsec);
}

ClockSample start_clock() {
    return {process_cpu_ns(), std::chrono::steady_clock::now()};
}

Elapsed stop_clock(const ClockSample& start) {
    return {
            process_cpu_ns() - start.cpu_ns,
            static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - start.wall)
                            .count())};
}

std::array<std::size_t, kMicrobenchmarkProbes> probe_rows() {
    std::array<std::size_t, kMicrobenchmarkProbes> result{};
    for (std::size_t probe = 0;
         probe < kMicrobenchmarkProbes; ++probe) {
        // Midpoints of equal row strata avoid selecting a convenient prefix.
        result[probe] =
                ((2 * probe + 1) * kRows) /
                (2 * kMicrobenchmarkProbes);
    }
    return result;
}

void check_shapes(
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Evaluation& shared_fit,
        const a4orb::Model& independent,
        const a4orb::Evaluation& independent_fit) {
    require_word_bits(shared.word_bits);
    const std::size_t centers = std::size_t{1} << shared.word_bits;
    if (panel.fit.size() != kRows * kDimensions ||
        shared.groups.size() != kGroups ||
        shared.expanded.blocks.size() != kGroups ||
        shared.shape.size() != 2 * centers ||
        independent.word_bits != shared.word_bits ||
        independent.blocks.size() != kGroups ||
        shared_fit.codes.size() != kRows * kGroups ||
        independent_fit.codes.size() != kRows * kGroups)
        throw std::invalid_argument("native benchmark shape");
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto valid_block = [centers](const a4orb::Block& block) {
            return block.dimension == 2 && block.centers == centers &&
                    block.values.size() == 2 * centers;
        };
        if (!valid_block(shared.expanded.blocks[group]) ||
            !valid_block(independent.blocks[group]))
            throw std::invalid_argument("native benchmark block");
    }
}

void build_probe_tables(
        char arm, const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Model& independent,
        std::size_t row, std::span<float> tables) {
    require_word_bits(shared.word_bits);
    const std::size_t centers = std::size_t{1} << shared.word_bits;
    if (tables.size() != kGroups * centers)
        throw std::invalid_argument("query table shape");
    for (std::size_t group = 0; group < kGroups; ++group) {
        const float* query =
                panel.fit.data() + row * kDimensions + 2 * group;
        std::span<float> table(
                tables.data() + group * centers, centers);
        if (arm == 'C')
            build_compact_table(query, shared, group, table);
        else if (arm == 'E')
            build_expanded_table(
                    query, shared.expanded.blocks[group], table);
        else if (arm == 'V')
            build_expanded_table(
                    query, independent.blocks[group], table);
        else
            throw std::invalid_argument("native benchmark arm");
    }
}

NativeTiming run_arm(
        char arm, std::size_t repetition,
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Model& independent,
        const std::array<std::size_t, kMicrobenchmarkProbes>& probes,
        std::span<const std::uint8_t> payload) {
    require_word_bits(shared.word_bits);
    const std::size_t centers = std::size_t{1} << shared.word_bits;
    // Allocation and payload construction remain outside all timed regions.
    std::vector<float> tables(kGroups * centers);
    NativeTiming result;
    result.arm = arm;
    result.repetition = repetition;
    result.table_entries =
            static_cast<std::uint64_t>(kMicrobenchmarkProbes) *
            kGroups * centers;

    result.scans.reserve(kCandidateCounts.size());
    for (const std::size_t candidates : kCandidateCounts)
        result.scans.push_back({
                candidates, 0, 0,
                kMicrobenchmarkProbes * candidates,
                kMicrobenchmarkProbes * candidates * kGroups,
                0});

    for (const std::size_t row : probes) {
        const auto build_start = start_clock();
        build_probe_tables(
                arm, panel, shared, independent, row, tables);
        const auto build_elapsed = stop_clock(build_start);
        result.build_cpu_ns += build_elapsed.cpu_ns;
        result.build_wall_ns += build_elapsed.wall_ns;
        // The scan consumes every table store. This untimed reduction supplies
        // an additional finite execution checksum without changing the path.
        for (const float value : tables) result.build_checksum += value;

        for (auto& scan : result.scans) {
            const auto scan_start = start_clock();
            const double checksum = scan_packed_tables(
                    tables, payload, shared.word_bits,
                    scan.candidate_count);
            const auto elapsed = stop_clock(scan_start);
            scan.cpu_ns += elapsed.cpu_ns;
            scan.wall_ns += elapsed.wall_ns;
            scan.checksum += checksum;
        }
    }
    if (!std::isfinite(result.build_checksum) ||
        !std::all_of(result.scans.begin(), result.scans.end(),
                     [](const PackedScanTiming& scan) {
                         return std::isfinite(scan.checksum);
                     }))
        throw std::runtime_error("non-finite native benchmark checksum");
    return result;
}

}  // namespace

bool supported_word_bits(int word_bits) {
    return word_bits == 4 || word_bits == 8;
}

std::size_t payload_bytes_per_candidate(int word_bits) {
    if (word_bits == 4) return kGroups / 2;
    if (word_bits == 8) return kGroups;
    throw std::invalid_argument("packed payload word bits");
}

std::vector<std::uint8_t> pack_labels(
        std::span<const std::uint16_t> labels, int word_bits) {
    require_word_bits(word_bits);
    if (labels.size() % kGroups != 0)
        throw std::invalid_argument("packed label shape");
    const std::size_t candidates = labels.size() / kGroups;
    std::vector<std::uint8_t> payload(
            candidates * payload_bytes_per_candidate(word_bits));
    const std::uint16_t limit = std::uint16_t{1} << word_bits;
    for (std::size_t candidate = 0; candidate < candidates; ++candidate) {
        const auto row = labels.subspan(candidate * kGroups, kGroups);
        for (std::size_t group = 0; group < kGroups; ++group) {
            if (row[group] >= limit)
                throw std::invalid_argument("packed label range");
            if (word_bits == 8)
                payload[candidate * kGroups + group] =
                        static_cast<std::uint8_t>(row[group]);
            else if ((group & 1U) == 0)
                payload[candidate * (kGroups / 2) + group / 2] =
                        static_cast<std::uint8_t>(row[group]);
            else
                payload[candidate * (kGroups / 2) + group / 2] |=
                        static_cast<std::uint8_t>(row[group] << 4);
        }
    }
    return payload;
}

std::uint16_t decode_label(
        std::span<const std::uint8_t> payload, int word_bits,
        std::size_t candidate, std::size_t group) {
    const std::size_t stride = payload_bytes_per_candidate(word_bits);
    if (group >= kGroups || candidate >= payload.size() / stride ||
        payload.size() % stride != 0)
        throw std::out_of_range("packed label decode");
    if (word_bits == 8) return payload[candidate * stride + group];
    const std::uint8_t byte =
            payload[candidate * stride + group / 2];
    return (group & 1U) == 0 ? byte & 0x0fU : byte >> 4;
}

double scan_packed_tables(
        std::span<const float> tables,
        std::span<const std::uint8_t> payload, int word_bits,
        std::size_t candidates) {
    require_word_bits(word_bits);
    const std::size_t stride = payload_bytes_per_candidate(word_bits);
    const std::size_t centers = std::size_t{1} << word_bits;
    if (tables.size() != kGroups * centers ||
        payload.size() < candidates * stride)
        throw std::invalid_argument("packed scan shape");
    double checksum = 0;
    for (std::size_t candidate = 0; candidate < candidates; ++candidate) {
        const std::uint8_t* code = payload.data() + candidate * stride;
        double estimate = 0;
        for (std::size_t group = 0; group < kGroups; ++group) {
            const std::size_t label = word_bits == 8
                    ? code[group]
                    : ((group & 1U) == 0
                               ? code[group / 2] & 0x0fU
                               : code[group / 2] >> 4);
            estimate += tables[group * centers + label];
        }
        checksum += estimate;
    }
    return checksum;
}

std::array<char, 3> measurement_arm_order(std::size_t repetition) {
    if (repetition >= kMicrobenchmarkRepetitions)
        throw std::out_of_range("measurement repetition");
    constexpr std::array<char, 3> arms{'C', 'E', 'V'};
    return {
            arms[repetition % arms.size()],
            arms[(repetition + 1) % arms.size()],
            arms[(repetition + 2) % arms.size()]};
}

Affordability evaluate_affordability(
        std::size_t candidates,
        double compact_build_cpu, double compact_build_wall,
        double compact_scan_cpu, double compact_scan_wall,
        double reference_build_cpu, double reference_build_wall,
        double reference_scan_cpu, double reference_scan_wall) {
    const std::array<double, 8> values{
            compact_build_cpu, compact_build_wall,
            compact_scan_cpu, compact_scan_wall,
            reference_build_cpu, reference_build_wall,
            reference_scan_cpu, reference_scan_wall};
    if (candidates == 0 ||
        !std::all_of(values.begin(), values.end(),
                     [](double value) {
                         return std::isfinite(value) && value >= 0;
                     }) ||
        reference_build_cpu <= 0 || reference_build_wall <= 0 ||
        reference_scan_cpu <= 0 || reference_scan_wall <= 0)
        throw std::invalid_argument("affordability timing");
    const double compact_total_cpu =
            compact_build_cpu + compact_scan_cpu * candidates;
    const double compact_total_wall =
            compact_build_wall + compact_scan_wall * candidates;
    const double reference_total_cpu =
            reference_build_cpu + reference_scan_cpu * candidates;
    const double reference_total_wall =
            reference_build_wall + reference_scan_wall * candidates;
    Affordability result{
            compact_scan_cpu / reference_scan_cpu,
            compact_scan_wall / reference_scan_wall,
            compact_total_cpu / reference_total_cpu,
            compact_total_wall / reference_total_wall,
            false};
    result.pass = result.scan_cpu_ratio <= 1.10 &&
            result.scan_wall_ratio <= 1.10 &&
            result.total_cpu_ratio <= 1.10 &&
            result.total_wall_ratio <= 1.10;
    return result;
}

void require_native_timing_admission(
        const NativeBenchmark& benchmark) {
    if (!benchmark.timings.empty() || !representation_valid(benchmark))
        throw std::runtime_error(
                "native correctness rejected before timing");
}

NativeBenchmark benchmark_native_tables(
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Evaluation& shared_fit,
        const a4orb::Model& independent,
        const a4orb::Evaluation& independent_fit) {
    check_shapes(panel, shared, shared_fit, independent, independent_fit);
    const auto probes = probe_rows();
    const std::size_t centers =
            std::size_t{1} << shared.word_bits;

    const std::vector<std::uint8_t> shared_payload =
            pack_labels(shared_fit.codes, shared.word_bits);
    const std::vector<std::uint8_t> independent_payload =
            pack_labels(independent_fit.codes, shared.word_bits);

    NativeBenchmark result;
    result.word_bits = shared.word_bits;
    result.shared_codes_reused = true;
    result.payload_bytes =
            payload_bytes_per_candidate(shared.word_bits);

    // The max-count prefix subsumes every registered smaller prefix.  This
    // check uses the same per-candidate accumulation order as the timed scan.
    bool direct_match = true;
    std::vector<float> compact(kGroups * centers);
    std::vector<float> expanded(kGroups * centers);
    for (std::size_t probe = 0;
         probe < kMicrobenchmarkProbes; ++probe) {
        build_probe_tables(
                'C', panel, shared, independent, probes[probe], compact);
        build_probe_tables(
                'E', panel, shared, independent, probes[probe], expanded);
        for (std::size_t entry = 0; entry < compact.size(); ++entry) {
            const double difference = std::fabs(
                    static_cast<double>(compact[entry]) - expanded[entry]);
            result.max_compact_table_difference = std::max(
                    result.max_compact_table_difference, difference);
            result.compact_table_violations +=
                    difference > table_entry_tolerance(expanded[entry]);
        }
        double packed_expanded_sum = 0;
        double direct_expanded_sum = 0;
        for (std::size_t candidate = 0;
             candidate < kCandidateCounts.back(); ++candidate) {
            double compact_estimate = 0;
            double expanded_estimate = 0;
            double direct_estimate = 0;
            double tolerance = 0;
            for (std::size_t group = 0; group < kGroups; ++group) {
                const std::size_t decoded = decode_label(
                        shared_payload, shared.word_bits,
                        candidate, group);
                const std::size_t direct =
                        shared_fit.codes[candidate * kGroups + group];
                direct_match = direct_match && decoded == direct;
                const float compact_value =
                        compact[group * centers + decoded];
                const float expanded_value =
                        expanded[group * centers + decoded];
                compact_estimate += compact_value;
                expanded_estimate += expanded_value;
                direct_estimate +=
                        expanded[group * centers + direct];
                tolerance += table_entry_tolerance(expanded_value);
            }
            const double difference =
                    std::fabs(compact_estimate - expanded_estimate);
            result.max_scan_difference =
                    std::max(result.max_scan_difference, difference);
            result.scan_tolerance_violations += difference > tolerance;
            packed_expanded_sum += expanded_estimate;
            direct_expanded_sum += direct_estimate;
        }
        direct_match = direct_match &&
                packed_expanded_sum == direct_expanded_sum &&
                packed_expanded_sum == scan_packed_tables(
                        expanded, shared_payload,
                        shared.word_bits, kCandidateCounts.back());
    }
    result.expanded_direct_match = direct_match;
    require_native_timing_admission(result);

    const std::array<char, 3> arms{'C', 'E', 'V'};
    const auto payload_for = [&](char arm)
            -> std::span<const std::uint8_t> {
        return arm == 'V'
                ? std::span<const std::uint8_t>(independent_payload)
                : std::span<const std::uint8_t>(shared_payload);
    };

    // One unrecorded warmup establishes code and data pages before timings.
    for (const char arm : arms)
        (void)run_arm(
                arm, 0, panel, shared, independent,
                probes, payload_for(arm));

    result.timings.reserve(3 * kMicrobenchmarkRepetitions);
    for (std::size_t repetition = 0;
         repetition < kMicrobenchmarkRepetitions; ++repetition) {
        for (const char arm : measurement_arm_order(repetition)) {
            result.timings.push_back(run_arm(
                    arm, repetition, panel, shared, independent,
                    probes, payload_for(arm)));
        }
    }
    return result;
}

bool valid(const NativeBenchmark& benchmark) {
    if (!representation_valid(benchmark) ||
        benchmark.timings.size() !=
                3 * kMicrobenchmarkRepetitions)
        return false;
    for (const auto& timing : benchmark.timings) {
        const std::uint64_t centers =
                std::uint64_t{1} << benchmark.word_bits;
        if ((timing.arm != 'C' && timing.arm != 'E' &&
             timing.arm != 'V') ||
            timing.repetition >= kMicrobenchmarkRepetitions ||
            timing.table_entries !=
                    static_cast<std::uint64_t>(kMicrobenchmarkProbes) *
                    kGroups * centers ||
            timing.build_cpu_ns == 0 || timing.build_wall_ns == 0 ||
            !std::isfinite(timing.build_checksum) ||
            timing.scans.size() != kCandidateCounts.size())
            return false;
        for (std::size_t index = 0;
             index < timing.scans.size(); ++index) {
            const auto& scan = timing.scans[index];
            if (scan.candidate_count != kCandidateCounts[index] ||
                scan.candidates_scanned !=
                        kMicrobenchmarkProbes * scan.candidate_count ||
                scan.lookups != scan.candidates_scanned * kGroups ||
                scan.cpu_ns == 0 || scan.wall_ns == 0 ||
                !std::isfinite(scan.checksum))
                return false;
        }
    }
    return true;
}

}  // namespace structured2d

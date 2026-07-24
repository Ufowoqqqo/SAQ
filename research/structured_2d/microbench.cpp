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

using Tables = std::vector<float>;

Tables prebuild_tables(
        char arm, const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Model& independent,
        const std::array<std::size_t, kMicrobenchmarkProbes>& probes) {
    const std::size_t centers = std::size_t{1} << shared.word_bits;
    Tables result(kMicrobenchmarkProbes * kGroups * centers);
    for (std::size_t probe = 0;
         probe < kMicrobenchmarkProbes; ++probe) {
        for (std::size_t group = 0; group < kGroups; ++group) {
            const float* query = panel.fit.data() +
                    probes[probe] * kDimensions + 2 * group;
            std::span<float> table(
                    result.data() +
                            (probe * kGroups + group) * centers,
                    centers);
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
    return result;
}

double build_all_tables(
        char arm, const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Model& independent,
        std::span<float> table) {
    double checksum = 0;
    for (std::size_t row = 0; row < kRows; ++row) {
        for (std::size_t group = 0; group < kGroups; ++group) {
            const float* query =
                    panel.fit.data() + row * kDimensions + 2 * group;
            if (arm == 'C')
                build_compact_table(query, shared, group, table);
            else if (arm == 'E')
                build_expanded_table(
                        query, shared.expanded.blocks[group], table);
            else
                build_expanded_table(
                        query, independent.blocks[group], table);
        }
    }
    // Builders live in a separate translation unit, so their stores cannot be
    // removed. Reading the final table also gives a finite execution checksum
    // without adding a per-entry reduction to the timed scientific path.
    for (const float value : table) checksum += value;
    return checksum;
}

double lookup_all(
        std::span<const float> tables,
        std::span<const std::uint16_t> codes,
        std::size_t centers) {
    double checksum = 0;
    for (std::size_t probe = 0;
         probe < kMicrobenchmarkProbes; ++probe) {
        for (std::size_t row = 0; row < kRows; ++row) {
            for (std::size_t group = 0; group < kGroups; ++group) {
                const std::size_t code = codes[row * kGroups + group];
                checksum += tables[
                        (probe * kGroups + group) * centers + code];
            }
        }
    }
    return checksum;
}

NativeTiming run_arm(
        char arm, std::size_t repetition,
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Model& independent,
        std::span<const float> lookup_tables,
        std::span<const std::uint16_t> codes) {
    const std::size_t centers = std::size_t{1} << shared.word_bits;
    std::vector<float> table(centers);
    NativeTiming result;
    result.arm = arm;
    result.repetition = repetition;
    result.table_entries =
            static_cast<std::uint64_t>(kRows) * kGroups * centers;
    result.lookups =
            static_cast<std::uint64_t>(kMicrobenchmarkProbes) *
            kRows * kGroups;

    const auto build_start = start_clock();
    result.build_checksum = build_all_tables(
            arm, panel, shared, independent, table);
    const auto build_elapsed = stop_clock(build_start);
    result.build_cpu_ns = build_elapsed.cpu_ns;
    result.build_wall_ns = build_elapsed.wall_ns;

    const auto lookup_start = start_clock();
    result.lookup_checksum =
            lookup_all(lookup_tables, codes, centers);
    const auto lookup_elapsed = stop_clock(lookup_start);
    result.lookup_cpu_ns = lookup_elapsed.cpu_ns;
    result.lookup_wall_ns = lookup_elapsed.wall_ns;
    if (!std::isfinite(result.build_checksum) ||
        !std::isfinite(result.lookup_checksum))
        throw std::runtime_error("non-finite native benchmark checksum");
    return result;
}

}  // namespace

NativeBenchmark benchmark_native_tables(
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Evaluation& shared_fit,
        const a4orb::Model& independent,
        const a4orb::Evaluation& independent_fit) {
    check_shapes(panel, shared, shared_fit, independent, independent_fit);
    const auto probes = probe_rows();

    const Tables compact =
            prebuild_tables('C', panel, shared, independent, probes);
    const Tables expanded =
            prebuild_tables('E', panel, shared, independent, probes);
    const Tables v_tables =
            prebuild_tables('V', panel, shared, independent, probes);

    NativeBenchmark result;
    result.word_bits = shared.word_bits;
    result.shared_codes_reused = true;
    for (std::size_t entry = 0; entry < compact.size(); ++entry) {
        const double difference = std::fabs(
                static_cast<double>(compact[entry]) - expanded[entry]);
        result.max_compact_table_difference = std::max(
                result.max_compact_table_difference, difference);
        result.compact_table_violations +=
                difference > table_entry_tolerance(expanded[entry]);
    }

    const std::array<char, 3> arms{'C', 'E', 'V'};
    const auto tables_for = [&](char arm) -> std::span<const float> {
        if (arm == 'C') return compact;
        if (arm == 'E') return expanded;
        return v_tables;
    };
    const auto codes_for = [&](char arm)
            -> std::span<const std::uint16_t> {
        return arm == 'V'
                ? std::span<const std::uint16_t>(independent_fit.codes)
                : std::span<const std::uint16_t>(shared_fit.codes);
    };

    // One unrecorded warmup establishes code and data pages before timings.
    for (const char arm : arms)
        (void)run_arm(
                arm, 0, panel, shared, independent,
                tables_for(arm), codes_for(arm));

    result.timings.reserve(3 * kMicrobenchmarkRepetitions);
    for (std::size_t repetition = 0;
         repetition < kMicrobenchmarkRepetitions; ++repetition) {
        for (std::size_t position = 0; position < arms.size(); ++position) {
            const char arm = arms[(position + repetition) % arms.size()];
            result.timings.push_back(run_arm(
                    arm, repetition, panel, shared, independent,
                    tables_for(arm), codes_for(arm)));
        }
    }
    return result;
}

bool valid(const NativeBenchmark& benchmark) {
    if (benchmark.compact_table_violations != 0 ||
        !benchmark.shared_codes_reused ||
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
                    static_cast<std::uint64_t>(kRows) * kGroups * centers ||
            timing.lookups !=
                    static_cast<std::uint64_t>(kMicrobenchmarkProbes) *
                    kRows * kGroups ||
            timing.build_cpu_ns == 0 || timing.build_wall_ns == 0 ||
            timing.lookup_cpu_ns == 0 || timing.lookup_wall_ns == 0 ||
            !std::isfinite(timing.build_checksum) ||
            !std::isfinite(timing.lookup_checksum))
            return false;
    }
    return true;
}

}  // namespace structured2d

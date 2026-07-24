#pragma once

#include "model.hpp"

#include "../a4_or_b/models.hpp"
#include "../a4_or_b/panel.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace structured2d {

constexpr std::size_t kMicrobenchmarkProbes = 64;
constexpr std::size_t kMicrobenchmarkRepetitions = 9;

struct NativeTiming {
    char arm = '?';
    std::size_t repetition = 0;
    std::uint64_t build_cpu_ns = 0;
    std::uint64_t build_wall_ns = 0;
    std::uint64_t lookup_cpu_ns = 0;
    std::uint64_t lookup_wall_ns = 0;
    std::uint64_t table_entries = 0;
    std::uint64_t lookups = 0;
    double build_checksum = 0;
    double lookup_checksum = 0;
};

struct NativeBenchmark {
    int word_bits = 0;
    std::size_t compact_table_violations = 0;
    double max_compact_table_difference = 0;
    bool shared_codes_reused = false;
    std::vector<NativeTiming> timings;
};

NativeBenchmark benchmark_native_tables(
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Evaluation& shared_fit,
        const a4orb::Model& independent,
        const a4orb::Evaluation& independent_fit);

bool valid(const NativeBenchmark& benchmark);

}  // namespace structured2d

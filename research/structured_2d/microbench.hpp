#pragma once

#include "model.hpp"

#include "../a4_or_b/models.hpp"
#include "../a4_or_b/panel.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace structured2d {

constexpr std::size_t kMicrobenchmarkProbes = 64;
constexpr std::size_t kMicrobenchmarkRepetitions = 9;
constexpr std::array<std::size_t, 4> kCandidateCounts{
        64, 256, 1024, 8192};

bool supported_word_bits(int word_bits);
std::size_t payload_bytes_per_candidate(int word_bits);
std::vector<std::uint8_t> pack_labels(
        std::span<const std::uint16_t> labels, int word_bits);
std::uint16_t decode_label(
        std::span<const std::uint8_t> payload, int word_bits,
        std::size_t candidate, std::size_t group);
double scan_packed_tables(
        std::span<const float> tables,
        std::span<const std::uint8_t> payload, int word_bits,
        std::size_t candidates);
std::array<char, 3> measurement_arm_order(std::size_t repetition);
struct Affordability {
    double scan_cpu_ratio = 0;
    double scan_wall_ratio = 0;
    double total_cpu_ratio = 0;
    double total_wall_ratio = 0;
    bool pass = false;
};

Affordability evaluate_affordability(
        std::size_t candidates,
        double compact_build_cpu, double compact_build_wall,
        double compact_scan_cpu, double compact_scan_wall,
        double reference_build_cpu, double reference_build_wall,
        double reference_scan_cpu, double reference_scan_wall);

struct PackedScanTiming {
    std::size_t candidate_count = 0;
    std::uint64_t cpu_ns = 0;
    std::uint64_t wall_ns = 0;
    std::uint64_t candidates_scanned = 0;
    std::uint64_t lookups = 0;
    double checksum = 0;
};

struct NativeTiming {
    char arm = '?';
    std::size_t repetition = 0;
    std::uint64_t build_cpu_ns = 0;
    std::uint64_t build_wall_ns = 0;
    std::uint64_t table_entries = 0;
    double build_checksum = 0;
    std::vector<PackedScanTiming> scans;
};

struct NativeBenchmark {
    int word_bits = 0;
    std::size_t compact_table_violations = 0;
    double max_compact_table_difference = 0;
    bool shared_codes_reused = false;
    std::size_t payload_bytes = 0;
    std::size_t scan_tolerance_violations = 0;
    double max_scan_difference = 0;
    bool expanded_direct_match = false;
    std::vector<NativeTiming> timings;
};

void require_native_timing_admission(const NativeBenchmark& benchmark);
NativeBenchmark benchmark_native_tables(
        const a4orb::Panel& panel,
        const SharedAffineModel& shared,
        const a4orb::Evaluation& shared_fit,
        const a4orb::Model& independent,
        const a4orb::Evaluation& independent_fit);

bool valid(const NativeBenchmark& benchmark);

}  // namespace structured2d

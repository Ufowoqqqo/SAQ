#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <limits>
#include <sstream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <sys/resource.h>
#include <time.h>

#include "quantization/caq/exact_event_oracle.hpp"

namespace {

using saqlib::caq_validation::ExactEventOracle;
using saqlib::caq_validation::ExactEventOracleResult;

constexpr uint64_t kTargetSamplePerDataset = 50000;
constexpr long double kCpuCeilingHours = 24.0L;

struct Cell {
    std::string_view family;
    size_t dimension;
    uint32_t total_bits;
};

enum class Profile {
    equal,
    dense_unit_interval,
    binary32_full_span,
};

struct TimedRow {
    Cell cell;
    Profile profile;
    uint64_t theoretical_events = 0;
    uint64_t wall_time_ns = 0;
    uint64_t cpu_time_ns = 0;
    uint64_t code_checksum = 0;
    ExactEventOracleResult oracle;
};

struct ProcessMetrics {
    uint64_t wall_time_ns = 0;
    uint64_t cpu_time_ns = 0;
    uint64_t peak_rss_bytes = 0;
};

[[noreturn]] void fail(const std::string &message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string &message) {
    if (!condition) {
        fail(message);
    }
}

uint64_t monotonic_cpu_time_ns() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0) {
        fail("clock_gettime(CLOCK_PROCESS_CPUTIME_ID) failed");
    }
    require(value.tv_sec >= 0 && value.tv_nsec >= 0, "negative process CPU timestamp");
    const uint64_t seconds = static_cast<uint64_t>(value.tv_sec);
    require(
        seconds <= (std::numeric_limits<uint64_t>::max() -
                    static_cast<uint64_t>(value.tv_nsec)) /
                UINT64_C(1000000000),
        "process CPU timestamp overflow");
    return seconds * UINT64_C(1000000000) + static_cast<uint64_t>(value.tv_nsec);
}

uint64_t elapsed_wall_ns(std::chrono::steady_clock::time_point start) {
    const auto elapsed = std::chrono::steady_clock::now() - start;
    const auto nanoseconds =
        std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count();
    require(nanoseconds >= 0, "negative wall-clock interval");
    return static_cast<uint64_t>(nanoseconds);
}

uint64_t peak_rss_bytes() {
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0 || usage.ru_maxrss <= 0) {
        return 0;
    }
    return static_cast<uint64_t>(usage.ru_maxrss) * UINT64_C(1024);
}

std::string_view profile_name(Profile profile) {
    switch (profile) {
    case Profile::equal:
        return "equal";
    case Profile::dense_unit_interval:
        return "dense_unit_interval";
    case Profile::binary32_full_span:
        return "binary32_full_span";
    }
    fail("unknown synthetic profile");
}

float apply_alternating_sign(float magnitude, size_t coordinate) {
    require(magnitude > 0 && std::isfinite(magnitude), "profile produced invalid magnitude");
    return coordinate % 2 == 0 ? magnitude : -magnitude;
}

std::vector<float> make_profile(size_t dimension, Profile profile) {
    require(dimension > 1, "full-span profile requires D>1");
    std::vector<float> input(dimension, 0);
    constexpr uint32_t largest_finite_pattern = UINT32_C(0x7f7fffff);

    for (size_t i = 0; i < dimension; ++i) {
        float magnitude = 0;
        switch (profile) {
        case Profile::equal:
            magnitude = 1.0F;
            break;
        case Profile::dense_unit_interval: {
            const double rank = static_cast<double>(i + 1) /
                static_cast<double>(dimension + 1);
            magnitude = static_cast<float>(0.5 + 0.5 * rank);
            break;
        }
        case Profile::binary32_full_span: {
            const uint64_t numerator = static_cast<uint64_t>(i) *
                static_cast<uint64_t>(largest_finite_pattern - 1U);
            const uint32_t raw = 1U + static_cast<uint32_t>(
                numerator / static_cast<uint64_t>(dimension - 1));
            magnitude = std::bit_cast<float>(raw);
            break;
        }
        }
        input[i] = apply_alternating_sign(magnitude, i);
    }
    return input;
}

uint64_t fnv1a_code_checksum(const ExactEventOracleResult &result) {
    uint64_t hash = UINT64_C(14695981039346656037);
    constexpr uint64_t prime = UINT64_C(1099511628211);
    const auto add_word = [&hash](uint32_t word) {
        for (unsigned shift = 0; shift < 32; shift += 8) {
            hash ^= static_cast<uint8_t>(word >> shift);
            hash *= prime;
        }
    };
    for (uint32_t code : result.magnitude_code) {
        add_word(code);
    }
    for (uint32_t code : result.centered_caq_code) {
        add_word(code);
    }
    return hash;
}

TimedRow run_row(const Cell &cell, Profile profile) {
    const uint64_t levels = UINT64_C(1) << (cell.total_bits - 1U);
    require(
        cell.dimension <= std::numeric_limits<uint64_t>::max() / (levels - 1),
        "theoretical event count overflow");
    const uint64_t theoretical_events =
        static_cast<uint64_t>(cell.dimension) * (levels - 1);
    std::vector<float> input = make_profile(cell.dimension, profile);

    const uint64_t cpu_start = monotonic_cpu_time_ns();
    const auto wall_start = std::chrono::steady_clock::now();
    ExactEventOracleResult oracle = ExactEventOracle::encode(input, cell.total_bits);
    const uint64_t wall_time_ns = elapsed_wall_ns(wall_start);
    const uint64_t cpu_end = monotonic_cpu_time_ns();
    require(cpu_end >= cpu_start, "negative process CPU interval");

    require(!oracle.degenerate, "cost profile unexpectedly degenerated");
    require(oracle.dimension == cell.dimension, "oracle dimension mismatch");
    require(oracle.nonzero_dimensions == cell.dimension, "profile contains a zero coordinate");
    require(
        oracle.work.first_pass_events == theoretical_events,
        "oracle first-pass event count differs from theory");
    require(
        oracle.work.objective_comparisons == theoretical_events,
        "oracle objective comparison count differs from theory");
    require(
        oracle.work.replay_events <= theoretical_events,
        "oracle replay event count exceeds complete event stream");

    TimedRow row;
    row.cell = cell;
    row.profile = profile;
    row.theoretical_events = theoretical_events;
    row.wall_time_ns = wall_time_ns;
    row.cpu_time_ns = cpu_end - cpu_start;
    row.code_checksum = fnv1a_code_checksum(oracle);
    row.oracle = std::move(oracle);
    return row;
}

long double replay_corrected_cpu_ns(const TimedRow &row) {
    const long double events = static_cast<long double>(row.theoretical_events);
    const long double observed_work =
        events + static_cast<long double>(row.oracle.work.replay_events);
    require(observed_work > 0, "cost row has no event work");
    return static_cast<long double>(row.cpu_time_ns) * (2.0L * events) / observed_work;
}

long double cell_upper_cpu_ns(
    std::span<const TimedRow> rows,
    std::string_view family,
    size_t dimension,
    uint32_t total_bits)
{
    long double upper = -1;
    size_t count = 0;
    for (const TimedRow &row : rows) {
        if (row.cell.family == family && row.cell.dimension == dimension &&
            row.cell.total_bits == total_bits) {
            upper = std::max(upper, replay_corrected_cpu_ns(row));
            ++count;
        }
    }
    require(count == 3, "cell does not contain exactly three frozen profiles");
    return upper;
}

std::string hexadecimal(uint64_t value) {
    std::ostringstream output;
    output << "0x" << std::hex << std::setfill('0') << std::setw(16) << value;
    return output.str();
}

void print_result(const std::vector<TimedRow> &rows, const ProcessMetrics &process) {
    const long double g64b11 = cell_upper_cpu_ns(rows, "GIST", 64, 11);
    const long double g192b6 = cell_upper_cpu_ns(rows, "GIST", 192, 6);
    const long double g320b4 = cell_upper_cpu_ns(rows, "GIST", 320, 4);
    const long double g256b2 = cell_upper_cpu_ns(rows, "GIST", 256, 2);
    const long double g832b4 = cell_upper_cpu_ns(rows, "GIST", 832, 4);
    const long double c64b9 = cell_upper_cpu_ns(rows, "CIFAR", 64, 9);
    const long double c192b5 = cell_upper_cpu_ns(rows, "CIFAR", 192, 5);
    const long double c128b3 = cell_upper_cpu_ns(rows, "CIFAR", 128, 3);
    const long double c384b4 = cell_upper_cpu_ns(rows, "CIFAR", 384, 4);

    const long double gist_per_vector_ns = 3.0L *
        (g64b11 + g192b6 + g320b4 + g256b2 + 5.0L * g832b4);
    const long double cifar_per_vector_ns = 3.0L *
        (c64b9 + c192b5 + c128b3 + 4.0L * c384b4);
    const long double total_cpu_hours =
        static_cast<long double>(kTargetSamplePerDataset) *
        (gist_per_vector_ns + cifar_per_vector_ns) / 3.6e12L;
    const bool pass = total_cpu_hours <= kCpuCeilingHours;

    std::cout << "{\n"
              << "  \"schema_version\": 1,\n"
              << "  \"stage\": \"V2-A2\",\n"
              << "  \"status\": \"" << (pass ? "PASS" : "NO-GO") << "\",\n"
              << "  \"synthetic_only\": true,\n"
              << "  \"persistent_bytes\": 0,\n"
              << "  \"profiles\": [\"equal\", \"dense_unit_interval\", "
                 "\"binary32_full_span\"],\n"
              << "  \"rows\": [\n";

    for (size_t i = 0; i < rows.size(); ++i) {
        const TimedRow &row = rows[i];
        const uint64_t levels = UINT64_C(1) << (row.cell.total_bits - 1U);
        std::cout << "    {\n"
                  << "      \"family\": \"" << row.cell.family << "\",\n"
                  << "      \"dimension\": " << row.cell.dimension << ",\n"
                  << "      \"total_bits\": " << row.cell.total_bits << ",\n"
                  << "      \"magnitude_levels\": " << levels << ",\n"
                  << "      \"profile\": \"" << profile_name(row.profile) << "\",\n"
                  << "      \"common_binary_exponent\": "
                  << row.oracle.common_binary_exponent << ",\n"
                  << "      \"theoretical_events\": " << row.theoretical_events << ",\n"
                  << "      \"first_pass_events\": " << row.oracle.work.first_pass_events << ",\n"
                  << "      \"replay_events\": " << row.oracle.work.replay_events << ",\n"
                  << "      \"heap_comparisons\": " << row.oracle.work.heap_comparisons << ",\n"
                  << "      \"objective_comparisons\": "
                  << row.oracle.work.objective_comparisons << ",\n"
                  << "      \"max_integer_bits\": " << row.oracle.work.max_integer_bits << ",\n"
                  << "      \"wall_time_ns\": " << row.wall_time_ns << ",\n"
                  << "      \"cpu_time_ns\": " << row.cpu_time_ns << ",\n"
                  << "      \"replay_corrected_cpu_ns\": " << std::fixed
                  << std::setprecision(3) << replay_corrected_cpu_ns(row) << ",\n"
                  << "      \"code_checksum_fnv1a64\": \""
                  << hexadecimal(row.code_checksum) << "\"\n"
                  << "    }" << (i + 1 == rows.size() ? "\n" : ",\n");
    }

    std::cout << "  ],\n"
              << "  \"feasibility\": {\n"
              << "    \"target_sample_per_dataset\": " << kTargetSamplePerDataset << ",\n"
              << "    \"rotation_seeds\": 3,\n"
              << "    \"cpu_ceiling_hours\": " << std::fixed << std::setprecision(3)
              << kCpuCeilingHours << ",\n"
              << "    \"gist_per_vector_upper_cpu_ns\": " << gist_per_vector_ns << ",\n"
              << "    \"cifar_per_vector_upper_cpu_ns\": " << cifar_per_vector_ns << ",\n"
              << "    \"total_upper_cpu_hours\": " << total_cpu_hours << "\n"
              << "  },\n"
              << "  \"process\": {\n"
              << "    \"wall_time_ns\": " << process.wall_time_ns << ",\n"
              << "    \"cpu_time_ns\": " << process.cpu_time_ns << ",\n"
              << "    \"peak_rss_bytes\": " << process.peak_rss_bytes << "\n"
              << "  }\n"
              << "}\n";
}

void print_failure() {
    std::cout << "{\n"
              << "  \"schema_version\": 1,\n"
              << "  \"stage\": \"V2-A2\",\n"
              << "  \"status\": \"FAIL\"\n"
              << "}\n";
}

} // namespace

int main(int argc, char **argv) {
    static_cast<void>(argv);
    try {
        require(argc == 1, "V2-A2 cost runner accepts no command-line arguments");
        constexpr Cell cells[] = {
            {"GIST", 64, 11},
            {"GIST", 192, 6},
            {"GIST", 320, 4},
            {"GIST", 256, 2},
            {"GIST", 832, 4},
            {"CIFAR", 64, 9},
            {"CIFAR", 192, 5},
            {"CIFAR", 128, 3},
            {"CIFAR", 384, 4},
        };
        constexpr Profile profiles[] = {
            Profile::equal,
            Profile::dense_unit_interval,
            Profile::binary32_full_span,
        };

        const uint64_t process_cpu_start = monotonic_cpu_time_ns();
        const auto process_wall_start = std::chrono::steady_clock::now();
        std::vector<TimedRow> rows;
        rows.reserve(std::size(cells) * std::size(profiles));
        for (const Cell &cell : cells) {
            for (Profile profile : profiles) {
                rows.push_back(run_row(cell, profile));
            }
        }

        ProcessMetrics process;
        process.wall_time_ns = elapsed_wall_ns(process_wall_start);
        const uint64_t process_cpu_end = monotonic_cpu_time_ns();
        require(process_cpu_end >= process_cpu_start, "negative matrix CPU interval");
        process.cpu_time_ns = process_cpu_end - process_cpu_start;
        process.peak_rss_bytes = peak_rss_bytes();
        print_result(rows, process);
        return 0;
    } catch (const std::exception &error) {
        print_failure();
        std::cerr << "V2-A2 cost study failed: " << error.what() << '\n';
        return 1;
    }
}

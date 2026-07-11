#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <sys/resource.h>

#include <boost/multiprecision/cpp_int.hpp>

#include "quantization/caq/exact_event_oracle.hpp"

namespace {

using boost::multiprecision::cpp_int;
using saqlib::caq_validation::ExactEventOracle;
using saqlib::caq_validation::ExactEventOracleResult;
using saqlib::caq_validation::ExactEventOracleWork;

struct ReferenceInput {
    std::vector<cpp_int> magnitudes;
    std::vector<bool> negative;
    int common_exponent = 0;
    size_t nonzero_dimensions = 0;
};

struct ExactScore {
    cpp_int dot = 0;
    cpp_int norm = 0;
};

struct ValidationCounters {
    uint64_t bruteforce_cases = 0;
    uint64_t prior_fixture_cases = 0;
    uint64_t initial_state_cases = 0;
    uint64_t zero_cases = 0;
    uint64_t tie_cases = 0;
    uint64_t padding_cases = 0;
    uint64_t subnormal_cases = 0;
    uint64_t largest_finite_cases = 0;
    uint64_t b11_cases = 0;
    uint64_t mapping_cases = 0;
    uint64_t invalid_input_cases = 0;
    ExactEventOracleWork work;
};

struct ExecutionMetrics {
    double wall_time_ms = 0;
    double cpu_time_ms = 0;
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

void checked_add(uint64_t &target, uint64_t value, const char *message) {
    if (value > std::numeric_limits<uint64_t>::max() - target) {
        throw std::overflow_error(message);
    }
    target += value;
}

ExecutionMetrics measure_execution(
    std::chrono::steady_clock::time_point wall_start,
    std::clock_t cpu_start)
{
    ExecutionMetrics metrics;
    const auto wall_end = std::chrono::steady_clock::now();
    metrics.wall_time_ms =
        std::chrono::duration<double, std::milli>(wall_end - wall_start).count();

    const std::clock_t cpu_end = std::clock();
    if (cpu_start != static_cast<std::clock_t>(-1) &&
        cpu_end != static_cast<std::clock_t>(-1)) {
        metrics.cpu_time_ms = 1000.0 * static_cast<double>(cpu_end - cpu_start) /
            static_cast<double>(CLOCKS_PER_SEC);
    }

    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) == 0 && usage.ru_maxrss > 0) {
        // Linux reports ru_maxrss in KiB.
        metrics.peak_rss_bytes = static_cast<uint64_t>(usage.ru_maxrss) * UINT64_C(1024);
    }
    return metrics;
}

ReferenceInput decompose_reference(std::span<const float> input) {
    if (input.empty()) {
        throw std::invalid_argument("reference decomposition requires nonempty input");
    }

    struct Component {
        uint32_t mantissa = 0;
        int exponent = 0;
        bool negative = false;
    };

    std::vector<Component> components;
    components.reserve(input.size());
    int common_exponent = std::numeric_limits<int>::max();
    size_t nonzero_dimensions = 0;
    for (float value : input) {
        const uint32_t bits = std::bit_cast<uint32_t>(value);
        const uint32_t raw = bits & UINT32_C(0x7fffffff);
        const uint32_t exponent_field = (raw >> 23U) & UINT32_C(0xff);
        const uint32_t fraction = raw & UINT32_C(0x7fffff);
        if (exponent_field == UINT32_C(0xff)) {
            throw std::invalid_argument("reference requires finite binary32 input");
        }

        Component component;
        component.negative = raw != 0 && (bits >> 31U) != 0;
        if (raw != 0) {
            if (exponent_field == 0) {
                component.mantissa = fraction;
                component.exponent = -149;
            } else {
                component.mantissa = UINT32_C(0x800000) | fraction;
                component.exponent = static_cast<int>(exponent_field) - 150;
            }
            common_exponent = std::min(common_exponent, component.exponent);
            ++nonzero_dimensions;
        }
        components.push_back(component);
    }

    ReferenceInput result;
    result.common_exponent = nonzero_dimensions == 0 ? 0 : common_exponent;
    result.nonzero_dimensions = nonzero_dimensions;
    result.magnitudes.assign(input.size(), 0);
    result.negative.reserve(input.size());
    for (size_t i = 0; i < input.size(); ++i) {
        result.negative.push_back(components[i].negative);
        if (components[i].mantissa == 0) {
            continue;
        }
        const int shift = components[i].exponent - common_exponent;
        require(shift >= 0, "reference common-exponent shift is negative");
        result.magnitudes[i] = cpp_int(components[i].mantissa) << shift;
    }
    return result;
}

ExactScore evaluate_reference_code(
    const ReferenceInput &input,
    std::span<const uint32_t> magnitude_code)
{
    require(input.magnitudes.size() == magnitude_code.size(), "reference code dimension mismatch");
    ExactScore score;
    for (size_t i = 0; i < magnitude_code.size(); ++i) {
        const uint64_t grid = UINT64_C(2) * magnitude_code[i] + 1;
        score.dot += input.magnitudes[i] * grid;
        score.norm += grid * grid;
    }
    return score;
}

bool score_better(const ExactScore &lhs, const ExactScore &rhs) {
    return lhs.dot * lhs.dot * rhs.norm > rhs.dot * rhs.dot * lhs.norm;
}

bool score_equal(const ExactScore &lhs, const ExactScore &rhs) {
    return lhs.dot * lhs.dot * rhs.norm == rhs.dot * rhs.dot * lhs.norm;
}

ExactScore brute_force_reference(
    const ReferenceInput &input,
    uint32_t total_bits,
    std::vector<uint32_t> *best_code)
{
    require(total_bits >= 1 && total_bits <= 16, "invalid brute-force bit width");
    const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
    std::vector<size_t> active;
    for (size_t i = 0; i < input.magnitudes.size(); ++i) {
        if (input.magnitudes[i] != 0) {
            active.push_back(i);
        }
    }
    require(active.size() <= 6, "brute-force fixture has too many active coordinates");

    uint64_t configurations = 1;
    for (size_t ignored : active) {
        static_cast<void>(ignored);
        require(
            configurations <= std::numeric_limits<uint64_t>::max() / levels,
            "brute-force configuration count overflow");
        configurations *= levels;
    }

    std::vector<uint32_t> code(input.magnitudes.size(), 0);
    ExactScore best = evaluate_reference_code(input, code);
    std::vector<uint32_t> selected = code;
    for (uint64_t ordinal = 0; ordinal < configurations; ++ordinal) {
        uint64_t value = ordinal;
        for (size_t coordinate : active) {
            code[coordinate] = static_cast<uint32_t>(value % levels);
            value /= levels;
        }
        const ExactScore candidate = evaluate_reference_code(input, code);
        if (score_better(candidate, best)) {
            best = candidate;
            selected = code;
        }
    }
    if (best_code != nullptr) {
        *best_code = std::move(selected);
    }
    return best;
}

void add_work(ValidationCounters &counters, const ExactEventOracleWork &work) {
    checked_add(counters.work.first_pass_events, work.first_pass_events, "aggregate event overflow");
    checked_add(counters.work.replay_events, work.replay_events, "aggregate replay overflow");
    checked_add(counters.work.heap_comparisons, work.heap_comparisons, "aggregate heap overflow");
    checked_add(
        counters.work.objective_comparisons,
        work.objective_comparisons,
        "aggregate objective overflow");
    counters.work.max_integer_bits = std::max(counters.work.max_integer_bits, work.max_integer_bits);
}

void validate_work(
    const ExactEventOracleResult &result,
    const ReferenceInput &reference,
    uint32_t total_bits)
{
    const uint64_t levels = UINT64_C(1) << (total_bits - 1U);
    if (levels > 1) {
        require(
            reference.nonzero_dimensions <=
                std::numeric_limits<uint64_t>::max() / (levels - 1),
            "expected event count overflow");
    }
    const uint64_t expected_events = levels == 1
        ? 0
        : static_cast<uint64_t>(reference.nonzero_dimensions) * (levels - 1);
    require(result.work.first_pass_events == expected_events, "first-pass event count mismatch");
    require(
        result.work.objective_comparisons == expected_events,
        "objective comparison count mismatch");
    require(result.best_event_ordinal <= expected_events, "best event ordinal out of range");
    require(result.work.replay_events == result.best_event_ordinal, "replay event count mismatch");
}

void validate_mapping_and_diagnostics(
    std::span<const float> input,
    const ReferenceInput &reference,
    const ExactEventOracleResult &result,
    ValidationCounters &counters)
{
    require(input.size() == result.magnitude_code.size(), "oracle magnitude dimension mismatch");
    require(input.size() == result.centered_caq_code.size(), "oracle centered dimension mismatch");
    const uint32_t levels = UINT32_C(1) << (result.total_bits - 1U);

    long double input_norm_squared = 0;
    long double grid_norm_squared = 0;
    long double input_grid_dot = 0;
    long double query_grid_dot = 0;
    for (size_t i = 0; i < input.size(); ++i) {
        require(result.magnitude_code[i] < levels, "oracle magnitude code out of range");
        require(result.centered_caq_code[i] < UINT32_C(2) * levels, "centered code out of range");

        const int64_t actual_twice =
            INT64_C(2) * result.centered_caq_code[i] + 1 - INT64_C(2) * levels;
        const int64_t magnitude_twice = INT64_C(2) * result.magnitude_code[i] + 1;
        const int64_t expected_twice = reference.negative[i] ? -magnitude_twice : magnitude_twice;
        require(actual_twice == expected_twice, "centered CAQ mapping mismatch");
        if (reference.magnitudes[i] == 0) {
            require(result.magnitude_code[i] == 0, "zero coordinate did not use minimum magnitude");
            require(actual_twice == 1, "zero coordinate did not use positive-zero convention");
        }

        const long double value = static_cast<long double>(input[i]);
        const long double centered_grid = static_cast<long double>(actual_twice) / 2.0L;
        input_norm_squared += value * value;
        grid_norm_squared += centered_grid * centered_grid;
        input_grid_dot += value * centered_grid;
        const long double query = std::sin(0.17L * static_cast<long double>(i + 1)) +
            0.1L * std::cos(0.07L * static_cast<long double>(i + 3));
        query_grid_dot += query * centered_grid;
    }

    require(input_norm_squared > 0, "nondegenerate mapping input has zero norm");
    require(input_grid_dot > 0, "sign-aligned grid has nonpositive inner product");
    const long double cosine = input_grid_dot /
        std::sqrt(input_norm_squared * grid_norm_squared);
    const long double fac_rescale = input_norm_squared / input_grid_dot;
    const long double tolerance =
        64.0L * static_cast<long double>(input.size()) *
        std::numeric_limits<long double>::epsilon();
    require(
        std::fabs(cosine - result.cosine) <=
            tolerance * std::max(1.0L, std::fabs(cosine)),
        "independent cosine mismatch");
    require(
        std::fabs(fac_rescale - result.fac_rescale_unit_grid) <=
            tolerance * std::max(1.0L, std::fabs(fac_rescale)),
        "independent rescale mismatch");

    const long double estimate_from_centered = fac_rescale * query_grid_dot;
    long double signed_magnitude_query_dot = 0;
    for (size_t i = 0; i < input.size(); ++i) {
        const long double sign = reference.negative[i] ? -1.0L : 1.0L;
        const long double grid = static_cast<long double>(result.magnitude_code[i]) + 0.5L;
        const long double query = std::sin(0.17L * static_cast<long double>(i + 1)) +
            0.1L * std::cos(0.07L * static_cast<long double>(i + 3));
        signed_magnitude_query_dot += sign * grid * query;
    }
    const long double estimate_from_magnitude =
        input_norm_squared * signed_magnitude_query_dot / input_grid_dot;
    require(
        std::fabs(estimate_from_centered - estimate_from_magnitude) <=
            tolerance * std::max(1.0L, std::fabs(estimate_from_magnitude)),
        "independent estimator mapping mismatch");
    ++counters.mapping_cases;
}

ExactEventOracleResult validate_nondegenerate_case(
    const std::vector<float> &input,
    uint32_t total_bits,
    bool compare_bruteforce,
    ValidationCounters &counters)
{
    const ReferenceInput reference = decompose_reference(input);
    require(reference.nonzero_dimensions > 0, "expected nondegenerate test input");
    const ExactEventOracleResult result = ExactEventOracle::encode(input, total_bits);
    require(!result.degenerate, "oracle marked nonzero input degenerate");
    require(result.dimension == input.size(), "oracle dimension metadata mismatch");
    require(
        result.nonzero_dimensions == reference.nonzero_dimensions,
        "oracle nonzero-dimension metadata mismatch");
    require(
        result.common_binary_exponent == reference.common_exponent,
        "oracle common exponent mismatch");

    const ExactScore selected = evaluate_reference_code(reference, result.magnitude_code);
    require(selected.dot == result.score_dot_integer, "oracle exact dot state mismatch");
    require(selected.norm == result.score_norm_integer, "oracle exact norm state mismatch");
    if (compare_bruteforce) {
        const ExactScore brute = brute_force_reference(reference, total_bits, nullptr);
        require(score_equal(selected, brute), "complete-event score differs from brute force");
        ++counters.bruteforce_cases;
    }

    validate_work(result, reference, total_bits);
    validate_mapping_and_diagnostics(input, reference, result, counters);
    add_work(counters, result.work);
    return result;
}

double l2_norm(const std::vector<double> &values) {
    double squared = 0;
    for (double value : values) {
        squared += value * value;
    }
    return std::sqrt(squared);
}

std::vector<float> make_prior_fixture(size_t dimension, uint64_t seed, int family) {
    std::mt19937_64 generator(seed);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::vector<double> values(dimension, 0);
    for (size_t i = 0; i < dimension; ++i) {
        const double jitter = 0.001 + 0.019 * uniform(generator);
        if (family == 0) {
            values[i] = 0.05 + 0.95 * uniform(generator) + jitter;
        } else if (family == 1) {
            values[i] = std::exp(-0.075 * static_cast<double>(i)) + jitter;
        } else if (family == 2) {
            values[i] = 1.0 + 0.01 * static_cast<double>(i) + jitter;
        } else {
            values[i] = (i == 0 ? 12.0 : 0.08 + 0.6 * uniform(generator)) + jitter;
        }
    }
    const double norm = l2_norm(values);
    std::vector<float> result(dimension, 0);
    for (size_t i = 0; i < dimension; ++i) {
        result[i] = static_cast<float>(values[i] / norm);
        require(result[i] > 0 && std::isfinite(result[i]), "prior fixture generation failed");
    }
    return result;
}

void validate_prior_fixtures(ValidationCounters &counters) {
    {
        std::vector<double> raw{1.0, 0.3367865068, 0.3436238941, 0.3457800453};
        const double norm = l2_norm(raw);
        std::vector<float> input;
        input.reserve(raw.size());
        for (double value : raw) {
            input.push_back(static_cast<float>(value / norm));
        }
        validate_nondegenerate_case(input, 3, true, counters);
        ++counters.prior_fixture_cases;
        ++counters.initial_state_cases;
    }

    for (size_t dimension = 2; dimension <= 4; ++dimension) {
        for (uint32_t total_bits = 2; total_bits <= 4; ++total_bits) {
            for (uint64_t seed = 1; seed <= 12; ++seed) {
                const std::vector<float> input = make_prior_fixture(
                    dimension,
                    1000 * dimension + 100 * total_bits + seed,
                    static_cast<int>(seed % 4));
                validate_nondegenerate_case(input, total_bits, true, counters);
                ++counters.prior_fixture_cases;
            }
        }
    }
    require(counters.prior_fixture_cases == 109, "prior fixture count changed");
}

void validate_initial_state_d64(ValidationCounters &counters) {
    std::vector<float> input(64, static_cast<float>(1.0 / std::sqrt(72.0)));
    input[0] = static_cast<float>(3.0 / std::sqrt(72.0));
    const ExactEventOracleResult result = validate_nondegenerate_case(input, 3, false, counters);
    require(result.magnitude_code[0] == 1, "D64 exact initial-state head code mismatch");
    for (size_t i = 1; i < input.size(); ++i) {
        require(result.magnitude_code[i] == 0, "D64 exact initial-state tail code mismatch");
    }
    require(
        std::fabs(result.cosine - 1.0L) <=
            512.0L * std::numeric_limits<long double>::epsilon(),
        "D64 initial-state cosine is not one within rounding error");
    ++counters.initial_state_cases;
}

void validate_zero_and_one_bit_cases(ValidationCounters &counters) {
    {
        std::vector<float> input(64, 0.0F);
        input[1] = -0.0F;
        for (uint32_t total_bits : {1U, 2U, 11U}) {
            const ExactEventOracleResult result = ExactEventOracle::encode(input, total_bits);
            const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
            require(result.degenerate, "all-zero input was not marked degenerate");
            require(result.work.first_pass_events == 0, "degenerate input performed event work");
            for (size_t i = 0; i < input.size(); ++i) {
                require(result.magnitude_code[i] == 0, "degenerate magnitude code mismatch");
                require(result.centered_caq_code[i] == levels, "degenerate positive-zero code mismatch");
            }
            ++counters.zero_cases;
        }
    }

    for (uint32_t total_bits : {1U, 2U, 3U, 4U}) {
        const std::vector<float> input{1.0F, 0.0F, -0.0F, -0.25F};
        validate_nondegenerate_case(input, total_bits, true, counters);
        ++counters.zero_cases;
    }
}

void validate_ties(ValidationCounters &counters) {
    const std::vector<std::vector<float>> inputs{
        {1.0F, 1.0F, 1.0F, 1.0F},
        {1.0F, 2.0F, 4.0F, 8.0F},
        {-0.5F, 0.5F, -1.0F, 1.0F},
    };
    for (const std::vector<float> &input : inputs) {
        for (uint32_t total_bits : {2U, 3U, 4U}) {
            validate_nondegenerate_case(input, total_bits, true, counters);
            ++counters.tie_cases;
        }
    }
}

void validate_padding(ValidationCounters &counters) {
    std::vector<float> input(64, 0.0F);
    input[0] = 1.0F;
    input[1] = -0.375F;
    input[2] = 0.125F;
    const ExactEventOracleResult result = validate_nondegenerate_case(input, 4, true, counters);
    for (size_t i = 3; i < input.size(); ++i) {
        require(result.magnitude_code[i] == 0, "padded lane used nonminimum magnitude");
    }
    ++counters.padding_cases;
}

void validate_binary32_extremes(ValidationCounters &counters) {
    const float denorm = std::numeric_limits<float>::denorm_min();
    {
        const std::vector<float> input{denorm, -2.0F * denorm, 1.0F, -0.0F};
        const ExactEventOracleResult result = validate_nondegenerate_case(input, 1, true, counters);
        require(result.common_binary_exponent == -149, "subnormal common exponent mismatch");
        require(
            result.score_dot_integer == (cpp_int(1) << 149) + 3,
            "explicit subnormal/normal integer decomposition mismatch");
        require(result.score_norm_integer == 4, "B1 subnormal fixture norm mismatch");
        ++counters.subnormal_cases;
    }
    {
        const std::vector<float> input{denorm, -2.0F * denorm, 4.0F * denorm, 0.0F};
        validate_nondegenerate_case(input, 4, true, counters);
        ++counters.subnormal_cases;
    }
    {
        const std::vector<float> input{
            std::numeric_limits<float>::max(),
            denorm,
            -std::ldexp(std::numeric_limits<float>::max(), -1),
        };
        validate_nondegenerate_case(input, 2, true, counters);
        ++counters.subnormal_cases;
        ++counters.largest_finite_cases;
    }
    {
        const float largest = std::numeric_limits<float>::max();
        const std::vector<float> input{largest, -std::ldexp(largest, -1), std::ldexp(largest, -2)};
        validate_nondegenerate_case(input, 3, true, counters);
        ++counters.largest_finite_cases;
    }
    {
        const float largest = std::numeric_limits<float>::max();
        const std::vector<float> input{largest, -std::ldexp(largest, -1), 0.0F};
        const ExactEventOracleResult result = validate_nondegenerate_case(input, 1, true, counters);
        const cpp_int largest_mantissa = (cpp_int(1) << 24) - 1;
        require(result.common_binary_exponent == 103, "largest-finite common exponent mismatch");
        require(
            result.score_dot_integer == 3 * largest_mantissa,
            "explicit largest-finite integer decomposition mismatch");
        require(result.score_norm_integer == 3, "B1 largest-finite fixture norm mismatch");
        ++counters.largest_finite_cases;
    }
}

void validate_b11(ValidationCounters &counters) {
    std::vector<float> input(64, std::ldexp(1.0F, -12));
    input[0] = -1.0F;
    const ExactEventOracleResult result = validate_nondegenerate_case(input, 11, false, counters);
    require(result.magnitude_code[0] > std::numeric_limits<uint8_t>::max(), "B11 fixture did not widen");
    require(result.magnitude_code[0] == 1023, "B11 saturated head magnitude mismatch");
    require(result.centered_caq_code[0] == 0, "B11 negative centered head code mismatch");
    ++counters.b11_cases;
}

template <typename Function>
void require_invalid(Function &&function, ValidationCounters &counters, const char *message) {
    try {
        function();
    } catch (const std::invalid_argument &) {
        ++counters.invalid_input_cases;
        return;
    }
    fail(message);
}

void validate_invalid_inputs(ValidationCounters &counters) {
    require_invalid(
        [] { ExactEventOracle::encode(std::span<const float>(), 2); },
        counters,
        "empty input was accepted");
    const std::vector<float> valid{1.0F};
    require_invalid([&] { ExactEventOracle::encode(valid, 0); }, counters, "B0 was accepted");
    require_invalid([&] { ExactEventOracle::encode(valid, 17); }, counters, "B17 was accepted");
    const std::vector<float> nan_input{std::numeric_limits<float>::quiet_NaN()};
    require_invalid([&] { ExactEventOracle::encode(nan_input, 2); }, counters, "NaN was accepted");
    const std::vector<float> inf_input{std::numeric_limits<float>::infinity()};
    require_invalid([&] { ExactEventOracle::encode(inf_input, 2); }, counters, "infinity was accepted");
}

void print_pass(const ValidationCounters &counters, const ExecutionMetrics &execution) {
    std::cout << "{\n"
              << "  \"schema_version\": 2,\n"
              << "  \"stage\": \"V2-A1\",\n"
              << "  \"status\": \"PASS\",\n"
              << "  \"oracle\": {\n"
              << "    \"name\": \"independent_exact_integer_complete_event\",\n"
              << "    \"official_source\": false,\n"
              << "    \"persistent_bytes\": 0\n"
              << "  },\n"
              << "  \"tests\": {\n"
              << "    \"bruteforce_cases\": " << counters.bruteforce_cases << ",\n"
              << "    \"prior_fixture_cases\": " << counters.prior_fixture_cases << ",\n"
              << "    \"initial_state_cases\": " << counters.initial_state_cases << ",\n"
              << "    \"zero_cases\": " << counters.zero_cases << ",\n"
              << "    \"tie_cases\": " << counters.tie_cases << ",\n"
              << "    \"padding_cases\": " << counters.padding_cases << ",\n"
              << "    \"subnormal_cases\": " << counters.subnormal_cases << ",\n"
              << "    \"largest_finite_cases\": " << counters.largest_finite_cases << ",\n"
              << "    \"b11_cases\": " << counters.b11_cases << ",\n"
              << "    \"mapping_cases\": " << counters.mapping_cases << ",\n"
              << "    \"invalid_input_cases\": " << counters.invalid_input_cases << "\n"
              << "  },\n"
              << "  \"work\": {\n"
              << "    \"first_pass_events\": " << counters.work.first_pass_events << ",\n"
              << "    \"replay_events\": " << counters.work.replay_events << ",\n"
              << "    \"heap_comparisons\": " << counters.work.heap_comparisons << ",\n"
              << "    \"objective_comparisons\": " << counters.work.objective_comparisons << ",\n"
              << "    \"max_integer_bits\": " << counters.work.max_integer_bits << "\n"
              << "  },\n"
              << "  \"execution\": {\n"
              << std::fixed << std::setprecision(3)
              << "    \"wall_time_ms\": " << execution.wall_time_ms << ",\n"
              << "    \"cpu_time_ms\": " << execution.cpu_time_ms << ",\n"
              << "    \"peak_rss_bytes\": " << execution.peak_rss_bytes << "\n"
              << "  }\n"
              << "}\n";
}

void print_fail(const ExecutionMetrics &execution) {
    std::cout << "{\n"
              << "  \"schema_version\": 2,\n"
              << "  \"stage\": \"V2-A1\",\n"
              << "  \"status\": \"FAIL\",\n"
              << "  \"execution\": {\n"
              << std::fixed << std::setprecision(3)
              << "    \"wall_time_ms\": " << execution.wall_time_ms << ",\n"
              << "    \"cpu_time_ms\": " << execution.cpu_time_ms << ",\n"
              << "    \"peak_rss_bytes\": " << execution.peak_rss_bytes << "\n"
              << "  }\n"
              << "}\n";
}

} // namespace

int main(int argc, char **argv) {
    static_cast<void>(argv);
    const auto wall_start = std::chrono::steady_clock::now();
    const std::clock_t cpu_start = std::clock();
    try {
        require(argc == 1, "V2-A1 validator accepts no command-line arguments");
        ValidationCounters counters;
        validate_prior_fixtures(counters);
        validate_initial_state_d64(counters);
        validate_zero_and_one_bit_cases(counters);
        validate_ties(counters);
        validate_padding(counters);
        validate_binary32_extremes(counters);
        validate_b11(counters);
        validate_invalid_inputs(counters);
        print_pass(counters, measure_execution(wall_start, cpu_start));
        return 0;
    } catch (const std::exception &error) {
        print_fail(measure_execution(wall_start, cpu_start));
        std::cerr << "V2-A1 validation failed: " << error.what() << '\n';
        return 1;
    }
}

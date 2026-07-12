#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

#include <time.h>

#include <boost/multiprecision/cpp_int.hpp>

#include "quantization/caq/co0_v2_measurement.hpp"
#include "quantization/caq/exact_one_shell_repair.hpp"

namespace {

using boost::multiprecision::cpp_int;
using saqlib::FloatVec;
using saqlib::caq_validation::Co0V2Arm;
using saqlib::caq_validation::ExactOneShellRepair;
using saqlib::caq_validation::ExactOneShellResult;
using saqlib::caq_validation::FixedWidthOneShellRepair;
using saqlib::caq_validation::FixedWidthOneShellResult;
using saqlib::caq_validation::co0_v2_measure_arm;

struct ReferenceInput {
    std::vector<cpp_int> magnitudes;
    size_t nonzero_dimensions = 0;
};

struct Score {
    cpp_int dot = 0;
    cpp_int norm = 0;
};

struct Counters {
    uint64_t exhaustive_cases = 0;
    uint64_t selected_cases = 0;
    uint64_t positive_examples = 0;
    uint64_t negative_examples = 0;
    uint64_t tie_cases = 0;
    uint64_t zero_cases = 0;
    uint64_t boundary_cases = 0;
    uint64_t subnormal_cases = 0;
    uint64_t largest_finite_cases = 0;
    uint64_t b11_cases = 0;
    uint64_t invalid_input_cases = 0;
    uint64_t fixed_width_parity_cases = 0;
    uint64_t fixed_width_abstentions = 0;
    uint64_t brute_force_codes = 0;
    uint64_t shell_events = 0;
    uint64_t shell_sort_comparisons = 0;
    uint64_t shell_objective_comparisons = 0;
    uint64_t shell_replay_events = 0;
    uint64_t maximum_tracked_transient_bytes = 0;
    uint64_t maximum_fixed_width_tracked_transient_bytes = 0;
};

struct CostRow {
    const char *profile = nullptr;
    uint32_t total_bits = 0;
    uint64_t repetitions = 0;
    uint64_t caq_r6_cpu_ns = 0;
    uint64_t exact_shell_cpu_ns = 0;
    uint64_t fixed_shell_cpu_ns = 0;
    uint64_t shell_events = 0;
    uint64_t shell_sort_comparisons = 0;
    uint64_t shell_filtered_objective_decisions = 0;
    uint64_t shell_exact_objective_fallbacks = 0;
    uint64_t improved = 0;
    uint64_t maximum_fixed_width_tracked_transient_bytes = 0;
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

uint64_t process_cpu_time_ns() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0) {
        throw std::runtime_error("clock_gettime(CLOCK_PROCESS_CPUTIME_ID) failed");
    }
    require(value.tv_sec >= 0 && value.tv_nsec >= 0, "negative CPU timestamp");
    return static_cast<uint64_t>(value.tv_sec) * UINT64_C(1000000000) +
           static_cast<uint64_t>(value.tv_nsec);
}

ReferenceInput decompose_reference(std::span<const float> input) {
    struct Component {
        uint32_t mantissa = 0;
        int exponent = 0;
    };

    require(!input.empty(), "reference decomposition requires nonempty input");
    std::vector<Component> components;
    components.reserve(input.size());
    int common_exponent = std::numeric_limits<int>::max();
    size_t nonzero_dimensions = 0;
    for (float value : input) {
        const uint32_t bits = std::bit_cast<uint32_t>(value);
        const uint32_t raw = bits & UINT32_C(0x7fffffff);
        const uint32_t exponent_field = (raw >> 23U) & UINT32_C(0xff);
        const uint32_t fraction = raw & UINT32_C(0x7fffff);
        if (exponent_field == UINT32_C(0xff) ||
            (raw != 0 && (bits >> 31U) != 0)) {
            throw std::invalid_argument("reference requires finite nonnegative input");
        }

        Component component;
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
    result.nonzero_dimensions = nonzero_dimensions;
    result.magnitudes.assign(input.size(), 0);
    if (nonzero_dimensions == 0) {
        return result;
    }
    for (size_t coordinate = 0; coordinate < components.size(); ++coordinate) {
        if (components[coordinate].mantissa == 0) {
            continue;
        }
        const int shift = components[coordinate].exponent - common_exponent;
        require(shift >= 0, "negative reference exponent shift");
        result.magnitudes[coordinate] =
            cpp_int(components[coordinate].mantissa) << shift;
    }
    return result;
}

Score evaluate(
    const ReferenceInput &input,
    std::span<const uint32_t> code)
{
    require(input.magnitudes.size() == code.size(), "reference score dimension mismatch");
    Score score;
    for (size_t coordinate = 0; coordinate < code.size(); ++coordinate) {
        const uint64_t grid = UINT64_C(2) * code[coordinate] + UINT64_C(1);
        score.dot += input.magnitudes[coordinate] * grid;
        score.norm += grid * grid;
    }
    return score;
}

bool better(const Score &lhs, const Score &rhs) {
    return lhs.dot * lhs.dot * rhs.norm > rhs.dot * rhs.dot * lhs.norm;
}

bool equal(const Score &lhs, const Score &rhs) {
    return lhs.dot * lhs.dot * rhs.norm == rhs.dot * rhs.dot * lhs.norm;
}

Score result_score(const ExactOneShellResult &result) {
    return Score{result.score_dot_integer, result.score_norm_integer};
}

std::vector<uint32_t> brute_force_shell(
    const ReferenceInput &input,
    std::span<const uint32_t> incumbent,
    uint32_t levels,
    Counters &counters)
{
    std::vector<uint32_t> best_code(incumbent.begin(), incumbent.end());
    Score best_score = evaluate(input, best_code);
    std::vector<uint32_t> current(best_code.size(), 0);
    std::function<void(size_t)> visit = [&](size_t coordinate) {
        if (coordinate == current.size()) {
            checked_add(counters.brute_force_codes, 1, "brute-force counter overflow");
            const Score candidate = evaluate(input, current);
            if (better(candidate, best_score)) {
                best_score = candidate;
                best_code = current;
            }
            return;
        }
        const uint32_t low = incumbent[coordinate] == 0
                                 ? 0
                                 : incumbent[coordinate] - 1U;
        const uint32_t high = incumbent[coordinate] + 1U < levels
                                  ? incumbent[coordinate] + 1U
                                  : incumbent[coordinate];
        for (uint32_t code = low; code <= high; ++code) {
            current[coordinate] = code;
            visit(coordinate + 1U);
        }
    };
    visit(0);
    return best_code;
}

void accumulate_work(const ExactOneShellResult &result, Counters &counters) {
    checked_add(counters.shell_events, result.work.events, "shell event counter overflow");
    checked_add(
        counters.shell_sort_comparisons,
        result.work.event_sort_comparisons,
        "shell sort counter overflow");
    checked_add(
        counters.shell_objective_comparisons,
        result.work.objective_comparisons,
        "shell objective counter overflow");
    checked_add(
        counters.shell_replay_events,
        result.work.replay_events,
        "shell replay counter overflow");
    counters.maximum_tracked_transient_bytes = std::max(
        counters.maximum_tracked_transient_bytes,
        result.work.tracked_transient_bytes);
}

ExactOneShellResult validate_case(
    const std::vector<float> &magnitudes,
    const std::vector<uint32_t> &incumbent,
    uint32_t total_bits,
    Counters &counters)
{
    const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
    const ReferenceInput reference = decompose_reference(magnitudes);
    const std::vector<uint32_t> brute =
        brute_force_shell(reference, incumbent, levels, counters);
    const ExactOneShellResult result = ExactOneShellRepair::repair(
        magnitudes,
        incumbent,
        total_bits);
    const FixedWidthOneShellResult fixed = FixedWidthOneShellRepair::repair(
        magnitudes,
        incumbent,
        total_bits);

    require(result.magnitude_code.size() == incumbent.size(), "shell output dimension mismatch");
    require(result.degenerate == (reference.nonzero_dimensions == 0), "shell zero-state mismatch");
    for (size_t coordinate = 0; coordinate < incumbent.size(); ++coordinate) {
        const uint32_t low = incumbent[coordinate] == 0
                                 ? 0
                                 : incumbent[coordinate] - 1U;
        const uint32_t high = incumbent[coordinate] + 1U < levels
                                  ? incumbent[coordinate] + 1U
                                  : incumbent[coordinate];
        require(
            result.magnitude_code[coordinate] >= low &&
                result.magnitude_code[coordinate] <= high,
            "shell output left the radius-one neighborhood");
    }

    if (result.degenerate) {
        require(result.magnitude_code == incumbent, "zero shell changed incumbent code");
        require(!result.improved, "zero shell reported an improvement");
    } else {
        const Score selected = evaluate(reference, result.magnitude_code);
        const Score brute_score = evaluate(reference, brute);
        const Score incumbent_score = evaluate(reference, incumbent);
        require(equal(selected, brute_score), "event shell differs from brute-force shell optimum");
        require(equal(selected, result_score(result)), "reported shell score differs from output code");
        require(!better(incumbent_score, selected), "shell repair regressed the incumbent");
        require(
            result.improved == better(selected, incumbent_score),
            "shell strict-improvement flag mismatch");
    }

    if (fixed.supported) {
        const Score fixed_score = evaluate(reference, fixed.magnitude_code);
        const Score exact_score = evaluate(reference, result.magnitude_code);
        require(equal(fixed_score, exact_score), "fixed-width shell differs from exact shell");
        require(fixed.improved == result.improved, "fixed-width shell improvement flag mismatch");
        require(fixed.degenerate == result.degenerate, "fixed-width shell zero-state mismatch");
        require(fixed.work.events == result.work.events, "fixed-width shell event count mismatch");
        require(
            fixed.work.filtered_objective_decisions +
                    fixed.work.exact_objective_fallbacks ==
                fixed.work.objective_comparisons,
            "fixed-width objective decision accounting mismatch");
        ++counters.fixed_width_parity_cases;
        counters.maximum_fixed_width_tracked_transient_bytes = std::max(
            counters.maximum_fixed_width_tracked_transient_bytes,
            fixed.work.tracked_transient_bytes);
    } else {
        require(fixed.magnitude_code == incumbent, "unsupported fixed-width shell changed code");
        require(!fixed.improved, "unsupported fixed-width shell reported improvement");
        ++counters.fixed_width_abstentions;
    }

    uint64_t expected_events = 0;
    for (size_t coordinate = 0; coordinate < incumbent.size(); ++coordinate) {
        if (reference.magnitudes[coordinate] == 0) {
            continue;
        }
        if (incumbent[coordinate] > 0) {
            ++expected_events;
        }
        if (incumbent[coordinate] + 1U < levels) {
            ++expected_events;
        }
    }
    require(result.work.events == expected_events, "shell event count mismatch");
    require(result.work.events <= 2 * reference.nonzero_dimensions, "shell exceeded 2D+ events");
    const uint64_t expected_objective_comparisons =
        result.degenerate ? 0 : result.work.events + 1U;
    require(
        result.work.objective_comparisons == expected_objective_comparisons,
        "shell objective-comparison count mismatch");
    require(result.work.replay_events <= result.work.events, "shell replay exceeds event count");
    accumulate_work(result, counters);
    return result;
}

void enumerate_vectors(
    size_t dimension,
    uint32_t alphabet,
    const std::function<void(const std::vector<uint32_t> &)> &visitor)
{
    std::vector<uint32_t> values(dimension, 0);
    std::function<void(size_t)> recurse = [&](size_t coordinate) {
        if (coordinate == dimension) {
            visitor(values);
            return;
        }
        for (uint32_t value = 0; value < alphabet; ++value) {
            values[coordinate] = value;
            recurse(coordinate + 1U);
        }
    };
    recurse(0);
}

void validate_exhaustive(Counters &counters) {
    for (size_t dimension = 1; dimension <= 3; ++dimension) {
        for (uint32_t total_bits = 1; total_bits <= 3; ++total_bits) {
            const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
            enumerate_vectors(dimension, 4, [&](const std::vector<uint32_t> &raw) {
                std::vector<float> magnitudes;
                magnitudes.reserve(raw.size());
                for (uint32_t value : raw) {
                    magnitudes.push_back(static_cast<float>(value));
                }
                enumerate_vectors(dimension, levels, [&](const std::vector<uint32_t> &code) {
                    validate_case(magnitudes, code, total_bits, counters);
                    ++counters.exhaustive_cases;
                });
            });
        }
    }

    const std::vector<std::vector<float>> dimension_four_profiles = {
        {0.0F, 1.0F, 2.0F, 3.0F},
        {1.0F, 1.0F, 1.0F, 1.0F},
        {0.5F, 1.25F, 2.75F, 4.0F},
        {4.0F, 2.0F, 1.0F, 0.5F},
    };
    for (const auto &magnitudes : dimension_four_profiles) {
        enumerate_vectors(4, 4, [&](const std::vector<uint32_t> &code) {
            validate_case(magnitudes, code, 3, counters);
            ++counters.exhaustive_cases;
        });
    }
}

void validate_examples_and_edges(Counters &counters) {
    {
        const ExactOneShellResult result =
            validate_case({2.0F, 7.0F}, {1, 3}, 3, counters);
        require(result.improved, "positive running example did not improve");
        require(result.magnitude_code == std::vector<uint32_t>({0, 2}),
                "positive running example selected the wrong code");
        ++counters.positive_examples;
    }
    {
        const ExactOneShellResult result =
            validate_case({1.0F, 3.0F}, {1, 3}, 3, counters);
        require(!result.improved, "negative running example unexpectedly improved");
        require(result.magnitude_code == std::vector<uint32_t>({1, 3}),
                "negative running example changed code");
        ++counters.negative_examples;
    }
    {
        validate_case({1.0F, 1.0F, 1.0F, 1.0F}, {0, 1, 2, 3}, 3, counters);
        ++counters.tie_cases;
    }
    {
        validate_case({0.0F, 0.0F, 0.0F}, {0, 2, 3}, 3, counters);
        ++counters.zero_cases;
    }
    {
        validate_case({1.0F, 2.0F, 4.0F, 8.0F}, {0, 0, 3, 3}, 3, counters);
        ++counters.boundary_cases;
    }
    {
        validate_case(
            {std::numeric_limits<float>::denorm_min(),
             2.0F * std::numeric_limits<float>::denorm_min(),
             1.0F},
            {0, 1, 2},
            3,
            counters);
        ++counters.subnormal_cases;
    }
    {
        validate_case(
            {std::numeric_limits<float>::max(),
             std::nextafter(std::numeric_limits<float>::max(), 0.0F),
             1.0F},
            {3, 3, 0},
            3,
            counters);
        ++counters.largest_finite_cases;
    }
    {
        validate_case(
            {0.125F, 0.25F, 0.5F, 1.0F},
            {0, 127, 511, 1023},
            11,
            counters);
        ++counters.b11_cases;
    }
    counters.selected_cases += 8;
}

template <typename Function>
void expect_invalid(Function &&function, Counters &counters) {
    bool rejected = false;
    try {
        function();
    } catch (const std::exception &) {
        rejected = true;
    }
    require(rejected, "invalid one-shell input was accepted");
    ++counters.invalid_input_cases;
}

void validate_invalid_inputs(Counters &counters) {
    expect_invalid(
        [&] { ExactOneShellRepair::repair({}, {}, 3); },
        counters);
    expect_invalid(
        [&] { ExactOneShellRepair::repair(std::vector<float>{1.0F}, {}, 3); },
        counters);
    expect_invalid(
        [&] { ExactOneShellRepair::repair(std::vector<float>{-1.0F}, std::vector<uint32_t>{0}, 3); },
        counters);
    expect_invalid(
        [&] {
            ExactOneShellRepair::repair(
                std::vector<float>{std::numeric_limits<float>::infinity()},
                std::vector<uint32_t>{0},
                3);
        },
        counters);
    expect_invalid(
        [&] {
            ExactOneShellRepair::repair(
                std::vector<float>{std::numeric_limits<float>::quiet_NaN()},
                std::vector<uint32_t>{0},
                3);
        },
        counters);
    expect_invalid(
        [&] { ExactOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{0}, 0); },
        counters);
    expect_invalid(
        [&] { ExactOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{0}, 17); },
        counters);
    expect_invalid(
        [&] { ExactOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{4}, 3); },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair({}, {}, 3); },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair(std::vector<float>{1.0F}, {}, 3); },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair(std::vector<float>{-1.0F}, std::vector<uint32_t>{0}, 3); },
        counters);
    expect_invalid(
        [&] {
            FixedWidthOneShellRepair::repair(
                std::vector<float>{std::numeric_limits<float>::infinity()},
                std::vector<uint32_t>{0},
                3);
        },
        counters);
    expect_invalid(
        [&] {
            FixedWidthOneShellRepair::repair(
                std::vector<float>{std::numeric_limits<float>::quiet_NaN()},
                std::vector<uint32_t>{0},
                3);
        },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{0}, 0); },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{0}, 17); },
        counters);
    expect_invalid(
        [&] { FixedWidthOneShellRepair::repair(std::vector<float>{1.0F}, std::vector<uint32_t>{4}, 3); },
        counters);
}

FloatVec make_profile(const char *profile) {
    constexpr size_t dimension = 64;
    FloatVec input(static_cast<Eigen::Index>(dimension));
    for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
        float magnitude = 0;
        if (std::string(profile) == "balanced") {
            magnitude = 0.5F +
                        static_cast<float>((coordinate * 37U) % dimension) /
                            static_cast<float>(dimension);
        } else if (std::string(profile) == "dyadic") {
            magnitude = std::ldexp(1.0F, -static_cast<int>(coordinate % 8U));
        } else {
            fail("unknown cost profile");
        }
        input[static_cast<Eigen::Index>(coordinate)] =
            coordinate % 2U == 0 ? magnitude : -magnitude;
    }
    return input;
}

std::vector<float> input_magnitudes(const FloatVec &input) {
    std::vector<float> magnitudes;
    magnitudes.reserve(static_cast<size_t>(input.cols()));
    for (Eigen::Index coordinate = 0; coordinate < input.cols(); ++coordinate) {
        magnitudes.push_back(std::fabs(input[coordinate]));
    }
    return magnitudes;
}

std::vector<uint32_t> magnitude_code(
    const FloatVec &input,
    std::span<const uint32_t> centered_code,
    uint32_t total_bits)
{
    const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
    require(static_cast<size_t>(input.cols()) == centered_code.size(), "centered-code dimension mismatch");
    std::vector<uint32_t> result;
    result.reserve(centered_code.size());
    for (size_t coordinate = 0; coordinate < centered_code.size(); ++coordinate) {
        const uint32_t code = centered_code[coordinate];
        if (input[static_cast<Eigen::Index>(coordinate)] >= 0) {
            require(code >= levels, "positive input has a negative centered code");
            result.push_back(code - levels);
        } else {
            require(code < levels, "negative input has a positive centered code");
            result.push_back(levels - 1U - code);
        }
    }
    return result;
}

CostRow measure_cost(const char *profile, uint32_t total_bits) {
    constexpr uint64_t repetitions = 1024;
    const FloatVec input = make_profile(profile);
    const std::vector<float> magnitudes = input_magnitudes(input);
    CostRow row;
    row.profile = profile;
    row.total_bits = total_bits;
    row.repetitions = repetitions;

    for (uint64_t repetition = 0; repetition < repetitions; ++repetition) {
        const auto caq = co0_v2_measure_arm(input, total_bits, Co0V2Arm::caq_r6);
        checked_add(row.caq_r6_cpu_ns, caq.cpu_time_ns, "CAQ cost counter overflow");

        const std::vector<uint32_t> incumbent =
            magnitude_code(input, caq.code, total_bits);
        const uint64_t exact_start = process_cpu_time_ns();
        const ExactOneShellResult exact_shell =
            ExactOneShellRepair::repair(magnitudes, incumbent, total_bits);
        const uint64_t exact_end = process_cpu_time_ns();
        require(exact_end >= exact_start, "negative exact-shell CPU interval");
        checked_add(
            row.exact_shell_cpu_ns,
            exact_end - exact_start,
            "exact-shell cost counter overflow");

        const uint64_t fixed_start = process_cpu_time_ns();
        const FixedWidthOneShellResult fixed_shell =
            FixedWidthOneShellRepair::repair(magnitudes, incumbent, total_bits);
        const uint64_t fixed_end = process_cpu_time_ns();
        require(fixed_end >= fixed_start, "negative fixed-shell CPU interval");
        require(fixed_shell.supported, "fixed cost profile unexpectedly abstained");
        const ReferenceInput reference = decompose_reference(magnitudes);
        require(
            equal(
                evaluate(reference, exact_shell.magnitude_code),
                evaluate(reference, fixed_shell.magnitude_code)),
            "fixed cost profile differs from exact shell");
        checked_add(
            row.fixed_shell_cpu_ns,
            fixed_end - fixed_start,
            "fixed-shell cost counter overflow");
        checked_add(row.shell_events, fixed_shell.work.events, "cost event counter overflow");
        checked_add(
            row.shell_sort_comparisons,
            fixed_shell.work.event_sort_comparisons,
            "cost sort counter overflow");
        checked_add(
            row.shell_filtered_objective_decisions,
            fixed_shell.work.filtered_objective_decisions,
            "cost filtered-decision counter overflow");
        checked_add(
            row.shell_exact_objective_fallbacks,
            fixed_shell.work.exact_objective_fallbacks,
            "cost exact-fallback counter overflow");
        row.improved += fixed_shell.improved ? 1U : 0U;
        row.maximum_fixed_width_tracked_transient_bytes = std::max(
            row.maximum_fixed_width_tracked_transient_bytes,
            fixed_shell.work.tracked_transient_bytes);
    }
    return row;
}

} // namespace

int main() {
    try {
        const auto wall_start = std::chrono::steady_clock::now();
        const uint64_t cpu_start = process_cpu_time_ns();
        Counters counters;
        validate_exhaustive(counters);
        validate_examples_and_edges(counters);
        validate_invalid_inputs(counters);

        const std::vector<CostRow> cost_rows = {
            measure_cost("balanced", 11),
            measure_cost("dyadic", 11),
            measure_cost("balanced", 9),
            measure_cost("dyadic", 9),
        };
        const uint64_t cpu_end = process_cpu_time_ns();
        require(cpu_end >= cpu_start, "negative validator CPU interval");
        const double wall_ms = std::chrono::duration<double, std::milli>(
                                   std::chrono::steady_clock::now() - wall_start)
                                   .count();

        std::cout << std::fixed << std::setprecision(6);
        std::cout << "{\n"
                  << "  \"status\": \"PASS\",\n"
                  << "  \"scope\": \"synthetic_only\",\n"
                  << "  \"exhaustive_cases\": " << counters.exhaustive_cases << ",\n"
                  << "  \"selected_cases\": " << counters.selected_cases << ",\n"
                  << "  \"positive_examples\": " << counters.positive_examples << ",\n"
                  << "  \"negative_examples\": " << counters.negative_examples << ",\n"
                  << "  \"tie_cases\": " << counters.tie_cases << ",\n"
                  << "  \"zero_cases\": " << counters.zero_cases << ",\n"
                  << "  \"boundary_cases\": " << counters.boundary_cases << ",\n"
                  << "  \"subnormal_cases\": " << counters.subnormal_cases << ",\n"
                  << "  \"largest_finite_cases\": " << counters.largest_finite_cases << ",\n"
                  << "  \"b11_cases\": " << counters.b11_cases << ",\n"
                  << "  \"invalid_input_cases\": " << counters.invalid_input_cases << ",\n"
                  << "  \"fixed_width_parity_cases\": "
                  << counters.fixed_width_parity_cases << ",\n"
                  << "  \"fixed_width_abstentions\": "
                  << counters.fixed_width_abstentions << ",\n"
                  << "  \"brute_force_codes\": " << counters.brute_force_codes << ",\n"
                  << "  \"shell_events\": " << counters.shell_events << ",\n"
                  << "  \"shell_sort_comparisons\": " << counters.shell_sort_comparisons << ",\n"
                  << "  \"shell_objective_comparisons\": "
                  << counters.shell_objective_comparisons << ",\n"
                  << "  \"shell_replay_events\": " << counters.shell_replay_events << ",\n"
                  << "  \"maximum_tracked_transient_bytes\": "
                  << counters.maximum_tracked_transient_bytes << ",\n"
                  << "  \"maximum_fixed_width_tracked_transient_bytes\": "
                  << counters.maximum_fixed_width_tracked_transient_bytes << ",\n"
                  << "  \"cost_rows\": [\n";
        for (size_t index = 0; index < cost_rows.size(); ++index) {
            const CostRow &row = cost_rows[index];
            const double exact_to_caq = row.caq_r6_cpu_ns == 0
                                            ? 0
                                            : static_cast<double>(row.exact_shell_cpu_ns) /
                                                  static_cast<double>(row.caq_r6_cpu_ns);
            const double fixed_to_caq = row.caq_r6_cpu_ns == 0
                                            ? 0
                                            : static_cast<double>(row.fixed_shell_cpu_ns) /
                                                  static_cast<double>(row.caq_r6_cpu_ns);
            std::cout << "    {\"profile\": \"" << row.profile
                      << "\", \"total_bits\": " << row.total_bits
                      << ", \"repetitions\": " << row.repetitions
                      << ", \"caq_r6_cpu_ns\": " << row.caq_r6_cpu_ns
                      << ", \"exact_shell_cpu_ns\": " << row.exact_shell_cpu_ns
                      << ", \"exact_shell_to_caq_cpu\": " << exact_to_caq
                      << ", \"fixed_shell_cpu_ns\": " << row.fixed_shell_cpu_ns
                      << ", \"fixed_shell_to_caq_cpu\": " << fixed_to_caq
                      << ", \"fixed_total_to_caq_cpu\": " << 1.0 + fixed_to_caq
                      << ", \"mean_shell_events\": "
                      << static_cast<double>(row.shell_events) / row.repetitions
                      << ", \"mean_sort_comparisons\": "
                      << static_cast<double>(row.shell_sort_comparisons) / row.repetitions
                      << ", \"mean_filtered_objective_decisions\": "
                      << static_cast<double>(row.shell_filtered_objective_decisions) /
                             row.repetitions
                      << ", \"mean_exact_objective_fallbacks\": "
                      << static_cast<double>(row.shell_exact_objective_fallbacks) /
                             row.repetitions
                      << ", \"maximum_fixed_width_tracked_transient_bytes\": "
                      << row.maximum_fixed_width_tracked_transient_bytes
                      << ", \"improved\": " << row.improved << "}";
            std::cout << (index + 1U == cost_rows.size() ? "\n" : ",\n");
        }
        std::cout << "  ],\n"
                  << "  \"cpu_time_ms\": "
                  << static_cast<double>(cpu_end - cpu_start) / 1e6 << ",\n"
                  << "  \"wall_time_ms\": " << wall_ms << "\n"
                  << "}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "one-shell synthetic validation failed: " << error.what() << '\n';
        return 1;
    }
}

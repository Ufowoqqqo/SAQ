#pragma once

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

namespace saqlib::caq_validation {

using boost::multiprecision::cpp_int;

struct ExactOneShellWork {
    uint64_t events = 0;
    uint64_t event_sort_comparisons = 0;
    uint64_t objective_comparisons = 0;
    uint64_t replay_events = 0;
    uint64_t filtered_objective_decisions = 0;
    uint64_t exact_objective_fallbacks = 0;
    uint64_t tracked_transient_bytes = 0;
};

struct ExactOneShellResult {
    bool degenerate = false;
    bool improved = false;
    uint32_t total_bits = 0;
    std::vector<uint32_t> magnitude_code;
    cpp_int score_dot_integer = 0;
    cpp_int score_norm_integer = 0;
    ExactOneShellWork work;
};

struct FixedWidthOneShellResult {
    bool supported = false;
    bool degenerate = false;
    bool improved = false;
    uint32_t total_bits = 0;
    uint32_t maximum_integer_magnitude_bits = 0;
    std::vector<uint32_t> magnitude_code;
    ExactOneShellWork work;
};

// Exact optimizer for the Cartesian product of each incumbent magnitude
// level and its immediate legal neighbors. This is validation/build-side
// research code; it is not used by the query path.
class ExactOneShellRepair {
    struct BinaryComponent {
        uint32_t mantissa = 0;
        int exponent = 0;
    };

    struct Event {
        uint32_t target_code = 0;
        size_t coordinate = 0;
    };

    static void increment(uint64_t &value, const char *message) {
        if (value == std::numeric_limits<uint64_t>::max()) {
            throw std::overflow_error(message);
        }
        ++value;
    }

    static uint64_t checked_bytes(size_t count, size_t width) {
        if (width != 0 && count > std::numeric_limits<uint64_t>::max() / width) {
            throw std::overflow_error("one-shell byte count overflow");
        }
        return static_cast<uint64_t>(count * width);
    }

    static void add_bytes(uint64_t &total, uint64_t value) {
        if (value > std::numeric_limits<uint64_t>::max() - total) {
            throw std::overflow_error("one-shell byte sum overflow");
        }
        total += value;
    }

    static uint64_t limb_capacity_bytes(const cpp_int &value) {
        const size_t capacity = value.backend().capacity();
        const size_t limb_bytes = sizeof(*value.backend().limbs());
        return checked_bytes(capacity, limb_bytes);
    }

    static BinaryComponent decompose_magnitude(float value) {
        const uint32_t bits = std::bit_cast<uint32_t>(value);
        const uint32_t magnitude = bits & UINT32_C(0x7fffffff);
        const uint32_t exponent_field = (magnitude >> 23U) & UINT32_C(0xff);
        const uint32_t fraction = magnitude & UINT32_C(0x7fffff);

        if (exponent_field == UINT32_C(0xff)) {
            throw std::invalid_argument("one-shell repair requires finite binary32 input");
        }
        if (magnitude != 0 && (bits >> 31U) != 0) {
            throw std::invalid_argument("one-shell repair requires nonnegative magnitudes");
        }

        BinaryComponent component;
        if (magnitude == 0) {
            return component;
        }
        if (exponent_field == 0) {
            component.mantissa = fraction;
            component.exponent = -149;
        } else {
            component.mantissa = UINT32_C(0x800000) | fraction;
            component.exponent = static_cast<int>(exponent_field) - 150;
        }
        return component;
    }

    static bool score_is_better(
        const cpp_int &dot,
        const cpp_int &norm,
        const cpp_int &best_dot,
        const cpp_int &best_norm,
        ExactOneShellWork &work)
    {
        increment(work.objective_comparisons, "one-shell objective counter overflow");
        return dot * dot * best_norm > best_dot * best_dot * norm;
    }

    static void evaluate_code(
        std::span<const cpp_int> magnitudes,
        std::span<const uint32_t> code,
        cpp_int &dot,
        cpp_int &norm)
    {
        if (magnitudes.size() != code.size()) {
            throw std::logic_error("one-shell score dimension mismatch");
        }
        dot = 0;
        norm = 0;
        for (size_t coordinate = 0; coordinate < code.size(); ++coordinate) {
            const uint64_t grid = UINT64_C(2) * code[coordinate] + UINT64_C(1);
            dot += magnitudes[coordinate] * grid;
            norm += grid * grid;
        }
    }

    static uint64_t tracked_transient_bytes(
        const std::vector<BinaryComponent> &components,
        const std::vector<cpp_int> &magnitudes,
        const std::vector<Event> &events,
        const std::vector<uint32_t> &initial_code,
        const std::vector<uint32_t> &incumbent,
        const cpp_int &dot,
        const cpp_int &norm,
        const cpp_int &best_dot,
        const cpp_int &best_norm)
    {
        uint64_t bytes = 0;
        add_bytes(bytes, checked_bytes(components.capacity(), sizeof(BinaryComponent)));
        add_bytes(bytes, checked_bytes(magnitudes.capacity(), sizeof(cpp_int)));
        add_bytes(bytes, checked_bytes(events.capacity(), sizeof(Event)));
        add_bytes(bytes, checked_bytes(initial_code.capacity(), sizeof(uint32_t)));
        add_bytes(bytes, checked_bytes(incumbent.capacity(), sizeof(uint32_t)));
        for (const cpp_int &magnitude : magnitudes) {
            add_bytes(bytes, limb_capacity_bytes(magnitude));
        }
        add_bytes(bytes, checked_bytes(4, sizeof(cpp_int)));
        add_bytes(bytes, limb_capacity_bytes(dot));
        add_bytes(bytes, limb_capacity_bytes(norm));
        add_bytes(bytes, limb_capacity_bytes(best_dot));
        add_bytes(bytes, limb_capacity_bytes(best_norm));
        return bytes;
    }

  public:
    static ExactOneShellResult repair(
        std::span<const float> magnitudes_input,
        std::span<const uint32_t> incumbent_input,
        uint32_t total_bits)
    {
        if (magnitudes_input.empty()) {
            throw std::invalid_argument("one-shell repair requires a positive dimension");
        }
        if (magnitudes_input.size() != incumbent_input.size()) {
            throw std::invalid_argument("one-shell input/code dimension mismatch");
        }
        if (total_bits < 1 || total_bits > 16) {
            throw std::invalid_argument("one-shell repair supports total B in [1,16]");
        }

        const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
        std::vector<uint32_t> incumbent(incumbent_input.begin(), incumbent_input.end());
        for (uint32_t code : incumbent) {
            if (code >= levels) {
                throw std::invalid_argument("one-shell incumbent magnitude code is out of range");
            }
        }

        std::vector<BinaryComponent> components;
        components.reserve(magnitudes_input.size());
        int common_exponent = std::numeric_limits<int>::max();
        size_t nonzero_dimensions = 0;
        for (float value : magnitudes_input) {
            BinaryComponent component = decompose_magnitude(value);
            if (component.mantissa != 0) {
                common_exponent = std::min(common_exponent, component.exponent);
                ++nonzero_dimensions;
            }
            components.push_back(component);
        }

        ExactOneShellResult result;
        result.total_bits = total_bits;
        result.magnitude_code = incumbent;
        if (nonzero_dimensions == 0) {
            result.degenerate = true;
            result.work.tracked_transient_bytes =
                checked_bytes(incumbent.capacity(), sizeof(uint32_t));
            return result;
        }

        std::vector<cpp_int> magnitudes(magnitudes_input.size(), 0);
        for (size_t coordinate = 0; coordinate < components.size(); ++coordinate) {
            if (components[coordinate].mantissa == 0) {
                continue;
            }
            const int shift = components[coordinate].exponent - common_exponent;
            if (shift < 0) {
                throw std::logic_error("invalid one-shell common exponent");
            }
            magnitudes[coordinate] =
                cpp_int(components[coordinate].mantissa) << shift;
        }

        std::vector<uint32_t> initial_code;
        initial_code.reserve(incumbent.size());
        std::vector<Event> events;
        events.reserve(2 * nonzero_dimensions);
        for (size_t coordinate = 0; coordinate < incumbent.size(); ++coordinate) {
            const uint32_t low = incumbent[coordinate] == 0
                                     ? 0
                                     : incumbent[coordinate] - 1U;
            const uint32_t high = incumbent[coordinate] + 1U < levels
                                      ? incumbent[coordinate] + 1U
                                      : incumbent[coordinate];
            initial_code.push_back(low);
            if (magnitudes[coordinate] == 0) {
                continue;
            }
            for (uint32_t target = low + 1U; target <= high; ++target) {
                events.push_back(Event{target, coordinate});
            }
        }
        result.work.events = static_cast<uint64_t>(events.size());

        std::sort(
            events.begin(),
            events.end(),
            [&magnitudes, &result](const Event &lhs, const Event &rhs) {
                increment(
                    result.work.event_sort_comparisons,
                    "one-shell sort-comparison counter overflow");
                const cpp_int left =
                    cpp_int(lhs.target_code) * magnitudes[rhs.coordinate];
                const cpp_int right =
                    cpp_int(rhs.target_code) * magnitudes[lhs.coordinate];
                if (left != right) {
                    return left < right;
                }
                if (lhs.coordinate != rhs.coordinate) {
                    return lhs.coordinate < rhs.coordinate;
                }
                return lhs.target_code < rhs.target_code;
            });

        cpp_int incumbent_dot;
        cpp_int incumbent_norm;
        evaluate_code(magnitudes, incumbent, incumbent_dot, incumbent_norm);
        cpp_int dot;
        cpp_int norm;
        evaluate_code(magnitudes, initial_code, dot, norm);

        cpp_int best_dot = incumbent_dot;
        cpp_int best_norm = incumbent_norm;
        uint64_t best_ordinal = 0;
        bool best_is_shell_path = false;
        if (score_is_better(dot, norm, best_dot, best_norm, result.work)) {
            best_dot = dot;
            best_norm = norm;
            best_is_shell_path = true;
        }

        std::vector<uint32_t> current_code = initial_code;
        uint64_t ordinal = 0;
        for (const Event &event : events) {
            increment(ordinal, "one-shell event ordinal overflow");
            uint32_t &code = current_code[event.coordinate];
            if (event.target_code != code + 1U) {
                throw std::logic_error("invalid one-shell event transition");
            }
            const uint64_t old_grid = UINT64_C(2) * code + UINT64_C(1);
            code = event.target_code;
            dot += UINT32_C(2) * magnitudes[event.coordinate];
            norm += UINT64_C(4) * old_grid + UINT64_C(4);
            if (score_is_better(dot, norm, best_dot, best_norm, result.work)) {
                best_dot = dot;
                best_norm = norm;
                best_ordinal = ordinal;
                best_is_shell_path = true;
            }
        }

        if (best_is_shell_path) {
            result.improved = true;
            result.magnitude_code = initial_code;
            for (uint64_t index = 0; index < best_ordinal; ++index) {
                const Event &event = events[static_cast<size_t>(index)];
                result.magnitude_code[event.coordinate] = event.target_code;
                increment(result.work.replay_events, "one-shell replay counter overflow");
            }
        }
        result.score_dot_integer = std::move(best_dot);
        result.score_norm_integer = std::move(best_norm);
        result.work.tracked_transient_bytes = tracked_transient_bytes(
            components,
            magnitudes,
            events,
            initial_code,
            incumbent,
            dot,
            norm,
            result.score_dot_integer,
            result.score_norm_integer);
        return result;
    }
};

// Fixed-width-integer variant for ordinary binary32 exponent spans. It avoids
// dynamic multiprecision integers but retains O(D) work arrays. It abstains
// and preserves the incumbent if its exact arithmetic cannot represent the
// input; there is no exact-oracle fallback.
class FixedWidthOneShellRepair {
    __extension__ typedef unsigned __int128 NativeUint128;
    using uint256_t = boost::multiprecision::uint256_t;

    struct BinaryComponent {
        uint32_t mantissa = 0;
        int exponent = 0;
    };

    struct Event {
        uint32_t target_code = 0;
        size_t coordinate = 0;
    };

    static void increment(uint64_t &value, const char *message) {
        if (value == std::numeric_limits<uint64_t>::max()) {
            throw std::overflow_error(message);
        }
        ++value;
    }

    static BinaryComponent decompose_magnitude(float value) {
        const uint32_t bits = std::bit_cast<uint32_t>(value);
        const uint32_t magnitude = bits & UINT32_C(0x7fffffff);
        const uint32_t exponent_field = (magnitude >> 23U) & UINT32_C(0xff);
        const uint32_t fraction = magnitude & UINT32_C(0x7fffff);
        if (exponent_field == UINT32_C(0xff)) {
            throw std::invalid_argument("fixed-width shell requires finite binary32 input");
        }
        if (magnitude != 0 && (bits >> 31U) != 0) {
            throw std::invalid_argument("fixed-width shell requires nonnegative magnitudes");
        }

        BinaryComponent component;
        if (magnitude == 0) {
            return component;
        }
        if (exponent_field == 0) {
            component.mantissa = fraction;
            component.exponent = -149;
        } else {
            component.mantissa = UINT32_C(0x800000) | fraction;
            component.exponent = static_cast<int>(exponent_field) - 150;
        }
        return component;
    }

    static uint32_t bit_width(uint64_t value) {
        if (value == 0) {
            return 0;
        }
        return 64U - static_cast<uint32_t>(std::countl_zero(value));
    }

    static uint256_t widen(NativeUint128 value) {
        const uint64_t low = static_cast<uint64_t>(value);
        const uint64_t high = static_cast<uint64_t>(value >> 64U);
        return (uint256_t(high) << 64U) | uint256_t(low);
    }

    static double approximate_cross_product(NativeUint128 dot, uint64_t norm) {
        const double dot_value = static_cast<double>(dot);
        return dot_value * dot_value * static_cast<double>(norm);
    }

    static bool score_is_better(
        NativeUint128 dot,
        uint64_t norm,
        NativeUint128 best_dot,
        uint64_t best_norm,
        ExactOneShellWork &work)
    {
        increment(work.objective_comparisons, "fixed-width shell objective counter overflow");
        const double left = approximate_cross_product(dot, best_norm);
        const double right = approximate_cross_product(best_dot, norm);
        // Each positive cross product has two integer conversions and two
        // rounded multiplications. A 64-epsilon separation is a conservative
        // filter; ambiguous comparisons retain the exact uint256_t test.
        constexpr double separation =
            64.0 * std::numeric_limits<double>::epsilon();
        if (std::isfinite(left) && std::isfinite(right) &&
            left > right * (1.0 + separation)) {
            increment(
                work.filtered_objective_decisions,
                "fixed-width filtered-decision counter overflow");
            return true;
        }
        if (std::isfinite(left) && std::isfinite(right) &&
            right > left * (1.0 + separation)) {
            increment(
                work.filtered_objective_decisions,
                "fixed-width filtered-decision counter overflow");
            return false;
        }
        increment(
            work.exact_objective_fallbacks,
            "fixed-width exact-fallback counter overflow");
        const uint256_t dot_wide = widen(dot);
        const uint256_t best_dot_wide = widen(best_dot);
        return dot_wide * dot_wide * best_norm >
               best_dot_wide * best_dot_wide * norm;
    }

    static bool checked_add_128(NativeUint128 &target, NativeUint128 value) {
        const NativeUint128 maximum = ~NativeUint128(0);
        if (value > maximum - target) {
            return false;
        }
        target += value;
        return true;
    }

    static bool checked_add_64(uint64_t &target, uint64_t value) {
        if (value > std::numeric_limits<uint64_t>::max() - target) {
            return false;
        }
        target += value;
        return true;
    }

    static bool evaluate_code(
        std::span<const uint64_t> magnitudes,
        std::span<const uint32_t> code,
        NativeUint128 &dot,
        uint64_t &norm)
    {
        if (magnitudes.size() != code.size()) {
            throw std::logic_error("fixed-width shell score dimension mismatch");
        }
        dot = 0;
        norm = 0;
        for (size_t coordinate = 0; coordinate < code.size(); ++coordinate) {
            const uint64_t grid = UINT64_C(2) * code[coordinate] + UINT64_C(1);
            if (!checked_add_128(
                    dot,
                    NativeUint128(magnitudes[coordinate]) * grid)) {
                return false;
            }
            if (grid != 0 && grid > std::numeric_limits<uint64_t>::max() / grid) {
                return false;
            }
            if (!checked_add_64(norm, grid * grid)) {
                return false;
            }
        }
        return true;
    }

    static uint64_t tracked_bytes(
        const std::vector<BinaryComponent> &components,
        const std::vector<uint64_t> &magnitudes,
        const std::vector<Event> &events,
        const std::vector<uint32_t> &initial_code,
        const std::vector<uint32_t> &incumbent,
        const std::vector<uint32_t> &current_code)
    {
        const auto bytes = [](size_t count, size_t width) -> uint64_t {
            if (width != 0 && count > std::numeric_limits<uint64_t>::max() / width) {
                throw std::overflow_error("fixed-width shell byte count overflow");
            }
            return static_cast<uint64_t>(count * width);
        };
        uint64_t total = 0;
        const auto add = [&total](uint64_t value) {
            if (value > std::numeric_limits<uint64_t>::max() - total) {
                throw std::overflow_error("fixed-width shell byte sum overflow");
            }
            total += value;
        };
        add(bytes(components.capacity(), sizeof(BinaryComponent)));
        add(bytes(magnitudes.capacity(), sizeof(uint64_t)));
        add(bytes(events.capacity(), sizeof(Event)));
        add(bytes(initial_code.capacity(), sizeof(uint32_t)));
        add(bytes(incumbent.capacity(), sizeof(uint32_t)));
        add(bytes(current_code.capacity(), sizeof(uint32_t)));
        add(4U * sizeof(NativeUint128));
        add(4U * sizeof(uint64_t));
        return total;
    }

  public:
    static FixedWidthOneShellResult repair(
        std::span<const float> magnitudes_input,
        std::span<const uint32_t> incumbent_input,
        uint32_t total_bits)
    {
        if (magnitudes_input.empty()) {
            throw std::invalid_argument("fixed-width shell requires a positive dimension");
        }
        if (magnitudes_input.size() != incumbent_input.size()) {
            throw std::invalid_argument("fixed-width shell input/code dimension mismatch");
        }
        if (total_bits < 1 || total_bits > 16) {
            throw std::invalid_argument("fixed-width shell supports total B in [1,16]");
        }

        const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
        std::vector<uint32_t> incumbent(incumbent_input.begin(), incumbent_input.end());
        for (uint32_t code : incumbent) {
            if (code >= levels) {
                throw std::invalid_argument("fixed-width shell incumbent code is out of range");
            }
        }

        FixedWidthOneShellResult result;
        result.total_bits = total_bits;
        result.magnitude_code = incumbent;
        std::vector<BinaryComponent> components;
        components.reserve(magnitudes_input.size());
        int common_exponent = std::numeric_limits<int>::max();
        size_t nonzero_dimensions = 0;
        for (float value : magnitudes_input) {
            BinaryComponent component = decompose_magnitude(value);
            if (component.mantissa != 0) {
                common_exponent = std::min(common_exponent, component.exponent);
                ++nonzero_dimensions;
            }
            components.push_back(component);
        }
        if (nonzero_dimensions == 0) {
            result.supported = true;
            result.degenerate = true;
            result.work.tracked_transient_bytes =
                static_cast<uint64_t>(incumbent.capacity() * sizeof(uint32_t));
            return result;
        }

        std::vector<uint64_t> magnitudes(magnitudes_input.size(), 0);
        uint32_t maximum_bits = 0;
        for (size_t coordinate = 0; coordinate < components.size(); ++coordinate) {
            if (components[coordinate].mantissa == 0) {
                continue;
            }
            const int shift = components[coordinate].exponent - common_exponent;
            if (shift < 0) {
                throw std::logic_error("invalid fixed-width shell common exponent");
            }
            if (shift > 40) {
                return result;
            }
            const uint64_t magnitude =
                static_cast<uint64_t>(components[coordinate].mantissa) << shift;
            maximum_bits = std::max(maximum_bits, bit_width(magnitude));
            magnitudes[coordinate] = magnitude;
        }
        result.maximum_integer_magnitude_bits = maximum_bits;

        std::vector<uint32_t> initial_code;
        initial_code.reserve(incumbent.size());
        std::vector<Event> events;
        events.reserve(2 * nonzero_dimensions);
        for (size_t coordinate = 0; coordinate < incumbent.size(); ++coordinate) {
            const uint32_t low = incumbent[coordinate] == 0
                                     ? 0
                                     : incumbent[coordinate] - 1U;
            const uint32_t high = incumbent[coordinate] + 1U < levels
                                      ? incumbent[coordinate] + 1U
                                      : incumbent[coordinate];
            initial_code.push_back(low);
            if (magnitudes[coordinate] == 0) {
                continue;
            }
            for (uint32_t target = low + 1U; target <= high; ++target) {
                events.push_back(Event{target, coordinate});
            }
        }
        result.work.events = static_cast<uint64_t>(events.size());
        std::sort(
            events.begin(),
            events.end(),
            [&magnitudes, &result](const Event &lhs, const Event &rhs) {
                increment(
                    result.work.event_sort_comparisons,
                    "fixed-width shell sort counter overflow");
                const NativeUint128 left =
                    NativeUint128(lhs.target_code) * magnitudes[rhs.coordinate];
                const NativeUint128 right =
                    NativeUint128(rhs.target_code) * magnitudes[lhs.coordinate];
                if (left != right) {
                    return left < right;
                }
                if (lhs.coordinate != rhs.coordinate) {
                    return lhs.coordinate < rhs.coordinate;
                }
                return lhs.target_code < rhs.target_code;
            });

        NativeUint128 incumbent_dot = 0;
        uint64_t incumbent_norm = 0;
        NativeUint128 dot = 0;
        uint64_t norm = 0;
        if (!evaluate_code(magnitudes, incumbent, incumbent_dot, incumbent_norm) ||
            !evaluate_code(magnitudes, initial_code, dot, norm)) {
            return result;
        }
        NativeUint128 best_dot = incumbent_dot;
        uint64_t best_norm = incumbent_norm;
        uint64_t best_ordinal = 0;
        bool best_is_shell_path = false;
        if (score_is_better(dot, norm, best_dot, best_norm, result.work)) {
            best_dot = dot;
            best_norm = norm;
            best_is_shell_path = true;
        }

        std::vector<uint32_t> current_code = initial_code;
        uint64_t ordinal = 0;
        for (const Event &event : events) {
            increment(ordinal, "fixed-width shell event ordinal overflow");
            uint32_t &code = current_code[event.coordinate];
            if (event.target_code != code + 1U) {
                throw std::logic_error("invalid fixed-width shell event transition");
            }
            const uint64_t old_grid = UINT64_C(2) * code + UINT64_C(1);
            code = event.target_code;
            if (!checked_add_128(dot, NativeUint128(2) * magnitudes[event.coordinate]) ||
                !checked_add_64(norm, UINT64_C(4) * old_grid + UINT64_C(4))) {
                return result;
            }
            if (score_is_better(dot, norm, best_dot, best_norm, result.work)) {
                best_dot = dot;
                best_norm = norm;
                best_ordinal = ordinal;
                best_is_shell_path = true;
            }
        }

        result.supported = true;
        if (best_is_shell_path) {
            result.improved = true;
            result.magnitude_code = initial_code;
            for (uint64_t index = 0; index < best_ordinal; ++index) {
                const Event &event = events[static_cast<size_t>(index)];
                result.magnitude_code[event.coordinate] = event.target_code;
                increment(result.work.replay_events, "fixed-width shell replay counter overflow");
            }
        }
        result.work.tracked_transient_bytes = tracked_bytes(
            components,
            magnitudes,
            events,
            initial_code,
            incumbent,
            current_code);
        return result;
    }
};

} // namespace saqlib::caq_validation

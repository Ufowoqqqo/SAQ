#pragma once

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <queue>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

namespace saqlib::caq_validation {

using boost::multiprecision::cpp_int;

static_assert(sizeof(float) == sizeof(uint32_t));
static_assert(std::numeric_limits<float>::is_iec559);

// Offline validation infrastructure. The index build and search paths do not
// use this exponential-in-bit-width oracle.
struct ExactEventOracleWork {
    uint64_t first_pass_events = 0;
    uint64_t replay_events = 0;
    uint64_t heap_comparisons = 0;
    uint64_t objective_comparisons = 0;
    size_t max_integer_bits = 0;
};

struct ExactEventOracleResult {
    bool degenerate = false;
    uint32_t total_bits = 0;
    size_t dimension = 0;
    size_t nonzero_dimensions = 0;
    int common_binary_exponent = 0;
    std::vector<uint32_t> magnitude_code;
    std::vector<uint32_t> centered_caq_code;
    uint64_t best_event_ordinal = 0;
    cpp_int score_dot_integer = 0;
    cpp_int score_norm_integer = 0;
    long double cosine = std::numeric_limits<long double>::quiet_NaN();
    long double fac_rescale_unit_grid = std::numeric_limits<long double>::quiet_NaN();
    ExactEventOracleWork work;
};

class ExactEventOracle {
    struct BinaryComponent {
        uint32_t mantissa = 0;
        int exponent = 0;
        bool negative = false;
    };

    struct Event {
        uint32_t level = 0;
        size_t coordinate = 0;
    };

    struct EventLater {
        const std::vector<cpp_int> *magnitudes = nullptr;
        ExactEventOracleWork *work = nullptr;

        bool operator()(const Event &lhs, const Event &rhs) const {
            increment(work->heap_comparisons, "heap comparison counter overflow");
            const cpp_int left = cpp_int(lhs.level) * (*magnitudes)[rhs.coordinate];
            const cpp_int right = cpp_int(rhs.level) * (*magnitudes)[lhs.coordinate];
            update_bits(left, *work);
            update_bits(right, *work);
            if (left != right) {
                return left > right;
            }
            return lhs.coordinate > rhs.coordinate;
        }
    };

    using EventHeap = std::priority_queue<Event, std::vector<Event>, EventLater>;

    static void increment(uint64_t &value, const char *message) {
        if (value == std::numeric_limits<uint64_t>::max()) {
            throw std::overflow_error(message);
        }
        ++value;
    }

    static size_t bit_width(const cpp_int &value) {
        if (value == 0) {
            return 0;
        }
        if (value < 0) {
            throw std::logic_error("bit-width input must be nonnegative");
        }
        return static_cast<size_t>(boost::multiprecision::msb(value)) + 1;
    }

    static void update_bits(const cpp_int &value, ExactEventOracleWork &work) {
        work.max_integer_bits = std::max(work.max_integer_bits, bit_width(value));
    }

    static BinaryComponent decompose(float value) {
        const uint32_t bits = std::bit_cast<uint32_t>(value);
        const uint32_t magnitude = bits & UINT32_C(0x7fffffff);
        const uint32_t exponent_field = (magnitude >> 23U) & UINT32_C(0xff);
        const uint32_t fraction = magnitude & UINT32_C(0x7fffff);

        if (exponent_field == UINT32_C(0xff)) {
            throw std::invalid_argument("exact oracle requires finite binary32 coordinates");
        }

        BinaryComponent component;
        component.negative = magnitude != 0 && (bits >> 31U) != 0;
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

    static EventHeap make_heap(
        const std::vector<cpp_int> &magnitudes,
        uint32_t levels,
        ExactEventOracleWork &work)
    {
        EventHeap heap(EventLater{&magnitudes, &work});
        if (levels == 1) {
            return heap;
        }
        for (size_t i = 0; i < magnitudes.size(); ++i) {
            if (magnitudes[i] != 0) {
                heap.push(Event{1, i});
            }
        }
        return heap;
    }

    static bool score_is_better(
        const cpp_int &dot,
        const cpp_int &norm,
        const cpp_int &best_dot,
        const cpp_int &best_norm,
        ExactEventOracleWork &work)
    {
        increment(work.objective_comparisons, "objective comparison counter overflow");
        const cpp_int dot_squared = dot * dot;
        const cpp_int best_dot_squared = best_dot * best_dot;
        const cpp_int left = dot_squared * best_norm;
        const cpp_int right = best_dot_squared * norm;
        update_bits(dot_squared, work);
        update_bits(best_dot_squared, work);
        update_bits(left, work);
        update_bits(right, work);
        return left > right;
    }

  public:
    static ExactEventOracleResult encode(std::span<const float> input, uint32_t total_bits) {
        if (input.empty()) {
            throw std::invalid_argument("exact oracle requires a positive dimension");
        }
        if (total_bits < 1 || total_bits > 16) {
            throw std::invalid_argument("exact oracle supports total B in [1,16]");
        }

        const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
        std::vector<BinaryComponent> components;
        components.reserve(input.size());
        int common_exponent = std::numeric_limits<int>::max();
        size_t nonzero_dimensions = 0;
        for (float value : input) {
            BinaryComponent component = decompose(value);
            if (component.mantissa != 0) {
                common_exponent = std::min(common_exponent, component.exponent);
                ++nonzero_dimensions;
            }
            components.push_back(component);
        }

        ExactEventOracleResult result;
        result.total_bits = total_bits;
        result.dimension = input.size();
        result.nonzero_dimensions = nonzero_dimensions;
        result.magnitude_code.assign(input.size(), 0);
        result.centered_caq_code.assign(input.size(), levels);

        if (nonzero_dimensions == 0) {
            result.degenerate = true;
            return result;
        }

        result.common_binary_exponent = common_exponent;
        std::vector<cpp_int> magnitudes(input.size(), 0);
        for (size_t i = 0; i < input.size(); ++i) {
            if (components[i].mantissa == 0) {
                continue;
            }
            const int shift = components[i].exponent - common_exponent;
            if (shift < 0) {
                throw std::logic_error("invalid common binary exponent");
            }
            magnitudes[i] = cpp_int(components[i].mantissa) << shift;
            update_bits(magnitudes[i], result.work);
        }

        cpp_int dot = 0;
        for (const cpp_int &magnitude : magnitudes) {
            dot += magnitude;
        }
        cpp_int norm = cpp_int(input.size());
        cpp_int best_dot = dot;
        cpp_int best_norm = norm;
        update_bits(dot, result.work);
        update_bits(norm, result.work);

        std::vector<uint32_t> current_code(input.size(), 0);
        EventHeap heap = make_heap(magnitudes, levels, result.work);
        uint64_t ordinal = 0;
        uint64_t best_ordinal = 0;
        while (!heap.empty()) {
            const Event event = heap.top();
            heap.pop();
            increment(ordinal, "event ordinal overflow");
            increment(result.work.first_pass_events, "first-pass event counter overflow");

            uint32_t &code = current_code[event.coordinate];
            if (event.level != code + 1 || event.level >= levels) {
                throw std::logic_error("invalid complete-event state transition");
            }
            const uint64_t old_grid = UINT64_C(2) * code + 1;
            code = event.level;
            dot += UINT32_C(2) * magnitudes[event.coordinate];
            norm += UINT64_C(4) * old_grid + UINT64_C(4);
            update_bits(dot, result.work);
            update_bits(norm, result.work);

            if (score_is_better(dot, norm, best_dot, best_norm, result.work)) {
                best_dot = dot;
                best_norm = norm;
                best_ordinal = ordinal;
            }
            if (event.level + 1 < levels) {
                heap.push(Event{event.level + 1, event.coordinate});
            }
        }

        current_code.assign(input.size(), 0);
        EventHeap replay = make_heap(magnitudes, levels, result.work);
        for (uint64_t replayed = 0; replayed < best_ordinal; ++replayed) {
            if (replay.empty()) {
                throw std::logic_error("best event ordinal exceeds replay stream");
            }
            const Event event = replay.top();
            replay.pop();
            uint32_t &code = current_code[event.coordinate];
            if (event.level != code + 1 || event.level >= levels) {
                throw std::logic_error("invalid replay state transition");
            }
            code = event.level;
            increment(result.work.replay_events, "replay event counter overflow");
            if (event.level + 1 < levels) {
                replay.push(Event{event.level + 1, event.coordinate});
            }
        }

        result.best_event_ordinal = best_ordinal;
        result.score_dot_integer = std::move(best_dot);
        result.score_norm_integer = std::move(best_norm);
        result.magnitude_code = std::move(current_code);

        long double input_norm_squared = 0;
        long double grid_norm_squared = 0;
        long double input_grid_dot = 0;
        for (size_t i = 0; i < input.size(); ++i) {
            const long double magnitude = std::fabs(static_cast<long double>(input[i]));
            const long double grid = static_cast<long double>(result.magnitude_code[i]) + 0.5L;
            input_norm_squared += magnitude * magnitude;
            grid_norm_squared += grid * grid;
            input_grid_dot += magnitude * grid;
            result.centered_caq_code[i] = components[i].negative
                ? levels - 1U - result.magnitude_code[i]
                : levels + result.magnitude_code[i];
        }

        result.cosine = input_grid_dot /
            std::sqrt(input_norm_squared * grid_norm_squared);
        result.fac_rescale_unit_grid = input_norm_squared / input_grid_dot;
        return result;
    }
};

} // namespace saqlib::caq_validation

#pragma once

#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <time.h>

#include "defines.hpp"
#include "quantization/caq/caq_encoder.hpp"
#include "quantization/caq/caq_estimator.hpp"
#include "quantization/caq/exact_event_oracle.hpp"
#include "quantization/cluster_data.hpp"
#include "quantization/config.h"
#include "quantization/quantizer_data.hpp"
#include "quantization/single_data.hpp"
#include "utils/tools.hpp"

namespace saqlib::caq_validation {

enum class Co0V2Arm {
    lvq_init,
    caq_r6,
    caq_local_fixed_point,
    corrected_exact,
};

inline std::string_view co0_v2_arm_name(Co0V2Arm arm) {
    switch (arm) {
    case Co0V2Arm::lvq_init:
        return "lvq_init";
    case Co0V2Arm::caq_r6:
        return "caq_r6";
    case Co0V2Arm::caq_local_fixed_point:
        return "caq_local_fixed_point";
    case Co0V2Arm::corrected_exact:
        return "corrected_exact";
    }
    throw std::logic_error("unknown CO-0 v2 arm");
}

struct Co0V2AdjustmentTrace {
    std::vector<uint32_t> code;
    double input_norm_squared = 0;
    double decoded_norm_squared = 0;
    double input_decoded_dot = 0;
    double max_abs_coordinate = 0;
    uint64_t accepted_moves = 0;
    uint64_t completed_rounds = 0;
};

struct Co0V2Geometry {
    long double input_norm_squared = 0;
    long double decoded_norm_squared = 0;
    long double input_decoded_dot = 0;
    long double cosine = 0;
    long double cosine_squared = 0;
    long double angular_excess = 0;
    long double fac_rescale = 0;
    long double independent_error_factor = 0;
};

struct Co0V2MemoryAccounting {
    uint64_t input_vector_bytes = 0;
    uint64_t scalar_code_float_bytes = 0;
    uint64_t caq_code_bytes = 0;
    uint64_t result_code_bytes = 0;
    uint64_t oracle_component_bytes = 0;
    uint64_t oracle_integer_object_bytes = 0;
    uint64_t oracle_integer_limb_bytes = 0;
    uint64_t oracle_event_heap_bytes = 0;
    uint64_t canonical_packed_code_bytes = 0;
    uint64_t estimator_packed_bytes = 0;
    uint64_t encoding_phase_bytes = 0;
    uint64_t packing_phase_bytes = 0;
    uint64_t peak_transient_bytes = 0;
};

struct Co0V2EncodingMeasurement {
    Co0V2Arm arm = Co0V2Arm::lvq_init;
    bool zero_segment = false;
    bool code_equal_corrected_exact = false;
    uint32_t total_bits = 0;
    std::vector<uint32_t> code;
    Co0V2Geometry geometry;
    float fac_rescale_float32 = 0;
    float fac_error_float32 = 0;
    uint64_t accepted_moves = 0;
    uint64_t completed_rounds = 0;
    ExactEventOracleWork oracle_work;
    uint64_t wall_time_ns = 0;
    uint64_t cpu_time_ns = 0;
    Co0V2MemoryAccounting memory;
};

struct Co0V2PairMeasurement {
    bool zero_norm_pair = false;
    double stored_norm = 0;
    double query_norm = 0;
    double true_inner_product = 0;
    double estimated_inner_product = 0;
    double signed_ip_error = 0;
    double absolute_ip_error = 0;
    double normalized_absolute_ip_error = 0;
    double true_l2_squared = 0;
    double estimated_l2_squared = 0;
    double absolute_l2_squared_error = 0;
    double bound_radius = 0;
    bool bound_covered = false;
};

namespace detail {

inline void co0_v2_require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

inline uint64_t checked_mul_bytes(size_t count, size_t element_bytes) {
    if (count > std::numeric_limits<uint64_t>::max() / element_bytes) {
        throw std::overflow_error("CO-0 v2 byte count overflow");
    }
    return static_cast<uint64_t>(count * element_bytes);
}

inline uint64_t checked_add_bytes(std::span<const uint64_t> terms) {
    uint64_t total = 0;
    for (uint64_t term : terms) {
        if (term > std::numeric_limits<uint64_t>::max() - total) {
            throw std::overflow_error("CO-0 v2 byte sum overflow");
        }
        total += term;
    }
    return total;
}

inline uint64_t process_cpu_time_ns() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0) {
        throw std::runtime_error("clock_gettime(CLOCK_PROCESS_CPUTIME_ID) failed");
    }
    co0_v2_require(value.tv_sec >= 0 && value.tv_nsec >= 0, "negative CPU timestamp");
    const uint64_t seconds = static_cast<uint64_t>(value.tv_sec);
    co0_v2_require(
        seconds <= (std::numeric_limits<uint64_t>::max() -
                    static_cast<uint64_t>(value.tv_nsec)) /
                       UINT64_C(1000000000),
        "CPU timestamp overflow");
    return seconds * UINT64_C(1000000000) + static_cast<uint64_t>(value.tv_nsec);
}

inline uint64_t elapsed_wall_ns(std::chrono::steady_clock::time_point start) {
    const auto elapsed = std::chrono::steady_clock::now() - start;
    const auto nanoseconds =
        std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count();
    co0_v2_require(nanoseconds >= 0, "negative wall interval");
    return static_cast<uint64_t>(nanoseconds);
}

struct SourceState {
    Eigen::VectorXi code;
    double v_mx = 0;
    double v_mi = 0;
    double delta = 0;
    double input_norm_squared = 0;
    double decoded_norm_squared = 0;
    double input_decoded_dot = 0;
    uint64_t accepted_moves = 0;
    uint64_t completed_rounds = 0;
};

inline SourceState source_scalar_initialization(const FloatVec &input, uint32_t total_bits) {
    co0_v2_require(input.cols() > 0, "CAQ source replica requires positive dimension");
    co0_v2_require(total_bits >= 1 && total_bits <= KMaxQuantizeBits, "invalid CAQ bit width");
    co0_v2_require(input.allFinite(), "CAQ source replica requires finite input");

    SourceState state;
    const size_t dimension = static_cast<size_t>(input.cols());
    const uint32_t code_max = (UINT32_C(1) << total_bits) - 1U;
    state.v_mx = std::max<double>(input.maxCoeff(), -input.minCoeff());
    state.v_mi = -state.v_mx;
    state.delta = (state.v_mx - state.v_mi) / static_cast<double>(code_max + 1U);
    const double vector_sum = input.sum();

    Eigen::VectorXf code_f;
    if (state.delta != 0) {
        code_f = ((input.array() - state.v_mi) / state.delta)
                     .floor()
                     .array()
                     .min(static_cast<float>(code_max));
    } else {
        code_f = Eigen::VectorXf::Zero(static_cast<Eigen::Index>(dimension));
    }

    double input_code_dot = 0;
    uint64_t code_norm_squared = 0;
    state.code.resize(static_cast<Eigen::Index>(dimension));
    for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
        input_code_dot += code_f[static_cast<Eigen::Index>(coordinate)] *
                          input[static_cast<Eigen::Index>(coordinate)];
        const int code = static_cast<int>(code_f[static_cast<Eigen::Index>(coordinate)]);
        state.code[static_cast<Eigen::Index>(coordinate)] = code;
        code_norm_squared += static_cast<uint64_t>(code) * static_cast<uint64_t>(code);
    }
    const uint32_t code_sum = static_cast<uint32_t>(state.code.sum());

    state.input_decoded_dot = input_code_dot * state.delta +
                              (state.v_mi + 0.5 * state.delta) * vector_sum;
    state.decoded_norm_squared = state.delta * state.delta * code_norm_squared +
                                 (state.delta * state.delta + 2 * state.delta * state.v_mi) * code_sum;
    state.decoded_norm_squared +=
        (0.25 * state.delta * state.delta + state.delta * state.v_mi +
         state.v_mi * state.v_mi) *
        dimension;
    state.input_norm_squared = input.squaredNorm();
    return state;
}

inline void source_adjustment(
    const FloatVec &input,
    SourceState &state,
    uint64_t round_limit,
    bool stop_at_local_fixed_point) {
    co0_v2_require(
        (round_limit > 0) != stop_at_local_fixed_point,
        "source adjustment requires either a round limit or local-fixed-point mode");
    if (state.decoded_norm_squared == 0) {
        return;
    }

    const size_t dimension = static_cast<size_t>(input.cols());
    // Scalar initialization can omit the top level. Recover B from delta/range instead.
    const long double levels = state.delta == 0
                                   ? 1
                                   : (state.v_mx - state.v_mi) / state.delta;
    const uint32_t recovered_code_max = static_cast<uint32_t>(std::llround(levels)) - 1U;
    const double re_eps = 1e-8 * state.decoded_norm_squared;

    while (true) {
        if (state.completed_rounds == std::numeric_limits<uint64_t>::max()) {
            throw std::overflow_error("CAQ completed-round counter overflow");
        }
        ++state.completed_rounds;
        uint64_t accepted_this_round = 0;

        for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
            const double original = input[static_cast<Eigen::Index>(coordinate)];
            uint32_t code = static_cast<uint32_t>(
                state.code[static_cast<Eigen::Index>(coordinate)]);
            double decoded = (code + 0.5) * state.delta + state.v_mi;
            const double other_norm = state.decoded_norm_squared - decoded * decoded;
            const double input_step = state.delta * original;

            while (code < recovered_code_max) {
                const double candidate_decoded = decoded + state.delta;
                const double candidate_norm =
                    other_norm + candidate_decoded * candidate_decoded;
                const double candidate_dot = state.input_decoded_dot + input_step;
                if ((state.input_decoded_dot * state.input_decoded_dot + re_eps) *
                        candidate_norm >=
                    candidate_dot * candidate_dot * state.decoded_norm_squared) {
                    break;
                }
                ++code;
                state.input_decoded_dot = candidate_dot;
                decoded = candidate_decoded;
                state.decoded_norm_squared = candidate_norm;
                ++accepted_this_round;
            }

            while (code > 0) {
                const double candidate_decoded = decoded - state.delta;
                const double candidate_norm =
                    other_norm + candidate_decoded * candidate_decoded;
                const double candidate_dot = state.input_decoded_dot - input_step;
                if ((state.input_decoded_dot * state.input_decoded_dot + re_eps) *
                        candidate_norm >=
                    candidate_dot * candidate_dot * state.decoded_norm_squared) {
                    break;
                }
                --code;
                state.input_decoded_dot = candidate_dot;
                decoded = candidate_decoded;
                state.decoded_norm_squared = candidate_norm;
                ++accepted_this_round;
            }
            state.code[static_cast<Eigen::Index>(coordinate)] = static_cast<int>(code);
        }

        if (accepted_this_round > std::numeric_limits<uint64_t>::max() - state.accepted_moves) {
            throw std::overflow_error("CAQ accepted-move counter overflow");
        }
        state.accepted_moves += accepted_this_round;

        if (!stop_at_local_fixed_point && state.completed_rounds >= round_limit) {
            break;
        }

        double corrected_norm = 0;
        double corrected_dot = 0;
        for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
            const double decoded =
                (state.code[static_cast<Eigen::Index>(coordinate)] + 0.5) * state.delta +
                state.v_mi;
            corrected_dot += decoded * input[static_cast<Eigen::Index>(coordinate)];
            corrected_norm += decoded * decoded;
        }
        state.input_decoded_dot = corrected_dot;
        state.decoded_norm_squared = corrected_norm;

        if (accepted_this_round == 0) {
            break;
        }
    }
}

inline Co0V2AdjustmentTrace trace_from_source_state(const SourceState &state) {
    Co0V2AdjustmentTrace trace;
    trace.code.reserve(static_cast<size_t>(state.code.size()));
    for (Eigen::Index coordinate = 0; coordinate < state.code.size(); ++coordinate) {
        co0_v2_require(state.code[coordinate] >= 0, "negative source-replica code");
        trace.code.push_back(static_cast<uint32_t>(state.code[coordinate]));
    }
    trace.input_norm_squared = state.input_norm_squared;
    trace.decoded_norm_squared = state.decoded_norm_squared;
    trace.input_decoded_dot = state.input_decoded_dot;
    trace.max_abs_coordinate = state.v_mx;
    trace.accepted_moves = state.accepted_moves;
    trace.completed_rounds = state.completed_rounds;
    return trace;
}

inline Co0V2AdjustmentTrace source_trace(
    const FloatVec &input,
    uint32_t total_bits,
    Co0V2Arm arm) {
    SourceState state = source_scalar_initialization(input, total_bits);
    if (arm == Co0V2Arm::caq_r6) {
        source_adjustment(input, state, 6, false);
    } else if (arm == Co0V2Arm::caq_local_fixed_point) {
        source_adjustment(input, state, 0, true);
    } else {
        co0_v2_require(arm == Co0V2Arm::lvq_init, "invalid source-trace arm");
    }
    return trace_from_source_state(state);
}

inline bool code_equals(const Eigen::VectorXi &lhs, std::span<const uint32_t> rhs) {
    if (static_cast<size_t>(lhs.size()) != rhs.size()) {
        return false;
    }
    for (size_t coordinate = 0; coordinate < rhs.size(); ++coordinate) {
        if (lhs[static_cast<Eigen::Index>(coordinate)] !=
            static_cast<int>(rhs[coordinate])) {
            return false;
        }
    }
    return true;
}

inline Co0V2Geometry geometry(
    const FloatVec &input,
    std::span<const uint32_t> code,
    uint32_t total_bits) {
    co0_v2_require(static_cast<size_t>(input.cols()) == code.size(), "geometry dimension mismatch");
    co0_v2_require(input.cols() > 1, "geometry requires dimension greater than one");
    const uint32_t levels = UINT32_C(1) << (total_bits - 1U);
    const uint32_t code_max = (UINT32_C(1) << total_bits) - 1U;

    Co0V2Geometry result;
    for (size_t coordinate = 0; coordinate < code.size(); ++coordinate) {
        co0_v2_require(code[coordinate] <= code_max, "code exceeds frozen bit width");
        const long double original = input[static_cast<Eigen::Index>(coordinate)];
        const long double decoded =
            (static_cast<long double>(code[coordinate]) + 0.5L - levels) / levels;
        result.input_norm_squared += original * original;
        result.decoded_norm_squared += decoded * decoded;
        result.input_decoded_dot += original * decoded;
    }

    if (result.input_norm_squared == 0) {
        return result;
    }
    co0_v2_require(result.decoded_norm_squared > 0, "nonzero input has zero decoded norm");
    co0_v2_require(result.input_decoded_dot > 0, "nonzero input has nonpositive decoded dot");
    result.cosine = result.input_decoded_dot /
                    std::sqrt(result.input_norm_squared * result.decoded_norm_squared);
    result.cosine_squared = result.cosine * result.cosine;
    const long double tolerance = 64 * std::numeric_limits<long double>::epsilon();
    if (result.cosine_squared > 1 && result.cosine_squared <= 1 + tolerance) {
        result.cosine_squared = 1;
    }
    co0_v2_require(
        result.cosine_squared > 0 && result.cosine_squared <= 1,
        "invalid centered-grid cosine squared");
    result.angular_excess = 1 / result.cosine_squared - 1;
    if (result.angular_excess < 0 && result.angular_excess >= -tolerance) {
        result.angular_excess = 0;
    }
    co0_v2_require(result.angular_excess >= 0, "negative angular excess");
    result.fac_rescale = result.input_norm_squared / result.input_decoded_dot;
    result.independent_error_factor = result.input_norm_squared * 1.9L *
                                      std::sqrt(result.angular_excess /
                                                static_cast<long double>(input.cols() - 1));
    return result;
}

inline Co0V2MemoryAccounting memory_accounting(
    Co0V2Arm arm,
    size_t dimension,
    uint32_t total_bits,
    const ExactEventOracleWork &oracle_work) {
    Co0V2MemoryAccounting memory;
    memory.input_vector_bytes = checked_mul_bytes(dimension, sizeof(float));
    memory.result_code_bytes = checked_mul_bytes(dimension, sizeof(uint32_t));
    memory.canonical_packed_code_bytes = checked_mul_bytes(dimension, total_bits) / 8;
    memory.estimator_packed_bytes =
        checked_mul_bytes(dimension, total_bits) / 8 +
        2 * sizeof(float) + sizeof(ExFactor);

    if (arm == Co0V2Arm::corrected_exact) {
        memory.oracle_component_bytes = checked_mul_bytes(
            dimension,
            ExactEventOracle::component_storage_bytes_per_dimension());
        memory.oracle_integer_object_bytes = checked_mul_bytes(
            dimension + 8,
            ExactEventOracle::integer_object_bytes());
        memory.oracle_integer_limb_bytes = oracle_work.peak_live_cpp_int_limb_bytes;
        memory.oracle_event_heap_bytes = checked_mul_bytes(
            oracle_work.peak_event_heap_capacity,
            ExactEventOracle::event_storage_bytes());
        const uint64_t terms[] = {
            memory.input_vector_bytes,
            memory.result_code_bytes * 3,
            memory.oracle_component_bytes,
            memory.oracle_integer_object_bytes,
            memory.oracle_integer_limb_bytes,
            memory.oracle_event_heap_bytes,
        };
        memory.encoding_phase_bytes = checked_add_bytes(terms);
    } else {
        memory.scalar_code_float_bytes = checked_mul_bytes(dimension, sizeof(float));
        memory.caq_code_bytes = checked_mul_bytes(dimension, sizeof(int));
        const uint64_t terms[] = {
            memory.input_vector_bytes,
            memory.scalar_code_float_bytes,
            memory.caq_code_bytes,
            memory.result_code_bytes,
        };
        memory.encoding_phase_bytes = checked_add_bytes(terms);
    }

    const uint64_t packing_terms[] = {
        memory.input_vector_bytes,
        memory.result_code_bytes,
        memory.canonical_packed_code_bytes,
        memory.estimator_packed_bytes,
    };
    memory.packing_phase_bytes = checked_add_bytes(packing_terms);
    memory.peak_transient_bytes =
        std::max(memory.encoding_phase_bytes, memory.packing_phase_bytes);
    return memory;
}

inline std::vector<uint32_t> production_code(const QuantBaseCode &base_code) {
    std::vector<uint32_t> code;
    code.reserve(static_cast<size_t>(base_code.code.size()));
    for (Eigen::Index coordinate = 0; coordinate < base_code.code.size(); ++coordinate) {
        co0_v2_require(base_code.code[coordinate] >= 0, "negative production CAQ code");
        code.push_back(static_cast<uint32_t>(base_code.code[coordinate]));
    }
    return code;
}

inline void pack_short_codes(
    std::span<const uint32_t> code,
    uint32_t total_bits,
    uint8_t *output) {
    co0_v2_require(code.size() % 64 == 0, "short-code dimension must be a multiple of 64");
    co0_v2_require(output != nullptr, "short-code output is null");
    const size_t bytes = code.size() / 8;
    const uint32_t short_bit = UINT32_C(1) << (total_bits - 1U);
    for (size_t byte_index = 0; byte_index < bytes; ++byte_index) {
        uint8_t byte = 0;
        const size_t base = byte_index * 8;
        for (size_t bit = 0; bit < 8; ++bit) {
            if ((code[base + bit] & short_bit) != 0) {
                byte |= static_cast<uint8_t>(UINT8_C(0x80) >> bit);
            }
        }
        const size_t covered = byte_index + 7 - 2 * (byte_index % 8);
        output[covered] = byte;
    }
}

inline void pack_long_codes(
    std::span<const uint32_t> code,
    uint32_t total_bits,
    uint8_t *output) {
    co0_v2_require(total_bits > 1, "long-code packing requires B>1");
    co0_v2_require(output != nullptr, "long-code output is null");
    const uint32_t short_bit = UINT32_C(1) << (total_bits - 1U);
    Uint16Vec lower;
    lower.resize(static_cast<Eigen::Index>(code.size()));
    for (size_t coordinate = 0; coordinate < code.size(); ++coordinate) {
        lower[static_cast<Eigen::Index>(coordinate)] =
            static_cast<uint16_t>(code[coordinate] & (short_bit - 1U));
    }
    const auto compact = utils::get_compacted_code16_func(total_bits - 1U);
    compact(output, &lower(0, 0), code.size());
}

inline void pack_for_current_estimator(
    const Co0V2EncodingMeasurement &measurement,
    CaqSingleDataWrapper &packed) {
    co0_v2_require(
        packed.num_dim_padded() == measurement.code.size(),
        "estimator pack dimension mismatch");
    co0_v2_require(
        packed.num_bits() == measurement.total_bits,
        "estimator pack bit-width mismatch");
    packed.factor_o_l2norm() = static_cast<float>(
        std::sqrt(measurement.geometry.input_norm_squared));
    packed.factor_ip_cent_oa() = 0;
    packed.long_factor().rescale = measurement.fac_rescale_float32;
    packed.long_factor().error = measurement.fac_error_float32;
    pack_short_codes(measurement.code, measurement.total_bits, packed.short_code());
    if (measurement.total_bits > 1) {
        pack_long_codes(measurement.code, measurement.total_bits, packed.long_code());
    }
}

} // namespace detail

inline Co0V2AdjustmentTrace co0_v2_source_trace(
    const FloatVec &input,
    uint32_t total_bits,
    Co0V2Arm arm) {
    return detail::source_trace(input, total_bits, arm);
}

inline Co0V2EncodingMeasurement co0_v2_measure_arm(
    const FloatVec &input,
    uint32_t total_bits,
    Co0V2Arm arm) {
    detail::co0_v2_require(input.cols() > 1, "CO-0 v2 encoding requires D>1");
    detail::co0_v2_require(
        static_cast<size_t>(input.cols()) % kDimPaddingSize == 0,
        "CO-0 v2 encoding requires a multiple-of-64 dimension");
    detail::co0_v2_require(input.allFinite(), "CO-0 v2 encoding requires finite input");
    detail::co0_v2_require(
        total_bits >= 1 && total_bits <= KMaxQuantizeBits,
        "CO-0 v2 encoding bit width is out of range");

    Co0V2EncodingMeasurement result;
    result.arm = arm;
    result.total_bits = total_bits;
    result.zero_segment = input.squaredNorm() == 0;

    if (arm == Co0V2Arm::lvq_init || arm == Co0V2Arm::caq_r6) {
        QuantSingleConfig config;
        config.random_rotation = false;
        config.use_fastscan = false;
        config.caq_adj_rd_lmt = arm == Co0V2Arm::caq_r6 ? 6 : 0;
        config.caq_adj_eps = 1e-8F;

        QuantBaseCode base_code;
        const uint64_t cpu_start = detail::process_cpu_time_ns();
        const auto wall_start = std::chrono::steady_clock::now();
        if (result.zero_segment) {
            base_code.code = Eigen::VectorXi::Zero(input.cols());
            base_code.o_l2norm = 0;
            base_code.fac_rescale = 0;
            base_code.fac_error = 0;
        } else {
            CAQEncoder encoder(static_cast<size_t>(input.cols()), total_bits, config);
            encoder.encode_and_fac(input, base_code, nullptr);
        }
        result.wall_time_ns = detail::elapsed_wall_ns(wall_start);
        const uint64_t cpu_end = detail::process_cpu_time_ns();
        detail::co0_v2_require(cpu_end >= cpu_start, "negative encoder CPU interval");
        result.cpu_time_ns = cpu_end - cpu_start;

        const Co0V2AdjustmentTrace trace = detail::source_trace(input, total_bits, arm);
        detail::co0_v2_require(
            detail::code_equals(base_code.code, trace.code),
            "source-aligned instrumentation diverged from production CAQEncoder");
        result.code = detail::production_code(base_code);
        result.fac_rescale_float32 = base_code.fac_rescale;
        result.fac_error_float32 = base_code.fac_error;
        result.accepted_moves = trace.accepted_moves;
        result.completed_rounds = trace.completed_rounds;
    } else if (arm == Co0V2Arm::caq_local_fixed_point) {
        const uint64_t cpu_start = detail::process_cpu_time_ns();
        const auto wall_start = std::chrono::steady_clock::now();
        const Co0V2AdjustmentTrace trace = detail::source_trace(input, total_bits, arm);
        result.wall_time_ns = detail::elapsed_wall_ns(wall_start);
        const uint64_t cpu_end = detail::process_cpu_time_ns();
        detail::co0_v2_require(cpu_end >= cpu_start, "negative local CAQ CPU interval");
        result.cpu_time_ns = cpu_end - cpu_start;
        result.code = trace.code;
        result.accepted_moves = trace.accepted_moves;
        result.completed_rounds = trace.completed_rounds;
    } else {
        detail::co0_v2_require(
            arm == Co0V2Arm::corrected_exact,
            "invalid CO-0 v2 arm");
        const uint64_t cpu_start = detail::process_cpu_time_ns();
        const auto wall_start = std::chrono::steady_clock::now();
        ExactEventOracleResult exact = ExactEventOracle::encode(
            std::span<const float>(input.data(), static_cast<size_t>(input.cols())),
            total_bits);
        result.wall_time_ns = detail::elapsed_wall_ns(wall_start);
        const uint64_t cpu_end = detail::process_cpu_time_ns();
        detail::co0_v2_require(cpu_end >= cpu_start, "negative exact-oracle CPU interval");
        result.cpu_time_ns = cpu_end - cpu_start;
        detail::co0_v2_require(
            exact.degenerate == result.zero_segment,
            "exact-oracle zero-state mismatch");
        result.code = std::move(exact.centered_caq_code);
        result.oracle_work = exact.work;
    }

    result.geometry = detail::geometry(input, result.code, total_bits);
    if (arm == Co0V2Arm::caq_local_fixed_point ||
        arm == Co0V2Arm::corrected_exact) {
        result.fac_rescale_float32 = static_cast<float>(result.geometry.fac_rescale);
        result.fac_error_float32 = static_cast<float>(
            result.geometry.independent_error_factor);
    }
    if (result.zero_segment) {
        result.fac_rescale_float32 = 0;
        result.fac_error_float32 = 0;
    }

    detail::co0_v2_require(
        std::isfinite(result.fac_rescale_float32) &&
            std::isfinite(result.fac_error_float32),
        "CO-0 v2 factor is non-finite");
    result.memory = detail::memory_accounting(
        arm,
        static_cast<size_t>(input.cols()),
        total_bits,
        result.oracle_work);
    return result;
}

inline std::vector<Co0V2EncodingMeasurement> co0_v2_measure_all_arms(
    const FloatVec &input,
    uint32_t total_bits) {
    const Co0V2Arm arms[] = {
        Co0V2Arm::lvq_init,
        Co0V2Arm::caq_r6,
        Co0V2Arm::caq_local_fixed_point,
        Co0V2Arm::corrected_exact,
    };
    std::vector<Co0V2EncodingMeasurement> results;
    results.reserve(std::size(arms));
    for (Co0V2Arm arm : arms) {
        results.push_back(co0_v2_measure_arm(input, total_bits, arm));
    }
    const std::vector<uint32_t> &exact_code = results.back().code;
    for (Co0V2EncodingMeasurement &result : results) {
        result.code_equal_corrected_exact = result.code == exact_code;
    }
    return results;
}

inline std::vector<uint8_t> co0_v2_pack_canonical_code(
    std::span<const uint32_t> code,
    uint32_t total_bits) {
    detail::co0_v2_require(total_bits >= 1 && total_bits <= 16, "invalid packed-code width");
    const uint64_t bit_count = static_cast<uint64_t>(code.size()) * total_bits;
    detail::co0_v2_require(bit_count % 8 == 0, "packed-code row is not byte aligned");
    std::vector<uint8_t> packed(static_cast<size_t>(bit_count / 8), 0);
    uint64_t bit_offset = 0;
    const uint32_t code_max = (UINT32_C(1) << total_bits) - 1U;
    for (uint32_t value : code) {
        detail::co0_v2_require(value <= code_max, "packed code exceeds bit width");
        for (uint32_t bit = 0; bit < total_bits; ++bit, ++bit_offset) {
            if ((value & (UINT32_C(1) << bit)) != 0) {
                packed[static_cast<size_t>(bit_offset / 8)] |=
                    static_cast<uint8_t>(UINT8_C(1) << (bit_offset % 8));
            }
        }
    }
    return packed;
}

inline std::vector<uint32_t> co0_v2_unpack_canonical_code(
    std::span<const uint8_t> packed,
    size_t dimension,
    uint32_t total_bits) {
    detail::co0_v2_require(
        static_cast<uint64_t>(dimension) * total_bits ==
            static_cast<uint64_t>(packed.size()) * 8,
        "canonical code payload length mismatch");
    std::vector<uint32_t> code(dimension, 0);
    uint64_t bit_offset = 0;
    for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
        for (uint32_t bit = 0; bit < total_bits; ++bit, ++bit_offset) {
            if ((packed[static_cast<size_t>(bit_offset / 8)] &
                 static_cast<uint8_t>(UINT8_C(1) << (bit_offset % 8))) != 0) {
                code[coordinate] |= UINT32_C(1) << bit;
            }
        }
    }
    return code;
}

inline void co0_v2_pack_for_current_estimator(
    const Co0V2EncodingMeasurement &measurement,
    CaqSingleDataWrapper &packed) {
    detail::pack_for_current_estimator(measurement, packed);
}

inline std::vector<Co0V2PairMeasurement> co0_v2_measure_pairs(
    const FloatVec &stored,
    const FloatVec &query,
    std::span<const Co0V2EncodingMeasurement> measurements) {
    detail::co0_v2_require(!measurements.empty(), "pair measurement arm set is empty");
    detail::co0_v2_require(stored.cols() == query.cols(), "pair dimension mismatch");
    detail::co0_v2_require(stored.allFinite() && query.allFinite(), "pair input is non-finite");
    for (const Co0V2EncodingMeasurement &measurement : measurements) {
        detail::co0_v2_require(
            static_cast<size_t>(stored.cols()) == measurement.code.size(),
            "pair/code dimension mismatch");
        detail::co0_v2_require(
            measurement.total_bits == measurements.front().total_bits,
            "pair arms use different bit widths");
    }

    Co0V2PairMeasurement reference;
    long double stored_norm_squared = 0;
    long double query_norm_squared = 0;
    long double true_ip = 0;
    long double true_l2 = 0;
    for (Eigen::Index coordinate = 0; coordinate < stored.cols(); ++coordinate) {
        const long double stored_value = stored[coordinate];
        const long double query_value = query[coordinate];
        stored_norm_squared += stored_value * stored_value;
        query_norm_squared += query_value * query_value;
        true_ip += stored_value * query_value;
        const long double difference = stored_value - query_value;
        true_l2 += difference * difference;
    }
    reference.stored_norm = static_cast<double>(std::sqrt(stored_norm_squared));
    reference.query_norm = static_cast<double>(std::sqrt(query_norm_squared));
    reference.zero_norm_pair = stored_norm_squared == 0 || query_norm_squared == 0;
    reference.true_inner_product = static_cast<double>(true_ip);
    reference.true_l2_squared = static_cast<double>(true_l2);
    std::vector<Co0V2PairMeasurement> results(measurements.size(), reference);
    if (reference.zero_norm_pair) {
        return results;
    }

    CaqSingleDataWrapper packed(
        static_cast<size_t>(stored.cols()),
        measurements.front().total_bits);
    packed.allocate_data();

    BaseQuantizerData estimator_data;
    estimator_data.num_dim_pad = static_cast<size_t>(stored.cols());
    estimator_data.num_bits = measurements.front().total_bits;
    estimator_data.cfg.random_rotation = false;
    estimator_data.cfg.use_fastscan = false;
    estimator_data.rotator.reset();
    SearcherConfig searcher;
    searcher.dist_type = DistType::IP;
    CaqSingleEstimator<DistType::IP> estimator(estimator_data, searcher, query);
    for (size_t arm_index = 0; arm_index < measurements.size(); ++arm_index) {
        const Co0V2EncodingMeasurement &measurement = measurements[arm_index];
        Co0V2PairMeasurement &result = results[arm_index];
        detail::pack_for_current_estimator(measurement, packed);
        result.estimated_inner_product = estimator.compAccurateDist(packed);
        result.signed_ip_error = result.estimated_inner_product - result.true_inner_product;
        result.absolute_ip_error = std::abs(result.signed_ip_error);
        result.normalized_absolute_ip_error = result.absolute_ip_error /
                                              (result.stored_norm * result.query_norm);
        result.estimated_l2_squared =
            result.stored_norm * result.stored_norm +
            result.query_norm * result.query_norm -
            2 * result.estimated_inner_product;
        result.absolute_l2_squared_error =
            std::abs(result.estimated_l2_squared - result.true_l2_squared);
        result.bound_radius = measurement.fac_error_float32 *
                              result.query_norm / result.stored_norm;
        result.bound_covered = result.absolute_ip_error <= result.bound_radius;

        detail::co0_v2_require(
            std::isfinite(result.estimated_inner_product) &&
                std::isfinite(result.normalized_absolute_ip_error) &&
                std::isfinite(result.absolute_l2_squared_error) &&
                std::isfinite(result.bound_radius),
            "pair metric is non-finite");
    }
    return results;
}

inline Co0V2PairMeasurement co0_v2_measure_pair(
    const FloatVec &stored,
    const FloatVec &query,
    const Co0V2EncodingMeasurement &measurement) {
    return co0_v2_measure_pairs(
               stored,
               query,
               std::span<const Co0V2EncodingMeasurement>(&measurement, 1))
        .front();
}

} // namespace saqlib::caq_validation

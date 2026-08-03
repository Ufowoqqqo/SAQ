#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <span>

namespace saq_component_oracle {

inline std::uint64_t splitmix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

inline double least_squares_scale(
        std::span<const float> residual,
        std::span<const float> direction) {
    double inner_product = 0;
    double direction_norm = 0;
    for (std::size_t index = 0; index < residual.size(); ++index) {
        inner_product += static_cast<double>(residual[index]) *
                direction[index];
        direction_norm += static_cast<double>(direction[index]) *
                direction[index];
    }
    return direction_norm == 0 ? 0 : inner_product / direction_norm;
}

inline bool rank_before(
        double left_distance, std::uint32_t left_id,
        double right_distance, std::uint32_t right_id) {
    return left_distance != right_distance
            ? left_distance < right_distance
            : left_id < right_id;
}

inline bool exact_tie(double left, double right) {
    return std::abs(left - right) <=
            1e-9 * std::max({1.0, std::abs(left), std::abs(right)});
}

inline bool is_inversion(
        double exact_left, double exact_right,
        double arm_left, double arm_right,
        std::uint32_t left_id, std::uint32_t right_id) {
    return rank_before(exact_left, left_id, exact_right, right_id) !=
            rank_before(arm_left, left_id, arm_right, right_id);
}

}  // namespace saq_component_oracle

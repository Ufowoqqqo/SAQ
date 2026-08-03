#pragma once

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

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

inline const std::vector<std::uint8_t>& joint_subset_masks() {
    static const std::vector<std::uint8_t> masks = [] {
        std::vector<std::uint8_t> result{0};
        for (int cardinality = 2; cardinality <= 4; ++cardinality) {
            for (std::uint8_t mask = 1; mask < 31; ++mask) {
                if (std::popcount(static_cast<unsigned>(mask)) == cardinality)
                    result.push_back(mask);
            }
        }
        result.push_back(31);
        return result;
    }();
    return masks;
}

inline std::string joint_subset_name(std::uint8_t mask) {
    if (mask == 0) return "PROD";
    if (mask == 31) return "EXACT_ALL";
    std::string name = "EXACT_SEGS";
    for (unsigned segment = 0; segment < 5; ++segment) {
        if ((mask & (1U << segment)) != 0)
            name += "_" + std::to_string(segment);
    }
    return name;
}

inline std::string joint_decision(unsigned minimum_passing_cardinality) {
    if (minimum_passing_cardinality == 2) return "PAIR_ACTIONABLE";
    if (minimum_passing_cardinality == 3 ||
        minimum_passing_cardinality == 4)
        return "CLOSE_DIFFUSE_THREE_PLUS";
    return "CLOSE_NO_SMALL_JOINT";
}

}  // namespace saq_component_oracle

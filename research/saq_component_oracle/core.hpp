#pragma once

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace saq_component_oracle {

struct ObjectiveChoice {
    std::size_t left = 0;
    std::size_t right = 0;
    double loss = 0;
};
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
inline ObjectiveChoice independent_objective_choice(
        std::span<const double> left, std::size_t left_count,
        std::span<const double> right, std::size_t right_count,
        std::size_t samples) {
    if (samples == 0 || left.size() != left_count * samples ||
        right.size() != right_count * samples)
        throw std::invalid_argument("invalid objective projection shape");
    ObjectiveChoice result;
    double best_left = std::numeric_limits<double>::infinity();
    double best_right = std::numeric_limits<double>::infinity();
    for (std::size_t alternative = 0; alternative < left_count; ++alternative) {
        double loss = 0;
        for (std::size_t sample = 0; sample < samples; ++sample) {
            const double value = left[alternative * samples + sample];
            loss += value * value;
        }
        if (loss < best_left) {
            best_left = loss;
            result.left = alternative;
        }
    }
    for (std::size_t alternative = 0; alternative < right_count; ++alternative) {
        double loss = 0;
        for (std::size_t sample = 0; sample < samples; ++sample) {
            const double value = right[alternative * samples + sample];
            loss += value * value;
        }
        if (loss < best_right) {
            best_right = loss;
            result.right = alternative;
        }
    }
    result.loss = best_left + best_right;
    return result;
}
inline ObjectiveChoice joint_objective_choice(
        std::span<const double> left, std::size_t left_count,
        std::span<const double> right, std::size_t right_count,
        std::size_t samples) {
    if (samples == 0 || left.size() != left_count * samples ||
        right.size() != right_count * samples)
        throw std::invalid_argument("invalid objective projection shape");
    ObjectiveChoice result;
    result.loss = std::numeric_limits<double>::infinity();
    for (std::size_t left_index = 0; left_index < left_count; ++left_index) {
        for (std::size_t right_index = 0; right_index < right_count; ++right_index) {
            double loss = 0;
            for (std::size_t sample = 0; sample < samples; ++sample) {
                const double value = left[left_index * samples + sample] +
                        right[right_index * samples + sample];
                loss += value * value;
            }
            if (loss < result.loss) {
                result = {left_index, right_index, loss};
            }
        }
    }
    return result;
}

inline double combined_objective_loss(
        std::span<const double> left, std::size_t left_index,
        std::span<const double> right, std::size_t right_index,
        std::size_t samples) {
    if (samples == 0 || left.size() % samples != 0 ||
        right.size() % samples != 0 ||
        left_index >= left.size() / samples ||
        right_index >= right.size() / samples)
        throw std::invalid_argument("invalid selected projection shape");
    double loss = 0;
    for (std::size_t sample = 0; sample < samples; ++sample) {
        const double value = left[left_index * samples + sample] +
                right[right_index * samples + sample];
        loss += value * value;
    }
    return loss;
}

}  // namespace saq_component_oracle

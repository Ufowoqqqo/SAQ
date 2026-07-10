#pragma once

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <random>
#include <string_view>
#include <vector>

#include <glog/logging.h>

#include "defines.hpp"

namespace saqlib::baseline {

struct SymphonyQGScalarQuery {
    FloatVec rotated;
    std::vector<uint8_t> codes;
    float lower = 0.0f;
    float upper = 0.0f;
    float width = 0.0f;
    int32_t code_sum = 0;
};

struct SymphonyQGScalarNeighbor {
    std::vector<uint8_t> residual_positive;
    float triple_x = 0.0f;
    float factor_dq = 0.0f;
    float factor_vq = 0.0f;
    bool zero_residual = false;
};

class SymphonyQGScalarEstimator {
  public:
    static constexpr std::string_view kSourceRevision =
        "6124ddb34ee4d176edea1bd7ad38d1672343df28";
    static constexpr int kQueryBits = 6;
    static constexpr size_t kMinPaddedDimension = 64;
    static constexpr size_t kMaxPaddedDimension = 2048;

  private:
    size_t dimension_ = 0;
    size_t padded_dimension_ = 0;
    uint64_t rotation_seed_ = 0;
    std::vector<int8_t> signs_;

    static size_t paddedDimension(size_t dimension) {
        CHECK_GT(dimension, 0);
        const size_t padded = std::bit_ceil(dimension);
        CHECK_GE(padded, kMinPaddedDimension);
        CHECK_LE(padded, kMaxPaddedDimension);
        return padded;
    }

    static void hadamardInPlace(float *values, size_t size) {
        CHECK(std::has_single_bit(size));
        for (size_t half = 1; half < size; half <<= 1) {
            const size_t block = half << 1;
            for (size_t begin = 0; begin < size; begin += block) {
                for (size_t offset = 0; offset < half; ++offset) {
                    const float left = values[begin + offset];
                    const float right = values[begin + half + offset];
                    values[begin + offset] = left + right;
                    values[begin + half + offset] = left - right;
                }
            }
        }
    }

  public:
    SymphonyQGScalarEstimator(size_t dimension, uint64_t rotation_seed)
        : dimension_(dimension),
          padded_dimension_(paddedDimension(dimension)),
          rotation_seed_(rotation_seed),
          signs_(padded_dimension_) {
        std::mt19937_64 generator(rotation_seed_);
        std::uniform_int_distribution<int> bernoulli(0, 1);
        for (auto &sign : signs_) {
            sign = static_cast<int8_t>((2 * bernoulli(generator)) - 1);
        }
    }

    size_t dimension() const { return dimension_; }
    size_t padded_dimension() const { return padded_dimension_; }
    uint64_t rotation_seed() const { return rotation_seed_; }
    const std::vector<int8_t> &signs() const { return signs_; }

    void rotate(const float *source, FloatVec &rotated) const {
        CHECK(source);
        rotated = FloatVec::Zero(padded_dimension_);
        const float scale = 1.0f / std::sqrt(static_cast<float>(padded_dimension_));
        for (size_t dim = 0; dim < dimension_; ++dim) {
            rotated[dim] = source[dim] * static_cast<float>(signs_[dim]) * scale;
        }
        hadamardInPlace(rotated.data(), padded_dimension_);
    }

    SymphonyQGScalarQuery prepareQuery(const float *query) const {
        SymphonyQGScalarQuery prepared;
        rotate(query, prepared.rotated);
        prepared.codes.resize(padded_dimension_);

        prepared.lower = 0.0f;
        prepared.upper = 0.0f;
        for (size_t dim = 0; dim < padded_dimension_; ++dim) {
            prepared.lower = std::min(prepared.lower, prepared.rotated[dim]);
            prepared.upper = std::max(prepared.upper, prepared.rotated[dim]);
        }
        prepared.width =
            (prepared.upper - prepared.lower) / static_cast<float>((1 << kQueryBits) - 1);
        CHECK_GT(prepared.width, 0.0f) << "SymphonyQG query quantization requires a nonzero range";

        const float inverse_width = 1.0f / prepared.width;
        for (size_t dim = 0; dim < padded_dimension_; ++dim) {
            const long code = std::lround(
                ((prepared.rotated[dim] - prepared.lower) * inverse_width) + 0.5f);
            CHECK_GE(code, 0);
            CHECK_LE(code, std::numeric_limits<uint8_t>::max());
            prepared.codes[dim] = static_cast<uint8_t>(code);
            prepared.code_sum += static_cast<int32_t>(prepared.codes[dim]);
        }
        return prepared;
    }

    void encodeNeighbor(const float *rotated_current, const float *rotated_neighbor,
                        SymphonyQGScalarNeighbor &encoded) const {
        CHECK(rotated_current);
        CHECK(rotated_neighbor);
        encoded.residual_positive.resize(padded_dimension_);
        encoded.triple_x = 0.0f;
        encoded.factor_dq = 0.0f;
        encoded.factor_vq = 0.0f;
        encoded.zero_residual = false;

        Eigen::Map<const FloatVec> current(rotated_current, padded_dimension_);
        Eigen::Map<const FloatVec> neighbor(rotated_neighbor, padded_dimension_);
        const FloatVec residual = neighbor - current;
        FloatVec signed_residual = FloatVec::Zero(padded_dimension_);
        int32_t sign_sum = 0;
        for (size_t dim = 0; dim < padded_dimension_; ++dim) {
            const bool positive = residual[dim] > 0.0f;
            encoded.residual_positive[dim] = static_cast<uint8_t>(positive);
            signed_residual[dim] = positive ? 1.0f : -1.0f;
            sign_sum += positive ? 1 : -1;
        }

        const float factor_normalization =
            1.0f / std::sqrt(static_cast<float>(padded_dimension_));
        const float residual_norm = residual.norm();
        if (residual_norm == 0.0f) {
            encoded.zero_residual = true;
            return;
        }
        const float factor_x0 =
            (residual.array() * signed_residual.array() * factor_normalization).sum() /
            residual_norm;
        CHECK_NE(factor_x0, 0.0f);
        const float factor_x1 =
            static_cast<float>((current.array() * signed_residual.array()).sum() *
                               factor_normalization);

        const double current_norm = residual_norm;
        const double current_x0 = factor_x0;
        const double current_x1 = factor_x1;
        const long double norm_over_x0 =
            static_cast<long double>(current_norm) / current_x0;
        encoded.triple_x = static_cast<float>(
            (current_norm * current_norm) + (2.0L * norm_over_x0 * current_x1));
        encoded.factor_dq = static_cast<float>(
            -2.0L * norm_over_x0 * factor_normalization);
        encoded.factor_vq = static_cast<float>(
            -2.0L * norm_over_x0 * factor_normalization * sign_sum);
    }

    int32_t signedQueryCodeDot(const SymphonyQGScalarQuery &query,
                               const SymphonyQGScalarNeighbor &neighbor) const {
        CHECK_EQ(query.codes.size(), padded_dimension_);
        CHECK_EQ(neighbor.residual_positive.size(), padded_dimension_);
        int32_t dot = 0;
        for (size_t dim = 0; dim < padded_dimension_; ++dim) {
            const int32_t code = static_cast<int32_t>(query.codes[dim]);
            dot += neighbor.residual_positive[dim] != 0 ? code : -code;
        }
        return dot;
    }

    float estimate(const SymphonyQGScalarQuery &query, float current_distance,
                   const SymphonyQGScalarNeighbor &neighbor) const {
        if (neighbor.zero_residual) {
            return current_distance;
        }
        const float signed_dot =
            static_cast<float>(signedQueryCodeDot(query, neighbor));
        const float base = current_distance + neighbor.triple_x;
        const float query_value_term =
            std::fma(neighbor.factor_vq, query.lower, base);
        const float query_code_term =
            (neighbor.factor_dq * query.width) * signed_dot;
        return query_code_term + query_value_term;
    }
};

} // namespace saqlib::baseline

#pragma once

#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "defines.hpp"

namespace saqlib::caq_validation {

inline FloatRowMat co0_v2_production_rotation(size_t dimension) {
    if (dimension == 0) {
        throw std::invalid_argument("CO-0 v2 rotation requires positive dimension");
    }
    FloatRowMat random(FloatRowMat::Random(
        static_cast<Eigen::Index>(dimension),
        static_cast<Eigen::Index>(dimension)));
    Eigen::HouseholderQR<FloatRowMat> qr(random);
    FloatRowMat q = qr.householderQ();
    FloatRowMat rotation = q.transpose();
    if (!rotation.allFinite()) {
        throw std::runtime_error("CO-0 v2 rotation contains a non-finite value");
    }
    return rotation;
}

inline std::vector<FloatRowMat> co0_v2_segmented_rotations(
    const std::vector<size_t> &dimensions,
    int logical_seed) {
    if (logical_seed < 0 || logical_seed > 2) {
        throw std::invalid_argument("CO-0 v2 logical seed must be in [0,2]");
    }
    std::srand(static_cast<unsigned int>(logical_seed) + 1U);
    std::vector<FloatRowMat> rotations;
    rotations.reserve(dimensions.size());
    for (size_t dimension : dimensions) {
        rotations.push_back(co0_v2_production_rotation(dimension));
    }
    return rotations;
}

inline FloatRowMat co0_v2_whole_rotation(size_t dimension, int logical_seed) {
    if (logical_seed < 0 || logical_seed > 2) {
        throw std::invalid_argument("CO-0 v2 logical seed must be in [0,2]");
    }
    std::srand(static_cast<unsigned int>(logical_seed) + 1U);
    return co0_v2_production_rotation(dimension);
}

} // namespace saqlib::caq_validation

#pragma once

#include <cstddef>
#include <span>
#include <vector>

namespace saqlib::caq_validation {

void co0_v2_frozen_segmented_rotation_values(
    const std::vector<size_t> &dimensions,
    int logical_seed,
    const std::vector<std::span<float>> &row_major_outputs);

void co0_v2_frozen_whole_rotation_values(
    size_t dimension,
    int logical_seed,
    std::span<float> row_major_output);

} // namespace saqlib::caq_validation

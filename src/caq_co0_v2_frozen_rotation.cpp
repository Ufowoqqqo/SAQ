#include <algorithm>
#include <cstddef>
#include <span>
#include <stdexcept>
#include <vector>

#include "quantization/caq/co0_v2_frozen_rotation.hpp"
#include "quantization/caq/co0_v2_rotation.hpp"

#if defined(__AVX__) || defined(__AVX2__) || defined(__AVX512F__) || defined(__FMA__)
#error "CO-0 v2 frozen rotations must use the preregistered non-AVX build path"
#endif

namespace saqlib::caq_validation {
namespace {

void copy_row_major(const FloatRowMat &rotation, std::span<float> output) {
    const size_t value_count = static_cast<size_t>(rotation.size());
    if (output.size() != value_count) {
        throw std::invalid_argument("CO-0 v2 frozen rotation output size mismatch");
    }
    std::copy_n(rotation.data(), value_count, output.data());
}

} // namespace

void co0_v2_frozen_segmented_rotation_values(
    const std::vector<size_t> &dimensions,
    int logical_seed,
    const std::vector<std::span<float>> &row_major_outputs) {
    if (row_major_outputs.size() != dimensions.size()) {
        throw std::invalid_argument("CO-0 v2 frozen segmented output count mismatch");
    }
    const std::vector<FloatRowMat> rotations =
        co0_v2_segmented_rotations(dimensions, logical_seed);
    for (size_t index = 0; index < rotations.size(); ++index) {
        copy_row_major(rotations[index], row_major_outputs[index]);
    }
}

void co0_v2_frozen_whole_rotation_values(
    size_t dimension,
    int logical_seed,
    std::span<float> row_major_output) {
    copy_row_major(
        co0_v2_whole_rotation(dimension, logical_seed),
        row_major_output);
}

} // namespace saqlib::caq_validation

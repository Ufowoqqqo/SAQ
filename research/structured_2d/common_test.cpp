#include "common.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::vector<float> fixture(std::size_t rows, std::size_t dimensions) {
    std::vector<float> values(rows * dimensions);
    for (std::size_t row = 0; row < rows; ++row)
        for (std::size_t dimension = 0;
             dimension < dimensions; ++dimension)
            values[row * dimensions + dimension] =
                    static_cast<float>(
                            std::sin((row + 1) * (dimension + 2) * 0.17) +
                            0.03 * row - 0.07 * dimension);
    return values;
}

void moment_test() {
    const std::vector<float> values{1, 2, 3, 4, 5, 6};
    const auto moments =
            structured2d::admission::coordinate_moments(values, 2);
    require(std::abs(moments.mean[0] - 3) < 1e-14, "mean 0");
    require(std::abs(moments.mean[1] - 4) < 1e-14, "mean 1");
    require(
            std::abs(
                    moments.standard_deviation[0] -
                    std::sqrt(8.0 / 3)) < 1e-14,
            "standard deviation");
}

void pca_and_synthetic_test() {
    constexpr std::size_t rows = 64;
    constexpr std::size_t dimensions = 4;
    const auto values = fixture(rows, dimensions);
    auto pca = structured2d::admission::train_full_pca(
            values, dimensions);
    std::vector<float> transformed(values.size());
    pca->apply_noalloc(rows, values.data(), transformed.data());
    const auto moments =
            structured2d::admission::coordinate_moments(
                    transformed, dimensions);
    const auto first =
            structured2d::admission::deterministic_synthetic_queries(
                    structured2d::admission::Dataset::Sift1M,
                    moments, *pca, 64);
    const auto replay =
            structured2d::admission::deterministic_synthetic_queries(
                    structured2d::admission::Dataset::Sift1M,
                    moments, *pca, 64);
    const auto other =
            structured2d::admission::deterministic_synthetic_queries(
                    structured2d::admission::Dataset::Gist1M,
                    moments, *pca, 64);
    require(first == replay, "synthetic replay");
    require(first != other, "dataset-specific synthetic queries");
    for (float value : first)
        require(std::isfinite(value), "finite synthetic query");
}

void coarse_test() {
    constexpr std::size_t rows = 96;
    constexpr std::size_t dimensions = 4;
    const auto values = fixture(rows, dimensions);
    auto coarse = structured2d::admission::train_coarse(
            values, dimensions, 4);
    const auto assignments =
            structured2d::admission::assign_lists(
                    *coarse, values, dimensions);
    const auto counts =
            structured2d::admission::count_lists(assignments, 4);
    std::uint64_t total = 0;
    for (std::uint64_t count : counts) total += count;
    require(total == rows, "assignment count");
    require(coarse->ntotal == 4, "centroid count");
}

}  // namespace

int main() {
    try {
        moment_test();
        pca_and_synthetic_test();
        coarse_test();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "common_test: " << error.what() << '\n';
        return 1;
    }
}

#pragma once

#include "admission.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <vector>

namespace faiss {
struct IndexFlatL2;
struct PCAMatrix;
}  // namespace faiss

namespace structured2d::admission {

struct CoordinateMoments {
    std::vector<double> mean;
    std::vector<double> standard_deviation;
};

CoordinateMoments coordinate_moments(
        std::span<const float> vectors, std::size_t dimensions);

std::vector<float> deterministic_synthetic_queries(
        Dataset dataset, const CoordinateMoments& moments,
        const faiss::PCAMatrix& pca, std::size_t count);

std::unique_ptr<faiss::PCAMatrix> train_full_pca(
        std::span<const float> learn, std::size_t dimensions);

std::unique_ptr<faiss::IndexFlatL2> train_coarse(
        std::span<const float> transformed_learn,
        std::size_t dimensions, std::size_t nlist);

std::vector<std::uint32_t> assign_lists(
        const faiss::IndexFlatL2& coarse,
        std::span<const float> vectors, std::size_t dimensions);

std::vector<std::uint64_t> count_lists(
        std::span<const std::uint32_t> assignments,
        std::size_t nlist);

struct DatasetBuildSpec {
    Dataset dataset{};
    std::filesystem::path learn_path;
    std::filesystem::path base_path;
    std::filesystem::path output_directory;
    std::size_t dimensions = 0;
    std::size_t learn_rows = 0;
    std::size_t base_rows = 0;
    std::size_t block_rows = 0;
};

void prepare_common_state(const DatasetBuildSpec& spec);

}  // namespace structured2d::admission

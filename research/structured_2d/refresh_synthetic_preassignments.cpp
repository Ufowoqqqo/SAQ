#include "admission.hpp"
#include "dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kQueries = 64;

void run(
        const std::filesystem::path& dataset_directory,
        std::size_t dimensions) {
    structured2d::admission::FvecsReader original_reader(
            dataset_directory / "synthetic_original.fvecs",
            kQueries, dimensions);
    const auto original =
            structured2d::admission::read_all(original_reader);
    auto pca = faiss::read_VectorTransform_up(
            (dataset_directory / "pca.faiss").c_str());
    if (pca == nullptr || !pca->is_trained ||
        pca->d_in != static_cast<int>(dimensions) ||
        pca->d_out != static_cast<int>(dimensions))
        throw std::runtime_error("refresh PCA");

    std::vector<float> transformed(kQueries * dimensions);
    for (std::size_t query = 0; query < kQueries; ++query)
        pca->apply_noalloc(
                1, original.data() + query * dimensions,
                transformed.data() + query * dimensions);
    structured2d::admission::FvecsWriter transformed_writer(
            dataset_directory / "synthetic_pca.fvecs",
            dimensions);
    transformed_writer.write(transformed);
    transformed_writer.close();

    for (const std::size_t nlist : {1024UL, 4096UL}) {
        const auto directory = dataset_directory /
                ("nlist_" + std::to_string(nlist));
        auto coarse_owner = faiss::read_index_up(
                (directory / "coarse.faiss").c_str());
        auto* coarse =
                dynamic_cast<faiss::IndexFlatL2*>(
                        coarse_owner.get());
        if (coarse == nullptr ||
            coarse->d != static_cast<int>(dimensions) ||
            coarse->ntotal != static_cast<faiss::idx_t>(nlist))
            throw std::runtime_error("refresh coarse");
        const std::size_t max_probe =
                structured2d::admission::frozen_nprobes(nlist).back();
        std::vector<float> distances(kQueries * max_probe);
        std::vector<faiss::idx_t> labels(kQueries * max_probe);
        for (std::size_t query = 0; query < kQueries; ++query)
            coarse->search(
                    1, transformed.data() + query * dimensions,
                    max_probe,
                    distances.data() + query * max_probe,
                    labels.data() + query * max_probe);
        std::vector<std::uint32_t> selected(labels.size());
        for (std::size_t index = 0; index < labels.size(); ++index) {
            if (labels[index] < 0 ||
                labels[index] >=
                        static_cast<faiss::idx_t>(nlist))
                throw std::runtime_error("refresh label");
            selected[index] =
                    static_cast<std::uint32_t>(labels[index]);
        }
        structured2d::admission::write_u32(
                directory / "synthetic_selected_lists.u32",
                selected);
        structured2d::admission::FvecsWriter distance_writer(
                directory / "synthetic_coarse_distances.fvecs",
                max_probe);
        distance_writer.write(distances);
        distance_writer.close();
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument(
                    "usage: structured_2d_refresh_synthetic_preassignments "
                    "<dataset_directory> <dimensions>");
        run(argv[1], std::stoull(argv[2]));
        return 0;
    } catch (const std::exception& error) {
        std::cerr
                << "structured_2d_refresh_synthetic_preassignments: "
                << error.what() << '\n';
        return 1;
    }
}

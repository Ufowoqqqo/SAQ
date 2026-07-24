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

void run(
        const std::filesystem::path& admission_dataset,
        const std::filesystem::path& query_path,
        std::size_t queries, std::size_t dimensions,
        const std::filesystem::path& output_dataset) {
    structured2d::admission::FvecsReader reader(
            query_path, queries, dimensions);
    const auto original =
            structured2d::admission::read_all(reader);
    auto pca = faiss::read_VectorTransform_up(
            (admission_dataset / "pca.faiss").c_str());
    if (pca == nullptr || !pca->is_trained ||
        pca->d_in != static_cast<int>(dimensions) ||
        pca->d_out != static_cast<int>(dimensions))
        throw std::runtime_error("natural schedule PCA");
    std::vector<float> transformed(queries * dimensions);
    for (std::size_t query = 0; query < queries; ++query)
        pca->apply_noalloc(
                1, original.data() + query * dimensions,
                transformed.data() + query * dimensions);
    std::filesystem::create_directories(output_dataset);
    structured2d::admission::FvecsWriter pca_writer(
            output_dataset / "query_pca.fvecs", dimensions);
    pca_writer.write(transformed);
    pca_writer.close();

    for (const std::size_t nlist : {1024UL, 4096UL}) {
        const auto common = admission_dataset /
                ("nlist_" + std::to_string(nlist));
        auto coarse_owner = faiss::read_index_up(
                (common / "coarse.faiss").c_str());
        auto* coarse = dynamic_cast<faiss::IndexFlatL2*>(
                coarse_owner.get());
        if (coarse == nullptr ||
            coarse->d != static_cast<int>(dimensions) ||
            coarse->ntotal != static_cast<faiss::idx_t>(nlist))
            throw std::runtime_error("natural schedule coarse");
        const std::size_t max_probe =
                structured2d::admission::frozen_nprobes(nlist).back();
        std::vector<float> distances(queries * max_probe);
        std::vector<faiss::idx_t> labels(queries * max_probe);
        for (std::size_t query = 0; query < queries; ++query)
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
                throw std::runtime_error("natural schedule label");
            selected[index] =
                    static_cast<std::uint32_t>(labels[index]);
        }
        const auto output = output_dataset /
                ("nlist_" + std::to_string(nlist));
        std::filesystem::create_directories(output);
        structured2d::admission::write_u32(
                output / "query_selected_lists.u32", selected);
        structured2d::admission::FvecsWriter distance_writer(
                output / "query_coarse_distances.fvecs",
                max_probe);
        distance_writer.write(distances);
        distance_writer.close();
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: structured_2d_prepare_natural_schedule "
                    "<admission_dataset> <query_fvecs> "
                    "<query_rows> <dimensions> <output_dataset>");
        run(
                argv[1], argv[2], std::stoull(argv[3]),
                std::stoull(argv[4]), argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_prepare_natural_schedule: "
                  << error.what() << '\n';
        return 1;
    }
}

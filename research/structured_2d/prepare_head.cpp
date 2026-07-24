#include "dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kHead = 128;

void extract_head(
        const std::filesystem::path& source,
        const std::filesystem::path& destination,
        std::size_t rows, std::size_t dimensions,
        std::size_t block_rows) {
    structured2d::admission::FvecsReader reader(
            source, rows, dimensions);
    structured2d::admission::FvecsWriter writer(
            destination, kHead);
    std::vector<float> input(block_rows * dimensions);
    std::vector<float> output(block_rows * kHead);
    std::size_t offset = 0;
    while (offset < rows) {
        const std::size_t requested =
                std::min(block_rows, rows - offset);
        const std::size_t count = reader.read(
                std::span<float>(
                        input.data(), requested * dimensions));
        if (count != requested)
            throw std::runtime_error("short head input");
        for (std::size_t row = 0; row < count; ++row)
            std::copy_n(
                    input.data() + row * dimensions, kHead,
                    output.data() + row * kHead);
        writer.write(std::span<const float>(
                output.data(), count * kHead));
        offset += count;
    }
    writer.close();
}

void prepare(
        const std::filesystem::path& full,
        const std::filesystem::path& head) {
    if (std::filesystem::exists(head))
        throw std::invalid_argument("head output exists");
    std::filesystem::create_directories(head);
    extract_head(
            full / "learn_pca.fvecs",
            head / "learn_pca.fvecs",
            500000, 960, 4096);
    extract_head(
            full / "base_pca.fvecs",
            head / "base_pca.fvecs",
            1000000, 960, 4096);

    for (std::size_t nlist : {1024, 4096}) {
        const auto full_dir =
                full / ("nlist_" + std::to_string(nlist));
        const auto head_dir =
                head / ("nlist_" + std::to_string(nlist));
        std::filesystem::create_directories(head_dir);
        const std::string source =
                (full_dir / "coarse.faiss").string();
        std::unique_ptr<faiss::Index> loaded(
                faiss::read_index(source.c_str()));
        auto* full_coarse =
                dynamic_cast<faiss::IndexFlatL2*>(loaded.get());
        if (full_coarse == nullptr ||
            full_coarse->d != 960 ||
            full_coarse->ntotal !=
                    static_cast<faiss::idx_t>(nlist))
            throw std::runtime_error("full coarse type");
        faiss::IndexFlatL2 head_coarse(kHead);
        std::vector<float> centroids(nlist * kHead);
        const float* full_centroids = full_coarse->get_xb();
        for (std::size_t list = 0; list < nlist; ++list)
            std::copy_n(
                    full_centroids + list * 960, kHead,
                    centroids.data() + list * kHead);
        head_coarse.add(nlist, centroids.data());
        const std::string target =
                (head_dir / "coarse.faiss").string();
        faiss::write_index(&head_coarse, target.c_str());

        for (const char* file :
             {"learn_assignments.u32", "base_assignments.u32",
              "list_sizes.u64"}) {
            std::filesystem::copy_file(
                    full_dir / file, head_dir / file,
                    std::filesystem::copy_options::none);
        }
    }
    std::ofstream note(head / "HEAD_VIEW_SOURCE.txt");
    note << "Derived from the first 128 coordinates of the frozen "
            "full-dimensional GIST PCA state.\n"
            "Assignments and list sizes are byte copies of the "
            "full-dimensional shared coarse state; the head coarse "
            "centroids are used only for residual encoding and never "
            "for candidate selection.\n";
    note.close();
    if (!note) throw std::runtime_error("write head note");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument(
                    "usage: structured_2d_prepare_head "
                    "<full_common> <head_common>");
        prepare(argv[1], argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_prepare_head: "
                  << error.what() << '\n';
        return 1;
    }
}

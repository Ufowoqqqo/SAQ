#include "../structured_2d/dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::size_t kRows = 1'000'000;
constexpr std::size_t kSelected = 16'384;
constexpr std::size_t kHead = 128;
constexpr std::size_t kParityRows = 256;
constexpr std::array<std::size_t, 2> kNlists = {1024, 4096};

std::vector<std::uint64_t> read_indices(
        const std::filesystem::path& path) {
    if (std::filesystem::file_size(path) !=
        kSelected * sizeof(std::uint64_t))
        throw std::runtime_error("index file size");
    std::vector<std::uint64_t> result(kSelected);
    std::ifstream input(path, std::ios::binary);
    input.read(
            reinterpret_cast<char*>(result.data()),
            static_cast<std::streamsize>(result.size() * sizeof(result[0])));
    if (!input || input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("read indices");
    std::vector<bool> seen(kRows, false);
    for (const auto row : result) {
        if (row >= kRows || seen[row]) throw std::runtime_error("invalid index");
        seen[row] = true;
    }
    return result;
}

struct CoarseState {
    std::size_t nlist = 0;
    std::vector<std::uint32_t> assignments;
    std::unique_ptr<faiss::Index> owner;
    faiss::IndexFlatL2* index = nullptr;
    std::unique_ptr<structured2d::admission::FvecsWriter> writer;
};

void extract(
        const std::filesystem::path& raw_path,
        const std::filesystem::path& common,
        std::size_t dimensions,
        const std::filesystem::path& index_path,
        const std::filesystem::path& output) {
    if (dimensions < kHead || std::filesystem::exists(output))
        throw std::invalid_argument("stage extraction arguments");
    std::filesystem::create_directories(output);
    const auto indices = read_indices(index_path);

    std::unique_ptr<faiss::VectorTransform> transform(
            faiss::read_VectorTransform((common / "pca.faiss").c_str()));
    auto* pca = dynamic_cast<faiss::PCAMatrix*>(transform.get());
    if (pca == nullptr || pca->d_in != static_cast<int>(dimensions) ||
        pca->d_out != static_cast<int>(dimensions))
        throw std::runtime_error("PCA shape");

    std::vector<CoarseState> states;
    states.reserve(kNlists.size());
    for (const auto nlist : kNlists) {
        const auto directory = common / ("nlist_" + std::to_string(nlist));
        CoarseState state;
        state.nlist = nlist;
        state.assignments = structured2d::admission::read_u32(
                directory / "base_assignments.u32", kRows);
        state.owner.reset(faiss::read_index((directory / "coarse.faiss").c_str()));
        state.index = dynamic_cast<faiss::IndexFlatL2*>(state.owner.get());
        if (state.index == nullptr ||
            state.index->d != static_cast<faiss::idx_t>(dimensions) ||
            state.index->ntotal != static_cast<faiss::idx_t>(nlist))
            throw std::runtime_error("coarse index shape");
        state.writer =
                std::make_unique<structured2d::admission::FvecsWriter>(
                        output / ("residual_nlist" + std::to_string(nlist) +
                                  ".fvecs"),
                        kHead);
        states.push_back(std::move(state));
    }

    structured2d::admission::FvecsWriter pca_writer(
            output / "pca_head128.fvecs", kHead);
    std::ifstream base(common / "base_pca.fvecs", std::ios::binary);
    std::ifstream raw(raw_path, std::ios::binary);
    if (!base || !raw) throw std::runtime_error("open base input");
    const std::uint64_t row_bytes =
            (static_cast<std::uint64_t>(dimensions) + 1) * sizeof(float);
    if (std::filesystem::file_size(common / "base_pca.fvecs") !=
            kRows * row_bytes ||
        std::filesystem::file_size(raw_path) != kRows * row_bytes)
        throw std::runtime_error("base input size");

    std::vector<float> vector(dimensions);
    std::vector<float> raw_vector(dimensions);
    std::vector<float> replay(dimensions);
    std::vector<float> parity_vectors(kParityRows * dimensions);
    std::vector<float> head(kHead);
    std::vector<float> residual(kHead);
    double maximum_pca_difference = 0;
    for (std::size_t position = 0; position < indices.size(); ++position) {
        const auto row = indices[position];
        base.seekg(static_cast<std::streamoff>(row * row_bytes));
        std::uint32_t stored_dimensions = 0;
        base.read(reinterpret_cast<char*>(&stored_dimensions), sizeof(stored_dimensions));
        base.read(
                reinterpret_cast<char*>(vector.data()),
                static_cast<std::streamsize>(dimensions * sizeof(float)));
        if (!base || stored_dimensions != dimensions ||
            !std::all_of(vector.begin(), vector.end(), [](float value) {
                return std::isfinite(value);
            }))
            throw std::runtime_error("base PCA row");
        if (position < kParityRows) {
            raw.seekg(static_cast<std::streamoff>(row * row_bytes));
            std::uint32_t raw_dimensions = 0;
            raw.read(reinterpret_cast<char*>(&raw_dimensions), sizeof(raw_dimensions));
            raw.read(
                    reinterpret_cast<char*>(raw_vector.data()),
                    static_cast<std::streamsize>(dimensions * sizeof(float)));
            if (!raw || raw_dimensions != dimensions)
                throw std::runtime_error("raw base row");
            pca->apply_noalloc(1, raw_vector.data(), replay.data());
            for (std::size_t coordinate = 0; coordinate < dimensions; ++coordinate) {
                const double difference = std::abs(
                        static_cast<double>(replay[coordinate]) - vector[coordinate]);
                maximum_pca_difference =
                        std::max(maximum_pca_difference, difference);
                const double tolerance =
                        2e-4 * std::max(1.0, std::abs(static_cast<double>(vector[coordinate])));
                if (!std::isfinite(raw_vector[coordinate]) ||
                    !std::isfinite(replay[coordinate]) || difference > tolerance)
                    throw std::runtime_error("raw-to-PCA parity");
            }
            std::copy(
                    vector.begin(), vector.end(),
                    parity_vectors.begin() + position * dimensions);
        }
        std::copy_n(vector.begin(), kHead, head.begin());
        pca_writer.write(head);

        for (auto& state : states) {
            const std::uint32_t list = state.assignments[row];
            if (list >= state.nlist) throw std::runtime_error("assignment range");
            const float* centroid =
                    state.index->get_xb() +
                    static_cast<std::size_t>(list) * dimensions;
            for (std::size_t coordinate = 0; coordinate < kHead; ++coordinate)
                residual[coordinate] = head[coordinate] - centroid[coordinate];
            state.writer->write(residual);
        }
    }
    pca_writer.close();
    for (auto& state : states) state.writer->close();

    for (const auto& state : states) {
        std::vector<float> distances(kParityRows);
        std::vector<faiss::idx_t> labels(kParityRows);
        state.index->search(
                kParityRows, parity_vectors.data(), 1,
                distances.data(), labels.data());
        for (std::size_t position = 0; position < kParityRows; ++position)
            if (!std::isfinite(distances[position]) || labels[position] < 0 ||
                static_cast<std::uint32_t>(labels[position]) !=
                        state.assignments[indices[position]])
                throw std::runtime_error("coarse assignment parity");
    }

    std::ofstream note(output / "STAGE_SOURCE.txt");
    note << "Rows follow the supplied frozen u64 index order.\n"
            "PCA is the first 128 coordinates of the full-dimensional transform.\n"
            "Residual routing uses the corresponding full-dimensional coarse index "
            "and saved base assignment.\n"
         << "raw_to_saved_pca_max_abs_difference="
         << maximum_pca_difference << '\n'
         << "pca_parity_rows=" << kParityRows << '\n'
         << "coarse_assignment_parity_rows_per_nlist=" << kParityRows << '\n';
    note.close();
    if (!note) throw std::runtime_error("stage note");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: correlated_pair_extract_stages "
                    "<raw-base> <common-dir> <dimensions> <indices.u64> "
                    "<output-dir>");
        extract(argv[1], argv[2], std::stoull(argv[3]), argv[4], argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "correlated_pair_extract_stages: " << error.what() << '\n';
        return 1;
    }
}

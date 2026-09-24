#include "../structured_2d/common.hpp"
#include "../structured_2d/dataset_io.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
namespace io = structured2d::admission;
constexpr std::size_t kBaseRows = 1'000'000, kSelected = 16'384;
constexpr std::size_t kHead = 128, kNlist = 1024, kParityRows = 256;

std::vector<float> selected_rows(
        const std::filesystem::path& path, std::size_t dimensions,
        const std::vector<std::uint64_t>& indices) {
    const std::uint64_t row_bytes = (dimensions + 1) * sizeof(float);
    if (std::filesystem::file_size(path) != kBaseRows * row_bytes)
        throw std::runtime_error("base file size");
    std::vector<bool> seen(kBaseRows, false);
    std::vector<float> rows(indices.size() * dimensions);
    std::ifstream input(path, std::ios::binary);
    for (std::size_t i = 0; i < indices.size(); ++i) {
        const auto row = indices[i];
        if (row >= kBaseRows || seen[row])
            throw std::runtime_error("invalid or duplicate selected index");
        seen[row] = true;
        input.seekg(static_cast<std::streamoff>(row * row_bytes));
        std::uint32_t stored_dimensions = 0;
        input.read(reinterpret_cast<char*>(&stored_dimensions), sizeof(stored_dimensions));
        input.read(reinterpret_cast<char*>(rows.data() + i * dimensions),
                   static_cast<std::streamsize>(dimensions * sizeof(float)));
        if (!input || stored_dimensions != dimensions)
            throw std::runtime_error("selected base row");
    }
    if (!std::all_of(rows.begin(), rows.end(), [](float x) { return std::isfinite(x); }))
        throw std::runtime_error("non-finite selected base value");
    return rows;
}

void rebuild(int argc, char** argv) {
    if (argc != 6)
        throw std::invalid_argument(
                "usage: correlated_pair_rebuild_panel <sift|gist> "
                "<learn.fvecs> <base.fvecs> <indices.u64> <output>");
    const std::string dataset = argv[1];
    if (dataset != "sift" && dataset != "gist")
        throw std::invalid_argument("dataset must be sift or gist");
    const std::size_t dimensions = dataset == "sift" ? 128 : 960;
    const std::size_t learn_rows = dataset == "sift" ? 100'000 : 500'000;
    const std::filesystem::path output = argv[5];
    if (std::filesystem::exists(output))
        throw std::invalid_argument("output already exists");
    const auto indices = io::read_u64(argv[4], kSelected);
    const auto original = selected_rows(argv[3], dimensions, indices);
    io::FvecsReader learn_reader(argv[2], learn_rows, dimensions);
    auto learn = io::read_all(learn_reader);
    std::filesystem::create_directories(output / "nlist_1024");

    std::cout << "train_full_pca " << dataset << std::endl;
    auto pca = io::train_full_pca(learn, dimensions);
    std::vector<float> transformed_learn(learn.size());
    pca->apply_noalloc(static_cast<faiss::idx_t>(learn_rows),
                       learn.data(), transformed_learn.data());
    std::vector<float>().swap(learn);
    // Reuse the frozen training function: all learn rows, seed 1234,
    // 25 iterations, one redo. Only nlist=1024 is built for this experiment.
    std::cout << "train_coarse_nlist1024 " << dataset << std::endl;
    auto coarse = io::train_coarse(transformed_learn, dimensions, kNlist);
    std::vector<float>().swap(transformed_learn);
    const auto pca_path = output / "pca.faiss";
    const auto coarse_path = output / "nlist_1024/coarse.faiss";
    faiss::write_VectorTransform(pca.get(), pca_path.c_str());
    faiss::write_index(coarse.get(), coarse_path.c_str());
    std::unique_ptr<faiss::VectorTransform> loaded_transform(
            faiss::read_VectorTransform(pca_path.c_str()));
    std::unique_ptr<faiss::Index> loaded_index(faiss::read_index(coarse_path.c_str()));
    auto* loaded_pca = dynamic_cast<faiss::PCAMatrix*>(loaded_transform.get());
    auto* loaded_coarse = dynamic_cast<faiss::IndexFlatL2*>(loaded_index.get());
    if (!loaded_pca || loaded_pca->d_in != static_cast<int>(dimensions) ||
        loaded_pca->d_out != static_cast<int>(dimensions) || !loaded_pca->is_trained ||
        !loaded_coarse || loaded_coarse->d != static_cast<int>(dimensions) ||
        loaded_coarse->ntotal != static_cast<faiss::idx_t>(kNlist))
        throw std::runtime_error("reloaded model shape");

    // Both sides use the same batch shape: this checks serialization,
    // not equality to the deleted historical panel's different BLAS batches.
    std::vector<float> before(kParityRows * dimensions), after(before.size());
    pca->apply_noalloc(kParityRows, original.data(), before.data());
    loaded_pca->apply_noalloc(kParityRows, original.data(), after.data());
    double maximum_difference = 0;
    for (std::size_t i = 0; i < before.size(); ++i) {
        const double difference = std::abs(static_cast<double>(before[i]) - after[i]);
        maximum_difference = std::max(maximum_difference, difference);
        if (!std::isfinite(before[i]) || !std::isfinite(after[i]) ||
            difference > 2e-4 * std::max(1.0, std::abs(static_cast<double>(before[i]))))
            throw std::runtime_error("serialized PCA parity");
    }
    if (io::assign_lists(*coarse, before, dimensions) !=
        io::assign_lists(*loaded_coarse, after, dimensions))
        throw std::runtime_error("serialized coarse assignment parity");
    pca.reset();
    coarse.reset();

    std::cout << "transform_and_route_selected " << dataset << std::endl;
    std::vector<float> transformed(original.size());
    // Full-dimensional routing precedes truncation, including all 960 GIST
    // coordinates. The fixed 16384-row batch is part of this rebuilt identity.
    loaded_pca->apply_noalloc(kSelected, original.data(), transformed.data());
    const auto assignments = io::assign_lists(*loaded_coarse, transformed, dimensions);
    io::write_u32(output / "selected_assignments.u32", assignments);
    io::FvecsWriter writer(output / "residual_nlist1024.fvecs", kHead);
    std::vector<float> residual(kHead);
    for (std::size_t i = 0; i < kSelected; ++i) {
        const float* centroid = loaded_coarse->get_xb() + assignments[i] * dimensions;
        for (std::size_t d = 0; d < kHead; ++d)
            residual[d] = transformed[i * dimensions + d] - centroid[d];
        writer.write(residual);
    }
    writer.close();
    std::ofstream note(output / "STAGE_SOURCE.txt");
    note << std::setprecision(17)
         << "representation_identity=REBUILT\noriginal_panel_bitwise_reproduction=false\n"
         << "dataset=" << dataset << "\nlearn_source=" << argv[2]
         << "\nbase_source=" << argv[3] << "\nindices_source=" << argv[4]
         << "\nlearn_rows=" << learn_rows << "\nfull_dimensions=" << dimensions
         << "\nselected_rows=16384\nselected_batch_rows=16384\noutput_dimensions=128\n"
         << "nlist=1024\ncoarse_seed=1234\ncoarse_iterations=25\ncoarse_redo=1\n"
         << "routing=full_dimensional_PCA_nearest_coarse_then_residual_head128\n"
         << "row_order=supplied_frozen_u64_indices\nserialization_parity_rows=256\n"
         << "serialized_pca_max_abs_difference=" << maximum_difference
         << "\nserialized_assignment_parity=PASS\n";
    note.close();
    if (!note) throw std::runtime_error("write stage source");
    std::cout << "rebuilt_panel_complete " << output << std::endl;
}
}  // namespace

int main(int argc, char** argv) {
    try {
        rebuild(argc, argv);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "correlated_pair_rebuild_panel: " << error.what() << '\n';
        return 1;
    }
}

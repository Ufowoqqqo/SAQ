// Reuse trained full-dimensional PCA/coarse models; never train or read queries.
#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
constexpr size_t rows = 16384, base_rows = 1000000;

template<class T> std::vector<T> read_array(const fs::path& path, size_t n) {
    if (fs::file_size(path) != n * sizeof(T)) throw std::runtime_error("array size: " + path.string());
    std::vector<T> result(n);
    std::ifstream stream(path, std::ios::binary);
    stream.read(reinterpret_cast<char*>(result.data()), n * sizeof(T));
    if (!stream) throw std::runtime_error("read: " + path.string());
    return result;
}

void write_fvecs(const fs::path& path, const std::vector<float>& values, int dimensions) {
    if (values.size() != rows * dimensions) throw std::runtime_error("output shape");
    std::ofstream stream(path, std::ios::binary);
    int32_t d = dimensions;
    for (size_t i = 0; i < rows; ++i) {
        stream.write(reinterpret_cast<const char*>(&d), sizeof(d));
        stream.write(reinterpret_cast<const char*>(values.data() + i*dimensions), dimensions*sizeof(float));
    }
    stream.close();
    if (!stream) throw std::runtime_error("write: " + path.string());
}

int main(int argc, char** argv) {
    try {
        if (argc != 6) throw std::runtime_error(
            "usage: export_panels <128|960> <base.fvecs> <indices.u64> <old-panel-dir> <new-output>");
        int d = std::stoi(argv[1]);
        if (d != 128 && d != 960) throw std::runtime_error("full dimensions required");
        fs::path base = argv[2], old = argv[4], output = argv[5];
        if (fs::exists(output)) throw std::runtime_error("output exists");
        const auto ids = read_array<uint64_t>(argv[3], rows);
        std::vector<bool> seen(base_rows, false);
        std::vector<float> original(rows*d);
        const uint64_t stride = (d+1)*sizeof(float);
        if (fs::file_size(base) != base_rows*stride) throw std::runtime_error("base size");
        std::ifstream input(base, std::ios::binary);
        for (size_t i = 0; i < rows; ++i) {
            auto row = ids[i];
            if (row >= base_rows || seen[row]) throw std::runtime_error("invalid/duplicate sample");
            seen[row] = true;
            input.seekg(row*stride);
            int32_t header = 0;
            input.read(reinterpret_cast<char*>(&header), sizeof(header));
            input.read(reinterpret_cast<char*>(original.data()+i*d), d*sizeof(float));
            if (!input || header != d) throw std::runtime_error("base row format");
        }
        for (float x: original) if (!std::isfinite(x)) throw std::runtime_error("nonfinite base");
        std::unique_ptr<faiss::VectorTransform> transform(
            faiss::read_VectorTransform((old / "pca.faiss").c_str()));
        std::unique_ptr<faiss::Index> owner(
            faiss::read_index((old / "nlist_1024/coarse.faiss").c_str()));
        auto* pca = dynamic_cast<faiss::PCAMatrix*>(transform.get());
        auto* coarse = dynamic_cast<faiss::IndexFlatL2*>(owner.get());
        if (!pca || !coarse || pca->d_in != d || pca->d_out != d ||
            !pca->is_trained || !pca->is_orthonormal || pca->random_rotation ||
            pca->eigen_power != 0 || coarse->d != d || coarse->ntotal != 1024)
            throw std::runtime_error("unexpected upstream model");
        std::vector<float> transformed(rows*d), distances(rows), residual(rows*d);
        std::vector<faiss::idx_t> labels(rows);
        // Same 16,384-row batch shape as the archived rebuild.
        pca->apply_noalloc(rows, original.data(), transformed.data());
        coarse->search(rows, transformed.data(), 1, distances.data(), labels.data());
        for (size_t i = 0; i < rows; ++i) {
            if (labels[i] < 0 || labels[i] >= 1024 || !std::isfinite(distances[i]))
                throw std::runtime_error("invalid coarse assignment");
            const float* center = coarse->get_xb() + labels[i]*d;
            for (int j = 0; j < d; ++j) {
                residual[i*d+j] = transformed[i*d+j]-center[j];
                if (!std::isfinite(residual[i*d+j])) throw std::runtime_error("nonfinite residual");
            }
        }
        // Match the archived head; never silently substitute another representation.
        std::ifstream head(old / "residual_nlist1024.fvecs", std::ios::binary);
        if (!head || fs::file_size(old / "residual_nlist1024.fvecs") != rows*129*sizeof(float))
            throw std::runtime_error("missing archived head");
        double maximum = 0;
        for (size_t i = 0; i < rows; ++i) {
            int32_t header = 0;
            float values[128];
            head.read(reinterpret_cast<char*>(&header), sizeof(header));
            head.read(reinterpret_cast<char*>(values), sizeof(values));
            if (!head || header != 128) throw std::runtime_error("bad archived head");
            for (size_t j = 0; j < 128; ++j) {
                double difference = std::abs(double(values[j])-residual[i*d+j]);
                if (!std::isfinite(values[j]) || difference > 2e-5*std::max(1.0, std::abs(double(values[j]))))
                    throw std::runtime_error("archived residual head parity failed");
                maximum = std::max(maximum, difference);
            }
        }
        if (fs::exists(old / "selected_assignments.u32")) {
            const auto recorded = read_array<uint32_t>(old / "selected_assignments.u32", rows);
            for (size_t i=0; i<rows; ++i) if (recorded[i] != labels[i])
                throw std::runtime_error("assignment mismatch");
        }
        fs::create_directories(output);
        write_fvecs(output / "pca_full.fvecs", transformed, d);
        write_fvecs(output / "residual_nlist1024_full.fvecs", residual, d);
        std::ofstream note(output / "STAGE_SOURCE.txt");
        note << "source=REEXTRACTED_FROM_ARCHIVED_FULL_MODELS\n"
             << "upstream_full_PCA=retained\nlocal_PCA=none\nnlist=1024\n"
             << "dimensions=" << d << "\nrows=" << rows << "\n"
             << "base=" << base << "\nindices=" << argv[3] << "\nmodels=" << old << "\n"
             << "head128_parity_max_abs_difference=" << maximum << "\n"
             << "head128_parity_tolerance=2e-5*max(1,abs(reference))\n";
        note.close();
        if (!note) throw std::runtime_error("write provenance");
        std::cout << "exported " << d << " dimensions; head parity max abs " << maximum << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}

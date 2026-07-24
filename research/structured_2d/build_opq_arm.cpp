#include "dataset_io.hpp"
#include "faiss_pool.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <tuple>
#include <vector>

namespace {

double cpu_seconds() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return value.tv_sec + value.tv_nsec * 1e-9;
}

std::uint64_t peak_rss_bytes() {
    rusage value{};
    if (getrusage(RUSAGE_SELF, &value) != 0)
        throw std::runtime_error("getrusage");
    return static_cast<std::uint64_t>(value.ru_maxrss) * 1024;
}

struct Timer {
    double cpu = cpu_seconds();
    std::chrono::steady_clock::time_point wall =
            std::chrono::steady_clock::now();
};

std::pair<double, double> elapsed(const Timer& timer) {
    return {
            cpu_seconds() - timer.cpu,
            std::chrono::duration<double>(
                    std::chrono::steady_clock::now() -
                    timer.wall).count()};
}

std::vector<faiss::idx_t> widen(
        std::span<const std::uint32_t> values) {
    std::vector<faiss::idx_t> result(values.size());
    std::transform(
            values.begin(), values.end(), result.begin(),
            [](std::uint32_t value) {
                return static_cast<faiss::idx_t>(value);
            });
    return result;
}

void compute_residuals(
        std::span<const float> vectors,
        std::span<const std::uint32_t> assignments,
        std::span<const float> centroids,
        std::size_t dimensions,
        std::span<float> output) {
    if (vectors.size() != assignments.size() * dimensions ||
        output.size() != vectors.size() ||
        centroids.empty() ||
        centroids.size() % dimensions != 0)
        throw std::invalid_argument("OPQ residual shape");
    const std::size_t nlist = centroids.size() / dimensions;
    for (std::size_t row = 0; row < assignments.size(); ++row) {
        if (assignments[row] >= nlist)
            throw std::out_of_range("OPQ assignment");
        const float* centroid =
                centroids.data() +
                static_cast<std::size_t>(assignments[row]) *
                        dimensions;
        for (std::size_t dimension = 0;
             dimension < dimensions; ++dimension)
            output[row * dimensions + dimension] =
                    vectors[row * dimensions + dimension] -
                    centroid[dimension];
    }
}

void configure_pq(
        faiss::ProductQuantizer& pq, std::size_t learn_rows) {
    pq.cp.seed = 1234;
    pq.cp.niter = 25;
    pq.cp.nredo = 1;
    pq.cp.spherical = false;
    pq.cp.use_faster_subsampling = false;
    pq.cp.max_points_per_centroid =
            static_cast<int>(
                    (learn_rows + pq.ksub - 1) / pq.ksub);
}

void write_resources(
        const std::filesystem::path& output,
        const std::string& id, std::size_t dimensions,
        std::size_t nlist, std::size_t learn_rows,
        std::size_t subquantizers,
        std::size_t bits, std::uint64_t complete_bytes,
        double residual_cpu, double residual_wall,
        double opq_cpu, double opq_wall,
        double pq_cpu, double pq_wall,
        double add_cpu, double add_wall,
        double write_cpu, double write_wall,
        double load_cpu, double load_wall) {
    std::ofstream record(
            output.string() + ".resources.tsv", std::ios::trunc);
    record << "arm_id\tdimensions\tnlist\tlearn_rows\tbase_rows"
              "\tcomplete_serialized_bytes\tcommon_id_bytes"
              "\tpacked_code_bytes_per_vector"
              "\tresidual_cpu_seconds\tresidual_wall_seconds"
              "\topq_train_cpu_seconds\topq_train_wall_seconds"
              "\tpq_train_cpu_seconds\tpq_train_wall_seconds"
              "\tadd_cpu_seconds\tadd_wall_seconds"
              "\twrite_cpu_seconds\twrite_wall_seconds"
              "\tload_cpu_seconds\tload_wall_seconds"
              "\tpeak_rss_bytes\n";
    record << std::setprecision(17)
           << id << '\t' << dimensions << '\t' << nlist << '\t'
           << learn_rows
           << '\t' << 1000000 << '\t' << complete_bytes << '\t'
           << 1000000 * sizeof(faiss::idx_t) << '\t'
           << static_cast<double>(subquantizers * bits) / 8
           << '\t' << residual_cpu << '\t' << residual_wall
           << '\t' << opq_cpu << '\t' << opq_wall
           << '\t' << pq_cpu << '\t' << pq_wall
           << '\t' << add_cpu << '\t' << add_wall
           << '\t' << write_cpu << '\t' << write_wall
           << '\t' << load_cpu << '\t' << load_wall
           << '\t' << peak_rss_bytes() << '\n';
    record.close();
    if (!record) throw std::runtime_error("write OPQ resources");
}

void run(
        const std::string& dataset, const std::string& view,
        std::size_t nlist, std::size_t subquantizers,
        std::size_t bits, const std::filesystem::path& common,
        const std::filesystem::path& output) {
    const bool sift = dataset == "sift";
    const bool head = view == "head";
    if ((!sift && dataset != "gist") ||
        (!head && view != "full") ||
        (nlist != 1024 && nlist != 4096) ||
        (bits != 4 && bits != 8) ||
        std::filesystem::exists(output) ||
        std::filesystem::exists(output.string() + ".opq.faiss"))
        throw std::invalid_argument("OPQ arguments");
    const std::size_t dimensions =
            head || sift ? 128 : 960;
    if (dimensions % subquantizers != 0)
        throw std::invalid_argument("OPQ subquantizers");
    const std::size_t learn_rows =
            sift ? 100000 : 500000;
    const auto nlist_dir =
            common / ("nlist_" + std::to_string(nlist));

    structured2d::admission::FvecsReader learn_reader(
            common / "learn_pca.fvecs",
            learn_rows, dimensions);
    auto learn =
            structured2d::admission::read_all(learn_reader);
    const auto learn_assignments =
            structured2d::admission::read_u32(
                    nlist_dir / "learn_assignments.u32",
                    learn_rows);
    const std::string coarse_path =
            (nlist_dir / "coarse.faiss").string();
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index(coarse_path.c_str()));
    auto* coarse =
            dynamic_cast<faiss::IndexFlatL2*>(
                    coarse_owner.get());
    if (coarse == nullptr ||
        coarse->d != static_cast<int>(dimensions) ||
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("OPQ coarse type");
    const auto centroids = std::span<const float>(
            coarse->get_xb(), nlist * dimensions);

    std::vector<float> residuals(learn.size());
    double residual_cpu = 0, residual_wall = 0;
    {
        const Timer timer;
        compute_residuals(
                learn, learn_assignments, centroids,
                dimensions, residuals);
        std::tie(residual_cpu, residual_wall) = elapsed(timer);
    }
    learn.clear();
    learn.shrink_to_fit();

    faiss::OPQMatrix opq(
            static_cast<int>(dimensions),
            static_cast<int>(subquantizers));
    double opq_cpu = 0, opq_wall = 0;
    {
        const Timer timer;
        opq.train(
                static_cast<faiss::idx_t>(learn_rows),
                residuals.data());
        if (!opq.is_trained || !opq.is_orthonormal)
            throw std::runtime_error("OPQ training");
        std::tie(opq_cpu, opq_wall) = elapsed(timer);
    }
    std::vector<float> rotated(residuals.size());
    opq.apply_noalloc(
            static_cast<faiss::idx_t>(learn_rows),
            residuals.data(), rotated.data());
    residuals.clear();
    residuals.shrink_to_fit();

    faiss::IndexIVFPQ index(
            coarse, dimensions, nlist, subquantizers, bits,
            faiss::METRIC_L2);
    index.own_fields = false;
    index.by_residual = false;
    index.use_precomputed_table = 0;
    configure_pq(index.pq, learn_rows);
    double pq_cpu = 0, pq_wall = 0;
    {
        const Timer timer;
        index.pq.train(
                static_cast<faiss::idx_t>(learn_rows),
                rotated.data());
        index.is_trained = true;
        std::tie(pq_cpu, pq_wall) = elapsed(timer);
    }
    rotated.clear();
    rotated.shrink_to_fit();

    const auto base_assignments =
            structured2d::admission::read_u32(
                    nlist_dir / "base_assignments.u32", 1000000);
    structured2d::admission::FvecsReader base_reader(
            common / "base_pca.fvecs", 1000000, dimensions);
    constexpr std::size_t block_rows = 4096;
    std::vector<float> base(block_rows * dimensions);
    std::vector<float> base_residuals(base.size());
    std::vector<float> base_rotated(base.size());
    double add_cpu = 0, add_wall = 0;
    {
        const Timer timer;
        std::size_t offset = 0;
        while (offset < 1000000) {
            const std::size_t count =
                    std::min(block_rows, 1000000 - offset);
            if (base_reader.read(std::span<float>(
                        base.data(), count * dimensions)) != count)
                throw std::runtime_error("short OPQ base");
            const auto block_assignments =
                    std::span<const std::uint32_t>(
                            base_assignments.data() + offset,
                            count);
            compute_residuals(
                    std::span<const float>(
                            base.data(), count * dimensions),
                    block_assignments, centroids, dimensions,
                    std::span<float>(
                            base_residuals.data(),
                            count * dimensions));
            opq.apply_noalloc(
                    static_cast<faiss::idx_t>(count),
                    base_residuals.data(), base_rotated.data());
            const auto labels = widen(block_assignments);
            std::vector<faiss::idx_t> ids(count);
            for (std::size_t row = 0; row < count; ++row)
                ids[row] =
                        static_cast<faiss::idx_t>(offset + row);
            index.add_core(
                    static_cast<faiss::idx_t>(count),
                    base_rotated.data(), ids.data(), labels.data());
            offset += count;
        }
        structured2d::admission::verify_native_faiss_layout(
                index, base_assignments);
        std::tie(add_cpu, add_wall) = elapsed(timer);
    }

    double write_cpu = 0, write_wall = 0;
    {
        const Timer timer;
        faiss::write_index(&index, output.c_str());
        const std::string opq_path =
                output.string() + ".opq.faiss";
        faiss::write_VectorTransform(&opq, opq_path.c_str());
        std::tie(write_cpu, write_wall) = elapsed(timer);
    }
    const std::uint64_t complete_bytes =
            std::filesystem::file_size(output) +
            std::filesystem::file_size(
                    output.string() + ".opq.faiss");

    double load_cpu = 0, load_wall = 0;
    {
        const Timer timer;
        std::unique_ptr<faiss::Index> loaded_owner(
                faiss::read_index(output.c_str()));
        auto* loaded =
                dynamic_cast<faiss::IndexIVFPQ*>(
                        loaded_owner.get());
        std::unique_ptr<faiss::VectorTransform> loaded_opq(
                faiss::read_VectorTransform(
                        (output.string() + ".opq.faiss").c_str()));
        auto* loaded_matrix =
                dynamic_cast<faiss::LinearTransform*>(
                        loaded_opq.get());
        if (loaded == nullptr || loaded_matrix == nullptr ||
            loaded_matrix->A != opq.A ||
            loaded_matrix->d_in != opq.d_in ||
            loaded_matrix->d_out != opq.d_out ||
            !loaded_matrix->is_orthonormal ||
            loaded->pq.centroids != index.pq.centroids ||
            loaded->by_residual)
            throw std::runtime_error("OPQ load parity");
        structured2d::admission::verify_native_faiss_layout(
                *loaded, base_assignments);
        std::tie(load_cpu, load_wall) = elapsed(timer);
    }
    const std::string id =
            std::string("OPQ") +
            (head ? "128" : "FULL") + "_M" +
            std::to_string(subquantizers) + "X" +
            std::to_string(bits) +
            (sift ? "_SIFT" : "_GIST");
    write_resources(
            output, id, dimensions, nlist, learn_rows,
            subquantizers, bits, complete_bytes,
            residual_cpu, residual_wall, opq_cpu, opq_wall,
            pq_cpu, pq_wall, add_cpu, add_wall,
            write_cpu, write_wall, load_cpu, load_wall);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 8)
            throw std::invalid_argument(
                    "usage: structured_2d_build_opq_arm "
                    "<sift|gist> <head|full> <nlist> <M> <bits> "
                    "<common_directory> <output_index>");
        run(
                argv[1], argv[2], std::stoull(argv[3]),
                std::stoull(argv[4]), std::stoull(argv[5]),
                argv[6], argv[7]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_build_opq_arm: "
                  << error.what() << '\n';
        return 1;
    }
}

#include "dataset_io.hpp"

#include <faiss/IndexFlat.h>
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

void compute_residuals(
        std::span<const float> vectors,
        std::span<const std::uint32_t> assignments,
        std::span<const float> centroids, std::size_t dimensions,
        std::span<float> output) {
    if (vectors.size() != assignments.size() * dimensions ||
        output.size() != vectors.size() ||
        centroids.size() % dimensions != 0)
        throw std::invalid_argument("probe residual shape");
    const std::size_t nlist = centroids.size() / dimensions;
    for (std::size_t row = 0; row < assignments.size(); ++row) {
        if (assignments[row] >= nlist)
            throw std::out_of_range("probe assignment");
        const float* centroid =
                centroids.data() +
                static_cast<std::size_t>(assignments[row]) * dimensions;
        std::transform(
                vectors.data() + row * dimensions,
                vectors.data() + (row + 1) * dimensions,
                centroid, output.data() + row * dimensions,
                [](float value, float center) { return value - center; });
    }
}

void run(
        std::size_t nlist, std::size_t subquantizers,
        std::size_t pq_iterations,
        const std::filesystem::path& common,
        const std::filesystem::path& output) {
    constexpr std::size_t dimensions = 960;
    constexpr std::size_t learn_rows = 500000;
    if ((nlist != 1024 && nlist != 4096) ||
        dimensions % subquantizers != 0 ||
        (pq_iterations != 1 && pq_iterations != 4 &&
         pq_iterations != 40) ||
        std::filesystem::exists(output))
        throw std::invalid_argument("probe arguments");

    const auto nlist_dir =
            common / ("nlist_" + std::to_string(nlist));
    structured2d::admission::FvecsReader learn_reader(
            common / "learn_pca.fvecs", learn_rows, dimensions);
    auto learn = structured2d::admission::read_all(learn_reader);
    const auto assignments = structured2d::admission::read_u32(
            nlist_dir / "learn_assignments.u32", learn_rows);
    const std::string coarse_path =
            (nlist_dir / "coarse.faiss").string();
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index(coarse_path.c_str()));
    auto* coarse =
            dynamic_cast<faiss::IndexFlatL2*>(coarse_owner.get());
    if (coarse == nullptr || coarse->d != dimensions ||
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("probe coarse type");

    std::vector<float> residuals(learn.size());
    compute_residuals(
            learn, assignments,
            std::span<const float>(
                    coarse->get_xb(), nlist * dimensions),
            dimensions, residuals);
    learn.clear();
    learn.shrink_to_fit();

    faiss::OPQMatrix opq(
            static_cast<int>(dimensions),
            static_cast<int>(subquantizers));
    opq.niter = 1;
    opq.niter_pq_0 = static_cast<int>(pq_iterations);
    opq.niter_pq = static_cast<int>(pq_iterations);
    const double cpu_start = cpu_seconds();
    const auto wall_start = std::chrono::steady_clock::now();
    opq.train(learn_rows, residuals.data());
    const double cpu = cpu_seconds() - cpu_start;
    const double wall = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - wall_start).count();
    if (!opq.is_trained || !opq.is_orthonormal)
        throw std::runtime_error("probe OPQ training");

    std::ofstream record(output, std::ios::trunc);
    record << "dimensions\tnlist\tM\tlearn_rows\topq_niter"
              "\tniter_pq_0\tniter_pq\tcpu_seconds\twall_seconds"
              "\tpeak_rss_bytes\n";
    record << std::setprecision(17)
           << dimensions << '\t' << nlist << '\t' << subquantizers
           << '\t' << learn_rows << "\t1\t" << pq_iterations
           << '\t' << pq_iterations << '\t'
           << cpu << '\t' << wall << '\t' << peak_rss_bytes() << '\n';
    if (!record)
        throw std::runtime_error("write OPQ probe");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: structured_2d_probe_opq_cost "
                    "<nlist> <M> <pq_iterations:{1,4,40}> "
                    "<common_directory> <output_tsv>");
        run(
                std::stoull(argv[1]), std::stoull(argv[2]),
                std::stoull(argv[3]), argv[4], argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_probe_opq_cost: "
                  << error.what() << '\n';
        return 1;
    }
}

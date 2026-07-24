#include "faiss_pool.hpp"

#include "dataset_io.hpp"

#include <faiss/IndexIVF.h>
#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFFlat.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/IndexIVFPQFastScan.h>
#include <faiss/IndexIVFRaBitQ.h>
#include <faiss/IndexIVFRaBitQFastScan.h>
#include <faiss/impl/ProductQuantizer.h>
#include <faiss/index_io.h>
#include <faiss/invlists/InvertedLists.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <tuple>

namespace structured2d::admission {
namespace {

double process_cpu_seconds() {
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

struct Timing {
    double train_cpu = 0;
    double train_wall = 0;
    double add_cpu = 0;
    double add_wall = 0;
    double write_cpu = 0;
    double write_wall = 0;
    double load_cpu = 0;
    double load_wall = 0;
};

struct Clock {
    double cpu = process_cpu_seconds();
    std::chrono::steady_clock::time_point wall =
            std::chrono::steady_clock::now();
};

std::pair<double, double> elapsed(const Clock& start) {
    return {
            process_cpu_seconds() - start.cpu,
            std::chrono::duration<double>(
                    std::chrono::steady_clock::now() -
                    start.wall).count()};
}

std::pair<std::size_t, std::size_t> parse_m_bits(
        const std::string& id) {
    const std::size_t marker = id.rfind("_M");
    const std::size_t separator =
            marker == std::string::npos
            ? std::string::npos
            : id.find('X', marker + 2);
    if (marker == std::string::npos ||
        separator == std::string::npos)
        throw std::invalid_argument("PQ arm id");
    const std::size_t subquantizers =
            std::stoull(id.substr(
                    marker + 2, separator - marker - 2));
    const std::size_t bits =
            std::stoull(id.substr(separator + 1));
    return {subquantizers, bits};
}

void configure_product_quantizer(
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

void configure_fast_scan(faiss::IndexIVFFastScan& index) {
    index.implem = 0;
    index.qbs = 0;
    index.qbs2 = 0;
    index.parallel_mode = 0;
    index.skip = 0;
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

void require_vector_shape(
        std::span<const float> vectors,
        std::size_t rows, std::size_t dimensions) {
    if (rows == 0 || dimensions == 0 ||
        vectors.size() != rows * dimensions ||
        !std::all_of(
                vectors.begin(), vectors.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("native arm vector shape");
}

void write_record(
        const NativeBuildSpec& spec, const Timing& timing,
        std::uint64_t serialized_bytes,
        std::uint64_t coarse_bytes) {
    const auto record_path =
            spec.output_index.string() + ".resources.tsv";
    std::ofstream output(record_path, std::ios::trunc);
    output << "arm_id\tdimensions\tnlist\tlearn_rows\tbase_rows"
              "\tserialized_bytes\tcommon_coarse_bytes"
              "\tcommon_id_bytes\tpacked_code_bytes_per_vector"
              "\ttrain_cpu_seconds\ttrain_wall_seconds"
              "\tadd_cpu_seconds\tadd_wall_seconds"
              "\twrite_cpu_seconds\twrite_wall_seconds"
              "\tload_cpu_seconds\tload_wall_seconds"
              "\tpeak_rss_bytes\n";
    const double code_bytes =
            spec.arm.kind == FaissArmKind::IvfFlat
            ? spec.arm.dimensions * sizeof(float)
            : spec.arm.kind == FaissArmKind::IvfPq ||
                            spec.arm.kind ==
                                    FaissArmKind::IvfPqFastScan
            ? static_cast<double>(
                      spec.arm.subquantizers * spec.arm.bits) /
                    8
            : static_cast<double>(
                      spec.arm.dimensions * spec.arm.bits) /
                    8;
    output << std::setprecision(17)
           << spec.arm.id << '\t' << spec.arm.dimensions << '\t'
           << spec.arm.nlist << '\t' << spec.learn_rows << '\t'
           << spec.base_rows << '\t' << serialized_bytes << '\t'
           << coarse_bytes << '\t'
           << spec.base_rows * sizeof(faiss::idx_t) << '\t'
           << code_bytes << '\t'
           << timing.train_cpu << '\t' << timing.train_wall << '\t'
           << timing.add_cpu << '\t' << timing.add_wall << '\t'
           << timing.write_cpu << '\t' << timing.write_wall << '\t'
           << timing.load_cpu << '\t' << timing.load_wall << '\t'
           << peak_rss_bytes() << '\n';
    output.close();
    if (!output) throw std::runtime_error("write native arm record");
}

}  // namespace

FaissArmConfig parse_native_faiss_arm(
        const std::string& id, std::size_t dimensions,
        std::size_t nlist) {
    if (dimensions == 0 || nlist == 0)
        throw std::invalid_argument("native Faiss arm shape");
    FaissArmConfig result{id, {}, dimensions, nlist, 0, 0};
    if (id == "IVFFLAT") {
        result.kind = FaissArmKind::IvfFlat;
    } else if (
            id.rfind("PQFULL_M", 0) == 0 ||
            id.rfind("PQ128_M", 0) == 0) {
        result.kind = FaissArmKind::IvfPq;
        std::tie(result.subquantizers, result.bits) =
                parse_m_bits(id);
    } else if (id.rfind("PQFSFULL_M", 0) == 0) {
        result.kind = FaissArmKind::IvfPqFastScan;
        std::tie(result.subquantizers, result.bits) =
                parse_m_bits(id);
    } else if (id.rfind("RABITQFS_B", 0) == 0) {
        result.kind = FaissArmKind::IvfRaBitQFastScan;
        result.bits = std::stoull(id.substr(10));
    } else if (id.rfind("RABITQ_B", 0) == 0) {
        result.kind = FaissArmKind::IvfRaBitQ;
        result.bits = std::stoull(id.substr(8));
    } else {
        throw std::invalid_argument("not a native Faiss arm");
    }
    if ((result.kind == FaissArmKind::IvfPq ||
         result.kind == FaissArmKind::IvfPqFastScan) &&
        (result.subquantizers == 0 ||
         dimensions % result.subquantizers != 0 ||
         (result.bits != 4 && result.bits != 8)))
        throw std::invalid_argument("invalid PQ configuration");
    if (result.kind == FaissArmKind::IvfPqFastScan &&
        result.bits != 4)
        throw std::invalid_argument("FastScan requires four bits");
    if ((result.kind == FaissArmKind::IvfRaBitQ ||
         result.kind == FaissArmKind::IvfRaBitQFastScan) &&
        (result.bits < 1 || result.bits > 4))
        throw std::invalid_argument("invalid RaBitQ bits");
    return result;
}

std::unique_ptr<faiss::IndexIVF> make_native_faiss_arm(
        const FaissArmConfig& config, faiss::IndexFlatL2* coarse,
        std::size_t learn_rows) {
    if (coarse == nullptr ||
        coarse->d != static_cast<int>(config.dimensions) ||
        coarse->ntotal != static_cast<faiss::idx_t>(config.nlist))
        throw std::invalid_argument("native arm coarse index");
    std::unique_ptr<faiss::IndexIVF> result;
    if (config.kind == FaissArmKind::IvfFlat) {
        result = std::make_unique<faiss::IndexIVFFlat>(
                coarse, config.dimensions, config.nlist,
                faiss::METRIC_L2);
    } else if (config.kind == FaissArmKind::IvfPq) {
        auto index = std::make_unique<faiss::IndexIVFPQ>(
                coarse, config.dimensions, config.nlist,
                config.subquantizers, config.bits,
                faiss::METRIC_L2);
        configure_product_quantizer(index->pq, learn_rows);
        index->use_precomputed_table = 0;
        result = std::move(index);
    } else if (config.kind == FaissArmKind::IvfPqFastScan) {
        auto index = std::make_unique<faiss::IndexIVFPQFastScan>(
                coarse, config.dimensions, config.nlist,
                config.subquantizers, config.bits,
                faiss::METRIC_L2, 32);
        configure_product_quantizer(index->pq, learn_rows);
        index->use_precomputed_table = 0;
        configure_fast_scan(*index);
        result = std::move(index);
    } else if (config.kind == FaissArmKind::IvfRaBitQ) {
        auto index = std::make_unique<faiss::IndexIVFRaBitQ>(
                coarse, config.dimensions, config.nlist,
                faiss::METRIC_L2, true,
                static_cast<std::uint8_t>(config.bits));
        index->qb = 4;
        result = std::move(index);
    } else {
        auto index =
                std::make_unique<faiss::IndexIVFRaBitQFastScan>(
                        coarse, config.dimensions, config.nlist,
                        faiss::METRIC_L2, 32, true,
                        static_cast<std::uint8_t>(config.bits));
        index->qb = 8;
        index->centered = false;
        configure_fast_scan(*index);
        result = std::move(index);
    }
    result->own_fields = false;
    result->parallel_mode = 0;
    return result;
}

void train_native_faiss_arm(
        faiss::IndexIVF& index,
        std::span<const float> transformed_learn,
        std::span<const std::uint32_t> assignments,
        std::size_t dimensions) {
    require_vector_shape(
            transformed_learn,
            transformed_learn.size() / dimensions, dimensions);
    const std::size_t rows =
            transformed_learn.size() / dimensions;
    if (index.d != static_cast<int>(dimensions) ||
        assignments.size() != rows)
        throw std::invalid_argument("native arm train dimension");
    if (dynamic_cast<faiss::IndexIVFFlat*>(&index) == nullptr) {
        const auto labels = widen(assignments);
        std::vector<float> residuals(transformed_learn.size());
        index.quantizer->compute_residual_n(
                static_cast<faiss::idx_t>(rows),
                transformed_learn.data(), residuals.data(),
                labels.data());
        index.train_encoder(
                static_cast<faiss::idx_t>(rows),
                residuals.data(), labels.data());
        index.is_trained = true;
    }
    if (!index.is_trained)
        throw std::runtime_error("native arm not trained");
}

void add_native_faiss_arm(
        faiss::IndexIVF& index,
        std::span<const float> transformed_base,
        std::span<const std::uint32_t> assignments,
        std::size_t dimensions) {
    require_vector_shape(
            transformed_base, assignments.size(), dimensions);
    if (!index.is_trained || index.ntotal != 0)
        throw std::invalid_argument("native arm add state");
    const auto labels = widen(assignments);
    std::vector<faiss::idx_t> ids(assignments.size());
    for (std::size_t row = 0; row < ids.size(); ++row)
        ids[row] = static_cast<faiss::idx_t>(row);
    if (dynamic_cast<faiss::IndexIVFFastScan*>(&index) != nullptr) {
        index.add_with_ids(
                static_cast<faiss::idx_t>(ids.size()),
                transformed_base.data(), ids.data());
    } else {
        index.add_core(
                static_cast<faiss::idx_t>(ids.size()),
                transformed_base.data(), ids.data(), labels.data());
    }
    if (index.ntotal != static_cast<faiss::idx_t>(ids.size()))
        throw std::runtime_error("native arm added row count");
}

void verify_native_faiss_layout(
        const faiss::IndexIVF& index,
        std::span<const std::uint32_t> assignments) {
    if (index.invlists == nullptr ||
        index.ntotal !=
                static_cast<faiss::idx_t>(assignments.size()))
        throw std::invalid_argument("native layout state");
    std::vector<std::vector<faiss::idx_t>> expected(index.nlist);
    for (std::size_t row = 0; row < assignments.size(); ++row) {
        if (assignments[row] >= index.nlist)
            throw std::out_of_range("native layout assignment");
        expected[assignments[row]].push_back(
                static_cast<faiss::idx_t>(row));
    }
    std::size_t total = 0;
    for (std::size_t list = 0; list < index.nlist; ++list) {
        const std::size_t size = index.invlists->list_size(list);
        if (size != expected[list].size())
            throw std::runtime_error("native list size parity");
        faiss::InvertedLists::ScopedIds ids(
                index.invlists, list);
        if (!std::equal(
                    expected[list].begin(),
                    expected[list].end(), ids.get()))
            throw std::runtime_error("native list ID/order parity");
        total += size;
    }
    if (total != assignments.size())
        throw std::runtime_error("native layout total");
}

void build_native_faiss_arm(const NativeBuildSpec& spec) {
    if (spec.learn_rows == 0 || spec.base_rows == 0 ||
        spec.arm.dimensions == 0 ||
        std::filesystem::exists(spec.output_index) ||
        std::filesystem::exists(
                spec.output_index.string() + ".resources.tsv"))
        throw std::invalid_argument("native build spec");
    const auto nlist_dir =
            spec.common_directory /
            ("nlist_" + std::to_string(spec.arm.nlist));
    const std::string coarse_path =
            (nlist_dir / "coarse.faiss").string();
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index(coarse_path.c_str()));
    auto* coarse =
            dynamic_cast<faiss::IndexFlatL2*>(coarse_owner.get());
    if (coarse == nullptr)
        throw std::runtime_error("native coarse type");
    const auto assignments = read_u32(
            nlist_dir / "base_assignments.u32",
            spec.base_rows);

    std::vector<float> learn;
    std::vector<std::uint32_t> learn_assignments;
    if (spec.arm.kind != FaissArmKind::IvfFlat) {
        FvecsReader reader(
                spec.common_directory / "learn_pca.fvecs",
                spec.learn_rows, spec.arm.dimensions);
        learn = read_all(reader);
        learn_assignments = read_u32(
                nlist_dir / "learn_assignments.u32",
                spec.learn_rows);
    }

    auto index = make_native_faiss_arm(
            spec.arm, coarse, spec.learn_rows);
    Timing timing;
    if (spec.arm.kind != FaissArmKind::IvfFlat) {
        const Clock start;
        train_native_faiss_arm(
                *index, learn, learn_assignments,
                spec.arm.dimensions);
        std::tie(timing.train_cpu, timing.train_wall) =
                elapsed(start);
    }
    FvecsReader base_reader(
            spec.common_directory / "base_pca.fvecs",
            spec.base_rows, spec.arm.dimensions);
    const auto base = read_all(base_reader);
    {
        const Clock start;
        add_native_faiss_arm(
                *index, base, assignments, spec.arm.dimensions);
        verify_native_faiss_layout(*index, assignments);
        std::tie(timing.add_cpu, timing.add_wall) =
                elapsed(start);
    }
    {
        const Clock start;
        faiss::write_index(index.get(),
                           spec.output_index.c_str());
        std::tie(timing.write_cpu, timing.write_wall) =
                elapsed(start);
    }
    const std::uint64_t serialized_bytes =
            std::filesystem::file_size(spec.output_index);
    {
        const Clock start;
        std::unique_ptr<faiss::Index> loaded_owner(
                faiss::read_index(spec.output_index.c_str()));
        auto* loaded =
                dynamic_cast<faiss::IndexIVF*>(
                        loaded_owner.get());
        if (loaded == nullptr)
            throw std::runtime_error("loaded native arm type");
        verify_native_faiss_layout(*loaded, assignments);
        std::tie(timing.load_cpu, timing.load_wall) =
                elapsed(start);
    }
    write_record(
            spec, timing, serialized_bytes,
            std::filesystem::file_size(coarse_path));
}

}  // namespace structured2d::admission

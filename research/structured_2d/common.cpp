#include "common.hpp"

#include "dataset_io.hpp"

#include <faiss/Clustering.h>
#include <faiss/IndexFlat.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>

namespace structured2d::admission {
namespace {

constexpr std::array<std::size_t, 2> kNlists{1024, 4096};
constexpr std::size_t kSyntheticQueries = 64;

std::uint64_t splitmix64_next(std::uint64_t& state) {
    state += 0x9e3779b97f4a7c15ULL;
    std::uint64_t value = state;
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

double open_unit(std::uint64_t bits) {
    constexpr double scale = 0x1.0p-53;
    return (static_cast<double>(bits >> 11) + 0.5) * scale;
}

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

struct StageRecord {
    std::string stage;
    double cpu_seconds = 0;
    double wall_seconds = 0;
    std::uint64_t peak_rss = 0;
};

class StageTimer {
  public:
    StageTimer(std::vector<StageRecord>& records, std::string stage)
            : records_(records),
              stage_(std::move(stage)),
              cpu_start_(process_cpu_seconds()),
              wall_start_(std::chrono::steady_clock::now()) {}

    ~StageTimer() {
        const auto wall_end = std::chrono::steady_clock::now();
        records_.push_back({
                stage_,
                process_cpu_seconds() - cpu_start_,
                std::chrono::duration<double>(
                        wall_end - wall_start_).count(),
                peak_rss_bytes()});
    }

  private:
    std::vector<StageRecord>& records_;
    std::string stage_;
    double cpu_start_;
    std::chrono::steady_clock::time_point wall_start_;
};

void require_shape(
        std::span<const float> vectors, std::size_t dimensions) {
    if (dimensions == 0 || vectors.empty() ||
        vectors.size() % dimensions != 0)
        throw std::invalid_argument("vector shape");
    if (!std::all_of(
                vectors.begin(), vectors.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::runtime_error("non-finite vector");
}

std::filesystem::path nlist_directory(
        const std::filesystem::path& root, std::size_t nlist) {
    return root / ("nlist_" + std::to_string(nlist));
}

void write_u64(
        const std::filesystem::path& path,
        std::span<const std::uint64_t> values) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output.write(
            reinterpret_cast<const char*>(values.data()),
            values.size_bytes());
    output.close();
    if (!output ||
        std::filesystem::file_size(path) != values.size_bytes())
        throw std::runtime_error("write u64");
}

void write_stage_records(
        const std::filesystem::path& path,
        std::span<const StageRecord> records) {
    std::ofstream output(path, std::ios::trunc);
    output << "stage\tcpu_seconds\twall_seconds\tpeak_rss_bytes\n";
    output << std::setprecision(17);
    for (const auto& record : records)
        output << record.stage << '\t' << record.cpu_seconds << '\t'
               << record.wall_seconds << '\t' << record.peak_rss << '\n';
    output.close();
    if (!output) throw std::runtime_error("write stage records");
}

void verify_transform_round_trip(
        const faiss::PCAMatrix& pca,
        std::span<const float> original,
        std::span<const float> transformed,
        std::size_t dimensions) {
    const std::size_t rows =
            std::min<std::size_t>(16, original.size() / dimensions);
    std::vector<float> loaded_output(rows * dimensions);
    std::vector<float> reconstructed(rows * dimensions);
    pca.apply_noalloc(
            static_cast<faiss::idx_t>(rows),
            original.data(), loaded_output.data());
    if (!std::equal(
                loaded_output.begin(), loaded_output.end(),
                transformed.begin()))
        throw std::runtime_error("PCA serialization parity");
    pca.reverse_transform(
            static_cast<faiss::idx_t>(rows),
            loaded_output.data(), reconstructed.data());
    for (std::size_t index = 0; index < reconstructed.size(); ++index) {
        const double tolerance =
                2e-4 * std::max(
                               1.0,
                               std::abs(
                                       static_cast<double>(
                                               original[index])));
        if (std::abs(reconstructed[index] - original[index]) > tolerance)
            throw std::runtime_error("PCA round-trip");
    }
}

}  // namespace

CoordinateMoments coordinate_moments(
        std::span<const float> vectors, std::size_t dimensions) {
    require_shape(vectors, dimensions);
    const std::size_t rows = vectors.size() / dimensions;
    CoordinateMoments result;
    result.mean.assign(dimensions, 0);
    std::vector<long double> squared(dimensions, 0);
    for (std::size_t row = 0; row < rows; ++row) {
        const long double count = row + 1;
        for (std::size_t dimension = 0;
             dimension < dimensions; ++dimension) {
            const double value = vectors[row * dimensions + dimension];
            const double delta = value - result.mean[dimension];
            result.mean[dimension] += delta / count;
            squared[dimension] +=
                    delta * (value - result.mean[dimension]);
        }
    }
    result.standard_deviation.resize(dimensions);
    for (std::size_t dimension = 0;
         dimension < dimensions; ++dimension) {
        const long double variance = squared[dimension] / rows;
        if (!std::isfinite(static_cast<double>(variance)) ||
            variance < 0)
            throw std::runtime_error("coordinate variance");
        result.standard_deviation[dimension] =
                std::sqrt(static_cast<double>(variance));
    }
    return result;
}

std::vector<float> deterministic_synthetic_queries(
        Dataset dataset, const CoordinateMoments& moments,
        const faiss::PCAMatrix& pca, std::size_t count) {
    const std::size_t dimensions = moments.mean.size();
    if (count == 0 || dimensions == 0 ||
        moments.standard_deviation.size() != dimensions ||
        pca.d_in != static_cast<int>(dimensions) ||
        pca.d_out != static_cast<int>(dimensions) ||
        !pca.is_trained || !pca.is_orthonormal)
        throw std::invalid_argument("synthetic query inputs");
    std::vector<float> transformed(count * dimensions);
    constexpr double two_pi =
            6.283185307179586476925286766559;
    for (std::size_t query = 0; query < count; ++query) {
        auto seed_words = synthetic_seed_words(dataset, query);
        std::uint64_t state =
                seed_words[0] ^ std::rotl(seed_words[1], 17) ^
                std::rotl(seed_words[2], 31) ^
                std::rotl(seed_words[3], 47);
        for (std::size_t dimension = 0;
             dimension < dimensions; dimension += 2) {
            const double u1 = open_unit(splitmix64_next(state));
            const double u2 = open_unit(splitmix64_next(state));
            const double radius = std::sqrt(-2 * std::log(u1));
            const double angle = two_pi * u2;
            const std::array<double, 2> normal{
                    radius * std::cos(angle),
                    radius * std::sin(angle)};
            for (std::size_t offset = 0;
                 offset < 2 && dimension + offset < dimensions;
                 ++offset) {
                const std::size_t coordinate = dimension + offset;
                const double value = moments.mean[coordinate] +
                        moments.standard_deviation[coordinate] *
                                normal[offset];
                if (!std::isfinite(value) ||
                    std::abs(value) >
                            std::numeric_limits<float>::max())
                    throw std::runtime_error("synthetic query value");
                transformed[query * dimensions + coordinate] =
                        static_cast<float>(value);
            }
        }
    }
    std::vector<float> original(transformed.size());
    pca.reverse_transform(
            static_cast<faiss::idx_t>(count),
            transformed.data(), original.data());
    require_shape(original, dimensions);
    std::vector<float> replay(transformed.size());
    pca.apply_noalloc(
            static_cast<faiss::idx_t>(count),
            original.data(), replay.data());
    for (std::size_t index = 0; index < replay.size(); ++index) {
        const double reference = transformed[index];
        const double tolerance =
                2e-4 * std::max(1.0, std::abs(reference));
        if (!std::isfinite(replay[index]) ||
            std::abs(replay[index] - reference) > tolerance)
            throw std::runtime_error("synthetic PCA round-trip");
    }
    return original;
}

std::unique_ptr<faiss::PCAMatrix> train_full_pca(
        std::span<const float> learn, std::size_t dimensions) {
    require_shape(learn, dimensions);
    auto pca = std::make_unique<faiss::PCAMatrix>(
            static_cast<int>(dimensions),
            static_cast<int>(dimensions), 0, false);
    pca->train(
            static_cast<faiss::idx_t>(learn.size() / dimensions),
            learn.data());
    if (!pca->is_trained || !pca->is_orthonormal)
        throw std::runtime_error("non-orthonormal PCA");
    return pca;
}

std::unique_ptr<faiss::IndexFlatL2> train_coarse(
        std::span<const float> transformed_learn,
        std::size_t dimensions, std::size_t nlist) {
    require_shape(transformed_learn, dimensions);
    const std::size_t rows = transformed_learn.size() / dimensions;
    if (nlist == 0 || rows < nlist)
        throw std::invalid_argument("coarse shape");
    faiss::ClusteringParameters parameters;
    parameters.seed = 1234;
    parameters.niter = 25;
    parameters.nredo = 1;
    parameters.spherical = false;
    parameters.max_points_per_centroid =
            static_cast<int>((rows + nlist - 1) / nlist);
    auto coarse = std::make_unique<faiss::IndexFlatL2>(
            static_cast<faiss::idx_t>(dimensions));
    faiss::Clustering clustering(
            static_cast<int>(dimensions),
            static_cast<int>(nlist), parameters);
    clustering.train(
            static_cast<faiss::idx_t>(rows),
            transformed_learn.data(), *coarse);
    if (coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("coarse centroid count");
    return coarse;
}

std::vector<std::uint32_t> assign_lists(
        const faiss::IndexFlatL2& coarse,
        std::span<const float> vectors, std::size_t dimensions) {
    require_shape(vectors, dimensions);
    if (coarse.d != static_cast<int>(dimensions) ||
        coarse.ntotal <= 0 ||
        coarse.ntotal >
                static_cast<faiss::idx_t>(
                        std::numeric_limits<std::uint32_t>::max()))
        throw std::invalid_argument("coarse index");
    const std::size_t rows = vectors.size() / dimensions;
    std::vector<float> distances(rows);
    std::vector<faiss::idx_t> labels(rows);
    coarse.search(
            static_cast<faiss::idx_t>(rows), vectors.data(), 1,
            distances.data(), labels.data());
    std::vector<std::uint32_t> result(rows);
    for (std::size_t row = 0; row < rows; ++row) {
        if (!std::isfinite(distances[row]) || labels[row] < 0 ||
            labels[row] >= coarse.ntotal)
            throw std::runtime_error("invalid coarse assignment");
        result[row] = static_cast<std::uint32_t>(labels[row]);
    }
    return result;
}

std::vector<std::uint64_t> count_lists(
        std::span<const std::uint32_t> assignments,
        std::size_t nlist) {
    if (assignments.empty() || nlist == 0)
        throw std::invalid_argument("list counts");
    std::vector<std::uint64_t> result(nlist);
    for (std::uint32_t assignment : assignments) {
        if (assignment >= nlist)
            throw std::out_of_range("list assignment");
        ++result[assignment];
    }
    return result;
}

void prepare_common_state(const DatasetBuildSpec& spec) {
    if (spec.dimensions == 0 || spec.learn_rows == 0 ||
        spec.base_rows == 0 || spec.block_rows == 0 ||
        std::filesystem::exists(spec.output_directory))
        throw std::invalid_argument("dataset build spec");
    std::filesystem::create_directories(spec.output_directory);
    for (std::size_t nlist : kNlists)
        std::filesystem::create_directories(
                nlist_directory(spec.output_directory, nlist));

    std::vector<StageRecord> records;
    FvecsReader learn_reader(
            spec.learn_path, spec.learn_rows, spec.dimensions);
    std::vector<float> learn;
    {
        StageTimer timer(records, "read_learn");
        learn = read_all(learn_reader);
    }

    std::unique_ptr<faiss::PCAMatrix> pca;
    {
        StageTimer timer(records, "train_pca");
        pca = train_full_pca(learn, spec.dimensions);
    }
    std::vector<float> transformed_learn(learn.size());
    {
        StageTimer timer(records, "transform_learn");
        pca->apply_noalloc(
                static_cast<faiss::idx_t>(spec.learn_rows),
                learn.data(), transformed_learn.data());
    }
    {
        StageTimer timer(records, "serialize_pca_and_learn");
        const std::string pca_path =
                (spec.output_directory / "pca.faiss").string();
        faiss::write_VectorTransform(pca.get(), pca_path.c_str());
        FvecsWriter writer(
                spec.output_directory / "learn_pca.fvecs",
                spec.dimensions);
        writer.write(transformed_learn);
        writer.close();
    }

    std::array<std::unique_ptr<faiss::IndexFlatL2>, 2> coarse;
    std::array<std::vector<std::uint32_t>, 2> learn_assignments;
    for (std::size_t index = 0; index < kNlists.size(); ++index) {
        const std::size_t nlist = kNlists[index];
        {
            StageTimer timer(
                    records, "train_coarse_" + std::to_string(nlist));
            coarse[index] =
                    train_coarse(
                            transformed_learn, spec.dimensions, nlist);
        }
        {
            StageTimer timer(
                    records,
                    "assign_learn_" + std::to_string(nlist));
            learn_assignments[index] = assign_lists(
                    *coarse[index], transformed_learn,
                    spec.dimensions);
            const auto directory =
                    nlist_directory(spec.output_directory, nlist);
            write_u32(
                    directory / "learn_assignments.u32",
                    learn_assignments[index]);
            const std::string coarse_path =
                    (directory / "coarse.faiss").string();
            faiss::write_index(coarse[index].get(), coarse_path.c_str());
        }
    }

    std::vector<float> synthetic_original;
    std::vector<float> synthetic_pca(
            kSyntheticQueries * spec.dimensions);
    {
        StageTimer timer(records, "generate_synthetic_queries");
        const auto moments =
                coordinate_moments(
                        transformed_learn, spec.dimensions);
        synthetic_original = deterministic_synthetic_queries(
                spec.dataset, moments, *pca, kSyntheticQueries);
        // Use one canonical per-query transform so latency and batch timing
        // cannot select different BLAS shapes and therefore different IVF
        // candidates near coarse-distance ties.
        for (std::size_t query = 0;
             query < kSyntheticQueries; ++query)
            pca->apply_noalloc(
                    1,
                    synthetic_original.data() +
                            query * spec.dimensions,
                    synthetic_pca.data() +
                            query * spec.dimensions);
        FvecsWriter original_writer(
                spec.output_directory / "synthetic_original.fvecs",
                spec.dimensions);
        original_writer.write(synthetic_original);
        original_writer.close();
        FvecsWriter pca_writer(
                spec.output_directory / "synthetic_pca.fvecs",
                spec.dimensions);
        pca_writer.write(synthetic_pca);
        pca_writer.close();
    }

    std::array<std::vector<std::uint32_t>, 2> base_assignments;
    for (auto& assignments : base_assignments)
        assignments.resize(spec.base_rows);
    {
        StageTimer timer(records, "transform_and_assign_base");
        FvecsReader base_reader(
                spec.base_path, spec.base_rows, spec.dimensions);
        FvecsWriter base_writer(
                spec.output_directory / "base_pca.fvecs",
                spec.dimensions);
        std::vector<float> original(
                spec.block_rows * spec.dimensions);
        std::vector<float> transformed(original.size());
        std::size_t offset = 0;
        while (offset < spec.base_rows) {
            const std::size_t requested =
                    std::min(spec.block_rows, spec.base_rows - offset);
            const std::size_t count = base_reader.read(
                    std::span<float>(
                            original.data(),
                            requested * spec.dimensions));
            if (count != requested)
                throw std::runtime_error("short base read");
            const std::size_t values = count * spec.dimensions;
            pca->apply_noalloc(
                    static_cast<faiss::idx_t>(count),
                    original.data(), transformed.data());
            base_writer.write(
                    std::span<const float>(
                            transformed.data(), values));
            for (std::size_t index = 0;
                 index < kNlists.size(); ++index) {
                auto block_assignments = assign_lists(
                        *coarse[index],
                        std::span<const float>(
                                transformed.data(), values),
                        spec.dimensions);
                std::copy(
                        block_assignments.begin(),
                        block_assignments.end(),
                        base_assignments[index].begin() + offset);
            }
            offset += count;
        }
        base_writer.close();
    }

    for (std::size_t index = 0; index < kNlists.size(); ++index) {
        const std::size_t nlist = kNlists[index];
        StageTimer timer(
                records, "serialize_assignments_" +
                        std::to_string(nlist));
        const auto directory =
                nlist_directory(spec.output_directory, nlist);
        write_u32(
                directory / "base_assignments.u32",
                base_assignments[index]);
        const auto sizes =
                count_lists(base_assignments[index], nlist);
        write_u64(directory / "list_sizes.u64", sizes);

        const std::size_t max_probe = frozen_nprobes(nlist).back();
        std::vector<float> distances(
                kSyntheticQueries * max_probe);
        std::vector<faiss::idx_t> labels(
                kSyntheticQueries * max_probe);
        for (std::size_t query = 0;
             query < kSyntheticQueries; ++query)
            coarse[index]->search(
                    1,
                    synthetic_pca.data() +
                            query * spec.dimensions,
                    static_cast<faiss::idx_t>(max_probe),
                    distances.data() + query * max_probe,
                    labels.data() + query * max_probe);
        std::vector<std::uint32_t> selected(labels.size());
        for (std::size_t item = 0; item < labels.size(); ++item) {
            if (labels[item] < 0 ||
                labels[item] >=
                        static_cast<faiss::idx_t>(nlist) ||
                !std::isfinite(distances[item]))
                throw std::runtime_error("synthetic coarse result");
            selected[item] =
                    static_cast<std::uint32_t>(labels[item]);
        }
        write_u32(
                directory / "synthetic_selected_lists.u32",
                selected);
        FvecsWriter distance_writer(
                directory / "synthetic_coarse_distances.fvecs",
                max_probe);
        distance_writer.write(distances);
        distance_writer.close();
    }

    {
        StageTimer timer(records, "load_parity");
        const std::string pca_path =
                (spec.output_directory / "pca.faiss").string();
        std::unique_ptr<faiss::VectorTransform> loaded_pca(
                faiss::read_VectorTransform(pca_path.c_str()));
        auto* loaded_matrix =
                dynamic_cast<faiss::PCAMatrix*>(loaded_pca.get());
        if (loaded_matrix == nullptr)
            throw std::runtime_error("loaded PCA type");
        verify_transform_round_trip(
                *loaded_matrix, learn, transformed_learn,
                spec.dimensions);
        for (std::size_t index = 0;
             index < kNlists.size(); ++index) {
            const std::string coarse_path =
                    (nlist_directory(
                             spec.output_directory, kNlists[index]) /
                     "coarse.faiss").string();
            std::unique_ptr<faiss::Index> loaded(
                    faiss::read_index(coarse_path.c_str()));
            auto* loaded_flat =
                    dynamic_cast<faiss::IndexFlatL2*>(loaded.get());
            if (loaded_flat == nullptr)
                throw std::runtime_error("loaded coarse type");
            const std::size_t rows =
                    std::min<std::size_t>(256, spec.learn_rows);
            const auto replay = assign_lists(
                    *loaded_flat,
                    std::span<const float>(
                            transformed_learn.data(),
                            rows * spec.dimensions),
                    spec.dimensions);
            if (!std::equal(
                        replay.begin(), replay.end(),
                        learn_assignments[index].begin()))
                throw std::runtime_error(
                        "coarse assignment load parity");
        }
    }
    write_stage_records(
            spec.output_directory / "common_build_resources.tsv",
            records);
}

}  // namespace structured2d::admission

#include "admission.hpp"
#include "dataset_io.hpp"
#include "full_index.hpp"
#include "synthetic_timing.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVF.h>
#include <faiss/IndexIVFFastScan.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/VectorTransform.h>
#include <faiss/index_io.h>
#include <omp.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <utility>
#include <vector>

namespace {

constexpr std::size_t kSyntheticQueries = 64;
constexpr std::size_t kTopK = 100;

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

struct Clock {
    double cpu = cpu_seconds();
    std::chrono::steady_clock::time_point wall =
            std::chrono::steady_clock::now();
};

struct Elapsed {
    double cpu = 0;
    double wall = 0;
};

Elapsed elapsed(const Clock& start) {
    return {
            cpu_seconds() - start.cpu,
            std::chrono::duration<double>(
                    std::chrono::steady_clock::now() -
                    start.wall).count()};
}

struct Pass {
    Elapsed transform;
    Elapsed coarse;
    Elapsed scan;
    std::uint64_t candidates = 0;
    std::uint64_t output_hash = 0;
    std::uint64_t recall_hits = 0;
    std::vector<double> query_cpu_seconds;
    std::vector<double> query_wall_seconds;

    Elapsed total() const {
        return {
                transform.cpu + coarse.cpu + scan.cpu,
                transform.wall + coarse.wall + scan.wall};
    }
};

enum class Mode { Single, Batch12 };

std::string physical_id(
        const std::string& dataset, int budget,
        const std::string& logical) {
    const std::string suffix = budget == 32 ? "B4" : "B8";
    if (logical == "S128" || logical == "D128" ||
        logical == "V128")
        return logical + "_" + suffix;
    if (logical == "A128")
        return "A128_" + suffix;
    if (logical == "D128_FULL")
        return "D128_" + suffix;
    if (dataset == "sift" && logical == "PQ128_M32X8")
        return "PQFULL_M32X8";
    if (dataset == "sift" && logical == "PQ128_M64X8")
        return "PQFULL_M64X8";
    if (logical == "OPQ128_M32X8")
        return dataset == "sift"
                ? "OPQFULL_M32X8"
                : "OPQHEAD_M32X8";
    if (logical == "OPQ128_M64X8")
        return dataset == "sift"
                ? "OPQFULL_M64X8"
                : "OPQHEAD_M64X8";
    return logical;
}

std::filesystem::path artifact_path(
        const std::filesystem::path& directory,
        const std::string& id) {
    return directory /
            (id + (id.rfind("S128_", 0) == 0 ? ".s2d" : ".faiss"));
}

std::vector<std::uint16_t> read_radices(
        const std::filesystem::path& path,
        std::size_t expected) {
    std::ifstream input(path, std::ios::binary);
    std::vector<std::uint16_t> result(expected);
    input.read(
            reinterpret_cast<char*>(result.data()),
            static_cast<std::streamsize>(
                    result.size() * sizeof(std::uint16_t)));
    if (!input ||
        input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("D radix file");
    return result;
}

struct MixedShape {
    std::vector<std::uint16_t> radices;
    std::vector<std::uint16_t> used_states;
};

MixedShape read_mixed_shape(
        const std::filesystem::path& path,
        std::size_t expected) {
    std::ifstream input(path, std::ios::binary);
    MixedShape result;
    result.radices.resize(expected);
    result.used_states.resize(expected);
    for (std::size_t group = 0; group < expected; ++group) {
        input.read(
                reinterpret_cast<char*>(
                        &result.radices[group]),
                sizeof(std::uint16_t));
        input.read(
                reinterpret_cast<char*>(
                        &result.used_states[group]),
                sizeof(std::uint16_t));
    }
    if (!input ||
        input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("mixed-radix shape file");
    return result;
}

struct State {
    std::string dataset;
    int budget = 0;
    std::string logical_id;
    std::string physical_id;
    std::size_t dimensions = 0;
    std::size_t nlist = 0;
    std::size_t nprobe = 0;
    std::size_t queries = 0;
    bool natural = false;
    Mode mode{};
    std::vector<float> original;
    std::vector<float> pca_queries;
    std::vector<float> coarse_distances;
    std::vector<faiss::idx_t> selected;
    std::vector<std::uint32_t> saved_all_selected;
    std::vector<std::uint32_t> saved_selected;
    std::vector<float> saved_all_coarse_distances;
    std::vector<float> saved_coarse_distances;
    std::vector<std::uint32_t> truth_sorted;
    std::unique_ptr<faiss::VectorTransform> pca;
    std::unique_ptr<faiss::Index> coarse_owner;
    faiss::IndexFlatL2* coarse = nullptr;
    std::unique_ptr<faiss::Index> index_owner;
    faiss::IndexIVF* ivf = nullptr;
    faiss::IndexIVFPQ* ivfpq = nullptr;
    faiss::IndexIVFFastScan* fastscan = nullptr;
    std::unique_ptr<faiss::VectorTransform> opq_owner;
    faiss::LinearTransform* opq = nullptr;
    structured2d::FullIndex s_index;
    std::vector<std::uint16_t> radices;
    std::vector<std::uint16_t> used_states;

    bool is_s() const {
        return logical_id == "S128";
    }
    bool is_d() const {
        return logical_id == "D128";
    }
    bool is_mixed() const {
        return logical_id == "A128" ||
                logical_id == "D128_FULL";
    }
    bool is_head_regular() const {
        return dataset == "gist" &&
                (logical_id == "V128" ||
                 logical_id.rfind("PQ128_", 0) == 0);
    }
    bool is_opq() const {
        return logical_id.rfind("OPQ", 0) == 0;
    }
    bool custom_scan() const {
        return is_s() || is_d() || is_mixed() ||
                is_head_regular() || is_opq();
    }
};

State load_state(
        const std::string& dataset, std::size_t nlist,
        int budget, const std::string& logical_id,
        std::size_t nprobe, Mode mode,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& query_path,
        const std::filesystem::path& selected_path,
        const std::filesystem::path& distance_path,
        std::size_t query_count) {
    if ((dataset != "sift" && dataset != "gist") ||
        (nlist != 1024 && nlist != 4096) ||
        (budget != 32 && budget != 64) ||
        nprobe == 0)
        throw std::invalid_argument("timing arguments");
    const auto frozen =
            structured2d::admission::frozen_nprobes(nlist);
    if (std::find(frozen.begin(), frozen.end(), nprobe) ==
        frozen.end())
        throw std::invalid_argument("timing nprobe");

    State state;
    state.dataset = dataset;
    state.budget = budget;
    state.logical_id = logical_id;
    state.physical_id =
            physical_id(dataset, budget, logical_id);
    state.dimensions = dataset == "sift" ? 128 : 960;
    state.nlist = nlist;
    state.nprobe = nprobe;
    state.queries = query_count;
    state.mode = mode;
    const auto common = admission_root / dataset;
    structured2d::admission::FvecsReader original_reader(
            query_path,
            state.queries, state.dimensions);
    state.original =
            structured2d::admission::read_all(original_reader);
    state.pca_queries.resize(state.queries * state.dimensions);
    state.coarse_distances.resize(state.queries * nprobe);
    state.selected.resize(state.queries * nprobe);
    state.pca = faiss::read_VectorTransform_up(
            (common / "pca.faiss").c_str());
    if (state.pca == nullptr || !state.pca->is_trained ||
        state.pca->d_in != static_cast<int>(state.dimensions) ||
        state.pca->d_out != static_cast<int>(state.dimensions))
        throw std::runtime_error("timing PCA");
    state.coarse_owner.reset(faiss::read_index(
            (common / ("nlist_" + std::to_string(nlist)) /
             "coarse.faiss")
                    .c_str()));
    state.coarse = dynamic_cast<faiss::IndexFlatL2*>(
            state.coarse_owner.get());
    if (state.coarse == nullptr ||
        state.coarse->d != static_cast<int>(state.dimensions) ||
        state.coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("timing coarse");
    state.saved_all_selected =
            structured2d::admission::read_u32(
                    selected_path,
                    state.queries * frozen.back());
    structured2d::admission::FvecsReader distance_reader(
            distance_path, state.queries, frozen.back());
    state.saved_all_coarse_distances =
            structured2d::admission::read_all(distance_reader);
    state.saved_selected.resize(state.queries * nprobe);
    state.saved_coarse_distances.resize(state.queries * nprobe);
    for (std::size_t query = 0; query < state.queries; ++query)
        std::copy_n(
                state.saved_all_selected.begin() +
                        query * frozen.back(),
                nprobe,
                state.saved_selected.begin() + query * nprobe);
    for (std::size_t query = 0; query < state.queries; ++query)
        std::copy_n(
                state.saved_all_coarse_distances.begin() +
                        query * frozen.back(),
                nprobe,
                state.saved_coarse_distances.begin() +
                        query * nprobe);

    const auto directory =
            pool_root / dataset /
            ("nlist_" + std::to_string(nlist));
    const auto artifact =
            artifact_path(directory, state.physical_id);
    if (state.is_s()) {
        state.s_index = structured2d::load_full_index(artifact);
        if (state.s_index.dimensions != state.dimensions)
            throw std::runtime_error("timing S dimensions");
    } else {
        state.index_owner.reset(
                faiss::read_index(artifact.c_str()));
        state.ivf = dynamic_cast<faiss::IndexIVF*>(
                state.index_owner.get());
        state.ivfpq = dynamic_cast<faiss::IndexIVFPQ*>(
                state.index_owner.get());
        state.fastscan =
                dynamic_cast<faiss::IndexIVFFastScan*>(
                        state.index_owner.get());
        if (state.ivf == nullptr ||
            state.ivf->nlist != nlist ||
            state.ivf->ntotal !=
                    static_cast<faiss::idx_t>(1000000))
            throw std::runtime_error("timing IVF");
        if ((state.is_d() || state.is_mixed() ||
             state.is_head_regular() ||
             state.is_opq()) &&
            state.ivfpq == nullptr)
            throw std::runtime_error("timing IVFPQ");
        if (state.is_d())
            state.radices = read_radices(
                    artifact.string() + ".radix.u16",
                    state.ivfpq->pq.M);
        if (state.logical_id == "A128") {
            auto shape = read_mixed_shape(
                    artifact.string() + ".shape.u16",
                    state.ivfpq->pq.M);
            state.radices = std::move(shape.radices);
            state.used_states = std::move(shape.used_states);
        } else if (state.logical_id == "D128_FULL") {
            state.radices = read_radices(
                    artifact.string() + ".radix.u16",
                    state.ivfpq->pq.M);
            state.used_states.assign(
                    state.ivfpq->pq.M,
                    static_cast<std::uint16_t>(
                            state.ivfpq->pq.ksub));
        }
        if (state.is_opq()) {
            state.opq_owner =
                    faiss::read_VectorTransform_up(
                            (artifact.string() + ".opq.faiss")
                                    .c_str());
            state.opq = dynamic_cast<faiss::LinearTransform*>(
                    state.opq_owner.get());
            if (state.opq == nullptr ||
                !state.opq->is_orthonormal)
                throw std::runtime_error("timing OPQ");
        }
    }
    if (state.fastscan != nullptr) {
        if (state.fastscan->bbs != 32 ||
            state.fastscan->implem != 0 ||
            state.fastscan->qbs != 0 ||
            state.fastscan->qbs2 != 0 ||
            state.fastscan->parallel_mode != 0 ||
            state.fastscan->skip != 0)
            throw std::runtime_error("FastScan frozen fields");
    }
    return state;
}

std::span<const float> full_centroids(const State& state) {
    return {
            state.coarse->get_xb(),
            state.nlist * state.dimensions};
}

structured2d::admission::TopKResult search_custom_one(
        const State& state, std::size_t query) {
    const auto query_vector = std::span<const float>(
            state.pca_queries.data() + query * state.dimensions,
            state.dimensions);
    const auto lists = std::span<const faiss::idx_t>(
            state.selected.data() + query * state.nprobe,
            state.nprobe);
    if (state.is_s()) {
        std::vector<std::uint32_t> narrow(lists.size());
        std::transform(
                lists.begin(), lists.end(), narrow.begin(),
                [](faiss::idx_t value) {
                    return static_cast<std::uint32_t>(value);
                });
        const auto result =
                structured2d::search_preassigned_validated(
                state.s_index, query_vector, narrow, kTopK);
        structured2d::admission::TopKResult converted;
        converted.candidates = result.candidates_scored;
        converted.ids.resize(result.hits.size());
        converted.distances.resize(result.hits.size());
        for (std::size_t index = 0;
             index < result.hits.size(); ++index) {
            converted.ids[index] =
                    static_cast<faiss::idx_t>(
                            result.hits[index].id);
            converted.distances[index] =
                    static_cast<float>(
                            result.hits[index].distance);
        }
        return converted;
    }
    const std::size_t tail_start =
            state.dataset == "gist" &&
                    (state.is_d() || state.is_mixed() ||
                     state.is_head_regular() ||
                     state.logical_id.rfind("OPQ128_", 0) == 0)
            ? 128
            : state.dimensions;
    if (state.is_d())
        return structured2d::admission::search_dyadic_lists(
                *state.ivfpq, state.radices, query_vector,
                full_centroids(state), state.dimensions,
                tail_start, lists, kTopK);
    if (state.is_mixed())
        return structured2d::admission::search_mixed_radix_lists(
                *state.ivfpq, state.radices, state.used_states,
                query_vector, full_centroids(state),
                state.dimensions, tail_start, lists, kTopK);
    return structured2d::admission::search_ivfpq_lists(
            *state.ivfpq, state.opq, query_vector,
            full_centroids(state), state.dimensions,
            tail_start, lists, kTopK);
}

std::vector<structured2d::admission::TopKResult>
scan_custom(State& state) {
    std::vector<structured2d::admission::TopKResult> results(
            state.queries);
    const bool parallel = state.mode == Mode::Batch12;
#pragma omp parallel for schedule(static) if (parallel)
    for (std::int64_t query = 0;
         query < static_cast<std::int64_t>(state.queries); ++query)
        results[query] = search_custom_one(
                state, static_cast<std::size_t>(query));
    return results;
}

std::vector<structured2d::admission::TopKResult>
scan_native(State& state) {
    if (state.ivf == nullptr)
        throw std::runtime_error("native IVF missing");
    faiss::IVFSearchParameters parameters;
    parameters.nprobe = state.nprobe;
    if (state.fastscan == nullptr)
        state.ivf->parallel_mode =
                state.mode == Mode::Batch12 ? 3 : 0;
    std::vector<float> distances(state.queries * kTopK);
    std::vector<faiss::idx_t> ids(state.queries * kTopK);
    if (state.mode == Mode::Batch12) {
        state.ivf->search_preassigned(
                state.queries, state.pca_queries.data(), kTopK,
                state.selected.data(),
                state.coarse_distances.data(),
                distances.data(), ids.data(), false,
                &parameters);
    } else {
        for (std::size_t query = 0; query < state.queries; ++query)
            state.ivf->search_preassigned(
                    1,
                    state.pca_queries.data() +
                            query * state.dimensions,
                    kTopK,
                    state.selected.data() +
                            query * state.nprobe,
                    state.coarse_distances.data() +
                            query * state.nprobe,
                    distances.data() + query * kTopK,
                    ids.data() + query * kTopK, false,
                    &parameters);
    }
    std::vector<structured2d::admission::TopKResult> results(
            state.queries);
    for (std::size_t query = 0; query < state.queries; ++query) {
        results[query].distances.assign(
                distances.begin() + query * kTopK,
                distances.begin() + (query + 1) * kTopK);
        results[query].ids.assign(
                ids.begin() + query * kTopK,
                ids.begin() + (query + 1) * kTopK);
        for (std::size_t probe = 0;
             probe < state.nprobe; ++probe)
            results[query].candidates +=
                    state.ivf->invlists->list_size(
                            state.selected[
                                    query * state.nprobe + probe]);
    }
    return results;
}

structured2d::admission::TopKResult scan_native_one(
        State& state, std::size_t query) {
    faiss::IVFSearchParameters parameters;
    parameters.nprobe = state.nprobe;
    std::vector<float> distances(kTopK);
    std::vector<faiss::idx_t> ids(kTopK);
    state.ivf->parallel_mode = 0;
    state.ivf->search_preassigned(
            1,
            state.pca_queries.data() + query * state.dimensions,
            kTopK,
            state.selected.data() + query * state.nprobe,
            state.coarse_distances.data() + query * state.nprobe,
            distances.data(), ids.data(), false, &parameters);
    structured2d::admission::TopKResult result;
    result.distances = std::move(distances);
    result.ids = std::move(ids);
    for (std::size_t probe = 0; probe < state.nprobe; ++probe)
        result.candidates += state.ivf->invlists->list_size(
                state.selected[query * state.nprobe + probe]);
    return result;
}

void check_preassignments(const State& state) {
    for (std::size_t index = 0;
         index < state.selected.size(); ++index) {
        if (state.selected[index] < 0 ||
            state.selected[index] >=
                    static_cast<faiss::idx_t>(state.nlist) ||
            state.selected[index] !=
                    static_cast<faiss::idx_t>(
                            state.saved_selected[index]) ||
            !std::isfinite(state.coarse_distances[index]) ||
            state.coarse_distances[index] !=
                    state.saved_coarse_distances[index])
            throw std::runtime_error(
                    "coarse parity at nprobe=" +
                    std::to_string(state.nprobe) +
                    " flat_index=" + std::to_string(index) +
                    " measured=" +
                    std::to_string(state.selected[index]) +
                    " saved=" +
                    std::to_string(state.saved_selected[index]));
    }
}

void check_preassignment_query(
        const State& state, std::size_t query) {
    const std::size_t first = query * state.nprobe;
    for (std::size_t probe = 0; probe < state.nprobe; ++probe) {
        const std::size_t index = first + probe;
        if (state.selected[index] < 0 ||
            state.selected[index] >=
                    static_cast<faiss::idx_t>(state.nlist) ||
            state.selected[index] !=
                    static_cast<faiss::idx_t>(
                            state.saved_selected[index]) ||
            !std::isfinite(state.coarse_distances[index]) ||
            state.coarse_distances[index] !=
                    state.saved_coarse_distances[index])
            throw std::runtime_error(
                    "natural coarse parity at query=" +
                    std::to_string(query) +
                    " nprobe=" + std::to_string(state.nprobe));
    }
}

std::uint64_t recall_hits(
        const State& state,
        std::span<const structured2d::admission::TopKResult> outputs) {
    if (state.truth_sorted.empty()) return 0;
    if (outputs.size() != state.queries ||
        state.truth_sorted.size() != state.queries * kTopK)
        throw std::runtime_error("recall shape");
    std::uint64_t hits = 0;
    for (std::size_t query = 0; query < state.queries; ++query) {
        if (outputs[query].ids.size() != kTopK)
            throw std::runtime_error("top-k result count");
        std::vector<faiss::idx_t> returned;
        returned.reserve(kTopK);
        for (std::size_t rank = 0; rank < kTopK; ++rank) {
            const faiss::idx_t id = outputs[query].ids[rank];
            if (id == -1) {
                if (!std::isinf(outputs[query].distances[rank]) ||
                    outputs[query].distances[rank] < 0)
                    throw std::runtime_error(
                            "invalid missing top-k slot");
                continue;
            }
            if (id < 0)
                throw std::runtime_error("negative returned ID");
            returned.push_back(id);
        }
        std::sort(returned.begin(), returned.end());
        if (std::adjacent_find(returned.begin(), returned.end()) !=
                    returned.end())
            throw std::runtime_error("invalid returned IDs");
        const auto truth_begin =
                state.truth_sorted.begin() + query * kTopK;
        const auto truth_end = truth_begin + kTopK;
        for (const faiss::idx_t id : returned)
            if (std::binary_search(
                        truth_begin, truth_end,
                        static_cast<std::uint32_t>(id)))
                ++hits;
    }
    return hits;
}

Pass run_natural_single(State& state) {
    Pass result;
    result.query_cpu_seconds.resize(state.queries);
    result.query_wall_seconds.resize(state.queries);
    std::vector<structured2d::admission::TopKResult> outputs(
            state.queries);
    for (std::size_t query = 0; query < state.queries; ++query) {
        const Clock total_clock;
        Clock phase_clock;
        state.pca->apply_noalloc(
                1,
                state.original.data() + query * state.dimensions,
                state.pca_queries.data() + query * state.dimensions);
        const Elapsed transform = elapsed(phase_clock);
        result.transform.cpu += transform.cpu;
        result.transform.wall += transform.wall;

        phase_clock = Clock{};
        state.coarse->search(
                1,
                state.pca_queries.data() + query * state.dimensions,
                state.nprobe,
                state.coarse_distances.data() +
                        query * state.nprobe,
                state.selected.data() + query * state.nprobe);
        const Elapsed coarse = elapsed(phase_clock);
        result.coarse.cpu += coarse.cpu;
        result.coarse.wall += coarse.wall;

        phase_clock = Clock{};
        outputs[query] = state.custom_scan()
                ? search_custom_one(state, query)
                : scan_native_one(state, query);
        structured2d::admission::normalize_topk(
                outputs[query], kTopK);
        const Elapsed scan = elapsed(phase_clock);
        result.scan.cpu += scan.cpu;
        result.scan.wall += scan.wall;
        const Elapsed total = elapsed(total_clock);
        result.query_cpu_seconds[query] = total.cpu;
        result.query_wall_seconds[query] = total.wall;
        check_preassignment_query(state, query);
    }
    result.output_hash =
            structured2d::admission::hash_topk(outputs);
    result.recall_hits = recall_hits(state, outputs);
    for (const auto& output : outputs)
        result.candidates += output.candidates;
    return result;
}

Pass run_pass(State& state) {
    if (state.natural && state.mode == Mode::Single)
        return run_natural_single(state);
    Pass result;
    std::vector<structured2d::admission::TopKResult> outputs;
    if (state.mode == Mode::Batch12) {
        Clock clock;
#pragma omp parallel for schedule(static)
        for (std::int64_t query = 0;
             query < static_cast<std::int64_t>(state.queries);
             ++query)
            state.pca->apply_noalloc(
                    1,
                    state.original.data() +
                            query * state.dimensions,
                    state.pca_queries.data() +
                            query * state.dimensions);
        result.transform = elapsed(clock);

        clock = Clock{};
#pragma omp parallel for schedule(static)
        for (std::int64_t query = 0;
             query < static_cast<std::int64_t>(state.queries);
             ++query)
            state.coarse->search(
                    1,
                    state.pca_queries.data() +
                            query * state.dimensions,
                    state.nprobe,
                    state.coarse_distances.data() +
                            query * state.nprobe,
                    state.selected.data() +
                            query * state.nprobe);
        result.coarse = elapsed(clock);
        check_preassignments(state);

        clock = Clock{};
        outputs = state.custom_scan()
                ? scan_custom(state)
                : scan_native(state);
        result.scan = elapsed(clock);
    } else {
        Clock clock;
        for (std::size_t query = 0; query < state.queries; ++query) {
            state.pca->apply_noalloc(
                    1,
                    state.original.data() +
                            query * state.dimensions,
                    state.pca_queries.data() +
                            query * state.dimensions);
        }
        result.transform = elapsed(clock);

        clock = Clock{};
        for (std::size_t query = 0; query < state.queries; ++query)
            state.coarse->search(
                    1,
                    state.pca_queries.data() +
                            query * state.dimensions,
                    state.nprobe,
                    state.coarse_distances.data() +
                            query * state.nprobe,
                    state.selected.data() +
                            query * state.nprobe);
        result.coarse = elapsed(clock);
        check_preassignments(state);

        clock = Clock{};
        if (state.custom_scan()) {
            outputs.resize(state.queries);
            for (std::size_t query = 0;
                 query < state.queries; ++query)
                outputs[query] =
                        search_custom_one(state, query);
        } else {
            outputs = scan_native(state);
        }
        result.scan = elapsed(clock);
    }
    for (auto& output : outputs)
        structured2d::admission::normalize_topk(output, kTopK);
    result.output_hash =
            structured2d::admission::hash_topk(outputs);
    result.recall_hits = recall_hits(state, outputs);
    for (const auto& output : outputs)
        result.candidates += output.candidates;
    return result;
}

int resolved_fastscan(const State& state) {
    if (state.fastscan == nullptr) return -1;
    int implementation = state.fastscan->implem;
    if (implementation == 0) {
        implementation = state.fastscan->bbs == 32 ? 12 : 10;
        if (kTopK > 20) ++implementation;
    }
    return implementation;
}

void write_results(
        const State& state, std::span<const Pass> passes,
        const std::filesystem::path& output_path, bool append,
        std::size_t repetition_offset = 0) {
    std::ofstream output(
            output_path, append ? std::ios::app : std::ios::trunc);
    if (!output)
        throw std::runtime_error("open timing output");
    if (!append)
        output << "dataset\tnlist\tbudget_bytes\tarm_id"
                  "\tphysical_arm_id\tnprobe\tmode\trepetition"
                  "\tqueries\tthreads\ttotal_cpu_seconds"
                  "\ttotal_wall_seconds\ttransform_cpu_seconds"
                  "\ttransform_wall_seconds\tcoarse_cpu_seconds"
                  "\tcoarse_wall_seconds\tscan_cpu_seconds"
                  "\tscan_wall_seconds\tcandidates\toutput_hash"
                  "\tconfigured_fastscan_implem"
                  "\tresolved_fastscan_implem\tpeak_rss_bytes"
                  "\trecall_at_100\n";
    output << std::setprecision(17);
    for (std::size_t repetition = 0;
         repetition < passes.size(); ++repetition) {
        const Pass& pass = passes[repetition];
        const Elapsed total = pass.total();
        output << state.dataset << '\t' << state.nlist << '\t'
               << state.budget << '\t' << state.logical_id << '\t'
               << state.physical_id << '\t' << state.nprobe << '\t'
               << (state.mode == Mode::Single ? "single" : "batch12")
               << '\t' << repetition + repetition_offset << '\t'
               << state.queries << '\t'
               << (state.mode == Mode::Single ? 1 : 12) << '\t'
               << total.cpu << '\t' << total.wall << '\t'
               << pass.transform.cpu << '\t' << pass.transform.wall
               << '\t' << pass.coarse.cpu << '\t'
               << pass.coarse.wall << '\t' << pass.scan.cpu << '\t'
               << pass.scan.wall << '\t' << pass.candidates << '\t'
               << std::hex << pass.output_hash << std::dec << '\t'
               << (state.fastscan ? state.fastscan->implem : -1)
               << '\t' << resolved_fastscan(state) << '\t'
               << peak_rss_bytes() << '\t'
               << (state.truth_sorted.empty()
                           ? 0.0
                           : static_cast<double>(pass.recall_hits) /
                                   (state.queries * kTopK))
               << '\n';
    }
    output.close();
    if (!output)
        throw std::runtime_error("write timing output");
}

void write_query_latencies(
        const State& state, std::span<const Pass> passes,
        const std::filesystem::path& timing_path, bool append,
        std::size_t) {
    if (state.mode != Mode::Single || !state.natural) return;
    const auto path = std::filesystem::path(
            timing_path.string() + ".latency.f64");
    std::ofstream output(
            path, std::ios::binary |
                    (append ? std::ios::app : std::ios::trunc));
    if (!output)
        throw std::runtime_error("open query latency output");
    for (const Pass& pass : passes) {
        if (pass.query_cpu_seconds.size() != state.queries ||
            pass.query_wall_seconds.size() != state.queries)
            throw std::runtime_error("raw query latency shape");
        output.write(
                reinterpret_cast<const char*>(
                        pass.query_wall_seconds.data()),
                static_cast<std::streamsize>(
                        pass.query_wall_seconds.size() *
                        sizeof(double)));
    }
    output.close();
    if (!output)
        throw std::runtime_error("write query latency output");
}

double median(std::vector<double> values) {
    if (values.empty())
        throw std::invalid_argument("empty median");
    std::sort(values.begin(), values.end());
    const std::size_t middle = values.size() / 2;
    return values.size() % 2 == 0
            ? (values[middle - 1] + values[middle]) / 2
            : values[middle];
}

double nearest_rank(
        const std::vector<double>& sorted, double probability) {
    if (sorted.empty() || probability <= 0 || probability > 1)
        throw std::invalid_argument("quantile");
    const std::size_t rank = static_cast<std::size_t>(
            std::ceil(probability * sorted.size()));
    return sorted[std::max<std::size_t>(1, rank) - 1];
}

void write_latency_summary(
        const State& state, std::span<const Pass> passes,
        const std::filesystem::path& timing_path, bool append) {
    if (state.mode != Mode::Single || !state.natural) return;
    std::vector<double> query_medians(state.queries);
    for (std::size_t query = 0; query < state.queries; ++query) {
        std::vector<double> repetitions;
        repetitions.reserve(passes.size());
        for (const Pass& pass : passes) {
            if (pass.query_wall_seconds.size() != state.queries)
                throw std::runtime_error("latency query shape");
            repetitions.push_back(pass.query_wall_seconds[query]);
        }
        query_medians[query] = median(std::move(repetitions));
    }
    std::sort(query_medians.begin(), query_medians.end());
    const double mean =
            std::accumulate(
                    query_medians.begin(), query_medians.end(), 0.0) /
            query_medians.size();
    const double p50 = nearest_rank(query_medians, 0.50);
    std::vector<double> deviations(query_medians.size());
    std::transform(
            query_medians.begin(), query_medians.end(),
            deviations.begin(),
            [p50](double value) { return std::abs(value - p50); });
    const double mad = median(std::move(deviations));
    const auto path =
            std::filesystem::path(timing_path.string() + ".latency.tsv");
    std::ofstream output(
            path, append ? std::ios::app : std::ios::trunc);
    if (!output)
        throw std::runtime_error("open latency summary");
    if (!append)
        output << "dataset\tnlist\tbudget_bytes\tarm_id"
                  "\tphysical_arm_id\tnprobe\tqueries"
                  "\trepetitions\tmean_seconds\tp50_seconds"
                  "\tp95_seconds\tp99_seconds\tmax_seconds"
                  "\tmad_seconds\n";
    output << std::setprecision(17)
           << state.dataset << '\t' << state.nlist << '\t'
           << state.budget << '\t' << state.logical_id << '\t'
           << state.physical_id << '\t' << state.nprobe << '\t'
           << state.queries << '\t' << passes.size() << '\t'
           << mean << '\t' << p50 << '\t'
           << nearest_rank(query_medians, 0.95) << '\t'
           << nearest_rank(query_medians, 0.99) << '\t'
           << query_medians.back() << '\t' << mad << '\n';
}

void measure_current(
        State& state, const std::filesystem::path& output_path,
        bool append, std::size_t repetitions) {
    const Pass warmup = run_pass(state);
    std::vector<Pass> passes;
    passes.reserve(repetitions);
    for (std::size_t repetition = 0;
         repetition < repetitions; ++repetition) {
        passes.push_back(run_pass(state));
        if (passes.back().output_hash != warmup.output_hash ||
            passes.back().candidates != warmup.candidates)
            throw std::runtime_error("unstable timing output");
    }
    write_results(state, passes, output_path, append);
    write_latency_summary(state, passes, output_path, append);
}

State load_natural_state(
        const std::string& dataset, std::size_t nlist,
        int budget, const std::string& arm_id, Mode mode,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& query_path,
        const std::filesystem::path& groundtruth_path,
        const std::filesystem::path& schedule_root) {
    const std::size_t query_count =
            dataset == "sift" ? 10000
            : dataset == "gist" ? 1000
            : throw std::invalid_argument("natural dataset");
    const auto frozen =
            structured2d::admission::frozen_nprobes(nlist);
    State state = load_state(
            dataset, nlist, budget, arm_id, frozen.back(),
            mode, admission_root, pool_root, query_path,
            schedule_root / dataset /
                    ("nlist_" + std::to_string(nlist)) /
                    "query_selected_lists.u32",
            schedule_root / dataset /
                    ("nlist_" + std::to_string(nlist)) /
                    "query_coarse_distances.fvecs",
            query_count);
    state.natural = true;
    state.truth_sorted = structured2d::admission::read_ivecs(
            groundtruth_path, query_count, kTopK, 1000000, true);
    for (std::size_t query = 0; query < query_count; ++query)
        std::sort(
                state.truth_sorted.begin() + query * kTopK,
                state.truth_sorted.begin() + (query + 1) * kTopK);
    return state;
}

void configure_nprobe(State& state, std::size_t nprobe) {
    const auto frozen =
            structured2d::admission::frozen_nprobes(state.nlist);
    if (std::find(frozen.begin(), frozen.end(), nprobe) ==
        frozen.end())
        throw std::invalid_argument("timing nprobe");
    const std::size_t saved_stride = frozen.back();
    if (state.saved_all_selected.size() !=
                state.queries * saved_stride ||
        state.saved_all_coarse_distances.size() !=
                state.queries * saved_stride)
        throw std::runtime_error("saved preassignment shape");
    state.nprobe = nprobe;
    state.coarse_distances.resize(state.queries * nprobe);
    state.selected.resize(state.queries * nprobe);
    state.saved_selected.resize(state.queries * nprobe);
    state.saved_coarse_distances.resize(state.queries * nprobe);
    for (std::size_t query = 0; query < state.queries; ++query)
        std::copy_n(
                state.saved_all_selected.begin() +
                        query * saved_stride,
                nprobe,
                state.saved_selected.begin() + query * nprobe);
    for (std::size_t query = 0; query < state.queries; ++query)
        std::copy_n(
                state.saved_all_coarse_distances.begin() +
                        query * saved_stride,
                nprobe,
                state.saved_coarse_distances.begin() +
                        query * nprobe);
}

void run(
        const std::string& dataset, std::size_t nlist,
        int budget, const std::string& arm_id,
        const std::string& nprobe_text, const std::string& mode_text,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& output_path) {
    const Mode mode = mode_text == "single"
            ? Mode::Single
            : mode_text == "batch12"
            ? Mode::Batch12
            : throw std::invalid_argument("timing mode");
    omp_set_dynamic(0);
    omp_set_num_threads(mode == Mode::Single ? 1 : 12);
    const auto frozen =
            structured2d::admission::frozen_nprobes(nlist);
    const bool all_nprobes = nprobe_text == "all";
    const std::size_t initial_nprobe = all_nprobes
            ? frozen.back()
            : std::stoull(nprobe_text);
    State state = load_state(
            dataset, nlist, budget, arm_id, initial_nprobe, mode,
            admission_root, pool_root,
            admission_root / dataset /
                    "synthetic_original.fvecs",
            admission_root / dataset /
                    ("nlist_" + std::to_string(nlist)) /
                    "synthetic_selected_lists.u32",
            admission_root / dataset /
                    ("nlist_" + std::to_string(nlist)) /
                    "synthetic_coarse_distances.fvecs",
            kSyntheticQueries);
    if (!all_nprobes) {
        measure_current(state, output_path, false, 3);
        return;
    }
    bool append = false;
    for (const std::size_t nprobe : frozen) {
        configure_nprobe(state, nprobe);
        measure_current(state, output_path, append, 3);
        append = true;
    }
}

void run_natural(
        const std::string& dataset, std::size_t nlist,
        int budget, const std::string& arm_id,
        const std::string& mode_text,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& query_path,
        const std::filesystem::path& groundtruth_path,
        const std::filesystem::path& schedule_root,
        const std::filesystem::path& output_path) {
    const Mode mode = mode_text == "single"
            ? Mode::Single
            : mode_text == "batch12"
            ? Mode::Batch12
            : throw std::invalid_argument("natural timing mode");
    omp_set_dynamic(0);
    omp_set_num_threads(mode == Mode::Single ? 1 : 12);
    const auto frozen =
            structured2d::admission::frozen_nprobes(nlist);
    State state = load_natural_state(
            dataset, nlist, budget, arm_id, mode,
            admission_root, pool_root, query_path,
            groundtruth_path, schedule_root);
    bool append = false;
    for (const std::size_t nprobe : frozen) {
        configure_nprobe(state, nprobe);
        measure_current(state, output_path, append, 7);
        append = true;
    }
}

void run_natural_pass(
        const std::string& dataset, std::size_t nlist,
        int budget, const std::string& arm_id,
        const std::string& mode_text,
        const std::filesystem::path& admission_root,
        const std::filesystem::path& pool_root,
        const std::filesystem::path& query_path,
        const std::filesystem::path& groundtruth_path,
        const std::filesystem::path& schedule_root,
        std::size_t repetition, bool append,
        const std::filesystem::path& output_path) {
    const Mode mode = mode_text == "single"
            ? Mode::Single
            : mode_text == "batch12"
            ? Mode::Batch12
            : throw std::invalid_argument("natural pass mode");
    omp_set_dynamic(0);
    omp_set_num_threads(mode == Mode::Single ? 1 : 12);
    State state = load_natural_state(
            dataset, nlist, budget, arm_id, mode,
            admission_root, pool_root, query_path,
            groundtruth_path, schedule_root);
    const auto frozen =
            structured2d::admission::frozen_nprobes(nlist);
    bool row_append = append;
    for (const std::size_t nprobe : frozen) {
        configure_nprobe(state, nprobe);
        const Pass pass = run_pass(state);
        write_results(
                state, std::span<const Pass>(&pass, 1),
                output_path, row_append, repetition);
        write_query_latencies(
                state, std::span<const Pass>(&pass, 1),
                output_path, row_append, repetition);
        row_append = true;
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 15 &&
            std::string(argv[1]) == "natural-pass") {
            const std::string write_mode = argv[13];
            if (write_mode != "truncate" &&
                write_mode != "append")
                throw std::invalid_argument(
                        "natural pass write mode");
            run_natural_pass(
                    argv[2], std::stoull(argv[3]),
                    std::stoi(argv[4]), argv[5], argv[6],
                    argv[7], argv[8], argv[9], argv[10],
                    argv[11], std::stoull(argv[12]),
                    write_mode == "append", argv[14]);
            return 0;
        }
        if (argc == 13 && std::string(argv[1]) == "natural") {
            run_natural(
                    argv[2], std::stoull(argv[3]),
                    std::stoi(argv[4]), argv[5], argv[6],
                    argv[7], argv[8], argv[9], argv[10],
                    argv[11], argv[12]);
            return 0;
        }
        if (argc != 10)
            throw std::invalid_argument(
                    "usage: structured_2d_run_synthetic_timing "
                    "<sift|gist> <nlist> <32|64> <arm_id> <nprobe|all> "
                    "<single|batch12> <admission_root> <pool_root> "
                    "<output_tsv>; or natural <sift|gist> <nlist> "
                    "<32|64> <arm_id> <single|batch12> "
                    "<admission_root> <pool_root> <query_fvecs> "
                    "<groundtruth_ivecs> <schedule_root> <output_tsv>; "
                    "or natural-pass <sift|gist> <nlist> <32|64> "
                    "<arm_id> <single|batch12> <admission_root> "
                    "<pool_root> <query_fvecs> <groundtruth_ivecs> "
                    "<schedule_root> <repetition> <truncate|append> "
                    "<output_tsv>");
        run(
                argv[1], std::stoull(argv[2]), std::stoi(argv[3]),
                argv[4], argv[5], argv[6],
                argv[7], argv[8], argv[9]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_run_synthetic_timing: "
                  << error.what() << '\n';
        return 1;
    }
}

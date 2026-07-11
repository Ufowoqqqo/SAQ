#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <numeric>
#include <string>
#include <tuple>
#include <unordered_set>
#include <utility>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "define_options.h"

#include "analysis/graph_estimator_work.hpp"
#include "baseline/symphonyqg_fastscan.hpp"
#include "baseline/symphonyqg_scalar.hpp"
#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/IO.hpp"

using namespace saqlib;

DEFINE_string(graph_bench_data_file, "", "PCA-space base vectors.");
DEFINE_string(graph_bench_query_file, "", "PCA-space held-out queries.");
DEFINE_string(graph_bench_index_file, "", "Loaded SAQ IVF index.");
DEFINE_string(graph_bench_output_prefix, "", "Output prefix for trial, summary, work, and Markdown files.");
DEFINE_int32(graph_bench_subset, 4096, "Exact-adjacency subset size used only during untimed setup.");
DEFINE_int32(graph_bench_degree, 32, "Fixed local graph degree.");
DEFINE_int32(graph_bench_max_queries, 100, "Number of held-out queries.");
DEFINE_int32(graph_bench_roots_per_query, 8, "Root expansions per query.");
DEFINE_int32(graph_bench_trials, 7, "Independent timing trials.");
DEFINE_int32(graph_bench_rounds, 5, "Full fixed-trace repetitions per timing trial.");
DEFINE_int32(graph_bench_warmup_rounds, 1, "Untimed repetitions before each trial.");
DEFINE_uint64(graph_bench_symqg_rotation_seed, 0, "Fixed SymphonyQG rotation seed.");

namespace {

volatile double benchmark_sink = 0.0;

struct ClusterLoc {
    PID cluster_id = 0;
    size_t local_idx = 0;
    bool valid = false;
};

struct CandidateRef {
    PID id = 0;
    PID cluster_id = 0;
    size_t local_idx = 0;
    size_t block_idx = 0;
    size_t lane = 0;
};

struct BlockGroup {
    PID cluster_id = 0;
    size_t block_idx = 0;
    std::vector<CandidateRef> candidates;
    SaqCluEstimator<DistType::L2Sqr> *cached_estimator = nullptr;
};

struct RootTrace {
    PID root_id = 0;
    float current_distance = 0.0f;
    std::vector<CandidateRef> candidates;
    std::vector<BlockGroup> grouped_candidates;
};

struct QueryTrace {
    PID query_id = 0;
    FloatVec query;
    baseline::SymphonyQGFastScanQuery symqg_query;
    std::unique_ptr<SaqCluEstimator<DistType::L2Sqr>> saq_estimator;
    std::vector<PID> cluster_ids;
    std::map<PID, std::unique_ptr<SaqCluEstimator<DistType::L2Sqr>>>
        cached_cluster_estimators;
    SaqCluEstimator<DistType::L2Sqr> *full_block_estimator = nullptr;
    std::vector<RootTrace> roots;
};

struct TraceStats {
    size_t queries = 0;
    size_t root_events = 0;
    size_t candidates = 0;
    size_t sequential_cluster_prepares = 0;
    size_t grouped_cluster_prepares = 0;
    size_t grouped_block_scans = 0;
    size_t distinct_clusters = 0;
    size_t unique_query_clusters = 0;
};

struct TrialResult {
    std::string component;
    std::string unit;
    size_t trial = 0;
    size_t units_per_round = 0;
    size_t timed_rounds = 0;
    double elapsed_ns = 0.0;
    double ns_per_unit = 0.0;
    double checksum = 0.0;
};

struct SummaryResult {
    std::string component;
    std::string unit;
    size_t trials = 0;
    size_t units_per_round = 0;
    size_t timed_rounds = 0;
    double median_ns_per_unit = 0.0;
    double p10_ns_per_unit = 0.0;
    double p90_ns_per_unit = 0.0;
    double min_ns_per_unit = 0.0;
    double max_ns_per_unit = 0.0;
};

struct WorkRow {
    std::string estimator;
    std::string schedule;
    size_t root_events = 0;
    size_t candidates = 0;
    size_t block_scan_calls = 0;
    size_t cluster_prepare_calls = 0;
    size_t graph_id_read_bytes = 0;
    size_t locator_read_bytes = 0;
    size_t short_or_edge_code_read_bytes = 0;
    size_t short_factor_read_bytes = 0;
    size_t query_lut_read_bytes = 0;
    size_t long_code_read_bytes = 0;
    size_t long_factor_value_read_bytes = 0;
    size_t accurate_query_read_bytes = 0;
    size_t cluster_prepare_input_bytes = 0;
    size_t cluster_prepare_query_state_write_bytes = 0;
    size_t cluster_prepare_lut_write_bytes = 0;
    size_t exact_current_vector_read_bytes = 0;
    size_t total_logical_input_bytes = 0;
    double logical_input_bytes_per_candidate = 0.0;
    double cacheline_input_bytes_per_candidate = 0.0;
    size_t modeled_index_bytes_per_node = 0;
    double actual_saq_index_bytes_per_vector = 0.0;
    size_t duplicated_neighbor_code_bytes_per_node = 0;
    size_t query_cluster_cache_bytes = 0;
};

enum class Kernel {
    Symqg,
    SaqFastSequential,
    SaqPrefix1Sequential,
    SaqFastGrouped,
    SaqPrefix1Grouped,
    SaqFastGroupedCached,
    SaqPrefix1GroupedCached,
    SaqFastPerfectFullBlock,
    SaqPrefix1PerfectFullBlock,
};

float l2Sqr(
    const Eigen::Ref<const FloatVec> &left,
    const Eigen::Ref<const FloatVec> &right) {
    return (left - right).squaredNorm();
}

std::vector<std::vector<PID>> buildExactSubsetAdjacency(
    const FloatRowMat &data, size_t subset, size_t degree) {
    CHECK_GT(subset, 1);
    CHECK_LT(degree, subset);
    std::vector<std::vector<PID>> adjacency(subset);
    for (size_t source = 0; source < subset; ++source) {
        std::vector<std::pair<float, PID>> distances;
        distances.reserve(subset - 1);
        const FloatVec source_vector = data.row(source);
        for (size_t target = 0; target < subset; ++target) {
            if (source == target) {
                continue;
            }
            distances.emplace_back(
                l2Sqr(source_vector, data.row(target)),
                static_cast<PID>(target));
        }
        if (degree < distances.size()) {
            std::nth_element(
                distances.begin(), distances.begin() + degree, distances.end());
            distances.resize(degree);
        }
        std::sort(distances.begin(), distances.end());
        for (const auto &[distance, id] : distances) {
            (void)distance;
            adjacency[source].push_back(id);
        }
    }
    return adjacency;
}

std::vector<PID> exactNearestRoots(
    const FloatRowMat &data, const FloatVec &query,
    size_t subset, size_t count) {
    std::vector<std::pair<float, PID>> distances;
    distances.reserve(subset);
    for (size_t id = 0; id < subset; ++id) {
        distances.emplace_back(
            l2Sqr(query, data.row(id)), static_cast<PID>(id));
    }
    if (count < distances.size()) {
        std::nth_element(
            distances.begin(), distances.begin() + count, distances.end());
        distances.resize(count);
    }
    std::sort(distances.begin(), distances.end());
    std::vector<PID> roots;
    for (const auto &[distance, id] : distances) {
        (void)distance;
        roots.push_back(id);
    }
    return roots;
}

std::vector<ClusterLoc> buildIdToLoc(const IVF &ivf) {
    std::vector<ClusterLoc> locations(ivf.num_data());
    const auto &clusters = ivf.get_pclusters();
    for (PID cluster_id = 0; cluster_id < clusters.size(); ++cluster_id) {
        const auto &cluster = clusters[cluster_id];
        for (size_t local = 0; local < cluster.num_vec_; ++local) {
            const PID id = cluster.ids()[local];
            CHECK_LT(id, locations.size());
            locations[id] = ClusterLoc{cluster_id, local, true};
        }
    }
    for (size_t id = 0; id < locations.size(); ++id) {
        CHECK(locations[id].valid) << "missing vector id " << id;
    }
    return locations;
}

std::vector<BlockGroup> groupCandidates(
    const std::vector<CandidateRef> &candidates) {
    std::map<std::pair<PID, size_t>, std::vector<CandidateRef>> grouped;
    for (const auto &candidate : candidates) {
        grouped[{candidate.cluster_id, candidate.block_idx}].push_back(candidate);
    }
    std::vector<BlockGroup> result;
    for (auto &[key, values] : grouped) {
        result.push_back(BlockGroup{
            key.first, key.second, std::move(values), nullptr});
    }
    return result;
}

double percentile(std::vector<double> values, double probability) {
    CHECK(!values.empty());
    std::sort(values.begin(), values.end());
    const double position = probability * static_cast<double>(values.size() - 1);
    const size_t index = static_cast<size_t>(std::ceil(position));
    return values[std::min(index, values.size() - 1)];
}

std::string kernelName(Kernel kernel) {
    switch (kernel) {
    case Kernel::Symqg:
        return "symqg_fht_fastscan";
    case Kernel::SaqFastSequential:
        return "saq_fast_candidate_order";
    case Kernel::SaqPrefix1Sequential:
        return "saq_prefix_acc1_candidate_order";
    case Kernel::SaqFastGrouped:
        return "saq_fast_grouped_block_lower_bound";
    case Kernel::SaqPrefix1Grouped:
        return "saq_prefix_acc1_grouped_block_lower_bound";
    case Kernel::SaqFastGroupedCached:
        return "saq_fast_grouped_cached_cluster_lower_bound";
    case Kernel::SaqPrefix1GroupedCached:
        return "saq_prefix_acc1_grouped_cached_cluster_lower_bound";
    case Kernel::SaqFastPerfectFullBlock:
        return "saq_fast_perfect_full_block_kernel_lower_bound";
    case Kernel::SaqPrefix1PerfectFullBlock:
        return "saq_prefix_acc1_perfect_full_block_kernel_lower_bound";
    }
    LOG(FATAL) << "unknown benchmark kernel";
    return "unknown";
}

void ensureParent(const std::string &path) {
    const auto parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
}

class GraphEstimatorBenchmark {
  private:
    FloatRowMat data_;
    FloatRowMat queries_;
    IVF ivf_;
    std::vector<ClusterLoc> id_to_loc_;
    std::vector<std::vector<PID>> adjacency_;
    std::unique_ptr<baseline::SymphonyQGScalarEstimator> symqg_scalar_;
    std::unique_ptr<baseline::SymphonyQGFastScanEstimator> symqg_fastscan_;
    FloatRowMat symqg_rotated_data_;
    std::vector<baseline::SymphonyQGFastScanBatch> symqg_batches_;
    std::vector<QueryTrace> traces_;
    TraceStats trace_stats_;
    SearcherConfig searcher_cfg_;

    size_t subset_ = 0;
    size_t degree_ = 0;
    size_t max_queries_ = 0;
    size_t roots_per_query_ = 0;
    std::string data_file_;
    std::string query_file_;
    std::string index_file_;
    std::string output_prefix_;

    double runKernel(
        Kernel kernel, size_t rounds,
        baseline::SymphonyQGFastScanScratch &symqg_scratch,
        std::vector<float> &symqg_distances) {
        const auto &clusters = ivf_.get_pclusters();
        double checksum = 0.0;
        float PORTABLE_ALIGN64 block_values[KFastScanSize];
        float PORTABLE_ALIGN64 segment_values[KFastScanSize];
        float PORTABLE_ALIGN64 first_segment_values[KFastScanSize];

        for (size_t round = 0; round < rounds; ++round) {
            for (auto &query_trace : traces_) {
                auto &saq = *query_trace.saq_estimator;
                const bool perfect_full_block =
                    kernel == Kernel::SaqFastPerfectFullBlock ||
                    kernel == Kernel::SaqPrefix1PerfectFullBlock;
                if (perfect_full_block) {
                    CHECK(query_trace.full_block_estimator);
                    auto &prepared = *query_trace.full_block_estimator;
                    const bool prefix =
                        kernel == Kernel::SaqPrefix1PerfectFullBlock;
                    if (!prefix) {
                        __m512 distances[2];
                        prepared.compFastDist(0, distances);
                        _mm512_store_ps(block_values, distances[0]);
                        _mm512_store_ps(block_values + 16, distances[1]);
                        checksum += std::accumulate(
                            block_values, block_values + KFastScanSize, 0.0);
                    } else {
                        std::fill(
                            block_values, block_values + KFastScanSize, 0.0f);
                        for (size_t segment = 0;
                             segment < prepared.numSegments(); ++segment) {
                            __m512 distances[2];
                            prepared.compFastDistSegment(segment, 0, distances);
                            _mm512_store_ps(segment_values, distances[0]);
                            _mm512_store_ps(
                                segment_values + 16, distances[1]);
                            for (size_t lane = 0; lane < KFastScanSize; ++lane) {
                                block_values[lane] += segment_values[lane];
                            }
                            if (segment == 0) {
                                std::copy(
                                    segment_values,
                                    segment_values + KFastScanSize,
                                    first_segment_values);
                            }
                        }
                        for (size_t lane = 0; lane < KFastScanSize; ++lane) {
                            checksum += block_values[lane] -
                                        first_segment_values[lane] +
                                        prepared.compAccurateDistSegment(0, lane);
                        }
                    }
                    continue;
                }
                for (const auto &root : query_trace.roots) {
                    if (kernel == Kernel::Symqg) {
                        symqg_fastscan_->estimateBatchInto(
                            query_trace.symqg_query, root.current_distance,
                            symqg_batches_[root.root_id], symqg_scratch,
                            symqg_distances);
                        for (size_t candidate = 0;
                             candidate < root.candidates.size(); ++candidate) {
                            checksum += symqg_distances[candidate];
                        }
                        continue;
                    }

                    PID prepared_cluster = std::numeric_limits<PID>::max();
                    const bool grouped =
                        kernel == Kernel::SaqFastGrouped ||
                        kernel == Kernel::SaqPrefix1Grouped ||
                        kernel == Kernel::SaqFastGroupedCached ||
                        kernel == Kernel::SaqPrefix1GroupedCached;
                    const bool cached =
                        kernel == Kernel::SaqFastGroupedCached ||
                        kernel == Kernel::SaqPrefix1GroupedCached;
                    const bool prefix =
                        kernel == Kernel::SaqPrefix1Sequential ||
                        kernel == Kernel::SaqPrefix1Grouped ||
                        kernel == Kernel::SaqPrefix1GroupedCached;

                    if (!grouped) {
                        for (const auto &candidate : root.candidates) {
                            if (prepared_cluster != candidate.cluster_id) {
                                saq.prepare(&clusters[candidate.cluster_id]);
                                prepared_cluster = candidate.cluster_id;
                            }
                            if (!prefix) {
                                checksum += saq.compFastDistSingle(candidate.local_idx);
                                continue;
                            }
                            float distance = 0.0f;
                            for (size_t segment = 0;
                                 segment < saq.numSegments(); ++segment) {
                                const float fast = saq.compFastDistSegmentSingle(
                                    segment, candidate.local_idx);
                                distance += segment == 0
                                                ? saq.compAccurateDistSegment(
                                                      segment, candidate.local_idx)
                                                : fast;
                            }
                            checksum += distance;
                        }
                        continue;
                    }

                    for (const auto &group : root.grouped_candidates) {
                        SaqCluEstimator<DistType::L2Sqr> *group_estimator = &saq;
                        if (cached) {
                            CHECK(group.cached_estimator);
                            group_estimator = group.cached_estimator;
                        } else if (prepared_cluster != group.cluster_id) {
                            group_estimator->prepare(&clusters[group.cluster_id]);
                            prepared_cluster = group.cluster_id;
                        }
                        auto &prepared = *group_estimator;
                        if (!prefix) {
                            __m512 distances[2];
                            prepared.compFastDist(group.block_idx, distances);
                            _mm512_store_ps(block_values, distances[0]);
                            _mm512_store_ps(block_values + 16, distances[1]);
                            for (const auto &candidate : group.candidates) {
                                checksum += block_values[candidate.lane];
                            }
                            continue;
                        }

                        std::fill(
                            block_values, block_values + KFastScanSize, 0.0f);
                        for (size_t segment = 0;
                             segment < prepared.numSegments(); ++segment) {
                            __m512 distances[2];
                            prepared.compFastDistSegment(
                                segment, group.block_idx, distances);
                            _mm512_store_ps(segment_values, distances[0]);
                            _mm512_store_ps(segment_values + 16, distances[1]);
                            for (size_t lane = 0; lane < KFastScanSize; ++lane) {
                                block_values[lane] += segment_values[lane];
                            }
                            if (segment == 0) {
                                std::copy(
                                    segment_values,
                                    segment_values + KFastScanSize,
                                    first_segment_values);
                            }
                        }
                        for (const auto &candidate : group.candidates) {
                            const float accurate = prepared.compAccurateDistSegment(
                                0, candidate.local_idx);
                            checksum += block_values[candidate.lane] -
                                        first_segment_values[candidate.lane] +
                                        accurate;
                        }
                    }
                }
            }
        }
        CHECK(std::isfinite(checksum));
        return checksum;
    }

    double runExactCurrent(size_t rounds) const {
        double checksum = 0.0;
        for (size_t round = 0; round < rounds; ++round) {
            for (const auto &query_trace : traces_) {
                for (const auto &root : query_trace.roots) {
                    checksum += l2Sqr(
                        query_trace.query, data_.row(root.root_id));
                }
            }
        }
        return checksum;
    }

    double runSymqgQueryPrepare(size_t rounds) const {
        double checksum = 0.0;
        for (size_t round = 0; round < rounds; ++round) {
            for (size_t query_id = 0; query_id < max_queries_; ++query_id) {
                const FloatVec query = queries_.row(query_id);
                const auto scalar = symqg_scalar_->prepareQuery(query.data());
                const auto packed = symqg_fastscan_->prepareQuery(scalar);
                checksum += packed.width + packed.lower +
                            static_cast<double>(packed.code_sum) +
                            packed.packed_lut.front();
            }
        }
        return checksum;
    }

    double runSaqQueryPrepare(size_t rounds) const {
        double checksum = 0.0;
        for (size_t round = 0; round < rounds; ++round) {
            for (size_t query_id = 0; query_id < max_queries_; ++query_id) {
                const FloatVec query = queries_.row(query_id);
                SaqCluEstimator<DistType::L2Sqr> estimator(
                    *ivf_.get_saq_data(), searcher_cfg_, query);
                checksum += static_cast<double>(estimator.numSegments());
            }
        }
        return checksum;
    }

    double runSaqClusterCachePrepare(size_t rounds) const {
        const auto &clusters = ivf_.get_pclusters();
        double checksum = 0.0;
        for (size_t round = 0; round < rounds; ++round) {
            for (const auto &query_trace : traces_) {
                for (PID cluster_id : query_trace.cluster_ids) {
                    SaqCluEstimator<DistType::L2Sqr> estimator(
                        *ivf_.get_saq_data(), searcher_cfg_, query_trace.query);
                    estimator.prepare(&clusters[cluster_id]);
                    checksum += static_cast<double>(estimator.numSegments());
                }
            }
        }
        return checksum;
    }

    template <typename Function>
    TrialResult timeComponent(
        const std::string &component, const std::string &unit,
        size_t trial, size_t units_per_round, Function function) {
        function(static_cast<size_t>(FLAGS_graph_bench_warmup_rounds));
        const auto begin = std::chrono::steady_clock::now();
        const double checksum = function(static_cast<size_t>(FLAGS_graph_bench_rounds));
        const auto end = std::chrono::steady_clock::now();
        const double elapsed_ns = static_cast<double>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count());
        const size_t total_units =
            units_per_round * static_cast<size_t>(FLAGS_graph_bench_rounds);
        benchmark_sink = benchmark_sink + checksum;
        return TrialResult{
            component,
            unit,
            trial,
            units_per_round,
            static_cast<size_t>(FLAGS_graph_bench_rounds),
            elapsed_ns,
            elapsed_ns / static_cast<double>(total_units),
            checksum,
        };
    }

  public:
    void load() {
        CHECK(!FLAGS_graph_bench_data_file.empty());
        CHECK(!FLAGS_graph_bench_query_file.empty());
        CHECK(!FLAGS_graph_bench_index_file.empty());
        CHECK(!FLAGS_graph_bench_output_prefix.empty());
        CHECK_GT(FLAGS_graph_bench_subset, 1);
        CHECK_GT(FLAGS_graph_bench_degree, 0);
        CHECK_GT(FLAGS_graph_bench_max_queries, 0);
        CHECK_GT(FLAGS_graph_bench_roots_per_query, 0);
        CHECK_GT(FLAGS_graph_bench_trials, 0);
        CHECK_GT(FLAGS_graph_bench_rounds, 0);
        CHECK_GE(FLAGS_graph_bench_warmup_rounds, 0);

        data_file_ = FLAGS_graph_bench_data_file;
        query_file_ = FLAGS_graph_bench_query_file;
        index_file_ = FLAGS_graph_bench_index_file;
        output_prefix_ = FLAGS_graph_bench_output_prefix;
        utils::load_something<float, FloatRowMat>(data_file_.c_str(), data_);
        utils::load_something<float, FloatRowMat>(query_file_.c_str(), queries_);
        ivf_.load(index_file_.c_str());
        CHECK_EQ(static_cast<size_t>(data_.rows()), ivf_.num_data());
        CHECK_EQ(static_cast<size_t>(data_.cols()), ivf_.num_dim());
        CHECK_EQ(queries_.cols(), data_.cols());

        subset_ = std::min(
            static_cast<size_t>(FLAGS_graph_bench_subset),
            static_cast<size_t>(data_.rows()));
        degree_ = static_cast<size_t>(FLAGS_graph_bench_degree);
        max_queries_ = std::min(
            static_cast<size_t>(FLAGS_graph_bench_max_queries),
            static_cast<size_t>(queries_.rows()));
        roots_per_query_ = static_cast<size_t>(FLAGS_graph_bench_roots_per_query);
        CHECK_LT(degree_, subset_);
        CHECK_LE(roots_per_query_, subset_);

        searcher_cfg_.dist_type = DistType::L2Sqr;
        searcher_cfg_.searcher_safe_block_min_mode = 2;
        adjacency_ = buildExactSubsetAdjacency(data_, subset_, degree_);
        id_to_loc_ = buildIdToLoc(ivf_);

        symqg_scalar_ = std::make_unique<baseline::SymphonyQGScalarEstimator>(
            static_cast<size_t>(data_.cols()),
            FLAGS_graph_bench_symqg_rotation_seed);
        symqg_fastscan_ =
            std::make_unique<baseline::SymphonyQGFastScanEstimator>(
                symqg_scalar_->padded_dimension());
        symqg_rotated_data_.resize(
            subset_, symqg_scalar_->padded_dimension());
        for (size_t id = 0; id < subset_; ++id) {
            FloatVec rotated;
            symqg_scalar_->rotate(data_.row(id).data(), rotated);
            symqg_rotated_data_.row(id) = rotated;
        }
        symqg_batches_.resize(subset_);
        for (size_t root = 0; root < subset_; ++root) {
            std::vector<baseline::SymphonyQGScalarNeighbor> encoded(degree_);
            for (size_t candidate = 0; candidate < degree_; ++candidate) {
                const PID neighbor = adjacency_[root][candidate];
                symqg_scalar_->encodeNeighbor(
                    symqg_rotated_data_.row(root).data(),
                    symqg_rotated_data_.row(neighbor).data(),
                    encoded[candidate]);
            }
            symqg_batches_[root] = symqg_fastscan_->encodeBatch(encoded);
        }

        traces_.reserve(max_queries_);
        trace_stats_.queries = max_queries_;
        for (PID query_id = 0; query_id < max_queries_; ++query_id) {
            QueryTrace trace;
            trace.query_id = query_id;
            trace.query = queries_.row(query_id);
            const auto scalar_query =
                symqg_scalar_->prepareQuery(trace.query.data());
            trace.symqg_query = symqg_fastscan_->prepareQuery(scalar_query);
            trace.saq_estimator =
                std::make_unique<SaqCluEstimator<DistType::L2Sqr>>(
                    *ivf_.get_saq_data(), searcher_cfg_, trace.query);
            const auto roots = exactNearestRoots(
                data_, trace.query, subset_, roots_per_query_);
            std::unordered_set<PID> query_clusters;
            for (PID root_id : roots) {
                RootTrace root;
                root.root_id = root_id;
                root.current_distance = l2Sqr(trace.query, data_.row(root_id));
                PID previous_cluster = std::numeric_limits<PID>::max();
                std::unordered_set<PID> distinct_clusters;
                for (PID id : adjacency_[root_id]) {
                    const auto loc = id_to_loc_[id];
                    CandidateRef candidate{
                        id,
                        loc.cluster_id,
                        loc.local_idx,
                        loc.local_idx / KFastScanSize,
                        loc.local_idx % KFastScanSize,
                    };
                    root.candidates.push_back(candidate);
                    distinct_clusters.insert(loc.cluster_id);
                    query_clusters.insert(loc.cluster_id);
                    if (previous_cluster != loc.cluster_id) {
                        ++trace_stats_.sequential_cluster_prepares;
                        previous_cluster = loc.cluster_id;
                    }
                }
                root.grouped_candidates = groupCandidates(root.candidates);
                trace_stats_.root_events++;
                trace_stats_.candidates += root.candidates.size();
                trace_stats_.grouped_block_scans +=
                    root.grouped_candidates.size();
                trace_stats_.grouped_cluster_prepares +=
                    distinct_clusters.size();
                trace_stats_.distinct_clusters += distinct_clusters.size();
                trace.roots.push_back(std::move(root));
            }
            trace.cluster_ids.assign(
                query_clusters.begin(), query_clusters.end());
            std::sort(trace.cluster_ids.begin(), trace.cluster_ids.end());
            trace_stats_.unique_query_clusters += trace.cluster_ids.size();
            for (PID cluster_id : trace.cluster_ids) {
                auto estimator =
                    std::make_unique<SaqCluEstimator<DistType::L2Sqr>>(
                        *ivf_.get_saq_data(), searcher_cfg_, trace.query);
                estimator->prepare(&ivf_.get_pclusters()[cluster_id]);
                trace.cached_cluster_estimators.emplace(
                    cluster_id, std::move(estimator));
            }
            for (PID cluster_id : trace.cluster_ids) {
                if (ivf_.get_pclusters()[cluster_id].num_vec_ >= KFastScanSize) {
                    trace.full_block_estimator =
                        trace.cached_cluster_estimators.at(cluster_id).get();
                    break;
                }
            }
            CHECK(trace.full_block_estimator)
                << "no full SAQ block found for query " << query_id;
            for (auto &root : trace.roots) {
                for (auto &group : root.grouped_candidates) {
                    group.cached_estimator =
                        trace.cached_cluster_estimators.at(group.cluster_id).get();
                }
            }
            traces_.push_back(std::move(trace));
        }
    }

    std::vector<TrialResult> benchmark() {
        baseline::SymphonyQGFastScanScratch scratch;
        std::vector<float> distances;
        const double fast_sequential = runKernel(
            Kernel::SaqFastSequential, 1, scratch, distances);
        const double fast_grouped = runKernel(
            Kernel::SaqFastGrouped, 1, scratch, distances);
        const double prefix_sequential = runKernel(
            Kernel::SaqPrefix1Sequential, 1, scratch, distances);
        const double prefix_grouped = runKernel(
            Kernel::SaqPrefix1Grouped, 1, scratch, distances);
        const double fast_cached = runKernel(
            Kernel::SaqFastGroupedCached, 1, scratch, distances);
        const double prefix_cached = runKernel(
            Kernel::SaqPrefix1GroupedCached, 1, scratch, distances);
        CHECK_LE(
            std::abs(fast_sequential - fast_grouped),
            1e-5 * std::max(1.0, std::abs(fast_sequential)));
        CHECK_LE(
            std::abs(prefix_sequential - prefix_grouped),
            1e-5 * std::max(1.0, std::abs(prefix_sequential)));
        CHECK_LE(
            std::abs(fast_grouped - fast_cached),
            1e-5 * std::max(1.0, std::abs(fast_grouped)));
        CHECK_LE(
            std::abs(prefix_grouped - prefix_cached),
            1e-5 * std::max(1.0, std::abs(prefix_grouped)));

        const std::vector<Kernel> kernels = {
            Kernel::Symqg,
            Kernel::SaqFastSequential,
            Kernel::SaqPrefix1Sequential,
            Kernel::SaqFastGrouped,
            Kernel::SaqPrefix1Grouped,
            Kernel::SaqFastGroupedCached,
            Kernel::SaqPrefix1GroupedCached,
            Kernel::SaqFastPerfectFullBlock,
            Kernel::SaqPrefix1PerfectFullBlock,
        };
        std::vector<TrialResult> results;
        for (size_t trial = 0;
             trial < static_cast<size_t>(FLAGS_graph_bench_trials); ++trial) {
            for (size_t offset = 0; offset < kernels.size(); ++offset) {
                const Kernel kernel = kernels[(trial + offset) % kernels.size()];
                const bool perfect_full_block =
                    kernel == Kernel::SaqFastPerfectFullBlock ||
                    kernel == Kernel::SaqPrefix1PerfectFullBlock;
                results.push_back(timeComponent(
                    kernelName(kernel), "candidate", trial,
                    perfect_full_block
                        ? trace_stats_.queries * KFastScanSize
                        : trace_stats_.candidates,
                    [&](size_t rounds) {
                        return runKernel(kernel, rounds, scratch, distances);
                    }));
            }
            results.push_back(timeComponent(
                "exact_current_l2", "root", trial,
                trace_stats_.root_events,
                [&](size_t rounds) { return runExactCurrent(rounds); }));
            results.push_back(timeComponent(
                "symqg_query_prepare", "query", trial,
                trace_stats_.queries,
                [&](size_t rounds) { return runSymqgQueryPrepare(rounds); }));
            results.push_back(timeComponent(
                "saq_query_prepare", "query", trial,
                trace_stats_.queries,
                [&](size_t rounds) { return runSaqQueryPrepare(rounds); }));
            results.push_back(timeComponent(
                "saq_query_cluster_cache_prepare", "query_cluster", trial,
                trace_stats_.unique_query_clusters,
                [&](size_t rounds) {
                    return runSaqClusterCachePrepare(rounds);
                }));
        }
        return results;
    }

    std::vector<SummaryResult> summarize(
        const std::vector<TrialResult> &trials) const {
        std::map<std::pair<std::string, std::string>, std::vector<TrialResult>> grouped;
        for (const auto &trial : trials) {
            grouped[{trial.component, trial.unit}].push_back(trial);
        }
        std::vector<SummaryResult> summaries;
        for (const auto &[key, values] : grouped) {
            std::vector<double> ns;
            for (const auto &value : values) {
                ns.push_back(value.ns_per_unit);
            }
            summaries.push_back(SummaryResult{
                key.first,
                key.second,
                values.size(),
                values.front().units_per_round,
                values.front().timed_rounds,
                percentile(ns, 0.50),
                percentile(ns, 0.10),
                percentile(ns, 0.90),
                *std::min_element(ns.begin(), ns.end()),
                *std::max_element(ns.begin(), ns.end()),
            });
        }
        return summaries;
    }

    std::vector<WorkRow> workRows() const {
        const auto symqg = analysis::makeSymphonyQGWorkModel(
            ivf_.num_dim(), symqg_fastscan_->padded_dimension(), degree_);
        const auto fast = analysis::makeSaqStageWorkModel(
            ivf_.num_dim(), ivf_.get_saq_data()->quant_plan, degree_, 0);
        const auto prefix1 = analysis::makeSaqStageWorkModel(
            ivf_.num_dim(), ivf_.get_saq_data()->quant_plan, degree_, 1);
        const double actual_saq_bytes =
            static_cast<double>(std::filesystem::file_size(index_file_)) /
            static_cast<double>(ivf_.num_data());

        std::vector<WorkRow> rows;
        auto addSymqg = [&](const std::string &schedule, bool cold_current) {
            WorkRow row;
            row.estimator = "symqg_fht_fastscan";
            row.schedule = schedule;
            row.root_events = trace_stats_.root_events;
            row.candidates = trace_stats_.candidates;
            row.block_scan_calls = trace_stats_.root_events;
            row.graph_id_read_bytes =
                trace_stats_.candidates * sizeof(PID);
            row.short_or_edge_code_read_bytes =
                trace_stats_.root_events * symqg.code_bytes_per_root();
            row.short_factor_read_bytes =
                trace_stats_.root_events * symqg.factor_bytes_per_root();
            row.query_lut_read_bytes =
                trace_stats_.root_events * symqg.query_lut_bytes;
            row.exact_current_vector_read_bytes =
                cold_current
                    ? trace_stats_.root_events *
                          symqg.exact_current_vector_bytes_per_root
                    : 0;
            row.total_logical_input_bytes =
                row.graph_id_read_bytes +
                row.short_or_edge_code_read_bytes +
                row.short_factor_read_bytes + row.query_lut_read_bytes +
                row.exact_current_vector_read_bytes;
            row.logical_input_bytes_per_candidate =
                static_cast<double>(row.total_logical_input_bytes) /
                static_cast<double>(row.candidates);
            row.cacheline_input_bytes_per_candidate =
                row.logical_input_bytes_per_candidate;
            row.modeled_index_bytes_per_node = symqg.edge_index_bytes_per_node();
            row.duplicated_neighbor_code_bytes_per_node =
                degree_ * symqg.code_bytes_per_candidate;
            rows.push_back(row);
        };
        addSymqg("cached_current_distance", false);
        addSymqg("cold_current_vector", true);

        auto addSaq = [&](const std::string &estimator,
                          const std::string &schedule,
                          const analysis::SaqStageWorkModel &model,
                          const analysis::SaqTraceWork &trace,
                          bool cached_cluster_state,
                          bool include_graph_inputs) {
            const auto bytes = analysis::calculateSaqTraceBytes(model, trace);
            WorkRow row;
            row.estimator = estimator;
            row.schedule = schedule;
            row.root_events = trace.root_events;
            row.candidates = trace.candidates;
            row.block_scan_calls = trace.block_scan_calls;
            row.cluster_prepare_calls = trace.cluster_prepare_calls;
            row.graph_id_read_bytes = include_graph_inputs
                                          ? trace.candidates * sizeof(PID)
                                          : 0;
            row.locator_read_bytes = include_graph_inputs
                                         ? trace.candidates *
                                               model.locator_bytes_per_candidate
                                         : 0;
            row.short_or_edge_code_read_bytes = bytes.short_code;
            row.short_factor_read_bytes = bytes.short_factor_values;
            row.query_lut_read_bytes = bytes.query_lut;
            row.long_code_read_bytes = bytes.accurate_long_code;
            row.long_factor_value_read_bytes = bytes.accurate_factor_values;
            row.accurate_query_read_bytes = bytes.accurate_query;
            row.cluster_prepare_input_bytes = bytes.cluster_prepare_inputs;
            row.cluster_prepare_query_state_write_bytes =
                bytes.cluster_prepare_query_state_writes;
            row.cluster_prepare_lut_write_bytes =
                bytes.cluster_prepare_lut_writes;
            row.total_logical_input_bytes =
                bytes.totalLogicalReads() + row.graph_id_read_bytes +
                row.locator_read_bytes;
            row.logical_input_bytes_per_candidate =
                static_cast<double>(row.total_logical_input_bytes) /
                static_cast<double>(row.candidates);
            const double cacheline_accurate =
                static_cast<double>(trace.candidates) *
                model.accurate_cacheline_read_bytes_per_candidate();
            row.cacheline_input_bytes_per_candidate =
                (static_cast<double>(
                     trace.block_scan_calls * model.block_scan_logical_read_bytes() +
                     trace.cluster_prepare_calls * model.cluster_prepare_input_bytes +
                     row.graph_id_read_bytes) +
                 static_cast<double>(
                     include_graph_inputs
                         ? trace.candidates * analysis::kCacheLineBytes
                         : 0) +
                 cacheline_accurate) /
                static_cast<double>(trace.candidates);
            row.modeled_index_bytes_per_node =
                model.full_saq_payload_bytes_per_vector() +
                degree_ * sizeof(PID) + model.locator_bytes_per_candidate;
            row.actual_saq_index_bytes_per_vector = actual_saq_bytes;
            row.query_cluster_cache_bytes = cached_cluster_state
                                                ? trace_stats_.unique_query_clusters *
                                                      model.query_state_bytes
                                                : 0;
            rows.push_back(row);
        };

        addSaq(
            "saq_fast", "candidate_order", fast,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.candidates,
             trace_stats_.sequential_cluster_prepares},
            false, true);
        addSaq(
            "saq_prefix_acc1", "candidate_order", prefix1,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.candidates,
             trace_stats_.sequential_cluster_prepares},
            false, true);
        addSaq(
            "saq_fast", "grouped_block_lower_bound", fast,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.grouped_block_scans,
             trace_stats_.grouped_cluster_prepares},
            false, true);
        addSaq(
            "saq_prefix_acc1", "grouped_block_lower_bound", prefix1,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.grouped_block_scans,
             trace_stats_.grouped_cluster_prepares},
            false, true);
        addSaq(
            "saq_fast", "grouped_cached_cluster_lower_bound", fast,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.grouped_block_scans, 0},
            true, true);
        addSaq(
            "saq_prefix_acc1", "grouped_cached_cluster_lower_bound", prefix1,
            {trace_stats_.root_events, trace_stats_.candidates,
             trace_stats_.grouped_block_scans, 0},
            true, true);
        const analysis::SaqTraceWork perfect_full_block{
            trace_stats_.queries,
            trace_stats_.queries * KFastScanSize,
            trace_stats_.queries,
            0,
        };
        addSaq(
            "saq_fast", "perfect_full_block_kernel_lower_bound", fast,
            perfect_full_block, false, false);
        addSaq(
            "saq_prefix_acc1", "perfect_full_block_kernel_lower_bound",
            prefix1, perfect_full_block, false, false);
        return rows;
    }

    void write(
        const std::vector<TrialResult> &trials,
        const std::vector<SummaryResult> &summaries,
        const std::vector<WorkRow> &work) const {
        ensureParent(output_prefix_);
        {
            std::ofstream out(output_prefix_ + ".trials.csv");
            out << std::setprecision(17);
            out << "component,unit,trial,units_per_round,timed_rounds,total_units,elapsed_ns,ns_per_unit,checksum\n";
            for (const auto &row : trials) {
                out << row.component << ',' << row.unit << ',' << row.trial << ','
                    << row.units_per_round << ',' << row.timed_rounds << ','
                    << row.units_per_round * row.timed_rounds << ','
                    << row.elapsed_ns << ',' << row.ns_per_unit << ','
                    << row.checksum << '\n';
            }
        }
        {
            std::ofstream out(output_prefix_ + ".summary.csv");
            out << std::setprecision(17);
            out << "component,unit,trials,units_per_round,timed_rounds,median_ns_per_unit,p10_ns_per_unit,p90_ns_per_unit,min_ns_per_unit,max_ns_per_unit\n";
            for (const auto &row : summaries) {
                out << row.component << ',' << row.unit << ',' << row.trials << ','
                    << row.units_per_round << ',' << row.timed_rounds << ','
                    << row.median_ns_per_unit << ',' << row.p10_ns_per_unit << ','
                    << row.p90_ns_per_unit << ',' << row.min_ns_per_unit << ','
                    << row.max_ns_per_unit << '\n';
            }
        }
        {
            std::ofstream out(output_prefix_ + ".work.csv");
            out << std::setprecision(17);
            out << "estimator,schedule,root_events,candidates,block_scan_calls,cluster_prepare_calls,graph_id_read_bytes,locator_read_bytes,short_or_edge_code_read_bytes,short_factor_read_bytes,query_lut_read_bytes,long_code_read_bytes,long_factor_value_read_bytes,accurate_query_read_bytes,cluster_prepare_input_bytes,cluster_prepare_query_state_write_bytes,cluster_prepare_lut_write_bytes,exact_current_vector_read_bytes,total_logical_input_bytes,logical_input_bytes_per_candidate,cacheline_input_bytes_per_candidate,modeled_index_bytes_per_node,actual_saq_index_bytes_per_vector,duplicated_neighbor_code_bytes_per_node,query_cluster_cache_bytes\n";
            for (const auto &row : work) {
                out << row.estimator << ',' << row.schedule << ','
                    << row.root_events << ',' << row.candidates << ','
                    << row.block_scan_calls << ',' << row.cluster_prepare_calls << ','
                    << row.graph_id_read_bytes << ',' << row.locator_read_bytes << ','
                    << row.short_or_edge_code_read_bytes << ','
                    << row.short_factor_read_bytes << ','
                    << row.query_lut_read_bytes << ',' << row.long_code_read_bytes << ','
                    << row.long_factor_value_read_bytes << ','
                    << row.accurate_query_read_bytes << ','
                    << row.cluster_prepare_input_bytes << ','
                    << row.cluster_prepare_query_state_write_bytes << ','
                    << row.cluster_prepare_lut_write_bytes << ','
                    << row.exact_current_vector_read_bytes << ','
                    << row.total_logical_input_bytes << ','
                    << row.logical_input_bytes_per_candidate << ','
                    << row.cacheline_input_bytes_per_candidate << ','
                    << row.modeled_index_bytes_per_node << ','
                    << row.actual_saq_index_bytes_per_vector << ','
                    << row.duplicated_neighbor_code_bytes_per_node << ','
                    << row.query_cluster_cache_bytes << '\n';
            }
        }
        {
            std::ofstream out(output_prefix_ + ".md");
            out << "# Isolated Graph Estimator Benchmark\n\n";
            out << "## Fixed Trace\n\n";
            out << "- data: `" << data_file_ << "`\n";
            out << "- query: `" << query_file_ << "`\n";
            out << "- SAQ index: `" << index_file_ << "`\n";
            out << "- subset: " << subset_ << "\n";
            out << "- degree: " << degree_ << "\n";
            out << "- queries: " << trace_stats_.queries << "\n";
            out << "- roots: " << trace_stats_.root_events << "\n";
            out << "- candidates: " << trace_stats_.candidates << "\n";
            out << "- sequential SAQ cluster preparations: "
                << trace_stats_.sequential_cluster_prepares << "\n";
            out << "- grouped SAQ cluster preparations: "
                << trace_stats_.grouped_cluster_prepares << "\n";
            out << "- grouped unique SAQ blocks: "
                << trace_stats_.grouped_block_scans << "\n";
            out << "- unique query-cluster states: "
                << trace_stats_.unique_query_clusters << "\n";
            out << "- trials: " << FLAGS_graph_bench_trials << "\n";
            out << "- timed rounds/trial: " << FLAGS_graph_bench_rounds << "\n";
            out << "- warmup rounds/trial: "
                << FLAGS_graph_bench_warmup_rounds << "\n\n";
            out << "Adjacency construction, edge encoding, query preparation, exact-current\n";
            out << "distance, and file output are excluded from candidate-estimator rows.\n";
            out << "Query preparation and exact-current L2 are reported separately.\n\n";
            out << "## Runtime\n\n";
            out << "| component | unit | median ns/unit | p10 | p90 |\n";
            out << "|---|---|---:|---:|---:|\n";
            for (const auto &row : summaries) {
                out << "| " << row.component << " | " << row.unit << " | "
                    << row.median_ns_per_unit << " | " << row.p10_ns_per_unit
                    << " | " << row.p90_ns_per_unit << " |\n";
            }
            out << "\n## Logical Input Work\n\n";
            out << "| estimator | schedule | input B/candidate | cache-line B/candidate | modeled index B/node |\n";
            out << "|---|---|---:|---:|---:|\n";
            for (const auto &row : work) {
                out << "| " << row.estimator << " | " << row.schedule << " | "
                    << row.logical_input_bytes_per_candidate << " | "
                    << row.cacheline_input_bytes_per_candidate << " | "
                    << row.modeled_index_bytes_per_node << " |\n";
            }
            out << "\nThe grouped SAQ rows are an implementable block-reuse lower bound, not\n";
            out << "an end-to-end graph method. The cold SymphonyQG row adds one exact\n";
            out << "960-dimensional current-vector read per root; the cached row assumes\n";
            out << "that exact current distance is already available. The perfect-full-block\n";
            out << "rows additionally grant a prepared cluster estimator and 32 useful lanes;\n";
            out << "they isolate an unattainable best-case kernel rather than the fixed trace.\n";
        }
    }

    const TraceStats &traceStats() const { return trace_stats_; }
};

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);
    QuantizeConfig config;
    const auto args = parseArgs(&config);
    LOG(INFO) << args;

    GraphEstimatorBenchmark benchmark;
    benchmark.load();
    const auto trials = benchmark.benchmark();
    const auto summaries = benchmark.summarize(trials);
    const auto work = benchmark.workRows();
    benchmark.write(trials, summaries, work);
    std::cout << "Benchmark outputs written to: "
              << FLAGS_graph_bench_output_prefix << ".{trials,summary,work}.csv/.md\n";
    std::cout << "benchmark_sink=" << benchmark_sink << '\n';
    return 0;
}

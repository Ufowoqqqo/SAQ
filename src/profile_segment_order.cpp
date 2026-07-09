#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <immintrin.h>

#include "define_options.h"
#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/IO.hpp"
#include "utils/pool.hpp"

DEFINE_int32(profile_nprobe, 200, "nprobe used by the segment-order replay");
DEFINE_int32(profile_topk, 100, "top-k used by the segment-order replay");
DEFINE_int32(profile_max_queries, 0, "maximum number of queries to replay; 0 means all queries");
DEFINE_string(profile_orders, "pca,reverse,bit_desc,dim_desc,cost_asc,risk_per_cost_desc",
              "comma-separated segment orders to evaluate");
DEFINE_string(profile_output_csv, "", "optional CSV output path for segment-order replay results");

namespace {
using namespace saqlib;

struct SegmentOrder {
    std::string name;
    std::vector<size_t> order;
};

struct ReplayResult {
    std::string order_name;
    size_t nprobe = 0;
    size_t queries = 0;
    float recall = 0;
    QueryRuntimeMetrics metrics;
};

class SegmentOrderReplaySearcher : public SaqCluEstimator<DistType::Any> {
    using SaqCluEstimator<DistType::Any>::FAST_ARRAY;
    using SaqCluEstimator<DistType::Any>::estimators_;

    std::vector<size_t> segment_order_;
    float *clu_dist_ = nullptr;
    __m512 *clu_dist512_ = nullptr;
    QueryRuntimeMetrics runtime_metrics_;

  public:
    SegmentOrderReplaySearcher(const SaqData &data, const SearcherConfig &searcher_cfg,
                               const Eigen::RowVectorXf &query, std::vector<size_t> segment_order)
        : SaqCluEstimator<DistType::Any>(data, searcher_cfg, query),
          segment_order_(std::move(segment_order)) {
        CHECK_EQ(segment_order_.size(), data.base_datas.size());
        const auto segment_count = data.base_datas.size();
        clu_dist_ = memory::align_mm<64, float>(segment_count * KFastScanSize);
        clu_dist512_ = memory::align_mm<64, __m512>(segment_count * FAST_ARRAY);
    }

    ~SegmentOrderReplaySearcher() override {
        std::free(clu_dist512_);
        std::free(clu_dist_);
    }

    QueryRuntimeMetrics getRuntimeMetrics() const {
        return runtime_metrics_;
    }

    void searchCluster(const SaqCluData *saq_clust, utils::ResultPool &KNNs) {
        const auto segment_count = saq_clust->num_segments_;
        CHECK_EQ(segment_count, estimators_.size());
        CHECK_EQ(segment_count, segment_order_.size());

        this->prepare(saq_clust);

        const auto num_blocks = saq_clust->num_blocks_;
        const auto num_points = saq_clust->num_vec_;
        float distk = KNNs.distk();

        runtime_metrics_.clusters_scanned++;
        runtime_metrics_.blocks_scanned += num_blocks;
        runtime_metrics_.valid_lanes_scanned += num_points;

        float PORTABLE_ALIGN64 curr_dist[KFastScanSize];
        __m512 curr_dist512[FAST_ARRAY];
        for (size_t blk_idx = 0; blk_idx < num_blocks; ++blk_idx) {
            curr_dist512[0] = _mm512_setzero_ps();
            curr_dist512[1] = _mm512_setzero_ps();

            const auto blk_begin = blk_idx * KFastScanSize;
            const size_t valid_lanes = std::min<size_t>(KFastScanSize, num_points - blk_begin);
            float mi = std::numeric_limits<float>::max();

            runtime_metrics_.variance_blocks++;
            for (size_t c_i = 0; c_i < segment_count; ++c_i) {
                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];
                estimator.varsEstDist(blk_idx, cd);

                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);
            }

            mi = finiteBlockMin(curr_dist512, valid_lanes, curr_dist);
            if (mi > distk) {
                runtime_metrics_.variance_pruned_blocks++;
                continue;
            }

            for (const size_t c_i : segment_order_) {
                auto &cur_cluster = saq_clust->get_segment(c_i);
                if (cur_cluster.num_bits_ == 0) {
                    continue;
                }

                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];

                runtime_metrics_.fast_segment_calls++;
                curr_dist512[0] = _mm512_sub_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_sub_ps(curr_dist512[1], cd[1]);

                estimator.compFastDist(blk_idx, cd);
                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);

                mi = finiteBlockMin(curr_dist512, valid_lanes, curr_dist);
                if (mi > distk) {
                    runtime_metrics_.fast_pruned_blocks++;
                    break;
                }
            }

            if (mi > distk) {
                continue;
            }

            _mm512_store_ps(curr_dist, curr_dist512[0]);
            _mm512_store_ps(curr_dist + 16, curr_dist512[1]);

            for (size_t c_i = 0; c_i < segment_count; ++c_i) {
                _mm512_store_ps(clu_dist_ + c_i * KFastScanSize, clu_dist512_[c_i * FAST_ARRAY]);
                _mm512_store_ps(clu_dist_ + c_i * KFastScanSize + 16, clu_dist512_[c_i * FAST_ARRAY + 1]);
            }

            for (size_t j = 0; j < valid_lanes; ++j) {
                if (curr_dist[j] >= distk) {
                    continue;
                }

                const auto idx = blk_begin + j;
                runtime_metrics_.accurate_candidate_attempts++;
                float acc_dist = curr_dist[j];

                for (size_t order_pos = 0; order_pos < segment_order_.size(); ++order_pos) {
                    const size_t c_i = segment_order_[order_pos];
                    auto &estimator = estimators_[c_i];
                    runtime_metrics_.accurate_segment_calls++;
                    acc_dist += estimator.compAccurateDist(idx) - clu_dist_[c_i * KFastScanSize + j];
                    if (acc_dist >= distk) {
                        if (order_pos + 1 < segment_order_.size()) {
                            runtime_metrics_.accurate_segment_early_exits++;
                        }
                        break;
                    }
                }

                runtime_metrics_.result_insert_attempts++;
                if (KNNs.insert(saq_clust->ids()[idx], acc_dist)) {
                    runtime_metrics_.result_insert_successes++;
                }
                distk = KNNs.distk();
            }
        }

        runtime_metrics_.fast_bitsum = 0;
        runtime_metrics_.acc_bitsum = 0;
        for (size_t c_i = 0; c_i < segment_count; ++c_i) {
            auto metrics = estimators_[c_i].getRuntimeMetrics();
            runtime_metrics_.fast_bitsum += metrics.fast_bitsum;
            runtime_metrics_.acc_bitsum += metrics.acc_bitsum;
        }
        runtime_metrics_.total_comp_cnt += num_blocks * KFastScanSize;
    }

  private:
    static bool rawFinite(float value) {
        uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        return (bits & 0x7f800000u) != 0x7f800000u;
    }

    static float finiteBlockMin(const __m512 *dist, size_t valid_lanes, float *scratch) {
        _mm512_store_ps(scratch, dist[0]);
        _mm512_store_ps(scratch + 16, dist[1]);
        float mi = std::numeric_limits<float>::max();
        for (size_t lane = 0; lane < valid_lanes; ++lane) {
            const float val = scratch[lane];
            if (rawFinite(val) && val < mi) {
                mi = val;
            }
        }
        return mi;
    }
};

std::vector<std::string> splitNames(const std::string &value) {
    std::vector<std::string> names;
    std::stringstream ss(value);
    std::string token;
    while (std::getline(ss, token, ',')) {
        if (!token.empty()) {
            names.push_back(token);
        }
    }
    return names;
}

std::vector<size_t> pcaOrder(size_t n) {
    std::vector<size_t> order(n);
    std::iota(order.begin(), order.end(), 0);
    return order;
}

double segmentVariance(const SaqData &data, size_t segment_id) {
    size_t offset = 0;
    for (size_t i = 0; i < segment_id; ++i) {
        offset += data.quant_plan[i].first;
    }
    const size_t dim = data.quant_plan[segment_id].first;
    return data.data_variance.segment(offset, dim).sum();
}

std::vector<size_t> sortedOrder(const SaqData &data, const std::string &name) {
    auto order = pcaOrder(data.quant_plan.size());
    if (name == "pca") {
        return order;
    }
    if (name == "reverse") {
        std::reverse(order.begin(), order.end());
        return order;
    }

    std::sort(order.begin(), order.end(), [&](size_t lhs, size_t rhs) {
        const auto [lhs_dim, lhs_bits] = data.quant_plan[lhs];
        const auto [rhs_dim, rhs_bits] = data.quant_plan[rhs];
        if (name == "bit_desc") {
            return std::make_tuple(lhs_bits, lhs_dim, static_cast<size_t>(data.quant_plan.size() - lhs)) >
                   std::make_tuple(rhs_bits, rhs_dim, static_cast<size_t>(data.quant_plan.size() - rhs));
        }
        if (name == "dim_desc") {
            return std::make_tuple(lhs_dim, lhs_bits, static_cast<size_t>(data.quant_plan.size() - lhs)) >
                   std::make_tuple(rhs_dim, rhs_bits, static_cast<size_t>(data.quant_plan.size() - rhs));
        }
        if (name == "cost_asc") {
            const size_t lhs_cost = lhs_bits ? lhs_dim : std::numeric_limits<size_t>::max();
            const size_t rhs_cost = rhs_bits ? rhs_dim : std::numeric_limits<size_t>::max();
            return std::make_tuple(lhs_cost, lhs, lhs_bits) < std::make_tuple(rhs_cost, rhs, rhs_bits);
        }
        if (name == "risk_per_cost_desc") {
            const double lhs_cost = static_cast<double>(std::max<size_t>(1, lhs_dim) * std::max<size_t>(1, lhs_bits));
            const double rhs_cost = static_cast<double>(std::max<size_t>(1, rhs_dim) * std::max<size_t>(1, rhs_bits));
            const double lhs_score = segmentVariance(data, lhs) / lhs_cost;
            const double rhs_score = segmentVariance(data, rhs) / rhs_cost;
            if (lhs_score != rhs_score) {
                return lhs_score > rhs_score;
            }
            return lhs < rhs;
        }
        CHECK(false) << "unknown segment order: " << name;
        return lhs < rhs;
    });
    return order;
}

std::string orderToString(const SegmentOrder &segment_order, const SaqData &data) {
    std::string out;
    for (size_t pos = 0; pos < segment_order.order.size(); ++pos) {
        const size_t id = segment_order.order[pos];
        if (pos) {
            out += ";";
        }
        out += fmt::format("{}:{}x{}", id, data.quant_plan[id].first, data.quant_plan[id].second);
    }
    return out;
}

std::vector<SegmentOrder> makeSegmentOrders(const SaqData &data, const std::string &names_csv) {
    std::vector<SegmentOrder> orders;
    for (const auto &name : splitNames(names_csv)) {
        orders.push_back(SegmentOrder{name, sortedOrder(data, name)});
    }
    CHECK(!orders.empty()) << "no segment orders requested";
    return orders;
}

size_t countCorrect(const UintRowMat &gt, size_t query_idx, const std::vector<PID> &results, size_t topk) {
    size_t correct = 0;
    for (size_t j = 0; j < topk; ++j) {
        for (size_t k = 0; k < topk; ++k) {
            if (gt(query_idx, k) == results[j]) {
                correct++;
                break;
            }
        }
    }
    return correct;
}

ReplayResult runReplay(const IVF &ivf, const FloatRowMat &query, const UintRowMat &gt,
                       const SegmentOrder &segment_order, size_t topk, size_t nprobe,
                       SearcherConfig searcher_cfg, size_t max_queries) {
    const size_t query_count = max_queries == 0 ? static_cast<size_t>(query.rows())
                                                : std::min(max_queries, static_cast<size_t>(query.rows()));
    const auto *saq_data = ivf.get_saq_data();
    const auto &clusters = ivf.get_pclusters();

    ReplayResult result;
    result.order_name = segment_order.name;
    result.nprobe = nprobe;
    result.queries = query_count;

    size_t total_correct = 0;
    std::vector<Candidate> centroid_dist(nprobe);
    std::vector<PID> query_results(topk);

    for (size_t q_i = 0; q_i < query_count; ++q_i) {
        ivf.get_initer()->centroids_distances(query.row(q_i), nprobe, searcher_cfg.dist_type, centroid_dist);

        utils::ResultPool KNNs(topk, searcher_cfg.dist_type == DistType::IP);
        SegmentOrderReplaySearcher searcher(*saq_data, searcher_cfg, query.row(q_i), segment_order.order);
        for (size_t i = 0; i < nprobe; ++i) {
            const PID cid = centroid_dist[i].id;
            searcher.searchCluster(&clusters[cid], KNNs);
        }

        KNNs.copy_results(query_results.data());
        total_correct += countCorrect(gt, q_i, query_results, topk);
        result.metrics += searcher.getRuntimeMetrics();
    }

    result.recall = static_cast<float>(total_correct) / static_cast<float>(query_count * topk);
    return result;
}

double avgMetric(size_t value, size_t queries) {
    return queries ? static_cast<double>(value) / static_cast<double>(queries) : 0.0;
}

std::string csvHeader() {
    return "order,nprobe,queries,recall,fast_bitsum,acc_bitsum,total_comp_cnt,"
           "clusters_scanned,blocks_scanned,valid_lanes_scanned,variance_blocks,"
           "variance_pruned_blocks,fast_segment_calls,fast_pruned_blocks,"
           "accurate_candidate_attempts,accurate_segment_calls,"
           "accurate_segment_early_exits,result_insert_attempts,"
           "result_insert_successes\n";
}

std::string csvRow(const ReplayResult &r) {
    const auto &m = r.metrics;
    return fmt::format("{},{},{},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f},{:.6f}\n",
                       r.order_name,
                       r.nprobe,
                       r.queries,
                       r.recall,
                       avgMetric(m.fast_bitsum, r.queries),
                       avgMetric(m.acc_bitsum, r.queries),
                       avgMetric(m.total_comp_cnt, r.queries),
                       avgMetric(m.clusters_scanned, r.queries),
                       avgMetric(m.blocks_scanned, r.queries),
                       avgMetric(m.valid_lanes_scanned, r.queries),
                       avgMetric(m.variance_blocks, r.queries),
                       avgMetric(m.variance_pruned_blocks, r.queries),
                       avgMetric(m.fast_segment_calls, r.queries),
                       avgMetric(m.fast_pruned_blocks, r.queries),
                       avgMetric(m.accurate_candidate_attempts, r.queries),
                       avgMetric(m.accurate_segment_calls, r.queries),
                       avgMetric(m.accurate_segment_early_exits, r.queries),
                       avgMetric(m.result_insert_attempts, r.queries),
                       avgMetric(m.result_insert_successes, r.queries));
}

} // namespace

int main(int argc, char **argv) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    QuantizeConfig cfg;
    parseArgs(&cfg);

    SearcherConfig searcher_cfg;
    searcher_cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;
    searcher_cfg.searcher_safe_block_min = FLAGS_searcher_safe_block_min;
    searcher_cfg.searcher_safe_block_min_mode = FLAGS_searcher_safe_block_min_mode;
    searcher_cfg.dist_type = FLAGS_searcher_dist_type == 1 ? DistType::IP : DistType::L2Sqr;

    DataFilePaths paths;
    FloatRowMat query;
    UintRowMat gt;
    utils::load_something<float, FloatRowMat>(paths.query_file.c_str(), query);
    utils::load_something<PID, UintRowMat>(paths.gt_file.c_str(), gt);
    CHECK_GE(static_cast<size_t>(gt.cols()), static_cast<size_t>(FLAGS_profile_topk));

    IVF ivf;
    ivf.load(paths.quant_file.c_str());
    CHECK_EQ(static_cast<size_t>(query.cols()), ivf.num_dim());

    const auto *saq_data = ivf.get_saq_data();
    CHECK(saq_data != nullptr);
    const auto orders = makeSegmentOrders(*saq_data, FLAGS_profile_orders);

    std::string output = csvHeader();
    for (const auto &order : orders) {
        LOG(INFO) << "Replay order " << order.name << ": " << orderToString(order, *saq_data);
        const ReplayResult result = runReplay(ivf, query, gt, order,
                                              static_cast<size_t>(FLAGS_profile_topk),
                                              static_cast<size_t>(FLAGS_profile_nprobe),
                                              searcher_cfg,
                                              static_cast<size_t>(FLAGS_profile_max_queries));
        output += csvRow(result);
    }

    std::cout << output;
    if (!FLAGS_profile_output_csv.empty()) {
        std::ofstream csv(FLAGS_profile_output_csv, std::ios::out);
        CHECK(csv.good()) << "cannot write " << FLAGS_profile_output_csv;
        csv << output;
    }

    return 0;
}

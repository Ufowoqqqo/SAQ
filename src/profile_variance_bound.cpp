#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
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
#include "utils/memory.hpp"
#include "utils/pool.hpp"

DEFINE_int32(profile_nprobe, 200, "nprobe used by the variance-bound replay");
DEFINE_int32(profile_topk, 100, "top-k used by the variance-bound replay");
DEFINE_int32(profile_max_queries, 0, "maximum number of queries to replay; 0 means all queries");
DEFINE_string(profile_output_csv, "", "optional CSV output path for variance-bound summary");

namespace {
using namespace saqlib;

struct VarianceBoundStats {
    size_t queries = 0;
    size_t clusters_scanned = 0;
    size_t blocks = 0;
    size_t boundary_not_finite_blocks = 0;
    size_t finite_boundary_blocks = 0;
    size_t variance_pruned_blocks = 0;
    size_t unpruned_finite_blocks = 0;
    size_t no_bound_prunable_blocks = 0;
    size_t fast_pruned_after_variance_blocks = 0;

    size_t rel_gap_le_1pct = 0;
    size_t rel_gap_le_5pct = 0;
    size_t rel_gap_le_10pct = 0;
    size_t rel_gap_le_25pct = 0;
    size_t rel_gap_le_50pct = 0;

    std::vector<double> margins;
    std::vector<double> rel_gaps;
    std::vector<double> required_slack_fractions;

    void merge(const VarianceBoundStats &other) {
        queries += other.queries;
        clusters_scanned += other.clusters_scanned;
        blocks += other.blocks;
        boundary_not_finite_blocks += other.boundary_not_finite_blocks;
        finite_boundary_blocks += other.finite_boundary_blocks;
        variance_pruned_blocks += other.variance_pruned_blocks;
        unpruned_finite_blocks += other.unpruned_finite_blocks;
        no_bound_prunable_blocks += other.no_bound_prunable_blocks;
        fast_pruned_after_variance_blocks += other.fast_pruned_after_variance_blocks;

        rel_gap_le_1pct += other.rel_gap_le_1pct;
        rel_gap_le_5pct += other.rel_gap_le_5pct;
        rel_gap_le_10pct += other.rel_gap_le_10pct;
        rel_gap_le_25pct += other.rel_gap_le_25pct;
        rel_gap_le_50pct += other.rel_gap_le_50pct;

        margins.insert(margins.end(), other.margins.begin(), other.margins.end());
        rel_gaps.insert(rel_gaps.end(), other.rel_gaps.begin(), other.rel_gaps.end());
        required_slack_fractions.insert(required_slack_fractions.end(),
                                        other.required_slack_fractions.begin(),
                                        other.required_slack_fractions.end());
    }
};

class VarianceBoundProfiler : public SaqCluEstimator<DistType::Any> {
    using SaqCluEstimator<DistType::Any>::FAST_ARRAY;
    using SaqCluEstimator<DistType::Any>::estimators_;

    SaqCluEstimator<DistType::Any> no_bound_estimator_;
    float *clu_dist_ = nullptr;
    __m512 *clu_dist512_ = nullptr;
    VarianceBoundStats stats_;

  public:
    VarianceBoundProfiler(const SaqData &data, const SearcherConfig &searcher_cfg,
                          const Eigen::RowVectorXf &query)
        : SaqCluEstimator<DistType::Any>(data, searcher_cfg, query),
          no_bound_estimator_(data, noBoundConfig(searcher_cfg), query) {
        const auto segment_count = data.base_datas.size();
        clu_dist_ = memory::align_mm<64, float>(segment_count * KFastScanSize);
        clu_dist512_ = memory::align_mm<64, __m512>(segment_count * FAST_ARRAY);
    }

    ~VarianceBoundProfiler() override {
        std::free(clu_dist512_);
        std::free(clu_dist_);
    }

    const VarianceBoundStats &stats() const {
        return stats_;
    }

    void searchCluster(const SaqCluData *saq_clust, utils::ResultPool &KNNs) {
        const auto segment_count = saq_clust->num_segments_;
        CHECK_EQ(segment_count, estimators_.size());

        this->prepare(saq_clust);
        no_bound_estimator_.prepare(saq_clust);

        const auto num_blocks = saq_clust->num_blocks_;
        const auto num_points = saq_clust->num_vec_;
        float distk = KNNs.distk();

        stats_.clusters_scanned++;
        stats_.blocks += num_blocks;

        float PORTABLE_ALIGN64 curr_dist[KFastScanSize];
        __m512 curr_dist512[FAST_ARRAY];
        __m512 no_bound_dist512[FAST_ARRAY];

        for (size_t blk_idx = 0; blk_idx < num_blocks; ++blk_idx) {
            curr_dist512[0] = _mm512_setzero_ps();
            curr_dist512[1] = _mm512_setzero_ps();

            const auto blk_begin = blk_idx * KFastScanSize;
            const size_t valid_lanes = std::min<size_t>(KFastScanSize, num_points - blk_begin);

            for (size_t c_i = 0; c_i < segment_count; ++c_i) {
                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];
                estimator.varsEstDist(blk_idx, cd);

                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);
            }

            no_bound_estimator_.varsEstDist(blk_idx, no_bound_dist512);

            float mi = finiteBlockMin(curr_dist512, valid_lanes, curr_dist);
            const float no_bound_mi = finiteBlockMin(no_bound_dist512, valid_lanes, curr_dist);
            recordVarianceBlock(mi, no_bound_mi, distk);

            if (mi > distk) {
                stats_.variance_pruned_blocks++;
                continue;
            }

            bool fast_pruned = false;
            for (size_t c_i = 0; c_i < segment_count; ++c_i) {
                auto &cur_cluster = saq_clust->get_segment(c_i);
                if (cur_cluster.num_bits_ == 0) {
                    continue;
                }

                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];
                curr_dist512[0] = _mm512_sub_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_sub_ps(curr_dist512[1], cd[1]);

                estimator.compFastDist(blk_idx, cd);
                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);

                mi = finiteBlockMin(curr_dist512, valid_lanes, curr_dist);
                if (mi > distk) {
                    stats_.fast_pruned_after_variance_blocks++;
                    fast_pruned = true;
                    break;
                }
            }

            if (fast_pruned) {
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
                float acc_dist = curr_dist[j];
                for (size_t c_i = 0; c_i < segment_count; ++c_i) {
                    auto &estimator = estimators_[c_i];
                    acc_dist += estimator.compAccurateDist(idx) - clu_dist_[c_i * KFastScanSize + j];
                    if (acc_dist >= distk) {
                        break;
                    }
                }

                KNNs.insert(saq_clust->ids()[idx], acc_dist);
                distk = KNNs.distk();
            }
        }
    }

  private:
    static SearcherConfig noBoundConfig(SearcherConfig cfg) {
        cfg.searcher_vars_bound_m = 0;
        return cfg;
    }

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

    static bool finiteBoundary(float distk) {
        return std::isfinite(distk) && distk < std::numeric_limits<float>::max() / 2;
    }

    void recordVarianceBlock(float mi, float no_bound_mi, float distk) {
        if (!finiteBoundary(distk)) {
            stats_.boundary_not_finite_blocks++;
            return;
        }

        stats_.finite_boundary_blocks++;
        stats_.margins.push_back(static_cast<double>(mi) - static_cast<double>(distk));

        if (mi > distk) {
            return;
        }

        stats_.unpruned_finite_blocks++;
        const double gap = static_cast<double>(distk) - static_cast<double>(mi);
        const double denom = std::max(1e-12, std::fabs(static_cast<double>(distk)));
        const double rel_gap = gap / denom;
        stats_.rel_gaps.push_back(rel_gap);

        stats_.rel_gap_le_1pct += rel_gap <= 0.01;
        stats_.rel_gap_le_5pct += rel_gap <= 0.05;
        stats_.rel_gap_le_10pct += rel_gap <= 0.10;
        stats_.rel_gap_le_25pct += rel_gap <= 0.25;
        stats_.rel_gap_le_50pct += rel_gap <= 0.50;

        const double removable_slack = static_cast<double>(no_bound_mi) - static_cast<double>(mi);
        if (removable_slack > 0 && no_bound_mi > distk) {
            stats_.no_bound_prunable_blocks++;
            stats_.required_slack_fractions.push_back(gap / removable_slack);
        }
    }
};

double ratio(size_t num, size_t den) {
    return den ? static_cast<double>(num) / static_cast<double>(den) : 0.0;
}

double quantile(std::vector<double> values, double q) {
    if (values.empty()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    std::sort(values.begin(), values.end());
    const double pos = q * static_cast<double>(values.size() - 1);
    const size_t lo = static_cast<size_t>(std::floor(pos));
    const size_t hi = static_cast<size_t>(std::ceil(pos));
    if (lo == hi) {
        return values[lo];
    }
    const double frac = pos - static_cast<double>(lo);
    return values[lo] * (1.0 - frac) + values[hi] * frac;
}

std::string csvHeader() {
    return "nprobe,queries,clusters_scanned,blocks,finite_boundary_blocks,"
           "boundary_not_finite_blocks,variance_pruned_blocks,"
           "unpruned_finite_blocks,no_bound_prunable_blocks,"
           "fast_pruned_after_variance_blocks,variance_prune_rate_all,"
           "variance_prune_rate_finite,no_bound_prunable_rate_unpruned,"
           "fast_prune_rate_after_variance,rel_gap_le_1pct,rel_gap_le_5pct,"
           "rel_gap_le_10pct,rel_gap_le_25pct,rel_gap_le_50pct,"
           "rel_gap_q10,rel_gap_q25,rel_gap_q50,rel_gap_q75,rel_gap_q90,"
           "required_slack_fraction_q10,required_slack_fraction_q25,"
           "required_slack_fraction_q50,required_slack_fraction_q75,"
           "required_slack_fraction_q90\n";
}

std::string csvRow(size_t nprobe, const VarianceBoundStats &s) {
    return fmt::format("{},{},{},{},{},{},{},{},{},{},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f},{:.8f}\n",
                       nprobe,
                       s.queries,
                       s.clusters_scanned,
                       s.blocks,
                       s.finite_boundary_blocks,
                       s.boundary_not_finite_blocks,
                       s.variance_pruned_blocks,
                       s.unpruned_finite_blocks,
                       s.no_bound_prunable_blocks,
                       s.fast_pruned_after_variance_blocks,
                       ratio(s.variance_pruned_blocks, s.blocks),
                       ratio(s.variance_pruned_blocks, s.finite_boundary_blocks),
                       ratio(s.no_bound_prunable_blocks, s.unpruned_finite_blocks),
                       ratio(s.fast_pruned_after_variance_blocks,
                             s.blocks - s.variance_pruned_blocks),
                       ratio(s.rel_gap_le_1pct, s.unpruned_finite_blocks),
                       ratio(s.rel_gap_le_5pct, s.unpruned_finite_blocks),
                       ratio(s.rel_gap_le_10pct, s.unpruned_finite_blocks),
                       ratio(s.rel_gap_le_25pct, s.unpruned_finite_blocks),
                       ratio(s.rel_gap_le_50pct, s.unpruned_finite_blocks),
                       quantile(s.rel_gaps, 0.10),
                       quantile(s.rel_gaps, 0.25),
                       quantile(s.rel_gaps, 0.50),
                       quantile(s.rel_gaps, 0.75),
                       quantile(s.rel_gaps, 0.90),
                       quantile(s.required_slack_fractions, 0.10),
                       quantile(s.required_slack_fractions, 0.25),
                       quantile(s.required_slack_fractions, 0.50),
                       quantile(s.required_slack_fractions, 0.75),
                       quantile(s.required_slack_fractions, 0.90));
}

VarianceBoundStats runProfile(const IVF &ivf, const FloatRowMat &query, size_t nprobe,
                              size_t topk, SearcherConfig searcher_cfg, size_t max_queries) {
    const size_t query_count = max_queries == 0 ? static_cast<size_t>(query.rows())
                                                : std::min(max_queries, static_cast<size_t>(query.rows()));
    const auto *saq_data = ivf.get_saq_data();
    const auto &clusters = ivf.get_pclusters();
    CHECK(saq_data != nullptr);

    VarianceBoundStats total;
    total.queries = query_count;

    std::vector<Candidate> centroid_dist(nprobe);
    for (size_t q_i = 0; q_i < query_count; ++q_i) {
        ivf.get_initer()->centroids_distances(query.row(q_i), nprobe, searcher_cfg.dist_type, centroid_dist);

        utils::ResultPool KNNs(topk, searcher_cfg.dist_type == DistType::IP);
        VarianceBoundProfiler profiler(*saq_data, searcher_cfg, query.row(q_i));
        for (size_t i = 0; i < nprobe; ++i) {
            const PID cid = centroid_dist[i].id;
            profiler.searchCluster(&clusters[cid], KNNs);
        }
        total.merge(profiler.stats());
    }

    total.queries = query_count;
    return total;
}

} // namespace

int main(int argc, char **argv) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    SearcherConfig searcher_cfg;
    searcher_cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;
    searcher_cfg.searcher_safe_block_min = FLAGS_searcher_safe_block_min;
    searcher_cfg.searcher_safe_block_min_mode = FLAGS_searcher_safe_block_min_mode;
    searcher_cfg.dist_type = FLAGS_searcher_dist_type == 1 ? DistType::IP : DistType::L2Sqr;

    DataFilePaths paths;
    FloatRowMat query;
    utils::load_something<float, FloatRowMat>(paths.query_file.c_str(), query);

    IVF ivf;
    ivf.load(paths.quant_file.c_str());
    CHECK_EQ(static_cast<size_t>(query.cols()), ivf.num_dim());

    const auto stats = runProfile(ivf, query,
                                  static_cast<size_t>(FLAGS_profile_nprobe),
                                  static_cast<size_t>(FLAGS_profile_topk),
                                  searcher_cfg,
                                  static_cast<size_t>(FLAGS_profile_max_queries));

    const std::string output = csvHeader() + csvRow(static_cast<size_t>(FLAGS_profile_nprobe), stats);
    std::cout << output;
    if (!FLAGS_profile_output_csv.empty()) {
        std::ofstream csv(FLAGS_profile_output_csv, std::ios::out);
        CHECK(csv.good()) << "cannot write " << FLAGS_profile_output_csv;
        csv << output;
    }

    return 0;
}

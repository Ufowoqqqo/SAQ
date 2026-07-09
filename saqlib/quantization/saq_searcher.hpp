#pragma once

#include <algorithm>
#include <bit>
#include <cstring>
#include <immintrin.h>
#include <limits>
#include <stdint.h>

#include <glog/logging.h>

#include "defines.hpp"
#include "quantization/caq/caq_estimator.hpp"
#include "quantization/cluster_data.hpp"
#include "quantization/config.h"
#include "quantization/saq_data.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/memory.hpp"
#include "utils/pool.hpp"

namespace saqlib {
template <DistType kDistType = DistType::Any>
class SAQSearcher : public SaqCluEstimator<kDistType> {
    using SaqCluEstimator<kDistType>::FAST_ARRAY;
    using SaqCluEstimator<kDistType>::estimators_;

    float *clu_dist_;
    __m512 *clu_dist512_;
    const int safe_block_min_mode_;
    QueryRuntimeMetrics runtime_metrics_;

  public:
    /**
     * @brief Construct a new SAQSearcher object
     *
     * Initializes the SAQ searcher with quantized data, configuration, and query vector.
     *
     * @param data Pointer to SAQ data structure containing quantized base vectors
     * @param searcher_cfg Configuration parameters for search behavior
     * @param query Pointer to query vector (Eigen row vector format)
     */
    SAQSearcher(const SaqData &data, const SearcherConfig &searcher_cfg, const Eigen::RowVectorXf &query)
        : SaqCluEstimator<kDistType>(data, searcher_cfg, query),
          safe_block_min_mode_(normalizeSafeBlockMinMode(searcher_cfg)) {
        CHECK(kDistType == DistType::Any || kDistType == searcher_cfg.dist_type) << "distance type mismatch";
        auto clus_num = data.base_datas.size();
        clu_dist_ = memory::align_mm<64, float>(clus_num * KFastScanSize);
        clu_dist512_ = memory::align_mm<64, __m512>(clus_num * FAST_ARRAY);
    }

    ~SAQSearcher() {
        std::free(clu_dist512_);
        std::free(clu_dist_);
    }

    auto getRuntimeMetrics() const {
        return runtime_metrics_;
    }

    /**
     * @brief Search for nearest neighbors in multiple clusters
     *
     * Performs approximate nearest neighbor search using SAQ quantization with
     * multi-stage filtering: variance estimation, fast distance computation,
     * and accurate distance refinement. Supports optional variance-based pruning.
     *
     * @tparam enable_var Enable variance estimation for early pruning (default: true)
     * @param saq_clust Pointer to SAQ cluster data containing quantized vectors
     * @param KNNs Reference to result pool for storing k-nearest neighbors
     */
    template <bool enable_var = true>
    void searchCluster(const SaqCluData *saq_clust, utils::ResultPool &KNNs) {
        auto clus_num = saq_clust->num_segments_;
        CHECK_EQ(clus_num, estimators_.size());

        if (clus_num == 1) {
            scanCluster(&saq_clust->get_segment(0), KNNs);
            return;
        }

        // 0. prepare current cluster
        this->prepare(saq_clust);

        auto num_blocks = saq_clust->num_blocks_;
        float distk = KNNs.distk();
        const auto num_points = saq_clust->num_vec_;
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

            // 1. computes distance estimates using variance information for early pruning.
            if constexpr (enable_var) {
                runtime_metrics_.variance_blocks++;
                for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                    auto &estimator = estimators_[c_i];
                    auto cd = &clu_dist512_[c_i * FAST_ARRAY];
                    estimator.varsEstDist(blk_idx, cd);

                    curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                    curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);
                }

                mi = blockMin(curr_dist512, valid_lanes, curr_dist);
                if (mi > distk) {
                    runtime_metrics_.variance_pruned_blocks++;
                    continue;
                }
            }

            // 2. use 1st bit to compute fast distance
            for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                auto &cur_cluster = saq_clust->get_segment(c_i);
                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];

                if (cur_cluster.num_bits_ == 0)
                    continue;
                runtime_metrics_.fast_segment_calls++;
                if constexpr (enable_var) {
                    curr_dist512[0] = _mm512_sub_ps(curr_dist512[0], cd[0]);
                    curr_dist512[1] = _mm512_sub_ps(curr_dist512[1], cd[1]);
                }

                estimator.compFastDist(blk_idx, cd);
                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);

                mi = blockMin(curr_dist512, valid_lanes, curr_dist);
                if (mi > distk) {
                    runtime_metrics_.fast_pruned_blocks++;
                    break;
                }
            }

            // 3. use full bits to compute accurate distance
            if (mi <= distk) {
                _mm512_store_ps(curr_dist, curr_dist512[0]);
                _mm512_store_ps(curr_dist + 16, curr_dist512[1]);

                for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                    _mm512_store_ps(clu_dist_ + c_i * KFastScanSize, clu_dist512_[c_i * FAST_ARRAY]);
                    _mm512_store_ps(clu_dist_ + c_i * KFastScanSize + 16, clu_dist512_[c_i * FAST_ARRAY + 1]);
                }
                for (size_t j = 0; j < KFastScanSize; ++j) {
                    if (curr_dist[j] < distk) {
                        auto idx = blk_begin + j;
                        if (idx >= num_points) {
                            break;
                        }
                        runtime_metrics_.accurate_candidate_attempts++;
                        float acc_dist = curr_dist[j];
                        for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                            auto &estimator = estimators_[c_i];
                            runtime_metrics_.accurate_segment_calls++;
                            acc_dist += estimator.compAccurateDist(idx) - clu_dist_[c_i * KFastScanSize + j];
                            if (acc_dist >= distk) {
                                if (c_i + 1 < clus_num) {
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
            }
        }

        runtime_metrics_.fast_bitsum = 0;
        runtime_metrics_.acc_bitsum = 0;
        for (size_t c_i = 0; c_i < clus_num; ++c_i) {
            auto &estimator = estimators_[c_i];
            auto metrics = estimator.getRuntimeMetrics();
            runtime_metrics_.acc_bitsum += metrics.acc_bitsum;
            runtime_metrics_.fast_bitsum += metrics.fast_bitsum;
        }
        runtime_metrics_.total_comp_cnt += num_blocks * KFastScanSize;
    }

  private:
    static int normalizeSafeBlockMinMode(const SearcherConfig &cfg) {
        CHECK_GE(cfg.searcher_safe_block_min_mode, 0);
        CHECK_LE(cfg.searcher_safe_block_min_mode, 2);
        if (cfg.searcher_safe_block_min && cfg.searcher_safe_block_min_mode == 0) {
            return 1;
        }
        return cfg.searcher_safe_block_min_mode;
    }

    static bool rawFinite(float value) {
        uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        return (bits & 0x7f800000u) != 0x7f800000u;
    }

    static __mmask16 lowMask(size_t n) {
        return n >= 16 ? 0xffff : static_cast<__mmask16>((1u << n) - 1u);
    }

    static __m512 finiteOrMax(__m512 value, __mmask16 valid_mask) {
        const __m512i bits = _mm512_castps_si512(value);
        const __m512i exp = _mm512_and_si512(bits, _mm512_set1_epi32(0x7f800000));
        const __mmask16 finite_mask = _mm512_cmpneq_epi32_mask(exp, _mm512_set1_epi32(0x7f800000));
        const __mmask16 keep_mask = finite_mask & valid_mask;
        return _mm512_mask_blend_ps(keep_mask, _mm512_set1_ps(std::numeric_limits<float>::max()), value);
    }

    static float hmin16(__m512 value) {
        const __m256 lo = _mm512_castps512_ps256(value);
        const __m256 hi = _mm512_extractf32x8_ps(value, 1);
        const __m256 v8 = _mm256_min_ps(lo, hi);
        const __m128 v8_lo = _mm256_castps256_ps128(v8);
        const __m128 v8_hi = _mm256_extractf128_ps(v8, 1);
        const __m128 v4 = _mm_min_ps(v8_lo, v8_hi);
        const __m128 shuf1 = _mm_movehdup_ps(v4);
        const __m128 v2 = _mm_min_ps(v4, shuf1);
        const __m128 shuf2 = _mm_movehl_ps(shuf1, v2);
        const __m128 v1 = _mm_min_ss(v2, shuf2);
        return _mm_cvtss_f32(v1);
    }

    static float simdFiniteBlockMin(const __m512 *dist, size_t valid_lanes) {
        const __mmask16 mask0 = lowMask(std::min<size_t>(valid_lanes, 16));
        const __mmask16 mask1 = valid_lanes > 16 ? lowMask(valid_lanes - 16) : 0;
        const __m512 v0 = finiteOrMax(dist[0], mask0);
        const __m512 v1 = finiteOrMax(dist[1], mask1);
        return hmin16(_mm512_min_ps(v0, v1));
    }

    static float scalarFiniteBlockMin(const __m512 *dist, size_t valid_lanes, float *scratch) {
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

    float blockMin(const __m512 *dist, size_t valid_lanes, float *scratch) const {
        switch (safe_block_min_mode_) {
        case 0:
            return _mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]));
        case 1:
            return scalarFiniteBlockMin(dist, valid_lanes, scratch);
        case 2:
            return simdFiniteBlockMin(dist, valid_lanes);
        default:
            CHECK(false) << "bad safe block-min mode: " << safe_block_min_mode_;
            return std::numeric_limits<float>::max();
        }
    }

    void scanCluster(const CAQClusterData *clusters, utils::ResultPool &KNNs) {
        auto &estimator = estimators_[0];
        estimator.prepare(clusters);

        float distk = KNNs.distk();

        auto num_blocks = clusters->num_blocks();
        runtime_metrics_.clusters_scanned++;
        runtime_metrics_.blocks_scanned += num_blocks;
        runtime_metrics_.valid_lanes_scanned += clusters->num_vec_;

        __m512 est_dist[2];
        for (size_t blk_idx = 0; blk_idx < num_blocks; ++blk_idx) {
            auto curr_num_points = (blk_idx == num_blocks - 1) ? clusters->num_vec_ % KFastScanSize : KFastScanSize;

            runtime_metrics_.fast_segment_calls++;
            estimator.compFastDist(blk_idx, est_dist);

            __m512 simd_distk = _mm512_set1_ps(distk);
            uint32_t mask = ((uint32_t)_mm512_cmp_ps_mask(est_dist[0], simd_distk, 1)) |
                            ((uint32_t)_mm512_cmp_ps_mask(est_dist[1], simd_distk, 1) << 16);

            // The following line is important: the number of num_points is not necessarily 32.
            mask = (mask & ((1ull << curr_num_points) - 1));
            if (mask == 0) {
                runtime_metrics_.fast_pruned_blocks++;
            }

            // incremental distance computation - V2
            while (mask) {
                uint32_t j = std::countr_zero(mask);
                uint32_t lb = 1u << j;
                auto idx = KFastScanSize * blk_idx + j;
                mask -= lb;
                PID id = clusters->ids()[idx];
                runtime_metrics_.accurate_candidate_attempts++;
                runtime_metrics_.accurate_segment_calls++;
                auto ex_dist = estimator.compAccurateDist(idx);
                runtime_metrics_.result_insert_attempts++;
                if (KNNs.insert(id, ex_dist)) {
                    runtime_metrics_.result_insert_successes++;
                }
                distk = KNNs.distk();
            }
        }

        auto metrics = estimator.getRuntimeMetrics();
        runtime_metrics_.total_comp_cnt += num_blocks * KFastScanSize;
        runtime_metrics_.acc_bitsum = metrics.acc_bitsum;
        runtime_metrics_.fast_bitsum = metrics.fast_bitsum;
    }
};
} // namespace saqlib

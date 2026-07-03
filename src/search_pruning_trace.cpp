#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
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

using namespace saqlib;

DEFINE_int32(trace_topk, 100, "top-k used for pruning trace comparison");
DEFINE_string(trace_nprobes, "200", "comma-separated nprobe values");
DEFINE_string(trace_query_ids, "580,500", "comma-separated query ids to trace");
DEFINE_string(trace_target_ids, "", "optional target override: qid:pid;pid|qid:pid;pid");
DEFINE_string(trace_output, "", "output CSV path for pruning trace rows");

namespace {
struct IdLoc {
    size_t cid = 0;
    size_t local_idx = 0;
};

struct EstimateInfo {
    int accurate_rank = -1;
    int fast_rank = -1;
    int vars_rank = -1;
    float accurate_dist = std::numeric_limits<float>::quiet_NaN();
    float fast_dist = std::numeric_limits<float>::quiet_NaN();
    float vars_dist = std::numeric_limits<float>::quiet_NaN();
};

struct TargetMeta {
    std::string role;
    PID id = 0;
    int gt_rank = -1;
    int default_rank = -1;
    int custom_rank = -1;
    EstimateInfo custom_est;
};

struct TraceRow {
    int query_id = -1;
    int nprobe = -1;
    std::string role;
    PID id = 0;
    int gt_rank = -1;
    int default_rank = -1;
    int custom_rank = -1;
    int trace_final_rank = -1;
    EstimateInfo custom_est;

    int probed = 0;
    int64_t cid = -1;
    int64_t local_idx = -1;
    int64_t block_idx = -1;
    int64_t block_pos = -1;
    int64_t probe_rank = -1;
    std::string stage = "not_probed";

    float distk_before_block = std::numeric_limits<float>::quiet_NaN();
    float variance_mi = std::numeric_limits<float>::quiet_NaN();
    float variance_target = std::numeric_limits<float>::quiet_NaN();
    int fast_break_segment = -1;
    float fast_mi = std::numeric_limits<float>::quiet_NaN();
    float fast_scalar_min = std::numeric_limits<float>::quiet_NaN();
    float fast_target = std::numeric_limits<float>::quiet_NaN();
    int fast_nonfinite_count = 0;
    int fast_first_nonfinite_pos = -1;
    int64_t fast_first_nonfinite_pid = -1;
    float vector_dist = std::numeric_limits<float>::quiet_NaN();
    float vector_distk = std::numeric_limits<float>::quiet_NaN();
    int entered_refine = 0;
    int accurate_break_segment = -1;
    float candidate_dist = std::numeric_limits<float>::quiet_NaN();
    float candidate_distk = std::numeric_limits<float>::quiet_NaN();
    int would_insert = 0;
    float distk_after_candidate = std::numeric_limits<float>::quiet_NaN();
};

std::vector<int> parse_int_list(const std::string &text) {
    std::vector<int> values;
    std::stringstream ss(text);
    std::string token;
    while (std::getline(ss, token, ',')) {
        if (token.empty()) {
            continue;
        }
        size_t pos = 0;
        int value = std::stoi(token, &pos);
        CHECK_EQ(pos, token.size()) << "bad integer token: " << token;
        values.push_back(value);
    }
    return values;
}

std::unordered_map<int, std::unordered_set<PID>> parse_target_ids(const std::string &text) {
    std::unordered_map<int, std::unordered_set<PID>> targets;
    if (text.empty()) {
        return targets;
    }
    std::stringstream groups(text);
    std::string group;
    while (std::getline(groups, group, '|')) {
        if (group.empty()) {
            continue;
        }
        const auto sep = group.find(':');
        CHECK(sep != std::string::npos) << "bad trace_target_ids group: " << group;
        size_t pos = 0;
        const int qid = std::stoi(group.substr(0, sep), &pos);
        CHECK_EQ(pos, sep) << "bad query id in trace_target_ids group: " << group;
        std::stringstream ids(group.substr(sep + 1));
        std::string id_token;
        while (std::getline(ids, id_token, ';')) {
            if (id_token.empty()) {
                continue;
            }
            size_t id_pos = 0;
            const auto id = static_cast<PID>(std::stoul(id_token, &id_pos));
            CHECK_EQ(id_pos, id_token.size()) << "bad pid in trace_target_ids group: " << group;
            targets[qid].insert(id);
        }
    }
    return targets;
}

std::string make_args_for_plan(const std::string &seg_plan) {
    const std::string old_plan = FLAGS_seg_plan;
    FLAGS_seg_plan = seg_plan;
    const std::string args = parseArgs(nullptr);
    FLAGS_seg_plan = old_plan;
    return args;
}

std::string input_path() {
    return std::string("./data/") + FLAGS_dataset;
}

std::string result_path() {
    return std::string("./results/saq/");
}

std::string query_file() {
    return fmt::format("{}/{}_query{}.fvecs", input_path(), FLAGS_dataset, FLAGS_enable_PCA ? "_pca" : "");
}

std::string gt_file() {
    auto file = fmt::format("{}/{}_groundtruth.ivecs", input_path(), FLAGS_dataset);
    if (FLAGS_searcher_dist_type == 1) {
        const size_t last_dot = file.find_last_of('.');
        if (last_dot != std::string::npos) {
            file.replace(last_dot, 1, ".ip.");
        }
    }
    return file;
}

std::string quant_file_for_args(const std::string &args) {
    return fmt::format("{}/{}.index", input_path(), args);
}

std::unordered_map<PID, IdLoc> build_locations(const IVF &ivf) {
    std::unordered_map<PID, IdLoc> locs;
    locs.reserve(ivf.num_data() * 2);
    const auto &clusters = ivf.get_pclusters();
    for (size_t cid = 0; cid < clusters.size(); ++cid) {
        const auto &cluster = clusters[cid];
        for (size_t local_idx = 0; local_idx < cluster.num_vec_; ++local_idx) {
            locs.emplace(cluster.ids()[local_idx], IdLoc{cid, local_idx});
        }
    }
    return locs;
}

std::unordered_map<PID, int> build_result_rank(const std::vector<PID> &ids) {
    std::unordered_map<PID, int> ranks;
    ranks.reserve(ids.size() * 2);
    for (size_t i = 0; i < ids.size(); ++i) {
        ranks.emplace(ids[i], static_cast<int>(i));
    }
    return ranks;
}

std::unordered_map<PID, EstimateInfo> build_estimate_info(const std::vector<std::pair<PID, float>> &accurate,
                                                          const std::vector<float> &fast,
                                                          const std::vector<float> &vars) {
    CHECK_EQ(accurate.size(), fast.size());
    CHECK_EQ(accurate.size(), vars.size());

    std::unordered_map<PID, EstimateInfo> info;
    info.reserve(accurate.size() * 2);
    for (size_t i = 0; i < accurate.size(); ++i) {
        auto &entry = info[accurate[i].first];
        entry.accurate_dist = accurate[i].second;
        entry.fast_dist = fast[i];
        entry.vars_dist = vars[i];
    }

    std::vector<size_t> order(accurate.size());
    std::iota(order.begin(), order.end(), 0);

    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return accurate[a].second < accurate[b].second;
    });
    for (size_t rank = 0; rank < order.size(); ++rank) {
        info[accurate[order[rank]].first].accurate_rank = static_cast<int>(rank);
    }

    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return fast[a] < fast[b];
    });
    for (size_t rank = 0; rank < order.size(); ++rank) {
        info[accurate[order[rank]].first].fast_rank = static_cast<int>(rank);
    }

    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return vars[a] < vars[b];
    });
    for (size_t rank = 0; rank < order.size(); ++rank) {
        info[accurate[order[rank]].first].vars_rank = static_cast<int>(rank);
    }

    return info;
}

EstimateInfo find_estimate(const std::unordered_map<PID, EstimateInfo> &info, PID id) {
    const auto it = info.find(id);
    return it == info.end() ? EstimateInfo{} : it->second;
}

int find_rank(const std::unordered_map<PID, int> &ranks, PID id) {
    const auto it = ranks.find(id);
    return it == ranks.end() ? -1 : it->second;
}

std::string role_for(bool in_default, bool in_custom, bool in_top_gt) {
    if (in_default && !in_custom && in_top_gt) {
        return "lost_gt";
    }
    if (in_default && !in_custom) {
        return "default_only_fp";
    }
    if (!in_default && in_custom && in_top_gt) {
        return "gained_gt";
    }
    if (!in_default && in_custom) {
        return "replacement_fp";
    }
    return "manual_target";
}

uint32_t float_bits(float value) {
    uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

bool raw_is_nan(float value) {
    const uint32_t bits = float_bits(value);
    return (bits & 0x7f800000u) == 0x7f800000u && (bits & 0x007fffffu) != 0;
}

bool raw_is_inf(float value) {
    const uint32_t bits = float_bits(value);
    return (bits & 0x7fffffffu) == 0x7f800000u;
}

bool raw_bits_are_finite(uint32_t bits) {
    return (bits & 0x7f800000u) != 0x7f800000u;
}

bool raw_is_finite(float value) {
    return raw_bits_are_finite(float_bits(value));
}

std::string csv_float(float value) {
    if (raw_is_nan(value)) {
        return "nan";
    }
    if (raw_is_inf(value)) {
        return (float_bits(value) & 0x80000000u) ? "-inf" : "inf";
    }
    std::ostringstream oss;
    oss << std::setprecision(9) << value;
    return oss.str();
}

void write_trace_header(std::ofstream &out) {
    out << "query_id,nprobe,role,pid,gt_rank,default_rank,custom_rank,trace_final_rank,"
        << "custom_full_rank,custom_fast_rank,custom_vars_rank,"
        << "custom_full_dist,custom_fast_dist,custom_vars_dist,"
        << "stage,probed,cid,local_idx,block_idx,block_pos,probe_rank,"
        << "distk_before_block,variance_mi,variance_target,"
        << "fast_break_segment,fast_mi,fast_scalar_min,fast_target,fast_nonfinite_count,"
        << "fast_first_nonfinite_pos,fast_first_nonfinite_pid,"
        << "vector_dist,vector_distk,entered_refine,accurate_break_segment,"
        << "candidate_dist,candidate_distk,would_insert,distk_after_candidate\n";
}

void write_trace_row(std::ofstream &out, const TraceRow &row) {
    out << row.query_id << ',' << row.nprobe << ',' << row.role << ',' << row.id << ','
        << row.gt_rank << ',' << row.default_rank << ',' << row.custom_rank << ',' << row.trace_final_rank << ','
        << row.custom_est.accurate_rank << ',' << row.custom_est.fast_rank << ',' << row.custom_est.vars_rank << ','
        << csv_float(row.custom_est.accurate_dist) << ',' << csv_float(row.custom_est.fast_dist) << ','
        << csv_float(row.custom_est.vars_dist) << ',' << row.stage << ',' << row.probed << ','
        << row.cid << ',' << row.local_idx << ',' << row.block_idx << ',' << row.block_pos << ',' << row.probe_rank << ','
        << csv_float(row.distk_before_block) << ',' << csv_float(row.variance_mi) << ','
        << csv_float(row.variance_target) << ',' << row.fast_break_segment << ',' << csv_float(row.fast_mi) << ','
        << csv_float(row.fast_scalar_min) << ',' << csv_float(row.fast_target) << ',' << row.fast_nonfinite_count << ','
        << row.fast_first_nonfinite_pos << ',' << row.fast_first_nonfinite_pid << ','
        << csv_float(row.vector_dist) << ',' << csv_float(row.vector_distk) << ','
        << row.entered_refine << ',' << row.accurate_break_segment << ',' << csv_float(row.candidate_dist) << ','
        << csv_float(row.candidate_distk) << ',' << row.would_insert << ','
        << csv_float(row.distk_after_candidate) << '\n';
}

class SearchPruningTracer : public SaqCluEstimator<DistType::Any> {
    using Base = SaqCluEstimator<DistType::Any>;
    using Base::estimators_;
    static constexpr size_t FAST_ARRAY = KFastScanSize / 16;

    const bool full_refine_;
    const bool safe_block_min_;
    float *clu_dist_ = nullptr;
    __m512 *clu_dist512_ = nullptr;

  public:
    SearchPruningTracer(const SaqData &data, const SearcherConfig &searcher_cfg, const FloatVec &query)
        : Base(data, searcher_cfg, query),
          full_refine_(searcher_cfg.searcher_full_refine),
          safe_block_min_(searcher_cfg.searcher_safe_block_min) {
        const auto clus_num = data.base_datas.size();
        clu_dist_ = memory::align_mm<64, float>(clus_num * KFastScanSize);
        clu_dist512_ = memory::align_mm<64, __m512>(clus_num * FAST_ARRAY);
    }

    ~SearchPruningTracer() override {
        std::free(clu_dist512_);
        std::free(clu_dist_);
    }

    struct BlockMinStats {
        float scalar_min = std::numeric_limits<float>::max();
        int nonfinite_count = 0;
        int first_nonfinite_pos = -1;
        int64_t first_nonfinite_pid = -1;
    };

    BlockMinStats inspectBlock(const __m512 *dist,
                               size_t valid_lanes,
                               size_t blk_begin,
                               const SaqCluData *saq_clust,
                               float *scratch) const {
        _mm512_store_ps(scratch, dist[0]);
        _mm512_store_ps(scratch + 16, dist[1]);
        uint32_t PORTABLE_ALIGN64 bits[KFastScanSize];
        _mm512_store_si512(reinterpret_cast<__m512i *>(bits), _mm512_castps_si512(dist[0]));
        _mm512_store_si512(reinterpret_cast<__m512i *>(bits + 16), _mm512_castps_si512(dist[1]));

        BlockMinStats stats;
        for (size_t lane = 0; lane < valid_lanes; ++lane) {
            if (!raw_bits_are_finite(bits[lane])) {
                if (stats.first_nonfinite_pos < 0) {
                    stats.first_nonfinite_pos = static_cast<int>(lane);
                    stats.first_nonfinite_pid = static_cast<int64_t>(saq_clust->ids()[blk_begin + lane]);
                }
                stats.nonfinite_count += 1;
            } else if (scratch[lane] < stats.scalar_min) {
                stats.scalar_min = scratch[lane];
            }
        }
        return stats;
    }

    float blockMin(const __m512 *dist,
                   size_t valid_lanes,
                   size_t blk_begin,
                   const SaqCluData *saq_clust,
                   float *scratch,
                   BlockMinStats *stats_out = nullptr) const {
        if (!safe_block_min_ && stats_out == nullptr) {
            return _mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]));
        }

        BlockMinStats stats = inspectBlock(dist, valid_lanes, blk_begin, saq_clust, scratch);
        if (stats_out != nullptr) {
            *stats_out = stats;
        }
        return safe_block_min_ ? stats.scalar_min : _mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]));
    }

    void traceCluster(const SaqCluData *saq_clust,
                      PID cid,
                      size_t probe_rank,
                      utils::ResultPool &KNNs,
                      std::unordered_map<PID, TraceRow> &rows) {
        const auto clus_num = saq_clust->num_segments_;
        CHECK_EQ(clus_num, estimators_.size());
        CHECK_GT(clus_num, 1) << "trace currently targets multi-segment SAQ search";

        this->prepare(saq_clust);
        const auto num_blocks = saq_clust->num_blocks_;
        const auto num_points = saq_clust->num_vec_;

        float PORTABLE_ALIGN64 curr_dist[KFastScanSize];
        __m512 curr_dist512[FAST_ARRAY];
        for (size_t blk_idx = 0; blk_idx < num_blocks; ++blk_idx) {
            curr_dist512[0] = _mm512_setzero_ps();
            curr_dist512[1] = _mm512_setzero_ps();
            const auto blk_begin = blk_idx * KFastScanSize;
            const auto valid_lanes = std::min(KFastScanSize, num_points - blk_begin);
            float distk = KNNs.distk();
            float mi = std::numeric_limits<float>::max();

            std::vector<TraceRow *> block_targets;
            for (auto &[pid, row] : rows) {
                if (row.cid == static_cast<int64_t>(cid) && row.local_idx >= 0 &&
                    static_cast<size_t>(row.local_idx) / KFastScanSize == blk_idx) {
                    row.probed = 1;
                    row.probe_rank = static_cast<int64_t>(probe_rank);
                    row.block_idx = static_cast<int64_t>(blk_idx);
                    row.block_pos = static_cast<int64_t>(static_cast<size_t>(row.local_idx) % KFastScanSize);
                    row.distk_before_block = distk;
                    row.stage = "block_entered";
                    block_targets.push_back(&row);
                }
            }

            for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];
                estimator.varsEstDist(blk_idx, cd);
                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);
            }
            BlockMinStats variance_stats;
            mi = blockMin(curr_dist512, valid_lanes, blk_begin, saq_clust, curr_dist,
                          block_targets.empty() ? nullptr : &variance_stats);
            if (!block_targets.empty()) {
                for (auto *row : block_targets) {
                    row->variance_mi = mi;
                    row->variance_target = curr_dist[row->block_pos];
                }
            }
            if (mi > distk) {
                for (auto *row : block_targets) {
                    row->stage = "variance_block_pruned";
                }
                continue;
            }

            bool fast_pruned = false;
            int fast_break_segment = -1;
            for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                auto &cur_cluster = saq_clust->get_segment(c_i);
                auto &estimator = estimators_[c_i];
                auto cd = &clu_dist512_[c_i * FAST_ARRAY];

                if (cur_cluster.num_bits_ == 0) {
                    continue;
                }

                curr_dist512[0] = _mm512_sub_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_sub_ps(curr_dist512[1], cd[1]);
                estimator.compFastDist(blk_idx, cd);
                curr_dist512[0] = _mm512_add_ps(curr_dist512[0], cd[0]);
                curr_dist512[1] = _mm512_add_ps(curr_dist512[1], cd[1]);

                BlockMinStats fast_stats;
                mi = blockMin(curr_dist512, valid_lanes, blk_begin, saq_clust, curr_dist,
                              block_targets.empty() ? nullptr : &fast_stats);
                if (!block_targets.empty()) {
                    for (auto *row : block_targets) {
                        row->fast_break_segment = static_cast<int>(c_i);
                        row->fast_mi = mi;
                        row->fast_scalar_min = fast_stats.scalar_min;
                        row->fast_target = curr_dist[row->block_pos];
                        row->fast_nonfinite_count = fast_stats.nonfinite_count;
                        row->fast_first_nonfinite_pos = fast_stats.first_nonfinite_pos;
                        row->fast_first_nonfinite_pid = fast_stats.first_nonfinite_pid;
                    }
                }
                if (mi > distk) {
                    fast_pruned = true;
                    fast_break_segment = static_cast<int>(c_i);
                    break;
                }
            }

            if (fast_pruned) {
                for (auto *row : block_targets) {
                    row->stage = "fast_block_pruned";
                    row->fast_break_segment = fast_break_segment;
                }
                continue;
            }

            if (!raw_is_finite(mi)) {
                for (auto *row : block_targets) {
                    row->stage = "fast_nonfinite_block_skipped";
                }
                continue;
            }

            if (mi <= distk) {
                _mm512_store_ps(curr_dist, curr_dist512[0]);
                _mm512_store_ps(curr_dist + 16, curr_dist512[1]);

                for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                    _mm512_store_ps(clu_dist_ + c_i * KFastScanSize, clu_dist512_[c_i * FAST_ARRAY]);
                    _mm512_store_ps(clu_dist_ + c_i * KFastScanSize + 16, clu_dist512_[c_i * FAST_ARRAY + 1]);
                }

                for (size_t j = 0; j < KFastScanSize; ++j) {
                    const auto idx = blk_begin + j;
                    if (idx >= num_points) {
                        break;
                    }
                    const PID id = saq_clust->ids()[idx];
                    const auto row_it = rows.find(id);
                    TraceRow *row = row_it == rows.end() ? nullptr : &row_it->second;
                    if (row != nullptr) {
                        row->vector_dist = curr_dist[j];
                        row->vector_distk = distk;
                    }

                    if (curr_dist[j] < distk) {
                        float acc_dist = curr_dist[j];
                        int break_segment = -1;
                        if (row != nullptr) {
                            row->entered_refine = 1;
                        }
                        for (size_t c_i = 0; c_i < clus_num; ++c_i) {
                            auto &estimator = estimators_[c_i];
                            acc_dist += estimator.compAccurateDist(idx) - clu_dist_[c_i * KFastScanSize + j];
                            if (!full_refine_ && acc_dist >= distk) {
                                break_segment = static_cast<int>(c_i);
                                break;
                            }
                        }
                        const float distk_before_insert = distk;
                        if (row != nullptr) {
                            row->accurate_break_segment = break_segment;
                            row->candidate_dist = acc_dist;
                            row->candidate_distk = distk_before_insert;
                            row->would_insert = acc_dist < distk_before_insert ? 1 : 0;
                            if (row->would_insert) {
                                row->stage = "inserted";
                            } else if (break_segment >= 0) {
                                row->stage = "accurate_break_rejected";
                            } else {
                                row->stage = "accurate_rejected";
                            }
                        }
                        KNNs.insert(id, acc_dist);
                        distk = KNNs.distk();
                        if (row != nullptr) {
                            row->distk_after_candidate = distk;
                        }
                    } else if (row != nullptr) {
                        row->stage = "vector_filtered";
                    }
                }
            }
        }
    }
};

std::vector<TraceRow> trace_search(const IVF &ivf,
                                   const FloatVec &query,
                                   int query_id,
                                   int nprobe,
                                   size_t topk,
                                   SearcherConfig searcher_cfg,
                                   const std::vector<TargetMeta> &targets,
                                   const std::unordered_map<PID, IdLoc> &locations) {
    CHECK(!searcher_cfg.searcher_force_accurate_scan) << "pruning trace expects the normal pruning search path";
    CHECK(searcher_cfg.dist_type == DistType::L2Sqr) << "trace currently supports L2 squared distance";

    std::vector<Candidate> centroid_dist(static_cast<size_t>(nprobe));
    ivf.get_initer()->centroids_distances(query, static_cast<size_t>(nprobe), searcher_cfg.dist_type, centroid_dist);

    std::unordered_map<PID, TraceRow> rows;
    rows.reserve(targets.size() * 2 + 1);
    for (const auto &target : targets) {
        const auto loc_it = locations.find(target.id);
        CHECK(loc_it != locations.end()) << "missing target id in custom IVF index: " << target.id;
        TraceRow row;
        row.query_id = query_id;
        row.nprobe = nprobe;
        row.role = target.role;
        row.id = target.id;
        row.gt_rank = target.gt_rank;
        row.default_rank = target.default_rank;
        row.custom_rank = target.custom_rank;
        row.custom_est = target.custom_est;
        row.cid = static_cast<int64_t>(loc_it->second.cid);
        row.local_idx = static_cast<int64_t>(loc_it->second.local_idx);
        rows.emplace(target.id, std::move(row));
    }

    utils::ResultPool knns(topk, searcher_cfg.dist_type == DistType::IP);
    SearchPruningTracer tracer(*ivf.get_saq_data(), searcher_cfg, query);
    const auto &clusters = ivf.get_pclusters();
    for (size_t probe_rank = 0; probe_rank < static_cast<size_t>(nprobe); ++probe_rank) {
        const PID cid = centroid_dist[probe_rank].id;
        tracer.traceCluster(&clusters[cid], cid, probe_rank, knns, rows);
    }

    std::vector<PID> traced_results(topk);
    knns.copy_results(traced_results.data());
    const auto traced_rank = build_result_rank(traced_results);

    std::vector<TraceRow> result;
    result.reserve(rows.size());
    for (auto &[pid, row] : rows) {
        row.trace_final_rank = find_rank(traced_rank, pid);
        if (row.stage == "inserted" && row.trace_final_rank < 0) {
            row.stage = "inserted_then_evicted";
        }
        result.push_back(row);
    }
    std::sort(result.begin(), result.end(), [](const TraceRow &a, const TraceRow &b) {
        if (a.query_id != b.query_id) {
            return a.query_id < b.query_id;
        }
        if (a.nprobe != b.nprobe) {
            return a.nprobe < b.nprobe;
        }
        if (a.role != b.role) {
            return a.role < b.role;
        }
        return a.id < b.id;
    });
    return result;
}

std::vector<TargetMeta> build_targets_for_query(const std::vector<PID> &default_results,
                                                const std::vector<PID> &custom_results,
                                                const UintRowMat &gt,
                                                int query_id,
                                                size_t topk,
                                                const std::unordered_map<PID, EstimateInfo> &custom_estimate_info,
                                                const std::unordered_set<PID> *manual_targets) {
    const auto default_rank = build_result_rank(default_results);
    const auto custom_rank = build_result_rank(custom_results);
    const std::unordered_set<PID> default_set(default_results.begin(), default_results.end());
    const std::unordered_set<PID> custom_set(custom_results.begin(), custom_results.end());

    std::unordered_map<PID, int> gt_rank;
    gt_rank.reserve(static_cast<size_t>(gt.cols()) * 2);
    for (int i = 0; i < gt.cols(); ++i) {
        gt_rank.emplace(gt(query_id, i), i);
    }
    std::unordered_set<PID> top_gt;
    top_gt.reserve(topk * 2);
    for (size_t i = 0; i < topk; ++i) {
        top_gt.insert(gt(query_id, static_cast<int>(i)));
    }

    std::vector<PID> ids_to_trace;
    if (manual_targets != nullptr && !manual_targets->empty()) {
        ids_to_trace.assign(manual_targets->begin(), manual_targets->end());
        std::sort(ids_to_trace.begin(), ids_to_trace.end());
    } else {
        ids_to_trace.reserve(topk * 2);
        for (PID id : default_results) {
            if (custom_set.find(id) == custom_set.end()) {
                ids_to_trace.push_back(id);
            }
        }
        for (PID id : custom_results) {
            if (default_set.find(id) == default_set.end()) {
                ids_to_trace.push_back(id);
            }
        }
    }

    std::vector<TargetMeta> targets;
    targets.reserve(ids_to_trace.size());
    for (PID id : ids_to_trace) {
        const bool in_default = default_set.find(id) != default_set.end();
        const bool in_custom = custom_set.find(id) != custom_set.end();
        const bool in_top_gt = top_gt.find(id) != top_gt.end();
        TargetMeta target;
        target.role = manual_targets != nullptr && !manual_targets->empty()
                          ? role_for(in_default, in_custom, in_top_gt)
                          : role_for(in_default, in_custom, in_top_gt);
        target.id = id;
        target.gt_rank = find_rank(gt_rank, id);
        target.default_rank = find_rank(default_rank, id);
        target.custom_rank = find_rank(custom_rank, id);
        target.custom_est = find_estimate(custom_estimate_info, id);
        targets.push_back(std::move(target));
    }
    return targets;
}

void print_stage_summary(int query_id, int nprobe, const std::vector<TraceRow> &rows) {
    std::map<std::pair<std::string, std::string>, size_t> counts;
    for (const auto &row : rows) {
        counts[{row.role, row.stage}] += 1;
    }
    std::cout << "query=" << query_id << " nprobe=" << nprobe << " trace_targets=" << rows.size();
    for (const auto &[key, count] : counts) {
        std::cout << " " << key.first << ':' << key.second << '=' << count;
    }
    std::cout << '\n';
}

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK_GT(FLAGS_trace_topk, 0) << "trace_topk must be positive";
    CHECK(!FLAGS_seg_plan.empty()) << "provide custom plan through -seg_plan";
    CHECK(!FLAGS_searcher_force_accurate_scan) << "trace the normal pruning path, not force-accurate scan";
    const auto nprobes = parse_int_list(FLAGS_trace_nprobes);
    CHECK(!nprobes.empty()) << "trace_nprobes is empty";
    const auto query_ids = parse_int_list(FLAGS_trace_query_ids);
    CHECK(!query_ids.empty()) << "trace_query_ids is empty";
    const auto manual_targets = parse_target_ids(FLAGS_trace_target_ids);

    SearcherConfig searcher_cfg;
    if (FLAGS_searcher_dist_type == 0) {
        searcher_cfg.dist_type = DistType::L2Sqr;
    } else {
        CHECK_EQ(FLAGS_searcher_dist_type, 0) << "search_pruning_trace currently supports only L2 squared distance";
    }
    searcher_cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;
    searcher_cfg.searcher_full_refine = FLAGS_searcher_full_refine;
    searcher_cfg.searcher_force_accurate_scan = FLAGS_searcher_force_accurate_scan;
    searcher_cfg.searcher_safe_block_min = FLAGS_searcher_safe_block_min;

    const std::string custom_plan = FLAGS_seg_plan;
    const std::string default_args = make_args_for_plan("");
    const std::string custom_args = make_args_for_plan(custom_plan);
    const std::string default_index = quant_file_for_args(default_args);
    const std::string custom_index = quant_file_for_args(custom_args);

    FloatRowMat query;
    UintRowMat gt;
    utils::load_something<float, FloatRowMat>(query_file().c_str(), query);
    utils::load_something<PID, UintRowMat>(gt_file().c_str(), gt);
    CHECK_GE(gt.cols(), FLAGS_trace_topk) << "groundtruth has fewer columns than trace_topk";

    IVF default_ivf;
    IVF custom_ivf;
    std::cout << "load default index from " << default_index << '\n';
    default_ivf.load(default_index.c_str());
    std::cout << "load custom index from " << custom_index << '\n';
    custom_ivf.load(custom_index.c_str());
    const auto custom_locations = build_locations(custom_ivf);

    std::string output = FLAGS_trace_output;
    if (output.empty()) {
        output = fmt::format("{}pruning_trace_{}_{}_vs_{}.csv", result_path(), FLAGS_dataset, default_args, custom_args);
    }
    std::ofstream out(output, std::ios::out);
    CHECK(out.is_open()) << "failed to open trace output: " << output;
    write_trace_header(out);

    const size_t topk = static_cast<size_t>(FLAGS_trace_topk);
    std::vector<PID> default_results(topk);
    std::vector<PID> custom_results(topk);

    for (int nprobe : nprobes) {
        CHECK_GT(nprobe, 0) << "nprobe must be positive";
        for (int query_id : query_ids) {
            CHECK_GE(query_id, 0);
            CHECK_LT(query_id, static_cast<int>(query.rows()));
            const FloatVec q = query.row(query_id);
            default_ivf.search(q, topk, static_cast<size_t>(nprobe), searcher_cfg, default_results.data());
            custom_ivf.search(q, topk, static_cast<size_t>(nprobe), searcher_cfg, custom_results.data());

            std::vector<std::pair<PID, float>> custom_estimates;
            std::vector<float> custom_fast_distances;
            std::vector<float> custom_vars_distances;
            custom_ivf.estimate(q, static_cast<size_t>(nprobe), searcher_cfg, custom_estimates,
                                &custom_fast_distances, &custom_vars_distances);
            const auto custom_estimate_info = build_estimate_info(custom_estimates, custom_fast_distances,
                                                                  custom_vars_distances);

            const auto manual_it = manual_targets.find(query_id);
            const std::unordered_set<PID> *manual = manual_it == manual_targets.end() ? nullptr : &manual_it->second;
            auto targets = build_targets_for_query(default_results, custom_results, gt, query_id, topk,
                                                   custom_estimate_info, manual);
            auto trace_rows = trace_search(custom_ivf, q, query_id, nprobe, topk, searcher_cfg,
                                           targets, custom_locations);
            for (const auto &row : trace_rows) {
                write_trace_row(out, row);
            }
            print_stage_summary(query_id, nprobe, trace_rows);
        }
    }

    std::cout << "trace output: " << output << '\n';
    return 0;
}

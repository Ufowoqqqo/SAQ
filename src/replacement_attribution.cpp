#include <algorithm>
#include <cmath>
#include <fstream>
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

#include "define_options.h"

#include "defines.hpp"
#include "index/ivf.hpp"
#include "utils/IO.hpp"
#include "utils/code_helper.hpp"

using namespace saqlib;

DEFINE_int32(repl_topk, 100, "top-k used for replacement-level recall comparison");
DEFINE_string(repl_nprobes, "20,50,100,200,400", "comma-separated nprobe values");
DEFINE_string(repl_query_ids, "580,500", "comma-separated query ids to diagnose");
DEFINE_string(repl_item_output, "", "output CSV path for lost/replacement item-level diagnostics");
DEFINE_string(repl_segment_output, "", "output CSV path for per-item segment attribution");
DEFINE_string(repl_pair_output, "", "output CSV path for lost-vs-replacement pair diagnostics");

namespace {
struct IdLoc {
    size_t cid = 0;
    size_t local_idx = 0;
};

struct SegmentEval {
    size_t begin = 0;
    size_t dim_len = 0;
    size_t bits = 0;
    float true_dist = 0;
    float approx_dist = 0;
    float error = 0;
};

struct PlanEval {
    std::vector<SegmentEval> segments;
    float total_true = 0;
    float total_approx = 0;
    float total_error = 0;
    float total_abs_error = 0;
};

struct EstimateInfo {
    int accurate_rank = -1;
    int fast_rank = -1;
    int vars_rank = -1;
    float accurate_dist = std::numeric_limits<float>::quiet_NaN();
    float fast_dist = std::numeric_limits<float>::quiet_NaN();
    float vars_dist = std::numeric_limits<float>::quiet_NaN();
};

struct ItemEval {
    std::string role;
    PID id = 0;
    int gt_rank = -1;
    int default_rank = -1;
    int custom_rank = -1;
    EstimateInfo default_est;
    EstimateInfo custom_est;
    PlanEval default_eval;
    PlanEval custom_eval;
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

std::string data_file() {
    return fmt::format("{}/{}_base{}.fvecs", input_path(), FLAGS_dataset, FLAGS_enable_PCA ? "_pca" : "");
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
            const PID id = cluster.ids()[local_idx];
            locs.emplace(id, IdLoc{cid, local_idx});
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

uint8_t decode_fastscan_short_byte(const CAQClusterData &cluster, size_t local_idx, size_t byte_col) {
    static constexpr int inv_perm[16] = {0, 2, 4, 6, 8, 10, 12, 14, 1, 3, 5, 7, 9, 11, 13, 15};
    const size_t row = local_idx % KFastScanSize;
    const bool high_half = row >= 16;
    const size_t packed_pos = static_cast<size_t>(inv_perm[row % 16]);
    const uint8_t *packed_col = cluster.short_code(local_idx / KFastScanSize) + byte_col * KFastScanSize;
    const uint8_t high_nibble_byte = packed_col[packed_pos];
    const uint8_t low_nibble_byte = packed_col[packed_pos + 16];
    const uint8_t high_nibble = high_half ? (high_nibble_byte >> 4) : (high_nibble_byte & 0x0f);
    const uint8_t low_nibble = high_half ? (low_nibble_byte >> 4) : (low_nibble_byte & 0x0f);
    return static_cast<uint8_t>((high_nibble << 4) | low_nibble);
}

float short_msb_ip(const FloatVec &query_residual, const CAQClusterData &cluster, size_t local_idx, bool use_fastscan) {
    float ip = 0;
    const size_t num_byte_cols = cluster.num_dim_padded_ / 8;
    const uint8_t *plain_short_code = use_fastscan ? nullptr : cluster.short_code_single(local_idx);
    for (size_t byte_col = 0; byte_col < num_byte_cols; ++byte_col) {
        const uint8_t code_byte = use_fastscan ? decode_fastscan_short_byte(cluster, local_idx, byte_col)
                                               : plain_short_code[byte_col];
        for (size_t bit = 0; bit < 8; ++bit) {
            if (code_byte & (0x80u >> bit)) {
                ip += query_residual[byte_col * 8 + bit];
            }
        }
    }
    return ip;
}

FloatVec padded_query_segment(const FloatVec &query, size_t offset, size_t dim_len) {
    FloatVec segment = FloatVec::Zero(dim_len);
    const size_t copy_size = std::min(dim_len, static_cast<size_t>(query.cols()) - offset);
    if (copy_size > 0) {
        segment.head(copy_size) = query.segment(offset, copy_size);
    }
    return segment;
}

float true_segment_distance(const FloatRowMat &data, const FloatVec &query, PID id, size_t offset, size_t dim_len) {
    const size_t copy_size = std::min(dim_len, static_cast<size_t>(data.cols()) - offset);
    if (copy_size == 0) {
        return 0;
    }
    return (query.segment(offset, copy_size) - data.row(id).segment(offset, copy_size)).squaredNorm();
}

float explicit_segment_approx(const SaqData &saq_data,
                              const CAQClusterData &cluster_segment,
                              const FloatVec &query,
                              size_t local_idx,
                              size_t seg_idx,
                              size_t offset) {
    const auto &base_data = saq_data.base_datas[seg_idx];
    const size_t dim_len = base_data.num_dim_pad;
    const size_t bits = base_data.num_bits;
    FloatVec query_segment = padded_query_segment(query, offset, dim_len);
    if (base_data.rotator) {
        query_segment = query_segment * base_data.rotator->get_P();
    }
    const FloatVec query_residual = query_segment - cluster_segment.centroid();
    const float q_l2sqr = query_residual.squaredNorm();
    const size_t block_idx = local_idx / KFastScanSize;
    const size_t block_pos = local_idx % KFastScanSize;
    const float o_l2norm = cluster_segment.factor_o_l2norm(block_idx)[block_pos];
    const float o_l2sqr = o_l2norm * o_l2norm;
    if (bits == 0) {
        return o_l2sqr + q_l2sqr;
    }

    const float short_ip = short_msb_ip(query_residual, cluster_segment, local_idx, base_data.cfg.use_fastscan);
    const int ex_bits = static_cast<int>(bits) - 1;
    auto ip_func = utils::get_IP_FUNC(ex_bits);
    const float ex_ip = ip_func(query_residual.data(), cluster_segment.long_code(local_idx), dim_len);
    const float delta = 2.0f / static_cast<float>(1u << bits);
    const float normalized_ip = short_ip + ex_ip * delta + (-1.0f + delta / 2.0f) * query_residual.sum();
    const auto &factor = cluster_segment.long_factor(local_idx);
    const float ip_o_q = factor.rescale * normalized_ip;
    return o_l2sqr + q_l2sqr - 2.0f * ip_o_q;
}

PlanEval evaluate_plan(const IVF &ivf,
                       const std::unordered_map<PID, IdLoc> &locations,
                       const FloatRowMat &data,
                       const FloatVec &query,
                       PID id) {
    const auto it = locations.find(id);
    CHECK(it != locations.end()) << "missing id in IVF index: " << id;

    const SaqData *saq_data = ivf.get_saq_data();
    CHECK(saq_data != nullptr) << "SAQ data missing";
    const auto &clusters = ivf.get_pclusters();
    CHECK_LT(it->second.cid, clusters.size());
    const auto &cluster = clusters[it->second.cid];

    PlanEval eval;
    eval.segments.reserve(saq_data->quant_plan.size());
    size_t offset = 0;
    for (size_t seg_idx = 0; seg_idx < saq_data->quant_plan.size(); ++seg_idx) {
        const auto [dim_len, bits] = saq_data->quant_plan[seg_idx];
        const float true_dist = true_segment_distance(data, query, id, offset, dim_len);
        const float approx_dist = explicit_segment_approx(*saq_data, cluster.get_segment(seg_idx), query,
                                                          it->second.local_idx, seg_idx, offset);
        const float error = approx_dist - true_dist;
        eval.segments.push_back(SegmentEval{offset, dim_len, bits, true_dist, approx_dist, error});
        eval.total_true += true_dist;
        eval.total_approx += approx_dist;
        eval.total_abs_error += std::abs(error);
        offset += dim_len;
    }
    eval.total_error = eval.total_approx - eval.total_true;
    return eval;
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
    return "shared";
}

void write_item_row(std::ofstream &items,
                    int query_id,
                    int nprobe,
                    const ItemEval &item,
                    float gt_k_dist,
                    float gt_kplus1_dist) {
    items << query_id << ',' << nprobe << ',' << item.role << ',' << item.id << ','
          << item.gt_rank << ',' << item.default_rank << ',' << item.custom_rank << ','
          << item.default_est.accurate_rank << ',' << item.custom_est.accurate_rank << ','
          << item.custom_est.fast_rank << ',' << item.custom_est.vars_rank << ','
          << item.custom_eval.total_true << ',' << gt_k_dist << ',' << gt_kplus1_dist << ','
          << (item.custom_eval.total_true - gt_k_dist) << ','
          << item.default_eval.total_approx << ',' << item.custom_eval.total_approx << ','
          << item.custom_est.accurate_dist << ',' << item.custom_est.fast_dist << ',' << item.custom_est.vars_dist << ','
          << item.default_eval.total_error << ',' << item.custom_eval.total_error << ','
          << (item.custom_eval.total_error - item.default_eval.total_error) << '\n';
}

void write_segment_rows(std::ofstream &segments,
                        int query_id,
                        int nprobe,
                        const ItemEval &item,
                        const std::string &plan_name,
                        const PlanEval &eval) {
    for (size_t seg_idx = 0; seg_idx < eval.segments.size(); ++seg_idx) {
        const auto &seg = eval.segments[seg_idx];
        const double share = eval.total_abs_error > 0 ? std::abs(seg.error) / eval.total_abs_error : 0;
        segments << query_id << ',' << nprobe << ',' << item.role << ',' << item.id << ','
                 << item.gt_rank << ',' << item.default_rank << ',' << item.custom_rank << ','
                 << plan_name << ',' << seg_idx << ',' << seg.begin << ',' << seg.dim_len << ',' << seg.bits << ','
                 << seg.true_dist << ',' << seg.approx_dist << ',' << seg.error << ',' << std::abs(seg.error) << ','
                 << share << ',' << eval.total_true << ',' << eval.total_approx << ',' << eval.total_error << '\n';
    }
}

void write_pair_row(std::ofstream &pairs,
                    int query_id,
                    int nprobe,
                    const ItemEval &lost,
                    const ItemEval &repl) {
    const float exact_margin = repl.custom_eval.total_true - lost.custom_eval.total_true;
    const float default_approx_margin = repl.default_eval.total_approx - lost.default_eval.total_approx;
    const float custom_approx_margin = repl.custom_eval.total_approx - lost.custom_eval.total_approx;
    const float default_error_margin = repl.default_eval.total_error - lost.default_eval.total_error;
    const float custom_error_margin = repl.custom_eval.total_error - lost.custom_eval.total_error;
    pairs << query_id << ',' << nprobe << ','
          << lost.id << ',' << lost.gt_rank << ',' << lost.default_rank << ',' << lost.custom_rank << ','
          << lost.custom_est.accurate_rank << ',' << lost.custom_est.fast_rank << ',' << lost.custom_est.vars_rank << ','
          << repl.id << ',' << repl.role << ',' << repl.gt_rank << ',' << repl.default_rank << ',' << repl.custom_rank << ','
          << repl.custom_est.accurate_rank << ',' << repl.custom_est.fast_rank << ',' << repl.custom_est.vars_rank << ','
          << lost.custom_eval.total_true << ',' << repl.custom_eval.total_true << ',' << exact_margin << ','
          << lost.default_eval.total_approx << ',' << repl.default_eval.total_approx << ',' << default_approx_margin << ','
          << lost.custom_eval.total_approx << ',' << repl.custom_eval.total_approx << ',' << custom_approx_margin << ','
          << lost.default_eval.total_error << ',' << repl.default_eval.total_error << ',' << default_error_margin << ','
          << lost.custom_eval.total_error << ',' << repl.custom_eval.total_error << ',' << custom_error_margin << ','
          << (exact_margin > 0 && custom_approx_margin < 0 ? 1 : 0) << ','
          << (exact_margin > 0 && default_approx_margin < 0 ? 1 : 0) << '\n';
}

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK_GT(FLAGS_repl_topk, 0) << "repl_topk must be positive";
    CHECK(!FLAGS_seg_plan.empty()) << "provide custom plan through -seg_plan";
    const auto nprobes = parse_int_list(FLAGS_repl_nprobes);
    CHECK(!nprobes.empty()) << "repl_nprobes is empty";
    const auto query_ids = parse_int_list(FLAGS_repl_query_ids);
    CHECK(!query_ids.empty()) << "repl_query_ids is empty";

    SearcherConfig searcher_cfg;
    if (FLAGS_searcher_dist_type == 0) {
        searcher_cfg.dist_type = DistType::L2Sqr;
    } else {
        CHECK_EQ(FLAGS_searcher_dist_type, 0) << "replacement attribution currently supports only L2 squared distance";
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

    FloatRowMat data;
    FloatRowMat query;
    UintRowMat gt;
    utils::load_something<float, FloatRowMat>(data_file().c_str(), data);
    utils::load_something<float, FloatRowMat>(query_file().c_str(), query);
    utils::load_something<PID, UintRowMat>(gt_file().c_str(), gt);
    CHECK_GE(gt.cols(), FLAGS_repl_topk) << "groundtruth has fewer columns than repl_topk";

    IVF default_ivf;
    IVF custom_ivf;
    std::cout << "load default index from " << default_index << '\n';
    default_ivf.load(default_index.c_str());
    std::cout << "load custom index from " << custom_index << '\n';
    custom_ivf.load(custom_index.c_str());

    const auto default_locations = build_locations(default_ivf);
    const auto custom_locations = build_locations(custom_ivf);

    std::string item_output = FLAGS_repl_item_output;
    if (item_output.empty()) {
        item_output = fmt::format("{}replacement_attribution_{}_{}_vs_{}.items.csv",
                                  result_path(), FLAGS_dataset, default_args, custom_args);
    }
    std::string segment_output = FLAGS_repl_segment_output;
    if (segment_output.empty()) {
        segment_output = fmt::format("{}replacement_attribution_{}_{}_vs_{}.segments.csv",
                                     result_path(), FLAGS_dataset, default_args, custom_args);
    }
    std::string pair_output = FLAGS_repl_pair_output;
    if (pair_output.empty()) {
        pair_output = fmt::format("{}replacement_attribution_{}_{}_vs_{}.pairs.csv",
                                  result_path(), FLAGS_dataset, default_args, custom_args);
    }

    std::ofstream items(item_output, std::ios::out);
    CHECK(items.is_open()) << "failed to open item output: " << item_output;
    items << "query_id,nprobe,role,pid,gt_rank,default_rank,custom_rank,"
          << "default_full_rank,custom_full_rank,custom_fast_rank,custom_vars_rank,"
          << "exact_dist,gt_k_dist,gt_kplus1_dist,exact_minus_gt_k_dist,"
          << "default_total_approx,custom_total_approx,custom_full_dist,custom_fast_dist,custom_vars_dist,"
          << "default_total_error,custom_total_error,delta_custom_minus_default_error\n";

    std::ofstream segments(segment_output, std::ios::out);
    CHECK(segments.is_open()) << "failed to open segment output: " << segment_output;
    segments << "query_id,nprobe,role,pid,gt_rank,default_rank,custom_rank,plan,segment_id,dim_begin,dim_len,bits,"
             << "true_dist,approx_dist,error,abs_error,abs_error_share,total_true,total_approx,total_error\n";

    std::ofstream pairs(pair_output, std::ios::out);
    CHECK(pairs.is_open()) << "failed to open pair output: " << pair_output;
    pairs << "query_id,nprobe,lost_pid,lost_gt_rank,lost_default_rank,lost_custom_rank,"
          << "lost_custom_full_rank,lost_custom_fast_rank,lost_custom_vars_rank,"
          << "replacement_pid,replacement_role,replacement_gt_rank,replacement_default_rank,replacement_custom_rank,"
          << "replacement_custom_full_rank,replacement_custom_fast_rank,replacement_custom_vars_rank,"
          << "lost_exact_dist,replacement_exact_dist,exact_margin_replacement_minus_lost,"
          << "lost_default_approx,replacement_default_approx,default_approx_margin_replacement_minus_lost,"
          << "lost_custom_approx,replacement_custom_approx,custom_approx_margin_replacement_minus_lost,"
          << "lost_default_error,replacement_default_error,default_error_margin_replacement_minus_lost,"
          << "lost_custom_error,replacement_custom_error,custom_error_margin_replacement_minus_lost,"
          << "custom_inverts_exact,default_inverts_exact\n";

    const size_t topk = static_cast<size_t>(FLAGS_repl_topk);
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

            const auto default_rank = build_result_rank(default_results);
            const auto custom_rank = build_result_rank(custom_results);
            const std::unordered_set<PID> default_set(default_results.begin(), default_results.end());
            const std::unordered_set<PID> custom_set(custom_results.begin(), custom_results.end());

            std::vector<std::pair<PID, float>> default_estimates;
            std::vector<std::pair<PID, float>> custom_estimates;
            std::vector<float> default_fast_distances;
            std::vector<float> default_vars_distances;
            std::vector<float> custom_fast_distances;
            std::vector<float> custom_vars_distances;
            default_ivf.estimate(q, static_cast<size_t>(nprobe), searcher_cfg, default_estimates,
                                 &default_fast_distances, &default_vars_distances);
            custom_ivf.estimate(q, static_cast<size_t>(nprobe), searcher_cfg, custom_estimates,
                                &custom_fast_distances, &custom_vars_distances);
            const auto default_estimate_info = build_estimate_info(default_estimates, default_fast_distances,
                                                                   default_vars_distances);
            const auto custom_estimate_info = build_estimate_info(custom_estimates, custom_fast_distances,
                                                                  custom_vars_distances);

            std::unordered_map<PID, int> gt_rank;
            gt_rank.reserve(static_cast<size_t>(gt.cols()) * 2);
            for (int i = 0; i < gt.cols(); ++i) {
                gt_rank.emplace(gt(query_id, i), i);
            }
            std::unordered_set<PID> top_gt;
            top_gt.reserve(topk * 2);
            for (size_t i = 0; i < topk; ++i) {
                top_gt.insert(gt(query_id, i));
            }

            std::vector<PID> ids_to_eval;
            ids_to_eval.reserve(topk * 2);
            for (PID id : default_results) {
                if (custom_set.find(id) == custom_set.end()) {
                    ids_to_eval.push_back(id);
                }
            }
            for (PID id : custom_results) {
                if (default_set.find(id) == default_set.end()) {
                    ids_to_eval.push_back(id);
                }
            }

            std::vector<ItemEval> item_evals;
            item_evals.reserve(ids_to_eval.size());
            for (PID id : ids_to_eval) {
                const bool in_default = default_set.find(id) != default_set.end();
                const bool in_custom = custom_set.find(id) != custom_set.end();
                const bool in_top_gt = top_gt.find(id) != top_gt.end();
                const int rank = find_rank(gt_rank, id);
                ItemEval item;
                item.role = role_for(in_default, in_custom, in_top_gt);
                item.id = id;
                item.gt_rank = rank;
                item.default_rank = find_rank(default_rank, id);
                item.custom_rank = find_rank(custom_rank, id);
                item.default_est = find_estimate(default_estimate_info, id);
                item.custom_est = find_estimate(custom_estimate_info, id);
                item.default_eval = evaluate_plan(default_ivf, default_locations, data, q, id);
                item.custom_eval = evaluate_plan(custom_ivf, custom_locations, data, q, id);
                item_evals.push_back(std::move(item));
            }

            const float gt_k_dist = (q - data.row(gt(query_id, topk - 1))).squaredNorm();
            const float gt_kplus1_dist = gt.cols() > static_cast<int>(topk)
                                             ? (q - data.row(gt(query_id, topk))).squaredNorm()
                                             : std::numeric_limits<float>::quiet_NaN();

            std::vector<const ItemEval *> lost_items;
            std::vector<const ItemEval *> replacement_items;
            size_t replacement_fp_count = 0;
            size_t gained_gt_count = 0;
            for (const auto &item : item_evals) {
                write_item_row(items, query_id, nprobe, item, gt_k_dist, gt_kplus1_dist);
                write_segment_rows(segments, query_id, nprobe, item, "default", item.default_eval);
                write_segment_rows(segments, query_id, nprobe, item, "custom", item.custom_eval);
                if (item.role == "lost_gt") {
                    lost_items.push_back(&item);
                }
                if (item.role == "replacement_fp" || item.role == "gained_gt") {
                    replacement_items.push_back(&item);
                    replacement_fp_count += item.role == "replacement_fp";
                    gained_gt_count += item.role == "gained_gt";
                }
            }
            std::sort(lost_items.begin(), lost_items.end(), [](const ItemEval *a, const ItemEval *b) {
                return a->gt_rank < b->gt_rank;
            });
            std::sort(replacement_items.begin(), replacement_items.end(), [](const ItemEval *a, const ItemEval *b) {
                return a->custom_rank < b->custom_rank;
            });

            size_t custom_inversions = 0;
            size_t pair_count = 0;
            for (const ItemEval *lost : lost_items) {
                for (const ItemEval *repl : replacement_items) {
                    const float exact_margin = repl->custom_eval.total_true - lost->custom_eval.total_true;
                    const float custom_margin = repl->custom_eval.total_approx - lost->custom_eval.total_approx;
                    custom_inversions += exact_margin > 0 && custom_margin < 0;
                    pair_count += 1;
                    write_pair_row(pairs, query_id, nprobe, *lost, *repl);
                }
            }

            std::cout << "query=" << query_id
                      << " nprobe=" << nprobe
                      << " default_only=" << std::count_if(item_evals.begin(), item_evals.end(), [](const auto &item) {
                             return item.default_rank >= 0 && item.custom_rank < 0;
                         })
                      << " custom_only=" << std::count_if(item_evals.begin(), item_evals.end(), [](const auto &item) {
                             return item.default_rank < 0 && item.custom_rank >= 0;
                         })
                      << " lost_gt=" << lost_items.size()
                      << " gained_gt=" << gained_gt_count
                      << " replacement_fp=" << replacement_fp_count
                      << " custom_inverting_pairs=" << custom_inversions << '/' << pair_count
                      << " lost_full_topk=" << std::count_if(lost_items.begin(), lost_items.end(), [](const auto *item) {
                             return item->custom_est.accurate_rank >= 0 && item->custom_est.accurate_rank < 100;
                         }) << '/' << lost_items.size()
                      << '\n';
        }
    }

    items.close();
    segments.close();
    pairs.close();

    std::cout << "item diagnostics written to " << item_output << '\n';
    std::cout << "segment diagnostics written to " << segment_output << '\n';
    std::cout << "pair diagnostics written to " << pair_output << '\n';
    return 0;
}

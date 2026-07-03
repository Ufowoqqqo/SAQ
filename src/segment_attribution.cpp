#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <sstream>
#include <string>
#include <tuple>
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

DEFINE_int32(attrib_topk, 100, "top-k used for default/custom recall comparison");
DEFINE_string(attrib_nprobes, "20,50,100,200,400", "comma-separated nprobe values");
DEFINE_string(attrib_query_ids, "", "optional comma-separated query ids; empty means all queries");
DEFINE_string(attrib_event_output, "", "output CSV path for event-level segment attribution");
DEFINE_string(attrib_summary_output, "", "output CSV path for aggregate segment attribution");

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

struct SummaryAgg {
    size_t count = 0;
    size_t dim_begin = 0;
    size_t dim_len = 0;
    size_t bits = 0;
    double sum_true = 0;
    double sum_approx = 0;
    double sum_error = 0;
    double sum_abs_error = 0;
    double sum_abs_error_share = 0;
    size_t positive_error_count = 0;
    size_t negative_error_count = 0;
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

void add_summary(std::map<std::tuple<int, std::string, std::string, size_t>, SummaryAgg> &summary,
                 int nprobe,
                 const std::string &event_type,
                 const std::string &plan_name,
                 size_t seg_idx,
                 const SegmentEval &seg,
                 float total_abs_error) {
    auto key = std::make_tuple(nprobe, event_type, plan_name, seg_idx);
    auto &agg = summary[key];
    agg.count += 1;
    agg.dim_begin = seg.begin;
    agg.dim_len = seg.dim_len;
    agg.bits = seg.bits;
    agg.sum_true += seg.true_dist;
    agg.sum_approx += seg.approx_dist;
    agg.sum_error += seg.error;
    agg.sum_abs_error += std::abs(seg.error);
    if (total_abs_error > 0) {
        agg.sum_abs_error_share += std::abs(seg.error) / total_abs_error;
    }
    agg.positive_error_count += seg.error > 0;
    agg.negative_error_count += seg.error < 0;
}

void write_event_rows(std::ofstream &events,
                      std::map<std::tuple<int, std::string, std::string, size_t>, SummaryAgg> &summary,
                      int query_id,
                      int nprobe,
                      const std::string &event_type,
                      PID id,
                      int gt_rank,
                      const PlanEval &default_eval,
                      const PlanEval &custom_eval,
                      const std::string &plan_name,
                      const PlanEval &plan_eval) {
    for (size_t seg_idx = 0; seg_idx < plan_eval.segments.size(); ++seg_idx) {
        const auto &seg = plan_eval.segments[seg_idx];
        const double share = plan_eval.total_abs_error > 0 ? std::abs(seg.error) / plan_eval.total_abs_error : 0;
        events << query_id << ',' << nprobe << ',' << event_type << ',' << id << ',' << gt_rank << ','
               << default_eval.total_true << ',' << default_eval.total_approx << ',' << default_eval.total_error << ','
               << custom_eval.total_true << ',' << custom_eval.total_approx << ',' << custom_eval.total_error << ','
               << (custom_eval.total_error - default_eval.total_error) << ','
               << plan_name << ',' << seg_idx << ',' << seg.begin << ',' << seg.dim_len << ',' << seg.bits << ','
               << seg.true_dist << ',' << seg.approx_dist << ',' << seg.error << ',' << std::abs(seg.error) << ','
               << share << '\n';
        add_summary(summary, nprobe, event_type, plan_name, seg_idx, seg, plan_eval.total_abs_error);
    }
}

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK_GT(FLAGS_attrib_topk, 0) << "attrib_topk must be positive";
    CHECK(!FLAGS_seg_plan.empty()) << "provide custom plan through -seg_plan";
    const auto nprobes = parse_int_list(FLAGS_attrib_nprobes);
    CHECK(!nprobes.empty()) << "attrib_nprobes is empty";

    SearcherConfig searcher_cfg;
    if (FLAGS_searcher_dist_type == 0) {
        searcher_cfg.dist_type = DistType::L2Sqr;
    } else {
        CHECK_EQ(FLAGS_searcher_dist_type, 0) << "segment attribution currently supports only L2 squared distance";
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
    CHECK_GE(gt.cols(), FLAGS_attrib_topk) << "groundtruth has fewer columns than attrib_topk";

    IVF default_ivf;
    IVF custom_ivf;
    std::cout << "load default index from " << default_index << '\n';
    default_ivf.load(default_index.c_str());
    std::cout << "load custom index from " << custom_index << '\n';
    custom_ivf.load(custom_index.c_str());

    const auto default_locations = build_locations(default_ivf);
    const auto custom_locations = build_locations(custom_ivf);

    std::vector<int> query_ids = parse_int_list(FLAGS_attrib_query_ids);
    if (query_ids.empty()) {
        query_ids.resize(query.rows());
        std::iota(query_ids.begin(), query_ids.end(), 0);
    }

    std::string event_output = FLAGS_attrib_event_output;
    if (event_output.empty()) {
        event_output = fmt::format("{}segment_attribution_{}_{}_vs_{}.events.csv",
                                   result_path(), FLAGS_dataset, default_args, custom_args);
    }
    std::string summary_output = FLAGS_attrib_summary_output;
    if (summary_output.empty()) {
        summary_output = fmt::format("{}segment_attribution_{}_{}_vs_{}.summary.csv",
                                     result_path(), FLAGS_dataset, default_args, custom_args);
    }

    std::ofstream events(event_output, std::ios::out);
    CHECK(events.is_open()) << "failed to open event output: " << event_output;
    events << "query_id,nprobe,event_type,pid,gt_rank,"
           << "default_total_true,default_total_approx,default_total_error,"
           << "custom_total_true,custom_total_approx,custom_total_error,delta_custom_minus_default_error,"
           << "plan,segment_id,dim_begin,dim_len,bits,true_dist,approx_dist,error,abs_error,abs_error_share\n";

    std::map<std::tuple<int, std::string, std::string, size_t>, SummaryAgg> summary;
    std::map<int, size_t> lost_events_by_nprobe;
    std::map<int, size_t> gained_events_by_nprobe;

    const size_t topk = static_cast<size_t>(FLAGS_attrib_topk);
    std::vector<PID> default_results(topk);
    std::vector<PID> custom_results(topk);

    for (int nprobe : nprobes) {
        CHECK_GT(nprobe, 0) << "nprobe must be positive";
        size_t lost_events = 0;
        size_t gained_events = 0;
        for (int query_id : query_ids) {
            CHECK_GE(query_id, 0);
            CHECK_LT(query_id, query.rows());
            const FloatVec q = query.row(query_id);
            default_ivf.search(q, topk, static_cast<size_t>(nprobe), searcher_cfg, default_results.data());
            custom_ivf.search(q, topk, static_cast<size_t>(nprobe), searcher_cfg, custom_results.data());

            std::unordered_map<PID, int> gt_rank;
            gt_rank.reserve(topk * 2);
            std::unordered_set<PID> gt_set;
            gt_set.reserve(topk * 2);
            for (size_t i = 0; i < topk; ++i) {
                const PID id = gt(query_id, i);
                gt_set.insert(id);
                gt_rank.emplace(id, static_cast<int>(i));
            }

            const std::unordered_set<PID> default_set(default_results.begin(), default_results.end());
            const std::unordered_set<PID> custom_set(custom_results.begin(), custom_results.end());
            std::vector<std::pair<std::string, PID>> events_to_eval;
            for (PID id : gt_set) {
                const bool in_default = default_set.find(id) != default_set.end();
                const bool in_custom = custom_set.find(id) != custom_set.end();
                if (in_default && !in_custom) {
                    events_to_eval.emplace_back("lost", id);
                    lost_events += 1;
                } else if (!in_default && in_custom) {
                    events_to_eval.emplace_back("gained", id);
                    gained_events += 1;
                }
            }
            std::sort(events_to_eval.begin(), events_to_eval.end(), [&](const auto &a, const auto &b) {
                if (a.first != b.first) {
                    return a.first < b.first;
                }
                return gt_rank[a.second] < gt_rank[b.second];
            });

            for (const auto &[event_type, id] : events_to_eval) {
                const int rank = gt_rank[id];
                const auto default_eval = evaluate_plan(default_ivf, default_locations, data, q, id);
                const auto custom_eval = evaluate_plan(custom_ivf, custom_locations, data, q, id);
                write_event_rows(events, summary, query_id, nprobe, event_type, id, rank,
                                 default_eval, custom_eval, "default", default_eval);
                write_event_rows(events, summary, query_id, nprobe, event_type, id, rank,
                                 default_eval, custom_eval, "custom", custom_eval);
            }
        }
        lost_events_by_nprobe[nprobe] = lost_events;
        gained_events_by_nprobe[nprobe] = gained_events;
        std::cout << "nprobe=" << nprobe
                  << " lost_events=" << lost_events
                  << " gained_events=" << gained_events << '\n';
    }
    events.close();

    std::ofstream summary_csv(summary_output, std::ios::out);
    CHECK(summary_csv.is_open()) << "failed to open summary output: " << summary_output;
    summary_csv << "nprobe,event_type,plan,segment_id,dim_begin,dim_len,bits,event_count,"
                << "mean_true,mean_approx,mean_error,mean_abs_error,positive_error_frac,negative_error_frac,mean_abs_error_share\n";
    for (const auto &[key, agg] : summary) {
        const auto &[nprobe, event_type, plan_name, seg_idx] = key;
        const double denom = static_cast<double>(agg.count);
        summary_csv << nprobe << ',' << event_type << ',' << plan_name << ',' << seg_idx << ','
                    << agg.dim_begin << ',' << agg.dim_len << ',' << agg.bits << ',' << agg.count << ','
                    << agg.sum_true / denom << ',' << agg.sum_approx / denom << ','
                    << agg.sum_error / denom << ',' << agg.sum_abs_error / denom << ','
                    << agg.positive_error_count / denom << ',' << agg.negative_error_count / denom << ','
                    << agg.sum_abs_error_share / denom << '\n';
    }
    summary_csv.close();

    std::cout << "event attribution written to " << event_output << '\n';
    std::cout << "summary attribution written to " << summary_output << '\n';
    return 0;
}

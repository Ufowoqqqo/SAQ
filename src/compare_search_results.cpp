#include <algorithm>
#include <fstream>
#include <iostream>
#include <limits>
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
#include "utils/space.hpp"

using namespace saqlib;

DEFINE_int32(compare_topk, 100, "top-k used for per-query recall comparison");
DEFINE_int32(compare_nprobe, 50, "nprobe used for per-query recall comparison");
DEFINE_string(compare_output, "", "output CSV path for per-query comparison");

namespace {
std::string join_ids(const std::vector<PID> &ids, size_t limit = 16) {
    std::ostringstream os;
    const size_t n = std::min(limit, ids.size());
    for (size_t i = 0; i < n; ++i) {
        if (i) {
            os << ';';
        }
        os << ids[i];
    }
    if (ids.size() > limit) {
        os << ";...";
    }
    return os.str();
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

float exact_distance(const FloatRowMat &data, const FloatVec &query, PID id, DistType dist_type) {
    if (dist_type == DistType::IP) {
        return query.dot(data.row(id));
    }
    return (query - data.row(id)).squaredNorm();
}

struct NeighborStats {
    int count = 0;
    int min_rank = -1;
    double mean_rank = 0.0;
    double mean_dist = 0.0;
    std::vector<PID> ids;
};

NeighborStats summarize_neighbors(const std::vector<PID> &ids,
                                  const std::unordered_map<PID, int> &gt_rank,
                                  const FloatRowMat &data,
                                  const FloatVec &query,
                                  DistType dist_type) {
    NeighborStats stats;
    stats.count = static_cast<int>(ids.size());
    stats.ids = ids;
    if (ids.empty()) {
        return stats;
    }
    int rank_sum = 0;
    double dist_sum = 0.0;
    stats.min_rank = std::numeric_limits<int>::max();
    for (PID id : ids) {
        const auto it = gt_rank.find(id);
        CHECK(it != gt_rank.end()) << "lost/gained id is missing from gt rank map";
        const int rank = it->second;
        stats.min_rank = std::min(stats.min_rank, rank);
        rank_sum += rank;
        dist_sum += exact_distance(data, query, id, dist_type);
    }
    stats.mean_rank = static_cast<double>(rank_sum) / ids.size();
    stats.mean_dist = dist_sum / ids.size();
    return stats;
}

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK_GT(FLAGS_compare_topk, 0) << "compare_topk must be positive";
    CHECK_GT(FLAGS_compare_nprobe, 0) << "compare_nprobe must be positive";
    CHECK(!FLAGS_seg_plan.empty()) << "provide custom plan through -seg_plan";

    SearcherConfig searcher_cfg;
    if (FLAGS_searcher_dist_type == 0) {
        searcher_cfg.dist_type = DistType::L2Sqr;
    } else if (FLAGS_searcher_dist_type == 1) {
        searcher_cfg.dist_type = DistType::IP;
    } else {
        LOG(ERROR) << "Invalid searcher distance type: " << FLAGS_searcher_dist_type;
        return -1;
    }
    searcher_cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;

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
    CHECK_GE(gt.cols(), FLAGS_compare_topk) << "groundtruth has fewer columns than compare_topk";

    IVF default_ivf;
    IVF custom_ivf;
    std::cout << "load default index from " << default_index << '\n';
    default_ivf.load(default_index.c_str());
    std::cout << "load custom index from " << custom_index << '\n';
    custom_ivf.load(custom_index.c_str());

    std::string output = FLAGS_compare_output;
    if (output.empty()) {
        output = fmt::format("{}compare_{}_{}_vs_{}_np{}_top{}.csv",
                             result_path(), FLAGS_dataset, default_args, custom_args,
                             FLAGS_compare_nprobe, FLAGS_compare_topk);
    }
    std::ofstream csv(output, std::ios::out);
    CHECK(csv.is_open()) << "failed to open output: " << output;

    csv << "query_id,nprobe,topk,default_hits,custom_hits,delta_hits,"
        << "default_recall,custom_recall,result_overlap,default_only_results,custom_only_results,"
        << "lost_gt_count,gained_gt_count,lost_gt_min_rank,lost_gt_mean_rank,lost_gt_mean_dist,"
        << "gained_gt_min_rank,gained_gt_mean_rank,gained_gt_mean_dist,"
        << "gt_k_dist,gt_kplus1_dist,lost_gt_ids,gained_gt_ids\n";

    const size_t nq = query.rows();
    const size_t topk = static_cast<size_t>(FLAGS_compare_topk);
    std::vector<PID> default_results(topk);
    std::vector<PID> custom_results(topk);

    size_t default_hit_sum = 0;
    size_t custom_hit_sum = 0;
    size_t custom_better = 0;
    size_t custom_equal = 0;
    size_t custom_worse = 0;
    int worst_delta = 0;
    size_t worst_query = 0;

    for (size_t qi = 0; qi < nq; ++qi) {
        const FloatVec q = query.row(qi);
        default_ivf.search(q, topk, FLAGS_compare_nprobe, searcher_cfg, default_results.data());
        custom_ivf.search(q, topk, FLAGS_compare_nprobe, searcher_cfg, custom_results.data());

        std::unordered_map<PID, int> gt_rank;
        gt_rank.reserve(topk * 2);
        std::unordered_set<PID> gt_set;
        gt_set.reserve(topk * 2);
        for (size_t i = 0; i < topk; ++i) {
            PID id = gt(qi, i);
            gt_set.insert(id);
            gt_rank.emplace(id, static_cast<int>(i));
        }

        std::unordered_set<PID> default_set(default_results.begin(), default_results.end());
        std::unordered_set<PID> custom_set(custom_results.begin(), custom_results.end());
        std::vector<PID> lost_gt;
        std::vector<PID> gained_gt;
        size_t default_hits = 0;
        size_t custom_hits = 0;
        for (PID id : gt_set) {
            const bool in_default = default_set.find(id) != default_set.end();
            const bool in_custom = custom_set.find(id) != custom_set.end();
            default_hits += in_default;
            custom_hits += in_custom;
            if (in_default && !in_custom) {
                lost_gt.push_back(id);
            } else if (!in_default && in_custom) {
                gained_gt.push_back(id);
            }
        }
        std::sort(lost_gt.begin(), lost_gt.end(), [&](PID a, PID b) { return gt_rank[a] < gt_rank[b]; });
        std::sort(gained_gt.begin(), gained_gt.end(), [&](PID a, PID b) { return gt_rank[a] < gt_rank[b]; });

        size_t result_overlap = 0;
        for (PID id : default_results) {
            result_overlap += custom_set.find(id) != custom_set.end();
        }

        const int delta = static_cast<int>(custom_hits) - static_cast<int>(default_hits);
        custom_better += delta > 0;
        custom_equal += delta == 0;
        custom_worse += delta < 0;
        if (delta < worst_delta) {
            worst_delta = delta;
            worst_query = qi;
        }
        default_hit_sum += default_hits;
        custom_hit_sum += custom_hits;

        const auto lost_stats = summarize_neighbors(lost_gt, gt_rank, data, q, searcher_cfg.dist_type);
        const auto gained_stats = summarize_neighbors(gained_gt, gt_rank, data, q, searcher_cfg.dist_type);
        const float gt_k_dist = exact_distance(data, q, gt(qi, topk - 1), searcher_cfg.dist_type);
        const float gt_kplus1_dist = gt.cols() > static_cast<int>(topk)
                                       ? exact_distance(data, q, gt(qi, topk), searcher_cfg.dist_type)
                                       : std::numeric_limits<float>::quiet_NaN();

        csv << qi << ',' << FLAGS_compare_nprobe << ',' << topk << ','
            << default_hits << ',' << custom_hits << ',' << delta << ','
            << static_cast<double>(default_hits) / topk << ','
            << static_cast<double>(custom_hits) / topk << ','
            << result_overlap << ',' << (topk - result_overlap) << ',' << (topk - result_overlap) << ','
            << lost_stats.count << ',' << gained_stats.count << ','
            << lost_stats.min_rank << ',' << lost_stats.mean_rank << ',' << lost_stats.mean_dist << ','
            << gained_stats.min_rank << ',' << gained_stats.mean_rank << ',' << gained_stats.mean_dist << ','
            << gt_k_dist << ',' << gt_kplus1_dist << ','
            << join_ids(lost_stats.ids) << ',' << join_ids(gained_stats.ids) << '\n';
    }

    csv.close();

    const double denom = static_cast<double>(nq) * topk;
    const double default_recall = default_hit_sum / denom;
    const double custom_recall = custom_hit_sum / denom;
    std::cout << "output: " << output << '\n';
    std::cout << "default_recall: " << default_recall << '\n';
    std::cout << "custom_recall: " << custom_recall << '\n';
    std::cout << "delta_recall: " << custom_recall - default_recall << '\n';
    std::cout << "custom_better_queries: " << custom_better << '\n';
    std::cout << "custom_equal_queries: " << custom_equal << '\n';
    std::cout << "custom_worse_queries: " << custom_worse << '\n';
    std::cout << "worst_query: " << worst_query << '\n';
    std::cout << "worst_delta_hits: " << worst_delta << '\n';

    return 0;
}

#pragma once

#include <algorithm>
#include <cctype>
#include <cstring>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "quantization/config.h"

DEFINE_int32(num_threads, 0, "number of threads to use");
// DEFINE_bool(enable_statistis, false, "Enable extra statistics (will slow down the program)");
DEFINE_string(data_path, "", "dataset path");
DEFINE_string(dataset, "", "dataset name.");
DEFINE_double(B, 2, "number of bits for quantization.");
DEFINE_int32(K, 4096, "Number of centroids");
DEFINE_bool(enable_PCA, true, "use pretrained PCA");
DEFINE_bool(use_ipivf, false, "use IPIVF or not. If true, will use IPIVF searcher instead of CAQ searcher");
DEFINE_bool(use_1_centroid, false, "use 1 centroid for each cluster. Only works with CAQ quantization");

// CAQ config
DEFINE_bool(rand_rotate, true, "Enable random rotation for quantization");
DEFINE_int32(caq_adj_rd_lmt, 6, "adjustment round limit. 0 means no limit");
DEFINE_double(caq_adj_eps, 1e-8, "adjustment with EPS");
DEFINE_int32(caq_ori_qB, 0, "(Experiment Only) Original quantization bits. 0 means disable");

// SAQ config
DEFINE_bool(enable_segmentation, true, "enable segmentation");
DEFINE_int32(seg_eqseg, 0, "segmentation equalization");
DEFINE_string(seg_plan, "", "custom SAQ segment plan override, format dim:bits,dim:bits,...");
DEFINE_bool(use_compact_layout, false, "use compact memory layout");
DEFINE_double(q_firstdim, 0, "only quantization first dimension");

// Searcher config
DEFINE_double(searcher_vars_bound_m, 4, "");
DEFINE_bool(searcher_full_refine, false, "disable per-segment early break during accurate refinement");
DEFINE_bool(searcher_force_accurate_scan, false, "scan all probed IVF candidates with full-code distances");
DEFINE_bool(searcher_safe_block_min, false, "use NaN-safe scalar fallback for multi-segment block minima");
DEFINE_int32(searcher_dist_type, 0, "searcher distance type. 0: L2Sqr, 1: IP");


inline std::string compactPlanForPath(const std::string &plan_spec) {
    if (plan_spec.empty()) {
        return "";
    }
    std::string suffix = "_plan";
    for (unsigned char ch : plan_spec) {
        if (std::isdigit(ch)) {
            suffix.push_back(static_cast<char>(ch));
        } else if (ch == ':' || ch == 'x' || ch == 'X') {
            suffix.push_back('x');
        } else if (ch == ',' || ch == ';' || std::isspace(ch)) {
            if (suffix.back() != '_') {
                suffix.push_back('_');
            }
        }
    }
    if (suffix.back() == '_') {
        suffix.pop_back();
    }
    return suffix;
}

inline std::vector<std::pair<size_t, size_t>> parseSegPlanSpec(const std::string &plan_spec) {
    std::vector<std::pair<size_t, size_t>> plan;
    if (plan_spec.empty()) {
        return plan;
    }

    std::stringstream ss(plan_spec);
    std::string token;
    while (std::getline(ss, token, ',')) {
        token.erase(std::remove_if(token.begin(), token.end(), [](unsigned char ch) {
                        return std::isspace(ch);
                    }),
                    token.end());
        if (token.empty()) {
            continue;
        }
        auto sep = token.find(':');
        if (sep == std::string::npos) {
            sep = token.find('x');
        }
        if (sep == std::string::npos) {
            sep = token.find('X');
        }
        CHECK(sep != std::string::npos) << "Bad -seg_plan token: " << token;

        size_t end_pos = 0;
        size_t dim_len = std::stoull(token.substr(0, sep), &end_pos);
        CHECK_EQ(end_pos, sep) << "Bad segment dimension in -seg_plan token: " << token;
        std::string bits_str = token.substr(sep + 1);
        size_t bits = std::stoull(bits_str, &end_pos);
        CHECK_EQ(end_pos, bits_str.size()) << "Bad segment bits in -seg_plan token: " << token;
        plan.emplace_back(dim_len, bits);
    }
    CHECK(!plan.empty()) << "-seg_plan was provided but no valid segment was parsed";
    return plan;
}

inline std::string parseArgs(saqlib::QuantizeConfig *config = nullptr) {
    saqlib::QuantizeConfig cfg;
    auto args_str = fmt::format("ivf{}", FLAGS_K);
    cfg.avg_bits = FLAGS_B;
    cfg.single.random_rotation = FLAGS_rand_rotate;

    {
        cfg.single.quant_type = saqlib::BaseQuantType::CAQ;
        cfg.single.caq_adj_rd_lmt = FLAGS_caq_adj_rd_lmt;
        cfg.single.caq_adj_eps = FLAGS_caq_adj_eps;
    }
    if (FLAGS_caq_ori_qB) {
        cfg.single.caq_ori_qB = FLAGS_caq_ori_qB;
    }
    if (FLAGS_enable_segmentation) {
        cfg.enable_segmentation = true;
        if (FLAGS_seg_eqseg > 0) {
            cfg.seg_eqseg = FLAGS_seg_eqseg;
        }
    } else {
        cfg.enable_segmentation = false;
    }
    if (FLAGS_use_compact_layout) {
        cfg.use_compact_layout = true;
    }

    args_str += cfg.toString();
    args_str += compactPlanForPath(FLAGS_seg_plan);

    if (config)
        *config = cfg;

    if (FLAGS_enable_PCA) {
        args_str += fmt::format("_pca");
    }

    if (FLAGS_use_1_centroid) {
        args_str += "_1c";
    }

    return args_str;
}

// Struct to store file paths for dataset loading
struct DataFilePaths {
    std::string input_path;
    std::string result_path;

    std::string data_file;
    std::string centroids_file;
    std::string cids_file;
    std::string data_vars_file;

    std::string quant_file;

    std::string query_file;
    std::string gt_file;

    // Initialize file paths based on dataset parameters
    DataFilePaths() {
        const auto &dataset = FLAGS_dataset;
        bool use_pca = FLAGS_enable_PCA;
        size_t K = FLAGS_K;
        auto args_str = parseArgs();

        input_path = std::string("./data/") + dataset;
        result_path = std::string("./results/saq/");

        data_file = fmt::format("{}/{}_base{}.fvecs", input_path, dataset, use_pca ? "_pca" : "");
        centroids_file = fmt::format("{}/{}_centroid_{}{}.fvecs", input_path, dataset, K, use_pca ? "_pca" : "");
        cids_file = fmt::format("{}/{}_cluster_id_{}.ivecs", input_path, dataset, K);
        data_vars_file = fmt::format("{}/{}_base{}.vars.fvecs", input_path, dataset, use_pca ? "_pca" : "");

        quant_file = fmt::format("{}/{}.index", input_path, args_str);

        query_file = fmt::format("{}/{}_query{}.fvecs", input_path, dataset, use_pca ? "_pca" : "");
        gt_file = fmt::format("{}/{}_groundtruth.ivecs", input_path, dataset);

        if (FLAGS_searcher_dist_type == 1) {
            auto add_ip = [](std::string &s) {
                size_t last_dot = s.find_last_of(".");
                if (last_dot != std::string::npos) {
                    s.replace(last_dot, 1, ".ip.");
                }
            };
            add_ip(gt_file);
        }
    }
};

#include <fstream>
#include <iostream>

#include <fmt/core.h>
#include <sstream>
#include <string>
#include <vector>

#include "define_options.h"

#include "index/ivf.hpp"
#include "utils/IO.hpp"
#include "utils/StopW.hpp"

using namespace saqlib;

namespace {
using QuantPlan = SaqData::QuantPlanT;

QuantPlan parsePlanString(const std::string &plan_str) {
    QuantPlan plan;
    std::stringstream ss(plan_str);
    std::string item;
    while (std::getline(ss, item, ',')) {
        auto pos = item.find(':');
        CHECK(pos != std::string::npos) << "bad plan segment: " << item;
        size_t dim = std::stoull(item.substr(0, pos));
        size_t bits = std::stoull(item.substr(pos + 1));
        plan.emplace_back(dim, bits);
    }
    CHECK(!plan.empty()) << "empty plan string";
    return plan;
}

void loadSharedPlanFile(const std::string &path, std::vector<QuantPlan> &plans, std::vector<size_t> &plan_ids) {
    std::ifstream input(path);
    CHECK(input.is_open()) << "cannot open shared plan file: " << path;

    std::string token;
    size_t expected_plans = 0;
    size_t expected_clusters = 0;
    while (input >> token) {
        if (token == "shared_plans_v1") {
            continue;
        }
        if (token == "num_plans") {
            input >> expected_plans;
            plans.clear();
            plans.resize(expected_plans);
        } else if (token == "plan") {
            size_t plan_id = 0;
            std::string plan_str;
            input >> plan_id >> plan_str;
            CHECK_LT(plan_id, plans.size());
            plans[plan_id] = parsePlanString(plan_str);
        } else if (token == "num_clusters") {
            input >> expected_clusters;
            plan_ids.assign(expected_clusters, 0);
        } else if (token == "assignments") {
            CHECK_GT(expected_clusters, 0);
            for (size_t i = 0; i < expected_clusters; ++i) {
                size_t cid = 0;
                size_t plan_id = 0;
                input >> cid >> plan_id;
                CHECK_LT(cid, plan_ids.size());
                CHECK_LT(plan_id, plans.size());
                plan_ids[cid] = plan_id;
            }
        } else {
            CHECK(false) << "unknown shared plan file token: " << token;
        }
    }

    CHECK_EQ(plans.size(), expected_plans);
    CHECK_EQ(plan_ids.size(), expected_clusters);
    for (size_t i = 0; i < plans.size(); ++i) {
        CHECK(!plans[i].empty()) << "missing shared plan " << i;
    }
}
} // namespace

class IndexCreator {
  private:
    FloatRowMat data_;
    FloatRowMat centroids_;
    UintRowMat cids_;
    FloatRowMat data_vars_;
    std::unique_ptr<IVF> ivf_;

  public:
    void buildIndex(const std::string &dataset, size_t K, const QuantizeConfig &cfg, const std::string &args_str) {
        // Create file paths and load all data needed for index creation
        DataFilePaths paths;
        utils::load_something<float, FloatRowMat>(paths.data_file.c_str(), data_);
        utils::load_something<float, FloatRowMat>(paths.centroids_file.c_str(), centroids_);
        utils::load_something<PID, UintRowMat>(paths.cids_file.c_str(), cids_);
        if (utils::file_exists(paths.data_vars_file.c_str())) {
            utils::load_something<float, FloatRowMat>(paths.data_vars_file.c_str(), data_vars_);
        }

        size_t num_threads = FLAGS_num_threads ? FLAGS_num_threads : 64;

        size_t num_vecs = data_.rows();
        size_t num_dim = data_.cols();

        std::cout << "data loaded\n";
        std::cout << "\tN: " << num_vecs << '\n';
        std::cout << "\tDIM: " << num_dim << '\n';

        utils::StopW stopw;

        // Create IVF index using unique_ptr
        ivf_ = std::make_unique<IVF>(num_vecs, num_dim, K, cfg);

        // Set variance if available
        if (data_vars_.rows() != 0) {
            ivf_->set_variance(std::move(data_vars_));
        }
        if (!FLAGS_shared_plan_file.empty()) {
            std::vector<QuantPlan> shared_plans;
            std::vector<size_t> cluster_plan_ids;
            loadSharedPlanFile(FLAGS_shared_plan_file, shared_plans, cluster_plan_ids);
            CHECK_EQ(cluster_plan_ids.size(), K) << "shared-plan assignment must cover all IVF clusters";
            ivf_->set_shared_quant_plans(std::move(shared_plans), std::move(cluster_plan_ids));
        }

        ivf_->construct(data_, centroids_, cids_.data(), num_threads, FLAGS_use_1_centroid);
        float tm_sec = stopw.getElapsedTimeMili() / 1000;
        LOG(INFO) << "ivf constructed ";
        ivf_->save(paths.quant_file.c_str());

        std::cout << "index saved at: " << paths.quant_file << '\n';
        std::cout << "Indexing time: " << tm_sec << "seconds\n";

        // === output to csv ===
        auto csv_path = fmt::format("{}/{}_{}.index.csv", paths.result_path, dataset, args_str);
        std::ofstream csv_data(csv_path, std::ios::out);
        csv_data << "index_time_s,ip_err_avg,ip_err_max";
        auto &statis_ip = ivf_->quant_metrics_.norm_ip_o_oa;
        csv_data << std::endl;

        csv_data << tm_sec << ",";
        csv_data << statis_ip.avg() << ",";
        csv_data << statis_ip.max();
        csv_data << std::endl;
        csv_data.close();
        std::cout << "Basic Statistics logged to: " << csv_path << "\n";
    }
};

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    QuantizeConfig cfg;
    auto args_str = parseArgs(&cfg);
    LOG(INFO) << args_str << "\n";

    IndexCreator creator;
    creator.buildIndex(FLAGS_dataset, FLAGS_K, cfg, args_str);

    return 0;
}

#include <cstring>
#include <iostream>
#include <set>
#include <string>

#include "define_options.h"

#include "defines.hpp"
#include "utils/BS_thread_pool.hpp"
#include "utils/IO.hpp"
#include "utils/memory.hpp"
#include "utils/pool.hpp"
#include "utils/space.hpp"

using namespace saqlib;

DEFINE_int32(gt_topk, 1000, "top-k exact groundtruth depth to compute");
DEFINE_int32(gt_threads, 100, "number of threads used for exact groundtruth computation");
DEFINE_string(gt_output, "", "optional output ivecs path; defaults to the dataset groundtruth path");
DEFINE_bool(gt_overwrite, false, "overwrite an existing groundtruth output file");
DEFINE_bool(gt_check_existing, true, "when output exists and overwrite is false, compare it against the computed GT");

size_t N;
size_t DIM;
size_t NQ;
size_t K;

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    std::string DATASET = FLAGS_dataset;
    DataFilePaths paths;
    CHECK_GT(FLAGS_gt_topk, 0);
    CHECK_GT(FLAGS_gt_threads, 0);
    const size_t topk = static_cast<size_t>(FLAGS_gt_topk);
    const std::string output_file = FLAGS_gt_output.empty() ? paths.gt_file : FLAGS_gt_output;

    FloatRowMat data;
    FloatRowMat queries;
    FloatRowMat centroids;
    UintRowMat gt;
    UintRowMat cids;

    utils::load_something<float, FloatRowMat>(paths.data_file.c_str(), data);
    utils::load_something<float, FloatRowMat>(paths.query_file.c_str(), queries);

    N = data.rows();
    DIM = queries.cols();
    NQ = queries.rows();

    std::cout << "data loaded\n";
    std::cout << "\tN: " << N << '\n'
              << "\tDIM: " << DIM << '\n';
    std::cout << "query loaded\n";
    std::cout << "\tNQ: " << NQ << '\n';

    BS::thread_pool pool(static_cast<size_t>(FLAGS_gt_threads));
    gt.resize(NQ, topk);

    // if (FLAGS_DEBUG) {
    //     NQ = 1;
    // }

    for (size_t qi = 0; qi < NQ; qi++) {
        pool.detach_task([&, qi]() {
            FloatVec query = queries.row(qi);
            utils::ResultPool KNNs(topk, FLAGS_searcher_dist_type == 1);
            if (FLAGS_searcher_dist_type == 0) { // L2Sqr
                for (size_t id = 0; id < N; ++id) {
                    auto dist = (data.row(id) - query).squaredNorm();
                    KNNs.insert(id, dist);
                }
            } else { // IP
                for (size_t id = 0; id < N; ++id) {
                    auto dist = query.dot(data.row(id));
                    KNNs.insert(id, dist);
                }
            }

            KNNs.copy_results(gt.row(qi).data());
        });
    }
    pool.wait();

    if (utils::file_exists(output_file.data()) && !FLAGS_gt_overwrite) {
        std::cout << "ground truth file exists: " << output_file << '\n';
        if (!FLAGS_gt_check_existing) {
            std::cout << "skip existing ground truth check\n";
            return 0;
        }
        std::cout << "check if the ground truth is correct\n";
        UintRowMat gt_test;
        utils::load_something<PID, UintRowMat>(output_file.data(), gt_test);
        CHECK_GE(gt_test.cols(), topk) << "existing GT depth is smaller than gt_topk";

        for (size_t i = 0; i < NQ; ++i) {
            std::set<PID> gt_set;
            for (size_t j = 0; j < topk; ++j) {
                gt_set.insert(gt_test(i, j));
            }
            for (size_t j = 0; j < topk; ++j) {
                if (gt_set.find(gt(i, j)) == gt_set.end()) {
                    std::cerr << "ground truth not match\n";
                    std::cerr << "query: " << i << '\n';
                    std::cerr << "gt: " << gt(i, j) << '\n';
                    std::cerr << "gt_test: " << gt_test(i, j) << '\n';
                    std::cerr << "-===========================\n";
                    // return -1;
                }
            }
        }
        std::cout << "ground truth is correct\n";
        return 0;
    }

    // if (FLAGS_DEBUG) {
    //     return 0;
    // }
    utils::save_vecs<float, UintRowMat>(output_file.data(), gt);
    std::cout << "ground truth saved to " << output_file << '\n';

    return 0;
}

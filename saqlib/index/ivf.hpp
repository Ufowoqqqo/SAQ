#pragma once

#include <cassert>
#include <cstddef>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <vector>

#include "glog/logging.h"
#include <fmt/core.h>

#include "defines.hpp"
#include "index/initializer.hpp"
#include "quantization/cluster_data.hpp"
#include "quantization/config.h"
#include "quantization/saq_data.hpp"
#include "quantization/saq_quantizer.hpp"
#include "quantization/saq_searcher.hpp"
#include "utils/BS_thread_pool.hpp"
#include "utils/StopW.hpp"
#include "utils/pool.hpp"

namespace saqlib
{
class IVF
{
  public:
    QuantMetrics quant_metrics_; // Quantization metrics
  protected:
    static constexpr size_t kSharedPlanMagic = 0x5351504c414e7631ULL; // "SQPLANv1"
    size_t num_data_; // num of data points
    size_t num_dim_;  // dimension of data points
    size_t num_cen_;  // num of centroids
    QuantizeConfig cfg_;
    std::unique_ptr<Initializer> initer_ = nullptr;
    std::vector<SaqCluData> parallel_clusters_; // cluster data for SAQ
    std::unique_ptr<SaqData> saq_data_;
    std::vector<std::unique_ptr<SaqData>> shared_saq_datas_;
    std::vector<SaqData::QuantPlanT> shared_quant_plans_;
    std::vector<size_t> cluster_plan_ids_;
    //  ======= Presistence data above  =======
    std::unique_ptr<SaqDataMaker> saq_data_maker_;

    void allocate_clusters(const std::vector<size_t> &);
    bool use_shared_plans() const { return !shared_saq_datas_.empty(); }
    const SaqData &saq_data_for_cluster(size_t cid) const {
        if (use_shared_plans()) {
            CHECK_LT(cid, cluster_plan_ids_.size());
            CHECK_LT(cluster_plan_ids_[cid], shared_saq_datas_.size());
            return *shared_saq_datas_[cluster_plan_ids_[cid]];
        }
        return *saq_data_;
    }
    void prepare_shared_saq_datas();

    void prepare_initer(const FloatRowMat *centroids)
    {
        if (num_cen_ < 20000ul) {
            this->initer_ = std::make_unique<FlatInitializer>(num_dim_,
            num_cen_);
        } else {
            CHECK(false) << "HNSW not implemented\n";
            // this->initer_ = std::make_unique<HNSWInitializer>(D, num_cen_);
        }

        if (centroids) {
            initer_->set_centroids(*centroids);
        }
    }

    void free_memory()
    {
        initer_.reset();
        parallel_clusters_.clear();
        saq_data_.reset();
        shared_saq_datas_.clear();
        shared_quant_plans_.clear();
        cluster_plan_ids_.clear();
        saq_data_maker_.reset();
    }

  public:
    explicit IVF() = default;
    explicit IVF(size_t n, size_t num_dim, size_t k, QuantizeConfig cfg)
        : num_data_(n), num_dim_(num_dim), num_cen_(k), cfg_(std::move(cfg)),
          saq_data_maker_(std::make_unique<SaqDataMaker>(cfg_, num_dim))
    {
    }
    IVF(const IVF &) = delete;

    ~IVF() { free_memory(); }

    auto num_data() const { return num_data_; }
    auto num_dim() const { return num_dim_; }
    auto &get_config() const { return cfg_; }
    auto get_initer() const { return initer_.get(); }
    const SaqData *get_saq_data() const { return saq_data_.get(); }
    auto &get_pclusters() const { return parallel_clusters_; }

    void set_shared_quant_plans(std::vector<SaqData::QuantPlanT> plans, std::vector<size_t> plan_ids)
    {
        shared_quant_plans_ = std::move(plans);
        cluster_plan_ids_ = std::move(plan_ids);
    }

    void construct(const FloatRowMat &data, const FloatRowMat &centroids, const PID *cluster_ids,
                   int num_threads = 64, bool use_1_centroid = false);

    void save(const char *) const;

    void load(const char *);

    template <DistType kDistType = DistType::Any>
    void search(const Eigen::RowVectorXf &__restrict__ ori_query,
                size_t topk, size_t nprobe, SearcherConfig searcher_cfg,
                PID *__restrict__ results, QueryRuntimeMetrics *runtime_metrics = nullptr);

    template <DistType kDistType = DistType::Any>
    void estimate(const Eigen::RowVectorXf &__restrict__ ori_query,
                  size_t nprobe, SearcherConfig searcher_cfg,
                  std::vector<std::pair<PID, float>> &dist_list, std::vector<float> *fast_dist_list = nullptr,
                  std::vector<float> *vars_dist_list = nullptr, QueryRuntimeMetrics *runtime_metrics = nullptr);

    size_t k() const { return num_cen_; }

    void set_variance(FloatVec vars)
    {
        saq_data_maker_->set_variance(std::move(vars));
    }

    void printQPlan(const SaqData *data, const std::string &label = "")
    {
        LOG(INFO) << (label.empty() ? "Dynamic bits allocation plan:" : label);
        size_t dims_sum = 0;
        std::string log = fmt::format("{}bits: ", cfg_.avg_bits);
        dims_sum = 0;
        for (auto &[dim_len, bits] : data->quant_plan) {
            log += fmt::format("| {} -> {} ({}d {}b) ", dims_sum, dims_sum + dim_len, dim_len, bits);
            dims_sum += dim_len;
        }
        LOG(INFO) << log;
    }
};

/**
 * @brief Construct clusters in IVF
 *
 * @param data Data vectors
 * @param centroids Centroid vectors as FloatRowMat (K*DIM)
 * @param clustter_ids Cluster ID for each data objects
 */
inline void IVF::construct(const FloatRowMat &data, const FloatRowMat &centroids, const PID *cluster_ids,
                           int num_threads, bool use_1_centroid)
{
    LOG(INFO) << "Start IVF construction...\n";

    // 1. prepare initializer
    prepare_initer(&centroids);

    // 2. prepare SAQ data
    {
        if (!saq_data_maker_->is_variance_set()) {
            // If variance is not set, compute it from data
            saq_data_maker_->compute_variance(data);
        }
        saq_data_ = saq_data_maker_->return_data();
        printQPlan(saq_data_.get());
        if (!shared_quant_plans_.empty()) {
            prepare_shared_saq_datas();
        }
    }

    // 3. prepare clusters
    std::vector<std::vector<PID>> id_lists(num_cen_);
    {
        std::vector<size_t> counts(num_cen_, 0);
        for (size_t i = 0; i < num_data_; ++i) {
            PID cid = cluster_ids[i];
            CHECK_LE(cid, num_cen_) << "Bad cluster id\n";
            id_lists[cid].push_back((PID)i);
            counts[cid] += 1;
        }
        allocate_clusters(counts);
    }

    // 4. quantize clusters
    {
        // use the same centroid for all clusters when quantizing
        FloatVec tot_avg_centroid;
        if (use_1_centroid) {
            tot_avg_centroid = data.colwise().mean();
        }
        SAQuantizer saq_quantizer_(saq_data_.get());
        std::vector<std::unique_ptr<SAQuantizer>> shared_quantizers;
        if (use_shared_plans()) {
            CHECK_EQ(cluster_plan_ids_.size(), num_cen_);
            shared_quantizers.reserve(shared_saq_datas_.size());
            for (const auto &data_ptr : shared_saq_datas_) {
                shared_quantizers.emplace_back(std::make_unique<SAQuantizer>(data_ptr.get()));
            }
        }
        BS::thread_pool pool(num_threads);
        utils::StopW stopw;
        /* Quantize each cluster */
        for (size_t i = 0; i < num_cen_; ++i) {
            pool.detach_task([&, this, i]() {
                const FloatVec &cur_centroid = use_1_centroid ? tot_avg_centroid : centroids.row(i);
                auto &clu = parallel_clusters_[i];

                if (use_shared_plans()) {
                    const auto plan_id = cluster_plan_ids_[i];
                    CHECK_LT(plan_id, shared_quantizers.size());
                    shared_quantizers[plan_id]->quantize_cluster(data, cur_centroid, id_lists[i], clu);
                } else {
                    saq_quantizer_.quantize_cluster(data, cur_centroid, id_lists[i], clu);
                }
            });
        }
        pool.wait();
        auto tm_ms = stopw.getElapsedTimeMicro() / 1000.0;
        LOG(INFO) << "Quantization done. tm: " << tm_ms / 1e3 << " S";
    }
}

inline void IVF::prepare_shared_saq_datas()
{
    CHECK(saq_data_) << "global SAQ data must be prepared first";
    CHECK_EQ(cluster_plan_ids_.size(), num_cen_);
    shared_saq_datas_.clear();
    shared_saq_datas_.reserve(shared_quant_plans_.size());
    for (size_t plan_id = 0; plan_id < shared_quant_plans_.size(); ++plan_id) {
        SaqDataMaker maker(cfg_, num_dim_);
        maker.set_variance(saq_data_->data_variance);
        maker.set_quant_plan(shared_quant_plans_[plan_id]);
        auto data = maker.return_data();
        printQPlan(data.get(), fmt::format("Shared quantization plan {}:", plan_id));
        shared_saq_datas_.emplace_back(std::move(data));
    }
    for (auto plan_id : cluster_plan_ids_) {
        CHECK_LT(plan_id, shared_saq_datas_.size());
    }
}

inline void IVF::allocate_clusters(const std::vector<size_t> &cluster_sizes)
{
    // init clusters
    parallel_clusters_.clear();
    parallel_clusters_.reserve(num_cen_);
    for (size_t i = 0; i < num_cen_; ++i) {
        const auto &plan = use_shared_plans() ? saq_data_for_cluster(i).quant_plan : saq_data_->quant_plan;
        parallel_clusters_.emplace_back(cluster_sizes[i], plan, cfg_.use_compact_layout);
    }
    LOG(INFO) << "Initializing done... num_points: " << num_data_;
}

inline void IVF::save(const char *filename) const
{
    if (parallel_clusters_.empty()) {
        LOG(ERROR) << "IVF not constructed\n";
        return;
    }

    std::ofstream output(filename, std::ios::binary);

    /* Save meta data */
    output.write((char *)&num_data_, sizeof(size_t));
    output.write((char *)&num_dim_, sizeof(size_t));
    output.write((char *)&num_cen_, sizeof(size_t));

    this->initer_->save(output, filename);

    saq_data_->save(output);
    if (use_shared_plans()) {
        size_t magic = kSharedPlanMagic;
        output.write((char *)&magic, sizeof(size_t));
        size_t num_shared_plans = shared_saq_datas_.size();
        output.write((char *)&num_shared_plans, sizeof(size_t));
        for (const auto &data : shared_saq_datas_) {
            data->save(output);
        }
        size_t num_plan_ids = cluster_plan_ids_.size();
        output.write((char *)&num_plan_ids, sizeof(size_t));
        output.write((char *)cluster_plan_ids_.data(), sizeof(size_t) * num_plan_ids);
    }

    /* Save number of vectors of each cluster */
    std::vector<size_t> cluster_sizes;
    cluster_sizes.reserve(num_cen_);
    for (const auto &cur_cluster : parallel_clusters_) {
        cluster_sizes.push_back(cur_cluster.num_vec_);
    }
    output.write((char *)cluster_sizes.data(), sizeof(size_t) * num_cen_);

    for (const auto &pclu : parallel_clusters_) {
        pclu.save(output);
    }

    output.close();
}

inline void IVF::load(const char *filename)
{
    free_memory();
    LOG(INFO) << "Loading IVF...\n";
    std::ifstream input(filename, std::ios::binary);
    assert(input.is_open());

    /* Load meta data */
    LOG(INFO) << "\tLoading meta data...\n";
    input.read((char *)&this->num_data_, sizeof(size_t));
    input.read((char *)&this->num_dim_, sizeof(size_t));
    input.read((char *)&this->num_cen_, sizeof(size_t));

    prepare_initer(nullptr);
    this->initer_->load(input, filename);

    saq_data_ = std::make_unique<SaqData>();
    saq_data_->load(input);

    /* Load number of vectors of each cluster */
    std::vector<size_t> cluster_sizes(num_cen_, 0);
    size_t first_cluster_size_or_magic = 0;
    input.read((char *)&first_cluster_size_or_magic, sizeof(size_t));
    if (first_cluster_size_or_magic == kSharedPlanMagic) {
        size_t num_shared_plans = 0;
        input.read((char *)&num_shared_plans, sizeof(size_t));
        shared_saq_datas_.clear();
        shared_saq_datas_.reserve(num_shared_plans);
        for (size_t i = 0; i < num_shared_plans; ++i) {
            auto data = std::make_unique<SaqData>();
            data->load(input);
            shared_saq_datas_.emplace_back(std::move(data));
        }
        size_t num_plan_ids = 0;
        input.read((char *)&num_plan_ids, sizeof(size_t));
        CHECK_EQ(num_plan_ids, num_cen_) << "shared-plan assignment size mismatch";
        cluster_plan_ids_.resize(num_plan_ids);
        input.read((char *)cluster_plan_ids_.data(), sizeof(size_t) * num_plan_ids);
        for (auto plan_id : cluster_plan_ids_) {
            CHECK_LT(plan_id, shared_saq_datas_.size());
        }
        input.read((char *)cluster_sizes.data(), sizeof(size_t) * num_cen_);
    } else {
        cluster_sizes[0] = first_cluster_size_or_magic;
        if (num_cen_ > 1) {
            input.read((char *)(cluster_sizes.data() + 1), sizeof(size_t) * (num_cen_ - 1));
        }
    }
    DCHECK_EQ(num_data_,
              std::accumulate(cluster_sizes.begin(), cluster_sizes.end(), 0));

    allocate_clusters(cluster_sizes);
    for (auto &pclu : parallel_clusters_) {
        pclu.load(input);
    }

    input.close();
    LOG(INFO) << "Index loaded\n";
}

/*
 * @brief Search for k nearest neighbors
 *
 * @param ori_query Original query vector (without padding)
 * @param data Data vectors without rotate
 * @param topk Number of neighbors
 * @param nprobe Number of clusters to search
 * @param results Result pool
 */
template <DistType kDistType>
inline void IVF::search(const Eigen::RowVectorXf &__restrict__ ori_query, size_t topk, size_t nprobe,
                        SearcherConfig searcher_cfg, PID *__restrict__ results,
                        QueryRuntimeMetrics *runtime_metrics)
{
    CHECK_EQ(ori_query.cols(), num_dim_);

    /* Compute distance to original centroids using original query */
    std::vector<Candidate> centroid_dist(nprobe);
    this->initer_->centroids_distances(ori_query, nprobe, searcher_cfg.dist_type, centroid_dist);

    utils::ResultPool KNNs(topk, searcher_cfg.dist_type == DistType::IP);

    std::unique_ptr<SAQSearcher<kDistType>> searcher;
    std::vector<std::unique_ptr<SAQSearcher<kDistType>>> shared_searchers;
    if (use_shared_plans()) {
        shared_searchers.resize(shared_saq_datas_.size());
    } else {
        searcher = std::make_unique<SAQSearcher<kDistType>>(*saq_data_.get(), searcher_cfg, ori_query);
    }

    // LOG(INFO) << "Searching clusters";
    for (size_t i = 0; i < nprobe; ++i) {
        PID cid = centroid_dist[i].id;
        if (use_shared_plans()) {
            const auto plan_id = cluster_plan_ids_[cid];
            CHECK_LT(plan_id, shared_searchers.size());
            if (!shared_searchers[plan_id]) {
                shared_searchers[plan_id] =
                    std::make_unique<SAQSearcher<kDistType>>(*shared_saq_datas_[plan_id], searcher_cfg, ori_query);
            }
            shared_searchers[plan_id]->searchCluster(&parallel_clusters_[cid], KNNs);
        } else {
            searcher->searchCluster(&parallel_clusters_[cid], KNNs);
        }
    }

    KNNs.copy_results(results);
    if (runtime_metrics) {
        if (use_shared_plans()) {
            QueryRuntimeMetrics metrics;
            for (const auto &cur_searcher : shared_searchers) {
                if (!cur_searcher) {
                    continue;
                }
                auto cur_metrics = cur_searcher->getRuntimeMetrics();
                metrics.acc_bitsum += cur_metrics.acc_bitsum;
                metrics.fast_bitsum += cur_metrics.fast_bitsum;
                metrics.total_comp_cnt += cur_metrics.total_comp_cnt;
            }
            *runtime_metrics = metrics;
        } else {
            *runtime_metrics = searcher->getRuntimeMetrics();
        }
    }

    // if (FLAGS_DEBUG) {
    //     LOG(INFO) << "Search done. Topk: " << topk << ", nprobe: " << nprobe;
    //     std::string str;
    //     for (size_t i = 0; i < topk; ++i) {
    //         auto [id, dist] = KNNs.get(i);
    //         str += fmt::format("\t{}: id={}, dist={}\n", i, id, dist);
    //     }
    //     LOG(INFO) << "Results: \n"
    //               << str;
    // }
}

template <DistType kDistType>
inline void IVF::estimate(const Eigen::RowVectorXf &__restrict__ ori_query, size_t nprobe,
                          SearcherConfig searcher_cfg,
                          std::vector<std::pair<PID, float>> &dist_list, std::vector<float> *fast_dist_list, std::vector<float> *vars_dist_list, QueryRuntimeMetrics *runtime_metrics)
{
    CHECK_EQ(ori_query.cols(), num_dim_);

    /* Compute distance to original centroids using original query */
    std::vector<Candidate> centroid_dist(nprobe);
    this->initer_->centroids_distances(ori_query, nprobe, searcher_cfg.dist_type, centroid_dist);

    SaqCluEstimator<kDistType> estimator(*saq_data_.get(), searcher_cfg, ori_query);
    std::vector<std::unique_ptr<SaqCluEstimator<kDistType>>> shared_estimators;
    if (use_shared_plans()) {
        shared_estimators.reserve(shared_saq_datas_.size());
        for (const auto &data : shared_saq_datas_) {
            shared_estimators.emplace_back(std::make_unique<SaqCluEstimator<kDistType>>(*data, searcher_cfg, ori_query));
        }
    }
    for (size_t j = 0; j < nprobe; ++j) {
        PID cid = centroid_dist[j].id;
        const auto &pcluster = parallel_clusters_[cid];
        auto &cur_estimator = use_shared_plans() ? *shared_estimators[cluster_plan_ids_[cid]] : estimator;

        // Prepare estimator for this cluster
        cur_estimator.prepare(&pcluster);

        // Estimate distances for all vectors in this cluster
        float PORTABLE_ALIGN64 fastdist_t[KFastScanSize];
        float PORTABLE_ALIGN64 vardist_t[KFastScanSize];
        for (size_t vec_idx = 0; vec_idx < pcluster.num_vec_; ++vec_idx) {
            if (vec_idx % KFastScanSize == 0) {
                __m512 t[2];
                cur_estimator.compFastDist(vec_idx / KFastScanSize, t);
                _mm512_store_ps(fastdist_t, t[0]);
                _mm512_store_ps(fastdist_t + 16, t[1]);
                cur_estimator.varsEstDist(vec_idx / KFastScanSize, t);
                _mm512_store_ps(vardist_t, t[0]);
                _mm512_store_ps(vardist_t + 16, t[1]);
            }

            PID data_id = pcluster.ids()[vec_idx];
            float est_dist = cur_estimator.compAccurateDist(vec_idx);

            dist_list.emplace_back(data_id, est_dist);

            if (fast_dist_list) {
                fast_dist_list->push_back(fastdist_t[vec_idx % KFastScanSize]);
            }
            if (vars_dist_list) {
                vars_dist_list->push_back(vardist_t[vec_idx % KFastScanSize]);
            }
        }
    }
    if (runtime_metrics) {
        if (use_shared_plans()) {
            QueryRuntimeMetrics metrics;
            for (const auto &cur_estimator : shared_estimators) {
                auto cur_metrics = cur_estimator->getRuntimeMetrics();
                metrics.acc_bitsum += cur_metrics.acc_bitsum;
                metrics.fast_bitsum += cur_metrics.fast_bitsum;
                metrics.total_comp_cnt += cur_metrics.total_comp_cnt;
            }
            *runtime_metrics = metrics;
        } else {
            *runtime_metrics = estimator.getRuntimeMetrics();
        }
    }
}
} // namespace saqlib

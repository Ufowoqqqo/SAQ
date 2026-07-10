#include <algorithm>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "define_options.h"

#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/IO.hpp"
#include "utils/StopW.hpp"

using namespace saqlib;

DEFINE_string(graph_data_file, "", "Override base vector file. Defaults to DataFilePaths::data_file.");
DEFINE_string(graph_query_file, "", "Override query vector file. Defaults to DataFilePaths::query_file.");
DEFINE_string(graph_index_file, "", "Override SAQ index file. Defaults to DataFilePaths::quant_file.");
DEFINE_string(graph_output_prefix, "", "Output prefix for aggregate CSV, event CSV, and Markdown summary.");
DEFINE_int32(graph_subset, 512, "Number of first base vectors used to build a deterministic exact kNN adjacency.");
DEFINE_int32(graph_degree, 32, "Fixed diagnostic graph degree.");
DEFINE_int32(graph_max_queries, 16, "Maximum number of held-out queries used for replay.");
DEFINE_int32(graph_roots_per_query, 8, "Exact-nearest subset roots evaluated per query.");
DEFINE_int32(graph_max_events, 0, "Global event cap. 0 means no cap beyond query/root budgets.");
DEFINE_int32(graph_topl_max, 32, "Largest top-L containment value reported as powers of two.");
DEFINE_bool(graph_write_event_csv, true, "Write per-event estimator ranks.");

namespace {

struct ClusterLoc {
    PID cluster_id = 0;
    size_t local_idx = 0;
    bool valid = false;
};

struct PathConfig {
    std::string data_file;
    std::string query_file;
    std::string index_file;
    std::string output_prefix;
};

struct EstimatorStats {
    std::string name;
    double approx_code_bits_per_candidate = 0.0;
    size_t events = 0;
    size_t top1_disagreement = 0;
    double rank_sum = 0.0;
    std::vector<size_t> top_l_hits;
    std::vector<size_t> ranks;

    EstimatorStats(std::string n, double bits, size_t num_top_l)
        : name(std::move(n)),
          approx_code_bits_per_candidate(bits),
          top_l_hits(num_top_l, 0) {
    }

    void add(size_t rank, bool disagree, const std::vector<size_t> &top_l_values) {
        events++;
        rank_sum += static_cast<double>(rank);
        ranks.push_back(rank);
        if (disagree) {
            top1_disagreement++;
        }
        for (size_t i = 0; i < top_l_values.size(); ++i) {
            if (rank <= top_l_values[i]) {
                top_l_hits[i]++;
            }
        }
    }
};

struct CandidateScores {
    PID id = 0;
    PID cluster_id = 0;
    float exact = 0.0f;
    float rabitq_style = 0.0f;
    float symqg_vertex = 0.0f;
    float saq_var = 0.0f;
    float saq_fast = 0.0f;
    float saq_full = 0.0f;
    std::vector<float> saq_prefix;
};

float l2_sqr(const Eigen::Ref<const FloatVec> &a, const Eigen::Ref<const FloatVec> &b) {
    return (a - b).squaredNorm();
}

std::vector<size_t> top_l_values(size_t degree, size_t top_l_max) {
    std::vector<size_t> values;
    for (size_t l = 1; l <= degree && l <= top_l_max; l *= 2) {
        values.push_back(l);
        if (l > std::numeric_limits<size_t>::max() / 2) {
            break;
        }
    }
    if (values.empty() || values.back() != std::min(degree, top_l_max)) {
        values.push_back(std::min(degree, top_l_max));
    }
    values.erase(std::unique(values.begin(), values.end()), values.end());
    return values;
}

double percentile(std::vector<size_t> values, double p) {
    if (values.empty()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    std::sort(values.begin(), values.end());
    const double pos = p * static_cast<double>(values.size() - 1);
    const size_t idx = static_cast<size_t>(std::ceil(pos));
    return static_cast<double>(values[std::min(idx, values.size() - 1)]);
}

std::pair<size_t, size_t> best_and_rank_of_exact_best(
    const std::vector<CandidateScores> &scores,
    const std::vector<float> &estimate,
    size_t exact_best_pos) {
    CHECK_EQ(scores.size(), estimate.size());
    CHECK_LT(exact_best_pos, scores.size());

    size_t best_pos = 0;
    for (size_t i = 1; i < estimate.size(); ++i) {
        if (std::tie(estimate[i], scores[i].id) < std::tie(estimate[best_pos], scores[best_pos].id)) {
            best_pos = i;
        }
    }

    size_t rank = 1;
    for (size_t i = 0; i < estimate.size(); ++i) {
        if (i == exact_best_pos) {
            continue;
        }
        if (std::tie(estimate[i], scores[i].id) <
            std::tie(estimate[exact_best_pos], scores[exact_best_pos].id)) {
            rank++;
        }
    }
    return {best_pos, rank};
}

PathConfig resolve_paths() {
    DataFilePaths paths;
    PathConfig resolved;
    resolved.data_file = FLAGS_graph_data_file.empty() ? paths.data_file : FLAGS_graph_data_file;
    resolved.query_file = FLAGS_graph_query_file.empty() ? paths.query_file : FLAGS_graph_query_file;
    resolved.index_file = FLAGS_graph_index_file.empty() ? paths.quant_file : FLAGS_graph_index_file;

    if (FLAGS_graph_output_prefix.empty()) {
        QuantizeConfig cfg;
        auto args_str = parseArgs(&cfg);
        resolved.output_prefix = fmt::format("{}/graph_frontier_{}_{}", paths.result_path, FLAGS_dataset, args_str);
    } else {
        resolved.output_prefix = FLAGS_graph_output_prefix;
    }
    return resolved;
}

void ensure_parent_dir(const std::string &path) {
    const std::filesystem::path p(path);
    const auto parent = p.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
}

std::vector<ClusterLoc> build_id_to_cluster_local(const IVF &ivf) {
    std::vector<ClusterLoc> id_to_loc(ivf.num_data());
    const auto &clusters = ivf.get_pclusters();
    for (PID cid = 0; cid < clusters.size(); ++cid) {
        const auto &cluster = clusters[cid];
        const PID *ids = cluster.ids();
        for (size_t local = 0; local < cluster.num_vec_; ++local) {
            const PID id = ids[local];
            CHECK_LT(id, id_to_loc.size()) << "cluster contains an out-of-range vector id";
            id_to_loc[id] = ClusterLoc{cid, local, true};
        }
    }
    for (size_t id = 0; id < id_to_loc.size(); ++id) {
        CHECK(id_to_loc[id].valid) << "vector id missing from loaded IVF clusters: " << id;
    }
    return id_to_loc;
}

std::vector<std::vector<PID>> build_exact_subset_adjacency(const FloatRowMat &data, size_t subset, size_t degree) {
    CHECK_GT(subset, 1);
    CHECK_GT(degree, 0);
    CHECK_LT(degree, subset);

    std::vector<std::vector<PID>> adjacency(subset);
    for (size_t u = 0; u < subset; ++u) {
        std::vector<std::pair<float, PID>> distances;
        distances.reserve(subset - 1);
        const FloatVec u_vec = data.row(u);
        for (size_t v = 0; v < subset; ++v) {
            if (u == v) {
                continue;
            }
            const float dist = l2_sqr(u_vec, data.row(v));
            distances.emplace_back(dist, static_cast<PID>(v));
        }
        if (degree < distances.size()) {
            std::nth_element(distances.begin(), distances.begin() + degree, distances.end());
            distances.resize(degree);
        }
        std::sort(distances.begin(), distances.end());

        adjacency[u].reserve(degree);
        for (const auto &[dist, id] : distances) {
            (void)dist;
            adjacency[u].push_back(id);
        }
    }
    return adjacency;
}

std::vector<PID> exact_nearest_subset_roots(const FloatRowMat &data, const FloatVec &query, size_t subset, size_t count) {
    std::vector<std::pair<float, PID>> distances;
    distances.reserve(subset);
    for (size_t id = 0; id < subset; ++id) {
        distances.emplace_back(l2_sqr(query, data.row(id)), static_cast<PID>(id));
    }
    if (count < distances.size()) {
        std::nth_element(distances.begin(), distances.begin() + count, distances.end());
        distances.resize(count);
    }
    std::sort(distances.begin(), distances.end());

    std::vector<PID> roots;
    roots.reserve(distances.size());
    for (const auto &[dist, id] : distances) {
        (void)dist;
        roots.push_back(id);
    }
    return roots;
}

class OneBitStyleProxy {
  private:
    FloatVec center_;
    std::vector<float> centered_norms_;
    size_t num_dim_ = 0;

  public:
    void build(const FloatRowMat &data) {
        num_dim_ = data.cols();
        center_ = data.colwise().mean();
        centered_norms_.resize(data.rows());
        for (size_t i = 0; i < static_cast<size_t>(data.rows()); ++i) {
            centered_norms_[i] = std::sqrt((data.row(i) - center_).squaredNorm());
        }
    }

    float estimate_l2(const FloatRowMat &data, const FloatVec &query, PID id) const {
        CHECK_LT(id, centered_norms_.size());
        const FloatVec q_centered = query - center_;
        const FloatVec x_centered = data.row(id) - center_;
        const float q_l2sqr = q_centered.squaredNorm();
        const float x_norm = centered_norms_[id];
        if (x_norm == 0.0f || num_dim_ == 0) {
            return q_l2sqr;
        }

        double q_dot_sign_x = 0.0;
        for (size_t d = 0; d < num_dim_; ++d) {
            q_dot_sign_x += x_centered[d] >= 0.0f ? q_centered[d] : -q_centered[d];
        }
        const float ip_est = static_cast<float>(x_norm * q_dot_sign_x / std::sqrt(static_cast<double>(num_dim_)));
        return std::max(0.0f, q_l2sqr + x_norm * x_norm - 2.0f * ip_est);
    }
};

class SymphonyQGVertexProxy {
  private:
    static constexpr int kQueryBits = 6;
    size_t num_dim_ = 0;

  public:
    void build(const FloatRowMat &data) {
        num_dim_ = data.cols();
    }

    float approx_bits_per_candidate() const {
        return static_cast<float>(num_dim_);
    }

    float estimate_l2(const FloatRowMat &data, const FloatVec &query, PID root_id, PID neighbor_id) const {
        CHECK_GT(num_dim_, 0);
        const FloatVec center = data.row(root_id);
        const FloatVec residual = data.row(neighbor_id) - center;
        const float residual_norm = std::sqrt(residual.squaredNorm());
        const float q_center_sqr = l2_sqr(query, center);
        if (residual_norm == 0.0f) {
            return q_center_sqr;
        }

        const float fac_norm = 1.0f / std::sqrt(static_cast<float>(num_dim_));
        double residual_l1 = 0.0;
        double center_sign_ip = 0.0;
        double query_code_sign_ip = 0.0;
        int sign_sum = 0;

        float q_lo = query.minCoeff();
        float q_hi = query.maxCoeff();
        const float width = (q_hi - q_lo) / static_cast<float>((1 << kQueryBits) - 1);
        const bool has_query_width = width > 0.0f;

        for (size_t d = 0; d < num_dim_; ++d) {
            const float sign = residual[d] > 0.0f ? 1.0f : -1.0f;
            residual_l1 += std::abs(residual[d]);
            center_sign_ip += center[d] * sign;
            sign_sum += sign > 0.0f ? 1 : -1;

            if (has_query_width) {
                const float raw_code = ((query[d] - q_lo) / width) + 0.5f;
                query_code_sign_ip += static_cast<double>(std::lround(raw_code)) * sign;
            }
        }

        if (residual_l1 == 0.0) {
            return q_center_sqr;
        }

        const double fac_x0 = (residual_l1 * static_cast<double>(fac_norm)) / residual_norm;
        if (fac_x0 == 0.0) {
            return q_center_sqr;
        }

        const double x_x0 = residual_norm / fac_x0;
        const double fac_x1 = center_sign_ip * static_cast<double>(fac_norm);
        const double triple_x = residual_norm * residual_norm + 2.0 * x_x0 * fac_x1;
        const double factor_dq = -2.0 * x_x0 * static_cast<double>(fac_norm);
        const double factor_vq = factor_dq * static_cast<double>(sign_sum);
        const double query_term = has_query_width
                                      ? factor_dq * static_cast<double>(width) * query_code_sign_ip +
                                            factor_vq * static_cast<double>(q_lo)
                                      : 0.0;
        return std::max(0.0, static_cast<double>(q_center_sqr) + triple_x + query_term);
    }
};

double saq_bits_for_prefix(const SaqData &saq_data, size_t accurate_prefix) {
    double bits = 0.0;
    for (size_t i = 0; i < saq_data.quant_plan.size(); ++i) {
        const auto &[dim, seg_bits] = saq_data.quant_plan[i];
        if (seg_bits == 0) {
            continue;
        }
        bits += static_cast<double>(dim) * (i < accurate_prefix ? seg_bits : 1);
    }
    return bits;
}

double saq_full_bits(const SaqData &saq_data) {
    double bits = 0.0;
    for (const auto &[dim, seg_bits] : saq_data.quant_plan) {
        bits += static_cast<double>(dim) * seg_bits;
    }
    return bits;
}

double saq_fast_bits(const SaqData &saq_data) {
    double bits = 0.0;
    for (const auto &[dim, seg_bits] : saq_data.quant_plan) {
        if (seg_bits > 0) {
            bits += static_cast<double>(dim);
        }
    }
    return bits;
}

std::string format_quant_plan(const SaqData &saq_data) {
    std::ostringstream oss;
    size_t offset = 0;
    for (size_t i = 0; i < saq_data.quant_plan.size(); ++i) {
        const auto &[dim, bits] = saq_data.quant_plan[i];
        if (i) {
            oss << " | ";
        }
        oss << offset << "->" << (offset + dim) << " (" << dim << "d " << bits << "b)";
        offset += dim;
    }
    return oss.str();
}

class GraphFrontierProfiler {
  private:
    PathConfig paths_;
    SearcherConfig searcher_cfg_;
    FloatRowMat data_;
    FloatRowMat query_;
    IVF ivf_;
    std::vector<ClusterLoc> id_to_loc_;
    std::vector<std::vector<PID>> adjacency_;
    OneBitStyleProxy one_bit_proxy_;
    SymphonyQGVertexProxy symqg_vertex_proxy_;
    std::vector<size_t> top_l_values_;

    size_t subset_ = 0;
    size_t degree_ = 0;
    size_t max_queries_ = 0;
    size_t roots_per_query_ = 0;
    size_t max_events_ = 0;
    size_t num_segments_ = 0;
    double exact_margin_sum_ = 0.0;
    double distinct_clusters_sum_ = 0.0;
    size_t events_ = 0;

    std::vector<EstimatorStats> stats_;
    std::ofstream event_csv_;

    size_t add_stat(const std::string &name, double bits) {
        stats_.emplace_back(name, bits, top_l_values_.size());
        return stats_.size() - 1;
    }

    void initialize_stats() {
        const SaqData *saq_data = ivf_.get_saq_data();
        CHECK(saq_data);
        num_segments_ = saq_data->quant_plan.size();

        add_stat("exact_float", static_cast<double>(ivf_.num_dim()) * 32.0);
        add_stat("rabitq_style_proxy", static_cast<double>(ivf_.num_dim()));
        add_stat("symqg_vertex_proxy", symqg_vertex_proxy_.approx_bits_per_candidate());
        add_stat("saq_var", 0.0);
        add_stat("saq_fast", saq_fast_bits(*saq_data));
        add_stat("saq_full", saq_full_bits(*saq_data));
        for (size_t prefix = 0; prefix <= num_segments_; ++prefix) {
            add_stat(fmt::format("saq_prefix_acc{}", prefix), saq_bits_for_prefix(*saq_data, prefix));
        }
    }

    std::vector<CandidateScores> score_event(
        const FloatVec &curr_query,
        PID root_id,
        const std::vector<PID> &neighbors,
        SaqCluEstimator<DistType::L2Sqr> &saq_estimator) {
        std::vector<CandidateScores> scores;
        scores.reserve(neighbors.size());

        PID prepared_cluster = std::numeric_limits<PID>::max();
        const auto &clusters = ivf_.get_pclusters();

        for (PID id : neighbors) {
            CHECK_LT(id, id_to_loc_.size());
            const auto loc = id_to_loc_[id];
            CHECK(loc.valid);
            if (prepared_cluster != loc.cluster_id) {
                saq_estimator.prepare(&clusters[loc.cluster_id]);
                prepared_cluster = loc.cluster_id;
            }

            CandidateScores s;
            s.id = id;
            s.cluster_id = loc.cluster_id;
            s.exact = l2_sqr(curr_query, data_.row(id));
            s.rabitq_style = one_bit_proxy_.estimate_l2(data_, curr_query, id);
            s.symqg_vertex = symqg_vertex_proxy_.estimate_l2(data_, curr_query, root_id, id);
            s.saq_var = saq_estimator.varsEstDistSingle(loc.local_idx);
            s.saq_fast = saq_estimator.compFastDistSingle(loc.local_idx);
            s.saq_full = saq_estimator.compAccurateDist(loc.local_idx);

            std::vector<float> seg_fast(num_segments_, 0.0f);
            std::vector<float> seg_full(num_segments_, 0.0f);
            s.saq_prefix.assign(num_segments_ + 1, 0.0f);
            for (size_t seg = 0; seg < num_segments_; ++seg) {
                seg_fast[seg] = saq_estimator.compFastDistSegmentSingle(seg, loc.local_idx);
                seg_full[seg] = saq_estimator.compAccurateDistSegment(seg, loc.local_idx);
                s.saq_prefix[0] += seg_fast[seg];
            }
            for (size_t prefix = 1; prefix <= num_segments_; ++prefix) {
                s.saq_prefix[prefix] = s.saq_prefix[prefix - 1] - seg_fast[prefix - 1] + seg_full[prefix - 1];
            }
            scores.push_back(std::move(s));
        }
        return scores;
    }

    void add_estimator_event(
        size_t stat_idx,
        PID query_id,
        PID root_id,
        const std::vector<CandidateScores> &scores,
        const std::vector<float> &estimate,
        size_t exact_best_pos,
        PID exact_best_id,
        float exact_gap,
        size_t distinct_clusters) {
        auto [best_pos, rank] = best_and_rank_of_exact_best(scores, estimate, exact_best_pos);
        const bool disagree = scores[best_pos].id != exact_best_id;
        stats_[stat_idx].add(rank, disagree, top_l_values_);

        if (event_csv_.is_open()) {
            event_csv_ << query_id << ','
                       << root_id << ','
                       << exact_best_id << ','
                       << exact_gap << ','
                       << scores.size() << ','
                       << distinct_clusters << ','
                       << stats_[stat_idx].name << ','
                       << rank << ','
                       << scores[best_pos].id << ','
                       << (disagree ? 1 : 0) << '\n';
        }
    }

    void add_event(PID query_id, PID root_id, const FloatVec &curr_query, SaqCluEstimator<DistType::L2Sqr> &saq_estimator) {
        const auto &neighbors = adjacency_[root_id];
        CHECK(!neighbors.empty());

        auto scores = score_event(curr_query, root_id, neighbors, saq_estimator);
        size_t exact_best_pos = 0;
        size_t exact_second_pos = scores.size() > 1 ? 1 : 0;
        for (size_t i = 1; i < scores.size(); ++i) {
            if (std::tie(scores[i].exact, scores[i].id) <
                std::tie(scores[exact_best_pos].exact, scores[exact_best_pos].id)) {
                exact_second_pos = exact_best_pos;
                exact_best_pos = i;
            } else if (i != exact_best_pos &&
                       std::tie(scores[i].exact, scores[i].id) <
                           std::tie(scores[exact_second_pos].exact, scores[exact_second_pos].id)) {
                exact_second_pos = i;
            }
        }
        if (exact_second_pos == exact_best_pos && scores.size() > 1) {
            exact_second_pos = exact_best_pos == 0 ? 1 : 0;
        }
        const PID exact_best_id = scores[exact_best_pos].id;
        const float exact_gap = scores.size() > 1
                                    ? scores[exact_second_pos].exact - scores[exact_best_pos].exact
                                    : 0.0f;

        std::unordered_set<PID> clusters;
        clusters.reserve(scores.size());
        for (const auto &s : scores) {
            clusters.insert(s.cluster_id);
        }
        const size_t distinct_clusters = clusters.size();

        exact_margin_sum_ += exact_gap;
        distinct_clusters_sum_ += static_cast<double>(distinct_clusters);
        events_++;

        std::vector<float> estimate(scores.size());

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].exact;
        }
        add_estimator_event(0, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].rabitq_style;
        }
        add_estimator_event(1, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].symqg_vertex;
        }
        add_estimator_event(2, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].saq_var;
        }
        add_estimator_event(3, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].saq_fast;
        }
        add_estimator_event(4, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t i = 0; i < scores.size(); ++i) {
            estimate[i] = scores[i].saq_full;
        }
        add_estimator_event(5, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);

        for (size_t prefix = 0; prefix <= num_segments_; ++prefix) {
            for (size_t i = 0; i < scores.size(); ++i) {
                estimate[i] = scores[i].saq_prefix[prefix];
            }
            add_estimator_event(6 + prefix, query_id, root_id, scores, estimate, exact_best_pos, exact_best_id, exact_gap, distinct_clusters);
        }
    }

    void write_aggregate_csv() const {
        const auto path = paths_.output_prefix + ".csv";
        ensure_parent_dir(path);
        std::ofstream out(path);
        out << "estimator,events,degree,approx_code_bits_per_candidate,top1_disagreement_rate,rank_mean,rank_p50,rank_p90,rank_p99";
        for (const size_t l : top_l_values_) {
            out << ",top" << l << "_containment";
        }
        out << ",avg_exact_margin,avg_distinct_clusters_per_event\n";

        for (const auto &s : stats_) {
            const double events = static_cast<double>(s.events);
            out << s.name << ','
                << s.events << ','
                << degree_ << ','
                << s.approx_code_bits_per_candidate << ','
                << (events ? static_cast<double>(s.top1_disagreement) / events : 0.0) << ','
                << (events ? s.rank_sum / events : 0.0) << ','
                << percentile(s.ranks, 0.50) << ','
                << percentile(s.ranks, 0.90) << ','
                << percentile(s.ranks, 0.99);
            for (size_t i = 0; i < top_l_values_.size(); ++i) {
                out << ',' << (events ? static_cast<double>(s.top_l_hits[i]) / events : 0.0);
            }
            out << ','
                << (events_ ? exact_margin_sum_ / static_cast<double>(events_) : 0.0) << ','
                << (events_ ? distinct_clusters_sum_ / static_cast<double>(events_) : 0.0)
                << '\n';
        }
        std::cout << "Aggregate CSV written to: " << path << '\n';
    }

    void write_summary_md() const {
        const auto path = paths_.output_prefix + ".md";
        ensure_parent_dir(path);
        std::ofstream out(path);

        out << "# Local Neighbor-Order Profiler Summary\n\n";
        out << "## Scope\n\n";
        out << "This provisional diagnostic independently scores fixed query-root\n";
        out << "neighbor sets. It does not execute a frontier or path-dependent graph\n";
        out << "traversal. The SymphonyQG formula-level vertex proxy omits random-sign\n";
        out << "FHT, power-of-two padding, packed FastScan, and multiple-estimate\n";
        out << "behavior, so it is not a source-aligned SymphonyQG baseline.\n\n";

        out << "## Inputs\n\n";
        out << "- data_file: `" << paths_.data_file << "`\n";
        out << "- query_file: `" << paths_.query_file << "`\n";
        out << "- index_file: `" << paths_.index_file << "`\n";
        out << "- subset: " << subset_ << "\n";
        out << "- degree: " << degree_ << "\n";
        out << "- max_queries: " << max_queries_ << "\n";
        out << "- roots_per_query: " << roots_per_query_ << "\n";
        out << "- events: " << events_ << "\n";
        out << "- SAQ quant_plan: `" << format_quant_plan(*ivf_.get_saq_data()) << "`\n";
        out << "- avg_exact_margin: " << (events_ ? exact_margin_sum_ / static_cast<double>(events_) : 0.0) << "\n";
        out << "- avg_distinct_clusters_per_event: "
            << (events_ ? distinct_clusters_sum_ / static_cast<double>(events_) : 0.0) << "\n\n";

        out << "## Aggregate Metrics\n\n";
        out << "| estimator | code_bits_only | top1 disagreement | mean rank | p90 rank |";
        for (const size_t l : top_l_values_) {
            out << " top" << l << " containment |";
        }
        out << "\n|---|---:|---:|---:|---:|";
        for (size_t i = 0; i < top_l_values_.size(); ++i) {
            out << "---:|";
        }
        out << "\n";

        for (const auto &s : stats_) {
            const double events = static_cast<double>(s.events);
            out << "| " << s.name
                << " | " << s.approx_code_bits_per_candidate
                << " | " << (events ? static_cast<double>(s.top1_disagreement) / events : 0.0)
                << " | " << (events ? s.rank_sum / events : 0.0)
                << " | " << percentile(s.ranks, 0.90) << " |";
            for (size_t i = 0; i < top_l_values_.size(); ++i) {
                out << " " << (events ? static_cast<double>(s.top_l_hits[i]) / events : 0.0) << " |";
            }
            out << "\n";
        }

        out << "\n## Interpretation Rule\n\n";
        out << "Continue the graph direction only if the SAQ prefix curve shows a stable\n";
        out << "rank-recovery or work-reduction advantage over `symqg_vertex_proxy`.\n";
        out << "If the strongest result is merely that SAQ can score graph neighbors,\n";
        out << "this profiler should be treated as negative evidence rather than a\n";
        out << "method contribution.\n";

        std::cout << "Summary written to: " << path << '\n';
    }

  public:
    explicit GraphFrontierProfiler(SearcherConfig cfg)
        : paths_(resolve_paths()),
          searcher_cfg_(cfg) {
    }

    void load() {
        CHECK(searcher_cfg_.dist_type == DistType::L2Sqr)
            << "profile_graph_frontier currently supports L2 squared distance only";

        utils::load_something<float, FloatRowMat>(paths_.data_file.c_str(), data_);
        utils::load_something<float, FloatRowMat>(paths_.query_file.c_str(), query_);
        ivf_.load(paths_.index_file.c_str());

        CHECK_EQ(static_cast<size_t>(data_.rows()), ivf_.num_data());
        CHECK_EQ(static_cast<size_t>(data_.cols()), ivf_.num_dim());
        CHECK_EQ(query_.cols(), data_.cols());

        subset_ = std::min(static_cast<size_t>(FLAGS_graph_subset), static_cast<size_t>(data_.rows()));
        degree_ = std::min(static_cast<size_t>(FLAGS_graph_degree), subset_ > 0 ? subset_ - 1 : 0);
        max_queries_ = std::min(static_cast<size_t>(FLAGS_graph_max_queries), static_cast<size_t>(query_.rows()));
        roots_per_query_ = std::min(static_cast<size_t>(FLAGS_graph_roots_per_query), subset_);
        max_events_ = static_cast<size_t>(FLAGS_graph_max_events);

        CHECK_GT(subset_, 1);
        CHECK_GT(degree_, 0);
        CHECK_GT(max_queries_, 0);
        CHECK_GT(roots_per_query_, 0);

        top_l_values_ = top_l_values(degree_, static_cast<size_t>(FLAGS_graph_topl_max));
        id_to_loc_ = build_id_to_cluster_local(ivf_);

        utils::StopW build_timer;
        adjacency_ = build_exact_subset_adjacency(data_, subset_, degree_);
        std::cout << "Exact subset adjacency built in " << build_timer.getElapsedTimeMili() / 1000.0 << "s\n";

        one_bit_proxy_.build(data_);
        symqg_vertex_proxy_.build(data_);
        initialize_stats();

        if (FLAGS_graph_write_event_csv) {
            const auto event_path = paths_.output_prefix + ".events.csv";
            ensure_parent_dir(event_path);
            event_csv_.open(event_path);
            event_csv_ << "query_id,root_id,exact_best_id,exact_gap,degree,distinct_clusters,estimator,rank_exact_best,est_best_id,top1_disagree\n";
            std::cout << "Event CSV will be written to: " << event_path << '\n';
        }
    }

    void run() {
        utils::StopW timer;
        for (PID qid = 0; qid < max_queries_; ++qid) {
            const FloatVec curr_query = query_.row(qid);
            SaqCluEstimator<DistType::L2Sqr> saq_estimator(*ivf_.get_saq_data(), searcher_cfg_, curr_query);
            const auto roots = exact_nearest_subset_roots(data_, curr_query, subset_, roots_per_query_);
            for (PID root : roots) {
                if (max_events_ != 0 && events_ >= max_events_) {
                    break;
                }
                add_event(qid, root, curr_query, saq_estimator);
            }
            if (max_events_ != 0 && events_ >= max_events_) {
                break;
            }
        }
        if (event_csv_.is_open()) {
            event_csv_.close();
        }

        std::cout << "Replay completed in " << timer.getElapsedTimeMili() / 1000.0 << "s\n";
        write_aggregate_csv();
        write_summary_md();
    }
};

SearcherConfig make_searcher_config() {
    SearcherConfig cfg;
    cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;
    cfg.searcher_safe_block_min = FLAGS_searcher_safe_block_min;
    cfg.searcher_safe_block_min_mode = FLAGS_searcher_safe_block_min_mode;
    if (FLAGS_searcher_dist_type == 0) {
        cfg.dist_type = DistType::L2Sqr;
    } else {
        LOG(FATAL) << "profile_graph_frontier currently supports -searcher_dist_type=0 only";
    }
    return cfg;
}

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    QuantizeConfig cfg;
    auto args_str = parseArgs(&cfg);
    LOG(INFO) << args_str << "\n";

    GraphFrontierProfiler profiler(make_searcher_config());
    profiler.load();
    profiler.run();
    return 0;
}

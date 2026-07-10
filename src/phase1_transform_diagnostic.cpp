#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <unistd.h>

#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/config.h"
#include "quantization/saq_data.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/IO.hpp"

using namespace saqlib;

DEFINE_string(base_file, "", "Explicit transformed base fvecs/fbin path.");
DEFINE_string(query_file, "", "Explicit transformed query fvecs/fbin path.");
DEFINE_string(centroids_file, "", "Explicit transformed IVF centroid fvecs/fbin path.");
DEFINE_string(cluster_ids_file, "", "Explicit fixed cluster-id ivecs/bin path.");
DEFINE_string(variance_file, "", "Explicit transformed base-variance fvecs/fbin path.");
DEFINE_string(fixed_probes_file, "", "Explicit query-by-probed-cluster ivecs/bin path.");
DEFINE_string(pca_variance_file, "", "Explicit PCA variance fvecs/fbin path used only to derive the frozen plan.");
DEFINE_string(output_prefix, "", "Output prefix for .query_stages.csv, .segment_errors.csv, and .configs.csv.");
DEFINE_string(transform_label, "", "Stable transform label written to every output row.");
DEFINE_int32(max_queries, 128, "Maximum number of fixed-probe queries to measure.");
DEFINE_int32(topk, 100, "Fixed-candidate top-k used by ranking metrics.");
DEFINE_int32(num_threads, 16, "IVF construction threads.");
DEFINE_double(B, 4.0, "Nominal SAQ average bits per dimension.");
DEFINE_double(vars_bound_m, 4.0, "Variance lower-bound multiplier used by the current SAQ estimator.");
DEFINE_string(plans, "native,frozen-pca,uniform", "Comma-separated plan controls: native,frozen-pca,uniform.");
DEFINE_string(rotation_seeds, "0,1,2,3,4,5,6,7,8,9,off",
              "Comma-separated internal rotation controls: seeds 0..9 and/or off.");

namespace {

using Clock = std::chrono::steady_clock;
using QuantPlan = SaqData::QuantPlanT;

constexpr double kRelativeEpsilon = 1e-12;

double seconds_since(Clock::time_point begin) {
    return std::chrono::duration<double>(Clock::now() - begin).count();
}

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::vector<std::string> split_list(const std::string &value) {
    std::vector<std::string> result;
    std::stringstream input(value);
    std::string token;
    while (std::getline(input, token, ',')) {
        token = trim(token);
        if (!token.empty()) {
            result.push_back(token);
        }
    }
    return result;
}

std::string csv_string(const std::string &value) {
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for (char ch : value) {
        if (ch == '"') {
            escaped.push_back('"');
        }
        escaped.push_back(ch);
    }
    escaped.push_back('"');
    return escaped;
}

std::string plan_string(const QuantPlan &plan) {
    std::string result;
    size_t offset = 0;
    for (size_t i = 0; i < plan.size(); ++i) {
        if (i) {
            result += '|';
        }
        const auto [dim, bits] = plan[i];
        result += fmt::format("{}:{}@{}b", offset, offset + dim, bits);
        offset += dim;
    }
    return result;
}

double quantile_sorted(const std::vector<double> &values, double probability) {
    if (values.empty()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const double position = probability * static_cast<double>(values.size() - 1);
    const size_t lower = static_cast<size_t>(std::floor(position));
    const size_t upper = static_cast<size_t>(std::ceil(position));
    const double weight = position - static_cast<double>(lower);
    return values[lower] * (1.0 - weight) + values[upper] * weight;
}

struct MetricSummary {
    uint64_t total_count = 0;
    uint64_t finite_count = 0;
    uint64_t nonfinite_count = 0;
    double bias = std::numeric_limits<double>::quiet_NaN();
    double mae = std::numeric_limits<double>::quiet_NaN();
    double rmse = std::numeric_limits<double>::quiet_NaN();
    double abs_relative_p50 = std::numeric_limits<double>::quiet_NaN();
    double abs_relative_p90 = std::numeric_limits<double>::quiet_NaN();
    double abs_relative_p99 = std::numeric_limits<double>::quiet_NaN();
};

struct ErrorAccumulator {
    uint64_t total_count = 0;
    uint64_t finite_count = 0;
    uint64_t nonfinite_count = 0;
    long double error_sum = 0;
    long double absolute_error_sum = 0;
    long double squared_error_sum = 0;
    std::vector<double> absolute_relative_errors;

    void add(double exact, double estimate) {
        ++total_count;
        if (!std::isfinite(estimate)) {
            ++nonfinite_count;
            return;
        }
        ++finite_count;
        const double error = estimate - exact;
        error_sum += error;
        absolute_error_sum += std::abs(error);
        squared_error_sum += error * error;
        absolute_relative_errors.push_back(std::abs(error) / std::max(std::abs(exact), kRelativeEpsilon));
    }

    MetricSummary finish() {
        MetricSummary result;
        result.total_count = total_count;
        result.finite_count = finite_count;
        result.nonfinite_count = nonfinite_count;
        if (finite_count == 0) {
            return result;
        }
        const double denominator = static_cast<double>(finite_count);
        result.bias = static_cast<double>(error_sum / denominator);
        result.mae = static_cast<double>(absolute_error_sum / denominator);
        result.rmse = std::sqrt(static_cast<double>(squared_error_sum / denominator));
        std::sort(absolute_relative_errors.begin(), absolute_relative_errors.end());
        result.abs_relative_p50 = quantile_sorted(absolute_relative_errors, 0.50);
        result.abs_relative_p90 = quantile_sorted(absolute_relative_errors, 0.90);
        result.abs_relative_p99 = quantile_sorted(absolute_relative_errors, 0.99);
        return result;
    }
};

struct ResidualIpAccumulator {
    uint64_t count = 0;
    long double true_ip_sum = 0;
    long double true_ip_absolute_sum = 0;
    long double true_ip_squared_sum = 0;
    long double implied_ip_absolute_error_sum = 0;
    long double implied_ip_squared_error_sum = 0;

    void add(double true_ip, double implied_ip) {
        ++count;
        const double error = implied_ip - true_ip;
        true_ip_sum += true_ip;
        true_ip_absolute_sum += std::abs(true_ip);
        true_ip_squared_sum += true_ip * true_ip;
        implied_ip_absolute_error_sum += std::abs(error);
        implied_ip_squared_error_sum += error * error;
    }
};

enum class StageKind {
    VarsLowerBound,
    FastPrefix,
    AccuratePrefix,
};

struct StageSpec {
    std::string label;
    StageKind kind;
    size_t prefix_segments = 0;
    size_t logical_factor_bytes = 0;
    size_t logical_fast_code_bytes = 0;
    size_t logical_long_code_bytes = 0;
    size_t logical_long_factor_bytes = 0;

    size_t logical_total_bytes() const {
        return logical_factor_bytes + logical_fast_code_bytes + logical_long_code_bytes + logical_long_factor_bytes;
    }
};

struct SegmentDescriptor {
    size_t index = 0;
    size_t offset = 0;
    size_t dimensions = 0;
    size_t bits = 0;
    double transform_variance_sum = 0;
    double pca_variance_sum = 0;
    double transform_proxy = 0;
    double pca_proxy = 0;
};

double variance_sum(const FloatVec &variance, size_t offset, size_t dimensions) {
    if (offset >= static_cast<size_t>(variance.cols())) {
        return 0;
    }
    const size_t available = static_cast<size_t>(variance.cols()) - offset;
    const size_t length = std::min(dimensions, available);
    return static_cast<double>(variance.segment(offset, length).sum());
}

std::vector<SegmentDescriptor> describe_segments(
    const QuantPlan &plan, const FloatVec &transform_variance, const FloatVec &pca_variance) {
    std::vector<SegmentDescriptor> result;
    result.reserve(plan.size());
    size_t offset = 0;
    for (size_t i = 0; i < plan.size(); ++i) {
        const auto [dimensions, bits] = plan[i];
        SegmentDescriptor descriptor;
        descriptor.index = i;
        descriptor.offset = offset;
        descriptor.dimensions = dimensions;
        descriptor.bits = bits;
        descriptor.transform_variance_sum = variance_sum(transform_variance, offset, dimensions);
        descriptor.pca_variance_sum = variance_sum(pca_variance, offset, dimensions);
        const double divisor = std::ldexp(1.0, static_cast<int>(bits));
        descriptor.transform_proxy = descriptor.transform_variance_sum / divisor;
        descriptor.pca_proxy = descriptor.pca_variance_sum / divisor;
        result.push_back(descriptor);
        offset += dimensions;
    }
    return result;
}

std::vector<StageSpec> make_stages(const QuantPlan &plan) {
    const size_t factor_bytes_all = plan.size() * sizeof(float);
    auto fast_bytes_through = [&](size_t prefix) {
        size_t bytes = 0;
        for (size_t i = 0; i < prefix; ++i) {
            if (plan[i].second > 0) {
                bytes += plan[i].first / 8;
            }
        }
        return bytes;
    };
    auto long_bytes_through = [&](size_t prefix) {
        size_t bytes = 0;
        for (size_t i = 0; i < prefix; ++i) {
            const auto [dimensions, bits] = plan[i];
            if (bits > 0) {
                bytes += dimensions * (bits - 1) / 8;
            }
        }
        return bytes;
    };
    auto long_factor_bytes_through = [&](size_t prefix) {
        size_t bytes = 0;
        for (size_t i = 0; i < prefix; ++i) {
            if (plan[i].second > 0) {
                bytes += sizeof(ExFactor);
            }
        }
        return bytes;
    };

    std::vector<StageSpec> result;
    result.push_back({"vars_conservative_lower_bound_all", StageKind::VarsLowerBound, 0,
                      factor_bytes_all, 0, 0, 0});
    for (size_t prefix = 1; prefix <= plan.size(); ++prefix) {
        const std::string label = prefix == plan.size()
                                      ? "fast_all"
                                      : fmt::format("fast_prefix_{}", prefix);
        result.push_back({label, StageKind::FastPrefix, prefix, factor_bytes_all,
                          fast_bytes_through(prefix), 0, 0});
    }
    const size_t fast_bytes_all = fast_bytes_through(plan.size());
    for (size_t prefix = 1; prefix <= plan.size(); ++prefix) {
        const std::string label = prefix == plan.size()
                                      ? "full"
                                      : fmt::format("accurate_prefix_{}", prefix);
        result.push_back({label, StageKind::AccuratePrefix, prefix, factor_bytes_all,
                          fast_bytes_all, long_bytes_through(prefix), long_factor_bytes_through(prefix)});
    }
    return result;
}

double compose_stage(const StageSpec &stage, const std::vector<float> &vars,
                     const std::vector<float> &fast, const std::vector<float> &accurate) {
    double estimate = 0;
    for (size_t i = 0; i < vars.size(); ++i) {
        switch (stage.kind) {
        case StageKind::VarsLowerBound:
            estimate += vars[i];
            break;
        case StageKind::FastPrefix:
            estimate += i < stage.prefix_segments ? fast[i] : vars[i];
            break;
        case StageKind::AccuratePrefix:
            estimate += i < stage.prefix_segments ? accurate[i] : fast[i];
            break;
        }
    }
    return estimate;
}

struct RotationControl {
    bool enabled = false;
    int seed = -1;
    std::string label;
};

std::vector<RotationControl> parse_rotations() {
    std::vector<RotationControl> result;
    std::set<std::string> seen;
    for (const auto &token : split_list(FLAGS_rotation_seeds)) {
        if (token == "off") {
            if (seen.insert(token).second) {
                result.push_back({false, -1, "off"});
            }
            continue;
        }
        size_t parsed = 0;
        int seed = 0;
        try {
            seed = std::stoi(token, &parsed);
        } catch (const std::exception &) {
            LOG(FATAL) << "invalid rotation control: " << token;
        }
        CHECK_EQ(parsed, token.size()) << "invalid rotation seed: " << token;
        CHECK_GE(seed, 0);
        CHECK_LE(seed, 9) << "Phase-1 rotation seeds are predeclared as 0..9";
        const std::string label = fmt::format("seed{}", seed);
        if (seen.insert(label).second) {
            result.push_back({true, seed, label});
        }
    }
    CHECK(!result.empty()) << "at least one rotation control is required";
    return result;
}

enum class PlanKind {
    Native,
    FrozenPca,
    Uniform,
};

struct PlanControl {
    PlanKind kind;
    std::string label;
    std::optional<QuantPlan> custom_plan;
};

QuantizeConfig base_quantize_config(bool random_rotation) {
    QuantizeConfig config;
    config.avg_bits = static_cast<float>(FLAGS_B);
    config.enable_segmentation = true;
    config.single.quant_type = BaseQuantType::CAQ;
    config.single.random_rotation = random_rotation;
    return config;
}

QuantPlan derive_native_plan(const FloatVec &variance, size_t dimension) {
    QuantizeConfig config = base_quantize_config(false);
    SaqDataMaker maker(config, dimension);
    maker.set_variance(variance);
    return maker.get_data()->quant_plan;
}

std::vector<PlanControl> parse_plans(const QuantPlan &frozen_pca_plan, size_t padded_dimension) {
    const double rounded_bits = std::round(FLAGS_B);
    CHECK_LE(std::abs(FLAGS_B - rounded_bits), 1e-6)
        << "the uniform control requires an integral B";
    CHECK_GE(rounded_bits, 0);
    CHECK_LE(rounded_bits, static_cast<double>(KMaxQuantizeBits));
    const QuantPlan uniform_plan{{padded_dimension, static_cast<size_t>(rounded_bits)}};

    std::vector<PlanControl> result;
    std::set<std::string> seen;
    for (std::string token : split_list(FLAGS_plans)) {
        std::replace(token.begin(), token.end(), '_', '-');
        if (!seen.insert(token).second) {
            continue;
        }
        if (token == "native") {
            result.push_back({PlanKind::Native, token, std::nullopt});
        } else if (token == "frozen-pca") {
            result.push_back({PlanKind::FrozenPca, token, frozen_pca_plan});
        } else if (token == "uniform") {
            result.push_back({PlanKind::Uniform, token, uniform_plan});
        } else {
            LOG(FATAL) << "unknown plan control: " << token;
        }
    }
    CHECK(!result.empty()) << "at least one plan control is required";
    return result;
}

double ranking_value(double value) {
    return std::isfinite(value) ? value : std::numeric_limits<double>::infinity();
}

struct RankingSummary {
    size_t topk_used = 0;
    double topk_agreement = std::numeric_limits<double>::quiet_NaN();
    size_t exact_best_estimated_rank = 0;
    uint64_t boundary_inversions = 0;
    uint64_t boundary_pairs = 0;
    double boundary_inversion_rate = std::numeric_limits<double>::quiet_NaN();
};

RankingSummary ranking_summary(const std::vector<double> &exact, const std::vector<double> &estimate,
                               const std::vector<PID> &ids, size_t requested_topk) {
    CHECK_EQ(exact.size(), estimate.size());
    CHECK_EQ(exact.size(), ids.size());
    RankingSummary result;
    if (exact.empty()) {
        return result;
    }

    std::vector<size_t> exact_order(exact.size());
    std::iota(exact_order.begin(), exact_order.end(), 0);
    std::sort(exact_order.begin(), exact_order.end(), [&](size_t lhs, size_t rhs) {
        if (exact[lhs] != exact[rhs]) {
            return exact[lhs] < exact[rhs];
        }
        return ids[lhs] < ids[rhs];
    });

    std::vector<size_t> estimated_order(exact.size());
    std::iota(estimated_order.begin(), estimated_order.end(), 0);
    std::sort(estimated_order.begin(), estimated_order.end(), [&](size_t lhs, size_t rhs) {
        const double lhs_value = ranking_value(estimate[lhs]);
        const double rhs_value = ranking_value(estimate[rhs]);
        if (lhs_value != rhs_value) {
            return lhs_value < rhs_value;
        }
        return ids[lhs] < ids[rhs];
    });

    const size_t topk = std::min(requested_topk, exact.size());
    result.topk_used = topk;
    std::vector<char> is_exact_topk(exact.size(), false);
    for (size_t i = 0; i < topk; ++i) {
        is_exact_topk[exact_order[i]] = true;
    }
    size_t overlap = 0;
    for (size_t i = 0; i < topk; ++i) {
        overlap += is_exact_topk[estimated_order[i]] ? 1 : 0;
    }
    result.topk_agreement = static_cast<double>(overlap) / static_cast<double>(topk);

    const size_t exact_best = exact_order.front();
    const auto best_position = std::find(estimated_order.begin(), estimated_order.end(), exact_best);
    result.exact_best_estimated_rank = static_cast<size_t>(best_position - estimated_order.begin()) + 1;

    if (topk < exact.size()) {
        std::vector<double> outside_estimates;
        outside_estimates.reserve(exact.size() - topk);
        for (size_t i = topk; i < exact.size(); ++i) {
            outside_estimates.push_back(ranking_value(estimate[exact_order[i]]));
        }
        std::sort(outside_estimates.begin(), outside_estimates.end());
        for (size_t i = 0; i < topk; ++i) {
            const double top_estimate = ranking_value(estimate[exact_order[i]]);
            result.boundary_inversions += static_cast<uint64_t>(
                std::lower_bound(outside_estimates.begin(), outside_estimates.end(), top_estimate) -
                outside_estimates.begin());
        }
        result.boundary_pairs = static_cast<uint64_t>(topk) * static_cast<uint64_t>(exact.size() - topk);
        result.boundary_inversion_rate = static_cast<double>(result.boundary_inversions) /
                                         static_cast<double>(result.boundary_pairs);
    } else {
        result.boundary_inversion_rate = 0;
    }
    return result;
}

void write_metric_columns(std::ofstream &output, const MetricSummary &summary) {
    output << summary.total_count << ',' << summary.finite_count << ',' << summary.nonfinite_count << ','
           << summary.bias << ',' << summary.mae << ',' << summary.rmse << ','
           << summary.abs_relative_p50 << ',' << summary.abs_relative_p90 << ','
           << summary.abs_relative_p99;
}

struct SegmentMeasurements {
    std::array<ErrorAccumulator, 3> distance_errors;
    ResidualIpAccumulator residual_ip;
};

struct LoadedView {
    FloatRowMat base;
    FloatRowMat queries;
    FloatRowMat centroids;
    UintRowMat cluster_ids;
    FloatVec variance;
    FloatVec pca_variance;
    UintRowMat fixed_probes;
};

FloatVec load_single_vector(const std::string &path, const char *label) {
    FloatRowMat matrix;
    utils::load_something<float, FloatRowMat>(path.c_str(), matrix);
    CHECK_EQ(matrix.rows(), 1) << label << " must contain exactly one row";
    return matrix.row(0);
}

LoadedView load_view() {
    LoadedView view;
    utils::load_something<float, FloatRowMat>(FLAGS_base_file.c_str(), view.base);
    utils::load_something<float, FloatRowMat>(FLAGS_query_file.c_str(), view.queries);
    utils::load_something<float, FloatRowMat>(FLAGS_centroids_file.c_str(), view.centroids);
    utils::load_something<PID, UintRowMat>(FLAGS_cluster_ids_file.c_str(), view.cluster_ids);
    view.variance = load_single_vector(FLAGS_variance_file, "transform variance");
    view.pca_variance = load_single_vector(FLAGS_pca_variance_file, "PCA variance");
    utils::load_something<PID, UintRowMat>(FLAGS_fixed_probes_file.c_str(), view.fixed_probes);

    CHECK_GT(view.base.rows(), 0);
    CHECK_GT(view.base.cols(), 0);
    CHECK_EQ(view.queries.cols(), view.base.cols());
    CHECK_EQ(view.centroids.cols(), view.base.cols());
    CHECK_EQ(view.cluster_ids.rows(), view.base.rows());
    CHECK_EQ(view.cluster_ids.cols(), 1);
    CHECK_EQ(view.variance.cols(), view.base.cols());
    CHECK_EQ(view.pca_variance.cols(), view.base.cols());
    CHECK_GT(view.fixed_probes.rows(), 0);
    CHECK_GT(view.fixed_probes.cols(), 0);
    for (Eigen::Index i = 0; i < view.cluster_ids.rows(); ++i) {
        CHECK_LT(view.cluster_ids(i, 0), static_cast<PID>(view.centroids.rows()));
    }
    for (Eigen::Index row = 0; row < view.fixed_probes.rows(); ++row) {
        for (Eigen::Index col = 0; col < view.fixed_probes.cols(); ++col) {
            CHECK_LT(view.fixed_probes(row, col), static_cast<PID>(view.centroids.rows()));
        }
    }
    return view;
}

size_t query_count(const LoadedView &view) {
    CHECK_GT(FLAGS_max_queries, 0);
    size_t count = std::min(static_cast<size_t>(FLAGS_max_queries), static_cast<size_t>(view.queries.rows()));
    if (view.fixed_probes.rows() != 1) {
        count = std::min(count, static_cast<size_t>(view.fixed_probes.rows()));
    }
    return count;
}

std::vector<PID> probes_for_query(const LoadedView &view, size_t query_index) {
    const size_t row = view.fixed_probes.rows() == 1 ? 0 : query_index;
    std::vector<PID> probes;
    probes.reserve(view.fixed_probes.cols());
    std::unordered_set<PID> seen;
    for (Eigen::Index col = 0; col < view.fixed_probes.cols(); ++col) {
        const PID cluster = view.fixed_probes(row, col);
        if (seen.insert(cluster).second) {
            probes.push_back(cluster);
        }
    }
    return probes;
}

void validate_required_flags() {
    const std::array<std::pair<const std::string *, const char *>, 9> required{{
        {&FLAGS_base_file, "base_file"},
        {&FLAGS_query_file, "query_file"},
        {&FLAGS_centroids_file, "centroids_file"},
        {&FLAGS_cluster_ids_file, "cluster_ids_file"},
        {&FLAGS_variance_file, "variance_file"},
        {&FLAGS_fixed_probes_file, "fixed_probes_file"},
        {&FLAGS_pca_variance_file, "pca_variance_file"},
        {&FLAGS_output_prefix, "output_prefix"},
        {&FLAGS_transform_label, "transform_label"},
    }};
    for (const auto &[value, name] : required) {
        CHECK(!value->empty()) << '-' << name << " is required";
    }
    CHECK_GT(FLAGS_topk, 0);
    CHECK_GT(FLAGS_num_threads, 0);
    CHECK_GT(FLAGS_B, 0);
    CHECK_GE(FLAGS_vars_bound_m, 0);
}

} // namespace

int main(int argc, char **argv) {
    google::InitGoogleLogging(argv[0]);
    gflags::ParseCommandLineFlags(&argc, &argv, true);
    validate_required_flags();

    LoadedView view = load_view();
    const size_t dimension = static_cast<size_t>(view.base.cols());
    const size_t padded_dimension = ((dimension + kDimPaddingSize - 1) / kDimPaddingSize) * kDimPaddingSize;
    const size_t queries_to_measure = query_count(view);
    const QuantPlan frozen_pca_plan = derive_native_plan(view.pca_variance, dimension);
    const auto plan_controls = parse_plans(frozen_pca_plan, padded_dimension);
    const auto rotation_controls = parse_rotations();

    const std::filesystem::path prefix(FLAGS_output_prefix);
    const std::filesystem::path output_directory = prefix.parent_path().empty() ? "." : prefix.parent_path();
    std::filesystem::create_directories(output_directory);
    std::ofstream query_output(FLAGS_output_prefix + ".query_stages.csv", std::ios::trunc);
    std::ofstream segment_output(FLAGS_output_prefix + ".segment_errors.csv", std::ios::trunc);
    std::ofstream config_output(FLAGS_output_prefix + ".configs.csv", std::ios::trunc);
    CHECK(query_output.is_open());
    CHECK(segment_output.is_open());
    CHECK(config_output.is_open());
    query_output << std::setprecision(10);
    segment_output << std::setprecision(10);
    config_output << std::setprecision(10);

    query_output
        << "transform,config_id,plan_control,rotation_control,rotation_seed,query,stage,stage_semantics,"
           "candidate_count,finite_count,nonfinite_count,bias,mae,rmse,abs_relative_eps1e-12_p50,"
           "abs_relative_eps1e-12_p90,abs_relative_eps1e-12_p99,topk_used,fixed_candidate_topk_agreement,"
           "exact_best_estimated_rank,strict_exact_topk_vs_outside_boundary_inversions,boundary_pairs,"
           "strict_boundary_inversion_rate,logical_factor_bytes_per_candidate,logical_fast_code_bytes_per_candidate,"
           "logical_long_code_bytes_per_candidate,logical_long_factor_bytes_per_candidate,"
           "logical_total_requested_bytes_per_candidate,logical_byte_model\n";
    segment_output
        << "transform,config_id,plan_control,rotation_control,rotation_seed,segment,offset,dimensions,bits,"
           "distance_mode,mode_semantics,total_count,finite_count,nonfinite_count,bias,mae,rmse,"
           "abs_relative_eps1e-12_p50,abs_relative_eps1e-12_p90,abs_relative_eps1e-12_p99,"
           "transform_variance_sum,pca_variance_sum,transform_planner_proxy,pca_planner_proxy,"
           "true_residual_ip_mean,true_residual_ip_abs_mean,true_residual_ip_sq_mean,"
           "accurate_distance_implied_ip_abs_error_mean,accurate_distance_implied_ip_sq_error_mean\n";
    config_output
        << "transform,config_id,plan_control,rotation_control,rotation_enabled,rotation_seed,seed_scope,"
           "N,D,K,queries,fixed_probes_per_query,topk_requested,nominal_B,vars_bound_m,segments,plan,"
           "nominal_code_bits_per_vector,transform_planner_proxy_total,pca_planner_proxy_total,"
           "actual_serialized_index_bytes,actual_serialized_index_bytes_per_vector,build_time_s,"
           "serialization_time_s,measurement_time_s,candidate_evaluations,exact_distance_scope\n";

    for (const auto &plan_control : plan_controls) {
        for (const auto &rotation : rotation_controls) {
            // Eigen::Random, used by Rotator, follows the C RNG.  glibc aliases
            // srand(0) and srand(1), so map the predeclared logical seeds 0..9
            // to distinct C RNG seeds 1..10 before constructing SaqDataMaker.
            const unsigned int c_rng_seed = rotation.enabled
                                                ? static_cast<unsigned int>(rotation.seed) + 1U
                                                : 0U;
            std::srand(c_rng_seed);
            QuantizeConfig quantize_config = base_quantize_config(rotation.enabled);
            const std::string config_id = fmt::format("{}__{}__{}", FLAGS_transform_label,
                                                       plan_control.label, rotation.label);

            const auto build_begin = Clock::now();
            auto ivf = std::make_unique<IVF>(view.base.rows(), dimension, view.centroids.rows(), quantize_config);
            if (plan_control.custom_plan) {
                ivf->set_custom_quant_plan(*plan_control.custom_plan);
            }
            ivf->set_variance(view.variance);
            ivf->construct(view.base, view.centroids, view.cluster_ids.data(), FLAGS_num_threads);
            const double build_time = seconds_since(build_begin);

            const QuantPlan plan = ivf->get_saq_data()->quant_plan;
            const auto segment_descriptors = describe_segments(plan, view.variance, view.pca_variance);
            const auto stages = make_stages(plan);
            std::vector<SegmentMeasurements> segment_measurements(plan.size());

            const std::filesystem::path temporary_index = output_directory /
                fmt::format(".phase1_transform_diagnostic_{}_{}.tmp.index", getpid(), config_id);
            const auto serialization_begin = Clock::now();
            ivf->save(temporary_index.string().c_str());
            const uintmax_t serialized_bytes = std::filesystem::file_size(temporary_index);
            const double serialization_time = seconds_since(serialization_begin);
            std::error_code remove_error;
            std::filesystem::remove(temporary_index, remove_error);
            CHECK(!remove_error) << "failed to remove temporary index " << temporary_index << ": "
                                 << remove_error.message();

            SearcherConfig searcher_config;
            searcher_config.dist_type = DistType::L2Sqr;
            searcher_config.searcher_vars_bound_m = static_cast<float>(FLAGS_vars_bound_m);
            uint64_t candidate_evaluations = 0;
            const auto measurement_begin = Clock::now();
            const auto &clusters = ivf->get_pclusters();
            for (size_t query_index = 0; query_index < queries_to_measure; ++query_index) {
                const FloatVec query = view.queries.row(query_index);
                SaqCluEstimator<DistType::L2Sqr> estimator(*ivf->get_saq_data(), searcher_config, query);
                const auto probes = probes_for_query(view, query_index);
                size_t candidate_reserve = 0;
                for (PID cluster_id : probes) {
                    candidate_reserve += clusters[cluster_id].num_vec_;
                }
                std::vector<PID> candidate_ids;
                std::vector<double> exact_distances;
                std::vector<std::vector<double>> stage_estimates(stages.size());
                candidate_ids.reserve(candidate_reserve);
                exact_distances.reserve(candidate_reserve);
                for (auto &values : stage_estimates) {
                    values.reserve(candidate_reserve);
                }

                for (PID cluster_id : probes) {
                    const SaqCluData &cluster = clusters[cluster_id];
                    estimator.prepare(&cluster);
                    auto &segment_estimators = estimator.getEstimators();
                    CHECK_EQ(segment_estimators.size(), plan.size());
                    for (size_t block_index = 0; block_index < cluster.num_blocks_; ++block_index) {
                        std::vector<std::array<float, KFastScanSize>> vars_block(plan.size());
                        std::vector<std::array<float, KFastScanSize>> fast_block(plan.size());
                        for (size_t segment_index = 0; segment_index < plan.size(); ++segment_index) {
                            __m512 lanes[2];
                            segment_estimators[segment_index].varsEstDist(block_index, lanes);
                            _mm512_storeu_ps(vars_block[segment_index].data(), lanes[0]);
                            _mm512_storeu_ps(vars_block[segment_index].data() + 16, lanes[1]);

                            // Accurate decoding reuses the LUT state and the
                            // block's fast-code preparation. Populate fast for
                            // every segment before any accurate value in this block.
                            segment_estimators[segment_index].compFastDist(block_index, lanes);
                            _mm512_storeu_ps(fast_block[segment_index].data(), lanes[0]);
                            _mm512_storeu_ps(fast_block[segment_index].data() + 16, lanes[1]);
                        }

                        const size_t local_begin = block_index * KFastScanSize;
                        const size_t local_end = std::min(local_begin + KFastScanSize, cluster.num_vec_);
                        for (size_t local_index = local_begin; local_index < local_end; ++local_index) {
                            const size_t lane = local_index - local_begin;
                            const PID data_id = cluster.ids()[local_index];
                            CHECK_LT(data_id, static_cast<PID>(view.base.rows()));
                            std::vector<float> vars(plan.size());
                            std::vector<float> fast(plan.size());
                            std::vector<float> accurate(plan.size());
                            double exact_distance = 0;

                            for (size_t segment_index = 0; segment_index < plan.size(); ++segment_index) {
                                const auto &descriptor = segment_descriptors[segment_index];
                                const size_t actual_dimensions = descriptor.offset >= dimension
                                                                     ? 0
                                                                     : std::min(descriptor.dimensions,
                                                                                dimension - descriptor.offset);
                                double exact_segment_distance = 0;
                                double query_residual_norm_sq = 0;
                                double data_residual_norm_sq = 0;
                                double true_residual_ip = 0;
                                if (actual_dimensions > 0) {
                                    const auto query_segment = query.segment(descriptor.offset, actual_dimensions);
                                    const auto data_segment = view.base.row(data_id).segment(
                                        descriptor.offset, actual_dimensions);
                                    const auto centroid_segment = view.centroids.row(cluster_id).segment(
                                        descriptor.offset, actual_dimensions);
                                    exact_segment_distance = (query_segment - data_segment).squaredNorm();
                                    const auto query_residual = query_segment - centroid_segment;
                                    const auto data_residual = data_segment - centroid_segment;
                                    query_residual_norm_sq = query_residual.squaredNorm();
                                    data_residual_norm_sq = data_residual.squaredNorm();
                                    true_residual_ip = query_residual.dot(data_residual);
                                }
                                exact_distance += exact_segment_distance;

                                vars[segment_index] = vars_block[segment_index][lane];
                                fast[segment_index] = fast_block[segment_index][lane];
                                accurate[segment_index] =
                                    segment_estimators[segment_index].compAccurateDist(local_index);

                                segment_measurements[segment_index].distance_errors[0].add(
                                    exact_segment_distance, vars[segment_index]);
                                segment_measurements[segment_index].distance_errors[1].add(
                                    exact_segment_distance, fast[segment_index]);
                                segment_measurements[segment_index].distance_errors[2].add(
                                    exact_segment_distance, accurate[segment_index]);
                                const double implied_ip = (query_residual_norm_sq + data_residual_norm_sq -
                                                           accurate[segment_index]) /
                                                          2.0;
                                segment_measurements[segment_index].residual_ip.add(true_residual_ip, implied_ip);
                            }

                            candidate_ids.push_back(data_id);
                            exact_distances.push_back(exact_distance);
                            for (size_t stage_index = 0; stage_index < stages.size(); ++stage_index) {
                                stage_estimates[stage_index].push_back(
                                    compose_stage(stages[stage_index], vars, fast, accurate));
                            }
                        }
                    }
                }
                CHECK(!candidate_ids.empty()) << "query " << query_index << " has no fixed-probe candidates";
                candidate_evaluations += candidate_ids.size();

                for (size_t stage_index = 0; stage_index < stages.size(); ++stage_index) {
                    ErrorAccumulator errors;
                    for (size_t candidate = 0; candidate < exact_distances.size(); ++candidate) {
                        errors.add(exact_distances[candidate], stage_estimates[stage_index][candidate]);
                    }
                    const MetricSummary metrics = errors.finish();
                    const RankingSummary ranking = ranking_summary(
                        exact_distances, stage_estimates[stage_index], candidate_ids,
                        static_cast<size_t>(FLAGS_topk));
                    const auto &stage = stages[stage_index];
                    query_output << csv_string(FLAGS_transform_label) << ',' << csv_string(config_id) << ','
                                 << plan_control.label << ',' << rotation.label << ',' << rotation.seed << ','
                                 << query_index << ',' << stage.label << ','
                                 << (stage.kind == StageKind::VarsLowerBound
                                         ? "conservative_lower_bound_not_ordinary_distance_estimator"
                                         : "progressive_distance_estimate")
                                 << ',';
                    write_metric_columns(query_output, metrics);
                    query_output << ',' << ranking.topk_used << ',' << ranking.topk_agreement << ','
                                 << ranking.exact_best_estimated_rank << ',' << ranking.boundary_inversions << ','
                                 << ranking.boundary_pairs << ',' << ranking.boundary_inversion_rate << ','
                                 << stage.logical_factor_bytes << ',' << stage.logical_fast_code_bytes << ','
                                 << stage.logical_long_code_bytes << ',' << stage.logical_long_factor_bytes << ','
                                 << stage.logical_total_bytes() << ','
                                 << "cumulative_staged_reuse_excludes_query_centroid_and_lut_bytes\n";
                }
            }
            const double measurement_time = seconds_since(measurement_begin);

            const std::array<const char *, 3> mode_labels{{
                "vars_conservative_lower_bound", "fast_1bit", "accurate_full_code"}};
            const std::array<const char *, 3> mode_semantics{{
                "conservative_lower_bound_not_ordinary_distance_estimator",
                "one_bit_distance_estimate", "full_code_distance_estimate"}};
            for (size_t segment_index = 0; segment_index < plan.size(); ++segment_index) {
                const auto &descriptor = segment_descriptors[segment_index];
                const auto &ip = segment_measurements[segment_index].residual_ip;
                const double ip_denominator = static_cast<double>(ip.count);
                for (size_t mode = 0; mode < mode_labels.size(); ++mode) {
                    const MetricSummary metrics = segment_measurements[segment_index].distance_errors[mode].finish();
                    segment_output << csv_string(FLAGS_transform_label) << ',' << csv_string(config_id) << ','
                                   << plan_control.label << ',' << rotation.label << ',' << rotation.seed << ','
                                   << descriptor.index << ',' << descriptor.offset << ',' << descriptor.dimensions << ','
                                   << descriptor.bits << ',' << mode_labels[mode] << ',' << mode_semantics[mode] << ',';
                    write_metric_columns(segment_output, metrics);
                    segment_output << ',' << descriptor.transform_variance_sum << ','
                                   << descriptor.pca_variance_sum << ',' << descriptor.transform_proxy << ','
                                   << descriptor.pca_proxy << ','
                                   << static_cast<double>(ip.true_ip_sum / ip_denominator) << ','
                                   << static_cast<double>(ip.true_ip_absolute_sum / ip_denominator) << ','
                                   << static_cast<double>(ip.true_ip_squared_sum / ip_denominator) << ','
                                   << static_cast<double>(ip.implied_ip_absolute_error_sum / ip_denominator) << ','
                                   << static_cast<double>(ip.implied_ip_squared_error_sum / ip_denominator) << '\n';
                }
            }

            const uint64_t nominal_code_bits = std::accumulate(
                plan.begin(), plan.end(), uint64_t{0}, [](uint64_t sum, const auto &segment) {
                    return sum + segment.first * segment.second;
                });
            const double transform_proxy_total = std::accumulate(
                segment_descriptors.begin(), segment_descriptors.end(), 0.0,
                [](double sum, const auto &segment) { return sum + segment.transform_proxy; });
            const double pca_proxy_total = std::accumulate(
                segment_descriptors.begin(), segment_descriptors.end(), 0.0,
                [](double sum, const auto &segment) { return sum + segment.pca_proxy; });
            config_output << csv_string(FLAGS_transform_label) << ',' << csv_string(config_id) << ','
                          << plan_control.label << ',' << rotation.label << ',' << (rotation.enabled ? 1 : 0) << ','
                          << rotation.seed << ','
                          << "logical_seed_0_9_maps_to_c_rng_seed_1_10_not_cross_plan_matrix_identity" << ','
                          << view.base.rows() << ',' << dimension << ',' << view.centroids.rows() << ','
                          << queries_to_measure << ',' << view.fixed_probes.cols() << ',' << FLAGS_topk << ','
                          << FLAGS_B << ',' << FLAGS_vars_bound_m << ',' << plan.size() << ','
                          << csv_string(plan_string(plan)) << ',' << nominal_code_bits << ','
                          << transform_proxy_total << ',' << pca_proxy_total << ',' << serialized_bytes << ','
                          << static_cast<double>(serialized_bytes) / static_cast<double>(view.base.rows()) << ','
                          << build_time << ',' << serialization_time << ',' << measurement_time << ','
                          << candidate_evaluations << ',' << "transform_view_squared_L2" << '\n';
            query_output.flush();
            segment_output.flush();
            config_output.flush();
            LOG(INFO) << "completed " << config_id << " plan=" << plan_string(plan)
                      << " bytes=" << serialized_bytes;
        }
    }

    return 0;
}

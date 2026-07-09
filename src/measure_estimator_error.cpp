#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "defines.hpp"
#include "quantization/caq/caq_encoder.hpp"
#include "quantization/config.h"
#include "utils/IO.hpp"
#include "utils/rotator.hpp"
#include "utils/tools.hpp"

DEFINE_string(case_label, "", "label for this measurement run");
DEFINE_string(dataset, "", "dataset label for CSV output");
DEFINE_string(data_file, "", "PCA/base .fvecs file");
DEFINE_string(vars_file, "", "one-row PCA variance .fvecs file");
DEFINE_string(centroids_file, "", "optional centroid .fvecs file for residual measurement");
DEFINE_string(cids_file, "", "optional cluster-id .ivecs file for residual measurement");
DEFINE_string(output_csv, "", "output CSV path");
DEFINE_uint64(max_rows, 4096, "deterministic row-sample budget; 0 means all rows");
DEFINE_uint64(max_pairs, 4096, "deterministic same-cluster pair budget; 0 means all constructed pairs");
DEFINE_int32(min_bits, 0, "minimum bit width to evaluate");
DEFINE_int32(max_bits, saqlib::KMaxQuantizeBits, "maximum bit width to evaluate");
DEFINE_bool(rand_rotate, true, "apply deterministic per-segment random rotation before CAQ measurement");
DEFINE_int32(rotation_seed, 12345, "seed for deterministic measurement rotations");

namespace {
using namespace saqlib;

struct VecsInfo {
    std::string path;
    size_t rows = 0;
    size_t cols = 0;
    size_t row_bytes = 0;
};

struct ResidualPair {
    size_t query_idx = 0;
    size_t data_idx = 0;
    uint32_t cid = 0;
};

struct MetricAccumulator {
    size_t pairs = 0;
    size_t zero_data_norm_pairs = 0;
    size_t zero_query_norm_pairs = 0;
    size_t finite_direction_rows = 0;
    size_t finite_fac_error_rows = 0;
    size_t small_true_dist_pairs = 0;

    double data_norm2_sum = 0;
    double query_norm2_sum = 0;
    double true_ip_sum = 0;
    double true_l2_sum = 0;
    double est_l2_sum = 0;

    double raw_sse_sum = 0;
    double aligned_sse_sum = 0;
    double direction_loss_sum = 0;
    double cosine_sum = 0;
    double fac_error_sum = 0;

    double signed_ip_error_sum = 0;
    double abs_ip_error_sum = 0;
    double sq_ip_error_sum = 0;
    double signed_l2_error_sum = 0;
    double abs_l2_error_sum = 0;
    double sq_l2_error_sum = 0;
    double rel_l2_error_sum = 0;
    double overestimate_count = 0;
};

VecsInfo inspect_vecs_file(const std::string &path, size_t value_size) {
    CHECK(!path.empty()) << "empty vecs path";
    CHECK(utils::file_exists(path.c_str())) << "file does not exist: " << path;

    std::ifstream input(path, std::ios::binary);
    uint32_t cols = 0;
    input.read(reinterpret_cast<char *>(&cols), sizeof(uint32_t));
    CHECK_GT(cols, 0U) << "bad vecs dimension in " << path;

    const size_t file_size = utils::get_filesize(path.c_str());
    const size_t row_bytes = sizeof(uint32_t) + static_cast<size_t>(cols) * value_size;
    CHECK_EQ(file_size % row_bytes, 0U) << "file size is not divisible by row size: " << path;

    return VecsInfo{path, file_size / row_bytes, cols, row_bytes};
}

std::vector<size_t> deterministic_sample_indices(size_t rows, size_t max_rows) {
    const size_t sample_rows = (max_rows == 0 || max_rows >= rows) ? rows : max_rows;
    std::vector<size_t> indices;
    indices.reserve(sample_rows);
    for (size_t i = 0; i < sample_rows; ++i) {
        indices.push_back((i * rows) / sample_rows);
    }
    return indices;
}

FloatRowMat load_sampled_fvecs(const VecsInfo &info, const std::vector<size_t> &indices, size_t output_cols) {
    CHECK_GE(output_cols, info.cols);
    FloatRowMat rows(indices.size(), output_cols);
    rows.setZero();
    std::ifstream input(info.path, std::ios::binary);
    CHECK(input.good()) << "cannot open " << info.path;

    for (size_t out_i = 0; out_i < indices.size(); ++out_i) {
        const size_t row_id = indices[out_i];
        CHECK_LT(row_id, info.rows);
        input.seekg(static_cast<std::streamoff>(row_id * info.row_bytes), std::ios::beg);
        uint32_t cols = 0;
        input.read(reinterpret_cast<char *>(&cols), sizeof(uint32_t));
        CHECK_EQ(static_cast<size_t>(cols), info.cols);
        input.read(reinterpret_cast<char *>(&rows(out_i, 0)), sizeof(float) * info.cols);
    }
    return rows;
}

FloatRowMat pad_columns(FloatRowMat mat, size_t output_cols) {
    CHECK_LE(static_cast<size_t>(mat.cols()), output_cols);
    if (static_cast<size_t>(mat.cols()) == output_cols) {
        return mat;
    }
    FloatRowMat padded(mat.rows(), output_cols);
    padded.setZero();
    padded.leftCols(mat.cols()) = mat;
    return padded;
}

std::vector<uint32_t> load_sampled_ivec1(const std::string &path, const std::vector<size_t> &indices,
                                         size_t expected_rows) {
    const VecsInfo info = inspect_vecs_file(path, sizeof(uint32_t));
    CHECK_EQ(info.cols, 1U) << "cluster-id ivecs must have one column: " << path;
    CHECK_EQ(info.rows, expected_rows) << "cluster-id row count mismatch: " << path;

    std::vector<uint32_t> values(indices.size());
    std::ifstream input(path, std::ios::binary);
    CHECK(input.good()) << "cannot open " << path;
    for (size_t out_i = 0; out_i < indices.size(); ++out_i) {
        input.seekg(static_cast<std::streamoff>(indices[out_i] * info.row_bytes), std::ios::beg);
        uint32_t cols = 0;
        input.read(reinterpret_cast<char *>(&cols), sizeof(uint32_t));
        CHECK_EQ(cols, 1U);
        input.read(reinterpret_cast<char *>(&values[out_i]), sizeof(uint32_t));
    }
    return values;
}

FloatVec load_variance_vector(const std::string &path, size_t padded_dim) {
    FloatRowMat vars;
    utils::load_something<float, FloatRowMat>(path.c_str(), vars);
    CHECK_EQ(vars.rows(), 1) << "variance file must contain one row: " << path;

    FloatVec out = FloatVec::Zero(padded_dim);
    const size_t copy_size = std::min<size_t>(vars.cols(), padded_dim);
    out.head(copy_size) = vars.row(0).head(copy_size);
    return out;
}

double variance_sum(const FloatVec &vars, size_t start_dim, size_t dim_len) {
    return vars.segment(start_dim, dim_len).cast<double>().sum();
}

FloatRowMat build_segment_rows(const FloatRowMat &sampled_data, const FloatRowMat *centroids,
                               const std::vector<uint32_t> *cids, size_t start_dim, size_t dim_len) {
    FloatRowMat segment(sampled_data.rows(), dim_len);
    segment.setZero();
    for (Eigen::Index r = 0; r < sampled_data.rows(); ++r) {
        segment.row(r) = sampled_data.row(r).segment(start_dim, dim_len);
        if (centroids != nullptr && cids != nullptr) {
            const uint32_t cid = (*cids)[static_cast<size_t>(r)];
            CHECK_LT(cid, static_cast<uint32_t>(centroids->rows()));
            segment.row(r) -= centroids->row(cid).segment(start_dim, dim_len);
        }
    }
    return segment;
}

std::vector<ResidualPair> build_pairs(const std::vector<uint32_t> *sampled_cids, size_t sample_rows,
                                      size_t max_pairs) {
    CHECK_GT(sample_rows, 1U);
    std::vector<ResidualPair> pairs;
    pairs.reserve(max_pairs == 0 ? sample_rows : max_pairs);
    const auto budget_reached = [&]() { return max_pairs != 0 && pairs.size() >= max_pairs; };

    if (sampled_cids != nullptr) {
        std::map<uint32_t, std::vector<size_t>> groups;
        for (size_t i = 0; i < sampled_cids->size(); ++i) {
            groups[(*sampled_cids)[i]].push_back(i);
        }

        bool added = true;
        for (size_t stride = 1; added && !budget_reached(); ++stride) {
            added = false;
            for (const auto &[cid, rows] : groups) {
                const size_t n = rows.size();
                if (n <= 1 || stride >= n) {
                    continue;
                }
                for (size_t i = 0; i < n && !budget_reached(); ++i) {
                    const size_t q_idx = rows[i];
                    const size_t o_idx = rows[(i + stride) % n];
                    if (q_idx == o_idx) {
                        continue;
                    }
                    pairs.push_back(ResidualPair{q_idx, o_idx, cid});
                    added = true;
                }
            }
        }
        return pairs;
    }

    bool added = true;
    for (size_t stride = 1; added && !budget_reached(); ++stride) {
        added = false;
        if (stride >= sample_rows) {
            break;
        }
        for (size_t i = 0; i < sample_rows && !budget_reached(); ++i) {
            pairs.push_back(ResidualPair{i, (i + stride) % sample_rows, 0});
            added = true;
        }
    }
    return pairs;
}

double safe_direction_loss(double norm2, double oa_norm2, double ip, double *cosine_out) {
    if (norm2 <= 0 || oa_norm2 <= 0 || !std::isfinite(ip)) {
        *cosine_out = 0;
        return 1;
    }
    double cosine = ip / std::sqrt(norm2 * oa_norm2);
    cosine = std::max(-1.0, std::min(1.0, cosine));
    *cosine_out = cosine;
    return std::max(0.0, 1.0 - cosine * cosine);
}

double safe_fac_error(double norm2, double oa_norm2, double ip, size_t dim_len) {
    if (dim_len <= 1 || norm2 <= 0 || oa_norm2 <= 0 || ip == 0 || !std::isfinite(ip)) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const double ratio = (norm2 * oa_norm2) / (ip * ip);
    const double inner = std::max(0.0, ratio - 1.0) / static_cast<double>(dim_len - 1);
    return norm2 * 1.9 * std::sqrt(inner);
}

MetricAccumulator measure_bit(const FloatRowMat &segment_rows, const std::vector<ResidualPair> &pairs, size_t bits) {
    QuantSingleConfig cfg;
    cfg.quant_type = BaseQuantType::CAQ;
    cfg.random_rotation = false;

    MetricAccumulator acc;
    acc.pairs = pairs.size();

    std::unique_ptr<CAQEncoder> encoder;
    if (bits > 0) {
        encoder = std::make_unique<CAQEncoder>(static_cast<size_t>(segment_rows.cols()), bits, cfg);
    }

    for (const auto &pair : pairs) {
        const FloatVec q = segment_rows.row(static_cast<Eigen::Index>(pair.query_idx));
        const FloatVec o = segment_rows.row(static_cast<Eigen::Index>(pair.data_idx));
        const double q_norm2 = q.cast<double>().squaredNorm();
        const double o_norm2 = o.cast<double>().squaredNorm();
        const double true_ip = q.cast<double>().dot(o.cast<double>());
        const double true_l2_raw = q_norm2 + o_norm2 - 2.0 * true_ip;
        const double true_l2 = std::max(0.0, true_l2_raw);

        acc.query_norm2_sum += q_norm2;
        acc.data_norm2_sum += o_norm2;
        acc.true_ip_sum += true_ip;
        acc.true_l2_sum += true_l2;
        if (q_norm2 <= 0) {
            acc.zero_query_norm_pairs++;
        }
        if (o_norm2 <= 0) {
            acc.zero_data_norm_pairs++;
        }

        double ip_est = 0.0;
        double raw_sse = o_norm2;
        double aligned_sse = o_norm2;
        double direction_loss = o_norm2 > 0 ? 1.0 : 0.0;
        double cosine = 0.0;
        double fac_error = std::numeric_limits<double>::quiet_NaN();

        if (bits > 0) {
            CaqCode caq;
            encoder->encode(o, caq);
            const FloatVec oa = caq.get_oa();
            raw_sse = (o - oa).cast<double>().squaredNorm();
            const double oa_norm2 = caq.oa_l2sqr;
            const double ip_o_oa = caq.ip_o_oa;
            const double projected = oa_norm2 > 0 ? (ip_o_oa * ip_o_oa) / oa_norm2 : 0.0;
            aligned_sse = std::max(0.0, o_norm2 - projected);
            direction_loss = safe_direction_loss(o_norm2, oa_norm2, ip_o_oa, &cosine);
            fac_error = safe_fac_error(o_norm2, oa_norm2, ip_o_oa, static_cast<size_t>(segment_rows.cols()));
            const double rescale = ip_o_oa != 0.0 ? o_norm2 / ip_o_oa : 0.0;
            ip_est = rescale * q.cast<double>().dot(oa.cast<double>());
        }

        const double est_l2 = q_norm2 + o_norm2 - 2.0 * ip_est;
        const double ip_error = ip_est - true_ip;
        const double l2_error = est_l2 - true_l2;

        acc.est_l2_sum += est_l2;
        acc.raw_sse_sum += raw_sse;
        acc.aligned_sse_sum += aligned_sse;
        acc.direction_loss_sum += direction_loss;
        acc.cosine_sum += cosine;
        acc.finite_direction_rows++;
        if (std::isfinite(fac_error)) {
            acc.fac_error_sum += fac_error;
            acc.finite_fac_error_rows++;
        }

        acc.signed_ip_error_sum += ip_error;
        acc.abs_ip_error_sum += std::abs(ip_error);
        acc.sq_ip_error_sum += ip_error * ip_error;
        acc.signed_l2_error_sum += l2_error;
        acc.abs_l2_error_sum += std::abs(l2_error);
        acc.sq_l2_error_sum += l2_error * l2_error;
        if (std::abs(true_l2) <= 1e-9) {
            acc.small_true_dist_pairs++;
        }
        acc.rel_l2_error_sum += std::abs(l2_error) / std::max(1e-9, std::abs(true_l2));
        if (l2_error > 0) {
            acc.overestimate_count += 1.0;
        }
    }
    return acc;
}

double mean_or_zero(double sum, size_t count) {
    return count == 0 ? 0.0 : sum / static_cast<double>(count);
}

double mean_or_nan(double sum, size_t count) {
    return count == 0 ? std::numeric_limits<double>::quiet_NaN() : sum / static_cast<double>(count);
}

void write_header(std::ofstream &out) {
    out << "case,dataset,source_mode,rotation,sample_rows,total_rows,dim,start_dim,end_dim,segment_dim,bits,"
        << "pair_count,max_pairs,variance_sum,saq_proxy,saq_proxy_per_dim,"
        << "mean_data_norm2,mean_query_norm2,mean_true_ip,mean_true_l2,mean_est_l2,"
        << "mean_raw_sse,mean_aligned_sse,mean_direction_loss,mean_cosine,mean_fac_error,"
        << "mean_signed_ip_error,mean_abs_ip_error,mean_sq_ip_error,"
        << "mean_signed_l2_error,mean_abs_l2_error,mean_sq_l2_error,mean_rel_l2_error,overestimate_rate,"
        << "valid_direction_rows,valid_fac_error_rows,zero_data_norm_pairs,zero_query_norm_pairs,small_true_dist_pairs\n";
}

} // namespace

int main(int argc, char **argv) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK(!FLAGS_data_file.empty()) << "-data_file is required";
    CHECK(!FLAGS_vars_file.empty()) << "-vars_file is required";
    CHECK(!FLAGS_output_csv.empty()) << "-output_csv is required";
    CHECK_GE(FLAGS_min_bits, 0);
    CHECK_LE(FLAGS_max_bits, static_cast<int32_t>(KMaxQuantizeBits));
    CHECK_LE(FLAGS_min_bits, FLAGS_max_bits);

    const bool residual_mode = !FLAGS_centroids_file.empty() || !FLAGS_cids_file.empty();
    CHECK_EQ(FLAGS_centroids_file.empty(), FLAGS_cids_file.empty())
        << "centroids and cluster ids must be provided together";

    const VecsInfo data_info = inspect_vecs_file(FLAGS_data_file, sizeof(float));
    const size_t padded_dim = utils::rd_up_to_multiple_of(data_info.cols, kDimPaddingSize);
    const auto sample_indices = deterministic_sample_indices(data_info.rows, FLAGS_max_rows);
    std::cerr << "sample rows: " << sample_indices.size() << " / " << data_info.rows << "\n";

    FloatRowMat sampled_data = load_sampled_fvecs(data_info, sample_indices, padded_dim);
    const FloatVec vars = load_variance_vector(FLAGS_vars_file, padded_dim);

    FloatRowMat centroids;
    std::vector<uint32_t> sampled_cids;
    if (residual_mode) {
        utils::load_something<float, FloatRowMat>(FLAGS_centroids_file.c_str(), centroids);
        CHECK_LE(static_cast<size_t>(centroids.cols()), padded_dim);
        centroids = pad_columns(std::move(centroids), padded_dim);
        sampled_cids = load_sampled_ivec1(FLAGS_cids_file, sample_indices, data_info.rows);
    }

    const std::vector<ResidualPair> pairs =
        build_pairs(residual_mode ? &sampled_cids : nullptr, sample_indices.size(), FLAGS_max_pairs);
    CHECK(!pairs.empty()) << "no query-unaware data pairs could be constructed";
    std::cerr << "pairs: " << pairs.size() << "\n";

    if (FLAGS_rand_rotate) {
        std::srand(FLAGS_rotation_seed);
    }

    const std::filesystem::path output_path(FLAGS_output_csv);
    if (!output_path.parent_path().empty()) {
        std::filesystem::create_directories(output_path.parent_path());
    }
    std::ofstream out(FLAGS_output_csv, std::ios::out);
    CHECK(out.good()) << "cannot open output CSV: " << FLAGS_output_csv;
    write_header(out);

    const size_t num_blocks = padded_dim / kDimPaddingSize;
    const std::string source_mode = residual_mode ? "ivf_residual_same_cluster_pairs" : "base_vector_pairs";
    const std::string rotation = FLAGS_rand_rotate ? "deterministic_random" : "none";
    const FloatRowMat *centroids_ptr = residual_mode ? &centroids : nullptr;
    const std::vector<uint32_t> *cids_ptr = residual_mode ? &sampled_cids : nullptr;

    for (size_t start_block = 0; start_block < num_blocks; ++start_block) {
        for (size_t end_block = start_block + 1; end_block <= num_blocks; ++end_block) {
            const size_t start_dim = start_block * kDimPaddingSize;
            const size_t end_dim = end_block * kDimPaddingSize;
            const size_t dim_len = end_dim - start_dim;
            FloatRowMat segment_rows = build_segment_rows(sampled_data, centroids_ptr, cids_ptr, start_dim, dim_len);

            if (FLAGS_rand_rotate) {
                utils::Rotator rotator(static_cast<uint32_t>(dim_len));
                rotator.orthogonalize();
                segment_rows = segment_rows * rotator.get_P();
            }

            const double var_sum = variance_sum(vars, start_dim, dim_len);
            for (int bits = FLAGS_min_bits; bits <= FLAGS_max_bits; ++bits) {
                const MetricAccumulator acc = measure_bit(segment_rows, pairs, static_cast<size_t>(bits));
                const double denom = bits == 0 ? 1.0 : static_cast<double>(1ULL << bits);
                const double proxy = var_sum / denom;
                const double pair_count_d = static_cast<double>(acc.pairs);
                const double dim_d = static_cast<double>(dim_len);
                out << FLAGS_case_label << ',' << FLAGS_dataset << ',' << source_mode << ',' << rotation << ','
                    << sample_indices.size() << ',' << data_info.rows << ',' << data_info.cols << ','
                    << start_dim << ',' << end_dim << ',' << dim_len << ',' << bits << ','
                    << acc.pairs << ',' << FLAGS_max_pairs << ','
                    << var_sum << ',' << proxy << ',' << proxy / dim_d << ','
                    << acc.data_norm2_sum / pair_count_d << ',' << acc.query_norm2_sum / pair_count_d << ','
                    << acc.true_ip_sum / pair_count_d << ',' << acc.true_l2_sum / pair_count_d << ','
                    << acc.est_l2_sum / pair_count_d << ','
                    << acc.raw_sse_sum / pair_count_d << ',' << acc.aligned_sse_sum / pair_count_d << ','
                    << mean_or_zero(acc.direction_loss_sum, acc.finite_direction_rows) << ','
                    << mean_or_zero(acc.cosine_sum, acc.finite_direction_rows) << ','
                    << mean_or_nan(acc.fac_error_sum, acc.finite_fac_error_rows) << ','
                    << acc.signed_ip_error_sum / pair_count_d << ',' << acc.abs_ip_error_sum / pair_count_d << ','
                    << acc.sq_ip_error_sum / pair_count_d << ','
                    << acc.signed_l2_error_sum / pair_count_d << ',' << acc.abs_l2_error_sum / pair_count_d << ','
                    << acc.sq_l2_error_sum / pair_count_d << ',' << acc.rel_l2_error_sum / pair_count_d << ','
                    << acc.overestimate_count / pair_count_d << ','
                    << acc.finite_direction_rows << ',' << acc.finite_fac_error_rows << ','
                    << acc.zero_data_norm_pairs << ',' << acc.zero_query_norm_pairs << ',' << acc.small_true_dist_pairs
                    << '\n';
            }
        }
    }

    std::cout << "estimator-error measurement written to: " << FLAGS_output_csv << "\n";
    return 0;
}

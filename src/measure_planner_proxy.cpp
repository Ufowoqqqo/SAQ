#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
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

struct MetricAccumulator {
    size_t rows = 0;
    size_t zero_norm_rows = 0;
    size_t finite_direction_rows = 0;
    size_t finite_fac_error_rows = 0;
    double norm2_sum = 0;
    double raw_sse_sum = 0;
    double aligned_sse_sum = 0;
    double direction_loss_sum = 0;
    double cosine_sum = 0;
    double fac_error_sum = 0;
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

MetricAccumulator measure_bit(const FloatRowMat &segment_rows, size_t bits) {
    QuantSingleConfig cfg;
    cfg.quant_type = BaseQuantType::CAQ;
    cfg.random_rotation = false;

    MetricAccumulator acc;
    acc.rows = static_cast<size_t>(segment_rows.rows());

    if (bits > 0) {
        CAQEncoder encoder(static_cast<size_t>(segment_rows.cols()), bits, cfg);
        for (Eigen::Index r = 0; r < segment_rows.rows(); ++r) {
            const FloatVec v = segment_rows.row(r);
            const double norm2 = v.cast<double>().squaredNorm();
            acc.norm2_sum += norm2;
            if (norm2 <= 0) {
                acc.zero_norm_rows++;
                continue;
            }

            CaqCode caq;
            encoder.encode(v, caq);
            const FloatVec oa = caq.get_oa();
            const double raw_sse = (v - oa).cast<double>().squaredNorm();
            const double oa_norm2 = caq.oa_l2sqr;
            const double ip = caq.ip_o_oa;
            const double projected = oa_norm2 > 0 ? (ip * ip) / oa_norm2 : 0;
            const double aligned_sse = std::max(0.0, norm2 - projected);

            double cosine = 0;
            const double direction_loss = safe_direction_loss(norm2, oa_norm2, ip, &cosine);
            const double fac_error = safe_fac_error(norm2, oa_norm2, ip, static_cast<size_t>(segment_rows.cols()));

            acc.raw_sse_sum += raw_sse;
            acc.aligned_sse_sum += aligned_sse;
            acc.direction_loss_sum += direction_loss;
            acc.cosine_sum += cosine;
            acc.finite_direction_rows++;
            if (std::isfinite(fac_error)) {
                acc.fac_error_sum += fac_error;
                acc.finite_fac_error_rows++;
            }
        }
        return acc;
    }

    for (Eigen::Index r = 0; r < segment_rows.rows(); ++r) {
        const double norm2 = segment_rows.row(r).cast<double>().squaredNorm();
        acc.norm2_sum += norm2;
        acc.raw_sse_sum += norm2;
        acc.aligned_sse_sum += norm2;
        if (norm2 <= 0) {
            acc.zero_norm_rows++;
        } else {
            acc.direction_loss_sum += 1;
            acc.finite_direction_rows++;
        }
    }
    return acc;
}

double mean_or_zero(double sum, size_t count) {
    return count == 0 ? 0.0 : sum / static_cast<double>(count);
}

void write_header(std::ofstream &out) {
    out << "case,dataset,source_mode,rotation,sample_rows,total_rows,dim,start_dim,end_dim,segment_dim,bits,"
        << "variance_sum,saq_proxy,saq_proxy_per_dim,mean_norm2,mean_norm2_per_dim,"
        << "mean_raw_sse,mean_raw_sse_per_dim,mean_aligned_sse,mean_aligned_sse_per_dim,"
        << "mean_direction_loss,mean_cosine,mean_fac_error,valid_direction_rows,valid_fac_error_rows,zero_norm_rows\n";
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

    if (FLAGS_rand_rotate) {
        std::srand(FLAGS_rotation_seed);
    }

    std::filesystem::create_directories(std::filesystem::path(FLAGS_output_csv).parent_path());
    std::ofstream out(FLAGS_output_csv, std::ios::out);
    CHECK(out.good()) << "cannot open output CSV: " << FLAGS_output_csv;
    write_header(out);

    const size_t num_blocks = padded_dim / kDimPaddingSize;
    const std::string source_mode = residual_mode ? "ivf_residual" : "base_vector";
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
                const MetricAccumulator acc = measure_bit(segment_rows, static_cast<size_t>(bits));
                const double denom = bits == 0 ? 1.0 : static_cast<double>(1ULL << bits);
                const double proxy = var_sum / denom;
                const double sample_rows_d = static_cast<double>(sample_indices.size());
                const double dim_d = static_cast<double>(dim_len);
                out << FLAGS_case_label << ',' << FLAGS_dataset << ',' << source_mode << ',' << rotation << ','
                    << sample_indices.size() << ',' << data_info.rows << ',' << data_info.cols << ','
                    << start_dim << ',' << end_dim << ',' << dim_len << ',' << bits << ','
                    << var_sum << ',' << proxy << ',' << proxy / dim_d << ','
                    << acc.norm2_sum / sample_rows_d << ',' << acc.norm2_sum / sample_rows_d / dim_d << ','
                    << acc.raw_sse_sum / sample_rows_d << ',' << acc.raw_sse_sum / sample_rows_d / dim_d << ','
                    << acc.aligned_sse_sum / sample_rows_d << ',' << acc.aligned_sse_sum / sample_rows_d / dim_d << ','
                    << mean_or_zero(acc.direction_loss_sum, acc.finite_direction_rows) << ','
                    << mean_or_zero(acc.cosine_sum, acc.finite_direction_rows) << ','
                    << mean_or_zero(acc.fac_error_sum, acc.finite_fac_error_rows) << ','
                    << acc.finite_direction_rows << ',' << acc.finite_fac_error_rows << ',' << acc.zero_norm_rows << '\n';
            }
        }
    }

    std::cout << "planner proxy measurement written to: " << FLAGS_output_csv << "\n";
    return 0;
}

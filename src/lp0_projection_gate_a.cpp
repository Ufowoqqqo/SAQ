#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <gflags/gflags.h>
#include <glog/logging.h>

#include "defines.hpp"
#include "utils/IO.hpp"

using namespace saqlib;

DEFINE_string(raw_base_file, "", "Frozen raw GIST base fvecs.");
DEFINE_string(raw_query_file, "", "Frozen raw GIST query fvecs.");
DEFINE_string(pca_base_file, "", "Frozen historical full-dimensional PCA base fvecs.");
DEFINE_string(pca_query_file, "", "Frozen historical full-dimensional PCA query fvecs.");
DEFINE_string(pca_centroids_file, "", "Frozen historical PCA IVF centroids fvecs.");
DEFINE_string(cluster_ids_file, "", "Frozen IVF cluster assignments ivecs.");
DEFINE_string(pca_variance_file, "", "Frozen historical PCA variance fvecs (provenance only).");
DEFINE_string(fixed_probes_file, "", "Frozen q128/nprobe16 probe ivecs.");
DEFINE_string(prepared_manifest, "", "LP-0 preparation manifest.");
DEFINE_string(output_prefix, "", "Output prefix for Gate-A CSV and JSON artifacts.");

namespace {

using DoubleRowMat = Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;

constexpr size_t kN = 50000;
constexpr size_t kD = 960;
constexpr size_t kProjectedD = 576;
constexpr size_t kK = 512;
constexpr size_t kQueries = 128;
constexpr size_t kNProbe = 16;
constexpr size_t kTopK = 100;
constexpr double kRelativeEpsilon = 1e-12;
constexpr double kTailTolerance = 1e-6;
constexpr double kOperatorOrthogonalityTolerance = 1e-12;
constexpr const char *kExpectedCandidateSha256 =
    "f5eaef79fbbceda7a0cb04adb5dc232d24d00e0173b4cd70bb0f29ddae25b099";
constexpr uint64_t kExpectedCandidateTotal = 442823;
constexpr size_t kExpectedCandidateMin = 1675;
constexpr size_t kExpectedCandidateMax = 5433;
constexpr const char *kExactScope = "canonical_raw_float64_squared_L2";
constexpr uint64_t kFnv1aOffsetBasis = UINT64_C(14695981039346656037);
constexpr uint64_t kFnv1aPrime = UINT64_C(1099511628211);

struct FrozenFile {
    const char *manifest_key;
    const std::string *path;
    const char *expected_sha256;
};

class Sha256 {
  public:
    Sha256() { reset(); }

    void update(const void *data, size_t size) {
        const auto *bytes = static_cast<const uint8_t *>(data);
        total_bytes_ += size;
        while (size > 0) {
            const size_t take = std::min(size, block_.size() - block_size_);
            std::copy_n(bytes, take, block_.data() + block_size_);
            block_size_ += take;
            bytes += take;
            size -= take;
            if (block_size_ == block_.size()) {
                transform(block_.data());
                block_size_ = 0;
            }
        }
    }

    void append_u32_le(uint32_t value) {
        std::array<uint8_t, 4> bytes{};
        for (size_t i = 0; i < bytes.size(); ++i) {
            bytes[i] = static_cast<uint8_t>((value >> (8 * i)) & UINT32_C(0xff));
        }
        update(bytes.data(), bytes.size());
    }

    void append_u64_le(uint64_t value) {
        std::array<uint8_t, 8> bytes{};
        for (size_t i = 0; i < bytes.size(); ++i) {
            bytes[i] = static_cast<uint8_t>((value >> (8 * i)) & UINT64_C(0xff));
        }
        update(bytes.data(), bytes.size());
    }

    std::string hex_digest() const {
        Sha256 copy = *this;
        return copy.finish();
    }

  private:
    static constexpr std::array<uint32_t, 64> kRoundConstants{
        UINT32_C(0x428a2f98), UINT32_C(0x71374491), UINT32_C(0xb5c0fbcf), UINT32_C(0xe9b5dba5),
        UINT32_C(0x3956c25b), UINT32_C(0x59f111f1), UINT32_C(0x923f82a4), UINT32_C(0xab1c5ed5),
        UINT32_C(0xd807aa98), UINT32_C(0x12835b01), UINT32_C(0x243185be), UINT32_C(0x550c7dc3),
        UINT32_C(0x72be5d74), UINT32_C(0x80deb1fe), UINT32_C(0x9bdc06a7), UINT32_C(0xc19bf174),
        UINT32_C(0xe49b69c1), UINT32_C(0xefbe4786), UINT32_C(0x0fc19dc6), UINT32_C(0x240ca1cc),
        UINT32_C(0x2de92c6f), UINT32_C(0x4a7484aa), UINT32_C(0x5cb0a9dc), UINT32_C(0x76f988da),
        UINT32_C(0x983e5152), UINT32_C(0xa831c66d), UINT32_C(0xb00327c8), UINT32_C(0xbf597fc7),
        UINT32_C(0xc6e00bf3), UINT32_C(0xd5a79147), UINT32_C(0x06ca6351), UINT32_C(0x14292967),
        UINT32_C(0x27b70a85), UINT32_C(0x2e1b2138), UINT32_C(0x4d2c6dfc), UINT32_C(0x53380d13),
        UINT32_C(0x650a7354), UINT32_C(0x766a0abb), UINT32_C(0x81c2c92e), UINT32_C(0x92722c85),
        UINT32_C(0xa2bfe8a1), UINT32_C(0xa81a664b), UINT32_C(0xc24b8b70), UINT32_C(0xc76c51a3),
        UINT32_C(0xd192e819), UINT32_C(0xd6990624), UINT32_C(0xf40e3585), UINT32_C(0x106aa070),
        UINT32_C(0x19a4c116), UINT32_C(0x1e376c08), UINT32_C(0x2748774c), UINT32_C(0x34b0bcb5),
        UINT32_C(0x391c0cb3), UINT32_C(0x4ed8aa4a), UINT32_C(0x5b9cca4f), UINT32_C(0x682e6ff3),
        UINT32_C(0x748f82ee), UINT32_C(0x78a5636f), UINT32_C(0x84c87814), UINT32_C(0x8cc70208),
        UINT32_C(0x90befffa), UINT32_C(0xa4506ceb), UINT32_C(0xbef9a3f7), UINT32_C(0xc67178f2)};

    static uint32_t rotate_right(uint32_t value, unsigned int count) {
        return (value >> count) | (value << (32 - count));
    }

    void reset() {
        state_ = {UINT32_C(0x6a09e667), UINT32_C(0xbb67ae85), UINT32_C(0x3c6ef372),
                  UINT32_C(0xa54ff53a), UINT32_C(0x510e527f), UINT32_C(0x9b05688c),
                  UINT32_C(0x1f83d9ab), UINT32_C(0x5be0cd19)};
        block_.fill(0);
        block_size_ = 0;
        total_bytes_ = 0;
    }

    void transform(const uint8_t *block) {
        std::array<uint32_t, 64> schedule{};
        for (size_t i = 0; i < 16; ++i) {
            schedule[i] = (static_cast<uint32_t>(block[4 * i]) << 24) |
                          (static_cast<uint32_t>(block[4 * i + 1]) << 16) |
                          (static_cast<uint32_t>(block[4 * i + 2]) << 8) |
                          static_cast<uint32_t>(block[4 * i + 3]);
        }
        for (size_t i = 16; i < schedule.size(); ++i) {
            const uint32_t s0 = rotate_right(schedule[i - 15], 7) ^
                                rotate_right(schedule[i - 15], 18) ^ (schedule[i - 15] >> 3);
            const uint32_t s1 = rotate_right(schedule[i - 2], 17) ^
                                rotate_right(schedule[i - 2], 19) ^ (schedule[i - 2] >> 10);
            schedule[i] = schedule[i - 16] + s0 + schedule[i - 7] + s1;
        }

        uint32_t a = state_[0];
        uint32_t b = state_[1];
        uint32_t c = state_[2];
        uint32_t d = state_[3];
        uint32_t e = state_[4];
        uint32_t f = state_[5];
        uint32_t g = state_[6];
        uint32_t h = state_[7];
        for (size_t i = 0; i < schedule.size(); ++i) {
            const uint32_t sum1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
            const uint32_t choose = (e & f) ^ ((~e) & g);
            const uint32_t temp1 = h + sum1 + choose + kRoundConstants[i] + schedule[i];
            const uint32_t sum0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
            const uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
            const uint32_t temp2 = sum0 + majority;
            h = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }
        state_[0] += a;
        state_[1] += b;
        state_[2] += c;
        state_[3] += d;
        state_[4] += e;
        state_[5] += f;
        state_[6] += g;
        state_[7] += h;
    }

    std::string finish() {
        const uint64_t bit_count = static_cast<uint64_t>(total_bytes_) * 8;
        const uint8_t marker = 0x80;
        update(&marker, 1);
        const uint8_t zero = 0;
        while (block_size_ != 56) {
            update(&zero, 1);
        }
        std::array<uint8_t, 8> length{};
        for (size_t i = 0; i < length.size(); ++i) {
            length[7 - i] = static_cast<uint8_t>((bit_count >> (8 * i)) & UINT64_C(0xff));
        }
        update(length.data(), length.size());
        CHECK_EQ(block_size_, 0U);
        std::ostringstream output;
        output << std::hex << std::setfill('0');
        for (uint32_t value : state_) {
            output << std::setw(8) << value;
        }
        return output.str();
    }

    std::array<uint32_t, 8> state_{};
    std::array<uint8_t, 64> block_{};
    size_t block_size_ = 0;
    size_t total_bytes_ = 0;
};

std::string sha256_file(const std::string &path) {
    std::ifstream input(path, std::ios::binary);
    CHECK(input.is_open()) << "cannot open " << path;
    Sha256 digest;
    std::array<char, 4 * 1024 * 1024> buffer{};
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const auto count = input.gcount();
        if (count > 0) {
            digest.update(buffer.data(), static_cast<size_t>(count));
        }
    }
    CHECK(input.eof()) << "failed while hashing " << path;
    return digest.hex_digest();
}

void fnv1a_append_byte(uint64_t &hash, uint8_t value) {
    hash ^= value;
    hash *= kFnv1aPrime;
}

void fnv1a_append_u32(uint64_t &hash, uint32_t value) {
    for (unsigned int shift = 0; shift < 32; shift += 8) {
        fnv1a_append_byte(hash, static_cast<uint8_t>((value >> shift) & UINT32_C(0xff)));
    }
}

void fnv1a_append_u64(uint64_t &hash, uint64_t value) {
    for (unsigned int shift = 0; shift < 64; shift += 8) {
        fnv1a_append_byte(hash, static_cast<uint8_t>((value >> shift) & UINT64_C(0xff)));
    }
}

std::string uint64_hex(uint64_t value) {
    std::ostringstream output;
    output << std::hex << std::setfill('0') << std::setw(16) << value;
    return output.str();
}

std::string json_string(const std::string &value) {
    std::ostringstream output;
    output << '"';
    for (unsigned char ch : value) {
        switch (ch) {
        case '"': output << "\\\""; break;
        case '\\': output << "\\\\"; break;
        case '\b': output << "\\b"; break;
        case '\f': output << "\\f"; break;
        case '\n': output << "\\n"; break;
        case '\r': output << "\\r"; break;
        case '\t': output << "\\t"; break;
        default:
            if (ch < 0x20) {
                output << "\\u" << std::hex << std::setfill('0') << std::setw(4)
                       << static_cast<unsigned int>(ch) << std::dec;
            } else {
                output << static_cast<char>(ch);
            }
        }
    }
    output << '"';
    return output.str();
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

std::string pipe_separated_ids(const std::vector<PID> &ids) {
    std::ostringstream output;
    for (size_t i = 0; i < ids.size(); ++i) {
        if (i != 0) {
            output << '|';
        }
        output << ids[i];
    }
    return output.str();
}

// Keep this accumulation expression fixed: under the repository's registered
// Release flags, its full-range result is byte-identical to the already-frozen
// Phase-1 raw-distance reference.  The evaluator enforces that identity.
template <class LeftDerived, class RightDerived>
double squared_l2_float64_range(const Eigen::MatrixBase<LeftDerived> &left,
                                const Eigen::MatrixBase<RightDerived> &right,
                                size_t begin, size_t end) {
    CHECK_EQ(left.cols(), right.cols());
    CHECK_LE(end, static_cast<size_t>(left.cols()));
    double result = 0;
    for (size_t dimension = begin; dimension < end; ++dimension) {
        const double difference = static_cast<double>(left(static_cast<Eigen::Index>(dimension))) -
                                  static_cast<double>(right(static_cast<Eigen::Index>(dimension)));
        result += difference * difference;
    }
    return result;
}

bool finite_double_bits(double value) {
    return (std::bit_cast<uint64_t>(value) & UINT64_C(0x7ff0000000000000)) !=
           UINT64_C(0x7ff0000000000000);
}

DoubleRowMat load_f64bin(const std::filesystem::path &path) {
    static_assert(std::endian::native == std::endian::little,
                  "LP-0 dense binary artifacts require a little-endian host");
    std::ifstream input(path, std::ios::binary);
    CHECK(input.is_open()) << "cannot open " << path;
    uint32_t rows = 0;
    uint32_t cols = 0;
    input.read(reinterpret_cast<char *>(&rows), sizeof(rows));
    input.read(reinterpret_cast<char *>(&cols), sizeof(cols));
    CHECK(input.good()) << "truncated f64bin header in " << path;
    DoubleRowMat values(rows, cols);
    input.read(reinterpret_cast<char *>(values.data()),
               static_cast<std::streamsize>(values.size() * sizeof(double)));
    CHECK(input.good()) << "truncated f64bin payload in " << path;
    CHECK_EQ(input.peek(), std::char_traits<char>::eof()) << "trailing bytes in " << path;
    return values;
}

std::string sha256_array_int32(const UintRowMat &values) {
    static_assert(std::endian::native == std::endian::little,
                  "array hashes require a little-endian host for this registered run");
    Sha256 digest;
    constexpr char dtype[] = "int32";
    digest.update(dtype, sizeof(dtype) - 1);
    digest.append_u32_le(2);
    digest.append_u64_le(static_cast<uint64_t>(values.rows()));
    digest.append_u64_le(static_cast<uint64_t>(values.cols()));
    digest.update(values.data(), static_cast<size_t>(values.size()) * sizeof(uint32_t));
    return digest.hex_digest();
}

std::string sha256_array_float64(const DoubleRowMat &values) {
    static_assert(std::endian::native == std::endian::little,
                  "array hashes require a little-endian host for this registered run");
    Sha256 digest;
    constexpr char dtype[] = "float64";
    digest.update(dtype, sizeof(dtype) - 1);
    digest.append_u32_le(2);
    digest.append_u64_le(static_cast<uint64_t>(values.rows()));
    digest.append_u64_le(static_cast<uint64_t>(values.cols()));
    digest.update(values.data(), static_cast<size_t>(values.size()) * sizeof(double));
    return digest.hex_digest();
}

double quantile_sorted(const std::vector<double> &values, double probability) {
    CHECK(!values.empty());
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
    double relative_p50 = std::numeric_limits<double>::quiet_NaN();
    double relative_p90 = std::numeric_limits<double>::quiet_NaN();
    double relative_p99 = std::numeric_limits<double>::quiet_NaN();
};

MetricSummary summarize_errors(const std::vector<double> &exact,
                               const std::vector<double> &estimate) {
    CHECK_EQ(exact.size(), estimate.size());
    MetricSummary result;
    result.total_count = exact.size();
    long double error_sum = 0;
    long double absolute_error_sum = 0;
    long double squared_error_sum = 0;
    std::vector<double> relative_errors;
    relative_errors.reserve(exact.size());
    for (size_t i = 0; i < exact.size(); ++i) {
        if (!finite_double_bits(estimate[i])) {
            ++result.nonfinite_count;
            continue;
        }
        ++result.finite_count;
        const double error = estimate[i] - exact[i];
        error_sum += error;
        absolute_error_sum += std::abs(error);
        squared_error_sum += error * error;
        relative_errors.push_back(std::abs(error) /
                                  std::max(std::abs(exact[i]), kRelativeEpsilon));
    }
    CHECK_EQ(result.finite_count, result.total_count) << "Gate A produced a non-finite estimate";
    const double denominator = static_cast<double>(result.finite_count);
    result.bias = static_cast<double>(error_sum / denominator);
    result.mae = static_cast<double>(absolute_error_sum / denominator);
    result.rmse = std::sqrt(static_cast<double>(squared_error_sum / denominator));
    std::sort(relative_errors.begin(), relative_errors.end());
    result.relative_p50 = quantile_sorted(relative_errors, 0.50);
    result.relative_p90 = quantile_sorted(relative_errors, 0.90);
    result.relative_p99 = quantile_sorted(relative_errors, 0.99);
    return result;
}

double ranking_value(double value) {
    return finite_double_bits(value) ? value : std::numeric_limits<double>::infinity();
}

struct RankingSummary {
    size_t topk_used = 0;
    double topk_agreement = std::numeric_limits<double>::quiet_NaN();
    size_t exact_best_estimated_rank = 0;
    uint64_t boundary_inversions = 0;
    uint64_t boundary_pairs = 0;
    double boundary_inversion_rate = std::numeric_limits<double>::quiet_NaN();
};

RankingSummary ranking_summary(const std::vector<double> &exact,
                               const std::vector<double> &estimate,
                               const std::vector<PID> &ids) {
    CHECK_EQ(exact.size(), estimate.size());
    CHECK_EQ(exact.size(), ids.size());
    CHECK_GE(exact.size(), kTopK);
    std::vector<size_t> exact_order(exact.size());
    std::iota(exact_order.begin(), exact_order.end(), 0);
    std::sort(exact_order.begin(), exact_order.end(), [&](size_t lhs, size_t rhs) {
        if (exact[lhs] != exact[rhs]) {
            return exact[lhs] < exact[rhs];
        }
        return ids[lhs] < ids[rhs];
    });
    std::vector<size_t> estimate_order(exact.size());
    std::iota(estimate_order.begin(), estimate_order.end(), 0);
    std::sort(estimate_order.begin(), estimate_order.end(), [&](size_t lhs, size_t rhs) {
        const double lhs_value = ranking_value(estimate[lhs]);
        const double rhs_value = ranking_value(estimate[rhs]);
        if (lhs_value != rhs_value) {
            return lhs_value < rhs_value;
        }
        return ids[lhs] < ids[rhs];
    });

    RankingSummary result;
    result.topk_used = kTopK;
    std::vector<char> is_exact_topk(exact.size(), false);
    for (size_t i = 0; i < kTopK; ++i) {
        is_exact_topk[exact_order[i]] = true;
    }
    size_t overlap = 0;
    for (size_t i = 0; i < kTopK; ++i) {
        overlap += is_exact_topk[estimate_order[i]] ? 1 : 0;
    }
    result.topk_agreement = static_cast<double>(overlap) / static_cast<double>(kTopK);
    const size_t exact_best = exact_order.front();
    result.exact_best_estimated_rank = static_cast<size_t>(
        std::find(estimate_order.begin(), estimate_order.end(), exact_best) - estimate_order.begin()) + 1;

    std::vector<double> outside_estimates;
    outside_estimates.reserve(exact.size() - kTopK);
    for (size_t i = kTopK; i < exact.size(); ++i) {
        outside_estimates.push_back(ranking_value(estimate[exact_order[i]]));
    }
    std::sort(outside_estimates.begin(), outside_estimates.end());
    for (size_t i = 0; i < kTopK; ++i) {
        const double top_estimate = ranking_value(estimate[exact_order[i]]);
        result.boundary_inversions += static_cast<uint64_t>(
            std::lower_bound(outside_estimates.begin(), outside_estimates.end(), top_estimate) -
            outside_estimates.begin());
    }
    result.boundary_pairs = static_cast<uint64_t>(kTopK) *
                            static_cast<uint64_t>(exact.size() - kTopK);
    result.boundary_inversion_rate = static_cast<double>(result.boundary_inversions) /
                                     static_cast<double>(result.boundary_pairs);
    return result;
}

template <typename Scalar>
Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>
load_dense_bin(const std::filesystem::path &path) {
    static_assert(std::endian::native == std::endian::little,
                  "LP-0 dense binary artifacts require a little-endian host");
    std::ifstream input(path, std::ios::binary);
    CHECK(input.is_open()) << "cannot open " << path;
    uint32_t rows = 0;
    uint32_t cols = 0;
    input.read(reinterpret_cast<char *>(&rows), sizeof(rows));
    input.read(reinterpret_cast<char *>(&cols), sizeof(cols));
    CHECK(input.good()) << "truncated dense-bin header in " << path;
    Eigen::Matrix<Scalar, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> values(rows, cols);
    input.read(reinterpret_cast<char *>(values.data()),
               static_cast<std::streamsize>(values.size() * sizeof(Scalar)));
    CHECK(input.good()) << "truncated dense-bin payload in " << path;
    CHECK_EQ(input.peek(), std::char_traits<char>::eof()) << "trailing bytes in " << path;
    return values;
}

struct PreparedArtifacts {
    std::filesystem::path directory;
    std::filesystem::path mean;
    std::filesystem::path retained_operator;
    std::filesystem::path raw_centroids;
    std::filesystem::path head_base;
    std::filesystem::path head_query;
    std::filesystem::path head_centroids;
    std::filesystem::path base_tail_sq_exact;
    std::filesystem::path base_tail_norm_deployed;
    std::filesystem::path query_probe_tail_sq_exact;
    std::filesystem::path query_probe_tail_sq_deployed;
    std::filesystem::path fixed_probes;
    std::filesystem::path candidate_inventory;
};

std::filesystem::path prepared_output_path(const boost::property_tree::ptree &manifest,
                                           const std::filesystem::path &directory,
                                           const char *key) {
    const std::string prefix = std::string("outputs.") + key;
    const auto relative = manifest.get<std::string>(prefix + ".relative_path");
    const auto path = directory / relative;
    CHECK(std::filesystem::is_regular_file(path)) << "missing prepared artifact " << path;
    const std::string observed_file_hash = sha256_file(path.string());
    const std::string registered_file_hash = manifest.get<std::string>(prefix + ".file_sha256");
    CHECK_EQ(observed_file_hash, registered_file_hash)
        << "prepared artifact file hash drift for " << key;
    return path;
}

PreparedArtifacts prepared_artifacts(const boost::property_tree::ptree &manifest) {
    const auto manifest_path = std::filesystem::absolute(FLAGS_prepared_manifest);
    CHECK(std::filesystem::is_regular_file(manifest_path))
        << "missing prepared manifest " << manifest_path;
    const auto directory = manifest_path.parent_path();
    PreparedArtifacts result;
    result.directory = directory;
    result.mean = prepared_output_path(manifest, directory, "apply_mean");
    result.retained_operator = prepared_output_path(manifest, directory, "retained_operator");
    result.raw_centroids = prepared_output_path(manifest, directory, "raw_centroids");
    result.head_base = prepared_output_path(manifest, directory, "pca_head_base");
    result.head_query = prepared_output_path(manifest, directory, "pca_head_query");
    result.head_centroids = prepared_output_path(manifest, directory, "pca_head_centroids");
    result.base_tail_sq_exact = prepared_output_path(manifest, directory, "base_tail_sq_exact");
    result.base_tail_norm_deployed =
        prepared_output_path(manifest, directory, "base_tail_norm_deployed");
    result.query_probe_tail_sq_exact =
        prepared_output_path(manifest, directory, "query_probe_tail_sq_exact");
    result.query_probe_tail_sq_deployed =
        prepared_output_path(manifest, directory, "query_probe_tail_sq_deployed");
    result.fixed_probes = prepared_output_path(manifest, directory, "fixed_probes");
    result.candidate_inventory = prepared_output_path(manifest, directory, "candidate_inventory");
    return result;
}

std::string read_text_file(const std::string &path) {
    std::ifstream input(path, std::ios::binary);
    CHECK(input.is_open()) << "cannot open " << path;
    std::ostringstream contents;
    contents << input.rdbuf();
    CHECK(input.good() || input.eof()) << "failed reading " << path;
    return contents.str();
}

void require_manifest_contains_hash(const std::string &manifest_text,
                                    const std::string &hash, const char *label) {
    CHECK_NE(manifest_text.find(hash), std::string::npos)
        << "prepared manifest does not contain the registered " << label << " hash " << hash;
}

struct LoadedData {
    FloatRowMat raw_base;
    FloatRowMat raw_query;
    FloatRowMat pca_base;
    FloatRowMat pca_query;
    FloatRowMat pca_centroids;
    FloatRowMat pca_variance;
    UintRowMat cluster_ids;
    UintRowMat fixed_probes;

    FloatRowMat prepared_head_base;
    FloatRowMat prepared_head_query;
    FloatRowMat prepared_head_centroids;
    UintRowMat prepared_fixed_probes;
    DoubleRowMat mean;
    DoubleRowMat retained_operator;
    DoubleRowMat raw_centroids;
    DoubleRowMat prepared_base_tail_sq_exact;
    Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>
        prepared_base_tail_norm_deployed;
    DoubleRowMat prepared_query_probe_tail_sq_exact;
    Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>
        prepared_query_probe_tail_sq_deployed;
};

LoadedData load_data(const PreparedArtifacts &prepared) {
    LoadedData data;
    utils::load_something<float, FloatRowMat>(FLAGS_raw_base_file.c_str(), data.raw_base);
    utils::load_something<float, FloatRowMat>(FLAGS_raw_query_file.c_str(), data.raw_query);
    utils::load_something<float, FloatRowMat>(FLAGS_pca_base_file.c_str(), data.pca_base);
    utils::load_something<float, FloatRowMat>(FLAGS_pca_query_file.c_str(), data.pca_query);
    utils::load_something<float, FloatRowMat>(FLAGS_pca_centroids_file.c_str(), data.pca_centroids);
    utils::load_something<float, FloatRowMat>(FLAGS_pca_variance_file.c_str(), data.pca_variance);
    utils::load_something<PID, UintRowMat>(FLAGS_cluster_ids_file.c_str(), data.cluster_ids);
    utils::load_something<PID, UintRowMat>(FLAGS_fixed_probes_file.c_str(), data.fixed_probes);
    utils::load_something<float, FloatRowMat>(prepared.head_base.c_str(), data.prepared_head_base);
    utils::load_something<float, FloatRowMat>(prepared.head_query.c_str(), data.prepared_head_query);
    utils::load_something<float, FloatRowMat>(prepared.head_centroids.c_str(),
                                               data.prepared_head_centroids);
    utils::load_something<PID, UintRowMat>(prepared.fixed_probes.c_str(), data.prepared_fixed_probes);
    data.mean = load_f64bin(prepared.mean);
    data.retained_operator = load_f64bin(prepared.retained_operator);
    data.raw_centroids = load_f64bin(prepared.raw_centroids);
    data.prepared_base_tail_sq_exact = load_dense_bin<double>(prepared.base_tail_sq_exact);
    data.prepared_base_tail_norm_deployed =
        load_dense_bin<float>(prepared.base_tail_norm_deployed);
    data.prepared_query_probe_tail_sq_exact =
        load_dense_bin<double>(prepared.query_probe_tail_sq_exact);
    data.prepared_query_probe_tail_sq_deployed =
        load_dense_bin<float>(prepared.query_probe_tail_sq_deployed);

    CHECK_EQ(data.raw_base.rows(), static_cast<Eigen::Index>(kN));
    CHECK_EQ(data.raw_base.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.raw_query.cols(), static_cast<Eigen::Index>(kD));
    CHECK_GE(data.raw_query.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.pca_base.rows(), data.raw_base.rows());
    CHECK_EQ(data.pca_base.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.pca_query.rows(), data.raw_query.rows());
    CHECK_EQ(data.pca_query.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.pca_centroids.rows(), static_cast<Eigen::Index>(kK));
    CHECK_EQ(data.pca_centroids.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.pca_variance.rows(), 1);
    CHECK_EQ(data.pca_variance.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.cluster_ids.rows(), static_cast<Eigen::Index>(kN));
    CHECK_EQ(data.cluster_ids.cols(), 1);
    CHECK_EQ(data.fixed_probes.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.fixed_probes.cols(), static_cast<Eigen::Index>(kNProbe));
    CHECK_EQ(data.prepared_head_base.rows(), static_cast<Eigen::Index>(kN));
    CHECK_EQ(data.prepared_head_base.cols(), static_cast<Eigen::Index>(kProjectedD));
    CHECK_EQ(data.prepared_head_query.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.prepared_head_query.cols(), static_cast<Eigen::Index>(kProjectedD));
    CHECK_EQ(data.prepared_head_centroids.rows(), static_cast<Eigen::Index>(kK));
    CHECK_EQ(data.prepared_head_centroids.cols(), static_cast<Eigen::Index>(kProjectedD));
    CHECK_EQ(data.prepared_fixed_probes.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.prepared_fixed_probes.cols(), static_cast<Eigen::Index>(kNProbe));
    CHECK_EQ(data.mean.rows(), 1);
    CHECK_EQ(data.mean.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.retained_operator.rows(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.retained_operator.cols(), static_cast<Eigen::Index>(kProjectedD));
    CHECK_EQ(data.raw_centroids.rows(), static_cast<Eigen::Index>(kK));
    CHECK_EQ(data.raw_centroids.cols(), static_cast<Eigen::Index>(kD));
    CHECK_EQ(data.prepared_base_tail_sq_exact.rows(), static_cast<Eigen::Index>(kN));
    CHECK_EQ(data.prepared_base_tail_sq_exact.cols(), 1);
    CHECK_EQ(data.prepared_base_tail_norm_deployed.rows(), static_cast<Eigen::Index>(kN));
    CHECK_EQ(data.prepared_base_tail_norm_deployed.cols(), 1);
    CHECK_EQ(data.prepared_query_probe_tail_sq_exact.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.prepared_query_probe_tail_sq_exact.cols(), static_cast<Eigen::Index>(kNProbe));
    CHECK_EQ(data.prepared_query_probe_tail_sq_deployed.rows(), static_cast<Eigen::Index>(kQueries));
    CHECK_EQ(data.prepared_query_probe_tail_sq_deployed.cols(), static_cast<Eigen::Index>(kNProbe));
    CHECK(data.raw_base.allFinite());
    CHECK(data.raw_query.allFinite());
    CHECK(data.pca_base.allFinite());
    CHECK(data.pca_query.allFinite());
    CHECK(data.pca_centroids.allFinite());
    CHECK(data.mean.allFinite());
    CHECK(data.retained_operator.allFinite());
    CHECK(data.raw_centroids.allFinite());
    return data;
}

struct PreparationValidation {
    double operator_orthogonality_frobenius_per_d = 0;
    double head_max_absolute_difference = 0;
    double base_tail_exact_max_absolute_difference = 0;
    uint64_t base_tail_deployed_bit_mismatches = 0;
    double query_tail_materialized_max_absolute_difference = 0;
    double query_tail_derived_max_absolute_difference = 0;
    uint64_t query_tail_clamp_count = 0;
    uint64_t query_tail_deployed_bit_mismatches = 0;
};

struct TailState {
    std::vector<double> base_exact_sq;
    std::vector<float> base_deployed_norm;
    DoubleRowMat query_probe_exact_sq;
    Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> query_probe_deployed_sq;
};

TailState validate_preparation(const LoadedData &data, PreparationValidation &validation) {
    const DoubleRowMat gram = data.retained_operator.transpose() * data.retained_operator;
    const DoubleRowMat identity = DoubleRowMat::Identity(kProjectedD, kProjectedD);
    validation.operator_orthogonality_frobenius_per_d =
        (gram - identity).norm() / static_cast<double>(kProjectedD);
    CHECK_LE(validation.operator_orthogonality_frobenius_per_d,
             kOperatorOrthogonalityTolerance);

    for (Eigen::Index row = 0; row < data.prepared_head_base.rows(); ++row) {
        for (Eigen::Index col = 0; col < data.prepared_head_base.cols(); ++col) {
            validation.head_max_absolute_difference = std::max(
                validation.head_max_absolute_difference,
                std::abs(static_cast<double>(data.prepared_head_base(row, col)) -
                         static_cast<double>(data.pca_base(row, col))));
        }
    }
    for (Eigen::Index row = 0; row < data.prepared_head_query.rows(); ++row) {
        for (Eigen::Index col = 0; col < data.prepared_head_query.cols(); ++col) {
            validation.head_max_absolute_difference = std::max(
                validation.head_max_absolute_difference,
                std::abs(static_cast<double>(data.prepared_head_query(row, col)) -
                         static_cast<double>(data.pca_query(row, col))));
        }
    }
    for (Eigen::Index row = 0; row < data.prepared_head_centroids.rows(); ++row) {
        for (Eigen::Index col = 0; col < data.prepared_head_centroids.cols(); ++col) {
            validation.head_max_absolute_difference = std::max(
                validation.head_max_absolute_difference,
                std::abs(static_cast<double>(data.prepared_head_centroids(row, col)) -
                         static_cast<double>(data.pca_centroids(row, col))));
        }
    }
    CHECK_EQ(validation.head_max_absolute_difference, 0.0)
        << "prepared PCA heads are not exact slices of the frozen historical coordinates";
    CHECK_EQ(data.fixed_probes, data.prepared_fixed_probes)
        << "prepared fixed probes differ from the frozen probe file";

    TailState tails;
    tails.base_exact_sq.resize(kN);
    tails.base_deployed_norm.resize(kN);
    for (size_t data_id = 0; data_id < kN; ++data_id) {
        const PID cluster_id = data.cluster_ids(static_cast<Eigen::Index>(data_id), 0);
        CHECK_LT(cluster_id, kK);
        const double exact_sq = squared_l2_float64_range(
            data.pca_base.row(static_cast<Eigen::Index>(data_id)),
            data.pca_centroids.row(cluster_id), kProjectedD, kD);
        const float deployed_norm = static_cast<float>(std::sqrt(exact_sq));
        tails.base_exact_sq[data_id] = exact_sq;
        tails.base_deployed_norm[data_id] = deployed_norm;
        validation.base_tail_exact_max_absolute_difference = std::max(
            validation.base_tail_exact_max_absolute_difference,
            std::abs(exact_sq - data.prepared_base_tail_sq_exact(
                                    static_cast<Eigen::Index>(data_id), 0)));
        if (std::bit_cast<uint32_t>(deployed_norm) !=
            std::bit_cast<uint32_t>(data.prepared_base_tail_norm_deployed(
                static_cast<Eigen::Index>(data_id), 0))) {
            ++validation.base_tail_deployed_bit_mismatches;
        }
    }
    CHECK_LE(validation.base_tail_exact_max_absolute_difference, 1e-15)
        << "prepared exact base-tail values differ from independent recomputation";
    CHECK_EQ(validation.base_tail_deployed_bit_mismatches, 0U)
        << "prepared deployed base-tail norms differ in float32 bits";

    tails.query_probe_exact_sq = DoubleRowMat(kQueries, kNProbe);
    tails.query_probe_deployed_sq =
        Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>(kQueries, kNProbe);
    for (size_t query = 0; query < kQueries; ++query) {
        std::unordered_set<PID> seen_probes;
        for (size_t probe = 0; probe < kNProbe; ++probe) {
            const PID cluster_id = data.fixed_probes(query, probe);
            CHECK_LT(cluster_id, kK);
            CHECK(seen_probes.insert(cluster_id).second)
                << "duplicate probe cluster " << cluster_id << " for query " << query;
            const double pca_head_sq = squared_l2_float64_range(
                data.pca_query.row(query), data.pca_centroids.row(cluster_id), 0, kProjectedD);
            const double materialized_tail_sq = squared_l2_float64_range(
                data.pca_query.row(query), data.pca_centroids.row(cluster_id), kProjectedD, kD);
            const double raw_full_sq = squared_l2_float64_range(
                data.raw_query.row(query), data.raw_centroids.row(cluster_id), 0, kD);
            double derived_tail_sq = raw_full_sq - pca_head_sq;
            if (derived_tail_sq < 0) {
                CHECK_GE(derived_tail_sq, -kTailTolerance * std::max(1.0, raw_full_sq))
                    << "invalid negative derived query-tail norm for query " << query
                    << " probe " << probe;
                derived_tail_sq = 0;
                ++validation.query_tail_clamp_count;
            }
            const double allowed = kTailTolerance * std::max(1.0, std::abs(materialized_tail_sq));
            validation.query_tail_derived_max_absolute_difference = std::max(
                validation.query_tail_derived_max_absolute_difference,
                std::abs(derived_tail_sq - materialized_tail_sq));
            CHECK_LE(std::abs(derived_tail_sq - materialized_tail_sq), allowed)
                << "raw-derived query tail does not match the materialized historical PCA tail"
                << " for query " << query << " probe " << probe;
            const float deployed_tail_sq = static_cast<float>(derived_tail_sq);
            tails.query_probe_exact_sq(query, probe) = materialized_tail_sq;
            tails.query_probe_deployed_sq(query, probe) = deployed_tail_sq;
            validation.query_tail_materialized_max_absolute_difference = std::max(
                validation.query_tail_materialized_max_absolute_difference,
                std::abs(materialized_tail_sq -
                         data.prepared_query_probe_tail_sq_exact(query, probe)));
            if (std::bit_cast<uint32_t>(deployed_tail_sq) !=
                std::bit_cast<uint32_t>(data.prepared_query_probe_tail_sq_deployed(query, probe))) {
                ++validation.query_tail_deployed_bit_mismatches;
            }
        }
    }
    CHECK_LE(validation.query_tail_materialized_max_absolute_difference, 1e-15)
        << "prepared exact query-tail values differ from independent recomputation";
    CHECK_EQ(validation.query_tail_deployed_bit_mismatches, 0U)
        << "prepared deployed query-tail values differ in float32 bits";
    return tails;
}

struct QueryReference {
    std::vector<PID> candidate_ids;
    std::vector<PID> candidate_clusters;
    std::vector<uint32_t> candidate_probe_positions;
    std::vector<double> exact_distances;
    uint64_t candidate_ids_digest = kFnv1aOffsetBasis;
    uint64_t exact_id_distance_digest = kFnv1aOffsetBasis;
    PID exact_best_id = 0;
    std::vector<PID> exact_topk_ids;
    double exact_topk_boundary_distance = std::numeric_limits<double>::quiet_NaN();
    double exact_first_outside_distance = std::numeric_limits<double>::quiet_NaN();
    double exact_boundary_gap = std::numeric_limits<double>::quiet_NaN();
};

struct CandidateInventory {
    std::string sha256;
    uint64_t total = 0;
    size_t min_per_query = std::numeric_limits<size_t>::max();
    size_t max_per_query = 0;
    uint64_t duplicate_count = 0;
};

std::vector<QueryReference> build_query_references(const LoadedData &data,
                                                   CandidateInventory &inventory) {
    std::vector<std::vector<PID>> cluster_members(kK);
    for (size_t data_id = 0; data_id < kN; ++data_id) {
        const PID cluster = data.cluster_ids(static_cast<Eigen::Index>(data_id), 0);
        CHECK_LT(cluster, kK);
        cluster_members[cluster].push_back(static_cast<PID>(data_id));
    }

    Sha256 candidate_hash;
    std::vector<QueryReference> references;
    references.reserve(kQueries);
    for (size_t query = 0; query < kQueries; ++query) {
        QueryReference reference;
        size_t candidate_count = 0;
        for (size_t probe = 0; probe < kNProbe; ++probe) {
            candidate_count += cluster_members[data.fixed_probes(query, probe)].size();
        }
        CHECK_GE(candidate_count, kTopK);
        reference.candidate_ids.reserve(candidate_count);
        reference.candidate_clusters.reserve(candidate_count);
        reference.candidate_probe_positions.reserve(candidate_count);
        reference.exact_distances.reserve(candidate_count);
        std::unordered_set<PID> seen_ids;
        const auto exact_query = data.raw_query.row(query);
        for (size_t probe = 0; probe < kNProbe; ++probe) {
            const PID cluster = data.fixed_probes(query, probe);
            PID previous_id = 0;
            bool have_previous = false;
            for (PID data_id : cluster_members[cluster]) {
                CHECK(!have_previous || previous_id < data_id)
                    << "cluster members are not in ascending base-row order";
                have_previous = true;
                previous_id = data_id;
                if (!seen_ids.insert(data_id).second) {
                    ++inventory.duplicate_count;
                    LOG(FATAL) << "duplicate candidate " << data_id << " for query " << query;
                }
                reference.candidate_ids.push_back(data_id);
                reference.candidate_clusters.push_back(cluster);
                reference.candidate_probe_positions.push_back(static_cast<uint32_t>(probe));
                const double exact = squared_l2_float64_range(
                    exact_query, data.raw_base.row(data_id), 0, kD);
                CHECK(finite_double_bits(exact));
                reference.exact_distances.push_back(exact);
            }
        }
        CHECK_EQ(reference.candidate_ids.size(), candidate_count);

        candidate_hash.append_u32_le(static_cast<uint32_t>(query));
        candidate_hash.append_u64_le(static_cast<uint64_t>(candidate_count));
        for (PID data_id : reference.candidate_ids) {
            candidate_hash.append_u32_le(data_id);
        }
        inventory.total += candidate_count;
        inventory.min_per_query = std::min(inventory.min_per_query, candidate_count);
        inventory.max_per_query = std::max(inventory.max_per_query, candidate_count);

        std::vector<size_t> exact_order(candidate_count);
        std::iota(exact_order.begin(), exact_order.end(), 0);
        std::sort(exact_order.begin(), exact_order.end(), [&](size_t lhs, size_t rhs) {
            if (reference.exact_distances[lhs] != reference.exact_distances[rhs]) {
                return reference.exact_distances[lhs] < reference.exact_distances[rhs];
            }
            return reference.candidate_ids[lhs] < reference.candidate_ids[rhs];
        });
        reference.exact_best_id = reference.candidate_ids[exact_order.front()];
        reference.exact_topk_ids.reserve(kTopK);
        for (size_t rank = 0; rank < kTopK; ++rank) {
            reference.exact_topk_ids.push_back(reference.candidate_ids[exact_order[rank]]);
        }
        reference.exact_topk_boundary_distance =
            reference.exact_distances[exact_order[kTopK - 1]];
        reference.exact_first_outside_distance =
            reference.exact_distances[exact_order[kTopK]];
        reference.exact_boundary_gap = reference.exact_first_outside_distance -
                                       reference.exact_topk_boundary_distance;

        std::vector<size_t> id_order(candidate_count);
        std::iota(id_order.begin(), id_order.end(), 0);
        std::sort(id_order.begin(), id_order.end(), [&](size_t lhs, size_t rhs) {
            return reference.candidate_ids[lhs] < reference.candidate_ids[rhs];
        });
        fnv1a_append_u64(reference.candidate_ids_digest, candidate_count);
        fnv1a_append_u64(reference.exact_id_distance_digest, candidate_count);
        for (size_t position : id_order) {
            const PID data_id = reference.candidate_ids[position];
            fnv1a_append_u32(reference.candidate_ids_digest, data_id);
            fnv1a_append_u32(reference.exact_id_distance_digest, data_id);
            fnv1a_append_u64(reference.exact_id_distance_digest,
                             std::bit_cast<uint64_t>(reference.exact_distances[position]));
        }
        references.push_back(std::move(reference));
    }
    inventory.sha256 = candidate_hash.hex_digest();
    CHECK_EQ(inventory.sha256, kExpectedCandidateSha256);
    CHECK_EQ(inventory.total, kExpectedCandidateTotal);
    CHECK_EQ(inventory.min_per_query, kExpectedCandidateMin);
    CHECK_EQ(inventory.max_per_query, kExpectedCandidateMax);
    CHECK_EQ(inventory.duplicate_count, 0U);
    return references;
}

void validate_candidate_stream(const std::filesystem::path &path,
                               const std::vector<QueryReference> &references) {
    CHECK_EQ(sha256_file(path.string()), kExpectedCandidateSha256)
        << "prepared candidate stream hash differs from the frozen inventory";
    std::ifstream input(path, std::ios::binary);
    CHECK(input.is_open());
    for (size_t query = 0; query < references.size(); ++query) {
        uint32_t observed_query = 0;
        uint64_t observed_count = 0;
        input.read(reinterpret_cast<char *>(&observed_query), sizeof(observed_query));
        input.read(reinterpret_cast<char *>(&observed_count), sizeof(observed_count));
        CHECK(input.good()) << "truncated prepared candidate stream";
        CHECK_EQ(observed_query, query);
        CHECK_EQ(observed_count, references[query].candidate_ids.size());
        for (PID expected_id : references[query].candidate_ids) {
            int32_t observed_id = -1;
            input.read(reinterpret_cast<char *>(&observed_id), sizeof(observed_id));
            CHECK(input.good()) << "truncated prepared candidate stream";
            CHECK_GE(observed_id, 0);
            CHECK_EQ(static_cast<PID>(observed_id), expected_id)
                << "prepared candidate order drift for query " << query;
        }
    }
    CHECK_EQ(input.peek(), std::char_traits<char>::eof())
        << "trailing bytes in prepared candidate stream";
}

void write_query_references(const std::string &path,
                            const std::vector<QueryReference> &references) {
    std::ofstream output(path, std::ios::trunc);
    CHECK(output.is_open());
    output << std::setprecision(17);
    output << "query,candidate_count,candidate_ids_fnv1a64,exact_id_distance_fnv1a64,"
              "exact_best_id,exact_topk_used,exact_topk_ids,exact_topk_boundary_distance,"
              "exact_first_outside_distance,exact_boundary_gap,exact_reference_scope\n";
    for (size_t query = 0; query < references.size(); ++query) {
        const auto &reference = references[query];
        output << query << ',' << reference.candidate_ids.size() << ','
               << uint64_hex(reference.candidate_ids_digest) << ','
               << uint64_hex(reference.exact_id_distance_digest) << ','
               << reference.exact_best_id << ',' << reference.exact_topk_ids.size() << ','
               << csv_string(pipe_separated_ids(reference.exact_topk_ids)) << ','
               << reference.exact_topk_boundary_distance << ','
               << reference.exact_first_outside_distance << ','
               << reference.exact_boundary_gap << ',' << kExactScope << '\n';
    }
    CHECK(output.good());
}

uint64_t estimate_digest(const std::vector<PID> &ids,
                         const std::vector<double> &estimates) {
    CHECK_EQ(ids.size(), estimates.size());
    std::vector<size_t> id_order(ids.size());
    std::iota(id_order.begin(), id_order.end(), 0);
    std::sort(id_order.begin(), id_order.end(), [&](size_t lhs, size_t rhs) {
        return ids[lhs] < ids[rhs];
    });
    uint64_t digest = kFnv1aOffsetBasis;
    fnv1a_append_u64(digest, ids.size());
    for (size_t position : id_order) {
        fnv1a_append_u32(digest, ids[position]);
        fnv1a_append_u64(digest, std::bit_cast<uint64_t>(estimates[position]));
    }
    return digest;
}

struct ComponentSummary {
    double projection_bias = 0;
    double projection_mae = 0;
    double projection_rmse = 0;
    double summary_bias = 0;
    double summary_mae = 0;
    double summary_rmse = 0;
    double projection_summary_covariance = 0;
    double identity_max_abs = 0;
};

ComponentSummary component_summary(const std::vector<double> &exact,
                                   const std::vector<double> &dp,
                                   const std::vector<double> &estimate) {
    CHECK_EQ(exact.size(), dp.size());
    CHECK_EQ(exact.size(), estimate.size());
    ComponentSummary result;
    long double projection_sum = 0;
    long double projection_abs_sum = 0;
    long double projection_sq_sum = 0;
    long double summary_sum = 0;
    long double summary_abs_sum = 0;
    long double summary_sq_sum = 0;
    long double product_sum = 0;
    for (size_t i = 0; i < exact.size(); ++i) {
        const double projection = dp[i] - exact[i];
        const double summary = estimate[i] - dp[i];
        const double total = estimate[i] - exact[i];
        projection_sum += projection;
        projection_abs_sum += std::abs(projection);
        projection_sq_sum += projection * projection;
        summary_sum += summary;
        summary_abs_sum += std::abs(summary);
        summary_sq_sum += summary * summary;
        product_sum += projection * summary;
        result.identity_max_abs = std::max(
            result.identity_max_abs, std::abs(total - (projection + summary)));
        CHECK_LE(std::abs(total - (projection + summary)),
                 1e-10 * std::max(1.0, std::abs(total)));
    }
    const long double count = exact.size();
    result.projection_bias = static_cast<double>(projection_sum / count);
    result.projection_mae = static_cast<double>(projection_abs_sum / count);
    result.projection_rmse = std::sqrt(static_cast<double>(projection_sq_sum / count));
    result.summary_bias = static_cast<double>(summary_sum / count);
    result.summary_mae = static_cast<double>(summary_abs_sum / count);
    result.summary_rmse = std::sqrt(static_cast<double>(summary_sq_sum / count));
    result.projection_summary_covariance = static_cast<double>(
        product_sum / count - (projection_sum / count) * (summary_sum / count));
    return result;
}

void write_metric_row(std::ofstream &output, const char *arm, const char *distance_value,
                      const char *tail_treatment, size_t query,
                      const QueryReference &reference, const std::vector<double> &dp,
                      const std::vector<double> &estimate) {
    const MetricSummary errors = summarize_errors(reference.exact_distances, estimate);
    const RankingSummary ranking = ranking_summary(
        reference.exact_distances, estimate, reference.candidate_ids);
    const ComponentSummary components = component_summary(
        reference.exact_distances, dp, estimate);
    output << arm << ',' << distance_value << ',' << tail_treatment << ',' << kExactScope << ','
           << query << ',' << reference.candidate_ids.size() << ',' << errors.finite_count << ','
           << errors.nonfinite_count << ',' << errors.bias << ',' << errors.mae << ','
           << errors.rmse << ',' << errors.relative_p50 << ',' << errors.relative_p90 << ','
           << errors.relative_p99 << ',' << ranking.topk_used << ',' << ranking.topk_agreement << ','
           << ranking.exact_best_estimated_rank << ',' << ranking.boundary_inversions << ','
           << ranking.boundary_pairs << ',' << ranking.boundary_inversion_rate << ','
           << uint64_hex(reference.candidate_ids_digest) << ','
           << uint64_hex(reference.exact_id_distance_digest) << ','
           << uint64_hex(estimate_digest(reference.candidate_ids, estimate)) << ','
           << components.projection_bias << ',' << components.projection_mae << ','
           << components.projection_rmse << ',' << components.summary_bias << ','
           << components.summary_mae << ',' << components.summary_rmse << ','
           << components.projection_summary_covariance << ',' << components.identity_max_abs << '\n';
}

void write_query_metrics(const std::string &path, const std::string &candidate_path,
                         const LoadedData &data,
                         const TailState &tails,
                         const std::vector<QueryReference> &references) {
    std::ofstream output(path, std::ios::trunc);
    std::ofstream candidate_output(candidate_path, std::ios::trunc);
    CHECK(output.is_open());
    CHECK(candidate_output.is_open());
    output << std::setprecision(17);
    candidate_output << std::setprecision(17);
    output << "arm,distance_value,tail_treatment,distance_reference_scope,query,candidate_count,"
              "finite_count,nonfinite_count,bias,mae,rmse,abs_relative_eps1e-12_p50,"
              "abs_relative_eps1e-12_p90,abs_relative_eps1e-12_p99,topk_used,"
              "fixed_candidate_topk_agreement,exact_best_estimated_rank,"
              "strict_exact_topk_vs_outside_boundary_inversions,boundary_pairs,"
              "strict_boundary_inversion_rate,candidate_ids_fnv1a64,exact_id_distance_fnv1a64,"
              "estimate_id_distance_fnv1a64,e_projection_bias,e_projection_mae,e_projection_rmse,"
              "e_summary_bias,e_summary_mae,e_summary_rmse,"
              "e_projection_e_summary_population_covariance,error_sum_identity_max_abs\n";
    candidate_output
        << "query,probe_position,cluster_id,candidate_position,base_id,D0,DP_none,DS_none,"
           "DP_norm,DS_norm,e_projection_none,e_summary_none,e_total_none,"
           "e_projection_norm,e_summary_norm,e_total_norm,error_sum_identity_none,"
           "error_sum_identity_norm\n";
    for (size_t query = 0; query < references.size(); ++query) {
        const auto &reference = references[query];
        std::vector<double> none_dp;
        std::vector<double> norm_dp;
        std::vector<double> norm_ds;
        none_dp.reserve(reference.candidate_ids.size());
        norm_dp.reserve(reference.candidate_ids.size());
        norm_ds.reserve(reference.candidate_ids.size());
        for (size_t position = 0; position < reference.candidate_ids.size(); ++position) {
            const PID data_id = reference.candidate_ids[position];
            const uint32_t probe = reference.candidate_probe_positions[position];
            CHECK_EQ(reference.candidate_clusters[position], data.fixed_probes(query, probe));
            const double head_sq = squared_l2_float64_range(
                data.pca_query.row(query), data.pca_base.row(data_id), 0, kProjectedD);
            const double exact_tail = tails.base_exact_sq[data_id] +
                                      tails.query_probe_exact_sq(query, probe);
            const float base_norm = tails.base_deployed_norm[data_id];
            const float base_sq = base_norm * base_norm;
            const float query_sq = tails.query_probe_deployed_sq(query, probe);
            const float deployed_tail = base_sq + query_sq;
            const double dp_value = head_sq + exact_tail;
            const double ds_value = head_sq + static_cast<double>(deployed_tail);
            CHECK(finite_double_bits(head_sq));
            CHECK(finite_double_bits(dp_value));
            CHECK(finite_double_bits(ds_value));
            const double d0 = reference.exact_distances[position];
            const double e_projection_none = head_sq - d0;
            const double e_summary_none = head_sq - head_sq;
            const double e_total_none = head_sq - d0;
            const double e_projection_norm = dp_value - d0;
            const double e_summary_norm = ds_value - dp_value;
            const double e_total_norm = ds_value - d0;
            const double identity_none = std::abs(
                e_total_none - (e_projection_none + e_summary_none));
            const double identity_norm = std::abs(
                e_total_norm - (e_projection_norm + e_summary_norm));
            CHECK_LE(identity_none, 1e-10 * std::max(1.0, std::abs(e_total_none)));
            CHECK_LE(identity_norm, 1e-10 * std::max(1.0, std::abs(e_total_norm)));
            candidate_output << query << ',' << probe << ','
                             << reference.candidate_clusters[position] << ',' << position << ','
                             << data_id << ',' << d0 << ',' << head_sq << ',' << head_sq << ','
                             << dp_value << ',' << ds_value << ',' << e_projection_none << ','
                             << e_summary_none << ',' << e_total_none << ','
                             << e_projection_norm << ',' << e_summary_norm << ',' << e_total_norm
                             << ',' << identity_none << ',' << identity_norm << '\n';
            none_dp.push_back(head_sq);
            norm_dp.push_back(dp_value);
            norm_ds.push_back(ds_value);
        }
        const std::vector<double> none_ds = none_dp;
        CHECK(std::equal(none_dp.begin(), none_dp.end(), none_ds.begin(),
                         [](double lhs, double rhs) {
                             return std::bit_cast<uint64_t>(lhs) == std::bit_cast<uint64_t>(rhs);
                         }));
        write_metric_row(output, "oracle576_none", "DP", "none", query,
                         reference, none_dp, none_dp);
        write_metric_row(output, "oracle576_none", "DS", "none", query,
                         reference, none_dp, none_ds);
        write_metric_row(output, "oracle576_norm", "DP",
                         "exact_float64_combined_tail_norm", query,
                         reference, norm_dp, norm_dp);
        write_metric_row(output, "oracle576_norm", "DS",
                         "deployed_float32_combined_tail_norm", query,
                         reference, norm_dp, norm_ds);
    }
    CHECK(output.good());
    CHECK(candidate_output.good());
}

std::string sha256_array_float64_vector(const DoubleRowMat &values) {
    CHECK_EQ(values.rows(), 1);
    static_assert(std::endian::native == std::endian::little,
                  "array hashes require a little-endian host for this registered run");
    Sha256 digest;
    constexpr char dtype[] = "float64";
    digest.update(dtype, sizeof(dtype) - 1);
    digest.append_u32_le(1);
    digest.append_u64_le(static_cast<uint64_t>(values.cols()));
    digest.update(values.data(), static_cast<size_t>(values.size()) * sizeof(double));
    return digest.hex_digest();
}

struct FrozenArtifactHash {
    std::string expected;
    std::string observed;
};

using FrozenHashes = std::vector<std::pair<std::string, FrozenArtifactHash>>;

FrozenHashes validate_frozen_hashes(const LoadedData &data,
                                    const boost::property_tree::ptree &prepared_manifest) {
    FrozenHashes hashes{
        {"raw_base_file", {"bd31f1332e60205472a50cf83a7c4c8cf5ecf5ffd6145cb4e8c44d591f8b2066", ""}},
        {"raw_query_file", {"0d1d620049de12da455ed7201e97cbab372c4d54d0e6dedbc8c503f62c911299", ""}},
        {"historical_pca_base_file", {"a027be4e9942c7935ba4c7184eac09b4ad2d2c6fbe561ed9a598e66933b20671", ""}},
        {"historical_pca_query_file", {"8f888359b836b3a5f498d3bf15bf63744024e320f99fe668c3953db2535cf974", ""}},
        {"historical_pca_centroids_file", {"48af2216744f9bb39fd7dccf2e0358aa705a4647227adb777796623c676674db", ""}},
        {"cluster_assignments_file", {"c466b5685dd4ef12f42f1d7fa304f42b2c9989df12190c84b8bb4c0a29618eb1", ""}},
        {"historical_pca_variance_file", {"20345de79dbd6ead9728c2c9abdbdb3f12e4f0ad449122f586d87ed3036b9c35", ""}},
        {"recovered_mean_array", {"9d70b61994ad42c4d35734a786b3814493f8da721cfbfd19943b1b9875167114", ""}},
        {"recovered_full_operator_array", {"5e5de629a3bd95d1b5fe72f29db495113b1313e106ea3caad56992a526d58bdb", ""}},
        {"retained_operator_array", {"b3d467728c62d2540f1d34309a78a8419ecebeafce9e3a07319af4eb35623b53", ""}},
        {"fixed_probes_file", {"a568c32ff9555aaef9df68e49b65a64f895fb5e37c5aefdf63ff0102732e7b80", ""}},
        {"fixed_probes_array", {"c0e1ed9424a8a287cba9d85dabb2732c89ad132485ae431432c55725e674ebfc", ""}},
    };
    hashes[0].second.observed = sha256_file(FLAGS_raw_base_file);
    hashes[1].second.observed = sha256_file(FLAGS_raw_query_file);
    hashes[2].second.observed = sha256_file(FLAGS_pca_base_file);
    hashes[3].second.observed = sha256_file(FLAGS_pca_query_file);
    hashes[4].second.observed = sha256_file(FLAGS_pca_centroids_file);
    hashes[5].second.observed = sha256_file(FLAGS_cluster_ids_file);
    hashes[6].second.observed = sha256_file(FLAGS_pca_variance_file);
    hashes[7].second.observed = sha256_array_float64_vector(data.mean);
    hashes[8].second.observed = prepared_manifest.get<std::string>(
        "recovered_mapping.full_operator_array_sha256");
    hashes[9].second.observed = sha256_array_float64(data.retained_operator);
    hashes[10].second.observed = sha256_file(FLAGS_fixed_probes_file);
    hashes[11].second.observed = sha256_array_int32(data.fixed_probes);
    for (const auto &[name, identity] : hashes) {
        CHECK_EQ(identity.observed, identity.expected)
            << "frozen artifact hash mismatch for " << name;
    }
    CHECK_EQ(prepared_manifest.get<std::string>("recovered_mapping.mean_array_sha256"),
             hashes[7].second.expected);
    CHECK_EQ(prepared_manifest.get<std::string>(
                 "recovered_mapping.retained_operator_array_sha256"),
             hashes[9].second.expected);
    return hashes;
}

void write_manifest(const std::string &path, const std::string &query_metrics_path,
                    const std::string &query_reference_path,
                    const std::string &candidate_distances_path,
                    const FrozenHashes &frozen_hashes,
                    const CandidateInventory &candidate_inventory,
                    const PreparationValidation &validation,
                    const PreparedArtifacts &prepared,
                    const boost::property_tree::ptree &prepared_manifest) {
    std::ofstream output(path, std::ios::trunc);
    CHECK(output.is_open());
    output << std::setprecision(17);
    output << "{\n"
           << "  \"schema_version\": \"saq_lp0_gate_a_oracle_v1\",\n"
           << "  \"status\": \"complete\",\n"
           << "  \"configuration\": {\n"
           << "    \"dataset\": \"gist_sample50k\",\n"
           << "    \"N\": " << kN << ",\n"
           << "    \"D\": " << kD << ",\n"
           << "    \"d\": " << kProjectedD << ",\n"
           << "    \"K\": " << kK << ",\n"
           << "    \"queries\": " << kQueries << ",\n"
           << "    \"fixed_probes_per_query\": " << kNProbe << ",\n"
           << "    \"topk\": " << kTopK << ",\n"
           << "    \"metric\": \"squared_L2\",\n"
           << "    \"accumulation\": "
           << "\"historical_pca_float32_coordinates_float64_accumulation\"\n"
           << "  },\n"
           << "  \"frozen_artifacts\": {\n";
    for (size_t i = 0; i < frozen_hashes.size(); ++i) {
        const auto &[name, identity] = frozen_hashes[i];
        output << "    " << json_string(name) << ": {\"expected_sha256\": "
               << json_string(identity.expected) << ", \"observed_sha256\": "
               << json_string(identity.observed) << "}"
               << (i + 1 == frozen_hashes.size() ? "\n" : ",\n");
    }
    output << "  },\n"
           << "  \"candidate_inventory\": {\n"
           << "    \"expected_sha256\": " << json_string(kExpectedCandidateSha256) << ",\n"
           << "    \"observed_sha256\": " << json_string(candidate_inventory.sha256) << ",\n"
           << "    \"expected_total\": " << kExpectedCandidateTotal << ",\n"
           << "    \"observed_total\": " << candidate_inventory.total << ",\n"
           << "    \"expected_min_per_query\": " << kExpectedCandidateMin << ",\n"
           << "    \"observed_min_per_query\": " << candidate_inventory.min_per_query << ",\n"
           << "    \"expected_max_per_query\": " << kExpectedCandidateMax << ",\n"
           << "    \"observed_max_per_query\": " << candidate_inventory.max_per_query << ",\n"
           << "    \"duplicate_count\": " << candidate_inventory.duplicate_count << "\n"
           << "  },\n"
           << "  \"tail_contract\": {\n"
           << "    \"base_sidecar\": \"float32_L2_norm_squared_in_float32\",\n"
           << "    \"query_sidecar\": "
           << "\"float32_squared_norm_from_raw_full_minus_float64_PCA_head\",\n"
           << "    \"tail_addition\": \"float32_base_sq_plus_query_sq_before_float64_head\",\n"
           << "    \"clamp_relative_scale\": " << kTailTolerance << ",\n"
           << "    \"materialized_crosscheck_relative_absolute_tolerance\": "
           << kTailTolerance << "\n"
           << "  },\n"
           << "  \"preparation_validation\": {\n"
           << "    \"prepared_manifest_path\": " << json_string(FLAGS_prepared_manifest) << ",\n"
           << "    \"prepared_manifest_sha256\": "
           << json_string(sha256_file(FLAGS_prepared_manifest)) << ",\n"
           << "    \"prepared_schema_version\": "
           << json_string(prepared_manifest.get<std::string>("schema_version")) << ",\n"
           << "    \"retained_operator_file\": "
           << json_string(prepared.retained_operator.string()) << ",\n"
           << "    \"operator_orthogonality_frobenius_per_d\": "
           << validation.operator_orthogonality_frobenius_per_d << ",\n"
           << "    \"operator_orthogonality_threshold\": "
           << kOperatorOrthogonalityTolerance << ",\n"
           << "    \"head_max_absolute_difference\": "
           << validation.head_max_absolute_difference << ",\n"
           << "    \"base_tail_exact_max_absolute_difference\": "
           << validation.base_tail_exact_max_absolute_difference << ",\n"
           << "    \"base_tail_deployed_bit_mismatches\": "
           << validation.base_tail_deployed_bit_mismatches << ",\n"
           << "    \"query_tail_materialized_max_absolute_difference\": "
           << validation.query_tail_materialized_max_absolute_difference << ",\n"
           << "    \"query_tail_derived_vs_materialized_max_absolute_difference\": "
           << validation.query_tail_derived_max_absolute_difference << ",\n"
           << "    \"query_tail_clamp_count\": " << validation.query_tail_clamp_count << ",\n"
           << "    \"query_tail_deployed_bit_mismatches\": "
           << validation.query_tail_deployed_bit_mismatches << "\n"
           << "  },\n"
           << "  \"implementation_provenance\": {\n"
           << "    \"diagnostic_source\": {\"path\": " << json_string(__FILE__)
           << ", \"sha256\": " << json_string(sha256_file(__FILE__)) << "},\n"
           << "    \"build_registration\": {\"path\": \"src/CMakeLists.txt\", \"sha256\": "
           << json_string(sha256_file("src/CMakeLists.txt")) << "},\n"
           << "    \"floating_point_compile_contract\": "
           << "\"repository Release flags shared with phase1_transform_diagnostic; canonical D0 uses the identical Phase-1 accumulation\",\n"
           << "    \"source_inputs\": {\n"
           << "      \"raw_base_file\": {\"path\": " << json_string(FLAGS_raw_base_file)
           << ", \"sha256\": " << json_string(sha256_file(FLAGS_raw_base_file)) << "},\n"
           << "      \"raw_query_file\": {\"path\": " << json_string(FLAGS_raw_query_file)
           << ", \"sha256\": " << json_string(sha256_file(FLAGS_raw_query_file)) << "},\n"
           << "      \"historical_pca_base_file\": {\"path\": "
           << json_string(FLAGS_pca_base_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_pca_base_file)) << "},\n"
           << "      \"historical_pca_query_file\": {\"path\": "
           << json_string(FLAGS_pca_query_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_pca_query_file)) << "},\n"
           << "      \"historical_pca_centroids_file\": {\"path\": "
           << json_string(FLAGS_pca_centroids_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_pca_centroids_file)) << "},\n"
           << "      \"cluster_assignments_file\": {\"path\": "
           << json_string(FLAGS_cluster_ids_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_cluster_ids_file)) << "},\n"
           << "      \"historical_pca_variance_file\": {\"path\": "
           << json_string(FLAGS_pca_variance_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_pca_variance_file)) << "},\n"
           << "      \"fixed_probes_file\": {\"path\": "
           << json_string(FLAGS_fixed_probes_file) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_fixed_probes_file)) << "},\n"
           << "      \"prepared_manifest\": {\"path\": "
           << json_string(FLAGS_prepared_manifest) << ", \"sha256\": "
           << json_string(sha256_file(FLAGS_prepared_manifest)) << "}\n"
           << "    },\n"
           << "    \"flag_bundle\": {\n"
           << "      \"raw_base_file\": " << json_string(FLAGS_raw_base_file) << ",\n"
           << "      \"raw_query_file\": " << json_string(FLAGS_raw_query_file) << ",\n"
           << "      \"pca_base_file\": " << json_string(FLAGS_pca_base_file) << ",\n"
           << "      \"pca_query_file\": " << json_string(FLAGS_pca_query_file) << ",\n"
           << "      \"pca_centroids_file\": " << json_string(FLAGS_pca_centroids_file) << ",\n"
           << "      \"cluster_ids_file\": " << json_string(FLAGS_cluster_ids_file) << ",\n"
           << "      \"pca_variance_file\": " << json_string(FLAGS_pca_variance_file) << ",\n"
           << "      \"fixed_probes_file\": " << json_string(FLAGS_fixed_probes_file) << ",\n"
           << "      \"prepared_manifest\": " << json_string(FLAGS_prepared_manifest) << ",\n"
           << "      \"output_prefix\": " << json_string(FLAGS_output_prefix) << "\n"
           << "    },\n"
           << "    \"prepared_inputs\": {\n";
    const std::array<std::pair<const char *, std::filesystem::path>, 12> prepared_inputs{{
        {"apply_mean", prepared.mean},
        {"retained_operator", prepared.retained_operator},
        {"raw_centroids", prepared.raw_centroids},
        {"pca_head_base", prepared.head_base},
        {"pca_head_query", prepared.head_query},
        {"pca_head_centroids", prepared.head_centroids},
        {"base_tail_sq_exact", prepared.base_tail_sq_exact},
        {"base_tail_norm_deployed", prepared.base_tail_norm_deployed},
        {"query_probe_tail_sq_exact", prepared.query_probe_tail_sq_exact},
        {"query_probe_tail_sq_deployed", prepared.query_probe_tail_sq_deployed},
        {"fixed_probes", prepared.fixed_probes},
        {"candidate_inventory", prepared.candidate_inventory},
    }};
    for (size_t i = 0; i < prepared_inputs.size(); ++i) {
        const auto &[name, input_path] = prepared_inputs[i];
        output << "      " << json_string(name) << ": {\"path\": "
               << json_string(input_path.string()) << ", \"sha256\": "
               << json_string(sha256_file(input_path.string())) << "}"
               << (i + 1 == prepared_inputs.size() ? "\n" : ",\n");
    }
    output << "    }\n"
           << "  },\n"
           << "  \"outputs\": {\n"
           << "    \"query_metrics\": {\"path\": " << json_string(query_metrics_path)
           << ", \"sha256\": " << json_string(sha256_file(query_metrics_path)) << "},\n"
           << "    \"query_reference\": {\"path\": " << json_string(query_reference_path)
           << ", \"sha256\": " << json_string(sha256_file(query_reference_path)) << "},\n"
           << "    \"candidate_distances\": {\"path\": "
           << json_string(candidate_distances_path) << ", \"sha256\": "
           << json_string(sha256_file(candidate_distances_path)) << ", \"rows\": "
           << candidate_inventory.total << "}\n"
           << "  }\n"
           << "}\n";
    CHECK(output.good());
}

void validate_required_flags() {
    const std::array<std::pair<const std::string *, const char *>, 10> required{{
        {&FLAGS_raw_base_file, "raw_base_file"},
        {&FLAGS_raw_query_file, "raw_query_file"},
        {&FLAGS_pca_base_file, "pca_base_file"},
        {&FLAGS_pca_query_file, "pca_query_file"},
        {&FLAGS_pca_centroids_file, "pca_centroids_file"},
        {&FLAGS_cluster_ids_file, "cluster_ids_file"},
        {&FLAGS_pca_variance_file, "pca_variance_file"},
        {&FLAGS_fixed_probes_file, "fixed_probes_file"},
        {&FLAGS_prepared_manifest, "prepared_manifest"},
        {&FLAGS_output_prefix, "output_prefix"},
    }};
    for (const auto &[value, name] : required) {
        CHECK(!value->empty()) << '-' << name << " is required";
    }
}

} // namespace

int main(int argc, char **argv) {
    google::InitGoogleLogging(argv[0]);
    gflags::ParseCommandLineFlags(&argc, &argv, true);
    validate_required_flags();

    boost::property_tree::ptree prepared_manifest;
    boost::property_tree::read_json(FLAGS_prepared_manifest, prepared_manifest);
    const std::string manifest_text = read_text_file(FLAGS_prepared_manifest);
    require_manifest_contains_hash(
        manifest_text, "9d70b61994ad42c4d35734a786b3814493f8da721cfbfd19943b1b9875167114",
        "recovered mean array");
    require_manifest_contains_hash(
        manifest_text, "5e5de629a3bd95d1b5fe72f29db495113b1313e106ea3caad56992a526d58bdb",
        "full operator array");
    require_manifest_contains_hash(
        manifest_text, "b3d467728c62d2540f1d34309a78a8419ecebeafce9e3a07319af4eb35623b53",
        "retained operator array");

    const PreparedArtifacts prepared = prepared_artifacts(prepared_manifest);
    LoadedData data = load_data(prepared);
    const FrozenHashes frozen_hashes = validate_frozen_hashes(data, prepared_manifest);
    PreparationValidation preparation_validation;
    const TailState tails = validate_preparation(data, preparation_validation);

    CandidateInventory candidate_inventory;
    const auto references = build_query_references(data, candidate_inventory);
    validate_candidate_stream(prepared.candidate_inventory, references);

    const std::filesystem::path prefix(FLAGS_output_prefix);
    const auto output_directory = prefix.parent_path().empty()
                                      ? std::filesystem::path(".")
                                      : prefix.parent_path();
    std::filesystem::create_directories(output_directory);
    const std::string query_reference_path = FLAGS_output_prefix + ".query_reference.csv";
    const std::string query_metrics_path = FLAGS_output_prefix + ".query_metrics.csv";
    const std::string candidate_distances_path =
        FLAGS_output_prefix + ".candidate_distances.csv";
    const std::string manifest_path = FLAGS_output_prefix + ".manifest.json";
    write_query_references(query_reference_path, references);
    write_query_metrics(query_metrics_path, candidate_distances_path, data, tails, references);
    write_manifest(manifest_path, query_metrics_path, query_reference_path,
                   candidate_distances_path,
                   frozen_hashes, candidate_inventory, preparation_validation,
                   prepared, prepared_manifest);
    LOG(INFO) << "LP-0 Gate-A oracle diagnostic complete: " << manifest_path;
    return 0;
}

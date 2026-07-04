#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#include <fmt/core.h>
#include <gflags/gflags.h>
#include <glog/logging.h>
#include <immintrin.h>

#include "define_options.h"

#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/saq_estimator.hpp"
#include "utils/IO.hpp"
#include "utils/memory.hpp"

using namespace saqlib;

DEFINE_string(blockdiag_query_ids, "580,500", "comma-separated query ids to inspect");
DEFINE_int32(blockdiag_nprobe, 200, "nprobe used only to report the target cluster probe rank");
DEFINE_int32(blockdiag_cid, 171, "IVF cluster id to inspect");
DEFINE_int32(blockdiag_block, 16, "block index within the IVF cluster to inspect");
DEFINE_string(blockdiag_output, "", "output CSV path for block-min diagnostics");

namespace {
static constexpr size_t kFastArray = KFastScanSize / 16;
static_assert(kFastArray == 2);

std::vector<int> parse_int_list(const std::string &text) {
    std::vector<int> values;
    std::stringstream ss(text);
    std::string token;
    while (std::getline(ss, token, ',')) {
        if (token.empty()) {
            continue;
        }
        size_t pos = 0;
        const int value = std::stoi(token, &pos);
        CHECK_EQ(pos, token.size()) << "bad integer token: " << token;
        values.push_back(value);
    }
    return values;
}

std::string input_path() {
    return std::string("./data/") + FLAGS_dataset;
}

std::string result_path() {
    return std::string("./results/saq/");
}

std::string query_file() {
    return fmt::format("{}/{}_query{}.fvecs", input_path(), FLAGS_dataset, FLAGS_enable_PCA ? "_pca" : "");
}

std::string quant_file() {
    return fmt::format("{}/{}.index", input_path(), parseArgs(nullptr));
}

uint32_t float_bits(float value) {
    uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

bool bits_are_finite(uint32_t bits) {
    return (bits & 0x7f800000u) != 0x7f800000u;
}

bool is_nan_bits(uint32_t bits) {
    return (bits & 0x7f800000u) == 0x7f800000u && (bits & 0x007fffffu) != 0;
}

bool is_inf_bits(uint32_t bits) {
    return (bits & 0x7fffffffu) == 0x7f800000u;
}

std::string csv_float(float value) {
    const uint32_t bits = float_bits(value);
    if (is_nan_bits(bits)) {
        return "nan";
    }
    if (is_inf_bits(bits)) {
        return (bits & 0x80000000u) ? "-inf" : "inf";
    }
    std::ostringstream oss;
    oss << std::setprecision(9) << value;
    return oss.str();
}

std::string hex32(uint32_t bits) {
    std::ostringstream oss;
    oss << "0x" << std::hex << std::setw(8) << std::setfill('0') << bits;
    return oss.str();
}

std::string join_hex(const uint32_t *bits, size_t n) {
    std::string out;
    for (size_t i = 0; i < n; ++i) {
        if (i) {
            out.push_back('|');
        }
        out += hex32(bits[i]);
    }
    return out;
}

std::string join_values(const float *values, size_t n) {
    std::string out;
    for (size_t i = 0; i < n; ++i) {
        if (i) {
            out.push_back('|');
        }
        out += csv_float(values[i]);
    }
    return out;
}

__mmask16 low_mask(size_t n) {
    return n >= 16 ? 0xffff : static_cast<__mmask16>((1u << n) - 1u);
}

__m512 finite_or_max(__m512 value, __mmask16 valid_mask) {
    const __m512i bits = _mm512_castps_si512(value);
    const __m512i exp = _mm512_and_si512(bits, _mm512_set1_epi32(0x7f800000));
    const __mmask16 finite_mask = _mm512_cmpneq_epi32_mask(exp, _mm512_set1_epi32(0x7f800000));
    const __mmask16 keep_mask = finite_mask & valid_mask;
    return _mm512_mask_blend_ps(keep_mask, _mm512_set1_ps(std::numeric_limits<float>::max()), value);
}

float hmin16(__m512 value) {
    const __m256 lo = _mm512_castps512_ps256(value);
    const __m256 hi = _mm512_extractf32x8_ps(value, 1);
    const __m256 v8 = _mm256_min_ps(lo, hi);
    const __m128 v8_lo = _mm256_castps256_ps128(v8);
    const __m128 v8_hi = _mm256_extractf128_ps(v8, 1);
    const __m128 v4 = _mm_min_ps(v8_lo, v8_hi);
    const __m128 shuf1 = _mm_movehdup_ps(v4);
    const __m128 v2 = _mm_min_ps(v4, shuf1);
    const __m128 shuf2 = _mm_movehl_ps(shuf1, v2);
    const __m128 v1 = _mm_min_ss(v2, shuf2);
    return _mm_cvtss_f32(v1);
}

float simd_finite_min(const __m512 *dist, size_t valid_lanes) {
    const __mmask16 mask0 = low_mask(std::min<size_t>(valid_lanes, 16));
    const __mmask16 mask1 = valid_lanes > 16 ? low_mask(valid_lanes - 16) : 0;
    const __m512 v0 = finite_or_max(dist[0], mask0);
    const __m512 v1 = finite_or_max(dist[1], mask1);
    return hmin16(_mm512_min_ps(v0, v1));
}

struct InspectStats {
    float native_reduce = 0;
    float manual_pair_reduce = 0;
    float simd_safe_min = 0;
    float scalar_finite_min = std::numeric_limits<float>::max();
    int input_nonfinite_count = 0;
    int pair_nonfinite_count = 0;
    int first_input_nonfinite_lane = -1;
    int first_pair_nonfinite_lane = -1;
    float lanes[KFastScanSize]{};
    float pair_lanes[16]{};
    uint32_t lane_bits[KFastScanSize]{};
    uint32_t pair_bits[16]{};
};

InspectStats inspect_block_min(const __m512 *dist, size_t valid_lanes) {
    InspectStats stats;
    _mm512_store_ps(stats.lanes, dist[0]);
    _mm512_store_ps(stats.lanes + 16, dist[1]);
    _mm512_store_si512(reinterpret_cast<__m512i *>(stats.lane_bits), _mm512_castps_si512(dist[0]));
    _mm512_store_si512(reinterpret_cast<__m512i *>(stats.lane_bits + 16), _mm512_castps_si512(dist[1]));

    const __m512 pair = _mm512_min_ps(dist[0], dist[1]);
    _mm512_store_ps(stats.pair_lanes, pair);
    _mm512_store_si512(reinterpret_cast<__m512i *>(stats.pair_bits), _mm512_castps_si512(pair));

    stats.native_reduce = _mm512_reduce_min_ps(pair);
    stats.manual_pair_reduce = hmin16(pair);
    stats.simd_safe_min = simd_finite_min(dist, valid_lanes);

    for (size_t i = 0; i < valid_lanes; ++i) {
        if (!bits_are_finite(stats.lane_bits[i])) {
            if (stats.first_input_nonfinite_lane < 0) {
                stats.first_input_nonfinite_lane = static_cast<int>(i);
            }
            stats.input_nonfinite_count += 1;
        } else if (stats.lanes[i] < stats.scalar_finite_min) {
            stats.scalar_finite_min = stats.lanes[i];
        }
    }
    for (size_t i = 0; i < 16; ++i) {
        const bool pair_lane_valid = i < valid_lanes || i + 16 < valid_lanes;
        if (!pair_lane_valid) {
            continue;
        }
        if (!bits_are_finite(stats.pair_bits[i])) {
            if (stats.first_pair_nonfinite_lane < 0) {
                stats.first_pair_nonfinite_lane = static_cast<int>(i);
            }
            stats.pair_nonfinite_count += 1;
        }
    }
    return stats;
}

int find_probe_rank(const IVF &ivf, const FloatVec &query, size_t nprobe, PID cid, DistType dist_type) {
    std::vector<Candidate> centroid_dist(nprobe);
    ivf.get_initer()->centroids_distances(query, nprobe, dist_type, centroid_dist);
    for (size_t i = 0; i < centroid_dist.size(); ++i) {
        if (centroid_dist[i].id == cid) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

void write_header(std::ofstream &out) {
    out << "query_id,cid,probe_rank,block_idx,stage,segment_id,num_bits,valid_lanes,"
        << "native_reduce,manual_pair_reduce,simd_safe_min,scalar_finite_min,"
        << "native_is_nan,manual_is_nan,simd_is_nan,input_nonfinite_count,pair_nonfinite_count,"
        << "first_input_nonfinite_lane,first_pair_nonfinite_lane,"
        << "lane_bits,pair_bits,lane_values,pair_values\n";
}

void write_row(std::ofstream &out,
               int query_id,
               PID cid,
               int probe_rank,
               size_t block_idx,
               const std::string &stage,
               int segment_id,
               int num_bits,
               size_t valid_lanes,
               const InspectStats &stats) {
    out << query_id << ',' << cid << ',' << probe_rank << ',' << block_idx << ',' << stage << ','
        << segment_id << ',' << num_bits << ',' << valid_lanes << ','
        << csv_float(stats.native_reduce) << ',' << csv_float(stats.manual_pair_reduce) << ','
        << csv_float(stats.simd_safe_min) << ',' << csv_float(stats.scalar_finite_min) << ','
        << (is_nan_bits(float_bits(stats.native_reduce)) ? 1 : 0) << ','
        << (is_nan_bits(float_bits(stats.manual_pair_reduce)) ? 1 : 0) << ','
        << (is_nan_bits(float_bits(stats.simd_safe_min)) ? 1 : 0) << ','
        << stats.input_nonfinite_count << ',' << stats.pair_nonfinite_count << ','
        << stats.first_input_nonfinite_lane << ',' << stats.first_pair_nonfinite_lane << ','
        << join_hex(stats.lane_bits, KFastScanSize) << ',' << join_hex(stats.pair_bits, 16) << ','
        << join_values(stats.lanes, KFastScanSize) << ',' << join_values(stats.pair_lanes, 16) << '\n';
}

class BlockMinInspector : public SaqCluEstimator<DistType::Any> {
    using Base = SaqCluEstimator<DistType::Any>;
    using Base::estimators_;

    __m512 *segment_dist_ = nullptr;

  public:
    BlockMinInspector(const SaqData &data, const SearcherConfig &searcher_cfg, const FloatVec &query)
        : Base(data, searcher_cfg, query) {
        segment_dist_ = memory::align_mm<64, __m512>(data.base_datas.size() * kFastArray);
    }

    ~BlockMinInspector() override {
        std::free(segment_dist_);
    }

    void inspect(int query_id,
                 PID cid,
                 int probe_rank,
                 const SaqCluData *cluster,
                 size_t block_idx,
                 std::ofstream &out) {
        CHECK_LT(block_idx, cluster->num_blocks_);
        CHECK_EQ(cluster->num_segments_, estimators_.size());
        this->prepare(cluster);

        const size_t blk_begin = block_idx * KFastScanSize;
        const size_t valid_lanes = std::min(KFastScanSize, cluster->num_vec_ - blk_begin);
        __m512 curr[kFastArray];
        curr[0] = _mm512_setzero_ps();
        curr[1] = _mm512_setzero_ps();

        for (size_t c_i = 0; c_i < cluster->num_segments_; ++c_i) {
            auto cd = &segment_dist_[c_i * kFastArray];
            estimators_[c_i].varsEstDist(block_idx, cd);
            curr[0] = _mm512_add_ps(curr[0], cd[0]);
            curr[1] = _mm512_add_ps(curr[1], cd[1]);
        }
        write_row(out, query_id, cid, probe_rank, block_idx, "vars_all", -1, -1, valid_lanes,
                  inspect_block_min(curr, valid_lanes));

        for (size_t c_i = 0; c_i < cluster->num_segments_; ++c_i) {
            const auto &segment = cluster->get_segment(c_i);
            if (segment.num_bits_ == 0) {
                continue;
            }

            auto cd = &segment_dist_[c_i * kFastArray];
            curr[0] = _mm512_sub_ps(curr[0], cd[0]);
            curr[1] = _mm512_sub_ps(curr[1], cd[1]);
            estimators_[c_i].compFastDist(block_idx, cd);
            curr[0] = _mm512_add_ps(curr[0], cd[0]);
            curr[1] = _mm512_add_ps(curr[1], cd[1]);

            write_row(out, query_id, cid, probe_rank, block_idx, fmt::format("fast_after_seg{}", c_i),
                      static_cast<int>(c_i), static_cast<int>(segment.num_bits_), valid_lanes,
                      inspect_block_min(curr, valid_lanes));
        }
    }
};

} // namespace

int main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    CHECK(!FLAGS_dataset.empty()) << "provide -dataset";
    CHECK(!FLAGS_seg_plan.empty()) << "provide custom plan through -seg_plan";
    CHECK_GE(FLAGS_blockdiag_cid, 0);
    CHECK_GE(FLAGS_blockdiag_block, 0);
    CHECK_GT(FLAGS_blockdiag_nprobe, 0);
    const auto query_ids = parse_int_list(FLAGS_blockdiag_query_ids);
    CHECK(!query_ids.empty()) << "blockdiag_query_ids is empty";

    SearcherConfig searcher_cfg;
    if (FLAGS_searcher_dist_type == 0) {
        searcher_cfg.dist_type = DistType::L2Sqr;
    } else {
        CHECK_EQ(FLAGS_searcher_dist_type, 0) << "block_min_diagnostic currently supports only L2 squared distance";
    }
    searcher_cfg.searcher_vars_bound_m = FLAGS_searcher_vars_bound_m;

    FloatRowMat query;
    utils::load_something<float, FloatRowMat>(query_file().c_str(), query);

    IVF ivf;
    const std::string index_path = quant_file();
    std::cout << "load index from " << index_path << '\n';
    ivf.load(index_path.c_str());
    CHECK_LT(static_cast<size_t>(FLAGS_blockdiag_cid), ivf.get_pclusters().size());
    const auto &cluster = ivf.get_pclusters()[FLAGS_blockdiag_cid];
    CHECK_LT(static_cast<size_t>(FLAGS_blockdiag_block), cluster.num_blocks_);

    std::string output = FLAGS_blockdiag_output;
    if (output.empty()) {
        output = fmt::format("{}block_min_diagnostic_{}_{}_q{}_cid{}_blk{}.csv",
                             result_path(), FLAGS_dataset, parseArgs(nullptr), FLAGS_blockdiag_query_ids,
                             FLAGS_blockdiag_cid, FLAGS_blockdiag_block);
    }
    std::ofstream out(output, std::ios::out);
    CHECK(out.is_open()) << "failed to open output: " << output;
    write_header(out);

    for (int query_id : query_ids) {
        CHECK_GE(query_id, 0);
        CHECK_LT(query_id, static_cast<int>(query.rows()));
        const FloatVec q = query.row(query_id);
        const int probe_rank = find_probe_rank(ivf, q, static_cast<size_t>(FLAGS_blockdiag_nprobe),
                                               static_cast<PID>(FLAGS_blockdiag_cid), searcher_cfg.dist_type);
        BlockMinInspector inspector(*ivf.get_saq_data(), searcher_cfg, q);
        inspector.inspect(query_id, static_cast<PID>(FLAGS_blockdiag_cid), probe_rank, &cluster,
                          static_cast<size_t>(FLAGS_blockdiag_block), out);
    }

    std::cout << "diagnostic output: " << output << '\n';
    return 0;
}

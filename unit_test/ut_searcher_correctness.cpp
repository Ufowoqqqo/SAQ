#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <limits>
#include <string>
#include <system_error>
#include <vector>

#include <gtest/gtest.h>

#include "defines.hpp"
#include "index/ivf.hpp"
#include "quantization/block_min.hpp"
#include "quantization/config.h"
#include "quantization/saq_estimator.hpp"
#include "test_base.hpp"

using namespace saqlib;

namespace {

struct EstimateSnapshot {
    std::vector<float> fast;
    std::vector<float> accurate;
};

EstimateSnapshot collectEstimates(const IVF &ivf, const FloatVec &query, const SearcherConfig &cfg) {
    CHECK_EQ(ivf.get_pclusters().size(), 1);
    const auto &cluster = ivf.get_pclusters().front();
    SaqCluEstimator<DistType::L2Sqr> estimator(*ivf.get_saq_data(), cfg, query);
    estimator.prepare(&cluster);

    EstimateSnapshot snapshot;
    snapshot.fast.resize(cluster.num_vec_);
    snapshot.accurate.resize(cluster.num_vec_);
    alignas(64) float block[KFastScanSize];
    for (size_t block_idx = 0; block_idx < cluster.num_blocks_; ++block_idx) {
        __m512 estimate[2];
        estimator.compFastDist(block_idx, estimate);
        _mm512_store_ps(block, estimate[0]);
        _mm512_store_ps(block + 16, estimate[1]);

        const size_t begin = block_idx * KFastScanSize;
        const size_t end = std::min(begin + KFastScanSize, cluster.num_vec_);
        for (size_t idx = begin; idx < end; ++idx) {
            snapshot.fast[idx] = block[idx - begin];
            snapshot.accurate[idx] = estimator.compAccurateDist(idx);
        }
    }
    return snapshot;
}

class ScopedIndexFile {
  public:
    std::filesystem::path path;

    ScopedIndexFile() {
        const auto nonce = std::chrono::steady_clock::now().time_since_epoch().count();
        path = std::filesystem::temp_directory_path() /
               ("saq_positive_one_bit_" + std::to_string(nonce) + ".index");
    }

    ~ScopedIndexFile() {
        std::error_code error;
        std::filesystem::remove(path, error);
    }
};

} // namespace

TEST(BlockMinCorrectnessTest, ScalarAndSimdAgreeForEveryPartialBlockSize) {
    alignas(64) float values[KFastScanSize];
    alignas(64) float scratch[KFastScanSize];

    for (size_t valid_lanes = 1; valid_lanes < KFastScanSize; ++valid_lanes) {
        std::vector<size_t> min_lanes = {0, valid_lanes - 1};
        if (valid_lanes > 15) {
            min_lanes.push_back(15);
        }
        if (valid_lanes > 16) {
            min_lanes.push_back(16);
        }

        for (const size_t min_lane : min_lanes) {
            for (size_t lane = 0; lane < KFastScanSize; ++lane) {
                if (lane < valid_lanes) {
                    values[lane] = 1000.0f + static_cast<float>(lane);
                } else {
                    values[lane] = lane % 2 == 0
                                       ? std::numeric_limits<float>::quiet_NaN()
                                       : std::numeric_limits<float>::infinity();
                }
            }
            const float expected = -1000.0f - static_cast<float>(min_lane);
            values[min_lane] = expected;

            const __m512 packed[2] = {
                _mm512_load_ps(values),
                _mm512_load_ps(values + 16),
            };
            const auto scalar = block_min::scalarFiniteBlockMin(packed, valid_lanes, scratch);
            const auto simd = block_min::simdFiniteBlockMin(packed, valid_lanes);

            ASSERT_TRUE(scalar.all_valid_lanes_finite) << "valid_lanes=" << valid_lanes;
            ASSERT_TRUE(simd.all_valid_lanes_finite) << "valid_lanes=" << valid_lanes;
            EXPECT_FLOAT_EQ(scalar.min, expected) << "valid_lanes=" << valid_lanes;
            EXPECT_FLOAT_EQ(simd.min, expected) << "valid_lanes=" << valid_lanes;
        }
    }
}

TEST(BlockMinCorrectnessTest, ValidLaneNonFiniteDisablesApproximatePruning) {
    alignas(64) float values[KFastScanSize];
    alignas(64) float scratch[KFastScanSize];

    for (size_t valid_lanes = 1; valid_lanes < KFastScanSize; ++valid_lanes) {
        std::fill_n(values, KFastScanSize, 10.0f);
        values[valid_lanes / 2] = std::numeric_limits<float>::quiet_NaN();
        if (valid_lanes > 1) {
            values[valid_lanes - 1] = std::numeric_limits<float>::infinity();
        }

        const __m512 packed[2] = {
            _mm512_load_ps(values),
            _mm512_load_ps(values + 16),
        };
        const auto scalar = block_min::scalarFiniteBlockMin(packed, valid_lanes, scratch);
        const auto simd = block_min::simdFiniteBlockMin(packed, valid_lanes);

        ASSERT_FALSE(scalar.all_valid_lanes_finite) << "valid_lanes=" << valid_lanes;
        ASSERT_FALSE(simd.all_valid_lanes_finite) << "valid_lanes=" << valid_lanes;
        EXPECT_FLOAT_EQ(scalar.min, simd.min) << "valid_lanes=" << valid_lanes;
        EXPECT_EQ(block_min::conservativePruningMin(scalar), std::numeric_limits<float>::lowest());
        EXPECT_EQ(block_min::conservativePruningMin(simd), std::numeric_limits<float>::lowest());
    }
}

TEST(SearcherConfigCorrectnessTest, SimdFiniteBlockMinIsDefault) {
    const SearcherConfig cfg;
    EXPECT_EQ(cfg.searcher_safe_block_min_mode, 2);
    EXPECT_FALSE(cfg.searcher_safe_block_min);
}

class PositiveOneBitSegmentTest : public ::testing::Test, public TestBase {
};

TEST_F(PositiveOneBitSegmentTest, ConstructSerializeLoadAndEstimate) {
    constexpr size_t num_data = 37;
    constexpr size_t num_dim = 128;
    constexpr size_t topk = 5;
    generateTestData(num_data, 1, num_dim, 1, 73);

    QuantizeConfig quant_cfg;
    quant_cfg.avg_bits = 1.0f;
    quant_cfg.enable_segmentation = true;
    quant_cfg.seg_eqseg = 2;
    quant_cfg.single.random_rotation = false;

    IVF original(data_.rows(), data_.cols(), 1, quant_cfg);
    original.construct(data_, centroids_, cids_.data(), 1);

    ASSERT_EQ(original.get_saq_data()->quant_plan.size(), 2);
    for (const auto &[segment_dim, segment_bits] : original.get_saq_data()->quant_plan) {
        EXPECT_EQ(segment_dim, 64);
        EXPECT_EQ(segment_bits, 1);
    }

    SearcherConfig search_cfg;
    search_cfg.dist_type = DistType::L2Sqr;
    const auto before = collectEstimates(original, query_.row(0), search_cfg);
    std::array<PID, topk> search_before{};
    original.search<DistType::L2Sqr>(query_.row(0), topk, 1, search_cfg, search_before.data());

    ScopedIndexFile index_file;
    original.save(index_file.path.c_str());
    ASSERT_TRUE(std::filesystem::exists(index_file.path));
    ASSERT_GT(std::filesystem::file_size(index_file.path), 0);

    IVF loaded;
    loaded.load(index_file.path.c_str());
    ASSERT_EQ(loaded.get_saq_data()->quant_plan, original.get_saq_data()->quant_plan);
    const auto after = collectEstimates(loaded, query_.row(0), search_cfg);
    std::array<PID, topk> search_after{};
    loaded.search<DistType::L2Sqr>(query_.row(0), topk, 1, search_cfg, search_after.data());

    ASSERT_EQ(before.fast.size(), num_data);
    ASSERT_EQ(before.accurate.size(), num_data);
    ASSERT_EQ(after.fast.size(), num_data);
    ASSERT_EQ(after.accurate.size(), num_data);
    for (size_t idx = 0; idx < num_data; ++idx) {
        ASSERT_TRUE(block_min::rawFinite(before.fast[idx])) << "idx=" << idx;
        ASSERT_TRUE(block_min::rawFinite(before.accurate[idx])) << "idx=" << idx;
        ASSERT_TRUE(block_min::rawFinite(after.fast[idx])) << "idx=" << idx;
        ASSERT_TRUE(block_min::rawFinite(after.accurate[idx])) << "idx=" << idx;
        EXPECT_FLOAT_EQ(before.fast[idx], after.fast[idx]) << "idx=" << idx;
        EXPECT_FLOAT_EQ(before.accurate[idx], after.accurate[idx]) << "idx=" << idx;
    }
    EXPECT_EQ(search_before, search_after);
    for (const PID id : search_after) {
        EXPECT_LT(id, num_data);
    }
}

#pragma once

// Packed layout and AVX-512 accumulation follow SymphonyQG
// quantization/fastscan_impl.hpp at revision 6124ddb34ee4d176edea1bd7ad38d1672343df28.

#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <vector>

#include <glog/logging.h>

#include "baseline/symphonyqg_scalar.hpp"

namespace saqlib::baseline {

struct SymphonyQGFastScanQuery {
    std::vector<uint8_t> packed_lut;
    float lower = 0.0f;
    float width = 0.0f;
    int32_t code_sum = 0;
};

struct SymphonyQGFastScanBatch {
    size_t neighbor_count = 0;
    size_t padded_neighbor_count = 0;
    std::vector<uint8_t> packed_codes;
    std::vector<float> triple_x;
    std::vector<float> factor_dq;
    std::vector<float> factor_vq;
};

struct SymphonyQGFastScanScratch {
    std::vector<uint16_t> positive_sums;
    std::vector<float> signed_dots;
};

class SymphonyQGFastScanEstimator {
  public:
    static constexpr size_t kBatchSize = 32;

  private:
    static constexpr std::array<int, 16> kQueryPosition = {
        3, 3, 2, 3, 1, 3, 2, 3, 0, 3, 2, 3, 1, 3, 2, 3};
    static constexpr std::array<int, 16> kCodePermutation = {
        0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15};

    size_t padded_dimension_ = 0;

    static size_t roundUpBatch(size_t count) {
        return count == 0
                   ? 0
                   : ((count + kBatchSize - 1) & ~(kBatchSize - 1));
    }

    static void accumulateBlock(const uint8_t *codes, const uint8_t *lut,
                                size_t dimension, uint16_t *result) {
        const size_t code_length = dimension << 2;
        const __m512i low_mask = _mm512_set1_epi8(0x0f);
        __m512i accu0 = _mm512_setzero_si512();
        __m512i accu1 = _mm512_setzero_si512();
        __m512i accu2 = _mm512_setzero_si512();
        __m512i accu3 = _mm512_setzero_si512();

        for (size_t offset = 0; offset < code_length; offset += 64) {
            const __m512i code = _mm512_loadu_si512(&codes[offset]);
            const __m512i table = _mm512_loadu_si512(&lut[offset]);
            const __m512i low = _mm512_and_si512(code, low_mask);
            const __m512i high =
                _mm512_and_si512(_mm512_srli_epi16(code, 4), low_mask);
            const __m512i result_low = _mm512_shuffle_epi8(table, low);
            const __m512i result_high = _mm512_shuffle_epi8(table, high);

            accu0 = _mm512_add_epi16(accu0, result_low);
            accu1 = _mm512_add_epi16(
                accu1, _mm512_srli_epi16(result_low, 8));
            accu2 = _mm512_add_epi16(accu2, result_high);
            accu3 = _mm512_add_epi16(
                accu3, _mm512_srli_epi16(result_high, 8));
        }

        accu0 = _mm512_sub_epi16(accu0, _mm512_slli_epi16(accu1, 8));
        accu2 = _mm512_sub_epi16(accu2, _mm512_slli_epi16(accu3, 8));

        const __m512i reduced01 = _mm512_add_epi16(
            _mm512_mask_blend_epi64(0b11110000, accu0, accu1),
            _mm512_shuffle_i64x2(accu0, accu1, 0b01001110));
        const __m512i reduced23 = _mm512_add_epi16(
            _mm512_mask_blend_epi64(0b11110000, accu2, accu3),
            _mm512_shuffle_i64x2(accu2, accu3, 0b01001110));
        __m512i reduced = _mm512_shuffle_i64x2(
            reduced01, reduced23, 0b10001000);
        reduced = _mm512_add_epi16(
            reduced,
            _mm512_shuffle_i64x2(reduced01, reduced23, 0b11011101));
        _mm512_storeu_si512(result, reduced);
    }

  public:
    explicit SymphonyQGFastScanEstimator(size_t padded_dimension)
        : padded_dimension_(padded_dimension) {
        CHECK(std::has_single_bit(padded_dimension_));
        CHECK_EQ(padded_dimension_ % 64, 0);
        CHECK_GE(padded_dimension_, SymphonyQGScalarEstimator::kMinPaddedDimension);
        CHECK_LE(padded_dimension_, SymphonyQGScalarEstimator::kMaxPaddedDimension);
        static_assert(std::endian::native == std::endian::little,
                      "SymphonyQG packed layout assumes little-endian words");
    }

    size_t padded_dimension() const { return padded_dimension_; }
    size_t query_lut_bytes() const { return padded_dimension_ << 2; }
    size_t logical_code_bits_per_neighbor() const { return padded_dimension_; }
    size_t factor_bytes_per_neighbor() const { return 3 * sizeof(float); }

    size_t paddedNeighborCount(size_t count) const { return roundUpBatch(count); }

    size_t packedCodeBytes(size_t count) const {
        return roundUpBatch(count) * padded_dimension_ / 8;
    }

    SymphonyQGFastScanQuery prepareQuery(
        const SymphonyQGScalarQuery &scalar_query) const {
        CHECK_EQ(scalar_query.codes.size(), padded_dimension_);
        SymphonyQGFastScanQuery query;
        query.lower = scalar_query.lower;
        query.width = scalar_query.width;
        query.code_sum = scalar_query.code_sum;
        query.packed_lut.resize(query_lut_bytes());

        uint8_t *lut = query.packed_lut.data();
        const uint8_t *codes = scalar_query.codes.data();
        for (size_t group = 0; group < padded_dimension_ / 4; ++group) {
            lut[0] = 0;
            for (int subset = 1; subset < 16; ++subset) {
                const int low_bit = subset & -subset;
                lut[subset] = static_cast<uint8_t>(
                    lut[subset - low_bit] + codes[kQueryPosition[subset]]);
            }
            lut += 16;
            codes += 4;
        }
        return query;
    }

    SymphonyQGFastScanBatch encodeBatch(
        const std::vector<SymphonyQGScalarNeighbor> &neighbors) const {
        SymphonyQGFastScanBatch batch;
        batch.neighbor_count = neighbors.size();
        batch.padded_neighbor_count = roundUpBatch(batch.neighbor_count);
        if (batch.neighbor_count == 0) {
            return batch;
        }

        const size_t words_per_neighbor = padded_dimension_ / 64;
        const size_t bytes_per_neighbor = padded_dimension_ / 8;
        std::vector<uint64_t> binary_words(
            batch.neighbor_count * words_per_neighbor, 0);
        for (size_t neighbor = 0; neighbor < batch.neighbor_count; ++neighbor) {
            CHECK_EQ(
                neighbors[neighbor].residual_positive.size(), padded_dimension_);
            for (size_t word = 0; word < words_per_neighbor; ++word) {
                uint64_t packed = 0;
                for (size_t bit = 0; bit < 64; ++bit) {
                    const size_t dimension = (word * 64) + bit;
                    const uint8_t positive =
                        neighbors[neighbor].residual_positive[dimension];
                    CHECK_LE(positive, 1);
                    packed |= static_cast<uint64_t>(positive)
                              << (63 - bit);
                }
                binary_words[(neighbor * words_per_neighbor) + word] = packed;
            }
        }

        std::vector<uint8_t> byte_codes(
            batch.padded_neighbor_count * bytes_per_neighbor, 0);
        std::memcpy(
            byte_codes.data(), binary_words.data(),
            batch.neighbor_count * bytes_per_neighbor);
        for (size_t neighbor = 0; neighbor < batch.neighbor_count; ++neighbor) {
            for (size_t word = 0; word < words_per_neighbor; ++word) {
                const size_t word_offset =
                    (neighbor * bytes_per_neighbor) + (word * 8);
                for (size_t byte = 0; byte < 4; ++byte) {
                    std::swap(
                        byte_codes[word_offset + byte],
                        byte_codes[word_offset + 7 - byte]);
                }
            }
        }
        for (size_t offset = 0;
             offset < batch.neighbor_count * bytes_per_neighbor; ++offset) {
            const uint8_t value = byte_codes[offset];
            byte_codes[offset] = static_cast<uint8_t>(
                ((value & 0x0f) << 4) | (value >> 4));
        }

        batch.packed_codes.assign(packedCodeBytes(batch.neighbor_count), 0);
        uint8_t *output = batch.packed_codes.data();
        const size_t codebooks = padded_dimension_ / 4;
        for (size_t block = 0;
             block < batch.padded_neighbor_count; block += kBatchSize) {
            for (size_t codebook = 0; codebook < codebooks; codebook += 2) {
                std::array<uint8_t, kBatchSize> column{};
                for (size_t lane = 0; lane < kBatchSize; ++lane) {
                    const size_t neighbor = block + lane;
                    if (neighbor < batch.neighbor_count) {
                        column[lane] = byte_codes[
                            (neighbor * bytes_per_neighbor) + (codebook / 2)];
                    }
                }

                for (size_t lane = 0; lane < 16; ++lane) {
                    const uint8_t low0 =
                        static_cast<uint8_t>(column[kCodePermutation[lane]] & 0x0f);
                    const uint8_t low1 = static_cast<uint8_t>(
                        column[kCodePermutation[lane] + 16] & 0x0f);
                    const uint8_t high0 =
                        static_cast<uint8_t>(column[kCodePermutation[lane]] >> 4);
                    const uint8_t high1 = static_cast<uint8_t>(
                        column[kCodePermutation[lane] + 16] >> 4);
                    output[lane] = static_cast<uint8_t>(low0 | (low1 << 4));
                    output[lane + 16] =
                        static_cast<uint8_t>(high0 | (high1 << 4));
                }
                output += kBatchSize;
            }
        }

        batch.triple_x.assign(batch.padded_neighbor_count, 0.0f);
        batch.factor_dq.assign(batch.padded_neighbor_count, 0.0f);
        batch.factor_vq.assign(batch.padded_neighbor_count, 0.0f);
        for (size_t neighbor = 0; neighbor < batch.neighbor_count; ++neighbor) {
            batch.triple_x[neighbor] = neighbors[neighbor].triple_x;
            batch.factor_dq[neighbor] = neighbors[neighbor].factor_dq;
            batch.factor_vq[neighbor] = neighbors[neighbor].factor_vq;
        }
        return batch;
    }

    std::vector<uint16_t> positiveCodeSums(
        const SymphonyQGFastScanQuery &query,
        const SymphonyQGFastScanBatch &batch) const {
        std::vector<uint16_t> sums;
        positiveCodeSumsInto(query, batch, sums);
        return sums;
    }

    void positiveCodeSumsInto(
        const SymphonyQGFastScanQuery &query,
        const SymphonyQGFastScanBatch &batch,
        std::vector<uint16_t> &sums) const {
        CHECK_EQ(query.packed_lut.size(), query_lut_bytes());
        CHECK_EQ(
            batch.padded_neighbor_count,
            roundUpBatch(batch.neighbor_count));
        CHECK_EQ(
            batch.packed_codes.size(), packedCodeBytes(batch.neighbor_count));
        sums.resize(batch.padded_neighbor_count);
        const size_t code_bytes_per_batch = padded_dimension_ << 2;
        for (size_t block = 0;
             block < batch.padded_neighbor_count; block += kBatchSize) {
            accumulateBlock(
                &batch.packed_codes[(block / kBatchSize) * code_bytes_per_batch],
                query.packed_lut.data(), padded_dimension_, &sums[block]);
        }
    }

    std::vector<int32_t> signedQueryCodeDots(
        const SymphonyQGFastScanQuery &query,
        const SymphonyQGFastScanBatch &batch) const {
        const auto positive_sums = positiveCodeSums(query, batch);
        std::vector<int32_t> signed_dots(batch.neighbor_count);
        for (size_t neighbor = 0; neighbor < batch.neighbor_count; ++neighbor) {
            signed_dots[neighbor] =
                (static_cast<int32_t>(positive_sums[neighbor]) << 1) -
                query.code_sum;
        }
        return signed_dots;
    }

    std::vector<float> estimateBatch(
        const SymphonyQGFastScanQuery &query, float current_distance,
        const SymphonyQGFastScanBatch &batch) const {
        SymphonyQGFastScanScratch scratch;
        std::vector<float> distances;
        estimateBatchInto(query, current_distance, batch, scratch, distances);
        distances.resize(batch.neighbor_count);
        return distances;
    }

    void estimateBatchInto(
        const SymphonyQGFastScanQuery &query, float current_distance,
        const SymphonyQGFastScanBatch &batch,
        SymphonyQGFastScanScratch &scratch,
        std::vector<float> &distances) const {
        CHECK_EQ(batch.triple_x.size(), batch.padded_neighbor_count);
        CHECK_EQ(batch.factor_dq.size(), batch.padded_neighbor_count);
        CHECK_EQ(batch.factor_vq.size(), batch.padded_neighbor_count);
        CHECK_EQ(
            batch.padded_neighbor_count,
            roundUpBatch(batch.neighbor_count));
        positiveCodeSumsInto(query, batch, scratch.positive_sums);
        scratch.signed_dots.resize(batch.padded_neighbor_count);
        for (size_t neighbor = 0;
             neighbor < batch.padded_neighbor_count; ++neighbor) {
            scratch.signed_dots[neighbor] = static_cast<float>(
                (static_cast<int32_t>(scratch.positive_sums[neighbor]) << 1) -
                query.code_sum);
        }

        distances.resize(batch.padded_neighbor_count);
        const __m512 current = _mm512_set1_ps(current_distance);
        const __m512 width = _mm512_set1_ps(query.width);
        const __m512 lower = _mm512_set1_ps(query.lower);
        for (size_t offset = 0;
             offset < batch.padded_neighbor_count; offset += 16) {
            const __m512 dot = _mm512_loadu_ps(&scratch.signed_dots[offset]);
            __m512 triple = _mm512_loadu_ps(&batch.triple_x[offset]);
            __m512 factor_dq = _mm512_loadu_ps(&batch.factor_dq[offset]);
            const __m512 factor_vq = _mm512_loadu_ps(&batch.factor_vq[offset]);

            triple = _mm512_add_ps(triple, current);
            factor_dq = _mm512_mul_ps(factor_dq, width);
            factor_dq = _mm512_mul_ps(factor_dq, dot);
            const __m512 query_value =
                _mm512_fmadd_ps(factor_vq, lower, triple);
            const __m512 distance = _mm512_add_ps(factor_dq, query_value);
            _mm512_storeu_ps(&distances[offset], distance);
        }
    }
};

} // namespace saqlib::baseline

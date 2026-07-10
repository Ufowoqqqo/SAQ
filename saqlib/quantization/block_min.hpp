#pragma once

#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <immintrin.h>
#include <limits>

#include <glog/logging.h>

namespace saqlib::block_min {

struct FiniteBlockMinResult {
    float min = std::numeric_limits<float>::max();
    bool all_valid_lanes_finite = true;
};

inline bool rawFinite(float value) {
    const uint32_t bits = std::bit_cast<uint32_t>(value);
    return (bits & 0x7f800000u) != 0x7f800000u;
}

inline __mmask16 lowMask(size_t n) {
    return n >= 16 ? 0xffff : static_cast<__mmask16>((1u << n) - 1u);
}

inline __mmask16 finiteMask(__m512 value) {
    const __m512i bits = _mm512_castps_si512(value);
    const __m512i exp = _mm512_and_si512(bits, _mm512_set1_epi32(0x7f800000));
    return _mm512_cmpneq_epi32_mask(exp, _mm512_set1_epi32(0x7f800000));
}

inline __m512 retainFiniteValidLanes(__m512 value, __mmask16 valid_mask, __mmask16 finite_mask) {
    const __mmask16 keep_mask = finite_mask & valid_mask;
    return _mm512_mask_blend_ps(keep_mask, _mm512_set1_ps(std::numeric_limits<float>::max()), value);
}

inline float hmin16(__m512 value) {
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

inline FiniteBlockMinResult simdFiniteBlockMin(const __m512 *dist, size_t valid_lanes) {
    CHECK_GT(valid_lanes, 0);
    CHECK_LE(valid_lanes, 32);

    const __mmask16 valid0 = lowMask(std::min<size_t>(valid_lanes, 16));
    const __mmask16 valid1 = valid_lanes > 16 ? lowMask(valid_lanes - 16) : 0;
    const __mmask16 finite0 = finiteMask(dist[0]);
    const __mmask16 finite1 = finiteMask(dist[1]);
    const __m512 v0 = retainFiniteValidLanes(dist[0], valid0, finite0);
    const __m512 v1 = retainFiniteValidLanes(dist[1], valid1, finite1);

    return {
        hmin16(_mm512_min_ps(v0, v1)),
        (finite0 & valid0) == valid0 && (finite1 & valid1) == valid1,
    };
}

inline FiniteBlockMinResult scalarFiniteBlockMin(const __m512 *dist, size_t valid_lanes, float *scratch) {
    CHECK_GT(valid_lanes, 0);
    CHECK_LE(valid_lanes, 32);

    _mm512_storeu_ps(scratch, dist[0]);
    _mm512_storeu_ps(scratch + 16, dist[1]);
    FiniteBlockMinResult result;
    for (size_t lane = 0; lane < valid_lanes; ++lane) {
        const float value = scratch[lane];
        if (!rawFinite(value)) {
            result.all_valid_lanes_finite = false;
            continue;
        }
        result.min = std::min(result.min, value);
    }
    return result;
}

inline float conservativePruningMin(const FiniteBlockMinResult &result) {
    return result.all_valid_lanes_finite
               ? result.min
               : std::numeric_limits<float>::lowest();
}

} // namespace saqlib::block_min

#pragma once

#include <cstddef>
#include <cstdint>

namespace symphonyqg_scalar_fixture_input {

inline constexpr size_t kDimension = 63;
inline constexpr size_t kPaddedDimension = 64;
inline constexpr size_t kNeighborCount = 16;
inline constexpr uint64_t kRotationSeed = 7;

inline float queryValue(size_t dim) {
    const int primary = static_cast<int>((dim * 7 + 3) % 31) - 15;
    const int secondary = static_cast<int>(dim % 3);
    const int tertiary = static_cast<int>((dim * 5 + 1) % 11) - 5;
    return static_cast<float>(primary) / 8.0f +
           static_cast<float>(secondary) / 32.0f +
           static_cast<float>(tertiary) / 1024.0f;
}

inline float currentValue(size_t dim) {
    const int primary = static_cast<int>((dim * 11 + 5) % 37) - 18;
    return static_cast<float>(primary) / 8.0f;
}

inline float neighborValue(size_t neighbor, size_t dim) {
    const size_t source_neighbor =
        neighbor + 1 == kNeighborCount ? neighbor - 1 : neighbor;
    const int raw_delta =
        static_cast<int>(((source_neighbor + 1) * (dim + 3) * 13 +
                          source_neighbor * 7) % 41) - 20;
    const int nonzero_delta =
        raw_delta == 0 ? (source_neighbor % 2 == 0 ? 1 : -1) : raw_delta;
    return currentValue(dim) + static_cast<float>(nonzero_delta) / 16.0f;
}

} // namespace symphonyqg_scalar_fixture_input

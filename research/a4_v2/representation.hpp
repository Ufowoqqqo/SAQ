#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace saq::a4_v2::producer {

inline constexpr std::size_t kCoordinateCount = 128;
inline constexpr std::size_t kGroupCount = 64;

struct PointBits2 {
  std::uint32_t x{0};
  std::uint32_t y{0};
  friend bool operator==(const PointBits2&, const PointBits2&) = default;
};

struct RepresentationCounters {
  std::uint64_t mixed_radix_encodes{0};
  std::uint64_t mixed_radix_decodes{0};
  std::uint64_t scalar_distances{0};
  std::uint64_t point_distances{0};
  std::uint64_t pack_operations{0};
  std::uint64_t unpack_operations{0};
};

struct LookupBits {
  bool valid{false};
  std::uint64_t binary64_bits{0x7ff0000000000000ULL};
  std::uint32_t binary32_bits{0x7f800000U};
};

struct MatchedLookup {
  std::uint32_t capacity{0};
  std::uint32_t valid_states{0};
  std::vector<LookupBits> entries;
};

struct GlobalPacked {
  std::vector<std::uint8_t> bytes;
  std::vector<std::uint32_t> bit_offsets;
  std::uint32_t used_bits{0};
};

[[nodiscard]] std::uint64_t MixedRadixEncode(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint32_t> radices,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] std::vector<std::uint32_t> MixedRadixDecode(
    std::uint64_t address, std::span<const std::uint32_t> radices,
    RepresentationCounters* counters = nullptr);

[[nodiscard]] std::vector<std::uint8_t> PackMatched(
    std::span<const std::uint32_t> labels, std::uint32_t word_bits,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] std::vector<std::uint32_t> UnpackMatched(
    std::span<const std::uint8_t> bytes, std::uint32_t word_bits,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] GlobalPacked PackGlobal(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint8_t> widths, std::size_t paid_bytes,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] std::vector<std::uint32_t> UnpackGlobal(
    std::span<const std::uint8_t> bytes,
    std::span<const std::uint8_t> widths,
    RepresentationCounters* counters = nullptr);

[[nodiscard]] std::uint32_t AssignScalar(
    std::uint32_t value_bits, std::span<const std::uint32_t> centroid_bits,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] std::uint32_t AssignPoint2(
    const PointBits2& value, std::span<const PointBits2> centroids,
    RepresentationCounters* counters = nullptr);
[[nodiscard]] std::vector<PointBits2> CartesianBits(
    std::span<const std::uint32_t> axis0,
    std::span<const std::uint32_t> axis1);
[[nodiscard]] MatchedLookup BuildMatchedLookup(
    const PointBits2& query, std::span<const PointBits2> reconstructions,
    std::uint32_t capacity);

void RepresentationSmoke();

}  // namespace saq::a4_v2::producer

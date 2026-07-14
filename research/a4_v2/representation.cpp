#include "representation.hpp"

#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace saq::a4_v2::producer {
namespace {

[[nodiscard]] double Promote(std::uint32_t bits) {
  const float value = std::bit_cast<float>(bits);
  if (!std::isfinite(value)) {
    throw std::invalid_argument("representation value must be finite");
  }
  return static_cast<double>(value);
}

[[nodiscard]] double ScalarDistance(std::uint32_t lhs, std::uint32_t rhs) {
  const double difference = Promote(lhs) - Promote(rhs);
  const double result = difference * difference;
  if (!std::isfinite(result)) {
    throw std::overflow_error("nonfinite scalar distance");
  }
  return result;
}

[[nodiscard]] double PointDistance(const PointBits2& lhs,
                                   const PointBits2& rhs) {
  const double dx = Promote(lhs.x) - Promote(rhs.x);
  const double x2 = dx * dx;
  const double dy = Promote(lhs.y) - Promote(rhs.y);
  const double y2 = dy * dy;
  const double result = x2 + y2;
  if (!std::isfinite(result)) {
    throw std::overflow_error("nonfinite point distance");
  }
  return result;
}

void RequireWordBits(std::uint32_t bits) {
  if (bits != 4 && bits != 8) {
    throw std::invalid_argument("word bits must be 4 or 8");
  }
}

}  // namespace

std::uint64_t MixedRadixEncode(std::span<const std::uint32_t> labels,
                               std::span<const std::uint32_t> radices,
                               RepresentationCounters* counters) {
  if (labels.empty() || labels.size() != radices.size()) {
    throw std::invalid_argument("mixed-radix shape mismatch");
  }
  std::uint64_t address = 0;
  std::uint64_t multiplier = 1;
  for (std::size_t index = 0; index < labels.size(); ++index) {
    if (radices[index] == 0 || labels[index] >= radices[index] ||
        multiplier >
            std::numeric_limits<std::uint64_t>::max() / radices[index]) {
      throw std::invalid_argument("invalid mixed-radix digit");
    }
    address += static_cast<std::uint64_t>(labels[index]) * multiplier;
    multiplier *= radices[index];
  }
  if (counters != nullptr) ++counters->mixed_radix_encodes;
  return address;
}

std::vector<std::uint32_t> MixedRadixDecode(
    std::uint64_t address, std::span<const std::uint32_t> radices,
    RepresentationCounters* counters) {
  if (radices.empty()) {
    throw std::invalid_argument("empty mixed-radix decoder");
  }
  std::uint64_t capacity = 1;
  for (const std::uint32_t radix : radices) {
    if (radix == 0 ||
        capacity > std::numeric_limits<std::uint64_t>::max() / radix) {
      throw std::invalid_argument("invalid mixed-radix base");
    }
    capacity *= radix;
  }
  if (address >= capacity) {
    throw std::invalid_argument("mixed-radix address out of range");
  }
  std::vector<std::uint32_t> result;
  result.reserve(radices.size());
  for (const std::uint32_t radix : radices) {
    result.push_back(static_cast<std::uint32_t>(address % radix));
    address /= radix;
  }
  if (counters != nullptr) ++counters->mixed_radix_decodes;
  return result;
}

std::vector<std::uint8_t> PackMatched(
    std::span<const std::uint32_t> labels, std::uint32_t word_bits,
    RepresentationCounters* counters) {
  RequireWordBits(word_bits);
  if (labels.size() != kGroupCount) {
    throw std::invalid_argument("matched packing needs 64 labels");
  }
  const std::uint32_t limit = 1U << word_bits;
  std::vector<std::uint8_t> result(word_bits == 4 ? 32 : 64, 0);
  for (std::size_t group = 0; group < labels.size(); ++group) {
    if (labels[group] >= limit) {
      throw std::invalid_argument("matched label exceeds word");
    }
    if (word_bits == 4) {
      result[group / 2] |= static_cast<std::uint8_t>(
          labels[group] << ((group % 2) == 0 ? 0U : 4U));
    } else {
      result[group] = static_cast<std::uint8_t>(labels[group]);
    }
  }
  if (counters != nullptr) ++counters->pack_operations;
  return result;
}

std::vector<std::uint32_t> UnpackMatched(
    std::span<const std::uint8_t> bytes, std::uint32_t word_bits,
    RepresentationCounters* counters) {
  RequireWordBits(word_bits);
  if (bytes.size() != (word_bits == 4 ? 32U : 64U)) {
    throw std::invalid_argument("matched payload size mismatch");
  }
  std::vector<std::uint32_t> result(kGroupCount);
  for (std::size_t group = 0; group < kGroupCount; ++group) {
    result[group] = word_bits == 4
                        ? ((bytes[group / 2] >>
                            ((group % 2) == 0 ? 0U : 4U)) &
                           0x0fU)
                        : bytes[group];
  }
  if (counters != nullptr) ++counters->unpack_operations;
  return result;
}

GlobalPacked PackGlobal(std::span<const std::uint32_t> labels,
                        std::span<const std::uint8_t> widths,
                        std::size_t paid_bytes,
                        RepresentationCounters* counters) {
  if (labels.size() != kCoordinateCount || widths.size() != kCoordinateCount ||
      (paid_bytes != 32 && paid_bytes != 64)) {
    throw std::invalid_argument("global packing shape mismatch");
  }
  GlobalPacked result;
  result.bytes.assign(paid_bytes, 0);
  result.bit_offsets.reserve(kCoordinateCount);
  std::uint64_t offset = 0;
  for (std::size_t coordinate = 0; coordinate < labels.size(); ++coordinate) {
    const std::uint8_t width = widths[coordinate];
    if (width > 8 || labels[coordinate] >= (1U << width) ||
        offset + width > paid_bytes * 8ULL) {
      throw std::invalid_argument("global label/width invalid");
    }
    result.bit_offsets.push_back(static_cast<std::uint32_t>(offset));
    for (std::uint32_t bit = 0; bit < width; ++bit) {
      if (((labels[coordinate] >> bit) & 1U) != 0) {
        const std::uint64_t stream = offset + bit;
        result.bytes[stream / 8U] |=
            static_cast<std::uint8_t>(1U << (stream % 8U));
      }
    }
    offset += width;
  }
  result.used_bits = static_cast<std::uint32_t>(offset);
  if (counters != nullptr) ++counters->pack_operations;
  return result;
}

std::vector<std::uint32_t> UnpackGlobal(
    std::span<const std::uint8_t> bytes,
    std::span<const std::uint8_t> widths,
    RepresentationCounters* counters) {
  if ((bytes.size() != 32 && bytes.size() != 64) ||
      widths.size() != kCoordinateCount) {
    throw std::invalid_argument("global unpacking shape mismatch");
  }
  std::vector<std::uint32_t> result(kCoordinateCount, 0);
  std::uint64_t offset = 0;
  for (std::size_t coordinate = 0; coordinate < result.size(); ++coordinate) {
    if (widths[coordinate] > 8 || offset + widths[coordinate] > bytes.size() * 8ULL) {
      throw std::invalid_argument("global widths exceed payload");
    }
    for (std::uint32_t bit = 0; bit < widths[coordinate]; ++bit) {
      const std::uint64_t stream = offset + bit;
      result[coordinate] |=
          ((bytes[stream / 8U] >> (stream % 8U)) & 1U) << bit;
    }
    offset += widths[coordinate];
  }
  for (std::uint64_t bit = offset; bit < bytes.size() * 8ULL; ++bit) {
    if (((bytes[bit / 8U] >> (bit % 8U)) & 1U) != 0) {
      throw std::invalid_argument("global padding is nonzero");
    }
  }
  if (counters != nullptr) ++counters->unpack_operations;
  return result;
}

std::uint32_t AssignScalar(std::uint32_t value_bits,
                           std::span<const std::uint32_t> centroid_bits,
                           RepresentationCounters* counters) {
  if (centroid_bits.empty()) {
    throw std::invalid_argument("scalar assignment has no centroid");
  }
  std::uint32_t best = 0;
  double best_distance = std::numeric_limits<double>::infinity();
  for (std::uint32_t label = 0; label < centroid_bits.size(); ++label) {
    const double distance = ScalarDistance(value_bits, centroid_bits[label]);
    if (counters != nullptr) ++counters->scalar_distances;
    if (distance < best_distance) {
      best_distance = distance;
      best = label;
    }
  }
  return best;
}

std::uint32_t AssignPoint2(const PointBits2& value,
                           std::span<const PointBits2> centroids,
                           RepresentationCounters* counters) {
  if (centroids.empty()) {
    throw std::invalid_argument("point assignment has no centroid");
  }
  std::uint32_t best = 0;
  double best_distance = std::numeric_limits<double>::infinity();
  for (std::uint32_t label = 0; label < centroids.size(); ++label) {
    const double distance = PointDistance(value, centroids[label]);
    if (counters != nullptr) ++counters->point_distances;
    if (distance < best_distance) {
      best_distance = distance;
      best = label;
    }
  }
  return best;
}

std::vector<PointBits2> CartesianBits(
    std::span<const std::uint32_t> axis0,
    std::span<const std::uint32_t> axis1) {
  if (axis0.empty() || axis1.empty()) {
    throw std::invalid_argument("empty Cartesian axes");
  }
  std::vector<PointBits2> result;
  result.reserve(axis0.size() * axis1.size());
  for (const std::uint32_t y : axis1) {
    for (const std::uint32_t x : axis0) result.push_back(PointBits2{x, y});
  }
  return result;
}

MatchedLookup BuildMatchedLookup(
    const PointBits2& query, std::span<const PointBits2> reconstructions,
    std::uint32_t capacity) {
  if ((capacity != 16 && capacity != 256) || reconstructions.empty() ||
      reconstructions.size() > capacity) {
    throw std::invalid_argument("matched lookup shape invalid");
  }
  MatchedLookup result;
  result.capacity = capacity;
  result.valid_states =
      static_cast<std::uint32_t>(reconstructions.size());
  result.entries.reserve(capacity);
  for (const PointBits2& reconstruction : reconstructions) {
    const double distance = PointDistance(query, reconstruction);
    const float narrowed = static_cast<float>(distance);
    if (!std::isfinite(narrowed)) {
      throw std::overflow_error("lookup narrowing overflow");
    }
    result.entries.push_back(LookupBits{true, std::bit_cast<std::uint64_t>(distance),
                                        std::bit_cast<std::uint32_t>(narrowed)});
  }
  while (result.entries.size() < capacity) result.entries.push_back(LookupBits{});
  return result;
}

void RepresentationSmoke() {
  RepresentationCounters counters;
  const std::vector<std::uint32_t> radices{3, 5};
  const std::vector<std::uint32_t> labels{2, 4};
  const std::uint64_t address = MixedRadixEncode(labels, radices, &counters);
  if (address != 14 || MixedRadixDecode(address, radices, &counters) != labels) {
    throw std::logic_error("mixed-radix smoke failed");
  }
  std::vector<std::uint32_t> matched(kGroupCount);
  for (std::size_t group = 0; group < matched.size(); ++group) {
    matched[group] = static_cast<std::uint32_t>(group % 16);
  }
  const std::vector<std::uint8_t> b4 = PackMatched(matched, 4, &counters);
  if (b4.size() != 32 || b4[0] != 0x10U ||
      UnpackMatched(b4, 4, &counters) != matched) {
    throw std::logic_error("B4 packing smoke failed");
  }
  std::vector<std::uint32_t> global(kCoordinateCount, 0);
  std::vector<std::uint8_t> widths(kCoordinateCount, 0);
  widths[0] = 1; widths[1] = 2; widths[2] = 3;
  global[0] = 1; global[1] = 2; global[2] = 5;
  const GlobalPacked packed = PackGlobal(global, widths, 32, &counters);
  if (packed.bytes[0] != 0x2dU ||
      UnpackGlobal(packed.bytes, widths, &counters) != global) {
    throw std::logic_error("global packing smoke failed");
  }
  const std::uint32_t zero = std::bit_cast<std::uint32_t>(0.0F);
  const std::vector<std::uint32_t> tied{
      std::bit_cast<std::uint32_t>(-1.0F),
      std::bit_cast<std::uint32_t>(1.0F)};
  if (AssignScalar(zero, tied) != 0) {
    throw std::logic_error("lower-label tie smoke failed");
  }
}

}  // namespace saq::a4_v2::producer

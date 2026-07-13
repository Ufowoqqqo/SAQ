#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace saq::a4_1s {

inline constexpr std::size_t kFrozenGroupCount = 64;
inline constexpr std::size_t kFrozenCoordinateCount = 128;
inline constexpr std::uint32_t kBinary32PositiveInfinityBits = 0x7f800000U;
inline constexpr std::uint64_t kBinary64PositiveInfinityBits =
    0x7ff0000000000000ULL;

struct RepresentationCounters {
    std::uint64_t mixed_radix_encodes{0};
    std::uint64_t mixed_radix_decodes{0};
    std::uint64_t mixed_radix_digits{0};
    std::uint64_t scalar_distance_evaluations{0};
    std::uint64_t point_distance_evaluations{0};
    std::uint64_t binary64_subtractions{0};
    std::uint64_t binary64_multiplications{0};
    std::uint64_t binary64_additions{0};
    std::uint64_t binary32_narrowings{0};
    std::uint64_t valid_lookup_entries{0};
    std::uint64_t invalid_lookup_entries{0};
    std::uint64_t packed_labels_written{0};
    std::uint64_t packed_labels_read{0};
    std::uint64_t packed_bytes_written{0};
    std::uint64_t packed_bytes_read{0};
    std::uint64_t stream_bits_written{0};
    std::uint64_t stream_bits_read{0};
    std::uint64_t padding_bits_checked{0};
    std::uint64_t cartesian_reconstructions{0};

    void Merge(const RepresentationCounters &other) noexcept;
};

struct Binary32Point2 {
    std::uint32_t coordinate0_bits{0};
    std::uint32_t coordinate1_bits{0};

    friend bool operator==(const Binary32Point2 &,
                           const Binary32Point2 &) = default;
};

// Both layers are persisted for parity.  Invalid matched-word addresses use
// the exact positive-infinity bit pattern in both fields and valid=false.
struct LookupEntryBits {
    bool valid{false};
    std::uint64_t pre_narrow_binary64_bits{kBinary64PositiveInfinityBits};
    std::uint32_t stored_binary32_bits{kBinary32PositiveInfinityBits};
};

struct MatchedLookupTableBits {
    std::uint32_t capacity{0};
    std::uint32_t valid_states{0};
    std::vector<LookupEntryBits> entries;
};

struct GlobalLookupTableBits {
    // coordinate_offsets has coordinate_count+1 entries.  Entries for
    // coordinate j occupy [offset[j], offset[j+1]).
    std::vector<std::uint32_t> coordinate_offsets;
    std::vector<LookupEntryBits> entries;
};

struct GlobalPackedLabels {
    std::vector<std::uint8_t> bytes;
    std::vector<std::uint32_t> bit_offsets;
    std::uint32_t used_bits{0};
};

[[nodiscard]] std::uint64_t MixedRadixCapacity(
    std::span<const std::uint32_t> radices);

// Coordinate zero is the least-significant digit.  Thus the registered
// two-factor address is u=z0+K0*z1.
[[nodiscard]] std::uint64_t MixedRadixEncode(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint32_t> radices,
    RepresentationCounters *counters = nullptr);

[[nodiscard]] std::vector<std::uint32_t> MixedRadixDecode(
    std::uint64_t address,
    std::span<const std::uint32_t> radices,
    RepresentationCounters *counters = nullptr);

// The matched-word panel always contains exactly 64 group labels.  B4 packs
// even group ids in the low nibble and odd ids in the high nibble.  B8 stores
// one group per byte.
[[nodiscard]] std::vector<std::uint8_t> PackMatchedGroupLabels(
    std::span<const std::uint32_t> labels,
    std::uint32_t word_bits,
    RepresentationCounters *counters = nullptr);

[[nodiscard]] std::vector<std::uint32_t> UnpackMatchedGroupLabels(
    std::span<const std::uint8_t> payload,
    std::uint32_t word_bits,
    RepresentationCounters *counters = nullptr);

// The global control always has 128 labels and widths in [0,8].  The paid
// payload is exactly 32 or 64 bytes.  Label bits and the whole stream are both
// least-significant-bit first; every high-tail padding bit is zero.
[[nodiscard]] GlobalPackedLabels PackGlobalLabels(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint8_t> bit_widths,
    std::size_t paid_payload_bytes,
    RepresentationCounters *counters = nullptr);

[[nodiscard]] std::vector<std::uint32_t> UnpackGlobalLabels(
    std::span<const std::uint8_t> payload,
    std::span<const std::uint8_t> bit_widths,
    RepresentationCounters *counters = nullptr);

// Serialized binary32 inputs are promoted directly to binary64.  Iteration is
// in label order and only a strict distance improvement replaces the winner,
// so an exact tie chooses the lower label.
[[nodiscard]] std::uint32_t AssignNearestScalarLabel(
    std::uint32_t value_bits,
    std::span<const std::uint32_t> centroid_bits,
    RepresentationCounters *counters = nullptr);

[[nodiscard]] std::uint32_t AssignNearestPoint2Label(
    const Binary32Point2 &value,
    std::span<const Binary32Point2> centroids,
    RepresentationCounters *counters = nullptr);

// Cartesian reconstruction order is mixed-radix order u=z0+K0*z1.
[[nodiscard]] std::vector<Binary32Point2> BuildCartesianReconstruction2(
    std::span<const std::uint32_t> axis0_centroid_bits,
    std::span<const std::uint32_t> axis1_centroid_bits,
    RepresentationCounters *counters = nullptr);

// Each valid matched entry computes coordinate-0 subtract/square, then
// coordinate-1 subtract/square, then one addition and one binary32 narrowing.
// reconstructions.size() may be below capacity for a product arm; the tail is
// filled with exact positive infinity.  Frozen capacities are 16 and 256.
[[nodiscard]] MatchedLookupTableBits BuildMatchedLookupTable(
    const Binary32Point2 &query,
    std::span<const Binary32Point2> reconstructions,
    std::uint32_t capacity,
    RepresentationCounters *counters = nullptr);

// The global table is the concatenation of the per-coordinate scalar tables.
// Every scalar entry performs one promoted subtract/square and one narrowing.
[[nodiscard]] GlobalLookupTableBits BuildGlobalLookupTable(
    std::span<const std::uint32_t> query_coordinate_bits,
    const std::vector<std::vector<std::uint32_t>> &centroid_bits_by_coordinate,
    std::span<const std::uint8_t> bit_widths,
    RepresentationCounters *counters = nullptr);

// Hand-written constants only.  Throws on any semantic mismatch and performs
// no I/O, random generation, or dataset access.
void RunRepresentationConstantSmoke();

} // namespace saq::a4_1s

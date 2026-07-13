#include "representation.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

namespace saq::a4_1s {
namespace {

[[nodiscard]] float FloatFromBits(std::uint32_t bits) noexcept {
    return std::bit_cast<float>(bits);
}

[[nodiscard]] std::uint32_t FloatBits(float value) noexcept {
    return std::bit_cast<std::uint32_t>(value);
}

[[nodiscard]] std::uint64_t DoubleBits(double value) noexcept {
    return std::bit_cast<std::uint64_t>(value);
}

[[nodiscard]] double RequireFinitePromoted(std::uint32_t bits,
                                           const char *description) {
    const float value = FloatFromBits(bits);
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(description) +
                                    " must be finite binary32");
    }
    return static_cast<double>(value);
}

void Increment(std::uint64_t RepresentationCounters::*field,
               RepresentationCounters *counters,
               std::uint64_t amount = 1) noexcept {
    if (counters != nullptr) {
        counters->*field += amount;
    }
}

[[nodiscard]] double ScalarSquaredDistance(
    std::uint32_t lhs_bits,
    std::uint32_t rhs_bits,
    RepresentationCounters *counters) {
    const double lhs = RequireFinitePromoted(lhs_bits, "scalar value");
    const double rhs = RequireFinitePromoted(rhs_bits, "scalar centroid");
    const double difference = lhs - rhs;
    const double squared = difference * difference;
    if (!std::isfinite(squared)) {
        throw std::overflow_error("binary64 scalar distance is nonfinite");
    }
    Increment(&RepresentationCounters::scalar_distance_evaluations, counters);
    Increment(&RepresentationCounters::binary64_subtractions, counters);
    Increment(&RepresentationCounters::binary64_multiplications, counters);
    return squared;
}

[[nodiscard]] double PointSquaredDistance(
    const Binary32Point2 &lhs,
    const Binary32Point2 &rhs,
    RepresentationCounters *counters) {
    const double lhs0 =
        RequireFinitePromoted(lhs.coordinate0_bits, "point coordinate 0");
    const double lhs1 =
        RequireFinitePromoted(lhs.coordinate1_bits, "point coordinate 1");
    const double rhs0 =
        RequireFinitePromoted(rhs.coordinate0_bits, "centroid coordinate 0");
    const double rhs1 =
        RequireFinitePromoted(rhs.coordinate1_bits, "centroid coordinate 1");

    const double difference0 = lhs0 - rhs0;
    const double square0 = difference0 * difference0;
    const double difference1 = lhs1 - rhs1;
    const double square1 = difference1 * difference1;
    const double total = square0 + square1;
    if (!std::isfinite(total)) {
        throw std::overflow_error("binary64 point distance is nonfinite");
    }
    Increment(&RepresentationCounters::point_distance_evaluations, counters);
    Increment(&RepresentationCounters::binary64_subtractions, counters, 2);
    Increment(&RepresentationCounters::binary64_multiplications, counters, 2);
    Increment(&RepresentationCounters::binary64_additions, counters);
    return total;
}

[[nodiscard]] LookupEntryBits NarrowLookupValue(
    double value,
    RepresentationCounters *counters) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::overflow_error("valid lookup pre-narrow value is invalid");
    }
    const float narrowed = static_cast<float>(value);
    if (!std::isfinite(narrowed)) {
        throw std::overflow_error("valid lookup binary32 value is nonfinite");
    }
    Increment(&RepresentationCounters::binary32_narrowings, counters);
    Increment(&RepresentationCounters::valid_lookup_entries, counters);
    return LookupEntryBits{
        true,
        DoubleBits(value),
        FloatBits(narrowed),
    };
}

[[nodiscard]] LookupEntryBits InvalidLookupValue(
    RepresentationCounters *counters) noexcept {
    Increment(&RepresentationCounters::invalid_lookup_entries, counters);
    return LookupEntryBits{
        false,
        kBinary64PositiveInfinityBits,
        kBinary32PositiveInfinityBits,
    };
}

void RequireFrozenWordBits(std::uint32_t word_bits) {
    if (word_bits != 4 && word_bits != 8) {
        throw std::invalid_argument("matched word bits must be 4 or 8");
    }
}

void RequirePaidPayloadBytes(std::size_t paid_payload_bytes) {
    if (paid_payload_bytes != 32 && paid_payload_bytes != 64) {
        throw std::invalid_argument("global paid payload must be 32 or 64 bytes");
    }
}

[[nodiscard]] std::uint32_t LabelLimit(std::uint8_t bit_width) {
    if (bit_width > 8) {
        throw std::invalid_argument("global bit width exceeds cap 8");
    }
    return std::uint32_t{1} << bit_width;
}

void RequireCondition(bool condition, const char *description) {
    if (!condition) {
        throw std::runtime_error(std::string("representation smoke failed: ") +
                                 description);
    }
}

} // namespace

void RepresentationCounters::Merge(
    const RepresentationCounters &other) noexcept {
    mixed_radix_encodes += other.mixed_radix_encodes;
    mixed_radix_decodes += other.mixed_radix_decodes;
    mixed_radix_digits += other.mixed_radix_digits;
    scalar_distance_evaluations += other.scalar_distance_evaluations;
    point_distance_evaluations += other.point_distance_evaluations;
    binary64_subtractions += other.binary64_subtractions;
    binary64_multiplications += other.binary64_multiplications;
    binary64_additions += other.binary64_additions;
    binary32_narrowings += other.binary32_narrowings;
    valid_lookup_entries += other.valid_lookup_entries;
    invalid_lookup_entries += other.invalid_lookup_entries;
    packed_labels_written += other.packed_labels_written;
    packed_labels_read += other.packed_labels_read;
    packed_bytes_written += other.packed_bytes_written;
    packed_bytes_read += other.packed_bytes_read;
    stream_bits_written += other.stream_bits_written;
    stream_bits_read += other.stream_bits_read;
    padding_bits_checked += other.padding_bits_checked;
    cartesian_reconstructions += other.cartesian_reconstructions;
}

std::uint64_t MixedRadixCapacity(
    std::span<const std::uint32_t> radices) {
    if (radices.empty()) {
        throw std::invalid_argument("mixed radix requires at least one digit");
    }
    std::uint64_t product = 1;
    for (const std::uint32_t radix : radices) {
        if (radix == 0) {
            throw std::invalid_argument("mixed radix base must be positive");
        }
        if (product > std::numeric_limits<std::uint64_t>::max() / radix) {
            throw std::overflow_error("mixed radix capacity overflows uint64");
        }
        product *= radix;
    }
    return product;
}

std::uint64_t MixedRadixEncode(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint32_t> radices,
    RepresentationCounters *counters) {
    if (labels.size() != radices.size() || labels.empty()) {
        throw std::invalid_argument("mixed-radix labels/radices shape mismatch");
    }
    const std::uint64_t capacity = MixedRadixCapacity(radices);
    std::uint64_t address = 0;
    std::uint64_t multiplier = 1;
    for (std::size_t index = 0; index < labels.size(); ++index) {
        if (labels[index] >= radices[index]) {
            throw std::invalid_argument("mixed-radix label exceeds radix");
        }
        address += static_cast<std::uint64_t>(labels[index]) * multiplier;
        multiplier *= radices[index];
    }
    if (address >= capacity) {
        throw std::logic_error("mixed-radix encoder produced invalid address");
    }
    Increment(&RepresentationCounters::mixed_radix_encodes, counters);
    Increment(&RepresentationCounters::mixed_radix_digits, counters,
              labels.size());
    return address;
}

std::vector<std::uint32_t> MixedRadixDecode(
    std::uint64_t address,
    std::span<const std::uint32_t> radices,
    RepresentationCounters *counters) {
    const std::uint64_t capacity = MixedRadixCapacity(radices);
    if (address >= capacity) {
        throw std::invalid_argument("mixed-radix address exceeds capacity");
    }
    std::vector<std::uint32_t> labels;
    labels.reserve(radices.size());
    std::uint64_t remainder = address;
    for (const std::uint32_t radix : radices) {
        labels.push_back(static_cast<std::uint32_t>(remainder % radix));
        remainder /= radix;
    }
    Increment(&RepresentationCounters::mixed_radix_decodes, counters);
    Increment(&RepresentationCounters::mixed_radix_digits, counters,
              radices.size());
    return labels;
}

std::vector<std::uint8_t> PackMatchedGroupLabels(
    std::span<const std::uint32_t> labels,
    std::uint32_t word_bits,
    RepresentationCounters *counters) {
    RequireFrozenWordBits(word_bits);
    if (labels.size() != kFrozenGroupCount) {
        throw std::invalid_argument("matched packing requires exactly 64 labels");
    }
    const std::uint32_t limit = std::uint32_t{1} << word_bits;
    const std::size_t byte_count = word_bits == 4 ? 32 : 64;
    std::vector<std::uint8_t> payload(byte_count, 0);
    for (std::size_t group = 0; group < labels.size(); ++group) {
        if (labels[group] >= limit) {
            throw std::invalid_argument("matched label exceeds word capacity");
        }
        if (word_bits == 4) {
            const std::size_t byte = group / 2;
            const std::uint32_t shift = group % 2 == 0 ? 0U : 4U;
            payload[byte] |=
                static_cast<std::uint8_t>(labels[group] << shift);
        } else {
            payload[group] = static_cast<std::uint8_t>(labels[group]);
        }
    }
    Increment(&RepresentationCounters::packed_labels_written, counters,
              labels.size());
    Increment(&RepresentationCounters::packed_bytes_written, counters,
              payload.size());
    return payload;
}

std::vector<std::uint32_t> UnpackMatchedGroupLabels(
    std::span<const std::uint8_t> payload,
    std::uint32_t word_bits,
    RepresentationCounters *counters) {
    RequireFrozenWordBits(word_bits);
    const std::size_t expected_bytes = word_bits == 4 ? 32 : 64;
    if (payload.size() != expected_bytes) {
        throw std::invalid_argument("matched payload has wrong byte length");
    }
    std::vector<std::uint32_t> labels(kFrozenGroupCount, 0);
    for (std::size_t group = 0; group < labels.size(); ++group) {
        if (word_bits == 4) {
            const std::uint32_t shift = group % 2 == 0 ? 0U : 4U;
            labels[group] = (payload[group / 2] >> shift) & 0x0fU;
        } else {
            labels[group] = payload[group];
        }
    }
    Increment(&RepresentationCounters::packed_labels_read, counters,
              labels.size());
    Increment(&RepresentationCounters::packed_bytes_read, counters,
              payload.size());
    return labels;
}

GlobalPackedLabels PackGlobalLabels(
    std::span<const std::uint32_t> labels,
    std::span<const std::uint8_t> bit_widths,
    std::size_t paid_payload_bytes,
    RepresentationCounters *counters) {
    RequirePaidPayloadBytes(paid_payload_bytes);
    if (labels.size() != kFrozenCoordinateCount ||
        bit_widths.size() != kFrozenCoordinateCount) {
        throw std::invalid_argument("global packing requires 128 labels/widths");
    }

    GlobalPackedLabels packed;
    packed.bytes.assign(paid_payload_bytes, 0);
    packed.bit_offsets.reserve(kFrozenCoordinateCount);
    std::uint64_t offset = 0;
    for (std::size_t coordinate = 0; coordinate < labels.size(); ++coordinate) {
        const std::uint8_t width = bit_widths[coordinate];
        const std::uint32_t limit = LabelLimit(width);
        if (labels[coordinate] >= limit) {
            throw std::invalid_argument("global label exceeds selected bit width");
        }
        if (offset + width > paid_payload_bytes * 8ULL) {
            throw std::invalid_argument("global bit widths exceed paid payload");
        }
        packed.bit_offsets.push_back(static_cast<std::uint32_t>(offset));
        for (std::uint32_t bit = 0; bit < width; ++bit) {
            if (((labels[coordinate] >> bit) & 1U) != 0U) {
                const std::uint64_t stream_bit = offset + bit;
                packed.bytes[stream_bit / 8U] |= static_cast<std::uint8_t>(
                    std::uint8_t{1} << (stream_bit % 8U));
            }
        }
        offset += width;
    }
    packed.used_bits = static_cast<std::uint32_t>(offset);
    Increment(&RepresentationCounters::packed_labels_written, counters,
              labels.size());
    Increment(&RepresentationCounters::packed_bytes_written, counters,
              packed.bytes.size());
    Increment(&RepresentationCounters::stream_bits_written, counters, offset);
    return packed;
}

std::vector<std::uint32_t> UnpackGlobalLabels(
    std::span<const std::uint8_t> payload,
    std::span<const std::uint8_t> bit_widths,
    RepresentationCounters *counters) {
    RequirePaidPayloadBytes(payload.size());
    if (bit_widths.size() != kFrozenCoordinateCount) {
        throw std::invalid_argument("global unpacking requires 128 bit widths");
    }
    std::vector<std::uint32_t> labels(kFrozenCoordinateCount, 0);
    std::uint64_t offset = 0;
    for (std::size_t coordinate = 0; coordinate < labels.size(); ++coordinate) {
        const std::uint8_t width = bit_widths[coordinate];
        static_cast<void>(LabelLimit(width));
        if (offset + width > payload.size() * 8ULL) {
            throw std::invalid_argument("global bit widths exceed payload");
        }
        std::uint32_t label = 0;
        for (std::uint32_t bit = 0; bit < width; ++bit) {
            const std::uint64_t stream_bit = offset + bit;
            const std::uint32_t value =
                (payload[stream_bit / 8U] >> (stream_bit % 8U)) & 1U;
            label |= value << bit;
        }
        labels[coordinate] = label;
        offset += width;
    }
    for (std::uint64_t bit = offset; bit < payload.size() * 8ULL; ++bit) {
        if (((payload[bit / 8U] >> (bit % 8U)) & 1U) != 0U) {
            throw std::invalid_argument("global payload has nonzero high-tail padding");
        }
    }
    Increment(&RepresentationCounters::packed_labels_read, counters,
              labels.size());
    Increment(&RepresentationCounters::packed_bytes_read, counters,
              payload.size());
    Increment(&RepresentationCounters::stream_bits_read, counters, offset);
    Increment(&RepresentationCounters::padding_bits_checked, counters,
              payload.size() * 8ULL - offset);
    return labels;
}

std::uint32_t AssignNearestScalarLabel(
    std::uint32_t value_bits,
    std::span<const std::uint32_t> centroid_bits,
    RepresentationCounters *counters) {
    if (centroid_bits.empty()) {
        throw std::invalid_argument("scalar assignment requires a centroid");
    }
    std::uint32_t best_label = 0;
    double best_distance = std::numeric_limits<double>::infinity();
    for (std::size_t label = 0; label < centroid_bits.size(); ++label) {
        const double distance =
            ScalarSquaredDistance(value_bits, centroid_bits[label], counters);
        if (distance < best_distance) {
            best_distance = distance;
            best_label = static_cast<std::uint32_t>(label);
        }
    }
    return best_label;
}

std::uint32_t AssignNearestPoint2Label(
    const Binary32Point2 &value,
    std::span<const Binary32Point2> centroids,
    RepresentationCounters *counters) {
    if (centroids.empty()) {
        throw std::invalid_argument("point assignment requires a centroid");
    }
    std::uint32_t best_label = 0;
    double best_distance = std::numeric_limits<double>::infinity();
    for (std::size_t label = 0; label < centroids.size(); ++label) {
        const double distance = PointSquaredDistance(value, centroids[label],
                                                     counters);
        if (distance < best_distance) {
            best_distance = distance;
            best_label = static_cast<std::uint32_t>(label);
        }
    }
    return best_label;
}

std::vector<Binary32Point2> BuildCartesianReconstruction2(
    std::span<const std::uint32_t> axis0_centroid_bits,
    std::span<const std::uint32_t> axis1_centroid_bits,
    RepresentationCounters *counters) {
    if (axis0_centroid_bits.empty() || axis1_centroid_bits.empty()) {
        throw std::invalid_argument("Cartesian reconstruction axes must be nonempty");
    }
    for (const std::uint32_t bits : axis0_centroid_bits) {
        static_cast<void>(RequireFinitePromoted(bits, "axis-0 centroid"));
    }
    for (const std::uint32_t bits : axis1_centroid_bits) {
        static_cast<void>(RequireFinitePromoted(bits, "axis-1 centroid"));
    }
    if (axis0_centroid_bits.size() >
        std::numeric_limits<std::size_t>::max() /
            axis1_centroid_bits.size()) {
        throw std::overflow_error("Cartesian reconstruction size overflows");
    }
    std::vector<Binary32Point2> result;
    result.reserve(axis0_centroid_bits.size() * axis1_centroid_bits.size());
    for (const std::uint32_t axis1 : axis1_centroid_bits) {
        for (const std::uint32_t axis0 : axis0_centroid_bits) {
            result.push_back(Binary32Point2{axis0, axis1});
        }
    }
    Increment(&RepresentationCounters::cartesian_reconstructions, counters,
              result.size());
    return result;
}

MatchedLookupTableBits BuildMatchedLookupTable(
    const Binary32Point2 &query,
    std::span<const Binary32Point2> reconstructions,
    std::uint32_t capacity,
    RepresentationCounters *counters) {
    if (capacity != 16 && capacity != 256) {
        throw std::invalid_argument("matched lookup capacity must be 16 or 256");
    }
    if (reconstructions.empty() || reconstructions.size() > capacity) {
        throw std::invalid_argument("matched lookup valid-state count is invalid");
    }
    static_cast<void>(RequireFinitePromoted(query.coordinate0_bits,
                                            "query coordinate 0"));
    static_cast<void>(RequireFinitePromoted(query.coordinate1_bits,
                                            "query coordinate 1"));

    MatchedLookupTableBits table;
    table.capacity = capacity;
    table.valid_states = static_cast<std::uint32_t>(reconstructions.size());
    table.entries.reserve(capacity);
    for (const Binary32Point2 &reconstruction : reconstructions) {
        const double distance =
            PointSquaredDistance(query, reconstruction, counters);
        table.entries.push_back(NarrowLookupValue(distance, counters));
    }
    while (table.entries.size() < capacity) {
        table.entries.push_back(InvalidLookupValue(counters));
    }
    return table;
}

GlobalLookupTableBits BuildGlobalLookupTable(
    std::span<const std::uint32_t> query_coordinate_bits,
    const std::vector<std::vector<std::uint32_t>> &centroid_bits_by_coordinate,
    std::span<const std::uint8_t> bit_widths,
    RepresentationCounters *counters) {
    if (query_coordinate_bits.size() != centroid_bits_by_coordinate.size() ||
        query_coordinate_bits.size() != bit_widths.size() ||
        query_coordinate_bits.empty()) {
        throw std::invalid_argument("global lookup query/codebook shape mismatch");
    }
    if (query_coordinate_bits.size() != kFrozenCoordinateCount) {
        throw std::invalid_argument("global lookup requires 128 coordinates");
    }

    GlobalLookupTableBits table;
    table.coordinate_offsets.reserve(query_coordinate_bits.size() + 1);
    table.coordinate_offsets.push_back(0);
    std::size_t total_entries = 0;
    for (std::size_t coordinate = 0;
         coordinate < centroid_bits_by_coordinate.size();
         ++coordinate) {
        const auto &centroids = centroid_bits_by_coordinate[coordinate];
        const std::uint32_t expected_cardinality = LabelLimit(bit_widths[coordinate]);
        if (centroids.size() != expected_cardinality) {
            throw std::invalid_argument(
                "global scalar alphabet does not match its dyadic bit width");
        }
        if (total_entries >
            std::numeric_limits<std::uint32_t>::max() - centroids.size()) {
            throw std::overflow_error("global lookup offset overflows uint32");
        }
        total_entries += centroids.size();
        table.coordinate_offsets.push_back(
            static_cast<std::uint32_t>(total_entries));
    }
    table.entries.reserve(total_entries);
    for (std::size_t coordinate = 0;
         coordinate < query_coordinate_bits.size();
         ++coordinate) {
        for (const std::uint32_t centroid_bits :
             centroid_bits_by_coordinate[coordinate]) {
            const double distance = ScalarSquaredDistance(
                query_coordinate_bits[coordinate], centroid_bits, counters);
            table.entries.push_back(NarrowLookupValue(distance, counters));
        }
    }
    return table;
}

void RunRepresentationConstantSmoke() {
    RepresentationCounters counters;

    const std::vector<std::uint32_t> radices{3, 5};
    const std::vector<std::uint32_t> digits{2, 4};
    const std::uint64_t address = MixedRadixEncode(digits, radices, &counters);
    RequireCondition(address == 14, "mixed-radix encode");
    RequireCondition(MixedRadixDecode(address, radices, &counters) == digits,
                     "mixed-radix decode");

    std::vector<std::uint32_t> matched_labels(kFrozenGroupCount, 0);
    for (std::size_t group = 0; group < matched_labels.size(); ++group) {
        matched_labels[group] = static_cast<std::uint32_t>(group % 16);
    }
    const auto b4 = PackMatchedGroupLabels(matched_labels, 4, &counters);
    RequireCondition(b4.size() == 32 && b4.front() == 0x10U,
                     "B4 nibble order");
    RequireCondition(UnpackMatchedGroupLabels(b4, 4, &counters) ==
                         matched_labels,
                     "B4 round-trip");
    const auto b8 = PackMatchedGroupLabels(matched_labels, 8, &counters);
    RequireCondition(b8.size() == 64 && b8[15] == 15U,
                     "B8 byte order");
    RequireCondition(UnpackMatchedGroupLabels(b8, 8, &counters) ==
                         matched_labels,
                     "B8 round-trip");

    std::vector<std::uint32_t> global_labels(kFrozenCoordinateCount, 0);
    std::vector<std::uint8_t> global_widths(kFrozenCoordinateCount, 0);
    global_widths[0] = 1;
    global_widths[1] = 2;
    global_widths[2] = 3;
    global_labels[0] = 1;
    global_labels[1] = 2;
    global_labels[2] = 5;
    const GlobalPackedLabels global =
        PackGlobalLabels(global_labels, global_widths, 32, &counters);
    RequireCondition(global.used_bits == 6 && global.bytes.front() == 0x2dU,
                     "global LSB-first stream");
    RequireCondition(UnpackGlobalLabels(global.bytes, global_widths, &counters) ==
                         global_labels,
                     "global round-trip");

    const std::uint32_t zero = FloatBits(0.0F);
    const std::uint32_t minus_one = FloatBits(-1.0F);
    const std::uint32_t plus_one = FloatBits(1.0F);
    const std::vector<std::uint32_t> tied_centroids{minus_one, plus_one};
    RequireCondition(AssignNearestScalarLabel(zero, tied_centroids, &counters) ==
                         0,
                     "scalar lower-label tie");
    const Binary32Point2 origin{zero, zero};
    const std::vector<Binary32Point2> tied_points{
        Binary32Point2{minus_one, zero},
        Binary32Point2{plus_one, zero},
    };
    RequireCondition(AssignNearestPoint2Label(origin, tied_points, &counters) ==
                         0,
                     "point lower-label tie");

    const std::vector<Binary32Point2> one_reconstruction{
        Binary32Point2{FloatBits(3.0F), FloatBits(4.0F)},
    };
    const MatchedLookupTableBits matched =
        BuildMatchedLookupTable(origin, one_reconstruction, 16, &counters);
    RequireCondition(matched.entries.size() == 16 &&
                         matched.entries[0].valid &&
                         matched.entries[0].pre_narrow_binary64_bits ==
                             DoubleBits(25.0) &&
                         matched.entries[0].stored_binary32_bits ==
                             FloatBits(25.0F),
                     "matched lookup two precision layers");
    RequireCondition(!matched.entries[1].valid &&
                         matched.entries[1].stored_binary32_bits ==
                             kBinary32PositiveInfinityBits,
                     "matched invalid infinity");

    std::vector<std::uint32_t> global_query(kFrozenCoordinateCount, zero);
    std::vector<std::vector<std::uint32_t>> global_centroids(
        kFrozenCoordinateCount, std::vector<std::uint32_t>{zero});
    for (std::size_t coordinate = 0; coordinate < global_centroids.size();
         ++coordinate) {
        global_centroids[coordinate].assign(
            LabelLimit(global_widths[coordinate]), zero);
    }
    global_centroids[0] = tied_centroids;
    const GlobalLookupTableBits scalar_table =
        BuildGlobalLookupTable(global_query, global_centroids, global_widths,
                               &counters);
    RequireCondition(scalar_table.coordinate_offsets.size() == 129 &&
                         scalar_table.entries.size() == 139 &&
                         scalar_table.entries[0].pre_narrow_binary64_bits ==
                             DoubleBits(1.0) &&
                         scalar_table.entries[0].stored_binary32_bits ==
                             FloatBits(1.0F),
                     "global scalar lookup layers");
    RequireCondition(counters.binary32_narrowings ==
                         counters.valid_lookup_entries &&
                         counters.invalid_lookup_entries == 15 &&
                         counters.packed_bytes_written == 128,
                     "representation counters");
}

} // namespace saq::a4_1s

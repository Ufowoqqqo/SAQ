#pragma once

#include "allocation_curve_io.hpp"
#include "exact_quantizer.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_1s {
namespace allocation_item_detail {

inline constexpr std::string_view kInputMagic = "A4ALI001";
inline constexpr std::string_view kInputTerminal = "A4AIEND1";
inline constexpr std::string_view kOutputMagic = "A4ALO001";
inline constexpr std::string_view kOutputTerminal = "A4AOEND1";
inline constexpr std::uint32_t kSchemaVersion = 1;
inline constexpr std::uint32_t kProductKind = 1;
inline constexpr std::uint32_t kGlobalKind = 2;
inline constexpr std::uint32_t kArbitraryCardinalitySet = 0;
inline constexpr std::uint32_t kDyadicCardinalitySet = 1;
inline constexpr std::uint32_t kFrozenCoordinateCount = 128;
inline constexpr std::uint32_t kMaximumCardinality = 256;
inline constexpr std::uint32_t kProductItemCount = 256;
inline constexpr std::uint32_t kGlobalB4ItemId = 256;
inline constexpr std::uint32_t kGlobalB8ItemId = 257;

struct TaggedCurve {
    std::uint32_t id{0};
    ScalarCurveResult curve;
};

class AllocationItemWriter {
  public:
    explicit AllocationItemWriter(const std::string &path)
        : output_(path, std::ios::binary | std::ios::trunc) {
        if (!output_) {
            throw std::runtime_error("failed to create allocation-item output");
        }
    }

    void WriteU8(std::uint8_t value) {
        output_.put(static_cast<char>(value));
        RequireGood("uint8");
    }

    void WriteU32(std::uint32_t value) {
        std::array<char, 4> bytes{};
        for (std::size_t index = 0; index < bytes.size(); ++index) {
            bytes[index] = static_cast<char>(value >> (8U * index));
        }
        WriteBytes(std::string_view(bytes.data(), bytes.size()));
    }

    void WriteI32(std::int32_t value) {
        WriteU32(std::bit_cast<std::uint32_t>(value));
    }

    void WriteU64(std::uint64_t value) {
        std::array<char, 8> bytes{};
        for (std::size_t index = 0; index < bytes.size(); ++index) {
            bytes[index] = static_cast<char>(value >> (8U * index));
        }
        WriteBytes(std::string_view(bytes.data(), bytes.size()));
    }

    void WriteBytes(std::string_view bytes) {
        output_.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        RequireGood("bytes");
    }

    void WriteObjective(const CanonicalScaledRational &objective) {
        if (objective.binary_exponent != -298 || objective.numerator < 0 ||
            objective.denominator <= 0) {
            throw std::logic_error(
                "allocation-item output objective is not canonical");
        }
        const std::string numerator = objective.numerator.get_str();
        const std::string denominator = objective.denominator.get_str();
        if (numerator.size() > std::numeric_limits<std::uint32_t>::max() ||
            denominator.size() > std::numeric_limits<std::uint32_t>::max()) {
            throw std::overflow_error(
                "allocation-item objective text exceeds uint32 framing");
        }
        WriteI32(objective.binary_exponent);
        WriteU32(static_cast<std::uint32_t>(numerator.size()));
        WriteBytes(numerator);
        WriteU32(static_cast<std::uint32_t>(denominator.size()));
        WriteBytes(denominator);
    }

    void Finish() {
        WriteBytes(kOutputTerminal);
        output_.flush();
        RequireGood("flush");
    }

  private:
    void RequireGood(const char *field) {
        if (!output_) {
            throw std::runtime_error(
                std::string("failed to write allocation-item ") + field);
        }
    }

    std::ofstream output_;
};

[[nodiscard]] inline bool IsFrozenProductCapacity(
    std::uint32_t capacity) noexcept {
    return capacity == 16 || capacity == 256;
}

[[nodiscard]] inline bool IsFrozenGlobalBudget(
    std::uint32_t budget) noexcept {
    return budget == 256 || budget == 512;
}

[[nodiscard]] inline std::uint64_t ExpectedProductCandidateCount(
    std::uint32_t capacity,
    bool dyadic_only) {
    return dyadic_only ? std::bit_width(capacity)
                       : static_cast<std::uint64_t>(capacity);
}

[[nodiscard]] inline std::uint64_t ExpectedGlobalTransitionCount(
    std::uint32_t coordinate_count,
    std::uint32_t bit_budget) {
    std::uint64_t result = 0;
    for (std::uint32_t coordinate = 0;
         coordinate < coordinate_count;
         ++coordinate) {
        const std::uint32_t maximum_previous_bits =
            std::min<std::uint32_t>(8U * coordinate, bit_budget);
        for (std::uint32_t used = 0; used <= maximum_previous_bits; ++used) {
            result += std::min<std::uint32_t>(8U, bit_budget - used) + 1U;
        }
    }
    return result;
}

[[nodiscard]] inline TaggedCurve ReadTaggedCurve(
    AllocationCurveReader *reader,
    std::uint32_t maximum_cardinality) {
    TaggedCurve result;
    result.id = reader->ReadU32("curve_id");
    if (result.id >= kFrozenCoordinateCount) {
        throw std::runtime_error("allocation-item curve id is outside [0,127]");
    }
    result.curve = ReadExactAllocationCurve(reader, maximum_cardinality);
    return result;
}

inline void RequireCommonHeader(AllocationCurveReader *reader,
                                std::uint32_t *kind,
                                std::uint32_t *item_id) {
    reader->RequireMagic(kInputMagic);
    if (reader->ReadU32("schema_version") != kSchemaVersion) {
        throw std::runtime_error("allocation-item schema version mismatch");
    }
    *kind = reader->ReadU32("item_kind");
    *item_id = reader->ReadU32("item_id");
    if (*kind == kProductKind) {
        if (*item_id >= kProductItemCount) {
            throw std::runtime_error(
                "product allocation item id is outside [0,255]");
        }
    } else if (*kind == kGlobalKind) {
        if (*item_id != kGlobalB4ItemId && *item_id != kGlobalB8ItemId) {
            throw std::runtime_error(
                "global allocation item id must be 256 or 257");
        }
    } else {
        throw std::runtime_error("allocation-item kind must be 1 or 2");
    }
}

inline void WriteOutputHeader(AllocationItemWriter *writer,
                              std::uint32_t kind,
                              std::uint32_t item_id) {
    writer->WriteBytes(kOutputMagic);
    writer->WriteU32(kSchemaVersion);
    writer->WriteU32(kind);
    writer->WriteU32(item_id);
}

inline void RunProductItem(AllocationCurveReader *reader,
                           const std::string &output_path,
                           std::uint32_t item_id) {
    const std::uint32_t capacity = reader->ReadU32("capacity");
    const std::uint32_t cardinality_set =
        reader->ReadU32("cardinality_set");
    const std::uint32_t curve_count = reader->ReadU32("curve_count");
    const std::uint32_t maximum_cardinality =
        reader->ReadU32("maximum_cardinality");
    if (!IsFrozenProductCapacity(capacity) ||
        (cardinality_set != kArbitraryCardinalitySet &&
         cardinality_set != kDyadicCardinalitySet) ||
        curve_count != 2 || maximum_cardinality != capacity) {
        throw std::runtime_error(
            "product item descriptor is outside the frozen schema");
    }

    TaggedCurve first = ReadTaggedCurve(reader, maximum_cardinality);
    TaggedCurve second = ReadTaggedCurve(reader, maximum_cardinality);
    if ((first.id % 2U) != 0U || second.id != first.id + 1U) {
        throw std::runtime_error(
            "product allocation curve ids must be one frozen adjacent pair");
    }
    const std::uint32_t rate_index = capacity == 16 ? 0U : 1U;
    const std::uint32_t group_id = first.id / 2U;
    const std::uint32_t expected_item_id =
        ((rate_index * 64U + group_id) * 2U) + cardinality_set;
    if (item_id != expected_item_id) {
        throw std::runtime_error(
            "product item id does not match rate/group/cardinality set");
    }
    reader->RequireBytes(kInputTerminal, "input terminal");
    reader->RequireEof();

    const bool dyadic_only = cardinality_set == kDyadicCardinalitySet;
    const ProductAllocation allocation = AllocateProduct2(
        first.curve, second.curve, capacity,
        dyadic_only ? ProductCardinalitySet::kPowersOfTwo
                    : ProductCardinalitySet::kAllPositiveIntegers);
    const std::uint64_t expected_candidates =
        ExpectedProductCandidateCount(capacity, dyadic_only);
    if (allocation.capacity != capacity ||
        allocation.first_cardinality == 0 ||
        allocation.second_cardinality == 0 ||
        allocation.used_states !=
            static_cast<std::uint64_t>(allocation.first_cardinality) *
                allocation.second_cardinality ||
        allocation.used_states > capacity ||
        allocation.optimized_candidate_evaluation_count !=
            expected_candidates) {
        throw std::logic_error(
            "product allocation violates the item result contract");
    }

    const ScalarSolution &first_selected =
        first.curve.at(allocation.first_cardinality);
    const ScalarSolution &second_selected =
        second.curve.at(allocation.second_cardinality);
    const bool first_reachable =
        first_selected.effective_cardinality == allocation.first_cardinality;
    const bool second_reachable =
        second_selected.effective_cardinality == allocation.second_cardinality;
    if (allocation.nominal_alphabets_reachable !=
        (first_reachable && second_reachable)) {
        throw std::logic_error("product allocation reachability mismatch");
    }

    AllocationItemWriter writer(output_path);
    WriteOutputHeader(&writer, kProductKind, item_id);
    writer.WriteU32(capacity);
    writer.WriteU32(cardinality_set);
    writer.WriteU32(curve_count);
    writer.WriteU32(first.id);
    writer.WriteU32(allocation.first_cardinality);
    writer.WriteU32(first_selected.effective_cardinality);
    writer.WriteU8(first_reachable ? 1U : 0U);
    writer.WriteU32(second.id);
    writer.WriteU32(allocation.second_cardinality);
    writer.WriteU32(second_selected.effective_cardinality);
    writer.WriteU8(second_reachable ? 1U : 0U);
    writer.WriteU64(allocation.used_states);
    writer.WriteU8(allocation.nominal_alphabets_reachable ? 1U : 0U);
    writer.WriteObjective(allocation.sse);
    writer.WriteU64(allocation.optimized_candidate_evaluation_count);
    writer.Finish();
}

inline void RunGlobalItem(AllocationCurveReader *reader,
                          const std::string &output_path,
                          std::uint32_t item_id) {
    const std::uint32_t bit_budget = reader->ReadU32("bit_budget");
    const std::uint32_t curve_count = reader->ReadU32("curve_count");
    const std::uint32_t maximum_cardinality =
        reader->ReadU32("maximum_cardinality");
    if (!IsFrozenGlobalBudget(bit_budget) ||
        curve_count != kFrozenCoordinateCount ||
        maximum_cardinality != kMaximumCardinality) {
        throw std::runtime_error(
            "global item descriptor is outside the frozen schema");
    }
    if ((item_id == kGlobalB4ItemId && bit_budget != 256) ||
        (item_id == kGlobalB8ItemId && bit_budget != 512)) {
        throw std::runtime_error(
            "global item id does not match its frozen bit budget");
    }

    std::vector<TaggedCurve> tagged_curves;
    std::vector<ScalarCurveResult> curves;
    tagged_curves.reserve(curve_count);
    curves.reserve(curve_count);
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
        TaggedCurve tagged =
            ReadTaggedCurve(reader, maximum_cardinality);
        if (tagged.id != coordinate) {
            throw std::runtime_error(
                "global allocation curve ids must be exactly 0..127");
        }
        curves.push_back(tagged.curve);
        tagged_curves.push_back(std::move(tagged));
    }
    reader->RequireBytes(kInputTerminal, "input terminal");
    reader->RequireEof();

    const GlobalDyadicAllocation allocation =
        AllocateGlobalDyadicCap8(curves, bit_budget);
    const std::uint64_t expected_transitions =
        ExpectedGlobalTransitionCount(curve_count, bit_budget);
    if (allocation.bit_budget != bit_budget ||
        allocation.bit_widths.size() != curve_count ||
        allocation.used_bits > bit_budget ||
        allocation.transition_evaluation_count != expected_transitions) {
        throw std::logic_error(
            "global allocation violates the item result contract");
    }
    std::uint32_t replay_used_bits = 0;
    bool replay_reachable = true;
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
        const std::uint8_t width = allocation.bit_widths[coordinate];
        if (width > 8) {
            throw std::logic_error("global allocation width exceeds cap 8");
        }
        replay_used_bits += width;
        const std::uint32_t cardinality = std::uint32_t{1} << width;
        replay_reachable =
            replay_reachable &&
            curves[coordinate].at(cardinality).effective_cardinality ==
                cardinality;
    }
    if (replay_used_bits != allocation.used_bits ||
        replay_reachable != allocation.nominal_alphabets_reachable) {
        throw std::logic_error("global allocation diagnostic replay mismatch");
    }

    AllocationItemWriter writer(output_path);
    WriteOutputHeader(&writer, kGlobalKind, item_id);
    writer.WriteU32(bit_budget);
    writer.WriteU32(curve_count);
    writer.WriteU32(allocation.used_bits);
    writer.WriteU8(allocation.nominal_alphabets_reachable ? 1U : 0U);
    writer.WriteObjective(allocation.sse);
    writer.WriteU64(allocation.transition_evaluation_count);
    writer.WriteU32(curve_count);
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
        const std::uint8_t width = allocation.bit_widths[coordinate];
        const std::uint32_t cardinality = std::uint32_t{1} << width;
        const std::uint32_t effective =
            curves[coordinate].at(cardinality).effective_cardinality;
        writer.WriteU32(tagged_curves[coordinate].id);
        writer.WriteU8(width);
        writer.WriteU32(cardinality);
        writer.WriteU32(effective);
        writer.WriteU8(effective == cardinality ? 1U : 0U);
    }
    writer.Finish();
}

} // namespace allocation_item_detail

inline void WriteAllocationItemFiles(const std::string &input_path,
                                     const std::string &output_path) {
    AllocationCurveReader reader(input_path);
    std::uint32_t kind = 0;
    std::uint32_t item_id = 0;
    allocation_item_detail::RequireCommonHeader(&reader, &kind, &item_id);
    if (kind == allocation_item_detail::kProductKind) {
        allocation_item_detail::RunProductItem(&reader, output_path, item_id);
    } else {
        allocation_item_detail::RunGlobalItem(&reader, output_path, item_id);
    }
}

} // namespace saq::a4_1s

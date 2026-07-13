#include "representation_cli.hpp"

#include "allocation_curve_io.hpp"
#include "exhaustive_product_reference.hpp"
#include "exact_quantizer.hpp"
#include "representation.hpp"

#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_1s {
namespace {

constexpr std::uint64_t kTinyCaseCount = 780;
constexpr std::uint64_t kExpectedAllocationRecordCount = 2'433'600;
constexpr std::uint64_t kExpectedExhaustiveTupleEvaluationCount = 958'838'400;
constexpr std::uint64_t kExpectedOptimizedCandidateEvaluationCount = 174'002'400;
constexpr std::array<std::uint32_t, 5> kIntegerUniverseBits{
    0xc0000000U, // -2
    0xbf800000U, // -1
    0x00000000U, //  0
    0x3f800000U, //  1
    0x40000000U, //  2
};
constexpr std::array<std::uint32_t, 2> kCapacities{16, 256};
constexpr std::uint32_t kAllocationCurveCount = 128;

struct GroupAllocationDecision {
    std::uint32_t word_bits{0};
    std::uint32_t group_id{0};
    ProductAllocation dyadic;
    ProductAllocation arbitrary;
};

struct EvpContextDeleter {
    void operator()(EVP_MD_CTX *context) const noexcept {
        EVP_MD_CTX_free(context);
    }
};

class Sha256Accumulator {
  public:
    Sha256Accumulator()
        : context_(EVP_MD_CTX_new()) {
        if (context_ == nullptr ||
            EVP_DigestInit_ex(context_.get(), EVP_sha256(), nullptr) != 1) {
            throw std::runtime_error("failed to initialize SHA-256 accumulator");
        }
    }

    Sha256Accumulator(const Sha256Accumulator &) = delete;
    Sha256Accumulator &operator=(const Sha256Accumulator &) = delete;

    void Update(std::string_view bytes) {
        if (finalized_) {
            throw std::logic_error("cannot update finalized SHA-256 accumulator");
        }
        if (EVP_DigestUpdate(context_.get(), bytes.data(), bytes.size()) != 1) {
            throw std::runtime_error("failed to update SHA-256 accumulator");
        }
    }

    [[nodiscard]] std::string FinalHex() {
        if (finalized_) {
            throw std::logic_error("SHA-256 accumulator finalized twice");
        }
        std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
        unsigned int digest_size = 0;
        if (EVP_DigestFinal_ex(context_.get(), digest.data(), &digest_size) != 1 ||
            digest_size != 32) {
            throw std::runtime_error("failed to finalize SHA-256 accumulator");
        }
        finalized_ = true;
        std::ostringstream encoded;
        encoded << std::hex << std::setfill('0');
        for (unsigned int index = 0; index < digest_size; ++index) {
            encoded << std::setw(2) << static_cast<unsigned int>(digest[index]);
        }
        return encoded.str();
    }

  private:
    std::unique_ptr<EVP_MD_CTX, EvpContextDeleter> context_;
    bool finalized_{false};
};

void EnumerateWeights(
    const std::vector<std::uint32_t> &support_bits,
    std::size_t position,
    std::vector<std::uint64_t> *weights,
    std::vector<std::vector<WeightedBinary32>> *cases) {
    if (position == support_bits.size()) {
        std::vector<WeightedBinary32> samples;
        samples.reserve(support_bits.size());
        for (std::size_t index = 0; index < support_bits.size(); ++index) {
            samples.push_back(WeightedBinary32{
                support_bits[index],
                (*weights)[index],
                static_cast<std::uint64_t>(index),
            });
        }
        cases->push_back(std::move(samples));
        return;
    }
    for (std::uint64_t weight = 1; weight <= 3; ++weight) {
        (*weights)[position] = weight;
        EnumerateWeights(support_bits, position + 1, weights, cases);
    }
}

void EnumerateSupportSubsets(
    std::size_t target_size,
    std::size_t next_universe_index,
    std::vector<std::uint32_t> *support_bits,
    std::vector<std::vector<WeightedBinary32>> *cases) {
    if (support_bits->size() == target_size) {
        std::vector<std::uint64_t> weights(target_size, 1);
        EnumerateWeights(*support_bits, 0, &weights, cases);
        return;
    }
    const std::size_t remaining = target_size - support_bits->size();
    for (std::size_t universe_index = next_universe_index;
         universe_index + remaining <= kIntegerUniverseBits.size();
         ++universe_index) {
        support_bits->push_back(kIntegerUniverseBits[universe_index]);
        EnumerateSupportSubsets(target_size, universe_index + 1, support_bits,
                                cases);
        support_bits->pop_back();
    }
}

[[nodiscard]] std::vector<std::vector<WeightedBinary32>> BuildTinyCases() {
    std::vector<std::vector<WeightedBinary32>> cases;
    cases.reserve(kTinyCaseCount);
    for (std::size_t support_size = 1; support_size <= 4; ++support_size) {
        std::vector<std::uint32_t> support_bits;
        support_bits.reserve(support_size);
        EnumerateSupportSubsets(support_size, 0, &support_bits, &cases);
    }
    if (cases.size() != kTinyCaseCount) {
        throw std::logic_error("frozen tiny-case enumeration is not 780 cases");
    }
    return cases;
}

[[nodiscard]] bool IsPowerOfTwo(std::uint32_t value) noexcept {
    return value != 0 && (value & (value - 1U)) == 0;
}

void ValidateAllocation(const ProductAllocation &allocation,
                        std::uint32_t capacity,
                        bool dyadic_only) {
    const std::uint64_t expected_candidate_evaluations =
        dyadic_only ? std::bit_width(capacity)
                    : static_cast<std::uint64_t>(capacity);
    if (allocation.capacity != capacity ||
        allocation.first_cardinality == 0 ||
        allocation.second_cardinality == 0 ||
        allocation.used_states !=
            static_cast<std::uint64_t>(allocation.first_cardinality) *
                allocation.second_cardinality ||
        allocation.used_states > capacity ||
        allocation.optimized_candidate_evaluation_count !=
            expected_candidate_evaluations) {
        throw std::logic_error("production allocation violates capacity contract");
    }
    if (dyadic_only &&
        (!IsPowerOfTwo(allocation.first_cardinality) ||
         !IsPowerOfTwo(allocation.second_cardinality))) {
        throw std::logic_error("dyadic allocator selected a nondyadic cardinality");
    }
    if (allocation.sse.binary_exponent != -298 ||
        allocation.sse.numerator < 0 ||
        allocation.sse.denominator <= 0) {
        throw std::logic_error("allocation objective violates exact SSE schema");
    }
}

[[nodiscard]] std::string AllocationPreimage(
    const ProductAllocation &allocation,
    bool dyadic_only) {
    // Keys are deliberately emitted in lexicographic order.  Every dynamic
    // string is an integer digit sequence, so no JSON escaping is required.
    std::string result;
    result.reserve(256);
    result += "{\"capacity\":";
    result += std::to_string(allocation.capacity);
    result += ",\"cardinalities\":[";
    result += std::to_string(allocation.first_cardinality);
    result += ',';
    result += std::to_string(allocation.second_cardinality);
    result += "],\"dyadic_only\":";
    result += dyadic_only ? "true" : "false";
    result += ",\"objective\":{\"binary_grid_exponent\":-298,";
    result += "\"denominator\":\"";
    result += allocation.sse.denominator.get_str();
    result += "\",\"numerator\":\"";
    result += allocation.sse.numerator.get_str();
    result += "\"},\"used_states\":";
    result += std::to_string(allocation.used_states);
    result += "}\n";
    return result;
}

[[nodiscard]] std::string ExhaustiveAllocationPreimage(
    const ExhaustiveProductReferenceDecision &allocation,
    bool dyadic_only) {
    std::string result;
    result.reserve(256);
    result += "{\"capacity\":";
    result += std::to_string(allocation.capacity);
    result += ",\"cardinalities\":[";
    result += std::to_string(allocation.first_cardinality);
    result += ',';
    result += std::to_string(allocation.second_cardinality);
    result += "],\"dyadic_only\":";
    result += dyadic_only ? "true" : "false";
    result += ",\"objective\":{\"binary_grid_exponent\":-298,";
    result += "\"denominator\":\"";
    result += allocation.sse.denominator.get_str();
    result += "\",\"numerator\":\"";
    result += allocation.sse.numerator.get_str();
    result += "\"},\"used_states\":";
    result += std::to_string(allocation.used_states);
    result += "}\n";
    return result;
}

[[nodiscard]] bool SameExactObjective(
    const CanonicalScaledRational &lhs,
    const CanonicalScaledRational &rhs) noexcept {
    return lhs.binary_exponent == rhs.binary_exponent &&
           lhs.numerator == rhs.numerator &&
           lhs.denominator == rhs.denominator;
}

[[nodiscard]] bool SameAllocationDecision(
    const ExhaustiveProductReferenceDecision &independent,
    const ProductAllocation &optimized) noexcept {
    return independent.capacity == optimized.capacity &&
           independent.first_cardinality == optimized.first_cardinality &&
           independent.second_cardinality == optimized.second_cardinality &&
           independent.used_states == optimized.used_states &&
           independent.nominal_alphabets_reachable ==
               optimized.nominal_alphabets_reachable &&
           SameExactObjective(independent.sse, optimized.sse);
}

[[nodiscard]] std::vector<ScalarCurveResult> FitCurvesForCapacity(
    const std::vector<std::vector<WeightedBinary32>> &cases,
    std::uint32_t capacity) {
    std::vector<ScalarCurveResult> curves;
    curves.reserve(cases.size());
    for (const auto &samples : cases) {
        curves.push_back(FitExactScalarCurve(samples, capacity));
    }
    return curves;
}

void AppendExactObjective(std::string *json,
                          const CanonicalScaledRational &objective) {
    if (objective.binary_exponent != -298 || objective.numerator < 0 ||
        objective.denominator <= 0) {
        throw std::logic_error("allocation output objective is invalid");
    }
    json->append("{\"binary_grid_exponent\":-298,\"denominator\":\"");
    json->append(objective.denominator.get_str());
    json->append("\",\"numerator\":\"");
    json->append(objective.numerator.get_str());
    json->append("\"}");
}

void AppendProductAllocation(std::string *json,
                             const ProductAllocation &allocation) {
    json->append("{\"cardinalities\":[");
    json->append(std::to_string(allocation.first_cardinality));
    json->push_back(',');
    json->append(std::to_string(allocation.second_cardinality));
    json->append("],\"objective\":");
    AppendExactObjective(json, allocation.sse);
    json->append(",\"reachable\":");
    json->append(allocation.nominal_alphabets_reachable ? "true" : "false");
    json->append(",\"used_states\":");
    json->append(std::to_string(allocation.used_states));
    json->push_back('}');
}

void AppendGlobalAllocation(std::string *json,
                            const GlobalDyadicAllocation &allocation) {
    if (allocation.bit_widths.size() != kAllocationCurveCount) {
        throw std::logic_error("global allocation did not return 128 widths");
    }
    json->append("{\"bit_widths\":[");
    for (std::size_t coordinate = 0;
         coordinate < allocation.bit_widths.size();
         ++coordinate) {
        if (coordinate != 0) {
            json->push_back(',');
        }
        json->append(std::to_string(allocation.bit_widths[coordinate]));
    }
    json->append("],\"objective\":");
    AppendExactObjective(json, allocation.sse);
    json->append(",\"reachable\":");
    json->append(allocation.nominal_alphabets_reachable ? "true" : "false");
    json->append(",\"used_bits\":");
    json->append(std::to_string(allocation.used_bits));
    json->push_back('}');
}

[[nodiscard]] std::string BuildAllocationJson(
    const std::vector<GroupAllocationDecision> &groups,
    const GlobalDyadicAllocation &global_b4,
    const GlobalDyadicAllocation &global_b8) {
    if (groups.size() != 2 * kFrozenGroupCount) {
        throw std::logic_error("allocation output requires 128 group decisions");
    }
    std::string json;
    json.reserve(128 * 512);
    // Top-level keys, nested object keys, and group fields are lexicographic.
    json.append("{\"globals\":{\"B4\":");
    AppendGlobalAllocation(&json, global_b4);
    json.append(",\"B8\":");
    AppendGlobalAllocation(&json, global_b8);
    json.append("},\"groups\":[");
    for (std::size_t index = 0; index < groups.size(); ++index) {
        if (index != 0) {
            json.push_back(',');
        }
        const GroupAllocationDecision &group = groups[index];
        json.append("{\"arbitrary\":");
        AppendProductAllocation(&json, group.arbitrary);
        json.append(",\"dyadic\":");
        AppendProductAllocation(&json, group.dyadic);
        json.append(",\"group\":");
        json.append(std::to_string(group.group_id));
        json.append(",\"rate\":\"B");
        json.append(std::to_string(group.word_bits));
        json.append("\"}");
    }
    json.append("]}\n");
    return json;
}

[[nodiscard]] std::string Hex32(std::uint32_t bits) {
    std::ostringstream encoded;
    encoded << "0x" << std::hex << std::setfill('0') << std::setw(8) << bits;
    return encoded.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t bits) {
    std::ostringstream encoded;
    encoded << "0x" << std::hex << std::setfill('0') << std::setw(16) << bits;
    return encoded.str();
}

[[nodiscard]] std::string BytesHex(
    std::span<const std::uint8_t> bytes) {
    std::ostringstream encoded;
    encoded << std::hex << std::setfill('0');
    for (const std::uint8_t byte : bytes) {
        encoded << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return encoded.str();
}

[[nodiscard]] std::string TinyCurveInventorySha256(
    const std::vector<std::vector<WeightedBinary32>> &cases) {
    Sha256Accumulator digest;
    for (std::size_t case_id = 0; case_id < cases.size(); ++case_id) {
        std::string preimage{"{\"case_id\":"};
        preimage.append(std::to_string(case_id));
        preimage.append(",\"samples\":[");
        for (std::size_t index = 0; index < cases[case_id].size(); ++index) {
            if (index != 0) {
                preimage.push_back(',');
            }
            const WeightedBinary32 &sample = cases[case_id][index];
            preimage.append("{\"binary32_bits\":\"");
            preimage.append(Hex32(sample.bits));
            preimage.append("\",\"vector_id\":");
            preimage.append(std::to_string(sample.vector_id));
            preimage.append(",\"weight\":\"");
            preimage.append(std::to_string(sample.weight));
            preimage.append("\"}");
        }
        preimage.append("]}\n");
        digest.Update(preimage);
    }
    return digest.FinalHex();
}

[[nodiscard]] ScalarCurveResult BuildThreePointWeightedCurve(
    const std::array<std::uint64_t, 3> &weights,
    std::uint32_t maximum_cardinality) {
    std::vector<WeightedBinary32> samples;
    samples.reserve(weights.size());
    for (std::size_t index = 0; index < weights.size(); ++index) {
        samples.push_back(WeightedBinary32{
            kIntegerUniverseBits[index],
            weights[index],
            static_cast<std::uint64_t>(index),
        });
    }
    return FitExactScalarCurve(samples, maximum_cardinality);
}

void AppendSmallAllocationParity(
    std::string *json,
    const ExhaustiveProductReferenceDecision &independent,
    const ProductAllocation &optimized) {
    json->append("{\"independent_cardinalities\":[");
    json->append(std::to_string(independent.first_cardinality));
    json->push_back(',');
    json->append(std::to_string(independent.second_cardinality));
    json->append("],\"independent_feasible_tuple_evaluation_count\":\"");
    json->append(std::to_string(
        independent.feasible_tuple_evaluation_count));
    json->append("\",\"independent_objective\":");
    AppendExactObjective(json, independent.sse);
    json->append(",\"optimized_candidate_evaluation_count\":\"");
    json->append(std::to_string(
        optimized.optimized_candidate_evaluation_count));
    json->append("\",\"optimized_cardinalities\":[");
    json->append(std::to_string(optimized.first_cardinality));
    json->push_back(',');
    json->append(std::to_string(optimized.second_cardinality));
    json->append("],\"optimized_objective\":");
    AppendExactObjective(json, optimized.sse);
    json->append(",\"parity\":");
    json->append(SameAllocationDecision(independent, optimized)
                     ? "true"
                     : "false");
    json->push_back('}');
}

[[nodiscard]] std::string BuildSameHDifferentWeightFixtureJson() {
    constexpr std::uint32_t capacity = 4;
    const std::array<std::uint64_t, 3> curve_a_weights{1, 1, 1};
    const std::array<std::uint64_t, 3> curve_b_weights{1, 1, 2};
    const std::array<std::uint64_t, 3> mate_weights{3, 3, 3};
    const ScalarCurveResult curve_a =
        BuildThreePointWeightedCurve(curve_a_weights, capacity);
    const ScalarCurveResult curve_b =
        BuildThreePointWeightedCurve(curve_b_weights, capacity);
    const ScalarCurveResult mate =
        BuildThreePointWeightedCurve(mate_weights, capacity);
    if (curve_a.support.size() != 3 || curve_b.support.size() != 3 ||
        !SameExactObjective(curve_a.at(3).sse, curve_b.at(3).sse) ||
        SameExactObjective(curve_a.at(1).sse, curve_b.at(1).sse)) {
        throw std::logic_error(
            "same-H/different-weight fixture does not distinguish curves");
    }

    std::string json{"{\"arms\":["};
    bool first_arm = true;
    for (const bool dyadic_only : {false, true}) {
        const ProductCardinalitySet cardinality_set =
            dyadic_only ? ProductCardinalitySet::kPowersOfTwo
                        : ProductCardinalitySet::kAllPositiveIntegers;
        const ExhaustiveProductReferenceDecision independent_a =
            EnumerateProductAllocationReference(
                curve_a, mate, capacity, dyadic_only);
        const ExhaustiveProductReferenceDecision independent_b =
            EnumerateProductAllocationReference(
                curve_b, mate, capacity, dyadic_only);
        const ProductAllocation optimized_a = AllocateProduct2(
            curve_a, mate, capacity, cardinality_set);
        const ProductAllocation optimized_b = AllocateProduct2(
            curve_b, mate, capacity, cardinality_set);
        ValidateAllocation(optimized_a, capacity, dyadic_only);
        ValidateAllocation(optimized_b, capacity, dyadic_only);
        const std::uint64_t expected_exhaustive = dyadic_only ? 6 : 8;
        if (!SameAllocationDecision(independent_a, optimized_a) ||
            !SameAllocationDecision(independent_b, optimized_b) ||
            independent_a.feasible_tuple_evaluation_count !=
                expected_exhaustive ||
            independent_b.feasible_tuple_evaluation_count !=
                expected_exhaustive ||
            independent_a.first_cardinality != 1 ||
            independent_a.second_cardinality != 4 ||
            independent_b.first_cardinality != 2 ||
            independent_b.second_cardinality != 2) {
            throw std::logic_error(
                "same-H/different-weight allocation fixture failed");
        }
        if (!first_arm) {
            json.push_back(',');
        }
        first_arm = false;
        json.append("{\"cardinality_kind\":\"");
        json.append(dyadic_only ? "dyadic" : "arbitrary");
        json.append("\",\"curve_a\":");
        AppendSmallAllocationParity(&json, independent_a, optimized_a);
        json.append(",\"curve_b\":");
        AppendSmallAllocationParity(&json, independent_b, optimized_b);
        json.append(",\"different_weight_sensitive_winners\":true}");
    }
    json.append("],\"capacity\":4,\"common_support_binary32_bits\":[\"");
    json.append(Hex32(kIntegerUniverseBits[0]));
    json.append("\",\"");
    json.append(Hex32(kIntegerUniverseBits[1]));
    json.append("\",\"");
    json.append(Hex32(kIntegerUniverseBits[2]));
    json.append("\"],\"curve_a_k1_objective\":");
    AppendExactObjective(&json, curve_a.at(1).sse);
    json.append(",\"curve_a_weights\":[1,1,1],"
                "\"curve_b_k1_objective\":");
    AppendExactObjective(&json, curve_b.at(1).sse);
    json.append(",\"curve_b_weights\":[1,1,2],"
                "\"mate_weights\":[3,3,3],"
                "\"same_support_size\":3}");
    return json;
}

template <typename Range>
void AppendUnsignedArray(std::string *json, const Range &values) {
    json->push_back('[');
    bool first = true;
    for (const auto value : values) {
        if (!first) {
            json->push_back(',');
        }
        first = false;
        json->append(std::to_string(static_cast<std::uint64_t>(value)));
    }
    json->push_back(']');
}

template <typename Range>
void AppendHex32Array(std::string *json, const Range &values) {
    json->push_back('[');
    bool first = true;
    for (const auto value : values) {
        if (!first) {
            json->push_back(',');
        }
        first = false;
        json->push_back('"');
        json->append(Hex32(static_cast<std::uint32_t>(value)));
        json->push_back('"');
    }
    json->push_back(']');
}

void AppendPoint2BitsArray(
    std::string *json,
    std::span<const Binary32Point2> points) {
    json->push_back('[');
    for (std::size_t index = 0; index < points.size(); ++index) {
        if (index != 0) {
            json->push_back(',');
        }
        json->append("[\"");
        json->append(Hex32(points[index].coordinate0_bits));
        json->append("\",\"");
        json->append(Hex32(points[index].coordinate1_bits));
        json->append("\"]");
    }
    json->push_back(']');
}

void AppendLookupValue(std::string *json, const LookupEntryBits &entry) {
    json->append("\"pre_narrow_binary64_bits\":\"");
    json->append(Hex64(entry.pre_narrow_binary64_bits));
    json->append("\",\"stored_binary32_bits\":\"");
    json->append(Hex32(entry.stored_binary32_bits));
    json->append("\",\"valid\":");
    json->append(entry.valid ? "true" : "false");
}

[[nodiscard]] std::vector<ScalarCurveResult> BuildSupportSizeCurves(
    std::uint32_t capacity) {
    std::vector<ScalarCurveResult> curves;
    curves.reserve(4);
    for (std::size_t support_size = 1; support_size <= 4; ++support_size) {
        std::vector<WeightedBinary32> samples;
        samples.reserve(support_size);
        for (std::size_t index = 0; index < support_size; ++index) {
            samples.push_back(WeightedBinary32{
                kIntegerUniverseBits[index],
                1,
                static_cast<std::uint64_t>(index),
            });
        }
        curves.push_back(FitExactScalarCurve(samples, capacity));
    }
    return curves;
}

[[nodiscard]] std::vector<std::uint32_t> AllowedCardinalities(
    std::uint32_t capacity,
    bool dyadic_only) {
    std::vector<std::uint32_t> allowed;
    if (dyadic_only) {
        for (std::uint32_t value = 1; value <= capacity; value <<= 1U) {
            allowed.push_back(value);
            if (value > capacity / 2U) {
                break;
            }
        }
    } else {
        allowed.reserve(capacity);
        for (std::uint32_t value = 1; value <= capacity; ++value) {
            allowed.push_back(value);
        }
    }
    return allowed;
}

[[nodiscard]] std::uint64_t ExhaustiveValidTupleCount(
    std::uint32_t capacity,
    bool dyadic_only) {
    const std::vector<std::uint32_t> allowed =
        AllowedCardinalities(capacity, dyadic_only);
    std::uint64_t count = 0;
    for (const std::uint32_t first : allowed) {
        for (const std::uint32_t second : allowed) {
            if (static_cast<std::uint64_t>(first) * second <= capacity) {
                ++count;
            }
        }
    }
    return count;
}

[[nodiscard]] std::string BuildSupportSizeWinnerJson() {
    std::string json{"["};
    bool first_record = true;
    std::uint64_t record_count = 0;
    for (const std::uint32_t capacity : kCapacities) {
        const std::vector<ScalarCurveResult> curves =
            BuildSupportSizeCurves(capacity);
        for (const bool dyadic_only : {false, true}) {
            const ProductCardinalitySet cardinality_set =
                dyadic_only ? ProductCardinalitySet::kPowersOfTwo
                            : ProductCardinalitySet::kAllPositiveIntegers;
            const std::uint64_t exhaustive_count =
                ExhaustiveValidTupleCount(capacity, dyadic_only);
            for (std::size_t first_support_size = 1;
                 first_support_size <= 4;
                 ++first_support_size) {
                for (std::size_t second_support_size = 1;
                     second_support_size <= 4;
                     ++second_support_size) {
                    const ProductAllocation allocation = AllocateProduct2(
                        curves[first_support_size - 1],
                        curves[second_support_size - 1], capacity,
                        cardinality_set);
                    ValidateAllocation(allocation, capacity, dyadic_only);
                    if (!first_record) {
                        json.push_back(',');
                    }
                    first_record = false;
                    json.append("{\"capacity\":");
                    json.append(std::to_string(capacity));
                    json.append(",\"cardinality_kind\":\"");
                    json.append(dyadic_only ? "dyadic" : "arbitrary");
                    json.append("\",\"exhaustive_valid_tuple_count\":\"");
                    json.append(std::to_string(exhaustive_count));
                    json.append("\",\"first_support_size\":");
                    json.append(std::to_string(first_support_size));
                    json.append(",\"objective\":");
                    AppendExactObjective(&json, allocation.sse);
                    json.append(",\"optimized_candidate_evaluation_count\":\"");
                    json.append(std::to_string(
                        allocation.optimized_candidate_evaluation_count));
                    json.append("\",\"reachable\":");
                    json.append(allocation.nominal_alphabets_reachable
                                    ? "true"
                                    : "false");
                    json.append(",\"second_support_size\":");
                    json.append(std::to_string(second_support_size));
                    json.append(",\"selected_cardinalities\":[");
                    json.append(std::to_string(allocation.first_cardinality));
                    json.push_back(',');
                    json.append(std::to_string(allocation.second_cardinality));
                    json.append("],\"used_states\":");
                    json.append(std::to_string(allocation.used_states));
                    json.push_back('}');
                    ++record_count;
                }
            }
        }
    }
    if (record_count != 64) {
        throw std::logic_error("support-size winner inventory is not 64");
    }
    json.push_back(']');
    return json;
}

[[nodiscard]] std::string BuildMixedRadixCaseJson() {
    const std::vector<std::uint32_t> radices{3, 5};
    const std::uint64_t valid_tuple_count = MixedRadixCapacity(radices);
    std::string json{"{\"entries\":["};
    for (std::uint64_t address = 0; address < 16; ++address) {
        if (address != 0) {
            json.push_back(',');
        }
        json.append("{\"address\":");
        json.append(std::to_string(address));
        if (address < valid_tuple_count) {
            const std::vector<std::uint32_t> labels =
                MixedRadixDecode(address, radices);
            const std::uint64_t encoded = MixedRadixEncode(labels, radices);
            if (encoded != address) {
                throw std::logic_error("mixed-radix fixture did not round trip");
            }
            json.append(",\"decoded_labels\":");
            AppendUnsignedArray(&json, labels);
            json.append(",\"encoded_address\":");
            json.append(std::to_string(encoded));
            json.append(",\"labels\":");
            AppendUnsignedArray(&json, labels);
            json.append(",\"valid\":true}");
        } else {
            bool rejected = false;
            try {
                static_cast<void>(MixedRadixDecode(address, radices));
            } catch (const std::invalid_argument &) {
                rejected = true;
            }
            if (!rejected) {
                throw std::logic_error("invalid mixed-radix address was accepted");
            }
            json.append(",\"decoded_labels\":null,\"encoded_address\":null,"
                        "\"labels\":null,\"valid\":false}");
        }
    }
    json.append("],\"nominal_capacity\":16,\"radices\":[3,5],"
                "\"valid_tuple_count\":15}");
    return json;
}

[[nodiscard]] std::string BuildMatchedPackingCasesJson() {
    std::string json{"["};
    for (const std::uint32_t word_bits : {4U, 8U}) {
        if (word_bits != 4) {
            json.push_back(',');
        }
        std::vector<std::uint32_t> labels(kFrozenGroupCount, 0);
        for (std::size_t index = 0; index < labels.size(); ++index) {
            labels[index] = word_bits == 4
                                ? static_cast<std::uint32_t>(index % 16)
                                : static_cast<std::uint32_t>((3 * index + 1) % 256);
        }
        const std::vector<std::uint8_t> payload =
            PackMatchedGroupLabels(labels, word_bits);
        const std::vector<std::uint32_t> roundtrip =
            UnpackMatchedGroupLabels(payload, word_bits);
        if (roundtrip != labels) {
            throw std::logic_error("matched packing fixture did not round trip");
        }
        json.append("{\"labels\":");
        AppendUnsignedArray(&json, labels);
        json.append(",\"payload_bytes\":");
        json.append(std::to_string(payload.size()));
        json.append(",\"payload_hex\":\"");
        json.append(BytesHex(payload));
        json.append("\",\"roundtrip_labels\":");
        AppendUnsignedArray(&json, roundtrip);
        json.append(",\"word_bits\":");
        json.append(std::to_string(word_bits));
        json.push_back('}');
    }
    json.push_back(']');
    return json;
}

struct GlobalPackingFixtureInputs {
    std::size_t paid_payload_bytes{0};
    std::vector<std::uint8_t> bit_widths;
    std::vector<std::uint32_t> labels;
};

[[nodiscard]] GlobalPackingFixtureInputs BuildGlobalPackingFixtureInputs(
    std::size_t paid_payload_bytes) {
    GlobalPackingFixtureInputs fixture;
    fixture.paid_payload_bytes = paid_payload_bytes;
    fixture.bit_widths.assign(kFrozenCoordinateCount, 0);
    fixture.labels.assign(kFrozenCoordinateCount, 0);
    if (paid_payload_bytes == 32) {
        const std::array<std::uint8_t, 7> widths{0, 1, 3, 4, 0, 7, 2};
        const std::array<std::uint32_t, 7> labels{0, 1, 5, 9, 0, 85, 3};
        std::copy(widths.begin(), widths.end(), fixture.bit_widths.begin());
        std::copy(labels.begin(), labels.end(), fixture.labels.begin());
    } else if (paid_payload_bytes == 64) {
        const std::array<std::uint8_t, 8> widths{8, 0, 5, 3, 1, 7, 2, 4};
        const std::array<std::uint32_t, 8> labels{255, 0, 17, 5, 1, 100, 3, 9};
        std::copy(widths.begin(), widths.end(), fixture.bit_widths.begin());
        std::copy(labels.begin(), labels.end(), fixture.labels.begin());
    } else {
        throw std::invalid_argument("unexpected global packing fixture size");
    }
    return fixture;
}

[[nodiscard]] bool HasZeroHighTail(
    std::span<const std::uint8_t> payload,
    std::uint32_t used_bits) {
    for (std::uint64_t bit = used_bits; bit < payload.size() * 8ULL; ++bit) {
        if (((payload[bit / 8U] >> (bit % 8U)) & 1U) != 0U) {
            return false;
        }
    }
    return true;
}

[[nodiscard]] std::string BuildGlobalPackingCaseJson(
    std::size_t paid_payload_bytes) {
    const GlobalPackingFixtureInputs fixture =
        BuildGlobalPackingFixtureInputs(paid_payload_bytes);
    const GlobalPackedLabels packed = PackGlobalLabels(
        fixture.labels, fixture.bit_widths, paid_payload_bytes);
    const std::vector<std::uint32_t> roundtrip =
        UnpackGlobalLabels(packed.bytes, fixture.bit_widths);
    const bool zero_tail = HasZeroHighTail(packed.bytes, packed.used_bits);
    if (roundtrip != fixture.labels || !zero_tail) {
        throw std::logic_error("global packing fixture did not round trip");
    }
    std::string json{"{\"bit_offsets\":"};
    AppendUnsignedArray(&json, packed.bit_offsets);
    json.append(",\"bit_widths\":");
    AppendUnsignedArray(&json, fixture.bit_widths);
    json.append(",\"labels\":");
    AppendUnsignedArray(&json, fixture.labels);
    json.append(",\"paid_payload_bytes\":");
    json.append(std::to_string(paid_payload_bytes));
    json.append(",\"payload_hex\":\"");
    json.append(BytesHex(packed.bytes));
    json.append("\",\"roundtrip_labels\":");
    AppendUnsignedArray(&json, roundtrip);
    json.append(",\"used_bits\":");
    json.append(std::to_string(packed.used_bits));
    json.append(",\"zero_tail\":");
    json.append(zero_tail ? "true" : "false");
    json.push_back('}');
    return json;
}

[[nodiscard]] std::string BuildGlobalPackingCasesJson() {
    std::string json{"["};
    json.append(BuildGlobalPackingCaseJson(32));
    json.push_back(',');
    json.append(BuildGlobalPackingCaseJson(64));
    json.push_back(']');
    return json;
}

[[nodiscard]] std::vector<std::uint32_t> Binary32BitsOf(
    std::span<const float> values) {
    std::vector<std::uint32_t> bits;
    bits.reserve(values.size());
    for (const float value : values) {
        bits.push_back(Binary32Bits(value));
    }
    return bits;
}

[[nodiscard]] std::string BuildMatchedLookupCaseJson(
    std::uint32_t capacity,
    std::span<const std::uint32_t> axis0,
    std::span<const std::uint32_t> axis1,
    const Binary32Point2 &query) {
    const std::vector<Binary32Point2> reconstructions =
        BuildCartesianReconstruction2(axis0, axis1);
    const MatchedLookupTableBits table = BuildMatchedLookupTable(
        query, reconstructions, capacity);
    if (table.entries.size() != capacity ||
        table.valid_states != reconstructions.size()) {
        throw std::logic_error("matched lookup fixture has invalid shape");
    }

    std::string json{"{\"axis0_centroid_bits\":"};
    AppendHex32Array(&json, axis0);
    json.append(",\"axis1_centroid_bits\":");
    AppendHex32Array(&json, axis1);
    json.append(",\"capacity\":");
    json.append(std::to_string(capacity));
    json.append(",\"entries\":[");
    for (std::size_t address = 0; address < table.entries.size(); ++address) {
        if (address != 0) {
            json.push_back(',');
        }
        json.append("{\"address\":");
        json.append(std::to_string(address));
        json.push_back(',');
        AppendLookupValue(&json, table.entries[address]);
        json.push_back('}');
    }
    json.append("],\"query_bits\":[\"");
    json.append(Hex32(query.coordinate0_bits));
    json.append("\",\"");
    json.append(Hex32(query.coordinate1_bits));
    json.append("\"],\"radices\":[");
    json.append(std::to_string(axis0.size()));
    json.push_back(',');
    json.append(std::to_string(axis1.size()));
    json.append("],\"reconstruction_bits\":");
    AppendPoint2BitsArray(&json, reconstructions);
    json.append(",\"valid_states\":");
    json.append(std::to_string(table.valid_states));
    json.push_back('}');
    return json;
}

[[nodiscard]] std::string BuildMatchedLookupCasesJson() {
    const std::array<float, 3> axis0_b4_values{-1.0F, 0.0F, 2.0F};
    const std::array<float, 5> axis1_b4_values{
        -2.0F, -0.5F, 1.0F, 3.0F, 4.0F};
    const std::vector<std::uint32_t> axis0_b4 =
        Binary32BitsOf(axis0_b4_values);
    const std::vector<std::uint32_t> axis1_b4 =
        Binary32BitsOf(axis1_b4_values);
    const Binary32Point2 query_b4{
        Binary32Bits(0.5F),
        Binary32Bits(-0.75F),
    };

    std::vector<std::uint32_t> axis0_b8;
    std::vector<std::uint32_t> axis1_b8;
    axis0_b8.reserve(13);
    axis1_b8.reserve(19);
    for (int value = -6; value <= 6; ++value) {
        axis0_b8.push_back(Binary32Bits(static_cast<float>(value)));
    }
    for (int value = -9; value <= 9; ++value) {
        axis1_b8.push_back(Binary32Bits(static_cast<float>(value)));
    }
    const Binary32Point2 query_b8{
        Binary32Bits(0.25F),
        Binary32Bits(-0.5F),
    };

    std::string json{"["};
    json.append(BuildMatchedLookupCaseJson(
        16, axis0_b4, axis1_b4, query_b4));
    json.push_back(',');
    json.append(BuildMatchedLookupCaseJson(
        256, axis0_b8, axis1_b8, query_b8));
    json.push_back(']');
    return json;
}

[[nodiscard]] std::vector<std::uint32_t> GlobalLookupPalette() {
    const std::array<float, 16> values{
        -4.0F, -3.0F, -2.0F, -1.0F,
        -0.5F, -0.25F, 0.0F, 0.25F,
        0.5F, 1.0F, 2.0F, 3.0F,
        4.0F, 5.0F, 6.0F, 8.0F,
    };
    return Binary32BitsOf(values);
}

[[nodiscard]] std::string BuildGlobalLookupCaseJson() {
    const GlobalPackingFixtureInputs packing =
        BuildGlobalPackingFixtureInputs(32);
    const std::vector<std::uint32_t> palette = GlobalLookupPalette();
    std::vector<std::uint32_t> query(kFrozenCoordinateCount, 0);
    std::vector<std::vector<std::uint32_t>> centroids(
        kFrozenCoordinateCount);
    for (std::size_t coordinate = 0;
         coordinate < kFrozenCoordinateCount;
         ++coordinate) {
        query[coordinate] = palette[(3 * coordinate) % palette.size()];
        const std::size_t cardinality =
            std::size_t{1} << packing.bit_widths[coordinate];
        centroids[coordinate].reserve(cardinality);
        for (std::size_t label = 0; label < cardinality; ++label) {
            centroids[coordinate].push_back(
                palette[(coordinate + 3 * label) % palette.size()]);
        }
    }
    const GlobalLookupTableBits table = BuildGlobalLookupTable(
        query, centroids, packing.bit_widths);

    std::string json{"{\"bit_widths\":"};
    AppendUnsignedArray(&json, packing.bit_widths);
    json.append(",\"centroid_bits_by_coordinate\":[");
    for (std::size_t coordinate = 0; coordinate < centroids.size(); ++coordinate) {
        if (coordinate != 0) {
            json.push_back(',');
        }
        AppendHex32Array(&json, centroids[coordinate]);
    }
    json.append("],\"coordinate_offsets\":");
    AppendUnsignedArray(&json, table.coordinate_offsets);
    json.append(",\"entries\":[");
    std::size_t flat_index = 0;
    for (std::size_t coordinate = 0; coordinate < centroids.size(); ++coordinate) {
        for (std::size_t label = 0; label < centroids[coordinate].size(); ++label) {
            if (flat_index != 0) {
                json.push_back(',');
            }
            if (flat_index >= table.entries.size()) {
                throw std::logic_error("global lookup fixture entry underflow");
            }
            json.append("{\"coordinate\":");
            json.append(std::to_string(coordinate));
            json.append(",\"flat_index\":");
            json.append(std::to_string(flat_index));
            json.append(",\"label\":");
            json.append(std::to_string(label));
            json.push_back(',');
            AppendLookupValue(&json, table.entries[flat_index]);
            json.push_back('}');
            ++flat_index;
        }
    }
    if (flat_index != table.entries.size()) {
        throw std::logic_error("global lookup fixture entry overflow");
    }
    json.append("],\"query_coordinate_bits\":");
    AppendHex32Array(&json, query);
    json.push_back('}');
    return json;
}

} // namespace

void RunExhaustiveAllocationReferenceHandSmoke() {
    static_cast<void>(BuildSameHDifferentWeightFixtureJson());
}

void WriteRepresentationSuite(std::ostream &output) {
    RunRepresentationConstantSmoke();
    const std::vector<std::vector<WeightedBinary32>> cases = BuildTinyCases();

    Sha256Accumulator independent_digest;
    Sha256Accumulator optimized_digest;
    std::uint64_t record_count = 0;
    std::uint64_t decision_equality_count = 0;
    std::uint64_t exhaustive_tuple_evaluation_count = 0;
    std::uint64_t optimized_candidate_evaluation_count = 0;
    std::uint64_t exact_objective_class_count = 0;
    bool objective_contract = true;
    for (const std::uint32_t capacity : kCapacities) {
        const std::vector<ScalarCurveResult> curves =
            FitCurvesForCapacity(cases, capacity);
        for (const bool dyadic_only : {false, true}) {
            const ProductCardinalitySet cardinality_set =
                dyadic_only ? ProductCardinalitySet::kPowersOfTwo
                            : ProductCardinalitySet::kAllPositiveIntegers;
            for (const ScalarCurveResult &first : curves) {
                for (const ScalarCurveResult &second : curves) {
                    const ExhaustiveProductReferenceDecision independent =
                        EnumerateProductAllocationReference(
                            first, second, capacity, dyadic_only);
                    const ProductAllocation optimized = AllocateProduct2(
                        first, second, capacity, cardinality_set);
                    ValidateAllocation(optimized, capacity, dyadic_only);
                    const std::uint64_t expected_feasible =
                        ExhaustiveValidTupleCount(capacity, dyadic_only);
                    if (independent.feasible_tuple_evaluation_count !=
                        expected_feasible) {
                        throw std::logic_error(
                            "independent exhaustive tuple count mismatch");
                    }
                    objective_contract =
                        objective_contract &&
                        independent.sse.binary_exponent == -298 &&
                        optimized.sse.binary_exponent == -298;
                    independent_digest.Update(
                        ExhaustiveAllocationPreimage(
                            independent, dyadic_only));
                    optimized_digest.Update(
                        AllocationPreimage(optimized, dyadic_only));
                    exhaustive_tuple_evaluation_count +=
                        independent.feasible_tuple_evaluation_count;
                    optimized_candidate_evaluation_count +=
                        optimized.optimized_candidate_evaluation_count;
                    exact_objective_class_count +=
                        independent.exact_objective_class_count;
                    if (SameAllocationDecision(independent, optimized)) {
                        ++decision_equality_count;
                    }
                    ++record_count;
                }
            }
        }
    }

    if (record_count != kExpectedAllocationRecordCount) {
        throw std::logic_error("frozen allocation record count is not 2,433,600");
    }
    if (exhaustive_tuple_evaluation_count !=
            kExpectedExhaustiveTupleEvaluationCount ||
        optimized_candidate_evaluation_count !=
            kExpectedOptimizedCandidateEvaluationCount) {
        throw std::logic_error("frozen allocation candidate count mismatch");
    }
    const std::string independent_exhaustive_sha256 =
        independent_digest.FinalHex();
    const std::string optimized_sha256 = optimized_digest.FinalHex();
    const bool all_decisions_equal =
        decision_equality_count == record_count;
    const bool authority_hashes_equal =
        independent_exhaustive_sha256 == optimized_sha256;
    const std::string tiny_curve_inventory_sha256 =
        TinyCurveInventorySha256(cases);
    const std::string same_h_different_weight_fixture =
        BuildSameHDifferentWeightFixtureJson();
    const std::string support_size_winners = BuildSupportSizeWinnerJson();
    const std::string mixed_radix_case = BuildMixedRadixCaseJson();
    const std::string matched_packing_cases =
        BuildMatchedPackingCasesJson();
    const std::string global_packing_cases =
        BuildGlobalPackingCasesJson();
    const std::string matched_lookup_cases =
        BuildMatchedLookupCasesJson();
    const std::string global_lookup_case = BuildGlobalLookupCaseJson();

    // Top-level and nested keys are emitted in lexicographic order.
    output << "{\"allocation_record_count\":" << record_count
           << ",\"allocation_sha256\":\"" << optimized_sha256
           << "\",\"all_decisions_equal\":"
           << (all_decisions_equal ? "true" : "false")
           << ",\"authority_hashes_equal\":"
           << (authority_hashes_equal ? "true" : "false")
           << ",\"candidate_counts\":{"
           << "\"independent_feasible_tuple_evaluations\":\""
           << exhaustive_tuple_evaluation_count
           << "\",\"optimized_candidate_evaluations\":\""
           << optimized_candidate_evaluation_count << "\"}"
           << ",\"checks\":{"
           << "\"allocation_record_count\":true,"
           << "\"all_decisions_equal\":"
           << (all_decisions_equal ? "true" : "false") << ','
           << "\"authority_hashes_equal\":"
           << (authority_hashes_equal ? "true" : "false") << ','
           << "\"candidate_counts\":true,"
           << "\"equidistant_lower_codeword\":true,"
           << "\"objective_contract\":"
           << (objective_contract ? "true" : "false") << ','
           << "\"representation_constant_smoke\":true,"
           << "\"tiny_case_count\":true},"
           << "\"decision_equality_count\":"
           << decision_equality_count << ','
           << "\"exact_objective_class_count\":\""
           << exact_objective_class_count << "\","
           << "\"global_lookup_case\":" << global_lookup_case << ','
           << "\"global_packing_cases\":" << global_packing_cases << ','
           << "\"matched_lookup_cases\":" << matched_lookup_cases << ','
           << "\"matched_packing_cases\":" << matched_packing_cases << ','
           << "\"mixed_radix_case\":" << mixed_radix_case << ','
           << "\"independent_exhaustive_sha256\":\""
           << independent_exhaustive_sha256 << "\","
           << "\"optimized_sha256\":\"" << optimized_sha256 << "\","
           << "\"python_order_fingerprint_authoritative\":false,"
           << "\"python_order_fingerprint_sha256\":\""
           << optimized_sha256 << "\","
           << "\"same_h_different_weight_fixture\":"
           << same_h_different_weight_fixture << ','
           << "\"support_size_winners\":" << support_size_winners
           << ",\"tiny_curve_inventory_preimage_schema\":\""
              "canonical JSONL: case_id, then samples with binary32_bits, "
              "vector_id, weight; terminal LF per case\","
           << "\"tiny_curve_inventory_sha256\":\""
           << tiny_curve_inventory_sha256 << "\""
           << "}\n";
    if (!output) {
        throw std::runtime_error("failed to write representation suite JSON");
    }
}

void WriteAllocationSuiteFiles(const std::string &input_path,
                               const std::string &output_path) {
    RunRepresentationConstantSmoke();
    const std::vector<ScalarCurveResult> curves =
        ReadAllocationCurvesA4alc001(input_path);

    std::vector<GroupAllocationDecision> groups;
    groups.reserve(2 * kFrozenGroupCount);
    for (const std::uint32_t word_bits : {4U, 8U}) {
        const std::uint32_t capacity = std::uint32_t{1} << word_bits;
        for (std::uint32_t group_id = 0; group_id < kFrozenGroupCount;
             ++group_id) {
            const ScalarCurveResult &first = curves[2U * group_id];
            const ScalarCurveResult &second = curves[2U * group_id + 1U];
            GroupAllocationDecision decision;
            decision.word_bits = word_bits;
            decision.group_id = group_id;
            decision.dyadic = AllocateProduct2(
                first, second, capacity,
                ProductCardinalitySet::kPowersOfTwo);
            decision.arbitrary = AllocateProduct2(
                first, second, capacity,
                ProductCardinalitySet::kAllPositiveIntegers);
            ValidateAllocation(decision.dyadic, capacity, true);
            ValidateAllocation(decision.arbitrary, capacity, false);
            groups.push_back(std::move(decision));
        }
    }

    const GlobalDyadicAllocation global_b4 =
        AllocateGlobalDyadicCap8(curves, 64U * 4U);
    const GlobalDyadicAllocation global_b8 =
        AllocateGlobalDyadicCap8(curves, 64U * 8U);
    if (global_b4.bit_budget != 256 || global_b8.bit_budget != 512) {
        throw std::logic_error("global allocator returned the wrong bit budget");
    }

    const std::string json = BuildAllocationJson(groups, global_b4, global_b8);
    std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error("failed to create allocation-suite output");
    }
    output.write(json.data(), static_cast<std::streamsize>(json.size()));
    output.flush();
    if (!output) {
        throw std::runtime_error("failed to flush allocation-suite output");
    }
}

namespace {

constexpr std::string_view kEncodingInputMagic = "A4ENC002";
constexpr std::string_view kEncodingInputTerminal = "A4EIEND2";
constexpr std::string_view kEncodingOutputMagic = "A4EOUT02";
constexpr std::string_view kEncodingOutputTerminal = "A4EOEND2";
constexpr std::uint32_t kEncodingSchemaVersion = 2;
constexpr std::uint32_t kEncodingRowMarker = 0x31574f52U; // "ROW1" LE.
constexpr std::uint32_t kMaximumEncodingRows = 8192;
constexpr std::uint32_t kDyadicArmId = 0;
constexpr std::uint32_t kArbitraryArmId = 1;
constexpr std::uint32_t kBlockArmId = 2;
constexpr std::uint32_t kGlobalArmId = 3;
constexpr std::uint32_t kEncodingArmCount = 4;

class EncodingInputReader {
  public:
    explicit EncodingInputReader(const std::string &path)
        : input_(path, std::ios::binary) {
        if (!input_) {
            throw std::runtime_error("failed to open encoding-suite input");
        }
    }

    void RequireMagic(std::string_view expected, const char *field) {
        std::string observed(expected.size(), '\0');
        ReadExact(observed.data(), observed.size(), field);
        if (observed != expected) {
            throw std::runtime_error(std::string("encoding-suite ") + field +
                                     " mismatch");
        }
    }

    [[nodiscard]] std::uint32_t ReadU32(const char *field) {
        std::array<unsigned char, 4> bytes{};
        ReadExact(reinterpret_cast<char *>(bytes.data()), bytes.size(), field);
        return static_cast<std::uint32_t>(bytes[0]) |
               (static_cast<std::uint32_t>(bytes[1]) << 8U) |
               (static_cast<std::uint32_t>(bytes[2]) << 16U) |
               (static_cast<std::uint32_t>(bytes[3]) << 24U);
    }

    [[nodiscard]] std::uint64_t ReadU64(const char *field) {
        std::array<unsigned char, 8> bytes{};
        ReadExact(reinterpret_cast<char *>(bytes.data()), bytes.size(), field);
        std::uint64_t result = 0;
        for (std::size_t index = 0; index < bytes.size(); ++index) {
            result |= static_cast<std::uint64_t>(bytes[index]) << (8U * index);
        }
        return result;
    }

    [[nodiscard]] std::vector<std::uint32_t> ReadU32Vector(
        std::uint32_t count,
        const char *field) {
        std::vector<std::uint32_t> result;
        result.reserve(count);
        for (std::uint32_t index = 0; index < count; ++index) {
            result.push_back(ReadU32(field));
        }
        return result;
    }

    void RequireEof() {
        char trailing = 0;
        if (input_.read(&trailing, 1)) {
            throw std::runtime_error(
                "encoding-suite input has trailing bytes");
        }
        if (!input_.eof() || input_.bad()) {
            throw std::runtime_error(
                "failed while checking encoding-suite input EOF");
        }
    }

  private:
    void ReadExact(char *destination,
                   std::size_t byte_count,
                   const char *field) {
        if (byte_count > static_cast<std::size_t>(
                             std::numeric_limits<std::streamsize>::max())) {
            throw std::runtime_error(std::string(field) + " is too large");
        }
        input_.read(destination, static_cast<std::streamsize>(byte_count));
        if (!input_) {
            throw std::runtime_error(std::string("truncated encoding ") +
                                     field);
        }
    }

    std::ifstream input_;
};

class EncodingOutputWriter {
  public:
    explicit EncodingOutputWriter(const std::string &path)
        : output_(path, std::ios::binary | std::ios::trunc) {
        if (!output_) {
            throw std::runtime_error("failed to create encoding-suite output");
        }
    }

    void WriteMagic(std::string_view value) {
        WriteBytes(value.data(), value.size());
    }

    void WriteU32(std::uint32_t value) {
        const std::array<unsigned char, 4> bytes{
            static_cast<unsigned char>(value & 0xffU),
            static_cast<unsigned char>((value >> 8U) & 0xffU),
            static_cast<unsigned char>((value >> 16U) & 0xffU),
            static_cast<unsigned char>((value >> 24U) & 0xffU),
        };
        WriteBytes(reinterpret_cast<const char *>(bytes.data()), bytes.size());
    }

    void WriteU64(std::uint64_t value) {
        std::array<unsigned char, 8> bytes{};
        for (std::size_t index = 0; index < bytes.size(); ++index) {
            bytes[index] =
                static_cast<unsigned char>((value >> (8U * index)) & 0xffU);
        }
        WriteBytes(reinterpret_cast<const char *>(bytes.data()), bytes.size());
    }

    void WriteU32Vector(std::span<const std::uint32_t> values) {
        for (const std::uint32_t value : values) {
            WriteU32(value);
        }
    }

    void WriteByteVector(std::span<const std::uint8_t> values) {
        WriteBytes(reinterpret_cast<const char *>(values.data()), values.size());
    }

    void Finish() {
        output_.flush();
        if (!output_) {
            throw std::runtime_error("failed to flush encoding-suite output");
        }
    }

  private:
    void WriteBytes(const char *data, std::size_t size) {
        if (size > static_cast<std::size_t>(
                       std::numeric_limits<std::streamsize>::max())) {
            throw std::runtime_error("encoding-suite output record is too large");
        }
        output_.write(data, static_cast<std::streamsize>(size));
        if (!output_) {
            throw std::runtime_error("failed to write encoding-suite output");
        }
    }

    std::ofstream output_;
};

struct ScalarPairModel {
    std::vector<std::uint32_t> axis0;
    std::vector<std::uint32_t> axis1;
};

struct EncodingSuiteInput {
    std::uint32_t selected_arm_id{0};
    std::uint32_t word_bits{0};
    std::uint32_t row_count{0};
    std::vector<std::uint32_t> matrix_bits;
    std::array<std::vector<ScalarPairModel>, 2> scalar_groups;
    std::vector<std::vector<Binary32Point2>> block_groups;
    std::vector<std::uint8_t> global_widths;
    std::vector<std::vector<std::uint32_t>> global_centroids;
};

struct EncodedArm {
    std::uint32_t arm_id{0};
    std::vector<std::uint32_t> labels;
    std::vector<std::uint8_t> payload;
    std::vector<std::uint32_t> roundtrip_labels;
    std::uint64_t distance_comparisons{0};
    std::uint64_t pack_operations{0};
    std::uint64_t unpack_operations{0};
    std::uint64_t mixed_radix_encodes{0};
    std::uint64_t mixed_radix_decodes{0};
    std::uint64_t owned_payload_peak_bytes{0};
};

[[nodiscard]] std::uint32_t EncodingCapacity(std::uint32_t word_bits) {
    if (word_bits != 4 && word_bits != 8) {
        throw std::runtime_error("encoding word_bits must be 4 or 8");
    }
    return std::uint32_t{1} << word_bits;
}

void RequireEncodingCardinality(std::uint32_t cardinality,
                                std::uint32_t capacity,
                                const char *field) {
    if (cardinality == 0 || cardinality > capacity) {
        throw std::runtime_error(std::string(field) +
                                 " is outside [1,capacity]");
    }
}

[[nodiscard]] EncodingSuiteInput ReadEncodingSuiteInput(
    const std::string &path) {
    EncodingInputReader reader(path);
    reader.RequireMagic(kEncodingInputMagic, "magic");
    if (reader.ReadU32("schema_version") != kEncodingSchemaVersion) {
        throw std::runtime_error("encoding-suite schema version mismatch");
    }

    EncodingSuiteInput result;
    result.selected_arm_id = reader.ReadU32("selected_arm_id");
    if (result.selected_arm_id >= kEncodingArmCount) {
        throw std::runtime_error("encoding-suite selected arm is invalid");
    }
    result.word_bits = reader.ReadU32("word_bits");
    const std::uint32_t capacity = EncodingCapacity(result.word_bits);
    result.row_count = reader.ReadU32("row_count");
    const std::uint32_t coordinate_count = reader.ReadU32("coordinate_count");
    const std::uint32_t group_count = reader.ReadU32("group_count");
    const std::uint64_t matrix_count = reader.ReadU64("matrix_value_count");
    if (result.row_count == 0 || result.row_count > kMaximumEncodingRows ||
        coordinate_count != kFrozenCoordinateCount ||
        group_count != kFrozenGroupCount ||
        matrix_count != static_cast<std::uint64_t>(result.row_count) *
                            kFrozenCoordinateCount) {
        throw std::runtime_error("encoding-suite header shape mismatch");
    }
    result.matrix_bits = reader.ReadU32Vector(
        static_cast<std::uint32_t>(matrix_count), "matrix_value_bits");

    if (result.selected_arm_id == kDyadicArmId ||
        result.selected_arm_id == kArbitraryArmId) {
        const std::uint32_t arm_id = result.selected_arm_id;
        if (reader.ReadU32("scalar_arm_id") != result.selected_arm_id) {
            throw std::runtime_error("encoding scalar arm order mismatch");
        }
        std::vector<ScalarPairModel> &groups = result.scalar_groups[arm_id];
        groups.reserve(kFrozenGroupCount);
        for (std::uint32_t group_id = 0; group_id < kFrozenGroupCount;
             ++group_id) {
            if (reader.ReadU32("scalar_group_id") != group_id) {
                throw std::runtime_error("encoding scalar group order mismatch");
            }
            const std::uint32_t cardinality0 =
                reader.ReadU32("scalar_cardinality0");
            const std::uint32_t cardinality1 =
                reader.ReadU32("scalar_cardinality1");
            RequireEncodingCardinality(cardinality0, capacity,
                                       "scalar cardinality0");
            RequireEncodingCardinality(cardinality1, capacity,
                                       "scalar cardinality1");
            if (static_cast<std::uint64_t>(cardinality0) * cardinality1 >
                capacity) {
                throw std::runtime_error(
                    "encoding scalar product exceeds word capacity");
            }
            ScalarPairModel model;
            model.axis0 =
                reader.ReadU32Vector(cardinality0, "scalar_axis0_bits");
            model.axis1 =
                reader.ReadU32Vector(cardinality1, "scalar_axis1_bits");
            groups.push_back(std::move(model));
        }
    } else if (result.selected_arm_id == kBlockArmId) {
        if (reader.ReadU32("block_arm_id") != kBlockArmId) {
            throw std::runtime_error("encoding block arm order mismatch");
        }
        result.block_groups.reserve(kFrozenGroupCount);
        for (std::uint32_t group_id = 0; group_id < kFrozenGroupCount;
             ++group_id) {
            if (reader.ReadU32("block_group_id") != group_id ||
                reader.ReadU32("block_center_count") != capacity) {
                throw std::runtime_error("encoding block group shape mismatch");
            }
            std::vector<Binary32Point2> centers;
            centers.reserve(capacity);
            for (std::uint32_t label = 0; label < capacity; ++label) {
                centers.push_back(Binary32Point2{
                    reader.ReadU32("block_center0_bits"),
                    reader.ReadU32("block_center1_bits"),
                });
            }
            result.block_groups.push_back(std::move(centers));
        }
    } else {
        if (reader.ReadU32("global_arm_id") != kGlobalArmId) {
            throw std::runtime_error("encoding global arm order mismatch");
        }
        result.global_widths.reserve(kFrozenCoordinateCount);
        result.global_centroids.reserve(kFrozenCoordinateCount);
        std::uint32_t used_bits = 0;
        for (std::uint32_t coordinate = 0;
             coordinate < kFrozenCoordinateCount;
             ++coordinate) {
            if (reader.ReadU32("global_coordinate_id") != coordinate) {
                throw std::runtime_error(
                    "encoding global coordinate order mismatch");
            }
            const std::uint32_t width = reader.ReadU32("global_bit_width");
            const std::uint32_t cardinality =
                reader.ReadU32("global_cardinality");
            if (width > 8 || cardinality == 0 ||
                cardinality > (std::uint32_t{1} << width)) {
                throw std::runtime_error(
                    "encoding global width/cardinality mismatch");
            }
            used_bits += width;
            result.global_widths.push_back(static_cast<std::uint8_t>(width));
            result.global_centroids.push_back(
                reader.ReadU32Vector(cardinality, "global_centroid_bits"));
        }
        if (used_bits > kFrozenGroupCount * result.word_bits) {
            throw std::runtime_error(
                "encoding global widths exceed paid payload");
        }
    }
    reader.RequireMagic(kEncodingInputTerminal, "terminal");
    if (reader.ReadU32("terminal_row_count") != result.row_count ||
        reader.ReadU32("terminal_selected_arm_id") !=
            result.selected_arm_id) {
        throw std::runtime_error("encoding input terminal mismatch");
    }
    reader.RequireEof();
    return result;
}

[[nodiscard]] EncodedArm EncodeScalarPairArm(
    const EncodingSuiteInput &input,
    std::uint32_t row,
    std::uint32_t arm_id) {
    EncodedArm result;
    result.arm_id = arm_id;
    result.labels.reserve(kFrozenGroupCount);
    RepresentationCounters counters;
    for (std::size_t group = 0; group < kFrozenGroupCount; ++group) {
        const ScalarPairModel &model = input.scalar_groups[arm_id][group];
        const std::uint32_t value0 =
            input.matrix_bits[row * kFrozenCoordinateCount + 2 * group];
        const std::uint32_t value1 =
            input.matrix_bits[row * kFrozenCoordinateCount + 2 * group + 1];
        const std::array<std::uint32_t, 2> labels{
            AssignNearestScalarLabel(value0, model.axis0, &counters),
            AssignNearestScalarLabel(value1, model.axis1, &counters),
        };
        const std::array<std::uint32_t, 2> radices{
            static_cast<std::uint32_t>(model.axis0.size()),
            static_cast<std::uint32_t>(model.axis1.size()),
        };
        const std::uint64_t address =
            MixedRadixEncode(labels, radices, &counters);
        if (MixedRadixDecode(address, radices, &counters) !=
            std::vector<std::uint32_t>(labels.begin(), labels.end())) {
            throw std::logic_error("native mixed-radix roundtrip mismatch");
        }
        result.labels.push_back(static_cast<std::uint32_t>(address));
    }
    result.payload =
        PackMatchedGroupLabels(result.labels, input.word_bits, &counters);
    result.roundtrip_labels =
        UnpackMatchedGroupLabels(result.payload, input.word_bits, &counters);
    if (result.roundtrip_labels != result.labels ||
        counters.mixed_radix_encodes != kFrozenGroupCount ||
        counters.mixed_radix_decodes != kFrozenGroupCount ||
        counters.packed_labels_written != kFrozenGroupCount ||
        counters.packed_labels_read != kFrozenGroupCount) {
        throw std::logic_error("native scalar encoding roundtrip mismatch");
    }
    result.distance_comparisons = counters.scalar_distance_evaluations;
    result.pack_operations = 1;
    result.unpack_operations = 1;
    result.mixed_radix_encodes = counters.mixed_radix_encodes;
    result.mixed_radix_decodes = counters.mixed_radix_decodes;
    result.owned_payload_peak_bytes =
        static_cast<std::uint64_t>(result.labels.size()) *
            sizeof(std::uint32_t) +
        static_cast<std::uint64_t>(result.payload.size()) *
            sizeof(std::uint8_t) +
        static_cast<std::uint64_t>(result.roundtrip_labels.size()) *
            sizeof(std::uint32_t);
    return result;
}

[[nodiscard]] EncodedArm EncodeBlockArm(const EncodingSuiteInput &input,
                                        std::uint32_t row) {
    EncodedArm result;
    result.arm_id = kBlockArmId;
    result.labels.reserve(kFrozenGroupCount);
    RepresentationCounters counters;
    for (std::size_t group = 0; group < kFrozenGroupCount; ++group) {
        const Binary32Point2 value{
            input.matrix_bits[row * kFrozenCoordinateCount + 2 * group],
            input.matrix_bits[row * kFrozenCoordinateCount + 2 * group + 1],
        };
        result.labels.push_back(
            AssignNearestPoint2Label(value, input.block_groups[group],
                                     &counters));
    }
    result.payload =
        PackMatchedGroupLabels(result.labels, input.word_bits, &counters);
    result.roundtrip_labels =
        UnpackMatchedGroupLabels(result.payload, input.word_bits, &counters);
    if (result.roundtrip_labels != result.labels ||
        counters.packed_labels_written != kFrozenGroupCount ||
        counters.packed_labels_read != kFrozenGroupCount) {
        throw std::logic_error("native block encoding roundtrip mismatch");
    }
    result.distance_comparisons = counters.point_distance_evaluations;
    result.pack_operations = 1;
    result.unpack_operations = 1;
    result.owned_payload_peak_bytes =
        static_cast<std::uint64_t>(result.labels.size()) *
            sizeof(std::uint32_t) +
        static_cast<std::uint64_t>(result.payload.size()) *
            sizeof(std::uint8_t) +
        static_cast<std::uint64_t>(result.roundtrip_labels.size()) *
            sizeof(std::uint32_t);
    return result;
}

[[nodiscard]] EncodedArm EncodeGlobalArm(const EncodingSuiteInput &input,
                                         std::uint32_t row) {
    EncodedArm result;
    result.arm_id = kGlobalArmId;
    result.labels.reserve(kFrozenCoordinateCount);
    RepresentationCounters counters;
    for (std::size_t coordinate = 0; coordinate < kFrozenCoordinateCount;
         ++coordinate) {
        result.labels.push_back(AssignNearestScalarLabel(
            input.matrix_bits[row * kFrozenCoordinateCount + coordinate],
            input.global_centroids[coordinate], &counters));
    }
    const std::size_t paid_bytes = input.word_bits == 4 ? 32 : 64;
    GlobalPackedLabels packed = PackGlobalLabels(
        result.labels, input.global_widths, paid_bytes, &counters);
    const std::uint64_t bit_offset_payload_bytes =
        static_cast<std::uint64_t>(packed.bit_offsets.size()) *
        sizeof(std::uint32_t);
    result.payload = std::move(packed.bytes);
    result.roundtrip_labels = UnpackGlobalLabels(
        result.payload, input.global_widths, &counters);
    if (result.roundtrip_labels != result.labels ||
        counters.packed_labels_written != kFrozenCoordinateCount ||
        counters.packed_labels_read != kFrozenCoordinateCount) {
        throw std::logic_error("native global encoding roundtrip mismatch");
    }
    result.distance_comparisons = counters.scalar_distance_evaluations;
    result.pack_operations = 1;
    result.unpack_operations = 1;
    result.owned_payload_peak_bytes =
        static_cast<std::uint64_t>(result.labels.size()) *
            sizeof(std::uint32_t) +
        static_cast<std::uint64_t>(result.payload.size()) *
            sizeof(std::uint8_t) +
        static_cast<std::uint64_t>(result.roundtrip_labels.size()) *
            sizeof(std::uint32_t) +
        bit_offset_payload_bytes;
    return result;
}

[[nodiscard]] EncodedArm EncodeSelectedArm(const EncodingSuiteInput &input,
                                           std::uint32_t row) {
    switch (input.selected_arm_id) {
    case kDyadicArmId:
    case kArbitraryArmId:
        return EncodeScalarPairArm(input, row, input.selected_arm_id);
    case kBlockArmId:
        return EncodeBlockArm(input, row);
    case kGlobalArmId:
        return EncodeGlobalArm(input, row);
    default:
        throw std::logic_error("selected encoding arm is invalid");
    }
}

void WriteEncodedArm(EncodingOutputWriter *writer, const EncodedArm &arm) {
    writer->WriteU32(arm.arm_id);
    writer->WriteU64(arm.distance_comparisons);
    writer->WriteU32(static_cast<std::uint32_t>(arm.labels.size()));
    writer->WriteU32Vector(arm.labels);
    writer->WriteU32(static_cast<std::uint32_t>(arm.payload.size()));
    writer->WriteByteVector(arm.payload);
    writer->WriteU32(static_cast<std::uint32_t>(arm.roundtrip_labels.size()));
    writer->WriteU32Vector(arm.roundtrip_labels);
    writer->WriteU32(arm.labels == arm.roundtrip_labels ? 1U : 0U);
    writer->WriteU64(arm.pack_operations);
    writer->WriteU64(arm.unpack_operations);
}

[[nodiscard]] std::uint64_t EncodingInputOwnedPayloadBytes(
    const EncodingSuiteInput &input) {
    std::uint64_t bytes =
        static_cast<std::uint64_t>(input.matrix_bits.size()) *
        sizeof(std::uint32_t);
    for (const auto &arm : input.scalar_groups) {
        for (const ScalarPairModel &group : arm) {
            bytes += static_cast<std::uint64_t>(group.axis0.size()) *
                     sizeof(std::uint32_t);
            bytes += static_cast<std::uint64_t>(group.axis1.size()) *
                     sizeof(std::uint32_t);
        }
    }
    for (const auto &centers : input.block_groups) {
        bytes += static_cast<std::uint64_t>(centers.size()) *
                 sizeof(Binary32Point2);
    }
    bytes += static_cast<std::uint64_t>(input.global_widths.size()) *
             sizeof(std::uint8_t);
    for (const auto &centroids : input.global_centroids) {
        bytes += static_cast<std::uint64_t>(centroids.size()) *
                 sizeof(std::uint32_t);
    }
    return bytes;
}

} // namespace

void WriteEncodingSuiteFiles(const std::string &input_path,
                             const std::string &output_path) {
    RunRepresentationConstantSmoke();
    const EncodingSuiteInput input = ReadEncodingSuiteInput(input_path);
    EncodingOutputWriter writer(output_path);
    writer.WriteMagic(kEncodingOutputMagic);
    writer.WriteU32(kEncodingSchemaVersion);
    writer.WriteU32(input.selected_arm_id);
    writer.WriteU32(input.word_bits);
    writer.WriteU32(input.row_count);
    writer.WriteU32(static_cast<std::uint32_t>(kFrozenCoordinateCount));
    writer.WriteU32(static_cast<std::uint32_t>(kFrozenGroupCount));
    writer.WriteU32(1U);

    std::uint64_t total_comparisons = 0;
    std::uint64_t total_payload_bytes = 0;
    std::uint64_t total_pack_operations = 0;
    std::uint64_t total_unpack_operations = 0;
    std::uint64_t total_mixed_radix_encodes = 0;
    std::uint64_t total_mixed_radix_decodes = 0;
    std::uint64_t total_arm_vectors = 0;
    const std::uint64_t input_owned_payload_bytes =
        EncodingInputOwnedPayloadBytes(input);
    std::uint64_t owned_payload_high_water_bytes = input_owned_payload_bytes;
    for (std::uint32_t row = 0; row < input.row_count; ++row) {
        writer.WriteU32(kEncodingRowMarker);
        writer.WriteU32(row);
        const EncodedArm arm = EncodeSelectedArm(input, row);
        WriteEncodedArm(&writer, arm);
        const std::uint64_t live_payload_bytes =
            input_owned_payload_bytes + arm.owned_payload_peak_bytes;
        total_comparisons += arm.distance_comparisons;
        total_payload_bytes += arm.payload.size();
        total_pack_operations += arm.pack_operations;
        total_unpack_operations += arm.unpack_operations;
        total_mixed_radix_encodes += arm.mixed_radix_encodes;
        total_mixed_radix_decodes += arm.mixed_radix_decodes;
        ++total_arm_vectors;
        owned_payload_high_water_bytes =
            std::max(owned_payload_high_water_bytes, live_payload_bytes);
    }

    writer.WriteMagic(kEncodingOutputTerminal);
    writer.WriteU32(input.row_count);
    writer.WriteU32(1U);
    writer.WriteU32(input.selected_arm_id);
    writer.WriteU64(total_comparisons);
    writer.WriteU64(total_payload_bytes);
    writer.WriteU64(total_pack_operations);
    writer.WriteU64(total_unpack_operations);
    writer.WriteU64(total_mixed_radix_encodes);
    writer.WriteU64(total_mixed_radix_decodes);
    writer.WriteU64(total_arm_vectors);
    writer.WriteU64(owned_payload_high_water_bytes);
    writer.Finish();
}

} // namespace saq::a4_1s

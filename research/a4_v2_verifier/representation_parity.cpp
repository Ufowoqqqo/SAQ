#include "parity_cli.hpp"

#include "exact_reference.hpp"
#include "json_value.hpp"

#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_v2::verifier {
namespace {

constexpr std::uint64_t kTinyCount = 780;
constexpr std::uint64_t kRecordCount = 2'433'600;
constexpr std::uint64_t kExhaustiveCount = 958'838'400;
constexpr std::uint64_t kOptimizedCount = 174'002'400;
constexpr std::array<std::uint32_t, 5> kUniverse{
    0xc0000000U, 0xbf800000U, 0x00000000U, 0x3f800000U, 0x40000000U};
constexpr std::array<std::uint32_t, 2> kCapacities{16, 256};

class DigestStream {
 public:
  DigestStream() : context_(EVP_MD_CTX_new(), EVP_MD_CTX_free) {
    if (context_ == nullptr ||
        EVP_DigestInit_ex(context_.get(), EVP_sha256(), nullptr) != 1) {
      throw std::runtime_error("cannot initialize verifier PAR digest");
    }
  }
  void update(std::string_view bytes) {
    if (done_ ||
        EVP_DigestUpdate(context_.get(), bytes.data(), bytes.size()) != 1) {
      throw std::runtime_error("cannot update verifier PAR digest");
    }
  }
  [[nodiscard]] std::string finish() {
    if (done_) throw std::logic_error("verifier PAR digest reused");
    std::array<unsigned char, EVP_MAX_MD_SIZE> bytes{};
    unsigned int size = 0;
    if (EVP_DigestFinal_ex(context_.get(), bytes.data(), &size) != 1 ||
        size != 32) {
      throw std::runtime_error("cannot finalize verifier PAR digest");
    }
    done_ = true;
    std::ostringstream output;
    output << std::hex << std::nouppercase << std::setfill('0');
    for (unsigned int index = 0; index < size; ++index) {
      output << std::setw(2) << static_cast<unsigned int>(bytes[index]);
    }
    return output.str();
  }

 private:
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> context_;
  bool done_{false};
};

[[nodiscard]] std::string Hex32(std::uint32_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::nouppercase << std::setw(8)
         << std::setfill('0') << value;
  return output.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::nouppercase << std::setw(16)
         << std::setfill('0') << value;
  return output.str();
}

void EnumerateWeights(
    const std::vector<std::uint32_t>& support, std::size_t position,
    std::vector<std::uint64_t>* weights,
    std::vector<std::vector<WeightedExactSample>>* cases) {
  if (position == support.size()) {
    std::vector<WeightedExactSample> samples;
    for (std::size_t index = 0; index < support.size(); ++index) {
      samples.push_back(
          WeightedExactSample{support[index], (*weights)[index], index});
    }
    cases->push_back(std::move(samples));
    return;
  }
  for (std::uint64_t weight = 1; weight <= 3; ++weight) {
    (*weights)[position] = weight;
    EnumerateWeights(support, position + 1, weights, cases);
  }
}

void EnumerateSupports(
    std::size_t target, std::size_t next,
    std::vector<std::uint32_t>* support,
    std::vector<std::vector<WeightedExactSample>>* cases) {
  if (support->size() == target) {
    std::vector<std::uint64_t> weights(target, 1);
    EnumerateWeights(*support, 0, &weights, cases);
    return;
  }
  const std::size_t needed = target - support->size();
  for (std::size_t index = next; index + needed <= kUniverse.size(); ++index) {
    support->push_back(kUniverse[index]);
    EnumerateSupports(target, index + 1, support, cases);
    support->pop_back();
  }
}

[[nodiscard]] std::vector<std::vector<WeightedExactSample>> TinyCases() {
  std::vector<std::vector<WeightedExactSample>> cases;
  cases.reserve(kTinyCount);
  for (std::size_t size = 1; size <= 4; ++size) {
    std::vector<std::uint32_t> support;
    EnumerateSupports(size, 0, &support, &cases);
  }
  if (cases.size() != kTinyCount) {
    throw std::logic_error("verifier tiny inventory is not 780");
  }
  return cases;
}

[[nodiscard]] std::vector<ExactCurve> FitCases(
    const std::vector<std::vector<WeightedExactSample>>& cases,
    std::uint32_t capacity) {
  std::vector<ExactCurve> curves;
  curves.reserve(cases.size());
  for (const auto& samples : cases) {
    // H<=4 for the frozen 780-case authority.  Reuse the verifier's bounded
    // all-partitions reference, never its runtime D&C solver.
    curves.push_back(FitParityScalarExhaustive(samples, capacity));
  }
  return curves;
}

[[nodiscard]] bool PowerOfTwo(std::uint32_t value) {
  return value != 0 && (value & (value - 1U)) == 0;
}

struct Decision {
  std::uint32_t first{0};
  std::uint32_t second{0};
  std::uint64_t states{0};
  ExactValue objective;
  bool reachable{false};
  std::uint64_t evaluations{0};
  std::uint32_t objective_classes{0};
};

struct ObjectiveRanks {
  std::vector<std::vector<std::uint32_t>> ranks;
  std::vector<ExactValue> objectives;
};

[[nodiscard]] ObjectiveRanks BuildRanks(const ExactCurve& first,
                                         const ExactCurve& second,
                                         std::uint32_t capacity) {
  const std::uint32_t h0 = first.at(capacity).effective_cardinality;
  const std::uint32_t h1 = second.at(capacity).effective_cardinality;
  std::vector<std::vector<mpq_class>> sums(
      h0 + 1, std::vector<mpq_class>(h1 + 1));
  std::vector<mpq_class> unique;
  for (std::uint32_t a = 1; a <= h0; ++a) {
    for (std::uint32_t b = 1; b <= h1; ++b) {
      mpq_class sum = first.at(a).sse.coefficient() +
                      second.at(b).sse.coefficient();
      sum.canonicalize();
      sums[a][b] = sum;
      unique.push_back(sum);
    }
  }
  std::sort(unique.begin(), unique.end(), [](const mpq_class& lhs,
                                             const mpq_class& rhs) {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) < 0;
  });
  unique.erase(std::unique(unique.begin(), unique.end(),
                           [](const mpq_class& lhs, const mpq_class& rhs) {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) == 0;
  }), unique.end());
  ObjectiveRanks result;
  result.ranks.assign(h0 + 1, std::vector<std::uint32_t>(h1 + 1));
  for (const mpq_class& value : unique) {
    result.objectives.emplace_back(value.get_num(), value.get_den(), -298);
  }
  for (std::uint32_t a = 1; a <= h0; ++a) {
    for (std::uint32_t b = 1; b <= h1; ++b) {
      const auto found = std::lower_bound(
          unique.begin(), unique.end(), sums[a][b],
          [](const mpq_class& lhs, const mpq_class& rhs) {
            return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) < 0;
          });
      if (found == unique.end()) throw std::logic_error("rank lookup failed");
      result.ranks[a][b] =
          static_cast<std::uint32_t>(found - unique.begin());
    }
  }
  return result;
}

[[nodiscard]] Decision ExhaustiveDecision(const ExactCurve& first,
                                          const ExactCurve& second,
                                          std::uint32_t capacity,
                                          CardinalityDomain domain) {
  const ObjectiveRanks classes = BuildRanks(first, second, capacity);
  bool found = false;
  std::uint32_t best_rank = 0;
  Decision result;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(a)) continue;
    for (std::uint32_t b = 1; b <= capacity / a; ++b) {
      if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(b)) continue;
      ++result.evaluations;
      const std::uint32_t rank =
          classes.ranks[first.at(a).effective_cardinality]
                       [second.at(b).effective_cardinality];
      const std::uint64_t states = static_cast<std::uint64_t>(a) * b;
      if (!found || rank < best_rank ||
          (rank == best_rank &&
           (states > result.states ||
            (states == result.states &&
             std::pair{a, b} < std::pair{result.first, result.second})))) {
        found = true;
        best_rank = rank;
        result.first = a;
        result.second = b;
        result.states = states;
      }
    }
  }
  if (!found) throw std::logic_error("verifier exhaustive decision absent");
  result.objective = classes.objectives[best_rank];
  result.reachable =
      first.at(result.first).effective_cardinality == result.first &&
      second.at(result.second).effective_cardinality == result.second;
  result.objective_classes =
      static_cast<std::uint32_t>(classes.objectives.size());
  return result;
}

[[nodiscard]] Decision BoundaryDecision(const ExactCurve& first,
                                        const ExactCurve& second,
                                        std::uint32_t capacity,
                                        CardinalityDomain domain) {
  bool found = false;
  mpq_class best;
  Decision result;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(a)) continue;
    const std::uint32_t limit = capacity / a;
    const std::uint32_t b =
        domain == CardinalityDomain::kPowersOfTwo
            ? (std::uint32_t{1} << (31U - std::countl_zero(limit)))
            : limit;
    ++result.evaluations;
    mpq_class objective = first.at(a).sse.coefficient() +
                          second.at(b).sse.coefficient();
    objective.canonicalize();
    const std::uint64_t states = static_cast<std::uint64_t>(a) * b;
    const int order = found
                          ? mpq_cmp(objective.get_mpq_t(), best.get_mpq_t())
                          : -1;
    if (!found || order < 0 ||
        (order == 0 &&
         (states > result.states ||
          (states == result.states &&
           std::pair{a, b} < std::pair{result.first, result.second})))) {
      found = true;
      best = objective;
      result.first = a;
      result.second = b;
      result.states = states;
    }
  }
  if (!found) throw std::logic_error("verifier boundary decision absent");
  result.objective = ExactValue(best.get_num(), best.get_den(), -298);
  result.reachable =
      first.at(result.first).effective_cardinality == result.first &&
      second.at(result.second).effective_cardinality == result.second;
  return result;
}

[[nodiscard]] bool SameDecision(const Decision& lhs, const Decision& rhs) {
  return lhs.first == rhs.first && lhs.second == rhs.second &&
         lhs.states == rhs.states && lhs.reachable == rhs.reachable &&
         lhs.objective.binary_grid_exponent ==
             rhs.objective.binary_grid_exponent &&
         lhs.objective.numerator == rhs.objective.numerator &&
         lhs.objective.denominator == rhs.objective.denominator;
}

[[nodiscard]] Json ExactJson(const ExactValue& value);

[[nodiscard]] Json DecisionJson(const Decision& decision) {
  return Json(Json::Object{
      {"cardinalities",
       Json(Json::Array{Json(static_cast<std::int64_t>(decision.first)),
                        Json(static_cast<std::int64_t>(decision.second))})},
      {"objective", ExactJson(decision.objective)},
      {"reachable", Json(decision.reachable)},
      {"used_states", Json(static_cast<std::int64_t>(decision.states))}});
}

[[nodiscard]] std::string DecisionPreimage(const Decision& decision,
                                           std::uint32_t capacity,
                                           bool dyadic) {
  return "{\"capacity\":" + std::to_string(capacity) +
         ",\"cardinalities\":[" + std::to_string(decision.first) + "," +
         std::to_string(decision.second) + "],\"dyadic_only\":" +
         (dyadic ? "true" : "false") +
         ",\"objective\":{\"binary_grid_exponent\":-298,"
         "\"denominator\":\"" + decision.objective.denominator.get_str() +
         "\",\"numerator\":\"" + decision.objective.numerator.get_str() +
         "\"},\"used_states\":" + std::to_string(decision.states) + "}\n";
}

[[nodiscard]] Json ExactJson(const ExactValue& value) {
  return Json(Json::Object{
      {"binary_grid_exponent", Json(static_cast<std::int64_t>(
                                   value.binary_grid_exponent))},
      {"denominator", Json(value.denominator.get_str())},
      {"numerator", Json(value.numerator.get_str())}});
}

template <typename Range>
[[nodiscard]] Json UnsignedArray(const Range& values) {
  Json::Array result;
  for (const auto value : values) {
    result.emplace_back(static_cast<std::int64_t>(value));
  }
  return Json(std::move(result));
}

template <typename Range>
[[nodiscard]] Json Hex32Array(const Range& values) {
  Json::Array result;
  for (const auto value : values) {
    result.emplace_back(Hex32(static_cast<std::uint32_t>(value)));
  }
  return Json(std::move(result));
}

[[nodiscard]] std::string BytesHex(const std::vector<std::uint8_t>& bytes) {
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setfill('0');
  for (const std::uint8_t byte : bytes) {
    output << std::setw(2) << static_cast<unsigned int>(byte);
  }
  return output.str();
}

[[nodiscard]] std::string InventorySha(
    const std::vector<std::vector<WeightedExactSample>>& cases) {
  DigestStream digest;
  for (std::size_t case_id = 0; case_id < cases.size(); ++case_id) {
    std::string row{"{\"case_id\":"};
    row += std::to_string(case_id) + ",\"samples\":[";
    for (std::size_t index = 0; index < cases[case_id].size(); ++index) {
      if (index != 0) row.push_back(',');
      const WeightedExactSample& sample = cases[case_id][index];
      row += "{\"binary32_bits\":\"" + Hex32(sample.binary32_bits) +
             "\",\"vector_id\":" + std::to_string(sample.vector_id) +
             ",\"weight\":\"" + std::to_string(sample.weight) + "\"}";
    }
    row += "]}\n";
    digest.update(row);
  }
  return digest.finish();
}

[[nodiscard]] std::uint64_t MixedEncode(
    const std::vector<std::uint32_t>& labels,
    const std::vector<std::uint32_t>& radices) {
  if (labels.empty() || labels.size() != radices.size()) {
    throw std::runtime_error("verifier mixed-radix shape mismatch");
  }
  std::uint64_t address = 0;
  std::uint64_t multiplier = 1;
  for (std::size_t index = 0; index < labels.size(); ++index) {
    if (radices[index] == 0 || labels[index] >= radices[index]) {
      throw std::runtime_error("verifier mixed-radix digit invalid");
    }
    address += labels[index] * multiplier;
    multiplier *= radices[index];
  }
  return address;
}

[[nodiscard]] std::vector<std::uint32_t> MixedDecode(
    std::uint64_t address, const std::vector<std::uint32_t>& radices) {
  std::uint64_t capacity = 1;
  for (const std::uint32_t radix : radices) capacity *= radix;
  if (radices.empty() || address >= capacity) {
    throw std::invalid_argument("verifier mixed-radix address invalid");
  }
  std::vector<std::uint32_t> labels;
  for (const std::uint32_t radix : radices) {
    labels.push_back(static_cast<std::uint32_t>(address % radix));
    address /= radix;
  }
  return labels;
}

[[nodiscard]] Json MixedRadixFixture() {
  const std::vector<std::uint32_t> radices{3, 5};
  Json::Array entries;
  for (std::uint64_t address = 0; address < 16; ++address) {
    if (address < 15) {
      const std::vector<std::uint32_t> labels = MixedDecode(address, radices);
      const std::uint64_t encoded = MixedEncode(labels, radices);
      entries.emplace_back(Json::Object{
          {"address", Json(static_cast<std::int64_t>(address))},
          {"decoded_labels", UnsignedArray(labels)},
          {"encoded_address", Json(static_cast<std::int64_t>(encoded))},
          {"labels", UnsignedArray(labels)},
          {"valid", Json(true)}});
    } else {
      bool rejected = false;
      try {
        static_cast<void>(MixedDecode(address, radices));
      } catch (const std::invalid_argument&) {
        rejected = true;
      }
      if (!rejected) throw std::logic_error("mixed invalid address accepted");
      entries.emplace_back(Json::Object{
          {"address", Json(static_cast<std::int64_t>(address))},
          {"decoded_labels", Json(nullptr)},
          {"encoded_address", Json(nullptr)},
          {"labels", Json(nullptr)},
          {"valid", Json(false)}});
    }
  }
  return Json(Json::Object{
      {"entries", Json(std::move(entries))},
      {"nominal_capacity", Json(std::int64_t{16})},
      {"radices", UnsignedArray(radices)},
      {"valid_tuple_count", Json(std::int64_t{15})}});
}

[[nodiscard]] std::vector<std::uint8_t> PackMatched(
    const std::vector<std::uint32_t>& labels, std::uint32_t bits) {
  if (labels.size() != 64 || (bits != 4 && bits != 8)) {
    throw std::runtime_error("verifier matched packing shape invalid");
  }
  std::vector<std::uint8_t> bytes(bits == 4 ? 32 : 64, 0);
  for (std::size_t index = 0; index < labels.size(); ++index) {
    if (labels[index] >= (1U << bits)) {
      throw std::runtime_error("verifier matched label overflow");
    }
    if (bits == 4) {
      bytes[index / 2] |= static_cast<std::uint8_t>(
          labels[index] << ((index % 2) == 0 ? 0U : 4U));
    } else {
      bytes[index] = static_cast<std::uint8_t>(labels[index]);
    }
  }
  return bytes;
}

[[nodiscard]] std::vector<std::uint32_t> UnpackMatched(
    const std::vector<std::uint8_t>& bytes, std::uint32_t bits) {
  if (bytes.size() != (bits == 4 ? 32U : 64U)) {
    throw std::runtime_error("verifier matched payload shape invalid");
  }
  std::vector<std::uint32_t> labels(64);
  for (std::size_t index = 0; index < labels.size(); ++index) {
    labels[index] = bits == 4
                        ? ((bytes[index / 2] >>
                            ((index % 2) == 0 ? 0U : 4U)) & 15U)
                        : bytes[index];
  }
  return labels;
}

[[nodiscard]] Json MatchedPackingFixture() {
  Json::Array cases;
  for (const std::uint32_t bits : {4U, 8U}) {
    std::vector<std::uint32_t> labels(64);
    for (std::size_t index = 0; index < labels.size(); ++index) {
      labels[index] = bits == 4 ? index % 16 : (3 * index + 1) % 256;
    }
    const std::vector<std::uint8_t> bytes = PackMatched(labels, bits);
    const std::vector<std::uint32_t> replay = UnpackMatched(bytes, bits);
    if (labels != replay) throw std::logic_error("matched fixture replay failed");
    cases.emplace_back(Json::Object{
        {"labels", UnsignedArray(labels)},
        {"payload_bytes", Json(static_cast<std::int64_t>(bytes.size()))},
        {"payload_hex", Json(BytesHex(bytes))},
        {"roundtrip_labels", UnsignedArray(replay)},
        {"word_bits", Json(static_cast<std::int64_t>(bits))}});
  }
  return Json(std::move(cases));
}

struct GlobalInput {
  std::vector<std::uint8_t> widths;
  std::vector<std::uint32_t> labels;
};

[[nodiscard]] GlobalInput GlobalFixtureInput(std::size_t paid_bytes) {
  GlobalInput result{std::vector<std::uint8_t>(128, 0),
                     std::vector<std::uint32_t>(128, 0)};
  if (paid_bytes == 32) {
    const std::array<std::uint8_t, 7> widths{0, 1, 3, 4, 0, 7, 2};
    const std::array<std::uint32_t, 7> labels{0, 1, 5, 9, 0, 85, 3};
    std::copy(widths.begin(), widths.end(), result.widths.begin());
    std::copy(labels.begin(), labels.end(), result.labels.begin());
  } else if (paid_bytes == 64) {
    const std::array<std::uint8_t, 8> widths{8, 0, 5, 3, 1, 7, 2, 4};
    const std::array<std::uint32_t, 8> labels{255, 0, 17, 5, 1, 100, 3, 9};
    std::copy(widths.begin(), widths.end(), result.widths.begin());
    std::copy(labels.begin(), labels.end(), result.labels.begin());
  } else {
    throw std::runtime_error("global fixture paid bytes invalid");
  }
  return result;
}

struct GlobalPacked {
  std::vector<std::uint8_t> bytes;
  std::vector<std::uint32_t> offsets;
  std::uint32_t used{0};
};

[[nodiscard]] GlobalPacked PackGlobal(const GlobalInput& input,
                                      std::size_t paid_bytes) {
  GlobalPacked result;
  result.bytes.assign(paid_bytes, 0);
  std::uint32_t offset = 0;
  for (std::size_t coordinate = 0; coordinate < 128; ++coordinate) {
    const std::uint8_t width = input.widths[coordinate];
    if (width > 8 || input.labels[coordinate] >= (1U << width) ||
        offset + width > paid_bytes * 8U) {
      throw std::runtime_error("global fixture label invalid");
    }
    result.offsets.push_back(offset);
    for (std::uint32_t bit = 0; bit < width; ++bit) {
      if (((input.labels[coordinate] >> bit) & 1U) != 0) {
        const std::uint32_t stream = offset + bit;
        result.bytes[stream / 8U] |=
            static_cast<std::uint8_t>(1U << (stream % 8U));
      }
    }
    offset += width;
  }
  result.used = offset;
  return result;
}

[[nodiscard]] std::vector<std::uint32_t> UnpackGlobal(
    const GlobalPacked& packed, const std::vector<std::uint8_t>& widths) {
  std::vector<std::uint32_t> labels(128, 0);
  std::uint32_t offset = 0;
  for (std::size_t coordinate = 0; coordinate < 128; ++coordinate) {
    for (std::uint32_t bit = 0; bit < widths[coordinate]; ++bit) {
      const std::uint32_t stream = offset + bit;
      labels[coordinate] |=
          ((packed.bytes[stream / 8U] >> (stream % 8U)) & 1U) << bit;
    }
    offset += widths[coordinate];
  }
  return labels;
}

[[nodiscard]] Json GlobalPackingCase(std::size_t paid_bytes) {
  const GlobalInput input = GlobalFixtureInput(paid_bytes);
  const GlobalPacked packed = PackGlobal(input, paid_bytes);
  const std::vector<std::uint32_t> replay =
      UnpackGlobal(packed, input.widths);
  bool zero_tail = replay == input.labels;
  for (std::uint64_t bit = packed.used; bit < packed.bytes.size() * 8ULL; ++bit) {
    zero_tail = zero_tail &&
                ((packed.bytes[bit / 8U] >> (bit % 8U)) & 1U) == 0;
  }
  if (!zero_tail) throw std::logic_error("global fixture replay failed");
  return Json(Json::Object{
      {"bit_offsets", UnsignedArray(packed.offsets)},
      {"bit_widths", UnsignedArray(input.widths)},
      {"labels", UnsignedArray(input.labels)},
      {"paid_payload_bytes", Json(static_cast<std::int64_t>(paid_bytes))},
      {"payload_hex", Json(BytesHex(packed.bytes))},
      {"roundtrip_labels", UnsignedArray(replay)},
      {"used_bits", Json(static_cast<std::int64_t>(packed.used))},
      {"zero_tail", Json(true)}});
}

[[nodiscard]] Json GlobalPackingFixture() {
  return Json(Json::Array{GlobalPackingCase(32), GlobalPackingCase(64)});
}

struct PointBits {
  std::uint32_t x{0};
  std::uint32_t y{0};
};

[[nodiscard]] double Promote(std::uint32_t bits) {
  const float value = std::bit_cast<float>(bits);
  if (!std::isfinite(value)) throw std::runtime_error("lookup value nonfinite");
  return static_cast<double>(value);
}

[[nodiscard]] Json LookupValue(double distance) {
  const float stored = static_cast<float>(distance);
  if (!std::isfinite(distance) || !std::isfinite(stored)) {
    throw std::runtime_error("lookup distance nonfinite");
  }
  return Json(Json::Object{
      {"pre_narrow_binary64_bits",
       Json(Hex64(std::bit_cast<std::uint64_t>(distance)))},
      {"stored_binary32_bits",
       Json(Hex32(std::bit_cast<std::uint32_t>(stored)))},
      {"valid", Json(true)}});
}

[[nodiscard]] Json InvalidLookupValue() {
  return Json(Json::Object{
      {"pre_narrow_binary64_bits", Json("0x7ff0000000000000")},
      {"stored_binary32_bits", Json("0x7f800000")},
      {"valid", Json(false)}});
}

[[nodiscard]] std::vector<std::uint32_t> BitsOf(
    const std::vector<float>& values) {
  std::vector<std::uint32_t> result;
  for (const float value : values) {
    result.push_back(std::bit_cast<std::uint32_t>(value));
  }
  return result;
}

[[nodiscard]] Json MatchedLookupCase(
    std::uint32_t capacity, const std::vector<std::uint32_t>& axis0,
    const std::vector<std::uint32_t>& axis1, PointBits query) {
  std::vector<PointBits> reconstructions;
  for (const std::uint32_t y : axis1) {
    for (const std::uint32_t x : axis0) {
      reconstructions.push_back(PointBits{x, y});
    }
  }
  if (reconstructions.empty() || reconstructions.size() > capacity) {
    throw std::runtime_error("matched lookup reconstruction shape invalid");
  }
  Json::Array entries;
  for (std::size_t address = 0; address < capacity; ++address) {
    Json::Object entry{{"address", Json(static_cast<std::int64_t>(address))}};
    const Json value = address < reconstructions.size()
                           ? LookupValue(
                                 (Promote(query.x) -
                                  Promote(reconstructions[address].x)) *
                                     (Promote(query.x) -
                                      Promote(reconstructions[address].x)) +
                                 (Promote(query.y) -
                                  Promote(reconstructions[address].y)) *
                                     (Promote(query.y) -
                                      Promote(reconstructions[address].y)))
                           : InvalidLookupValue();
    for (const auto& [key, field] : value.object()) entry.emplace(key, field);
    entries.emplace_back(std::move(entry));
  }
  Json::Array reconstruction_json;
  for (const PointBits& point : reconstructions) {
    reconstruction_json.emplace_back(
        Json::Array{Json(Hex32(point.x)), Json(Hex32(point.y))});
  }
  return Json(Json::Object{
      {"axis0_centroid_bits", Hex32Array(axis0)},
      {"axis1_centroid_bits", Hex32Array(axis1)},
      {"capacity", Json(static_cast<std::int64_t>(capacity))},
      {"entries", Json(std::move(entries))},
      {"query_bits", Json(Json::Array{Json(Hex32(query.x)),
                                      Json(Hex32(query.y))})},
      {"radices", Json(Json::Array{
                      Json(static_cast<std::int64_t>(axis0.size())),
                      Json(static_cast<std::int64_t>(axis1.size()))})},
      {"reconstruction_bits", Json(std::move(reconstruction_json))},
      {"valid_states",
       Json(static_cast<std::int64_t>(reconstructions.size()))}});
}

[[nodiscard]] Json MatchedLookupFixture() {
  const std::vector<std::uint32_t> axis0_b4 =
      BitsOf({-1.0F, 0.0F, 2.0F});
  const std::vector<std::uint32_t> axis1_b4 =
      BitsOf({-2.0F, -0.5F, 1.0F, 3.0F, 4.0F});
  std::vector<float> values0;
  std::vector<float> values1;
  for (int value = -6; value <= 6; ++value) values0.push_back(value);
  for (int value = -9; value <= 9; ++value) values1.push_back(value);
  return Json(Json::Array{
      MatchedLookupCase(
          16, axis0_b4, axis1_b4,
          PointBits{std::bit_cast<std::uint32_t>(0.5F),
                    std::bit_cast<std::uint32_t>(-0.75F)}),
      MatchedLookupCase(
          256, BitsOf(values0), BitsOf(values1),
          PointBits{std::bit_cast<std::uint32_t>(0.25F),
                    std::bit_cast<std::uint32_t>(-0.5F)})});
}

[[nodiscard]] std::vector<std::uint32_t> LookupPalette() {
  return BitsOf({-4.0F, -3.0F, -2.0F, -1.0F, -0.5F, -0.25F, 0.0F, 0.25F,
                 0.5F, 1.0F, 2.0F, 3.0F, 4.0F, 5.0F, 6.0F, 8.0F});
}

[[nodiscard]] Json GlobalLookupFixture() {
  const GlobalInput packing = GlobalFixtureInput(32);
  const std::vector<std::uint32_t> palette = LookupPalette();
  std::vector<std::uint32_t> query(128);
  std::vector<std::vector<std::uint32_t>> centroids(128);
  std::vector<std::uint32_t> offsets{0};
  for (std::size_t coordinate = 0; coordinate < 128; ++coordinate) {
    query[coordinate] = palette[(3 * coordinate) % palette.size()];
    const std::size_t cardinality =
        std::size_t{1} << packing.widths[coordinate];
    for (std::size_t label = 0; label < cardinality; ++label) {
      centroids[coordinate].push_back(
          palette[(coordinate + 3 * label) % palette.size()]);
    }
    offsets.push_back(offsets.back() +
                      static_cast<std::uint32_t>(cardinality));
  }
  Json::Array centroid_json;
  Json::Array entries;
  std::size_t flat = 0;
  for (std::size_t coordinate = 0; coordinate < 128; ++coordinate) {
    centroid_json.push_back(Hex32Array(centroids[coordinate]));
    for (std::size_t label = 0; label < centroids[coordinate].size(); ++label) {
      const double difference = Promote(query[coordinate]) -
                                Promote(centroids[coordinate][label]);
      Json::Object entry{
          {"coordinate", Json(static_cast<std::int64_t>(coordinate))},
          {"flat_index", Json(static_cast<std::int64_t>(flat))},
          {"label", Json(static_cast<std::int64_t>(label))}};
      const Json value = LookupValue(difference * difference);
      for (const auto& [key, field] : value.object()) entry.emplace(key, field);
      entries.emplace_back(std::move(entry));
      ++flat;
    }
  }
  if (flat != offsets.back()) throw std::logic_error("global lookup offset mismatch");
  return Json(Json::Object{
      {"bit_widths", UnsignedArray(packing.widths)},
      {"centroid_bits_by_coordinate", Json(std::move(centroid_json))},
      {"coordinate_offsets", UnsignedArray(offsets)},
      {"entries", Json(std::move(entries))},
      {"query_coordinate_bits", Hex32Array(query)}});
}

[[nodiscard]] ExactCurve ThreePointCurve(
    const std::array<std::uint64_t, 3>& weights, std::uint32_t maximum) {
  std::vector<WeightedExactSample> samples;
  for (std::size_t index = 0; index < weights.size(); ++index) {
    samples.push_back(WeightedExactSample{kUniverse[index], weights[index],
                                          index});
  }
  return FitParityScalarExhaustive(samples, maximum);
}

[[nodiscard]] Json SmallParity(const Decision& independent,
                               const Decision& optimized) {
  return Json(Json::Object{
      {"independent_cardinalities",
       Json(Json::Array{Json(static_cast<std::int64_t>(independent.first)),
                        Json(static_cast<std::int64_t>(independent.second))})},
      {"independent_feasible_tuple_evaluation_count",
       Json(std::to_string(independent.evaluations))},
      {"independent_objective", ExactJson(independent.objective)},
      {"optimized_candidate_evaluation_count",
       Json(std::to_string(optimized.evaluations))},
      {"optimized_cardinalities",
       Json(Json::Array{Json(static_cast<std::int64_t>(optimized.first)),
                        Json(static_cast<std::int64_t>(optimized.second))})},
      {"optimized_objective", ExactJson(optimized.objective)},
      {"parity", Json(SameDecision(independent, optimized))}});
}

[[nodiscard]] Json DifferentWeightFixture() {
  constexpr std::uint32_t capacity = 4;
  const ExactCurve curve_a = ThreePointCurve({1, 1, 1}, capacity);
  const ExactCurve curve_b = ThreePointCurve({1, 1, 2}, capacity);
  const ExactCurve mate = ThreePointCurve({3, 3, 3}, capacity);
  if (curve_a.at(1).sse.coefficient() == curve_b.at(1).sse.coefficient() ||
      curve_a.at(3).sse.coefficient() != curve_b.at(3).sse.coefficient()) {
    throw std::logic_error("verifier weight fixture not discriminative");
  }
  Json::Array arms;
  for (const CardinalityDomain domain :
       {CardinalityDomain::kAllPositive, CardinalityDomain::kPowersOfTwo}) {
    const Decision ia = ExhaustiveDecision(curve_a, mate, capacity, domain);
    const Decision ib = ExhaustiveDecision(curve_b, mate, capacity, domain);
    const Decision oa = BoundaryDecision(curve_a, mate, capacity, domain);
    const Decision ob = BoundaryDecision(curve_b, mate, capacity, domain);
    if (!SameDecision(ia, oa) || !SameDecision(ib, ob) || ia.first != 1 ||
        ia.second != 4 || ib.first != 2 || ib.second != 2) {
      throw std::logic_error("verifier weight winner fixture failed");
    }
    arms.emplace_back(Json::Object{
        {"cardinality_kind",
         Json(domain == CardinalityDomain::kPowersOfTwo ? "dyadic"
                                                        : "arbitrary")},
        {"curve_a", SmallParity(ia, oa)},
        {"curve_b", SmallParity(ib, ob)},
        {"different_weight_sensitive_winners", Json(true)}});
  }
  return Json(Json::Object{
      {"arms", Json(std::move(arms))},
      {"capacity", Json(std::int64_t{4})},
      {"common_support_binary32_bits",
       Json(Json::Array{Json(Hex32(kUniverse[0])), Json(Hex32(kUniverse[1])),
                        Json(Hex32(kUniverse[2]))})},
      {"curve_a_k1_objective", ExactJson(curve_a.at(1).sse)},
      {"curve_a_weights",
       Json(Json::Array{Json(std::int64_t{1}), Json(std::int64_t{1}),
                        Json(std::int64_t{1})})},
      {"curve_b_k1_objective", ExactJson(curve_b.at(1).sse)},
      {"curve_b_weights",
       Json(Json::Array{Json(std::int64_t{1}), Json(std::int64_t{1}),
                        Json(std::int64_t{2})})},
      {"mate_weights",
       Json(Json::Array{Json(std::int64_t{3}), Json(std::int64_t{3}),
                        Json(std::int64_t{3})})},
      {"same_support_size", Json(std::int64_t{3})}});
}

[[nodiscard]] std::uint64_t FeasibleCount(std::uint32_t capacity,
                                          CardinalityDomain domain) {
  std::uint64_t count = 0;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(a)) continue;
    for (std::uint32_t b = 1; b <= capacity / a; ++b) {
      if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(b)) continue;
      ++count;
    }
  }
  return count;
}

[[nodiscard]] Json SupportWinnerFixture() {
  Json::Array records;
  for (const std::uint32_t capacity : kCapacities) {
    std::vector<ExactCurve> curves;
    for (std::size_t size = 1; size <= 4; ++size) {
      std::vector<WeightedExactSample> samples;
      for (std::size_t index = 0; index < size; ++index) {
        samples.push_back(WeightedExactSample{kUniverse[index], 1, index});
      }
      curves.push_back(FitParityScalarExhaustive(samples, capacity));
    }
    for (const CardinalityDomain domain :
         {CardinalityDomain::kAllPositive,
          CardinalityDomain::kPowersOfTwo}) {
      for (std::size_t first = 1; first <= 4; ++first) {
        for (std::size_t second = 1; second <= 4; ++second) {
          const Decision selected = BoundaryDecision(
              curves[first - 1], curves[second - 1], capacity, domain);
          records.emplace_back(Json::Object{
              {"capacity", Json(static_cast<std::int64_t>(capacity))},
              {"cardinality_kind",
               Json(domain == CardinalityDomain::kPowersOfTwo ? "dyadic"
                                                              : "arbitrary")},
              {"exhaustive_valid_tuple_count",
               Json(std::to_string(FeasibleCount(capacity, domain)))},
              {"first_support_size", Json(static_cast<std::int64_t>(first))},
              {"objective", ExactJson(selected.objective)},
              {"optimized_candidate_evaluation_count",
               Json(std::to_string(selected.evaluations))},
              {"reachable", Json(selected.reachable)},
              {"second_support_size", Json(static_cast<std::int64_t>(second))},
              {"selected_cardinalities",
               Json(Json::Array{
                   Json(static_cast<std::int64_t>(selected.first)),
                   Json(static_cast<std::int64_t>(selected.second))})},
              {"used_states",
               Json(static_cast<std::int64_t>(selected.states))}});
        }
      }
    }
  }
  if (records.size() != 64) throw std::logic_error("support fixture not 64");
  return Json(std::move(records));
}

[[nodiscard]] bool LowerLabelTieControl() {
  const double query = 0.0;
  const std::array<double, 2> centers{-1.0, 1.0};
  std::size_t best = 0;
  double minimum = std::numeric_limits<double>::infinity();
  for (std::size_t index = 0; index < centers.size(); ++index) {
    const double difference = query - centers[index];
    const double distance = difference * difference;
    if (distance < minimum) {
      minimum = distance;
      best = index;
    }
  }
  return best == 0;
}

}  // namespace

void WriteRepresentationParity(const std::string& output_path) {
  const std::vector<std::vector<WeightedExactSample>> cases = TinyCases();
  DigestStream independent_hash;
  DigestStream optimized_hash;
  std::uint64_t record_count = 0;
  std::uint64_t equality_count = 0;
  std::uint64_t exhaustive_count = 0;
  std::uint64_t optimized_count = 0;
  std::uint64_t objective_classes = 0;
  std::string first_mismatch{"null"};
  bool objective_contract = true;
  for (const std::uint32_t capacity : kCapacities) {
    const std::vector<ExactCurve> curves = FitCases(cases, capacity);
    for (const CardinalityDomain domain :
         {CardinalityDomain::kAllPositive,
          CardinalityDomain::kPowersOfTwo}) {
      const bool dyadic = domain == CardinalityDomain::kPowersOfTwo;
      for (std::size_t first_id = 0; first_id < curves.size(); ++first_id) {
        const ExactCurve& first = curves[first_id];
        for (std::size_t second_id = 0; second_id < curves.size(); ++second_id) {
          const ExactCurve& second = curves[second_id];
          const Decision independent =
              ExhaustiveDecision(first, second, capacity, domain);
          const Decision optimized =
              BoundaryDecision(first, second, capacity, domain);
          independent_hash.update(
              DecisionPreimage(independent, capacity, dyadic));
          optimized_hash.update(DecisionPreimage(optimized, capacity, dyadic));
          exhaustive_count += independent.evaluations;
          optimized_count += optimized.evaluations;
          objective_classes += independent.objective_classes;
          objective_contract = objective_contract &&
              independent.objective.binary_grid_exponent == -298 &&
              optimized.objective.binary_grid_exponent == -298;
          const bool equal = SameDecision(independent, optimized);
          equality_count += equal ? 1U : 0U;
          if (!equal && first_mismatch == "null") {
            first_mismatch = DumpJson(Json(Json::Object{
                {"capacity", Json(static_cast<std::int64_t>(capacity))},
                {"cardinality_kind", Json(dyadic ? "dyadic" : "arbitrary")},
                {"first_case_id", Json(static_cast<std::int64_t>(first_id))},
                {"independent", DecisionJson(independent)},
                {"optimized", DecisionJson(optimized)},
                {"second_case_id", Json(static_cast<std::int64_t>(second_id))}}));
          }
          ++record_count;
        }
      }
    }
  }
  if (record_count != kRecordCount || exhaustive_count != kExhaustiveCount ||
      optimized_count != kOptimizedCount || !LowerLabelTieControl()) {
    throw std::logic_error("verifier representation PAR inventory changed");
  }
  const std::string independent_sha = independent_hash.finish();
  const std::string optimized_sha = optimized_hash.finish();
  const bool decisions_equal = equality_count == record_count;
  const bool hashes_equal = independent_sha == optimized_sha;

  const Json global_lookup = GlobalLookupFixture();
  const Json global_packing = GlobalPackingFixture();
  const Json matched_lookup = MatchedLookupFixture();
  const Json matched_packing = MatchedPackingFixture();
  const Json mixed_radix = MixedRadixFixture();
  const Json weight_fixture = DifferentWeightFixture();
  const Json support_fixture = SupportWinnerFixture();
  const std::string inventory_sha = InventorySha(cases);

  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create representation PAR output");
  // Preserve the predecessor full-suite field order for byte-exact PAR.
  output << "{\"allocation_record_count\":" << record_count
         << ",\"allocation_sha256\":\"" << optimized_sha
         << "\",\"all_decisions_equal\":"
         << (decisions_equal ? "true" : "false")
         << ",\"authority_hashes_equal\":"
         << (hashes_equal ? "true" : "false")
         << ",\"candidate_counts\":{"
         << "\"independent_feasible_tuple_evaluations\":\""
         << exhaustive_count
         << "\",\"optimized_candidate_evaluations\":\"" << optimized_count
         << "\"},\"checks\":{\"allocation_record_count\":true,"
         << "\"all_decisions_equal\":"
         << (decisions_equal ? "true" : "false")
         << ",\"authority_hashes_equal\":"
         << (hashes_equal ? "true" : "false")
         << ",\"candidate_counts\":true,"
         << "\"equidistant_lower_codeword\":true,\"objective_contract\":"
         << (objective_contract ? "true" : "false")
         << ",\"representation_constant_smoke\":true,"
         << "\"tiny_case_count\":true},\"decision_equality_count\":"
         << equality_count << ",\"exact_objective_class_count\":\""
         << objective_classes << "\",\"first_mismatch\":" << first_mismatch
         << ",\"global_lookup_case\":"
         << DumpJson(global_lookup) << ",\"global_packing_cases\":"
         << DumpJson(global_packing) << ",\"matched_lookup_cases\":"
         << DumpJson(matched_lookup) << ",\"matched_packing_cases\":"
         << DumpJson(matched_packing) << ",\"mixed_radix_case\":"
         << DumpJson(mixed_radix) << ",\"independent_exhaustive_sha256\":\""
         << independent_sha << "\",\"optimized_sha256\":\"" << optimized_sha
         << "\",\"python_order_fingerprint_authoritative\":false,"
         << "\"python_order_fingerprint_sha256\":\"" << optimized_sha
         << "\",\"same_h_different_weight_fixture\":"
         << DumpJson(weight_fixture) << ",\"support_size_winners\":"
         << DumpJson(support_fixture)
         << ",\"tiny_curve_inventory_preimage_schema\":\""
            "canonical JSONL: case_id, then samples with binary32_bits, "
            "vector_id, weight; terminal LF per case\","
         << "\"tiny_curve_inventory_sha256\":\"" << inventory_sha
         << "\"}\n";
  output.flush();
  if (!output) throw std::runtime_error("representation PAR output failed");
}

}  // namespace saq::a4_v2::verifier

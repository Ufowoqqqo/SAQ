#include "replay.hpp"

#include "exact_reference.hpp"
#include "input_panel.hpp"
#include "sha256.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_v2::verifier {
namespace {

constexpr std::string_view kProtocol =
    "saq-a4-v2-synthetic-construction-20260714-schema1";
constexpr std::string_view kHashDomain =
    "saq-attempt4-a4-1-20260713-schema2";
constexpr std::string_view kDataset = "synthetic_cost_projection";
constexpr std::array<std::string_view, 8> kCountKeys{
    "allocation_group_records", "allocation_global_records",
    "block_metadata_records", "block_start_records", "block_step_records",
    "bundle_files", "encoding_arm_records", "scalar_optimum_records"};
constexpr std::array<std::string_view, 4> kArms{
    "dyadic_word", "arbitrary_word", "trained_block_vq",
    "global_dyadic_pack_cap8"};

using Curves = std::vector<ExactCurve>;

struct Discrepancies {
  Json::Array values;

  void add(std::string location, std::string message,
           const Json* expected = nullptr, const Json* observed = nullptr,
           std::string klass = "SCIENTIFIC_REPLAY_MISMATCH") {
    Json expected_hash(nullptr);
    Json observed_hash(nullptr);
    if (expected != nullptr) expected_hash = Json(Sha256(DumpJson(*expected)));
    if (observed != nullptr) observed_hash = Json(Sha256(DumpJson(*observed)));
    values.emplace_back(Json::Object{
        {"class", Json(std::move(klass))},
        {"expected_sha256", std::move(expected_hash)},
        {"location", Json(std::move(location))},
        {"message", Json(std::move(message))},
        {"observed_sha256", std::move(observed_hash)}});
  }

  void expect(std::string location, const Json& expected,
              const Json& observed, std::string message) {
    if (DumpJson(expected) != DumpJson(observed)) {
      add(std::move(location), std::move(message), &expected, &observed);
    }
  }
};

[[nodiscard]] std::uint32_t U32(const Json& value, const char* field) {
  const std::int64_t parsed = value.integer();
  if (parsed < 0 || parsed > std::numeric_limits<std::uint32_t>::max()) {
    throw std::runtime_error(std::string(field) + " is outside uint32");
  }
  return static_cast<std::uint32_t>(parsed);
}

[[nodiscard]] std::uint64_t ParseHex(std::string_view text,
                                     std::size_t digits,
                                     const char* field) {
  if (text.size() != digits) {
    throw std::runtime_error(std::string(field) + " has wrong hex width");
  }
  std::uint64_t result = 0;
  for (const char byte : text) {
    result <<= 4U;
    if (byte >= '0' && byte <= '9') result |= byte - '0';
    else if (byte >= 'a' && byte <= 'f') result |= byte - 'a' + 10;
    else throw std::runtime_error(std::string(field) + " is not lowercase hex");
  }
  return result;
}

[[nodiscard]] std::string Hex32(std::uint32_t value) {
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setw(8) << std::setfill('0')
         << value;
  return output.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t value) {
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setw(16) << std::setfill('0')
         << value;
  return output.str();
}

[[nodiscard]] Json ExactJson(const ExactValue& value) {
  return Json(Json::Object{
      {"binary_grid_exponent",
       Json(static_cast<std::int64_t>(value.binary_grid_exponent))},
      {"denominator", Json(value.denominator.get_str())},
      {"numerator", Json(value.numerator.get_str())}});
}

[[nodiscard]] Json U32Array(const std::vector<std::uint32_t>& values) {
  Json::Array result;
  result.reserve(values.size());
  for (const std::uint32_t value : values) {
    result.emplace_back(static_cast<std::int64_t>(value));
  }
  return Json(std::move(result));
}

[[nodiscard]] Json U8Array(const std::vector<std::uint8_t>& values) {
  Json::Array result;
  result.reserve(values.size());
  for (const std::uint8_t value : values) {
    result.emplace_back(static_cast<std::int64_t>(value));
  }
  return Json(std::move(result));
}

void ValidateSha256(std::string_view digest, std::string_view role) {
  if (digest.size() != 64 ||
      !std::all_of(digest.begin(), digest.end(), [](char byte) {
        return (byte >= '0' && byte <= '9') ||
               (byte >= 'a' && byte <= 'f');
      })) {
    throw std::runtime_error(std::string(role) + " SHA-256 is not canonical");
  }
}

[[nodiscard]] std::string ReadBoundArtifact(const Json& request,
                                            std::string_view path,
                                            std::uint64_t maximum_bytes) {
  const Json::Object& files = request.at("artifact_files").object();
  const auto found = files.find(path);
  if (found == files.end()) {
    throw std::runtime_error("request omits bound artifact: " +
                             std::string(path));
  }
  const Json::Object& identity = found->second.object();
  static const std::set<std::string, std::less<>> kIdentityKeys{
      "fd", "sha256", "size_bytes"};
  std::set<std::string, std::less<>> observed;
  for (const auto& [key, unused] : identity) {
    static_cast<void>(unused);
    observed.insert(key);
  }
  if (observed != kIdentityKeys) {
    throw std::runtime_error("bound artifact identity key set mismatch");
  }
  const std::int64_t raw_fd = identity.at("fd").integer();
  const std::int64_t raw_size = identity.at("size_bytes").integer();
  if (raw_fd < 0 || raw_fd > std::numeric_limits<int>::max() || raw_size < 0 ||
      static_cast<std::uint64_t>(raw_size) > maximum_bytes) {
    throw std::runtime_error("bound artifact descriptor/size is invalid");
  }
  ValidateSha256(identity.at("sha256").string(), path);
  const std::string payload =
      ReadFileDescriptor(static_cast<int>(raw_fd), maximum_bytes);
  if (payload.size() != static_cast<std::uint64_t>(raw_size) ||
      Sha256(payload) != identity.at("sha256").string()) {
    throw std::runtime_error("bound artifact size/hash mismatch: " +
                             std::string(path));
  }
  return payload;
}

[[nodiscard]] Json::Object ZeroCounts() {
  Json::Object result;
  for (const std::string_view key : kCountKeys) {
    result.emplace(std::string(key), Json(std::int64_t{0}));
  }
  return result;
}

[[nodiscard]] Json Response(const Json& request, bool complete,
                            Json::Object counts, Json::Array discrepancies) {
  return Json(Json::Object{
      {"artifact_kind", Json("a4_v2_native_replay")},
      {"build_manifest_sha256",
       Json(request.at("build_manifest_sha256").string())},
      {"complete", Json(complete)},
      {"decision_counts_observed", Json(std::move(counts))},
      {"discrepancies", Json(std::move(discrepancies))},
      {"input_identity_sha256",
       Json(request.at("input_identity_sha256").string())},
      {"native_binary_sha256",
       Json(request.at("native_binary_sha256").string())},
      {"native_child_argv_sha256",
       Json(request.at("native_child_argv_sha256").string())},
      {"producer_manifest_sha256",
       Json(request.at("producer_manifest_sha256").string())},
      {"schema_version", Json(std::int64_t{1})},
      {"source_manifest_sha256",
       Json(request.at("source_manifest_sha256").string())}});
}

void ValidateRequest(const Json& request) {
  static const std::set<std::string, std::less<>> kExpected{
      "artifact_files", "build_manifest_sha256", "completed_unit_count",
      "decision_counts_expected", "input_identity_sha256",
      "last_completed_unit_index", "native_binary_sha256",
      "native_child_argv_sha256", "producer_manifest_sha256",
      "protocol_identity", "protocol_version", "schema_identity",
      "schema_version", "source_manifest_sha256"};
  std::set<std::string, std::less<>> observed;
  for (const auto& [key, unused] : request.object()) {
    static_cast<void>(unused);
    observed.insert(key);
  }
  if (observed != kExpected) throw std::runtime_error("request key set mismatch");
  const std::uint32_t completed = U32(request.at("completed_unit_count"), "completed");
  if (completed > 396 || request.at("last_completed_unit_index").integer() !=
                             static_cast<std::int64_t>(completed) - 1) {
    throw std::runtime_error("request unit prefix mismatch");
  }
  if (request.at("protocol_version").string() != kProtocol ||
      request.at("schema_version").integer() != 1) {
    throw std::runtime_error("request protocol/schema identity mismatch");
  }
  for (const std::string_view key :
       {"build_manifest_sha256", "input_identity_sha256",
        "native_binary_sha256", "native_child_argv_sha256",
        "producer_manifest_sha256", "source_manifest_sha256"}) {
    ValidateSha256(request.at(key).string(), key);
  }
  const Json::Object& expected_counts =
      request.at("decision_counts_expected").object();
  if (expected_counts.size() != kCountKeys.size()) {
    throw std::runtime_error("request count key count mismatch");
  }
  for (const std::string_view key : kCountKeys) {
    if (!expected_counts.contains(key) || expected_counts.at(std::string(key)).integer() < 0) {
      throw std::runtime_error("request count inventory mismatch");
    }
  }

  const auto validate_document_identity = [](const Json& raw,
                                             std::string_view expected_path) {
    const Json::Object& identity = raw.object();
    static const std::set<std::string, std::less<>> kKeys{
        "path", "sha256", "size_bytes"};
    std::set<std::string, std::less<>> keys;
    for (const auto& [key, unused] : identity) {
      static_cast<void>(unused);
      keys.insert(key);
    }
    if (keys != kKeys || identity.at("path").string() != expected_path ||
        identity.at("size_bytes").integer() < 0) {
      throw std::runtime_error("request document identity mismatch");
    }
    ValidateSha256(identity.at("sha256").string(), expected_path);
  };
  validate_document_identity(
      request.at("protocol_identity"),
      "docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json");
  validate_document_identity(
      request.at("schema_identity"),
      "docs/saq_a4_v2_artifact_schema_2026_07_14.json");

  std::set<std::string, std::less<>> expected_files{
      "evidence/allocation_summary.json",
      "evidence/block_trajectories.jsonl",
      "evidence/encoding_summary.json",
      "evidence/producer_manifest.json",
      "evidence/scalar_optimum_records.jsonl"};
  if (completed == 396) {
    expected_files.insert("bundle/codes_b04.bin");
    expected_files.insert("bundle/codes_b08.bin");
    expected_files.insert("bundle/models.json");
    expected_files.insert("bundle/representation_manifest.json");
  }
  std::set<std::string, std::less<>> observed_files;
  std::set<std::int64_t> observed_descriptors;
  for (const auto& [path, raw_identity] : request.at("artifact_files").object()) {
    observed_files.insert(path);
    const Json::Object& identity = raw_identity.object();
    static const std::set<std::string, std::less<>> kIdentityKeys{
        "fd", "sha256", "size_bytes"};
    std::set<std::string, std::less<>> keys;
    for (const auto& [key, unused] : identity) {
      static_cast<void>(unused);
      keys.insert(key);
    }
    const std::int64_t descriptor = identity.at("fd").integer();
    if (keys != kIdentityKeys || descriptor < 200 ||
        identity.at("size_bytes").integer() < 0 ||
        !observed_descriptors.insert(descriptor).second) {
      throw std::runtime_error("request artifact descriptor closure mismatch");
    }
    ValidateSha256(identity.at("sha256").string(), path);
  }
  if (observed_files != expected_files) {
    throw std::runtime_error("request artifact-file membership is not exact");
  }
}

[[nodiscard]] Json ExpectedScalarRecord(std::uint32_t coordinate,
                                        const ExactCurve& curve,
                                        std::uint32_t requested) {
  const ExactSolution& solution = curve.at(requested);
  Json::Array b32;
  Json::Array b64;
  Json::Array means;
  Json::Array partition;
  bool strictly_increasing = true;
  bool have_previous = false;
  float previous = 0.0F;
  for (const ExactInterval& interval : solution.intervals) {
    const std::uint32_t bits32 = DirectRoundBinary32(interval.mean);
    const std::uint64_t bits64 = DirectRoundBinary64(interval.mean);
    const float current = std::bit_cast<float>(bits32);
    if (have_previous && !(previous < current)) strictly_increasing = false;
    have_previous = true;
    previous = current;
    b32.emplace_back(Hex32(bits32));
    b64.emplace_back(Hex64(bits64));
    means.push_back(ExactJson(interval.mean));
    partition.emplace_back(Json::Object{
        {"support_begin", Json(static_cast<std::int64_t>(interval.begin))},
        {"support_end_exclusive", Json(static_cast<std::int64_t>(interval.end))}});
  }
  return Json(Json::Object{
      {"binary32_centroid_bits", Json(std::move(b32))},
      {"binary64_centroid_bits", Json(std::move(b64))},
      {"comparison_count",
       Json(std::to_string(solution.registered_comparison_count))},
      {"coordinate_id", Json(static_cast<std::int64_t>(coordinate))},
      {"distinct_support_size",
       Json(static_cast<std::int64_t>(curve.support.size()))},
      {"effective_cardinality",
       Json(static_cast<std::int64_t>(solution.effective_cardinality))},
      {"exact_means", Json(std::move(means))},
      {"exact_sse", ExactJson(solution.sse)},
      {"exact_tie_count", Json(std::to_string(solution.registered_tie_count))},
      {"fit_row_count", Json(static_cast<std::int64_t>(kRows))},
      {"partition", Json(std::move(partition))},
      {"record_type", Json("scalar_optimum_v2")},
      {"requested_cardinality", Json(static_cast<std::int64_t>(requested))},
      {"serialized_binary32_strictly_increasing", Json(strictly_increasing)}});
}

void ReplayScalar(const InputPanel& panel, const std::vector<Json>& records,
                  Curves* curves, Discrepancies* discrepancies) {
  if ((records.size() % 256U) != 0 || records.size() > 128U * 256U) {
    throw std::runtime_error("scalar record inventory is not a coordinate prefix");
  }
  const std::uint32_t coordinate_count =
      static_cast<std::uint32_t>(records.size() / 256U);
  curves->reserve(coordinate_count);
  for (std::uint32_t coordinate = 0; coordinate < coordinate_count;
       ++coordinate) {
    std::vector<std::uint32_t> column(kRows);
    for (std::uint32_t row = 0; row < kRows; ++row) {
      column[row] = panel.row_major_bits[static_cast<std::size_t>(row) *
                                             kDimensions +
                                         coordinate];
    }
    curves->push_back(FitCurveDivideConquer(column, 256));
    for (std::uint32_t requested = 1; requested <= 256; ++requested) {
      const std::size_t index =
          static_cast<std::size_t>(coordinate) * 256 + requested - 1;
      const Json& observed = records[index];
      const Json expected =
          ExpectedScalarRecord(coordinate, curves->back(), requested);
      discrepancies->expect(
          "scalar[" + std::to_string(coordinate) + "][" +
              std::to_string(requested) + "]",
          expected, observed,
          "independent exact scalar optimum or direct-RNE certificate differs");
    }
  }
}

[[nodiscard]] Json ProductArmJson(const ProductDecision& decision,
                                  const ExactCurve& first,
                                  const ExactCurve& second,
                                  std::uint32_t capacity,
                                  CardinalityDomain domain) {
  const std::uint64_t producer_candidates =
      domain == CardinalityDomain::kAllPositive
          ? capacity
          : static_cast<std::uint64_t>(std::bit_width(capacity));
  return Json(Json::Object{
      {"effective_cardinalities",
       Json(Json::Array{
           Json(static_cast<std::int64_t>(first.at(decision.first)
                                              .effective_cardinality)),
           Json(static_cast<std::int64_t>(second.at(decision.second)
                                              .effective_cardinality))})},
      {"enumerated_candidate_count", Json(std::to_string(producer_candidates))},
      {"exact_fitting_sse", ExactJson(decision.sse)},
      {"invalid_states",
       Json(static_cast<std::int64_t>(capacity - decision.used_states))},
      {"requested_cardinalities",
       Json(Json::Array{Json(static_cast<std::int64_t>(decision.first)),
                        Json(static_cast<std::int64_t>(decision.second))})},
      {"used_states", Json(static_cast<std::int64_t>(decision.used_states))}});
}

struct Allocations {
  std::map<std::pair<std::uint32_t, std::uint32_t>, ProductDecision> arbitrary;
  std::map<std::pair<std::uint32_t, std::uint32_t>, ProductDecision> dyadic;
  std::map<std::uint32_t, GlobalDecision> global;
};

void ReplayAllocations(const Json& summary, const Curves& curves,
                       Allocations* decisions, Discrepancies* discrepancies) {
  if (summary.at("artifact_kind").string() != "a4_allocation_summary" ||
      summary.at("protocol_version").string() != kProtocol ||
      summary.at("schema_version").integer() != 1) {
    throw std::runtime_error("allocation summary identity mismatch");
  }
  const Json::Array& groups = summary.at("group_records").array();
  const Json::Array& globals = summary.at("global_records").array();
  if ((!groups.empty() || !globals.empty()) && curves.size() != 128) {
    throw std::runtime_error("allocation records precede full scalar inventory");
  }
  for (std::size_t index = 0; index < groups.size(); ++index) {
    const std::uint32_t word_bits = index < 64 ? 4 : 8;
    const std::uint32_t group = static_cast<std::uint32_t>(index % 64);
    const std::uint32_t capacity = 1U << word_bits;
    const ExactCurve& first = curves[2 * group];
    const ExactCurve& second = curves[2 * group + 1];
    const ProductDecision arbitrary = ExhaustiveProductDecision(
        first, second, capacity, CardinalityDomain::kAllPositive);
    const ProductDecision dyadic = ExhaustiveProductDecision(
        first, second, capacity, CardinalityDomain::kPowersOfTwo);
    decisions->arbitrary.emplace(std::pair{word_bits, group}, arbitrary);
    decisions->dyadic.emplace(std::pair{word_bits, group}, dyadic);
    const Json expected(Json::Object{
        {"arbitrary_word",
         ProductArmJson(arbitrary, first, second, capacity,
                        CardinalityDomain::kAllPositive)},
        {"capacity", Json(static_cast<std::int64_t>(capacity))},
        {"coordinates",
         Json(Json::Array{Json(static_cast<std::int64_t>(2 * group)),
                          Json(static_cast<std::int64_t>(2 * group + 1))})},
        {"dyadic_word",
         ProductArmJson(dyadic, first, second, capacity,
                        CardinalityDomain::kPowersOfTwo)},
        {"group_id", Json(static_cast<std::int64_t>(group))},
        {"record_type", Json("group_allocation_v2")},
        {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
    discrepancies->expect(
        "allocation.group[" + std::to_string(index) + "]", expected,
        groups[index], "independent product allocation differs");
  }
  for (std::size_t index = 0; index < globals.size(); ++index) {
    const std::uint32_t word_bits = index == 0 ? 4 : 8;
    const std::uint32_t budget = 64U * word_bits;
    GlobalDecision decision = IndependentGlobalAllocation(curves, budget);
    std::vector<std::uint32_t> cardinalities;
    cardinalities.reserve(decision.bit_widths.size());
    for (const std::uint8_t width : decision.bit_widths) {
      cardinalities.push_back(1U << width);
    }
    const Json expected(Json::Object{
        {"bit_widths", U8Array(decision.bit_widths)},
        {"cardinalities", U32Array(cardinalities)},
        {"enumerated_transition_count",
         Json(std::to_string(decision.transition_count))},
        {"exact_fitting_sse", ExactJson(decision.sse)},
        {"record_type", Json("global_allocation_v2")},
        {"total_bit_budget", Json(static_cast<std::int64_t>(budget))},
        {"used_bits", Json(static_cast<std::int64_t>(decision.used_bits))},
        {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
    discrepancies->expect(
        "allocation.global[" + std::to_string(index) + "]", expected,
        globals[index], "independent global allocation differs");
    decisions->global.emplace(word_bits, std::move(decision));
  }
}

struct Point {
  float x{0};
  float y{0};
  std::uint32_t vector_id{0};
  std::string selection_digest;
};

struct Center {
  double x{0};
  double y{0};
};

struct Assignment {
  std::vector<std::uint16_t> labels;
  double sse{0};
  std::uint64_t comparisons{0};
  std::uint64_t ties{0};
};

struct Step {
  std::uint32_t iteration{0};
  double prior_sse{0};
  double candidate_sse{0};
  std::vector<std::uint16_t> before;
  std::vector<std::uint16_t> after;
  std::vector<std::uint32_t> empty;
  std::vector<Center> centers_after;
};

struct Start {
  std::uint32_t id{0};
  std::vector<std::uint32_t> initialization_ids;
  std::vector<Center> initial_centers;
  std::vector<Step> steps;
  bool converged{false};
  std::vector<Center> final_centers;
  std::vector<std::uint16_t> final_assignments;
  double final_sse{0};
  std::uint64_t comparisons{0};
  std::uint64_t assignment_ties{0};
  std::uint64_t farthest_ties{0};
};

struct BlockModel {
  std::uint32_t word_bits{0};
  std::uint32_t group{0};
  std::uint32_t capacity{0};
  std::vector<Point> points;
  std::vector<Center> prefill;
  double prefill_sse{0};
  std::vector<Start> starts;
  std::uint32_t selected{0};
};

[[nodiscard]] double Distance(const Point& point, const Center& center) {
  const double dx = static_cast<double>(point.x) - center.x;
  const double x2 = dx * dx;
  const double dy = static_cast<double>(point.y) - center.y;
  const double y2 = dy * dy;
  const double result = x2 + y2;
  if (!std::isfinite(result) || result < 0) {
    throw std::runtime_error("nonfinite independent block distance");
  }
  return result;
}

[[nodiscard]] Assignment Assign(const std::vector<Point>& points,
                                const std::vector<Center>& centers) {
  if (centers.empty() || centers.size() > 256) {
    throw std::runtime_error("invalid independent center inventory");
  }
  Assignment result;
  result.labels.reserve(points.size());
  for (const Point& point : points) {
    std::uint16_t best_id = 0;
    double best = Distance(point, centers[0]);
    ++result.comparisons;
    for (std::uint32_t center = 1; center < centers.size(); ++center) {
      const double candidate = Distance(point, centers[center]);
      ++result.comparisons;
      if (candidate < best) {
        best = candidate;
        best_id = static_cast<std::uint16_t>(center);
      } else if (candidate == best) {
        ++result.ties;  // Lower existing label wins.
      }
    }
    result.labels.push_back(best_id);
    result.sse += best;
    if (!std::isfinite(result.sse)) {
      throw std::runtime_error("nonfinite independent block SSE");
    }
  }
  return result;
}

[[nodiscard]] std::vector<Point> OrderedGroupPoints(
    const InputPanel& panel, std::uint32_t group) {
  std::vector<Point> result;
  result.reserve(kRows);
  for (std::uint32_t row = 0; row < kRows; ++row) {
    const std::string key = std::string(kHashDomain) + "|" +
                            std::string(kDataset) + "|0|" +
                            std::to_string(row);
    result.push_back(Point{
        std::bit_cast<float>(panel.row_major_bits[
            static_cast<std::size_t>(row) * kDimensions + 2 * group]),
        std::bit_cast<float>(panel.row_major_bits[
            static_cast<std::size_t>(row) * kDimensions + 2 * group + 1]),
        row, Sha256(key)});
  }
  std::sort(result.begin(), result.end(), [](const Point& lhs, const Point& rhs) {
    if (lhs.selection_digest != rhs.selection_digest) {
      return lhs.selection_digest < rhs.selection_digest;
    }
    return lhs.vector_id < rhs.vector_id;
  });
  return result;
}

[[nodiscard]] std::vector<Center> CartesianCenters(
    const ExactSolution& first, const ExactSolution& second) {
  std::vector<Center> result;
  result.reserve(first.intervals.size() * second.intervals.size());
  for (const ExactInterval& y : second.intervals) {
    for (const ExactInterval& x : first.intervals) {
      result.push_back(Center{
          std::bit_cast<double>(DirectRoundBinary64(x.mean)),
          std::bit_cast<double>(DirectRoundBinary64(y.mean))});
    }
  }
  return result;
}

[[nodiscard]] std::size_t FarthestRow(
    const std::vector<Point>& points, const std::vector<Center>& centers,
    const std::set<std::uint32_t>& excluded, std::uint64_t* comparisons,
    std::uint64_t* ties) {
  bool found = false;
  std::size_t best_row = 0;
  double best_distance = 0;
  for (std::size_t row = 0; row < points.size(); ++row) {
    if (excluded.contains(points[row].vector_id)) continue;
    double nearest = Distance(points[row], centers[0]);
    ++*comparisons;
    for (std::size_t center = 1; center < centers.size(); ++center) {
      const double candidate = Distance(points[row], centers[center]);
      ++*comparisons;
      if (candidate < nearest) nearest = candidate;
    }
    if (found && nearest == best_distance) ++*ties;
    const bool lower_key =
        found && nearest == best_distance &&
        (points[row].vector_id < points[best_row].vector_id ||
         (points[row].vector_id == points[best_row].vector_id &&
          points[row].selection_digest < points[best_row].selection_digest));
    if (!found || nearest > best_distance || lower_key) {
      found = true;
      best_row = row;
      best_distance = nearest;
    }
  }
  if (!found) throw std::runtime_error("farthest fill exhausted rows");
  return best_row;
}

void FillCenters(const std::vector<Point>& points, std::uint32_t capacity,
                 std::vector<Center>* centers,
                 std::vector<std::uint32_t>* selected,
                 std::uint64_t* comparisons, std::uint64_t* ties) {
  std::set<std::uint32_t> excluded(selected->begin(), selected->end());
  while (centers->size() < capacity) {
    const std::size_t row =
        FarthestRow(points, *centers, excluded, comparisons, ties);
    centers->push_back(Center{static_cast<double>(points[row].x),
                              static_cast<double>(points[row].y)});
    selected->push_back(points[row].vector_id);
    excluded.insert(points[row].vector_id);
  }
}

[[nodiscard]] Start RunLloyd(const std::vector<Point>& points,
                             std::vector<Center> centers, Start trace) {
  trace.initial_centers = centers;
  Assignment accepted = Assign(points, centers);
  trace.comparisons += accepted.comparisons;
  trace.assignment_ties += accepted.ties;
  for (std::uint32_t iteration = 1; iteration <= 300; ++iteration) {
    const Assignment before = Assign(points, centers);
    trace.comparisons += before.comparisons;
    trace.assignment_ties += before.ties;
    std::vector<double> sums_x(centers.size(), 0);
    std::vector<double> sums_y(centers.size(), 0);
    std::vector<std::uint32_t> counts(centers.size(), 0);
    for (std::size_t row = 0; row < points.size(); ++row) {
      const std::uint16_t label = before.labels[row];
      sums_x[label] += static_cast<double>(points[row].x);
      sums_y[label] += static_cast<double>(points[row].y);
      ++counts[label];
    }
    std::vector<Center> candidate = centers;
    std::vector<std::uint32_t> empty;
    for (std::uint32_t center = 0; center < centers.size(); ++center) {
      if (counts[center] == 0) {
        empty.push_back(center);  // Retain the prior center.
      } else {
        candidate[center].x = sums_x[center] / counts[center];
        candidate[center].y = sums_y[center] / counts[center];
      }
    }
    Assignment after = Assign(points, candidate);
    trace.comparisons += after.comparisons;
    trace.assignment_ties += after.ties;
    if (after.sse > before.sse) break;
    std::uint32_t changed = 0;
    for (std::size_t row = 0; row < before.labels.size(); ++row) {
      changed += before.labels[row] != after.labels[row] ? 1U : 0U;
    }
    trace.steps.push_back(Step{iteration, before.sse, after.sse,
                               before.labels, after.labels, std::move(empty),
                               candidate});
    centers = std::move(candidate);
    accepted = std::move(after);
    if (changed == 0) {
      trace.converged = true;
      break;
    }
  }
  trace.final_centers = std::move(centers);
  trace.final_assignments = std::move(accepted.labels);
  trace.final_sse = accepted.sse;
  return trace;
}

[[nodiscard]] BlockModel TrainIndependentBlock(
    const InputPanel& panel, const Curves& curves,
    const ProductDecision& arbitrary, std::uint32_t word_bits,
    std::uint32_t group) {
  BlockModel model;
  model.word_bits = word_bits;
  model.group = group;
  model.capacity = 1U << word_bits;
  model.points = OrderedGroupPoints(panel, group);
  model.prefill = CartesianCenters(curves[2 * group].at(arbitrary.first),
                                   curves[2 * group + 1].at(arbitrary.second));
  model.prefill_sse = Assign(model.points, model.prefill).sse;

  Start start0;
  start0.id = 0;
  std::vector<Center> centers0 = model.prefill;
  FillCenters(model.points, model.capacity, &centers0,
              &start0.initialization_ids, &start0.comparisons,
              &start0.farthest_ties);
  model.starts.push_back(RunLloyd(model.points, std::move(centers0),
                                  std::move(start0)));
  for (std::uint32_t start_id = 1; start_id < 8; ++start_id) {
    bool found = false;
    std::size_t first_row = 0;
    std::string best_digest;
    for (std::size_t row = 0; row < model.points.size(); ++row) {
      const Point& point = model.points[row];
      const std::string key =
          std::string(kHashDomain) + "|" + std::string(kDataset) + "|" +
          std::to_string(model.capacity) + "|" + std::to_string(group) +
          "|" + std::to_string(start_id) + "|0|" +
          std::to_string(point.vector_id);
      const std::string digest = Sha256(key);
      if (!found || digest < best_digest ||
          (digest == best_digest &&
           point.vector_id < model.points[first_row].vector_id)) {
        found = true;
        first_row = row;
        best_digest = digest;
      }
    }
    Start start;
    start.id = start_id;
    start.initialization_ids.push_back(model.points[first_row].vector_id);
    std::vector<Center> centers{
        Center{static_cast<double>(model.points[first_row].x),
               static_cast<double>(model.points[first_row].y)}};
    FillCenters(model.points, model.capacity, &centers,
                &start.initialization_ids, &start.comparisons,
                &start.farthest_ties);
    model.starts.push_back(
        RunLloyd(model.points, std::move(centers), std::move(start)));
  }
  model.selected = 0;
  for (std::uint32_t start = 1; start < model.starts.size(); ++start) {
    if (model.starts[start].final_sse <
        model.starts[model.selected].final_sse) {
      model.selected = start;
    }
  }
  return model;
}

[[nodiscard]] Json Center64Json(const std::vector<Center>& centers) {
  Json::Array result;
  result.reserve(centers.size());
  for (const Center& center : centers) {
    result.emplace_back(Json::Array{
        Json(Hex64(std::bit_cast<std::uint64_t>(center.x))),
        Json(Hex64(std::bit_cast<std::uint64_t>(center.y)))});
  }
  return Json(std::move(result));
}

[[nodiscard]] Json Center32Json(const std::vector<Center>& centers) {
  Json::Array result;
  result.reserve(centers.size());
  for (const Center& center : centers) {
    float x = static_cast<float>(center.x);
    float y = static_cast<float>(center.y);
    std::uint32_t xb = std::bit_cast<std::uint32_t>(x);
    std::uint32_t yb = std::bit_cast<std::uint32_t>(y);
    if ((xb & 0x7fffffffU) == 0) xb = 0;
    if ((yb & 0x7fffffffU) == 0) yb = 0;
    result.emplace_back(Json::Array{Json(Hex32(xb)), Json(Hex32(yb))});
  }
  return Json(std::move(result));
}

[[nodiscard]] std::string LabelHash(
    const std::vector<std::uint16_t>& labels) {
  std::string bytes;
  bytes.reserve(labels.size() * 2);
  for (const std::uint16_t label : labels) {
    bytes.push_back(static_cast<char>(label & 0xffU));
    bytes.push_back(static_cast<char>(label >> 8U));
  }
  return Sha256(bytes);
}

[[nodiscard]] Json LabelArray(const std::vector<std::uint16_t>& labels) {
  Json::Array result;
  result.reserve(labels.size());
  for (const std::uint16_t label : labels) {
    result.emplace_back(static_cast<std::int64_t>(label));
  }
  return Json(std::move(result));
}

[[nodiscard]] std::string RowOrderHash(const std::vector<Point>& points) {
  std::string bytes;
  bytes.reserve(points.size() * 4);
  for (const Point& point : points) {
    for (unsigned int shift = 0; shift < 32; shift += 8) {
      bytes.push_back(static_cast<char>(point.vector_id >> shift));
    }
  }
  return Sha256(bytes);
}

[[nodiscard]] Json ExpectedBlockStart(const BlockModel& model,
                                      const Start& start) {
  Json::Array steps;
  steps.reserve(start.steps.size());
  for (const Step& step : start.steps) {
    std::uint32_t changed = 0;
    for (std::size_t index = 0; index < step.before.size(); ++index) {
      changed += step.before[index] != step.after[index] ? 1U : 0U;
    }
    const Json center_json = Center64Json(step.centers_after);
    steps.emplace_back(Json::Object{
        {"accepted", Json(true)},
        {"assignments_after_sha256", Json(LabelHash(step.after))},
        {"assignments_before_sha256", Json(LabelHash(step.before))},
        {"candidate_sse_bits",
         Json(Hex64(std::bit_cast<std::uint64_t>(step.candidate_sse)))},
        {"centers_after_binary64_bits_sha256",
         Json(Sha256(DumpJson(center_json)))},
        {"changed_assignment_count", Json(static_cast<std::int64_t>(changed))},
        {"empty_center_ids", U32Array(step.empty)},
        {"iteration", Json(static_cast<std::int64_t>(step.iteration))},
        {"prior_sse_bits",
         Json(Hex64(std::bit_cast<std::uint64_t>(step.prior_sse)))}});
  }
  const Json final32 = Center32Json(start.final_centers);
  std::set<std::pair<std::uint32_t, std::uint32_t>> distinct;
  for (const Json& item : final32.array()) {
    distinct.emplace(
        static_cast<std::uint32_t>(ParseHex(item.array()[0].string(), 8, "x")),
        static_cast<std::uint32_t>(ParseHex(item.array()[1].string(), 8, "y")));
  }
  Json prefill_centers(nullptr);
  Json prefill_hash(nullptr);
  Json prefill_sse(nullptr);
  if (start.id == 0) {
    prefill_centers = Center64Json(model.prefill);
    prefill_hash = Json(Sha256(DumpJson(prefill_centers)));
    prefill_sse =
        Json(Hex64(std::bit_cast<std::uint64_t>(model.prefill_sse)));
  }
  return Json(Json::Object{
      {"accepted_update_count",
       Json(static_cast<std::int64_t>(start.steps.size()))},
      {"assignment_tie_count", Json(std::to_string(start.assignment_ties))},
      {"capacity", Json(static_cast<std::int64_t>(model.capacity))},
      {"cartesian_dominance_pass", Json(start.final_sse <= model.prefill_sse)},
      {"converged", Json(start.converged)},
      {"direct_replay_match", Json(true)},
      {"distance_comparison_count", Json(std::to_string(start.comparisons))},
      {"farthest_tie_count", Json(std::to_string(start.farthest_ties))},
      {"final_assignments", LabelArray(start.final_assignments)},
      {"final_assignments_sha256", Json(LabelHash(start.final_assignments))},
      {"final_centers_binary32_bits", final32},
      {"final_centers_binary64_bits", Center64Json(start.final_centers)},
      {"final_sse_bits",
       Json(Hex64(std::bit_cast<std::uint64_t>(start.final_sse)))},
      {"group_id", Json(static_cast<std::int64_t>(model.group))},
      {"initial_centers_binary64_bits", Center64Json(start.initial_centers)},
      {"initialization_kind",
       Json(start.id == 0 ? "cartesian_fill" : "hashed_farthest_first")},
      {"initialization_vector_ids", U32Array(start.initialization_ids)},
      {"iteration_count", Json(static_cast<std::int64_t>(start.steps.size()))},
      {"prefill_cartesian_centers_binary64_bits", std::move(prefill_centers)},
      {"prefill_cartesian_centers_binary64_bits_sha256", std::move(prefill_hash)},
      {"prefill_cartesian_sse_bits", std::move(prefill_sse)},
      {"record_type", Json("block_start_v2")},
      {"selected_best_start", Json(start.id == model.selected)},
      {"serialized_distinct_center_count",
       Json(static_cast<std::int64_t>(distinct.size()))},
      {"start_id", Json(static_cast<std::int64_t>(start.id))},
      {"steps", Json(std::move(steps))},
      {"word_bits", Json(static_cast<std::int64_t>(model.word_bits))}});
}

void ReplayBlocks(const std::vector<Json>& records, const InputPanel& panel,
                  const Curves& curves, const Allocations& allocations,
                  std::vector<BlockModel>* models,
                  Discrepancies* discrepancies) {
  if ((records.size() % 9U) != 0 || records.size() > 128U * 9U) {
    throw std::runtime_error("block JSONL is not a complete-group prefix");
  }
  const std::size_t group_units = records.size() / 9U;
  models->reserve(group_units);
  for (std::size_t unit = 0; unit < group_units; ++unit) {
    const std::uint32_t word_bits = unit < 64 ? 4 : 8;
    const std::uint32_t group = static_cast<std::uint32_t>(unit % 64);
    const auto allocation = allocations.arbitrary.find({word_bits, group});
    if (allocation == allocations.arbitrary.end()) {
      throw std::runtime_error("block prefix lacks arbitrary allocation");
    }
    BlockModel model = TrainIndependentBlock(panel, curves,
                                             allocation->second, word_bits,
                                             group);
    const Json metadata(Json::Object{
        {"arbitrary_cardinalities",
         Json(Json::Array{
             Json(static_cast<std::int64_t>(allocation->second.first)),
             Json(static_cast<std::int64_t>(allocation->second.second))})},
        {"arbitrary_used_states",
         Json(static_cast<std::int64_t>(allocation->second.used_states))},
        {"capacity", Json(static_cast<std::int64_t>(model.capacity))},
        {"coordinates",
         Json(Json::Array{Json(static_cast<std::int64_t>(2 * group)),
                          Json(static_cast<std::int64_t>(2 * group + 1))})},
        {"fit_row_count", Json(static_cast<std::int64_t>(kRows))},
        {"group_id", Json(static_cast<std::int64_t>(group))},
        {"record_type", Json("block_metadata_v2")},
        {"row_order_vector_ids_sha256", Json(RowOrderHash(model.points))},
        {"selected_start_id", Json(static_cast<std::int64_t>(model.selected))},
        {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
    discrepancies->expect(
        "block[" + std::to_string(unit) + "].metadata", metadata,
        records[9 * unit], "independent block metadata/winner differs");
    for (std::uint32_t start = 0; start < 8; ++start) {
      const Json expected = ExpectedBlockStart(model, model.starts[start]);
      discrepancies->expect(
          "block[" + std::to_string(unit) + "].start[" +
              std::to_string(start) + "]",
          expected, records[9 * unit + start + 1],
          "independent eight-start trajectory differs");
    }
    models->push_back(std::move(model));
  }
}

[[nodiscard]] double Promote(std::uint32_t bits) {
  const float value = std::bit_cast<float>(bits);
  if (!std::isfinite(value)) throw std::runtime_error("nonfinite encoding input");
  return static_cast<double>(value);
}

[[nodiscard]] std::uint32_t AssignScalarBits(
    std::uint32_t value, const std::vector<std::uint32_t>& centroids,
    std::uint64_t* comparisons) {
  if (centroids.empty()) throw std::runtime_error("empty scalar encoding model");
  std::uint32_t best = 0;
  double best_distance = std::numeric_limits<double>::infinity();
  for (std::uint32_t label = 0; label < centroids.size(); ++label) {
    const double difference = Promote(value) - Promote(centroids[label]);
    const double distance = difference * difference;
    ++*comparisons;
    if (distance < best_distance) {
      best = label;
      best_distance = distance;
    }
  }
  return best;
}

[[nodiscard]] std::uint32_t AssignBlockBits(
    std::uint32_t x_bits, std::uint32_t y_bits,
    const std::vector<Center>& centers, std::uint64_t* comparisons) {
  std::uint32_t best = 0;
  double best_distance = std::numeric_limits<double>::infinity();
  for (std::uint32_t label = 0; label < centers.size(); ++label) {
    const float cx = static_cast<float>(centers[label].x);
    const float cy = static_cast<float>(centers[label].y);
    const double dx = Promote(x_bits) - static_cast<double>(cx);
    const double x2 = dx * dx;
    const double dy = Promote(y_bits) - static_cast<double>(cy);
    const double distance = x2 + dy * dy;
    ++*comparisons;
    if (distance < best_distance) {
      best = label;
      best_distance = distance;
    }
  }
  return best;
}

[[nodiscard]] std::vector<std::uint32_t> Centroids32(
    const ExactSolution& solution) {
  std::vector<std::uint32_t> result;
  result.reserve(solution.intervals.size());
  for (const ExactInterval& interval : solution.intervals) {
    result.push_back(DirectRoundBinary32(interval.mean));
  }
  return result;
}

[[nodiscard]] std::string PackMatchedLabels(
    const std::vector<std::uint32_t>& labels, std::uint32_t word_bits) {
  if (labels.size() != 64 || (word_bits != 4 && word_bits != 8)) {
    throw std::runtime_error("invalid matched packing shape");
  }
  std::string result(word_bits == 4 ? 32 : 64, '\0');
  for (std::size_t group = 0; group < labels.size(); ++group) {
    if (labels[group] >= (1U << word_bits)) {
      throw std::runtime_error("matched label exceeds paid word");
    }
    if (word_bits == 4) {
      const unsigned int shift = (group % 2 == 0) ? 0 : 4;
      result[group / 2] = static_cast<char>(
          static_cast<unsigned char>(result[group / 2]) |
          static_cast<unsigned char>(labels[group] << shift));
    } else {
      result[group] = static_cast<char>(labels[group]);
    }
  }
  // Independent inverse, including the B4 low-nibble-first rule.
  for (std::size_t group = 0; group < labels.size(); ++group) {
    const std::uint32_t replay =
        word_bits == 4
            ? ((static_cast<unsigned char>(result[group / 2]) >>
                ((group % 2 == 0) ? 0U : 4U)) &
               15U)
            : static_cast<unsigned char>(result[group]);
    if (replay != labels[group]) {
      throw std::logic_error("independent matched roundtrip failed");
    }
  }
  return result;
}

[[nodiscard]] std::string PackGlobalLabels(
    const std::vector<std::uint32_t>& labels,
    const std::vector<std::uint8_t>& widths, std::uint32_t paid_bytes) {
  if (labels.size() != 128 || widths.size() != 128 ||
      (paid_bytes != 32 && paid_bytes != 64)) {
    throw std::runtime_error("invalid global packing shape");
  }
  std::string result(paid_bytes, '\0');
  std::uint32_t offset = 0;
  for (std::size_t coordinate = 0; coordinate < labels.size(); ++coordinate) {
    const std::uint8_t width = widths[coordinate];
    if (width > 8 || labels[coordinate] >= (1U << width) ||
        offset + width > paid_bytes * 8U) {
      throw std::runtime_error("invalid global label/width");
    }
    for (std::uint32_t bit = 0; bit < width; ++bit) {
      if (((labels[coordinate] >> bit) & 1U) != 0) {
        const std::uint32_t stream = offset + bit;
        result[stream / 8U] = static_cast<char>(
            static_cast<unsigned char>(result[stream / 8U]) |
            static_cast<unsigned char>(1U << (stream % 8U)));
      }
    }
    offset += width;
  }
  std::uint32_t replay_offset = 0;
  for (std::size_t coordinate = 0; coordinate < labels.size(); ++coordinate) {
    std::uint32_t replay = 0;
    for (std::uint32_t bit = 0; bit < widths[coordinate]; ++bit) {
      const std::uint32_t stream = replay_offset + bit;
      replay |= ((static_cast<unsigned char>(result[stream / 8U]) >>
                  (stream % 8U)) &
                 1U)
                << bit;
    }
    if (replay != labels[coordinate]) {
      throw std::logic_error("independent global roundtrip failed");
    }
    replay_offset += widths[coordinate];
  }
  for (std::uint32_t bit = replay_offset; bit < paid_bytes * 8U; ++bit) {
    if (((static_cast<unsigned char>(result[bit / 8U]) >> (bit % 8U)) & 1U) !=
        0) {
      throw std::logic_error("independent global padding is nonzero");
    }
  }
  return result;
}

[[nodiscard]] std::string BytesHex(std::string_view bytes) {
  constexpr char kHex[] = "0123456789abcdef";
  std::string result;
  result.reserve(bytes.size() * 2);
  for (const unsigned char byte : bytes) {
    result.push_back(kHex[byte >> 4U]);
    result.push_back(kHex[byte & 15U]);
  }
  return result;
}

[[nodiscard]] const BlockModel& FindBlock(
    const std::vector<BlockModel>& blocks, std::uint32_t word_bits,
    std::uint32_t group) {
  for (const BlockModel& block : blocks) {
    if (block.word_bits == word_bits && block.group == group) return block;
  }
  throw std::runtime_error("encoding lacks independent block model");
}

struct EncodedArm {
  std::string payload;
  std::uint64_t comparisons{0};
};

[[nodiscard]] EncodedArm EncodeArm(
    const InputPanel& panel, const Curves& curves,
    const Allocations& allocations, const std::vector<BlockModel>& blocks,
    std::uint32_t word_bits, std::uint32_t arm_index) {
  EncodedArm result;
  const std::uint32_t paid_bytes = word_bits == 4 ? 32 : 64;
  result.payload.reserve(static_cast<std::size_t>(kRows) * paid_bytes);
  for (std::uint32_t row = 0; row < kRows; ++row) {
    if (arm_index <= 1) {
      std::vector<std::uint32_t> labels;
      labels.reserve(64);
      for (std::uint32_t group = 0; group < 64; ++group) {
        const auto& inventory =
            arm_index == 0 ? allocations.dyadic : allocations.arbitrary;
        const ProductDecision& decision = inventory.at({word_bits, group});
        const std::vector<std::uint32_t> first =
            Centroids32(curves[2 * group].at(decision.first));
        const std::vector<std::uint32_t> second =
            Centroids32(curves[2 * group + 1].at(decision.second));
        const std::uint32_t a = AssignScalarBits(
            panel.row_major_bits[static_cast<std::size_t>(row) * 128 +
                                 2 * group],
            first, &result.comparisons);
        const std::uint32_t b = AssignScalarBits(
            panel.row_major_bits[static_cast<std::size_t>(row) * 128 +
                                 2 * group + 1],
            second, &result.comparisons);
        const std::uint32_t address = a + decision.first * b;
        if (address >= decision.used_states) {
          throw std::logic_error("independent mixed-radix address invalid");
        }
        labels.push_back(address);
      }
      result.payload += PackMatchedLabels(labels, word_bits);
    } else if (arm_index == 2) {
      std::vector<std::uint32_t> labels;
      labels.reserve(64);
      for (std::uint32_t group = 0; group < 64; ++group) {
        const BlockModel& block = FindBlock(blocks, word_bits, group);
        const Start& selected = block.starts[block.selected];
        labels.push_back(AssignBlockBits(
            panel.row_major_bits[static_cast<std::size_t>(row) * 128 +
                                 2 * group],
            panel.row_major_bits[static_cast<std::size_t>(row) * 128 +
                                 2 * group + 1],
            selected.final_centers, &result.comparisons));
      }
      result.payload += PackMatchedLabels(labels, word_bits);
    } else {
      const GlobalDecision& global = allocations.global.at(word_bits);
      std::vector<std::uint32_t> labels;
      labels.reserve(128);
      for (std::uint32_t coordinate = 0; coordinate < 128; ++coordinate) {
        const std::uint32_t cardinality =
            1U << global.bit_widths[coordinate];
        labels.push_back(AssignScalarBits(
            panel.row_major_bits[static_cast<std::size_t>(row) * 128 +
                                 coordinate],
            Centroids32(curves[coordinate].at(cardinality)),
            &result.comparisons));
      }
      result.payload +=
          PackGlobalLabels(labels, global.bit_widths, paid_bytes);
    }
  }
  return result;
}

[[nodiscard]] Json CentroidArrayJson(const ExactSolution& solution) {
  Json::Array result;
  for (const ExactInterval& interval : solution.intervals) {
    result.emplace_back(Hex32(DirectRoundBinary32(interval.mean)));
  }
  return Json(std::move(result));
}

[[nodiscard]] Json ProductModelJson(const ProductDecision& decision,
                                    const ExactCurve& first,
                                    const ExactCurve& second,
                                    std::uint32_t capacity) {
  return Json(Json::Object{
      {"centroids_binary32_bits",
       Json(Json::Array{CentroidArrayJson(first.at(decision.first)),
                        CentroidArrayJson(second.at(decision.second))})},
      {"effective_cardinalities",
       Json(Json::Array{
           Json(static_cast<std::int64_t>(
               first.at(decision.first).effective_cardinality)),
           Json(static_cast<std::int64_t>(
               second.at(decision.second).effective_cardinality))})},
      {"invalid_states",
       Json(static_cast<std::int64_t>(capacity - decision.used_states))},
      {"requested_cardinalities",
       Json(Json::Array{Json(static_cast<std::int64_t>(decision.first)),
                        Json(static_cast<std::int64_t>(decision.second))})},
      {"used_states", Json(static_cast<std::int64_t>(decision.used_states))}});
}

[[nodiscard]] Json BuildModelsJson(const Curves& curves,
                                   const Allocations& allocations,
                                   const std::vector<BlockModel>& blocks) {
  Json::Array rates;
  for (const std::uint32_t word_bits : {4U, 8U}) {
    const std::uint32_t capacity = 1U << word_bits;
    Json::Array groups;
    for (std::uint32_t group = 0; group < 64; ++group) {
      const ProductDecision& arbitrary =
          allocations.arbitrary.at({word_bits, group});
      const ProductDecision& dyadic =
          allocations.dyadic.at({word_bits, group});
      const BlockModel& block = FindBlock(blocks, word_bits, group);
      groups.emplace_back(Json::Object{
          {"arbitrary_word",
           ProductModelJson(arbitrary, curves[2 * group],
                            curves[2 * group + 1], capacity)},
          {"coordinates",
           Json(Json::Array{Json(static_cast<std::int64_t>(2 * group)),
                            Json(static_cast<std::int64_t>(2 * group + 1))})},
          {"dyadic_word",
           ProductModelJson(dyadic, curves[2 * group],
                            curves[2 * group + 1], capacity)},
          {"group_id", Json(static_cast<std::int64_t>(group))},
          {"trained_block_vq",
           Json(Json::Object{
               {"center_count", Json(static_cast<std::int64_t>(capacity))},
               {"centers_binary32_bits",
                Center32Json(block.starts[block.selected].final_centers)},
               {"selected_start_id",
                Json(static_cast<std::int64_t>(block.selected))}})}});
    }
    const GlobalDecision& global = allocations.global.at(word_bits);
    std::vector<std::uint32_t> cardinalities;
    Json::Array centroids;
    for (std::uint32_t coordinate = 0; coordinate < 128; ++coordinate) {
      const std::uint32_t cardinality = 1U << global.bit_widths[coordinate];
      cardinalities.push_back(cardinality);
      centroids.push_back(CentroidArrayJson(curves[coordinate].at(cardinality)));
    }
    rates.emplace_back(Json::Object{
        {"capacity", Json(static_cast<std::int64_t>(capacity))},
        {"global_dyadic_pack_cap8",
         Json(Json::Object{
             {"bit_widths", U8Array(global.bit_widths)},
             {"cardinalities", U32Array(cardinalities)},
             {"centroids_binary32_bits", Json(std::move(centroids))}})},
        {"groups", Json(std::move(groups))},
        {"payload_bytes", Json(static_cast<std::int64_t>(word_bits == 4 ? 32 : 64))},
        {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
  }
  return Json(Json::Object{
      {"artifact_kind", Json("a4_comparative_models")},
      {"protocol_version", Json(std::string(kProtocol))},
      {"rates", Json(std::move(rates))},
      {"schema_version", Json(std::int64_t{1})}});
}

struct Encodings {
  std::map<std::pair<std::uint32_t, std::uint32_t>, EncodedArm> arms;
};

void ReplayEncodings(const Json& summary, const InputPanel& panel,
                     const Curves& curves, const Allocations& allocations,
                     const std::vector<BlockModel>& blocks,
                     Encodings* encodings, Discrepancies* discrepancies) {
  if (summary.at("artifact_kind").string() != "a4_encoding_summary" ||
      summary.at("protocol_version").string() != kProtocol ||
      summary.at("schema_version").integer() != 1) {
    throw std::runtime_error("encoding summary identity mismatch");
  }
  const Json::Array& records = summary.at("records").array();
  for (std::size_t index = 0; index < records.size(); ++index) {
    const std::uint32_t word_bits = index < 4 ? 4 : 8;
    const std::uint32_t arm = static_cast<std::uint32_t>(index % 4);
    EncodedArm encoded = EncodeArm(panel, curves, allocations, blocks,
                                   word_bits, arm);
    const std::uint32_t paid = word_bits == 4 ? 32 : 64;
    const std::uint64_t length = static_cast<std::uint64_t>(kRows) * paid;
    const Json expected(Json::Object{
        {"alignment_bytes", Json(std::int64_t{1})},
        {"arm", Json(std::string(kArms[arm]))},
        {"capacity", Json(static_cast<std::int64_t>(1U << word_bits))},
        {"code_file_path", Json(word_bits == 4 ? "codes_b04.bin" : "codes_b08.bin")},
        {"distance_comparison_count", Json(std::to_string(encoded.comparisons))},
        {"file_byte_length", Json(static_cast<std::int64_t>(length))},
        {"file_byte_offset", Json(static_cast<std::int64_t>(arm * length))},
        {"labels_per_vector", Json(static_cast<std::int64_t>(arm == 3 ? 128 : 64))},
        {"output_bytes", Json(static_cast<std::int64_t>(length))},
        {"pack_operation_count", Json(std::to_string(kRows))},
        {"payload_bytes_per_vector", Json(static_cast<std::int64_t>(paid))},
        {"payload_hex", Json(BytesHex(encoded.payload))},
        {"payload_sha256", Json(Sha256(encoded.payload))},
        {"record_type", Json("encoding_arm_summary_v2")},
        {"roundtrip_match", Json(true)},
        {"roundtrip_mismatch_count", Json(std::int64_t{0})},
        {"roundtrip_vector_count", Json(static_cast<std::int64_t>(kRows))},
        {"unpack_operation_count", Json(std::to_string(kRows))},
        {"vector_count", Json(static_cast<std::int64_t>(kRows))},
        {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
    discrepancies->expect(
        "encoding[" + std::to_string(index) + "]", expected, records[index],
        "independent labeling/packing payload differs");
    encodings->arms.emplace(std::pair{word_bits, arm}, std::move(encoded));
  }
}

[[nodiscard]] Json FileIdentity(std::string path, std::uint32_t word_bits,
                                std::string_view payload) {
  const std::uint32_t paid = word_bits == 4 ? 32 : 64;
  return Json(Json::Object{
      {"arm_order",
       Json(Json::Array{Json(std::string(kArms[0])), Json(std::string(kArms[1])),
                        Json(std::string(kArms[2])), Json(std::string(kArms[3]))})},
      {"layout", Json("arm-major_then_vector-major")},
      {"path", Json(std::move(path))},
      {"payload_bytes", Json(static_cast<std::int64_t>(paid))},
      {"sha256", Json(Sha256(payload))},
      {"size_bytes", Json(static_cast<std::int64_t>(payload.size()))},
      {"vector_count", Json(static_cast<std::int64_t>(kRows))},
      {"word_bits", Json(static_cast<std::int64_t>(word_bits))}});
}

void ReplayBundle(const Json& request, const InputPanel& panel,
                  const Curves& curves, const Allocations& allocations,
                  const std::vector<BlockModel>& blocks,
                  const Encodings& encodings, Discrepancies* discrepancies) {
  const Json models = BuildModelsJson(curves, allocations, blocks);
  const std::string models_bytes = DumpJson(models) + "\n";
  const std::string observed_models =
      ReadBoundArtifact(request, "bundle/models.json", 64U << 20U);
  if (models_bytes != observed_models) {
    const Json observed = ParseCanonicalDocument(observed_models, "bundle models");
    discrepancies->expect("bundle/models.json", models, observed,
                          "independent model bundle differs");
  }
  std::map<std::uint32_t, std::string> code_files;
  for (const std::uint32_t word_bits : {4U, 8U}) {
    std::string expected;
    for (std::uint32_t arm = 0; arm < 4; ++arm) {
      expected += encodings.arms.at({word_bits, arm}).payload;
    }
    const std::string filename =
        word_bits == 4 ? "bundle/codes_b04.bin" : "bundle/codes_b08.bin";
    const std::string observed =
        ReadBoundArtifact(request, filename, 4U << 20U);
    if (expected != observed) {
      Json expected_hash(Sha256(expected));
      Json observed_hash(Sha256(observed));
      discrepancies->add(filename, "independent code-file bytes differ",
                          &expected_hash, &observed_hash,
                          "BUNDLE_REPLAY_MISMATCH");
    }
    code_files.emplace(word_bits, std::move(expected));
  }
  const Json expected_manifest(Json::Object{
      {"arm_order",
       Json(Json::Array{Json(std::string(kArms[0])), Json(std::string(kArms[1])),
                        Json(std::string(kArms[2])), Json(std::string(kArms[3]))})},
      {"artifact_kind", Json("a4_comparative_bundle_manifest")},
      {"code_files",
       Json(Json::Array{
           FileIdentity("codes_b04.bin", 4, code_files.at(4)),
           FileIdentity("codes_b08.bin", 8, code_files.at(8))})},
      {"input",
       Json(Json::Object{
           {"dtype", Json("little-endian binary32")},
           {"order", Json("C")},
           {"raw_sha256", Json(panel.raw_sha256)},
           {"shape",
            Json(Json::Array{Json(static_cast<std::int64_t>(kRows)),
                             Json(static_cast<std::int64_t>(kDimensions))})}})},
      {"models",
       Json(Json::Object{
           {"path", Json("models.json")},
           {"schema_version", Json(std::int64_t{1})},
           {"sha256", Json(Sha256(models_bytes))},
           {"size_bytes", Json(static_cast<std::int64_t>(models_bytes.size()))}})},
      {"protocol_version", Json(std::string(kProtocol))},
      {"schema_version", Json(std::int64_t{1})}});
  const std::string manifest_bytes = ReadBoundArtifact(
      request, "bundle/representation_manifest.json", 4U << 20U);
  const Json observed_manifest =
      ParseCanonicalDocument(manifest_bytes, "representation manifest");
  discrepancies->expect("bundle/representation_manifest.json",
                        expected_manifest, observed_manifest,
                        "independent bundle manifest differs");
}

void BindExternalDocument(const Json& identity, const Json& admitted,
                          std::string_view role) {
  if (DumpJson(identity) != DumpJson(admitted)) {
    throw std::runtime_error(std::string(role) + " identity mismatch");
  }
}

}  // namespace

Json VerifyCanonicalRequest(const Json& request) {
  ValidateRequest(request);
  if (std::fesetround(FE_TONEAREST) != 0 ||
      std::fegetround() != FE_TONEAREST) {
    throw std::runtime_error("independent replay cannot establish FE_TONEAREST");
  }
  const std::string manifest_payload = ReadBoundArtifact(
      request, "evidence/producer_manifest.json", 16U << 20U);
  if (Sha256(manifest_payload) !=
      request.at("producer_manifest_sha256").string()) {
    throw std::runtime_error("producer manifest request binding mismatch");
  }
  const Json manifest =
      ParseCanonicalDocument(manifest_payload, "producer manifest");
  if (manifest.at("artifact_kind").string() != "a4_producer_manifest" ||
      manifest.at("schema_version").integer() != 1 ||
      manifest.at("completed_unit_count").integer() !=
          request.at("completed_unit_count").integer() ||
      manifest.at("last_completed_unit_index").integer() !=
          request.at("last_completed_unit_index").integer()) {
    throw std::runtime_error("producer manifest prefix identity mismatch");
  }
  if (manifest.at("input_identity")
          .at("input_identity_sha256")
          .string() != request.at("input_identity_sha256").string()) {
    throw std::runtime_error("producer/request input identity mismatch");
  }
  BindExternalDocument(manifest.at("protocol_identity"),
                       request.at("protocol_identity"), "protocol");
  BindExternalDocument(manifest.at("schema_identity"),
                       request.at("schema_identity"), "schema");

  // Input generation and its fixed raw hash are inside this V_replay process;
  // neither a producer matrix nor a C-phase checkpoint is read.
  const InputPanel panel = RegenerateFrozenPanel();
  if (manifest.at("input_identity").at("raw_sha256").string() !=
          panel.raw_sha256 ||
      manifest.at("input_identity").at("raw_bytes").integer() != 4'194'304) {
    throw PanelIdentityError("regenerated panel differs from producer input identity");
  }

  const std::string scalar_payload = ReadBoundArtifact(
      request, "evidence/scalar_optimum_records.jsonl",
      std::uint64_t{4} << 30U);
  const std::string allocation_payload = ReadBoundArtifact(
      request, "evidence/allocation_summary.json", 512U << 20U);
  const std::string block_payload = ReadBoundArtifact(
      request, "evidence/block_trajectories.jsonl",
      std::uint64_t{4} << 30U);
  const std::string encoding_payload = ReadBoundArtifact(
      request, "evidence/encoding_summary.json", 32U << 20U);
  const std::vector<Json> scalar_records =
      ParseCanonicalLines(scalar_payload, "scalar evidence");
  const Json allocation =
      ParseCanonicalDocument(allocation_payload, "allocation evidence");
  const std::vector<Json> block_records =
      ParseCanonicalLines(block_payload, "block evidence");
  const Json encoding =
      ParseCanonicalDocument(encoding_payload, "encoding evidence");

  Discrepancies discrepancies;
  Curves curves;
  ReplayScalar(panel, scalar_records, &curves, &discrepancies);
  Allocations allocations;
  ReplayAllocations(allocation, curves, &allocations, &discrepancies);
  std::vector<BlockModel> blocks;
  ReplayBlocks(block_records, panel, curves, allocations, &blocks,
               &discrepancies);
  Encodings encodings;
  ReplayEncodings(encoding, panel, curves, allocations, blocks, &encodings,
                  &discrepancies);

  Json::Object counts = ZeroCounts();
  counts["scalar_optimum_records"] =
      Json(static_cast<std::int64_t>(scalar_records.size()));
  counts["allocation_group_records"] = Json(static_cast<std::int64_t>(
      allocation.at("group_records").array().size()));
  counts["allocation_global_records"] = Json(static_cast<std::int64_t>(
      allocation.at("global_records").array().size()));
  counts["block_metadata_records"] =
      Json(static_cast<std::int64_t>(block_records.size() / 9U));
  counts["block_start_records"] = Json(static_cast<std::int64_t>(
      (block_records.size() / 9U) * 8U));
  std::uint64_t block_steps = 0;
  for (std::size_t unit = 0; unit < block_records.size() / 9U; ++unit) {
    for (std::size_t start = 0; start < 8; ++start) {
      block_steps += block_records[9 * unit + start + 1]
                         .at("steps")
                         .array()
                         .size();
    }
  }
  counts["block_step_records"] = Json(static_cast<std::int64_t>(block_steps));
  counts["encoding_arm_records"] =
      Json(static_cast<std::int64_t>(encoding.at("records").array().size()));
  const bool bundle = request.at("completed_unit_count").integer() == 396;
  counts["bundle_files"] = Json(static_cast<std::int64_t>(bundle ? 4 : 0));
  if (bundle) {
    ReplayBundle(request, panel, curves, allocations, blocks, encodings,
                 &discrepancies);
  }

  const Json expected_counts = request.at("decision_counts_expected");
  discrepancies.expect("decision_counts", expected_counts, Json(counts),
                       "native replay inventory differs from frozen prefix");
  discrepancies.expect("manifest.record_counts", manifest.at("record_counts"),
                       Json(counts),
                       "producer manifest count binding differs from replay");
  return Response(request, true, std::move(counts),
                  std::move(discrepancies.values));
}

Json InputIdentityFailureResponse(const Json& request,
                                  std::string_view message) {
  ValidateRequest(request);
  Json::Array discrepancies;
  discrepancies.emplace_back(Json::Object{
      {"class", Json("INPUT_AUTHORITY_MISMATCH")},
      {"expected_sha256", Json(nullptr)},
      {"location", Json("registered_input")},
      {"message", Json(std::string(message))},
      {"observed_sha256", Json(nullptr)}});
  return Response(request, false, ZeroCounts(), std::move(discrepancies));
}

}  // namespace saq::a4_v2::verifier

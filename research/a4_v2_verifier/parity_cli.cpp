#include "parity_cli.hpp"

#include "exact_reference.hpp"
#include "sha256.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
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

class BinaryReader {
 public:
  explicit BinaryReader(const std::string& path)
      : input_(path, std::ios::binary) {
    if (!input_) throw std::runtime_error("cannot open verifier PAR input");
  }
  void Require(std::string_view expected, const char* field) {
    std::string observed(expected.size(), '\0');
    Read(observed.data(), observed.size(), field);
    if (observed != expected) {
      throw std::runtime_error(std::string(field) + " magic mismatch");
    }
  }
  [[nodiscard]] std::uint32_t U32(const char* field) {
    std::array<unsigned char, 4> bytes{};
    Read(reinterpret_cast<char*>(bytes.data()), bytes.size(), field);
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8U) |
           (static_cast<std::uint32_t>(bytes[2]) << 16U) |
           (static_cast<std::uint32_t>(bytes[3]) << 24U);
  }
  [[nodiscard]] std::uint64_t U64(const char* field) {
    std::array<unsigned char, 8> bytes{};
    Read(reinterpret_cast<char*>(bytes.data()), bytes.size(), field);
    std::uint64_t result = 0;
    for (std::size_t index = 0; index < bytes.size(); ++index) {
      result |= static_cast<std::uint64_t>(bytes[index]) << (8U * index);
    }
    return result;
  }
  [[nodiscard]] std::string Bytes(std::size_t size, const char* field) {
    std::string result(size, '\0');
    Read(result.data(), result.size(), field);
    return result;
  }
  void Eof() {
    char byte = 0;
    if (input_.read(&byte, 1) || !input_.eof() || input_.bad()) {
      throw std::runtime_error("verifier PAR input has trailing bytes");
    }
  }

 private:
  void Read(char* destination, std::size_t size, const char* field) {
    input_.read(destination, static_cast<std::streamsize>(size));
    if (!input_) throw std::runtime_error(std::string("truncated ") + field);
  }
  std::ifstream input_;
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

[[nodiscard]] std::uint32_t PredecessorLayer(const ExactCurve& curve,
                                             std::uint32_t requested) {
  if (curve.predecessors.size() <= 1) {
    throw std::logic_error("verifier predecessor certificate absent");
  }
  return std::min<std::uint32_t>(
      requested, static_cast<std::uint32_t>(curve.predecessors.size() - 1));
}

struct ExhaustivePrefix {
  std::vector<mpz_class> weight;
  std::vector<mpz_class> first;
  std::vector<mpz_class> second;

  explicit ExhaustivePrefix(const std::vector<ExactSupport>& support)
      : weight(support.size() + 1),
        first(support.size() + 1),
        second(support.size() + 1) {
    for (std::size_t index = 0; index < support.size(); ++index) {
      weight[index + 1] = weight[index] + support[index].weight;
      first[index + 1] =
          first[index] + support[index].weight * support[index].grid_integer;
      second[index + 1] =
          second[index] + support[index].weight * support[index].grid_integer *
                                support[index].grid_integer;
    }
  }

  [[nodiscard]] mpq_class Cost(std::uint32_t begin,
                               std::uint32_t end) const {
    const mpz_class w = weight[end] - weight[begin];
    const mpz_class a = first[end] - first[begin];
    const mpz_class c = second[end] - second[begin];
    mpq_class result(w * c - a * a, w);
    result.canonicalize();
    return result;
  }

  [[nodiscard]] ExactValue Mean(std::uint32_t begin,
                                std::uint32_t end) const {
    return ExactValue(first[end] - first[begin],
                      weight[end] - weight[begin], -149);
  }
};

struct ExhaustivePartition {
  bool present{false};
  mpq_class objective{0};
  std::vector<std::uint32_t> cuts;
};

[[nodiscard]] bool ReverseLexLower(
    const std::vector<std::uint32_t>& lhs,
    const std::vector<std::uint32_t>& rhs) {
  return std::lexicographical_compare(lhs.rbegin(), lhs.rend(),
                                      rhs.rbegin(), rhs.rend());
}

void EnumerateCuts(const ExhaustivePrefix& prefix, std::uint32_t end,
                   std::uint32_t required, std::uint32_t next,
                   std::vector<std::uint32_t>* cuts,
                   ExhaustivePartition* best) {
  if (cuts->size() == required) {
    mpq_class objective(0);
    std::uint32_t begin = 0;
    for (const std::uint32_t cut : *cuts) {
      objective += prefix.Cost(begin, cut);
      begin = cut;
    }
    objective += prefix.Cost(begin, end);
    objective.canonicalize();
    const int order = best->present
                          ? mpq_cmp(objective.get_mpq_t(),
                                    best->objective.get_mpq_t())
                          : -1;
    if (!best->present || order < 0 ||
        (order == 0 && ReverseLexLower(*cuts, best->cuts))) {
      best->present = true;
      best->objective = std::move(objective);
      best->cuts = *cuts;
    }
    return;
  }
  const std::uint32_t remaining =
      required - static_cast<std::uint32_t>(cuts->size());
  for (std::uint32_t cut = next; cut + remaining <= end; ++cut) {
    cuts->push_back(cut);
    EnumerateCuts(prefix, end, required, cut + 1, cuts, best);
    cuts->pop_back();
  }
}

[[nodiscard]] ExactCurve FitWeightedCurveExhaustive(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum) {
  if (samples.empty() || maximum == 0) {
    throw std::invalid_argument("empty exhaustive scalar PAR case");
  }
  struct Aggregate {
    mpz_class weight{0};
    std::uint64_t lowest{0};
  };
  std::map<mpz_class, Aggregate> aggregate;
  for (const WeightedExactSample& sample : samples) {
    if (sample.weight == 0) throw std::invalid_argument("zero PAR weight");
    const mpz_class value = DecodeBinary32Exact(sample.binary32_bits);
    const auto [position, inserted] = aggregate.try_emplace(value);
    position->second.weight +=
        mpz_class(static_cast<unsigned long>(sample.weight));
    if (inserted || sample.vector_id < position->second.lowest) {
      position->second.lowest = sample.vector_id;
    }
  }
  ExactCurve curve;
  for (const auto& [value, state] : aggregate) {
    curve.support.push_back(ExactSupport{value, state.weight, state.lowest});
  }
  const std::uint32_t h = static_cast<std::uint32_t>(curve.support.size());
  if (h > 12 || std::min(h, maximum) > 8) {
    throw std::invalid_argument(
        "exhaustive scalar PAR is bounded to H<=12 and effective K<=8");
  }
  const std::uint32_t layers = std::min(h, maximum);
  curve.solutions.resize(maximum + 1);
  curve.predecessors.assign(
      layers + 1,
      std::vector<std::uint32_t>(h + 1,
                                 std::numeric_limits<std::uint32_t>::max()));
  const ExhaustivePrefix prefix(curve.support);
  for (std::uint32_t layer = 1; layer <= layers; ++layer) {
    curve.predecessors[layer][0] = 0;
    for (std::uint32_t end = layer; end <= h; ++end) {
      ExhaustivePartition best;
      std::vector<std::uint32_t> cuts;
      EnumerateCuts(prefix, end, layer - 1, 1, &cuts, &best);
      if (!best.present) throw std::logic_error("partition enumeration empty");
      curve.predecessors[layer][end] =
          best.cuts.empty() ? 0 : best.cuts.back();
      if (end == h) {
        std::vector<ExactInterval> intervals;
        mpq_class replay(0);
        std::uint32_t begin = 0;
        for (const std::uint32_t cut : best.cuts) {
          replay += prefix.Cost(begin, cut);
          intervals.push_back(ExactInterval{begin, cut,
                                            prefix.Mean(begin, cut)});
          begin = cut;
        }
        replay += prefix.Cost(begin, h);
        replay.canonicalize();
        if (mpq_cmp(replay.get_mpq_t(), best.objective.get_mpq_t()) != 0) {
          throw std::logic_error("exhaustive partition replay mismatch");
        }
        intervals.push_back(
            ExactInterval{begin, h, prefix.Mean(begin, h)});
        curve.solutions[layer] = ExactSolution{
            layer, layer,
            ExactValue(best.objective.get_num(), best.objective.get_den(),
                       -298),
            std::move(intervals), 0, 0};
      }
    }
  }
  for (std::uint32_t requested = layers + 1; requested <= maximum;
       ++requested) {
    curve.solutions[requested] = curve.solutions[layers];
    curve.solutions[requested].requested_cardinality = requested;
    curve.solutions[requested].effective_cardinality = h;
  }
  return curve;
}

[[nodiscard]] ExactSolution ReconstructQuadraticSolution(
    const ExhaustivePrefix& prefix,
    const std::vector<std::vector<std::uint32_t>>& predecessors,
    std::uint32_t support_size, std::uint32_t cardinality,
    const mpq_class& optimum) {
  std::uint32_t end = support_size;
  std::vector<ExactInterval> reverse;
  reverse.reserve(cardinality);
  mpq_class replay(0);
  for (std::uint32_t layer = cardinality; layer > 0; --layer) {
    const std::uint32_t begin = predecessors[layer][end];
    if (begin >= end) {
      throw std::logic_error("quadratic block-axis partition is empty");
    }
    replay += prefix.Cost(begin, end);
    reverse.push_back(
        ExactInterval{begin, end, prefix.Mean(begin, end)});
    end = begin;
  }
  replay.canonicalize();
  if (end != 0 ||
      mpq_cmp(replay.get_mpq_t(), optimum.get_mpq_t()) != 0) {
    throw std::logic_error("quadratic block-axis replay mismatch");
  }
  std::reverse(reverse.begin(), reverse.end());
  return ExactSolution{
      cardinality, cardinality,
      ExactValue(optimum.get_num(), optimum.get_den(), -298),
      std::move(reverse), 0, 0};
}

// Independent bounded O(K H^2) exact DP for par-block axis validation.  It is
// deliberately neither the producer's SMAWK implementation nor V_replay's
// divide-and-conquer solver, and it does not use Python-provided partitions.
[[nodiscard]] ExactCurve FitBlockAxisCurveQuadratic(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum) {
  if (samples.empty() || maximum == 0 || maximum > 256) {
    throw std::invalid_argument("invalid quadratic block-axis inventory");
  }
  struct Aggregate {
    mpz_class weight{0};
    std::uint64_t lowest{0};
  };
  std::map<mpz_class, Aggregate> aggregate;
  for (const WeightedExactSample& sample : samples) {
    if (sample.weight == 0) {
      throw std::invalid_argument("zero quadratic block-axis weight");
    }
    const mpz_class value = DecodeBinary32Exact(sample.binary32_bits);
    const auto [position, inserted] = aggregate.try_emplace(value);
    position->second.weight +=
        mpz_class(static_cast<unsigned long>(sample.weight));
    if (inserted || sample.vector_id < position->second.lowest) {
      position->second.lowest = sample.vector_id;
    }
  }
  ExactCurve curve;
  for (const auto& [value, state] : aggregate) {
    curve.support.push_back(ExactSupport{value, state.weight, state.lowest});
  }
  const std::uint32_t h = static_cast<std::uint32_t>(curve.support.size());
  if (h == 0 || h > 256) {
    throw std::invalid_argument("block-axis support is outside [1,256]");
  }
  const std::uint32_t layers = std::min(h, maximum);
  curve.solutions.resize(static_cast<std::size_t>(maximum) + 1);
  curve.predecessors.assign(
      static_cast<std::size_t>(layers) + 1,
      std::vector<std::uint32_t>(static_cast<std::size_t>(h) + 1,
                                 std::numeric_limits<std::uint32_t>::max()));
  const ExhaustivePrefix prefix(curve.support);
  std::vector<mpq_class> previous(h + 1);
  std::vector<mpq_class> current(h + 1);
  curve.predecessors[1][0] = 0;
  for (std::uint32_t end = 1; end <= h; ++end) {
    curve.predecessors[1][end] = 0;
    previous[end] = prefix.Cost(0, end);
  }
  curve.solutions[1] = ReconstructQuadraticSolution(
      prefix, curve.predecessors, h, 1, previous[h]);
  for (std::uint32_t layer = 2; layer <= layers; ++layer) {
    curve.predecessors[layer][0] = 0;
    for (std::uint32_t end = layer; end <= h; ++end) {
      bool found = false;
      mpq_class best;
      std::uint32_t best_predecessor = 0;
      for (std::uint32_t predecessor = layer - 1; predecessor < end;
           ++predecessor) {
        mpq_class candidate =
            previous[predecessor] + prefix.Cost(predecessor, end);
        candidate.canonicalize();
        const int order = found
                              ? mpq_cmp(candidate.get_mpq_t(),
                                        best.get_mpq_t())
                              : -1;
        // Ascending scan plus strict replacement is the earliest-predecessor
        // recursive tie certificate.
        if (!found || order < 0) {
          found = true;
          best = std::move(candidate);
          best_predecessor = predecessor;
        }
      }
      if (!found) throw std::logic_error("quadratic block-axis state absent");
      current[end] = std::move(best);
      curve.predecessors[layer][end] = best_predecessor;
    }
    curve.solutions[layer] = ReconstructQuadraticSolution(
        prefix, curve.predecessors, h, layer, current[h]);
    previous.swap(current);
  }
  for (std::uint32_t requested = layers + 1; requested <= maximum;
       ++requested) {
    curve.solutions[requested] = curve.solutions[layers];
    curve.solutions[requested].requested_cardinality = requested;
    curve.solutions[requested].effective_cardinality = h;
  }
  return curve;
}

void WriteScalarLogicalCase(std::ostream& output, std::uint32_t case_id,
                            std::uint32_t sample_count,
                            const ExactCurve& curve,
                            std::uint32_t maximum) {
  output << "CASE\t" << case_id << '\t' << sample_count << '\t' << maximum
         << '\t' << curve.support.size() << '\n';
  for (std::size_t support = 0; support < curve.support.size(); ++support) {
    output << "SUPPORT\t" << case_id << '\t' << support << '\t'
           << curve.support[support].grid_integer.get_str() << '\t'
           << curve.support[support].weight.get_str() << '\t'
           << curve.support[support].lowest_vector_id << '\n';
  }
  for (std::uint32_t requested = 1; requested <= maximum; ++requested) {
    const ExactSolution& solution = curve.at(requested);
    output << "SOLUTION\t" << case_id << '\t' << requested << '\t'
           << solution.effective_cardinality << '\t'
           << solution.sse.numerator.get_str() << '\t'
           << solution.sse.denominator.get_str() << '\t'
           << solution.sse.binary_grid_exponent << '\t'
           << solution.intervals.size() << '\n';
    for (std::size_t cluster = 0; cluster < solution.intervals.size();
         ++cluster) {
      const ExactInterval& interval = solution.intervals[cluster];
      output << "CLUSTER\t" << case_id << '\t' << requested << '\t'
             << cluster << '\t' << interval.begin << '\t' << interval.end
             << '\t' << interval.mean.numerator.get_str() << '\t'
             << interval.mean.denominator.get_str() << '\t'
             << interval.mean.binary_grid_exponent << '\t'
             << Hex32(DirectRoundBinary32(interval.mean)) << '\t'
             << Hex64(DirectRoundBinary64(interval.mean)) << '\n';
    }
    const std::uint32_t layer = PredecessorLayer(curve, requested);
    output << "PREDECESSOR_ROW\t" << case_id << '\t' << requested << '\t'
           << (curve.support.size() - layer + 1);
    for (std::size_t prefix = layer; prefix <= curve.support.size();
         ++prefix) {
      output << '\t' << curve.predecessors[layer][prefix];
    }
    output << '\n';
  }
  for (std::size_t layer = 1; layer < curve.predecessors.size(); ++layer) {
    bool monotone = true;
    for (std::size_t prefix = layer + 1; prefix <= curve.support.size();
         ++prefix) {
      monotone = monotone &&
                 curve.predecessors[layer][prefix - 1] <=
                     curve.predecessors[layer][prefix];
    }
    output << "MONOTONE\t" << case_id << '\t' << layer << '\t'
           << static_cast<unsigned int>(monotone) << '\n';
  }
  output << "END_CASE\t" << case_id << '\n';
}

}  // namespace

ExactCurve FitParityScalarExhaustive(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum_cardinality) {
  return FitWeightedCurveExhaustive(samples, maximum_cardinality);
}

void WriteScalarParity(const std::string& input_path,
                       const std::string& output_path) {
  BinaryReader input(input_path);
  input.Require("A4SCL001", "scalar PAR input");
  const std::uint32_t case_count = input.U32("scalar PAR case count");
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create scalar PAR output");
  output << "A4V2_PAR_SCALAR_V1\n";
  for (std::uint32_t index = 0; index < case_count; ++index) {
    const std::uint32_t case_id = input.U32("scalar PAR case id");
    const std::uint32_t sample_count = input.U32("scalar PAR sample count");
    const std::uint32_t maximum = input.U32("scalar PAR maximum K");
    if (sample_count == 0 || maximum == 0 || maximum > 8) {
      throw std::runtime_error("invalid scalar PAR case shape");
    }
    std::vector<WeightedExactSample> samples;
    samples.reserve(sample_count);
    for (std::uint32_t sample = 0; sample < sample_count; ++sample) {
      samples.push_back(WeightedExactSample{
          input.U32("scalar PAR bits"), input.U64("scalar PAR weight"),
          input.U64("scalar PAR vector id")});
    }
    const ExactCurve curve = FitParityScalarExhaustive(samples, maximum);
    WriteScalarLogicalCase(output, case_id, sample_count, curve, maximum);
  }
  input.Eof();
  output << "END\t" << case_count << '\n';
  output.flush();
  if (!output) throw std::runtime_error("scalar PAR output failed");
}

namespace {

constexpr std::string_view kBlockHashDomain =
    "saq-attempt4-a4-1-20260713-schema2";

struct ParPoint {
  float x{0};
  float y{0};
  std::uint64_t cell_id{0};
  std::uint64_t vector_id{0};
  std::string selection_digest;
};

struct ParCenter {
  double x{0};
  double y{0};
};

enum class ParFailure {
  kNone,
  kNonfinite,
  kSseIncrease,
  kIterationLimit,
  kSerializedCollision,
  kCartesianDominance,
};

struct ParAssignment {
  std::vector<std::uint16_t> labels;
  double sse{0};
  std::uint64_t comparisons{0};
  std::uint64_t ties{0};
};

struct ParStep {
  std::uint32_t iteration{0};
  double prior_sse{0};
  double candidate_sse{0};
  std::uint64_t changed{0};
  std::vector<std::uint32_t> empty;
  std::vector<ParCenter> centers_after;
  std::vector<std::uint16_t> before;
  std::vector<std::uint16_t> after;
};

struct ParStart {
  std::uint32_t id{0};
  std::string first_seed_digest{64, '0'};
  std::vector<std::uint64_t> selected_ids;
  std::uint64_t comparisons{0};
  std::uint64_t assignment_ties{0};
  std::uint64_t farthest_ties{0};
  std::vector<ParCenter> initial_centers;
  double initial_sse{0};
  std::vector<ParStep> steps;
  bool converged{false};
  ParFailure failure{ParFailure::kNone};
  std::vector<ParCenter> final_centers;
  std::vector<std::uint16_t> final_assignments;
  double final_sse{0};
  std::vector<std::pair<std::uint32_t, std::uint32_t>> serialized;
  std::uint32_t distinct_serialized{0};
};

struct ParBlockCase {
  std::uint32_t case_id{0};
  std::uint32_t capacity{0};
  std::uint32_t group_id{0};
  std::string dataset_id;
  std::vector<ParPoint> points;
  std::vector<double> axis0;
  std::vector<double> axis1;
  std::vector<std::uint64_t> axis0_bits;
  std::vector<std::uint64_t> axis1_bits;
};

struct ParBlockResult {
  bool valid{false};
  ParFailure failure{ParFailure::kNone};
  std::uint32_t failed_start{0};
  std::string detail;
  std::vector<ParPoint> points;
  std::vector<ParCenter> cartesian;
  double cartesian_sse{0};
  double filled_sse{0};
  std::vector<ParStart> starts;
  std::uint32_t best{0};
};

class ParNonfinite final : public std::runtime_error {
 public:
  ParNonfinite() : std::runtime_error("nonfinite block arithmetic") {}
};

[[nodiscard]] std::string SelectionDigest(std::string_view dataset,
                                          std::uint64_t cell,
                                          std::uint64_t vector) {
  return Sha256(std::string(kBlockHashDomain) + "|" + std::string(dataset) +
                "|" + std::to_string(cell) + "|" +
                std::to_string(vector));
}

[[nodiscard]] std::string StartDigest(const ParBlockCase& input,
                                      std::uint32_t start,
                                      const ParPoint& point) {
  return Sha256(std::string(kBlockHashDomain) + "|" + input.dataset_id + "|" +
                std::to_string(input.capacity) + "|" +
                std::to_string(input.group_id) + "|" +
                std::to_string(start) + "|" +
                std::to_string(point.cell_id) + "|" +
                std::to_string(point.vector_id));
}

[[nodiscard]] double ParDistance(const ParPoint& point,
                                 const ParCenter& center) {
  const double dx = static_cast<double>(point.x) - center.x;
  const double x2 = dx * dx;
  const double dy = static_cast<double>(point.y) - center.y;
  const double y2 = dy * dy;
  const double result = x2 + y2;
  if (!std::isfinite(result) || result < 0) throw ParNonfinite();
  return result;
}

[[nodiscard]] ParAssignment ParAssign(const std::vector<ParPoint>& points,
                                      const std::vector<ParCenter>& centers) {
  if (centers.empty() || centers.size() > 256) {
    throw std::runtime_error("invalid verifier PAR center inventory");
  }
  ParAssignment result;
  result.labels.reserve(points.size());
  for (const ParPoint& point : points) {
    std::uint16_t best = 0;
    double minimum = ParDistance(point, centers[0]);
    ++result.comparisons;
    for (std::uint32_t center = 1; center < centers.size(); ++center) {
      const double candidate = ParDistance(point, centers[center]);
      ++result.comparisons;
      if (candidate < minimum) {
        minimum = candidate;
        best = static_cast<std::uint16_t>(center);
      } else if (candidate == minimum) {
        ++result.ties;
      }
    }
    result.labels.push_back(best);
    result.sse += minimum;
    if (!std::isfinite(result.sse)) throw ParNonfinite();
  }
  return result;
}

[[nodiscard]] std::size_t ParFarthest(
    const std::vector<ParPoint>& points, const std::vector<ParCenter>& centers,
    const std::set<std::uint64_t>& excluded, std::uint64_t* comparisons,
    std::uint64_t* ties) {
  bool found = false;
  std::size_t best_row = 0;
  double best_distance = 0;
  for (std::size_t row = 0; row < points.size(); ++row) {
    if (excluded.contains(points[row].vector_id)) continue;
    double nearest = ParDistance(points[row], centers[0]);
    ++*comparisons;
    for (std::size_t center = 1; center < centers.size(); ++center) {
      const double candidate = ParDistance(points[row], centers[center]);
      ++*comparisons;
      if (candidate < nearest) nearest = candidate;
    }
    bool lower_key = false;
    if (found && nearest == best_distance) {
      ++*ties;
      const ParPoint& incumbent = points[best_row];
      if (points[row].vector_id != incumbent.vector_id) {
        lower_key = points[row].vector_id < incumbent.vector_id;
      } else if (points[row].cell_id != incumbent.cell_id) {
        lower_key = points[row].cell_id < incumbent.cell_id;
      } else {
        lower_key = points[row].selection_digest < incumbent.selection_digest;
      }
    }
    if (!found || nearest > best_distance ||
        (nearest == best_distance && lower_key)) {
      found = true;
      best_row = row;
      best_distance = nearest;
    }
  }
  if (!found) throw std::runtime_error("verifier PAR farthest exhausted rows");
  return best_row;
}

void ParFill(const std::vector<ParPoint>& points, std::uint32_t capacity,
             std::vector<ParCenter>* centers,
             std::vector<std::uint64_t>* selected,
             std::uint64_t* comparisons, std::uint64_t* ties) {
  std::set<std::uint64_t> excluded(selected->begin(), selected->end());
  while (centers->size() < capacity) {
    const std::size_t row =
        ParFarthest(points, *centers, excluded, comparisons, ties);
    centers->push_back(ParCenter{static_cast<double>(points[row].x),
                                 static_cast<double>(points[row].y)});
    selected->push_back(points[row].vector_id);
    excluded.insert(points[row].vector_id);
  }
}

void ParSerialize(ParStart* start) {
  std::set<std::pair<std::uint32_t, std::uint32_t>> distinct;
  for (const ParCenter& center : start->final_centers) {
    const float x = static_cast<float>(center.x);
    const float y = static_cast<float>(center.y);
    if (!std::isfinite(x) || !std::isfinite(y)) throw ParNonfinite();
    std::uint32_t xb = std::bit_cast<std::uint32_t>(x);
    std::uint32_t yb = std::bit_cast<std::uint32_t>(y);
    if ((xb & 0x7fffffffU) == 0) xb = 0;
    if ((yb & 0x7fffffffU) == 0) yb = 0;
    start->serialized.emplace_back(xb, yb);
    distinct.emplace(xb, yb);
  }
  start->distinct_serialized = static_cast<std::uint32_t>(distinct.size());
}

[[nodiscard]] ParStart ParLloyd(const std::vector<ParPoint>& points,
                                std::vector<ParCenter> centers,
                                ParStart trace) {
  trace.initial_centers = centers;
  ParAssignment accepted;
  bool have_accepted = false;
  try {
    accepted = ParAssign(points, centers);
    have_accepted = true;
    trace.initial_sse = accepted.sse;
    trace.comparisons += accepted.comparisons;
    trace.assignment_ties += accepted.ties;
    for (std::uint32_t iteration = 1; iteration <= 300; ++iteration) {
      const ParAssignment before = ParAssign(points, centers);
      trace.comparisons += before.comparisons;
      trace.assignment_ties += before.ties;
      std::vector<double> sum_x(centers.size(), 0);
      std::vector<double> sum_y(centers.size(), 0);
      std::vector<std::uint64_t> counts(centers.size(), 0);
      for (std::size_t row = 0; row < points.size(); ++row) {
        const std::uint16_t label = before.labels[row];
        sum_x[label] += static_cast<double>(points[row].x);
        sum_y[label] += static_cast<double>(points[row].y);
        ++counts[label];
      }
      std::vector<ParCenter> candidate = centers;
      std::vector<std::uint32_t> empty;
      for (std::uint32_t center = 0; center < centers.size(); ++center) {
        if (counts[center] == 0) {
          empty.push_back(center);
        } else {
          candidate[center].x = sum_x[center] / counts[center];
          candidate[center].y = sum_y[center] / counts[center];
          if (!std::isfinite(candidate[center].x) ||
              !std::isfinite(candidate[center].y)) {
            throw ParNonfinite();
          }
        }
      }
      ParAssignment after = ParAssign(points, candidate);
      trace.comparisons += after.comparisons;
      trace.assignment_ties += after.ties;
      std::uint64_t changed = 0;
      for (std::size_t row = 0; row < before.labels.size(); ++row) {
        changed += before.labels[row] != after.labels[row] ? 1U : 0U;
      }
      if (after.sse > before.sse) {
        trace.failure = ParFailure::kSseIncrease;
        trace.final_centers = centers;
        trace.final_assignments = accepted.labels;
        trace.final_sse = accepted.sse;
        return trace;
      }
      trace.steps.push_back(ParStep{iteration, before.sse, after.sse, changed,
                                    std::move(empty), candidate,
                                    before.labels, after.labels});
      centers = std::move(candidate);
      accepted = std::move(after);
      if (changed == 0) {
        trace.converged = true;
        break;
      }
    }
    trace.final_centers = centers;
    trace.final_assignments = accepted.labels;
    trace.final_sse = accepted.sse;
    if (!trace.converged) {
      trace.failure = ParFailure::kIterationLimit;
      return trace;
    }
    ParSerialize(&trace);
    return trace;
  } catch (const ParNonfinite&) {
    trace.failure = ParFailure::kNonfinite;
    trace.final_centers = centers;
    trace.final_sse = have_accepted
                          ? accepted.sse
                          : std::numeric_limits<double>::infinity();
    if (have_accepted) trace.final_assignments = accepted.labels;
    return trace;
  }
}

void SetParFailure(ParBlockResult* result, ParFailure failure,
                   std::uint32_t start, std::string detail) {
  if (result->failure == ParFailure::kNone) {
    result->failure = failure;
    result->failed_start = start;
    result->detail = std::move(detail);
  }
}

[[nodiscard]] std::vector<ParCenter> ParCartesian(
    const ParBlockCase& input) {
  if (input.axis0.empty() || input.axis1.empty() ||
      static_cast<std::uint64_t>(input.axis0.size()) * input.axis1.size() >
          input.capacity) {
    throw std::runtime_error("invalid verifier PAR Cartesian axes");
  }
  for (const std::vector<double>* axis : {&input.axis0, &input.axis1}) {
    for (std::size_t index = 0; index < axis->size(); ++index) {
      if (!std::isfinite((*axis)[index]) ||
          (index != 0 && !((*axis)[index - 1] < (*axis)[index]))) {
        throw std::runtime_error("non-increasing verifier PAR axis");
      }
    }
  }
  std::vector<ParCenter> result;
  for (const double y : input.axis1) {
    for (const double x : input.axis0) result.push_back(ParCenter{x, y});
  }
  return result;
}

[[nodiscard]] ParBlockCase ReadParBlockCase(BinaryReader* input) {
  ParBlockCase result;
  result.case_id = input->U32("block PAR case id");
  result.capacity = input->U32("block PAR capacity");
  result.group_id = input->U32("block PAR group id");
  const std::uint32_t dataset_size = input->U32("block PAR dataset size");
  if (dataset_size == 0 || dataset_size > (1U << 20U)) {
    throw std::runtime_error("invalid block PAR dataset size");
  }
  result.dataset_id = input->Bytes(dataset_size, "block PAR dataset id");
  if (result.dataset_id.find_first_of("\t\n\r|") != std::string::npos) {
    throw std::runtime_error("block PAR dataset id contains delimiter");
  }
  const std::uint32_t point_count = input->U32("block PAR point count");
  const std::uint32_t axis0_count = input->U32("block PAR axis0 count");
  const std::uint32_t axis1_count = input->U32("block PAR axis1 count");
  if (result.capacity < 2 || result.capacity > 256 || point_count > 256 ||
      point_count < result.capacity || axis0_count == 0 || axis1_count == 0 ||
      static_cast<std::uint64_t>(axis0_count) * axis1_count >
          result.capacity) {
    throw std::runtime_error("invalid block PAR case shape");
  }
  std::set<std::uint64_t> vector_ids;
  result.points.reserve(point_count);
  for (std::uint32_t row = 0; row < point_count; ++row) {
    const std::uint32_t xb = input->U32("block PAR x bits");
    const std::uint32_t yb = input->U32("block PAR y bits");
    const std::uint64_t cell = input->U64("block PAR cell id");
    const std::uint64_t vector = input->U64("block PAR vector id");
    const float x = std::bit_cast<float>(xb);
    const float y = std::bit_cast<float>(yb);
    if (!std::isfinite(x) || !std::isfinite(y) ||
        !vector_ids.insert(vector).second) {
      throw std::runtime_error("invalid block PAR point");
    }
    result.points.push_back(ParPoint{
        x, y, cell, vector, SelectionDigest(result.dataset_id, cell, vector)});
  }
  std::sort(result.points.begin(), result.points.end(),
            [](const ParPoint& lhs, const ParPoint& rhs) {
    if (lhs.cell_id != rhs.cell_id) return lhs.cell_id < rhs.cell_id;
    if (lhs.selection_digest != rhs.selection_digest) {
      return lhs.selection_digest < rhs.selection_digest;
    }
    return lhs.vector_id < rhs.vector_id;
  });
  for (std::uint32_t index = 0; index < axis0_count; ++index) {
    const std::uint64_t bits = input->U64("block PAR axis0 bits");
    result.axis0_bits.push_back(bits);
    result.axis0.push_back(std::bit_cast<double>(bits));
  }
  for (std::uint32_t index = 0; index < axis1_count; ++index) {
    const std::uint64_t bits = input->U64("block PAR axis1 bits");
    result.axis1_bits.push_back(bits);
    result.axis1.push_back(std::bit_cast<double>(bits));
  }
  return result;
}

[[nodiscard]] std::vector<std::uint64_t> ExactAxisBits(
    const ExactSolution& solution) {
  std::vector<std::uint64_t> result;
  result.reserve(solution.intervals.size());
  for (const ExactInterval& interval : solution.intervals) {
    result.push_back(DirectRoundBinary64(interval.mean));
  }
  return result;
}

[[nodiscard]] bool IsBlockHelper(std::uint32_t case_id) {
  return case_id >= 1000 && case_id <= 1004;
}

void ValidateBlockHelperInput(const ParBlockCase& input) {
  if (!IsBlockHelper(input.case_id) ||
      input.group_id != input.case_id - 1000 ||
      input.dataset_id != "a4_v2_par_block_microfixture") {
    throw std::runtime_error("block helper authority identity mismatch");
  }
  using Row = std::pair<std::uint32_t, std::uint32_t>;
  std::vector<Row> expected_rows;
  std::uint32_t expected_capacity = 2;
  std::vector<std::uint64_t> expected_axis0;
  std::vector<std::uint64_t> expected_axis1{0x0000000000000000ULL};
  switch (input.case_id) {
    case 1000:
      expected_rows = {{0xbf800000U, 0U}, {0x3f800000U, 0U}, {0U, 0U}};
      expected_axis0 = {0xbff0000000000000ULL, 0x3ff0000000000000ULL};
      break;
    case 1001:
    case 1003:
      expected_rows = {{0xbf800000U, 0U}, {0x3f800000U, 0U}};
      expected_axis0 = {0x0000000000000000ULL};
      break;
    case 1002:
      expected_capacity = 3;
      expected_rows = {{0U, 0U}, {0U, 0U}, {0x3f800000U, 0U}};
      expected_axis0 = {0x0000000000000000ULL};
      break;
    case 1004:
      expected_rows = {{0xbf800000U, 0U}, {0x3f800000U, 0U}};
      expected_axis0 = {0xbff0000000000000ULL, 0x3ff0000000000000ULL};
      break;
    default:
      throw std::logic_error("unreachable block helper id");
  }
  if (input.capacity != expected_capacity ||
      input.axis0_bits != expected_axis0 || input.axis1_bits != expected_axis1 ||
      input.points.size() != expected_rows.size()) {
    throw std::runtime_error("block helper frozen shape mismatch");
  }
  for (std::size_t row = 0; row < expected_rows.size(); ++row) {
    if (std::bit_cast<std::uint32_t>(input.points[row].x) !=
            expected_rows[row].first ||
        std::bit_cast<std::uint32_t>(input.points[row].y) !=
            expected_rows[row].second ||
        input.points[row].cell_id != row || input.points[row].vector_id != row) {
      throw std::runtime_error("block helper row/cell/vector identity mismatch");
    }
  }
}

void ValidateIndependentBlockAxes(const ParBlockCase& input) {
  if (IsBlockHelper(input.case_id)) {
    ValidateBlockHelperInput(input);
    return;
  }
  if (input.case_id >= 64) {
    throw std::runtime_error("production block PAR case id is outside 0..63");
  }
  std::vector<WeightedExactSample> first_samples;
  std::vector<WeightedExactSample> second_samples;
  first_samples.reserve(input.points.size());
  second_samples.reserve(input.points.size());
  for (const ParPoint& point : input.points) {
    first_samples.push_back(WeightedExactSample{
        std::bit_cast<std::uint32_t>(point.x), 1, point.vector_id});
    second_samples.push_back(WeightedExactSample{
        std::bit_cast<std::uint32_t>(point.y), 1, point.vector_id});
  }
  const ExactCurve first =
      FitBlockAxisCurveQuadratic(first_samples, input.capacity);
  const ExactCurve second =
      FitBlockAxisCurveQuadratic(second_samples, input.capacity);
  const ProductDecision allocation = ExhaustiveProductDecision(
      first, second, input.capacity, CardinalityDomain::kAllPositive);
  const std::vector<std::uint64_t> expected_first =
      ExactAxisBits(first.at(allocation.first));
  const std::vector<std::uint64_t> expected_second =
      ExactAxisBits(second.at(allocation.second));
  if (input.axis0_bits != expected_first ||
      input.axis1_bits != expected_second) {
    throw std::runtime_error(
        "block PAR axes differ from independent exact allocation/direct-b64");
  }
}

[[nodiscard]] ParBlockResult TrainParBlock(const ParBlockCase& input) {
  ParBlockResult result;
  result.points = input.points;
  ParStart seed0;
  seed0.id = 0;
  std::vector<ParCenter> centers0;
  try {
    result.cartesian = ParCartesian(input);
    result.cartesian_sse = ParAssign(result.points, result.cartesian).sse;
    centers0 = result.cartesian;
    ParFill(result.points, input.capacity, &centers0, &seed0.selected_ids,
            &seed0.comparisons, &seed0.farthest_ties);
    result.filled_sse = ParAssign(result.points, centers0).sse;
    if (result.filled_sse > result.cartesian_sse) {
      seed0.failure = ParFailure::kCartesianDominance;
      SetParFailure(&result, ParFailure::kCartesianDominance, 0,
                    "farthest fill exceeds Cartesian SSE");
    }
  } catch (const ParNonfinite&) {
    seed0.failure = ParFailure::kNonfinite;
    result.cartesian_sse = std::numeric_limits<double>::infinity();
    result.filled_sse = std::numeric_limits<double>::infinity();
    SetParFailure(&result, ParFailure::kNonfinite, 0,
                  "nonfinite Cartesian initialization");
  }
  if (seed0.failure == ParFailure::kNone) {
    result.starts.push_back(
        ParLloyd(result.points, std::move(centers0), std::move(seed0)));
  } else {
    seed0.initial_centers = centers0;
    seed0.final_centers = centers0;
    seed0.initial_sse = result.filled_sse;
    seed0.final_sse = result.filled_sse;
    result.starts.push_back(std::move(seed0));
  }
  if (result.starts[0].failure != ParFailure::kNone) {
    SetParFailure(&result, result.starts[0].failure, 0,
                  "start 0 control failure");
  } else if (result.starts[0].final_sse > result.cartesian_sse) {
    result.starts[0].failure = ParFailure::kCartesianDominance;
    SetParFailure(&result, ParFailure::kCartesianDominance, 0,
                  "start 0 final SSE exceeds Cartesian SSE");
  }
  for (std::uint32_t start_id = 1; start_id < 8; ++start_id) {
    ParStart seed;
    seed.id = start_id;
    try {
      bool found = false;
      std::size_t first_row = 0;
      for (std::size_t row = 0; row < result.points.size(); ++row) {
        const std::string digest = StartDigest(input, start_id,
                                               result.points[row]);
        if (!found || digest < seed.first_seed_digest ||
            (digest == seed.first_seed_digest &&
             result.points[row].vector_id <
                 result.points[first_row].vector_id)) {
          found = true;
          first_row = row;
          seed.first_seed_digest = digest;
        }
      }
      seed.selected_ids.push_back(result.points[first_row].vector_id);
      std::vector<ParCenter> centers{
          ParCenter{static_cast<double>(result.points[first_row].x),
                    static_cast<double>(result.points[first_row].y)}};
      ParFill(result.points, input.capacity, &centers, &seed.selected_ids,
              &seed.comparisons, &seed.farthest_ties);
      seed = ParLloyd(result.points, std::move(centers), std::move(seed));
    } catch (const ParNonfinite&) {
      seed.failure = ParFailure::kNonfinite;
      seed.final_sse = std::numeric_limits<double>::infinity();
    }
    result.starts.push_back(std::move(seed));
    if (result.starts.back().failure != ParFailure::kNone) {
      SetParFailure(&result, result.starts.back().failure, start_id,
                    "salted start control failure");
    }
  }
  if (result.failure != ParFailure::kNone) return result;
  result.best = 0;
  for (std::uint32_t start = 1; start < result.starts.size(); ++start) {
    if (result.starts[start].final_sse < result.starts[result.best].final_sse) {
      result.best = start;
    }
  }
  if (result.starts[result.best].final_sse > result.cartesian_sse) {
    SetParFailure(&result, ParFailure::kCartesianDominance, result.best,
                  "best start exceeds Cartesian SSE");
    return result;
  }
  if (result.starts[result.best].distinct_serialized != input.capacity) {
    result.starts[result.best].failure = ParFailure::kSerializedCollision;
    SetParFailure(&result, ParFailure::kSerializedCollision, result.best,
                  "selected binary32 centers collide");
    return result;
  }
  result.valid = true;
  return result;
}

void ValidateBlockHelperResult(const ParBlockCase& input,
                               const ParBlockResult& result) {
  if (!IsBlockHelper(input.case_id)) return;
  if (result.starts.empty()) {
    throw std::runtime_error("block helper produced no start trace");
  }
  const ParStart& start0 = result.starts[0];
  switch (input.case_id) {
    case 1000: {
      if (start0.steps.empty() || start0.steps[0].before.size() != 3 ||
          start0.steps[0].before[2] != 0 || start0.assignment_ties == 0) {
        throw std::runtime_error(
            "equidistant helper did not retain lower codeword index");
      }
      break;
    }
    case 1001:
      if (start0.selected_ids.size() != 1 || start0.selected_ids[0] != 0 ||
          start0.farthest_ties == 0) {
        throw std::runtime_error(
            "farthest-fill helper did not select lower vector_id on tie");
      }
      break;
    case 1002: {
      bool witnessed_retention = false;
      std::vector<ParCenter> prior = start0.initial_centers;
      for (const ParStep& step : start0.steps) {
        for (const std::uint32_t empty : step.empty) {
          if (empty >= prior.size() || empty >= step.centers_after.size()) {
            throw std::runtime_error("empty-center helper index is invalid");
          }
          if (std::bit_cast<std::uint64_t>(prior[empty].x) !=
                  std::bit_cast<std::uint64_t>(step.centers_after[empty].x) ||
              std::bit_cast<std::uint64_t>(prior[empty].y) !=
                  std::bit_cast<std::uint64_t>(step.centers_after[empty].y)) {
            throw std::runtime_error(
                "empty-center helper changed retained binary64 center bits");
          }
          witnessed_retention = true;
        }
        prior = step.centers_after;
      }
      if (!witnessed_retention) {
        throw std::runtime_error("empty-center helper emitted no STEP_EMPTY");
      }
      break;
    }
    case 1003:
      if (result.cartesian.size() != 1 || start0.initial_centers.size() != 2 ||
          start0.selected_ids.size() != 1) {
        throw std::runtime_error(
            "Cartesian-before-fill helper ordering/size mismatch");
      }
      break;
    case 1004: {
      if (!result.valid || result.starts.size() != 8 || result.best != 0) {
        throw std::runtime_error("best-of-eight helper did not select start zero");
      }
      const std::uint64_t expected_sse =
          std::bit_cast<std::uint64_t>(result.starts[0].final_sse);
      for (const ParStart& start : result.starts) {
        if (start.failure != ParFailure::kNone || !start.converged ||
            std::bit_cast<std::uint64_t>(start.final_sse) != expected_sse) {
          throw std::runtime_error(
              "best-of-eight helper starts are not all valid/equal-SSE");
        }
      }
      break;
    }
    default:
      throw std::logic_error("unreachable block helper result id");
  }
}

[[nodiscard]] const char* ParFailureName(ParFailure failure) {
  switch (failure) {
    case ParFailure::kNone: return "NONE";
    case ParFailure::kNonfinite: return "NONFINITE_CONTROL";
    case ParFailure::kSseIncrease: return "CANDIDATE_SSE_INCREASE";
    case ParFailure::kIterationLimit: return "ITERATION_LIMIT";
    case ParFailure::kSerializedCollision: return "SERIALIZED_CENTER_COLLISION";
    case ParFailure::kCartesianDominance: return "CARTESIAN_DOMINANCE";
  }
  throw std::logic_error("unknown verifier PAR block failure");
}

void EmitParStart(std::ostream& output, std::uint32_t case_id,
                  const std::vector<ParPoint>& points,
                  const ParStart& start) {
  output << "START\t" << case_id << '\t' << start.id << '\t'
         << start.first_seed_digest << '\t' << start.selected_ids.size()
         << '\t' << start.initial_centers.size() << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(start.initial_sse)) << '\t'
         << start.steps.size() << '\t' << start.steps.size() << '\t'
         << static_cast<unsigned int>(start.converged) << '\t'
         << ParFailureName(start.failure) << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(start.final_sse)) << '\t'
         << start.final_assignments.size() << '\t'
         << start.final_centers.size() << '\t' << start.serialized.size()
         << '\t' << start.distinct_serialized << '\t' << start.comparisons
         << '\t' << start.assignment_ties << '\t' << start.farthest_ties
         << '\n';
  for (std::size_t index = 0; index < start.selected_ids.size(); ++index) {
    output << "START_SELECTED\t" << case_id << '\t' << start.id << '\t'
           << index << '\t' << start.selected_ids[index] << '\n';
  }
  for (std::size_t center = 0; center < start.initial_centers.size(); ++center) {
    output << "START_CENTER\t" << case_id << '\t' << start.id << '\t'
           << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(
                  start.initial_centers[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(
                  start.initial_centers[center].y))
           << '\n';
  }
  for (const ParStep& step : start.steps) {
    output << "STEP\t" << case_id << '\t' << start.id << '\t'
           << step.iteration << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(step.prior_sse)) << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(step.candidate_sse)) << '\t'
           << step.changed << '\t' << step.empty.size() << '\t'
           << step.centers_after.size() << '\n';
    for (std::size_t index = 0; index < step.empty.size(); ++index) {
      output << "STEP_EMPTY\t" << case_id << '\t' << start.id << '\t'
             << step.iteration << '\t' << index << '\t' << step.empty[index]
             << '\n';
    }
    for (std::size_t center = 0; center < step.centers_after.size(); ++center) {
      output << "STEP_CENTER\t" << case_id << '\t' << start.id << '\t'
             << step.iteration << '\t' << center << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(
                    step.centers_after[center].x))
             << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(
                    step.centers_after[center].y))
             << '\n';
    }
    if (step.before.size() != points.size() ||
        step.after.size() != points.size()) {
      throw std::logic_error("verifier PAR step assignment shape mismatch");
    }
    for (std::size_t row = 0; row < points.size(); ++row) {
      output << "STEP_ASSIGNMENT_BEFORE\t" << case_id << '\t' << start.id
             << '\t' << step.iteration << '\t' << row << '\t'
             << points[row].vector_id << '\t' << step.before[row] << '\n';
    }
    for (std::size_t row = 0; row < points.size(); ++row) {
      output << "STEP_ASSIGNMENT_AFTER\t" << case_id << '\t' << start.id
             << '\t' << step.iteration << '\t' << row << '\t'
             << points[row].vector_id << '\t' << step.after[row] << '\n';
    }
  }
  for (std::size_t row = 0; row < start.final_assignments.size(); ++row) {
    output << "FINAL_ASSIGNMENT\t" << case_id << '\t' << start.id << '\t'
           << row << '\t' << points[row].vector_id << '\t'
           << start.final_assignments[row] << '\n';
  }
  for (std::size_t center = 0; center < start.final_centers.size(); ++center) {
    output << "FINAL_CENTER\t" << case_id << '\t' << start.id << '\t'
           << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.final_centers[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.final_centers[center].y))
           << '\n';
  }
  for (std::size_t center = 0; center < start.serialized.size(); ++center) {
    output << "FINAL_SERIALIZED_CENTER\t" << case_id << '\t' << start.id
           << '\t' << center << '\t' << Hex32(start.serialized[center].first)
           << '\t' << Hex32(start.serialized[center].second) << '\n';
  }
  output << "END_START\t" << case_id << '\t' << start.id << '\n';
}

void EmitParBlockCase(std::ostream& output, const ParBlockCase& input,
                      const ParBlockResult& result) {
  output << "CASE\t" << input.case_id << '\t' << kBlockHashDomain << '\t'
         << input.dataset_id << '\t' << input.capacity << '\t'
         << input.group_id << '\t' << input.points.size() << '\t'
         << input.axis0.size() << '\t' << input.axis1.size() << '\t'
         << static_cast<unsigned int>(result.valid) << '\t'
         << ParFailureName(result.failure) << '\t' << result.failed_start
         << '\t' << result.detail << '\n';
  for (std::size_t index = 0; index < input.axis0_bits.size(); ++index) {
    output << "AXIS\t" << input.case_id << "\t0\t" << index << '\t'
           << Hex64(input.axis0_bits[index]) << '\n';
  }
  for (std::size_t index = 0; index < input.axis1_bits.size(); ++index) {
    output << "AXIS\t" << input.case_id << "\t1\t" << index << '\t'
           << Hex64(input.axis1_bits[index]) << '\n';
  }
  for (std::size_t row = 0; row < result.points.size(); ++row) {
    const ParPoint& point = result.points[row];
    output << "ROW\t" << input.case_id << '\t' << row << '\t'
           << point.cell_id << '\t' << point.vector_id << '\t'
           << point.selection_digest << '\t'
           << Hex32(std::bit_cast<std::uint32_t>(point.x)) << '\t'
           << Hex32(std::bit_cast<std::uint32_t>(point.y)) << '\n';
  }
  output << "CARTESIAN\t" << input.case_id << '\t'
         << result.cartesian.size() << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(result.cartesian_sse)) << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(result.filled_sse)) << '\n';
  for (std::size_t center = 0; center < result.cartesian.size(); ++center) {
    output << "CARTESIAN_CENTER\t" << input.case_id << '\t' << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(result.cartesian[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(result.cartesian[center].y))
           << '\n';
  }
  for (const ParStart& start : result.starts) {
    EmitParStart(output, input.case_id, result.points, start);
  }
  if (!result.valid) {
    output << "BEST\t" << input.case_id << "\t0\n";
  } else {
    const ParStart& best = result.starts[result.best];
    output << "BEST\t" << input.case_id << "\t1\t" << result.best << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(best.final_sse)) << '\t'
           << best.final_centers.size() << '\t'
           << best.final_assignments.size() << '\t' << best.serialized.size()
           << '\n';
    for (std::size_t center = 0; center < best.final_centers.size(); ++center) {
      output << "BEST_CENTER\t" << input.case_id << '\t' << center << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(best.final_centers[center].x))
             << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(best.final_centers[center].y))
             << '\t' << Hex32(best.serialized[center].first) << '\t'
             << Hex32(best.serialized[center].second) << '\n';
    }
    for (std::size_t row = 0; row < best.final_assignments.size(); ++row) {
      output << "BEST_ASSIGNMENT\t" << input.case_id << '\t' << row << '\t'
             << result.points[row].vector_id << '\t'
             << best.final_assignments[row] << '\n';
    }
  }
  output << "END_CASE\t" << input.case_id << '\n';
}

}  // namespace

void WriteBlockParity(const std::string& input_path,
                      const std::string& output_path) {
  BinaryReader input(input_path);
  input.Require("A4BLK001", "block PAR input");
  const std::uint32_t case_count = input.U32("block PAR case count");
  if (case_count != 69) {
    throw std::runtime_error("block PAR requires five helpers plus 64 production cases");
  }
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create block PAR output");
  output << "A4S_BLOCK_RESULT_V1\nPROTOCOL\t" << kBlockHashDomain << '\n';
  std::uint32_t valid = 0;
  for (std::uint32_t index = 0; index < case_count; ++index) {
    const ParBlockCase block = ReadParBlockCase(&input);
    const std::uint32_t expected_case_id =
        index < 5 ? 1000 + index : index - 5;
    if (block.case_id != expected_case_id) {
      throw std::runtime_error("block PAR helper/production ordering mismatch");
    }
    ValidateIndependentBlockAxes(block);
    const ParBlockResult result = TrainParBlock(block);
    ValidateBlockHelperResult(block, result);
    EmitParBlockCase(output, block, result);
    valid += result.valid ? 1U : 0U;
  }
  input.Eof();
  output << "END\t" << case_count << '\t' << valid << '\t'
         << (case_count - valid) << '\n';
  output.flush();
  if (!output) throw std::runtime_error("block PAR output failed");
}

}  // namespace saq::a4_v2::verifier

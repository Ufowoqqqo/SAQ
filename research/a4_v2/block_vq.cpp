#include "block_vq.hpp"

#include <openssl/sha.h>

#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace saq::a4_v2::producer {
namespace {

constexpr std::uint32_t kStartCount = 8;
constexpr std::uint32_t kIterationCap = 300;

class Nonfinite final : public std::runtime_error {
 public:
  explicit Nonfinite(const char* message) : std::runtime_error(message) {}
};

void ValidateKey(std::string_view value, const char* field) {
  if (value.empty() || value.find('|') != std::string_view::npos ||
      value.find('\n') != std::string_view::npos ||
      value.find('\r') != std::string_view::npos) {
    throw std::invalid_argument(std::string("invalid block ") + field);
  }
}

[[nodiscard]] Digest Hash(std::string_view bytes) {
  Digest result{};
  if (SHA256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(),
             result.data()) == nullptr) {
    throw std::runtime_error("SHA-256 failure");
  }
  return result;
}

[[nodiscard]] std::string SelectionKey(std::string_view hash_domain,
                                       std::string_view dataset_id,
                                       std::uint64_t cell_id,
                                       std::uint64_t vector_id) {
  ValidateKey(hash_domain, "hash domain");
  ValidateKey(dataset_id, "dataset id");
  return std::string(hash_domain) + "|" + std::string(dataset_id) + "|" +
         std::to_string(cell_id) + "|" + std::to_string(vector_id);
}

[[nodiscard]] std::string StartKey(const BlockMetadata& metadata,
                                   std::uint32_t start_id,
                                   std::uint64_t cell_id,
                                   std::uint64_t vector_id) {
  if (start_id >= kStartCount || metadata.capacity == 0) {
    throw std::invalid_argument("invalid block start metadata");
  }
  ValidateKey(metadata.hash_domain, "hash domain");
  ValidateKey(metadata.dataset_id, "dataset id");
  return metadata.hash_domain + "|" + metadata.dataset_id + "|" +
         std::to_string(metadata.capacity) + "|" +
         std::to_string(metadata.group_id) + "|" +
         std::to_string(start_id) + "|" + std::to_string(cell_id) + "|" +
         std::to_string(vector_id);
}

void ValidateCenter(const Center2& center) {
  if (!std::isfinite(center.x) || !std::isfinite(center.y)) {
    throw Nonfinite("nonfinite block center");
  }
}

[[nodiscard]] Center2 CenterFromPoint(const Point2& point) {
  return Center2{static_cast<double>(point.x), static_cast<double>(point.y)};
}

[[nodiscard]] double Distance(const Point2& point, const Center2& center) {
  const double dx = static_cast<double>(point.x) - center.x;
  const double x2 = dx * dx;
  const double dy = static_cast<double>(point.y) - center.y;
  const double y2 = dy * dy;
  const double result = x2 + y2;
  if (!std::isfinite(result) || result < 0.0) {
    throw Nonfinite("nonfinite block distance");
  }
  return result;
}

struct Assignment {
  std::vector<std::uint16_t> labels;
  double sse{0.0};
  std::uint64_t comparisons{0};
  std::uint64_t ties{0};
};

[[nodiscard]] Assignment Assign(const std::vector<Point2>& points,
                                const std::vector<Center2>& centers) {
  if (centers.empty() || centers.size() > 256) {
    throw std::invalid_argument("block center count outside [1,256]");
  }
  for (const Center2& center : centers) {
    ValidateCenter(center);
  }
  Assignment result;
  result.labels.resize(points.size());
  for (std::size_t row = 0; row < points.size(); ++row) {
    std::uint32_t best = 0;
    double best_distance = Distance(points[row], centers[0]);
    ++result.comparisons;
    for (std::uint32_t center = 1; center < centers.size(); ++center) {
      const double candidate = Distance(points[row], centers[center]);
      ++result.comparisons;
      if (candidate < best_distance) {
        best = center;
        best_distance = candidate;
      } else if (candidate == best_distance) {
        ++result.ties;
      }
    }
    result.labels[row] = static_cast<std::uint16_t>(best);
    result.sse += best_distance;
    if (!std::isfinite(result.sse)) {
      throw Nonfinite("nonfinite block SSE");
    }
  }
  return result;
}

[[nodiscard]] std::size_t Farthest(
    const std::vector<Point2>& points, const std::vector<Center2>& centers,
    const std::set<std::uint64_t>& excluded, std::uint64_t* comparisons,
    std::uint64_t* ties) {
  bool found = false;
  std::size_t best_row = 0;
  double best_distance = 0.0;
  for (std::size_t row = 0; row < points.size(); ++row) {
    if (excluded.contains(points[row].vector_id)) {
      continue;
    }
    double nearest = Distance(points[row], centers[0]);
    ++*comparisons;
    for (std::size_t center = 1; center < centers.size(); ++center) {
      const double candidate = Distance(points[row], centers[center]);
      ++*comparisons;
      if (candidate < nearest) {
        nearest = candidate;
      }
    }
    bool lower_tie_key = false;
    if (found && nearest == best_distance) {
      ++*ties;
      const Point2& incumbent = points[best_row];
      if (points[row].vector_id != incumbent.vector_id) {
        lower_tie_key = points[row].vector_id < incumbent.vector_id;
      } else if (points[row].cell_id != incumbent.cell_id) {
        lower_tie_key = points[row].cell_id < incumbent.cell_id;
      } else if (points[row].selection_digest != incumbent.selection_digest) {
        lower_tie_key =
            points[row].selection_digest < incumbent.selection_digest;
      }
    }
    if (!found || nearest > best_distance ||
        (nearest == best_distance && lower_tie_key)) {
      found = true;
      best_row = row;
      best_distance = nearest;
    }
  }
  if (!found) {
    throw std::invalid_argument("insufficient unique block rows");
  }
  return best_row;
}

void FarthestFill(const std::vector<Point2>& points, std::uint32_t capacity,
                  std::vector<Center2>* centers,
                  std::vector<std::uint64_t>* selected,
                  std::uint64_t* comparisons, std::uint64_t* ties) {
  std::set<std::uint64_t> excluded(selected->begin(), selected->end());
  while (centers->size() < capacity) {
    const std::size_t row =
        Farthest(points, *centers, excluded, comparisons, ties);
    centers->push_back(CenterFromPoint(points[row]));
    selected->push_back(points[row].vector_id);
    excluded.insert(points[row].vector_id);
  }
}

[[nodiscard]] std::vector<Center2> Cartesian(
    const std::vector<double>& axis0, const std::vector<double>& axis1,
    std::uint32_t capacity) {
  if (axis0.empty() || axis1.empty() ||
      static_cast<std::uint64_t>(axis0.size()) * axis1.size() > capacity) {
    throw std::invalid_argument("invalid Cartesian initialization");
  }
  for (const std::vector<double>* axis : {&axis0, &axis1}) {
    for (std::size_t index = 0; index < axis->size(); ++index) {
      if (!std::isfinite((*axis)[index]) ||
          (index != 0 && !((*axis)[index - 1] < (*axis)[index]))) {
        throw std::invalid_argument("non-increasing Cartesian axis");
      }
    }
  }
  std::vector<Center2> result;
  result.reserve(capacity);
  for (const double y : axis1) {
    for (const double x : axis0) {
      result.push_back(Center2{x, y});  // x/z0 is the fast digit.
    }
  }
  return result;
}

[[nodiscard]] std::uint64_t Changed(
    const std::vector<std::uint16_t>& before,
    const std::vector<std::uint16_t>& after) {
  if (before.size() != after.size()) {
    throw std::logic_error("assignment shape changed");
  }
  std::uint64_t result = 0;
  for (std::size_t index = 0; index < before.size(); ++index) {
    result += before[index] != after[index] ? 1U : 0U;
  }
  return result;
}

void SerializeFinal(BlockStartTrace* trace) {
  std::vector<SerializedCenter2> serialized_centers;
  serialized_centers.reserve(trace->final_centers.size());
  std::set<SerializedCenter2> distinct;
  for (const Center2& center : trace->final_centers) {
    const SerializedCenter2 serialized = SerializeCenter(center);
    serialized_centers.push_back(serialized);
    distinct.insert(serialized);
  }
  trace->serialized_final_centers = std::move(serialized_centers);
  trace->distinct_serialized_center_count =
      static_cast<std::uint32_t>(distinct.size());
}

void SerializeFailureState(BlockStartTrace* trace) {
  try {
    SerializeFinal(trace);
  } catch (const Nonfinite&) {
    trace->serialized_final_centers.clear();
    trace->distinct_serialized_center_count = 0;
  }
}

[[nodiscard]] BlockStartTrace Lloyd(const std::vector<Point2>& points,
                                    std::vector<Center2> centers,
                                    BlockStartTrace trace) {
  trace.initial_centers = centers;
  Assignment accepted;
  bool has_accepted = false;
  try {
    accepted = Assign(points, centers);
    has_accepted = true;
    trace.initial_sse = accepted.sse;
    trace.distance_comparison_count += accepted.comparisons;
    trace.assignment_tie_count += accepted.ties;
    for (std::uint32_t iteration = 1; iteration <= kIterationCap;
         ++iteration) {
      const Assignment before = Assign(points, centers);
      trace.distance_comparison_count += before.comparisons;
      trace.assignment_tie_count += before.ties;
      std::vector<double> sums_x(centers.size(), 0.0);
      std::vector<double> sums_y(centers.size(), 0.0);
      std::vector<std::uint64_t> counts(centers.size(), 0);
      for (std::size_t row = 0; row < points.size(); ++row) {
        const std::uint16_t label = before.labels[row];
        sums_x[label] += static_cast<double>(points[row].x);
        sums_y[label] += static_cast<double>(points[row].y);
        ++counts[label];
      }
      std::vector<Center2> candidate_centers = centers;
      std::vector<std::uint32_t> empty;
      for (std::uint32_t center = 0; center < centers.size(); ++center) {
        if (counts[center] == 0) {
          empty.push_back(center);
        } else {
          candidate_centers[center].x =
              sums_x[center] / static_cast<double>(counts[center]);
          candidate_centers[center].y =
              sums_y[center] / static_cast<double>(counts[center]);
          ValidateCenter(candidate_centers[center]);
        }
      }
      Assignment after = Assign(points, candidate_centers);
      trace.distance_comparison_count += after.comparisons;
      trace.assignment_tie_count += after.ties;
      const std::uint64_t changed = Changed(before.labels, after.labels);
      if (after.sse > before.sse) {
        trace.failure = BlockFailure::kSseIncrease;
        trace.final_centers = centers;
        trace.final_assignments = accepted.labels;
        trace.final_sse = accepted.sse;
        SerializeFailureState(&trace);
        return trace;
      }
      trace.steps.push_back(BlockStep{iteration,
                                      before.sse,
                                      after.sse,
                                      changed,
                                      std::move(empty),
                                      candidate_centers,
                                      before.labels,
                                      after.labels});
      centers = std::move(candidate_centers);
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
      trace.failure = BlockFailure::kIterationLimit;
      SerializeFailureState(&trace);
      return trace;
    }
    SerializeFinal(&trace);
    return trace;
  } catch (const Nonfinite&) {
    trace.failure = BlockFailure::kNonfinite;
    trace.final_centers = centers;
    if (has_accepted) {
      trace.final_assignments = accepted.labels;
      trace.final_sse = accepted.sse;
    } else {
      trace.initial_sse = std::numeric_limits<double>::infinity();
      trace.final_sse = std::numeric_limits<double>::infinity();
    }
    SerializeFailureState(&trace);
    return trace;
  }
}

void SetFailure(BlockResult* result, BlockFailure failure,
                std::uint32_t start_id, std::string detail) {
  if (result->failure == BlockFailure::kNone) {
    result->failure = failure;
    result->failed_start_id = start_id;
    result->failure_detail = std::move(detail);
  }
}

}  // namespace

Digest SelectionDigest(std::string_view hash_domain,
                       std::string_view dataset_id, std::uint64_t cell_id,
                       std::uint64_t vector_id) {
  return Hash(SelectionKey(hash_domain, dataset_id, cell_id, vector_id));
}

Digest StartDigest(const BlockMetadata& metadata, std::uint32_t start_id,
                   std::uint64_t cell_id, std::uint64_t vector_id) {
  return Hash(StartKey(metadata, start_id, cell_id, vector_id));
}

Point2 MakePoint(float x, float y, std::uint64_t cell_id,
                 std::uint64_t vector_id, std::string_view hash_domain,
                 std::string_view dataset_id) {
  if (!std::isfinite(x) || !std::isfinite(y)) {
    throw std::invalid_argument("block input must be finite binary32");
  }
  return Point2{x, y, cell_id, vector_id,
                SelectionDigest(hash_domain, dataset_id, cell_id, vector_id)};
}

std::vector<Point2> OrderPoints(const std::vector<Point2>& points,
                                std::string_view hash_domain,
                                std::string_view dataset_id) {
  if (points.empty()) {
    throw std::invalid_argument("empty block fit");
  }
  std::set<std::uint64_t> ids;
  std::vector<Point2> result = points;
  for (const Point2& point : result) {
    if (!ids.insert(point.vector_id).second ||
        point.selection_digest != SelectionDigest(
                                      hash_domain, dataset_id, point.cell_id,
                                      point.vector_id)) {
      throw std::invalid_argument("block row identity invalid");
    }
  }
  std::sort(result.begin(), result.end(), [](const Point2& lhs,
                                             const Point2& rhs) {
    if (lhs.cell_id != rhs.cell_id) return lhs.cell_id < rhs.cell_id;
    if (lhs.selection_digest != rhs.selection_digest) {
      return lhs.selection_digest < rhs.selection_digest;
    }
    return lhs.vector_id < rhs.vector_id;
  });
  return result;
}

SerializedCenter2 SerializeCenter(const Center2& center) {
  ValidateCenter(center);
  if (std::fegetround() != FE_TONEAREST) {
    throw std::runtime_error("block serialization requires FE_TONEAREST");
  }
  const float x = static_cast<float>(center.x);
  const float y = static_cast<float>(center.y);
  if (!std::isfinite(x) || !std::isfinite(y)) {
    throw Nonfinite("block center overflows binary32");
  }
  std::uint32_t xb = std::bit_cast<std::uint32_t>(x);
  std::uint32_t yb = std::bit_cast<std::uint32_t>(y);
  if ((xb & 0x7fffffffU) == 0) xb = 0;
  if ((yb & 0x7fffffffU) == 0) yb = 0;
  return SerializedCenter2{xb, yb};
}

BlockAssignmentTieFixture RunBlockAssignmentTieFixture() {
  const std::vector<Point2> points{
      Point2{0.0F, 0.0F, 0, 1, Digest{}}};
  const std::vector<Center2> centers{
      Center2{-1.0, 0.0}, Center2{1.0, 0.0}};
  const Assignment replay = Assign(points, centers);
  if (replay.labels.size() != 1) {
    throw std::logic_error("assignment-tie fixture shape mismatch");
  }
  return BlockAssignmentTieFixture{replay.labels[0], replay.sse,
                                   replay.comparisons, replay.ties};
}

BlockFarthestTieFixture RunBlockFarthestTieFixture() {
  Digest higher_digest{};
  higher_digest[0] = 1;
  const Digest lower_digest{};
  // Repeated vector ids are deliberately admitted only inside this bounded
  // primitive fixture, so the tertiary cell-id tie key is observable without
  // weakening OrderPoints' production uniqueness requirement.
  const std::vector<Point2> points{
      Point2{-1.0F, 0.0F, 9, 7, higher_digest},
      Point2{1.0F, 0.0F, 3, 7, lower_digest}};
  const std::vector<Center2> centers{Center2{0.0, 0.0}};
  std::uint64_t comparisons = 0;
  std::uint64_t ties = 0;
  const std::size_t selected =
      Farthest(points, centers, {}, &comparisons, &ties);
  if (comparisons != points.size()) {
    throw std::logic_error("farthest-tie fixture comparison mismatch");
  }
  return BlockFarthestTieFixture{points[selected].cell_id,
                                points[selected].vector_id, ties};
}

[[nodiscard]] BlockResult TrainBlockVqImpl(
    const std::vector<Point2>& points, const BlockMetadata& metadata,
    const std::vector<double>& axis0, const std::vector<double>& axis1,
    bool parity_capacity) {
  if (std::fegetround() != FE_TONEAREST ||
      (parity_capacity
           ? (metadata.capacity < 2 || metadata.capacity > 256)
           : (metadata.capacity != 16 && metadata.capacity != 256))) {
    throw std::invalid_argument("invalid frozen block environment/capacity");
  }
  BlockResult result;
  result.ordered_points =
      OrderPoints(points, metadata.hash_domain, metadata.dataset_id);
  if (metadata.capacity > result.ordered_points.size()) {
    throw std::invalid_argument("block capacity exceeds row count");
  }

  BlockStartTrace start0_seed;
  start0_seed.start_id = 0;
  std::vector<Center2> start0_centers;
  std::vector<std::uint16_t> start0_assignments;
  bool have_cartesian_sse = false;
  bool have_filled_sse = false;
  try {
    result.cartesian_centers = Cartesian(axis0, axis1, metadata.capacity);
    start0_centers = result.cartesian_centers;
    result.cartesian_sse =
        Assign(result.ordered_points, result.cartesian_centers).sse;
    have_cartesian_sse = true;
    FarthestFill(result.ordered_points, metadata.capacity, &start0_centers,
                 &start0_seed.initialization_vector_ids,
                 &start0_seed.distance_comparison_count,
                 &start0_seed.farthest_tie_count);
    const Assignment filled = Assign(result.ordered_points, start0_centers);
    result.filled_sse = filled.sse;
    have_filled_sse = true;
    start0_assignments = filled.labels;
    if (result.filled_sse > result.cartesian_sse) {
      start0_seed.failure = BlockFailure::kCartesianDominance;
      SetFailure(&result, BlockFailure::kCartesianDominance, 0,
                 "farthest fill exceeds Cartesian SSE");
    }
  } catch (const Nonfinite&) {
    start0_seed.failure = BlockFailure::kNonfinite;
    if (!have_cartesian_sse) {
      result.cartesian_sse = std::numeric_limits<double>::infinity();
    }
    if (!have_filled_sse) {
      result.filled_sse = std::numeric_limits<double>::infinity();
    }
    SetFailure(&result, BlockFailure::kNonfinite, 0,
               "nonfinite Cartesian initialization");
  }
  BlockStartTrace start0;
  if (start0_seed.failure == BlockFailure::kNone) {
    start0 = Lloyd(result.ordered_points, start0_centers,
                   std::move(start0_seed));
  } else {
    start0 = std::move(start0_seed);
    start0.initial_centers = start0_centers;
    start0.final_centers = start0_centers;
    start0.final_assignments = start0_assignments;
    start0.initial_sse = result.filled_sse;
    start0.final_sse = result.filled_sse;
    SerializeFailureState(&start0);
  }
  result.starts.push_back(std::move(start0));
  if (result.starts[0].failure != BlockFailure::kNone) {
    SetFailure(&result, result.starts[0].failure, 0,
               "start 0 control failure");
  } else if (result.starts[0].final_sse > result.cartesian_sse) {
    result.starts[0].failure = BlockFailure::kCartesianDominance;
    SetFailure(&result, BlockFailure::kCartesianDominance, 0,
               "start 0 final SSE exceeds Cartesian SSE");
  }

  for (std::uint32_t start_id = 1; start_id < kStartCount; ++start_id) {
    BlockStartTrace seed;
    seed.start_id = start_id;
    std::vector<Center2> centers;
    try {
      bool found = false;
      std::size_t first_row = 0;
      Digest first_digest{};
      std::uint64_t first_vector = 0;
      for (std::size_t row = 0; row < result.ordered_points.size(); ++row) {
        const Point2& point = result.ordered_points[row];
        const Digest digest = StartDigest(metadata, start_id, point.cell_id,
                                          point.vector_id);
        if (!found || digest < first_digest ||
            (digest == first_digest && point.vector_id < first_vector)) {
          found = true;
          first_row = row;
          first_digest = digest;
          first_vector = point.vector_id;
        }
      }
      seed.first_seed_digest = first_digest;
      seed.initialization_vector_ids.push_back(first_vector);
      centers = {CenterFromPoint(result.ordered_points[first_row])};
      FarthestFill(result.ordered_points, metadata.capacity, &centers,
                   &seed.initialization_vector_ids,
                   &seed.distance_comparison_count,
                   &seed.farthest_tie_count);
      seed = Lloyd(result.ordered_points, std::move(centers), std::move(seed));
    } catch (const Nonfinite&) {
      seed.failure = BlockFailure::kNonfinite;
      seed.initial_centers = centers;
      seed.final_centers = centers;
      seed.initial_sse = std::numeric_limits<double>::infinity();
      seed.final_sse = std::numeric_limits<double>::infinity();
      SerializeFailureState(&seed);
    }
    result.starts.push_back(std::move(seed));
    if (result.starts.back().failure != BlockFailure::kNone) {
      SetFailure(&result, result.starts.back().failure, start_id,
                 "salted start control failure");
    }
  }
  if (result.failure != BlockFailure::kNone) {
    return result;
  }
  std::size_t best = 0;
  for (std::size_t index = 1; index < result.starts.size(); ++index) {
    if (result.starts[index].final_sse < result.starts[best].final_sse) {
      best = index;
    }
  }
  if (result.starts[best].final_sse > result.cartesian_sse) {
    result.starts[best].failure = BlockFailure::kCartesianDominance;
    SetFailure(&result, BlockFailure::kCartesianDominance,
               result.starts[best].start_id,
               "best start exceeds Cartesian SSE");
    return result;
  }
  if (result.starts[best].distinct_serialized_center_count !=
      metadata.capacity) {
    result.starts[best].failure = BlockFailure::kSerializedCollision;
    SetFailure(&result, BlockFailure::kSerializedCollision,
               result.starts[best].start_id,
               "selected binary32 centers collide");
    return result;
  }
  result.control_valid = true;
  result.best_start_id = result.starts[best].start_id;
  return result;
}

BlockResult TrainBlockVq(const std::vector<Point2>& points,
                         const BlockMetadata& metadata,
                         const std::vector<double>& axis0,
                         const std::vector<double>& axis1) {
  return TrainBlockVqImpl(points, metadata, axis0, axis1, false);
}

BlockResult TrainBlockVqParity(const std::vector<Point2>& points,
                               const BlockMetadata& metadata,
                               const std::vector<double>& axis0,
                               const std::vector<double>& axis1) {
  return TrainBlockVqImpl(points, metadata, axis0, axis1, true);
}

}  // namespace saq::a4_v2::producer

#include "block_vq.hpp"

#include <openssl/sha.h>

#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_1s {
namespace {

constexpr std::uint32_t kStartCount = 8;
constexpr std::uint32_t kMaximumCompleteIterations = 300;

class NonfiniteBlockControl final : public std::runtime_error {
  public:
    explicit NonfiniteBlockControl(const char *message)
        : std::runtime_error(message) {}
};

void ValidateKeyField(std::string_view value, std::string_view name) {
    if (value.empty()) {
        throw std::invalid_argument(std::string(name) + " must not be empty");
    }
    if (value.find('|') != std::string_view::npos ||
        value.find('\n') != std::string_view::npos ||
        value.find('\r') != std::string_view::npos) {
        throw std::invalid_argument(std::string(name) +
                                    " contains a frozen-key delimiter");
    }
}

void ValidateMetadata(const BlockVqMetadata &metadata) {
    ValidateKeyField(metadata.protocol_version, "protocol_version");
    ValidateKeyField(metadata.dataset_id, "dataset_id");
    if (metadata.capacity == 0) {
        throw std::invalid_argument("block capacity must be positive");
    }
}

[[nodiscard]] Sha256Digest Sha256(std::string_view bytes) {
    Sha256Digest digest{};
    const auto *input =
        reinterpret_cast<const unsigned char *>(bytes.data());
    if (SHA256(input, bytes.size(), digest.data()) == nullptr) {
        throw std::runtime_error("OpenSSL SHA-256 failed");
    }
    return digest;
}

[[nodiscard]] std::string SelectionKey(std::string_view protocol_version,
                                       std::string_view dataset_id,
                                       std::uint64_t cell_id,
                                       std::uint64_t vector_id) {
    ValidateKeyField(protocol_version, "protocol_version");
    ValidateKeyField(dataset_id, "dataset_id");
    return std::string(protocol_version) + "|" + std::string(dataset_id) +
           "|" + std::to_string(cell_id) + "|" +
           std::to_string(vector_id);
}

[[nodiscard]] std::string StartKey(const BlockVqMetadata &metadata,
                                   std::uint32_t start_id,
                                   std::uint64_t cell_id,
                                   std::uint64_t vector_id) {
    ValidateMetadata(metadata);
    if (start_id >= kStartCount) {
        throw std::invalid_argument("block start id must be in [0,7]");
    }
    return metadata.protocol_version + "|" + metadata.dataset_id + "|" +
           std::to_string(metadata.capacity) + "|" +
           std::to_string(metadata.group_id) + "|" +
           std::to_string(start_id) + "|" + std::to_string(cell_id) + "|" +
           std::to_string(vector_id);
}

void ValidateCenter(const Center2 &center) {
    if (!std::isfinite(center.coordinate0) ||
        !std::isfinite(center.coordinate1)) {
        throw NonfiniteBlockControl("block center is nonfinite");
    }
}

[[nodiscard]] Center2 CenterFromPoint(const Point2 &point) noexcept {
    return Center2{static_cast<double>(point.coordinate0),
                   static_cast<double>(point.coordinate1)};
}

[[nodiscard]] double SquaredDistance(const Point2 &point,
                                     const Center2 &center) {
    const double difference0 =
        static_cast<double>(point.coordinate0) - center.coordinate0;
    const double square0 = difference0 * difference0;
    const double difference1 =
        static_cast<double>(point.coordinate1) - center.coordinate1;
    const double square1 = difference1 * difference1;
    const double distance = square0 + square1;
    if (!std::isfinite(distance) || distance < 0.0) {
        throw NonfiniteBlockControl("block squared distance is nonfinite");
    }
    return distance;
}

struct AssignmentReplay {
    std::vector<std::uint32_t> assignments;
    double sse{0.0};
    std::uint64_t distance_comparison_count{0};
    std::uint64_t tie_count{0};
};

// Both assignment and SSE accumulation follow the canonical fitting-row order.
// Center ids are visited in ascending order and replacement is strict, so an
// exact binary64 distance tie remains at the lower codeword id.
[[nodiscard]] AssignmentReplay AssignAndReplay(
    const std::vector<Point2> &ordered_points,
    const std::vector<Center2> &centers) {
    if (centers.empty()) {
        throw std::invalid_argument("block assignment requires a center");
    }
    for (const Center2 &center : centers) {
        ValidateCenter(center);
    }

    AssignmentReplay replay;
    replay.assignments.resize(ordered_points.size());
    for (std::size_t row = 0; row < ordered_points.size(); ++row) {
        std::uint32_t best_center = 0;
        double best_distance = SquaredDistance(ordered_points[row], centers[0]);
        ++replay.distance_comparison_count;
        for (std::uint32_t center = 1; center < centers.size(); ++center) {
            const double distance =
                SquaredDistance(ordered_points[row], centers[center]);
            ++replay.distance_comparison_count;
            if (distance < best_distance) {
                best_distance = distance;
                best_center = center;
            } else if (distance == best_distance) {
                ++replay.tie_count;
            }
        }
        replay.assignments[row] = best_center;
        replay.sse += best_distance;
        if (!std::isfinite(replay.sse)) {
            throw NonfiniteBlockControl("block SSE accumulation is nonfinite");
        }
    }
    return replay;
}

[[nodiscard]] std::size_t SelectFarthestPoint(
    const std::vector<Point2> &ordered_points,
    const std::vector<Center2> &centers,
    const std::set<std::uint64_t> &excluded_vector_ids,
    std::uint64_t *distance_comparison_count,
    std::uint64_t *tie_count) {
    if (centers.empty()) {
        throw std::invalid_argument("farthest selection requires a center");
    }
    bool found = false;
    std::size_t best_row = 0;
    double best_distance = 0.0;
    for (std::size_t row = 0; row < ordered_points.size(); ++row) {
        const Point2 &point = ordered_points[row];
        if (excluded_vector_ids.contains(point.vector_id)) {
            continue;
        }
        double nearest_distance = SquaredDistance(point, centers[0]);
        if (distance_comparison_count != nullptr) {
            ++*distance_comparison_count;
        }
        for (std::size_t center = 1; center < centers.size(); ++center) {
            const double distance = SquaredDistance(point, centers[center]);
            if (distance_comparison_count != nullptr) {
                ++*distance_comparison_count;
            }
            if (distance < nearest_distance) {
                nearest_distance = distance;
            }
        }
        if (found && nearest_distance == best_distance && tie_count != nullptr) {
            ++*tie_count;
        }
        bool tie_key_is_lower = false;
        if (found && nearest_distance == best_distance) {
            const Point2 &incumbent = ordered_points[best_row];
            // Frozen precedence is vector id first.  If a future semantic
            // fixture reuses a vector id, fall back to the complete registered
            // fitting-row tuple without weakening the production uniqueness
            // requirement.
            if (point.vector_id != incumbent.vector_id) {
                tie_key_is_lower = point.vector_id < incumbent.vector_id;
            } else if (point.cell_id != incumbent.cell_id) {
                tie_key_is_lower = point.cell_id < incumbent.cell_id;
            } else if (point.selection_digest != incumbent.selection_digest) {
                tie_key_is_lower =
                    point.selection_digest < incumbent.selection_digest;
            }
        }
        if (!found || nearest_distance > best_distance ||
            (nearest_distance == best_distance && tie_key_is_lower)) {
            found = true;
            best_row = row;
            best_distance = nearest_distance;
        }
    }
    if (!found) {
        throw std::invalid_argument(
            "not enough unique fitting rows to fill the block codebook");
    }
    return best_row;
}

void FarthestFill(const std::vector<Point2> &ordered_points,
                  std::uint32_t capacity,
                  std::vector<Center2> *centers,
                  std::vector<std::uint64_t> *selected_vector_ids,
                  std::uint64_t *distance_comparison_count,
                  std::uint64_t *tie_count) {
    if (centers == nullptr || selected_vector_ids == nullptr ||
        centers->empty() || centers->size() > capacity) {
        throw std::invalid_argument("invalid farthest-fill state");
    }
    std::set<std::uint64_t> excluded(selected_vector_ids->begin(),
                                     selected_vector_ids->end());
    while (centers->size() < capacity) {
        const std::size_t row =
            SelectFarthestPoint(ordered_points, *centers, excluded,
                                distance_comparison_count, tie_count);
        const std::uint64_t vector_id = ordered_points[row].vector_id;
        centers->push_back(CenterFromPoint(ordered_points[row]));
        selected_vector_ids->push_back(vector_id);
        excluded.insert(vector_id);
    }
}

[[nodiscard]] std::vector<Center2> BuildCartesianCenters(
    const std::vector<double> &axis0,
    const std::vector<double> &axis1,
    std::uint32_t capacity) {
    if (axis0.empty() || axis1.empty()) {
        throw std::invalid_argument("start-0 scalar axes must be nonempty");
    }
    for (const std::vector<double> *axis : {&axis0, &axis1}) {
        for (std::size_t index = 0; index < axis->size(); ++index) {
            if (!std::isfinite((*axis)[index])) {
                throw NonfiniteBlockControl(
                    "start-0 scalar center is nonfinite");
            }
            if (index > 0 && !((*axis)[index - 1] < (*axis)[index])) {
                throw std::invalid_argument(
                    "start-0 scalar centers must be strictly increasing");
            }
        }
    }
    const std::uint64_t product =
        static_cast<std::uint64_t>(axis0.size()) * axis1.size();
    if (product > capacity) {
        throw std::invalid_argument(
            "start-0 Cartesian product exceeds block capacity");
    }

    std::vector<Center2> centers;
    centers.reserve(static_cast<std::size_t>(capacity));
    // u=z0+K0*z1: z0 is the inner/fast mixed-radix coordinate.
    for (const double coordinate1 : axis1) {
        for (const double coordinate0 : axis0) {
            centers.push_back(Center2{coordinate0, coordinate1});
        }
    }
    return centers;
}

[[nodiscard]] std::pair<std::vector<Center2>, BlockVqStartTrace>
BuildSaltedFarthestStart(const std::vector<Point2> &ordered_points,
                         const BlockVqMetadata &metadata,
                         std::uint32_t start_id) {
    if (start_id == 0 || start_id >= kStartCount) {
        throw std::invalid_argument("salted starts are numbered 1 through 7");
    }
    bool found = false;
    std::size_t first_row = 0;
    Sha256Digest first_digest{};
    std::uint64_t first_vector_id = 0;
    for (std::size_t row = 0; row < ordered_points.size(); ++row) {
        const Point2 &point = ordered_points[row];
        const Sha256Digest digest = ComputeBlockStartDigest(
            metadata, start_id, point.cell_id, point.vector_id);
        if (!found || digest < first_digest ||
            (digest == first_digest && point.vector_id < first_vector_id)) {
            found = true;
            first_row = row;
            first_digest = digest;
            first_vector_id = point.vector_id;
        }
    }
    if (!found) {
        throw std::invalid_argument("block fitting inventory must not be empty");
    }

    BlockVqStartTrace trace;
    trace.start_id = start_id;
    trace.first_seed_digest = first_digest;
    trace.selected_vector_ids.push_back(first_vector_id);
    std::vector<Center2> centers{CenterFromPoint(ordered_points[first_row])};
    FarthestFill(ordered_points, metadata.capacity, &centers,
                 &trace.selected_vector_ids,
                 &trace.distance_comparison_count,
                 &trace.farthest_tie_count);
    return {std::move(centers), std::move(trace)};
}

[[nodiscard]] std::uint64_t ChangedAssignmentCount(
    const std::vector<std::uint32_t> &before,
    const std::vector<std::uint32_t> &after) {
    if (before.size() != after.size()) {
        throw std::logic_error("assignment vectors have different sizes");
    }
    std::uint64_t changed = 0;
    for (std::size_t index = 0; index < before.size(); ++index) {
        if (before[index] != after[index]) {
            ++changed;
        }
    }
    return changed;
}

void RecordSerializedCenters(BlockVqStartTrace *trace) {
    if (trace == nullptr) {
        throw std::invalid_argument("missing block start trace");
    }
    trace->serialized_final_centers.clear();
    trace->serialized_final_centers.reserve(trace->final_centers.size());
    std::set<SerializedCenter2> distinct;
    for (const Center2 &center : trace->final_centers) {
        const SerializedCenter2 serialized = SerializeCenterBinary32(center);
        trace->serialized_final_centers.push_back(serialized);
        distinct.insert(serialized);
    }
    trace->distinct_serialized_center_count = distinct.size();
}

[[nodiscard]] BlockVqStartTrace RunLloyd(
    const std::vector<Point2> &ordered_points,
    std::vector<Center2> initial_centers,
    BlockVqStartTrace trace) {
    trace.initial_centers = initial_centers;
    std::vector<Center2> current_centers = std::move(initial_centers);
    AssignmentReplay accepted;
    bool has_accepted_state = false;
    try {
        accepted = AssignAndReplay(ordered_points, current_centers);
        has_accepted_state = true;
        trace.distance_comparison_count += accepted.distance_comparison_count;
        trace.assignment_tie_count += accepted.tie_count;
        trace.initial_sse = accepted.sse;

        for (std::uint32_t iteration = 1;
             iteration <= kMaximumCompleteIterations;
             ++iteration) {
        // Step 1 is deliberately replayed even though the preceding accepted
        // state is available: the frozen algorithm defines every complete
        // step from a direct row-order assignment.
            const AssignmentReplay before =
                AssignAndReplay(ordered_points, current_centers);
            trace.distance_comparison_count += before.distance_comparison_count;
            trace.assignment_tie_count += before.tie_count;

            std::vector<double> sums0(current_centers.size(), 0.0);
            std::vector<double> sums1(current_centers.size(), 0.0);
            std::vector<std::uint64_t> counts(current_centers.size(), 0);
            for (std::size_t row = 0; row < ordered_points.size(); ++row) {
                const std::uint32_t center = before.assignments[row];
                sums0[center] +=
                    static_cast<double>(ordered_points[row].coordinate0);
                sums1[center] +=
                    static_cast<double>(ordered_points[row].coordinate1);
                ++counts[center];
            }

            std::vector<Center2> candidate_centers = current_centers;
            std::vector<std::uint32_t> empty_centers;
            for (std::uint32_t center = 0; center < candidate_centers.size();
                 ++center) {
                if (counts[center] == 0) {
                    empty_centers.push_back(center); // Retain previous center.
                    continue;
                }
                candidate_centers[center].coordinate0 =
                    sums0[center] / static_cast<double>(counts[center]);
                candidate_centers[center].coordinate1 =
                    sums1[center] / static_cast<double>(counts[center]);
                ValidateCenter(candidate_centers[center]);
            }

            AssignmentReplay candidate =
                AssignAndReplay(ordered_points, candidate_centers);
            trace.distance_comparison_count +=
                candidate.distance_comparison_count;
            trace.assignment_tie_count += candidate.tie_count;
            const std::uint64_t changed = ChangedAssignmentCount(
                before.assignments, candidate.assignments);

            // A numerically increasing candidate is a failed control, not an
            // accepted Lloyd step.  Keep the last accepted state and do not
            // let the rejected candidate enter the schema-1 step inventory or
            // accepted-iteration count.
            if (candidate.sse > before.sse) {
                trace.failure = BlockVqFailure::kCandidateSseIncrease;
                trace.final_centers = std::move(current_centers);
                trace.final_assignments = std::move(accepted.assignments);
                trace.final_sse = accepted.sse;
                return trace;
            }

            trace.steps.push_back(LloydStepTrace{
                iteration,
                before.sse,
                candidate.sse,
                changed,
                std::move(empty_centers),
                candidate_centers});
            trace.complete_iterations = iteration;

            current_centers = std::move(candidate_centers);
            accepted = std::move(candidate);
            if (changed == 0) {
                trace.converged = true;
                break;
            }
        }

        trace.final_centers = std::move(current_centers);
        trace.final_assignments = std::move(accepted.assignments);
        trace.final_sse = accepted.sse;
        if (!trace.converged) {
            trace.failure = BlockVqFailure::kIterationLimit;
            return trace;
        }
        // Every start records its runtime-facing serialization for attribution.
        // Distinctness is a gate only for the selected winner, after all eight
        // final direct-replay SSE values participate in best-start choice.
        RecordSerializedCenters(&trace);
        return trace;
    } catch (const NonfiniteBlockControl &) {
        trace.failure = BlockVqFailure::kNonfiniteControl;
        if (trace.final_centers.empty()) {
            trace.final_centers = std::move(current_centers);
        }
        if (has_accepted_state) {
            if (trace.final_assignments.empty()) {
                trace.final_assignments = std::move(accepted.assignments);
                trace.final_sse = accepted.sse;
            }
        } else {
            trace.final_sse = std::numeric_limits<double>::infinity();
        }
        return trace;
    }
}

void SetFailure(BlockVqTrainingResult *result,
                BlockVqFailure failure,
                std::uint32_t start_id,
                std::string detail) {
    if (result->failure != BlockVqFailure::kNone) {
        return; // Preserve the lowest-start/earliest frozen control failure.
    }
    result->control_valid = false;
    result->failure = failure;
    result->failed_start_id = start_id;
    result->failure_detail = std::move(detail);
}

} // namespace

Sha256Digest ComputeSelectionDigest(std::string_view protocol_version,
                                    std::string_view dataset_id,
                                    std::uint64_t cell_id,
                                    std::uint64_t vector_id) {
    return Sha256(
        SelectionKey(protocol_version, dataset_id, cell_id, vector_id));
}

Sha256Digest ComputeBlockStartDigest(const BlockVqMetadata &metadata,
                                     std::uint32_t start_id,
                                     std::uint64_t cell_id,
                                     std::uint64_t vector_id) {
    return Sha256(StartKey(metadata, start_id, cell_id, vector_id));
}

Point2 MakePoint2(float coordinate0,
                  float coordinate1,
                  std::uint64_t cell_id,
                  std::uint64_t vector_id,
                  std::string_view protocol_version,
                  std::string_view dataset_id) {
    if (!std::isfinite(coordinate0) || !std::isfinite(coordinate1)) {
        throw std::invalid_argument("block fitting coordinates must be finite");
    }
    return Point2{coordinate0,
                  coordinate1,
                  cell_id,
                  vector_id,
                  ComputeSelectionDigest(
                      protocol_version, dataset_id, cell_id, vector_id)};
}

std::vector<Point2> OrderAndValidatePoints(
    const std::vector<Point2> &points,
    std::string_view protocol_version,
    std::string_view dataset_id) {
    ValidateKeyField(protocol_version, "protocol_version");
    ValidateKeyField(dataset_id, "dataset_id");
    if (points.empty()) {
        throw std::invalid_argument("block fitting inventory must not be empty");
    }

    std::set<std::uint64_t> vector_ids;
    std::vector<Point2> ordered = points;
    for (const Point2 &point : ordered) {
        if (!std::isfinite(point.coordinate0) ||
            !std::isfinite(point.coordinate1)) {
            throw std::invalid_argument(
                "block fitting coordinates must be finite binary32");
        }
        const Sha256Digest expected = ComputeSelectionDigest(
            protocol_version, dataset_id, point.cell_id, point.vector_id);
        if (point.selection_digest != expected) {
            throw std::invalid_argument("point selection SHA-256 mismatch");
        }
        if (!vector_ids.insert(point.vector_id).second) {
            throw std::invalid_argument(
                "block fitting vector ids must be globally unique");
        }
    }
    std::sort(ordered.begin(), ordered.end(),
              [](const Point2 &lhs, const Point2 &rhs) {
                  if (lhs.cell_id != rhs.cell_id) {
                      return lhs.cell_id < rhs.cell_id;
                  }
                  if (lhs.selection_digest != rhs.selection_digest) {
                      return lhs.selection_digest < rhs.selection_digest;
                  }
                  return lhs.vector_id < rhs.vector_id;
              });
    return ordered;
}

SerializedCenter2 SerializeCenterBinary32(const Center2 &center) {
    ValidateCenter(center);
    if (std::fegetround() != FE_TONEAREST) {
        throw std::runtime_error(
            "binary32 center serialization requires FE_TONEAREST");
    }
    const float coordinate0 = static_cast<float>(center.coordinate0);
    const float coordinate1 = static_cast<float>(center.coordinate1);
    if (!std::isfinite(coordinate0) || !std::isfinite(coordinate1)) {
        throw NonfiniteBlockControl("block center overflows binary32");
    }
    std::uint32_t bits0 = std::bit_cast<std::uint32_t>(coordinate0);
    std::uint32_t bits1 = std::bit_cast<std::uint32_t>(coordinate1);
    if ((bits0 & 0x7fffffffU) == 0) {
        bits0 = 0;
    }
    if ((bits1 & 0x7fffffffU) == 0) {
        bits1 = 0;
    }
    return SerializedCenter2{bits0, bits1};
}

BlockAssignmentTieMicrofixtureResult
RunBlockAssignmentTieMicrofixture() {
    const std::vector<Point2> points{
        Point2{0.0F, 0.0F, 0, 1, Sha256Digest{}}};
    const std::vector<Center2> centers{
        Center2{-1.0, 0.0}, Center2{1.0, 0.0}};
    const AssignmentReplay replay = AssignAndReplay(points, centers);
    if (replay.assignments.size() != 1) {
        throw std::logic_error(
            "block assignment tie microfixture produced invalid shape");
    }
    return BlockAssignmentTieMicrofixtureResult{
        replay.assignments[0], replay.sse,
        replay.distance_comparison_count, replay.tie_count};
}

BlockFarthestFallbackMicrofixtureResult
RunBlockFarthestFallbackMicrofixture() {
    Sha256Digest high_digest{};
    high_digest[0] = 1;
    Sha256Digest low_digest{};
    const std::vector<Point2> points{
        Point2{-1.0F, 0.0F, 9, 7, high_digest},
        Point2{1.0F, 0.0F, 3, 7, low_digest}};
    const std::vector<Center2> centers{Center2{0.0, 0.0}};
    std::uint64_t comparisons = 0;
    std::uint64_t ties = 0;
    const std::size_t selected = SelectFarthestPoint(
        points, centers, {}, &comparisons, &ties);
    if (comparisons != 2) {
        throw std::logic_error(
            "block farthest fallback microfixture comparison mismatch");
    }
    return BlockFarthestFallbackMicrofixtureResult{
        points[selected].cell_id, points[selected].vector_id, ties};
}

BlockVqTrainingResult TrainFrozenBlockVq(
    const std::vector<Point2> &points,
    const BlockVqMetadata &metadata,
    const std::vector<double> &start0_axis0,
    const std::vector<double> &start0_axis1) {
    ValidateMetadata(metadata);
    if (std::fegetround() != FE_TONEAREST) {
        throw std::runtime_error("block training requires FE_TONEAREST");
    }
    const std::vector<Point2> ordered = OrderAndValidatePoints(
        points, metadata.protocol_version, metadata.dataset_id);
    if (metadata.capacity > ordered.size()) {
        throw std::invalid_argument(
            "block capacity exceeds the unique fitting-row count");
    }

    BlockVqTrainingResult result;
    result.ordered_vector_ids.reserve(ordered.size());
    result.ordered_selection_digests.reserve(ordered.size());
    for (const Point2 &point : ordered) {
        result.ordered_vector_ids.push_back(point.vector_id);
        result.ordered_selection_digests.push_back(point.selection_digest);
    }

    result.starts.reserve(kStartCount);
    BlockVqStartTrace start0_seed_trace;
    start0_seed_trace.start_id = 0;
    std::vector<Center2> start0_centers;
    AssignmentReplay filled;
    bool filled_state_available = false;
    try {
        result.start0_cartesian_centers = BuildCartesianCenters(
            start0_axis0, start0_axis1, metadata.capacity);
        start0_centers = result.start0_cartesian_centers;
        const AssignmentReplay cartesian =
            AssignAndReplay(ordered, result.start0_cartesian_centers);
        result.start0_cartesian_sse = cartesian.sse;

        FarthestFill(ordered, metadata.capacity, &start0_centers,
                     &start0_seed_trace.selected_vector_ids,
                     &start0_seed_trace.distance_comparison_count,
                     &start0_seed_trace.farthest_tie_count);
        filled = AssignAndReplay(ordered, start0_centers);
        filled_state_available = true;
        result.start0_filled_sse = filled.sse;
        if (filled.sse > cartesian.sse) {
            start0_seed_trace.failure = BlockVqFailure::kCartesianDominance;
            SetFailure(
                &result, BlockVqFailure::kCartesianDominance, 0,
                "start-0 farthest fill increased direct Cartesian SSE");
        }
    } catch (const NonfiniteBlockControl &) {
        result.start0_cartesian_sse =
            std::numeric_limits<double>::infinity();
        result.start0_filled_sse =
            std::numeric_limits<double>::infinity();
        start0_seed_trace.failure = BlockVqFailure::kNonfiniteControl;
        SetFailure(&result, BlockVqFailure::kNonfiniteControl, 0,
                   "nonfinite block value in start-0 initialization");
    }

    BlockVqStartTrace start0;
    if (start0_seed_trace.failure == BlockVqFailure::kNone) {
        start0 = RunLloyd(ordered, std::move(start0_centers),
                          std::move(start0_seed_trace));
    } else {
        start0 = std::move(start0_seed_trace);
        start0.initial_centers = start0_centers;
        start0.final_centers = start0_centers;
        if (filled_state_available) {
            start0.initial_sse = filled.sse;
            start0.final_assignments = std::move(filled.assignments);
            start0.final_sse = filled.sse;
        } else {
            start0.initial_sse = std::numeric_limits<double>::infinity();
            start0.final_sse = std::numeric_limits<double>::infinity();
        }
    }
    result.starts.push_back(std::move(start0));
    if (result.starts.back().failure != BlockVqFailure::kNone) {
        SetFailure(&result, result.starts.back().failure, 0,
                   "frozen Lloyd/control failure in start 0");
    } else if (result.starts.back().final_sse >
               result.start0_cartesian_sse) {
        result.starts.back().failure = BlockVqFailure::kCartesianDominance;
        SetFailure(&result, BlockVqFailure::kCartesianDominance, 0,
                   "start-0 final SSE exceeds direct Cartesian replay");
    }

    for (std::uint32_t start_id = 1; start_id < kStartCount; ++start_id) {
        BlockVqStartTrace trace;
        trace.start_id = start_id;
        try {
            auto [initial_centers, seed_trace] =
                BuildSaltedFarthestStart(ordered, metadata, start_id);
            trace = RunLloyd(ordered, std::move(initial_centers),
                             std::move(seed_trace));
        } catch (const NonfiniteBlockControl &) {
            trace.failure = BlockVqFailure::kNonfiniteControl;
            trace.initial_sse = std::numeric_limits<double>::infinity();
            trace.final_sse = std::numeric_limits<double>::infinity();
        }
        result.starts.push_back(std::move(trace));
        if (result.starts.back().failure != BlockVqFailure::kNone) {
            SetFailure(&result, result.starts.back().failure, start_id,
                       "frozen Lloyd/control failure in salted start");
        }
    }

    if (result.starts.size() != kStartCount) {
        throw std::logic_error("block trainer did not record all eight starts");
    }
    if (result.failure != BlockVqFailure::kNone) {
        return result; // Best-of-eight is undefined unless every control passed.
    }

    std::size_t best_index = 0;
    for (std::size_t index = 1; index < result.starts.size(); ++index) {
        // Starts are stored in start-id order.  Strict replacement therefore
        // keeps the lower id on an exact binary64 final-SSE tie.
        if (result.starts[index].final_sse <
            result.starts[best_index].final_sse) {
            best_index = index;
        }
    }
    if (result.starts[best_index].final_sse > result.start0_cartesian_sse) {
        SetFailure(&result, BlockVqFailure::kCartesianDominance,
                   result.starts[best_index].start_id,
                   "best block start does not dominate Cartesian replay");
        return result;
    }

    if (result.starts[best_index].distinct_serialized_center_count !=
        metadata.capacity) {
        result.starts[best_index].failure =
            BlockVqFailure::kSerializedCenterCollision;
        SetFailure(&result, BlockVqFailure::kSerializedCenterCollision,
                   result.starts[best_index].start_id,
                   "selected block start has colliding binary32 centers");
        return result;
    }

    const BlockVqStartTrace &best = result.starts[best_index];
    result.best_start_id = best.start_id;
    result.best_centers = best.final_centers;
    result.best_assignments = best.final_assignments;
    result.best_sse = best.final_sse;
    result.best_serialized_centers = best.serialized_final_centers;
    result.control_valid = true;
    result.failure = BlockVqFailure::kNone;
    result.failure_detail.clear();
    return result;
}

} // namespace saq::a4_1s

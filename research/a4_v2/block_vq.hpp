#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace saq::a4_v2::producer {

using Digest = std::array<std::uint8_t, 32>;

struct BlockMetadata {
  std::string hash_domain;
  std::string dataset_id;
  std::uint32_t capacity{0};
  std::uint32_t group_id{0};
};

struct Point2 {
  float x{0.0F};
  float y{0.0F};
  std::uint64_t cell_id{0};
  std::uint64_t vector_id{0};
  Digest selection_digest{};
};

struct Center2 {
  double x{0.0};
  double y{0.0};
};

struct SerializedCenter2 {
  std::uint32_t x_bits{0};
  std::uint32_t y_bits{0};
  friend bool operator==(const SerializedCenter2&,
                         const SerializedCenter2&) = default;
  friend bool operator<(const SerializedCenter2& lhs,
                        const SerializedCenter2& rhs) noexcept {
    return lhs.x_bits != rhs.x_bits ? lhs.x_bits < rhs.x_bits
                                    : lhs.y_bits < rhs.y_bits;
  }
};

enum class BlockFailure {
  kNone,
  kNonfinite,
  kSseIncrease,
  kIterationLimit,
  kSerializedCollision,
  kCartesianDominance,
};

struct BlockStep {
  std::uint32_t iteration{0};
  double prior_sse{0.0};
  double candidate_sse{0.0};
  std::uint64_t changed_assignment_count{0};
  std::vector<std::uint32_t> empty_center_ids;
  std::vector<Center2> centers_after;

  // V2 retains these scientific preimages in C_core.  E_emit may hash them
  // as unsigned little-endian uint16 labels but may not recompute assignments.
  std::vector<std::uint16_t> assignments_before;
  std::vector<std::uint16_t> assignments_after;
};

struct BlockStartTrace {
  std::uint32_t start_id{0};
  Digest first_seed_digest{};
  std::vector<std::uint64_t> initialization_vector_ids;
  std::uint64_t distance_comparison_count{0};
  std::uint64_t assignment_tie_count{0};
  std::uint64_t farthest_tie_count{0};
  std::vector<Center2> initial_centers;
  double initial_sse{0.0};
  std::vector<BlockStep> steps;
  bool converged{false};
  BlockFailure failure{BlockFailure::kNone};
  std::vector<Center2> final_centers;
  std::vector<std::uint16_t> final_assignments;
  double final_sse{0.0};
  std::vector<SerializedCenter2> serialized_final_centers;
  std::uint32_t distinct_serialized_center_count{0};
};

struct BlockResult {
  bool control_valid{false};
  BlockFailure failure{BlockFailure::kNone};
  std::uint32_t failed_start_id{0};
  std::string failure_detail;
  std::vector<Point2> ordered_points;
  std::vector<Center2> cartesian_centers;
  double cartesian_sse{0.0};
  double filled_sse{0.0};
  std::vector<BlockStartTrace> starts;
  std::uint32_t best_start_id{0};
};

// Bounded PAR fixtures which exercise the production block primitives rather
// than a second representation-layer implementation.
struct BlockAssignmentTieFixture {
  std::uint32_t selected_codeword{0};
  double sse{0.0};
  std::uint64_t distance_comparison_count{0};
  std::uint64_t tie_count{0};
};

struct BlockFarthestTieFixture {
  std::uint64_t selected_cell_id{0};
  std::uint64_t selected_vector_id{0};
  std::uint64_t tie_count{0};
};

[[nodiscard]] Digest SelectionDigest(std::string_view hash_domain,
                                     std::string_view dataset_id,
                                     std::uint64_t cell_id,
                                     std::uint64_t vector_id);
[[nodiscard]] Digest StartDigest(const BlockMetadata& metadata,
                                 std::uint32_t start_id,
                                 std::uint64_t cell_id,
                                 std::uint64_t vector_id);
[[nodiscard]] Point2 MakePoint(float x, float y, std::uint64_t cell_id,
                               std::uint64_t vector_id,
                               std::string_view hash_domain,
                               std::string_view dataset_id);
[[nodiscard]] std::vector<Point2> OrderPoints(
    const std::vector<Point2>& points, std::string_view hash_domain,
    std::string_view dataset_id);
[[nodiscard]] SerializedCenter2 SerializeCenter(const Center2& center);
[[nodiscard]] BlockAssignmentTieFixture RunBlockAssignmentTieFixture();
[[nodiscard]] BlockFarthestTieFixture RunBlockFarthestTieFixture();
[[nodiscard]] BlockResult TrainBlockVq(
    const std::vector<Point2>& points, const BlockMetadata& metadata,
    const std::vector<double>& axis0, const std::vector<double>& axis1);
// PAR-only bounded fixture surface.  Production evidence remains restricted
// to the frozen B4/B8 capacities through TrainBlockVq.
[[nodiscard]] BlockResult TrainBlockVqParity(
    const std::vector<Point2>& points, const BlockMetadata& metadata,
    const std::vector<double>& axis0, const std::vector<double>& axis1);

}  // namespace saq::a4_v2::producer

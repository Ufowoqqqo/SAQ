#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace saq::a4_1s {

using Sha256Digest = std::array<std::uint8_t, 32>;

struct BlockVqMetadata {
    std::string protocol_version;
    std::string dataset_id;
    std::uint32_t capacity{0};
    std::uint32_t group_id{0};
};

// Coordinates are stored as binary32 because every registered fitting row is
// a pair of binary32 residuals.  All block operations promote them directly
// to binary64; no other input precision is admitted.
struct Point2 {
    float coordinate0{0.0F};
    float coordinate1{0.0F};
    std::uint64_t cell_id{0};
    std::uint64_t vector_id{0};
    Sha256Digest selection_digest{};
};

struct Center2 {
    double coordinate0{0.0};
    double coordinate1{0.0};
};

struct SerializedCenter2 {
    std::uint32_t coordinate0_bits{0};
    std::uint32_t coordinate1_bits{0};

    friend bool operator==(const SerializedCenter2 &,
                           const SerializedCenter2 &) = default;
    friend bool operator<(const SerializedCenter2 &lhs,
                          const SerializedCenter2 &rhs) noexcept {
        if (lhs.coordinate0_bits != rhs.coordinate0_bits) {
            return lhs.coordinate0_bits < rhs.coordinate0_bits;
        }
        return lhs.coordinate1_bits < rhs.coordinate1_bits;
    }
};

enum class BlockVqFailure {
    kNone,
    kNonfiniteControl,
    kCandidateSseIncrease,
    kIterationLimit,
    kSerializedCenterCollision,
    kCartesianDominance,
};

struct BlockAssignmentTieMicrofixtureResult {
    std::uint32_t selected_codeword{0};
    double sse{0.0};
    std::uint64_t distance_comparison_count{0};
    std::uint64_t tie_count{0};
};

struct BlockFarthestFallbackMicrofixtureResult {
    std::uint64_t selected_cell_id{0};
    std::uint64_t selected_vector_id{0};
    std::uint64_t tie_count{0};
};

struct LloydStepTrace {
    std::uint32_t iteration{0};
    double prior_sse{0.0};
    double candidate_sse{0.0};
    std::uint64_t changed_assignment_count{0};
    std::vector<std::uint32_t> empty_center_ids;
    // The accepted center state after this complete step.  Final assignments
    // are stored once at the start level to keep the trace bounded.
    std::vector<Center2> centers_after;
};

struct BlockVqStartTrace {
    std::uint32_t start_id{0};
    Sha256Digest first_seed_digest{}; // Zero for Cartesian start 0.

    // For start 0 this contains only vector ids appended by the farthest
    // fill.  For starts 1..7 it contains all farthest-first seed ids.
    std::vector<std::uint64_t> selected_vector_ids;
    std::uint64_t distance_comparison_count{0};
    std::uint64_t assignment_tie_count{0};
    std::uint64_t farthest_tie_count{0};
    std::vector<Center2> initial_centers;
    double initial_sse{0.0};

    std::vector<LloydStepTrace> steps;
    std::uint32_t complete_iterations{0};
    bool converged{false};
    BlockVqFailure failure{BlockVqFailure::kNone};

    std::vector<Center2> final_centers;
    std::vector<std::uint32_t> final_assignments;
    double final_sse{0.0};
    std::vector<SerializedCenter2> serialized_final_centers;
    std::size_t distinct_serialized_center_count{0};
};

struct BlockVqTrainingResult {
    bool control_valid{false};
    BlockVqFailure failure{BlockVqFailure::kNone};
    std::uint32_t failed_start_id{0};
    std::string failure_detail;

    // Canonical fitting-row order and identities used by every operation.
    std::vector<std::uint64_t> ordered_vector_ids;
    std::vector<Sha256Digest> ordered_selection_digests;

    // Start-0 Cartesian codewords use u=z0+K0*z1.  The first SSE is replayed
    // before fill; the second after deterministic farthest fill.
    std::vector<Center2> start0_cartesian_centers;
    double start0_cartesian_sse{0.0};
    double start0_filled_sse{0.0};

    std::vector<BlockVqStartTrace> starts;
    std::uint32_t best_start_id{0};
    std::vector<Center2> best_centers;
    std::vector<std::uint32_t> best_assignments;
    double best_sse{0.0};
    std::vector<SerializedCenter2> best_serialized_centers;
};

// UTF-8 bytes of the exact no-brace/no-newline templates are hashed.  Numeric
// fields use std::to_string's canonical unsigned decimal representation.
[[nodiscard]] Sha256Digest ComputeSelectionDigest(
    std::string_view protocol_version,
    std::string_view dataset_id,
    std::uint64_t cell_id,
    std::uint64_t vector_id);

[[nodiscard]] Sha256Digest ComputeBlockStartDigest(
    const BlockVqMetadata &metadata,
    std::uint32_t start_id,
    std::uint64_t cell_id,
    std::uint64_t vector_id);

[[nodiscard]] Point2 MakePoint2(float coordinate0,
                                float coordinate1,
                                std::uint64_t cell_id,
                                std::uint64_t vector_id,
                                std::string_view protocol_version,
                                std::string_view dataset_id);

// Validate every selection identity, require globally unique vector ids, and
// order by (cell_id, raw selection digest bytes, vector_id).
[[nodiscard]] std::vector<Point2> OrderAndValidatePoints(
    const std::vector<Point2> &points,
    std::string_view protocol_version,
    std::string_view dataset_id);

// Serialize one binary64 center by an independent binary64-to-binary32 RNE
// conversion per coordinate.  Signed zero is canonicalized to +0 because
// +/-0 are the same reconstruction and must not evade the distinctness gate.
[[nodiscard]] SerializedCenter2 SerializeCenterBinary32(const Center2 &center);

// Exercise the block trainer's actual assignment/replay implementation with
// one point exactly equidistant from codewords 0 and 1.  This is deliberately
// separate from the representation-layer assignment helper.
[[nodiscard]] BlockAssignmentTieMicrofixtureResult
RunBlockAssignmentTieMicrofixture();

// Exercise the repeated-vector-id fallback of the frozen farthest tie key
// without relaxing OrderAndValidatePoints' production uniqueness contract.
[[nodiscard]] BlockFarthestFallbackMicrofixtureResult
RunBlockFarthestFallbackMicrofixture();

// Run all eight frozen starts.  start0_axis0/axis1 must already be the exact
// arbitrary-word means rounded directly to binary64.  Their Cartesian product
// is constructed in mixed-radix order u=z0+K0*z1, filled to capacity by the
// frozen farthest rule, and used as start 0.  Starts 1..7 use their salted hash
// first seed and deterministic farthest-first completion.
//
// Invalid metadata and malformed inputs are implementation errors and throw.
// Nonfinite arithmetic and other frozen Lloyd/control failures are returned as
// control_valid=false.  Independent starts continue so all eight traces are
// recorded whenever their initialization remains feasible.
[[nodiscard]] BlockVqTrainingResult TrainFrozenBlockVq(
    const std::vector<Point2> &points,
    const BlockVqMetadata &metadata,
    const std::vector<double> &start0_axis0,
    const std::vector<double> &start0_axis1);

} // namespace saq::a4_1s

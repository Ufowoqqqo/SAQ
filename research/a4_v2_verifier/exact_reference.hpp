#pragma once

#include <gmpxx.h>

#include <cstdint>
#include <vector>

namespace saq::a4_v2::verifier {

struct ExactValue {
  mpz_class numerator{0};
  mpz_class denominator{1};
  int binary_grid_exponent{0};
  ExactValue() = default;
  ExactValue(mpz_class numerator_in, mpz_class denominator_in, int exponent);
  [[nodiscard]] mpq_class coefficient() const;
};

struct ExactInterval {
  std::uint32_t begin{0};
  std::uint32_t end{0};
  ExactValue mean;
};

struct ExactSolution {
  std::uint32_t requested_cardinality{0};
  std::uint32_t effective_cardinality{0};
  ExactValue sse;
  std::vector<ExactInterval> intervals;
  // Counter-only replay of the preregistered producer schedule.  These
  // values never select an objective, predecessor, or serialized centroid.
  std::uint64_t registered_comparison_count{0};
  std::uint64_t registered_tie_count{0};
};

struct ExactSupport {
  mpz_class grid_integer{0};
  mpz_class weight{0};
  std::uint64_t lowest_vector_id{0};
};

struct ExactCurve {
  std::vector<ExactSupport> support;
  std::vector<ExactSolution> solutions;
  std::vector<std::vector<std::uint32_t>> predecessors;
  [[nodiscard]] const ExactSolution& at(std::uint32_t cardinality) const;
};

struct WeightedExactSample {
  std::uint32_t binary32_bits{0};
  std::uint64_t weight{0};
  std::uint64_t vector_id{0};
};

enum class CardinalityDomain { kAllPositive, kPowersOfTwo };

struct ProductDecision {
  std::uint32_t first{0};
  std::uint32_t second{0};
  std::uint64_t used_states{0};
  ExactValue sse;
  std::uint64_t tuple_count{0};
};

struct GlobalDecision {
  std::vector<std::uint8_t> bit_widths;
  std::uint32_t used_bits{0};
  ExactValue sse;
  std::uint64_t transition_count{0};
};

[[nodiscard]] mpz_class DecodeBinary32Exact(std::uint32_t bits);

// Independent optimized solver: each exact-K Monge layer is evaluated with
// divide-and-conquer monotone-minima recursion.  It shares neither the
// producer's complete-matrix construction nor its SMAWK implementation.
// Bound: O(K H log H) interval candidates, O(K H) retained certificates.
[[nodiscard]] ExactCurve FitCurveDivideConquer(
    const std::vector<std::uint32_t>& binary32_bits,
    std::uint32_t maximum_cardinality);
[[nodiscard]] ExactCurve FitWeightedCurveDivideConquer(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum_cardinality);

[[nodiscard]] std::uint32_t DirectRoundBinary32(const ExactValue& value);
[[nodiscard]] std::uint64_t DirectRoundBinary64(const ExactValue& value);

[[nodiscard]] ProductDecision ExhaustiveProductDecision(
    const ExactCurve& first, const ExactCurve& second,
    std::uint32_t capacity, CardinalityDomain domain);
[[nodiscard]] GlobalDecision IndependentGlobalAllocation(
    const std::vector<ExactCurve>& curves, std::uint32_t bit_budget);

}  // namespace saq::a4_v2::verifier

#pragma once

#include <gmpxx.h>

#include <cstddef>
#include <cstdint>
#include <vector>

namespace saq::a4_1s {

// A value represented as (numerator / denominator) * 2^binary_exponent.
// numerator/denominator is always canonical: denominator is positive and the
// gcd is one.  The frozen A4-1S contract uses exponent -149 for centroids and
// exponent -298 for squared-error values.
struct CanonicalScaledRational {
    mpz_class numerator{0};
    mpz_class denominator{1};
    int binary_exponent{0};

    CanonicalScaledRational() = default;
    CanonicalScaledRational(mpz_class numerator_in,
                            mpz_class denominator_in,
                            int binary_exponent_in);

    [[nodiscard]] mpq_class coefficient() const;
    [[nodiscard]] mpq_class value() const;
};

// The registered fit inventory is unweighted, while the frozen parity suite
// also exercises positive integer weights.  vector_id is used only to retain
// deterministic provenance when equal values are aggregated.
struct WeightedBinary32 {
    std::uint32_t bits{0};
    std::uint64_t weight{1};
    std::uint64_t vector_id{0};
};

// One distinct support point.  grid_integer is the exact n in
// x = n * 2^-149.  weight is arbitrary precision even though each input
// record exposes a uint64 weight, so aggregation cannot overflow.
struct ExactSupportPoint {
    mpz_class grid_integer{0};
    mpz_class weight{0};
    std::uint64_t lowest_vector_id{0};
};

struct ExactIntervalStatistics {
    mpz_class weight{0};
    mpz_class weighted_sum{0};
    mpz_class weighted_sum_of_squares{0};
    mpz_class sse_numerator{0}; // weight*C - A^2; denominator is weight.

    [[nodiscard]] CanonicalScaledRational sse() const;
    [[nodiscard]] CanonicalScaledRational mean() const;
};

struct ScalarInterval {
    std::uint32_t begin{0};       // Inclusive support index.
    std::uint32_t end{0};         // Exclusive support index.
    CanonicalScaledRational mean; // Exact interval mean, exponent -149.
};

struct ScalarSolution {
    std::uint32_t requested_cardinality{0};
    std::uint32_t effective_cardinality{0};
    CanonicalScaledRational sse; // Exact curve value, exponent -298.
    std::vector<ScalarInterval> intervals;
};

struct ScalarDiagnostics {
    std::uint64_t exact_comparisons{0};
    std::uint64_t exact_ties{0};
    std::uint64_t matrix_entry_evaluations{0};
    std::uint64_t interval_evaluations{0};
    std::uint64_t exact_replay_checks{0};
    // Index is the effective DP layer.  A value of one means the returned
    // predecessor sequence was nondecreasing over all nonempty prefixes.
    std::vector<std::uint8_t> predecessor_monotone;
    // Per-requested-cardinality work for the DP layer that produces K.
    // K=1 and copied nominal K>H solutions perform no matrix comparisons.
    // The sum of each vector equals the corresponding whole-curve total.
    std::vector<std::uint64_t> exact_comparisons_by_cardinality;
    std::vector<std::uint64_t> exact_ties_by_cardinality;
};

struct ScalarCurveResult {
    std::vector<ExactSupportPoint> support;

    // solutions[K] is the registered at-most-K solution.  Index zero is an
    // unused sentinel so nominal cardinalities can be addressed directly.
    std::vector<ScalarSolution> solutions;

    // predecessors[layer][prefix] is the zero-based beginning of the final
    // nonempty interval.  Only layers up to min(max_cardinality, H) exist.
    // UINT32_MAX denotes an unused state; prefix zero is set to zero.
    std::vector<std::vector<std::uint32_t>> predecessors;
    ScalarDiagnostics diagnostics;

    [[nodiscard]] const ScalarSolution &at(std::uint32_t cardinality) const;
};

enum class ProductCardinalitySet {
    kAllPositiveIntegers,
    kPowersOfTwo,
};

struct ProductAllocation {
    std::uint32_t first_cardinality{0};
    std::uint32_t second_cardinality{0};
    std::uint64_t used_states{0};
    std::uint32_t capacity{0};
    CanonicalScaledRational sse;
    bool nominal_alphabets_reachable{false};
    // Number of objective candidates actually evaluated by the optimized
    // monotone-curve search.  This is accounting only and never affects the
    // selected allocation.
    std::uint64_t optimized_candidate_evaluation_count{0};
};

struct GlobalDyadicAllocation {
    std::vector<std::uint8_t> bit_widths;
    std::uint32_t used_bits{0};
    std::uint32_t bit_budget{0};
    CanonicalScaledRational sse;
    bool nominal_alphabets_reachable{false};
    // Number of (previous-state, selected-width) transitions whose exact
    // objective was evaluated.  This diagnostic does not affect selection.
    std::uint64_t transition_evaluation_count{0};
};

// Decode a finite IEEE-754 binary32 bit pattern exactly.  Both signed zeros
// map to n=0.  NaN and infinity are rejected.
[[nodiscard]] mpz_class DecodeBinary32GridInteger(std::uint32_t bits);

[[nodiscard]] std::uint32_t Binary32Bits(float value) noexcept;
[[nodiscard]] std::uint64_t Binary64Bits(double value) noexcept;
[[nodiscard]] float Binary32FromBits(std::uint32_t bits) noexcept;
[[nodiscard]] double Binary64FromBits(std::uint64_t bits) noexcept;

// Aggregate equal exact values, sort by exact numeric order, and retain the
// lowest contributing vector id.  All weights must be positive and all input
// bit patterns finite.
[[nodiscard]] std::vector<ExactSupportPoint> CanonicalizeSupport(
    const std::vector<WeightedBinary32> &samples);

// Independent interval helper used by exhaustive parity tests.  The fitting
// path builds arbitrary-precision prefix sums and evaluates the same formula
// in O(1) prefix operations.
[[nodiscard]] ExactIntervalStatistics ComputeIntervalStatistics(
    const std::vector<ExactSupportPoint> &support,
    std::size_t begin,
    std::size_t end);

// Fit every registered at-most-K curve with the full-matrix SMAWK recurrence
// described in exact_quantizer.cpp.  All matrix ordering is exact rational;
// no floating-point value participates in a scientific decision.
[[nodiscard]] ScalarCurveResult FitExactScalarCurve(
    const std::vector<WeightedBinary32> &samples,
    std::uint32_t maximum_cardinality);

// Direct round-to-nearest, ties-to-even from the exact rational to the target
// IEEE representation.  There is no binary64 intermediate on the binary32
// path.  An overflow to infinity is rejected.
[[nodiscard]] std::uint32_t RoundExactToBinary32Bits(
    const CanonicalScaledRational &value);
[[nodiscard]] std::uint64_t RoundExactToBinary64Bits(
    const CanonicalScaledRational &value);

// Exact two-factor allocation under K1*K2 <= capacity.  Curves must contain
// every nominal cardinality through capacity.  Ties are resolved by larger
// used-state product and then lexicographically smaller (K1,K2).
[[nodiscard]] ProductAllocation AllocateProduct2(
    const ScalarCurveResult &first,
    const ScalarCurveResult &second,
    std::uint32_t capacity,
    ProductCardinalitySet cardinality_set);

// Exact global dyadic allocation with b_j in [0,8] and K_j=2^b_j.  Ties use
// more of the fixed payload, then the lexicographically smaller bit vector.
[[nodiscard]] GlobalDyadicAllocation AllocateGlobalDyadicCap8(
    const std::vector<ScalarCurveResult> &coordinate_curves,
    std::uint32_t bit_budget);

} // namespace saq::a4_1s

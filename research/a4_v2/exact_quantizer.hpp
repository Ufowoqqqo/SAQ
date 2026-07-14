#pragma once

#include <gmpxx.h>

#include <cstdint>
#include <vector>

namespace saq::a4_v2::producer {

struct ScaledRational {
  mpz_class numerator{0};
  mpz_class denominator{1};
  int binary_exponent{0};

  ScaledRational() = default;
  ScaledRational(mpz_class numerator_in, mpz_class denominator_in,
                 int binary_exponent_in);
  [[nodiscard]] mpq_class coefficient() const;
};

struct WeightedBinary32 {
  std::uint32_t bits{0};
  std::uint64_t weight{1};
  std::uint64_t vector_id{0};
};

struct SupportPoint {
  mpz_class grid_integer{0};
  mpz_class weight{0};
  std::uint64_t lowest_vector_id{0};
};

struct ScalarInterval {
  std::uint32_t begin{0};
  std::uint32_t end{0};
  ScaledRational mean;
};

struct ScalarSolution {
  std::uint32_t requested_cardinality{0};
  std::uint32_t effective_cardinality{0};
  ScaledRational sse;
  std::vector<ScalarInterval> intervals;
  std::uint64_t comparison_count{0};
  std::uint64_t tie_count{0};
};

struct ScalarCurve {
  std::vector<SupportPoint> support;
  std::vector<ScalarSolution> solutions;  // Index zero is unused.
  std::vector<std::vector<std::uint32_t>> predecessors;
  std::vector<std::uint8_t> predecessor_monotone;
  [[nodiscard]] const ScalarSolution& at(std::uint32_t cardinality) const;
};

enum class ProductCardinalitySet { kArbitrary, kDyadic };

struct ProductAllocation {
  std::uint32_t first_cardinality{0};
  std::uint32_t second_cardinality{0};
  std::uint64_t used_states{0};
  std::uint32_t capacity{0};
  ScaledRational sse;
  bool nominal_alphabets_reachable{false};
  std::uint64_t enumerated_candidate_count{0};
};

struct GlobalAllocation {
  std::vector<std::uint8_t> bit_widths;
  std::uint32_t used_bits{0};
  std::uint32_t bit_budget{0};
  ScaledRational sse;
  bool nominal_alphabets_reachable{false};
  std::uint64_t enumerated_transition_count{0};
};

[[nodiscard]] mpz_class DecodeBinary32(std::uint32_t bits);
[[nodiscard]] ScalarCurve FitExactScalarCurve(
    const std::vector<WeightedBinary32>& samples,
    std::uint32_t maximum_cardinality);
[[nodiscard]] std::uint32_t RoundToBinary32(const ScaledRational& value);
[[nodiscard]] std::uint64_t RoundToBinary64(const ScaledRational& value);

[[nodiscard]] ProductAllocation AllocateProduct2(
    const ScalarCurve& first, const ScalarCurve& second,
    std::uint32_t capacity, ProductCardinalitySet set);
[[nodiscard]] GlobalAllocation AllocateGlobalDyadicCap8(
    const std::vector<ScalarCurve>& curves, std::uint32_t bit_budget);

}  // namespace saq::a4_v2::producer

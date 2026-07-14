#include "exact_quantizer.hpp"

#include <algorithm>
#include <bit>
#include <cstddef>
#include <limits>
#include <map>
#include <stdexcept>
#include <utility>
#include <vector>

namespace saq::a4_v2::producer {
namespace {

constexpr int kValueExponent = -149;
constexpr int kSquaredExponent = -298;

[[nodiscard]] mpz_class ImportU64(std::uint64_t value) {
  mpz_class result;
  mpz_import(result.get_mpz_t(), 1, 1, sizeof(value), 0, 0, &value);
  return result;
}

[[nodiscard]] int Compare(const mpq_class& lhs,
                          const mpq_class& rhs) noexcept {
  return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t());
}

struct IntervalMoments {
  mpz_class weight{0};
  mpz_class sum{0};
  mpz_class sum_squares{0};
  mpz_class sse_numerator{0};
};

class PrefixMoments {
 public:
  explicit PrefixMoments(const std::vector<SupportPoint>& support)
      : support_(support),
        weights_(support.size() + 1),
        sums_(support.size() + 1),
        sums_squares_(support.size() + 1) {
    for (std::size_t index = 0; index < support.size(); ++index) {
      if (support[index].weight <= 0 ||
          (index != 0 && support[index - 1].grid_integer >=
                             support[index].grid_integer)) {
        throw std::invalid_argument("noncanonical scalar support");
      }
      weights_[index + 1] = weights_[index] + support[index].weight;
      sums_[index + 1] =
          sums_[index] + support[index].weight * support[index].grid_integer;
      sums_squares_[index + 1] =
          sums_squares_[index] + support[index].weight *
                                          support[index].grid_integer *
                                          support[index].grid_integer;
    }
  }

  [[nodiscard]] IntervalMoments interval(std::size_t begin,
                                         std::size_t end) const {
    if (begin >= end || end > support_.size()) {
      throw std::out_of_range("invalid scalar interval");
    }
    IntervalMoments result;
    result.weight = weights_[end] - weights_[begin];
    result.sum = sums_[end] - sums_[begin];
    result.sum_squares = sums_squares_[end] - sums_squares_[begin];
    result.sse_numerator =
        result.weight * result.sum_squares - result.sum * result.sum;
    if (result.weight <= 0 || result.sse_numerator < 0) {
      throw std::logic_error("invalid exact scalar moments");
    }
    return result;
  }

 private:
  const std::vector<SupportPoint>& support_;
  std::vector<mpz_class> weights_;
  std::vector<mpz_class> sums_;
  std::vector<mpz_class> sums_squares_;
};

struct Fraction {
  mpz_class numerator{0};
  mpz_class denominator{1};
};

// This is the predecessor's complete totally-monotone matrix.  In
// particular, column>row means an empty last interval and has the finite
// value previous[row]; it is not triangular +infinity padding.
class LayerMatrix {
 public:
  LayerMatrix(const PrefixMoments& moments,
              const std::vector<mpq_class>& previous,
              std::uint64_t* comparisons,
              std::uint64_t* ties)
      : moments_(moments),
        previous_(previous),
        comparisons_(comparisons),
        ties_(ties) {}

  [[nodiscard]] int compare(std::uint32_t row, std::uint32_t lhs,
                            std::uint32_t rhs) const {
    ++*comparisons_;
    const Fraction a = entry(row, lhs);
    const Fraction b = entry(row, rhs);
    const mpz_class left = a.numerator * b.denominator;
    const mpz_class right = b.numerator * a.denominator;
    const int result = mpz_cmp(left.get_mpz_t(), right.get_mpz_t());
    if (result == 0) {
      ++*ties_;
    }
    return result;
  }

  [[nodiscard]] mpq_class value(std::uint32_t row,
                                std::uint32_t column) const {
    const Fraction raw = entry(row, column);
    mpq_class result(raw.numerator, raw.denominator);
    result.canonicalize();
    return result;
  }

 private:
  [[nodiscard]] Fraction entry(std::uint32_t row,
                               std::uint32_t column) const {
    if (row == 0 || row >= previous_.size() || column == 0 ||
        column >= previous_.size()) {
      throw std::out_of_range("scalar matrix index");
    }
    if (column > row) {
      return Fraction{previous_[row].get_num(), previous_[row].get_den()};
    }
    const std::size_t predecessor = column - 1;
    const IntervalMoments interval = moments_.interval(predecessor, row);
    Fraction result;
    result.numerator = previous_[predecessor].get_num() * interval.weight +
                       interval.sse_numerator *
                           previous_[predecessor].get_den();
    result.denominator =
        previous_[predecessor].get_den() * interval.weight;
    return result;
  }

  const PrefixMoments& moments_;
  const std::vector<mpq_class>& previous_;
  std::uint64_t* comparisons_;
  std::uint64_t* ties_;
};

void Smawk(const std::vector<std::uint32_t>& rows,
           const std::vector<std::uint32_t>& columns,
           const LayerMatrix& matrix,
           std::vector<std::uint32_t>* minima) {
  if (rows.empty()) {
    return;
  }
  if (columns.empty() || minima == nullptr) {
    throw std::invalid_argument("invalid SMAWK inventory");
  }
  std::vector<std::uint32_t> reduced;
  reduced.reserve(std::min(rows.size(), columns.size()));
  for (const std::uint32_t column : columns) {
    while (!reduced.empty()) {
      const std::uint32_t row = rows[reduced.size() - 1];
      if (matrix.compare(row, column, reduced.back()) < 0) {
        reduced.pop_back();
      } else {
        break;  // Equality retains the earlier column.
      }
    }
    if (reduced.size() < rows.size()) {
      reduced.push_back(column);
    }
  }

  std::vector<std::uint32_t> odd_rows;
  for (std::size_t index = 1; index < rows.size(); index += 2) {
    odd_rows.push_back(rows[index]);
  }
  Smawk(odd_rows, reduced, matrix, minima);

  for (std::size_t index = 0; index < rows.size(); index += 2) {
    std::size_t first = 0;
    std::size_t last = reduced.size() - 1;
    if (index > 0) {
      const auto iterator = std::lower_bound(
          reduced.begin(), reduced.end(), (*minima)[rows[index - 1]]);
      if (iterator == reduced.end() || *iterator != (*minima)[rows[index - 1]]) {
        throw std::logic_error("SMAWK preceding minimum absent");
      }
      first = static_cast<std::size_t>(iterator - reduced.begin());
    }
    if (index + 1 < rows.size()) {
      const auto iterator = std::lower_bound(
          reduced.begin(), reduced.end(), (*minima)[rows[index + 1]]);
      if (iterator == reduced.end() || *iterator != (*minima)[rows[index + 1]]) {
        throw std::logic_error("SMAWK following minimum absent");
      }
      last = static_cast<std::size_t>(iterator - reduced.begin());
    }
    if (first > last) {
      throw std::logic_error("SMAWK interpolation order");
    }
    const std::uint32_t row = rows[index];
    std::uint32_t best = reduced[first];
    for (std::size_t position = first + 1; position <= last; ++position) {
      if (matrix.compare(row, reduced[position], best) < 0) {
        best = reduced[position];
      }
    }
    (*minima)[row] = best;
  }
}

[[nodiscard]] IntervalMoments ReplayInterval(
    const std::vector<SupportPoint>& support, std::size_t begin,
    std::size_t end) {
  if (begin >= end || end > support.size()) {
    throw std::out_of_range("invalid replay interval");
  }
  IntervalMoments result;
  for (std::size_t index = begin; index < end; ++index) {
    result.weight += support[index].weight;
    result.sum += support[index].weight * support[index].grid_integer;
    result.sum_squares += support[index].weight * support[index].grid_integer *
                          support[index].grid_integer;
  }
  result.sse_numerator =
      result.weight * result.sum_squares - result.sum * result.sum;
  return result;
}

[[nodiscard]] ScalarSolution Reconstruct(
    std::uint32_t cardinality, const mpq_class& objective,
    const std::vector<SupportPoint>& support,
    const std::vector<std::vector<std::uint32_t>>& predecessors,
    std::uint64_t comparisons, std::uint64_t ties) {
  std::size_t end = support.size();
  std::vector<ScalarInterval> reverse;
  mpq_class replay(0);
  for (std::uint32_t layer = cardinality; layer != 0; --layer) {
    if (end >= predecessors[layer].size()) {
      throw std::logic_error("predecessor replay index");
    }
    const std::uint32_t begin = predecessors[layer][end];
    if (begin >= end) {
      throw std::logic_error("predecessor replay empty interval");
    }
    const IntervalMoments moment = ReplayInterval(support, begin, end);
    replay += mpq_class(moment.sse_numerator, moment.weight);
    reverse.push_back(ScalarInterval{
        begin, static_cast<std::uint32_t>(end),
        ScaledRational(moment.sum, moment.weight, kValueExponent)});
    end = begin;
  }
  replay.canonicalize();
  if (end != 0 || Compare(replay, objective) != 0) {
    throw std::logic_error("scalar exact replay mismatch");
  }
  std::reverse(reverse.begin(), reverse.end());
  return ScalarSolution{cardinality,
                        cardinality,
                        ScaledRational(objective.get_num(), objective.get_den(),
                                       kSquaredExponent),
                        std::move(reverse),
                        comparisons,
                        ties};
}

[[nodiscard]] long FloorLog2Ratio(const mpz_class& numerator,
                                  const mpz_class& denominator) {
  const long numerator_bits =
      static_cast<long>(mpz_sizeinbase(numerator.get_mpz_t(), 2));
  const long denominator_bits =
      static_cast<long>(mpz_sizeinbase(denominator.get_mpz_t(), 2));
  long exponent = numerator_bits - denominator_bits;
  mpz_class lhs = numerator;
  mpz_class rhs = denominator;
  if (exponent >= 0) {
    mpz_mul_2exp(rhs.get_mpz_t(), rhs.get_mpz_t(), exponent);
  } else {
    mpz_mul_2exp(lhs.get_mpz_t(), lhs.get_mpz_t(), -exponent);
  }
  if (lhs < rhs) {
    --exponent;
  }
  return exponent;
}

[[nodiscard]] mpz_class RoundRatio(const mpz_class& numerator,
                                   const mpz_class& denominator) {
  mpz_class quotient;
  mpz_class remainder;
  mpz_tdiv_qr(quotient.get_mpz_t(), remainder.get_mpz_t(),
              numerator.get_mpz_t(), denominator.get_mpz_t());
  const mpz_class doubled_remainder = remainder * 2;
  const int midpoint = mpz_cmp(doubled_remainder.get_mpz_t(),
                               denominator.get_mpz_t());
  if (midpoint > 0 ||
      (midpoint == 0 && mpz_odd_p(quotient.get_mpz_t()) != 0)) {
    ++quotient;
  }
  return quotient;
}

[[nodiscard]] mpz_class RoundShifted(const mpz_class& numerator,
                                     const mpz_class& denominator,
                                     long shift) {
  if (shift >= 0) {
    mpz_class scaled = numerator;
    mpz_mul_2exp(scaled.get_mpz_t(), scaled.get_mpz_t(), shift);
    return RoundRatio(scaled, denominator);
  }
  mpz_class scaled = denominator;
  mpz_mul_2exp(scaled.get_mpz_t(), scaled.get_mpz_t(), -shift);
  return RoundRatio(numerator, scaled);
}

[[nodiscard]] std::uint64_t RoundIeee(const ScaledRational& input,
                                      int fraction_bits, int exponent_bits,
                                      int exponent_bias) {
  if (input.denominator <= 0) {
    throw std::invalid_argument("nonpositive exact denominator");
  }
  const bool negative = input.numerator < 0;
  const mpz_class magnitude = negative ? -input.numerator : input.numerator;
  const int total_bits = 1 + exponent_bits + fraction_bits;
  const std::uint64_t sign =
      negative ? (std::uint64_t{1} << (total_bits - 1)) : 0;
  if (magnitude == 0) {
    return 0;
  }
  const long value_exponent =
      FloorLog2Ratio(magnitude, input.denominator) + input.binary_exponent;
  const long minimum_normal = 1L - exponent_bias;
  const long maximum_normal = exponent_bias;
  const std::uint64_t hidden = std::uint64_t{1} << fraction_bits;
  std::uint64_t exponent_field = 0;
  std::uint64_t fraction_field = 0;
  if (value_exponent >= minimum_normal) {
    mpz_class rounded = RoundShifted(
        magnitude, input.denominator,
        static_cast<long>(input.binary_exponent) - value_exponent +
            fraction_bits);
    std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
    long encoded_exponent = value_exponent;
    if (significand == (hidden << 1U)) {
      significand >>= 1U;
      ++encoded_exponent;
    }
    if (encoded_exponent > maximum_normal || significand < hidden ||
        significand >= (hidden << 1U)) {
      throw std::overflow_error("exact value is outside finite IEEE range");
    }
    exponent_field =
        static_cast<std::uint64_t>(encoded_exponent + exponent_bias);
    fraction_field = significand - hidden;
  } else {
    const long minimum_subnormal = minimum_normal - fraction_bits;
    const mpz_class rounded = RoundShifted(
        magnitude, input.denominator,
        static_cast<long>(input.binary_exponent) - minimum_subnormal);
    const std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
    if (significand > hidden) {
      throw std::logic_error("subnormal rounding skipped boundary");
    }
    if (significand == hidden) {
      exponent_field = 1;
    } else {
      fraction_field = significand;
    }
  }
  const std::uint64_t max_exponent =
      (std::uint64_t{1} << exponent_bits) - 1;
  if (exponent_field == max_exponent || fraction_field >= hidden) {
    throw std::logic_error("invalid finite IEEE encoding");
  }
  return sign | (exponent_field << fraction_bits) | fraction_field;
}

[[nodiscard]] bool IsPowerOfTwo(std::uint32_t value) noexcept {
  return value != 0 && (value & (value - 1)) == 0;
}

[[nodiscard]] ScaledRational FromCoefficient(const mpq_class& value,
                                             int exponent) {
  return ScaledRational(value.get_num(), value.get_den(), exponent);
}

}  // namespace

ScaledRational::ScaledRational(mpz_class numerator_in,
                               mpz_class denominator_in,
                               int binary_exponent_in)
    : binary_exponent(binary_exponent_in) {
  if (denominator_in == 0) {
    throw std::invalid_argument("zero rational denominator");
  }
  mpq_class value(std::move(numerator_in), std::move(denominator_in));
  value.canonicalize();
  numerator = value.get_num();
  denominator = value.get_den();
}

mpq_class ScaledRational::coefficient() const {
  if (denominator <= 0) {
    throw std::logic_error("noncanonical rational");
  }
  mpq_class value(numerator, denominator);
  value.canonicalize();
  return value;
}

const ScalarSolution& ScalarCurve::at(std::uint32_t cardinality) const {
  if (cardinality == 0 || cardinality >= solutions.size()) {
    throw std::out_of_range("scalar cardinality unavailable");
  }
  return solutions[cardinality];
}

mpz_class DecodeBinary32(std::uint32_t bits) {
  const std::uint32_t exponent = (bits >> 23U) & 0xffU;
  const std::uint32_t fraction = bits & 0x7fffffU;
  if (exponent == 0xffU) {
    throw std::invalid_argument("scalar input must be finite binary32");
  }
  mpz_class value;
  if (exponent == 0) {
    value = static_cast<unsigned long>(fraction);
  } else {
    value = static_cast<unsigned long>((1U << 23U) | fraction);
    mpz_mul_2exp(value.get_mpz_t(), value.get_mpz_t(), exponent - 1U);
  }
  if ((bits >> 31U) != 0 && value != 0) {
    value = -value;
  }
  return value;
}

ScalarCurve FitExactScalarCurve(
    const std::vector<WeightedBinary32>& samples,
    std::uint32_t maximum_cardinality) {
  if (samples.empty() || maximum_cardinality == 0) {
    throw std::invalid_argument("empty scalar fit or zero K");
  }
  struct Aggregate {
    mpz_class weight{0};
    std::uint64_t lowest_vector_id{0};
  };
  std::map<mpz_class, Aggregate> aggregates;
  for (const WeightedBinary32& sample : samples) {
    if (sample.weight == 0) {
      throw std::invalid_argument("scalar weights must be positive");
    }
    const mpz_class decoded = DecodeBinary32(sample.bits);
    const auto [iterator, inserted] = aggregates.try_emplace(decoded);
    iterator->second.weight += ImportU64(sample.weight);
    if (inserted || sample.vector_id < iterator->second.lowest_vector_id) {
      iterator->second.lowest_vector_id = sample.vector_id;
    }
  }

  ScalarCurve result;
  result.support.reserve(aggregates.size());
  for (auto& [value, aggregate] : aggregates) {
    result.support.push_back(
        SupportPoint{value, aggregate.weight, aggregate.lowest_vector_id});
  }
  const std::uint32_t support_size =
      static_cast<std::uint32_t>(result.support.size());
  const std::uint32_t effective_max =
      std::min(maximum_cardinality, support_size);
  result.solutions.resize(static_cast<std::size_t>(maximum_cardinality) + 1);
  result.predecessors.assign(
      static_cast<std::size_t>(effective_max) + 1,
      std::vector<std::uint32_t>(static_cast<std::size_t>(support_size) + 1,
                                 std::numeric_limits<std::uint32_t>::max()));
  result.predecessor_monotone.assign(
      static_cast<std::size_t>(effective_max) + 1, 0);
  for (std::uint32_t layer = 1; layer <= effective_max; ++layer) {
    result.predecessors[layer][0] = 0;
  }

  const PrefixMoments moments(result.support);
  std::vector<mpq_class> previous(support_size + 1, mpq_class(0));
  std::vector<mpq_class> current(support_size + 1, mpq_class(0));
  for (std::uint32_t prefix = 1; prefix <= support_size; ++prefix) {
    const IntervalMoments interval = moments.interval(0, prefix);
    previous[prefix] = mpq_class(interval.sse_numerator, interval.weight);
    previous[prefix].canonicalize();
    result.predecessors[1][prefix] = 0;
  }
  result.predecessor_monotone[1] = 1;
  result.solutions[1] = Reconstruct(
      1, previous[support_size], result.support, result.predecessors, 0, 0);

  std::vector<std::uint32_t> rows(support_size);
  std::vector<std::uint32_t> columns(support_size);
  for (std::uint32_t index = 0; index < support_size; ++index) {
    rows[index] = columns[index] = index + 1;
  }
  for (std::uint32_t layer = 2; layer <= effective_max; ++layer) {
    std::uint64_t comparisons = 0;
    std::uint64_t ties = 0;
    const LayerMatrix matrix(moments, previous, &comparisons, &ties);
    std::vector<std::uint32_t> minima(support_size + 1, 0);
    Smawk(rows, columns, matrix, &minima);
    std::uint32_t prior = 0;
    for (std::uint32_t prefix = 1; prefix <= support_size; ++prefix) {
      const std::uint32_t column = minima[prefix];
      if (column == 0 || column > prefix) {
        throw std::logic_error("SMAWK selected empty final interval");
      }
      const std::uint32_t predecessor = column - 1;
      if (prefix > 1 && predecessor < prior) {
        throw std::logic_error("SMAWK predecessors are not monotone");
      }
      result.predecessors[layer][prefix] = predecessor;
      current[prefix] = matrix.value(prefix, column);
      prior = predecessor;
    }
    result.solutions[layer] =
        Reconstruct(layer, current[support_size], result.support, result.predecessors,
                    comparisons, ties);
    result.predecessor_monotone[layer] = 1;
    previous.swap(current);
  }
  for (std::uint32_t requested = effective_max + 1;
       requested <= maximum_cardinality; ++requested) {
    result.solutions[requested] = result.solutions[effective_max];
    result.solutions[requested].requested_cardinality = requested;
    result.solutions[requested].effective_cardinality = support_size;
    result.solutions[requested].comparison_count = 0;
    result.solutions[requested].tie_count = 0;
  }
  return result;
}

std::uint32_t RoundToBinary32(const ScaledRational& value) {
  return static_cast<std::uint32_t>(RoundIeee(value, 23, 8, 127));
}

std::uint64_t RoundToBinary64(const ScaledRational& value) {
  return RoundIeee(value, 52, 11, 1023);
}

ProductAllocation AllocateProduct2(const ScalarCurve& first,
                                   const ScalarCurve& second,
                                   std::uint32_t capacity,
                                   ProductCardinalitySet set) {
  if (capacity == 0) {
    throw std::invalid_argument("zero product capacity");
  }
  static_cast<void>(first.at(capacity));
  static_cast<void>(second.at(capacity));
  bool found = false;
  mpq_class best;
  std::uint32_t best_first = 0;
  std::uint32_t best_second = 0;
  std::uint64_t best_product = 0;
  std::uint64_t count = 0;
  for (std::uint32_t first_k = 1; first_k <= capacity; ++first_k) {
    if (set == ProductCardinalitySet::kDyadic && !IsPowerOfTwo(first_k)) {
      continue;
    }
    const std::uint32_t limit = capacity / first_k;
    std::uint32_t second_k = limit;
    if (set == ProductCardinalitySet::kDyadic) {
      second_k = std::uint32_t{1}
                 << (31U - std::countl_zero(limit));
    }
    ++count;
    mpq_class candidate = first.at(first_k).sse.coefficient() +
                          second.at(second_k).sse.coefficient();
    candidate.canonicalize();
    const std::uint64_t product =
        static_cast<std::uint64_t>(first_k) * second_k;
    bool replace = !found;
    if (found) {
      const int ordering = Compare(candidate, best);
      replace = ordering < 0 ||
                (ordering == 0 &&
                 (product > best_product ||
                  (product == best_product &&
                   std::pair{first_k, second_k} <
                       std::pair{best_first, best_second})));
    }
    if (replace) {
      found = true;
      best = candidate;
      best_first = first_k;
      best_second = second_k;
      best_product = product;
    }
  }
  if (!found) {
    throw std::logic_error("product allocation has no state");
  }
  return ProductAllocation{
      best_first,
      best_second,
      best_product,
      capacity,
      FromCoefficient(best, kSquaredExponent),
      first.at(best_first).effective_cardinality == best_first &&
          second.at(best_second).effective_cardinality == best_second,
      count};
}

GlobalAllocation AllocateGlobalDyadicCap8(
    const std::vector<ScalarCurve>& curves, std::uint32_t bit_budget) {
  if (curves.empty()) {
    throw std::invalid_argument("global allocation needs curves");
  }
  struct State {
    bool reachable{false};
    mpq_class cost{0};
    std::vector<std::uint8_t> bits;
  };
  std::vector<State> previous(bit_budget + 1);
  std::vector<State> current(bit_budget + 1);
  previous[0].reachable = true;
  std::uint64_t transitions = 0;
  for (const ScalarCurve& curve : curves) {
    static_cast<void>(curve.at(256));
    for (State& state : current) {
      state = State{};
    }
    for (std::uint32_t used = 0; used <= bit_budget; ++used) {
      if (!previous[used].reachable) {
        continue;
      }
      for (std::uint8_t bits = 0; bits <= 8 && used + bits <= bit_budget;
           ++bits) {
        ++transitions;
        const std::uint32_t cardinality = std::uint32_t{1} << bits;
        mpq_class cost =
            previous[used].cost + curve.at(cardinality).sse.coefficient();
        cost.canonicalize();
        std::vector<std::uint8_t> candidate = previous[used].bits;
        candidate.push_back(bits);
        State& destination = current[used + bits];
        bool replace = !destination.reachable;
        if (destination.reachable) {
          const int ordering = Compare(cost, destination.cost);
          replace = ordering < 0 ||
                    (ordering == 0 && candidate < destination.bits);
        }
        if (replace) {
          destination.reachable = true;
          destination.cost = std::move(cost);
          destination.bits = std::move(candidate);
        }
      }
    }
    previous.swap(current);
  }
  bool found = false;
  std::uint32_t best_used = 0;
  State best;
  for (std::uint32_t used = 0; used <= bit_budget; ++used) {
    if (!previous[used].reachable) {
      continue;
    }
    bool replace = !found;
    if (found) {
      const int ordering = Compare(previous[used].cost, best.cost);
      replace = ordering < 0 ||
                (ordering == 0 &&
                 (used > best_used ||
                  (used == best_used && previous[used].bits < best.bits)));
    }
    if (replace) {
      found = true;
      best_used = used;
      best = previous[used];
    }
  }
  if (!found) {
    throw std::logic_error("global allocation has no state");
  }
  bool reachable = true;
  for (std::size_t coordinate = 0; coordinate < curves.size(); ++coordinate) {
    const std::uint32_t cardinality =
        std::uint32_t{1} << best.bits[coordinate];
    reachable = reachable &&
                curves[coordinate].at(cardinality).effective_cardinality ==
                    cardinality;
  }
  return GlobalAllocation{std::move(best.bits),
                          best_used,
                          bit_budget,
                          FromCoefficient(best.cost, kSquaredExponent),
                          reachable,
                          transitions};
}

}  // namespace saq::a4_v2::producer

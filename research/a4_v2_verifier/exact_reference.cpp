#include "exact_reference.hpp"

#include <algorithm>
#include <bit>
#include <limits>
#include <map>
#include <stdexcept>
#include <utility>

namespace saq::a4_v2::verifier {
namespace {

constexpr int kValueExponent = -149;
constexpr int kSquaredExponent = -298;

struct PrefixSums {
  std::vector<mpz_class> weight;
  std::vector<mpz_class> first;
  std::vector<mpz_class> second;

  explicit PrefixSums(const std::vector<ExactSupport>& support)
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

  [[nodiscard]] mpq_class cost(std::uint32_t begin,
                               std::uint32_t end) const {
    if (begin >= end || end >= weight.size()) {
      throw std::out_of_range("invalid independent interval");
    }
    const mpz_class w = weight[end] - weight[begin];
    const mpz_class a = first[end] - first[begin];
    const mpz_class c = second[end] - second[begin];
    mpq_class result(w * c - a * a, w);
    result.canonicalize();
    if (result < 0) throw std::logic_error("negative independent SSE");
    return result;
  }

  [[nodiscard]] ExactValue mean(std::uint32_t begin,
                                std::uint32_t end) const {
    const mpz_class w = weight[end] - weight[begin];
    const mpz_class a = first[end] - first[begin];
    return ExactValue(a, w, kValueExponent);
  }
};

class MonotoneLayer {
 public:
  MonotoneLayer(std::uint32_t layer, const PrefixSums& prefix,
                const std::vector<mpq_class>& previous,
                std::vector<mpq_class>* current,
                std::vector<std::uint32_t>* predecessor)
      : layer_(layer),
        prefix_(prefix),
        previous_(previous),
        current_(current),
        predecessor_(predecessor) {}

  void Compute(std::uint32_t support_size) {
    Solve(layer_, support_size, layer_ - 1, support_size - 1);
  }

 private:
  void Solve(std::uint32_t row_first, std::uint32_t row_last,
             std::uint32_t option_first, std::uint32_t option_last) {
    if (row_first > row_last) return;
    const std::uint32_t row = row_first + (row_last - row_first) / 2;
    const std::uint32_t last = std::min(option_last, row - 1);
    if (option_first > last) {
      throw std::logic_error("empty divide-and-conquer option interval");
    }
    bool found = false;
    mpq_class best;
    std::uint32_t best_predecessor = option_first;
    for (std::uint32_t candidate = option_first; candidate <= last;
         ++candidate) {
      mpq_class value = previous_[candidate] + prefix_.cost(candidate, row);
      value.canonicalize();
      const int ordering =
          found ? mpq_cmp(value.get_mpq_t(), best.get_mpq_t()) : -1;
      // Earliest predecessor is the independent recursive tie certificate.
      if (!found || ordering < 0) {
        found = true;
        best = std::move(value);
        best_predecessor = candidate;
      }
    }
    (*current_)[row] = std::move(best);
    (*predecessor_)[row] = best_predecessor;
    if (row != row_first) {
      Solve(row_first, row - 1, option_first, best_predecessor);
    }
    if (row != row_last) {
      Solve(row + 1, row_last, best_predecessor, option_last);
    }
  }

  std::uint32_t layer_;
  const PrefixSums& prefix_;
  const std::vector<mpq_class>& previous_;
  std::vector<mpq_class>* current_;
  std::vector<std::uint32_t>* predecessor_;
};

// This counter-only certificate deliberately models the registered complete
// matrix and SMAWK comparison schedule.  It is disjoint from MonotoneLayer:
// its minima and objective rows are never consumed by the independent D&C
// scientific solution, reconstruction, allocation, or serialization paths.
class RegisteredScheduleMatrix {
 public:
  RegisteredScheduleMatrix(const PrefixSums& prefix,
                           const std::vector<mpq_class>& previous,
                           std::uint64_t* comparisons,
                           std::uint64_t* ties)
      : prefix_(prefix),
        previous_(previous),
        comparisons_(comparisons),
        ties_(ties) {}

  [[nodiscard]] mpq_class value(std::uint32_t row,
                                std::uint32_t column) const {
    if (row == 0 || row >= previous_.size() || column == 0 ||
        column >= previous_.size()) {
      throw std::out_of_range("registered schedule matrix index");
    }
    if (column > row) return previous_[row];
    mpq_class result = previous_[column - 1] + prefix_.cost(column - 1, row);
    result.canonicalize();
    return result;
  }

  [[nodiscard]] int compare(std::uint32_t row, std::uint32_t lhs,
                            std::uint32_t rhs) const {
    ++*comparisons_;
    const mpq_class left = value(row, lhs);
    const mpq_class right = value(row, rhs);
    const int result = mpq_cmp(left.get_mpq_t(), right.get_mpq_t());
    if (result == 0) ++*ties_;
    return result;
  }

 private:
  const PrefixSums& prefix_;
  const std::vector<mpq_class>& previous_;
  std::uint64_t* comparisons_;
  std::uint64_t* ties_;
};

void CountRegisteredSmawk(const std::vector<std::uint32_t>& rows,
                          const std::vector<std::uint32_t>& columns,
                          const RegisteredScheduleMatrix& matrix,
                          std::vector<std::uint32_t>* minima) {
  if (rows.empty()) return;
  if (columns.empty() || minima == nullptr) {
    throw std::invalid_argument("invalid registered SMAWK inventory");
  }
  std::vector<std::uint32_t> reduced;
  reduced.reserve(std::min(rows.size(), columns.size()));
  for (const std::uint32_t column : columns) {
    while (!reduced.empty()) {
      const std::uint32_t row = rows[reduced.size() - 1];
      if (matrix.compare(row, column, reduced.back()) < 0) {
        reduced.pop_back();
      } else {
        break;
      }
    }
    if (reduced.size() < rows.size()) reduced.push_back(column);
  }
  std::vector<std::uint32_t> odd_rows;
  for (std::size_t index = 1; index < rows.size(); index += 2) {
    odd_rows.push_back(rows[index]);
  }
  CountRegisteredSmawk(odd_rows, reduced, matrix, minima);
  for (std::size_t index = 0; index < rows.size(); index += 2) {
    std::size_t first = 0;
    std::size_t last = reduced.size() - 1;
    if (index > 0) {
      const auto found = std::lower_bound(
          reduced.begin(), reduced.end(), (*minima)[rows[index - 1]]);
      if (found == reduced.end() || *found != (*minima)[rows[index - 1]]) {
        throw std::logic_error("registered SMAWK prior minimum absent");
      }
      first = static_cast<std::size_t>(found - reduced.begin());
    }
    if (index + 1 < rows.size()) {
      const auto found = std::lower_bound(
          reduced.begin(), reduced.end(), (*minima)[rows[index + 1]]);
      if (found == reduced.end() || *found != (*minima)[rows[index + 1]]) {
        throw std::logic_error("registered SMAWK following minimum absent");
      }
      last = static_cast<std::size_t>(found - reduced.begin());
    }
    if (first > last) {
      throw std::logic_error("registered SMAWK interpolation order");
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

[[nodiscard]] ExactSolution Reconstruct(
    std::uint32_t cardinality, const std::vector<ExactSupport>& support,
    const PrefixSums& prefix,
    const std::vector<std::vector<std::uint32_t>>& predecessors,
    const mpq_class& optimum) {
  std::uint32_t end = static_cast<std::uint32_t>(support.size());
  std::vector<ExactInterval> intervals;
  intervals.reserve(cardinality);
  mpq_class replay(0);
  for (std::uint32_t layer = cardinality; layer > 0; --layer) {
    const std::uint32_t begin = predecessors[layer][end];
    if (begin >= end) throw std::logic_error("empty reconstructed interval");
    replay += prefix.cost(begin, end);
    intervals.push_back(ExactInterval{begin, end, prefix.mean(begin, end)});
    end = begin;
  }
  replay.canonicalize();
  if (end != 0 || replay != optimum) {
    throw std::logic_error("independent scalar certificate does not replay");
  }
  std::reverse(intervals.begin(), intervals.end());
  return ExactSolution{
      cardinality,
      cardinality,
      ExactValue(optimum.get_num(), optimum.get_den(), kSquaredExponent),
      std::move(intervals),
      0,
      0};
}

[[nodiscard]] bool PowerOfTwo(std::uint32_t value) {
  return value != 0 && (value & (value - 1U)) == 0;
}

[[nodiscard]] long BinaryFloor(const mpz_class& numerator,
                               const mpz_class& denominator) {
  long result = static_cast<long>(mpz_sizeinbase(numerator.get_mpz_t(), 2)) -
                static_cast<long>(mpz_sizeinbase(denominator.get_mpz_t(), 2));
  mpz_class left = numerator;
  mpz_class right = denominator;
  if (result >= 0) mpz_mul_2exp(right.get_mpz_t(), right.get_mpz_t(), result);
  else mpz_mul_2exp(left.get_mpz_t(), left.get_mpz_t(), -result);
  if (left < right) --result;
  return result;
}

[[nodiscard]] mpz_class NearestEvenQuotient(mpz_class numerator,
                                             mpz_class denominator) {
  mpz_class quotient;
  mpz_class remainder;
  mpz_fdiv_qr(quotient.get_mpz_t(), remainder.get_mpz_t(),
              numerator.get_mpz_t(), denominator.get_mpz_t());
  const mpz_class twice = 2 * remainder;
  const int side = mpz_cmp(twice.get_mpz_t(), denominator.get_mpz_t());
  if (side > 0 || (side == 0 && mpz_odd_p(quotient.get_mpz_t()) != 0)) {
    ++quotient;
  }
  return quotient;
}

[[nodiscard]] mpz_class ShiftAndRound(const mpz_class& numerator,
                                       const mpz_class& denominator,
                                       long binary_shift) {
  mpz_class top = numerator;
  mpz_class bottom = denominator;
  if (binary_shift >= 0) {
    mpz_mul_2exp(top.get_mpz_t(), top.get_mpz_t(), binary_shift);
  } else {
    mpz_mul_2exp(bottom.get_mpz_t(), bottom.get_mpz_t(), -binary_shift);
  }
  return NearestEvenQuotient(std::move(top), std::move(bottom));
}

[[nodiscard]] std::uint64_t DirectIeee(const ExactValue& value,
                                       int fraction_bits, int exponent_bits,
                                       int bias) {
  if (value.denominator <= 0) throw std::invalid_argument("invalid exact value");
  const bool negative = value.numerator < 0;
  const mpz_class magnitude = negative ? -value.numerator : value.numerator;
  const int total_bits = 1 + exponent_bits + fraction_bits;
  const std::uint64_t sign =
      negative ? (std::uint64_t{1} << (total_bits - 1)) : 0;
  if (magnitude == 0) return 0;  // Canonical signed zero.
  const long exponent = BinaryFloor(magnitude, value.denominator) +
                        value.binary_grid_exponent;
  const long minimum_normal = 1L - bias;
  const long maximum_normal = bias;
  const std::uint64_t implicit = std::uint64_t{1} << fraction_bits;
  std::uint64_t exponent_field = 0;
  std::uint64_t fraction_field = 0;
  if (exponent >= minimum_normal) {
    mpz_class rounded = ShiftAndRound(
        magnitude, value.denominator,
        static_cast<long>(value.binary_grid_exponent) - exponent +
            fraction_bits);
    std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
    long encoded_exponent = exponent;
    if (significand == 2 * implicit) {
      significand /= 2;
      ++encoded_exponent;
    }
    if (encoded_exponent > maximum_normal || significand < implicit ||
        significand >= 2 * implicit) {
      throw std::overflow_error("direct RNE overflow");
    }
    exponent_field = static_cast<std::uint64_t>(encoded_exponent + bias);
    fraction_field = significand - implicit;
  } else {
    const long least_subnormal = minimum_normal - fraction_bits;
    const mpz_class rounded = ShiftAndRound(
        magnitude, value.denominator,
        static_cast<long>(value.binary_grid_exponent) - least_subnormal);
    const std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
    if (significand > implicit) throw std::logic_error("subnormal RNE overflow");
    if (significand == implicit) exponent_field = 1;
    else fraction_field = significand;
  }
  const std::uint64_t reserved = (std::uint64_t{1} << exponent_bits) - 1;
  if (exponent_field == reserved || fraction_field >= implicit) {
    throw std::logic_error("direct RNE emitted nonfinite bits");
  }
  return sign | (exponent_field << fraction_bits) | fraction_field;
}

}  // namespace

ExactValue::ExactValue(mpz_class numerator_in, mpz_class denominator_in,
                       int exponent)
    : binary_grid_exponent(exponent) {
  if (denominator_in == 0) throw std::invalid_argument("zero exact denominator");
  mpq_class reduced(std::move(numerator_in), std::move(denominator_in));
  reduced.canonicalize();
  numerator = reduced.get_num();
  denominator = reduced.get_den();
}

mpq_class ExactValue::coefficient() const {
  mpq_class result(numerator, denominator);
  result.canonicalize();
  return result;
}

const ExactSolution& ExactCurve::at(std::uint32_t cardinality) const {
  if (cardinality == 0 || cardinality >= solutions.size()) {
    throw std::out_of_range("independent curve cardinality unavailable");
  }
  return solutions[cardinality];
}

mpz_class DecodeBinary32Exact(std::uint32_t bits) {
  const std::uint32_t exponent = (bits >> 23U) & 0xffU;
  const std::uint32_t fraction = bits & 0x7fffffU;
  if (exponent == 0xffU) throw std::invalid_argument("nonfinite panel value");
  mpz_class significand;
  unsigned int shift = 0;
  if (exponent == 0) {
    significand = fraction;
  } else {
    significand = (1U << 23U) | fraction;
    shift = exponent - 1U;
  }
  mpz_mul_2exp(significand.get_mpz_t(), significand.get_mpz_t(), shift);
  if ((bits >> 31U) != 0 && significand != 0) significand = -significand;
  return significand;
}

ExactCurve FitCurveDivideConquer(
    const std::vector<std::uint32_t>& binary32_bits,
    std::uint32_t maximum_cardinality) {
  std::vector<WeightedExactSample> samples;
  samples.reserve(binary32_bits.size());
  for (std::size_t index = 0; index < binary32_bits.size(); ++index) {
    samples.push_back(WeightedExactSample{
        binary32_bits[index], 1, static_cast<std::uint64_t>(index)});
  }
  return FitWeightedCurveDivideConquer(samples, maximum_cardinality);
}

ExactCurve FitWeightedCurveDivideConquer(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum_cardinality) {
  if (samples.empty() || maximum_cardinality == 0) {
    throw std::invalid_argument("empty independent scalar fit");
  }
  struct Aggregate {
    mpz_class weight{0};
    std::uint64_t lowest_vector_id{0};
  };
  std::map<mpz_class, Aggregate> frequencies;
  for (const WeightedExactSample& sample : samples) {
    if (sample.weight == 0) {
      throw std::invalid_argument("independent scalar weight is zero");
    }
    const mpz_class value = DecodeBinary32Exact(sample.binary32_bits);
    const auto [position, inserted] = frequencies.try_emplace(value);
    position->second.weight +=
        mpz_class(static_cast<unsigned long>(sample.weight));
    if (inserted || sample.vector_id < position->second.lowest_vector_id) {
      position->second.lowest_vector_id = sample.vector_id;
    }
  }
  ExactCurve curve;
  curve.support.reserve(frequencies.size());
  for (const auto& [value, aggregate] : frequencies) {
    curve.support.push_back(ExactSupport{
        value, aggregate.weight, aggregate.lowest_vector_id});
  }
  const std::uint32_t h = static_cast<std::uint32_t>(curve.support.size());
  const std::uint32_t layers = std::min(h, maximum_cardinality);
  curve.solutions.resize(static_cast<std::size_t>(maximum_cardinality) + 1);
  curve.predecessors.assign(
      static_cast<std::size_t>(layers) + 1,
      std::vector<std::uint32_t>(static_cast<std::size_t>(h) + 1,
                                 std::numeric_limits<std::uint32_t>::max()));
  std::vector<std::vector<std::uint32_t>>& predecessor = curve.predecessors;
  for (std::uint32_t layer = 1; layer <= layers; ++layer) {
    predecessor[layer][0] = 0;
  }
  const PrefixSums prefix(curve.support);
  std::vector<mpq_class> previous(h + 1);
  std::vector<mpq_class> current(h + 1);
  for (std::uint32_t row = 1; row <= h; ++row) {
    previous[row] = prefix.cost(0, row);
    predecessor[1][row] = 0;
  }
  curve.solutions[1] =
      Reconstruct(1, curve.support, prefix, predecessor, previous[h]);
  std::vector<mpq_class> registered_previous = previous;
  std::vector<mpq_class> registered_current(h + 1);
  std::vector<std::uint32_t> registered_rows(h);
  std::vector<std::uint32_t> registered_columns(h);
  for (std::uint32_t index = 0; index < h; ++index) {
    registered_rows[index] = registered_columns[index] = index + 1;
  }
  for (std::uint32_t layer = 2; layer <= layers; ++layer) {
    MonotoneLayer solver(layer, prefix, previous, &current,
                         &predecessor[layer]);
    solver.Compute(h);
    curve.solutions[layer] = Reconstruct(
        layer, curve.support, prefix, predecessor, current[h]);
    std::uint64_t comparisons = 0;
    std::uint64_t ties = 0;
    const RegisteredScheduleMatrix schedule(
        prefix, registered_previous, &comparisons, &ties);
    std::vector<std::uint32_t> minima(h + 1, 0);
    CountRegisteredSmawk(
        registered_rows, registered_columns, schedule, &minima);
    for (std::uint32_t row = 1; row <= h; ++row) {
      if (minima[row] == 0 || minima[row] > row) {
        throw std::logic_error(
            "registered SMAWK counter selected an empty interval");
      }
      registered_current[row] = schedule.value(row, minima[row]);
    }
    curve.solutions[layer].registered_comparison_count = comparisons;
    curve.solutions[layer].registered_tie_count = ties;
    previous.swap(current);
    registered_previous.swap(registered_current);
  }
  for (std::uint32_t requested = layers + 1;
       requested <= maximum_cardinality; ++requested) {
    curve.solutions[requested] = curve.solutions[layers];
    curve.solutions[requested].requested_cardinality = requested;
    curve.solutions[requested].effective_cardinality = h;
    curve.solutions[requested].registered_comparison_count = 0;
    curve.solutions[requested].registered_tie_count = 0;
  }
  return curve;
}

std::uint32_t DirectRoundBinary32(const ExactValue& value) {
  return static_cast<std::uint32_t>(DirectIeee(value, 23, 8, 127));
}

std::uint64_t DirectRoundBinary64(const ExactValue& value) {
  return DirectIeee(value, 52, 11, 1023);
}

ProductDecision ExhaustiveProductDecision(
    const ExactCurve& first, const ExactCurve& second,
    std::uint32_t capacity, CardinalityDomain domain) {
  if (capacity == 0) throw std::invalid_argument("zero product capacity");
  static_cast<void>(first.at(capacity));
  static_cast<void>(second.at(capacity));
  bool found = false;
  mpq_class best;
  std::uint32_t best_first = 0;
  std::uint32_t best_second = 0;
  std::uint64_t best_states = 0;
  std::uint64_t tuples = 0;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(a)) continue;
    for (std::uint32_t b = 1; b <= capacity / a; ++b) {
      if (domain == CardinalityDomain::kPowersOfTwo && !PowerOfTwo(b)) continue;
      ++tuples;
      mpq_class cost = first.at(a).sse.coefficient() +
                       second.at(b).sse.coefficient();
      cost.canonicalize();
      const std::uint64_t states = static_cast<std::uint64_t>(a) * b;
      const int ordering =
          found ? mpq_cmp(cost.get_mpq_t(), best.get_mpq_t()) : -1;
      if (!found || ordering < 0 ||
          (ordering == 0 &&
           (states > best_states ||
            (states == best_states &&
             std::pair{a, b} < std::pair{best_first, best_second})))) {
        found = true;
        best = std::move(cost);
        best_first = a;
        best_second = b;
        best_states = states;
      }
    }
  }
  if (!found) throw std::logic_error("independent product has no state");
  return ProductDecision{
      best_first, best_second, best_states,
      ExactValue(best.get_num(), best.get_den(), kSquaredExponent), tuples};
}

GlobalDecision IndependentGlobalAllocation(
    const std::vector<ExactCurve>& curves, std::uint32_t bit_budget) {
  struct State {
    bool present{false};
    mpq_class cost{0};
    std::vector<std::uint8_t> widths;
  };
  if (curves.empty()) throw std::invalid_argument("empty global allocation");
  std::vector<State> prior(bit_budget + 1), next(bit_budget + 1);
  prior[0].present = true;
  std::uint64_t transitions = 0;
  for (const ExactCurve& curve : curves) {
    std::fill(next.begin(), next.end(), State{});
    for (std::uint32_t used = 0; used <= bit_budget; ++used) {
      if (!prior[used].present) continue;
      for (std::uint8_t width = 0; width <= 8 && used + width <= bit_budget;
           ++width) {
        ++transitions;
        mpq_class cost = prior[used].cost +
                         curve.at(std::uint32_t{1} << width).sse.coefficient();
        cost.canonicalize();
        std::vector<std::uint8_t> candidate = prior[used].widths;
        candidate.push_back(width);
        State& destination = next[used + width];
        const int ordering = destination.present
                                 ? mpq_cmp(cost.get_mpq_t(),
                                           destination.cost.get_mpq_t())
                                 : -1;
        if (!destination.present || ordering < 0 ||
            (ordering == 0 && candidate < destination.widths)) {
          destination = State{true, std::move(cost), std::move(candidate)};
        }
      }
    }
    prior.swap(next);
  }
  bool found = false;
  std::uint32_t best_used = 0;
  State best;
  for (std::uint32_t used = 0; used <= bit_budget; ++used) {
    if (!prior[used].present) continue;
    const int ordering =
        found ? mpq_cmp(prior[used].cost.get_mpq_t(), best.cost.get_mpq_t())
              : -1;
    if (!found || ordering < 0 ||
        (ordering == 0 &&
         (used > best_used ||
          (used == best_used && prior[used].widths < best.widths)))) {
      found = true;
      best_used = used;
      best = prior[used];
    }
  }
  if (!found) throw std::logic_error("independent global allocation absent");
  return GlobalDecision{
      std::move(best.widths), best_used,
      ExactValue(best.cost.get_num(), best.cost.get_den(), kSquaredExponent),
      transitions};
}

}  // namespace saq::a4_v2::verifier

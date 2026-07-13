#include "exact_quantizer.hpp"

#include <algorithm>
#include <bit>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <stdexcept>
#include <utility>
#include <vector>

namespace saq::a4_1s {
namespace {

constexpr int kBinary32GridExponent = -149;
constexpr int kSquaredGridExponent = -298;

[[nodiscard]] mpz_class MpzFromU64(std::uint64_t value) {
    mpz_class result;
    mpz_import(result.get_mpz_t(), 1, 1, sizeof(value), 0, 0, &value);
    return result;
}

[[nodiscard]] CanonicalScaledRational ScaledFromCoefficient(
    const mpq_class &coefficient,
    int binary_exponent) {
    return CanonicalScaledRational(
        coefficient.get_num(), coefficient.get_den(), binary_exponent);
}

[[nodiscard]] int CompareRationals(const mpq_class &lhs,
                                   const mpq_class &rhs) noexcept {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t());
}

struct PrefixMoments {
    explicit PrefixMoments(const std::vector<ExactSupportPoint> &support_in,
                           ScalarDiagnostics *diagnostics_in)
        : support(support_in), diagnostics(diagnostics_in) {
        const std::size_t size = support.size();
        weights.resize(size + 1);
        sums.resize(size + 1);
        sums_of_squares.resize(size + 1);

        for (std::size_t index = 0; index < size; ++index) {
            if (support[index].weight <= 0) {
                throw std::invalid_argument("support weights must be positive");
            }
            if (index > 0 &&
                support[index - 1].grid_integer >= support[index].grid_integer) {
                throw std::invalid_argument(
                    "canonical support must be strictly increasing");
            }

            weights[index + 1] = weights[index] + support[index].weight;
            sums[index + 1] =
                sums[index] + support[index].weight * support[index].grid_integer;
            sums_of_squares[index + 1] =
                sums_of_squares[index] + support[index].weight *
                                             support[index].grid_integer *
                                             support[index].grid_integer;
        }
    }

    [[nodiscard]] ExactIntervalStatistics interval(std::size_t begin,
                                                   std::size_t end) const {
        if (begin >= end || end > support.size()) {
            throw std::out_of_range("interval must be nonempty and in range");
        }
        if (diagnostics != nullptr) {
            ++diagnostics->interval_evaluations;
        }

        ExactIntervalStatistics result;
        result.weight = weights[end] - weights[begin];
        result.weighted_sum = sums[end] - sums[begin];
        result.weighted_sum_of_squares =
            sums_of_squares[end] - sums_of_squares[begin];
        result.sse_numerator =
            result.weight * result.weighted_sum_of_squares -
            result.weighted_sum * result.weighted_sum;
        if (result.weight <= 0 || result.sse_numerator < 0) {
            throw std::logic_error("invalid exact weighted interval moments");
        }
        return result;
    }

    const std::vector<ExactSupportPoint> &support;
    ScalarDiagnostics *diagnostics;
    std::vector<mpz_class> weights;
    std::vector<mpz_class> sums;
    std::vector<mpz_class> sums_of_squares;
};

struct UnreducedFraction {
    mpz_class numerator{0};
    mpz_class denominator{1};
};

// Matrix oracle for one DP layer.  Rows are prefix ends m=1..H and columns
// are possible starts j=1..H of the final interval.  Following the full
// matrix construction in the fast exact 1D k-means/quantization literature,
// j>m denotes an empty final cluster:
//
//   C_i[m,j] = D_{i-1}[min(j-1,m)] + (j<=m ? CC(j,m) : 0).
//
// This is crucial.  Padding the triangular feasible region with +infinity is
// not the same construction and does not by itself give classic SMAWK a
// total-monotonicity proof.  The finite empty-cluster extension is consistent
// with A4-1S's at-most-K objective.  Because the support is strictly ordered,
// a useful split strictly improves SSE; with leftmost ties the returned final
// cluster is nonempty whenever another nonempty cluster is available.
class LayerMatrix {
  public:
    LayerMatrix(const PrefixMoments &prefixes_in,
                const std::vector<mpq_class> &previous_in,
                ScalarDiagnostics *diagnostics_in)
        : prefixes(prefixes_in),
          previous(previous_in),
          diagnostics(diagnostics_in) {}

    [[nodiscard]] int compare(std::uint32_t row,
                              std::uint32_t lhs_column,
                              std::uint32_t rhs_column) const {
        if (diagnostics != nullptr) {
            ++diagnostics->exact_comparisons;
        }
        const UnreducedFraction lhs = entry(row, lhs_column);
        const UnreducedFraction rhs = entry(row, rhs_column);
        const mpz_class lhs_cross = lhs.numerator * rhs.denominator;
        const mpz_class rhs_cross = rhs.numerator * lhs.denominator;
        const int comparison = mpz_cmp(lhs_cross.get_mpz_t(), rhs_cross.get_mpz_t());
        if (comparison == 0 && diagnostics != nullptr) {
            ++diagnostics->exact_ties;
        }
        return comparison;
    }

    [[nodiscard]] mpq_class value(std::uint32_t row,
                                  std::uint32_t column) const {
        const UnreducedFraction fraction = entry(row, column);
        mpq_class result(fraction.numerator, fraction.denominator);
        result.canonicalize();
        return result;
    }

  private:
    [[nodiscard]] UnreducedFraction entry(std::uint32_t row,
                                          std::uint32_t column) const {
        if (row == 0 || row >= previous.size() || column == 0 ||
            column >= previous.size()) {
            throw std::out_of_range("SMAWK matrix index is out of range");
        }
        if (diagnostics != nullptr) {
            ++diagnostics->matrix_entry_evaluations;
        }

        if (column > row) {
            UnreducedFraction result;
            mpz_set(result.numerator.get_mpz_t(),
                    mpq_numref(previous[row].get_mpq_t()));
            mpz_set(result.denominator.get_mpz_t(),
                    mpq_denref(previous[row].get_mpq_t()));
            return result;
        }

        const std::size_t predecessor = column - 1;
        const ExactIntervalStatistics interval = prefixes.interval(predecessor, row);

        // P/Q + N/W = (P*W + N*Q)/(Q*W).  Do not normalize here: SMAWK only
        // requires exact ordering, so cross multiplication avoids a gcd on every
        // comparison.  The selected value is canonicalized exactly once.
        UnreducedFraction result;
        mpz_mul(result.numerator.get_mpz_t(),
                mpq_numref(previous[predecessor].get_mpq_t()),
                interval.weight.get_mpz_t());
        mpz_addmul(result.numerator.get_mpz_t(),
                   interval.sse_numerator.get_mpz_t(),
                   mpq_denref(previous[predecessor].get_mpq_t()));
        mpz_mul(result.denominator.get_mpz_t(),
                mpq_denref(previous[predecessor].get_mpq_t()),
                interval.weight.get_mpz_t());
        if (result.denominator <= 0) {
            throw std::logic_error("matrix entry has a nonpositive denominator");
        }
        return result;
    }

    const PrefixMoments &prefixes;
    const std::vector<mpq_class> &previous;
    ScalarDiagnostics *diagnostics;
};

// Classic SMAWK for leftmost row minima of a full totally monotone matrix.
// Columns and rows remain sorted.  On equality the older (smaller) column is
// retained both during reduction and interpolation, implementing the frozen
// earliest-predecessor tie rule.
void SmawkLeftmostMinima(const std::vector<std::uint32_t> &rows,
                         const std::vector<std::uint32_t> &columns,
                         const LayerMatrix &matrix,
                         std::vector<std::uint32_t> *minima) {
    if (rows.empty()) {
        return;
    }
    if (columns.empty() || minima == nullptr) {
        throw std::invalid_argument("SMAWK requires nonempty columns and output");
    }

    std::vector<std::uint32_t> reduced;
    reduced.reserve(std::min(rows.size(), columns.size()));
    for (const std::uint32_t column : columns) {
        while (!reduced.empty()) {
            const std::uint32_t row = rows[reduced.size() - 1];
            // Strict comparison is intentional: an equal later column cannot be
            // the leftmost minimum for this row.
            if (matrix.compare(row, column, reduced.back()) < 0) {
                reduced.pop_back();
            } else {
                break;
            }
        }
        if (reduced.size() < rows.size()) {
            reduced.push_back(column);
        }
    }

    std::vector<std::uint32_t> odd_rows;
    odd_rows.reserve(rows.size() / 2);
    for (std::size_t index = 1; index < rows.size(); index += 2) {
        odd_rows.push_back(rows[index]);
    }
    SmawkLeftmostMinima(odd_rows, reduced, matrix, minima);

    for (std::size_t index = 0; index < rows.size(); index += 2) {
        std::size_t begin_position = 0;
        if (index > 0) {
            const std::uint32_t previous_minimum = (*minima)[rows[index - 1]];
            const auto iterator =
                std::lower_bound(reduced.begin(), reduced.end(), previous_minimum);
            if (iterator == reduced.end() || *iterator != previous_minimum) {
                throw std::logic_error("SMAWK lost the preceding odd-row minimum");
            }
            begin_position = static_cast<std::size_t>(iterator - reduced.begin());
        }

        std::size_t end_position = reduced.size() - 1;
        if (index + 1 < rows.size()) {
            const std::uint32_t next_minimum = (*minima)[rows[index + 1]];
            const auto iterator =
                std::lower_bound(reduced.begin(), reduced.end(), next_minimum);
            if (iterator == reduced.end() || *iterator != next_minimum) {
                throw std::logic_error("SMAWK lost the following odd-row minimum");
            }
            end_position = static_cast<std::size_t>(iterator - reduced.begin());
        }
        if (begin_position > end_position) {
            throw std::logic_error("SMAWK interpolation bounds are reversed");
        }

        const std::uint32_t row = rows[index];
        std::uint32_t best_column = reduced[begin_position];
        for (std::size_t position = begin_position + 1;
             position <= end_position;
             ++position) {
            const std::uint32_t candidate = reduced[position];
            if (matrix.compare(row, candidate, best_column) < 0) {
                best_column = candidate;
            }
        }
        (*minima)[row] = best_column;
    }
}

[[nodiscard]] ScalarSolution ReconstructSolution(
    std::uint32_t cardinality,
    const mpq_class &curve_value,
    const std::vector<ExactSupportPoint> &support,
    const std::vector<std::vector<std::uint32_t>> &predecessors,
    ScalarDiagnostics *diagnostics) {
    const std::size_t support_size = support.size();
    std::size_t end = support_size;
    std::vector<ScalarInterval> reverse_intervals;
    reverse_intervals.reserve(cardinality);
    mpq_class replay(0);

    for (std::uint32_t layer = cardinality; layer > 0; --layer) {
        if (end >= predecessors[layer].size()) {
            throw std::logic_error("predecessor replay index is out of range");
        }
        const std::uint32_t begin = predecessors[layer][end];
        if (begin == std::numeric_limits<std::uint32_t>::max() || begin >= end) {
            throw std::logic_error("predecessor replay produced an empty interval");
        }
        // Replay through the deliberately independent point-by-point helper,
        // not the PrefixMoments path used by the optimized DP matrix.  This
        // makes a shared prefix/statistics defect observable before a curve is
        // returned or serialized.
        const ExactIntervalStatistics interval =
            ComputeIntervalStatistics(support, begin, end);
        replay += mpq_class(interval.sse_numerator, interval.weight);
        reverse_intervals.push_back(ScalarInterval{
            begin, static_cast<std::uint32_t>(end), interval.mean()});
        end = begin;
    }
    if (end != 0) {
        throw std::logic_error("predecessor replay did not consume the support");
    }
    replay.canonicalize();
    if (CompareRationals(replay, curve_value) != 0) {
        throw std::logic_error("exact scalar curve replay mismatch");
    }
    if (diagnostics != nullptr) {
        ++diagnostics->exact_replay_checks;
    }

    std::reverse(reverse_intervals.begin(), reverse_intervals.end());
    ScalarSolution result;
    result.requested_cardinality = cardinality;
    result.effective_cardinality = cardinality;
    result.sse = ScaledFromCoefficient(curve_value, kSquaredGridExponent);
    result.intervals = std::move(reverse_intervals);
    return result;
}

[[nodiscard]] bool IsPowerOfTwo(std::uint32_t value) noexcept {
    return value != 0 && (value & (value - 1)) == 0;
}

[[nodiscard]] long FloorLog2PositiveRatio(const mpz_class &numerator,
                                          const mpz_class &denominator) {
    if (numerator <= 0 || denominator <= 0) {
        throw std::invalid_argument("log2 ratio requires positive operands");
    }
    const long numerator_bits =
        static_cast<long>(mpz_sizeinbase(numerator.get_mpz_t(), 2));
    const long denominator_bits =
        static_cast<long>(mpz_sizeinbase(denominator.get_mpz_t(), 2));
    long exponent = numerator_bits - denominator_bits;

    int comparison = 0;
    if (exponent >= 0) {
        mpz_class shifted_denominator;
        mpz_mul_2exp(shifted_denominator.get_mpz_t(), denominator.get_mpz_t(),
                     static_cast<mp_bitcnt_t>(exponent));
        comparison =
            mpz_cmp(numerator.get_mpz_t(), shifted_denominator.get_mpz_t());
    } else {
        mpz_class shifted_numerator;
        mpz_mul_2exp(shifted_numerator.get_mpz_t(), numerator.get_mpz_t(),
                     static_cast<mp_bitcnt_t>(-exponent));
        comparison =
            mpz_cmp(shifted_numerator.get_mpz_t(), denominator.get_mpz_t());
    }
    if (comparison < 0) {
        --exponent;
    }
    return exponent;
}

[[nodiscard]] mpz_class RoundPositiveRatioToInteger(
    const mpz_class &numerator,
    const mpz_class &denominator) {
    if (numerator < 0 || denominator <= 0) {
        throw std::invalid_argument("rounding requires a nonnegative ratio");
    }
    mpz_class quotient;
    mpz_class remainder;
    mpz_tdiv_qr(quotient.get_mpz_t(), remainder.get_mpz_t(),
                numerator.get_mpz_t(), denominator.get_mpz_t());
    const mpz_class doubled_remainder = remainder * 2;
    const int midpoint =
        mpz_cmp(doubled_remainder.get_mpz_t(), denominator.get_mpz_t());
    if (midpoint > 0 || (midpoint == 0 && mpz_odd_p(quotient.get_mpz_t()) != 0)) {
        ++quotient;
    }
    return quotient;
}

[[nodiscard]] mpz_class RoundScaledPositiveRatioToInteger(
    const mpz_class &numerator,
    const mpz_class &denominator,
    long binary_shift) {
    if (binary_shift >= 0) {
        mpz_class shifted_numerator;
        mpz_mul_2exp(shifted_numerator.get_mpz_t(), numerator.get_mpz_t(),
                     static_cast<mp_bitcnt_t>(binary_shift));
        return RoundPositiveRatioToInteger(shifted_numerator, denominator);
    }
    mpz_class shifted_denominator;
    mpz_mul_2exp(shifted_denominator.get_mpz_t(), denominator.get_mpz_t(),
                 static_cast<mp_bitcnt_t>(-binary_shift));
    return RoundPositiveRatioToInteger(numerator, shifted_denominator);
}

[[nodiscard]] std::uint64_t RoundExactToIeeeBits(
    const CanonicalScaledRational &input,
    int fraction_bits,
    int exponent_bits,
    int exponent_bias) {
    if (input.denominator <= 0) {
        throw std::invalid_argument("exact rational denominator must be positive");
    }
    const int total_bits = 1 + exponent_bits + fraction_bits;
    if (total_bits > 64 || fraction_bits <= 0 || exponent_bits <= 1) {
        throw std::invalid_argument("unsupported IEEE target format");
    }

    const bool negative = input.numerator < 0;
    const mpz_class magnitude = negative ? -input.numerator : input.numerator;
    const std::uint64_t sign_bit =
        negative ? (std::uint64_t{1} << (total_bits - 1)) : 0;
    if (magnitude == 0) {
        return 0; // Exact zero is canonical +0.
    }

    const long ratio_exponent =
        FloorLog2PositiveRatio(magnitude, input.denominator);
    const long value_exponent =
        ratio_exponent + static_cast<long>(input.binary_exponent);
    const long minimum_normal_exponent = 1L - exponent_bias;
    const long maximum_normal_exponent = exponent_bias;
    const std::uint64_t hidden_bit = std::uint64_t{1} << fraction_bits;
    const std::uint64_t carry_bit = hidden_bit << 1;

    mpz_class rounded;
    std::uint64_t exponent_field = 0;
    std::uint64_t fraction_field = 0;
    if (value_exponent >= minimum_normal_exponent) {
        const long shift = static_cast<long>(input.binary_exponent) -
                           value_exponent + fraction_bits;
        rounded = RoundScaledPositiveRatioToInteger(
            magnitude, input.denominator, shift);
        if (mpz_sizeinbase(rounded.get_mpz_t(), 2) >
            static_cast<std::size_t>(fraction_bits + 2)) {
            throw std::logic_error("normal significand rounding overflowed twice");
        }
        std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
        long encoded_exponent = value_exponent;
        if (significand == carry_bit) {
            significand >>= 1;
            ++encoded_exponent;
        }
        if (encoded_exponent > maximum_normal_exponent) {
            throw std::overflow_error("exact rational rounds to IEEE infinity");
        }
        if (significand < hidden_bit || significand >= carry_bit) {
            throw std::logic_error("normal significand is outside its target binade");
        }
        exponent_field =
            static_cast<std::uint64_t>(encoded_exponent + exponent_bias);
        fraction_field = significand - hidden_bit;
    } else {
        const long minimum_subnormal_exponent =
            minimum_normal_exponent - fraction_bits;
        const long shift = static_cast<long>(input.binary_exponent) -
                           minimum_subnormal_exponent;
        rounded = RoundScaledPositiveRatioToInteger(
            magnitude, input.denominator, shift);
        if (mpz_sizeinbase(rounded.get_mpz_t(), 2) >
            static_cast<std::size_t>(fraction_bits + 1)) {
            throw std::logic_error("subnormal significand is too large");
        }
        const std::uint64_t significand = mpz_get_ui(rounded.get_mpz_t());
        if (significand > hidden_bit) {
            throw std::logic_error("subnormal rounding skipped the normal boundary");
        }
        if (significand == hidden_bit) {
            exponent_field = 1; // Rounded to the smallest normal value.
            fraction_field = 0;
        } else {
            exponent_field = 0;
            fraction_field = significand;
        }
    }

    const std::uint64_t maximum_exponent_field =
        (std::uint64_t{1} << exponent_bits) - 1;
    if (exponent_field == maximum_exponent_field ||
        fraction_field >= hidden_bit) {
        throw std::logic_error("invalid finite IEEE encoding");
    }
    return sign_bit | (exponent_field << fraction_bits) | fraction_field;
}

} // namespace

CanonicalScaledRational::CanonicalScaledRational(mpz_class numerator_in,
                                                 mpz_class denominator_in,
                                                 int binary_exponent_in)
    : binary_exponent(binary_exponent_in) {
    if (denominator_in == 0) {
        throw std::invalid_argument("exact rational denominator must be nonzero");
    }
    mpq_class canonical(std::move(numerator_in), std::move(denominator_in));
    canonical.canonicalize();
    numerator = canonical.get_num();
    denominator = canonical.get_den();
}

mpq_class CanonicalScaledRational::coefficient() const {
    if (denominator <= 0) {
        throw std::logic_error("noncanonical exact rational denominator");
    }
    mpq_class result(numerator, denominator);
    result.canonicalize();
    return result;
}

mpq_class CanonicalScaledRational::value() const {
    mpq_class result = coefficient();
    mpz_class factor(1);
    if (binary_exponent >= 0) {
        mpz_mul_2exp(factor.get_mpz_t(), factor.get_mpz_t(),
                     static_cast<mp_bitcnt_t>(binary_exponent));
        result *= factor;
    } else {
        mpz_mul_2exp(factor.get_mpz_t(), factor.get_mpz_t(),
                     static_cast<mp_bitcnt_t>(-binary_exponent));
        result /= factor;
    }
    result.canonicalize();
    return result;
}

CanonicalScaledRational ExactIntervalStatistics::sse() const {
    if (weight <= 0 || sse_numerator < 0) {
        throw std::logic_error("invalid exact interval SSE");
    }
    return CanonicalScaledRational(
        sse_numerator, weight, kSquaredGridExponent);
}

CanonicalScaledRational ExactIntervalStatistics::mean() const {
    if (weight <= 0) {
        throw std::logic_error("invalid exact interval mean");
    }
    return CanonicalScaledRational(
        weighted_sum, weight, kBinary32GridExponent);
}

const ScalarSolution &ScalarCurveResult::at(
    std::uint32_t cardinality) const {
    if (cardinality == 0 || cardinality >= solutions.size()) {
        throw std::out_of_range("scalar curve cardinality is unavailable");
    }
    return solutions[cardinality];
}

mpz_class DecodeBinary32GridInteger(std::uint32_t bits) {
    const std::uint32_t exponent = (bits >> 23U) & 0xffU;
    const std::uint32_t fraction = bits & 0x7fffffU;
    if (exponent == 0xffU) {
        throw std::invalid_argument("A4-1S scalar inputs must be finite binary32");
    }

    mpz_class result;
    if (exponent == 0) {
        result = static_cast<unsigned long>(fraction);
    } else {
        const std::uint32_t mantissa = (std::uint32_t{1} << 23U) | fraction;
        result = static_cast<unsigned long>(mantissa);
        mpz_mul_2exp(result.get_mpz_t(), result.get_mpz_t(), exponent - 1U);
    }
    if ((bits >> 31U) != 0 && result != 0) {
        result = -result;
    }
    return result;
}

std::uint32_t Binary32Bits(float value) noexcept {
    return std::bit_cast<std::uint32_t>(value);
}

std::uint64_t Binary64Bits(double value) noexcept {
    return std::bit_cast<std::uint64_t>(value);
}

float Binary32FromBits(std::uint32_t bits) noexcept {
    return std::bit_cast<float>(bits);
}

double Binary64FromBits(std::uint64_t bits) noexcept {
    return std::bit_cast<double>(bits);
}

std::vector<ExactSupportPoint> CanonicalizeSupport(
    const std::vector<WeightedBinary32> &samples) {
    if (samples.empty()) {
        throw std::invalid_argument("scalar fit inventory must not be empty");
    }

    struct Aggregate {
        mpz_class weight{0};
        std::uint64_t lowest_vector_id{0};
    };
    std::map<mpz_class, Aggregate> aggregates;
    for (const WeightedBinary32 &sample : samples) {
        if (sample.weight == 0) {
            throw std::invalid_argument("scalar fit weights must be positive");
        }
        const mpz_class value = DecodeBinary32GridInteger(sample.bits);
        const auto [iterator, inserted] =
            aggregates.try_emplace(value, Aggregate{});
        Aggregate &aggregate = iterator->second;
        aggregate.weight += MpzFromU64(sample.weight);
        if (inserted || sample.vector_id < aggregate.lowest_vector_id) {
            aggregate.lowest_vector_id = sample.vector_id;
        }
    }

    std::vector<ExactSupportPoint> support;
    support.reserve(aggregates.size());
    for (auto &[value, aggregate] : aggregates) {
        support.push_back(ExactSupportPoint{
            value, std::move(aggregate.weight), aggregate.lowest_vector_id});
    }
    return support;
}

ExactIntervalStatistics ComputeIntervalStatistics(
    const std::vector<ExactSupportPoint> &support,
    std::size_t begin,
    std::size_t end) {
    if (begin >= end || end > support.size()) {
        throw std::out_of_range("interval must be nonempty and in range");
    }
    ExactIntervalStatistics result;
    for (std::size_t index = begin; index < end; ++index) {
        const ExactSupportPoint &point = support[index];
        if (point.weight <= 0) {
            throw std::invalid_argument("support weights must be positive");
        }
        result.weight += point.weight;
        result.weighted_sum += point.weight * point.grid_integer;
        result.weighted_sum_of_squares +=
            point.weight * point.grid_integer * point.grid_integer;
    }
    result.sse_numerator =
        result.weight * result.weighted_sum_of_squares -
        result.weighted_sum * result.weighted_sum;
    if (result.sse_numerator < 0) {
        throw std::logic_error("weighted interval SSE numerator is negative");
    }
    return result;
}

ScalarCurveResult FitExactScalarCurve(
    const std::vector<WeightedBinary32> &samples,
    std::uint32_t maximum_cardinality) {
    if (maximum_cardinality == 0) {
        throw std::invalid_argument("maximum scalar cardinality must be positive");
    }

    ScalarCurveResult result;
    result.support = CanonicalizeSupport(samples);
    if (result.support.size() >
        std::numeric_limits<std::uint32_t>::max()) {
        throw std::length_error("scalar support is too large for frozen indices");
    }
    const std::uint32_t support_size =
        static_cast<std::uint32_t>(result.support.size());
    const std::uint32_t effective_maximum =
        std::min(maximum_cardinality, support_size);
    result.solutions.resize(static_cast<std::size_t>(maximum_cardinality) + 1);
    result.predecessors.assign(
        static_cast<std::size_t>(effective_maximum) + 1,
        std::vector<std::uint32_t>(
            static_cast<std::size_t>(support_size) + 1,
            std::numeric_limits<std::uint32_t>::max()));
    result.diagnostics.predecessor_monotone.assign(
        static_cast<std::size_t>(effective_maximum) + 1, 0);
    result.diagnostics.exact_comparisons_by_cardinality.assign(
        static_cast<std::size_t>(maximum_cardinality) + 1, 0);
    result.diagnostics.exact_ties_by_cardinality.assign(
        static_cast<std::size_t>(maximum_cardinality) + 1, 0);
    for (std::uint32_t layer = 1; layer <= effective_maximum; ++layer) {
        result.predecessors[layer][0] = 0;
    }

    PrefixMoments prefixes(result.support, &result.diagnostics);
    std::vector<mpq_class> previous(
        static_cast<std::size_t>(support_size) + 1, mpq_class(0));
    std::vector<mpq_class> current(
        static_cast<std::size_t>(support_size) + 1, mpq_class(0));

    // One interval is the base DP layer and needs no matrix search.
    for (std::uint32_t prefix = 1; prefix <= support_size; ++prefix) {
        const ExactIntervalStatistics interval = prefixes.interval(0, prefix);
        previous[prefix] = mpq_class(interval.sse_numerator, interval.weight);
        previous[prefix].canonicalize();
        result.predecessors[1][prefix] = 0;
    }
    result.diagnostics.predecessor_monotone[1] = 1;
    result.solutions[1] = ReconstructSolution(
        1, previous[support_size], result.support, result.predecessors,
        &result.diagnostics);

    std::vector<std::uint32_t> rows(support_size);
    std::vector<std::uint32_t> columns(support_size);
    for (std::uint32_t index = 0; index < support_size; ++index) {
        rows[index] = index + 1;
        columns[index] = index + 1;
    }

    for (std::uint32_t layer = 2; layer <= effective_maximum; ++layer) {
        const std::uint64_t comparisons_before =
            result.diagnostics.exact_comparisons;
        const std::uint64_t ties_before = result.diagnostics.exact_ties;
        LayerMatrix matrix(prefixes, previous, &result.diagnostics);
        std::vector<std::uint32_t> minima(
            static_cast<std::size_t>(support_size) + 1, 0);
        SmawkLeftmostMinima(rows, columns, matrix, &minima);

        current[0] = 0;
        std::uint32_t prior_predecessor = 0;
        bool monotone = true;
        for (std::uint32_t prefix = 1; prefix <= support_size; ++prefix) {
            const std::uint32_t column = minima[prefix];
            if (column == 0 || column > prefix) {
                // With strictly distinct support, a nonempty final interval is always
                // at least as good as an empty one, and the smaller-column tie rule
                // must select it.  Reaching this branch is an implementation defect.
                throw std::logic_error("SMAWK selected an empty final interval");
            }
            const std::uint32_t predecessor = column - 1;
            result.predecessors[layer][prefix] = predecessor;
            current[prefix] = matrix.value(prefix, column);
            if (prefix > 1 && predecessor < prior_predecessor) {
                monotone = false;
            }
            prior_predecessor = predecessor;
        }
        result.diagnostics.predecessor_monotone[layer] = monotone ? 1 : 0;
        if (!monotone) {
            throw std::logic_error("exact SMAWK predecessors are not monotone");
        }

        result.solutions[layer] = ReconstructSolution(
            layer, current[support_size], result.support, result.predecessors,
            &result.diagnostics);
        result.diagnostics.exact_comparisons_by_cardinality[layer] =
            result.diagnostics.exact_comparisons - comparisons_before;
        result.diagnostics.exact_ties_by_cardinality[layer] =
            result.diagnostics.exact_ties - ties_before;
        previous.swap(current);
    }

    // K>H uses the H-point solution without manufacturing duplicate labels.
    for (std::uint32_t requested = effective_maximum + 1;
         requested <= maximum_cardinality;
         ++requested) {
        result.solutions[requested] = result.solutions[effective_maximum];
        result.solutions[requested].requested_cardinality = requested;
        result.solutions[requested].effective_cardinality = support_size;
    }
    return result;
}

std::uint32_t RoundExactToBinary32Bits(
    const CanonicalScaledRational &value) {
    return static_cast<std::uint32_t>(
        RoundExactToIeeeBits(value, 23, 8, 127));
}

std::uint64_t RoundExactToBinary64Bits(
    const CanonicalScaledRational &value) {
    return RoundExactToIeeeBits(value, 52, 11, 1023);
}

ProductAllocation AllocateProduct2(
    const ScalarCurveResult &first,
    const ScalarCurveResult &second,
    std::uint32_t capacity,
    ProductCardinalitySet cardinality_set) {
    if (capacity == 0) {
        throw std::invalid_argument("product capacity must be positive");
    }
    // Validate availability before beginning a partial search.
    static_cast<void>(first.at(capacity));
    static_cast<void>(second.at(capacity));

    bool found = false;
    mpq_class best_cost;
    std::uint32_t best_first = 0;
    std::uint32_t best_second = 0;
    std::uint64_t best_product = 0;
    std::uint64_t candidate_evaluation_count = 0;
    for (std::uint32_t first_cardinality = 1;
         first_cardinality <= capacity;
         ++first_cardinality) {
        if (cardinality_set == ProductCardinalitySet::kPowersOfTwo &&
            !IsPowerOfTwo(first_cardinality)) {
            continue;
        }
        const std::uint32_t second_limit = capacity / first_cardinality;
        std::uint32_t second_cardinality = second_limit;
        if (cardinality_set == ProductCardinalitySet::kPowersOfTwo) {
            second_cardinality = std::uint32_t{1}
                                 << (31U - std::countl_zero(second_limit));
        }
        // Scalar at-most-K SSE is nonincreasing.  For a fixed first K, the
        // largest feasible allowed second K therefore has minimum SSE; if a
        // plateau ties a smaller K, it also wins the registered larger-product
        // tie.  Exactly one second candidate per first K is sufficient.
        ++candidate_evaluation_count;
        const ScalarSolution &first_solution = first.at(first_cardinality);
        const ScalarSolution &second_solution = second.at(second_cardinality);
        if (first_solution.sse.binary_exponent != kSquaredGridExponent ||
            second_solution.sse.binary_exponent != kSquaredGridExponent) {
            throw std::invalid_argument("product curves use incompatible SSE scales");
        }
        mpq_class candidate = first_solution.sse.coefficient() +
                              second_solution.sse.coefficient();
        candidate.canonicalize();
        const std::uint64_t product =
            static_cast<std::uint64_t>(first_cardinality) * second_cardinality;

        bool replace = !found;
        if (found) {
            const int comparison = CompareRationals(candidate, best_cost);
            replace = comparison < 0 ||
                      (comparison == 0 &&
                       (product > best_product ||
                        (product == best_product &&
                         std::pair{first_cardinality, second_cardinality} <
                             std::pair{best_first, best_second})));
        }
        if (replace) {
            found = true;
            best_cost = std::move(candidate);
            best_first = first_cardinality;
            best_second = second_cardinality;
            best_product = product;
        }
    }
    if (!found) {
        throw std::logic_error("product allocation has no feasible state");
    }

    ProductAllocation result;
    result.first_cardinality = best_first;
    result.second_cardinality = best_second;
    result.used_states = best_product;
    result.capacity = capacity;
    result.sse = ScaledFromCoefficient(best_cost, kSquaredGridExponent);
    result.nominal_alphabets_reachable =
        first.at(best_first).effective_cardinality == best_first &&
        second.at(best_second).effective_cardinality == best_second;
    result.optimized_candidate_evaluation_count = candidate_evaluation_count;
    return result;
}

GlobalDyadicAllocation AllocateGlobalDyadicCap8(
    const std::vector<ScalarCurveResult> &coordinate_curves,
    std::uint32_t bit_budget) {
    if (coordinate_curves.empty()) {
        throw std::invalid_argument("global allocation needs at least one curve");
    }
    for (const ScalarCurveResult &curve : coordinate_curves) {
        static_cast<void>(curve.at(256));
    }

    struct State {
        bool reachable{false};
        mpq_class cost{0};
        std::vector<std::uint8_t> bits;
    };
    std::vector<State> previous(static_cast<std::size_t>(bit_budget) + 1);
    std::vector<State> current(static_cast<std::size_t>(bit_budget) + 1);
    previous[0].reachable = true;
    std::uint64_t transition_evaluation_count = 0;

    for (const ScalarCurveResult &curve : coordinate_curves) {
        for (State &state : current) {
            state = State{};
        }
        for (std::uint32_t used = 0; used <= bit_budget; ++used) {
            if (!previous[used].reachable) {
                continue;
            }
            for (std::uint8_t bits = 0; bits <= 8; ++bits) {
                if (used + bits > bit_budget) {
                    break;
                }
                ++transition_evaluation_count;
                const std::uint32_t cardinality = std::uint32_t{1} << bits;
                const ScalarSolution &solution = curve.at(cardinality);
                if (solution.sse.binary_exponent != kSquaredGridExponent) {
                    throw std::invalid_argument("global curves use incompatible SSE scales");
                }
                const std::uint32_t next_used = used + bits;
                mpq_class candidate_cost =
                    previous[used].cost + solution.sse.coefficient();
                candidate_cost.canonicalize();
                std::vector<std::uint8_t> candidate_bits = previous[used].bits;
                candidate_bits.push_back(bits);

                State &destination = current[next_used];
                bool replace = !destination.reachable;
                if (destination.reachable) {
                    const int comparison =
                        CompareRationals(candidate_cost, destination.cost);
                    replace = comparison < 0 ||
                              (comparison == 0 &&
                               std::lexicographical_compare(
                                   candidate_bits.begin(), candidate_bits.end(),
                                   destination.bits.begin(), destination.bits.end()));
                }
                if (replace) {
                    destination.reachable = true;
                    destination.cost = std::move(candidate_cost);
                    destination.bits = std::move(candidate_bits);
                }
            }
        }
        previous.swap(current);
    }

    bool found = false;
    std::uint32_t best_used = 0;
    State best;
    for (std::uint32_t used = 0; used <= bit_budget; ++used) {
        const State &candidate = previous[used];
        if (!candidate.reachable) {
            continue;
        }
        bool replace = !found;
        if (found) {
            const int comparison = CompareRationals(candidate.cost, best.cost);
            replace = comparison < 0 ||
                      (comparison == 0 &&
                       (used > best_used ||
                        (used == best_used &&
                         std::lexicographical_compare(
                             candidate.bits.begin(), candidate.bits.end(),
                             best.bits.begin(), best.bits.end()))));
        }
        if (replace) {
            found = true;
            best_used = used;
            best = candidate;
        }
    }
    if (!found) {
        throw std::logic_error("global dyadic allocation has no feasible state");
    }

    GlobalDyadicAllocation result;
    result.bit_widths = std::move(best.bits);
    result.used_bits = best_used;
    result.bit_budget = bit_budget;
    result.sse = ScaledFromCoefficient(best.cost, kSquaredGridExponent);
    result.transition_evaluation_count = transition_evaluation_count;
    result.nominal_alphabets_reachable = true;
    for (std::size_t coordinate = 0;
         coordinate < coordinate_curves.size();
         ++coordinate) {
        const std::uint32_t cardinality =
            std::uint32_t{1} << result.bit_widths[coordinate];
        if (coordinate_curves[coordinate].at(cardinality).effective_cardinality != cardinality) {
            result.nominal_alphabets_reachable = false;
            break;
        }
    }
    return result;
}

} // namespace saq::a4_1s

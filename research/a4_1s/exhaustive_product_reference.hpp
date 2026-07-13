#pragma once

#include "exact_quantizer.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>

namespace saq::a4_1s {

// Structurally independent product-allocation authority for the bounded
// representation suite.  Exact GMP work is confined to constructing the
// objective equivalence classes for this actual pair of curves.  Every
// feasible nominal tuple is then visited and compared by its integer class
// rank followed by the frozen product/lexicographic ordering.  This helper
// deliberately never calls AllocateProduct2 or a production tie helper.
struct ExhaustiveProductReferenceDecision {
    std::uint32_t first_cardinality{0};
    std::uint32_t second_cardinality{0};
    std::uint64_t used_states{0};
    std::uint32_t capacity{0};
    CanonicalScaledRational sse;
    bool nominal_alphabets_reachable{false};
    std::uint64_t feasible_tuple_evaluation_count{0};
    std::uint32_t exact_objective_class_count{0};
};

namespace exhaustive_product_reference_detail {

struct ObjectiveClassRanks {
    std::vector<std::vector<std::uint32_t>> rank_by_effective_cardinality;
    std::vector<CanonicalScaledRational> objectives;
};

[[nodiscard]] inline int CompareExact(const mpq_class &lhs,
                                      const mpq_class &rhs) noexcept {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t());
}

[[nodiscard]] inline bool IsPowerOfTwo(std::uint32_t value) noexcept {
    return value != 0 && (value & (value - 1U)) == 0;
}

[[nodiscard]] inline ObjectiveClassRanks BuildObjectiveClassRanks(
    const ScalarCurveResult &first,
    const ScalarCurveResult &second,
    std::uint32_t capacity) {
    const std::uint32_t first_support =
        first.at(capacity).effective_cardinality;
    const std::uint32_t second_support =
        second.at(capacity).effective_cardinality;
    if (first_support == 0 || second_support == 0) {
        throw std::invalid_argument(
            "exhaustive product reference requires nonempty curves");
    }

    std::vector<std::vector<mpq_class>> exact_sums(
        static_cast<std::size_t>(first_support) + 1,
        std::vector<mpq_class>(static_cast<std::size_t>(second_support) + 1));
    std::vector<mpq_class> distinct;
    distinct.reserve(static_cast<std::size_t>(first_support) * second_support);
    for (std::uint32_t first_effective = 1;
         first_effective <= first_support;
         ++first_effective) {
        const ScalarSolution &first_solution = first.at(first_effective);
        if (first_solution.sse.binary_exponent != -298) {
            throw std::invalid_argument(
                "exhaustive product first curve has the wrong SSE scale");
        }
        for (std::uint32_t second_effective = 1;
             second_effective <= second_support;
             ++second_effective) {
            const ScalarSolution &second_solution = second.at(second_effective);
            if (second_solution.sse.binary_exponent != -298) {
                throw std::invalid_argument(
                    "exhaustive product second curve has the wrong SSE scale");
            }
            mpq_class sum = first_solution.sse.coefficient() +
                            second_solution.sse.coefficient();
            sum.canonicalize();
            exact_sums[first_effective][second_effective] = sum;
            distinct.push_back(std::move(sum));
        }
    }
    std::sort(distinct.begin(), distinct.end(),
              [](const mpq_class &lhs, const mpq_class &rhs) {
                  return CompareExact(lhs, rhs) < 0;
              });
    distinct.erase(
        std::unique(distinct.begin(), distinct.end(),
                    [](const mpq_class &lhs, const mpq_class &rhs) {
                        return CompareExact(lhs, rhs) == 0;
                    }),
        distinct.end());

    ObjectiveClassRanks result;
    result.rank_by_effective_cardinality.assign(
        static_cast<std::size_t>(first_support) + 1,
        std::vector<std::uint32_t>(
            static_cast<std::size_t>(second_support) + 1, 0));
    result.objectives.reserve(distinct.size());
    for (const mpq_class &objective : distinct) {
        result.objectives.emplace_back(
            objective.get_num(), objective.get_den(), -298);
    }
    for (std::uint32_t first_effective = 1;
         first_effective <= first_support;
         ++first_effective) {
        for (std::uint32_t second_effective = 1;
             second_effective <= second_support;
             ++second_effective) {
            const mpq_class &objective =
                exact_sums[first_effective][second_effective];
            std::uint32_t rank = 0;
            while (rank < distinct.size() &&
                   CompareExact(distinct[rank], objective) != 0) {
                ++rank;
            }
            if (rank == distinct.size()) {
                throw std::logic_error(
                    "exhaustive product objective class was not ranked");
            }
            result.rank_by_effective_cardinality[first_effective]
                                                        [second_effective] = rank;
        }
    }
    return result;
}

} // namespace exhaustive_product_reference_detail

[[nodiscard]] inline ExhaustiveProductReferenceDecision
EnumerateProductAllocationReference(
    const ScalarCurveResult &first,
    const ScalarCurveResult &second,
    std::uint32_t capacity,
    bool dyadic_only) {
    using exhaustive_product_reference_detail::BuildObjectiveClassRanks;
    using exhaustive_product_reference_detail::IsPowerOfTwo;

    if (capacity == 0) {
        throw std::invalid_argument(
            "exhaustive product capacity must be positive");
    }
    const auto classes = BuildObjectiveClassRanks(first, second, capacity);
    std::vector<std::uint32_t> first_effective(
        static_cast<std::size_t>(capacity) + 1, 0);
    std::vector<std::uint32_t> second_effective(
        static_cast<std::size_t>(capacity) + 1, 0);
    for (std::uint32_t cardinality = 1;
         cardinality <= capacity;
         ++cardinality) {
        first_effective[cardinality] =
            first.at(cardinality).effective_cardinality;
        second_effective[cardinality] =
            second.at(cardinality).effective_cardinality;
    }

    bool found = false;
    std::uint32_t best_rank = 0;
    std::uint32_t best_first = 0;
    std::uint32_t best_second = 0;
    std::uint64_t best_product = 0;
    std::uint64_t evaluated = 0;
    for (std::uint32_t first_cardinality = 1;
         first_cardinality <= capacity;
         ++first_cardinality) {
        if (dyadic_only && !IsPowerOfTwo(first_cardinality)) {
            continue;
        }
        for (std::uint32_t second_cardinality = 1;
             second_cardinality <= capacity / first_cardinality;
             ++second_cardinality) {
            if (dyadic_only && !IsPowerOfTwo(second_cardinality)) {
                continue;
            }
            ++evaluated;
            const std::uint32_t rank =
                classes.rank_by_effective_cardinality
                    [first_effective[first_cardinality]]
                    [second_effective[second_cardinality]];
            const std::uint64_t product =
                static_cast<std::uint64_t>(first_cardinality) *
                second_cardinality;

            // This is intentionally spelled out instead of sharing the
            // production selector: lower exact class, larger product, then
            // lexicographically lower nominal tuple.
            const bool replace =
                !found || rank < best_rank ||
                (rank == best_rank &&
                 (product > best_product ||
                  (product == best_product &&
                   (first_cardinality < best_first ||
                    (first_cardinality == best_first &&
                     second_cardinality < best_second)))));
            if (replace) {
                found = true;
                best_rank = rank;
                best_first = first_cardinality;
                best_second = second_cardinality;
                best_product = product;
            }
        }
    }
    if (!found || best_rank >= classes.objectives.size()) {
        throw std::logic_error(
            "exhaustive product reference found no feasible tuple");
    }

    ExhaustiveProductReferenceDecision result;
    result.first_cardinality = best_first;
    result.second_cardinality = best_second;
    result.used_states = best_product;
    result.capacity = capacity;
    result.sse = classes.objectives[best_rank];
    result.nominal_alphabets_reachable =
        first_effective[best_first] == best_first &&
        second_effective[best_second] == best_second;
    result.feasible_tuple_evaluation_count = evaluated;
    result.exact_objective_class_count =
        static_cast<std::uint32_t>(classes.objectives.size());
    return result;
}

} // namespace saq::a4_1s

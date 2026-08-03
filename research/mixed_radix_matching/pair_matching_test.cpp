#include "pair_matching.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

using mixedradix::matching::Result;
using mixedradix::matching::WeightedEdge;

double edge_weight(
        const std::vector<WeightedEdge>& edges,
        std::size_t first, std::size_t second) {
    const auto ordered = std::minmax(first, second);
    for (const auto& edge : edges)
        if (edge.first == ordered.first && edge.second == ordered.second)
            return edge.weight;
    throw std::logic_error("test edge missing");
}

double exhaustive(
        const std::vector<WeightedEdge>& edges,
        std::vector<bool>& used) {
    const auto first = std::find(used.begin(), used.end(), false);
    if (first == used.end()) return 0;
    const std::size_t vertex = first - used.begin();
    used[vertex] = true;
    double best = -std::numeric_limits<double>::infinity();
    for (std::size_t other = vertex + 1; other < used.size(); ++other) {
        if (used[other]) continue;
        used[other] = true;
        best = std::max(
                best, edge_weight(edges, vertex, other) +
                              exhaustive(edges, used));
        used[other] = false;
    }
    used[vertex] = false;
    return best;
}

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void test_against_exhaustive() {
    for (std::size_t n : {2U, 4U, 6U, 8U, 10U}) {
        for (std::size_t seed = 0; seed < 7; ++seed) {
            std::vector<WeightedEdge> edges;
            for (std::size_t first = 0; first < n; ++first)
                for (std::size_t second = first + 1; second < n; ++second) {
                    const int raw = static_cast<int>((
                            first * 37 + second * 17 +
                            first * second * 11 + seed * 13) % 29);
                    edges.push_back(
                            {first, second, static_cast<double>(raw - 14)});
                }
            const Result actual =
                    mixedradix::matching::maximum_weight_perfect_matching(
                            n, edges);
            const Result repeated =
                    mixedradix::matching::maximum_weight_perfect_matching(
                            n, edges);
            std::vector<bool> used(n, false);
            const double expected = exhaustive(edges, used);
            require(actual.pairs.size() == n / 2,
                    "not a perfect matching");
            require(actual.weight == expected,
                    "matching is not maximum weight");
            require(actual.pairs == repeated.pairs,
                    "matching is not deterministic");
        }
    }
}

a4or::CurveEntry entry(double sse) {
    return {sse, {}, {}, false};
}

std::vector<a4or::CurveEntry> saturation_curve(std::size_t cardinality) {
    std::vector<a4or::CurveEntry> curve;
    curve.reserve(16);
    for (std::size_t k = 1; k <= 16; ++k) {
        double sse = 0;
        if (k < cardinality)
            sse = 10.0 * static_cast<double>(cardinality - k);
        curve.push_back(entry(sse));
    }
    return curve;
}

void test_cardinality_cross_pairing() {
    a4orb::Curves curves;
    curves.histogram_bins = 16;
    curves.coordinates = {
            saturation_curve(3), saturation_curve(3),
            saturation_curve(5), saturation_curve(5)};

    const auto edges = mixedradix::matching::allocation_edges(
            curves, 4, false);
    const Result result =
            mixedradix::matching::maximum_weight_perfect_matching(4, edges);
    require(result.weight == 0.0, "unexpected arbitrary matching SSE");
    require(result.pairs.size() == 2, "cross-pairing cardinality");
    for (const auto& [first, second] : result.pairs)
        require((first < 2) != (second < 2),
                "matching did not recover complementary cardinalities");

    double same_pair_gain = 0;
    for (const auto& [first, second] : result.pairs) {
        const auto arbitrary = a4or::allocate_pair(
                curves.coordinates[first], curves.coordinates[second],
                4, false);
        const auto dyadic = a4or::allocate_pair(
                curves.coordinates[first], curves.coordinates[second],
                4, true);
        require(arbitrary.used_states == 15, "expected 3x5 allocation");
        require(dyadic.sse - arbitrary.sse == 10.0,
                "same-pair A/D gain was not isolated");
        same_pair_gain += dyadic.sse - arbitrary.sse;
    }
    require(same_pair_gain == 20.0, "unexpected reported radix gain");
}

void test_128_coordinate_scale() {
    constexpr std::size_t n = 128;
    std::vector<WeightedEdge> edges;
    edges.reserve(n * (n - 1) / 2);
    for (std::size_t first = 0; first < n; ++first)
        for (std::size_t second = first + 1; second < n; ++second)
            edges.push_back({
                    first, second,
                    second == (first ^ 1U)
                            ? 1000.0
                            : static_cast<double>((first + second) % 7)});
    const Result result =
            mixedradix::matching::maximum_weight_perfect_matching(n, edges);
    require(result.pairs.size() == n / 2, "128D matching cardinality");
    for (const auto& [first, second] : result.pairs)
        require(second == (first ^ 1U), "128D preferred pair was missed");
}

void test_validation() {
    bool rejected = false;
    try {
        (void)mixedradix::matching::maximum_weight_perfect_matching(
                3, {{0, 1, 1}, {0, 2, 1}, {1, 2, 1}});
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "odd graph was accepted");
}

a4orb::Curves variance_curves(std::initializer_list<double> proxies) {
    a4orb::Curves curves;
    for (double proxy : proxies)
        curves.coordinates.push_back({entry(proxy)});
    return curves;
}

void require_pairing(
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs,
        std::size_t dimensions, const char* message) {
    require(pairs.size() * 2 == dimensions, message);
    std::vector<bool> seen(dimensions, false);
    for (const auto& [first, second] : pairs) {
        require(first < second && second < dimensions, message);
        require(!seen[first] && !seen[second], message);
        seen[first] = seen[second] = true;
    }
    require(std::all_of(seen.begin(), seen.end(), [](bool value) {
                return value;
            }), message);
}

void test_eigenvalue_allocation() {
    const auto curves = variance_curves(
            {100, 90, 80, 70, 60, 50, 40, 30});
    const auto pairs =
            mixedradix::matching::eigenvalue_allocation_pairs(curves);
    require_pairing(pairs, 8, "EA invalid pairing");
    require(pairs == decltype(pairs)({{0, 7}, {1, 6}, {2, 5}, {3, 4}}),
            "EA primary-text ordering mismatch");

    const auto ties = mixedradix::matching::eigenvalue_allocation_pairs(
            variance_curves({1, 1, 1, 1}));
    require(ties == decltype(ties)({{0, 2}, {1, 3}}),
            "EA tie resolution mismatch");
}

void test_random_pairing() {
    constexpr std::uint64_t seeds[] = {
            2026080301ULL, 2026080302ULL, 2026080303ULL};
    std::vector<std::vector<std::pair<std::size_t, std::size_t>>> outputs;
    for (const auto seed : seeds) {
        const auto pairs = mixedradix::matching::random_pairs(128, seed);
        require_pairing(pairs, 128, "random invalid pairing");
        require(pairs == mixedradix::matching::random_pairs(128, seed),
                "random pairing is not reproducible");
        outputs.push_back(pairs);
    }
    require(outputs[0] != outputs[1] && outputs[0] != outputs[2] &&
                    outputs[1] != outputs[2],
            "random seeds did not separate pairings");
}

}  // namespace

int main() {
    try {
        test_against_exhaustive();
        test_cardinality_cross_pairing();
        test_128_coordinate_scale();
        test_validation();
        test_eigenvalue_allocation();
        test_random_pairing();
        std::cout << "pair_matching_test: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "pair_matching_test: FAIL: " << error.what() << '\n';
        return 1;
    }
}

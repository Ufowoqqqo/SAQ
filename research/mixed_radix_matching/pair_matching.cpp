#include "pair_matching.hpp"

#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/maximum_weighted_matching.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace mixedradix::matching {
namespace {

using Graph = boost::adjacency_list<
        boost::vecS, boost::vecS, boost::undirectedS,
        boost::no_property,
        boost::property<boost::edge_weight_t, std::int64_t>>;

// Boost's primal-dual implementation becomes impractically slow for a large
// integer range.  Four normalized decimal digits are used for this offline
// diagnostic; every result carries the resulting 64-edge objective bound.
constexpr double kWeightScale = 1e4;

void validate_complete_graph(
        std::size_t vertex_count,
        const std::vector<WeightedEdge>& edges) {
    if (vertex_count == 0 || (vertex_count & 1U) != 0)
        throw std::invalid_argument("matching requires positive even order");
    if (edges.size() != vertex_count * (vertex_count - 1) / 2)
        throw std::invalid_argument("matching graph is not complete");

    std::vector<bool> seen(vertex_count * vertex_count, false);
    for (const auto& edge : edges) {
        if (edge.first >= vertex_count || edge.second >= vertex_count ||
            edge.first >= edge.second || !std::isfinite(edge.weight))
            throw std::invalid_argument("invalid matching edge");
        const std::size_t key = edge.first * vertex_count + edge.second;
        if (seen[key]) throw std::invalid_argument("duplicate matching edge");
        seen[key] = true;
    }
}

}  // namespace

Result maximum_weight_perfect_matching(
        std::size_t vertex_count,
        const std::vector<WeightedEdge>& edges) {
    validate_complete_graph(vertex_count, edges);

    double minimum = std::numeric_limits<double>::infinity();
    double maximum = -std::numeric_limits<double>::infinity();
    for (const auto& edge : edges) {
        minimum = std::min(minimum, edge.weight);
        maximum = std::max(maximum, edge.weight);
    }
    const double range = maximum - minimum;

    Graph graph(vertex_count);
    for (const auto& edge : edges) {
        const std::int64_t scaled = range == 0
                ? 1
                : 1 + static_cast<std::int64_t>(std::llround(
                          (edge.weight - minimum) / range * kWeightScale));
        boost::add_edge(
                edge.first, edge.second,
                scaled, graph);
    }

    std::vector<Graph::vertex_descriptor> mate(vertex_count);
    auto mate_map = boost::make_iterator_property_map(
            mate.begin(), get(boost::vertex_index, graph));
    boost::maximum_weighted_matching(graph, mate_map);

    Result result;
    result.pairs.reserve(vertex_count / 2);
    std::vector<bool> emitted(vertex_count, false);
    for (std::size_t vertex = 0; vertex < vertex_count; ++vertex) {
        const auto other = mate[vertex];
        if (other == boost::graph_traits<Graph>::null_vertex() ||
            other >= vertex_count || mate[other] != vertex)
            throw std::runtime_error("matching result is not perfect");
        if (emitted[vertex]) continue;
        emitted[vertex] = emitted[other] = true;
        const std::size_t other_vertex = static_cast<std::size_t>(other);
        result.pairs.emplace_back(
                std::min(vertex, other_vertex),
                std::max(vertex, other_vertex));
    }
    std::sort(result.pairs.begin(), result.pairs.end());
    if (result.pairs.size() != vertex_count / 2)
        throw std::runtime_error("matching cardinality mismatch");
    // Each rounded edge differs by at most range/(2*scale).  Summing over
    // vertex_count/2 edges gives this conservative objective-error bound.
    result.objective_rounding_bound =
            vertex_count * range / (4 * kWeightScale);

    for (const auto& [first, second] : result.pairs) {
        const auto edge = std::find_if(
                edges.begin(), edges.end(),
                [=](const WeightedEdge& candidate) {
                    return candidate.first == first &&
                           candidate.second == second;
                });
        if (edge == edges.end())
            throw std::logic_error("matched edge missing");
        result.weight += edge->weight;
    }
    return result;
}

std::vector<WeightedEdge> allocation_edges(
        const a4orb::Curves& curves, int word_bits, bool dyadic) {
    if (curves.coordinates.empty() ||
        (curves.coordinates.size() & 1U) != 0)
        throw std::invalid_argument("curve count must be positive and even");
    if (word_bits != 4 && word_bits != 8)
        throw std::invalid_argument("word bits must be 4 or 8");
    for (const auto& curve : curves.coordinates)
        if (curve.empty()) throw std::invalid_argument("empty scalar curve");
    std::vector<WeightedEdge> edges;
    const std::size_t dimensions = curves.coordinates.size();
    edges.reserve(dimensions * (dimensions - 1) / 2);
    for (std::size_t first = 0; first < dimensions; ++first) {
        for (std::size_t second = first + 1; second < dimensions; ++second) {
            const auto allocation = a4or::allocate_pair(
                    curves.coordinates[first], curves.coordinates[second],
                    word_bits, dyadic);
            if (!std::isfinite(allocation.sse) || allocation.sse < 0)
                throw std::runtime_error("invalid allocation SSE");
            // Maximizing negative SSE is exactly minimizing total SSE because
            // every perfect matching contains the same number of edges.
            edges.push_back({first, second, -allocation.sse});
        }
    }
    return edges;
}

a4orb::Model allocate_paired_model(
        const a4orb::Curves& curves,
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs,
        int word_bits, bool dyadic) {
    if (curves.coordinates.empty() ||
        pairs.size() * 2 != curves.coordinates.size())
        throw std::invalid_argument("paired model dimensions");
    std::vector<bool> seen(curves.coordinates.size(), false);
    a4orb::Model model;
    model.arm = dyadic ? 'D' : 'A';
    model.word_bits = word_bits;
    model.blocks.reserve(pairs.size());
    for (const auto& [first_dimension, second_dimension] : pairs) {
        if (first_dimension >= curves.coordinates.size() ||
            second_dimension >= curves.coordinates.size() ||
            first_dimension == second_dimension || seen[first_dimension] ||
            seen[second_dimension])
            throw std::invalid_argument("paired model permutation");
        seen[first_dimension] = seen[second_dimension] = true;
        const auto allocation = a4or::allocate_pair(
                curves.coordinates[first_dimension],
                curves.coordinates[second_dimension], word_bits, dyadic);
        a4orb::Block block{
                2, allocation.used_states, allocation.k1, {},
                allocation.ambiguity};
        const auto& first = curves.coordinates[first_dimension]
                [allocation.k1 - 1].centers;
        const auto& second = curves.coordinates[second_dimension]
                [allocation.k2 - 1].centers;
        block.values.reserve(2 * block.centers);
        for (std::size_t z2 = 0; z2 < allocation.k2; ++z2)
            for (std::size_t z1 = 0; z1 < allocation.k1; ++z1) {
                block.values.push_back(first[z1]);
                block.values.push_back(second[z2]);
            }
        model.blocks.push_back(std::move(block));
    }
    return model;
}

std::vector<std::pair<std::size_t, std::size_t>>
eigenvalue_allocation_pairs(const a4orb::Curves& curves) {
    const std::size_t dimensions = curves.coordinates.size();
    if (dimensions == 0 || (dimensions & 1U) != 0)
        throw std::invalid_argument("EA dimensions must be positive and even");
    struct Coordinate {
        double variance_proxy = 0;
        std::size_t index = 0;
    };
    std::vector<Coordinate> order;
    order.reserve(dimensions);
    for (std::size_t index = 0; index < dimensions; ++index) {
        if (curves.coordinates[index].empty())
            throw std::invalid_argument("EA empty scalar curve");
        const double proxy = curves.coordinates[index][0].sse;
        if (!std::isfinite(proxy) || proxy < 0)
            throw std::invalid_argument("EA invalid variance proxy");
        order.push_back({proxy, index});
    }
    std::sort(order.begin(), order.end(), [](const auto& left,
                                             const auto& right) {
        return left.variance_proxy != right.variance_proxy
                ? left.variance_proxy > right.variance_proxy
                : left.index < right.index;
    });

    const std::size_t bucket_count = dimensions / 2;
    struct Bucket {
        long double product = 1;
        std::vector<std::size_t> coordinates;
    };
    std::vector<Bucket> buckets(bucket_count);
    // The primary text uses fixed-capacity buckets.  Fill every empty bucket
    // before assigning a second coordinate so the rule is invariant to a
    // global rescaling of eigenvalues.
    for (std::size_t bucket = 0; bucket < bucket_count; ++bucket) {
        const auto coordinate = order[bucket];
        buckets[bucket].coordinates.push_back(coordinate.index);
        buckets[bucket].product = coordinate.variance_proxy;
    }
    for (std::size_t position = bucket_count;
         position < dimensions; ++position) {
        const auto selected = std::min_element(
                buckets.begin(), buckets.end(),
                [](const Bucket& left, const Bucket& right) {
                    if (left.coordinates.size() == 2)
                        return false;
                    if (right.coordinates.size() == 2)
                        return true;
                    return left.product < right.product;
                });
        if (selected == buckets.end() || selected->coordinates.size() == 2)
            throw std::logic_error("EA has no non-full bucket");
        selected->coordinates.push_back(order[position].index);
        selected->product *= order[position].variance_proxy;
    }

    std::vector<std::pair<std::size_t, std::size_t>> pairs;
    pairs.reserve(bucket_count);
    for (const auto& bucket : buckets) {
        if (bucket.coordinates.size() != 2)
            throw std::logic_error("EA incomplete bucket");
        pairs.emplace_back(std::minmax(
                bucket.coordinates[0], bucket.coordinates[1]));
    }
    std::sort(pairs.begin(), pairs.end());
    return pairs;
}

std::vector<std::pair<std::size_t, std::size_t>> random_pairs(
        std::size_t dimensions, std::uint64_t seed) {
    if (dimensions == 0 || (dimensions & 1U) != 0)
        throw std::invalid_argument(
                "random pairing dimensions must be positive and even");
    std::vector<std::size_t> order(dimensions);
    std::iota(order.begin(), order.end(), 0);
    std::uint64_t state = seed;
    for (std::size_t remaining = dimensions; remaining > 1; --remaining) {
        state += 0x9e3779b97f4a7c15ULL;
        const std::size_t selected = static_cast<std::size_t>(
                a4or::splitmix64(state) % remaining);
        std::swap(order[remaining - 1], order[selected]);
    }
    std::vector<std::pair<std::size_t, std::size_t>> pairs;
    pairs.reserve(dimensions / 2);
    for (std::size_t index = 0; index < dimensions; index += 2)
        pairs.emplace_back(std::minmax(order[index], order[index + 1]));
    std::sort(pairs.begin(), pairs.end());
    return pairs;
}

}  // namespace mixedradix::matching

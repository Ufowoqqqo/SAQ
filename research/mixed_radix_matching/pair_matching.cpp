#include "pair_matching.hpp"

#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/maximum_weighted_matching.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
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

}  // namespace mixedradix::matching

#pragma once

#include "../a4_or_b/models.hpp"

#include <cstddef>
#include <utility>
#include <vector>

namespace mixedradix::matching {

struct WeightedEdge {
    std::size_t first = 0;
    std::size_t second = 0;
    double weight = 0;
};

struct Result {
    std::vector<std::pair<std::size_t, std::size_t>> pairs;
    double weight = 0;
    double objective_rounding_bound = 0;
};

Result maximum_weight_perfect_matching(
        std::size_t vertex_count,
        const std::vector<WeightedEdge>& edges);

std::vector<WeightedEdge> allocation_edges(
        const a4orb::Curves& curves, int word_bits, bool dyadic);

a4orb::Model allocate_paired_model(
        const a4orb::Curves& curves,
        const std::vector<std::pair<std::size_t, std::size_t>>& pairs,
        int word_bits, bool dyadic);

}  // namespace mixedradix::matching

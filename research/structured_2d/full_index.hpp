#pragma once

#include "model.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <vector>

namespace structured2d {

// Query-free prototype index for establishing full-index score semantics.
// It intentionally stores no raw database vectors and is not performance
// evidence; a later native runner may reuse the validated representation.
struct FullIndex {
    std::size_t dimensions = 0;
    SharedAffineModel model;
    std::vector<float> centroids;
    std::vector<std::uint64_t> list_offsets;
    std::vector<std::uint32_t> ids;
    std::vector<std::uint8_t> payload;
};

struct IndexByteAccounting {
    std::uint64_t header_bytes = 0;
    std::uint64_t model_bytes = 0;
    std::uint64_t centroid_bytes = 0;
    std::uint64_t list_offset_bytes = 0;
    std::uint64_t database_id_bytes = 0;
    std::uint64_t packed_code_bytes = 0;
    std::uint64_t complete_serialized_bytes = 0;
};

struct SearchHit {
    std::uint32_t id = 0;
    double distance = 0;

    friend bool operator==(const SearchHit&, const SearchHit&) = default;
};

struct SearchResult {
    std::vector<SearchHit> hits;
    std::uint64_t candidates_scored = 0;
    std::vector<std::uint32_t> visited_lists;

    friend bool operator==(const SearchResult&, const SearchResult&) = default;
};

FullIndex build_full_index(
        std::size_t dimensions, std::span<const float> centroids,
        std::span<const std::uint32_t> assignments,
        std::span<const std::uint32_t> ids,
        std::span<const float> base,
        const SharedAffineModel& model);

bool valid_full_index(const FullIndex& index);

IndexByteAccounting byte_accounting(const FullIndex& index);

SearchResult search_preassigned(
        const FullIndex& index, std::span<const float> query,
        std::span<const std::uint32_t> preassigned_lists,
        std::size_t top_k);

// Binary64 reconstruction reference for one stored candidate. The candidate
// position is local to the selected list.
double direct_reconstruction_score(
        const FullIndex& index, std::span<const float> query,
        std::uint32_t list, std::size_t position_in_list);

void save_full_index(
        const FullIndex& index, const std::filesystem::path& path);
FullIndex load_full_index(const std::filesystem::path& path);

}  // namespace structured2d

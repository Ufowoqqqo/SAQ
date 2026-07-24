#pragma once

#include <faiss/IndexIVFPQ.h>
#include <faiss/VectorTransform.h>

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace structured2d::admission {

struct TopKResult {
    std::vector<float> distances;
    std::vector<faiss::idx_t> ids;
    std::uint64_t candidates = 0;
};

// Canonicalize Faiss's (-1, FLT_MAX) missing-result slots to (-1, +inf)
// and pad a short custom result to exactly top_k entries.
void normalize_topk(TopKResult& result, std::size_t top_k);

// Native IVFPQ scanner with one shared heap. For a head-only GIST arm,
// full_dimensions and full_centroids include the tail and tail_start=128.
// For residual OPQ, transform is non-null and index.by_residual must be false.
TopKResult search_ivfpq_lists(
        const faiss::IndexIVFPQ& index,
        const faiss::LinearTransform* transform,
        std::span<const float> full_query,
        std::span<const float> full_centroids,
        std::size_t full_dimensions,
        std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k);

// Cheapest correct separable D128 table path. Each radix is k1 and the
// packed label is z1 + z2*k1.
TopKResult search_dyadic_lists(
        const faiss::IndexIVFPQ& index,
        std::span<const std::uint16_t> radices,
        std::span<const float> full_query,
        std::span<const float> full_centroids,
        std::size_t full_dimensions,
        std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k);

std::uint64_t hash_topk(
        std::span<const TopKResult> results);

}  // namespace structured2d::admission

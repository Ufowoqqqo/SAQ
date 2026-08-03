#include "synthetic_timing.hpp"

#include <faiss/impl/ResultHandler.h>
#include <faiss/invlists/InvertedLists.h>
#include <faiss/utils/Heap.h>

#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>

namespace structured2d::admission {
namespace {

class TailHeapHandler final : public faiss::ResultHandler {
  public:
    TailHeapHandler(
            std::size_t k, float* distances,
            faiss::idx_t* ids)
            : k_(k), distances_(distances), ids_(ids) {
        refresh_threshold();
    }

    void begin_list(float tail) {
        if (!std::isfinite(tail) || tail < 0)
            throw std::invalid_argument("tail constant");
        tail_ = tail;
        refresh_threshold();
    }

    bool add_result(float distance, faiss::idx_t id) final {
        const float complete = distance + tail_;
        if (faiss::CMax<float, faiss::idx_t>::cmp2(
                    distances_[0], complete, ids_[0], id)) {
            faiss::maxheap_replace_top(
                    k_, distances_, ids_, complete, id);
            refresh_threshold();
            return true;
        }
        return false;
    }

  private:
    void refresh_threshold() {
        const float raw = distances_[0] - tail_;
        threshold = std::isfinite(raw)
                ? std::nextafter(
                          raw,
                          std::numeric_limits<float>::infinity())
                : raw;
    }

    std::size_t k_;
    float* distances_;
    faiss::idx_t* ids_;
    float tail_ = 0;
};

std::uint64_t candidate_count(
        const faiss::IndexIVF& index,
        std::span<const faiss::idx_t> lists) {
    std::uint64_t result = 0;
    for (const faiss::idx_t list : lists) {
        if (list < 0 ||
            list >= static_cast<faiss::idx_t>(index.nlist))
            throw std::out_of_range("timing list");
        result += index.invlists->list_size(list);
    }
    return result;
}

TopKResult initialize_result(
        std::uint64_t candidates, std::size_t top_k) {
    TopKResult result;
    result.candidates = candidates;
    const std::size_t count =
            std::min<std::uint64_t>(candidates, top_k);
    result.distances.resize(count);
    result.ids.resize(count);
    if (count)
        faiss::maxheap_heapify(
                count, result.distances.data(), result.ids.data());
    return result;
}

float tail_distance(
        std::span<const float> query,
        std::span<const float> centroids,
        std::size_t dimensions, std::size_t tail_start,
        faiss::idx_t list) {
    if (tail_start >= dimensions) return 0;
    const float* centroid =
            centroids.data() +
            static_cast<std::size_t>(list) * dimensions;
    double result = 0;
    for (std::size_t dimension = tail_start;
         dimension < dimensions; ++dimension) {
        const double delta =
                static_cast<double>(query[dimension]) -
                centroid[dimension];
        result += delta * delta;
    }
    return static_cast<float>(result);
}

void validate_common(
        const faiss::IndexIVFPQ& index,
        std::span<const float> query,
        std::span<const float> centroids,
        std::size_t dimensions, std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k) {
    if (top_k == 0 || dimensions < static_cast<std::size_t>(index.d) ||
        query.size() != dimensions ||
        centroids.size() != index.nlist * dimensions ||
        tail_start < static_cast<std::size_t>(index.d) ||
        tail_start > dimensions || lists.empty() ||
        !std::all_of(
                query.begin(), query.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("timing search shape");
}

std::uint32_t decode_label(
        const std::uint8_t* code, int bits,
        std::size_t group) {
    if (bits == 8) return code[group];
    if (bits == 4)
        return (group & 1U) == 0
                ? code[group / 2] & 0x0fU
                : code[group / 2] >> 4;
    throw std::invalid_argument("D packed bits");
}

void distance_four_b4(
        std::size_t groups, const float* table,
        const std::uint8_t* code0,
        const std::uint8_t* code1, const std::uint8_t* code2,
        const std::uint8_t* code3, float& d0, float& d1,
        float& d2, float& d3) {
    d0 = d1 = d2 = d3 = 0;
    for (std::size_t byte = 0; byte < groups / 2; ++byte) {
        const float* low = table + 32 * byte;
        const float* high = low + 16;
        d0 += low[code0[byte] & 0x0fU] + high[code0[byte] >> 4];
        d1 += low[code1[byte] & 0x0fU] + high[code1[byte] >> 4];
        d2 += low[code2[byte] & 0x0fU] + high[code2[byte] >> 4];
        d3 += low[code3[byte] & 0x0fU] + high[code3[byte] >> 4];
    }
    if ((groups & 1U) != 0) {
        const std::size_t byte = groups / 2;
        const float* last = table + 16 * (groups - 1);
        d0 += last[code0[byte] & 0x0fU];
        d1 += last[code1[byte] & 0x0fU];
        d2 += last[code2[byte] & 0x0fU];
        d3 += last[code3[byte] & 0x0fU];
    }
}

void distance_four_b8(
        std::size_t groups, const float* table,
        const std::uint8_t* code0,
        const std::uint8_t* code1, const std::uint8_t* code2,
        const std::uint8_t* code3, float& d0, float& d1,
        float& d2, float& d3) {
    d0 = d1 = d2 = d3 = 0;
    for (std::size_t group = 0; group < groups; ++group) {
        const float* current = table + 256 * group;
        d0 += current[code0[group]];
        d1 += current[code1[group]];
        d2 += current[code2[group]];
        d3 += current[code3[group]];
    }
}

}  // namespace

void normalize_topk(TopKResult& result, std::size_t top_k) {
    if (top_k == 0 ||
        result.ids.size() != result.distances.size() ||
        result.ids.size() > top_k)
        throw std::invalid_argument("top-k normalization shape");
    for (std::size_t rank = 0; rank < result.ids.size(); ++rank) {
        if (result.ids[rank] == -1) {
            if (result.distances[rank] !=
                        std::numeric_limits<float>::max() &&
                !(std::isinf(result.distances[rank]) &&
                  result.distances[rank] > 0))
                throw std::runtime_error(
                        "invalid missing top-k distance");
            result.distances[rank] =
                    std::numeric_limits<float>::infinity();
        } else if (result.ids[rank] < 0 ||
                   !std::isfinite(result.distances[rank])) {
            throw std::runtime_error("invalid populated top-k slot");
        }
    }
    result.ids.resize(top_k, -1);
    result.distances.resize(
            top_k, std::numeric_limits<float>::infinity());
}

TopKResult search_ivfpq_lists(
        const faiss::IndexIVFPQ& index,
        const faiss::LinearTransform* transform,
        std::span<const float> full_query,
        std::span<const float> full_centroids,
        std::size_t full_dimensions,
        std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k) {
    validate_common(
            index, full_query, full_centroids, full_dimensions,
            tail_start, lists, top_k);
    if ((transform == nullptr && !index.by_residual) ||
        (transform != nullptr &&
         (index.by_residual || !transform->is_trained ||
          transform->d_in != index.d ||
          transform->d_out != index.d)))
        throw std::invalid_argument("timing OPQ semantics");

    TopKResult result =
            initialize_result(candidate_count(index, lists), top_k);
    if (result.ids.empty()) return result;
    TailHeapHandler handler(
            result.ids.size(), result.distances.data(),
            result.ids.data());
    std::unique_ptr<faiss::InvertedListScanner> scanner(
            index.get_InvertedListScanner(false, nullptr, nullptr));
    std::vector<float> residual(index.d), rotated(index.d);

    if (transform == nullptr)
        scanner->set_query(full_query.data());
    for (const faiss::idx_t list : lists) {
        // Faiss enables residual-IVFPQ precomputed tables when an index is
        // loaded. In that mode set_list() needs ||q_head-centroid_head||^2;
        // passing zero makes increasingly distant lists spuriously cheap.
        // Compute only the encoded head here because tail_distance() is added
        // separately for head-only GIST arms.
        const float* centroid =
                full_centroids.data() +
                static_cast<std::size_t>(list) *
                        full_dimensions;
        double head_coarse_distance = 0;
        for (std::size_t dimension = 0;
             dimension < static_cast<std::size_t>(index.d);
             ++dimension) {
            const double delta =
                    static_cast<double>(
                            full_query[dimension]) -
                    centroid[dimension];
            head_coarse_distance += delta * delta;
        }
        const float tail = tail_distance(
                full_query, full_centroids, full_dimensions,
                tail_start, list);
        if (transform != nullptr) {
            index.quantizer->compute_residual(
                    full_query.data(), residual.data(), list);
            transform->apply_noalloc(
                    1, residual.data(), rotated.data());
            scanner->set_query(rotated.data());
        }
        scanner->set_list(
                list,
                static_cast<float>(head_coarse_distance));
        handler.begin_list(tail);
        faiss::InvertedLists::ScopedCodes codes(
                index.invlists, list);
        faiss::InvertedLists::ScopedIds ids(
                index.invlists, list);
        scanner->scan_codes(
                index.invlists->list_size(list),
                codes.get(), ids.get(), handler);
    }
    faiss::maxheap_reorder(
            result.ids.size(), result.distances.data(),
            result.ids.data());
    return result;
}

TopKResult search_dyadic_lists(
        const faiss::IndexIVFPQ& index,
        std::span<const std::uint16_t> radices,
        std::span<const float> full_query,
        std::span<const float> full_centroids,
        std::size_t full_dimensions,
        std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k) {
    validate_common(
            index, full_query, full_centroids, full_dimensions,
            tail_start, lists, top_k);
    if (!index.by_residual ||
        index.pq.dsub != 2 ||
        radices.size() != index.pq.M ||
        (index.pq.nbits != 4 && index.pq.nbits != 8))
        throw std::invalid_argument("D timing semantics");

    TopKResult result =
            initialize_result(candidate_count(index, lists), top_k);
    if (result.ids.empty()) return result;
    const std::size_t groups = index.pq.M;
    const std::size_t centers = index.pq.ksub;
    std::vector<float> residual(index.d);
    std::vector<float> first(groups * centers);
    std::vector<float> second(groups * centers);

    for (const faiss::idx_t list : lists) {
        index.quantizer->compute_residual(
                full_query.data(), residual.data(), list);
        for (std::size_t group = 0; group < groups; ++group) {
            const std::size_t k1 = radices[group];
            if (k1 == 0 || centers % k1 != 0)
                throw std::runtime_error("D radix shape");
            const std::size_t k2 = centers / k1;
            const float* codebook =
                    index.pq.get_centroids(group, 0);
            for (std::size_t z1 = 0; z1 < k1; ++z1) {
                const float delta =
                        residual[2 * group] -
                        codebook[2 * z1];
                first[group * centers + z1] = delta * delta;
            }
            for (std::size_t z2 = 0; z2 < k2; ++z2) {
                const float delta =
                        residual[2 * group + 1] -
                        codebook[2 * z2 * k1 + 1];
                second[group * centers + z2] = delta * delta;
            }
        }
        const float tail = tail_distance(
                full_query, full_centroids, full_dimensions,
                tail_start, list);
        faiss::InvertedLists::ScopedCodes codes(
                index.invlists, list);
        faiss::InvertedLists::ScopedIds ids(
                index.invlists, list);
        const std::size_t count =
                index.invlists->list_size(list);
        for (std::size_t candidate = 0;
             candidate < count; ++candidate) {
            const std::uint8_t* code =
                    codes.get() + candidate * index.code_size;
            float distance = tail;
            for (std::size_t group = 0;
                 group < groups; ++group) {
                const std::uint32_t label =
                        decode_label(
                                code, index.pq.nbits, group);
                const std::size_t k1 = radices[group];
                distance +=
                        first[group * centers + label % k1] +
                        second[group * centers + label / k1];
            }
            if (faiss::CMax<float, faiss::idx_t>::cmp2(
                        result.distances[0], distance,
                        result.ids[0], ids.get()[candidate]))
                faiss::maxheap_replace_top(
                        result.ids.size(),
                        result.distances.data(),
                        result.ids.data(), distance,
                        ids.get()[candidate]);
        }
    }
    faiss::maxheap_reorder(
            result.ids.size(), result.distances.data(),
            result.ids.data());
    return result;
}

TopKResult search_mixed_radix_lists(
        const faiss::IndexIVFPQ& index,
        std::span<const std::uint16_t> radices,
        std::span<const std::uint16_t> used_states,
        std::span<const float> full_query,
        std::span<const float> full_centroids,
        std::size_t full_dimensions,
        std::size_t tail_start,
        std::span<const faiss::idx_t> lists,
        std::size_t top_k,
        std::span<const std::uint16_t> coordinates) {
    validate_common(
            index, full_query, full_centroids, full_dimensions,
            tail_start, lists, top_k);
    if (!index.by_residual || index.pq.dsub != 2 ||
        radices.size() != index.pq.M ||
        used_states.size() != index.pq.M ||
        (index.pq.nbits != 4 && index.pq.nbits != 8))
        throw std::invalid_argument("mixed-radix timing semantics");

    const std::size_t groups = index.pq.M;
    const std::size_t capacity = index.pq.ksub;
    if (!coordinates.empty()) {
        if (coordinates.size() != 2 * groups)
            throw std::invalid_argument("mixed-radix coordinate shape");
        std::vector<bool> seen(index.d, false);
        for (const std::uint16_t coordinate : coordinates) {
            if (coordinate >= static_cast<std::size_t>(index.d) ||
                seen[coordinate])
                throw std::invalid_argument(
                        "mixed-radix coordinate permutation");
            seen[coordinate] = true;
        }
    }
    for (std::size_t group = 0; group < groups; ++group)
        if (radices[group] == 0 ||
            used_states[group] == 0 ||
            used_states[group] > capacity ||
            used_states[group] % radices[group] != 0)
            throw std::invalid_argument("mixed-radix timing shape");

    TopKResult result =
            initialize_result(candidate_count(index, lists), top_k);
    if (result.ids.empty()) return result;
    std::vector<float> residual(index.d);
    std::vector<float> tables(groups * capacity);

    for (const faiss::idx_t list : lists) {
        index.quantizer->compute_residual(
                full_query.data(), residual.data(), list);
        for (std::size_t group = 0; group < groups; ++group) {
            const float* codebook =
                    index.pq.get_centroids(group, 0);
            float* table = tables.data() + group * capacity;
            const std::size_t first_coordinate = coordinates.empty()
                    ? 2 * group : coordinates[2 * group];
            const std::size_t second_coordinate = coordinates.empty()
                    ? 2 * group + 1 : coordinates[2 * group + 1];
            for (std::size_t label = 0;
                 label < used_states[group]; ++label) {
                const double first =
                        static_cast<double>(
                                residual[first_coordinate]) -
                        codebook[2 * label];
                const double second =
                        static_cast<double>(
                                residual[second_coordinate]) -
                        codebook[2 * label + 1];
                table[label] = static_cast<float>(
                        first * first + second * second);
            }
            for (std::size_t label = used_states[group];
                 label < capacity; ++label)
                table[label] =
                        std::numeric_limits<float>::infinity();
        }
        const float tail = tail_distance(
                full_query, full_centroids, full_dimensions,
                tail_start, list);
        faiss::InvertedLists::ScopedCodes codes(
                index.invlists, list);
        faiss::InvertedLists::ScopedIds ids(
                index.invlists, list);
        const std::size_t count =
                index.invlists->list_size(list);
        const auto consider = [&](std::size_t candidate, float raw) {
            const float distance = tail + raw;
            if (!std::isfinite(distance))
                throw std::runtime_error(
                        "stored invalid mixed-radix label");
            if (faiss::CMax<float, faiss::idx_t>::cmp2(
                        result.distances[0], distance,
                        result.ids[0], ids.get()[candidate]))
                faiss::maxheap_replace_top(
                        result.ids.size(),
                        result.distances.data(),
                        result.ids.data(), distance,
                        ids.get()[candidate]);
        };
        std::size_t candidate = 0;
        if (index.pq.nbits == 8) {
            for (; candidate + 4 <= count; candidate += 4) {
                float d0, d1, d2, d3;
                const std::uint8_t* code =
                        codes.get() + candidate * index.code_size;
                distance_four_b8(
                        groups, tables.data(),
                        code, code + index.code_size,
                        code + 2 * index.code_size,
                        code + 3 * index.code_size,
                        d0, d1, d2, d3);
                consider(candidate, d0);
                consider(candidate + 1, d1);
                consider(candidate + 2, d2);
                consider(candidate + 3, d3);
            }
        } else {
            for (; candidate + 4 <= count; candidate += 4) {
                float d0, d1, d2, d3;
                const std::uint8_t* code =
                        codes.get() + candidate * index.code_size;
                distance_four_b4(
                        groups, tables.data(),
                        code, code + index.code_size,
                        code + 2 * index.code_size,
                        code + 3 * index.code_size,
                        d0, d1, d2, d3);
                consider(candidate, d0);
                consider(candidate + 1, d1);
                consider(candidate + 2, d2);
                consider(candidate + 3, d3);
            }
        }
        for (; candidate < count; ++candidate) {
            float d0, d1, d2, d3;
            const std::uint8_t* code =
                    codes.get() + candidate * index.code_size;
            if (index.pq.nbits == 8)
                distance_four_b8(
                        groups, tables.data(),
                        code, code, code, code,
                        d0, d1, d2, d3);
            else
                distance_four_b4(
                        groups, tables.data(),
                        code, code, code, code,
                        d0, d1, d2, d3);
            consider(candidate, d0);
        }
    }
    faiss::maxheap_reorder(
            result.ids.size(), result.distances.data(),
            result.ids.data());
    return result;
}

std::uint64_t hash_topk(
        std::span<const TopKResult> results) {
    std::uint64_t hash = 1469598103934665603ULL;
    const auto append = [&hash](std::uint64_t value) {
        for (std::size_t byte = 0; byte < 8; ++byte) {
            hash ^= static_cast<std::uint8_t>(
                    value >> (8 * byte));
            hash *= 1099511628211ULL;
        }
    };
    for (std::size_t query = 0; query < results.size(); ++query) {
        const auto& result = results[query];
        if (result.ids.size() != result.distances.size())
            throw std::invalid_argument("top-k hash shape");
        append(result.ids.size());
        for (std::size_t index = 0;
             index < result.ids.size(); ++index) {
            const bool missing =
                    result.ids[index] == -1 &&
                    std::isinf(result.distances[index]) &&
                    result.distances[index] > 0;
            if ((!std::isfinite(result.distances[index]) ||
                 result.ids[index] < 0) &&
                !missing)
                throw std::runtime_error(
                        "invalid top-k output at query=" +
                        std::to_string(query) +
                        " rank=" + std::to_string(index) +
                        " id=" + std::to_string(result.ids[index]) +
                        " distance=" +
                        std::to_string(result.distances[index]));
            append(static_cast<std::uint64_t>(result.ids[index]));
            append(std::bit_cast<std::uint32_t>(
                    result.distances[index]));
        }
    }
    return hash;
}

}  // namespace structured2d::admission

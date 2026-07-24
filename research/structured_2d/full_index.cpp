#include "full_index.hpp"

#include "compact.hpp"
#include "microbench.hpp"

#include <faiss/utils/Heap.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <fstream>
#include <initializer_list>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <unordered_set>

namespace structured2d {
namespace {

constexpr std::size_t kHeadDimensions = a4orb::kPanelDimensions;
constexpr std::size_t kGroups = a4orb::kGroups;
constexpr std::array<char, 8> kMagic{
        'S', '2', 'D', 'I', 'V', 'F', '0', '1'};
constexpr std::uint32_t kVersion = 2;
constexpr std::uint64_t kHeaderBytes =
        kMagic.size() + 2 * sizeof(std::uint32_t) +
        7 * sizeof(std::uint64_t);

void require_model(const SharedAffineModel& model) {
    if (!supported_word_bits(model.word_bits) ||
        model.groups.size() != kGroups ||
        model.shape.size() !=
                2 * (std::size_t{1} << model.word_bits) ||
        !finite(model))
        throw std::invalid_argument("full index model");
}

std::size_t list_count(const FullIndex& index) {
    return index.list_offsets.empty()
            ? 0
            : index.list_offsets.size() - 1;
}

std::uint64_t checked_product(
        std::uint64_t left, std::uint64_t right,
        const char* message) {
    if (right != 0 &&
        left > std::numeric_limits<std::uint64_t>::max() / right)
        throw std::overflow_error(message);
    return left * right;
}

std::uint64_t checked_sum(
        std::initializer_list<std::uint64_t> values,
        const char* message) {
    std::uint64_t result = 0;
    for (const std::uint64_t value : values) {
        if (result > std::numeric_limits<std::uint64_t>::max() - value)
            throw std::overflow_error(message);
        result += value;
    }
    return result;
}

template <typename UInt>
void write_little(std::ostream& output, UInt value) {
    static_assert(std::is_unsigned_v<UInt>);
    std::array<char, sizeof(UInt)> bytes{};
    for (std::size_t index = 0; index < bytes.size(); ++index)
        bytes[index] = static_cast<char>(
                (value >> (8 * index)) & UInt{0xff});
    output.write(bytes.data(), bytes.size());
    if (!output) throw std::runtime_error("write full index");
}

void write_float(std::ostream& output, float value) {
    write_little(output, std::bit_cast<std::uint32_t>(value));
}

template <typename UInt>
UInt read_little(std::istream& input) {
    static_assert(std::is_unsigned_v<UInt>);
    std::array<unsigned char, sizeof(UInt)> bytes{};
    input.read(
            reinterpret_cast<char*>(bytes.data()), bytes.size());
    if (!input) throw std::runtime_error("truncated full index");
    UInt value = 0;
    for (std::size_t index = 0; index < bytes.size(); ++index)
        value |= static_cast<UInt>(bytes[index]) << (8 * index);
    return value;
}

float read_float(std::istream& input) {
    return std::bit_cast<float>(read_little<std::uint32_t>(input));
}

std::size_t checked_size(std::uint64_t value, const char* message) {
    if (value > std::numeric_limits<std::size_t>::max())
        throw std::overflow_error(message);
    return static_cast<std::size_t>(value);
}

std::vector<std::uint16_t> encode_residual(
        std::span<const float> vector,
        std::span<const float> centroid,
        const SharedAffineModel& model) {
    std::vector<std::uint16_t> labels(kGroups);
    std::array<float, 2> residual{};
    for (std::size_t group = 0; group < kGroups; ++group) {
        residual[0] =
                vector[2 * group] - centroid[2 * group];
        residual[1] =
                vector[2 * group + 1] - centroid[2 * group + 1];
        labels[group] = encode_compact_point(
                residual.data(), model, group);
    }
    return labels;
}

void validate_preassigned(
        const FullIndex& index,
        std::span<const std::uint32_t> preassigned_lists) {
    std::unordered_set<std::uint32_t> seen;
    seen.reserve(preassigned_lists.size());
    for (const std::uint32_t list : preassigned_lists) {
        if (list >= list_count(index))
            throw std::out_of_range("preassigned list");
        if (!seen.insert(list).second)
            throw std::invalid_argument("duplicate preassigned list");
    }
}

}  // namespace

FullIndex build_full_index(
        std::size_t dimensions, std::span<const float> centroids,
        std::span<const std::uint32_t> assignments,
        std::span<const std::uint64_t> ids,
        std::span<const float> base,
        const SharedAffineModel& model) {
    require_model(model);
    if (dimensions < kHeadDimensions || dimensions == 0 ||
        centroids.empty() || centroids.size() % dimensions != 0 ||
        assignments.size() != ids.size() ||
        base.size() != checked_product(
                ids.size(), dimensions, "base shape") ||
        ids.empty() ||
        !std::all_of(
                centroids.begin(), centroids.end(),
                [](float value) { return std::isfinite(value); }) ||
        !std::all_of(
                base.begin(), base.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("full index input shape");
    const std::size_t cells = centroids.size() / dimensions;

    std::unordered_set<std::uint64_t> unique_ids;
    unique_ids.reserve(ids.size());
    std::vector<std::uint64_t> counts(cells);
    for (std::size_t row = 0; row < ids.size(); ++row) {
        if (assignments[row] >= cells)
            throw std::out_of_range("base assignment");
        if (!unique_ids.insert(ids[row]).second)
            throw std::invalid_argument("duplicate database id");
        ++counts[assignments[row]];
    }

    FullIndex result;
    result.dimensions = dimensions;
    result.model = model;
    // Expanded centers are a transient correctness reference, not persistent
    // serialized state.
    result.model.expanded = {};
    result.centroids.assign(centroids.begin(), centroids.end());
    result.list_offsets.resize(cells + 1);
    for (std::size_t cell = 0; cell < cells; ++cell)
        result.list_offsets[cell + 1] =
                result.list_offsets[cell] + counts[cell];
    result.ids.resize(ids.size());

    const std::size_t stride =
            payload_bytes_per_candidate(model.word_bits);
    result.payload.resize(
            checked_product(ids.size(), stride, "payload shape"));
    std::vector<std::uint64_t> next = result.list_offsets;
    for (std::size_t row = 0; row < ids.size(); ++row) {
        const std::uint32_t cell = assignments[row];
        const std::size_t target =
                static_cast<std::size_t>(next[cell]++);
        result.ids[target] = ids[row];
        const auto labels = encode_residual(
                base.subspan(row * dimensions, dimensions),
                centroids.subspan(
                        static_cast<std::size_t>(cell) * dimensions,
                        dimensions),
                model);
        const auto packed = pack_labels(labels, model.word_bits);
        std::copy(
                packed.begin(), packed.end(),
                result.payload.begin() + target * stride);
    }
    if (!valid_full_index(result))
        throw std::runtime_error("built invalid full index");
    return result;
}

bool valid_full_index(const FullIndex& index) {
    try {
        require_model(index.model);
        if (index.dimensions < kHeadDimensions ||
            index.centroids.empty() || index.ids.empty() ||
            index.centroids.size() % index.dimensions != 0 ||
            index.list_offsets.size() !=
                    index.centroids.size() / index.dimensions + 1 ||
            index.list_offsets.front() != 0 ||
            index.list_offsets.back() != index.ids.size())
            return false;
        if (!std::is_sorted(
                    index.list_offsets.begin(),
                    index.list_offsets.end()))
            return false;
        const std::size_t stride =
                payload_bytes_per_candidate(index.model.word_bits);
        if (index.payload.size() != index.ids.size() * stride)
            return false;
        if (!std::all_of(
                    index.centroids.begin(), index.centroids.end(),
                    [](float value) { return std::isfinite(value); }))
            return false;
        std::unordered_set<std::uint64_t> ids;
        ids.reserve(index.ids.size());
        return std::all_of(
                index.ids.begin(), index.ids.end(),
                [&ids](std::uint64_t id) {
                    return ids.insert(id).second;
                });
    } catch (const std::exception&) {
        return false;
    }
}

IndexByteAccounting byte_accounting(const FullIndex& index) {
    if (!valid_full_index(index))
        throw std::invalid_argument("byte accounting index");
    IndexByteAccounting result;
    result.header_bytes = kHeaderBytes;
    result.model_bytes = checked_sum(
            {checked_product(
                     index.model.shape.size(), sizeof(float),
                     "model shape bytes"),
             checked_product(
                     index.model.groups.size(), 6 * sizeof(float),
                     "model group bytes")},
            "model bytes");
    result.centroid_bytes = checked_product(
            index.centroids.size(), sizeof(float), "centroid bytes");
    result.list_offset_bytes = checked_product(
            index.list_offsets.size(), sizeof(std::uint64_t),
            "offset bytes");
    result.database_id_bytes = checked_product(
            index.ids.size(), sizeof(std::uint64_t), "id bytes");
    result.packed_code_bytes = index.payload.size();
    result.complete_serialized_bytes = checked_sum(
            {result.header_bytes, result.model_bytes,
             result.centroid_bytes, result.list_offset_bytes,
             result.database_id_bytes, result.packed_code_bytes},
            "serialized bytes");
    return result;
}

SearchResult search_preassigned_impl(
        const FullIndex& index, std::span<const float> query,
        std::span<const std::uint32_t> preassigned_lists,
        std::size_t top_k, bool validate_index) {
    if ((validate_index && !valid_full_index(index)) ||
        query.size() != index.dimensions || top_k == 0)
        throw std::invalid_argument("preassigned search shape");
    if (!std::all_of(
                query.begin(), query.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("non-finite query");
    validate_preassigned(index, preassigned_lists);

    const std::size_t centers =
            std::size_t{1} << index.model.word_bits;
    const std::size_t stride =
            payload_bytes_per_candidate(index.model.word_bits);
    std::vector<float> tables(kGroups * centers);
    std::uint64_t candidates_scored = 0;
    for (const std::uint32_t list : preassigned_lists)
        candidates_scored +=
                index.list_offsets[list + 1] -
                index.list_offsets[list];
    const std::size_t result_count =
            std::min<std::uint64_t>(top_k, candidates_scored);
    std::vector<float> heap_distances(result_count);
    std::vector<std::int64_t> heap_ids(result_count);
    if (result_count != 0)
        faiss::maxheap_heapify(
                result_count, heap_distances.data(),
                heap_ids.data());
    for (const std::uint32_t list : preassigned_lists) {
        const float* centroid =
                index.centroids.data() +
                static_cast<std::size_t>(list) * index.dimensions;
        for (std::size_t group = 0; group < kGroups; ++group) {
            std::array<float, 2> residual{
                    query[2 * group] - centroid[2 * group],
                    query[2 * group + 1] -
                            centroid[2 * group + 1]};
            build_compact_table(
                    residual.data(), index.model, group,
                    std::span<float>(
                            tables.data() + group * centers,
                            centers));
        }

        // Unencoded coordinates reconstruct to the selected coarse centroid,
        // so this exact term is constant within one list but not across lists.
        double tail = 0;
        for (std::size_t dimension = kHeadDimensions;
             dimension < index.dimensions; ++dimension) {
            const double delta =
                    static_cast<double>(query[dimension]) -
                    centroid[dimension];
            tail += delta * delta;
        }
        const std::size_t first =
                static_cast<std::size_t>(index.list_offsets[list]);
        const std::size_t last =
                static_cast<std::size_t>(index.list_offsets[list + 1]);
        for (std::size_t candidate = first;
             candidate < last; ++candidate) {
            const auto code = std::span<const std::uint8_t>(
                    index.payload.data() + candidate * stride, stride);
            double distance = tail;
            for (std::size_t group = 0; group < kGroups; ++group) {
                const std::size_t label = index.model.word_bits == 8
                        ? code[group]
                        : ((group & 1U) == 0
                                   ? code[group / 2] & 0x0fU
                                   : code[group / 2] >> 4);
                distance += tables[group * centers + label];
            }
            const float float_distance =
                    static_cast<float>(distance);
            const std::int64_t id =
                    static_cast<std::int64_t>(index.ids[candidate]);
            if (result_count != 0 &&
                faiss::CMax<float, std::int64_t>::cmp2(
                        heap_distances[0], float_distance,
                        heap_ids[0], id))
                faiss::maxheap_replace_top(
                        result_count, heap_distances.data(),
                        heap_ids.data(), float_distance, id);
        }
    }
    if (result_count != 0)
        faiss::maxheap_reorder(
                result_count, heap_distances.data(),
                heap_ids.data());
    std::vector<SearchHit> scored(result_count);
    for (std::size_t index = 0; index < result_count; ++index)
        scored[index] = SearchHit{
                static_cast<std::uint64_t>(heap_ids[index]),
                heap_distances[index]};
    return {
            std::move(scored),
            candidates_scored,
            std::vector<std::uint32_t>(
                    preassigned_lists.begin(),
                    preassigned_lists.end())};
}

SearchResult search_preassigned(
        const FullIndex& index, std::span<const float> query,
        std::span<const std::uint32_t> preassigned_lists,
        std::size_t top_k) {
    return search_preassigned_impl(
            index, query, preassigned_lists, top_k, true);
}

SearchResult search_preassigned_validated(
        const FullIndex& index, std::span<const float> query,
        std::span<const std::uint32_t> preassigned_lists,
        std::size_t top_k) {
    return search_preassigned_impl(
            index, query, preassigned_lists, top_k, false);
}

double direct_reconstruction_score(
        const FullIndex& index, std::span<const float> query,
        std::uint32_t list, std::size_t position_in_list) {
    if (!valid_full_index(index) ||
        query.size() != index.dimensions || list >= list_count(index))
        throw std::invalid_argument("direct score shape");
    if (!std::all_of(
                query.begin(), query.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("non-finite direct query");
    const std::size_t first =
            static_cast<std::size_t>(index.list_offsets[list]);
    const std::size_t last =
            static_cast<std::size_t>(index.list_offsets[list + 1]);
    if (position_in_list >= last - first)
        throw std::out_of_range("direct score candidate");
    const std::size_t candidate = first + position_in_list;
    const std::size_t stride =
            payload_bytes_per_candidate(index.model.word_bits);
    const auto code = std::span<const std::uint8_t>(
            index.payload.data() + candidate * stride, stride);
    const float* centroid =
            index.centroids.data() +
            static_cast<std::size_t>(list) * index.dimensions;

    double distance = 0;
    for (std::size_t group = 0; group < kGroups; ++group) {
        const std::size_t label = index.model.word_bits == 8
                ? code[group]
                : ((group & 1U) == 0
                           ? code[group / 2] & 0x0fU
                           : code[group / 2] >> 4);
        for (std::size_t coordinate = 0; coordinate < 2;
             ++coordinate) {
            const std::size_t dimension = 2 * group + coordinate;
            const double reconstruction =
                    static_cast<double>(centroid[dimension]) +
                    compact_center_coordinate(
                            index.model, group, label, coordinate);
            const double delta =
                    static_cast<double>(query[dimension]) -
                    reconstruction;
            distance += delta * delta;
        }
    }
    for (std::size_t dimension = kHeadDimensions;
         dimension < index.dimensions; ++dimension) {
        const double delta =
                static_cast<double>(query[dimension]) -
                centroid[dimension];
        distance += delta * delta;
    }
    return distance;
}

void save_full_index(
        const FullIndex& index, const std::filesystem::path& path) {
    const auto bytes = byte_accounting(index);
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("open full index for write");
    output.write(kMagic.data(), kMagic.size());
    write_little(output, kVersion);
    write_little(
            output, static_cast<std::uint32_t>(index.model.word_bits));
    write_little(output, static_cast<std::uint64_t>(index.dimensions));
    write_little(
            output, static_cast<std::uint64_t>(index.centroids.size()));
    write_little(
            output, static_cast<std::uint64_t>(index.model.shape.size()));
    write_little(
            output, static_cast<std::uint64_t>(index.model.groups.size()));
    write_little(
            output, static_cast<std::uint64_t>(index.list_offsets.size()));
    write_little(output, static_cast<std::uint64_t>(index.ids.size()));
    write_little(
            output, static_cast<std::uint64_t>(index.payload.size()));
    for (const float value : index.centroids) write_float(output, value);
    for (const float value : index.model.shape) write_float(output, value);
    for (const auto& group : index.model.groups) {
        write_float(output, group.mean[0]);
        write_float(output, group.mean[1]);
        for (const float value : group.transform)
            write_float(output, value);
    }
    for (const std::uint64_t value : index.list_offsets)
        write_little(output, value);
    for (const std::uint64_t value : index.ids)
        write_little(output, value);
    output.write(
            reinterpret_cast<const char*>(index.payload.data()),
            index.payload.size());
    output.close();
    if (!output ||
        std::filesystem::file_size(path) !=
                bytes.complete_serialized_bytes)
        throw std::runtime_error("full index serialized size");
}

FullIndex load_full_index(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("open full index for read");
    std::array<char, kMagic.size()> magic{};
    input.read(magic.data(), magic.size());
    if (!input || magic != kMagic ||
        read_little<std::uint32_t>(input) != kVersion)
        throw std::runtime_error("full index header");

    FullIndex result;
    result.model.word_bits =
            static_cast<int>(read_little<std::uint32_t>(input));
    result.dimensions = checked_size(
            read_little<std::uint64_t>(input), "index dimensions");
    const std::size_t centroid_count = checked_size(
            read_little<std::uint64_t>(input), "centroid count");
    const std::size_t shape_count = checked_size(
            read_little<std::uint64_t>(input), "shape count");
    const std::size_t group_count = checked_size(
            read_little<std::uint64_t>(input), "group count");
    const std::size_t offset_count = checked_size(
            read_little<std::uint64_t>(input), "offset count");
    const std::size_t id_count = checked_size(
            read_little<std::uint64_t>(input), "id count");
    const std::size_t payload_count = checked_size(
            read_little<std::uint64_t>(input), "payload count");

    result.centroids.resize(centroid_count);
    result.model.shape.resize(shape_count);
    result.model.groups.resize(group_count);
    result.list_offsets.resize(offset_count);
    result.ids.resize(id_count);
    result.payload.resize(payload_count);
    for (float& value : result.centroids) value = read_float(input);
    for (float& value : result.model.shape) value = read_float(input);
    for (auto& group : result.model.groups) {
        group.mean[0] = read_float(input);
        group.mean[1] = read_float(input);
        for (float& value : group.transform)
            value = read_float(input);
    }
    for (std::uint64_t& value : result.list_offsets)
        value = read_little<std::uint64_t>(input);
    for (std::uint64_t& value : result.ids)
        value = read_little<std::uint64_t>(input);
    input.read(
            reinterpret_cast<char*>(result.payload.data()),
            result.payload.size());
    if (!input) throw std::runtime_error("truncated full index payload");
    if (input.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("trailing full index bytes");
    if (!valid_full_index(result) ||
        std::filesystem::file_size(path) !=
                byte_accounting(result).complete_serialized_bytes)
        throw std::runtime_error("invalid loaded full index");
    return result;
}

}  // namespace structured2d

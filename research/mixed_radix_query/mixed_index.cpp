#include "mixed_index.hpp"

#include <faiss/invlists/InvertedLists.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <stdexcept>

namespace mixedradix {
namespace {

constexpr std::size_t kDimensions = 128;
constexpr std::size_t kGroups = 64;

std::size_t nearest_scalar(
        float value, const a4orb::Block& block,
        bool second_coordinate) {
    const std::size_t k1 = block.radix;
    const std::size_t count =
            second_coordinate ? block.centers / k1 : k1;
    double best = std::numeric_limits<double>::infinity();
    std::size_t selected = 0;
    for (std::size_t label = 0; label < count; ++label) {
        const std::size_t expanded =
                second_coordinate ? label * k1 : label;
        const double delta =
                static_cast<double>(value) -
                block.values[2 * expanded +
                             (second_coordinate ? 1 : 0)];
        const double distance = delta * delta;
        if (distance < best) {
            best = distance;
            selected = label;
        }
    }
    return selected;
}

void validate_model(const a4orb::Model& model) {
    const std::size_t capacity = std::size_t{1} << model.word_bits;
    if ((model.word_bits != 4 && model.word_bits != 8) ||
        model.blocks.size() != kGroups)
        throw std::invalid_argument("mixed-radix model shape");
    for (const auto& block : model.blocks) {
        if (block.dimension != 2 || block.radix == 0 ||
            block.centers == 0 || block.centers > capacity ||
            block.centers % block.radix != 0 ||
            block.values.size() != 2 * block.centers)
            throw std::invalid_argument("mixed-radix block shape");
    }
}

}  // namespace

std::uint32_t decode_label(
        const std::uint8_t* code, int bits, std::size_t group) {
    if (code == nullptr) throw std::invalid_argument("null code");
    if (bits == 8) return code[group];
    if (bits == 4)
        return (group & 1U) == 0
                ? code[group / 2] & 0x0fU
                : code[group / 2] >> 4;
    throw std::invalid_argument("mixed-radix packed bits");
}

void encode_label(
        std::uint8_t* code, int bits, std::size_t group,
        std::uint32_t label) {
    if (code == nullptr) throw std::invalid_argument("null code");
    if (bits == 8) {
        if (label > 255) throw std::out_of_range("B8 label");
        code[group] = static_cast<std::uint8_t>(label);
        return;
    }
    if (bits != 4 || label > 15)
        throw std::out_of_range("B4 label");
    std::uint8_t& byte = code[group / 2];
    if ((group & 1U) == 0)
        byte = static_cast<std::uint8_t>(
                (byte & 0xf0U) | label);
    else
        byte = static_cast<std::uint8_t>(
                (byte & 0x0fU) | (label << 4));
}

Shape shape_of(const a4orb::Model& model) {
    validate_model(model);
    Shape result;
    result.radices.reserve(kGroups);
    result.used_states.reserve(kGroups);
    for (const auto& block : model.blocks) {
        result.radices.push_back(
                static_cast<std::uint16_t>(block.radix));
        result.used_states.push_back(
                static_cast<std::uint16_t>(block.centers));
    }
    return result;
}

std::vector<float> expanded_centers(const a4orb::Model& model) {
    validate_model(model);
    const std::size_t capacity = std::size_t{1} << model.word_bits;
    std::vector<float> result(kGroups * capacity * 2);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto& block = model.blocks[group];
        float* destination =
                result.data() + group * capacity * 2;
        std::copy(
                block.values.begin(), block.values.end(),
                destination);
        // Invalid paid-for addresses are unreachable. Duplicating center zero
        // keeps the serialized Faiss codebook finite without adding a state.
        for (std::size_t label = block.centers;
             label < capacity; ++label) {
            destination[2 * label] = block.values[0];
            destination[2 * label + 1] = block.values[1];
        }
    }
    return result;
}

std::vector<std::uint8_t> encode_residual(
        std::span<const float> residual,
        const a4orb::Model& model) {
    validate_model(model);
    if (residual.size() != kDimensions ||
        !std::all_of(
                residual.begin(), residual.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::invalid_argument("mixed-radix residual shape");
    std::vector<std::uint8_t> code(
            kGroups * model.word_bits / 8, 0);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto& block = model.blocks[group];
        const std::size_t z1 = nearest_scalar(
                residual[2 * group], block, false);
        const std::size_t z2 = nearest_scalar(
                residual[2 * group + 1], block, true);
        const std::size_t label = z1 + block.radix * z2;
        if (label >= block.centers)
            throw std::runtime_error("invalid mixed-radix address");
        encode_label(
                code.data(), model.word_bits, group,
                static_cast<std::uint32_t>(label));
    }
    return code;
}

std::unique_ptr<faiss::IndexIVFPQ> build_index(
        faiss::IndexFlatL2& coarse,
        std::span<const float> base,
        std::span<const std::uint32_t> assignments,
        const a4orb::Model& model) {
    validate_model(model);
    if (coarse.d != static_cast<int>(kDimensions) ||
        coarse.ntotal <= 0 ||
        base.size() != assignments.size() * kDimensions)
        throw std::invalid_argument("mixed-radix index shape");
    auto index = std::make_unique<faiss::IndexIVFPQ>(
            &coarse, kDimensions,
            static_cast<std::size_t>(coarse.ntotal), kGroups,
            model.word_bits, faiss::METRIC_L2);
    index->own_fields = false;
    index->by_residual = true;
    index->use_precomputed_table = 0;
    index->pq.centroids = expanded_centers(model);
    index->is_trained = true;

    std::vector<float> residual(kDimensions);
    for (std::size_t row = 0; row < assignments.size(); ++row) {
        const std::uint32_t list = assignments[row];
        if (list >= static_cast<std::uint32_t>(coarse.ntotal))
            throw std::out_of_range("mixed-radix assignment");
        coarse.compute_residual(
                base.data() + row * kDimensions,
                residual.data(), list);
        const auto code = encode_residual(residual, model);
        index->invlists->add_entry(
                list, static_cast<faiss::idx_t>(row),
                code.data());
    }
    index->ntotal = static_cast<faiss::idx_t>(assignments.size());
    validate_codes(*index, shape_of(model));
    return index;
}

void validate_codes(
        const faiss::IndexIVFPQ& index, const Shape& shape) {
    if (index.pq.dsub != 2 ||
        (index.pq.nbits != 4 && index.pq.nbits != 8) ||
        shape.radices.size() != index.pq.M ||
        shape.used_states.size() != index.pq.M)
        throw std::invalid_argument("mixed-radix validation shape");
    std::uint64_t counted = 0;
    for (std::size_t list = 0; list < index.nlist; ++list) {
        faiss::InvertedLists::ScopedCodes codes(
                index.invlists, list);
        const std::size_t size = index.invlists->list_size(list);
        counted += size;
        for (std::size_t row = 0; row < size; ++row) {
            const std::uint8_t* code =
                    codes.get() + row * index.code_size;
            for (std::size_t group = 0;
                 group < index.pq.M; ++group)
                if (decode_label(
                            code, index.pq.nbits, group) >=
                    shape.used_states[group])
                    throw std::runtime_error(
                            "stored invalid mixed-radix label");
        }
    }
    if (counted != static_cast<std::uint64_t>(index.ntotal))
        throw std::runtime_error("mixed-radix ntotal mismatch");
}

}  // namespace mixedradix

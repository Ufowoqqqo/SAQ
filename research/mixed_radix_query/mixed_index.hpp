#pragma once

#include "../a4_or_b/models.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <vector>

namespace mixedradix {

struct Shape {
    std::vector<std::uint16_t> radices;
    std::vector<std::uint16_t> used_states;
};

std::uint32_t decode_label(
        const std::uint8_t* code, int bits, std::size_t group);

void encode_label(
        std::uint8_t* code, int bits, std::size_t group,
        std::uint32_t label);

Shape shape_of(const a4orb::Model& model);

std::vector<float> expanded_centers(const a4orb::Model& model);

std::vector<std::uint8_t> encode_residual(
        std::span<const float> residual,
        const a4orb::Model& model);

std::unique_ptr<faiss::IndexIVFPQ> build_index(
        faiss::IndexFlatL2& coarse,
        std::span<const float> base,
        std::span<const std::uint32_t> assignments,
        const a4orb::Model& model);

void validate_codes(
        const faiss::IndexIVFPQ& index, const Shape& shape);

}  // namespace mixedradix

#include "mixed_index.hpp"

#include <faiss/IndexFlat.h>

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

a4orb::Model model(int bits) {
    a4orb::Model result;
    result.arm = 'A';
    result.word_bits = bits;
    for (std::size_t group = 0; group < 64; ++group) {
        const std::size_t k1 = bits == 4 ? 3 : 15;
        const std::size_t k2 = bits == 4 ? 5 : 17;
        a4orb::Block block{2, k1 * k2, k1, {}, false};
        for (std::size_t z2 = 0; z2 < k2; ++z2)
            for (std::size_t z1 = 0; z1 < k1; ++z1) {
                block.values.push_back(static_cast<float>(z1));
                block.values.push_back(static_cast<float>(z2));
            }
        result.blocks.push_back(std::move(block));
    }
    return result;
}

void packing_test(int bits) {
    const std::size_t groups = 64;
    std::vector<std::uint8_t> bytes(groups * bits / 8, 0);
    const std::uint32_t mask =
            bits == 4 ? 15U : 255U;
    for (std::size_t group = 0; group < groups; ++group)
        mixedradix::encode_label(
                bytes.data(), bits, group,
                static_cast<std::uint32_t>(group) & mask);
    for (std::size_t group = 0; group < groups; ++group)
        require(
                mixedradix::decode_label(
                        bytes.data(), bits, group) ==
                        (static_cast<std::uint32_t>(group) & mask),
                "packed round-trip");
}

void encoding_test(int bits) {
    const auto candidate = model(bits);
    std::vector<float> residual(128);
    for (std::size_t group = 0; group < 64; ++group) {
        residual[2 * group] = 1.1f;
        residual[2 * group + 1] = 2.2f;
    }
    const auto code =
            mixedradix::encode_residual(residual, candidate);
    const auto shape = mixedradix::shape_of(candidate);
    for (std::size_t group = 0; group < 64; ++group) {
        const auto label = mixedradix::decode_label(
                code.data(), bits, group);
        require(label == 1 + shape.radices[group] * 2,
                "nearest scalar address");
        require(label < shape.used_states[group],
                "valid scalar address");
    }
    const auto centers =
            mixedradix::expanded_centers(candidate);
    require(
            centers.size() ==
                    64 * (std::size_t{1} << bits) * 2,
            "expanded center shape");
}

void index_test() {
    const auto candidate = model(4);
    faiss::IndexFlatL2 coarse(128);
    std::vector<float> centroids(2 * 128, 0);
    centroids[128] = 10;
    coarse.add(2, centroids.data());
    std::vector<float> base(3 * 128, 0);
    base[0] = 1;
    base[128] = 11;
    base[256] = 2;
    const std::vector<std::uint32_t> assignments{0, 1, 0};
    auto index = mixedradix::build_index(
            coarse, base, assignments, candidate);
    require(index->ntotal == 3, "index ntotal");
    require(index->invlists->list_size(0) == 2,
            "index list zero");
    require(index->invlists->list_size(1) == 1,
            "index list one");
    mixedradix::validate_codes(
            *index, mixedradix::shape_of(candidate));
}

}  // namespace

int main() {
    try {
        packing_test(4);
        packing_test(8);
        encoding_test(4);
        encoding_test(8);
        index_test();
        std::cout << "mixed_index_test: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "mixed_index_test: " << error.what() << '\n';
        return 1;
    }
}

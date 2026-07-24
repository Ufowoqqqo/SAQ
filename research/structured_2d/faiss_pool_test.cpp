#include "faiss_pool.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVF.h>

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::vector<float> fixture(std::size_t rows, std::size_t dimensions) {
    std::vector<float> result(rows * dimensions);
    for (std::size_t row = 0; row < rows; ++row)
        for (std::size_t dimension = 0;
             dimension < dimensions; ++dimension)
            result[row * dimensions + dimension] =
                    static_cast<float>(
                            std::sin(0.13 * (row + 1) *
                                     (dimension + 3)) +
                            row * 0.01);
    return result;
}

void parse_test() {
    const auto pq =
            structured2d::admission::parse_native_faiss_arm(
                    "PQFULL_M32X8", 128, 1024);
    require(pq.subquantizers == 32 && pq.bits == 8, "PQ parse");
    const auto head =
            structured2d::admission::parse_native_faiss_arm(
                    "PQ128_M64X8", 128, 1024);
    require(
            head.subquantizers == 64 && head.bits == 8,
            "PQ head parse");
    const auto rabitq =
            structured2d::admission::parse_native_faiss_arm(
                    "RABITQFS_B4", 128, 1024);
    require(rabitq.bits == 4, "RaBitQ parse");
}

void arm_test(const std::string& id) {
    constexpr std::size_t dimensions = 8;
    constexpr std::size_t learn_rows = 128;
    constexpr std::size_t base_rows = 256;
    constexpr std::size_t nlist = 4;
    const auto learn = fixture(learn_rows, dimensions);
    const auto base = fixture(base_rows, dimensions);
    faiss::IndexFlatL2 coarse(dimensions);
    const std::vector<float> centroids{
            base.begin(), base.begin() + nlist * dimensions};
    coarse.add(nlist, centroids.data());
    std::vector<faiss::idx_t> assigned(base_rows);
    coarse.assign(base_rows, base.data(), assigned.data());
    std::vector<std::uint32_t> assignments(base_rows);
    for (std::size_t row = 0; row < base_rows; ++row)
        assignments[row] =
                static_cast<std::uint32_t>(assigned[row]);

    auto config =
            structured2d::admission::parse_native_faiss_arm(
                    id, dimensions, nlist);
    auto index =
            structured2d::admission::make_native_faiss_arm(
                    config, &coarse, learn_rows);
    std::vector<faiss::idx_t> assigned_learn(learn_rows);
    coarse.assign(
            learn_rows, learn.data(), assigned_learn.data());
    std::vector<std::uint32_t> learn_assignments(learn_rows);
    for (std::size_t row = 0; row < learn_rows; ++row)
        learn_assignments[row] =
                static_cast<std::uint32_t>(
                        assigned_learn[row]);
    structured2d::admission::train_native_faiss_arm(
            *index, learn, learn_assignments, dimensions);
    structured2d::admission::add_native_faiss_arm(
            *index, base, assignments, dimensions);
    structured2d::admission::verify_native_faiss_layout(
            *index, assignments);
    require(index->ntotal == base_rows, "native arm rows");
}

}  // namespace

int main() {
    try {
        parse_test();
        arm_test("IVFFLAT");
        arm_test("PQFULL_M2X4");
        arm_test("PQFSFULL_M2X4");
        arm_test("RABITQ_B1");
        arm_test("RABITQFS_B1");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "faiss_pool_test: " << error.what() << '\n';
        return 1;
    }
}

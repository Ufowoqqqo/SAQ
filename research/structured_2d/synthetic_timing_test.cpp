#include "synthetic_timing.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <tuple>
#include <utility>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

struct Fixture {
    faiss::IndexFlatL2 coarse{2};
    faiss::IndexIVFPQ index;

    explicit Fixture(bool by_residual)
            : index(
                      &coarse, 2, 2, 1, 4,
                      faiss::METRIC_L2) {
        const float centroids[]{0, 0, 10, 0};
        coarse.add(2, centroids);
        index.own_fields = false;
        index.by_residual = by_residual;
        index.use_precomputed_table = 0;
        index.pq.centroids.resize(16 * 2);
        for (std::size_t z2 = 0; z2 < 4; ++z2)
            for (std::size_t z1 = 0; z1 < 4; ++z1) {
                const std::size_t label = z1 + 4 * z2;
                index.pq.centroids[2 * label] =
                        static_cast<float>(z1);
                index.pq.centroids[2 * label + 1] =
                        static_cast<float>(z2);
            }
        index.is_trained = true;
        const auto add = [this](
                                 faiss::idx_t list,
                                 faiss::idx_t id,
                                 std::uint8_t label) {
            index.invlists->add_entry(list, id, &label);
        };
        add(0, 7, 0);
        add(0, 3, 1);
        add(0, 5, 4);
        add(1, 11, 0);
        add(1, 13, 15);
    }
};

std::vector<std::pair<float, faiss::idx_t>> reference() {
    const float query[]{0.2f, 0.3f, 0, 0};
    const float full_centroids[]{0, 0, 0, 0, 10, 0, 0, 4};
    const std::vector<std::tuple<int, int, int>> candidates{
            {0, 7, 0}, {0, 3, 1}, {0, 5, 4},
            {1, 11, 0}, {1, 13, 15}};
    std::vector<std::pair<float, faiss::idx_t>> result;
    for (const auto& [list, id, label] : candidates) {
        const std::size_t z1 = label % 4;
        const std::size_t z2 = label / 4;
        const float rx =
                query[0] - full_centroids[4 * list];
        const float ry =
                query[1] - full_centroids[4 * list + 1];
        const float tail =
                query[3] - full_centroids[4 * list + 3];
        const float distance =
                (rx - z1) * (rx - z1) +
                (ry - z2) * (ry - z2) + tail * tail;
        result.emplace_back(distance, id);
    }
    std::sort(
            result.begin(), result.end(),
            [](const auto& left, const auto& right) {
                return left.first != right.first
                        ? left.first < right.first
                        : left.second < right.second;
            });
    result.resize(4);
    return result;
}

void compare(
        const structured2d::admission::TopKResult& actual) {
    const auto expected = reference();
    require(actual.ids.size() == expected.size(), "top-k size");
    require(actual.candidates == 5, "candidate count");
    for (std::size_t index = 0; index < expected.size(); ++index) {
        require(actual.ids[index] == expected[index].second, "top-k id");
        require(
                std::fabs(
                        actual.distances[index] -
                        expected[index].first) < 1e-5f,
                "top-k distance");
    }
}

void regular_and_d_test() {
    Fixture fixture(true);
    const std::vector<float> query{0.2f, 0.3f, 0, 0};
    const std::vector<float> centroids{
            0, 0, 0, 0, 10, 0, 0, 4};
    const std::vector<faiss::idx_t> lists{0, 1};
    compare(structured2d::admission::search_ivfpq_lists(
            fixture.index, nullptr, query, centroids,
            4, 2, lists, 4));
    const std::vector<std::uint16_t> radices{4};
    compare(structured2d::admission::search_dyadic_lists(
            fixture.index, radices, query, centroids,
            4, 2, lists, 4));
}

void opq_test() {
    Fixture fixture(false);
    faiss::LinearTransform identity(2, 2, false);
    identity.A = {1, 0, 0, 1};
    identity.is_trained = true;
    identity.is_orthonormal = true;
    const std::vector<float> query{0.2f, 0.3f, 0, 0};
    const std::vector<float> centroids{
            0, 0, 0, 0, 10, 0, 0, 4};
    const std::vector<faiss::idx_t> lists{0, 1};
    compare(structured2d::admission::search_ivfpq_lists(
            fixture.index, &identity, query, centroids,
            4, 2, lists, 4));
}

}  // namespace

int main() {
    try {
        regular_and_d_test();
        opq_test();
        std::cout << "PASS structured_2d_synthetic_timing_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

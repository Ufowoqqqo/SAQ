#include <algorithm>
#include <numeric>
#include <tuple>
#include <vector>

#include <gtest/gtest.h>

#include "baseline/symphonyqg_fastscan.hpp"
#include "fixtures/symphonyqg_scalar_fixture_input.hpp"
#include "fixtures/symphonyqg_scalar_reference.hpp"
#include "fixtures/symphonyqg_scalar_reference_strict.hpp"

using namespace saqlib;

namespace input = symphonyqg_scalar_fixture_input;
#if defined(NDEBUG)
namespace reference = symphonyqg_scalar_reference;
#else
namespace reference = symphonyqg_scalar_reference_strict;
#endif

namespace {

FloatVec makeQuery() {
    FloatVec query(input::kDimension);
    for (size_t dim = 0; dim < input::kDimension; ++dim) {
        query[dim] = input::queryValue(dim);
    }
    return query;
}

FloatVec makeCurrent() {
    FloatVec current(input::kDimension);
    for (size_t dim = 0; dim < input::kDimension; ++dim) {
        current[dim] = input::currentValue(dim);
    }
    return current;
}

FloatVec makeNeighbor(size_t neighbor) {
    FloatVec result(input::kDimension);
    for (size_t dim = 0; dim < input::kDimension; ++dim) {
        result[dim] = input::neighborValue(neighbor, dim);
    }
    return result;
}

std::vector<baseline::SymphonyQGScalarNeighbor> encodeFixtureNeighbors(
    const baseline::SymphonyQGScalarEstimator &scalar,
    const FloatVec &rotated_current) {
    std::vector<baseline::SymphonyQGScalarNeighbor> neighbors(
        input::kNeighborCount);
    for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
        const FloatVec source = makeNeighbor(neighbor);
        FloatVec rotated;
        scalar.rotate(source.data(), rotated);
        scalar.encodeNeighbor(
            rotated_current.data(), rotated.data(), neighbors[neighbor]);
    }
    return neighbors;
}

} // namespace

TEST(SymphonyQGFastScanParityTest, PackedLayoutAndScanMatchPinnedSource) {
    baseline::SymphonyQGScalarEstimator scalar(
        input::kDimension, input::kRotationSeed);
    baseline::SymphonyQGFastScanEstimator fastscan(
        scalar.padded_dimension());
    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const auto scalar_query = scalar.prepareQuery(query.data());
    const auto packed_query = fastscan.prepareQuery(scalar_query);
    FloatVec rotated_current;
    scalar.rotate(current.data(), rotated_current);
    const auto neighbors = encodeFixtureNeighbors(scalar, rotated_current);
    const auto batch = fastscan.encodeBatch(neighbors);

    EXPECT_EQ(batch.neighbor_count, reference::kNeighborCount);
    EXPECT_EQ(batch.padded_neighbor_count, reference::kPackedNeighborCount);
    ASSERT_EQ(packed_query.packed_lut.size(), reference::kPackedLut.size());
    for (size_t offset = 0; offset < reference::kPackedLut.size(); ++offset) {
        EXPECT_EQ(packed_query.packed_lut[offset], reference::kPackedLut[offset])
            << "LUT offset=" << offset;
    }
    ASSERT_EQ(batch.packed_codes.size(), reference::kPackedCodes.size());
    for (size_t offset = 0; offset < reference::kPackedCodes.size(); ++offset) {
        EXPECT_EQ(batch.packed_codes[offset], reference::kPackedCodes[offset])
            << "code offset=" << offset;
    }

    const auto positive_sums = fastscan.positiveCodeSums(packed_query, batch);
    ASSERT_EQ(positive_sums.size(), reference::kPositiveCodeSum.size());
    for (size_t neighbor = 0;
         neighbor < reference::kPositiveCodeSum.size(); ++neighbor) {
        EXPECT_EQ(positive_sums[neighbor], reference::kPositiveCodeSum[neighbor])
            << "neighbor=" << neighbor;
    }

    const auto signed_dots = fastscan.signedQueryCodeDots(packed_query, batch);
    ASSERT_EQ(signed_dots.size(), reference::kPackedSignedDot.size());
    for (size_t neighbor = 0; neighbor < signed_dots.size(); ++neighbor) {
        EXPECT_EQ(signed_dots[neighbor], reference::kPackedSignedDot[neighbor])
            << "neighbor=" << neighbor;
        EXPECT_EQ(
            signed_dots[neighbor],
            scalar.signedQueryCodeDot(scalar_query, neighbors[neighbor]))
            << "scalar neighbor=" << neighbor;
    }

    const auto distances = fastscan.estimateBatch(
        packed_query, reference::kCurrentDistance, batch);
    ASSERT_EQ(distances.size(), reference::kPackedEstimatedDistance.size());
    for (size_t neighbor = 0; neighbor < distances.size(); ++neighbor) {
        EXPECT_NEAR(
            distances[neighbor], reference::kPackedEstimatedDistance[neighbor],
            5e-5f)
            << "neighbor=" << neighbor;
        EXPECT_NEAR(
            distances[neighbor],
            scalar.estimate(
                scalar_query, reference::kCurrentDistance, neighbors[neighbor]),
            5e-5f)
            << "scalar neighbor=" << neighbor;
    }

    std::vector<size_t> order(distances.size());
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](size_t left, size_t right) {
        return std::tie(distances[left], left) <
               std::tie(distances[right], right);
    });
    EXPECT_TRUE(std::equal(
        order.begin(), order.end(), reference::kPackedOrder.begin()));
}

TEST(SymphonyQGFastScanParityTest, MultipleBatchesMatchScalar) {
    baseline::SymphonyQGScalarEstimator scalar(
        input::kDimension, input::kRotationSeed);
    baseline::SymphonyQGFastScanEstimator fastscan(
        scalar.padded_dimension());
    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const auto scalar_query = scalar.prepareQuery(query.data());
    const auto packed_query = fastscan.prepareQuery(scalar_query);
    FloatVec rotated_current;
    scalar.rotate(current.data(), rotated_current);
    const auto fixture_neighbors =
        encodeFixtureNeighbors(scalar, rotated_current);

    std::vector<baseline::SymphonyQGScalarNeighbor> neighbors(33);
    for (size_t neighbor = 0; neighbor < neighbors.size(); ++neighbor) {
        neighbors[neighbor] = fixture_neighbors[neighbor % fixture_neighbors.size()];
    }
    const auto batch = fastscan.encodeBatch(neighbors);
    EXPECT_EQ(batch.padded_neighbor_count, 64);
    const auto signed_dots = fastscan.signedQueryCodeDots(packed_query, batch);
    const auto distances = fastscan.estimateBatch(
        packed_query, reference::kCurrentDistance, batch);
    ASSERT_EQ(signed_dots.size(), neighbors.size());
    ASSERT_EQ(distances.size(), neighbors.size());
    for (size_t neighbor = 0; neighbor < neighbors.size(); ++neighbor) {
        EXPECT_EQ(
            signed_dots[neighbor],
            scalar.signedQueryCodeDot(scalar_query, neighbors[neighbor]))
            << "neighbor=" << neighbor;
        EXPECT_NEAR(
            distances[neighbor],
            scalar.estimate(
                scalar_query, reference::kCurrentDistance, neighbors[neighbor]),
            5e-5f)
            << "neighbor=" << neighbor;
    }
}

TEST(SymphonyQGFastScanParityTest, GistDimensionMultipleBatchesMatchScalar) {
    constexpr size_t dimension = 960;
    constexpr size_t neighbor_count = 33;
    baseline::SymphonyQGScalarEstimator scalar(dimension, 0);
    baseline::SymphonyQGFastScanEstimator fastscan(
        scalar.padded_dimension());

    FloatVec query(dimension);
    FloatVec current(dimension);
    for (size_t dim = 0; dim < dimension; ++dim) {
        query[dim] = static_cast<float>(
                         static_cast<int>((dim * 7 + 3) % 101) - 50) /
                     16.0f;
        current[dim] = static_cast<float>(
                           static_cast<int>((dim * 11 + 5) % 97) - 48) /
                       16.0f;
    }
    const auto scalar_query = scalar.prepareQuery(query.data());
    const auto packed_query = fastscan.prepareQuery(scalar_query);
    FloatVec rotated_current;
    scalar.rotate(current.data(), rotated_current);

    std::vector<baseline::SymphonyQGScalarNeighbor> neighbors(neighbor_count);
    for (size_t neighbor = 0; neighbor < neighbor_count; ++neighbor) {
        FloatVec source(dimension);
        for (size_t dim = 0; dim < dimension; ++dim) {
            const int raw_delta = static_cast<int>(
                                      ((neighbor + 1) * (dim + 3) * 13 +
                                       neighbor * 7) %
                                      41) -
                                  20;
            const int delta =
                raw_delta == 0 ? (neighbor % 2 == 0 ? 1 : -1) : raw_delta;
            source[dim] = current[dim] + static_cast<float>(delta) / 32.0f;
        }
        FloatVec rotated;
        scalar.rotate(source.data(), rotated);
        scalar.encodeNeighbor(
            rotated_current.data(), rotated.data(), neighbors[neighbor]);
    }

    const auto batch = fastscan.encodeBatch(neighbors);
    EXPECT_EQ(batch.padded_neighbor_count, 64);
    const auto signed_dots = fastscan.signedQueryCodeDots(packed_query, batch);
    constexpr float current_distance = 1234.5f;
    const auto packed_distances = fastscan.estimateBatch(
        packed_query, current_distance, batch);
    std::vector<float> scalar_distances(neighbor_count);
    for (size_t neighbor = 0; neighbor < neighbor_count; ++neighbor) {
        EXPECT_EQ(
            signed_dots[neighbor],
            scalar.signedQueryCodeDot(scalar_query, neighbors[neighbor]))
            << "neighbor=" << neighbor;
        scalar_distances[neighbor] = scalar.estimate(
            scalar_query, current_distance, neighbors[neighbor]);
        EXPECT_NEAR(
            packed_distances[neighbor], scalar_distances[neighbor], 5e-4f)
            << "neighbor=" << neighbor;
    }

    std::vector<size_t> scalar_order(neighbor_count);
    std::vector<size_t> packed_order(neighbor_count);
    std::iota(scalar_order.begin(), scalar_order.end(), 0);
    std::iota(packed_order.begin(), packed_order.end(), 0);
    std::sort(
        scalar_order.begin(), scalar_order.end(), [&](size_t left, size_t right) {
            return std::tie(scalar_distances[left], left) <
                   std::tie(scalar_distances[right], right);
        });
    std::sort(
        packed_order.begin(), packed_order.end(), [&](size_t left, size_t right) {
            return std::tie(packed_distances[left], left) <
                   std::tie(packed_distances[right], right);
        });
    EXPECT_EQ(packed_order, scalar_order);
}

TEST(SymphonyQGFastScanRobustnessTest, ZeroResidualAndPaddingRemainExact) {
    baseline::SymphonyQGScalarEstimator scalar(
        input::kDimension, input::kRotationSeed);
    baseline::SymphonyQGFastScanEstimator fastscan(
        scalar.padded_dimension());
    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const auto scalar_query = scalar.prepareQuery(query.data());
    const auto packed_query = fastscan.prepareQuery(scalar_query);
    FloatVec rotated_current;
    scalar.rotate(current.data(), rotated_current);

    baseline::SymphonyQGScalarNeighbor zero;
    scalar.encodeNeighbor(
        rotated_current.data(), rotated_current.data(), zero);
    ASSERT_TRUE(zero.zero_residual);
    const auto batch = fastscan.encodeBatch({zero});
    EXPECT_EQ(batch.neighbor_count, 1);
    EXPECT_EQ(batch.padded_neighbor_count, 32);
    const auto distances = fastscan.estimateBatch(packed_query, 12.5f, batch);
    ASSERT_EQ(distances.size(), 1);
    EXPECT_EQ(distances[0], 12.5f);
}

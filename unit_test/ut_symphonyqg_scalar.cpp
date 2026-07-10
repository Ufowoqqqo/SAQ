#include <algorithm>
#include <numeric>
#include <string_view>
#include <tuple>
#include <vector>

#include <gtest/gtest.h>

#include "baseline/symphonyqg_scalar.hpp"
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

void expectVectorNear(const FloatVec &actual, const auto &expected, float tolerance) {
    ASSERT_EQ(static_cast<size_t>(actual.size()), expected.size());
    for (size_t index = 0; index < expected.size(); ++index) {
        EXPECT_NEAR(actual[index], expected[index], tolerance) << "index=" << index;
    }
}

} // namespace

TEST(SymphonyQGScalarParityTest, RotationAndQueryStateMatchPinnedSource) {
    baseline::SymphonyQGScalarEstimator estimator(
        input::kDimension, input::kRotationSeed);
    EXPECT_EQ(estimator.dimension(), reference::kDimension);
    EXPECT_EQ(estimator.padded_dimension(), reference::kPaddedDimension);
    EXPECT_EQ(estimator.rotation_seed(), reference::kRotationSeed);
    EXPECT_EQ(
        baseline::SymphonyQGScalarEstimator::kSourceRevision,
        std::string_view(reference::kSourceRevision));

    ASSERT_EQ(estimator.signs().size(), reference::kSigns.size());
    for (size_t dim = 0; dim < reference::kSigns.size(); ++dim) {
        EXPECT_EQ(estimator.signs()[dim], reference::kSigns[dim]) << "dim=" << dim;
    }

    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const FloatVec neighbor0 = makeNeighbor(0);
    FloatVec rotated_query;
    FloatVec rotated_current;
    FloatVec rotated_neighbor0;
    estimator.rotate(query.data(), rotated_query);
    estimator.rotate(current.data(), rotated_current);
    estimator.rotate(neighbor0.data(), rotated_neighbor0);
    expectVectorNear(rotated_query, reference::kRotatedQuery, 1e-6f);
    expectVectorNear(rotated_current, reference::kRotatedCurrent, 1e-6f);
    expectVectorNear(rotated_neighbor0, reference::kRotatedNeighbor0, 1e-6f);

    const auto prepared = estimator.prepareQuery(query.data());
    expectVectorNear(prepared.rotated, reference::kRotatedQuery, 1e-6f);
    EXPECT_NEAR(prepared.lower, reference::kQueryLower, 1e-7f);
    EXPECT_NEAR(prepared.upper, reference::kQueryUpper, 1e-7f);
    EXPECT_NEAR(prepared.width, reference::kQueryWidth, 1e-7f);
    EXPECT_EQ(prepared.code_sum, reference::kQueryCodeSum);
    ASSERT_EQ(prepared.codes.size(), reference::kQueryCodes.size());
    for (size_t dim = 0; dim < reference::kQueryCodes.size(); ++dim) {
        EXPECT_EQ(prepared.codes[dim], reference::kQueryCodes[dim]) << "dim=" << dim;
    }
}

TEST(SymphonyQGScalarParityTest, FactorsDistancesAndOrderingMatchPinnedSource) {
    baseline::SymphonyQGScalarEstimator estimator(
        input::kDimension, input::kRotationSeed);
    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const auto prepared = estimator.prepareQuery(query.data());
    FloatVec rotated_current;
    estimator.rotate(current.data(), rotated_current);

    const float current_distance = (query - current).squaredNorm();
    EXPECT_NEAR(current_distance, reference::kCurrentDistance, 5e-5f);

    std::vector<float> distances(reference::kNeighborCount);
    for (size_t neighbor = 0; neighbor < reference::kNeighborCount; ++neighbor) {
        const FloatVec source_neighbor = makeNeighbor(neighbor);
        FloatVec rotated_neighbor;
        estimator.rotate(source_neighbor.data(), rotated_neighbor);

        baseline::SymphonyQGScalarNeighbor encoded;
        estimator.encodeNeighbor(
            rotated_current.data(), rotated_neighbor.data(), encoded);
        ASSERT_EQ(encoded.residual_positive.size(), reference::kPaddedDimension);
        for (size_t dim = 0; dim < reference::kPaddedDimension; ++dim) {
            const size_t flat_index = neighbor * reference::kPaddedDimension + dim;
            EXPECT_EQ(
                encoded.residual_positive[dim], reference::kResidualPositive[flat_index])
                << "neighbor=" << neighbor << " dim=" << dim;
        }

        EXPECT_NEAR(encoded.triple_x, reference::kTriple[neighbor], 2e-5f)
            << "neighbor=" << neighbor;
        EXPECT_NEAR(encoded.factor_dq, reference::kFactorDq[neighbor], 2e-6f)
            << "neighbor=" << neighbor;
        EXPECT_NEAR(encoded.factor_vq, reference::kFactorVq[neighbor], 2e-5f)
            << "neighbor=" << neighbor;
        EXPECT_EQ(
            estimator.signedQueryCodeDot(prepared, encoded),
            static_cast<int32_t>(reference::kSignedDot[neighbor]))
            << "neighbor=" << neighbor;

        distances[neighbor] =
            estimator.estimate(prepared, reference::kCurrentDistance, encoded);
        EXPECT_NEAR(
            distances[neighbor], reference::kEstimatedDistance[neighbor], 5e-5f)
            << "neighbor=" << neighbor;
    }

    std::vector<size_t> order(reference::kNeighborCount);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](size_t left, size_t right) {
        return std::tie(distances[left], left) < std::tie(distances[right], right);
    });
    EXPECT_TRUE(std::equal(order.begin(), order.end(), reference::kOrder.begin()));
}

TEST(SymphonyQGScalarRobustnessTest, ZeroResidualReturnsCurrentDistance) {
    baseline::SymphonyQGScalarEstimator estimator(
        input::kDimension, input::kRotationSeed);
    const FloatVec query = makeQuery();
    const FloatVec current = makeCurrent();
    const auto prepared = estimator.prepareQuery(query.data());

    FloatVec rotated_current;
    estimator.rotate(current.data(), rotated_current);
    baseline::SymphonyQGScalarNeighbor encoded;
    estimator.encodeNeighbor(
        rotated_current.data(), rotated_current.data(), encoded);

    EXPECT_TRUE(encoded.zero_residual);
    EXPECT_EQ(encoded.triple_x, 0.0f);
    EXPECT_EQ(encoded.factor_dq, 0.0f);
    EXPECT_EQ(encoded.factor_vq, 0.0f);
    EXPECT_EQ(estimator.estimate(prepared, 12.5f, encoded), 12.5f);
}

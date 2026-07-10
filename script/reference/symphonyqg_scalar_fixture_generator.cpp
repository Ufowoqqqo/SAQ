#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <tuple>
#include <type_traits>
#include <vector>

#include "common.hpp"
#include "qg/qg_scanner.hpp"
#include "quantization/rabitq.hpp"
#include "space/l2.hpp"
#include "third/ffht/fht_avx.hpp"
#include "utils/memory.hpp"
#include "utils/scalar_quantize.hpp"

#include "symphonyqg_scalar_fixture_input.hpp"

namespace input = symphonyqg_scalar_fixture_input;

namespace {

template <typename Container>
void printArray(const std::string &name, const Container &values, const std::string &type) {
    using T = typename Container::value_type;
    std::cout << "inline constexpr std::array<" << type << ", " << values.size() << "> "
              << name << " = {\n    ";
    for (size_t i = 0; i < values.size(); ++i) {
        if constexpr (std::is_floating_point_v<T>) {
            std::cout << std::showpoint << std::setprecision(9) << values[i] << 'f';
        } else {
            std::cout << static_cast<long long>(values[i]);
        }
        if (i + 1 != values.size()) {
            if ((i + 1) % 8 == 0) {
                std::cout << ",\n    ";
            } else {
                std::cout << ", ";
            }
        }
    }
    std::cout << "\n};\n\n";
}

std::vector<int8_t> makeSigns() {
    std::mt19937_64 generator(input::kRotationSeed);
    std::uniform_int_distribution<int> bernoulli(0, 1);
    std::vector<int8_t> signs(input::kPaddedDimension);
    for (auto &sign : signs) {
        sign = static_cast<int8_t>((2 * bernoulli(generator)) - 1);
    }
    return signs;
}

using AlignedFloatVector =
    std::vector<float, symqg::memory::AlignedAllocator<float, 64>>;

AlignedFloatVector rotate(const std::vector<float> &source, const std::vector<int8_t> &signs) {
    AlignedFloatVector result(input::kPaddedDimension, 0.0f);
    const float scale = 1.0f / std::sqrt(static_cast<float>(input::kPaddedDimension));
    for (size_t dim = 0; dim < input::kDimension; ++dim) {
        result[dim] = source[dim] * static_cast<float>(signs[dim]) * scale;
    }
    helper_float_6(result.data());
    return result;
}

} // namespace

int main(int argc, char **argv) {
    const std::string output_namespace =
        argc > 1 ? argv[1] : "symphonyqg_scalar_reference";
    std::vector<float> query(input::kDimension);
    std::vector<float> current(input::kDimension);
    std::vector<std::vector<float>> neighbors(
        input::kNeighborCount, std::vector<float>(input::kDimension));
    for (size_t dim = 0; dim < input::kDimension; ++dim) {
        query[dim] = input::queryValue(dim);
        current[dim] = input::currentValue(dim);
        for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
            neighbors[neighbor][dim] = input::neighborValue(neighbor, dim);
        }
    }

    const auto signs = makeSigns();
    const auto rotated_query = rotate(query, signs);
    const auto rotated_current = rotate(current, signs);
    std::vector<AlignedFloatVector> rotated_neighbors(input::kNeighborCount);
    for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
        rotated_neighbors[neighbor] = rotate(neighbors[neighbor], signs);
    }

    float lower = 0.0f;
    float upper = 0.0f;
    symqg::scalar::data_range(
        rotated_query.data(), input::kPaddedDimension, lower, upper);
    const float width = (upper - lower) / static_cast<float>((1 << QG_BQUERY) - 1);
    std::vector<uint8_t> query_codes(input::kPaddedDimension);
    int32_t query_code_sum = 0;
    symqg::scalar::quantize(
        query_codes.data(), rotated_query.data(), input::kPaddedDimension,
        lower, width, query_code_sum);

    symqg::RowMatrix<float> rotated_neighbor_matrix(
        input::kNeighborCount, input::kPaddedDimension);
    symqg::RowMatrix<float> rotated_current_matrix(1, input::kPaddedDimension);
    for (size_t dim = 0; dim < input::kPaddedDimension; ++dim) {
        rotated_current_matrix(0, static_cast<long>(dim)) = rotated_current[dim];
        for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
            rotated_neighbor_matrix(
                static_cast<long>(neighbor), static_cast<long>(dim)) =
                rotated_neighbors[neighbor][dim] - rotated_current[dim];
        }
    }

    symqg::RowMatrix<int> binary(input::kNeighborCount, input::kPaddedDimension);
    std::vector<uint8_t> binary_flat(input::kNeighborCount * input::kPaddedDimension);
    for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
        for (size_t dim = 0; dim < input::kPaddedDimension; ++dim) {
            const int positive = rotated_neighbor_matrix(
                                     static_cast<long>(neighbor), static_cast<long>(dim)) > 0.0f
                                     ? 1
                                     : 0;
            binary(static_cast<long>(neighbor), static_cast<long>(dim)) = positive;
            binary_flat[neighbor * input::kPaddedDimension + dim] =
                static_cast<uint8_t>(positive);
        }
    }

    std::vector<float> triple(input::kNeighborCount);
    std::vector<float> factor_dq(input::kNeighborCount);
    std::vector<float> factor_vq(input::kNeighborCount);
    symqg::rabitq_factors(
        rotated_neighbor_matrix, rotated_current_matrix, binary,
        triple.data(), factor_dq.data(), factor_vq.data());

    std::vector<float> signed_dot(input::kNeighborCount);
    for (size_t neighbor = 0; neighbor < input::kNeighborCount; ++neighbor) {
        int32_t dot = 0;
        for (size_t dim = 0; dim < input::kPaddedDimension; ++dim) {
            dot += binary(static_cast<long>(neighbor), static_cast<long>(dim)) != 0
                       ? static_cast<int32_t>(query_codes[dim])
                       : -static_cast<int32_t>(query_codes[dim]);
        }
        signed_dot[neighbor] = static_cast<float>(dot);
    }

    const float current_distance =
        symqg::space::l2_sqr(query.data(), current.data(), input::kDimension);
    std::vector<float> estimated_distance(input::kNeighborCount);
    symqg::appro_dist_impl(
        input::kNeighborCount, current_distance, width, lower,
        signed_dot.data(), triple.data(), factor_dq.data(), factor_vq.data(),
        estimated_distance.data());

    std::vector<size_t> order(input::kNeighborCount);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](size_t left, size_t right) {
        return std::tie(estimated_distance[left], left) <
               std::tie(estimated_distance[right], right);
    });

    std::cout << "#pragma once\n\n";
    std::cout << "#include <array>\n#include <cstddef>\n#include <cstdint>\n\n";
    std::cout << "namespace " << output_namespace << " {\n\n";
    std::cout << "inline constexpr const char *kSourceRevision = "
              << "\"6124ddb34ee4d176edea1bd7ad38d1672343df28\";\n";
    std::cout << "inline constexpr size_t kDimension = " << input::kDimension << ";\n";
    std::cout << "inline constexpr size_t kPaddedDimension = "
              << input::kPaddedDimension << ";\n";
    std::cout << "inline constexpr size_t kNeighborCount = "
              << input::kNeighborCount << ";\n";
    std::cout << "inline constexpr uint64_t kRotationSeed = "
              << input::kRotationSeed << ";\n\n";

    printArray("kSigns", signs, "int8_t");
    printArray("kRotatedQuery", rotated_query, "float");
    printArray("kRotatedCurrent", rotated_current, "float");
    printArray("kRotatedNeighbor0", rotated_neighbors.front(), "float");
    std::cout << "inline constexpr float kQueryLower = " << std::setprecision(9)
              << lower << "f;\n";
    std::cout << "inline constexpr float kQueryUpper = " << std::setprecision(9)
              << upper << "f;\n";
    std::cout << "inline constexpr float kQueryWidth = " << std::setprecision(9)
              << width << "f;\n";
    std::cout << "inline constexpr int32_t kQueryCodeSum = "
              << query_code_sum << ";\n\n";
    printArray("kQueryCodes", query_codes, "uint8_t");
    printArray("kResidualPositive", binary_flat, "uint8_t");
    printArray("kTriple", triple, "float");
    printArray("kFactorDq", factor_dq, "float");
    printArray("kFactorVq", factor_vq, "float");
    printArray("kSignedDot", signed_dot, "float");
    std::cout << "inline constexpr float kCurrentDistance = "
              << std::setprecision(9) << current_distance << "f;\n\n";
    printArray("kEstimatedDistance", estimated_distance, "float");
    printArray("kOrder", order, "size_t");
    std::cout << "} // namespace " << output_namespace << "\n";
    return 0;
}

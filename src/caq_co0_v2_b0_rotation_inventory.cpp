#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "defines.hpp"

namespace {

using saqlib::FloatRowMat;

struct DatasetRotationSpec {
    std::string_view dataset_id;
    std::vector<size_t> segment_dimensions;
    size_t whole_dimension;
};

[[noreturn]] void fail(const std::string &message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string &message) {
    if (!condition) {
        fail(message);
    }
}

FloatRowMat production_rotation(size_t dimension) {
    FloatRowMat random(FloatRowMat::Random(dimension, dimension));
    Eigen::HouseholderQR<FloatRowMat> qr(random);
    FloatRowMat q = qr.householderQ();
    FloatRowMat rotation = q.transpose();
    require(rotation.allFinite(), "rotation contains a non-finite value");
    return rotation;
}

void write_rotation(const std::filesystem::path &path, const FloatRowMat &rotation) {
    require(rotation.rows() == rotation.cols(), "rotation matrix is not square");
    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) {
        fail("cannot open rotation output: " + path.string());
    }
    for (Eigen::Index row = 0; row < rotation.rows(); ++row) {
        for (Eigen::Index column = 0; column < rotation.cols(); ++column) {
            const float value = rotation(row, column);
            output.write(reinterpret_cast<const char *>(&value), sizeof(value));
        }
    }
    if (!output) {
        fail("failed to write rotation output: " + path.string());
    }
}

std::filesystem::path segmented_path(
    const std::filesystem::path &root,
    std::string_view dataset_id,
    int logical_seed,
    size_t segment,
    size_t dimension)
{
    return root / std::string(dataset_id) /
        ("logical_seed_" + std::to_string(logical_seed)) /
        ("segmented_s" + std::to_string(segment) + "_d" +
         std::to_string(dimension) + ".f32");
}

std::filesystem::path whole_path(
    const std::filesystem::path &root,
    std::string_view dataset_id,
    int logical_seed,
    size_t dimension)
{
    return root / std::string(dataset_id) /
        ("logical_seed_" + std::to_string(logical_seed)) /
        ("whole_d" + std::to_string(dimension) + ".f32");
}

size_t generate_dataset(
    const std::filesystem::path &root,
    const DatasetRotationSpec &dataset)
{
    size_t matrices = 0;
    for (int logical_seed = 0; logical_seed < 3; ++logical_seed) {
        const unsigned int c_rng_seed = static_cast<unsigned int>(logical_seed) + 1U;
        std::srand(c_rng_seed);
        for (size_t segment = 0; segment < dataset.segment_dimensions.size(); ++segment) {
            const size_t dimension = dataset.segment_dimensions[segment];
            write_rotation(
                segmented_path(root, dataset.dataset_id, logical_seed, segment, dimension),
                production_rotation(dimension));
            ++matrices;
        }

        std::srand(c_rng_seed);
        write_rotation(
            whole_path(root, dataset.dataset_id, logical_seed, dataset.whole_dimension),
            production_rotation(dataset.whole_dimension));
        ++matrices;
    }
    return matrices;
}

} // namespace

int main(int argc, char **argv) {
    try {
        static_assert(sizeof(float) == 4);
        static_assert(std::numeric_limits<float>::is_iec559);
        require(argc == 2, "usage: caq_co0_v2_b0_rotation_inventory OUTPUT_DIR");
        const std::filesystem::path output_root(argv[1]);
        require(!output_root.empty(), "rotation output directory is empty");

        const std::vector<DatasetRotationSpec> datasets{
            {"gist_sample50k_k512", {64, 192, 320, 256}, 832},
            {"cifar60k_k512", {64, 192, 128}, 384},
        };

        size_t matrices = 0;
        for (const DatasetRotationSpec &dataset : datasets) {
            matrices += generate_dataset(output_root, dataset);
        }
        require(matrices == 27, "unexpected rotation matrix count");

        std::cout << "{\n"
                  << "  \"schema_version\": 1,\n"
                  << "  \"stage\": \"V2-B0\",\n"
                  << "  \"status\": \"PASS\",\n"
                  << "  \"logical_seeds\": [0, 1, 2],\n"
                  << "  \"c_rng_seeds\": [1, 2, 3],\n"
                  << "  \"matrix_count\": " << matrices << "\n"
                  << "}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cout << "{\n"
                  << "  \"schema_version\": 1,\n"
                  << "  \"stage\": \"V2-B0\",\n"
                  << "  \"status\": \"FAIL\"\n"
                  << "}\n";
        std::cerr << "V2-B0 rotation generation failed: " << error.what() << '\n';
        return 1;
    }
}

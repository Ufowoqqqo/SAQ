#include "index/ivf.hpp"
#include "core.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>

namespace {

using saqlib::FloatRowMat;
using saqlib::FloatVec;
using saqlib::IVF;
using saqlib::PID;
using saqlib::QuantizeConfig;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

std::vector<std::uint8_t> read_bytes(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(input.is_open(), "open round-trip file");
    input.seekg(0, std::ios::end);
    const auto size = input.tellg();
    require(size >= 0, "round-trip file size");
    input.seekg(0);
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
    input.read(reinterpret_cast<char*>(bytes.data()),
               static_cast<std::streamsize>(size));
    require(input.good(), "read round-trip file");
    return bytes;
}

void test_multicluster_round_trip() {
    constexpr std::size_t dimensions = 64;
    constexpr std::size_t clusters = 3;
    constexpr std::size_t rows = 9;

    FloatRowMat data(rows, dimensions);
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t dimension = 0; dimension < dimensions; ++dimension) {
            data(row, dimension) = static_cast<float>(
                    0.01 * static_cast<double>(row + 1) +
                    0.0001 * static_cast<double>(dimension));
        }
    }
    FloatRowMat centroids(clusters, dimensions);
    centroids.row(0) = data.row(0);
    centroids.row(1) = data.row(2);
    centroids.row(2) = data.row(5);
    const std::vector<PID> assignments{0, 0, 1, 1, 1, 2, 2, 2, 2};

    QuantizeConfig config;
    config.avg_bits = 2;
    config.enable_segmentation = false;
    config.single.random_rotation = false;
    config.single.caq_adj_rd_lmt = 6;

    IVF original(rows, dimensions, clusters, config);
    original.construct(data, centroids, assignments.data(), 1, false);

    const auto base = std::filesystem::temp_directory_path() /
            ("saq_component_loader_" + std::to_string(::getpid()));
    const auto first = base.string() + ".index";
    const auto second = base.string() + ".roundtrip.index";
    original.save(first.c_str());

    IVF loaded;
    loaded.load(first.c_str());
    require(loaded.num_data() == rows, "loaded row count");
    require(loaded.num_dim() == dimensions, "loaded dimensions");
    require(loaded.k() == clusters, "loaded cluster count");
    require(loaded.get_pclusters().size() == clusters,
            "loaded cluster vector size");
    constexpr std::size_t expected_sizes[]{2, 3, 4};
    for (std::size_t cluster = 0; cluster < clusters; ++cluster) {
        const auto& before = original.get_pclusters()[cluster];
        const auto& after = loaded.get_pclusters()[cluster];
        require(after.num_vec_ == expected_sizes[cluster],
                "loaded unequal cluster size");
        require(before.num_segments_ == after.num_segments_,
                "loaded segment count");
        for (std::size_t index = 0; index < after.num_vec_; ++index) {
            require(before.ids()[index] == after.ids()[index],
                    "loaded IDs");
            const auto& before_segment = before.get_segment(0);
            const auto& after_segment = after.get_segment(0);
            require(before_segment.long_factor(index).rescale ==
                            after_segment.long_factor(index).rescale,
                    "loaded rescale");
            const float before_error = before_segment.long_factor(index).error;
            const float after_error = after_segment.long_factor(index).error;
            require(before_error == after_error ||
                            (std::isnan(before_error) &&
                             std::isnan(after_error)),
                    "loaded error factor");
            const std::size_t long_bytes = dimensions * (2 - 1) / 8;
            for (std::size_t byte = 0; byte < long_bytes; ++byte) {
                require(before_segment.long_code(index)[byte] ==
                                after_segment.long_code(index)[byte],
                        "loaded long code");
            }
        }
        require((before.get_segment(0).centroid() -
                 after.get_segment(0).centroid()).cwiseAbs().maxCoeff() == 0,
                "loaded centroid");
    }

    loaded.save(second.c_str());
    require(read_bytes(first) == read_bytes(second),
            "index load/save is not byte-identical");
    std::filesystem::remove(first);
    std::filesystem::remove(second);
}

void test_least_squares_scale() {
    FloatVec residual(4);
    residual << 2.0f, -1.0f, 0.5f, 3.0f;
    FloatVec direction(4);
    direction << 1.0f, -1.0f, 1.0f, 1.0f;
    const double scale = saq_component_oracle::least_squares_scale(
            {residual.data(), 4}, {direction.data(), 4});
    const double baseline = residual.cast<double>().squaredNorm();
    const double fitted = (residual.cast<double>() -
                           scale * direction.cast<double>()).squaredNorm();
    require(std::isfinite(scale) && fitted <= baseline,
            "least-squares scale did not reduce residual SSE");
}

void test_deterministic_ranking_helpers() {
    using namespace saq_component_oracle;
    require(splitmix64(2026080304ULL ^ 7) ==
                    splitmix64(2026080304ULL ^ 7),
            "splitmix64 is not deterministic");
    require(splitmix64(2026080304ULL ^ 7) !=
                    splitmix64(2026080304ULL ^ 8),
            "splitmix64 failed seed separation");
    require(rank_before(1.0, 3, 1.0, 4), "ID tie order");
    require(!exact_tie(1.0, 1.01), "wide exact tie");
    require(is_inversion(1.0, 2.0, 2.0, 1.0, 3, 4),
            "inversion detection");
}

}  // namespace

int main() {
    try {
        test_multicluster_round_trip();
        test_least_squares_scale();
        test_deterministic_ranking_helpers();
        std::cout << "saq_component_oracle_test: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "saq_component_oracle_test: " << error.what() << '\n';
        return 1;
    }
}

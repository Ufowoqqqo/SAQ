#include "core.hpp"

#include "index/ivf.hpp"
#include "quantization/fastscan/lut.hpp"
#include "quantization/saq_estimator.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <tuple>
#include <utility>
#include <vector>

namespace {

using saq_component_oracle::exact_tie;
using saq_component_oracle::is_inversion;
using saq_component_oracle::least_squares_scale;
using saq_component_oracle::rank_before;
using saq_component_oracle::splitmix64;
using saqlib::DistType;
using saqlib::FloatVec;
using saqlib::IVF;
using saqlib::PID;
using saqlib::SaqCluEstimator;
using saqlib::SearcherConfig;

constexpr std::size_t kRows = 50000;
constexpr std::size_t kDimensions = 960;
constexpr std::size_t kSegments = 5;
constexpr std::size_t kProbes = 256;
constexpr std::size_t kParityProbes = 32;
constexpr std::size_t kPool = 4096;
constexpr std::size_t kLocal = 64;
constexpr std::uint64_t kSeed = 2026080304ULL;
constexpr std::array<std::size_t, kSegments> kSegmentDimensions{
        64, 192, 320, 256, 128};
constexpr std::array<std::size_t, kSegments> kSegmentBits{
        11, 6, 4, 2, 0};

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

struct Dataset {
    std::size_t rows = 0;
    std::size_t dimensions = 0;
    std::vector<float> values;

    std::span<const float> row(std::size_t index) const {
        return {values.data() + index * dimensions, dimensions};
    }
};

Dataset read_fvecs(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(input.is_open(), "open base fvecs");
    input.seekg(0, std::ios::end);
    const auto bytes = input.tellg();
    require(bytes > 0, "base fvecs size");
    input.seekg(0);
    std::int32_t dimensions = 0;
    input.read(reinterpret_cast<char*>(&dimensions), sizeof(dimensions));
    require(input.good() && dimensions > 0, "base fvecs dimensions");
    const std::size_t row_bytes = sizeof(std::int32_t) +
            static_cast<std::size_t>(dimensions) * sizeof(float);
    require(static_cast<std::size_t>(bytes) % row_bytes == 0,
            "base fvecs row boundary");
    Dataset dataset;
    dataset.rows = static_cast<std::size_t>(bytes) / row_bytes;
    dataset.dimensions = static_cast<std::size_t>(dimensions);
    dataset.values.resize(dataset.rows * dataset.dimensions);
    input.seekg(0);
    for (std::size_t row = 0; row < dataset.rows; ++row) {
        std::int32_t current_dimensions = 0;
        input.read(reinterpret_cast<char*>(&current_dimensions),
                   sizeof(current_dimensions));
        require(current_dimensions == dimensions, "ragged base fvecs");
        input.read(reinterpret_cast<char*>(
                           dataset.values.data() + row * dataset.dimensions),
                   static_cast<std::streamsize>(
                           dataset.dimensions * sizeof(float)));
        require(input.good(), "read base fvecs row");
    }
    return dataset;
}

double exact_distance(
        std::span<const float> left, std::span<const float> right,
        std::size_t begin = 0, std::size_t length = kDimensions) {
    double distance = 0;
    for (std::size_t dimension = begin;
         dimension < begin + length; ++dimension) {
        const double difference = static_cast<double>(left[dimension]) -
                right[dimension];
        distance += difference * difference;
    }
    return distance;
}

struct Location {
    std::uint32_t cluster = std::numeric_limits<std::uint32_t>::max();
    std::uint32_t position = std::numeric_limits<std::uint32_t>::max();
};

struct Population {
    std::vector<PID> probes;
    std::vector<PID> pool;
};

Population make_population() {
    std::vector<PID> ids(kRows);
    std::iota(ids.begin(), ids.end(), 0);
    std::sort(ids.begin(), ids.end(), [](PID left, PID right) {
        const auto left_hash = splitmix64(kSeed ^ left);
        const auto right_hash = splitmix64(kSeed ^ right);
        return left_hash != right_hash ? left_hash < right_hash : left < right;
    });
    Population population;
    population.probes.assign(ids.begin(), ids.begin() + kProbes);
    population.pool.assign(
            ids.begin() + kProbes, ids.begin() + kProbes + kPool);
    return population;
}

std::vector<Location> validate_index(const IVF& index) {
    require(index.num_data() == kRows, "natural index row count");
    require(index.num_dim() == kDimensions, "natural index dimensions");
    require(index.k() == 512, "natural index cluster count");
    const auto* saq_data = index.get_saq_data();
    require(saq_data != nullptr, "natural SAQ data");
    require(saq_data->quant_plan.size() == kSegments,
            "natural segment count");
    for (std::size_t segment = 0; segment < kSegments; ++segment) {
        require(saq_data->quant_plan[segment].first ==
                        kSegmentDimensions[segment] &&
                        saq_data->quant_plan[segment].second ==
                        kSegmentBits[segment],
                "natural segment plan");
    }
    std::vector<Location> locations(kRows);
    std::vector<bool> seen(kRows, false);
    const auto& clusters = index.get_pclusters();
    require(clusters.size() == index.k(), "natural cluster vector size");
    for (std::size_t cluster = 0; cluster < clusters.size(); ++cluster) {
        for (std::size_t position = 0;
             position < clusters[cluster].num_vec_; ++position) {
            const PID id = clusters[cluster].ids()[position];
            require(id < kRows && !seen[id], "natural unique ID coverage");
            seen[id] = true;
            locations[id] = {static_cast<std::uint32_t>(cluster),
                             static_cast<std::uint32_t>(position)};
        }
    }
    require(std::all_of(seen.begin(), seen.end(), [](bool value) {
                return value;
            }), "natural complete ID coverage");
    return locations;
}

struct Reconstructions {
    std::array<std::vector<float>, kSegments> production;
    std::array<std::vector<float>, kSegments> least_squares;
    std::array<std::vector<double>, kSegments> residual_norm2;
    double max_stored_rescale_relative_error = 0;
    double max_stored_norm_relative_error = 0;
};

FloatVec map_segment(
        std::span<const float> row, std::size_t offset,
        std::size_t dimensions) {
    return Eigen::Map<const FloatVec>(row.data() + offset, dimensions);
}

struct PackedBit {
    std::size_t byte = 0;
    std::uint8_t mask = 0;
};

std::vector<PackedBit> build_compacted_bit_map(
        std::size_t dimensions, std::size_t bits) {
    std::vector<PackedBit> mapping(dimensions * bits);
    if (bits == 0) return mapping;
    const auto compact = saqlib::utils::get_compacted_code16_func(bits);
    std::vector<std::uint16_t> raw(dimensions, 0);
    std::vector<std::uint8_t> packed(dimensions * bits / 8, 0);
    for (std::size_t dimension = 0; dimension < dimensions; ++dimension) {
        for (std::size_t bit = 0; bit < bits; ++bit) {
            raw[dimension] = static_cast<std::uint16_t>(1U << bit);
            std::fill(packed.begin(), packed.end(), 0);
            compact(packed.data(), raw.data(), dimensions);
            std::size_t found = 0;
            for (std::size_t byte = 0; byte < packed.size(); ++byte) {
                for (std::size_t packed_bit = 0; packed_bit < 8; ++packed_bit) {
                    const std::uint8_t mask = static_cast<std::uint8_t>(
                            1U << packed_bit);
                    if ((packed[byte] & mask) != 0) {
                        mapping[dimension * bits + bit] = {byte, mask};
                        ++found;
                    }
                }
            }
            require(found == 1, "compacted code is not a bit permutation");
            raw[dimension] = 0;
        }
    }
    return mapping;
}

std::uint16_t decode_low_code(
        const std::uint8_t* packed, std::size_t dimension,
        std::size_t bits, const std::vector<PackedBit>& mapping) {
    std::uint16_t code = 0;
    for (std::size_t bit = 0; bit < bits; ++bit) {
        const auto location = mapping[dimension * bits + bit];
        if ((packed[location.byte] & location.mask) != 0)
            code |= static_cast<std::uint16_t>(1U << bit);
    }
    return code;
}

bool decode_fastscan_msb(
        const saqlib::CAQClusterData& segment, std::size_t position,
        std::size_t dimension) {
    const std::uint8_t* block = segment.short_code(
            position / saqlib::KFastScanSize);
    const std::size_t within_block = position % saqlib::KFastScanSize;
    const std::size_t within_half = within_block % 16;
    const std::size_t packed_position = within_half < 8
            ? 2 * within_half : 2 * (within_half - 8) + 1;
    const unsigned shift = within_block < 16 ? 0 : 4;
    const std::size_t byte_column = dimension / 8;
    const std::uint8_t upper = static_cast<std::uint8_t>(
            (block[byte_column * 32 + packed_position] >> shift) & 0x0f);
    const std::uint8_t lower = static_cast<std::uint8_t>(
            (block[byte_column * 32 + packed_position + 16] >> shift) & 0x0f);
    const std::uint8_t original = static_cast<std::uint8_t>(
            (upper << 4) | lower);
    return (original & (0x80U >> (dimension % 8))) != 0;
}

Reconstructions prepare_reconstructions(
        const Dataset& base, const IVF& index,
        const std::vector<Location>& locations,
        const Population& population) {
    Reconstructions result;
    const auto* saq_data = index.get_saq_data();
    const auto& clusters = index.get_pclusters();
    for (std::size_t segment = 0; segment < kSegments; ++segment) {
        result.production[segment].resize(
                kPool * kSegmentDimensions[segment], 0);
        result.least_squares[segment].resize(
                kPool * kSegmentDimensions[segment], 0);
        result.residual_norm2[segment].resize(kPool, 0);
    }
    std::array<std::vector<PackedBit>, kSegments> compacted_maps;
    for (std::size_t segment = 0; segment < kSegments; ++segment) {
        const std::size_t bits = kSegmentBits[segment];
        compacted_maps[segment] = build_compacted_bit_map(
                kSegmentDimensions[segment], bits == 0 ? 0 : bits - 1);
    }

    for (std::size_t pool_index = 0; pool_index < kPool; ++pool_index) {
        const PID id = population.pool[pool_index];
        const auto location = locations[id];
        const auto& cluster = clusters[location.cluster];
        std::size_t offset = 0;
        for (std::size_t segment = 0; segment < kSegments; ++segment) {
            const auto& quantizer_data = saq_data->base_datas[segment];
            const std::size_t dimensions = kSegmentDimensions[segment];
            FloatVec rotated = map_segment(base.row(id), offset, dimensions);
            if (quantizer_data.rotator) {
                rotated = rotated * quantizer_data.rotator->get_P();
            }
            FloatVec residual = rotated -
                    cluster.get_segment(segment).centroid();
            const auto& stored_segment = cluster.get_segment(segment);
            const double stored_norm = stored_segment.factor_o_l2norm(
                    location.position / saqlib::KFastScanSize)
                    [location.position % saqlib::KFastScanSize];
            const double stored_norm2 = stored_norm * stored_norm;
            result.residual_norm2[segment][pool_index] = stored_norm2;
            const double true_norm = residual.cast<double>().norm();
            result.max_stored_norm_relative_error = std::max(
                    result.max_stored_norm_relative_error,
                    std::abs(stored_norm - true_norm) /
                            std::max(1.0, true_norm));

            if (kSegmentBits[segment] > 0) {
                const std::size_t bits = kSegmentBits[segment];
                const std::size_t low_bits = bits - 1;
                const std::uint8_t* packed = stored_segment.long_code(
                        location.position);
                FloatVec direction(dimensions);
                const double delta = 2.0 / static_cast<double>(1U << bits);
                for (std::size_t dimension = 0;
                     dimension < dimensions; ++dimension) {
                    std::uint16_t code = decode_low_code(
                            packed, dimension, low_bits,
                            compacted_maps[segment]);
                    if (decode_fastscan_msb(
                                stored_segment, location.position, dimension))
                        code |= static_cast<std::uint16_t>(1U << low_bits);
                    direction[dimension] = static_cast<float>(
                            -1.0 + (static_cast<double>(code) + 0.5) * delta);
                }
                const double stored_scale =
                        stored_segment.long_factor(location.position).rescale;
                const double code_inner_product =
                        residual.cast<double>().dot(direction.cast<double>());
                const double recomputed_scale = code_inner_product == 0
                        ? 0 : residual.cast<double>().squaredNorm() /
                                code_inner_product;
                const double ls_scale = least_squares_scale(
                        {residual.data(), dimensions},
                        {direction.data(), dimensions});
                float* production = result.production[segment].data() +
                        pool_index * dimensions;
                float* least_squares =
                        result.least_squares[segment].data() +
                        pool_index * dimensions;
                for (std::size_t dimension = 0;
                     dimension < dimensions; ++dimension) {
                    production[dimension] = static_cast<float>(
                            stored_scale * direction[dimension]);
                    least_squares[dimension] = static_cast<float>(
                            ls_scale * direction[dimension]);
                }
                result.max_stored_rescale_relative_error = std::max(
                        result.max_stored_rescale_relative_error,
                        std::abs(recomputed_scale - stored_scale) /
                                std::max(1.0, std::abs(stored_scale)));
            }
            offset += dimensions;
        }
    }
    return result;
}

std::array<FloatVec, kSegments> rotated_probe(
        const Dataset& base, const IVF& index, PID probe) {
    std::array<FloatVec, kSegments> result;
    const auto* saq_data = index.get_saq_data();
    std::size_t offset = 0;
    for (std::size_t segment = 0; segment < kSegments; ++segment) {
        result[segment] = map_segment(
                base.row(probe), offset, kSegmentDimensions[segment]);
        const auto& quantizer_data = saq_data->base_datas[segment];
        if (quantizer_data.rotator) {
            result[segment] = result[segment] *
                    quantizer_data.rotator->get_P();
        }
        offset += kSegmentDimensions[segment];
    }
    return result;
}

using Contributions = std::array<double, kSegments>;

std::vector<Contributions> stored_contributions(
        const Dataset& base, const IVF& index,
        const std::vector<Location>& locations,
        const Population& population, PID probe,
        const std::vector<std::size_t>& pool_indices) {
    SearcherConfig searcher;
    searcher.dist_type = DistType::L2Sqr;
    const auto query = Eigen::Map<const FloatVec>(
            base.row(probe).data(), kDimensions);
    SaqCluEstimator<DistType::L2Sqr> estimator(
            *index.get_saq_data(), searcher, query);
    std::vector<Contributions> output(pool_indices.size());
    std::vector<std::vector<std::pair<std::size_t, std::size_t>>> grouped(
            index.k());
    for (std::size_t output_index = 0;
         output_index < pool_indices.size(); ++output_index) {
        const std::size_t pool_index = pool_indices[output_index];
        const auto location = locations[population.pool[pool_index]];
        grouped[location.cluster].push_back({location.position, output_index});
    }
    for (std::size_t cluster = 0; cluster < grouped.size(); ++cluster) {
        auto& entries = grouped[cluster];
        if (entries.empty()) continue;
        std::sort(entries.begin(), entries.end());
        estimator.prepare(&index.get_pclusters()[cluster]);
        std::size_t current_block = std::numeric_limits<std::size_t>::max();
        for (const auto& [position, output_index] : entries) {
            const std::size_t block = position / saqlib::KFastScanSize;
            if (block != current_block) {
                __m512 ignored[2];
                estimator.compFastDist(block, ignored);
                current_block = block;
            }
            auto& segments = estimator.getEstimators();
            for (std::size_t segment = 0;
                 segment < kSegments; ++segment) {
                output[output_index][segment] =
                        segments[segment].compAccurateDist(position);
            }
        }
    }
    return output;
}

std::vector<Contributions> recomputed_stored_contributions(
        const Dataset& base, const IVF& index,
        const std::vector<Location>& locations,
        const Population& population, PID probe,
        const std::vector<std::size_t>& pool_indices) {
    const auto rotated = rotated_probe(base, index, probe);
    std::vector<Contributions> output(pool_indices.size());
    std::vector<std::vector<std::pair<std::size_t, std::size_t>>> grouped(
            index.k());
    for (std::size_t output_index = 0;
         output_index < pool_indices.size(); ++output_index) {
        const std::size_t pool_index = pool_indices[output_index];
        const auto location = locations[population.pool[pool_index]];
        grouped[location.cluster].push_back({location.position, output_index});
    }
    for (std::size_t cluster = 0; cluster < grouped.size(); ++cluster) {
        auto& entries = grouped[cluster];
        if (entries.empty()) continue;
        std::sort(entries.begin(), entries.end());
        const auto& cluster_data = index.get_pclusters()[cluster];
        for (std::size_t segment = 0; segment < kSegments; ++segment) {
            const auto& segment_data = cluster_data.get_segment(segment);
            saqlib::Lut lut(
                    kSegmentDimensions[segment],
                    kSegmentBits[segment] == 0
                            ? 0 : kSegmentBits[segment] - 1);
            lut.prepare(rotated[segment] - segment_data.centroid());
            std::size_t current_block =
                    std::numeric_limits<std::size_t>::max();
            for (const auto& [position, output_index] : entries) {
                const std::size_t block =
                        position / saqlib::KFastScanSize;
                const std::size_t within =
                        position % saqlib::KFastScanSize;
                const float norm = segment_data.factor_o_l2norm(block)[within];
                float distance = norm * norm + lut.getQL2Sqr();
                if (kSegmentBits[segment] > 0) {
                    if (block != current_block) {
                        lut.compFastIP(
                                segment_data.factor_o_l2norm(block),
                                segment_data.short_code(block), nullptr);
                        current_block = block;
                    }
                    const float inner_product =
                            segment_data.long_factor(position).rescale *
                            lut.getExtIP(
                                    segment_data.long_code(position),
                                    2.0f / static_cast<float>(
                                            1U << kSegmentBits[segment]),
                                    within);
                    distance -= 2.0f * inner_product;
                }
                output[output_index][segment] = distance;
            }
        }
    }
    return output;
}

struct ParityResult {
    double max_production_relative_error = 0;
    double max_exact_relative_error = 0;
    std::uint64_t comparisons = 0;
};

ParityResult check_parity(
        const Dataset& base, const IVF& index,
        const std::vector<Location>& locations,
        const Population& population) {
    ParityResult result;
    std::vector<std::size_t> all_pool(kPool);
    std::iota(all_pool.begin(), all_pool.end(), 0);
    for (std::size_t probe_index = 0;
         probe_index < kParityProbes; ++probe_index) {
        const PID probe = population.probes[probe_index];
        const auto stored = stored_contributions(
                base, index, locations, population, probe, all_pool);
        const auto recomputed_stored = recomputed_stored_contributions(
                base, index, locations, population, probe, all_pool);
        for (std::size_t pool_index = 0;
             pool_index < kPool; ++pool_index) {
            const PID candidate = population.pool[pool_index];
            double exact_sum = 0;
            std::size_t offset = 0;
            for (std::size_t segment = 0;
                 segment < kSegments; ++segment) {
                const std::size_t dimensions = kSegmentDimensions[segment];
                exact_sum += exact_distance(
                        base.row(probe), base.row(candidate),
                        offset, dimensions);
                result.max_production_relative_error = std::max(
                        result.max_production_relative_error,
                        std::abs(stored[pool_index][segment] -
                                 recomputed_stored[pool_index][segment]) /
                                std::max(1.0, std::abs(
                                        stored[pool_index][segment])));
                offset += dimensions;
            }
            const double raw_exact = exact_distance(
                    base.row(probe), base.row(candidate));
            result.max_exact_relative_error = std::max(
                    result.max_exact_relative_error,
                    std::abs(exact_sum - raw_exact) /
                            std::max(1.0, raw_exact));
            result.comparisons++;
        }
    }
    return result;
}

std::vector<std::size_t> local_candidates(
        const Dataset& base, const Population& population, PID probe) {
    std::vector<std::size_t> indices(kPool);
    std::vector<double> distances(kPool);
    std::iota(indices.begin(), indices.end(), 0);
    for (std::size_t index = 0; index < kPool; ++index) {
        distances[index] = exact_distance(
                base.row(probe), base.row(population.pool[index]));
    }
    std::partial_sort(
            indices.begin(), indices.begin() + kLocal, indices.end(),
            [&](std::size_t left, std::size_t right) {
                const double left_distance = distances[left];
                const double right_distance = distances[right];
                return left_distance != right_distance
                        ? left_distance < right_distance
                        : population.pool[left] < population.pool[right];
            });
    indices.resize(kLocal);
    return indices;
}

const std::vector<std::string>& arm_names() {
    static const std::vector<std::string> names{
            "PROD", "LS_ALL", "LS_SEG_0", "LS_SEG_1",
            "LS_SEG_2", "LS_SEG_3", "EXACT_SEG_0", "EXACT_SEG_1",
            "EXACT_SEG_2", "EXACT_SEG_3", "EXACT_SEG_4", "EXACT_ALL"};
    return names;
}

std::vector<double> arm_distances(
        const Contributions& production,
        const Contributions& least_squares,
        const Contributions& exact) {
    const double production_sum = std::accumulate(
            production.begin(), production.end(), 0.0);
    const double exact_sum = std::accumulate(exact.begin(), exact.end(), 0.0);
    double ls_all = production[4];
    for (std::size_t segment = 0; segment < 4; ++segment)
        ls_all += least_squares[segment];
    std::vector<double> output{production_sum, ls_all};
    for (std::size_t segment = 0; segment < 4; ++segment)
        output.push_back(production_sum - production[segment] +
                         least_squares[segment]);
    for (std::size_t segment = 0; segment < kSegments; ++segment)
        output.push_back(production_sum - production[segment] +
                         exact[segment]);
    output.push_back(exact_sum);
    require(output.size() == arm_names().size(), "arm distance count");
    return output;
}

struct Aggregate {
    std::uint64_t pairs = 0;
    std::uint64_t inversions = 0;
    std::uint64_t repaired = 0;
    std::uint64_t newly_inverted = 0;
    double top10_sum = 0;
    std::uint64_t probes = 0;
    std::vector<double> relative_errors;
};

double quantile(std::vector<double> values, double probability) {
    if (values.empty()) return 0;
    std::sort(values.begin(), values.end());
    const std::size_t index = static_cast<std::size_t>(
            probability * static_cast<double>(values.size() - 1));
    return values[index];
}

struct ExperimentResult {
    std::array<std::vector<Aggregate>, 3> aggregates;
};

ExperimentResult run_experiment(
        const Dataset& base, const IVF& index,
        const std::vector<Location>& locations,
        const Population& population,
        const Reconstructions& reconstructions,
        const std::filesystem::path& output_dir) {
    ExperimentResult result;
    for (auto& fold : result.aggregates)
        fold.resize(arm_names().size());
    std::ofstream per_probe(output_dir / "per_probe.tsv");
    per_probe << "fold\tprobe_id\tarm\tpairs\tinversions"
                 "\trepaired\tnewly_inverted\ttop10_agreement\n";

    for (std::size_t probe_index = 0;
         probe_index < kProbes; ++probe_index) {
        const std::size_t fold = probe_index < kProbes / 2 ? 0 : 1;
        const PID probe = population.probes[probe_index];
        const auto selected = local_candidates(base, population, probe);
        const auto stored = stored_contributions(
                base, index, locations, population, probe, selected);
        const auto rotated = rotated_probe(base, index, probe);
        std::vector<PID> candidate_ids(kLocal);
        std::vector<std::vector<double>> distances(
                arm_names().size(), std::vector<double>(kLocal));
        for (std::size_t local = 0; local < kLocal; ++local) {
            const std::size_t pool_index = selected[local];
            const PID candidate = population.pool[pool_index];
            candidate_ids[local] = candidate;
            const auto location = locations[candidate];
            Contributions exact{};
            Contributions least_squares{};
            std::size_t offset = 0;
            for (std::size_t segment = 0;
                 segment < kSegments; ++segment) {
                const std::size_t dimensions = kSegmentDimensions[segment];
                exact[segment] = exact_distance(
                        base.row(probe), base.row(candidate),
                        offset, dimensions);
                if (segment < 4) {
                    FloatVec query_residual = rotated[segment] -
                            index.get_pclusters()[location.cluster]
                                    .get_segment(segment).centroid();
                    const float* reconstruction =
                            reconstructions.least_squares[segment].data() +
                            pool_index * dimensions;
                    least_squares[segment] =
                            query_residual.cast<double>().squaredNorm() +
                            reconstructions.residual_norm2[segment][pool_index] -
                            2 * query_residual.cast<double>().dot(
                                    Eigen::Map<const FloatVec>(
                                            reconstruction,
                                            dimensions).cast<double>());
                } else {
                    least_squares[segment] = stored[local][segment];
                }
                offset += dimensions;
            }
            const auto arms = arm_distances(
                    stored[local], least_squares, exact);
            for (std::size_t arm = 0; arm < arms.size(); ++arm)
                distances[arm][local] = arms[arm];
        }

        std::vector<std::size_t> exact_order(kLocal);
        std::iota(exact_order.begin(), exact_order.end(), 0);
        std::sort(exact_order.begin(), exact_order.end(),
                  [&](std::size_t left, std::size_t right) {
            return rank_before(
                    distances.back()[left], candidate_ids[left],
                    distances.back()[right], candidate_ids[right]);
        });
        std::vector<bool> exact_top10(kLocal, false);
        for (std::size_t index = 0; index < 10; ++index)
            exact_top10[exact_order[index]] = true;

        std::vector<std::uint64_t> local_pairs(arm_names().size(), 0);
        std::vector<std::uint64_t> local_inversions(arm_names().size(), 0);
        std::vector<std::uint64_t> local_repaired(arm_names().size(), 0);
        std::vector<std::uint64_t> local_new(arm_names().size(), 0);
        for (std::size_t left = 0; left < kLocal; ++left) {
            for (std::size_t right = left + 1; right < kLocal; ++right) {
                if (exact_tie(
                            distances.back()[left],
                            distances.back()[right])) continue;
                const bool production_inversion = is_inversion(
                        distances.back()[left], distances.back()[right],
                        distances[0][left], distances[0][right],
                        candidate_ids[left], candidate_ids[right]);
                for (std::size_t arm = 0;
                     arm < arm_names().size(); ++arm) {
                    const bool inversion = is_inversion(
                            distances.back()[left], distances.back()[right],
                            distances[arm][left], distances[arm][right],
                            candidate_ids[left], candidate_ids[right]);
                    local_pairs[arm]++;
                    local_inversions[arm] += inversion;
                    local_repaired[arm] += production_inversion && !inversion;
                    local_new[arm] += !production_inversion && inversion;
                }
            }
        }

        for (std::size_t arm = 0; arm < arm_names().size(); ++arm) {
            std::vector<std::size_t> order(kLocal);
            std::iota(order.begin(), order.end(), 0);
            std::sort(order.begin(), order.end(),
                      [&](std::size_t left, std::size_t right) {
                return rank_before(
                        distances[arm][left], candidate_ids[left],
                        distances[arm][right], candidate_ids[right]);
            });
            std::size_t top10 = 0;
            for (std::size_t index = 0; index < 10; ++index)
                top10 += exact_top10[order[index]];
            const double top10_agreement = static_cast<double>(top10) / 10;
            per_probe << fold << '\t' << probe << '\t' << arm_names()[arm]
                      << '\t' << local_pairs[arm] << '\t'
                      << local_inversions[arm] << '\t'
                      << local_repaired[arm] << '\t' << local_new[arm]
                      << '\t' << top10_agreement << '\n';
            for (const std::size_t aggregate_index : {fold, std::size_t{2}}) {
                auto& aggregate = result.aggregates[aggregate_index][arm];
                aggregate.pairs += local_pairs[arm];
                aggregate.inversions += local_inversions[arm];
                aggregate.repaired += local_repaired[arm];
                aggregate.newly_inverted += local_new[arm];
                aggregate.top10_sum += top10_agreement;
                aggregate.probes++;
                for (std::size_t local = 0; local < kLocal; ++local) {
                    aggregate.relative_errors.push_back(
                            std::abs(distances[arm][local] -
                                     distances.back()[local]) /
                            std::max(1e-12, distances.back()[local]));
                }
            }
        }
    }
    require(per_probe.good(), "write per-probe output");
    return result;
}

void write_population(
        const std::filesystem::path& output_dir,
        const Population& population) {
    std::ofstream output(output_dir / "population.tsv");
    output << "role\tposition\tid\thash\n";
    for (std::size_t index = 0; index < population.probes.size(); ++index)
        output << "probe\t" << index << '\t' << population.probes[index]
               << '\t' << splitmix64(kSeed ^ population.probes[index]) << '\n';
    for (std::size_t index = 0; index < population.pool.size(); ++index)
        output << "candidate\t" << index << '\t' << population.pool[index]
               << '\t' << splitmix64(kSeed ^ population.pool[index]) << '\n';
    require(output.good(), "write population output");
}

void write_parity(
        const std::filesystem::path& output_dir,
        const ParityResult& parity,
        const Reconstructions& reconstructions) {
    std::ofstream output(output_dir / "parity.tsv");
    output << "metric\tvalue\tlimit\tpass\n" << std::setprecision(17);
    const auto row = [&](const char* name, double value, double limit) {
        output << name << '\t' << value << '\t' << limit << '\t'
               << (value <= limit ? 1 : 0) << '\n';
    };
    row("stored_production_relative_error",
        parity.max_production_relative_error, 1e-5);
    row("exact_segment_sum_relative_error",
        parity.max_exact_relative_error, 1e-9);
    row("stored_rescale_relative_error",
        reconstructions.max_stored_rescale_relative_error, 1e-5);
    row("stored_norm_relative_error",
        reconstructions.max_stored_norm_relative_error, 1e-5);
    output << "parity_comparisons\t" << parity.comparisons
           << "\t" << parity.comparisons << "\t1\n";
    require(output.good(), "write parity output");
}

void require_parity(
        const ParityResult& parity,
        const Reconstructions& reconstructions) {
    require(parity.max_production_relative_error <= 1e-5,
            "stored/recomputed production parity");
    require(parity.max_exact_relative_error <= 1e-9,
            "exact segment/full parity");
    require(reconstructions.max_stored_rescale_relative_error <= 1e-5,
            "stored/recomputed rescale parity");
    require(reconstructions.max_stored_norm_relative_error <= 1e-5,
            "stored/recomputed norm parity");
}

void write_summary(
        const std::filesystem::path& output_dir,
        const ExperimentResult& result) {
    std::ofstream output(output_dir / "summary.tsv");
    output << "fold\tarm\tpairs\tinversions\tinversion_rate"
              "\tabsolute_reduction\trepair_fraction\tnew_inversion_fraction"
              "\ttop10_agreement\tmedian_relative_error"
              "\tp95_relative_error\n" << std::setprecision(17);
    for (std::size_t fold = 0; fold < result.aggregates.size(); ++fold) {
        const auto& production = result.aggregates[fold][0];
        const double production_rate = production.pairs == 0 ? 0 :
                static_cast<double>(production.inversions) / production.pairs;
        for (std::size_t arm = 0; arm < arm_names().size(); ++arm) {
            const auto& aggregate = result.aggregates[fold][arm];
            const double rate = aggregate.pairs == 0 ? 0 :
                    static_cast<double>(aggregate.inversions) /
                    aggregate.pairs;
            const double repair = production.inversions == 0 ? 0 :
                    static_cast<double>(aggregate.repaired) /
                    production.inversions;
            const double newly =
                    production.pairs == production.inversions ? 0 :
                    static_cast<double>(aggregate.newly_inverted) /
                    (production.pairs - production.inversions);
            output << (fold == 2 ? "combined" : std::to_string(fold))
                   << '\t' << arm_names()[arm] << '\t' << aggregate.pairs
                   << '\t' << aggregate.inversions << '\t' << rate << '\t'
                   << production_rate - rate << '\t' << repair << '\t'
                   << newly << '\t'
                   << aggregate.top10_sum / aggregate.probes << '\t'
                   << quantile(aggregate.relative_errors, 0.5) << '\t'
                   << quantile(aggregate.relative_errors, 0.95) << '\n';
        }
    }
    require(output.good(), "write summary output");
}

void write_decision(
        const std::filesystem::path& output_dir,
        const ExperimentResult& result) {
    std::ofstream output(output_dir / "decision.txt");
    const auto rate = [&](std::size_t fold, std::size_t arm) {
        const auto& aggregate = result.aggregates[fold][arm];
        return aggregate.pairs == 0 ? 0.0 :
                static_cast<double>(aggregate.inversions) / aggregate.pairs;
    };
    const bool low_headroom = rate(0, 0) < 0.002 && rate(1, 0) < 0.002;
    output << std::setprecision(17)
           << "production_fold0_inversion_rate=" << rate(0, 0) << '\n'
           << "production_fold1_inversion_rate=" << rate(1, 0) << '\n';
    if (low_headroom) {
        output << "decision=CLOSE_LOW_HEADROOM\n";
        return;
    }
    std::vector<std::string> actionable;
    for (std::size_t arm = 1; arm + 1 < arm_names().size(); ++arm) {
        bool passes = true;
        for (std::size_t fold = 0; fold < 2; ++fold) {
            const auto& production = result.aggregates[fold][0];
            const auto& candidate = result.aggregates[fold][arm];
            const double reduction = rate(fold, 0) - rate(fold, arm);
            const double repair = production.inversions == 0 ? 0 :
                    static_cast<double>(candidate.repaired) /
                    production.inversions;
            passes = passes && reduction >= 0.002 && repair >= 0.20;
        }
        if (passes) actionable.push_back(arm_names()[arm]);
    }
    if (actionable.empty()) {
        output << "decision=CLOSE_NO_ACTIONABLE_COMPONENT\n";
    } else {
        output << "decision=ACTIONABLE_COMPONENT\n";
        for (const auto& arm : actionable)
            output << "actionable=" << arm << '\n';
    }
}

double process_cpu_seconds() {
    timespec value{};
    require(clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) == 0,
            "process CPU clock");
    return static_cast<double>(value.tv_sec) +
            static_cast<double>(value.tv_nsec) * 1e-9;
}

std::uint64_t peak_rss_bytes() {
    rusage usage{};
    require(getrusage(RUSAGE_SELF, &usage) == 0, "peak RSS");
    return static_cast<std::uint64_t>(usage.ru_maxrss) * 1024;
}

void run(
        const std::filesystem::path& base_path,
        const std::filesystem::path& index_path,
        const std::filesystem::path& output_dir,
        const std::string& mode) {
    require(mode == "parity-v1" || mode == "frozen-v1", "frozen mode");
    std::filesystem::create_directories(output_dir);
    const double cpu_start = process_cpu_seconds();
    const auto wall_start = std::chrono::steady_clock::now();

    const Dataset base = read_fvecs(base_path);
    require(base.rows == kRows && base.dimensions == kDimensions,
            "frozen base shape");
    IVF index;
    index.load(index_path.c_str());
    const auto locations = validate_index(index);
    const auto population = make_population();
    require(population.probes.size() == kProbes &&
                    population.pool.size() == kPool,
            "frozen population sizes");
    std::vector<bool> selected(kRows, false);
    for (const PID id : population.probes) selected[id] = true;
    for (const PID id : population.pool) {
        require(!selected[id], "probe/pool overlap");
        selected[id] = true;
    }
    write_population(output_dir, population);

    const auto reconstructions = prepare_reconstructions(
            base, index, locations, population);
    const auto parity = check_parity(
            base, index, locations, population);
    write_parity(output_dir, parity, reconstructions);
    require_parity(parity, reconstructions);

    if (mode == "frozen-v1") {
        const auto experiment = run_experiment(
                base, index, locations, population,
                reconstructions, output_dir);
        write_summary(output_dir, experiment);
        write_decision(output_dir, experiment);
    }

    const double cpu_seconds = process_cpu_seconds() - cpu_start;
    const double wall_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - wall_start).count();
    std::ofstream resources(output_dir / "resources.tsv");
    resources << "mode\tcpu_seconds\twall_seconds\tpeak_rss_bytes\n"
              << mode << '\t' << std::setprecision(17) << cpu_seconds << '\t'
              << wall_seconds << '\t' << peak_rss_bytes() << '\n';
    require(resources.good(), "write resources output");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 5)
            throw std::invalid_argument(
                    "usage: saq_component_oracle <base.fvecs> <index> "
                    "<output-dir> <parity-v1|frozen-v1>");
        run(argv[1], argv[2], argv[3], argv[4]);
        std::cout << "saq_component_oracle: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "saq_component_oracle: " << error.what() << '\n';
        return 1;
    }
}

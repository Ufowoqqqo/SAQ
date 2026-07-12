#include <algorithm>
#include <bit>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include <unistd.h>

#include "quantization/caq/co0_v2_b1_io.hpp"
#include "quantization/caq/co0_v2_measurement.hpp"
#include "quantization/quantizer.hpp"

namespace {

using saqlib::FloatVec;
using saqlib::caq_validation::co0_v2_measure_all_arms;
using saqlib::caq_validation::co0_v2_measure_pair;
using saqlib::caq_validation::co0_v2_measure_pairs;
using saqlib::caq_validation::co0_v2_pack_canonical_code;
using saqlib::caq_validation::co0_v2_pack_for_current_estimator;
using saqlib::caq_validation::co0_v2_unpack_canonical_code;
using saqlib::caq_validation::Co0V2Arm;
using saqlib::caq_validation::Co0V2EncodingMeasurement;

struct Cell {
    std::string_view dataset;
    size_t dimension;
    uint32_t total_bits;
};

enum class Profile {
    equal,
    dense,
    bounded_binary32_span,
};

struct Counters {
    uint64_t cells = 0;
    uint64_t arm_measurements = 0;
    uint64_t source_parity_checks = 0;
    uint64_t production_packer_checks = 0;
    uint64_t canonical_roundtrips = 0;
    uint64_t estimator_checks = 0;
    uint64_t estimator_reuse_checks = 0;
    uint64_t memory_checks = 0;
    uint64_t zero_checks = 0;
    uint64_t io_checks = 0;
};

[[noreturn]] void fail(const std::string &message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string &message) {
    if (!condition) {
        fail(message);
    }
}

float signed_value(float magnitude, size_t coordinate) {
    return coordinate % 2 == 0 ? magnitude : -magnitude;
}

FloatVec make_profile(size_t dimension, Profile profile) {
    require(dimension > 1, "synthetic profile requires D>1");
    FloatVec result(static_cast<Eigen::Index>(dimension));
    constexpr uint32_t lower_finite = UINT32_C(0x3a800000);
    constexpr uint32_t upper_finite = UINT32_C(0x44800000);
    for (size_t coordinate = 0; coordinate < dimension; ++coordinate) {
        float magnitude = 0;
        switch (profile) {
        case Profile::equal:
            magnitude = 1.0F;
            break;
        case Profile::dense: {
            const double rank = static_cast<double>(coordinate + 1) /
                                static_cast<double>(dimension + 1);
            magnitude = static_cast<float>(0.25 + 1.5 * rank);
            break;
        }
        case Profile::bounded_binary32_span: {
            const uint64_t numerator = static_cast<uint64_t>(coordinate) *
                                       static_cast<uint64_t>(upper_finite - lower_finite);
            const uint32_t bits = lower_finite + static_cast<uint32_t>(
                                                     numerator / static_cast<uint64_t>(dimension - 1));
            magnitude = std::bit_cast<float>(bits);
            break;
        }
        }
        result[static_cast<Eigen::Index>(coordinate)] =
            signed_value(magnitude, coordinate);
    }
    require(result.allFinite(), "synthetic profile is non-finite");
    return result;
}

std::string_view profile_name(Profile profile) {
    switch (profile) {
    case Profile::equal:
        return "equal";
    case Profile::dense:
        return "dense";
    case Profile::bounded_binary32_span:
        return "bounded_binary32_span";
    }
    fail("unknown synthetic profile");
}

FloatVec make_query(const FloatVec &stored) {
    FloatVec query(stored.cols());
    for (Eigen::Index coordinate = 0; coordinate < stored.cols(); ++coordinate) {
        const Eigen::Index source = stored.cols() - 1 - coordinate;
        const float scale = coordinate % 3 == 0 ? 0.75F : 1.125F;
        query[coordinate] = stored[source] * scale;
    }
    return query;
}

struct DirectIpReference {
    long double estimate = 0;
    long double absolute_term_sum = 0;
};

DirectIpReference direct_estimated_ip(
    const FloatVec &query,
    const Co0V2EncodingMeasurement &measurement) {
    const uint32_t levels = UINT32_C(1) << (measurement.total_bits - 1U);
    DirectIpReference result;
    for (size_t coordinate = 0; coordinate < measurement.code.size(); ++coordinate) {
        const long double decoded =
            (static_cast<long double>(measurement.code[coordinate]) + 0.5L - levels) /
            levels;
        const long double term =
            query[static_cast<Eigen::Index>(coordinate)] * decoded;
        result.estimate += term;
        result.absolute_term_sum += std::fabs(term);
    }
    result.estimate *= static_cast<long double>(measurement.fac_rescale_float32);
    result.absolute_term_sum *=
        std::fabs(static_cast<long double>(measurement.fac_rescale_float32));
    return result;
}

void validate_production_packer(
    const FloatVec &stored,
    const Co0V2EncodingMeasurement &measurement,
    Counters &counters) {
    if (measurement.arm != Co0V2Arm::lvq_init &&
        measurement.arm != Co0V2Arm::caq_r6) {
        return;
    }

    saqlib::BaseQuantizerData data;
    data.num_dim_pad = static_cast<size_t>(stored.cols());
    data.num_bits = measurement.total_bits;
    data.cfg.random_rotation = false;
    data.cfg.use_fastscan = false;
    data.cfg.caq_adj_rd_lmt = measurement.arm == Co0V2Arm::caq_r6 ? 6 : 0;
    data.cfg.caq_adj_eps = 1e-8F;

    saqlib::CaqSingleDataWrapper production(data.num_dim_pad, data.num_bits);
    saqlib::CaqSingleDataWrapper measured(data.num_dim_pad, data.num_bits);
    production.allocate_data();
    measured.allocate_data();
    saqlib::QuantizerSingle quantizer(&data);
    quantizer.quantize(stored, &production);
    co0_v2_pack_for_current_estimator(measurement, measured);

    const size_t short_bytes = data.num_dim_pad / 8;
    const size_t long_bytes = data.num_dim_pad * (data.num_bits - 1) / 8;
    require(
        std::memcmp(production.short_code(), measured.short_code(), short_bytes) == 0,
        "measurement short-code pack differs from production");
    require(
        std::memcmp(production.long_code(), measured.long_code(), long_bytes) == 0,
        "measurement long-code pack differs from production");
    require(
        std::memcmp(
            &production.long_factor(),
            &measured.long_factor(),
            sizeof(saqlib::ExFactor)) == 0,
        "measurement factors differ from production");
    ++counters.production_packer_checks;
}

void validate_memory(const Co0V2EncodingMeasurement &measurement, Counters &counters) {
    const auto &memory = measurement.memory;
    require(memory.input_vector_bytes > 0, "memory account omitted input vector");
    require(memory.result_code_bytes > 0, "memory account omitted result code");
    require(memory.canonical_packed_code_bytes > 0, "memory account omitted code shard");
    require(memory.estimator_packed_bytes > 0, "memory account omitted estimator pack");
    require(
        memory.peak_transient_bytes ==
            std::max(memory.encoding_phase_bytes, memory.packing_phase_bytes),
        "memory peak does not equal the declared phase maximum");
    if (measurement.arm == Co0V2Arm::corrected_exact && !measurement.zero_segment) {
        require(memory.oracle_component_bytes > 0, "oracle component bytes missing");
        require(memory.oracle_integer_object_bytes > 0, "oracle integer objects missing");
        require(memory.oracle_integer_limb_bytes > 0, "oracle integer limbs missing");
        require(memory.oracle_event_heap_bytes > 0, "oracle heap bytes missing");
    }
    ++counters.memory_checks;
}

void validate_cell(const Cell &cell, Profile profile, Counters &counters) {
    const FloatVec stored = make_profile(cell.dimension, profile);
    const FloatVec query = make_query(stored);
    std::vector<Co0V2EncodingMeasurement> measurements;
    try {
        measurements = co0_v2_measure_all_arms(stored, cell.total_bits);
    } catch (const std::exception &error) {
        fail(
            std::string(cell.dataset) + " D=" + std::to_string(cell.dimension) +
            " B=" + std::to_string(cell.total_bits) + " profile=" +
            std::string(profile_name(profile)) + ": " + error.what());
    }
    require(measurements.size() == 4, "unexpected arm count");

    const long double init_j = measurements[0].geometry.cosine_squared;
    const long double r6_j = measurements[1].geometry.cosine_squared;
    const long double local_j = measurements[2].geometry.cosine_squared;
    const long double exact_j = measurements[3].geometry.cosine_squared;
    constexpr long double objective_tolerance = 1e-12L;
    require(r6_j + objective_tolerance >= init_j, "r6 objective regressed from initialization");
    require(local_j + objective_tolerance >= r6_j, "local fixed point regressed from r6");
    require(exact_j + objective_tolerance >= local_j, "exact oracle is below local fixed point");
    require(measurements[2].completed_rounds >= 1, "local fixed point completed no round");
    const auto reused_pair_measurements = co0_v2_measure_pairs(stored, query, measurements);
    require(reused_pair_measurements.size() == measurements.size(), "reused estimator arm count mismatch");

    for (size_t measurement_index = 0; measurement_index < measurements.size(); ++measurement_index) {
        const Co0V2EncodingMeasurement &measurement = measurements[measurement_index];
        require(measurement.code.size() == cell.dimension, "measurement dimension mismatch");
        const std::vector<uint8_t> packed =
            co0_v2_pack_canonical_code(measurement.code, cell.total_bits);
        const std::vector<uint32_t> unpacked =
            co0_v2_unpack_canonical_code(packed, cell.dimension, cell.total_bits);
        require(unpacked == measurement.code, "canonical packed-code roundtrip failed");
        ++counters.canonical_roundtrips;

        const auto pair = co0_v2_measure_pair(stored, query, measurement);
        require(!pair.zero_norm_pair, "nonzero synthetic pair marked zero");
        require(
            pair.estimated_inner_product ==
                reused_pair_measurements[measurement_index].estimated_inner_product,
            "reused estimator changed the full-code estimate");
        ++counters.estimator_reuse_checks;
        validate_production_packer(stored, measurement, counters);
        const DirectIpReference reference = direct_estimated_ip(query, measurement);
        const long double absolute_difference =
            std::fabs(static_cast<long double>(pair.estimated_inner_product) -
                      reference.estimate);
        const long double epsilon = std::numeric_limits<float>::epsilon();
        const long double operations = static_cast<long double>(
            cell.dimension * (cell.total_bits + 2U) + 32U);
        const long double gamma = operations * epsilon / (1 - operations * epsilon);
        const long double numerical_bound =
            4 * gamma * std::max<long double>(1, reference.absolute_term_sum);
        if (absolute_difference > numerical_bound) {
            fail(
                std::string(cell.dataset) + " D=" + std::to_string(cell.dimension) +
                " B=" + std::to_string(cell.total_bits) + " profile=" +
                std::string(profile_name(profile)) + " arm=" +
                std::string(saqlib::caq_validation::co0_v2_arm_name(measurement.arm)) +
                " estimator=" + std::to_string(pair.estimated_inner_product) +
                " direct=" + std::to_string(static_cast<double>(reference.estimate)) +
                " abs_diff=" + std::to_string(static_cast<double>(absolute_difference)) +
                " numerical_bound=" + std::to_string(static_cast<double>(numerical_bound)));
        }
        ++counters.estimator_checks;
        validate_memory(measurement, counters);
        ++counters.arm_measurements;
    }

    counters.source_parity_checks += 2;
    ++counters.cells;
}

void validate_zero_case(Counters &counters) {
    FloatVec zero = FloatVec::Zero(64);
    const std::vector<Co0V2EncodingMeasurement> measurements =
        co0_v2_measure_all_arms(zero, 4);
    require(measurements.size() == 4, "zero fixture arm count mismatch");
    for (const Co0V2EncodingMeasurement &measurement : measurements) {
        require(measurement.zero_segment, "zero fixture was not marked zero");
        require(measurement.fac_rescale_float32 == 0, "zero rescale is not zero");
        require(measurement.fac_error_float32 == 0, "zero error factor is not zero");
        validate_memory(measurement, counters);
        ++counters.zero_checks;
    }
    const auto pair = co0_v2_measure_pair(zero, zero, measurements[1]);
    require(pair.zero_norm_pair, "zero pair was not marked zero");
    ++counters.zero_checks;
}

void validate_io_contract(Counters &counters) {
    namespace fs = std::filesystem;
    const fs::path root = fs::temp_directory_path() /
                          ("saq-co0-v2-b1-synthetic-" + std::to_string(static_cast<uint64_t>(getpid())));
    require(!fs::exists(root), "synthetic I/O directory already exists");
    fs::create_directories(root);
    try {
        const std::array<uint8_t, 3> abc{'a', 'b', 'c'};
        require(
            saqlib::caq_validation::co0_v2_sha256_bytes(abc) ==
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "SHA-256 synthetic fixture mismatch");
        ++counters.io_checks;

        const fs::path fvec_path = root / "tiny.fvecs";
        {
            std::ofstream output(fvec_path, std::ios::binary | std::ios::trunc);
            const uint32_t dimension = 64;
            for (uint32_t row = 0; row < 2; ++row) {
                output.write(reinterpret_cast<const char *>(&dimension), sizeof(dimension));
                for (uint32_t coordinate = 0; coordinate < dimension; ++coordinate) {
                    const float value = static_cast<float>(row * 1000U + coordinate) / 16.0F;
                    output.write(reinterpret_cast<const char *>(&value), sizeof(value));
                }
            }
            require(static_cast<bool>(output), "failed to write synthetic fvec fixture");
        }
        const auto shape = saqlib::caq_validation::co0_v2_validate_vector_file(
            fvec_path,
            2,
            64,
            sizeof(float));
        require(shape.rows == 2 && shape.dimension == 64, "synthetic fvec shape mismatch");
        saqlib::caq_validation::Co0V2FvecReader fvec_reader(fvec_path, 2, 64);
        const FloatVec row = fvec_reader.read(1);
        require(row[17] == static_cast<float>(1017) / 16.0F, "synthetic fvec random read mismatch");
        counters.io_checks += 2;

        const fs::path sample_path = root / "sample.csv.gz";
        {
            saqlib::caq_validation::Co0V2GzipWriter output(sample_path);
            output.write("dataset_id,cell_id,rank_in_cell,vector_id\n");
            output.write("tiny,0,0,1\n");
            output.write("tiny,0,1,0\n");
            output.close();
        }
        const auto samples =
            saqlib::caq_validation::co0_v2_read_sample_inventory(sample_path, "tiny");
        require(samples.size() == 2 && samples[1].vector_id == 0, "synthetic sample inventory mismatch");
        ++counters.io_checks;

        const fs::path pair_path = root / "pairs.csv.gz";
        {
            saqlib::caq_validation::Co0V2GzipWriter output(pair_path);
            output.write("dataset_id,cell_id,pair_rank,stored_vector_id,query_vector_id\n");
            output.write("tiny,0,0,1,0\n");
            output.close();
        }
        const auto pairs =
            saqlib::caq_validation::co0_v2_read_pair_inventory(pair_path, "tiny");
        require(pairs.size() == 1 && pairs[0].query_vector_id == 0, "synthetic pair inventory mismatch");
        ++counters.io_checks;

        const std::vector<uint32_t> code = [] {
            std::vector<uint32_t> values(64);
            for (size_t coordinate = 0; coordinate < values.size(); ++coordinate) {
                values[coordinate] = static_cast<uint32_t>((coordinate * 7) % 32);
            }
            return values;
        }();
        const fs::path shard_path = root / "codes.bin";
        saqlib::caq_validation::Co0V2CodeLocation location;
        {
            saqlib::caq_validation::Co0V2CodeShardWriter writer(shard_path, 5);
            location = writer.append(code);
            writer.close();
        }
        require(location.bit_offset == 0 && location.bit_length == 320, "synthetic code location mismatch");
        std::ifstream shard(shard_path, std::ios::binary);
        const std::vector<uint8_t> bytes(
            (std::istreambuf_iterator<char>(shard)),
            std::istreambuf_iterator<char>());
        require(
            saqlib::caq_validation::co0_v2_unpack_canonical_code(bytes, 64, 5) == code,
            "synthetic code shard roundtrip mismatch");
        counters.io_checks += 2;

        fs::remove_all(root);
    } catch (...) {
        fs::remove_all(root);
        throw;
    }
}

} // namespace

int main() {
    try {
        static_assert(sizeof(float) == 4);
        static_assert(std::numeric_limits<float>::is_iec559);

        const std::vector<Cell> cells{
            {"GIST", 64, 11},
            {"GIST", 192, 6},
            {"GIST", 320, 4},
            {"GIST", 256, 2},
            {"GIST", 832, 4},
            {"CIFAR", 64, 9},
            {"CIFAR", 192, 5},
            {"CIFAR", 128, 3},
            {"CIFAR", 384, 4},
        };
        const Profile profiles[] = {
            Profile::equal,
            Profile::dense,
            Profile::bounded_binary32_span,
        };

        Counters counters;
        for (const Cell &cell : cells) {
            for (Profile profile : profiles) {
                validate_cell(cell, profile, counters);
            }
        }
        validate_zero_case(counters);
        validate_io_contract(counters);

        std::cout << "{\n"
                  << "  \"schema_version\": 1,\n"
                  << "  \"stage\": \"V2-B1-synthetic\",\n"
                  << "  \"status\": \"PASS\",\n"
                  << "  \"cells\": " << counters.cells << ",\n"
                  << "  \"arm_measurements\": " << counters.arm_measurements << ",\n"
                  << "  \"source_parity_checks\": " << counters.source_parity_checks << ",\n"
                  << "  \"production_packer_checks\": " << counters.production_packer_checks << ",\n"
                  << "  \"canonical_roundtrips\": " << counters.canonical_roundtrips << ",\n"
                  << "  \"estimator_checks\": " << counters.estimator_checks << ",\n"
                  << "  \"estimator_reuse_checks\": " << counters.estimator_reuse_checks << ",\n"
                  << "  \"memory_checks\": " << counters.memory_checks << ",\n"
                  << "  \"zero_checks\": " << counters.zero_checks << ",\n"
                  << "  \"io_checks\": " << counters.io_checks << "\n"
                  << "}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cout << "{\n"
                  << "  \"schema_version\": 1,\n"
                  << "  \"stage\": \"V2-B1-synthetic\",\n"
                  << "  \"status\": \"FAIL\"\n"
                  << "}\n";
        std::cerr << "V2-B1 synthetic validation failed: " << error.what() << '\n';
        return 1;
    }
}

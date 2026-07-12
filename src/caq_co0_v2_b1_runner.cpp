#define BOOST_BIND_GLOBAL_PLACEHOLDERS

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include <time.h>

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>

#include "quantization/caq/co0_v2_b1_io.hpp"
#include "quantization/caq/co0_v2_frozen_rotation.hpp"
#include "quantization/caq/co0_v2_measurement.hpp"

namespace {

using boost::property_tree::ptree;
using saqlib::FloatRowMat;
using saqlib::FloatVec;
using saqlib::caq_validation::co0_v2_arm_name;
using saqlib::caq_validation::co0_v2_frozen_segmented_rotation_values;
using saqlib::caq_validation::co0_v2_frozen_whole_rotation_values;
using saqlib::caq_validation::co0_v2_measure_arm;
using saqlib::caq_validation::co0_v2_measure_pairs;
using saqlib::caq_validation::co0_v2_peak_rss_bytes;
using saqlib::caq_validation::co0_v2_read_pair_inventory;
using saqlib::caq_validation::co0_v2_read_sample_inventory;
using saqlib::caq_validation::co0_v2_sha256_file;
using saqlib::caq_validation::co0_v2_sha256_matrix;
using saqlib::caq_validation::co0_v2_validate_vector_file;
using saqlib::caq_validation::Co0V2Arm;
using saqlib::caq_validation::Co0V2CodeLocation;
using saqlib::caq_validation::Co0V2CodeShardWriter;
using saqlib::caq_validation::Co0V2EncodingMeasurement;
using saqlib::caq_validation::Co0V2FvecReader;
using saqlib::caq_validation::Co0V2GzipWriter;
using saqlib::caq_validation::Co0V2PairMeasurement;
using saqlib::caq_validation::Co0V2PairRow;
using saqlib::caq_validation::Co0V2SampleRow;

constexpr std::string_view kInputSpecSha =
    "044e965b9b7f7d78d999e8e16a900402dc0ad58f9a9e9d52b4d01102daebc88b";
constexpr std::string_view kPreregistrationSha =
    "39c1d591e22ac28de3041452f132c54c29f3b8831841863de055acc867039761";
constexpr std::string_view kHypothesesSha =
    "a70d38f380f2b4efa29c536bdf2c015f1af314552e78eb906dfc24dc8e7c7f34";
constexpr std::string_view kInventoryManifestSha =
    "38a24135876be6952208e2b9aaaaa6855843780c4bd96eb406a1f6a5e71d7952";
constexpr std::string_view kProtocolVersion =
    "saq-caq-co0-v2-b0-20260711-schema1";
constexpr uint64_t kExactCpuCeilingNs = UINT64_C(24) * UINT64_C(60) * UINT64_C(60) * UINT64_C(1000000000);

struct Cli {
    std::filesystem::path input_spec;
    std::filesystem::path preregistration;
    std::filesystem::path hypotheses;
    std::filesystem::path inventory_manifest;
    std::filesystem::path output_dir;
    unsigned int threads = 0;
};

struct ArtifactSpec {
    std::filesystem::path path;
    std::string format;
    uint64_t rows = 0;
    uint32_t dimension = 0;
    uint64_t size_bytes = 0;
    std::string expected_sha256;
};

struct SegmentSpec {
    size_t offset = 0;
    size_t dimension = 0;
    uint32_t total_bits = 0;
};

struct DatasetSpec {
    std::string dataset_id;
    uint64_t rows = 0;
    size_t dimension = 0;
    uint32_t clusters = 0;
    size_t positive_dimension = 0;
    std::vector<SegmentSpec> segments;
    ArtifactSpec base;
    ArtifactSpec centroids;
    ArtifactSpec variance;
    ArtifactSpec cluster_ids;
};

enum class ViewKind {
    native,
    same_segment_uniform,
    whole_uniform,
};

struct ViewSpec {
    std::string view_id;
    ViewKind kind = ViewKind::native;
    int segment_index = -1;
    size_t offset = 0;
    size_t dimension = 0;
    uint32_t total_bits = 0;
};

struct InventoryFiles {
    std::filesystem::path sample;
    std::string sample_sha;
    uint64_t sample_count = 0;
    std::filesystem::path pairs;
    std::string pairs_sha;
    uint64_t pair_count = 0;
    std::filesystem::path allocation;
    std::string allocation_sha;
};

struct RotationExpected {
    std::string dataset_id;
    int logical_seed = 0;
    std::string scope;
    int segment_index = -1;
    size_t dimension = 0;
    std::string sha256;
};

struct DuplicateSignature {
    std::string code_sha;
    uint32_t rescale_bits = 0;
    uint32_t error_bits = 0;

    bool operator==(const DuplicateSignature &) const = default;
};

struct ShardRecord {
    std::string dataset_id;
    int logical_seed = 0;
    std::string view_id;
    std::string arm;
    uint64_t encoding_csv_bytes = 0;
    uint64_t pair_csv_bytes = 0;
    uint64_t code_bytes = 0;
    uint64_t total_bytes = 0;
    uint64_t peak_rss_bytes = 0;
};

struct RunCounters {
    uint64_t encoding_rows = 0;
    uint64_t pair_rows = 0;
    uint64_t exact_cpu_ns = 0;
    uint64_t duplicate_checks = 0;
    uint64_t code_bytes = 0;
    uint64_t preflight_wall_ns = 0;
    uint64_t preflight_cpu_ns = 0;
    uint64_t rotation_wall_ns = 0;
    uint64_t rotation_cpu_ns = 0;
    uint64_t input_io_wall_ns = 0;
    uint64_t input_io_cpu_ns = 0;
    uint64_t residual_wall_ns = 0;
    uint64_t residual_cpu_ns = 0;
    std::array<uint64_t, 4> arm_wall_ns{};
    std::array<uint64_t, 4> arm_cpu_ns{};
    uint64_t source_parity_wall_ns = 0;
    uint64_t source_parity_cpu_ns = 0;
    uint64_t pair_estimator_wall_ns = 0;
    uint64_t pair_estimator_cpu_ns = 0;
    uint64_t output_io_wall_ns = 0;
    uint64_t output_io_cpu_ns = 0;
    uint64_t total_wall_ns = 0;
    uint64_t total_cpu_ns = 0;
    uint64_t serialized_output_bytes = 0;
    std::vector<ShardRecord> shards;
};

[[noreturn]] void fail(const std::string &message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string &message) {
    if (!condition) {
        fail(message);
    }
}

uint64_t cpu_time_ns() {
    timespec value{};
    require(
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) == 0,
        "clock_gettime(CLOCK_PROCESS_CPUTIME_ID) failed");
    require(value.tv_sec >= 0 && value.tv_nsec >= 0, "negative CPU timestamp");
    return static_cast<uint64_t>(value.tv_sec) * UINT64_C(1000000000) +
           static_cast<uint64_t>(value.tv_nsec);
}

uint64_t wall_elapsed_ns(std::chrono::steady_clock::time_point start) {
    const auto elapsed = std::chrono::steady_clock::now() - start;
    const auto nanoseconds =
        std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count();
    require(nanoseconds >= 0, "negative wall interval");
    return static_cast<uint64_t>(nanoseconds);
}

void add_counter(uint64_t &target, uint64_t value, std::string_view label) {
    require(value <= std::numeric_limits<uint64_t>::max() - target,
            std::string(label) + " counter overflow");
    target += value;
}

std::string view_kind_name(ViewKind kind) {
    switch (kind) {
    case ViewKind::native:
        return "native";
    case ViewKind::same_segment_uniform:
        return "same_segment_uniform";
    case ViewKind::whole_uniform:
        return "whole_uniform";
    }
    fail("unknown view kind");
}

Cli parse_cli(int argc, char **argv) {
    require(
        argc == 12,
        "usage: caq_co0_v2_b1_runner --input-spec PATH --preregistration PATH "
        "--hypotheses PATH --inventory-manifest PATH --output-dir PATH --threads=1");
    std::map<std::string, std::string> values;
    bool saw_threads = false;
    for (int index = 1; index < argc;) {
        const std::string key(argv[index]);
        if (key == "--threads=1") {
            require(!saw_threads, "duplicate --threads=1 argument");
            saw_threads = true;
            ++index;
            continue;
        }
        require(index + 1 < argc, "B1 argument is missing its value");
        const std::string value(argv[index + 1]);
        require(key.starts_with("--"), "B1 argument key must begin with --");
        require(!value.empty(), "B1 argument value is empty");
        require(values.emplace(key, value).second, "duplicate B1 argument: " + key);
        index += 2;
    }
    const std::set<std::string> expected{
        "--input-spec",
        "--preregistration",
        "--hypotheses",
        "--inventory-manifest",
        "--output-dir",
    };
    std::set<std::string> observed;
    for (const auto &[key, ignored] : values) {
        static_cast<void>(ignored);
        observed.insert(key);
    }
    require(observed == expected, "B1 CLI differs from the frozen interface");
    require(saw_threads, "B1 requires --threads=1");

    Cli cli;
    cli.input_spec = values.at("--input-spec");
    cli.preregistration = values.at("--preregistration");
    cli.hypotheses = values.at("--hypotheses");
    cli.inventory_manifest = values.at("--inventory-manifest");
    cli.output_dir = values.at("--output-dir");
    cli.threads = 1;
    require(!cli.output_dir.empty(), "B1 output directory is empty");
    return cli;
}

void verify_frozen_file(
    const std::filesystem::path &path,
    std::string_view expected_sha,
    std::string_view label) {
    require(std::filesystem::is_regular_file(path), std::string(label) + " is not a regular file");
    const std::string observed = co0_v2_sha256_file(path);
    require(observed == expected_sha, std::string(label) + " SHA-256 mismatch");
}

ArtifactSpec parse_artifact(const ptree &tree) {
    ArtifactSpec result;
    result.path = tree.get<std::string>("path");
    result.format = tree.get<std::string>("format");
    result.rows = tree.get<uint64_t>("rows");
    result.dimension = tree.get<uint32_t>("dimension");
    result.size_bytes = tree.get<uint64_t>("size_bytes");
    result.expected_sha256 = tree.get<std::string>("expected_sha256");
    return result;
}

std::vector<DatasetSpec> parse_input_spec(const std::filesystem::path &path) {
    ptree root;
    boost::property_tree::read_json(path.string(), root);
    require(root.get<unsigned int>("schema_version") == 1, "input spec schema mismatch");
    require(root.get<std::string>("protocol_version") == kProtocolVersion, "protocol version mismatch");
    require(root.get<uint64_t>("sample_size_per_dataset") == 50000, "sample size changed");

    std::vector<DatasetSpec> datasets;
    for (const auto &dataset_node : root.get_child("datasets")) {
        const ptree &tree = dataset_node.second;
        DatasetSpec dataset;
        dataset.dataset_id = tree.get<std::string>("dataset_id");
        dataset.rows = tree.get<uint64_t>("rows");
        dataset.dimension = tree.get<size_t>("dimension");
        dataset.clusters = tree.get<uint32_t>("ivf_clusters");
        dataset.positive_dimension = tree.get<size_t>("positive_dimension");
        for (const auto &segment_node : tree.get_child("plan")) {
            const ptree &segment = segment_node.second;
            dataset.segments.push_back(SegmentSpec{
                segment.get<size_t>("offset"),
                segment.get<size_t>("dimensions"),
                segment.get<uint32_t>("total_bits"),
            });
        }
        const ptree &artifacts = tree.get_child("artifacts");
        dataset.base = parse_artifact(artifacts.get_child("base"));
        dataset.centroids = parse_artifact(artifacts.get_child("centroids"));
        dataset.variance = parse_artifact(artifacts.get_child("variance"));
        dataset.cluster_ids = parse_artifact(artifacts.get_child("cluster_ids"));
        datasets.push_back(std::move(dataset));
    }
    require(datasets.size() == 2, "B1 requires exactly two frozen datasets");
    require(datasets[0].dataset_id == "gist_sample50k_k512", "first frozen dataset changed");
    require(datasets[1].dataset_id == "cifar60k_k512", "second frozen dataset changed");
    for (const DatasetSpec &dataset : datasets) {
        require(dataset.clusters == 512, "frozen IVF cluster count changed");
        size_t expected_offset = 0;
        for (const SegmentSpec &segment : dataset.segments) {
            require(segment.offset == expected_offset, "plan is not contiguous");
            expected_offset += segment.dimension;
        }
        require(expected_offset == dataset.dimension, "plan dimension does not match dataset");
    }
    return datasets;
}

std::map<std::string, InventoryFiles> parse_inventory_manifest(
    const std::filesystem::path &path,
    std::vector<RotationExpected> &rotations) {
    ptree root;
    boost::property_tree::read_json(path.string(), root);
    require(root.get<std::string>("protocol_version") == kProtocolVersion, "inventory protocol mismatch");
    const std::filesystem::path base_dir = path.parent_path();
    std::map<std::string, InventoryFiles> files;
    for (const auto &dataset_node : root.get_child("datasets")) {
        const ptree &tree = dataset_node.second;
        const std::string dataset_id = tree.get<std::string>("dataset_id");
        InventoryFiles item;
        item.sample = base_dir / tree.get<std::string>("sample_file.relative_path");
        item.sample_sha = tree.get<std::string>("sample_file.compressed_sha256");
        item.sample_count = tree.get<uint64_t>("sample_count");
        item.pairs = base_dir / tree.get<std::string>("pair_file.relative_path");
        item.pairs_sha = tree.get<std::string>("pair_file.compressed_sha256");
        item.pair_count = tree.get<uint64_t>("pair_count");
        item.allocation = base_dir / tree.get<std::string>("allocation_file.relative_path");
        item.allocation_sha = tree.get<std::string>("allocation_file.compressed_sha256");
        require(files.emplace(dataset_id, std::move(item)).second, "duplicate inventory dataset");
    }
    for (const auto &rotation_node : root.get_child("rotations")) {
        const ptree &tree = rotation_node.second;
        RotationExpected expected;
        expected.dataset_id = tree.get<std::string>("dataset_id");
        expected.logical_seed = tree.get<int>("logical_seed");
        expected.scope = tree.get<std::string>("scope");
        const std::string segment_index = tree.get<std::string>("segment_index", "null");
        expected.segment_index = segment_index == "null" ? -1 : std::stoi(segment_index);
        expected.dimension = tree.get<size_t>("dimension");
        expected.sha256 = tree.get<std::string>("sha256");
        rotations.push_back(std::move(expected));
    }
    require(rotations.size() == 27, "rotation inventory count changed");
    return files;
}

void preflight_artifact(const ArtifactSpec &artifact, std::string_view label) {
    require(std::filesystem::is_regular_file(artifact.path), std::string(label) + " does not exist");
    require(std::filesystem::file_size(artifact.path) == artifact.size_bytes, std::string(label) + " size mismatch");
    require(co0_v2_sha256_file(artifact.path) == artifact.expected_sha256, std::string(label) + " hash mismatch");
    require(artifact.format == "fvecs" || artifact.format == "ivecs", std::string(label) + " format changed");
    co0_v2_validate_vector_file(
        artifact.path,
        artifact.rows,
        artifact.dimension,
        sizeof(uint32_t));
}

std::vector<ViewSpec> make_views(const DatasetSpec &dataset) {
    std::vector<ViewSpec> views;
    for (size_t segment_index = 0; segment_index < dataset.segments.size(); ++segment_index) {
        const SegmentSpec &segment = dataset.segments[segment_index];
        if (segment.total_bits == 0) {
            continue;
        }
        views.push_back(ViewSpec{
            "native_s" + std::to_string(segment_index) + "_d" +
                std::to_string(segment.dimension) + "_b" +
                std::to_string(segment.total_bits),
            ViewKind::native,
            static_cast<int>(segment_index),
            segment.offset,
            segment.dimension,
            segment.total_bits,
        });
    }
    for (size_t segment_index = 0; segment_index < dataset.segments.size(); ++segment_index) {
        const SegmentSpec &segment = dataset.segments[segment_index];
        if (segment.total_bits == 0) {
            continue;
        }
        views.push_back(ViewSpec{
            "uniform_s" + std::to_string(segment_index) + "_d" +
                std::to_string(segment.dimension) + "_b4",
            ViewKind::same_segment_uniform,
            static_cast<int>(segment_index),
            segment.offset,
            segment.dimension,
            4,
        });
    }
    views.push_back(ViewSpec{
        "whole_d" + std::to_string(dataset.positive_dimension) + "_b4",
        ViewKind::whole_uniform,
        -1,
        0,
        dataset.positive_dimension,
        4,
    });
    const size_t expected = dataset.dataset_id == "gist_sample50k_k512" ? 9 : 7;
    require(views.size() == expected, "frozen view count changed");
    return views;
}

const RotationExpected &find_rotation(
    const std::vector<RotationExpected> &rotations,
    std::string_view dataset_id,
    int logical_seed,
    std::string_view scope,
    int segment_index,
    size_t dimension) {
    const RotationExpected *found = nullptr;
    for (const RotationExpected &rotation : rotations) {
        if (rotation.dataset_id == dataset_id && rotation.logical_seed == logical_seed &&
            rotation.scope == scope && rotation.segment_index == segment_index &&
            rotation.dimension == dimension) {
            require(found == nullptr, "duplicate frozen rotation entry");
            found = &rotation;
        }
    }
    require(found != nullptr, "missing frozen rotation entry");
    return *found;
}

std::vector<FloatRowMat> verified_segmented_rotations(
    const DatasetSpec &dataset,
    int logical_seed,
    const std::vector<RotationExpected> &expected) {
    std::vector<size_t> dimensions;
    for (const SegmentSpec &segment : dataset.segments) {
        if (segment.total_bits > 0) {
            dimensions.push_back(segment.dimension);
        }
    }
    std::vector<FloatRowMat> rotations;
    rotations.reserve(dimensions.size());
    for (size_t dimension : dimensions) {
        rotations.emplace_back(
            static_cast<Eigen::Index>(dimension),
            static_cast<Eigen::Index>(dimension));
    }
    std::vector<std::span<float>> outputs;
    outputs.reserve(rotations.size());
    for (FloatRowMat &rotation : rotations) {
        outputs.emplace_back(rotation.data(), static_cast<size_t>(rotation.size()));
    }
    co0_v2_frozen_segmented_rotation_values(dimensions, logical_seed, outputs);
    for (size_t index = 0; index < rotations.size(); ++index) {
        const RotationExpected &frozen = find_rotation(
            expected,
            dataset.dataset_id,
            logical_seed,
            "segmented",
            static_cast<int>(index),
            dimensions[index]);
        require(co0_v2_sha256_matrix(rotations[index]) == frozen.sha256, "rotation hash mismatch");
    }
    return rotations;
}

FloatRowMat verified_whole_rotation(
    const DatasetSpec &dataset,
    int logical_seed,
    const std::vector<RotationExpected> &expected) {
    FloatRowMat rotation(
        static_cast<Eigen::Index>(dataset.positive_dimension),
        static_cast<Eigen::Index>(dataset.positive_dimension));
    co0_v2_frozen_whole_rotation_values(
        dataset.positive_dimension,
        logical_seed,
        std::span<float>(rotation.data(), static_cast<size_t>(rotation.size())));
    const RotationExpected &frozen = find_rotation(
        expected,
        dataset.dataset_id,
        logical_seed,
        "whole",
        -1,
        dataset.positive_dimension);
    require(co0_v2_sha256_matrix(rotation) == frozen.sha256, "whole rotation hash mismatch");
    return rotation;
}

void validate_inventory_structure(
    const DatasetSpec &dataset,
    std::vector<Co0V2SampleRow> &samples,
    const std::vector<Co0V2PairRow> &pairs,
    uint64_t expected_sample_count,
    uint64_t expected_pair_count) {
    require(samples.size() == expected_sample_count, "sample inventory count mismatch");
    require(pairs.size() == expected_pair_count, "pair inventory count mismatch");
    std::sort(samples.begin(), samples.end(), [](const auto &lhs, const auto &rhs) {
        return std::tie(lhs.cell_id, lhs.vector_id) < std::tie(rhs.cell_id, rhs.vector_id);
    });
    std::set<uint32_t> vector_ids;
    std::map<uint32_t, uint32_t> vector_cell;
    for (const Co0V2SampleRow &row : samples) {
        require(row.cell_id < dataset.clusters, "sample cell is out of range");
        require(row.vector_id < dataset.rows, "sample vector id is out of range");
        require(vector_ids.insert(row.vector_id).second, "sample vector is duplicated");
        vector_cell[row.vector_id] = row.cell_id;
    }
    std::set<uint32_t> paired_ids;
    for (const Co0V2PairRow &pair : pairs) {
        require(pair.cell_id < dataset.clusters, "pair cell is out of range");
        require(vector_cell.at(pair.stored_vector_id) == pair.cell_id, "stored pair side is in wrong cell");
        require(vector_cell.at(pair.query_vector_id) == pair.cell_id, "query pair side is in wrong cell");
        require(paired_ids.insert(pair.stored_vector_id).second, "stored pair vector reused");
        require(paired_ids.insert(pair.query_vector_id).second, "query pair vector reused");
    }
}

std::vector<FloatVec> load_centroids(const DatasetSpec &dataset, RunCounters &counters) {
    Co0V2FvecReader reader(dataset.centroids.path, dataset.centroids.rows, dataset.centroids.dimension);
    std::vector<FloatVec> centroids;
    centroids.reserve(dataset.clusters);
    const uint64_t cpu_start = cpu_time_ns();
    const auto wall_start = std::chrono::steady_clock::now();
    for (uint32_t cell = 0; cell < dataset.clusters; ++cell) {
        centroids.push_back(reader.read(cell));
    }
    add_counter(counters.input_io_wall_ns, wall_elapsed_ns(wall_start), "input I/O wall");
    add_counter(counters.input_io_cpu_ns, cpu_time_ns() - cpu_start, "input I/O CPU");
    return centroids;
}

FloatRowMat prepare_residuals(
    const DatasetSpec &dataset,
    const std::vector<Co0V2SampleRow> &samples,
    const std::vector<FloatVec> &centroids,
    RunCounters &counters) {
    Co0V2FvecReader base(dataset.base.path, dataset.base.rows, dataset.base.dimension);
    FloatRowMat residuals(
        static_cast<Eigen::Index>(samples.size()),
        static_cast<Eigen::Index>(dataset.dimension));
    uint64_t cpu_start = cpu_time_ns();
    auto wall_start = std::chrono::steady_clock::now();
    for (size_t row_index = 0; row_index < samples.size(); ++row_index) {
        const Co0V2SampleRow &sample = samples[row_index];
        residuals.row(static_cast<Eigen::Index>(row_index)) =
            base.read(sample.vector_id);
    }
    add_counter(counters.input_io_wall_ns, wall_elapsed_ns(wall_start), "input I/O wall");
    add_counter(counters.input_io_cpu_ns, cpu_time_ns() - cpu_start, "input I/O CPU");

    cpu_start = cpu_time_ns();
    wall_start = std::chrono::steady_clock::now();
    for (size_t row_index = 0; row_index < samples.size(); ++row_index) {
        const Co0V2SampleRow &sample = samples[row_index];
        residuals.row(static_cast<Eigen::Index>(row_index)) -= centroids[sample.cell_id];
        require(residuals.row(static_cast<Eigen::Index>(row_index)).allFinite(), "residual is non-finite");
    }
    add_counter(counters.residual_wall_ns, wall_elapsed_ns(wall_start), "residual wall");
    add_counter(counters.residual_cpu_ns, cpu_time_ns() - cpu_start, "residual CPU");
    return residuals;
}

long double exact_call_upper_ns(
    std::string_view dataset,
    size_t dimension,
    uint32_t bits,
    ViewKind view_kind) {
    using Key = std::tuple<std::string_view, size_t, uint32_t>;
    static const std::map<Key, long double> bounds{
        {{"gist_sample50k_k512", 64, 11}, 81361952.100L},
        {{"gist_sample50k_k512", 192, 6}, 9239443.382L},
        {{"gist_sample50k_k512", 320, 4}, 3833114.132L},
        {{"gist_sample50k_k512", 256, 2}, 534626.084L},
        {{"gist_sample50k_k512", 832, 4}, 10508014.358L},
        {{"cifar60k_k512", 64, 9}, 20646318.872L},
        {{"cifar60k_k512", 192, 5}, 4436014.646L},
        {{"cifar60k_k512", 128, 3}, 631575.631L},
        {{"cifar60k_k512", 384, 4}, 4511192.412L},
    };
    if (view_kind != ViewKind::native && bits == 4) {
        const size_t whole_dimension = dataset == "gist_sample50k_k512" ? 832 : 384;
        return bounds.at(Key{dataset, whole_dimension, 4});
    }
    const auto found = bounds.find(Key{dataset, dimension, bits});
    require(found != bounds.end(), "missing frozen exact-call CPU bound");
    return found->second;
}

std::string encoding_header() {
    return "dataset_id,vector_id,cell_id,logical_seed,c_rng_seed,view_id,view_kind,"
           "segment_index,offset,dimension,total_bits,arm,zero_segment,code_shard,"
           "code_bit_offset,code_bit_length,code_sha256,cosine,cosine_squared_J,"
           "angular_excess_E,fac_rescale_float32,fac_error_float32,"
           "independent_error_factor,code_equal_corrected_exact,accepted_moves,"
           "completed_rounds,first_pass_events,replay_events,heap_comparisons,"
           "objective_comparisons,max_integer_bits,wall_time_ns,cpu_time_ns,"
           "peak_transient_bytes\n";
}

std::string pair_header() {
    return "dataset_id,cell_id,pair_rank,stored_vector_id,query_vector_id,logical_seed,"
           "view_id,arm,stored_norm,query_norm,zero_norm_pair,true_inner_product,"
           "estimated_inner_product,signed_ip_error,absolute_ip_error,"
           "normalized_absolute_ip_error,true_l2_squared,estimated_l2_squared,"
           "absolute_l2_squared_error,bound_radius,bound_covered\n";
}

std::string encoding_csv_row(
    const DatasetSpec &dataset,
    const Co0V2SampleRow &sample,
    int logical_seed,
    const ViewSpec &view,
    const Co0V2EncodingMeasurement &measurement,
    std::string_view code_shard,
    const Co0V2CodeLocation &location) {
    std::ostringstream output;
    output << std::setprecision(21)
           << dataset.dataset_id << ',' << sample.vector_id << ',' << sample.cell_id << ','
           << logical_seed << ',' << logical_seed + 1 << ',' << view.view_id << ','
           << view_kind_name(view.kind) << ',' << view.segment_index << ',' << view.offset << ','
           << view.dimension << ',' << view.total_bits << ',' << co0_v2_arm_name(measurement.arm) << ','
           << (measurement.zero_segment ? 1 : 0) << ',' << code_shard << ','
           << location.bit_offset << ',' << location.bit_length << ',' << location.sha256 << ','
           << measurement.geometry.cosine << ',' << measurement.geometry.cosine_squared << ','
           << measurement.geometry.angular_excess << ',' << measurement.fac_rescale_float32 << ','
           << measurement.fac_error_float32 << ',' << measurement.geometry.independent_error_factor << ','
           << (measurement.code_equal_corrected_exact ? 1 : 0) << ','
           << measurement.accepted_moves << ',' << measurement.completed_rounds << ','
           << measurement.oracle_work.first_pass_events << ',' << measurement.oracle_work.replay_events << ','
           << measurement.oracle_work.heap_comparisons << ','
           << measurement.oracle_work.objective_comparisons << ','
           << measurement.oracle_work.max_integer_bits << ',' << measurement.wall_time_ns << ','
           << measurement.cpu_time_ns << ',' << measurement.memory.peak_transient_bytes << '\n';
    return output.str();
}

std::string pair_csv_row(
    const DatasetSpec &dataset,
    const Co0V2PairRow &pair,
    int logical_seed,
    const ViewSpec &view,
    Co0V2Arm arm,
    const Co0V2PairMeasurement &measurement) {
    std::ostringstream output;
    output << std::setprecision(17)
           << dataset.dataset_id << ',' << pair.cell_id << ',' << pair.pair_rank << ','
           << pair.stored_vector_id << ',' << pair.query_vector_id << ',' << logical_seed << ','
           << view.view_id << ',' << co0_v2_arm_name(arm) << ',' << measurement.stored_norm << ','
           << measurement.query_norm << ',' << (measurement.zero_norm_pair ? 1 : 0) << ','
           << measurement.true_inner_product << ',' << measurement.estimated_inner_product << ','
           << measurement.signed_ip_error << ',' << measurement.absolute_ip_error << ','
           << measurement.normalized_absolute_ip_error << ',' << measurement.true_l2_squared << ','
           << measurement.estimated_l2_squared << ',' << measurement.absolute_l2_squared_error << ','
           << measurement.bound_radius << ',' << (measurement.bound_covered ? 1 : 0) << '\n';
    return output.str();
}

std::array<Co0V2Arm, 4> arms() {
    return {
        Co0V2Arm::lvq_init,
        Co0V2Arm::caq_r6,
        Co0V2Arm::caq_local_fixed_point,
        Co0V2Arm::corrected_exact,
    };
}

void write_run_manifest(
    const std::filesystem::path &output_dir,
    std::string_view status,
    const RunCounters &counters,
    std::string_view message) {
    std::filesystem::create_directories(output_dir);
    std::ofstream output(output_dir / "run_manifest.json", std::ios::trunc);
    if (!output) {
        return;
    }
    output << "{\n"
           << "  \"schema_version\": 1,\n"
           << "  \"stage\": \"V2-B1\",\n"
           << "  \"status\": \"" << status << "\",\n"
           << "  \"protocol_version\": \"" << kProtocolVersion << "\",\n"
           << "  \"threads\": 1,\n"
           << "  \"encoding_rows\": " << counters.encoding_rows << ",\n"
           << "  \"pair_rows\": " << counters.pair_rows << ",\n"
           << "  \"exact_cpu_ns\": " << counters.exact_cpu_ns << ",\n"
           << "  \"duplicate_checks\": " << counters.duplicate_checks << ",\n"
           << "  \"code_bytes\": " << counters.code_bytes << ",\n"
           << "  \"serialized_output_bytes\": " << counters.serialized_output_bytes << ",\n"
           << "  \"peak_rss_bytes\": " << co0_v2_peak_rss_bytes() << ",\n"
           << "  \"work_accounting_ns\": {\n"
           << "    \"preflight_wall\": " << counters.preflight_wall_ns << ",\n"
           << "    \"preflight_cpu\": " << counters.preflight_cpu_ns << ",\n"
           << "    \"rotation_wall\": " << counters.rotation_wall_ns << ",\n"
           << "    \"rotation_cpu\": " << counters.rotation_cpu_ns << ",\n"
           << "    \"input_io_wall\": " << counters.input_io_wall_ns << ",\n"
           << "    \"input_io_cpu\": " << counters.input_io_cpu_ns << ",\n"
           << "    \"residual_wall\": " << counters.residual_wall_ns << ",\n"
           << "    \"residual_cpu\": " << counters.residual_cpu_ns << ",\n"
           << "    \"pair_estimator_wall\": " << counters.pair_estimator_wall_ns << ",\n"
           << "    \"pair_estimator_cpu\": " << counters.pair_estimator_cpu_ns << ",\n"
           << "    \"source_parity_wall\": " << counters.source_parity_wall_ns << ",\n"
           << "    \"source_parity_cpu\": " << counters.source_parity_cpu_ns << ",\n"
           << "    \"output_io_wall\": " << counters.output_io_wall_ns << ",\n"
           << "    \"output_io_cpu\": " << counters.output_io_cpu_ns << ",\n"
           << "    \"total_wall\": " << counters.total_wall_ns << ",\n"
           << "    \"total_cpu\": " << counters.total_cpu_ns << ",\n"
           << "    \"arms\": {\n";
    const auto arm_values = arms();
    for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
        output << "      \"" << co0_v2_arm_name(arm_values[arm_index]) << "\": {"
               << "\"wall\": " << counters.arm_wall_ns[arm_index] << ", "
               << "\"cpu\": " << counters.arm_cpu_ns[arm_index] << "}"
               << (arm_index + 1 == arm_values.size() ? "\n" : ",\n");
    }
    output << "    }\n"
           << "  },\n"
           << "  \"shards\": [\n";
    for (size_t index = 0; index < counters.shards.size(); ++index) {
        const ShardRecord &shard = counters.shards[index];
        output << "    {\"dataset_id\": \"" << shard.dataset_id
               << "\", \"logical_seed\": " << shard.logical_seed
               << ", \"view_id\": \"" << shard.view_id
               << "\", \"arm\": \"" << shard.arm
               << "\", \"encoding_csv_bytes\": " << shard.encoding_csv_bytes
               << ", \"pair_csv_bytes\": " << shard.pair_csv_bytes
               << ", \"code_bytes\": " << shard.code_bytes
               << ", \"total_bytes\": " << shard.total_bytes
               << ", \"peak_rss_bytes\": " << shard.peak_rss_bytes << "}"
               << (index + 1 == counters.shards.size() ? "\n" : ",\n");
    }
    output << "  ],\n"
           << "  \"message\": \"";
    for (char character : message) {
        if (character == '\\' || character == '"') {
            output << '\\';
        }
        output << character;
    }
    output << "\"\n}\n";
}

void run_view(
    const DatasetSpec &dataset,
    const std::vector<Co0V2SampleRow> &samples,
    const std::vector<Co0V2PairRow> &pairs,
    const FloatRowMat &residuals,
    int logical_seed,
    const ViewSpec &view,
    const FloatRowMat &rotation,
    const std::filesystem::path &output_dir,
    std::vector<std::array<DuplicateSignature, 4>> &duplicate_reference,
    RunCounters &counters) {
    const std::filesystem::path shard_dir = output_dir / dataset.dataset_id /
                                            ("logical_seed_" + std::to_string(logical_seed)) / view.view_id;
    std::array<std::unique_ptr<Co0V2GzipWriter>, 4> encoding_writers;
    std::array<std::unique_ptr<Co0V2GzipWriter>, 4> pair_writers;
    std::array<std::unique_ptr<Co0V2CodeShardWriter>, 4> code_writers;
    std::array<std::string, 4> code_relative;
    std::array<std::filesystem::path, 4> encoding_paths;
    std::array<std::filesystem::path, 4> pair_paths;
    std::array<std::filesystem::path, 4> code_paths;
    const auto arm_values = arms();
    for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
        const std::string arm(co0_v2_arm_name(arm_values[arm_index]));
        encoding_paths[arm_index] = shard_dir / (arm + ".encoding.csv.gz");
        pair_paths[arm_index] = shard_dir / (arm + ".pairs.csv.gz");
        code_paths[arm_index] = shard_dir / (arm + ".codes.bin");
        encoding_writers[arm_index] =
            std::make_unique<Co0V2GzipWriter>(encoding_paths[arm_index]);
        pair_writers[arm_index] =
            std::make_unique<Co0V2GzipWriter>(pair_paths[arm_index]);
        code_writers[arm_index] =
            std::make_unique<Co0V2CodeShardWriter>(code_paths[arm_index], view.total_bits);
        encoding_writers[arm_index]->write(encoding_header());
        pair_writers[arm_index]->write(pair_header());
        code_relative[arm_index] =
            std::filesystem::relative(code_paths[arm_index], output_dir).generic_string();
    }

    size_t sample_begin = 0;
    size_t pair_begin = 0;
    for (uint32_t cell = 0; cell < dataset.clusters; ++cell) {
        size_t sample_end = sample_begin;
        while (sample_end < samples.size() && samples[sample_end].cell_id == cell) {
            ++sample_end;
        }
        size_t pair_end = pair_begin;
        while (pair_end < pairs.size() && pairs[pair_end].cell_id == cell) {
            ++pair_end;
        }
        if (sample_begin == sample_end) {
            require(pair_begin == pair_end, "pair exists in empty sampled cell");
            continue;
        }

        const size_t cell_size = sample_end - sample_begin;
        FloatRowMat rotated(
            static_cast<Eigen::Index>(cell_size),
            static_cast<Eigen::Index>(view.dimension));
        for (size_t local = 0; local < cell_size; ++local) {
            const size_t row = sample_begin + local;
            rotated.row(static_cast<Eigen::Index>(local)) =
                residuals.row(static_cast<Eigen::Index>(row))
                    .segment(static_cast<Eigen::Index>(view.offset),
                             static_cast<Eigen::Index>(view.dimension)) *
                rotation;
            require(rotated.row(static_cast<Eigen::Index>(local)).allFinite(), "rotated residual is non-finite");
        }

        std::vector<std::array<Co0V2EncodingMeasurement, 4>> measurements(cell_size);
        std::unordered_map<uint32_t, size_t> local_index;
        local_index.reserve(cell_size);
        for (size_t local = 0; local < cell_size; ++local) {
            const Co0V2SampleRow &sample = samples[sample_begin + local];
            local_index.emplace(sample.vector_id, local);
            FloatVec input = rotated.row(static_cast<Eigen::Index>(local));
            for (size_t arm_index = 0; arm_index < 3; ++arm_index) {
                const uint64_t measured_cpu_start = cpu_time_ns();
                const auto measured_wall_start = std::chrono::steady_clock::now();
                measurements[local][arm_index] =
                    co0_v2_measure_arm(input, view.total_bits, arm_values[arm_index]);
                const uint64_t measured_wall = wall_elapsed_ns(measured_wall_start);
                const uint64_t measured_cpu = cpu_time_ns() - measured_cpu_start;
                add_counter(
                    counters.arm_wall_ns[arm_index],
                    measurements[local][arm_index].wall_time_ns,
                    "arm wall");
                add_counter(
                    counters.arm_cpu_ns[arm_index],
                    measurements[local][arm_index].cpu_time_ns,
                    "arm CPU");
                if (arm_index < 2) {
                    require(
                        measured_wall >= measurements[local][arm_index].wall_time_ns,
                        "source-parity wall accounting underflow");
                    require(
                        measured_cpu >= measurements[local][arm_index].cpu_time_ns,
                        "source-parity CPU accounting underflow");
                    add_counter(
                        counters.source_parity_wall_ns,
                        measured_wall - measurements[local][arm_index].wall_time_ns,
                        "source-parity wall");
                    add_counter(
                        counters.source_parity_cpu_ns,
                        measured_cpu - measurements[local][arm_index].cpu_time_ns,
                        "source-parity CPU");
                }
            }
            const long double next_upper = exact_call_upper_ns(
                dataset.dataset_id,
                view.dimension,
                view.total_bits,
                view.kind);
            require(
                static_cast<long double>(counters.exact_cpu_ns) + next_upper <=
                    static_cast<long double>(kExactCpuCeilingNs),
                "exact-label CPU ceiling reached before the next frozen label");
            measurements[local][3] =
                co0_v2_measure_arm(input, view.total_bits, Co0V2Arm::corrected_exact);
            add_counter(
                counters.arm_wall_ns[3],
                measurements[local][3].wall_time_ns,
                "exact arm wall");
            add_counter(
                counters.arm_cpu_ns[3],
                measurements[local][3].cpu_time_ns,
                "exact arm CPU");
            require(
                measurements[local][3].cpu_time_ns <=
                    std::numeric_limits<uint64_t>::max() - counters.exact_cpu_ns,
                "exact CPU accumulator overflow");
            counters.exact_cpu_ns += measurements[local][3].cpu_time_ns;
            require(
                counters.exact_cpu_ns <= kExactCpuCeilingNs,
                "exact-label CPU ceiling was exceeded by a frozen call");
            const auto &exact_code = measurements[local][3].code;
            for (auto &measurement : measurements[local]) {
                measurement.code_equal_corrected_exact = measurement.code == exact_code;
            }

            for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
                const DuplicateSignature signature{
                    saqlib::caq_validation::co0_v2_sha256_code_words(
                        measurements[local][arm_index].code),
                    std::bit_cast<uint32_t>(measurements[local][arm_index].fac_rescale_float32),
                    std::bit_cast<uint32_t>(measurements[local][arm_index].fac_error_float32),
                };
                const bool duplicate_native = dataset.dataset_id == "gist_sample50k_k512" &&
                                              view.kind == ViewKind::native && view.segment_index == 2;
                const bool duplicate_uniform = dataset.dataset_id == "gist_sample50k_k512" &&
                                               view.kind == ViewKind::same_segment_uniform && view.segment_index == 2;
                if (duplicate_native) {
                    duplicate_reference[sample_begin + local][arm_index] = signature;
                } else if (duplicate_uniform) {
                    require(
                        duplicate_reference[sample_begin + local][arm_index] == signature,
                        "predeclared GIST native/uniform duplicate check failed");
                    ++counters.duplicate_checks;
                }
            }
        }

        uint64_t io_cpu_start = cpu_time_ns();
        auto io_wall_start = std::chrono::steady_clock::now();
        for (size_t local = 0; local < cell_size; ++local) {
            const Co0V2SampleRow &sample = samples[sample_begin + local];
            for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
                const Co0V2CodeLocation location =
                    code_writers[arm_index]->append(measurements[local][arm_index].code);
                encoding_writers[arm_index]->write(encoding_csv_row(
                    dataset,
                    sample,
                    logical_seed,
                    view,
                    measurements[local][arm_index],
                    code_relative[arm_index],
                    location));
                ++counters.encoding_rows;
            }
        }
        add_counter(counters.output_io_wall_ns, wall_elapsed_ns(io_wall_start), "output I/O wall");
        add_counter(counters.output_io_cpu_ns, cpu_time_ns() - io_cpu_start, "output I/O CPU");

        std::vector<std::array<Co0V2PairMeasurement, 4>> pair_measurements(pair_end - pair_begin);
        const uint64_t pair_cpu_start = cpu_time_ns();
        const auto pair_wall_start = std::chrono::steady_clock::now();
        for (size_t pair_index = pair_begin; pair_index < pair_end; ++pair_index) {
            const Co0V2PairRow &pair = pairs[pair_index];
            const size_t stored_local = local_index.at(pair.stored_vector_id);
            const size_t query_local = local_index.at(pair.query_vector_id);
            const FloatVec stored = rotated.row(static_cast<Eigen::Index>(stored_local));
            const FloatVec query = rotated.row(static_cast<Eigen::Index>(query_local));
            const std::vector<Co0V2PairMeasurement> measured = co0_v2_measure_pairs(
                stored,
                query,
                measurements[stored_local]);
            require(measured.size() == arm_values.size(), "pair arm count changed");
            for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
                pair_measurements[pair_index - pair_begin][arm_index] = measured[arm_index];
            }
        }
        add_counter(
            counters.pair_estimator_wall_ns,
            wall_elapsed_ns(pair_wall_start),
            "pair estimator wall");
        add_counter(
            counters.pair_estimator_cpu_ns,
            cpu_time_ns() - pair_cpu_start,
            "pair estimator CPU");

        io_cpu_start = cpu_time_ns();
        io_wall_start = std::chrono::steady_clock::now();
        for (size_t pair_index = pair_begin; pair_index < pair_end; ++pair_index) {
            const Co0V2PairRow &pair = pairs[pair_index];
            for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
                pair_writers[arm_index]->write(pair_csv_row(
                    dataset,
                    pair,
                    logical_seed,
                    view,
                    arm_values[arm_index],
                    pair_measurements[pair_index - pair_begin][arm_index]));
                ++counters.pair_rows;
            }
        }
        add_counter(counters.output_io_wall_ns, wall_elapsed_ns(io_wall_start), "output I/O wall");
        add_counter(counters.output_io_cpu_ns, cpu_time_ns() - io_cpu_start, "output I/O CPU");

        sample_begin = sample_end;
        pair_begin = pair_end;
    }
    require(sample_begin == samples.size(), "not all sample rows were processed");
    require(pair_begin == pairs.size(), "not all pair rows were processed");

    const uint64_t close_cpu_start = cpu_time_ns();
    const auto close_wall_start = std::chrono::steady_clock::now();
    for (size_t arm_index = 0; arm_index < arm_values.size(); ++arm_index) {
        encoding_writers[arm_index]->close();
        pair_writers[arm_index]->close();
        code_writers[arm_index]->close();
        add_counter(
            counters.code_bytes,
            code_writers[arm_index]->bytes_written(),
            "code bytes");
        const uint64_t encoding_bytes = std::filesystem::file_size(encoding_paths[arm_index]);
        const uint64_t pair_bytes = std::filesystem::file_size(pair_paths[arm_index]);
        const uint64_t code_bytes = std::filesystem::file_size(code_paths[arm_index]);
        const uint64_t total_bytes = encoding_bytes + pair_bytes + code_bytes;
        add_counter(counters.serialized_output_bytes, total_bytes, "serialized output");
        counters.shards.push_back(ShardRecord{
            dataset.dataset_id,
            logical_seed,
            view.view_id,
            std::string(co0_v2_arm_name(arm_values[arm_index])),
            encoding_bytes,
            pair_bytes,
            code_bytes,
            total_bytes,
            co0_v2_peak_rss_bytes(),
        });
    }
    add_counter(counters.output_io_wall_ns, wall_elapsed_ns(close_wall_start), "output I/O wall");
    add_counter(counters.output_io_cpu_ns, cpu_time_ns() - close_cpu_start, "output I/O CPU");
}

void run_dataset(
    const DatasetSpec &dataset,
    const InventoryFiles &inventory,
    const std::vector<RotationExpected> &rotation_expected,
    const std::filesystem::path &output_dir,
    RunCounters &counters) {
    std::vector<Co0V2SampleRow> samples =
        co0_v2_read_sample_inventory(inventory.sample, dataset.dataset_id);
    std::vector<Co0V2PairRow> pairs =
        co0_v2_read_pair_inventory(inventory.pairs, dataset.dataset_id);
    validate_inventory_structure(
        dataset,
        samples,
        pairs,
        inventory.sample_count,
        inventory.pair_count);
    std::sort(pairs.begin(), pairs.end(), [](const auto &lhs, const auto &rhs) {
        return std::tie(lhs.cell_id, lhs.pair_rank) < std::tie(rhs.cell_id, rhs.pair_rank);
    });

    const std::vector<FloatVec> centroids = load_centroids(dataset, counters);
    const FloatRowMat residuals = prepare_residuals(dataset, samples, centroids, counters);
    const std::vector<ViewSpec> views = make_views(dataset);

    for (int logical_seed = 0; logical_seed < 3; ++logical_seed) {
        const uint64_t rotation_cpu_start = cpu_time_ns();
        const auto rotation_wall_start = std::chrono::steady_clock::now();
        const std::vector<FloatRowMat> segmented =
            verified_segmented_rotations(dataset, logical_seed, rotation_expected);
        const FloatRowMat whole =
            verified_whole_rotation(dataset, logical_seed, rotation_expected);
        add_counter(
            counters.rotation_wall_ns,
            wall_elapsed_ns(rotation_wall_start),
            "rotation wall");
        add_counter(
            counters.rotation_cpu_ns,
            cpu_time_ns() - rotation_cpu_start,
            "rotation CPU");
        std::vector<std::array<DuplicateSignature, 4>> duplicate_reference(samples.size());
        for (const ViewSpec &view : views) {
            const FloatRowMat &rotation = view.kind == ViewKind::whole_uniform
                                              ? whole
                                              : segmented[static_cast<size_t>(view.segment_index)];
            run_view(
                dataset,
                samples,
                pairs,
                residuals,
                logical_seed,
                view,
                rotation,
                output_dir,
                duplicate_reference,
                counters);
        }
    }
}

} // namespace

int main(int argc, char **argv) {
    std::optional<Cli> cli;
    bool output_initialized = false;
    RunCounters counters;
    const auto total_wall_start = std::chrono::steady_clock::now();
    uint64_t total_cpu_start = 0;
    try {
        static_assert(sizeof(float) == 4);
        static_assert(std::numeric_limits<float>::is_iec559);
        static_assert(std::endian::native == std::endian::little);
        total_cpu_start = cpu_time_ns();
        cli = parse_cli(argc, argv);

        const uint64_t preflight_cpu_start = cpu_time_ns();
        const auto preflight_wall_start = std::chrono::steady_clock::now();
        verify_frozen_file(cli->input_spec, kInputSpecSha, "input spec");
        verify_frozen_file(cli->preregistration, kPreregistrationSha, "preregistration");
        verify_frozen_file(cli->hypotheses, kHypothesesSha, "hypothesis ledger");
        verify_frozen_file(cli->inventory_manifest, kInventoryManifestSha, "inventory manifest");

        if (std::filesystem::exists(cli->output_dir)) {
            require(
                std::filesystem::is_directory(cli->output_dir) &&
                    std::filesystem::is_empty(cli->output_dir),
                "B1 output directory must not exist or must be empty");
        }
        std::filesystem::create_directories(cli->output_dir);
        output_initialized = true;

        const std::vector<DatasetSpec> datasets = parse_input_spec(cli->input_spec);
        std::vector<RotationExpected> rotations;
        const std::map<std::string, InventoryFiles> inventories =
            parse_inventory_manifest(cli->inventory_manifest, rotations);

        for (const DatasetSpec &dataset : datasets) {
            preflight_artifact(dataset.base, dataset.dataset_id + " base");
            preflight_artifact(dataset.centroids, dataset.dataset_id + " centroids");
            preflight_artifact(dataset.variance, dataset.dataset_id + " variance");
            preflight_artifact(dataset.cluster_ids, dataset.dataset_id + " cluster ids");
            const InventoryFiles &inventory = inventories.at(dataset.dataset_id);
            verify_frozen_file(inventory.sample, inventory.sample_sha, "sample inventory");
            verify_frozen_file(inventory.pairs, inventory.pairs_sha, "pair inventory");
            verify_frozen_file(inventory.allocation, inventory.allocation_sha, "allocation inventory");
        }
        counters.preflight_wall_ns = wall_elapsed_ns(preflight_wall_start);
        counters.preflight_cpu_ns = cpu_time_ns() - preflight_cpu_start;

        // All registered bytes and all 27 generated rotations are verified before
        // the first encoder call.
        const uint64_t rotation_cpu_start = cpu_time_ns();
        const auto rotation_wall_start = std::chrono::steady_clock::now();
        for (const DatasetSpec &dataset : datasets) {
            for (int logical_seed = 0; logical_seed < 3; ++logical_seed) {
                static_cast<void>(verified_segmented_rotations(dataset, logical_seed, rotations));
                static_cast<void>(verified_whole_rotation(dataset, logical_seed, rotations));
            }
        }
        add_counter(
            counters.rotation_wall_ns,
            wall_elapsed_ns(rotation_wall_start),
            "rotation wall");
        add_counter(
            counters.rotation_cpu_ns,
            cpu_time_ns() - rotation_cpu_start,
            "rotation CPU");

        for (const DatasetSpec &dataset : datasets) {
            run_dataset(
                dataset,
                inventories.at(dataset.dataset_id),
                rotations,
                cli->output_dir,
                counters);
        }
        counters.total_wall_ns = wall_elapsed_ns(total_wall_start);
        counters.total_cpu_ns = cpu_time_ns() - total_cpu_start;
        write_run_manifest(cli->output_dir, "COMPLETE", counters, "frozen B1 measurement completed");
        std::cout << "V2-B1 measurement completed; run the frozen summarizer separately.\n";
        return 0;
    } catch (const std::exception &error) {
        counters.total_wall_ns = wall_elapsed_ns(total_wall_start);
        if (total_cpu_start != 0) {
            counters.total_cpu_ns = cpu_time_ns() - total_cpu_start;
        }
        if (cli.has_value() && output_initialized) {
            write_run_manifest(cli->output_dir, "STOPPED", counters, error.what());
        }
        std::cerr << "V2-B1 runner stopped: " << error.what() << '\n';
        return 1;
    }
}

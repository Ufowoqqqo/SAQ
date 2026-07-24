#include "admission.hpp"
#include "dataset_io.hpp"
#include "full_index.hpp"
#include "model.hpp"

#include "../a4_or_b/models.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/index_io.h>
#include <openssl/sha.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <time.h>
#include <vector>

namespace {

constexpr std::size_t kFitRows = 8192;
constexpr std::size_t kHead = 128;

double cpu_seconds() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return value.tv_sec + value.tv_nsec * 1e-9;
}

std::uint64_t peak_rss_bytes() {
    rusage value{};
    if (getrusage(RUSAGE_SELF, &value) != 0)
        throw std::runtime_error("getrusage");
    return static_cast<std::uint64_t>(value.ru_maxrss) * 1024;
}

struct Timer {
    double cpu = cpu_seconds();
    std::chrono::steady_clock::time_point wall =
            std::chrono::steady_clock::now();
};

std::pair<double, double> elapsed(const Timer& timer) {
    return {
            cpu_seconds() - timer.cpu,
            std::chrono::duration<double>(
                    std::chrono::steady_clock::now() -
                    timer.wall).count()};
}

void append_u64(
        std::vector<std::uint8_t>& bytes, std::uint64_t value) {
    for (std::size_t offset = 0; offset < 8; ++offset)
        bytes.push_back(
                static_cast<std::uint8_t>(
                        value >> (8 * offset)));
}

std::array<unsigned char, SHA256_DIGEST_LENGTH> row_hash(
        std::string_view dataset_id, std::size_t nlist,
        std::size_t row) {
    std::vector<std::uint8_t> bytes(
            dataset_id.begin(), dataset_id.end());
    append_u64(bytes, nlist);
    append_u64(bytes, row);
    append_u64(bytes, 20260724);
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    if (::SHA256(
                bytes.data(), bytes.size(), digest.data()) == nullptr)
        throw std::runtime_error("SHA-256 selection");
    return digest;
}

std::vector<std::size_t> selected_rows(
        std::string_view dataset_id, std::size_t nlist,
        std::size_t rows) {
    struct Entry {
        std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
        std::size_t row = 0;
    };
    std::vector<Entry> entries(rows);
    for (std::size_t row = 0; row < rows; ++row)
        entries[row] = {row_hash(dataset_id, nlist, row), row};
    const auto less = [](const Entry& left, const Entry& right) {
        return left.hash != right.hash
                ? left.hash < right.hash
                : left.row < right.row;
    };
    std::partial_sort(
            entries.begin(), entries.begin() + kFitRows,
            entries.end(), less);
    std::vector<std::size_t> result(kFitRows);
    for (std::size_t index = 0; index < kFitRows; ++index)
        result[index] = entries[index].row;
    return result;
}

std::vector<float> residual_fit(
        std::span<const float> learn, std::size_t dimensions,
        std::span<const float> centroids,
        std::span<const std::uint32_t> assignments,
        std::span<const std::size_t> rows) {
    if (learn.size() != assignments.size() * dimensions ||
        centroids.empty() ||
        centroids.size() % dimensions != 0 ||
        rows.size() != kFitRows)
        throw std::invalid_argument("S residual fit shape");
    std::vector<float> result(kFitRows * kHead);
    for (std::size_t index = 0; index < rows.size(); ++index) {
        const std::size_t row = rows[index];
        const std::size_t list = assignments[row];
        if (row >= assignments.size() ||
            list >= centroids.size() / dimensions)
            throw std::out_of_range("S residual fit row");
        for (std::size_t dimension = 0;
             dimension < kHead; ++dimension)
            result[index * kHead + dimension] =
                    learn[row * dimensions + dimension] -
                    centroids[list * dimensions + dimension];
    }
    return result;
}

void write_resources(
        const std::filesystem::path& output, const std::string& arm,
        std::size_t dimensions, std::size_t nlist,
        const structured2d::IndexByteAccounting& bytes,
        double train_cpu, double train_wall,
        double encode_cpu, double encode_wall,
        double write_cpu, double write_wall,
        double load_cpu, double load_wall) {
    std::ofstream record(
            output.string() + ".resources.tsv", std::ios::trunc);
    record << "arm_id\tdimensions\tnlist\tfit_rows\tbase_rows"
              "\tserialized_bytes\tmodel_bytes\tcentroid_bytes"
              "\tlist_offset_bytes\tcommon_id_bytes"
              "\tpacked_code_bytes_per_vector"
              "\ttrain_cpu_seconds\ttrain_wall_seconds"
              "\tencode_cpu_seconds\tencode_wall_seconds"
              "\twrite_cpu_seconds\twrite_wall_seconds"
              "\tload_cpu_seconds\tload_wall_seconds"
              "\tpeak_rss_bytes\n";
    record << std::setprecision(17)
           << arm << '\t' << dimensions << '\t' << nlist << '\t'
           << kFitRows << '\t' << 1000000 << '\t'
           << bytes.complete_serialized_bytes << '\t'
           << bytes.model_bytes << '\t' << bytes.centroid_bytes
           << '\t' << bytes.list_offset_bytes << '\t'
           << bytes.database_id_bytes << '\t'
           << static_cast<double>(bytes.packed_code_bytes) / 1000000
           << '\t' << train_cpu << '\t' << train_wall << '\t'
           << encode_cpu << '\t' << encode_wall << '\t'
           << write_cpu << '\t' << write_wall << '\t'
           << load_cpu << '\t' << load_wall << '\t'
           << peak_rss_bytes() << '\n';
    record.close();
    if (!record) throw std::runtime_error("write S resources");
}

void run(
        const std::string& dataset, std::size_t nlist,
        int word_bits, const std::filesystem::path& common,
        const std::filesystem::path& output) {
    const bool sift = dataset == "sift";
    if ((!sift && dataset != "gist") ||
        (nlist != 1024 && nlist != 4096) ||
        (word_bits != 4 && word_bits != 8) ||
        std::filesystem::exists(output))
        throw std::invalid_argument("S build arguments");
    const std::size_t dimensions = sift ? 128 : 960;
    const std::size_t learn_rows = sift ? 100000 : 500000;
    const auto nlist_dir =
            common / ("nlist_" + std::to_string(nlist));

    structured2d::admission::FvecsReader learn_reader(
            common / "learn_pca.fvecs", learn_rows, dimensions);
    const auto learn =
            structured2d::admission::read_all(learn_reader);
    const auto learn_assignments =
            structured2d::admission::read_u32(
                    nlist_dir / "learn_assignments.u32",
                    learn_rows);
    const std::string coarse_path =
            (nlist_dir / "coarse.faiss").string();
    std::unique_ptr<faiss::Index> coarse_owner(
            faiss::read_index(coarse_path.c_str()));
    auto* coarse =
            dynamic_cast<faiss::IndexFlatL2*>(
                    coarse_owner.get());
    if (coarse == nullptr ||
        coarse->d != static_cast<int>(dimensions) ||
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("S coarse type");
    const auto rows = selected_rows(
            sift ? "SIFT1M" : "GIST1M", nlist, learn_rows);
    const auto fit = residual_fit(
            learn, dimensions,
            std::span<const float>(
                    coarse->get_xb(), nlist * dimensions),
            learn_assignments, rows);

    double train_cpu = 0, train_wall = 0;
    structured2d::SharedAffineModel model;
    {
        const Timer timer;
        model = structured2d::train(
                fit, word_bits,
                structured2d::kFixedBudgetIterations);
        std::tie(train_cpu, train_wall) = elapsed(timer);
    }
    const auto evaluation = a4orb::evaluate(fit, model.expanded);
    if (!structured2d::fixed_budget_complete(model) ||
        !structured2d::pooled_occupancy_valid(
                model.expanded, evaluation) ||
        !evaluation.shape_valid || !evaluation.encoding_valid)
        throw std::runtime_error("S trained model validity");

    structured2d::admission::FvecsReader base_reader(
            common / "base_pca.fvecs", 1000000, dimensions);
    const auto base =
            structured2d::admission::read_all(base_reader);
    const auto assignments =
            structured2d::admission::read_u32(
                    nlist_dir / "base_assignments.u32", 1000000);
    std::vector<std::uint64_t> ids(1000000);
    std::iota(ids.begin(), ids.end(), std::uint64_t{0});

    double encode_cpu = 0, encode_wall = 0;
    structured2d::FullIndex index;
    {
        const Timer timer;
        index = structured2d::build_full_index(
                dimensions,
                std::span<const float>(
                        coarse->get_xb(), nlist * dimensions),
                assignments, ids, base, model);
        std::tie(encode_cpu, encode_wall) = elapsed(timer);
    }
    const auto bytes = structured2d::byte_accounting(index);
    double write_cpu = 0, write_wall = 0;
    {
        const Timer timer;
        structured2d::save_full_index(index, output);
        std::tie(write_cpu, write_wall) = elapsed(timer);
    }

    double load_cpu = 0, load_wall = 0;
    {
        const Timer timer;
        auto loaded = structured2d::load_full_index(output);
        structured2d::admission::FvecsReader query_reader(
                common / "synthetic_pca.fvecs", 64, dimensions);
        const auto queries =
                structured2d::admission::read_all(query_reader);
        const std::size_t max_probe =
                structured2d::admission::frozen_nprobes(nlist).back();
        const auto selected =
                structured2d::admission::read_u32(
                        nlist_dir /
                                "synthetic_selected_lists.u32",
                        64 * max_probe);
        const std::array<std::uint32_t, 1> first_list{
                selected.front()};
        const auto before = structured2d::search_preassigned(
                index,
                std::span<const float>(
                        queries.data(), dimensions),
                first_list, 100);
        const auto after = structured2d::search_preassigned(
                loaded,
                std::span<const float>(
                        queries.data(), dimensions),
                first_list, 100);
        if (before != after ||
            structured2d::byte_accounting(loaded)
                            .complete_serialized_bytes !=
                    bytes.complete_serialized_bytes)
            throw std::runtime_error("S load/search parity");
        std::tie(load_cpu, load_wall) = elapsed(timer);
    }
    write_resources(
            output,
            "S128_B" + std::to_string(word_bits),
            dimensions, nlist, bytes,
            train_cpu, train_wall, encode_cpu, encode_wall,
            write_cpu, write_wall, load_cpu, load_wall);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: structured_2d_build_s_arm "
                    "<sift|gist> <nlist> <4|8> "
                    "<common_directory> <output_index>");
        run(
                argv[1], std::stoull(argv[2]), std::stoi(argv[3]),
                argv[4], argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_build_s_arm: "
                  << error.what() << '\n';
        return 1;
    }
}

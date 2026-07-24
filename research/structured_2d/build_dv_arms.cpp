#include "admission.hpp"
#include "dataset_io.hpp"
#include "faiss_pool.hpp"

#include "../a4_or_b/models.hpp"

#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>
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
#include <tuple>
#include <vector>

namespace {

constexpr std::size_t kFitRows = 8192;
constexpr std::size_t kHead = 128;
constexpr std::size_t kGroups = 64;

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
        std::string_view dataset, std::size_t nlist,
        std::size_t row) {
    std::vector<std::uint8_t> bytes(
            dataset.begin(), dataset.end());
    append_u64(bytes, nlist);
    append_u64(bytes, row);
    append_u64(bytes, 20260724);
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    if (::SHA256(
                bytes.data(), bytes.size(), digest.data()) == nullptr)
        throw std::runtime_error("DV SHA-256");
    return digest;
}

std::vector<std::size_t> select_rows(
        std::string_view dataset, std::size_t nlist,
        std::size_t rows) {
    struct Entry {
        std::array<unsigned char, SHA256_DIGEST_LENGTH> hash{};
        std::size_t row = 0;
    };
    std::vector<Entry> entries(rows);
    for (std::size_t row = 0; row < rows; ++row)
        entries[row] = {row_hash(dataset, nlist, row), row};
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

std::vector<float> fit_residuals(
        std::span<const float> learn,
        std::span<const std::uint32_t> assignments,
        std::span<const float> centroids,
        std::span<const std::size_t> rows) {
    if (learn.size() != assignments.size() * kHead ||
        centroids.empty() || centroids.size() % kHead != 0 ||
        rows.size() != kFitRows)
        throw std::invalid_argument("DV fit shape");
    std::vector<float> fit(kFitRows * kHead);
    for (std::size_t index = 0; index < kFitRows; ++index) {
        const std::size_t row = rows[index];
        if (row >= assignments.size() ||
            assignments[row] >= centroids.size() / kHead)
            throw std::out_of_range("DV selected row");
        const float* centroid =
                centroids.data() +
                static_cast<std::size_t>(assignments[row]) *
                        kHead;
        for (std::size_t dimension = 0;
             dimension < kHead; ++dimension)
            fit[index * kHead + dimension] =
                    learn[row * kHead + dimension] -
                    centroid[dimension];
    }
    return fit;
}

std::vector<float> flatten_centers(
        const a4orb::Model& model, int bits) {
    const std::size_t centers = std::size_t{1} << bits;
    if (model.blocks.size() != kGroups ||
        model.word_bits != bits)
        throw std::invalid_argument("DV model blocks");
    std::vector<float> result(
            kGroups * centers * 2);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto& block = model.blocks[group];
        if (block.dimension != 2 ||
            block.centers != centers ||
            block.values.size() != centers * 2)
            throw std::runtime_error("DV block shape");
        std::copy(
                block.values.begin(), block.values.end(),
                result.begin() + group * centers * 2);
    }
    return result;
}

void write_radices(
        const std::filesystem::path& path,
        const a4orb::Model& model) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    for (const auto& block : model.blocks) {
        const std::uint16_t value =
                static_cast<std::uint16_t>(block.radix);
        output.write(
                reinterpret_cast<const char*>(&value),
                sizeof(value));
    }
    output.close();
    if (!output ||
        std::filesystem::file_size(path) !=
                kGroups * sizeof(std::uint16_t))
        throw std::runtime_error("write D radices");
}

void write_resources(
        const std::filesystem::path& output,
        const std::string& id, int bits, std::size_t nlist,
        double train_cpu, double train_wall,
        double add_cpu, double add_wall,
        double write_cpu, double write_wall,
        double load_cpu, double load_wall) {
    std::ofstream record(
            output.string() + ".resources.tsv", std::ios::trunc);
    record << "arm_id\tdimensions\tnlist\tfit_rows\tbase_rows"
              "\tserialized_bytes\tcommon_id_bytes"
              "\tpacked_code_bytes_per_vector"
              "\ttrain_cpu_seconds\ttrain_wall_seconds"
              "\tadd_cpu_seconds\tadd_wall_seconds"
              "\twrite_cpu_seconds\twrite_wall_seconds"
              "\tload_cpu_seconds\tload_wall_seconds"
              "\tpeak_rss_bytes\n";
    record << std::setprecision(17)
           << id << '\t' << kHead << '\t' << nlist << '\t'
           << kFitRows << '\t' << 1000000 << '\t'
           << std::filesystem::file_size(output) << '\t'
           << 1000000 * sizeof(faiss::idx_t) << '\t'
           << bits * kGroups / 8 << '\t'
           << train_cpu << '\t' << train_wall << '\t'
           << add_cpu << '\t' << add_wall << '\t'
           << write_cpu << '\t' << write_wall << '\t'
           << load_cpu << '\t' << load_wall << '\t'
           << peak_rss_bytes() << '\n';
    record.close();
    if (!record) throw std::runtime_error("write DV resources");
}

void build_one(
        const std::string& id, const a4orb::Model& model,
        int bits, std::size_t nlist, faiss::IndexFlatL2& coarse,
        std::span<const float> base,
        std::span<const std::uint32_t> assignments,
        const std::filesystem::path& output,
        double train_cpu, double train_wall) {
    if (std::filesystem::exists(output))
        throw std::invalid_argument("DV output exists");
    faiss::IndexIVFPQ index(
            &coarse, kHead, nlist, kGroups, bits,
            faiss::METRIC_L2);
    index.own_fields = false;
    index.use_precomputed_table = 0;
    index.pq.centroids = flatten_centers(model, bits);
    index.is_trained = true;

    double add_cpu = 0, add_wall = 0;
    {
        const Timer timer;
        structured2d::admission::add_native_faiss_arm(
                index, base, assignments, kHead);
        structured2d::admission::verify_native_faiss_layout(
                index, assignments);
        std::tie(add_cpu, add_wall) = elapsed(timer);
    }
    double write_cpu = 0, write_wall = 0;
    {
        const Timer timer;
        faiss::write_index(&index, output.c_str());
        std::tie(write_cpu, write_wall) = elapsed(timer);
    }
    double load_cpu = 0, load_wall = 0;
    {
        const Timer timer;
        std::unique_ptr<faiss::Index> loaded_owner(
                faiss::read_index(output.c_str()));
        auto* loaded =
                dynamic_cast<faiss::IndexIVFPQ*>(
                        loaded_owner.get());
        if (loaded == nullptr)
            throw std::runtime_error("loaded DV type");
        structured2d::admission::verify_native_faiss_layout(
                *loaded, assignments);
        if (loaded->pq.centroids != index.pq.centroids)
            throw std::runtime_error("DV centroid load parity");
        std::tie(load_cpu, load_wall) = elapsed(timer);
    }
    if (id.rfind("D128", 0) == 0)
        write_radices(output.string() + ".radix.u16", model);
    write_resources(
            output, id, bits, nlist,
            train_cpu, train_wall, add_cpu, add_wall,
            write_cpu, write_wall, load_cpu, load_wall);
}

void run(
        const std::string& dataset, std::size_t nlist, int bits,
        const std::filesystem::path& common,
        const std::filesystem::path& output_directory) {
    const bool sift = dataset == "sift";
    if ((!sift && dataset != "gist") ||
        (nlist != 1024 && nlist != 4096) ||
        (bits != 4 && bits != 8))
        throw std::invalid_argument("DV arguments");
    const std::size_t learn_rows = sift ? 100000 : 500000;
    const std::filesystem::path view =
            sift ? common :
            std::filesystem::path(
                    common.string() + "_head128");
    const auto nlist_dir =
            view / ("nlist_" + std::to_string(nlist));
    structured2d::admission::FvecsReader learn_reader(
            view / "learn_pca.fvecs", learn_rows, kHead);
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
        coarse->ntotal != static_cast<faiss::idx_t>(nlist))
        throw std::runtime_error("DV coarse type");
    const auto rows = select_rows(
            sift ? "SIFT1M" : "GIST1M",
            nlist, learn_rows);
    const auto fit = fit_residuals(
            learn, learn_assignments,
            std::span<const float>(
                    coarse->get_xb(), nlist * kHead),
            rows);

    double d_cpu = 0, d_wall = 0;
    a4orb::Model dyadic;
    {
        const Timer timer;
        const auto curves = a4orb::fit_curves(fit, 1024);
        dyadic = a4orb::allocate_scalar(curves, bits, true);
        std::tie(d_cpu, d_wall) = elapsed(timer);
    }
    const auto d_evaluation = a4orb::evaluate(fit, dyadic);
    if (!d_evaluation.shape_valid ||
        !d_evaluation.encoding_valid ||
        d_evaluation.collisions != 0)
        throw std::runtime_error("D model validity");

    double v_cpu = 0, v_wall = 0;
    a4orb::Model independent;
    {
        const Timer timer;
        independent = a4orb::train_v(fit, bits, dyadic);
        std::tie(v_cpu, v_wall) = elapsed(timer);
    }
    const auto v_evaluation =
            a4orb::evaluate(fit, independent);
    if (!v_evaluation.shape_valid ||
        !v_evaluation.encoding_valid ||
        v_evaluation.collisions != 0)
        throw std::runtime_error("V model validity");

    structured2d::admission::FvecsReader base_reader(
            view / "base_pca.fvecs", 1000000, kHead);
    const auto base =
            structured2d::admission::read_all(base_reader);
    const auto assignments =
            structured2d::admission::read_u32(
                    nlist_dir / "base_assignments.u32", 1000000);
    build_one(
            "D128_B" + std::to_string(bits), dyadic,
            bits, nlist, *coarse, base, assignments,
            output_directory /
                    ("D128_B" + std::to_string(bits) + ".faiss"),
            d_cpu, d_wall);
    build_one(
            "V128_B" + std::to_string(bits), independent,
            bits, nlist, *coarse, base, assignments,
            output_directory /
                    ("V128_B" + std::to_string(bits) + ".faiss"),
            v_cpu, v_wall);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: structured_2d_build_dv_arms "
                    "<sift|gist> <nlist> <4|8> "
                    "<common_directory> <output_directory>");
        run(
                argv[1], std::stoull(argv[2]), std::stoi(argv[3]),
                argv[4], argv[5]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_build_dv_arms: "
                  << error.what() << '\n';
        return 1;
    }
}

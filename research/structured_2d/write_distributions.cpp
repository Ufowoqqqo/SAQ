#include "admission.hpp"
#include "dataset_io.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using structured2d::admission::CandidateDistribution;
using structured2d::admission::Dataset;
using structured2d::admission::Quantiles;
using structured2d::admission::SizeBins;

void write_quantiles(
        std::ofstream& output, const Quantiles& value) {
    output << '\t' << value.minimum << '\t' << value.p10
           << '\t' << value.p25 << '\t' << value.median
           << '\t' << value.p75 << '\t' << value.p90
           << '\t' << value.p95 << '\t' << value.p99
           << '\t' << value.maximum;
}

void write_bins(std::ofstream& output, const SizeBins& value) {
    output << '\t' << value.below_256
           << '\t' << value.from_256_to_1023
           << '\t' << value.from_1024_to_8191
           << '\t' << value.at_least_8192;
}

void write_quantile_header(
        std::ofstream& output, const std::string& prefix) {
    for (const char* suffix :
         {"min", "p10", "p25", "median", "p75",
          "p90", "p95", "p99", "max"})
        output << '\t' << prefix << '_' << suffix;
}

void write_bin_header(
        std::ofstream& output, const std::string& prefix) {
    output << '\t' << prefix << "_lt256"
           << '\t' << prefix << "_256_1023"
           << '\t' << prefix << "_1024_8191"
           << '\t' << prefix << "_ge8192";
}

void write_header(std::ofstream& output) {
    output << "dataset\tnlist\tnprobe";
    write_quantile_header(output, "candidates");
    write_quantile_header(output, "padded_candidates");
    write_quantile_header(output, "selected_list_size");
    write_bin_header(output, "query_fraction");
    write_bin_header(output, "selected_list_fraction");
    write_bin_header(output, "candidate_weighted_list_fraction");
    output << '\n';
}

void write_row(
        std::ofstream& output, const std::string& dataset,
        std::size_t nlist, std::size_t nprobe,
        const CandidateDistribution& distribution) {
    output << dataset << '\t' << nlist << '\t' << nprobe;
    write_quantiles(output, distribution.candidates_per_query);
    write_quantiles(
            output, distribution.padded_candidates_per_query);
    write_quantiles(output, distribution.selected_list_sizes);
    write_bins(output, distribution.query_fractions);
    write_bins(output, distribution.selected_list_fractions);
    write_bins(
            output,
            distribution.candidate_weighted_list_fractions);
    output << '\n';
}

void run(
        const std::filesystem::path& root,
        const std::filesystem::path& output_path) {
    constexpr std::size_t queries = 64;
    std::ofstream output(output_path, std::ios::trunc);
    if (!output)
        throw std::runtime_error("open distribution output");
    output << std::setprecision(17);
    write_header(output);

    for (const auto& [dataset_name, dataset] :
         std::array<std::pair<std::string, Dataset>, 2>{
                 std::pair{"sift", Dataset::Sift1M},
                 std::pair{"gist", Dataset::Gist1M}}) {
        (void)dataset;
        for (const std::size_t nlist : {1024UL, 4096UL}) {
            const auto directory =
                    root / dataset_name /
                    ("nlist_" + std::to_string(nlist));
            const auto sizes =
                    structured2d::admission::read_u64(
                            directory / "list_sizes.u64", nlist);
            const auto probes =
                    structured2d::admission::frozen_nprobes(nlist);
            const std::size_t max_probe = probes.back();
            const auto all_selected =
                    structured2d::admission::read_u32(
                            directory /
                                    "synthetic_selected_lists.u32",
                            queries * max_probe);
            for (const std::size_t nprobe : probes) {
                std::vector<std::uint32_t> selected(
                        queries * nprobe);
                for (std::size_t query = 0;
                     query < queries; ++query)
                    std::copy_n(
                            all_selected.begin() +
                                    query * max_probe,
                            nprobe,
                            selected.begin() + query * nprobe);
                const auto distribution =
                        structured2d::admission::
                                candidate_distribution(
                                        sizes, selected, queries,
                                        nprobe);
                write_row(
                        output, dataset_name, nlist, nprobe,
                        distribution);
            }
        }
    }
    output.close();
    if (!output)
        throw std::runtime_error("write distribution output");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3)
            throw std::invalid_argument(
                    "usage: structured_2d_write_distributions "
                    "<admission_root> <output_tsv>");
        run(argv[1], argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_write_distributions: "
                  << error.what() << '\n';
        return 1;
    }
}

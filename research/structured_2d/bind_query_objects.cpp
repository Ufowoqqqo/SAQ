#include "dataset_io.hpp"

#include <algorithm>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc != 7)
            throw std::invalid_argument(
                    "usage: structured_2d_bind_query_objects "
                    "<dataset> <query_fvecs> <gt_ivecs> "
                    "<rows> <dimensions> <database_rows>");
        const std::string dataset = argv[1];
        const std::filesystem::path query_path = argv[2];
        const std::filesystem::path gt_path = argv[3];
        const std::size_t rows = std::stoull(argv[4]);
        const std::size_t dimensions = std::stoull(argv[5]);
        const std::uint32_t database_rows =
                static_cast<std::uint32_t>(std::stoul(argv[6]));
        structured2d::admission::FvecsReader query_reader(
                query_path, rows, dimensions);
        const auto queries =
                structured2d::admission::read_all(query_reader);
        const auto truth = structured2d::admission::read_ivecs(
                gt_path, rows, 100, database_rows, true);
        const auto [minimum, maximum] =
                std::minmax_element(truth.begin(), truth.end());
        std::cout
                << "dataset\tquery_path\tquery_rows"
                   "\tquery_dimensions\tquery_bytes"
                   "\tgroundtruth_path\tgroundtruth_rows"
                   "\tgroundtruth_dimensions\tgroundtruth_bytes"
                   "\tgroundtruth_min_id\tgroundtruth_max_id\n"
                << dataset << '\t' << query_path << '\t'
                << rows << '\t' << dimensions << '\t'
                << std::filesystem::file_size(query_path) << '\t'
                << gt_path << '\t' << rows << "\t100\t"
                << std::filesystem::file_size(gt_path) << '\t'
                << *minimum << '\t' << *maximum << '\n';
        return queries.empty() ? 1 : 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_bind_query_objects: "
                  << error.what() << '\n';
        return 1;
    }
}

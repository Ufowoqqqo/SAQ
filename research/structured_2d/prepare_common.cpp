#include "common.hpp"

#include <exception>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

structured2d::admission::DatasetBuildSpec parse(int argc, char** argv) {
    if (argc != 5)
        throw std::invalid_argument(
                "usage: structured_2d_prepare_common "
                "<sift|gist> <learn.fvecs> <base.fvecs> <output>");
    structured2d::admission::DatasetBuildSpec spec;
    const std::string dataset = argv[1];
    if (dataset == "sift") {
        spec.dataset = structured2d::admission::Dataset::Sift1M;
        spec.dimensions = 128;
        spec.learn_rows = 100000;
        spec.base_rows = 1000000;
        spec.block_rows = 16384;
    } else if (dataset == "gist") {
        spec.dataset = structured2d::admission::Dataset::Gist1M;
        spec.dimensions = 960;
        spec.learn_rows = 500000;
        spec.base_rows = 1000000;
        spec.block_rows = 4096;
    } else {
        throw std::invalid_argument("dataset must be sift or gist");
    }
    spec.learn_path = argv[2];
    spec.base_path = argv[3];
    spec.output_directory = argv[4];
    return spec;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        structured2d::admission::prepare_common_state(
                parse(argc, argv));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_prepare_common: "
                  << error.what() << '\n';
        return 1;
    }
}

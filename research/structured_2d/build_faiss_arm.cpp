#include "faiss_pool.hpp"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc != 6)
            throw std::invalid_argument(
                    "usage: structured_2d_build_faiss_arm "
                    "<sift|gist|gist_head> <nlist> <arm_id> "
                    "<common_directory> <output_index>");
        const std::string dataset = argv[1];
        const std::size_t dimensions =
                dataset == "sift" || dataset == "gist_head" ? 128 :
                dataset == "gist" ? 960 :
                throw std::invalid_argument("dataset");
        const std::size_t learn_rows =
                dataset == "sift" ? 100000 :
                dataset == "gist" || dataset == "gist_head"
                ? 500000 :
                throw std::invalid_argument("dataset");
        const std::size_t nlist = std::stoull(argv[2]);
        structured2d::admission::NativeBuildSpec spec;
        spec.arm =
                structured2d::admission::parse_native_faiss_arm(
                        argv[3], dimensions, nlist);
        spec.common_directory = argv[4];
        spec.output_index = argv[5];
        spec.learn_rows = learn_rows;
        spec.base_rows = 1000000;
        structured2d::admission::build_native_faiss_arm(spec);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "structured_2d_build_faiss_arm: "
                  << error.what() << '\n';
        return 1;
    }
}

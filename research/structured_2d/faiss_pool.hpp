#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <vector>

namespace faiss {
struct Index;
struct IndexFlatL2;
struct IndexIVF;
}  // namespace faiss

namespace structured2d::admission {

enum class FaissArmKind {
    IvfFlat,
    IvfPq,
    IvfPqFastScan,
    IvfRaBitQ,
    IvfRaBitQFastScan,
};

struct FaissArmConfig {
    std::string id;
    FaissArmKind kind{};
    std::size_t dimensions = 0;
    std::size_t nlist = 0;
    std::size_t subquantizers = 0;
    std::size_t bits = 0;
};

FaissArmConfig parse_native_faiss_arm(
        const std::string& id, std::size_t dimensions,
        std::size_t nlist);

std::unique_ptr<faiss::IndexIVF> make_native_faiss_arm(
        const FaissArmConfig& config, faiss::IndexFlatL2* coarse,
        std::size_t learn_rows);

void train_native_faiss_arm(
        faiss::IndexIVF& index,
        std::span<const float> transformed_learn,
        std::span<const std::uint32_t> assignments,
        std::size_t dimensions);

void add_native_faiss_arm(
        faiss::IndexIVF& index,
        std::span<const float> transformed_base,
        std::span<const std::uint32_t> assignments,
        std::size_t dimensions);

void verify_native_faiss_layout(
        const faiss::IndexIVF& index,
        std::span<const std::uint32_t> assignments);

struct NativeBuildSpec {
    FaissArmConfig arm;
    std::filesystem::path common_directory;
    std::filesystem::path output_index;
    std::size_t learn_rows = 0;
    std::size_t base_rows = 0;
};

void build_native_faiss_arm(const NativeBuildSpec& spec);

}  // namespace structured2d::admission

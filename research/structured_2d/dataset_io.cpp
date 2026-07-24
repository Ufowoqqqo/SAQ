#include "dataset_io.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace structured2d::admission {
namespace {

std::uint64_t checked_product(
        std::uint64_t left, std::uint64_t right,
        const char* message) {
    if (right != 0 &&
        left > std::numeric_limits<std::uint64_t>::max() / right)
        throw std::overflow_error(message);
    return left * right;
}

void require_finite(std::span<const float> values) {
    if (!std::all_of(
                values.begin(), values.end(),
                [](float value) { return std::isfinite(value); }))
        throw std::runtime_error("non-finite fvecs value");
}

}  // namespace

FvecsReader::FvecsReader(
        const std::filesystem::path& path,
        std::size_t expected_rows,
        std::size_t expected_dimensions)
        : path_(path),
          input_(path, std::ios::binary),
          rows_(expected_rows),
          dimensions_(expected_dimensions) {
    if (!input_ || rows_ == 0 || dimensions_ == 0)
        throw std::invalid_argument("fvecs input");
    const std::uint64_t row_bytes =
            checked_product(
                    dimensions_ + 1, sizeof(std::uint32_t),
                    "fvecs row bytes");
    const std::uint64_t expected_bytes =
            checked_product(rows_, row_bytes, "fvecs file bytes");
    if (std::filesystem::file_size(path_) != expected_bytes)
        throw std::runtime_error("fvecs file size");
}

std::size_t FvecsReader::read(std::span<float> output) {
    if (output.empty() || output.size() % dimensions_ != 0)
        throw std::invalid_argument("fvecs output shape");
    const std::size_t requested = output.size() / dimensions_;
    const std::size_t count = std::min(requested, rows_ - position_);
    for (std::size_t row = 0; row < count; ++row) {
        std::uint32_t dimension = 0;
        input_.read(
                reinterpret_cast<char*>(&dimension),
                sizeof(dimension));
        if (!input_ || dimension != dimensions_)
            throw std::runtime_error("fvecs row dimension");
        float* target = output.data() + row * dimensions_;
        input_.read(
                reinterpret_cast<char*>(target),
                dimensions_ * sizeof(float));
        if (!input_) throw std::runtime_error("truncated fvecs row");
        require_finite(
                std::span<const float>(target, dimensions_));
    }
    position_ += count;
    if (position_ == rows_ &&
        input_.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("trailing fvecs bytes");
    return count;
}

void FvecsReader::rewind() {
    input_.close();
    input_.open(path_, std::ios::binary);
    if (!input_) throw std::runtime_error("rewind fvecs");
    position_ = 0;
}

std::vector<float> read_all(FvecsReader& reader) {
    std::vector<float> result(
            checked_product(
                    reader.rows(), reader.dimensions(),
                    "fvecs allocation"));
    const std::size_t rows = reader.read(result);
    if (rows != reader.rows())
        throw std::runtime_error("short fvecs file");
    return result;
}

FvecsWriter::FvecsWriter(
        const std::filesystem::path& path,
        std::size_t dimensions)
        : output_(path, std::ios::binary | std::ios::trunc),
          dimensions_(dimensions) {
    if (!output_ || dimensions_ == 0 ||
        dimensions_ > std::numeric_limits<std::uint32_t>::max())
        throw std::invalid_argument("fvecs output");
}

void FvecsWriter::write(std::span<const float> vectors) {
    if (closed_ || vectors.empty() ||
        vectors.size() % dimensions_ != 0)
        throw std::invalid_argument("fvecs write shape");
    require_finite(vectors);
    const std::uint32_t dimension =
            static_cast<std::uint32_t>(dimensions_);
    const std::size_t rows = vectors.size() / dimensions_;
    for (std::size_t row = 0; row < rows; ++row) {
        output_.write(
                reinterpret_cast<const char*>(&dimension),
                sizeof(dimension));
        output_.write(
                reinterpret_cast<const char*>(
                        vectors.data() + row * dimensions_),
                dimensions_ * sizeof(float));
        if (!output_) throw std::runtime_error("write fvecs");
    }
    rows_written_ += rows;
}

void FvecsWriter::close() {
    if (closed_) return;
    output_.close();
    if (!output_) throw std::runtime_error("close fvecs");
    closed_ = true;
}

void write_u32(
        const std::filesystem::path& path,
        std::span<const std::uint32_t> values) {
    if (values.empty()) throw std::invalid_argument("empty u32 output");
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    output.write(
            reinterpret_cast<const char*>(values.data()),
            values.size_bytes());
    output.close();
    if (!output ||
        std::filesystem::file_size(path) != values.size_bytes())
        throw std::runtime_error("write u32");
}

std::vector<std::uint32_t> read_u32(
        const std::filesystem::path& path,
        std::size_t expected_values) {
    if (expected_values == 0 ||
        std::filesystem::file_size(path) !=
                expected_values * sizeof(std::uint32_t))
        throw std::runtime_error("u32 file size");
    std::vector<std::uint32_t> result(expected_values);
    std::ifstream input(path, std::ios::binary);
    input.read(
            reinterpret_cast<char*>(result.data()),
            result.size() * sizeof(std::uint32_t));
    if (!input || input.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("read u32");
    return result;
}

std::vector<std::uint64_t> read_u64(
        const std::filesystem::path& path,
        std::size_t expected_values) {
    std::ifstream input(path, std::ios::binary);
    if (!input)
        throw std::runtime_error("open u64 input");
    std::vector<std::uint64_t> values(expected_values);
    input.read(
            reinterpret_cast<char*>(values.data()),
            static_cast<std::streamsize>(
                    values.size() * sizeof(std::uint64_t)));
    if (!input || input.peek() != std::ifstream::traits_type::eof())
        throw std::runtime_error("u64 input shape");
    return values;
}

}  // namespace structured2d::admission

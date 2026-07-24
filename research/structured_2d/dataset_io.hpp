#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <span>
#include <vector>

namespace structured2d::admission {

class FvecsReader {
  public:
    FvecsReader(
            const std::filesystem::path& path,
            std::size_t expected_rows,
            std::size_t expected_dimensions);

    std::size_t rows() const { return rows_; }
    std::size_t dimensions() const { return dimensions_; }
    std::size_t position() const { return position_; }

    std::size_t read(std::span<float> output);
    void rewind();

  private:
    std::filesystem::path path_;
    std::ifstream input_;
    std::size_t rows_ = 0;
    std::size_t dimensions_ = 0;
    std::size_t position_ = 0;
};

std::vector<float> read_all(FvecsReader& reader);

class FvecsWriter {
  public:
    FvecsWriter(
            const std::filesystem::path& path,
            std::size_t dimensions);
    void write(std::span<const float> vectors);
    void close();
    std::size_t rows_written() const { return rows_written_; }

  private:
    std::ofstream output_;
    std::size_t dimensions_ = 0;
    std::size_t rows_written_ = 0;
    bool closed_ = false;
};

void write_u32(
        const std::filesystem::path& path,
        std::span<const std::uint32_t> values);
std::vector<std::uint32_t> read_u32(
        const std::filesystem::path& path,
        std::size_t expected_values);
std::vector<std::uint64_t> read_u64(
        const std::filesystem::path& path,
        std::size_t expected_values);
std::vector<std::uint32_t> read_ivecs(
        const std::filesystem::path& path,
        std::size_t expected_rows,
        std::size_t expected_dimensions,
        std::uint32_t exclusive_upper_bound,
        bool require_unique_rows);

}  // namespace structured2d::admission

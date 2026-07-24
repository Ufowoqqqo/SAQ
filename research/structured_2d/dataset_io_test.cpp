#include "dataset_io.hpp"

#include <bit>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace structured2d::admission;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void io_test() {
    const auto directory =
            std::filesystem::temp_directory_path();
    const auto fvecs = directory /
            "structured_2d_dataset_io_test.fvecs";
    const auto u32 = directory /
            "structured_2d_dataset_io_test.u32";
    const auto ivecs = directory /
            "structured_2d_dataset_io_test.ivecs";
    std::filesystem::remove(fvecs);
    std::filesystem::remove(u32);
    std::filesystem::remove(ivecs);

    const std::vector<float> source{
            1, 2, 3, 4, 5, 6,
            -1, -2, -3, -4, -5, -6,
            0.25F, 0.5F, 0.75F, 1, 1.25F, 1.5F};
    FvecsWriter writer(fvecs, 6);
    writer.write(std::span<const float>(source.data(), 12));
    writer.write(std::span<const float>(source.data() + 12, 6));
    require(writer.rows_written() == 3, "writer row count");
    writer.close();

    FvecsReader reader(fvecs, 3, 6);
    std::vector<float> first(12);
    require(reader.read(first) == 2, "block read");
    require(first == std::vector<float>(
                             source.begin(), source.begin() + 12),
            "block contents");
    std::vector<float> last(6);
    require(reader.read(last) == 1, "last read");
    require(last == std::vector<float>(
                            source.begin() + 12, source.end()),
            "last contents");
    reader.rewind();
    require(read_all(reader) == source, "read-all replay");

    const std::vector<std::uint32_t> ids{
            7, 0, 99, std::numeric_limits<std::uint32_t>::max()};
    write_u32(u32, ids);
    require(read_u32(u32, ids.size()) == ids, "u32 replay");

    {
        std::ofstream output(ivecs, std::ios::binary);
        const std::uint32_t dimensions = 3;
        const std::uint32_t rows[2][3]{
                {1, 3, 5}, {0, 2, 4}};
        for (const auto& row : rows) {
            output.write(
                    reinterpret_cast<const char*>(&dimensions),
                    sizeof(dimensions));
            output.write(
                    reinterpret_cast<const char*>(row),
                    sizeof(row));
        }
    }
    require(
            read_ivecs(ivecs, 2, 3, 6, true) ==
                    std::vector<std::uint32_t>{
                            1, 3, 5, 0, 2, 4},
            "ivecs replay");

    bool rejected = false;
    try {
        FvecsReader wrong(fvecs, 4, 6);
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    require(rejected, "fvecs size rejection");

    std::filesystem::remove(fvecs);
    std::filesystem::remove(u32);
    std::filesystem::remove(ivecs);
}

}  // namespace

int main() {
    try {
        io_test();
        std::cout << "PASS structured_2d_dataset_io_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

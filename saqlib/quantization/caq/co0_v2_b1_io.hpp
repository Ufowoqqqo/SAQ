#pragma once

#include <array>
#include <bit>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <openssl/evp.h>
#include <sys/resource.h>
#include <zlib.h>

#include "defines.hpp"
#include "quantization/caq/co0_v2_measurement.hpp"

namespace saqlib::caq_validation {

struct Co0V2VectorFileShape {
    uint64_t rows = 0;
    uint32_t dimension = 0;
    uint64_t size_bytes = 0;
};

struct Co0V2SampleRow {
    std::string dataset_id;
    uint32_t cell_id = 0;
    uint32_t rank_in_cell = 0;
    uint32_t vector_id = 0;
};

struct Co0V2PairRow {
    std::string dataset_id;
    uint32_t cell_id = 0;
    uint32_t pair_rank = 0;
    uint32_t stored_vector_id = 0;
    uint32_t query_vector_id = 0;
};

struct Co0V2CodeLocation {
    uint64_t bit_offset = 0;
    uint64_t bit_length = 0;
    std::string sha256;
};

namespace io_detail {

inline void require_io(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

class DigestContext {
  public:
    DigestContext()
        : context_(EVP_MD_CTX_new()) {
        if (context_ == nullptr || EVP_DigestInit_ex(context_, EVP_sha256(), nullptr) != 1) {
            if (context_ != nullptr) {
                EVP_MD_CTX_free(context_);
            }
            throw std::runtime_error("cannot initialize SHA-256 context");
        }
    }

    DigestContext(const DigestContext &) = delete;
    DigestContext &operator=(const DigestContext &) = delete;

    ~DigestContext() {
        EVP_MD_CTX_free(context_);
    }

    void update(std::span<const uint8_t> bytes) {
        if (!bytes.empty() && EVP_DigestUpdate(context_, bytes.data(), bytes.size()) != 1) {
            throw std::runtime_error("SHA-256 update failed");
        }
    }

    std::array<uint8_t, 32> finish() {
        std::array<uint8_t, 32> digest{};
        unsigned int length = 0;
        if (EVP_DigestFinal_ex(context_, digest.data(), &length) != 1 ||
            length != digest.size()) {
            throw std::runtime_error("SHA-256 finalization failed");
        }
        return digest;
    }

  private:
    EVP_MD_CTX *context_ = nullptr;
};

inline std::string hex_digest(std::span<const uint8_t> digest) {
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (uint8_t byte : digest) {
        output << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return output.str();
}

inline uint32_t parse_u32(std::string_view value, std::string_view field) {
    require_io(!value.empty(), std::string(field) + " is empty");
    uint64_t parsed = 0;
    for (char character : value) {
        require_io(
            character >= '0' && character <= '9',
            std::string(field) + " is not an unsigned decimal integer");
        parsed = parsed * 10 + static_cast<unsigned int>(character - '0');
        require_io(parsed <= std::numeric_limits<uint32_t>::max(), std::string(field) + " overflows uint32");
    }
    return static_cast<uint32_t>(parsed);
}

inline std::vector<std::string> split_csv(std::string_view line) {
    std::vector<std::string> fields;
    size_t begin = 0;
    while (begin <= line.size()) {
        const size_t comma = line.find(',', begin);
        const size_t end = comma == std::string_view::npos ? line.size() : comma;
        fields.emplace_back(line.substr(begin, end - begin));
        if (comma == std::string_view::npos) {
            break;
        }
        begin = comma + 1;
    }
    return fields;
}

inline uint32_t little_u32(const std::array<uint8_t, 4> &bytes) {
    return static_cast<uint32_t>(bytes[0]) |
           (static_cast<uint32_t>(bytes[1]) << 8U) |
           (static_cast<uint32_t>(bytes[2]) << 16U) |
           (static_cast<uint32_t>(bytes[3]) << 24U);
}

} // namespace io_detail

inline std::string co0_v2_sha256_bytes(std::span<const uint8_t> bytes) {
    io_detail::DigestContext context;
    context.update(bytes);
    const auto digest = context.finish();
    return io_detail::hex_digest(digest);
}

inline std::string co0_v2_sha256_file(const std::filesystem::path &path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open file for SHA-256: " + path.string());
    }
    io_detail::DigestContext context;
    std::array<uint8_t, 1U << 20U> buffer{};
    while (input) {
        input.read(reinterpret_cast<char *>(buffer.data()), buffer.size());
        const std::streamsize count = input.gcount();
        if (count > 0) {
            context.update(std::span<const uint8_t>(buffer.data(), static_cast<size_t>(count)));
        }
    }
    if (!input.eof()) {
        throw std::runtime_error("failed while hashing file: " + path.string());
    }
    const auto digest = context.finish();
    return io_detail::hex_digest(digest);
}

inline std::string co0_v2_sha256_matrix(const FloatRowMat &matrix) {
    static_assert(std::endian::native == std::endian::little);
    const auto *bytes = reinterpret_cast<const uint8_t *>(matrix.data());
    return co0_v2_sha256_bytes(std::span<const uint8_t>(
        bytes,
        static_cast<size_t>(matrix.size()) * sizeof(float)));
}

inline std::string co0_v2_sha256_code_words(std::span<const uint32_t> code) {
    std::vector<uint8_t> bytes;
    bytes.reserve(code.size() * sizeof(uint32_t));
    for (uint32_t value : code) {
        bytes.push_back(static_cast<uint8_t>(value));
        bytes.push_back(static_cast<uint8_t>(value >> 8U));
        bytes.push_back(static_cast<uint8_t>(value >> 16U));
        bytes.push_back(static_cast<uint8_t>(value >> 24U));
    }
    return co0_v2_sha256_bytes(bytes);
}

inline Co0V2VectorFileShape co0_v2_validate_vector_file(
    const std::filesystem::path &path,
    uint64_t expected_rows,
    uint32_t expected_dimension,
    size_t scalar_bytes) {
    io_detail::require_io(scalar_bytes == 4, "CO-0 v2 vector files require four-byte scalars");
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open vector file: " + path.string());
    }
    uint64_t rows = 0;
    while (true) {
        std::array<uint8_t, 4> dimension_bytes{};
        input.read(reinterpret_cast<char *>(dimension_bytes.data()), dimension_bytes.size());
        if (input.gcount() == 0 && input.eof()) {
            break;
        }
        io_detail::require_io(
            input.gcount() == static_cast<std::streamsize>(dimension_bytes.size()),
            "truncated vector dimension header: " + path.string());
        const uint32_t dimension = io_detail::little_u32(dimension_bytes);
        io_detail::require_io(
            dimension == expected_dimension,
            "vector dimension mismatch in " + path.string());
        const uint64_t payload = static_cast<uint64_t>(dimension) * scalar_bytes;
        io_detail::require_io(
            payload <= static_cast<uint64_t>(std::numeric_limits<std::streamoff>::max()),
            "vector row payload is too large");
        input.seekg(static_cast<std::streamoff>(payload), std::ios::cur);
        io_detail::require_io(static_cast<bool>(input), "truncated vector row: " + path.string());
        ++rows;
    }
    io_detail::require_io(rows == expected_rows, "vector row count mismatch in " + path.string());
    const uint64_t size = std::filesystem::file_size(path);
    const uint64_t expected_size = expected_rows *
                                   (sizeof(uint32_t) + static_cast<uint64_t>(expected_dimension) * scalar_bytes);
    io_detail::require_io(size == expected_size, "vector file size/shape mismatch in " + path.string());
    return Co0V2VectorFileShape{rows, expected_dimension, size};
}

class Co0V2FvecReader {
  public:
    Co0V2FvecReader(
        std::filesystem::path path,
        uint64_t rows,
        uint32_t dimension)
        : path_(std::move(path)), rows_(rows), dimension_(dimension), input_(path_, std::ios::binary) {
        if (!input_) {
            throw std::runtime_error("cannot open fvec file: " + path_.string());
        }
        row_bytes_ = sizeof(uint32_t) + static_cast<uint64_t>(dimension_) * sizeof(float);
    }

    FloatVec read(uint32_t vector_id) {
        io_detail::require_io(vector_id < rows_, "fvec vector id is out of range");
        const uint64_t offset = static_cast<uint64_t>(vector_id) * row_bytes_;
        io_detail::require_io(
            offset <= static_cast<uint64_t>(std::numeric_limits<std::streamoff>::max()),
            "fvec offset overflows streamoff");
        input_.clear();
        input_.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
        std::array<uint8_t, 4> dimension_bytes{};
        input_.read(reinterpret_cast<char *>(dimension_bytes.data()), dimension_bytes.size());
        io_detail::require_io(
            input_ && io_detail::little_u32(dimension_bytes) == dimension_,
            "fvec row dimension mismatch");
        FloatVec result(static_cast<Eigen::Index>(dimension_));
        input_.read(reinterpret_cast<char *>(result.data()),
                    static_cast<std::streamsize>(dimension_) * sizeof(float));
        io_detail::require_io(static_cast<bool>(input_), "failed to read fvec row");
        io_detail::require_io(result.allFinite(), "fvec row contains non-finite coordinate");
        return result;
    }

  private:
    std::filesystem::path path_;
    uint64_t rows_ = 0;
    uint32_t dimension_ = 0;
    uint64_t row_bytes_ = 0;
    std::ifstream input_;
};

class Co0V2GzipLineReader {
  public:
    explicit Co0V2GzipLineReader(const std::filesystem::path &path)
        : path_(path), file_(gzopen(path.c_str(), "rb")) {
        if (file_ == nullptr) {
            throw std::runtime_error("cannot open gzip input: " + path.string());
        }
    }

    Co0V2GzipLineReader(const Co0V2GzipLineReader &) = delete;
    Co0V2GzipLineReader &operator=(const Co0V2GzipLineReader &) = delete;

    ~Co0V2GzipLineReader() {
        if (file_ != nullptr) {
            gzclose(file_);
        }
    }

    bool next(std::string &line) {
        line.clear();
        std::array<char, 4096> buffer{};
        while (true) {
            char *read = gzgets(file_, buffer.data(), static_cast<int>(buffer.size()));
            if (read == nullptr) {
                int error_number = Z_OK;
                const char *message = gzerror(file_, &error_number);
                if (error_number != Z_OK && error_number != Z_STREAM_END) {
                    throw std::runtime_error(
                        "gzip read failed for " + path_.string() + ": " + message);
                }
                return !line.empty();
            }
            line.append(read);
            if (!line.empty() && line.back() == '\n') {
                line.pop_back();
                if (!line.empty() && line.back() == '\r') {
                    line.pop_back();
                }
                return true;
            }
            if (gzeof(file_) != 0) {
                return true;
            }
        }
    }

  private:
    std::filesystem::path path_;
    gzFile file_ = nullptr;
};

inline std::vector<Co0V2SampleRow> co0_v2_read_sample_inventory(
    const std::filesystem::path &path,
    std::string_view expected_dataset) {
    Co0V2GzipLineReader input(path);
    std::string line;
    io_detail::require_io(input.next(line), "sample inventory is empty");
    io_detail::require_io(
        line == "dataset_id,cell_id,rank_in_cell,vector_id",
        "sample inventory header mismatch");
    std::vector<Co0V2SampleRow> rows;
    while (input.next(line)) {
        const auto fields = io_detail::split_csv(line);
        io_detail::require_io(fields.size() == 4, "sample inventory field count mismatch");
        io_detail::require_io(fields[0] == expected_dataset, "sample inventory dataset mismatch");
        rows.push_back(Co0V2SampleRow{
            fields[0],
            io_detail::parse_u32(fields[1], "cell_id"),
            io_detail::parse_u32(fields[2], "rank_in_cell"),
            io_detail::parse_u32(fields[3], "vector_id"),
        });
    }
    return rows;
}

inline std::vector<Co0V2PairRow> co0_v2_read_pair_inventory(
    const std::filesystem::path &path,
    std::string_view expected_dataset) {
    Co0V2GzipLineReader input(path);
    std::string line;
    io_detail::require_io(input.next(line), "pair inventory is empty");
    io_detail::require_io(
        line == "dataset_id,cell_id,pair_rank,stored_vector_id,query_vector_id",
        "pair inventory header mismatch");
    std::vector<Co0V2PairRow> rows;
    while (input.next(line)) {
        const auto fields = io_detail::split_csv(line);
        io_detail::require_io(fields.size() == 5, "pair inventory field count mismatch");
        io_detail::require_io(fields[0] == expected_dataset, "pair inventory dataset mismatch");
        rows.push_back(Co0V2PairRow{
            fields[0],
            io_detail::parse_u32(fields[1], "cell_id"),
            io_detail::parse_u32(fields[2], "pair_rank"),
            io_detail::parse_u32(fields[3], "stored_vector_id"),
            io_detail::parse_u32(fields[4], "query_vector_id"),
        });
    }
    return rows;
}

class Co0V2GzipWriter {
  public:
    explicit Co0V2GzipWriter(const std::filesystem::path &path)
        : path_(path) {
        std::filesystem::create_directories(path.parent_path());
        file_ = gzopen(path.c_str(), "wb9");
        if (file_ == nullptr) {
            throw std::runtime_error("cannot open gzip output: " + path.string());
        }
    }

    Co0V2GzipWriter(const Co0V2GzipWriter &) = delete;
    Co0V2GzipWriter &operator=(const Co0V2GzipWriter &) = delete;

    ~Co0V2GzipWriter() {
        if (file_ != nullptr) {
            gzclose(file_);
        }
    }

    void write(std::string_view text) {
        io_detail::require_io(
            text.size() <= static_cast<size_t>(std::numeric_limits<unsigned int>::max()),
            "gzip output write is too large");
        const int written = gzwrite(file_, text.data(), static_cast<unsigned int>(text.size()));
        io_detail::require_io(
            written == static_cast<int>(text.size()),
            "gzip write failed for " + path_.string());
    }

    void close() {
        if (file_ != nullptr) {
            const int status = gzclose(file_);
            file_ = nullptr;
            io_detail::require_io(status == Z_OK, "gzip close failed for " + path_.string());
        }
    }

  private:
    std::filesystem::path path_;
    gzFile file_ = nullptr;
};

class Co0V2CodeShardWriter {
  public:
    Co0V2CodeShardWriter(std::filesystem::path path, uint32_t total_bits)
        : path_(std::move(path)), total_bits_(total_bits) {
        std::filesystem::create_directories(path_.parent_path());
        output_.open(path_, std::ios::binary | std::ios::trunc);
        if (!output_) {
            throw std::runtime_error("cannot open code shard: " + path_.string());
        }
    }

    Co0V2CodeLocation append(std::span<const uint32_t> code) {
        const std::vector<uint8_t> packed = co0_v2_pack_canonical_code(code, total_bits_);
        const uint64_t bit_length = static_cast<uint64_t>(packed.size()) * 8;
        const uint64_t bit_offset = bytes_written_ * 8;
        output_.write(reinterpret_cast<const char *>(packed.data()),
                      static_cast<std::streamsize>(packed.size()));
        io_detail::require_io(static_cast<bool>(output_), "failed to write code shard");
        bytes_written_ += packed.size();
        return Co0V2CodeLocation{
            bit_offset,
            bit_length,
            co0_v2_sha256_code_words(code),
        };
    }

    uint64_t bytes_written() const {
        return bytes_written_;
    }

    void close() {
        output_.flush();
        io_detail::require_io(static_cast<bool>(output_), "failed to flush code shard");
        output_.close();
    }

  private:
    std::filesystem::path path_;
    uint32_t total_bits_ = 0;
    uint64_t bytes_written_ = 0;
    std::ofstream output_;
};

inline uint64_t co0_v2_peak_rss_bytes() {
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0 || usage.ru_maxrss <= 0) {
        return 0;
    }
    return static_cast<uint64_t>(usage.ru_maxrss) * UINT64_C(1024);
}

} // namespace saqlib::caq_validation

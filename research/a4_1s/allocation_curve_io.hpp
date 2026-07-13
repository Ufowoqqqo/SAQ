#pragma once

#include "exact_quantizer.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cctype>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_1s {

// Strict little-endian reader shared by the allocation-suite and the
// allocation-item commands.  Decimal integers use their shortest unsigned
// ASCII representation; RequireEof rejects every trailing byte.
class AllocationCurveReader {
  public:
    explicit AllocationCurveReader(const std::string &path)
        : input_(path, std::ios::binary) {
        if (!input_) {
            throw std::runtime_error("failed to open allocation curve input");
        }
    }

    void RequireMagic(std::string_view expected) {
        RequireBytes(expected, "magic");
    }

    [[nodiscard]] std::uint8_t ReadU8(const char *field) {
        std::uint8_t result = 0;
        ReadExact(reinterpret_cast<char *>(&result), sizeof(result), field);
        return result;
    }

    [[nodiscard]] std::uint32_t ReadU32(const char *field) {
        std::array<unsigned char, 4> bytes{};
        ReadExact(reinterpret_cast<char *>(bytes.data()), bytes.size(), field);
        return static_cast<std::uint32_t>(bytes[0]) |
               (static_cast<std::uint32_t>(bytes[1]) << 8U) |
               (static_cast<std::uint32_t>(bytes[2]) << 16U) |
               (static_cast<std::uint32_t>(bytes[3]) << 24U);
    }

    [[nodiscard]] std::int32_t ReadI32(const char *field) {
        return std::bit_cast<std::int32_t>(ReadU32(field));
    }

    [[nodiscard]] std::string ReadDecimal(bool positive,
                                          const char *field) {
        const std::uint32_t length = ReadU32(field);
        if (length == 0 ||
            length > static_cast<std::uint64_t>(
                         std::numeric_limits<std::streamsize>::max())) {
            throw std::runtime_error(std::string(field) +
                                     " has invalid byte length");
        }
        std::string value(length, '\0');
        ReadExact(value.data(), value.size(), field);
        if (!std::all_of(value.begin(), value.end(), [](unsigned char byte) {
                return std::isdigit(byte) != 0;
            })) {
            throw std::runtime_error(std::string(field) +
                                     " is not unsigned ASCII decimal");
        }
        if (value.size() > 1 && value.front() == '0') {
            throw std::runtime_error(std::string(field) +
                                     " has a noncanonical leading zero");
        }
        if (positive && value == "0") {
            throw std::runtime_error(std::string(field) + " must be positive");
        }
        return value;
    }

    void RequireBytes(std::string_view expected, const char *field) {
        std::string observed(expected.size(), '\0');
        ReadExact(observed.data(), observed.size(), field);
        if (observed != expected) {
            throw std::runtime_error(std::string("allocation ") + field +
                                     " mismatch");
        }
    }

    void RequireEof() {
        char trailing = 0;
        if (input_.read(&trailing, 1)) {
            throw std::runtime_error("allocation input has trailing bytes");
        }
        if (!input_.eof() || input_.bad()) {
            throw std::runtime_error(
                "failed while checking allocation input EOF");
        }
    }

  private:
    void ReadExact(char *destination,
                   std::size_t byte_count,
                   const char *field) {
        if (byte_count > static_cast<std::uint64_t>(
                             std::numeric_limits<std::streamsize>::max())) {
            throw std::runtime_error(std::string(field) +
                                     " byte count is too large");
        }
        input_.read(destination, static_cast<std::streamsize>(byte_count));
        if (!input_) {
            throw std::runtime_error(std::string("truncated allocation ") +
                                     field);
        }
    }

    std::ifstream input_;
};

// Read one exact scalar at-most-K curve.  The binary payload contains one
// effective cardinality and one exact squared-error objective for each
// implicit requested cardinality K=1..maximum_cardinality.  The reader also
// validates min(K,H), objective monotonicity, the unreachable nominal tail,
// exponent -298, and canonical nonnegative rational text.
[[nodiscard]] inline ScalarCurveResult ReadExactAllocationCurve(
    AllocationCurveReader *reader,
    std::uint32_t maximum_cardinality) {
    if (reader == nullptr) {
        throw std::invalid_argument("allocation curve reader is null");
    }
    if (maximum_cardinality == 0 || maximum_cardinality > 256) {
        throw std::runtime_error(
            "allocation curve maximum cardinality must be in [1,256]");
    }

    auto read_objective = [reader]() {
        const std::int32_t binary_exponent =
            reader->ReadI32("binary_exponent");
        if (binary_exponent != -298) {
            throw std::runtime_error(
                "allocation curve exponent must be -298");
        }
        const std::string numerator_text =
            reader->ReadDecimal(false, "numerator");
        const std::string denominator_text =
            reader->ReadDecimal(true, "denominator");
        CanonicalScaledRational result(mpz_class(numerator_text, 10),
                                       mpz_class(denominator_text, 10),
                                       binary_exponent);
        if (result.numerator < 0 || result.denominator <= 0 ||
            result.numerator.get_str() != numerator_text ||
            result.denominator.get_str() != denominator_text) {
            throw std::runtime_error(
                "allocation curve rational is not canonical "
                "nonnegative/positive");
        }
        return result;
    };

    ScalarCurveResult curve;
    curve.solutions.resize(
        static_cast<std::size_t>(maximum_cardinality) + 1U);
    for (std::uint32_t cardinality = 1;
         cardinality <= maximum_cardinality;
         ++cardinality) {
        ScalarSolution solution;
        solution.requested_cardinality = cardinality;
        solution.effective_cardinality =
            reader->ReadU32("effective_cardinality");
        if (solution.effective_cardinality == 0 ||
            solution.effective_cardinality > cardinality) {
            throw std::runtime_error(
                "effective cardinality is outside [1,K]");
        }
        solution.sse = read_objective();
        curve.solutions[cardinality] = std::move(solution);
    }

    const std::uint32_t distinct_support =
        curve.solutions[maximum_cardinality].effective_cardinality;
    for (std::uint32_t cardinality = 1;
         cardinality <= maximum_cardinality;
         ++cardinality) {
        const std::uint32_t expected_effective =
            std::min(cardinality, distinct_support);
        if (curve.solutions[cardinality].effective_cardinality !=
            expected_effective) {
            throw std::runtime_error(
                "effective cardinalities do not follow min(K,H)");
        }
        if (cardinality > 1) {
            const mpq_class previous =
                curve.solutions[cardinality - 1].sse.coefficient();
            const mpq_class current =
                curve.solutions[cardinality].sse.coefficient();
            if (mpq_cmp(current.get_mpq_t(), previous.get_mpq_t()) > 0) {
                throw std::runtime_error(
                    "allocation curve objective increases with K");
            }
        }
        if (cardinality > distinct_support) {
            const mpq_class current =
                curve.solutions[cardinality].sse.coefficient();
            const mpq_class support_limit =
                curve.solutions[distinct_support].sse.coefficient();
            if (mpq_cmp(current.get_mpq_t(),
                        support_limit.get_mpq_t()) != 0) {
                throw std::runtime_error(
                    "unreachable nominal K does not copy the H-point objective");
            }
        }
    }
    return curve;
}

[[nodiscard]] inline std::vector<ScalarCurveResult> ReadExactAllocationCurves(
    AllocationCurveReader *reader,
    std::uint32_t curve_count,
    std::uint32_t maximum_cardinality) {
    if (curve_count == 0 || curve_count > 128) {
        throw std::runtime_error("allocation curve count must be in [1,128]");
    }
    std::vector<ScalarCurveResult> curves;
    curves.reserve(curve_count);
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
        curves.push_back(
            ReadExactAllocationCurve(reader, maximum_cardinality));
    }
    return curves;
}

// Decode the legacy full-panel A4ALC001 interchange.  Kept as a named helper
// so the legacy allocation-suite and the itemized allocator share one decoder.
[[nodiscard]] inline std::vector<ScalarCurveResult>
ReadAllocationCurvesA4alc001(const std::string &input_path) {
    constexpr std::string_view input_magic = "A4ALC001";
    constexpr std::uint32_t curve_count = 128;
    constexpr std::uint32_t maximum_cardinality = 256;
    AllocationCurveReader reader(input_path);
    reader.RequireMagic(input_magic);
    if (reader.ReadU32("curve_count") != curve_count ||
        reader.ReadU32("maximum_K") != maximum_cardinality) {
        throw std::runtime_error(
            "allocation-suite input must contain 128 curves through K=256");
    }
    std::vector<ScalarCurveResult> curves =
        ReadExactAllocationCurves(&reader, curve_count, maximum_cardinality);
    reader.RequireEof();
    return curves;
}

} // namespace saq::a4_1s

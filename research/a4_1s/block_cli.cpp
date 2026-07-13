#include "block_cli.hpp"

#include "block_vq.hpp"

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <ios>
#include <istream>
#include <limits>
#include <locale>
#include <ostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace saq::a4_1s {
namespace {

constexpr std::string_view kBlockInputMagic = "A4BLK001";
constexpr std::string_view kBlockOutputMagic = "A4S_BLOCK_RESULT_V1";
constexpr std::uint32_t kMaximumCaseCount = 1U << 20U;
constexpr std::uint32_t kMaximumDatasetIdBytes = 1U << 20U;
constexpr std::uint32_t kMaximumPointCount = 1U << 24U;
constexpr std::uint32_t kMaximumCapacity = 1U << 20U;

void ReadExact(std::istream &input, char *destination, std::size_t size) {
    if (size > static_cast<std::size_t>(
                   std::numeric_limits<std::streamsize>::max())) {
        throw std::runtime_error("native block input field is too large");
    }
    input.read(destination, static_cast<std::streamsize>(size));
    if (!input) {
        throw std::runtime_error("truncated native block-suite input");
    }
}

[[nodiscard]] std::uint32_t ReadU32(std::istream &input) {
    std::array<unsigned char, 4> bytes{};
    ReadExact(input, reinterpret_cast<char *>(bytes.data()), bytes.size());
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8U) |
           (static_cast<std::uint32_t>(bytes[2]) << 16U) |
           (static_cast<std::uint32_t>(bytes[3]) << 24U);
}

[[nodiscard]] std::uint64_t ReadU64(std::istream &input) {
    std::array<unsigned char, 8> bytes{};
    ReadExact(input, reinterpret_cast<char *>(bytes.data()), bytes.size());
    std::uint64_t value = 0;
    for (std::size_t index = 0; index < bytes.size(); ++index) {
        value |= static_cast<std::uint64_t>(bytes[index]) << (8U * index);
    }
    return value;
}

void RequireMagic(std::istream &input) {
    std::array<char, 8> observed{};
    ReadExact(input, observed.data(), observed.size());
    if (std::string_view(observed.data(), observed.size()) != kBlockInputMagic) {
        throw std::runtime_error("native block-suite input magic mismatch");
    }
}

[[nodiscard]] bool IsContinuation(unsigned char byte) noexcept {
    return (byte & 0xc0U) == 0x80U;
}

// Strict UTF-8 validation rejects overlong sequences, surrogate code points,
// and values above U+10FFFF.  TSV delimiters and the frozen hash delimiter are
// rejected separately so every emitted dataset id remains one literal field.
void ValidateDatasetId(std::string_view value) {
    if (value.empty()) {
        throw std::runtime_error("block dataset id must not be empty");
    }
    for (const char character : value) {
        if (character == '\0' || character == '\t' || character == '\n' ||
            character == '\r' || character == '|') {
            throw std::runtime_error(
                "block dataset id contains a forbidden delimiter");
        }
    }

    std::size_t index = 0;
    while (index < value.size()) {
        const auto first = static_cast<unsigned char>(value[index]);
        if (first <= 0x7fU) {
            ++index;
            continue;
        }
        if (first >= 0xc2U && first <= 0xdfU) {
            if (index + 1 >= value.size() ||
                !IsContinuation(static_cast<unsigned char>(value[index + 1]))) {
                throw std::runtime_error("block dataset id is not valid UTF-8");
            }
            index += 2;
            continue;
        }
        if (first >= 0xe0U && first <= 0xefU) {
            if (index + 2 >= value.size()) {
                throw std::runtime_error("block dataset id is not valid UTF-8");
            }
            const auto second = static_cast<unsigned char>(value[index + 1]);
            const auto third = static_cast<unsigned char>(value[index + 2]);
            const bool second_valid =
                IsContinuation(second) &&
                !(first == 0xe0U && second < 0xa0U) &&
                !(first == 0xedU && second > 0x9fU);
            if (!second_valid || !IsContinuation(third)) {
                throw std::runtime_error("block dataset id is not valid UTF-8");
            }
            index += 3;
            continue;
        }
        if (first >= 0xf0U && first <= 0xf4U) {
            if (index + 3 >= value.size()) {
                throw std::runtime_error("block dataset id is not valid UTF-8");
            }
            const auto second = static_cast<unsigned char>(value[index + 1]);
            const auto third = static_cast<unsigned char>(value[index + 2]);
            const auto fourth = static_cast<unsigned char>(value[index + 3]);
            const bool second_valid =
                IsContinuation(second) &&
                !(first == 0xf0U && second < 0x90U) &&
                !(first == 0xf4U && second > 0x8fU);
            if (!second_valid || !IsContinuation(third) ||
                !IsContinuation(fourth)) {
                throw std::runtime_error("block dataset id is not valid UTF-8");
            }
            index += 4;
            continue;
        }
        throw std::runtime_error("block dataset id is not valid UTF-8");
    }
}

[[nodiscard]] std::string ReadDatasetId(std::istream &input,
                                        std::uint32_t length) {
    if (length == 0 || length > kMaximumDatasetIdBytes) {
        throw std::runtime_error("invalid block dataset-id length");
    }
    std::string dataset_id(length, '\0');
    ReadExact(input, dataset_id.data(), dataset_id.size());
    ValidateDatasetId(dataset_id);
    return dataset_id;
}

[[nodiscard]] std::string Hex32(std::uint32_t value) {
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << "0x" << std::hex << std::nouppercase << std::setw(8)
           << std::setfill('0') << value;
    return output.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t value) {
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << "0x" << std::hex << std::nouppercase << std::setw(16)
           << std::setfill('0') << value;
    return output.str();
}

[[nodiscard]] std::string DigestHex(const Sha256Digest &digest) {
    std::ostringstream output;
    output.imbue(std::locale::classic());
    output << std::hex << std::nouppercase << std::setfill('0');
    for (const std::uint8_t byte : digest) {
        output << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return output.str();
}

[[nodiscard]] std::uint64_t DoubleBits(double value) noexcept {
    return std::bit_cast<std::uint64_t>(value);
}

[[nodiscard]] std::string FailureName(BlockVqFailure failure) {
    switch (failure) {
    case BlockVqFailure::kNone:
        return "NONE";
    case BlockVqFailure::kNonfiniteControl:
        return "NONFINITE_CONTROL";
    case BlockVqFailure::kCandidateSseIncrease:
        return "CANDIDATE_SSE_INCREASE";
    case BlockVqFailure::kIterationLimit:
        return "ITERATION_LIMIT";
    case BlockVqFailure::kSerializedCenterCollision:
        return "SERIALIZED_CENTER_COLLISION";
    case BlockVqFailure::kCartesianDominance:
        return "CARTESIAN_DOMINANCE";
    }
    throw std::logic_error("unknown block failure enum");
}

void ValidateFailureDetail(std::string_view detail) {
    if (detail.find('\t') != std::string_view::npos ||
        detail.find('\n') != std::string_view::npos ||
        detail.find('\r') != std::string_view::npos) {
        throw std::logic_error("block failure detail is not TSV-safe");
    }
}

struct ParsedBlockCase {
    std::uint32_t case_id{0};
    BlockVqMetadata metadata;
    std::vector<Point2> points;
    std::vector<double> axis0;
    std::vector<double> axis1;
    std::vector<std::uint64_t> axis0_bits;
    std::vector<std::uint64_t> axis1_bits;
};

[[nodiscard]] ParsedBlockCase ReadCase(std::istream &input) {
    ParsedBlockCase fixture;
    fixture.case_id = ReadU32(input);
    fixture.metadata.capacity = ReadU32(input);
    fixture.metadata.group_id = ReadU32(input);
    const std::uint32_t dataset_id_length = ReadU32(input);
    fixture.metadata.dataset_id = ReadDatasetId(input, dataset_id_length);
    fixture.metadata.protocol_version = std::string(kBlockSuiteProtocolVersion);

    const std::uint32_t point_count = ReadU32(input);
    const std::uint32_t axis0_count = ReadU32(input);
    const std::uint32_t axis1_count = ReadU32(input);
    if (fixture.metadata.capacity == 0 ||
        fixture.metadata.capacity > kMaximumCapacity || point_count == 0 ||
        point_count > kMaximumPointCount || axis0_count == 0 ||
        axis1_count == 0 || fixture.metadata.capacity > point_count) {
        throw std::runtime_error("invalid native block-suite case shape");
    }
    const std::uint64_t product =
        static_cast<std::uint64_t>(axis0_count) * axis1_count;
    if (product > fixture.metadata.capacity) {
        throw std::runtime_error(
            "native block start-0 product exceeds capacity");
    }

    fixture.points.reserve(point_count);
    for (std::uint32_t row = 0; row < point_count; ++row) {
        const std::uint32_t coordinate0_bits = ReadU32(input);
        const std::uint32_t coordinate1_bits = ReadU32(input);
        const std::uint64_t cell_id = ReadU64(input);
        const std::uint64_t vector_id = ReadU64(input);
        fixture.points.push_back(MakePoint2(
            std::bit_cast<float>(coordinate0_bits),
            std::bit_cast<float>(coordinate1_bits), cell_id, vector_id,
            fixture.metadata.protocol_version, fixture.metadata.dataset_id));
    }

    fixture.axis0.reserve(axis0_count);
    fixture.axis0_bits.reserve(axis0_count);
    for (std::uint32_t index = 0; index < axis0_count; ++index) {
        const std::uint64_t bits = ReadU64(input);
        fixture.axis0_bits.push_back(bits);
        fixture.axis0.push_back(std::bit_cast<double>(bits));
    }
    fixture.axis1.reserve(axis1_count);
    fixture.axis1_bits.reserve(axis1_count);
    for (std::uint32_t index = 0; index < axis1_count; ++index) {
        const std::uint64_t bits = ReadU64(input);
        fixture.axis1_bits.push_back(bits);
        fixture.axis1.push_back(std::bit_cast<double>(bits));
    }
    return fixture;
}

void VerifyOrderedAuthority(const std::vector<Point2> &ordered,
                            const BlockVqTrainingResult &result) {
    if (ordered.size() != result.ordered_vector_ids.size() ||
        ordered.size() != result.ordered_selection_digests.size()) {
        throw std::logic_error("block result row-authority size mismatch");
    }
    for (std::size_t row = 0; row < ordered.size(); ++row) {
        if (ordered[row].vector_id != result.ordered_vector_ids[row] ||
            ordered[row].selection_digest !=
                result.ordered_selection_digests[row]) {
            throw std::logic_error("block result row-authority mismatch");
        }
    }
}

void EmitStart(std::ostream &output,
               std::uint32_t case_id,
               const std::vector<Point2> &ordered,
               const BlockVqStartTrace &start) {
    output << "START\t" << case_id << '\t' << start.start_id << '\t'
           << DigestHex(start.first_seed_digest) << '\t'
           << start.selected_vector_ids.size() << '\t'
           << start.initial_centers.size() << '\t'
           << Hex64(DoubleBits(start.initial_sse)) << '\t'
           << start.steps.size() << '\t' << start.complete_iterations << '\t'
           << static_cast<unsigned int>(start.converged) << '\t'
           << FailureName(start.failure) << '\t'
           << Hex64(DoubleBits(start.final_sse)) << '\t'
           << start.final_assignments.size() << '\t'
           << start.final_centers.size() << '\t'
           << start.serialized_final_centers.size() << '\t'
           << start.distinct_serialized_center_count << '\t'
           << start.distance_comparison_count << '\t'
           << start.assignment_tie_count << '\t'
           << start.farthest_tie_count << '\n';

    for (std::size_t index = 0; index < start.selected_vector_ids.size();
         ++index) {
        output << "START_SELECTED\t" << case_id << '\t' << start.start_id
               << '\t' << index << '\t' << start.selected_vector_ids[index]
               << '\n';
    }
    for (std::size_t center = 0; center < start.initial_centers.size();
         ++center) {
        output << "START_CENTER\t" << case_id << '\t' << start.start_id << '\t'
               << center << '\t'
               << Hex64(DoubleBits(start.initial_centers[center].coordinate0))
               << '\t'
               << Hex64(DoubleBits(start.initial_centers[center].coordinate1))
               << '\n';
    }

    for (const LloydStepTrace &step : start.steps) {
        output << "STEP\t" << case_id << '\t' << start.start_id << '\t'
               << step.iteration << '\t'
               << Hex64(DoubleBits(step.prior_sse)) << '\t'
               << Hex64(DoubleBits(step.candidate_sse)) << '\t'
               << step.changed_assignment_count << '\t'
               << step.empty_center_ids.size() << '\t'
               << step.centers_after.size() << '\n';
        for (std::size_t index = 0; index < step.empty_center_ids.size();
             ++index) {
            output << "STEP_EMPTY\t" << case_id << '\t' << start.start_id
                   << '\t' << step.iteration << '\t' << index << '\t'
                   << step.empty_center_ids[index] << '\n';
        }
        for (std::size_t center = 0; center < step.centers_after.size();
             ++center) {
            output << "STEP_CENTER\t" << case_id << '\t' << start.start_id
                   << '\t' << step.iteration << '\t' << center << '\t'
                   << Hex64(
                          DoubleBits(step.centers_after[center].coordinate0))
                   << '\t'
                   << Hex64(
                          DoubleBits(step.centers_after[center].coordinate1))
                   << '\n';
        }
    }

    if (!start.final_assignments.empty() &&
        start.final_assignments.size() != ordered.size()) {
        throw std::logic_error("block final-assignment row count mismatch");
    }
    for (std::size_t row = 0; row < start.final_assignments.size(); ++row) {
        output << "FINAL_ASSIGNMENT\t" << case_id << '\t' << start.start_id
               << '\t' << row << '\t' << ordered[row].vector_id << '\t'
               << start.final_assignments[row] << '\n';
    }
    for (std::size_t center = 0; center < start.final_centers.size();
         ++center) {
        output << "FINAL_CENTER\t" << case_id << '\t' << start.start_id << '\t'
               << center << '\t'
               << Hex64(DoubleBits(start.final_centers[center].coordinate0))
               << '\t'
               << Hex64(DoubleBits(start.final_centers[center].coordinate1))
               << '\n';
    }
    for (std::size_t center = 0;
         center < start.serialized_final_centers.size(); ++center) {
        output << "FINAL_SERIALIZED_CENTER\t" << case_id << '\t'
               << start.start_id << '\t' << center << '\t'
               << Hex32(start.serialized_final_centers[center].coordinate0_bits)
               << '\t'
               << Hex32(start.serialized_final_centers[center].coordinate1_bits)
               << '\n';
    }
    output << "END_START\t" << case_id << '\t' << start.start_id << '\n';
}

void EmitBest(std::ostream &output,
              std::uint32_t case_id,
              const std::vector<Point2> &ordered,
              const BlockVqTrainingResult &result) {
    if (!result.control_valid) {
        output << "BEST\t" << case_id << "\t0\n";
        return;
    }
    if (result.best_assignments.size() != ordered.size() ||
        result.best_centers.size() != result.best_serialized_centers.size()) {
        throw std::logic_error("best block state is incomplete");
    }
    output << "BEST\t" << case_id << "\t1\t" << result.best_start_id << '\t'
           << Hex64(DoubleBits(result.best_sse)) << '\t'
           << result.best_centers.size() << '\t'
           << result.best_assignments.size() << '\t'
           << result.best_serialized_centers.size() << '\n';
    for (std::size_t center = 0; center < result.best_centers.size(); ++center) {
        output << "BEST_CENTER\t" << case_id << '\t' << center << '\t'
               << Hex64(DoubleBits(result.best_centers[center].coordinate0))
               << '\t'
               << Hex64(DoubleBits(result.best_centers[center].coordinate1))
               << '\t'
               << Hex32(result.best_serialized_centers[center].coordinate0_bits)
               << '\t'
               << Hex32(result.best_serialized_centers[center].coordinate1_bits)
               << '\n';
    }
    for (std::size_t row = 0; row < result.best_assignments.size(); ++row) {
        output << "BEST_ASSIGNMENT\t" << case_id << '\t' << row << '\t'
               << ordered[row].vector_id << '\t' << result.best_assignments[row]
               << '\n';
    }
}

void EmitCase(std::ostream &output,
              const ParsedBlockCase &fixture,
              const std::vector<Point2> &ordered,
              const BlockVqTrainingResult &result) {
    ValidateFailureDetail(result.failure_detail);
    output << "CASE\t" << fixture.case_id << '\t'
           << fixture.metadata.protocol_version << '\t'
           << fixture.metadata.dataset_id << '\t' << fixture.metadata.capacity
           << '\t' << fixture.metadata.group_id << '\t' << fixture.points.size()
           << '\t' << fixture.axis0.size() << '\t' << fixture.axis1.size()
           << '\t' << static_cast<unsigned int>(result.control_valid) << '\t'
           << FailureName(result.failure) << '\t' << result.failed_start_id
           << '\t' << result.failure_detail << '\n';

    for (std::size_t index = 0; index < fixture.axis0_bits.size(); ++index) {
        output << "AXIS\t" << fixture.case_id << "\t0\t" << index << '\t'
               << Hex64(fixture.axis0_bits[index]) << '\n';
    }
    for (std::size_t index = 0; index < fixture.axis1_bits.size(); ++index) {
        output << "AXIS\t" << fixture.case_id << "\t1\t" << index << '\t'
               << Hex64(fixture.axis1_bits[index]) << '\n';
    }
    for (std::size_t row = 0; row < ordered.size(); ++row) {
        output << "ROW\t" << fixture.case_id << '\t' << row << '\t'
               << ordered[row].cell_id << '\t' << ordered[row].vector_id << '\t'
               << DigestHex(ordered[row].selection_digest) << '\t'
               << Hex32(std::bit_cast<std::uint32_t>(ordered[row].coordinate0))
               << '\t'
               << Hex32(std::bit_cast<std::uint32_t>(ordered[row].coordinate1))
               << '\n';
    }

    output << "CARTESIAN\t" << fixture.case_id << '\t'
           << result.start0_cartesian_centers.size() << '\t'
           << Hex64(DoubleBits(result.start0_cartesian_sse)) << '\t'
           << Hex64(DoubleBits(result.start0_filled_sse)) << '\n';
    for (std::size_t center = 0;
         center < result.start0_cartesian_centers.size(); ++center) {
        output << "CARTESIAN_CENTER\t" << fixture.case_id << '\t' << center
               << '\t'
               << Hex64(DoubleBits(
                      result.start0_cartesian_centers[center].coordinate0))
               << '\t'
               << Hex64(DoubleBits(
                      result.start0_cartesian_centers[center].coordinate1))
               << '\n';
    }
    for (const BlockVqStartTrace &start : result.starts) {
        EmitStart(output, fixture.case_id, ordered, start);
    }
    EmitBest(output, fixture.case_id, ordered, result);
    output << "END_CASE\t" << fixture.case_id << '\n';
}

} // namespace

BlockCliSummary RunBlockSuiteStreams(std::istream &input,
                                     std::ostream &output) {
    input.imbue(std::locale::classic());
    output.imbue(std::locale::classic());
    RequireMagic(input);
    const std::uint32_t case_count = ReadU32(input);
    if (case_count > kMaximumCaseCount) {
        throw std::runtime_error("native block-suite case count is too large");
    }

    output << kBlockOutputMagic << '\n';
    output << "PROTOCOL\t" << kBlockSuiteProtocolVersion << '\n';
    std::set<std::uint32_t> case_ids;
    BlockCliSummary summary;
    summary.case_count = case_count;
    for (std::uint32_t case_index = 0; case_index < case_count; ++case_index) {
        ParsedBlockCase fixture = ReadCase(input);
        if (!case_ids.insert(fixture.case_id).second) {
            throw std::runtime_error("duplicate native block-suite case id");
        }
        const std::vector<Point2> ordered = OrderAndValidatePoints(
            fixture.points, fixture.metadata.protocol_version,
            fixture.metadata.dataset_id);
        const BlockVqTrainingResult result = TrainFrozenBlockVq(
            fixture.points, fixture.metadata, fixture.axis0, fixture.axis1);
        VerifyOrderedAuthority(ordered, result);

        std::ostringstream case_output;
        case_output.imbue(std::locale::classic());
        EmitCase(case_output, fixture, ordered, result);
        if (!case_output) {
            throw std::runtime_error("failed to serialize block-suite case");
        }
        output << case_output.str();
        if (result.control_valid) {
            ++summary.control_valid_count;
        } else {
            ++summary.control_invalid_count;
        }
    }

    if (input.peek() != std::char_traits<char>::eof()) {
        throw std::runtime_error("native block-suite input has trailing bytes");
    }
    if (input.bad()) {
        throw std::runtime_error("failed while checking block-suite input EOF");
    }
    output << "END\t" << summary.case_count << '\t'
           << summary.control_valid_count << '\t'
           << summary.control_invalid_count << '\n';
    if (!output) {
        throw std::runtime_error("failed to write native block-suite output");
    }
    return summary;
}

BlockCliSummary WriteBlockSuiteFiles(const std::string &input_path,
                                     const std::string &output_path) {
    std::ifstream input(input_path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("failed to open block-suite input");
    }
    std::ofstream output(output_path,
                         std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error("failed to create block-suite output");
    }
    const BlockCliSummary summary = RunBlockSuiteStreams(input, output);
    output.flush();
    if (!output) {
        throw std::runtime_error("failed to flush block-suite output");
    }
    return summary;
}

} // namespace saq::a4_1s

#include "native_cli.hpp"

#include "block_vq.hpp"
#include "exact_quantizer.hpp"
#include "representation.hpp"

#include <openssl/evp.h>

#include <algorithm>
#include <array>
#include <bit>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <memory>
#include <sstream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace saq::a4_v2::producer {
namespace {

constexpr std::string_view kHashDomain =
    "saq-attempt4-a4-1-20260713-schema2";

class Reader {
 public:
  explicit Reader(const std::string& path) : input_(path, std::ios::binary) {
    if (!input_) throw std::runtime_error("cannot open native input");
  }

  void Require(std::string_view expected, const char* field) {
    std::string value(expected.size(), '\0');
    Read(value.data(), value.size(), field);
    if (value != expected) {
      throw std::runtime_error(std::string(field) + " magic mismatch");
    }
  }
  [[nodiscard]] std::uint8_t U8(const char* field) {
    std::uint8_t value = 0;
    Read(reinterpret_cast<char*>(&value), 1, field);
    return value;
  }
  [[nodiscard]] std::uint32_t U32(const char* field) {
    std::array<unsigned char, 4> bytes{};
    Read(reinterpret_cast<char*>(bytes.data()), bytes.size(), field);
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8U) |
           (static_cast<std::uint32_t>(bytes[2]) << 16U) |
           (static_cast<std::uint32_t>(bytes[3]) << 24U);
  }
  [[nodiscard]] std::int32_t I32(const char* field) {
    return std::bit_cast<std::int32_t>(U32(field));
  }
  [[nodiscard]] std::uint64_t U64(const char* field) {
    std::array<unsigned char, 8> bytes{};
    Read(reinterpret_cast<char*>(bytes.data()), bytes.size(), field);
    std::uint64_t result = 0;
    for (std::size_t index = 0; index < bytes.size(); ++index) {
      result |= static_cast<std::uint64_t>(bytes[index]) << (8U * index);
    }
    return result;
  }
  [[nodiscard]] std::string Bytes(std::size_t size, const char* field) {
    std::string result(size, '\0');
    Read(result.data(), result.size(), field);
    return result;
  }
  [[nodiscard]] std::string Decimal(bool positive, const char* field) {
    const std::uint32_t size = U32(field);
    if (size == 0) throw std::runtime_error("empty decimal field");
    const std::string result = Bytes(size, field);
    if (!std::all_of(result.begin(), result.end(), [](unsigned char byte) {
          return std::isdigit(byte) != 0;
        }) ||
        (result.size() > 1 && result.front() == '0') ||
        (positive && result == "0")) {
      throw std::runtime_error("noncanonical decimal field");
    }
    return result;
  }
  void Eof() {
    char byte = 0;
    if (input_.read(&byte, 1) || !input_.eof() || input_.bad()) {
      throw std::runtime_error("native input has trailing bytes");
    }
  }

 private:
  void Read(char* destination, std::size_t size, const char* field) {
    input_.read(destination, static_cast<std::streamsize>(size));
    if (!input_) throw std::runtime_error(std::string("truncated ") + field);
  }
  std::ifstream input_;
};

class Writer {
 public:
  explicit Writer(const std::string& path)
      : output_(path, std::ios::binary | std::ios::trunc) {
    if (!output_) throw std::runtime_error("cannot create native output");
  }
  void Bytes(std::string_view bytes) {
    output_.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    Good();
  }
  void U8(std::uint8_t value) {
    output_.put(static_cast<char>(value));
    Good();
  }
  void U32(std::uint32_t value) {
    std::array<char, 4> bytes{};
    for (std::size_t index = 0; index < bytes.size(); ++index) {
      bytes[index] = static_cast<char>(value >> (8U * index));
    }
    Bytes(std::string_view(bytes.data(), bytes.size()));
  }
  void I32(std::int32_t value) { U32(std::bit_cast<std::uint32_t>(value)); }
  void U64(std::uint64_t value) {
    std::array<char, 8> bytes{};
    for (std::size_t index = 0; index < bytes.size(); ++index) {
      bytes[index] = static_cast<char>(value >> (8U * index));
    }
    Bytes(std::string_view(bytes.data(), bytes.size()));
  }
  void Finish() {
    output_.flush();
    Good();
  }

 private:
  void Good() {
    if (!output_) throw std::runtime_error("native output write failed");
  }
  std::ofstream output_;
};

[[nodiscard]] std::string Hex32(std::uint32_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::nouppercase << std::setw(8)
         << std::setfill('0') << value;
  return output.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::nouppercase << std::setw(16)
         << std::setfill('0') << value;
  return output.str();
}

[[nodiscard]] std::string DigestHex(const Digest& digest) {
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setfill('0');
  for (const std::uint8_t byte : digest) {
    output << std::setw(2) << static_cast<unsigned int>(byte);
  }
  return output.str();
}

[[nodiscard]] std::string FailureName(BlockFailure failure) {
  switch (failure) {
    case BlockFailure::kNone: return "NONE";
    case BlockFailure::kNonfinite: return "NONFINITE_CONTROL";
    case BlockFailure::kSseIncrease: return "CANDIDATE_SSE_INCREASE";
    case BlockFailure::kIterationLimit: return "ITERATION_LIMIT";
    case BlockFailure::kSerializedCollision: return "SERIALIZED_CENTER_COLLISION";
    case BlockFailure::kCartesianDominance: return "CARTESIAN_DOMINANCE";
  }
  throw std::logic_error("unknown block failure");
}

[[nodiscard]] std::uint32_t PredecessorLayer(const ScalarCurve& curve,
                                             std::uint32_t requested) {
  return std::min<std::uint32_t>(
      requested, static_cast<std::uint32_t>(curve.predecessors.size() - 1));
}

[[nodiscard]] ScaledRational ReadObjective(Reader* reader) {
  const std::int32_t exponent = reader->I32("objective exponent");
  const std::string numerator = reader->Decimal(false, "objective numerator");
  const std::string denominator = reader->Decimal(true, "objective denominator");
  if (exponent != -298) throw std::runtime_error("objective exponent is not -298");
  ScaledRational result(mpz_class(numerator, 10), mpz_class(denominator, 10),
                        exponent);
  if (result.numerator < 0 || result.numerator.get_str() != numerator ||
      result.denominator.get_str() != denominator) {
    throw std::runtime_error("objective rational is noncanonical");
  }
  return result;
}

void WriteObjective(Writer* writer, const ScaledRational& value) {
  if (value.binary_exponent != -298 || value.numerator < 0 ||
      value.denominator <= 0) {
    throw std::logic_error("invalid allocation objective");
  }
  const std::string numerator = value.numerator.get_str();
  const std::string denominator = value.denominator.get_str();
  writer->I32(value.binary_exponent);
  writer->U32(static_cast<std::uint32_t>(numerator.size()));
  writer->Bytes(numerator);
  writer->U32(static_cast<std::uint32_t>(denominator.size()));
  writer->Bytes(denominator);
}

[[nodiscard]] ScalarCurve ReadCurve(Reader* reader,
                                    std::uint32_t maximum_cardinality) {
  ScalarCurve result;
  result.solutions.resize(maximum_cardinality + 1);
  for (std::uint32_t cardinality = 1; cardinality <= maximum_cardinality;
       ++cardinality) {
    ScalarSolution solution;
    solution.requested_cardinality = cardinality;
    solution.effective_cardinality = reader->U32("effective cardinality");
    solution.sse = ReadObjective(reader);
    if (solution.effective_cardinality == 0 ||
        solution.effective_cardinality > cardinality) {
      throw std::runtime_error("invalid effective cardinality");
    }
    result.solutions[cardinality] = std::move(solution);
  }
  const std::uint32_t support =
      result.solutions[maximum_cardinality].effective_cardinality;
  for (std::uint32_t cardinality = 1; cardinality <= maximum_cardinality;
       ++cardinality) {
    if (result.at(cardinality).effective_cardinality !=
        std::min(cardinality, support)) {
      throw std::runtime_error("allocation curve violates at-most-K semantics");
    }
    if (cardinality > 1 &&
        result.at(cardinality).sse.coefficient() >
            result.at(cardinality - 1).sse.coefficient()) {
      throw std::runtime_error("allocation curve objective increases");
    }
  }
  return result;
}

void WriteScalarCase(std::ostream& output, std::uint32_t case_id,
                     const std::vector<WeightedBinary32>& samples,
                     std::uint32_t maximum_cardinality) {
  const ScalarCurve curve = FitExactScalarCurve(samples, maximum_cardinality);
  std::uint64_t total_comparisons = 0;
  std::uint64_t total_ties = 0;
  for (std::uint32_t k = 1; k <= maximum_cardinality; ++k) {
    total_comparisons += curve.at(k).comparison_count;
    total_ties += curve.at(k).tie_count;
  }
  output << "CASE\t" << case_id << '\t' << samples.size() << '\t'
         << maximum_cardinality << '\t' << curve.support.size() << '\t'
         << total_comparisons << '\t' << total_ties << "\t0\t0\t"
         << std::min<std::size_t>(maximum_cardinality, curve.support.size())
         << '\n';
  for (std::size_t index = 0; index < curve.support.size(); ++index) {
    output << "SUPPORT\t" << case_id << '\t' << index << '\t'
           << curve.support[index].grid_integer.get_str() << '\t'
           << curve.support[index].weight.get_str() << '\t'
           << curve.support[index].lowest_vector_id << '\n';
  }
  for (std::uint32_t k = 1; k <= maximum_cardinality; ++k) {
    const ScalarSolution& solution = curve.at(k);
    output << "SOLUTION\t" << case_id << '\t' << k << '\t'
           << solution.effective_cardinality << '\t'
           << solution.sse.numerator.get_str() << '\t'
           << solution.sse.denominator.get_str() << '\t'
           << solution.sse.binary_exponent << '\t' << solution.intervals.size()
           << '\t' << solution.comparison_count << '\t' << solution.tie_count
           << '\n';
    for (std::size_t cluster = 0; cluster < solution.intervals.size();
         ++cluster) {
      const ScalarInterval& interval = solution.intervals[cluster];
      output << "CLUSTER\t" << case_id << '\t' << k << '\t' << cluster
             << '\t' << interval.begin << '\t' << interval.end << '\t'
             << interval.mean.numerator.get_str() << '\t'
             << interval.mean.denominator.get_str() << '\t'
             << interval.mean.binary_exponent << '\t'
             << Hex32(RoundToBinary32(interval.mean)) << '\t'
             << Hex64(RoundToBinary64(interval.mean)) << '\n';
    }
    const std::uint32_t layer = PredecessorLayer(curve, k);
    output << "PREDECESSOR_ROW\t" << case_id << '\t' << k << '\t'
           << curve.predecessors[layer].size();
    for (const std::uint32_t predecessor : curve.predecessors[layer]) {
      output << '\t' << predecessor;
    }
    output << '\n';
  }
  for (std::size_t layer = 1; layer < curve.predecessor_monotone.size();
       ++layer) {
    output << "MONOTONE\t" << case_id << '\t' << layer << '\t'
           << static_cast<unsigned int>(curve.predecessor_monotone[layer])
           << '\n';
  }
  output << "END_CASE\t" << case_id << '\n';
}

}  // namespace

void WriteScalarSuite(const std::string& input_path,
                      const std::string& output_path) {
  Reader reader(input_path);
  reader.Require("A4SCL001", "scalar input");
  const std::uint32_t cases = reader.U32("scalar case count");
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create scalar output");
  output << "A4S_SCALAR_RESULT_V1\n";
  for (std::uint32_t index = 0; index < cases; ++index) {
    const std::uint32_t case_id = reader.U32("scalar case id");
    const std::uint32_t sample_count = reader.U32("scalar sample count");
    const std::uint32_t maximum = reader.U32("scalar maximum K");
    if (sample_count == 0 || maximum == 0 || maximum > 256) {
      throw std::runtime_error("invalid scalar case shape");
    }
    std::vector<WeightedBinary32> samples;
    samples.reserve(sample_count);
    for (std::uint32_t sample = 0; sample < sample_count; ++sample) {
      samples.push_back(WeightedBinary32{reader.U32("scalar bits"),
                                         reader.U64("scalar weight"),
                                         reader.U64("scalar vector id")});
    }
    WriteScalarCase(output, case_id, samples, maximum);
  }
  reader.Eof();
  output << "END\t" << cases << '\n';
  output.flush();
  if (!output) throw std::runtime_error("scalar output failed");
}

void WriteScalarParitySuite(const std::string& input_path,
                            const std::string& output_path) {
  Reader reader(input_path);
  reader.Require("A4SCL001", "scalar parity input");
  const std::uint32_t cases = reader.U32("scalar parity case count");
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create scalar parity output");
  output << "A4V2_PAR_SCALAR_V1\n";
  for (std::uint32_t index = 0; index < cases; ++index) {
    const std::uint32_t case_id = reader.U32("scalar parity case id");
    const std::uint32_t sample_count = reader.U32("scalar parity sample count");
    const std::uint32_t maximum = reader.U32("scalar parity maximum K");
    if (sample_count == 0 || maximum == 0 || maximum > 8) {
      throw std::runtime_error("invalid scalar parity case shape");
    }
    std::vector<WeightedBinary32> samples;
    samples.reserve(sample_count);
    for (std::uint32_t sample = 0; sample < sample_count; ++sample) {
      samples.push_back(WeightedBinary32{
          reader.U32("scalar parity bits"),
          reader.U64("scalar parity weight"),
          reader.U64("scalar parity vector id")});
    }
    const ScalarCurve curve = FitExactScalarCurve(samples, maximum);
    if (curve.support.size() > 12) {
      throw std::runtime_error("scalar parity support exceeds H=12 bound");
    }
    output << "CASE\t" << case_id << '\t' << sample_count << '\t'
           << maximum << '\t' << curve.support.size() << '\n';
    for (std::size_t support = 0; support < curve.support.size(); ++support) {
      output << "SUPPORT\t" << case_id << '\t' << support << '\t'
             << curve.support[support].grid_integer.get_str() << '\t'
             << curve.support[support].weight.get_str() << '\t'
             << curve.support[support].lowest_vector_id << '\n';
    }
    for (std::uint32_t requested = 1; requested <= maximum; ++requested) {
      const ScalarSolution& solution = curve.at(requested);
      output << "SOLUTION\t" << case_id << '\t' << requested << '\t'
             << solution.effective_cardinality << '\t'
             << solution.sse.numerator.get_str() << '\t'
             << solution.sse.denominator.get_str() << '\t'
             << solution.sse.binary_exponent << '\t'
             << solution.intervals.size() << '\n';
      for (std::size_t cluster = 0; cluster < solution.intervals.size();
           ++cluster) {
        const ScalarInterval& interval = solution.intervals[cluster];
        output << "CLUSTER\t" << case_id << '\t' << requested << '\t'
               << cluster << '\t' << interval.begin << '\t' << interval.end
               << '\t' << interval.mean.numerator.get_str() << '\t'
               << interval.mean.denominator.get_str() << '\t'
               << interval.mean.binary_exponent << '\t'
               << Hex32(RoundToBinary32(interval.mean)) << '\t'
               << Hex64(RoundToBinary64(interval.mean)) << '\n';
      }
      const std::uint32_t layer = PredecessorLayer(curve, requested);
      output << "PREDECESSOR_ROW\t" << case_id << '\t' << requested << '\t'
             << (curve.support.size() - layer + 1);
      for (std::size_t prefix = layer; prefix <= curve.support.size();
           ++prefix) {
        output << '\t' << curve.predecessors[layer][prefix];
      }
      output << '\n';
    }
    for (std::size_t layer = 1; layer < curve.predecessor_monotone.size();
         ++layer) {
      output << "MONOTONE\t" << case_id << '\t' << layer << '\t'
             << static_cast<unsigned int>(curve.predecessor_monotone[layer])
             << '\n';
    }
    output << "END_CASE\t" << case_id << '\n';
  }
  reader.Eof();
  output << "END\t" << cases << '\n';
  output.flush();
  if (!output) throw std::runtime_error("scalar parity output failed");
}

void WriteAllocationItem(const std::string& input_path,
                         const std::string& output_path) {
  Reader reader(input_path);
  reader.Require("A4ALI001", "allocation input");
  if (reader.U32("allocation version") != 1) {
    throw std::runtime_error("allocation version mismatch");
  }
  const std::uint32_t kind = reader.U32("allocation kind");
  const std::uint32_t item_id = reader.U32("allocation item id");
  Writer writer(output_path);
  writer.Bytes("A4ALO001");
  writer.U32(1);
  writer.U32(kind);
  writer.U32(item_id);
  if (kind == 1) {
    const std::uint32_t capacity = reader.U32("product capacity");
    const std::uint32_t cardinality_set = reader.U32("cardinality set");
    const std::uint32_t curve_count = reader.U32("curve count");
    const std::uint32_t maximum = reader.U32("curve maximum");
    if ((capacity != 16 && capacity != 256) || cardinality_set > 1 ||
        curve_count != 2 || maximum != capacity || item_id >= 256) {
      throw std::runtime_error("product descriptor mismatch");
    }
    const std::uint32_t first_id = reader.U32("first curve id");
    const ScalarCurve first = ReadCurve(&reader, maximum);
    const std::uint32_t second_id = reader.U32("second curve id");
    const ScalarCurve second = ReadCurve(&reader, maximum);
    if (first_id >= 128 || (first_id % 2) != 0 ||
        second_id != first_id + 1) {
      throw std::runtime_error("product coordinate pair mismatch");
    }
    const std::uint32_t rate_index = capacity == 16 ? 0U : 1U;
    const std::uint32_t expected_item =
        ((rate_index * 64U + first_id / 2U) * 2U) + cardinality_set;
    if (item_id != expected_item) {
      throw std::runtime_error("product item id does not bind rate/group/set");
    }
    reader.Require("A4AIEND1", "allocation terminal");
    reader.Eof();
    const ProductAllocation result = AllocateProduct2(
        first, second, capacity,
        cardinality_set == 0 ? ProductCardinalitySet::kArbitrary
                             : ProductCardinalitySet::kDyadic);
    const bool first_reachable =
        first.at(result.first_cardinality).effective_cardinality ==
        result.first_cardinality;
    const bool second_reachable =
        second.at(result.second_cardinality).effective_cardinality ==
        result.second_cardinality;
    writer.U32(capacity);
    writer.U32(cardinality_set);
    writer.U32(2);
    writer.U32(first_id);
    writer.U32(result.first_cardinality);
    writer.U32(first.at(result.first_cardinality).effective_cardinality);
    writer.U8(first_reachable ? 1 : 0);
    writer.U32(second_id);
    writer.U32(result.second_cardinality);
    writer.U32(second.at(result.second_cardinality).effective_cardinality);
    writer.U8(second_reachable ? 1 : 0);
    writer.U64(result.used_states);
    writer.U8(result.nominal_alphabets_reachable ? 1 : 0);
    WriteObjective(&writer, result.sse);
    writer.U64(result.enumerated_candidate_count);
  } else if (kind == 2) {
    const std::uint32_t budget = reader.U32("global bit budget");
    const std::uint32_t curve_count = reader.U32("global curve count");
    const std::uint32_t maximum = reader.U32("global maximum K");
    if ((budget != 256 && budget != 512) || curve_count != 128 ||
        maximum != 256 || item_id != (budget == 256 ? 256U : 257U)) {
      throw std::runtime_error("global descriptor mismatch");
    }
    std::vector<ScalarCurve> curves;
    curves.reserve(curve_count);
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
      if (reader.U32("global coordinate id") != coordinate) {
        throw std::runtime_error("global curve order mismatch");
      }
      curves.push_back(ReadCurve(&reader, maximum));
    }
    reader.Require("A4AIEND1", "allocation terminal");
    reader.Eof();
    const GlobalAllocation result = AllocateGlobalDyadicCap8(curves, budget);
    writer.U32(budget);
    writer.U32(curve_count);
    writer.U32(result.used_bits);
    writer.U8(result.nominal_alphabets_reachable ? 1 : 0);
    WriteObjective(&writer, result.sse);
    writer.U64(result.enumerated_transition_count);
    writer.U32(curve_count);
    for (std::uint32_t coordinate = 0; coordinate < curve_count; ++coordinate) {
      const std::uint8_t width = result.bit_widths[coordinate];
      const std::uint32_t requested = 1U << width;
      const std::uint32_t effective =
          curves[coordinate].at(requested).effective_cardinality;
      writer.U32(coordinate);
      writer.U8(width);
      writer.U32(requested);
      writer.U32(effective);
      writer.U8(effective == requested ? 1 : 0);
    }
  } else {
    throw std::runtime_error("allocation kind must be 1 or 2");
  }
  writer.Bytes("A4AOEND1");
  writer.Finish();
}

namespace {

struct BlockCase {
  std::uint32_t case_id{0};
  BlockMetadata metadata;
  std::vector<Point2> points;
  std::vector<double> axis0;
  std::vector<double> axis1;
  std::vector<std::uint64_t> axis0_bits;
  std::vector<std::uint64_t> axis1_bits;
};

[[nodiscard]] BlockCase ReadBlockCase(Reader* reader, bool parity_capacity) {
  BlockCase result;
  result.case_id = reader->U32("block case id");
  result.metadata.capacity = reader->U32("block capacity");
  result.metadata.group_id = reader->U32("block group id");
  const std::uint32_t dataset_size = reader->U32("dataset id size");
  if (dataset_size == 0 || dataset_size > (1U << 20U)) {
    throw std::runtime_error("invalid block dataset id size");
  }
  result.metadata.dataset_id = reader->Bytes(dataset_size, "dataset id");
  if (result.metadata.dataset_id.find_first_of("\t\n\r|") !=
      std::string::npos) {
    throw std::runtime_error("block dataset id contains delimiter");
  }
  result.metadata.hash_domain = std::string(kHashDomain);
  const std::uint32_t point_count = reader->U32("block point count");
  const std::uint32_t axis0_count = reader->U32("block axis0 count");
  const std::uint32_t axis1_count = reader->U32("block axis1 count");
  const bool capacity_valid =
      parity_capacity
          ? result.metadata.capacity >= 2 && result.metadata.capacity <= 256
          : result.metadata.capacity == 16 || result.metadata.capacity == 256;
  if (point_count == 0 || (parity_capacity && point_count > 256) ||
      !capacity_valid ||
      result.metadata.capacity > point_count || axis0_count == 0 ||
      axis1_count == 0 ||
      static_cast<std::uint64_t>(axis0_count) * axis1_count >
          result.metadata.capacity) {
    throw std::runtime_error("invalid block case shape");
  }
  result.points.reserve(point_count);
  for (std::uint32_t row = 0; row < point_count; ++row) {
    const std::uint32_t x = reader->U32("block x bits");
    const std::uint32_t y = reader->U32("block y bits");
    const std::uint64_t cell = reader->U64("block cell id");
    const std::uint64_t vector = reader->U64("block vector id");
    result.points.push_back(MakePoint(std::bit_cast<float>(x),
                                      std::bit_cast<float>(y), cell, vector,
                                      result.metadata.hash_domain,
                                      result.metadata.dataset_id));
  }
  for (std::uint32_t index = 0; index < axis0_count; ++index) {
    const std::uint64_t bits = reader->U64("block axis0 bits");
    result.axis0_bits.push_back(bits);
    result.axis0.push_back(std::bit_cast<double>(bits));
  }
  for (std::uint32_t index = 0; index < axis1_count; ++index) {
    const std::uint64_t bits = reader->U64("block axis1 bits");
    result.axis1_bits.push_back(bits);
    result.axis1.push_back(std::bit_cast<double>(bits));
  }
  return result;
}

void EmitBlockStart(std::ostream& output, std::uint32_t case_id,
                    const std::vector<Point2>& points,
                    const BlockStartTrace& start) {
  output << "START\t" << case_id << '\t' << start.start_id << '\t'
         << DigestHex(start.first_seed_digest) << '\t'
         << start.initialization_vector_ids.size() << '\t'
         << start.initial_centers.size() << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(start.initial_sse)) << '\t'
         << start.steps.size() << '\t' << start.steps.size() << '\t'
         << static_cast<unsigned int>(start.converged) << '\t'
         << FailureName(start.failure) << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(start.final_sse)) << '\t'
         << start.final_assignments.size() << '\t'
         << start.final_centers.size() << '\t'
         << start.serialized_final_centers.size() << '\t'
         << start.distinct_serialized_center_count << '\t'
         << start.distance_comparison_count << '\t'
         << start.assignment_tie_count << '\t' << start.farthest_tie_count
         << '\n';
  for (std::size_t index = 0;
       index < start.initialization_vector_ids.size(); ++index) {
    output << "START_SELECTED\t" << case_id << '\t' << start.start_id << '\t'
           << index << '\t' << start.initialization_vector_ids[index] << '\n';
  }
  for (std::size_t center = 0; center < start.initial_centers.size(); ++center) {
    output << "START_CENTER\t" << case_id << '\t' << start.start_id << '\t'
           << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.initial_centers[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.initial_centers[center].y))
           << '\n';
  }
  for (const BlockStep& step : start.steps) {
    output << "STEP\t" << case_id << '\t' << start.start_id << '\t'
           << step.iteration << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(step.prior_sse)) << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(step.candidate_sse)) << '\t'
           << step.changed_assignment_count << '\t'
           << step.empty_center_ids.size() << '\t'
           << step.centers_after.size() << '\n';
    for (std::size_t index = 0; index < step.empty_center_ids.size(); ++index) {
      output << "STEP_EMPTY\t" << case_id << '\t' << start.start_id << '\t'
             << step.iteration << '\t' << index << '\t'
             << step.empty_center_ids[index] << '\n';
    }
    for (std::size_t center = 0; center < step.centers_after.size(); ++center) {
      output << "STEP_CENTER\t" << case_id << '\t' << start.start_id << '\t'
             << step.iteration << '\t' << center << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(step.centers_after[center].x))
             << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(step.centers_after[center].y))
             << '\n';
    }
    if (step.assignments_before.size() != points.size() ||
        step.assignments_after.size() != points.size()) {
      throw std::logic_error("block step assignment preimage shape mismatch");
    }
    // C_core transports the complete scientific preimages.  All BEFORE rows
    // precede all AFTER rows so the Python conductor can reject truncation or
    // interleaving without regenerating assignments during E_emit.
    for (std::size_t row = 0; row < points.size(); ++row) {
      output << "STEP_ASSIGNMENT_BEFORE\t" << case_id << '\t'
             << start.start_id << '\t' << step.iteration << '\t' << row
             << '\t' << points[row].vector_id << '\t'
             << step.assignments_before[row] << '\n';
    }
    for (std::size_t row = 0; row < points.size(); ++row) {
      output << "STEP_ASSIGNMENT_AFTER\t" << case_id << '\t'
             << start.start_id << '\t' << step.iteration << '\t' << row
             << '\t' << points[row].vector_id << '\t'
             << step.assignments_after[row] << '\n';
    }
  }
  for (std::size_t row = 0; row < start.final_assignments.size(); ++row) {
    output << "FINAL_ASSIGNMENT\t" << case_id << '\t' << start.start_id
           << '\t' << row << '\t' << points[row].vector_id << '\t'
           << start.final_assignments[row] << '\n';
  }
  for (std::size_t center = 0; center < start.final_centers.size(); ++center) {
    output << "FINAL_CENTER\t" << case_id << '\t' << start.start_id << '\t'
           << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.final_centers[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(start.final_centers[center].y))
           << '\n';
  }
  for (std::size_t center = 0;
       center < start.serialized_final_centers.size(); ++center) {
    output << "FINAL_SERIALIZED_CENTER\t" << case_id << '\t'
           << start.start_id << '\t' << center << '\t'
           << Hex32(start.serialized_final_centers[center].x_bits) << '\t'
           << Hex32(start.serialized_final_centers[center].y_bits) << '\n';
  }
  output << "END_START\t" << case_id << '\t' << start.start_id << '\n';
}

void EmitBlockCase(std::ostream& output, const BlockCase& input,
                   const BlockResult& result) {
  output << "CASE\t" << input.case_id << '\t' << input.metadata.hash_domain
         << '\t' << input.metadata.dataset_id << '\t'
         << input.metadata.capacity << '\t' << input.metadata.group_id << '\t'
         << input.points.size() << '\t' << input.axis0.size() << '\t'
         << input.axis1.size() << '\t'
         << static_cast<unsigned int>(result.control_valid) << '\t'
         << FailureName(result.failure) << '\t' << result.failed_start_id
         << '\t' << result.failure_detail << '\n';
  for (std::size_t index = 0; index < input.axis0_bits.size(); ++index) {
    output << "AXIS\t" << input.case_id << "\t0\t" << index << '\t'
           << Hex64(input.axis0_bits[index]) << '\n';
  }
  for (std::size_t index = 0; index < input.axis1_bits.size(); ++index) {
    output << "AXIS\t" << input.case_id << "\t1\t" << index << '\t'
           << Hex64(input.axis1_bits[index]) << '\n';
  }
  for (std::size_t row = 0; row < result.ordered_points.size(); ++row) {
    const Point2& point = result.ordered_points[row];
    output << "ROW\t" << input.case_id << '\t' << row << '\t'
           << point.cell_id << '\t' << point.vector_id << '\t'
           << DigestHex(point.selection_digest) << '\t'
           << Hex32(std::bit_cast<std::uint32_t>(point.x)) << '\t'
           << Hex32(std::bit_cast<std::uint32_t>(point.y)) << '\n';
  }
  output << "CARTESIAN\t" << input.case_id << '\t'
         << result.cartesian_centers.size() << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(result.cartesian_sse)) << '\t'
         << Hex64(std::bit_cast<std::uint64_t>(result.filled_sse)) << '\n';
  for (std::size_t center = 0; center < result.cartesian_centers.size();
       ++center) {
    output << "CARTESIAN_CENTER\t" << input.case_id << '\t' << center << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(result.cartesian_centers[center].x))
           << '\t'
           << Hex64(std::bit_cast<std::uint64_t>(result.cartesian_centers[center].y))
           << '\n';
  }
  for (const BlockStartTrace& start : result.starts) {
    EmitBlockStart(output, input.case_id, result.ordered_points, start);
  }
  if (!result.control_valid) {
    output << "BEST\t" << input.case_id << "\t0\n";
  } else {
    const BlockStartTrace& best = result.starts[result.best_start_id];
    output << "BEST\t" << input.case_id << "\t1\t" << result.best_start_id
           << '\t' << Hex64(std::bit_cast<std::uint64_t>(best.final_sse))
           << '\t' << best.final_centers.size() << '\t'
           << best.final_assignments.size() << '\t'
           << best.serialized_final_centers.size() << '\n';
    for (std::size_t center = 0; center < best.final_centers.size(); ++center) {
      output << "BEST_CENTER\t" << input.case_id << '\t' << center << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(best.final_centers[center].x))
             << '\t'
             << Hex64(std::bit_cast<std::uint64_t>(best.final_centers[center].y))
             << '\t' << Hex32(best.serialized_final_centers[center].x_bits)
             << '\t' << Hex32(best.serialized_final_centers[center].y_bits)
             << '\n';
    }
    for (std::size_t row = 0; row < best.final_assignments.size(); ++row) {
      output << "BEST_ASSIGNMENT\t" << input.case_id << '\t' << row << '\t'
             << result.ordered_points[row].vector_id << '\t'
             << best.final_assignments[row] << '\n';
    }
  }
  output << "END_CASE\t" << input.case_id << '\n';
}

}  // namespace

namespace {

void WriteBlockSuiteImpl(const std::string& input_path,
                         const std::string& output_path,
                         bool parity_capacity) {
  Reader reader(input_path);
  reader.Require("A4BLK001", "block input");
  const std::uint32_t cases = reader.U32("block case count");
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create block output");
  output << "A4S_BLOCK_RESULT_V1\nPROTOCOL\t" << kHashDomain << '\n';
  std::uint32_t valid = 0;
  for (std::uint32_t index = 0; index < cases; ++index) {
    const BlockCase input = ReadBlockCase(&reader, parity_capacity);
    const BlockResult result =
        parity_capacity
            ? TrainBlockVqParity(input.points, input.metadata, input.axis0,
                                 input.axis1)
            : TrainBlockVq(input.points, input.metadata, input.axis0,
                           input.axis1);
    EmitBlockCase(output, input, result);
    valid += result.control_valid ? 1U : 0U;
  }
  reader.Eof();
  output << "END\t" << cases << '\t' << valid << '\t' << (cases - valid)
         << '\n';
  output.flush();
  if (!output) throw std::runtime_error("block output failed");
}

}  // namespace

void WriteBlockSuite(const std::string& input_path,
                     const std::string& output_path) {
  WriteBlockSuiteImpl(input_path, output_path, false);
}

void WriteBlockParitySuite(const std::string& input_path,
                           const std::string& output_path) {
  WriteBlockSuiteImpl(input_path, output_path, true);
}

namespace {

struct ScalarPairModel {
  std::vector<std::uint32_t> axis0;
  std::vector<std::uint32_t> axis1;
};

struct EncodingInput {
  std::uint32_t arm{0};
  std::uint32_t word_bits{0};
  std::uint32_t rows{0};
  std::vector<std::uint32_t> matrix;
  std::vector<ScalarPairModel> scalar_groups;
  std::vector<std::vector<PointBits2>> block_groups;
  std::vector<std::uint8_t> global_widths;
  std::vector<std::vector<std::uint32_t>> global_centroids;
};

[[nodiscard]] EncodingInput ReadEncodingInput(const std::string& path) {
  Reader reader(path);
  reader.Require("A4ENC002", "encoding input");
  if (reader.U32("encoding version") != 2) {
    throw std::runtime_error("encoding version mismatch");
  }
  EncodingInput result;
  result.arm = reader.U32("encoding arm");
  result.word_bits = reader.U32("encoding word bits");
  result.rows = reader.U32("encoding rows");
  const std::uint32_t dimensions = reader.U32("encoding dimensions");
  const std::uint32_t groups = reader.U32("encoding groups");
  const std::uint64_t values = reader.U64("encoding value count");
  if (result.arm > 3 || (result.word_bits != 4 && result.word_bits != 8) ||
      result.rows == 0 || result.rows > 8192 || dimensions != 128 ||
      groups != 64 || values != static_cast<std::uint64_t>(result.rows) * 128) {
    throw std::runtime_error("encoding header mismatch");
  }
  result.matrix.reserve(static_cast<std::size_t>(values));
  for (std::uint64_t index = 0; index < values; ++index) {
    result.matrix.push_back(reader.U32("encoding matrix bits"));
  }
  if (reader.U32("encoding model arm") != result.arm) {
    throw std::runtime_error("encoding model arm mismatch");
  }
  const std::uint32_t capacity = 1U << result.word_bits;
  if (result.arm <= 1) {
    result.scalar_groups.reserve(64);
    for (std::uint32_t group = 0; group < 64; ++group) {
      if (reader.U32("scalar model group") != group) {
        throw std::runtime_error("scalar model group order");
      }
      const std::uint32_t first = reader.U32("scalar model K0");
      const std::uint32_t second = reader.U32("scalar model K1");
      if (first == 0 || second == 0 ||
          static_cast<std::uint64_t>(first) * second > capacity) {
        throw std::runtime_error("scalar model cardinality invalid");
      }
      ScalarPairModel model;
      for (std::uint32_t index = 0; index < first; ++index) {
        model.axis0.push_back(reader.U32("scalar axis0 bits"));
      }
      for (std::uint32_t index = 0; index < second; ++index) {
        model.axis1.push_back(reader.U32("scalar axis1 bits"));
      }
      result.scalar_groups.push_back(std::move(model));
    }
  } else if (result.arm == 2) {
    result.block_groups.reserve(64);
    for (std::uint32_t group = 0; group < 64; ++group) {
      if (reader.U32("block model group") != group ||
          reader.U32("block model centers") != capacity) {
        throw std::runtime_error("block model shape mismatch");
      }
      std::vector<PointBits2> centers;
      centers.reserve(capacity);
      for (std::uint32_t center = 0; center < capacity; ++center) {
        centers.push_back(PointBits2{reader.U32("block model x"),
                                     reader.U32("block model y")});
      }
      result.block_groups.push_back(std::move(centers));
    }
  } else {
    result.global_widths.reserve(128);
    result.global_centroids.reserve(128);
    std::uint32_t used_bits = 0;
    for (std::uint32_t coordinate = 0; coordinate < 128; ++coordinate) {
      if (reader.U32("global coordinate") != coordinate) {
        throw std::runtime_error("global coordinate order mismatch");
      }
      const std::uint32_t width = reader.U32("global width");
      const std::uint32_t cardinality = reader.U32("global cardinality");
      if (width > 8 || cardinality != (1U << width)) {
        throw std::runtime_error("global width/cardinality mismatch");
      }
      used_bits += width;
      result.global_widths.push_back(static_cast<std::uint8_t>(width));
      std::vector<std::uint32_t> centroids;
      centroids.reserve(cardinality);
      for (std::uint32_t index = 0; index < cardinality; ++index) {
        centroids.push_back(reader.U32("global centroid bits"));
      }
      result.global_centroids.push_back(std::move(centroids));
    }
    if (used_bits > 64U * result.word_bits) {
      throw std::runtime_error("global model exceeds paid bits");
    }
  }
  reader.Require("A4EIEND2", "encoding input terminal");
  if (reader.U32("encoding terminal rows") != result.rows ||
      reader.U32("encoding terminal arm") != result.arm) {
    throw std::runtime_error("encoding terminal descriptor mismatch");
  }
  reader.Eof();
  return result;
}

struct EncodedRow {
  std::vector<std::uint32_t> labels;
  std::vector<std::uint8_t> payload;
  std::vector<std::uint32_t> roundtrip;
  std::uint64_t comparisons{0};
  std::uint64_t pack_operations{0};
  std::uint64_t unpack_operations{0};
  std::uint64_t mixed_encodes{0};
  std::uint64_t mixed_decodes{0};
  bool control_valid{true};
};

[[nodiscard]] EncodedRow EncodeRow(const EncodingInput& input,
                                   std::uint32_t row) {
  EncodedRow result;
  RepresentationCounters counters;
  if (input.arm <= 1) {
    result.labels.reserve(64);
    for (std::size_t group = 0; group < 64; ++group) {
      const ScalarPairModel& model = input.scalar_groups[group];
      const std::array<std::uint32_t, 2> labels{
          AssignScalar(input.matrix[row * 128 + 2 * group], model.axis0,
                       &counters),
          AssignScalar(input.matrix[row * 128 + 2 * group + 1], model.axis1,
                       &counters)};
      const std::array<std::uint32_t, 2> radices{
          static_cast<std::uint32_t>(model.axis0.size()),
          static_cast<std::uint32_t>(model.axis1.size())};
      const std::uint64_t address =
          MixedRadixEncode(labels, radices, &counters);
      const std::vector<std::uint32_t> decoded =
          MixedRadixDecode(address, radices, &counters);
      result.control_valid =
          decoded == std::vector<std::uint32_t>(labels.begin(), labels.end()) &&
          result.control_valid;
      result.labels.push_back(static_cast<std::uint32_t>(address));
    }
    result.payload = PackMatched(result.labels, input.word_bits, &counters);
    result.roundtrip =
        UnpackMatched(result.payload, input.word_bits, &counters);
  } else if (input.arm == 2) {
    result.labels.reserve(64);
    for (std::size_t group = 0; group < 64; ++group) {
      result.labels.push_back(AssignPoint2(
          PointBits2{input.matrix[row * 128 + 2 * group],
                     input.matrix[row * 128 + 2 * group + 1]},
          input.block_groups[group], &counters));
    }
    result.payload = PackMatched(result.labels, input.word_bits, &counters);
    result.roundtrip =
        UnpackMatched(result.payload, input.word_bits, &counters);
  } else {
    result.labels.reserve(128);
    for (std::size_t coordinate = 0; coordinate < 128; ++coordinate) {
      result.labels.push_back(
          AssignScalar(input.matrix[row * 128 + coordinate],
                       input.global_centroids[coordinate], &counters));
    }
    GlobalPacked packed = PackGlobal(result.labels, input.global_widths,
                                     input.word_bits == 4 ? 32 : 64,
                                     &counters);
    result.payload = std::move(packed.bytes);
    result.roundtrip =
        UnpackGlobal(result.payload, input.global_widths, &counters);
  }
  result.control_valid = result.control_valid &&
                         result.labels == result.roundtrip &&
                         counters.pack_operations == 1 &&
                         counters.unpack_operations == 1;
  result.comparisons = counters.scalar_distances + counters.point_distances;
  result.pack_operations = counters.pack_operations;
  result.unpack_operations = counters.unpack_operations;
  result.mixed_encodes = counters.mixed_radix_encodes;
  result.mixed_decodes = counters.mixed_radix_decodes;
  return result;
}

}  // namespace

void WriteEncodingSuite(const std::string& input_path,
                        const std::string& output_path) {
  RepresentationSmoke();
  const EncodingInput input = ReadEncodingInput(input_path);
  Writer writer(output_path);
  writer.Bytes("A4EOUT02");
  writer.U32(2);
  writer.U32(input.arm);
  writer.U32(input.word_bits);
  writer.U32(input.rows);
  writer.U32(128);
  writer.U32(64);
  writer.U32(1);
  std::uint64_t total_comparisons = 0;
  std::uint64_t total_payload = 0;
  std::uint64_t total_pack = 0;
  std::uint64_t total_unpack = 0;
  std::uint64_t total_mixed_encode = 0;
  std::uint64_t total_mixed_decode = 0;
  std::uint64_t high_water =
      static_cast<std::uint64_t>(input.matrix.size()) * sizeof(std::uint32_t);
  for (std::uint32_t row = 0; row < input.rows; ++row) {
    const EncodedRow encoded = EncodeRow(input, row);
    writer.U32(0x31574f52U);
    writer.U32(row);
    writer.U32(input.arm);
    writer.U64(encoded.comparisons);
    writer.U32(static_cast<std::uint32_t>(encoded.labels.size()));
    for (const std::uint32_t label : encoded.labels) writer.U32(label);
    writer.U32(static_cast<std::uint32_t>(encoded.payload.size()));
    writer.Bytes(std::string_view(
        reinterpret_cast<const char*>(encoded.payload.data()),
        encoded.payload.size()));
    writer.U32(static_cast<std::uint32_t>(encoded.roundtrip.size()));
    for (const std::uint32_t label : encoded.roundtrip) writer.U32(label);
    writer.U32(encoded.control_valid ? 1U : 0U);
    writer.U64(encoded.pack_operations);
    writer.U64(encoded.unpack_operations);
    total_comparisons += encoded.comparisons;
    total_payload += encoded.payload.size();
    total_pack += encoded.pack_operations;
    total_unpack += encoded.unpack_operations;
    total_mixed_encode += encoded.mixed_encodes;
    total_mixed_decode += encoded.mixed_decodes;
    const std::uint64_t row_owned =
        static_cast<std::uint64_t>(encoded.labels.size() +
                                   encoded.roundtrip.size()) *
            sizeof(std::uint32_t) +
        encoded.payload.size();
    high_water = std::max(high_water,
                          static_cast<std::uint64_t>(input.matrix.size()) *
                                  sizeof(std::uint32_t) +
                              row_owned);
  }
  writer.Bytes("A4EOEND2");
  writer.U32(input.rows);
  writer.U32(1);
  writer.U32(input.arm);
  writer.U64(total_comparisons);
  writer.U64(total_payload);
  writer.U64(total_pack);
  writer.U64(total_unpack);
  writer.U64(total_mixed_encode);
  writer.U64(total_mixed_decode);
  writer.U64(input.rows);
  writer.U64(high_water);
  writer.Finish();
}

namespace {

[[nodiscard]] bool SameObjective(const ScaledRational& lhs,
                                 const ScaledRational& rhs) {
  return lhs.binary_exponent == rhs.binary_exponent &&
         lhs.numerator == rhs.numerator && lhs.denominator == rhs.denominator;
}

class Sha256Accumulator {
 public:
  Sha256Accumulator() : context_(EVP_MD_CTX_new(), EVP_MD_CTX_free) {
    if (context_ == nullptr ||
        EVP_DigestInit_ex(context_.get(), EVP_sha256(), nullptr) != 1) {
      throw std::runtime_error("cannot initialize representation SHA-256");
    }
  }
  void Update(std::string_view bytes) {
    if (finalized_ ||
        EVP_DigestUpdate(context_.get(), bytes.data(), bytes.size()) != 1) {
      throw std::runtime_error("cannot update representation SHA-256");
    }
  }
  [[nodiscard]] std::string FinalHex() {
    if (finalized_) throw std::logic_error("representation SHA-256 reused");
    std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
    unsigned int size = 0;
    if (EVP_DigestFinal_ex(context_.get(), digest.data(), &size) != 1 ||
        size != 32) {
      throw std::runtime_error("cannot finalize representation SHA-256");
    }
    finalized_ = true;
    std::ostringstream output;
    output << std::hex << std::nouppercase << std::setfill('0');
    for (unsigned int index = 0; index < size; ++index) {
      output << std::setw(2) << static_cast<unsigned int>(digest[index]);
    }
    return output.str();
  }

 private:
  std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> context_;
  bool finalized_{false};
};

struct ExhaustiveDecision {
  ProductAllocation allocation;
  std::uint32_t exact_objective_class_count{0};
};

[[nodiscard]] ExhaustiveDecision ExhaustiveProductByObjectiveClass(
    const ScalarCurve& first, const ScalarCurve& second,
    std::uint32_t capacity, ProductCardinalitySet set) {
  const std::uint32_t first_support =
      first.at(capacity).effective_cardinality;
  const std::uint32_t second_support =
      second.at(capacity).effective_cardinality;
  std::vector<std::vector<mpq_class>> sums(
      first_support + 1, std::vector<mpq_class>(second_support + 1));
  std::vector<mpq_class> distinct;
  distinct.reserve(static_cast<std::size_t>(first_support) * second_support);
  for (std::uint32_t a = 1; a <= first_support; ++a) {
    for (std::uint32_t b = 1; b <= second_support; ++b) {
      mpq_class sum = first.at(a).sse.coefficient() +
                      second.at(b).sse.coefficient();
      sum.canonicalize();
      sums[a][b] = sum;
      distinct.push_back(std::move(sum));
    }
  }
  std::sort(distinct.begin(), distinct.end(), [](const mpq_class& lhs,
                                                 const mpq_class& rhs) {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) < 0;
  });
  distinct.erase(std::unique(distinct.begin(), distinct.end(),
                             [](const mpq_class& lhs, const mpq_class& rhs) {
    return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) == 0;
  }), distinct.end());
  std::vector<std::vector<std::uint32_t>> rank(
      first_support + 1,
      std::vector<std::uint32_t>(second_support + 1, 0));
  for (std::uint32_t a = 1; a <= first_support; ++a) {
    for (std::uint32_t b = 1; b <= second_support; ++b) {
      const auto position = std::lower_bound(
          distinct.begin(), distinct.end(), sums[a][b],
          [](const mpq_class& lhs, const mpq_class& rhs) {
            return mpq_cmp(lhs.get_mpq_t(), rhs.get_mpq_t()) < 0;
          });
      if (position == distinct.end() ||
          mpq_cmp(position->get_mpq_t(), sums[a][b].get_mpq_t()) != 0) {
        throw std::logic_error("objective class lookup failed");
      }
      rank[a][b] = static_cast<std::uint32_t>(position - distinct.begin());
    }
  }

  bool found = false;
  std::uint32_t best_rank = 0;
  std::uint32_t best_first = 0;
  std::uint32_t best_second = 0;
  std::uint64_t best_states = 0;
  std::uint64_t evaluated = 0;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (set == ProductCardinalitySet::kDyadic && (a & (a - 1U)) != 0) {
      continue;
    }
    for (std::uint32_t b = 1; b <= capacity / a; ++b) {
      if (set == ProductCardinalitySet::kDyadic && (b & (b - 1U)) != 0) {
        continue;
      }
      ++evaluated;
      const std::uint32_t candidate_rank =
          rank[first.at(a).effective_cardinality]
              [second.at(b).effective_cardinality];
      const std::uint64_t states = static_cast<std::uint64_t>(a) * b;
      const bool replace =
          !found || candidate_rank < best_rank ||
          (candidate_rank == best_rank &&
           (states > best_states ||
            (states == best_states &&
             std::pair{a, b} < std::pair{best_first, best_second})));
      if (replace) {
        found = true;
        best_rank = candidate_rank;
        best_first = a;
        best_second = b;
        best_states = states;
      }
    }
  }
  if (!found || best_rank >= distinct.size()) {
    throw std::logic_error("exhaustive class replay has no decision");
  }
  return ExhaustiveDecision{
      ProductAllocation{
          best_first, best_second, best_states, capacity,
          ScaledRational(distinct[best_rank].get_num(),
                         distinct[best_rank].get_den(), -298),
          first.at(best_first).effective_cardinality == best_first &&
              second.at(best_second).effective_cardinality == best_second,
          evaluated},
      static_cast<std::uint32_t>(distinct.size())};
}

[[nodiscard]] std::string AllocationPreimage(
    const ProductAllocation& allocation, bool dyadic_only) {
  std::string output{"{\"capacity\":"};
  output += std::to_string(allocation.capacity);
  output += ",\"cardinalities\":[";
  output += std::to_string(allocation.first_cardinality);
  output.push_back(',');
  output += std::to_string(allocation.second_cardinality);
  output += "],\"dyadic_only\":";
  output += dyadic_only ? "true" : "false";
  output += ",\"objective\":{\"binary_grid_exponent\":-298,"
            "\"denominator\":\"";
  output += allocation.sse.denominator.get_str();
  output += "\",\"numerator\":\"";
  output += allocation.sse.numerator.get_str();
  output += "\"},\"used_states\":";
  output += std::to_string(allocation.used_states);
  output += "}\n";
  return output;
}

void AppendObjective(std::string* output, const ScaledRational& objective) {
  if (objective.binary_exponent != -298 || objective.numerator < 0 ||
      objective.denominator <= 0) {
    throw std::logic_error("noncanonical allocation objective");
  }
  output->append("{\"binary_grid_exponent\":-298,\"denominator\":\"");
  output->append(objective.denominator.get_str());
  output->append("\",\"numerator\":\"");
  output->append(objective.numerator.get_str());
  output->append("\"}");
}

void AppendProduct(std::string* output, const ProductAllocation& allocation) {
  output->append("{\"cardinalities\":[");
  output->append(std::to_string(allocation.first_cardinality));
  output->push_back(',');
  output->append(std::to_string(allocation.second_cardinality));
  output->append("],\"objective\":");
  AppendObjective(output, allocation.sse);
  output->append(",\"reachable\":");
  output->append(allocation.nominal_alphabets_reachable ? "true" : "false");
  output->append(",\"used_states\":");
  output->append(std::to_string(allocation.used_states));
  output->push_back('}');
}

void AppendGlobal(std::string* output, const GlobalAllocation& allocation) {
  if (allocation.bit_widths.size() != kCoordinateCount) {
    throw std::logic_error("global allocation has wrong coordinate count");
  }
  output->append("{\"bit_widths\":[");
  for (std::size_t index = 0; index < allocation.bit_widths.size(); ++index) {
    if (index != 0) output->push_back(',');
    output->append(std::to_string(allocation.bit_widths[index]));
  }
  output->append("],\"objective\":");
  AppendObjective(output, allocation.sse);
  output->append(",\"reachable\":");
  output->append(allocation.nominal_alphabets_reachable ? "true" : "false");
  output->append(",\"used_bits\":");
  output->append(std::to_string(allocation.used_bits));
  output->push_back('}');
}

struct GroupDecision {
  std::uint32_t word_bits{0};
  std::uint32_t group_id{0};
  ProductAllocation arbitrary;
  ProductAllocation dyadic;
};

[[nodiscard]] std::string AllocationJson(
    const std::vector<GroupDecision>& groups,
    const GlobalAllocation& global_b4,
    const GlobalAllocation& global_b8) {
  if (groups.size() != 2 * kGroupCount) {
    throw std::logic_error("allocation output needs B4 and B8 group rows");
  }
  std::string output;
  output.append("{\"globals\":{\"B4\":");
  AppendGlobal(&output, global_b4);
  output.append(",\"B8\":");
  AppendGlobal(&output, global_b8);
  output.append("},\"groups\":[");
  for (std::size_t index = 0; index < groups.size(); ++index) {
    if (index != 0) output.push_back(',');
    output.append("{\"arbitrary\":");
    AppendProduct(&output, groups[index].arbitrary);
    output.append(",\"dyadic\":");
    AppendProduct(&output, groups[index].dyadic);
    output.append(",\"group\":");
    output.append(std::to_string(groups[index].group_id));
    output.append(",\"rate\":\"B");
    output.append(std::to_string(groups[index].word_bits));
    output.append("\"}");
  }
  output.append("]}\n");
  return output;
}

}  // namespace

void WriteAllocationSuite(const std::string& input_path,
                          const std::string& output_path) {
  RepresentationSmoke();
  Reader reader(input_path);
  reader.Require("A4ALC001", "allocation panel input");
  constexpr std::uint32_t kCurveCount = 128;
  constexpr std::uint32_t kMaximum = 256;
  if (reader.U32("allocation panel curve count") != kCurveCount ||
      reader.U32("allocation panel maximum K") != kMaximum) {
    throw std::runtime_error("allocation panel must be 128 curves through K=256");
  }
  std::vector<ScalarCurve> curves;
  curves.reserve(kCurveCount);
  for (std::uint32_t coordinate = 0; coordinate < kCurveCount; ++coordinate) {
    curves.push_back(ReadCurve(&reader, kMaximum));
  }
  reader.Eof();

  std::vector<GroupDecision> groups;
  groups.reserve(2 * kGroupCount);
  for (const std::uint32_t word_bits : {4U, 8U}) {
    const std::uint32_t capacity = 1U << word_bits;
    for (std::uint32_t group = 0; group < kGroupCount; ++group) {
      groups.push_back(GroupDecision{
          word_bits,
          group,
          AllocateProduct2(curves[2 * group], curves[2 * group + 1], capacity,
                           ProductCardinalitySet::kArbitrary),
          AllocateProduct2(curves[2 * group], curves[2 * group + 1], capacity,
                           ProductCardinalitySet::kDyadic)});
    }
  }
  const GlobalAllocation global_b4 = AllocateGlobalDyadicCap8(curves, 256);
  const GlobalAllocation global_b8 = AllocateGlobalDyadicCap8(curves, 512);
  const std::string json = AllocationJson(groups, global_b4, global_b8);
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create allocation panel output");
  output.write(json.data(), static_cast<std::streamsize>(json.size()));
  output.flush();
  if (!output) throw std::runtime_error("allocation panel output failed");
}

void WriteNativeSmoke(const std::string& output_path) {
  RepresentationSmoke();
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) throw std::runtime_error("cannot create native smoke output");
  output << "A4S_NATIVE_SMOKE_V1\n";
  const std::array<std::uint32_t, 10> patterns{
      0x00000000U, 0x80000000U, 0x00000001U, 0x007fffffU, 0x00800000U,
      0x3f800000U, 0x3f800001U, 0x7f7fffffU, 0x80000001U, 0xbf800000U};
  for (const std::uint32_t bits : patterns) {
    const ScaledRational exact(DecodeBinary32(bits), 1, -149);
    const std::uint32_t canonical_bits =
        (bits & 0x7fffffffU) == 0 ? 0U : bits;
    if (RoundToBinary32(exact) != canonical_bits) {
      throw std::logic_error("binary32 direct-RNE roundtrip failed");
    }
    output << "ROUNDTRIP\t" << Hex32(bits) << '\t'
           << exact.numerator.get_str() << '\t' << Hex32(RoundToBinary32(exact))
           << '\t' << Hex64(RoundToBinary64(exact)) << '\n';
  }
  for (const ScaledRational& midpoint :
       std::array<ScaledRational, 4>{ScaledRational(1, 2, -149),
                                    ScaledRational(3, 2, -149),
                                    ScaledRational(-1, 2, -149),
                                    ScaledRational(-3, 2, -149)}) {
    output << "MIDPOINT\t" << midpoint.numerator.get_str() << '\t'
           << midpoint.denominator.get_str() << '\t'
           << midpoint.binary_exponent << '\t'
           << Hex32(RoundToBinary32(midpoint)) << '\t'
           << Hex64(RoundToBinary64(midpoint)) << '\n';
  }
  for (const ScaledRational& rational :
       std::array<ScaledRational, 2>{ScaledRational(1, 3, 0),
                                    ScaledRational(-1, 3, 0)}) {
    output << "RATIONAL\t" << rational.numerator.get_str() << '\t'
           << rational.denominator.get_str() << '\t'
           << rational.binary_exponent << '\t'
           << Hex32(RoundToBinary32(rational)) << '\t'
           << Hex64(RoundToBinary64(rational)) << '\n';
  }

  const std::vector<WeightedBinary32> scalar_samples{
      WeightedBinary32{0x00000000U, 1, 10},
      WeightedBinary32{0x3f800000U, 1, 11}};
  const ScalarCurve scalar = FitExactScalarCurve(scalar_samples, 4);
  if (scalar.support.size() != 2 ||
      scalar.at(4).effective_cardinality != 2 ||
      !SameObjective(scalar.at(2).sse, scalar.at(4).sse) ||
      PredecessorLayer(scalar, 4) != 2) {
    throw std::logic_error("at-most-K scalar certificate smoke failed");
  }
  output << "SCALAR_K_GT_H\t4\t2\t2\t"
         << scalar.predecessors[2].size() << '\n';

  const BlockAssignmentTieFixture assignment_tie =
      RunBlockAssignmentTieFixture();
  if (assignment_tie.selected_codeword != 0 ||
      assignment_tie.sse != 1.0 ||
      assignment_tie.distance_comparison_count != 2 ||
      assignment_tie.tie_count != 1) {
    throw std::logic_error("block assignment-tie smoke failed");
  }
  output << "BLOCK_ASSIGNMENT_TIE\t" << assignment_tie.selected_codeword
         << '\t' << Hex64(std::bit_cast<std::uint64_t>(assignment_tie.sse))
         << '\t' << assignment_tie.distance_comparison_count << '\t'
         << assignment_tie.tie_count << '\n';

  const BlockFarthestTieFixture farthest_tie =
      RunBlockFarthestTieFixture();
  if (farthest_tie.selected_cell_id != 3 ||
      farthest_tie.selected_vector_id != 7 ||
      farthest_tie.tie_count != 1) {
    throw std::logic_error("block farthest-tie smoke failed");
  }
  output << "BLOCK_FARTHEST_FALLBACK\t"
         << farthest_tie.selected_cell_id << '\t'
         << farthest_tie.selected_vector_id << '\t'
         << farthest_tie.tie_count << '\n';

  BlockMetadata metadata{std::string(kHashDomain), "native_smoke_block", 16,
                         0};
  const std::vector<double> axis{-1.0, 0.0, 1.0, 2.0};
  std::vector<Point2> points;
  for (std::uint64_t y = 0; y < axis.size(); ++y) {
    for (std::uint64_t x = 0; x < axis.size(); ++x) {
      const std::uint64_t id = y * axis.size() + x;
      points.push_back(MakePoint(static_cast<float>(axis[x]),
                                 static_cast<float>(axis[y]), 0, id,
                                 metadata.hash_domain, metadata.dataset_id));
    }
  }
  const BlockResult block = TrainBlockVq(points, metadata, axis, axis);
  if (!block.control_valid || block.starts.size() != 8 ||
      block.best_start_id >= block.starts.size() ||
      block.starts[block.best_start_id].final_assignments.size() !=
          points.size()) {
    throw std::logic_error("eight-start block smoke failed");
  }
  output << "BLOCK_VALID_EIGHT_STARTS\t" << block.starts.size() << '\t'
         << block.best_start_id << '\n';

  BlockMetadata nonfinite_metadata{std::string(kHashDomain),
                                   "native_smoke_nonfinite", 16, 0};
  std::vector<Point2> nonfinite_points;
  nonfinite_points.reserve(16);
  for (std::uint64_t id = 0; id < 16; ++id) {
    nonfinite_points.push_back(MakePoint(
        0.0F, 0.0F, 0, id, nonfinite_metadata.hash_domain,
        nonfinite_metadata.dataset_id));
  }
  const BlockResult nonfinite = TrainBlockVq(
      nonfinite_points, nonfinite_metadata,
      {std::numeric_limits<double>::max()}, {0.0});
  bool complete_start_inventory = nonfinite.starts.size() == 8;
  for (std::size_t index = 0; index < nonfinite.starts.size(); ++index) {
    const BlockStartTrace& start = nonfinite.starts[index];
    complete_start_inventory =
        complete_start_inventory && start.start_id == index &&
        (index == 0
             ? start.failure == BlockFailure::kNonfinite
             : start.failure == BlockFailure::kNone && start.converged);
  }
  if (nonfinite.control_valid ||
      nonfinite.failure != BlockFailure::kNonfinite ||
      !complete_start_inventory) {
    throw std::logic_error("block nonfinite-control smoke failed");
  }
  output << "BLOCK_NONFINITE_CONTROL\t8\t0\n";
  output << "END\n";
  output.flush();
  if (!output) throw std::runtime_error("native smoke output failed");
}

namespace {

constexpr std::uint64_t kTinyCaseCount = 780;
constexpr std::uint64_t kAllocationRecordCount = 2'433'600;
constexpr std::uint64_t kExhaustiveTupleCount = 958'838'400;
constexpr std::uint64_t kOptimizedCandidateCount = 174'002'400;
constexpr std::array<std::uint32_t, 5> kTinyUniverse{
    0xc0000000U, 0xbf800000U, 0x00000000U, 0x3f800000U, 0x40000000U};
constexpr std::array<std::uint32_t, 2> kParityCapacities{16, 256};

void EnumerateTinyWeights(
    const std::vector<std::uint32_t>& support, std::size_t position,
    std::vector<std::uint64_t>* weights,
    std::vector<std::vector<WeightedBinary32>>* cases) {
  if (position == support.size()) {
    std::vector<WeightedBinary32> samples;
    samples.reserve(support.size());
    for (std::size_t index = 0; index < support.size(); ++index) {
      samples.push_back(
          WeightedBinary32{support[index], (*weights)[index], index});
    }
    cases->push_back(std::move(samples));
    return;
  }
  for (std::uint64_t weight = 1; weight <= 3; ++weight) {
    (*weights)[position] = weight;
    EnumerateTinyWeights(support, position + 1, weights, cases);
  }
}

void EnumerateTinySupports(
    std::size_t target, std::size_t next,
    std::vector<std::uint32_t>* support,
    std::vector<std::vector<WeightedBinary32>>* cases) {
  if (support->size() == target) {
    std::vector<std::uint64_t> weights(target, 1);
    EnumerateTinyWeights(*support, 0, &weights, cases);
    return;
  }
  const std::size_t needed = target - support->size();
  for (std::size_t index = next;
       index + needed <= kTinyUniverse.size(); ++index) {
    support->push_back(kTinyUniverse[index]);
    EnumerateTinySupports(target, index + 1, support, cases);
    support->pop_back();
  }
}

[[nodiscard]] std::vector<std::vector<WeightedBinary32>> TinyCases() {
  std::vector<std::vector<WeightedBinary32>> cases;
  cases.reserve(kTinyCaseCount);
  for (std::size_t size = 1; size <= 4; ++size) {
    std::vector<std::uint32_t> support;
    EnumerateTinySupports(size, 0, &support, &cases);
  }
  if (cases.size() != kTinyCaseCount) {
    throw std::logic_error("tiny parity inventory is not 780 cases");
  }
  return cases;
}

[[nodiscard]] std::vector<ScalarCurve> FitTinyCurves(
    const std::vector<std::vector<WeightedBinary32>>& cases,
    std::uint32_t capacity) {
  std::vector<ScalarCurve> curves;
  curves.reserve(cases.size());
  for (const auto& samples : cases) {
    curves.push_back(FitExactScalarCurve(samples, capacity));
  }
  return curves;
}

[[nodiscard]] bool IsPowerOfTwo(std::uint32_t value) {
  return value != 0 && (value & (value - 1U)) == 0;
}

void ValidateParityAllocation(const ProductAllocation& allocation,
                              std::uint32_t capacity,
                              ProductCardinalitySet set) {
  const std::uint64_t expected =
      set == ProductCardinalitySet::kDyadic ? std::bit_width(capacity)
                                            : capacity;
  if (allocation.capacity != capacity || allocation.first_cardinality == 0 ||
      allocation.second_cardinality == 0 ||
      allocation.used_states !=
          static_cast<std::uint64_t>(allocation.first_cardinality) *
              allocation.second_cardinality ||
      allocation.used_states > capacity ||
      allocation.enumerated_candidate_count != expected ||
      allocation.sse.binary_exponent != -298 ||
      allocation.sse.numerator < 0 || allocation.sse.denominator <= 0 ||
      (set == ProductCardinalitySet::kDyadic &&
       (!IsPowerOfTwo(allocation.first_cardinality) ||
        !IsPowerOfTwo(allocation.second_cardinality)))) {
    throw std::logic_error("product allocation violates parity contract");
  }
}

[[nodiscard]] std::uint64_t ExhaustiveFeasibleCount(
    std::uint32_t capacity, ProductCardinalitySet set) {
  std::uint64_t count = 0;
  for (std::uint32_t a = 1; a <= capacity; ++a) {
    if (set == ProductCardinalitySet::kDyadic && !IsPowerOfTwo(a)) continue;
    for (std::uint32_t b = 1; b <= capacity / a; ++b) {
      if (set == ProductCardinalitySet::kDyadic && !IsPowerOfTwo(b)) continue;
      ++count;
    }
  }
  return count;
}

[[nodiscard]] std::string TinyInventorySha256(
    const std::vector<std::vector<WeightedBinary32>>& cases) {
  Sha256Accumulator digest;
  for (std::size_t case_id = 0; case_id < cases.size(); ++case_id) {
    std::string preimage{"{\"case_id\":"};
    preimage += std::to_string(case_id);
    preimage += ",\"samples\":[";
    for (std::size_t index = 0; index < cases[case_id].size(); ++index) {
      if (index != 0) preimage.push_back(',');
      const WeightedBinary32& sample = cases[case_id][index];
      preimage += "{\"binary32_bits\":\"" + Hex32(sample.bits) +
                  "\",\"vector_id\":" +
                  std::to_string(sample.vector_id) + ",\"weight\":\"" +
                  std::to_string(sample.weight) + "\"}";
    }
    preimage += "]}\n";
    digest.Update(preimage);
  }
  return digest.FinalHex();
}

template <typename Range>
void AppendUnsignedArray(std::string* json, const Range& values) {
  json->push_back('[');
  bool first = true;
  for (const auto value : values) {
    if (!first) json->push_back(',');
    first = false;
    json->append(std::to_string(static_cast<std::uint64_t>(value)));
  }
  json->push_back(']');
}

template <typename Range>
void AppendHex32Array(std::string* json, const Range& values) {
  json->push_back('[');
  bool first = true;
  for (const auto value : values) {
    if (!first) json->push_back(',');
    first = false;
    json->append("\"");
    json->append(Hex32(static_cast<std::uint32_t>(value)));
    json->append("\"");
  }
  json->push_back(']');
}

[[nodiscard]] std::string BytesHex(std::span<const std::uint8_t> bytes) {
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setfill('0');
  for (const std::uint8_t byte : bytes) {
    output << std::setw(2) << static_cast<unsigned int>(byte);
  }
  return output.str();
}

[[nodiscard]] ScalarCurve ThreePointCurve(
    const std::array<std::uint64_t, 3>& weights,
    std::uint32_t maximum_cardinality) {
  std::vector<WeightedBinary32> samples;
  for (std::size_t index = 0; index < weights.size(); ++index) {
    samples.push_back(
        WeightedBinary32{kTinyUniverse[index], weights[index], index});
  }
  return FitExactScalarCurve(samples, maximum_cardinality);
}

void AppendSmallParity(std::string* json,
                       const ExhaustiveDecision& independent,
                       const ProductAllocation& optimized) {
  json->append("{\"independent_cardinalities\":[");
  json->append(std::to_string(
      independent.allocation.first_cardinality));
  json->push_back(',');
  json->append(std::to_string(
      independent.allocation.second_cardinality));
  json->append("],\"independent_feasible_tuple_evaluation_count\":\"");
  json->append(std::to_string(
      independent.allocation.enumerated_candidate_count));
  json->append("\",\"independent_objective\":");
  AppendObjective(json, independent.allocation.sse);
  json->append(",\"optimized_candidate_evaluation_count\":\"");
  json->append(std::to_string(optimized.enumerated_candidate_count));
  json->append("\",\"optimized_cardinalities\":[");
  json->append(std::to_string(optimized.first_cardinality));
  json->push_back(',');
  json->append(std::to_string(optimized.second_cardinality));
  json->append("],\"optimized_objective\":");
  AppendObjective(json, optimized.sse);
  json->append(",\"parity\":");
  const bool parity =
      optimized.first_cardinality ==
          independent.allocation.first_cardinality &&
      optimized.second_cardinality ==
          independent.allocation.second_cardinality &&
      optimized.used_states == independent.allocation.used_states &&
      optimized.nominal_alphabets_reachable ==
          independent.allocation.nominal_alphabets_reachable &&
      SameObjective(optimized.sse, independent.allocation.sse);
  json->append(parity ? "true}" : "false}");
}

[[nodiscard]] std::string SameSupportDifferentWeightsJson() {
  constexpr std::uint32_t capacity = 4;
  const ScalarCurve curve_a = ThreePointCurve({1, 1, 1}, capacity);
  const ScalarCurve curve_b = ThreePointCurve({1, 1, 2}, capacity);
  const ScalarCurve mate = ThreePointCurve({3, 3, 3}, capacity);
  if (curve_a.support.size() != 3 || curve_b.support.size() != 3 ||
      !SameObjective(curve_a.at(3).sse, curve_b.at(3).sse) ||
      SameObjective(curve_a.at(1).sse, curve_b.at(1).sse)) {
    throw std::logic_error("different-weight fixture is not discriminative");
  }
  std::string json{"{\"arms\":["};
  bool first_arm = true;
  for (const ProductCardinalitySet set :
       {ProductCardinalitySet::kArbitrary, ProductCardinalitySet::kDyadic}) {
    const ExhaustiveDecision independent_a =
        ExhaustiveProductByObjectiveClass(curve_a, mate, capacity, set);
    const ExhaustiveDecision independent_b =
        ExhaustiveProductByObjectiveClass(curve_b, mate, capacity, set);
    const ProductAllocation optimized_a =
        AllocateProduct2(curve_a, mate, capacity, set);
    const ProductAllocation optimized_b =
        AllocateProduct2(curve_b, mate, capacity, set);
    ValidateParityAllocation(optimized_a, capacity, set);
    ValidateParityAllocation(optimized_b, capacity, set);
    const std::uint64_t expected =
        set == ProductCardinalitySet::kDyadic ? 6 : 8;
    if (independent_a.allocation.enumerated_candidate_count != expected ||
        independent_b.allocation.enumerated_candidate_count != expected ||
        independent_a.allocation.first_cardinality != 1 ||
        independent_a.allocation.second_cardinality != 4 ||
        independent_b.allocation.first_cardinality != 2 ||
        independent_b.allocation.second_cardinality != 2) {
      throw std::logic_error("different-weight allocation fixture failed");
    }
    if (!first_arm) json.push_back(',');
    first_arm = false;
    json += "{\"cardinality_kind\":\"";
    json += set == ProductCardinalitySet::kDyadic ? "dyadic" : "arbitrary";
    json += "\",\"curve_a\":";
    AppendSmallParity(&json, independent_a, optimized_a);
    json += ",\"curve_b\":";
    AppendSmallParity(&json, independent_b, optimized_b);
    json += ",\"different_weight_sensitive_winners\":true}";
  }
  json += "],\"capacity\":4,\"common_support_binary32_bits\":[\"";
  json += Hex32(kTinyUniverse[0]);
  json += "\",\"" + Hex32(kTinyUniverse[1]) + "\",\"" +
          Hex32(kTinyUniverse[2]) + "\"],\"curve_a_k1_objective\":";
  AppendObjective(&json, curve_a.at(1).sse);
  json += ",\"curve_a_weights\":[1,1,1],\"curve_b_k1_objective\":";
  AppendObjective(&json, curve_b.at(1).sse);
  json += ",\"curve_b_weights\":[1,1,2],\"mate_weights\":[3,3,3],"
          "\"same_support_size\":3}";
  return json;
}

[[nodiscard]] std::string SupportWinnerJson() {
  std::string json{"["};
  bool first_record = true;
  std::uint64_t count = 0;
  for (const std::uint32_t capacity : kParityCapacities) {
    std::vector<ScalarCurve> curves;
    for (std::size_t size = 1; size <= 4; ++size) {
      std::vector<WeightedBinary32> samples;
      for (std::size_t index = 0; index < size; ++index) {
        samples.push_back(WeightedBinary32{kTinyUniverse[index], 1, index});
      }
      curves.push_back(FitExactScalarCurve(samples, capacity));
    }
    for (const ProductCardinalitySet set :
         {ProductCardinalitySet::kArbitrary,
          ProductCardinalitySet::kDyadic}) {
      const std::uint64_t exhaustive = ExhaustiveFeasibleCount(capacity, set);
      for (std::size_t first = 1; first <= 4; ++first) {
        for (std::size_t second = 1; second <= 4; ++second) {
          const ProductAllocation allocation = AllocateProduct2(
              curves[first - 1], curves[second - 1], capacity, set);
          ValidateParityAllocation(allocation, capacity, set);
          if (!first_record) json.push_back(',');
          first_record = false;
          json += "{\"capacity\":" + std::to_string(capacity) +
                  ",\"cardinality_kind\":\"" +
                  (set == ProductCardinalitySet::kDyadic ? "dyadic" :
                                                            "arbitrary") +
                  "\",\"exhaustive_valid_tuple_count\":\"" +
                  std::to_string(exhaustive) +
                  "\",\"first_support_size\":" +
                  std::to_string(first) + ",\"objective\":";
          AppendObjective(&json, allocation.sse);
          json += ",\"optimized_candidate_evaluation_count\":\"" +
                  std::to_string(allocation.enumerated_candidate_count) +
                  "\",\"reachable\":" +
                  std::string(allocation.nominal_alphabets_reachable
                                  ? "true"
                                  : "false") +
                  ",\"second_support_size\":" +
                  std::to_string(second) +
                  ",\"selected_cardinalities\":[" +
                  std::to_string(allocation.first_cardinality) + "," +
                  std::to_string(allocation.second_cardinality) +
                  "],\"used_states\":" +
                  std::to_string(allocation.used_states) + "}";
          ++count;
        }
      }
    }
  }
  if (count != 64) throw std::logic_error("support inventory is not 64");
  json.push_back(']');
  return json;
}

[[nodiscard]] std::string MixedRadixJson() {
  const std::array<std::uint32_t, 2> radices{3, 5};
  constexpr std::uint64_t valid_count = 15;
  std::string json{"{\"entries\":["};
  for (std::uint64_t address = 0; address < 16; ++address) {
    if (address != 0) json.push_back(',');
    json += "{\"address\":" + std::to_string(address);
    if (address < valid_count) {
      const std::vector<std::uint32_t> labels =
          MixedRadixDecode(address, radices);
      const std::uint64_t replay = MixedRadixEncode(labels, radices);
      if (replay != address) {
        throw std::logic_error("mixed-radix fixture failed replay");
      }
      json += ",\"decoded_labels\":";
      AppendUnsignedArray(&json, labels);
      json += ",\"encoded_address\":" + std::to_string(replay) +
              ",\"labels\":";
      AppendUnsignedArray(&json, labels);
      json += ",\"valid\":true}";
    } else {
      bool rejected = false;
      try {
        static_cast<void>(MixedRadixDecode(address, radices));
      } catch (const std::invalid_argument&) {
        rejected = true;
      }
      if (!rejected) {
        throw std::logic_error("invalid mixed-radix address accepted");
      }
      json += ",\"decoded_labels\":null,\"encoded_address\":null,"
              "\"labels\":null,\"valid\":false}";
    }
  }
  json += "],\"nominal_capacity\":16,\"radices\":[3,5],"
          "\"valid_tuple_count\":15}";
  return json;
}

[[nodiscard]] std::string MatchedPackingJson() {
  std::string json{"["};
  for (const std::uint32_t word_bits : {4U, 8U}) {
    if (word_bits == 8) json.push_back(',');
    std::vector<std::uint32_t> labels(kGroupCount, 0);
    for (std::size_t index = 0; index < labels.size(); ++index) {
      labels[index] = word_bits == 4
                          ? static_cast<std::uint32_t>(index % 16)
                          : static_cast<std::uint32_t>((3 * index + 1) % 256);
    }
    const std::vector<std::uint8_t> payload = PackMatched(labels, word_bits);
    const std::vector<std::uint32_t> replay =
        UnpackMatched(payload, word_bits);
    if (replay != labels) throw std::logic_error("matched packing fixture failed");
    json += "{\"labels\":";
    AppendUnsignedArray(&json, labels);
    json += ",\"payload_bytes\":" + std::to_string(payload.size()) +
            ",\"payload_hex\":\"" + BytesHex(payload) +
            "\",\"roundtrip_labels\":";
    AppendUnsignedArray(&json, replay);
    json += ",\"word_bits\":" + std::to_string(word_bits) + "}";
  }
  json.push_back(']');
  return json;
}

struct GlobalPackingInput {
  std::vector<std::uint8_t> widths;
  std::vector<std::uint32_t> labels;
};

[[nodiscard]] GlobalPackingInput MakeGlobalPackingInput(
    std::size_t paid_bytes) {
  GlobalPackingInput input;
  input.widths.assign(kCoordinateCount, 0);
  input.labels.assign(kCoordinateCount, 0);
  if (paid_bytes == 32) {
    const std::array<std::uint8_t, 7> widths{0, 1, 3, 4, 0, 7, 2};
    const std::array<std::uint32_t, 7> labels{0, 1, 5, 9, 0, 85, 3};
    std::copy(widths.begin(), widths.end(), input.widths.begin());
    std::copy(labels.begin(), labels.end(), input.labels.begin());
  } else if (paid_bytes == 64) {
    const std::array<std::uint8_t, 8> widths{8, 0, 5, 3, 1, 7, 2, 4};
    const std::array<std::uint32_t, 8> labels{255, 0, 17, 5, 1, 100, 3, 9};
    std::copy(widths.begin(), widths.end(), input.widths.begin());
    std::copy(labels.begin(), labels.end(), input.labels.begin());
  } else {
    throw std::invalid_argument("unexpected global packing fixture size");
  }
  return input;
}

[[nodiscard]] std::string GlobalPackingCaseJson(std::size_t paid_bytes) {
  const GlobalPackingInput input = MakeGlobalPackingInput(paid_bytes);
  const GlobalPacked packed =
      PackGlobal(input.labels, input.widths, paid_bytes);
  const std::vector<std::uint32_t> replay =
      UnpackGlobal(packed.bytes, input.widths);
  bool zero_tail = replay == input.labels;
  for (std::uint64_t bit = packed.used_bits;
       bit < packed.bytes.size() * 8ULL; ++bit) {
    zero_tail = zero_tail &&
                ((packed.bytes[bit / 8U] >> (bit % 8U)) & 1U) == 0;
  }
  if (!zero_tail) throw std::logic_error("global packing fixture failed");
  std::string json{"{\"bit_offsets\":"};
  AppendUnsignedArray(&json, packed.bit_offsets);
  json += ",\"bit_widths\":";
  AppendUnsignedArray(&json, input.widths);
  json += ",\"labels\":";
  AppendUnsignedArray(&json, input.labels);
  json += ",\"paid_payload_bytes\":" + std::to_string(paid_bytes) +
          ",\"payload_hex\":\"" + BytesHex(packed.bytes) +
          "\",\"roundtrip_labels\":";
  AppendUnsignedArray(&json, replay);
  json += ",\"used_bits\":" + std::to_string(packed.used_bits) +
          ",\"zero_tail\":true}";
  return json;
}

[[nodiscard]] std::string GlobalPackingJson() {
  return "[" + GlobalPackingCaseJson(32) + "," +
         GlobalPackingCaseJson(64) + "]";
}

void AppendPointBitsArray(std::string* json,
                          std::span<const PointBits2> points) {
  json->push_back('[');
  for (std::size_t index = 0; index < points.size(); ++index) {
    if (index != 0) json->push_back(',');
    json->append("[\"");
    json->append(Hex32(points[index].x));
    json->append("\",\"");
    json->append(Hex32(points[index].y));
    json->append("\"]");
  }
  json->push_back(']');
}

void AppendLookup(std::string* json, const LookupBits& entry) {
  json->append("\"pre_narrow_binary64_bits\":\"");
  json->append(Hex64(entry.binary64_bits));
  json->append("\",\"stored_binary32_bits\":\"");
  json->append(Hex32(entry.binary32_bits));
  json->append("\",\"valid\":");
  json->append(entry.valid ? "true" : "false");
}

[[nodiscard]] std::vector<std::uint32_t> FloatBitsOf(
    std::span<const float> values) {
  std::vector<std::uint32_t> result;
  result.reserve(values.size());
  for (const float value : values) {
    result.push_back(std::bit_cast<std::uint32_t>(value));
  }
  return result;
}

[[nodiscard]] std::string MatchedLookupCaseJson(
    std::uint32_t capacity, std::span<const std::uint32_t> axis0,
    std::span<const std::uint32_t> axis1, const PointBits2& query) {
  const std::vector<PointBits2> reconstructions = CartesianBits(axis0, axis1);
  const MatchedLookup table =
      BuildMatchedLookup(query, reconstructions, capacity);
  if (table.entries.size() != capacity ||
      table.valid_states != reconstructions.size()) {
    throw std::logic_error("matched lookup fixture shape mismatch");
  }
  std::string json{"{\"axis0_centroid_bits\":"};
  AppendHex32Array(&json, axis0);
  json += ",\"axis1_centroid_bits\":";
  AppendHex32Array(&json, axis1);
  json += ",\"capacity\":" + std::to_string(capacity) +
          ",\"entries\":[";
  for (std::size_t address = 0; address < table.entries.size(); ++address) {
    if (address != 0) json.push_back(',');
    json += "{\"address\":" + std::to_string(address) + ",";
    AppendLookup(&json, table.entries[address]);
    json.push_back('}');
  }
  json += "],\"query_bits\":[\"" + Hex32(query.x) + "\",\"" +
          Hex32(query.y) + "\"],\"radices\":[" +
          std::to_string(axis0.size()) + "," +
          std::to_string(axis1.size()) + "],\"reconstruction_bits\":";
  AppendPointBitsArray(&json, reconstructions);
  json += ",\"valid_states\":" + std::to_string(table.valid_states) + "}";
  return json;
}

[[nodiscard]] std::string MatchedLookupJson() {
  const std::array<float, 3> a0{-1.0F, 0.0F, 2.0F};
  const std::array<float, 5> a1{-2.0F, -0.5F, 1.0F, 3.0F, 4.0F};
  const std::vector<std::uint32_t> b4_axis0 = FloatBitsOf(a0);
  const std::vector<std::uint32_t> b4_axis1 = FloatBitsOf(a1);
  std::vector<std::uint32_t> b8_axis0;
  std::vector<std::uint32_t> b8_axis1;
  for (int value = -6; value <= 6; ++value) {
    b8_axis0.push_back(
        std::bit_cast<std::uint32_t>(static_cast<float>(value)));
  }
  for (int value = -9; value <= 9; ++value) {
    b8_axis1.push_back(
        std::bit_cast<std::uint32_t>(static_cast<float>(value)));
  }
  const PointBits2 q4{std::bit_cast<std::uint32_t>(0.5F),
                      std::bit_cast<std::uint32_t>(-0.75F)};
  const PointBits2 q8{std::bit_cast<std::uint32_t>(0.25F),
                      std::bit_cast<std::uint32_t>(-0.5F)};
  return "[" + MatchedLookupCaseJson(16, b4_axis0, b4_axis1, q4) +
         "," + MatchedLookupCaseJson(256, b8_axis0, b8_axis1, q8) + "]";
}

[[nodiscard]] LookupBits ScalarLookup(std::uint32_t query_bits,
                                      std::uint32_t centroid_bits) {
  const double query =
      static_cast<double>(std::bit_cast<float>(query_bits));
  const double centroid =
      static_cast<double>(std::bit_cast<float>(centroid_bits));
  const double difference = query - centroid;
  const double distance = difference * difference;
  const float narrowed = static_cast<float>(distance);
  if (!std::isfinite(distance) || !std::isfinite(narrowed)) {
    throw std::logic_error("global lookup fixture became nonfinite");
  }
  return LookupBits{true, std::bit_cast<std::uint64_t>(distance),
                    std::bit_cast<std::uint32_t>(narrowed)};
}

[[nodiscard]] std::vector<std::uint32_t> LookupPalette() {
  const std::array<float, 16> values{
      -4.0F, -3.0F, -2.0F, -1.0F, -0.5F, -0.25F, 0.0F, 0.25F,
      0.5F,  1.0F,  2.0F,  3.0F,  4.0F,  5.0F,  6.0F, 8.0F};
  return FloatBitsOf(values);
}

[[nodiscard]] std::string GlobalLookupJson() {
  const GlobalPackingInput packing = MakeGlobalPackingInput(32);
  const std::vector<std::uint32_t> palette = LookupPalette();
  std::vector<std::uint32_t> query(kCoordinateCount, 0);
  std::vector<std::vector<std::uint32_t>> centroids(kCoordinateCount);
  std::vector<std::uint32_t> offsets{0};
  for (std::size_t coordinate = 0; coordinate < kCoordinateCount;
       ++coordinate) {
    query[coordinate] = palette[(3 * coordinate) % palette.size()];
    const std::size_t cardinality =
        std::size_t{1} << packing.widths[coordinate];
    for (std::size_t label = 0; label < cardinality; ++label) {
      centroids[coordinate].push_back(
          palette[(coordinate + 3 * label) % palette.size()]);
    }
    offsets.push_back(offsets.back() +
                      static_cast<std::uint32_t>(cardinality));
  }
  std::string json{"{\"bit_widths\":"};
  AppendUnsignedArray(&json, packing.widths);
  json += ",\"centroid_bits_by_coordinate\":[";
  for (std::size_t coordinate = 0; coordinate < centroids.size();
       ++coordinate) {
    if (coordinate != 0) json.push_back(',');
    AppendHex32Array(&json, centroids[coordinate]);
  }
  json += "],\"coordinate_offsets\":";
  AppendUnsignedArray(&json, offsets);
  json += ",\"entries\":[";
  std::size_t flat = 0;
  for (std::size_t coordinate = 0; coordinate < centroids.size();
       ++coordinate) {
    for (std::size_t label = 0; label < centroids[coordinate].size(); ++label) {
      if (flat != 0) json.push_back(',');
      json += "{\"coordinate\":" + std::to_string(coordinate) +
              ",\"flat_index\":" + std::to_string(flat) +
              ",\"label\":" + std::to_string(label) + ",";
      AppendLookup(&json,
                   ScalarLookup(query[coordinate], centroids[coordinate][label]));
      json.push_back('}');
      ++flat;
    }
  }
  if (flat != offsets.back()) {
    throw std::logic_error("global lookup fixture offset mismatch");
  }
  json += "],\"query_coordinate_bits\":";
  AppendHex32Array(&json, query);
  json.push_back('}');
  return json;
}

}  // namespace

void WriteRepresentationSuite(std::ostream& output) {
  RepresentationSmoke();
  const std::vector<std::vector<WeightedBinary32>> cases = TinyCases();
  Sha256Accumulator independent_digest;
  Sha256Accumulator optimized_digest;
  std::uint64_t records = 0;
  std::uint64_t equal_decisions = 0;
  std::uint64_t exhaustive_evaluations = 0;
  std::uint64_t optimized_evaluations = 0;
  std::uint64_t exact_classes = 0;
  std::string first_mismatch{"null"};
  bool objective_contract = true;
  for (const std::uint32_t capacity : kParityCapacities) {
    const std::vector<ScalarCurve> curves = FitTinyCurves(cases, capacity);
    for (const ProductCardinalitySet set :
         {ProductCardinalitySet::kArbitrary,
          ProductCardinalitySet::kDyadic}) {
      const bool dyadic = set == ProductCardinalitySet::kDyadic;
      const std::uint64_t expected_exhaustive =
          ExhaustiveFeasibleCount(capacity, set);
      for (std::size_t first_id = 0; first_id < curves.size(); ++first_id) {
        const ScalarCurve& first = curves[first_id];
        for (std::size_t second_id = 0; second_id < curves.size(); ++second_id) {
          const ScalarCurve& second = curves[second_id];
          const ExhaustiveDecision independent =
              ExhaustiveProductByObjectiveClass(first, second, capacity, set);
          const ProductAllocation optimized =
              AllocateProduct2(first, second, capacity, set);
          ValidateParityAllocation(optimized, capacity, set);
          if (independent.allocation.enumerated_candidate_count !=
              expected_exhaustive) {
            throw std::logic_error("exhaustive tuple count mismatch");
          }
          independent_digest.Update(
              AllocationPreimage(independent.allocation, dyadic));
          optimized_digest.Update(AllocationPreimage(optimized, dyadic));
          exhaustive_evaluations +=
              independent.allocation.enumerated_candidate_count;
          optimized_evaluations += optimized.enumerated_candidate_count;
          exact_classes += independent.exact_objective_class_count;
          objective_contract = objective_contract &&
                               optimized.sse.binary_exponent == -298 &&
                               independent.allocation.sse.binary_exponent ==
                                   -298;
          const bool equal =
              optimized.first_cardinality ==
                  independent.allocation.first_cardinality &&
              optimized.second_cardinality ==
                  independent.allocation.second_cardinality &&
              optimized.used_states == independent.allocation.used_states &&
              optimized.nominal_alphabets_reachable ==
                  independent.allocation.nominal_alphabets_reachable &&
              SameObjective(optimized.sse, independent.allocation.sse);
          if (equal) {
            ++equal_decisions;
          } else if (first_mismatch == "null") {
            std::string independent_json;
            std::string optimized_json;
            AppendProduct(&independent_json, independent.allocation);
            AppendProduct(&optimized_json, optimized);
            first_mismatch =
                "{\"capacity\":" + std::to_string(capacity) +
                ",\"cardinality_kind\":\"" +
                (dyadic ? "dyadic" : "arbitrary") +
                "\",\"first_case_id\":" + std::to_string(first_id) +
                ",\"independent\":" + independent_json +
                ",\"optimized\":" + optimized_json +
                ",\"second_case_id\":" + std::to_string(second_id) + "}";
          }
          ++records;
        }
      }
    }
  }
  if (records != kAllocationRecordCount ||
      exhaustive_evaluations != kExhaustiveTupleCount ||
      optimized_evaluations != kOptimizedCandidateCount) {
    throw std::logic_error("frozen representation parity inventory changed");
  }
  const std::string independent_sha = independent_digest.FinalHex();
  const std::string optimized_sha = optimized_digest.FinalHex();
  const bool all_equal = equal_decisions == records;
  const bool hashes_equal = independent_sha == optimized_sha;
  const std::string global_lookup = GlobalLookupJson();
  const std::string global_packing = GlobalPackingJson();
  const std::string matched_lookup = MatchedLookupJson();
  const std::string matched_packing = MatchedPackingJson();
  const std::string mixed_radix = MixedRadixJson();
  const std::string different_weights = SameSupportDifferentWeightsJson();
  const std::string support_winners = SupportWinnerJson();
  const std::string inventory_sha = TinyInventorySha256(cases);

  output << "{\"allocation_record_count\":" << records
         << ",\"allocation_sha256\":\"" << optimized_sha
         << "\",\"all_decisions_equal\":"
         << (all_equal ? "true" : "false")
         << ",\"authority_hashes_equal\":"
         << (hashes_equal ? "true" : "false")
         << ",\"candidate_counts\":{"
         << "\"independent_feasible_tuple_evaluations\":\""
         << exhaustive_evaluations
         << "\",\"optimized_candidate_evaluations\":\""
         << optimized_evaluations << "\"},\"checks\":{"
         << "\"allocation_record_count\":true,\"all_decisions_equal\":"
         << (all_equal ? "true" : "false")
         << ",\"authority_hashes_equal\":"
         << (hashes_equal ? "true" : "false")
         << ",\"candidate_counts\":true,"
         << "\"equidistant_lower_codeword\":true,\"objective_contract\":"
         << (objective_contract ? "true" : "false")
         << ",\"representation_constant_smoke\":true,"
         << "\"tiny_case_count\":true},\"decision_equality_count\":"
         << equal_decisions << ",\"exact_objective_class_count\":\""
         << exact_classes << "\",\"first_mismatch\":" << first_mismatch
         << ",\"global_lookup_case\":" << global_lookup
         << ",\"global_packing_cases\":" << global_packing
         << ",\"matched_lookup_cases\":" << matched_lookup
         << ",\"matched_packing_cases\":" << matched_packing
         << ",\"mixed_radix_case\":" << mixed_radix
         << ",\"independent_exhaustive_sha256\":\"" << independent_sha
         << "\",\"optimized_sha256\":\"" << optimized_sha
         << "\",\"python_order_fingerprint_authoritative\":false,"
         << "\"python_order_fingerprint_sha256\":\"" << optimized_sha
         << "\",\"same_h_different_weight_fixture\":" << different_weights
         << ",\"support_size_winners\":" << support_winners
         << ",\"tiny_curve_inventory_preimage_schema\":\""
            "canonical JSONL: case_id, then samples with binary32_bits, "
            "vector_id, weight; terminal LF per case\","
         << "\"tiny_curve_inventory_sha256\":\"" << inventory_sha
         << "\"}\n";
  if (!output) throw std::runtime_error("representation suite output failed");
}

}  // namespace saq::a4_v2::producer

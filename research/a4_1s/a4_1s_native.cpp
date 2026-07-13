#include "block_cli.hpp"
#include "block_vq.hpp"
#include "allocation_item_cli.hpp"
#include "exact_quantizer.hpp"
#include "numeric_runtime.hpp"
#include "representation_cli.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace saq::a4_1s {
namespace {

constexpr std::string_view kScalarInputMagic = "A4SCL001";

[[nodiscard]] std::uint32_t EffectivePredecessorLayer(
    const ScalarCurveResult& curve,
    std::uint32_t requested_cardinality) {
  if (curve.predecessors.size() <= 1) {
    throw std::logic_error("scalar predecessor row is unavailable");
  }
  const std::uint32_t layer = std::min<std::uint32_t>(
      requested_cardinality,
      static_cast<std::uint32_t>(curve.predecessors.size() - 1));
  if (layer == 0 || layer >= curve.predecessors.size()) {
    throw std::logic_error("scalar predecessor row is unavailable");
  }
  return layer;
}

[[nodiscard]] std::uint32_t ReadU32(std::istream& input) {
  std::array<unsigned char, 4> bytes{};
  input.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
  if (!input) {
    throw std::runtime_error("truncated uint32 in native input");
  }
  return static_cast<std::uint32_t>(bytes[0]) |
         (static_cast<std::uint32_t>(bytes[1]) << 8U) |
         (static_cast<std::uint32_t>(bytes[2]) << 16U) |
         (static_cast<std::uint32_t>(bytes[3]) << 24U);
}

[[nodiscard]] std::uint64_t ReadU64(std::istream& input) {
  std::array<unsigned char, 8> bytes{};
  input.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
  if (!input) {
    throw std::runtime_error("truncated uint64 in native input");
  }
  std::uint64_t value = 0;
  for (std::size_t index = 0; index < bytes.size(); ++index) {
    value |= static_cast<std::uint64_t>(bytes[index]) << (8U * index);
  }
  return value;
}

void RequireMagic(std::istream& input, std::string_view expected) {
  std::string observed(expected.size(), '\0');
  input.read(observed.data(), static_cast<std::streamsize>(observed.size()));
  if (!input || observed != expected) {
    throw std::runtime_error("native input magic mismatch");
  }
}

[[nodiscard]] std::string Hex32(std::uint32_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::setw(8) << std::setfill('0') << value;
  return output.str();
}

[[nodiscard]] std::string Hex64(std::uint64_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::setw(16) << std::setfill('0') << value;
  return output.str();
}

void WriteScalarSuite(const std::string& input_path,
                      const std::string& output_path) {
  std::ifstream input(input_path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("failed to open scalar-suite input");
  }
  RequireMagic(input, kScalarInputMagic);
  const std::uint32_t case_count = ReadU32(input);

  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) {
    throw std::runtime_error("failed to create scalar-suite output");
  }
  output << "A4S_SCALAR_RESULT_V1\n";
  for (std::uint32_t case_index = 0; case_index < case_count; ++case_index) {
    const std::uint32_t case_id = ReadU32(input);
    const std::uint32_t sample_count = ReadU32(input);
    const std::uint32_t maximum_cardinality = ReadU32(input);
    if (sample_count == 0 || maximum_cardinality == 0) {
      throw std::runtime_error("invalid scalar-suite case shape");
    }
    std::vector<WeightedBinary32> samples;
    samples.reserve(sample_count);
    for (std::uint32_t sample = 0; sample < sample_count; ++sample) {
      WeightedBinary32 value;
      value.bits = ReadU32(input);
      value.weight = ReadU64(input);
      value.vector_id = ReadU64(input);
      samples.push_back(value);
    }

    const ScalarCurveResult curve =
        FitExactScalarCurve(samples, maximum_cardinality);
    output << "CASE\t" << case_id << '\t' << sample_count << '\t'
           << maximum_cardinality << '\t' << curve.support.size() << '\t'
           << curve.diagnostics.exact_comparisons << '\t'
           << curve.diagnostics.exact_ties << '\t'
           << curve.diagnostics.matrix_entry_evaluations << '\t'
           << curve.diagnostics.interval_evaluations << '\t'
           << curve.diagnostics.exact_replay_checks << '\n';
    for (std::size_t support_id = 0; support_id < curve.support.size();
         ++support_id) {
      const ExactSupportPoint& point = curve.support[support_id];
      output << "SUPPORT\t" << case_id << '\t' << support_id << '\t'
             << point.grid_integer.get_str() << '\t' << point.weight.get_str()
             << '\t' << point.lowest_vector_id << '\n';
    }
    for (std::uint32_t cardinality = 1;
         cardinality <= maximum_cardinality;
         ++cardinality) {
      const ScalarSolution& solution = curve.at(cardinality);
      output << "SOLUTION\t" << case_id << '\t' << cardinality << '\t'
             << solution.effective_cardinality << '\t'
             << solution.sse.numerator.get_str() << '\t'
             << solution.sse.denominator.get_str() << '\t'
             << solution.sse.binary_exponent << '\t'
             << solution.intervals.size() << '\t'
             << curve.diagnostics
                    .exact_comparisons_by_cardinality[cardinality]
             << '\t'
             << curve.diagnostics.exact_ties_by_cardinality[cardinality]
             << '\n';
      for (std::size_t cluster_id = 0;
           cluster_id < solution.intervals.size();
           ++cluster_id) {
        const ScalarInterval& interval = solution.intervals[cluster_id];
        const std::uint32_t f32 = RoundExactToBinary32Bits(interval.mean);
        const std::uint64_t f64 = RoundExactToBinary64Bits(interval.mean);
        output << "CLUSTER\t" << case_id << '\t' << cardinality << '\t'
               << cluster_id << '\t' << interval.begin << '\t' << interval.end
               << '\t' << interval.mean.numerator.get_str() << '\t'
               << interval.mean.denominator.get_str() << '\t'
               << interval.mean.binary_exponent << '\t' << Hex32(f32) << '\t'
               << Hex64(f64) << '\n';
      }
      // At-most-K semantics copy the H-support solution for every K>H.  The
      // corresponding certificate is therefore the H-layer predecessor row,
      // not a manufactured row for an empty-cluster layer.
      const std::uint32_t predecessor_layer =
          EffectivePredecessorLayer(curve, cardinality);
      output << "PREDECESSOR_ROW\t" << case_id << '\t' << cardinality
             << '\t' << curve.predecessors[predecessor_layer].size();
      for (const std::uint32_t predecessor :
           curve.predecessors[predecessor_layer]) {
        output << '\t' << predecessor;
      }
      output << '\n';
    }
    for (std::size_t layer = 1;
         layer < curve.diagnostics.predecessor_monotone.size();
         ++layer) {
      output << "MONOTONE\t" << case_id << '\t' << layer << '\t'
             << static_cast<unsigned int>(
                    curve.diagnostics.predecessor_monotone[layer])
             << '\n';
    }
    output << "END_CASE\t" << case_id << '\n';
  }
  char trailing = 0;
  if (input.read(&trailing, 1)) {
    throw std::runtime_error("scalar-suite input has trailing bytes");
  }
  output << "END\t" << case_count << '\n';
  output.flush();
  if (!output) {
    throw std::runtime_error("failed to flush scalar-suite output");
  }
}

void WriteNativeSmoke(const std::string& output_path) {
  RunExhaustiveAllocationReferenceHandSmoke();
  std::ofstream output(output_path, std::ios::binary | std::ios::trunc);
  if (!output) {
    throw std::runtime_error("failed to create native-smoke output");
  }
  const std::array<std::uint32_t, 10> patterns{
      0x00000000U, 0x80000000U, 0x00000001U, 0x007fffffU,
      0x00800000U, 0x3f800000U, 0x3f800001U, 0x7f7fffffU,
      0x80000001U, 0xbf800000U};
  output << "A4S_NATIVE_SMOKE_V1\n";
  for (const std::uint32_t bits : patterns) {
    const CanonicalScaledRational value(
        DecodeBinary32GridInteger(bits), 1, -149);
    output << "ROUNDTRIP\t" << Hex32(bits) << '\t'
           << value.numerator.get_str() << '\t'
           << Hex32(RoundExactToBinary32Bits(value)) << '\t'
           << Hex64(RoundExactToBinary64Bits(value)) << '\n';
  }
  const std::array<CanonicalScaledRational, 4> midpoint_cases{
      CanonicalScaledRational(1, 2, -149),
      CanonicalScaledRational(3, 2, -149),
      CanonicalScaledRational(-1, 2, -149),
      CanonicalScaledRational(-3, 2, -149)};
  for (const auto& value : midpoint_cases) {
    output << "MIDPOINT\t" << value.numerator.get_str() << '\t'
           << value.denominator.get_str() << '\t'
           << value.binary_exponent << '\t'
           << Hex32(RoundExactToBinary32Bits(value)) << '\t'
           << Hex64(RoundExactToBinary64Bits(value)) << '\n';
  }
  const std::array<CanonicalScaledRational, 2> rational_cases{
      CanonicalScaledRational(1, 3, 0),
      CanonicalScaledRational(-1, 3, 0)};
  for (const auto& value : rational_cases) {
    output << "RATIONAL\t" << value.numerator.get_str() << '\t'
           << value.denominator.get_str() << '\t' << value.binary_exponent
           << '\t' << Hex32(RoundExactToBinary32Bits(value)) << '\t'
           << Hex64(RoundExactToBinary64Bits(value)) << '\n';
  }

  // Deterministic K>H regression: the writer must reuse the H-layer
  // certificate while retaining the nominal requested cardinality.
  const std::vector<WeightedBinary32> scalar_samples{
      WeightedBinary32{0x00000000U, 1, 10},
      WeightedBinary32{0x3f800000U, 1, 11}};
  const ScalarCurveResult scalar_curve = FitExactScalarCurve(scalar_samples, 4);
  const ScalarSolution& support_solution = scalar_curve.at(2);
  const ScalarSolution& copied_solution = scalar_curve.at(4);
  const std::uint32_t copied_predecessor_layer =
      EffectivePredecessorLayer(scalar_curve, 4);
  bool copied_intervals_equal =
      support_solution.intervals.size() == copied_solution.intervals.size();
  for (std::size_t index = 0;
       copied_intervals_equal && index < support_solution.intervals.size();
       ++index) {
    const ScalarInterval& expected = support_solution.intervals[index];
    const ScalarInterval& observed = copied_solution.intervals[index];
    copied_intervals_equal =
        expected.begin == observed.begin && expected.end == observed.end &&
        expected.mean.numerator == observed.mean.numerator &&
        expected.mean.denominator == observed.mean.denominator &&
        expected.mean.binary_exponent == observed.mean.binary_exponent;
  }
  if (scalar_curve.support.size() != 2 ||
      copied_solution.requested_cardinality != 4 ||
      copied_solution.effective_cardinality != 2 ||
      copied_predecessor_layer != 2 ||
      support_solution.sse.numerator != copied_solution.sse.numerator ||
      support_solution.sse.denominator != copied_solution.sse.denominator ||
      support_solution.sse.binary_exponent !=
          copied_solution.sse.binary_exponent ||
      !copied_intervals_equal) {
    throw std::logic_error("native scalar K>H regression failed");
  }
  output << "SCALAR_K_GT_H\t4\t2\t" << copied_predecessor_layer << '\t'
         << scalar_curve.predecessors[copied_predecessor_layer].size() << '\n';

  // This calls block_vq.cpp's actual AssignAndReplay routine, not the
  // representation helper with similar tie semantics.
  const BlockAssignmentTieMicrofixtureResult assignment_tie =
      RunBlockAssignmentTieMicrofixture();
  if (assignment_tie.selected_codeword != 0 || assignment_tie.sse != 1.0 ||
      assignment_tie.distance_comparison_count != 2 ||
      assignment_tie.tie_count != 1) {
    throw std::logic_error("native block assignment tie regression failed");
  }
  output << "BLOCK_ASSIGNMENT_TIE\t" << assignment_tie.selected_codeword
         << '\t' << Hex64(std::bit_cast<std::uint64_t>(assignment_tie.sse))
         << '\t' << assignment_tie.distance_comparison_count << '\t'
         << assignment_tie.tie_count << '\n';

  const BlockFarthestFallbackMicrofixtureResult farthest_fallback =
      RunBlockFarthestFallbackMicrofixture();
  if (farthest_fallback.selected_cell_id != 3 ||
      farthest_fallback.selected_vector_id != 7 ||
      farthest_fallback.tie_count != 1) {
    throw std::logic_error("native block farthest fallback regression failed");
  }
  output << "BLOCK_FARTHEST_FALLBACK\t"
         << farthest_fallback.selected_cell_id << '\t'
         << farthest_fallback.selected_vector_id << '\t'
         << farthest_fallback.tie_count << '\n';

  const BlockVqMetadata valid_block_metadata{
      std::string(kBlockSuiteProtocolVersion), "native_smoke_valid_block", 1,
      0};
  const std::vector<Point2> valid_block_points{MakePoint2(
      0.0F, 0.0F, 0, 19, valid_block_metadata.protocol_version,
      valid_block_metadata.dataset_id)};
  const BlockVqTrainingResult valid_block_result = TrainFrozenBlockVq(
      valid_block_points, valid_block_metadata, {0.0}, {0.0});
  bool valid_start_inventory = valid_block_result.starts.size() == 8;
  for (std::size_t index = 0; index < valid_block_result.starts.size();
       ++index) {
    valid_start_inventory =
        valid_start_inventory &&
        valid_block_result.starts[index].start_id == index &&
        valid_block_result.starts[index].converged &&
        valid_block_result.starts[index].failure == BlockVqFailure::kNone;
  }
  if (!valid_block_result.control_valid || !valid_start_inventory ||
      valid_block_result.best_start_id != 0 ||
      valid_block_result.best_assignments != std::vector<std::uint32_t>{0}) {
    throw std::logic_error("native valid eight-start block regression failed");
  }
  output << "BLOCK_VALID_EIGHT_STARTS\t8\t0\n";

  // A finite center whose squared distance overflows binary64 must be a
  // CONTROL_INVALID result.  The seven independent salted starts still run.
  const BlockVqMetadata nonfinite_metadata{
      std::string(kBlockSuiteProtocolVersion),
      "native_smoke_nonfinite_control", 1, 0};
  const std::vector<Point2> nonfinite_points{MakePoint2(
      0.0F, 0.0F, 0, 20, nonfinite_metadata.protocol_version,
      nonfinite_metadata.dataset_id)};
  const BlockVqTrainingResult nonfinite_result = TrainFrozenBlockVq(
      nonfinite_points, nonfinite_metadata,
      {std::numeric_limits<double>::max()}, {0.0});
  bool complete_start_inventory = nonfinite_result.starts.size() == 8;
  for (std::size_t index = 0; index < nonfinite_result.starts.size(); ++index) {
    complete_start_inventory =
        complete_start_inventory &&
        nonfinite_result.starts[index].start_id == index &&
        (index == 0
             ? nonfinite_result.starts[index].failure ==
                   BlockVqFailure::kNonfiniteControl
             : nonfinite_result.starts[index].failure == BlockVqFailure::kNone &&
                   nonfinite_result.starts[index].converged);
  }
  if (nonfinite_result.control_valid ||
      nonfinite_result.failure != BlockVqFailure::kNonfiniteControl ||
      !complete_start_inventory || !nonfinite_result.best_centers.empty() ||
      !nonfinite_result.best_assignments.empty()) {
    throw std::logic_error("native block nonfinite-control regression failed");
  }
  output << "BLOCK_NONFINITE_CONTROL\t8\t0\n";
  output << "END\n";
}

[[nodiscard]] int Run(int argc, char** argv) {
  const NumericRuntimeManifest startup = initialize_frozen_numeric_runtime();
  if (argc < 2) {
    throw std::invalid_argument(
        "usage: a4_1s_native manifest | native-smoke OUT | "
        "scalar-suite INPUT OUT | block-suite INPUT OUT | "
        "representation-suite | allocation-suite INPUT OUT | "
        "encoding-suite INPUT OUT");
  }
  const std::string command = argv[1];
  if (command == "manifest") {
    if (argc != 2) {
      throw std::invalid_argument("manifest accepts no arguments");
    }
    const NumericRuntimeManifest final = capture_numeric_runtime_manifest();
    std::cout << numeric_runtime_manifest_json(startup, final) << '\n';
  } else if (command == "native-smoke") {
    if (argc != 3) {
      throw std::invalid_argument("native-smoke requires one output path");
    }
    WriteNativeSmoke(argv[2]);
  } else if (command == "scalar-suite") {
    if (argc != 4) {
      throw std::invalid_argument("scalar-suite requires input and output paths");
    }
    WriteScalarSuite(argv[2], argv[3]);
  } else if (command == "block-suite") {
    if (argc != 4) {
      throw std::invalid_argument("block-suite requires input and output paths");
    }
    static_cast<void>(WriteBlockSuiteFiles(argv[2], argv[3]));
  } else if (command == "representation-suite") {
    if (argc != 2) {
      throw std::invalid_argument("representation-suite accepts no arguments");
    }
    WriteRepresentationSuite(std::cout);
  } else if (command == "allocation-suite") {
    if (argc != 4) {
      throw std::invalid_argument("allocation-suite requires input and output paths");
    }
    WriteAllocationSuiteFiles(argv[2], argv[3]);
  } else if (command == "allocation-item") {
    if (argc != 4) {
      throw std::invalid_argument("allocation-item requires input and output paths");
    }
    WriteAllocationItemFiles(argv[2], argv[3]);
  } else if (command == "encoding-suite") {
    if (argc != 4) {
      throw std::invalid_argument("encoding-suite requires input and output paths");
    }
    WriteEncodingSuiteFiles(argv[2], argv[3]);
  } else {
    throw std::invalid_argument("unknown a4_1s_native command");
  }
  verify_frozen_numeric_runtime();
  return 0;
}

}  // namespace
}  // namespace saq::a4_1s

int main(int argc, char** argv) {
  try {
    return saq::a4_1s::Run(argc, argv);
  } catch (const std::exception& error) {
    std::cerr << "A4-1S IMPLEMENTATION_INVALID: " << error.what() << '\n';
    return 2;
  }
}

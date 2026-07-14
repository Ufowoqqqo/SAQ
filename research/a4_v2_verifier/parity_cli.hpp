#pragma once

#include "exact_reference.hpp"

#include <string>
#include <vector>

namespace saq::a4_v2::verifier {

[[nodiscard]] ExactCurve FitParityScalarExhaustive(
    const std::vector<WeightedExactSample>& samples,
    std::uint32_t maximum_cardinality);

void WriteScalarParity(const std::string& input_path,
                       const std::string& output_path);
void WriteBlockParity(const std::string& input_path,
                      const std::string& output_path);
void WriteRepresentationParity(const std::string& output_path);

}  // namespace saq::a4_v2::verifier

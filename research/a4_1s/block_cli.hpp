#pragma once

#include <cstdint>
#include <iosfwd>
#include <string>
#include <string_view>

namespace saq::a4_1s {

inline constexpr std::string_view kBlockSuiteProtocolVersion =
    "saq-attempt4-a4-1-20260713-schema2";

struct BlockCliSummary {
    std::uint32_t case_count{0};
    std::uint32_t control_valid_count{0};
    std::uint32_t control_invalid_count{0};
};

// Parse the frozen A4BLK001 little-endian stream, execute each block fixture,
// and emit deterministic authority-complete TSV.  Format/identity defects
// throw; a frozen block control failure is represented in TSV and counted in
// the returned summary.
[[nodiscard]] BlockCliSummary RunBlockSuiteStreams(std::istream &input,
                                                   std::ostream &output);

// File-path wrapper intended for the native command dispatcher.  Both paths
// are opened in binary mode and the output is truncated atomically at open.
[[nodiscard]] BlockCliSummary WriteBlockSuiteFiles(
    const std::string &input_path,
    const std::string &output_path);

} // namespace saq::a4_1s

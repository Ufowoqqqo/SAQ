#pragma once

#include <string>

namespace saq::a4_1s {

// Read exactly one canonical A4ALI001 request, run exactly one product arm or
// one global dyadic allocation, and write exactly one A4ALO001 result.  Both
// interchanges are binary, terminal-delimited, and require exact EOF.
inline void WriteAllocationItemFiles(const std::string &input_path,
                                     const std::string &output_path);

} // namespace saq::a4_1s

#include "allocation_item_cli_impl.hpp"

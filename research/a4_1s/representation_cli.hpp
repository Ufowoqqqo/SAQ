#pragma once

#include <iosfwd>
#include <string>

namespace saq::a4_1s {

// Run the complete frozen constant representation/allocation suite and write
// exactly one canonical JSON object followed by LF.  The function performs no
// random generation or dataset access.
void WriteRepresentationSuite(std::ostream &output);

// Bounded hand-constant validation for the independent exhaustive product
// reference.  It exercises same-H curves with different weights and performs
// no RNG, full parity sweep, cost measurement, or data access.
void RunExhaustiveAllocationReferenceHandSmoke();

// Read the fixed A4ALC001 exact-curve interchange, run the registered B4/B8
// group and global allocators, and write one canonical single-line JSON file.
// The binary input contains synthetic curve state only; this function has no
// dataset adapter and performs no random generation.
void WriteAllocationSuiteFiles(const std::string &input_path,
                               const std::string &output_path);

// Read one arm-major A4ENC002 full-shape encoding interchange and emit one
// arm-major A4EOUT02 binary result interchange.  The native executable is the sole
// authority for nearest-centroid assignment, mixed-radix addressing, and
// payload pack/unpack.  Both formats carry explicit schema/version, shape,
// record identifiers, terminal markers, and require exact EOF.
void WriteEncodingSuiteFiles(const std::string &input_path,
                             const std::string &output_path);

} // namespace saq::a4_1s

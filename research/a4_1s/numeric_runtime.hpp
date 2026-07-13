#pragma once

#include <cstdint>
#include <string>

namespace saq::a4_1s {

struct NumericRuntimeManifest {
  std::string compiler_id;
  std::string compiler_version;
  std::string compile_flags;
  std::string cpu_model;
  std::string gmp_library_version;
  std::string mpfr_library_version;
  std::string openssl_version;
  int rounding_mode{};
  std::string rounding_mode_name;
  std::uint32_t mxcsr{};
  bool mxcsr_flush_to_zero{};
  bool mxcsr_denormals_are_zero{};
};

// Establish the frozen floating-point environment.  Failure to set or verify
// any property is an implementation error and is reported with an exception.
void configure_frozen_numeric_runtime();

// Verify the environment without changing it.
void verify_frozen_numeric_runtime();

// Capture the compiler, exact-arithmetic libraries, CPU, rounding mode, and
// MXCSR state after verifying the frozen runtime contract.
[[nodiscard]] NumericRuntimeManifest capture_numeric_runtime_manifest();

// Configure, verify, and capture in the order required at process startup.
[[nodiscard]] NumericRuntimeManifest initialize_frozen_numeric_runtime();

// Stable JSON serialization for inclusion in a larger run manifest.  The two
// named snapshots make the parent protocol's initial/final floating-point
// environment evidence explicit.
[[nodiscard]] std::string numeric_runtime_manifest_json(
    const NumericRuntimeManifest& initial,
    const NumericRuntimeManifest& final);

}  // namespace saq::a4_1s

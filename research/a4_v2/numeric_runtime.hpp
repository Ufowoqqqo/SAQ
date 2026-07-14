#pragma once

#include <cstdint>
#include <string>

namespace saq::a4_v2::producer {

struct NumericManifest {
  std::string compiler;
  std::string compiler_version;
  std::string flags;
  std::string cpu;
  std::string gmp;
  std::string mpfr;
  std::string openssl;
  int rounding{0};
  std::uint32_t mxcsr{0};
};

[[nodiscard]] NumericManifest InitializeNumericRuntime();
[[nodiscard]] NumericManifest CaptureNumericRuntime();
void VerifyNumericRuntime();
[[nodiscard]] std::string NumericManifestJson(const NumericManifest& initial,
                                              const NumericManifest& final);

}  // namespace saq::a4_v2::producer

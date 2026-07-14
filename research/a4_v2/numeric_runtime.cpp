#include "numeric_runtime.hpp"

#include <cfenv>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>

#include <gmp.h>
#include <mpfr.h>
#include <openssl/crypto.h>

#if !defined(__x86_64__)
#error "A4-V2 producer requires x86-64"
#endif
#if !defined(__GNUC__) || defined(__clang__) || __GNUC__ != 11 || \
    __GNUC_MINOR__ != 5 || __GNUC_PATCHLEVEL__ != 0
#error "A4-V2 producer requires exactly GCC 11.5.0"
#endif

#include <xmmintrin.h>

#ifndef A4_V2_FROZEN_COMPILE_FLAGS
#error "A4-V2 compile-flag receipt must come from the reviewed CMake target"
#endif
#if defined(__FAST_MATH__) || \
    (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ != 0)
#error "A4-V2 producer was compiled with nonfrozen finite/fast-math semantics"
#endif
#if !defined(__OPTIMIZE__) || !defined(__SSE2__) || defined(__FMA__)
#error "A4-V2 producer compile-mode macros differ from the frozen numeric flags"
#endif

namespace saq::a4_v2::producer {
namespace {

constexpr std::uint32_t kFrozenMxcsr = 0x00001f80U;

[[nodiscard]] std::string Trim(std::string value) {
  while (!value.empty() &&
         std::isspace(static_cast<unsigned char>(value.front())) != 0) {
    value.erase(value.begin());
  }
  while (!value.empty() &&
         std::isspace(static_cast<unsigned char>(value.back())) != 0) {
    value.pop_back();
  }
  return value;
}

[[nodiscard]] std::string CpuModel() {
  std::ifstream input("/proc/cpuinfo");
  std::string line;
  while (std::getline(input, line)) {
    if (line.rfind("model name", 0) == 0) {
      const std::size_t colon = line.find(':');
      if (colon != std::string::npos) {
        return Trim(line.substr(colon + 1));
      }
    }
  }
  return "unknown";
}

[[nodiscard]] std::string Escape(std::string_view value) {
  std::ostringstream output;
  for (const unsigned char byte : value) {
    switch (byte) {
      case '"': output << "\\\""; break;
      case '\\': output << "\\\\"; break;
      case '\n': output << "\\n"; break;
      case '\r': output << "\\r"; break;
      case '\t': output << "\\t"; break;
      default:
        if (byte < 0x20U) {
          output << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                 << static_cast<unsigned int>(byte) << std::dec;
        } else {
          output << static_cast<char>(byte);
        }
    }
  }
  return output.str();
}

[[nodiscard]] std::string Hex32(std::uint32_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::setw(8) << std::setfill('0') << value;
  return output.str();
}

}  // namespace

void VerifyNumericRuntime() {
  if (std::fegetround() != FE_TONEAREST) {
    throw std::runtime_error("A4-V2 requires FE_TONEAREST");
  }
  if (_mm_getcsr() != kFrozenMxcsr) {
    throw std::runtime_error("A4-V2 requires MXCSR 0x00001f80");
  }
}

NumericManifest CaptureNumericRuntime() {
  VerifyNumericRuntime();
  return NumericManifest{"GCC",
                         __VERSION__,
                         A4_V2_FROZEN_COMPILE_FLAGS,
                         CpuModel(),
                         ::gmp_version,
                         ::mpfr_get_version(),
                         ::OpenSSL_version(OPENSSL_VERSION),
                         std::fegetround(),
                         _mm_getcsr()};
}

NumericManifest InitializeNumericRuntime() {
  if (std::fesetround(FE_TONEAREST) != 0) {
    throw std::runtime_error("cannot establish FE_TONEAREST");
  }
  _mm_setcsr(kFrozenMxcsr);
  return CaptureNumericRuntime();
}

std::string NumericManifestJson(const NumericManifest& initial,
                                const NumericManifest& final) {
  if (initial.compiler != final.compiler ||
      initial.compiler_version != final.compiler_version ||
      initial.flags != final.flags || initial.cpu != final.cpu ||
      initial.gmp != final.gmp || initial.mpfr != final.mpfr ||
      initial.openssl != final.openssl) {
    throw std::runtime_error("numeric identity changed during native process");
  }
  std::ostringstream output;
  // Lexicographic key order and no insignificant whitespace make this a
  // canonical JSON receipt suitable for hashing by the conductor.
  output << "{\"artifact_kind\":\"a4_v2_native_build_manifest\""
         << ",\"binary_protocols\":{"
         << "\"allocation_item\":\"A4ALI001/A4ALO001/schema-1\","
         << "\"block_suite\":\"A4BLK001/A4S_BLOCK_RESULT_V1/"
            "saq-attempt4-a4-1-20260713-schema2\","
         << "\"encoding_suite\":\"A4ENC002/A4EOUT02/schema-2\","
         << "\"scalar_suite\":\"A4SCL001/A4S_SCALAR_RESULT_V1\"}"
         << ",\"compile_flags\":\"" << Escape(initial.flags)
         << "\",\"compiler_id\":\"" << Escape(initial.compiler)
         << "\",\"compiler_version\":\"" << Escape(initial.compiler_version)
         << "\",\"cpu_model\":\"" << Escape(initial.cpu)
         << "\",\"final_mxcsr\":\"" << Hex32(final.mxcsr)
         << "\",\"final_mxcsr_denormals_are_zero\":false"
         << ",\"final_mxcsr_flush_to_zero\":false"
         << ",\"final_rounding_mode\":" << final.rounding
         << ",\"final_rounding_mode_name\":\"FE_TONEAREST\""
         << ",\"gmp_version\":\"" << Escape(initial.gmp)
         << "\",\"initial_mxcsr\":\"" << Hex32(initial.mxcsr)
         << "\",\"initial_mxcsr_denormals_are_zero\":false"
         << ",\"initial_mxcsr_flush_to_zero\":false"
         << ",\"initial_rounding_mode\":" << initial.rounding
         << ",\"initial_rounding_mode_name\":\"FE_TONEAREST\""
         << ",\"mpfr_version\":\"" << Escape(initial.mpfr)
         << "\",\"numeric_contract\":\"FE_TONEAREST;MXCSR=0x00001f80;"
            "no-FTZ;no-DAZ;no-FMA-contraction\""
         << ",\"openssl_version\":\"" << Escape(initial.openssl)
         << "\",\"schema_version\":1}";
  return output.str();
}

}  // namespace saq::a4_v2::producer

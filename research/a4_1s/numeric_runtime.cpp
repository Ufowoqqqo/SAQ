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
#error "The frozen A4-1S numeric runtime requires x86-64 MXCSR semantics"
#endif

#include <xmmintrin.h>

#if !defined(__GNUC__) || defined(__clang__)
#error "The frozen A4-1S numeric runtime requires GCC 11.5.0"
#endif

#if __GNUC__ != 11 || __GNUC_MINOR__ != 5 || __GNUC_PATCHLEVEL__ != 0
#error "The frozen A4-1S numeric runtime requires GCC 11.5.0"
#endif

#ifndef A4_1S_FROZEN_COMPILE_FLAGS
#define A4_1S_FROZEN_COMPILE_FLAGS                                      \
  "-O3 -fno-fast-math -ffp-contract=off -frounding-math " \
  "-mfpmath=sse"
#endif

namespace saq::a4_1s {
namespace {

constexpr std::uint32_t kMxcsrDenormalsAreZero = 1U << 6U;
constexpr std::uint32_t kMxcsrFlushToZero = 1U << 15U;
constexpr std::uint32_t kMxcsrForbiddenMask =
    kMxcsrDenormalsAreZero | kMxcsrFlushToZero;

std::string trim_copy(std::string value) {
  const auto is_space = [](unsigned char character) {
    return std::isspace(character) != 0;
  };
  while (!value.empty() && is_space(static_cast<unsigned char>(value.front()))) {
    value.erase(value.begin());
  }
  while (!value.empty() && is_space(static_cast<unsigned char>(value.back()))) {
    value.pop_back();
  }
  return value;
}

std::string read_cpu_model() {
  std::ifstream cpuinfo("/proc/cpuinfo");
  std::string line;
  while (std::getline(cpuinfo, line)) {
    if (line.rfind("model name", 0) != 0) {
      continue;
    }
    const auto separator = line.find(':');
    if (separator != std::string::npos) {
      const std::string model = trim_copy(line.substr(separator + 1));
      if (!model.empty()) {
        return model;
      }
    }
  }
  return "unknown";
}

std::string rounding_mode_name(int mode) {
  switch (mode) {
    case FE_TONEAREST:
      return "FE_TONEAREST";
    case FE_DOWNWARD:
      return "FE_DOWNWARD";
    case FE_UPWARD:
      return "FE_UPWARD";
    case FE_TOWARDZERO:
      return "FE_TOWARDZERO";
    default:
      return "UNKNOWN";
  }
}

std::string json_escape(std::string_view input) {
  std::ostringstream output;
  for (const unsigned char character : input) {
    switch (character) {
      case '"':
        output << "\\\"";
        break;
      case '\\':
        output << "\\\\";
        break;
      case '\b':
        output << "\\b";
        break;
      case '\f':
        output << "\\f";
        break;
      case '\n':
        output << "\\n";
        break;
      case '\r':
        output << "\\r";
        break;
      case '\t':
        output << "\\t";
        break;
      default:
        if (character < 0x20U) {
          output << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                 << static_cast<unsigned int>(character) << std::dec;
        } else {
          output << static_cast<char>(character);
        }
        break;
    }
  }
  return output.str();
}

std::string mxcsr_hex(std::uint32_t value) {
  std::ostringstream output;
  output << "0x" << std::hex << std::setw(8) << std::setfill('0') << value;
  return output.str();
}

}  // namespace

void configure_frozen_numeric_runtime() {
  if (std::fesetround(FE_TONEAREST) != 0) {
    throw std::runtime_error("failed to set FE_TONEAREST");
  }
  if (std::fegetround() != FE_TONEAREST) {
    throw std::runtime_error("rounding mode did not remain FE_TONEAREST");
  }

  const std::uint32_t initial_mxcsr = _mm_getcsr();
  _mm_setcsr(initial_mxcsr & ~kMxcsrForbiddenMask);
  const std::uint32_t configured_mxcsr = _mm_getcsr();
  if ((configured_mxcsr & kMxcsrForbiddenMask) != 0U) {
    throw std::runtime_error("failed to clear MXCSR FTZ/DAZ bits");
  }
}

void verify_frozen_numeric_runtime() {
  if (std::fegetround() != FE_TONEAREST) {
    throw std::runtime_error("numeric runtime is not FE_TONEAREST");
  }
  if ((_mm_getcsr() & kMxcsrForbiddenMask) != 0U) {
    throw std::runtime_error("numeric runtime has MXCSR FTZ or DAZ enabled");
  }
}

NumericRuntimeManifest capture_numeric_runtime_manifest() {
  verify_frozen_numeric_runtime();

  NumericRuntimeManifest manifest;
  manifest.compiler_id = "GCC";
  manifest.compiler_version = __VERSION__;
  manifest.compile_flags = A4_1S_FROZEN_COMPILE_FLAGS;
  manifest.cpu_model = read_cpu_model();
  manifest.gmp_library_version = ::gmp_version;
  manifest.mpfr_library_version = ::mpfr_get_version();
  manifest.openssl_version = ::OpenSSL_version(OPENSSL_VERSION);
  manifest.rounding_mode = std::fegetround();
  manifest.rounding_mode_name = rounding_mode_name(manifest.rounding_mode);
  manifest.mxcsr = _mm_getcsr();
  manifest.mxcsr_flush_to_zero =
      (manifest.mxcsr & kMxcsrFlushToZero) != 0U;
  manifest.mxcsr_denormals_are_zero =
      (manifest.mxcsr & kMxcsrDenormalsAreZero) != 0U;
  return manifest;
}

NumericRuntimeManifest initialize_frozen_numeric_runtime() {
  configure_frozen_numeric_runtime();
  return capture_numeric_runtime_manifest();
}

std::string numeric_runtime_manifest_json(
    const NumericRuntimeManifest& initial,
    const NumericRuntimeManifest& final) {
  if (initial.compiler_id != final.compiler_id ||
      initial.compiler_version != final.compiler_version ||
      initial.compile_flags != final.compile_flags ||
      initial.cpu_model != final.cpu_model ||
      initial.gmp_library_version != final.gmp_library_version ||
      initial.mpfr_library_version != final.mpfr_library_version ||
      initial.openssl_version != final.openssl_version) {
    throw std::runtime_error(
        "numeric runtime static manifest changed within one process");
  }
  std::ostringstream output;
  output << '{'
         << "\"compiler_id\":\"" << json_escape(initial.compiler_id) << "\","
         << "\"compiler_version\":\""
         << json_escape(initial.compiler_version) << "\","
         << "\"compile_flags\":\"" << json_escape(initial.compile_flags)
         << "\","
         << "\"cpu_model\":\"" << json_escape(initial.cpu_model) << "\","
         << "\"gmp_version\":\""
         << json_escape(initial.gmp_library_version) << "\","
         << "\"mpfr_version\":\""
         << json_escape(initial.mpfr_library_version)
         << "\","
         << "\"openssl_version\":\""
         << json_escape(initial.openssl_version) << "\","
         << "\"initial_rounding_mode\":" << initial.rounding_mode << ','
         << "\"initial_rounding_mode_name\":\""
         << json_escape(initial.rounding_mode_name) << "\","
         << "\"initial_mxcsr\":\"" << mxcsr_hex(initial.mxcsr) << "\","
         << "\"initial_mxcsr_flush_to_zero\":"
         << (initial.mxcsr_flush_to_zero ? "true" : "false") << ','
         << "\"initial_mxcsr_denormals_are_zero\":"
         << (initial.mxcsr_denormals_are_zero ? "true" : "false") << ','
         << "\"final_rounding_mode\":" << final.rounding_mode << ','
         << "\"final_rounding_mode_name\":\""
         << json_escape(final.rounding_mode_name) << "\","
         << "\"final_mxcsr\":\"" << mxcsr_hex(final.mxcsr) << "\","
         << "\"final_mxcsr_flush_to_zero\":"
         << (final.mxcsr_flush_to_zero ? "true" : "false") << ','
         << "\"final_mxcsr_denormals_are_zero\":"
         << (final.mxcsr_denormals_are_zero ? "true" : "false") << '}';
  return output.str();
}

}  // namespace saq::a4_1s

#include "input_panel.hpp"
#include "json_value.hpp"
#include "parity_cli.hpp"
#include "replay.hpp"

#include <cfenv>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

#if !defined(__x86_64__)
#error "A4-V2 verifier requires x86-64"
#endif
#if !defined(__GNUC__) || defined(__clang__) || __GNUC__ != 11 || \
    __GNUC_MINOR__ != 5 || __GNUC_PATCHLEVEL__ != 0
#error "A4-V2 verifier requires exactly GCC 11.5.0"
#endif

#include <xmmintrin.h>

namespace saq::a4_v2::verifier {
namespace {

constexpr std::uint32_t kFrozenMxcsr = 0x00001f80U;

void EstablishNumericRuntime() {
  if (std::fesetround(FE_TONEAREST) != 0) {
    throw std::runtime_error("cannot establish verifier FE_TONEAREST");
  }
  _mm_setcsr(kFrozenMxcsr);
  if (std::fegetround() != FE_TONEAREST || _mm_getcsr() != kFrozenMxcsr) {
    throw std::runtime_error("verifier numeric runtime does not match contract");
  }
}

void VerifyNumericRuntime() {
  if (std::fegetround() != FE_TONEAREST || _mm_getcsr() != kFrozenMxcsr) {
    throw std::runtime_error("numeric runtime changed during verifier work");
  }
}

int Run(int argc, char** argv) {
  EstablishNumericRuntime();
  if (argc < 2) {
    throw std::invalid_argument(
        "usage: a4_v2_native manifest | verify-canonical-request | "
        "par-scalar IN OUT | par-block IN OUT | par-representation OUT");
  }
  const std::string command(argv[1]);
  if (command == "manifest") {
    if (argc != 2) throw std::invalid_argument("manifest takes no arguments");
    std::cout << InputAuthorityManifestJson();
    VerifyNumericRuntime();
    return 0;
  }
  if (command == "par-scalar") {
    if (argc != 4) throw std::invalid_argument("par-scalar requires IN OUT");
    WriteScalarParity(argv[2], argv[3]);
    VerifyNumericRuntime();
    return 0;
  }
  if (command == "par-block") {
    if (argc != 4) throw std::invalid_argument("par-block requires IN OUT");
    WriteBlockParity(argv[2], argv[3]);
    VerifyNumericRuntime();
    return 0;
  }
  if (command == "par-representation") {
    if (argc != 3) throw std::invalid_argument("par-representation requires OUT");
    WriteRepresentationParity(argv[2]);
    VerifyNumericRuntime();
    return 0;
  }
  if (command != "verify-canonical-request" || argc != 2) {
    throw std::invalid_argument("unknown A4-V2 verifier command or arity");
  }
  std::string input((std::istreambuf_iterator<char>(std::cin)),
                    std::istreambuf_iterator<char>());
  if (input.size() > (1U << 20U)) {
    throw std::runtime_error("canonical verifier request exceeds 1 MiB");
  }
  const Json request = ParseCanonicalDocument(input, "verifier request");
  Json response;
  try {
    response = VerifyCanonicalRequest(request);
  } catch (const PanelIdentityError& error) {
    // Identity mismatch is an explicit incomplete verification result.  No
    // scientific replay is allowed after this branch.
    response = InputIdentityFailureResponse(request, error.what());
  }
  VerifyNumericRuntime();
  std::cout << DumpJson(response) << '\n';
  return 0;
}

}  // namespace
}  // namespace saq::a4_v2::verifier

int main(int argc, char** argv) {
  try {
    return saq::a4_v2::verifier::Run(argc, argv);
  } catch (const std::exception& error) {
    std::cerr << "A4-V2 VERIFIER_INVALID: " << error.what() << '\n';
    return 2;
  }
}

#include "sha256.hpp"

#include <openssl/sha.h>

#include <array>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace saq::a4_v2::verifier {

std::string Sha256(std::span<const std::uint8_t> bytes) {
  std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
  if (::SHA256(bytes.data(), bytes.size(), digest.data()) == nullptr) {
    throw std::runtime_error("SHA-256 failure");
  }
  std::ostringstream output;
  output << std::hex << std::nouppercase << std::setfill('0');
  for (const unsigned char byte : digest) {
    output << std::setw(2) << static_cast<unsigned int>(byte);
  }
  return output.str();
}

std::string Sha256(std::string_view bytes) {
  return Sha256(std::span<const std::uint8_t>(
      reinterpret_cast<const std::uint8_t*>(bytes.data()), bytes.size()));
}

}  // namespace saq::a4_v2::verifier

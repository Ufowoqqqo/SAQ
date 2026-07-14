#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <string_view>

namespace saq::a4_v2::verifier {

[[nodiscard]] std::string Sha256(std::span<const std::uint8_t> bytes);
[[nodiscard]] std::string Sha256(std::string_view bytes);

}  // namespace saq::a4_v2::verifier

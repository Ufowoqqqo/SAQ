#pragma once

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace saq::a4_v2::verifier {

inline constexpr std::uint32_t kRows = 8192;
inline constexpr std::uint32_t kDimensions = 128;

class PanelIdentityError : public std::runtime_error {
 public:
  explicit PanelIdentityError(const std::string& message)
      : std::runtime_error(message) {}
};

struct InputPanel {
  std::vector<std::uint32_t> row_major_bits;
  std::string raw_sha256;
  std::string python_version;
  std::string numpy_version;
};

// Regenerates the registered input inside this process using only the frozen
// external CPython/NumPy authority.  It never imports a repository module and
// never accepts a producer panel or checkpoint path.
[[nodiscard]] InputPanel RegenerateFrozenPanel();
[[nodiscard]] std::string InputAuthorityManifestJson();

}  // namespace saq::a4_v2::verifier

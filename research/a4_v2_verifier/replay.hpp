#pragma once

#include "json_value.hpp"

#include <string_view>

namespace saq::a4_v2::verifier {

// Parses the exact canonical request, regenerates the frozen input, and
// independently replays the complete producer prefix.  The returned object is
// the native response; callers append the sole terminal LF.
[[nodiscard]] Json VerifyCanonicalRequest(const Json& request);

// Produces a schema-shaped incomplete response for a frozen-input authority
// failure.  Scientific replay is deliberately not attempted after such a
// failure.
[[nodiscard]] Json InputIdentityFailureResponse(const Json& request,
                                                std::string_view message);

}  // namespace saq::a4_v2::verifier

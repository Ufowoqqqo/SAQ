#pragma once

#include <string>

namespace fmt {

template <typename... Arguments>
std::string format(const char *, Arguments &&...) {
    return {};
}

} // namespace fmt

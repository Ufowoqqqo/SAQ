#pragma once

#include <sstream>
#include <stdexcept>
#include <string>

namespace caq_co0_validation_stub {

class CheckFailure {
  public:
    CheckFailure(const char *expression, const char *file, int line) {
        stream_ << file << ':' << line << ": check failed: " << expression << ' ';
    }

    ~CheckFailure() noexcept(false) {
        throw std::runtime_error(stream_.str());
    }

    std::ostringstream &stream() {
        return stream_;
    }

  private:
    std::ostringstream stream_;
};

} // namespace caq_co0_validation_stub

#define CHECK(condition) \
    if (condition) {      \
    } else                \
        ::caq_co0_validation_stub::CheckFailure(#condition, __FILE__, __LINE__).stream()

#define CHECK_EQ(lhs, rhs) CHECK((lhs) == (rhs))
#define CHECK_NE(lhs, rhs) CHECK((lhs) != (rhs))
#define CHECK_LT(lhs, rhs) CHECK((lhs) < (rhs))
#define CHECK_LE(lhs, rhs) CHECK((lhs) <= (rhs))
#define CHECK_GT(lhs, rhs) CHECK((lhs) > (rhs))
#define CHECK_GE(lhs, rhs) CHECK((lhs) >= (rhs))

#define DCHECK(condition) CHECK(condition)
#define DCHECK_EQ(lhs, rhs) CHECK_EQ(lhs, rhs)
#define DCHECK_NE(lhs, rhs) CHECK_NE(lhs, rhs)
#define DCHECK_LT(lhs, rhs) CHECK_LT(lhs, rhs)
#define DCHECK_LE(lhs, rhs) CHECK_LE(lhs, rhs)
#define DCHECK_GT(lhs, rhs) CHECK_GT(lhs, rhs)
#define DCHECK_GE(lhs, rhs) CHECK_GE(lhs, rhs)

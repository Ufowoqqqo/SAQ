#include "json_value.hpp"

#include <charconv>
#include <cerrno>
#include <cstddef>
#include <cstring>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <type_traits>

#include <sys/stat.h>
#include <unistd.h>

namespace saq::a4_v2::verifier {
namespace {

[[noreturn]] void TypeError(const char* expected) {
  throw std::runtime_error(std::string("JSON value is not ") + expected);
}

void ValidateUtf8(std::string_view input) {
  const auto continuation = [](unsigned char byte) {
    return byte >= 0x80U && byte <= 0xbfU;
  };
  for (std::size_t index = 0; index < input.size();) {
    const unsigned char first = static_cast<unsigned char>(input[index]);
    if (first <= 0x7fU) {
      ++index;
      continue;
    }
    std::size_t length = 0;
    unsigned char second_minimum = 0x80U;
    unsigned char second_maximum = 0xbfU;
    if (first >= 0xc2U && first <= 0xdfU) {
      length = 2;
    } else if (first >= 0xe0U && first <= 0xefU) {
      length = 3;
      if (first == 0xe0U) second_minimum = 0xa0U;  // No overlong form.
      if (first == 0xedU) second_maximum = 0x9fU;  // No surrogate scalar.
    } else if (first >= 0xf0U && first <= 0xf4U) {
      length = 4;
      if (first == 0xf0U) second_minimum = 0x90U;  // No overlong form.
      if (first == 0xf4U) second_maximum = 0x8fU;  // At most U+10FFFF.
    } else {
      throw std::runtime_error("JSON is not well-formed UTF-8");
    }
    if (index + length > input.size()) {
      throw std::runtime_error("JSON contains truncated UTF-8");
    }
    const unsigned char second =
        static_cast<unsigned char>(input[index + 1]);
    if (second < second_minimum || second > second_maximum) {
      throw std::runtime_error("JSON contains noncanonical UTF-8");
    }
    for (std::size_t offset = 2; offset < length; ++offset) {
      if (!continuation(static_cast<unsigned char>(input[index + offset]))) {
        throw std::runtime_error("JSON contains invalid UTF-8 continuation");
      }
    }
    index += length;
  }
}

void AppendUtf8(std::string* output, std::uint32_t codepoint) {
  if (codepoint <= 0x7fU) {
    output->push_back(static_cast<char>(codepoint));
  } else if (codepoint <= 0x7ffU) {
    output->push_back(static_cast<char>(0xc0U | (codepoint >> 6U)));
    output->push_back(static_cast<char>(0x80U | (codepoint & 0x3fU)));
  } else if (codepoint <= 0xffffU) {
    output->push_back(static_cast<char>(0xe0U | (codepoint >> 12U)));
    output->push_back(static_cast<char>(0x80U | ((codepoint >> 6U) & 0x3fU)));
    output->push_back(static_cast<char>(0x80U | (codepoint & 0x3fU)));
  } else if (codepoint <= 0x10ffffU) {
    output->push_back(static_cast<char>(0xf0U | (codepoint >> 18U)));
    output->push_back(static_cast<char>(0x80U | ((codepoint >> 12U) & 0x3fU)));
    output->push_back(static_cast<char>(0x80U | ((codepoint >> 6U) & 0x3fU)));
    output->push_back(static_cast<char>(0x80U | (codepoint & 0x3fU)));
  } else {
    throw std::runtime_error("JSON Unicode scalar is out of range");
  }
}

class Parser {
 public:
  explicit Parser(std::string_view input) : input_(input) {}

  Json Parse() {
    ValidateUtf8(input_);
    Json result = Value();
    if (position_ != input_.size()) Fail("trailing bytes");
    return result;
  }

 private:
  [[noreturn]] void Fail(const char* message) const {
    throw std::runtime_error(std::string("JSON parse error at byte ") +
                             std::to_string(position_) + ": " + message);
  }

  char Take() {
    if (position_ == input_.size()) Fail("unexpected EOF");
    return input_[position_++];
  }

  bool Consume(std::string_view token) {
    if (input_.substr(position_, token.size()) != token) return false;
    position_ += token.size();
    return true;
  }

  Json Value() {
    if (position_ == input_.size()) Fail("missing value");
    switch (input_[position_]) {
      case 'n':
        if (!Consume("null")) Fail("invalid null");
        return Json(nullptr);
      case 't':
        if (!Consume("true")) Fail("invalid true");
        return Json(true);
      case 'f':
        if (!Consume("false")) Fail("invalid false");
        return Json(false);
      case '"': return Json(String());
      case '[': return Json(Array());
      case '{': return Json(Object());
      default: return Json(Integer());
    }
  }

  std::int64_t Integer() {
    const std::size_t begin = position_;
    if (input_[position_] == '-') ++position_;
    if (position_ == input_.size()) Fail("truncated integer");
    if (input_[position_] == '0') {
      ++position_;
      if (position_ != input_.size() && input_[position_] >= '0' &&
          input_[position_] <= '9') {
        Fail("integer has a leading zero");
      }
    } else {
      if (input_[position_] < '1' || input_[position_] > '9') {
        Fail("expected integer");
      }
      while (position_ != input_.size() && input_[position_] >= '0' &&
             input_[position_] <= '9') {
        ++position_;
      }
    }
    if (position_ != input_.size() &&
        (input_[position_] == '.' || input_[position_] == 'e' ||
         input_[position_] == 'E')) {
      Fail("floating JSON number is forbidden");
    }
    std::int64_t result = 0;
    const char* first = input_.data() + begin;
    const char* last = input_.data() + position_;
    const auto parsed = std::from_chars(first, last, result);
    if (parsed.ec != std::errc{} || parsed.ptr != last) {
      Fail("integer is outside signed 64-bit range");
    }
    return result;
  }

  std::uint32_t Hex4() {
    if (position_ + 4 > input_.size()) Fail("truncated Unicode escape");
    std::uint32_t result = 0;
    for (int index = 0; index < 4; ++index) {
      const char byte = input_[position_++];
      result <<= 4U;
      if (byte >= '0' && byte <= '9') result |= byte - '0';
      else if (byte >= 'a' && byte <= 'f') result |= byte - 'a' + 10;
      else if (byte >= 'A' && byte <= 'F') result |= byte - 'A' + 10;
      else Fail("invalid Unicode escape");
    }
    return result;
  }

  std::string String() {
    if (Take() != '"') Fail("expected string");
    std::string result;
    while (true) {
      const unsigned char byte = static_cast<unsigned char>(Take());
      if (byte == '"') return result;
      if (byte < 0x20U) Fail("unescaped control byte");
      if (byte != '\\') {
        result.push_back(static_cast<char>(byte));
        continue;
      }
      switch (Take()) {
        case '"': result.push_back('"'); break;
        case '\\': result.push_back('\\'); break;
        case '/': result.push_back('/'); break;
        case 'b': result.push_back('\b'); break;
        case 'f': result.push_back('\f'); break;
        case 'n': result.push_back('\n'); break;
        case 'r': result.push_back('\r'); break;
        case 't': result.push_back('\t'); break;
        case 'u': {
          std::uint32_t codepoint = Hex4();
          if (codepoint >= 0xd800U && codepoint <= 0xdbffU) {
            if (!Consume("\\u")) Fail("missing low surrogate");
            const std::uint32_t low = Hex4();
            if (low < 0xdc00U || low > 0xdfffU) Fail("invalid low surrogate");
            codepoint = 0x10000U + ((codepoint - 0xd800U) << 10U) +
                        (low - 0xdc00U);
          } else if (codepoint >= 0xdc00U && codepoint <= 0xdfffU) {
            Fail("unpaired low surrogate");
          }
          AppendUtf8(&result, codepoint);
          break;
        }
        default: Fail("invalid string escape");
      }
    }
  }

  Json::Array Array() {
    if (Take() != '[') Fail("expected array");
    Json::Array result;
    if (position_ != input_.size() && input_[position_] == ']') {
      ++position_;
      return result;
    }
    while (true) {
      result.push_back(Value());
      const char delimiter = Take();
      if (delimiter == ']') return result;
      if (delimiter != ',') Fail("expected array comma");
    }
  }

  Json::Object Object() {
    if (Take() != '{') Fail("expected object");
    Json::Object result;
    if (position_ != input_.size() && input_[position_] == '}') {
      ++position_;
      return result;
    }
    while (true) {
      if (position_ == input_.size() || input_[position_] != '"') {
        Fail("object key is not a string");
      }
      std::string key = String();
      if (Take() != ':') Fail("expected object colon");
      if (!result.emplace(std::move(key), Value()).second) {
        Fail("duplicate object key");
      }
      const char delimiter = Take();
      if (delimiter == '}') return result;
      if (delimiter != ',') Fail("expected object comma");
    }
  }

  std::string_view input_;
  std::size_t position_{0};
};

void DumpString(std::string_view value, std::string* output) {
  output->push_back('"');
  constexpr char kHex[] = "0123456789abcdef";
  for (const unsigned char byte : value) {
    switch (byte) {
      case '"': output->append("\\\""); break;
      case '\\': output->append("\\\\"); break;
      case '\b': output->append("\\b"); break;
      case '\f': output->append("\\f"); break;
      case '\n': output->append("\\n"); break;
      case '\r': output->append("\\r"); break;
      case '\t': output->append("\\t"); break;
      default:
        if (byte < 0x20U) {
          output->append("\\u00");
          output->push_back(kHex[byte >> 4U]);
          output->push_back(kHex[byte & 15U]);
        } else {
          output->push_back(static_cast<char>(byte));
        }
    }
  }
  output->push_back('"');
}

}  // namespace

bool Json::is_null() const noexcept {
  return std::holds_alternative<std::nullptr_t>(value_);
}
bool Json::boolean() const {
  if (const auto* value = std::get_if<bool>(&value_)) return *value;
  TypeError("a boolean");
}
std::int64_t Json::integer() const {
  if (const auto* value = std::get_if<std::int64_t>(&value_)) return *value;
  TypeError("an integer");
}
const std::string& Json::string() const {
  if (const auto* value = std::get_if<std::string>(&value_)) return *value;
  TypeError("a string");
}
const Json::Array& Json::array() const {
  if (const auto* value = std::get_if<Array>(&value_)) return *value;
  TypeError("an array");
}
const Json::Object& Json::object() const {
  if (const auto* value = std::get_if<Object>(&value_)) return *value;
  TypeError("an object");
}
Json::Array& Json::array() {
  if (auto* value = std::get_if<Array>(&value_)) return *value;
  TypeError("an array");
}
Json::Object& Json::object() {
  if (auto* value = std::get_if<Object>(&value_)) return *value;
  TypeError("an object");
}
const Json& Json::at(std::string_view key) const {
  const Object& values = object();
  const auto iterator = values.find(key);
  if (iterator == values.end()) {
    throw std::runtime_error("JSON object is missing key: " + std::string(key));
  }
  return iterator->second;
}
bool Json::contains(std::string_view key) const {
  return object().contains(key);
}

std::string DumpJson(const Json& value) {
  std::string output;
  const auto visit = [&output](const auto& self, const Json& node) -> void {
    std::visit(
        [&output, &self](const auto& item) {
          using T = std::decay_t<decltype(item)>;
          if constexpr (std::is_same_v<T, std::nullptr_t>) output.append("null");
          else if constexpr (std::is_same_v<T, bool>)
            output.append(item ? "true" : "false");
          else if constexpr (std::is_same_v<T, std::int64_t>)
            output.append(std::to_string(item));
          else if constexpr (std::is_same_v<T, std::string>) DumpString(item, &output);
          else if constexpr (std::is_same_v<T, Json::Array>) {
            output.push_back('[');
            for (std::size_t index = 0; index < item.size(); ++index) {
              if (index != 0) output.push_back(',');
              self(self, item[index]);
            }
            output.push_back(']');
          } else {
            output.push_back('{');
            std::size_t index = 0;
            for (const auto& [key, child] : item) {
              if (index++ != 0) output.push_back(',');
              DumpString(key, &output);
              output.push_back(':');
              self(self, child);
            }
            output.push_back('}');
          }
        },
        node.value_);
  };
  visit(visit, value);
  return output;
}

Json ParseCanonicalDocument(std::string_view payload,
                            std::string_view description) {
  if (payload.empty() || payload.back() != '\n' ||
      (payload.size() > 1 && payload[payload.size() - 2] == '\n')) {
    throw std::runtime_error(std::string(description) +
                             " must have exactly one terminal LF");
  }
  Json result = Parser(payload.substr(0, payload.size() - 1)).Parse();
  if (DumpJson(result) + "\n" != payload) {
    throw std::runtime_error(std::string(description) +
                             " is not canonical JSON");
  }
  return result;
}

std::vector<Json> ParseCanonicalLines(std::string_view payload,
                                      std::string_view description) {
  std::vector<Json> result;
  if (payload.empty()) return result;
  std::size_t begin = 0;
  std::size_t line = 1;
  while (begin < payload.size()) {
    const std::size_t end = payload.find('\n', begin);
    if (end == std::string_view::npos) {
      throw std::runtime_error(std::string(description) +
                               " has unterminated JSONL");
    }
    result.push_back(ParseCanonicalDocument(
        payload.substr(begin, end - begin + 1),
        std::string(description) + " line " + std::to_string(line++)));
    begin = end + 1;
  }
  return result;
}

std::string ReadFileDescriptor(int descriptor, std::uint64_t maximum_bytes) {
  if (descriptor < 0) throw std::runtime_error("artifact descriptor is negative");
  struct stat before {};
  if (::fstat(descriptor, &before) != 0) {
    throw std::runtime_error(std::string("cannot fstat artifact descriptor: ") +
                             std::strerror(errno));
  }
  if (!S_ISREG(before.st_mode) || before.st_size < 0 ||
      static_cast<std::uint64_t>(before.st_size) > maximum_bytes) {
    throw std::runtime_error("artifact descriptor is nonregular or exceeds ceiling");
  }
  std::string result(static_cast<std::size_t>(before.st_size), '\0');
  std::size_t offset = 0;
  while (offset < result.size()) {
    const ssize_t count = ::pread(descriptor, result.data() + offset,
                                  result.size() - offset,
                                  static_cast<off_t>(offset));
    if (count < 0 && errno == EINTR) continue;
    if (count <= 0) throw std::runtime_error("short artifact descriptor read");
    offset += static_cast<std::size_t>(count);
  }
  char trailer = '\0';
  ssize_t trailer_count;
  do {
    trailer_count = ::pread(descriptor, &trailer, 1, before.st_size);
  } while (trailer_count < 0 && errno == EINTR);
  if (trailer_count != 0) {
    throw std::runtime_error("artifact descriptor grew during read");
  }
  struct stat after {};
  if (::fstat(descriptor, &after) != 0 || before.st_dev != after.st_dev ||
      before.st_ino != after.st_ino || before.st_mode != after.st_mode ||
      before.st_size != after.st_size ||
      before.st_mtim.tv_sec != after.st_mtim.tv_sec ||
      before.st_mtim.tv_nsec != after.st_mtim.tv_nsec ||
      before.st_ctim.tv_sec != after.st_ctim.tv_sec ||
      before.st_ctim.tv_nsec != after.st_ctim.tv_nsec) {
    throw std::runtime_error("artifact descriptor changed during read");
  }
  return result;
}

}  // namespace saq::a4_v2::verifier

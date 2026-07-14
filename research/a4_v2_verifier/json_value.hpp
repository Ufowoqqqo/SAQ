#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace saq::a4_v2::verifier {

class Json {
 public:
  using Array = std::vector<Json>;
  using Object = std::map<std::string, Json, std::less<>>;

  Json() = default;
  Json(std::nullptr_t) : value_(nullptr) {}
  Json(bool value) : value_(value) {}
  Json(std::int64_t value) : value_(value) {}
  Json(std::string value) : value_(std::move(value)) {}
  Json(const char* value) : value_(std::string(value)) {}
  Json(Array value) : value_(std::move(value)) {}
  Json(Object value) : value_(std::move(value)) {}

  [[nodiscard]] bool is_null() const noexcept;
  [[nodiscard]] bool boolean() const;
  [[nodiscard]] std::int64_t integer() const;
  [[nodiscard]] const std::string& string() const;
  [[nodiscard]] const Array& array() const;
  [[nodiscard]] const Object& object() const;
  [[nodiscard]] Array& array();
  [[nodiscard]] Object& object();
  [[nodiscard]] const Json& at(std::string_view key) const;
  [[nodiscard]] bool contains(std::string_view key) const;

 private:
  std::variant<std::nullptr_t, bool, std::int64_t, std::string, Array, Object>
      value_{nullptr};
  friend std::string DumpJson(const Json& value);
};

[[nodiscard]] Json ParseCanonicalDocument(std::string_view payload,
                                          std::string_view description);
[[nodiscard]] std::vector<Json> ParseCanonicalLines(
    std::string_view payload, std::string_view description);
[[nodiscard]] std::string DumpJson(const Json& value);
[[nodiscard]] std::string ReadFileDescriptor(int descriptor,
                                             std::uint64_t maximum_bytes);

}  // namespace saq::a4_v2::verifier

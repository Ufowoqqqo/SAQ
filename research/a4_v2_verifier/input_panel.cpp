#include "input_panel.hpp"

#include "json_value.hpp"
#include "sha256.hpp"

#include <Python.h>
#include <gmp.h>
#include <openssl/crypto.h>

#include <bit>
#include <cstring>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <system_error>

namespace saq::a4_v2::verifier {
namespace {

constexpr const char* kExpectedPythonPrefix = "3.9.25 ";
constexpr const char* kExpectedNumpy = "1.23.5";
constexpr const char* kExpectedRaw =
    "10e128854768358323a8b13066a6f34076cfc7216db35992ac58ece0ec6f5b0c";

[[noreturn]] void PythonFailure(const char* message) {
  if (PyErr_Occurred() != nullptr) PyErr_Print();
  throw PanelIdentityError(message);
}

[[nodiscard]] std::string PythonString(PyObject* object, const char* field) {
  if (object == nullptr || !PyUnicode_Check(object)) PythonFailure(field);
  const char* value = PyUnicode_AsUTF8(object);
  if (value == nullptr) PythonFailure(field);
  return value;
}

[[nodiscard]] std::filesystem::path AbsoluteNormalizedPath(
    const std::string& value, const char* field) {
  const std::filesystem::path path(value);
  if (!path.is_absolute()) {
    throw PanelIdentityError(std::string(field) + " is not absolute");
  }
  std::error_code error;
  const std::filesystem::path normalized =
      std::filesystem::weakly_canonical(path, error);
  if (error) {
    throw PanelIdentityError(std::string("cannot normalize ") + field);
  }
  return normalized.lexically_normal();
}

[[nodiscard]] bool IsWithin(const std::filesystem::path& candidate,
                            const std::filesystem::path& root) {
  auto candidate_part = candidate.begin();
  for (auto root_part = root.begin(); root_part != root.end(); ++root_part) {
    if (candidate_part == candidate.end() || *candidate_part != *root_part) {
      return false;
    }
    ++candidate_part;
  }
  return true;
}

void RequireFlag(PyObject* flags, const char* name, long expected) {
  PyObject* value = PyObject_GetAttrString(flags, name);
  if (value == nullptr || !PyLong_Check(value)) {
    Py_XDECREF(value);
    PythonFailure("isolated CPython flag is unavailable");
  }
  const long observed = PyLong_AsLong(value);
  Py_DECREF(value);
  if (PyErr_Occurred() != nullptr) PythonFailure("cannot read CPython flag");
  if (observed != expected) {
    throw PanelIdentityError(std::string("unexpected isolated CPython flag: ") +
                             name);
  }
}

void ValidateIsolatedRuntime() {
  PyObject* flags = PySys_GetObject("flags");  // Borrowed.
  if (flags == nullptr) PythonFailure("CPython flags are unavailable");
  RequireFlag(flags, "isolated", 1);
  RequireFlag(flags, "ignore_environment", 1);
  RequireFlag(flags, "no_user_site", 1);
  RequireFlag(flags, "no_site", 1);

  const std::filesystem::path expected_site =
      AbsoluteNormalizedPath(A4_V2_NUMPY_SITE_PACKAGES,
                             "registered NumPy site-packages");
  const std::filesystem::path repository =
      AbsoluteNormalizedPath(A4_V2_VERIFIER_REPO_ROOT, "verifier repository");
  PyObject* search_path = PySys_GetObject("path");  // Borrowed.
  if (search_path == nullptr || !PyList_Check(search_path)) {
    PythonFailure("isolated CPython sys.path is unavailable");
  }
  bool found_registered_site = false;
  const Py_ssize_t count = PyList_Size(search_path);
  for (Py_ssize_t index = 0; index < count; ++index) {
    PyObject* entry = PyList_GetItem(search_path, index);  // Borrowed.
    const std::string value = PythonString(entry, "non-string sys.path entry");
    if (value.empty()) {
      throw PanelIdentityError("isolated CPython sys.path contains cwd");
    }
    const std::filesystem::path normalized =
        AbsoluteNormalizedPath(value, "isolated CPython sys.path entry");
    if (IsWithin(normalized, repository)) {
      throw PanelIdentityError("isolated CPython sys.path enters repository");
    }
    found_registered_site = found_registered_site || normalized == expected_site;
  }
  if (!found_registered_site) {
    throw PanelIdentityError(
        "isolated CPython omitted registered NumPy site-packages");
  }
}

void ValidateNumpyOrigin(PyObject* numpy) {
  PyObject* file =
      numpy == nullptr ? nullptr : PyObject_GetAttrString(numpy, "__file__");
  if (file == nullptr) PythonFailure("NumPy origin is unavailable");
  const std::string origin = PythonString(file, "NumPy origin");
  Py_DECREF(file);
  const std::filesystem::path observed =
      AbsoluteNormalizedPath(origin, "NumPy origin");
  const std::filesystem::path expected_package =
      AbsoluteNormalizedPath(A4_V2_NUMPY_PACKAGE_DIR,
                             "registered NumPy package");
  if (observed.parent_path() != expected_package ||
      observed.filename() != "__init__.py") {
    throw PanelIdentityError("NumPy was not imported from registered package");
  }
}

void RejectRepositoryModuleImports() {
  const std::filesystem::path repository =
      AbsoluteNormalizedPath(A4_V2_VERIFIER_REPO_ROOT, "verifier repository");
  PyObject* modules = PyImport_GetModuleDict();  // Borrowed.
  if (modules == nullptr || !PyDict_Check(modules)) {
    PythonFailure("CPython module table is unavailable");
  }
  Py_ssize_t position = 0;
  PyObject* name = nullptr;
  PyObject* module = nullptr;
  while (PyDict_Next(modules, &position, &name, &module) != 0) {
    PyObject* file = PyObject_GetAttrString(module, "__file__");
    if (file == nullptr) {
      PyErr_Clear();
      continue;
    }
    if (PyUnicode_Check(file)) {
      const std::string origin = PythonString(file, "module origin");
      const std::filesystem::path normalized =
          AbsoluteNormalizedPath(origin, "module origin");
      Py_DECREF(file);
      if (IsWithin(normalized, repository)) {
        throw PanelIdentityError("CPython imported a repository module");
      }
    } else {
      Py_DECREF(file);
    }
  }
}

[[noreturn]] void ConfigFailure(PyConfig* config, PyStatus status,
                                const char* operation) {
  const std::string detail = status.err_msg == nullptr ? "unknown error"
                                                       : status.err_msg;
  PyConfig_Clear(config);
  if (Py_IsInitialized() != 0) Py_FinalizeEx();
  throw PanelIdentityError(std::string(operation) + ": " + detail);
}

void RequireConfigStatus(PyConfig* config, PyStatus status,
                         const char* operation) {
  if (PyStatus_Exception(status) != 0) {
    ConfigFailure(config, status, operation);
  }
}

class Interpreter {
 public:
  Interpreter() {
    if (Py_IsInitialized() != 0) {
      throw PanelIdentityError(
          "embedded Python was initialized before verifier input");
    }
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.isolated = 1;
    config.use_environment = 0;
    config.user_site_directory = 0;
    config.site_import = 0;
    config.parse_argv = 0;
    config.install_signal_handlers = 0;
    config.write_bytecode = 0;
    RequireConfigStatus(
        &config,
        PyConfig_SetBytesString(&config, &config.program_name,
                                A4_V2_PYTHON_EXECUTABLE),
        "cannot set frozen CPython executable");
    RequireConfigStatus(&config, PyConfig_Read(&config),
                        "cannot read isolated CPython configuration");
    std::size_t wide_length = 0;
    wchar_t* numpy_site =
        Py_DecodeLocale(A4_V2_NUMPY_SITE_PACKAGES, &wide_length);
    if (numpy_site == nullptr || wide_length == static_cast<std::size_t>(-1)) {
      PyMem_RawFree(numpy_site);
      ConfigFailure(&config, PyStatus_NoMemory(),
                    "cannot decode registered NumPy site-packages");
    }
    const PyStatus append_status =
        PyWideStringList_Append(&config.module_search_paths, numpy_site);
    PyMem_RawFree(numpy_site);
    RequireConfigStatus(&config, append_status,
                        "cannot append registered NumPy site-packages");
    config.module_search_paths_set = 1;
    const PyStatus initialize_status = Py_InitializeFromConfig(&config);
    RequireConfigStatus(&config, initialize_status,
                        "cannot initialize frozen CPython authority");
    PyConfig_Clear(&config);
    if (Py_IsInitialized() == 0) {
      throw PanelIdentityError("cannot initialize frozen CPython authority");
    }
    try {
      ValidateIsolatedRuntime();
    } catch (...) {
      Py_FinalizeEx();
      throw;
    }
  }
  ~Interpreter() {
    if (Py_IsInitialized() != 0) Py_FinalizeEx();
  }
  Interpreter(const Interpreter&) = delete;
  Interpreter& operator=(const Interpreter&) = delete;
};

}  // namespace

InputPanel RegenerateFrozenPanel() {
  Interpreter interpreter;
  const std::string python_version = Py_GetVersion();
  if (python_version.rfind(kExpectedPythonPrefix, 0) != 0) {
    throw PanelIdentityError("CPython runtime is not exactly 3.9.25");
  }

  PyObject* main_module = PyImport_AddModule("__main__");  // Borrowed.
  if (main_module == nullptr) PythonFailure("cannot acquire __main__");
  PyObject* globals = PyModule_GetDict(main_module);  // Borrowed.
  if (globals == nullptr) PythonFailure("cannot acquire Python globals");
  // No sys.path mutation and no repository import occurs here.  NumPy is the
  // registered input authority, not a scientific implementation dependency.
  constexpr const char* kProgram =
      "import numpy as _a4_np\n"
      "if _a4_np.__version__ != '1.23.5':\n"
      "    raise RuntimeError('NumPy authority mismatch')\n"
      "_a4_panel = _a4_np.random.Generator("
      "_a4_np.random.PCG64(20260713)).standard_normal("
      "(8192,128), dtype=_a4_np.float32)\n"
      "if (_a4_panel.shape != (8192,128) or "
      "_a4_panel.dtype.str not in ('<f4','=f4') or "
      "not _a4_panel.flags.c_contiguous):\n"
      "    raise RuntimeError('panel layout mismatch')\n";
  PyObject* executed =
      PyRun_StringFlags(kProgram, Py_file_input, globals, globals, nullptr);
  if (executed == nullptr) PythonFailure("frozen NumPy panel generation failed");
  Py_DECREF(executed);

  PyObject* numpy = PyDict_GetItemString(globals, "_a4_np");  // Borrowed.
  PyObject* version_object =
      numpy == nullptr ? nullptr : PyObject_GetAttrString(numpy, "__version__");
  if (version_object == nullptr) PythonFailure("NumPy version is unavailable");
  const std::string numpy_version = PythonString(version_object, "NumPy version");
  Py_DECREF(version_object);
  if (numpy_version != kExpectedNumpy) {
    throw PanelIdentityError("NumPy runtime is not exactly 1.23.5");
  }
  ValidateNumpyOrigin(numpy);
  RejectRepositoryModuleImports();

  PyObject* matrix = PyDict_GetItemString(globals, "_a4_panel");  // Borrowed.
  if (matrix == nullptr) PythonFailure("generated panel is unavailable");
  Py_buffer view{};
  if (PyObject_GetBuffer(matrix, &view, PyBUF_CONTIG_RO) != 0) {
    PythonFailure("generated panel does not expose a contiguous buffer");
  }
  struct Release {
    Py_buffer* view;
    ~Release() { PyBuffer_Release(view); }
  } release{&view};
  constexpr std::size_t kBytes =
      static_cast<std::size_t>(kRows) * kDimensions * sizeof(std::uint32_t);
  if (view.len != static_cast<Py_ssize_t>(kBytes) || view.buf == nullptr) {
    throw PanelIdentityError("generated panel byte size is not 4,194,304");
  }
  const auto* bytes = static_cast<const std::uint8_t*>(view.buf);
  const std::string raw_sha =
      Sha256(std::span<const std::uint8_t>(bytes, kBytes));
  if (raw_sha != kExpectedRaw) {
    throw PanelIdentityError("registered NumPy panel raw SHA-256 mismatch");
  }
  if constexpr (std::endian::native != std::endian::little) {
    throw PanelIdentityError("verifier host is not little-endian");
  }
  InputPanel result;
  result.row_major_bits.resize(static_cast<std::size_t>(kRows) * kDimensions);
  std::memcpy(result.row_major_bits.data(), bytes, kBytes);
  result.raw_sha256 = raw_sha;
  result.python_version = python_version;
  result.numpy_version = numpy_version;
  return result;
}

std::string InputAuthorityManifestJson() {
  Interpreter interpreter;
  const std::string python_version = Py_GetVersion();
  if (python_version.rfind(kExpectedPythonPrefix, 0) != 0) {
    throw PanelIdentityError("CPython runtime is not exactly 3.9.25");
  }
  PyObject* numpy = PyImport_ImportModule("numpy");
  if (numpy == nullptr) PythonFailure("cannot import frozen NumPy authority");
  PyObject* version = PyObject_GetAttrString(numpy, "__version__");
  const std::string numpy_version = PythonString(version, "NumPy version");
  Py_XDECREF(version);
  if (numpy_version != kExpectedNumpy) {
    Py_DECREF(numpy);
    throw PanelIdentityError("NumPy runtime is not exactly 1.23.5");
  }
  ValidateNumpyOrigin(numpy);
  RejectRepositoryModuleImports();
  Py_DECREF(numpy);
  Json::Object manifest{
      {"artifact_kind", Json("a4_v2_verifier_source_manifest")},
      {"compile_flags", Json(A4_V2_VERIFIER_FLAGS)},
      {"compiler_id", Json("GCC")},
      {"compiler_version", Json(__VERSION__)},
      {"gmp_version", Json(gmp_version)},
      {"input_authority",
       Json(Json::Object{{"numpy", Json(numpy_version)},
                         {"python", Json("CPython 3.9.25")},
                         {"role", Json("registered-input-regeneration-only")}})},
      {"numpy_repo_imports", Json(false)},
      {"openssl_version", Json(OpenSSL_version(OPENSSL_VERSION))},
      {"parity_surfaces",
       Json(Json::Array{Json("par-scalar"), Json("par-block"),
                        Json("par-representation")})},
      {"producer_source_linked", Json(false)},
      {"schema_version", Json(std::int64_t{1})},
      {"solver",
       Json("V_replay:independent-divide-and-conquer-Monge-exact-DP;"
            "PAR-scalar:bounded-all-contiguous-partitions-exhaustive;"
            "PAR-block-axis:bounded-quadratic-exact-DP")}};
  return DumpJson(Json(std::move(manifest))) + "\n";
}

}  // namespace saq::a4_v2::verifier

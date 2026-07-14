cmake_minimum_required(VERSION 3.16)

project(SAQ_A4_V2_INDEPENDENT_VERIFIER LANGUAGES CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR
   NOT CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL "11.5.0")
  message(FATAL_ERROR
          "A4-V2 verifier requires exactly GCC 11.5.0; found "
          "${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
endif()
if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  message(FATAL_ERROR "A4-V2 verifier requires x86-64")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# The build command fixes Release and supplies no CXXFLAGS cache argument.
# Reject every ambient compile flag, not merely a blacklist: compile_commands
# is later sealed and independently checked against this exact closure.
if(NOT CMAKE_BUILD_TYPE STREQUAL "Release" OR
   NOT CMAKE_CXX_FLAGS STREQUAL "" OR
   NOT CMAKE_CXX_FLAGS_RELEASE STREQUAL "-O3 -DNDEBUG")
  message(FATAL_ERROR
          "A4-V2 verifier requires empty ambient CXX flags and the exact "
          "Release defaults; found global='${CMAKE_CXX_FLAGS}', "
          "release='${CMAKE_CXX_FLAGS_RELEASE}'")
endif()

find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED IMPORTED_TARGET gmp)
pkg_check_modules(GMPXX REQUIRED IMPORTED_TARGET gmpxx)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)
# The registered panel is defined by this exact external authority.  The
# verifier embeds it only to regenerate the immutable input; no repository
# Python module is imported and no producer checkpoint is read.
find_package(Python3 3.9.25 EXACT REQUIRED COMPONENTS Interpreter Development)

# Locate the registered system NumPy without importing it.  Both -I and -S
# are required: the query must ignore environment/user paths and must not run
# site initialization (including .pth files).  The resulting directory is
# appended explicitly to an isolated embedded interpreter below; arbitrary
# repository paths are never inherited through PYTHONPATH, cwd, or site.
execute_process(
  COMMAND
    "${Python3_EXECUTABLE}" -I -S -B -c
    "import os,sysconfig\nprint(os.path.realpath(sysconfig.get_path('purelib')))\nprint(os.path.realpath(sysconfig.get_path('platlib')))"
  RESULT_VARIABLE _a4_v2_sysconfig_status
  OUTPUT_VARIABLE _a4_v2_sysconfig_paths
  ERROR_VARIABLE _a4_v2_sysconfig_error
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT _a4_v2_sysconfig_status EQUAL 0)
  message(FATAL_ERROR
          "isolated CPython sysconfig query failed: "
          "${_a4_v2_sysconfig_error}")
endif()
string(REPLACE "\n" ";" _a4_v2_sysconfig_paths
       "${_a4_v2_sysconfig_paths}")
set(_a4_v2_numpy_site "")
foreach(_candidate IN LISTS _a4_v2_sysconfig_paths)
  if(IS_ABSOLUTE "${_candidate}" AND
     EXISTS "${_candidate}/numpy/__init__.py")
    get_filename_component(_candidate_real "${_candidate}" REALPATH)
    set(_a4_v2_numpy_site "${_candidate_real}")
    break()
  endif()
endforeach()
if(_a4_v2_numpy_site STREQUAL "")
  message(FATAL_ERROR
          "NumPy 1.23.5 is absent from the isolated CPython system paths")
endif()

get_filename_component(_a4_v2_python_executable
                       "${Python3_EXECUTABLE}" REALPATH)
get_filename_component(_a4_v2_repo_root
                       "${CMAKE_CURRENT_SOURCE_DIR}/../.." REALPATH)
get_filename_component(_a4_v2_numpy_package
                       "${_a4_v2_numpy_site}/numpy" REALPATH)
foreach(_authority_path
        "${_a4_v2_python_executable}"
        "${_a4_v2_numpy_site}"
        "${_a4_v2_numpy_package}")
  string(FIND "${_authority_path}/" "${_a4_v2_repo_root}/"
         _a4_v2_authority_in_repo)
  if(_a4_v2_authority_in_repo EQUAL 0)
    message(FATAL_ERROR
            "registered Python/NumPy authority resolves inside repository: "
            "${_authority_path}")
  endif()
  if(_authority_path MATCHES "[;\\\"\\\\]")
    message(FATAL_ERROR
            "registered Python/NumPy path cannot be represented safely: "
            "${_authority_path}")
  endif()
endforeach()

# Import only after the isolated system path has been selected and rejected as
# a repository path.  This configure-time check pins both the package version
# and the physical package origin used later by the embedded verifier.
execute_process(
  COMMAND
    "${_a4_v2_python_executable}" -I -S -B -c
    "import os,sys\nsys.path.append(sys.argv[1])\nimport numpy\nprint(numpy.__version__)\nprint(os.path.realpath(numpy.__file__))"
    "${_a4_v2_numpy_site}"
  RESULT_VARIABLE _a4_v2_numpy_status
  OUTPUT_VARIABLE _a4_v2_numpy_identity
  ERROR_VARIABLE _a4_v2_numpy_error
  OUTPUT_STRIP_TRAILING_WHITESPACE)
if(NOT _a4_v2_numpy_status EQUAL 0)
  message(FATAL_ERROR
          "isolated registered NumPy import failed: ${_a4_v2_numpy_error}")
endif()
string(REPLACE "\n" ";" _a4_v2_numpy_identity
       "${_a4_v2_numpy_identity}")
list(LENGTH _a4_v2_numpy_identity _a4_v2_numpy_identity_count)
if(NOT _a4_v2_numpy_identity_count EQUAL 2)
  message(FATAL_ERROR "registered NumPy identity output is malformed")
endif()
list(GET _a4_v2_numpy_identity 0 _a4_v2_numpy_version)
list(GET _a4_v2_numpy_identity 1 _a4_v2_numpy_origin)
get_filename_component(_a4_v2_expected_numpy_origin
                       "${_a4_v2_numpy_package}/__init__.py" REALPATH)
if(NOT _a4_v2_numpy_version STREQUAL "1.23.5" OR
   NOT _a4_v2_numpy_origin STREQUAL "${_a4_v2_expected_numpy_origin}")
  message(FATAL_ERROR
          "registered NumPy identity mismatch: version="
          "${_a4_v2_numpy_version}, origin=${_a4_v2_numpy_origin}")
endif()

# This inventory is intentionally disjoint from research/a4_v2.  Neither
# sources nor headers from the producer target are linked into this binary.
add_executable(
  a4_v2_native
  a4_v2_native.cpp
  exact_reference.cpp
  input_panel.cpp
  json_value.cpp
  parity_cli.cpp
  representation_parity.cpp
  replay.cpp
  sha256.cpp)

target_include_directories(a4_v2_native PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_options(
  a4_v2_native PRIVATE
  -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
  -Wall -Wextra -Wpedantic)
target_compile_definitions(
  a4_v2_native PRIVATE
  A4_V2_VERIFIER_FLAGS="-O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse"
  A4_V2_PYTHON_AUTHORITY="CPython 3.9.25"
  A4_V2_NUMPY_AUTHORITY="NumPy 1.23.5"
  A4_V2_PYTHON_EXECUTABLE="${_a4_v2_python_executable}"
  A4_V2_NUMPY_SITE_PACKAGES="${_a4_v2_numpy_site}"
  A4_V2_NUMPY_PACKAGE_DIR="${_a4_v2_numpy_package}"
  A4_V2_VERIFIER_REPO_ROOT="${_a4_v2_repo_root}")
target_link_libraries(
  a4_v2_native PRIVATE
  PkgConfig::GMPXX PkgConfig::GMP OpenSSL::Crypto Python3::Python)

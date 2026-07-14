cmake_minimum_required(VERSION 3.16)

project(SAQ_A4_V2_PRODUCER LANGUAGES CXX)

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR
   NOT CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL "11.5.0")
  message(FATAL_ERROR
          "A4-V2 producer requires exactly GCC 11.5.0; found "
          "${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
endif()

if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  message(FATAL_ERROR "A4-V2 producer requires x86-64 MXCSR semantics")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE STREQUAL "Release")
  message(FATAL_ERROR "A4-V2 producer requires exactly CMAKE_BUILD_TYPE=Release")
endif()

# Reject caller/environment flag injection instead of trying to blacklist a
# subset after the fact.  GCC's Release initializer is separately pinned; the
# scientific numeric options below have exactly one compiler-argv source each.
# The pinned Release initializer alone supplies -O3; the target supplies the
# other four options.  The runtime receipt combines those reviewed sources.
if(NOT CMAKE_CXX_FLAGS STREQUAL "")
  message(FATAL_ERROR
          "A4-V2 producer forbids ambient CMAKE_CXX_FLAGS: ${CMAKE_CXX_FLAGS}")
endif()
if(NOT CMAKE_CXX_FLAGS_RELEASE STREQUAL "-O3 -DNDEBUG")
  message(FATAL_ERROR
          "A4-V2 producer Release initializer changed: ${CMAKE_CXX_FLAGS_RELEASE}")
endif()
if(CMAKE_INTERPROCEDURAL_OPTIMIZATION OR
   CMAKE_INTERPROCEDURAL_OPTIMIZATION_RELEASE)
  message(FATAL_ERROR "A4-V2 producer forbids ambient interprocedural optimization")
endif()

set(_a4_v2_target_numeric_flags
    -fno-fast-math
    -ffp-contract=off
    -frounding-math
    -mfpmath=sse)
set(_a4_v2_numeric_flags -O3 ${_a4_v2_target_numeric_flags})
string(JOIN " " _a4_v2_numeric_flags_receipt ${_a4_v2_numeric_flags})

find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED IMPORTED_TARGET gmp)
pkg_check_modules(GMPXX REQUIRED IMPORTED_TARGET gmpxx)
pkg_check_modules(MPFR REQUIRED IMPORTED_TARGET mpfr)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)

# The explicit inventory is part of the reviewed source identity.  Do not use
# globbing and do not add a source from another worktree.
add_executable(
  a4_v2_native
  a4_v2_native.cpp
  block_vq.cpp
  exact_quantizer.cpp
  native_cli.cpp
  numeric_runtime.cpp
  representation.cpp)

target_include_directories(a4_v2_native PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_options(
  a4_v2_native PRIVATE
  ${_a4_v2_target_numeric_flags}
  -Wall -Wextra -Wpedantic)
target_compile_definitions(
  a4_v2_native PRIVATE
  A4_V2_FROZEN_COMPILE_FLAGS="${_a4_v2_numeric_flags_receipt}")
target_link_libraries(
  a4_v2_native PRIVATE
  PkgConfig::GMPXX PkgConfig::MPFR PkgConfig::GMP OpenSSL::Crypto)

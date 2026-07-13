cmake_minimum_required(VERSION 3.16)

project(SAQ_A4_1S LANGUAGES CXX)

if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  message(FATAL_ERROR
          "A4-1S requires the frozen GNU C++ compiler, not ${CMAKE_CXX_COMPILER_ID}")
endif()

if(NOT CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL "11.5.0")
  message(FATAL_ERROR
          "A4-1S requires GCC 11.5.0; found ${CMAKE_CXX_COMPILER_VERSION}")
endif()

if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  message(FATAL_ERROR
          "A4-1S requires x86-64 so that the frozen MXCSR contract is enforceable")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# The A4-1S numeric contract forbids inheriting the upstream SAQ Release flags
# (-Ofast and -march=native).  This is deliberately a standalone CMake project.
set(_a4_1s_all_cxx_flags "${CMAKE_CXX_FLAGS}")
foreach(_config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  string(APPEND _a4_1s_all_cxx_flags " ${CMAKE_CXX_FLAGS_${_config}}")
endforeach()

if(_a4_1s_all_cxx_flags MATCHES
   "(^|[ ;])(-Ofast|-ffast-math|-march(=[^ ;]+)?|-mtune=native)([ ;]|$)")
  message(FATAL_ERROR
          "A4-1S received a flag forbidden by the frozen numeric contract: ${_a4_1s_all_cxx_flags}")
endif()

find_package(PkgConfig REQUIRED)
pkg_check_modules(GMP REQUIRED IMPORTED_TARGET gmp)
pkg_check_modules(GMPXX REQUIRED IMPORTED_TARGET gmpxx)
pkg_check_modules(MPFR REQUIRED IMPORTED_TARGET mpfr)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)

add_executable(
  a4_1s_native
  block_cli.cpp
  block_vq.cpp
  exact_quantizer.cpp
  numeric_runtime.cpp
  representation.cpp
  representation_cli.cpp
  a4_1s_native.cpp)

target_include_directories(a4_1s_native PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")

target_compile_options(
  a4_1s_native
  PRIVATE
    -O3
    -fno-fast-math
    -ffp-contract=off
    -frounding-math
    -mfpmath=sse
    -Wall
    -Wextra
    -Wpedantic)

target_compile_definitions(
  a4_1s_native
  PRIVATE
    A4_1S_FROZEN_COMPILE_FLAGS="-O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse")

target_link_libraries(
  a4_1s_native
  PRIVATE
    PkgConfig::GMPXX
    PkgConfig::MPFR
    PkgConfig::GMP
    OpenSSL::Crypto)

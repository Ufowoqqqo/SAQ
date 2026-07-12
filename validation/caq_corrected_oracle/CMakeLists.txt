cmake_minimum_required(VERSION 3.16)

project(caq_corrected_oracle_validation LANGUAGES CXX)

option(CAQ_CORRECTED_ORACLE_ENABLE_ASAN "Build the validator with AddressSanitizer" OFF)

enable_testing()

find_package(OpenSSL REQUIRED)
find_package(ZLIB REQUIRED)

add_executable(
  caq_corrected_oracle_validation
  ../../src/caq_corrected_oracle_validation.cpp)
add_executable(
  caq_corrected_oracle_cost_study
  ../../src/caq_corrected_oracle_cost_study.cpp)
add_executable(
  caq_co0_v2_b0_rotation_inventory
  ../../src/caq_co0_v2_b0_rotation_inventory.cpp)
add_executable(
  caq_co0_v2_b1_synthetic_validation
  ../../src/caq_co0_v2_b1_synthetic_validation.cpp)
add_executable(
  caq_co0_v2_b1_runner
  ../../src/caq_co0_v2_b1_runner.cpp)
add_library(
  caq_co0_v2_frozen_rotation STATIC
  ../../src/caq_co0_v2_frozen_rotation.cpp)

function(configure_corrected_oracle_target target)
  target_compile_features(${target} PRIVATE cxx_std_20)
  target_include_directories(${target} PRIVATE ../../saqlib)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(
      ${target}
      PRIVATE -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off)
    if(CAQ_CORRECTED_ORACLE_ENABLE_ASAN)
      target_compile_options(
        ${target} PRIVATE -fsanitize=address -fno-omit-frame-pointer)
      target_link_options(${target} PRIVATE -fsanitize=address)
    endif()
  endif()
endfunction()

configure_corrected_oracle_target(caq_corrected_oracle_validation)
configure_corrected_oracle_target(caq_corrected_oracle_cost_study)
configure_corrected_oracle_target(caq_co0_v2_b0_rotation_inventory)
configure_corrected_oracle_target(caq_co0_v2_b1_synthetic_validation)
configure_corrected_oracle_target(caq_co0_v2_b1_runner)
configure_corrected_oracle_target(caq_co0_v2_frozen_rotation)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(
    caq_co0_v2_frozen_rotation
    PRIVATE -O3 -fno-fast-math -ffp-contract=off
    -mno-avx512f -mno-avx512dq -mno-avx512bw -mno-avx512vl
    -mno-avx2 -mno-avx -mno-fma)
  target_compile_definitions(caq_co0_v2_frozen_rotation PRIVATE NDEBUG)
endif()

target_compile_options(
  caq_co0_v2_b1_synthetic_validation
  PRIVATE -mavx2 -mfma -mavx512f -mavx512dq -mavx512bw -mavx512vl)
target_include_directories(
  caq_co0_v2_b1_synthetic_validation
  BEFORE PRIVATE stubs)
target_link_libraries(
  caq_co0_v2_b1_synthetic_validation
  PRIVATE caq_co0_v2_frozen_rotation OpenSSL::Crypto ZLIB::ZLIB)
target_compile_options(
  caq_co0_v2_b1_runner
  PRIVATE -mavx2 -mfma -mavx512f -mavx512dq -mavx512bw -mavx512vl)
target_include_directories(
  caq_co0_v2_b1_runner
  BEFORE PRIVATE stubs)
target_link_libraries(
  caq_co0_v2_b1_runner
  PRIVATE caq_co0_v2_frozen_rotation OpenSSL::Crypto ZLIB::ZLIB)

add_test(
  NAME caq_corrected_oracle_validation
  COMMAND caq_corrected_oracle_validation)
add_test(
  NAME caq_corrected_oracle_cost_study
  COMMAND caq_corrected_oracle_cost_study)
add_test(
  NAME caq_co0_v2_b1_synthetic_validation
  COMMAND caq_co0_v2_b1_synthetic_validation)
add_test(
  NAME caq_co0_v2_b1_runner_rejects_incomplete_cli
  COMMAND caq_co0_v2_b1_runner)
set_tests_properties(
  caq_co0_v2_b1_runner_rejects_incomplete_cli
  PROPERTIES WILL_FAIL TRUE)
if(CAQ_CORRECTED_ORACLE_ENABLE_ASAN)
  set_tests_properties(
    caq_corrected_oracle_validation caq_corrected_oracle_cost_study
    caq_co0_v2_b1_synthetic_validation
    PROPERTIES ENVIRONMENT "ASAN_OPTIONS=detect_leaks=0:halt_on_error=1")
endif()

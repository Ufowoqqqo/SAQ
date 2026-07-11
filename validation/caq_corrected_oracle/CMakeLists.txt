cmake_minimum_required(VERSION 3.16)

project(caq_corrected_oracle_validation LANGUAGES CXX)

option(CAQ_CORRECTED_ORACLE_ENABLE_ASAN "Build the validator with AddressSanitizer" OFF)

enable_testing()

add_executable(
  caq_corrected_oracle_validation
  ../../src/caq_corrected_oracle_validation.cpp)
add_executable(
  caq_corrected_oracle_cost_study
  ../../src/caq_corrected_oracle_cost_study.cpp)

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

add_test(
  NAME caq_corrected_oracle_validation
  COMMAND caq_corrected_oracle_validation)
add_test(
  NAME caq_corrected_oracle_cost_study
  COMMAND caq_corrected_oracle_cost_study)
if(CAQ_CORRECTED_ORACLE_ENABLE_ASAN)
  set_tests_properties(
    caq_corrected_oracle_validation caq_corrected_oracle_cost_study
    PROPERTIES ENVIRONMENT "ASAN_OPTIONS=detect_leaks=0:halt_on_error=1")
endif()

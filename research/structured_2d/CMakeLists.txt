cmake_minimum_required(VERSION 3.20)
project(structured_2d LANGUAGES CXX)

find_package(OpenSSL REQUIRED COMPONENTS Crypto)
find_package(OpenMP REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(FAISS_ENABLE_GPU OFF CACHE BOOL "" FORCE)
set(FAISS_ENABLE_PYTHON OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(FAISS_SOURCE_DIR
    ${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/faiss
    CACHE PATH "Pinned Faiss source directory")
add_subdirectory(${FAISS_SOURCE_DIR}
                 ${CMAKE_CURRENT_BINARY_DIR}/faiss-build EXCLUDE_FROM_ALL)

set(STRUCTURED_2D_FLAGS
  -O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
  -Wall -Wextra -Wpedantic)

set(SHARED_SOURCES
  model.cpp
  compact.cpp
  microbench.cpp
  ../a4_or_b/models.cpp
  ../a4_or_b/panel.cpp
  ../a4_or_c/core.cpp)

add_executable(structured_2d_model_test
  ${SHARED_SOURCES} model_test.cpp)
add_executable(structured_2d_full_index_test
  ${SHARED_SOURCES} full_index.cpp full_index_test.cpp)
add_executable(structured_2d_admission_test
  admission.cpp admission_test.cpp)
add_executable(structured_2d_dataset_io_test
  dataset_io.cpp dataset_io_test.cpp)
add_executable(structured_2d_bind_query_objects
  dataset_io.cpp bind_query_objects.cpp)
add_executable(structured_2d_common_test
  admission.cpp dataset_io.cpp common.cpp common_test.cpp)
add_executable(structured_2d_prepare_common
  admission.cpp dataset_io.cpp common.cpp prepare_common.cpp)
add_executable(structured_2d_faiss_pool_test
  dataset_io.cpp faiss_pool.cpp faiss_pool_test.cpp)
add_executable(structured_2d_build_faiss_arm
  dataset_io.cpp faiss_pool.cpp build_faiss_arm.cpp)
add_executable(structured_2d_prepare_head
  dataset_io.cpp prepare_head.cpp)
add_executable(structured_2d_build_s_arm
  ${SHARED_SOURCES}
  admission.cpp dataset_io.cpp full_index.cpp build_s_arm.cpp)
add_executable(structured_2d_build_dv_arms
  ../a4_or_b/models.cpp ../a4_or_b/panel.cpp ../a4_or_c/core.cpp
  admission.cpp dataset_io.cpp faiss_pool.cpp build_dv_arms.cpp)
add_executable(mixed_radix_build_a_arm
  ../a4_or_b/models.cpp ../a4_or_b/panel.cpp ../a4_or_c/core.cpp
  dataset_io.cpp
  ../mixed_radix_query/mixed_index.cpp
  ../mixed_radix_query/build_a_arm.cpp)
add_executable(mixed_radix_index_test
  ../a4_or_b/models.cpp ../a4_or_b/panel.cpp ../a4_or_c/core.cpp
  ../mixed_radix_query/mixed_index.cpp
  ../mixed_radix_query/mixed_index_test.cpp)
add_executable(mixed_radix_synthetic_witness
  ../a4_or_b/models.cpp ../a4_or_b/panel.cpp ../a4_or_c/core.cpp
  synthetic_timing.cpp
  ../mixed_radix_query/mixed_index.cpp
  ../mixed_radix_query/synthetic_witness.cpp)
add_executable(structured_2d_build_opq_arm
  dataset_io.cpp faiss_pool.cpp build_opq_arm.cpp)
add_executable(structured_2d_probe_opq_cost
  dataset_io.cpp probe_opq_cost.cpp)
add_executable(structured_2d_write_distributions
  admission.cpp dataset_io.cpp write_distributions.cpp)
add_executable(structured_2d_refresh_synthetic_preassignments
  admission.cpp dataset_io.cpp refresh_synthetic_preassignments.cpp)
add_executable(structured_2d_prepare_natural_schedule
  admission.cpp dataset_io.cpp prepare_natural_schedule.cpp)
add_executable(structured_2d_synthetic_timing_test
  synthetic_timing.cpp synthetic_timing_test.cpp)
add_executable(structured_2d_run_synthetic_timing
  ${SHARED_SOURCES}
  admission.cpp dataset_io.cpp full_index.cpp synthetic_timing.cpp
  run_synthetic_timing.cpp)
add_executable(structured_2d_inspect_opq inspect_opq.cpp)
add_executable(structured_2d_runner
  ${SHARED_SOURCES} runner.cpp)

foreach(target
    structured_2d_model_test
    structured_2d_full_index_test
    structured_2d_admission_test
    structured_2d_dataset_io_test
    structured_2d_bind_query_objects
    structured_2d_common_test
    structured_2d_prepare_common
    structured_2d_faiss_pool_test
    structured_2d_build_faiss_arm
    structured_2d_prepare_head
    structured_2d_build_s_arm
    structured_2d_build_dv_arms
    mixed_radix_build_a_arm
    mixed_radix_index_test
    mixed_radix_synthetic_witness
    structured_2d_build_opq_arm
    structured_2d_probe_opq_cost
    structured_2d_write_distributions
    structured_2d_refresh_synthetic_preassignments
    structured_2d_prepare_natural_schedule
    structured_2d_synthetic_timing_test
    structured_2d_run_synthetic_timing
    structured_2d_inspect_opq
    structured_2d_runner)
  target_include_directories(${target} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_b
    ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_c)
  target_compile_options(${target} PRIVATE ${STRUCTURED_2D_FLAGS})
  target_link_libraries(${target} PRIVATE faiss)
endforeach()

target_link_libraries(structured_2d_build_s_arm PRIVATE OpenSSL::Crypto)
target_link_libraries(structured_2d_build_dv_arms PRIVATE OpenSSL::Crypto)
target_link_libraries(mixed_radix_build_a_arm PRIVATE OpenSSL::Crypto)
target_link_libraries(
  structured_2d_run_synthetic_timing PRIVATE OpenMP::OpenMP_CXX)
target_link_libraries(
  mixed_radix_synthetic_witness PRIVATE OpenMP::OpenMP_CXX)

set(BUILD_TESTING ON CACHE BOOL "" FORCE)
enable_testing()
add_test(NAME structured_2d_model_test COMMAND structured_2d_model_test)
add_test(
  NAME structured_2d_full_index_test
  COMMAND structured_2d_full_index_test)
add_test(
  NAME structured_2d_admission_test
  COMMAND structured_2d_admission_test)
add_test(
  NAME structured_2d_dataset_io_test
  COMMAND structured_2d_dataset_io_test)
add_test(
  NAME structured_2d_common_test
  COMMAND structured_2d_common_test)
add_test(
  NAME structured_2d_faiss_pool_test
  COMMAND structured_2d_faiss_pool_test)
add_test(
  NAME structured_2d_synthetic_timing_test
  COMMAND structured_2d_synthetic_timing_test)
add_test(
  NAME mixed_radix_index_test
  COMMAND mixed_radix_index_test)

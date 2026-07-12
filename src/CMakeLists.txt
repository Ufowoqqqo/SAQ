set (CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/bin)

add_executable(create_index create_index.cpp)
target_link_libraries(create_index PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

add_executable(test_qps test_qps.cpp)
target_link_libraries(test_qps PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

# add_executable(test_qps_thread test_qps_thread.cpp)
# target_link_libraries(test_qps_thread PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

add_executable(test_relative_error test_relative_error.cpp)
target_link_libraries(test_relative_error PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

add_executable(compute_gt compute_gt.cpp)
target_link_libraries(compute_gt PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

add_executable(test_ivf test_ivf.cpp)
target_link_libraries(test_ivf PRIVATE glog::glog fmt::fmt ${GFLAGS_LIBRARIES})

add_executable(caq_corrected_oracle_validation caq_corrected_oracle_validation.cpp)
add_executable(caq_corrected_oracle_cost_study caq_corrected_oracle_cost_study.cpp)
add_executable(caq_co0_v2_b0_rotation_inventory caq_co0_v2_b0_rotation_inventory.cpp)
add_library(caq_co0_v2_frozen_rotation STATIC caq_co0_v2_frozen_rotation.cpp)
add_executable(caq_co0_v2_b1_synthetic_validation caq_co0_v2_b1_synthetic_validation.cpp)
target_link_libraries(
  caq_co0_v2_b1_synthetic_validation
  PRIVATE caq_co0_v2_frozen_rotation glog::glog ${GFLAGS_LIBRARIES} OpenSSL::Crypto ZLIB::ZLIB)
add_executable(caq_co0_v2_b1_runner caq_co0_v2_b1_runner.cpp)
target_link_libraries(
  caq_co0_v2_b1_runner
  PRIVATE caq_co0_v2_frozen_rotation glog::glog ${GFLAGS_LIBRARIES} OpenSSL::Crypto ZLIB::ZLIB)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(
    caq_corrected_oracle_validation PRIVATE -fno-fast-math -ffp-contract=off)
  target_compile_options(
    caq_corrected_oracle_cost_study PRIVATE -fno-fast-math -ffp-contract=off)
  target_compile_options(
    caq_co0_v2_b0_rotation_inventory PRIVATE -fno-fast-math -ffp-contract=off)
  target_compile_options(
    caq_co0_v2_frozen_rotation PRIVATE
    -O3 -fno-fast-math -ffp-contract=off
    -mno-avx512f -mno-avx512dq -mno-avx512bw -mno-avx512vl
    -mno-avx2 -mno-avx -mno-fma)
  target_compile_definitions(caq_co0_v2_frozen_rotation PRIVATE NDEBUG)
  target_compile_options(
    caq_co0_v2_b1_synthetic_validation PRIVATE -fno-fast-math -ffp-contract=off)
  target_compile_options(
    caq_co0_v2_b1_runner PRIVATE -fno-fast-math -ffp-contract=off)
endif()

cmake_minimum_required(VERSION 3.20)
project(saq_component_oracle LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(SAQ_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../..)
set(SAQ_DEPS_ROOT "" CACHE PATH "Optional prefix containing glog/fmt/gflags")
find_path(GLOG_INCLUDE_DIR glog/logging.h HINTS ${SAQ_DEPS_ROOT}/include REQUIRED)
find_path(FMT_INCLUDE_DIR fmt/core.h HINTS ${SAQ_DEPS_ROOT}/include REQUIRED)
find_path(GFLAGS_INCLUDE_DIR gflags/gflags.h HINTS ${SAQ_DEPS_ROOT}/include REQUIRED)
find_library(GLOG_LIBRARY glog HINTS ${SAQ_DEPS_ROOT}/lib64 REQUIRED)
find_library(FMT_LIBRARY fmt HINTS ${SAQ_DEPS_ROOT}/lib64 REQUIRED)
find_library(GFLAGS_LIBRARY gflags HINTS ${SAQ_DEPS_ROOT}/lib64 REQUIRED)
set(SAQ_ORACLE_FLAGS
    -O3 -march=native -mavx512f -mavx512dq -mavx512bw -mavx512vl
    -fno-fast-math -ffp-contract=off -Wall -Wextra -Wpedantic)

add_executable(saq_component_oracle runner.cpp)
add_executable(saq_component_oracle_test test.cpp)

foreach(target saq_component_oracle saq_component_oracle_test)
  target_include_directories(${target} PRIVATE
      ${SAQ_ROOT}/saqlib ${GLOG_INCLUDE_DIR} ${FMT_INCLUDE_DIR}
      ${GFLAGS_INCLUDE_DIR})
  target_compile_options(${target} PRIVATE ${SAQ_ORACLE_FLAGS})
  target_link_libraries(${target} PRIVATE
      ${GLOG_LIBRARY} ${FMT_LIBRARY} ${GFLAGS_LIBRARY})
endforeach()

enable_testing()
add_test(NAME saq_component_oracle_test COMMAND saq_component_oracle_test)

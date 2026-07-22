cmake_minimum_required(VERSION 3.20)
project(a4_or_c LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/faiss
                 ${CMAKE_CURRENT_BINARY_DIR}/faiss-build EXCLUDE_FROM_ALL)

add_executable(a4_or_c_tiny core.cpp tiny_tests.cpp tiny_main.cpp)
add_executable(a4_or_c_synthetic core.cpp synthetic.cpp synthetic_main.cpp)
target_include_directories(a4_or_c_tiny PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(a4_or_c_synthetic PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
set(A4_OR_C_FLAGS
  -O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
  -Wall -Wextra -Wpedantic)
target_compile_options(a4_or_c_tiny PRIVATE ${A4_OR_C_FLAGS})
target_compile_options(a4_or_c_synthetic PRIVATE ${A4_OR_C_FLAGS})
target_link_libraries(a4_or_c_tiny PRIVATE faiss)
target_link_libraries(a4_or_c_synthetic PRIVATE faiss)

enable_testing()
add_test(NAME a4_or_c_tiny COMMAND a4_or_c_tiny)

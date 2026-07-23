cmake_minimum_required(VERSION 3.20)
project(a4_or_b LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/faiss
                 ${CMAKE_CURRENT_BINARY_DIR}/faiss-build EXCLUDE_FROM_ALL)

set(A4_OR_B_FLAGS
  -O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
  -Wall -Wextra -Wpedantic)

add_executable(a4_or_b_panel_smoke panel.cpp panel_smoke.cpp)
add_executable(a4_or_b_models_test
  panel.cpp models.cpp ../a4_or_c/core.cpp models_test.cpp)
add_executable(a4_or_b_runner
  panel.cpp models.cpp ../a4_or_c/core.cpp runner.cpp)
target_include_directories(a4_or_b_panel_smoke PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(a4_or_b_models_test PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_c)
target_include_directories(a4_or_b_runner PRIVATE
                           ${CMAKE_CURRENT_SOURCE_DIR}
                           ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_c)
target_compile_options(a4_or_b_panel_smoke PRIVATE ${A4_OR_B_FLAGS})
target_compile_options(a4_or_b_models_test PRIVATE ${A4_OR_B_FLAGS})
target_compile_options(a4_or_b_runner PRIVATE ${A4_OR_B_FLAGS})
target_link_libraries(a4_or_b_models_test PRIVATE faiss)
target_link_libraries(a4_or_b_runner PRIVATE faiss)

enable_testing()
add_test(NAME a4_or_b_panel_self_test COMMAND a4_or_b_panel_smoke --self-test)
add_test(NAME a4_or_b_models_self_test COMMAND a4_or_b_models_test)

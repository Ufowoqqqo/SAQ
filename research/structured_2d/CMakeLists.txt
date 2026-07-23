cmake_minimum_required(VERSION 3.20)
project(structured_2d LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(FAISS_ENABLE_GPU OFF CACHE BOOL "" FORCE)
set(FAISS_ENABLE_PYTHON OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/faiss
                 ${CMAKE_CURRENT_BINARY_DIR}/faiss-build EXCLUDE_FROM_ALL)

set(STRUCTURED_2D_FLAGS
  -O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
  -Wall -Wextra -Wpedantic)

set(SHARED_SOURCES
  model.cpp
  ../a4_or_b/models.cpp
  ../a4_or_b/panel.cpp
  ../a4_or_c/core.cpp)

add_executable(structured_2d_model_test
  ${SHARED_SOURCES} model_test.cpp)
add_executable(structured_2d_runner
  ${SHARED_SOURCES} runner.cpp)

foreach(target structured_2d_model_test structured_2d_runner)
  target_include_directories(${target} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_b
    ${CMAKE_CURRENT_SOURCE_DIR}/../a4_or_c)
  target_compile_options(${target} PRIVATE ${STRUCTURED_2D_FLAGS})
  target_link_libraries(${target} PRIVATE faiss)
endforeach()

set(BUILD_TESTING ON CACHE BOOL "" FORCE)
enable_testing()
add_test(NAME structured_2d_model_test COMMAND structured_2d_model_test)

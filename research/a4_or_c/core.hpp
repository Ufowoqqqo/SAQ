#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace a4or {

struct Point {
    float value;
    std::uint64_t weight;
    std::uint32_t vector_id;
};

struct CurveEntry {
    double sse;
    std::vector<std::size_t> boundaries;
    std::vector<float> centers;
    bool ambiguity;
};

struct Allocation {
    std::size_t k1;
    std::size_t k2;
    std::size_t used_states;
    double sse;
};

struct ControlShape {
    int word_bits;
    std::size_t pq_m;
    std::size_t pq_dsub;
    std::size_t pq_ksub;
    std::size_t v_groups;
    std::size_t v_centers;
    int pq_seed;
};

std::uint64_t splitmix64(std::uint64_t x);
std::vector<float> synthetic_panel();
std::vector<Point> rank_histogram(const float* values, std::size_t n,
                                  std::size_t h);
std::vector<CurveEntry> scalar_curve(const std::vector<Point>& points,
                                     std::size_t max_k);
Allocation allocate_pair(const std::vector<CurveEntry>& first,
                         const std::vector<CurveEntry>& second, int word_bits,
                         bool dyadic);
std::uint32_t pack(std::size_t z1, std::size_t z2, std::size_t k1);
std::pair<std::size_t, std::size_t> unpack(std::uint32_t code,
                                           std::size_t k1, std::size_t k2);
double lookup_distance(std::uint32_t code, std::size_t k1, std::size_t k2,
                       const std::vector<float>& c1,
                       const std::vector<float>& c2, float q1, float q2);
ControlShape control_shape(int word_bits);
bool faiss_contract_smoke();
bool run_tiny_exact(std::string& failure, double& max_error,
                    std::size_t& passed, std::size_t& oracle_cleared);
bool run_representation_checks(std::string& failure,
                               std::size_t& roundtrips,
                               std::size_t& lookups);

}  // namespace a4or

#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace a4or {

struct SyntheticResult {
    bool passed = false;
    std::string failure;
    double eta = 0;
    double eta_limit = 0;
    bool sensitivity_same = true;
    bool near_tie_same = true;
    bool allocation_order_same = true;
    bool finite_nonnegative = true;
    bool p_shape_valid = true, v_shape_valid = true;
    std::size_t d_collisions = 0, a_collisions = 0;
    std::size_t p_collisions = 0, v_collisions = 0;
    std::size_t p_nsplit = 0, v_nsplit = 0;
    std::uint64_t shared_scalar_cpu_us = 0;
    std::uint64_t d_cpu_us = 0, a_cpu_us = 0;
    std::uint64_t p_cpu_us = 0, v_cpu_us = 0;
    std::uint64_t support_cpu_us = 0, wall_us = 0;
    std::uint64_t peak_rss_bytes = 0;
};

SyntheticResult run_synthetic_admission();

}  // namespace a4or

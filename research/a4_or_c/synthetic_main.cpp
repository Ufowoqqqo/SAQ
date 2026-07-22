#include "synthetic.hpp"

#include <iostream>

int main() {
    for (int repetition = 0; repetition < 4; ++repetition) {
        const a4or::SyntheticResult r = a4or::run_synthetic_admission();
        std::cout << (repetition == 0 ? "warmup" : "repetition") << '='
                  << repetition << " passed=" << r.passed
                  << " failure=" << (r.failure.empty() ? "none" : r.failure)
                  << " eta=" << r.eta << " eta_limit=" << r.eta_limit
                  << " sensitivity=" << r.sensitivity_same
                  << " near_tie=" << r.near_tie_same
                  << " finite=" << r.finite_nonnegative
                  << " allocation_order=" << r.allocation_order_same
                  << " shapes=" << r.p_shape_valid << ',' << r.v_shape_valid
                  << " collisions=" << r.d_collisions << ',' << r.a_collisions
                  << ',' << r.p_collisions << ',' << r.v_collisions
                  << " nsplit=" << r.p_nsplit << ',' << r.v_nsplit
                  << " cpu_us=" << r.shared_scalar_cpu_us << ',' << r.d_cpu_us
                  << ',' << r.a_cpu_us << ',' << r.p_cpu_us << ',' << r.v_cpu_us
                  << " support_cpu_us=" << r.support_cpu_us
                  << " wall_us=" << r.wall_us
                  << " peak_rss_bytes=" << r.peak_rss_bytes << '\n';
        if (!r.passed) return 2;
    }
    return 0;
}

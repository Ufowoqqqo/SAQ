#include "synthetic.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string_view>

namespace {

std::uint64_t median(std::array<std::uint64_t, 3> values) {
    std::sort(values.begin(), values.end());
    return values[1];
}

}  // namespace

int main() {
    std::array<a4or::SyntheticResult, 3> measured;
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
                  << " encoding=" << r.p_encoding_valid << ','
                  << r.v_encoding_valid
                  << " empty_centers=" << r.p_empty_centers << ','
                  << r.v_empty_centers
                  << " encoded_labels=" << r.p_encoded_labels << ','
                  << r.v_encoded_labels
                  << " collisions=" << r.d_collisions << ',' << r.a_collisions
                  << ',' << r.p_collisions << ',' << r.v_collisions
                  << " nsplit=" << r.p_nsplit << ',' << r.v_nsplit
                  << " cpu_us=" << r.shared_scalar_cpu_us << ',' << r.d_cpu_us
                  << ',' << r.a_cpu_us << ',' << r.p_cpu_us << ',' << r.v_cpu_us
                  << " support_cpu_us=" << r.support_cpu_us
                  << " wall_us=" << r.wall_us
                  << " peak_rss_bytes=" << r.peak_rss_bytes << '\n';
        if (!r.passed) return 2;
        if (repetition > 0) measured[repetition - 1] = r;
    }

    std::array<std::uint64_t, 3> t_da{}, support{}, scientific{}, a_specific{},
            shared_scalar{}, peak_rss{};
    for (std::size_t i = 0; i < measured.size(); ++i) {
        const auto& r = measured[i];
        t_da[i] = r.shared_scalar_cpu_us + r.d_cpu_us + r.a_cpu_us;
        support[i] = r.support_cpu_us;
        scientific[i] = t_da[i] + r.p_cpu_us + r.v_cpu_us;
        a_specific[i] = r.a_cpu_us;
        shared_scalar[i] = r.shared_scalar_cpu_us;
        peak_rss[i] = r.peak_rss_bytes;
    }
    const std::uint64_t median_t_da = median(t_da);
    const std::uint64_t median_support = median(support);
    const std::uint64_t median_scientific = median(scientific);
    const std::uint64_t median_a_specific = median(a_specific);
    const std::uint64_t median_shared_scalar = median(shared_scalar);
    const std::uint64_t max_peak_rss =
            *std::max_element(peak_rss.begin(), peak_rss.end());
    const std::uint64_t t_project = 2 * median_t_da;
    const double support_ratio =
            double(median_support) / double(median_scientific);
    const double a_specific_ratio =
            double(median_a_specific) / double(median_shared_scalar);
    const char* failure = "none";
    if (max_peak_rss > 17179869184ULL)
        failure = "rss";
    else if (support_ratio > 0.25)
        failure = "support_ratio";
    else if (t_project > 3600000000ULL)
        failure = "T_project";
    else if (a_specific_ratio > 0.25)
        failure = "A_specific_ratio";
    std::cout << "timing_passed=" << (failure == std::string_view{"none"})
              << " failure=" << failure
              << " median_T_DA_cpu_us=" << median_t_da
              << " T_project_cpu_us=" << t_project
              << " median_support_cpu_us=" << median_support
              << " median_scientific_cpu_us=" << median_scientific
              << " support_ratio=" << support_ratio
              << " median_A_specific_cpu_us=" << median_a_specific
              << " median_shared_scalar_cpu_us=" << median_shared_scalar
              << " A_specific_ratio=" << a_specific_ratio
              << " max_peak_rss_bytes=" << max_peak_rss << '\n';
    if (failure != std::string_view{"none"}) return 3;
    return 0;
}

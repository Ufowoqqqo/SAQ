#include "panel.hpp"

#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void self_test() {
    const std::vector<float> values{0.0F, -0.0F, 1.0F, -2.0F};
    a4orb::Panel panel;
    panel.fit = values;
    panel.heldout = values;
    panel.fit_rows = {{0, 1, 0, -1, a4orb::PairSide::None}};
    panel.heldout_rows = {{0, 2, 0, 0, a4orb::PairSide::Left},
                          {0, 3, 1, 0, a4orb::PairSide::Right}};
    if (!a4orb::finite_panel(panel))
        throw std::runtime_error("finite self test");
    const std::uint64_t first = a4orb::panel_fingerprint(panel);
    panel.heldout.back() = std::nextafter(panel.heldout.back(), 0.0F);
    if (first == a4orb::panel_fingerprint(panel))
        throw std::runtime_error("fingerprint self test");
}

std::size_t parse_size(const char* value) {
    std::size_t consumed = 0;
    const std::size_t result = std::stoull(value, &consumed);
    if (consumed != std::string(value).size())
        throw std::runtime_error("invalid numeric argument");
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            self_test();
            std::cout << "PASS panel_self_test\n";
            return 0;
        }
        if (argc != 7) {
            std::cerr << "usage: " << argv[0]
                      << " BASE CENTROIDS CLUSTER_IDS INVENTORY ROWS D\n";
            return 2;
        }
        if (std::fesetround(FE_TONEAREST) != 0)
            throw std::runtime_error("cannot set FE_TONEAREST");
        const a4orb::Panel panel = a4orb::load_panel(
                {argv[1], argv[2], argv[3], argv[4]},
                parse_size(argv[5]), parse_size(argv[6]));
        if (!a4orb::finite_panel(panel))
            throw std::runtime_error("nonfinite panel");
        const auto [fit_min, fit_max] =
                std::minmax_element(panel.fit.begin(), panel.fit.end());
        const auto [held_min, held_max] =
                std::minmax_element(panel.heldout.begin(), panel.heldout.end());
        std::cout << "PASS"
                  << " source_rows=" << panel.source_rows
                  << " source_dimensions=" << panel.source_dimensions
                  << " fit_rows=" << panel.fit_rows.size()
                  << " heldout_rows=" << panel.heldout_rows.size()
                  << " panel_dimensions=" << panel.coordinates.size()
                  << " eligible_cells=" << panel.eligible_cells
                  << " heldout_pairs=" << panel.heldout_pairs
                  << " fit_min=" << *fit_min << " fit_max=" << *fit_max
                  << " heldout_min=" << *held_min
                  << " heldout_max=" << *held_max
                  << " fingerprint=" << a4orb::panel_fingerprint(panel) << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

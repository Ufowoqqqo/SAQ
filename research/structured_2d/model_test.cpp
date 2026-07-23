#include "model.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void expansion_test() {
    std::vector<float> shape{0, 0, 1, 0, 0, 1, -1, -1};
    std::vector<structured2d::AffineGroup> groups(a4orb::kGroups);
    for (auto& group : groups) {
        group.mean[0] = 2;
        group.mean[1] = -3;
        group.transform[0] = 4;
        group.transform[1] = 1;
        group.transform[2] = 2;
        group.transform[3] = 5;
    }
    const auto expanded = structured2d::expand(2, shape, groups);
    require(expanded.arm == 'S', "arm");
    require(expanded.blocks.size() == a4orb::kGroups, "group count");
    const auto& values = expanded.blocks.front().values;
    require(values[2] == 6 && values[3] == -1, "first affine axis");
    require(values[4] == 3 && values[5] == 2, "second affine axis");

    structured2d::SharedAffineModel compact;
    compact.shape = shape;
    compact.groups = groups;
    compact.expanded = expanded;
    require(structured2d::persistent_model_bytes(compact) ==
                    (shape.size() + 6 * a4orb::kGroups) * sizeof(float),
            "compact bytes");
    require(structured2d::transient_expanded_bytes(compact) ==
                    2 * 4 * a4orb::kGroups * sizeof(float),
            "expanded bytes");
    require(structured2d::finite(compact), "finite");
}

void encoding_replay_test() {
    std::vector<float> shape{-1, -1, 1, -1, -1, 1, 1, 1};
    std::vector<structured2d::AffineGroup> groups(a4orb::kGroups);
    for (auto& group : groups) {
        group.transform[0] = 1;
        group.transform[3] = 1;
    }
    const auto model = structured2d::expand(2, shape, groups);
    std::vector<float> panel(
            a4orb::kRowsPerSplit * a4orb::kPanelDimensions);
    for (std::size_t row = 0; row < a4orb::kRowsPerSplit; ++row) {
        const float x = (row & 1) ? 1 : -1;
        const float y = (row & 2) ? 1 : -1;
        for (std::size_t group = 0; group < a4orb::kGroups; ++group) {
            panel[row * a4orb::kPanelDimensions + 2 * group] = x;
            panel[row * a4orb::kPanelDimensions + 2 * group + 1] = y;
        }
    }
    const auto evaluation = a4orb::evaluate(panel, model);
    require(evaluation.shape_valid, "shape validity");
    require(evaluation.encoding_valid, "encoding validity");
    require(evaluation.collisions == 0, "collisions");
    require(evaluation.empty_centers == 0, "occupancy");
    require(structured2d::pooled_occupancy_valid(model, evaluation),
            "pooled occupancy");
    require(evaluation.direct_sse == 0, "reconstruction");
    require(std::fabs(
                    evaluation.direct_sse - evaluation.sufficient_sse) <
                    1e-12,
            "replay");

    auto incomplete = evaluation;
    std::fill(incomplete.codes.begin(), incomplete.codes.end(), 0);
    require(!structured2d::pooled_occupancy_valid(model, incomplete),
            "pooled empty label detection");
}

void full_affine_refinement_test() {
    std::vector<float> shape{-1, -1, 1, -1, -1, 1, 1, 1};
    std::vector<structured2d::AffineGroup> initial(a4orb::kGroups);
    for (auto& group : initial) {
        group.transform[0] = 1;
        group.transform[3] = 1;
    }
    std::vector<float> fit(
            a4orb::kRowsPerSplit * a4orb::kPanelDimensions);
    for (std::size_t row = 0; row < a4orb::kRowsPerSplit; ++row) {
        const std::size_t label = row % 4;
        const double z0 = shape[2 * label];
        const double z1 = shape[2 * label + 1];
        for (std::size_t group = 0; group < a4orb::kGroups; ++group) {
            fit[row * a4orb::kPanelDimensions + 2 * group] =
                    static_cast<float>(
                            0.25 + 1.1 * z0 + 0.3 * z1);
            fit[row * a4orb::kPanelDimensions + 2 * group + 1] =
                    static_cast<float>(
                            -0.4 - 0.2 * z0 + 0.9 * z1);
        }
    }
    structured2d::SharedAffineModel model;
    model.word_bits = 2;
    model.shape = shape;
    model.groups = initial;
    model.expanded = structured2d::expand(2, shape, initial);
    const double before = a4orb::evaluate(fit, model.expanded).direct_sse;
    structured2d::refine(fit, model, 3);
    const double after = a4orb::evaluate(fit, model.expanded).direct_sse;
    require(model.refinement_iterations > 0, "refinement iteration");
    require(after < 1e-8 * before, "affine refinement objective");
    require(std::fabs(model.groups[0].transform[1]) > 0.1,
            "full affine upper-right coefficient");
}

}  // namespace

int main() {
    try {
        expansion_test();
        encoding_replay_test();
        full_affine_refinement_test();
        std::cout << "PASS structured_2d_model_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

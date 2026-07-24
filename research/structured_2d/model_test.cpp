#include "model.hpp"
#include "compact.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void expansion_test() {
    static_assert(structured2d::kSensitivityIterations == 20);
    static_assert(structured2d::kFixedBudgetIterations == 100);
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
    structured2d::refine(fit, model, 6, 1e-8, 2);
    const double after = a4orb::evaluate(fit, model.expanded).direct_sse;
    require(model.refinement_iterations > 0, "refinement iteration");
    require(after < 1e-8 * before, "affine refinement objective");
    require(std::fabs(model.groups[0].transform[1]) > 0.1,
            "full affine upper-right coefficient");
    require(model.converged, "fit-only convergence");
    require(structured2d::fixed_budget_complete(model, 6),
            "early fixed-point budget completion");
    require(model.fit_trace.size() ==
                    model.refinement_iterations + 1,
            "trace length");
    for (std::size_t step = 1; step < model.fit_trace.size(); ++step)
        require(model.fit_trace[step].fit_sse <=
                        model.fit_trace[step - 1].fit_sse,
                "monotone trace");
}

void fixed_budget_status_test() {
    structured2d::SharedAffineModel model;
    model.refinement_iterations =
            structured2d::kFixedBudgetIterations;
    require(structured2d::fixed_budget_complete(model),
            "full fixed budget");
    model.refinement_iterations =
            structured2d::kSensitivityIterations;
    require(!structured2d::fixed_budget_complete(model),
            "incomplete primary budget");
    model.converged = true;
    model.fit_trace.push_back({20, 1.0, 1e-8});
    require(!structured2d::fixed_budget_complete(model),
            "loose convergence is not a fixed-budget stop");
    model.refinement_iterations =
            structured2d::kFixedBudgetIterations;
    model.converged = false;
    model.stopped_nonmonotonic = true;
    require(!structured2d::fixed_budget_complete(model),
            "non-monotonic stop");
}

a4orb::Panel make_compact_panel() {
    a4orb::Panel panel;
    panel.fit.resize(
            a4orb::kRowsPerSplit * a4orb::kPanelDimensions);
    panel.heldout.resize(panel.fit.size());
    panel.fit_rows.resize(a4orb::kRowsPerSplit);
    panel.heldout_rows.resize(a4orb::kRowsPerSplit);
    panel.heldout_pairs = a4orb::kRowsPerSplit / 2;
    for (std::size_t row = 0; row < a4orb::kRowsPerSplit; ++row) {
        const float x = (row & 1) ? 1 : -1;
        const float y = (row & 2) ? 1 : -1;
        for (std::size_t group = 0; group < a4orb::kGroups; ++group) {
            const std::size_t at =
                    row * a4orb::kPanelDimensions + 2 * group;
            panel.fit[at] = panel.heldout[at] = x;
            panel.fit[at + 1] = panel.heldout[at + 1] = y;
        }
        panel.heldout_rows[row] = {
                0, static_cast<std::uint32_t>(row),
                static_cast<std::uint32_t>(row),
                static_cast<std::int32_t>(row / 2),
                (row & 1) ? a4orb::PairSide::Right
                          : a4orb::PairSide::Left};
    }
    return panel;
}

void compact_equivalence_test() {
    structured2d::SharedAffineModel model;
    model.word_bits = 2;
    model.shape = {-1, -1, 1, -1, -1, 1, 1, 1};
    model.groups.resize(a4orb::kGroups);
    for (auto& group : model.groups) {
        group.transform[0] = 1;
        group.transform[3] = 1;
    }
    model.expanded =
            structured2d::expand(2, model.shape, model.groups);
    const auto panel = make_compact_panel();
    const auto fit = a4orb::evaluate(panel.fit, model.expanded);
    const auto heldout =
            a4orb::evaluate(panel.heldout, model.expanded);
    const auto pairs =
            a4orb::evaluate_pairs(panel, model.expanded, heldout);
    const auto check = structured2d::check_compact(
            panel, model, fit, heldout, pairs);
    require(structured2d::valid(check, pairs), "compact equivalence");
    require(check.peak_table_bytes == 4 * sizeof(float),
            "one-table memory");
    std::vector<float> compact_table(4), expanded_table(4);
    structured2d::build_compact_table(
            panel.fit.data(), model, 0, compact_table);
    structured2d::build_expanded_table(
            panel.fit.data(), model.expanded.blocks[0], expanded_table);
    for (std::size_t label = 0; label < compact_table.size(); ++label)
        require(
                std::fabs(compact_table[label] - expanded_table[label]) <=
                        structured2d::table_entry_tolerance(
                                expanded_table[label]),
                "public native table builders");

    // The reference is deliberately inconsistent with the compact state.
    // The tolerance checker must detect this instead of silently blessing a
    // candidate merely because its encoding labels happen to remain stable.
    auto perturbed = model;
    perturbed.expanded.blocks[0].values[0] += 0.25F;
    const auto bad_fit =
            a4orb::evaluate(panel.fit, perturbed.expanded);
    const auto bad_heldout =
            a4orb::evaluate(panel.heldout, perturbed.expanded);
    const auto bad_pairs = a4orb::evaluate_pairs(
            panel, perturbed.expanded, bad_heldout);
    const auto bad_check = structured2d::check_compact(
            panel, perturbed, bad_fit, bad_heldout, bad_pairs);
    require(bad_check.table_tolerance_violations > 0,
            "compact tolerance enforcement");
    require(!structured2d::valid(bad_check, bad_pairs),
            "compact invalid reference");
}

}  // namespace

int main() {
    try {
        expansion_test();
        encoding_replay_test();
        full_affine_refinement_test();
        fixed_budget_status_test();
        compact_equivalence_test();
        std::cout << "PASS structured_2d_model_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

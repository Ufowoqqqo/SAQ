#include "model.hpp"
#include "compact.hpp"
#include "microbench.hpp"

#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
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

structured2d::SharedAffineModel make_parity_model(int word_bits) {
    const std::size_t centers = std::size_t{1} << word_bits;
    structured2d::SharedAffineModel model;
    model.word_bits = word_bits;
    model.shape.resize(2 * centers);
    for (std::size_t label = 0; label < centers; ++label) {
        model.shape[2 * label] =
                (static_cast<float>(label) -
                 static_cast<float>(centers) / 2) /
                static_cast<float>(centers);
        model.shape[2 * label + 1] =
                (static_cast<float>((29 * label) % centers) -
                 static_cast<float>(centers) / 2) /
                static_cast<float>(centers);
    }
    model.shape[0] = std::numeric_limits<float>::quiet_NaN();
    model.shape[2] = std::numeric_limits<float>::infinity();
    model.shape[4] = -std::numeric_limits<float>::infinity();
    model.shape[6] = std::numeric_limits<float>::denorm_min();
    model.shape[7] = -std::numeric_limits<float>::denorm_min();
    model.shape[8] = -0.0F;
    model.shape[9] = 0.0F;
    model.shape[10] = std::numeric_limits<float>::max() / 4;
    model.shape[11] = -std::numeric_limits<float>::max() / 4;

    model.groups.resize(a4orb::kGroups);
    for (std::size_t group = 0; group < model.groups.size(); ++group) {
        auto& affine = model.groups[group];
        affine.mean[0] = 0.001F * static_cast<float>(group);
        affine.mean[1] = -0.002F * static_cast<float>(group);
        affine.transform[0] = 0.8F + 0.001F * group;
        affine.transform[1] = 0.13F;
        affine.transform[2] = -0.07F;
        affine.transform[3] = 1.1F - 0.001F * group;
    }
    return model;
}

void sse2_scalar_parity_test() {
    const int original_rounding = std::fegetround();
    bool all_equal = true;
    const std::array<int, 4> roundings{
            FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO};
    const std::array<std::array<float, 2>, 3> queries{{
            {0.125F, -0.875F},
            {-0.0F, 0.0F},
            {std::numeric_limits<float>::quiet_NaN(), 1.0F}}};

    for (const int rounding : roundings) {
        require(std::fesetround(rounding) == 0, "set rounding mode");
        for (const int bits : {4, 8}) {
            const auto model = make_parity_model(bits);
            const std::size_t centers = std::size_t{1} << bits;
            std::vector<float> actual(centers), reference(centers);
            for (const std::size_t group :
                 {std::size_t{0}, std::size_t{7}, std::size_t{63}}) {
                for (const auto& query : queries) {
                    structured2d::build_compact_table(
                            query.data(), model, group, actual);
                    structured2d::build_compact_table_scalar_reference(
                            query.data(), model, group, reference);
                    for (std::size_t label = 0;
                         label < centers; ++label)
                        all_equal = all_equal &&
                                std::bit_cast<std::uint32_t>(
                                        actual[label]) ==
                                std::bit_cast<std::uint32_t>(
                                        reference[label]);
                }
            }
        }
    }
    require(std::fesetround(original_rounding) == 0,
            "restore rounding mode");
    require(all_equal, "SSE2/scalar bitwise parity");

    // Exercise the scalar tail independently of the even B4/B8 codebooks.
    auto odd = make_parity_model(4);
    odd.shape.resize(10);
    std::vector<float> actual(5), reference(5);
    const std::array<float, 2> query{0.25F, -0.5F};
    structured2d::build_compact_table(
            query.data(), odd, 0, actual);
    structured2d::build_compact_table_scalar_reference(
            query.data(), odd, 0, reference);
    require(actual == reference, "SSE2 scalar tail");
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

void packed_consumer_test() {
    for (const int bits : {4, 8}) {
        const std::size_t centers = std::size_t{1} << bits;
        constexpr std::size_t candidates = 5;
        std::vector<std::uint16_t> labels(
                candidates * a4orb::kGroups);
        for (std::size_t candidate = 0;
             candidate < candidates; ++candidate) {
            for (std::size_t group = 0;
                 group < a4orb::kGroups; ++group) {
                // Mix ordinary modular labels with boundary-heavy rows.
                const std::size_t selector = candidate % 3;
                labels[candidate * a4orb::kGroups + group] =
                        selector == 0 ? (7 * group + candidate) % centers
                        : selector == 1 ? (group & 1U ? centers - 1 : 0)
                                        : centers - 1 - (group % centers);
            }
        }

        const auto payload =
                structured2d::pack_labels(labels, bits);
        require(payload.size() ==
                        candidates *
                        structured2d::payload_bytes_per_candidate(bits),
                "packed payload bytes");
        for (std::size_t candidate = 0;
             candidate < candidates; ++candidate)
            for (std::size_t group = 0;
                 group < a4orb::kGroups; ++group)
                require(
                        structured2d::decode_label(
                                payload, bits, candidate, group) ==
                                labels[candidate * a4orb::kGroups + group],
                        "packed roundtrip");
        if (bits == 4)
            require(
                    payload[0] ==
                            static_cast<std::uint8_t>(
                                    labels[0] | (labels[1] << 4)),
                    "B4 low-nibble-first");

        std::vector<float> expanded(
                a4orb::kGroups * centers);
        for (std::size_t group = 0;
             group < a4orb::kGroups; ++group)
            for (std::size_t label = 0; label < centers; ++label)
                expanded[group * centers + label] =
                        static_cast<float>(group * 0.25 + label * 0.5);
        auto compact = expanded;
        for (float& value : compact)
            value = std::nextafter(
                    value, std::numeric_limits<float>::infinity());
        const double compact_sum = structured2d::scan_packed_tables(
                compact, payload, bits, candidates);
        const double expanded_sum = structured2d::scan_packed_tables(
                expanded, payload, bits, candidates);
        double direct_sum = 0;
        for (std::size_t candidate = 0;
             candidate < candidates; ++candidate) {
            double estimate = 0;
            for (std::size_t group = 0;
                 group < a4orb::kGroups; ++group)
                estimate += expanded[
                        group * centers +
                        labels[candidate * a4orb::kGroups + group]];
            direct_sum += estimate;
        }
        double selected_tolerance = 0;
        for (std::size_t candidate = 0;
             candidate < candidates; ++candidate)
            for (std::size_t group = 0;
                 group < a4orb::kGroups; ++group)
                selected_tolerance +=
                        structured2d::table_entry_tolerance(
                                expanded[
                                        group * centers +
                                        labels[candidate *
                                                       a4orb::kGroups +
                                               group]]);
        require(std::fabs(compact_sum - expanded_sum) <=
                        selected_tolerance,
                "compact/expanded selected-entry tolerance");
        require(expanded_sum == direct_sum,
                "packed/direct accumulation parity");

        bool rejected = false;
        auto invalid = labels;
        invalid.front() = static_cast<std::uint16_t>(centers);
        try {
            (void)structured2d::pack_labels(invalid, bits);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "invalid packed label rejection");

        rejected = false;
        try {
            (void)structured2d::decode_label(
                    payload, bits, candidates, 0);
        } catch (const std::out_of_range&) {
            rejected = true;
        }
        require(rejected, "packed decode bounds");

        rejected = false;
        try {
            (void)structured2d::scan_packed_tables(
                    expanded,
                    std::span<const std::uint8_t>(
                            payload.data(), payload.size() - 1),
                    bits, candidates);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "truncated packed scan rejection");
    }
}

void integration_policy_test() {
    require(structured2d::kCandidateCounts ==
                    std::array<std::size_t, 4>{
                            64, 256, 1024, 8192},
            "fixed candidate counts");
    const std::array<std::array<char, 3>, 3> rotations{{
            {'C', 'E', 'V'}, {'E', 'V', 'C'}, {'V', 'C', 'E'}}};
    for (std::size_t repetition = 0;
         repetition < structured2d::kMicrobenchmarkRepetitions;
         ++repetition)
        require(
                structured2d::measurement_arm_order(repetition) ==
                        rotations[repetition % rotations.size()],
                "fixed arm rotation");

    for (const int bits : {0, 3, 5, 9}) {
        require(!structured2d::supported_word_bits(bits),
                "illegal bits unsupported");
        const std::vector<std::uint16_t> labels(a4orb::kGroups);
        std::size_t rejected = 0;
        try {
            (void)structured2d::payload_bytes_per_candidate(bits);
        } catch (const std::invalid_argument&) {
            ++rejected;
        }
        try {
            (void)structured2d::pack_labels(labels, bits);
        } catch (const std::invalid_argument&) {
            ++rejected;
        }
        try {
            (void)structured2d::decode_label({}, bits, 0, 0);
        } catch (const std::invalid_argument&) {
            ++rejected;
        }
        try {
            (void)structured2d::scan_packed_tables({}, {}, bits, 0);
        } catch (const std::invalid_argument&) {
            ++rejected;
        }
        require(rejected == 4, "illegal bits rejected before shifts");
    }

    const auto affordable = structured2d::evaluate_affordability(
            8192, 10, 10, 1, 1, 10, 10, 1, 1);
    require(affordable.pass, "CPU/wall affordability pass");
    const auto cpu_fail = structured2d::evaluate_affordability(
            8192, 10, 10, 1.11, 1, 10, 10, 1, 1);
    require(!cpu_fail.pass, "CPU scan affordability enforced");
    bool rejected = false;
    try {
        (void)structured2d::evaluate_affordability(
                8192, 10, 10, 1, 1, 10, 10, 0, 1);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, "affordability denominator guard");

    structured2d::NativeBenchmark admission;
    admission.word_bits = 4;
    admission.shared_codes_reused = true;
    admission.payload_bytes = 32;
    admission.expanded_direct_match = true;
    structured2d::require_native_timing_admission(admission);
    auto parity_failure = admission;
    parity_failure.compact_table_violations = 1;
    rejected = false;
    try {
        structured2d::require_native_timing_admission(parity_failure);
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    require(rejected && parity_failure.timings.empty(),
            "parity failure rejected before timing");
}

}  // namespace

int main() {
    try {
        expansion_test();
        encoding_replay_test();
        full_affine_refinement_test();
        fixed_budget_status_test();
        sse2_scalar_parity_test();
        compact_equivalence_test();
        packed_consumer_test();
        integration_policy_test();
        std::cout << "PASS structured_2d_model_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

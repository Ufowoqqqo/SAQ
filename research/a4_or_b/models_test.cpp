#include "models.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

int main() {
    try {
        if (!a4or::faiss_contract_smoke())
            throw std::runtime_error("floating-point/Faiss contract");
        a4orb::Panel panel;
        panel.fit.assign(
                a4orb::kRowsPerSplit * a4orb::kPanelDimensions, 0.0F);
        panel.heldout = panel.fit;
        panel.fit_rows.reserve(a4orb::kRowsPerSplit);
        panel.heldout_rows.reserve(a4orb::kRowsPerSplit);
        for (std::size_t row = 0; row < a4orb::kRowsPerSplit; ++row) {
            panel.fit_rows.push_back(
                    {0, static_cast<std::uint32_t>(row),
                     static_cast<std::uint32_t>(row), -1,
                     a4orb::PairSide::None});
            panel.heldout_rows.push_back(
                    {0, static_cast<std::uint32_t>(row),
                     static_cast<std::uint32_t>(row),
                     static_cast<std::int32_t>(row / 2),
                     row % 2 == 0 ? a4orb::PairSide::Left
                                  : a4orb::PairSide::Right});
        }
        panel.heldout_pairs = a4orb::kRowsPerSplit / 2;

        a4orb::Model model;
        model.arm = 'A';
        model.word_bits = 4;
        for (std::size_t group = 0; group < a4orb::kGroups; ++group)
            model.blocks.push_back({2, 1, 1, {0.0F, 0.0F}, false});
        const auto evaluation = a4orb::evaluate(panel.heldout, model);
        if (!evaluation.shape_valid || !evaluation.encoding_valid ||
            evaluation.direct_sse != 0 || evaluation.sufficient_sse != 0 ||
            evaluation.encoded_labels !=
                    a4orb::kRowsPerSplit * a4orb::kGroups ||
            evaluation.empty_centers != 0 || evaluation.collisions != 0)
            throw std::runtime_error("zero-model evaluation");
        const auto pairs =
                a4orb::evaluate_pairs(panel, model, evaluation);
        if (pairs.absolute_errors.size() != panel.heldout_pairs ||
            !std::all_of(pairs.absolute_errors.begin(),
                         pairs.absolute_errors.end(),
                         [](double value) { return value == 0; }))
            throw std::runtime_error("zero-model pair evaluation");
        if (a4orb::persistent_model_bytes(model) !=
            a4orb::kGroups * (2 * sizeof(float) +
                              2 * sizeof(std::uint16_t)))
            throw std::runtime_error("product model byte count");
        std::cout << "PASS models_self_test\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

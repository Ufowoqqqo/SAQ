#pragma once

#include "model.hpp"

#include "../a4_or_b/panel.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace structured2d {

struct CompactCheck {
    std::size_t fit_encoding_mismatches = 0;
    std::size_t heldout_encoding_mismatches = 0;
    std::size_t table_tolerance_violations = 0;
    std::size_t pair_tolerance_violations = 0;
    std::uint64_t table_entries_built = 0;
    std::size_t peak_table_bytes = 0;
    double max_table_absolute_difference = 0;
    double max_pair_absolute_error_difference = 0;
    std::vector<double> absolute_errors;
};

CompactCheck check_compact(
        const a4orb::Panel& panel,
        const SharedAffineModel& model,
        const a4orb::Evaluation& fit_reference,
        const a4orb::Evaluation& heldout_reference,
        const a4orb::PairEvaluation& pair_reference);

bool valid(const CompactCheck& check,
           const a4orb::PairEvaluation& pair_reference);

}  // namespace structured2d

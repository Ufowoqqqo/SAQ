#include "compact.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace structured2d {
namespace {

constexpr std::size_t kRows = a4orb::kRowsPerSplit;
constexpr std::size_t kGroups = a4orb::kGroups;
constexpr std::size_t kDimensions = a4orb::kPanelDimensions;

struct Sum {
    double value = 0;
    double correction = 0;

    void add(double term) {
        const double next = value + term;
        if (std::fabs(value) >= std::fabs(term))
            correction += (value - next) + term;
        else
            correction += (term - next) + value;
        value = next;
    }

    double get() const { return value + correction; }
};

float center_coordinate(const SharedAffineModel& model, std::size_t group,
                        std::size_t label, std::size_t coordinate) {
    const auto& affine = model.groups[group];
    const double z0 = model.shape[2 * label];
    const double z1 = model.shape[2 * label + 1];
    if (coordinate == 0)
        return static_cast<float>(
                affine.mean[0] + affine.transform[0] * z0 +
                affine.transform[1] * z1);
    return static_cast<float>(
            affine.mean[1] + affine.transform[2] * z0 +
            affine.transform[3] * z1);
}

std::size_t compact_label(const float* point,
                          const SharedAffineModel& model,
                          std::size_t group) {
    const std::size_t centers = model.shape.size() / 2;
    double best = std::numeric_limits<double>::infinity();
    std::size_t selected = 0;
    for (std::size_t label = 0; label < centers; ++label) {
        // Recreate one binary32 center at a time. This is exactly the center
        // rounding used by expand(), but never materializes 64*K centers.
        const double delta0 =
                static_cast<double>(point[0]) -
                center_coordinate(model, group, label, 0);
        const double delta1 =
                static_cast<double>(point[1]) -
                center_coordinate(model, group, label, 1);
        const double distance =
                delta0 * delta0 + delta1 * delta1;
        if (distance < best) best = distance, selected = label;
    }
    return selected;
}

std::size_t encoding_mismatches(
        const std::vector<float>& panel,
        const SharedAffineModel& model,
        const a4orb::Evaluation& reference,
        std::vector<std::uint16_t>* codes) {
    if (reference.codes.size() != kRows * kGroups)
        throw std::invalid_argument("reference code shape");
    if (codes != nullptr) codes->resize(kRows * kGroups);
    std::size_t mismatches = 0;
    for (std::size_t row = 0; row < kRows; ++row) {
        for (std::size_t group = 0; group < kGroups; ++group) {
            const float* point =
                    panel.data() + row * kDimensions + 2 * group;
            const std::size_t label =
                    compact_label(point, model, group);
            mismatches += label != reference.codes[row * kGroups + group];
            if (codes != nullptr)
                (*codes)[row * kGroups + group] =
                        static_cast<std::uint16_t>(label);
        }
    }
    return mismatches;
}

float reference_distance(const float* query, const a4orb::Block& block,
                         std::size_t label) {
    const double delta0 =
            static_cast<double>(query[0]) - block.values[2 * label];
    const double delta1 =
            static_cast<double>(query[1]) - block.values[2 * label + 1];
    return static_cast<float>(
            delta0 * delta0 + delta1 * delta1);
}

struct TableTerms {
    double constant = 0;
    double h0 = 0;
    double h1 = 0;
    double m00 = 0;
    double m01 = 0;
    double m11 = 0;
};

TableTerms table_terms(const float* query,
                       const SharedAffineModel& model,
                       std::size_t group) {
    const auto& affine = model.groups[group];
    const double u0 = static_cast<double>(query[0]) - affine.mean[0];
    const double u1 = static_cast<double>(query[1]) - affine.mean[1];
    const double a00 = affine.transform[0];
    const double a01 = affine.transform[1];
    const double a10 = affine.transform[2];
    const double a11 = affine.transform[3];

    // ||u-Az||^2 = ||u||^2 - 2 z^T A^T u + z^T A^T A z.
    // These six terms are constant for all K entries in one group/query table.
    return {
            u0 * u0 + u1 * u1,
            a00 * u0 + a10 * u1,
            a01 * u0 + a11 * u1,
            a00 * a00 + a10 * a10,
            a00 * a01 + a10 * a11,
            a01 * a01 + a11 * a11};
}

float compact_distance(const TableTerms& terms,
                       const SharedAffineModel& model,
                       std::size_t label) {
    const double z0 = model.shape[2 * label];
    const double z1 = model.shape[2 * label + 1];
    const double value =
            terms.constant -
            2 * (z0 * terms.h0 + z1 * terms.h1) +
            z0 * z0 * terms.m00 +
            2 * z0 * z1 * terms.m01 +
            z1 * z1 * terms.m11;
    // The mathematical value is nonnegative; clamp only cancellation-sized
    // negative roundoff before converting the table entry to binary32.
    return static_cast<float>(std::max(0.0, value));
}

double entry_tolerance(float reference) {
    return 8 * std::numeric_limits<float>::epsilon() *
            std::max(1.0, std::fabs(static_cast<double>(reference)));
}

}  // namespace

CompactCheck check_compact(
        const a4orb::Panel& panel,
        const SharedAffineModel& model,
        const a4orb::Evaluation& fit_reference,
        const a4orb::Evaluation& heldout_reference,
        const a4orb::PairEvaluation& pair_reference) {
    if (model.groups.size() != kGroups ||
        model.expanded.blocks.size() != kGroups ||
        model.shape.empty() || model.shape.size() % 2 != 0)
        throw std::invalid_argument("compact model shape");
    const std::size_t centers = model.shape.size() / 2;

    CompactCheck result;
    result.fit_encoding_mismatches =
            encoding_mismatches(
                    panel.fit, model, fit_reference, nullptr);
    std::vector<std::uint16_t> heldout_codes;
    result.heldout_encoding_mismatches =
            encoding_mismatches(
                    panel.heldout, model, heldout_reference,
                    &heldout_codes);
    result.peak_table_bytes = centers * sizeof(float);
    result.absolute_errors.reserve(panel.heldout_pairs);

    std::vector<float> table(centers);
    std::size_t pair = 0;
    for (std::size_t left = 0; left < panel.heldout_rows.size(); ++left) {
        if (panel.heldout_rows[left].pair_side !=
            a4orb::PairSide::Left)
            continue;
        const std::size_t right = left + 1;
        Sum truth;
        Sum estimate;
        double lookup_tolerance = 0;
        for (std::size_t group = 0; group < kGroups; ++group) {
            const float* query = panel.heldout.data() +
                    right * kDimensions + 2 * group;
            const TableTerms terms =
                    table_terms(query, model, group);
            for (std::size_t label = 0; label < centers; ++label) {
                const float candidate =
                        compact_distance(terms, model, label);
                const float reference = reference_distance(
                        query, model.expanded.blocks[group], label);
                const double difference = std::fabs(
                        static_cast<double>(candidate) - reference);
                const double tolerance = entry_tolerance(reference);
                result.max_table_absolute_difference = std::max(
                        result.max_table_absolute_difference, difference);
                result.table_tolerance_violations +=
                        difference > tolerance;
                table[label] = candidate;
            }
            result.table_entries_built += centers;
            const std::size_t code =
                    heldout_codes[left * kGroups + group];
            estimate.add(table[code]);
            const float reference_lookup = reference_distance(
                    query, model.expanded.blocks[group], code);
            lookup_tolerance += entry_tolerance(reference_lookup);

            const float* stored = panel.heldout.data() +
                    left * kDimensions + 2 * group;
            const double delta0 =
                    static_cast<double>(query[0]) - stored[0];
            const double delta1 =
                    static_cast<double>(query[1]) - stored[1];
            truth.add(delta0 * delta0 + delta1 * delta1);
        }
        const double absolute_error =
                std::fabs(estimate.get() - truth.get());
        const double pair_difference = std::fabs(
                absolute_error - pair_reference.absolute_errors[pair]);
        result.max_pair_absolute_error_difference = std::max(
                result.max_pair_absolute_error_difference,
                pair_difference);
        result.pair_tolerance_violations +=
                pair_difference > lookup_tolerance + 1e-12;
        result.absolute_errors.push_back(absolute_error);
        ++pair;
    }
    if (pair != pair_reference.absolute_errors.size() ||
        pair != panel.heldout_pairs)
        throw std::runtime_error("compact pair count mismatch");
    return result;
}

bool valid(const CompactCheck& check,
           const a4orb::PairEvaluation& pair_reference) {
    return check.fit_encoding_mismatches == 0 &&
            check.heldout_encoding_mismatches == 0 &&
            check.table_tolerance_violations == 0 &&
            check.pair_tolerance_violations == 0 &&
            check.table_entries_built ==
                    pair_reference.table_entries_built &&
            check.absolute_errors.size() ==
                    pair_reference.absolute_errors.size();
}

}  // namespace structured2d

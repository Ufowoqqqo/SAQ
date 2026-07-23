#include "model.hpp"
#include "compact.hpp"

#include "../a4_or_b/panel.hpp"

#include <immintrin.h>

#include <algorithm>
#include <cfenv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Timing {
    std::uint64_t cpu_us = 0;
    std::uint64_t wall_us = 0;
};

struct Timer {
    std::uint64_t cpu_start;
    std::chrono::steady_clock::time_point wall_start;
};

struct Record {
    int rate = 0;
    a4orb::Model model;
    a4orb::Evaluation fit;
    a4orb::Evaluation heldout;
    a4orb::PairEvaluation pairs;
    Timing training;
    Timing fit_evaluation;
    Timing heldout_evaluation;
    Timing pair_evaluation;
    std::size_t compact_bytes = 0;
    std::size_t transient_bytes = 0;
    std::size_t refinement_iterations = 0;
    bool converged = false;
    bool stopped_nonmonotonic = false;
    bool fixed_budget_complete = false;
};

struct CompactRecord {
    int rate = 0;
    structured2d::CompactCheck check;
    Timing timing;
    std::uint64_t reference_table_entries = 0;
    bool valid = false;
};

struct TraceRecord {
    int rate = 0;
    std::vector<structured2d::RefinementStep> steps;
};

std::uint64_t cpu_us() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return static_cast<std::uint64_t>(value.tv_sec) * 1000000 +
            static_cast<std::uint64_t>(value.tv_nsec) / 1000;
}

Timer start_timer() {
    return {cpu_us(), std::chrono::steady_clock::now()};
}

Timing stop_timer(const Timer& start) {
    return {
            cpu_us() - start.cpu_start,
            static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::microseconds>(
                            std::chrono::steady_clock::now() -
                            start.wall_start)
                            .count())};
}

Timing add_timing(const Timing& first, const Timing& second) {
    return {
            first.cpu_us + second.cpu_us,
            first.wall_us + second.wall_us};
}

template <typename Function>
auto timed(Function&& function, Timing& timing) {
    const auto start = start_timer();
    auto result = function();
    timing = stop_timer(start);
    return result;
}

unsigned prepare_numeric_environment() {
    if (std::fesetround(FE_TONEAREST) != 0 ||
        std::fegetround() != FE_TONEAREST)
        throw std::runtime_error("cannot establish FE_TONEAREST");
    unsigned control = _mm_getcsr();
    control &= ~(1U << 15);
    control &= ~(1U << 6);
    _mm_setcsr(control);
    return _mm_getcsr();
}

std::size_t parse_size(const char* value) {
    std::size_t consumed = 0;
    const auto result = std::stoull(value, &consumed);
    if (consumed != std::string(value).size())
        throw std::runtime_error("invalid numeric argument");
    return result;
}

double mean(const std::vector<double>& values) {
    if (values.empty()) throw std::runtime_error("empty mean");
    return std::accumulate(values.begin(), values.end(), 0.0) /
            values.size();
}

bool valid(const Record& record) {
    const bool common =
            record.fit.shape_valid && record.fit.encoding_valid &&
            record.heldout.shape_valid && record.heldout.encoding_valid &&
            record.fit.collisions == 0 &&
            record.heldout.collisions == 0 &&
            std::isfinite(record.fit.direct_sse) &&
            std::isfinite(record.heldout.direct_sse) &&
            std::fabs(record.fit.direct_sse -
                      record.fit.sufficient_sse) <=
                    1e-8 * std::max(1.0, record.fit.direct_sse) &&
            std::fabs(record.heldout.direct_sse -
                      record.heldout.sufficient_sse) <=
                    1e-8 * std::max(1.0, record.heldout.direct_sse);
    bool occupancy = true;
    if (record.model.arm == 'V') {
        occupancy = record.fit.empty_centers == 0;
    } else if (record.model.arm == 'S' || record.model.arm == 'T') {
        // T is the iteration-20 snapshot of the same shared-label model.
        // Both snapshots therefore use pooled, not per-group, occupancy.
        occupancy =
                structured2d::pooled_occupancy_valid(
                        record.model, record.fit);
    }
    return common && occupancy;
}

Record evaluate_model(int rate, a4orb::Model model,
                      const a4orb::Panel& panel, Timing training,
                      std::size_t compact_bytes = 0,
                      std::size_t transient_bytes = 0,
                      std::size_t refinement_iterations = 0,
                      bool converged = false,
                      bool stopped_nonmonotonic = false,
                      bool budget_complete = false) {
    Record record;
    record.rate = rate;
    record.model = std::move(model);
    record.training = training;
    record.compact_bytes =
            compact_bytes == 0
                    ? a4orb::persistent_model_bytes(record.model)
                    : compact_bytes;
    record.transient_bytes = transient_bytes;
    record.refinement_iterations = refinement_iterations;
    record.converged = converged;
    record.stopped_nonmonotonic = stopped_nonmonotonic;
    record.fixed_budget_complete = budget_complete;
    record.fit = timed(
            [&] { return a4orb::evaluate(panel.fit, record.model); },
            record.fit_evaluation);
    record.heldout = timed(
            [&] { return a4orb::evaluate(panel.heldout, record.model); },
            record.heldout_evaluation);
    record.pairs = timed(
            [&] {
                return a4orb::evaluate_pairs(
                        panel, record.model, record.heldout);
            },
            record.pair_evaluation);
    return record;
}

const Record& find(const std::vector<Record>& records, int rate, char arm) {
    const auto found = std::find_if(
            records.begin(), records.end(), [&](const Record& record) {
                return record.rate == rate && record.model.arm == arm;
            });
    if (found == records.end()) throw std::runtime_error("missing record");
    return *found;
}

double recovery(double d, double s, double v) {
    const double opportunity = d - v;
    if (!(opportunity > 0))
        return std::numeric_limits<double>::quiet_NaN();
    return (d - s) / opportunity;
}

void write_summary(const std::filesystem::path& path,
                   const std::string& dataset,
                   std::uint64_t fingerprint,
                   const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write summary");
    output << std::setprecision(17);
    output << "dataset\tfingerprint\trate\tarm\tshape\tfit_sse"
              "\theldout_sse\tpair_mae\tcompact_bytes"
              "\ttransient_expanded_bytes\ttraining_splits"
              "\trefinement_iterations\tconverged"
              "\tstopped_nonmonotonic\tfixed_budget_complete"
              "\tfit_empty_centers\theldout_empty_centers"
              "\tfit_collisions\theldout_collisions\tvalid"
              "\tfit_cpu_us\tfit_wall_us\tencode_fit_cpu_us"
              "\tencode_fit_wall_us\tencode_heldout_cpu_us"
              "\tencode_heldout_wall_us\tpair_cpu_us\tpair_wall_us"
              "\ttable_entries\n";
    for (const auto& record : records) {
        output << dataset << '\t' << fingerprint << '\t' << record.rate
               << '\t' << record.model.arm << '\t'
               << a4orb::model_shape(record.model) << '\t'
               << record.fit.direct_sse << '\t'
               << record.heldout.direct_sse << '\t'
               << mean(record.pairs.absolute_errors) << '\t'
               << record.compact_bytes << '\t' << record.transient_bytes
               << '\t' << record.model.training_splits << '\t'
               << record.refinement_iterations << '\t'
               << record.converged << '\t'
               << record.stopped_nonmonotonic << '\t'
               << record.fixed_budget_complete << '\t'
               << record.fit.empty_centers << '\t'
               << record.heldout.empty_centers << '\t'
               << record.fit.collisions << '\t'
               << record.heldout.collisions << '\t' << valid(record)
               << '\t' << record.training.cpu_us << '\t'
               << record.training.wall_us << '\t'
               << record.fit_evaluation.cpu_us << '\t'
               << record.fit_evaluation.wall_us << '\t'
               << record.heldout_evaluation.cpu_us << '\t'
               << record.heldout_evaluation.wall_us << '\t'
               << record.pair_evaluation.cpu_us << '\t'
               << record.pair_evaluation.wall_us << '\t'
               << record.pairs.table_entries_built << '\n';
    }
}

void write_groups(const std::filesystem::path& path,
                  const std::string& dataset,
                  const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write groups");
    output << std::setprecision(17);
    output << "dataset\trate\tarm\tgroup\tfit_sse\theldout_sse\n";
    for (const auto& record : records)
        for (std::size_t group = 0; group < a4orb::kGroups; ++group)
            output << dataset << '\t' << record.rate << '\t'
                   << record.model.arm << '\t' << group << '\t'
                   << record.fit.group_sse[group] << '\t'
                   << record.heldout.group_sse[group] << '\n';
}

bool write_decision(const std::filesystem::path& path,
                    const std::string& dataset,
                    const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write decision");
    output << std::setprecision(17);
    output << "dataset\trate\treconstruction_recovery"
              "\tpair_recovery\tgroups_improved\tcell_pass\n";
    bool all_pass = true;
    for (const int rate : {4, 8}) {
        const auto& d = find(records, rate, 'D');
        const auto& s = find(records, rate, 'S');
        const auto& v = find(records, rate, 'V');
        const double recon = recovery(
                d.heldout.direct_sse, s.heldout.direct_sse,
                v.heldout.direct_sse);
        const double pair = recovery(
                mean(d.pairs.absolute_errors),
                mean(s.pairs.absolute_errors),
                mean(v.pairs.absolute_errors));
        std::size_t improved = 0;
        for (std::size_t group = 0; group < a4orb::kGroups; ++group)
            improved += s.heldout.group_sse[group] <
                    d.heldout.group_sse[group];
        const bool pair_pass = std::isnan(pair) || pair >= 0.50;
        const bool pass = valid(d) && valid(s) && valid(v) &&
                recon >= 0.70 && improved >= 48 && pair_pass;
        all_pass = all_pass && pass;
        output << dataset << '\t' << rate << '\t' << recon << '\t'
               << pair << '\t' << improved << '\t' << pass << '\n';
    }
    return all_pass;
}

void write_traces(const std::filesystem::path& path,
                  const std::string& dataset,
                  const std::vector<TraceRecord>& traces) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write traces");
    output << std::setprecision(17);
    output << "dataset\trate\titeration\tfit_sse"
              "\trelative_improvement\n";
    for (const auto& trace : traces)
        for (const auto& step : trace.steps)
            output << dataset << '\t' << trace.rate << '\t'
                   << step.iteration << '\t' << step.fit_sse << '\t'
                   << step.relative_improvement << '\n';
}

void write_compact(const std::filesystem::path& path,
                   const std::string& dataset,
                   const std::vector<CompactRecord>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write compact checks");
    output << std::setprecision(17);
    output << "dataset\trate\tfit_encoding_mismatches"
              "\theldout_encoding_mismatches"
              "\ttable_tolerance_violations"
              "\tpair_tolerance_violations"
              "\tmax_table_abs_difference"
              "\tmax_pair_abs_error_difference"
              "\ttable_entries\treference_table_entries"
              "\tpeak_table_bytes\tcheck_cpu_us\tcheck_wall_us"
              "\tvalid\n";
    for (const auto& record : records)
        output << dataset << '\t' << record.rate << '\t'
               << record.check.fit_encoding_mismatches << '\t'
               << record.check.heldout_encoding_mismatches << '\t'
               << record.check.table_tolerance_violations << '\t'
               << record.check.pair_tolerance_violations << '\t'
               << record.check.max_table_absolute_difference << '\t'
               << record.check.max_pair_absolute_error_difference << '\t'
               << record.check.table_entries_built << '\t'
               << record.reference_table_entries << '\t'
               << record.check.peak_table_bytes << '\t'
               << record.timing.cpu_us << '\t'
               << record.timing.wall_us << '\t'
               << record.valid << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    std::cout << std::unitbuf;
    try {
        if (argc != 9) {
            std::cerr << "usage: " << argv[0]
                      << " DATASET BASE CENTROIDS CLUSTER_IDS INVENTORY"
                         " ROWS D OUTPUT_DIR\n";
            return 2;
        }
        const unsigned mxcsr = prepare_numeric_environment();
        const std::string dataset = argv[1];
        const a4orb::Panel panel = a4orb::load_panel(
                {argv[2], argv[3], argv[4], argv[5]},
                parse_size(argv[6]), parse_size(argv[7]));
        const auto fingerprint = a4orb::panel_fingerprint(panel);
        std::cout << "PANEL dataset=" << dataset
                  << " fingerprint=" << fingerprint
                  << " mxcsr=" << mxcsr << '\n';

        Timing curves_time;
        std::cout << "START D curves H=1024\n";
        const auto curves = timed(
                [&] { return a4orb::fit_curves(panel.fit, 1024); },
                curves_time);
        std::cout << "DONE D curves cpu_us=" << curves_time.cpu_us << '\n';

        std::vector<Record> records;
        std::vector<CompactRecord> compact_records;
        std::vector<TraceRecord> traces;
        for (const int rate : {4, 8}) {
            Timing d_time;
            auto d = timed(
                    [&] { return a4orb::allocate_scalar(curves, rate, true); },
                    d_time);
            d_time.cpu_us += curves_time.cpu_us;
            d_time.wall_us += curves_time.wall_us;
            records.push_back(evaluate_model(
                    rate, std::move(d), panel, d_time));

            const auto arbitrary =
                    a4orb::allocate_scalar(curves, rate, false);
            Timing s_time;
            std::cout << "START S20_SENSITIVITY B=" << rate << '\n';
            auto shared20 = timed(
                    [&] {
                        return structured2d::train(
                                panel.fit, rate,
                                structured2d::kSensitivityIterations);
                    },
                    s_time);
            auto s20_model = shared20.expanded;
            s20_model.arm = 'T';
            records.push_back(evaluate_model(
                    rate, std::move(s20_model), panel, s_time,
                    structured2d::persistent_model_bytes(shared20),
                    structured2d::transient_expanded_bytes(shared20),
                    shared20.refinement_iterations,
                    shared20.converged,
                    shared20.stopped_nonmonotonic,
                    structured2d::fixed_budget_complete(
                            shared20,
                            structured2d::kSensitivityIterations)));
            std::cout << "DONE S20_SENSITIVITY B=" << rate
                      << " cpu_us=" << s_time.cpu_us << '\n';

            // Continue the exact iteration-20 state to the method's fixed
            // construction budget. Held-out data never selects an iteration.
            auto shared = shared20;
            Timing continuation_time;
            std::cout << "START S_FIXED_BUDGET B=" << rate << '\n';
            timed(
                    [&] {
                        structured2d::refine(
                                panel.fit, shared,
                                structured2d::kFixedBudgetIterations);
                        return 0;
                    },
                    continuation_time);
            const Timing final_training =
                    add_timing(s_time, continuation_time);
            shared.expanded.arm = 'S';
            records.push_back(evaluate_model(
                    rate, shared.expanded, panel, final_training,
                    structured2d::persistent_model_bytes(shared),
                    structured2d::transient_expanded_bytes(shared),
                    shared.refinement_iterations,
                    shared.converged,
                    shared.stopped_nonmonotonic,
                    structured2d::fixed_budget_complete(shared)));
            const Record& final_record = records.back();
            CompactRecord compact;
            compact.rate = rate;
            compact.reference_table_entries =
                    final_record.pairs.table_entries_built;
            compact.check = timed(
                    [&] {
                        return structured2d::check_compact(
                                panel, shared, final_record.fit,
                                final_record.heldout,
                                final_record.pairs);
                    },
                    compact.timing);
            compact.valid =
                    structured2d::valid(
                            compact.check, final_record.pairs);
            compact_records.push_back(std::move(compact));
            traces.push_back({rate, shared.fit_trace});
            std::cout << "DONE S_FIXED_BUDGET B=" << rate
                      << " iterations=" << shared.refinement_iterations
                      << " budget_complete="
                      << structured2d::fixed_budget_complete(shared)
                      << " cpu_us=" << continuation_time.cpu_us << '\n';

            Timing v_time;
            std::cout << "START V B=" << rate << '\n';
            auto v = timed(
                    [&] {
                        return a4orb::train_v(
                                panel.fit, rate, arbitrary);
                    },
                    v_time);
            records.push_back(evaluate_model(
                    rate, std::move(v), panel, v_time));
            std::cout << "DONE V B=" << rate
                      << " cpu_us=" << v_time.cpu_us << '\n';
        }

        const std::filesystem::path output_directory = argv[8];
        std::filesystem::create_directories(output_directory);
        write_summary(
                output_directory / "summary.tsv", dataset,
                fingerprint, records);
        write_groups(output_directory / "groups.tsv", dataset, records);
        write_traces(
                output_directory / "convergence_trace.tsv",
                dataset, traces);
        write_compact(
                output_directory / "compact.tsv",
                dataset, compact_records);
        const bool pass = write_decision(
                output_directory / "decision.tsv", dataset, records);
        const bool all_valid =
                std::all_of(records.begin(), records.end(), valid);
        const bool compact_valid = std::all_of(
                compact_records.begin(), compact_records.end(),
                [](const CompactRecord& record) {
                    return record.valid;
                });
        const bool fixed_budget_all = std::all_of(
                records.begin(), records.end(),
                [](const Record& record) {
                    return record.model.arm != 'S' ||
                            record.fixed_budget_complete;
                });
        std::cout << "RESULT valid=" << all_valid
                  << " compact_valid=" << compact_valid
                  << " fixed_budget_all=" << fixed_budget_all
                  << " cell_pass=" << pass
                  << " output=" << output_directory << '\n';
        return all_valid && compact_valid && fixed_budget_all ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

#include "model.hpp"
#include "compact.hpp"
#include "microbench.hpp"

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

struct Distribution {
    double minimum = 0;
    double median = 0;
    double maximum = 0;
    double median_absolute_deviation = 0;
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

Distribution distribution(std::vector<double> values) {
    if (values.empty()) throw std::runtime_error("empty distribution");
    std::sort(values.begin(), values.end());
    const double median = values[values.size() / 2];
    std::vector<double> deviations;
    deviations.reserve(values.size());
    for (const double value : values)
        deviations.push_back(std::fabs(value - median));
    std::sort(deviations.begin(), deviations.end());
    return {
            values.front(), median, values.back(),
            deviations[deviations.size() / 2]};
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

void write_native_raw(
        const std::filesystem::path& path,
        const std::string& dataset, std::uint64_t fingerprint,
        const std::vector<structured2d::NativeBenchmark>& benchmarks) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write native timings");
    output << std::setprecision(17);
    output << "dataset\tfingerprint\trate\tarm\trepetition"
              "\tcandidate_count\tpayload_bytes_per_candidate"
              "\tbuild_cpu_ns\tbuild_wall_ns\tscan_cpu_ns"
              "\tscan_wall_ns\ttable_entries\tcandidates_scanned"
              "\tlookups\tbuild_checksum\tscan_checksum\n";
    for (const auto& benchmark : benchmarks)
        for (const auto& timing : benchmark.timings)
            for (const auto& scan : timing.scans)
                output << dataset << '\t' << fingerprint << '\t'
                       << benchmark.word_bits << '\t' << timing.arm << '\t'
                       << timing.repetition << '\t'
                       << scan.candidate_count << '\t'
                       << benchmark.payload_bytes << '\t'
                       << timing.build_cpu_ns << '\t'
                       << timing.build_wall_ns << '\t'
                       << scan.cpu_ns << '\t' << scan.wall_ns << '\t'
                       << timing.table_entries << '\t'
                       << scan.candidates_scanned << '\t'
                       << scan.lookups << '\t'
                       << timing.build_checksum << '\t'
                       << scan.checksum << '\n';
}

struct NativeSummary {
    int rate = 0;
    char arm = '?';
    std::size_t candidate_count = 0;
    std::uint64_t table_entries = 0;
    std::uint64_t lookups = 0;
    Distribution build_cpu;
    Distribution build_wall;
    Distribution scan_cpu;
    Distribution scan_wall;
};

NativeSummary summarize_native(
        const structured2d::NativeBenchmark& benchmark, char arm,
        std::size_t candidate_count) {
    std::vector<double> build_cpu, build_wall, scan_cpu, scan_wall;
    std::uint64_t table_entries = 0;
    std::uint64_t lookups = 0;
    for (const auto& timing : benchmark.timings) {
        if (timing.arm != arm) continue;
        table_entries = timing.table_entries;
        const auto found = std::find_if(
                timing.scans.begin(), timing.scans.end(),
                [&](const structured2d::PackedScanTiming& scan) {
                    return scan.candidate_count == candidate_count;
                });
        if (found == timing.scans.end())
            throw std::runtime_error("missing packed scan count");
        lookups = found->lookups;
        build_cpu.push_back(
                static_cast<double>(timing.build_cpu_ns) /
                structured2d::kMicrobenchmarkProbes);
        build_wall.push_back(
                static_cast<double>(timing.build_wall_ns) /
                structured2d::kMicrobenchmarkProbes);
        scan_cpu.push_back(
                static_cast<double>(found->cpu_ns) /
                found->candidates_scanned);
        scan_wall.push_back(
                static_cast<double>(found->wall_ns) /
                found->candidates_scanned);
    }
    if (build_cpu.size() != structured2d::kMicrobenchmarkRepetitions)
        throw std::runtime_error("native repetition count");
    return {
            benchmark.word_bits, arm, candidate_count,
            table_entries, lookups,
            distribution(std::move(build_cpu)),
            distribution(std::move(build_wall)),
            distribution(std::move(scan_cpu)),
            distribution(std::move(scan_wall))};
}

void write_distribution(std::ofstream& output,
                        const Distribution& value) {
    output << value.minimum << '\t' << value.median << '\t'
           << value.maximum << '\t'
           << value.median_absolute_deviation;
}

bool write_native_summary(
        const std::filesystem::path& summary_path,
        const std::filesystem::path& decision_path,
        const std::string& dataset, std::uint64_t fingerprint,
        const std::vector<structured2d::NativeBenchmark>& benchmarks) {
    std::ofstream summary(summary_path);
    std::ofstream decision(decision_path);
    if (!summary || !decision)
        throw std::runtime_error("cannot write native summary");
    summary << std::setprecision(17);
    decision << std::setprecision(17);
    summary << "dataset\tfingerprint\trate\tarm\tcandidate_count"
               "\trepetitions\ttable_entries_per_rep\tlookups_per_rep"
               "\tbuild_cpu_ns_per_probe_min"
               "\tbuild_cpu_ns_per_probe_median"
               "\tbuild_cpu_ns_per_probe_max"
               "\tbuild_cpu_ns_per_probe_mad"
               "\tbuild_wall_ns_per_probe_min"
               "\tbuild_wall_ns_per_probe_median"
               "\tbuild_wall_ns_per_probe_max"
               "\tbuild_wall_ns_per_probe_mad"
               "\tscan_cpu_ns_per_candidate_min"
               "\tscan_cpu_ns_per_candidate_median"
               "\tscan_cpu_ns_per_candidate_max"
               "\tscan_cpu_ns_per_candidate_mad"
               "\tscan_wall_ns_per_candidate_min"
               "\tscan_wall_ns_per_candidate_median"
               "\tscan_wall_ns_per_candidate_max"
               "\tscan_wall_ns_per_candidate_mad\n";
    decision << "dataset\trate\tcandidate_count\tpayload_bytes"
                "\tpeak_query_table_bytes\tcompact_table_violations"
                "\tscan_tolerance_violations"
                "\tmax_compact_table_difference"
                "\tmax_scan_difference\tshared_codes_reused"
                "\texpanded_direct_match"
                "\tcompact_expanded_scan_cpu_ratio"
                "\tcompact_expanded_scan_wall_ratio"
                "\tcompact_v_scan_cpu_ratio"
                "\tcompact_v_scan_wall_ratio"
                "\tcompact_expanded_total_cpu_ratio"
                "\tcompact_expanded_total_wall_ratio"
                "\tcompact_v_total_cpu_ratio"
                "\tcompact_v_total_wall_ratio"
                "\tfirst_compact_expanded_affordable_count"
                "\tcount_affordable\tcell_pass\n";

    bool all_pass = true;
    for (const auto& benchmark : benchmarks) {
        if (!structured2d::valid(benchmark))
            throw std::runtime_error(
                    "invalid native benchmark before ratios");
        std::size_t first_affordable = 0;
        for (const std::size_t count :
             structured2d::kCandidateCounts) {
            const NativeSummary compact =
                    summarize_native(benchmark, 'C', count);
            const NativeSummary expanded =
                    summarize_native(benchmark, 'E', count);
            const auto affordability =
                    structured2d::evaluate_affordability(
                            count,
                            compact.build_cpu.median,
                            compact.build_wall.median,
                            compact.scan_cpu.median,
                            compact.scan_wall.median,
                            expanded.build_cpu.median,
                            expanded.build_wall.median,
                            expanded.scan_cpu.median,
                            expanded.scan_wall.median);
            if (affordability.pass) {
                first_affordable = count;
                break;
            }
        }
        for (const std::size_t count :
             structured2d::kCandidateCounts) {
            const NativeSummary compact =
                    summarize_native(benchmark, 'C', count);
            const NativeSummary expanded =
                    summarize_native(benchmark, 'E', count);
            const NativeSummary independent =
                    summarize_native(benchmark, 'V', count);
            for (const NativeSummary* record :
                 {&compact, &expanded, &independent}) {
                summary << dataset << '\t' << fingerprint << '\t'
                        << record->rate << '\t' << record->arm << '\t'
                        << count << '\t'
                        << structured2d::kMicrobenchmarkRepetitions << '\t'
                        << record->table_entries << '\t'
                        << record->lookups << '\t';
                write_distribution(summary, record->build_cpu);
                summary << '\t';
                write_distribution(summary, record->build_wall);
                summary << '\t';
                write_distribution(summary, record->scan_cpu);
                summary << '\t';
                write_distribution(summary, record->scan_wall);
                summary << '\n';
            }

            const auto ce = structured2d::evaluate_affordability(
                    count,
                    compact.build_cpu.median,
                    compact.build_wall.median,
                    compact.scan_cpu.median,
                    compact.scan_wall.median,
                    expanded.build_cpu.median,
                    expanded.build_wall.median,
                    expanded.scan_cpu.median,
                    expanded.scan_wall.median);
            const auto cv = structured2d::evaluate_affordability(
                    count,
                    compact.build_cpu.median,
                    compact.build_wall.median,
                    compact.scan_cpu.median,
                    compact.scan_wall.median,
                    independent.build_cpu.median,
                    independent.build_wall.median,
                    independent.scan_cpu.median,
                    independent.scan_wall.median);
            const bool count_pass = ce.pass;
            if (count == structured2d::kCandidateCounts.back())
                all_pass = all_pass && count_pass;
            const std::size_t centers =
                    benchmark.word_bits == 4 ? 16 : 256;
            decision << dataset << '\t' << benchmark.word_bits << '\t'
                     << count << '\t' << benchmark.payload_bytes << '\t'
                     << 64 * centers * sizeof(float)
                     << '\t' << benchmark.compact_table_violations << '\t'
                     << benchmark.scan_tolerance_violations << '\t'
                     << benchmark.max_compact_table_difference << '\t'
                     << benchmark.max_scan_difference << '\t'
                     << benchmark.shared_codes_reused << '\t'
                     << benchmark.expanded_direct_match << '\t'
                     << ce.scan_cpu_ratio << '\t'
                     << ce.scan_wall_ratio << '\t'
                     << cv.scan_cpu_ratio << '\t'
                     << cv.scan_wall_ratio << '\t'
                     << ce.total_cpu_ratio << '\t'
                     << ce.total_wall_ratio << '\t'
                     << cv.total_cpu_ratio << '\t'
                     << cv.total_wall_ratio << '\t'
                     << first_affordable << '\t' << ce.pass << '\t'
                     << count_pass << '\n';
        }
    }
    return all_pass;
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
        std::vector<structured2d::NativeBenchmark> native_benchmarks;
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
            auto v_record = evaluate_model(
                    rate, std::move(v), panel, v_time);
            std::cout << "START NATIVE_MICROBENCH B=" << rate << '\n';
            native_benchmarks.push_back(
                    structured2d::benchmark_native_tables(
                            panel, shared, final_record.fit,
                            v_record.model, v_record.fit));
            records.push_back(std::move(v_record));
            std::cout << "DONE NATIVE_MICROBENCH B=" << rate
                      << " valid="
                      << structured2d::valid(native_benchmarks.back())
                      << '\n';
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
        write_native_raw(
                output_directory / "native_microbenchmark.tsv",
                dataset, fingerprint, native_benchmarks);
        const bool native_pass = write_native_summary(
                output_directory / "native_microbenchmark_summary.tsv",
                output_directory / "native_microbenchmark_decision.tsv",
                dataset, fingerprint, native_benchmarks);
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
                  << " native_pass=" << native_pass
                  << " cell_pass=" << pass
                  << " output=" << output_directory << '\n';
        return all_valid && compact_valid && fixed_budget_all &&
                native_pass
                ? 0
                : 1;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

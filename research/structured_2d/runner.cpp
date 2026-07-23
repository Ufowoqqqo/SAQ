#include "model.hpp"

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
    } else if (record.model.arm == 'S') {
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
                      std::size_t refinement_iterations = 0) {
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
              "\trefinement_iterations"
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
            std::cout << "START S B=" << rate << '\n';
            auto shared = timed(
                    [&] { return structured2d::train(panel.fit, rate); },
                    s_time);
            records.push_back(evaluate_model(
                    rate, std::move(shared.expanded), panel, s_time,
                    structured2d::persistent_model_bytes(shared),
                    structured2d::transient_expanded_bytes(shared),
                    shared.refinement_iterations));
            std::cout << "DONE S B=" << rate
                      << " cpu_us=" << s_time.cpu_us << '\n';

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
        const bool pass = write_decision(
                output_directory / "decision.tsv", dataset, records);
        const bool all_valid =
                std::all_of(records.begin(), records.end(), valid);
        std::cout << "RESULT valid=" << all_valid
                  << " cell_pass=" << pass
                  << " output=" << output_directory << '\n';
        return all_valid ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

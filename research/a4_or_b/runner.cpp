#include "models.hpp"
#include "panel.hpp"

#include <algorithm>
#include <chrono>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#include <immintrin.h>

namespace {

struct Timer {
    std::uint64_t cpu_start = 0;
    std::chrono::steady_clock::time_point wall_start;
};

struct Timing {
    std::uint64_t cpu_us = 0;
    std::uint64_t wall_us = 0;
};

std::uint64_t cpu_us() {
    timespec value{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
        throw std::runtime_error("process CPU clock");
    return static_cast<std::uint64_t>(value.tv_sec) * 1000000 +
            static_cast<std::uint64_t>(value.tv_nsec) / 1000;
}

unsigned prepare_numeric_environment() {
    if (std::fesetround(FE_TONEAREST) != 0 ||
        std::fegetround() != FE_TONEAREST)
        throw std::runtime_error("cannot establish FE_TONEAREST");
    unsigned control = _mm_getcsr();
    control &= ~(1U << 15);
    control &= ~(1U << 6);
    _mm_setcsr(control);
    control = _mm_getcsr();
    if ((control & (1U << 15)) != 0 || (control & (1U << 6)) != 0)
        throw std::runtime_error("cannot clear FTZ/DAZ");
    return control;
}

Timer start_timer() {
    return {cpu_us(), std::chrono::steady_clock::now()};
}

Timing stop_timer(const Timer& start) {
    const auto elapsed = std::chrono::steady_clock::now() - start.wall_start;
    return {
            cpu_us() - start.cpu_start,
            static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::microseconds>(
                            elapsed)
                            .count()),
    };
}

struct Phase {
    std::string name;
    std::size_t histogram = 0;
    int rate = 0;
    char arm = '-';
    Timing timing;
};

struct Record {
    std::size_t histogram = 0;
    int rate = 0;
    a4orb::Model model;
    a4orb::Evaluation fit;
    a4orb::Evaluation heldout;
    a4orb::PairEvaluation pairs;
    Timing allocation_or_training;
    Timing fit_evaluation;
    Timing heldout_evaluation;
    Timing pair_evaluation;
};

template <typename Function>
auto timed(Function&& function, Timing& timing) {
    const Timer start = start_timer();
    auto result = function();
    timing = stop_timer(start);
    return result;
}

double mean(const std::vector<double>& values) {
    return std::accumulate(values.begin(), values.end(), 0.0) / values.size();
}

Record finish_record(std::size_t histogram, int rate, a4orb::Model model,
                     const a4orb::Panel& panel, Timing fit_time) {
    Record record;
    record.histogram = histogram;
    record.rate = rate;
    record.model = std::move(model);
    record.allocation_or_training = fit_time;
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

Record allocate_record(const a4orb::Curves& curves, std::size_t histogram,
                       int rate, bool dyadic, const a4orb::Panel& panel) {
    Timing timing;
    auto model = timed(
            [&] { return a4orb::allocate_scalar(curves, rate, dyadic); },
            timing);
    return finish_record(
            histogram, rate, std::move(model), panel, timing);
}

Record p_record(int rate, const a4orb::Panel& panel) {
    Timing timing;
    auto model = timed(
            [&] { return a4orb::train_p(panel.fit, rate); }, timing);
    return finish_record(0, rate, std::move(model), panel, timing);
}

Record v_record(int rate, const a4orb::Panel& panel,
                const a4orb::Model& arbitrary) {
    Timing timing;
    auto model = timed(
            [&] {
                return a4orb::train_v(panel.fit, rate, arbitrary);
            },
            timing);
    return finish_record(0, rate, std::move(model), panel, timing);
}

bool valid_record(const Record& record) {
    const bool common =
            record.fit.shape_valid && record.fit.encoding_valid &&
            record.heldout.shape_valid && record.heldout.encoding_valid &&
            record.fit.collisions == 0 &&
            record.heldout.collisions == 0 &&
            std::isfinite(record.fit.direct_sse) &&
            std::isfinite(record.fit.sufficient_sse) &&
            std::isfinite(record.heldout.direct_sse) &&
            std::isfinite(record.heldout.sufficient_sse);
    const bool control =
            (record.model.arm != 'P' && record.model.arm != 'V') ||
            record.fit.empty_centers == 0;
    return common && control;
}

const Record& find_record(const std::vector<Record>& records,
                          std::size_t histogram, int rate, char arm) {
    const auto found = std::find_if(
            records.begin(), records.end(), [&](const Record& record) {
                return record.histogram == histogram &&
                        record.rate == rate && record.model.arm == arm;
            });
    if (found == records.end()) throw std::runtime_error("missing record");
    return *found;
}

int sign(double value) {
    return (value > 0) - (value < 0);
}

std::vector<int> decision_signs(const Record& d, const Record& a,
                                const Record& p, const Record& v) {
    const double dd = d.heldout.direct_sse;
    const double da = a.heldout.direct_sse;
    const double dp = p.heldout.direct_sse;
    const double dv = v.heldout.direct_sse;
    const double ed = mean(d.pairs.absolute_errors);
    const double ea = mean(a.pairs.absolute_errors);
    return {
            sign((dd - da) - 0.05 * dd),
            sign(dd - dv),
            sign((dd - da) - 0.50 * (dd - dv)),
            sign((ed - ea) - 0.05 * ed),
            sign(1.01 * dp - da),
    };
}

void write_summary(const std::filesystem::path& path,
                   const std::string& dataset,
                   std::uint64_t fingerprint,
                   const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write summary");
    output << std::setprecision(17);
    output << "dataset\tfingerprint\thistogram\trate\tarm\tshape"
              "\tfit_sse\theldout_sse\theldout_distortion"
              "\treplay_abs_difference\tpair_mae\tmodel_bytes"
              "\ttraining_splits\tfit_empty_centers"
              "\theldout_empty_centers\tfit_collisions"
              "\theldout_collisions\tfit_encoded\theldout_encoded"
              "\tambiguity\tvalid\tfit_cpu_us\tfit_wall_us"
              "\tfit_eval_cpu_us\tfit_eval_wall_us"
              "\theldout_eval_cpu_us\theldout_eval_wall_us"
              "\tpair_cpu_us\tpair_wall_us\ttable_entries\n";
    for (const auto& record : records) {
        output << dataset << '\t' << fingerprint << '\t'
               << record.histogram << '\t' << record.rate << '\t'
               << record.model.arm << '\t'
               << a4orb::model_shape(record.model) << '\t'
               << record.fit.direct_sse << '\t'
               << record.heldout.direct_sse << '\t'
               << record.heldout.direct_sse / a4orb::kRowsPerSplit << '\t'
               << std::fabs(record.heldout.direct_sse -
                            record.heldout.sufficient_sse)
               << '\t' << mean(record.pairs.absolute_errors) << '\t'
               << a4orb::persistent_model_bytes(record.model) << '\t'
               << record.model.training_splits << '\t'
               << record.fit.empty_centers << '\t'
               << record.heldout.empty_centers << '\t'
               << record.fit.collisions << '\t'
               << record.heldout.collisions << '\t'
               << record.fit.encoded_labels << '\t'
               << record.heldout.encoded_labels << '\t'
               << (record.fit.ambiguity || record.heldout.ambiguity) << '\t'
               << valid_record(record) << '\t'
               << record.allocation_or_training.cpu_us << '\t'
               << record.allocation_or_training.wall_us << '\t'
               << record.fit_evaluation.cpu_us << '\t'
               << record.fit_evaluation.wall_us << '\t'
               << record.heldout_evaluation.cpu_us << '\t'
               << record.heldout_evaluation.wall_us << '\t'
               << record.pair_evaluation.cpu_us << '\t'
               << record.pair_evaluation.wall_us << '\t'
               << record.pairs.table_entries_built << '\n';
    }
}

void write_phases(const std::filesystem::path& path,
                  const std::vector<Phase>& phases) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write phases");
    output << "phase\thistogram\trate\tarm\tcpu_us\twall_us\n";
    for (const auto& phase : phases)
        output << phase.name << '\t' << phase.histogram << '\t'
               << phase.rate << '\t' << phase.arm << '\t'
               << phase.timing.cpu_us << '\t' << phase.timing.wall_us
               << '\n';
}

void write_reconstruction(const std::filesystem::path& path,
                          const std::string& dataset,
                          const a4orb::Panel& panel,
                          const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write reconstruction");
    output << std::setprecision(17);
    output << "dataset\thistogram\trate\tarm\tcell_id\tvector_id"
              "\trow_sse\n";
    for (const auto& record : records) {
        for (std::size_t row = 0; row < panel.heldout_rows.size(); ++row) {
            const auto& metadata = panel.heldout_rows[row];
            output << dataset << '\t' << record.histogram << '\t'
                   << record.rate << '\t' << record.model.arm << '\t'
                   << metadata.cell_id << '\t' << metadata.vector_id << '\t'
                   << record.heldout.row_sse[row] << '\n';
        }
    }
}

void write_pairs(const std::filesystem::path& path,
                 const std::string& dataset,
                 const a4orb::Panel& panel,
                 const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write pairs");
    output << std::setprecision(17);
    output << "dataset\thistogram\trate\tarm\tcell_id"
              "\tleft_vector_id\tright_vector_id\tabsolute_error\n";
    for (const auto& record : records) {
        std::size_t pair = 0;
        for (std::size_t row = 0; row < panel.heldout_rows.size(); ++row) {
            if (panel.heldout_rows[row].pair_side !=
                a4orb::PairSide::Left)
                continue;
            output << dataset << '\t' << record.histogram << '\t'
                   << record.rate << '\t' << record.model.arm << '\t'
                   << panel.heldout_rows[row].cell_id << '\t'
                   << panel.heldout_rows[row].vector_id << '\t'
                   << panel.heldout_rows[row + 1].vector_id << '\t'
                   << record.pairs.absolute_errors[pair++] << '\n';
        }
    }
}

void write_groups(const std::filesystem::path& path,
                  const std::string& dataset,
                  const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write groups");
    output << std::setprecision(17);
    output << "dataset\thistogram\trate\tarm\tgroup\theldout_sse\n";
    for (const auto& record : records) {
        for (std::size_t group = 0; group < a4orb::kGroups; ++group)
            output << dataset << '\t' << record.histogram << '\t'
                   << record.rate << '\t' << record.model.arm << '\t'
                   << group << '\t'
                   << record.heldout.group_sse[group] << '\n';
    }
}

void write_allocations(const std::filesystem::path& path,
                       const std::string& dataset,
                       const std::vector<Record>& records) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write allocations");
    output << "dataset\thistogram\trate\tarm\tgroup\tdimension"
              "\tcenters\tradix1\tradix2\n";
    for (const auto& record : records) {
        std::size_t offset = 0;
        for (std::size_t block = 0;
             block < record.model.blocks.size(); ++block) {
            const auto& value = record.model.blocks[block];
            const std::size_t radix2 =
                    value.radix == 0 ? 0 : value.centers / value.radix;
            output << dataset << '\t' << record.histogram << '\t'
                   << record.rate << '\t' << record.model.arm << '\t'
                   << block << '\t' << value.dimension << '\t'
                   << value.centers << '\t' << value.radix << '\t'
                   << radix2 << '\n';
            offset += value.dimension;
        }
        if (offset != a4orb::kPanelDimensions)
            throw std::runtime_error("allocation dimension");
    }
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
        const std::uint64_t fingerprint =
                a4orb::panel_fingerprint(panel);
        std::cout << "PANEL dataset=" << dataset
                  << " fingerprint=" << fingerprint
                  << " eligible_cells=" << panel.eligible_cells
                  << " pairs=" << panel.heldout_pairs
                  << " mxcsr=" << mxcsr << '\n';

        std::vector<Record> records;
        std::vector<Phase> phases;
        for (const std::size_t histogram : {1024U, 2048U}) {
            Timing curve_time;
            std::cout << "START curves H=" << histogram << '\n';
            auto curves = timed(
                    [&] {
                        return a4orb::fit_curves(
                                panel.fit, histogram);
                    },
                    curve_time);
            phases.push_back(
                    {"scalar_curves", histogram, 0, '-', curve_time});
            std::cout << "DONE curves H=" << histogram
                      << " cpu_us=" << curve_time.cpu_us
                      << " wall_us=" << curve_time.wall_us << '\n';
            for (const int rate : {4, 8}) {
                records.push_back(allocate_record(
                        curves, histogram, rate, true, panel));
                records.push_back(allocate_record(
                        curves, histogram, rate, false, panel));
                std::cout << "DONE scalar_models H=" << histogram
                          << " B=" << rate << '\n';
            }
        }

        for (const int rate : {4, 8}) {
            std::cout << "START P B=" << rate << '\n';
            records.push_back(p_record(rate, panel));
            std::cout << "DONE P B=" << rate << '\n';
            const auto& arbitrary =
                    find_record(records, 1024, rate, 'A').model;
            std::cout << "START V B=" << rate << '\n';
            records.push_back(v_record(rate, panel, arbitrary));
            std::cout << "DONE V B=" << rate << '\n';
        }

        bool all_valid = std::all_of(
                records.begin(), records.end(), valid_record);
        bool sensitivity_same = true;
        for (const int rate : {4, 8}) {
            const auto& p = find_record(records, 0, rate, 'P');
            const auto& v = find_record(records, 0, rate, 'V');
            const auto primary = decision_signs(
                    find_record(records, 1024, rate, 'D'),
                    find_record(records, 1024, rate, 'A'), p, v);
            const auto sensitivity = decision_signs(
                    find_record(records, 2048, rate, 'D'),
                    find_record(records, 2048, rate, 'A'), p, v);
            sensitivity_same =
                    sensitivity_same && primary == sensitivity;
        }

        double replay_max = 0;
        double minimum_d = std::numeric_limits<double>::infinity();
        for (const auto& record : records) {
            replay_max = std::max(
                    replay_max,
                    std::fabs(record.heldout.direct_sse -
                              record.heldout.sufficient_sse) /
                            a4orb::kRowsPerSplit);
            if (record.model.arm == 'D')
                minimum_d = std::min(
                        minimum_d,
                        record.heldout.direct_sse /
                                a4orb::kRowsPerSplit);
        }
        const double replay_limit = 0.0005 * minimum_d;
        const bool replay_valid = replay_max <= replay_limit;

        const std::filesystem::path output_directory = argv[8];
        std::filesystem::create_directories(output_directory);
        write_summary(
                output_directory / "summary.tsv", dataset,
                fingerprint, records);
        write_phases(output_directory / "phases.tsv", phases);
        write_reconstruction(
                output_directory / "reconstruction.tsv",
                dataset, panel, records);
        write_pairs(
                output_directory / "pairs.tsv", dataset, panel, records);
        write_groups(
                output_directory / "groups.tsv", dataset, records);
        write_allocations(
                output_directory / "allocations.tsv", dataset, records);
        std::cout << "RESULT valid=" << all_valid
                  << " replay_valid=" << replay_valid
                  << " replay_max=" << std::setprecision(17) << replay_max
                  << " replay_limit=" << replay_limit
                  << " sensitivity_same=" << sensitivity_same
                  << " output=" << output_directory.string() << '\n';
        return all_valid && replay_valid && sensitivity_same ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

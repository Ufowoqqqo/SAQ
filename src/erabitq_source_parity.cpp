#include <immintrin.h>
#include <bits/stdc++.h>

#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// Load Eigen before exposing the official paper artifact's private encoder.
// This confines the access-control macro to the official classes rather than
// changing declarations in Eigen or the standard library.
#include "third/Eigen/Dense"

#define private public
#include "index/Quantizer.hpp"
#undef private

#ifndef ERABITQ_SOURCE_COMMIT
#define ERABITQ_SOURCE_COMMIT "unknown"
#endif

namespace {

constexpr double kObjectiveTolerance = 2e-12;
constexpr double kFloatFactorTolerance = 3e-6;
constexpr double kOfficialEpsilon = 1e-5;
constexpr int kOfficialExtraEnumeration = 10;

struct EncodeResult {
    std::vector<uint32_t> magnitude_code;
    double cosine = -std::numeric_limits<double>::infinity();
    double numerator = 0;
    double code_norm = 0;
    double scale = 0;
};

struct Counters {
    size_t tiny_exhaustive_cases = 0;
    size_t tiny_official_window_misses = 0;
    size_t official_supported_cases = 0;
    size_t official_private_extension_cases = 0;
    size_t official_b11_cases = 0;
    size_t d64_official_window_misses = 0;
    size_t mapping_cases = 0;
    size_t widened_values = 0;
    double max_tiny_objective_gap = 0;
    double max_tiny_official_window_gap = 0;
    double max_official_code_objective_gap = 0;
    double max_official_factor_relative_gap = 0;
    double max_full_event_gap = 0;
    double max_mapping_abs_gap = 0;
    std::string first_tiny_counterexample;
    std::string d64_counterexample;
};

[[noreturn]] void fail(const std::string &message) {
    throw std::runtime_error(message);
}

void require(bool condition, const std::string &message) {
    if (!condition) {
        fail(message);
    }
}

double l2_norm(const std::vector<double> &x) {
    double sum = 0;
    for (double value : x) {
        sum += value * value;
    }
    return std::sqrt(sum);
}

std::vector<double> as_double(const std::vector<float> &x) {
    return std::vector<double>(x.begin(), x.end());
}

EncodeResult evaluate_code(
    const std::vector<double> &x,
    const std::vector<uint32_t> &code,
    double scale = 0)
{
    require(x.size() == code.size(), "objective input size mismatch");
    double numerator = 0;
    double code_l2 = 0;
    for (size_t i = 0; i < x.size(); ++i) {
        const double value = static_cast<double>(code[i]) + 0.5;
        numerator += x[i] * value;
        code_l2 += value * value;
    }
    const double x_norm = l2_norm(x);
    require(x_norm > 0 && code_l2 > 0, "degenerate objective input");
    return EncodeResult{
        code,
        numerator / (x_norm * std::sqrt(code_l2)),
        numerator,
        std::sqrt(code_l2),
        scale,
    };
}

EncodeResult brute_force_magnitude_grid(const std::vector<double> &x, int total_bits) {
    require(total_bits >= 2 && total_bits <= 4, "tiny brute force supports B in [2,4]");
    const uint32_t levels = uint32_t{1} << (total_bits - 1);
    uint64_t configurations = 1;
    for (size_t i = 0; i < x.size(); ++i) {
        configurations *= levels;
    }

    EncodeResult best;
    std::vector<uint32_t> code(x.size(), 0);
    for (uint64_t ordinal = 0; ordinal < configurations; ++ordinal) {
        uint64_t value = ordinal;
        for (size_t i = 0; i < x.size(); ++i) {
            code[i] = static_cast<uint32_t>(value % levels);
            value /= levels;
        }
        const auto candidate = evaluate_code(x, code);
        if (candidate.cosine > best.cosine) {
            best = candidate;
        }
    }
    return best;
}

EncodeResult full_scale_event_oracle(const std::vector<double> &x, int total_bits) {
    require(total_bits >= 2 && total_bits <= 16, "unsupported total bit width");
    const uint32_t levels = uint32_t{1} << (total_bits - 1);
    std::vector<uint32_t> code(x.size(), 0);
    EncodeResult best = evaluate_code(x, code, 0);

    using Event = std::pair<double, size_t>;
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> events;
    for (size_t i = 0; i < x.size(); ++i) {
        require(x[i] > 0 && std::isfinite(x[i]), "event oracle requires finite positive coordinates");
        if (levels > 1) {
            events.emplace(1.0 / x[i], i);
        }
    }

    while (!events.empty()) {
        const auto [scale, coordinate] = events.top();
        events.pop();
        require(code[coordinate] + 1 < levels, "invalid event beyond magnitude grid");
        ++code[coordinate];
        const auto candidate = evaluate_code(x, code, scale);
        if (candidate.cosine > best.cosine) {
            best = candidate;
        }
        if (code[coordinate] + 1 < levels) {
            events.emplace((static_cast<double>(code[coordinate]) + 1.0) / x[coordinate], coordinate);
        }
    }
    return best;
}

// Source-faithful scalar extraction of DataQuantizer::fast_quantize. The only
// intentional change is a widened output type, which is required when total
// B=11 (the official magnitude code then needs 10 bits, but the paper artifact
// writes it through uint8_t).
EncodeResult official_window_widened(const std::vector<double> &x, int total_bits) {
    require(total_bits >= 2 && total_bits <= 16, "unsupported total bit width");
    const uint32_t levels = uint32_t{1} << (total_bits - 1);
    const double max_x = *std::max_element(x.begin(), x.end());
    require(max_x > 0 && std::isfinite(max_x), "official extraction requires positive input");

    const double start_scale = static_cast<double>((levels - 1) / 3) / max_x;
    const double end_scale = static_cast<double>(levels - 1 + kOfficialExtraEnumeration) / max_x;

    std::vector<uint32_t> current(x.size(), 0);
    double denominator_sqr = static_cast<double>(x.size()) * 0.25;
    double numerator = 0;
    for (size_t i = 0; i < x.size(); ++i) {
        current[i] = static_cast<uint32_t>(start_scale * x[i] + kOfficialEpsilon);
        denominator_sqr += static_cast<double>(current[i]) * current[i] + current[i];
        numerator += (static_cast<double>(current[i]) + 0.5) * x[i];
    }

    using Event = std::pair<double, size_t>;
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> events;
    for (size_t i = 0; i < x.size(); ++i) {
        events.emplace((static_cast<double>(current[i]) + 1.0) / x[i], i);
    }

    double best_cosine_without_x_norm = 0;
    double best_scale = 0;
    while (!events.empty()) {
        const auto [scale, coordinate] = events.top();
        events.pop();

        ++current[coordinate];
        const uint32_t updated = current[coordinate];
        denominator_sqr += 2.0 * updated;
        numerator += x[coordinate];

        const double candidate = numerator / std::sqrt(denominator_sqr);
        if (candidate > best_cosine_without_x_norm) {
            best_cosine_without_x_norm = candidate;
            best_scale = scale;
        }

        if (updated < levels - 1) {
            const double next_scale = (static_cast<double>(updated) + 1.0) / x[coordinate];
            if (next_scale < end_scale) {
                events.emplace(next_scale, coordinate);
            }
        }
    }

    std::vector<uint32_t> code(x.size(), 0);
    for (size_t i = 0; i < x.size(); ++i) {
        const double raw = best_scale * x[i] + kOfficialEpsilon;
        code[i] = static_cast<uint32_t>(raw);
        if (code[i] >= levels) {
            code[i] = levels - 1;
        }
    }
    return evaluate_code(x, code, best_scale);
}

std::vector<float> make_fixture(size_t dimension, uint64_t seed, int family) {
    std::mt19937_64 generator(seed);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::vector<double> values(dimension, 0);
    for (size_t i = 0; i < dimension; ++i) {
        const double jitter = 0.001 + 0.019 * uniform(generator);
        if (family == 0) {
            values[i] = 0.05 + 0.95 * uniform(generator) + jitter;
        } else if (family == 1) {
            values[i] = std::exp(-0.075 * static_cast<double>(i)) + jitter;
        } else if (family == 2) {
            values[i] = 1.0 + 0.01 * static_cast<double>(i) + jitter;
        } else {
            values[i] = (i == 0 ? 12.0 : 0.08 + 0.6 * uniform(generator)) + jitter;
        }
    }
    const double norm = l2_norm(values);
    std::vector<float> result(dimension, 0);
    for (size_t i = 0; i < dimension; ++i) {
        result[i] = static_cast<float>(values[i] / norm);
        require(result[i] > 0 && std::isfinite(result[i]), "fixture generation failed");
    }
    return result;
}

bool officially_exposed_total_bits(int total_bits) {
    switch (total_bits) {
    case 3:
    case 4:
    case 5:
    case 7:
    case 8:
    case 9:
        return true;
    default:
        return false;
    }
}

void validate_tiny_exhaustive(Counters &counters) {
    const auto check_case = [&counters](const std::vector<double> &x, int total_bits, const std::string &label) {
        const auto brute = brute_force_magnitude_grid(x, total_bits);
        const auto events = full_scale_event_oracle(x, total_bits);
        const auto window = official_window_widened(x, total_bits);
        const double event_gap = std::abs(brute.cosine - events.cosine);
        const double window_gap = std::abs(brute.cosine - window.cosine);
        counters.max_tiny_objective_gap = std::max(counters.max_tiny_objective_gap, event_gap);
        counters.max_tiny_official_window_gap =
            std::max(counters.max_tiny_official_window_gap, window_gap);
        require(event_gap <= kObjectiveTolerance, "full-event oracle failed tiny exhaustive parity");
        if (window_gap > kObjectiveTolerance) {
            ++counters.tiny_official_window_misses;
            if (counters.first_tiny_counterexample.empty()) {
                std::ostringstream description;
                description << std::setprecision(17)
                            << label << ";B=" << total_bits
                            << ";exact_cos=" << brute.cosine
                            << ";official_window_cos=" << window.cosine
                            << ";exact_code=";
                for (uint32_t value : brute.magnitude_code) {
                    description << value << ',';
                }
                description << ";official_window_code=";
                for (uint32_t value : window.magnitude_code) {
                    description << value << ',';
                }
                counters.first_tiny_counterexample = description.str();
            }
        }
        ++counters.tiny_exhaustive_cases;
    };

    // Explicit source-kernel counterexample. The optimal code is the official
    // t_start state, which DataQuantizer::fast_quantize initializes but never
    // evaluates because max_ip starts at zero and only post-increment states
    // are considered.
    {
        std::vector<double> raw{1.0, 0.3367865068, 0.3436238941, 0.3457800453};
        const double norm = l2_norm(raw);
        std::vector<double> x;
        x.reserve(raw.size());
        for (double value : raw) {
            x.push_back(static_cast<double>(static_cast<float>(value / norm)));
        }
        check_case(x, 3, "initial-state-counterexample");
    }

    for (size_t dimension = 2; dimension <= 4; ++dimension) {
        for (int total_bits = 2; total_bits <= 4; ++total_bits) {
            for (uint64_t seed = 1; seed <= 12; ++seed) {
                const auto xf = make_fixture(dimension, 1000 * dimension + 100 * total_bits + seed, seed % 4);
                const auto x = as_double(xf);
                check_case(x, total_bits, "deterministic-random");
            }
        }
    }
}

void validate_official_source(Counters &counters) {
    // Reachable public-dimension counterexample from the pinned C++ artifact.
    // With total B=3 (EX_BITS=2), this vector is exactly collinear with the
    // magnitude-grid code [1,0,...,0]. That code is the unscored t_start state.
    {
        constexpr int total_bits = 3;
        DataQuantizer official_quantizer(64, total_bits - 1);
        std::vector<float> xf(64, static_cast<float>(1.0 / std::sqrt(72.0)));
        xf[0] = static_cast<float>(3.0 / std::sqrt(72.0));
        const auto x = as_double(xf);
        std::vector<uint8_t> official_code(64, 0);
        float official_ip_norm = 0;
        official_quantizer.fast_quantize(xf.data(), official_code.data(), official_ip_norm);
        const auto mirror = official_window_widened(x, total_bits);
        const auto complete = full_scale_event_oracle(x, total_bits);
        for (size_t i = 0; i < 64; ++i) {
            require(
                official_code[i] == mirror.magnitude_code[i],
                "official D=64 counterexample differs from source extraction");
        }
        const double complete_gap = std::abs(mirror.cosine - complete.cosine);
        counters.max_full_event_gap = std::max(counters.max_full_event_gap, complete_gap);
        if (complete_gap > kObjectiveTolerance) {
            ++counters.d64_official_window_misses;
            std::ostringstream description;
            description << std::setprecision(17)
                        << "total_B=3;x=(3,1x63)/sqrt(72)"
                        << ";exact_cos=" << complete.cosine
                        << ";official_cos=" << mirror.cosine
                        << ";exact_head_code=" << complete.magnitude_code[0]
                        << ";exact_tail_code=" << complete.magnitude_code[1]
                        << ";official_head_code=" << mirror.magnitude_code[0]
                        << ";official_tail_code=" << mirror.magnitude_code[1];
            counters.d64_counterexample = description.str();
        }
        const double expected_ip_norm = 1.0 / mirror.numerator;
        const double factor_relative_gap = std::abs(
            static_cast<double>(official_ip_norm) - expected_ip_norm) /
            std::max(std::abs(expected_ip_norm), 1e-30);
        counters.max_official_factor_relative_gap =
            std::max(counters.max_official_factor_relative_gap, factor_relative_gap);
        require(
            factor_relative_gap <= kFloatFactorTolerance,
            "official D=64 counterexample factor differs from source extraction");
        ++counters.official_supported_cases;
    }

    const std::vector<int> total_bit_widths{2, 3, 4, 5, 6, 7, 8, 9, 11};
    for (int total_bits : total_bit_widths) {
        const int magnitude_bits = total_bits - 1;
        DataQuantizer official_quantizer(64, magnitude_bits);
        require(official_quantizer.D == 64, "official quantizer changed D=64 padding");
        require(
            official_quantizer.EX_BITS == static_cast<size_t>(magnitude_bits),
            "official magnitude-bit construction mismatch");

        for (int family = 0; family < 4; ++family) {
            for (uint64_t seed = 1; seed <= 6; ++seed) {
                const auto xf = make_fixture(64, 100000 * total_bits + 1000 * family + seed, family);
                const auto x = as_double(xf);
                std::vector<uint8_t> official_code(64, 0);
                float official_ip_norm = 0;
                official_quantizer.fast_quantize(xf.data(), official_code.data(), official_ip_norm);

                const auto mirror = official_window_widened(x, total_bits);
                const auto complete = full_scale_event_oracle(x, total_bits);
                const double complete_gap = std::abs(mirror.cosine - complete.cosine);
                counters.max_full_event_gap = std::max(counters.max_full_event_gap, complete_gap);
                if (complete_gap > kObjectiveTolerance) {
                    ++counters.d64_official_window_misses;
                }

                std::vector<uint32_t> official_widened(64, 0);
                for (size_t i = 0; i < 64; ++i) {
                    official_widened[i] = official_code[i];
                    if (total_bits == 11) {
                        require(
                            official_code[i] == static_cast<uint8_t>(mirror.magnitude_code[i]),
                            "B=11 official byte is not the expected narrowed magnitude code");
                        if (mirror.magnitude_code[i] > std::numeric_limits<uint8_t>::max()) {
                            ++counters.widened_values;
                        }
                    } else {
                        require(
                            official_widened[i] == mirror.magnitude_code[i],
                            "official magnitude code differs from source-faithful extraction");
                    }
                }

                if (total_bits != 11) {
                    const auto official_objective = evaluate_code(x, official_widened);
                    const double code_gap = std::abs(official_objective.cosine - mirror.cosine);
                    counters.max_official_code_objective_gap =
                        std::max(counters.max_official_code_objective_gap, code_gap);
                    require(code_gap <= kObjectiveTolerance, "official code objective mismatch");
                }

                const double expected_ip_norm = 1.0 / mirror.numerator;
                const double factor_relative_gap = std::abs(
                    static_cast<double>(official_ip_norm) - expected_ip_norm) /
                    std::max(std::abs(expected_ip_norm), 1e-30);
                counters.max_official_factor_relative_gap =
                    std::max(counters.max_official_factor_relative_gap, factor_relative_gap);
                require(
                    factor_relative_gap <= kFloatFactorTolerance,
                    "official xipnorm factor differs from source-faithful extraction");

                if (total_bits == 11) {
                    ++counters.official_b11_cases;
                } else if (officially_exposed_total_bits(total_bits)) {
                    ++counters.official_supported_cases;
                } else {
                    ++counters.official_private_extension_cases;
                }
            }
        }
    }
    require(counters.widened_values > 0, "B=11 fixtures did not exercise widened magnitude codes");
}

void validate_caq_mapping(Counters &counters) {
    const std::vector<int> total_bit_widths{2, 3, 4, 6, 9, 11};
    for (int total_bits : total_bit_widths) {
        const uint32_t magnitude_levels = uint32_t{1} << (total_bits - 1);
        for (uint64_t seed = 1; seed <= 8; ++seed) {
            const auto absolute_float = make_fixture(64, 900000 + 1000 * total_bits + seed, seed % 4);
            const auto absolute = as_double(absolute_float);
            const auto encoded = official_window_widened(absolute, total_bits);
            const double absolute_norm = l2_norm(absolute);

            std::vector<double> signed_unit(64, 0);
            std::vector<double> signed_grid(64, 0);
            std::vector<uint32_t> caq_code(64, 0);
            for (size_t i = 0; i < 64; ++i) {
                const double sign = ((i + seed) % 3 == 0) ? -1.0 : 1.0;
                signed_unit[i] = sign * absolute[i] / absolute_norm;
                signed_grid[i] = sign * (static_cast<double>(encoded.magnitude_code[i]) + 0.5);
                caq_code[i] = sign > 0
                    ? magnitude_levels + encoded.magnitude_code[i]
                    : magnitude_levels - 1 - encoded.magnitude_code[i];

                const double centered =
                    static_cast<double>(caq_code[i]) - (static_cast<double>(magnitude_levels) - 0.5);
                const double mapping_gap = std::abs(centered - signed_grid[i]);
                counters.max_mapping_abs_gap = std::max(counters.max_mapping_abs_gap, mapping_gap);
                require(mapping_gap == 0, "official sign/magnitude to CAQ code mapping failed");
            }

            const double residual_norm = 3.25;
            double max_unit_abs = 0;
            for (double value : signed_unit) {
                max_unit_abs = std::max(max_unit_abs, std::abs(value));
            }
            const double vmax = residual_norm * max_unit_abs;
            const double delta = vmax / static_cast<double>(magnitude_levels);
            std::vector<double> residual(64, 0);
            std::vector<double> caq_decoded(64, 0);
            for (size_t i = 0; i < 64; ++i) {
                residual[i] = residual_norm * signed_unit[i];
                caq_decoded[i] = -vmax + delta * (static_cast<double>(caq_code[i]) + 0.5);
                require(
                    std::abs(caq_decoded[i] - delta * signed_grid[i]) <= 1e-14,
                    "CAQ decoded grid is not a scaled E-RaBitQ codeword");
            }

            double ip_o_oa = 0;
            double oa_l2 = 0;
            double signed_ip = 0;
            double signed_grid_l2 = 0;
            for (size_t i = 0; i < 64; ++i) {
                ip_o_oa += residual[i] * caq_decoded[i];
                oa_l2 += caq_decoded[i] * caq_decoded[i];
                signed_ip += signed_unit[i] * signed_grid[i];
                signed_grid_l2 += signed_grid[i] * signed_grid[i];
            }
            const double cosine_caq = ip_o_oa / (residual_norm * std::sqrt(oa_l2));
            const double cosine_erabitq = signed_ip / std::sqrt(signed_grid_l2);
            require(
                std::abs(cosine_caq - cosine_erabitq) <= 2e-14,
                "CAQ/E-RaBitQ normalized direction mismatch");

            std::vector<double> query(64, 0);
            for (size_t i = 0; i < 64; ++i) {
                query[i] = std::sin(0.17 * static_cast<double>(i + 1)) +
                    0.1 * std::cos(0.07 * static_cast<double>(i + seed));
            }
            double ip_oa_q = 0;
            double ip_grid_q = 0;
            for (size_t i = 0; i < 64; ++i) {
                ip_oa_q += caq_decoded[i] * query[i];
                ip_grid_q += signed_grid[i] * query[i];
            }
            const double caq_rescale = residual_norm * residual_norm / ip_o_oa;
            const double caq_estimate = caq_rescale * ip_oa_q;
            const double erabitq_estimate = residual_norm * ip_grid_q / signed_ip;
            require(
                std::abs(caq_estimate - erabitq_estimate) <=
                    2e-13 * std::max(1.0, std::abs(erabitq_estimate)),
                "CAQ/E-RaBitQ rescaled inner-product estimator mismatch");

            constexpr double epsilon = 1.9;
            const double fac_from_state = residual_norm * residual_norm * epsilon *
                std::sqrt(
                    ((residual_norm * residual_norm * oa_l2) / (ip_o_oa * ip_o_oa) - 1.0) /
                    63.0);
            const double fac_from_cosine = residual_norm * residual_norm * epsilon *
                std::sqrt((1.0 / (cosine_caq * cosine_caq) - 1.0) / 63.0);
            require(
                std::abs(fac_from_state - fac_from_cosine) <=
                    2e-10 * std::max(1.0, std::abs(fac_from_cosine)),
                "CAQ error-factor formula mismatch");
            ++counters.mapping_cases;
        }
    }
}

bool print_summary(const Counters &counters) {
    const bool official_exact_parity =
        counters.tiny_official_window_misses == 0 &&
        counters.d64_official_window_misses == 0 &&
        counters.widened_values == 0;
    std::cout << std::setprecision(17);
    std::cout << "official_repo=https://github.com/VectorDB-NTU/Extended-RaBitQ.git\n";
    std::cout << "official_commit=" << ERABITQ_SOURCE_COMMIT << '\n';
    std::cout << "official_license=Apache-2.0\n";
    std::cout << "official_encoder=inc/index/Quantizer.hpp:DataQuantizer::fast_quantize\n";
    std::cout << "tiny_exhaustive_cases=" << counters.tiny_exhaustive_cases << '\n';
    std::cout << "tiny_official_window_misses=" << counters.tiny_official_window_misses << '\n';
    std::cout << "first_tiny_counterexample=" << counters.first_tiny_counterexample << '\n';
    std::cout << "official_supported_cases=" << counters.official_supported_cases << '\n';
    std::cout << "official_private_extension_cases=" << counters.official_private_extension_cases << '\n';
    std::cout << "official_b11_narrowing_cases=" << counters.official_b11_cases << '\n';
    std::cout << "d64_official_window_misses=" << counters.d64_official_window_misses << '\n';
    std::cout << "d64_counterexample=" << counters.d64_counterexample << '\n';
    std::cout << "mapping_cases=" << counters.mapping_cases << '\n';
    std::cout << "b11_widened_values=" << counters.widened_values << '\n';
    std::cout << "max_tiny_objective_gap=" << counters.max_tiny_objective_gap << '\n';
    std::cout << "max_tiny_official_window_gap=" << counters.max_tiny_official_window_gap << '\n';
    std::cout << "max_official_code_objective_gap=" << counters.max_official_code_objective_gap << '\n';
    std::cout << "max_official_factor_relative_gap=" << counters.max_official_factor_relative_gap << '\n';
    std::cout << "max_full_event_gap=" << counters.max_full_event_gap << '\n';
    std::cout << "max_mapping_abs_gap=" << counters.max_mapping_abs_gap << '\n';
    std::cout << "b11_adapter=source-faithful widened uint32 magnitude code; official uint8 output narrows modulo 256\n";
    std::cout << "full_event_tiny_exact="
              << (counters.max_tiny_objective_gap <= kObjectiveTolerance ? "PASS" : "FAIL") << '\n';
    std::cout << "official_source_exact_parity=" << (official_exact_parity ? "PASS" : "FAIL") << '\n';
    std::cout << "status=" << (official_exact_parity ? "PASS" : "FAIL") << '\n';
    return official_exact_parity;
}

} // namespace

int main() {
    try {
        Counters counters;
        validate_tiny_exhaustive(counters);
        validate_official_source(counters);
        validate_caq_mapping(counters);
        return print_summary(counters) ? 0 : 1;
    } catch (const std::exception &error) {
        std::cerr << "status=FAIL\nreason=" << error.what() << '\n';
        return 1;
    }
}

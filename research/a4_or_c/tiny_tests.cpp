#include "core.hpp"

#include <algorithm>
#include <bit>
#include <boost/multiprecision/cpp_int.hpp>
#include <boost/rational.hpp>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace a4or {
namespace {

constexpr std::uint64_t kTinySeed = 0xA40C202607220002ULL;
constexpr std::uint64_t kRowMul = 0x9E3779B97F4A7C15ULL;
constexpr std::uint64_t kCoordMul = 0xBF58476D1CE4E5B9ULL;
constexpr std::uint64_t kStreamXor = 0x94D049BB133111EBULL;

double canonical(double x) {
    if (!std::isfinite(x)) throw std::invalid_argument("nonfinite input");
    return x == 0.0 ? 0.0 : x;
}

std::vector<Point> aggregate(std::vector<Point> points) {
    for (auto& point : points) point.value = canonical(point.value);
    std::sort(points.begin(), points.end(), [](const Point& a, const Point& b) {
        return a.value < b.value ||
               (a.value == b.value && a.vector_id < b.vector_id);
    });
    std::vector<Point> result;
    for (const Point& point : points) {
        if (!result.empty() && result.back().value == point.value) {
            result.back().weight += point.weight;
            result.back().vector_id =
                    std::min(result.back().vector_id, point.vector_id);
        } else {
            result.push_back(point);
        }
    }
    return result;
}

using boost::multiprecision::cpp_int;
using Exact = boost::rational<cpp_int>;

cpp_int float_scaled(double value) {
    const float binary32 = static_cast<float>(value);
    if (static_cast<double>(binary32) != value)
        throw std::invalid_argument("tiny exact input is not binary32");
    const std::uint32_t u = std::bit_cast<std::uint32_t>(binary32 == 0 ? 0.0F
                                                                       : binary32);
    const bool negative = (u >> 31) != 0;
    const std::uint32_t exponent = (u >> 23) & 0xffU;
    const std::uint32_t fraction = u & 0x7fffffU;
    cpp_int magnitude;
    unsigned shift;
    if (exponent == 0) {
        magnitude = fraction;
        shift = 0;
    } else {
        magnitude = (1U << 23) | fraction;
        shift = exponent - 1;
    }
    magnitude <<= shift;
    return negative ? -magnitude : magnitude;
}

Exact exact_interval(const std::vector<Point>& points, std::size_t lo,
                     std::size_t hi) {
    cpp_int weight = 0, weighted_value = 0, weighted_square = 0;
    for (std::size_t i = lo; i < hi; ++i) {
        const cpp_int value = float_scaled(points[i].value);
        weight += points[i].weight;
        weighted_value += cpp_int(points[i].weight) * value;
        weighted_square += cpp_int(points[i].weight) * value * value;
    }
    return {weighted_square * weight - weighted_value * weighted_value, weight};
}

struct ExactResult {
    Exact objective;
    std::vector<std::size_t> boundaries;
    std::size_t ties;
};

bool last_boundary_less(const std::vector<std::size_t>& a,
                        const std::vector<std::size_t>& b) {
    return std::lexicographical_compare(a.rbegin(), a.rend(), b.rbegin(), b.rend());
}

ExactResult exhaustive(const std::vector<Point>& points, std::size_t k) {
    Exact best;
    bool have_best = false;
    std::vector<std::size_t> best_boundaries, boundaries;
    std::size_t ties = 0;
    std::function<void(std::size_t, std::size_t)> visit =
            [&](std::size_t start, std::size_t remaining) {
                if (remaining == 1) {
                    Exact objective;
                    std::size_t lo = 0;
                    for (std::size_t hi : boundaries) {
                        objective += exact_interval(points, lo, hi);
                        lo = hi;
                    }
                    objective += exact_interval(points, lo, points.size());
                    if (!have_best || objective < best) {
                        best = objective;
                        best_boundaries = boundaries;
                        ties = 1;
                        have_best = true;
                    } else if (objective == best) {
                        ++ties;
                        if (last_boundary_less(boundaries, best_boundaries))
                            best_boundaries = boundaries;
                    }
                    return;
                }
                const std::size_t max_boundary = points.size() - remaining + 1;
                for (std::size_t boundary = start; boundary <= max_boundary;
                     ++boundary) {
                    boundaries.push_back(boundary);
                    visit(boundary + 1, remaining - 1);
                    boundaries.pop_back();
                }
            };
    visit(1, k);
    return {best, best_boundaries, ties};
}

bool check_case(const std::vector<Point>& raw, std::size_t max_k,
                double& max_error, std::size_t& oracle_cleared,
                std::string& failure) {
    const auto points = aggregate(raw);
    const std::size_t curve_size = std::min(max_k, points.size());
    const auto curve = scalar_curve_ordered(
            points, curve_size, CandidateOrder::Forward);
    const auto reverse = scalar_curve_ordered(
            points, curve_size, CandidateOrder::Reverse);
    const auto shuffle = scalar_curve_ordered(
            points, curve_size, CandidateOrder::Shuffle);
    for (std::size_t k = 1; k <= curve.size(); ++k) {
        const auto reference = exhaustive(points, k);
        const long double exact_ld = std::ldexp(
                reference.objective.numerator().convert_to<long double>() /
                        reference.objective.denominator().convert_to<long double>(),
                -298);
        const double exact = static_cast<double>(exact_ld);
        const double error = std::fabs(curve[k - 1].sse - exact);
        max_error = std::max(max_error, error);
        const bool order_invariant =
                std::bit_cast<std::uint64_t>(curve[k - 1].sse) ==
                        std::bit_cast<std::uint64_t>(reverse[k - 1].sse) &&
                std::bit_cast<std::uint64_t>(curve[k - 1].sse) ==
                        std::bit_cast<std::uint64_t>(shuffle[k - 1].sse) &&
                curve[k - 1].boundaries == reverse[k - 1].boundaries &&
                curve[k - 1].boundaries == shuffle[k - 1].boundaries &&
                curve[k - 1].ambiguity == reverse[k - 1].ambiguity &&
                curve[k - 1].ambiguity == shuffle[k - 1].ambiguity;
        if (error > 1e-10 * std::max(1.0, std::fabs(exact)) ||
            curve[k - 1].boundaries != reference.boundaries ||
            (curve[k - 1].ambiguity && reference.ties == 1) ||
            !order_invariant) {
            std::ostringstream message;
            message << "tiny objective or tie mismatch k=" << k
                    << " production=" << curve[k - 1].sse
                    << " exact=" << exact << " production_boundaries=";
            for (auto boundary : curve[k - 1].boundaries)
                message << boundary << ',';
            message << " exact_boundaries=";
            for (auto boundary : reference.boundaries) message << boundary << ',';
            message << " ambiguity=" << curve[k - 1].ambiguity
                    << " exact_ties=" << reference.ties
                    << " order_invariant=" << order_invariant;
            failure = message.str();
            return false;
        }
        if (curve[k - 1].ambiguity && reference.ties > 1) ++oracle_cleared;
    }
    return true;
}

}  // namespace

bool run_tiny_exact(std::string& failure, double& max_error,
                    std::size_t& passed, std::size_t& oracle_cleared) {
    const float values[] = {-2, -1, 0, 1, 2};
    passed = 0;
    max_error = 0;
    oracle_cleared = 0;
    if (!last_boundary_less({2, 3}, {1, 4}) ||
        last_boundary_less({1, 4}, {2, 3})) {
        failure = "last-predecessor tie order";
        return false;
    }
    const float mean_inputs[] = {1.0F, std::bit_cast<float>(0x3f800001U)};
    const auto mean_bin = rank_histogram(mean_inputs, 2, 1);
    const double exact_mean =
            (static_cast<double>(mean_inputs[0]) + mean_inputs[1]) / 2;
    if (mean_bin[0].value != exact_mean ||
        mean_bin[0].value == static_cast<float>(mean_bin[0].value)) {
        failure = "histogram representative rounded before DP";
        return false;
    }
    for (std::size_t size = 1; size <= 4; ++size) {
        std::vector<std::size_t> chosen;
        std::function<bool(std::size_t)> combinations = [&](std::size_t begin) {
            if (chosen.size() == size) {
                std::uint64_t assignments = 1;
                for (std::size_t i = 0; i < size; ++i) assignments *= 3;
                for (std::uint64_t mask = 0; mask < assignments; ++mask) {
                    std::uint64_t q = mask;
                    std::vector<Point> points;
                    std::vector<std::uint64_t> point_weights(size);
                    for (std::size_t i = size; i-- > 0;) {
                        point_weights[i] = 1 + q % 3;
                        q /= 3;
                    }
                    if (passed == 16 &&
                        point_weights != std::vector<std::uint64_t>{1, 2}) {
                        failure = "fixture lexicographic case order";
                        return false;
                    }
                    for (std::size_t i = 0; i < size; ++i)
                        points.push_back({values[chosen[i]], point_weights[i],
                                          static_cast<std::uint32_t>(i)});
                    if (!check_case(points, size, max_error, oracle_cleared,
                                    failure))
                        return false;
                    ++passed;
                }
                return true;
            }
            for (std::size_t i = begin; i <= 5 - (size - chosen.size()); ++i) {
                chosen.push_back(i);
                if (!combinations(i + 1)) return false;
                chosen.pop_back();
            }
            return true;
        };
        if (!combinations(0)) return false;
    }
    const std::uint32_t patterns[][4] = {
        {0x80000000, 0, 0, 0},
        {0xbf800000, 0x80000000, 0, 0x3f800000},
        {0x80000001, 0x80000000, 0, 1},
        {0x80800000, 0x807fffff, 0x007fffff, 0x00800000},
        {0xff7fffff, 0xbf800000, 0x3f800000, 0x7f7fffff},
        {0xbf800000, 0, 0x3f800000, 0},
        {0x3f800000, 0x3f800001, 0, 0},
        {0x3f800001, 0x3f800002, 0, 0}};
    const std::uint64_t weights[][4] = {
        {1, 1, 0, 0}, {1, 2, 3, 1}, {1, 1, 1, 1}, {1, 2, 3, 4},
        {1, 1, 1, 1}, {1, 1, 1, 0}, {1, 1, 0, 0}, {1, 1, 0, 0}};
    const std::size_t sizes[] = {2, 4, 4, 4, 4, 3, 2, 2};
    for (std::size_t c = 0; c < 8; ++c) {
        std::vector<Point> points;
        for (std::size_t j = 0; j < sizes[c]; ++j)
            points.push_back({std::bit_cast<float>(patterns[c][j]), weights[c][j],
                              static_cast<std::uint32_t>(j)});
        if (!check_case(points, aggregate(points).size(), max_error,
                        oracle_cleared, failure))
            return false;
        ++passed;
    }
    for (std::uint64_t i = 0; i < 256; ++i) {
        const std::size_t size = 1 + i % 12;
        std::vector<Point> points;
        for (std::uint64_t j = 0; j < size; ++j) {
            const std::uint64_t base = kTinySeed ^ ((i + 1) * kRowMul) ^
                                       ((j + 1) * kCoordMul);
            points.push_back({
                static_cast<float>(-32 + static_cast<std::int64_t>(
                                                  splitmix64(base) % 65)),
                1 + splitmix64(base ^ kStreamXor) % 8,
                static_cast<std::uint32_t>(j)});
        }
        const std::size_t max_k =
                std::min<std::size_t>(8, aggregate(points).size());
        if (!check_case(points, max_k, max_error, oracle_cleared, failure))
            return false;
        ++passed;
    }
    if (oracle_cleared == 0) {
        failure = "no overlapping enclosure exact tie exercised";
        return false;
    }
    std::vector<Point> x1{{-1, 5, 0}, {0, 5, 1}, {1, 5, 2}};
    std::vector<Point> x2{{-2, 3, 0}, {-1, 3, 1}, {0, 3, 2},
                          {1, 3, 3}, {2, 3, 4}};
    auto first = scalar_curve(x1, 3), second = scalar_curve(x2, 5);
    first.resize(16, first.back());
    second.resize(16, second.back());
    auto reference = [&](int bits, bool dyadic) {
        std::vector<Allocation> candidates;
        const std::size_t capacity = std::size_t{1} << bits;
        for (std::size_t k1 = 1; k1 <= first.size(); ++k1) {
            if (dyadic && (k1 & (k1 - 1))) continue;
            for (std::size_t k2 = 1;
                 k2 <= second.size() && k1 * k2 <= capacity; ++k2) {
                if (dyadic && (k2 & (k2 - 1))) continue;
                candidates.push_back({
                    k1, k2, k1 * k2,
                    first[k1 - 1].sse + second[k2 - 1].sse,
                    first[k1 - 1].ambiguity || second[k2 - 1].ambiguity});
            }
        }
        std::sort(candidates.begin(), candidates.end(), [](const auto& a,
                                                            const auto& b) {
            if (a.sse != b.sse) return a.sse < b.sse;
            if (a.used_states != b.used_states)
                return a.used_states > b.used_states;
            return std::pair{a.k1, a.k2} < std::pair{b.k1, b.k2};
        });
        return candidates.front();
    };
    for (int bits : {4, 8}) {
        for (bool dyadic : {false, true}) {
            const Allocation got = allocate_pair(first, second, bits, dyadic);
            const Allocation expected = reference(bits, dyadic);
            if (got.k1 != expected.k1 || got.k2 != expected.k2 ||
                got.used_states != expected.used_states ||
                got.sse != expected.sse ||
                got.ambiguity != expected.ambiguity) {
                failure = "D/A exhaustive allocation parity";
                return false;
            }
        }
    }
    const Allocation witness = allocate_pair(first, second, 4, false);
    if (witness.k1 != 3 || witness.k2 != 5 || witness.sse != 0) {
        failure = "A4 (3,5) zero-error witness";
        return false;
    }
    const Allocation dyadic_witness = allocate_pair(first, second, 4, true);
    if (dyadic_witness.k1 != 4 || dyadic_witness.k2 != 4 ||
        dyadic_witness.sse != 1.5) {
        failure = "D (4,4) witness distortion";
        return false;
    }
    first[2].ambiguity = true;
    if (!allocate_pair(first, second, 4, false).ambiguity) {
        failure = "allocation ambiguity propagation";
        return false;
    }
    return passed == 1044;
}

bool run_representation_checks(std::string& failure,
                               std::size_t& roundtrips,
                               std::size_t& lookups) {
    roundtrips = 0;
    lookups = 0;
    for (int bits : {4, 8}) {
        const std::size_t capacity = std::size_t{1} << bits;
        for (std::size_t group = 0; group < 64; ++group) {
            const std::size_t k1 = bits == 4 ? 3 : 15;
            const std::size_t k2 = bits == 4 ? 5 : 17;
            std::vector<float> c1(k1), c2(k2);
            for (std::size_t i = 0; i < k1; ++i)
                c1[i] = float(int(i) - int(k1 / 2));
            for (std::size_t i = 0; i < k2; ++i)
                c2[i] = float(int(i) - int(k2 / 2)) / 2;
            std::vector<double> lut(
                    capacity, std::numeric_limits<double>::infinity());
            for (std::size_t address = 0; address < capacity; ++address) {
                if (address < k1 * k2) {
                    const auto labels = unpack(address, k1, k2);
                    if (pack(labels.first, labels.second, k1) != address) {
                        failure = "mixed-radix roundtrip";
                        return false;
                    }
                    ++roundtrips;
                    lut[address] = lookup_distance(
                            address, k1, k2, c1, c2, 0.25F, -0.5F);
                    const double x = 0.25 - c1[labels.first];
                    const double y = -0.5 - c2[labels.second];
                    if (lut[address] != x * x + y * y) {
                        failure = "lookup/direct mismatch";
                        return false;
                    }
                    ++lookups;
                } else {
                    try {
                        (void)unpack(address, k1, k2);
                    } catch (const std::out_of_range&) {
                        ++roundtrips;
                        continue;
                    }
                    failure = "invalid address accepted";
                    return false;
                }
            }
        }
    }
    return true;
}

}  // namespace a4or

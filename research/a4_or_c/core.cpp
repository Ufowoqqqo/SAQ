#include "core.hpp"

#include <faiss/Clustering.h>
#include <faiss/impl/ProductQuantizer.h>

#include <algorithm>
#include <bit>
#include <boost/multiprecision/cpp_int.hpp>
#include <boost/rational.hpp>
#include <cmath>
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <functional>
#include <immintrin.h>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace a4or {
namespace {

constexpr std::uint64_t kSeed = 0xA40C202607220001ULL;
constexpr std::uint64_t kTinySeed = 0xA40C202607220002ULL;
constexpr std::uint64_t kRowMul = 0x9E3779B97F4A7C15ULL;
constexpr std::uint64_t kCoordMul = 0xBF58476D1CE4E5B9ULL;
constexpr std::uint64_t kStreamXor = 0x94D049BB133111EBULL;

struct Enclosure {
    double lower;
    double upper;
};

struct Cost {
    double central;
    Enclosure enclosure;
};

struct Costs {
    std::size_t width;
    std::vector<Cost> values;
    Cost operator()(std::size_t lo, std::size_t hi) const {
        return values[lo * width + hi];
    }
};

double down(double x) {
    return std::nextafter(x, -std::numeric_limits<double>::infinity());
}

double up(double x) {
    return std::nextafter(x, std::numeric_limits<double>::infinity());
}

Enclosure add(Enclosure a, Enclosure b) {
    return {down(a.lower + b.lower), up(a.upper + b.upper)};
}

Enclosure subtract(Enclosure a, Enclosure b) {
    return {down(a.lower - b.upper), up(a.upper - b.lower)};
}

Enclosure multiply(Enclosure a, Enclosure b) {
    const double products[] = {a.lower * b.lower, a.lower * b.upper,
                               a.upper * b.lower, a.upper * b.upper};
    return {down(*std::min_element(products, products + 4)),
            up(*std::max_element(products, products + 4))};
}

Enclosure divide_positive(Enclosure a, Enclosure b) {
    if (!(b.lower > 0)) throw std::runtime_error("nonpositive interval divisor");
    return multiply(a, {down(1.0 / b.upper), up(1.0 / b.lower)});
}

float canonical(float x) {
    if (!std::isfinite(x)) throw std::invalid_argument("nonfinite input");
    return x == 0.0F ? 0.0F : x;
}

Costs stable_costs(const std::vector<Point>& p) {
    const std::size_t width = p.size() + 1;
    Costs result{width, std::vector<Cost>(width * width, {0, {0, 0}})};
    for (std::size_t lo = 0; lo < p.size(); ++lo) {
        double total_weight = 0, mean = 0, m2 = 0;
        Enclosure iw{0, 0}, imean{0, 0}, im2{0, 0};
        for (std::size_t hi = lo; hi < p.size(); ++hi) {
            if (p[hi].weight > (std::uint64_t{1} << 53) ||
                total_weight + static_cast<double>(p[hi].weight) >
                        static_cast<double>(std::uint64_t{1} << 53))
                throw std::invalid_argument("weight exceeds exact binary64 range");
            const double weight = static_cast<double>(p[hi].weight);
            const double next_weight = total_weight + weight;
            const double delta = static_cast<double>(p[hi].value) - mean;
            const double next_mean = mean + delta * (weight / next_weight);
            m2 += weight * delta *
                  (static_cast<double>(p[hi].value) - next_mean);

            const Enclosure ix{p[hi].value, p[hi].value};
            const Enclosure iweight{weight, weight};
            const Enclosure inext_weight = add(iw, iweight);
            const Enclosure idelta = subtract(ix, imean);
            const Enclosure iratio = divide_positive(iweight, inext_weight);
            const Enclosure inext_mean = add(imean, multiply(idelta, iratio));
            im2 = add(im2, multiply(multiply(iweight, idelta),
                                    subtract(ix, inext_mean)));
            total_weight = next_weight;
            mean = next_mean;
            iw = inext_weight;
            imean = inext_mean;
            result.values[lo * width + hi + 1] = {m2, im2};
        }
    }
    return result;
}

enum class CandidateOrder { Forward, Reverse, Shuffle };

std::vector<CurveEntry> scalar_curve_ordered(const std::vector<Point>& points,
                                             std::size_t max_k,
                                             CandidateOrder order);

struct Cell {
    double central = std::numeric_limits<double>::infinity();
    Enclosure enclosure{std::numeric_limits<double>::infinity(),
                        std::numeric_limits<double>::infinity()};
    std::size_t boundary = 0;
    bool ambiguity = false;
};

std::vector<Point> aggregate(std::vector<Point> p) {
    for (auto& v : p) v.value = canonical(v.value);
    std::sort(p.begin(), p.end(), [](const Point& a, const Point& b) {
        return a.value < b.value ||
               (a.value == b.value && a.vector_id < b.vector_id);
    });
    std::vector<Point> out;
    for (const Point& x : p) {
        if (!out.empty() && out.back().value == x.value) {
            out.back().weight += x.weight;
            out.back().vector_id = std::min(out.back().vector_id, x.vector_id);
        } else {
            out.push_back(x);
        }
    }
    return out;
}

using boost::multiprecision::cpp_int;

cpp_int float_scaled(float value) {
    const std::uint32_t u = std::bit_cast<std::uint32_t>(canonical(value));
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

using Exact = boost::rational<cpp_int>;

Exact exact_interval(const std::vector<Point>& p, std::size_t lo,
                     std::size_t hi) {
    cpp_int w = 0, wx = 0, wx2 = 0;
    for (std::size_t i = lo; i < hi; ++i) {
        const cpp_int x = float_scaled(p[i].value);
        w += p[i].weight;
        wx += cpp_int(p[i].weight) * x;
        wx2 += cpp_int(p[i].weight) * x * x;
    }
    return {wx2 * w - wx * wx, w};
}

struct ExactResult {
    Exact objective;
    std::vector<std::size_t> boundaries;
    std::size_t ties;
};

ExactResult exhaustive(const std::vector<Point>& p, std::size_t k) {
    Exact best;
    bool have_best = false;
    std::vector<std::size_t> best_boundaries;
    std::size_t ties = 0;
    std::vector<std::size_t> boundaries;
    std::function<void(std::size_t, std::size_t)> visit =
            [&](std::size_t start, std::size_t remaining) {
                if (remaining == 1) {
                    Exact objective;
                    std::size_t lo = 0;
                    for (std::size_t hi : boundaries) {
                        objective += exact_interval(p, lo, hi);
                        lo = hi;
                    }
                    objective += exact_interval(p, lo, p.size());
                    if (!have_best || objective < best) {
                        best = objective;
                        best_boundaries = boundaries;
                        ties = 1;
                        have_best = true;
                    } else if (objective == best) {
                        ++ties;
                        best_boundaries = std::min(best_boundaries, boundaries);
                    }
                    return;
                }
                const std::size_t max_boundary = p.size() - remaining + 1;
                for (std::size_t b = start; b <= max_boundary; ++b) {
                    boundaries.push_back(b);
                    visit(b + 1, remaining - 1);
                    boundaries.pop_back();
                }
            };
    visit(1, k);
    return {best, best_boundaries, ties};
}

bool check_case(const std::vector<Point>& raw, std::size_t max_k,
                double& max_error, std::size_t& oracle_cleared,
                std::string& failure) {
    const auto p = aggregate(raw);
    const std::size_t curve_size = std::min(max_k, p.size());
    const auto curve = scalar_curve_ordered(p, curve_size, CandidateOrder::Forward);
    const auto reverse = scalar_curve_ordered(p, curve_size, CandidateOrder::Reverse);
    const auto shuffle = scalar_curve_ordered(p, curve_size, CandidateOrder::Shuffle);
    for (std::size_t k = 1; k <= curve.size(); ++k) {
        const auto reference = exhaustive(p, k);
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
            for (auto b : curve[k - 1].boundaries) message << b << ',';
            message << " exact_boundaries=";
            for (auto b : reference.boundaries) message << b << ',';
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

std::uint64_t splitmix64(std::uint64_t x) {
    std::uint64_t z = x + kRowMul;
    z = (z ^ (z >> 30)) * kCoordMul;
    z = (z ^ (z >> 27)) * kStreamXor;
    return z ^ (z >> 31);
}

std::vector<float> synthetic_panel() {
    std::vector<float> result(8192 * 128);
    for (std::uint64_t row = 0; row < 8192; ++row) {
        for (std::uint64_t coordinate = 0; coordinate < 128; ++coordinate) {
            const std::uint64_t base = kSeed ^ ((row + 1) * kRowMul) ^
                                       ((coordinate + 1) * kCoordMul);
            const std::int64_t states = 3 + coordinate % 14;
            const std::int64_t label = splitmix64(base) % states;
            const std::int64_t noise =
                    static_cast<std::int64_t>(splitmix64(base ^ kStreamXor) % 17) - 8;
            const std::int64_t numerator =
                    (2 * label - (states - 1)) * 64 + noise;
            result[row * 128 + coordinate] =
                    static_cast<float>(static_cast<double>(numerator) / 64.0);
        }
    }
    return result;
}

std::vector<Point> rank_histogram(const float* values, std::size_t n,
                                  std::size_t h) {
    if (n == 0 || h == 0 || n % h != 0) throw std::invalid_argument("rank shape");
    std::vector<Point> sorted;
    sorted.reserve(n);
    for (std::size_t i = 0; i < n; ++i)
        sorted.push_back({canonical(values[i]), 1, static_cast<std::uint32_t>(i)});
    std::sort(sorted.begin(), sorted.end(), [](const Point& a, const Point& b) {
        return a.value < b.value ||
               (a.value == b.value && a.vector_id < b.vector_id);
    });
    std::vector<Point> bins;
    bins.reserve(h);
    const std::size_t width = n / h;
    for (std::size_t bin = 0; bin < h; ++bin) {
        double sum = 0, correction = 0;
        for (std::size_t i = bin * width; i < (bin + 1) * width; ++i) {
            const double t = sum + sorted[i].value;
            if (std::fabs(sum) >= std::fabs(sorted[i].value))
                correction += (sum - t) + sorted[i].value;
            else
                correction += (sorted[i].value - t) + sum;
            sum = t;
        }
        bins.push_back({static_cast<float>((sum + correction) / width), width,
                        static_cast<std::uint32_t>(bin)});
    }
    return bins;
}

namespace {

std::vector<CurveEntry> scalar_curve_ordered(const std::vector<Point>& points,
                                             std::size_t max_k,
                                             CandidateOrder order) {
    if (points.empty() || max_k == 0 || max_k > points.size())
        throw std::invalid_argument("curve shape");
    const Costs costs = stable_costs(points);
    const std::size_t n = points.size();
    std::vector<Cell> previous(n + 1);
    previous[0] = {0, {0, 0}, 0, false};
    std::vector<std::vector<std::size_t>> choices(max_k + 1,
                                                  std::vector<std::size_t>(n + 1));
    std::vector<std::vector<bool>> ambiguities(max_k + 1,
                                               std::vector<bool>(n + 1));
    std::vector<CurveEntry> curve;
    for (std::size_t k = 1; k <= max_k; ++k) {
        std::vector<Cell> current(n + 1);
        for (std::size_t end = k; end <= n; ++end) {
            std::vector<std::size_t> candidates(end - (k - 1));
            std::iota(candidates.begin(), candidates.end(), k - 1);
            if (order == CandidateOrder::Reverse)
                std::reverse(candidates.begin(), candidates.end());
            else if (order == CandidateOrder::Shuffle)
                std::sort(candidates.begin(), candidates.end(), [](auto a, auto b) {
                    const auto ha = splitmix64(0x51ed270bULL ^ a);
                    const auto hb = splitmix64(0x51ed270bULL ^ b);
                    return ha < hb || (ha == hb && a < b);
                });
            struct Candidate {
                std::size_t boundary;
                double central;
                Enclosure enclosure;
                bool ambiguity;
            };
            std::vector<Candidate> evaluated;
            double min_upper = std::numeric_limits<double>::infinity();
            for (std::size_t boundary : candidates) {
                const Cost cost = costs(boundary, end);
                Candidate candidate{boundary,
                                    previous[boundary].central + cost.central,
                                    add(previous[boundary].enclosure,
                                        cost.enclosure),
                                    previous[boundary].ambiguity};
                min_upper = std::min(min_upper, candidate.enclosure.upper);
                evaluated.push_back(candidate);
            }
            std::vector<Candidate> plausible;
            for (const Candidate& candidate : evaluated)
                if (candidate.enclosure.lower <= min_upper)
                    plausible.push_back(candidate);
            if (plausible.empty()) throw std::runtime_error("empty plausible set");
            const auto selected = std::min_element(
                    plausible.begin(), plausible.end(),
                    [](const Candidate& a, const Candidate& b) {
                        return a.boundary < b.boundary;
                    });
            bool unequal = false;
            for (const Candidate& candidate : plausible)
                unequal = unequal ||
                          std::bit_cast<std::uint64_t>(candidate.central) !=
                                  std::bit_cast<std::uint64_t>(selected->central);
            current[end] = {selected->central, selected->enclosure,
                            selected->boundary,
                            selected->ambiguity || (plausible.size() > 1 && unequal)};
            choices[k][end] = current[end].boundary;
            ambiguities[k][end] = current[end].ambiguity;
        }
        std::vector<std::size_t> boundaries;
        std::size_t end = n;
        bool path_ambiguity = false;
        for (std::size_t g = k; g > 1; --g) {
            path_ambiguity = path_ambiguity || ambiguities[g][end];
            end = choices[g][end];
            boundaries.push_back(end);
        }
        path_ambiguity = path_ambiguity || ambiguities[1][end];
        std::reverse(boundaries.begin(), boundaries.end());
        std::vector<float> centers;
        std::size_t lo = 0;
        for (std::size_t g = 0; g < k; ++g) {
            const std::size_t hi = g + 1 == k ? n : boundaries[g];
            double sum = 0, correction = 0, weight = 0;
            for (std::size_t i = lo; i < hi; ++i) {
                const double term = static_cast<double>(points[i].value) * points[i].weight;
                const double t = sum + term;
                if (std::fabs(sum) >= std::fabs(term)) correction += (sum - t) + term;
                else correction += (term - t) + sum;
                sum = t;
                weight += points[i].weight;
            }
            centers.push_back(static_cast<float>((sum + correction) / weight));
            lo = hi;
        }
        curve.push_back({current[n].central, std::move(boundaries),
                         std::move(centers), path_ambiguity});
        previous.swap(current);
    }
    return curve;
}

}  // namespace

std::vector<CurveEntry> scalar_curve(const std::vector<Point>& points,
                                     std::size_t max_k) {
    return scalar_curve_ordered(points, max_k, CandidateOrder::Forward);
}

Allocation allocate_pair(const std::vector<CurveEntry>& first,
                         const std::vector<CurveEntry>& second, int word_bits,
                         bool dyadic) {
    const std::size_t capacity = std::size_t{1} << word_bits;
    Allocation best{0, 0, 0, std::numeric_limits<double>::infinity()};
    for (std::size_t k1 = 1; k1 <= first.size(); ++k1) {
        if (dyadic && (k1 & (k1 - 1))) continue;
        for (std::size_t k2 = 1; k2 <= second.size() && k1 * k2 <= capacity; ++k2) {
            if (dyadic && (k2 & (k2 - 1))) continue;
            const double objective = first[k1 - 1].sse + second[k2 - 1].sse;
            const std::size_t used = k1 * k2;
            if (objective < best.sse ||
                (objective == best.sse &&
                 (used > best.used_states ||
                  (used == best.used_states && std::pair{k1, k2} <
                                                       std::pair{best.k1, best.k2}))))
                best = {k1, k2, used, objective};
        }
    }
    return best;
}

std::uint32_t pack(std::size_t z1, std::size_t z2, std::size_t k1) {
    return static_cast<std::uint32_t>(z1 + k1 * z2);
}

std::pair<std::size_t, std::size_t> unpack(std::uint32_t code,
                                           std::size_t k1, std::size_t k2) {
    if (k1 == 0 || code >= k1 * k2) throw std::out_of_range("invalid address");
    return {code % k1, code / k1};
}

double lookup_distance(std::uint32_t code, std::size_t k1, std::size_t k2,
                       const std::vector<float>& c1,
                       const std::vector<float>& c2, float q1, float q2) {
    const auto [z1, z2] = unpack(code, k1, k2);
    const double d1 = static_cast<double>(q1) - c1.at(z1);
    const double d2 = static_cast<double>(q2) - c2.at(z2);
    return d1 * d1 + d2 * d2;
}

ControlShape control_shape(int word_bits) {
    if (word_bits == 4) return {4, 32, 4, 256, 64, 16, 2026072204};
    if (word_bits == 8) return {8, 64, 2, 256, 64, 256, 2026072208};
    throw std::invalid_argument("word bits");
}

bool faiss_contract_smoke() {
    if (std::fegetround() != FE_TONEAREST) return false;
    const unsigned mxcsr = _mm_getcsr();
    if ((mxcsr & (1U << 15)) != 0 || (mxcsr & (1U << 6)) != 0) return false;
    for (int bits : {4, 8}) {
        const ControlShape s = control_shape(bits);
        faiss::ProductQuantizer pq(128, s.pq_m, 8);
        pq.train_type = faiss::ProductQuantizer::Train_default;
        pq.cp.niter = 300; pq.cp.nredo = 8; pq.cp.seed = s.pq_seed;
        pq.cp.min_points_per_centroid = 1; pq.cp.max_points_per_centroid = 8192;
        pq.cp.use_faster_subsampling = false; pq.cp.spherical = false;
        pq.cp.int_centroids = false; pq.cp.update_index = true; pq.cp.verbose = false;
        faiss::Clustering v(2, s.v_centers);
        v.niter = 300; v.nredo = 1; v.min_points_per_centroid = 1;
        v.max_points_per_centroid = 8192; v.use_faster_subsampling = false;
        v.spherical = false; v.int_centroids = false; v.update_index = true;
        v.verbose = false;
        if (pq.M != s.pq_m || pq.dsub != s.pq_dsub || pq.ksub != s.pq_ksub ||
            v.d != 2 || v.k != s.v_centers) return false;
    }
    return true;
}

bool run_tiny_exact(std::string& failure, double& max_error,
                    std::size_t& passed, std::size_t& oracle_cleared) {
    const float values[] = {-2, -1, 0, 1, 2};
    passed = 0; max_error = 0; oracle_cleared = 0;
    for (std::size_t size = 1; size <= 4; ++size) {
        std::vector<std::size_t> chosen;
        std::function<bool(std::size_t)> combinations = [&](std::size_t begin) {
            if (chosen.size() == size) {
                std::uint64_t assignments = 1;
                for (std::size_t i = 0; i < size; ++i) assignments *= 3;
                for (std::uint64_t mask = 0; mask < assignments; ++mask) {
                    std::uint64_t q = mask; std::vector<Point> p;
                    for (std::size_t i = 0; i < size; ++i) {
                        p.push_back({values[chosen[i]], 1 + q % 3,
                                     static_cast<std::uint32_t>(i)}); q /= 3;
                    }
                    if (!check_case(p, size, max_error, oracle_cleared, failure)) return false;
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
        {0x80000000,0,0,0}, {0xbf800000,0x80000000,0,0x3f800000},
        {0x80000001,0x80000000,0,1}, {0x80800000,0x807fffff,0x007fffff,0x00800000},
        {0xff7fffff,0xbf800000,0x3f800000,0x7f7fffff},
        {0xbf800000,0,0x3f800000,0}, {0x3f800000,0x3f800001,0,0},
        {0x3f800001,0x3f800002,0,0}};
    const std::uint64_t weights[][4] = {{1,1,0,0},{1,2,3,1},{1,1,1,1},{1,2,3,4},
        {1,1,1,1},{1,1,1,0},{1,1,0,0},{1,1,0,0}};
    const std::size_t sizes[] = {2,4,4,4,4,3,2,2};
    for (std::size_t c = 0; c < 8; ++c) {
        std::vector<Point> p;
        for (std::size_t j = 0; j < sizes[c]; ++j)
            p.push_back({std::bit_cast<float>(patterns[c][j]), weights[c][j],
                         static_cast<std::uint32_t>(j)});
        if (!check_case(p, aggregate(p).size(), max_error, oracle_cleared, failure)) return false;
        ++passed;
    }
    for (std::uint64_t i = 0; i < 256; ++i) {
        const std::size_t size = 1 + i % 12; std::vector<Point> p;
        for (std::uint64_t j = 0; j < size; ++j) {
            const std::uint64_t base = kTinySeed ^ ((i + 1) * kRowMul) ^
                                       ((j + 1) * kCoordMul);
            p.push_back({static_cast<float>(-32 + static_cast<std::int64_t>(splitmix64(base) % 65)),
                         1 + splitmix64(base ^ kStreamXor) % 8,
                         static_cast<std::uint32_t>(j)});
        }
        const std::size_t max_k = std::min<std::size_t>(8, aggregate(p).size());
        if (!check_case(p, max_k, max_error, oracle_cleared, failure)) return false;
        ++passed;
    }
    if (oracle_cleared == 0) {
        failure = "no overlapping enclosure exact tie exercised";
        return false;
    }
    return passed == 1044;
}

bool run_representation_checks(std::string& failure,
                               std::size_t& roundtrips,
                               std::size_t& lookups) {
    roundtrips = 0; lookups = 0;
    for (int bits : {4, 8}) {
        const std::size_t capacity = std::size_t{1} << bits;
        for (std::size_t group = 0; group < 64; ++group) {
            const std::size_t k1 = bits == 4 ? 3 : 15;
            const std::size_t k2 = bits == 4 ? 5 : 17;
            std::vector<float> c1(k1), c2(k2);
            for (std::size_t i = 0; i < k1; ++i) c1[i] = float(int(i) - int(k1 / 2));
            for (std::size_t i = 0; i < k2; ++i) c2[i] = float(int(i) - int(k2 / 2)) / 2;
            std::vector<double> lut(capacity, std::numeric_limits<double>::infinity());
            for (std::size_t address = 0; address < capacity; ++address) {
                if (address < k1 * k2) {
                    const auto labels = unpack(address, k1, k2);
                    if (pack(labels.first, labels.second, k1) != address) {
                        failure = "mixed-radix roundtrip"; return false;
                    }
                    ++roundtrips;
                    lut[address] = lookup_distance(address, k1, k2, c1, c2, 0.25F, -0.5F);
                    const double x = 0.25 - c1[labels.first];
                    const double y = -0.5 - c2[labels.second];
                    if (lut[address] != x * x + y * y) {
                        failure = "lookup/direct mismatch"; return false;
                    }
                    ++lookups;
                } else {
                    try { (void)unpack(address, k1, k2); }
                    catch (const std::out_of_range&) { ++roundtrips; continue; }
                    failure = "invalid address accepted"; return false;
                }
            }
        }
    }
    return true;
}

}  // namespace a4or

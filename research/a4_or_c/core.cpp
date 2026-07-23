#include "core.hpp"

#include <faiss/Clustering.h>
#include <faiss/impl/ProductQuantizer.h>

#include <algorithm>
#include <bit>
#include <cmath>
#include <cfenv>
#include <cstdint>
#include <immintrin.h>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace a4or {
namespace {

constexpr std::uint64_t kSeed = 0xA40C202607220001ULL;
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
        return values[hi * width + lo];
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
            const double delta = p[hi].value - mean;
            const double next_mean = mean + delta * (weight / next_weight);
            m2 += weight * delta *
                  (p[hi].value - next_mean);

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
            result.values[(hi + 1) * width + lo] = {m2, im2};
        }
    }
    return result;
}

struct Cell {
    double central = std::numeric_limits<double>::infinity();
    Enclosure enclosure{std::numeric_limits<double>::infinity(),
                        std::numeric_limits<double>::infinity()};
    std::size_t boundary = 0;
    bool ambiguity = false;
};

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
        bins.push_back({(sum + correction) / width, width,
                        static_cast<std::uint32_t>(bin)});
    }
    return bins;
}

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
    struct Candidate {
        std::size_t boundary;
        double central;
        Enclosure enclosure;
        bool ambiguity;
    };
    std::vector<Candidate> evaluated;
    evaluated.reserve(n);
    std::vector<std::size_t> candidates;
    candidates.reserve(n);
    for (std::size_t k = 1; k <= max_k; ++k) {
        std::vector<Cell> current(n + 1);
        for (std::size_t end = k; end <= n; ++end) {
            candidates.clear();
            if (order != CandidateOrder::Forward) {
                candidates.resize(end - (k - 1));
                std::iota(candidates.begin(), candidates.end(), k - 1);
                if (order == CandidateOrder::Reverse)
                    std::reverse(candidates.begin(), candidates.end());
                else
                    std::sort(candidates.begin(), candidates.end(),
                              [](auto a, auto b) {
                                  const auto ha =
                                          splitmix64(0x51ed270bULL ^ a);
                                  const auto hb =
                                          splitmix64(0x51ed270bULL ^ b);
                                  return ha < hb || (ha == hb && a < b);
                              });
            }
            evaluated.clear();
            double min_upper = std::numeric_limits<double>::infinity();
            const auto evaluate = [&](std::size_t boundary) {
                const Cost cost = costs(boundary, end);
                Candidate candidate{boundary,
                                    previous[boundary].central + cost.central,
                                    add(previous[boundary].enclosure,
                                        cost.enclosure),
                                    previous[boundary].ambiguity};
                min_upper = std::min(min_upper, candidate.enclosure.upper);
                evaluated.push_back(candidate);
            };
            if (order == CandidateOrder::Forward) {
                for (std::size_t boundary = k - 1; boundary < end; ++boundary)
                    evaluate(boundary);
            } else {
                for (std::size_t boundary : candidates) evaluate(boundary);
            }
            Candidate selected{};
            bool have_selected = false;
            bool have_central = false;
            std::uint64_t first_central = 0;
            std::size_t plausible_count = 0;
            bool unequal = false;
            for (const Candidate& candidate : evaluated) {
                if (candidate.enclosure.lower > min_upper) continue;
                ++plausible_count;
                const std::uint64_t central =
                        std::bit_cast<std::uint64_t>(candidate.central);
                if (!have_central)
                    first_central = central, have_central = true;
                else
                    unequal = unequal || central != first_central;
                if (!have_selected || candidate.boundary < selected.boundary)
                    selected = candidate, have_selected = true;
            }
            if (!have_selected) throw std::runtime_error("empty plausible set");
            current[end] = {selected.central, selected.enclosure,
                            selected.boundary,
                            selected.ambiguity ||
                                    (plausible_count > 1 && unequal)};
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
                const double term = points[i].value * points[i].weight;
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

std::vector<CurveEntry> scalar_curve(const std::vector<Point>& points,
                                     std::size_t max_k) {
    return scalar_curve_ordered(points, max_k, CandidateOrder::Forward);
}

Allocation allocate_pair(const std::vector<CurveEntry>& first,
                         const std::vector<CurveEntry>& second, int word_bits,
                         bool dyadic) {
    const std::size_t capacity = std::size_t{1} << word_bits;
    Allocation best{0, 0, 0, std::numeric_limits<double>::infinity(), false};
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
                best = {k1, k2, used, objective,
                        first[k1 - 1].ambiguity || second[k2 - 1].ambiguity};
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

}  // namespace a4or

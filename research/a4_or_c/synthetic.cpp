#include "synthetic.hpp"

#include "core.hpp"

#include <faiss/Clustering.h>
#include <faiss/IndexFlat.h>
#include <faiss/impl/ProductQuantizer.h>

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <limits>
#include <stdexcept>
#include <sys/resource.h>
#include <utility>
#include <vector>

namespace a4or {
namespace {

constexpr std::size_t kRows = 8192, kDimensions = 128;

std::uint64_t cpu_us() {
    timespec t{};
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t) != 0)
        throw std::runtime_error("process clock");
    return std::uint64_t(t.tv_sec) * 1000000 + t.tv_nsec / 1000;
}

struct Sum {
    double value = 0, correction = 0;
    void add(double x) {
        const double t = value + x;
        if (std::fabs(value) >= std::fabs(x)) correction += (value - t) + x;
        else correction += (x - t) + value;
        value = t;
    }
    double get() const { return value + correction; }
};

struct Block {
    std::size_t dimension = 0, centers = 0;
    std::vector<float> values;
    std::size_t radix = 0;
    bool ambiguity = false;
};

struct Replay {
    double direct = 0, sufficient = 0;
    std::size_t collisions = 0;
    bool ambiguity = false;
};

std::size_t nearest(const float* x, const Block& block) {
    double best = std::numeric_limits<double>::infinity();
    std::size_t label = 0;
    for (std::size_t k = 0; k < block.centers; ++k) {
        double distance = 0;
        for (std::size_t j = 0; j < block.dimension; ++j) {
            const double delta = x[j] - block.values[k * block.dimension + j];
            distance += delta * delta;
        }
        if (distance < best) best = distance, label = k;
    }
    return label;
}

std::size_t collisions(const Block& block) {
    std::size_t count = 0;
    for (std::size_t a = 0; a < block.centers; ++a)
        for (std::size_t b = 0; b < a; ++b) {
            bool equal = true;
            for (std::size_t j = 0; j < block.dimension; ++j)
                equal = equal &&
                        std::bit_cast<std::uint32_t>(
                                block.values[a * block.dimension + j]) ==
                        std::bit_cast<std::uint32_t>(
                                block.values[b * block.dimension + j]);
            if (equal) { ++count; break; }
        }
    return count;
}

Replay replay(const std::vector<float>& panel, const std::vector<Block>& blocks,
              const std::vector<std::uint8_t>* supplied_codes = nullptr) {
    Replay result;
    std::size_t offset = 0;
    for (std::size_t g = 0; g < blocks.size(); ++g) {
        const Block& block = blocks[g];
        result.collisions += collisions(block);
        result.ambiguity = result.ambiguity || block.ambiguity;
        std::vector<std::uint64_t> count(block.centers);
        std::vector<Sum> sum(block.centers * block.dimension), square(sum.size());
        Sum direct;
        for (std::size_t row = 0; row < kRows; ++row) {
            const float* x = panel.data() + row * kDimensions + offset;
            std::size_t label;
            if (supplied_codes) label = (*supplied_codes)[row * blocks.size() + g];
            else if (block.radix) {
                std::size_t z1 = 0, z2 = 0;
                double first = std::numeric_limits<double>::infinity();
                double second = first;
                const std::size_t k2 = block.centers / block.radix;
                for (std::size_t k = 0; k < block.radix; ++k) {
                    const double delta = x[0] - block.values[2 * k];
                    if (delta * delta < first) first = delta * delta, z1 = k;
                }
                for (std::size_t k = 0; k < k2; ++k) {
                    const double delta = x[1] - block.values[2 * k * block.radix + 1];
                    if (delta * delta < second) second = delta * delta, z2 = k;
                }
                label = pack(z1, z2, block.radix);
                if (unpack(label, block.radix, k2) != std::pair{z1, z2})
                    throw std::runtime_error("mixed-radix replay");
            } else label = nearest(x, block);
            if (label >= block.centers) throw std::runtime_error("invalid label");
            ++count[label];
            for (std::size_t j = 0; j < block.dimension; ++j) {
                const double value = x[j];
                const double center = block.values[label * block.dimension + j];
                const double delta = value - center;
                direct.add(delta * delta);
                sum[label * block.dimension + j].add(value);
                square[label * block.dimension + j].add(value * value);
            }
        }
        Sum sufficient;
        for (std::size_t k = 0; k < block.centers; ++k)
            for (std::size_t j = 0; j < block.dimension; ++j) {
                const double center = block.values[k * block.dimension + j];
                const std::size_t at = k * block.dimension + j;
                sufficient.add(square[at].get() - 2 * center * sum[at].get() +
                               count[k] * center * center);
            }
        result.direct += direct.get();
        result.sufficient += sufficient.get();
        offset += block.dimension;
    }
    if (offset != kDimensions) throw std::runtime_error("block shape");
    return result;
}

using Curves = std::array<std::vector<CurveEntry>, kDimensions>;

Curves fit_curves(const std::vector<float>& panel, std::size_t h,
                  std::uint64_t deadline, bool& exceeded) {
    Curves result;
    std::vector<float> coordinate(kRows);
    for (std::size_t d = 0; d < kDimensions; ++d) {
        for (std::size_t row = 0; row < kRows; ++row)
            coordinate[row] = panel[row * kDimensions + d];
        result[d] = scalar_curve(rank_histogram(coordinate.data(), kRows, h), 256);
        if (cpu_us() > deadline) { exceeded = true; break; }
    }
    return result;
}

std::vector<Block> allocate(const Curves& curves, int bits, bool dyadic) {
    std::vector<Block> result;
    result.reserve(64);
    for (std::size_t g = 0; g < 64; ++g) {
        const Allocation a = allocate_pair(curves[2 * g], curves[2 * g + 1],
                                           bits, dyadic);
        Block block{2, a.used_states, {}, a.k1, a.ambiguity};
        const auto& first = curves[2 * g][a.k1 - 1].centers;
        const auto& second = curves[2 * g + 1][a.k2 - 1].centers;
        block.values.reserve(2 * a.used_states);
        for (std::size_t z2 = 0; z2 < a.k2; ++z2)
            for (std::size_t z1 = 0; z1 < a.k1; ++z1) {
                block.values.push_back(first[z1]);
                block.values.push_back(second[z2]);
            }
        result.push_back(std::move(block));
    }
    return result;
}

Allocation allocate_reverse(const std::vector<CurveEntry>& first,
                            const std::vector<CurveEntry>& second, int bits,
                            bool dyadic) {
    const std::size_t capacity = std::size_t{1} << bits;
    Allocation best{0, 0, 0, std::numeric_limits<double>::infinity(), false};
    for (std::size_t k1 = first.size(); k1 > 0; --k1) {
        if (dyadic && (k1 & (k1 - 1))) continue;
        for (std::size_t k2 = second.size(); k2 > 0; --k2) {
            if (k1 * k2 > capacity || (dyadic && (k2 & (k2 - 1)))) continue;
            const double objective = first[k1 - 1].sse + second[k2 - 1].sse;
            const std::size_t used = k1 * k2;
            if (objective < best.sse ||
                (objective == best.sse &&
                 (used > best.used_states ||
                  (used == best.used_states &&
                   std::pair{k1, k2} < std::pair{best.k1, best.k2}))))
                best = {k1, k2, used, objective,
                        first[k1 - 1].ambiguity || second[k2 - 1].ambiguity};
        }
    }
    return best;
}

bool same_allocation(const Allocation& a, const Allocation& b) {
    return a.k1 == b.k1 && a.k2 == b.k2 &&
           a.used_states == b.used_states && a.sse == b.sse &&
           a.ambiguity == b.ambiguity;
}

faiss::Clustering configured(std::size_t dimension, std::size_t k, int seed,
                             int redos) {
    faiss::Clustering clustering(dimension, k);
    clustering.niter = 300;
    clustering.nredo = redos;
    clustering.seed = seed;
    clustering.min_points_per_centroid = 1;
    clustering.max_points_per_centroid = 8192;
    clustering.use_faster_subsampling = false;
    clustering.spherical = false;
    clustering.int_centroids = false;
    clustering.update_index = true;
    clustering.verbose = false;
    return clustering;
}

std::size_t nsplit(const faiss::Clustering& clustering) {
    std::size_t result = 0;
    for (const auto& stat : clustering.iteration_stats) result += stat.nsplit;
    return result;
}

struct Control {
    std::vector<Block> blocks;
    std::vector<std::uint8_t> codes;
    std::size_t split_count = 0;
};

Control train_p(const std::vector<float>& panel, int bits) {
    const ControlShape shape = control_shape(bits);
    faiss::ProductQuantizer pq(128, shape.pq_m, 8);
    pq.train_type = faiss::ProductQuantizer::Train_default;
    std::vector<float> sub(kRows * shape.pq_dsub);
    std::size_t splits = 0;
    for (std::size_t g = 0; g < shape.pq_m; ++g) {
        for (std::size_t row = 0; row < kRows; ++row)
            std::copy_n(panel.data() + row * 128 + g * shape.pq_dsub,
                        shape.pq_dsub, sub.data() + row * shape.pq_dsub);
        auto clustering = configured(shape.pq_dsub, 256, shape.pq_seed, 8);
        faiss::IndexFlatL2 index(shape.pq_dsub);
        clustering.train(kRows, sub.data(), index);
        splits += nsplit(clustering);
        pq.set_params(clustering.centroids.data(), g);
    }
    std::vector<std::uint8_t> codes(kRows * shape.pq_m);
    pq.compute_codes(panel.data(), codes.data(), kRows);
    std::vector<Block> blocks;
    for (std::size_t g = 0; g < shape.pq_m; ++g) {
        Block block{shape.pq_dsub, 256, {}, 0, false};
        block.values.assign(pq.get_centroids(g, 0),
                            pq.get_centroids(g, 0) + 256 * shape.pq_dsub);
        blocks.push_back(std::move(block));
    }
    return {std::move(blocks), std::move(codes), splits};
}

double block_sse(const std::vector<float>& points, const Block& block) {
    Sum result;
    for (std::size_t row = 0; row < kRows; ++row) {
        const float* x = points.data() + row * 2;
        const std::size_t label = nearest(x, block);
        for (std::size_t j = 0; j < 2; ++j) {
            const double delta = x[j] - block.values[label * 2 + j];
            result.add(delta * delta);
        }
    }
    return result.get();
}

Block v_start0(const std::vector<float>& points, const Block& a,
               std::size_t target) {
    Block result = a;
    while (result.centers < target) {
        double farthest = -1;
        std::size_t chosen = 0;
        for (std::size_t row = 0; row < kRows; ++row) {
            const float* x = points.data() + row * 2;
            const std::size_t label = nearest(x, result);
            double distance = 0;
            for (std::size_t j = 0; j < 2; ++j) {
                const double delta = x[j] - result.values[label * 2 + j];
                distance += delta * delta;
            }
            if (distance > farthest) farthest = distance, chosen = row;
        }
        result.values.push_back(points[2 * chosen]);
        result.values.push_back(points[2 * chosen + 1]);
        ++result.centers;
    }
    return result;
}

Control train_v(const std::vector<float>& panel, int bits,
                const std::vector<Block>& primary_a) {
    const std::size_t k = std::size_t{1} << bits;
    std::vector<Block> blocks;
    std::size_t splits = 0;
    std::vector<float> points(kRows * 2);
    for (std::size_t g = 0; g < 64; ++g) {
        for (std::size_t row = 0; row < kRows; ++row) {
            points[2 * row] = panel[row * 128 + 2 * g];
            points[2 * row + 1] = panel[row * 128 + 2 * g + 1];
        }
        double best = std::numeric_limits<double>::infinity();
        Block winner;
        for (int redo = 0; redo < 8; ++redo) {
            auto clustering = configured(2, k,
                    20260722 + bits * 10000 + g * 8 + redo, 1);
            if (redo == 0)
                clustering.centroids = v_start0(points, primary_a[g], k).values;
            faiss::IndexFlatL2 index(2);
            clustering.train(kRows, points.data(), index);
            splits += nsplit(clustering);
            Block candidate{2, k, clustering.centroids, 0, false};
            const double objective = block_sse(points, candidate);
            if (objective < best) best = objective, winner = std::move(candidate);
        }
        blocks.push_back(std::move(winner));
    }
    return {std::move(blocks), {}, splits};
}

int sign(double x) { return (x > 0) - (x < 0); }

std::array<int, 4> decisions(double d, double a, double p, double v) {
    return {sign((d - a) - 0.05 * d), sign(d - v),
            sign((d - a) - 0.5 * (d - v)), sign(1.01 * p - a)};
}

}  // namespace

SyntheticResult run_synthetic_admission() {
    SyntheticResult out;
    const auto wall_start = std::chrono::steady_clock::now();
    std::uint64_t mark = cpu_us();
    const auto panel = synthetic_panel();
    out.support_cpu_us = cpu_us() - mark;
    std::array<std::array<Replay, 2>, 2> d{}, a{};
    std::array<std::vector<Block>, 2> primary_a;
    const std::uint64_t da_deadline = cpu_us() + 1800000000ULL;
    bool cost_exceeded = false;
    for (std::size_t hi = 0; hi < 2; ++hi) {
        mark = cpu_us();
        const Curves curves = fit_curves(panel, hi == 0 ? 1024 : 2048,
                                         da_deadline, cost_exceeded);
        out.shared_scalar_cpu_us += cpu_us() - mark;
        if (cost_exceeded) break;
        for (std::size_t bi = 0; bi < 2; ++bi) {
            const int bits = bi == 0 ? 4 : 8;
            for (std::size_t g = 0; g < 64; ++g)
                for (bool dyadic : {false, true})
                    out.allocation_order_same = out.allocation_order_same &&
                            same_allocation(
                                    allocate_pair(curves[2 * g], curves[2 * g + 1],
                                                  bits, dyadic),
                                    allocate_reverse(curves[2 * g], curves[2 * g + 1],
                                                     bits, dyadic));
            mark = cpu_us();
            const auto dm = allocate(curves, bits, true);
            d[hi][bi] = replay(panel, dm);
            out.d_cpu_us += cpu_us() - mark;
            mark = cpu_us();
            auto am = allocate(curves, bits, false);
            a[hi][bi] = replay(panel, am);
            out.a_cpu_us += cpu_us() - mark;
            if (hi == 0) primary_a[bi] = std::move(am);
        }
    }
    if (cost_exceeded ||
        2 * (out.shared_scalar_cpu_us + out.d_cpu_us + out.a_cpu_us) >
                3600000000ULL) {
        out.failure = "T_project";
        rusage usage{};
        getrusage(RUSAGE_SELF, &usage);
        out.peak_rss_bytes = std::uint64_t(usage.ru_maxrss) * 1024;
        out.wall_us = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::steady_clock::now() - wall_start).count();
        return out;
    }
    std::array<Replay, 2> p{}, v{};
    for (std::size_t bi = 0; bi < 2; ++bi) {
        const int bits = bi == 0 ? 4 : 8;
        mark = cpu_us();
        const Control pc = train_p(panel, bits);
        const ControlShape shape = control_shape(bits);
        out.p_shape_valid = out.p_shape_valid && pc.blocks.size() == shape.pq_m &&
                pc.codes.size() == kRows * shape.pq_m;
        for (const Block& block : pc.blocks)
            out.p_shape_valid = out.p_shape_valid &&
                    block.dimension == shape.pq_dsub && block.centers == 256 &&
                    block.values.size() == 256 * shape.pq_dsub;
        p[bi] = replay(panel, pc.blocks, &pc.codes);
        out.p_nsplit += pc.split_count;
        out.p_cpu_us += cpu_us() - mark;
        mark = cpu_us();
        const Control vc = train_v(panel, bits, primary_a[bi]);
        out.v_shape_valid = out.v_shape_valid && vc.blocks.size() == 64;
        for (const Block& block : vc.blocks)
            out.v_shape_valid = out.v_shape_valid && block.dimension == 2 &&
                    block.centers == shape.v_centers &&
                    block.values.size() == 2 * shape.v_centers;
        v[bi] = replay(panel, vc.blocks);
        out.v_nsplit += vc.split_count;
        out.v_cpu_us += cpu_us() - mark;
    }
    double min_d = std::numeric_limits<double>::infinity();
    for (std::size_t hi = 0; hi < 2; ++hi)
        for (std::size_t bi = 0; bi < 2; ++bi) {
            min_d = std::min(min_d, d[hi][bi].direct / kRows);
            out.eta = std::max({out.eta,
                    std::fabs(d[hi][bi].direct - d[hi][bi].sufficient) / kRows,
                    std::fabs(a[hi][bi].direct - a[hi][bi].sufficient) / kRows});
            out.d_collisions += d[hi][bi].collisions;
            out.a_collisions += a[hi][bi].collisions;
            out.near_tie_same = out.near_tie_same && !d[hi][bi].ambiguity &&
                                !a[hi][bi].ambiguity;
            out.finite_nonnegative = out.finite_nonnegative &&
                    std::isfinite(d[hi][bi].direct) && d[hi][bi].direct >= 0 &&
                    std::isfinite(d[hi][bi].sufficient) &&
                    d[hi][bi].sufficient >= 0 && std::isfinite(a[hi][bi].direct) &&
                    a[hi][bi].direct >= 0 && std::isfinite(a[hi][bi].sufficient) &&
                    a[hi][bi].sufficient >= 0;
        }
    for (std::size_t bi = 0; bi < 2; ++bi) {
        out.eta = std::max({out.eta,
                std::fabs(p[bi].direct - p[bi].sufficient) / kRows,
                std::fabs(v[bi].direct - v[bi].sufficient) / kRows});
        out.p_collisions += p[bi].collisions;
        out.v_collisions += v[bi].collisions;
        out.finite_nonnegative = out.finite_nonnegative &&
                std::isfinite(p[bi].direct) && p[bi].direct >= 0 &&
                std::isfinite(p[bi].sufficient) && p[bi].sufficient >= 0 &&
                std::isfinite(v[bi].direct) && v[bi].direct >= 0 &&
                std::isfinite(v[bi].sufficient) && v[bi].sufficient >= 0;
        out.sensitivity_same = out.sensitivity_same &&
                decisions(d[0][bi].direct, a[0][bi].direct, p[bi].direct,
                          v[bi].direct) ==
                decisions(d[1][bi].direct, a[1][bi].direct, p[bi].direct,
                          v[bi].direct);
    }
    out.eta_limit = 0.0005 * min_d;
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
    out.peak_rss_bytes = std::uint64_t(usage.ru_maxrss) * 1024;
    out.wall_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - wall_start).count();
    if (!out.finite_nonnegative) out.failure = "finite_nonnegative";
    else if (out.d_collisions || out.a_collisions) out.failure = "AD_center_collision_zero";
    else if (!out.allocation_order_same) out.failure = "allocation_order";
    else if (!(std::isfinite(out.eta) && out.eta <= out.eta_limit)) out.failure = "eta";
    else if (!out.p_shape_valid) out.failure = "P_shape";
    else if (!out.v_shape_valid) out.failure = "V_shape";
    else if (out.p_collisions) out.failure = "P_center_collision_zero";
    else if (out.v_collisions) out.failure = "V_center_collision_zero";
    else if (out.p_nsplit) out.failure = "P_nsplit_zero";
    else if (out.v_nsplit) out.failure = "V_nsplit_zero";
    else if (!out.sensitivity_same) out.failure = "sensitivity";
    else if (!out.near_tie_same) out.failure = "near_tie";
    else if (out.peak_rss_bytes > 17179869184ULL) out.failure = "rss";
    out.passed = out.failure.empty();
    return out;
}

}  // namespace a4or

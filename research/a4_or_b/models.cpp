#include "models.hpp"

#include <faiss/Clustering.h>
#include <faiss/IndexFlat.h>

#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace a4orb {
namespace {

constexpr std::size_t kRows = kRowsPerSplit;
constexpr std::size_t kDimensions = kPanelDimensions;

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

std::size_t nearest(const float* point, const Block& block) {
    if (block.radix != 0) {
        const std::size_t k1 = block.radix;
        const std::size_t k2 = block.centers / k1;
        double best1 = std::numeric_limits<double>::infinity();
        double best2 = std::numeric_limits<double>::infinity();
        std::size_t z1 = 0, z2 = 0;
        for (std::size_t label = 0; label < k1; ++label) {
            const double delta =
                    static_cast<double>(point[0]) - block.values[2 * label];
            const double distance = delta * delta;
            if (distance < best1) best1 = distance, z1 = label;
        }
        for (std::size_t label = 0; label < k2; ++label) {
            const double delta = static_cast<double>(point[1]) -
                    block.values[2 * label * k1 + 1];
            const double distance = delta * delta;
            if (distance < best2) best2 = distance, z2 = label;
        }
        return a4or::pack(z1, z2, k1);
    }

    double best = std::numeric_limits<double>::infinity();
    std::size_t selected = 0;
    for (std::size_t center = 0; center < block.centers; ++center) {
        double distance = 0;
        const float* candidate =
                block.values.data() + center * block.dimension;
        for (std::size_t coordinate = 0;
             coordinate < block.dimension; ++coordinate) {
            const double delta = static_cast<double>(point[coordinate]) -
                    candidate[coordinate];
            distance += delta * delta;
        }
        if (distance < best) best = distance, selected = center;
    }
    return selected;
}

std::size_t collision_count(const Block& block) {
    std::size_t result = 0;
    for (std::size_t current = 0; current < block.centers; ++current) {
        for (std::size_t previous = 0; previous < current; ++previous) {
            bool equal = true;
            for (std::size_t coordinate = 0;
                 coordinate < block.dimension; ++coordinate) {
                equal = equal &&
                        std::bit_cast<std::uint32_t>(
                                block.values[current * block.dimension +
                                             coordinate]) ==
                        std::bit_cast<std::uint32_t>(
                                block.values[previous * block.dimension +
                                             coordinate]);
            }
            if (equal) {
                ++result;
                break;
            }
        }
    }
    return result;
}

faiss::Clustering configured(std::size_t dimension, std::size_t centers,
                             int seed, int redos) {
    faiss::Clustering clustering(dimension, centers);
    clustering.niter = 300;
    clustering.nredo = redos;
    clustering.seed = seed;
    clustering.min_points_per_centroid = 1;
    clustering.max_points_per_centroid = kRows;
    clustering.use_faster_subsampling = false;
    clustering.spherical = false;
    clustering.int_centroids = false;
    clustering.update_index = true;
    clustering.verbose = false;
    return clustering;
}

std::size_t split_count(const faiss::Clustering& clustering) {
    std::size_t result = 0;
    for (const auto& stat : clustering.iteration_stats) result += stat.nsplit;
    return result;
}

double fitting_sse(const std::vector<float>& points, const Block& block) {
    Sum result;
    for (std::size_t row = 0; row < kRows; ++row) {
        const float* point = points.data() + row * block.dimension;
        const std::size_t label = nearest(point, block);
        for (std::size_t coordinate = 0;
             coordinate < block.dimension; ++coordinate) {
            const double delta = static_cast<double>(point[coordinate]) -
                    block.values[label * block.dimension + coordinate];
            result.add(delta * delta);
        }
    }
    return result.get();
}

Block product_start(const std::vector<float>& points, const Block& arbitrary,
                    std::size_t target) {
    Block result = arbitrary;
    while (result.centers < target) {
        double farthest = -1;
        std::size_t chosen = 0;
        for (std::size_t row = 0; row < kRows; ++row) {
            const float* point = points.data() + 2 * row;
            const std::size_t label = nearest(point, result);
            double distance = 0;
            for (std::size_t coordinate = 0; coordinate < 2; ++coordinate) {
                const double delta = static_cast<double>(point[coordinate]) -
                        result.values[2 * label + coordinate];
                distance += delta * delta;
            }
            if (distance > farthest)
                farthest = distance, chosen = row;
        }
        result.values.push_back(points[2 * chosen]);
        result.values.push_back(points[2 * chosen + 1]);
        ++result.centers;
    }
    result.radix = 0;
    return result;
}

float table_distance(const float* query, const Block& block,
                     std::size_t center) {
    double distance = 0;
    const float* candidate =
            block.values.data() + center * block.dimension;
    for (std::size_t coordinate = 0;
         coordinate < block.dimension; ++coordinate) {
        const double delta = static_cast<double>(query[coordinate]) -
                candidate[coordinate];
        distance += delta * delta;
    }
    return static_cast<float>(distance);
}

}  // namespace

Curves fit_curves(const std::vector<float>& fit, std::size_t histogram_bins) {
    if (fit.size() != kRows * kDimensions)
        throw std::invalid_argument("fit panel shape");
    Curves result;
    result.histogram_bins = histogram_bins;
    result.coordinates.resize(kDimensions);
    std::vector<float> coordinate(kRows);
    for (std::size_t dimension = 0; dimension < kDimensions; ++dimension) {
        for (std::size_t row = 0; row < kRows; ++row)
            coordinate[row] = fit[row * kDimensions + dimension];
        result.coordinates[dimension] = a4or::scalar_curve(
                a4or::rank_histogram(coordinate.data(), kRows, histogram_bins),
                256);
    }
    return result;
}

Model allocate_scalar(const Curves& curves, int word_bits, bool dyadic) {
    if (curves.coordinates.size() != kDimensions)
        throw std::invalid_argument("curve shape");
    Model model;
    model.arm = dyadic ? 'D' : 'A';
    model.word_bits = word_bits;
    model.blocks.reserve(kGroups);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto allocation = a4or::allocate_pair(
                curves.coordinates[2 * group],
                curves.coordinates[2 * group + 1], word_bits, dyadic);
        Block block{2, allocation.used_states, allocation.k1, {},
                    allocation.ambiguity};
        const auto& first =
                curves.coordinates[2 * group][allocation.k1 - 1].centers;
        const auto& second =
                curves.coordinates[2 * group + 1][allocation.k2 - 1].centers;
        block.values.reserve(2 * block.centers);
        for (std::size_t z2 = 0; z2 < allocation.k2; ++z2) {
            for (std::size_t z1 = 0; z1 < allocation.k1; ++z1) {
                block.values.push_back(first[z1]);
                block.values.push_back(second[z2]);
            }
        }
        model.blocks.push_back(std::move(block));
    }
    return model;
}

Model train_p(const std::vector<float>& fit, int word_bits) {
    if (fit.size() != kRows * kDimensions)
        throw std::invalid_argument("fit panel shape");
    const a4or::ControlShape shape = a4or::control_shape(word_bits);
    Model model;
    model.arm = 'P';
    model.word_bits = word_bits;
    model.blocks.reserve(shape.pq_m);
    std::vector<float> points(kRows * shape.pq_dsub);
    for (std::size_t group = 0; group < shape.pq_m; ++group) {
        for (std::size_t row = 0; row < kRows; ++row) {
            std::copy_n(
                    fit.data() + row * kDimensions +
                            group * shape.pq_dsub,
                    shape.pq_dsub,
                    points.data() + row * shape.pq_dsub);
        }
        auto clustering = configured(
                shape.pq_dsub, shape.pq_ksub, shape.pq_seed, 8);
        faiss::IndexFlatL2 index(shape.pq_dsub);
        clustering.train(kRows, points.data(), index);
        model.training_splits += split_count(clustering);
        model.blocks.push_back(
                {shape.pq_dsub, shape.pq_ksub, 0,
                 std::move(clustering.centroids), false});
    }
    return model;
}

Model train_v(const std::vector<float>& fit, int word_bits,
              const Model& arbitrary) {
    if (fit.size() != kRows * kDimensions ||
        arbitrary.blocks.size() != kGroups)
        throw std::invalid_argument("V input shape");
    const std::size_t centers = std::size_t{1} << word_bits;
    Model model;
    model.arm = 'V';
    model.word_bits = word_bits;
    model.blocks.reserve(kGroups);
    std::vector<float> points(kRows * 2);
    for (std::size_t group = 0; group < kGroups; ++group) {
        for (std::size_t row = 0; row < kRows; ++row) {
            points[2 * row] = fit[row * kDimensions + 2 * group];
            points[2 * row + 1] =
                    fit[row * kDimensions + 2 * group + 1];
        }
        double best = std::numeric_limits<double>::infinity();
        Block winner;
        for (int redo = 0; redo < 8; ++redo) {
            auto clustering = configured(
                    2, centers,
                    20260722 + word_bits * 10000 +
                            static_cast<int>(group) * 8 + redo,
                    1);
            if (redo == 0)
                clustering.centroids =
                        product_start(points, arbitrary.blocks[group],
                                      centers)
                                .values;
            faiss::IndexFlatL2 index(2);
            clustering.train(kRows, points.data(), index);
            model.training_splits += split_count(clustering);
            Block candidate{
                    2, centers, 0, std::move(clustering.centroids), false};
            const double objective = fitting_sse(points, candidate);
            if (objective < best) {
                best = objective;
                winner = std::move(candidate);
            }
        }
        model.blocks.push_back(std::move(winner));
    }
    return model;
}

Evaluation evaluate(const std::vector<float>& panel, const Model& model) {
    Evaluation result;
    if (panel.size() != kRows * kDimensions) {
        result.shape_valid = false;
        result.encoding_valid = false;
        return result;
    }
    std::size_t total_dimensions = 0;
    for (const auto& block : model.blocks) {
        if (block.dimension == 0 || block.centers == 0 ||
            block.values.size() != block.dimension * block.centers ||
            (block.radix != 0 &&
             (block.dimension != 2 || block.centers % block.radix != 0)) ||
            total_dimensions + block.dimension > kDimensions) {
            result.shape_valid = false;
            result.encoding_valid = false;
            return result;
        }
        total_dimensions += block.dimension;
        result.collisions += collision_count(block);
        result.ambiguity = result.ambiguity || block.ambiguity;
    }
    if (total_dimensions != kDimensions) {
        result.shape_valid = false;
        result.encoding_valid = false;
        return result;
    }

    result.row_sse.assign(kRows, 0);
    result.group_sse.assign(kGroups, 0);
    result.codes.resize(kRows * model.blocks.size());
    std::size_t offset = 0;
    Sum all_direct, all_sufficient;
    for (std::size_t group = 0; group < model.blocks.size(); ++group) {
        const Block& block = model.blocks[group];
        std::vector<std::uint64_t> counts(block.centers);
        std::vector<Sum> sums(block.centers * block.dimension);
        std::vector<Sum> squares(block.centers * block.dimension);
        for (std::size_t row = 0; row < kRows; ++row) {
            const float* point = panel.data() + row * kDimensions + offset;
            const std::size_t label = nearest(point, block);
            if (label >= block.centers ||
                label > std::numeric_limits<std::uint16_t>::max()) {
                result.encoding_valid = false;
                continue;
            }
            result.codes[row * model.blocks.size() + group] =
                    static_cast<std::uint16_t>(label);
            ++result.encoded_labels;
            ++counts[label];
            for (std::size_t coordinate = 0;
                 coordinate < block.dimension; ++coordinate) {
                const double value = point[coordinate];
                const double center =
                        block.values[label * block.dimension + coordinate];
                const double delta = value - center;
                const double error = delta * delta;
                all_direct.add(error);
                result.row_sse[row] += error;
                result.group_sse[(offset + coordinate) / 2] += error;
                const std::size_t at = label * block.dimension + coordinate;
                sums[at].add(value);
                squares[at].add(value * value);
            }
        }
        for (std::size_t center = 0; center < block.centers; ++center) {
            result.empty_centers += counts[center] == 0;
            for (std::size_t coordinate = 0;
                 coordinate < block.dimension; ++coordinate) {
                const std::size_t at = center * block.dimension + coordinate;
                const double value =
                        block.values[center * block.dimension + coordinate];
                all_sufficient.add(
                        squares[at].get() - 2 * value * sums[at].get() +
                        counts[center] * value * value);
            }
        }
        offset += block.dimension;
    }
    result.direct_sse = all_direct.get();
    result.sufficient_sse = all_sufficient.get();
    result.encoding_valid = result.encoding_valid &&
            result.encoded_labels == kRows * model.blocks.size();
    return result;
}

PairEvaluation evaluate_pairs(const Panel& panel, const Model& model,
                              const Evaluation& heldout) {
    if (heldout.codes.size() !=
        kRows * model.blocks.size())
        throw std::invalid_argument("heldout code shape");
    PairEvaluation result;
    result.absolute_errors.reserve(panel.heldout_pairs);
    std::vector<float> table;
    for (std::size_t left = 0; left < panel.heldout_rows.size(); ++left) {
        if (panel.heldout_rows[left].pair_side != PairSide::Left) continue;
        const std::size_t right = left + 1;
        Sum truth, estimate;
        std::size_t offset = 0;
        for (std::size_t group = 0; group < model.blocks.size(); ++group) {
            const Block& block = model.blocks[group];
            const std::size_t entries =
                    block.radix == 0
                            ? block.centers
                            : (std::size_t{1} << model.word_bits);
            table.assign(entries, std::numeric_limits<float>::infinity());
            const float* query =
                    panel.heldout.data() + right * kDimensions + offset;
            for (std::size_t center = 0; center < block.centers; ++center)
                table[center] = table_distance(query, block, center);
            result.table_entries_built += entries;
            const std::size_t code =
                    heldout.codes[left * model.blocks.size() + group];
            if (code >= table.size() || !std::isfinite(table[code]))
                throw std::runtime_error("invalid lookup code");
            estimate.add(table[code]);
            const float* stored =
                    panel.heldout.data() + left * kDimensions + offset;
            for (std::size_t coordinate = 0;
                 coordinate < block.dimension; ++coordinate) {
                const double delta = static_cast<double>(query[coordinate]) -
                        stored[coordinate];
                truth.add(delta * delta);
            }
            offset += block.dimension;
        }
        result.absolute_errors.push_back(
                std::fabs(estimate.get() - truth.get()));
    }
    if (result.absolute_errors.size() != panel.heldout_pairs)
        throw std::runtime_error("pair count mismatch");
    return result;
}

std::size_t persistent_model_bytes(const Model& model) {
    std::size_t result = 0;
    for (const auto& block : model.blocks) {
        if (block.radix == 0) {
            result += block.values.size() * sizeof(float);
        } else {
            const std::size_t k1 = block.radix;
            const std::size_t k2 = block.centers / k1;
            result += (k1 + k2) * sizeof(float);
            result += 2 * sizeof(std::uint16_t);
        }
    }
    return result;
}

std::string model_shape(const Model& model) {
    std::ostringstream output;
    output << model.blocks.size() << 'x';
    if (model.blocks.empty()) return output.str() + "empty";
    output << model.blocks.front().dimension << 'd' << 'x'
           << model.blocks.front().centers;
    return output.str();
}

}  // namespace a4orb

#include "model.hpp"

#include <faiss/Clustering.h>
#include <faiss/IndexFlat.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace structured2d {
namespace {

constexpr std::size_t kRows = a4orb::kRowsPerSplit;
constexpr std::size_t kGroups = a4orb::kGroups;
constexpr std::size_t kDimensions = a4orb::kPanelDimensions;

AffineGroup fit_group_transform(const std::vector<float>& fit,
                                std::size_t group) {
    double mean0 = 0;
    double mean1 = 0;
    for (std::size_t row = 0; row < kRows; ++row) {
        mean0 += fit[row * kDimensions + 2 * group];
        mean1 += fit[row * kDimensions + 2 * group + 1];
    }
    mean0 /= kRows;
    mean1 /= kRows;

    double c00 = 0;
    double c01 = 0;
    double c11 = 0;
    for (std::size_t row = 0; row < kRows; ++row) {
        const double x0 = fit[row * kDimensions + 2 * group] - mean0;
        const double x1 = fit[row * kDimensions + 2 * group + 1] - mean1;
        c00 += x0 * x0;
        c01 += x0 * x1;
        c11 += x1 * x1;
    }
    c00 /= kRows;
    c01 /= kRows;
    c11 /= kRows;
    const double ridge =
            std::max((c00 + c11) * 1e-8, 1e-20);
    c00 += ridge;
    c11 += ridge;

    const double l00 = std::sqrt(c00);
    if (!(l00 > 0) || !std::isfinite(l00))
        throw std::runtime_error("invalid group covariance");
    const double l10 = c01 / l00;
    const double remaining = c11 - l10 * l10;
    if (!(remaining > 0) || !std::isfinite(remaining))
        throw std::runtime_error("singular group covariance");
    const double l11 = std::sqrt(remaining);

    AffineGroup result;
    result.mean[0] = static_cast<float>(mean0);
    result.mean[1] = static_cast<float>(mean1);
    result.transform[0] = static_cast<float>(l00);
    result.transform[1] = 0;
    result.transform[2] = static_cast<float>(l10);
    result.transform[3] = static_cast<float>(l11);
    return result;
}

void standardize(const std::vector<float>& fit,
                 const std::vector<AffineGroup>& groups,
                 std::vector<float>& pooled) {
    pooled.resize(kRows * kGroups * 2);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto& affine = groups[group];
        const double l00 = affine.transform[0];
        const double l10 = affine.transform[2];
        const double l11 = affine.transform[3];
        for (std::size_t row = 0; row < kRows; ++row) {
            const double x0 =
                    fit[row * kDimensions + 2 * group] - affine.mean[0];
            const double x1 =
                    fit[row * kDimensions + 2 * group + 1] - affine.mean[1];
            const std::size_t at = 2 * (group * kRows + row);
            pooled[at] = static_cast<float>(x0 / l00);
            pooled[at + 1] =
                    static_cast<float>((x1 - l10 * (x0 / l00)) / l11);
        }
    }
}

std::size_t split_count(const faiss::Clustering& clustering) {
    std::size_t result = 0;
    for (const auto& stat : clustering.iteration_stats) result += stat.nsplit;
    return result;
}

bool solve3(double matrix[3][3], double right[3], double result[3]) {
    for (std::size_t column = 0; column < 3; ++column) {
        std::size_t pivot = column;
        for (std::size_t row = column + 1; row < 3; ++row)
            if (std::fabs(matrix[row][column]) >
                std::fabs(matrix[pivot][column]))
                pivot = row;
        if (!(std::fabs(matrix[pivot][column]) >
              std::numeric_limits<double>::epsilon()))
            return false;
        if (pivot != column) {
            for (std::size_t at = column; at < 3; ++at)
                std::swap(matrix[column][at], matrix[pivot][at]);
            std::swap(right[column], right[pivot]);
        }
        for (std::size_t row = column + 1; row < 3; ++row) {
            const double factor =
                    matrix[row][column] / matrix[column][column];
            for (std::size_t at = column; at < 3; ++at)
                matrix[row][at] -= factor * matrix[column][at];
            right[row] -= factor * right[column];
        }
    }
    for (std::size_t reverse = 0; reverse < 3; ++reverse) {
        const std::size_t row = 2 - reverse;
        double value = right[row];
        for (std::size_t column = row + 1; column < 3; ++column)
            value -= matrix[row][column] * result[column];
        result[row] = value / matrix[row][row];
    }
    return std::all_of(result, result + 3, [](double value) {
        return std::isfinite(value);
    });
}

bool solve2(double a00, double a01, double a11, double b0, double b1,
            double& x0, double& x1) {
    const double determinant = a00 * a11 - a01 * a01;
    if (!(std::fabs(determinant) >
          std::numeric_limits<double>::epsilon()))
        return false;
    x0 = (a11 * b0 - a01 * b1) / determinant;
    x1 = (a00 * b1 - a01 * b0) / determinant;
    return std::isfinite(x0) && std::isfinite(x1);
}

void update_groups(const std::vector<float>& fit,
                   const std::vector<std::uint16_t>& codes,
                   const std::vector<float>& shape,
                   std::vector<AffineGroup>& groups) {
    for (std::size_t group = 0; group < kGroups; ++group) {
        double normal[3][3]{};
        double right0[3]{};
        double right1[3]{};
        for (std::size_t row = 0; row < kRows; ++row) {
            const std::size_t label = codes[row * kGroups + group];
            const double predictor[3]{
                    1, shape[2 * label], shape[2 * label + 1]};
            const double y0 = fit[row * kDimensions + 2 * group];
            const double y1 = fit[row * kDimensions + 2 * group + 1];
            for (std::size_t first = 0; first < 3; ++first) {
                right0[first] += predictor[first] * y0;
                right1[first] += predictor[first] * y1;
                for (std::size_t second = 0; second < 3; ++second)
                    normal[first][second] +=
                            predictor[first] * predictor[second];
            }
        }
        const double ridge =
                std::max((normal[1][1] + normal[2][2]) * 1e-12, 1e-20);
        normal[1][1] += ridge;
        normal[2][2] += ridge;
        double matrix0[3][3];
        double matrix1[3][3];
        for (std::size_t row = 0; row < 3; ++row)
            for (std::size_t column = 0; column < 3; ++column) {
                matrix0[row][column] = normal[row][column];
                matrix1[row][column] = normal[row][column];
            }
        double beta0[3]{};
        double beta1[3]{};
        if (!solve3(matrix0, right0, beta0) ||
            !solve3(matrix1, right1, beta1))
            throw std::runtime_error("singular affine regression");
        groups[group].mean[0] = static_cast<float>(beta0[0]);
        groups[group].mean[1] = static_cast<float>(beta1[0]);
        groups[group].transform[0] = static_cast<float>(beta0[1]);
        groups[group].transform[1] = static_cast<float>(beta0[2]);
        groups[group].transform[2] = static_cast<float>(beta1[1]);
        groups[group].transform[3] = static_cast<float>(beta1[2]);
    }
}

void update_shape(const std::vector<float>& fit,
                  const std::vector<std::uint16_t>& codes,
                  const std::vector<AffineGroup>& groups,
                  std::vector<float>& shape) {
    const std::size_t centers = shape.size() / 2;
    struct Normal {
        double a00 = 0;
        double a01 = 0;
        double a11 = 0;
        double b0 = 0;
        double b1 = 0;
        std::size_t count = 0;
    };
    std::vector<Normal> normals(centers);
    for (std::size_t group = 0; group < kGroups; ++group) {
        const auto& affine = groups[group];
        const double a00 = affine.transform[0];
        const double a01 = affine.transform[1];
        const double a10 = affine.transform[2];
        const double a11 = affine.transform[3];
        const double ata00 = a00 * a00 + a10 * a10;
        const double ata01 = a00 * a01 + a10 * a11;
        const double ata11 = a01 * a01 + a11 * a11;
        for (std::size_t row = 0; row < kRows; ++row) {
            const std::size_t label = codes[row * kGroups + group];
            auto& normal = normals[label];
            const double x0 = fit[row * kDimensions + 2 * group] -
                    affine.mean[0];
            const double x1 = fit[row * kDimensions + 2 * group + 1] -
                    affine.mean[1];
            normal.a00 += ata00;
            normal.a01 += ata01;
            normal.a11 += ata11;
            normal.b0 += a00 * x0 + a10 * x1;
            normal.b1 += a01 * x0 + a11 * x1;
            ++normal.count;
        }
    }
    for (std::size_t center = 0; center < centers; ++center) {
        auto normal = normals[center];
        if (normal.count == 0) continue;
        const double ridge =
                std::max((normal.a00 + normal.a11) * 1e-12, 1e-20);
        normal.a00 += ridge;
        normal.a11 += ridge;
        double z0 = 0;
        double z1 = 0;
        if (!solve2(normal.a00, normal.a01, normal.a11,
                    normal.b0, normal.b1, z0, z1))
            throw std::runtime_error("singular shared-shape regression");
        shape[2 * center] = static_cast<float>(z0);
        shape[2 * center + 1] = static_cast<float>(z1);
    }
}

}  // namespace

a4orb::Model expand(int word_bits, const std::vector<float>& shape,
                    const std::vector<AffineGroup>& groups) {
    if (word_bits <= 0 || word_bits > 8)
        throw std::invalid_argument("unsupported word bits");
    const std::size_t centers = std::size_t{1} << word_bits;
    if (shape.size() != 2 * centers || groups.size() != kGroups)
        throw std::invalid_argument("shared affine shape");

    a4orb::Model result;
    result.arm = 'S';
    result.word_bits = word_bits;
    result.blocks.reserve(kGroups);
    for (const auto& affine : groups) {
        a4orb::Block block{2, centers, 0, {}, false};
        block.values.reserve(2 * centers);
        for (std::size_t center = 0; center < centers; ++center) {
            const double z0 = shape[2 * center];
            const double z1 = shape[2 * center + 1];
            block.values.push_back(static_cast<float>(
                    affine.mean[0] + affine.transform[0] * z0 +
                    affine.transform[1] * z1));
            block.values.push_back(static_cast<float>(
                    affine.mean[1] + affine.transform[2] * z0 +
                    affine.transform[3] * z1));
        }
        result.blocks.push_back(std::move(block));
    }
    return result;
}

SharedAffineModel train(const std::vector<float>& fit, int word_bits) {
    if (fit.size() != kRows * kDimensions)
        throw std::invalid_argument("fit panel shape");
    if (word_bits != 4 && word_bits != 8)
        throw std::invalid_argument("registered rates are B4/B8");
    const std::size_t centers = std::size_t{1} << word_bits;

    SharedAffineModel result;
    result.word_bits = word_bits;
    result.groups.reserve(kGroups);
    for (std::size_t group = 0; group < kGroups; ++group)
        result.groups.push_back(fit_group_transform(fit, group));

    std::vector<float> pooled;
    standardize(fit, result.groups, pooled);
    faiss::Clustering clustering(2, centers);
    clustering.niter = 300;
    clustering.nredo = 8;
    clustering.seed = 20260723 + word_bits * 10000;
    clustering.min_points_per_centroid = 1;
    clustering.max_points_per_centroid = kRows;
    clustering.use_faster_subsampling = false;
    clustering.spherical = false;
    clustering.int_centroids = false;
    clustering.update_index = true;
    clustering.verbose = false;
    faiss::IndexFlatL2 index(2);
    clustering.train(kRows * kGroups, pooled.data(), index);
    result.training_splits = split_count(clustering);
    result.shape = std::move(clustering.centroids);
    result.expanded = expand(word_bits, result.shape, result.groups);
    result.expanded.training_splits = result.training_splits;
    if (!finite(result)) throw std::runtime_error("non-finite shared model");
    refine(fit, result, 20);
    return result;
}

void refine(const std::vector<float>& fit, SharedAffineModel& model,
            std::size_t maximum_iterations) {
    if (fit.size() != kRows * kDimensions ||
        model.shape.size() !=
                2 * (std::size_t{1} << model.word_bits) ||
        model.groups.size() != kGroups)
        throw std::invalid_argument("affine refinement shape");
    auto evaluation = a4orb::evaluate(fit, model.expanded);
    if (!evaluation.shape_valid || !evaluation.encoding_valid ||
        !std::isfinite(evaluation.direct_sse))
        throw std::runtime_error("invalid affine initialization");
    for (std::size_t iteration = 0;
         iteration < maximum_iterations; ++iteration) {
        SharedAffineModel candidate = model;
        update_groups(
                fit, evaluation.codes, candidate.shape, candidate.groups);
        update_shape(
                fit, evaluation.codes, candidate.groups, candidate.shape);
        candidate.expanded = expand(
                candidate.word_bits, candidate.shape, candidate.groups);
        candidate.expanded.training_splits = candidate.training_splits;
        if (!finite(candidate))
            throw std::runtime_error("non-finite affine refinement");
        auto candidate_evaluation =
                a4orb::evaluate(fit, candidate.expanded);
        if (!candidate_evaluation.shape_valid ||
            !candidate_evaluation.encoding_valid ||
            !std::isfinite(candidate_evaluation.direct_sse))
            throw std::runtime_error("invalid affine refinement");
        const double previous = evaluation.direct_sse;
        const double next = candidate_evaluation.direct_sse;
        if (next > previous + 1e-10 * std::max(1.0, previous))
            break;
        model = std::move(candidate);
        evaluation = std::move(candidate_evaluation);
        ++model.refinement_iterations;
        if (previous - next <= 1e-10 * std::max(1.0, previous))
            break;
    }
}

std::size_t persistent_model_bytes(const SharedAffineModel& model) {
    return (model.shape.size() + 6 * model.groups.size()) * sizeof(float);
}

std::size_t transient_expanded_bytes(const SharedAffineModel& model) {
    std::size_t values = 0;
    for (const auto& block : model.expanded.blocks)
        values += block.values.size();
    return values * sizeof(float);
}

bool finite(const SharedAffineModel& model) {
    const auto finite_value = [](float value) { return std::isfinite(value); };
    if (!std::all_of(model.shape.begin(), model.shape.end(), finite_value))
        return false;
    for (const auto& group : model.groups) {
        if (!std::all_of(group.mean, group.mean + 2, finite_value) ||
            !std::all_of(
                    group.transform, group.transform + 4, finite_value))
            return false;
    }
    for (const auto& block : model.expanded.blocks)
        if (!std::all_of(
                    block.values.begin(), block.values.end(), finite_value))
            return false;
    return true;
}

bool pooled_occupancy_valid(const a4orb::Model& model,
                            const a4orb::Evaluation& evaluation) {
    if (model.blocks.empty() ||
        evaluation.codes.size() !=
                kRows * model.blocks.size())
        return false;
    const std::size_t centers = model.blocks.front().centers;
    if (centers == 0 ||
        std::any_of(model.blocks.begin(), model.blocks.end(),
                    [&](const a4orb::Block& block) {
                        return block.centers != centers;
                    }))
        return false;
    std::vector<bool> used(centers);
    for (const auto code : evaluation.codes) {
        if (code >= centers) return false;
        used[code] = true;
    }
    return std::all_of(
            used.begin(), used.end(), [](bool value) { return value; });
}

}  // namespace structured2d

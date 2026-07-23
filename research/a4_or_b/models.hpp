#pragma once

#include "panel.hpp"

#include "../a4_or_c/core.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace a4orb {

struct Block {
    std::size_t dimension = 0;
    std::size_t centers = 0;
    std::size_t radix = 0;
    std::vector<float> values;
    bool ambiguity = false;
};

struct Model {
    char arm = '?';
    int word_bits = 0;
    std::vector<Block> blocks;
    std::size_t training_splits = 0;
};

struct Curves {
    std::size_t histogram_bins = 0;
    std::vector<std::vector<a4or::CurveEntry>> coordinates;
};

struct Evaluation {
    double direct_sse = 0;
    double sufficient_sse = 0;
    std::vector<double> row_sse;
    std::vector<double> group_sse;
    std::vector<std::uint16_t> codes;
    std::size_t encoded_labels = 0;
    std::size_t empty_centers = 0;
    std::size_t collisions = 0;
    bool shape_valid = true;
    bool encoding_valid = true;
    bool ambiguity = false;
};

struct PairEvaluation {
    std::vector<double> absolute_errors;
    std::uint64_t table_entries_built = 0;
};

Curves fit_curves(const std::vector<float>& fit, std::size_t histogram_bins);
Model allocate_scalar(const Curves& curves, int word_bits, bool dyadic);
Model train_p(const std::vector<float>& fit, int word_bits);
Model train_v(const std::vector<float>& fit, int word_bits,
              const Model& arbitrary);
Evaluation evaluate(const std::vector<float>& panel, const Model& model);
PairEvaluation evaluate_pairs(const Panel& panel, const Model& model,
                              const Evaluation& heldout);
std::size_t persistent_model_bytes(const Model& model);
std::string model_shape(const Model& model);

}  // namespace a4orb

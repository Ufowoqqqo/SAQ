#pragma once

#include "../a4_or_b/models.hpp"

#include <cstddef>
#include <vector>

namespace structured2d {

struct AffineGroup {
    float mean[2]{};
    // Row-major full 2x2 affine linear map.
    float transform[4]{};
};

struct RefinementStep {
    std::size_t iteration = 0;
    double fit_sse = 0;
    double relative_improvement = 0;
};

struct SharedAffineModel {
    int word_bits = 0;
    std::vector<float> shape;
    std::vector<AffineGroup> groups;
    a4orb::Model expanded;
    std::size_t training_splits = 0;
    std::size_t refinement_iterations = 0;
    std::vector<RefinementStep> fit_trace;
    bool converged = false;
    bool stopped_nonmonotonic = false;
};

SharedAffineModel train(const std::vector<float>& fit, int word_bits);
void refine(const std::vector<float>& fit, SharedAffineModel& model,
            std::size_t maximum_total_iterations,
            double relative_tolerance = 0,
            std::size_t required_consecutive = 0);
a4orb::Model expand(int word_bits, const std::vector<float>& shape,
                    const std::vector<AffineGroup>& groups);
std::size_t persistent_model_bytes(const SharedAffineModel& model);
std::size_t transient_expanded_bytes(const SharedAffineModel& model);
bool finite(const SharedAffineModel& model);
bool pooled_occupancy_valid(const a4orb::Model& model,
                            const a4orb::Evaluation& evaluation);

}  // namespace structured2d

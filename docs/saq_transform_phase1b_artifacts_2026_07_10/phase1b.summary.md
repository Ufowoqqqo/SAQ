# SAQ Phase-1 transform evidence summary

This report is descriptive evidence for reviewing the PCA/SAQ mismatch hypothesis. It does not make an automatic novelty or contribution claim.

## Inference contract

- Baseline: `current_pca`.
- Internal-rotation seeds `0..9` are averaged within each query before inference; the `off` control is reported separately.
- The paired 95% percentile bootstrap resamples queries (10000 replicates, global seed 20260710). SHA-256-derived comparison sub-seeds and NumPy 1.23.5 `default_rng` make intervals stable to unrelated output additions. Candidates and seeds are not treated as independent units.
- Every reported difference is `transform - current_pca`. Lower is better for RMSE, MAE, boundary inversion, and exact-best rank; higher is better for top-k agreement.
- Two RMSE estimands are kept separate: `mean_per_query_candidate_rmse` gives queries equal weight after averaging rotation repeats within query; `pooled_candidate_rmse` reconstructs SSE as `candidate_count * RMSE^2` and recomputes each arm's square root inside every query bootstrap replicate.
- `vars_conservative_lower_bound_all` is a conservative bound diagnostic, not an ordinary unbiased distance estimator.
- Dominance is only a partial diagnostic comparison of mean metrics, logical requested bytes, and serialized index bytes. Serialized bytes omit the outer transform artifact; logical bytes omit query transform, centroid, LUT, and other complete-work costs. It is not a statistical, complete-Pareto, or novelty conclusion.

Inputs: `current_pca` (`/tmp/saq-phase1b-cifar60k/results/current`), `residual_pca` (`/tmp/saq-phase1b-cifar60k/results/residual`)

Machine-readable outputs:

- `phase1b.stage_curves.csv`: all individual prefix stages against logical bytes.
- `phase1b.paired_vs_pca.csv`: common endpoints plus strictly byte-matched intermediate prefixes, with paired differences and confidence intervals.
- `phase1b.per_seed_effects.csv`: descriptive seed-by-seed effects for stability review.
- `phase1b.config_summary.csv`: actual serialized bytes, plans, and construction metadata.
- `phase1b.segment_proxy.csv`: low-n segment proxy/error Spearman agreement.

## Actual index bytes and plans

| Transform | Plan control | Rotation | Segments | Serialized bytes | Bytes/vector | Plan |
|---|---|---:|---:|---:|---:|---|
| current_pca | frozen-pca | seed_average | 4 | 2.151e+07 | 358.4699 | 0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b |
| current_pca | frozen-pca | off | 4 | 2.121e+07 | 353.5547 | 0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b |
| residual_pca | frozen-pca | seed_average | 4 | 2.151e+07 | 358.4699 | 0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b |
| residual_pca | frozen-pca | off | 4 | 2.121e+07 | 353.5547 | 0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b |

## Paired matched-stage evidence versus PCA

CI cells show mean difference and `[95% CI]`; the final tag states whether the interval favors the transform, favors PCA, or includes zero.

| Transform | Plan | Rotation | Stage | Matched budget | Δmean-query RMSE | Δpooled RMSE | ΔTop-k agreement | ΔBoundary inversion | Mean relation |
|---|---|---|---|---|---:|---:|---:|---:|---|
| residual_pca | frozen-pca | seed_average | vars_conservative_lower_bound_all | True | -4.786e-04 [-0.0010, 3.995e-05] (includes_zero) | -4.429e-04 [-9.691e-04, 8.786e-05] (includes_zero) | 0.0020 [9.897e-04, 0.0031] (favors_transform) | -0.0023 [-0.0029, -0.0016] (favors_transform) | not_applicable_conservative_bound |
| residual_pca | frozen-pca | seed_average | fast_prefix_1 | True | 4.178e-04 [3.192e-04, 5.174e-04] (favors_pca) | 4.190e-04 [3.196e-04, 5.208e-04] (favors_pca) | -3.790e-04 [-0.0013, 5.670e-04] (includes_zero) | 5.676e-06 [-1.319e-04, 1.423e-04] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | fast_prefix_2 | True | 5.602e-05 [1.751e-05, 9.358e-05] (favors_pca) | 5.477e-05 [1.733e-05, 9.309e-05] (favors_pca) | -1.090e-04 [-0.0010, 8.070e-04] (includes_zero) | -2.764e-06 [-1.211e-04, 1.146e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | fast_prefix_3 | True | 4.230e-05 [5.052e-06, 7.897e-05] (favors_pca) | 4.127e-05 [2.544e-06, 8.066e-05] (favors_pca) | -9.700e-05 [-0.0010, 8.450e-04] (includes_zero) | -9.536e-06 [-1.334e-04, 1.079e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | fast_all | True | 4.230e-05 [5.373e-06, 7.956e-05] (favors_pca) | 4.127e-05 [3.609e-06, 7.982e-05] (favors_pca) | -9.700e-05 [-0.0010, 8.630e-04] (includes_zero) | -9.536e-06 [-1.264e-04, 1.100e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | accurate_prefix_1 | True | 1.394e-06 [-2.216e-05, 2.461e-05] (includes_zero) | 2.030e-06 [-2.233e-05, 2.638e-05] (includes_zero) | -1.350e-04 [-6.680e-04, 4.010e-04] (includes_zero) | 2.931e-06 [-1.218e-05, 1.828e-05] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | accurate_prefix_2 | True | 2.947e-06 [6.004e-07, 5.216e-06] (favors_pca) | 1.415e-06 [-1.020e-06, 3.890e-06] (includes_zero) | -8.300e-05 [-3.160e-04, 1.490e-04] (includes_zero) | 4.810e-07 [-8.650e-07, 1.820e-06] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | accurate_prefix_3 | True | 2.158e-06 [7.354e-07, 3.586e-06] (favors_pca) | 1.948e-06 [4.445e-07, 3.434e-06] (favors_pca) | 1.100e-05 [-1.520e-04, 1.730e-04] (includes_zero) | 1.571e-07 [-3.369e-07, 6.500e-07] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | full | True | -2.610e-07 [-1.043e-06, 5.094e-07] (includes_zero) | -2.310e-07 [-1.045e-06, 5.840e-07] (includes_zero) | -1.200e-05 [-1.730e-04, 1.510e-04] (includes_zero) | 1.606e-07 [-3.256e-07, 6.599e-07] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | vars_conservative_lower_bound_all | True | -4.786e-04 [-9.965e-04, 4.063e-05] (includes_zero) | -4.429e-04 [-9.618e-04, 7.783e-05] (includes_zero) | 0.0020 [0.0010, 0.0030] (favors_transform) | -0.0023 [-0.0029, -0.0016] (favors_transform) | not_applicable_conservative_bound |
| residual_pca | frozen-pca | off | fast_prefix_1 | True | 4.060e-04 [2.790e-04, 5.328e-04] (favors_pca) | 4.098e-04 [2.765e-04, 5.399e-04] (favors_pca) | -2.400e-04 [-0.0031, 0.0026] (includes_zero) | -1.474e-04 [-6.078e-04, 2.994e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | fast_prefix_2 | True | 6.622e-05 [-3.030e-05, 1.623e-04] (includes_zero) | 6.704e-05 [-2.901e-05, 1.608e-04] (includes_zero) | 7.600e-04 [-0.0020, 0.0036] (includes_zero) | -1.356e-04 [-5.444e-04, 2.637e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | fast_prefix_3 | True | 5.222e-05 [-4.377e-05, 1.487e-04] (includes_zero) | 5.365e-05 [-4.341e-05, 1.504e-04] (includes_zero) | -1.000e-05 [-0.0027, 0.0027] (includes_zero) | -1.470e-04 [-5.524e-04, 2.521e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | fast_all | True | 5.222e-05 [-4.319e-05, 1.507e-04] (includes_zero) | 5.365e-05 [-4.151e-05, 1.499e-04] (includes_zero) | -1.000e-05 [-0.0028, 0.0028] (includes_zero) | -1.470e-04 [-5.376e-04, 2.569e-04] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | accurate_prefix_1 | True | 1.152e-05 [-2.019e-05, 4.282e-05] (includes_zero) | 1.324e-05 [-2.009e-05, 4.762e-05] (includes_zero) | 1.600e-04 [-0.0012, 0.0015] (includes_zero) | -1.510e-05 [-5.141e-05, 2.193e-05] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | accurate_prefix_2 | True | 3.269e-06 [-4.438e-07, 7.010e-06] (includes_zero) | 2.609e-06 [-1.286e-06, 6.568e-06] (includes_zero) | 4.000e-04 [-2.300e-04, 0.0010] (includes_zero) | -1.389e-06 [-4.651e-06, 1.894e-06] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | accurate_prefix_3 | True | 3.272e-06 [7.522e-07, 5.729e-06] (favors_pca) | 3.545e-06 [9.077e-07, 6.164e-06] (favors_pca) | 2.400e-04 [-3.200e-04, 7.900e-04] (includes_zero) | 4.489e-07 [-1.341e-06, 2.248e-06] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | full | True | 9.886e-07 [-1.098e-06, 3.057e-06] (includes_zero) | 1.484e-06 [-6.822e-07, 3.663e-06] (includes_zero) | 2.000e-04 [-3.700e-04, 7.700e-04] (includes_zero) | 4.416e-07 [-1.346e-06, 2.245e-06] (includes_zero) | tradeoff |

## Planner proxy versus measured segment error

Spearman values below are descriptive only. Segment counts are the effective sample sizes and are generally too small for inferential claims; ties or a single uniform segment produce `NA`. The CSV additionally reports seedwise rho min/median/max and sign counts for distance RMSE and implied-IP MAE.

| Transform | Plan | Rotation | n segments | Support | ρ(transform proxy, distance RMSE) | ρ(transform proxy, IP RMSE) |
|---|---|---|---:|---|---:|---:|
| current_pca | frozen-pca | seed_average | 4 | low_support | 1.0000 | 1.0000 |
| current_pca | frozen-pca | off | 4 | low_support | 0.8000 | 0.8000 |
| residual_pca | frozen-pca | seed_average | 4 | low_support | 1.0000 | 1.0000 |
| residual_pca | frozen-pca | off | 4 | low_support | 0.8000 | 0.8000 |

## Data-quality notes

- Complete matched query sets were available for every reported comparison.

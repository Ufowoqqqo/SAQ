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

Inputs: `current_pca` (`/tmp/saq-phase1-transform/results/current_pca`), `identity` (`/tmp/saq-phase1-transform/results/identity`), `residual_pca` (`/tmp/saq-phase1-transform/results/residual_pca`), `random_orthogonal` (`/tmp/saq-phase1-transform/results/random_orthogonal`)

Machine-readable outputs:

- `phase1.stage_curves.csv`: all individual prefix stages against logical bytes.
- `phase1.paired_vs_pca.csv`: common endpoints plus strictly byte-matched intermediate prefixes, with paired differences and confidence intervals.
- `phase1.per_seed_effects.csv`: descriptive seed-by-seed effects for stability review.
- `phase1.config_summary.csv`: actual serialized bytes, plans, and construction metadata.
- `phase1.segment_proxy.csv`: low-n segment proxy/error Spearman agreement.

## Actual index bytes and plans

| Transform | Plan control | Rotation | Segments | Serialized bytes | Bytes/vector | Plan |
|---|---|---:|---:|---:|---:|---|
| current_pca | native | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| current_pca | native | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| current_pca | frozen-pca | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| current_pca | frozen-pca | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| current_pca | uniform | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| current_pca | uniform | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |
| identity | native | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| identity | native | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |
| identity | frozen-pca | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| identity | frozen-pca | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| identity | uniform | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| identity | uniform | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |
| residual_pca | native | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| residual_pca | native | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| residual_pca | frozen-pca | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| residual_pca | frozen-pca | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| residual_pca | uniform | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| residual_pca | uniform | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |
| random_orthogonal | native | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| random_orthogonal | native | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |
| random_orthogonal | frozen-pca | seed_average | 5 | 3.420e+07 | 684.0258 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| random_orthogonal | frozen-pca | off | 5 | 3.330e+07 | 666.0034 | 0:64@11b\|64:256@6b\|256:576@4b\|576:832@2b\|832:960@0b |
| random_orthogonal | uniform | seed_average | 1 | 3.401e+07 | 680.2622 | 0:960@4b |
| random_orthogonal | uniform | off | 1 | 3.033e+07 | 606.5342 | 0:960@4b |

## Paired matched-stage evidence versus PCA

CI cells show mean difference and `[95% CI]`; the final tag states whether the interval favors the transform, favors PCA, or includes zero.

| Transform | Plan | Rotation | Stage | Matched budget | Δmean-query RMSE | Δpooled RMSE | ΔTop-k agreement | ΔBoundary inversion | Mean relation |
|---|---|---|---|---|---:|---:|---:|---:|---|
| identity | native | seed_average | vars_conservative_lower_bound_all | False | -1.3026 [-1.3776, -1.2281] (favors_transform) | -1.3054 [-1.3784, -1.2346] (favors_transform) | 0.1657 [0.1505, 0.1813] (favors_transform) | -0.0903 [-0.1005, -0.0805] (favors_transform) | not_applicable_conservative_bound |
| identity | native | seed_average | fast_all | False | -0.2638 [-0.2772, -0.2511] (favors_transform) | -0.2637 [-0.2761, -0.2518] (favors_transform) | 0.2492 [0.2443, 0.2543] (favors_transform) | -0.0167 [-0.0175, -0.0160] (favors_transform) | transform_partially_dominates_pca |
| identity | native | seed_average | full | False | 0.0067 [0.0064, 0.0070] (favors_pca) | 0.0066 [0.0063, 0.0069] (favors_pca) | -0.0180 [-0.0190, -0.0171] (favors_pca) | 5.430e-05 [4.956e-05, 5.912e-05] (favors_pca) | tradeoff |
| identity | native | off | vars_conservative_lower_bound_all | False | -1.3026 [-1.3785, -1.2296] (favors_transform) | -1.3054 [-1.3772, -1.2370] (favors_transform) | 0.1657 [0.1503, 0.1814] (favors_transform) | -0.0903 [-0.1004, -0.0804] (favors_transform) | not_applicable_conservative_bound |
| identity | native | off | fast_all | False | -0.2141 [-0.2289, -0.1993] (favors_transform) | -0.2157 [-0.2305, -0.2015] (favors_transform) | 0.1216 [0.1095, 0.1332] (favors_transform) | -0.0135 [-0.0149, -0.0121] (favors_transform) | transform_partially_dominates_pca |
| identity | native | off | full | False | 0.0115 [0.0110, 0.0122] (favors_pca) | 0.0114 [0.0108, 0.0120] (favors_pca) | -0.0290 [-0.0315, -0.0265] (favors_pca) | 1.316e-04 [1.145e-04, 1.501e-04] (favors_pca) | tradeoff |
| identity | frozen-pca | seed_average | vars_conservative_lower_bound_all | True | -0.7753 [-0.8381, -0.7174] (favors_transform) | -0.7839 [-0.8437, -0.7267] (favors_transform) | 0.1623 [0.1466, 0.1783] (favors_transform) | -0.0864 [-0.0966, -0.0766] (favors_transform) | not_applicable_conservative_bound |
| identity | frozen-pca | seed_average | fast_prefix_1 | True | 0.4803 [0.4594, 0.5023] (favors_pca) | 0.4680 [0.4481, 0.4882] (favors_pca) | -0.2875 [-0.3023, -0.2721] (favors_pca) | 0.1077 [0.0992, 0.1169] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | fast_prefix_2 | True | 0.4179 [0.4012, 0.4342] (favors_pca) | 0.4091 [0.3930, 0.4255] (favors_pca) | -0.1808 [-0.1971, -0.1643] (favors_pca) | 0.0541 [0.0480, 0.0608] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | fast_prefix_3 | True | 0.2278 [0.2152, 0.2410] (favors_pca) | 0.2235 [0.2103, 0.2377] (favors_pca) | 0.0126 [-0.0061, 0.0306] (includes_zero) | 0.0090 [0.0052, 0.0133] (favors_pca) | tradeoff |
| identity | frozen-pca | seed_average | fast_prefix_4 | True | 0.0026 [-0.0052, 0.0105] (includes_zero) | 4.934e-04 [-0.0073, 0.0086] (includes_zero) | 0.1684 [0.1560, 0.1798] (favors_transform) | -0.0120 [-0.0132, -0.0106] (favors_transform) | tradeoff |
| identity | frozen-pca | seed_average | fast_all | True | 0.0026 [-0.0052, 0.0107] (includes_zero) | 4.934e-04 [-0.0073, 0.0087] (includes_zero) | 0.1684 [0.1562, 0.1798] (favors_transform) | -0.0120 [-0.0132, -0.0106] (favors_transform) | tradeoff |
| identity | frozen-pca | seed_average | accurate_prefix_1 | True | 0.2831 [0.2716, 0.2952] (favors_pca) | 0.2776 [0.2662, 0.2902] (favors_pca) | -0.1377 [-0.1493, -0.1269] (favors_pca) | 0.0060 [0.0051, 0.0071] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | accurate_prefix_2 | True | 0.2959 [0.2838, 0.3087] (favors_pca) | 0.2948 [0.2818, 0.3082] (favors_pca) | -0.1915 [-0.2031, -0.1807] (favors_pca) | 0.0062 [0.0052, 0.0072] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | accurate_prefix_3 | True | 0.2548 [0.2430, 0.2672] (favors_pca) | 0.2567 [0.2438, 0.2703] (favors_pca) | -0.1874 [-0.2008, -0.1751] (favors_pca) | 0.0054 [0.0044, 0.0065] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | accurate_prefix_4 | True | 0.2009 [0.1911, 0.2115] (favors_pca) | 0.2032 [0.1924, 0.2151] (favors_pca) | -0.1772 [-0.1912, -0.1640] (favors_pca) | 0.0051 [0.0041, 0.0062] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | seed_average | full | True | 0.0660 [0.0621, 0.0703] (favors_pca) | 0.0676 [0.0630, 0.0726] (favors_pca) | -0.1778 [-0.1918, -0.1646] (favors_pca) | 0.0052 [0.0042, 0.0063] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | vars_conservative_lower_bound_all | True | -0.7753 [-0.8350, -0.7168] (favors_transform) | -0.7839 [-0.8423, -0.7268] (favors_transform) | 0.1623 [0.1465, 0.1782] (favors_transform) | -0.0864 [-0.0966, -0.0764] (favors_transform) | not_applicable_conservative_bound |
| identity | frozen-pca | off | fast_prefix_1 | True | 0.4714 [0.4508, 0.4930] (favors_pca) | 0.4593 [0.4386, 0.4801] (favors_pca) | -0.2404 [-0.2547, -0.2261] (favors_pca) | 0.1001 [0.0918, 0.1088] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | fast_prefix_2 | True | 0.4075 [0.3894, 0.4257] (favors_pca) | 0.3998 [0.3816, 0.4185] (favors_pca) | -0.1497 [-0.1664, -0.1332] (favors_pca) | 0.0518 [0.0455, 0.0583] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | fast_prefix_3 | True | 0.2258 [0.2087, 0.2434] (favors_pca) | 0.2232 [0.2057, 0.2414] (favors_pca) | 0.0025 [-0.0162, 0.0207] (includes_zero) | 0.0112 [0.0068, 0.0159] (favors_pca) | tradeoff |
| identity | frozen-pca | off | fast_prefix_4 | True | 0.0122 [8.933e-05, 0.0240] (favors_pca) | 0.0093 [-0.0035, 0.0219] (includes_zero) | 0.0930 [0.0780, 0.1073] (favors_transform) | -0.0090 [-0.0110, -0.0069] (favors_transform) | tradeoff |
| identity | frozen-pca | off | fast_all | True | 0.0122 [-7.270e-05, 0.0243] (includes_zero) | 0.0093 [-0.0033, 0.0219] (includes_zero) | 0.0930 [0.0783, 0.1072] (favors_transform) | -0.0090 [-0.0110, -0.0069] (favors_transform) | tradeoff |
| identity | frozen-pca | off | accurate_prefix_1 | True | 0.3020 [0.2893, 0.3162] (favors_pca) | 0.2957 [0.2821, 0.3104] (favors_pca) | -0.2387 [-0.2520, -0.2252] (favors_pca) | 0.0152 [0.0136, 0.0169] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | accurate_prefix_2 | True | 0.3119 [0.2993, 0.3256] (favors_pca) | 0.3097 [0.2964, 0.3237] (favors_pca) | -0.2613 [-0.2742, -0.2495] (favors_pca) | 0.0114 [0.0100, 0.0129] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | accurate_prefix_3 | True | 0.2603 [0.2496, 0.2725] (favors_pca) | 0.2608 [0.2490, 0.2742] (favors_pca) | -0.2108 [-0.2243, -0.1980] (favors_pca) | 0.0070 [0.0057, 0.0084] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | accurate_prefix_4 | True | 0.2022 [0.1928, 0.2126] (favors_pca) | 0.2043 [0.1937, 0.2159] (favors_pca) | -0.1835 [-0.1973, -0.1703] (favors_pca) | 0.0053 [0.0043, 0.0065] (favors_pca) | pca_partially_dominates_transform |
| identity | frozen-pca | off | full | True | 0.0677 [0.0636, 0.0722] (favors_pca) | 0.0693 [0.0646, 0.0744] (favors_pca) | -0.1830 [-0.1972, -0.1696] (favors_pca) | 0.0054 [0.0044, 0.0065] (favors_pca) | pca_partially_dominates_transform |
| identity | uniform | seed_average | vars_conservative_lower_bound_all | True | -1.6112 [-1.7224, -1.5064] (favors_transform) | -1.6427 [-1.7532, -1.5329] (favors_transform) | 0.1720 [0.1495, 0.1947] (favors_transform) | 0.0966 [0.0840, 0.1094] (favors_pca) | not_applicable_conservative_bound |
| identity | uniform | seed_average | fast_all | True | 2.288e-06 [-9.564e-05, 9.523e-05] (includes_zero) | 2.268e-05 [-7.289e-05, 1.165e-04] (includes_zero) | -4.531e-04 [-0.0024, 0.0015] (includes_zero) | 3.285e-05 [-1.313e-05, 7.845e-05] (includes_zero) | tradeoff |
| identity | uniform | seed_average | full | True | 8.782e-05 [7.904e-05, 9.678e-05] (favors_pca) | 8.442e-05 [7.527e-05, 9.368e-05] (favors_pca) | -1.875e-04 [-8.203e-04, 4.531e-04] (includes_zero) | 1.693e-06 [-5.799e-07, 4.041e-06] (includes_zero) | pca_partially_dominates_transform |
| identity | uniform | off | vars_conservative_lower_bound_all | True | -1.6112 [-1.7237, -1.5068] (favors_transform) | -1.6427 [-1.7577, -1.5328] (favors_transform) | 0.1720 [0.1497, 0.1952] (favors_transform) | 0.0966 [0.0838, 0.1095] (favors_pca) | not_applicable_conservative_bound |
| identity | uniform | off | fast_all | True | -0.0547 [-0.0607, -0.0487] (favors_transform) | -0.0536 [-0.0595, -0.0480] (favors_transform) | 0.2338 [0.2208, 0.2463] (favors_transform) | -0.0485 [-0.0525, -0.0448] (favors_transform) | transform_partially_dominates_pca |
| identity | uniform | off | full | True | -0.0499 [-0.0523, -0.0476] (favors_transform) | -0.0491 [-0.0513, -0.0470] (favors_transform) | 0.1284 [0.1221, 0.1345] (favors_transform) | -0.0030 [-0.0033, -0.0028] (favors_transform) | transform_partially_dominates_pca |
| residual_pca | native | seed_average | vars_conservative_lower_bound_all | True | 0.0054 [0.0019, 0.0096] (favors_pca) | 0.0054 [0.0015, 0.0102] (favors_pca) | -4.609e-04 [-0.0023, 0.0013] (includes_zero) | 4.061e-04 [-4.997e-04, 0.0014] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | native | seed_average | fast_prefix_1 | True | 6.151e-04 [-2.151e-04, 0.0014] (includes_zero) | 6.309e-04 [-1.797e-04, 0.0015] (includes_zero) | -0.0028 [-0.0055, 3.125e-05] (includes_zero) | 1.800e-04 [-6.434e-05, 4.319e-04] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | seed_average | fast_prefix_2 | True | 7.586e-04 [5.218e-04, 9.992e-04] (favors_pca) | 7.831e-04 [5.536e-04, 0.0010] (favors_pca) | -0.0032 [-0.0063, -1.641e-04] (favors_pca) | 2.426e-04 [1.343e-05, 4.714e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | native | seed_average | fast_prefix_3 | True | 6.600e-04 [4.309e-04, 8.988e-04] (favors_pca) | 6.904e-04 [4.611e-04, 9.296e-04] (favors_pca) | -0.0037 [-0.0067, -7.029e-04] (favors_pca) | 2.375e-04 [1.763e-05, 4.646e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | native | seed_average | fast_prefix_4 | True | 6.398e-04 [4.080e-04, 8.813e-04] (favors_pca) | 6.691e-04 [4.399e-04, 9.040e-04] (favors_pca) | -0.0033 [-0.0063, -3.516e-04] (favors_pca) | 2.281e-04 [4.002e-06, 4.589e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | native | seed_average | fast_all | True | 6.398e-04 [4.093e-04, 8.777e-04] (favors_pca) | 6.691e-04 [4.361e-04, 9.058e-04] (favors_pca) | -0.0033 [-0.0063, -4.061e-04] (favors_pca) | 2.281e-04 [4.162e-06, 4.528e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | native | seed_average | accurate_prefix_1 | True | -4.922e-04 [-6.882e-04, -2.920e-04] (favors_transform) | -5.342e-04 [-7.507e-04, -3.067e-04] (favors_transform) | 0.0013 [-6.250e-05, 0.0026] (includes_zero) | -1.737e-05 [-3.706e-05, 1.304e-06] (includes_zero) | transform_partially_dominates_pca |
| residual_pca | native | seed_average | accurate_prefix_2 | True | -2.052e-05 [-4.277e-05, 2.499e-06] (includes_zero) | -2.895e-05 [-5.757e-05, -8.089e-07] (favors_transform) | 3.281e-04 [-2.969e-04, 9.687e-04] (includes_zero) | 2.448e-07 [-2.047e-06, 2.600e-06] (includes_zero) | tradeoff |
| residual_pca | native | seed_average | accurate_prefix_3 | True | -2.372e-06 [-7.718e-06, 3.055e-06] (includes_zero) | -3.443e-06 [-1.076e-05, 4.504e-06] (includes_zero) | 2.344e-04 [-1.953e-04, 6.641e-04] (includes_zero) | -6.363e-08 [-5.649e-07, 4.578e-07] (includes_zero) | tradeoff |
| residual_pca | native | seed_average | accurate_prefix_4 | True | -2.842e-06 [-6.668e-06, 9.272e-07] (includes_zero) | -2.956e-06 [-7.132e-06, 1.315e-06] (includes_zero) | 1.953e-04 [-1.641e-04, 5.625e-04] (includes_zero) | 2.227e-08 [-2.701e-07, 3.268e-07] (includes_zero) | tradeoff |
| residual_pca | native | seed_average | full | True | -5.572e-06 [-8.552e-06, -2.675e-06] (favors_transform) | -5.479e-06 [-8.814e-06, -2.094e-06] (favors_transform) | 1.406e-04 [-2.187e-04, 4.922e-04] (includes_zero) | 4.541e-08 [-2.416e-07, 3.449e-07] (includes_zero) | tradeoff |
| residual_pca | native | off | vars_conservative_lower_bound_all | True | 0.0054 [0.0019, 0.0097] (favors_pca) | 0.0054 [0.0015, 0.0100] (favors_pca) | -4.688e-04 [-0.0023, 0.0013] (includes_zero) | 4.062e-04 [-4.990e-04, 0.0013] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | native | off | fast_prefix_1 | True | 2.334e-04 [-0.0012, 0.0016] (includes_zero) | -3.114e-05 [-0.0015, 0.0013] (includes_zero) | 0.0025 [-0.0055, 0.0105] (includes_zero) | 7.183e-04 [-3.076e-04, 0.0018] (includes_zero) | tradeoff |
| residual_pca | native | off | fast_prefix_2 | True | 3.877e-04 [-7.309e-04, 0.0014] (includes_zero) | 1.417e-04 [-0.0010, 0.0012] (includes_zero) | -7.031e-04 [-0.0084, 0.0070] (includes_zero) | 9.700e-04 [-2.658e-05, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | off | fast_prefix_3 | True | 2.830e-04 [-7.862e-04, 0.0013] (includes_zero) | 3.432e-05 [-0.0011, 0.0011] (includes_zero) | -0.0033 [-0.0110, 0.0046] (includes_zero) | 9.838e-04 [-1.538e-05, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | off | fast_prefix_4 | True | 2.627e-04 [-8.232e-04, 0.0013] (includes_zero) | 1.223e-05 [-0.0011, 0.0011] (includes_zero) | -0.0045 [-0.0123, 0.0035] (includes_zero) | 9.775e-04 [-1.792e-05, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | off | fast_all | True | 2.627e-04 [-8.049e-04, 0.0013] (includes_zero) | 1.223e-05 [-0.0011, 0.0011] (includes_zero) | -0.0045 [-0.0122, 0.0034] (includes_zero) | 9.775e-04 [-8.753e-06, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | off | accurate_prefix_1 | True | -5.611e-04 [-8.204e-04, -2.932e-04] (favors_transform) | -5.816e-04 [-8.904e-04, -2.429e-04] (favors_transform) | -8.594e-04 [-0.0047, 0.0030] (includes_zero) | -2.463e-05 [-8.570e-05, 3.426e-05] (includes_zero) | tradeoff |
| residual_pca | native | off | accurate_prefix_2 | True | -4.399e-05 [-8.403e-05, -5.999e-06] (favors_transform) | -7.032e-05 [-1.149e-04, -2.585e-05] (favors_transform) | 7.813e-04 [-0.0010, 0.0026] (includes_zero) | 1.747e-06 [-4.778e-06, 8.435e-06] (includes_zero) | tradeoff |
| residual_pca | native | off | accurate_prefix_3 | True | 4.348e-06 [-9.773e-06, 1.917e-05] (includes_zero) | 2.400e-06 [-1.876e-05, 2.406e-05] (includes_zero) | -7.031e-04 [-0.0022, 7.813e-04] (includes_zero) | 1.283e-06 [-4.638e-07, 3.055e-06] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | native | off | accurate_prefix_4 | True | 2.041e-06 [-7.063e-06, 1.105e-05] (includes_zero) | 3.455e-06 [-8.490e-06, 1.523e-05] (includes_zero) | -7.813e-04 [-0.0020, 4.688e-04] (includes_zero) | 1.765e-06 [3.984e-07, 3.123e-06] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | native | off | full | True | -1.097e-06 [-9.264e-06, 6.746e-06] (includes_zero) | 3.420e-07 [-9.366e-06, 1.002e-05] (includes_zero) | -9.375e-04 [-0.0022, 3.125e-04] (includes_zero) | 1.855e-06 [4.733e-07, 3.246e-06] (favors_pca) | tradeoff |
| residual_pca | frozen-pca | seed_average | vars_conservative_lower_bound_all | True | 0.0054 [0.0019, 0.0095] (favors_pca) | 0.0054 [0.0015, 0.0103] (favors_pca) | -4.609e-04 [-0.0023, 0.0013] (includes_zero) | 4.061e-04 [-4.854e-04, 0.0013] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | frozen-pca | seed_average | fast_prefix_1 | True | 6.151e-04 [-2.243e-04, 0.0014] (includes_zero) | 6.309e-04 [-2.128e-04, 0.0014] (includes_zero) | -0.0028 [-0.0056, 3.906e-05] (includes_zero) | 1.800e-04 [-6.536e-05, 4.332e-04] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | fast_prefix_2 | True | 7.586e-04 [5.252e-04, 0.0010] (favors_pca) | 7.831e-04 [5.523e-04, 0.0010] (favors_pca) | -0.0032 [-0.0062, -1.250e-04] (favors_pca) | 2.426e-04 [1.328e-05, 4.783e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | fast_prefix_3 | True | 6.600e-04 [4.288e-04, 8.958e-04] (favors_pca) | 6.904e-04 [4.630e-04, 9.234e-04] (favors_pca) | -0.0037 [-0.0067, -6.875e-04] (favors_pca) | 2.375e-04 [1.944e-05, 4.590e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | fast_prefix_4 | True | 6.398e-04 [4.041e-04, 8.782e-04] (favors_pca) | 6.691e-04 [4.366e-04, 9.104e-04] (favors_pca) | -0.0033 [-0.0063, -4.531e-04] (favors_pca) | 2.281e-04 [1.482e-06, 4.556e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | fast_all | True | 6.398e-04 [4.096e-04, 8.815e-04] (favors_pca) | 6.691e-04 [4.380e-04, 9.053e-04] (favors_pca) | -0.0033 [-0.0063, -4.141e-04] (favors_pca) | 2.281e-04 [5.082e-06, 4.587e-04] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | seed_average | accurate_prefix_1 | True | -4.922e-04 [-6.897e-04, -2.928e-04] (favors_transform) | -5.342e-04 [-7.515e-04, -3.034e-04] (favors_transform) | 0.0013 [-7.812e-05, 0.0026] (includes_zero) | -1.737e-05 [-3.707e-05, 1.591e-06] (includes_zero) | transform_partially_dominates_pca |
| residual_pca | frozen-pca | seed_average | accurate_prefix_2 | True | -2.052e-05 [-4.337e-05, 1.706e-06] (includes_zero) | -2.895e-05 [-5.736e-05, -1.443e-06] (favors_transform) | 3.281e-04 [-3.047e-04, 9.687e-04] (includes_zero) | 2.448e-07 [-2.139e-06, 2.571e-06] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | accurate_prefix_3 | True | -2.372e-06 [-7.761e-06, 2.937e-06] (includes_zero) | -3.443e-06 [-1.073e-05, 4.676e-06] (includes_zero) | 2.344e-04 [-2.031e-04, 6.719e-04] (includes_zero) | -6.363e-08 [-5.540e-07, 4.401e-07] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | accurate_prefix_4 | True | -2.842e-06 [-6.605e-06, 9.711e-07] (includes_zero) | -2.956e-06 [-7.085e-06, 1.322e-06] (includes_zero) | 1.953e-04 [-1.719e-04, 5.549e-04] (includes_zero) | 2.227e-08 [-2.683e-07, 3.202e-07] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | seed_average | full | True | -5.572e-06 [-8.446e-06, -2.685e-06] (favors_transform) | -5.479e-06 [-8.800e-06, -2.139e-06] (favors_transform) | 1.406e-04 [-2.109e-04, 4.922e-04] (includes_zero) | 4.541e-08 [-2.451e-07, 3.419e-07] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | vars_conservative_lower_bound_all | True | 0.0054 [0.0020, 0.0095] (favors_pca) | 0.0054 [0.0015, 0.0101] (favors_pca) | -4.688e-04 [-0.0023, 0.0013] (includes_zero) | 4.062e-04 [-4.842e-04, 0.0013] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | frozen-pca | off | fast_prefix_1 | True | 2.334e-04 [-0.0012, 0.0016] (includes_zero) | -3.114e-05 [-0.0014, 0.0014] (includes_zero) | 0.0025 [-0.0054, 0.0106] (includes_zero) | 7.183e-04 [-3.152e-04, 0.0018] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | fast_prefix_2 | True | 3.877e-04 [-6.965e-04, 0.0014] (includes_zero) | 1.417e-04 [-0.0010, 0.0012] (includes_zero) | -7.031e-04 [-0.0082, 0.0070] (includes_zero) | 9.700e-04 [-2.197e-05, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | fast_prefix_3 | True | 2.830e-04 [-8.118e-04, 0.0013] (includes_zero) | 3.432e-05 [-0.0011, 0.0011] (includes_zero) | -0.0033 [-0.0111, 0.0047] (includes_zero) | 9.838e-04 [-1.292e-05, 0.0020] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | fast_prefix_4 | True | 2.627e-04 [-8.074e-04, 0.0013] (includes_zero) | 1.223e-05 [-0.0011, 0.0011] (includes_zero) | -0.0045 [-0.0123, 0.0034] (includes_zero) | 9.775e-04 [2.889e-06, 0.0020] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | fast_all | True | 2.627e-04 [-8.168e-04, 0.0013] (includes_zero) | 1.223e-05 [-0.0011, 0.0011] (includes_zero) | -0.0045 [-0.0124, 0.0033] (includes_zero) | 9.775e-04 [7.011e-06, 0.0020] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | accurate_prefix_1 | True | -5.611e-04 [-8.291e-04, -2.784e-04] (favors_transform) | -5.816e-04 [-8.901e-04, -2.398e-04] (favors_transform) | -8.594e-04 [-0.0047, 0.0029] (includes_zero) | -2.463e-05 [-8.437e-05, 3.490e-05] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | accurate_prefix_2 | True | -4.399e-05 [-8.469e-05, -4.922e-06] (favors_transform) | -7.032e-05 [-1.153e-04, -2.656e-05] (favors_transform) | 7.813e-04 [-0.0010, 0.0027] (includes_zero) | 1.747e-06 [-4.843e-06, 8.544e-06] (includes_zero) | tradeoff |
| residual_pca | frozen-pca | off | accurate_prefix_3 | True | 4.348e-06 [-9.827e-06, 1.905e-05] (includes_zero) | 2.400e-06 [-1.944e-05, 2.420e-05] (includes_zero) | -7.031e-04 [-0.0023, 7.813e-04] (includes_zero) | 1.283e-06 [-4.183e-07, 3.070e-06] (includes_zero) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | accurate_prefix_4 | True | 2.041e-06 [-6.993e-06, 1.101e-05] (includes_zero) | 3.455e-06 [-8.498e-06, 1.500e-05] (includes_zero) | -7.813e-04 [-0.0020, 4.688e-04] (includes_zero) | 1.765e-06 [4.267e-07, 3.137e-06] (favors_pca) | pca_partially_dominates_transform |
| residual_pca | frozen-pca | off | full | True | -1.097e-06 [-9.148e-06, 7.032e-06] (includes_zero) | 3.420e-07 [-9.398e-06, 1.024e-05] (includes_zero) | -9.375e-04 [-0.0022, 3.125e-04] (includes_zero) | 1.855e-06 [4.951e-07, 3.242e-06] (favors_pca) | tradeoff |
| residual_pca | uniform | seed_average | vars_conservative_lower_bound_all | True | -0.0046 [-0.0142, 0.0046] (includes_zero) | -0.0056 [-0.0149, 0.0035] (includes_zero) | 8.594e-04 [-0.0029, 0.0045] (includes_zero) | 3.542e-04 [-0.0015, 0.0023] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | uniform | seed_average | fast_all | True | -7.617e-05 [-1.652e-04, 7.654e-06] (includes_zero) | -5.687e-05 [-1.448e-04, 2.935e-05] (includes_zero) | -1.250e-04 [-0.0020, 0.0017] (includes_zero) | -8.946e-07 [-4.481e-05, 4.288e-05] (includes_zero) | tradeoff |
| residual_pca | uniform | seed_average | full | True | 5.481e-07 [-9.058e-06, 9.793e-06] (includes_zero) | -3.666e-07 [-1.037e-05, 9.782e-06] (includes_zero) | -2.109e-04 [-9.846e-04, 5.547e-04] (includes_zero) | 1.099e-06 [-1.761e-06, 3.905e-06] (includes_zero) | tradeoff |
| residual_pca | uniform | off | vars_conservative_lower_bound_all | True | -0.0046 [-0.0140, 0.0046] (includes_zero) | -0.0056 [-0.0151, 0.0036] (includes_zero) | 8.594e-04 [-0.0029, 0.0045] (includes_zero) | 3.542e-04 [-0.0016, 0.0023] (includes_zero) | not_applicable_conservative_bound |
| residual_pca | uniform | off | fast_all | True | -1.129e-04 [-4.735e-04, 2.099e-04] (includes_zero) | -1.765e-04 [-5.704e-04, 1.828e-04] (includes_zero) | -0.0040 [-0.0089, 9.395e-04] (includes_zero) | 8.232e-04 [8.493e-05, 0.0016] (favors_pca) | tradeoff |
| residual_pca | uniform | off | full | True | 7.377e-04 [4.104e-04, 0.0011] (favors_pca) | 7.625e-04 [4.238e-04, 0.0011] (favors_pca) | -0.0056 [-0.0101, -0.0010] (favors_pca) | 3.427e-04 [1.621e-04, 5.334e-04] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | native | seed_average | vars_conservative_lower_bound_all | False | -1.3083 [-1.3856, -1.2331] (favors_transform) | -1.3098 [-1.3827, -1.2371] (favors_transform) | 0.1645 [0.1491, 0.1803] (favors_transform) | -0.0905 [-0.1005, -0.0804] (favors_transform) | not_applicable_conservative_bound |
| random_orthogonal | native | seed_average | fast_all | False | -0.2637 [-0.2769, -0.2508] (favors_transform) | -0.2637 [-0.2759, -0.2517] (favors_transform) | 0.2500 [0.2448, 0.2552] (favors_transform) | -0.0168 [-0.0175, -0.0160] (favors_transform) | transform_partially_dominates_pca |
| random_orthogonal | native | seed_average | full | False | 0.0067 [0.0064, 0.0070] (favors_pca) | 0.0066 [0.0063, 0.0069] (favors_pca) | -0.0182 [-0.0192, -0.0172] (favors_pca) | 5.423e-05 [4.921e-05, 5.942e-05] (favors_pca) | tradeoff |
| random_orthogonal | native | off | vars_conservative_lower_bound_all | False | -1.3083 [-1.3864, -1.2333] (favors_transform) | -1.3098 [-1.3828, -1.2390] (favors_transform) | 0.1645 [0.1492, 0.1802] (favors_transform) | -0.0905 [-0.1007, -0.0804] (favors_transform) | not_applicable_conservative_bound |
| random_orthogonal | native | off | fast_all | False | -0.2762 [-0.2900, -0.2633] (favors_transform) | -0.2758 [-0.2888, -0.2633] (favors_transform) | 0.2950 [0.2840, 0.3056] (favors_transform) | -0.0246 [-0.0259, -0.0234] (favors_transform) | transform_partially_dominates_pca |
| random_orthogonal | native | off | full | False | 0.0064 [0.0061, 0.0067] (favors_pca) | 0.0063 [0.0060, 0.0066] (favors_pca) | -0.0180 [-0.0200, -0.0162] (favors_pca) | 5.317e-05 [4.676e-05, 5.979e-05] (favors_pca) | tradeoff |
| random_orthogonal | frozen-pca | seed_average | vars_conservative_lower_bound_all | True | -0.7660 [-0.8274, -0.7066] (favors_transform) | -0.7711 [-0.8295, -0.7140] (favors_transform) | 0.1615 [0.1460, 0.1768] (favors_transform) | -0.0907 [-0.1010, -0.0806] (favors_transform) | not_applicable_conservative_bound |
| random_orthogonal | frozen-pca | seed_average | fast_prefix_1 | True | 0.4769 [0.4547, 0.4990] (favors_pca) | 0.4680 [0.4462, 0.4903] (favors_pca) | -0.2750 [-0.2891, -0.2607] (favors_pca) | 0.1000 [0.0921, 0.1083] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | fast_prefix_2 | True | 0.4240 [0.4071, 0.4415] (favors_pca) | 0.4161 [0.3998, 0.4332] (favors_pca) | -0.1579 [-0.1722, -0.1435] (favors_pca) | 0.0436 [0.0396, 0.0477] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | fast_prefix_3 | True | 0.2083 [0.1985, 0.2183] (favors_pca) | 0.2033 [0.1942, 0.2128] (favors_pca) | 0.0956 [0.0866, 0.1046] (favors_transform) | -0.0066 [-0.0073, -0.0058] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | seed_average | fast_prefix_4 | True | 3.720e-04 [-0.0049, 0.0057] (includes_zero) | -0.0016 [-0.0064, 0.0033] (includes_zero) | 0.2261 [0.2207, 0.2314] (favors_transform) | -0.0159 [-0.0166, -0.0151] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | seed_average | fast_all | True | 3.720e-04 [-0.0049, 0.0057] (includes_zero) | -0.0016 [-0.0063, 0.0033] (includes_zero) | 0.2261 [0.2207, 0.2314] (favors_transform) | -0.0159 [-0.0166, -0.0151] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | seed_average | accurate_prefix_1 | True | 0.2767 [0.2668, 0.2873] (favors_pca) | 0.2709 [0.2614, 0.2808] (favors_pca) | -0.0791 [-0.0827, -0.0755] (favors_pca) | 0.0023 [0.0021, 0.0024] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | accurate_prefix_2 | True | 0.2909 [0.2799, 0.3024] (favors_pca) | 0.2877 [0.2775, 0.2986] (favors_pca) | -0.1341 [-0.1385, -0.1295] (favors_pca) | 0.0026 [0.0024, 0.0028] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | accurate_prefix_3 | True | 0.2430 [0.2340, 0.2524] (favors_pca) | 0.2411 [0.2324, 0.2499] (favors_pca) | -0.1262 [-0.1310, -0.1213] (favors_pca) | 0.0019 [0.0018, 0.0020] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | accurate_prefix_4 | True | 0.1900 [0.1834, 0.1970] (favors_pca) | 0.1888 [0.1824, 0.1956] (favors_pca) | -0.1141 [-0.1191, -0.1090] (favors_pca) | 0.0016 [0.0015, 0.0017] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | seed_average | full | True | 0.0463 [0.0441, 0.0487] (favors_pca) | 0.0461 [0.0440, 0.0483] (favors_pca) | -0.1191 [-0.1232, -0.1151] (favors_pca) | 0.0017 [0.0016, 0.0018] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | vars_conservative_lower_bound_all | True | -0.7660 [-0.8260, -0.7077] (favors_transform) | -0.7711 [-0.8314, -0.7164] (favors_transform) | 0.1615 [0.1466, 0.1771] (favors_transform) | -0.0907 [-0.1010, -0.0807] (favors_transform) | not_applicable_conservative_bound |
| random_orthogonal | frozen-pca | off | fast_prefix_1 | True | 0.4678 [0.4460, 0.4902] (favors_pca) | 0.4591 [0.4376, 0.4808] (favors_pca) | -0.2259 [-0.2397, -0.2119] (favors_pca) | 0.0914 [0.0839, 0.0993] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | fast_prefix_2 | True | 0.4124 [0.3957, 0.4294] (favors_pca) | 0.4049 [0.3886, 0.4215] (favors_pca) | -0.1120 [-0.1255, -0.0977] (favors_pca) | 0.0356 [0.0319, 0.0395] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | fast_prefix_3 | True | 0.1959 [0.1865, 0.2055] (favors_pca) | 0.1913 [0.1822, 0.2007] (favors_pca) | 0.1434 [0.1320, 0.1548] (favors_transform) | -0.0147 [-0.0158, -0.0135] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | off | fast_prefix_4 | True | -0.0122 [-0.0177, -0.0067] (favors_transform) | -0.0137 [-0.0189, -0.0086] (favors_transform) | 0.2734 [0.2632, 0.2835] (favors_transform) | -0.0238 [-0.0250, -0.0225] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | off | fast_all | True | -0.0122 [-0.0175, -0.0066] (favors_transform) | -0.0137 [-0.0188, -0.0087] (favors_transform) | 0.2734 [0.2633, 0.2836] (favors_transform) | -0.0238 [-0.0250, -0.0225] (favors_transform) | tradeoff |
| random_orthogonal | frozen-pca | off | accurate_prefix_1 | True | 0.2751 [0.2652, 0.2852] (favors_pca) | 0.2693 [0.2600, 0.2792] (favors_pca) | -0.0741 [-0.0798, -0.0683] (favors_pca) | 0.0020 [0.0019, 0.0022] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | accurate_prefix_2 | True | 0.2906 [0.2798, 0.3021] (favors_pca) | 0.2874 [0.2773, 0.2980] (favors_pca) | -0.1309 [-0.1368, -0.1250] (favors_pca) | 0.0025 [0.0023, 0.0027] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | accurate_prefix_3 | True | 0.2429 [0.2337, 0.2521] (favors_pca) | 0.2409 [0.2325, 0.2500] (favors_pca) | -0.1251 [-0.1309, -0.1191] (favors_pca) | 0.0019 [0.0017, 0.0021] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | accurate_prefix_4 | True | 0.1897 [0.1830, 0.1968] (favors_pca) | 0.1885 [0.1821, 0.1952] (favors_pca) | -0.1125 [-0.1177, -0.1073] (favors_pca) | 0.0016 [0.0015, 0.0017] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | frozen-pca | off | full | True | 0.0460 [0.0438, 0.0483] (favors_pca) | 0.0457 [0.0437, 0.0480] (favors_pca) | -0.1173 [-0.1216, -0.1130] (favors_pca) | 0.0017 [0.0016, 0.0018] (favors_pca) | pca_partially_dominates_transform |
| random_orthogonal | uniform | seed_average | vars_conservative_lower_bound_all | True | -1.6169 [-1.7237, -1.5116] (favors_transform) | -1.6470 [-1.7574, -1.5394] (favors_transform) | 0.1709 [0.1486, 0.1937] (favors_transform) | 0.0964 [0.0834, 0.1093] (favors_pca) | not_applicable_conservative_bound |
| random_orthogonal | uniform | seed_average | fast_all | True | 6.559e-05 [-1.672e-05, 1.453e-04] (includes_zero) | 7.866e-05 [-6.645e-06, 1.607e-04] (includes_zero) | 2.891e-04 [-0.0015, 0.0021] (includes_zero) | -1.937e-06 [-4.836e-05, 4.564e-05] (includes_zero) | tradeoff |
| random_orthogonal | uniform | seed_average | full | True | 8.314e-05 [7.343e-05, 9.323e-05] (favors_pca) | 8.030e-05 [7.085e-05, 9.027e-05] (favors_pca) | -3.359e-04 [-0.0010, 3.672e-04] (includes_zero) | 1.625e-06 [-9.107e-07, 4.338e-06] (includes_zero) | pca_partially_dominates_transform |
| random_orthogonal | uniform | off | vars_conservative_lower_bound_all | True | -1.6169 [-1.7293, -1.5066] (favors_transform) | -1.6470 [-1.7601, -1.5401] (favors_transform) | 0.1709 [0.1485, 0.1937] (favors_transform) | 0.0964 [0.0840, 0.1093] (favors_pca) | not_applicable_conservative_bound |
| random_orthogonal | uniform | off | fast_all | True | -0.1168 [-0.1233, -0.1109] (favors_transform) | -0.1138 [-0.1198, -0.1082] (favors_transform) | 0.4072 [0.3922, 0.4227] (favors_transform) | -0.0596 [-0.0639, -0.0555] (favors_transform) | transform_partially_dominates_pca |
| random_orthogonal | uniform | off | full | True | -0.0550 [-0.0578, -0.0524] (favors_transform) | -0.0542 [-0.0567, -0.0518] (favors_transform) | 0.1393 [0.1334, 0.1452] (favors_transform) | -0.0031 [-0.0033, -0.0029] (favors_transform) | transform_partially_dominates_pca |

## Planner proxy versus measured segment error

Spearman values below are descriptive only. Segment counts are the effective sample sizes and are generally too small for inferential claims; ties or a single uniform segment produce `NA`. The CSV additionally reports seedwise rho min/median/max and sign counts for distance RMSE and implied-IP MAE.

| Transform | Plan | Rotation | n segments | Support | ρ(transform proxy, distance RMSE) | ρ(transform proxy, IP RMSE) |
|---|---|---|---:|---|---:|---:|
| current_pca | native | seed_average | 5 | descriptive_only | 0.9000 | 0.9000 |
| current_pca | native | off | 5 | descriptive_only | 0.9000 | 0.9000 |
| current_pca | frozen-pca | seed_average | 5 | descriptive_only | 0.9000 | 0.9000 |
| current_pca | frozen-pca | off | 5 | descriptive_only | 0.9000 | 0.9000 |
| current_pca | uniform | seed_average | 1 | insufficient_n | NA | NA |
| current_pca | uniform | off | 1 | insufficient_n | NA | NA |
| identity | native | seed_average | 1 | insufficient_n | NA | NA |
| identity | native | off | 1 | insufficient_n | NA | NA |
| identity | frozen-pca | seed_average | 5 | descriptive_only | 1.0000 | 1.0000 |
| identity | frozen-pca | off | 5 | descriptive_only | 1.0000 | 1.0000 |
| identity | uniform | seed_average | 1 | insufficient_n | NA | NA |
| identity | uniform | off | 1 | insufficient_n | NA | NA |
| residual_pca | native | seed_average | 5 | descriptive_only | 0.9000 | 0.9000 |
| residual_pca | native | off | 5 | descriptive_only | 0.9000 | 0.9000 |
| residual_pca | frozen-pca | seed_average | 5 | descriptive_only | 0.9000 | 0.9000 |
| residual_pca | frozen-pca | off | 5 | descriptive_only | 0.9000 | 0.9000 |
| residual_pca | uniform | seed_average | 1 | insufficient_n | NA | NA |
| residual_pca | uniform | off | 1 | insufficient_n | NA | NA |
| random_orthogonal | native | seed_average | 1 | insufficient_n | NA | NA |
| random_orthogonal | native | off | 1 | insufficient_n | NA | NA |
| random_orthogonal | frozen-pca | seed_average | 5 | descriptive_only | 1.0000 | 1.0000 |
| random_orthogonal | frozen-pca | off | 5 | descriptive_only | 1.0000 | 1.0000 |
| random_orthogonal | uniform | seed_average | 1 | insufficient_n | NA | NA |
| random_orthogonal | uniform | off | 1 | insufficient_n | NA | NA |

## Data-quality notes

- Complete matched query sets were available for every reported comparison.

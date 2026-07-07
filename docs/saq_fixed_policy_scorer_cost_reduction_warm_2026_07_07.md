# SAQ Fixed-Policy Scorer Cost Evaluation

Date: 2026-07-07

This report evaluates whether cheaper data-only scorer sampling settings preserve the fixed-policy decisions.

## Scope

- Candidate sets are fixed from the existing default-neighborhood matrix.
- No index is built and no held-out query labels are used for selection.
- `risky_fallback_best_score` is mapped to `reject`, following the fixed-policy interpretation.

## Decision Stability

| preset | runs | decision matches | plan matches | total runtime s |
|---|---:|---:|---:|---:|
| a1024_p2_grid_endpoints_cached_features | 10 | 10/10 | 10/10 | 5.656 |

## Cost-Reduction Summary

- Total measured scorer runtime: 5.656 s.
- Reference scorer runtime from the overhead table: 481.764 s.
- Runtime ratio vs reference: 0.012.
- Feature-cache statuses: 8 hits, 0 cold misses.
- Measured residual-risk time in this run: 0.000 s.
- Measured tail-risk time in this run: 0.000 s.
- Measured boundary-pair sampling time in this run: 0.000 s.
- Measured scoring-grid time in this run: 0.057 s.

## Per-Run Results

| run | preset | decision | baseline | selected plan | plan match | pairs | pair ratio | configs | config ratio | cache | pair sample s | grid s | runtime s | runtime ratio |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| gist_full_K4096_B3 | a1024_p2_grid_endpoints_cached_features | promote | promote | `64:8,320:5,320:2,256:0` | True | 2048 | 0.139 | 64 | 0.005 | hit |  | 0.006 | 1.541 | 0.011 |
| gist_full_K4096_B4 | a1024_p2_grid_endpoints_cached_features | promote | promote | `128:9,320:5,320:3,192:0` | True | 2048 | 0.139 | 160 | 0.005 | hit |  | 0.011 | 1.584 | 0.011 |
| gist_full_K4096_B5 | a1024_p2_grid_endpoints_cached_features | promote | promote | `128:9,128:7,320:5,320:3,64:0` | True | 2048 | 0.139 | 160 | 0.005 | hit |  | 0.011 | 1.625 | 0.011 |
| cifar60k_B3 | a1024_p2_grid_endpoints_cached_features | promote | promote | `128:6,64:4,192:2,128:0` | True | 534 | 0.500 | 128 | 0.005 | hit |  | 0.008 | 0.186 | 0.022 |
| cifar60k_B4 | a1024_p2_grid_endpoints_cached_features | promote | promote | `128:7,256:4,128:0` | True | 534 | 0.500 | 128 | 0.005 | hit |  | 0.008 | 0.189 | 0.022 |
| cifar60k_B5 | a1024_p2_grid_endpoints_cached_features | promote | promote | `128:8,64:6,256:4,64:0` | True | 534 | 0.500 | 128 | 0.005 | hit |  | 0.007 | 0.190 | 0.023 |
| deep1M_sample100k_B4 | a1024_p2_grid_endpoints_cached_features | reject | reject | `128:4,128:3` | True | 952 | 0.500 | 64 | 0.005 | hit |  | 0.003 | 0.169 | 0.030 |
| deep1M_sample100k_B5 | a1024_p2_grid_endpoints_cached_features | reject | reject | `128:5,128:4` | True | 952 | 0.500 | 64 | 0.005 | hit |  | 0.003 | 0.171 | 0.030 |
| audio_K4096_B4 | a1024_p2_grid_endpoints_cached_features | abstain | abstain | `` | True |  |  |  |  |  |  |  | 0.000 |  |
| word2vec_sample100k_B4 | a1024_p2_grid_endpoints_cached_features | abstain | abstain | `` | True |  |  |  |  |  |  |  | 0.000 |  |

## Interpretation

A useful cheap scorer should preserve the promote/reject/abstain decision and preferably the selected plan. If decision stability fails, the sampling setting is too aggressive for the current policy.

The current stable calibration point is `a1024_p2`: it preserves every fixed-policy decision and selected plan in the checked matrix. Smaller representative settings can preserve the decision while changing the GIST B=4 selected plan, so they are not stable enough for exact-plan reproduction.

Pair-count reduction alone does not fully solve scorer overhead. In the full matrix, `a1024_p2` reduces GIST sampling from 14,740 pairs to 2,048 pairs, but scorer runtime remains close to the full scorer. This indicates that the next cost-reduction target should be cached residual/tail features or a smaller scoring grid, not only fewer sampled pairs.

The endpoint grid preset is a scorer-grid reduction evaluation, not a new selection rule. It keeps the boundary-risk endpoints that selected the current matrix plans and should be checked by exact decision/plan stability before use.

The feature cache is a data-only reuse mechanism keyed by dataset, IVF setting, sampling parameters, residual-risk statistic, and tail-risk quantile. It does not use held-out query labels. Its main benefit is avoiding repeated residual/tail feature computation across B values for the same dataset/K/sampling setting.

## Output Tables

```text
docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.csv
docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.json
```

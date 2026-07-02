# Boundary-Aware Residual DP Extension Prototype

Date: 2026-07-02

## 1. Motivation

The residual-aware DP prototype improved mean relative error on `gist_sample100k`, but the first custom plan also showed a small recall regression:

```text
residual_aggressive = 64:9,256:6,256:4,256:2,128:0
```

The later conservative sweep showed that moving one bit from the first 64 dimensions into the next 64 dimensions can recover recall:

```text
eq_s0_to_s1 = 64:8,64:7,192:6,256:4,256:2,128:0
```

This suggests that the residual-only objective was too focused on average residual variance and did not sufficiently protect recall-sensitive segment boundaries, especially around the first 128 PCA dimensions.

The goal here is to keep the method query-unaware, but make the offline planner less aggressive by adding boundary and tail-risk terms to the DP objective.

## 2. Extension Idea

The original residual-aware DP uses a per-dimension residual risk vector:

```text
r_j = pooled centered residual variance of dimension j inside IVF cells
```

This prototype builds a boundary-risk vector from three query-unaware signals:

```text
b_j = (1 - lambda) * r_j
      + lambda * normalize_sum_like(g_j, r_j)
      + alpha * normalize_sum_like(t_j, r_j)
```

where:

- `g_j` is the global PCA variance vector from the default SAQ planner.
- `r_j` is the IVF residual variance vector.
- `t_j` is a residual tail-excess vector.
- `lambda` is `--boundary-global-blend`.
- `alpha` is `--boundary-tail-alpha`.

The tail-excess term is:

```text
t_j = max(quantile_p((x_j - c_j)^2) - mean((x_j - c_j)^2), 0)
```

where `x` is a base vector, `c` is its assigned IVF centroid, and the quantile is computed over data vectors. In this run, `p=0.95`.

The DP segment cost becomes:

```text
cost(segment [a,b), bit B) = sum_{j in [a,b)} b_j / 2^B + segment_penalty
```

with:

```text
segment_penalty = segment_penalty_scale * sum_j b_j / 2^avg_bits
```

This is intentionally simple. The penalty is not a final theoretical claim; it is a control knob that asks the planner to avoid extra segment boundaries unless they buy enough boundary-risk reduction.

## 3. Implementation

The extension is implemented in:

```text
script/propose_residual_plan.py
```

New CLI knobs:

```text
--boundary-tail-alpha
--boundary-tail-quantile
--boundary-global-blend
--segment-penalty-scale
```

The script now emits an additional `boundary_dp` plan alongside the existing `global_dp_reimpl` and `residual_dp` plans. CSV outputs also include boundary-risk columns:

```text
boundary_risk_sum
boundary_risk_share
boundary_cost_contrib
```

Prototype caveat: the tail quantile path currently materializes residual squared values in memory. This is fine for `gist_sample100k`, but a larger dataset should use sampling or a streaming quantile sketch before this becomes a production-scale planner path.

## 4. Planner Grid

Dataset and planner setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 4
PCA = true
padding = 64
max segments = 7
```

All plans below have the same effective average bits including nonzero-segment overhead: `4.0667 b/d`.

| config | boundary segments | boundary cost reduction vs default | plan |
|---|---:|---:|---|
| `a000_g025_sp002` | 4 | 0.059284 | `128:9,384:5,320:2,128:0` |
| `a025_g000_sp002` | 4 | 0.061527 | `128:9,384:5,320:2,128:0` |
| `a025_g025_sp000` | 5 | 0.025847 | `64:9,256:6,256:4,256:2,128:0` |
| `a025_g025_sp002` | 4 | 0.059152 | `128:9,384:5,320:2,128:0` |
| `a025_g025_sp005` | 3 | 0.150714 | `192:8,320:4,448:2` |
| `a025_g040_sp002` | 4 | 0.057575 | `128:9,384:5,320:2,128:0` |
| `a050_g025_sp002` | 4 | 0.059068 | `128:9,384:5,320:2,128:0` |

Readout:

- Without a segment penalty, the boundary objective falls back to the residual-aggressive plan.
- With a small segment penalty, the planner repeatedly chooses `128:9,384:5,320:2,128:0`.
- With a stronger segment penalty, the planner collapses to `192:8,320:4,448:2`, which is too coarse in recall evaluation.

## 5. Actual Index Evaluation

Two boundary-aware candidates were encoded and evaluated:

```text
boundary_4seg = 128:9,384:5,320:2,128:0
boundary_3seg = 192:8,320:4,448:2
```

Comparison uses PCA-space `gist_sample100k`, IVF512, B=4, CAQ adjustment, R@100, top1000 sample groundtruth, and 24 threads for QPS. Treat QPS as indicative because these are single local runs; the main signal in this prototype is the recall/error tradeoff.

| name | R@100 np20 | np50 | np100 | np200 | np400 | QPS np200 | err_tot_avg | err_tot_max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default | 0.759150 | 0.927500 | 0.980870 | 0.990870 | 0.991190 | 9299.8 | 0.000476260 | 0.006655460 |
| residual_aggressive | 0.758430 | 0.926840 | 0.980370 | 0.990680 | 0.991040 | 9652.9 | 0.000467793 | 0.008507790 |
| eq_s0_to_s1 | 0.759230 | 0.927680 | 0.981120 | 0.991360 | 0.991660 | 8664.3 | 0.000527125 | 0.008094720 |
| boundary_4seg | 0.759060 | 0.927420 | 0.980750 | 0.991010 | 0.991390 | 11252.8 | 0.000463861 | 0.006829680 |
| boundary_3seg | 0.759220 | 0.927400 | 0.980140 | 0.989840 | 0.990170 | 11485.0 | 0.000585094 | 0.008315990 |

## 6. Interpretation

`boundary_4seg` is the useful candidate from this run.

It improves np200 recall over the residual-aggressive plan:

```text
0.991010 vs 0.990680
```

It also slightly beats the default np200 recall:

```text
0.991010 vs 0.990870
```

Its mean relative error is the best among the listed plans:

```text
0.000463861
```

The max relative error is close to default and better than the residual-aggressive plan:

```text
boundary_4seg:       0.006829680
default:             0.006655460
residual_aggressive: 0.008507790
```

This is a better tradeoff than `eq_s0_to_s1` for the current objective: `eq_s0_to_s1` has higher recall, but noticeably worse mean relative error and lower QPS.

`boundary_3seg` should not be the main candidate. It is faster and simpler, but np200 recall drops to `0.989840` and mean relative error worsens to `0.000585094`.

## 7. What This Extension Adds

This moves the planner from a purely residual-variance objective to a query-unaware risk objective with three signals:

1. Local residual risk: protects IVF residual quantization quality.
2. Global PCA variance: prevents over-discounting high-variance early PCA dimensions.
3. Residual tail risk: penalizes dimensions where a small number of vectors have large residual excursions.

The segment penalty adds a system-aware bias: extra segment boundaries are only worth keeping if they reduce enough risk. This matters because more segments can increase estimator overhead and may create brittle boundary behavior.

## 8. Artifacts

Planner summaries:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_plan_*.summary.json
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_plan_*.csv
```

Encoded indexes:

```text
/tmp/saq-run/data/gist_sample100k/ivf512_b4_caq_adj_seg_plan128x9_384x5_320x2_128x0_pca.index
/tmp/saq-run/data/gist_sample100k/ivf512_b4_caq_adj_seg_plan192x8_320x4_448x2_pca.index
```

Evaluation CSVs:

```text
/tmp/saq-run/reports/gist_sample100k_B4_boundary_candidate_qps.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_strongpenalty_qps.csv
/tmp/saq-run/results/saq/gist_sample100k_ivf512_b4_caq_adj_seg_plan128x9_384x5_320x2_128x0_pca_sm4.csv
/tmp/saq-run/results/saq/gist_sample100k_ivf512_b4_caq_adj_seg_plan192x8_320x4_448x2_pca_sm4.csv
```

## 9. Suggested Next Step

Run per-query comparison and segment-level attribution for `boundary_4seg` against default, residual-aggressive, and `eq_s0_to_s1`.

The specific question is whether `boundary_4seg` fixes the persistent lost-neighbor cases seen in residual-aggressive while avoiding the broad mean-error penalty introduced by `eq_s0_to_s1`.

If it passes that check, the next step is to promote boundary-aware DP from prototype into a more systematic sweep over B values and at least one additional high-dimensional dataset.


Follow-up status: this review has now been completed in `docs/saq_gist_sample100k_B4_boundary_4seg_review_2026_07_02.md`. The result is mixed: `boundary_4seg` keeps the best aggregate mean-error tradeoff, but it only partially fixes residual persistent-worse queries and introduces query 35 as a new stable failure. The recommended next design is boundary-aware DP v2 with an intra-segment risk penalty, not a stronger global segment-count penalty. That v2 follow-up is now implemented and summarized in `docs/saq_boundary_aware_dp_v2_intra_segment_2026_07_02.md`.

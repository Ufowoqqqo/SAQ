# SAQ Residual-Aware DP Offline Prototype

Date: 2026-07-02

This note records the first offline prototype for residual-aware SAQ planning.
It follows the query-unaware pivot and the GIST higher-dimensional segment
diagnostic.

The purpose is narrow:

```text
Keep SAQ's original dynamic-programming planner constraints, but replace the DP
cost vector from global PCA variance to pooled IVF residual variance. Then check
whether the proposed segment/bit plan changes in a stable and interpretable way.
```

This is not yet an encoding/search change. It only proposes and compares plans.

## 1. New Script

```text
script/propose_residual_plan.py
```

The script reads normal SAQ artifacts:

```text
*_base_pca.fvecs
*_base_pca.vars.fvecs
*_centroid_{K}_pca.fvecs
*_cluster_id_{K}.ivecs
SAQ default quant-plan CSV from script/extract_quant_plan.py
```

It implements two DP runs:

1. `global_dp_reimpl`: use global PCA variance, matching SAQ's default planner.
2. `residual_dp`: use pooled cluster-local residual variance.

The DP intentionally mirrors `saqlib/quantization/saq_data.hpp`:

```text
padding block = 64 dimensions
per non-zero segment overhead = 64 bits
max bit per segment = 11
0-bit segment is allowed only as the final tail
max_num_segs = D/64 if B < 2, otherwise D/128
cost(segment, b) = risk_sum(segment) / 2^b
```

The default residual risk is `pooled_centered_var`:

```text
For each IVF cluster, compute residuals x - centroid[cid]. Then aggregate the
within-cluster residual variance per dimension, weighted by cluster size.
```

Clusters smaller than `min_cluster_size=2` are skipped by default, matching the
segment diagnostic script.

## 2. Validation: DP Reimplementation Matches SAQ

A critical sanity check is whether `global_dp_reimpl` reproduces SAQ's own
extracted quant plan. It does on every run below.

| Dataset | B values | global DP matches SAQ default? |
| --- | --- | --- |
| GIST sampled, `N=100k`, `D=960`, `K=512` | 1, 2, 3, 4 | yes |
| audio, `N=53,387`, `D=192`, `K=4096` | 1, 2, 4, 8 | yes |

This makes the residual-aware comparison meaningful: any changed plan is caused
by the cost vector, not by accidentally using a different DP budget model.

## 3. GIST Sampled Results

Run outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B{1,2,3,4}_residual_plan.csv
/tmp/saq-run/reports/gist_sample100k_K512_B{1,2,3,4}_residual_plan.summary.json
```

Summary table:

| B | SAQ default plan | Residual-aware plan | Residual cost reduction | Global cost change |
| ---: | --- | --- | ---: | ---: |
| 1 | `0-64: 6b; 64-320: 2b; 320-960: 0b` | `0-64: 5b; 64-256: 3b; 256-960: 0b` | 0.93% | +5.55% |
| 2 | `0-64: 8b; 64-256: 4b; 256-512: 2b; 512-960: 0b` | `0-128: 6b; 128-256: 4b; 256-512: 2b; 512-960: 0b` | 0.07% | +12.05% |
| 3 | `0-64: 9b; 64-256: 5b; 256-576: 3b; 576-768: 1b; 768-960: 0b` | `0-64: 8b; 64-192: 6b; 192-384: 4b; 384-704: 2b; 704-960: 0b` | 2.38% | +1.77% |
| 4 | `0-64: 11b; 64-256: 6b; 256-576: 4b; 576-832: 2b; 832-960: 0b` | `0-64: 9b; 64-320: 6b; 320-576: 4b; 576-832: 2b; 832-960: 0b` | 3.38% | +2.94% |

Other data-only mismatch statistics are stable across B because the underlying
risk vectors are the same:

```text
global-vs-residual share total variation = 0.309353
global-vs-residual vector Pearson = 0.662232
```

Interpretation:

- The residual-aware DP consistently reduces the bit pressure on the first PCA
  head block.
- It often moves segment boundaries to give more resolution to the first
  post-head/middle region, which matches the earlier diagnostic that residual
  mass shifts from `0-64` toward `64-256` and beyond after IVF clustering.
- The residual objective does not always give a large offline cost reduction.
  B=2 is nearly flat under residual cost, while B=3/4 are more promising.
- The global cost usually gets worse, which is expected: the new plan is not
  optimizing global PCA variance anymore.

## 4. Audio Results

Run outputs:

```text
/tmp/saq-run/reports/audio_K4096_B{1,2,4,8}_residual_plan.csv
/tmp/saq-run/reports/audio_K4096_B{1,2,4,8}_residual_plan.summary.json
```

Summary table:

| B | SAQ default plan | Residual-aware plan | Residual cost reduction |
| ---: | --- | --- | ---: |
| 1 | `0-64: 3b; 64-192: 0b` | `0-64: 3b; 64-192: 0b` | 0.00% |
| 2 | `0-192: 2b` | `0-192: 2b` | 0.00% |
| 4 | `0-192: 4b` | `0-192: 4b` | 0.00% |
| 8 | `0-192: 8b` | `0-192: 8b` | 0.00% |

This negative result is useful. For `audio`, `D=192` leaves only three 64-dim
blocks, and SAQ's rule `max_num_segs = D/128` for `B >= 2` allows only one
segment. The residual-aware objective cannot change the plan unless the planner
constraints change. Even at B=1, the original plan remains optimal under the
same constraints.

## 5. Current Takeaway

The prototype advances the idea from a mismatch observation to a concrete
planner alternative.

```text
On a higher-dimensional multi-segment case, replacing global PCA variance with
pooled IVF residual variance produces systematically different SAQ plans under
the same budget and segment-overhead constraints.
```

This is still not an end-to-end method result. The next claim cannot be
"residual-aware SAQ improves recall" yet. The current defensible claim is:

```text
The residual-aware objective exposes a data-only planning alternative that SAQ's
current global-variance planner would not choose.
```

## 6. Next Engineering Step

The next implementation step should be a minimal plan-injection path, not a full
rewrite of SAQ.

Recommended next task:

```text
Add an experimental custom-plan override for create_index, so that the encoder
can use the offline residual-aware plan and we can measure relative error / recall
against SAQ default under identical data, K, B, PCA, and CAQ settings.
```

A conservative path is:

1. Add a parser for a CSV or compact string plan, e.g. `64:9,256:6,256:4,256:2,128:0`.
2. Add a config field and CLI flag such as `-seg_plan=...` or `-seg_plan_csv=...`.
3. In `SaqDataMaker::analyze_plan()`, use the custom plan when provided;
   otherwise keep the original DP/equal-segmentation behavior.
4. Run GIST sampled B=3/4 first, because those had the largest offline residual
   cost reductions.
5. Only after the sampled run works, repeat on official GIST/K4096 or another
   properly preprocessed high-dimensional dataset.

The official GIST/K4096 reproduction remains important before making a strong
research claim, but it no longer needs to block this minimal prototype step.

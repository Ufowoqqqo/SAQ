# SAQ Query-Unaware Segment Diagnostic

Date: 2026-07-02

This note records the first query-unaware segment diagnostic after the paper-code
alignment audit. The goal is to test whether SAQ's global PCA-variance plan is a
good proxy for the local residual structure that is actually quantized inside IVF
clusters.

## 1. Diagnostic Tool

New script:

```text
script/segment_diagnostics.py
```

The script reads normal SAQ build artifacts:

```text
*_base_pca.fvecs
*_centroid_{K}_pca.fvecs
*_cluster_id_{K}.ivecs
*_base_pca.vars.fvecs
quant-plan CSV from script/extract_quant_plan.py
```

It outputs one row per SAQ segment with:

```text
segment_id,start_dim,end_dim,dim_len,bits,
global_var_sum,global_var_share,
cluster_residual_var_mean,cluster_residual_var_p90,
cluster_residual_var_share_mean,cluster_residual_var_share_p90,
cluster_residual_var_share_weighted_mean,
share_gap_weighted_residual_minus_global,
within_segment_top1_var_share,within_segment_top8_var_share
```

The script uses only base/index data. It does not use query vectors or workload
statistics.

## 2. Run Setup

Working data directory:

```text
/tmp/saq-run/data/audio
```

Dataset:

```text
audio, N=53,387, D=192, K=4096
```

Cluster-filter rule:

```text
min_cluster_size = 2
used clusters = 3,882
skipped clusters = 214
cluster size p50 = 12
cluster size p90 = 24
cluster size max = 52
```

Default SAQ quant-plan CSVs came from the earlier create-index runs:

```text
/tmp/saq-run/logs/audio_K4096_B{1,2,4,8}_quant_plan.csv
```

Equal-segment controls were generated with:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset audio -K 4096 -B 2 -enable_PCA=true -seg_eqseg=3 -logtostderr=1

LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset audio -K 4096 -B 4 -enable_PCA=true -seg_eqseg=3 -logtostderr=1
```

Raw diagnostic CSVs were written to:

```text
/tmp/saq-run/reports/audio_K4096_B1_segment_diagnostics.csv
/tmp/saq-run/reports/audio_K4096_B2_segment_diagnostics.csv
/tmp/saq-run/reports/audio_K4096_B4_segment_diagnostics.csv
/tmp/saq-run/reports/audio_K4096_B8_segment_diagnostics.csv
/tmp/saq-run/reports/audio_K4096_B2_eqseg3_segment_diagnostics.csv
/tmp/saq-run/reports/audio_K4096_B4_eqseg3_segment_diagnostics.csv
```

## 3. Default SAQ B=1 Result

SAQ default plan:

```text
0 -> 64  (64d, 3b)
64 -> 192 (128d, 0b)
```

| Segment | Bits | Global variance share | Weighted residual share | Residual share p90 | Weighted gap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 3 | 0.982829 | 0.943989 | 0.978693 | -0.038839 |
| 64-192 | 0 | 0.017171 | 0.056011 | 0.111713 | +0.038839 |

Interpretation:

```text
The discarded tail segment has only 1.7% of global PCA variance, but it carries
5.6% of weighted cluster-local residual variance. At the 90th percentile cluster,
its residual share reaches 11.2%.
```

This is a positive smoke signal for the query-unaware hypothesis. The signal is
not yet an end-to-end recall result, but it shows that global PCA variance can
understate local residual variance in segments that SAQ may discard.

## 4. Equal-Segment Control

For B=2 and B=4, default SAQ uses one full segment, so there is no segment-level
allocation decision to inspect. This probe forced three equal 64-dimensional segments with
`-seg_eqseg=3` as a diagnostic control.

The B=2 and B=4 equal-segment diagnostics have identical variance shares because
the data and segment boundaries are the same; only the assigned bitwidth differs.

| Segment | Global variance share | Weighted residual share | Residual share p90 | Weighted gap | Top-8 global share inside segment |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 0.982829 | 0.943989 | 0.978693 | -0.038839 | 0.745504 |
| 64-128 | 0.014957 | 0.048422 | 0.096588 | +0.033465 | 0.245037 |
| 128-192 | 0.002214 | 0.007588 | 0.015179 | +0.005374 | 0.235714 |

Interpretation:

```text
Most of the tail mismatch comes from dimensions 64-128. That block has only
1.5% global PCA variance, but 4.8% weighted local residual variance and 9.7% p90
local residual share.
```

This suggests that a useful next diagnostic is not merely "tail vs head". It is
to compare global PCA variance against residual variance after IVF clustering,
especially around the first block after the high-variance head.

## 5. Current Takeaway

The first diagnostic supports the paper-code alignment conclusion:

```text
SAQ's query-unaware planner is global-variance driven, while the quantized object
inside IVF is cluster residual. These two statistics can disagree.
```

For `audio`, the disagreement is visible even though the dataset is small and
low-dimensional. The result is not yet sufficient to claim a method improvement.
It is sufficient to justify the next step: run the same diagnostic on a
higher-dimensional dataset or implement a cluster-local residual variance summary
that can be used to design shared local plans.

## 6. Next Step

The next concrete step should be one of:

1. Run this diagnostic on a higher-dimensional SAQ dataset where default DP
   creates multiple segments at B=2/3/4.
2. If such data is not ready locally, extend the diagnostic to propose a small
   family of residual-aware shared plans and evaluate them as `-seg_eqseg` or
   DP-cost controls before touching the SAQ search path.

Do not switch back to query-aware allocation unless the advisor explicitly
reopens that setting.

## 7. Follow-Up: GIST Higher-Dimensional Smoke Run

The higher-dimensional follow-up is recorded in:

```text
docs/saq_gist_higher_dim_segment_diagnostic_2026_07_02.md
```

The GIST sampled run uses `N=100,000`, `D=960`, `K=512` and shows the same
query-unaware mismatch with non-trivial default SAQ plans: the `0-64` head has
77.7% global PCA variance but only 62.9% weighted cluster-local residual share,
while `64-256` has 16.0% global variance but 27.0% weighted residual share.

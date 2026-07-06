# SAQ Default-Neighborhood Candidate Generator

Date: 2026-07-06

This note documents the first implementation of a middle-shape /
default-neighborhood candidate generator. The goal is to stop relying only on
large boundary-aware sweeps and instead generate a small, interpretable set of
plans near the SAQ default.

## 1. Implementation

New script:

```text
script/generate_default_neighborhood_plans.py
```

Inputs:

- a default plan string, a default plan CSV, or dataset artifacts plus `B`;
- conservative plan-shape guards;
- optional expected plans for validation.

Outputs:

```text
<output-prefix>.csv
<output-prefix>.summary.json
```

The script can infer the SAQ default plan by rerunning the global PCA-variance
DP over:

```text
{dataset}_base_pca.vars.fvecs
```

It then generates a small set of structured plans using these families:

| family | idea |
|---|---|
| `head_split` | split the post-head block and move one bit level into the split block |
| `head_widen_keep_levels` | widen the head by one 64-dim block while preserving later bit levels |
| `speed_merge_same_tail` | widen head and merge middle/tail-positive dimensions without changing zero tail |
| `tail_expand_middle_merge` | preserve a small head, merge middle dimensions, and expand the zero tail |
| `tail_expand_head_widen` | widen head, use broad middle chunks, and expand the zero tail |

The generator enforces:

```text
sum(dim_len) == D
used_bits_with_nonzero_segment_overhead <= B * D + 64
bits are nonincreasing by default
optional feasibility guards such as min_positive_bits and zero-tail constraints
```

This is not a learned planner yet. It is a structured candidate generator that
turns the current shape observations into reproducible candidate sets.

## 2. CIFAR60K B=4 Validation

Command:

```bash
python script/generate_default_neighborhood_plans.py \
  --data-dir /tmp/saq-run/data/cifar60k \
  --dataset cifar60k \
  --avg-bits 4 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --expect-plan 128:7,128:5,128:3,128:0 \
  --expect-plan 128:7,256:4,128:0 \
  --output-prefix /tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_2026_07_06
```

Default:

```text
64:9,192:5,128:3,128:0
```

Generated candidates:

| rank | plan | family | measured status |
|---:|---|---|---|
| 0 | `128:7,128:5,128:3,128:0` | `head_widen_keep_levels` | known positive middle |
| 1 | `64:7,64:6,128:5,128:3,128:0` | `head_split` | not yet measured |
| 2 | `128:7,256:4,128:0` | `speed_merge_same_tail` | known positive speed point |
| 3 | `64:9,192:5,128:3,128:0` | `default` | baseline |

Expected-plan check:

```text
missing_expected_plans = []
```

Measured result from the cross-dataset pilot:

| plan | R@10 np200 | QPS np200 | QPS ratio |
|---|---:|---:|---:|
| default | 0.9781 | 24472.672 | 1.000x |
| `128:7,256:4,128:0` | 0.9785 | 26295.217 | 1.074x |
| `128:7,128:5,128:3,128:0` | 0.9801 | 25368.984 | 1.037x |

Readout:

The generator reproduces the CIFAR positive middle plan and speed plan without
using the previous measured leaderboard as input.

## 3. Full GIST K4096 B=4 Validation

Command:

```bash
python script/generate_default_neighborhood_plans.py \
  --data-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --avg-bits 4 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 128 \
  --max-segments 6 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --expect-plan 64:10,320:6,384:3,192:0 \
  --expect-plan 128:9,320:5,320:3,192:0 \
  --output-prefix /tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_2026_07_06
```

Default:

```text
64:11,192:6,320:4,256:2,128:0
```

Generated candidates:

| rank | plan | family | measured status |
|---:|---|---|---|
| 0 | `128:9,320:5,320:3,192:0` | `tail_expand_head_widen` | `compact_k4096`, known speed positive |
| 1 | `64:10,320:6,384:3,192:0` | `tail_expand_middle_merge` | `filtered_new`, known balanced positive |
| 2 | `64:9,64:7,128:6,320:4,256:2,128:0` | `head_split` | `v2_split64`, known recall positive but slower |
| 3 | `128:8,128:6,320:4,256:2,128:0` | `head_widen_keep_levels` | not yet measured |
| 4 | `64:11,192:6,320:4,256:2,128:0` | `default` | baseline |

Expected-plan check:

```text
missing_expected_plans = []
```

Measured safe-searcher results already documented for full GIST K4096 B=4:

| plan | R@100 np800 | QPS np800 | QPS ratio |
|---|---:|---:|---:|
| default | 0.98845 | 1013.64 | 1.000x |
| `v2_split64` | 0.98975 | 918.44 | 0.906x |
| `filtered_new` | 0.98948 | 1092.29 | 1.078x |
| `compact_k4096` | 0.98922 | 1211.10 | 1.195x |

Readout:

The generator recovers all three important full-GIST plans from the default
shape alone:

```text
recall endpoint  = v2_split64
balanced middle  = filtered_new
speed endpoint   = compact_k4096
```

This is the first fixed, non-sweep mechanism that can reproduce the measured
balanced plan `filtered_new`.

## 4. Current Interpretation

The generator encodes the shape rule that emerged from GIST and CIFAR:

```text
SAQ can over-concentrate precision in the first 64 PCA dimensions.
Useful alternatives widen or split the head and preserve enough middle precision.
Speed-oriented alternatives reduce nonzero segment count or expand the zero tail.
```

DEEP remains a cautionary counterexample. On `deep1M_sample100k`, the default
plan is already compact:

```text
B=5 default = 64:7,192:4
candidate   = 128:7,128:2
```

That candidate improves QPS by about `1.10x` but loses about `0.00045` R@100 at
np200. So the generator should not automatically promote every neighborhood
candidate. It should generate a small set, then rank with boundary/speed proxies
and validate before making measured claims.

## 5. Remaining Gaps

1. The generator is rule-based. It is not yet integrated with pair-risk scoring.
2. It recovers known positive shapes on CIFAR and GIST, but has not yet been
   tested as an automatic selector across many datasets.
3. The next useful step is to score these generated candidates with the existing
   data-only pair-risk and speed proxies, then build/evaluate only the top few.
4. The unmeasured GIST candidate `128:8,128:6,320:4,256:2,128:0` and CIFAR
   candidate `64:7,64:6,128:5,128:3,128:0` can be used to test whether the
   generated neighborhood contains additional positives beyond the known ones.

## 6. Artifacts

```text
/tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_2026_07_06.csv
/tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_2026_07_06.summary.json
/tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_2026_07_06.summary.json
```

# Full GIST K4096 Data-Only Boundary Pair Sweep

Date: 2026-07-05

## 1. Purpose

The data-only boundary-pair sweep driver was first smoke-tested on
`gist_sample100k / K512`. This note extends the same planner proxy to the
full-GIST K4096 setting used by the latest mechanism audits.

The goal is not to evaluate a new encoded index yet. The goal is to ask:

```text
Given only base/index data, does the boundary-pair proxy produce a shortlist
that differs from or explains the current K4096 candidates?
```

Reference K4096 candidates:

```text
default      = 64:11,192:6,320:4,256:2,128:0
filtered_new = 64:10,320:6,384:3,192:0
v2_split64   = 64:9,64:7,128:6,320:4,256:2,128:0
```

## 2. Setup

Dataset/setup:

```text
dataset = gist_full
N = 1,000,000
D = 960
K = 4096
B = 4
PCA = true
query-aware signals = none
```

Artifacts:

```text
/tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_centroid_4096_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_cluster_id_4096.ivecs
```

I used `tail_alpha=0` in this first full run. This avoids the full residual
tail-risk path, which materializes a large residual-square matrix. The sweep
still uses global PCA variance, pooled residual risk, and sampled data-only
boundary-pair risk.

## 3. Command

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --avg-bits 4 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 2048 \
  --max-pairs 8192 \
  --boundary-global-blends 0,0.25 \
  --boundary-tail-alphas 0 \
  --boundary-pair-alphas 0,0.5,1,2 \
  --segment-penalty-scales 0,0.01,0.02 \
  --intra-segment-penalty-scales 0,1.6,3.2 \
  --inversion-penalty-scales 0,0.05,0.1 \
  --runtime-penalty-scales 0,0.005 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05
```

Outputs:

```text
/tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05.csv
/tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05.unique.csv
/tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05.pairs.csv
/tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05.risk.csv
/tmp/saq-run/reports/gist_full_K4096_B4_data_boundary_pair_sweep_2026_07_05.summary.json
```

## 4. Sampling Summary

The run sampled local base-as-query boundary pairs inside IVF cells:

| metric | value |
|---|---:|
| IVF cells | 4096 |
| eligible cells | 3686 |
| sampled anchors | 2048 |
| sampled boundary pairs | 8192 |
| median exact margin | 0.004338 |
| p90 exact margin | 0.019296 |
| pair-weight tau | 0.004338 |
| pair-risk top64 share | 0.576154 |

The pair-risk signal remains concentrated, but slightly less than in the
sample100k sweep, where top64 share was about `0.609`. On full K4096, the first
64 PCA dimensions still dominate the sampled near-boundary energy:

| block | dims | pair-risk share |
|---:|---|---:|
| 0 | 0-64 | 0.574112 |
| 1 | 64-128 | 0.169842 |
| 2 | 128-192 | 0.084476 |
| 3 | 192-256 | 0.053670 |
| 4 | 256-320 | 0.034346 |
| 5 | 320-384 | 0.024943 |

## 5. Sweep Result

Grid summary:

| metric | value |
|---|---:|
| all configs | 432 |
| feasible configs | 378 |
| infeasible configs | 54 |
| all unique plans | 8 |
| feasible unique plans | 6 |
| selected unique plans | 6 |

Filtered unique plans:

| rank | plan | configs | ranking score | boundary reduction | soft inversion ratio vs default | nonzero segments |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `64:9,64:7,128:6,320:4,256:2,128:0` | 96 | 0.919199 | 0.077928 | 0.971267 | 5 |
| 1 | `128:9,320:5,320:3,192:0` | 60 | 0.932612 | 0.065038 | 0.976507 | 3 |
| 2 | `128:9,384:5,320:2,128:0` | 78 | 0.933882 | 0.064237 | 0.981194 | 3 |
| 3 | `64:8,192:7,320:4,256:2,128:0` | 90 | 0.935883 | 0.061238 | 0.971205 | 4 |
| 4 | `64:9,256:6,256:4,256:2,128:0` | 48 | 0.953751 | 0.041762 | 0.955130 | 4 |
| 5 | `64:9,192:6,320:4,320:2,64:0` | 6 | 0.969037 | 0.029468 | 0.985056 | 4 |

## 6. Readout

The full K4096 result is consistent with the earlier boundary-aware direction:

1. `v2_split64` is again the top-ranked plan by the combined proxy.
2. The sweep does not rediscover `filtered_new`. The data-only pair proxy is
   more aligned with recall-oriented splitting than with the speed-oriented
   coarse plan.
3. The compact plan `128:9,320:5,320:3,192:0` is the strongest new shortlist
   candidate. It has only three nonzero segments, a 192-dimensional zero tail,
   and a good combined score.
4. `64:9,256:6,256:4,256:2,128:0` has the lowest soft inversion ratio in this
   sweep (`0.955x` of default), but its boundary-cost reduction is weaker.

This means the data-only pair proxy is not just reproducing the previous
speed-oriented result. It is primarily an accuracy/stability proxy. That is
useful, but it also means actual QPS validation is necessary before treating a
candidate as better than `filtered_new`.

## 7. Relationship To Existing K4096 Audits

Current measured K4096 R@100/QPS:

| plan | measured role | R@100 np800 | QPS role |
|---|---|---:|---|
| default | baseline | 0.98845 | baseline |
| `filtered_new` | speed-oriented | 0.98948 | fastest |
| `v2_split64` | recall-oriented | 0.98975 | slower |

New proxy shortlist:

| candidate | why it matters |
|---|---|
| `v2_split64` | proxy confirms existing recall-oriented candidate |
| `128:9,320:5,320:3,192:0` | compact three-nonzero-segment candidate; likely faster than `v2_split64` |
| `64:9,256:6,256:4,256:2,128:0` | lowest soft inversion proxy; useful stability contrast |

The key question is whether either new candidate can approach `v2_split64`'s
R@100 while closing part of the QPS gap to `filtered_new`.

## 8. Next Step

Build and evaluate the two new full-K4096 candidates:

```text
compact_k4096 = 128:9,320:5,320:3,192:0
low_inv_k4096 = 64:9,256:6,256:4,256:2,128:0
```

Evaluation should use the same protocol as the previous K4096 validation:

```text
dataset = gist_full
K = 4096
B = 4
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
nprobe = 50,100,200,400,800
QPS = np800, top100, thread24
```

If `compact_k4096` is close to `v2_split64` on R@100 but meaningfully faster,
it becomes the most interesting practical candidate. If `low_inv_k4096` does
not improve recall, then the pair proxy is more useful as a diagnostic signal
than as a direct planner objective.


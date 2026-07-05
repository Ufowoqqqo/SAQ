# Data-Only Boundary Pair Sweep Prototype

Date: 2026-07-05

## 1. Purpose

The full-GIST K4096 mechanism audits showed that current custom plans move
R@100 mostly through near-boundary rank replacements:

```text
filtered_new = fast, positive R@100, but boundary-biased
v2_split64   = higher R@100, slower, still inversion-prone
```

The next planner signal should stay query-unaware. This prototype adds a
data-only boundary-pair proxy: use base vectors as pseudo-queries, sample
same-IVF-cell positive/negative neighbor pairs near a local rank boundary, and
score segment plans by a DP objective plus a pair-level inversion proxy.

## 2. New Driver

Added script:

```text
script/sweep_data_boundary_pairs.py
```

It is a batch sweep driver, similar in spirit to `script/sweep_boundary_plan.py`,
but with one extra data-only signal:

1. Load PCA base vectors, IVF centroids, IVF ids, and global PCA variance.
2. Compute residual risk and optional residual tail risk as before.
3. Sample base-as-pseudo-query boundary pairs inside each IVF cell.
4. Build a per-dimension boundary-pair risk vector:

   ```text
   w_j += exp(-margin / tau) * ((a_j - p_j)^2 + (a_j - n_j)^2)
   ```

   where `a` is the anchor/base-as-query vector, `p` is the closer positive
   neighbor, `n` is the farther negative neighbor, and `margin = d(a,n)-d(a,p)`.
5. Blend this pair risk into the residual/global/tail DP risk vector.
6. Run the SAQ-style dynamic programming planner over a hyperparameter grid.
7. For every emitted plan, compute a pair-level inversion proxy:

   ```text
   proxy_error(pair, plan) = sum_segments pair_energy(segment) / 2^bits(segment)
   proxy_ratio = proxy_error / exact_margin
   soft_inversion_penalty = mean_w(max(proxy_ratio - 1, 0))
   ```

8. Rank plans by:

   ```text
   boundary_cost_ratio_vs_default
   + inversion_penalty_scale * (soft_penalty_ratio_vs_default - 1)
   + runtime_penalty_scale * nonzero_segment_count
   ```

This makes the inversion term relative to the default plan. A plan with lower
pair-inversion proxy than default is rewarded; a plan with higher proxy is
penalized.

The driver writes:

```text
<output-prefix>.csv          # one row per hyperparameter config
<output-prefix>.unique.csv   # one row per unique segment plan
<output-prefix>.pairs.csv    # sampled data-only boundary pairs
<output-prefix>.risk.csv     # global/residual/pair risk by 64-dim block
<output-prefix>.summary.json # grid, pair summary, top configs, top unique plans
```

## 3. Smoke Test

Compile check:

```bash
python -m py_compile script/sweep_data_boundary_pairs.py
```

Small smoke run:

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 4 \
  --boundary-rank 100 \
  --neighbor-window 4 \
  --pairs-per-anchor 2 \
  --anchors-per-cluster 1 \
  --max-anchors 64 \
  --max-pairs 128 \
  --boundary-global-blends 0,0.25 \
  --boundary-tail-alphas 0 \
  --boundary-pair-alphas 0,1 \
  --segment-penalty-scales 0,0.01 \
  --intra-segment-penalty-scales 0,1.6 \
  --inversion-penalty-scales 0,0.05 \
  --runtime-penalty-scales 0,0.005 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_smoke_norm_2026_07_05
```

Smoke result:

| metric | value |
|---|---:|
| configs | 64 |
| feasible configs | 64 |
| sampled pairs | 128 |
| unique plans | 6 |
| top plan | `64:9,64:7,128:6,320:4,256:2,128:0` |

The smoke test verifies the end-to-end path: sampling, risk construction, DP
sweep, pair proxy scoring, CSV output, and JSON summary.

## 4. Medium GIST Sample Sweep

Command:

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 4 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 512 \
  --max-pairs 2048 \
  --boundary-global-blends 0,0.25 \
  --boundary-tail-alphas 0,0.25 \
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
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05
```

Outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05.pairs.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05.risk.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_data_boundary_pair_sweep_rel_2026_07_05.summary.json
```

Sampling summary:

| metric | value |
|---|---:|
| IVF cells | 512 |
| eligible cells | 410 |
| sampled anchors | 410 |
| sampled boundary pairs | 1640 |
| median exact margin | 0.006965 |
| p90 exact margin | 0.031586 |
| pair-risk top64 share | 0.609148 |

The pair-risk vector is strongly concentrated: the top 64 dimensions account for
about 61% of the weighted pair risk. This is useful because it gives the planner
a data-only boundary signal that is not just the same as global residual
variance.

## 5. Initial Readout

Filtered unique plans from the medium sweep:

| rank | plan | configs | ranking score | boundary reduction | soft inversion ratio vs default | nonzero segments |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `64:9,64:7,128:6,320:4,256:2,128:0` | 192 | 0.923242 | 0.074356 | 0.975978 | 5 |
| 1 | `128:9,384:5,320:2,128:0` | 228 | 0.933295 | 0.064513 | 0.978080 | 3 |
| 2 | `64:8,192:7,320:4,256:2,128:0` | 162 | 0.945737 | 0.052816 | 0.985532 | 4 |
| 3 | `128:9,320:5,320:3,192:0` | 60 | 0.957916 | 0.039244 | 0.971600 | 3 |
| 4 | `64:9,256:6,256:4,256:2,128:0` | 96 | 0.961232 | 0.034696 | 0.959278 | 4 |
| 5 | `64:10,192:7,256:4,320:2,128:0` | 30 | 0.968493 | 0.028803 | 0.972959 | 4 |

Readout:

1. `v2_split64` remains the top plan under this data-only boundary-pair
   prototype, consistent with the earlier boundary-aware v2 sweep.
2. The new pair proxy does distinguish plans: several candidates reduce the
   soft inversion proxy below default, with ratios around `0.96-0.99`.
3. `64:9,256:6,256:4,256:2,128:0` has the lowest soft inversion proxy among the
   listed plans (`0.959x` of default), but its DP boundary reduction is weaker.
4. `128:9,320:5,320:3,192:0` is a compact 4-segment candidate with a good
   inversion proxy (`0.972x`) and a longer zero tail, but it needs actual index
   evaluation before any conclusion.

## 6. Limitations

This is a planner proxy, not a direct recall predictor.

- The pairs are sampled inside the same IVF cell, so they approximate local
  candidate-boundary behavior but do not model cross-cell recall loss.
- The inversion proxy uses a bit-scaled energy heuristic, not actual encoded
  SAQ codewords.
- The raw hard inversion rate is often near 1.0 under the current calibration,
  so the useful ranking signal is the relative soft penalty, not the hard rate.
- The medium sweep is on `gist_sample100k`, not full GIST K4096.

## 7. Next Step

Use this driver to shortlist a small number of data-only candidates, then build
and evaluate only the most informative ones.

Recommended immediate candidates:

| name | plan | reason |
|---|---|---|
| current recall candidate | `64:9,64:7,128:6,320:4,256:2,128:0` | still top by combined proxy |
| compact contrast | `128:9,320:5,320:3,192:0` | good pair proxy with fewer segments |
| inversion-proxy contrast | `64:9,256:6,256:4,256:2,128:0` | lowest soft inversion proxy in this sweep |

The strongest next validation is to run this same driver on full GIST K4096
with a moderate pair sample, then evaluate any new shortlist candidates against
`filtered_new` and `v2_split64`.


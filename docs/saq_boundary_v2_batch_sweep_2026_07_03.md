# Boundary-Aware DP v2 Batch Sweep

Date: 2026-07-03

Correction note, 2026-07-04: the B=4 qualitative conclusion that `v2_split64`
is the best current automatic recall candidate still holds under the corrected
safe searcher, but the exact recall/QPS leaderboard has been updated in
`docs/saq_gist_sample100k_safe_corrected_leaderboard_2026_07_04.md`. Future
comparisons should use `-searcher_safe_block_min_mode=2`.

This note records the first systematic batch sweep for the boundary-aware DP v2 planner on `gist_sample100k`. The sweep is planner-level: it enumerates v2 hyperparameters after loading the GIST sample artifacts once, deduplicates the generated segment plans, and then we selectively build/evaluate the most relevant candidates.

## 1. Why Batch Sweep

The previous v2 note identified `v2_split64` as the best automatic candidate so far:

```text
v2_split64 = 64:9,64:7,128:6,320:4,256:2,128:0
```

That result came from a small number of manual runs. The remaining question was whether `v2_split64` is a narrow accident of one hyperparameter setting or a stable region of the v2 objective.

The new driver is intended to answer that question without repeatedly recomputing residual statistics.

## 2. New Driver

Added script:

```text
script/sweep_boundary_plan.py
```

It is the batch counterpart of `script/propose_residual_plan.py`:

1. Load PCA base vectors, centroids, IVF ids, and global PCA variance once.
2. Compute residual variance risk once.
3. Compute residual tail-excess risk once when any tail alpha is positive.
4. Enumerate a grid over boundary objective hyperparameters.
5. Run the same DP planner used by the single-run prototype.
6. Write per-config rows, deduplicated unique plans, and a JSON summary.

The driver writes:

```text
<output-prefix>.csv          # one row per hyperparameter config
<output-prefix>.unique.csv   # one row per unique segment plan
<output-prefix>.summary.json # grid, summaries, top configs, top unique plans
```

## 3. Sweep Setup

Dataset/setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 4
PCA = true
padding = 64
residual risk = pooled centered residual variance
residual tail quantile = 0.95
```

Command:

```bash
python script/sweep_boundary_plan.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 4 \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_batch_sweep_2026_07_03
```

Grid:

| knob | values |
|---|---|
| `boundary_global_blend` | `0, 0.15, 0.25, 0.4` |
| `boundary_tail_alpha` | `0, 0.1, 0.25, 0.5` |
| `segment_penalty_scale` | `0, 0.005, 0.01, 0.02, 0.04` |
| `intra_segment_penalty_scale` | `0, 0.8, 1.6, 2.4, 3.2, 4.8, 6.4` |

Total configs:

```text
4 * 4 * 5 * 7 = 560
```

Raw local outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_batch_sweep_2026_07_03.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_batch_sweep_2026_07_03.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_batch_sweep_2026_07_03.summary.json
```

## 4. Sweep Result

The 560 configs collapsed to 14 unique segment plans.

Top unique plans by frequency:

| rank | configs | plan | segments | max nonzero segment | best objective reduction | comment |
|---:|---:|---|---:|---:|---:|---|
| 0 | 134 | `64:9,64:7,128:6,320:4,256:2,128:0` | 6 | 320 | 0.092336 | `v2_split64`; current best automatic candidate |
| 1 | 121 | `128:9,384:5,320:2,128:0` | 4 | 384 | 0.066049 | `boundary_4seg`; known `128-512` wide-segment pathology |
| 2 | 68 | `64:8,192:7,320:4,256:2,128:0` | 5 | 320 | 0.066803 | evaluated below; weaker recall/error |
| 3 | 60 | `64:9,64:7,128:6,192:4,256:3,192:1,64:0` | 7 | 256 | 0.178362 | high objective gain but build-time feasibility issue |
| 4 | 33 | `192:8,320:4,448:2` | 3 | 448 | 0.123459 | coarse no-tail plan |
| 5 | 30 | `64:9,256:6,256:4,256:2,128:0` | 5 | 256 | 0.033804 | residual-style baseline region |
| 6 | 29 | `64:8,64:6,128:6,192:4,192:3,256:2,64:0` | 7 | 256 | 0.188264 | high objective gain; too fragmented for immediate trust |
| 7 | 22 | `64:9,192:6,256:4,448:2` | 4 | 448 | 0.049962 | broad tail segment |
| 8 | 22 | `64:10,192:7,256:4,320:2,128:0` | 5 | 320 | 0.032904 | previous `v2_mid` contrast |
| 9 | 21 | `64:8,64:6,128:6,320:4,320:2,64:0` | 6 | 320 | 0.120865 | short zero tail |

The main readout is that `v2_split64` is not a one-off. It appears under all tested global blends and all tested tail alphas, across segment penalty scales `0, 0.005, 0.01, 0.02` and intra scales `0.8` through `6.4`.

## 5. Candidate Evaluation

We already had aggregate evaluation for default, `boundary_4seg`, `v2_split64`, and `v2_mid` from the v2 note. After the batch sweep, I evaluated the rank-2 unique plan as an additional shortlist candidate:

```text
sweep_rank2 = 64:8,192:7,320:4,256:2,128:0
```

Aggregate comparison:

| name | R@100 np20 | R@100 np50 | R@100 np100 | R@100 np200 | R@100 np400 | QPS np200 | err_tot_avg | err_tot_max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default | 0.759150 | 0.927500 | 0.980870 | 0.990870 | 0.991190 | 9299.8 | 0.000476260 | 0.006655460 |
| boundary_4seg | 0.759060 | 0.927420 | 0.980750 | 0.991010 | 0.991390 | 11252.8 | 0.000463861 | 0.006829680 |
| v2_split64 | 0.758890 | 0.927660 | 0.981110 | 0.991300 | 0.991590 | 8798.5 | 0.000456743 | 0.007399120 |
| sweep_rank2 | 0.757670 | 0.925780 | 0.979400 | 0.989520 | 0.989910 | 9367.1 | 0.000545425 | 0.007289770 |

`sweep_rank2` is worse than default and `v2_split64` on recall and mean relative error. It should not be pursued further.

I also attempted to build the rank-3 unique plan:

```text
64:9,64:7,128:6,192:4,256:3,192:1,64:0
```

`create_index` printed the custom plan and then failed with `SIGSEGV` during/after IVF index initialization. This is a useful negative result: the planner objective can produce high-scoring plans whose shape is risky for the current encoder/index path. In particular, this plan has a 1-bit non-final nonzero segment and only a 64-dimensional zero tail.

## 6. Interpretation

The sweep supports the previous v2 conclusion:

```text
v2_split64 remains the best automatic candidate among evaluated plans.
```

Reasons:

1. It is the most frequent unique plan in the 560-config sweep.
2. It removes the known `boundary_4seg` `128-512` 5-bit segment.
3. It improves np200 R@100 over default and `boundary_4seg`.
4. It gives lower mean relative error than default, `boundary_4seg`, and the evaluated rank-2 plan.
5. It does not rely on a single narrow hyperparameter setting.

The main caveat is still QPS. `v2_split64` uses more nonzero segments than default and `boundary_4seg`, so it is slower in the current local run.

## 7. What The Sweep Exposed

The batch sweep adds two important findings beyond the previous manual v2 runs.

First, objective reduction is not enough as a ranking criterion. Some high-reduction plans are too fragmented or contain risky low-bit internal segments.

Second, the planner and C++ build path need explicit plan-shape feasibility checks. The current Python planner can emit a plan that `create_index` accepts syntactically but cannot encode safely.

## 8. Next Step

Before expanding to more datasets or larger grids, the next implementation step should be a feasibility guard in the batch driver and possibly in custom-plan injection:

1. Add plan-shape flags such as minimum positive bitwidth, internal 1-bit segment, and short zero-tail detection.
2. Add optional sweep filters, disabled by default for compatibility, for example `--min-positive-bits 2` and `--min-zero-tail-dim 128`.
3. Rerun the same GIST B=4 sweep under conservative feasibility filters.
4. Evaluate the best remaining feasible candidates against `v2_split64` rather than chasing objective reduction alone.

This keeps the next search query-unaware and aligned with the current SAQ follow-up direction.

## 9. Feasibility Guard Implementation

The next step from Section 8 has now been implemented in `script/sweep_boundary_plan.py`.

The driver now emits plan-shape diagnostics for every candidate:

```text
positive_bitwidths
min_positive_bits
has_positive_1bit_segment
has_internal_1bit_segment
has_nonfinal_1bit_segment
zero_tail_dim_len
is_feasible
infeasible_reasons
```

New guard knobs:

```text
--min-positive-bits
--min-zero-tail-dim
--max-segments
--max-nonzero-segment-dim
--exclude-internal-1bit
--exclude-nonfinal-1bit
--filter-infeasible
```

By default, the driver remains backward-compatible: if no guard is enabled and `--filter-infeasible` is not set, it still writes the full sweep. With guards enabled, every row is annotated. With `--filter-infeasible`, the main CSV, unique CSV, and top-summary lists contain only feasible plans.

## 10. Filtered Sweep

Filtered command:

```bash
python script/sweep_boundary_plan.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 4 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 128 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_filtered_sweep_2026_07_03
```

Guard policy:

| guard | value | purpose |
|---|---:|---|
| minimum positive bitwidth | 2 | remove the risky non-final 1-bit segment pattern |
| minimum nonempty zero tail | 128 dims | remove 64-dim zero-tail plans seen in unstable high-reduction candidates |
| maximum segments | 6 | remove overly fragmented 7-segment plans |
| maximum positive segment width | 384 dims | remove very broad 448-dim positive segments |
| exclude non-final 1-bit | true | explicitly remove the rank-3 failure shape |

Raw local outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_filtered_sweep_2026_07_03.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_filtered_sweep_2026_07_03.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_filtered_sweep_2026_07_03.summary.json
```

Filtered summary:

| metric | value |
|---|---:|
| all configs | 560 |
| feasible configs | 382 |
| infeasible configs | 178 |
| all unique plans | 14 |
| feasible unique plans | 6 |
| selected unique plans | 6 |

Retained unique plans:

| rank | configs | plan | max nonzero segment | objective reduction | prior status |
|---:|---:|---|---:|---:|---|
| 0 | 134 | `64:9,64:7,128:6,320:4,256:2,128:0` | 320 | 0.092336 | `v2_split64`; best evaluated automatic candidate |
| 1 | 121 | `128:9,384:5,320:2,128:0` | 384 | 0.066049 | `boundary_4seg`; known wide `128-512` issue |
| 2 | 68 | `64:8,192:7,320:4,256:2,128:0` | 320 | 0.066803 | evaluated as `sweep_rank2`; weaker |
| 3 | 30 | `64:9,256:6,256:4,256:2,128:0` | 256 | 0.033804 | residual-style candidate |
| 4 | 22 | `64:10,192:7,256:4,320:2,128:0` | 320 | 0.032904 | `v2_mid`; lower error but weaker recall |
| 5 | 7 | `64:10,320:6,384:3,192:0` | 384 | 0.061480 | retained new feasible candidate; not yet recall-evaluated |

Filtered-out unique plans:

| original rank | configs | plan | reasons |
|---:|---:|---|---|
| 3 | 60 | `64:9,64:7,128:6,192:4,256:3,192:1,64:0` | `min_positive_bits<2`; `zero_tail_dim_len<128`; `segment_count>6`; `nonfinal_1bit_segment` |
| 4 | 33 | `192:8,320:4,448:2` | `max_nonzero_segment_dim_len>384` |
| 6 | 29 | `64:8,64:6,128:6,192:4,192:3,256:2,64:0` | `zero_tail_dim_len<128`; `segment_count>6` |
| 7 | 22 | `64:9,192:6,256:4,448:2` | `max_nonzero_segment_dim_len>384` |
| 9 | 21 | `64:8,64:6,128:6,320:4,320:2,64:0` | `zero_tail_dim_len<128` |
| 11 | 6 | `64:9,64:6,64:5,192:5,256:3,256:2,64:0` | `zero_tail_dim_len<128`; `segment_count>6` |
| 12 | 4 | `64:9,192:6,320:4,320:2,64:0` | `zero_tail_dim_len<128` |
| 13 | 3 | `64:8,192:7,256:4,384:2,64:0` | `zero_tail_dim_len<128` |

## 11. Updated Decision

The filtered sweep strengthens the previous decision rather than changing it:

```text
v2_split64 remains the best current automatic planner candidate.
```

The new guard is useful because it removes the exact type of high-objective but risky plan that caused the `create_index` failure, while preserving `v2_split64` and the other already evaluated feasible baselines.

The only retained candidate not yet recall-evaluated is:

```text
64:10,320:6,384:3,192:0
```

It appears in only 7 configs, but it has a moderate objective reduction and passes the conservative shape guard. The next experimental step should be to build/evaluate this one retained new plan, then decide whether to expand the filtered sweep to other B values or datasets.

## 12. Retained New Candidate Evaluation

The filtered sweep left one feasible candidate that had not yet been recall-evaluated:

```text
filtered_new = 64:10,320:6,384:3,192:0
```

Build command:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_sample100k \
  -K 512 \
  -B 4 \
  -enable_PCA=true \
  -seg_plan=64:10,320:6,384:3,192:0 \
  -logtostderr=1
```

The index built successfully:

```text
/tmp/saq-run/data/gist_sample100k/ivf512_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca.index
```

Evaluation used the same setup as the earlier B=4 runs: PCA-space `gist_sample100k`, IVF512, B=4, top1000 groundtruth, R@100, `searcher_vars_bound_m=4`, and 24 threads for QPS.

Raw local summaries:

```text
/tmp/saq-run/reports/gist_sample100k_B4_filtered_new_candidate_qps.csv
/tmp/saq-run/reports/gist_sample100k_B4_filtered_new_candidate_summary.csv
```

Aggregate comparison:

| name | R@100 np20 | np50 | np100 | np200 | np400 | QPS np200 | err_tot_avg | err_tot_max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default | 0.759150 | 0.927500 | 0.980870 | 0.990870 | 0.991190 | 9299.8 | 0.000476260 | 0.006655460 |
| boundary_4seg | 0.759060 | 0.927420 | 0.980750 | 0.991010 | 0.991390 | 11252.8 | 0.000463861 | 0.006829680 |
| v2_split64 | 0.758890 | 0.927660 | 0.981110 | 0.991300 | 0.991590 | 8798.5 | 0.000456743 | 0.007399120 |
| v2_mid | 0.758450 | 0.926870 | 0.980500 | 0.990710 | 0.991080 | 9357.4 | 0.000434397 | 0.007538950 |
| sweep_rank2 | 0.757670 | 0.925780 | 0.979400 | 0.989520 | 0.989910 | 9367.1 | 0.000545425 | 0.007289770 |
| filtered_new | 0.758610 | 0.926940 | 0.980820 | 0.990970 | 0.991290 | 10290.7 | 0.000440546 | 0.011613200 |

Readout:

- `filtered_new` is buildable and passes the conservative plan-shape guard.
- It improves np200 R@100 over default by only `+0.000100`, and is below `v2_split64` by `-0.000330`.
- Its mean relative error is better than default, boundary_4seg, and v2_split64, but worse than `v2_mid`.
- Its max relative error is the worst among the listed candidates, which suggests the broad `384-768` 3-bit segment creates tail-risk cases.
- Its np200 QPS is faster than default and v2_split64, but slower than boundary_4seg.

Decision:

```text
filtered_new is not a replacement for v2_split64.
```

It is useful as a tradeoff point: lower mean error and better speed than `v2_split64`, but weaker recall and worse max error. The GIST B=4 filtered sweep can now be considered closed unless we want a per-query review of `filtered_new` specifically. The higher-value next step is to apply the guarded sweep/evaluation loop to another B value or dataset.

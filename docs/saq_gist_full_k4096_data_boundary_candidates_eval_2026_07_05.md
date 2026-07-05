# Full GIST K4096 Data-Boundary Candidate Evaluation

Date: 2026-07-05

## 1. Purpose

The full-GIST K4096 data-only boundary-pair sweep produced two new shortlist
candidates:

```text
compact_k4096 = 128:9,320:5,320:3,192:0
low_inv_k4096 = 64:9,256:6,256:4,256:2,128:0
```

This note builds both indexes and evaluates them with the same full K4096
protocol used for `filtered_new` and `v2_split64`.

Configuration:

```text
dataset = gist_full
K = 4096
B = 4
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
nprobe = 50,100,200,400,800
QPS = np800, top100, thread24
```

## 2. Built Indexes

Both candidate indexes built successfully.

| name | plan | build time | index size |
|---|---|---:|---:|
| `compact_k4096` | `128:9,320:5,320:3,192:0` | 2.73s | 547 MB |
| `low_inv_k4096` | `64:9,256:6,256:4,256:2,128:0` | 2.72s | 555 MB |

Index artifacts:

```text
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca.index
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_plan64x9_256x6_256x4_256x2_128x0_pca.index
```

## 3. Evaluation Artifacts

Summary outputs:

```text
/tmp/saq-run/reports/gist_full_k4096_new_candidates_b4_leaderboard_2026_07_05.csv
/tmp/saq-run/reports/gist_full_k4096_new_candidates_b4_compare_rows_2026_07_05.csv
/tmp/saq-run/reports/gist_full_k4096_new_candidates_b4_leaderboard_2026_07_05.json
```

QPS outputs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x9_256x6_256x4_256x2_128x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
```

## 4. Leaderboard

| plan | R@100 np50 | np100 | np200 | np400 | np800 | QPS np800 | avg ms | QPS ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default | 0.74477 | 0.86604 | 0.94469 | 0.97999 | 0.98845 | 1013.64 | 23.68 | 1.000x |
| `v2_split64` | 0.74498 | 0.86633 | 0.94526 | 0.98097 | 0.98975 | 918.44 | 26.13 | 0.906x |
| `filtered_new` | 0.74481 | 0.86609 | 0.94509 | 0.98097 | 0.98948 | 1092.29 | 21.97 | 1.078x |
| `compact_k4096` | 0.74491 | 0.86606 | 0.94485 | 0.98065 | 0.98922 | 1211.10 | 19.82 | 1.195x |
| `low_inv_k4096` | 0.74490 | 0.86617 | 0.94508 | 0.98064 | 0.98918 | 1023.99 | 23.44 | 1.010x |

Delta versus default:

| plan | delta np50 | np100 | np200 | np400 | np800 |
|---|---:|---:|---:|---:|---:|
| `v2_split64` | +0.00021 | +0.00029 | +0.00057 | +0.00098 | +0.00130 |
| `filtered_new` | +0.00004 | +0.00005 | +0.00040 | +0.00098 | +0.00103 |
| `compact_k4096` | +0.00014 | +0.00002 | +0.00016 | +0.00066 | +0.00077 |
| `low_inv_k4096` | +0.00013 | +0.00013 | +0.00039 | +0.00065 | +0.00073 |

## 5. Query-Level Movement At np800

| plan | better | equal | worse | worst query | worst delta | best query | best delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v2_split64` | 310 | 481 | 209 | 78 | -3 | 102 | +3 |
| `filtered_new` | 295 | 496 | 209 | 650 | -3 | 442 | +3 |
| `compact_k4096` | 301 | 466 | 233 | 535 | -3 | 43 | +3 |
| `low_inv_k4096` | 297 | 466 | 237 | 359 | -3 | 43 | +3 |

Both new candidates remain boundary-level plans. They have many query-level
swaps and still contain `-3` worst cases. Neither removes the rank-inversion
risk observed in the mechanism audits.

## 6. Readout

`compact_k4096` is the useful new result.

It does not reach the recall of `filtered_new` or `v2_split64`:

```text
np800 R@100:
compact_k4096 = 0.98922
filtered_new  = 0.98948
v2_split64    = 0.98975
```

But it is much faster:

```text
QPS np800:
compact_k4096 = 1211.10
filtered_new  = 1092.29
default       = 1013.64
v2_split64    = 918.44
```

So `compact_k4096` is not the recall-oriented replacement for `v2_split64`.
Instead, it becomes a speed-oriented point on the Pareto curve: it gives a
positive `+0.00077` R@100 over default while improving QPS by about `19.5%`.
Compared with `filtered_new`, it sacrifices `0.00026` R@100 but gains about
`10.9%` QPS.

`low_inv_k4096` should not be pursued as a main candidate. It is dominated by
`compact_k4096` on both R@100 and QPS, and also dominated by `filtered_new` on
both R@100 and QPS:

```text
low_inv_k4096: R@100 0.98918, QPS 1023.99
compact_k4096: R@100 0.98922, QPS 1211.10
filtered_new:  R@100 0.98948, QPS 1092.29
```

## 7. Implication

The data-only boundary-pair proxy was useful for producing an unexpected
high-speed candidate, but it did not produce a better recall/QPS balanced plan
than `filtered_new`.

Current practical shortlist:

| role | plan | reason |
|---|---|---|
| best recall | `v2_split64` | highest measured R@100, but slow |
| balanced speed/recall | `filtered_new` | better R@100 than compact, faster than default |
| speed extreme | `compact_k4096` | fastest measured plan with positive R@100 delta |

`low_inv_k4096` is useful as a negative validation of the proxy: the lowest
soft-inversion proxy did not translate into a better measured tradeoff.

## 8. Next Step

The next high-signal step is a mechanism audit for `compact_k4096`, not for
`low_inv_k4096`.

The audit should answer:

1. Why does the compact 4-segment plan run faster than `filtered_new` despite
   having similar total dimensional coverage?
2. Is its recall loss relative to `filtered_new` concentrated in the same
   near-boundary inversion pattern?
3. Does the 192-dimensional zero tail explain the speedup, or is the main
   factor fewer nonzero segments and earlier fast-stage rejection?

If the mechanism is clean, `compact_k4096` can be presented as a speed-oriented
systems candidate. If it relies on fragile boundary bias, it should remain a
diagnostic point rather than a main method.


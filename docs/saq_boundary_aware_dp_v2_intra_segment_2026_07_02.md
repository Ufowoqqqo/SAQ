# Boundary-Aware DP v2: Intra-Segment Risk Penalty

Date: 2026-07-02

## 1. Motivation

The first boundary-aware DP candidate was:

```text
boundary_4seg = 128:9,384:5,320:2,128:0
```

It had a good aggregate tradeoff, but the per-query review showed that its wide `128-512` 5-bit segment created stable boundary failures. Query 35 was the clearest example: the same three GT@100 ids were lost at every nprobe, and the `128-512` segment dominated the lost-id error.

The next objective should therefore not simply increase the global segment-count penalty. Stronger segment penalty already produced a too-coarse 3-segment plan with poor recall. The goal of v2 is more targeted:

```text
penalize wide segments whose internal 64-block risk is uneven
```

## 2. Objective Change

For each candidate segment `[a,b)` with bitwidth `B`, v1 used:

```text
cost([a,b), B) = sum_risk([a,b)) / 2^B + segment_penalty
```

v2 adds an intra-segment risk penalty:

```text
cost([a,b), B)
  = (sum_risk([a,b)) + gamma * intra_penalty([a,b))) / 2^B
    + segment_penalty
```

The prototype defines:

```text
intra_penalty([a,b)) = max_64block_risk([a,b)) - mean_64block_risk([a,b))
```

where each 64-block risk is the boundary-risk sum over one 64-dimensional block. This has two intended effects:

1. A one-block segment has zero intra penalty.
2. A wide segment containing one unusually risky 64-block is penalized, even if its total risk looks acceptable.

The implementation is still query-unaware: it uses base vectors, IVF assignments, PCA variance, residual variance, and residual tail risk only.

## 3. Implementation

Modified file:

```text
script/propose_residual_plan.py
```

New CLI knob:

```text
--intra-segment-penalty-scale
```

New CSV diagnostics:

```text
boundary_intra_penalty
boundary_intra_cost_contrib
boundary_v2_cost_contrib
```

The old default behavior is preserved when `--intra-segment-penalty-scale=0`.

## 4. Planner Sweep

Dataset/setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 4
PCA = true
padding = 64
R@100 groundtruth = sample-specific top1000 GT
```

The full-tail selected sweep used:

```text
boundary_tail_alpha = 0.25
boundary_global_blend = 0.25
```

Selected results:

| label | segment penalty scale | intra scale | plan |
|---|---:|---:|---|
| `sp000_ip1p6` | 0.000 | 1.6 | `64:9,64:7,128:6,320:4,256:2,128:0` |
| `sp0005_ip1p6` | 0.005 | 1.6 | `64:9,64:7,128:6,320:4,256:2,128:0` |
| `sp001_ip2p4` | 0.010 | 2.4 | `64:9,64:7,128:6,320:4,256:2,128:0` |

A faster no-tail exploratory grid also produced a more conservative candidate:

```text
v2_mid = 64:10,192:7,256:4,320:2,128:0
```

This candidate was evaluated as a contrast because it has fewer segments and stronger first-block protection.

## 5. Aggregate Evaluation

All rows use PCA-space `gist_sample100k`, IVF512, B=4, CAQ adjustment, R@100, and 24 threads for QPS. QPS is indicative because these are local runs.

| name | R@100 np20 | np50 | np100 | np200 | np400 | QPS np200 | err_tot_avg | err_tot_max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default | 0.759150 | 0.927500 | 0.980870 | 0.990870 | 0.991190 | 9299.8 | 0.000476260 | 0.006655460 |
| residual_aggressive | 0.758430 | 0.926840 | 0.980370 | 0.990680 | 0.991040 | 9652.9 | 0.000467793 | 0.008507790 |
| eq_s0_to_s1 | 0.759230 | 0.927680 | 0.981120 | 0.991360 | 0.991660 | 8664.3 | 0.000527125 | 0.008094720 |
| boundary_4seg | 0.759060 | 0.927420 | 0.980750 | 0.991010 | 0.991390 | 11252.8 | 0.000463861 | 0.006829680 |
| v2_split64 | 0.758890 | 0.927660 | 0.981110 | 0.991300 | 0.991590 | 8798.5 | 0.000456743 | 0.007399120 |
| v2_mid | 0.758450 | 0.926870 | 0.980500 | 0.990710 | 0.991080 | 9357.4 | 0.000434397 | 0.007538950 |

Readout:

- `v2_split64` nearly matches `eq_s0_to_s1` recall while keeping much lower mean relative error.
- `v2_split64` improves np200 R@100 over default by `+0.000430` and over boundary_4seg by `+0.000290`.
- `v2_split64` has better mean relative error than default, residual-aggressive, eq_s0_to_s1, and boundary_4seg.
- `v2_mid` gives the best mean relative error, but its recall is below default at np200, so it is not the main candidate.
- `v2_split64` is slower than boundary_4seg and default because it has more nonzero segments.

## 6. Per-Query Review for v2_split64

Aggregate per-query comparison against default:

| nprobe | default R@100 | v2 R@100 | delta | lost events | gained events | worse q | better q | equal q | worst q delta | best q delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20 | 0.759150 | 0.758890 | -0.000260 | 81 | 55 | 63 | 49 | 888 | 243:-3 | 609:+2 |
| 50 | 0.927500 | 0.927660 | +0.000160 | 162 | 178 | 107 | 134 | 759 | 243:-3 | 22:+2 |
| 100 | 0.980870 | 0.981110 | +0.000240 | 401 | 425 | 194 | 223 | 583 | 556:-3 | 259:+3 |
| 200 | 0.990870 | 0.991300 | +0.000430 | 557 | 600 | 227 | 270 | 503 | 556:-3 | 259:+3 |
| 400 | 0.991190 | 0.991590 | +0.000400 | 575 | 615 | 229 | 275 | 496 | 556:-3 | 259:+3 |

Persistent query behavior:

| comparison vs default | persistent worse queries | ever worse queries | persistent better queries |
|---|---:|---:|---:|
| residual_aggressive | 63 | 314 | 34 |
| eq_s0_to_s1 | 33 | 292 | 41 |
| boundary_4seg | 43 | 319 | 41 |
| v2_split64 | 37 | 283 | 32 |

`v2_split64` fixes most residual-aggressive persistent failures:

```text
still residual persistent-worse under v2:
[27, 36, 153, 482, 509, 536, 979]
```

It also fixes most boundary_4seg persistent failures:

```text
fixed boundary_4seg persistent-worse queries: 41 / 43
```

## 7. Query Checks

Query 974:

```text
boundary_4seg: -1 at every nprobe
v2_split64:     0 at every nprobe
```

`v2_split64` fully fixes the canonical query 974 membership failure.

Query 35:

```text
boundary_4seg: -3 at every nprobe
v2_split64:     0 at np20/50/100, -1 at np200/400
```

`v2_split64` mostly fixes the new boundary_4seg failure. The remaining lost id at high nprobe is `82634` at GT rank 96, with the largest segment error in `0-64`, not the old wide `128-512` segment.

New worst query:

```text
query 556: -3 at every nprobe
lost ids: 96544;98747;98757
```

The query 556 attribution is not dominated by a single wide segment. Its error is spread across `0-64`, `128-256`, `256-576`, and `576-832` depending on the id. This is a different failure mode from boundary_4seg's `128-512` pathology.

## 8. Segment Attribution at np200

Custom lost events for `v2_split64`:

| segment | bits | event count | mean error | mean abs error | abs share | positive frac |
|---|---:|---:|---:|---:|---:|---:|
| 0-64 | 9 | 557 | 0.000135 | 0.000370 | 0.137 | 0.616 |
| 64-128 | 7 | 557 | 0.000128 | 0.000375 | 0.132 | 0.616 |
| 128-256 | 6 | 557 | 0.000189 | 0.000478 | 0.163 | 0.637 |
| 256-576 | 4 | 557 | 0.000704 | 0.001026 | 0.309 | 0.752 |
| 576-832 | 2 | 557 | 0.000403 | 0.000589 | 0.164 | 0.684 |
| 832-960 | 0 | 557 | 0.0000999 | 0.000335 | 0.096 | 0.587 |

Compared with boundary_4seg, v2 removes the wide `128-512` segment. Lost-event absolute error is still largest in a mid segment, but the largest segment is now `256-576` with 30.9% share instead of `128-512` with 43.0% share. This confirms that the intra-segment penalty directly addressed the diagnosed issue.

## 9. Decision

`v2_split64` is the best automatic planner candidate so far.

It should not yet be treated as final because it pays a QPS cost and still has persistent failures, especially query 556. But relative to the previous automatic candidate, it is a clear improvement:

```text
boundary_4seg np200 R@100: 0.991010, err_tot_avg: 0.000463861
v2_split64   np200 R@100: 0.991300, err_tot_avg: 0.000456743
```

The next step should be a more efficient planner-sweep driver that loads data once and evaluates many DP hyperparameters, followed by testing v2 on another B value or dataset. The current CLI recomputes residual statistics for every grid point, which made even small sweeps slow.

## 10. Artifacts

Planner outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_*.summary.json
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_fast_*.summary.json
/tmp/saq-run/reports/gist_sample100k_K512_B4_boundary_v2_selected_*.summary.json
```

Encoded indexes:

```text
/tmp/saq-run/data/gist_sample100k/ivf512_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca.index
/tmp/saq-run/data/gist_sample100k/ivf512_b4_caq_adj_seg_plan64x10_192x7_256x4_320x2_128x0_pca.index
```

Review summaries:

```text
/tmp/saq-run/reports/gist_sample100k_B4_v2_split64_review_summary.json
/tmp/saq-run/reports/gist_sample100k_B4_v2_split64_segment_attribution_summary.csv
/tmp/saq-run/reports/gist_sample100k_B4_v2_split64_segment_attribution_events.csv
```

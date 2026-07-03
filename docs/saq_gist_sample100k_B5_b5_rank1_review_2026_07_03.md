# GIST Sample100k B=5 `b5_rank1` Per-Query and Segment Attribution Review

Date: 2026-07-03

This note follows up the B=5 guarded sweep. The candidate under review is the best practical B=5 plan from that sweep:

```text
b5_rank1 = 128:10,256:6,320:4,256:2
```

The default B=5 plan from `create_index` is:

```text
default_b5 = 64:11,192:7,320:5,320:3,64:0
```

The goal here is not to run another broad sweep. It is to check whether the aggregate improvement of `b5_rank1` is broad and stable, or whether it hides severe per-query regressions.

## 1. Setup

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 5
PCA = true
groundtruth = sample-specific top1000 GT
metric = top100 recall at nprobe in {20,50,100,200,400}
```

Raw local artifacts:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_compare_np20_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_compare_np50_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_compare_np100_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_compare_np200_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_compare_np400_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_segment_attribution_events.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_segment_attribution_summary.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_review_summary.json
```

## 2. Aggregate Per-Query Comparison

| nprobe | default R@100 | custom R@100 | delta | better queries | equal queries | worse queries | mean result overlap | worst query | worst delta | best query | best delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.758330 | 0.759500 | +0.001170 | 121 | 847 | 32 | 99.265 | 580 | -8 | 621 | +5 |
| 50 | 0.927440 | 0.928660 | +0.001220 | 172 | 752 | 76 | 99.212 | 580 | -8 | 621 | +5 |
| 100 | 0.982540 | 0.983490 | +0.000950 | 227 | 620 | 153 | 99.174 | 580 | -8 | 621 | +5 |
| 200 | 0.993370 | 0.994450 | +0.001080 | 266 | 546 | 188 | 99.163 | 580 | -8 | 621 | +5 |
| 400 | 0.993740 | 0.994820 | +0.001080 | 268 | 541 | 191 | 99.165 | 580 | -8 | 621 | +5 |

Readout:

- `b5_rank1` improves mean R@100 at every nprobe tested.
- The improvement is small but stable: roughly `+0.0010` absolute recall.
- Result overlap stays above 99 on average, so the plan mostly perturbs boundary cases rather than changing the whole ranking.
- The per-query distribution is asymmetric in count but has two large negative outliers: query `580` at `-8` and query `500` at `-6`.

At `nprobe=200`, the per-query delta distribution is:

| delta hits | query count |
|---:|---:|
| -8 | 1 |
| -6 | 1 |
| -2 | 13 |
| -1 | 173 |
| 0 | 546 |
| +1 | 221 |
| +2 | 38 |
| +3 | 5 |
| +4 | 1 |
| +5 | 1 |

Across all five nprobe values:

| query set | count |
|---|---:|
| ever worse | 220 |
| ever better | 322 |
| persistently worse | 23 |
| persistently better | 92 |

Persistent worse queries:

```text
16, 29, 44, 46, 101, 129, 159, 341, 392, 420, 438, 500,
580, 598, 682, 713, 729, 739, 843, 856, 925, 962, 966
```

This is the key caveat: the aggregate win is real, but not monotone per query.

## 3. Stable Worst Query: 580

Query `580` is the worst regression at every nprobe. The lost GT ids are identical across all nprobe values, so this is not simply an IVF probing issue.

| nprobe | default hits | custom hits | delta | lost GT ids |
|---:|---:|---:|---:|---|
| 20 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |
| 50 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |
| 100 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |
| 200 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |
| 400 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |

The lost ids are all high-rank boundary neighbors except one relatively early neighbor:

```text
lost_gt_min_rank = 22
lost_gt_mean_rank = 63.625
```

Custom-plan attribution for query `580` lost events is also stable across nprobes because the same eight ids are lost each time:

| segment | bits | mean error | mean abs error | positive error frac |
|---|---:|---:|---:|---:|
| 0-128 | 10 | +0.00000354 | 0.00001971 | 0.625 |
| 128-384 | 6 | +0.00000331 | 0.00001503 | 0.750 |
| 384-704 | 4 | -0.00000183 | 0.00000557 | 0.625 |
| 704-960 | 2 | +0.00000015 | 0.00000110 | 0.500 |

Interpretation:

- The tail segment `704-960:2b` is not the main source of the query-580 failure.
- The largest absolute contribution comes from the front and mid segments, especially `0-128:10b` and `128-384:6b`.
- Even though the average errors are tiny, the top-100 boundary is tight enough that small signed errors can eject true neighbors.
- The failure appears to be a ranking-boundary issue caused by segment estimator bias, not a raw recall ceiling from insufficient probing.

## 4. Stable Best Query: 621

Query `621` is the best improvement at every nprobe. The gained GT ids are also identical across all nprobe values.

| nprobe | default hits | custom hits | delta | gained GT ids |
|---:|---:|---:|---:|---|
| 20 | 92 | 97 | +5 | `92493;99125;97391;97380;97379` |
| 50 | 95 | 100 | +5 | `92493;99125;97391;97380;97379` |
| 100 | 95 | 100 | +5 | `92493;99125;97391;97380;97379` |
| 200 | 95 | 100 | +5 | `92493;99125;97391;97380;97379` |
| 400 | 95 | 100 | +5 | `92493;99125;97391;97380;97379` |

Custom-plan attribution for query `621` gained events:

| segment | bits | mean error | mean abs error | positive error frac |
|---|---:|---:|---:|---:|
| 0-128 | 10 | +0.00040970 | 0.00040970 | 1.000 |
| 128-384 | 6 | -0.00044794 | 0.00058985 | 0.200 |
| 384-704 | 4 | +0.00070198 | 0.00130734 | 0.800 |
| 704-960 | 2 | +0.00041504 | 0.00081174 | 0.800 |

This case is useful because it shows that `b5_rank1` is not just adding random noise. It can consistently rescue the same GT neighbors across nprobe settings. The strongest absolute attribution is again in the mid segment `384-704:4b`, with nontrivial tail contribution.

## 5. Aggregate Segment Attribution

The following table uses all lost/gained events at `nprobe=200`.

Custom lost events: 385

| segment | bits | mean error | mean abs error | abs-error share | positive error frac |
|---|---:|---:|---:|---:|---:|
| 0-128 | 10 | +0.00004236 | 0.00016770 | 0.161229 | 0.558442 |
| 128-384 | 6 | +0.00038556 | 0.00056804 | 0.378130 | 0.724675 |
| 384-704 | 4 | +0.00029319 | 0.00049952 | 0.313063 | 0.683117 |
| 704-960 | 2 | +0.00011577 | 0.00025415 | 0.147578 | 0.638961 |

Custom gained events: 493

| segment | bits | mean error | mean abs error | abs-error share | positive error frac |
|---|---:|---:|---:|---:|---:|
| 0-128 | 10 | +0.00000222 | 0.00017623 | 0.185965 | 0.529412 |
| 128-384 | 6 | -0.00007059 | 0.00043159 | 0.350510 | 0.421907 |
| 384-704 | 4 | -0.00007736 | 0.00039037 | 0.293757 | 0.432049 |
| 704-960 | 2 | -0.00000500 | 0.00022141 | 0.169768 | 0.505071 |

Readout:

- Both lost and gained events are dominated by the middle two segments, `128-384:6b` and `384-704:4b`.
- For lost events, those middle segments have positive mean error, making true GT neighbors look farther away.
- For gained events, those same middle segments have negative mean error, making true GT neighbors look closer.
- The `704-960:2b` tail contributes, but it is not the dominant factor. Therefore the B=5 improvement should not be summarized as only tail preservation. A better summary is: `b5_rank1` changes the mid/tail budget enough to shift tight top-100 boundary decisions, usually in the right direction, but with stable bad queries.

## 6. Decision

`b5_rank1` remains the strongest evaluated B=5 candidate:

```text
R@100 improves at every nprobe.
QPS at nprobe=200 improves by about 13.4% versus default.
The plan uses only 4 segments, fewer than default's 5 segments.
```

However, it is not safe to treat the improvement as uniformly better. Query `580` and query `500` are stable regressions, and query `580` loses a rank-22 GT neighbor even when `nprobe=400`.

The next most useful diagnostic is a targeted local-boundary review for the stable regressions, starting with queries `580` and `500`. The concrete question is whether the lost GT ids are being displaced by a small set of false positives with systematically lower custom approximate distances, and whether that displacement is caused by the `128-384` / `384-704` boundary or by the 4-segment shape as a whole.

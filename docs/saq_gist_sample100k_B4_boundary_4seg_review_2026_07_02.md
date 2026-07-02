# GIST sample100k B=4 boundary_4seg Per-Query and Segment Attribution Review

Date: 2026-07-02

Plan under review:

```text
boundary_4seg = 128:9,384:5,320:2,128:0
```

This plan came from the boundary-aware residual DP prototype. Its aggregate metrics looked promising: it slightly improved np200 R@100 over default and had the best mean relative error among the tested plans. This review checks whether the aggregate improvement also fixes the persistent per-query failures seen in the residual-aggressive plan.

## 1. Aggregate Per-Query Comparison

All rows compare `boundary_4seg` against the default SAQ B=4 plan on `gist_sample100k`, IVF512, PCA-space vectors, R@100, and top1000 sample groundtruth.

| nprobe | default R@100 | boundary R@100 | delta | lost events | gained events | worse q | better q | equal q | mean overlap | worst q delta | best q delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20 | 0.759150 | 0.759060 | -0.000090 | 87 | 78 | 57 | 58 | 885 | 98.97 | 35:-3 | 367:+2 |
| 50 | 0.927500 | 0.927420 | -0.000080 | 221 | 213 | 133 | 145 | 722 | 98.82 | 35:-3 | 41:+2 |
| 100 | 0.980870 | 0.980750 | -0.000120 | 477 | 465 | 230 | 223 | 547 | 98.79 | 35:-3 | 132:+3 |
| 200 | 0.990870 | 0.991010 | +0.000140 | 626 | 640 | 258 | 271 | 471 | 98.79 | 35:-3 | 132:+3 |
| 400 | 0.991190 | 0.991390 | +0.000200 | 637 | 657 | 255 | 275 | 470 | 98.78 | 35:-3 | 132:+3 |

Readout:

- At low nprobe, boundary_4seg is slightly below default.
- At np200 and np400, boundary_4seg becomes positive because gained GT@100 events slightly exceed lost events.
- The improvement is smaller than `eq_s0_to_s1`, but boundary_4seg previously had much better mean relative error and QPS.

## 2. Persistent Query Behavior

| comparison vs default | persistent worse queries | ever worse queries | persistent better queries |
|---|---:|---:|---:|
| residual_aggressive | 63 | 314 | 34 |
| eq_s0_to_s1 | 33 | 292 | 41 |
| boundary_4seg | 43 | 319 | 41 |

Boundary_4seg fixes most, but not all, of the residual-aggressive persistent failures:

```text
fixed residual persistent-worse queries: 53 / 63
still residual persistent-worse: [651, 739, 813, 958, 961, 962, 966, 974, 981, 983]
new boundary persistent-worse: [35, 75, 80, 89, 101, 107, 160, 189, 230, 244, 281, 332, 360, 373, 450, 451, 459, 481, 551, 559, 573, 616, 645, 682, 684, 711, 728, 729, 840, 852, 880, 905, 925]
```

Behavior of boundary_4seg on the 63 residual persistent-worse queries:

| nprobe | better | equal | worse | total delta hits |
|---:|---:|---:|---:|---:|
| 20 | 3 | 49 | 11 | -8 |
| 50 | 6 | 44 | 13 | -8 |
| 100 | 7 | 34 | 22 | -16 |
| 200 | 10 | 26 | 27 | -20 |
| 400 | 10 | 27 | 26 | -18 |

This is a partial fix. Compared with residual-aggressive, boundary_4seg reduces the persistent-worse count from 63 to 43, but it is not as clean as `eq_s0_to_s1`, which reduced it to 33 and fixed the canonical query 974 failure at the membership level.

## 3. Query 974 Check

Query 974 was the canonical residual-aggressive persistent failure. Residual-aggressive lost four GT@100 ids at every nprobe. `eq_s0_to_s1` fixed it completely. Boundary_4seg improves it, but does not eliminate it.

| nprobe | boundary delta | lost ids | gained ids |
|---:|---:|---|---|
| 20 | -1 | `30993` | `` |
| 50 | -1 | `30993` | `` |
| 100 | -1 | `30993` | `` |
| 200 | -1 | `30993` | `` |
| 400 | -1 | `30993` | `` |

For the lost id `30993` at GT rank 94, the custom total error is strongly negative:

| nprobe | pid | rank | custom total error | delta custom-default error | dominant segment errors |
|---:|---:|---:|---:|---:|---|
| 20 | 30993 | 94 | -0.007681 | -0.015079 | `0-128: -0.004556`, `128-512: -0.002366`, `512-832: -0.000676` |
| 200 | 30993 | 94 | -0.007681 | -0.015079 | `0-128: -0.004556`, `128-512: -0.002366`, `512-832: -0.000676` |
| 400 | 30993 | 94 | -0.007681 | -0.015079 | `0-128: -0.004556`, `128-512: -0.002366`, `512-832: -0.000676` |

The same lost id appears at every nprobe, so this is a stable boundary case rather than a search-depth artifact.

## 4. Query 35 Check

Query 35 is the worst boundary_4seg query. It is a new persistent failure and loses the same three GT ids at every nprobe.

| nprobe | boundary delta | lost ids | gained ids |
|---:|---:|---|---|
| 20 | -3 | `96067;96774;94660` | `` |
| 50 | -3 | `96067;96774;94660` | `` |
| 100 | -3 | `96067;96774;94660` | `` |
| 200 | -3 | `96067;96774;94660` | `` |
| 400 | -3 | `96067;96774;94660` | `` |

Segment attribution for the lost ids shows that the wide `128-512` segment dominates most of the error:

| pid | rank | custom total error | delta custom-default error | dominant segment errors |
|---:|---:|---:|---:|---|
| 96067 | 25 | -0.000894 | -0.002352 | `128-512: -0.000801` with 90% abs-error share |
| 96774 | 33 | -0.000839 | +0.000440 | `128-512: -0.000873`, `512-832: +0.000437` |
| 94660 | 40 | -0.000608 | -0.001957 | `128-512: -0.000559`, `0-128: +0.000288` |

This is the clearest sign that the merged `128-512` segment is too coarse for some boundary cases.

## 5. Segment Attribution at np200

Custom-plan lost events at np200:

| plan | segment | bits | count | mean error | mean abs error | abs share | positive frac |
|---|---|---:|---:|---:|---:|---:|---:|
| residual_aggressive | 0-64 | 9 | 592 | 0.0000607 | 0.000374 | 0.148 | 0.583 |
| residual_aggressive | 64-320 | 6 | 592 | 0.000751 | 0.001082 | 0.364 | 0.755 |
| residual_aggressive | 320-576 | 4 | 592 | 0.000219 | 0.000689 | 0.219 | 0.630 |
| residual_aggressive | 576-832 | 2 | 592 | 0.000293 | 0.000561 | 0.170 | 0.633 |
| residual_aggressive | 832-960 | 0 | 592 | 0.000103 | 0.000311 | 0.098 | 0.627 |
| eq_s0_to_s1 | 0-64 | 8 | 558 | 0.000470 | 0.000770 | 0.256 | 0.733 |
| eq_s0_to_s1 | 64-128 | 7 | 558 | 0.000102 | 0.000376 | 0.129 | 0.602 |
| eq_s0_to_s1 | 128-320 | 6 | 558 | 0.000284 | 0.000540 | 0.175 | 0.658 |
| eq_s0_to_s1 | 320-576 | 4 | 558 | 0.000391 | 0.000686 | 0.193 | 0.645 |
| eq_s0_to_s1 | 576-832 | 2 | 558 | 0.000395 | 0.000629 | 0.158 | 0.659 |
| eq_s0_to_s1 | 832-960 | 0 | 558 | 0.0000971 | 0.000346 | 0.088 | 0.590 |
| boundary_4seg | 0-128 | 9 | 626 | 0.000110 | 0.000340 | 0.166 | 0.597 |
| boundary_4seg | 128-512 | 5 | 626 | 0.000841 | 0.001149 | 0.430 | 0.765 |
| boundary_4seg | 512-832 | 2 | 626 | 0.000546 | 0.000842 | 0.290 | 0.687 |
| boundary_4seg | 832-960 | 0 | 626 | 0.000114 | 0.000306 | 0.114 | 0.570 |

Boundary_4seg improves the first 128 dimensions by giving them 9 bits, but it pays for that by making `128-512` a wide 5-bit segment. On lost events, this segment accounts for 43.0% of the custom absolute error at np200, and it has a 76.5% positive-error fraction. The next segment, `512-832` at 2 bits, contributes another 29.0%.

Custom-plan gained events at np200:

| plan | segment | bits | count | mean error | mean abs error | abs share | positive frac |
|---|---|---:|---:|---:|---:|---:|---:|
| boundary_4seg | 0-128 | 9 | 640 | -0.0000697 | 0.000328 | 0.190 | 0.447 |
| boundary_4seg | 128-512 | 5 | 640 | -0.000270 | 0.000868 | 0.386 | 0.414 |
| boundary_4seg | 512-832 | 2 | 640 | -0.000234 | 0.000699 | 0.286 | 0.422 |
| boundary_4seg | 832-960 | 0 | 640 | 0.0000879 | 0.000344 | 0.139 | 0.588 |

The same wide middle segment helps some gained events and hurts some lost events. That explains why aggregate recall becomes slightly positive while persistent failures remain.

## 6. Decision

Do not promote boundary_4seg as the final custom plan.

It is still useful because it gives the best aggregate error/recall tradeoff among the automatic planner variants tested so far:

```text
np200 R@100: 0.991010
err_tot_avg: 0.000463861
```

But the per-query review shows two remaining problems:

1. It only partially fixes residual-aggressive persistent failures: 43 persistent-worse queries remain.
2. It introduces a new stable worst query, query 35, where the wide `128-512` segment dominates the error.

The next planner change should not simply increase the global segment penalty. Strong penalty already produced the 3-segment plan `192:8,320:4,448:2`, whose recall dropped to `0.989840` at np200. The better direction is boundary-aware DP v2 with an additional within-segment risk term, for example a max-block or tail-block penalty inside a segment. That would discourage wide risky segments like `128-512` without forcing the whole plan to collapse into too few segments.

Follow-up status: v2 has now been implemented and reviewed in `docs/saq_boundary_aware_dp_v2_intra_segment_2026_07_02.md`. The v2 candidate `64:9,64:7,128:6,320:4,256:2,128:0` fixes the wide `128-512` failure mode and improves the aggregate recall/error tradeoff, but it introduces a QPS cost and leaves new per-query tail cases.

## 7. Artifacts

Per-query compare CSVs:

```text
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_compare_np20_top100.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_compare_np50_top100.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_compare_np100_top100.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_compare_np200_top100.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_compare_np400_top100.csv
```

Segment attribution:

```text
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_segment_attribution_events.csv
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_segment_attribution_summary.csv
```

Merged review summary:

```text
/tmp/saq-run/reports/gist_sample100k_B4_boundary_4seg_review_summary.json
```

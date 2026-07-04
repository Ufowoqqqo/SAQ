# GIST Sample100k B=5 `b5_rank0` Safe-Searcher Review

Date: 2026-07-04

## 1. Question

The safe-searcher corrected leaderboard changed the B=5 conclusion. The previous practical winner `b5_rank1` no longer improves recall under:

```text
-searcher_safe_block_min_mode=2
```

The corrected B=5 recall winner is:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

This review checks whether `b5_rank0` is a stable aggregate improvement or whether it hides severe per-query regressions.

## 2. Setup

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 5
PCA = true
groundtruth = sample-specific top1000 GT
metric = R@100
nprobe = 20, 50, 100, 200, 400
searcher = -searcher_safe_block_min_mode=2
```

Default B=5 plan:

```text
default_b5 = 64:11,192:7,320:5,320:3,64:0
```

Compared with default, `b5_rank0` moves one bit from `0-64` to `64-256`, and moves the 5-bit to 3-bit boundary from 576 to 512:

```text
default_b5: 0-64:11, 64-256:7, 256-576:5, 576-896:3, 896-960:0
b5_rank0:  0-64:10, 64-256:8, 256-512:5, 512-896:3, 896-960:0
```

## 3. Aggregate Per-Query Comparison

All rows use the safe searcher.

| nprobe | default R@100 | b5_rank0 R@100 | delta | lost GT | gained GT | worse queries | better queries | worst query | best query |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20 | 0.75972 | 0.75979 | +0.00007 | 5 | 12 | 5 | 12 | 194:-1 | 926:+1 |
| 50 | 0.92900 | 0.92908 | +0.00008 | 45 | 53 | 33 | 43 | 155:-2 | 821:+2 |
| 100 | 0.98396 | 0.98413 | +0.00017 | 146 | 163 | 95 | 114 | 155:-2 | 988:+2 |
| 200 | 0.99478 | 0.99521 | +0.00043 | 236 | 279 | 145 | 186 | 155:-2 | 988:+2 |
| 400 | 0.99516 | 0.99561 | +0.00045 | 238 | 283 | 144 | 188 | 155:-2 | 988:+2 |

At nprobe 200, the delta-hit distribution is:

| delta hits | query count |
|---:|---:|
| -2 | 9 |
| -1 | 136 |
| 0 | 669 |
| +1 | 175 |
| +2 | 11 |

This is a boundary-only improvement profile. There are no large negative outliers like the earlier native-searcher `b5_rank1` q580/q500 failures.

## 4. Persistent Query Behavior

Across all five nprobe values:

| query set | count |
|---|---:|
| ever worse | 154 |
| ever better | 206 |
| persistently worse | 5 |
| persistently better | 11 |

Persistent worse queries:

```text
194, 281, 359, 367, 728
```

At nprobe 200:

| query | delta | lost GT ids | lost min rank |
|---:|---:|---|---:|
| 194 | -1 | `44984` | 98 |
| 281 | -1 | `64738` | 99 |
| 359 | -2 | `75533;33145` | 98 |
| 367 | -1 | `73989` | 99 |
| 728 | -1 | `9363` | 99 |

Persistent better queries:

```text
10, 167, 190, 286, 330, 484, 485, 509, 568, 571, 926
```

Most persistent changes are rank-98/99 boundary cases. The only persistent better query with an earlier gained rank is query 167, which gains a rank-79 GT neighbor at nprobe 200.

## 5. Worst Query: 155

Query 155 is the worst query from nprobe 50 onward, but the loss is small and not present at nprobe 20.

| nprobe | default hits | b5_rank0 hits | delta | lost GT ids |
|---:|---:|---:|---:|---|
| 20 | 95 | 95 | 0 | `` |
| 50 | 100 | 98 | -2 | `95810;49413` |
| 100 | 100 | 98 | -2 | `95810;49413` |
| 200 | 100 | 98 | -2 | `95810;49413` |
| 400 | 100 | 98 | -2 | `95810;49413` |

The lost GT ranks are 97 and 98.

Segment attribution at nprobe 200:

| pid | GT rank | custom total error | delta custom-default error | dominant custom segment errors |
|---:|---:|---:|---:|---|
| 95810 | 97 | -0.000088 | -0.000015 | `256-512: -0.000090` with 83.5% abs-error share |
| 49413 | 98 | +0.000198 | +0.000126 | `256-512: +0.000176` with 77.2% abs-error share |

Query 155 is therefore a tight boundary case dominated by the `256-512:5b` segment. It is not a head-dimension or zero-tail failure.

## 6. Best Query: 988

Query 988 is the best query at nprobe 100/200/400.

| nprobe | default hits | b5_rank0 hits | delta | gained GT ids |
|---:|---:|---:|---:|---|
| 20 | 95 | 95 | 0 | `` |
| 50 | 97 | 98 | +1 | `37214` |
| 100 | 98 | 100 | +2 | `37214;91377` |
| 200 | 98 | 100 | +2 | `37214;91377` |
| 400 | 98 | 100 | +2 | `37214;91377` |

The gained GT ranks are 98 and 99.

Segment attribution at nprobe 200:

| pid | GT rank | custom total error | delta custom-default error | dominant custom segment errors |
|---:|---:|---:|---:|---|
| 37214 | 98 | -0.000024 | -0.000838 | `256-512: -0.000581`, `512-896: +0.000337`, `64-256: +0.000301` |
| 91377 | 99 | -0.000908 | -0.001098 | `256-512: -0.000613`, `512-896: -0.000455` |

The best-case gains are again mid/tail-boundary effects, mainly the `256-512` and `512-896` custom segments.

## 7. Segment Attribution at nprobe 200

Custom-plan lost events: 236.

| segment | bits | mean error | mean abs error | abs-error share | positive error frac |
|---|---:|---:|---:|---:|---:|
| 0-64 | 10 | +0.0000586 | 0.0001778 | 0.132 | 0.589 |
| 64-256 | 8 | +0.0001113 | 0.0002338 | 0.174 | 0.648 |
| 256-512 | 5 | +0.0003722 | 0.0005388 | 0.345 | 0.775 |
| 512-896 | 3 | +0.0003033 | 0.0004318 | 0.251 | 0.725 |
| 896-960 | 0 | +0.0000246 | 0.0001582 | 0.098 | 0.572 |

Custom-plan gained events: 279.

| segment | bits | mean error | mean abs error | abs-error share | positive error frac |
|---|---:|---:|---:|---:|---:|
| 0-64 | 10 | -0.0000018 | 0.0001737 | 0.153 | 0.470 |
| 64-256 | 8 | +0.0000081 | 0.0002107 | 0.176 | 0.538 |
| 256-512 | 5 | -0.0001611 | 0.0004432 | 0.321 | 0.362 |
| 512-896 | 3 | -0.0001294 | 0.0003560 | 0.242 | 0.405 |
| 896-960 | 0 | +0.0000505 | 0.0001734 | 0.108 | 0.573 |

Readout:

- Both lost and gained events are dominated by the middle custom segments, especially `256-512:5b` and `512-896:3b`.
- For lost events, these segments have positive mean error, making true GT neighbors look farther away.
- For gained events, these segments have negative mean error, making true GT neighbors look closer.
- The zero tail `896-960:0b` is not the dominant source of either gains or losses.
- The extra bit in `64-256:8b` is not by itself the whole story; the main observed ranking movement is in the `256-896` boundary region.

## 8. Decision

`b5_rank0` is a credible corrected B=5 recall candidate:

```text
R@100 np200: 0.99521 vs default 0.99478
delta: +0.00043
QPS ratio: 0.993x
worst query at np200: -2 hits
```

It should replace `b5_rank1` as the B=5 recall-oriented candidate in the current narrative. The improvement is modest, but it is stable at nprobe 100/200/400 and does not hide a severe per-query regression.

The right caveat is that `b5_rank0` is still a boundary-case plan. At nprobe 200, lost events have mean GT rank 97.73 and gained events have mean GT rank 98.07. This is not a broad ranking reshaping; it is a small but favorable shift around the top-100 cutoff.

## 9. Artifacts

Safe compare CSVs:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_compare_np20_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_compare_np50_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_compare_np100_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_compare_np200_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_compare_np400_top100.csv
```

Safe segment attribution:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_segment_attribution_events.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank0_safeblockminsimd_segment_attribution_summary.csv
```

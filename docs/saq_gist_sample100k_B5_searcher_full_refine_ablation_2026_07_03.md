# GIST Sample100k B=5 Searcher Full-Refinement Ablation

Date: 2026-07-03

This note tests whether the bad `b5_rank1` query-level regressions are caused by the quantization plan itself or by the search-time multi-stage pruning path.

Plan under test:

```text
b5_rank1 = 128:10,256:6,320:4,256:2
```

Default B=5 plan:

```text
default_b5 = 64:11,192:7,320:5,320:3,64:0
```

## 1. Code Changes

I added two searcher ablation flags:

| flag | behavior | intended use |
|---|---|---|
| `-searcher_full_refine=true` | disables the per-segment early break inside accurate refinement | test whether partial full-code refinement is unsafe |
| `-searcher_force_accurate_scan=true` | computes full-code distances for all candidates in the probed IVF clusters | correctness oracle for searcher pruning |

The flags are wired through `SearcherConfig` and are available to:

```text
compare_search_results
replacement_attribution
segment_attribution
test_qps
test_relative_error
```

Relevant source locations:

```text
saqlib/quantization/config.h
saqlib/quantization/saq_searcher.hpp
src/define_options.h
src/compare_search_results.cpp
src/replacement_attribution.cpp
src/segment_attribution.cpp
src/test_qps.cpp
src/test_relative_error.cpp
```

## 2. Experiment Setup

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 5
PCA = true
metric = R@100
test nprobe = 20,50,100,200,400
QPS nprobe = 200
QPS threads = 24
```

Raw local artifacts:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_fullrefine_compare_np{20,50,100,200,400}_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_accuratescan_compare_np{20,50,100,200,400}_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_fullrefine_replacement_items_q580_q500_np200.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_accuratescan_replacement_items_q580_q500_np200.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_searcher_ablation_summary.json
/tmp/saq-run/results/saq/qps_gist_sample100k_*_np200_sm4*.csv
```

## 3. Recall Results

Current searcher, before this ablation:

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.758330 | 0.759500 | +0.001170 | 580 | -8 |
| 50 | 0.927440 | 0.928660 | +0.001220 | 580 | -8 |
| 100 | 0.982540 | 0.983490 | +0.000950 | 580 | -8 |
| 200 | 0.993370 | 0.994450 | +0.001080 | 580 | -8 |
| 400 | 0.993740 | 0.994820 | +0.001080 | 580 | -8 |

`searcher_full_refine=true`:

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.758340 | 0.759500 | +0.001160 | 580 | -8 |
| 50 | 0.927480 | 0.928670 | +0.001190 | 580 | -8 |
| 100 | 0.982600 | 0.983500 | +0.000900 | 580 | -8 |
| 200 | 0.993440 | 0.994460 | +0.001020 | 580 | -8 |
| 400 | 0.993810 | 0.994830 | +0.001020 | 580 | -8 |

`searcher_force_accurate_scan=true`:

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.759870 | 0.759890 | +0.000020 | 16 | -1 |
| 50 | 0.929360 | 0.929410 | +0.000050 | 15 | -1 |
| 100 | 0.984390 | 0.984340 | -0.000050 | 449 | -2 |
| 200 | 0.995150 | 0.995270 | +0.000120 | 230 | -2 |
| 400 | 0.995530 | 0.995650 | +0.000120 | 230 | -2 |

## 4. Query 580/500 Check

At `nprobe=200`, current searcher and full-refine mode both keep the same stable failures:

| mode | query | default hits | b5_rank1 hits | delta | lost GT |
|---|---:|---:|---:|---:|---|
| current | 580 | 100 | 92 | -8 | `99498;99942;99496;99506;99497;99503;99502;99501` |
| current | 500 | 100 | 94 | -6 | `99507;99501;99496;99497;99503;99502` |
| full-refine | 580 | 100 | 92 | -8 | same as current |
| full-refine | 500 | 100 | 94 | -6 | same as current |
| accurate-scan | 580 | 100 | 100 | 0 | none |
| accurate-scan | 500 | 100 | 100 | 0 | none |

This rules out the narrow hypothesis that the per-segment accurate-refinement early break is the only cause. The lost GT are being removed before that point, most likely by the variance/fast-stage block/vector pruning path.

## 5. QPS Results at nprobe=200

| mode | plan | R@100 | QPS | avg query ms | relative QPS vs current same plan |
|---|---|---:|---:|---:|---:|
| current | default_b5 | 0.993370 | 9075.9 | 2.644 | 1.00x |
| current | b5_rank1 | 0.994450 | 10364.4 | 2.316 | 1.00x |
| full-refine | default_b5 | 0.993440 | 7509.1 | 3.196 | 0.83x |
| full-refine | b5_rank1 | 0.994460 | 9127.7 | 2.629 | 0.88x |
| accurate-scan | default_b5 | 0.995150 | 1810.3 | 13.258 | 0.20x |
| accurate-scan | b5_rank1 | 0.995270 | 1566.0 | 15.326 | 0.15x |

Readout:

- `full_refine` is not enough to fix query 580/500 and costs roughly 12-17% QPS at np200.
- `accurate_scan` fixes query 580/500 and raises both plans' recall, but costs roughly 5-7x QPS.
- Under accurate scan, `b5_rank1`'s large apparent advantage mostly disappears: at np200 the delta is only `+0.000120` instead of current searcher's `+0.001080`.

## 6. Interpretation

The original replacement-level diagnostic showed:

```text
For query 580/500, lost GT remain in b5_rank1 custom full-code top100.
Replacement false positives remain outside custom full-code top100.
```

This ablation refines that conclusion:

```text
The issue is not only partial accurate-refinement early break.
The issue is earlier search-stage pruning, because only full accurate scan over all probed candidates recovers the lost GT.
```

This matters for interpreting the boundary-plan work. A plan can look better or worse under the current `IVF::search` because it interacts with fast-stage pruning, not because its full-code distance estimator is intrinsically better or worse.

## 7. Decision

Do not continue broad plan sweeps until the searcher pruning question is isolated. The current searcher can mask the true quality of a quantization plan.

The next useful step is to instrument the pruning path directly:

1. Count how many candidates are rejected at variance block prune, fast-stage block prune, vector-level `curr_dist[j] < distk`, and accurate-refinement break.
2. For selected query ids `580` and `500`, log which stage rejects each lost GT.
3. Use that evidence to design a safer fast-stage pruning bound, instead of falling back to full accurate scan.

A production fix cannot simply use `searcher_force_accurate_scan=true`, because it is too slow. The viable path is a calibrated lower-bound or conservative pruning rule that recovers most of the accurate-scan recall without paying the full 5-7x slowdown.

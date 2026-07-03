# GIST Sample100k B=5 `b5_rank1` Replacement-Level Diagnostic

Date: 2026-07-03

This note follows the per-query review of the B=5 candidate:

```text
b5_rank1 = 128:10,256:6,320:4,256:2
```

The target bad queries are `580` and `500`, the two stable worst regressions against the default B=5 plan.

## 1. Diagnostic Tool

I added a focused C++ diagnostic:

```text
src/replacement_attribution.cpp
bin/replacement_attribution
```

It compares default vs custom search results and writes three CSVs:

| artifact | purpose |
|---|---|
| `items.csv` | lost GT and custom-only replacement items, with exact distance, actual search rank, full-code rank, fast rank, and variance-bound rank |
| `segments.csv` | per-segment true / approximate distance and signed error for each item |
| `pairs.csv` | every lost-GT vs replacement pair, with exact and approximate margins |

For the main run:

```text
dataset = gist_sample100k
K = 512
B = 5
PCA = true
topk = 100
nprobe = 20,50,100,200,400
queries = 580,500
searcher_vars_bound_m = 4
```

Raw local outputs:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_replacement_items_q580_q500.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_replacement_segments_q580_q500.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_replacement_pairs_q580_q500.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_replacement_review_q580_q500_summary.json
```

I also ran sensitivity checks:

```text
searcher_vars_bound_m = 8,16,32 at topk=100, nprobe=200
topk = 200 and 1000 at nprobe=200
```

## 2. Main Finding

The stable regressions are not caused by the custom full-code distance estimator ranking the replacements ahead of the lost GT.

For both query `580` and query `500`:

```text
All old top100 lost GT are still inside custom full-code top100.
All custom replacement false positives are outside custom full-code top100.
Actual IVF::search still returns the replacements and drops the lost GT.
```

This means the problem is in the search-time multi-stage pruning/refinement path, not in the final full-code distance ordering.

At `nprobe=200`:

| query | lost GT | replacement FP | lost GT in custom full-code top100 | replacement FP in custom full-code top100 | custom pair inversions |
|---:|---:|---:|---:|---:|---:|
| 580 | 8 | 8 | 8/8 | 0/8 | 0/64 |
| 500 | 6 | 6 | 6/6 | 0/6 | 0/36 |

Here, a custom pair inversion means:

```text
replacement exact distance > lost GT exact distance
but replacement custom full-code approximate distance < lost GT custom full-code approximate distance
```

There are zero such inversions for both queries.

## 3. Query 580 at nprobe=200

Lost GT:

| pid | GT rank | default search rank | custom search rank | custom full-code rank | custom fast rank | exact minus GT@100 dist |
|---:|---:|---:|---:|---:|---:|---:|
| 99498 | 22 | 22 | -1 | 22 | 9 | -0.04649730 |
| 99942 | 34 | 34 | -1 | 34 | 64 | -0.03849980 |
| 99496 | 44 | 44 | -1 | 44 | 61 | -0.03329590 |
| 99506 | 68 | 68 | -1 | 68 | 66 | -0.01588440 |
| 99497 | 73 | 73 | -1 | 73 | 96 | -0.01007940 |
| 99503 | 84 | 84 | -1 | 84 | 75 | -0.00620575 |
| 99502 | 85 | 85 | -1 | 85 | 81 | -0.00609531 |
| 99501 | 99 | 99 | -1 | 99 | 140 | +0.00000001 |

Replacement false positives:

| pid | GT rank | custom search rank | custom full-code rank | custom fast rank | exact minus GT@100 dist |
|---:|---:|---:|---:|---:|---:|
| 99425 | 100 | 92 | 100 | 146 | +0.00039631 |
| 19798 | 101 | 93 | 101 | 103 | +0.00119108 |
| 47344 | 102 | 94 | 102 | 102 | +0.00149639 |
| 51921 | 103 | 95 | 103 | 36 | +0.00189142 |
| 10439 | 104 | 96 | 104 | 118 | +0.00281198 |
| 47466 | 105 | 97 | 105 | 92 | +0.00331119 |
| 79146 | 106 | 98 | 106 | 135 | +0.00352558 |
| 51209 | 108 | 99 | 107 | 136 | +0.00380519 |

Readout:

- The custom full-code ranking exactly preserves the old top100 GT membership for these items.
- The actual custom search drops all eight lost GT and admits GT ranks `100,101,102,103,104,105,106,108`.
- Several lost GT have excellent fast ranks, for example pid `99498` has custom fast rank `9`, so the issue is not simply that all lost GT look bad under the first-bit approximation.

## 4. Query 500 at nprobe=200

Lost GT:

| pid | GT rank | default search rank | custom search rank | custom full-code rank | custom fast rank | exact minus GT@100 dist |
|---:|---:|---:|---:|---:|---:|---:|
| 99507 | 29 | 29 | -1 | 29 | 53 | -0.01705300 |
| 99501 | 37 | 37 | -1 | 37 | 62 | -0.01446420 |
| 99496 | 66 | 66 | -1 | 66 | 59 | -0.00594935 |
| 99497 | 87 | 87 | -1 | 87 | 117 | -0.00108221 |
| 99503 | 92 | 92 | -1 | 92 | 63 | -0.00058082 |
| 99502 | 93 | 93 | -1 | 93 | 57 | -0.00051598 |

Replacement false positives:

| pid | GT rank | custom search rank | custom full-code rank | custom fast rank | exact minus GT@100 dist |
|---:|---:|---:|---:|---:|---:|
| 17690 | 100 | 94 | 100 | 85 | +0.00022636 |
| 65799 | 101 | 95 | 101 | 137 | +0.00034176 |
| 24290 | 102 | 96 | 102 | 92 | +0.00040109 |
| 38922 | 103 | 97 | 103 | 71 | +0.00072553 |
| 75313 | 104 | 98 | 104 | 83 | +0.00098391 |
| 94595 | 106 | 99 | 106 | 193 | +0.00149158 |

Readout:

- Same pattern as query `580`: custom full-code ranking would keep all six lost GT in top100.
- Actual `IVF::search` drops them and admits near-boundary false positives.

## 5. Segment Attribution at nprobe=200

Custom plan, query `580`:

| role | segment | bits | mean error | mean abs error | positive frac | mean abs share |
|---|---|---:|---:|---:|---:|---:|
| lost GT | 0-128 | 10 | +0.00000354 | 0.00001971 | 0.625 | 0.474 |
| lost GT | 128-384 | 6 | +0.00000331 | 0.00001503 | 0.750 | 0.372 |
| lost GT | 384-704 | 4 | -0.00000183 | 0.00000557 | 0.625 | 0.127 |
| lost GT | 704-960 | 2 | +0.00000015 | 0.00000110 | 0.500 | 0.027 |
| replacement FP | 0-128 | 10 | -0.00000639 | 0.00001312 | 0.500 | 0.338 |
| replacement FP | 128-384 | 6 | +0.00000394 | 0.00000943 | 0.500 | 0.247 |
| replacement FP | 384-704 | 4 | -0.00000098 | 0.00001531 | 0.375 | 0.312 |
| replacement FP | 704-960 | 2 | +0.00000136 | 0.00000382 | 0.375 | 0.103 |

Custom plan, query `500`:

| role | segment | bits | mean error | mean abs error | positive frac | mean abs share |
|---|---|---:|---:|---:|---:|---:|
| lost GT | 0-128 | 10 | +0.00000667 | 0.00001318 | 0.667 | 0.506 |
| lost GT | 128-384 | 6 | +0.00000015 | 0.00000533 | 0.667 | 0.232 |
| lost GT | 384-704 | 4 | -0.00000018 | 0.00000404 | 0.500 | 0.205 |
| lost GT | 704-960 | 2 | -0.00000082 | 0.00000094 | 0.167 | 0.057 |
| replacement FP | 0-128 | 10 | +0.00001001 | 0.00001058 | 0.833 | 0.426 |
| replacement FP | 128-384 | 6 | +0.00000612 | 0.00000894 | 0.500 | 0.345 |
| replacement FP | 384-704 | 4 | -0.00000130 | 0.00000298 | 0.167 | 0.146 |
| replacement FP | 704-960 | 2 | -0.00000111 | 0.00000171 | 0.333 | 0.083 |

The segment-level errors are small and do not explain the actual search result by full-code ranking. They remain useful for understanding the estimator, but the decisive issue is now search-stage pruning/refinement.

## 6. Source-Level Interpretation

The relevant code path is:

```text
saqlib/index/ivf.hpp
  IVF::search(...)
    SAQSearcher::searchCluster(...)

saqlib/quantization/saq_searcher.hpp
  SAQSearcher::searchCluster(...)
```

The suspicious block is the accurate refinement loop:

```cpp
float acc_dist = curr_dist[j];
for (size_t c_i = 0; c_i < clus_num; ++c_i) {
    auto &estimator = estimators_[c_i];
    acc_dist += estimator.compAccurateDist(idx) - clu_dist_[c_i * KFastScanSize + j];
    if (acc_dist >= distk) {
        break;
    }
}
KNNs.insert(saq_clust->ids()[idx], acc_dist);
```

This assumes that once the partial refined distance exceeds `distk`, later segment corrections cannot bring it back below `distk`. That is not guaranteed: a later segment can have a negative correction relative to the fast estimate. Therefore the loop can reject a vector whose final full-code distance would be inside top-k.

The diagnostic result is consistent with that failure mode:

- `IVF::estimate`, which computes full accurate distances for all probed candidates, ranks the lost GT inside top100.
- `IVF::search`, which uses multi-stage pruning/refinement, drops those same ids.
- Raising `searcher_vars_bound_m` from `4` to `8/16/32` does not fix the issue, so this is not just the initial variance-bound pruning.
- Increasing requested `topk` to `200` or `1000` still does not recover the original lost GT, so the failure is persistent in the search-stage path.

## 7. Decision

The previous B=5 conclusion should be refined:

```text
b5_rank1's full-code custom estimator is not responsible for query 580/500 losing those GT neighbors.
The actual recall loss appears to be caused by the multi-stage search implementation.
```

This is an important distinction. It means `b5_rank1` may be a better quantization plan than the actual `IVF::search` result suggests, but the current searcher can fail to realize that quality.

## 8. Next Step

The next step should be a searcher-level ablation:

1. Add a safe/full-refinement search mode that disables the per-segment `if (acc_dist >= distk) break` during accurate refinement.
2. Re-run default vs `b5_rank1` for GIST B=5 at the same nprobes.
3. Compare recall and QPS against the current multi-stage searcher.
4. If recall recovers with tolerable QPS cost, design a safer pruning condition using a valid lower bound on remaining segment corrections.

This is now higher priority than another boundary-plan sweep, because the current search path can mask the true quality of a quantization plan.

# GIST Sample100k B=5 Safe Block-Min Ablation

## 1. Question

The pruning trace in `docs/saq_gist_sample100k_B5_pruning_trace_2026_07_03.md` showed that the bad query 580/500 losses for `b5_rank1` were not caused by full-code refinement. The lost GT vectors were skipped before vector-level refinement because the fast-stage block-min value `mi` became `nan`, making this guard false:

```cpp
if (mi <= distk) {
    // vector-level filtering and accurate refinement
}
```

This ablation asks whether a NaN-safe block-min path changes the apparent default-vs-custom comparison.

## 2. Implementation

Added a searcher flag:

```text
-searcher_safe_block_min=true
```

Code path:

- `SearcherConfig::searcher_safe_block_min`
- `SAQSearcher::blockMin(...)`
- CLI flag in `src/define_options.h`

Default behavior is unchanged. When the flag is false, the searcher still uses the original AVX512 reduction:

```cpp
_mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]))
```

When the flag is true, the searcher stores the 32 lanes, skips NaN/Inf by raw IEEE754 bit pattern, and computes a finite scalar min over the valid lanes in the block. This fallback is used only for the multi-segment block-min gate; full-code refinement and code layout are unchanged.

The diagnostic tracer also honors the same flag, so it can replay either the current or safe block-min path.

## 3. Commands

Recall comparison, current and safe:

```bash
/rwproject/kdd-db/kluaq/saq/bin/compare_search_results \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -seg_plan=128:10,256:6,320:4,256:2 \
  -compare_topk=100 \
  -compare_nprobe=${NP} \
  -compare_output=/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_${MODE}_compare_np${NP}_top100.csv
```

For safe mode, add:

```bash
-searcher_safe_block_min=true
```

QPS comparison at nprobe 200:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -fix_thread=24 \
  -fix_nprobe=200
```

For `b5_rank1`, add:

```bash
-seg_plan=128:10,256:6,320:4,256:2
```

For safe mode, add:

```bash
-searcher_safe_block_min=true
```

## 4. Recall Results

All rows use PCA-space `gist_sample100k`, IVF512, B=5, top100 GT, and R@100.

### Current Searcher

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta hits |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.758330 | 0.759500 | +0.001170 | 580 | -8 |
| 50 | 0.927440 | 0.928660 | +0.001220 | 580 | -8 |
| 100 | 0.982540 | 0.983490 | +0.000950 | 580 | -8 |
| 200 | 0.993370 | 0.994450 | +0.001080 | 580 | -8 |
| 400 | 0.993740 | 0.994820 | +0.001080 | 580 | -8 |

### Safe Block-Min Searcher

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta hits |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.759720 | 0.759740 | +0.000020 | 16 | -1 |
| 50 | 0.929000 | 0.929010 | +0.000010 | 38 | -2 |
| 100 | 0.983960 | 0.983820 | -0.000140 | 38 | -2 |
| 200 | 0.994780 | 0.994760 | -0.000020 | 38 | -2 |
| 400 | 0.995160 | 0.995130 | -0.000030 | 38 | -2 |

## 5. Query 580/500 Check

At nprobe 200:

| mode | query | default hits | b5_rank1 hits | delta hits |
|---|---:|---:|---:|---:|
| current | 580 | 100 | 92 | -8 |
| current | 500 | 100 | 94 | -6 |
| safe block-min | 580 | 100 | 100 | 0 |
| safe block-min | 500 | 100 | 100 | 0 |

So the exact queries found by the pruning trace are recovered by the safe block-min path.

## 6. QPS at nprobe 200

Single local run, 24 threads, 10 internal rounds from `test_qps`.

| mode | plan | R@100 | QPS | avg ms/query | relative QPS vs current same plan |
|---|---|---:|---:|---:|---:|
| current | default | 0.993370 | 9090.3 | 2.640 | 1.00x |
| current | b5_rank1 | 0.994450 | 10396.1 | 2.309 | 1.00x |
| safe block-min | default | 0.994780 | 8436.5 | 2.845 | 0.93x |
| safe block-min | b5_rank1 | 0.994760 | 9724.8 | 2.468 | 0.94x |

The safe fallback costs about 6-7% QPS at nprobe 200 in this local setup, far less than force-accurate scan from the earlier ablation.

## 7. Interpretation

Safe block-min changes the story materially:

1. The q580/q500 losses are implementation artifacts in the current search path, not evidence that `b5_rank1` is intrinsically bad for those queries.
2. The large aggregate `b5_rank1` gain under the current searcher is also partly a search-path artifact. Once the block-min gate is made robust, default and `b5_rank1` become nearly tied.
3. Under safe block-min, `b5_rank1` no longer clearly improves recall at B=5; at nprobe 100/200/400 it is slightly below default by `1e-4` or less.
4. The new worst query is much smaller in magnitude: query 38 has `-2` hits, not the previous query 580 `-8` hits.

The main conclusion is therefore not "`b5_rank1` is a better plan". A more defensible conclusion is:

```text
The current multi-stage searcher can silently skip good blocks when the AVX512 block-min reduction/control value becomes NaN. Fixing this removes the severe q580/q500 regressions and makes the B=5 custom plan nearly equivalent to SAQ default.
```

## 8. Next Step

Follow-up completed in `docs/saq_gist_sample100k_B5_block_min_root_cause_and_simd_safe_2026_07_04.md`.

The root cause is now more precise than this first ablation could show:

- The bad q580/q500 block is a partial last block with only 12 valid lanes.
- The valid input lanes are finite, which is why the first trace showed `fast_nonfinite_count = 0`.
- The native reduction performs `_mm512_min_ps(dist[0], dist[1])` before applying a valid-lane mask, so padded high-half lanes can inject NaNs into the pairwise-min vector.
- A low-overhead SIMD-safe reduction masks invalid lanes and replaces non-finite lanes with `FLT_MAX` before the pairwise min.

The SIMD-safe mode matches scalar-safe recall and restores q580/q500 to 100/100 hits at nprobe 200, while the measured QPS is essentially the same as the native path in the local run:

| mode | plan | R@100 | QPS |
|---|---|---:|---:|
| native | default | 0.993370 | 9090.3 |
| native | b5_rank1 | 0.994450 | 10396.1 |
| scalar safe | default | 0.994780 | 8436.5 |
| scalar safe | b5_rank1 | 0.994760 | 9724.8 |
| SIMD safe | default | 0.994780 | 9128.7 |
| SIMD safe | b5_rank1 | 0.994760 | 10379.4 |

Before more planner sweeps, decide whether to treat SIMD-safe block-min as:

1. a production robustness fix to keep enabled, possibly replacing the scalar fallback with a cheaper NaN-safe SIMD reduction; or
2. an ablation-only guard used to separate planner quality from search-path artifacts.

The immediate technical recommendation is to run future planner-quality comparisons with:

```text
-searcher_safe_block_min_mode=2
```

This avoids attributing partial-block reduction artifacts to the quantization plan.

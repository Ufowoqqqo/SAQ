# GIST Sample100k B=5 Block-Min Root Cause and SIMD-Safe Reduction

## 1. Question

The earlier pruning trace showed that `b5_rank1` lost several top-100 ground-truth vectors for queries 580 and 500 because the multi-segment fast-stage block-min gate received `mi = nan` and skipped vector-level refinement:

```cpp
if (mi <= distk) {
    // vector-level filtering and accurate refinement
}
```

The scalar safe fallback recovered those vectors, but it stored and scanned 32 lanes on every block-min check. This note answers two follow-up questions:

1. What is the concrete root cause of the NaN block-min?
2. Can we use a lower-overhead safe reduction instead of the scalar fallback?

## 2. Root Cause

The problematic block is a partial last block in IVF cluster 171:

```text
query ids: 580, 500
cluster id: 171
block index: 16
valid lanes: 12
probe rank: 0
```

The current native reduction is:

```cpp
_mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]))
```

This assumes both 16-lane halves are fully valid. In the partial block above, only lanes `0..11` are valid. Lanes `12..31` are padded/invalid and can contain `NaN`, `Inf`, or stale large finite values.

The earlier trace only counted non-finite values among valid input lanes, so it reported `fast_nonfinite_count = 0`. The new diagnostic checks both the valid input lanes and the 16 lanes after the pairwise `_mm512_min_ps(dist[0], dist[1])`. That reveals the actual failure mode:

| query | stage | valid lanes | input nonfinite | pairwise-min nonfinite | native reduce | SIMD-safe min | scalar finite min |
|---:|---|---:|---:|---:|---:|---:|---:|
| 580 | fast_after_seg0 | 12 | 0 | 4 | NaN | 0.099217318 | 0.099217318 |
| 580 | fast_after_seg1 | 12 | 0 | 4 | NaN | 0.109350234 | 0.109350234 |
| 580 | fast_after_seg2 | 12 | 0 | 4 | NaN | 0.111481912 | 0.111481912 |
| 580 | fast_after_seg3 | 12 | 0 | 4 | NaN | 0.111713454 | 0.111713454 |
| 500 | fast_after_seg0 | 12 | 0 | 4 | NaN | 0.084295556 | 0.084295556 |
| 500 | fast_after_seg1 | 12 | 0 | 4 | NaN | 0.091504164 | 0.091504164 |
| 500 | fast_after_seg2 | 12 | 0 | 4 | NaN | 0.092665292 | 0.092665292 |
| 500 | fast_after_seg3 | 12 | 0 | 4 | NaN | 0.092761323 | 0.092761323 |

So the root cause is not that valid candidate distances become non-finite. The native reduction compares valid low-half lanes with invalid padded high-half lanes before masking by `valid_lanes`, and NaNs from those padded lanes can poison the block-min control value.

## 3. Implementation

Added a mode-based searcher option:

```text
-searcher_safe_block_min_mode=0  # native path, unchanged default
-searcher_safe_block_min_mode=1  # scalar finite min, existing diagnostic fallback
-searcher_safe_block_min_mode=2  # SIMD finite min, low-overhead safe path
```

The old boolean flag remains a compatibility alias:

```text
-searcher_safe_block_min=true  =>  -searcher_safe_block_min_mode=1
```

Mode 2 uses the same logical result as the scalar fallback:

1. Build valid-lane masks for the two 16-lane halves.
2. Use raw IEEE754 exponent bits to replace invalid or non-finite lanes with `FLT_MAX`.
3. Run pairwise min only after sanitization.
4. Use a manual horizontal min over finite values.

This avoids the store-and-scan scalar fallback while still preventing padded lanes from entering the block-min gate.

## 4. Recall Check

All rows use PCA-space `gist_sample100k`, IVF512, B=5, top100 GT, and `b5_rank1 = 128:10,256:6,320:4,256:2`.

| nprobe | default R@100 | b5_rank1 R@100 | delta | worst query | worst delta hits |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.759720 | 0.759740 | +0.000020 | 16 | -1 |
| 50 | 0.929000 | 0.929010 | +0.000010 | 38 | -2 |
| 100 | 0.983960 | 0.983820 | -0.000140 | 38 | -2 |
| 200 | 0.994780 | 0.994760 | -0.000020 | 38 | -2 |
| 400 | 0.995160 | 0.995130 | -0.000030 | 38 | -2 |

At nprobe 200, the two traced bad queries are recovered:

| query | default hits | b5_rank1 hits | delta hits |
|---:|---:|---:|---:|
| 500 | 100 | 100 | 0 |
| 580 | 100 | 100 | 0 |

These recall numbers match the earlier scalar safe fallback, which is the expected result if mode 2 is computing the same finite minimum more cheaply.

## 5. QPS Check

Single local run, 24 threads, nprobe 200, 10 internal rounds from `test_qps`.

| mode | plan | R@100 | QPS | avg ms/query | relative QPS vs native same plan |
|---|---|---:|---:|---:|---:|
| native | default | 0.993370 | 9090.3 | 2.640 | 1.00x |
| native | b5_rank1 | 0.994450 | 10396.1 | 2.309 | 1.00x |
| scalar safe | default | 0.994780 | 8436.5 | 2.845 | 0.93x |
| scalar safe | b5_rank1 | 0.994760 | 9724.8 | 2.468 | 0.94x |
| SIMD safe | default | 0.994780 | 9128.7 | 2.629 | 1.00x |
| SIMD safe | b5_rank1 | 0.994760 | 10379.4 | 2.312 | 1.00x |

Mode 2 keeps the scalar-safe recall recovery but removes almost all measured overhead in this run.

## 6. Artifacts

Root-cause diagnostic:

```bash
/rwproject/kdd-db/kluaq/saq/bin/block_min_diagnostic \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -seg_plan=128:10,256:6,320:4,256:2 \
  -blockdiag_query_ids=580,500 \
  -blockdiag_nprobe=200 \
  -blockdiag_cid=171 \
  -blockdiag_block=16 \
  -blockdiag_output=/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_block_min_diag_q580_q500_c171_b16.csv
```

SIMD-safe recall reports:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_safeblockminsimd_compare_np20_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_safeblockminsimd_compare_np50_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_safeblockminsimd_compare_np100_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_safeblockminsimd_compare_np200_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_safeblockminsimd_compare_np400_top100.csv
```

SIMD-safe QPS logs:

```text
/tmp/saq-run/results/saq/qps_gist_sample100k_ivf512_b5_caq_adj_seg_pca_th24_np200_sm4_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_sample100k_ivf512_b5_caq_adj_seg_plan128x10_256x6_320x4_256x2_pca_th24_np200_sm4_safeblockminsimd.csv
```

## 7. Interpretation

The previous `b5_rank1` q580/q500 losses were searcher implementation artifacts caused by unmasked padded lanes in partial blocks. Once block-min is made finite and lane-mask aware, default and `b5_rank1` remain nearly tied at B=5, and the severe per-query losses disappear.

For future planner experiments, `-searcher_safe_block_min_mode=2` is the cleaner evaluation setting. It separates plan quality from a native reduction artifact without the scalar fallback's measurable QPS cost.

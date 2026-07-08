# Native AVX512 block-min can be poisoned by padded lanes in partial search blocks

## Summary

The native multi-segment SAQ search path can silently skip valid candidates
when the last block of an IVF cluster is only partially full. The current
block-min reduction appears to include padded/invalid SIMD lanes before applying
a valid-lane mask. If one of those padded lanes contains `NaN`, the block-min
control value can become `NaN`, and the searcher skips vector-level refinement
for the whole block.

This is a search-time correctness issue, independent of the separate 1-bit
segment `create_index` crash.

## Affected Code Path

The relevant native reduction is in the multi-segment search path. In this
branch the code is:

```cpp
return _mm512_reduce_min_ps(_mm512_min_ps(dist[0], dist[1]));
```

This assumes that both 16-lane halves are fully valid. However, SAQ scans fixed
32-lane blocks, and the last block of a cluster may contain fewer than 32 real
vectors.

The block-min result controls this pruning gate:

```cpp
mi = blockMin(curr_dist512, curr_num_points, curr_dist);
if (mi <= distk) {
    // vector-level filtering and accurate refinement
}
```

If `mi` is `NaN`, `mi <= distk` evaluates to false, so the entire block is
skipped before accurate refinement.

## Reproduction / Diagnostic Case

I diagnosed this on GIST sample100k with PCA enabled, IVF512, `B=5`, top100 GT,
and a multi-segment custom plan:

```text
128:10,256:6,320:4,256:2
```

The observed bad cases were query IDs `580` and `500`. Both lost top-100 ground
truth vectors under the native path. The problematic block was:

```text
cluster id: 171
block index: 16
valid lanes: 12
probe rank: 0
```

Only lanes `0..11` were valid. Lanes `12..31` were padded/invalid.

The diagnostic command used in my branch was:

```bash
./bin/block_min_diagnostic \
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

## Observed Diagnostic Output

The valid input lanes were finite, but the pairwise `_mm512_min_ps(dist[0],
dist[1])` result contained non-finite values from invalid padded lanes. The
native reduction then returned `NaN`.

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

So the root cause is not that valid candidate distances became non-finite. The
native reduction compared valid low-half lanes with invalid padded high-half
lanes before masking by `valid_lanes`.

## Recall Impact

At `nprobe=200`, the native search path lost top-100 ground-truth neighbors for
queries 580 and 500. A finite/lane-aware block-min path recovered those cases:

| query | default hits | custom hits after finite/lane-aware block-min | delta hits |
|---:|---:|---:|---:|
| 500 | 100 | 100 | 0 |
| 580 | 100 | 100 | 0 |

Across the checked nprobe grid, the severe per-query regressions disappeared
once block-min was made finite and lane-mask aware.

## Expected Behavior

The block-min pruning gate should consider only real candidate lanes in the
current block. Padded lanes and non-finite lanes should not be able to poison
the pruning control value.

At minimum, a `NaN` block-min should not silently skip accurate refinement for
the whole block.

## Possible Fix Direction

A low-overhead fix is to make the block-min reduction lane-mask aware and
finite-only before the pairwise/horizontal min:

1. Build valid-lane masks for the two 16-lane halves.
2. Replace invalid or non-finite lanes with `FLT_MAX`.
3. Run pairwise SIMD min only after sanitization.
4. Compute a horizontal min over the sanitized values.

In my branch, the finite/lane-aware SIMD path produced the same logical result
as a scalar finite fallback while avoiding most of the scalar fallback overhead.

## Notes

- This is separate from the positive 1-bit segment crash in `create_index`.
- The issue affects search/evaluation correctness, not index construction.
- I have not submitted a pull request because I wanted to first confirm the
  intended behavior for partial SIMD blocks in the native search path.

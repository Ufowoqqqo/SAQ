# GIST Sample100k B=5 `b5_rank1` Pruning Trace

## 1. Purpose

This trace follows up on the searcher-level ablation in `docs/saq_gist_sample100k_B5_searcher_full_refine_ablation_2026_07_03.md`.

That ablation showed:

- `searcher_full_refine=true` does not recover the bad query 580/500 losses.
- `searcher_force_accurate_scan=true` does recover them.

So the remaining question was: where exactly are the lost GT vectors rejected before full-code refinement?

## 2. Tool

Added a diagnostic binary:

```text
src/search_pruning_trace.cpp
bin/search_pruning_trace
```

The tool replays the normal multi-segment `SAQSearcher::searchCluster` path for selected queries and target pids. It records, per target:

- IVF cluster, local index, block index, and probe rank;
- `distk` at the target block;
- variance-stage block min and target distance;
- fast-stage block min, scalar min, target distance, and non-finite lane count;
- whether the target enters vector-level filtering and accurate refinement;
- final trace rank and custom full/fast/vars ranks from `IVF::estimate`.

It is intentionally separate from the production searcher so normal search output is not polluted.

## 3. Command

Run from `/tmp/saq-run`, because the prepared sampled-GIST artifacts live under `/tmp/saq-run/data/gist_sample100k`:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
/rwproject/kdd-db/kluaq/saq/bin/search_pruning_trace \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -seg_plan=128:10,256:6,320:4,256:2 \
  -trace_topk=100 \
  -trace_query_ids=580,500 \
  -trace_nprobes=200 \
  -trace_output=/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_pruning_trace_q580_q500_np200.csv \
  -logtostderr=1
```

Output:

```text
/tmp/saq-run/reports/gist_sample100k_B5_b5_rank1_pruning_trace_q580_q500_np200.csv
```

## 4. Main Result

For both queries, every lost GT target is skipped at the same stage:

| query | lost GT count | lost GT stage | replacement FP count | replacement FP stage |
|---:|---:|---|---:|---|
| 580 | 8 | `fast_nonfinite_block_skipped` | 8 | `inserted` |
| 500 | 6 | `fast_nonfinite_block_skipped` | 6 | `inserted` |

All lost GT targets are in custom IVF cluster `171`, block `16`, probe rank `0`.

This means the lost GT vectors are not rejected by a normal threshold comparison like `mi > distk`. Instead, after the fast-stage segment loop, the block-level `mi` used by the searcher becomes `nan`. The production path then evaluates:

```cpp
if (mi <= distk) {
    // enter vector-level filter and accurate refinement
}
```

For `nan`, this condition is false, so the whole block is skipped before any vector-level or accurate-distance check.

## 5. Key Rows

For query 580, the lost GT targets include:

| pid | GT rank | custom full rank | custom fast rank | fast target | block distk | fast mi | scalar fast min |
|---:|---:|---:|---:|---:|---:|---|---:|
| 99498 | 22 | 22 | 9 | 0.111713 | 0.204303 | `nan` | 0.111713 |
| 99942 | 34 | 34 | 64 | 0.148289 | 0.204303 | `nan` | 0.111713 |
| 99496 | 44 | 44 | 61 | 0.147910 | 0.204303 | `nan` | 0.111713 |

For query 500:

| pid | GT rank | custom full rank | custom fast rank | fast target | block distk | fast mi | scalar fast min |
|---:|---:|---:|---:|---:|---:|---|---:|
| 99507 | 29 | 29 | 53 | 0.092761 | 0.118455 | `nan` | 0.092761 |
| 99501 | 37 | 37 | 62 | 0.094189 | 0.118455 | `nan` | 0.092761 |
| 99496 | 66 | 66 | 59 | 0.094060 | 0.118455 | `nan` | 0.092761 |

The important detail is that the scalar fast minimum is finite and below `distk`, and the target fast distances are also below `distk`. These blocks should have entered the vector-level filter and full-code refinement.

## 6. Non-Finite Lane Check

The tracer also stores the AVX512 fast-distance registers by raw `uint32_t` bit pattern and checks each valid lane directly. For the lost-GT block:

```text
fast_nonfinite_count = 0
fast_first_nonfinite_pos = -1
fast_first_nonfinite_pid = -1
```

So the trace did not find an actual NaN/Inf lane in the stored fast distances. The inconsistency is:

```text
fast_mi = nan
fast_scalar_min = finite
fast_nonfinite_count = 0
```

This points to the block-min reduction/control-flow value, not to a target vector whose fast distance is actually non-finite.

## 7. Interpretation

This explains the earlier ablations:

- Full-refine mode does not help because these lost GT vectors never enter refinement.
- Force-accurate scan helps because it bypasses the fast block-min gate entirely.
- Replacement FPs are inserted normally from earlier blocks, while the later lost-GT block is skipped even though full-code ranking would place those GT vectors inside top100.

The immediate hypothesis is a search-path robustness bug around the AVX512 block-min computation:

```cpp
mi = _mm512_reduce_min_ps(_mm512_min_ps(curr_dist512[0], curr_dist512[1]));
```

When `mi` becomes `nan`, the current code neither treats it as prune nor as pass; it silently skips accurate refinement because `mi <= distk` is false.

## 8. Next Step

The next controlled experiment should add a searcher ablation with a safe block-min path:

1. compute the same fast-stage vectors;
2. store the 32 lanes and compute scalar finite min, or use a NaN-safe SIMD reduction helper;
3. rerun default vs `b5_rank1` on GIST B=5;
4. compare recall and QPS against current search, full-refine, and force-accurate scan.

If this recovers query 580/500 without the huge force-accurate QPS loss, then part of the observed `b5_rank1` behavior is a searcher implementation issue rather than a segment-plan quality issue.


Follow-up status: this ablation is now completed in `docs/saq_gist_sample100k_B5_safe_block_min_ablation_2026_07_03.md`. Safe block-min recovers q580/q500 and makes default vs `b5_rank1` nearly tied under B=5.

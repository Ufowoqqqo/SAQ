# Phase 4 Complete Estimator-Work Evidence

## Research Question

Phase 3 found that `saq_prefix_acc1` gives better fixed-neighborhood ordering
than the source-aligned packed SymphonyQG estimator on GIST sample50k, but it
also reads more code bits. Phase 4 asks the narrower question:

> Does the first accurate SAQ segment remain a plausible graph-traversal
> building block after factors, padding, residual-cluster preparation, memory
> layout, and isolated estimator time are included?

This is a work gate, not an end-to-end graph experiment. No frontier policy,
heap, visited set, or path-dependent traversal is implemented here.

## Fixed Evaluation

```text
data/query coordinates: GIST sample50k PCA
SAQ index:              K=512, B=4
SAQ plan:               (64,11), (192,6), (320,4), (256,2), (128,0)
fixed adjacency subset: 4096 vectors
out-degree M:            32
queries Q:               100
exact-nearest roots:     8/query, 800 total
candidate estimates:     25,600 total, 256/query
trials:                  7
timed rounds/trial:      5 after 1 warm-up round
thread placement:        one process pinned to logical CPU 0
CPU:                     Intel Core i9-10920X, AVX-512
build:                   Release, -Ofast -march=native
SymphonyQG rotation:     fixed seed 0 for runtime
```

Adjacency construction, SymphonyQG edge encoding, graph-id-to-IVF-location
materialization, grouping, correctness checks, and file output happen outside
timed regions. Query preparation and the exact current-vertex distance required
by SymphonyQG are timed separately. Graph ids and SAQ locator bytes are counted
in logical work, but their dispatch time is not charged; this makes the SAQ
runtime comparison optimistic rather than pessimistic.

Reproduction command:

```bash
taskset -c 0 ./bin/benchmark_graph_estimators \
  -dataset=gist_sample50k -K=512 -B=4 -enable_PCA=true \
  -graph_bench_data_file=/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  -graph_bench_query_file=/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_query_pca.fvecs \
  -graph_bench_index_file=/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index \
  -graph_bench_output_prefix=results/saq/graph_phase4_estimator_work_gist4096_b4 \
  -graph_bench_subset=4096 -graph_bench_degree=32 \
  -graph_bench_max_queries=100 -graph_bench_roots_per_query=8 \
  -graph_bench_trials=7 -graph_bench_rounds=5 \
  -graph_bench_warmup_rounds=1 -graph_bench_symqg_rotation_seed=0
```

The preserved machine-readable outputs are:

- `docs/saq_graph_phase4_estimator_runtime_trials_2026_07_11.csv`;
- `docs/saq_graph_phase4_estimator_runtime_summary_2026_07_11.csv`;
- `docs/saq_graph_phase4_estimator_work_2026_07_11.csv`.

## Accounting Model

Let:

```text
d  = original dimension = 960
d' = SymphonyQG power-of-two padded dimension = 1024
M  = graph out-degree = FastScan block width = 32
S  = number of SAQ segments = 5
d+ = dimensions in positive-bit SAQ segments = 832
U_b = distinct SAQ (cluster, block) pairs in one expansion schedule
U_c = distinct residual-reference clusters in that schedule
```

### SymphonyQG

Each edge stores one `d'`-bit neighbor-relative code, three `float` factors,
and one 32-bit neighbor id. One query has a `4d'`-byte packed lookup table.
For one degree-`M` expansion,

```text
B_sym,cached = M * (d'/8 + 3*4 + 4) + 4d'
             = 32 * (128 + 12 + 4) + 4096
             = 8704 bytes/root = 272 bytes/candidate.
```

If the exact current distance is not already cached, SymphonyQG additionally
reads the current `d`-dimensional float vector:

```text
B_sym,cold = B_sym,cached + 4d
           = 12,544 bytes/root = 392 bytes/candidate.
```

### SAQ Fast Stage

The SAQ FastScan path reads one 1-bit code for every positive-bit dimension,
one norm factor per segment and lane, and the high-accuracy lookup tables:

```text
short code/block = M * d+/8 = 3328 bytes
factor/block     = M * S * 4 = 640 bytes
LUT/block        = 8 * d+ = 6656 bytes
total/block      = 10,624 bytes.
```

The stock single-candidate interface scans the containing 32-vector block for
each candidate. Grouping neighbors by `(residual cluster, block)` preserves
the scores and scans each distinct block once, but the measured trace still
contains `11,798` blocks for `25,600` candidates, or only `2.17` useful
candidates per scanned block.

Preparing one residual cluster reads the segmented query and centroid, at
least `2 * 4d = 7680` bytes, writes a `4d = 3840`-byte residual-query state,
and writes `8d = 7680` LUT bytes. The trace requires `22,434` preparations in
candidate order or `10,905` after within-expansion grouping.

### First Accurate Segment

`saq_prefix_acc1` replaces the first 64-dimensional segment's fast estimate
with its 11-bit estimate. Per candidate it additionally requests:

```text
long code:       64 * (11 - 1) / 8 = 80 bytes
rescale factor:  1 float = 4 bytes
query segment:   64 floats = 256 bytes
total:           340 logical bytes/candidate.
```

The source-level cache-line request estimate is 448 bytes/candidate for this
accurate step. It is reported separately from logical bytes and is not a
hardware-counter measurement.

## Trace Structure

```text
candidate-order cluster preparations: 22,434 = 28.04/root
grouped cluster preparations:         10,905 = 13.63/root
grouped unique blocks:                11,798 = 14.75/root
unique query-cluster states:           4,202 = 42.02/query
```

The main incompatibility is therefore structural. A graph expansion returns
neighbors distributed across many IVF residual clusters and FastScan blocks,
whereas SAQ's layout is designed for contiguous scans within one IVF cluster.

## Logical Input Results

Writes from residual-cluster preparation are kept in the CSV as separate
columns and are not folded into the input-byte column.

| estimator | schedule | input B/candidate | relative to cold SymphonyQG |
|---|---|---:|---:|
| `symqg_fht_fastscan` | cached exact-current distance | 272.00 | 0.69x |
| `symqg_fht_fastscan` | cold exact-current vector | 392.00 | 1.00x |
| `saq_fast` | candidate order | 17,366.20 | 44.30x |
| `saq_prefix_acc1` | candidate order | 17,706.20 | 45.17x |
| `saq_fast` | grouped blocks | 8,179.67 | 20.87x |
| `saq_prefix_acc1` | grouped blocks | 8,519.67 | 21.73x |
| `saq_fast` | grouped, cluster states supplied free | 4,908.17 | 12.52x |
| `saq_prefix_acc1` | grouped, cluster states supplied free | 5,248.17 | 13.39x |
| `saq_fast` | perfect full block, state supplied free | 332.00 | 0.85x |
| `saq_prefix_acc1` | perfect full block, state supplied free | 672.00 | 1.71x |

The final two rows are deliberately optimistic kernel bounds. They assume all
32 lanes are useful and one prepared cluster state is already available; they
do not represent the fixed graph trace.

Residual preparation also writes `86.15 MB` of residual-query state and
`172.29 MB` of LUT state in candidate order. Grouping reduces these to
`41.88 MB` and `83.75 MB`, respectively. Prebuilding every query-cluster state
would require `64.54 MB` across this 100-query matrix, or about `645 KB` for
one average query, before allocator and object overhead.

## Isolated Runtime

Median times are used below. The accounted fixed-trace estimator time amortizes
query preparation over 256 candidates/query. SymphonyQG also amortizes one
exact current-vector distance over 32 candidates/root:

```text
T_sym = 9.863 + 7848.910/256 + 210.285/32
      = 47.094 ns/candidate.

T_saq = T_candidate_kernel + 14942.852/256.
```

| estimator/schedule | kernel ns/candidate | accounted ns/candidate | vs accounted SymphonyQG |
|---|---:|---:|---:|
| SymphonyQG packed | 9.863 | 47.094 | 1.00x |
| SAQ fast, candidate order | 2,347.172 | 2,405.542 | 51.08x |
| SAQ prefix 1, candidate order | 2,413.414 | 2,471.785 | 52.49x |
| SAQ fast, grouped blocks | 1,156.106 | 1,214.477 | 25.79x |
| SAQ prefix 1, grouped blocks | 1,206.041 | 1,264.412 | 26.85x |
| SAQ fast, grouped and cluster states supplied free | 299.387 | lower bound only | 30.35x kernel ratio |
| SAQ prefix 1, grouped and cluster states supplied free | 374.125 | lower bound only | 37.93x kernel ratio |
| SAQ fast, perfect full block and state supplied free | 16.369 | lower bound only | 1.66x kernel ratio |
| SAQ prefix 1, perfect full block and state supplied free | 41.475 | lower bound only | 4.21x kernel ratio |

Constructing all `4,202` cached query-cluster estimators costs an amortized
`2,871 ns/candidate`; adding the cached prefix kernel gives
`3,245 ns/candidate`, so the cache is not a deployable optimization. The
free-cache rows remain useful because they show that cache construction is not
the only bottleneck.

## Quality Joined With Work

The quality values are the Phase 3 subset-4096 query means over ten fixed
SymphonyQG rotations. Lower rank, disagreement, and regret are better.

| estimator | mean exact-best rank | top-1 disagreement | exact regret | relevant complete time |
|---|---:|---:|---:|---:|
| SymphonyQG packed | 1.8606 | 0.3814 | 0.031495 | 47.09 ns/candidate |
| SAQ fast | 2.2575 | 0.4613 | 0.051584 | 2,405.54 ns/candidate |
| SAQ prefix 1 | 1.1725 | 0.1375 | 0.003735 | 2,471.78 ns/candidate |
| SAQ prefix 1 with grouped blocks | same scores | same scores | same scores | 1,264.41 ns/candidate |

`saq_fast` is worse in both ordering quality and query work. The first accurate
segment gives a real and statistically stable quality improvement, but under
the observed schedule it costs `52.5x` the accounted SymphonyQG estimator time
and `45.2x` the cold logical input. Grouping cuts the overhead but still costs
`26.8x` the complete time. Even the unattainable perfect-full-block prefix
kernel remains `4.2x` slower before query or cluster preparation.

This is not strict all-dimensional dominance because SAQ uses less compressed
index storage. It is evidence that the Phase 3 quality gain is not a
work-matched estimator improvement.

## Storage

SymphonyQG duplicates a 128-byte code and 12 factor bytes on every outgoing
edge. At degree 32, edge ids, codes, and factors require `4608 B/node`.

For this SAQ plan, the modeled per-vector payload is:

```text
short code                         104 B
long-code payload                  352 B
physical long-code stride          368 B  (16-byte segment alignment)
short factors                       40 B
long factors                        40 B
stored vector id                     4 B
SAQ payload                        556 B
graph ids                          128 B
id-to-(cluster, local) locator       8 B  (lower bound)
modeled total                      692 B/node.
```

The serialized SAQ IVF file is `34,201,289 B`, or `684.03 B/vector`, including
IVF/SAQ metadata, centroids, rotations, block padding, and ids. Adding graph
ids and the locator lower bound gives about `820.03 B/node`, `5.62x` smaller
than SymphonyQG's compressed edge structure.

The `4608 B/node` SymphonyQG figure excludes the original 960-dimensional
float vector needed for an uncached current distance. If both systems retain
the same `3840 B/node` raw-vector store for result reranking, their totals are
approximately `8448 B/node` and `4660 B/node`, a `1.81x` ratio. Both storage
conventions are reported to avoid attributing a shared reranking store to only
one method.

## Complexity

For one degree-`M` expansion:

```text
SymphonyQG packed: O(M d'/w), with one edge-contiguous batch.

SAQ candidate order:
  O(M * M_b * d+/w + C_switch * d),
  where M_b=32 is the FastScan block width and C_switch is the number of
  residual-cluster preparations.

SAQ grouped blocks:
  O(U_b * M_b * d+/w + U_c * d + M * d_acc),
  where d_acc=64 for prefix_acc1.
```

`w` denotes SIMD lane-level work rather than a scalar machine-word guarantee.
The relevant measured values are `U_b=11,798/800=14.75` and
`U_c=10,905/800=13.63` per root. The asymptotic notation alone hides the large
block-read and cluster-preparation constants, so runtime and byte counts are
the primary evidence.

## Decision

The Phase 4 work gate does not support proceeding to a full graph integration:

1. the source-aligned packed baseline is both more accurate and much cheaper
   than `saq_fast`;
2. `saq_prefix_acc1` improves local ordering only by paying substantially more
   query work;
3. implementable block grouping does not close the gap;
4. free cluster states and perfect block utilization still do not make the
   accurate prefix a faster estimator kernel;
5. obtaining the ideal block schedule would require a graph-specific layout
   or code duplication, overlapping the design space already occupied by
   graph-aware quantizers such as SymphonyQG.

Therefore the branch should stop before Phase 5. The defensible negative result
is narrower than “SAQ cannot work with graph indexes”:

> SAQ's current IVF residual-cluster and FastScan layout does not convert its
> first-prefix local-ordering advantage into a competitive random graph-edge
> estimator on this fixed GIST replay.

## Limitations

- The replay is GIST sample50k with one `B=4` SAQ plan and degree 32.
- Runtime uses one CPU and one fixed SymphonyQG seed; Phase 3 quality uses ten
  seeds.
- Logical and cache-line bytes are source-derived request models, not hardware
  performance-counter measurements.
- The perfect-block rows are optimistic kernel bounds on unrelated full SAQ
  blocks, not a realizable graph schedule.
- No end-to-end recall--QPS curve, graph dispatch time, or heap/visited-set time
  is reported because the Phase 4 stop condition is met before implementing a
  frontier traversal. The accounted estimator time must not be presented as an
  end-to-end graph result.
- A separately built scalar, graph-oriented SAQ layout could avoid FastScan
  block amplification, but that would be a different design and requires a
  new related-work and novelty gate rather than being treated as a rescue of
  the present hypothesis.

## Code Locations

- static accounting formulas:
  `saqlib/analysis/graph_estimator_work.hpp`;
- isolated benchmark and fixed trace:
  `src/benchmark_graph_estimators.cpp`;
- allocation-free packed SymphonyQG path:
  `saqlib/baseline/symphonyqg_fastscan.hpp`;
- segment-level SAQ FastScan entry point:
  `saqlib/quantization/saq_estimator.hpp`;
- regression coverage:
  `unit_test/ut_graph_estimator_work.cpp` and
  `unit_test/ut_symphonyqg_fastscan.cpp`.

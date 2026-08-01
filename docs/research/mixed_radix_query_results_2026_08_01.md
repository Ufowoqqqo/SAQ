# Original mixed-radix Recall/QPS result

Date: 2026-08-01

## Decision

The frozen fixed-adjacent, two-coordinate mixed-radix hypothesis is not
supported. Arbitrary integer radices did not produce a stable or material
Recall--QPS improvement over the otherwise identical power-of-two control,
and they did not establish a new deployable frontier against matched PQ/OPQ.

This closes the tested formulation. It does not prove that every possible
adaptive grouping or higher-dimensional mixed-radix representation must fail;
those would change the scientific question and are not results of this run.

## Frozen comparison

- `A128`: 64 adjacent scalar pairs over the first 128 PCA residual
  coordinates, arbitrary positive integer `(K1,K2)`, and
  `K1*K2 <= 2^B`.
- `D128_FULL`: identical fitting, grouping, packing, bytes, and complete-word
  query consumer, with both radices restricted to powers of two.
- Payloads: 32 or 64 bytes per vector.
- Workloads: SIFT1M and GIST1M, `nlist={1024,4096}`, the complete frozen
  nine-point nprobe schedules, Recall@100, one-thread latency, and 12-core
  batch QPS.
- Controls: matched PQ128 and OPQ128.
- Repetitions: one warmup and seven measured repetitions per mode and cell.

The design was frozen before inspecting A128 query outcomes in
`docs/research/mixed_radix_query_design_2026_07_30.md`.

## Completeness and correctness

- Registry: 32 cells.
- Accepted execution grid: 512 distinct PASS keys, with no duplicate key and
  no missing warmup, repetition, mode, arm, or cell.
- Output checks: exact nine-probe grids, stable candidate counts, output
  hashes, and Recall across warmups, single-thread runs, and batch runs.
- Latency checks: every single-thread TSV row has exactly one matching block
  of per-query float64 latency values.
- Correctness tests: B4/B8 packing, valid-label rejection, deterministic
  save/load, direct-distance/full-table parity, identical A/D consumer
  dispatch, and residual-IVFPQ precomputed-table behavior.
- Build and test: all eight CTest targets pass.
- The rebuilt native runner hash equals the recorded experiment binary hash:
  `ee74ef8178890bfad96f3131d96281b2c82112fa5be57ccb463053015256fcb7`.

One overlapped OPQ timing pass was detected through duplicate interleaved
rows, preserved under
`/tmp/mixed-radix-query/matrix-v1/recovery-backup-20260731/`, and marked
`INVALIDATED_OVERLAP`. Its CPU and wall cost remain counted, but it is not
measurement evidence. The exact frozen pass was rerun cleanly. No accepted
cell contains duplicate or partial rows.

## Mechanism result

At 32 bytes, every fitted A128 group selected `(K1,K2)=(4,4)`. A128 therefore
became exactly the D128_FULL representation: all four dataset/nlist cells had
identical rankings and zero Recall difference at all nine nprobe values.

At 64 bytes, only 10--24 of 64 groups differed from `(16,16)`, depending on
dataset and nlist. Almost all differences were `(15,17)` or `(17,15)`, using
255 of 256 paid-for states; one GIST cell also used a 252-state `(18,14)`
group. Thus the frozen scalar objective found only a narrow allocation change,
not a large amount of otherwise unreachable payload capacity.

Across all 64-byte cells and probes, the same-nprobe A-minus-D Recall@100
difference ranged from `-0.00106` to `+0.00054`:

| Dataset | nlist | Recall delta range | Positive / negative probes |
| --- | ---: | ---: | ---: |
| GIST1M | 1024 | -0.00096 to +0.00054 | 3 / 6 |
| GIST1M | 4096 | -0.00106 to +0.00017 | 2 / 7 |
| SIFT1M | 1024 | -0.000097 to +0.000066 | 4 / 5 |
| SIFT1M | 4096 | -0.000033 to +0.000436 | 8 / 1 |

The sign is not consistent across datasets, nlist values, or probes. The
largest positive change is 0.054 percentage points; the largest negative
change is 0.106 percentage points.

## Query performance and baselines

A and D used the same complete `2^B` table builder and scan loop. Their
same-probe batch-QPS ratio ranged from `0.9918` to `1.0069`, with group
medians near one. Their p95 latency ratio ranged from `0.9897` to `1.0251`.
These differences are comparable to the observed repetition dispersion and
do not provide a mechanism-specific speed claim.

Some A points are formally non-dominated in the discrete four-arm point set,
but this does not rescue the hypothesis: at 32 bytes A and D are the same
model, while at 64 bytes the A/D Recall differences are tiny and mixed-sign
and their consumer work is identical. PQ/OPQ generally reach higher Recall
and occupy the useful high-Recall portions of the frontier. A nonzero or
formally non-dominated point is not a material mixed-radix contribution.

Median relative QPS MAD is approximately 0.07%--0.28% by arm; the worst point
is 1.72%. No accepted Recall, output hash, or candidate count varied across
repetitions.

## Construction, storage, and resource cost

- Total accounted experiment cost, including the invalidated overlap:
  `32.357324648 CPU-hours` and `17.086804086 wall-hours`, below the frozen
  40/48-hour ceilings.
- Peak query RSS: `683,565,056` bytes.
- Peak build RSS across reported arms: `1,521,369,088` bytes, below 16 GiB.
- A construction CPU time was 148.4--150.7 seconds and wall time was
  148.7--151.1 seconds across its eight indexes.
- D construction CPU time was 165.5--228.3 seconds and wall time was
  160.9--166.7 seconds. The builders use different artifact paths, so this is
  resource accounting, not a construction-speed contribution.
- A's `(radix,used_states)` sidecar adds 128 bytes relative to D's radix-only
  sidecar. No per-vector payload or query-dependent metadata is added.

## Reproduction

The matrix command was:

```bash
python research/mixed_radix_query/run_natural_matrix.py \
  --runner /tmp/saq-mixed-radix-query-build/structured_2d_run_synthetic_timing \
  --admission-root /tmp/structured-2d-admission \
  --pool-root /tmp/structured-2d-admission/pool \
  --finalized /tmp/structured-2d-admission/finalized \
  --data-root /tmp/structured-2d-admission-data \
  --schedule-root /tmp/structured-2d-natural/schedule \
  --output /tmp/mixed-radix-query/matrix-v1 \
  --prior-cpu-hours 1.5 --prior-wall-hours 1.5 \
  --cap-cpu-hours 40 --cap-wall-hours 48
```

Final validation and summary:

```bash
python research/mixed_radix_query/summarize_matrix.py \
  /tmp/mixed-radix-query/matrix-v1 \
  /tmp/structured-2d-admission/finalized \
  /tmp/mixed-radix-query/matrix-v1/summary-v1
cmake --build /tmp/saq-mixed-radix-query-build -j 12
ctest --test-dir /tmp/saq-mixed-radix-query-build --output-on-failure
git diff --check
```

Primary generated outputs are:

- `/tmp/mixed-radix-query/matrix-v1/execution_ledger.tsv`;
- `/tmp/mixed-radix-query/matrix-v1/measurements/`;
- `/tmp/mixed-radix-query/matrix-v1/summary-v1/points.tsv`;
- `/tmp/mixed-radix-query/matrix-v1/summary-v1/a_vs_d_same_probe.tsv`;
- `/tmp/mixed-radix-query/matrix-v1/summary-v1/frontiers.tsv`; and
- `/tmp/mixed-radix-query/matrix-v1/summary-v1/summary.txt`.

The run context records base HEAD `d2565dc498f461dd0ac73277cb88cf8ed260f784`.
The native binary hash above exactly matches the final rebuild from this
worktree. The final acceptance commit is the source snapshot for the added
mixed-radix and recovery code.

## Claim boundary

Verified: the frozen fixed-pair arbitrary-radix representation does not
materially improve the Recall--QPS frontier over its dyadic control on this
matrix.

Not established: that reconstruction error determines Recall, that all
mixed-radix schemes fail, or that adaptive grouping, larger groups, a changed
allocator, or a different consumer would have the same result. Pursuing any
of those would be a new scientific question rather than continuation of this
frozen evaluation.

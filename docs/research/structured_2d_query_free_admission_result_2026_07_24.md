# Structured-2D query-free admission result

Date: 2026-07-24
Branch: `saq-structured-2d-modeling`
Design:
`docs/research/structured_2d_fair_query_evaluation_2026_07_24.md`

## Decision

The complete query-free synthetic admission is **admitted** under the final
user-authorized 256 aggregate CPU-hour, 120 wall-hour, and 16 GiB ceilings.

All required query-free pool, correctness, distribution, and synthetic timing
work completed without opening natural benchmark queries or ground truth. The
frozen projection is:

| Resource | Projected | Authorized | Decision |
| --- | ---: | ---: | --- |
| Aggregate CPU | 252.483 h | 256 h | ADMIT |
| Registered evaluation wall time, lower bound | 98.772 h | 120 h | ADMIT |
| Peak RSS | 3.64 GiB | 16 GiB | ADMIT |

The CPU gate passes with only 3.517 CPU-hours of headroom. Including the
tracked successful construction and final synthetic matrix gives a
103.839-hour wall lower bound, leaving about 16.161 hours for failed-attempt
charges, future index loading, orchestration, and result computation. The
bound official natural query and ground-truth objects may therefore be opened
for the frozen evaluation, with live enforcement of all three resource caps.

This is a resource-boundary result, not evidence for or against the Recall,
latency, QPS, or Pareto position of S.

## Data boundary

Only the bound learn/base objects and outputs created by this admission were
read:

- SIFT learn:
  `331bc82b6a0e89465776a3ba0c2113e0bd0cceaa014ec3ed639bc8b981af72ea`;
- SIFT base:
  `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`;
- GIST learn:
  `9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17`;
- GIST base:
  `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0`.

Natural query and ground-truth contents, old Recall/QPS results, and old
serialized indexes were not opened, hashed, parsed, sampled, or executed.

## Completed pool and context resolution

The shared state contains full-dimensional PCA, common
`nlist={1024,4096}` coarse quantizers, byte-identical database assignments,
real list sizes, and 64 deterministic finite synthetic vectors in original
and PCA coordinates for each dataset. GIST also has the frozen first-128
coordinate view while retaining full-dimensional routing.

The finalized pool contains 102 validated physical artifacts across the two
datasets and two coarse grids:

- S128, D128, and V128 at both code budgets;
- IVF-Flat;
- all forced regular full-dimensional PQ controls;
- all forced residual-OPQ controls;
- all forced PQ FastScan controls; and
- the finite regular/FastScan RaBitQ source pool.

SIFT PQ128/OPQ128 are byte-identical aliases of the corresponding full-128
artifacts. GIST has separate head-128 PQ/OPQ artifacts. D128's required
128-byte radix sidecar is included in complete serialized storage.

Production SAQ and CAQ are unavailable as contextual arms. At frozen source
revision `76fb83a`, `saqlib/index/ivf.hpp` has an outer `num_cen` loop around
an inner loop that already loads every cluster, so the required multi-cell
save/load prerequisite fails. The current file has SHA-256
`af4b005a3f077673acf2e9809965552d9997f17b391023167fbbb995507477f9`.
Production modification was forbidden, so no SAQ/CAQ timing point was
substituted.

The RaBitQ contextual slots were selected by actual complete bytes before
timing. SIFT has a low and high slot at both budgets; GIST has only the
available high `RABITQ_B1` slot at both budgets.

Finalized query-free artifacts are under:

```text
/tmp/structured-2d-admission/finalized/
  pool_manifest.tsv
  arm_aliases.tsv
  context_availability.tsv
  context_slots.tsv
  candidate_distributions.tsv
```

## Correctness findings before timing

Four implementation findings were corrected without changing the scientific
question, candidate policy, metric, or arm registry:

1. D128's radix sidecar was required for decoding but omitted from complete
   byte accounting. It is now required, size-checked, and charged.
2. S128's query path called full-index validation for every query, including
   rescanning and rehashing one million IDs. A loaded-index hot path now
   retains query/list checks but does not repeat load-time validation. The
   output hash remained identical while the `nprobe=1` SIFT smoke fell from
   about 3.8 to about 0.008 CPU seconds for 64 queries.
3. Batch and one-query PCA/coarse calls used different numerical execution
   shapes. At GIST `nlist=1024,nprobe=256`, a far-list boundary changed for
   one synthetic query. Both timing modes now use one canonical per-query
   transform and coarse-search semantics; batch mode parallelizes across
   queries.
4. The saved synthetic PCA vectors, ordered lists, coarse distances, and
   candidate distributions were regenerated from that canonical path before
   the final matrix.

These are artifact-correctness and measurement fixes, not research
contributions.

## Synthetic timing coverage

The final registry contains 94 logical dataset/`nlist`/budget/arm cells.
Byte-identical aliases and physical artifacts reused across budgets were
measured once, yielding 160 physical arm/mode processes. Each process covered
all nine frozen `nprobe` values with one warmup and three measured passes.

Coverage totals:

- 160/160 physical timing processes passed;
- 4,320 measured rows passed candidate and output-hash stability checks;
- 1,692 logical arm/`nprobe`/mode projection cells were produced;
- FastScan's frozen `implem=0` resolved to implementation 13 in all recorded
  rows; and
- maximum recorded process RSS was 3,907,956,736 bytes (3.64 GiB), below the
  16 GiB ceiling.

The timing and projection artifacts are:

```text
/tmp/structured-2d-admission/timing-final-v2/
  logical_registry.tsv
  execution_ledger.tsv
  measurements/*.tsv
  projection_cells.tsv
  projection_summary.tsv
```

The measurement host was Linux
`5.14.0-687.24.1.el9_8.x86_64` on one Intel Core i9-10920X socket with 12
physical cores, 24 hardware threads, one NUMA node, microcode `0x5003901`,
and 32 GiB installed memory. The CPU governor was `performance` and turbo was
enabled (`intel_pstate/no_turbo=0`). The Release build used GCC 11.5.0 with
the repository's `-O3 -fno-fast-math -ffp-contract=off -frounding-math
-mfpmath=sse` flags, libgomp 11.5.0, and OpenBLAS 0.3.29. Batch mode used 12
OpenMP threads; single mode used one.

The final matrix consumed 1.245 CPU-hours and 0.602 sequential wall-hours.
The frozen natural-evaluation
projection is 169.517 CPU-hours for SIFT and 33.571 for GIST. By mode it is
115.196 CPU-hours for batch12 and 87.893 for single-query latency. The largest
method-family totals are:

| Logical family | Projected CPU hours |
| --- | ---: |
| D128 | 45.719 |
| IVF-Flat | 19.974 |
| OPQFULL_M128X4 | 15.812 |
| OPQFULL_M64X8 | 12.961 |
| PQFULL_M128X4 | 11.991 |
| S128 | 11.655 |

These are registered CPU-work projections, not latency/QPS comparisons and
not quality evidence.

The successful common-state and pool resource rows contain 4.465 tracked
wall-hours. Adding those rows, the final synthetic matrix, and the registered
evaluation projection gives a tracked lower bound of 103.839 wall-hours.
Failed attempts, cost probes, compilation, loading during the future
evaluation, orchestration, and Recall computation are additional. A practical
unchanged-scope wall budget therefore needs margin above this lower bound,
not merely a change from 24 to 99 hours.

## CPU-accounting provenance

The original construction ledger was:

| Work | CPU seconds | CPU hours |
| --- | ---: | ---: |
| Shared SIFT/GIST PCA and coarse state | 2,351.249 | 0.653 |
| Native Faiss IVF/PQ/FastScan/RaBitQ and PQ128 | 33,828.780 | 9.397 |
| D128 and V128 | 3,465.987 | 0.963 |
| S128 | 18,854.523 | 5.237 |
| SIFT residual OPQ | 34,520.976 | 9.589 |
| GIST head-128 residual OPQ | 28,855.972 | 8.016 |
| GIST full-960 residual OPQ | 47,032.458 | 13.065 |
| Successful construction subtotal | 168,909.945 | 46.919 |
| Full-960 OPQ cost probes | 1,195.132 | 0.332 |
| First OPQ failed-build conservative charge | 3,000.000 | 0.833 |
| Original tracked total | 173,105.077 | 48.085 |

The first failed OPQ build completed the expensive work and failed only its
final load-type check, so it remains conservatively charged. The resumed
baseline was raised to 48.150 CPU-hours to cover intervening compile, smoke,
failed-parity, and repair checks before the separately measured final matrix.
This remains conservative accounting rather than an exact whole-task process
ledger. Under the later 256 CPU-hour authorization, the CPU projection passes
narrowly; the independent wall-time lower bound is the decisive blocker.

## Interpretation

The full frozen evaluation package fits just inside 256 aggregate CPU-hours
and the final 120-hour sequential wall boundary. The
registered wall projection is 98.772 hours: 88.072 hours for single-query
latency and 10.700 hours for batch12 throughput. SIFT accounts for 84.059
hours and GIST for 14.712 hours. These are lower bounds because they omit
index loading and non-timed orchestration.

The dominant work is the predeclared 10,000-query SIFT matrix repeated over
both modes, seven repetitions, all arms, both coarse grids, and all probe
points. This conclusion does not imply that S itself is especially expensive:
S128 contributes 11.655 of the 203.088 projected evaluation CPU-hours.

Performance status is query-free cost-profiled but
`PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`; there is no natural-query Recall,
latency, QPS, or SOTA comparison. The scientific hot path is per-list table
construction plus packed-code candidate scanning. Instrumentation,
serialization, and provenance work are outside the timed phases.

The official SIFT1M/GIST1M query and ground-truth objects were subsequently
bound and validated as recorded in
`docs/research/structured_2d_query_binding_2026_07_25.md`. The natural matrix
may execute without changing its scope or choices.

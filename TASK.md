# Completed Task: original mixed-radix Recall/QPS evaluation

## Branch and base

- Active branch: `saq-mixed-radix-query`
- Base: `d2565dc7` (`saq-structured-2d-modeling`)
- Status: completed and accepted on 2026-08-01
- Mode: `REVIEW`

## Research question

At exactly 32 or 64 packed bytes per vector, does the original fixed-adjacent
two-coordinate mixed-radix representation improve the real Recall@100--QPS
frontier over the same representation restricted to power-of-two radices,
and is either representation competitive with matched PQ/OPQ?

The hypothesis is deliberately about ranking, not reconstruction: allowing
non-power-of-two scalar cardinalities may allocate a fixed word more closely
to coordinate difficulty and may change nearest-neighbour ordering even when
mean reconstruction improvement is small.

## Frozen method and comparisons

- View: first 128 full-PCA residual coordinates, paired as
  `(0,1), (2,3), ..., (126,127)`.
- One global model per dataset, `nlist`, and byte budget, fitted without
  benchmark queries.
- `A128` candidate: arbitrary positive integer radices `(K1,K2)` with
  `K1*K2 <= 2^B`, selected by the existing scalar allocation objective.
- `D128_FULL` forced control: the same fitting, grouping, storage, and
  consumer, with both radices restricted to powers of two.
- Address: `label = z1 + K1*z2`; unused labels remain paid-for payload states
  and are never emitted.
- Consumer: a focused native IVFPQ scanner uses pinned Faiss distance-table
  construction and packed-code decoders to construct the complete `2^B`
  table once per selected IVF list and group, then perform one lookup per
  group and candidate. A and D execute this exact scanner; D's separable fast
  path is not admissible. Invalid addresses map to infinity and fail, while a
  direct-reconstruction calculation provides the correctness reference.
- Strong controls: matched `PQ128_M32X8`/`PQ128_M64X8` and
  `OPQ128_M32X8`/`OPQ128_M64X8` under the same public runner.

The inherited S/V/structured-2D outcomes are not method evidence for this
task and may not be used to tune A.

## Data, metrics, and fixed workload

- Standard SIFT1M and GIST1M learn/base/query/ground-truth objects already
  identity-bound by the inherited query evaluation.
- Shared full PCA, `nlist={1024,4096}`, base assignments, query assignments,
  IDs, and ordered preassigned lists from `/tmp/structured-2d-admission` and
  `/tmp/structured-2d-natural/schedule`.
- Probe schedules:
  - `nlist=1024`: `1,2,4,8,16,32,64,128,256`;
  - `nlist=4096`: `4,8,16,32,64,128,256,512,1024`.
- Full-dimensional L2, top 100, Recall@100.
- Complete end-to-end time includes query PCA, coarse assignment, all
  selected-list table construction, packed scan, and top-k.
- One-thread latency and 12-physical-core batch QPS, one warmup and seven
  measured repetitions, fixed affinity and thread settings inherited from
  `research/structured_2d/run_natural_matrix.py`.
- Primary comparison uses discrete measured operating points without
  interpolation. Report complete Recall--QPS curves and Pareto relations;
  do not rescue the method by changing a threshold after seeing results.

## Paths and permissions

Relevant source:

- `research/a4_or_b/models.{hpp,cpp}`: frozen scalar curves and allocation;
- `research/structured_2d/{build_dv_arms.cpp,synthetic_timing.cpp,
  run_synthetic_timing.cpp,run_natural_matrix.py}`: inherited public
  infrastructure;
- `research/mixed_radix_query/`: new focused builder, tests, and run helpers;
- `docs/research/mixed_radix_query_design_2026_07_30.md`.

Allowed reads:

- repository source, documents, and Git metadata;
- the identity-bound SIFT1M/GIST1M learn/base/query/ground-truth objects;
- the named common PCA/coarse/schedule artifacts;
- inherited PQ/OPQ index artifacts and frozen measurement summaries for
  context, after the A/D method choices above are recorded.

Allowed writes:

- `TASK.md`;
- focused code/tests under `research/mixed_radix_query/`;
- minimal integration changes under `research/structured_2d/`;
- focused notes under `docs/research/`;
- builds, A/D indexes, timing outputs, and logs under `/tmp`.

Forbidden:

- production `saqlib/` changes;
- query-trained radices, grouping, triggers, or thresholds;
- changing datasets, PCA, IVF candidates, probe schedules, metric, byte
  budgets, or baseline settings after observing A/D query outcomes;
- reading any unbound dataset or unrelated branch output;
- presenting reconstruction, pair proxies, consumer engineering, or a
  nonzero Recall change alone as a contribution.

## Commands and resource boundary

Allowed commands include repository inspection, CMake build/CTest, the focused
index builder and query runner, `taskset`, and result summarization. Generated
artifacts stay under `/tmp`.

Incremental target: at most 40 CPU-hours, 48 wall-hours, and 16 GiB peak RSS,
with one large index resident at a time. This is a stop ceiling, not a target
to consume. Run a tiny deterministic parity test and one representative
natural pass before launching the complete A/D matrix. If the frozen full
matrix is projected to exceed this ceiling, report the measured projection
instead of silently reducing the workload.

## Deliverables and done criteria

Deliver:

- deterministic mixed-radix packing, save/load, valid-label, direct-distance,
  and full-table parity tests;
- A128 and D128_FULL indexes for both datasets, both `nlist` values, and both
  byte budgets, with build time, bytes, and peak memory;
- actual Recall@100, single-thread latency, batch QPS, and dispersion over the
  complete frozen probe schedules;
- matched PQ/OPQ context and a clear frontier interpretation;
- exact commands, source revision, artifact paths, hardware/thread settings,
  limitations, and a decision-log entry.

Done means the A/D consumer is correct and identical except for radices, every
fixed A/D cell is measured without query-dependent tuning, results are stable
across repetitions, resource accounting is complete, and `git diff --check`
plus relevant tests pass.

Current blocker: none.

Outcome: the complete 512-pass matrix rejects a material or stable advantage
for the frozen fixed-adjacent mixed-radix formulation. At 32 bytes A is exactly
D; at 64 bytes its same-nprobe Recall delta is -0.00106 to +0.00054 with mixed
signs and essentially equal query work. See
`docs/research/mixed_radix_query_results_2026_08_01.md`.

There is no active experiment. The next action is a user-level research
decision: preserve this negative result and either stop mixed-radix work or
formulate a scientifically distinct question such as adaptive grouping or a
different allocation objective. Do not treat those alternatives as already
authorized by this completed task.

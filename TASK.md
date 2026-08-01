# Active Task: natural-data nearest-neighbour collision diagnostic

## Branch, base, and mode

- Active branch: `saq-mixed-radix-query`
- Base: `5611155c` (`Update mixed-radix meeting deck`)
- Mode: `IMPLEMENT` then `EXPERIMENT` and `REVIEW`
- Status: completed on 2026-08-01

## Research question and frozen hypothesis

Why did the frozen 64-byte arbitrary-radix arm A128 fail to improve Recall
materially over the identical power-of-two arm D128_FULL on SIFT1M/GIST1M?
Specifically, are D labels that A splits rare at the actual top-100 decision
boundary, or is there substantial collision-related Recall headroom that the
reconstruction allocator fails to realize?

The frozen working hypothesis is that collision witnesses are too sparse near
the true top-100 boundary to support a material `+0.002` Recall improvement.
The diagnostic must report the result unchanged if this is false.

This is an explanatory offline analysis of the completed fixed-adjacent
method. It does not authorize adaptive grouping, a new allocator, a new
consumer, parameter tuning, or another performance matrix.

## Frozen scope and definitions

Analyze exactly the four 64-byte cells:

- SIFT1M with `nlist=1024` and `4096`;
- GIST1M with `nlist=1024` and `4096`.

Use all nine previously frozen `nprobe` values for each `nlist`, the existing
query order, exact top-100 ground truth, saved ordered IVF lists, and existing
A128_B8/D128_B8 indexes. The 32-byte cells are a documented zero-effect
control because A and D are byte-equivalent there; do not rerun them.

For each query and probe:

1. rerun A and D through the existing complete-word consumer and verify their
   aggregate Recall against the accepted matrix;
2. define D false positives as returned IDs outside exact top-100;
3. define candidate-present D misses as exact top-100 IDs absent from D output
   but assigned to one of the selected IVF lists;
4. count an exact full-code witness when such a miss and false positive have
   identical complete D codes but different complete A codes;
5. count a changed-group witness when they share a D label in at least one
   group whose A/D shapes differ, but A assigns different labels in that
   group; and
6. report an explicitly optimistic collision ceiling that assumes every
   witnessed candidate-present miss can replace one D false positive, capped
   at Recall 1.0.

The changed-group ceiling is intentionally generous and is not a realizable
method. The exact-full-code statistic is the closest natural analogue of the
synthetic prototype collision. Candidate Recall is the independent ceiling
imposed by the frozen selected IVF lists.

The predeclared interpretation line is `+0.002` Recall over D:

- if even the optimistic changed-group ceiling adds less than `0.002` at all
  frozen points, collision scarcity closes this explanation;
- if it exceeds `0.002`, the current method remains negative but a distinct
  base-only collision-aware objective may merit investigation;
- query outcomes may diagnose headroom but may not train or select a method.

## Relevant paths and access

Relevant source:

- `research/mixed_radix_query/mixed_index.{hpp,cpp}`;
- `research/structured_2d/{synthetic_timing,dataset_io}.{hpp,cpp}`;
- `research/structured_2d/CMakeLists.txt`;
- focused new diagnostic code under `research/mixed_radix_query/`.

Allowed reads:

- repository source, Git metadata, completed mixed-radix result documents;
- `/tmp/structured-2d-admission/{sift,gist}/` PCA/coarse/base-assignment state;
- `/tmp/structured-2d-admission/pool/{sift,gist}/nlist_{1024,4096}/`
  A128_B8 and D128_B8 indexes and shape sidecars;
- `/tmp/structured-2d-natural/schedule/` frozen PCA queries and selected lists;
- `/tmp/structured-2d-admission-data/{sift,gist}/` frozen query and
  ground-truth files only;
- `/tmp/mixed-radix-query/matrix-v1/summary-v1/` accepted aggregate results
  for parity checking.

Forbidden reads are learn/base vector payloads, benchmark data outside the
named objects, unrelated branch outputs, and any new dataset. Index codes and
base assignments named above are allowed; raw base vectors are not needed and
must not be read.

Allowed writes are `TASK.md`, focused code/tests under
`research/mixed_radix_query/`, minimal CMake integration, a focused result and
decision-log update under `docs/research/`, and generated TSV/log output under
`/tmp/mixed-radix-query/collision-diagnostic-v1/`. Do not modify `saqlib/`.

## Commands and budget

Allowed commands are repository inspection, CMake build, CTest, the focused
diagnostic executable, deterministic rerun/comparison, result summarization,
and `git diff --check`.

Limits: 4 aggregate CPU-hours, 6 wall-hours, and 8 GiB peak RSS. Use one
process and one thread. This is diagnostic analysis, not performance evidence.

## Deliverables and done criteria

Deliver:

- a deterministic diagnostic with a tiny self-test;
- one cell/probe table containing actual A/D Recall, candidate ceiling, exact
  full-code collision ceiling, and changed-group collision ceiling;
- per-group witness attribution and A/D shape information;
- parity against the accepted A/D Recall values;
- exact commands, resource cost, output hashes, limitations, and a concise
  scientific interpretation;
- an update to `docs/research/DECISION_LOG.md`.

Done means all four cells and all frozen probes are covered, the tiny test and
repository tests pass, two diagnostic executions are byte-identical, no
budget is exceeded, and conclusions remain within the diagnostic claim.

Outcome: all 36 A/D Recall points reproduced exactly and two diagnostic runs
were byte-identical. There were zero exact full-code witnesses among
1,147,139 candidate-present D-miss events. The permissive changed-group
witness was instead abundant and crossed `+0.002` at 34/36 points, but it was
non-specific and did not predict the tiny, mixed-sign realized A-D Recall.
See
`docs/research/mixed_radix_natural_collision_diagnostic_2026_08_01.md`.

Current blocker: none. There is no active experiment. The next action is a
user-level decision between stopping mixed-radix work or posing a distinct
margin- or distance-direction-aware base-only question; neither is authorized
by this completed diagnostic.

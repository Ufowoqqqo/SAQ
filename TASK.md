# Current Task: query-free baseline-pool admission

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Base: `ce350f47aabb0f8ed972ec92ad78585571794291`
- Mode: `IMPLEMENT` and `EXPERIMENT`

## Research question and hypothesis

At exactly 32 or 64 packed code bytes per database vector, can the independent
shared-shape full-affine two-dimensional VQ representation (`S`) move the
Recall@100--latency/QPS frontier against the best matched PQ/OPQ control under
identical IVF candidates and complete end-to-end timing?

The hypothesis is that S's reusable non-Cartesian 2D shape improves distance
ordering enough to repay compact per-cell table construction. It fails if
full-dimensional PQ/OPQ has equal or better quality, real IVF lists are too
small to amortize tables, or any gain depends on weaker Recall, different
candidates, omitted work, or extra storage.

## Authoritative design

- `docs/research/structured_2d_fair_query_evaluation_2026_07_24.md`
- `docs/research/RESEARCH_CHARTER.md`
- `docs/saq_structured_2d_base_only_result_2026_07_23.md`
- `research/structured_2d/`
- `research/a4_or_b/`
- `third_party/faiss/` at
  `0ca9df4792b173d573044ee14ca0704780176e82`
- production SAQ/CAQ source at design base `76fb83a`

Historical A4 documents explain earlier evidence but do not authorize or
change this task.

## Frozen decisions

- confirmatory datasets: standard SIFT1M and GIST1M learn/base/query/GT splits;
- metric and output: full-dimensional L2, top 100, Recall@100;
- code budgets: exactly 32 and 64 packed bytes per database vector;
- coarse IVF: shared `nlist={1024,4096}` and identical preassigned lists;
- probe schedules:
  - 1024: `1,2,4,8,16,32,64,128,256`;
  - 4096: `4,8,16,32,64,128,256,512,1024`;
- S view: first 128 full-PCA residual coordinates, 64 adjacent pairs;
- GIST tail: reconstruct the unencoded residual tail as the coarse centroid
  and add its exact query-to-centroid tail norm once per selected list;
- every measured arm recomputes the identical common PCA/coarse search inside
  its end-to-end timer; saved preassignments are consistency references only;
- OPQ is trained and applied to residuals after the common coarse assignment
  and may not change probed lists;
- primary controls: D128, V128, PQ128, OPQ128, full-dimensional IVFPQ,
  IVFPQ FastScan, and OPQ-IVFPQ;
- quality/context controls: IVF-Flat and actual-byte SAQ/CAQ/RaBitQ points
  selected only from the finite source/config pools in the design;
- complete table construction, transform, coarse assignment, scan, and top-k
  work is included in end-to-end timing;
- single-thread latency and 12-physical-core batch QPS use one warmup and seven
  measured repetitions; and
- the materiality rule is the exact discrete-frontier rule in the design
  document, without interpolation or query-selected operating points.

## Reads and writes

Allowed reads now:

- repository source, Git metadata, build definitions, and research documents;
- official SIFT1M and GIST1M learn and base vectors;
- public source metadata needed to bind those two objects;
- newly built coarse assignments, PCA state, indexes, serialization records,
  and synthetic-query outputs from this task; and
- already documented base-only summaries and synthetic fixture outputs.

Allowed writes now:

- `TASK.md`;
- focused source and tests under `research/structured_2d/`; and
- focused result documentation under `docs/research/`; and
- downloaded learn/base objects, builds, indexes, and query-free outputs
  under `/tmp`.

Forbidden now:

- opening, hashing, parsing, sampling, or executing any natural benchmark
  query or ground-truth file;
- reading old Recall/QPS output or serialized indexes;
- running a query executable;
- modifying production `saqlib/` or the frozen fair-query design;
- reading held-out query quality, Recall, or ground-truth-derived metrics; and
- creating a new method, metric, baseline-selection rule, or authorization
  stage.

Filename discovery and source-level path inspection do not authorize file
content reads.

## Commands and budget

Allowed:

```bash
git status --short --branch
git diff
git diff --check
git log
rg ...
sed -n ...
find ... -type f
wc ...
curl -L ...                # only bound learn/base objects or source metadata
sha256sum <learn-or-base>
tar -xzf <archive> <learn-or-base-member>
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
```

This admission uses the user-revised evaluation ceiling authorized on
2026-07-24: 16 GiB peak RSS, 256 aggregate CPU-hours, and 24 hours wall time.
Only the CPU ceiling changed from the original design's 48 hours. One index
arm may be resident at a time. Natural query and ground-truth contents remain
unread.

## Deliverables and done criteria

Deliver:

- bound and shape/hash-validated SIFT1M/GIST1M learn/base objects;
- full-dimensional PCA plus shared `nlist={1024,4096}` coarse state and
  byte-identical database assignments;
- every forced S/D/V/PQ/OPQ/FastScan/IVF-Flat arm and the finite
  SAQ/CAQ/RaBitQ contextual pool, or an explicit source-level unavailability
  finding that precedes all synthetic timing;
- serialized bytes, method-owned bytes, build CPU/wall time, peak RSS,
  load parity, and selected contextual low/high slots;
- real list-size distributions for every frozen `nprobe`;
- 64 deterministic finite synthetic queries per dataset; and
- one warmup plus three measured passes in both one-thread latency and
  12-thread batch modes, followed by the frozen 1.25x/7-repeat CPU projection.

The synthetic vectors are fixed before any timing outcome: estimate each
coordinate's mean and population variance from the complete PCA-transformed
official learn split, draw 64 independent standard-normal coordinate vectors
with the repository's SplitMix64 seed words and an explicit Box--Muller
transform, form `mean + standard_deviation * z`, and reverse the trained
orthonormal PCA to the original space. Save both forms and reject any
non-finite value or PCA round-trip mismatch. These vectors are a cost probe,
not a quality sample, and cannot be used for Recall or method selection.

Done means:

- the complete predeclared pool has been built and serialized without
  outcome-dependent arm removal;
- every arm uses the same PCA, centroids, assignments, IDs, and ordered
  preassigned lists;
- all query-free correctness, save/load, byte-accounting, and deterministic
  output checks pass;
- the synthetic projection covers every required arm, dataset, `nlist`,
  budget, and `nprobe` in both timing modes;
- the projected total includes already consumed build CPU and is compared
  with the user-authorized 256 CPU-hour ceiling;
- `git diff --check` passes; and
- no query, ground truth, old QPS result, or serialized index was read.

## Current state and next action

The complete query-free pool, context availability, byte accounting,
candidate distributions, and synthetic timing matrix are finished. Production
SAQ/CAQ are unavailable because the frozen multi-cell save/load path fails;
the finite RaBitQ context is finalized. All 160 physical arm/mode processes
passed, covering 94 logical arm cells, every frozen `nprobe`, one warmup, and
three measured passes.

The conservative pre-matrix ledger is 48.150 CPU-hours and the final matrix
used 1.245 CPU-hours. Applying the frozen 1.25x/seven-repeat formula projects
another 203.088 CPU-hours, for 252.483 aggregate CPU-hours. The user raised
the CPU ceiling to 256 hours, so the CPU gate passes narrowly. The registered
evaluation wall-time lower bound is 98.772 hours, exceeding the unchanged
24-hour ceiling before loading and orchestration. The wall-time resource
boundary is therefore the active blocker. Including 4.465 tracked successful
construction wall-hours and 0.602 hours for the final synthetic matrix gives
a 103.839-hour tracked lower bound before failed attempts, probes, future
loads, orchestration, and Recall computation. Natural query and ground-truth
contents remain unread and unauthorized.

The authoritative result is
`docs/research/structured_2d_query_free_admission_result_2026_07_24.md`.
The one concrete next action is to preserve the completed evidence and obtain
a user decision to close the admission, raise the wall-time ceiling with
operational margin, or explicitly change the evaluation scope.

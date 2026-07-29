# Current Task: frozen structured-2D natural-query evaluation

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Base: `ce350f47aabb0f8ed972ec92ad78585571794291`
- Mode: `EXPERIMENT` with focused implementation/debugging

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
- the official SIFT1M and GIST1M query and ground-truth objects after their
  paths, byte sizes, shapes, and SHA-256 identities are recorded; and
- already documented base-only summaries and synthetic fixture outputs.

Allowed writes now:

- `TASK.md`;
- focused source and tests under `research/structured_2d/`; and
- focused result documentation under `docs/research/`; and
- downloaded learn/base objects, builds, indexes, and query-free outputs
  under `/tmp`; and
- frozen natural-query timing, ID, Recall, and frontier outputs under `/tmp`.

Forbidden now:

- opening any natural benchmark query or ground-truth object other than the
  bound official SIFT1M/GIST1M objects;
- reading old Recall/QPS output or serialized indexes;
- modifying production `saqlib/` or the frozen fair-query design;
- using query/ground-truth outcomes to tune an encoder, arm registry, coarse
  grid, probe schedule, threshold, metric, or claim; and
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

This evaluation uses the user-revised ceilings: 16 GiB peak RSS, 256
aggregate CPU-hours, and 120 hours wall time. The CPU ceiling was last raised
on 2026-07-24 and the wall ceiling on 2026-07-25. One index arm may be
resident at a time.

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
  12-thread batch modes, followed by the frozen 1.25x/7-repeat CPU projection;
- bound official query/ground-truth identities and shapes;
- all seven registered natural-query repetitions for every admitted logical
  arm cell, `nprobe`, and timing mode; and
- Recall@100, latency distributions, batch QPS, complete-byte joins, discrete
  frontiers, materiality decisions, and limitations under the frozen rules.

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
- the tracked and projected wall total remains within 120 hours;
- every fixed arm/operating-point output is stable across repetitions;
- the final analysis applies the frozen discrete-frontier rules without
  interpolation or outcome-dependent point removal;
- `git diff --check` passes; and
- no unbound query/ground truth, old QPS result, or old serialized index was
  read.

## Current state and next action

The frozen natural-query matrix is complete. All 94 logical arm cells,
188 warmups, 1,316 measured arm/mode passes, seven repetitions, and every
registered `nprobe` passed coverage and deterministic output checks. Aggregate
usage was 239.253 CPU-hours, 101.222 wall-hours, and 11.12 GiB peak RSS,
within the authorized limits.

The terminal result is **NO-GO**. Neither 32 nor 64 code bytes satisfies one
common speed or quality route on both SIFT1M and GIST1M at both coarse-index
sizes. GIST at `nlist=1024` and SIFT at `nlist=4096,64 B` contain local
positive points, but they do not meet the predeclared cross-dataset,
cross-index requirement. GIST at `nlist=4096` also fails complete-index byte
parity.

The authoritative final result is
`docs/research/structured_2d_natural_query_result_2026_07_29.md`. Raw outputs
remain under `/tmp/structured-2d-natural/matrix-v1/`; deterministic summaries
are generated by
`research/structured_2d/summarize_natural_matrix.py`.

The immutable matrix summary passed bounded independent review with no
remaining blocker, high, or medium finding. The one concrete next action is
to present the negative terminal result. Do not change the frozen rule or
start a successor mechanism as part of this task.

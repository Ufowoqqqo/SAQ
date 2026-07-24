# Current Task: query-free structured-2D full-index fixture

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Base: `da9c22bb3fa632045eb38ad3caf3f288c07dec28`
- Mode: `IMPLEMENT`

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
- already documented base-only summaries; and
- synthetic inputs created by the focused fixture.

Allowed writes now:

- `TASK.md`;
- focused source and tests under `research/structured_2d/`; and
- build and synthetic fixture outputs under `/tmp`.

Forbidden now:

- opening, hashing, parsing, sampling, or executing any natural benchmark
  query or ground-truth file;
- reading old Recall/QPS output or serialized indexes;
- running a query executable;
- modifying production `saqlib/` or the frozen fair-query design;
- building a natural-data index or running a natural-data experiment; and
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
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
```

This fixture task has a four-hour wall-time budget, two aggregate CPU-hours,
and 4 GiB peak RSS. It must use synthetic data only.

The future frozen evaluation has the separate resource ceiling written in the
design: 16 GiB peak RSS, 48 aggregate CPU-hours, and 24 hours wall time.

## Deliverables and done criteria

Deliver:

- a reusable prototype S full-index representation with compact packed codes,
  shared centroids, list offsets, database IDs, and no raw database vectors;
- one tiny deterministic fixture with at least three cells and a nonzero
  unencoded tail, exercised at both 32-byte B4 and 64-byte B8;
- fixed preassigned-list search whose optimized compact-table scores agree
  with direct binary64 reconstruction;
- deterministic top-100 ordering by `(distance,id)`;
- portable save/load parity and complete serialized-byte accounting; and
- focused build and test integration.

Done means:

- the fixture proves head-plus-tail score parity, preassigned-list order,
  candidate count, packed payload size, deterministic replay, save/load
  parity, and complete byte accounting for B4 and B8;
- the search representation contains no raw database vectors;
- all focused tests pass in Release mode;
- `git diff --check` passes; and
- no query, ground truth, old QPS result, or serialized index was read.

## Current blocker and next action

There is no blocker for this fixture. The reusable prototype container,
multi-cell preassigned search, binary serialization, and B4/B8 synthetic
fixture are implemented and pass the focused Release and AddressSanitizer
checks. This is correctness evidence only; the search wrapper still performs
prototype validation and full sorting and is
`PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`.

The next task, after this checkpoint, is to build the finite query-free
baseline pool and perform the frozen synthetic-query CPU-cost projection.
Query and ground-truth contents remain unread until every prerequisite in the
frozen design passes and the complete projected evaluation fits the 48
CPU-hour ceiling.

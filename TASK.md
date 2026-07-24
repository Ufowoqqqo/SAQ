# Current Task: freeze independent VQ fair query evaluation

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Base: `76fb83aa94d0bdee2e553199d2fd490286151b4f`
- Mode: `IDEATE` and `REVIEW`; documentation only

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
- primary papers and official implementation documentation; and
- already documented base-only summaries.

Allowed writes now:

- `TASK.md`;
- the fair-query design under `docs/research/`; and
- temporary text-only review output under `/tmp`.

Forbidden now:

- opening, hashing, parsing, sampling, or executing any natural benchmark
  query or ground-truth file;
- reading old Recall/QPS output or serialized indexes;
- running a query executable;
- modifying scientific or production source;
- building an index or running an experiment; and
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
```

This documentation task has a two-hour wall-time budget and no experimental
CPU budget. It must not start a long-running process.

The future frozen evaluation has the separate resource ceiling written in the
design: 16 GiB peak RSS, 48 aggregate CPU-hours, and 24 hours wall time.

## Deliverables and done criteria

Deliver:

- one readable evaluation design that completely specifies datasets,
  representation semantics, direct and SOTA controls, byte accounting,
  Recall alignment, candidate distributions, timing/QPS, resources, pass/fail
  interpretation, and query-access prerequisites; and
- this current-state task file.

Done means:

- no required metric, baseline, code budget, dataset, probe schedule, distance
  term, timing boundary, or decision threshold remains query-selectable;
- an independent bounded review finds no blocker or high-severity fairness
  defect;
- the diff contains documentation only;
- `git diff --check` passes; and
- no query, ground truth, old QPS result, or serialized index was read.

## Current blocker and next action

The evaluation is not executable yet. S has a 128-coordinate trainer and
packed microkernel, but no full-database IVF encoder, correct GIST tail score,
shared preassigned-list runner, serialized index, or end-to-end harness.
Standard SIFT1M/GIST1M objects are also not currently bound by path and hash.

After this design passes review, the next action is query-free: implement one
tiny synthetic multi-cell fixture that proves S's packed head-plus-tail score,
shared list schedule, deterministic top-100 behavior, save/load parity, and
complete byte accounting. Then build the finite baseline pool and perform the
frozen synthetic-query CPU-cost projection. Query and ground-truth contents
remain unread until those checks pass and the complete projected evaluation
fits the frozen 48 CPU-hour budget.

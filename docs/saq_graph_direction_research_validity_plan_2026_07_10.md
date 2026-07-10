# SAQ Graph Direction Research-Validity Plan

## Purpose

This document defines the ordered work needed before the graph-index direction
can support a research claim. It is an execution plan, not evidence that the
direction will succeed.

The plan follows three principles:

1. Correct the comparison before extending the method.
2. Stop the direction if a source-aligned baseline explains the current signal.
3. Measure traversal and system work directly before claiming a graph-search
   contribution.

All work remains on the `saq-graph-traversal-analysis` research branch. The
upstream SAQ branch remains unchanged. Confirmed correctness changes should be
kept in isolated commits so that they can be reviewed or migrated separately.

## Why This Plan Is Necessary

The current `symqg_vertex_proxy` preserves the current-vertex residual formula,
but omits several parts of SymphonyQG's estimator:

- random-sign Fast Hadamard rotation;
- power-of-two dimension padding, which changes GIST from 960 to 1024
  coordinates;
- the official packed FastScan arithmetic and layout;
- SymphonyQG's multiple-estimate graph-search behavior.

The current profiler also reports code bits rather than complete storage or
runtime work, and evaluates independent query-near local neighborhoods rather
than a beam-search traversal.

An independent review-time scalar reproduction added padding and random-sign
FHT without modifying the repository. On the existing subset-4096 setting, five
fixed rotation seeds produced the following range:

| estimator | top-1 disagreement | mean exact-best rank | p90 rank | top-8 containment |
|---|---:|---:|---:|---:|
| current unrotated proxy | 0.87625 | 8.2775 | 19 | 0.6150 |
| review-time FHT reproduction | 0.2475--0.2975 | 1.4425--1.5600 | 2--3 | 0.99625--1.0000 |
| current `saq_fast` | 0.46125 | 2.2575 | 5 | 0.98125 |

Phase 2 now contains parity-tested source-aligned scalar and packed FastScan
implementations. A small seed-0 sanity run gives identical scalar and packed
ordering and reproduces the same qualitative correction: the aligned baseline
is substantially stronger than the historical unrotated proxy. Multiple-
estimate traversal behavior remains absent, so the current graph result is
still provisional.

## Execution Overview

| phase | objective | status | dependency |
|---|---|---|---|
| 0 | contain unsupported claims and synchronize control documents | completed (2026-07-10) | none |
| 1 | make confirmed correctness behavior the default and test it | completed (2026-07-10) | phase 0 |
| 2 | implement a deterministic source-aligned SymphonyQG estimator | completed (2026-07-10) | phase 1 |
| 3 | rerun the local replay and apply the research stop gate | pending | phase 2 |
| 4 | replace nominal code-bit comparisons with complete work accounting | pending | phase 3 passes |
| 5 | implement a true fixed-graph frontier/traversal replay | pending | phases 3 and 4 pass |
| 6 | make preparation and evaluation reproducible from a clean checkout | pending | developed alongside phases 2--5 |
| 7 | update related work, synthesis, and meeting materials | pending | each evidence-changing phase |

Only one phase should be treated as active at a time. A phase is complete only
when its acceptance criteria are satisfied and its result is committed with the
command and evidence needed for review.

## Phase 0: Claim Containment and Document Synchronization

### Required work

- Mark all current `symqg_vertex_proxy` comparisons as provisional.
- Replace table labels such as `bits/candidate` with `code_bits_only` wherever
  only compressed code bits were counted.
- State explicitly that the current local replay does not test beam traversal or
  SymphonyQG's multiple-estimate mechanism.
- Update `TASK.md` so that it no longer asks for a profiler that already exists.
- Correct documentation drift, including:
  - `SaqDataWrapper::dynamic_programming` to
    `SaqDataMaker::dynamic_programming`;
  - candidate top-`r` refinement versus segment-prefix refinement;
  - `SaqCluEstimatorSingle` references where the implementation uses
    `SaqCluEstimator`.

### Acceptance criteria

- No current document states or implies that SAQ has been shown to outperform a
  source-aligned SymphonyQG estimator.
- `TASK.md`, the synthesis, and the slides identify the same active next step.
- Historical numbers remain available but are visibly separated from validated
  evidence.

## Phase 1: Correctness Defaults and Regression Tests

### Required work

- Make SIMD finite valid-lane block minimum mode the default search behavior.
- Keep the native reduction only as an explicitly selected legacy comparison.
- Define valid-lane non-finite behavior conservatively: report the invariant
  violation and do not allow the affected block to be pruned silently.
- Add a positive 1-bit segment regression test covering index construction,
  serialization, loading, fast estimation, and accurate estimation.
- Add partial-block tests for every valid-lane count from 1 through 31.
- Verify that scalar and SIMD finite minima agree on finite inputs, padded NaNs,
  padded infinities, and adversarial lane placements.
- Reject negative graph-profiler budgets before conversion to `size_t`.
- Check that result files open successfully before writing.

### Acceptance criteria

- Correct multi-segment search requires no additional CLI flag.
- The two confirmed upstream correctness failures have focused regression tests.
- The full build and focused tests pass in both Release and ASAN Debug builds.
- GIST B=3 with a positive 1-bit segment completes build/load/search smoke
  evaluation.

### Non-goal

Correctness fixes are evaluation prerequisites, not research contributions.

## Phase 2: Source-Aligned SymphonyQG Estimator

### Reference

Use the pinned SymphonyQG revision:

```text
6124ddb34ee4d176edea1bd7ad38d1672343df28
```

The relevant source files are:

```text
symqglib/utils/rotator.hpp
symqglib/utils/scalar_quantize.hpp
symqglib/quantization/rabitq.hpp
symqglib/qg/qg_query.hpp
symqglib/qg/qg_scanner.hpp
```

### Required implementation

1. Pad the original vector dimension to the next power of two.
2. Apply the same random-sign FHT construction to data, current vertex, and
   query.
3. Make the rotation seed explicit and serializable.
4. Perform the official 6-bit query scalar quantization in rotated padded space.
5. Compute residual signs and `triple_x`, `factor_dq`, and `factor_vq` in the
   same space and precision as the reference path.
6. Preserve the reference estimator's ordering semantics; do not introduce an
   extra non-negative clamp.
7. Implement a scalar reference first, then a packed/FastScan-equivalent path.

### Parity tests

For a small synthetic graph and fixed rotator matrix, compare the local
implementation with the official source for:

- rotated and padded query values;
- lower/upper query range, width, query codes, and query-code sum;
- residual sign code;
- all three stored factors;
- every estimated neighbor distance;
- final neighbor ordering, including deterministic tie handling.

### Acceptance criteria

- Scalar reference values match the official source within a documented
  floating-point tolerance.
- Packed/FastScan and scalar paths produce the same rank ordering on the parity
  cases.
- Output records padded dimension, rotation seed, source revision, and whether
  scalar or packed evaluation was used.

### Milestone status (2026-07-10)

The scalar implementation, official-source fixture, Release/ASAN parity tests,
and small real-data sanity run are recorded in
`docs/saq_symphonyqg_scalar_parity_2026_07_10.md`. The implementation matches
the pinned source for rotation, query state, edge code, factors, distances, and
ordering. The packed implementation, official-source fixture extension,
Release/ASAN parity tests, storage/work model, and real-data sanity run are
recorded in `docs/saq_symphonyqg_fastscan_parity_2026_07_10.md`. Packed and
scalar ordering match; all Phase 2 acceptance criteria are satisfied.

## Phase 3: Local-Replay Re-evaluation and Research Stop Gate

### Fixed evaluation settings

Retain the current settings for continuity before adding new datasets:

```text
dataset: GIST sample50k
SAQ index: K=512, B=4, PCA enabled
graph degree: 32
subsets: 1024 and 4096
queries: 50 and 100, respectively
roots per query: 8
```

Use a predeclared rotation replication schedule rather than selecting a favorable
seed. The default schedule is seeds `0..9`; this is an evaluation replication
budget, not a method hyperparameter. Report every seed and the aggregate.

### Required estimators

```text
exact_float
symqg_unrotated_proxy        historical diagnostic only
symqg_fht_scalar             source-aligned reference
symqg_fht_fastscan           source-aligned packed path
saq_fast
saq_prefix_acc1 ... saq_prefix_accS
saq_full
```

### Required statistics

- top-1 disagreement;
- exact-best mean and p50/p90/p99 rank;
- top-`L` containment;
- exact-distance regret of the selected neighbor;
- margin-conditioned rank statistics;
- per-query results and query-level 95% confidence intervals;
- variation across fixed rotation seeds.

Treat the query, not each root, as the independent statistical unit. Nested
roots may contribute to one query-level aggregate but must not inflate the
reported sample size.

### Continue condition

Continue the graph direction only if at least one SAQ progressive stage is
consistently non-dominated in rank quality versus complete logical work, across
the predeclared rotations, and the advantage is not explained by reading more
code or metadata.

### Stop condition

Stop using local rank recovery as the main graph-direction foundation if a
source-aligned SymphonyQG estimator matches or dominates `saq_fast`, and no SAQ
prefix point supplies a statistically stable Pareto improvement after complete
work accounting.

If the stop condition is met:

- record the result as negative evidence;
- explain that the earlier signal was caused by an incomplete baseline;
- do not implement a full graph integration to rescue the hypothesis;
- return to a new related-work-reviewed direction proposal.

## Phase 4: Complete Storage and Runtime Work Accounting

This phase runs only if Phase 3 passes its local evidence gate.

### Replace nominal bit counts

Report the following separately:

- compressed code bits;
- per-vector and per-edge factors;
- dimension padding;
- graph neighbor identifiers;
- cluster identifiers or local offsets;
- exact current-vertex reads;
- exact refinement or reranking reads;
- duplicated neighbor-side codes;
- total serialized index size.

### Query-work counters

- graph nodes visited;
- neighbor expansions;
- candidate distance estimates;
- SAQ cluster/estimator preparations;
- distinct residual-reference clusters touched;
- short-code, long-code, and factor bytes requested;
- cache-line-aware bytes touched where measurable;
- frontier insertions, duplicate entries, and heap operations;
- exact-distance evaluations;
- query preparation and rotation time.

### Runtime evaluation

- Isolate estimator microbenchmarks from end-to-end traversal.
- Use repeated runs, warm-up, pinned thread count, and reported hardware.
- Compare at matched recall and matched index-memory budgets.
- Report complete recall--QPS curves rather than one favorable operating point.

### Acceptance criteria

- Every accuracy point has a corresponding storage and query-work point.
- No paper-facing conclusion uses code bits as a substitute for bytes or time.
- Experimental validation cost is separated from deployable method cost.

## Phase 5: True Fixed-Graph Frontier and Traversal Replay

This phase runs only if Phases 3 and 4 show a plausible SAQ-specific advantage.

### Required search semantics

- one fixed graph and entry point shared by all estimators;
- the same beam size and termination rule;
- a real frontier heap and visited set;
- full path-dependent expansion rather than independent local events;
- SymphonyQG's multiple estimates for a vertex reached from different parents;
- exact current-vertex distance for implicit result refinement;
- SAQ staged refinement without learned query thresholds.

### Required outputs

- Recall@`k` and QPS/latency;
- visited nodes and expanded edges;
- visited-set and path divergence from exact traversal;
- rank of the exact next frontier node;
- number of candidates and segments refined;
- duplicate frontier entries for multiple-estimate methods;
- complete bytes, factor reads, heap work, and exact reads;
- final index size.

### Refinement analysis

First report full diagnostic curves over candidate and segment refinement. Do
not select a deployment threshold from benchmark-query recall. A later fixed
rule must be derived from stored SAQ quantities and must have a mechanism-level
rationale.

### Acceptance criteria

- A local estimator difference translates into a statistically stable
  end-to-end recall/work improvement.
- The improvement survives matched graph, memory, and search parameters.
- The policy remains query-unaware and introduces no arbitrary fitted threshold.

## Phase 6: Clean-Checkout Reproducibility

Reproducibility work should be added alongside the experiment that first needs
it rather than deferred to the end.

### Required artifacts

- one command to prepare GIST sample/PCA/IVF artifacts from the documented raw
  dataset;
- fixed PCA, IVF, graph, and rotation seeds;
- pinned SAQ and SymphonyQG revisions;
- dependency versions and compiler flags;
- a machine-readable run configuration beside each result;
- small committed aggregate CSV/JSON results;
- commands to verify input dimensions and hashes;
- no committed raw datasets, large indexes, binaries, or event-level logs.

### Acceptance criteria

A clean checkout with access to the documented raw dataset can regenerate the
paper-facing aggregate table with one preparation command and one evaluation
command.

## Phase 7: Related Work and Research Communication

### Related-work update

Before proposing a graph method, review at least:

- SymphonyQG and NGT-QG;
- Routing-Guided Learned Product Quantization;
- QuIVer;
- Link and Code;
- other compressed-graph or progressive-refinement methods found in the updated
  primary-source survey.

For each work, record what it already solves, its estimator and graph semantics,
its storage model, and the remaining SAQ-specific gap.

### Document update policy

- Update `TASK.md` immediately when a phase changes status.
- Keep one canonical aggregate result file for each table.
- Generate or verify Markdown and Beamer tables from the same source.
- Compile the Beamer deck and check overfull frames before meeting use.
- Separate confirmed evidence, provisional evidence, and proposed methods.
- Preserve negative results when they determine a research pivot.

## Planned Commit Sequence

Use small commits in this order:

1. `Clarify provisional graph evidence and execution plan` (completed
   2026-07-10)
2. `Make finite block minima the tested default` (completed 2026-07-10)
3. `Add one-bit and partial-block regression coverage` (completed 2026-07-10)
4. `Add source-aligned SymphonyQG scalar estimator` (completed 2026-07-10)
5. `Validate SymphonyQG estimator parity` (completed 2026-07-10)
6. `Record aligned local-replay decision`
7. `Add complete graph-estimator work accounting` only if Phase 3 passes
8. `Add fixed-graph frontier replay` only if Phases 3 and 4 pass
9. `Update graph related work and meeting synthesis`

Each evidence commit must include the exact command, fixed configuration,
aggregate output, interpretation, and explicit continue/stop decision.

## Actions Explicitly Deferred

Until the Phase 3 gate passes, do not:

- implement full HNSW or DiskANN integration;
- add a learned or query-calibrated refinement policy;
- broaden the benchmark matrix merely to search for a positive dataset;
- optimize profiler runtime before estimator semantics are correct;
- add new SAQ candidate-plan families;
- describe the current proxy result as a research contribution.

The immediate executable work is Phase 3: run the predeclared fixed-seed local
replay, aggregate at the query level, compare rank quality against complete
logical work, and apply the documented stop gate before any method design or
full graph integration.

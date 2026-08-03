# Active Task: closest-baseline pairing discrimination

## State and research question

- Branch: `saq-mixed-radix-query`
- Base snapshot: `552fa7b`
- Mode: `IMPLEMENT`, `EXPERIMENT`, then `REVIEW`

Test whether the completed empirical-SSE minimum-weight perfect matching
(`D-MWM`, previously `D_FLEX`) improves the identical dyadic scalar-product
consumer beyond established permutation-only grouping controls.  This is a
pairing-objective test, not a mixed-radix test.

Hypothesis: `D-MWM` should beat OPQ's parametric Eigenvalue Allocation pairing
(`D-EA`) and predeclared random pairings on both natural datasets.  Otherwise
the positive pilot is adequately explained by known optimized decomposition.

## Frozen methods and inputs

- SIFT1M and GIST1M;
- `nlist=4096`, 64-byte/B8 codes;
- `nprobe={64,1024}`;
- batch12, one warmup and three measured repetitions;
- identical PCA residuals, first 8,192 SHA-ordered fitting rows, IVF
  assignments, query order, selected lists, top-100 ground truth, scalar curve
  fitter, dyadic allocator, complete-table consumer, and four-candidate scan.

Arms:

- `D_MWM`: accepted `D_flex` pairs from the byte-identical offline result;
- `D_EA`: Ge et al.'s parametric OPQ Eigenvalue Allocation, specialized to 64
  buckets of capacity two, using the fitted residual-coordinate variances;
- `D_RANDOM_0..2`: Fisher--Yates permutations using fixed 64-bit seeds
  `2026080301`, `2026080302`, and `2026080303`, paired consecutively;
- `D_ADJ`: `(0,1),(2,3),...,(126,127)` anchor.

All arms use dyadic allocation after pairing.  Do not build or evaluate an
arbitrary-radix arm.  Do not select random seeds, probes, thresholds, or
pairings from query outcomes.

For Eigenvalue Allocation, use the OPQ primary-text rule: sort coordinate
variances descending, then assign each coordinate to the non-full bucket with
the smallest current product.  Empty buckets must be filled before any bucket
receives its second coordinate; ties are resolved by bucket index.  Record the
resulting pairing and fitted SSE.

## Reads, writes, and commands

Allowed reads are current repository source/results, the accepted pair table
under `/tmp/mixed-radix-query/matched-offline-v1/run7/pairs.tsv`, and the same
SIFT1M/GIST1M admission/query/ground-truth artifacts used by the completed
pilot.  Do not read another dataset or previously unexamined query outcome.

Allowed writes are focused source/tests under
`research/mixed_radix_matching/` and minimal arm/mode integration in
`research/structured_2d/`, plus `TASK.md`, the decision log, and one focused
result note.  Generated indexes and results belong only under
`/tmp/mixed-radix-query/closest-baseline-v1/`.

Allowed commands are the existing CMake build, focused unit tests, the focused
baseline builder, and the natural query runner restricted to the frozen cells.
No production `saqlib/` change, dependency change, full matrix, parameter
sweep, or query-trained choice is allowed.

## Resources and correctness

Budget: 4 aggregate CPU-hours, 4 wall-hours, 16 GiB peak RSS, one build
process, and at most 12 query threads.  Stop before exceeding a limit.

Tests must verify the primary-text Eigenvalue Allocation order and tie rules,
valid perfect pairings, fixed random reproducibility and seed separation,
matched-sidecar round-trip, valid labels, direct/table distance parity, and
stable query output hashes.  Reuse existing index/consumer tests where they
already cover the latter properties.

The scientific hot path remains table construction plus the unchanged B8
candidate scan.  Pair generation, logging, and serialization remain outside
timed query regions.

## Decision and completion state

This is an early falsification gate, not a SOTA comparison.  Report all arms
and both datasets unchanged.  Treat `D_MWM` as differentiated only if it beats
`D_EA` on both datasets with a consistent positive Recall trend and reaches at
least `+0.002` Recall@100 at one of the two frozen probes on each dataset,
without more than 5% QPS regression.  Random and adjacent controls provide
attribution but cannot substitute for beating `D_EA`.

Done means all focused tests pass; every arm builds with valid sidecars/codes;
all 72 arm/dataset/probe/repetition measurement rows are stable; construction,
bytes, memory, commands, hashes, Recall/QPS, and limitations are recorded; and
the result says whether to proceed to DP-OPQ/full evaluation or close MWM as a
standalone direction.

Status: complete, with no blocker.  All 72 rows are present and stable, tests
pass, and the resource limits were respected.  `D_MWM` misses the gate: its
Recall delta over `D_EA` is below `+0.002` everywhere and changes sign on
GIST1M.  The standalone MWM pairing direction is closed; do not proceed to
DP-OPQ or a full matrix from this result.

Result: `docs/research/nonadjacent_pairing_closest_baseline_result_2026_08_03.md`.
The meeting summary now includes this negative discrimination result.  One
concrete next action is to select a scientifically different question before
authorizing any further implementation or experiment.

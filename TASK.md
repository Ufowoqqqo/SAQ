# Current Task: correlated-pair resource-allocation diagnostic

## Branch and base

- Active branch: `saq-correlated-pair-allocation`
- Base: `d305578` (`saq-mixed-radix-query`)
- The mixed-radix result at the base remains closed evidence. This task tests a
  different independent variable and does not reopen within-pair radix tuning.

## Research question

Do base vectors contain stable pairs of strongly associated dimensions, and
do the resulting two-dimensional blocks have sufficiently different marginal
rate--distortion curves to justify allocating a fixed total bit budget across
dimension pairs rather than fixing the same budget for every pair?

The allocation unit is a two-dimensional block such as `(D1,D2)`. The first
diagnostic must not optimize the split between `D1` and `D2` using arbitrary
mixed radices and present that as the tested mechanism.

## Falsifiable hypothesis and decision

On disjoint deterministic base-only folds:

1. correlation-selected pairs retain the sign and substantial magnitude of
   their fitted association on the held-out fold; and
2. under the same total bit budget, fit-fold allocation across those pairs
   lowers held-out reconstruction error relative to eight bits per pair by a
   material amount, rather than merely moving bits among unstable pairs.

For this first diagnostic, `5%` held-out reconstruction reduction in both
cross-fit directions is the materiality screen. Failure is evidence against
this simple correlation-driven allocation mechanism, not against every
block-quantization or estimator-aware method. Passing permits a later
closest-primary-work and exact-consumer design; it is not Recall or systems
performance evidence.

## Inputs and relevant paths

Allowed base inputs:

- `/rwproject/kdd-db/kluaq/dataset/sift10m/sift10m_base.fvecs`, restricted to
  its first 1,000,000 rows and first 128 dimensions;
- `/rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs`, restricted initially
  to its first 128 dimensions so the two datasets have the same 64-pair,
  512-bit diagnostic boundary.

Relevant reusable source and evidence:

- `research/mixed_radix_matching/` for deterministic matching utilities and
  earlier pair controls;
- `research/a4_or_c/core.*` for scalar allocation semantics when useful;
- `research/structured_2d/dataset_io.*` for fvecs validation when useful;
- `docs/research/nonadjacent_pairing_closest_baseline_result_2026_08_03.md`;
- `docs/research/mixed_radix_max_weight_matching_offline_2026_08_01.md`;
- `docs/research/RESEARCH_CHARTER.md`.

## Read/write boundary

Allowed reads are repository source/documents, the two base files above, and
generated outputs from this task. Allowed writes are focused source/tests and
current research notes in this branch, build products and measurements under
`/tmp`, and this current-state `TASK.md`.

Forbidden reads include every query file, ground-truth file, prior Recall/QPS
artifact for outcome selection, and dimensions 128--959 of GIST in this first
matched-boundary diagnostic. Do not modify production SAQ code, build an ANN
index, or create a query consumer in this task.

## Frozen first diagnostic

- Deterministically sample 16,384 rows from the permitted first 1,000,000 base
  rows of each dataset and split them into two 8,192-row folds.
- Measure train/held-out Pearson association and compare correlation-selected,
  adjacent, and OPQ-P-style variance-balanced pairings.
- For each two-dimensional block, derive a fit-fold local PCA basis and a
  reconstruction curve for integer group budgets from 6 through 10 bits.
- Compare uniform eight bits per pair with a deterministic dynamic program
  that assigns exactly 512 total bits across the 64 blocks. Evaluate every
  fitted choice unchanged on the opposite fold and run both fold directions.
- Record pair stability, budget histograms, fit and held-out reconstruction,
  commands, seeds, runtime, peak memory, and limitations. Label the result
  `BASE_ONLY_RECONSTRUCTION_DIAGNOSTIC`, not query-performance evidence.

## Commands and resource budget

Allowed commands are focused Python syntax/unit tests, CMake builds or C++
tests needed by reused code, the diagnostic runner over the two allowed base
files, and standard read-only inspection commands.

- Total ceiling: 2 CPU-hours and 2 wall-hours.
- Peak RSS ceiling: 16 GiB.
- Generated outputs must stay under `/tmp/correlated-pair-allocation/`.
- BLAS thread count must be recorded; provenance and output writing remain
  outside any reported scientific timing region.

## Deliverables and done criteria

Deliver:

- a focused, tested diagnostic runner;
- one reproducible result directory under `/tmp`;
- a concise research note stating evidence, decision, costs, and claim limits.

Status: completed. Both datasets and both fold directions finished within
budget, focused tests passed, a repeated run produced byte-identical scientific
tables, and every allocation totals exactly 512 bits. The correlation-selected
allocation gains were 3.110%/4.139% on SIFT and 1.487%/1.541% on GIST-head128,
so the frozen 5% rule gives `CORRELATION_DRIVEN_ALLOCATION_SCREEN_FAIL`.

The result note is
`docs/research/correlated_pair_allocation_base_diagnostic_2026_09_02.md`.
Accepted generated evidence is under
`/tmp/correlated-pair-allocation/base-v3/`; its deterministic repetition is
under `base-v4/`.

There is no blocker for this completed raw-base diagnostic. The old derived
SAQ residual panel under `/tmp` has expired, so a residual-space continuation
would first need to recreate only the necessary base-derived input. This task
does not authorize that continuation and does not claim residual-space or
query evidence.

## Concrete next action

Review the completed result with the user. If the direction continues, the
smallest new question is why fixed adjacent GIST blocks pass the allocation
screen while strongest-correlation blocks do not, measured in the actual SAQ
residual space before any index or query consumer is implemented.

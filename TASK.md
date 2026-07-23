# Current Task: A4-OR-B base-data feasibility

## Branch and base

- Active branch: `saq-a4-original-reopening-protocol`
- Base commit: `383ffccb16e38cb324b5c037360acaa78d02e1d8`
- Prerequisite: revised `PASS_A4_OR_C_SYNTHETIC_ONLY`
- Active mode: `IMPLEMENT` then `EXPERIMENT`

The user has authorized continuing the current Attempt 4 through dataset
experiments. This activates the existing A4-OR-B base-only question; it does
not authorize changing its scientific question or using benchmark queries to
tune the encoder.

## Research question and hypothesis

On the frozen GIST and CIFAR residual panels at 32- and 64-byte payloads, test
whether arbitrary-cardinality mixed-radix factorization:

- removes more than 5% of dyadic reconstruction error;
- closes more than half of the opportunity exposed by same-capacity 2D block
  VQ;
- improves the base-pair distance-estimator proxy by more than 5%;
- remains within 1% of independently trained ordinary PQ; and
- has a material fitting-time or model-byte advantage without a twofold
  regression in the other metric.

This is a query-unaware, base-only feasibility gate. It is not Recall, QPS, or
unchanged-SAQ compatibility evidence.

## Frozen inputs and inventory

Datasets and shapes:

- `gist_sample50k_k512`: 50,000 by 960, 512 IVF cells;
- `cifar60k_k512`: 60,000 by 512, 512 IVF cells.

For each dataset use exactly 8,192 fitting and 8,192 held-out base residuals,
the inherited cluster-stratified SHA-256 selection rule, 64 fixed adjacent
coordinate pairs, and B4/B8. Pair consecutive held-out rows within each cell
without reuse.

Residuals are one binary32 subtraction:

```text
residual[j] = float32(base_pca[j] - centroid_pca[cell_id,j])
```

The exact selection rule, coordinate lists, shapes, sizes, and input hashes
are preserved at Git commit `3aa2f6e` in:

- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`;
- `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`.

The current A4-OR-B decision rule is Section 9--11 of
`docs/saq_attempt4_original_reopening_protocol_2026_07_22.md`.

## Allowed reads

Read only:

- the six content-identified PCA-base, PCA-centroid, and cluster-id files;
- source, build configuration, pinned Faiss, and Git metadata needed for this
  implementation;
- the frozen input/preregistration documents named above; and
- newly generated A4-OR-B outputs from this worktree.

Current located GIST root:

`/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/`

The frozen CIFAR PCA artifacts are not currently located. The raw CIFAR base
is not a substitute unless the exact frozen PCA/IVF artifacts can be
reproduced and match their registered hashes.

## Forbidden reads and changes

Do not read benchmark queries, ground truth, Recall/QPS results, serialized
indexes, variance files, PCA matrices, prior A4 outcomes, or outputs from other
branches. Do not use held-out base rows for fitting or model selection.

Do not change datasets, groups, rates, sample sizes, seeds, histogram sizes,
thresholds, controls, or the query-unaware boundary after observing results.
Do not modify SAQ/CAQ production search code during A4-OR-B.

## Implementation plan and budget

Smallest falsifiable question: can the inherited GIST inventory be constructed
exactly as registered before any model is fitted? Only after that preflight
passes is the cheapest scientific check a GIST B4/B8 native smoke using the
complete frozen fit and held-out inventory.

Expected files:

- `research/a4_or_b/`: native reader, trainer, encoder, scorer, and CLI,
  approximately 500--1,000 scientific lines;
- `script/a4_or_b_inventory.py`: deterministic selection only, under 250
  support lines;
- `script/a4_or_b_statistics.py`: frozen bootstrap/Holm analysis only, under
  350 support lines.

Use existing `research/a4_or_c` scalar DP and pinned Faiss rather than copying
or importing old A4 runners. Keep generated inventories, builds, models, and
large contributions under `/tmp`.

Resource boundary:

- one process and one thread for registered measurements;
- 16 GiB peak RSS;
- JSON/logging/hashing outside timed scientific regions;
- fail rather than silently reducing rows, groups, starts, iterations, or
  controls.

## Deliverables and done criteria

Deliver:

- exact input identity and inventory hashes;
- D/A/P/V held-out reconstruction and base-pair contributions for both
  datasets and both rates;
- 20 frozen bootstrap contrasts with Holm correction;
- group prevalence and leave-one-group-out checks;
- fitting, encoding, table, model-byte, transient-memory, and lookup ledger;
- a truthful `PASS_A4_OR_B_BASE_ONLY` or `NO_GO_BASE_ONLY` interpretation.

A4-OR-B is done only after both datasets run successfully and all required
rows are present. A pass permits implementing the query-free native scan
microbenchmark. Benchmark-query evaluation begins only after encoder,
representation, and operating points are frozen.

## Current blocker and next action

The registered GIST files are available and their hashes match, but the
inherited inventory rule is infeasible before model fitting: all 512 cells are
occupied, yet 168 cells contain fewer than four rows (minimum one). Those 168
cells contain 219 of the 50,000 vectors. The rule requires at least two fitting
and two held-out rows in every cell, so the exact 8,192/8,192 inventory cannot
be constructed. The inventory tool fails closed on this contradiction.

The three frozen CIFAR PCA/IVF inputs are also missing from their expected
locations.

Next action: resolve the GIST input-contract contradiction before observing
model outcomes. A defensible candidate is to freeze an eligible-cell sampling
frame containing only cells with at least four rows, while retaining the
8,192/8,192 sizes and proportional allocation; this is a sampling-method
correction and must not be applied silently. Then rerun the inventory preflight
and proceed to the native reader/scorer only if it passes.

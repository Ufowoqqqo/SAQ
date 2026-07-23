# Current Task: A4-OR-B base-data feasibility complete

## Branch and base

- Active branch: `saq-a4-original-reopening-protocol`
- Base commit: `383ffccb16e38cb324b5c037360acaa78d02e1d8`
- Prerequisite: revised `PASS_A4_OR_C_SYNTHETIC_ONLY`
- Active mode: `REVIEW`

The authorized base-only experiment completed on both datasets. Its terminal
result is `NO_GO_BASE_ONLY`. This does not authorize benchmark-query or native
scan evaluation.

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
64 fixed adjacent coordinate pairs, and B4/B8. Pair consecutive held-out rows
within each cell without reuse.

The inherited inventory is corrected before any model outcome is observed:

- compute occupancy from the content-identified assignment file;
- define eligible cells as exactly those with at least four base rows;
- exclude all rows from ineligible cells;
- within each eligible cell, preserve the inherited SHA-256 ordering and
  even-rank fitting/odd-rank held-out pool split;
- in each pool reserve the first two rows from every eligible cell;
- allocate the remaining rows to reach exactly 8,192 by the inherited
  capacity-proportional largest-remainder rule, breaking remainder ties by
  ascending original cell id; and
- bootstrap over the eligible original cell ids, retaining the inherited
  vector/pair weighting.

This changes only the sampling frame needed to make the registered inputs
feasible. It does not change datasets, selected coordinate groups, rates,
sample sizes, arms, metrics, thresholds, or query-unaware scope. Results
estimate behavior conditional on eligible cells and must report the excluded
cell and row counts.

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

The frozen CIFAR PCA artifacts were reproduced under `/tmp` from the raw base
without reading query or ground-truth files. The PCA base, centroids, and
cluster ids match all three registered hashes exactly.

## Forbidden reads and changes

Do not read benchmark queries, ground truth, Recall/QPS results, serialized
indexes, variance files, PCA matrices, prior A4 outcomes, or outputs from other
branches. Do not use held-out base rows for fitting or model selection.

Do not change datasets, groups, rates, sample sizes, seeds, histogram sizes,
thresholds, controls, or the query-unaware boundary after observing results.
Do not modify SAQ/CAQ production search code during A4-OR-B.

## Implementation plan and budget

Smallest falsifiable question: can the corrected eligible-cell GIST inventory
be constructed deterministically before any model is fitted? Only after that
preflight passes is the cheapest scientific check a GIST B4/B8 native smoke
using the complete frozen fit and held-out inventory.

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

A4-OR-B is complete. Both datasets ran successfully and every required
D/A/P/V, B4/B8, H1024/H2048, reconstruction, pair, group, cost, and bootstrap
row was produced. The result is recorded in:

`docs/saq_a4_or_b_base_only_result_2026_07_23.md`.

Only a pass would have permitted the query-free native scan microbenchmark.
The observed no-go ends this formulation before query evaluation.

## Current blocker and next action

There is no implementation, input, control, resource, or statistical blocker.
The scientific hypothesis failed: all `L_G`, `L_C`, and `L_Q5` hypotheses
failed Holm, while only the four `L_V` opportunity checks passed. B4 selected
no non-dyadic allocation; B8 activated non-dyadic allocations but produced
near-zero or negative held-out gains.

Do not implement a native scan kernel or access benchmark queries for this
formulation. The concrete next repository action is a bounded diff review and,
if requested, commit and push. Any further scientific work must begin from a
different mechanism-level question about how to capture the observed
two-dimensional opportunity; changing rates, groups, thresholds, or datasets
would be a rescue sweep and is forbidden.

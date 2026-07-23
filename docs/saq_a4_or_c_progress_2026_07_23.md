# A4-OR-C current progress

## Current status

A4-OR-C is complete with terminal status `CONTROL_INVALID`. The first failed
condition is `P_nsplit_zero`: the frozen ordinary product-quantization control
reported at least one Faiss empty-cluster split during training.

The authoritative result is commit `67009a8` and these files:

- `docs/saq_a4_or_c_synthetic_result_2026_07_22.md`;
- `docs/saq_a4_or_c_synthetic_artifacts_2026_07_22/terminal_result.json`;
- `docs/saq_a4_or_c_synthetic_artifacts_2026_07_22/numeric_admission.json`.

This result remains unchanged. It is not an A4-OR-C pass and grants no
natural-data, query, or A4-OR-B authority.

On 2026-07-23, the user authorized a narrow synthetic-only revision: P and V
validity will now check final occupancy, final center collision, exact shape,
and complete encoding. Intermediate `nsplit` remains reported but is no longer
fatal. The exact rule is recorded in
`docs/saq_a4_or_c_control_validity_revision_2026_07_23.md`. This opens a new
revision run; it does not alter the old terminal result.

## What passed before the stop

- all 1,044 tiny exact cases;
- mixed-radix pack/unpack and direct lookup checks;
- finite and nonnegative reconstruction checks;
- D/A allocation-order checks;
- P and V shape checks;
- zero final serialized-center collisions; and
- the replay discrepancy limit.

The experiment stopped at the P control rule. Later sensitivity, near-tie,
memory, measured timing, and projected-cost conditions are `NOT_RUN`.

## P-control postmortem

On 2026-07-23, a temporary diagnostic reproduced only the frozen P training on
the deterministic 8,192-by-128 synthetic panel. It did not run D, A, V,
natural data, or queries.

The diagnostic separated the eight Faiss redos so that split events could be
attributed to a subspace, redo, and iteration. This is equivalent to Faiss's
multi-redo initialization because pinned `Clustering.cpp` initializes redo
`r` with

```text
base_seed + 1 + r * 15486557
```

and chooses the lowest final training objective, with the earlier redo winning
an exact tie.

Temporary diagnostic identities:

- source SHA-256:
  `e3771807647cd615ae2601ef8732a100191b7cb8efd63658cd00f08fa47792af`;
- binary SHA-256:
  `3467a13b088c14ea23b0556b0a016e2ab22bd9bb6223417a3a60953c42dca8aa`.

It used one process, one thread, logical CPU 0, the frozen seeds, 256 centers,
eight redos, and the 300-iteration cap.

### Distinct training points

| Rate | P shape | Distinct points per subspace | Subspaces below 256 |
| --- | --- | --- | ---: |
| B4 | 32 four-dimensional subspaces | min 8,191; median 8,192; max 8,192 | 0 |
| B8 | 64 two-dimensional subspaces | min 3,123; median 7,021; max 7,744 | 0 |

The split events are therefore not explained by a subspace having fewer than
256 distinct training points.

### Intermediate split incidence

| Rate | Redo runs with a split | Subspaces affected | Winning runs with a split | Sum of split events |
| --- | ---: | ---: | ---: | ---: |
| B4 | 40 / 256 | 5 / 32 | 5 / 32 | 160 |
| B8 | 505 / 512 | 64 / 64 | 63 / 64 | 4,557 |

For B4, 39 affected redo runs first split at iteration 1 and one at iteration
2. For B8, 377 first split at iteration 0 and 128 at iteration 1. Splits are
therefore concentrated at initialization and the first update, especially for
the two-dimensional B8 control.

The formal run's aggregate `P nsplit=2855` is not the all-redo total above.
Pinned Faiss stores a cumulative `iteration_stats` vector and restores the
snapshot associated with the winning redo. That representation can include
earlier redo statistics and omit later ones. Both measurements provide a
reliable nonzero witness, but their totals have different meanings.

### Final-model checks

Across all 768 independently inspected redo runs:

- final reassignment empty clusters: 0;
- final duplicate centers: 0.

For the selected winners:

- B4 encoded exactly `8192 * 32 = 262,144` byte labels;
- B8 encoded exactly `8192 * 64 = 524,288` byte labels;
- both encoded reconstructions were finite; and
- the frozen center count and subspace shape were complete.

Faiss calls `split_clusters` after computing centroids, then adds the repaired
centers to the index for the next iteration. The evidence therefore identifies
`nsplit` as an intermediate empty-cluster recovery event in these runs, not a
remaining empty cluster or malformed final P model.

## Scientific interpretation

The frozen rule “any intermediate `nsplit` invalidates P” is stricter than a
final-model validity test. On this synthetic panel it rejects complete,
collision-free, fully encodable final controls; at B8 it rejects almost every
winning training run.

This does not retroactively change A4-OR-C. The committed result remains
`CONTROL_INVALID`. It does show that the stop was caused by the control
validity definition, not by evidence that the arbitrary-cardinality candidate
failed its quality or cost hypothesis.

That scientific decision has now been made: the final-model rule is authorized
for a revised synthetic admission. Before an expensive rerun, the runner must
compile, preserve the tiny exact results, and be checked for complete
sensitivity, near-tie, resource, and timing decisions. Natural-data work
remains unauthorized.

## Revised synthetic admission

The revised runner was built and executed on 2026-07-23. One warmup and all
three measured repetitions passed. P and V had zero final empty centers, zero
final center collisions, exact shapes, and complete encodings; intermediate
`nsplit` remained nonzero and diagnostic.

The two-dataset projected D/A CPU time was 1,857,618,614 microseconds
(30.96 minutes), support/scientific CPU ratio was 0.00000969393,
A-specific/shared-scalar CPU ratio was 0.000000670752, and maximum peak RSS was
233,926,656 bytes. All frozen cost limits passed.

The separate result is
`docs/saq_a4_or_c_revised_synthetic_result_2026_07_23.md`. This supports only
`PASS_A4_OR_C_SYNTHETIC_ONLY`; natural data, queries, Recall, and A4-OR-B remain
outside the active authority.

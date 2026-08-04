# Active Task: SAQ base-trained joint-objective viability diagnostic

## State and question

- Branch: `saq-mixed-radix-query`
- Base snapshot: `15f8617`
- Modes: `IMPLEMENT`, `EXPERIMENT`, `REVIEW`

The user selected the explicit pivot identified by the static audit:

> Does a base-trained, estimator-aware joint choice of existing segment-1 and
> segment-2 CAQ codes obtain material held-out estimator-error improvement over
> independently chosen codes, without changing the SAQ plan, stored format, or
> query consumer?

The smallest hypothesis is that cross-segment workload information is
actionable rather than merely nonzero.  On a frozen local alternative-code
set, joint training should reduce held-out estimator MSE relative to
independent training by at least 5% in both cross-fit folds and improve at
least 60% of target vectors.  The 5% line is deliberately below, but of the
same order as, the approximately 9% interaction excess relative to production
inversion rate in the preceding exact-replacement diagnostic.

This is an offline base-only mechanism diagnostic.  It is not a production
encoder, Recall/QPS result, novelty claim, or performance comparison.

## Frozen inputs and population

Read only:

- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs`;
- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index`.

Reuse the deterministic population from the component oracle with seed
`2026080304`: 256 probes and a disjoint 4,096-row pool.  Use probes `0..127`
and `128..255` as the two direction folds.  Use the first 32 pool rows as
fixed target vectors.  Cross-fit twice: train code choices on one direction
fold and evaluate unchanged choices on the other, then swap folds.

For each target, construct query residual directions relative to that target's
stored IVF centroid and apply the existing segment-local rotation exactly as
the accurate consumer does.

Forbidden reads: benchmark queries, ground truth, query-result tables, another
dataset/index, or any previous generated payload beyond accepted notes.

## Frozen feasible alternatives and arms

Target only segment 1 (`192d@6b`) and segment 2 (`320d@4b`).  For each segment
and target, decode the stored production code and include:

1. the production code;
2. every code obtained by changing exactly one coordinate by `-1`, when legal;
3. every code obtained by changing exactly one coordinate by `+1`, when legal.

For every alternative, recompute `rescale=||x||^2/<x,z>` in float64 from the
decoded normalized grid direction.  Reject only a non-finite or non-positive
inner product.  Do not add multi-coordinate search, random alternatives,
learned codebooks, bit changes, rescale fitting, thresholds, or query-trained
features.

Report these arms at identical serialized bytes and query arithmetic:

- `PROD`: stored codes and rescale;
- `IND_TRAIN`: independently minimize training direction MSE in each segment,
  then combine the selected codes;
- `JOINT_TRAIN`: minimize combined training direction MSE over the Cartesian
  product of the two alternative sets;
- `JOINT_EVAL_ORACLE`: minimize on the evaluation directions, reported only as
  a local diagnostic ceiling and never as a learned method.

## Metrics and decision

Before outcome inspection, require the existing stored/recomputed production,
norm, rescale, and exact-distance parity checks.  Additionally require the
decoded production alternative to reproduce the stored segment contribution
within relative error `1e-5` for all targets and directions.

For each cross-fit fold and combined, report:

- squared accurate-estimator error and relative change versus `PROD` and
  `IND_TRAIN`;
- fraction of targets where `JOINT_TRAIN` beats `IND_TRAIN` on evaluation;
- fraction of targets where joint and independent code choices differ;
- local-alternative counts and evaluated Cartesian pairs per target;
- train/evaluation cross-term contributions for the selected alternatives;
- CPU, wall time, peak RSS, and output bytes.

Decision:

- `JOINT_LOCAL_ACTIONABLE`: in both cross-fit folds, `JOINT_TRAIN` reduces
  evaluation MSE versus `IND_TRAIN` by at least 5%, improves at least 60% of
  targets, and has finite deterministic output;
- otherwise `JOINT_LOCAL_NO_GO`.

The evaluation oracle cannot pass the gate.  A pass authorizes only a later
method-design review; a fail closes this workload-coupling lead under the
frozen one-coordinate neighborhood.

## Allowed changes, commands, and budget

Modify only `research/saq_component_oracle/`, this task file, the decision log,
one design note, and one result note.  Do not modify production `saqlib/`.
Generated outputs belong under `/tmp/saq-joint-objective-v1/` and must not be
committed.

Allowed commands are the focused CMake configure/build/test, `parity-v1`, the
new frozen diagnostic mode, byte reproduction, resource inspection, and Git
diff/status checks.  Do not build a new index.

Budget: 2 aggregate CPU-hours, 1 wall-hour, one thread, 4 GiB peak RSS, and
10 MiB generated output.  Stop on parity failure, non-finite arithmetic, or a
resource-limit breach.

Expected scientific-core change: roughly 200--350 lines in the focused runner
and 30--80 test lines.  Support should remain below the scientific core and
reuse the existing reader, parity, population, and resource reporting.

## Deliverables and done criteria

Done means the frozen population and alternatives are recorded; focused tests
and parity pass before outcome inspection; both cross-fit folds and all four
arms are complete for 32 targets; one unchanged run reproduces byte-identical
scientific outputs; costs and limitations are reported; and exactly one frozen
decision is selected.

Current blocker: none.  The diagnostic is complete with
`JOINT_LOCAL_NO_GO`.  In the two cross-fit directions, joint selection changes
held-out MSE versus independent selection by `+0.0805%` and `-1.3644%`, and
improves only 15/32 and 13/32 targets.  Primary and unchanged reproduction
scientific files are byte-identical.  Full result:
`docs/research/saq_joint_objective_viability_result_2026_08_04.md`.

One concrete next action: record this terminal local negative result in the
meeting summary when requested.  Do not enlarge the code neighborhood, tune
the direction split, lower the gate, implement a production consumer, or read
benchmark queries to rescue this workload-coupling lead.

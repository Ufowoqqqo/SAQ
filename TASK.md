# TASK.md

## Active Goal

Preserve the completed Phase 1/1b evidence and closure decision for the
full-dimensional PCA limitation hypothesis. Do not continue PCA-replacement
method development from this branch; select a distinct SAQ research question
before beginning another experiment.

The target is a database top-conference-level contribution suitable for SIGMOD,
VLDB, or ICDE. The work is independent of the graph-index direction. Judge it
by research novelty, falsifiable evidence, complete overhead accounting, and
reviewer defensibility rather than by implementation volume.

The authoritative plan is
`docs/saq_transform_replacement_research_proposal_2026_07_10.md`.

## Phase 1 And Phase 1b Decision

The minimal Phase 1 operating point is complete. The result is recorded in
`docs/saq_transform_phase1_limitation_evidence_2026_07_10.md`, with compact
machine-readable summaries under
`docs/saq_transform_phase1_artifacts_2026_07_10/`.

Decision:

```text
Do not advance to learned-transform development from this evidence.
```

Residual PCA lowered matched-plan mean per-query candidate RMSE by about 0.60%
at the first accurate prefix and 0.33% at full code. The prefix effect held for
all ten rotation seeds and with rotation off, but ranking confidence intervals
included zero and the fast prefixes worsened. Identity and random orthogonal
transforms exposed plan/rotation tradeoffs rather than an outer-transform
dominance result. The evidence therefore identifies a narrow estimator
mismatch, not a defensible SAQ progressive-ranking contribution.

The explicitly reopened Phase 1b external replication is also complete. Its
preregistered protocol and evidence are recorded in:

- `docs/saq_transform_phase1b_external_replication_protocol_2026_07_10.md`;
- `docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md`.

Phase 1b used CIFAR60k, all 1,000 queries, one canonical raw float64 exact
reference, a frozen four-segment current-PCA plan, identical candidates and
serialized bytes, ten paired internal-rotation seeds, and rotation off. The
artifact gate passed, but the narrow replication gate failed:

```text
accurate_prefix_1 mean-query RMSE delta: +1.394e-6
95% CI: [-2.216e-5, +2.461e-5], seeds favoring residual PCA: 4/10

full mean-query RMSE delta: -2.610e-7
95% CI: [-1.043e-6, +5.094e-7], seeds favoring residual PCA: 5/10
```

Rotation-off was opposite to the registered direction at both endpoints, and
`fast_all` RMSE significantly favored current PCA. The registered decision is:

```text
close_one_dataset_estimator_effect
```

This closes the PCA-replacement premise on this branch. It does not prove PCA
universally optimal; it establishes that the current evidence does not justify
spending research degrees of freedom on a learner or broader transform sweep.

## Starting Point

This branch starts from `saq-correctness-base` and keeps only correctness fixes
needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search support.

No graph prototype, graph result, profiler, runner, or graph research document
is part of the starting point. Previous branches remain historical evidence and
should not be migrated by default.

## Current Understanding

The repository's current PCA preprocessing is full dimensional:

```text
D_OUT = D_IN
```

It changes basis, decorrelates coordinates, and orders them by variance, but it
does not physically reduce the vector dimension. Effective rate reduction is
instead introduced by SAQ's mixed-bit plan, including an optional 0-bit tail.

The current design exposes five research-relevant facts:

1. The planner minimizes a variance proxy approximately proportional to
   `segment_variance / 2^bits`, rather than measured CAQ or prefix ranking
   error.
2. Segment boundaries are constrained to contiguous 64-dimensional blocks and
   a 0-bit region is a tail segment.
3. Each positive-bit segment may receive its own random orthogonal rotation,
   which can erase gains from an outer transform that only changes within-
   segment orientation.
4. A 0-bit tail still stores a base residual norm. Its L2 estimate keeps the
   base and query tail norms while omitting the tail inner product, so a simple
   "PCA head plus tail norm" proposal overlaps both current SAQ behavior and
   MRQ.
5. Existing transformed-data tests can treat the projected space as exact and
   therefore hide `D -> d` projection error. New lossy experiments must retain
   original-space exact distance and ground truth.

## Research Question

```text
Does PCA's variance-only objective mismatch the actual error of SAQ's
segmented CAQ estimator and progressive prefixes, and can one base-only,
global, full-dimensional orthogonal transform jointly with one global SAQ plan
improve the rate-error-work or Recall-QPS-bytes Pareto frontier?
```

The null result is valid and should stop the direction: PCA and the current SAQ
plan may already be sufficiently well matched after simple controls and
per-segment rotations.

## Scope

Primary scope:

```text
L2 + IVF
full-D affine orthogonal transforms
base/index data only for fitting
held-out queries only for evaluation
one dataset-level transform
one global segment/bit plan
no index-format change during the limitation study
```

Secondary diagnostic scope:

```text
lossy D -> d projection
original-space ground truth retained
projection, quantization, and staging error reported separately
truncated PCA, LeanVec-ID, and MRQ treated as direct baselines
```

## Related-Work Gate

Simple transform coding and bit allocation, ITQ/OPQ-style learned rotations,
LeanVec-style projection plus scalar quantization, GleanVec local projections,
and MRQ's PCA head plus tail correction already occupy the broad design space.
Therefore:

- random projection, FHT, ITQ, OPQ, truncated PCA, and compact tail summaries
  are controls or baselines, not contributions;
- a learned method is only viable if it targets measured SAQ-specific CAQ or
  prefix-estimator error under an actual-byte budget;
- if residual PCA, coordinate permutation, OPQ, or the internal segment
  rotations explain the gain, stop rather than rebrand the baseline.

## Immediate Next Step

Do not implement a learned transform, broaden the transform sweep, rerun the
gate on a more favorable dataset/plan/budget, or begin the counterfactual
`(segment, bit)` analysis. Preserve this branch as completed negative evidence
and select a different independent SAQ research question.

## Continue Gate

Phase 1 met the weak diagnostic trigger through one stable GIST
accurate-prefix RMSE mismatch. Phase 1b failed to reproduce that trigger on the
registered second regime. The stronger learner/contribution gate remains
closed; a learned transform would have required all of the following:

- the variance proxy systematically mispredicts measured CAQ or prefix error;
- the mismatch is stable across predeclared seeds and more than one spectral
  regime;
- a base-only global candidate improves error/ranking at matched actual bytes
  and complete query work;
- the result survives frozen-plan and segment-rotation ablations;
- residual PCA, permutation, FHT/random rotation, and OPQ/ITQ-style controls do
  not explain the result;
- the improvement has a plausible path to end-to-end IVF Recall-QPS gains.

The GIST 0.60% accurate-prefix and 0.33% full-code RMSE changes, followed by the
failed CIFAR replication, do not satisfy these conditions and must not be used
to justify a learner. The selected-segment proxy correlations also do not
replace a counterfactual segment-by-bit evaluation of the planner choice
space—and the failed replication does not authorize that evaluation.

## Lossy Projection Diagnostic

This is a historical secondary-track specification, not an active next step.
The failed Phase 1b gate does not authorize it.

Only after the primary diagnostic is defined, evaluate `D -> d` as a separate
track. For the existing GIST PCA plan, use predeclared plan boundaries rather
than tuning arbitrary dimensions:

```text
d in {64, 256, 576, 832, 960}
```

Measure, for the same query-candidate pairs:

```text
D0: original exact distance
DP: projected exact distance plus the selected tail summary
DQ: projected full-SAQ distance with exact-tail diagnostic
DT: projected staged/full-SAQ distance plus the selected tail summary
```

Report projection error, quantization error, staged error, their covariance,
and total error. Keep the original IVF candidate lists fixed first; rebuild a
low-dimensional IVF index only if the offline gate passes.

## Stop Conditions

Stop treating PCA replacement as a main research direction if any of the
following is observed:

- the variance proxy already predicts measured CAQ/prefix error adequately;
- residual PCA, a coordinate permutation, OPQ, or internal segment rotations
  reproduce the full gain;
- projection error dominates and the best design is truncated PCA plus a tail
  norm/variance, making it an MRQ-style variant;
- the design requires benchmark queries, per-cluster transforms, plan ids, or
  mixed dispatch;
- transform/model/metadata overhead removes the scan benefit;
- fixed-candidate improvements do not transfer to end-to-end IVF;
- gains appear only on one dataset or operating point, are seed-sensitive, or
  amount to small noisy recall/QPS changes.

Record a negative result as evidence that full-dimensional PCA and current SAQ
are already well matched; do not force a method from a failed premise.

## Reporting Constraints

- Match actual serialized bytes, not nominal `B` alone.
- Include raw-query transform and preparation time in end-to-end QPS.
- Report model/operator bytes, centroids, segment rotators, factors, tail
  metadata, padding/alignment, and rerank vectors consistently.
- State dataset, `K`, `B`, transform, dimensions, `nprobe`, candidate set,
  metric, plan, seeds, command, and block-min mode for every search claim.
- Prefer small falsifiable experiments over more tooling.
- Keep durable documents concise and paper-facing.

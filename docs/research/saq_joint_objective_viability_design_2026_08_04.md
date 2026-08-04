# SAQ base-trained joint-objective viability diagnostic

Date: 2026-08-04

## Purpose

The static audit proved that the fixed two-segment feasible set is a Cartesian
product.  Standard reconstruction and isotropic unseen-direction objectives
therefore separate, but a workload-conditioned estimator loss can contain a
cross term.  This diagnostic asks the cheapest empirical question needed
before method implementation:

> Is that cross term large and stable enough that joint selection from a tiny
> existing-code neighborhood beats independent selection on held-out base
> directions?

The test retains the current SAQ plan, code format, per-segment rescale, index,
and accurate query formula.  It changes no production code and reads no
benchmark query.

## Falsifiable hypothesis

For both directions of a 128/128 base-probe cross-fit, `JOINT_TRAIN` must beat
`IND_TRAIN` by at least 5% in aggregate held-out estimator MSE and on at least
60% of 32 fixed target vectors.  Failure selects `JOINT_LOCAL_NO_GO` and stops
this local workload-coupling lead.

## Population and alternatives

The input, seed, probe/pool split, target rows, segment pair, alternative set,
arms, metrics, thresholds, commands, and resource limits are frozen in
`TASK.md`.  The alternative family is intentionally small and symmetric:
production plus every legal one-coordinate `+1/-1` code move.  Each code uses
the current analytical CAQ rescale, not a fitted scalar.

The two direction folds are swapped so every reported learned arm is evaluated
on directions that did not select its codes.  `JOINT_EVAL_ORACLE` exposes only
the local neighborhood ceiling and cannot affect the decision.

## Why these controls discriminate the mechanism

`IND_TRAIN` is the decisive control.  It receives the identical direction
population and alternative codes but deletes the cross-segment term by
optimizing each segment alone.  Therefore `JOINT_TRAIN - IND_TRAIN` isolates
the incremental value of workload coupling rather than ordinary local code
repair.

`PROD` shows whether the neighborhood contains any estimator-aware headroom.
`JOINT_EVAL_ORACLE` separates lack of learnability/generalization from lack of
representational alternatives, but is never method evidence.

## Claim and cost boundaries

A pass would show only that a local, base-trained joint objective merits method
design.  It would not establish Recall improvement, query generalization,
cross-dataset stability, affordable full encoding, or novelty over
estimator-aware quantization.  The Cartesian pair count and CPU time must be
reported because an accuracy-only gain with prohibitive construction work is
not paper-viable.

The runner remains `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`.  Its hot path is
alternative projection and Cartesian training-loss evaluation; evidence
serialization is outside the measured scientific loop.  There is no SOTA
comparison: `PERFORMANCE_NOT_YET_MEASURED`.

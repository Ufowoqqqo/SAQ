# TASK.md

## Active Goal

Evaluate a new, independent **lossy projection + SAQ** research line. Test
whether physically materializing a base-only `D -> d` representation exposes
an original-space Recall-QPS-bytes opportunity beyond full-D SAQ and the
closest projection/quantization systems.

Current status:

```text
branch opened
bounded related-work review complete for branch opening
LP-0 preregistered
LP-0 Gate A completed: FAIL
registered GIST/d576/B4 line stopped before Gate B
no contribution established
```

Authoritative documents:

- `docs/saq_lossy_projection_research_proposal_2026_07_11.md`;
- `docs/saq_lossy_projection_related_work_2026_07_11.md`;
- `docs/saq_lossy_projection_related_work_sources_2026_07_11.json`;
- `docs/saq_lossy_projection_lp0_preregistration_2026_07_11.md`;
- `docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md`.

## Boundary From The Parent Branch

The parent `saq-transform-analysis` study tested full-dimensional L2-isometric
transforms. Its preregistered CIFAR60k replication closed the PCA-objective
replacement premise:

```text
close_one_dataset_estimator_effect
```

Do not reopen it by changing the dataset, prefix, budget, or transform. That
negative result did not test physical dimension reduction:

```text
parent: D -> D, exact L2 preserved, basis objective tested
current: D -> d, original-space error accepted, physical state/work tested
```

Reuse only canonical raw exact replay, deterministic candidates, provenance,
and confidence-interval infrastructure that directly serves the new question.

## Current Evidence

1. `python/pca.py` fixes `D_OUT = D_IN`; the checked-in execution path is
   physically full dimensional.
2. The SAQ paper nevertheless defines dimension reduction as PCA plus tail
   discard and presents SAQ as bridging reduction and balancing.
3. The frozen GIST plan is
   `0:64@11 | 64:256@6 | 256:576@4 | 576:832@2 | 832:960@0`.
4. A 0-bit L2 residual segment retains base/query residual norms and omits the
   residual-tail inner product. A head plus tail norm is therefore a current
   SAQ/MRQ control, not a contribution.
5. SAQ accepts a projected dimension and pads it to 64-coordinate blocks.
6. The Gate-A diagnostic now supports common `D0` with `raw_D=960` and
   projected `d=576`, emits candidate-level `D0/DP/DS`, and validates all
   ranking and error identities against the frozen replay.
7. The old PCA-prefix routine in `src/test_ivf.cpp` is not SAQ and has no
   checked-in evidence of a lossy run.
8. No local ASH, MRQ, LeanVec, or GleanVec implementation/artifact is present.
9. At the frozen point, the exact tail-norm oracle has top-100 agreement
   `0.992890625` versus native SAQ `0.9946171875`; the paired delta lower bound
   is `-0.002578125`, below zero.
10. Its boundary-inversion rate is `6.852478398e-6` versus native
    `4.086870951e-6`; the paired delta upper bound is `4.216880965e-6`, above
    zero. Both Gate-A conditions fail, with the same directions rotation-off.
11. Deployed float32 tail-summary RMSE is only `1.507223596e-7`, compared with
    exact tail-norm projection RMSE `0.002481796224`; summary rounding does not
    explain the ranking failure.

## Research Question

```text
At matched deployable bytes and complete query work, does physical D -> d
projection interact non-separably with SAQ's heterogeneous segments, CAQ
adjustment, and progressive stages, producing an original-space Pareto point
not explained by logical tail omission, ASH, MRQ, LeanVec-ID, DADE/ADSampling,
or uniform-bit projected quantization?
```

Null explanations are projection error, logical/physical equivalence,
ordinary tail summaries, uniform rate reallocation, full-vector reranking, and
closest-system dominance.

## What LP-0 Can And Cannot Show

LP-0 freezes the first three plan segments and does not reallocate saved bits.
It can measure:

- the exact projected-surrogate upper bound;
- frozen projected-SAQ quality and progressive compatibility;
- algebraic equivalence between physical and logical head-only estimators;
- gross savings versus native full-D SAQ;
- incremental persisted-state savings versus the equivalent logical view.

It cannot demonstrate the non-separable plan hypothesis. Passing LP-0 only
authorizes closest-baseline analysis and, conditionally, a separately
preregistered byte-matched plan-interaction test.

## LP-0 Frozen Point

```text
dataset                 data/gist_sample50k
N, D                    50,000, 960
queries                 first 128
IVF                     K=512, frozen nprobe=16 probes
candidates              every vector in the frozen probed lists; no cap
candidate inventory     442,823 total, frozen SHA-256 in protocol
top-k                   100
nominal parent budget   B=4
confirmatory d          576 only
retained plan           0:64@11 | 64:256@6 | 256:576@4
retained payload        3,136 bits/vector, 5.444 bits/retained dimension
rotation                seeds 0..9; off reported separately
bootstrap               query-paired, 10,000 resamples, seed 20260711
```

`d=576` is selected from the base-only plan. It removes 40% of PCA output
components and 512 positive code bits: 13.33% of the nominal four-bit budget,
or 14.04% of the frozen plan's actual positive code bits. Do not substitute a
different `d`, budget, plan, prefix, or candidate set.

All input/operator/probe hashes, numerical tolerances, tail precision, byte
denominator, and decision rules are frozen in the LP-0 protocol.

## LP-0 Arms

- `native_full_saq`: full-D five-segment reference; confirmatory endpoints are
  `full` and `fast_all`.
- `oracle576_none`: exact retained PCA head only.
- `oracle576_norm`: exact retained head plus exact float64 residual-tail norms,
  omitting the tail inner product.
- `logical576_norm`: full persisted index, first-three full-code estimates,
  and the same one-scalar float32 tail sidecar/query term as the physical arm.
- `physical576_norm`: three-segment persisted index plus that identical
  sidecar and query term.

The implemented `accurate_prefix_3` remains descriptive: it refines the first
three segments but still uses fast suffix estimates. It is not a logical stop
at dimension 576.

`logical576_norm` and `physical576_norm` must have identical decoded retained
state, estimator bit patterns, and ranking digests. A difference is an invalid
artifact, never evidence that physical projection improves ranking.

## Error Contract

Every candidate uses a common original-space exact reference and emits:

```text
D0 = original-space float64 exact distance
DP = exact projected surrogate with exact tail treatment
DS = exact projected head with deployed tail-summary precision
DQ = full projected-SAQ with deployed tail summary
DT = staged projected-SAQ with deployed tail summary

e_projection   = DP - D0
e_summary      = DS - DP
e_quantization = DQ - DS
e_staging      = DT - DQ
e_total        = DT - D0
```

Report component covariance and validate the additive identity. Do not hide
projection or summary error inside "quantization error".

## Registered Gates

### Gate A: Exact-Surrogate Upper Bound

Compare `oracle576_norm.DP` with seed-averaged `native_full_saq.full` under raw
labels. Both one-sided zero-margin ranking bounds must be favorable: agreement
lower bound at least zero and inversion upper bound at most zero.

Failure means insufficient evidence at this registered GIST/`d=576`/`B=4`
point. It is not a universal claim about projection.

**Observed result: FAIL.** Agreement lower bound `-0.002578125`; inversion
upper bound `4.216880965e-6`. Stop this registered line.

### Gate B: Frozen Projected SAQ

**Not authorized because Gate A failed.** The text below preserves the
registered conditional rule and is not an execution instruction.

After enforcing exact logical/physical equivalence, compare
`physical576_norm.DQ` with `native_full_saq.full`. Require the same two
zero-margin ranking bounds, at least 8/10 seeds with favorable point-estimate
directions, and matching rotation-off directions. RMSE is required but
secondary; do not use failure to reject a non-inferiority hypothesis that was
not registered.

### Gate C: Progressive Endpoint

The only confirmatory staged comparison is projected `fast_all` versus native
`fast_all`, with the same zero-margin ranking bounds. Other stage curves are
descriptive; no post-hoc stage may rescue failure.

### Gate D: Systems Accounting

Report separate ledgers:

- gross versus native full-D SAQ: projection work, online operator state,
  total serialized bytes, full-stage candidate bytes, and query preparation;
- incremental versus `logical576_norm`: exact estimator equivalence and only
  the persisted/resident state actually removed by physical materialization.

If the incremental result is storage-only, label it storage-only. Do not
attribute gross query-work savings to physical representation beyond a logical
sliced view. Use the complete byte denominator and thresholds in the protocol.

### Gate E: Closest Baselines

Only after Gates A--D pass, evaluate ASH, MRQ/MRQ+, LeanVec-ID or its
reproducible projection control, uniform-bit projected quantization, and
compatible DADE/ADSampling controls. Use simultaneous paired-query bounds over
the baseline envelope.

Passing Gate E authorizes a new plan-interaction preregistration, not a method
claim.

## Later Phases

The phases below are not authorized on the registered line because Gate A
failed. They remain historical conditional design, not an active plan.

1. **Plan-interaction gate:** predeclare a byte-matched projected SAQ plan and
   uniform-rate control using base statistics only. Test whether `d` and SAQ's
   heterogeneous/progressive plan are genuinely non-separable.
2. **End-to-end IVF:** rebuild projected IVF only after the offline and closest
   baseline gates. Time raw projection, routing, tail work, scan, refinement,
   and original-vector reranking.
3. **External replication:** freeze the mechanism and base-only selection rule
   before a second spectral regime. Do not tune `d`, plan, stage, or bounds on
   its held-out queries.

## Immediate Next Action

Preserve the Gate-A negative result and stop the registered
GIST/`d=576`/`B=4` line. Do not build projected SAQ, run Gates B--E, change the
persisted format, learn a projection, rebuild IVF, import a large baseline, or
sweep dimensions/budgets/plans/tail rules as a rescue.

Before any new lossy-projection proposal, first review the closest primary
work again and identify a distinct SAQ-specific limitation not answered by
this exact-surrogate failure. A viable new question requires a new
preregistration and cannot reuse held-out query outcomes to select its design.

## Stop And Reporting Rules

Stop if any registered gate fails, if logical/physical rankings differ, if the
gain is storage-only and closest work already covers it, or if the method needs
query-aware/local state. Record a negative result as no evidence at the frozen
point, not as universal projection failure.

For every claim record dataset and hashes, `D`, `d`, plan, `K`, `B`, probes,
candidates, tail precision, seeds, command, raw-label scope, actual serialized
and resident bytes, complete work, and block-min mode where applicable.

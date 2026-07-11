# New-Direction Go/No-Go Memo: Finite-Round CAQ Optimality

Date: 2026-07-11

## Executive Decision

**Conditional GO for one offline oracle gate; NO-GO for method development at
present.**

The bounded primary-source review closes five broader directions and leaves
one precise SAQ premise worth testing:

```text
SAQ relies on a fast finite-round CAQ encoder in place of E-RaBitQ's exact
grid-on-sphere encoder. Does SAQ's heterogeneous segmentation create a regime
where production r=6 CAQ leaves a material, systematic alignment/error-factor
gap to the exact codeword?
```

The next authorized work is `CO-0`, a base/index-data-only comparison against
a source-validated E-RaBitQ oracle. A positive result establishes only that the
limitation exists. It does not establish a new encoder, a systems contribution,
or a paper.

All other reviewed candidates are no-go as independent main directions:

- certified progressive bounds collide with RaBitQ/E-RaBitQ,
  ADSampling/DADE, MRQ, SymphonyQG, and TurboQuant;
- streaming adaptation collides with OnlinePQ/OnlineOPQ, DeDrift/SPFresh, and
  CoDEQ, while old variable-width SAQ codes are not backward compatible with a
  changed global plan;
- filtered staging is a generic candidate-generation, heap, and physical-plan
  effect already addressed by filtered-vector systems;
- SIMD/tiered layouts are mature and the graph branch already found a large
  non-layout overhead;
- arbitrary `2..B` CAQ prefixes are not consumed by current IVF SAQ.

The supporting review is
`docs/saq_limitation_primary_source_review_2026_07_11.md`; its source ledger is
`docs/saq_limitation_primary_sources_2026_07_11.json`.

## Limitation Being Tested

CAQ and E-RaBitQ use equivalent direction codebooks, but their encoders are
different:

```text
E-RaBitQ exact/pruned search: O(2^B * D * log D)
CAQ coordinate adjustment:  O(r * D), production r=6
```

The SAQ theorem is conditional on CAQ solving the cosine objective. The paper
states that coordinate adjustment need not find the optimum and already reports
a small average gap even at `B=4, r=32`. The unchecked possibility is not
generic local-search failure. It is a segment-amplified failure mode created by
SAQ itself:

- leading segments can be short and use very high bit widths;
- later segments are longer and use fewer bits;
- the same fixed six rounds are used across these different discrete search
  spaces;
- the achieved code and rescale control every full-code estimate for that
  segment.

The encoder also stores an error factor derived from achieved cosine, but the
current search path never reads `ExFactor.error`. It uses the code and
`rescale`. Therefore an oracle reduction in stored error factor is only a
diagnostic; the gate must show an improvement under the unchanged estimator.

This question holds the PCA view, IVF assignments, residual vectors, segment
boundaries, bit widths, rotation seeds, storage, and query estimator fixed. It
does not reopen planner-objective, transform, or lossy-projection work.

## Research Question And Null

Research question:

```text
For frozen SAQ residual segments, how much of the exact E-RaBitQ
grid-on-sphere alignment opportunity remains after production six-round CAQ,
and is the regret systematically concentrated in SAQ's short/high-bit
segments?
```

Null explanation:

```text
Finite-round CAQ is already close enough to the exact codeword across SAQ
segment regimes; any residual difference is rare, tiny, dataset-specific, or
recoverable only by the known E-RaBitQ time cost or by increasing r.
```

The null is the expected outcome until the oracle gate says otherwise.

## Expected Contribution If The Gate Eventually Leads To A Method

A defensible later contribution would need to be more than “run more CAQ
rounds” or “fall back to E-RaBitQ.” The target would be:

```text
a base-only certificate or deterministic repair that identifies hard
SAQ segment encodings and closes a material part of the exact objective gap,
while preserving the existing codebook, global plan, serialized code size,
factors, estimator, and query-time work.
```

The paper-level value would come from jointly showing:

1. SAQ segmentation creates a reproducible encoder regime not exposed by
   uniform-bit whole-vector CAQ;
2. a cheap certificate predicts objective regret before exact encoding;
3. selective repair improves the build-time versus estimator-error frontier
   over both default CAQ and exact E-RaBitQ;
4. the frozen encoder improvement transfers to recall at unchanged index bytes
   and query work on multiple datasets.

Without all four, the result is encoder validation or parameter tuning rather
than a database-systems contribution.

## Overhead Model

The gate must report encode-side overhead even though no query path changes.

For every segment arm record:

- rotation and residual preparation time;
- objective-evaluation and code-adjustment operations;
- sort/enumeration work in the exact oracle;
- elapsed time and cycles per encoded coordinate;
- peak transient memory;
- fraction of segment codes sent to any repair arm;
- permanent metadata and serialized bytes, which should remain unchanged.

A later method is allowed build-time overhead, not hidden query-time overhead.
Any extra per-vector certificate, plan identity, or alternate code must be
counted. A result that needs two stored codes or mixed query dispatch violates
the intended architecture.

## Strict-Reviewer Objection

The strongest likely objection is:

> The SAQ paper already says coordinate descent is approximate and evaluates
> adjustment rounds. E-RaBitQ already supplies the exact encoder, LSQ++ makes
> approximate local-search encoding routine, and TurboQuant supplies a fast
> analyzed quantizer. A selective exact fallback is an obvious build-time knob.
> Where is the database contribution?

The work survives this objection only if the gap is specifically amplified by
SAQ's heterogeneous segment geometry and a new cheap certificate/repair moves
the CAQ--E-RaBitQ Pareto frontier without changing query state. Merely finding
nonzero objective regret is insufficient.

## CO-0: Exact-Oracle Limitation Gate

### CO-0A: Oracle And Codebook Parity

Before measuring data, review and pin the official Extended-RaBitQ artifact.
Do not reimplement the oracle from the SAQ prose alone.

Required validity checks:

1. record the upstream repository URL, commit, build flags, and license;
2. for tiny predeclared `(D,B)` cells, enumerate the complete grid codebook and
   verify that the official encoder reaches the same maximum cosine;
3. verify the normalization/code mapping asserted by SAQ's codebook-equivalence
   lemma;
4. verify objective, code, alignment, rescale, and error-factor calculations
   independently in float64;
5. reject the artifact if padding, clipping, or bit-order differences change
   the feasible codebook.

Failure of any parity check is an invalid gate, not evidence against CAQ.

### CO-0B: Frozen Base-Only Screen

Use two already established regimes and no benchmark queries:

```text
GIST sample50k, K=512, B=4 plan:
  64@11 | 192@6 | 320@4 | 256@2 | 128@0

CIFAR60k, K=512, B=4 plan:
  64@9 | 192@5 | 128@3 | 128@0
```

The final preregistration must freeze a deterministic cluster-stratified base
sample and rotation seeds after an oracle-complexity dry run that uses synthetic
vectors only. Dataset values must not be inspected to choose sample size,
segments, or seeds.

For every positive-bit segment compare:

- `lvq_init`: independent scalar initialization, no adjustment;
- `caq_r6`: the production six-round CAQ arm;
- `caq_local_fixed_point`: continue the identical coordinate rule until no
  coordinate changes, implemented explicitly because the current `r=0` option
  disables adjustment rather than invoking an unlimited run;
- `erabitq_exact`: source-validated exact grid-on-sphere oracle.

Hold the residual, rotation, quantization range, codebook, padding, and numeric
precision common. The exact arm is an oracle, not a deployable timing baseline.

Add exactly two attribution controls, not a bit-width sweep:

- re-encode each frozen segment at uniform `B=4`, the nominal SAQ budget, with
  the same four encoder arms;
- encode the complete positive-dimensional residual view at uniform `B=4`
  with the same rotation seed and encoder arms.

The first separates a high-bit effect from segment data/dimension; the second
tests whether any regret is generic whole-vector CAQ behavior. No other `B`,
dimension, boundary, or plan may be selected after observing the gate.

### Metrics

For each vector/segment emit:

```text
cos_init, cos_r6, cos_local, cos_exact
objective_regret = cos_exact - cos_r6
error_factor_init, error_factor_r6, error_factor_local, error_factor_exact
code_equal_r6_exact
adjustment rounds and accepted coordinate moves
encoding time/work per arm
```

Use a disjoint, hash-selected base-only residual-pair set as a fixed estimator
proxy: one residual supplies the stored code and another residual direction
plays the query-side operand. Report paired inner-product error, squared-L2
error, and bound coverage for every encoder arm. These are construction-data
diagnostics, not benchmark-query results, and the pair inventory/hash must be
frozen in the preregistration.

Use a scale-normalized opportunity fraction wherever the denominator is
well-defined:

```text
unrecovered_fraction =
  (error_factor_r6 - error_factor_exact) /
  (error_factor_init - error_factor_exact)
```

This gives a mechanism-level unit: the fraction of the available
initialization-to-exact improvement still left by production CAQ. Also report
unscaled distributions so the ratio cannot hide small denominators.

Aggregate with paired vector-level bootstrap intervals, stratified by dataset,
segment dimension/bit width, and rotation seed. Cluster and residual-norm
strata are descriptive only unless frozen in the preregistration.

### Decision Rule To Freeze In The Preregistration

The recommended minimum limitation threshold is:

```text
on the leading high-bit segment in both datasets,
the 95% lower confidence bound of mean unrecovered_fraction is >= 0.10,
the unscaled error-factor gap is positive with seed-consistent direction,
and the frozen base-only residual-pair estimator error improves in both
datasets with paired confidence intervals excluding zero.
```

`0.10` is a research-significance floor, not a learned model parameter: it
requires production CAQ to leave at least one tenth of the entire
LVQ-initialization-to-exact opportunity. Sensitivity at `0.05` and `0.20` must
be reported, but neither may replace the registered decision.

The gate also requires that the planned leading high-bit segment have a larger
normalized gap than (1) its same-vector uniform-`B=4` control, (2) lower-bit
planned segments, and (3) the whole-residual uniform-`B=4` control within each
dataset, with paired confidence intervals excluding zero where pairing is
defined. This tests the proposed SAQ-specific amplification; a uniform gap is
generic CAQ behavior already acknowledged by the paper.

### Gate Outcomes

`NO-GO` if any of the following holds:

- oracle parity fails;
- the `0.10` limitation condition fails in either dataset;
- high-bit segments do not show the registered amplification;
- the effect depends on one rotation seed or negligible denominators;
- local fixed-point adjustment closes the gap through ordinary extra rounds,
  making the result an `r` setting rather than a new mechanism;
- exact E-RaBitQ fallback is the only repair;
- a positive objective/error-factor gap does not improve the preregistered
  base-only residual-pair estimator proxy after codes are frozen.

`CONDITIONAL PASS` only establishes the limitation and authorizes:

1. a narrower primary-source/theory review of certificates for the discrete
   fractional cosine objective;
2. a preregistered base-only certificate-prediction study;
3. only after that, a frozen held-out-query evaluation of an already specified
   encoder.

It does not authorize a planner change, broad `r/B/D` sweep, learned query
policy, new index layout, or end-to-end system build.

## Method-Level Gate After CO-0, If Needed

Before query evaluation, a candidate certificate/repair would have to recover
at least half of the exact oracle gap while using at most twice the production
CAQ encoding work on the frozen base sample. These are build-side Pareto
screens, not final contribution claims. The method must retain:

```text
one global PCA/SAQ plan
one code per vector segment
the same serialized bit widths and factors
the same query estimator and search path
no query-trained trigger
```

If the only successful design stores an additional code/certificate or invokes
exact E-RaBitQ for a large fraction of vectors, return `NO-GO` and preserve the
oracle evidence as a limitation study.

## Branch And Artifact Decision

Do not implement `CO-0` on the current lossy-projection branch. If the user
authorizes the gate, create a fresh `saq-caq-optimality-analysis` branch from
`saq-correctness-base` and migrate only:

- this memo and the bounded source review/ledger;
- the necessary research constraints from `AGENTS.md` and `TASK.md`;
- minimal exact-label/statistical infrastructure only if directly reused.

Do not migrate the LP-0 projected-distance diagnostic, graph profiler, local
plans, planner variants, or old empirical scorers.

## Final Recommendation

The current new-direction status is:

```text
GO:    write and execute one source-validated, base-only CO-0 oracle gate
NO-GO: claim or implement a new CAQ method before that gate passes
```

If `CO-0` fails, the reviewed portfolio has no remaining evidence-backed SAQ
main direction. Record that conclusion instead of rescuing the gate with new
datasets, bit widths, segments, rounds, or thresholds.

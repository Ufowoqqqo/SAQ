# Physical Lossy Projection For SAQ: A Collision-First Research Proposal

## Status And Decision

This document opens an independent direction on branch
`saq-lossy-projection-analysis`.

```text
status: bounded related-work review complete for branch opening
registered experiment: LP-0 Gate A only
method/contribution status: unproven
```

The direction is a falsification study. ASH already combines learned
dimensionality reduction and scalar quantization at fixed payload; MRQ already
combines a quantized PCA head, tail statistics, and multi-stage refinement;
LeanVec already combines low-dimensional primary vectors with secondary
representations; DADE/ADSampling already cover projected progressive distance
computation. A simple "truncated PCA + SAQ" system is a composition, not a
paper contribution.

The governing rule is:

```text
First establish a physical-projection opportunity under original-space labels
and complete accounting. Then defeat the closest systems. Only after both may
a separate gate test an SAQ-specific joint projection/plan mechanism.
```

The detailed first protocol is
`docs/saq_lossy_projection_lp0_preregistration_2026_07_11.md`.

## Why This Is Independent Of The Closed PCA Study

The parent study asked whether a full-dimensional, L2-isometric basis should
replace current PCA for SAQ. Its external replication closed that premise.

This proposal changes the independent variable:

```text
closed direction: D -> D; exact L2 preserved; transform objective tested
new direction:    D -> d; projection error accepted; physical state/work tested
```

The parent result neither proves nor disproves a physical projection benefit.
It remains binding negative evidence: do not reopen full-D transform learning
or use lossy projection as a pretext to rerun that gate.

## Motivation

The current preprocessing script fixes `D_OUT = D_IN`. It materializes every
PCA output component, while SAQ reduces rate through heterogeneous segment
bits and a possible terminal 0-bit segment.

Physical `D -> d` materialization could reduce:

- dense query projection state and operations versus native full-D SAQ;
- transformed base and centroid state;
- positive suffix codes, factors, norms, and rotators;
- resident and serialized bytes;
- candidate arithmetic and memory traffic.

It also introduces projection error and may require tail metadata,
original-dimensional query-to-centroid norm work, or full-vector refinement.
An optimized logical head-only view can use the same sliced query operator as a
physical view, so gross savings versus native full-D SAQ are not automatically
incremental benefits of physical materialization.

The original SAQ paper already calls PCA tail discard dimension reduction and
presents SAQ as bridging reduction and balancing. The possible research gap is
therefore narrow: does physical `d` eventually need to be co-designed with
SAQ's heterogeneous progressive estimator, after existing projection systems
and logical controls are exhausted?

## Research Question And Hypotheses

Primary question:

```text
At matched deployable bytes and complete query work, can one base-only global
D -> d representation and one global SAQ plan improve the original-space
Recall-QPS-bytes frontier beyond native SAQ, its logical head/tail controls,
ASH, MRQ, LeanVec-ID, DADE/ADSampling, and uniform-bit projected quantization?
```

Potential SAQ-specific question, which LP-0 cannot yet answer:

```text
Are physical d, heterogeneous segment boundaries/bits, CAQ adjustment, and
progressive stages non-separable under an actual-byte/work objective?
```

Null explanations:

- `H0-projection`: the exact projected surrogate loses too much original-space
  ranking quality.
- `H0-equivalence`: the physical estimator is only an algebraically equivalent
  materialization of a logical head-plus-tail view.
- `H0-composition`: gains come from tail norms, uniform rate reallocation, or
  full-vector reranking.
- `H0-systems`: tail, operator, centroid, alignment, or refinement overhead
  removes the gross scan benefit.
- `H0-baseline`: ASH, MRQ/MRQ+, LeanVec-ID, or projected progressive controls
  match or dominate.

Only after these controls may a separately preregistered `H1-SAQ` test ask
whether a byte-matched projected SAQ plan yields a non-separable Pareto point.

## Scope And Architecture

Initial scope:

```text
metric: squared L2
index family: IVF
fit information: base/index data only
evaluation information: held-out queries only
projection: one dataset-level operator
quantization: one global SAQ plan
query state: one estimator/searcher state
format: unchanged during LP-0
```

Excluded initially:

- query-aware dimension, transform, plan, loss, or threshold selection;
- per-cluster projection matrices or SAQ plans;
- plan IDs and mixed dispatch;
- graph traversal;
- nonlinear encoders and learned Matryoshka embeddings;
- low-dimensional IVF rebuild before the offline gates.

Ordinary IVF centroids and assignments are allowed. Cluster-specific learned
projection state is not.

## Related Work And Novelty Boundary

The primary-source review and source metadata are:

- `docs/saq_lossy_projection_related_work_2026_07_11.md`;
- `docs/saq_lossy_projection_related_work_sources_2026_07_11.json`.

### ASH

[ASH](https://arxiv.org/abs/2606.07870) is the direct collision for the
fixed-payload tradeoff between uniform bitrate and its derived retained
dimension. It learns a row-orthonormal lower-dimensional representation and
scalar-quantizes database vectors. Its main formulation is inner
product/cosine. Its squared-L2 correction uses regression calibration sampled
from queries and indexed vectors; report that published query-calibrated form
only as an outside-scope reference and freeze a separate base-only calibration
for the admissible comparison. Its June 2026 v1 does not link an official
source artifact.

Consequences: neither a learned global projection nor "fewer dimensions with
more uniform bits" is new. ASH is mandatory before a fixed-payload
dimension-bitrate tradeoff claim.

### MRQ

[MRQ](https://www.vldb.org/pvldb/vol19/p1240-yang.pdf) is the direct collision
for a PCA head, per-vector tail norm, dataset-level residual variances, and
multi-stage IVF refinement. Its official
[RESQ artifact](https://github.com/mingyu-hkustgz/RESQ) exposes additional
configuration such as variance-count and bound parameters; freeze them from
base-only information rather than evaluation queries.

Consequences: a tail norm/variance, residual bound, or approximate/projected/
original refinement sequence is a baseline. Current SAQ's 0-bit residual
semantics already overlap MRQ's coarse norm-only approximation.

### LeanVec And GleanVec

[LeanVec](https://openreview.net/forum?id=wczqrpOrIc) combines projection and
quantization with primary and secondary representations. LeanVec-ID is the
query-unaware boundary, but its reported dimension selection uses query
performance; this branch must instead freeze a base-only rule. The public SVS
repository does not include the proprietary LeanVec/LVQ implementation, so
distinguish a reproducible truncated-PCA control from an official packaged
system result.

[GleanVec](https://arxiv.org/abs/2410.22347) covers locally adaptive
piecewise-linear projection. Its cluster-specific state violates the initial
one-global-projection architecture.

### Projected Progressive Distance

[DADE](https://www.vldb.org/pvldb/vol18/p812-zheng.pdf) estimates distance in a lower-
dimensional space and adaptively chooses projected work with a hypothesis test;
the same line compares PCA/data-aware and random-projection/ADSampling-style
distance operations and integrates them with IVF/HNSW. It occupies broad
claims around projected prefixes, probabilistic bounds, and original exact
fallback.

### Quantization Controls

OPQ is a classical learned full-D rotation control. TurboQuant is a modern
random-rotation scalar-quantization control whose residual correction concerns
quantization residual rather than discarded PCA tail. Neither is the physical
projection contribution, but both bound a later learned objective.

The narrowest hypothesis not directly covered by this bounded review is the
joint effect of physical `d` and SAQ's heterogeneous CAQ progressive plan. It
remains a hypothesis, not a novelty claim.

## Distance And Error Contract

For an IVF centroid `c`, split the common PCA residual coordinates at `d`:

```text
x-c = [x_h, x_t]
q-c = [q_h, q_t]
```

The original-space exact reference is always computed from raw vectors:

```text
D0 = ||x-q||^2
```

Two projected surrogates are controls:

```text
DP_none = ||x_h-q_h||^2

DP_norm = ||x_h-q_h||^2 + ||x_t||^2 + ||q_t||^2
```

`DP_norm` omits `-2<x_t,q_t>`. It is an SAQ 0-bit/MRQ-style control, not a new
correction.

Production tail metadata has finite precision, so add an explicit summary
stage:

```text
D0 = original-space float64 exact distance
DP = exact projected surrogate with exact float64 tail treatment
DS = exact projected head with deployed tail-summary precision
DQ = full projected-SAQ with deployed tail summary
DT = staged projected-SAQ with deployed tail summary

e_projection   = DP - D0
e_summary      = DS - DP
e_quantization = DQ - DS
e_staging      = DT - DQ
e_total        = DT - D0
```

Require the additive identity and report component covariance. An exact-tail
diagnostic may isolate head quantization but is not deployable.

## Systems Work And Space Model

Record rather than assume:

```text
query head projection
query-to-probed-centroid residual-tail norms
centroid routing
segment rotation and lookup preparation
candidate code/factor/norm bytes
staged and exact refinement
```

For an orthogonal head, a query tail norm can be derived as
`||q-c||^2 - ||P_d(q-c)||^2`, but `||q-c||^2` may require original-dimensional
work for each probed centroid. Count it and any retained full-D centroid state.

Deployable bytes include:

```text
codes + factors + norms + tail sidecar + padding/alignment + IDs/list state
+ amortized centroids + online operator/mean + rotators
+ secondary/full rerank representation
```

Report serialized, resident, amortized, and bytes-read components separately.
Nominal `B` is not an adequate denominator.

## Phase 0: Bounded Review And Repository Inventory

Status: complete for opening the branch.

Findings:

- current preprocessing is full-D;
- the 0-bit residual estimator is a mandatory equivalence control;
- SAQ accepts projected dimensions with 64-coordinate padding;
- the recovered historical PCA operator and q128 fixed replay can be frozen by
  content hash;
- canonical raw exact replay needs only a controlled lossy schema extension;
- sibling transform utilities are conceptually reusable but remain full-D;
- no local ASH, MRQ, LeanVec, or GleanVec implementation was found;
- the old non-SAQ PCA-prefix routine is not a completed lossy experiment.

## LP-0: Prerequisite Screen

LP-0 freezes GIST `D=960`, `d=576`, the first 128 queries, current K=512
assignments, q128/nprobe16 probes, and the retained first-three plan:

```text
0:64@11 | 64:256@6 | 256:576@4
```

The choice removes 40% of PCA output components and 512 code bits: 13.33% of
the nominal four-bit budget and 14.04% of the frozen plan's positive bits.

LP-0 has five roles:

1. validate frozen artifacts and common raw labels;
2. test the exact projected oracle against native full-D SAQ quality;
3. test frozen projected SAQ and the confirmatory `fast_all` stage;
4. require bit/ranking equivalence between physical and logical head-only
   estimators;
5. separate gross savings versus native SAQ from incremental materialization
   savings versus the equivalent logical view.

If incremental evidence is storage-only, label it storage-only. LP-0 cannot
establish the proposed plan interaction because the retained bits are frozen.

## Phase 1: Closest-Baseline Collision

Only after LP-0 passes:

1. reproduce or faithfully implement ASH with its published query-calibrated
   squared-L2 reference labeled outside scope and a separate base-only
   calibration used for the admissible comparison;
2. evaluate MRQ/MRQ+ with base-only frozen configuration;
3. separate LeanVec-ID's reproducible projection control from any official
   packaged system measurement;
4. include uniform-bit projected quantization and compatible DADE/ADSampling
   controls;
5. use a simultaneous paired-query comparison over the baseline envelope with
   complete deployable bytes and query work.

If the result is truncated PCA plus a norm, uniform rate reallocation, or an
interchangeable head quantizer inside an existing system, stop.

## Phase 2: SAQ Plan-Interaction Gate

Only if the closest-baseline envelope leaves a gap, write a new preregistration
before changing the plan. It must include:

- one base-only rule for selecting `d`;
- a byte-matched projected heterogeneous SAQ plan;
- a uniform-rate projected control;
- frozen actual-byte and work constraints;
- a factorial comparison that separates projection, plan, and progressive
  effects;
- no benchmark-query selection.

This is the earliest phase that can test the non-separable SAQ hypothesis.

## Phase 3: End-To-End IVF And External Replication

Only after the plan-interaction gate:

- rebuild projected IVF;
- time raw projection, routing, tail work, scan, staged refinement, and
  original-vector reranking;
- report original-space Recall-QPS-total-bytes curves;
- freeze the mechanism and selection rule before a second spectral regime;
- require replication across multiple practical budget/recall points.

## Strict-Reviewer Objection

The default objection is:

> This is ASH or truncated PCA for the head, MRQ for the tail/refinement, and
> SAQ plugged in as another quantizer. The physical/logical estimators are
> identical, so where is the new database mechanism?

The only possible answer requires evidence that:

1. LP-0 leaves a material physical systems opportunity;
2. closest systems do not explain it;
3. a separately preregistered byte-matched plan test shows a non-separable
   SAQ-specific interaction;
4. complete end-to-end gains replicate without query tuning.

If any point fails, do not propose a method.

## Stop Conditions

Stop if:

- the registered exact-oracle, projected-SAQ, progressive, or systems gate
  fails;
- logical and physical estimator outputs differ;
- incremental evidence is only storage materialization already covered by
  existing systems;
- tail summaries, uniform rate, or reranking explain the result;
- ASH, MRQ/MRQ+, LeanVec-ID, or projected progressive controls dominate;
- complete state/work removes the gain;
- query-aware/local state becomes necessary;
- the result fails external replication.

A stopped GIST gate means no evidence at the registered operating point, not
that lossy projection is universally ineffective.

## Immediate Deliverable

Implement LP-0 Gate A only: validate frozen hashes, prepare exact `d=576`
head/tail values, extend canonical replay to `raw_D != projected_d`, emit
`D0/DP/DS`, and decide the preregistered oracle screen. Do not build projected
SAQ, change the format, learn a projection, rebuild IVF, or sweep dimensions
before that decision.

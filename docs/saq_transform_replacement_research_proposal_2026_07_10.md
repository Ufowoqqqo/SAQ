# Beyond PCA in SAQ: Query-Unaware Transform-Plan Co-Design for Segmented Progressive Quantization

## Status And Decision

This document defines an independent, non-graph research direction starting
from `saq-correctness-base`. The first objective is to test whether PCA is an
actual SAQ limitation. It does not authorize a learned replacement before the
limitation survives simple controls.

**Outcome update:** Phase 1 found a small GIST estimator mismatch but no stable
ranking improvement. The preregistered CIFAR60k Phase 1b replication then
failed to reproduce the estimator effect and closed the direction. See
`saq_transform_phase1_limitation_evidence_2026_07_10.md` and
`saq_transform_phase1b_external_replication_evidence_2026_07_10.md`. The later
method phases below are retained as the original conditional design; they are
not authorized next steps.

The central decision is:

```text
First falsify the claimed PCA/SAQ mismatch.
Only then design a replacement.
```

Simple "replace PCA with module X" experiments are useful baselines but are not
a sufficient database-systems contribution.

## Motivation

The current preprocessing script trains a FAISS PCA transform with
`D_OUT = D_IN`. It therefore preserves the numerical dimension and, for L2,
acts as a centered orthogonal change of basis. Its important downstream roles
are to decorrelate coordinates, order them by decreasing variance, and expose a
low-variance tail to SAQ's segmented mixed-bit planner.

SAQ then chooses contiguous 64-dimensional segments and bit widths using a
variance proxy. Positive-bit segments can be independently randomized by
orthogonal rotations. A 0-bit tail does not disappear completely: the base
residual norm and query tail norm remain in the L2 estimate, while their inner
product is omitted.

These details create a specific research question. PCA is optimal for several
classical reconstruction and truncation objectives, but SAQ does not directly
optimize those objectives. It uses a mixed-bit CAQ angular estimator,
progressive prefixes, contiguous segment boundaries, tail omission, metadata,
and candidate-ranking decisions. The variance proxy may or may not align with
that actual system behavior.

## Research Question And Hypotheses

Primary research question:

```text
Does PCA's variance-only objective mismatch the measured error of SAQ's
segmented CAQ estimator and progressive prefixes, and can a base-only, single
global, full-dimensional orthogonal transform jointly with one global SAQ plan
improve rate-error-work and end-to-end Recall-QPS-bytes?
```

Null hypothesis `H0`:

```text
After controlling for residual statistics, coordinate order, plan changes,
and per-segment random rotations, PCA is already well matched to SAQ.
```

Limitation hypothesis `H1`:

```text
The planner's diagonal variance proxy systematically misranks segment/bit
choices relative to measured CAQ full-code or progressive-prefix error.
```

Method hypothesis `H2`, considered only if `H1` survives:

```text
A query-unaware global transform and global plan optimized for measured SAQ
estimator behavior can improve the matched-byte and complete-work Pareto
frontier beyond PCA and established rotation/projection baselines.
```

## Scope And Metric Contract

The primary study is deliberately narrow:

```text
distance: L2
index family: IVF
training information: base/index data only
evaluation information: held-out benchmark queries only
transform: one dataset-level full-D affine orthogonal operator
quantization: one global SAQ segment/bit plan
dispatch: one query-side transform/estimator state
format: no persisted-index change during the limitation study
```

For `T(x) = (x - mu) R`, with `R^T R = I`, applying the same transform to
base vectors, queries, and centroids preserves L2 distance and linear residual
structure. This is the primary drop-in contract.

The following are separate studies rather than equivalent replacements:

- `D -> d` projection is lossy and changes exact distances;
- whitening is not L2-isometric;
- nonlinear encoders do not preserve `T(x) - T(c) = T(x - c)`;
- mean-centered PCA does not preserve raw inner product without correction.

Consequently, the first study is L2-only and full dimensional. Lossy projection
is retained as a secondary diagnostic because it may reduce query preparation,
code work, and metadata, but it must be evaluated against original-space ground
truth.

## Repository Evidence Behind The Proposal

The proposal is grounded in the current implementation:

- `python/pca.py` sets `D_OUT = D_IN` and writes transformed base, query, and
  centroid files plus a variance vector.
- `saqlib/quantization/saq_data.hpp` optimizes a dynamic-programming cost using
  approximately `variance_sum / 2^bits`, with a possible 0-bit tail.
- `saqlib/defines.hpp` fixes the segmentation granularity at 64 dimensions.
- `saqlib/quantization/quantizer_data.hpp` can create a separate random
  orthogonal rotator for every segment.
- `saqlib/quantization/caq/caq_encoder.hpp` retains residual norms, and
  `caq_estimator.hpp` estimates a 0-bit L2 segment as base-norm squared plus
  query-norm squared, omitting only the cross inner product.
- `src/test_relative_error.cpp` can use transformed vectors as its exact
  reference, so a lossy projection would require an explicit original-space
  decomposition rather than reuse of that result alone.
- `src/define_options.h` treats PCA as a file-suffix choice rather than a
  general transform abstraction.

These facts imply that the outer transform can affect contiguous subspace
assignment, energy ordering, plan shape, and progressive work. Its
within-segment orientation may be neutralized by the inner rotations and must
be ablated.

## Related Work And Novelty Boundary

The broad idea of transform-plus-quantization is established:

- Classical [transform coding with bit allocation](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/0557.pdf)
  already combines PCA-like transforms, nonuniform rate allocation, and dropped
  dimensions.
- [ITQ](https://slazebni.cs.illinois.edu/publications/cvpr11_small_code.pdf)
  and [OPQ](https://openaccess.thecvf.com/content_cvpr_2013/html/Ge_Optimized_Product_Quantization_2013_CVPR_paper.html)
  establish learned orthogonal rotations for quantization objectives.
- [LeanVec](https://arxiv.org/abs/2312.16335) combines linear dimensionality
  reduction with quantized vector search; its ID setting is a direct baseline
  for query-unaware PCA truncation.
- [GleanVec](https://arxiv.org/abs/2410.22347) studies cluster-specific
  piecewise-linear projections, but its local transform state conflicts with
  this branch's one-global-transform architecture.
- [Quantization Meets Projection / MRQ](https://www.vldb.org/pvldb/vol19/p1240-yang.pdf)
  is the closest collision for a quantized PCA head plus tail norm/variance and
  staged refinement in IVF.
- [TurboQuant](https://arxiv.org/abs/2504.19874) is a relevant modern control
  for fast randomized transforms and quantization-oriented search.

Therefore, none of the following is a novel contribution on its own:

```text
truncated PCA + SAQ
random projection + SAQ
FHT/random rotation + SAQ
OPQ matrix + SAQ
PCA head + compact tail norm/variance
```

The only currently plausible novelty claim is SAQ-specific: demonstrate that
PCA's variance objective is mismatched with the segmented mixed-bit CAQ prefix
estimator, then optimize a base-only global transform and one global plan for
that measured mechanism under actual bytes and complete query work.

## Candidate Hierarchy

### Tier 1: Required Controls

- current raw-data full-D PCA;
- identity/raw coordinate order;
- identity plus base-variance coordinate permutation;
- global PCA on IVF residuals rather than raw vectors;
- seeded random full-D orthogonal transform;
- seeded random orthogonal transform followed by variance sorting;
- FHT-style mixing plus a deterministic variance permutation;
- PCA-coordinate reversal or controlled permutations.

These controls determine whether any result comes from decorrelation, residual
statistics, coordinate ordering, or generic mixing.

### Tier 2: Strong Learned Baselines

- ITQ/OPQ-style global orthogonal rotation followed by the unchanged SAQ
  planner;
- the same rotation with a frozen PCA plan;
- a candidate SAQ-aware global rotation, but only after the limitation gate.

### Tier 3: Explicitly Lossy Baselines

- truncated PCA;
- Gaussian or sparse random projection;
- LeanVec-ID;
- MRQ or the closest reproducible MRQ-style head/tail configuration.

Lossy baselines answer a distinct systems question and cannot be mixed into the
full-D isometric claim.

## Research Plan

### Phase 0: Reproducible Offline Transform Views

Create only the minimum artifact contract needed for fair offline comparison:

```text
TransformTrainer.fit(base_only, seed) -> TransformState
TransformState.apply(base/query/centroids) -> transformed views

views/<transform-id>/
  base.fvecs
  query.fvecs
  centroid_K.fvecs
  variance.fvecs
  operator.npz
  manifest.json
```

The manifest records:

- input, output, and padded dimensions;
- metric contract such as `l2_exact` or `lossy_projection`;
- mean, operator, coordinate permutation, and seed;
- fit rows and hashes plus output shapes/hashes;
- orthogonality error and off-diagonal covariance ratio;
- operator/model bytes, fit time, batch apply time, and raw-query latency.

Reuse ideas selectively from the sibling repository's
`scripts/pca_transform_fvecs.py`,
`scripts/random_orthogonal_transform_fvecs.py`, and
`scripts/transform_manifest.py`. Extend provenance as needed, but do not modify
the sibling repository without authorization. Do not change the SAQ persisted
index format in this phase.

### Phase 1: Minimal Limitation Falsification

Start with one small, fixed operating point:

```text
dataset: gist_sample50k
IVF K: 512
nominal B: 4
block-min mode: 2
candidate lists: identical across transform comparisons
transforms: current PCA, residual PCA, identity, seeded random orthogonal
```

For every transform, compare:

1. the planner's segment variance proxy;
2. measured CAQ error by segment and bit width;
3. measured full-estimator distance/ranking error;
4. progressive-prefix distance/ranking error;
5. the native transform-specific plan, a frozen PCA plan, and a uniform or
   no-segmentation CAQ control where meaningful.

Report fixed-candidate top-k agreement, boundary-pair flip rate, exact-best
rank, error bias, relative/absolute-error p50/p90/p99, prefix error versus bytes
read, false negatives, plan shape, bytes per candidate, and cycles or time per
candidate.

A useful diagnostic is the agreement between proxy-predicted plan preference
and empirically measured CAQ/prefix preference. A new learner is not justified
if disagreement is small, unstable across seeds, or explained by the simple
controls.

### Phase 2: Full-D Transform Comparison

Proceed only if Phase 1 identifies a stable mismatch. Add the remaining Tier 1
controls and strong rotation baselines. Predeclare segment-rotation seeds
`0..9` and report query-level paired bootstrap 95% confidence intervals.

Required ablations:

- internal segment rotation: default, fixed seed, and off;
- CAQ adjustment rounds: zero, default, and a near-converged diagnostic;
- transform only, plan only, and joint transform-plus-plan;
- raw-data PCA versus IVF-residual PCA;
- native plan versus frozen PCA plan.

The result must survive these controls before it can be interpreted as an outer
transform effect.

### Phase 3: Lossy `D -> d` Error Decomposition

Treat physical projection as a separate secondary study. For the existing GIST
PCA plan, predeclare dimensions at plan boundaries:

```text
d in {64, 256, 576, 832, 960}
```

For each fixed query-candidate pair compute:

```text
D0 = original exact distance
DP = projected exact distance plus the chosen tail approximation
DQ = full-SAQ projected-head distance with an exact-tail diagnostic
DT = projected staged/full-SAQ distance plus the chosen tail approximation
```

Decompose:

```text
projection error    = DP - D0
quantization error  = DQ - D0
total error         = DT - D0
```

Also report the covariance between projection and quantization error; apparent
total-error gains may otherwise come from cancellation. Keep candidate lists
and original ground truth fixed. Rebuild IVF in the projected space only after
this gate passes.

### Phase 4: Conditional SAQ-Aware Method

Only after positive limitation evidence, learn a single global full-D
orthogonal transform jointly with one global segment/bit plan. Initialize from
PCA. Use only base data and a disjoint base validation split. Optimize a loss
that approximates measured CAQ full-code and prefix estimator behavior under an
actual-byte constraint.

The method must not require benchmark queries, per-cluster matrices, transform
ids, local plans, or mixed search dispatch. Every hyperparameter needs a
mechanism-level rationale, unit/scale, fixed selection rule, and sensitivity or
ablation plan.

### Phase 5: End-To-End IVF Validation

If the method passes offline gates, evaluate complete IVF search on datasets
with different dimensions and spectra, including GIST and at least two of DEEP,
MSMARCO, or an OpenAI high-dimensional dataset. Predeclare multiple `B`, `K`,
and `nprobe` operating points.

Report Recall@k-QPS-actual-bytes Pareto frontiers. Include raw-query transform,
query preparation, candidate scoring, progressive reads, and exact refinement
in the query time. Do not time only pretransformed-query scanning.

## Fair Budget And Work Accounting

Nominal `B` is not a complete space budget. Use actual serialized bytes per
vector:

```text
bytes/vector =
    packed short and long codes
  + short and long factors
  + tail summaries
  + alignment and padding
  + amortized centroids and global transform state
  + amortized segment rotators
```

If raw vectors are retained for reranking, count them consistently for all
methods. Also report transform matrix bytes separately because dense query
projection has `O(D^2)` work for a full-D operator and `O(Dd)` for a projected
operator. Segment rotations may be composed with the outer operator for query
preparation, but the resulting online work and memory traffic still count.

Complete query work includes:

```text
raw-query transform
query norm and tail-summary preparation
SAQ per-segment lookup preparation
code and factor bytes read
candidate estimates and progressive refinements
exact projected/full-vector reranking
```

## Expected Contribution, Conditional On Evidence

A viable paper would need all four components:

1. empirical and analytical evidence that PCA's variance objective mismatches
   actual segmented CAQ or prefix-estimator behavior;
2. a base-only, one-global-transform and one-global-plan objective specific to
   SAQ rather than generic reconstruction distortion;
3. a theoretical connection between the proposed loss and estimator variance,
   boundary ranking error, or rate-work behavior;
4. end-to-end IVF Recall-QPS-memory gains after all transform and metadata
   overhead is included.

If experiments only show that a different off-the-shelf transform sometimes
improves one setting, report it as a sensitivity or negative study rather than
as a new method.

## Strict-Reviewer Objections And Required Answers

1. **Is this just OPQ or ITQ plugged into SAQ?** Compare directly and identify
   the SAQ-specific loss and mechanism.
2. **Why does classical PCA/KLT optimality not settle the problem?** Show that
   the target is CAQ prefix ranking and actual rate/work, not only Gaussian
   reconstruction MSE.
3. **Would residual PCA or a simple coordinate permutation obtain the gain?**
   Include both controls.
4. **Do SAQ's per-segment random rotations erase the outer transform?** Perform
   default/fixed/off ablations across predeclared seeds.
5. **Is the lossy result merely MRQ?** Treat MRQ and truncated PCA plus tail
   summaries as direct baselines and keep lossy claims separate.
6. **Were queries used to tune the method?** Preserve manifests and selection
   logs demonstrating base-only fitting and fixed choices before evaluation.
7. **Does query transformation erase scan savings?** Include raw-query latency
   and complete query work.
8. **Are methods actually matched in space?** Report serialized bytes including
   factors, padding, operator state, and metadata.
9. **Does estimator RMSE translate into a database result?** Report boundary
   ranking, fixed-candidate recall, and end-to-end Recall-QPS-bytes.

## Stop Conditions

Stop the direction if any condition holds:

- the variance proxy already predicts measured CAQ and prefix error;
- residual PCA, a permutation, random/FHT mixing, or OPQ explains all gains;
- internal per-segment rotations erase the effect;
- the best lossy result is PCA truncation plus a tail norm/variance, overlapping
  MRQ without a distinct mechanism;
- projection error dominates or only changes the exact neighbor problem;
- benchmark queries are required to choose `d`, the loss, or a threshold;
- a method needs per-cluster transform/plan state or mixed dispatch;
- operator, metadata, or query-preparation overhead removes the QPS benefit;
- fixed-candidate gains do not transfer to end-to-end IVF;
- results are limited to one dataset or one `B`, are seed-sensitive, or are too
  small/noisy to support a mechanism claim.

A negative Phase 1 result is a useful conclusion: full-D PCA and current SAQ
may already be well matched. Record that evidence and stop before building a
new learner.

## Immediate Deliverable

The next deliverable is the Phase 1 protocol and measurement, not a replacement
module. It should reproduce current PCA, residual PCA, identity, and a seeded
random orthogonal control under fixed IVF candidates, then decide the
continue/stop gate using measured CAQ and prefix errors with complete budget
accounting.

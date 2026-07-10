# SAQ Transform Phase 1b: Preregistered External Replication Gate

## Status

This protocol is frozen before inspecting any `cifar60k` query outcome in this
branch.  Its first Git commit is the preregistration record.  Later corrections
must be appended as explicitly dated amendments; endpoints, signs, or stop
rules must not be silently changed after evaluation starts.

Phase 1b is a closure replication of the narrow GIST result.  It is not a new
transform sweep and does not authorize a learned transform.

## Question And Prior Result

Phase 1 found that residual PCA, relative to SAQ's current raw-data PCA, reduced
distance-estimator RMSE at the first accurate prefix and at full code under a
matched plan and matched serialized bytes.  The signal did not establish a
ranking improvement and the fast stage worsened.

Phase 1b asks only:

```text
Does that narrow residual-PCA estimator effect replicate, without plan,
candidate-set, exact-reference, byte, or internal-rotation confounding, on one
preselected external dataset with a different dimension and spectrum?
```

The null result is decisive for this branch: a failure closes PCA replacement
as a dataset-specific observation.  A positive result remains evidence of a
limitation, not a contribution.

## Frozen Dataset And Inputs

| Item | Frozen value |
|---|---|
| Dataset | `cifar60k` |
| Metric | squared L2 |
| Base | 60,000 x 512 float32 |
| Queries | all 1,000 x 512 held-out queries |
| Base SHA-256 | `a7170faaa80a072cd603ed472104049ead87fbaff224e94a529021d161f8aea4` |
| Query SHA-256 | `88109c80b4f4d779440422df89eb9242c23d8cd4021682782294c50c57cca6d7` |
| Supplied GT SHA-256 | `28900a95d593c7d70bb9cfafb78be395d5ebade7bfffbbd8327e8ffa23ab336d7` |

The supplied ground truth is only an input cross-check.  Fixed-candidate exact
labels are recomputed from the canonical raw float32 base/query pair.

The dataset was selected without using query outcomes: it is external to the
GIST Phase 1 sample, has a different dimension, remains high-dimensional, its
dimension is an exact multiple of SAQ's 64-dimensional block, and its size
makes a complete 1,000-query replication practical.  Base-only spectrum
statistics may characterize the new regime but must not be used to replace the
dataset or change this protocol.

## Frozen Construction

```text
IVF clusters K                 512
historical clustering input    all 60,000 base rows, first 64 current-PCA coordinates
historical k-means iterations  4
historical k-means seed        0
historical empty clusters      0
nominal SAQ budget B           4 bits/dimension
probes per query               16
fixed-candidate top-k          100
evaluation queries             all 1,000, evaluation only
internal rotation controls     logical seeds 0..9 and off
logical-to-C seed mapping      0..9 -> 1..10
bootstrap                      query-paired percentile, 10,000 replicates
bootstrap global seed          20260710
```

Phase 1b reuses the locally materialized, query-unaware CIFAR codebook and
assignments whose summary records the settings above.  The historical
clustering used the first 64 current-PCA coordinates, while its stored
centroids are full 512-dimensional cluster means.  The operator is validated
before the full centroids are mapped back to one canonical raw-space codebook.
This PCA-prefix clustering is a limitation of the fixed candidate distribution,
but not a transform-arm confound: the recovered full-D codebook, assignments,
raw-space probe lists, and candidates are frozen and identical for both arms.
No claim about IVF partition quality is made.  The source summary and all input
artifact hashes must be copied into the generated manifest because `/tmp`
storage is not durable.

Only two base-only, global, full-dimensional affine orthogonal views are in
scope:

1. `current_pca`: PCA of centered raw base vectors;
2. `residual_pca`: PCA of raw IVF residuals around the one fixed codebook.

The only plan is the current-PCA variance plan derived at `B=4`, frozen and
applied byte-for-byte to both views.  No native residual plan, uniform plan,
identity, random rotation, alternative budget, alternative `K`, or threshold
is evaluated.  If the frozen plan has fewer than two segments and therefore no
`accurate_prefix_1`, the registered mechanism is not testable at this operating
point: report that fact and stop without substituting another prefix or plan.

The normal matrix is therefore:

```text
2 transforms x (10 paired internal-rotation seeds + rotation off) = 22 configs
```

`off` is a mechanism-support control.  It is not pooled with normal SAQ seeds.

## Canonical Exact And Replay Contract

All transform configurations must use the same canonical exact reference:

```text
exact(q, x) = sum_j (float64(raw_q[j]) - float64(raw_x[j]))^2
```

Candidate exact order uses `(exact distance, base id)` as its deterministic tie
break.  Transform-view distances must not serve as exact labels.  The common
raw base/query hashes, fixed probes, per-query candidate counts, exact-best
IDs, and exact top-100 IDs must be inventoried so the two runs can be checked
for identity.

The replay uses production packed/FastScan estimators on the fixed candidates
and reports the conservative variance stage, every fast prefix, `fast_all`,
every accurate prefix, and `full`.  Search pruning and block-min decisions are
bypassed, so safe block-min mode is not applicable.  All stages remain visible,
but the confirmatory endpoints are frozen before evaluation:

```text
fast_all             no-harm endpoint
accurate_prefix_1    primary mechanism and ranking endpoint
full                 confirmatory estimator endpoint
```

For each stage report equal-query mean of per-query RMSE, candidate-pooled RMSE
reconstructed from query SSE/count, MAE, bias, relative-error quantiles,
fixed-candidate top-100 agreement, exact-best estimated rank, strict exact
top-100-versus-outside boundary inversions, and logical bytes.  Report actual
serialized index bytes for every configuration.

Inference first averages the ten paired rotation seeds within each query, then
resamples queries.  Candidates and rotation seeds are not independent samples.
Also report the sign for each of the ten paired seeds.  Rotation-off is reported
separately.

## Artifact Gate

No scientific gate is interpreted unless all of these checks pass:

- input hashes, shapes, and finite-value checks match the frozen contract;
- both outer operators are full-dimensional and have relative L2 isometry
  error at most `1e-5`;
- both transforms use identical raw codebook, cluster assignments, probes,
  candidate IDs, candidate counts, exact-best IDs, and exact top-100 IDs;
- every query has at least 100 fixed candidates;
- the plan string is identical in all 22 configurations;
- within each paired rotation mode, serialized index bytes are identical;
- both outer operators have identical runtime state shape and bytes;
- every query-stage and segment output is finite.

Failure is an invalid replication, not evidence for or against PCA.

## Preregistered Decision Gate

All deltas are `residual_pca - current_pca`.  Lower is better for RMSE and
boundary inversions; higher is better for top-100 agreement.

### Gate A: Narrow estimator replication

Gate A passes only if all conditions hold:

- at both `accurate_prefix_1` and `full`, the paired 95% confidence intervals
  for both mean-query RMSE delta and pooled-RMSE delta are wholly below zero;
- at each of those two stages, at least 8 of 10 paired rotation-seed RMSE
  deltas are below zero;
- rotation-off mean-query RMSE is directionally below zero at both stages.

No other prefix can replace a failed confirmatory endpoint.

### Gate B: Practical ranking evidence

Gate B is examined only if Gate A passes.  It passes only if:

- at `accurate_prefix_1`, the paired 95% confidence interval for boundary
  inversion delta is wholly below zero; and
- at least 8 of 10 paired rotation-seed boundary-inversion deltas are below
  zero; and
- the `accurate_prefix_1` top-100 agreement point estimate does not decrease.

Boundary inversion is the single primary ranking endpoint.  Top-100 agreement
is a key secondary no-harm check, not an alternative endpoint.

### Gate C: Progressive no-harm

Gate C is examined only if Gates A and B pass.  At `fast_all`, neither RMSE
estimand, boundary inversion, nor top-100 agreement may have a confidence
interval showing significant degradation.  At `full`, boundary inversion and
top-100 agreement must likewise show no significant degradation.

## Decision Table

| Outcome | Decision |
|---|---|
| Artifact gate fails | Repair or report invalid replication; make no scientific claim |
| Gate A fails | Close PCA replacement as a one-dataset estimator effect |
| Gate A passes, Gate B fails | Confirm the narrow estimator mismatch but close PCA replacement because ranking evidence is absent |
| Gates A and B pass, Gate C fails | Record a stage tradeoff and close a global replacement direction |
| Gates A, B, and C pass | Permit one base-only counterfactual `(segment, bit)` mechanism analysis; do not authorize a learner or end-to-end claim |

The maximum positive consequence is deliberately small.  Phase 1b cannot by
itself justify a learned transform, a persisted-format change, or a
Recall-QPS claim.

## Overhead Boundary

Both alternatives retain one dense `(D x D)` float32 operator and one float32
mean: `1,050,624` runtime-state bytes at `D=512`, and approximately `D^2`
multiply-accumulates per raw query.  Record PCA/residual-PCA fitting time,
materialization time, operator bytes, and actual serialized index bytes.
Timings are provenance only: the fixed-candidate gate makes no QPS claim.

Residual PCA adds an offline residual-covariance fit, but no online state or
dispatch beyond current PCA.  Any unequal runtime state or paired index bytes
invalidates the matched-overhead comparison.

## Reviewer Interpretation

This design fixes the dataset, queries, operating point, candidate set, plan,
stages, signs, inference unit, and stop decision before query evaluation.  The
canonical raw exact reference removes transform-view roundoff as a label
confound; paired internal rotations remove seed confounding; the frozen plan
and actual bytes isolate the outer transform; and all 1,000 held-out queries
increase ranking power without training on query labels.

Residual PCA is an established control.  Even complete passage of this gate
would identify a repeatable SAQ-specific limitation only; novelty would still
require a separate related-work review and a mechanism that standard controls
do not already explain.

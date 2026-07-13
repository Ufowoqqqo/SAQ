# Attempt 3: Distance-Quality Re-evaluation -- Related Work And Novelty Gate

Date: 2026-07-13

## Decision

```text
FINAL: CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE
```

The original review decision was `CONDITIONAL_GO_FOR_EVALUATION_ONLY`. A3-0
through A3-3 are now complete. GIST supplies one metric-sensitive operating
point, while DEEP B4/B5 preserve their negative-control decisions. The
cross-dataset positive-reproduction and mechanism gates do not pass. See
`docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md`.

Attempt 3 may implement a paper-exact `1/Ratio@k` evaluator and use it to
re-evaluate a small, frozen set of earlier outcomes. This decision does not
authorize a new SAQ method, a metric-aware optimizer, benchmark-query fitting,
or the reopening of an earlier direction.

The stage passes only if it establishes whether the evaluation metric changes
the scientific interpretation of an existing comparison. The metric itself is
prior work and cannot be claimed as this project's contribution.

## Problem

Recall@`k` counts identifier overlap with the exact top-`k` set. When many
vectors have nearly equal distances near rank `k`, replacing one exact
identifier with a geometrically equivalent vector can reduce Recall even when
the returned set has nearly unchanged distance quality.

For query `q`, let

- `d_i(q)` be the Euclidean distance to the `i`-th exact neighbor after sorting
  the exact top-`k` by true distance;
- `d_tilde_i(q)` be the Euclidean distance to the `i`-th returned vector after
  sorting the returned set by true distance.

The paper defines

```text
Ratio@k(q) = (1/k) * sum_{i=1}^k d_tilde_i(q) / d_i(q)

1/Ratio@k(q) = k / sum_{i=1}^k d_tilde_i(q) / d_i(q)
```

Each position-wise ratio is at least one, so `1/Ratio@k(q)` lies in `(0, 1]`.
Unlike Recall, it does not require returned identifiers to match exact
identifiers when their distances are equivalent.

### Running example

For `k=3`, suppose the exact distances are

```text
d = [1.00, 1.10, 1.20]
```

and the returned identifiers overlap the exact set only once, but their true
distances are

```text
d_tilde = [1.00, 1.11, 1.21].
```

Then Recall@3 is `1/3`, while

```text
1/Ratio@3
  = 3 / (1.00/1.00 + 1.11/1.10 + 1.21/1.20)
  = 0.9945.
```

The two metrics answer different questions: exact-identifier recovery versus
geometric quality of the returned set.

## Closest Primary Work

### ANN Search: Recall What Matters

Dimitropoulos and Mamoulis propose `1/Ratio@k` as a judge-free,
hyperparameter-free metric computable from standard ANN benchmark inputs. The
paper compares Annoy, SuCo, HNSW, RaBitQ, and SymphonyQG on six datasets and
evaluates query time, distance computations, build time, memory, classification,
and RAG quality.

At quality threshold `0.95` and `k=100`, the paper reports that satisfying
Recall requires, on average, `9.36x`, `2.48x`, `2.38x`, `1.86x`, and `3.22x`
more distance computations than satisfying `1/Ratio` for HNSW, RaBitQ,
SymphonyQG, SuCo, and Annoy, respectively. On GIST, RaBitQ and SymphonyQG
obtain `4.49x` and `5.27x` QPS differences between the operating points needed
to reach the two quality thresholds.

The paper also reports the main warning for this project: changing the metric
usually changes the absolute cost required to reach a quality threshold, but
the relative algorithm ranking remains largely unchanged. Attempt 3 therefore
cannot assume that a previously inferior SAQ variant becomes superior.

### Other Critiques Of Recall

| Work | What it measures | Distinction from `1/Ratio@k` |
|---|---|---|
| Semantic Recall / Tolerant Recall | semantic relevance or distance-tolerant matches | Semantic Recall requires relevance judgments; Tolerant Recall introduces a tolerance |
| Iceberg | downstream task quality across realistic vector-search applications | requires task labels and application-specific evaluation |
| Robustness-`delta`@K | fraction of queries whose Recall exceeds a floor `delta` | retains identifier Recall and introduces `delta` |
| DARTH | adaptive early termination for a declared Recall target | changes search execution; it does not replace Recall with a distance-quality metric |

These works already occupy the claims that Recall can be misaligned with
downstream utility, that query-level means can hide difficult queries, and
that search effort can be controlled by a target quality level.

## What Attempt 3 Can Add

The bounded contribution of this stage is retrospective scientific
clarification:

1. implement the paper's exact metric in the SAQ evaluation environment;
2. identify which earlier conclusions are invariant to the metric;
3. identify any comparison whose Pareto order changes under distance quality;
4. distinguish geometric-quality failures from exact-identifier-boundary
   failures; and
5. report both metrics rather than replacing Recall.

This can improve the validity of the project and determine whether a later
method question exists. It is not yet a database-systems method contribution.

## Earlier Directions Worth Re-evaluating

### Highest priority: one-global-plan GIST sample comparison

The fac-error global plan on `gist_sample100k`, `K=512`, `B=4`, changed the
measured operating point from

```text
default:   nprobe=200, R@100=0.99132, QPS= 9215.208
fac-error: nprobe=200, R@100=0.99059, QPS=12334.000
```

Increasing `nprobe` did not recover the default Recall before losing the speed
advantage. The Recall difference is small enough that a distance-quality
metric may distinguish an identifier-boundary change from a material geometric
loss. Both default and custom plans must be evaluated across the same `nprobe`
grid; evaluating only the custom plan at one operating point would be invalid.

### High priority negative control: DEEP rejected local plans

The fixed-policy study rejected DEEP candidates despite positive QPS because
Recall decreased by approximately `0.02757` and `0.01429` at `B=4` and `B=5`.
These larger losses test whether `1/Ratio` merely makes every faster setting
look acceptable or can preserve meaningful negative controls.

### Medium priority: exact-hist scalar DP

Exact-hist scalar DP lowered weighted histogram SSE but sometimes reduced
Recall relative to Lloyd. `1/Ratio` can determine whether those reversals are
identifier-sensitive or reflect worse returned distances. This remains a
baseline/objective-mismatch analysis, because optimal 1D scalar quantization
is established work.

### Medium priority: lossy projection oracle

The `D -> d` projection study found high top-100 agreement for an exact
head-plus-tail-norm oracle but lower agreement than native full-dimensional
SAQ. A distance-quality metric may show whether the remaining disagreement is
geometrically small. However, no real projected index/QPS implementation was
completed, and the direction still collides with established reduced-dimension
ANN methods. This is not the first execution target.

## Directions Not Reopened By A Metric Change

The following failures are caused by method overhead, missing signal, or lack
of novelty rather than Recall semantics:

- residual-PCA replication failure outside GIST;
- mixed local-plan dispatch and estimator overhead;
- static segment-cost plans that reduced a proxy but were slower end to end;
- graph-prefix estimators with `26.8x--52.5x` work amplification;
- exact and one-shell CAQ encoding costs (`272.9x` and `4.579x--8.169x`);
- inactive or ineffective safe bounds and search schedules.

Attempt 3 must not use `1/Ratio` as a reason to resume these directions.

## Strict-Reviewer Assessment

The strongest objection is:

```text
The new metric is prior work, and its authors already show that it usually
does not change algorithm rankings. Replotting old SAQ results under this
metric is evaluation maintenance, not a method contribution.
```

The response is deliberately limited: this stage is a falsification study,
not the proposed paper contribution. A later method review is justified only
if a frozen comparison exhibits a stable Pareto-order change and the mechanism
is meaningful for at least two independent strong baselines.

## Gate

Proceed with an evaluator and the frozen protocol in
`docs/saq_attempt3_ratio_metric_protocol_2026_07_13.md`.

After the first retrospective matrix:

```text
GO_TO_MECHANISM_REVIEW only if:
  - at least one prior conclusion changes under paper-exact 1/Ratio;
  - the change is stable across a full operating-point curve;
  - it is reproduced on at least two datasets or two independent baselines;
  - query-level tails do not reveal hidden material failures; and
  - a mechanism-level question remains after accounting for prior work.

otherwise:
  CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE.
```

## Sources

The bounded source ledger is
`docs/saq_attempt3_ratio_metric_sources_2026_07_13.json`.

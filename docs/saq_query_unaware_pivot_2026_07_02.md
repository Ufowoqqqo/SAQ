# SAQ Query-Unaware Pivot Note

Date: 2026-07-02

Related notes:

```text
docs/saq_paper_code_alignment_2026_07_02.md
docs/saq_segment_diagnostic_2026_07_02.md
docs/saq_gist_higher_dim_segment_diagnostic_2026_07_02.md
```

This note records the advisor feedback after the SAQ pivot:

```text
Query-aware or workload-aware indexing is not a good primary scenario for the
next step. The follow-up should preferably be query-unaware.
```

The practical consequence is important. The previous `vectordb` rank-boundary
idea remains useful as a diagnostic lens, but it should not define the main SAQ
method. A strong follow-up should avoid assuming that a representative query
workload is available at index-build time.

## 1. Revised Research Boundary

Use only data available in a normal offline index build:

```text
base vectors
PCA projection and variances
IVF centroids and cluster ids
cluster residuals
quantization plans and index metadata
```

Do not use query workload samples to learn the index-time bit allocation or
segment boundaries. Standard held-out queries are still valid for final
evaluation, e.g. Recall@10, Recall@100, relative error, and QPS. The distinction
is:

```text
Allowed for method design: base/index statistics.
Allowed for evaluation: held-out benchmark queries.
Diagnostic only: rank-boundary or workload-aware weights.
```

## 2. What Carries Over From The Previous Exploration

The useful lesson from the earlier project is not "use queries during indexing".
The useful lesson is:

```text
variance/reconstruction error and nearest-neighbor ranking quality can disagree.
```

For SAQ, this suggests an audit question that can be stated without query-aware
indexing:

```text
Does SAQ's global PCA-variance segment plan miss data-only structure that is
important for approximate nearest-neighbor quality?
```

Examples of data-only structure include:

- cluster-local residual covariance that differs from global PCA variance;
- heavy-tailed or high-error dimensions hidden inside long contiguous segments;
- local neighbor boundary instability measured with base vectors as pseudo
  queries, excluding the vector itself;
- segment granularity limits caused by padding, SIMD alignment, or fixed
  contiguous PCA blocks.

## 3. Revised Primary Hypothesis

SAQ's dynamic plan optimizes a global contiguous PCA segment objective close to:

```text
cost(segment, b) = variance_sum(segment) / 2^b
```

This is a strong and simple data-only objective, but the implementation then
uses the same global plan for IVF cluster residuals. The main query-unaware
hypothesis is:

```text
A global variance-driven segment plan may be mismatched to local residual
structure, within-segment concentration, or base-neighbor boundary stability,
even when no query workload is used during indexing.
```

This keeps the novelty search inside SAQ's own assumptions instead of moving to
a workload-specific setting.

## 4. Priority Order After The Pivot

### P0: Query-Unaware SAQ Limitation Audit

First measure whether SAQ's default plan agrees with data-only diagnostics:

```text
SAQ allocated bits per segment
global PCA variance per segment
cluster-local residual variance per segment
within-segment variance concentration
optional base-as-pseudo-query boundary diagnostics
```

A positive signal is a consistent mismatch, for example:

```text
A segment has modest global PCA variance but high local residual variance in
many IVF clusters, while SAQ assigns it few bits or discards it.
```

A negative signal is also useful:

```text
Global PCA variance, cluster-local residual variance, and base-neighbor boundary
risk all rank segments almost identically.
```

If the negative signal holds across datasets, this line should stop early.

### P1: Flexible Segmentation Under Data-Only Signals

If the audit shows that default contiguous PCA segments are too coarse, compare:

```text
default SAQ segmentation
equal segmentation via -seg_eqseg
data-only segmentation based on variance concentration or local residual risk
```

The goal is not to add query-aware weights. The goal is to test whether SAQ's
fixed segment shape leaves value on the table even under query-unaware signals.

### P2: Local Or Cluster-Aware SAQ Plans

SAQ's IVF path quantizes each cluster with the same global segment plan. A more
system-aligned follow-up is:

```text
learn a small number of local SAQ plans from cluster residual statistics, then
share those plans across clusters to control metadata overhead.
```

This is query-unaware and directly tied to the SAQ implementation. The main
engineering risk is plan metadata and training complexity.

### P3: SAQ + Graph-Based ANNS

Graph search remains a strong later systems direction because SAQ's progressive
estimator could support early pruning during graph traversal. It should wait
until the reproduction and query-unaware SAQ diagnostics are stable.

## 5. Immediate Experiment

Use the existing `audio` quant-plan probe only as plumbing validation:

```text
B=1: 0 -> 64 (64d 3b); 64 -> 192 (128d 0b)
```

For `audio` at B=2/4/8, default SAQ is a single uniform segment, so it cannot
answer a segmentation question. The next useful query-unaware experiment should
therefore do one of these:

1. force equal segments with `-seg_eqseg` and compute data-only segment
   diagnostics;
2. move to a higher-dimensional dataset where default SAQ creates multiple
   segments at normal bit budgets;
3. compute cluster-local residual variance by segment for the existing SAQ
   plans and check whether global variance is a good proxy.

The output should be a segment table like:

```text
segment_id,start_dim,end_dim,dim_len,bits,
global_variance_sum,global_variance_share,
cluster_residual_variance_mean,cluster_residual_variance_p90,
within_segment_top_dim_share
```

Held-out query recall should be reported only after the data-only plan or audit
signal is defined.

## 6. Higher-Dimensional Diagnostic Update

The GIST sampled diagnostic strengthens the P0 audit signal without introducing
query-aware assumptions. On `gist_sample100k` (`D=960`, `K=512`), SAQ's default
plans allocate many bits to the `0-64` head because it has 77.7% global PCA
variance, but that head carries only 62.9% weighted cluster-local residual
share. The first post-head segment, `64-256`, has 16.0% global variance but
27.0% weighted residual share.

This supports the revised query-unaware hypothesis: after IVF clustering, the
residual distribution can shift away from the global PCA variance profile used
by SAQ's dynamic planner.

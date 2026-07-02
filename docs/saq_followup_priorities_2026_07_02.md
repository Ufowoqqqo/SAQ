# SAQ Follow-Up Priorities After Paper Review

Date: 2026-07-02

This note distills the external paper-review notes provided after the SAQ pivot
and applies the later advisor feedback that the next direction should preferably
be query-unaware.

It complements:

```text
docs/saq_code_audit_2026_07_02.md
docs/audio_quant_plan_probe_2026_07_02.md
docs/saq_query_unaware_pivot_2026_07_02.md
docs/saq_paper_code_alignment_2026_07_02.md
docs/saq_segment_diagnostic_2026_07_02.md
docs/saq_gist_higher_dim_segment_diagnostic_2026_07_02.md
docs/saq_residual_aware_dp_prototype_2026_07_02.md
```

The revised conclusion is:

```text
SAQ already strongly covers "more accurate quantization + faster offline
encoding" through CAQ, PCA segmentation, and multi-stage estimation. A follow-up
should target a limitation inside SAQ's own query-unaware build setting, not a
small CAQ/SAQ variant and not a workload-specific index-build assumption.
```

## 1. What The Paper Already Does Well

SAQ's core contributions are already substantial:

1. CAQ avoids Extended RaBitQ's expensive enumeration by using code adjustment.
2. PCA concentrates variance into leading dimensions.
3. Dimension segmentation allocates more bits to high-variance segments.
4. Multi-stage estimators support early pruning during search.
5. Experiments cover relative error, Recall@100, quantization time, and QPS.

Therefore, a weak follow-up would be:

```text
slightly different CAQ adjustment
slightly different scalar quantizer
another small tau/clamp/residual sweep outside SAQ
query-aware reweighting that assumes build-time workload samples
```

Those do not solve the novelty problem under the revised boundary.

## 2. Most Relevant Follow-Up Directions

The supplied review listed several possible directions. After the advisor
feedback, the most relevant directions are these query-unaware ones.

### 2.1 Query-Unaware Data-Structure Audit

SAQ's plan is primarily based on global PCA data variance. In the code, the
segment DP uses a proxy close to:

```text
cost(segment, b) = variance_sum(segment) / 2^b
```

This is query-unaware, but it may still be incomplete because SAQ applies one
global segment/bit plan to IVF cluster residuals. A first follow-up should ask:

```text
Does SAQ's global variance-driven segment plan miss base/index structure that
matters for approximate nearest-neighbor quality?
```

Candidate data-only signals:

- global PCA variance share per segment;
- cluster-local residual variance share per segment;
- within-segment concentration, e.g. whether a few dimensions dominate a long
  segment;
- base-as-pseudo-query neighbor-boundary diagnostics, with self matches removed;
- quantization error concentration across clusters or segments.

This preserves the useful lesson from the earlier `vectordb` work:

```text
variance/reconstruction error can disagree with nearest-neighbor ranking quality
```

but does not require representative queries during index construction.

### 2.2 Flexible Segmentation Beyond Contiguous PCA Blocks

SAQ segments contiguous PCA dimensions, partly for SIMD/cache efficiency. The
review highlights two risks:

1. Low-dimensional datasets can have coarse segment granularity, e.g. minimum
   segment size around SIMD-friendly blocks.
2. Contiguous PCA order may not be the best grouping for local residual structure
   or within-segment error concentration.

This matches the first local probe:

| Dataset | B | SAQ default plan |
| --- | ---: | --- |
| audio | 1 | `0 -> 64 (64d 3b); 64 -> 192 (128d 0b)` |
| audio | 2 | `0 -> 192 (192d 2b)` |
| audio | 4 | `0 -> 192 (192d 4b)` |
| audio | 8 | `0 -> 192 (192d 8b)` |

For audio B=2/4, default SAQ has no segmentation to audit. That means a real
segmentation audit needs either:

- B=1 audio as a plumbing sanity case;
- equal-segment controls via `-seg_eqseg`;
- a higher-dimensional dataset where default SAQ segmentation becomes
  non-trivial.

Potential method if positive:

```text
data-only segment boundary selection
```

This is more aligned with the advisor feedback than rank-aware or workload-aware
segment selection.

### 2.3 Local / Cluster-Aware SAQ

SAQ's plan is global, while IVF clusters can have different local covariance and
residual distributions. This is the strongest revised systems direction because
it is fully query-unaware and directly connected to SAQ's IVF implementation.

A possible contribution shape is:

```text
cluster-aware SAQ: learn a small family of segment/bit plans from cluster
residual statistics, then assign each IVF cluster to one plan.
```

The main challenge is metadata overhead. A practical design should avoid one
large unique plan per cluster unless experiments show the benefit justifies it.

### 2.4 SAQ + Graph-Based ANNS

The review notes that SAQ's paper focuses on IVF-style evaluation, while HNSW,
DiskANN, and other proximity graph indexes are dominant in many vector database
settings.

Why this matters:

- graph traversal repeatedly evaluates many candidates;
- SAQ's progressive estimator could be useful for early pruning;
- inaccurate early estimates can change traversal order, so the pruning policy
  needs to be designed carefully rather than copied from IVF.

This is likely a stronger systems direction later, but it is a larger project
than the immediate query-unaware SAQ audit.

### 2.5 Higher-Dimensional Segment Diagnostic Update

The GIST sampled diagnostic adds a stronger P0 signal than `audio` because the
default SAQ planner creates multiple segments on `D=960`. The main observation
is that global PCA variance overweights the first 64 dimensions relative to IVF
residuals, while the first post-head block carries substantially more local
residual share than its global variance share suggests.

This keeps `cluster-aware` or `residual-aware` SAQ as the highest-priority
query-unaware direction.

## 3. Diagnostic-Only Directions

### Query-Aware / Workload-Aware SAQ

The earlier review suggested query-aware bit allocation because real query
traffic can differ from the base distribution. After the advisor feedback, this
should not be the primary method direction.

Keep it only as:

```text
diagnostic lens
upper-bound comparison
negative evidence if query-aware gains vanish under held-out queries
```

Do not design the next main algorithm around build-time representative query
samples.

### Learned Rotation + Bit Allocation

PCA optimizes variance explanation, not recall, ranking loss, or quantization
search error. A stronger transform could jointly optimize:

```text
rotation + segmentation + bit allocation
```

Under the revised boundary, the objective should be data-only, e.g. base
reconstruction, local residual geometry, or base-neighbor stability, not query
workload loss.

### Better Multi-Stage Bounds

SAQ uses variance/Chebyshev-style bounds. Learned or calibrated empirical bounds
could prune more aggressively under distribution shift, but this is downstream
of having a stable SAQ reproduction and evaluation setup.

### Online / Streaming SAQ

Dynamic data and embedding-model drift are important vector DB problems, but
this direction is farther from the current code audit.

### Metadata-Aware SAQ

At very low bit budgets, per-segment factors and side information may matter.
This is relevant if experiments focus on `B < 1` or extremely compressed
settings.

## 4. Current Priority Order

For this project, use the following priority order.

### P0: Query-Unaware SAQ Limitation Audit

Immediate question:

```text
Does SAQ's global variance-driven segment plan underrepresent segments that are
important under base-only or index-only diagnostics, such as cluster-local
residual variance and base-neighbor boundary stability?
```

Required artifacts:

- SAQ quant plan table;
- PCA variance per dimension;
- segment-level global variance aggregation;
- cluster-local residual variance aggregation;
- within-segment concentration statistics;
- optional base-as-pseudo-query boundary diagnostics, excluding self matches;
- relative error metrics;
- R@10 and R@100 as held-out evaluation only, not as build signals.

### P1: Flexible Segmentation Control

If P0 shows mismatch inside or across segments, test:

```text
default SAQ segmentation vs equal segmentation vs data-only segmentation
```

Start with controls before changing SAQ's DP.

### P2: Local / Cluster-Aware SAQ

If cluster-local residual statistics differ strongly from global PCA variance,
prototype a small family of local plans shared across clusters.

### P3: SAQ + Graph Index Sketch

Keep this as the larger systems direction. Do not start implementation until the
SAQ reproduction and P0/P1 audit are stable.

## 5. Immediate Next Experiment

The original immediate diagnostic sequence is now complete:

1. `audio` validated the segment diagnostic pipeline.
2. GIST sampled provided a higher-dimensional multi-segment signal.
3. `script/propose_residual_plan.py` showed that a residual-aware DP objective can
   generate different plans under the same SAQ budget model.

The next useful experiment is no longer another offline table. It should be:

```text
custom-plan injection for create_index, followed by relative-error / recall
comparison between SAQ default and residual-aware plans.
```

Start with GIST sampled B=3/4 because the offline residual cost reductions were
largest there. Full official GIST/K4096 reproduction remains necessary before
strong claims, but it should not block this implementation step.

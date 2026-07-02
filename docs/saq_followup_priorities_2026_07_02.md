# SAQ Follow-Up Priorities After Paper Review

Date: 2026-07-02

This note distills the external paper-review notes provided after the SAQ pivot.
It complements:

```text
docs/saq_code_audit_2026_07_02.md
docs/audio_quant_plan_probe_2026_07_02.md
```

The review's main conclusion is consistent with the code audit:

```text
SAQ already strongly covers the line of "more accurate quantization + faster
offline encoding" through CAQ, PCA segmentation, and multi-stage estimation.
A follow-up should target an implicit assumption or system gap, not a small
variant of CAQ/SAQ.
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
```

Those do not address the novelty problem.

## 2. Most Relevant Follow-Up Directions

The supplied review lists ten possible directions. For our current project, the
most relevant ones are these three.

### 2.1 Query-Aware / Workload-Aware SAQ

SAQ's plan is primarily based on PCA data variance. The paper assumes, at least
for its estimator/modeling, that query vectors share the data distribution. Real
vector database workloads may violate this:

- RAG queries can concentrate on specific semantic regions.
- recommender/user embeddings may not be distributed like items.
- production query traffic can be skewed or time-varying.

Candidate research question:

```text
Given representative query workload samples, can SAQ allocate segment bits to
improve top-k recall rather than only minimizing variance/distance error?
```

This directly connects to the previous `vectordb` result:

```text
PCA reconstruction allocation < PCA rank-boundary allocation
```

Current best first audit:

```text
Compare SAQ segment variance share against rank-boundary share under a query
workload.
```

If they differ, SAQ has a measurable blind spot. If they match, this direction
is less promising.

### 2.2 Flexible Segmentation Beyond Contiguous PCA Blocks

SAQ segments contiguous PCA dimensions, partly for SIMD/cache efficiency. The
review highlights two risks:

1. Low-dimensional datasets can have coarse segment granularity, e.g. minimum
   segment size around SIMD-friendly blocks.
2. Contiguous PCA order may not be the best grouping for query-distance or
   top-k boundary risk.

This matches the first local probe:

| Dataset | B | SAQ default plan |
| --- | ---: | --- |
| audio | 1 | `0 -> 64 (64d 3b); 64 -> 192 (128d 0b)` |
| audio | 2 | `0 -> 192 (192d 2b)` |
| audio | 4 | `0 -> 192 (192d 4b)` |
| audio | 8 | `0 -> 192 (192d 8b)` |

For audio B=2/4, default SAQ has no segmentation to audit. That means a real
segmentation audit needs either:

- B=1 audio as a sanity case;
- equal-segment controls via `-seg_eqseg`;
- a higher-dimensional dataset where default SAQ segmentation becomes
  non-trivial.

Potential method if positive:

```text
rank-aware segment boundary selection
```

This may be more novel than only reweighting bits after SAQ's fixed boundaries.

### 2.3 SAQ + Graph-Based ANNS

The review notes that SAQ's paper focuses on IVF-style evaluation, while HNSW,
DiskANN, and other proximity graph indexes are dominant in many vector database
settings.

Why this matters:

- graph traversal repeatedly evaluates many candidates;
- SAQ's progressive estimator could be useful for early pruning;
- inaccurate early estimates can change traversal order, so the pruning policy
  needs to be designed carefully rather than copied from IVF.

This is likely a stronger systems direction, but it is a larger project than the
immediate query-aware allocation audit.

## 3. Secondary Directions

These are worth keeping in mind, but they should not be first unless the primary
audit fails.

### Learned Rotation + Bit Allocation

PCA optimizes variance explanation, not recall, ranking loss, or quantization
search error. A stronger transform could jointly optimize:

```text
rotation + segmentation + bit allocation
```

This connects to OPQ-style methods, but would require much broader baselines.

### Local / Cluster-Aware SAQ

SAQ's plan is global. IVF clusters can have different local covariance and query
traffic. A local SAQ plan could help, but metadata overhead and training
complexity are real risks.

### Better Multi-Stage Bounds

SAQ uses variance/Chebyshev-style bounds. Learned or calibrated empirical bounds
could prune more aggressively under distribution shift, but this is downstream
of having a stable SAQ evaluation setup.

### Online / Streaming SAQ

Dynamic data and embedding-model drift are important vector DB problems, but
this direction is farther from the current code audit.

### Metadata-Aware SAQ

At very low bit budgets, per-segment factors and side information may matter.
This is relevant if experiments focus on `B < 1` or extremely compressed
settings.

## 4. Current Priority Order

For this project, use the following priority order.

### P0: Query-Aware / Boundary-Aware SAQ Audit

Immediate question:

```text
Does SAQ's variance-driven segment plan underrepresent dimensions or segments
that are important for top-k boundary decisions?
```

Required artifacts:

- SAQ quant plan table;
- PCA variance per dimension;
- rank-boundary weight per dimension;
- segment-level aggregation;
- R@10 and R@100 metrics;
- relative error metrics.

### P1: Flexible Segmentation Control

If P0 shows mismatch inside or across segments, test:

```text
default SAQ segmentation vs equal segmentation vs rank-aware segmentation
```

Start with controls before changing SAQ's DP.

### P2: SAQ + Graph Index Sketch

Keep this as the larger systems direction. Do not start implementation until the
SAQ reproduction and P0/P1 audit are stable.

## 5. Immediate Next Experiment

Because audio B=2/4 default SAQ is a single segment, the next useful experiment
should be one of these:

1. `audio`, B=1, default SAQ, join its two segments with rank-boundary weights.
2. `audio`, B=2/4, force equal segmentation with `-seg_eqseg`, then check whether
   segment-level rank-boundary share differs from variance share.
3. Move to a higher-dimensional dataset where SAQ's default DP creates multiple
   segments at normal bit budgets.

The fastest next step is option 1, because the quant plan already exists:

```text
B=1: 0 -> 64 (64d 3b); 64 -> 192 (128d 0b)
```

This gives a minimal end-to-end test of the join pipeline before spending time
on larger datasets.

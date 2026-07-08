# Structural SAQ Follow-Up Direction Review

Date: 2026-07-08

## Purpose

This note compares three query-unaware SAQ follow-up directions before writing
new method code. The goal is to avoid another local metric-tuning path and pick
a direction that can plausibly support a database top-conference contribution.

Status update: this recommendation has been superseded by the mixed shared-plan
end-to-end, static-cost, and runtime-decomposition results. Mixed local
shared-plan materialization is now treated as negative evidence rather than the
main direction. The active direction is single-global-plan segment-cost-aware
DP. See:

```text
docs/shared_plan_negative_evidence_and_dp_pivot_2026_07_08.md
```

All directions must use only normal index-build information:

```text
base vectors, PCA artifacts, IVF centroids, cluster ids, residual statistics,
SAQ quantization plans, and index metadata
```

Held-out queries should be used only for final evaluation.

## Direction 1: Cluster-Aware / Local Residual-Aware SAQ Plan Sharing

Targeted SAQ assumption:

```text
SAQ learns one global PCA-variance segment plan and applies it to every IVF
cluster, even though each cluster quantizes residuals around its centroid.
```

Proposed method:

1. Compute per-cluster residual variance profiles from `x - centroid(cid)`.
2. Learn a small family of shared segment/bit plans from these residual
   profiles.
3. Assign each IVF cluster one plan id.
4. Store the plan family plus one compact plan id per cluster.

Expected novelty:

This is the strongest direction because it targets a structural mismatch in
SAQ's IVF design rather than a post-hoc candidate filter. It remains
query-unaware and directly connects to SAQ's own implementation path.

Overhead model:

```text
training overhead: residual profile computation + plan-family learning
index overhead: one plan id per IVF cluster + multiple shared plan definitions
search overhead: possible per-plan searcher/estimator selection
implementation overhead: moderate, because the current IVF code stores one
global SaqData and one global plan
```

Smallest falsification experiment:

Run an offline residual-profile study without changing the index format:

```text
For each cluster c:
  compute local residual variance v_c
  compare cost(v_c, P_global) against cost(v_c, P_local_oracle)
  compress local signals into M shared plans for M in {2, 4, 8}
  compare cost(v_c, P_global) against cost(v_c, P_shared(g(c)))
```

Stop condition:

Stop this direction if local-oracle residual DP improves the weighted residual
cost only marginally, or if a small shared family loses most of the local-oracle
gain. A practical target should be a clearly visible weighted cost reduction
with small `M`, not a result that needs one plan per cluster.

Strict-reviewer risk:

A reviewer may ask whether residual-cost gains translate into recall/QPS gains
and whether the added plan metadata is justified. This is acceptable only if the
offline signal is strong enough to motivate real index implementation.

## Direction 2: Segment-Cost-Aware DP

Targeted SAQ assumption:

```text
SAQ's DP mainly optimizes a variance-based quantization-error proxy, while the
search path also depends on segment count, positive segment coverage, and
multi-stage refinement cost.
```

Proposed method:

Extend the planner objective or report a Pareto frontier over:

```text
quantization-risk proxy
search-time segment-cost proxy
budget and per-segment factor overhead
```

Expected novelty:

This is cleaner than the old scorer-filtering path because it changes the
planner rather than selecting from hand-generated candidates. However, it is
still close to SAQ unless the segment-cost term exposes a systematic limitation
of the variance-only DP.

Overhead model:

```text
training overhead: small, because DP state can include simple cost terms
index overhead: none if the output is still one global plan
search overhead: potentially lower if the plan has fewer costly segments
implementation overhead: low to moderate
```

Smallest falsification experiment:

Before changing C++ index code, reproduce SAQ's DP offline and generate a
risk/cost Pareto frontier for existing datasets. Compare whether the default
SAQ plan is far from the frontier under plausible search-cost terms.

Stop condition:

Stop if the default SAQ plan is already near the Pareto frontier, or if
search-cost-aware plans mainly reduce segment count while visibly increasing
quantization risk.

Strict-reviewer risk:

A reviewer may view this as adding another tuned lambda unless the objective is
simple, stable, and tied to actual search cost. It needs strong ablation against
plain segment-count minimization.

## Direction 3: Flexible Segmentation / Learned Grouping

Targeted SAQ assumption:

```text
SAQ uses contiguous PCA blocks with 64-dimensional granularity. This may be too
coarse or too tied to global PCA order for some residual distributions.
```

Proposed method:

Compare default contiguous PCA segmentation against query-unaware alternatives:

```text
data-only boundary selection
dimension grouping by residual statistics
block reordering before segmentation
```

Expected novelty:

This could be the most algorithmically novel direction, because it questions the
structure of SAQ's dimension partition itself. It is also the riskiest because
non-contiguous grouping can conflict with SIMD layout, memory access, and the
existing estimator design.

Overhead model:

```text
training overhead: potentially high if grouping is learned
index overhead: permutation/group metadata
search overhead: possible loss of contiguous memory access
implementation overhead: high, because quantizer, estimator, and serialization
may need layout changes
```

Smallest falsification experiment:

Start with an offline comparison: measure within-segment residual concentration
and ask whether high-risk dimensions are hidden inside long low-bit segments.
Only proceed if a simple data-only grouping signal is clearly stronger than
contiguous PCA order.

Stop condition:

Stop if residual risk remains mostly monotonic in PCA order, or if the expected
memory-layout cost dominates the possible quantization benefit.

Strict-reviewer risk:

A reviewer may ask whether the method abandons SAQ's main system advantage:
simple contiguous segments with efficient SIMD-friendly access. Any positive
story must include explicit layout and search-cost accounting.

## Historical Recommendation

The original recommendation was to start with Direction 1. That recommendation
is no longer active after the shared-plan end-to-end and runtime-decomposition
results.

The original first concrete task was an offline cluster residual profile and
shared-plan feasibility study. It did not require changing the index format,
but it directly tested the central structural hypothesis:

```text
one global SAQ plan may be mismatched to IVF-local residual distributions
```

The branch did proceed to a real prototype after the offline study showed a
visible residual-cost signal. The prototype then showed that mixed-plan search
overhead dominates the small residual-local gain. Therefore the current
direction is no longer mixed local plan sharing; it is single-global-plan
segment-cost-aware DP.

The historical proceed condition was:

```text
local-oracle residual plans improve weighted residual DP cost noticeably
small shared families, e.g. M = 2, 4, or 8, retain much of that gain
the resulting plan shapes are interpretable
metadata overhead is plausibly small
```

Direction 2 is now the active direction. Direction 3 remains a later,
higher-risk direction after the global segment-cost question is better
understood.

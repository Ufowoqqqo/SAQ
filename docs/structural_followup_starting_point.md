# Structural SAQ Follow-Up Starting Point

Date: 2026-07-08

## Why This Branch Exists

The previous `saq-boundary-audit` branch explored default-neighborhood plan
generation and empirical scorer-based promotion/rejection. That work produced
useful evidence, but the method is too close to local SAQ tuning to be the main
novelty path for a database top-conference paper.

This branch restarts from original SAQ code plus confirmed correctness fixes so
that future work can focus on structural SAQ limitations.

## What Is Kept

- Upstream SAQ implementation from `upstream/main`.
- Positive 1-bit segment packing fix.
- Padded-lane finite block-min search mode for reliable multi-segment search
  evaluation.
- Research guidance for a query-unaware structural follow-up.

## What Is Not Kept

- Fixed-policy scorer and default-neighborhood candidate generator.
- Scorer calibration, feature-cache, and fixed-policy matrix runners.
- Input hash/provenance tooling.
- Large historical result documents and meeting slides from the old branch.

## Primary Research Hypothesis

SAQ learns one global PCA-variance segment plan and applies it to all IVF
cluster residuals. This may be structurally mismatched to local residual
distributions even without using any query workload during indexing.

The first research direction is therefore:

```text
cluster-aware / local residual-aware SAQ plan sharing
```

The method should learn a small family of shared segment/bit plans from cluster
residual statistics and assign each IVF cell to a plan id, with explicit
metadata and search-cost accounting.

## Secondary Directions

1. Segment-cost-aware DP: include search-time segment cost in the planner
   objective or report a quantization-risk/search-cost Pareto frontier.
2. Flexible segmentation / learned grouping: test whether contiguous PCA blocks
   and 64-dimensional granularity are limiting query-unaware assumptions.

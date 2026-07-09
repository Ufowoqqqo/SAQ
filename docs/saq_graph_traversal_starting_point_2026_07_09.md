# SAQ Graph Traversal Starting Point

## Purpose

This note defines the starting point for the `saq-graph-traversal-analysis`
branch. The branch asks whether SAQ's progressive compressed distance estimator
is compatible with graph-based ANNS traversal.

The immediate goal is not to integrate SAQ into HNSW or DiskANN. The immediate
goal is to design a minimal offline measurement that can falsify or support the
graph-index direction.

## Why Pivot

Recent branches produced useful limitation evidence but did not yield a strong
main method:

- local or cluster-aware shared plans exposed residual structure but suffered
  from multi-plan estimator/search overhead;
- static segment-cost global DP did not translate lower static cost into
  recall-matched QPS benefit;
- direct CAQ estimator-error DP moved plan shapes but failed recall-matched
  evaluation on the first changed GIST plan;
- simple IVF segment reordering and variance-bound calibration did not reveal a
  safe low-overhead search-procedure method.

The next direction should therefore avoid another small IVF planner or
search-loop tweak. A graph index changes the role of approximate distance:

```text
IVF: approximate distances mostly rank/filter a candidate set selected by
centroid probing.

Graph ANNS: approximate distances can change which node is expanded next and
which region of the graph is visited.
```

This creates a graph-specific question that is not answered by the previous IVF
experiments.

## Research Question

```text
Can SAQ-style progressive compressed distance estimation be used inside
graph-based ANNS traversal without destabilizing the search path, and what
query-unaware refinement policy is needed to preserve the recall/work tradeoff?
```

## First Measurement Design

The first measurement should use a fixed graph or fixed adjacency replay as an
experimental harness. It should not change SAQ's persisted index format.

For each query and traversal decision, compare frontier ordering under:

1. exact float distance;
2. full SAQ estimate;
3. staged SAQ estimate before accurate refinement;
4. staged SAQ estimate with a small fixed refinement rule, only if justified by
   the first measurements.

Report:

- frontier top-1 disagreement rate;
- frontier top-L disagreement rate;
- rank of the exact-best neighbor under each SAQ estimate;
- probability that the exact-best expansion is demoted beyond the beam width;
- number of frontier candidates requiring refinement to recover exact ordering;
- graph nodes visited, neighbor expansions, compressed reads, and refinement
  reads.

The unit of analysis is a graph traversal decision, not a final IVF candidate
score.

## Reviewer Risks

A strict reviewer may say this is only engineering integration. The response
must be evidence-based: show a graph-specific failure mode or opportunity where
SAQ approximation changes traversal, not merely final reranking.

A strict reviewer may also say final reranking solves approximate distance
error. The measurement must separate visited-candidate reranking from traversal
path sensitivity, because final reranking cannot recover candidates that were
never visited.

Graph-search hyperparameters are another risk. Fix graph construction and graph
search parameters before comparing distance estimators. Vary only the distance
estimator and any explicitly justified refinement policy.

## Stop Conditions

Stop the graph-index direction if:

- SAQ approximate distances rarely change graph frontier order;
- the exact-best expansion usually remains inside the graph beam without
  refinement;
- recovering stable traversal requires refining nearly all frontier candidates;
- the first useful policy depends on arbitrary tuned thresholds;
- the result only shows a generic recall/speed tradeoff with no SAQ-specific
  insight.

## Immediate Next Step

Perform a graph-index compatibility review:

1. Read the SAQ paper sections on multi-stage estimation, IVF evaluation, and
   graph-index discussion or future work.
2. Locate the current repository's IVF search path and any available
   graph-related utilities.
3. Decide whether the first offline replay should use a small kNN graph or an
   external HNSW graph as a fixed harness.
4. Write the exact traversal-sensitivity metric before implementation.

# SAQ Pivot Synthesis and Graph-Index Direction Proposal

## Decision

Pivot away from small IVF planner and search-loop changes as the main research
direction. Treat the recent work as limitation evidence:

```text
SAQ's default IVF-oriented progressive search path is difficult to improve with
low-overhead query-unaware local changes.
```

The next candidate direction should be graph-index compatibility and traversal
path sensitivity. This proposal does not approve a full HNSW or DiskANN
integration yet. The first step should be a paper/source-code review and a
minimal traversal-sensitivity measurement.

## What Has Been Ruled Out

The following directions have been evaluated enough to stop as main methods on
this branch.

### 1. Mixed shared local plans

The mixed shared-plan direction exposed a real local residual signal, especially
on GIST. However, using multiple plans introduces query-time estimator dispatch
and per-plan overhead. The benefit was not strong enough to justify changing
SAQ's one-plan architecture.

Research value:

```text
Useful limitation evidence for local residual heterogeneity, but not a clean
main method.
```

### 2. Single global static segment-cost DP

The static segment-cost direction asked whether SAQ's variance DP misses
search-time cost. It found lower-cost candidate plans, but the end-to-end
safe-search evaluation did not produce a recall-matched QPS improvement.

Research value:

```text
Static cost terms alone do not reliably model SAQ's actual search-time
work/recall tradeoff.
```

### 3. Direct CAQ estimator-error planner objective

The fac-error objective selected a different GIST B=4 plan:

```text
SAQ variance plan:   64x11_192x6_320x4_256x2_128x0
fac-error plan:      192x9_512x4_256x0
```

At the same nprobe, the fac-error plan was faster and smaller, but recall
dropped. Increasing nprobe did not recover the default recall before the QPS
advantage disappeared.

Research value:

```text
Measured CAQ estimator error can move the plan, but the first one-global-plan
objective modification does not beat SAQ under recall-matched evaluation.
```

### 4. Simple segment-order scheduling

A diagnostic replay compared several hyperparameter-free segment orders:

```text
pca, reverse, bit_desc, dim_desc, cost_asc, risk_per_cost_desc
```

Across nprobe 160, 200, and 240 on GIST sample100k K512 B=4, the default PCA
order remained tied for the lowest observed work. Reverse and dimension
descending orders were substantially worse.

Research value:

```text
SAQ's default PCA/bit order already captures the easy query-unaware ordering
opportunity in the tested IVF setting.
```

### 5. Variance-bound tightening by calibration

The final variance-bound measurement showed why variance pruning is nearly
inactive. The variance-stage block minimum is usually far below the current
top-k boundary. The median relative gap is about 0.74, and meaningful pruning
would require removing roughly 58-63% of the conservative variance slack.

That scale of tightening would be arbitrary without a new safety argument.

Research value:

```text
The variance stage is weak, but the observed weakness does not imply a safe
low-overhead refinement.
```

## Synthesis

The negative evidence is useful because it narrows the plausible contribution.
The current data does not support another small plan search, another static cost
term, another segment-order rule, or another calibrated search threshold.

The strongest defensible statement is:

```text
Within SAQ's IVF candidate-filtering architecture, the default variance plan
and progressive estimator are more robust than several natural query-unaware
corrections. Remaining opportunities likely require changing the index context
or deriving a stronger estimator guarantee, not tuning local policies.
```

This framing is more valuable than reporting tiny recall/QPS changes. It
positions the project around a concrete SAQ limitation: SAQ is effective in the
IVF-style setting it was designed and evaluated around, but its behavior under
graph traversal remains underexplored.

## Why Graph Indexes Are The Next Structural Question

SAQ's implementation in this repository is IVF-centered. The initializer uses a
flat centroid scan for the current cluster counts, and the HNSW initializer path
is explicitly unavailable:

```text
CHECK(false) << "HNSW not implemented";
```

There is also no bundled graph-index implementation beyond a generic beam-set
utility comment. This means the next graph direction should not start by
modifying production search code. It should first isolate the research question.

The key difference is algorithmic:

```text
In IVF, compressed distances mainly rank and filter candidates after the
candidate set has been chosen by centroid probing.

In graph indexes, compressed distances can change the traversal path itself:
which node is expanded next, which neighbors enter the frontier, and which
region of the graph is explored.
```

This creates a higher-level limitation than the previous IVF search-loop work.
Even a small distance-estimation error can matter more in graph search because
it may prevent the traversal from reaching the right region. Final reranking
cannot always repair a wrong traversal path if the relevant candidates were
never visited.

## Research Question

The proposed research question is:

```text
Can SAQ-style progressive compressed distance estimation be used inside
graph-based ANNS traversal without destabilizing the search path, and what
query-unaware refinement policy is needed to preserve the recall/work tradeoff?
```

This remains query-unaware:

- no representative-query workload is used to learn a policy;
- no query labels are used to fit thresholds;
- benchmark queries are used only to evaluate traversal behavior and recall;
- graph parameters are fixed before comparing distance estimators.

## Why This Is Not Just "Integrate SAQ With HNSW"

A weak version of this direction would simply plug SAQ codes into an HNSW or
DiskANN implementation and report recall/QPS. That would be hard to defend.
It would mix estimator quality, graph construction, search parameters, memory
layout, and implementation effort.

The stronger research target is a graph-specific limitation and method:

```text
SAQ's progressive estimator was designed for staged filtering. Graph traversal
needs a frontier-stable estimator because early approximate distances affect
which nodes are expanded.
```

If the first measurements show no traversal instability, the direction should
stop. If they show stable instability, the contribution could become a
traversal-aware refinement policy for compressed graph search.

## First Falsifiable Experiment

Do not implement full HNSW or DiskANN integration first. The first study should
be an offline traversal-sensitivity measurement.

### Stage 0: Review

Review:

- SAQ paper sections on multi-stage distance estimation and IVF evaluation;
- SAQ paper discussion of graph indexes or future work;
- this repository's IVF search path;
- available local graph-related utilities.

Current source evidence suggests:

- `saqlib/index/ivf.hpp` implements IVF search and has no active HNSW
  initializer;
- `saqlib/utils/buffer.hpp` has a beam-set utility comment, but not a complete
  graph index;
- `saqlib/third/` only contains Eigen.

### Stage 1: Offline graph replay

Build or load a fixed graph only as an experimental harness. The graph can be a
small kNN graph or an external HNSW graph if an existing library is used as a
black-box builder. The first experiment should not change SAQ's persisted index
format.

For each query and traversal step, compare the frontier ordering induced by:

1. exact float distance;
2. full SAQ estimate;
3. staged SAQ estimate before accurate refinement;
4. staged SAQ estimate with a small fixed refinement rule.

Measure:

- frontier top-1 disagreement rate;
- frontier top-L disagreement rate;
- rank of the exact-best neighbor under each SAQ estimate;
- probability that the exact-best expansion is demoted beyond the beam width;
- number of frontier candidates requiring refinement to recover exact order;
- recall/work tradeoff for fixed refinement budgets.

The unit of analysis is a graph traversal decision, not a final IVF candidate
score.

### Stage 2: Minimal policy only if Stage 1 supports it

Only if Stage 1 finds a stable graph-specific failure, evaluate a minimal
query-unaware refinement policy such as:

```text
Refine candidates whose approximate frontier distance is within a fixed
estimator-derived uncertainty interval of the current best frontier distance.
```

The interval must come from stored SAQ quantities, finite-code error analysis,
or an explicit approximation model. It should not be tuned by benchmark query
recall.

## Expected Overhead Model

A graph-index proposal must account for:

- graph nodes visited;
- neighbor expansions;
- compressed code reads;
- segment/factor reads;
- full-vector or high-precision refinements, if any;
- frontier insertions and heap updates;
- final rerank cost;
- index size and any additional metadata.

The central metric should not be only QPS. It should report:

```text
recall versus graph work and memory traffic under fixed graph parameters.
```

This prevents the project from claiming a speed gain that is actually caused by
weaker traversal or by changing graph hyperparameters.

## Strict-Reviewer Objections

### Objection 1: This is only engineering integration.

Response required:

```text
Show a graph-specific failure mode or opportunity that does not exist in IVF:
compressed distances affect traversal path, not only candidate scoring.
```

### Objection 2: Final reranking can fix approximate distances.

Response required:

```text
Final reranking can only fix visited candidates. The proposed measurement must
show whether SAQ approximation changes which nodes are visited in the first
place.
```

### Objection 3: Graph search has too many tunable parameters.

Response required:

```text
Fix graph construction and graph search parameters. Vary only the distance
estimator and refinement policy.
```

### Objection 4: Exact refinement during traversal destroys compression value.

Response required:

```text
Report refinement frequency, memory traffic, and graph work. A valid method
must preserve a meaningful compression or bandwidth advantage.
```

### Objection 5: The method is another empirical threshold.

Response required:

```text
Any threshold must be derived from estimator structure or fixed before held-out
evaluation. Otherwise stop the direction.
```

## Stop Conditions

Stop the graph-index direction if any of the following happens:

- SAQ approximate distances rarely change graph frontier order;
- the exact-best expansion usually remains inside the graph beam without
  refinement;
- recovering stable traversal requires refining nearly all frontier candidates;
- the first useful policy depends on arbitrary tuned thresholds;
- implementation complexity becomes the main contribution before a
  graph-specific limitation is demonstrated;
- the result only shows a standard recall/speed tradeoff with no SAQ-specific
  insight.

## Immediate Next Step

Perform a graph-index compatibility review and design the minimal
traversal-sensitivity measurement.

The review should answer:

1. Which graph-index implementation or external harness should be used for the
   first offline replay?
2. Which dataset should be used first, given that GIST has repeatedly exposed
   SAQ plan sensitivity but single-dataset evidence is not enough?
3. Which SAQ distance estimates can be replayed without changing index format?
4. What exact metric determines whether graph traversal is sensitive enough to
   justify a method?

Do not start a full graph-index integration until the offline replay shows a
clear graph-specific signal.

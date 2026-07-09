# SAQ Graph Traversal Measurement Design

## Purpose

This note records the first graph-index compatibility review on the
`saq-graph-traversal-analysis` branch and defines a minimal offline
traversal-sensitivity measurement.

The goal is not to integrate SAQ into HNSW or DiskANN yet. The goal is to
answer a smaller falsifiable question:

```text
When a graph search must decide which frontier or neighbor candidate to expand
next, does SAQ's compressed distance estimate preserve the exact-float ordering
well enough to avoid traversal-path instability?
```

If this signal is absent, the graph direction should stop before implementation
surface grows. If the signal is present, the next method question is whether a
query-unaware refinement rule can stabilize graph traversal with controlled
memory traffic.

## Paper Review

The SAQ paper motivates multi-stage estimation for ANN search as a progressive
filtering mechanism. Its estimator starts from cheap segment-level information,
then refines with quantized codes, and uses bounds to avoid reading all segment
bits for candidates that cannot enter the result set.

The paper evaluation is IVF-centered. It builds IVF indexes, scans the
top-ranking clusters for each query, and reports recall/QPS by varying the
number of probed clusters. The paper explicitly recognizes proximity graph
indexes such as HNSW and NSG as important, but leaves the combination with
vector quantization to future work.

This matters because IVF and graph traversal use approximate distances in
different places:

```text
IVF: the candidate set is selected by centroid probing; SAQ mainly filters and
reranks vectors inside selected clusters.

Graph ANNS: the distance estimate can decide which node is expanded next, which
neighbors enter the frontier, and which region of the graph is reached.
```

The graph direction is therefore not just another QPS experiment. It tests
whether SAQ's estimator is stable enough for decisions that affect reachability,
not only final scoring among already visited candidates.

## Source Review

### Current Index Path

The current repository is IVF-centered:

- `saqlib/index/ivf.hpp` prepares a centroid initializer, searches the nearest
  `nprobe` centroids, and scans the selected clusters.
- The HNSW initializer path is not active. For large centroid counts, the code
  currently fails with `HNSW not implemented`.
- `saqlib/index/initializer.hpp` contains `FlatInitializer`, which computes
  centroid distances by full scan.
- `saqlib/utils/buffer.hpp` contains a sorted beam buffer utility with a comment
  that it can be used for graph-based ANN search, but the repository does not
  contain a complete graph index.
- `saqlib/third/` contains Eigen only; there is no bundled HNSW or DiskANN
  dependency.

Implication:

```text
The first graph experiment should be an offline replay over a fixed adjacency
list, not a production graph-index integration.
```

### Current SAQ Distance Interfaces

The useful existing interface is `IVF::estimate` in `saqlib/index/ivf.hpp`.
For each vector in the selected clusters, it can emit:

- `compAccurateDist`: full SAQ estimate using all available quantized bits;
- `compFastDist`: 1-bit fast estimate;
- `varsEstDist`: variance-bound estimate.

The lower-level estimator structure is:

- `SaqEstimatorBase` splits the query by SAQ segment and prepares one CAQ
  estimator per segment;
- `SaqCluEstimator` aggregates per-segment `varsEstDist`, `compFastDist`, and
  `compAccurateDist` over cluster-packed SAQ data;
- `SaqCluEstimatorSingle` exposes single-vector versions for cluster-packed
  data;
- `SaqSingleEstimator` can score a `SaqSingleDataWrapper`, but the current IVF
  index stores vectors in cluster-packed form.

For an offline graph replay, the most direct route is:

```text
load the existing SAQ IVF index
build id -> (cluster id, local offset) from `IVF::get_pclusters()`
for each graph candidate id:
  prepare the SAQ estimator for that candidate's assigned cluster
  score the candidate at its local offset
```

This does not use IVF's centroid probing to select candidates. The cluster id
is only used as SAQ code metadata, because current SAQ codes are residual-coded
relative to IVF centroids.

This is an important compatibility observation: graph traversal over SAQ codes
must either carry the residual reference metadata for each graph node or use a
different global-reference quantization layout. The first measurement should
record this overhead instead of hiding it.

## Measurement Principle

The first measurement should avoid full graph-search confounders. In particular,
it should not depend on:

- a learned query workload;
- fitted thresholds;
- a large graph-integration code path;
- HNSW entry-point heuristics;
- graph construction changes while comparing estimators.

Therefore the first measurement should be local and threshold-free:

```text
Given a query q and a graph expansion candidate u, compare how exact-float and
SAQ-estimated distances order the fixed neighbor set N(u).
```

This isolates the graph-specific question:

```text
Would SAQ choose or promote a different next expansion than exact distance on
the same graph neighborhood?
```

Only after this local expansion test shows a stable signal should we run a full
beam-search traversal replay.

## Fixed Graph Harness

The repository does not provide an HNSW implementation. The first harness should
therefore use a fixed adjacency list outside the production SAQ index format.

Recommended first harness:

```text
exact or approximate kNN adjacency over a deterministic data subset
```

Rationale:

- it avoids implementing HNSW before there is a research signal;
- it supplies graph neighborhoods where expansion order matters;
- it keeps graph construction fixed while changing only the distance estimator;
- exact kNN adjacency is acceptable for a diagnostic harness because graph
  construction cost is not part of the proposed method.

The first dataset should be GIST-derived because GIST has a high dimension,
multi-segment SAQ plans, and repeatedly exposed SAQ plan/search sensitivity in
earlier negative evidence. Any positive claim must later be checked on at least
one additional dataset.

The deterministic subset size and graph degree should be treated as measurement
budgets, not method hyperparameters. The note that reports results must state
the subset size, graph degree, graph construction method, and whether adjacency
was exact or approximate.

## Distance Variants To Compare

For each query-candidate pair, compare:

1. `exact_float`
   - squared L2 distance on original vectors, or equivalently on PCA-rotated
     vectors because PCA rotation preserves L2 distance.
2. `saq_full`
   - `SaqCluEstimatorSingle::compAccurateDist`, using all stored quantized
     bits.
3. `saq_fast`
   - `SaqCluEstimatorSingle::compFastDist`, using the 1-bit fast estimator.
4. `saq_var`
   - `SaqCluEstimatorSingle::varsEstDist`, using the variance-stage estimate.
5. `saq_refine_top_r`
   - a diagnostic counterfactual: sort by a cheap estimate, then refine the top
     `r` candidates with `saq_full`.

The `saq_refine_top_r` setting is not a method yet. Its purpose is to measure
how much refinement is needed to recover exact-float expansion choices. Report
the whole rank distribution rather than selecting a tuned `r`.

## Local Expansion Metrics

For a query `q` and a graph node `u`, let `N(u)` be the fixed neighbor set.
Let:

```text
v_exact = argmin_{v in N(u)} d_exact(q, v)
rank_est(v_exact) = rank of v_exact after sorting N(u) by an SAQ estimate
```

Report these threshold-free metrics:

- `top1_disagreement_rate`
  - fraction of `(q, u)` events where the SAQ-estimated best neighbor differs
    from `v_exact`;
- `rank_exact_best_mean`
  - mean rank of `v_exact` under the SAQ estimate;
- `rank_exact_best_p50/p90/p99`
  - distribution of how far the exact-best expansion is demoted;
- `topL_containment_curve`
  - for each `L`, fraction of events where `rank_est(v_exact) <= L`;
- `kendall_tau_or_spearman`
  - optional rank agreement between exact distances and SAQ estimates over
    `N(u)`;
- `margin_conditioned_rank`
  - rank statistics grouped by the exact gap between the best and second-best
    neighbor in `N(u)`.

The most important quantity is the rank distribution of `v_exact`. It directly
answers how many cheap-ranked candidates would need refinement before the exact
best expansion is visible.

## Frontier Replay Metrics

If local expansion disagreement is visible, run a second replay over frontier
sets produced by a fixed exact-distance graph traversal.

For each query and traversal step `t`, let `F_t` be the frontier before the next
expansion under exact traversal. Let:

```text
v_t = argmin_{v in F_t} d_exact(q, v)
rank_est(v_t) = rank of v_t under an SAQ estimate on F_t
```

Report:

- `frontier_top1_disagreement_rate`;
- `frontier_exact_next_rank_p50/p90/p99`;
- `frontier_topL_containment_curve`;
- `refinement_needed_to_include_exact_next`;
- `visited_set_divergence` between exact replay and SAQ replay, only after a
  full traversal replay is implemented.

This second stage is closer to real graph search, but it is still a replay. It
should not change graph construction or SAQ index format.

## Refinement Counterfactuals

Do not tune thresholds from benchmark recall. The first refinement analysis
should use rank-based counterfactuals:

```text
For each expansion event, sort candidates by `saq_fast`.
Refine the top r candidates with `saq_full`.
Ask whether the exact-float best candidate is included by rank r.
```

Report the complete curve over `r`:

```text
r = 1, 2, 4, 8, ..., degree
```

This is not a method hyperparameter because no value of `r` is selected for
deployment in this measurement. It is a diagnostic curve that estimates how
expensive a stable traversal-aware policy might need to be.

If the curve says almost all neighbors must be refined, the graph direction is
weak. If small `r` recovers most exact-best expansions, the next method could
study whether SAQ can derive an uncertainty interval or safe frontier rule that
selects those candidates without query-workload tuning.

## Expected Prototype Shape

The first prototype should be a diagnostic binary, not a production searcher.
A plausible binary name is:

```text
bin/profile_graph_frontier
```

Expected inputs:

- dataset name and data path;
- existing SAQ index path or normal SAQ `dataset/K/B/PCA` flags;
- base vectors for exact float distances;
- query vectors for evaluation only;
- fixed adjacency file, or a flag to build a deterministic diagnostic kNN
  adjacency on a subset;
- maximum number of queries/events to replay as a measurement budget.

Expected internal steps:

1. Load the SAQ index.
2. Load base and query vectors.
3. Build `id_to_cluster_local` by scanning `IVF::get_pclusters()`.
4. Load or build fixed adjacency.
5. For each query, construct one `SaqCluEstimatorSingle`.
6. For each candidate id, prepare the estimator for the candidate's cluster and
   score its local offset.
7. Write one aggregate CSV and one Markdown summary.

The first prototype should not alter:

- SAQ index serialization;
- graph node storage;
- production `IVF::search`;
- production `SAQSearcher::searchCluster`.

## Overhead To Account For

A graph-compatible SAQ method must account for:

- graph nodes visited;
- neighbor expansions;
- SAQ estimator preparations per query;
- number of distinct residual-reference clusters touched by a frontier;
- compressed code reads;
- segment/factor reads;
- full SAQ refinements;
- exact-vector reads, if any;
- frontier heap operations;
- final reranking cost;
- additional node metadata such as cluster id or local offset.

The first replay should at least report:

```text
events
neighbors_scored
distinct_clusters_per_event
saq_full_calls
saq_fast_calls
saq_var_calls
```

The `distinct_clusters_per_event` metric is important because current SAQ codes
are tied to IVF residual references. If graph frontiers touch many clusters,
the estimator-prepare overhead may become a structural compatibility problem.

## Strict-Reviewer Objections

### Objection 1: This is just plugging SAQ into HNSW.

Required response:

```text
The first evidence is not an integration benchmark. It isolates whether SAQ
estimation changes graph expansion decisions on the same fixed graph.
```

### Objection 2: Final reranking fixes approximate-distance error.

Required response:

```text
Final reranking only fixes candidates that graph traversal visited. The metric
measures whether SAQ changes which candidates would be expanded or reached.
```

### Objection 3: The result depends on arbitrary graph parameters.

Required response:

```text
The first local expansion metric uses fixed neighbor sets and reports rank
distributions rather than selecting a tuned beam or threshold.
```

### Objection 4: SAQ's IVF residual coding is not natural for graph indexes.

Required response:

```text
That is part of the compatibility question. The replay explicitly measures how
often graph frontiers cross residual-reference clusters and what estimator
setup overhead this implies.
```

### Objection 5: A refinement rule could become another empirical threshold.

Required response:

```text
The first replay reports complete rank/refinement curves. A later method may
select a rule only if it has a mechanism-level rationale from SAQ estimator
structure, not from fitted query recall.
```

## Stop Conditions

Stop before full graph integration if:

- `saq_full` almost always preserves the exact-best neighbor within the first
  few ranks, leaving no graph-specific failure to solve;
- `saq_fast` and `saq_var` are unstable, but recovering exact expansion order
  requires refining nearly all neighbors;
- frontier events touch so many residual-reference clusters that estimator
  preparation dominates any plausible compressed-distance saving;
- the only possible policy is a fitted distance threshold with no derivation;
- the effect appears only on one dataset and disappears on a second
  high-dimensional dataset.

## Immediate Next Step

Implement the minimal local expansion ordering profiler only after this design
is accepted.

The first implementation should:

1. avoid production graph-index integration;
2. use a fixed adjacency harness;
3. build the `id -> (cluster, local offset)` map from the loaded IVF index;
4. output exact-best rank distributions under `saq_full`, `saq_fast`, and
   `saq_var`;
5. report cluster-reference diversity per expansion event.

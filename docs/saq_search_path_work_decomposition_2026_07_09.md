# SAQ Search Path Review And Work-Decomposition Plan

## Scope

This note reviews the current SAQ query-time search path before proposing any
new search policy. The goal is to locate where work is spent and to define the
minimal measurements needed to evaluate whether search-procedure /
estimator-scheduling integration is a plausible research direction.

The review is intentionally conservative:

- no query-aware plan learning;
- no new pruning rule;
- no new estimator schedule;
- no claim that a schedule-level method exists yet.

The immediate question is:

```text
Does the current SAQ search path spend enough measurable work in avoidable
fast-estimation, accurate-refinement, pruning, or result-maintenance stages to
justify a principled search-procedure method?
```

## End-To-End Search Path

### 1. Benchmark Entry Point

`src/test_qps.cpp` drives the QPS/recall measurement.

Relevant code:

- `QPSTester::run_search`, lines 49-130;
- `main`, lines 255-281, where `SearcherConfig` is built.

For each query, the benchmark calls:

```cpp
ivf_.search(query_.row(i), TOPK, nprobe, searcher_cfg,
            results[i].data(), &runtime_metrics[i]);
```

After all queries finish, `test_qps` aggregates:

- recall from overlap with the supplied ground truth;
- average per-query time and QPS;
- `fast_bitsum + acc_bitsum` as a bandwidth proxy;
- `total_comp_cnt` as a candidate-computation proxy.

Current limitation: these metrics are too coarse to explain where time is
spent inside the search loop.

### 2. IVF Cluster Selection

`saqlib/index/ivf.hpp` contains the query entry point:

- `IVF::search`, lines 280-316;
- `IVF::estimate`, lines 318-365, used by analysis tools to collect fast,
  variance, and accurate distances for all scanned candidates.

`IVF::search` first calls:

```cpp
this->initer_->centroids_distances(ori_query, nprobe,
                                   searcher_cfg.dist_type, centroid_dist);
```

The concrete initializer is `FlatInitializer` in
`saqlib/index/initializer.hpp`, lines 52-75. It computes the distance from the
query to every centroid and uses `std::partial_sort` to select the `nprobe`
clusters.

Then `IVF::search` constructs:

```cpp
utils::ResultPool KNNs(topk, searcher_cfg.dist_type == DistType::IP);
SAQSearcher<kDistType> searchers(*saq_data_.get(), searcher_cfg, ori_query);
```

and scans each selected cluster:

```cpp
searchers.searchCluster(&parallel_clusters_[cid], KNNs);
```

### 3. Result Pool / Top-k Boundary

`saqlib/utils/pool.hpp` implements `utils::ResultPool`.

Relevant code:

- `ResultPool::insert`, lines 17-30;
- `ResultPool::distk`, lines 32-34;
- `ResultPool::copy_results`, line 36.

Despite the earlier shorthand "heap update", the current implementation is not
a binary heap. It maintains a sorted fixed-capacity array:

- `distk()` returns the current top-k boundary, or `max_float` before the pool
  is full;
- `insert()` rejects a candidate if the pool is full and the candidate is worse
  than the current boundary;
- otherwise it uses binary search plus `memmove` to keep candidates sorted.

For the next measurement, this stage should be described as "top-k result-pool
maintenance" rather than heap maintenance.

### 4. SAQ Multi-Segment Searcher

`saqlib/quantization/saq_searcher.hpp` is the central search loop.

Relevant code:

- `SAQSearcher::searchCluster`, lines 71-177;
- `SAQSearcher::scanCluster`, lines 256-294, the single-segment path;
- safe block-min helpers, lines 180-254.

For multi-segment SAQ plans, `searchCluster` performs:

1. prepare all segment estimators for the current cluster;
2. scan vectors in blocks of `KFastScanSize = 32`;
3. optionally compute variance-based block estimates;
4. compute fast 1-bit estimates segment by segment;
5. use block minima and current `distk` to stop work on blocks;
6. accurately refine candidates whose current estimate is below `distk`;
7. insert refined candidates into `ResultPool`.

The main pruning condition appears twice:

```cpp
mi = blockMin(curr_dist512, valid_lanes, curr_dist);
if (mi > distk) {
    continue;
}
```

after variance estimation, and:

```cpp
mi = blockMin(curr_dist512, valid_lanes, curr_dist);
if (mi > distk) {
    break;
}
```

inside the segment-by-segment fast-estimation loop.

Accurate refinement is guarded by:

```cpp
if (curr_dist[j] < distk) {
    ...
    acc_dist += estimator.compAccurateDist(idx)
              - clu_dist_[c_i * KFastScanSize + j];
    if (acc_dist >= distk) {
        break;
    }
    ...
    KNNs.insert(saq_clust->ids()[idx], acc_dist);
    distk = KNNs.distk();
}
```

The important research observation is that the searcher already has a staged
structure, but current metrics do not report how often each stage is reached or
which stage dominates runtime.

### 5. Safe Block-Min Logic

Safe block-min mode is controlled by `SearcherConfig`:

- `saqlib/quantization/config.h`, lines 76-80;
- `src/define_options.h`, lines 40-41;
- `src/test_qps.cpp`, lines 255-281.

In `SAQSearcher`, mode selection is normalized by
`normalizeSafeBlockMinMode`, lines 180-187:

```text
mode 0: native AVX512 reduce-min over both 16-lane halves
mode 1: scalar finite min over valid lanes only
mode 2: SIMD finite min over valid lanes only
```

The actual dispatch is `blockMin`, lines 242-254.

This matters because padded or non-finite lanes can otherwise make the block
minimum unsafe. For multi-segment recall/QPS evidence, the reliable mode is:

```text
-searcher_safe_block_min_mode=2
```

### 6. SAQ Segment Aggregation

`saqlib/quantization/saq_estimator.hpp` aggregates per-segment CAQ estimators.

Relevant code:

- constructor and query segmentation, lines 28-47;
- `SaqCluEstimator::prepare`, lines 110-116;
- `SaqCluEstimator::varsEstDist`, lines 127-137;
- `SaqCluEstimator::compFastDist`, lines 148-158;
- `SaqCluEstimator::compAccurateDist`, lines 169-176.

The constructor splits the query according to the dataset-level segment plan.
For each segment it computes a query-dependent variance bound:

```cpp
auto vars2 =
    (data_variance.segment(offset, bdata.num_dim_pad).array()
     * curr_query.array().square()).sum();

estimators_.emplace_back(...).setPruneBound(std::sqrt(vars2));
```

The estimator layer is therefore where SAQ's global segment plan becomes
query-specific pruning state, without learning from a query workload.

### 7. CAQ Fast Estimation And Accurate Refinement

`saqlib/quantization/caq/caq_estimator.hpp` contains the segment-level distance
estimators.

Relevant code for fastscan cluster search:

- `QueryRuntimeMetrics`, lines 21-25;
- `CaqCluEstimator::setPruneBound`, lines 80-82;
- `CaqCluEstimator::prepare`, lines 94-105;
- `CaqCluEstimator::varsEstDist`, lines 116-136;
- `CaqCluEstimator::compFastDist`, lines 148-179;
- `CaqCluEstimator::compAccurateDist`, lines 190-217.

`varsEstDist` computes a cheap conservative distance-like value from residual
norms, query norm, and the variance pruning bound. This is the first block-level
screening stage.

`compFastDist` computes the 1-bit fastscan estimate from short codes and the
query lookup table. If `num_bits_ == 0`, it falls back to `varsEstDist`.

`compAccurateDist` computes the full quantized estimator using the long code
and extension factor. If `num_bits_ == 0`, it returns the norm-only L2
contribution or centroid inner-product contribution.

Existing runtime accounting at this layer:

- `fast_bitsum += KFastScanSize * num_dim_padded_` in `compFastDist`;
- `acc_bitsum += num_dim_padded_ * (num_bits_ - 1)` in `compAccurateDist`.

These are bit-volume proxies, not wall-clock decomposition.

## Existing Metrics

Current query-level metrics are:

| metric | location | interpretation | limitation |
|---|---|---|---|
| `fast_bitsum` | CAQ estimator, aggregated by SAQ searcher | approximate number of fast-stage 1-bit dimension reads | no per-segment or per-stage reach counts |
| `acc_bitsum` | CAQ estimator, aggregated by SAQ searcher | approximate number of higher-bit dimension reads in accurate refinement | no count of refined vectors by segment |
| `total_comp_cnt` | SAQ searcher | `num_blocks * KFastScanSize` for scanned clusters | counts padded lanes and does not distinguish pruned/refined candidates |
| per-query time | `test_qps` | end-to-end per-query elapsed time | no internal timing decomposition |
| QPS / recall | `test_qps` | headline evaluation | cannot explain why QPS changes |

One important code-level detail: in the multi-segment path,
`SAQSearcher::searchCluster` resets `runtime_metrics_.fast_bitsum` and
`runtime_metrics_.acc_bitsum` after each cluster and then re-aggregates from the
estimators. Since the underlying CAQ estimator counters are cumulative across
clusters, the final value after the last searched cluster appears to be the
cumulative query-level total. `total_comp_cnt` is incremented separately for
each cluster. The next instrumentation should preserve this behavior and add
explicit stage counters rather than reinterpret these coarse proxies.

## Missing Measurements

To evaluate the search-procedure direction, the current metrics are
insufficient. The minimal missing counters are:

| category | needed counters | why it matters |
|---|---|---|
| cluster scan volume | clusters probed, blocks visited, valid candidates visited | separates IVF scan breadth from estimator work |
| variance stage | blocks reaching variance stage, blocks pruned after variance stage | evaluates whether the variance bound is useful |
| fast stage | segment fast-estimate calls, blocks pruned after each segment, candidates surviving fast estimates | measures whether segment order / segment cost matters |
| accurate stage | candidate-vector refinement attempts, segment refinements, early exits inside accurate refinement | measures whether full-code reads are concentrated and avoidable |
| result-pool stage | insert attempts, successful insertions, rejected insertions by boundary, boundary updates | measures cost and top-k pressure |
| padded / invalid lanes | last-block valid lanes, finite-min filtered lanes | checks safe-search behavior and avoids padded-lane artifacts |
| timing | centroid selection, estimator preparation, variance stage, fast stage, accurate stage, result-pool maintenance | converts counter evidence into QPS explanation |

The first implementation should not add all possible counters. It should add a
compact, opt-in runtime profile that answers:

```text
Among scanned candidates, how many are removed by variance pruning, by fast
segment pruning, by accurate-refinement early exit, and by top-k insertion?
```

## Work-Decomposition Plan

### Step 1: Add Minimal Runtime Profile Structures

Extend query-time metrics with an optional profile object. Keep existing
`QueryRuntimeMetrics` fields unchanged so prior scripts remain compatible.

Suggested fields:

```text
clusters_scanned
blocks_scanned
valid_lanes_scanned
variance_blocks
variance_pruned_blocks
fast_segment_calls
fast_pruned_blocks
accurate_candidate_attempts
accurate_segment_calls
accurate_segment_early_exits
result_insert_attempts
result_insert_successes
```

Timing should be optional and initially coarse:

```text
centroid_selection_us
cluster_prepare_us
variance_stage_us
fast_stage_us
accurate_stage_us
result_pool_us
```

Rationale: counters are less intrusive than timers and should be added first.
Timers can perturb tight SIMD loops, so they should be enabled only for small
diagnostic runs.

### Step 2: Produce A Single-Query And Aggregate Report

Add a small diagnostic binary or a flag-gated path for:

```text
GIST sample100k, K512, B=4, SAQ default plan,
safe block-min mode 2, R@100, nprobe=200.
```

Report:

- aggregate counts per query;
- distribution across queries, not only the mean;
- the relationship between `distk` becoming finite and pruning effectiveness;
- whether accurate refinement or fast estimation dominates the bit-volume proxy.

Do not introduce a new policy in this step.

### Step 3: Compare Operating Points

Repeat the profile at two or three `nprobe` values around the existing
operating point:

```text
nprobe = 160, 200, 240
```

The purpose is not to optimize nprobe. It is to see whether the work
decomposition is stable or only an artifact of one operating point.

### Step 4: Interpret Against Possible Search-Procedure Mechanisms

Only after the counters are available, answer these questions:

1. If variance pruning removes few blocks, is the bound too loose or is the
   candidate set already too hard?
2. If most blocks survive all fast segments but few candidates enter accurate
   refinement, is segment-level reordering meaningful?
3. If accurate refinement dominates and often exits early after a few segments,
   is there a safe refinement-ordering rule?
4. If result-pool maintenance is negligible, do not optimize it.
5. If top-k boundary becomes finite late, can this be explained by IVF cluster
   ordering rather than segment scheduling?

### Step 5: Stop Or Continue

Continue toward a search-procedure method only if the profile shows a
concentrated, explainable, and recall-safe opportunity, for example:

- many blocks survive early stages but are later removed by a small number of
  expensive segment reads;
- accurate refinement frequently exits before all segments, suggesting a
  principled refinement order could reduce reads;
- safe block-min pruning effectiveness depends strongly on segment order in a
  way that can be derived from existing SAQ bounds.

Stop this direction if:

- most time is spent in unavoidable centroid selection or candidate scanning;
- pruning/refinement work is already low relative to overhead;
- the only improvement path requires arbitrary fitted thresholds;
- any proposed rule cannot be stated as recall-preserving or as an explicit
  approximation tradeoff.

## Immediate Next Task

Implement only the minimal runtime-profile counters needed for Step 1, guarded
so normal QPS runs remain compatible. Then run the Step 2 diagnostic on GIST
sample100k K512 B=4 with safe search.

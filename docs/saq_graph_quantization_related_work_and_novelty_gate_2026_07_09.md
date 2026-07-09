# SAQ Graph Quantization Related-Work and Novelty Gate

## Purpose

This note reviews closely related quantization-plus-graph work before the
branch implements the proposed graph traversal profiler.

The decision is:

```text
Do not frame the direction as "SAQ + graph index" or "quantization for graph
search". SymphonyQG and related work already occupy that space.
```

The only defensible continuation is a narrower SAQ-specific question:

```text
Does SAQ's segmented progressive estimator provide a graph-traversal or
frontier-refinement advantage that RaBitQ/FastScan-style graph quantization
does not already provide?
```

If the first experiment cannot answer that question, the direction should stop
or be reframed before implementation.

## Related Work Reviewed

### SymphonyQG

Primary source:

```text
https://arxiv.org/abs/2411.12229
https://arxiv.org/html/2411.12229
```

SymphonyQG is directly related. It targets graph-based ANN search and explicitly
integrates quantization with graph traversal.

What it already solves:

- It starts from NGT-QG, where each graph vertex stores the quantization codes
  of its neighbors compactly so that a visited vertex can evaluate its outgoing
  neighbors with sequential memory access.
- It uses FastScan to estimate distances for a batch of neighbor codes during
  graph search.
- It replaces PQ in NGT-QG with RaBitQ, motivated by RaBitQ's unbiased distance
  estimator and error bound.
- It addresses a key graph-specific normalization problem: RaBitQ was designed
  around IVF centroids, but graph vertices do not have IVF centroids. SymphonyQG
  uses the current vertex as the normalization center for its neighbors.
- It handles the lookup-table preparation cost created by vertex-specific
  normalization, deriving a form that allows query-side LUTs to be shared more
  broadly.
- It avoids the explicit final reranking stage used by NGT-QG through implicit
  reranking during traversal.
- It uses multiple estimated distances for a vertex during graph search to
  reduce the chance that an over-estimated true nearest neighbor is missed.
- It aligns graph out-degree with FastScan batch size, supplementing graph
  edges so batch computation is not wasted.

Implication for this branch:

```text
SymphonyQG already covers "RaBitQ/FastScan estimated distances guide graph
traversal" and "layout-aware graph quantization".
```

Therefore this branch cannot claim:

- first integration of quantization with graph indexes;
- first use of estimated distances to guide graph traversal;
- first observation that graph traversal is sensitive to approximate distance;
- first graph-specific treatment of RaBitQ/IVF normalization;
- first layout-aware batch evaluation of graph neighbors with quantized codes;
- first avoidance of final reranking in quantized graph search.

### NGT-QG

SymphonyQG describes NGT-QG as the earlier graph-quantization framework it
improves. NGT-QG already:

- duplicates and stores neighbor quantization codes on the side of each vertex;
- scans those codes sequentially during graph search;
- uses FastScan to batch-estimate distances;
- performs explicit reranking using exact raw-vector distances at the end.

Implication:

```text
Even "neighbor-side quantized code layout plus FastScan" is not new.
```

### Routing-Guided Learned Product Quantization

Primary source:

```text
https://arxiv.org/abs/2311.18724
```

Routing-Guided Learned Product Quantization (RPQ) studies graph-aware
quantization from another angle. It argues that standard PQ does not model
proximity-graph routing features, then learns a PQ variant with graph/routing
features and integrates it with DiskANN and other proximity graphs.

What it already solves:

- It treats graph routing behavior as a first-class quantization objective.
- It uses graph-neighborhood and routing features to train the quantizer.
- It evaluates integration with graph indexes at scale.

Implication for this branch:

```text
The broad idea "make quantization aware of graph traversal" is also not new.
```

Because this branch is currently query-unaware and should avoid learned
workload-dependent policies, RPQ is not a direct method template. However, it
is a strong reviewer reference for any claim that graph routing should influence
compressed distance estimation.

## What SAQ Still Adds

SAQ is not just RaBitQ with a different implementation. Its graph-relevant
properties are:

1. **Segmented PCA dimensions.**
   SAQ orders and groups dimensions by PCA variance, then assigns different bit
   widths to different contiguous segments.

2. **Progressive segment-level estimator.**
   SAQ exposes a staged distance path:

   ```text
   variance estimate -> fast 1-bit estimate -> full-bit segment refinement
   ```

3. **Different per-segment bit widths.**
   A graph traversal policy could choose whether to refine high-bit,
   high-variance segments before low-bit or zero-tail segments.

4. **SAQ code layout is currently IVF-residual coded.**
   Existing SAQ implementation uses residuals around IVF centroids. Graph
   traversal has no natural IVF cluster as the visited-vertex reference unless
   we keep IVF residual metadata or redesign the graph-side code layout.

These properties create a narrower possible contribution:

```text
SAQ may support a traversal-aware progressive refinement policy that ranks or
stabilizes graph frontier candidates with less code access than a single-stage
RaBitQ/FastScan estimate.
```

This is a hypothesis, not a result.

## Required Reframing

The current graph traversal measurement design should be reframed.

Old framing:

```text
Does SAQ approximate distance change graph frontier order compared with exact
float distance?
```

This is insufficient because SymphonyQG already studies graph traversal guided
by estimated quantized distances.

New framing:

```text
Compared with a RaBitQ/FastScan-style single-stage graph estimator, does SAQ's
segmented progressive estimator offer a better refinement/work tradeoff for
frontier-stable graph traversal?
```

This reframing changes the first experiment. It is no longer enough to compare:

```text
exact_float vs saq_full vs saq_fast vs saq_var
```

The first experiment also needs a conceptual or implemented baseline:

```text
exact_float vs rabitq_or_symphonyqg_style_estimate vs saq_staged_estimates
```

If a direct SymphonyQG implementation is not available, the profiler should at
least define a RaBitQ/FastScan-style baseline in the same offline replay:

- one global or vertex-centered 1-bit RaBitQ-style estimate;
- no SAQ segment-level progressive refinement;
- same fixed adjacency and same exact-float expansion events;
- same rank-containment metrics.

Without this baseline, the experiment can only show that SAQ approximation
differs from exact distance, which is not a sufficient novelty argument.

## Candidate SAQ-Specific Gaps

The following are the only currently plausible gaps. Each must be falsified
early.

### Gap A: Progressive Refinement Beyond Multiple RaBitQ Estimates

SymphonyQG uses multiple estimated distances to reduce the chance of missing a
true nearest neighbor. SAQ may offer a different refinement axis: one candidate
can be refined progressively through segment/bit stages.

Potential contribution:

```text
A graph frontier policy that refines ambiguous candidates through SAQ segments
instead of inserting multiple independent estimates for the same candidate.
```

Required evidence:

- SAQ staged estimates recover exact-frontier ordering with fewer code reads or
  fewer candidate entries than the RaBitQ-style baseline;
- the policy does not require fitted query thresholds;
- the overhead of segment/factor reads is accounted for.

### Gap B: Segment-Aware Frontier Uncertainty

SAQ has segment-level variance and bit-width information. A frontier candidate
could carry an uncertainty interval derived from the remaining unrefined
segments.

Potential contribution:

```text
A segment-derived uncertainty criterion for deciding when graph frontier
candidates need further refinement.
```

Required evidence:

- the interval or criterion is derived from SAQ quantities, not calibrated from
  query recall;
- it is tighter or cheaper than using a full RaBitQ-style estimate;
- it changes traversal work without hiding exact-vector reranking cost.

### Gap C: Layout and Reference Mismatch for SAQ on Graphs

SymphonyQG solves a graph-specific RaBitQ normalization problem by using the
visited vertex as the center for neighbor codes and then reducing LUT overhead.
SAQ currently uses IVF residual centroids and stores cluster-packed codes.

Potential contribution:

```text
A study showing whether SAQ should use IVF-residual, global-reference, or
vertex-centered segmented codes in graph traversal, with explicit metadata and
estimator-setup accounting.
```

Required evidence:

- current IVF-residual SAQ frontiers touch many residual-reference clusters, or
  estimator preparation becomes a real overhead;
- a graph-side SAQ layout has a clear advantage over simply using SymphonyQG's
  RaBitQ/FastScan layout;
- duplicated neighbor-side SAQ segment codes do not create prohibitive memory
  overhead.

This gap is potentially important, but it is also the most implementation-heavy.
It should not be pursued before a smaller replay shows that SAQ estimates have
a useful graph-specific behavior.

## Claims That Are Not Allowed

Do not claim:

- SAQ would be the first quantizer integrated with graph ANN;
- quantized graph traversal is unexplored;
- estimated distances in graph traversal are a new idea;
- neighbor-side compact code layout is new;
- final reranking avoidance is new;
- graph out-degree alignment with SIMD batch size is new;
- a SAQ graph implementation is publishable if it only swaps RaBitQ for SAQ.

These claims are already challenged by SymphonyQG, NGT-QG, and graph-aware
quantization work such as RPQ.

## Revised First Experiment

Before implementing the local expansion profiler, revise its target.

### Required Baselines

The profiler should compare at least:

1. `exact_float`
   - exact L2 distance.
2. `rabitq_style`
   - a single-stage RaBitQ/SymphonyQG-style quantized estimate, or a clearly
     documented approximation of that estimator if a full implementation is not
     available.
3. `saq_fast`
   - SAQ's cheap 1-bit estimate.
4. `saq_full`
   - SAQ's full quantized estimate.
5. `saq_progressive_curve`
   - rank recovery as more SAQ segment/bit information is refined.

### Required Metrics

Report:

- rank of the exact-best neighbor under each estimate;
- top-L containment curves for each estimate;
- refinement work needed to recover the exact-best expansion;
- compressed-code bytes or bit reads per expansion event;
- number of candidate entries inserted into the frontier;
- residual-reference or vertex-reference metadata touched;
- whether SAQ's progressive curve dominates the RaBitQ-style estimate in any
  meaningful work/rank regime.

### Pass Condition

Continue only if:

```text
SAQ's segmented progressive estimates provide a stable rank-recovery or
work-reduction advantage over the RaBitQ/SymphonyQG-style baseline.
```

### Stop Condition

Stop or pivot if:

- SAQ is no better than the RaBitQ-style baseline on frontier rank recovery;
- SAQ requires substantially more metadata or code reads for comparable
  stability;
- any advantage appears only after using fitted thresholds;
- the strongest result is merely "SAQ can be plugged into graph search".

## Immediate Decision

The previous design note remains useful as a measurement skeleton, but it is
not sufficient for a research contribution.

Next step:

```text
Revise or implement the first profiler with a RaBitQ/SymphonyQG-style baseline
and SAQ progressive-refinement accounting. Do not run an SAQ-only graph replay.
```

This is the novelty gate for the graph-index direction.

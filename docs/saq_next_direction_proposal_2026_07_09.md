# SAQ Next-Direction Proposal

## Decision

Recommended next direction:

```text
Search-procedure / estimator-scheduling integration.
```

Do not continue the one-global-plan objective line as the main method. The
planner-objective synthesis shows that static segment cost, measured CAQ
estimator error, and earlier local-plan variants can change speed/space tradeoffs
but do not yet produce recall-matched improvement. The next direction should
therefore target the search procedure itself: when and how SAQ spends work
during progressive estimation, pruning, and accurate refinement.

This proposal does not approve implementation yet. It defines the first
review-and-measurement step needed before code.

## Direction Comparison

| direction | novelty potential | overhead risk | first evidence needed | strict-reviewer risk | decision |
|---|---|---|---|---|---|
| Query-unaware boundary-stability diagnosis | Medium | Medium | Show a low-parameter data-only signal that predicts recall loss better than previous scorers | May look like revived empirical scoring rules | Keep as supporting analysis, not main path |
| Search-procedure / estimator-scheduling integration | Medium to high | Medium | Show that current SAQ search spends measurable work in stages that can be reordered or skipped without changing recall | May look like systems engineering unless tied to SAQ's estimator structure | Recommended |
| Graph-index compatibility gap | High | High | Review SAQ estimator assumptions under graph traversal and identify a concrete failure or opportunity | Too broad; large implementation before evidence | Defer until search-procedure review is understood |

The recommended direction is the most balanced. It is more novel than another
static planner objective, but it is still close enough to the current code and
evidence to support a small falsifiable first study.

## Challenged SAQ Assumption

The new direction challenges this assumption:

```text
Given a fixed SAQ segment plan, the existing multi-stage distance estimator is
already an efficient way to spend query-time work.
```

The previous failures suggest that plan changes alone are too weak. However,
they also show that plan shape affects QPS significantly. The fac-error GIST
plan was 1.34x faster at the same nprobe because it changed the segment layout,
but recall dropped. This points to a search-procedure question:

```text
Can SAQ use its existing segment structure more adaptively during search,
without changing the global plan or learning from representative queries?
```

This is not the old fixed-policy planner problem. The plan can remain SAQ's
default. The research target becomes the estimator schedule and pruning path.

## Why This Is Not Parameter Tuning

A planner-objective tweak changes which dimensions receive bits. A
search-procedure contribution would instead change the execution policy:

- which estimator stage is computed first;
- when the searcher uses a cheap lower-confidence estimate;
- when accurate segment refinement is triggered;
- whether safe block-min pruning can avoid reading some segment codes;
- how runtime work is distributed across candidate blocks.

These are algorithmic/search-system decisions. They can be evaluated with
work decomposition and recall-preserving invariants, not by selecting a better
plan from a large empirical candidate set.

The method must avoid arbitrary thresholds. If a threshold is needed, it should
come from an existing SAQ bound, a safe inequality, or a fixed recall-preserving
rule. Otherwise the direction risks becoming another empirical scorer.

## Expected Overhead Model

The overhead should be measured in the query path, not as an offline planner
cost:

```text
query_time = centroid_scan_or_init
           + fast_stage_estimation
           + accurate_stage_refinement
           + pruning / heap maintenance
           + memory reads for codes and factors
```

The first study should report:

- number of candidate vectors visited;
- number of fast estimates computed;
- number of accurate refinements computed;
- fast-stage bit volume;
- accurate-stage bit volume;
- factor loads;
- total query time and QPS;
- recall under safe search.

This is a work-decomposition study, not a new method yet.

## First Falsifiable Experiment

First experiment:

```text
Instrument SAQ search on default GIST sample100k K512 B=4 and full GIST K4096
B=4 to measure where query-time work is spent across estimator stages under
safe search.
```

Required outputs:

1. A per-query and aggregate breakdown of candidate blocks, fast estimates,
   accurate refinements, bit volume, factor loads, and elapsed time.
2. A comparison across at least two nprobe values, including the operating point
   used in the recent GIST check.
3. A diagnosis of whether most time is spent in unavoidable candidate scanning,
   fast-stage estimation, accurate refinement, or metadata/factor work.
4. A yes/no decision on whether there is a plausible schedule-level
   intervention.

Stop immediately if the decomposition shows no concentrated avoidable work. In
that case, search-procedure integration is not a good main direction.

## Possible Mechanisms After The First Study

Do not implement these before the decomposition study. They are only examples
of mechanisms that would be defensible if the evidence supports them.

### Mechanism 1: Recall-Preserving Refinement Ordering

If accurate refinement dominates, reorder refinement so that candidates most
likely to affect the top-k boundary are refined first. This must be based on a
safe or monotone bound, not a learned query workload.

### Mechanism 2: Segment-Level Work Skipping

If some late segments are frequently computed for candidates that cannot enter
top-k, derive a safe condition for skipping them. The condition must preserve
recall or expose an explicit approximation bound.

### Mechanism 3: Bound Calibration Without Query Learning

If SAQ's current bound is systematically loose, use data-only distributional
statistics to tighten it. This is risky because it can become empirical
calibration. It is only acceptable if the statistic has a clear derivation and
does not use benchmark queries for fitting.

## Why Not Direction A First

Boundary-stability diagnosis is intellectually close to the failure mode, but
it risks recreating the old fixed-policy scorer line. The previous branch
already showed that data-only boundary-like signals can select plans, but the
resulting approach looked empirical and had weak novelty.

Direction A should remain a supporting analysis for Direction B:

```text
Use boundary-stability measurements to explain search-procedure behavior, not
to generate another custom plan family.
```

## Why Not Direction C First

Graph-index compatibility may have the highest novelty, because SAQ's segmented
progressive estimator was developed and evaluated mainly around IVF-style
candidate filtering. However, jumping directly to HNSW or DiskANN introduces a
large implementation surface and several confounders:

- graph traversal quality depends on expansion order;
- approximate distances can change the search path, not just final filtering;
- graph index implementations have their own pruning and memory layouts;
- integrating SAQ codes may require substantial engineering before the first
  research signal.

Direction C should be revisited after the SAQ search-procedure decomposition.
If the decomposition identifies a clear estimator-scheduling issue, the same
issue can later be studied in graph traversal.

## Strict-Reviewer Objection

A strict reviewer may say:

```text
This is only an implementation optimization of SAQ's search loop, not a new
database research contribution.
```

The response must be evidence-based. The direction becomes research-worthy only
if the first study shows a structural mismatch between SAQ's progressive
estimator and actual query-time work, and the later method provides a
principled recall-preserving or bound-controlled schedule. If the result is only
micro-optimization, this direction should stop.

## Stop Condition

Stop this direction if any of the following occurs:

- work decomposition shows no concentrated avoidable work;
- a proposed schedule requires arbitrary fitted thresholds;
- recall preservation cannot be stated as a safe rule or clear approximation
  tradeoff;
- QPS gains are smaller than measurement noise or disappear under
  recall-matched evaluation;
- implementation complexity becomes the main contribution.

## Immediate Next Step

Write and run no new search policy yet. First perform a code-level review of
SAQ's search path and produce a work-decomposition plan:

- locate where fast estimation, accurate refinement, safe block-min logic, and
  runtime metrics are implemented;
- identify which counters already exist and which counters are missing;
- define the minimal instrumentation needed for GIST sample100k K512 B=4;
- state exactly what observation would justify a schedule-level method.

Only after that review should instrumentation code be added.

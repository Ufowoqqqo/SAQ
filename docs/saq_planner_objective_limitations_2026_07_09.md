# SAQ Planner-Objective Limitation Synthesis

## Purpose

This note synthesizes the negative evidence collected after the branch pivoted
back to a clean query-unaware SAQ follow-up. The goal is not to rescue a local
planner tweak. The goal is to decide what SAQ limitation remains defensible
after several plausible one-global-plan objectives failed to produce a
recall-matched improvement.

The current evidence should be read under the project constraints:

- no representative query workload for learning;
- one dataset-level global segment/bit plan;
- no per-cluster plan ids or mixed-plan query dispatch;
- safe-search evaluation for recall/QPS claims;
- paper-facing standards for novelty, overhead, and reviewer defensibility.

## Evidence Summary

| direction | hypothesis | strongest positive signal | end-to-end outcome | interpretation |
|---|---|---|---|---|
| Mixed shared local plans | IVF-local residual structure may benefit from different shared plans | Some local plans improved recall in earlier experiments | Multi-plan estimator/search overhead dominated the benefit | Useful systems limitation: local plan diversity is costly unless estimator dispatch is redesigned |
| Static segment-cost global DP | SAQ's variance DP may ignore search-time segment cost | Lower-cost near-frontier plans existed | Full GIST/K4096 B=4 near-frontier plans were slower than default under safe search | Simple static cost terms are not reliable search-time models |
| Data-only planner-proxy measurement | SAQ variance risk may not match measured quantization error | Direction-only loss was not well ranked by variance risk | Raw/aligned SSE were strongly ranked by SAQ proxy across datasets | SAQ's variance objective is already strong for energy-weighted residual error |
| Direct fac-error DP | CAQ estimator-error measurement may produce a better global objective | B=4 fac-error DP changed GIST/CIFAR plans and selected a faster/smaller GIST plan | GIST B=4 custom plan failed recall-matched QPS comparison | Direct estimator-error cost moves plan shape, but does not preserve ranking recall |

The most important numerical result is the GIST sample100k B=4 recall-matched
check. At the same nprobe, the fac-error plan was 1.34x faster and 4.7% smaller
than SAQ default, but R@100 dropped from 0.99132 to 0.99059. Raising custom
`nprobe` up to the QPS break-even point did not recover the default R@100:

| plan | nprobe | R@100 | QPS | QPS vs default |
|---|---:|---:|---:|---:|
| SAQ variance | 200 | 0.99132 | 9215.208 | 1.000x |
| fac-error | 200 | 0.99059 | 12334.094 | 1.338x |
| fac-error | 280 | 0.99091 | 9875.544 | 1.072x |
| fac-error | 300 | 0.99091 | 9422.062 | 1.022x |
| fac-error | 320 | 0.99091 | 8956.573 | 0.972x |

This is the stopping evidence for the current fac-error objective.

## What Failed

The common failed assumption is:

```text
A better query-unaware segment-level objective should translate into a better
one-global-plan search/retrieval tradeoff.
```

The experiments suggest that this assumption is too weak for a paper-level
method. Three different objective families all miss the same issue:

1. **Segment reconstruction or estimator error is not top-k boundary error.**
   SAQ's search quality depends on whether approximate distances preserve the
   ordering around IVF candidate boundaries and final top-k replacement
   thresholds. A segment can reduce average absolute estimator error while
   still damaging exactly the candidates that determine recall.

2. **Static search cost is not realized search cost.**
   Reducing positive dimensions, code volume, or segment count does not
   necessarily reduce safe-search latency after pruning, accurate refinement,
   block-min behavior, factor loading, and zero-tail placement interact.

3. **One global plan has limited degrees of freedom.**
   Under query-unaware constraints, a single dataset-level plan must serve all
   clusters and query regions. SAQ's default variance DP already captures much
   of the globally stable energy allocation. Local improvements are possible,
   but the mixed-plan evidence shows that using them naively creates query-time
   overhead.

4. **Measured CAQ fac-error is too close to the estimator analysis to be novel
   by itself.**
   It is useful evidence, but a strict reviewer can frame it as remeasuring
   CAQ's own error factor offline. Without recall-matched improvement, it is
   not a contribution.

## Current Contribution Level

The current contribution is not a new quantizer and not a better SAQ planner.
It is a limitation analysis:

```text
Under a one-global-plan, query-unaware constraint, SAQ's default variance
planner is hard to improve with simple data-only segment objectives. Objectives
that are closer to CAQ estimator error can change the plan and expose
speed/space tradeoffs, but the first recall-matched check fails.
```

This is useful for a meeting and possibly for motivating a stronger follow-up,
but it is not yet enough for a SIGMOD/VLDB/ICDE full-paper contribution. A
paper-level next step needs a mechanism that directly addresses ranking
stability or search execution, rather than another scalar segment-cost proxy.

## Strict-Reviewer Review

A strict reviewer would likely raise the following objections if we submitted
the current planner-objective story as a method:

- **Novelty:** replacing `variance_sum / 2^bits` with measured CAQ error looks
  like objective tuning around SAQ, not a new quantization principle.
- **Overhead:** measuring fac-error over all segment/bit candidates adds offline
  cost. Without a recall-matched win, the overhead is unjustified.
- **Evidence:** GIST is the only end-to-end fac-error check so far, and it is
  negative under recall matching.
- **Mechanism:** the method does not explain why top-k ranking boundaries should
  be preserved.
- **Generality:** audio, DEEP, and word2vec did not even change plan at B=4 in
  the fac-error DP falsification.

These objections are strong enough that broadening fac-error sweeps would look
post-hoc unless a new mechanism is introduced first.

## Surviving Research Question

The surviving question is no longer "which scalar objective should replace SAQ
variance risk?" A better formulation is:

```text
What query-unaware information can predict whether a SAQ plan change preserves
top-k ranking boundaries, rather than merely reducing segment-level error or
static cost?
```

This reframes the problem from global reconstruction quality to retrieval
stability. It also explains why previous directions failed: none of them
directly measured or modeled boundary stability.

## Candidate Next Directions

These are candidate research directions, not approved implementation tasks.
Each needs a separate strict-reviewer check before code.

### Direction A: Query-Unaware Boundary-Stability Diagnosis

Use only base/index artifacts to study data-data replacement boundaries inside
IVF clusters. The goal would not be the old handcrafted scorer. The goal would
be a principled limitation analysis:

```text
When SAQ changes a global segment plan, which data-only cluster geometry
predicts whether near-boundary candidate orderings become unstable?
```

This direction is risky because it can drift back into empirical scorer design.
It is only worth pursuing if the first study produces a clear, low-parameter
mechanism.

### Direction B: Search-Procedure Integration

Stop trying to beat SAQ by changing only the static global plan. Instead, study
where SAQ's progressive estimator loses useful work during IVF or graph search.
The contribution would need to be a search algorithm or estimator scheduling
change, not a new plan objective.

This is closer to a systems contribution, but it must still avoid query-aware
training and must report overhead carefully.

### Direction C: Graph-Index Compatibility Gap

SAQ is evaluated primarily in an IVF setting. A stronger follow-up may study
whether SAQ's segmented progressive estimator can be used safely in HNSW or
DiskANN-style traversal, where early approximate distances affect expansion
order rather than only candidate filtering.

This direction is larger and likely more novel, but it should start with a
paper/source-code review before implementation.

## Decision

Stop the current planner-objective modification line as a main method. Keep the
measurement tools and custom-plan hook for controlled ablations, but do not
continue broad fac-error, static-cost, or local-candidate sweeps.

The next action should be a short proposal note that chooses between the
surviving directions above. That proposal must include:

- the SAQ assumption being challenged;
- why the direction is not just parameter tuning;
- expected overhead;
- first falsifiable experiment;
- strict-reviewer objection;
- stop condition.

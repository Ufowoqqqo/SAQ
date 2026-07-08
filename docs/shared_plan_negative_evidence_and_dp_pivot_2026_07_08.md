# Shared-Plan Negative Evidence And Global-DP Pivot

Date: 2026-07-08

## Decision

Stop treating mixed shared local SAQ plans as the main research direction.
Preserve the results as negative evidence and pivot to a single-global-plan
segment-cost-aware DP direction.

The new direction should keep SAQ's one-plan search architecture:

```text
one dataset-level segment/bit plan
one query-side estimator/searcher state
no per-query mixed-plan dispatch
```

This avoids the main overhead observed in the shared-plan prototype while still
testing the broader limitation suggested by the experiments:

```text
SAQ's variance-driven planner does not explicitly optimize search-time cost.
```

## Evidence From Mixed Shared Local Plans

The mixed shared-plan line tested whether IVF-local residual structure can
improve SAQ's one global plan. On `GIST full / K4096 / B=4`, the residual-local
signal was real but too small to overcome mixed-plan overhead.

| index | R@100 | QPS | QPS ratio | index size |
|---|---:|---:|---:|---:|
| SAQ default | 0.94469 | 2677.16 | 1.0000 | 570M |
| shared local M4 | 0.94548 | 2434.73 | 0.9094 | 573M |
| cost-aware M4 | 0.94485 | 2398.13 | 0.8958 | 567M |

The static cost analysis showed that segment count was not a reliable proxy:

| index | residual proxy ratio | fast volume ratio | accurate volume ratio | segment proxy ratio |
|---|---:|---:|---:|---:|
| shared local M4 | 0.9435 | 0.9750 | 1.0000 | 0.9995 |
| cost-aware M4 | 1.0245 | 0.9973 | 1.0038 | 0.9286 |

The runtime decomposition was more decisive. Both shared variants reduced
nominal scan/refinement work, but still lost QPS:

| index | fast bit ratio | accurate bit ratio | accurate segment eval ratio | distinct plans/query |
|---|---:|---:|---:|---:|
| shared local M4 | 0.9741 | 0.9097 | 0.9853 | 2.907 |
| cost-aware M4 | 0.9547 | 0.8809 | 0.8989 | 3.336 |

This means the QPS loss is not explained by more measured distance work. The
more plausible explanation is mixed-plan overhead:

- multiple plan-specific query-side searchers per query;
- separate estimator state and pruning-bound setup;
- separate lookup-table preparation paths;
- worse cache and layout locality when one query visits clusters with different
  plans.

## What To Keep

The mixed shared-plan results are still useful, but their role is narrower:

```text
SAQ's global plan can be locally mismatched with IVF residual structure, but
naively materializing multiple local plans introduces search-time overhead that
can dominate the residual benefit.
```

This can motivate a broader question:

```text
Can SAQ's single global planner account for search-time cost without adding
mixed-plan query overhead?
```

It should not be presented as a successful method or as evidence that local
shared plans improve SAQ's system tradeoff.

## New Main Direction

The next main direction is **single-global-plan segment-cost-aware DP**.

Targeted SAQ assumption:

```text
SAQ's DP optimizes a variance-based quantization-risk proxy, but the search
path also depends on positive dimensional volume, bit volume, segment count,
zero-tail behavior, and multi-stage pruning/refinement cost.
```

Constraint:

```text
Keep one global plan. Do not introduce per-cluster plan ids or mixed-plan
search dispatch.
```

Possible contribution:

```text
An implementation-derived global planner or Pareto frontier that exposes when
SAQ's variance-only plan is search-cost inefficient, while preserving SAQ's
simple index/search architecture.
```

## Immediate Study Before Any New Index Build

Start offline. Reproduce SAQ's global DP and produce a deterministic
risk-vs-cost frontier for existing datasets and bit budgets.

The first study should compare candidate global plans under:

- SAQ residual/variance risk objective;
- fast dimensional volume;
- accurate bit volume;
- positive segment count;
- zero-tail residual mass;
- expected segment metadata/factor overhead.

This study should answer:

1. Is SAQ's default global plan far from a risk-cost Pareto frontier?
2. Are there global plans with nearly identical risk but meaningfully lower
   implementation-derived cost?
3. Does the answer hold beyond GIST, or is it dataset-specific?
4. Can the objective avoid unjustified free hyperparameters?

## Stop Condition

Stop or downgrade this direction if the offline frontier shows that:

- SAQ's default plan is already near the risk-cost frontier;
- lower-cost global plans have visibly worse residual risk;
- any positive result depends on an arbitrary lambda or dataset-specific knob;
- predicted cost reductions fail to match runtime decomposition counters.

Only after passing this offline test should we build a new index and run
held-out query evaluation.

## Relevant Artifacts

Shared-plan end-to-end result:

```text
docs/gist_shared_plan_end_to_end_2026_07_08.md
```

Static cost analysis:

```text
docs/gist_shared_plan_static_cost_analysis_2026_07_08.md
```

Runtime decomposition:

```text
docs/gist_shared_plan_runtime_decomposition_2026_07_08.md
```

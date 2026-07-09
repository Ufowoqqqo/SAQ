# GIST Sample100K SAQ Runtime-Profile Evidence

## Purpose

This note records the first runtime-profile measurement for the search-procedure
direction. The goal is not to propose a new search policy. The goal is to
measure where the current SAQ search path spends query-time work under the
default plan.

Research question:

```text
Does the current SAQ search path expose a concentrated, explainable source of
avoidable work that could justify a principled estimator-scheduling method?
```

## Setup

Dataset and index:

```text
dataset = gist_sample100k
K = 512
B = 4
PCA = true
plan = SAQ default variance plan
plan shape = 64x11_192x6_320x4_256x2_128x0
top-k = 100
threads = 24
searcher_vars_bound_m = 4
safe search = -searcher_safe_block_min_mode=2
```

The profile was run at three operating points:

```text
nprobe = 160, 200, 240
```

The new runtime-profile counters were printed with:

```text
-print_runtime_profile=true
```

Logs are local artifacts under:

```text
/tmp/saq-run/runtime_profile/
```

## Headline Results

| nprobe | R@100 | QPS | avg query time | scanned candidates / query | accurate candidates / query |
|---:|---:|---:|---:|---:|---:|
| 160 | 0.99036 | 10119.473 | 2.3719 ms | 37339.7 | 2696.3 |
| 200 | 0.99132 | 9192.221 | 2.6111 ms | 45810.0 | 2767.4 |
| 240 | 0.99153 | 8183.555 | 2.9328 ms | 54044.2 | 2805.3 |

The profile counters are deterministic across the repeated QPS rounds. QPS
varies normally across rounds, but the query-level work counts are identical.

## Profile Counters

All values below are per-query averages.

| nprobe | clusters | blocks | variance-pruned blocks | fast-pruned blocks | fast segment calls | accurate candidates | accurate segment calls | accurate early exits | result-pool successes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 160 | 160 | 1245.45 | 1.75 | 563.21 | 3615.43 | 2696.29 | 4657.23 | 2262.40 | 430.36 |
| 200 | 200 | 1530.01 | 4.10 | 793.82 | 4134.88 | 2767.44 | 4729.46 | 2333.40 | 430.50 |
| 240 | 240 | 1807.10 | 8.17 | 1036.46 | 4563.87 | 2805.26 | 4767.56 | 2371.19 | 430.54 |

Derived ratios:

| nprobe | variance-pruned / blocks | fast-pruned / post-variance blocks | accurate candidates / scanned candidates | accurate calls / accurate candidate | early exits / accurate candidate | result successes / accurate candidate |
|---:|---:|---:|---:|---:|---:|---:|
| 160 | 0.14% | 45.29% | 7.22% | 1.73 | 83.91% | 15.96% |
| 200 | 0.27% | 52.02% | 6.04% | 1.71 | 84.32% | 15.55% |
| 240 | 0.45% | 57.60% | 5.19% | 1.70 | 84.52% | 15.35% |

The default B=4 plan has four positive-bit segments and one zero-bit tail. If
every post-variance block evaluated all positive-bit segments, the fast stage
would require approximately:

```text
4 * (blocks - variance_pruned_blocks)
```

fast segment calls per query. The observed fast segment calls are lower because
many blocks are removed during segment-by-segment fast estimation.

| nprobe | no-prune fast calls | observed fast calls | avoided fast calls |
|---:|---:|---:|---:|
| 160 | 4974.8 | 3615.4 | 27.32% |
| 200 | 6103.6 | 4134.9 | 32.25% |
| 240 | 7195.7 | 4563.9 | 36.58% |

## Interpretation

### 1. Variance pruning is almost inactive

The variance stage prunes less than 0.5% of scanned blocks across all three
nprobe values. This suggests that, at this operating point, SAQ's variance
bound is not the main work-saving mechanism.

This is useful evidence because it weakens a direction based only on tightening
the existing variance-bound stage. There may still be a bound-calibration
question, but this first profile does not show a large immediate opportunity
there.

### 2. Fast-stage pruning is the dominant block-level filter

The fast stage prunes 45-58% of post-variance blocks. The pruning fraction
increases as nprobe grows, which is plausible: later clusters are less likely
to contain vectors that can beat the current top-k boundary.

This is the strongest positive signal for the search-procedure direction. The
current search path already spends work progressively across positive-bit
segments, and a large number of blocks are removed before accurate refinement.

However, this does not yet imply that a new schedule will help. The current
segment order follows the SAQ plan order, which also follows PCA variance
priority. A new rule would need to show why a different segment order or
different bound use is recall-preserving or has an explicit approximation
tradeoff.

### 3. Accurate refinement reaches few scanned candidates

Only 5-7% of scanned candidates enter accurate refinement. This means the
current fast-stage filter is already effective at reducing full-code reads.

For the nprobe=200 operating point:

```text
scanned candidates / query = 45810.0
accurate candidates / query = 2767.4
```

This weakens a story that focuses only on reducing the number of candidates
that enter accurate refinement. The candidate count is not tiny, but it is
already a small fraction of the scanned candidate volume.

### 4. Accurate refinement already exits early

Among candidates that enter accurate refinement, roughly 84% exit before all
positive-bit segments are evaluated. The average number of accurate segment
calls per refined candidate is about 1.7, far below the four positive-bit
segments in the default plan.

This is an important mixed signal:

- positive: there is meaningful segment-level short-circuiting inside accurate
  refinement;
- negative: the current implementation may already capture much of the obvious
  refinement-skipping opportunity.

A future refinement-ordering method would need to show that the current PCA
segment order is systematically suboptimal for early exit. This should be
tested with a counterfactual analysis before changing the query path.

### 5. Result-pool maintenance is unlikely to be the main bottleneck

The result pool accepts only about 430 candidates per query across all nprobe
values. The number is stable because it reflects the number of candidates that
actually enter or replace the fixed-capacity top-k pool during search.

This suggests that top-k result-pool maintenance should not be the first target.
The larger work sources are scanned blocks, fast segment calls, and accurate
segment calls.

## Decision

The search-procedure direction is not disproved, but the next step should be
more specific than "optimize search":

```text
Analyze whether the current segment order is already near-optimal for
block-level fast pruning and accurate-refinement early exit.
```

The current profile supports a focused counterfactual study:

1. Keep the same default SAQ index and plan.
2. Do not change returned results yet.
3. Replay or instrument alternative segment orders only as an analysis path.
4. Measure whether another query-unaware order would reduce fast segment calls
   or accurate segment calls without weakening the pruning condition.

If no order has a clear advantage, the search-procedure direction should stop.
If a simple data-only ordering rule consistently predicts lower work under the
same safety condition, then estimator scheduling may still be a viable
contribution.

## Commands

The three runs used:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -fix_nprobe=<160|200|240> \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -print_runtime_profile=true
```

They were run from:

```text
/tmp/saq-run
```

because `test_qps` reads `./data/<dataset>` and writes `./results/saq/`.

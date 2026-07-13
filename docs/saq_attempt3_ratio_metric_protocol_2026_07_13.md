# Attempt 3: Frozen `1/Ratio@k` Retrospective Protocol

Date: 2026-07-13

## Status

```text
PROTOCOL_FROZEN_BEFORE_EVALUATOR_IMPLEMENTATION
```

This protocol authorizes evaluation only. It does not authorize plan fitting,
candidate generation, search-policy changes, or a metric-aware method.

## Research Question

```text
Does paper-exact distance quality change the Pareto interpretation of any
previously frozen SAQ comparison, after both the baseline and alternative are
evaluated over the same search-effort grid?
```

## Metric Definition

For each query `q`, compute exact Euclidean distances for:

1. the exact top-`k` identifiers, sorted by true Euclidean distance; and
2. the `k` distinct returned identifiers, sorted independently by true
   Euclidean distance.

Then compute

```text
inverse_ratio_at_k(q) =
    k / sum_{i=1}^k returned_distance_i(q) / exact_distance_i(q).
```

Report the arithmetic mean across queries, together with query-level minimum,
`p01`, `p05`, median, `p95`, and maximum. Report Recall@`k` on the same rows.

## Mandatory Semantics

1. SAQ's internal distances are squared L2. Take the square root before
   forming ratios; a ratio of squared distances is not the paper's metric.
2. Sort returned identifiers by recomputed true distance, not by the
   approximate score or output order.
3. Require exactly `k` valid, distinct identifiers for both sets.
4. Reject non-finite coordinates or distances.
5. If any exact position distance is zero, stop that evaluation with an
   explicit diagnostic. Do not introduce an epsilon or silently exclude the
   query; the paper does not define this edge case.
6. Use float64 accumulation for exact squared distances and the ratio sum.
7. Do not clip a result into `(0,1]`. A value above `1 + 1e-12` indicates an
   input, ground-truth, ordering, or arithmetic error and must stop the run.
8. Preserve query-level values in the output artifact.

## Evaluation Unit

One row is

```text
(dataset, index method, representation/plan, bit budget, search setting,
 k, Recall@k, mean 1/Ratio@k, QPS, work counters, build bytes).
```

One metric value per plan is insufficient because search effort changes both
quality and QPS. The scientific object is the operating-point curve.

## Frozen Stage A3-0: Evaluator Validation

The evaluator must pass deterministic fixtures covering:

1. exact returned identifiers, score `1`;
2. disjoint identifiers with equal per-position distances, score `1`;
3. a hand-computed nontrivial ratio;
4. returned IDs supplied in approximate-score order but reordered by true
   distance;
5. Euclidean versus squared-L2 distinction;
6. duplicate, negative, and out-of-range identifiers;
7. `k` mismatch and truncated rows;
8. non-finite inputs;
9. exact zero-distance stop; and
10. deterministic query-level aggregate statistics.

## Frozen Stage A3-1: Smallest Retrospective Comparison

Run `gist_sample100k`, `K=512`, `B=4`, top-100 only. This is the smallest
setting because it is the exact frozen setting that produced the historical
fac-error recall/QPS comparison; the recorded numbers do not come from full
GIST/K4096.

```text
representations:
  SAQ default global plan
  frozen fac-error global plan

initial search grid:
  nprobe in {200, 220, 240, 280, 300, 320}

metrics:
  Recall@100
  mean and query-level distribution of 1/Ratio@100
  QPS
  existing safe-search work counters when available
```

If the historical artifacts do not preserve returned identifiers, rerun the
unchanged search binaries with an output-only result-ID export. Do not change
the index, estimator, pruning, heap, search grid, or thread configuration.

### A3-1a range-sufficiency check

Before interpreting a Pareto change, verify that both measured curves cover the
quality range where either method could be selected. The recovery grid starts
at `nprobe=200`, so it can be insufficient under a metric whose main purpose is
to expose lower-effort operating points.

If either curve is left-truncated in the overlapping `1/Ratio` range, classify
A3-1a as `INSUFFICIENT_FRONTIER_SUPPORT`; do not claim a reversal from it.

### A3-1b corrected historical-union grid

For that range-sufficiency failure only, run both plans on the following grid:

```text
nprobe in {20, 50, 100, 160, 200, 220, 240, 280, 300, 320, 400}
```

This grid is frozen before A3-1b execution as the union of settings already
present in the earlier GIST candidate-family evaluations (`20`, `50`, `100`,
`160`, `200`, `240`, `400`) and the fac-error recall-recovery experiment
(`200`, `220`, `240`, `280`, `300`, `320`). It is not selected from
Attempt 3 quality values. Both plans must run every value, including repeated
A3-1a values, so that one registered execution supplies the final curve.

## Frozen Stage A3-2: Negative Control

Only after A3-1 is complete, evaluate the frozen DEEP `B=4` and `B=5`
default-versus-rejected comparisons at their historical search settings. This
stage tests whether distance quality still rejects alternatives with larger
Recall losses.

## Frozen Stage A3-3: Optional Baseline Analyses

These stages require a separate decision after A3-1/A3-2:

- exact-hist versus Lloyd scalar quantization;
- lossy-projection oracle analysis;
- additional algorithms such as RaBitQ or SymphonyQG.

Do not add a new candidate family or optimize a plan for `1/Ratio` in A3.

## Comparison Rule

For each method, construct the nondominated QPS-quality frontier separately
under Recall and `1/Ratio`. Compare methods at matched quality by interpolation
only within measured adjacent search settings; never extrapolate beyond the
observed grid.

A conclusion changes only if one of the following occurs:

1. a previously dominated alternative becomes nondominated under `1/Ratio`;
2. at a common measured or interpolated quality level, the QPS ordering flips;
3. a previously rejected alternative meets the same geometric-quality target
   with higher QPS while preserving the predeclared query-tail evidence.

A higher `1/Ratio` at one unmatched operating point is not a conclusion change.

## No New Threshold

The protocol reports curves and does not invent an acceptance threshold. The
paper's `0.95` and `0.99` thresholds may be shown for comparability, but they
must not decide whether a project direction passes. This avoids replacing one
arbitrary screening threshold with another.

## Query-Level Safeguard

Mean distance quality can hide difficult queries, just as mean Recall can.
Therefore report the empirical distribution and, for any plan comparison,
paired per-query differences:

```text
delta_q = inverse_ratio_alternative(q) - inverse_ratio_default(q).
```

Report the fraction of queries with `delta_q < 0`, the minimum, `p01`, `p05`,
median, and mean. These are descriptive statistics, not fitted decision rules.

## Complexity

Given `Q` queries, `N` base vectors, dimension `D`, and returned top-`k` IDs:

```text
exact distances for returned IDs: O(Q k D) time
sorting returned distances:       O(Q k log k) time
ratio and Recall aggregation:      O(Q k) time
query-level storage:               O(Q k) IDs plus O(Q) metrics
```

The evaluator does not require an `O(QND)` exact search if exact top-`k`
identifiers and distances already exist. If only identifiers exist, recompute
their `Qk` distances in `O(QkD)`.

This evaluation cost is benchmark-side overhead and is not part of index build
or query latency. It must nevertheless be reported separately.

## Stop Conditions

Stop and record negative evidence if:

- the implementation cannot reproduce the deterministic fixtures;
- required result identifiers cannot be exported without changing search
  semantics;
- baseline and alternative cannot be evaluated on the same search grid;
- apparent gains disappear on the full operating-point comparison; or
- the metric changes absolute quality but not any method conclusion.

No `nprobe` outside the frozen A3-1b historical-union grid, bit budget,
candidate plan, or dataset may be added to rescue the first comparison.

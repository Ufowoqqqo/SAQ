# TASK.md

## Active Goal

Run Attempt 3 as a bounded, evaluation-only test of whether paper-exact
`1/Ratio@k` changes the scientific interpretation of frozen SAQ comparisons.
The immediate target is not a method. It is a validated evaluator and a fair
QPS-versus-quality replay in which the baseline and alternative use the same
search-effort grid.

## Research Question

```text
Does distance quality, measured by 1/Ratio@k, change the Pareto interpretation
of any previously frozen SAQ comparison after both sides are evaluated over
the same operating-point curve?
```

## Decision Boundary

The related-work review returns:

```text
CONDITIONAL_GO_FOR_EVALUATION_ONLY
```

The new metric is established prior work. Replotting results is not a
SIGMOD/VLDB/ICDE contribution. Proceed to a mechanism review only if a stable
Pareto-order change appears on at least two datasets or two independent strong
baselines and survives query-level tail analysis.

## Frozen Sequence

```text
A3-0  implement and validate the paper-exact evaluator
A3-1  replay gist_sample100k K512 B=4 default versus frozen fac-error plan
      over the historical common nprobe grid
A3-2  evaluate frozen DEEP B=4/B=5 rejected candidates as negative controls
A3-3  decide whether any conclusion changed
```

Do not begin A3-2 before A3-1 is recorded. Exact-hist/Lloyd,
lossy-projection, RaBitQ, and SymphonyQG analyses are optional later stages and
require a separate decision.

## A3-0 Requirements

Implement a small reusable evaluator that:

1. reads query, base, exact top-`k`, and returned top-`k` artifacts;
2. recomputes float64 true squared-L2 distances for both ID sets;
3. sorts each set by true distance;
4. applies `sqrt` before the position-wise distance ratios;
5. computes Recall@`k` and paper-exact `1/Ratio@k` per query;
6. writes query-level values and deterministic aggregate statistics; and
7. fails on invalid IDs, duplicates, non-finite values, `k` mismatch, exact
   zero distance, or score above `1 + 1e-12`.

Required deterministic tests are frozen in
`docs/saq_attempt3_ratio_metric_protocol_2026_07_13.md`.

## A3-1 Inputs To Locate Before Running

- GIST sample100k base and query fvecs;
- original-space exact top-100 ground truth;
- default and frozen fac-error `K=512`, `B=4` indexes;
- historical common `nprobe` grid and thread/search configuration;
- a result-ID export path that does not alter search semantics.

If the existing result artifacts contain only aggregate Recall/QPS, rerun the
unchanged search with output-only ID recording. Do not reconstruct IDs from
summary values.

## Required Output

For each operating point report:

```text
dataset, plan, B, nprobe, k,
Recall@k, mean/min/p01/p05/median/p95/max 1/Ratio@k,
QPS, available work counters, index bytes,
command and input hashes.
```

For every alternative/default pair, report paired per-query `1/Ratio`
differences and construct separate nondominated frontiers under Recall and
`1/Ratio`.

## Stop Conditions

Stop and preserve negative evidence if the evaluator fails deterministic
validation, result IDs cannot be exported without changing semantics, the two
plans cannot share a search grid, or the full curve does not change any method
conclusion. Do not add post-hoc settings to search for a positive case.

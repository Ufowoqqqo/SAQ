# TASK.md

## Active Goal

Run Attempt 3 as a bounded, evaluation-only test of whether paper-exact
`1/Ratio@k` changes the scientific interpretation of frozen SAQ comparisons.
The immediate target is not a method. It is a validated evaluator and a fair
QPS-versus-quality replay in which the baseline and alternative use the same
search-effort grid.

A3-0 through A3-3 are complete. The evaluator passes all deterministic fixtures.
On `gist_sample100k/K512/B4`, fac-error `nprobe=280` exceeds the historical
default `nprobe=200` in mean `1/Ratio@100` and QPS (`1.07793x`), although it
cannot reach the default Recall target and 39.6% of paired query-level
`1/Ratio` differences are negative. On DEEP sample100k B4 and B5, the rejected
candidates cannot reach the default np200 target under either metric, and
97.1% / 87.3% of same-nprobe query deltas are negative. This is
metric-sensitivity evidence with preserved negative controls, not a method or
contribution.

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
A3-1a replay gist_sample100k K512 B=4 default versus frozen fac-error plan
       over the historical recovery grid; check curve-range sufficiency
A3-1b if A3-1a is left-truncated, rerun both plans on the preregistered union
       of nprobe values from the two historical experiment families
A3-2  evaluate frozen DEEP B=4/B=5 rejected candidates as negative controls
A3-3  decide whether any conclusion changed                         COMPLETE
```

Do not begin A3-2 before A3-1 is recorded. Exact-hist/Lloyd,
lossy-projection, RaBitQ, and SymphonyQG analyses are optional later stages and
require a separate decision.

A3-1 is recorded in
`docs/saq_attempt3_a3_0_a3_1_gist_evidence_2026_07_13.md`, with compact
artifacts under `docs/saq_attempt3_a3_1b_artifacts_2026_07_13/`. The immediate
decision and DEEP controls are recorded in
`docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md`, with compact artifacts
under `docs/saq_attempt3_a3_2_artifacts_2026_07_13/`.

Attempt 3 is closed as `CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE`. Do not broaden
GIST/DEEP, resume fac-error planning, or design a metric-aware method on this
branch. The next project step should be meeting synthesis or an independently
reviewed Attempt 4, not an Attempt 3 rescue.

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

A3-1a uses `{200,220,240,280,300,320}`. If it lacks frontier support, A3-1b
uses exactly `{20,50,100,160,200,220,240,280,300,320,400}` for both plans.
No additional value may be selected from Attempt 3 results.

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

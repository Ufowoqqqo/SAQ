# Phase 3 Query-Level Statistics and Fixed-Seed Driver

## Research Question

Phase 3 asks whether any SAQ progressive distance stage has a stable local
neighbor-order advantage over the source-aligned packed SymphonyQG estimator.
The evaluation remains a fixed-neighborhood replay. It does not execute a
path-dependent graph traversal and cannot by itself establish an end-to-end
graph-search contribution.

The predeclared matrix is:

```text
dataset: GIST sample50k, PCA coordinates
SAQ index: K=512, B=4
degree: 32
subset 1024: 50 queries, 8 roots per query
subset 4096: 100 queries, 8 roots per query
SymphonyQG rotation seeds: 0,1,...,9
```

The ten seeds are evaluation replications fixed before observing the result.
They are not tunable method parameters.

## Event-Level Sufficient Statistics

`src/profile_graph_frontier.cpp` now writes the following additional values for
every `(query, root, estimator)` event:

- exact-best squared-L2 distance;
- the selected candidate's estimator value;
- the selected candidate's exact squared-L2 distance;
- exact-distance regret.

For estimator `e`, query `q`, and root `r`, regret is

```text
regret(e,q,r) = d_exact(q, selected(e,q,r))
              - d_exact(q, exact_best(q,r)).
```

It is non-negative up to floating-point roundoff and is measured in squared-L2
units. These fields make every Phase 3 statistic recomputable from the event
CSV without re-reading vectors or inferring values from rounded aggregates.

## Statistical Unit

Roots are nested observations, not independent samples. For a root-level metric
`x`, the driver first computes

```text
x_bar(q,s) = (1 / R) * sum_r x(q,s,r),
```

where `R=8` roots and `s` is a fixed rotation seed. It then averages seed
replications within the same query:

```text
x_tilde(q) = (1 / S) * sum_s x_bar(q,s),
```

where `S=10`. The final mean and confidence interval use only the `Q` held-out
queries as independent observations:

```text
mean = (1 / Q) * sum_q x_tilde(q)
95% CI = mean +/- 1.95996 * sample_sd(x_tilde) / sqrt(Q).
```

This is explicitly a query-level normal-approximation interval. Seed-level
means, standard deviations, minima, and maxima are reported separately. Rank
`p50/p90/p99` values use the higher empirical order statistic. Top-`L`
containment is `1[rank_exact_best <= L]`, averaged using the same nesting rule.

Margin-conditioned statistics use empirical quartiles of the exact first-to-
second neighbor gap within each subset. Quartiles are descriptive strata, not
learned thresholds. Each `(query, root)` contributes once to the quartile
boundaries even though it appears under multiple estimators and seeds.

## Driver

The canonical run is:

```bash
python script/run_graph_phase3.py \
  --binary ./bin/profile_graph_frontier \
  --artifact-root /rwproject/kdd-db/kluaq/saq/data/gist_sample50k \
  --output-dir results/saq/graph_phase3_gist_sample50k_k512_b4
```

Canonical settings and seeds are defaults. Noncanonical `--setting`, `--seeds`,
`--degree`, and `--roots-per-query` overrides exist only for tests and explicit
diagnostics; the manifest labels such runs `canonical_phase3_matrix: false`.

Resume is enabled by default. A run is reused only when the event CSV has the
new sufficient-statistics schema, all three profiler outputs are present, and
the exact command matches the prior manifest. `--no-resume` deliberately
replaces runs. `--aggregate-only` regenerates tables without overwriting the
original execution manifest.

Outputs are:

```text
manifest.json
phase3_query_metrics.csv
phase3_seed_summary.csv
phase3_overall_summary.csv
phase3_paired_vs_symqg.csv
phase3_margin_boundaries.csv
phase3_margin_conditioned.csv
phase3_summary.md
runs/subset_<N>/seed_<S>.{events.csv,csv,md,log}
```

`phase3_paired_vs_symqg.csv` reports per-query candidate-minus-baseline deltas
against `symqg_fht_fastscan`. Lower is better for disagreement, rank, and
regret; higher is better for containment. The main table retains the profiler's
logical code-bit count but labels it `code bits only`: it is not a substitute
for complete byte traffic or runtime.

## Verification

Focused tests:

```bash
python -m unittest tests/test_graph_phase3.py -v
python -m py_compile script/run_graph_phase3.py tests/test_graph_phase3.py
```

The tests verify parsing, canonical-matrix detection, event-schema completeness,
resume command identity, root-to-query aggregation, seed-to-query aggregation,
paired differences, and margin-event deduplication.

A two-query, two-root, two-seed GIST smoke run completed end to end. It verified
the C++ event schema, manifest, resume metadata, and all aggregate outputs. Its
subset and sample size are intentionally noncanonical, so it is implementation
evidence only and supplies no Phase 3 research conclusion.

## Remaining Decision

Run the canonical matrix and apply the predeclared stop/continue condition from
`docs/saq_graph_direction_research_validity_plan_2026_07_10.md`. Do not design a
traversal policy or implement a full graph index before that decision.

# AGENTS.md

Durable guidance for Codex sessions on the `saq-ratio-metric-analysis` branch.

## Research Frame

Work as a doctoral researcher developing a database-systems contribution, not
as a programmer optimizing a repository. Code is measurement infrastructure.
Judge each task by novelty, scientific validity, complete overhead, and how a
strict SIGMOD/VLDB/ICDE reviewer would assess it.

Use research-paper terminology in research notes, summaries, slides, and task
descriptions. Prefer "review", "analyze", "evaluate", "survey", "evidence",
and "limitations". Use "audit", "harden", "triage", and "patch" only for
literal code or repository maintenance.

Before proposing a method, review the closest primary work, state what it
already solves, identify the remaining mechanism-level gap, and explain why
the proposal is not a direct composition. Do not introduce a hyperparameter
without a mechanism-level rationale, physical/statistical meaning, frozen
selection rule, and sensitivity or ablation plan.

## Active Direction

Attempt 3 is an evaluation-only study of `1/Ratio@k` from *ANN Search: Recall
What Matters*. Its first question is whether the metric changes the Pareto
interpretation of frozen SAQ comparisons. The metric is prior work and is not
this project's contribution.

The authoritative documents are:

- `docs/saq_attempt3_ratio_metric_related_work_and_gate_2026_07_13.md`;
- `docs/saq_attempt3_ratio_metric_sources_2026_07_13.json`;
- `docs/saq_attempt3_ratio_metric_protocol_2026_07_13.md`.

Do not design a metric-aware plan, fit on benchmark queries, add candidates,
or reopen an earlier method before the protocol's retrospective comparison is
complete. A later method review requires a stable Pareto-order change on at
least two datasets or two independent competitive baselines.

## Branch Hygiene

This branch starts from `saq-correctness-base@bc7829b`, retaining only:

- positive one-bit segment packing support; and
- finite valid-lane SIMD block minima as the safe multi-segment default.

Historical branches are evidence sources, not code donors. Do not migrate old
planner, fixed-policy, local-plan, CAQ-repair, graph-replay, or transform
prototype code unless the frozen evaluation protocol explicitly requires one
unchanged artifact or result exporter.

## Repository Layout

- `saqlib/`: C++ quantizers, estimators, IVF helpers, and search logic.
- `src/`: C++ executables including index construction and search evaluation.
- `script/`: upstream experiment helpers and small research drivers.
- `python/`: data-preparation helpers.
- `docs/`: research decisions, protocols, and evidence.
- `build/`, `bin/`, `data/`, `results/`: generated or local artifacts; do not
  commit binaries, indexes, or datasets.

## Build And Verification

Default build:

```bash
mkdir -p build bin
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Before committing:

```bash
git diff --check
python -m unittest discover -s tests -p 'test_*.py' -v
cmake --build build -j
git status --short --branch
```

If a command is unavailable because the corresponding build or test directory
does not yet exist, report that explicitly rather than claiming verification.

Multi-segment SAQ search uses finite valid-lane block minima by default. Use
`-searcher_safe_block_min_mode=0` only for a labeled reproduction of the
legacy native-reduction behavior.

## Metric Semantics

- Compute the paper's ratio from Euclidean distances, not squared L2.
- Recompute true distances for returned IDs and sort by those distances.
- Require `k` valid distinct IDs; reject malformed rows.
- Stop on zero exact distance rather than introducing an epsilon.
- Preserve query-level values and report tails with the mean.
- Evaluate baseline and alternative on the same search-effort grid.
- Report both Recall and `1/Ratio`; do not silently replace the established
  metric.

## Recurring Do-Not Rules

- Do not use benchmark queries to learn a plan, threshold, or search rule.
- Do not claim that a metric change is an algorithmic contribution.
- Do not compare one unmatched operating point or tune only the alternative.
- Do not invent a pass threshold; report full measured curves.
- Do not rescue a failed comparison with post-hoc datasets, bit budgets,
  `nprobe` values, or candidate plans.
- Do not present correctness fixes as research contributions.
- Do not continue an earlier direction whose failure was caused by overhead or
  missing signal rather than Recall semantics.
- Do not claim a universal SAQ improvement without cross-dataset,
  cross-baseline, end-to-end evidence and complete cost accounting.


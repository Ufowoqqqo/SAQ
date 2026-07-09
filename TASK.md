# TASK.md

## Active Goal

Develop a clean query-unaware structural SAQ follow-up from original SAQ code
plus confirmed correctness fixes. The current main direction is data-only
planner-objective analysis for SAQ: evaluate whether SAQ's global variance-risk
model is the right objective for CAQ/SAQ quantization and search.

The target is a database top-conference-level contribution suitable for SIGMOD,
VLDB, or ICDE. Future work should be judged by research novelty, evidence,
overhead, and reviewer defensibility rather than by implementation volume.

## Starting Point

This branch starts from `saq-correctness-base` and keeps only correctness fixes
needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search mode.

The previous mixed shared-plan work showed useful negative evidence: IVF-local
residual plans can slightly improve recall, but per-query multi-plan estimator
overhead can dominate the benefit. Treat that as motivation, not as the new
method.

The single-global static segment-cost direction also produced negative evidence:
SAQ's default global plan was not dominated on deterministic risk-cost
frontiers, and GIST near-frontier lower-cost plans did not improve safe-search
QPS end to end. Treat this as limitation evidence, not as the main method.

The first planner-objective measurement is recorded in
`docs/planner_proxy_measurement_2026_07_09.md`. It found that SAQ's variance
proxy strongly predicts energy-weighted residual CAQ error, especially raw and
scale-aligned SSE, but is weaker for pure direction-loss ranking.

The second measurement is recorded in
`docs/estimator_error_measurement_2026_07_09.md`. It measures query-unaware
distance-estimator error on same-cluster residual pairs. Direction loss alone is
not a stable predictor of absolute estimator error, but CAQ `fac_error` almost
perfectly ranks absolute segment estimator error across the first five datasets.

## Research Priority

**Data-only SAQ planner-objective analysis**

Question:

```text
Does SAQ's variance-risk objective, sum(segment_variance) / 2^bits, accurately
predict the actual query-unaware quantization and distance-estimation error of
CAQ/SAQ segments?
```

Candidate method:

```text
If the SAQ proxy has a systematic, cross-dataset mismatch with measured
data-only CAQ/SAQ error, derive a replacement global DP objective that keeps one
global plan and does not use representative queries.
```

Required accounting:

- exact SAQ proxy risk for each evaluated segment and bit width;
- measured data-only quantization or estimator error for the same segment and
  bit width;
- cross-dataset agreement or disagreement between proxy risk and measured
  error;
- offline measurement cost and how it compares with SAQ index construction;
- if a replacement objective is proposed, recall/QPS under safe search, index
  build time, index size, plan shape, and total bit budget.

## Immediate Next Step

Continue offline. Do not derive a broad new planner yet. First run a small
falsification study for a global `fac_error`-based objective:

1. Define a data-only global objective from measured CAQ `fac_error` for each
   candidate segment and bit width.
2. Compare the selected global plan against SAQ's variance-DP plan under the
   same bit budget.
3. Evaluate whether the selected plan is meaningfully different before any
   index build.
4. Stop this planner-objective direction if the plan is identical,
   near-identical, or only changes in ways unlikely to affect recall/QPS.

The research question is now narrower:

```text
Does replacing SAQ's variance-risk DP cost with a directly measured CAQ
fac-error cost produce a materially different one-global-plan allocation without
using query workloads?
```

The strict-reviewer objection is that `fac_error` may be a tautological,
offline-expensive remeasurement of CAQ's own estimator bound. Any follow-up must
therefore report measurement cost, plan difference, and one end-to-end
safe-search check before claiming a method.

## Constraints

- Stay query-unaware: use base vectors, PCA artifacts, global variance,
  quantization plans, and index-build metadata only for plan learning.
- Use held-out queries only for final evaluation.
- Keep one global plan. Do not introduce per-cluster plan ids or mixed-plan
  search dispatch.
- Do not continue simple static global segment-cost DP as the main method. Its
  current role is limitation evidence.
- Use research-paper terminology in new docs and task descriptions: prefer
  "review", "analyze", "evaluate", "survey", "evidence", and "limitations" over
  "audit", "harden", "triage", and "patch" unless discussing code correctness
  or referring to existing names.
- Before starting a new direction or broad experiment, state the research
  question, expected contribution, overhead model, likely strict-reviewer
  objection, and stop condition.
- Do not rely on unjustified hyperparameters. Each hyperparameter must have a
  mechanism-level rationale, clear unit or scale, fixed selection rule before
  held-out evaluation, and either sensitivity evidence or an ablation plan.
- Do not overclaim a universal improvement over SAQ before end-to-end
  validation across datasets and operating points.
- Avoid broad sweeps before stating the research hypothesis and stop condition.
- Prefer small, falsifiable experiments over more tooling.
- Keep documentation concise and paper-facing.

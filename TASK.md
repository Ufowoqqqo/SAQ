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

The first fac-error DP falsification is recorded in
`docs/fac_error_dp_falsification_2026_07_09.md`. At B=4, the fac-error objective
selects different global plans on GIST sample100k and CIFAR60K, but reproduces
SAQ's variance plan on audio, DEEP, and word2vec.

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

Run the smallest end-to-end falsification for the fac-error objective. Since the
B=4 offline DP selected different plans only on GIST sample100k and CIFAR60K,
do not broaden the sweep yet. First materialize one changed plan, preferably
GIST sample100k B=4 because its plan-shape change is larger:

```text
SAQ variance plan:   64x11_192x6_320x4_256x2_128x0
fac-error plan:      192x9_512x4_256x0
```

Then compare default vs fac-error plan under safe search. Report recall, QPS,
index size, indexing time, and whether the custom-plan materialization path adds
extra planner complexity.

The current research question is:

```text
Does replacing SAQ's variance-risk DP cost with a directly measured CAQ
fac-error cost produce a materially different and end-to-end useful
one-global-plan allocation without using query workloads?
```

The strict-reviewer objection is that `fac_error` may be a tautological,
offline-expensive remeasurement of CAQ's own estimator bound. Any follow-up must
therefore report measurement cost, plan difference, and one end-to-end
safe-search check before claiming a method. Stop if the changed GIST plan does
not improve recall/QPS or if the custom-plan machinery becomes the dominant
contribution.

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

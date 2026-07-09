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

The first end-to-end check is recorded in
`docs/fac_error_gist_b4_safe_search_2026_07_09.md`. On GIST sample100k K512 B=4
at nprobe=200 with safe search, the fac-error plan is 1.34x faster and 4.7%
smaller, but R@100 drops from 0.99132 to 0.99059. This is a speed/space/recall
tradeoff, not a strict improvement over SAQ.

The recall-matched follow-up is recorded in
`docs/fac_error_gist_b4_recall_matched_2026_07_09.md`. Increasing the custom
plan's nprobe up to the QPS break-even point did not recover the default R@100.
At nprobe=300, the custom plan is still 1.022x faster but R@100 remains below
default; at nprobe=320, it is slower than default and still below default
recall.

The planner-objective synthesis is recorded in
`docs/saq_planner_objective_limitations_2026_07_09.md`. It concludes that the
current one-global-plan objective-modification line should stop as a main
method. Static segment-cost, direct CAQ estimator-error, and earlier local-plan
directions all fail to produce a defensible recall-matched improvement.

The next-direction proposal is recorded in
`docs/saq_next_direction_proposal_2026_07_09.md`. It recommends
search-procedure / estimator-scheduling integration as the next candidate
direction, but only after a code-level search-path review and work-decomposition
plan. No new search policy is approved yet.

The search-path review is recorded in
`docs/saq_search_path_work_decomposition_2026_07_09.md`. It locates the current
fast-estimation, accurate-refinement, safe block-min, pruning, top-k result-pool
maintenance, and runtime-metric code paths. It also defines the minimal
query-time work decomposition needed before any new search policy is proposed.

The first runtime-profile evidence is recorded in
`docs/saq_runtime_profile_gist_sample100k_2026_07_09.md`. On GIST sample100k
K512 B=4, variance pruning is almost inactive, fast-stage pruning removes about
45-58% of post-variance blocks, only about 5-7% of scanned candidates enter
accurate refinement, and accurate refinement already exits early for about 84%
of refined candidates.

The segment-order counterfactual design and first prototype result are recorded
in `docs/saq_segment_order_counterfactual_design_2026_07_09.md`. A diagnostic
binary, `bin/profile_segment_order`, replays the search loop under alternative
segment orders without modifying the production search path. On GIST
sample100k K512 B=4 at nprobe=200, simple hyperparameter-free alternatives do
not reduce work relative to the default order; reverse and dimension-descending
orders are substantially worse.

The segment-order robustness check is recorded in
`docs/saq_segment_order_robustness_2026_07_09.md`. At nprobe 160, 200, and 240,
the default `pca` order remains tied for the lowest observed work among the
tested simple query-unaware orders. The simple segment-order branch should stop
as a main method direction.

The search-procedure direction decision is recorded in
`docs/saq_search_procedure_direction_decision_2026_07_09.md`. Generic
search-procedure optimization should not continue as a main method. The only
remaining allowed search-procedure question is a final bound-focused
measurement explaining why the variance-pruning stage is almost inactive and
whether any safe, non-empirical refinement exists.

The final variance-bound inactivity measurement is recorded in
`docs/saq_variance_bound_inactivity_final_2026_07_09.md`. It shows that the
variance-stage block minimum is usually far below the current top-k boundary:
the median relative gap is about 0.74, and meaningful pruning would require
removing roughly 58-63% of the current variance slack. This would be arbitrary
calibration without a new safety argument. The search-procedure direction is
therefore closed as a main method direction.

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

Stop treating the current one-global-plan planner-objective modification line
as the main method. It is now limitation evidence:

```text
SAQ variance plan:   64x11_192x6_320x4_256x2_128x0
fac-error plan:      192x9_512x4_256x0
```

The useful result is that direct CAQ estimator-error objectives can move SAQ
toward lower search cost, but the first changed plan does not produce a
recall-matched QPS improvement. Static segment-cost and earlier local-plan
directions also failed under end-to-end review.

The current research question is:

```text
What SAQ limitation remains after variance-risk, direct CAQ estimator-error,
and simple segment-cost objectives fail to produce a recall-matched improvement
under a one-global-plan, query-unaware constraint?
```

The immediate next step is to synthesize the negative search-procedure evidence
and decide the next structural SAQ limitation to study. Do not implement more
search-loop scheduling changes on this branch.

The synthesis should clearly state that one-global-plan objective changes,
static segment-cost DP, mixed local plans, simple segment reordering, and
variance-bound tightening by calibration have all failed as main methods. The
next direction should move away from small IVF search-loop scheduling changes
and toward a more structural SAQ limitation, such as graph-index compatibility,
estimator-bound theory, or non-PCA transform objectives with a stronger
derivation.

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

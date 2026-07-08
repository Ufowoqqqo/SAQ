# TASK.md

## Active Goal

Develop a clean query-unaware structural SAQ follow-up from original SAQ code
plus confirmed correctness fixes. The current main direction is
single-global-plan segment-cost-aware DP.

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

## Research Priority

**Single-global-plan segment-cost-aware DP**

Question:

```text
Can SAQ's global planner account for search-time segment cost without relying
on post-hoc candidate filtering or mixed per-cluster plans?
```

Candidate method:

```text
Extend the global DP objective or report a Pareto frontier over quantization
risk and implementation-derived segment-cost terms while keeping one global
plan.
```

Required accounting:

- recall and QPS under safe search;
- index build time and index size;
- plan shape and total bit budget;
- static cost terms such as positive dimensional volume, accurate bit volume,
  segment count, zero-tail mass, and per-segment metadata/factor overhead;
- runtime decomposition if an end-to-end index is built.

## Immediate Next Step

Start offline. Reproduce SAQ's global DP and generate a deterministic
risk-vs-cost frontier for existing datasets and bit budgets before building any
new index.

The first study should answer:

1. Is SAQ's default global plan far from a risk-cost Pareto frontier?
2. Are there global plans with nearly identical risk but meaningfully lower
   implementation-derived cost?
3. Does the signal hold beyond one dataset?
4. Can the objective avoid unjustified free hyperparameters?

## Constraints

- Stay query-unaware: use base vectors, PCA artifacts, global variance,
  quantization plans, and index-build metadata only for plan learning.
- Use held-out queries only for final evaluation.
- Keep one global plan. Do not introduce per-cluster plan ids or mixed-plan
  search dispatch.
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

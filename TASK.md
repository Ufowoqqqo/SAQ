# TASK.md

## Active Goal

Develop a clean query-unaware structural SAQ follow-up from original SAQ code
plus confirmed correctness fixes. The previous `saq-boundary-audit` branch is a
historical archive, not the implementation base for the new method.

The target is a database top-conference-level contribution suitable for SIGMOD,
VLDB, or ICDE. Future work should be judged by research novelty, evidence,
overhead, and reviewer defensibility rather than by implementation volume.

## Starting Point

This branch starts from upstream SAQ and keeps only correctness fixes needed for
reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search mode.

The old fixed-policy scorer line showed useful negative lessons, but it is not
the preferred novelty path because it is empirical, metric-heavy, and too close
to local SAQ tuning.

## Research Priorities

1. **Single-global-plan segment-cost-aware DP**
   - Question: can SAQ's planner account for search-time segment cost without
     relying on post-hoc candidate filtering or mixed per-cluster plans?
   - Candidate method: extend the global DP objective or report a Pareto
     frontier over quantization-risk and implementation-derived segment-cost
     terms while keeping one global plan.
   - Required accounting: recall, QPS, index build time, index size, plan shape,
     static cost terms, and runtime decomposition with safe search.

2. **Flexible segmentation / learned grouping**
   - Question: do contiguous PCA blocks and 64-dimensional granularity limit
     query-unaware plan quality?
   - Candidate method: compare default contiguous plans against data-only
     segment boundaries or grouped dimensions, with explicit SIMD/cache cost.

3. **Cluster-aware / local residual-aware SAQ plan sharing as limitation
   evidence only**
   - Finding: GIST full K4096 B4 shows residual-local shared plans can slightly
     improve recall, but mixed-plan search overhead dominates.
   - Role: use this as evidence that SAQ's global residual assumption can be
     imperfect, not as the main method.
   - Do not continue mixed shared local plans unless explicitly studying a new
     search architecture.

## Immediate Next Step

Write a concise negative-evidence and pivot note under `docs/` that records why
mixed shared local plans are no longer the main direction. Then start the
single-global-plan segment-cost-aware DP direction with an offline DP/Pareto
frontier study before building any new index.

## Constraints

- Stay query-unaware: use base vectors, PCA artifacts, IVF centroids/cluster
  ids, residual statistics, and index metadata only for plan learning.
- Use held-out queries only for final evaluation.
- Use research-paper terminology in new docs and task descriptions: prefer
  "review", "analyze", "evaluate", "survey", "evidence", and "limitations" over
  "audit", "harden", "triage", and "patch" unless discussing code correctness
  or referring to existing names.
- Before starting a new direction or broad experiment, state the research
  question, expected contribution, overhead model, likely strict-reviewer
  objection, and stop condition.
- Do not continue mixed shared local SAQ plans as the main method. Treat the
  existing results as SAQ limitation evidence unless a new architecture removes
  per-query multi-plan estimator overhead.
- Do not rely on unjustified hyperparameters. Each hyperparameter must have a
  mechanism-level rationale, clear unit or scale, fixed selection rule before
  held-out evaluation, and either sensitivity evidence or an ablation plan.
- Do not overclaim a universal improvement over SAQ before end-to-end
  validation across datasets and operating points.
- Avoid broad sweeps before stating the research hypothesis and stop condition.
- Prefer small, falsifiable experiments over more tooling.
- Keep documentation concise and paper-facing.

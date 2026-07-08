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

1. **Cluster-aware / local residual-aware SAQ plan sharing**
   - Question: does one global PCA-variance plan mismatch IVF cluster residual
     distributions?
   - Candidate method: learn a small shared family of segment/bit plans from
     cluster residual statistics and store one plan id per IVF cell.
   - Required accounting: recall, QPS, index build time, index size, plan-id
     metadata, and number of shared plans.

2. **Segment-cost-aware DP**
   - Question: can SAQ's planner account for search-time segment cost without
     relying on post-hoc candidate filtering?
   - Candidate method: extend the DP objective or report a Pareto frontier over
     quantization-risk and segment-cost proxies.

3. **Flexible segmentation / learned grouping**
   - Question: do contiguous PCA blocks and 64-dimensional granularity limit
     query-unaware plan quality?
   - Candidate method: compare default contiguous plans against data-only
     segment boundaries or grouped dimensions, with explicit SIMD/cache cost.

## Immediate Next Step

Write a short direction-review note under `docs/` comparing the three priority
directions by:

- exact SAQ assumption targeted;
- proposed method beyond local filtering;
- expected novelty;
- metadata/training/indexing/search overhead;
- smallest experiment that could falsify the direction.

Then start with cluster-aware / local residual-aware plan sharing unless the
review finds a stronger reason to choose another direction.

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
- Do not rely on unjustified hyperparameters. Each hyperparameter must have a
  mechanism-level rationale, clear unit or scale, fixed selection rule before
  held-out evaluation, and either sensitivity evidence or an ablation plan.
- Do not overclaim a universal improvement over SAQ before end-to-end
  validation across datasets and operating points.
- Avoid broad sweeps before stating the research hypothesis and stop condition.
- Prefer small, falsifiable experiments over more tooling.
- Keep documentation concise and paper-facing.

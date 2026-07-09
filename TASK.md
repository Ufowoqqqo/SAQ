# TASK.md

## Active Goal

Develop a clean query-unaware structural SAQ follow-up from original SAQ code
plus confirmed correctness fixes. The current branch studies graph-index
compatibility for SAQ: whether SAQ's progressive compressed distance estimator
remains traversal-stable in graph-based ANNS.

The target is a database top-conference-level contribution suitable for SIGMOD,
VLDB, or ICDE. Future work should be judged by research novelty, evidence,
overhead, and reviewer defensibility rather than by implementation volume.

## Starting Point

This branch starts from `saq-correctness-base` and keeps only correctness fixes
needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search mode.

Historical directions are treated as limitation evidence, not active methods:

- default-neighborhood and fixed-policy plan scoring found small positives but
  looked too empirical;
- mixed shared local plans exposed IVF-local residual structure but added
  multi-plan estimator/search overhead;
- single-global static segment-cost DP found lower-cost plans but did not
  produce recall-matched QPS benefit;
- direct CAQ estimator-error DP moved some plan shapes but failed
  recall-matched GIST evaluation;
- simple IVF segment reordering and variance-bound calibration did not expose a
  defensible low-overhead search-procedure method.

## Research Priority

**Graph-index compatibility and traversal-sensitivity analysis**

Question:

```text
Can SAQ-style progressive compressed distance estimation be used inside
graph-based ANNS traversal without destabilizing the search path, and what
query-unaware refinement policy is needed to preserve the recall/work tradeoff?
```

Candidate method, only if the first evidence supports it:

```text
A traversal-aware refinement policy that uses SAQ's stored estimator quantities
to refine only frontier-ambiguous candidates, without representative-query
learning and without changing SAQ's global quantization plan.
```

Required accounting:

- graph nodes visited and neighbor expansions;
- exact-float versus SAQ-estimate frontier disagreement;
- rank of the exact-best expansion under staged SAQ estimates;
- number of frontier candidates requiring refinement to recover stable
  traversal decisions;
- compressed code reads, segment/factor reads, and any exact-refinement reads;
- recall/work tradeoff under fixed graph construction and search parameters;
- index size and any additional metadata if a later method changes storage.

## Immediate Next Step

Perform a graph-index compatibility review plus a minimal
traversal-sensitivity measurement design. Do not implement full HNSW or DiskANN
integration yet.

The first graph-index step should answer:

- which existing graph implementation or offline adjacency harness can be used
  without changing SAQ's persisted index format;
- whether SAQ approximate/staged estimates change graph frontier ordering
  relative to exact float distances;
- how many frontier candidates would require refinement to recover stable
  traversal decisions;
- whether the observed behavior is a graph-specific SAQ limitation rather than
  another generic recall/speed tradeoff.

## Constraints

- Stay query-unaware: use base vectors, PCA artifacts, global variance,
  quantization plans, and index-build metadata only for method design.
- Use held-out queries only for final evaluation.
- Keep one global quantization plan unless a later note explicitly motivates a
  different architecture.
- Do not introduce per-cluster plan ids or mixed-plan search dispatch.
- Use research-paper terminology in new docs and task descriptions: prefer
  "review", "analyze", "evaluate", "survey", "evidence", and "limitations" over
  "audit", "harden", "triage", and "patch" unless discussing code correctness
  or referring to existing names.
- Before starting a new broad experiment, state the research question, expected
  contribution, overhead model, likely strict-reviewer objection, and stop
  condition.
- Do not rely on unjustified hyperparameters. Each hyperparameter must have a
  mechanism-level rationale, clear unit or scale, fixed selection rule before
  held-out evaluation, and either sensitivity evidence or an ablation plan.
- Do not overclaim a universal improvement over SAQ before validation across
  datasets and operating points.
- Prefer small, falsifiable experiments over more tooling.
- Keep documentation concise and paper-facing.

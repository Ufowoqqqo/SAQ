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

The first graph-index compatibility review and measurement design is recorded
in `docs/saq_graph_traversal_measurement_design_2026_07_09.md`. It concludes
that the repository has no active graph-index implementation and that the first
study should be an offline fixed-adjacency replay, not HNSW/DiskANN
integration.

The graph quantization related-work and novelty gate is recorded in
`docs/saq_graph_quantization_related_work_and_novelty_gate_2026_07_09.md`. It
concludes that SymphonyQG, NGT-QG, and graph-aware quantization work already
cover broad quantization-plus-graph integration. The branch must target a
narrower SAQ-specific contribution: whether SAQ's segmented progressive
estimator provides a traversal/refinement advantage beyond a
RaBitQ/SymphonyQG-style graph quantization baseline.

The ordered research-validity and evaluation plan is recorded in
`docs/saq_graph_direction_research_validity_plan_2026_07_10.md`. That plan is
the authoritative execution sequence for this branch.

## Current Evidence Status

The historical local graph result remains provisional. The old
`symqg_vertex_proxy` omits random-sign FHT and power-of-two padding and is kept
only as a historical control. Phase 2 now includes parity-tested
`symqg_fht_scalar` and `symqg_fht_fastscan` implementations aligned with pinned
SymphonyQG revision `6124ddb34ee4d176edea1bd7ad38d1672343df28`. On the
small GIST sample50k, subset-512, seed-0 sanity run, both aligned paths have
top-1 disagreement `0.304688`, compared with `0.867188` for the old proxy and
`0.453125` for `saq_fast`. This supports the baseline correction, not a
graph-search contribution.

The current profiler still measures independent query-near local-neighborhood
ordering. It now implements the official packed layout, query LUT, AVX-512
accumulation, and factor path, but not a frontier heap, visited set,
path-dependent beam traversal, or SymphonyQG's multiple estimates. Its primary
metric table labels code bits only; packed code, factor, LUT, padding, and SIMD
work are reported separately. The completed Phase 2 record is
`docs/saq_symphonyqg_fastscan_parity_2026_07_10.md`.

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

Phases 0 and 1 of
`docs/saq_graph_direction_research_validity_plan_2026_07_10.md` are complete.
The historical graph comparison is visibly provisional, finite valid-lane SIMD
block minima are the tested default, positive 1-bit segments and partial blocks
have focused regression coverage, and full GIST/K4096/B=3 completes fresh
build/load/search evaluation. The verification record is
`docs/saq_phase1_correctness_verification_2026_07_10.md`.

Phase 2 is complete. Power-of-two padding, seeded random-sign FHT, 6-bit query
quantization, residual factors, packed codes, query LUTs, AVX-512 accumulation,
distances, and deterministic ordering pass pinned-source parity in Release and
ASAN Debug builds. Scalar and packed rows are identical on the seed-0 sanity
run, and packed storage/work metadata is recorded.

The Phase 3 query-level statistics and fixed-seed evaluation driver is
implemented and documented in
`docs/saq_graph_phase3_fixed_seed_driver_2026_07_10.md`. It records sufficient
event-level values for exact-distance regret, aggregates nested roots within a
query, averages fixed rotations within that query, reports query-level 95%
confidence intervals and seed variation, and refuses resume when the command or
event schema differs. A noncanonical two-query/two-seed smoke run verifies the
complete output path but is not research evidence.

Execute the canonical Phase 3 matrix next:

1. run the fixed GIST sample50k/K512/B4 replay at subsets 1024 and 4096;
2. use every predeclared rotation seed `0..9`, without selecting favorable
   seeds;
3. aggregate roots at the query level and report confidence intervals;
4. compare SAQ progressive stages with packed SymphonyQG under complete logical
   work;
5. apply the documented continue/stop condition before any traversal policy or
   full graph integration.

Do not implement full HNSW/DiskANN integration, broaden the dataset matrix, or
design a refinement policy until this gate passes.

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
- Before proposing any new research idea, first survey closely related work.
  If similar work exists, state what it already solves, what assumptions or
  gaps remain, and how the proposed idea avoids duplication by targeting a
  distinct SAQ-specific limitation or contribution.
- Prefer small, falsifiable experiments over more tooling.
- Keep documentation concise and paper-facing.

# Active Task: SAQ component-wise base-only oracle diagnostic

## State and question

- Branch: `saq-mixed-radix-query`
- Base snapshot: `15de1ad`
- Modes: `IMPLEMENT`, `EXPERIMENT`, `REVIEW`

Determine which part of the unchanged production SAQ accurate-distance path,
if any, materially causes ordering errors among nearby base vectors.  This is
a limitation-localization diagnostic, not a new method, query experiment, or
performance claim.

Hypothesis: at least one of the current per-vector rescale or five frozen SAQ
segments accounts for a consistent and material share of base-neighbour
pairwise order reversals.  Failure means there is no localized estimator
component worth optimizing under this decomposition.

Detailed design:
`docs/research/saq_component_oracle_diagnostic_design_2026_08_03.md`.

## Frozen inputs and data boundary

Read only:

- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs`;
- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index`;
- relevant repository source and current research documents.

The base file has 50,000 rows and 960 dimensions.  The persisted index fixes
`K=512`, average four bits per dimension, production CAQ adjustment, random
segment rotations, and this plan:

```text
64d@11b | 192d@6b | 320d@4b | 256d@2b | 128d@0b
```

Do not read benchmark queries, ground truth, query-result TSVs, another
dataset, or another index.  Do not build a new index.  Base rows may act as
query-like probes only inside this offline diagnostic.

## Allowed implementation and commands

Allowed writes:

- one minimal correction to the repeated-cluster loop in
  `saqlib/index/ivf.hpp` plus a focused multi-cluster load regression test;
- focused source, tests, and CMake integration under
  `research/saq_component_oracle/`;
- `TASK.md`, the design/result note, and the decision log;
- generated output only under `/tmp/saq-component-oracle-v1/`.

Do not change the encoder, planner, rotations, index format, estimator, search
path, production configuration, or scientific thresholds.  The loader repair
is artifact correctness work, not evidence or a contribution.

Allowed commands are the focused CMake configure/build/tests, one primary
`frozen-v1` diagnostic execution, and at most one unchanged byte-reproduction
run named in the design note.  Do not run ANN search, Recall/QPS, a parameter
sweep, or an outcome-selected run.

## Budget

- at most 2 aggregate CPU-hours including build, tests, and execution;
- at most 2 wall-hours;
- one diagnostic process and one experimental thread;
- at most 4 GiB peak RSS;
- generated output below 100 MiB.

Stop before exceeding a limit.  Ordinary compile/test failures should be
fixed within scope.  Stop without scientific interpretation if index loading,
ID coverage, stored-versus-recomputed estimator parity, or exact-distance
parity cannot be established.

## Deliverables and done criteria

Done means:

- the focused loader and arithmetic tests pass;
- the frozen 256 probes and 4,096 candidate pool are disjoint and reproducible;
- every probe has exactly 64 exact-nearest evaluation candidates;
- production, rescale-replacement, and five single-segment replacement arms
  are complete on both 128-probe halves;
- exact-all substitution reproduces float64 raw-vector distance within the
  frozen tolerance;
- pairwise inversion, repaired/new inversion, top-10 agreement, distance
  error, CPU/wall time, RSS, hashes, and limitations are recorded;
- the result identifies an actionable component using the frozen rule or
  closes this localization attempt without inventing a new method.

Current blocker: none.  The frozen diagnostic is complete and closes with
`CLOSE_NO_ACTIONABLE_COMPONENT`; see
`docs/research/saq_component_oracle_diagnostic_result_2026_08_03.md`.
One concrete next action is a bounded diff review and user checkpoint; do not
start another experiment or change the scientific question.

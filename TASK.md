# Active Task: SAQ joint-component mechanism review

## State and question

- Branch: `saq-mixed-radix-query`
- Base snapshot: `7be0f68`
- Modes: `IDEATE`, `REVIEW`

The completed joint-component diagnostic returned `PAIR_ACTIONABLE` for exact
replacement of `192d@6b + 320d@4b`.  The active question is now:

> Does the fixed SAQ representation admit a query-unaware, matched-storage,
> non-separable joint encoding mechanism for these two segments, or is the
> oracle gain explained by generic ranking interaction and already-covered
> quantization mechanisms?

Working hypothesis: the super-additive inversion reduction does not prove
encoder coupling because the production estimate is additive and inversion is
a nonlinear sign decision.  Reconstruction-based joint optimization remains
separable.  A continuation is justified only if a base-only estimator-error
objective is non-separable while retaining the identical plan, bytes, and
query operations.

The completed evidence and active review are:

- `docs/research/saq_component_oracle_diagnostic_design_2026_08_03.md`;
- `docs/research/saq_component_oracle_diagnostic_result_2026_08_03.md`;
- `docs/research/saq_joint_component_oracle_result_2026_08_03.md`;
- `docs/research/saq_joint_component_closest_primary_work_mechanism_review_2026_08_03.md`.

## Read and write boundary

Allowed reads are production SAQ source, focused diagnostic source/results,
the research charter, and primary papers.  The two prior diagnostic artifacts
may be referenced but need not be read again:

- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs`;
- `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index`.

Do not read benchmark queries, ground truth, query-result tables, another
dataset/index, or generated result payloads beyond the accepted result notes.
Do not modify production or diagnostic code.  Documentation writes are limited
to this task file, the decision log, and the focused mechanism review.

## Fixed scientific boundary

Keep the current PCA view, IVF assignments, five-segment plan, per-segment
codes/factors, serialized storage, accurate estimator, and query work fixed.
No per-vector dispatch, extra metadata, query-trained rule, bit/boundary sweep,
or new codebook family is authorized.

The review must distinguish:

- additive estimator error from coupled encoder state;
- oracle localization from implementable matched-storage improvement;
- a genuinely SAQ-specific mechanism from direct composition, parameter
  variation, AQ/CQ, distance-encoded PQ, or generic estimator-aware loss.

## Commands and budget

Allowed commands are read-only repository inspection, Git diff/status checks,
and primary-source retrieval.  Do not compile, run the diagnostic, build an
index, or execute a method experiment.  Budget: 0.25 CPU-hours, 0.5 wall-hours,
one thread, and no generated experiment output.

## Deliverables and done criteria

Done means the focused review:

1. derives the current additive estimator and explains the oracle interaction;
2. quantifies the pair's true dimension, bit, and exact-storage scope;
3. checks SAQ, transform/PQ decomposition, distance-encoded PQ, AQ/CQ, and
   estimator-aware primary work;
4. classifies each plausible implementation as covered, boundary-changing, or
   genuinely open;
5. gives one smallest next action and a scientific stop condition.

Current blocker: none.  Review outcome is `NO_GO_DIRECT_IMPLEMENTATION` with
one static question open: prove or refute non-separability of an allowed
base-only objective over the existing code and rescale variables.

One concrete next action is the static two-segment feasible-objective audit
specified in the review.  Do not implement an encoder or read benchmark
queries.  If a non-separable allowed objective is found, return to the user
before changing the scientific question or closest-baseline set.

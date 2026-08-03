# Active Task: SAQ two-segment feasible-objective static audit

## State and question

- Branch: `saq-mixed-radix-query`
- Base snapshot: `7be0f68`
- Modes: `IDEATE`, `REVIEW`

The completed joint-component diagnostic returned `PAIR_ACTIONABLE` for exact
replacement of `192d@6b + 320d@4b`, and the closest-work review blocked direct
implementation.  The active static question was:

> Does the fixed SAQ code/rescale feasible set admit any base-only,
> matched-storage, no-extra-query-work objective that is genuinely
> non-separable across the two segments?

Static result: standard reconstruction and unseen-direction objectives are
separable, but workload-conditioned objectives need not be.  Empirical
base-direction estimator MSE is non-separable exactly when the cross-block
second moment is nonzero on the feasible residual-difference spans.  Pairwise
ranking loss also has a direct non-separable counterexample.  The coupling is
introduced by a workload model, not by the SAQ representation itself.

The completed evidence and active review are:

- `docs/research/saq_component_oracle_diagnostic_design_2026_08_03.md`;
- `docs/research/saq_component_oracle_diagnostic_result_2026_08_03.md`;
- `docs/research/saq_joint_component_oracle_result_2026_08_03.md`;
- `docs/research/saq_joint_component_closest_primary_work_mechanism_review_2026_08_03.md`;
- `docs/research/saq_two_segment_feasible_objective_static_audit_2026_08_03.md`.

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

Done means the focused audit:

1. defines the exact per-segment code/rescale feasible variables;
2. proves separability for reconstruction, worst-case unseen direction, and
   isotropic/block-diagonal average-case MSE;
3. states a necessary and sufficient cross-moment condition for non-separable
   quadratic estimator loss;
4. gives CAQ-compatible counterexamples for base-direction and ranking losses;
5. separates mathematical existence from an authorized or novel method.

Current blocker: a scientific choice, not an implementation defect.  The audit
is complete with `SEPARABLE_STANDARD_OBJECTIVES` and
`NONSEPARABLE_WORKLOAD_OBJECTIVES_EXIST`.

One concrete next action is for the user to choose whether to close the
pair-oracle direction or pivot explicitly to base-trained estimator-aware
joint code selection.  Do not implement an encoder, inspect data covariance,
or read benchmark queries before that checkpoint.  If the pivot is selected,
the cheapest next evidence is a frozen base-only projected-cross-term and tiny
joint upper-bound diagnostic, not a production consumer.

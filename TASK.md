# TASK.md

## Current Research Milestone

The bounded primary-source review and documentation-only V2 protocol design
are complete. The review returned `GO_PROTOCOL_DESIGN`; the current maximum
outcome is `PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION`. This is a protocol
milestone, not a synthetic gate result and not evidence that the direction is
feasible on base data.

Current authorization is documentation-only:

```text
A4-V2-R     bounded primary-source review             COMPLETED_DOCUMENTATION
A4-V2-D     cost/evidence-model go/no-go decision     GO_PROTOCOL_DESIGN
A4-V2-P     preregistration/schema/contract            COMPLETED_DOCUMENTATION
A4-V2-I     source implementation                      NOT_AUTHORIZED
A4-V2-PAR   build and frozen parity execution          NOT_AUTHORIZED
A4-V2-SRUN  one logical synthetic admission event     NOT_AUTHORIZED
data        benchmark/base/query/index reads           NOT_AUTHORIZED
```

Each future stage requires a separate explicit user authorization; one never
implies the next. No current authorization permits a build, implementation,
RNG, synthetic run, data read, or SAQ modification.

## Frozen V2 Outcome

The positive target is the four-arm diagnostic bundle under the A4 reference
decoder/lookup interface frozen before the old cost result at `3aa2f6e`. It is
not byte-equivalent or estimator-equivalent to current SAQ and is not a
full-vector ANN index.

The primary gate is:

```text
T_instrument = C_setup + C_core + C_bundle_io
PASS iff T_instrument <= 34,560,000,000 CPU microseconds
```

The cap is internal to the one synthetic panel. The old `5/2` real-dataset
projection does not transfer. Build, parity, evidence emission, independent
full replay, archive, memory, and bytes remain separately metered and mandatory
for any admissible later decision.

## Preserved Predecessor Result

The prior A4-1S gate remains terminal at
`saq-arbitrary-cardinality-analysis@f1b464b`, with cost evidence at `9ce1052`.
It stopped after 61 complete coordinate shards because the frozen `5/2`
projection was `24.170246892361` CPU-hours, above the registered 24-hour
ceiling. Full-detail canonical serialization was inside that timed pipeline.

This branch must neither overturn nor rerun that result. Its question is
whether primary work and a predeclared claim decomposition justify a new
protocol that reports, rather than hides, the distinction between:

```text
scientific construction work
independent verification work
archival evidence serialization and I/O
end-to-end reproducibility work
permanent and transient memory
future query/index work, if ever authorized
```

## Completed Deliverables

1. `docs/saq_a4_v2_cost_evidence_primary_source_review_2026_07_14.md`.
2. `docs/saq_a4_v2_primary_source_metadata_2026_07_14.json`.
3. `docs/saq_a4_v2_cost_evidence_go_no_go_memo_2026_07_14.md`.
4. `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md`.
5. `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`.
6. `docs/saq_a4_v2_artifact_schema_2026_07_14.json`.

Before these become authoritative, they must pass independent review, be
committed in focused commits, and receive the mandatory Meeting Summary
Handoff. Untracked drafts and WIP are never evidence.

## Review Boundaries

The review is limited to the closest work needed to decide the protocol:

- exact one-dimensional weighted quantization or clustering and its DP/Monge
  optimizations;
- reproducible and independently checkable computational evidence, including
  certificates, commitments, and deterministic replay;
- benchmark timing and resource-ledger methodology relevant to separating
  algorithm work from artifact materialization; and
- the nearest fixed-rate ANN quantization work needed to keep the claim tied
  to an ANN-relevant construction question.

Do not perform a broad literature survey, implement a prototype, inspect any
dataset, or use outcome-dependent empirical measurements to choose the new
ledger.

## Decision Standard

Return `GO_PROTOCOL_DESIGN` only if all are supported before execution:

- exactness and relevant tie semantics remain independently checkable;
- no construction, verification, serialization, I/O, or memory work vanishes
  from reporting;
- the primary feasibility timer corresponds to a defensible scientific claim
  rather than a convenient cheaper number;
- a separate end-to-end ledger prevents misleading systems or practicality
  claims;
- thresholds and failure precedence are frozen without using the old outcome
  to tune them; and
- the resulting study could falsify an ANN-relevant opportunity rather than
  merely demonstrate faster artifact production.

Stop after independent review, focused commits, push, and Meeting Summary
Handoff. Await explicit authorization for one named future stage; do not infer
it from protocol publication.

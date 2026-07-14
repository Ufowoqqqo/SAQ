# TASK.md

## Current Research Milestone

The bounded primary-source review and V2 protocol design are complete. The
review returned `GO_PROTOCOL_DESIGN`, and the original reviewed protocol
remains byte-frozen at `f86a51d`. The user subsequently authorized `A4-V2-I`,
but static source inspection exposed a terminal `P_parity` receipt/publication
self-reference before any implementation commit or review pass. The user then
explicitly authorized additive, documentation-only `A4-V2-P-ERRATUM`. The
corrected authority at `f13a383` passed exact-commit measurement, schema, and
Git-authority review.

The erratum is complete. The prior source authorization remains available but
was not resumed by this documentation stage:

```text
A4-V2-R     bounded primary-source review             COMPLETED_DOCUMENTATION
A4-V2-D     cost/evidence-model go/no-go decision     GO_PROTOCOL_DESIGN
A4-V2-P     preregistration/schema/contract            COMPLETED_DOCUMENTATION
A4-V2-P-ERRATUM finite PAR-report closure correction   COMPLETED_REVIEW_PASS
A4-V2-I     source implementation/static review         AUTHORIZED_READY_TO_RESUME
A4-V2-PAR   build and frozen parity execution          NOT_AUTHORIZED
A4-V2-SRUN  one logical synthetic admission event     NOT_AUTHORIZED
data        benchmark/base/query/index reads           NOT_AUTHORIZED
```

The completed erratum stage permitted only additive authority documents,
static review, focused commits, push, and Meeting Summary Handoff. It permitted
no implementation edit, build, Python import, syntax/test command, RNG,
synthetic run, generated scientific artifact, data read, or SAQ modification.
Untracked implementation WIP remains nonevidence.

## A4-V2-P-ERRATUM Deliverables

1. A prose erratum binding parent protocol commit `f86a51d` and superseding
   only the missing terminal-P closure clauses.
2. A machine-readable erratum contract.
3. A closed 15-key PAR-seal schema and canonical maximal-size witness.
4. A composite authority manifest preserving the exact parent blobs.
5. Independent static review of the exact committed erratum authority.
6. Focused push and mandatory Meeting Summary Handoff.

Its outcome is `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS` at reviewed target
`f13a383a0085c456ed2f02d3ee9e041f1c70da6e`. It is not a source, parity,
synthetic, or feasibility result.

## A4-V2-I Deliverables

1. A self-contained producer native implementation preserving the frozen
   A4-1S scientific semantics and native-child work granularity.
2. A new long-lived V2 supervisor implementing the 396-unit state machine,
   timers, receipts, byte/resource ledgers, atomic bundle, and encode-only
   evidence phase.
3. A physically independent verifier implementation that shares no producer
   solver, allocation/tie, rounding, block, packing, parser, or logical-record
   encoder code.
4. Separate archive and finite three-file trailer source.
5. A source/provenance and implementation-binding crosswalk.
6. Independent static review of the exact committed implementation source.

The maximum stage outcome is
`SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`. It authorizes nothing beyond asking
whether to start `A4-V2-PAR`.

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

These protocol objects passed independent review, were committed in focused
commits, and received the mandatory Meeting Summary Handoff before
`A4-V2-I` authorization. Untracked drafts and WIP remain nonevidence.

The completed additive erratum deliverables are:

1. `docs/saq_a4_v2_par_report_erratum_authorization_2026_07_14.md`.
2. `docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.md`.
3. `docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.json`.
4. `docs/saq_a4_v2_par_report_seal_schema_2026_07_14.json`.
5. `docs/saq_a4_v2_par_report_seal_maximal_instance_2026_07_14.json`.
6. `docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json`.
7. `docs/saq_a4_v2_par_report_timing_closure_erratum_independent_review_2026_07_14.md`.

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
Handoff. The earlier explicit A4-V2-I authorization then remains available but
is not resumed as part of this erratum stage. `A4-V2-PAR` and `A4-V2-SRUN`
still require separate explicit authorization; never infer either from
protocol publication.

# TASK.md

## Active Research Task

Conduct a bounded primary-source review of whether the A4-1S terminal result
supports a scientifically legitimate new feasibility protocol with separate
construction, verification, and archival-evidence cost ledgers.

Current authorization is documentation-only:

```text
A4-V2-R  bounded primary-source review             AUTHORIZED
A4-V2-D  cost/evidence-model go/no-go decision     AUTHORIZED
A4-V2-P  new preregistration, only if review GO    AUTHORIZED_TO_WRITE
A4-V2-X  implementation or execution               NOT_AUTHORIZED
data     synthetic RNG or benchmark inputs         NOT_AUTHORIZED
```

The maximum outcome of this task is
`PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION`. If the review cannot defend a
new scientific question and complete non-hidden cost ledger, stop with
`NO_GO_REOPENING`.

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

## Required Deliverables

1. A bounded review with explicit search scope, inclusion/exclusion rules,
   closest primary sources, and source-by-source applicability.
2. Machine-readable source metadata sufficient to recheck titles, versions,
   identifiers, URLs, and supported claims.
3. A decision memo returning either `GO_PROTOCOL_DESIGN` or
   `NO_GO_REOPENING`.
4. Only after `GO_PROTOCOL_DESIGN`, a frozen V2 preregistration that is
   explicitly marked `NOT_AUTHORIZED_FOR_EXECUTION`.
5. Independent review before treating the decision or protocol as a committed
   milestone.
6. After commit and review, the mandatory Meeting Summary Handoff.

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

Until a separately committed and reviewed execution authorization exists,
stop after writing and reviewing the protocol.

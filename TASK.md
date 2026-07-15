# TASK.md

## Current Research Milestone

The bounded primary-source review, V2 protocol design, additive timing-closure
erratum, and source-only implementation stage are complete. The original
reviewed protocol remains byte-frozen at `f86a51d`; corrected composite
authority `f13a383` passed exact-commit measurement, schema, and Git-authority
review. After that handoff, the prior `A4-V2-I` authorization resumed.

Initial implementation commit `3a4f7c5` failed static review and remains
failed/non-evidence. Corrected exact commit
`482c401521460d1742ffe86c39db7130ed038a06` passed three independent
exact-commit static reviews with no remaining issue at LOW or above. The
later exact source-repair commit
`e48df4523f99c085cfcb83623664054b5f9ae6f7` also passed three independent
exact-commit reviews with no issue at LOW or above. The maximum authorized
source-only outcomes are therefore reached:

```text
A4-V2-R     bounded primary-source review             COMPLETED_DOCUMENTATION
A4-V2-D     cost/evidence-model go/no-go decision     GO_PROTOCOL_DESIGN
A4-V2-P     preregistration/schema/contract            COMPLETED_DOCUMENTATION
A4-V2-P-ERRATUM finite PAR-report closure correction   COMPLETED_REVIEW_PASS
A4-V2-I     source implementation/static review         COMPLETED_REVIEW_PASS
A4-V2-PAR   pre-build executable identity admission    ARTIFACT_INVALID / REVIEWED_TERMINAL
A4-V2-I-R1  executable-identity source repair           COMPLETED_REVIEW_PASS
A4-V2-CACHE-P cache/staging documentation protocol      AUTHORIZED_DOCUMENTATION_ONLY
A4-V2-PAR-R1 corrected build/parity event               NOT_AUTHORIZED
A4-V2-SRUN  one logical synthetic admission event     NOT_AUTHORIZED
data        benchmark/base/query/index reads           NOT_AUTHORIZED
```

On 2026-07-15 the user explicitly authorized `A4-V2-PAR build/parity gate`.
The additive authority receipt is
`docs/saq_a4_v2_par_authorization_2026_07_15.md`. Before execution, the focused
authorization/status change was committed, pushed, and independently reviewed
at clean execution base `2e983a0`, with the exact 35-source manifest and
`d5b837...` source tree unchanged.

The one authorized top-level event then returned frozen status
`ARTIFACT_INVALID` before prelaunch observation or a B/P worker. The conductor
created its empty staging directory, then rejected `/bin/python` because the
leader-identity read uses `O_NOFOLLOW` and that path object is a symlink. It
did not build, collect NumPy authority, generate PCG64 fixtures, create a B/P
receipt, or publish a manifest, index, summary, or seal. The terminal record is
`docs/saq_a4_v2_par_prebuild_artifact_identity_failure_2026_07_15.md`.

Exact terminal target `30dfada` passed three-track independent review with no
finding at LOW or above. The durable review is
`docs/saq_a4_v2_par_prebuild_artifact_identity_failure_independent_review_2026_07_15.md`.

There is no valid PAR authority and no scientific decision. The empty staging
directory and five ignored Python caches are quarantined non-evidence. Do not
clean for retry, invoke the command again, substitute a resolved interpreter,
generate the SRUN panel, enter the 396-unit construction, or continue to an
execution stage automatically.

After the terminal handoff stated that the next admissible step was a clean
executable-identity source correction plus independent review, the user
instructed `继续`. The additive authorization is
`docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md`.
It opens only `A4-V2-I-R1`: a bounded source correction and static independent
review. It permits no cleanup, import, build, test, parity, RNG, SRUN, data
read, or SAQ change. Corrected execution is reserved as `A4-V2-PAR-R1` and
remains unauthorized.

## A4-V2-I-R1 Deliverables

1. Bind leader identity to the already-running CPython image through a stable
   `/proc/self/exe` descriptor and require the intentionally followed
   `sys.executable` path to name the same regular inode.
2. Apply that identity consistently to conductor, runner receipts/admission,
   and a physically independent verifier implementation without weakening
   generic no-follow artifact readers.
3. Update only the implementation binding, source-provenance crosswalk, and
   canonical 35-source manifest required by those source changes; rebind the
   existing manifest `authorization_identity` to the additive I-R1 receipt
   without adding a schema key.
4. Commit and independently review the exact repaired source using only
   static inspection, Git identities, hashes, byte sizes, canonical manifest
   recomputation, and diff checks.
5. Push and perform the mandatory Meeting Summary Handoff, then stop before
   `A4-V2-PAR-R1` authorization.

The maximum result is `SOURCE_REPAIR_STATIC_REVIEW_PASS`. It is not parity,
artifact execution readiness, scientific evidence, or a method claim.

The bounded three-file correction, binding, provenance, and manifest
rebinding passed exact-commit independent review. The durable verdict is
`docs/saq_a4_v2_executable_identity_source_repair_independent_review_2026_07_15.md`.
Its source-tree SHA-256 is
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.

The five quarantined bytecode files expose a separate import-cost and
unmetered-cache-byte determinism question. It was not causal to the executable-
identity failure and is outside I-R1. Do not add a bytecode admission policy or
open PAR-R1 until the user separately authorizes a resolution.

The user has now authorized only `A4-V2-CACHE-P`, recorded in
`docs/saq_a4_v2_cache_staging_policy_authorization_2026_07_15.md`. This stage
must review official CPython cache semantics and committed local source, then
produce a fail-closed protocol for bytecode determinism and bounded handling
of the named residuals. It must not read bytecode payloads, clean or alter the
residuals, edit implementation source, change the future runtime environment,
import/build/test/run anything, or open PAR-R1. Its maximum outcome is
`CACHE_STAGING_POLICY_REVIEW_PASS`.

## A4-V2-CACHE-P Deliverables

1. Bounded official-primary-source and local-static review of Python cache
   read/write behavior and the current A4-V2 import/admission chain.
2. A fail-closed protocol specifying exact residual inventory, no-follow
   identity/disposition rules, cache-mode binding and runtime attestation,
   error precedence, and complete preparation/runtime byte and cost ledgers.
3. A machine-readable contract and explicit determination of whether a later
   minimal implementation/preparation stage is required.
4. Exact-commit independent review proving the 35-source closure, manifest,
   and source-tree identity unchanged.
5. Focused push and mandatory Meeting Summary Handoff, followed by a stop.

Cleanup/source/environment work and `A4-V2-PAR-R1` each remain separately
unauthorized after this documentation stage.

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
`SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`; exact commit `482c401` reached that
outcome. That historical static result did not establish executable readiness;
the later PAR invocation stopped at artifact identity admission. Neither
result authorizes `A4-V2-SRUN`.

## A4-V2-PAR Terminal Failure

The exact command at `2e983a0` returned exit `3` and stderr
`ARTIFACT_INVALID: [Errno 40] Too many levels of symbolic links:
'/bin/python'`. The failure occurred before any build or parity worker. Its
maximum conclusion is:

```text
ARTIFACT_INVALID
STOPPED_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

It is not `PASS_PARITY`, a parity mismatch, a resource observation, or evidence
about arbitrary-cardinality quantization. The in-conductor external-signal
retry rule does not apply, and the consumed one-event authorization grants no
second top-level invocation. Exact target `30dfada` is independently reviewed
terminal evidence only for that failure classification. Any correction
requires a new clean source commit, independent review, and new explicit
authorization for the affected PAR stage.

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

The completed source-only implementation deliverables are:

1. exact corrected source commit
   `482c401521460d1742ffe86c39db7130ed038a06`;
2. `docs/saq_a4_v2_implementation_binding_2026_07_14.md`;
3. `docs/saq_a4_v2_implementation_manifest_2026_07_14.json`;
4. `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md`; and
5. `docs/saq_a4_v2_implementation_independent_review_2026_07_15.md`.

The manifest binds 35 exact source identities and source-tree SHA-256
`d5b8374ff2bfb967e0fbf758e2012029356ef779122681ed4a5a9d901e727cc7`.
No implementation was imported, built, syntax-checked, tested, or executed;
no scientific artifact was generated.

The completed executable-identity source-repair deliverables are:

1. additive authorization
   `docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md`;
2. exact repaired source commit
   `e48df4523f99c085cfcb83623664054b5f9ae6f7`; and
3. `docs/saq_a4_v2_executable_identity_source_repair_independent_review_2026_07_15.md`.

This reaches `SOURCE_REPAIR_STATIC_REVIEW_PASS` only. No implementation was
imported, syntax-checked, built, tested, or executed, and no PAR/scientific
artifact was generated.

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

The reviewed A4-V2-PAR terminal failure remains immutable. Completed
`A4-V2-I-R1` does not change the status of the empty staging directory or
ignored Python caches: they remain non-evidence and must not be synchronized
or cleaned. Only the documentation-only `A4-V2-CACHE-P` review/protocol stage
is active. There is no cleanup, cache-policy implementation, PAR-R1, SRUN,
data, or SAQ authority; never infer one from the historical source review,
failed invocation, repaired source, or documentation authorization.

# AGENTS.md

Durable guidance for Codex sessions on the
`saq-arbitrary-cardinality-feasibility-v2` branch.

## Research Frame

Work as a doctoral researcher seeking a SIGMOD/VLDB/ICDE-level database-
systems contribution. Code and artifact machinery are supporting instruments,
not contributions by themselves. For every proposed step, state the SAQ-
specific limitation, closest primary work, falsifiable claim, construction,
storage, verification, and query costs, and the likely objection from a strict
reviewer.

Before proposing an implementation, review the closest primary work and state
what it already solves, what remains open, and why the proposal is not a
direct composition, parameter variant, or artifact-engineering result.

## Branch Boundary And Authorization

This branch starts from `saq-correctness-base@bc7829b` and retains only the
positive one-bit packing and finite padded-lane block-min correctness fixes.
Treat every other SAQ branch as historical evidence, not an implementation
dependency. Do not merge or cherry-pick their runners, generated artifacts,
or method variants.

On 2026-07-14 the user first authorized only:

1. a bounded primary-source review of the cost-model and evidence-generation
   boundary exposed by A4-1S; and
2. if that review supports reopening, a new preregistration describing a
   scientifically defensible cost ledger and sufficient evidence contract.

That documentation-only stage ended at the reviewed protocol commit
`f86a51d`. The user then explicitly authorized `A4-V2-I`. Static source
inspection exposed a terminal `P_parity` receipt/publication self-reference,
so implementation stopped before a commit or review pass. On 2026-07-14 the
user explicitly authorized the documentation-only `A4-V2-P-ERRATUM` stage.
The corrected authority at `f13a383` passed three-track exact-commit review;
the verdict is recorded in
`docs/saq_a4_v2_par_report_timing_closure_erratum_independent_review_2026_07_14.md`.

After the erratum Meeting Summary Handoff, the prior `A4-V2-I` source
authorization was resumed. Initial source commit `3a4f7c5` failed static
review and remains failed/non-evidence. Corrected exact commit
`482c401521460d1742ffe86c39db7130ed038a06` passed three-track independent
static review; its verdict is recorded in
`docs/saq_a4_v2_implementation_independent_review_2026_07_15.md`.
`A4-V2-I` is complete at `SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`. No compiler,
build, Python import, syntax/test command, native execution, parity fixture,
RNG, synthetic event, generated artifact, benchmark/data read, or SAQ
modification occurred during that stage.

On 2026-07-15 the user explicitly authorized `A4-V2-PAR` build/parity only.
The additive receipt is
`docs/saq_a4_v2_par_authorization_2026_07_15.md`. Before any import, build, or
fixture execution, commit, push, and independently review that focused
authorization/status change while proving the 35 reviewed source blobs and
source-tree identity unchanged. Then run only the exact frozen PAR conductor
from that clean reviewed commit. The fixed PAR inventory includes its
registered `PCG64(20260713)` scalar and block fixtures; it does not authorize
the SRUN panel. `A4-V2-SRUN`, benchmark/data access, and SAQ modification
remain separately unauthorized.

That single authorized invocation ran from reviewed and pushed execution base
`2e983a0` on 2026-07-15. It stopped before prelaunch observation or any B/P
worker because `sys.executable` was the `/bin/python` symlink and the frozen
leader-identity reader required a no-follow regular file. The exact frozen
status is `ARTIFACT_INVALID`; there is no valid PAR authority and no scientific
decision. The terminal facts are recorded in
`docs/saq_a4_v2_par_prebuild_artifact_identity_failure_2026_07_15.md`. No
build, parity fixture, RNG, B/P receipt, artifact index, or seal was produced.
The empty staging directory and ignored Python caches are quarantined WIP,
not evidence. Do not rerun, substitute another Python path, clean for retry,
or repair source under this authorization. Exact terminal target `30dfada`
passed three-track independent review with no finding at LOW or above; its
review is
`docs/saq_a4_v2_par_prebuild_artifact_identity_failure_independent_review_2026_07_15.md`.

After the terminal handoff described the next admissible source-correction
step, the user instructed `继续`. That instruction is narrowly bound as
`A4-V2-I-R1`, a static-only repair of CPython leader executable identity. Its
additive authority is
`docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md`.
Before implementation source changes, that authority/status commit must be
pushed and independently exact-reviewed while the prior 35 source blobs,
manifest, and source-tree identity remain unchanged. The maximum later result
is `SOURCE_REPAIR_STATIC_REVIEW_PASS`. Corrected build/parity is reserved as
`A4-V2-PAR-R1` and remains separately unauthorized; source repair authorizes
neither cleanup nor execution.

The completed `A4-V2-P-ERRATUM` permitted only additive protocol-authority
documents, branch status documents, focused commits, static independent
review, push, and the required Meeting Summary Handoff. Do not edit or commit
implementation WIP under that authorization.

## Review And Protocol Outcome

The bounded review returned `GO_PROTOCOL_DESIGN`. The original reviewed
protocol remains byte-preserved at `f86a51d`. The erratum adds a reviewed
composite authority without rewriting those parent blobs. Its outcome is
`PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS`; it is not a gate result. The
parent authoritative documents are:

- `docs/saq_a4_v2_primary_source_metadata_2026_07_14.json`;
- `docs/saq_a4_v2_cost_evidence_primary_source_review_2026_07_14.md`;
- `docs/saq_a4_v2_cost_evidence_go_no_go_memo_2026_07_14.md`;
- `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md`;
- `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`; and
- `docs/saq_a4_v2_artifact_schema_2026_07_14.json`.

The additive erratum protocol and composite-authority records are:

- `docs/saq_a4_v2_par_report_erratum_authorization_2026_07_14.md`;
- `docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.md`;
- `docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.json`;
- `docs/saq_a4_v2_par_report_seal_schema_2026_07_14.json`;
- `docs/saq_a4_v2_par_report_seal_maximal_instance_2026_07_14.json`;
- `docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json`.

Their independent verdict is:

- `docs/saq_a4_v2_par_report_timing_closure_erratum_independent_review_2026_07_14.md`.

The positive object is an **A4-reference-equivalent four-arm diagnostic
bundle** whose scientific interface was frozen before the old cost outcome at
`saq-arbitrary-cardinality-analysis@3aa2f6e`. It is not byte-equivalent or
estimator-equivalent to current SAQ, not a full-vector ANN index, and not a
deployable representation.

The new primary FOM is complete comparative-instrument construction CPU:

```text
T_instrument = C_setup + C_core + C_bundle_io
PASS iff T_instrument <= 34,560,000,000 CPU microseconds
```

That number is an internal one-panel admission cap only. The predecessor's
`5/2` real-dataset projection does not transfer to the new FOM. Build, parity,
independent full replay, evidence emission, archive work, memory, and bytes
remain mandatory separately reported terms. A finite three-file reporting
trailer and the additive one-file `PAR_report` are the only disclosed timing-
closure exclusions. `PAR_report` changes no metered formula or scientific
boundary.

Current stages remain separate:

```text
A4-V2-P-ERRATUM documentation-only closure correction  COMPLETED_REVIEW_PASS
A4-V2-I     source implementation/static review         COMPLETED_REVIEW_PASS
A4-V2-PAR   pre-build executable identity admission     ARTIFACT_INVALID / REVIEWED_TERMINAL
A4-V2-I-R1  executable-identity source repair           AUTHORIZED_STATIC_ONLY
A4-V2-PAR-R1 corrected build/parity event                NOT_AUTHORIZED
A4-V2-SRUN  one logical synthetic admission event only  NOT_AUTHORIZED
```

Authorization for one stage never implies the next. No stage above permits
benchmark/base/query/index reads or SAQ modification.

The authoritative implementation-stage documents are:

- `docs/saq_a4_v2_implementation_authorization_2026_07_14.md`;
- `docs/saq_a4_v2_implementation_binding_2026_07_14.md`;
- `docs/saq_a4_v2_implementation_manifest_2026_07_14.json`;
- `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md`; and
- `docs/saq_a4_v2_implementation_independent_review_2026_07_15.md`.

The PAR authorization and reviewed terminal pre-build failure records are:

- `docs/saq_a4_v2_par_authorization_2026_07_15.md`;
- `docs/saq_a4_v2_par_prebuild_artifact_identity_failure_2026_07_15.md`; and
- `docs/saq_a4_v2_par_prebuild_artifact_identity_failure_independent_review_2026_07_15.md`.

The source pass remains a historical static-review result only. The attempted
PAR launch falsified executable artifact readiness before build; it is not a
parity result, synthetic gate, SAQ limitation result, method contribution, or
systems-performance claim. `A4-V2-I-R1` is active only for source repair and
static review. There is no active cleanup, PAR, SRUN, data, or SAQ execution
authorization.

## Prior A4-1S Result

The prior formulation remains terminal on
`saq-arbitrary-cardinality-analysis@f1b464b`. Its committed cost evidence is
at `9ce1052`, and its authoritative review is
`docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md` on that branch.

The registered early stop occurred after 61 complete scalar-coordinate
shards. The timed region used `34,805,155,525 us`; the frozen `5/2` projection
was `87,012,888,812.5 us`, or `24.170246892361` CPU-hours, above the 24-hour
ceiling. That result measures the frozen construction/evidence pipeline,
including canonical full-detail serialization. It is not a scalar-solver-only
lower bound, a production encoding measurement, or evidence that arbitrary
cardinalities are ineffective.

Do not revise, rerun, reinterpret, or rescue that gate. Any viable follow-up
must be a new protocol with a new question and ledger, while preserving the
old result unchanged as negative evidence.

## Review Questions

The bounded review must answer all of the following before a protocol is
accepted:

- Which operations are part of the scientific construction being evaluated,
  and which are verification or archival evidence costs?
- What evidence is minimally sufficient for deterministic independent replay
  of exact scalar optima, allocation decisions, representation semantics, and
  gate accounting?
- Would hashing, certificates, streaming, or sampled independent replay
  preserve the relevant correctness claim, or merely move hidden work outside
  the measured ledger?
- Does a revised ledger answer an ANN/quantization feasibility question, or
  only make an experimental artifact cheaper?
- Are construction, verification, serialization, transient memory, permanent
  bytes, and later query work all visible as separate non-overlapping terms?
- Does the proposed rule remain falsifiable without an outcome-dependent
  threshold, machine change, reduced shape, or post-hoc variant sweep?

Use primary papers, author artifacts, official standards, or official source
repositories. Record stable identifiers, URLs, versions, access dates, and the
specific claim each source supports. Secondary summaries may help discovery
but are not evidence.

## Protocol Requirements

A new protocol may be written only if the review concludes that a revised
ledger preserves exactness and auditability while measuring a distinct,
scientifically relevant construction question. It must:

- name the old A4-1S result as a failed predecessor, not a pilot to discard;
- distinguish construction, verification, archival serialization, and
  end-to-end evidence costs before any execution;
- specify exact inclusions, exclusions, timers, hashes or certificates,
  independent checks, failure precedence, resource ceilings, and atomic
  stopping behavior;
- count every excluded operation in a separately reported ledger rather than
  making it disappear;
- freeze the machine, compiler, libraries, precision, shape, seeds, and output
  schema needed by its claim;
- forbid real data until a separately authorized synthetic validation and
  cost gate passes; and
- state that protocol publication does not authorize implementation or run.

If the review cannot justify these conditions, record `NO_GO_REOPENING` and do
not write an executable protocol merely because the user requested another
attempt.

## Meeting Summary Handoff

The canonical direction registry and current meeting deck live on branch
`saq-meeting-summary`. Locate its worktree with `git worktree list`; never
assume a fixed path.

After each committed and independently reviewed protocol, gate result, or
terminal decision, this session owns a handoff. Before editing the summary
worktree, re-read its `AGENTS.md` and registry, fetch, require it to be clean
and equal to its remote, record that commit, and atomically acquire the
mandatory `saq-meeting-summary-edit.lock` under the Git common directory.
Update the registry first, update the deck only if this direction is selected,
stage only focused summary files, fetch again before push, never force-push,
and release the lock after a successful push or clean abort.

Only committed and independently reviewed evidence may be synchronized.
Untracked files, search notes, provisional drafts, running work, and generated
artifacts are never evidence. A summary handoff grants no experimental
authorization.

## Repository Layout

- `docs/`: primary-source review, frozen protocol, implementation binding, and
  independent source-review documents.
- `research/a4_v2/`, `research/a4_v2_verifier/`: V2-only native source; never
  include, link, or load a historical worktree at runtime.
- `script/a4_v2_*.py` and `script/run_arbitrary_cardinality_a4_v2.py`: V2-only
  source. Producer and verifier scientific implementations must remain
  physically independent as frozen by the protocol.
- `saqlib/`, `src/`, existing non-V2 `script/`, and `unit_test/`: out of scope;
  do not modify them for A4 V2.
- `data/`, `results/`, `bin/`, and `build/`: do not open or generate under the
  current stopped boundary. The failed conductor created neither registered
  build directory. Their former one-event exception is consumed and grants no
  repair or retry authority.

## Verification

For `A4-V2-P-ERRATUM`, verification is limited to diff/whitespace checks,
structured-document parsing, exact blob identities, schema/contract static
inspection, and independent review. Do not touch implementation WIP.

Before committing A4-V2-I source and documentation:

```bash
git diff --check
git status --short --branch
```

Do not build, import, syntax-check, execute, or test the implementation during
`A4-V2-I`. Verification is limited to diff/whitespace checks, source-to-
contract inspection, and independent static review. Structured frozen
metadata may be inspected but must not be rewritten.

The same static-only verification boundary applies to `A4-V2-I-R1`. It may
recompute source/document SHA-256 values, byte sizes, and the canonical source-
tree preimage without importing repository Python. It must not delete or read
the contents of the quarantined bytecode files or remove the empty staging
directory.

The one authorized `A4-V2-PAR` invocation used the following exact command
from clean reviewed execution base `2e983a0`:

```bash
MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python script/run_arbitrary_cardinality_a4_v2.py \
  par docs/saq_a4_v2_par_artifacts_2026_07_14
```

It returned `ARTIFACT_INVALID` before build and published no PAR tree. The
command is retained here as history; do not invoke it again. Under that
consumed A4-V2-PAR authority, only the terminal failure memo and branch status
were committed and independently reviewed. No failure result authorizes SRUN.

## Do-Not Rules

- Do not run or modify the old A4-1S command.
- Do not manually build V2, alter the frozen PAR command, or run only a parity
  subset; `B_build` and the complete inventory belong inside the one conductor.
- Do not rerun PAR, replace `python` with a resolved interpreter, alter PATH,
  delete the quarantined staging directory to make the root absent, or clean
  ignored caches as a route to retry.
- Do not repair the executable-identity path under the consumed PAR authority.
  Only the additive `A4-V2-I-R1` source/static-review authority permits the
  bounded correction; it grants no cleanup, build, parity, or retry.
- Do not continue from PAR to `A4-V2-SRUN` without a later explicit user
  authorization, even if every parity fixture passes.
- Do not copy, cherry-pick, import, include, link, or execute the old A4-1S
  runner. Historical kernels may be used only as read-only semantic oracles;
  V2 source must be self-contained and its provenance/crosswalk explicit.
- Do not build, import, execute, or parity-test V2 source in `A4-V2-I`.
- Do not edit, stage, commit, or describe untracked A4-V2-I source as evidence
  during `A4-V2-P-ERRATUM`.
- Do not rewrite the three parent protocol objects frozen at `f86a51d`; the
  erratum is additive and supersedes only its explicitly named closure clauses.
- Do not treat the narrow `24.170246892361 > 24` result as a general complexity
  lower bound or as noise that may be ignored.
- Do not remove serialization from a primary timer without recording its full
  cost and explaining why it is outside the scientific construction claim.
- Do not replace exhaustive evidence with hashes or sampling unless the
  protocol states exactly what remains independently checkable.
- Do not use a faster implementation, different machine, approximate
  objective, reduced shape, or changed threshold as a post-hoc rescue.
- Do not read base, centroid, cluster-id, query, ground-truth, index, or prior
  untracked result files.
- Do not modify SAQ/CAQ, index, packing, estimator, or search code.
- Do not present evidence tooling, hashing, serialization, or benchmark
  bookkeeping as the database-systems contribution.

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

Exact source-repair commit
`e48df4523f99c085cfcb83623664054b5f9ae6f7` passed three-track independent
static review with no finding at LOW or above. Its canonical 35-source tree is
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`;
the verdict is recorded in
`docs/saq_a4_v2_executable_identity_source_repair_independent_review_2026_07_15.md`.
`A4-V2-I-R1` is complete at `SOURCE_REPAIR_STATIC_REVIEW_PASS`.

After being told that the next admissible step was a separately authorized
documentation-only bytecode-cache determinism and bounded residual-handling
protocol, with corrected PAR still requiring another authorization, the user
instructed `授权`. This is narrowly bound as `A4-V2-CACHE-P`. Its receipt is
`docs/saq_a4_v2_cache_staging_policy_authorization_2026_07_15.md`. It permits
only bounded official-source/local-static review, protocol and contract
documents, exact-commit review, push, and Meeting Summary Handoff. It permits
no bytecode-payload read, cleanup, source/environment change, import, build,
test, PAR-R1, SRUN, data access, or SAQ modification. The maximum outcome is
`CACHE_STAGING_POLICY_REVIEW_PASS`; any later implementation/preparation and
`A4-V2-PAR-R1` remain separately unauthorized.

The bounded CACHE-P review returned
`GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED / NO_GO_DIRECT_PAR_R1`.
Its four protocol objects are:

- `docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json`;
- `docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md`;
- `docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md`; and
- `docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json`.

Exact target commit `56210f8f81557ed7a2521bf7f13c9f937396da29`
changes only those four paths plus `AGENTS.md` and `TASK.md`, preserves
implementation-manifest Git blob
`2aa64e50dad19626711e0dd90c038704ac73e328`, all 35 source blobs, and source-
tree SHA-256
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.
It passed three-track exact-commit independent review with no finding at LOW
or above. The durable verdict is
`docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md`.
The exact target was independently reviewed. At formation of its direct-child
review record, commit/push and the later live review-head closure still
remained. Until both occurred, the durable stage status was
`EXACT_TARGET_REVIEW_PASS_PENDING_LIVE_CLOSURE`; the conditional maximum
remained `CACHE_STAGING_POLICY_REVIEW_PASS`.

The direct-child CACHE-P review record was subsequently committed and pushed
at `249d5b8c1939acefbf12711790b3e791b019d560`; its registered live review-head
closure succeeded and the Meeting Summary Handoff was pushed at
`saq-meeting-summary@d1e80147ae106afcb88c721a413fa65dff3e7750`. The live
closure remains an operational, non-evidentiary predicate and is not Meeting
Summary evidence.

On 2026-07-15 the user explicitly authorized `A4-V2-CACHE-I`. Its additive
receipt is
`docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md`. This stage
permits only the generic 37-file-source/38-executable-unit cache-policy source,
schemas, manifests, static closure, exact commits, no-clone equality probes,
independent static review, push, and mandatory Meeting Summary Handoff frozen
by CACHE-P. It permits no Python/import/build/test, clone, PREP, PAR-R1, SRUN,
data access, quarantine access, cleanup, environment mutation, or SAQ change.
The maximum outcome is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`. PREP authorization remains a
separate future user instruction.

Exact authorization target
`4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d` is the direct child of
`249d5b8c1939acefbf12711790b3e791b019d560`, changes exactly the additive
authorization plus `AGENTS.md` and `TASK.md`, and preserves manifest blob
`2aa64e50dad19626711e0dd90c038704ac73e328` and the 35-source tree. Three-track
exact-target review found no issue at LOW or above; its durable verdict is
`docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md`.
The authorization target reaches `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.
Before any implementation edit, its direct-child review must be committed and
pushed, the live review-head closure must succeed, and the distinct
implementation-parent admission probe must be recorded in the later additive
cache-authority manifest.

That review record was subsequently committed and pushed at
`187e363ee08d1f63888137c21fd5a533555bb248`; its live review-head closure and
the distinct implementation-parent admission predicate succeeded.  The
CACHE-I implementation worktree is now statically sealed to exactly 37
filesystem sources, 38 executable units, and source-tree SHA-256
`9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2`.
Its exact changed-path closure is the 22 paths frozen in the machine contract.
At formation of that seal, before its exact target commit and direct-child
independent review, the files were WIP/nonevidence and the stage status was
only
`STATIC_SEAL_COMPLETE_PENDING_EXACT_TARGET_COMMIT_AND_INDEPENDENT_REVIEW`.

After the source bytes were locked, the user separately authorized the narrow
`A4-V2-CACHE-I-SYNTAX` edge.  `/usr/bin/python3.9` `compile()`-only
syntax checks passed for the exact six changed/new outer Python sources and
the exact inline PREP bootstrap.  No code object was executed and no module
was imported.  This narrow check establishes syntax acceptance only; it does
not establish importability, executability, correctness, schema validity,
runtime behavior, or scientific evidence.  It does not authorize build,
fixture, RNG, PREP, cache-verifier, PAR-R1, SRUN, data, quarantine, or SAQ/CAQ
work.  Preserve the original CACHE-I machine-attestation literals and record
this later exception separately.

The exact CACHE-I implementation target was subsequently committed and pushed
at `c33a2bff7e0ec9c98596498fd43a7e629ccf47fe`, with direct parent
`187e363ee08d1f63888137c21fd5a533555bb248` and tree
`66eaf2f5df8792c3470b247e59857fc2e7a25461`.  Its direct-child independent
review is
`docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md`.
That review found zero issues at LOW or above, recorded the successful exact
target-head remote-equality closure, disclosed and excluded an earlier
sandbox-only DNS failure that returned no remote observation, and assigned
the maximum outcome
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.  This is artifact-governance
source/static-review evidence only.  The review record was subsequently
committed and pushed at `5db302537793bc05f541aede119255213ea49e14`,
tree `f3c8e0ca52cb719018f5ad82952c06724ab9105a`.  CACHE-I is complete
at `GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.  No PREP, CACHE-BIND,
PAR-R1, SRUN, data, quarantine, or SAQ/CAQ authority follows from this result.

On 2026-07-16 the user instructed exactly
`授权 PREP authorization/review`.  This is narrowly bound to formation,
push, and independent review of
`docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md`; actual
PREP remains unauthorized.

The exact authorization target was subsequently committed and pushed at
`e7f940e924a338022bfe8fffcbb3496f12a5a75c`, with direct parent
`5db302537793bc05f541aede119255213ea49e14` and tree
`0386af8066a93d84ca772604990a08737a34aa33`.  It changes only the
authorization document, `AGENTS.md`, and `TASK.md`.  The distinct PREP
parent-admission probe and the later target-head closure each returned their
exact registered remote OID with no sandbox preflight.  The sole independent
review is
`docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md`;
it found zero issues at LOW or above and assigned the documentation verdict
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.

That verdict is not the future whole-stage ceiling
`ISOLATED_CLONE_PREPARED_REVIEW_PASS` and does not authorize actual PREP.  The
unique PREP authorization-review-head probe was not run and remains unspent:
it is both review-head closure and immediate execution-base admission and may
run only immediately before a separately user-authorized PREP, with no
intervening source-branch/worktree mutation.  If that cannot hold, stop for
new authority.  This review record remains WIP/nonevidence until committed
and pushed.  No clone, token, PREP, receipt, CACHE-BIND, PAR-R1, data,
quarantine, or SAQ/CAQ action follows from this record.

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
A4-V2-I-R1  executable-identity source repair           COMPLETED_REVIEW_PASS
A4-V2-CACHE-P cache/staging documentation protocol      COMPLETED_OPERATIONAL_PROTOCOL_CLOSURE
A4-V2-CACHE-I generic source/schema/static review       GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
A4-V2-CACHE-PREP-AUTH authorization record/review       PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-CACHE-PREP-ISO one isolated-clone PREP attempt    NOT_AUTHORIZED
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

The executable-identity correction records are:

- `docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md`;
- `docs/saq_a4_v2_executable_identity_source_repair_independent_review_2026_07_15.md`.

The CACHE-P records are the four objects named above plus their independent
review:

- `docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md`.

The source pass remains a historical static-review result only. The attempted
PAR launch falsified executable artifact readiness before build; it is not a
parity result, synthetic gate, SAQ limitation result, method contribution, or
systems-performance claim. `A4-V2-I-R1` is now a reviewed source correction,
not execution evidence or artifact readiness. The CACHE-P review/push/closure/
handoff sequence is complete. CACHE-I is now authorized only at the generic
source/schema/static-review boundary described above. There is no quarantine
access, cleanup, clone, PREP, PAR, SRUN, data, or SAQ execution authorization.

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

`A4-V2-CACHE-P` is documentation-only. Verification is limited to official
primary-source review, committed local static inspection, structured-document
parsing without repository Python, exact Git/blob/tree identities, hashes,
byte sizes, diff/whitespace checks, and independent review. It may not read a
quarantined bytecode payload, remove or alter a residual, edit implementation
source, mutate the future execution environment, import, build, test, or run
PAR.

`A4-V2-CACHE-I` is also static-only. Verification is limited to committed
source/document inspection, non-repository structured-data parsing, Git/blob
identities, SHA-256 values, byte sizes, canonical source-tree recomputation,
exact raw-slice crosswalk inspection, diff/whitespace checks, no-clone remote-
equality probes, and independent review. Do not invoke Python for syntax or
schema checks and do not create the isolated clone or PREP state.

The sole exception is the separately authorized, already completed
`A4-V2-CACHE-I-SYNTAX` check recorded above.  It permits no further Python
invocation and must not be generalized into import, schema, build, test, or
runtime authority.

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
- Do not infer cleanup, environment mutation, clone/PREP, or PAR-R1 authority
  from CACHE-P or the now-authorized static-only CACHE-I stage. CACHE-I permits
  only its frozen generic source/schema closure and review.
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

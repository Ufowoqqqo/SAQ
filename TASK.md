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
A4-V2-CACHE-P cache/staging documentation protocol      COMPLETED_OPERATIONAL_PROTOCOL_CLOSURE
A4-V2-CACHE-I generic source/schema/static review       GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
A4-V2-CACHE-PREP-AUTH authorization record/review       PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-CACHE-PREP-ISO original one-shot authority        UNSPENT_BUT_NONTRANSFERABLE
A4-V2-PREP-HOST-P host-rebind erratum protocol/review   COMPLETED_REVIEW_PASS
A4-V2-PREP-HOST-I-AUTH source-rebind authorization      AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-PREP-HOST-I-ERRATUM source-authority correction   HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
A4-V2-PREP-HOST-I coherent source/authority rebind      SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
A4-V2-PREP-HOST-I-R1-P correction-only repair protocol HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS
A4-V2-PREP-HOST-I-R1 correction-only artifact repair    HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS
A4-V2-SOURCE-HISTORY-P epoch-correction protocol         SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS
A4-V2-SOURCE-HISTORY-I original source correction        STOPPED_PRE_TARGET_PATH_CLOSURE_UNSATISFIABLE
A4-V2-SOURCE-HISTORY-I-R1-P path-closure erratum         SOURCE_HISTORY_I_R1_PATH_CLOSURE_ERRATUM_REVIEW_PASS
A4-V2-SOURCE-HISTORY-I-R1 corrected source target        SOURCE_HISTORY_EPOCH_CORRECTION_R1_TARGET_FORMED_REVIEW_PENDING
A4-V2-CACHE-PREP-R1-AUTH fresh PREP authorization       NOT_AUTHORIZED
A4-V2-CACHE-PREP-ISO-R1 one future PREP attempt         NOT_AUTHORIZED
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

The user previously authorized only `A4-V2-CACHE-P`, recorded in
`docs/saq_a4_v2_cache_staging_policy_authorization_2026_07_15.md`. This stage
must review official CPython cache semantics and committed local source, then
produce a fail-closed protocol for bytecode determinism and bounded handling
of the named residuals. It must not read bytecode payloads, clean or alter the
residuals, edit implementation source, change the future runtime environment,
import/build/test/run anything, or open PAR-R1. Its maximum outcome is
`CACHE_STAGING_POLICY_REVIEW_PASS`.

The bounded review returned
`GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED / NO_GO_DIRECT_PAR_R1` and
formed these focused target objects:

1. `docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json`;
2. `docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md`;
3. `docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md`; and
4. `docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json`.

Exact target commit `56210f8f81557ed7a2521bf7f13c9f937396da29`
changes only those four paths plus `AGENTS.md` and `TASK.md`, preserves
implementation-manifest Git blob
`2aa64e50dad19626711e0dd90c038704ac73e328`, the exact 35 sources, and source-
tree SHA-256
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.
It passed three-track exact-commit independent review with no finding at LOW
or above. The durable verdict is
`docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md`.
The exact target reached `EXACT_TARGET_INDEPENDENT_REVIEW_PASS`. At formation
of the direct-child review record, the stage remained
`EXACT_TARGET_REVIEW_PASS_PENDING_LIVE_CLOSURE` until that record could be
committed/pushed and its one-shot review-head closure could succeed; only then
could it reach the conditional maximum `CACHE_STAGING_POLICY_REVIEW_PASS`.

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

Items 1--4 completed for exact target `56210f8`. At formation of the review
record, item 5 still required the direct-child review commit/push, live review-
head closure predicate, and mandatory Meeting Summary Handoff.

Cleanup/source/environment work and `A4-V2-PAR-R1` each remain separately
unauthorized after this documentation stage.

The CACHE-P review record was subsequently committed and pushed at
`249d5b8c1939acefbf12711790b3e791b019d560`; its live review-head closure and
Meeting Summary Handoff completed. The live closure is operational and non-
evidentiary.

The user has now explicitly authorized only `A4-V2-CACHE-I`. Its additive
receipt is
`docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md`. Before any
source edit, that authorization target must be committed, pushed, independently
reviewed, and closed under the frozen no-clone equality predicates. CACHE-I
then permits only the exact 37-file-source/38-executable-unit generic policy
implementation, ten frozen generic JSON objects, four rebinding documents,
AGENTS/TASK status, exact commits, static review, push, and Meeting Summary
Handoff. Its maximum outcome is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.

It permits no Python/import/syntax/build/test execution, clone, PREP token or
attempt, PAR-R1, SRUN, quarantine read or cleanup, data access, environment
mutation, or SAQ/CAQ change. PREP remains a separate future authorization.

## A4-V2-CACHE-I Deliverables

1. Add only `script/a4_v2_isolated_clone_prep.py` and
   `script/a4_v2_cache_policy_verifier.py`; modify only the four existing
   Python sources frozen by protocol section 5.1.
2. Rebind the canonical implementation manifest from 35 to exactly 37 file
   sources while preserving the canonical tree algorithm, 27 native/CMake
   sources, four non-allowed Python sources, and all scientific behavior.
3. Publish the ten closed generic schema/maximal/static/authority objects and
   update only the four frozen existing authority documents.
4. Bind one ASCII-only inline PREP bootstrap as the 38th executable unit and
   close every import/call/open/mutation path statically.
5. Publish a complete raw-byte parent-precedence partition proving frozen
   status/retry/PAR-report components and limiting every delta to the exact
   cache-governance allowlist.
6. Commit and push exact authorization and implementation target/review pairs,
   satisfy their separately registered no-clone probes, perform three-track
   independent static review with zero LOW+ findings, and complete Meeting
   Summary Handoff.

The implementation target/review does not authorize PREP or establish clone
readiness, parity, synthetic feasibility, an SAQ limitation, systems
performance, novelty, or a method contribution.

Exact authorization target
`4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d` is the direct child of the pushed
CACHE-P review head, changes exactly the authorization receipt plus
`AGENTS.md` and `TASK.md`, and preserves the manifest blob and complete
35-source tree. Three independent exact-target reviews found no LOW+ issue.
The durable review is
`docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md`.

The target reaches `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. Before source
changes, commit/push this direct-child review, satisfy its live review-head
closure, and perform the distinct implementation-parent admission probe whose
result must be frozen in the additive cache-authority manifest.

The direct-child authorization review is now committed and pushed at
`187e363ee08d1f63888137c21fd5a533555bb248`; its live closure and the distinct
implementation-parent admission predicate succeeded.  The implementation
worktree is sealed to the frozen 22-path delta, exactly 37 filesystem sources,
38 executable units, and canonical source-tree SHA-256
`9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2`.
At that point it remained WIP/nonevidence until the exact target was committed
and its direct-child independent review passed.

The user separately authorized `A4-V2-CACHE-I-SYNTAX` after the exact source
bytes were locked.  Compile-only Python 3.9 checks passed for the six
changed/new outer sources and the inline PREP bootstrap.  No code object was
executed and no module was imported.  This establishes syntax acceptance only
and does not authorize or evidence importability, build, fixture, RNG, PREP,
cache-verifier, PAR-R1, SRUN, data, quarantine, SAQ/CAQ behavior, correctness,
or scientific value.

The exact CACHE-I implementation target is now committed and pushed at
`c33a2bff7e0ec9c98596498fd43a7e629ccf47fe`, with direct parent
`187e363ee08d1f63888137c21fd5a533555bb248` and tree
`66eaf2f5df8792c3470b247e59857fc2e7a25461`.  The direct-child review in
`docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md`
found zero issues at LOW or above.  The registered target-head probe returned
the exact target from the remote branch; the memo separately discloses a
preceding sandbox DNS failure that returned no remote observation and is not
used as evidence.  The maximum result is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.  This result is static
artifact governance only, not PREP readiness, parity, feasibility, an SAQ
limitation, performance, novelty, or method evidence.  The three-path review
record was subsequently committed and pushed at
`5db302537793bc05f541aede119255213ea49e14`, tree
`f3c8e0ca52cb719018f5ad82952c06724ab9105a`.  CACHE-I is complete;
PREP, CACHE-BIND, PAR-R1, SRUN, data, quarantine, and SAQ/CAQ work remain
unauthorized.

On 2026-07-16 the user instructed exactly
`授权 PREP authorization/review`.  The instruction opens only the fixed
three-path PREP authorization target and its fixed direct-child three-path
independent review.  Exact target
`e7f940e924a338022bfe8fffcbb3496f12a5a75c` is committed and pushed with
direct parent `5db302537793bc05f541aede119255213ea49e14`, tree
`0386af8066a93d84ca772604990a08737a34aa33`, and exactly the registered
three-path delta.  The distinct PREP parent-admission probe and the target-head
closure each returned their exact remote OID with no sandbox preflight.

The sole independent review is
`docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md`.
It found zero issues at LOW or above and reached only
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.  Actual PREP remains
`NOT_AUTHORIZED`, and the future whole-stage ceiling remains only
`ISOLATED_CLONE_PREPARED_REVIEW_PASS`.

At that historical documentation checkpoint, the PREP authorization-review-
head probe had not run and was unspent.  The then-current contract would have
made that single future probe both live review closure and immediate PREP
execution-base admission.  The later host mismatch retired that path before
use: the old probe was never run and must never run or be reused.  The
three-path review record was committed and pushed at
`16a8201ac36e6c8c514848d55ad5ef607eb053b9`.  No clone, token, PREP
invocation, receipt, CACHE-BIND, PAR-R1, data, quarantine, or SAQ/CAQ action
followed.

Before the later authorized actual invocation, static prelaunch checking
found that a root-level RPM transaction had replaced the frozen
`python3-3.9.25-7.el9_8` leader with
`python3-3.9.25-7.el9_8.2`.  The regular file retained size 15,448 but its
SHA-256 became `c7b3d12b...f42b`, so invocation would write durable START and
then necessarily reject the leader.  PREP and the unique delayed probe were
therefore not run; no contract terminal status was created.

The user's 2026-07-16 instruction
`为当前 .el9_8.2 做一个 bounded host-identity rebind/erratum` opened only
`A4-V2-PREP-HOST-P`, a documentation-only additive protocol and contract,
exact-commit independent review, push, and Meeting Summary Handoff.  The
exact four-path target was committed and pushed at
`5a47fed05321af39a236d2dfb56d2c0f43708db3`; a fresh direct-child static
review then found no issue at LOW severity or above.  The completed authority
and review paths are:

1. `docs/saq_a4_v2_prep_host_identity_rebind_erratum_protocol_2026_07_16.md`;
2. `docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json`;
3. `docs/saq_a4_v2_prep_host_identity_rebind_erratum_independent_review_2026_07_16.md`.

The maximum result after exact review is
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`, not
`HOST_IDENTITY_REBOUND`.  Existing sources, manifests, schemas, witnesses,
runtime authorities, and historical protocols must remain unchanged in this
stage.  Python, PREP, the old or a new execution-base probe, clone/token,
build, PAR-R1, SRUN, data, quarantine, and SAQ/CAQ actions are forbidden.
The valid review used none of them.  Its memo explicitly excludes one earlier
procedurally invalid reviewer attempt, which supports no conclusion.

The old PREP review remains historical but stale for activation.  Its actual
invocation authority is unspent but nontransferable; its unique delayed probe
is unspent but superseded and may never run or be reused.  A future coherent
five-source/derived-authority rebind, fresh PREP authorization/review, new
explicit one-invocation grant, and newly registered immediate probe each
remain separately unauthorized.

The user's 2026-07-16 instruction `授权 A4-V2-PREP-HOST-I-AUTH` opened only
formation, commit, push, and exact-commit independent review of
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_2026_07_16.md`
plus focused `AGENTS.md`/`TASK.md` status.  Its exact parent is
`b89dabedd0273a330dded7f61551e6ad1ceac19c`; the exact three-path target was
committed and pushed at `212a67b887aa710fed35f66766982db683b3fa63`.
An ordinary sanitized target-head check returned exact remote equality and is
only a documentation-publication observation, not a PREP or implementation
probe.

A fresh independent exact-target review found zero LOW-or-higher findings and
is recorded in
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_independent_review_2026_07_16.md`.
Its maximum verdict is `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.
`A4-V2-PREP-HOST-I` remains `NOT_AUTHORIZED`: no five-source or seven-derived-
object rebind occurred, and the AUTH node ran no Python, DNF, syntax, build,
PREP, probe, clone/token, data, quarantine, or SAQ/CAQ work.  After Meeting
Summary Handoff, stop for a separate explicit HOST-I instruction.

The user next instructed exactly `授权 A4-V2-PREP-HOST-I`.  A complete
pre-edit static closure check found a BLOCKER in the publication-closed AUTH:
it simultaneously required preservation of seven cache-authority protocol
components, addition of an eighth HOST-P contract, and no verifier source
semantic delta beyond seven leader-digest substitutions.  The committed cache
verifier enforces exact equality to the old seven key/path pairs, so the
required authority would be rejected.  Adding the eighth verifier key/path
also adds one path and one existing-loop identity read/hash, contradicting the
old no-path/resource/evidence-change clause.  Work stopped before any HOST-I
target, implementation edit, WIP evidence, Python, probe, PREP, build, data,
quarantine, or SAQ/CAQ action.

On 2026-07-16 the user instructed exactly
`授权 A4-V2-PREP-HOST-I-ERRATUM`.  This authorizes only a four-path additive
documentation target, its three-path direct-child independent review, push,
and Meeting Summary Handoff.  The governing objects are:

1. `docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_protocol_2026_07_16.md`;
2. `docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_contract_2026_07_16.json`; and
3. after the target commit, the registered independent review memo.

The erratum freezes the only extra future source loci as one new member of
`PROTOCOL_COMPONENT_KEYS` and the matching exact HOST-P-contract mapping in
`PROTOCOL_COMPONENT_PATHS`.  The resulting eighth entry receives exactly one
additional invocation of the existing identity-check loop, including its
unchanged fallback/mismatch/ledger semantics.  It also changes the future
HOST-I parent rule to the publication-closed erratum review head.  The future
fourteen-path target and three-path review remain otherwise unchanged.  The
conditional ceiling is
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`; it is not
`HOST_IDENTITY_REBOUND` or PREP readiness.  A fresh explicit HOST-I
authorization remains required after review and handoff.

The same static audit found a separate excluded downstream limitation: after
the five-source rebind, the cache verifier would compare the new current
source blobs with old CACHE-I/PREP history commits and report
`SOURCE_HISTORY_MISMATCH`.  This does not block source-only HOST-I or PREP,
which does not run that verifier, but it forbids any cache-verifier/PAR-
readiness claim.  Repair is outside this erratum and requires separate
protocol and source authorization.

Exact four-path erratum target
`6fe8544ae677fa8aaf7bba1306ae9aa8d4599f20`, tree
`51f9abc20ac6e7afcb0c584ce6bd4cfc79e3b5f9`, is committed and pushed as the
direct child of `71e6bec01dbabaf29333ac75dcd9ef7a238a079d`.  Three fresh
independent exact-target tracks found zero LOW-or-higher issues; the durable
review is
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md`.
The exact review reaches only
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS` once its registered three-path
direct-child record is committed and pushed.  A successful push established
remote acceptance of the target.  One optional SSH `ls-remote` failed locally
before remote observation, was not retried, and is excluded.  Review
publication and Meeting Summary Handoff must complete before the stage stops
for fresh HOST-I authorization.

The completed erratum stage permitted only additive authority documents,
static review, focused commits, push, and Meeting Summary Handoff. It permitted
no implementation edit, build, Python import, syntax/test command, RNG,
synthetic run, generated scientific artifact, data read, or SAQ modification.
Untracked implementation WIP remains nonevidence.

The user has now explicitly authorized `A4-V2-PREP-HOST-I source-static
target + direct-child review`.  The exact target is the direct child of
publication-closed erratum review head
`9fa9528f4181d51fe6e060c1de14ea568eb31c4a` and changes all and only the
frozen fourteen mode-`100644` paths.  It replaces the old CPython leader
digest at exactly seven active loci across the five registered sources and
adds only the erratum-frozen 197-byte eighth-component key/path admission in
the cache verifier.  The active closure remains 37 filesystem sources and 38
executable units; historical CACHE-I-SYNTAX identities remain bound to the
old bytes, and `build_status` remains `NOT_AUTHORIZED_NOT_RUN`.

Before direct-child review, the maximum target status is
`HOST_I_SOURCE_STATIC_TARGET_FORMED_REVIEW_PENDING`, not an independently
established host rebind.  The direct-child review may change exactly
`AGENTS.md`, `TASK.md`, and
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md`.
It must find zero LOW-or-higher issues before the bounded registered-object
`HOST_IDENTITY_REBOUND` claim is allowed.  The known downstream
`SOURCE_HISTORY_MISMATCH` remains unresolved and forbids cache-verifier/PAR
readiness; it does not block source-static review or PREP itself.  No Python,
syntax/import, compiler/build/test, verifier, PREP, clone, data, quarantine,
or SAQ/CAQ operation is authorized.  Commit, push, independent review, and
Meeting Summary Handoff are the complete current sequence; later PREP
authorization remains separate.

The exact source-static target was subsequently committed and pushed at
`46025854ce1657e09fa64ac9277e53a87c8e15b2`, tree
`c5080470082912475bc7df11accbfc214de1ebe6`, with direct parent
`9fa9528f4181d51fe6e060c1de14ea568eb31c4a`.  Its sole independent static
review returned FAIL with one HIGH finding: the implementation binding and
source-provenance crosswalk cite the 11,426-byte source-authority-erratum
review as
`c670d368647fbd13bfe4133241e2c37e29101e91538687a64349a606bd059f2a`,
whereas the immutable committed bytes are
`c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331`.
The terminal target-review status is
`SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH` and
`HOST_IDENTITY_REBOUND` is `NOT_ESTABLISHED`.

The registered three-path review projection permits only this status update
and its negative review memo; it cannot repair the two target documents or
their dependent manifest identities.  No correction, PREP, cache-verifier,
PAR, performance, or scientific claim is authorized or established.

On 2026-07-17 the user instructed exactly
`授权 A4-V2-PREP-HOST-I-R1-P correction-only repair protocol + direct-child review`.
This authorizes only a four-path protocol target, its exact three-path
direct-child independent review, commit/push, and mandatory Meeting Summary
Handoff.  The governing protocol and contract are:

1. `docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_2026_07_17.md`;
2. `docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_contract_2026_07_17.json`.

The protocol freezes a possible later five-path correction-only target.  It
would replace the false review digest exactly once in the binding and once in
the crosswalk, then update only their two whole-file SHA-256 fields in the
implementation manifest.  R1-P does not perform that repair and grants no
source, Python, build, PREP, cache-verifier, PAR, data, quarantine, or SAQ/CAQ
authority.  A separate future instruction naming
`A4-V2-PREP-HOST-I-R1` remains mandatory.  The current protocol target status
was `PROTOCOL_TARGET_FORMED_REVIEW_PENDING`.

Exact target `ddfef99104eec67e9f5d6236e12ec9805f560a86`, tree
`134aa95ee85259553d55275713e8af0c513f0900`, was committed and pushed as the
direct child of `e8e9c799fae39284688ff87d5c138be9ade80e51`.  Its sole
independent Git/hash/text review found zero LOW-or-higher findings.  The
durable review is
`docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_independent_review_2026_07_17.md`;
its protocol-only verdict is
`HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS`, conditional on the
exact three-path review record being committed and pushed.  It does not
authorize or form the five-path R1 repair.

The user's 2026-07-17 instruction `授权 A4-V2-PREP-HOST-I-R1` now authorizes
only that exact correction-only target and its direct-child review.  The
target is the direct child of clean, pushed protocol-review head
`b1a7429cda3e4817d7df494f304bbce24bec2b92` and changes exactly five
mode-`100644` paths: `AGENTS.md`, `TASK.md`, the implementation binding, the
implementation manifest, and the source-provenance crosswalk.  The two prose
objects each receive exactly one false-to-true immutable-review SHA-256
replacement; the manifest receives only their two dependent corrected
SHA-256 scalars.  All replacements are equal length, every filesystem source
and other authority object remains byte-identical, and the identity cascade
terminates at the manifest.

Before exact direct-child review, the target status is
`HOST_I_R1_CORRECTION_ONLY_REPAIR_TARGET_FORMED_REVIEW_PENDING`.  Nothing was
imported, compiled, built, tested, or executed.  R1 permits no Python, PREP,
cache-verifier, PAR, data, quarantine, or SAQ/CAQ action.  The separately
known `SOURCE_HISTORY_MISMATCH` remains unresolved and continues to forbid
cache-verifier/PAR-readiness claims.

Exact correction-only target
`e17f8870e090be693adcd3bce4b8aea07432f064`, tree
`533c27fbc3b9545829153d6ec5c95e81a7fe832a`, was committed and pushed as the
direct child of `b1a7429cda3e4817d7df494f304bbce24bec2b92`.  Its sole
independent static review found zero LOW-or-higher findings.  The durable
review is
`docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_independent_review_2026_07_17.md`.
Its exact outcome is `HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS`,
conditional on the exact three-path review record being committed and pushed,
and its bounded host result is
`HOST_IDENTITY_REBOUND = ESTABLISHED_FOR_REGISTERED_13_OBJECT_BUNDLE_ONLY`.
This is not whole-host identity, PREP/cache/PAR readiness, execution evidence,
performance evidence, or a scientific result.  `SOURCE_HISTORY_MISMATCH`
remains unresolved and all downstream stages remain separately unauthorized.

On 2026-07-17 the user instructed exactly
`授权 bounded SOURCE_HISTORY_MISMATCH correction protocol + direct-child review`.
This authorizes only `A4-V2-SOURCE-HISTORY-P`: a four-path documentation
target, its exact three-path direct-child review, focused commit/push, and
mandatory Meeting Summary Handoff.  The governing objects are:

1. `docs/saq_a4_v2_source_history_epoch_correction_protocol_2026_07_17.md`;
2. `docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json`;
3. after the target commit, the registered protocol-review memo.

The frozen correction model assigns each registered history role exactly one
source epoch.  The four immutable CACHE-I and original PREP-authorization
roles use the exact five pre-host-rebind Git-blob overrides; six future PREP-
receipt, CACHE-BIND, and PAR roles use only the active 37-source authority.
An old-or-new disjunction, observed-byte inference, ancestry/date/branch/host
selection, warning downgrade, or history rewrite is forbidden.

The protocol does not edit source.  A later source-static target would require
a separate explicit `A4-V2-SOURCE-HISTORY-I` instruction and could change only
the cache-policy verifier, seven derived authority/document objects, and root
status: exactly ten paths.  It must bind the committed contract as the sole
ninth cache-authority protocol component.  The present target's maximum status
before review is `PROTOCOL_TARGET_FORMED_REVIEW_PENDING`; even a protocol PASS
does not establish cache-verifier/PAR readiness, PREP, execution, performance,
or scientific evidence.

No Python, syntax/import, compiler/build/test, cache verifier, PREP, probe,
clone, CACHE-BIND, PAR, data, quarantine, or SAQ/CAQ action is authorized.
The stage stops after its direct-child review, push, Meeting Summary Handoff,
and user checkpoint.

Exact protocol target `dcaed57aaae6fe0f120377281921b6ea5336eb7f`, tree
`d0069768c8848327f04a23b444fae0b635eb2d78`, was committed and pushed as the
direct child of `e10bde78eff21802301549e4c796cc3f49c9d32b`.  Its sole
independent static review found zero LOW-or-higher findings.  The durable
review is
`docs/saq_a4_v2_source_history_epoch_correction_protocol_independent_review_2026_07_17.md`.
Its exact conditional protocol-only outcome is
`SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS`, once the exact
three-path review record is committed and pushed.  This does not authorize or
establish the future source correction, derived-authority edits, PREP,
cache-verifier/PAR readiness, execution, performance, or scientific evidence.
`A4-V2-SOURCE-HISTORY-I` remains separately unauthorized.

The user subsequently authorized `A4-V2-SOURCE-HISTORY-I`.  Before a target,
static closure inspection proved the frozen ten-path projection impossible:
the internal role-to-epoch correction does not change the generic runtime
schema or its already maximal witness, but the protocol required both files to
change while forbidding any new output or ledger shape.  The provisional
verifier edit was completely reverted.  No immutable target, review,
execution, or evidence resulted.

On 2026-07-18 the user authorized exactly
`A4-V2-SOURCE-HISTORY-I-R1-P correction-only path-closure erratum + direct-child review`.
This stage permits only a four-path additive erratum target, its exact
three-path direct-child review, focused commit/push, and Meeting Summary
Handoff.  Its protocol and contract are:

1. `docs/saq_a4_v2_source_history_i_r1_path_closure_erratum_protocol_2026_07_18.md`;
2. `docs/saq_a4_v2_source_history_i_r1_path_closure_erratum_contract_2026_07_18.json`.

The erratum changes only the future path closure from ten paths/seven changed
derived objects to eight paths/five changed derived objects.  Runtime schema
and maximal witness blobs remain exact.  The original epoch model, five
overrides, sole ninth component, line limits, runtime behavior, overhead, and
future review projection remain authoritative; the erratum is not a tenth
component.  Before review the maximum status is
`PATH_CLOSURE_ERRATUM_TARGET_FORMED_REVIEW_PENDING`.  It permits no source or
derived-authority edit and no execution.  Future implementation remains
separately unauthorized as `A4-V2-SOURCE-HISTORY-I-R1`.

Exact erratum target `150e5b38aa5b3e30dafe4e15632db5fb5add4a68`, tree
`29fa489d25a348997bb1eadeb5208dabd1717e0d`, was committed and pushed as the
direct child of `e98a3e401639cae4f11ea97d21883120e9b797fb`.  Its sole
independent static review found zero LOW-or-higher findings.  The durable
review is
`docs/saq_a4_v2_source_history_i_r1_path_closure_erratum_independent_review_2026_07_18.md`.
Its exact conditional documentation-only result is
`SOURCE_HISTORY_I_R1_PATH_CLOSURE_ERRATUM_REVIEW_PASS`, once the exact
three-path review is committed and pushed.  This establishes only the
corrected future eight-path/five-derived-object projection.  It does not
authorize source or derived-authority edits, execution, PREP/cache/PAR
readiness, performance, or scientific evidence.  The future implementation
still requires explicit `A4-V2-SOURCE-HISTORY-I-R1` authority.

The user has now explicitly authorized `A4-V2-SOURCE-HISTORY-I-R1`.  The
current source-static target is the direct child of clean, pushed path-closure
erratum-review head `774949179582c8a9acbf79d5bc1f2d9fc851957a` and changes
exactly the eight mode-`100644` paths frozen by R1-P: root status, one cache
verifier source, static closure, cache authority, implementation binding,
implementation manifest, and source-provenance crosswalk.  Runtime schema and
maximal witness remain exact and unchanged.

The one source edit contains the exact five legacy Git-blob overrides,
preassigns four legacy and six active history roles before observation,
selects only that role's expected map in the existing history loop, and adds
the original source-history contract as the sole ninth component.  It adds no
status, parser, Git observation, output, retry, cap, timer, or ledger field.
The verifier delta is 38 net lines; no second source is changed.

Before direct-child review, the maximum status is
`SOURCE_HISTORY_EPOCH_CORRECTION_R1_TARGET_FORMED_REVIEW_PENDING`.  The review
must change only `AGENTS.md`, `TASK.md`, and the registered source-history
implementation review memo and must find zero LOW-or-higher issues before the
maximum static-only result
`SOURCE_HISTORY_EPOCH_CORRECTION_SOURCE_STATIC_REVIEW_PASS` is allowed.

No Python, syntax/import, compiler/build/test, cache-verifier execution, PREP,
probe, clone, CACHE-BIND, PAR, data, quarantine, environment, or SAQ/CAQ
action is authorized.  No readiness, performance, or scientific evidence is
formed.  After exact target commit/push, direct-child review, and Meeting
Summary Handoff, stop for a user checkpoint.

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
or cleaned. The CACHE-P review/push/closure/handoff sequence is complete.
CACHE-I is now authorized only for its generic source/schema/static-review
sequence. There is no quarantine access, cleanup, clone, PREP, PAR-R1, SRUN,
data, or SAQ authority; never infer one from the historical source review,
failed invocation, repaired source, policy protocol, or static source
authorization.

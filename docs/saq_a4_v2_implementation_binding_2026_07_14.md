# A4 V2 Source-Implementation Binding

Date frozen: 2026-07-14

Stage: `A4-V2-I`

Status: **SOURCE_BINDING_FROZEN_NO_EXECUTION_AUTHORITY**

Parent protocol commit:
`f86a51d6923409d735dda0ee40f88fd2e0ad2e43`

## 1. Purpose and authority

This note freezes choices that the reviewed preregistration deliberately left
to `A4-V2-I`: source closure, process boundaries, native interchange,
identity preimages, counter ownership, and producer--verifier separation. It
does not alter the scientific shape, cost FOM, thresholds, schema, status
precedence, or authorization sequence.

The parent preregistration, machine-readable contract, and artifact schema
remain byte-for-byte unchanged.  Post-erratum source has one composite
protocol authority, bound by
`docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json`; the parent
preregistration is separately retained as provenance. This note authorizes no build, import,
parity command, RNG, synthetic event, artifact generation, data access, or SAQ
change.

## 2. Historical-source rule

`saq-arbitrary-cardinality-analysis@f1b464b` is a read-only semantic oracle.
The V2 tree may not include, link, import, execute, symlink to, or read source
at runtime from that branch or worktree. The old monolithic runner and its
259-shard state machine, output writers, finalizer, generated artifacts, and
tests are not migrated.

The producer scientific kernels deliberately implement the same registered
mathematics and native-child behavior. Their implementation review records a
function-level provenance crosswalk to the historical Git blobs. Similarity
is expected and is not a novelty claim; self-contained V2 source and the new
phase/evidence boundary are the only implementation delta.

## 3. Source and process closure

The reviewed implementation manifest must enumerate every source file under:

```text
research/a4_v2/
research/a4_v2_verifier/
script/run_arbitrary_cardinality_a4_v2.py
script/a4_v2_runner.py
script/a4_v2_producer.py
script/a4_v2_producer_wire.py
script/a4_v2_evidence.py
script/a4_v2_parity.py
script/a4_v2_verifier.py
script/a4_v2_archive.py
```

The exact final file list is frozen in the committed implementation manifest,
not inferred with a filesystem glob. Both native CMake projects are standalone
and link no SAQ target. They list translation units explicitly.

That manifest uses `protocol_identity` only for the composite authority
manifest and separately carries `parent_preregistration_identity`,
`contract_identity`, `artifact_schema_identity`,
`authorization_identity`, `implementation_binding_identity`, and
`source_provenance_identity`.  Its PAR contract freezes the external review
memo path and the later execution-authority binding path stated in Section
8.1; it never places either object inside the immutable PAR tree.

For the additive `A4-V2-I-R1` correction, `authorization_identity` names
`docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md`.
That receipt inherits and narrows the original implementation authority; it
does not rewrite the parent protocol, add a manifest field, or authorize an
execution event.

The producer and verifier are separate process families, build targets,
source directories, Python modules, wire parsers, and record encoders. The
verifier may share only the three normative documents, frozen input bytes,
operating-system interfaces, standard libraries, and pinned external GMP,
MPFR, OpenSSL, and JSON-schema semantics. It may not include, link, or import
the producer's solver, allocation or tie logic, rational conversion, block
trainer, packer, parser, canonical logical-record encoder, or self-replay.

Static review must check both the CMake source closures and Python import
closures. A common implementation helper crossing that boundary is an
`IMPLEMENTATION_INVALID` defect, not an optimization opportunity.

## 4. Frozen entry points and native surfaces

The outer entry point is exactly:

```text
script/run_arbitrary_cardinality_a4_v2.py
```

Its first A4 executable action obtains integer SELF+CHILDREN user/system
`getrusage` snapshots and `monotonic_ns`, before argument parsing, scientific
imports, filesystem or Git checks, environment validation, fixture
construction, or NumPy import. Before the snapshots the entry file may load
only the minimal standard-library machinery needed to issue those integer
clock calls; it may perform no other gate work. The four underlying timeval
components are summed with integer arithmetic into
`start_family_cpu_microseconds`; `monotonic_ns` supplies
`start_monotonic_wall_nanoseconds`. It imports the runner only after those
snapshots and passes these two integers as immutable arguments. It accepts
only a stage-selected command and artifact root; there is no seed,
shape, dimension, rate, group, cardinality, restart, iteration, thread, cap,
threshold, machine, or exclusion override.

The producer native executable basename is `a4_v2_native`. It retains these
surfaces so a later `A4-V2-PAR` can run the frozen predecessor fixture
inventory:

```text
manifest
native-smoke OUT
par-scalar INPUT OUT
par-block INPUT OUT
scalar-suite INPUT OUT
block-suite INPUT OUT
representation-suite
allocation-suite INPUT OUT
allocation-item INPUT OUT
encoding-suite INPUT OUT
```

The independent verifier native target is built in its own directory and is
also installed with basename `a4_v2_native`, so every capable invocation
exposes a basename in the frozen process-conflict marker set. Its full path,
binary identity, argv, and disjoint source closure distinguish it from the
producer. Its exact surfaces are:

```text
manifest
par-scalar INPUT OUT
par-block INPUT OUT
par-representation OUT
verify-canonical-request
```

The independent `par-scalar` path exhaustively enumerates all contiguous
partitions in the bounded PAR domain; it does not call the verifier's
full-shape divide-and-conquer solver. Before independent block training,
the 64 production `par-block` cases independently rebuild the two scalar
curves and product allocation from the raw binary32 rows with a bounded
`O(KH^2)` exact DP and direct binary64 rounding, then reject supplied axis
bits that differ.  Five helper-level cases precede those 64 cases and test,
one semantic each, lower-codeword assignment, lower-vector farthest fill,
empty-center binary64 retention, Cartesian-before-fill order, and the
best-of-eight tie.  Their deliberately underfilled axes are fixed helper
inputs and are not admitted as production exact-axis evidence. The full
replay command uses its own full-shape optimized exact implementation.

No command batches scientific units or retains a child across unit boundaries.
Every child is waited and reaped before the supervisor captures the unit
receipt or applies a cap.

## 5. Native child granularity

One full producer attempt has exactly this scientific child inventory:

```text
128 scalar children
    one coordinate, all requested K=1..256 per child

256 product-allocation children
    for each B4/B8 group, dyadic and arbitrary are separate children

2 global-allocation children
    one for B4 and one for B8

128 block children
    one B4/B8 group per child, all eight starts and winner inside it

8 encoding children
    one B4/B8 arm per child, all 8192 rows, pack and round-trip
```

The two product children are jointly one registered allocation unit. A block
child is one complete eight-start unit. An encoding child is one complete
arm unit. No child may be combined with another coordinate, group, arm, or
rate to reduce launch, interchange, wait, parse, or materialization work.

A block whose recorded controls are invalid is not a completed unit. The
producer first deletes and byte-ledger-charges that unit's input and output,
then asks the supervisor to checkpoint the prior complete prefix without
incrementing its unit index. All failed-tail CPU, wall, RSS, and cleanup stay
in the terminal C receipt; `CONTROL_INVALID` is additionally derived from that
receipt even when every control in the retained prefix is true.

Every other candidate unit is also tentative until its post-child cumulative
operational sample passes. Only then may the supervisor advance both its
retained `ProducerState` and receipt completed-unit index. An operational
crossing at that boundary keeps both objects at the prior complete prefix;
the candidate's already charged CPU, wall, RSS, child work, and cleanup remain
in the terminal receipt but its scientific record is not emitted.

The setup and whole-directory bundle-publication units are supervisor units.
Only U395 publishes `bundle/`; individual bundle files are not independently
published scientific prefixes.

Bundle bytes and their global ceiling are validated and reserved before the
no-replace directory rename. One SIGINT guard covers reservation, staging
fsync, no-replace rename, the local visibility flag and irreversible marker,
parent-directory fsync, and the already-validated ledger commit. Any
transaction error is captured into the C terminal guard before reservation
cancellation or descriptor cleanup. The C terminal closure also probes
`bundle/` independently with no-follow semantics. Any
visible entry before an admitted U395 forces
`ARTIFACT_INVALID/ATOMICALLY_PUBLISHED` and fail-stop; marker/path
disagreement is likewise artifact-invalid. If any failure occurs after the
target becomes physically visible but before U395 is admitted, the
terminal C receipt uses `ARTIFACT_INVALID` and
`staging_disposition=ATOMICALLY_PUBLISHED`, the retained scientific prefix
remains U394, and the supervisor exits without E, V, archive, retry, or any
attempt to reinterpret or delete the visible target.

Before the rename, `bundle.staging/` is an unpublished sibling of the attempt
staging directory, not one of its children. Every successful or failed
attempt therefore closes both namespaces explicitly: if that sibling still
exists as a real directory, the supervisor first charges its complete tree as
deleted partial bytes and then removes it. It never applies that cleanup to
the no-longer-staging `bundle/` target after a successful rename.
Target probing and the two staging cleanups are a one-shot terminal action.
If later receipt construction must re-enter the terminal finalizer, it reuses
the sticky disposition and cleanup-validity result; it does not rescan or
redelete either namespace.

An inventory error while closing either C staging namespace is not rescued by
physical deletion. If a special node prevents complete no-follow regular-file
accounting, the owned tree may be safely removed, but cleanup accounting is
marked incomplete and the run fail-stops before E. This prevents uncounted
regular siblings, peak-live bytes, or a hidden 16 GiB temporary-byte crossing
from entering a downstream artifact.

Resource-cap observations made at a terminal C boundary, after failed-tail
cleanup and receipt work have been charged, are sticky. The frozen receipt has
only one `exit_reason`, however, and therefore cannot independently encode a
nonnumeric Resource observation hidden by a simultaneous higher-precedence
`ARTIFACT_INVALID`, `IMPLEMENTATION_INVALID`, or `CONTROL_INVALID`. Such a
compound C failure is fail-stop before E, V, archive, or F; it is never passed
downstream as a boolean that archive cannot reconstruct. This conservative
fail-stop also applies when the Resource fact is numerically derivable: the
implementation does not split compound C failures into two runtime policies.
When Resource is the winning receipt reason, the existing downstream
reconciliation remains valid. The final decision adds the independently
reconciled archive-phase CPU, wall, RSS, and byte ceilings without inventing
an unregistered receipt side channel.

Concretely, the supervisor appends exactly one terminal C receipt and keeps
SIGINT blocked. A first fresh process-family observation seals failed-tail
cleanup (and, on a terminal attempt, descriptor 197 closure) into that
receipt. The supervisor then performs the exact-visible-U395,
downstream-admission, U000, and compound-failure checks. The final root-commit
operation takes a preliminary cap-classification snapshot, performs the
proposed final invariant checks, then takes the contiguous commit snapshot
that extends the receipt. Only the first tail snapshot and final commit
snapshot advance the receipt boundary; the preliminary snapshot neither
appends nor charges an interval. A cap that first crosses at the commit
snapshot is monotone and is classified once before handoff. The incremental
CPU is attributed once to the current C owner and `last_cpu` advances to the
final root boundary, so a retry or E starts after—not before—that work. A
retry is permitted only when the first sealed result still says exact
`EXTERNAL_INTERRUPTION/DISCARDED` with no Resource fact. This makes the
producer-attempt cap independently recomputable without charging C root
closure work again downstream.

The terminal guard retains the frozen unblocked CPython entry mask, and a
failed bundle guard transfers that original mask rather than nesting a second
blocked mask. Retry release rejects any still-active bundle guard or saved
mask that already contains SIGINT, then verifies the unblocked/default
CPython contract inside attempt 1's owning handler. Final C completion does
not create an unowned restore window: it transfers the still-blocked guard
and original unblocked mask directly to E. E's first fork consumes pending
SIGINT, gives its child the original unblocked mask, and owns the parent's
restore/recovery edge. A handoff owner is installed before root-to-E argument
preparation and remains active through all fallible E pre-fork setup. Any
pre-fork exception explicitly restores the original mask, or fail-stops with
the handoff owner still active and SIGINT still blocked if restoration itself
fails. After a successful fork the already-defined parent recovery path takes
ownership without an intervening fallible setup step. Thus neither a retry
transition nor a transaction cleanup error can silently carry blocked SIGINT
semantics into E or V.

A physically visible bundle is admissible downstream only when that unique
terminal receipt is exactly
`C_bundle_io/U395/PHASE_COMPLETE/ATOMICALLY_PUBLISHED`. Any other reason,
phase, unit, or disposition paired with a visible bundle is artifact-invalid
and fail-stop. The independently recorded primary-cap operand may still make
the final decision a cost no-go after a normal U395 `PHASE_COMPLETE`; it does
not rewrite that successful publication receipt.

Each capable producer-native launch uses the same parent-before-launch SIGINT
guard. The exec child installs `SIG_DFL` and unblocks SIGINT; the parent first
observes terminal state with `waitid(...,WNOWAIT)`, then blocks and performs the
unique `wait4`. On a failed native unit that mask remains owned through
nofollow output/stderr admission, staging cleanup, the C terminal sample, and
receipt append. A positive native exit is implementation-invalid even when a
lower-precedence Resource or stream failure is simultaneous. Resource remains
sticky independently, and a raw native signal is retryable only after both C
staging namespaces are proven physically absent and the receipt says
`DISCARDED`.

Meter samples commit attribution and `last_cpu` together under a deferred
SIGINT mask. Phase switches commit the closing receipt, boundary, new phase
start fields, byte-ledger phase, and owner as one transition. Unit admission
likewise advances the receipt index, retained `ProducerState`, and terminal
stop flags together; a pre-commit signal keeps the prior prefix, while a
commit/restore-edge signal retains the fully committed new prefix and records
Resource. Temporary-byte admission commits live ownership, created bytes,
peak-live bytes, and its ceiling check under the same rule. These guards are
measurement integrity, not additional scientific work.

The frozen C receipt vocabulary has no Evidence terminal reason. Producer
native launch, diagnostic, temporary-file, or cleanup transport failures that
would otherwise be evidence-incomplete are implementation-invalid at C,
before any producer evidence exists. The only registered failure statuses
admitted in C are `ARTIFACT_INVALID`, `IMPLEMENTATION_INVALID`,
`CONTROL_INVALID`, and `RESOURCE_INCOMPLETE_NO_DECISION`; every other
registered but out-of-phase status is implementation-invalid. Artifact and
Resource retain their higher/lower precedence as registered; archive therefore
never has to reinterpret an out-of-vocabulary C status.

## 6. Frozen interchange and counters

Native interchange is versioned binary input plus TSV-equivalent or binary
output. It is required work in `C_core`, including temporary bytes, child
launch/wait, parsing, and construction of compact in-memory records. A future
PAR review binds exact magic strings, byte layouts, end markers, and parser
strictness before any synthetic authorization.

The parity-compatible surfaces preserve the predecessor meanings:

```text
scalar      A4SCL001 -> A4S_SCALAR_RESULT_V1
block       A4BLK001 -> A4S_BLOCK_RESULT_V1
allocation  A4ALC001 -> canonical JSON
alloc item  A4ALI001/A4AIEND1 -> A4ALO001/A4AOEND1
encoding    A4ENC002/A4EIEND2 -> A4EOUT02/A4EOEND2
```

These identifiers describe the frozen semantic wire and do not authorize
reading historical files. V2-only compact trace additions are versioned
separately and must preserve every old decision.

Per-K scalar comparison and tie counts belong to the effective DP layer;
`K=1` and copied `K>H` records report zero layer work. Product
`enumerated_candidate_count` is the frozen optimized frontier count:

```text
arbitrary B4/B8: 16 / 256
dyadic    B4/B8:  5 /   9
```

It is not the number of all feasible ordered tuples. The global counter is
the number of exact `(prior state, selected width)` transitions evaluated.
Block distance, assignment-tie, farthest-tie, packing, unpacking, and
round-trip counters are monotone integer work counters and never affect a
decision.

## 7. Trace ownership and E_emit boundary

Before `C_core` closes, producer memory already contains every scientific
record required by the frozen evidence schema, including:

- all exact partitions, exact means, direct binary32/binary64 bits, and work
  counters;
- both product allocations and both global allocations;
- all block initial states, prefill states, every accepted-step before/after
  assignment preimage, centers, final assignments, controls, and winner;
- every selected model, label, address, packed payload, and round-trip result;
  and
- every byte/work counter used by the bundle and evidence records.

Step assignments are retained as compact unsigned little-endian 16-bit arrays
during `C_core`; they are not regenerated in `E_emit`. Producer record storage
becomes immutable before `C_bundle_io` begins and remains live through
`E_emit`. No unregistered detail checkpoint may substitute for this in-memory
boundary.

`C_bundle_io` only canonicalizes, writes, validates, hashes, flushes, closes,
and atomically publishes the four registered bundle children from those
records. `E_emit` only encodes and hashes the same already-computed records.
It may not optimize, backtrack, derive a mean, round a value, choose a model,
assign a label, regenerate a payload, or replay a block step.

## 8. Identity bindings

All canonical identity preimages omit a terminal LF unless the protocol says
they cover exact file bytes.

```text
verifier_summary.producer_identity
    SHA-256 of exact evidence/producer_manifest.json file bytes

verifier_summary.input_identity
    producer_manifest.input_identity.input_identity_sha256

producer_manifest.protocol_identity
    document identity of the composite protocol-authority manifest

archive_body.protocol_identity and decision.protocol_identity
    SHA-256 of exact composite protocol-authority-manifest bytes
```

The implementation/source manifest's `parent_preregistration_identity`
separately binds the original preregistration Markdown and its
`source_provenance_identity` binds this I-stage crosswalk.  Its
`protocol_identity` is never overloaded with the parent identity.  The
producer manifest's `schema_identity` binds the artifact schema. The
machine-readable contract, implementation authorization, implementation
binding, source-provenance crosswalk, and reviewed build/source manifest are
bound by their exact paths and hashes in the clean reviewed source commit and
its source manifest; they are not artifact-root files and therefore are not inserted into
`archive_body.pretrailer_files`. Thus no schema field is overloaded and the
artifact-root inventory in Section 9 remains exact.

`source_tree_sha256` covers the canonical array of
`{path,sha256,size_bytes}` for every reviewed implementation source, ordered by
ascending UTF-8 path bytes. Paths are repository-relative POSIX paths and may
not be absolute or contain empty, dot, or dot-dot components.

`logical_run_id` is SHA-256 of the canonical object containing protocol
version, clean execution commit, exact outer argv array, prelaunch UTC string,
preflight PID, preflight start-time clock ticks, and normalized output root.
It contains no RNG. A permitted restart retains this exact id.

The exact logical-run preimage and the environment object whose canonical
body yields `environment_sha256` must be persisted before their receipt hashes
are admitted.  PAR persists both in its build manifest.  SRUN persists the
environment object in `producer_manifest.json`; its logical preimage is
reconstructible without hidden state from that manifest's command, source,
prelaunch and protocol fields.  Admission recomputes these hashes rather than
accepting opaque receipt strings.

The prior `B_build` and `P_parity` receipts are sealed inputs from the later
separately authorized PAR stage. They retain their PAR logical-run id and are
not represented as children of the SRUN supervisor. The SRUN supervisor owns
one different logical-run id for C/E/V/archive phases. Resource-ledger ordering
is still phase order then attempt id; logical-run ids need not be equal across
the sealed PAR and SRUN receipt classes.

For each process-family receipt, `binary_sha256` identifies the family
leader's executable bytes and `argv_sha256` hashes its complete canonical argv
array. Producer/verifier native-child identities and argv are additionally
bound by the reviewed build manifest and phase-specific child inventory. A
single summary hash is never presented as the identity of multiple unlisted
executables.

The CPython leader identity is acquired from a bounded full read of a stable
descriptor opened on literal `/proc/self/exe`.  The intentionally followed,
normalized absolute `sys.executable` pathname must open as the same nonempty
regular inode before the read and must reopen with the same device, inode,
mode, size, modification time, and change time after it.  The running-image
descriptor must retain those same fields across an EOF-checked read capped at
one GiB.  Its SHA-256 and size are cached once per process and supply every
CPython leader/admission/receipt identity in that process.  This dedicated
rule does not alter the no-follow readers for documents, artifacts, trees, or
native binaries.  The independent verifier implements the same contract with
its own positional-read code rather than importing the conductor or runner
helper.

UTC strings use RFC 3339 UTC with six fractional decimal digits and terminal
`Z`. Linux `ru_maxrss` is multiplied by 1,024 exactly to obtain bytes.

### 8.1 Finite PAR authority closure

`B_build` and `P_parity` each permit one retry only after an external signal.
Their only successful receipt orders are `B0,P0`, `B0,B1,P0`, `B0,P0,P1`,
and `B0,B1,P0,P1`.  Completed B/P attempts use
`staging_disposition=NONE`; interrupted attempts use `DISCARDED` and the exact
`EXTERNAL_SIGNAL_n` reason.  The successful B terminal boundary is the exact
P start boundary.

Each B/P attempt runs its registered substantive work in a fresh forked phase
worker while the same lightweight supervisor remains the receipt leader and
eventual PAR publisher. Immediately before that worker is forked, the
supervisor freezes its cumulative SELF `ru_maxrss` as `H`. Every subprocess
inside the worker is reaped with `wait4`, and the parent ultimately reaps the
worker; `W` is the maximum current-attempt worker/direct-child `wait4` peak,
never cumulative `RUSAGE_CHILDREN.ru_maxrss`. The attempt is admissible only
if its registered workload naturally produces `W >= H`. There is no padding
allocation, tuning value, retry rescue, or synthetic memory guard. Failure of
this mechanism-derived inequality produces no PAR seal and no scientific
claim.

For an admitted attempt, its RSS is
`max(W, terminal supervisor SELF ru_maxrss)`. The value is phase-identifiable:
all supervisor history through the fork is dominated by a peak actually
reached by the current worker, while any larger terminal SELF HWM necessarily
arose after the fork inside the current attempt. The same proof is repeated
independently for B1 and P1. CPU is still only the boundary delta of
`getrusage(SELF)+getrusage(CHILDREN)`; `wait4` CPU is never added again.

Before terminal P, the conductor has completed every fixture and identity
comparison, written and fsynced every indexed regular no-follow file,
rejected nonregular or extra directory members, written the self-excluding
artifact index, derived both aggregate phase-byte entries, hashed all 15 seal
inputs, and opened the publication descriptors.  The terminal P boundary
captures process-family CPU, monotonic wall, peak RSS, and canonical UTC.
The successful P worker remains blocked on a one-byte release pipe after
closing its outputs while the supervisor performs that bounded preparation;
the supervisor then releases and reaps it, checks `W >= H`, and captures the
terminal P boundary. Thus no outer wait or unreaped child remains for
`PAR_report`.

After that boundary the finite `PAR_report` closure may only inject the four
terminal values, do bounded integer reconciliation/cap comparisons, assemble
and canonical-encode once the fixed 15-key seal, enforce both 5,171 and 65,536
byte limits, exclusively create/fsync `par_seal.json`, fsync staging,
no-replace rename the directory, fsync the parent, close descriptors, and
exit silently.  It performs no import, child launch/wait, clock sample, file
read/stat/list/hash, fixture work, or post-publication output.

The immutable PAR tree contains exactly index-listed B/P files plus
`artifact_index.json` and `par_seal.json`.  Independent review lives at
`docs/saq_a4_v2_par_artifacts_independent_review_2026_07_14.md`; the later E
binding lives at
`docs/saq_a4_v2_execution_authority_2026_07_14/par_review_binding.json`.
Neither is a PAR-tree member.  Admission requires strict commits
`I < P < R < E`, identical PAR tree OIDs at P/R/E, exact recursive regular
blob modes/names/OIDs, and exact `git show R:path` bytes for the seal, index,
and review memo.  The E binding also records
`par_seal_schema_pass=true` and
`par_seal_maximal_instance_bytes=5171`; these are reviewed prior facts, not a
runtime relaxation of either seal-size guard.

### 8.2 Publication-byte and RSS ownership

Every publisher reserves the global research-evidence or bundle bytes before
its no-replace rename.  A child publisher receives the already charged global
operand and rejects overflow before publication. The exact reviewed B/P
research-evidence bytes are bound once as a sealed global baseline before E;
they participate in every later prepublication/global cap comparison but are
inserted only once when the final per-phase objects merge.

Separately launched B/P workers report the process family's own
`wait4`/`getrusage` peak RSS and additionally satisfy the natural-dominance
proof above. For E/V/archive, a receipt records the maximum of the waited
family's peak and the terminal supervisor SELF+CHILDREN high-water mark. This
conservative envelope includes parent-side response parsing, output
validation, and cleanup, so those operations cannot cross 24 GiB invisibly.
It is an operational hard-cap witness, not a claim of exact phase-local memory
attribution: an earlier cumulative high-water mark may be repeated, but an
earlier crossing would already have stopped at its own boundary. Long-lived C
phases retain their explicitly labelled shared-cumulative scope.

The verifier and archive wrappers use a frozen typed exit channel: code `2`
means `EVIDENCE_INCOMPLETE_NO_DECISION`, code `3` is reserved for a registered
prepublication `RESOURCE_INCOMPLETE_NO_DECISION`, code `4` means
`ARTIFACT_INVALID`, code `5` means `IMPLEMENTATION_INVALID`, and code `6`
relays an external signal from the verifier's nested native child so the phase
may use its sole restart. Any other unexpected positive code is implementation
invalid. Thus a child-only global CPU or evidence-byte stop
cannot be demoted merely because the parent did not independently observe the
same operand before reaping it. Code `3` is prepublication-only: if its target
is already visible, the parent records an implementation invariant failure
instead of accepting the resource classification. Target visibility controls
the receipt disposition and retry prohibition; it does not otherwise erase a
more specific child status. A parent-observed cap crossing is merged with the
child status by the frozen precedence order.

Every launched E, V, or archive family leader is reaped before its terminal
receipt is constructed. Response transport, canonical output, exact
phase-interface identities, byte-ledger admission, staging disposition, and
owned-stream cleanup are all resolved before the terminal snapshot and are
folded into that same receipt. In particular, V's exact native binary, argv,
status, summary size, and summary-hash response is checked inside the V
boundary; it cannot leave a successful V receipt and charge failed validation
to archive. A post-launch parent failure enters one atomic deferred-SIGINT
recovery section, closes its inherited control descriptors, kills if
necessary, and must-reaps the child before proceeding, so an open parent pipe
writer cannot prevent response EOF and a second SIGINT cannot escape between
those operations.

The Python V/archive wrapper launch has no fork-to-interpreter SIGINT race.
Prelaunch first requires SIGINT to be unblocked with CPython's default
interrupt handler; an inherited blocked mask or custom handler is a failed
precondition, not a runtime variant.
The supervisor blocks SIGINT immediately before `Popen`, the child inherits
that mask, and the wrapper installs `SIG_DFL` and unblocks before argparse or
phase work. The parent restores its own mask immediately after `Popen`; a
parent SIGINT at that edge enters the ordinary kill/reap Resource path. E uses
the same parent-before-fork mask, then installs `SIG_DFL` and restores the
prior mask in the child before any evidence work.

At terminal handoff, the parent first observes the exact child with
`waitid(P_PID,...,WEXITED|WNOWAIT)`, blocks SIGINT while the child is still
waitable, and only then performs the unique `wait4`. SIGINT remains blocked
through response and output validation, ledger mutation, cleanup, required
post-cleanup validation, the terminal snapshot, and receipt append. Pending
SIGINT is synchronously consumed and folded into that receipt as
`RESOURCE_INCOMPLETE_NO_DECISION`; it prohibits retry and archive's terminal
resource-return exception. The prior mask is restored only after the receipt
exists. E uses the identical post-terminal handoff. Thus a launched attempt
cannot be asynchronously torn between reap and receipt construction, while a
pre-terminal SIGINT retains the existing prompt kill/reap behavior.
If that normal terminal handoff itself is interrupted or fails, recovery
atomically blocks SIGINT before issuing SIGKILL and enters a must-reap `wait4`
loop; further SIGINT remains pending and is folded into the Resource receipt
only after the unique child usage has been collected. A second SIGINT cannot
escape with a launched child still waitable.

Wrapper stdout and stderr are no-follow regular files, admitted to the byte
ledger before allocation, and each has an exact 1 MiB transport ceiling.
Published JSON is no-follow statted and its complete visible size is recorded
as one atomic ledger mutation before a read; the read is then bounded by the
4 GiB research-evidence ceiling and proves stable descriptor/path identity.
The producer-native diagnostic path retains the complete stderr file size in
the ledger but reads only a stable 4 KiB prefix. No diagnostic truncation
allocates the untruncated file.

The nested V native exchange does not use `communicate()` and has no private
16 MiB result threshold. A nonblocking selector writes the at-most-1 MiB
canonical request while draining stdout and stderr concurrently in 64 KiB
chunks, and runs the registered CPU/wall/RSS publication-reserve watchdog at
least once per second even under continuous I/O. Stderr is never accumulated:
the wrapper retains only its integer byte count, SHA-256 state, and one chunk.
Stdout is retained only up to
`4 GiB - prior_research_evidence_bytes`, where the prior operand has already
been proven equal to exact PAR plus the five producer-evidence files. Every
schema-valid response and final verifier summary reuse identical canonical
`decision_counts_observed` and `discrepancies` subtrees, while the summary has
the larger fixed envelope; the implementation asserts
`summary_size >= native_stdout_size` before applying the ordinary registered
prepublication evidence cap. Thus crossing this drain budget proves that no
admissible summary can be published and is the existing Resource result, not a
new scientific ceiling. Failure cleanup closes the three pipes and must-reaps
the process group without an unbounded diagnostic drain.

Any failed E/V/archive or producer staging tree admitted for discard is
inventoried only after its child has terminated. The root must be a real
directory opened with `O_DIRECTORY|O_NOFOLLOW`; recursion stays on verified
directory fds, and every child is opened relative to its parent with
`O_NOFOLLOW` and revalidated by device/inode/mode/size/timestamps. Every member
must be a real directory or regular file. A symlink, device, socket, FIFO, or
other special node is artifact-invalid rather than silently omitted or charged
through a target outside the owned tree.

All publication targets, phase staging roots, wrapper work directories, and
owned streams use no-follow presence probes, so a broken symlink is never
mistaken for absence. `DISCARDED` is written only after target absence and the
physical absence of every applicable staging/work namespace are confirmed;
an unknown or retained entry uses `NONE` and cannot authorize retry. A
non-directory regular staging root is charged as created/deleted partial bytes
before unlink; links and special nodes are classified without following their
targets and then safely unlinked when possible.

The inherited E child has a separate bounded typed response: explicit
artifact, implementation, resource, or evidence failures retain their
status, while an unknown exception or an out-of-vocabulary status is
implementation invalid. A partial response left by a raw external signal is
discarded rather than parsed as a scientific failure. Response, staging, and
child-byte-ledger errors are delayed only until the E receipt and parent cap
merge have been formed; E still stops immediately afterward. For an already
visible E publication, the response must contain the exact ordered five-file
identity inventory, and its file-size sum, `total_bytes`, net created-minus-
discarded bytes, retry-history created/deleted/peak fields, and research-
evidence bytes must agree. V independently
requires the supervisor's prior research-evidence operand to equal the exact
reviewed PAR bytes plus the sizes of the five producer-evidence files it
opened and validated. For an already visible external output, the parent
records created, peak-live, and research-
evidence/archive bytes as one complete ledger mutation before reporting any
postpublication byte-cap crossing. Thus the archive-only resource return
cannot omit the published archive bytes.

For V, only code `6` proves that the verifier wrapper cleaned up and reaped its
nested native process before requesting the one restart. A raw signal death of
the wrapper cannot prove that fact because the native runs in its own process
group; it is supervisor/unreaped-child loss and therefore RESOURCE with no
retry. E and archive have no nested capable child and retain their one raw-
signal restart.

If a successful archive publication is complete but the parent's
postpublication byte accounting or terminal sample first crosses a registered
phase/global resource ceiling, its local receipt is
`RESOURCE_INCOMPLETE_NO_DECISION/ATOMICALLY_PUBLISHED` and returns the already
complete archive body to the terminal publisher. F then freezes
`resource_complete_through_archive=false`. E or V cannot use this exception
because their missing downstream inputs would prevent a complete wrapper.
Eligibility is set only by the complete atomic archive-byte ledger mutation
or the terminal CPU/wall/RSS/study-cap comparison, and only after canonical
output, identity response, stream cleanup, and the exact pre-F tree validator
all succeed. Control/stream failures, oversized or invalid output, an
interrupted validator, or supervisor SIGINT can never use this exception.

## 9. Checkpoint and file-count bindings

`phase_start_checkpoint.input_file_count` is the number of already published,
immutable regular files admitted to that phase:

```text
E_emit          4 bundle files when U395 completed, otherwise 0
V_replay        all published bundle files plus the 5 evidence files
E_archive_body  the same files plus verifier/verifier_summary.json
```

For an early prefix before U395, E_emit still publishes the five schema-frozen
evidence files; V_replay therefore starts with exactly five input files and
the archive starts with those five plus the verifier summary. No staging,
temporary, source, build, contract, or parity file is counted in this field.
Their identities remain visible elsewhere in the manifest and file ledger.

`archive_body.pretrailer_files` is the ascending UTF-8 path-byte inventory of
all published bundle files if present, all five evidence files, and the
verifier summary. Its `attempt_ledger` and
`phase_receipts_through_verifier` contain the same receipt multiset: the first
is chronological by start instant with phase/attempt ties; the second is
phase order then attempt id.

Before reading those files, the independent archive enumerates the artifact
root without following links. At that instant the only permitted root members
are `evidence/`, `verifier/`, optional `bundle/`, and the active registered
`.e_archive_body.staging/`; their memberships are exactly five, one, optional
four, and the two wrapper streams respectively, and every leaf is regular.
After archive publication the parent removes the wrapper streams and staging
directory, then re-enumerates the exact root—now including only the one-file
`archive/` directory—before taking the archive terminal snapshot and receipt.
This closes complete pre-F membership inside `E_archive_body`; F consumes the
in-memory archive object and identity without rereading, reparsing, restatting,
or rehashing the archive body.

The archive independently reconstructs status inputs rather than trusting the
supervisor booleans. C receipt reasons determine sticky artifact and
implementation validity, combine with evidence-derived controls for control
validity, and make any explicit C resource-stop receipt resource-incomplete in
addition to the numeric CPU/wall/RSS/byte recomputation. Both `true` and
`false` are admissible when they match those facts: in particular, a valid
retained prefix may be archived as an `ARTIFACT_INVALID` failure wrapper after
a later unpublished temporary-file boundary failure. Either direction of a
receipt/status mismatch rejects archive publication. A published bundle is a
separate hard invariant: it requires exactly one atomically published
`C_bundle_io` receipt with `PHASE_COMPLETE` at U395 and cannot coexist with a C
artifact-failure receipt. Any higher-precedence terminal C status also remains
the causal process status if a later E, V, archive, or trailer operation fails;
the later local receipt or error is still classified on its own facts. Within
each producer attempt, only its last C receipt may be terminal; every earlier C
receipt is an unpublished `PHASE_COMPLETE` phase boundary. Attempt 1 exists
only after attempt 0 ends as a discarded `EXTERNAL_INTERRUPTION`, and a
published U395 receipt is the last C receipt of the final attempt. Completed
prefix indices are monotone within each attempt, but attempt 1 restarts at U0;
therefore its retained terminal prefix—not the maximum discarded attempt-0
prefix—binds the producer manifest and every E/V/archive checkpoint. Each
attempt's phase inventory is a consecutive prefix of
`C_setup,C_core,C_bundle_io`; their completed-index ranges are respectively
`0`, `0..394`, and `394..395` for any event that reaches the evidence
boundary. A pre-U000 failure has no encodable prefix and stops before E/V or
archive. A final unpublished success reason is
forbidden: `PHASE_COMPLETE` is terminal only for the atomically published U395
bundle; primary/representation stops use `NONE`, terminal failures use
`DISCARDED`, and a lone final attempt-0 interruption is admissible only when
its same receipt ledger proves the registered resource trigger. A nonterminal
phase boundary closes only after U000 for `C_setup` and U394 for `C_core`.
If the primary inequality first crosses at admitted U395, the receipt remains
`PHASE_COMPLETE/ATOMICALLY_PUBLISHED`; the separately retained cap operand
then produces the cost no-go rather than relabelling a complete publication.
Receipts are contiguous within an attempt, and attempt 1 starts at the exact
terminal UTC boundary of attempt 0; attempts never interleave.

The final artifact index contains every archive pre-trailer identity plus
`archive/archive_body.json`, `final/resource_ledger.json`, and
`final/decision.json`; it excludes itself. Its `producer_commit` is the clean
source/execution commit. The later evidence commit binds the index as an
external Git blob fact and is not placed inside the index, avoiding a commit
self-reference.

`E_archive_body` returns its already validated canonical object and exact
size/SHA-256 identity before its terminal boundary.  `F_trailer` must consume
those in-memory values without rereading, reparsing, restatting, or rehashing
the published archive.  It canonical-encodes each of resource ledger,
decision, and self-excluding artifact index exactly once; the index itself is
not hashed inside the event.  Publication writes those three already encoded
payloads, fsyncs, no-replace renames, fsyncs the parent, closes the publication
descriptors, and terminates through a direct silent process exit with no
post-publication comparison, Python return path, or status print.
Every fallible parent/staging open, mkdir, write, prepublication fsync, and
descriptor close before that terminal rename is a typed
`EVIDENCE_INCOMPLETE_NO_DECISION` operation and preserves any higher-priority
sticky status. Once the no-replace rename begins, the frozen direct-exit path
remains the only authority; it performs no recoverable Python work.

Bundle-manifest child paths are bundle-relative. Every archive/index
`file_identity.path` is artifact-root-relative. Implementations must not mix
those two namespaces.

## 10. Independent verifier contract

The verifier uses a separately written optimized exact solver capable of the
full registered shape. It recomputes global optimality and all tie decisions;
checking only the producer's chosen partition objective is insufficient. Its
direct rational-to-IEEE conversion is separately implemented. It parses
producer artifacts with its own strict duplicate-key- and float-rejecting
parser and creates logical records with its own canonical encoder.

For blocks it reconstructs every start and accepted step from the frozen raw
panel and recorded initialization, reproduces before/after assignments,
centers, SSE bits, controls, winner, and all assignment/center hash preimages.
For representations it independently assigns labels, constructs mixed-radix
addresses, packs and unpacks payloads, checks padding and invalid addresses,
and reconstructs all bundle bytes.

Matching producer hashes without reconstructing their preimages is
`VERIFICATION_INVALID`. The verifier wrapper persists discrepancies and
atomically publishes a complete summary even for a semantic mismatch; a
missing/partial publication remains the higher-priority evidence case.

## 11. Prelaunch and privacy boundary

The process inventory implements exactly the protocol's one frozen numeric-
PID snapshot and two-stage effective-UID filter. It reads byte-oriented proc
and executable-link interfaces and preserves the exact raw preimages. It does
not retry, skip a raced PID, filter zero-tick processes, decode arbitrary
bytes as text, or broaden the self allowlist.

PAR admission independently replays the complete filter and same-user arrays:
exact key sets, strict PID/filter ordering and one-to-one mapping, every raw
status/stat/cmdline/executable hex preimage and recorded SHA-256, parsed
PID/effective UID/start identity and CPU fields, initial/final stability,
marker basename order, the unique preflight self, classifications, and every
conflict bit. Counts or top-level pass flags alone are never accepted.

Those raw command lines may contain private arguments or credentials. The
protocol permits no redaction because it would change the verifier preimage.
Before any `A4-V2-SRUN` authorization, the user must separately inspect this
privacy risk and ensure no same-user command line contains material that may
not be committed. This warning does not authorize reading or collecting a
process inventory during `A4-V2-I` or PAR.

## 12. Static-review ceiling

Static source review checks completeness, source separation, constants,
state-machine edges, ownership, hash/timing DAG, and failure precedence. It
must explicitly state that no compiler, import, test, RNG, parity, synthetic
event, generated artifact, or data read occurred.

Even a clean review supports only:

```text
SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS
```

It does not establish that the code builds, that parity passes, that the
synthetic instrument fits its cap, or that arbitrary cardinalities improve an
ANN system.

## 13. CACHE-I additive evidence binding

The `A4-V2-CACHE-I` rebinding is governance-only and preserves the scientific
instrument above.  Its exact machine authority is
`docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json`; its exact
37-file-source manifest/tree and separately identified inline PREP bootstrap
are in `docs/saq_a4_v2_implementation_manifest_2026_07_14.json`; and its
complete executable-unit and parent-precedence closure is
`docs/saq_a4_v2_cache_static_closure_2026_07_15.json`.

The parent PAR launch is frozen to:

```text
MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -B script/run_arbitrary_cardinality_a4_v2.py \
  par docs/saq_a4_v2_par_artifacts_2026_07_14
```

The registered entrypoint observation occurs after the first CPU/wall
snapshots and before importing an A4 module.  It binds raw
`/proc/self/cmdline`, cwd, interpreter flags, bytecode/cache state, bounded
`sys.path` and `sys.meta_path`, retained modules, and the pinned running
CPython leader and installed bootstrap.  It is rechecked before the B terminal
and before the P terminal.  The cache namespace and ten adjacent legacy paths
must be absent under no-follow semantics at all three checkpoints.

The environment-preimage is extended by exactly one seventh top-level field,
`python_cache_policy`.  It binds only identities and expectations available
before B/P execution: the launch/startup observation, cache protocol/static
closure, source/schema/control, clone/PREP/BIND slots, expected B/P checks,
and independent-verifier contract.  It does not hash a future verifier result.
The actual B/P observations and independent result are instead carried by the
P-owned canonical `cache_policy_verification.json`.  It persists the exact
bounded canonical fd-198 control bytes as lowercase hex, binds and recomputes
their identity, and requires the decoded observations to recompute the result's
module summaries.  The artifact is validated, indexed, and sealed before the
P terminal.  This is independently reconstructible one-way publication, not a
self-reference.

The independent cache verifier is a standalone stdlib-only process launched
only in P through the already verified CPython descriptor with `-I -B -S`, cwd
`/`, the exact three-key environment, and bounded canonical control on fd 198.
It imports no repository module and writes only the registered P artifact.
Its resource/stream/accounting work belongs to P.  The existing SRUN path may
only receive dormant admission parsing for this new sealed input; CACHE-I
does not authorize SRUN and SRUN never launches the cache verifier.

Cache mismatch adds no retry or status.  Startup option/cache-state failure is
`PRECONDITION_NOT_MET`; source/clone/binding/origin/cache mismatch, including
a well-formed verifier mismatch report, is `ARTIFACT_INVALID`; verifier
schema/process/canonicalization defects after successful spawn and reap are
`IMPLEMENTATION_INVALID`.  The standalone verifier reserves exact exit `75`
only for an internal resource/system-call failure that cannot truthfully
publish its result; the parent maps only that exit to its existing resource
class, while exit `70` and every other ordinary nonzero remain implementation
defects.  Resource/system-call failures and a verifier wait status that reports
POSIX-signal termination delegate to the byte-preserved parent mapping.  Only
that last wait-status event may enter the already existing P signal-retry
boundary, and only while its existing `retry_safe` predicate holds.  Mismatch,
identity, schema, malformed output, ordinary nonzero exit other than the exact
resource channel, and any post-boundary failure are never translated or
retried.

The **PAR** build-manifest and **PAR** artifact-index cache-aware shapes are
version 2.  This does not renumber the later SRUN `F_trailer`
`artifact_index_v2`, whose schema remains version 1.  The PAR artifact index
must contain exactly one identity for
`cache_policy_verification.json`; the unchanged PAR seal binds its exact
bytes.  Both `_post_par_report_unchecked` and `_post_par_report` remain raw-byte
equal to the parent baseline, so no cache observation, import, stat, read, or
hash operation occurs after the P terminal snapshot.

The PREP source and inline bootstrap are published only as statically reviewed
future machinery.  They are not executed by CACHE-I, and no isolated clone,
token, receipt, CACHE-BIND object, PAR event, data result, or scientific claim
exists at this stage.  The maximum conclusion is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` after an exact committed
target and independent review find no issue at LOW or above.

The future PREP receipt contract is nevertheless closed at source-review time.
Its final resource ledger keeps seven mutually exclusive storage categories
(`directories`, loose Git objects, pack payloads, other Git administration,
tracked checkout, receipt, and temporary state), reconciles each category's
logical bytes, allocated bytes, and entry count to the outer totals, and
separately records ten supervisor/entry/fsync/process/capture operation counts.
Bounded journal snapshots carry the observed process inventory and completed
wait records, including per-process `/proc/io` when available and `ru_maxrss`.
Unavailable network or process-I/O counters are explicit null observations,
never inferred zeroes.  These are future evidence fields, not measurements
made by CACHE-I.

### 13.1 Exact CACHE-I static seal and narrow syntax record

The final locked filesystem-source closure is exactly 37 files: 27
native/CMake sources and 10 Python sources.  Its unchanged canonical-tree
algorithm now produces:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2
```

The separate inline PREP bootstrap remains outside that 37-file preimage.  Its
exact ASCII identity is
`9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b`
over 19,631 bytes; its durable-start prologue identity is
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`
over 2,778 bytes.  The 37 file sources plus this inline source are exactly 38
statically enumerated executable units.

After the original CACHE-I source-only boundary, the user separately granted
the narrow authority `A4-V2-CACHE-I-SYNTAX`.  Under that distinct authority,
`/usr/bin/python3.9` accepted `compile()`-only syntax checks for the exact
six changed/new outer Python source snapshots and the exact inline source
snapshot.  No resulting code object was executed; no module was imported; and
no build, fixture, RNG, PREP, cache-verifier, PAR, SRUN, data, quarantine, or
SAQ/CAQ operation was authorized or performed.  This result establishes only
Python 3.9 syntax acceptance for those seven exact byte snapshots.  It does
not establish importability, executability, correctness, runtime-policy
validity, schema acceptance, parity, or scientific evidence.

The additive cache-authority object's frozen
`no_execution_attestation` and prohibition list continue to state the
original CACHE-I authority exactly because the future verifier requires those
literal bytes.  The later syntax-only exception is recorded separately in the
static closure, this binding, the provenance crosswalk, `AGENTS.md`, and
`TASK.md`; it must not be silently folded into or misrepresented as an
operation under the original CACHE-I authority.

The canonical static-closure identity is
`f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0`
over 218,872 bytes.  The cache-authority identity is
`5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec`
over 42,903 bytes.  These are uncommitted target-worktree identities until a
focused exact target commit and its direct-child independent review close the
frozen predicates.  WIP and untracked files remain nonevidence.

The current maximum worktree status is therefore:

```text
STATIC_SEAL_COMPLETE_PENDING_EXACT_TARGET_COMMIT_AND_INDEPENDENT_REVIEW
```

It is below `GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` and grants no
PREP, CACHE-BIND, PAR-R1, SRUN, data, or SAQ/CAQ authority.

### 13.2 A4-V2-PREP-HOST-I active source-authority rebind

The separately reauthorized `A4-V2-PREP-HOST-I` target is an additive,
source-static artifact-governance rebind.  Its direct parent is the clean,
pushed, publication-closed HOST-I source-authority-erratum review head
`9fa9528f4181d51fe6e060c1de14ea568eb31c4a`.  The additive authority DAG is:

| Authority object | SHA-256 | Bytes |
| --- | --- | ---: |
| HOST-P rebind contract admitted as the eighth cache component | `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09` | 10,684 |
| HOST-I source-authority erratum protocol at target `6fe8544` | `5d9ac7222f93f00de5f2cd96b6df16d389b9f3123b604115c515bae963a1088d` | 14,716 |
| HOST-I source-authority erratum contract at target `6fe8544` | `01dadbe2ba73a429a67d7029b5e4dafafb6b400a6067767a1aac161e9457977a` | 10,967 |
| HOST-I source-authority erratum review at head `9fa9528` | `c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331` | 11,426 |
| HOST-I authorization record | `7a07e05eb2b96c7ecd57facf9f1b7405a63f0d6d66d2af3cad3a1eeb626ce3b0` | 11,928 |
| HOST-I authorization independent review | `bda4f52b549e28b69cca5c012c21e12867266e0c5920eda27f7df87e478d69e9` | 14,740 |

Exactly seven active source occurrences replace the old CPython leader digest
with the sole `.el9_8.2` digest
`c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b`
in the frozen `1 + 2 + 2 + 1 + 1` source partition.  The resulting active
filesystem-source identities are:

| Source | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `script/a4_v2_cache_policy_verifier.py` | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,568 | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` |
| `script/a4_v2_isolated_clone_prep.py` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 | `d671531132eb0c490dec1953ca778e8d03913b3d` |
| `script/a4_v2_runner.py` | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 | `44e1a8078caf8774d1005f88265c87167e462eb7` |
| `script/a4_v2_verifier.py` | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 | `d8e0bdc6df0865e95dfe631446d108368640e25d` |
| `script/run_arbitrary_cardinality_a4_v2.py` | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 | `21925cddb4d07a1ec046d405493980813a4d581a` |

The complete inventory remains exactly 37 filesystem sources and 38
executable units.  The canonical sorted 37-source tree is
`97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a`.
The active 19,631-byte inline PREP source is identically bound by its four
authorities at
`d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56`;
its raw 2,778-byte pre-START prologue remains byte-identical at
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`.

The rebound derived objects are:

| Object | SHA-256 | Bytes |
| --- | --- | ---: |
| cache runtime schema | `47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896` | 23,762 |
| cache runtime maximal instance | `5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42` | 4,439,071 |
| cache static closure | `815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d` | 218,872 |
| cache protocol authority | `09c1b6adf429f933620e503e8ee479b2b17380e460b8961782a78309a18e9885` | 43,128 |

The cache authority now has exactly eight protocol components: the seven
historical entries are byte-for-byte identity-preserved and the sole new
entry is the 10,684-byte HOST-P contract above.  The verifier admits it only
through one exact set member and one exact path-map member.  This adds 197
permanent source bytes and exactly one invocation of the existing
protocol-component `_check_identity` loop.  On physical success the existing
`filesystem_bytes_read` aggregate therefore increases by exactly 10,684;
fallback/mismatch accounting, caps, status mapping, and error precedence are
unchanged.  Across the exact fourteen-path target projection, the total
permanent tracked byte delta relative to parent `9fa9528` is
`+12,758` bytes; this is governance overhead, not scientific
construction or query work.

The implementation manifest keeps its existing schema and binds its existing
`authorization_identity` field to the committed HOST-I authorization record.
`build_status` remains `NOT_AUTHORIZED_NOT_RUN`.  The earlier
`A4-V2-CACHE-I-SYNTAX` source and inline identities above section 13.2 remain
historical evidence for the old snapshot only; they are deliberately not
relabeled as applying to these changed bytes.

The distinct `SOURCE_HISTORY_MISMATCH` remains unresolved: a future cache
verifier would compare these new active blobs with historical CACHE-I/PREP
commits that correctly retain old blobs.  This does not block this source-only
target, its static review, or PREP itself, but it forbids cache-verifier/PAR
readiness and requires a separate later protocol and source authorization.
No Python, syntax check, import, compiler, build, test, verifier, PREP, clone,
data, quarantine, or SAQ/CAQ operation was run.  Until the exact target's
direct-child independent review passes, the maximum claim is only
`HOST_I_SOURCE_STATIC_TARGET_FORMED_REVIEW_PENDING`; it is not yet an
independently established `HOST_IDENTITY_REBOUND` result.

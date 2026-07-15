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

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

The setup and whole-directory bundle-publication units are supervisor units.
Only U395 publishes `bundle/`; individual bundle files are not independently
published scientific prefixes.

Bundle bytes and their global ceiling are validated and reserved before the
no-replace directory rename.  Immediately after that rename the producer sets
an irreversible supervisor marker; the remaining parent-directory fsync and
ledger commit contain no protocol validation.  If any failure occurs after
the target becomes physically visible but before U395 is admitted, the
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

Resource-cap observations made at a terminal C boundary, after failed-tail
cleanup and receipt work have been charged, are sticky.  A simultaneous
higher-precedence failure such as `CONTROL_INVALID` retains its declared
status, but cannot make `resource_complete_through_verifier` true; absent the
visible-publication fail-stop above, the archive receives that independent
resource-incomplete operand. The final decision carries the same sticky fact
forward, adds the independently reconciled archive-phase CPU, wall, RSS, and
byte ceilings, and derives `resource_complete_through_archive` from that
combined boolean rather than from the winning status label.

Concretely, after constructing a terminal C receipt the supervisor takes one
fresh process-family snapshot, applies the sticky cap check, and extends that
same just-closed receipt and boundary through the fresh CPU, wall, and RSS
values. The incremental CPU is attributed once to the current C owner and
`last_cpu` advances to the same boundary, so a retry or E starts after—not
before—that tail. This makes the producer-attempt cap independently
recomputable from receipts without charging the tail again downstream.

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
operand and rejects overflow before publication.  Separately launched
B/P workers and E/V/archive receipts report that process family's own
`wait4`/`getrusage` peak RSS; B/P additionally satisfy the natural-dominance
proof above. The long-lived producer phases retain their explicitly labelled
shared-cumulative scope. No cumulative child peak or pre-attempt supervisor
peak is relabelled as a current child phase peak.

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

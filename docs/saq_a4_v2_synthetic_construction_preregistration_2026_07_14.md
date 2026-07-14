# A4 V2 Synthetic Comparative-Instrument Construction Preregistration

Date frozen: 2026-07-14

Stage: `A4-V2-PROTOCOL`

Status: **FROZEN_NOT_AUTHORIZED_FOR_IMPLEMENTATION_OR_EXECUTION**

Protocol version: `saq-a4-v2-synthetic-construction-20260714-schema1`

Machine-readable contract:
`docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`

Normative artifact schemas:
`docs/saq_a4_v2_artifact_schema_2026_07_14.json`

## 1. Authority and purpose

The user authorized a new primary-source review and, only if that review
returned go, a new protocol. The review returned `GO_PROTOCOL_DESIGN`. This
document exhausts that authorization. It does not authorize code, a build, a
parity command, random-number generation, a synthetic cost run, a dataset
read, or an SAQ modification.

The predecessor A4-1S result remains terminal at
`saq-arbitrary-cardinality-analysis@f1b464b6803e0f435055b45891255be0129cb9be`.
Its cost evidence is commit
`9ce105275d433c95d82557d3cbe1928916fa9ca8` and its result is
`NO_GO_EXACT_SOLVER_COST`. That historical name covered the entire frozen
construction/evidence pipeline, not only its native solver. V2 neither
relabels that result nor removes a term from its old timer after seeing the
outcome.

V2 asks a new, narrower question:

> Can the complete four-arm synthetic diagnostic instrument, with A4-1S's
> scientific shape, exact-rational scalar/allocation semantics, and
> deterministic block/encoding semantics unchanged, fit a frozen internal CPU
> admission cap while all research-only work is separately measured and every
> produced decision is independently reproduced?

This is a methodology gate for a possible research direction. Evidence
formatting, hashing, exact replay, and bookkeeping are not contributions.

## 2. Registered claim and falsifier

The primary figure of merit is `T_instrument`, the CPU consumed to construct
the complete four-arm diagnostic instrument. It includes setup, every
registered model and code computation, and the compact intermediate bundle
writes. It excludes build, parity, independent review replay, and archival
evidence production, but those costs remain mandatory and separately metered.

A passage can establish only:

> On the frozen machine, toolchain, exact-rational scalar/allocation semantics,
> deterministic bit-level block/encoding semantics, panel, and full synthetic
> shape, the four-arm instrument met its internal one-panel admission cap, and
> an independent implementation reproduced every registered decision.

It cannot establish natural-data prevalence, candidate-only affordability, a
benefit over strong block VQ, SAQ integration, end-to-end index-build time,
index size on a benchmark, distance-estimator behavior, recall, QPS, a
Pareto-frontier move, or novelty.

The resource-admission claim fails if the verified full instrument exceeds the
registered CPU cap. A selected representation failure is a separate scientific
screen. Control, evidence, or independent-replay failures mean that no claim
is established; they are instrument-invalid states, not falsifiers. No result
from an incomplete evidence bundle is admissible.

## 3. Frozen scientific work

### 3.1 Synthetic panel and identity

The only scientific input is exactly:

```text
Generator(PCG64(20260713)).standard_normal((8192,128), dtype=float32)
```

It is generated with NumPy `1.23.5` in C order as little-endian binary32. Its
4,194,304 raw bytes must have SHA-256:

```text
10e128854768358323a8b13066a6f34076cfc7216db35992ac58ece0ec6f5b0c
```

Rows use `dataset_id=synthetic_cost_projection`, `cell_id=0`, and
`vector_id=0..8191` in ascending order. To preserve all prior hashed ordering
and initialization decisions, selection and block-start keys retain the
predecessor hash-domain string
`saq-attempt4-a4-1-20260713-schema2`; they do not substitute the V2 protocol
version. The ordered selection-digest stream must hash to
`6e7dbc26c7d5f63c2c8e5a5fa4d647cf3237597696c3f2431fd715ffbc712145`.

Generation itself is not authorized by this document. The fixed hash records
the predecessor's committed panel identity; it is not new evidence.

### 3.2 Exact scalar curves

For each of 128 coordinates, compute every requested cardinality
`K=1..256`. Canonicalize signed zero, decode each finite binary32 value as
exact `n*2^-149`, aggregate equal values, and sort exactly. For an interval:

```text
W = sum w_i
A = sum w_i n_i
C = sum w_i n_i^2
SSE = ((W C - A^2) / W) * 2^-298.
```

The producer uses the predecessor's complete-matrix Monge/SMAWK dynamic
program with arbitrary-precision exact comparisons. This protocol authorizes
no faster algorithmic replacement. The cardinality meaning is at most `K`.
An exact tie chooses more nonempty intervals and then recursive earliest
predecessors. For `K` above the distinct-support size, copy that support-size
solution and record its effective cardinality.

Selected exact means are converted directly and independently to binary64
and binary32 under round-to-nearest, ties-to-even. Conversion through an
intermediate floating format is forbidden. A selected binary32 scalar
alphabet that is not strictly increasing is `NO_GO_REPRESENTATION`.

### 3.3 Allocations and representation arms

Use 64 groups `(2h,2h+1)`, `h=0..63`, and both word widths `B=4` and `B=8`,
with capacities 16 and 256. For every group/rate solve the dyadic and arbitrary
product allocations from the exact scalar objectives. A tie chooses more used
states, then the lexicographically smaller cardinality tuple. Arbitrary
mixed-radix addressing is `u=z1+K1*z2`; unused addresses still pay the fixed
word/table capacity and are invalid.

Also compute the global dyadic capped control over all 128 coordinates with
per-coordinate widths `0..8` and total budget at most `64B`. Its tie rule is
the predecessor rule. It is an attribution control and cannot alone pass the
gate.

The four constructed arms are:

```text
dyadic_word
arbitrary_word
trained_block_vq
global_dyadic_pack_cap8
```

### 3.4 Block VQ, encoding, and packing

For every group/rate run all eight deterministic block-VQ starts with at most
300 complete Lloyd iterations. Start 0 is the arbitrary Cartesian product
plus deterministic farthest fill. Starts 1--7 use the predecessor's salted
farthest-first rule. Preserve the registered row order, assignment and
farthest ties, empty-center behavior, complete-step monotonicity, convergence
condition, and best-start rule. Nonfinite values, an increasing accepted SSE,
failed Cartesian dominance, nonconvergence, or fewer than `S` distinct
selected binary32 centers is `CONTROL_INVALID`.

Encode all 8,192 rows for every arm and rate. B4 uses low then high nibbles;
B8 uses one byte per group. Global labels are packed least-significant bit
first and zero-padded to the same paid 32- or 64-byte payload. Every payload
must round-trip. No lookup or query work is inferred beyond the frozen parity
fixtures because the synthetic panel defines no query workload.

## 4. Frozen platform and no speed rescue

The registered environment is:

```text
CPU       Intel(R) Core(TM) i9-10920X CPU @ 3.50GHz
compiler  GCC 11.5.0 20240719 (Red Hat 11.5.0-14)
flags     -O3 -fno-fast-math -ffp-contract=off
          -frounding-math -mfpmath=sse
Python    CPython 3.9.25
NumPy     1.23.5
GMP       6.2.0
MPFR      4.1.0-p9
OpenSSL   3.5.5 27 Jan 2026
rounding  FE_TONEAREST
MXCSR     0x00001f80, FTZ=false, DAZ=false
threads   1; OMP/OPENBLAS/MKL_NUM_THREADS=1
```

`-march=native`, fast-math, fused multiply-add, a different exact library,
machine, compiler, panel shape, solver family, or precision is forbidden. A
future implementation review must show that the producer performs the same
mathematical and algorithmic construction as A4-1S; V2 is not a post-hoc
implementation-speed contest.

The permitted implementation delta is limited to phase instrumentation, a
compact producer-output mode that omits research-only detail, intermediate-bundle
I/O, separation of the independent verifier, and compact evidence/archive
writers. Preserve the predecessor's native-child execution architecture and
charge required binary interchange, process launch/wait, TSV or equivalent
model parsing, direct rounding, and compact model construction to `C_core`.
Replacing those paths with an in-process or otherwise faster constructor is a
different protocol, even if it returns the same objective.

## 5. Non-overlapping resource ledger

The frozen CPU terms are:

```text
B_build       clean frozen build and binary materialization
P_parity      complete pre-run correctness/control fixtures

C_setup       instrument bootstrap, preflight, panel identity and order
C_core        all model computation plus required child/IPC/parse,
              controls, encoding, packing and round-trip work
C_bundle_io   intermediate model/code bundle write/hash/flush/close
T_instrument  C_setup + C_core + C_bundle_io

E_emit        compact research-evidence encoding, hashing, write/flush
V_replay      independent full semantic recomputation and comparison
E_archive_body timed archive bodies and authority-bearing preimages

T_study_metered = B_build + P_parity + T_instrument
                  + E_emit + V_replay + E_archive_body

F_trailer     finite reporting trailer outside T_study_metered
```

`T_instrument`, not a pure native-solver timer, is the primary figure of merit.
`T_study_metered` prevents a claim that reproducibility work is free. Build and
parity are explicit because they are real study costs. `F_trailer` is an
explicit measurement-closure exclusion, not missing scientific work.

Human implementation/review time, an SAQ adapter, full-vector index build,
query-kernel work, and query evaluation are `NOT_MEASURED`; the latter four are
also unauthorized. They are named exclusions, so neither `T_study_metered`
nor a pass may be presented as total project, deployment, or SAQ system cost.
Any invalid earlier V2 attempt remains separate historical evidence and may
not be erased or folded into a faster accepted observation.

Within `C_core` and `C_bundle_io`, also report this exact attribution ledger:

```text
C_shared_fit       all 128 exact scalar curves and common rounded records
C_arm_dyadic       dyadic allocation, labels, packing and bundle subranges
C_arm_arbitrary    arbitrary allocation, labels, packing and bundle subranges
C_arm_block        all block starts, labels, packing and bundle subranges
C_arm_global       global control allocation, labels, packing and subranges
C_common_manifest  shared schemas, bundle validation and final manifest
C_interrupted_tail child CPU not recoverably attributable below a killed unit
```

Their logical-run sum, plus `C_setup`, reconciles to `T_instrument` across all
attempts; `C_interrupted_tail=0` without an external child interruption. An
operation used by two arms is charged once to `C_shared_fit`, never duplicated
or allocated by a post-run percentage. Report the conservative descriptive
candidate-ready subtotal `T_arbitrary_ready_conservative = C_setup +
C_shared_fit + C_arm_arbitrary + C_interrupted_tail`; all unattributable
interrupted CPU is included even if it may have occurred later. Do not use it
for passage. A failure of the full primary FOM closes the four-arm controlled
instrument only; it cannot be cited as candidate-only construction evidence.

Phase ownership and switch points are normative:

| Operation | Owner |
| --- | --- |
| Bootstrap, imports, contract/numeric checks, panel generation/hash/order | `C_setup` |
| Optimized native DP state for every coordinate and `K=1..256` | `C_shared_fit` |
| Native child launch/wait, required binary/TSV interchange and parse | `C_shared_fit` |
| Every all-`K` tie-broken partition, exact mean, direct b64/b32 rounding, and compact in-memory optimum record | `C_shared_fit` |
| Allocation, block training, assignment, encoding, packing, round-trip and work counters | the named `C_arm_*` |
| Model/code canonicalization and writes needed by the A4 reference decoder | matching `C_arm_*` or `C_common_manifest` |
| Canonical research JSON, logical-record SHA-256, schema-only validation | `E_emit` |
| Independent semantic recomputation and comparison | `V_replay` |

`C_setup` ends only after panel identity and order are frozen in memory.
`C_core` ends only after all full-shape logical optima, models, labels, payloads,
round-trips, and work counters exist in memory. `C_bundle_io` then writes and
atomically publishes the complete intermediate directory; no `E_emit` work may
interleave. `E_emit` may only encode/hash already computed producer records; it
may not optimize, backtrack, derive a mean, round a centroid, choose a model,
assign a label, or regenerate a payload. This preserves all old mixed `scalar`
work except independent replay, while moving only research-format work outside
the primary FOM.

### 5.1 CPU and wall clocks

Each phase records integer process-family CPU microseconds from user plus
system deltas of
`getrusage(RUSAGE_SELF)+getrusage(RUSAGE_CHILDREN)`. Every child must terminate
and be waited before its phase boundary; no worker may cross a boundary. The
instrument runner's first executable action captures CPU and monotonic-wall
snapshots before argument parsing, scientific imports, filesystem checks, or
NumPy import. Thus imports and preflight cannot be hidden.

Every phase also records integer wall nanoseconds. Wall time is descriptive,
not decisive. CPU fields must be nonnegative integers and reconcile exactly
to both `T_instrument` and `T_study_metered`. Outside `F_trailer`, a wrapper may
not perform unmetered model, encoding, comparison, or hash work.

Resource-ledger `phase_attempt_receipts` are ordered by the frozen phase order
and then ascending `attempt_id`; attempt ids are contiguous `0` or `0,1`.
`phase_resource_ledger` has exactly eight aggregate phase entries in frozen
order. An unstarted phase has `started=false`, `attempt_count=0`, and zero CPU,
wall, and RSS with `peak_rss_scope=unstarted`; a started entry reconciles
exactly to its attempt receipts. `C_setup`, `C_core`, and `C_bundle_io` use
`peak_rss_scope=shared_cumulative_producer` when the OS exposes only one
cumulative producer peak; separately launched families use
`phase_process_family`. The
archive's attempt ledger is chronological by start instant with phase order
and attempt id as exact ties. These are canonical array orders, not
presentation choices.

### 5.2 Finite timing-closure rule

`E_archive_body` is a separately launched child. It verifies all already
closed producer/evidence/verifier files, hashes them, and writes and flushes
`archive_body.json`. That body contains the complete pre-trailer file ledger,
raw phase records through `V_replay`, gate operands, status inputs, and an
`E_archive_body` start checkpoint; it excludes its own hash and does not claim
its own size, terminal CPU/wall/RSS, or final scientific status. After atomic
publication, the child hashes its exact body bytes and returns only
`{size_bytes,sha256}` over its inherited supervisor pipe. The supervisor then
waits for the child and captures its final SELF+CHILDREN CPU, wall, and RSS.
Those values close `T_study_metered`. A missing atomic archive directory,
identity message, or clean child exit is `EVIDENCE_INCOMPLETE_NO_DECISION`.

The archive status-input object ends at published producer evidence and the
published verifier summary; it cannot claim archive or final-wrapper
completeness. After the archive child closes, `decision.json` may add clean
archive completion, but it marks the artifact index as required. Only atomic
publication of the final directory satisfies that last condition externally.

The supervisor then performs exactly one `F_trailer` in a new
`final.staging/` directory with exactly three files in this order:

```text
resource_ledger.json
decision.json
artifact_index.json
```

`resource_ledger.json` injects the captured `E_archive_body` terminal integers,
reconciles all phase/attempt totals, and references the archive-body identity.
`decision.json` applies only the frozen integer/status rules and references the
completed resource-ledger identity. `artifact_index.json` copies every
pre-trailer identity and adds `archive_body.json`, `resource_ledger.json`, and
`decision.json`; it excludes itself. The supervisor then fsyncs all three
files and `final.staging/`, atomically renames the whole directory to `final/`,
and fsyncs the parent. Its Git blob at the clean reviewed evidence commit binds
the index. A decision is therefore never independently published without its
index.

Every archive or artifact-index file ledger uses normalized artifact-root-
relative POSIX paths, forbids absolute paths, `.`/`..` components and duplicate
paths, and orders entries by ascending UTF-8 path bytes. This is the one
registered array order used by both archive and index implementations.

`F_trailer` may only inject captured integers, perform frozen integer
addition/comparison and status precedence, copy existing hashes, hash the first
two wrappers, and write/flush/close. It may derive no model, label, payload,
verification result, resource sample, or scientific statistic. Canonical byte
ceilings are 1,048,576 for `resource_ledger.json`, 65,536 for `decision.json`,
and 2,097,152 for `artifact_index.json`; crossing one is
`EVIDENCE_INCOMPLETE_NO_DECISION`, not permission to enlarge the trailer.

The CPU/wall duration of these three final writes is outside
`T_study_metered` and is not interpreted; otherwise recording that duration in
one of the files would recursively change the value. The exclusion is finite
and fully disclosed by file names, fields, byte sizes, and hashes. A missing or
partial trailer is `EVIDENCE_INCOMPLETE_NO_DECISION`, never a scientific
result.

This gate has exactly one logical admission observation. It is reported as
one observation on the frozen machine, not as a performance distribution or
repeatability estimate. Best-of-retries, a median, or discarding a slower
attempt is forbidden. Record system load, CPU governor, affinity, concurrent
process policy, start/end timestamps, and every interruption. If an external
interruption is resumed, CPU from every attempt--including repeated setup,
validation, loading, or recomputation--is added to the same logical-run
ledger; previously consumed work cannot disappear.

Before launch require Linux
`5.14.0-687.24.1.el9_8.x86_64`, governor `performance`, turbo enabled
(`intel_pstate/no_turbo=0`), SMT active, allowed affinity `0-23`, at least
24 GiB available physical memory, at least 16 GiB free output space, and no
other A4 producer/verifier or SAQ cost run owned by the user. A mismatch is
`PRECONDITION_NOT_MET`; it authorizes no alternate machine or setting. Record
load average and all same-user processes, including zero-tick processes, but
apply no post-hoc load filter. The outcome is a single resource-admission event
with the exact integer boundary; there is no near-limit rerun or claim of
expected timing.

For every launched observation,
`evidence/producer_manifest.json.prelaunch_observation` persists the exact
prelaunch snapshot. Complete raw `/proc/loadavg` and `/proc/meminfo` bytes are
stored losslessly as lowercase hex with their SHA-256. The first three
load-average decimal tokens are stored as canonical strings; the unique
`MemAvailable` kB field and its exact multiplication by 1,024 are recorded.
Free output bytes are `statvfs(output_root).f_bavail * f_frsize`, with both
operands, the normalized absolute output root, and filesystem device id
recorded. The snapshot also records UTC time, effective UID, the preflight
`(PID,start_time_clock_ticks)` identity, and the SHA-256 of the complete
embedded `environment_identity`, which carries the observed kernel, governor,
turbo, SMT, affinity, toolchain, and numeric environment.

The same-user process inventory has exactly one two-stage algorithm. First,
freeze the numeric `/proc` PID names once and sort them by integer PID. For
every captured PID, read only the initial `/proc/[pid]/status`, persist its
complete raw bytes and SHA-256 in one ordered `pid_filter_records` entry, and
parse the effective UID. `numeric_pid_count` equals this array length. A
missing or unparsable initial status makes the inventory incomplete. If that
UID differs from the preflight effective UID, perform no stat, cmdline,
executable, or final-status read and emit no same-user process entry. If it
matches, read and persist in exactly this order: initial stat, initial cmdline,
initial executable-link target, final cmdline, final executable-link target,
final stat, final status. Any failed read or parse, initial/final cmdline or
executable-target inequality, a captured/filter/initial-stat/final-stat/
final-status PID disagreement, an initial/final-status effective-UID
disagreement, or an initial/final-stat start-time disagreement makes the
inventory incomplete. Reading the later files for another UID, silently
skipping an unreadable initial status, or filtering a same-UID process by CPU
ticks is forbidden.

Persist every stable same-UID process, including zero-tick processes and the
preflight process; exactly one entry must match the top-level preflight
identity. Each entry points to its unique same-UID PID-filter-record index and
contains PID, start-time clock ticks, process state, separate and summed
user/system clock ticks, and lossless lowercase byte-hex preimages for `comm`,
initial/final executable-link targets, and initial/final raw
`/proc/[pid]/cmdline`. Complete initial stat, final stat, and final status bytes
and every stat/status/cmdline SHA-256 are also persisted. Initial/final
cmdline and executable-target bytes must be equal. This avoids locale or
non-UTF-8 ambiguity. From each status, parse
the unique ASCII-decimal `Pid:` field and use the second of the four
ASCII-decimal `Uid:` fields. From each stat, take `comm`
between the first opening parenthesis after the PID and the rightmost closing
parenthesis followed by space, one ASCII state letter, and space; then parse
documented fields 1, 3, 14, 15, and 22 as PID, state, `utime`, `stime`, and
start time. Any missing, ambiguous, nondecimal, or inconsistent field makes
the inventory incomplete. The filter-record PIDs are strictly increasing; the
same-user array is ordered by `(pid,start_time_clock_ticks)`. Its count equals
both `same_user_process_count` and the number of true same-UID filter records;
each total, including zero, must equal the two CPU tick fields.

Conflict classification is byte-deterministic. Decode the equal
`final_cmdline_hex`; a nonempty value must contain NUL-separated argv fields
and exactly one terminal NUL. Split on NUL and remove only the terminal empty
field. For the equal final executable-link target and every nonempty argv
field, basename means the bytes
strictly after the last `0x2f`, or the whole byte field when no slash occurs.
There is no character decoding, case folding, dot/dot-dot normalization,
symlink resolution, substring, prefix, or regular-expression match. The exact
ASCII basename marker set, in UTF-8 byte order, is:

```text
a4_1s_native
a4_1s_runner.py
a4_v2_archive.py
a4_v2_native
a4_v2_runner.py
a4_v2_verifier.py
evaluate_arbitrary_cardinality.py
run_arbitrary_cardinality_a4_1s.py
run_arbitrary_cardinality_a4_v2.py
run_saq_cost_projection.py
saq_cost_projection
saq_cost_projection.py
```

Every future `A4-V2-I` executable or direct script invocation capable of
supervising, producing, verifying, or archiving must expose at least one of
those exact basenames. The prelaunch snapshot runs inside the outermost such
process; its parent and ancestors must expose none. `A4-V2-PAR` must commit and
independently review the exact invocation identities before any synthetic-run
authorization, so an implementation cannot evade the matcher by renaming a
runner after this protocol.

Each entry persists the unique exact matches in that order. Only the exact
entry matching the top-level preflight `(PID,start_time_clock_ticks)` is
allowlisted, as `ALLOW_PREFLIGHT_SELF`; there is no parent, ancestor, sibling,
shell, executable, UID, or name allowlist. After inventory completeness is
checked, compute every marker match before applying the self exception. A
nonself entry with any marker is `PRECONDITION_NOT_MET`; a nonself entry with
no marker is `ALLOW_NO_MARKER`. An incomplete inventory, failed
environment/memory/disk check, or conflict starts no scientific observation,
and no schema-valid launched producer manifest may claim otherwise. For a
launched observation, all pass flags and inventory completeness are `true`,
every conflict flag is `false`, and the independent verifier recomputes the
thresholds, ordering, arithmetic, cmdline hashes, environment binding, exact
marker matches, self identity, and classification from the recorded byte
preimages.

### 5.3 Memory, bytes, and operational ceilings

Report peak RSS for the instrument producer and each separately launched build,
parity, evidence, verifier, and archive process family. If the operating
system exposes only a cumulative producer peak, do not invent peaks for
its three subphases. Report that shared peak explicitly.

For every phase report created temporary bytes, maximum simultaneously live
owned temporary bytes, permanent intermediate-bundle bytes, research
evidence bytes, and deleted partial bytes. Existing repository and runtime
library files are environment inputs, not zero-cost output. No byte may be
charged to two output classes.

`resource_ledger.json.phase_byte_ledger` has exactly eight aggregate entries
in metered phase order (`B_build`, `P_parity`, `C_setup`, `C_core`,
`C_bundle_io`, `E_emit`, `V_replay`, `E_archive_body`). Each entry contains
exactly those five byte fields summed or peaked across that phase's attempts.
An unstarted phase has zero in all five byte fields.
The global byte ledger reconciles phase-created, permanent, evidence, and
deleted-byte totals without summing per-phase peaks. `F_trailer` bytes are not
assigned to a metered phase: `artifact_index.json` records the first two
wrapper sizes, while the clean reviewed Git blob supplies the index's own
size. Independent review reports their sum from those three finite identities;
no wrapper embeds a recursive total of itself.

The frozen operational ceilings are:

```text
each of B_build, P_parity, E_emit, V_replay, E_archive_body:
    CPU                         86,400,000,000 us (24 CPU-hours)
    wall                        172,800,000,000,000 ns (48 hours)

each producer attempt spanning C_setup/C_core/C_bundle_io:
    CPU                         86,400,000,000 us (24 CPU-hours)
    wall                        172,800,000,000,000 ns (48 hours)

T_study_metered CPU            518,400,000,000 us (144 CPU-hours)
producer or verifier peak RSS  25,769,803,776 bytes (24 GiB)
owned live temporary bytes     17,179,869,184 bytes (16 GiB)
intermediate bundle bytes         268,435,456 bytes (256 MiB)
research evidence/archive       4,294,967,296 bytes (4 GiB)
```

The per-process memory ceiling leaves more than 7 GB of the pinned machine's
33,047,748,608 physical bytes outside the instrument. The temporary ceiling is
well below the pinned output filesystem's pre-run free capacity, and the
bundle/evidence ceilings are conservative multiples of the byte-complete A4
reference payload and compact schema. The same inherited 24 CPU-hour
operational limit is used for each named nonprimary phase and each producer
attempt. The 144-hour metered-study cap is a separate global stop and may bind
before the sum of individually permitted restarted attempts. These are
termination safeguards, not method thresholds.

Crossing an operational CPU, wall, RSS, temporary, bundle, evidence, or study
ceiling aborts the current unpublished unit or staging directory; it does not
wait for that unit to become scientific evidence. Only the prior complete
atomic prefix remains, and the status is `RESOURCE_INCOMPLETE_NO_DECISION`.
It cannot become a pass or scientific no-go. `F_trailer` may still emit the
finite incomplete-status wrappers if its inputs are intact. If it cannot, the
causal classification remains resource-incomplete under precedence, but no
authority-bearing terminal artifact exists; partial wrappers are not evidence.

## 6. Comparative intermediate bundle and primary I/O

The equivalence target is the A4 panel decoder and ADC-table reference frozen
at pre-outcome commit
`3aa2f6e219763cfe72218050e420766a5a0efbcb`, before cost result
`9ce1052`. It is not current SAQ. The bundle must reconstruct every registered
A4 model, label, binary32 centroid, invalid address, packed byte, and reference
lookup value without consulting research evidence.

`C_bundle_io` must materialize exactly these files, in this order, from the
completed in-memory construction:

```text
bundle/models.json
bundle/codes_b04.bin
bundle/codes_b08.bin
bundle/representation_manifest.json
```

All JSON in the intermediate bundle is UTF-8 canonical JSON with keys recursively
sorted, comma and colon separators without spaces, no floating JSON numbers,
and exactly one terminal LF. Binary32 and binary64 bit patterns use fixed-width
lowercase hex strings of 8 and 16 characters without a `0x` prefix.

`models.json` has exactly this logical schema:

```text
{
  artifact_kind: "a4_comparative_models",
  schema_version: 1,
  protocol_version: string,
  rates: [rate_model(B4), rate_model(B8)]
}

rate_model = {
  word_bits, capacity, payload_bytes,
  groups: [group_model(group_id=0), ..., group_model(group_id=63)],
  global_dyadic_pack_cap8: {
    bit_widths[128], cardinalities[128],
    centroids_binary32_bits[128][]
  }
}

group_model = {
  group_id, coordinates[2],
  dyadic_word: product_model,
  arbitrary_word: product_model,
  trained_block_vq: {
    selected_start_id, center_count,
    centers_binary32_bits[center_count][2]
  }
}

product_model = {
  requested_cardinalities[2], effective_cardinalities[2],
  used_states, invalid_states,
  centroids_binary32_bits[2][]
}
```

Every array length is implied by its cardinality field and is validated before
publication. A zero-bit global coordinate has cardinality one and retains its
single fixed centroid.

Code files have no header. They are arm-major in exactly this order:

```text
dyadic_word
arbitrary_word
trained_block_vq
global_dyadic_pack_cap8
```

Within each arm they are vector-major for vector ids `0..8191`. Therefore
`codes_b04.bin` contains `4*8192*32 = 1,048,576` bytes and
`codes_b08.bin` contains `4*8192*64 = 2,097,152` bytes.

`representation_manifest.json`, written last, has exactly the keys
`artifact_kind`, `schema_version`, `protocol_version`, `input`, `arm_order`,
`models`, and `code_files`. `input` records raw hash, dtype, shape, and order.
`models` records path, schema version, size, and SHA-256. Each B4/B8 code-file
entry records path, word bits, vector count, payload bytes, layout, arm order,
size, and SHA-256. Producer source, build, environment, and research evidence
belong to `producer_manifest.json`, not the intermediate bundle.

Binary64 block-training trajectories and exact objectives are evidence unless
they are needed by the intermediate decoder.

The normative decoder is:

- for either product arm, unpack group word `u`, reject `u >= K1*K2`, set
  `z1=u mod K1` and `z2=floor(u/K1)`, then read both binary32 centroids in
  label order;
- for block VQ, use `u` directly as the selected binary32 center row;
- for the global control, consume each registered `b_j`-bit label LSB-first at
  its cumulative bit offset and read that coordinate's centroid;
- B4 consumes an even group from the low nibble and the following odd group
  from the high nibble; B8 consumes one byte per group; and
- a two-coordinate reference ADC table has `capacity` binary32 entries,
  computes each valid squared distance in the registered binary64 operation
  order followed by one binary32 narrowing, and stores `7f800000` for every
  invalid product address.

Every encoded label must be valid, unpack to the original label, and recreate
the producer's centroid bits. These rules define A4-reference equivalence;
only the paid 32/64-byte size happens to coincide with some SAQ payload sizes.

All four files are written under one new sibling staging directory on the
destination filesystem. Write and validate the three children first, write
the manifest last, `fsync` every file and the staging directory, atomically
rename the whole directory to `bundle/`, and `fsync` the parent directory. No child is
published independently. All of that work belongs to `C_bundle_io`. V2
deliberately does not call this bundle a
retained or deployable SAQ representation. Official SAQ source persists a
different CAQ code/factor/metadata layout, while A4 requires learned
two-coordinate codebooks and a future new scan interface. IVF insertion, an
SAQ adapter, query lookup tables, and query execution are not authorized and
not part of the claim.

The files contain all four registered arms, not only `arbitrary_word`. Thus
`T_instrument` is the cost of the frozen comparative diagnostic workload. It
cannot be cited as the recurring construction or deployment cost of one
selected arm. Failure closes this exact instrument on resource grounds, not
the candidate's intrinsic affordability.

## 7. Compact but complete research evidence

After the instrument clock stops, the named later phases produce:

```text
evidence/scalar_optimum_records.jsonl
evidence/allocation_summary.json
evidence/block_trajectories.jsonl
evidence/encoding_summary.json
evidence/producer_manifest.json        written last by E_emit
verifier/verifier_summary.json         produced by V_replay
archive/archive_body.json              produced by E_archive_body
final/resource_ledger.json             produced by F_trailer
final/decision.json                    produced by F_trailer
final/artifact_index.json              produced last by F_trailer
```

Each of `evidence/`, `verifier/`, and `archive/` is first a same-filesystem
sibling staging directory. Its producer writes and validates all children,
fsyncs every file and the staging directory, atomically renames the whole
directory, and fsyncs the parent. A staging or partial directory is never
evidence. Every phase reads prior published directories as immutable and may
not repair or overwrite them.

All evidence JSON uses the canonical encoding in Section 6. JSON Lines files
contain one canonical object plus one LF per record and no header. Structural
schemas are frozen in
`docs/saq_a4_v2_artifact_schema_2026_07_14.json`; the machine-readable contract
maps each path to its `$defs` entry and freezes cross-record invariants. Every
listed key is required, unlisted keys are forbidden, and nullable keys remain
present. Authority-bearing durations and byte counts are JSON integers. Large
algorithmic work counters are canonical nonnegative decimal strings. No
binary floating duration or decimalized exact objective is authoritative.

At full shape, `scalar_optimum_records.jsonl` stores all
`128*256 = 32,768` complete `scalar_optimum_v2` records in coordinate-major,
then increasing-`K` order. An early-stop artifact stores exactly 256 records
for every completed scalar-coordinate unit and no partial next coordinate.
There is no digest-only substitute. Each record includes `fit_row_count=8192`,
distinct-support size, reduced exact SSE, the complete recursively tie-broken
partition, exact means, direct binary32/binary64 centroid bits, comparison/tie
counts, and the strict-binary32-alphabet result. It contains no self hash.
The file-level hash binds its exact bytes.

Every rational pair is reduced with positive denominator. Zero is exactly
numerator `"0"`, denominator `"1"`; signs and leading zeroes are canonical.
Partition endpoints index the aggregated strictly increasing support, use
nonempty half-open intervals, are contiguous, and cover that support exactly.
Partition, exact-mean, binary32, and binary64 arrays each have
`effective_cardinality` entries in label order.

`allocation_summary.json` is one `allocation_summary_v2` object. At full
shape its `group_records` array has exactly 128 records ordered B4 groups
`0..63`, then B8 groups `0..63`; its `global_records` array is B4 then B8.
An early-stop object contains the exact completed prefix of those arrays.
Requested and
effective cardinalities, used/invalid states, exact fitting SSE, and canonical
candidate/transition counts are complete rather than summarized by a digest.

At full shape, `block_trajectories.jsonl` has exactly 1,152 lines: for each B4
group `0..63` and then B8 group `0..63`, one `block_metadata_v2` followed by
eight `block_start_v2` records in start order. An early-stop file ends only
after one such complete nine-record group. Metadata binds coordinates, row-order
identity, arbitrary initialization, and the selected winner. Every start
persists initialization rows, all prefill fields, initial centers, every
accepted step, all 8,192 final assignments, final binary64/binary32 centers,
final SSE, work/tie counts, and all control flags. The three prefill fields are
nonnull together only for start 0 and are explicit nulls for starts 1--7.
Step arrays have `iteration_count=accepted_update_count=length(steps)` and
iterations `1..n`; every group has exactly one selected start matching its
metadata.

Step and final-assignment hashes have a frozen preimage: exactly 8,192 labels
as unsigned little-endian 16-bit integers with no header or trailer. A
step-center or prefill-center hash covers the canonical JSON array of binary64
bit-string pairs with no LF. The row-order hash covers exactly 8,192 unsigned
little-endian 32-bit vector ids with no header or trailer. A record/file hash
never appears inside its own preimage. The independent verifier regenerates
every preimage; hashes only localize disagreement.

At full shape, `encoding_summary.json` is one `encoding_summary_v2` object
containing exactly eight `encoding_arm_summary_v2` entries: B4 arms in
registered order, then B8 arms. An early-stop object has the exact completed
entry prefix. Each freezes the code-file subrange, raw-byte SHA-256, vector/label/
payload counts, work counts, and all-vector round-trip result. Each entry also
persists that complete subrange once as lowercase `payload_hex`; its length is
exactly twice `file_byte_length`. This is the verifier's preimage when an early
stop occurs before bundle publication. At full shape it deliberately duplicates
the bundle subrange in research evidence; its separately metered cost may not
be moved into or out of `T_instrument` after seeing a result.
For arm index `a=0..3`, `file_byte_offset=a*8192*payload_bytes_per_vector`
and `file_byte_length=8192*payload_bytes_per_vector`; subranges are contiguous
with no header, gap, or trailer. `alignment_bytes=1` and
`output_bytes=file_byte_length`.

All four producer evidence siblings exist even for an empty class and are
bound by counts in `producer_manifest.json`; an empty JSONL is zero bytes and
an empty summary uses its schema-frozen object with an empty record array.
`producer_manifest.json` binds protocol/schema/source/binary/command/
environment/input identities, phase receipts, and the four producer-evidence
siblings; it is written last in the atomically published evidence directory.
It persists the complete prelaunch observation, complete argv, frozen observed
environment fields, input generator/order/hash fields, clean execution commit,
and document/file identities rather than hashes without preimages.
`argv_sha256` hashes the canonical argv array without LF.
`environment_sha256` and `input_identity_sha256` hash their canonical objects
with only the respective hash field omitted and no LF. Each prelaunch process
entry likewise persists both lossless raw cmdline byte strings before their
hashes and requires them to match.
`source_tree_sha256` hashes the canonical path/size/SHA-256 array for every
implementation source named by the reviewed build manifest; Git supplies the
same clean-tree preimage.
Its receipts stop at closed `T_instrument` phases and it records an `E_emit`
start checkpoint, never its own terminal resource values. `verifier_summary.json`
contains expected/observed decision counts, explicit independence attestations,
the discrepancy inventory, and a `V_replay` start checkpoint, never its own
terminal resource values. The supervisor-captured terminal `E_emit` and
`V_replay` receipts first appear in `archive_body.json` and later wrappers.
`archive_body.json`, `resource_ledger.json`, `decision.json`, and
`artifact_index.json` obey the finite ownership and hash DAG in Section 5.2.

The following predecessor redundancies are omitted:

- complete DP predecessor rows for every layer;
- a second producer copy of independently replayed values;
- repeated manifest fragments; and
- repeated arrays alongside both subarray and file hashes.

This changes evidence representation, not scientific computation. Every
optimum and block-start record is persisted once; every omitted internal state
needed by the claim is deterministically reconstructed by the verifier.
Canonical JSON is the only evidence encoding; no compressed or custom binary
evidence format is introduced.

## 8. Independent full replay

`V_replay` is a separately launched implementation. It may share the frozen
input and normative schemas, but not the producer's optimized solver,
allocation logic, tie logic, rational-to-float conversion, block trainer,
packer, logical-record encoder, parser core, or self-replay code. Its claim is
independent exact-rational scalar/allocation recomputation plus deterministic
bit-level block, encoding, and packing replay; block training is not described
as a mathematically exact optimizer.

It first validates the complete historical prelaunch observation against the
embedded environment identity, memory/disk thresholds, process count/order and
CPU arithmetic, raw-cmdline hashes, and conflict classifications. It does not
pretend to reproduce past system load from a later snapshot.

It must recompute:

1. every produced coordinate/`K` exact objective and registered optimum
   record;
2. every group and global allocation;
3. every produced block group/rate and all eight starts through every complete
   step;
4. every selected binary64/binary32 model;
5. every label, mixed-radix address, packed payload, and round-trip; and
6. every produced model/code file's logical contents and bytes.

It compares the full result, not a sample. SHA-256 binds preimages and
localizes changes but is not the correctness proof. A producer self-replay,
matching hashes without independent preimage generation, or sampled replay is
insufficient. The mismatch inventory must be empty.

For a completed construction, replay covers the full registered shape. For an
early cost stop, it covers every fully published atomic unit in the exact
producer prefix. A verifier mismatch or incomplete replay is
`VERIFICATION_INVALID` when a complete, schema-valid published verifier summary
records that condition; a missing or partial verifier-summary publication is
the higher-priority evidence-publication case in Section 12. No pass or cost
no-go may be reported in either case.

## 9. Primary gate and internal cap

The only primary inequality is:

```text
PASS iff T_instrument_cpu_microseconds <= 34_560_000_000.
```

The number is retained from the predecessor's preregistered algebra solely to
avoid selecting a more favorable cap after its narrow miss. V2 does **not**
carry forward the old `5/2` projection: under the new FOM there is no measured
or modeled mapping from one synthetic panel to GIST, CIFAR, two datasets, a
full vector, a current-SAQ index build, or production deployment. The cap is
not a SAQ-paper constant and does not establish expected runtime.

`B_build`, `P_parity`, `E_emit`, `V_replay`, and `E_archive_body` do not enter
the primary inequality because they validate or archive the comparative
instrument. They all enter `T_study_metered`, must stay within their operational
ceilings, and must complete before a scientific decision is admissible. Their
separation cannot support an end-to-end artifact-cost or SAQ index-build claim.

## 10. Atomic order and early stopping

The 396 construction units are fixed:

```text
U000          complete setup
U001..U128    one scalar coordinate, all K=1..256
U129..U256    one rate/group allocation, dyadic plus arbitrary
U257..U258    one rate's global allocation
U259..U386    one rate/group block unit, all eight starts plus winner
U387..U394    one rate/arm full encode, pack, and round-trip
U395          whole four-file intermediate-bundle directory publication
```

Rates are B4 then B8 and groups/arms use their registered order. A block start
is never an atomic scientific prefix because all eight starts and the winner
form one control. Intermediate files are never separate units because only
the atomically published directory is A4-reference-equivalent. Operational
resource checks may abort a staging write, but that yields
`RESOURCE_INCOMPLETE_NO_DECISION`, not a cost no-go.

After every complete unit, wait for all children, capture cumulative integer
process-family CPU, and freeze the unit identity/counts and any higher-priority
status. If logical-run `T_instrument` is strictly greater than
`34_560_000_000`, do not start the next unit. Discard any unpublished staging
unit and run `E_emit`, `V_replay`, `E_archive_body`, and `F_trailer` over the
exact complete prefix. A candidate cost no-go becomes admissible only when
that evidence, replay, archive, and final directory are complete and every
higher-priority condition passes. A pass requires all 396 units.

One long-lived supervisor owns one `logical_run_id` and directly launches and
reaps every child. An externally killed child may be restarted at most once,
only while that supervisor remains alive, with the same clean commit, binary,
argv, environment, and a new empty attempt staging directory. It restarts from
unit 0; no partial scientific state or untracked file is reused. CPU from all
attempts--including repeated setup, completed work, and the interrupted tail--
is added to the logical-run phase and primary totals. An unattributable killed
tail is reported as `C_interrupted_tail` but remains inside `T_instrument`.

A second interruption, supervisor or host loss, unreaped child, changed
identity, or missing cumulative receipt is `RESOURCE_INCOMPLETE_NO_DECISION`
and cannot resume under this protocol. Evidence, verifier, and archive phases
use the same one-restart/cumulative-CPU rule under their own operational
ceilings. Crossing the primary cap during an interruption is not a scientific
no-go unless a complete registered prefix remains available and is fully
encoded and independently verified. There is no cross-host checkpoint or
best-of-retries path.

## 11. Parity before any cost run

A future `A4-V2-I` implementation authorization would authorize source and
documentation changes only. It would not authorize a build, parity execution,
RNG, or the cost run. A later, separately explicit `A4-V2-PAR` authorization
would permit the frozen build and parity commands only. Those commands must
run the predecessor's exact-scalar exhaustive suite, 256-case scalar suite,
exhaustive allocation comparisons, rounding/packing/lookup fixtures, block
semantic microfixtures, and 64-case block suite. Their authoritative
definitions are in
`docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md` at
the preserved predecessor head `f1b464b`.

The V2 parity artifacts must be independently reviewed and committed. They
must demonstrate the same decision semantics, not merely output from the same
producer twice. Any implementation correction invalidates parity and returns
to a new clean implementation commit. Parity CPU, wall, RSS, and bytes are
`P_parity`, never silently omitted. Only after that parity bundle is committed
and independently reviewed may the user separately authorize `A4-V2-SRUN`,
which permits exactly one logical synthetic admission event. None of the three
authorizations permits real-data access.

## 12. Status precedence

`NOT_AUTHORIZED` and `PRECONDITION_NOT_MET` are prelaunch states; they do not
start a scientific observation. After launch, final interpretation uses this
precedence:

| Order | Condition | Status |
| ---: | --- | --- |
| 1 | Forbidden input, dirty execution, identity, schema, or artifact-boundary failure | `ARTIFACT_INVALID` |
| 2 | Toolchain, numeric, exactness, parity, timer, or resource-ledger failure | `IMPLEMENTATION_INVALID` |
| 3 | Block convergence, monotonicity, dominance, best-start, or packing/round-trip control failure | `CONTROL_INVALID` |
| 4 | Registered operational ceiling, attempt/supervisor loss, or construction/bundle publication incompleteness | `RESOURCE_INCOMPLETE_NO_DECISION` |
| 5 | Producer-evidence, verifier-summary, archive, or final-trailer publication is missing/partial without an order-4 resource trigger | `EVIDENCE_INCOMPLETE_NO_DECISION` |
| 6 | Independent full replay is incomplete or mismatches | `VERIFICATION_INVALID` |
| 7 | Verified selected scalar alphabet collapses or is unreachable in binary32 | `NO_GO_REPRESENTATION` |
| 8 | Verified complete unit prefix has `T_instrument > 34,560,000,000 us` | `NO_GO_SYNTHETIC_INSTRUMENT_COST` |
| 9 | Full 396 units, primary inequality, evidence, replay, and archive all pass | `PASS_SYNTHETIC_INSTRUMENT_GATE_ONLY` |

The selected block codebook's distinct-center rule remains a block control and
therefore order 3. Orders 1--6 are instrument/admissibility failures, not
scientific evidence, and always override a representation or cost outcome.
No producer source, binary, timer, schema, or phase ownership may be repaired
after the cost event and retain that event. A defect stops the stage; any fix
requires a new clean implementation commit, new downstream evidence, another
independent review, and explicit user authorization for the affected stage.
Orders 7 and 8 close this V2 formulation and permit no threshold, shape,
machine, library, algorithm, precision, or evidence-boundary rescue.

A scientific no-go exists only after the exact prefix is encoded, independently
replayed with an empty discrepancy list, archived within operational ceilings,
and the three-file final directory is atomically published. Before that point
it is `PENDING_ADMISSIBILITY`. A produced decision is not terminal evidence
until the whole bundle is committed and independently reviewed; staging,
untracked files, and a decision without its artifact index are never evidence.

## 13. Commit and authorization sequence

The three future stages are separate and non-transitive:

1. `A4-V2-I`: implement producer, independent verifier, schemas, timers, and
   ledgers; commit and independently review source. No build or execution.
2. `A4-V2-PAR`: from that clean reviewed commit, build and run only the frozen
   parity inventory; commit and independently review parity and phase
   ownership. No full-panel admission run.
3. `A4-V2-SRUN`: from the clean reviewed parity commit, run one logical
   synthetic admission event; commit and independently review the complete
   evidence/cost bundle; then perform Meeting Summary Handoff.

Each stage requires a new explicit user instruction naming that stage. An
authorization for one never implies the next. Nothing in this sequence is
currently authorized, and none permits benchmark/base/query/index reads or an
SAQ modification.

## 14. Decision after V2

`PASS_SYNTHETIC_INSTRUMENT_GATE_ONLY` permits only asking whether to write a
new base-only preregistration. It does not revive or run the old A4-1P
protocol, read base data, or inspect queries.

`NO_GO_REPRESENTATION` or `NO_GO_SYNTHETIC_INSTRUMENT_COST` preserves the
evidence and closes V2. An artifact, implementation, evidence, or verification
failure stops with no scientific decision. It may be repaired only after an
independent review identifies the defect and the user separately authorizes
the affected stage; it is never converted into a scientific result.

The present milestone ends at
`PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION`.

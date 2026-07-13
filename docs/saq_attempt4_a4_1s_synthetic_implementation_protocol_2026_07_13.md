# Attempt 4 A4-1S Synthetic Implementation Protocol

Date frozen: 2026-07-13

Stage: A4-1S

Status: **FROZEN_AUTHORIZED_NOT_IMPLEMENTED**

Protocol version: `saq-attempt4-a4-1s-20260713-schema1`

Artifact schema version: `1`

Authorization: the user explicitly authorized synthetic-only implementation,
parity review, and the full-shape synthetic cost projection on 2026-07-13.

Parent preregistration checkpoint: `3aa2f6e219763cfe72218050e420766a5a0efbcb`

## 1. Purpose, authority, and boundary

This document freezes the implementation-facing interpretation of the A4-1
base-only preregistration before an A4-1S runner is committed or a synthetic
random fixture is created. It resolves only mechanical ambiguities needed to
construct and review the registered instrument. It does not change the
scientific datasets, groups, rates, arms, objective, thresholds, or later
base-data decision rule.

The authoritative scientific contracts remain:

- `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`;
- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`; and
- `docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json`.

If this implementation protocol conflicts with one of those contracts, the
parent contract wins and A4-1S stops as `IMPLEMENTATION_INVALID` until a dated,
pre-outcome amendment is authorized. The `synthetic_runner_implementation_authorized`
field remains `false` in the frozen input contract because it records the
state at preregistration time. It must not be rewritten post hoc. This document
and the explicit user instruction are the later, narrower authorization.

A4-1S may:

- implement a branch-local native exact scalar solver and synthetic-only
  orchestration code;
- implement deterministic scalar, allocation, rounding, packing, lookup, and
  block-VQ correctness fixtures;
- run the frozen A4-0 tests and the frozen A4-1S synthetic parity suites;
- run the one-panel `8192 x 128` synthetic cost projection; and
- commit implementation, parity evidence, manifests, timing, and reviews.

A4-1S may not:

- implement or exercise a natural-data adapter;
- open any base, centroid, cluster-id, query, ground-truth, index, PCA,
  variance, prior-result, `data/`, or `results/` artifact;
- run the planned A4-1 atomic base command;
- modify SAQ/CAQ, an index format, estimator, scan kernel, or SIMD layout;
- inspect benchmark queries or claim ANN, recall, QPS, or SAQ-specific
  evidence; or
- authorize the first real-base read automatically after a synthetic pass.

No random generator is executed while this document is written. Random
fixtures may first be materialized from a clean implementation commit under
the commands and order in Sections 8 and 9.

## 2. Frozen implementation modules

The implementation must keep the following modules separable in code and in
the evidence manifest. A Python process may orchestrate them, but the exact
scalar solver must be compiled native code.

### 2.1 Authorization and synthetic read guard

The A4-1S entry point has only `parity` and `cost-projection` modes. Neither
mode accepts a dataset root, data filename, row count, dimension, group, rate,
cardinality, seed, restart count, iteration limit, threshold, or exclusion
override. It may read the two frozen JSON contracts, repository source and
build metadata, and its own declared output directory.

After parity evidence and its review are committed, `cost-projection` may also
read exactly the committed A4-1S build manifest, parity artifacts, parity
artifact index, and implementation/parity review named in Section 5. These
are instrument-validation evidence, not a prior scientific A4 result. Their
identities are bound as follows: entries in `parity_artifact_index.json` bind
the five non-index JSON artifacts--the build manifest and four parity
artifacts; the index itself is bound by its Git blob at the clean
reviewed-parity commit; and the Markdown review memo is independently bound by
its Git blob at that same commit. The review memo has no artifact schema or
producer entry. No other result or artifact becomes readable through this
exception.

The runner records all contract inputs and generated output paths. It must
reject any attempted open of a path beneath a repository `data/` or `results/`
directory, either real-data root recorded in the parent preregistration, or a
file with a registered scientific-artifact role. Such an attempted open is
`ARTIFACT_INVALID` even if no bytes are successfully read.

### 2.2 Native numeric and exact-arithmetic layer

The native path must use GCC 11.5.0 and exactly the numerical flags frozen in
the parent protocol:

```text
-O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
```

It must not add `-march=native`, fast-math, or fused multiply-add. At process
start and end it verifies `FE_TONEAREST`; on x86-64 it clears and verifies the
MXCSR flush-to-zero and denormals-are-zero bits. The manifest records compiler
identity, complete command and flags, CPU model, exact integer/rational
library and version, NumPy version, thread environment, rounding mode, and
MXCSR. GCC 11.5.0 is an exact identity, not a minimum version. An unavailable
or mismatched toolchain stops before parity as `IMPLEMENTATION_INVALID`.

The complete compiler commands are read from
`build/a4_1s/compile_commands.json` for exactly these seven target translation
units:

```text
a4_1s_native.cpp
block_cli.cpp
block_vq.cpp
exact_quantizer.cpp
numeric_runtime.cpp
representation.cpp
representation_cli.cpp
```

Sort entries by repository-relative source path, store each raw `command`
string, and tokenize it with Python `shlex.split(..., posix=True)` into the
recorded argv array. Absence of one of the seven entries, an extra target
translation unit, or absence of a raw `command` field is
`IMPLEMENTATION_INVALID`; do not silently substitute a generator-specific
representation. Every one of the seven argv arrays must contain all mandatory
flags and no forbidden flag. The runtime helper's compiled-in `compile_flags`
field records only the frozen numerical subset; it may not be reported as a
complete command. Source and binary hashes bind the manifest to these entries.

The layer must implement direct, correctly rounded, ties-to-even conversion
from the registered exact rational means to binary32 and independently to
binary64. Conversion through an intermediate floating type is forbidden.
Scientific binary32 and binary64 values in parity artifacts are serialized as
their IEEE-754 bit patterns, not as authority-bearing decimal strings.

### 2.3 Exact scalar curves

For finite binary32 input values, canonicalize either signed zero to `+0.0`,
decode every value as exact `n*2^-149`, aggregate equal `n` values using
positive integer weights, and sort by exact numeric value with lowest source
vector id as the support-point provenance tie.

For interval statistics use exact integers

```text
W = sum w_i
A = sum w_i n_i
C = sum w_i n_i^2
SSE = ((W C - A^2) / W) * 2^-298.
```

The solver must be a native exact Monge/SMAWK, divide-and-conquer, or
equivalent accelerated dynamic program. Every objective comparison uses exact
reduced rationals and arbitrary-precision cross multiplication. Ordinary
floating-point values may not choose a partition or allocation. An exact tie
chooses the earliest predecessor.

The registered implementation uses the complete totally monotone matrix from
Grønlund et al., [*Fast Exact k-Means, k-Medians and Bregman Divergence
Clustering in 1D*](https://arxiv.org/pdf/1701.07204) (Section 2.2). For DP
layer `i`, prefix endpoint `m`, and candidate last-cluster start `j`, define

```text
C_i[m,j] = D_{i-1}[min(j-1,m)] + (j<=m ? CC(j,m) : 0).
```

Thus `j>m` is an empty final cluster rather than an invalid `+infinity` cell.
Classic leftmost-minimum SMAWK runs on this complete matrix. The weighted
squared-error cost retains the cited Monge property. Replacing the upper
triangle by positive infinity and applying ordinary rectangular SMAWK is
forbidden because that padding is not the reviewed total-monotonicity
construction.

The curve has at-most-`K` semantics. For `K<=H_distinct`, an objective tie
chooses more nonempty intervals and then recursively applies the earliest
predecessor rule. For `K>H_distinct`, copy the `H_distinct` solution and record
that effective cardinality. Every `K` stores its exact objective as decimal
integer numerator and denominator strings plus
`binary_grid_exponent=-298`, its partition, exact interval means, comparison
and tie counts, and its nondecreasing-predecessor diagnostic. An independent
exact-rational replay must match.

The selected exact means are rounded directly to binary64 for block-VQ start
0 and separately to binary32 for runtime-facing representations. A selected
alphabet must remain strictly increasing in binary32. The intentionally small
correctness fixtures may exercise collision detection without turning the
fixture itself into a scientific result. A collision or unreachable nominal
alphabet selected by the full-shape cost projection is
`NO_GO_REPRESENTATION`.

### 2.4 Exact allocations

For every two-coordinate group and capacity `S in {16,256}`, solve both the
dyadic and arbitrary product allocations using exact scalar fitting SSE.
Candidate ties choose larger used-state product and then lexicographically
smaller `(K_1,K_2)`. The arbitrary address is
`u=z_1+K_1*z_2`; addresses from `K_1*K_2` through `S-1` are invalid but still
pay for the fixed word and expanded table.

The global attribution control uses all 128 coordinates, `b_j in [0,8]`, and
`sum b_j<=64*B_g`. It compares exact rational fitting SSE, then chooses more
paid bits, then the lexicographically smaller bit vector in selected-coordinate
order. The global control is included in the full-shape cost projection but
cannot determine its passage.

### 2.5 Packing and lookup reference

At `B_g=4`, even group ids occupy the low nibble and odd group ids the high
nibble. At `B_g=8`, one byte stores one group. Both produce exactly 32 or 64
bytes for 64 groups. The global control packs its 128 scalar labels in
selected-coordinate order, label least-significant bit first, with stream bit
`t` at byte `floor(t/8)`, bit `t mod 8`, and zero high-tail padding to the same
paid payload.

Nearest-centroid assignment promotes serialized binary32 values to binary64
and chooses the lower label on an exact binary64 distance tie. A matched-word
lookup computes coordinate-0 square, coordinate-1 square, adds in that order,
and narrows once to binary32. Invalid product entries are the exact binary32
positive-infinity bit pattern. The global scalar lookup performs one promoted
subtract and square and then one binary32 narrowing.

The parent gate's phrase “binary32 and binary64 lookup values” is resolved as
two parity layers: the independent reference must match the binary64
pre-narrow arithmetic value bit for bit and then match the stored binary32
value bit for bit. This does not create an additional stored binary64 table.

### 2.6 Deterministic trained block VQ

The block trainer follows all eight starts and the 300-complete-iteration cap
in the parent protocol. The following implementation details are frozen:

- start-0 farthest fill and starts 1--7 use the declared binary64 squared-L2
  arithmetic and the current codebook;
- every candidate row is considered in registered fitting-row order;
- a farthest-distance tie chooses lower vector id, then lower
  `(cell_id, selection_digest_bytes, vector_id)` if a fixture ever reuses a
  vector id;
- the “prior SSE” for a complete Lloyd step is the direct sequential replay
  SSE of the codebook before that step;
- step-1 assignments are compared with the step-3 reassignment from the same
  complete step; equality is the registered `assignments unchanged` stopping
  condition;
- sums, counts, and direct SSE follow the registered row and coordinate order;
- empty centers retain their exact prior binary64 bits;
- any nonfinite value or candidate SSE larger than prior SSE is
  `CONTROL_INVALID`; there is no tolerance or rejected-update recovery; and
- best-of-eight compares final direct-replay binary64 SSE, then start id.

The product initialization is checked before farthest fill. Every accepted
fill or Lloyd result must preserve the declared Cartesian-dominance invariant.
After selecting the winning start, all `S` binary32 centers must be distinct.

## 3. Frozen correctness fixtures

All expected answers are computed by implementations independent of the
optimized path. Passing a self-replay alone is insufficient.

### 3.1 Exhaustive exact-scalar tiny domain

The previously unspecified “exhaustive tiny support” is frozen as follows.
For the exact binary32 integer universe `{-2,-1,0,1,2}`, enumerate every
strictly increasing nonempty support subset of size one through four. For each
support enumerate every positive weight vector in `{1,2,3}^H`, and test every
`K=1,...,H`. This is 780 support/weight cases. For each case, enumerate all
contiguous partitions independently and compare effective cardinality,
objective, recursively tie-broken partition, and exact means.

Add the following bit-pattern cases, which are not substituted for those 780
cases:

1. binary32 `[-0,+0]` with weights `[1,1]`;
2. `[-1,-0,+0,+1]` with weights `[1,2,3,1]`;
3. `[-min_subnormal,-0,+0,+min_subnormal]` with weights `[1,1,1,1]`;
4. `[-min_normal,-max_subnormal,+max_subnormal,+min_normal]` with weights
   `[1,2,3,4]`;
5. `[-max_finite,-1,+1,+max_finite]` with unit weights;
6. `[-1,0,+1]` with unit weights to exercise an exact split tie;
7. `[0x3f800000,0x3f800001]` with unit weights; and
8. `[0x3f800001,0x3f800002]` with unit weights.

Here symbolic values are passed as raw IEEE-754 binary32 bits. Cases 7 and 8
exercise opposite ties-to-even directions at adjacent-normal midpoints.
Direct rounding also has independent rational fixtures for positive and
negative half-min-subnormal, three-half-min-subnormal, `1/3`, `-1/3`, and the
two adjacent-normal midpoints. Test the applicable result in both binary32 and
binary64; unsupported overflow repair or double rounding is a failure.

### 3.2 Frozen 256-case scalar suite

Use one and only one `Generator(PCG64(20260713))` stream. In case order
`t=0,...,255`, set input length `1+(t mod 12)`, draw that case's values with
`integers(-8,9)`, then its weights with `integers(1,6)`, and test
`K=1,...,min(8,H_distinct)`. The full inputs and independent/optimized results
are committed as canonical JSON. The existing A4-0 reference and all seven
A4-0 tests are additional compatibility checks, not exact-comparison
authority.

### 3.3 Allocation, address, packing, and lookup fixtures

Both product allocators must agree with exhaustive enumeration for every pair
of curves generated by the exhaustive integer supports at capacities 16 and
256 wherever the referenced curves exist. A bounded fixture may reuse a curve
at its maximum tested `K`; it may not interpret the fixture's deliberately
small `H` as a full-shape representation outcome.

The complete allocation-parity inventory has 2,433,600 decisions
(`780*780*2*2`) and need not be expanded as 2,433,600 JSON objects in the
committed artifact. This is a persistence clarification only; it does not
reduce the executed comparison. Freeze the decision order as capacity 16 then
256, arbitrary before dyadic within each capacity, first tiny-case id
`0..779`, then second tiny-case id `0..779`. For each decision, append

```text
canonical_json_bytes({
  capacity,
  cardinalities,
  dyadic_only,
  objective,
  used_states
}) || LF
```

where the object keys are canonically sorted and the value fields have the
same exact meanings as the allocation result. `representation_parity.json`
stores the decision count, this frozen order, and independent and optimized
SHA-256 values over exactly that byte stream; the two hashes must be equal.
Changing record fields, loop nesting, or the terminal LF changes the
authority-bearing preimage and is `IMPLEMENTATION_INVALID`.

The digest does not replace inspectable fixtures. The representation artifact
must additionally persist all 64 support-class winners in capacity,
arbitrary-before-dyadic, first-support-size, second-support-size order for
support sizes `1..4`. Each record includes both support sizes, capacity,
cardinality set, exhaustive valid-tuple count, optimized candidate-evaluation
count, exact winning objective, winning cardinalities, and used states.
Candidate counts use the explicit allowed nominal sets: all `K=1..S` for the
arbitrary arm and powers of two through `S` for the dyadic arm; the exhaustive
count is the number of ordered `(K_1,K_2)` with `K_1*K_2<=S`, while the
optimized count is the number actually evaluated by the reviewed monotonic
shortcut. These records make the digest reviewable without treating one
representative as evidence for all ordered tiny-case pairs.

Enumerate every valid tuple for registered mixed-radix examples and every
address through `S-1`; verify encode/decode, invalid positive-infinity entries,
B4/B8 packing, exact payload length, and round-trip. Exercise global bit widths
including zero, byte boundaries, and a non-byte-aligned paid-bit sum, while
always padding to the registered 32/64 bytes. Independent arithmetic must
match both lookup parity layers from Section 2.5.

Those small representation fixtures are committed explicitly, not only as
booleans or a digest. They contain inputs plus independent and optimized
outputs for: every `(z_1,z_2)` and address of the registered `(3,5)`
mixed-radix example and its invalid capacity-16 address; full B4 and B8 label,
payload-hex, payload-length, and unpacked-label round trips; global 32-byte and
64-byte payload round trips covering zero widths, a byte boundary,
non-byte-aligned used bits, and zero high-tail padding; and the complete
matched B4/B8 and global lookup fixtures. Every valid lookup entry stores its
pre-narrow binary64 bits and stored binary32 bits. Every invalid expanded-table
entry stores `valid=false` and binary32 bits `0x7f800000`. The artifact stores
both independent and optimized arrays and an exact-equality flag for each
fixture. A summary counter or pass boolean alone is insufficient parity
evidence.

### 3.4 Block semantic microfixtures and frozen 64-case suite

Before the 64 random cases, run fixed helper-level microfixtures for:

- an equidistant assignment choosing the lower codeword id;
- a farthest-point tie choosing the lower vector id;
- an empty center retaining its prior binary64 bits;
- a Cartesian start-0 codebook before fill; and
- a best-of-eight final-SSE tie choosing the lower start id.

These microfixtures validate semantics only and do not replace or alter a
start in the frozen random suite.

For the random suite, use one fresh `Generator(PCG64(20260713))` stream
dedicated to all 64 cases. In case order `t=0,...,63`, set
`N=8+(t mod 25)`, `S=2+(t mod 7)`, then draw exactly one `N x 2` array using
`integers(-8,9)`. Use the dataset, cell, vector, group, selection hash, and
start hash identities frozen in the parent protocol. Run the optimized
trainer twice and require bit-identical artifacts. An independent replay
checks assignment ties, empty-center behavior, per-step monotonicity,
Cartesian dominance, convergence of all starts, best-of-eight selection, and
binary32 distinct-center count.

## 4. Full-shape synthetic cost projection

The projection creates exactly

```text
Generator(PCG64(20260713)).standard_normal((8192,128), dtype=float32)
```

in C order. It records the NumPy version, dtype/endianness, shape, C-order raw
byte count, and SHA-256 of the generated array. It uses
`dataset_id=synthetic_cost_projection`, `cell_id=0`, `vector_id=i`, the frozen
selection and start hashes, groups `(2h,2h+1)` for `h=0,...,63`, both rates,
all scalar curves `K=1,...,256`, both product allocations, the global capped
control, all eight block starts, and the registered direct-rational rounding.

“Full registered scalar and block pipeline” is resolved to include:

1. contract and numeric preflight;
2. synthetic array generation, hashing, row digests, and registered row order;
3. all 128 exact scalar curves and their certificates;
4. all group/rate product allocations and both global allocations;
5. direct binary64/binary32 centroid serialization;
6. every registered block start through convergence or declared failure;
7. encoding all 8,192 synthetic rows for each arm and rate;
8. B4/B8/global packing and full round-trip;
9. representation byte/work accounting; and
10. canonical output serialization, ledger generation, flush, and close.

It does not invent held-out rows, base pairs, IVF-cell bootstrap samples,
query-like residuals, or table-construction timing. Those are not defined for
this synthetic matrix. Lookup arithmetic is instead certified by the parity
fixtures. Excluding these undefined later-base operations is not permission
to omit any listed fitting, allocation, block-training, encoding, packing, or
accounting work.

The gate CPU clock is the delta of
`getrusage(RUSAGE_SELF)+getrusage(RUSAGE_CHILDREN)`. The command entry file is
a bootstrap, not the scientific runner module. Its first A4-1S executable
action captures the start CPU and wall snapshots before importing the runner,
the independent reference, artifact helpers, or NumPy. It then imports the
runner and passes those integer snapshots as immutable arguments; the runner
must not replace them with a later sample. Consequently runner/reference
module import and initialization are charged to `preflight`. Only the minimal
standard-library machinery required to issue the integer `getrusage` call may
be loaded by the bootstrap before the snapshot, and it may perform no argument
parsing, Git/filesystem access, environment validation, fixture construction,
or other gate work first. Read each underlying `struct timeval` as integers and
convert it as
`tv_sec*1_000_000+tv_usec`; do not obtain the authority-bearing value by
multiplying a binary floating-point seconds value. Sum user and system time for
self and terminated children at the start and end, then subtract to obtain the
nonnegative integer `timed_region_cpu_microseconds`.
Every native child is waited to termination before its model checkpoint and
before the end snapshot, so its user and system time is present in
`RUSAGE_CHILDREN` exactly once.

The timed region includes contract/numeric preflight, NumPy import and
generation, all native children, every model, encoding, all external detail
shards, the complete detail-ledger body, its serialization, flush, and close.
The supervisor captures the end usage immediately after those timed files are
closed.

The captured end value is necessarily unavailable to a file that must already
contain and be flushed with that value. Therefore only the following small
trailer finalization is outside the gate clock: inject the captured total into
the cost manifest and summary, apply the integer timing decision, copy the
timed region's already-computed shard hashes into the detail-ledger wrapper,
write and hash those three files, then write the artifact index, and flush
those four committed JSON files. These wrappers may derive no model,
allocation, encoding, or work result; the final status may differ from the
timed body's pending status only through the frozen integer timing comparison.
Their own write/flush duration cannot be embedded without a second
self-reference, so no untimed-duration field is reported or interpreted. The
artifact index records the first three wrapper sizes and hashes and, as always,
excludes itself. This exact four-file trailer is the complete exclusion and
may not grow. It resolves the timing self-reference; it is not a discretionary
exclusion.

Record component CPU microseconds and wall nanoseconds as integers, but apply
the decision only to `timed_region_cpu_microseconds`. Store the projected cost
without floating point as

```text
projected_cpu_numerator_microseconds = 5 * timed_region_cpu_microseconds
projected_cpu_denominator = 2
base_cpu_limit_microseconds = 86_400_000_000
PASS iff 5 * timed_region_cpu_microseconds
        <= 2 * 86_400_000_000.
```

Equivalently, a complete one-panel timed region must be at most
`34_560_000_000` CPU microseconds. Decimal seconds are descriptive conversions
only and never enter the comparison.

Check cumulative integer timed-region CPU microseconds after each completed
scalar coordinate, allocation, block model, encoding arm, and output shard.
If it has exceeded `34_560_000_000`, further work cannot restore passage. The
runner may then stop at that checkpoint and return
`NO_GO_EXACT_SOLVER_COST` with `projection_complete=false` and the measured
integer CPU microseconds as a strict lower bound. This is not a reduced-shape
run: the full shape was launched, the fixed ceiling was already crossed, and
no scientific output is interpreted. A pass is valid only after every listed
operation completes.

The threshold covers the entire scalar-plus-block command despite the legacy
outcome name `NO_GO_EXACT_SOLVER_COST`. Solver, allocation, block-training,
encoding, and output components must also be reported separately. Wall time
does not replace CPU time. No approximation, alternate exact library,
reduced matrix, fewer coordinates, fewer rates, fewer starts, or reused
earlier timing may rescue an over-budget result.

## 5. Artifact schema and canonical encoding

Committed evidence lives under
`docs/saq_attempt4_a4_1s_artifacts_2026_07_13/` with these exact names:

```text
build_manifest.json
scalar_exact_parity.json
representation_parity.json
block_vq_parity.json
parity_summary.json
parity_artifact_index.json
synthetic_cost_projection_manifest.json
synthetic_cost_projection_summary.json
synthetic_cost_projection_detail_ledger.json
cost_projection_artifact_index.json
```

The two human reviews are:

```text
docs/saq_attempt4_a4_1s_implementation_parity_review_2026_07_13.md
docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md
```

Canonical JSON is UTF-8, object keys sorted lexicographically, arrays in the
registered execution order, no insignificant whitespace, one final newline,
and no JSON NaN or infinity. Exact integers that may exceed 53 bits are
decimal strings. An exact curve value is

```json
{"binary_grid_exponent":-298,"denominator":"positive_decimal","numerator":"nonnegative_decimal"}
```

Scientific floats are lowercase fixed-width hexadecimal IEEE bit strings:
eight hex digits after `0x` for binary32 and sixteen for binary64. The one
allowed invalid-LUT infinity is represented by binary32 bits `0x7f800000` and
an explicit `valid=false`; it is never emitted as a JSON numeric infinity.
Hashes are lowercase SHA-256 hexadecimal strings. Durations are integer CPU
microseconds or wall-clock nanoseconds; human decimal seconds are descriptive.

Define `canonical_json_bytes(v)` as the UTF-8 bytes produced with object keys
sorted lexicographically, separators `(',', ':')`, `ensure_ascii=False`, and
`allow_nan=False`, with no terminal LF. A JSONL record is
`canonical_json_bytes(record)` followed by one LF. For every logical array
field `x` paired with `x_sha256`, the hash preimage is exactly
`canonical_json_bytes(x)`. This rule applies even when only the hash, rather
than the full array, is persisted. A `payload_sha256` instead hashes the raw
bytes decoded from its paired lowercase `payload_hex`; file and shard hashes
cover the exact bytes on disk.

The schemas below use these aliases:

```text
id: nonnegative JSON integer
count: nonnegative decimal-integer string
sha256: 64-character lowercase hexadecimal string
bits32: string matching 0x followed by 8 lowercase hexadecimal digits
bits64: string matching 0x followed by 16 lowercase hexadecimal digits
exact_sse: {binary_grid_exponent:integer exactly -298,
            denominator:positive decimal-integer string,
            numerator:nonnegative decimal-integer string}
exact_mean: {binary_grid_exponent:integer exactly -149,
             denominator:positive decimal-integer string,
             numerator:signed decimal-integer string}
interval: {begin:id, end:id} with begin < end
```

Both rational aliases are reduced to greatest-common-divisor one; a zero
numerator has denominator `"1"`. Their separate binary-grid exponent is not
absorbed into the fraction.

For each JSONL record map and the timed-ledger map explicitly declared below,
the map lists every allowed key and no undeclared key is permitted in schema
version 1. A nullable field is present and has either its declared type or JSON
`null`; it is never omitted.

All committed top-level `.json` artifacts and the external
`timed_output_ledger_body.json` use `schema_version=1` and
`protocol_version="saq-attempt4-a4-1s-20260713-schema1"`. The common fields
have these fixed JSON types:

```text
schema_version: integer
protocol_version: string
stage: string, exactly "A4-1S"
status: string
parent_preregistration_commit: 40-character lowercase hexadecimal string
implementation_commit: 40-character lowercase hexadecimal string
execution_commit: 40-character lowercase hexadecimal string
command: array of strings containing argv without shell reconstruction
thread_environment: object from string keys to string values
input_ledger: array of {path:string, role:string, size_bytes:integer,
                        sha256:sha256}
output_ledger: array of {path:string, role:string, size_bytes:integer,
                         sha256:sha256, timed:boolean}
```

Paths are repository-relative for committed inputs and relative to the
declared empty output directory for external outputs. Ledger arrays sort by
path bytes. A generated value not yet associated with a Git commit uses the
40-zero sentinel only in an external precommit artifact; every committed
artifact must contain the actual producer commit. An artifact's embedded
`output_ledger` lists only external timed shards or direct child outputs. It
excludes the containing file and all committed peer wrappers in the same
checkpoint, avoiding self- and peer-hash cycles; the checkpoint artifact index
binds peer files from the outside. Individual JSONL records use their
record-specific schema below and do not repeat command or ledger fields.

Every artifact begins with:

```text
schema_version
protocol_version
stage
status
parent_preregistration_commit
implementation_commit
execution_commit
command
thread_environment
input_ledger
output_ledger
```

The build manifest additionally contains the complete native numeric fields
from Section 2.2 and hashes of the native binary and relevant source files.
The scalar parity artifact contains suite/RNG metadata, every input, aggregated
support, each `K`'s independent and optimized exact curve, partition, means,
effective cardinality, comparison/tie counts, and diagnostics. The
representation artifact contains the frozen ordered full-decision digest, the
explicit support-class winners and candidate counts, rounding fixtures,
addresses, full B4/B8/global payload round trips, and explicit binary64/
binary32 valid and invalid lookup entries from both parity layers. The block
artifact contains fixture identities, start hashes,
initialization, per-start/per-step SSE and assignment hashes, empty-center and
tie events, iterations, convergence, dominance, selected start, serialized
center hashes, and repeated-run equality.

The cost summary contains the array identity, all registered shape/count
checks, per-module and total CPU/wall time, projected CPU, peak RSS,
deterministic owned-buffer high water, operation counts, comparisons,
iterations, accepted updates, codebook/radix/address/payload bytes, selected
cardinalities, distinct-center checks, completion flag, and outcome. The cost
manifest repeats the runtime numeric state and records implementation, parity
evidence, parity review, and execution commits.

The authority-bearing timing fields in the cost manifest, cost summary, and
committed detail-ledger wrapper have exactly these names and JSON integer
types:

```text
timed_region_cpu_microseconds
projected_cpu_numerator_microseconds
projected_cpu_denominator, exactly 2
base_cpu_limit_microseconds, exactly 86400000000
gate_left_integer, exactly 5*timed_region_cpu_microseconds
gate_right_integer, exactly 2*base_cpu_limit_microseconds
component_cpu_microseconds: object with exactly the keys preflight,
    generation_and_order, scalar, allocation, block, encoding,
    shard_serialization, and total; values are nonnegative JSON integers
component_wall_nanoseconds: object with exactly the same keys and
    nonnegative JSON integer values
```

`gate_pass` is a JSON boolean equal to `gate_left_integer<=gate_right_integer`.
The first seven component keys form a nonoverlapping partition and sum exactly
to `total` in their respective units. No authority-bearing CPU-seconds or
floating projected-cost field is allowed.

For a completed projection, every exact curve and partition must be persisted
in the empty external output directory. A registered terminal run instead
persists the complete prefix defined in Section 5.5. Because the complete
partition detail can be large, raw detail is not committed to Git. Instead,
`synthetic_cost_projection_detail_ledger.json` commits, for every deterministic
output shard, its relative path, schema, record count, byte size, and SHA-256,
plus a SHA-256 over the canonical ordered ledger. The cost summary and timing
are committed as required by the parent protocol. Review must inspect a
deterministic sample from every shard class and independently verify all shard
hashes before real-base authorization is requested.

The external detail layout is frozen as follows:

```text
detail/scalar/coordinate_000.jsonl ... coordinate_127.jsonl
detail/allocations.jsonl
detail/block/group_000_b04.jsonl ... group_063_b04.jsonl
detail/block/group_000_b08.jsonl ... group_063_b08.jsonl
detail/encoding/rate_b04.jsonl
detail/encoding/rate_b08.jsonl
detail/timed_output_ledger_body.json
```

Only files ending in `.jsonl` are JSON Lines. Each contains one canonical
record plus LF per line. `timed_output_ledger_body.json` is one canonical
top-level JSON object with the common fields above and one final LF; it is not
JSON Lines. No gzip, compression, binary side format, or data-dependent split
is allowed.

### 5.1 Scalar JSONL record

Each scalar shard has 256 records in ascending `requested_cardinality`. Every
record has exactly this map:

```text
{
  record_type:string exactly "scalar_curve",
  coordinate_id:id,
  requested_cardinality:id in 1..256,
  effective_cardinality:id,
  fit_row_count:id exactly 8192,
  distinct_support_size:id,
  exact_sse:exact_sse,
  partition:array<interval>,
  exact_means:array<exact_mean>,
  binary32_centroid_bits:array<bits32>,
  binary32_centroid_bits_sha256:sha256,
  binary64_centroid_bits:array<bits64>,
  binary64_centroid_bits_sha256:sha256,
  predecessor_indices:array<id>,
  predecessor_indices_sha256:sha256,
  comparison_count:count,
  exact_tie_count:count,
  exact_replay_sse:exact_sse,
  exact_replay_match:boolean,
  predecessors_nondecreasing:boolean,
  serialized_binary32_strictly_increasing:boolean
}
```

The partition and mean arrays have length `effective_cardinality`, use support
indices after exact aggregation, and occur in increasing support order. The
centroid arrays use label order and have the same length. The predecessor
array is the optimized layer's complete endpoint-order predecessor row used by
the monotonicity diagnostic.

### 5.2 Block JSONL records

Each block shard has one metadata record followed by eight start records in
ascending `start_id`. The metadata record is exactly:

```text
{
  record_type:string exactly "block_metadata",
  word_bits:id restricted to 4 or 8,
  capacity:id equal to 2^word_bits,
  group_id:id in 0..63,
  coordinates:array<id> of length 2,
  fit_row_count:id exactly 8192,
  row_order_vector_ids:array<id> of length 8192,
  row_order_vector_ids_sha256:sha256,
  arbitrary_cardinalities:array<id> of length 2,
  arbitrary_used_states:id,
  selected_start_id:id
}
```

A block step is exactly:

```text
{
  iteration:id starting at 1,
  prior_sse_bits:bits64,
  candidate_sse_bits:bits64,
  assignments_before_sha256:sha256,
  assignments_after_sha256:sha256,
  centers_after_binary64_bits_sha256:sha256,
  changed_assignment_count:id,
  empty_center_ids:array<id>,
  empty_center_ids_sha256:sha256,
  accepted:boolean exactly true
}
```

The two assignment hashes use the canonical JSON bytes of the corresponding
8,192-integer label arrays. A start record is exactly:

```text
{
  record_type:string exactly "block_start",
  word_bits:id restricted to 4 or 8,
  capacity:id equal to 2^word_bits,
  group_id:id in 0..63,
  start_id:id in 0..7,
  initialization_kind:string restricted to "cartesian_fill" or
      "hashed_farthest_first",
  initialization_vector_ids:array<id>,
  initialization_vector_ids_sha256:sha256,
  prefill_cartesian_centers_binary64_bits:
      nullable array<array<bits64> of length 2>,
  prefill_cartesian_centers_binary64_bits_sha256:nullable sha256,
  prefill_cartesian_sse_bits:nullable bits64,
  initial_centers_binary64_bits:array<array<bits64> of length 2>,
  initial_centers_binary64_bits_sha256:sha256,
  steps:array<block_step>,
  iteration_count:id,
  accepted_update_count:id,
  converged:boolean,
  final_assignments:array<id> of length 8192,
  final_assignments_sha256:sha256,
  final_centers_binary64_bits:array<array<bits64> of length 2>,
  final_centers_binary64_bits_sha256:sha256,
  final_centers_binary32_bits:array<array<bits32> of length 2>,
  final_centers_binary32_bits_sha256:sha256,
  final_sse_bits:bits64,
  distance_comparison_count:count,
  assignment_tie_count:count,
  farthest_tie_count:count,
  serialized_distinct_center_count:id,
  direct_replay_match:boolean,
  cartesian_dominance_pass:boolean,
  selected_best_start:boolean
}
```

Every center array has `capacity` rows except the start-0 prefill array, whose
length is `arbitrary_used_states`. The three `prefill_cartesian_*` fields are
nonnull only for start 0 and are null together for starts 1--7. For start 0,
`initialization_vector_ids` lists only the deterministic fill rows and has
length `capacity-arbitrary_used_states`; for starts 1--7 it lists all
farthest-first rows and has length `capacity`. The step array contains every
accepted complete Lloyd step. Its center hash uses the canonical JSON bytes of
the logical post-update binary64 center-bit array. `iteration_count`,
`accepted_update_count`, and the step-array length are equal. The selected-start
flags contain exactly one `true`, matching the metadata record. Each
`cartesian_dominance_pass` records the direct comparison with the shared
start-0 prefill replay. Start 0 and the selected start must pass; the field is
descriptive for the other starts.

### 5.3 Allocation JSONL records

An allocation arm object is exactly:

```text
{
  requested_cardinalities:array<id> of length 2,
  effective_cardinalities:array<id> of length 2,
  used_states:id,
  invalid_states:id,
  exact_fitting_sse:exact_sse,
  enumerated_candidate_count:count
}
```

`allocations.jsonl` first has 128 group records in `(word_bits,group_id)` order,
B4 before B8. Each is exactly:

```text
{
  record_type:string exactly "group_allocation",
  word_bits:id restricted to 4 or 8,
  capacity:id equal to 2^word_bits,
  group_id:id in 0..63,
  coordinates:array<id> of length 2,
  dyadic_word:allocation_arm,
  arbitrary_word:allocation_arm
}
```

The final two records are B4 then B8 and are exactly:

```text
{
  record_type:string exactly "global_allocation",
  word_bits:id restricted to 4 or 8,
  total_bit_budget:id equal to 64*word_bits,
  bit_widths:array<id> of length 128,
  bit_widths_sha256:sha256,
  cardinalities:array<id> of length 128,
  cardinalities_sha256:sha256,
  used_bits:id,
  exact_fitting_sse:exact_sse,
  enumerated_transition_count:count
}
```

Thus a complete allocation shard always has exactly 130 records.

### 5.4 Encoding JSONL records

An encoding arm object is exactly:

```text
{
  label_count:id,
  labels:array<id>,
  labels_sha256:sha256,
  payload_bytes:id restricted to 32 or 64,
  payload_hex:string of exactly 2*payload_bytes lowercase hex digits,
  payload_sha256:sha256,
  alignment_bytes:id,
  output_bytes:id,
  roundtrip_labels:array<id>,
  roundtrip_labels_sha256:sha256,
  roundtrip_match:boolean,
  distance_comparison_count:count,
  pack_operation_count:count,
  unpack_operation_count:count
}
```

For the three matched-word arms, `label_count=64`; for the global arm it is
128. Each rate shard has 8,192 records in vector-id order, each exactly:

```text
{
  record_type:string exactly "encoded_vector",
  word_bits:id restricted to 4 or 8,
  vector_id:id in 0..8191,
  arms:{
    dyadic_word:encoding_arm,
    arbitrary_word:encoding_arm,
    trained_block_vq:encoding_arm,
    global_dyadic_pack_cap8:encoding_arm
  }
}
```

The arm object has exactly those four keys. Labels and round-trip labels use
their representation's declared group or selected-coordinate order.

### 5.5 Timed ledger and terminal prefixes

The pass plan contains exactly 259 normal shards in this order: 128 scalar
shards by coordinate id, the allocation shard, 64 B4 block shards by group,
64 B8 block shards by group, then the B4 and B8 encoding shards. A plan entry
is exactly:

```text
{index:id, path:string, role:string, expected_record_count:id}
```

Roles and pass counts are fixed by path class:

```text
detail/scalar/*.jsonl: role="scalar_curve_shard", count=256
detail/allocations.jsonl: role="allocation_shard", count=130
detail/block/*.jsonl: role="block_vq_shard", count=9
detail/encoding/*.jsonl: role="encoding_shard", count=8192
```

Plan indices are `0..127` for scalar coordinates, `128` for allocations,
`129..192` for B4 block groups, `193..256` for B8 block groups, `257` for B4
encoding, and `258` for B8 encoding.

A completed-shard entry is exactly:

```text
{index:id, path:string, role:string, record_count:id, size_bytes:id,
 sha256:sha256}
```

A normal shard is written to a temporary path, flushed and closed, checked for
its exact pass record count, hashed, and only then atomically published. A
temporary or partial normal shard is never published or entered in the
ledger.

The checkpoint object is exactly:

```text
{
  phase:string restricted to "preflight", "scalar", "allocation", "block",
      "encoding", "output", or "complete",
  completed_operation_count:id,
  last_completed_plan_index:integer at least -1,
  cumulative_cpu_microseconds:id,
  reason_code:string,
  message:string,
  path:nullable string,
  coordinate_id:nullable id,
  word_bits:nullable id,
  group_id:nullable id,
  start_id:nullable id,
  arm:nullable string,
  requested_cardinality:nullable id,
  effective_cardinality:nullable id,
  first_colliding_label:nullable id,
  prior_sse_bits:nullable bits64,
  candidate_sse_bits:nullable bits64,
  center_count:nullable id,
  distinct_center_count:nullable id,
  expected_sha256:nullable sha256,
  observed_sha256:nullable sha256
}
```

In addition to the common top-level fields,
`timed_output_ledger_body.json` has exactly:

```text
planned_shards:array<plan_entry>
completed_shards:array<completed_shard_entry>
missing_suffix:array<plan_entry>
checkpoint:checkpoint
projection_complete:boolean
terminal_status:string restricted to "ARTIFACT_INVALID",
    "IMPLEMENTATION_INVALID", "CONTROL_INVALID",
    "NO_GO_REPRESENTATION", "NO_GO_EXACT_SOLVER_COST", or
    "PENDING_FINAL_CPU_DECISION"
```

`planned_shards` is always the complete 259-entry pass plan.
`completed_shards` must match an exact prefix of that plan by index, path, role,
and expected record count. `missing_suffix` is exactly the remaining plan
suffix. The body does not list itself. When all scientific pipeline work is
complete, all 259 shards are present at their fixed counts,
`missing_suffix=[]`, checkpoint phase is `complete`,
`projection_complete=true`, and both the common `status` and
`terminal_status` are `PENDING_FINAL_CPU_DECISION`. The body is then closed and
the end CPU snapshot is captured. The untimed wrapper, manifest, and summary
replace that pending status with `PASS_SYNTHETIC_GATE_ONLY` or
`NO_GO_EXACT_SOLVER_COST` using only the integer gate in Section 4. Thus output
serialization that crosses the ceiling cannot leave a stale PASS in the timed
body.

For any terminal or early-stop status written directly into the timed body
before full pipeline completion, publish only fully completed normal shards in
the exact prefix, discard a current temporary shard, set the checkpoint to the
last completed operation and failure evidence, list the entire uncompleted
normal-shard suffix, and set `projection_complete=false`. This is the only
permitted incomplete normal-shard layout; it cannot reorder work, retain a
hole, publish a short normal shard, or omit a completed prefix shard. It lets
the declared `CONTROL_INVALID`, `NO_GO_REPRESENTATION`, and lower-bound
`NO_GO_EXACT_SOLVER_COST` states remain distinguishable from
`IMPLEMENTATION_INVALID`.

If all 259 normal shards and the timed body complete but the final integer CPU
snapshot fails the gate, the final state is `NO_GO_EXACT_SOLVER_COST` with
`projection_complete=true` and an empty missing suffix. This full-completion
case is distinct from the earlier lower-bound stop.

The timed ledger body, including serialization, flush, and close, is inside
the timed region. The committed detail-ledger wrapper repeats this body, binds
its canonical SHA-256, and adds the captured integer-microsecond timing trailer
outside the clock as specified in Section 4.

Each artifact index lists the relative path, byte size, SHA-256, schema
version, and producer execution commit of every committed artifact in that
checkpoint. An index does not include its own hash.

## 6. Status precedence and repair boundary

Gates run in the fixed order below and stop at the first applicable state.
A later no-go cannot mask an earlier artifact, implementation, or control
defect.

| Order | Condition | A4-1S status |
| ---: | --- | --- |
| 1 | Forbidden path/open, contract identity, or read-boundary failure | `ARTIFACT_INVALID` |
| 2 | Toolchain, numeric, exact-reference, allocation, rounding, packing, lookup, schema, ledger, or accounting failure | `IMPLEMENTATION_INVALID` |
| 3 | Block initialization, convergence, monotonicity, dominance, best-start, or distinct-center failure | `CONTROL_INVALID` |
| 4 | A full-shape selected scalar nominal alphabet is unreachable or collapses at binary32 | `NO_GO_REPRESENTATION` |
| 5 | `5*timed_region_cpu_microseconds > 2*86400000000`, or the running integer-microsecond lower bound has crossed the equivalent one-panel limit | `NO_GO_EXACT_SOLVER_COST` |
| 6 | Every parity/control check and the complete cost projection pass | `PASS_SYNTHETIC_GATE_ONLY` |

An external interruption, machine loss, scheduler eviction, or missing output
that occurs before a registered status can be established is
`INCOMPLETE_NO_DECISION`; resume the identical clean-commit command without
changing a frozen choice. `RESOURCE_STOP` remains the name for the later
atomic base command's 24 CPU-hour ceiling and is not used for an unrelated
A4-1S interruption.

`ARTIFACT_INVALID`, `IMPLEMENTATION_INVALID`, and `CONTROL_INVALID` are not
scientific negative results. A defect may be fixed, but the implementation
commit changes and all downstream parity/review/cost evidence must be
regenerated. `NO_GO_REPRESENTATION` and `NO_GO_EXACT_SOLVER_COST` preserve the
evidence and close this A4-1 formulation; they do not permit a precision,
shape, library, or parameter rescue. `PASS_SYNTHETIC_GATE_ONLY` permits only a
separate user decision about the first real-base read.

## 7. Commit-before-cost sequence

The following order is mandatory:

1. Commit this A4-1S protocol and authorization-state updates before accepting
   or committing runner implementation and before any RNG execution.
2. Implement the native path, synthetic guard, tests, and artifact writer from
   a clean tree. Commit them as the implementation commit.
3. From that exact clean commit, run all nonrandom tiny tests, A4-0 tests, the
   256 scalar suite, representation suite, and 64-case block suite.
4. Commit canonical parity artifacts and their index. Record the implementation
   commit that produced them.
5. Conduct an independent code/parity review and commit its review memo. Any
   code correction invalidates the parity evidence and returns to step 2.
6. Require a clean tree at the reviewed parity commit and verify that runner,
   native, and test sources have not changed since the recorded implementation
   commit. Only then run `cost-projection`.
7. Commit the cost manifest, summary, detail ledger, and artifact index.
8. Conduct and commit an independent cost-projection review. Verify the full
   external detail ledger before interpreting passage.
9. Report the A4-1S status. Only `PASS_SYNTHETIC_GATE_ONLY` permits asking the
   user whether to authorize the real-base gate.

No cost result from an uncommitted runner, an unreviewed parity artifact, a
dirty worktree, or a changed binary is admissible.

## 8. Frozen build and command interface

Use a dedicated ignored build directory and one build job:

```bash
cmake -S research/a4_1s -B build/a4_1s \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/a4_1s \
  --target a4_1s_native -j1
```

The target must enforce and manifest the exact flags; successful compilation
under another compiler is not passage.

The synthetic entry point is
`script/run_arbitrary_cardinality_a4_1s.py`. It is the timing bootstrap frozen
in Section 4: after its start snapshots it imports the separately hash-bound
runner module and delegates the command. The bootstrap and runner are both
implementation sources and must both remain unchanged across parity and cost.
Its only scientific subcommands and options are frozen below. Each output
directory must not exist or must be empty at process start.

Parity command:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python script/run_arbitrary_cardinality_a4_1s.py parity \
  --input-spec docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json \
  --hypotheses docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json \
  --output-dir /tmp/saq-attempt4-a4-1s-parity \
  --threads 1
```

Cost-projection command, admissible only after the reviewed parity commit:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python script/run_arbitrary_cardinality_a4_1s.py cost-projection \
  --input-spec docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json \
  --hypotheses docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json \
  --output-dir /tmp/saq-attempt4-a4-1s-cost-projection \
  --threads 1
```

The runner locates the fixed native target and committed parity index by
repository-relative paths; it exposes no override for them. It rejects unknown
arguments. It verifies the clean execution commit, source and binary hashes,
contract hashes, artifact-index hashes, environment variables, and runtime
numeric state before materializing a random fixture.

## 9. Decision after A4-1S

A4-1S asks only whether the registered exact implementation is correct,
deterministic, representation-complete, and affordable at the frozen
same-shape synthetic scale. It cannot show that arbitrary cardinalities help
natural residuals or ANN search.

If A4-1S returns `PASS_SYNTHETIC_GATE_ONLY`, stop and present the committed
implementation, parity review, cost evidence, and cost review to the user.
The next decision is whether to authorize the first read of the six registered
base-only artifacts. Until that separate explicit authorization, the A4-1
base-data gate remains forbidden.

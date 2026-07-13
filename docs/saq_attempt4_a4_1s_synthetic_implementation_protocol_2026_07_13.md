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
`build/a4_1s/compile_commands.json` for all three target translation units:
`a4_1s_native.cpp`, `exact_quantizer.cpp`, and `numeric_runtime.cpp`. Sort
entries by repository-relative source path, store each raw `command` string,
and tokenize it with Python `shlex.split(..., posix=True)` into the recorded
argv array. Absence of a raw `command` field is `IMPLEMENTATION_INVALID`; do
not silently substitute a generator-specific representation. Every one of the
three argv arrays must contain all mandatory flags and no forbidden flag. The
runtime helper's compiled-in `compile_flags` field records only the frozen
numerical subset; it may not be reported as a complete command. Source and
binary hashes bind the manifest to these entries.

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

Enumerate every valid tuple for registered mixed-radix examples and every
address through `S-1`; verify encode/decode, invalid positive-infinity entries,
B4/B8 packing, exact payload length, and round-trip. Exercise global bit widths
including zero, byte boundaries, and a non-byte-aligned paid-bit sum, while
always padding to the registered 32/64 bytes. Independent arithmetic must
match both lookup parity layers from Section 2.5.

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
`getrusage(RUSAGE_SELF)+getrusage(RUSAGE_CHILDREN)`, captured by the Python
supervisor at its first executable statement before NumPy is imported. The
timed region includes contract/numeric preflight, NumPy import and generation,
all native children, every model, encoding, all external detail shards, the
complete detail-ledger body, its serialization, flush, and close. The
supervisor captures the end usage immediately after those timed files are
closed.

The captured end value is necessarily unavailable to a file that must already
contain and be flushed with that value. Therefore only the following small
trailer finalization is outside the gate clock: inject the captured total into
the cost manifest and summary, copy the timed region's already-computed shard
hashes into the detail-ledger wrapper, write and hash those three files, then
write the artifact index, and flush those four committed JSON files. These
wrappers may derive no model, allocation, encoding, or work result. Their own
write/flush duration cannot be embedded without a second self-reference, so no
untimed-duration field is reported or interpreted. The artifact index records
the first three wrapper sizes and hashes and, as always, excludes itself.
This exact four-file trailer is the complete exclusion and may not grow. It
resolves the timing self-reference; it is not a discretionary exclusion.

Record component CPU and wall times as diagnostics, but apply the decision
only to the timed-region CPU delta. The projected two-dataset cost is exactly
`2.5 * timed_region_cpu_seconds`; passage requires it to be at most 86,400
seconds, equivalently a complete one-panel timed region at most 34,560 CPU
seconds.

Check cumulative timed-region CPU after each completed scalar coordinate, allocation,
block model, encoding arm, and output shard. If it has already exceeded 34,560
seconds, further work cannot restore passage. The runner may then stop at that
checkpoint and return `NO_GO_EXACT_SOLVER_COST` with `projection_complete=false`
and the measured CPU as a strict lower bound. This is not a reduced-shape run:
the full shape was launched, the fixed ceiling was already crossed, and no
scientific output is interpreted. A pass is valid only after every listed
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

All committed top-level `.json` artifacts and the external
`timed_output_ledger_body.json` use `schema_version=1` and
`protocol_version="saq-attempt4-a4-1s-20260713-schema1"`. The common fields
have these fixed JSON types:

```text
schema_version: integer
protocol_version: string
stage: string, exactly "A4-1S"
status: string
parent_preregistration_commit: 40-hex string
implementation_commit: 40-hex string
execution_commit: 40-hex string
command: array of strings containing argv without shell reconstruction
thread_environment: object from string keys to string values
input_ledger: array of {path:string, role:string, size_bytes:integer,
                        sha256:string}
output_ledger: array of {path:string, role:string, size_bytes:integer,
                         sha256:string, timed:boolean}
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
representation artifact contains exact allocation candidates/winners,
rounding fixtures, addresses, payload bit/byte layouts, and both lookup parity
layers. The block artifact contains fixture identities, start hashes,
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

Every exact curve and partition from the full projection must be persisted in
the empty external output directory. Because the complete partition detail can
be large, raw detail is not committed to Git. Instead,
`synthetic_cost_projection_detail_ledger.json` commits, for every deterministic
output shard, its relative path, schema, record count, byte size, and SHA-256,
plus a SHA-256 over the canonical ordered ledger. The cost summary and timing
are committed as required by the parent protocol. Review must inspect a
deterministic sample from every shard class and independently verify all shard
hashes before real-base authorization is requested.

The external detail layout is frozen, uncompressed UTF-8 canonical JSON Lines
with one canonical object and one LF per line:

```text
detail/scalar/coordinate_000.jsonl ... coordinate_127.jsonl
detail/block/group_000_b04.jsonl ... group_063_b04.jsonl
detail/block/group_000_b08.jsonl ... group_063_b08.jsonl
detail/allocations.jsonl
detail/encoding/rate_b04.jsonl
detail/encoding/rate_b08.jsonl
detail/timed_output_ledger_body.json
```

Each scalar shard has exactly 256 records in ascending `K`; each record holds
the exact curve, effective cardinality, complete partition/means, rounding
bits, replay result, and diagnostics for that coordinate and `K`. Each block
shard has one metadata record followed by exactly eight start records in start
id order; a start record contains its initialization and complete accepted-step
trace. `allocations.jsonl` has the 128 group/rate product records in
`(word_bits,group_id)` order followed by the B4 then B8 global records.

Each encoding shard has 8,192 records in vector-id order. A record contains
each arm's complete selected-label array **and** its SHA-256, exact paid
payload bytes as lowercase hex, round-trip result, and byte/work counters; the
global arm is included.
`timed_output_ledger_body.json` lists every preceding timed shard with path,
role, record count, byte size, and SHA-256. No gzip, compression, binary side
format, alternate shard count, or data-dependent split is allowed. These
fixed files, including serialization, flush, and close, are inside the timed
region. The committed detail-ledger wrapper repeats this body, binds its
ordered canonical SHA-256, and adds the captured timing trailer outside the
clock as specified in Section 4.

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
| 5 | Complete projection exceeds 34,560 CPU seconds, or its running lower bound has already crossed it | `NO_GO_EXACT_SOLVER_COST` |
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
`script/run_arbitrary_cardinality_a4_1s.py`. Its only scientific subcommands
and options are frozen below. Each output directory must not exist or must be
empty at process start.

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

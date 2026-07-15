# Independent Review: A4 V2 Executable-Identity Source Repair

Date: 2026-07-15

Reviewed stage: `A4-V2-I-R1`

Exact review target:
`e48df4523f99c085cfcb83623664054b5f9ae6f7`

Independent review verdict: **SOURCE_REPAIR_STATIC_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

## 1. Scope and method

Three independent read-only tracks reviewed the exact committed source:

1. producer/artifact-identity review checked the literal running-image
   descriptor, same-inode proof, bounded read, EOF and stability checks,
   descriptor closure, and generic no-follow boundary;
2. supervisor/Git-authority review checked all PAR admission and Python-family
   receipt sites, cache/fork semantics, error classification, exact source and
   document identities, and the frozen stage boundary; and
3. independent-verifier review checked the physically separate positional-I/O
   implementation, pathname reopen proof, failure mapping, and source-manifest
   enforcement.

The review used Git-object inspection, exact parent/tree/blob measurement,
SHA-256 and byte-size recomputation, canonical JSON comparison, diff and
whitespace checks, and static control-flow reasoning only. No implementation
module was imported or syntax-checked. No Python command, compiler, build,
test, parity fixture, RNG, native executable, generated artifact, benchmark,
dataset, index, or SAQ path was executed or read. The quarantined bytecode and
empty staging directory were not read, removed, renamed, or reused.

## 2. Exact Git identities

```text
commit       e48df4523f99c085cfcb83623664054b5f9ae6f7
parent       fe10bc3da39ed9265f9c5bb6b52c7a52bced7b2e
tree         86c1907d1bcaff817721ffddc0460d2f4f5c4b4a

AGENTS       4ef0f4fda347d51878ad7abc5bcc59884fbe93a6
TASK         dc43e513c3a4ef156adc11be87c0d7aaab9c4008
binding      5c5ab7bcfbe49a61e60d8d0a21471b7f908688ca
manifest     2aa64e50dad19626711e0dd90c038704ac73e328
provenance   ec1f0cc9100a30c3cdeee73af95fb470a3a44a3f
parity       1e8627075d81da89449cbb4729f60958bd134c3e
runner       b9c9993a4116f03b2e57a569fd16062308165f2e
verifier     b45c434099689c46102f5e7e18602a118cede9c2
```

The target changes exactly those eight authorized paths, with no mode change,
extra source, generated artifact, or scientific/native-source delta.
`git diff --check` passes.

The canonical implementation manifest is 11,972 bytes including its terminal
LF and has SHA-256
`2617de46e502323bd21ee9ed656f400b6ff7aa89ca2acd404496a9e23f427fbc`.
Its rebound document identities match these exact bytes:

```text
authorization  5,603 bytes  7c65bf52a244fa6e4c1af8098a33bf17e0c8b8bfeb44d3b54c5c0a73a0ef798a
binding       46,838 bytes  6faef77fd62a5e262a465cd2ba0dc2e62a1519c3b6e35edf69e73e49e21bfd63
provenance     9,602 bytes  764dc48bbf34ab4c1379d8c36dfd23b52c2e0ad0a7fb49ac2da03ec411dce9df
```

All 35 source SHA-256 and byte-size entries match the target Git blobs. The
three changed source identities are:

```text
script/a4_v2_parity.py    106,938 bytes  3da8bbd7f06381a34557a291393d4e180d00e7a54fb93e0ea9f2f75f2ab57b04
script/a4_v2_runner.py    315,760 bytes  6cc458d830e9808de717996ab2124690ff067de45971a08c240c2dda03985a7d
script/a4_v2_verifier.py  219,669 bytes  7ea2d21e4266e63cafab9d6075616ff6f359ef7f3baf6192260a79c87a6f7623
```

Recomputing the canonical ordered `{path,sha256,size_bytes}` array yields:

```text
8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a
```

The manifest remains canonical, contains exactly the same 35 sorted unique
source paths, and retains `build_status=NOT_AUTHORIZED_NOT_RUN`.

## 3. Repair verdict

The conductor now identifies the already-running CPython image through a
stable descriptor opened on literal `/proc/self/exe`. The normalized absolute
`sys.executable` pathname is intentionally followed only in this dedicated
helper and must identify the same nonempty regular inode before the read. The
running image is capped at one GiB, read to its recorded size, probed for EOF,
and checked for stable device, inode, mode, size, modification time, and change
time. Reopening `sys.executable` after the read must reproduce all six final
fields.

Runner admission and every Python-family receipt site use one validated
SHA-256/size identity. The cache is published only after complete success,
contains no descriptor, is safe for the frozen fork/exec call graph, and
cannot convert a partial read into evidence. Raw identity-I/O `OSError`
failures map to `ARTIFACT_INVALID`; existing typed failures remain intact.

The independent verifier implements the same contract with verifier-local
`pread` logic and imports no conductor or runner helper. Generic document,
artifact, tree, and native-binary readers retain their prior `O_NOFOLLOW`
boundaries. No solver, allocation, fixture, RNG, representation, timer,
receipt schema, FOM, threshold, or scientific claim changed.

Pre-freeze review found two LOW issues: an incomplete double-close guarantee
in the parity helper and syscall-location-dependent verifier error
classification. Both were corrected before this exact target was created;
all three exact-target reviews found no remaining issue at LOW or above.

## 4. Decision and authorization boundary

`A4-V2-I-R1` therefore ends at:

```text
SOURCE_REPAIR_STATIC_REVIEW_PASS
```

This is a reviewed source correction only. It is not `PASS_PARITY`, artifact
execution readiness, a synthetic feasibility result, evidence about an SAQ
limitation, a database-systems contribution, or a performance claim. The
historical `A4-V2-PAR` result remains
`ARTIFACT_INVALID / REVIEWED_TERMINAL / NO_SCIENTIFIC_DECISION`.

The five quarantined bytecode files still expose a separate import-cost and
unmetered-cache-byte determinism question. This review neither resolves nor
authorizes a policy for them. Cleanup, cache-policy implementation,
`A4-V2-PAR-R1`, `A4-V2-SRUN`, benchmark/data access, and SAQ modification all
remain unauthorized. A later step requires separate explicit user authority;
this review grants none.

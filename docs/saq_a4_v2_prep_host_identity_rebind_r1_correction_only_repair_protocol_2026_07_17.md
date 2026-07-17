# A4-V2 PREP HOST-I R1-P correction-only repair protocol

Date: 2026-07-17

Stage: `A4-V2-PREP-HOST-I-R1-P`

Authority: the user's exact instruction
`授权 A4-V2-PREP-HOST-I-R1-P correction-only repair protocol + direct-child review`.

## 1. Question, scope, and ceiling

The smallest falsifiable question is whether one documentation-only protocol
can freeze a truthful, finite repair of the sole HIGH finding against HOST-I
source-static target `46025854ce1657e09fa64ac9277e53a87c8e15b2`, without
rewriting that failed target, modifying any implementation source, or opening
PREP or scientific execution.

This target is protocol governance only.  It adds this protocol and its
machine contract plus focused branch status.  Its exact direct-child review
must inspect an immutable commit.  With zero findings at LOW severity or
above, the maximum outcome is:

```text
HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS
```

That verdict does not correct the false identity, establish
`HOST_IDENTITY_REBOUND`, authorize `A4-V2-PREP-HOST-I-R1`, or establish
syntax, PREP readiness, cache-verifier/PAR readiness, feasibility,
performance, an SAQ limitation, novelty, or a method.

## 2. Immutable failure being repaired

The publication-closed branch head is negative review `e8e9c79` (tree
`2185c5d`), whose parent is source-static target `4602585` (tree `c508047`).

The source-static target is preserved as failed evidence.  Its exact review
status is:

```text
SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
```

The immutable governing source-authority-erratum review is:

| Field | Value |
| --- | --- |
| commit | `9fa9528f4181d51fe6e060c1de14ea568eb31c4a` |
| path | `docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md` |
| Git blob | `2a59fc202c71e2ec736f1b6dc1fccf635ceb5b3e` |
| bytes | `11,426` |
| true SHA-256 | `c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331` |

Target `4602585` instead introduced the following unsupported value once in
the implementation binding and once in the source-provenance crosswalk:

```text
c670d368647fbd13bfe4133241e2c37e29101e91538687a64349a606bd059f2a
```

The failure is a provenance-referent defect, not host drift, a SHA-256
collision, source behavior, or scientific evidence.

## 3. Exact protocol-target and review projections

This protocol target must be the direct child of unchanged, clean, pushed
head `e8e9c799fae39284688ff87d5c138be9ade80e51`.  It changes all and only
these mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_2026_07_17.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_contract_2026_07_17.json
```

Its direct-child independent review changes all and only these mode-`100644`
paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_independent_review_2026_07_17.md
```

The reviewer may record PASS or FAIL but may not repair either protocol
object.  A LOW-or-higher finding forces a terminal protocol-review failure and
a user checkpoint.  Commit, push, publication bookkeeping, and the mandatory
Meeting Summary Handoff are permitted; they grant no repair or execution
authority.

## 4. Separately authorized future R1 topology

Only after this exact protocol target and direct-child review are committed,
pushed, publication-closed, handed off, and pass with zero LOW-or-higher
findings may the user separately authorize the exact stage name:

```text
A4-V2-PREP-HOST-I-R1
```

No separate authorization-document target is required by this minimal
protocol.  The later user instruction itself must be recorded in the two root
status files.  The future repair target must be the direct child of the clean,
pushed protocol-review head and changes all and only these five mode-`100644`
paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
```

Its exact direct-child repair review may change all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_independent_review_2026_07_17.md
```

This new topology supersedes only the earlier fourteen-path direct-parent and
three-path review rules for purposes of repairing the recorded HIGH.  It does
not change or retroactively pass `4602585/@e8e9c79`; those commits remain
immutable failed evidence.

## 5. Exact correction-only semantic delta

The future repair is deliberately smaller than the failed source target.
The five implementation sources and the other four derived runtime/cache
authorities already contain the intended HOST-I bytes and remain unchanged.

The implementation binding must replace exactly one occurrence:

```text
c670d368647fbd13bfe4133241e2c37e29101e91538687a64349a606bd059f2a
->
c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331
```

The source-provenance crosswalk must perform the identical one-occurrence
replacement.  No prose, whitespace, line ending, authority row, source
identity, size, or other byte may change in either file.

The implementation manifest must change exactly two existing scalar values:

1. `implementation_binding_identity.sha256` from
   `5d6b62bcd74a0626a2f807050dfde3c68b29f3f28ccfa171518af0ed89cc5245`
   to the corrected binding identity below; and
2. `source_provenance_identity.sha256` from
   `529d15a5407a18a247598005cae59d2710213e699b8ff9aeb6c94a1bb7ebba24`
   to the corrected crosswalk identity below.

The manifest path, byte-size fields, schema, key order, compact encoding,
`authorization_identity`, `source_tree_sha256`, every source array, and
`build_status=NOT_AUTHORIZED_NOT_RUN` remain byte-identical outside those two
equal-length replacements.

Correction-only projection produces these frozen identities:

| Object | Corrected SHA-256 | Bytes | Corrected Git blob |
| --- | --- | ---: | --- |
| implementation binding | `457eec708fa16246752b963a33de29c911e6944eba39297a863f1e75756901a2` | 60,272 | `44e412562b82d7dd484c7d37a6cb3aab5a92c6f4` |
| source-provenance crosswalk | `ae892a728424fd62c4e2798435cc257359534ed55038b085e1a65ca0c8d933cb` | 18,455 | `269831087d463ee48d3cfe37bb2f5cab73f42613` |
| implementation manifest | `de08c638b20821c039a9ef3659f9cbab1fedca32a04aba62989bf5c361490daa` | 34,789 | `f33adb28d5385e78d8edb882e9351e104bc5f757` |

These identities were computed as a read-only stream projection from
immutable `e8e9c79` bytes.  The later committed repair target, not this
prediction alone, must independently establish them.

R1-P is repair governance, not a new source-semantic authority component; it
must not be appended to the active binding or crosswalk or add a manifest
field.

## 6. Frozen closure and overhead

The identity cascade terminates at the implementation manifest.  The cache
authority, static closure, runtime schema, and maximal witness name the
manifest path where applicable but do not bind the manifest's whole-file
SHA-256.  They must remain byte-identical.

The correction changes no filesystem source.  The exact active closure
remains 37 filesystem sources, 38 executable units, 27 native/CMake sources,
10 Python sources, and source-tree SHA-256
`97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a`.

All five HOST-I source identities, the 19,631-byte inline bootstrap, the
2,778-byte pre-START prologue, eight-component cache authority, historical
CACHE-I-SYNTAX snapshots, and `build_status` remain unchanged.

The three corrected artifact files retain their exact byte sizes because all
replacements are equal length.  Thus the future repair has zero source-byte,
runtime, construction, query, index, and scientific-state overhead.  New
protocol/status/review bytes are permanent governance overhead and must not be
reported as method or performance work.

## 7. Future repair review requirements

The future direct-child repair reviewer must independently establish all of
the following from the immutable target:

1. exact parent, path/mode projection, tree, commit, push, and clean head;
2. the true 11,426-byte review identity by hashing
   `9fa9528:<registered review path>`, never a worktree copy or abbreviation;
3. exactly one false-to-true replacement in each of binding and crosswalk and
   no other byte change;
4. exact corrected SHA-256, size, and Git blob identities for both documents;
5. exactly the two registered manifest scalar replacements, exact corrected
   manifest identity, and all other manifest bytes unchanged;
6. byte identity of the other four derived runtime/cache authorities and all
   five HOST-I sources relative to `e8e9c79`;
7. the unchanged 37-source/38-unit inventory, canonical source tree, inline
   bootstrap/prologue, historical CACHE-I-SYNTAX labels, and build status;
8. read-only re-observation of all thirteen bounded HOST-P objects against the
   registered `.el9_8.2` identities; and
9. every claim ceiling and prohibition below.

Any shortened digest in an exact identity map is invalid.  Full 64-character
digests must come directly from hashing immutable `commit:path` bytes.  Two
documents repeating the same value is not independent evidence.

PASS requires zero findings at LOW severity or above.  Only then may the
review assign:

```text
HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS
HOST_IDENTITY_REBOUND = ESTABLISHED_FOR_REGISTERED_13_OBJECT_BUNDLE_ONLY
```

Whole-host identity remains unestablished because the loader, shared
libraries, kernel, and other mapped dependencies are outside the bounded
bundle.

## 8. Preserved downstream blocker and prohibitions

The known `SOURCE_HISTORY_MISMATCH` remains deliberately unrepaired.  Old
CACHE-I/PREP commits correctly retain old source blobs, while the active
authority contains the HOST-I source blobs.  This does not block this static
correction or PREP itself, but it forbids cache-verifier/PAR readiness until a
separate protocol, authorization, implementation, and review close it.

Neither this protocol nor its future R1 permits:

- rewriting, amending, reverting, force-pushing, or relabeling the failed
  `4602585/@e8e9c79` evidence;
- changing any Python, CMake, C++, schema, maximal witness, cache authority,
  static closure, runtime source, or SAQ/CAQ path;
- Python, DNF, syntax, import, compiler, build, test, fixture, RNG, repository
  executable, cache-verifier, PREP, probe, clone, START, token, receipt,
  CACHE-BIND, PAR-R1, or SRUN execution;
- quarantine enumeration/read/stat/hash/copy/cleanup or any dataset, query,
  ground-truth, centroid, cluster, index, or result access;
- environment or host mutation; or
- feasibility, performance, systems, novelty, SAQ-limitation, or method
  claims.

The old invocation authority remains nontransferable and the old probe
remains superseded and must never run or be reused.  Fresh PREP authorization,
an actual invocation grant, and every later cache/PAR/scientific stage remain
separate user checkpoints.

## 9. Stop rules

R1-P stops after target/review commit, push, handoff, and user report, or
earlier on any LOW+ finding, dirty/unpublished parent, unexpected path/mode,
identity inconsistency, or need for execution.  Even after PASS, do not form
the repair target without explicit `A4-V2-PREP-HOST-I-R1` authorization.

# A4 V2 Source Provenance And Semantic Crosswalk

Date: 2026-07-14

Stage: `A4-V2-I`

Status: **STATIC_SOURCE_PROVENANCE_NO_EXECUTION_EVIDENCE**

## Purpose

This crosswalk distinguishes the historical algorithmic semantics that V2
must preserve from the newly written V2 supervision, evidence, and verifier
source. It prevents two opposite errors:

1. presenting carried-forward scalar/block/representation machinery as a new
   research contribution; and
2. silently treating another branch's runner or worktree as an implementation
   dependency.

The source identifiers below are provenance only. V2 neither loads them at
runtime nor reads historical artifacts.

## Read-only historical semantic oracle

Historical source authority:

```text
repository: git@github.com:Ufowoqqqo/SAQ.git
commit:     f1b464b6803e0f435055b45891255be0129cb9be
```

| Historical object | Git blob | SHA-256 recorded by reviewed A4-1S build manifest | Semantic role |
| --- | --- | --- | --- |
| `research/a4_1s/exact_quantizer.cpp` | `dbf9a4313e1f584930e55f7472b4d4e6620643be` | `af3a6809ea222d80c913fbba9d3da793bf23030c255681b6b2303167b1154027` | exact support, complete-matrix SMAWK, direct RNE, allocations |
| `research/a4_1s/exact_quantizer.hpp` | `2192c52f723709d0f6c9f8b943f5844336c8f97d` | `691e7b4df6fbcfc2a78ed88ba30ab4457a6e76b9d1de979983802b9dbf564ae8` | scalar/allocation interfaces and exact record meaning |
| `research/a4_1s/block_vq.cpp` | `9a133a7cca9a13c6b552c89027ba44d35629edbc` | `dd21dd0a383d5a5d54d46745a095a0e34a4d19efbcc01986fe69c87d5fd91bb1` | row order, eight starts, Lloyd/control/best-start semantics |
| `research/a4_1s/block_vq.hpp` | `5c0107a501100f37607296cc201f5ef5997f04d0` | `b7b0d1c49a85fe5ccccd53d4762c1cc74f470b61212d312ee3a357bd1b9379c9` | block trace and failure interfaces |
| `research/a4_1s/representation.cpp` | `8f193e9fb1876e60b58c808b1b3597141345e933` | `56d9fbe46b30fcf25db0f82224c9f9c7d16a70701ed912895146b262100bf314` | mixed radix, assignment, lookup, B4/B8/global packing |
| `research/a4_1s/representation.hpp` | `5a56c166cd1fd7cf2ef86cb5d087a400a92a17e3` | `3170e1989438ae65ef6d51435a42e127aa0ab94772121bf0dc6fe6e3dd145662` | representation interface and counter meaning |
| `research/a4_1s/numeric_runtime.cpp` | `194a97e83dc335fd116636c7b80d9994fb290e17` | `8a0f151eb5df34a7993e578d8687276bc7d86a7dae00c2dd833cc367dcfeef1b` | compiler/library/rounding/MXCSR checks |
| `research/a4_1s/numeric_runtime.hpp` | `fa745fd51dab5a896b3c18bdd0fc905b9678e31e` | `1f79a199ccc3fae92545ffc699b36a528bb4300880734b07435697869d2d8a31` | frozen runtime interface |

Historical CLI source is consulted only to preserve scientific interchange
and child granularity:

| Historical object | Git blob | SHA-256 | Preserved boundary |
| --- | --- | --- | --- |
| `research/a4_1s/a4_1s_native.cpp` | `395e6e8260737e8862b4982041216d74ed31ea40` | `af3962e35bf34cb04fbc2d9c2d984606fea8cf0bd4e03320d64b017d26568cad` | parity command surfaces and strict child dispatch |
| `research/a4_1s/block_cli.cpp` | `130c17a15026b77697d34d0cfe611a4f04d14d99` | `d7773e0e1013ad388d5980fa79b3295ea13b7c1a5e29d5e662422b27962ad252` | one complete eight-start group per block child |
| `research/a4_1s/representation_cli.cpp` | `21c56bbabeaba80d7bafaa9ec067ed6f52a70241` | `4b40213a63c34a3b585fbedc66dcff06b69e000477789b64d2f7ad76f53cde7d` | allocation/encoding binary interchange |

## V2 producer preservation map

| Frozen semantic | V2 source owner | Required review question |
| --- | --- | --- |
| finite binary32 to exact `n*2^-149`, signed-zero canonicalization | `research/a4_v2/exact_quantizer.*` | Are all nonfinite inputs rejected and equal exact values aggregated? |
| complete-matrix Monge/SMAWK | `research/a4_v2/exact_quantizer.*` | Is `j>m` the finite empty-final-cluster extension rather than infinity padding? |
| at-most-K and recursive earliest predecessor | `research/a4_v2/exact_quantizer.*` | Are more nonempty intervals preferred before predecessor ties and `K>H` copied? |
| direct independent b32/b64 RNE | `research/a4_v2/exact_quantizer.*` | Is binary32 free of a binary64 intermediate? |
| product/global exact allocation | `research/a4_v2/exact_quantizer.*` | Are capacity and all three tie levels exact? |
| row order and hash-domain identity | `research/a4_v2/block_vq.*` | Is the predecessor domain retained and raw digest ordering used? |
| eight starts and scalar Lloyd order | `research/a4_v2/block_vq.*` | Are all starts complete, empty centers retained, and no tolerance introduced? |
| step assignment preimages | `research/a4_v2/block_vq.*` | Are before/after assignments retained during `C_core`, not regenerated in `E_emit`? |
| product/global packing and reference lookup | `research/a4_v2/representation.*` | Are nibble/bit order, invalid addresses, padding, and one narrowing exact? |
| frozen numeric environment | `research/a4_v2/numeric_runtime.*` | Are exact versions, flags, FE_TONEAREST, and MXCSR `0x00001f80` checked? |
| parity-compatible process boundary | `research/a4_v2/a4_v2_native.cpp` and native CLI source | Is every registered child separate and every child waited before a unit boundary? |

These are correctness-preserving ports, not proposed contributions.

## New V2-only implementation

The following source has no historical runner counterpart and must be reviewed
against the V2 protocol rather than judged by textual similarity:

| V2 source | New responsibility |
| --- | --- |
| `script/run_arbitrary_cardinality_a4_v2.py` | first-action integer timing bootstrap |
| `script/a4_v2_runner.py` | one supervisor, attempt lifecycle, sticky terminal-resource observation, irreversible visible-bundle fail-stop, full byte-level prelaunch replay, strict I--P--R--E Git admission, phase dispatch and finite finalizer; I-R1 adds one per-process stable running-CPython identity for PAR admission and Python-family receipts |
| `script/a4_v2_producer.py` | 396-unit prefix state, unpublished-invalid-unit boundary, exact phase ownership, and prevalidated atomic bundle publication |
| `script/a4_v2_producer_wire.py` | producer-only strict native interchange parser |
| `script/a4_v2_evidence.py` | encode-only producer evidence publication, prepublication byte reservation, and write-only F trailer |
| `script/a4_v2_parity.py` | later marker-bound build/PAR conductor, fresh-worker natural RSS-dominance admission, exact B/P retry ledger, five helper fixtures plus 64 production cases, finite `PAR_report` closure, and I-R1 stable running-CPython leader identity |
| `script/a4_v2_verifier.py` | standalone independent replay supervisor and verifier-summary publisher; I-R1 adds a verifier-local positional-read implementation of the running-CPython identity contract |
| `research/a4_v2_verifier/exact_reference.*` | disjoint full-shape exact solver and direct rational-to-IEEE conversion |
| `research/a4_v2_verifier/parity_cli.*` | exhaustive bounded scalar authority, exact helper semantics, and independent production-axis/block replay |
| `research/a4_v2_verifier/representation_parity.cpp` | independent allocation-order, packing, lookup, and 2,433,600-decision parity authority |
| `research/a4_v2_verifier/input_panel.*` | isolated CPython/NumPy input-authority regeneration with repository-import rejection |
| `research/a4_v2_verifier/replay.*` | complete producer-evidence and bundle reconstruction |
| `research/a4_v2_verifier/json_value.*`, `sha256.*` | verifier-local parser, canonical encoder, and digest implementation |
| `script/a4_v2_archive.py` | immutable pre-trailer audit, B/P `NONE`-disposition admission, prepublication global/RSS checks, archive body, identity pipe |

The old `script/a4_1s_runner.py`, `script/a4_1s_artifacts.py`, cost-projection
state, shard writers, finalizer, generated JSON, and tests are absent. V2 has
no import, include, link, symlink, subprocess, or filesystem path to them.

The three I-R1 additions have no A4-1S scientific counterpart.  They repair
only the artifact identity mechanism exposed by the reviewed pre-build
failure: literal `/proc/self/exe` identifies the already-running image,
`sys.executable` must name the same regular inode, and generic artifact reads
retain their previous no-follow semantics.  They do not change a solver,
fixture, RNG stream, representation, timer, receipt schema, or gate rule.

The PAR block input constructor preserves the historical deterministic
64-case fixture recipe in new source; it does not load a predecessor artifact.
Five fixed helper-level cases precede and do not alter that fresh PCG64 stream.
Their deliberately underfilled inputs isolate tie/fill/empty/order semantics.
For production cases only, the independent native verifier recomputes and
validates every scalar-axis bit from the raw rows before using it, so the
Python constructor is not accepted as independent block-replay evidence.

The timing/reporting state machines have no historical semantic authority.
In particular, the 15-key composite-authority PAR seal, exact 5,171-byte
ceiling, no-follow membership/fsync closure, one B/P external-signal restart,
strict `I < P < R < E` tree binding, and no-reread/no-rehash final trailer are
reviewed directly against the 2026-07-14 erratum.  They are instrumentation,
not a research contribution or executable evidence.

## CACHE-I additive governance provenance

`A4-V2-CACHE-I` adds artifact-governance code only.  It does not add or
replace a quantizer, solver, representation, fixture, random stream, search
rule, estimator, or scientific decision rule.  The two new filesystem sources
have the following disjoint roles:

| CACHE-I source | Additive responsibility | Explicit non-role |
| --- | --- | --- |
| `script/a4_v2_isolated_clone_prep.py` | standalone, stdlib-only supervisor for the separately authorized future isolated-clone preparation protocol | never imported by PAR, SRUN, producer, runner, parity, existing verifier, or SAQ |
| `script/a4_v2_cache_policy_verifier.py` | standalone, stdlib-only, PAR-only independent verifier of the parent/cache/source/binding control | never imported as a helper, never invoked by SRUN, and never evaluates scientific output |

Only `script/run_arbitrary_cardinality_a4_v2.py`, `script/a4_v2_runner.py`,
`script/a4_v2_parity.py`, and `script/a4_v2_verifier.py` receive additive
cache-governance changes.  The exact byte-level preservation and finite delta
claim is not inferred from prose or an AST normalization: it is the complete
baseline/candidate raw-byte partition in
`docs/saq_a4_v2_cache_static_closure_2026_07_15.json`.  That object separately
registers the frozen parent status-precedence functions, B/P external-signal
retry blocks, and both post-P-report functions as equal raw slices.  The other
four Python source blobs and all 27 native/CMake source blobs remain exact
members of the implementation manifest.

The file-source closure is therefore the prior 35 sources plus exactly these
two governance sources.  The immutable ASCII-only inline PREP bootstrap is a
separately identified executable unit, not a 38th filesystem path.  Its source
and raw-prefix prologue identities and its call/import/open/mutation/terminal
closure are bound by the additive cache authority and static-closure objects.
The resulting accounting is exactly 37 file sources and 38 executable units.

The cache-aware PAR build-manifest/PAR-index shapes, the seventh
`python_cache_policy` environment-preimage field, and the P-owned
`cache_policy_verification.json` artifact extend only the evidence DAG.  The
preimage contains policy/control identities that exist before P; actual B/P
observations and the independent result are written only in the P artifact.
That artifact retains the exact bounded canonical control preimage as
lowercase hex so its observation summaries and control identity can be
independently recomputed, then enters the existing index/seal publication
direction.  No earlier object predicts or hashes a future result.

## Claim boundary

This provenance record can support only a static statement that the V2 source
has named historical semantic authorities and a reviewable implementation
delta. It cannot establish compile success, parity, independent replay, cost,
representation validity, ANN behavior, or novelty.

For CACHE-I the same ceiling is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.  It is not PREP readiness,
PAR authority, a parity result, or scientific evidence.

## CACHE-I exact source seal and syntax-only exception

The final filesystem-source inventory is byte-sorted and contains exactly 37
paths.  Its canonical path/SHA-256/size preimage hashes to
`9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2`.
The separately identified inline bootstrap is the 38th executable unit and
has SHA-256
`9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b`
over 19,631 ASCII bytes.  It is not a filesystem source and is not included in
the source-tree preimage.

The exact six changed/new outer Python snapshots are:

| Source | SHA-256 | Bytes |
| --- | --- | ---: |
| `script/a4_v2_cache_policy_verifier.py` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | 151,371 |
| `script/a4_v2_isolated_clone_prep.py` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | 219,758 |
| `script/a4_v2_parity.py` | `2a85d17aad5863dcd01c598a7f87c3991ac26766a04b0297511bd24dad99127a` | 168,467 |
| `script/a4_v2_runner.py` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | 360,127 |
| `script/a4_v2_verifier.py` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | 250,023 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | 34,929 |

The user separately authorized `A4-V2-CACHE-I-SYNTAX` after these bytes were
locked.  `/usr/bin/python3.9` `compile()`-only checks passed for all six
outer snapshots and the exact inline snapshot.  No code object was executed
and no repository module was imported.  This is a syntax-only result, not
evidence of importability, runtime behavior, correctness, schema acceptance,
parity, cost, or scientific value.  It does not broaden PREP, PAR-R1, SRUN,
data, quarantine, or SAQ/CAQ authority.

The current worktree seal remains uncommitted nonevidence pending its exact
22-path target commit and direct-child independent review.  Its maximum status
is
`STATIC_SEAL_COMPLETE_PENDING_EXACT_TARGET_COMMIT_AND_INDEPENDENT_REVIEW`.

## HOST-I source-static provenance rebind

The active HOST-I source snapshot is a governance-only rebind layered on the
historical CACHE-I source seal above.  It is the direct child of reviewed
source-authority-erratum head
`9fa9528f4181d51fe6e060c1de14ea568eb31c4a`.  Its additive provenance is the
HOST-P component contract
`c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09`
(10,684 bytes), HOST-I erratum protocol/contract/review identities
`5d9ac7222f93f00de5f2cd96b6df16d389b9f3123b604115c515bae963a1088d`
(14,716),
`01dadbe2ba73a429a67d7029b5e4dafafb6b400a6067767a1aac161e9457977a`
(10,967), and
`c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331`
(11,426), plus the committed HOST-I authorization/review identities
`7a07e05eb2b96c7ecd57facf9f1b7405a63f0d6d66d2af3cad3a1eeb626ce3b0`
(11,928) and
`bda4f52b549e28b69cca5c012c21e12867266e0c5920eda27f7df87e478d69e9`
(14,740).

No scientific owner changes.  Exactly five active governance/runtime sources
receive seven equal-length leader-digest substitutions, partitioned
`1 + 2 + 2 + 1 + 1`; the cache verifier additionally receives the exact
eighth-component set/path admission frozen by the erratum:

| Active source | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `script/a4_v2_cache_policy_verifier.py` | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,568 | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` |
| `script/a4_v2_isolated_clone_prep.py` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 | `d671531132eb0c490dec1953ca778e8d03913b3d` |
| `script/a4_v2_runner.py` | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 | `44e1a8078caf8774d1005f88265c87167e462eb7` |
| `script/a4_v2_verifier.py` | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 | `d8e0bdc6df0865e95dfe631446d108368640e25d` |
| `script/run_arbitrary_cardinality_a4_v2.py` | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 | `21925cddb4d07a1ec046d405493980813a4d581a` |

All 27 native/CMake sources and the five unaffected Python sources remain
byte-identical.  The active closure remains 37 filesystem sources and 38
executable units, with canonical source-tree SHA-256
`97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a`.
The inline source is unchanged in length at 19,631 bytes and rebound
identically across PREP, cache authority, static closure, and implementation
manifest to
`d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56`;
its raw prologue remains 2,778 bytes at
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`.
The active cache authority is
`09c1b6adf429f933620e503e8ee479b2b17380e460b8961782a78309a18e9885`
over 43,128 bytes, and the active static closure is
`815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d`
over 218,872 bytes.

Permanent source growth is exactly 197 bytes.  The eighth authority member
adds one existing-loop identity check; a successful physical check adds
10,684 to the existing `filesystem_bytes_read` aggregate.  No ledger schema,
status, retry, cap, timer, construction, query, or scientific behavior
changes.  The exact fourteen-path target's total permanent tracked-byte delta
relative to `9fa9528` is `+12,758` bytes.

The CACHE-I-SYNTAX table immediately above remains an immutable historical
snapshot and is not evidence about the changed source bytes.  The separate
future `SOURCE_HISTORY_MISMATCH` is also preserved: historical commits retain
their old blobs, so this rebind establishes neither cache-verifier nor PAR
readiness.  No source was imported, parsed by Python, compiled, built, tested,
or executed, and no PREP, data, quarantine, or SAQ/CAQ action occurred.  The
target itself remains `HOST_I_SOURCE_STATIC_TARGET_FORMED_REVIEW_PENDING`
until its exact direct-child independent review; that ceiling is not a
performance or scientific result.

## SOURCE-HISTORY-I-R1 static provenance correction

`A4-V2-SOURCE-HISTORY-I-R1` changes no scientific owner or algorithm.  It
corrects only the standalone cache verifier's historical-source expectation:
four immutable pre-host-rebind commit roles use one closed five-override
legacy map, while six future roles use only the active 37-source authority.
The assignment is fixed by role before observation and never accepts whichever
epoch happens to match.

The exact immutable authority chain is source-history protocol target/review
`dcaed57aaae6fe0f120377281921b6ea5336eb7f` /
`e98a3e401639cae4f11ea97d21883120e9b797fb`, followed by path-closure erratum
target/review `150e5b38aa5b3e30dafe4e15632db5fb5add4a68` /
`774949179582c8a9acbf79d5bc1f2d9fc851957a`.  Their relevant immutable
SHA-256 identities are respectively protocol
`289e0acb8c1e8122e027fad1757f9fcc6b721ccf49affebce1141f51adfe2650`,
contract
`d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48`,
protocol review
`58bf7a3deb89e1ba9ab0bbe63c6f66e96d1abf6c44d2c7e47189bd38388c627e`,
erratum protocol
`f797d10b9a9ae3d7ad02000f6804858572bb6166b36564c797420b2c1493d3e3`,
erratum contract
`ea4412c35cbf087f251b62e7877bdfe75cc72343f9c2106ea6b1646f4c531ee2`,
and erratum review
`fa24897b393e878fe3f30ff20e95bd6c2e33f800cdcb655f0df1b2295309caab`.

The only changed filesystem source is:

| Source | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `script/a4_v2_cache_policy_verifier.py` | `8d0526273238ac510e0ef2e6887deee95157ae0e30c519f0cbb84207d922af9f` | 153,490 | `0797d0c860b69647a503b2a8e49ed19f16e61df5` |

All 36 other filesystem-source blobs remain exact.  The resulting canonical
37-source tree is
`2007875777e7af28a67e89d574b33ec35e71436d8bfaa203574c4343ef4cf973`.
The changed static closure is
`4c7787fb157b4d15985aeadca4133751160a34eb26cd62b4f19ed6b50849d292`
over 218,872 bytes, and the changed cache authority is
`3d5482a5b3fe7fc3a3164f0c56d875c4b00ada666024f5d5db31b5bac7132c7f`
over 43,349 bytes.

Relative to parent `7749491`, the verifier source grows by 1,922 permanent
bytes, the static closure changes identity at unchanged size, and the cache
authority grows by 221 bytes.  Their combined permanent delta is +2,143 bytes;
status and provenance prose are separate governance-document overhead.

The cache authority retains its original eight protocol components exactly
and adds only the immutable 11,379-byte source-history contract as component
nine.  The path-closure erratum is not a component.  Runtime schema and
maximal witness bytes remain unchanged because no output, parser, status,
observation, or ledger shape changes.  Permanent verifier-source growth is
1,922 bytes; a future successful component identity read would add 11,379 to
the existing filesystem-byte ledger, but no verifier was run here.

The earlier CACHE-I-SYNTAX identities remain historical and do not apply to
the changed source.  No Python, import, syntax, compiler, build, test,
verifier, PREP, CACHE-BIND, PAR, data, quarantine, or SAQ/CAQ operation ran.
Until direct-child review, the target supports only
`SOURCE_HISTORY_EPOCH_CORRECTION_R1_TARGET_FORMED_REVIEW_PENDING`, not
readiness, performance, scientific evidence, novelty, or a method claim.

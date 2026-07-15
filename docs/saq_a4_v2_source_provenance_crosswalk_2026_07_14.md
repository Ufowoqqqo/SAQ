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

## Claim boundary

This provenance record can support only a static statement that the V2 source
has named historical semantic authorities and a reviewable implementation
delta. It cannot establish compile success, parity, independent replay, cost,
representation validity, ANN behavior, or novelty.

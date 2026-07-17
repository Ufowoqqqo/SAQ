# A4-V2 PREP HOST-I R1 correction-only repair independent review

Date: 2026-07-17

Stage: `A4-V2-PREP-HOST-I-R1`

Reviewed immutable target:
`e17f8870e090be693adcd3bce4b8aea07432f064`

Reviewer role: sole independent static reviewer; no implementation ownership
and no recursive delegation.

## 1. Verdict and findings

```text
HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS
HOST_IDENTITY_REBOUND = ESTABLISHED_FOR_REGISTERED_13_OBJECT_BUNDLE_ONLY
```

| Severity | Count |
| --- | ---: |
| BLOCKER | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

The result is bounded to the thirteen registered `.el9_8.2` file/link
objects.  It is not whole-host identity: the loader, shared libraries, kernel,
and other mapped dependencies remain outside the bundle.

## 2. Review question, cost, and stop condition

The smallest falsifiable question was whether the immutable target performs
only the R1-P-frozen correction of the false governing-review identity and its
two dependent manifest scalars, while every source, other authority, historical
label, and downstream prohibition remains unchanged.

The cheapest decisive sequence was exact Git topology and projected-byte
equality, followed by closure/source comparison and finally read-only
re-observation of the thirteen host objects.  The target changes zero
scientific-core or implementation-source lines; its Git diff has 44 insertions
and five deletions, of which four equal-length scalar substitutions are the
artifact correction and the remainder is root governance status.  Existing
Git, `jq`, hash, byte-count, `stat`, and `readlink` tools were sufficient; no
support framework was created.  Any LOW-or-higher issue, extra byte, host
drift, or need for prohibited execution was a stop condition.

## 3. Exact target topology, publication, and identities

| Field | Value |
| --- | --- |
| commit | `e17f8870e090be693adcd3bce4b8aea07432f064` |
| tree | `533c27fbc3b9545829153d6ec5c95e81a7fe832a` |
| direct parent | `b1a7429cda3e4817d7df494f304bbce24bec2b92` |
| subject | `Form HOST-I R1 correction-only target` |
| local/tracking head at review start | both `e17f8870e090be693adcd3bce4b8aea07432f064` |

The worktree was clean at review start.  The target changed all and only the
five R1-P-registered mode-`100644` paths:

| Path | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `AGENTS.md` | `33a894e848e6bd5738a2c4cba8798858448dcbc4ca7c2f94c7322911202605cb` | 42,125 | `4a89a681de30410a6c199cc154af4daaa0fd0b0d` |
| `TASK.md` | `63c9a6697a9a0cad6ffd8312e09c59325a0beb62f846c8419717ee86142b015d` | 37,097 | `4774e89134b6c44b62490c804308a3ef3e86d811` |
| `docs/saq_a4_v2_implementation_binding_2026_07_14.md` | `457eec708fa16246752b963a33de29c911e6944eba39297a863f1e75756901a2` | 60,272 | `44e412562b82d7dd484c7d37a6cb3aab5a92c6f4` |
| `docs/saq_a4_v2_implementation_manifest_2026_07_14.json` | `de08c638b20821c039a9ef3659f9cbab1fedca32a04aba62989bf5c361490daa` | 34,789 | `f33adb28d5385e78d8edb882e9351e104bc5f757` |
| `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md` | `ae892a728424fd62c4e2798435cc257359534ed55038b085e1a65ca0c8d933cb` | 18,455 | `269831087d463ee48d3cfe37bb2f5cab73f42613` |

The exact review projection is all and only `AGENTS.md`, `TASK.md`, and this
memo, each mode `100644`.

## 4. Immutable referent and correction proof

Hashing the registered immutable object—not a worktree copy—established:

| Field | Observed value |
| --- | --- |
| commit | `9fa9528f4181d51fe6e060c1de14ea568eb31c4a` |
| path | `docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md` |
| SHA-256 | `c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331` |
| bytes | 11,426 |
| Git blob | `2a59fc202c71e2ec736f1b6dc1fccf635ceb5b3e` |

At the parent, unsupported value
`c670d368647fbd13bfe4133241e2c37e29101e91538687a64349a606bd059f2a`
occurred exactly once in the binding and once in the crosswalk.  Replacing
that value once with the true SHA produces byte-for-byte the target binding
blob `44e412562b82d7dd484c7d37a6cb3aab5a92c6f4` and target crosswalk blob
`269831087d463ee48d3cfe37bb2f5cab73f42613`.  Thus neither object has any
other prose, whitespace, line-ending, size, or identity change.

At the parent, old binding SHA
`5d6b62bcd74a0626a2f807050dfde3c68b29f3f28ccfa171518af0ed89cc5245`
and old crosswalk SHA
`529d15a5407a18a247598005cae59d2710213e699b8ff9aeb6c94a1bb7ebba24`
each occurred exactly once in the manifest at the registered scalar.  Replacing
only those values with the corrected SHA values produces byte-for-byte target
blob `f33adb28d5385e78d8edb882e9351e104bc5f757`.  The manifest remains valid
compact JSON with unchanged key order, 34,789 bytes, authorization identity,
source tree, source arrays, and `build_status=NOT_AUTHORIZED_NOT_RUN`.

## 5. Unchanged derived authorities and HOST-I sources

Every required object has the same Git blob at parent and target:

| Object | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| cache authority | `09c1b6adf429f933620e503e8ee479b2b17380e460b8961782a78309a18e9885` | 43,128 | `0ee5f516d147a38229e6ce9b7050cdcfed9369de` |
| static closure | `815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d` | 218,872 | `1c58d4bc2f6bb602822ce11cc7b0f0800af7aeee` |
| runtime schema | `47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896` | 23,762 | `4d0c93f7fea77fec649ff2a9ab4168f1a340a3cf` |
| maximal witness | `5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42` | 4,439,071 | `51a03242b7ef667a4bd4275d8565122f49222674` |
| cache-policy verifier | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,568 | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` |
| isolated-clone PREP | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 | `d671531132eb0c490dec1953ca778e8d03913b3d` |
| runner | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 | `44e1a8078caf8774d1005f88265c87167e462eb7` |
| verifier | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 | `d8e0bdc6df0865e95dfe631446d108368640e25d` |
| entrypoint | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 | `21925cddb4d07a1ec046d405493980813a4d581a` |

Because none of the four derived authorities binds the manifest's whole-file
SHA-256, the correction cascade terminates at the manifest.

## 6. Closure, bootstrap, and historical syntax

Independent `jq` canonicalization of all `{path,sha256,size_bytes}` source
records reproduced source-tree SHA-256
`97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a`.
The manifest and static closure agree on 37 filesystem sources, 38 executable
units, 27 native/CMake sources, and 10 Python sources.

Extracting the inline source without execution reproduced 19,631 bytes and
SHA-256 `d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56`.
Its first 2,778 raw bytes reproduced prologue SHA-256
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`.

The authority and static-closure objects containing the two historical
`A4-V2-CACHE-I-SYNTAX` subtrees are byte-identical to the parent.  Those
compile-only labels remain bound to their old seven-source snapshots and are
not evidence about the active HOST-I bytes.

## 7. Registered `.el9_8.2` host-object observation

Read-only `stat`, SHA-256, and raw-link-target hashing matched all thirteen
registered identities:

| Object group | Observed identity |
| --- | --- |
| `/usr/bin/python3.9` | regular, 15,448 bytes, `c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b` |
| `/usr/bin/env` | regular, 45,088 bytes, `4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b` |
| `/usr/bin/timeout` | regular, 36,848 bytes, `025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69` |
| `_bootstrap_external.py` | regular, 66,447 bytes, `8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4` |
| `/usr/bin/git` | regular, 4,397,352 bytes, `f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3` |
| `git-remote-http` | regular, 966,840 bytes, `c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902` |
| `git-remote-https` | symlink to `git-remote-http`, 15 bytes, raw-link SHA-256 `e2909ed8f8e19a7f87e0e57c2bebf7851351f3a949c5e6c60e2bf419f65bb7aa` |
| six registered Git helpers | each symlink to `../../bin/git`, 13 bytes, raw-link SHA-256 `c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b` |

This observation establishes only the registered bundle result stated in the
verdict.  It does not bind the rest of the host.

## 8. Preserved blocker and claim ceiling

The binding, crosswalk, and root status retain the known
`SOURCE_HISTORY_MISMATCH`: historical CACHE-I/PREP commits contain old source
blobs while current authority contains HOST-I source blobs.  It remains
excluded from R1 and continues to forbid cache-verifier/PAR-readiness claims.
It requires its own later protocol, authorization, implementation, and review.

The old invocation authority remains nontransferable and the old probe remains
superseded.  This PASS does not authorize PREP, an actual invocation, cache
verification, PAR-R1, SRUN, data access, quarantine access, or SAQ/CAQ work.
It establishes no syntax, importability, executability, correctness, parity,
feasibility, performance, novelty, SAQ limitation, or method claim.

## 9. No-execution attestation and next checkpoint

This review used immutable Git reads, hashes, byte counts, blob projection,
`jq`, text comparison, and read-only host `stat`/`readlink`/SHA observations.
It ran no Python, DNF, syntax/import, compiler, build, test, fixture, RNG,
repository executable, cache verifier, PREP, probe, clone, START/token/receipt,
PAR, SRUN, quarantine, dataset, query, index, result, or SAQ/CAQ operation.
Nothing was compiled, executed, profiled, or scientifically reproduced.

No new scientific evidence was produced.  There is no active scientific hot
path or timed instrumentation in this stage, and
`PERFORMANCE_NOT_YET_MEASURED`.  After this exact review is committed, pushed,
and handed off, stop.  The smallest next action is a user checkpoint; PREP and
all downstream work remain separately unauthorized.

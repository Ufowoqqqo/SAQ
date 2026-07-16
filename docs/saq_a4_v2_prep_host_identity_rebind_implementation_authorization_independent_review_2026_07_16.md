# A4 V2 PREP Host-Identity Rebind Implementation Authorization Independent Review

Date: 2026-07-16

Review scope: one fresh, bounded, independent static review of immutable
authorization target `212a67b887aa710fed35f66766982db683b3fa63`.

## Independence and review boundary

The reviewer did not form or edit the target commit and did not participate in
the HOST-P target/review. The reviewed object was the immutable commit and its
direct edge from the registered parent, not mutable working-tree content.

The smallest falsifiable question was whether this exact three-path target
authorizes only the documentation node `A4-V2-PREP-HOST-I-AUTH`, completely
and consistently freezes a possible later HOST-I source edge, and preserves
all HOST-P ceilings. There are zero scientific-core files in this target; the
only new support object is the authorization record. The stop condition was
any finding at LOW severity or above, in which case no PASS memo would be
formed.

This review used only read-only Git, `rg`, `sed`, `jq`, `stat`, `sha256sum`,
and RPM queries. It did not run Python or DNF/YUM; execute repository source,
scripts, or native code; import, compile, build, test, or run PREP; run an
admission, publication, or execution-base probe; inspect a dataset, query,
index, result, quarantine, token, journal, receipt, or generated artifact; use
the network; or edit any source or authority object.

## Verdict

**PASS — zero findings at LOW severity or above.**

Severity counts are:

```text
BLOCKER  0
HIGH     0
MEDIUM   0
LOW      0
```

The maximum and only current-node verdict is:

```text
AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
```

This is authorization-artifact governance only. It is not source review,
host-identity establishment, PREP readiness, parity, synthetic feasibility,
performance evidence, an SAQ limitation, novelty, or a scientific decision.

## Exact immutable target and projection

Read-only Git identity checks returned:

```text
target       212a67b887aa710fed35f66766982db683b3fa63
tree         1d04f82ff9e85ec0fb351009720897d828ee495d
parent       b89dabedd0273a330dded7f61551e6ad1ceac19c
parent tree  d4ca936c4fb2caff16a5fcc20ed5001e0e133867
branch       refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

At audit start, `git status --short --branch` returned only:

```text
## saq-arbitrary-cardinality-feasibility-v2...origin/saq-arbitrary-cardinality-feasibility-v2
```

Thus the worktree was clean before this memo was created. The target edge has
exactly three paths, all target mode `100644`:

| Status | Path | Parent blob | Target blob |
|---|---|---|---|
| M | `AGENTS.md` | `05078fd841a3d3f74632b25e7b9f85d3f738af97` | `a1cf0833cbb6ea1198f3fbb693da49744acddf05` |
| M | `TASK.md` | `987da95b523bcecab0ded03f3ab79fb58d06843a` | `04cdf8d25511b2eae74a85f9d7bce3d20e4e777c` |
| A | `docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_2026_07_16.md` | absent | `3d5428b2fb0c8e3ab2512de75d7be1bd6d26bda6` |

`git diff-tree --no-commit-id --name-status -r` and `--raw -r` returned only
those entries. Therefore every unlisted tracked blob and mode is unchanged.
`git show --check --oneline 212a67b...` returned exit 0 with no whitespace
error.

The exact target SHA-256 values and byte sizes are:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `AGENTS.md` | `180ebd79e0e32c9b9e79df8e59584b0a7c29f94732feef10d49023fbd384a66e` | 32,874 |
| `TASK.md` | `9085cacd10a74bfef3378ba8974f86c70d98a167573141e75bc8746a8383ade0` | 27,574 |
| authorization record | `7a07e05eb2b96c7ecd57facf9f1b7405a63f0d6d66d2af3cad3a1eeb626ce3b0` | 11,928 |

## Exact instruction, node separation, and probe discipline

The target records the exact user instruction:

```text
授权 A4-V2-PREP-HOST-I-AUTH
```

Its interpretation is exact: formation, commit, push, and independent review
of the authorization record plus focused `AGENTS.md`/`TASK.md` status only.
The root files consistently mark the AUTH node
`IN_PROGRESS_DOCUMENTATION_ONLY` and the distinct source node
`A4-V2-PREP-HOST-I` as `NOT_AUTHORIZED`.

The authorization does not invent or spend a parent-admission predicate. It
states that no pre-target parent-admission probe is registered. The only
permitted publication observations for this documentation node are an
ordinary target-head equality check and, after the review commit is pushed,
an ordinary live review-head equality check. Neither is the retired PREP
probe, a new PREP execution-base probe, an implementation-parent admission,
or HOST-I-readiness evidence.

The implementation owner supplied the following already-completed ordinary
documentation target-publication observation; this reviewer did not repeat
it or use the network:

```text
exit    0
stdout  212a67b887aa710fed35f66766982db683b3fa63 refs/heads/saq-arbitrary-cardinality-feasibility-v2
HOME/XDG registered absence paths  absent before and after
```

It establishes only equality of the published branch target to this reviewed
commit. It is not PREP admission, a source-parent predicate, or evidence that
host identity has been rebound.

## Bound HOST-P objects and current host pin

`sha256sum` and `stat` independently matched all three HOST-P objects named by
the authorization:

| Object | SHA-256 | Bytes |
|---|---|---:|
| erratum protocol | `0cef593b0532070c87be49d3b7b469abe755ff20a072b8bfff915a2bf848289e` | 14,350 |
| erratum contract | `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09` | 10,684 |
| independent review | `dea30436db0cd1fd031274e6847a4f11e9d84b36d0ec90fc5a32c227be2b9a86` | 6,540 |

The contract parsed with `jq`. Its instruction, authority DAG, path sets,
invariants, prohibitions, historical disposition, and claim ceiling agree
with the authorization record.

Read-only `stat`, `sha256sum`, and `rpm` queries matched the sole current
leader pin:

```text
/usr/bin/python3.9
  regular file, 15,448 bytes
  sha256  c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
  rpm     python3-3.9.25-7.el9_8.2.x86_64
  source  python3.9-3.9.25-7.el9_8.2.src.rpm
```

The other twelve registered host objects also matched:

- `/usr/bin/env`: regular, 45,088 bytes,
  `4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b`;
- `/usr/bin/timeout`: regular, 36,848 bytes,
  `025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69`;
- `/usr/lib64/python3.9/importlib/_bootstrap_external.py`: regular, 66,447
  bytes, `8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4`;
- `/usr/bin/git`: regular, 4,397,352 bytes,
  `f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3`;
- `/usr/libexec/git-core/git-remote-http`: regular, 966,840 bytes,
  `c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902`;
- `git-remote-https`: a 15-byte symlink to `git-remote-http`; and
- `git-checkout`, `git-config`, `git-fetch`, `git-fsck`, `git-index-pack`,
  and `git-unpack-objects`: 13-byte symlinks to `../../bin/git`.

RPM ownership matched the registered `coreutils-8.32-41.el9_8.x86_64`,
`python3-libs-3.9.25-7.el9_8.2.x86_64`, and
`git-core-2.52.0-1.el9.x86_64` packages as applicable. This remains a bounded
object bundle, not whole-host identity; the loader, libpython, libc, OpenSSL,
and other mapped libraries remain explicitly unbound.

The historical states remain non-escalating:

```text
old PREP review head   HISTORICAL_VALID / STALE_FOR_ACTIVATION
old actual authority   UNSPENT_BUT_NONTRANSFERABLE
old probe              UNSPENT_BUT_SUPERSEDED / NEVER_RUN_OR_REUSED
permanent START token  ABSENT / NOT_CONSUMED
```

## Five-source and seven-derived baseline closure

The five possible future source paths match the frozen pre-rebind identities:

| Path | SHA-256 | Bytes | Old-digest occurrences |
|---|---|---:|---:|
| `script/a4_v2_cache_policy_verifier.py` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | 151,371 | 1 |
| `script/a4_v2_isolated_clone_prep.py` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | 219,758 | 2 |
| `script/a4_v2_runner.py` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | 360,127 | 2 |
| `script/a4_v2_verifier.py` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | 250,023 | 1 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | 34,929 | 1 |

`rg --count-matches` over the V2 research and script source trees found
exactly seven active occurrences of old digest
`c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0`
with the `1/2/2/1/1` per-file partition above, and no active source occurrence
of new digest
`c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b`.
The old digest occurs once in the new authorization record, only under the
explicit label `old sole digest`.

The seven derived objects independently match:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json` | `5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec` | 42,903 |
| `docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json` | `45a82a4f6b23d32f8d07517bd285003e60b484674a581aa1572cc6398c9773e3` | 4,439,071 |
| `docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json` | `942519ee027e8a033c653cd34329231696c6f970d4578193ecb054906d1140ea` | 23,762 |
| `docs/saq_a4_v2_cache_static_closure_2026_07_15.json` | `f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0` | 218,872 |
| `docs/saq_a4_v2_implementation_binding_2026_07_14.md` | `07e87a073410a79a078f752258bb98575c6a7f994cf5c740795b5b4b5bccafec` | 54,934 |
| `docs/saq_a4_v2_implementation_manifest_2026_07_14.json` | `168e4d6da4dd326484d81bf4e9bfffa654f39dda4867580a4fdf3bb9d009b182` | 34,781 |
| `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md` | `2e35be12bd272f0a99297d8a81be77998f089aa05028050173f91e37cdac3cca` | 14,485 |

## Complete source-tree, inline, and prologue closure

The implementation manifest and static closure register exactly 37
filesystem sources: 27 native/CMake and ten Python. The static closure
registers exactly 38 executable units, with the inline PREP bootstrap as the
sole non-filesystem unit.

For all 37 registered paths, an independent comparison of `sha256sum`,
`stat`, and `git ls-tree 212a67b...` against the static-closure entries found:

```text
manifest entries  37
SHA entries       37
stat entries      37
Git entries       37
mismatches         0
```

The canonical tree preimage was recomputed without repository Python using:

```text
jq -cS -j '.source_files|map({path,sha256,size_bytes})|sort_by(.path)' \
  docs/saq_a4_v2_implementation_manifest_2026_07_14.json | sha256sum
```

It returned exactly:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2  -
```

The implementation manifest retains `build_status` equal to
`NOT_AUTHORIZED_NOT_RUN`.

The raw source between the reviewed outer-source markers was hashed with:

```text
sed -n '5234,5447p' script/a4_v2_isolated_clone_prep.py | sha256sum
```

The result was
`9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b`.
`jq -j ... | sha256sum` returned the same digest for the cache authority,
static closure, and implementation manifest. Their source strings are equal,
are each 19,631 ASCII bytes, and have identical metadata. Hashing the first
2,778 bytes returned
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`,
matching the frozen raw pre-START prologue identity.

## Future path projections and parent binding

The HOST-P contract and authorization record agree on all path sets. A
separately authorized future source target has exactly fourteen unique paths:
the two root status files, the seven derived objects above, and the five
source files above. It must be the direct child of the unchanged, committed,
pushed, and publication-closed direct-child AUTH review head. There is no
authority to form that target now.

The two three-path review edges are distinct and exact:

```text
current authorization review
  AGENTS.md
  TASK.md
  docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_independent_review_2026_07_16.md

future source review
  AGENTS.md
  TASK.md
  docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md
```

Machine-contract extraction returned five unique source paths, seven unique
derived paths, fourteen unique source-target paths, and three unique paths in
each authorization-target, authorization-review, and source-review set. All
sets exactly match the prose. Any additional path requires an additive
protocol erratum.

## Invariants, prohibitions, and stop rule

The possible later semantic delta remains only the seven-for-seven exact
digest replacement. Dual-hash admission, old-hash fallback, wildcard or
prefix matching, package-version-only admission, and runtime RPM lookup are
forbidden. The future static obligations preserve the 37/38 inventory,
recompute affected hashes/sizes/blobs and the source tree, keep inline bindings
coherent, keep the prologue byte-identical, use only the new digest in runtime
schema/witness aliases, add the exact erratum contract while retaining all
historical base identities, bind this authorization without a schema change,
retain `build_status=NOT_AUTHORIZED_NOT_RUN`, keep CACHE-I-SYNTAX historical,
and preserve control flow, error precedence, status, retry, resource, path,
timer, cache, token, receipt, evidence-boundary, and scientific behavior.

Static review is explicitly not syntax or runtime evidence. A later
compile-only check would require separate named authorization.

The AUTH node permits no source, derived-object, HOST-P, historical PREP,
schema/witness, package, host, or environment mutation. It permits no Python,
DNF/YUM, import, syntax, compiler, build, test, fixture, RNG, executable,
PREP, old/new probe, clone, START, token, capture, journal, receipt,
CACHE-BIND, PAR-R1, SRUN, quarantine, dataset/index/result, or SAQ/CAQ action.

After this exact review is committed/pushed and the mandatory Meeting Summary
Handoff completes, the required action is to stop. A separate explicit user
instruction naming `A4-V2-PREP-HOST-I` is still required.

## Explicit ceilings

```text
A4-V2-PREP-HOST-I-AUTH  AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-PREP-HOST-I       NOT_AUTHORIZED
HOST_IDENTITY_REBOUND   NOT_ESTABLISHED
PYTHON                   NOT_AUTHORIZED_NOT_RUN
SOURCE_EDITS             NOT_AUTHORIZED_NOT_RUN
BUILD                    NOT_AUTHORIZED_NOT_RUN
PREP                     NOT_AUTHORIZED_NOT_RUN
DATA                     NOT_AUTHORIZED_NOT_RUN
PERFORMANCE              PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION      NONE
```

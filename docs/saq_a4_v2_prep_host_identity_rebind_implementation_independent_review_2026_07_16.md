# A4-V2 PREP HOST-I source-static target independent review

Date: 2026-07-17

Review scope: one fresh, independent, read-only static review of immutable
target `46025854ce1657e09fa64ac9277e53a87c8e15b2`.

## Verdict

**FAIL — one HIGH finding.**

```text
BLOCKER  0
HIGH     1
MEDIUM   0
LOW      0
```

The exact-target terminal status is:

```text
SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
```

`HOST_IDENTITY_REBOUND` is **NOT ESTABLISHED**.  This review establishes no
whole-host identity, syntax or executability result, PREP authorization or
readiness, cache-verifier or PAR readiness, parity, synthetic feasibility,
performance, SAQ limitation, novelty, or scientific decision.

## Immutable target, ancestry, projection, and publication

The reviewed commit has the exact topology:

```text
target       46025854ce1657e09fa64ac9277e53a87c8e15b2
tree         c5080470082912475bc7df11accbfc214de1ebe6
parent       9fa9528f4181d51fe6e060c1de14ea568eb31c4a
parent tree  7e6477f7a2e65f8b1c74f6e8faf3da1434c74ce9
```

The direct parent is the clean, pushed, publication-closed HOST-I
source-authority-erratum review head required by the reviewed erratum.  The
target push was accepted as:

```text
9fa9528..4602585  saq-arbitrary-cardinality-feasibility-v2
```

The same-named local origin-tracking ref equaled the target with ahead/behind
`0/0` when reviewed.  This is publication bookkeeping, not a PREP or
implementation-admission probe.

`git diff-tree --raw` showed all and only the frozen fourteen paths, each
preserving mode `100644`:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json
docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json
docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json
docs/saq_a4_v2_cache_static_closure_2026_07_15.json
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
script/a4_v2_cache_policy_verifier.py
script/a4_v2_isolated_clone_prep.py
script/a4_v2_runner.py
script/a4_v2_verifier.py
script/run_arbitrary_cardinality_a4_v2.py
```

Every other tracked blob and mode is inherited unchanged.  `git show
--check` reported no whitespace error.  The fourteen target objects have
these independently recomputed identities:

| Path | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `AGENTS.md` | `30a3e8f71e191d6f981188e4b4fdec097073568f7a882a7bd435153625bd63f8` | 37,758 | `dd838d86d310704b6b09d648c73f4b6b7f967738` |
| `TASK.md` | `a046e94c4785276ea748d2b1406064ac6d88b66efce7c80a09d3772b255834d3` | 32,942 | `6dbad4caae9aabc0cce1b52315c99fe4dd18d41e` |
| cache protocol authority | `09c1b6adf429f933620e503e8ee479b2b17380e460b8961782a78309a18e9885` | 43,128 | `0ee5f516d147a38229e6ce9b7050cdcfed9369de` |
| runtime maximal instance | `5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42` | 4,439,071 | `51a03242b7ef667a4bd4275d8565122f49222674` |
| runtime schema | `47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896` | 23,762 | `4d0c93f7fea77fec649ff2a9ab4168f1a340a3cf` |
| cache static closure | `815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d` | 218,872 | `1c58d4bc2f6bb602822ce11cc7b0f0800af7aeee` |
| implementation binding | `5d6b62bcd74a0626a2f807050dfde3c68b29f3f28ccfa171518af0ed89cc5245` | 60,272 | `295804a61a19ed711f54eb5f2814b30ab645518f` |
| implementation manifest | `c4834c81c625ad0486a8d27af7199cd74bc69656e87856a06d27396f68514923` | 34,789 | `3386942560a437afa53c96acb1268043f420f0eb` |
| source-provenance crosswalk | `529d15a5407a18a247598005cae59d2710213e699b8ff9aeb6c94a1bb7ebba24` | 18,455 | `68c7b7c3b963081a96bcb13dbd1692b77277f7ec` |
| `script/a4_v2_cache_policy_verifier.py` | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,568 | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` |
| `script/a4_v2_isolated_clone_prep.py` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 | `d671531132eb0c490dec1953ca778e8d03913b3d` |
| `script/a4_v2_runner.py` | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 | `44e1a8078caf8774d1005f88265c87167e462eb7` |
| `script/a4_v2_verifier.py` | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 | `d8e0bdc6df0865e95dfe631446d108368640e25d` |
| `script/run_arbitrary_cardinality_a4_v2.py` | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 | `21925cddb4d07a1ec046d405493980813a4d581a` |

## HIGH finding: false source-authority review identity

The reviewed erratum requires both the implementation binding and the
source-provenance crosswalk to cite the exact committed HOST-I
source-authority-erratum protocol, contract, and review identities as additive
authority/DAG provenance.

The target instead records this SHA-256 for the 11,426-byte erratum review:

```text
c670d368647fbd13bfe4133241e2c37e29101e91538687a64349a606bd059f2a
```

It appears at:

```text
docs/saq_a4_v2_implementation_binding_2026_07_14.md:1005
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md:217
```

Independent hashing of the immutable object at both parent `9fa9528...` and
target `4602585...` gives:

```text
path      docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md
sha256    c670d3685256d94812ee03d4932df304e0bd2ed6a61eeb670a618a9ac6eab331
bytes     11426
git blob  2a59fc202c71e2ec736f1b6dc1fccf635ceb5b3e
```

The two recorded values are not aliases or alternate encodings; they are
different digests.  The target therefore does not truthfully bind its stated
governing review object.  This is an authority-DAG integrity failure and is
sufficient to fail the zero-LOW-or-higher rule even though the source delta
and the other mechanical identities below are internally consistent.

The registered direct-child review projection permits changes only to
`AGENTS.md`, `TASK.md`, and this negative review memo.  It cannot edit either
faulty target document.  Correcting those documents would also change the
implementation binding and crosswalk identities consumed by the implementation
manifest.  Such a correction and its commit topology require separate explicit
authority; they are not authorized or attempted by this review.

## Other static checks that passed

### Source delta, inventory, and canonical tree

The complete five-source diff contains exactly the permitted changes:

- seven equal-length replacements of old leader digest
  `c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0`
  with sole new digest
  `c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b`;
- the exact `1 + 2 + 2 + 1 + 1` occurrence partition across cache verifier,
  PREP, runner, independent verifier, and entrypoint; and
- only the frozen set-member and exact path-map entry in the cache verifier.

The cache-verifier source grew from 151,371 to 151,568 bytes, exactly the
registered 197-byte addition.  The quoted component key has exactly two
semantic constant-table occurrences and the exact mapped path has one.  No
ninth component, alternate path, fallback digest, wildcard, prefix,
version-only rule, runtime RPM query, branch, status, or control-flow change
appears in the source diff.

All 37 registered filesystem-source SHA-256/size/Git-blob triples matched the
immutable target.  The arrays in the cache authority and static closure are
identical; removing `git_blob` makes them identical to the implementation
manifest source array.  The inventory remains:

```text
filesystem sources  37
executable units    38
native/CMake        27
Python sources      10
unaffected Python    5
```

All 27 native/CMake sources and the five unaffected Python sources are
byte-identical to the parent.  Independent canonical recomputation from each
of the three source arrays produced the same no-trailing-LF source-tree hash:

```text
97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a
```

### Inline bootstrap, schema, witness, and historical syntax

The raw inline bootstrap extracted from the PREP source and the source strings
in the cache authority, static closure, and implementation manifest are all
exactly 19,631 bytes with SHA-256:

```text
d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56
```

The first 2,778 pre-START bytes remain:

```text
0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7
```

The runtime schema has exactly one active leader-digest constant using the
new digest.  The maximal witness has exactly six active aliases using the new
digest—command, `/proc/self/exe`, and `sys.executable` for both parent and
verifier—and no old digest.  The two historical CACHE-I-SYNTAX subtrees are
byte-identical to the parent and retain only their old source/inline
identities.  They are not relabeled for this target.  The implementation
manifest still states:

```text
build_status  NOT_AUTHORIZED_NOT_RUN
```

### Component closure, overhead, and permanent bytes

Removing the new entry from the target cache authority yields the exact seven
parent `protocol_components` identities.  The eighth and only new component
is:

```text
key     prep_host_identity_rebind_erratum_contract
path    docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json
sha256  c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09
bytes   10684
```

All 17 cache-authority protocol/generic-object identity crosslinks and all
eight top-level implementation-manifest object identity crosslinks matched
their immutable target bytes.  The exception is the prose authority-DAG
review identity identified above, which is not one of those machine fields.

The existing sorted protocol-component loop now performs exactly one
additional call to its byte-identical `_check_identity` body.  Exact physical
success adds 10,684 to the existing `filesystem_bytes_read` aggregate.
Readable mismatch, absent/unreadable input, Git fallback byte counters, caps,
mismatch shape, status mapping, and failure precedence retain their old
behavior; no ledger key or schema field was added.

The exact fourteen-path target has a total permanent tracked-byte delta of
`+12,758` relative to parent `9fa9528...`; the source-only part is `+197`.
This is artifact-governance overhead, not construction/query work or
performance evidence.

### Bounded host-object observation

Read-only `stat`, `readlink`, and SHA-256 checks found all thirteen frozen
file/link identities matching:

| Object group | Result |
| --- | --- |
| `/usr/bin/python3.9` | regular, 15,448 bytes, `c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b` |
| `/usr/bin/env` | regular, 45,088 bytes, `4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b` |
| `/usr/bin/timeout` | regular, 36,848 bytes, `025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69` |
| `_bootstrap_external.py` | regular, 66,447 bytes, `8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4` |
| `/usr/bin/git` | regular, 4,397,352 bytes, `f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3` |
| `git-remote-http` | regular, 966,840 bytes, `c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902` |
| `git-remote-https` | symlink to `git-remote-http`, 15 bytes, `e2909ed8f8e19a7f87e0e57c2bebf7851351f3a949c5e6c60e2bf419f65bb7aa` |
| six registered Git builtin helpers | each a 13-byte symlink to `../../bin/git`, `c9cbed5f4adb8bff3cad9e95dcd8fa86548eb4ada0671cd9f888827308d8cf7b` |

This is only the registered bounded bundle.  The dynamic loader, libpython,
libc, OpenSSL, and other mapped libraries remain unbound, so no whole-host
identity claim follows.

### Known downstream limitation and claim ceiling

The cache verifier still builds `expected_source_blobs` from the current
authority and compares those blobs against registered historical CACHE-I/PREP
commits.  Those commits correctly retain the old five source blobs, so later
cache-verifier or PAR execution would still report
`SOURCE_HISTORY_MISMATCH`.  This remains outside HOST-I and was not repaired.
It does not block this source-only audit or PREP itself, but it independently
forbids cache-verifier/PAR readiness.

## Static methods and no-execution boundary

The review used only immutable `git show`/`diff-tree`/`cat-file`/`rev-parse`
inspection, SHA-256 and byte counts, `jq` structured-object comparison,
`diff`, `sed`, `wc`, `dd`, and read-only host `stat`/`readlink`/hash checks.
Representative outcomes were:

```text
target path/mode count                 14 / all 100644
registered source identities checked  37 / mismatches 0
cache-authority crosslinks checked     17 / mismatches 0
manifest identity crosslinks checked   8 / mismatches 0
bounded host objects checked           13 / mismatches 0
historical syntax subtrees             BYTE_IDENTICAL
origin tracking equality               0/0
authority-DAG prose identity findings  1 HIGH
```

No Python interpreter, Python parser/compiler, import, repository module,
build, test, fixture, RNG, repository native executable, cache verifier, PREP
tool/bootstrap, probe, clone, START token, receipt, CACHE-BIND, PAR, SRUN,
quarantine, data, index, result, or SAQ/CAQ operation was run.  No host or
environment state was mutated.  Untracked/WIP state was not evidence.

This negative review record is valid only as the exact target's direct child
and only if its commit changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md
```

All three must remain mode `100644`, and every other tracked blob and mode
must remain identical to target `46025854...`.  The permitted review commit,
push, publication bookkeeping, and mandatory Meeting Summary Handoff do not
authorize correction or execution.

```text
A4-V2-PREP-HOST-I        SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
HOST_IDENTITY_REBOUND    NOT_ESTABLISHED
WHOLE_HOST_IDENTITY      NOT_ESTABLISHED
SYNTAX_EXECUTABILITY     NOT_ESTABLISHED
PREP                     NOT_AUTHORIZED_NOT_RUN
CACHE_VERIFIER_PAR_READY NOT_ESTABLISHED
PERFORMANCE              PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION      NONE
```

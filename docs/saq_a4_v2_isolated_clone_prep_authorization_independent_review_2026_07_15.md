# Independent Review: A4 V2 Fresh R1 Isolated-Clone PREP Authorization

Date: 2026-07-18

Reviewed documentation node: `A4-V2-CACHE-PREP-R1-AUTH`

Exact immutable review target:
`cd1757e880d4a9480ada141d3883feb5142f925f`

Independent review verdict:
**PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

Actual PREP invocation: **NOT_AUTHORIZED**

Future invocation node:
**A4-V2-CACHE-PREP-ISO-R1 / NOT_AUTHORIZED**

Performance status: **PERFORMANCE_NOT_YET_MEASURED**

## 1. Scope, falsifiable question, and method

The exact committed and pushed target was reviewed only as formation of the
fresh dormant PREP authorization requested by the user's exact instruction
`授权 A4-V2-CACHE-PREP-R1-AUTH`.  The falsifiable question was whether that
three-path documentation target closes over the exact reviewed source-history
head, active source and authority identities, registered host ceiling, and
unchanged PREP boundary without introducing a source, schema, runtime status,
mechanism, threshold, retry, path, resource, or claim change.

Review used only immutable Git-object inspection, `jq` extraction, SHA-256
and byte-size recomputation, canonical-source-tree reconstruction, raw
Git-tree comparison, focused source-text inspection, one ordinary read-only
target-head publication observation, and `git diff --check`.  WIP and
untracked files were not evidence.

No repository Python, DNF, syntax/import, compiler, build, test, fixture, RNG,
native executable, cache verifier, PREP bootstrap/tool, immediate review-head
probe, clone, START token, capture sidecar, journal, receipt, CACHE-BIND,
PAR-R1, SRUN, quarantine, dataset, base/query/centroid/cluster-id/
ground-truth/index/generated-result, live host, environment-mutation, or
SAQ/CAQ action was run, opened, or changed.

## 2. Exact ancestry, path closure, and protected tree

```text
target       cd1757e880d4a9480ada141d3883feb5142f925f
parent       a1198c4c1e38743377db10dca96d3ab28d6b6dba
parent tree  ebd28613ba6ec7063851be3a60edd6e194b1248f
target tree  4e3c0fe0e99106a8d7b4e1b8922f25af07ac73c9
subject      Authorize fresh R1 PREP review node
paths        3
insertions   375
deletions    200
```

The target is the required direct child and changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md
```

All three target modes are `100644`.  Excluding those exact paths, parent and
target projections each contain 506 entries and have the same raw
`git ls-tree -r` projection SHA-256:

```text
17cfd95411652aaa15a5f17dbdb86d592c014c72f164cebe273360e6cf85b620
```

Every other tracked blob and mode is therefore unchanged.  The exact
parent-to-target `git diff --check` passed.

The fresh authorization record is:

```text
git blob  4f0ac05f491d2b8f2c8f5c6b74684a073023f14d
sha256    89e831d1d3fc712ae7b2095c4e2a48eff73b221398b691a00ba887e0ee34e20e
bytes     18,877
```

The frozen direct-child review edge is exactly `AGENTS.md`, `TASK.md`, and
this fixed review path, all mode `100644`.  No other review-path mutation is
permitted.

## 3. Ordinary target-head publication equality

After the target was committed and pushed, the reviewer made exactly one
ordinary read-only target-head publication observation:

```text
git ls-remote --refs https://github.com/Ufowoqqqo/SAQ.git \
  refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

Its exact result was:

```text
exit     0
stdout   cd1757e880d4a9480ada141d3883feb5142f925f<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
```

There was no failed or no-observation attempt before this successful result.
This is ordinary documentation-target publication equality only.  It is not
the future immediate authorization-review-head HTTPS probe, does not close or
admit a future PREP execution base, and grants no invocation authority.  That
future probe was not run.

## 4. Historical PREP authority disposition

The original authorization and review remain reachable at their immutable
commits:

| Role | Commit | Git blob | SHA-256 | Bytes | Disposition |
| --- | --- | --- | --- | ---: | --- |
| original authorization | `e7f940e924a338022bfe8fffcbb3496f12a5a75c` | `ab12040dd7998f6ef1106162b9310c3a36e436a1` | `42f33050eeb22e9f7da7cd339eaa7121ddc0a9852e8d05d9e7843ef74f41ea73` | 13,783 | `HISTORICAL_VALID_STALE_FOR_ACTIVATION` |
| original review | `16a8201ac36e6c8c514848d55ad5ef607eb053b9` | `943b5008d75ffd8cb4981b5cf45d1daf3b676777` | `99c1d7c5a4daa4ce88d18617554bb5c9a6db32d618a184a121e1e2f317727c77` | 10,444 | `HISTORICAL_VALID_STALE_FOR_ACTIVATION` |

Their Git blobs, SHA-256 values, and sizes were independently recomputed.  The
original actual-PREP authority remains
`UNSPENT_BUT_NONTRANSFERABLE`; its unique probe remains
`UNSPENT_BUT_SUPERSEDED_NEVER_RUN_OR_REUSED`.  Neither historical commit,
chat grant, remote observation, nor probe role transfers into R1.

## 5. Current source and executable-unit closure

The current implementation manifest was independently reproduced as:

```text
path      docs/saq_a4_v2_implementation_manifest_2026_07_14.json
git blob  2658a2e21c1e5e1c8edfbb7c7ee599257803e5f0
sha256    df8f7763d79e5b3c20d688a89637730473e7d291e532748b7e94c3744983e023
bytes     34,789
```

Every one of its 37 filesystem-source path/SHA-256/size identities matched the
exact target Git bytes and mode `100644`.  The inventory is duplicate-free
and contains 27 native/CMake plus ten Python sources.  Canonicalizing the
ascending UTF-8 path-ordered array of `{path,sha256,size_bytes}` objects
without a terminal LF independently reproduced:

```text
2007875777e7af28a67e89d574b33ec35e71436d8bfaa203574c4343ef4cf973
```

The manifest still records `build_status = NOT_AUTHORIZED_NOT_RUN`.  The
separate inline bootstrap is the 38th executable unit, not a filesystem
source.  The critical current identities are:

| Object | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| PREP tool `script/a4_v2_isolated_clone_prep.py` | `d671531132eb0c490dec1953ca778e8d03913b3d` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 |
| cache-policy verifier `script/a4_v2_cache_policy_verifier.py` | `0797d0c860b69647a503b2a8e49ed19f16e61df5` | `8d0526273238ac510e0ef2e6887deee95157ae0e30c519f0cbb84207d922af9f` | 153,490 |
| inline PREP bootstrap | n/a | `d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56` | 19,631 |
| inline raw prologue | n/a | `0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7` | 2,778 |

The inline full-source and exact 2,778-byte prefix hashes were recomputed from
the manifest source string.  Focused source inspection also confirmed that
the PREP tool and inline bootstrap retain the exact reused authorization and
review paths.

## 6. Syntax chronology

The old CACHE-I-SYNTAX result remains bound only to its immutable snapshots.
Comparing all six outer source Git blobs at `c33a2bff` with the current
target shows exactly one unchanged source:
`script/a4_v2_parity.py`.  Its historical exact-snapshot syntax fact remains
valid.

The cache-policy verifier, PREP tool, runner, verifier, and entrypoint all have
different current blobs.  The current full inline bootstrap also differs from
the old syntax-checked inline snapshot.  No old syntax result transfers to
those five corrected Python sources or to the current inline bootstrap, and
this review performed no syntax, import, or execution check.

## 7. Active derived authority and source-history closure

All active derived identities matched exact target bytes:

| Role | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| implementation manifest | `2658a2e21c1e5e1c8edfbb7c7ee599257803e5f0` | `df8f7763d79e5b3c20d688a89637730473e7d291e532748b7e94c3744983e023` | 34,789 |
| cache authority | `cbd1099a0f2e4dae45534443efb6fdcfba8dfdd2` | `3d5482a5b3fe7fc3a3164f0c56d875c4b00ada666024f5d5db31b5bac7132c7f` | 43,349 |
| static closure | `e2db5963654746c37d33fcb9f72dbaddc0dc7ffb` | `4c7787fb157b4d15985aeadca4133751160a34eb26cd62b4f19ed6b50849d292` | 218,872 |
| implementation binding | `dfee27927fb1cbc8f555dae90564d2c028ae71b5` | `68dfe04057480116ef7a993a50c3d84b1a818c1c0cfa699a5a12791f039d25d7` | 64,766 |
| source crosswalk | `63cc59ba1461044c8ac3ae08a71d4cb8fa2c5a16` | `24146b3376355ae1bffd887152ca3e7997b6db0ac7bca705541e170549ab5b10` | 21,690 |

Static inspection at
`script/a4_v2_cache_policy_verifier.py:341`,
`script/a4_v2_cache_policy_verifier.py:348`,
`script/a4_v2_cache_policy_verifier.py:356`, and
`script/a4_v2_cache_policy_verifier.py:3629` independently confirmed:

- exactly five legacy Git-blob overrides;
- exactly four legacy roles and six active roles;
- disjoint, exhaustive preassignment of the ten registered roles before
  observation;
- the legacy map equals the active 37-source map plus only the five
  overrides;
- each non-null role selects exactly its preassigned map, while null roles
  retain the existing skip;
- no either-epoch or observation-adaptive acceptance; and
- the existing one-Git-observation, parser, kind check, ledger, mismatch,
  failure-precedence, and retry semantics remain unchanged.

The five override blobs were also checked at all four immutable legacy
commits `c33a2bff`, `5db3025`, `e7f940e`, and `16a8201`; each commit
contains exactly those five legacy blobs.  The active manifest matches all 37
current blobs.

The cache authority contains exactly nine component key/path identities.  The
source-history contract
`docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json`
is the sole ninth component at SHA-256
`d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48`
and 11,379 bytes.  Neither the path-closure erratum nor this authorization is
a tenth component.

## 8. Governing reviewed chain

The review independently recomputed all identities bound by the fresh record:

| Role | SHA-256 | Bytes |
| --- | --- | ---: |
| CACHE-P protocol | `3cdeab39081dd8558683587f385e8d2c849d8414d7fe57b236dd89d6237a2149` | 62,883 |
| CACHE-P contract | `06fb28c460cf2a0c4f75525abb69695c40da810892351ea0bbf96a0efe5ad64a` | 58,109 |
| HOST-P protocol | `0cef593b0532070c87be49d3b7b469abe755ff20a072b8bfff915a2bf848289e` | 14,350 |
| HOST-P contract | `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09` | 10,684 |
| HOST-P review | `dea30436db0cd1fd031274e6847a4f11e9d84b36d0ec90fc5a32c227be2b9a86` | 6,540 |
| HOST-I-R1 review | `0ef853de52b0c13fb37c145d5036320756968ed077e7d9fe98f23565cf23127a` | 10,279 |
| source-history protocol | `289e0acb8c1e8122e027fad1757f9fcc6b721ccf49affebce1141f51adfe2650` | 16,130 |
| source-history contract | `d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48` | 11,379 |
| source-history protocol review | `58bf7a3deb89e1ba9ab0bbe63c6f66e96d1abf6c44d2c7e47189bd38388c627e` | 13,478 |
| path-closure erratum review | `fa24897b393e878fe3f30ff20e95bd6c2e33f800cdcb655f0df1b2295309caab` | 10,142 |
| source-history implementation review | `033f42c78523090e4a049edfed17f46096da9148fab7f69d4178150d1aa7d0bc` | 12,182 |

The corresponding reviewed commit chain remains
`5a47fed/b89dabe`, failed immutable `4602585/e8e9c79`,
`e17f887/e10bde7`, `dcaed57/e98a3e4`,
`150e5b3/7749491`, and `e9b5c83/a1198c4`.  The failed HOST-I node remains
failed evidence; later corrections do not retroactively pass it.

## 9. Registered host ceiling without live re-observation

The bound HOST-P contract records one accepted 15,448-byte
`/usr/bin/python3.9` digest:

```text
c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
```

It records twelve other matching frozen objects, yielding the reviewed
13-object bundle.  The immutable HOST-I-R1 review states exactly:

```text
HOST_IDENTITY_REBOUND = ESTABLISHED_FOR_REGISTERED_13_OBJECT_BUNDLE_ONLY
```

This review made no live host observation, file stat/hash, RPM query, or DNF
query.  It does not bind the dynamic loader, libpython, libc, OpenSSL, kernel,
or other mapped libraries and does not claim whole-host identity.  The
registered 13-object result is the maximum host claim.

## 10. Preserved schemas, witnesses, paths, statuses, and resources

All preserved schema/witness identities were recomputed from target Git
bytes:

| Role | SHA-256 | Bytes |
| --- | --- | ---: |
| CACHE-PREP binding schema | `6676ba50b9c4520a87ad5d2d28db76d8fe7029d2a6bf7ede568ee4b89fb8ed1d` | 5,536 |
| CACHE-PREP binding maximal witness | `1a20a65e7ba9dd98a6b6f5586427dbfdf45be7b0e282ee81b9eb7701c0459a7a` | 2,621 |
| PREP token schema | `e71eed64903428046acd4cf235220b0f6af68861fc30663e99c72167d469898a` | 11,295 |
| PREP token maximal witness | `6e8b1f76f17de432cf21327025636fc1a6dcc7e9b25b572616714f333d214099` | 17,798 |
| PREP receipt schema | `2ab06e7cb62b3316f9ea58ee0b1d220f50b43fd1cedf1df2bb5de5ef835864da` | 24,973 |
| PREP receipt maximal witness | `5aba7fe04b103967d9784061d5f8695cfb38d6b1af490f21dc65ffe3a7fbe199` | 83,207 |
| cache runtime schema | `47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896` | 23,762 |
| cache runtime maximal witness | `5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42` | 4,439,071 |

The protected-tree equality proves that the normative CACHE-P contract,
status precedence, paths, retry rules, caps, and claim ceiling are unchanged.
Focused static inspection confirmed the retained principal ceilings:

```text
wall nanoseconds                       1,800,000,000,000
CPU microseconds                       1,800,000,000
maximum concurrent family RSS bytes   2,147,483,648
logical isolation bytes               1,073,741,824
allocated isolation bytes             1,073,741,824
filesystem entries                    20,000
journal records                        100,000
```

All stream, canonical-string, process, journal-byte, token, capture, path,
receipt, and one-shot limits remain those in the immutable contract.  The
durable START boundary remains
`/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.lock`; this review
did not inspect, create, or mutate it.

The effective downstream status remains:

```text
A4-V2-CACHE-PREP-ISO-R1   NOT_AUTHORIZED
A4-V2-CACHE-BIND          NOT_AUTHORIZED
A4-V2-PAR-R1              NOT_AUTHORIZED
A4-V2-SRUN                NOT_AUTHORIZED
```

Only the documentation-review result changes from target-formation pending to
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.  No runtime status enum,
parser, schema, mechanism, retry, threshold, resource cap, host pin, timer, or
evidence boundary changed.

## 11. Future immediate probe and stop boundary

The future authorization-review-head OID is intentionally absent from the
reviewed target and cannot be self-referenced.  The newly reserved immediate
HTTPS probe was deliberately **not run**.  It remains inseparable from a
later, separately authorized single `A4-V2-CACHE-PREP-ISO-R1` invocation,
must observe the exact pushed direct-child review head immediately before
launch, and permits no intervening source-branch or worktree mutation.

The ordinary target-head observation in Section 3 cannot be reused for that
role.  No old observation or retired probe transfers.  Failure, head drift,
mutation, host mismatch, or inability to preserve the probe-to-launch
boundary requires a stop and new authority.  This memo contains no
review-head execution-base observation.

## 12. Consolidated findings and verdict

| Severity | Count | Exact locations |
| --- | ---: | --- |
| BLOCKER | 0 | none |
| HIGH | 0 | none |
| MEDIUM | 0 | none |
| LOW | 0 | none |

No finding remains in the exact target.  The maximum documentation-only
result is therefore:

```text
PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
```

This establishes neither PREP readiness nor an invocation.  Actual
`A4-V2-CACHE-PREP-ISO-R1` and its immediate probe remain
`NOT_AUTHORIZED`, as do clone/token/capture/journal/receipt creation,
CACHE-BIND, PAR-R1, SRUN, data/quarantine access, environment mutation, and
SAQ/CAQ changes.

Scientific evidence gained is **none**.  Scientific algorithmic core/support
ratio is `0:documentation`.  The stage has no scientific hot path or timed
region, instrumentation exclusion is not applicable, and the exact
performance statement is `PERFORMANCE_NOT_YET_MEASURED`.  It provides no
SAQ limitation, feasibility, SOTA comparison, novelty, method, or
database-systems contribution.

This memo and its two root status edits remain WIP/nonevidence until committed
and pushed.  A mandatory Meeting Summary Handoff follows that committed
review.  No actual PREP step or immediate probe may begin from this WIP.

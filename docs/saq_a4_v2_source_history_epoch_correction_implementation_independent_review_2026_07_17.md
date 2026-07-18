# A4-V2 SOURCE-HISTORY-I-R1 implementation independent review

Date: 2026-07-18
Stage: `A4-V2-SOURCE-HISTORY-I-R1`
Reviewed target: `e9b5c83823040c0ffe67b69e349a2ef6169292ae`
Reviewed tree: `861a1d0de04e3018d7447e9aff222b475af96bbb`
Direct parent: `774949179582c8a9acbf79d5bc1f2d9fc851957a`
Reviewer: sole direct-child independent static reviewer

## Verdict and consolidated findings

`PASS`

The exact conditional static-only outcome is:

```text
SOURCE_HISTORY_EPOCH_CORRECTION_SOURCE_STATIC_REVIEW_PASS
```

| Severity | Count | Exact locations |
| --- | ---: | --- |
| BLOCKER | 0 | none |
| HIGH | 0 | none |
| MEDIUM | 0 | none |
| LOW | 0 | none |

The result becomes durable only after this exact three-path review is
committed and pushed.  It is not syntax, execution, readiness, performance,
or scientific evidence.

## 1. Question, method, and stop rule

The smallest falsifiable question was whether the immutable target implements
all and only the frozen two-epoch source-history correction, closes its exact
five-object identity cascade, and preserves every runtime and claim boundary.

Inspection used only read-only Git, `sha256sum`, `wc`, `jq`, and targeted text.
I did not run Python, syntax/import, a schema validator, compiler, build, test,
repository executable, cache verifier, PREP, probe, clone, CACHE-BIND, PAR,
SRUN, quarantine, data, or host action.  Any LOW-or-higher issue, unexpected
path, extra source, adaptive epoch rule, identity mismatch, or runtime-shape
change required FAIL without repair.  None occurred.

## 2. Immutable target and exact path/stat closure

At review start the explicit worktree was clean on the required branch; HEAD
and its remote-tracking ref both equalled the reviewed target.  The target has
the required sole parent and independently recomputed parent tree
`edf3bb5147c1ede0361764ef3ea3bba289f16c54`.

All and only these eight paths change, each mode `100644`:

| Path | + / - | Git blob | SHA-256 | Bytes |
| --- | ---: | --- | --- | ---: |
| `AGENTS.md` | 42 / 1 | `e9596281524277ba1a4294fa4bf87d858501e852` | `5abc9b62d6c2f85ba9d6547935c20cfc97dc25ec3dd0de6af4f08a920c38a4d8` | 50,740 |
| `TASK.md` | 29 / 1 | `46a853bc66b89142c21529821f0502ec1b64e8d2` | `b2ada6bcc2c17634b301f9c1220c115ef0348b59cea2720cfc9dc617ac945812` | 45,192 |
| `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json` | 1 / 1 | `cbd1099a0f2e4dae45534443efb6fdcfba8dfdd2` | `3d5482a5b3fe7fc3a3164f0c56d875c4b00ada666024f5d5db31b5bac7132c7f` | 43,349 |
| `docs/saq_a4_v2_cache_static_closure_2026_07_15.json` | 1 / 1 | `e2db5963654746c37d33fcb9f72dbaddc0dc7ffb` | `4c7787fb157b4d15985aeadca4133751160a34eb26cd62b4f19ed6b50849d292` | 218,872 |
| `docs/saq_a4_v2_implementation_binding_2026_07_14.md` | 64 / 0 | `dfee27927fb1cbc8f555dae90564d2c028ae71b5` | `68dfe04057480116ef7a993a50c3d84b1a818c1c0cfa699a5a12791f039d25d7` | 64,766 |
| `docs/saq_a4_v2_implementation_manifest_2026_07_14.json` | 1 / 1 | `2658a2e21c1e5e1c8edfbb7c7ee599257803e5f0` | `df8f7763d79e5b3c20d688a89637730473e7d291e532748b7e94c3744983e023` | 34,789 |
| `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md` | 62 / 0 | `63cc59ba1461044c8ac3ae08a71d4cb8fa2c5a16` | `24146b3376355ae1bffd887152ca3e7997b6db0ac7bca705541e170549ab5b10` | 21,690 |
| `script/a4_v2_cache_policy_verifier.py` | 50 / 12 | `0797d0c860b69647a503b2a8e49ed19f16e61df5` | `8d0526273238ac510e0ef2e6887deee95157ae0e30c519f0cbb84207d922af9f` | 153,490 |

The exact total is eight files, 250 insertions, and 17 deletions.  Diff and
whitespace inspection passed.  No second filesystem source changes.

## 3. Original and R1-P authority chain

The commit ancestry is exact and linear:
`dcaed57... -> e98a3e4... -> 150e5b3... -> 7749491... -> e9b5c83...`.
Every frozen authority object retains its registered identity:

| Object | Commit | Git blob | SHA-256 | Bytes |
| --- | --- | --- | --- | ---: |
| original protocol | `dcaed57aaae6fe0f120377281921b6ea5336eb7f` | `2297c34e227a1ad7fe21d15b2674a4987e44e858` | `289e0acb8c1e8122e027fad1757f9fcc6b721ccf49affebce1141f51adfe2650` | 16,130 |
| original contract | `dcaed57aaae6fe0f120377281921b6ea5336eb7f` | `9c08aaf63d1e524cfa3579a764fd8ea14176cde8` | `d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48` | 11,379 |
| original review | `e98a3e401639cae4f11ea97d21883120e9b797fb` | `d59a56082c52eec113856eb33e918999415f6201` | `58bf7a3deb89e1ba9ab0bbe63c6f66e96d1abf6c44d2c7e47189bd38388c627e` | 13,478 |
| R1-P protocol | `150e5b38aa5b3e30dafe4e15632db5fb5add4a68` | `2c0131a93b554f155a4e444bdd35fc3eba823eb2` | `f797d10b9a9ae3d7ad02000f6804858572bb6166b36564c797420b2c1493d3e3` | 10,684 |
| R1-P contract | `150e5b38aa5b3e30dafe4e15632db5fb5add4a68` | `d7527a5576d25ba72cf390b8b28748bf28beca3d` | `ea4412c35cbf087f251b62e7877bdfe75cc72343f9c2106ea6b1646f4c531ee2` | 7,410 |
| R1-P review / implementation parent | `774949179582c8a9acbf79d5bc1f2d9fc851957a` | `fdb9c43987b845eef1f9cde5450f6379e4d8b2fa` | `fa24897b393e878fe3f30ff20e95bd6c2e33f800cdcb655f0df1b2295309caab` | 10,142 |

The target changes none of these authority objects.

## 4. Source delta and epoch semantics

The sole source delta is 50 added and 12 deleted lines, or 38 net lines.  It
is below the 80-line hard stop and within the approximate 25--45-line semantic
core expected by the frozen contract.  Its three bounded changes are visible
at verifier lines 328--365, 594--622, and 3613--3678.

Lines 341--347 contain all and only these five legacy overrides:

| Path | Legacy Git blob |
| --- | --- |
| `script/a4_v2_cache_policy_verifier.py` | `6f4f6c2afc963066c3eb1a0dc053b4987ee70337` |
| `script/a4_v2_isolated_clone_prep.py` | `884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7` |
| `script/a4_v2_runner.py` | `4c0e35855fb8d51223f133fa75f00eeb983de49d` |
| `script/a4_v2_verifier.py` | `4d5964ed1996c8aceb202191b6bf48b78b23a94c` |
| `script/run_arbitrary_cardinality_a4_v2.py` | `69d0ba6734c9fe9435b4dccaf8990cc60cf2dbbe` |

Read-only `ls-tree` reproduced all five blobs at each of the four immutable
legacy commits.  Lines 348--365 assign exactly CACHE-I target/review and
original PREP-authorization target/review to the legacy epoch, and exactly
future PREP-receipt, CACHE-BIND, and PAR target/review to the active epoch.
The sets are disjoint and cover all ten role names.

Lines 3625--3635 derive both expected maps from the active 37-source authority
and bind each role to one map before any historical tree observation.  Lines
3636--3644 retain the active-only current-tree check.  Lines 3645--3678 retain
the null skip, exactly one existing Git observation per non-null role,
`kind=blob`, `SOURCE_HISTORY_UNAVAILABLE`, `SOURCE_HISTORY_MISMATCH`, and
existing stdout/stderr ledger increments.  There is no either-epoch fallback,
observed-byte inference, adaptive selection, or warning downgrade.

The complete source diff adds no second source, function, parser, status, Git
observation, output, retry, cap, timer, or ledger field.  Static review does
not establish syntax or executability.

## 5. Exact nine-component boundary

Verifier lines 328--340 contain exactly nine component keys; lines 594--622
contain the same nine exact paths.  Existing exact-key and exact-path checks
at lines 2777--2795 remain unchanged, and the existing loop at lines
2834--2842 performs one identity check for each component.

The original eight cache-authority components are byte-for-byte preserved.
The sole ninth component is:

```text
source_history_epoch_correction_contract
docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json
SHA-256 d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48
11,379 bytes
```

Neither R1-P erratum object is a component.  There is no tenth component,
alias, wildcard, filler, or runtime discovery path.

## 6. Source tree and derived identity cascade

Independent comparison of all 37 registered paths found exact equality for
every target Git blob, physical SHA-256, and byte count.  Cache authority and
static closure source inventories are exactly equal; the manifest projection
equals them after removing only `git_blob`.  All inventories have 37 unique,
byte-sorted paths.

Compact sorted-key recomputation from each of the three inventories produced
the same canonical source-tree SHA-256:

```text
2007875777e7af28a67e89d574b33ec35e71436d8bfaa203574c4343ef4cf973
```

The five changed derived objects and the source are independently reproduced:

| Object | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| verifier source | `0797d0c860b69647a503b2a8e49ed19f16e61df5` | `8d0526273238ac510e0ef2e6887deee95157ae0e30c519f0cbb84207d922af9f` | 153,490 |
| static closure | `e2db5963654746c37d33fcb9f72dbaddc0dc7ffb` | `4c7787fb157b4d15985aeadca4133751160a34eb26cd62b4f19ed6b50849d292` | 218,872 |
| cache authority | `cbd1099a0f2e4dae45534443efb6fdcfba8dfdd2` | `3d5482a5b3fe7fc3a3164f0c56d875c4b00ada666024f5d5db31b5bac7132c7f` | 43,349 |
| implementation binding | `dfee27927fb1cbc8f555dae90564d2c028ae71b5` | `68dfe04057480116ef7a993a50c3d84b1a818c1c0cfa699a5a12791f039d25d7` | 64,766 |
| provenance crosswalk | `63cc59ba1461044c8ac3ae08a71d4cb8fa2c5a16` | `24146b3376355ae1bffd887152ca3e7997b6db0ac7bca705541e170549ab5b10` | 21,690 |
| implementation manifest | `2658a2e21c1e5e1c8edfbb7c7ee599257803e5f0` | `df8f7763d79e5b3c20d688a89637730473e7d291e532748b7e94c3744983e023` | 34,789 |

After normalizing only the frozen changed fields, parent and target hashes are
identical for cache authority, static closure, and implementation manifest.
Thus the authority changes only the verifier/tree, static-closure identity,
and ninth component; static closure changes only both verifier occurrences
and the source tree; manifest changes only source/tree and the exact dependent
cache-authority, binding, and crosswalk identities.  Binding and crosswalk are
append-only registrations of the same authority and identity closure.

The manifest preserves `schema_version=2`,
`build_status=NOT_AUTHORIZED_NOT_RUN`, and the exact existing
`authorization_identity`: HOST-I authorization SHA-256
`7a07e05eb2b96c7ecd57facf9f1b7405a63f0d6d66d2af3cad3a1eeb626ce3b0`,
11,928 bytes.  All dependent identity fields equal the physical target files.

## 7. Runtime preservation, overhead, and claim ceiling

The parent and target retain exact mode-`100644` runtime objects:

| Object | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| runtime schema | `4d0c93f7fea77fec649ff2a9ab4168f1a340a3cf` | `47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896` | 23,762 |
| runtime maximal witness | `51a03242b7ef667a4bd4275d8565122f49222674` | `5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42` | 4,439,071 |

Verifier source grows by 1,922 permanent bytes, static closure changes identity
at unchanged size, and cache authority grows by 221 bytes: a +2,143-byte
source/static/authority subtotal.  Root and provenance documentation are
separate governance overhead.  A future successful ninth-component physical
read adds exactly 11,379 bytes to the existing `filesystem_bytes_read` ledger;
no runtime observation occurred here.

Scientific algorithmic core is zero lines; governance verifier support is 38
net lines, for a 0:38 scientific-core/support-code ratio.  No scientific
evidence was gained.  Nothing was syntax-checked, imported, compiled, built,
tested, executed, or independently reproduced at runtime.

Performance status is `PERFORMANCE_NOT_YET_MEASURED`.  There is no scientific
hot path, timed region, instrumentation measurement, SOTA comparison, or fair-
comparison delta.  Cache-verifier/PAR readiness, PREP, CACHE-BIND, PAR-R1,
SRUN, whole-host identity, and unknown downstream blockers remain excluded.

## 8. Terminal decision and next checkpoint

All frozen checks pass with zero findings at LOW severity or above.  No
repository workload or additional subagent was started by this reviewer, and
no review process remains active.  The only next action is to commit and push
this exact three-path review, perform the mandatory Meeting Summary Handoff,
and return to the user checkpoint.  No execution or downstream authorization
follows from this static PASS.

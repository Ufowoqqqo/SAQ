# A4-V2 SOURCE-HISTORY-I-R1-P independent review

Date: 2026-07-18
Stage: `A4-V2-SOURCE-HISTORY-I-R1-P`
Reviewed target: `150e5b38aa5b3e30dafe4e15632db5fb5add4a68`
Reviewed tree: `29fa489d25a348997bb1eadeb5208dabd1717e0d`
Direct parent: `e98a3e401639cae4f11ea97d21883120e9b797fb`
Reviewer: sole direct-child independent static reviewer

## Verdict and findings

`PASS`

The exact conditional documentation-only outcome is:

```text
SOURCE_HISTORY_I_R1_PATH_CLOSURE_ERRATUM_REVIEW_PASS
```

| Severity | Count | Exact locations |
| --- | ---: | --- |
| BLOCKER | 0 | none |
| HIGH | 0 | none |
| MEDIUM | 0 | none |
| LOW | 0 | none |

The verdict becomes durable only after this exact three-path review is
committed and pushed.  It grants no implementation or execution authority.

## 1. Method, boundary, and stop rule

The falsifiable question was whether the additive erratum corrects only the
unsatisfiable future changed-path projection while leaving every original
epoch, source, runtime, overhead, review, and claim boundary exact.

I used only read-only Git, SHA-256, byte-count, `jq`, and targeted text
inspection.  I did not run Python, a schema validator, build, test, verifier,
PREP, probe, CACHE-BIND, PAR, data, quarantine, host mutation, or any
repository executable.  Any LOW-or-higher issue, identity mismatch, filler
delta, tenth component, or need for execution was a mandatory FAIL.  None was
found.

## 2. Git and exact target projection

At review start, the explicit worktree was clean on
`saq-arbitrary-cardinality-feasibility-v2`; HEAD and the remote-tracking ref
both equalled the full reviewed target.  Its parent tree independently
recomputed to `dfc5df62443618c4af18391d25d28d5321c096de`.

The target changes all and only four mode-`100644` paths:

| Path | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `AGENTS.md` | `ff60f58b1b0d96e5a36dd4a2c3838d0573b05eee` | `b66fa570d5485421e6e3faa3f4646f48d6ba6f4a87214a1f1eed8697fa98ee52` | 47,671 |
| `TASK.md` | `be26da4657ed64b3f38de44485130a98dca89770` | `6481802d525f5f9c8728e13f451742f271fb2e39d845b7112d7cc108940eb22b` | 42,601 |
| `docs/saq_a4_v2_source_history_i_r1_path_closure_erratum_contract_2026_07_18.json` | `d7527a5576d25ba72cf390b8b28748bf28beca3d` | `ea4412c35cbf087f251b62e7877bdfe75cc72343f9c2106ea6b1646f4c531ee2` | 7,410 |
| `docs/saq_a4_v2_source_history_i_r1_path_closure_erratum_protocol_2026_07_18.md` | `2c0131a93b554f155a4e444bdd35fc3eba823eb2` | `f797d10b9a9ae3d7ad02000f6804858572bb6166b36564c797420b2c1493d3e3` | 10,684 |

The projection is 453 additions and two deletions, with no source change and
no whitespace defect.  Protocol section 6 and contract `erratum_review`
agree that this direct-child review may change only `AGENTS.md`, `TASK.md`,
and this memo, all mode `100644`.

## 3. Immutable original authority

The original target/review chain is exact: `dcaed57...` is a direct child of
`e10bde7...`; `e98a3e4...` is a direct child of `dcaed57...`; this erratum is
a direct child of `e98a3e4...`.

| Original object | Commit | Git blob | SHA-256 | Bytes |
| --- | --- | --- | --- | ---: |
| protocol | `dcaed57aaae6fe0f120377281921b6ea5336eb7f` | `2297c34e227a1ad7fe21d15b2674a4987e44e858` | `289e0acb8c1e8122e027fad1757f9fcc6b721ccf49affebce1141f51adfe2650` | 16,130 |
| contract | `dcaed57aaae6fe0f120377281921b6ea5336eb7f` | `9c08aaf63d1e524cfa3579a764fd8ea14176cde8` | `d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48` | 11,379 |
| review | `e98a3e401639cae4f11ea97d21883120e9b797fb` | `d59a56082c52eec113856eb33e918999415f6201` | `58bf7a3deb89e1ba9ab0bbe63c6f66e96d1abf6c44d2c7e47189bd38388c627e` | 13,478 |

These bytes remain unchanged.  Erratum protocol section 4 and contract
`supersession.supersedes_only` replace only the ten-path projection, the
seven-derived-object count, and the old review's ten-path necessity claim.

## 4. Original ten-path requirement is unsatisfiable

Original protocol lines 197--214 and original contract
`future_implementation.exact_target_changed_paths` require ten changed paths.
Original review lines 182--204 repeats that all seven derived objects are
necessary.  The only unsupported paths are:

- `docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json`; and
- `docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json`.

The correction changes internal expected-map selection for existing history
roles and adds one identity check through the existing component loop.  It
adds no result field, status, parser, observation, role, retry, cap, timer, or
ledger field, so neither runtime object's represented shape changes.

The schema already fixes 37 generic `source_checks`, permits root `PASS` and
`MISMATCH`, permits up to 256 generic mismatches, and types
`filesystem_bytes_read` through the existing `uint64` definition.  Its exact
identity is SHA-256
`47bfcd039acddebbf9c6e5058b1c20ca9a743a5d2518ff31d4fef72ae103f896`,
23,762 bytes, Git blob `4d0c93f7fea77fec649ff2a9ab4168f1a340a3cf`.

The maximal witness already contains 37 generic maximal source records, 256
mismatches, and `filesystem_bytes_read=18446744073709551615`.  It contains no
epoch, source-history, or protocol-component key or value.  Its exact identity
is SHA-256
`5a373bd002b48041e150588002a193a9c068cf98977897e6f5cc5f3339e71a42`,
4,439,071 bytes, Git blob `51a03242b7ef667a4bd4275d8565122f49222674`.

Both blobs are identical at the original protocol target, its review parent,
and this erratum target.  A comment, new field, or maximal filler added only
to force a delta would violate the frozen semantic boundary.  Therefore the
ten-path all-must-change projection cannot be satisfied legitimately.

## 5. Corrected eight-path cascade

Protocol section 5 and contract `future_implementation_target` agree on all
and only these future mode-`100644` paths:

1. `AGENTS.md`;
2. `TASK.md`;
3. `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json`;
4. `docs/saq_a4_v2_cache_static_closure_2026_07_15.json`;
5. `docs/saq_a4_v2_implementation_binding_2026_07_14.md`;
6. `docs/saq_a4_v2_implementation_manifest_2026_07_14.json`;
7. `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md`; and
8. `script/a4_v2_cache_policy_verifier.py`.

The one source edit changes its own identity and the 37-source tree.  The five
necessary derived objects are exactly: static closure; cache authority;
implementation binding; source-provenance crosswalk; and implementation
manifest.  They respectively close the changed source/tree, static-closure
and component identity, protocol/review authority, provenance, and dependent
whole-document identities.  The two root paths record state.  This is both
necessary and sufficient; runtime schema and witness are consumers of no
changed shape or identity.

## 6. Preserved original mechanics

The role assignment remains disjoint and observation-independent: four legacy
roles and six active roles, with exactly one epoch per non-null role.  The five
legacy overrides remain exact:

| Path | Legacy Git blob |
| --- | --- |
| `script/a4_v2_cache_policy_verifier.py` | `6f4f6c2afc963066c3eb1a0dc053b4987ee70337` |
| `script/a4_v2_isolated_clone_prep.py` | `884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7` |
| `script/a4_v2_runner.py` | `4c0e35855fb8d51223f133fa75f00eeb983de49d` |
| `script/a4_v2_verifier.py` | `4d5964ed1996c8aceb202191b6bf48b78b23a94c` |
| `script/run_arbitrary_cardinality_a4_v2.py` | `69d0ba6734c9fe9435b4dccaf8990cc60cf2dbbe` |

Either-epoch acceptance, observed-byte inference, ancestry/date/branch/host
selection, and warning downgrade remain forbidden.  Current closure,
`kind=blob`, statuses, parser, one observation per non-null role, caps,
ledger increments, precedence, retries, and null skips remain unchanged.

The current source has eight component keys at verifier lines 328--338, their
eight exact paths at lines 568--593, and one existing `_check_identity` loop
at lines 2805--2812.  The sole ninth component remains:

```text
source_history_epoch_correction_contract
docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json
```

The erratum and its contract are not components.  A tenth component, alias,
filler object, new parser/status/output/observation/ledger behavior, or second
source file is forbidden.  The semantic-core estimate remains approximately
25--45 changed logical verifier lines, with a hard stop above 80 net lines.

## 7. Overhead, agreement, and ceiling

The original overhead remains at most five deterministic map overrides and
one preassigned-map selection per non-null role, with no new Git observation
or source read.  The ninth component adds one existing-loop identity check;
physical success adds the immutable 11,379-byte contract length to the
existing filesystem-read ledger.  This is governance overhead only.

The prose and JSON agree on authority, stage, identities, four-path target,
three-path review, blocker, two preserved runtime blobs, eight-path/five-
derived-object replacement, original clauses, separate future authorization,
prohibitions, and outcome.  No tenth component or filler route exists.

Scientific evidence gained: none.  Implementation/support-code ratio: zero
implementation lines to zero support-code lines; all target and review changes
are governance documentation.  Nothing compiled, ran, or was reproduced by
execution.  Performance remains `PERFORMANCE_NOT_YET_MEASURED`; there is no
scientific hot path, timed region, SOTA comparison, or fair-comparison delta.

No repository workload or additional subagent was started by this reviewer,
and no review process remains active.  Fresh PREP lineage, CACHE-BIND DAG,
PAR-R1, whole-host identity, and unknown blockers remain excluded.

## 8. Terminal decision

All eight frozen checks pass with zero LOW-or-higher findings.  The erratum is
bounded, necessary, and sufficient for this path-closure defect only.  The
next action is limited to committing and pushing this exact three-path review,
performing the mandatory Meeting Summary Handoff, and returning to the user
checkpoint.  Do not form the eight-path source target without explicit
`A4-V2-SOURCE-HISTORY-I-R1` authorization.

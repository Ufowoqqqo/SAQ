# A4-V2 source-history epoch-correction protocol independent review

Date: 2026-07-17

Stage: `A4-V2-SOURCE-HISTORY-P`

Reviewed immutable target:
`dcaed57aaae6fe0f120377281921b6ea5336eb7f`

Reviewed tree: `d0069768c8848327f04a23b444fae0b635eb2d78`

Direct parent: `e10bde78eff21802301549e4c796cc3f49c9d32b`

Reviewer role: sole direct-child independent static reviewer

## Verdict

`PASS`

The exact conditional protocol-only outcome is:

```text
SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS
```

This outcome becomes durable only after this exact three-path review is
committed and pushed.  It authorizes no source correction, derived-authority
edit, Python or repository execution, PREP, CACHE-BIND, PAR, data access, or
scientific claim.  A future source-static target still requires a new explicit
instruction naming `A4-V2-SOURCE-HISTORY-I`.

| Severity | Count | Locations |
| --- | ---: | --- |
| BLOCKER | 0 | none |
| HIGH | 0 | none |
| MEDIUM | 0 | none |
| LOW | 0 | none |

## 1. Review question, method, and stop condition

The smallest falsifiable question was whether the immutable protocol gives the
known `SOURCE_HISTORY_MISMATCH` one closed, role-preassigned two-epoch rule
that preserves both immutable legacy evidence and the active 37-source
closure, without an either-epoch/adaptive allowlist and without expanding the
future repair beyond the minimum deterministic identity cascade.

I reviewed the immutable target, its parent, exact path/mode projection, the
protocol and contract, the existing verifier source-history implementation,
the four named legacy commits, and the active parent.  Read-only Git, text,
hash, byte-count, and machine-contract inspection was sufficient.  I did not
run Python, import or compile source, invoke a verifier or repository
executable, access PREP/CACHE-BIND/PAR/data/quarantine state, or mutate the
host.

The stop condition was any LOW-or-higher defect, identity inconsistency,
unexpected path or mode, adaptive epoch selection, incomplete legacy closure,
loss of an existing fail-closed check, unjustified future path, or need for
execution.  None occurred.

## 2. Target Git, path, mode, and identity closure

The reviewed target was clean and equal to
`origin/saq-arbitrary-cardinality-feasibility-v2` at review start.  Its sole
parent and independently recomputed parent tree were:

| Object | Identity |
| --- | --- |
| target commit | `dcaed57aaae6fe0f120377281921b6ea5336eb7f` |
| target tree | `d0069768c8848327f04a23b444fae0b635eb2d78` |
| direct parent | `e10bde78eff21802301549e4c796cc3f49c9d32b` |
| parent tree | `d1d09123d46b25229388052620c8ac1b19ab679c` |

The target changes all and only the following four mode-`100644` paths:

| Path | Git blob | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `AGENTS.md` | `240755d03757e12907ab4eda8ed7dd47ba11e763` | `94d67c0414b48b72b345993401eb3aa30f5324b6c8e9a47fd245f4b896492521` | 45,026 |
| `TASK.md` | `fc1e344c49c74a9b86318ab75ce935dc93113ebf` | `a50435d74684d2f11e7d740da70a0540aaae553bc6788d352b49a8a40317b370` | 39,972 |
| `docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json` | `9c08aaf63d1e524cfa3579a764fd8ea14176cde8` | `d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48` | 11,379 |
| `docs/saq_a4_v2_source_history_epoch_correction_protocol_2026_07_17.md` | `2297c34e227a1ad7fe21d15b2674a4987e44e858` | `289e0acb8c1e8122e027fad1757f9fcc6b721ccf49affebce1141f51adfe2650` | 16,130 |

The target contains 419 insertions and no source edit.  The protocol and
machine contract agree on the stage, target/review closures, epochs, roles,
overrides, future delta, line ceiling, overhead, exclusions, and claim
ceiling.

## 3. Current single-active-map mismatch reproduced statically

At both target and parent,
`script/a4_v2_cache_policy_verifier.py:3584`--`:3594` constructs one ordered
ten-entry `history_commits` list.  Lines `3596`--`3598` then construct one
`expected_source_blobs` map from the active cache authority.  Lines
`3599`--`3607` correctly apply that active map to the current tree, but lines
`3608`--`3639` reuse the same active map for every non-null historical role.

Therefore each of the following four immutable legacy commits is guaranteed
to report `SOURCE_HISTORY_MISMATCH`: all five listed legacy blobs differ from
the active map, while the current loop offers no role-specific epoch.

| Legacy role | Full commit |
| --- | --- |
| CACHE-I target | `c33a2bff7e0ec9c98596498fd43a7e629ccf47fe` |
| CACHE-I review | `5db302537793bc05f541aede119255213ea49e14` |
| original PREP-authorization target | `e7f940e924a338022bfe8fffcbb3496f12a5a75c` |
| original PREP-authorization review | `16a8201ac36e6c8c514848d55ad5ef607eb053b9` |

Each legacy commit differs from the active target parent in all and only these
five paths under `research/` and `script/`; the other 32 active-authority
source paths are preserved.

| Source path | Legacy Git blob | Active Git blob | Legacy SHA-256 | Active SHA-256 | Legacy / active bytes |
| --- | --- | --- | --- | --- | ---: |
| `script/a4_v2_cache_policy_verifier.py` | `6f4f6c2afc963066c3eb1a0dc053b4987ee70337` | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,371 / 151,568 |
| `script/a4_v2_isolated_clone_prep.py` | `884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7` | `d671531132eb0c490dec1953ca778e8d03913b3d` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 / 219,758 |
| `script/a4_v2_runner.py` | `4c0e35855fb8d51223f133fa75f00eeb983de49d` | `44e1a8078caf8774d1005f88265c87167e462eb7` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 / 360,127 |
| `script/a4_v2_verifier.py` | `4d5964ed1996c8aceb202191b6bf48b78b23a94c` | `d8e0bdc6df0865e95dfe631446d108368640e25d` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 / 250,023 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `69d0ba6734c9fe9435b4dccaf8990cc60cf2dbbe` | `21925cddb4d07a1ec046d405493980813a4d581a` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 / 34,929 |

The independently recomputed canonical source-tree identities are:

| Epoch | Sources / units / native / Python | Canonical source-tree SHA-256 |
| --- | --- | --- |
| legacy | 37 / 38 / 27 / 10 | `9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2` |
| active | 37 / 38 / 27 / 10 | `97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a` |

The corresponding 218,872-byte static closures are legacy blob
`dc26a0bc2c18b743f9d8b98ffed9f30586aeae4f`, SHA-256
`f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0`,
and active blob `1c58d4bc2f6bb602822ce11cc7b0f0800af7aeee`, SHA-256
`815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d`.
This proves an artifact-versioning mismatch, not source corruption or a host,
cache-policy, or scientific result.

## 4. Exact role partition and fail-closed semantics

The contract assigns exactly four roles to `LEGACY_PRE_HOST_REBIND`:

- `cache_i_target_commit`;
- `cache_i_review_commit`;
- `prep_authorization_target_commit`; and
- `prep_authorization_review_commit`.

It assigns exactly six roles to `ACTIVE_CORRECTED_SOURCE`:

- `prep_receipt_target_commit`;
- `prep_receipt_review_commit`;
- `cache_bind_target_commit`;
- `cache_bind_review_commit`;
- `par_target_commit`; and
- `par_review_commit`.

The sets are disjoint, their union is the exact ten-role sequence, and every
non-null role has exactly one assignment before observing that commit's tree.
Null roles retain the existing skip behavior.  The legacy map is the active
37-source map with exactly the five closed overrides above; it consequently
preserves the other 32 source expectations.

The protocol explicitly rejects accepting either epoch, inferring an epoch
from observed bytes, or selecting by ancestry, date, tag, branch, filesystem,
host state, or outcome.  It also forbids warning downgrade.  A wrong blob in
the preassigned epoch remains `SOURCE_HISTORY_MISMATCH`.

## 5. Existing checks preserved

The future semantic delta leaves the current-source active closure at
`script/a4_v2_cache_policy_verifier.py:3599`--`:3607` unchanged.  It also
preserves:

- `SOURCE_HISTORY_UNAVAILABLE` and `SOURCE_HISTORY_MISMATCH` status semantics;
- the full-tree parser at lines `1958`--`1987`, including relative paths,
  full OIDs, allowed modes, `kind=blob`, uniqueness, and nonempty output;
- the existing single Git observation per non-null role at lines
  `3611`--`3621`, its 300-second timeout, and the 8,388,608-byte stdout/stderr
  cap at lines `1765`--`1786`;
- the existing stdout/stderr ledger increments at lines `3623`--`3624`; and
- current failure precedence, retry behavior, null-role skips, and mismatch
  collection.

No new parser, status, Git observation, output, timer, retry, history role, or
ledger field is permitted or needed.

## 6. Future delta is necessary, sufficient, and bounded

For this mismatch only, the separately authorized future target changes one
source file plus the complete deterministic identity cascade, all mode
`100644`:

1. `AGENTS.md`;
2. `TASK.md`;
3. `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json`;
4. `docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json`;
5. `docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json`;
6. `docs/saq_a4_v2_cache_static_closure_2026_07_15.json`;
7. `docs/saq_a4_v2_implementation_binding_2026_07_14.md`;
8. `docs/saq_a4_v2_implementation_manifest_2026_07_14.json`;
9. `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md`; and
10. `script/a4_v2_cache_policy_verifier.py`.

The one source edit is necessary to replace the current single-active-map
history assumption.  The seven authority/document edits are exactly the
identity cascade caused by that source edit and the new protocol component;
the two root files record state.  No second source, schema version escape,
new manifest key, runtime-discovered path, or additional derived object is
necessary for this defect.

The current verifier has exactly eight protocol components at lines
`328`--`338`, exact paths beginning at line `568`, and one existing sorted
identity-check loop at lines `2805`--`2812`.  The future delta admits exactly
one ninth component:

| Field | Frozen value |
| --- | --- |
| key | `source_history_epoch_correction_contract` |
| path | `docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json` |
| current target identity | SHA-256 `d8150681aa9d7116d1d131ca61f9a027ea737b3a6245bf8ee2e000b88548ea48`, 11,379 bytes, Git blob `9c08aaf63d1e524cfa3579a764fd8ea14176cde8` |

The expected verifier semantic core is 25--45 changed logical lines.  More
than 80 net verifier lines, a second source file, or a new
status/parser/Git-observation mechanism is a mandatory stop.

## 7. Overhead, exclusions, and claim ceiling

The future role check adds at most five deterministic dictionary overrides and
one preassigned map lookup per non-null history role.  It adds no Git
observation or source read.  The ninth component adds one invocation of the
existing identity-check loop; on physical success the existing
`filesystem_bytes_read` aggregate increases by exactly the committed
contract's byte length.  Permanent source/authority byte delta and observed
ledger delta must be reported separately.  This nonzero work is governance
overhead, not scientific construction work.

Scientific algorithmic core added by the protocol is zero lines.  The
implementation/support ratio is therefore 0 scientific lines to all protocol
and guard lines.  Performance status is `PERFORMANCE_NOT_YET_MEASURED`; there
is no scientific hot path, timed region, SOTA comparison, or fair-comparison
delta in this documentation-only review.

The protocol correctly leaves outside scope the stale original PREP authority
and superseded probe, a fresh PREP lineage, CACHE-BIND schema/DAG questions,
PAR-R1 authorization, whole-host identity, and unknown future blockers.  It
forbids history rewriting, old-commit replacement, source or authority edits
in this stage, untracked/WIP evidence, host mutation, execution, and any
readiness, feasibility, performance, systems, novelty, SAQ-limitation, or
method claim.

## 8. Terminal review decision

All nine frozen review checks pass with zero findings at LOW severity or
above.  The protocol is necessary and sufficient to specify one future static
repair for the known epoch mismatch, and it is bounded tightly enough to
prevent an adaptive history allowlist or broader lineage repair.

No scientific evidence was produced.  Nothing was imported, compiled, built,
tested, or independently reproduced by execution.  No repository workload or
additional subagent was started by this reviewer, and no review process
remains active.  The next and only current action is to commit and push this
exact three-path review, perform the mandatory Meeting Summary Handoff, and
return to the user checkpoint.  Do not form or execute the future ten-path
source target without explicit `A4-V2-SOURCE-HISTORY-I` authorization.

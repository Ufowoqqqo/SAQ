# A4-V2 bounded source-history epoch correction protocol

Date: 2026-07-17

Stage: `A4-V2-SOURCE-HISTORY-P`

Authority: the user's exact instruction
`授权 bounded SOURCE_HISTORY_MISMATCH correction protocol + direct-child review`.

## 1. Smallest question, scope, and ceiling

The smallest falsifiable question is whether the known
`SOURCE_HISTORY_MISMATCH` can be given one finite, fail-closed correction rule
that preserves immutable old source snapshots and the active reviewed source
closure, without turning the history check into an "old or new" allowlist and
without executing the verifier.

This stage is documentation-only.  It forms this protocol, its machine
contract, focused root status, one immutable target, and one exact direct-child
independent review.  It does not edit the cache verifier or any derived
authority.  With zero findings at LOW severity or above, its maximum outcome
is:

```text
SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS
```

That verdict does not repair source, execute or validate the cache verifier,
establish PREP/CACHE-BIND/PAR readiness, or provide feasibility, performance,
SAQ-limitation, novelty, or method evidence.

## 2. Immutable defect and exact observations

At reviewed head `e10bde78eff21802301549e4c796cc3f49c9d32b`,
`script/a4_v2_cache_policy_verifier.py` constructs one
`expected_source_blobs` map from the active cache authority and applies that
same map to every non-null member of this ten-role history sequence:

```text
cache_i_target_commit
cache_i_review_commit
prep_authorization_target_commit
prep_authorization_review_commit
prep_receipt_target_commit
prep_receipt_review_commit
cache_bind_target_commit
cache_bind_review_commit
par_target_commit
par_review_commit
```

The current-source check is correct: the execution-base tree must match the
active 37-source authority exactly.  The defect is only the assumption that
all registered historical commits must also match the current source epoch.
Four immutable, independently reviewed pre-rebind commits correctly contain
the old source epoch:

| Role | Commit | Required epoch |
| --- | --- | --- |
| CACHE-I target | `c33a2bff7e0ec9c98596498fd43a7e629ccf47fe` | `LEGACY_PRE_HOST_REBIND` |
| CACHE-I review | `5db302537793bc05f541aede119255213ea49e14` | `LEGACY_PRE_HOST_REBIND` |
| original PREP authorization target | `e7f940e924a338022bfe8fffcbb3496f12a5a75c` | `LEGACY_PRE_HOST_REBIND` |
| original PREP authorization review | `16a8201ac36e6c8c514848d55ad5ef607eb053b9` | `LEGACY_PRE_HOST_REBIND` |

Read-only Git inspection establishes that those four commits have the same
five old source blobs below.  The current reviewed head has the five rebound
blobs, and `git diff --name-only c33a2bf..e10bde7 -- research script` names
all and only these five source paths.

| Source path | Legacy Git blob | Reviewed-head Git blob | Legacy SHA-256 | Reviewed-head SHA-256 | Bytes |
| --- | --- | --- | --- | --- | ---: |
| `script/a4_v2_cache_policy_verifier.py` | `6f4f6c2afc963066c3eb1a0dc053b4987ee70337` | `9ace42bb7c8d856e6b93c9836fb0c9732c169a37` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | `bd2a75beae4619beec34f37f3d5788caf71fdf2634fb0d864c358c9a29caa5e1` | 151,371 / 151,568 |
| `script/a4_v2_isolated_clone_prep.py` | `884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7` | `d671531132eb0c490dec1953ca778e8d03913b3d` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | `823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2` | 219,758 |
| `script/a4_v2_runner.py` | `4c0e35855fb8d51223f133fa75f00eeb983de49d` | `44e1a8078caf8774d1005f88265c87167e462eb7` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | `a59de1f673b16f13f87dc5682a608387ab1747c00d4a0d2db1d8d616ea037662` | 360,127 |
| `script/a4_v2_verifier.py` | `4d5964ed1996c8aceb202191b6bf48b78b23a94c` | `d8e0bdc6df0865e95dfe631446d108368640e25d` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | `425a7853198bffe2fb612f999a1bbbb3ea67ac4e7c4f16b6b182604cee87d5e5` | 250,023 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `69d0ba6734c9fe9435b4dccaf8990cc60cf2dbbe` | `21925cddb4d07a1ec046d405493980813a4d581a` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | `e11f5a62542f843cede94837cd73681cf713aa0700fb7c8bfdf2dcd07204fb2b` | 34,929 |

For the cache-policy verifier row only, the two byte counts are respectively
legacy and reviewed-head sizes.  Every other row has equal legacy and current
size despite different bytes.

The legacy canonical 37-source-tree SHA-256 is
`9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2`.
The active HOST-I source-tree SHA-256 is
`97f676357e6f8916a570ba28b7dabcdb358d7138f4485e7ca005a5e746a5e07a`.
The legacy and active static-closure objects are both 218,872 bytes and have
the following immutable identities:

| Epoch | Static-closure Git blob | Static-closure SHA-256 |
| --- | --- | --- |
| legacy at `c33a2bf` | `dc26a0bc2c18b743f9d8b98ffed9f30586aeae4f` | `f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0` |
| active at `e10bde7` | `1c58d4bc2f6bb602822ce11cc7b0f0800af7aeee` | `815478c1b6a22f4871c2e82c341f0c0d417de4014f19cc794ae3b3c44cf3776d` |

This is an artifact-versioning defect.  It is not source corruption, host
drift, a cache-policy result, or scientific evidence.

## 3. Frozen correction: one epoch per commit role

A separately authorized future source correction must retain the current
37-source check unchanged and replace only the history comparison rule with
an exact two-epoch assignment.

### 3.1 Legacy epoch

The exact four roles listed below must use
`LEGACY_PRE_HOST_REBIND`, never a value selected by observed bytes:

```text
cache_i_target_commit
cache_i_review_commit
prep_authorization_target_commit
prep_authorization_review_commit
```

The expected legacy map is the future active 37-source blob map with all and
only the five paths in section 2 overridden by their exact legacy Git blobs.
The override key set must equal that five-path set, and every key must already
exist in the active 37-source map.  The other 32 expected blobs come from the
future active authority and therefore remain exact and closed.

### 3.2 Active epoch

The following six future roles must use `ACTIVE_CORRECTED_SOURCE`, derived
only from the future active cache authority:

```text
prep_receipt_target_commit
prep_receipt_review_commit
cache_bind_target_commit
cache_bind_review_commit
par_target_commit
par_review_commit
```

Null roles retain the existing skip semantics.  Every non-null role must be
checked against exactly one assigned epoch.  It is forbidden to accept a
commit when it matches either epoch, to infer an epoch from the observed tree,
to select by commit ancestry ranges, dates, tags, branch names, filesystem
state, host RPM state, or outcome, or to downgrade a mismatch to a warning.

The existing `SOURCE_HISTORY_UNAVAILABLE` and `SOURCE_HISTORY_MISMATCH`
statuses, Git tree parser, kind=`blob` requirement, observation caps, ledger
increments, failure precedence, and retry behavior remain unchanged.  A
wrong blob in either epoch must still produce `SOURCE_HISTORY_MISMATCH`.

## 4. Exact separately authorized future source delta

This protocol does not implement the correction.  Only after target/review
publication, Meeting Summary Handoff, zero LOW-or-higher findings, and a new
user instruction naming exactly

```text
A4-V2-SOURCE-HISTORY-I
```

may a future target edit source.

The only implementation source permitted to change is:

```text
script/a4_v2_cache_policy_verifier.py
```

Its semantic delta is limited to:

1. one closed five-entry legacy Git-blob override constant;
2. one closed four-role legacy epoch assignment and one closed six-role active
   epoch assignment;
3. construction of the legacy expected map from the active map plus the five
   overrides;
4. selection of the preassigned map inside the existing history loop; and
5. admission of this protocol's machine contract as exactly one ninth
   protocol component.

The ninth component key and path are frozen as:

```text
source_history_epoch_correction_contract
docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json
```

The future cache authority must retain the existing eight components
byte-for-byte by identity and add exactly this ninth identity, computed from
the immutable protocol target.  The verifier may add the key once to
`PROTOCOL_COMPONENT_KEYS` and the exact key/path mapping once to
`PROTOCOL_COMPONENT_PATHS`.  No tenth component, alias, wildcard, prefix,
fallback, schema version escape, alternate path, or runtime discovery is
allowed.

The expected verifier semantic core is approximately 25--45 changed logical
lines.  More than 80 net changed lines in that source, a second source file,
or a new status/parser/Git-observation mechanism is a stop condition requiring
another protocol and explicit authorization.

## 5. Frozen future target and review closure

The future implementation target must be the direct child of the clean,
pushed, publication-closed review head of this protocol.  It changes all and
only these ten mode-`100644` paths:

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
```

The seven derived authority/document paths are the complete deterministic
identity cascade from the one source change and ninth component.  The binding
and crosswalk must register this exact protocol target and its committed
review identity.  The implementation manifest must preserve its schema and
continue to use its existing `authorization_identity`; no new manifest key is
allowed.  `build_status` remains `NOT_AUTHORIZED_NOT_RUN`.

The future direct-child implementation review changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_source_history_epoch_correction_implementation_independent_review_2026_07_17.md
```

Before that review, the maximum status is
`SOURCE_HISTORY_EPOCH_CORRECTION_TARGET_FORMED_REVIEW_PENDING`.  With zero
LOW-or-higher findings, the maximum future result is only:

```text
SOURCE_HISTORY_EPOCH_CORRECTION_SOURCE_STATIC_REVIEW_PASS
```

It means the one known history rule has a reviewed static correction.  It is
not execution, cache-verifier PASS, PREP/CACHE-BIND/PAR readiness, or a
scientific result.

## 6. Preserved closure and overhead ledger

The future source inventory remains exactly 37 filesystem sources, 38
executable units, 27 native/CMake sources, and 10 Python sources.  All 36
other source files remain byte-identical.  The canonical active source-tree
identity, source SHA-256, sizes, Git blobs, and all seven derived-object
identities must be recomputed from the immutable future target; this protocol
does not predict them.

The epoch correction does not add a Git observation, filesystem-source read,
history role, retry, output, timer, or ledger field.  Relative to the existing
history loop it adds at most five deterministic dictionary overrides and one
preassigned epoch selection per non-null role.  This CPU cost is governance
verification work and must not be called zero or scientific construction
work.

The ninth protocol component adds exactly one invocation of the existing
protocol-component `_check_identity` loop.  On physical success the existing
`filesystem_bytes_read` aggregate increases by the exact byte length of the
committed contract.  Existing fallback Git stdout/stderr accounting and
mismatch semantics apply unchanged.  The future target must report the exact
contract identity, permanent source/authority byte delta, and any observed
verification-ledger delta separately from scientific construction, query,
index, and performance work.

Scientific algorithmic core added by this protocol is zero lines.  All
protocol, derived-authority, review, and verifier-guard work is supporting
artifact governance and cannot establish paper viability.

## 7. Current protocol target and direct-child review

This protocol target must be the direct child of clean, pushed head
`e10bde78eff21802301549e4c796cc3f49c9d32b` with tree
`d1d09123d46b25229388052620c8ac1b19ab679c`, and changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_source_history_epoch_correction_protocol_2026_07_17.md
docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json
```

Its direct-child independent review changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_source_history_epoch_correction_protocol_independent_review_2026_07_17.md
```

The reviewer may record PASS or FAIL but may not edit either protocol object.
The review must independently establish:

1. exact parent, path/mode projections, immutable target, push, and clean
   tracking equality;
2. the current verifier's single-active-map history semantics and guaranteed
   mismatch against the four legacy commits;
3. exact five-path old/current source closure and all ten full commit/blob
   identities rather than abbreviations;
4. all-and-only assignment of four roles to the legacy epoch and six roles to
   the active epoch;
5. rejection of per-commit "either epoch" matching and every adaptive epoch
   selection rule;
6. preservation of current-source closure, kind checks, statuses, parser,
   observation count, caps, ledgers, and failure precedence;
7. necessity and sufficiency of the one-source, ten-path future target and
   one ninth-component admission for this mismatch only;
8. complete overhead disclosure and every claim ceiling/prohibition; and
9. explicit exclusion of all other PREP/CACHE-BIND/PAR lineage or execution
   questions.

Any finding at LOW severity or above forces a protocol-review FAIL and user
checkpoint.  Commit, push, and mandatory Meeting Summary Handoff are allowed;
they grant no implementation or execution authority.

## 8. Excluded blockers and prohibitions

This protocol corrects only the source-history comparison model.  It does not
repair or validate the stale original PREP authority, its superseded probe,
future PREP authorization lineage, CACHE-BIND schema/DAG requirements,
PAR-R1 authorization, host dependencies outside the registered 13-object
bundle, or any other static/runtime issue.  Even a future source-static PASS
would remove only this known blocker; all remaining prerequisites require
their own inspection, protocol, authorization, review, and where appropriate
execution.

Neither this protocol nor its review permits:

- any edit to existing Python, native/CMake, schema, witness, authority,
  manifest, binding, crosswalk, HOST-P/HOST-I/R1, or historical PREP object;
- rewriting, amending, reverting, force-pushing, relabeling, or replacing any
  immutable old commit or old source snapshot;
- Python, DNF, syntax, import, compiler, build, test, fixture, RNG, repository
  executable, cache-verifier, PREP, probe, clone, START, token, capture,
  receipt, CACHE-BIND, PAR-R1, SRUN, or data execution;
- quarantine enumeration/read/stat/hash/copy/cleanup, dataset/query/index/
  result access, or environment/host mutation;
- accepting untracked or WIP content as evidence; or
- readiness, feasibility, performance, systems, novelty, SAQ-limitation, or
  method claims.

The old PREP invocation authority remains nontransferable and its old probe
remains superseded and must never run or be reused.

## 9. Stop rule and user checkpoint

This stage stops after protocol target/review commit, push, Meeting Summary
Handoff, and user report, or earlier on any LOW-or-higher finding, dirty or
unpublished parent, unexpected path/mode, identity inconsistency, need for
source execution, or inability to preserve a unique epoch per commit role.
Even after PASS, do not form the ten-path source target without explicit
`A4-V2-SOURCE-HISTORY-I` authorization.

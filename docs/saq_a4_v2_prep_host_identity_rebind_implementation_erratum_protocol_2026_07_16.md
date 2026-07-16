# A4-V2 PREP host-identity implementation erratum protocol

Date: 2026-07-16
Stage: `A4-V2-PREP-HOST-I-ERRATUM`
Authority: exact user instruction `授权 A4-V2-PREP-HOST-I-ERRATUM`

Maximum outcome after a committed direct-child independent review with zero
findings at LOW severity or above:

```text
HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
```

This is an additive artifact-governance correction.  It is not
`HOST_IDENTITY_REBOUND`, PREP readiness, parity, feasibility, performance, or
scientific evidence.  It authorizes no implementation edit or execution.

## 1. Reason for the erratum

The publication-closed HOST-I authorization contains an internally
unsatisfiable source rule.  It simultaneously requires a future source target
to:

1. make exactly seven active old-to-new CPython leader-digest substitutions
   as its only source semantic delta;
2. preserve the seven historical entries in the cache authority's
   `protocol_components` object; and
3. add the reviewed HOST-P erratum contract as an eighth exact protocol
   component.

The committed cache verifier closes the component schema to exactly the seven
historical keys in `PROTOCOL_COMPONENT_KEYS`, closes their paths in
`PROTOCOL_COMPONENT_PATHS`, and applies `_require_keys` using set equality.
It then iterates over that same closed key set to read and hash each component.
Consequently:

- adding the required eighth authority entry without changing the verifier is
  rejected;
- replacing one of the seven entries violates historical-identity
  preservation and the exact path map; and
- teaching the verifier about the eighth entry is an additional observable
  source, path, verification-work, and evidence-ledger delta that the prior
  AUTH did not permit.

This is a protocol-closure defect, not an implementation result and not
evidence about SAQ or arbitrary-cardinality quantization.  It was found before
any HOST-I file was edited.  No Python, PREP, probe, clone, START, token,
build, data, quarantine, or SAQ/CAQ action occurred.

## 2. Frozen parent and current documentation projections

This erratum target must be the direct child of the clean, pushed, and
publication-closed HOST-I AUTH review head:

```text
commit  71e6bec01dbabaf29333ac75dcd9ef7a238a079d
tree    36f5a2a0a767711010fccbf8ec8eca7696f1a609
parent  212a67b887aa710fed35f66766982db683b3fa63
```

It may add or change exactly these four mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_contract_2026_07_16.json
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_protocol_2026_07_16.md
```

Its direct-child independent review may add or change exactly these three
mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md
```

Every other tracked path and mode must remain identical.  Any need for another
path stops this stage and requires another additive authorization.

## 3. Frozen parent objects

The erratum overlays, but does not rewrite, these reviewed records:

| Object | SHA-256 | Bytes |
| --- | --- | ---: |
| HOST-P protocol | `0cef593b0532070c87be49d3b7b469abe755ff20a072b8bfff915a2bf848289e` | 14,350 |
| HOST-P contract | `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09` | 10,684 |
| HOST-P independent review | `dea30436db0cd1fd031274e6847a4f11e9d84b36d0ec90fc5a32c227be2b9a86` | 6,540 |
| HOST-I AUTH record | `7a07e05eb2b96c7ecd57facf9f1b7405a63f0d6d66d2af3cad3a1eeb626ce3b0` | 11,928 |
| HOST-I AUTH independent review | `bda4f52b549e28b69cca5c012c21e12867266e0c5920eda27f7df87e478d69e9` | 14,740 |
| cache authority | `5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec` | 42,903 |
| cache policy verifier | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | 151,371 |

The cache verifier Git blob is
`6f4f6c2afc963066c3eb1a0dc053b4987ee70337`.  The cache authority contains
exactly these seven historical component keys, all of whose existing
path/SHA-256/size identities must survive a later source target unchanged:

```text
cache_contract
cache_i_authorization
cache_i_authorization_review
cache_p_independent_review
cache_primary_review
cache_primary_sources
cache_protocol
```

## 4. Narrow additive supersession

This erratum supersedes only three future-target clauses of the HOST-I AUTH.

### 4.1 Future source-parent rule

The future fourteen-path HOST-I source target is no longer allowed to be the
direct child of `71e6bec...`.  After this erratum target and its direct-child
review are committed, pushed, and publication-closed, a separately
reauthorized HOST-I target must be the direct child of that unchanged erratum
review head.  The future source review remains the direct child of its exact
source target.

No implementation-parent or PREP execution-base probe is introduced by this
rule.  Ordinary documentation remote equality is publication bookkeeping
only.

### 4.2 Future source-delta rule

The complete permitted future source semantic delta becomes:

1. the same exactly seven old-to-new leader-digest substitutions across the
   same five sources with the frozen `1 + 2 + 2 + 1 + 1` partition; plus
2. one closed eighth-component admission in the already listed
   `script/a4_v2_cache_policy_verifier.py` and no other source change.

The new component key and value are frozen as:

```text
key
  prep_host_identity_rebind_erratum_contract

path
  docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json

sha256
  c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09

size_bytes
  10684
```

The verifier edit is exactly:

- add that key once to `PROTOCOL_COMPONENT_KEYS`; and
- add one mapping entry from that key to that exact path in
  `PROTOCOL_COMPONENT_PATHS`.

The exact inserted source forms are:

```python
        "prep_host_identity_rebind_erratum_contract",

    "prep_host_identity_rebind_erratum_contract": (
        "docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json"
    ),
```

In their registered existing contexts these additions total 197 bytes.  With
the equal-length leader-digest substitution, the future cache-verifier size is
therefore frozen at 151,568 bytes.  Its SHA-256 and Git blob must be recomputed
from the committed target rather than predicted here.

The later cache authority must contain exactly eight protocol components: the
seven frozen historical entries plus this new identity.  The existing
`_require_keys`, normalization, sorted iteration, `_check_identity` call,
fallback-commit rule, mismatch status, error precedence, caps, and ledger
machinery remain byte-identical except for identities that cascade from the
allowed source edits.

No ninth component, generic-object substitution, alternative key, alias,
fallback, wildcard, prefix, version-only rule, or runtime RPM query is
admitted.

### 4.3 Verification-work disclosure

The prior statement that verification/resource behavior remains entirely
unchanged is narrowed.  The eighth entry intentionally causes exactly one
additional invocation of the existing protocol-component `_check_identity`
loop body.  On physical success this adds one bounded read and SHA-256/identity
comparison of the existing 10,684-byte HOST-P contract and increments the
existing aggregate `filesystem_bytes_read` counter by exactly 10,684.  On the
unchanged fallback path, the observed Git payload and stderr lengths
increment the existing `git_stdout_bytes` and `git_stderr_bytes` counters.  A
readable but mismatched physical payload remains counted by its observed
length in `filesystem_bytes_read` before those Git counters are additionally
updated; an absent or unreadable payload adds no filesystem bytes.  An
unavailable or mismatched physical identity records the existing mismatch.
No ledger key or schema entry is added.  The loop body, per-object rules,
caps, status mapping, and failure precedence do not change.

The future static target must report the exact permanent source/authority byte
delta and all recomputed object identities.  This governance overhead is not
part of the scientific construction timer, query work, or a performance
claim; it may not be hidden or described as zero.

## 5. Future HOST-I path closure

After this erratum is reviewed and the user separately reauthorizes HOST-I,
the source target must change exactly the same fourteen mode-`100644` paths:

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

Its direct-child source review may change exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md
```

The implementation binding and source-provenance crosswalk must cite the exact
committed erratum protocol, contract, and review identities as additive
authority/DAG provenance.  The implementation manifest must continue to use
its existing `authorization_identity` field for the committed HOST-I AUTH
record; no manifest schema key is added.

## 6. Preserved future obligations

All non-superseded HOST-P and HOST-I AUTH obligations remain in force.  A
future exact source target and review must prove at least:

1. exactly 37 filesystem sources and 38 executable units remain;
2. all 27 native/CMake sources and all five unaffected Python sources remain
   byte-identical;
3. the old leader digest disappears from active source and the sole new
   digest has exactly the registered seven active occurrences;
4. the new component key has exactly the two required source occurrences and
   denotes exactly one path-map entry; no alternate key or path exists;
5. all affected source SHA-256 values, sizes, Git blobs, and the canonical
   sorted 37-source-tree identity are independently recomputed;
6. inline PREP bytes agree across PREP source, cache authority, static closure,
   and implementation manifest, while the raw 2,778-byte pre-START prologue
   remains byte-identical;
7. runtime schema constants and every maximal-witness leader alias use only
   the new digest;
8. the cache authority has exactly eight components and preserves the exact
   seven historical identities;
9. `build_status` remains `NOT_AUTHORIZED_NOT_RUN`;
10. CACHE-I-SYNTAX identities remain labeled historical evidence for the old
    source snapshot and are never relabeled; and
11. apart from the disclosed extra identity check, no control flow, error
    precedence, status, retry, resource cap, timer, cache, token, receipt,
    scientific, or query behavior changes.

Static source review is not syntax or runtime execution.  The changed source
snapshot receives no syntax claim unless separately authorized later.

## 7. Known excluded downstream limitation

Static inspection also found a distinct downstream closure that this narrow
erratum does not repair.  The cache verifier builds `expected_source_blobs`
from the current authority and compares every one of those blobs against each
registered CACHE-I/PREP history commit.  After the five-source HOST-I rebind,
the old history commits necessarily retain the old blobs, so a later cache-
verifier/PAR execution would report `SOURCE_HISTORY_MISMATCH`.

This does not block the current documentation stage, a future source-only
HOST-I static review, or PREP itself, none of which executes that cache
verifier.  It does mean that neither this erratum nor a later HOST-I source
review may claim cache-verifier or PAR readiness.  Any repair to historical-
snapshot comparison semantics requires a separately authorized protocol and
source delta before cache-verifier/PAR execution.  This erratum admits no such
change.

## 8. Current-stage review and publication

Review of this documentation target is limited to committed static inspection,
Git ancestry/mode/path identities, SHA-256 and byte-size recomputation,
structured JSON parsing with non-repository tooling, exact verifier-source
inspection, and diff/whitespace checks.  PASS requires zero findings at LOW
severity or above.

The direct-child review must independently establish:

- exact parent, target and review projections;
- the 7-versus-8 contradiction and exact-set rejection path;
- necessity and sufficiency of the two constant-table additions only for the
  eighth-component exact-key/path admission, not cache-verifier or PAR PASS;
- the exact one-extra-identity-check overhead;
- the independently confirmed future `SOURCE_HISTORY_MISMATCH`, its exclusion
  from this erratum, and the resulting prohibition on cache-verifier/PAR-
  readiness claims;
- preservation of the fourteen-path future target and three-path review;
- the revised future parent rule and reauthorization requirement; and
- every prohibition and claim ceiling below.

After the target is committed and pushed, at most one ordinary target-head
remote-equality check may be recorded in its direct-child review.  After the
review is committed and pushed, at most one ordinary review-head equality
check may close documentation publication.  Neither is an implementation
admission or PREP probe.  The mandatory Meeting Summary Handoff follows; then
this stage stops.

## 9. Prohibitions and claim ceiling

This stage permits no edit to existing implementation source, derived
authority, HOST-P objects, HOST-I AUTH objects, historical PREP records,
schemas, witnesses, manifests, or environment.  It permits no Python, DNF,
syntax, import, compiler, build, test, fixture, RNG, native executable, cache
verifier execution, PREP bootstrap/tool, old or new probe, clone, START, token,
capture, journal, receipt, CACHE-BIND, PAR-R1, SRUN, quarantine, dataset,
index, result, or SAQ/CAQ action.

The halted HOST-I instruction is not automatically resumed.  After exact
review and Meeting Summary Handoff, a fresh explicit instruction naming
`A4-V2-PREP-HOST-I` is required.

The maximum conclusion is only:

```text
A4-V2-PREP-HOST-I-ERRATUM  HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
A4-V2-PREP-HOST-I          REAUTHORIZATION_REQUIRED_NOT_RUN
HOST_IDENTITY_REBOUND      NOT_ESTABLISHED
PREP                        NOT_AUTHORIZED_NOT_RUN
PERFORMANCE                 PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION         NONE
```

# A4 V2 PREP Host-Identity Rebind Implementation Authorization Record

Date: 2026-07-16

Authorized node: **A4-V2-PREP-HOST-I-AUTH**

Current activity: **AUTHORIZATION RECORD FORMATION, PUSH, AND INDEPENDENT
REVIEW ONLY**

Maximum current-node verdict: **AUTHORIZATION_EXACT_TARGET_REVIEW_PASS**

`A4-V2-PREP-HOST-I` source/authority rebind: **NOT AUTHORIZED**

`HOST_IDENTITY_REBOUND`: **NOT ESTABLISHED**

## 1. Exact instruction and narrow interpretation

On 2026-07-16 the user instructed exactly:

```text
授权 A4-V2-PREP-HOST-I-AUTH
```

This opens only the authorization-record node frozen by the reviewed HOST-P
erratum. It permits formation, commit, push, and exact-commit independent
review of this record plus focused `AGENTS.md` and `TASK.md` status text. It
does not open `A4-V2-PREP-HOST-I`, edit any implementation or derived
authority object, or execute any repository or scientific code.

After this authorization record is independently reviewed and handed off,
the source node still requires a separate explicit user instruction naming
`A4-V2-PREP-HOST-I`. Reviewed authorization is necessary but not sufficient
to form the future source target.

## 2. Exact parent and commit topology

The authorization target must be the direct child of the pushed HOST-P review
head:

```text
commit  b89dabedd0273a330dded7f61551e6ad1ceac19c
tree    d4ca936c4fb2caff16a5fcc20ed5001e0e133867
branch  refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

It may change exactly three mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_2026_07_16.md
```

Its direct-child independent review may change exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_independent_review_2026_07_16.md
```

The authorization-review path above is distinct from the later source-review
path
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md`.
Every unlisted tracked blob and mode must remain byte-identical on each edge.

## 3. Bound HOST-P authority and current host pin

This record depends on, and does not rewrite, the exact reviewed HOST-P
authority:

| Object | Git/role | SHA-256 | Bytes |
|---|---|---|---:|
| erratum protocol | HOST-P target `5a47fed05321af39a236d2dfb56d2c0f43708db3` | `0cef593b0532070c87be49d3b7b469abe755ff20a072b8bfff915a2bf848289e` | 14,350 |
| erratum contract | HOST-P target `5a47fed05321af39a236d2dfb56d2c0f43708db3` | `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09` | 10,684 |
| independent review | HOST-P review `b89dabedd0273a330dded7f61551e6ad1ceac19c` | `dea30436db0cd1fd031274e6847a4f11e9d84b36d0ec90fc5a32c227be2b9a86` | 6,540 |

The sole replacement leader identity admitted by that authority remains:

```text
path        /usr/bin/python3.9
type        regular
size        15,448 bytes
sha256      c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
rpm         python3-3.9.25-7.el9_8.2.x86_64
source rpm  python3.9-3.9.25-7.el9_8.2.src.rpm
```

The bootstrap-external bytes remain 66,447 bytes with SHA-256
`8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4`.
The other twelve registered host objects must still match at future source
review. This is not whole-host identity: the disclosed dynamic loader,
libpython, libc, OpenSSL, and other mapped libraries remain unbound.

Historical states remain immutable:

```text
old PREP review head      HISTORICAL_VALID / STALE_FOR_ACTIVATION
old actual authority      UNSPENT_BUT_NONTRANSFERABLE
old probe                 UNSPENT_BUT_SUPERSEDED / NEVER_RUN_OR_REUSED
permanent START token     ABSENT / NOT_CONSUMED
```

## 4. Frozen baseline for a possible later HOST-I source target

The current reviewed CACHE-I baseline remains exactly 37 filesystem sources,
38 executable units, 27 native/CMake sources, ten Python sources, and
canonical source-tree SHA-256:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2
```

The inline PREP source and raw pre-START prologue remain:

```text
inline source
  sha256  9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b
  bytes   19,631
raw pre-START prologue
  sha256  0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7
  bytes   2,778
```

The only five source paths that a separately authorized HOST-I stage could
change have this frozen pre-rebind identity:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `script/a4_v2_cache_policy_verifier.py` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | 151,371 |
| `script/a4_v2_isolated_clone_prep.py` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | 219,758 |
| `script/a4_v2_runner.py` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | 360,127 |
| `script/a4_v2_verifier.py` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | 250,023 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | 34,929 |

The seven derived objects that a later HOST-I target could coherently rebind
have this frozen pre-rebind identity:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json` | `5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec` | 42,903 |
| `docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json` | `45a82a4f6b23d32f8d07517bd285003e60b484674a581aa1572cc6398c9773e3` | 4,439,071 |
| `docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json` | `942519ee027e8a033c653cd34329231696c6f970d4578193ecb054906d1140ea` | 23,762 |
| `docs/saq_a4_v2_cache_static_closure_2026_07_15.json` | `f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0` | 218,872 |
| `docs/saq_a4_v2_implementation_binding_2026_07_14.md` | `07e87a073410a79a078f752258bb98575c6a7f994cf5c740795b5b4b5bccafec` | 54,934 |
| `docs/saq_a4_v2_implementation_manifest_2026_07_14.json` | `168e4d6da4dd326484d81bf4e9bfffa654f39dda4867580a4fdf3bb9d009b182` | 34,781 |
| `docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md` | `2e35be12bd272f0a99297d8a81be77998f089aa05028050173f91e37cdac3cca` | 14,485 |

The five unaffected Python sources and every native/CMake source must remain
byte-identical:

```text
script/a4_v2_archive.py
script/a4_v2_evidence.py
script/a4_v2_parity.py
script/a4_v2_producer.py
script/a4_v2_producer_wire.py
```

## 5. Exact future source/review projections (specification only)

If and only if the user later explicitly authorizes
`A4-V2-PREP-HOST-I`, its source target must be the direct child of the
unchanged, committed, pushed, and publication-closed AUTH direct-child review
head. It may change exactly these fourteen paths:

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

No path outside either projection may be added after outcome inspection. Any
need for another path is a protocol mismatch and requires an additive erratum.

## 6. Sole future semantic delta and static obligations

The only permitted future semantic delta is replacement of exactly seven
active source occurrences in exactly the five listed sources:

```text
old sole digest
c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0

new sole digest
c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
```

The outer PREP constant and separately bound inline bootstrap must change
coherently, as must the cache verifier, runner, independent verifier, and
entrypoint. Dual-hash admission, old-hash fallback, wildcard or prefix
matching, package-version-only admission, and runtime RPM lookup are
forbidden.

A future exact source target and independent review must also prove:

1. exactly 37 filesystem sources and 38 executable units remain;
2. all affected source SHA-256 values, byte sizes, Git blobs, and the canonical
   sorted 37-source-tree hash are independently recomputed;
3. inline source bytes agree across PREP source, cache authority, static
   closure, and implementation manifest;
4. the raw 2,778-byte pre-START prologue remains byte-identical;
5. runtime schema constants and every maximal-witness leader alias use only
   the new digest;
6. the cache authority adds
   `docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json`,
   SHA-256
   `c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09`
   and 10,684 bytes, as an exact additive protocol component while preserving
   every historical base-component identity;
7. the implementation manifest binds this committed authorization record
   without changing its schema;
8. `build_status` remains `NOT_AUTHORIZED_NOT_RUN`;
9. the old CACHE-I-SYNTAX observations remain bound only to their historical
   source snapshot and are never relabeled; and
10. control flow, error precedence, status, retry, resource, path, timer,
    cache, token, receipt, evidence boundary, and scientific behavior remain
    unchanged.

Static source review is not syntax or runtime execution. Any compile-only
check for future changed bytes requires its own separately named authority.

## 7. Current AUTH-node review and publication closure

Independent review of this exact authorization target must verify direct
ancestry, exact path/mode projection, all HOST-P identities, the current
leader pin and other twelve frozen host objects, the 37-source/38-unit
baseline, five-source/seven-occurrence closure, seven derived identities,
future fourteen-path projection, claim ceiling, and every prohibition. PASS
requires zero findings at LOW severity or above.

No pre-target parent-admission probe is registered for this node. After the
target is committed and pushed, at most one bounded ordinary documentation
target-head remote-equality check may be recorded in its direct-child review.
After that review is committed and pushed, at most one ordinary live review-
head equality check may close publication. Neither is an old or new PREP
execution-base probe, an implementation-parent admission, or evidence of
HOST-I readiness. Push success alone grants no later authority.

After exact review and mandatory Meeting Summary Handoff, stop. A separate
explicit user instruction is still required before forming any HOST-I source
target.

## 8. Current prohibitions and claim ceiling

This AUTH node permits no edit to the five sources, seven derived objects,
HOST-P objects, historical PREP authorization paths, schema/witness objects,
or environment. It permits no Python, DNF/YUM, import, syntax check, compiler,
build, test, fixture, RNG, native executable, PREP bootstrap/tool, old or new
PREP probe, clone, START, token, capture, journal, receipt, CACHE-BIND, PAR-R1,
SRUN, quarantine access, dataset/index/result access, or SAQ/CAQ action.

Untracked and WIP state is not evidence. No package, host, or environment
mutation is authorized.

The maximum conclusion after a clean exact review is only:

```text
A4-V2-PREP-HOST-I-AUTH  AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-PREP-HOST-I       NOT_AUTHORIZED
HOST_IDENTITY_REBOUND   NOT_ESTABLISHED
PREP                     NOT_AUTHORIZED_NOT_RUN
PERFORMANCE              PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION      NONE
```

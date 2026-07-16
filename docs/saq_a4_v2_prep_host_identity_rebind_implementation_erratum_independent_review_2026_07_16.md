# A4-V2 PREP host-identity source-authority erratum independent review

Date: 2026-07-16

Review scope: three fresh, independent, read-only static review tracks of exact
target `6fe8544ae677fa8aaf7bba1306ae9aa8d4599f20`.

## Verdict

**PASS — zero findings at LOW severity or above.**

```text
BLOCKER  0
HIGH     0
MEDIUM   0
LOW      0
```

Maximum stage verdict after this exact direct-child review record is committed
and pushed:

```text
HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
```

This is artifact-governance protocol evidence only.  It does not establish
`HOST_IDENTITY_REBOUND`, implementation readiness, PREP readiness,
cache-verifier or PAR readiness, parity, synthetic feasibility, performance,
an SAQ limitation, novelty, or a scientific decision.

## Exact target, ancestry, and projection

The reviewed target has the registered topology:

```text
target       6fe8544ae677fa8aaf7bba1306ae9aa8d4599f20
tree         51f9abc20ac6e7afcb0c584ce6bd4cfc79e3b5f9
parent       71e6bec01dbabaf29333ac75dcd9ef7a238a079d
parent tree  36f5a2a0a767711010fccbf8ec8eca7696f1a609
grandparent  212a67b887aa710fed35f66766982db683b3fa63
```

The direct parent is the clean, pushed, publication-closed HOST-I AUTH review
head required by the erratum.  `git diff-tree --raw` and independent path-set
comparison show exactly four target paths, all mode `100644`:

```text
M AGENTS.md
M TASK.md
A docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_contract_2026_07_16.json
A docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_protocol_2026_07_16.md
```

Every other tracked blob and mode is identical to the parent.  `git show
--check` and the target diff whitespace check returned no issue.

The four target objects have these independently recomputed identities:

| Path | SHA-256 | Bytes | Git blob |
| --- | --- | ---: | --- |
| `AGENTS.md` | `23fc8237819d52e025966df9b099c7d4c10ed320c59691e1d807541697df78ba` | 35,470 | `7555a6e5059f7638fdc236d57dca8bc878cc8e94` |
| `TASK.md` | `163c47428be47dd7074a8d95ed0020ebcb77e2d87131cfcba5a624766ff92a09` | 30,508 | `8021acdb2b95767e05ac45ac1fe9aae945aec399` |
| erratum contract | `01dadbe2ba73a429a67d7029b5e4dafafb6b400a6067767a1aac161e9457977a` | 10,967 | `0b65ce91cb258a8904e7bcadf1bde58d652ce381` |
| erratum protocol | `5d9ac7222f93f00de5f2cd96b6df16d389b9f3123b604115c515bae963a1088d` | 14,716 | `9a4e872bfc25fc70511f42f674893216714880b1` |

The contract parses as one JSON object with `jq`.  Its unique current target
and review projections contain exactly four and three paths; the future HOST-I
target and review projections contain exactly fourteen and three paths.  It
registers seven historical protocol components and exactly two verifier
constant-table additions.

## Parent authority and contradiction

All frozen parent identities in the protocol and contract match their bytes at
both parent and target.  This includes the HOST-P protocol/contract/review,
HOST-I AUTH/review, cache authority, and cache verifier.  The current cache
authority has exactly seven historical `protocol_components`, and every
existing path/SHA-256/size identity remains unchanged.

Independent source inspection confirms the parent contradiction:

1. HOST-I AUTH permits exactly seven leader-digest substitutions as the sole
   source semantic delta;
2. the same AUTH requires the seven old cache-authority components to be
   preserved and the HOST-P contract to be added as an eighth component;
3. `PROTOCOL_COMPONENT_KEYS` and `PROTOCOL_COMPONENT_PATHS` close the parent
   verifier to exactly the old seven keys/paths; and
4. `_require_keys` applies set equality before normalization, exact path
   comparison, and the sorted `_check_identity` loop.

An eight-entry authority with the unchanged verifier is therefore rejected;
omitting or replacing an entry violates the AUTH.  The erratum is necessary.
The previously reviewed AUTH remains immutable historical evidence, but its
unsatisfiable future source rule is superseded only by this additive erratum.

## Minimal eighth-component admission

The future source exception is closed to two semantic loci in the already
listed cache verifier:

```text
PROTOCOL_COMPONENT_KEYS
  add prep_host_identity_rebind_erratum_contract

PROTOCOL_COMPONENT_PATHS
  add prep_host_identity_rebind_erratum_contract
    -> docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json
```

The mapped component is the existing HOST-P contract with exact identity:

```text
sha256     c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09
size       10684
```

The set-member source line is 54 bytes and the three-line mapping is 143
bytes, for an exact 197-byte addition.  The cache verifier is currently
151,371 bytes; the seven registered digest substitutions are equal-length, so
the future frozen size is exactly 151,568 bytes.  The future committed target,
not this arithmetic, must determine its SHA-256 and Git blob.

The additions are necessary and sufficient only for eighth-component
exact-key/path admission.  They do not establish that the complete cache
verifier or PAR path will pass.  No subset rule, wildcard, alias, ninth
component, fallback digest, version-only rule, runtime RPM lookup, new branch,
new status, or new validation mechanism is admitted.

## Exact verification and resource behavior

The existing sorted loop invokes `_check_identity` once for every protocol
component.  The eighth entry therefore causes exactly one additional call
using the unchanged body:

- exact physical success reads and hashes the 10,684-byte contract and adds
  exactly 10,684 to the existing aggregate `filesystem_bytes_read` counter;
- a readable physical mismatch retains its observed byte count in that
  counter, records the existing mismatch, and additionally takes the Git
  fallback;
- an absent or unreadable physical payload adds no filesystem bytes, records
  the existing mismatch, and takes the same fallback; and
- fallback adds observed payload/stderr lengths to the existing
  `git_stdout_bytes` and `git_stderr_bytes` counters.

No resource-ledger key or schema field is added.  The loop body, caps,
normalization, failure precedence, status mapping, mismatch shape, and fallback
semantics stay unchanged.  The protocol correctly requires the future target
to measure its permanent source/authority byte delta and forbids describing
this governance overhead as zero or as scientific construction/query work.

## Future source closure and parent rule

The two root status paths, seven already listed derived-authority paths, and
five already listed source paths remain exactly the fourteen-path future
target.  The source review remains exactly the registered three paths.  No
new implementation path is needed for the eighth-component admission; the
HOST-P contract is an inherited immutable input.

Because this erratum and review advance the branch beyond `71e6bec...`, the
old future-parent rule cannot remain satisfiable.  The erratum correctly makes
a separately reauthorized HOST-I target the direct child of the clean, pushed,
publication-closed review head formed by this memo.  It introduces no
implementation-parent or PREP execution-base probe.

The original 37-filesystem-source/38-executable-unit closure remains.  Future
review must preserve all 27 native/CMake and five unaffected Python sources,
recompute affected hashes/sizes/blobs and the canonical 37-source tree, retain
the four-way inline identity and raw 2,778-byte prologue, use only the new
leader digest in active schema/witness aliases, preserve the seven historical
components, keep `build_status=NOT_AUTHORIZED_NOT_RUN`, and leave historical
CACHE-I-SYNTAX identities bound to the old snapshot.

## Independently confirmed excluded downstream limitation

The cache verifier constructs `expected_source_blobs` from the current cache
authority and compares every blob against each registered historical
CACHE-I/PREP commit.  A future five-source rebind changes the current expected
blobs while those historical commits correctly retain the old ones.  Without
a separate repair, later cache-verifier/PAR execution therefore reaches
`SOURCE_HISTORY_MISMATCH`.

This does not block this documentation review, a future source-only HOST-I
static review, or PREP itself; PREP does not invoke this cache verifier.  It
does prohibit any cache-verifier/PAR readiness claim.  The erratum records the
limitation consistently in its protocol, contract, `AGENTS.md`, and `TASK.md`
and grants no authority to repair it.  A separate protocol and source
authorization are required before such execution or readiness can be claimed.

## Publication observation

The target commit was accepted by the remote branch with a successful push:

```text
71e6bec..6fe8544  saq-arbitrary-cardinality-feasibility-v2
```

The local same-named origin-tracking ref then equaled the clean target with
ahead/behind `0/0`.  One optional post-push `git ls-remote` using the SSH
`origin` URL returned exit 128 before a remote observation because the local
process rejected `/etc/ssh/ssh_config.d/50-redhat.conf` ownership/permissions.
It produced no stdout, was not retried, and supports no publication-equality
claim.  It is disclosed and excluded.  The successful push receipt, not that
failed check, establishes that the remote accepted the target.

This review record is valid only as the target's direct child and only if it
changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md
```

All three must be mode `100644`; all other tracked blobs and modes must remain
identical.  After this review record is pushed, at most one ordinary
review-head equality check may close documentation publication.  It is not an
implementation admission or PREP probe.

## Independent tracks and execution boundary

The three review tracks independently covered:

| Track | Result | Primary responsibility |
| --- | --- | --- |
| Git/identity closure | PASS | ancestry, tree, path/mode projection, target and frozen-parent identities, JSON structure |
| semantic closure | PASS | exact-set rejection, two-locus admission, 197-byte arithmetic, `_check_identity` counters, future projection |
| authorization/scope | PASS | claim ceiling, parent supersession, reauthorization, downstream limitation, prohibitions and handoff |

Reviewers used only read-only Git/text/hash/byte-count/`jq` inspection.  They
ran no Python, network, build, compiler, test, cache verifier, PREP, probe,
clone, token, data, quarantine, or SAQ/CAQ action and edited no file.  The
target formation itself likewise ran no implementation or scientific code.

The only permitted next actions are this exact review commit/push, its one
ordinary publication check, and the mandatory Meeting Summary Handoff.  Then
stop.  A fresh explicit instruction naming `A4-V2-PREP-HOST-I` is required,
and even a later HOST-I static pass would not resolve the separate
`SOURCE_HISTORY_MISMATCH` before cache-verifier/PAR work.

```text
A4-V2-PREP-HOST-I-ERRATUM  HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
A4-V2-PREP-HOST-I          REAUTHORIZATION_REQUIRED_NOT_RUN
HOST_IDENTITY_REBOUND      NOT_ESTABLISHED
PREP                        NOT_AUTHORIZED_NOT_RUN
CACHE_VERIFIER_PAR_READY   NOT_ESTABLISHED
PERFORMANCE                 PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION         NONE
```

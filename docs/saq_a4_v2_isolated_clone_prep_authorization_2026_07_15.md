# A4 V2 Isolated-Clone PREP Authorization-Record Target

Date: 2026-07-16

Documentation activity:
**PREP AUTHORIZATION TARGET FORMATION, PUSH, AND INDEPENDENT REVIEW ONLY**

Current target-formation status:
**PREP_AUTHORIZATION_RECORD_FORMATION_AUTHORIZED**

Maximum documentation verdict, available only after exact committed review:
**PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS**

Actual PREP invocation: **NOT_AUTHORIZED**

Future whole-stage ceiling, not opened by this record:
**ISOLATED_CLONE_PREPARED_REVIEW_PASS**

## 1. Exact user instruction and narrow interpretation

On 2026-07-16 the user instructed exactly:

```text
授权 PREP authorization/review
```

This instruction authorizes only formation, push, and independent review of
the fixed PREP authorization record specified by the reviewed CACHE-P
protocol. It does not authorize the isolated-clone preparation command
itself. In particular, it creates no clone, permanent token, capture sidecar,
outer journal, receipt staging tree, final receipt, CACHE-BIND object, PAR-R1
event, dataset observation, or scientific result.

This document therefore freezes a dormant future execution contract. A later
explicit user instruction must separately authorize exactly one PREP
invocation from the unchanged reviewed authorization-review head. No wording
below activates that invocation.

## 2. Exact parent and distinct PREP parent admission

The exact target parent is the committed, pushed CACHE-I implementation review:

```text
commit  5db302537793bc05f541aede119255213ea49e14
tree    f3c8e0ca52cb719018f5ad82952c06724ab9105a
branch  refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

Before this target was formed, the one PREP-authorized child-node
parent-admission probe ran with cwd `/`, stdin `/dev/null`, and both frozen
HOME/XDG paths absent before and after. Its exact argv was:

```text
/usr/bin/env -i
GIT_ATTR_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
GIT_EXEC_PATH=/usr/libexec/git-core GIT_OPTIONAL_LOCKS=0
GIT_TERMINAL_PROMPT=0
HOME=/tmp/saq-a4-v2-incident-git-home-absent
XDG_CONFIG_HOME=/tmp/saq-a4-v2-incident-git-xdg-absent
LANG=C LC_ALL=C PATH=/usr/bin:/bin
/usr/bin/timeout --signal=TERM --kill-after=5s 300s
/usr/bin/git
-c core.hooksPath=/dev/null -c core.fsmonitor=false
-c core.autocrlf=false -c core.eol=lf
-c gc.auto=0 -c maintenance.auto=false
ls-remote --refs https://github.com/Ufowoqqqo/SAQ.git
refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

Its exact admitted result was:

```text
exit     0
stdout   5db302537793bc05f541aede119255213ea49e14<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

There was no sandbox preflight for this PREP parent-admission role and no
failed or no-observation attempt to disclose. The claim is limited to the
pinned env-to-timeout-to-Git successful exit and exact returned bytes. It
makes no outer-executor, capture, hashing, process-count, hard-reap,
failure-resource, or systems-performance claim. This is a distinct
child-node parent admission, not a reuse of the CACHE-I target/review closure,
and it is not PREP execution evidence.

## 3. Exact target and review commit closure

The authorization target must be the direct child of
`5db302537793bc05f541aede119255213ea49e14` and may change exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md
```

Its direct-child independent review must change exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md
```

Every other tracked blob and mode must remain unchanged in each edge. The
target-head no-clone equality result, after target commit and push, belongs in
the direct-child review memo. Push success alone is never authority.

This documentation stage does not run the later authorization-review-head
probe. Section 8 preserves that unique live predicate for a separately
authorized PREP invocation.

## 4. Preserved reviewed source and executable-unit closure

The target and review must preserve the reviewed implementation manifest:

```text
path      docs/saq_a4_v2_implementation_manifest_2026_07_14.json
git blob  31ad8222d61a5f6f15784092a8ec37d06f18e8af
bytes     34,781
sha256    168e4d6da4dd326484d81bf4e9bfffa654f39dda4867580a4fdf3bb9d009b182
```

It binds exactly 37 filesystem sources—27 native/CMake and ten Python—and
canonical source-tree SHA-256:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2
```

The future PREP tool remains the exact reviewed filesystem source:

```text
path      script/a4_v2_isolated_clone_prep.py
git blob  884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7
bytes     219,758
sha256    29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053
```

The separately bound inline bootstrap remains the 38th executable unit, not a
38th file source:

```text
full source  9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b / 19,631 bytes
raw prologue 0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7 / 2,778 bytes
```

The original CACHE-I no-execution attestation and the later, separately
authorized `A4-V2-CACHE-I-SYNTAX` chronology remain unchanged. That narrow
check established Python 3.9 syntax acceptance for six outer sources plus the
inline source only. This documentation target performs no additional Python
check and does not reinterpret syntax acceptance as importability,
executability, correctness, or PREP readiness.

## 5. Frozen authority objects and schema references

This record binds the following reviewed objects without copying their large
payloads:

| Role | Path | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| CACHE-P protocol | `docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md` | `3cdeab39081dd8558683587f385e8d2c849d8414d7fe57b236dd89d6237a2149` | 62,883 |
| machine contract | `docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json` | `06fb28c460cf2a0c4f75525abb69695c40da810892351ea0bbf96a0efe5ad64a` | 58,109 |
| cache authority | `docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json` | `5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec` | 42,903 |
| static closure | `docs/saq_a4_v2_cache_static_closure_2026_07_15.json` | `f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0` | 218,872 |
| CACHE-I exact review | `docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md` | `d9c1ca69a989bff4826939335d37683366738354091bbff1e43e588550e1a328` | 10,258 |
| PREP token schema | `docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json` | `e71eed64903428046acd4cf235220b0f6af68861fc30663e99c72167d469898a` | 11,295 |
| token maximal witness | `docs/saq_a4_v2_isolated_clone_prep_token_maximal_instance_2026_07_15.json` | `6e8b1f76f17de432cf21327025636fc1a6dcc7e9b25b572616714f333d214099` | 17,798 |
| PREP receipt schema | `docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json` | `2ab06e7cb62b3316f9ea58ee0b1d220f50b43fd1cedf1df2bb5de5ef835864da` | 24,973 |
| receipt maximal witness | `docs/saq_a4_v2_isolated_clone_prep_receipt_maximal_instance_2026_07_15.json` | `5aba7fe04b103967d9784061d5f8695cfb38d6b1af490f21dc65ffe3a7fbe199` | 83,207 |

The complete dormant PREP mechanism is defined by protocol section 6 and the
machine-contract objects at these JSON pointers:

```text
/preparation_contract
/preparation_status_precedence
/host_execution_identity
/commit_closure
/future_authority_dag
/claim_ceiling
```

Those objects—not this summary—are normative for every path, argv, identity,
schema, resource, status, publication, failure, and evidence boundary.

## 6. Dormant future PREP boundary

Only a later explicit user instruction may activate one PREP attempt. If
activated, its exact execution base must be the pushed and independently
reviewed PREP authorization-review head, with the same 37-source tree above.
The exact launch template, environment, cwd, root, Git origin, host pins,
bootstrap substitutions, pre-START builtins, no-follow path operations,
capture policy, process topology, receipt paths, and finite publication tail
remain those frozen in `/preparation_contract`.

The mechanical one-shot boundary is a durable START record in:

```text
/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.lock
```

The fixed token admits exactly START plus one TERMINAL and is permanently
consumed. Failure before durable START is the contract's
`LAUNCHER_INCOMPLETE_NO_DECISION / NOT_MACHINE_PROVABLE_INVOCATION_OR_DURABILITY`
incident branch and is never retried under the same authority. After START,
the frozen status precedence alone applies. A successful unreviewed
publication can reach only
`ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW`; the whole-stage ceiling
`ISOLATED_CLONE_PREPARED_REVIEW_PASS` requires the exact receipt target,
review, push, complete clone revalidation, and sanitized fresh-fetch equality
specified by the contract.

This section records future conditions only. The current effective
`/preparation_status_precedence` status remains:

```text
NOT_AUTHORIZED
```

## 7. Host, resource, status, and claim ceilings

The future host boundary is exactly `/host_execution_identity`: pinned bytes
for env, timeout, CPython, bootstrap_external, Git, and the registered
Git-HTTP helper/link closure. Package strings are static provenance only; the
dynamic loader and shared libraries remain disclosed unbound host inputs.
No runtime RPM query is permitted.

The complete numerical ceilings are exactly
`/preparation_contract/resource_ceilings`, including 1,800,000,000,000 ns
wall, 1,800,000,000 CPU microseconds, 2,147,483,648 bytes observed concurrent
family RSS, 1,073,741,824 logical and allocated isolation bytes, 20,000
filesystem entries, 100,000 journal records, and the separately frozen stream,
journal, process, and canonical-string caps. No number is selected or changed
by this authorization record.

Status ordering is exactly `/preparation_status_precedence`. Artifact,
resource, implementation, crash/unknown, launcher, pending-review, and
review-pass states must not be merged or reclassified. The observation claim
is only ephemeral physical readiness, not power-loss durability.

The claim ceiling remains artifact governance only. Neither authorization
review nor a later PREP result establishes an SAQ limitation, synthetic
feasibility, scientific FOM result, systems performance, novelty, SRUN
authority, data authority, or SAQ/CAQ change authority.

## 8. Unique delayed authorization-review-head probe

The frozen DAG assigns one PREP authorization-review-head no-clone HTTPS probe
two inseparable operational roles:

1. live closure of the pushed authorization-review head; and
2. immediate admission of that same commit as the one PREP execution base.

It is one probe, not two. It must **not** run during this documentation-only
authorization/review stage. It may run only immediately before a separately
user-authorized PREP invocation, after the review commit is pushed, with no
intervening source-branch or worktree mutation between the probe and launch.
Its expected OID must be the exact authorization-review head, and all frozen
cwd, stdin, env, timeout, Git, HTTPS, output-byte, and HOME/XDG absence rules
remain unchanged.

If a later session cannot keep the pushed review head and worktree unchanged
across that probe-to-launch boundary, or if the probe fails, the branch must
stop and request new authority. It must not run an early probe now, reuse an
older equality observation, issue a second execution-base probe, or mutate the
review head to repair the condition.

## 9. Explicit current prohibitions

This instruction and record permit no Python, import, syntax check, compiler,
build, test, fixture, RNG, native executable, clone, PREP bootstrap, PREP tool,
START token, capture sidecar, journal, receipt, CACHE-BIND, cache verifier,
PAR-R1, SRUN, or scientific execution. They permit no runtime environment
mutation and no chmod.

They also permit no enumeration, stat, hash, read, import, copy, rename,
cleanup, deletion, or reuse of a quarantined residual; no benchmark, base,
query, centroid, cluster-id, ground-truth, index, generated-result, or data
access; and no SAQ/CAQ, estimator, packing, search, or index change.

No new mechanism, parameter, threshold, path, status, host pin, schema,
resource ceiling, retry rule, or evidence boundary may be introduced.

## 10. Independent review and stop rule

The direct-child review must statically verify:

- exact parent, direct ancestry, and the target/review three-path closures;
- the parent-admission argv/result and explicit absence of a sandbox preflight;
- every other tracked blob/mode unchanged;
- all 37 source identities, the 38-unit accounting, manifest identity, and
  canonical source-tree hash unchanged;
- exact PREP tool, inline bootstrap/prologue, protocol, authority, schema, and
  host/resource/status references;
- preservation of the CACHE-I syntax chronology;
- the distinction between the documentation verdict and future whole-stage
  ceiling; and
- the delayed single review-head probe and all current prohibitions.

Only after the focused target is committed, pushed, target-head equality is
recorded, and the direct-child review finds zero issues at LOW or above may
the documentation node reach:

```text
PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
```

Even that verdict does not authorize PREP. The review record and branch-state
edits remain WIP/nonevidence until committed and pushed. The unique
review-head probe remains unspent until a later explicit PREP instruction.
No CACHE-BIND, PAR-R1, SRUN, data, or SAQ/CAQ action may follow automatically.

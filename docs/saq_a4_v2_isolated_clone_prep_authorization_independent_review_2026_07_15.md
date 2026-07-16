# Independent Review: A4 V2 Isolated-Clone PREP Authorization Record

Date: 2026-07-16

Reviewed documentation node: `A4-V2-CACHE-PREP-AUTH`

Exact review target:
`e7f940e924a338022bfe8fffcbb3496f12a5a75c`

Independent review verdict:
**PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

Actual PREP invocation: **NOT_AUTHORIZED**

## 1. Scope and method

The exact committed and pushed target was reviewed only as formation of the
PREP authorization record requested by the user's exact instruction
`授权 PREP authorization/review`.  Review covered direct ancestry, exact path
closure, all protected blobs and modes, both completed no-clone probe roles,
the complete source/executable-unit closure, PREP tool and inline-bootstrap
identities, protocol/authority/schema references, dormant host/resource/status
references, CACHE-I syntax chronology, claim ceilings, and the unique delayed
authorization-review-head probe.

Review used committed Git-object inspection, `jq`, Perl static validators,
SHA-256/size recomputation, raw-byte comparison, and diff/whitespace checks.
No repository Python, import, syntax check, compiler, build, test, fixture,
RNG, native executable, clone, PREP bootstrap/tool, token, capture, journal,
receipt, cache verifier, PAR-R1, SRUN, dataset, base/query/ground-truth/index,
quarantine, or SAQ/CAQ path was executed, opened, or changed.  WIP and
untracked files were not evidence.

## 2. Exact Git and path closure

```text
target       e7f940e924a338022bfe8fffcbb3496f12a5a75c
parent       5db302537793bc05f541aede119255213ea49e14
parent tree  f3c8e0ca52cb719018f5ad82952c06724ab9105a
target tree  0386af8066a93d84ca772604990a08737a34aa33
subject      docs: bind PREP authorization review target
paths        3
insertions   366
deletions    8
```

The target is the required direct child and changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md
```

All three target modes are `100644`.  Excluding those exact paths, parent and
target projections each contain 485 entries and are raw-identical, with
projection SHA-256
`d1223ca5e3b3e3951374536c12c66f4d9a9eeca0654fd7a26ca487f9f8811852`.
Every other tracked blob and mode is therefore unchanged.  The exact
parent-to-target `git diff --check` passes.

The new authorization record itself is:

```text
git blob  ab12040dd7998f6ef1106162b9310c3a36e436a1
sha256    42f33050eeb22e9f7da7cd339eaa7121ddc0a9852e8d05d9e7843ef74f41ea73
bytes     13,783
```

The frozen direct-child review edge is exactly `AGENTS.md`, `TASK.md`, and
this memo.  No other review-path mutation is permitted.

## 3. Completed parent and target probe roles

### 3.1 Distinct PREP parent admission

The authorization record preserves the distinct child-node parent-admission
probe of pushed parent `5db302537793bc05f541aede119255213ea49e14`.
It used cwd `/`, stdin `/dev/null`, absent frozen HOME/XDG paths before and
after, and the frozen env-to-timeout-to-Git argv.  Its exact result was:

```text
exit     0
stdout   5db302537793bc05f541aede119255213ea49e14<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

There was no sandbox preflight for this role.  This observation admits only
the exact parent OID returned by the pinned, wall-bounded command; it is not a
reuse of a CACHE-I closure and is not PREP evidence.

### 3.2 Authorization-target closure

After target commit and push, the single target-head probe used the same
frozen cwd `/`, stdin `/dev/null`, absence checks, and this exact argv:

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

Its exact result was:

```text
exit     0
stdout   e7f940e924a338022bfe8fffcbb3496f12a5a75c<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

There was no sandbox preflight or failed target-head attempt.  The remote
branch therefore equalled the immutable review target for this role.  Push
success itself is not authority.

## 4. Preserved source and executable-unit closure

The implementation manifest remains exact Git blob
`31ad8222d61a5f6f15784092a8ec37d06f18e8af`, 34,781 bytes, with SHA-256
`168e4d6da4dd326484d81bf4e9bfffa654f39dda4867580a4fdf3bb9d009b182`.
All 37 registered filesystem-source SHA-256 values, sizes, paths, and Git blob
identities match committed bytes.  The sorted, duplicate-free inventory
remains exactly 27 native/CMake and ten Python sources.  Recomputing the frozen
canonical source preimage gives:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2
```

The dormant PREP filesystem tool remains Git blob
`884214fb70461ac2ec2ccf4ed58aaaf3cf78ffa7`, 219,758 bytes, with SHA-256
`29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053`.
Static marker extraction proves that the separately bound inline bootstrap is
byte-identical to the manifest/static closure:

```text
inline source  9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b / 19,631
raw prologue   0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7 / 2,778
```

The inline bootstrap is one separately identified executable unit, not a
filesystem source.  The exact accounting therefore remains 37 files and 38
units.

## 5. Protocol, authority, schema, and dormant future references

All nine SHA-256/size rows in the authorization record match committed bytes:
the CACHE-P protocol and machine contract, cache authority and static closure,
CACHE-I exact review, token schema/witness, and receipt schema/witness.  The
normative machine contract remains 58,109 bytes with SHA-256
`06fb28c460cf2a0c4f75525abb69695c40da810892351ea0bbf96a0efe5ad64a`.

Static inspection confirms that its exact references remain:

- `/preparation_contract/authorized` is `false`, and its tool, launch,
  execution-base, token, capture, receipt, origin, and tree-authority fields
  remain unchanged;
- `/preparation_status_precedence/0` is `NOT_AUTHORIZED`, followed by the
  separately typed launcher, precondition, crash/unknown, resource, artifact,
  implementation, pending-review, and review-pass states;
- `/commit_closure` names the same three-path authorization target and same
  three-path direct-child review;
- `/future_authority_dag` keeps `A4-V2-CACHE-PREP-ISO` unauthorized with only
  the future ceiling `ISOLATED_CLONE_PREPARED_REVIEW_PASS`;
- `/host_execution_identity` retains the exact env, timeout, CPython,
  `bootstrap_external`, Git, and Git-HTTP-helper/link pins while explicitly
  leaving the dynamic loader/shared libraries unbound; and
- `/preparation_contract/resource_ceilings` retains all frozen wall, CPU,
  RSS, storage, entry, journal, process, stream, and canonical-string caps.

These are static references to a dormant future mechanism.  No runtime host,
resource, filesystem, process, or durability observation was made by this
review.  The authorization record introduces no mechanism, threshold, path,
status, host pin, schema, retry, or evidence-boundary change.

## 6. Syntax chronology and claim ceilings

The record preserves the original CACHE-I source-only no-execution
attestation and separately names the later `A4-V2-CACHE-I-SYNTAX` authority.
That earlier narrow result applied only to the exact six outer source
snapshots plus the exact inline source, used `compile()` without executing the
resulting code objects, and imported no repository module.  This target and
review performed no additional Python check and do not reinterpret syntax
acceptance as importability, executability, correctness, or PREP readiness.

The documentation verdict and whole-stage ceiling remain distinct:

```text
current reviewed documentation verdict  PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
actual PREP invocation                   NOT_AUTHORIZED
future whole-stage ceiling               ISOLATED_CLONE_PREPARED_REVIEW_PASS
```

The first line is authorization-record review only.  It creates no clone,
token, capture, journal, receipt, binding, PAR artifact, data result, or
scientific claim.

## 7. Unique delayed review-head probe

The PREP authorization-review-head probe was deliberately **not run** during
this documentation review.  It remains unspent.  The frozen contract assigns
that single future probe two inseparable roles: live closure of the pushed
review head and immediate admission of the same immutable commit as the PREP
execution base.

Only a later explicit user authorization for actual PREP may permit the probe,
immediately before the one launch, after this review record is committed and
pushed, with no intervening source-branch or worktree mutation from probe to
launch.  It is not two probes; no earlier observation may be reused and no
second execution-base probe may be issued.  Failure, head drift, worktree
mutation, or inability to preserve the probe-to-launch boundary requires a
stop and new authority.

This memo contains no review-head remote-equality result and must not be read
as one.

## 8. Verdict and stop boundary

No BLOCKER, HIGH, MEDIUM, or LOW finding remains in the exact target.  The
maximum documentation result is therefore:

```text
PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
```

Actual `A4-V2-CACHE-PREP-ISO` remains `NOT_AUTHORIZED`.  So do clone/token/
receipt creation, `A4-V2-CACHE-BIND`, `A4-V2-PAR-R1`, `A4-V2-SRUN`, data or
quarantine access, and SAQ/CAQ change.  This is artifact-governance
authorization-review evidence, not PREP readiness, parity, synthetic
feasibility, an SAQ limitation, systems performance, novelty, or a database-
systems contribution.

This direct-child review memo and its branch-state edits remain WIP/
nonevidence until committed and pushed.  No actual PREP step or delayed probe
may begin from the uncommitted worktree.

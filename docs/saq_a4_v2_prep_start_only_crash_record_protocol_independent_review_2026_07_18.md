# A4-V2 PREP-ISO-R1 START-only crash-record protocol independent review

Date: 2026-07-18

Stage: `A4-V2-CACHE-PREP-ISO-R1-CRASH-P`

Immutable target:
`1982865e8577eca9edd92de5073d030de89f81aa`

Verdict:

```text
START_ONLY_CRASH_RECORD_PROTOCOL_REVIEW_PASS
```

This verdict is conditional on this exact review record being committed as
the direct child of the target, pushed, and closed by the separately required
ordinary review-head publication-equality observation. It is documentation
governance only. It is not the future terminal record, a PREP admission or
retry, source repair, execution readiness, PAR authority, performance
evidence, or scientific evidence.

## 1. Scope and method

I was the sole independent reviewer. I read the target versions of
`AGENTS.md`, `TASK.md`, the START-only crash-record protocol, and its machine
contract completely. I reviewed the immutable target rather than a moving
worktree and used only Git/object inspection, `jq` parsing, hashes, sizes,
read-only filesystem observations, source text inspection, and the one
registered sanitized HTTPS target-head equality observation.

I did not run Python, PREP, a build, test, verifier, clone, CACHE-BIND, PAR,
SRUN, or any benchmark/data operation. I did not append, truncate, chmod,
copy, rename, remove, or otherwise mutate the token, captures, or isolation
namespace. I did not reproduce the crash. No source, protocol, or contract
byte was changed during review.

## 2. Immutable Git target

Git establishes:

```text
target  1982865e8577eca9edd92de5073d030de89f81aa
parent  eb1b89318d58ef06bff878219346e7b277ab9aea
tree    75e37422900097860a862efa90ea303101be949e
```

The target is the direct child of the registered execution base and changes
exactly these four mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_start_only_crash_record_contract_2026_07_18.json
docs/saq_a4_v2_prep_start_only_crash_record_protocol_2026_07_18.md
```

Their target Git blobs are respectively:

```text
8343133855f24f52fbeda173e4d0ae83ad1072a3
f885acca9bdd93a465f44a3177256f7c5e062fba
c66bb6a509a99aa14d112b590033029c11daa940
c2011d09ac955671de90d800f514191a71a5b78b
```

`git diff-tree --raw`, exact path-set comparison, and `git diff --check`
passed. Because the Git delta is exactly this four-path set, every other
tracked path and blob is preserved, including PREP source blob
`d671531132eb0c490dec1953ca778e8d03913b3d`, predecessor protocol blob
`af2117c409a8d4d3eba61a994984556d5418d304`, and predecessor contract blob
`381cb355634632716096885def26847a58eb6706`.

The new protocol is 9,217 bytes with SHA-256
`efcb827ed1d4dc8681e68fe530ea6f90f76eed84cad67cff155ecc91f539a434`.
The contract is 5,300 bytes with SHA-256
`7c7d8dc0e662cc558bc5fd601c9ea7879a9dd3a8c6f70c94a2dc9cdb63a5f5f8`.
The contract parses as one JSON object. Its target/review path sets, event
status, runtime identities, future topology, authorization boundary, and
claim ceiling agree with the prose.

## 3. Target publication equality

Before the observation, local HEAD and the local remote-tracking ref both
equaled the target, the worktree was clean, and both fixed HOME/XDG paths were
absent. The target had been pushed. Exactly one ordinary target-head
publication observation was then run from cwd `/` with stdin `/dev/null`:

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

The exact result was:

```text
exit     0
stdout   1982865e8577eca9edd92de5073d030de89f81aa<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

There was no earlier target-head probe for this node and no failed attempt.
This observation establishes publication equality only. It is not the
consumed PREP execution-base probe, does not admit a launch, and grants no
retry or invocation authority. The future review-head observation must not be
run until this review is committed and pushed; it is a live non-evidentiary
closure predicate and is not content of this review.

## 4. Read-only runtime-state reobservation

Independent observations before and after the review checks were identical:

| Object | Mode | Bytes | Blocks | SHA-256 | State |
| --- | ---: | ---: | ---: | --- | --- |
| `.git/saq-a4-v2-isolated-prep.lock` | `0600` | 1,295 | 8 | `ef0b9d435a14e0d95f48e72833bad6208134fc1da64a431188f34a4af08d5604` | one START line |
| `.git/saq-a4-v2-isolated-prep.stdout` | `0600` | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | empty |
| `.git/saq-a4-v2-isolated-prep.stderr` | `0600` | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | empty |

The token contains exactly one canonical compact/sorted JSON line with
`record_type=START`, `schema_version=1`, `sequence=0`, and no TERMINAL. Its
canonical re-encoding has the same SHA-256. Its claims independently match:

```text
execution base       eb1b89318d58ef06bff878219346e7b277ab9aea
authorization        89e831d1d3fc712ae7b2095c4e2a48eff73b221398b691a00ba887e0ee34e20e / 18,877
authorization review 4058a2dd8b1887157b92e0bc7338af788c875708171ee5a6ecc64007d4d4ef59 / 16,578
inline bootstrap     d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56 / 19,631
raw prologue         0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7 / 2,778
common directory     /rwproject/kdd-db/kluaq/saq/.git
umask                 0077
```

The fixed capture paths and caps also match the START record. The isolation
root `/tmp/saq-a4-v2-par-r1-isolation` was absent before and after review.
No runtime-artifact drift or mutation occurred.

## 5. Frozen status and commit-closure gap

The immutable CACHE-P protocol and contract say that a valid START followed
by absent, partial, corrupt, or otherwise noncanonical TERMINAL is only
`CRASH_OR_UNKNOWN`; this is precedence order 3 and cannot be inferred as a
typed precondition, resource, artifact, or implementation status. Every state
also carries `NO_PAR_AUTHORITY / NO_SCIENTIFIC_DECISION`.

Their existing commit closure registers only:

- a launcher-incident target/review when durable START was never reached; and
- a success-receipt target/review after a complete success TERMINAL and
  receipt publication.

Durable START makes the first inapplicable, while absent TERMINAL, isolation
root, and receipt make the second inapplicable. The additive protocol closes
this topology without rewriting or misusing either predecessor path and
without changing the primary status.

## 6. Static source-consistency check

The immutable PREP source is blob
`d671531132eb0c490dec1953ca778e8d03913b3d`, SHA-256
`823bb00711e036c832f96f66e1979c69931866460af0d38a48f93c3fa9c03de2`,
and 219,758 bytes. Static inspection found:

- `rd()` at source line 5271 opens every intermediate component with the
  no-follow directory flags;
- `kernel_start()` at line 5338 calls `rd("/proc/self/stat", ...)`; and
- the OSError fallback at lines 5439--5441 calls `kernel_start()` again when
  start identity was not obtained.

This mechanism is consistent with the operator-reported
`NotADirectoryError ... 'self'`, because `/proc/self` is a symlink. It is only
`STATIC_CAUSE_CANDIDATE_NOT_RUNTIME_REPRODUCTION`: the traceback is absent
from both registered captures, no runtime reproduction was performed, and
the finding does not reclassify `CRASH_OR_UNKNOWN` as
`IMPLEMENTATION_INVALID`.

## 7. Future topology and authority

The protocol and contract uniquely reserve a separately authorized future
`A4-V2-CACHE-PREP-ISO-R1-CRASH-I` target as the direct child of the clean,
pushed protocol-review head. Its target and review each have exactly the
three mode-`100644` paths frozen in the protocol, with distinct record and
review memo paths. The record must preserve:

```text
A4-V2-CACHE-PREP-ISO-R1 = CRASH_OR_UNKNOWN
NO_RETRY / NO_RESUME / NO_REPAIR_AUTHORITY
NO_PAR_AUTHORITY / NO_SCIENTIFIC_DECISION
```

CRASH-P does not authorize that target. It also authorizes no fabricated
TERMINAL, runtime-artifact copy/mutation, launcher-incident or receipt-path
reuse, source correction, new probe-to-launch, PREP, CACHE-BIND, PAR-R1,
SRUN, data access, or SAQ/CAQ work.

Scientific-core and implementation-source additions are zero lines. All
added bytes are governance overhead. There is no scientific hot path, timed
region, SOTA comparison, or performance claim:
`PERFORMANCE_NOT_YET_MEASURED` remains exact.

## 8. Consolidated findings and verdict

```text
BLOCKER  0
HIGH     0
MEDIUM   0
LOW      0
```

The target satisfies the fixed review checklist with no finding at LOW
severity or above. Subject only to committing/pushing this exact direct-child
review and satisfying its later ordinary live review-head publication
closure, the bounded verdict is:

```text
START_ONLY_CRASH_RECORD_PROTOCOL_REVIEW_PASS
```

Stop after publication closure and mandatory Meeting Summary Handoff. Do not
form the crash record, repair source, or retry PREP without a new explicit
user authorization.

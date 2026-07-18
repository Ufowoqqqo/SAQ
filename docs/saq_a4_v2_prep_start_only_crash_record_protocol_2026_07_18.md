# A4-V2 PREP-ISO-R1 START-only crash-record protocol

Date: 2026-07-18

Stage: `A4-V2-CACHE-PREP-ISO-R1-CRASH-P`

Authority: the user's exact instruction
`授权 A4-V2-CACHE-PREP-ISO-R1-CRASH-P`.

## 1. Smallest question, scope, and ceiling

The smallest falsifiable question is whether the already consumed R1 PREP
attempt can receive one truthful, finite, independently reviewable terminal
record without changing its frozen `CRASH_OR_UNKNOWN` classification,
mutating runtime artifacts, or creating retry, repair, or downstream
authority.

This stage forms only this protocol, its machine contract, focused root
status, one immutable target, and one exact direct-child review. It forms no
terminal crash record. With zero findings at LOW severity or above, its
maximum outcome is:

```text
START_ONLY_CRASH_RECORD_PROTOCOL_REVIEW_PASS
```

That outcome is governance only. It is not the future reviewed terminal,
PREP readiness, parity, feasibility, performance, SAQ-limitation, novelty,
systems, or method evidence.

## 2. Frozen predecessor and consumed event boundary

The unique invocation ran from clean, pushed, independently reviewed
execution base `eb1b89318d58ef06bff878219346e7b277ab9aea`, tree
`b4003faf2e2db2e871ab2c9604915ed05c0eb946`. Its inseparable immediate
HTTPS admission probe returned that exact OID. That probe and invocation are
consumed permanently and must never be rerun or reused.

The governing CACHE-P protocol states that a valid START followed by an
absent, partial, corrupt, or noncanonical TERMINAL is only
`CRASH_OR_UNKNOWN`. It also states that an uncontained post-START crash may
leave only START, no state is removed or resumed, and every status carries
`NO_PAR_AUTHORITY / NO_SCIENTIFIC_DECISION`.

The predecessor defines commit closures only for a pre-START launcher
incident and for a successful receipt. The first is inapplicable because
durable START exists; the second is inapplicable because no success TERMINAL
or receipt exists. Reusing either path would be a false classification.

## 3. Admission snapshot, not terminal evidence

Read-only inspection after the consumed invocation observed these fixed
source-common-directory objects:

| Object | Mode | Bytes | SHA-256 | Logical state |
| --- | ---: | ---: | --- | --- |
| `.git/saq-a4-v2-isolated-prep.lock` | `0600` | 1,295 | `ef0b9d435a14e0d95f48e72833bad6208134fc1da64a431188f34a4af08d5604` | one canonical START line; no TERMINAL |
| `.git/saq-a4-v2-isolated-prep.stdout` | `0600` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | empty |
| `.git/saq-a4-v2-isolated-prep.stderr` | `0600` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | empty |

START claims the exact R1 authorization SHA-256/bytes
`89e831d1d3fc712ae7b2095c4e2a48eff73b221398b691a00ba887e0ee34e20e /
18,877`, review
`4058a2dd8b1887157b92e0bc7338af788c875708171ee5a6ecc64007d4d4ef59 /
16,578`, inline bootstrap
`d14feb020a1389a6c90f9c3696033f07d0747a9e135be7c9905aeb08d1810b56 /
19,631`, prologue
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7 /
2,778`, execution base `eb1b89318d58ef06bff878219346e7b277ab9aea`,
common directory, capture policy, and umask.
The isolation root `/tmp/saq-a4-v2-par-r1-isolation` is absent; therefore no
outer journal, clone, staging receipt, final receipt, build, verifier, or PAR
artifact exists.

These observations are fixed admission expectations for a future record.
They are not terminal evidence merely because this protocol repeats them.
The future record and its reviewer must independently reobserve exact bytes,
mode, size, line shape, and relevant absence without mutation. Any drift
stops at `RUNTIME_ARTIFACT_STATE_DRIFT_NO_RECORD`; it never permits repair,
cleanup, or inferred status.

## 4. Bounded source-consistency finding

The executor reported exit code 1 and an outer traceback ending in
`NotADirectoryError: [Errno 20] Not a directory: 'self'`. That output is not
present in either registered capture sidecar and is therefore only an
operator observation, not independently bound runtime evidence.

Static source at the immutable execution base contains a mechanism consistent
with that observation: bootstrap `rd()` opens every intermediate component
with the no-follow directory flags, while `kernel_start()` calls it on
`/proc/self/stat`; its exception path calls `kernel_start()` again while
forming fallback process identity. A reviewer may confirm this source fact
but must label it `STATIC_CAUSE_CANDIDATE_NOT_RUNTIME_REPRODUCTION`.

Neither this consistency finding nor a later source repair may retroactively
replace the primary status with `IMPLEMENTATION_INVALID`. Missing TERMINAL
has higher applicable precedence and remains only `CRASH_OR_UNKNOWN`.

## 5. Exact future crash-record topology

Only after this protocol and its review are committed, pushed,
publication-closed, handed off, and pass with zero LOW-or-higher findings may
the user separately authorize exactly:

```text
A4-V2-CACHE-PREP-ISO-R1-CRASH-I
```

The future target must be the direct child of the clean, pushed protocol-
review head and change all and only these mode-`100644` paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_start_only_crash_2026_07_18.md
```

Its exact direct-child review changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_isolated_clone_prep_start_only_crash_independent_review_2026_07_18.md
```

The record must bind the protocol/review commits, execution base, START and
capture identities, exact START claims, isolation/receipt absence, consumed
probe/invocation disposition, status precedence, and the separation between
machine-observed state, operator-reported traceback, and static source
consistency. It must state exactly:

```text
A4-V2-CACHE-PREP-ISO-R1 = CRASH_OR_UNKNOWN
TERMINAL_RECORD = REVIEW_PENDING | REVIEW_PASS | REVIEW_FAIL
NO_RETRY / NO_RESUME / NO_REPAIR_AUTHORITY
NO_PAR_AUTHORITY / NO_SCIENTIFIC_DECISION
```

It must not append a fabricated TERMINAL, copy `.git` artifacts into the
repository, use the launcher-incident or receipt paths, or describe the
bootstrap as having entered PREP `run_from_bootstrap`.

## 6. Current protocol target and review closure

This protocol target is the direct child of clean, pushed execution-base head
`eb1b89318d58ef06bff878219346e7b277ab9aea`. It changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_start_only_crash_record_contract_2026_07_18.json
docs/saq_a4_v2_prep_start_only_crash_record_protocol_2026_07_18.md
```

Its exact direct-child independent review changes all and only:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_start_only_crash_record_protocol_independent_review_2026_07_18.md
```

After each push, one bounded sanitized HTTPS publication-equality observation
must return the corresponding exact OID. The target result is recorded and
independently checked in the review memo. The review-head result is a live,
non-evidentiary closure predicate and is not Meeting Summary evidence. These
two publication checks are not PREP admission probes and grant no launch.

## 7. Independent review requirements

The sole reviewer must independently establish:

1. exact parent, tree, modes, four-path target, three-path review, and remote
   target equality;
2. byte preservation of every other tracked path, especially the 37-source/
   38-unit tree, PREP source, schemas, predecessor protocol, authorization,
   and authorization review;
3. exact read-only runtime-artifact identities and START-only shape, with no
   token, capture, isolation-root, or receipt mutation;
4. applicability of `CRASH_OR_UNKNOWN` and inapplicability of both existing
   launcher-incident and receipt commit closures;
5. source consistency without runtime reproduction or status reclassification;
6. sufficiency and uniqueness of the future target/review topology; and
7. every claim ceiling, authority separation, stop rule, and prohibition.

The reviewer may record PASS or FAIL but may not edit either protocol object.
Any LOW-or-higher finding forces FAIL and a user checkpoint.

## 8. Overhead, prohibitions, and stop rule

Scientific algorithmic core and implementation source added are zero lines.
The protocol, contract, root status, and review are permanent governance
overhead. There is no scientific hot path, timed region, SOTA comparison, or
performance claim; `PERFORMANCE_NOT_YET_MEASURED` remains exact.

This stage permits no token/capture append, truncate, chmod, copy, rename,
cleanup, deletion, or replacement; no isolation root, journal, clone,
receipt, PREP, Python, DNF, syntax/import, compiler/build/test, cache verifier,
CACHE-BIND, PAR-R1, SRUN, quarantine, dataset/query/index/result access,
environment mutation, or SAQ/CAQ change. It permits no source repair and no
actual crash-record target.

CRASH-P stops after exact target/review commit, push, publication closure,
mandatory Meeting Summary Handoff, and user report, or earlier on a LOW+
finding, artifact drift, unexpected path/mode, dirty/unpublished parent, need
for execution, or need to widen the semantic delta. Even after PASS, do not
form the crash record or repair bootstrap without separate explicit authority.

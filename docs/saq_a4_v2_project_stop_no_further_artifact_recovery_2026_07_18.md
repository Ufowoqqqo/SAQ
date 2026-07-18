# Attempt 4 V2 project stop: no further artifact recovery

Date: 2026-07-18

Branch: `saq-arbitrary-cardinality-feasibility-v2`

Decision base: `8bec546c6dc59d9d07a0ba6da5590e61015d38b8`

Decision class: project portfolio allocation, documentation only

## Decision

The project stops Attempt 4 V2 with portfolio status:

```text
STOP_NO_FURTHER_ARTIFACT_RECOVERY
```

No further effort will be allocated on this branch to recovering the consumed
`A4-V2-CACHE-PREP-ISO-R1` attempt or advancing its artifact-governance chain.
This is a project stop decision, not an executor terminal record and not a
reclassification of machine state.

The frozen machine/runtime status remains exactly:

```text
A4-V2-CACHE-PREP-ISO-R1 = CRASH_OR_UNKNOWN / START_ONLY
```

The valid START record and empty capture sidecars establish only that the
authorized invocation started. The absent canonical TERMINAL prevents any
stronger runtime classification under the frozen precedence rules.

The following stage remains unchanged:

```text
A4-V2-CACHE-PREP-ISO-R1-CRASH-I = NOT_AUTHORIZED / NOT_RUN
```

This memo does not form, approximate, or substitute for the three-path crash
terminal record specified by the reviewed CRASH-P protocol.

## Frozen scientific interpretation

Attempt 4 V2 produced no scientific result. In particular, this decision
establishes none of the following:

- whether the proposed arbitrary-cardinality construction is correct;
- whether its synthetic admission panel would pass;
- whether its scientific hot path is affordable;
- whether the method changes estimator error or recall;
- whether any SAQ-specific limitation is material on base data; or
- whether any Pareto frontier moves against CAQ or E-RaBitQ.

No artifact-validity terminal outcome exists for the consumed PREP attempt.
The status is not `PASS`, `FAIL`, `ARTIFACT_INVALID`, `PRECONDITION_FAILED`,
or `EXECUTION_FAILED`. It remains `CRASH_OR_UNKNOWN` only.

No performance measurement exists for Attempt 4 V2. Its performance status
is:

```text
PERFORMANCE_NOT_YET_MEASURED
```

No build, parity result, synthetic run, real-data result, independent runtime
reproduction, or SOTA comparison may be inferred from the reviewed source and
protocol artifacts.

## Why the project stops

The branch has accumulated a long sequence of authorization, protocol,
erratum, source-history, cache, host-binding, and recovery stages without
reaching a scientific execution result. The current root status enumerates
more than twenty governance and repair nodes after protocol design, while the
scientific construction has not entered a valid timed or correctness-tested
run.

That sequence added source-static and artifact-governance confidence, but it
did not add decision-relevant evidence about the research hypothesis. A
further CRASH-I record would improve provenance only; it could not itself
establish correctness, affordability, estimator impact, or frontier movement.
It would also be followed by more separately authorized recovery, binding,
PAR-R1, and SRUN gates before any scientific evidence could exist.

The support/protocol burden has therefore clearly exceeded the executed
scientific core: the latter is zero for this attempt, whereas the former spans
the documented multi-stage chain and its static implementation. Continuing
would violate the project's efficiency rule to optimize for new
decision-relevant evidence per unit of reviewer attention, context, wall time,
and code.

This is sufficient reason to stop the workstream even though the underlying
runtime state remains unresolved. A portfolio decision need not manufacture
an artifact terminal result before declining further investment.

## Preservation boundary

All existing committed protocol, source, authorization, review, and status
evidence is preserved in Git history. In particular, preserve:

- the consumed PREP authorization and execution-base ancestry;
- the canonical START-only record description already committed;
- the reviewed CRASH-P protocol and contract;
- the independent CRASH-P review at the current base; and
- all earlier negative artifact and source-review evidence.

This closure performs no cleanup. It does not inspect, delete, rewrite, move,
or repair any token, capture, isolation, staging, journal, clone, receipt,
cache, or other machine-state path. Untracked or ignored outputs remain
nonevidence and outside this documentation-only decision.

The following actions remain unauthorized and must not be performed as part
of this closure:

- `A4-V2-CACHE-PREP-ISO-R1-CRASH-I`;
- any PREP retry, resume, replay, or replacement invocation;
- source or environment repair for another PREP attempt;
- CACHE-BIND or any new artifact binding;
- `A4-V2-PAR-R1` build or parity work;
- `A4-V2-SRUN`;
- benchmark, base, query, ground-truth, cluster, or index reads; and
- any SAQ/CAQ, estimator, packing, plan, or search modification.

## Reopening rule

This branch is closed as a research workstream. Ordinary instructions to
continue, retry, repair, record, or run do not reopen it.

Reopening would require a new explicit user decision that names a new
research question and supplies a fresh protocol from a clean branch or named
snapshot. That decision must justify why the expected scientific evidence is
worth the support/recovery cost and must freeze a cheap falsification gate
before implementation. It must not reuse the consumed PREP authority or
reinterpret the unresolved START-only state.

The stopped workstream is negative portfolio evidence: a tightly governed
artifact path can become too costly to justify before reaching the scientific
question. It is not negative evidence about the proposed algorithm itself.

## Closure verification

This closure is limited to this memo and focused root-status updates. The
only permitted checks are Git identity/status, focused text diff, and
whitespace validation. No build, import, syntax execution, test, probe,
runtime-state read, experiment, or data access belongs to this decision.

At this checkpoint:

```text
scientific evidence gained                 none
scientific code changed                    0 lines
machine/runtime status                     CRASH_OR_UNKNOWN / START_ONLY
CRASH-I                                    NOT_AUTHORIZED / NOT_RUN
artifact-validity terminal outcome         none
performance status                         PERFORMANCE_NOT_YET_MEASURED
fair SOTA comparison                       PERFORMANCE_NOT_YET_MEASURED
portfolio status                           STOP_NO_FURTHER_ARTIFACT_RECOVERY
active recovery/build/experiment processes none started by this closure
```

The smallest next action is independent read-only review of the immutable
documentation commit, followed by meeting-summary synchronization only if that
review accepts the status separation. Any LOW-or-higher finding that confuses
portfolio status with runtime or artifact status is a stop condition for that
handoff.

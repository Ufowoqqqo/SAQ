# TASK.md

## Active Task

Maintain the canonical research-direction registry and cross-attempt meeting
deck on `saq-meeting-summary`. This branch summarizes committed and
independently reviewed milestones from research branches; it does not execute
those research protocols.

Current summary inventory:

- `docs/saq_research_direction_registry.md` maps every audited SAQ branch to a
  normalized direction, scientific state, claim ceiling, and reporting state.
  Its user-confirmed completed-meeting boundary is the 2026-07-09 deck at
  `saq-graph-traversal-analysis@322214f`, with scientific content through
  `d94279d`. `R01`--`R05` are `REPORTED`; `R06` is `UPDATE_PENDING` because of
  its later evidence and closure; `R07`--`R12` are `UNREPORTED`.

- `docs/saq_research_progress_meeting_slides_2026_07_09.md` is the immutable
  completed-meeting deck, copied exactly from the registered source commit.
- `docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` is the superseded,
  unpresented intermediate draft originally hosted at
  `saq-caq-one-shell-repair@433e8ea`.
- `docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md` is the current,
  unpresented successor draft. It queues `R07`, `R08`, `R10`, `R11`, and
  `R12`; its Attempt 4 scientific snapshot is
  `saq-arbitrary-cardinality-feasibility-v2@b89dabe`, whose latest material
  milestone is host-rebind erratum target/review `5a47fed/@b89dabe`.

## Current Attempt 4 Boundary

The deck may currently report only:

```text
A4-0  PASS_INSTRUMENT_ONLY
A4-1P FROZEN_NOT_AUTHORIZED / NOT_RUN
A4-1S NO_GO_EXACT_SOLVER_COST / REVIEWED_TERMINAL
A4-V2-R GO_PROTOCOL_DESIGN / REVIEWED
A4-V2-P PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION / REVIEWED
A4-V2-P-ERRATUM PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS
A4-V2-I SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS
A4-V2-PAR ARTIFACT_INVALID / REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY
A4-V2-I-R1 SOURCE_REPAIR_STATIC_REVIEW_PASS
A4-V2-CACHE-P EXACT_TARGET_INDEPENDENT_REVIEW_PASS
A4-V2-CACHE-I GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
A4-V2-CACHE-PREP-AUTH PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
A4-V2-PREP-HOST-P HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS
A4-V2-PREP-HOST-I-AUTH / HOST-I NOT_AUTHORIZED
A4-V2-CACHE-PREP-ISO-R1 NOT_AUTHORIZED
A4-V2-SRUN NOT_AUTHORIZED
```

The six canonical A4-1S parity artifacts are committed at `335837e`; their
independent review is committed at `988ace0`. The cost evidence is committed
at `9ce1052`, and its independent review and terminal decision are committed
at `f1b464b`. The frozen pipeline stopped after 61 scalar-coordinate shards:
timed CPU was `34,805,155,525 us`, and the registered `5/2` projection was
`24.170246892361` CPU-hours, above the 24-hour ceiling. Canonical shard
serialization is included in that cost, so this is not a solver-only
complexity claim. There is no natural-data, block-VQ, ANN, or SAQ integration
result. The A4-1S formulation is closed, the base gate was not run, and
untracked files in an experiment worktree are not evidence.

The V2 primary-source review is committed at `c4ccea3`, and the parent
protocol is independently reviewed at `f86a51d`. Source-only A4-V2-I
inspection then exposed a terminal-P receipt/publication self-reference before
any implementation commit or review pass. The additive protocol correction is
committed at `f13a383` and independently reviewed at branch head `98e6999`
with verdict `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS`. V2 does not overturn
the old stop. It replaces neither the old timer nor its decision; instead it
preregisters a new internal synthetic comparative-instrument FOM:

```text
T_instrument = C_setup + C_core + C_bundle_io
PASS iff T_instrument <= 34,560,000,000 CPU microseconds
```

Build, parity, evidence emission, independent replay, archive, memory, and
bytes remain separately metered and mandatory. The old `5/2` projection does
not transfer to this FOM, so the protocol makes no real-data, SAQ index-build,
deployment-cost, ANN, or systems claim. The erratum adds one finite one-file
`PAR_report` after terminal P without changing the parent blobs, scientific
computation, FOM, threshold, parity/retry rules, or status precedence. Its
5,171-byte maximal seal is a conservative syntactic schema bound, not an
admissible resource observation. Initial implementation commit `3a4f7c5`
failed static review and remains non-evidence. Corrected source `482c401` and
its 35-source manifest reached static review only.

The user then explicitly authorized A4-V2-PAR at reviewed execution base
`2e983a0`. Its one frozen invocation returned exit `3` and frozen status
`ARTIFACT_INVALID` before any B/P worker: `/bin/python` was a symlink rejected
by the no-follow leader-identity read. No build, NumPy authority, PCG64
fixture, parity case, receipt, ledger, build manifest, parity summary,
artifact index, or seal was produced. Terminal result `30dfada` passed three-
track independent review at branch head `fd5367e`. It establishes no valid PAR
authority and no scientific decision. Empty staging and ignored caches are
WIP/non-evidence.

Subsequent reviewed work stayed at artifact-governance ceilings. I-R1 repaired
the source-only executable identity; CACHE-P selected sanitized remote
isolation and rejected direct PAR-R1; CACHE-I reached a generic source/static
pass; and PREP authorization target/review `e7f940e/@16a8201` froze only a
dormant contract. Before PREP, static checking found that a root RPM update
had replaced the frozen `.el9_8` Python leader with `.el9_8.2`; PREP was not
invoked, START was not created, and no runtime terminal status exists.

The bounded additive host-rebind erratum target/review `5a47fed/@b89dabe`
passed exact-commit independent review with 0 LOW+ findings. Its ceiling is
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`, not host rebound, PREP readiness,
feasibility, performance, or scientific evidence. The old invocation
authority is unspent but nontransferable, and the old probe is unspent but
superseded and must never run or be reused.

## Next Admissible Summary Work

There is no active source-branch execution authority. The next admissible
source-branch node is a separately user-authorized
`A4-V2-PREP-HOST-I-AUTH`; only after its review could a separately authorized
HOST-I coherently update the five affected sources and seven derived
authority objects. Fresh PREP authorization/review, a new actual-invocation
grant and immediate probe, CACHE-BIND, PAR-R1, SRUN, data reads, generated
scientific evidence, and SAQ changes all remain unauthorized. This summary
handoff grants none of them.

For the next handoff, re-read `AGENTS.md` and the registry, fetch, require this
worktree to be clean and equal to its remote, record that remote commit, and
acquire the mandatory common-directory summary lock before editing:

1. verify the source branch and exact commit;
2. read the authoritative evidence and artifact paths from that commit;
3. update the registry's audited head, scientific snapshot, research state,
   status, claim ceiling, evidence paths, and next authorized step;
4. preserve `UNREPORTED`, or set a previously reported direction to
   `UPDATE_PENDING`, according to the registry rollover rules;
5. update the current deck only if that direction is selected for the meeting;
6. stage only the exact summary files and review `git diff --cached --check`
   plus the focused cached documentation diff; and
7. re-fetch and compare the remote with the recorded starting commit; if it
   moved, stop and integrate deliberately while retaining the lock; and
8. commit and push only the summary documents without force, then release the
   lock after success or a clean abort.

Writing a result into a draft deck never marks it `REPORTED`. Only a user-
confirmed completed meeting with an exact deck commit can roll reporting state
forward.

Do not merge or cherry-pick an experiment branch merely to update the deck.
Do not copy experiment code, generated artifacts, untracked files, or
provisional outcomes. Never merge this summary branch back into an experiment
branch.

## Not Authorized Here

- implementing or rerunning A4-1S, or opening its foreclosed base gate;
- implementing or executing A4 V2 on this summary branch; A4-V2-PAR is a
  reviewed terminal `ARTIFACT_INVALID` with no valid PAR authority, and
  HOST-I, PREP, rerun, A4-V2-SRUN, data, and SAQ work remain unauthorized;
- opening registered base, query, ground-truth, or index artifacts;
- modifying SAQ/CAQ, index, estimator, packing, or search code;
- expanding any source branch's experimental authorization; or
- presenting instrument validation as natural-data, ANN, or systems evidence.

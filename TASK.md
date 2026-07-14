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
  `saq-arbitrary-cardinality-analysis@f1b464b`.

## Current Attempt 4 Boundary

The deck may currently report only:

```text
A4-0  PASS_INSTRUMENT_ONLY
A4-1P FROZEN_NOT_AUTHORIZED / NOT_RUN
A4-1S NO_GO_EXACT_SOLVER_COST / REVIEWED_TERMINAL
```

The six canonical A4-1S parity artifacts are committed at `335837e`; their
independent review is committed at `988ace0`. The cost evidence is committed
at `9ce1052`, and its independent review and terminal decision are committed
at `f1b464b`. The frozen pipeline stopped after 61 scalar-coordinate shards:
timed CPU was `34,805,155,525 us`, and the registered `5/2` projection was
`24.170246892361` CPU-hours, above the 24-hour ceiling. Canonical shard
serialization is included in that cost, so this is not a solver-only
complexity claim. There is no natural-data, block-VQ, ANN, or SAQ integration
result. The formulation is closed, the base gate was not run, and untracked
files in an experiment worktree are not evidence.

## Next Admissible Summary Work

Wait for another source branch to produce a committed and independently
reviewed protocol, gate result, or terminal decision. Attempt 4 has no further
authorized experiment. For the next handoff, re-read `AGENTS.md` and the
registry, fetch, require this
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
- opening registered base, query, ground-truth, or index artifacts;
- modifying SAQ/CAQ, index, estimator, packing, or search code;
- expanding any source branch's experimental authorization; or
- presenting instrument validation as natural-data, ANN, or systems evidence.

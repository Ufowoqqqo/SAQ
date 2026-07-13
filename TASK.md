# TASK.md

## Active Task

Maintain the canonical research-direction registry and cross-attempt meeting
deck on `saq-meeting-summary`. This branch summarizes committed and
independently reviewed milestones from research branches; it does not execute
those research protocols.

Current summary inventory:

- `docs/saq_research_direction_registry.md` maps every audited SAQ branch to a
  normalized direction, scientific state, claim ceiling, and reporting state.
  Its imported completed-meeting proxy is the historical Attempts 1--3 deck at
  `saq-meeting-summary@5cdc270`; the actual meeting date is not recorded.
  Attempt 4 remains `UNREPORTED` even though it is included in the successor
  draft.

- `docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` is the immutable
  historical Attempts 1--3 snapshot from
  `saq-caq-one-shell-repair@433e8ea`.
- `docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md` is the current deck.
  Its Attempt 4 scientific snapshot is
  `saq-arbitrary-cardinality-analysis@3c0a49f`.

## Current Attempt 4 Boundary

The deck may currently report only:

```text
A4-0  PASS_INSTRUMENT_ONLY
A4-1P FROZEN_NOT_AUTHORIZED
A4-1S FROZEN_AUTHORIZED_NOT_IMPLEMENTED
```

There is no committed A4-1S runner, parity result, cost projection, natural-
data outcome, ANN result, or SAQ integration result in the cited snapshot.
Untracked files in an experiment worktree are not evidence.

## Next Admissible Summary Work

Wait for a source branch to produce a committed and independently reviewed
protocol, gate result, or terminal decision. Then re-read `AGENTS.md` and the
registry, fetch, require this worktree to be clean and equal to its remote,
record that remote commit, and acquire the mandatory common-directory summary
lock before editing:

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

- implementing or running A4-1S;
- opening registered base, query, ground-truth, or index artifacts;
- modifying SAQ/CAQ, index, estimator, packing, or search code;
- expanding any source branch's experimental authorization; or
- presenting instrument validation as natural-data, ANN, or systems evidence.

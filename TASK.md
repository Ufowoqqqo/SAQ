# TASK.md

## Active Task

Maintain the canonical cross-attempt meeting deck on
`saq-meeting-summary`. This branch summarizes committed and independently
reviewed milestones from research branches; it does not execute those research
protocols.

Current deck inventory:

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
protocol, gate result, or terminal decision. Then, if this worktree is clean
and has no known concurrent editor:

1. verify the source branch and exact commit;
2. read the authoritative evidence and artifact paths from that commit;
3. record the status, claim ceiling, and next authorized step in the current
   deck;
4. update the evidence map and source snapshot;
5. run `git diff --check` and review the focused documentation diff; and
6. commit and push only the summary documents.

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

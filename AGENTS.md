# AGENTS.md

Durable guidance for Codex sessions on the `saq-meeting-summary` branch.

## Branch Purpose

This is the canonical cross-attempt meeting-summary branch. It preserves
historical decks and maintains both the research-direction registry and the
current project-level deck across research branches. It is not an experiment-
execution branch, a source-code integration branch, or a replacement for the
authoritative protocol and evidence files on the source branches.

Do not run research experiments, read newly authorized datasets, or develop
methods here. Preserve completed decks as immutable historical snapshots.
Maintain `docs/saq_research_direction_registry.md` as the single source of
truth for direction, branch, scientific-snapshot, and reporting state. When a
new attempt or material milestone must be presented, create or update the
current successor deck without rewriting the older deck's history.

## Source And Claim Discipline

Only summarize evidence that is committed and independently reviewed on its
source branch. Every material update must state:

- the source branch and exact commit;
- the protocol, gate result, or terminal decision;
- the maximum claim supported by that evidence;
- the authoritative document and artifact paths; and
- the next step that is explicitly authorized.

Untracked implementation files, generated local artifacts, running jobs, and
provisional outcomes are not evidence and must not appear as results. A frozen
protocol is not an execution result; authorization is not completion; a
synthetic witness is not natural-data or ANN evidence.

The registry and deck record authorization; neither grants authorization to a
source branch.

## Meeting Summary Handoff

The session producing a committed and reviewed protocol, gate result, or
terminal decision owns the handoff to this branch. Locate this linked worktree
with `git worktree list`; do not rely on a hard-coded `/tmp` path.

Before editing, re-read this file and
`docs/saq_research_direction_registry.md`, fetch, require a clean summary
worktree whose HEAD equals `origin/saq-meeting-summary`, and record that exact
starting commit. One summary writer is mandatory: atomically acquire a lock
directory named `saq-meeting-summary-edit.lock` under the Git common directory
before the first edit. If the lock cannot be acquired, or cleanliness and
remote equality cannot be established, do not edit; report the source branch,
commit, status, claim ceiling, evidence paths, and next authorized step to the
user instead.

Update the registry first from the named committed sources. Update the current
deck only when the direction is selected for that meeting or an already-
selected direction has a newer material milestone. Do not copy experiment
code, generated artifacts, or unrelated branch files. Do not merge or cherry-
pick an experiment branch merely to update summary documents, and never merge
this summary branch back into an experiment branch. Re-fetch before push,
verify the focused diff, and compare the remote with the recorded starting
commit. If it moved, stop and integrate deliberately while retaining the lock.
Commit the summary update separately, never force-push
`saq-meeting-summary`, and release the lock after a successful push or a clean
abort.

## Reporting State

Use the exact definitions and rollover procedure in
`docs/saq_research_direction_registry.md`.

- New directions start `UNREPORTED`.
- A new branch enters the branch crosswalk as `PENDING_REVIEW` without a
  scientific claim; create its direction row only after a committed and
  independently reviewed milestone.
- Draft-deck inclusion does not mean a meeting occurred and does not change
  reporting state.
- A material committed milestone after a reported snapshot changes the state
  to `UPDATE_PENDING`; wording or handoff-only commits do not.
- Change a snapshot to `REPORTED` only after the user confirms the completed
  meeting and the exact deck commit. Record `reported_through` and the report
  source at the same time.
- A bare mention, baseline use, or “do not reopen” reference is not substantive
  reporting.

## Summary Inventory

- `docs/saq_research_direction_registry.md` is the living canonical direction,
  branch, evidence-boundary, and reporting-state registry.
- `docs/saq_research_progress_meeting_slides_2026_07_09.md` is the immutable,
  confirmed completed-meeting deck, copied from
  `saq-graph-traversal-analysis@322214f` with only the trailing blank line
  normalized. Its scientific snapshot is
  `saq-graph-traversal-analysis@d94279d`; later edits to the same source-branch
  filename are post-meeting evidence and are not part of this deck.
- `docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` is a superseded,
  unpresented intermediate draft retained for provenance. It is not a
  completed-meeting deck.
- `docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md` is the current,
  unpresented cross-attempt draft. Its Attempt 4 status must cite the exact
  source snapshot and must be revised only after another committed and
  reviewed milestone.

## Reporting Standard

Write as a doctoral researcher seeking a SIGMOD/VLDB/ICDE-level contribution.
Separate mathematical facts, instrument validation, offline data evidence,
ANN evidence, and systems evidence. State the closest prior work and novelty
boundary, construction/storage/query costs, likely reviewer objections, and
the exact reason a direction continues or stops.

Do not present known primitives, bug fixes, source validation, tooling, or
parameter variants as contributions. Preserve negative evidence and never add
post-hoc datasets, thresholds, seeds, or variants to rescue a failed gate.

## Verification

Before committing a registry or deck update:

```bash
git diff --cached --check
git diff --cached -- AGENTS.md TASK.md docs/
git status --short --branch
```

Stage only the exact intended summary files before running these checks. Do
not commit datasets, indexes, binaries, build products, caches, or experiment
worktrees.

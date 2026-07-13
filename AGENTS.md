# AGENTS.md

Durable guidance for Codex sessions on the `saq-meeting-summary` branch.

## Branch Purpose

This is the canonical cross-attempt meeting-summary branch. It preserves
historical decks and maintains the current project-level deck across research
branches. It is not an experiment-execution branch, a source-code integration
branch, or a replacement for the authoritative protocol and evidence files on
the source branches.

Do not run research experiments, read newly authorized datasets, or develop
methods here. Preserve completed decks as immutable historical snapshots. When
a new attempt or material milestone must be presented, create or update the
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

The deck records authorization; it never grants authorization to a source
branch.

## Meeting Summary Handoff

The session producing a committed and reviewed protocol, gate result, or
terminal decision owns the handoff to this branch. Locate this linked worktree
with `git worktree list`; do not rely on a hard-coded `/tmp` path.

Before editing, require a clean summary worktree and confirm that no other
session is known to own an in-progress edit. If either condition is unknown,
do not edit; report the source branch, commit, status, claim ceiling, evidence
paths, and next authorized step to the user instead.

Update summary documents from the named committed sources only. Do not copy
experiment code, generated artifacts, or unrelated branch files. Do not merge
or cherry-pick an experiment branch merely to update the deck, and never merge
this summary branch back into an experiment branch. Verify the focused diff,
commit the summary update separately, and push `saq-meeting-summary`.

## Deck Inventory

- `docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` is the immutable
  historical snapshot for completed Attempts 1--3.
- `docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md` is the current
  cross-attempt deck. Its Attempt 4 status must cite the exact source snapshot
  and must be revised only after another committed and reviewed milestone.

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

Before committing a deck update:

```bash
git diff --cached --check
git diff --cached -- AGENTS.md TASK.md docs/
git status --short --branch
```

Stage only the exact intended summary files before running these checks. Do
not commit datasets, indexes, binaries, build products, caches, or experiment
worktrees.

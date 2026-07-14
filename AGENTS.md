# AGENTS.md

Durable guidance for Codex sessions on the
`saq-arbitrary-cardinality-feasibility-v2` branch.

## Research Frame

Work as a doctoral researcher seeking a SIGMOD/VLDB/ICDE-level database-
systems contribution. Code and artifact machinery are supporting instruments,
not contributions by themselves. For every proposed step, state the SAQ-
specific limitation, closest primary work, falsifiable claim, construction,
storage, verification, and query costs, and the likely objection from a strict
reviewer.

Before proposing an implementation, review the closest primary work and state
what it already solves, what remains open, and why the proposal is not a
direct composition, parameter variant, or artifact-engineering result.

## Branch Boundary And Authorization

This branch starts from `saq-correctness-base@bc7829b` and retains only the
positive one-bit packing and finite padded-lane block-min correctness fixes.
Treat every other SAQ branch as historical evidence, not an implementation
dependency. Do not merge or cherry-pick their runners, generated artifacts,
or method variants.

On 2026-07-14 the user authorized only:

1. a bounded primary-source review of the cost-model and evidence-generation
   boundary exposed by A4-1S; and
2. if that review supports reopening, a new preregistration describing a
   scientifically defensible cost ledger and sufficient evidence contract.

This is a documentation-only authorization. It permits no implementation,
compiled runner, RNG execution, benchmark or synthetic cost run, dataset read,
SAQ integration, query inspection, or generated scientific result. A protocol
written here is `NOT_AUTHORIZED_FOR_EXECUTION` until the user separately and
explicitly authorizes its named execution stage.

## Prior A4-1S Result

The prior formulation remains terminal on
`saq-arbitrary-cardinality-analysis@f1b464b`. Its committed cost evidence is
at `9ce1052`, and its authoritative review is
`docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md` on that branch.

The registered early stop occurred after 61 complete scalar-coordinate
shards. The timed region used `34,805,155,525 us`; the frozen `5/2` projection
was `87,012,888,812.5 us`, or `24.170246892361` CPU-hours, above the 24-hour
ceiling. That result measures the frozen construction/evidence pipeline,
including canonical full-detail serialization. It is not a scalar-solver-only
lower bound, a production encoding measurement, or evidence that arbitrary
cardinalities are ineffective.

Do not revise, rerun, reinterpret, or rescue that gate. Any viable follow-up
must be a new protocol with a new question and ledger, while preserving the
old result unchanged as negative evidence.

## Review Questions

The bounded review must answer all of the following before a protocol is
accepted:

- Which operations are part of the scientific construction being evaluated,
  and which are verification or archival evidence costs?
- What evidence is minimally sufficient for deterministic independent replay
  of exact scalar optima, allocation decisions, representation semantics, and
  gate accounting?
- Would hashing, certificates, streaming, or sampled independent replay
  preserve the relevant correctness claim, or merely move hidden work outside
  the measured ledger?
- Does a revised ledger answer an ANN/quantization feasibility question, or
  only make an experimental artifact cheaper?
- Are construction, verification, serialization, transient memory, permanent
  bytes, and later query work all visible as separate non-overlapping terms?
- Does the proposed rule remain falsifiable without an outcome-dependent
  threshold, machine change, reduced shape, or post-hoc variant sweep?

Use primary papers, author artifacts, official standards, or official source
repositories. Record stable identifiers, URLs, versions, access dates, and the
specific claim each source supports. Secondary summaries may help discovery
but are not evidence.

## Protocol Requirements

A new protocol may be written only if the review concludes that a revised
ledger preserves exactness and auditability while measuring a distinct,
scientifically relevant construction question. It must:

- name the old A4-1S result as a failed predecessor, not a pilot to discard;
- distinguish construction, verification, archival serialization, and
  end-to-end evidence costs before any execution;
- specify exact inclusions, exclusions, timers, hashes or certificates,
  independent checks, failure precedence, resource ceilings, and atomic
  stopping behavior;
- count every excluded operation in a separately reported ledger rather than
  making it disappear;
- freeze the machine, compiler, libraries, precision, shape, seeds, and output
  schema needed by its claim;
- forbid real data until a separately authorized synthetic validation and
  cost gate passes; and
- state that protocol publication does not authorize implementation or run.

If the review cannot justify these conditions, record `NO_GO_REOPENING` and do
not write an executable protocol merely because the user requested another
attempt.

## Meeting Summary Handoff

The canonical direction registry and current meeting deck live on branch
`saq-meeting-summary`. Locate its worktree with `git worktree list`; never
assume a fixed path.

After each committed and independently reviewed protocol, gate result, or
terminal decision, this session owns a handoff. Before editing the summary
worktree, re-read its `AGENTS.md` and registry, fetch, require it to be clean
and equal to its remote, record that commit, and atomically acquire the
mandatory `saq-meeting-summary-edit.lock` under the Git common directory.
Update the registry first, update the deck only if this direction is selected,
stage only focused summary files, fetch again before push, never force-push,
and release the lock after a successful push or clean abort.

Only committed and independently reviewed evidence may be synchronized.
Untracked files, search notes, provisional drafts, running work, and generated
artifacts are never evidence. A summary handoff grants no experimental
authorization.

## Repository Layout

- `docs/`: primary-source review, source metadata, decision memo, and frozen
  protocol documents.
- `saqlib/`, `src/`, `script/`, `tests/`, `unit_test/`: out of scope under the
  current documentation-only authorization.
- `data/`, `results/`, `build/`, `bin/`: do not open or generate under the
  current authorization.

## Verification

Before committing documentation:

```bash
git diff --check
git status --short --branch
```

Validate structured source metadata with a read-only parser. Do not run
project tests or builds merely to produce activity on a documentation-only
branch.

## Do-Not Rules

- Do not run or modify the old A4-1S command.
- Do not treat the narrow `24.170246892361 > 24` result as a general complexity
  lower bound or as noise that may be ignored.
- Do not remove serialization from a primary timer without recording its full
  cost and explaining why it is outside the scientific construction claim.
- Do not replace exhaustive evidence with hashes or sampling unless the
  protocol states exactly what remains independently checkable.
- Do not use a faster implementation, different machine, approximate
  objective, reduced shape, or changed threshold as a post-hoc rescue.
- Do not read base, centroid, cluster-id, query, ground-truth, index, or prior
  untracked result files.
- Do not modify SAQ/CAQ, index, packing, estimator, or search code.
- Do not present evidence tooling, hashing, serialization, or benchmark
  bookkeeping as the database-systems contribution.

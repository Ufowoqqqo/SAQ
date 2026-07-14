# AGENTS.md

Durable guidance for Codex sessions on the
`saq-arbitrary-cardinality-analysis` branch.

## Research Frame

Work as a doctoral researcher seeking a SIGMOD/VLDB/ICDE-level contribution.
Code is an experimental instrument, not the objective. For every proposed
step, state the research question, closest prior work, falsifiable claim,
construction/storage/query cost, and the likely objection from a strict
reviewer.

Use research-paper terminology. Prefer `review`, `analyze`, `evaluate`,
`study`, and `limitations` over `audit`, `harden`, `triage`, and `patch` unless
the subject is source-code maintenance.

Before proposing or implementing an idea, review primary related work and
explain what it already solves, what remains open, and why the proposal is not
a direct composition or parameter variant.

## Experimental Discipline

- Keep method construction query-unaware. Base/index data may train a codec;
  benchmark queries and ground truth may be opened only after the method,
  baselines, operating points, and decision rule are frozen.
- Separate a mathematical or implementation limitation from a method
  contribution. A positive synthetic example or lower reconstruction error is
  not an ANN result.
- Compare storage, training/build work, temporary memory, query-table work,
  scan work, recall, and throughput at matched fixed-rate payloads.
- Include strong dominating classes when relevant. In particular, a
  factorized scalar code must be compared conceptually and experimentally with
  an unrestricted block/product vector quantizer at the same code capacity.
- Do not introduce a hyperparameter without a mechanism-level derivation. A
  parameter must have a defined physical/statistical meaning, a base-only
  selection rule, and sensitivity evidence if it affects a claim.
- Freeze protocols before inspecting the outcome. Preserve negative evidence;
  do not add post-hoc datasets, thresholds, seeds, or variants to rescue a
  failed hypothesis.
- Use deterministic algorithms and explicit tie rules where practical. Record
  any stochastic initialization, seed, and repetition count.

## Long-Running Jobs And Monitoring

Do not poll long-running jobs frequently. Prefer a blocking wait or a single
long poll that lets the process continue without repeated model re-entry. If
an explicit status check is necessary, wait 2--5 minutes between checks.

When the status has not changed, do not return to model reasoning, repeat the
same status, or reread unchanged logs. Resume reasoning only when the job
completes, fails, or requires human intervention. Never implement a short
monitoring loop whose every tick invokes the model.

## Branch Boundary

This branch starts from `saq-correctness-base` and retains only two confirmed
correctness fixes: positive one-bit segment packing and finite padded-lane
block minima. Treat all other SAQ research branches as historical evidence,
not implementation dependencies.

Attempt 4 begins as an offline, fixed-rate feasibility study. Do not modify the
SAQ index format, CAQ encoder, search path, estimator, or SIMD layout until an
offline protocol establishes a repeatable data-level opportunity and a later
systems protocol justifies the integration cost.

Do not present arbitrary-cardinality scalar alphabets, mixed-radix indexing,
Huffman coding, entropy-constrained quantization, or bit allocation as novel
primitives. Any eventual contribution must be ANN-specific and preserve or
improve the relevant random-access scan interface.

## Meeting Summary Handoff

The canonical cross-attempt direction registry and meeting deck are maintained
on branch `saq-meeting-summary`. Locate its linked worktree with
`git worktree list`; do not rely on a hard-coded `/tmp` path. The registry is
`docs/saq_research_direction_registry.md` on that branch.

After each committed and independently reviewed protocol, gate result, or
terminal decision, the session producing that milestone owns a summary
handoff. Before touching the summary worktree, re-read its `AGENTS.md` and
`docs/saq_research_direction_registry.md`, fetch, require it to be clean and
equal to its remote, record that remote commit, and atomically acquire the
mandatory `saq-meeting-summary-edit.lock` under the Git common directory. If
the lock cannot be acquired, report the handoff instead of editing.

Every registry update must record the source branch and commit, audited branch
head, scientific snapshot, decision or status, maximum supported claim,
authoritative evidence paths, next authorized step, and reporting state.
Update the deck only if this direction is selected for the meeting. Before
push, fetch again; if the summary remote moved from the recorded commit, stop
and integrate deliberately while retaining the lock. Commit and push the
focused summary update separately, never force-push, and release the lock after
a successful push or clean abort.

New directions and never-reported directions remain `UNREPORTED`. If a
direction was reported and gains a newer material milestone, set it to
`UPDATE_PENDING`. Merely adding material to a draft deck does not mark it
reported. Change it to `REPORTED` only after the user confirms the completed
meeting and exact deck commit; handoff-only or wording commits do not advance
the scientific snapshot.

Synchronize committed evidence only. Never copy untracked implementation
files, generated artifacts, or provisional outcomes into the summary branch.
Do not merge or cherry-pick an experiment branch merely to update the deck,
and never merge the summary branch back into an experiment branch. If the
summary worktree is dirty, its ownership is unclear, or the milestone has not
been reviewed, leave the experiment branch unchanged and report the handoff
to the user instead.

This documentation handoff grants no authority to run another experiment,
read data, alter a frozen protocol, or advance the source branch. All
source-branch authorization remains unchanged.

## A4-1S Authorization State

The A4-1 base-only feasibility protocol is frozen. Its authoritative
scientific contracts are:

- `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`;
- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`;
- `docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json`.

On 2026-07-13 the user explicitly authorized **A4-1S only**: synthetic runner
implementation, exact parity, deterministic block-control review, and the
full-shape `8192 x 128` synthetic cost projection. The frozen implementation
contract is:

- `docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md`.

This authorization does not permit a natural-data adapter, any read of the six
registered scientific inputs, the future atomic base command, or SAQ
integration. The `synthetic_runner_implementation_authorized=false` field in
the input contract records its preregistration-time state and must not be
rewritten; the dated user instruction and A4-1S protocol are the later narrow
authority.

Commit the implementation before generating the frozen random parity suites.
Commit and independently review parity evidence before the full-shape cost
projection. Then commit and review the cost manifest, summary, and detail
ledger. Only `PASS_SYNTHETIC_GATE_ONLY` permits asking the user for a separate
real-base authorization; it never grants that authorization itself.

The maximum registered outcome is `GO_TO_SYSTEMS_PREREG`: evidence of a
word-local base-data opportunity that permits writing a later systems/ANN
protocol. It is not authorization to modify SAQ or inspect benchmark queries.
The registered scalar objective uses exact rational SSE on binary32 inputs.
If the same-shape synthetic projection puts that solver above the frozen cost
ceiling, return `NO_GO_EXACT_SOLVER_COST`; do not substitute a floating-point
objective or reduce the projection shape.

## Repository Layout

- `saqlib/`: upstream C++ SAQ/CAQ implementation and search path.
- `src/`: upstream command-line binaries.
- `script/`: small, research-question-driven offline instruments.
- `tests/`: Python tests for branch-local research instruments.
- `unit_test/`: upstream C++ unit tests.
- `docs/`: formulations, related-work reviews, frozen protocols, evidence, and
  source ledgers.
- `data/`, `results/`, `build/`, `bin/`: datasets or generated products; do not
  commit large data, indexes, binaries, or build outputs.

## Build And Verification

Default C++ build:

```bash
mkdir -p build bin
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Branch-local Python verification:

```bash
python -m py_compile script/*.py tests/*.py
python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
git status --short --branch
```

Before a scientific claim, rerun the exact frozen command from a clean output
directory and record input provenance, command line, environment, runtime, and
canonical output.

## Do-Not Rules

- Do not alter upstream code during the first offline feasibility stage.
- Do not extend the A4-1S authorization beyond synthetic implementation,
  parity, block-control review, and the frozen full-shape cost projection.
- Do not implement a natural-data adapter or open `data/`, `results/`, or any
  registered base, centroid, cluster-id, query, ground-truth, or index file.
- Do not run the cost projection from an uncommitted implementation, before
  parity evidence is committed and reviewed, or with a dirty worktree.
- Do not rewrite the frozen A4-1P contracts to record later authorization.
- Do not use benchmark queries to choose cardinalities, groups, codebooks, or
  stopping decisions.
- Do not equate a budget on the sum of center counts with a fixed bit budget;
  fixed-rate Cartesian capacity is the product of per-factor cardinalities.
- Do not claim that Huffman coding reduces worst-case fixed payload length; it
  reduces expected length only under a nonuniform symbol distribution.
- Do not claim a recall or QPS guarantee from an L2 reconstruction guarantee.
- Do not omit unused mixed-radix states, lookup-table bytes, entropy metadata,
  address metadata, or decode work from overhead accounting.
- Do not describe bug fixes, provenance checks, or experimental tooling as
  research contributions.

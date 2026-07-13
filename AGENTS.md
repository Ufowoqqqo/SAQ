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

## A4-1 Preregistration State

The A4-1 base-only feasibility protocol is frozen but **not authorized for
implementation or execution**. Its authoritative contracts are:

- `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`;
- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`;
- `docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json`.

No natural-data adapter or result was produced when these contracts were
written, and no dataset artifact was opened. Do not implement the A4-1 runner,
read its six registered scientific inputs, or execute its gate without later
explicit user authorization. Runner implementation needs its own
authorization. Synthetic parity, code review, and the same-shape cost
projection must then be committed and reviewed before a separate authorization
for the first base read.

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
- Do not treat the frozen A4-1 preregistration as authorization to implement
  or execute its runner.
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

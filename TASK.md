# Current Task: A4-OR-C revised synthetic admission complete

## Branch and base

- Active branch: `saq-a4-original-reopening-protocol`
- Remote-synchronized result commit: `67009a8`
- Historical result at that commit: `CONTROL_INVALID`
- Current work: an uncommitted, completed revision authorized on 2026-07-23
- Revised result: `PASS_A4_OR_C_SYNTHETIC_ONLY`

The old result, contract, schema, and artifacts remain unchanged. This task
does not retroactively turn that execution into a pass.

## Research question

Can the original Attempt 4 candidate complete its frozen synthetic admission
when P and V control validity is judged from the selected final models rather
than from intermediate Faiss empty-cluster repairs?

The hypothesis under test was that nonzero `nsplit` is compatible with a valid
final control. A control is valid only if its final shape is exact, every row
and block receives an in-range encoded label, every final center is occupied
after reassignment, and no final centers collide.

## Fixed scientific boundary

The following remain frozen:

- deterministic 8,192-by-128 synthetic panel;
- the D, A, P, and V algorithms;
- B4 and B8 rates;
- histogram sizes, seeds, restarts, iteration limits, and tie rules;
- all numerical, sensitivity, near-tie, memory, timing, and projected-cost
  conditions other than the P/V validity correction; and
- one process, one thread, and the existing 16-GiB memory limit.

Intermediate P/V `nsplit` counts must still be reported, but are diagnostic and
nonfatal. The exact revised rule and check order are in
`docs/saq_a4_or_c_control_validity_revision_2026_07_23.md`.

## Relevant paths

- Revised rule:
  `docs/saq_a4_or_c_control_validity_revision_2026_07_23.md`
- Old result: `docs/saq_a4_or_c_synthetic_result_2026_07_22.md`
- Old terminal artifacts:
  `docs/saq_a4_or_c_synthetic_artifacts_2026_07_22/`
- Old frozen contract:
  `docs/saq_a4_or_c_machine_contract_2026_07_22.json`
- Synthetic implementation: `research/a4_or_c/`
- Pinned Faiss source: `third_party/faiss` at
  `0ca9df4792b173d573044ee14ca0704780176e82`
- Current progress: `docs/saq_a4_or_c_progress_2026_07_23.md`
- Meeting summary: `docs/saq_a4_or_c_meeting_summary_2026_07_23.md`

## Allowed reads and writes

Allowed reads:

- the paths above;
- build configuration needed for the A4-OR-C targets; and
- Git metadata needed to identify the source snapshot.

Allowed writes:

- `TASK.md`;
- `research/a4_or_c/`;
- concise A4-OR-C documents under `docs/`;
- A4-OR-C build output under `/tmp`; and
- new synthetic-only result artifacts after a complete valid execution.

## Forbidden reads and work

Do not read `data/`, `results/`, or `bin/`; GIST/CIFAR; benchmark queries;
ground truth; generated indexes; ignored prior A4 artifacts; or unrelated old
A4 runners.

Do not modify the old contract, old schema, old result, or old artifact
directory. Do not change SAQ/CAQ production or query code. Do not change a
scientific method, baseline, metric, threshold, seed, or workload. Do not
enter A4-OR-B or natural-data evaluation.

## Allowed commands and budget

Allowed commands are configuration and build commands for the A4-OR-C targets,
the tiny exact and representation tests, and the deterministic synthetic
executable with:

```bash
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
OMP_DYNAMIC=FALSE
taskset -c 0
```

Use one process and one thread. Peak RSS must not exceed 16 GiB. Perform cheap
compile and tiny checks before deciding whether to spend the approximately
40-minute-per-execution cost observed in the old unoptimized run. Do not start
a four-execution formal rerun until the full PASS path is statically complete
and the expected runtime is re-estimated.

## Deliverables and done criteria

Deliver:

- the exact final-model control-validity rule;
- runner fields for P/V shape, encoding, final occupancy, collisions, and
  diagnostic `nsplit`;
- a successful build and unchanged tiny-test result;
- a bounded review of the full PASS path and runtime;
- if affordable and complete, a fresh synthetic-only execution whose artifacts
  do not overwrite the old result.

This task is complete. The revised rule was implemented, built, covered by a
focused control-validity smoke test, and checked by the unchanged tiny suite.
One warmup and three measured synthetic runs all passed. The result and exact
stdout are:

- `docs/saq_a4_or_c_revised_synthetic_result_2026_07_23.md`;
- `docs/saq_a4_or_c_revised_synthetic_stdout_2026_07_23.txt`.

## Current blocker and next action

There is no remaining synthetic correctness or resource blocker. The result
does not authorize natural-data or query work. The current source and result
are uncommitted, so the concrete next repository action is a bounded diff
review followed by commit and push if requested. The next scientific action,
outside this task, would be a base-data-only evaluation that preserves the
query-unaware boundary and makes no unchanged-SAQ compatibility claim.

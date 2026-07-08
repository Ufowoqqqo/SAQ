# AGENTS.md

Durable guidance for Codex sessions on the `saq-structural-followup` branch.

## Research Frame

Work as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a repository. Code and scripts are
supporting tools. Every task should first answer: what SAQ limitation is being
tested, what evidence it adds, what overhead it introduces, and how a strict
SIGMOD/VLDB/ICDE reviewer would evaluate it.

The ultimate objective is a database top-conference-level research work
suitable for SIGMOD, VLDB, or ICDE. Treat small recall/QPS gains as insufficient
unless the method exposes a clear SAQ limitation, has controlled overhead, and
can be explained as more than parameter tuning.

The active direction is query-unaware structural follow-up work for SAQ. Do not
use representative query workloads or held-out query labels to learn plans.
Held-out benchmark queries are allowed only for final evaluation.

Use research-paper terminology in new research notes, summaries, slides, and
task descriptions. Prefer words such as "review", "analyze", "evaluate",
"survey", "evidence", and "limitations". Avoid software-maintenance framing
such as "audit", "harden", "triage", and "patch" unless the topic is literally
code correctness, debugging, or repository maintenance. Existing branch names,
file names, and historical artifact names do not need to be renamed only for
terminology cleanup.

## Priority Directions

1. **Cluster-aware / local residual-aware SAQ plan sharing.** Test whether SAQ's
   one global PCA-variance plan is mismatched to IVF cluster residual structure.
   A plausible method should learn a small family of shared segment/bit plans
   from cluster residual statistics and assign each IVF cell to a plan id under
   explicit metadata overhead.
2. **Segment-cost-aware DP.** If local plan sharing is not promising, study a
   planner objective or Pareto frontier that jointly accounts for quantization
   risk and search-time segment cost. Avoid post-hoc metric filtering as the
   main method.
3. **Flexible segmentation / learned grouping.** Study whether contiguous PCA
   blocks and fixed 64-dimensional granularity are limiting assumptions under
   query-unaware data-only signals.

Treat `saq-boundary-audit` as a historical archive. Do not migrate its
fixed-policy scorer, default-neighborhood generator, matrix runner, provenance
tooling, or large result documents unless the user explicitly asks.

## Repository Layout

- `saqlib/`: C++ SAQ/CAQ implementation, quantizers, estimators, IVF helpers,
  and search logic.
- `src/`: C++ binaries such as `create_index`, `test_qps`,
  `test_relative_error`, and `compute_gt`.
- `script/`: lightweight experiment and data-preparation helpers from upstream
  SAQ. Keep new scripts small and research-question driven.
- `python/`: dataset preprocessing helpers.
- `data/`, `results/`, `bin/`, `build/`: generated or local-output areas; do
  not commit generated datasets, indexes, binaries, or build outputs.
- `docs/`: concise research notes for durable decisions and evidence.

## Build And Verification

Default build:

```bash
mkdir -p build bin
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Before committing:

```bash
git diff --check
cmake --build build -j
git status --short --branch
```

If C++ search results are claimed, report dataset, K, B, PCA setting, nprobe,
top-k/recall metric, command, plan, and whether safe search was used. For
multi-segment recall/QPS claims, prefer:

```bash
-searcher_safe_block_min_mode=2
```

## Do-Not Rules

- Do not continue the old empirical fixed-policy scorer as the main method.
- Do not add wider scorer grids, extra local candidate families, or complex
  post-hoc filters unless they are used only as baselines or ablations.
- Do not use query-aware plan learning under the current direction.
- Do not present bug fixes as research contributions.
- Do not start broad experiments before writing the research question, expected
  contribution, overhead model, strict-reviewer objection, and stop condition.
- Do not introduce unjustified hyperparameters. Any hyperparameter used in a
  proposed method must have a mechanism-level rationale, a clear unit or scale,
  a fixed selection rule before held-out evaluation, and either sensitivity
  evidence or an ablation plan.
- Do not overclaim universal improvement over SAQ before end-to-end validation
  across datasets and operating points.
- Do not spend time on artifact-management completeness unless it directly
  supports a research claim or necessary reproducibility.

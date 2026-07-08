# AGENTS.md

Durable guidance for Codex sessions on the `saq-global-cost-dp` branch.

## Research Frame

Work as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a repository. Code and scripts are
supporting tools. Every task should first answer: what SAQ limitation is being
tested, what evidence it adds, what overhead it introduces, and how a strict
SIGMOD/VLDB/ICDE reviewer would evaluate it.

The objective is a database top-conference-level research work suitable for
SIGMOD, VLDB, or ICDE. Treat small recall/QPS gains as insufficient unless the
method exposes a clear SAQ limitation, has controlled overhead, and can be
explained as more than parameter tuning.

The active direction is query-unaware structural follow-up work for SAQ. Do not
use representative query workloads or held-out query labels to learn plans.
Held-out benchmark queries are allowed only for final evaluation.

Use research-paper terminology in new research notes, summaries, slides, and
task descriptions. Prefer words such as "review", "analyze", "evaluate",
"survey", "evidence", and "limitations". Avoid software-maintenance framing
such as "audit", "harden", "triage", and "patch" unless the topic is literally
code correctness, debugging, or repository maintenance.

## Active Direction

**Data-only SAQ planner-objective analysis.** Study whether SAQ's global
variance-risk model, `sum(segment_variance) / 2^bits`, is a faithful
query-unaware objective for CAQ/SAQ quantization and distance estimation.

Any proposed method should preserve SAQ's one-plan search architecture unless a
later note explicitly motivates a different architecture:

```text
one dataset-level segment/bit plan
one query-side estimator/searcher state
no per-cluster plan ids
no mixed-plan search dispatch
```

The first implementation should be offline only: compare SAQ's variance proxy
against measured data-only segment error across existing datasets and bit
budgets before proposing a replacement planner or building new indexes.

Retired main directions on this branch:

- mixed shared local SAQ plans: useful negative evidence, but multi-plan
  estimator overhead can dominate the recall benefit;
- simple single-global static segment-cost DP: useful limitation evidence, but
  deterministic risk-cost frontiers did not dominate SAQ default and GIST
  near-frontier plans did not improve safe-search QPS.

## Branch Hygiene

This branch starts from `saq-correctness-base`, which keeps only confirmed
correctness fixes needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search mode.

Treat `saq-structural-followup` and `saq-boundary-audit` as historical
archives. Do not migrate mixed shared-plan prototype code, default-neighborhood
scorers, fixed-policy runners, broad result documents, or provenance tooling
unless explicitly requested.

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

- Do not continue mixed shared local SAQ plans as the main method.
- Do not continue simple static global segment-cost DP as the main method.
- Do not continue the old empirical fixed-policy scorer as the main method.
- Do not add wider scorer grids, local candidate families, or complex post-hoc
  filters unless they are used only as baselines or ablations.
- Do not use query-aware plan learning under the current direction.
- Do not present bug fixes as research contributions.
- Treat `-custom_quant_plan` as an experimental evaluation hook, not as a
  research contribution by itself.
- Do not start broad experiments before writing the research question, expected
  contribution, overhead model, strict-reviewer objection, and stop condition.
- Do not introduce unjustified hyperparameters. Any hyperparameter used in a
  proposed method must have a mechanism-level rationale, a clear unit or scale,
  a fixed selection rule before held-out evaluation, and either sensitivity
  evidence or an ablation plan.
- Do not overclaim universal improvement over SAQ before end-to-end validation
  across datasets and operating points.

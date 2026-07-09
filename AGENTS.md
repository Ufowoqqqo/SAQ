# AGENTS.md

Durable guidance for Codex sessions on the `saq-graph-traversal-analysis`
branch.

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
use representative query workloads or held-out query labels to learn plans or
thresholds. Held-out benchmark queries are allowed only for evaluation.

Use research-paper terminology in new research notes, summaries, slides, and
task descriptions. Prefer words such as "review", "analyze", "evaluate",
"survey", "evidence", and "limitations". Avoid software-maintenance framing
such as "audit", "harden", "triage", and "patch" unless the topic is literally
code correctness, debugging, or repository maintenance.

## Active Direction

**Graph-index compatibility and traversal-sensitivity analysis.** Study whether
SAQ's segmented progressive distance estimator remains traversal-stable in
graph-based ANNS, where approximate distances affect frontier expansion rather
than only filtering a fixed IVF candidate set.

Do not implement a full HNSW or DiskANN integration before a paper/source-code
review and a minimal offline traversal-sensitivity measurement. Any proposed
method should preserve SAQ's one global quantization plan unless a later note
explicitly motivates a different architecture:

```text
one dataset-level segment/bit plan
one query-side estimator/searcher state
no per-cluster plan ids
no mixed-plan search dispatch
```

The first implementation should be offline only: compare exact float frontier
decisions with full SAQ estimates and staged SAQ estimates on a fixed graph or
adjacency replay, without changing SAQ's persisted index format.

## Branch Hygiene

This branch starts from `saq-correctness-base`, which keeps only confirmed
correctness fixes needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search mode.

Treat previous branches as historical evidence, not code to migrate by default:

- `saq-boundary-audit`: default-neighborhood and empirical fixed-policy scorer
  experiments;
- `saq-structural-followup`: mixed shared local-plan experiments;
- `saq-global-cost-dp`: static global segment-cost DP experiments;
- `saq-planner-objective-analysis`: fac-error planner-objective and IVF
  search-procedure measurements.

Do not migrate prototype code, broad result documents, old runners, fixed-policy
scorers, local-candidate families, or profiler binaries unless explicitly
requested and justified by the current graph-index question.

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

If C++ search results are claimed, report dataset, K, B, PCA setting, graph or
IVF parameters, top-k/recall metric, command, plan, and whether safe search was
used. For multi-segment recall/QPS claims in the SAQ IVF path, prefer:

```bash
-searcher_safe_block_min_mode=2
```

## Do-Not Rules

- Do not continue mixed shared local SAQ plans as the main method.
- Do not continue simple static global segment-cost DP as the main method.
- Do not continue the old empirical fixed-policy scorer as the main method.
- Do not continue small IVF search-loop scheduling changes as the main method.
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
- Do not implement full graph-index integration until an offline traversal
  replay shows a graph-specific SAQ limitation.

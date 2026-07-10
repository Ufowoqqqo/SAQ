# AGENTS.md

Durable guidance for Codex sessions on the `saq-transform-analysis` branch.

## Research Frame

Work as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a repository. Code and scripts are
supporting tools. Every task should first answer: what SAQ limitation is being
tested, what evidence it adds, what overhead it introduces, and how a strict
SIGMOD/VLDB/ICDE reviewer would evaluate it.

The objective is a database top-conference-level research work suitable for
SIGMOD, VLDB, or ICDE. Treat small recall/QPS gains as insufficient unless the
method exposes a clear SAQ-specific limitation, has controlled overhead, and
can be explained as more than transform or parameter tuning.

The active direction is query-unaware structural follow-up work for SAQ. Do not
use representative query workloads or held-out query labels to learn
transforms, dimensions, plans, losses, or thresholds. Held-out benchmark
queries are allowed only for evaluation.

Use research-paper terminology in new research notes, summaries, slides, and
task descriptions. Prefer words such as "review", "analyze", "evaluate",
"survey", "evidence", and "limitations". Avoid software-maintenance framing
such as "audit", "harden", "triage", and "patch" unless the topic is literally
code correctness, debugging, or repository maintenance.

## Active Direction

**Completed query-unaware transform and SAQ-plan compatibility analysis.** The
study tested whether PCA's variance-only objective was mismatched with SAQ's
segmented CAQ estimator, progressive prefix behavior, and actual storage/work
budget.

**Status: closed after the preregistered Phase 1b replication.** This branch
now preserves the evidence and decision boundary; it does not authorize more
PCA-replacement method development. Select a distinct SAQ research question
before beginning new experiments.

The completed primary study was not generic dimensionality reduction. It
compared
full-dimensional, dataset-level transforms that preserve the original L2
problem. Physical `D -> d` projection is a separate, explicitly lossy secondary
study whose projection error would need original-space ground truth; it is not
an active next step after the failed Phase 1b gate.

Preserve the following architecture unless a later evidence note explicitly
motivates a change:

```text
L2 + IVF first
base/index data only for fitting
one dataset-level transform
one global SAQ segment/bit plan
one query-side transform/estimator state
no per-cluster transform or plan ids
no mixed-plan search dispatch
held-out queries for evaluation only
```

The authoritative research proposal is
`docs/saq_transform_replacement_research_proposal_2026_07_10.md`.

## Phase 1 And Phase 1b Decision

The minimal Phase 1 operating point is complete. The authoritative evidence and
method-development decision are recorded in
`docs/saq_transform_phase1_limitation_evidence_2026_07_10.md`.

The study found a narrow estimator mismatch: at the same five-segment plan and
serialized index bytes, residual PCA reduced mean per-query candidate RMSE by
about 0.60% at the first accurate prefix and 0.33% at full code. The prefix
effect held for all ten internal-rotation seeds and with rotation off. It did
not establish a top-k, boundary-inversion, or exact-best-rank improvement, and
the fast prefixes worsened. Identity/random gains were explained by plan shape
and internal rotation.

Phase 1 did not authorize a learned SAQ-aware transform, broad transform
matrix, persisted-format change, or positive method claim. Its only permitted
closure test was one preregistered second-regime replication with a common raw
exact reference and no tuning on the GIST evaluation queries.

That second-regime replication is now complete. The authoritative Phase 1b
protocol and evidence are:

- `docs/saq_transform_phase1b_external_replication_protocol_2026_07_10.md`;
- `docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md`.

On CIFAR60k, all artifact checks passed, but the GIST residual-PCA RMSE effect
did not reproduce. At `accurate_prefix_1`, mean-query RMSE was slightly worse
and the CI crossed zero; at `full`, the small favorable point estimate also had
a CI crossing zero. Seed agreement was only 4/10 and 5/10, rotation-off was
opposite to the registered direction, and `fast_all` RMSE significantly
favored current PCA. The preregistered decision is
`close_one_dataset_estimator_effect`.

Do not substitute another prefix, dataset, budget, codebook, or transform after
this failure. Do not begin the counterfactual `(segment, bit)` analysis or a
learner. The combined result is a useful negative finding: PCA is locally
imperfect on GIST but has not been shown to be a systematic practical SAQ
limitation.

## Evidence And Novelty Gate

Do not assume that replacing PCA is a contribution. Classical transform coding,
ITQ/OPQ, LeanVec, GleanVec, MRQ, and related projection-plus-quantization work
already cover large parts of the design space.

The first offline limitation measurement and its external closure replication
have been completed. Phase 1 compared the
SAQ variance proxy with measured full-code and prefix estimator error under
current PCA and simple controls. Its weak diagnostic trigger was positive, but
its learner/contribution gate failed. Phase 1b then failed to reproduce even
the narrow estimator gate on the registered second dataset. Do not train a new
transform, change the persisted index format, start a broad post-hoc dataset
matrix, or execute the counterfactual `(segment, bit)` analysis from these
results. The selected-segment Spearman analysis remains descriptive.

A learned method is justified only if the evidence shows a systematic gap that
is not explained by residual PCA, a coordinate permutation, a seeded random
orthogonal transform, FHT-style mixing, OPQ/ITQ-style rotation, or SAQ's own
per-segment random rotations.

For lossy projection, separately report:

```text
original exact distance
projected exact distance
projected full-SAQ estimate
projected staged-SAQ estimate
```

Do not let transformed-space ground truth hide projection error. Treat
truncated PCA, LeanVec-ID, and MRQ as mandatory novelty and empirical baselines,
not as proposed contributions.

## Branch Hygiene

This branch starts from `saq-correctness-base`, which keeps only confirmed
correctness fixes needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search support.

Treat previous branches as historical evidence, not code to migrate by default:

- `saq-boundary-audit`: default-neighborhood and empirical fixed-policy scorer
  experiments;
- `saq-structural-followup`: mixed shared local-plan experiments;
- `saq-global-cost-dp`: static global segment-cost DP experiments;
- `saq-planner-objective-analysis`: fac-error planner-objective and IVF
  search-procedure measurements;
- `saq-graph-traversal-analysis`: graph compatibility and traversal-sensitivity
  analysis.

The graph direction is explicitly out of scope on this branch. Do not migrate
graph profilers, SymphonyQG baselines, traversal replay code, graph documents,
prototype methods, broad result documents, old runners, fixed-policy scorers,
local-candidate families, or profiler binaries unless the user explicitly
requests and justifies the migration for the transform question.

## Repository Layout

- `saqlib/`: C++ SAQ/CAQ implementation, quantizers, estimators, IVF helpers,
  and search logic.
- `src/`: C++ binaries such as `create_index`, `test_qps`,
  `test_relative_error`, and `compute_gt`.
- `script/`: lightweight experiment and data-preparation helpers from upstream
  SAQ. Keep new scripts small and research-question driven.
- `python/`: dataset preprocessing helpers. The current PCA path is here.
- `data/`, `results/`, `bin/`, `build/`: generated or local-output areas; do
  not commit generated datasets, indexes, binaries, or build outputs.
- `docs/`: concise research notes for durable decisions and evidence.
- `../vectordb/scripts/`: sibling-repository transform and manifest utilities
  that may be reused selectively; do not modify that repository from this
  branch without explicit authorization.

## Measurement And Accounting

For every transform experiment, record:

- dataset, metric, `K`, `B`, `nprobe`, candidate set, top-k/recall metric, and
  command;
- transform contract, input/output dimensions, training rows and hash, random
  seed, operator/model bytes, fit time, apply time, and raw-query transform
  latency;
- covariance diagnostics, SAQ plan, segment-rotation setting, and whether
  `-searcher_safe_block_min_mode=2` was used;
- transform, quantization, and staged-estimator error separately;
- actual serialized bytes, bytes read, cycles or time per candidate, and any
  exact-refinement work.

Do not use nominal `B` as the sole space comparison. Count packed codes,
short/long factors, tail metadata, padding/alignment, centroids, global
transform state, segment rotators, and raw vectors used for reranking
consistently.

Use predeclared seeds and query-level paired confidence intervals for claims.
Do not select a dimension, loss, threshold, or transform using the held-out
benchmark queries later used to report performance.

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

For multi-segment SAQ IVF claims, prefer the finite valid-lane implementation:

```bash
-searcher_safe_block_min_mode=2
```

Label mode `0` explicitly if it is used only to reproduce legacy native
reduction behavior.

## Do-Not Rules

- Do not present a plug-in replacement of PCA as a research contribution.
- Do not continue PCA-replacement experiments after the failed preregistered
  Phase 1b gate by changing the dataset, prefix, budget, codebook, or transform.
- Do not conflate full-dimensional PCA rotation with physical dimension
  reduction.
- Do not claim a lossy projection gain without original-space ground truth and
  an explicit projection/quantization/staging error decomposition.
- Do not continue graph-index integration or graph traversal analysis here.
- Do not continue mixed shared local plans, static global cost DP, the old
  empirical fixed-policy scorer, or small IVF search-loop scheduling changes as
  the main method.
- Do not use query-aware transform, plan, dimension, loss, or threshold
  learning.
- Do not present bug fixes or tooling as research contributions.
- Do not change the persisted index format before the offline limitation gate.
- Do not start broad experiments before stating the research question,
  expected contribution, overhead model, strict-reviewer objection, and stop
  condition.
- Do not introduce unjustified hyperparameters. Each must have a
  mechanism-level rationale, a clear unit or scale, a fixed selection rule
  before held-out evaluation, and either sensitivity evidence or an ablation
  plan.
- Do not overclaim universal improvement over SAQ before end-to-end validation
  across datasets and operating points.
- Before proposing a new method, first survey closely related work. State what
  it already solves, what assumptions or gaps remain, and how the idea targets
  a distinct SAQ-specific limitation.

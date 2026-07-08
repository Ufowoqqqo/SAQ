# AGENTS.md

Durable instructions for Codex sessions working on the `saq-boundary-audit` branch of the SAQ repository.

This file is intended to replace or extend the current root `AGENTS.md`. Keep it concise enough that future Codex sessions actually follow it, but strict enough to prevent false progress.

## 1. Current Research Direction

The active follow-up direction is **query-unaware SAQ segment-plan improvement**.

The current best framing is not “find one custom segment plan that beats SAQ.” The current method story is:

> Use data-only boundary-risk diagnostics to generate and score local default-neighborhood segment plans, promote only conservative/frontier candidates, reject bad speed-only changes, and abstain when the SAQ default plan has no meaningful local multi-segment neighborhood.

The method must stay query-unaware unless the user explicitly changes the research direction. Held-out benchmark queries may be used only for final evaluation, not for learning or selecting candidate plans.

Current priority shift: do not treat the fixed-policy metric-scorer approach as
the main path for future novelty. It remains useful evidence and a diagnostic
baseline, but its empirical metrics and hyperparameters make it too close to
local SAQ tuning unless ablation proves otherwise. Future method exploration
should prioritize more structural SAQ limitations in this order:

1. **Cluster-aware / local residual-aware SAQ plan sharing.** SAQ learns one
   global PCA-variance segment plan, then applies it to all IVF residual
   clusters. A stronger query-unaware contribution is to learn a small family of
   shared segment/bit plans from cluster residual statistics, assign each IVF
   cell to a plan id, and evaluate the recall/QPS/metadata tradeoff against the
   default one-global-plan SAQ baseline.
2. **Segment-cost-aware DP.** Instead of post-hoc candidate filtering, revise
   the planner objective or Pareto frontier to account for quantization risk and
   search-time segment cost under SAQ's budget and overhead constraints. This is
   valuable only if it exposes a systematic limitation of SAQ's variance-only
   DP, not if it becomes another tuned scorer.
3. **Flexible segmentation / learned grouping.** Study whether contiguous PCA
   blocks and fixed 64-dimensional granularity leave value on the table under
   query-unaware data-only signals. This is potentially more novel but should
   be attempted after the local residual and segment-cost directions are scoped.

Do not add more default-neighborhood candidate families or scorer terms as the
next research step unless a severe-reviewer check explains why they answer a
paper-level question better than the three directions above.

The current strategic concern is **novelty and overhead**. The project must not
drift into spending large offline time, index-build time, memory, or search
complexity for tiny recall/QPS deltas. Any next method change should clarify
what SAQ limitation it exposes and why the added policy/scoring overhead is
worthwhile.

Treat the current boundary-risk scorer as an empirical proxy, not as a
theoretically guaranteed planner. Its multiple metrics and hyperparameters are
currently a liability for novelty and practicality unless ablation shows that
they are necessary. Before making the scorer more complex, compare it against
simple baselines such as speed-only selection, random local selection,
guard-removed selection, and a fixed single-configuration scorer. If the
complex scorer is not meaningfully safer than those alternatives, stop adding
scorer terms or candidate families and pivot to a clearer SAQ limitation.

Current paper-readiness assessment: the novelty is low-to-medium to medium.
The work is a good meeting report / technical note, but it is not yet a
SIGMOD/VLDB/ICDE full-paper contribution. The current method is best described
as a query-unaware local correction policy around SAQ's default segment
planner, not as a new quantizer, not as a theoretically guaranteed planner,
and not as a universal improvement over SAQ.

The ultimate objective is to produce a database top-conference-level research
work suitable for SIGMOD, VLDB, or ICDE, so every exploratory step should be
judged by whether it can plausibly support that level of contribution.

Use a **researcher-first role frame**. Treat the working identity for this
project as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a codebase. Code, scripts,
reproducibility tools, and engineering cleanup are support functions. Before
starting or recommending work, first ask what research question it clarifies,
what SAQ limitation it exposes, what evidence it would add, how a strict
reviewer would evaluate it, and whether it moves the project closer to a
paper-level contribution.

Use research-paper terminology for research direction, documentation, and
meeting materials. Prefer words such as "review", "analyze", "evaluate",
"survey", "evidence", and "limitations". Avoid software-maintenance framing
such as "audit", "harden", "triage", and "patch" unless the topic is literally
code correctness, debugging, or repository maintenance. Do not rename existing
artifact paths only for terminology cleanup, but use this style for new docs,
slides, task descriptions, and summaries.

## 2. Repository Layout

- `saqlib/`: header-heavy C++ SAQ/CAQ implementation, quantizers, estimators, IVF helpers, utilities, and fast scan/search code.
- `src/`: C++ binaries such as `create_index`, `test_qps`, `test_relative_error`, `compare_search_results`, attribution tools, and diagnostics.
- `unit_test/`: GoogleTest unit tests built as `bin/unit_tests` when enabled.
- `script/`: Python and shell experiment drivers, diagnostics, planner sweeps, fixed-policy validation, and report generation.
- `python/`: dataset download/preprocess, PCA, IVF, and groundtruth helpers.
- `data/`: dataset directories. Generated dataset subdirectories are ignored by git.
- `docs/`: durable experiment notes, reviews, synthesis reports, method specs, and meeting-facing documentation.
- `results/`: figures/notebooks and generated result directories. Generated SAQ/LLM result subdirectories are ignored by git.
- `bin/`: CMake runtime output directory for built binaries. Ignored by git.

## 3. Current Important Files To Read First

Before making decisions, read these files if present:

1. `TASK.md`
2. `PROGRESS.md`
3. `EXPERIMENTS.md`
4. `RESULTS.md`
5. `codex_handoff.md`
6. `docs/saq_fixed_policy_method_spec_2026_07_07.md`
7. `docs/saq_stage_synthesis_v3_conservative_2026_07_06.md`
8. `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
9. Any doc named in `TASK.md` or `EXPERIMENTS.md`

Do not rely on memory from an earlier Codex session if these files disagree with it. Prefer checked-in docs and exact generated artifacts.

## 4. Non-Negotiable Research Constraints

1. **Remain query-unaware.** Do not use representative query workloads, held-out query labels, or query-specific fitting to generate or score plans.
2. **Use corrected safe search for measured claims.** Any recall/QPS claim involving multi-segment search must use:

   ```bash
   -searcher_safe_block_min_mode=2
   ```

3. **Do not promote raw offline planner winners without measured validation.** Planner v3 recall-risk endpoints are diagnostic. They are not method claims unless validated end to end.
4. **Do not treat `--allow-risky-fallback` as a promotion policy.** Risky fallback is only for negative/control diagnostics.
5. **Do not overclaim universal applicability.** The current evidence supports a shape-dependent method: strongest when the SAQ default plan has a multi-stage bit ladder, preferably with a zero tail and enough middle/tail positive dimensions to redistribute.
6. **Respect abstention.** For single-uniform default plans such as current audio/word2vec cases, report abstention unless the generator itself is explicitly and defensibly expanded.
7. **Keep reports reproducible.** Every claimed result must include dataset, K, B, PCA setting, top-k/recall metric, nprobe, searcher mode, plan, command, and artifact path.
8. **Do not rely only on `/tmp`.** Local `/tmp/saq-run` artifacts are useful but not durable. Durable conclusions belong in `docs/` or checked-in summary files.
9. **Novelty gate before new sweeps.** Do not start a new expensive sweep,
   dataset run, or candidate-family expansion unless the expected contribution
   is more than local tuning around SAQ. State the SAQ failure mode, why the
   existing default planner cannot already capture it, and what would count as
   a meaningful result.
10. **Overhead gate before promotion.** Do not promote a method variant unless
    its offline scoring cost, index-build cost, memory/metadata overhead, and
    search-time overhead are accounted for against SAQ baseline. Small recall
    or QPS deltas are not enough if they require substantial extra time, space,
    or implementation complexity.
    Distinguish deployable overhead from experimental validation overhead:
    deployable overhead is candidate generation, boundary-pair scoring, and
    one selected index build; experimental overhead includes extra candidate
    builds and recall/QPS evaluations used only to validate the policy.
11. **Adversarial reviewer review before new directions.** Before proposing a
    new direction, candidate family, or expensive evaluation, write a short
    severe-reviewer assessment. It should ask whether the idea would be seen as
    SAQ parameter tuning, whether the claimed limitation is already handled by
    SAQ, what ablation would distinguish the new signal from a speed-only or
    random-local baseline, what overhead it adds, and what stop-loss condition
    would justify pivoting.
12. **Scorer simplicity gate.** Do not add new boundary-risk terms, wider
    hyperparameter grids, or candidate-family-specific scorer branches unless a
    simpler scorer fails on a documented promote/reject/abstain boundary. The
    default decision preference is to simplify or ablate the scorer, not to
    improve headline metrics by adding more empirical knobs.
13. **Researcher-first framing.** Treat implementation work as a means to
    answer a research question. Avoid spending time on tooling, cleanup, or
    workflow completeness unless it directly supports novelty, evidence,
    reproducibility needed for claims, or meeting/paper communication.
14. **Priority research directions.** When the user asks what to do next, prefer
    the structural directions in this order: cluster-aware/local residual-aware
    SAQ plan sharing; segment-cost-aware DP; flexible segmentation or learned
    grouping. Treat the current metric-scorer fixed policy as background
    evidence unless the task is explicitly to ablate or document it.

## 5. Build, Test, And Sanity Commands

Prerequisites noted by the project:

```bash
apt install libfmt-dev libgoogle-glog-dev libgflags-dev libgtest-dev
```

AVX512 is mandatory. Builds on machines without AVX512 support are expected to fail.

Default build:

```bash
mkdir -p build bin
cmake -S . -B build
cmake --build build -j
```

Build without unit tests when local GoogleTest/CMake setup is unavailable:

```bash
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Python syntax checks before planner/driver edits:

```bash
python -m py_compile \
  script/sweep_data_boundary_pairs.py \
  script/generate_default_neighborhood_plans.py \
  script/score_default_neighborhood_plans.py \
  script/run_default_neighborhood_cross_dataset.py \
  script/run_fixed_policy_matrix.py \
  script/report_fixed_policy_validation.py \
  script/propose_residual_plan.py \
  script/sweep_boundary_plan.py \
  script/segment_diagnostics.py
```

Before committing code changes, run at least:

```bash
cmake --build build -j || true
python -m py_compile script/*.py python/*.py python/utils/*.py
git diff --check
git status --short
```

If unit tests are available:

```bash
ctest --test-dir build --output-on-failure
# or
./bin/unit_tests
```

## 6. Fixed-Policy Validation Commands

Regenerate and check the clean fixed-policy summary:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Regenerate the fixed-policy matrix if local artifacts are available:

```bash
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Run default-neighborhood applicability scan:

```bash
python script/scan_default_neighborhood_applicability.py \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_applicability_scan_$(date +%Y_%m_%d)
```

When building/evaluating selected candidates, make sure the evaluation path uses the safe-searcher mode:

```bash
-searcher_safe_block_min_mode=2
```

## 7. Autonomous Iteration Protocol

For each Codex run:

1. Read `TASK.md`, `PROGRESS.md`, `EXPERIMENTS.md`, `RESULTS.md`, and the relevant docs.
2. Inspect `git status --short` before editing.
3. State the current hypothesis in `PROGRESS.md` before making nontrivial changes.
4. Make the smallest useful change or experiment.
5. Run the cheapest relevant validation first.
6. Record exact commands, outputs/artifact paths, and interpretation in `PROGRESS.md`.
7. If a path fails twice for the same reason, stop repeating it and pivot.
8. If a result is important, add or update a durable report in `docs/`.
9. Update `RESULTS.md` only for stable conclusions, not speculative observations.
10. Before starting expensive work, check the novelty/overhead gate: is this
    likely to become a defensible contribution, or is it just buying a tiny
    metric gain with more machinery?
11. Before proposing a new research direction, run the adversarial reviewer
    review: state the likely harsh-review objections and the ablation/overhead
    evidence needed to answer them.
12. End with a short handoff: changed files, commands run, evidence, risks, and next recommended action.

## 8. Iteration Budget

Default autonomous budget per session:

- Maximum 8 iterations.
- Maximum 3 major approaches.
- Maximum 1 new end-to-end dataset/budget evaluation unless `TASK.md` explicitly asks for more.
- Prefer reproducing/reporting existing evidence before starting expensive new runs.

Stop early when:

- the success criteria in `TASK.md` are met;
- the next step needs unavailable datasets/artifacts/credentials;
- the machine lacks AVX512 or required local artifacts;
- further work would be destructive or would rewrite unrelated experiment history;
- the evidence contradicts the hypothesis and no clean pivot is available.
- the next idea mainly increases offline/index/search complexity for marginal
  metric movement and does not reveal a clear SAQ limitation or contribution.
- the next idea cannot answer a basic severe-reviewer objection: why this is
  more than local tuning around SAQ's already strong planner.

## 9. Coding And Documentation Rules

- C++ standard is C++20.
- Follow `.clang-format`: LLVM base style, 4-space indentation, no column limit.
- Keep C++ changes compatible with AVX512 compile flags in `CMakeLists.txt`.
- Keep Python experiment scripts deterministic where practical; expose parameters as flags instead of hard-coding one-off values.
- Put durable experiment writeups in `docs/`.
- Use research-paper terminology in non-code writeups: prefer "review",
  "analyze", "evaluate", "survey", and "limitations" over "audit", "harden",
  "triage", and "patch" unless discussing code.
- Do not commit generated datasets, built binaries, `build/`, `bin/`, or generated result directories ignored by `.gitignore`.
- Do not rewrite unrelated docs or revert user changes.
- Do not rewrite git history.
- Do not delete large directories or generated artifacts unless explicitly asked.

## 10. Known Pitfalls

- Planner rankings are proxies. Prior work found that low offline recall-risk can still be a measured false positive.
- A previous B=5 raw v3 recall-risk endpoint was a false positive and should not be promoted without the conservative guard.
- GIST B=3 required a positive 1-bit segment implementation fix; this fix is an upstream correctness repair, not the planner contribution.
- Audio and word2vec currently have single-uniform default plans under B=3/4/5 and are stable abstention cases under the current generator.
- DEEP B=4/B=5 are useful negative controls: speed can improve while recall drops too much.
- Local `/tmp/saq-run` artifacts may disappear; keep enough metadata in checked-in docs to reproduce or diagnose.
- The current fixed policy is not an independent quantizer; it is a policy
  layer around SAQ's default plan. Future work must be honest about this and
  avoid presenting local plan tuning as a strong contribution without a clear
  failure-mode analysis and overhead accounting.
- Tiny recall/QPS gains can be misleading if they require many candidate
  builds, extra scorer passes, large local artifacts, or complex implementation
  branches that would not be acceptable in a practical indexing pipeline.
- The strongest current evidence is the policy boundary, not raw recall gain:
  GIST/CIFAR positives, DEEP reject controls, and audio/word2vec abstentions.
  Future work should prove why the boundary-risk scorer is safer than
  speed-only, random-local, or handcrafted heuristics before adding more
  candidate families.
- The scorer has no current theoretical guarantee and contains many empirical
  choices. Future decisions should treat that as a central weakness, not a
  detail to hide: either simplify the policy until it is easy to explain, or
  provide ablation evidence that the extra metrics and hyperparameters prevent
  real false positives at acceptable overhead.

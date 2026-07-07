# AGENTS.md

Durable instructions for Codex sessions working on the `saq-boundary-audit` branch of the SAQ repository.

This file is intended to replace or extend the current root `AGENTS.md`. Keep it concise enough that future Codex sessions actually follow it, but strict enough to prevent false progress.

## 1. Current Research Direction

The active follow-up direction is **query-unaware SAQ segment-plan improvement**.

The current best framing is not “find one custom segment plan that beats SAQ.” The current method story is:

> Use data-only boundary-risk diagnostics to generate and score local default-neighborhood segment plans, promote only conservative/frontier candidates, reject bad speed-only changes, and abstain when the SAQ default plan has no meaningful local multi-segment neighborhood.

The method must stay query-unaware unless the user explicitly changes the research direction. Held-out benchmark queries may be used only for final evaluation, not for learning or selecting candidate plans.

The current strategic concern is **novelty and overhead**. The project must not
drift into spending large offline time, index-build time, memory, or search
complexity for tiny recall/QPS deltas. Any next method change should clarify
what SAQ limitation it exposes and why the added policy/scoring overhead is
worthwhile.

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
11. End with a short handoff: changed files, commands run, evidence, risks, and next recommended action.

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

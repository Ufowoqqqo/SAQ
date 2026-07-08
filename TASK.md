# TASK.md

## Active Goal

Develop and evaluate the current **query-unaware default-neighborhood fixed-policy method** into a reproducible, meeting/paper-ready SAQ follow-up story.

The goal is not to maximize one benchmark number. The goal is to make the current method boundary precise, reproducible, and defensible:

> Generate local segment-plan candidates around SAQ's default plan, score them with data-only boundary-risk and speed proxies, promote only conservative/frontier-like candidates, reject bad speed-only candidates, and abstain when the default plan shape has no meaningful neighborhood.

New strategic constraint after the latest discussion: the work must be judged
by **novelty and overhead**, not only by recall/QPS deltas. The current method
is a policy layer on top of SAQ, not an independent quantizer. Future progress
must explain what concrete SAQ limitation is being addressed and whether the
extra planning/scoring/indexing/search complexity is justified.

The ultimate objective is to produce a database top-conference-level research
work suitable for SIGMOD, VLDB, or ICDE, so every exploratory step should be
judged by whether it can plausibly support that level of contribution.

Terminology constraint: use research-paper terminology rather than
software-maintenance terminology in new research notes, summaries, slides, and
task descriptions. Prefer "review", "analyze", "evaluate", "survey",
"evidence", and "limitations" over "audit", "harden", "triage", and "patch"
unless discussing code correctness or repository maintenance. Existing artifact
paths and historical task names do not need to be renamed only for wording.

## Current Status Summary

The branch already contains evidence that:

- GIST full K4096 is positive across B=3/B=4/B=5.
- CIFAR60K is positive across B=3/B=4/B=5.
- DEEP100K B=4/B=5 are useful reject/negative-control cases: QPS improves, but recall drops too much.
- audio and word2vec are stable abstention cases under the current generator because their default plans are single uniform segments for the scanned budgets.
- The previous B=5 v3 raw recall-risk endpoint false positive is now handled by a conservative role-selection guard.
- GIST B=3 exposed and fixed a positive 1-bit CAQ segment implementation bug; this is a correctness fix, not the method contribution.

Treat this as the baseline state. Do not restart from the older handoff state unless current files are missing.

## Read First

Read these files before deciding what to do:

1. `AGENTS.md`
2. `PROGRESS.md`
3. `EXPERIMENTS.md`
4. `RESULTS.md`
5. `docs/saq_fixed_policy_method_spec_2026_07_07.md`
6. `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
7. `docs/saq_stage_synthesis_v3_conservative_2026_07_06.md`
8. `docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md`
9. `docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md`
10. `docs/saq_default_neighborhood_applicability_scan_2026_07_06.md`

## Primary Success Criteria

A successful autonomous run should complete at least one of the following without violating query-unaware constraints:

0. **Novelty and overhead review**
   - Before launching new expensive experiments, write down the expected
     contribution beyond local tuning of SAQ's default plan.
   - Account for extra offline scorer time, candidate generation, index-build
     cost, memory/metadata overhead, search-time overhead, and implementation
     complexity.
   - If the expected gain is only a tiny recall/QPS improvement with large
     overhead, stop or pivot instead of continuing the sweep.

1. **Reproducibility evaluation**
   - Run `script/report_fixed_policy_validation.py` against the checked-in expected CSV.
   - If it fails, diagnose whether the failure is a script bug, stale artifact mismatch, missing local artifact, or expected-table issue.
   - Update `PROGRESS.md` and, if needed, a small durable doc under `docs/`.

2. **Matrix validation evaluation**
   - Run or dry-run `script/run_fixed_policy_matrix.py` using the existing artifact date.
   - Confirm whether the checked-in clean table is reproducible from existing artifacts.
   - If not reproducible due to missing `/tmp/saq-run` artifacts, document exactly which artifacts are missing and what command would regenerate them.

3. **Policy robustness review**
   - Review candidate generation, scoring, and promotion logic for cases where the policy might promote false positives or reject valid frontier-like positives.
   - Any proposed guard change must be validated against the known positive, reject, and abstain cases.
   - Do not tune thresholds using held-out query labels as training data.

4. **Meeting/paper narrative cleanup**
   - Produce or update a concise synthesis doc explaining the method, evidence, limitations, and next experiments.
   - The narrative must distinguish: method contribution, implementation fix, positive cases, reject cases, abstention cases, and unresolved threats to validity.

## Secondary Success Criteria

After satisfying a primary criterion, optionally attempt one low-cost improvement:

- Add or update a novelty/overhead table for the current method.
- Add explicit complexity accounting to the fixed-policy method docs.
- Improve command reproducibility in the report scripts.
- Add clearer error messages for missing artifacts.
- Add a small consistency checker for the clean validation table.
- Add explicit documentation for why `--allow-risky-fallback` is diagnostic only.
- Add a compact README section or doc section that states the fixed-policy method in algorithmic steps.

## Non-Goals For This Run

Do not spend the session on these unless the user explicitly asks:

- Query-aware plan selection.
- Broad full-plan search unrelated to SAQ default-neighborhood perturbations.
- New expensive dataset preparation unless needed to reproduce an already documented result.
- Forcing audio/word2vec into a non-abstain result under the current generator.
- Treating DEEP speed-only improvements as positive method evidence.
- Re-running large end-to-end experiments before verifying existing report reproducibility.
- Pursuing tiny recall/QPS deltas by adding large offline search, many custom
  index builds, heavy metadata, or complex policy branches without a clear
  novelty story.
- Presenting a local post-planning tweak as a strong standalone method unless
  the SAQ baseline limitation and added-overhead tradeoff are explicitly
  documented.

## Required Validation Commands

Before code edits:

```bash
git status --short
python -m py_compile \
  script/sweep_data_boundary_pairs.py \
  script/generate_default_neighborhood_plans.py \
  script/score_default_neighborhood_plans.py \
  script/run_default_neighborhood_cross_dataset.py \
  script/run_fixed_policy_matrix.py \
  script/report_fixed_policy_validation.py
```

For fixed-policy report reproducibility:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

For full matrix reproduction if local artifacts exist:

```bash
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Before finalizing code/doc changes:

```bash
git diff --check
git status --short
```

If C++ code changed and the machine supports the build:

```bash
cmake --build build -j
ctest --test-dir build --output-on-failure || true
```

## Evidence Rules

- All measured recall/QPS claims must use `-searcher_safe_block_min_mode=2`.
- Each result must include dataset, K, B, PCA setting, plan, metric, nprobe, top-k, command, and artifact path.
- If a claim comes only from an offline proxy, label it as proxy-only.
- If a script relies on local `/tmp/saq-run` artifacts, say so explicitly.
- Each claimed method improvement must state whether it requires extra
  candidate scoring, extra index builds, extra metadata, or extra search-time
  computation relative to SAQ baseline.
- Update `RESULTS.md` only for stable conclusions.

## Expected Final Handoff

At the end of the run, update `PROGRESS.md` with:

- exact task attempted;
- files changed;
- commands run;
- artifacts produced;
- result and interpretation;
- whether success criteria were met;
- next recommended action.

If a stable conclusion changed, update `RESULTS.md` too.

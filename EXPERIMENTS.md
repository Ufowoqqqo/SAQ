# EXPERIMENTS.md

This file tracks hypotheses, candidate experiments, and documentation tasks. Codex should pick from this list using expected value, validation cost, and risk.

Status labels:

- `todo`: not started
- `running`: currently being attempted
- `done`: completed and documented
- `blocked`: cannot proceed without missing artifact, dataset, credentials, or human decision
- `rejected`: tried and not worth pursuing further

## A. Reproducibility And Hygiene

### A1. Verify clean fixed-policy report regeneration

- Status: `done`
- Priority: highest
- Hypothesis: the checked-in clean validation table can be regenerated from existing summary artifacts.
- Command:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

- Success: command exits cleanly and generated rows match the expected CSV.
- Failure handling:
  - If summary artifacts are missing, record exact missing paths.
  - If values differ, determine whether the expected CSV is stale or the report script changed.
  - Do not silently update expected values without explaining the source of truth.

### A2. Verify or harden fixed-policy matrix runner

- Status: `done`
- Priority: high
- Hypothesis: `script/run_fixed_policy_matrix.py` can reproduce the fixed-policy table when local artifacts exist.
- Command:

```bash
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

- Success: matrix output matches expected CSV, or missing artifacts are reported clearly.
- Useful improvement: add clearer missing-artifact diagnostics if failure is opaque.
- Do not start expensive reruns until existing-artifact reproducibility is understood.

### A3. Python syntax and command smoke checks

- Status: `done`
- Priority: high before edits
- Command:

```bash
python -m py_compile \
  script/sweep_data_boundary_pairs.py \
  script/generate_default_neighborhood_plans.py \
  script/score_default_neighborhood_plans.py \
  script/run_default_neighborhood_cross_dataset.py \
  script/run_fixed_policy_matrix.py \
  script/report_fixed_policy_validation.py
```

- Success: all scripts compile.
- Failure: fix syntax/import-level issues before changing research logic.

## B. Policy Robustness

### B1. Audit promotion decisions against the clean validation table

- Status: `done`
- Priority: high
- Hypothesis: current conservative/frontier/abstain policy decisions align with measured positives, rejects, and abstentions.
- Work:
  1. Read `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`.
  2. Trace each row back to generator/scorer summary artifacts if available.
  3. Check whether decision type is explainable from policy thresholds.
- Success: produce a short doc or `PROGRESS.md` section mapping each row to policy reason.
- Result: documented in `docs/saq_fixed_policy_decision_audit_2026_07_07.md`.
- Caution: do not tune policy thresholds on held-out query results as if they were training labels.

### B2. Check false-positive resistance

- Status: `todo`
- Priority: high
- Known false positive: GIST sample100k B=5 raw v3 endpoint `64:9,64:8,128:7,320:5,320:3,64:0`.
- Hypothesis: conservative role guard prevents promotion because soft-inversion ratio, weighted ratio, and speed-proxy ratio are all worse than default.
- Success: demonstrate from current CSV/roles output that the guard promotes `b5_rank0 = 64:10,192:8,256:5,384:3,64:0` instead.
- Output: small note in `PROGRESS.md` unless a durable doc is missing.

### B3. Frontier-like fallback audit

- Status: `todo`
- Priority: medium
- Known reason: CIFAR B=4 is a small positive selected as `frontier_like`; strict conservative guard alone would be too strict.
- Hypothesis: frontier-like fallback is necessary but should remain narrow.
- Work:
  - inspect CIFAR B=3/B=4/B=5 scorer summaries;
  - check whether `best_recall_risk_score <= 1.0` and `best_speed_proxy_ratio_vs_default <= 1.0` explain the promotion;
  - check that DEEP risky candidates do not pass the fallback.
- Success: document the boundary of frontier-like fallback.

### B4. Abstention audit

- Status: `todo`
- Priority: medium
- Known abstentions: audio and word2vec under B=3/B=4/B=5.
- Hypothesis: abstention follows from single-uniform default plans and no feasible non-default candidates under the current default-neighborhood generator.
- Command:

```bash
python script/scan_default_neighborhood_applicability.py \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_applicability_scan_$(date +%Y_%m_%d)
```

- Success: scan confirms stable abstention, or reports an actual generator change.
- Do not force an arbitrary non-default plan for these datasets unless the generator is intentionally expanded.

## C. Method Extension Ideas

### C1. Expand generator only within query-unaware default-neighborhood logic

- Status: `todo`
- Priority: medium-low
- Hypothesis: new local candidate families may improve coverage without turning into arbitrary full-plan search.
- Allowed signals:
  - base vectors;
  - PCA variance artifacts;
  - IVF centroids and cluster IDs;
  - cluster residuals;
  - base-as-pseudo-query boundary pairs;
  - SAQ default plan metadata.
- Constraints:
  - preserve nonincreasing bit levels unless there is a documented reason;
  - maintain feasibility guards;
  - avoid nonfinal 1-bit promoted candidates unless explicitly validated;
  - keep candidate set small and explainable.
- Required validation: any new family must be tested against GIST/CIFAR positives, DEEP rejects, and audio/word2vec abstentions.

### C2. Better applicability classifier

- Status: `todo`
- Priority: medium
- Hypothesis: the method boundary can be stated more precisely than “multi-segment with zero tail.”
- Possible features:
  - top-64 PCA variance share;
  - default shape label;
  - number of positive segments;
  - zero-tail dimension;
  - middle/tail positive dimensions available for redistribution;
  - whether the default has nonfinal 1-bit segments.
- Success: produce a small table or doc section that explains when to promote, reject, or abstain before expensive evaluation.

### C3. Robustness of GIST B=3 1-bit fix

- Status: `todo`
- Priority: medium if C++ edits continue
- Hypothesis: the 1-bit CAQ segment fix is minimal and does not affect >1-bit behavior.
- Required checks:
  - build succeeds;
  - relevant unit tests if available;
  - at least one default B=3 index build succeeds;
  - no unintended changes to B=4/B=5 outputs.
- Output: keep this framed as an implementation correctness fix, not a planner contribution.

## D. Negative Controls And Threats To Validity

### D1. DEEP reject control

- Status: `todo`
- Priority: medium
- Current evidence: DEEP B=4/B=5 candidates improve QPS but lose too much R@100.
- Goal: make sure future policy changes do not accidentally promote these cases.
- Success: any policy/generator change preserves reject decision unless a new measured candidate avoids the recall loss.

### D2. Artifact-staleness audit

- Status: `todo`
- Priority: medium
- Problem: many outputs live under `/tmp/saq-run`, which is not durable.
- Work:
  - identify which checked-in docs rely on local artifacts;
  - record exact commands to regenerate them;
  - add clearer “artifact required” notes in docs or scripts.
- Success: a future Codex session can understand missing artifacts without guessing.

### D3. Avoid metric cherry-picking

- Status: `todo`
- Priority: medium
- Work:
  - ensure each result states nprobe, top-k, and QPS setting;
  - avoid promoting a plan that only wins at one cherry-picked nprobe if broader behavior is negative;
  - state whether small recall deltas are practically meaningful.

## E. Documentation / Meeting Narrative

### E1. Produce concise method summary

- Status: `todo`
- Priority: high if preparing for advisor/meeting
- Output candidate:
  - `docs/saq_fixed_policy_meeting_summary_YYYY_MM_DD.md`
- Required sections:
  1. one-sentence contribution;
  2. algorithm steps;
  3. evidence table;
  4. positive cases;
  5. reject/negative cases;
  6. abstention cases;
  7. implementation fix separated from method;
  8. limitations and next steps.

### E2. Paper-style method spec cleanup

- Status: `todo`
- Priority: medium
- Goal: turn `docs/saq_fixed_policy_method_spec_2026_07_07.md` into a more formal method section.
- Caution: do not hide empirical threshold choices or overclaim theoretical guarantees.

### E3. Handoff update

- Status: `todo`
- Priority: medium
- Goal: update `codex_handoff.md` or create a new handoff after the latest fixed-policy progress, because the old handoff emphasizes the B=5 false-positive recovery state.
- Success: future context compaction starts from the fixed-policy method state, not the older v3-guard-only state.

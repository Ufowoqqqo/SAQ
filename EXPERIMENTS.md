# EXPERIMENTS.md

This file tracks hypotheses, candidate experiments, and documentation tasks. Codex should pick from this list using expected value, validation cost, and risk.

Terminology rule for new work: use research-paper terminology rather than
software-maintenance terminology. Prefer "review", "analyze", "evaluate",
"survey", "evidence", and "limitations" over "audit", "harden", "triage",
and "patch" unless discussing code correctness or repository maintenance.
Existing artifact paths and historical task labels do not need to be renamed
solely for terminology cleanup.

Decision rule for new work: use a researcher-first frame. Choose experiments
and documentation tasks by the research question, SAQ limitation, evidence
value, reviewer risk, and paper contribution they address. Engineering tasks
are secondary and should not be treated as progress unless they directly
support a claim, an essential validation, or meeting/paper communication.

Current research-priority rule: stop treating the empirical fixed-policy scorer
as the main novelty path. Prefer structural SAQ limitations in this order:

1. cluster-aware / local residual-aware SAQ plan sharing under explicit metadata
   overhead;
2. segment-cost-aware DP or Pareto planning that jointly considers
   quantization-risk and search-time segment cost;
3. flexible segmentation / learned grouping beyond contiguous PCA blocks and
   fixed 64-dimensional granularity.

New scorer metrics, wider scorer grids, or extra local candidate families are
low priority unless they are required for an ablation or for comparing against a
stronger structural method.

Status labels:

- `todo`: not started
- `running`: currently being attempted
- `done`: completed and documented
- `blocked`: cannot proceed without missing artifact, dataset, credentials, or human decision
- `rejected`: tried and not worth pursuing further

## A. Reproducibility And Hygiene

### A-1. Structural SAQ follow-up direction review

- Status: `todo`
- Priority: highest before extending the fixed-policy scorer
- Goal: convert the current novelty concern into a stronger research direction.
- Candidate directions, in priority order:
  1. cluster-aware / local residual-aware SAQ plan sharing;
  2. segment-cost-aware DP;
  3. flexible segmentation / learned grouping.
- Required review questions:
  - What exact SAQ assumption or limitation is targeted?
  - What method would be proposed beyond local candidate filtering?
  - What metadata, training, indexing, and search-time overhead is introduced?
  - What small experiment would falsify the direction early?
  - How would a strict database reviewer distinguish it from SAQ tuning?
- Success: a short durable note under `docs/` recommending whether to start
  cluster-aware plan sharing, segment-cost-aware DP, or flexible segmentation.

### A0. Novelty and overhead gate

- Status: `done`
- Priority: highest
- Hypothesis: the current fixed-policy story may be too close to SAQ and may
  buy small metric gains with nontrivial offline complexity.
- Work:
  1. Compare SAQ baseline pipeline against the fixed-policy pipeline.
  2. Separate one-time experiment overhead from deployable method overhead.
  3. Estimate or bound candidate generation, boundary-pair scoring, extra index
     build, metadata, and search-time costs.
  4. State what the contribution is if the method remains a local policy layer
     around SAQ.
  5. Define stop/pivot criteria for future sweeps when gains are too small.
- Success: a short durable doc or method-spec section that answers:
  - What is the concrete SAQ limitation?
  - What extra overhead does our method add?
  - Are the observed recall/QPS gains large enough to justify that overhead?
  - What experiments should not be run because they only add tuning complexity?
- Constraint: do not start new expensive build/eval sweeps before this review is
  completed or explicitly deferred by the user.
- Result: documented in
  `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`.

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

### A2. Verify or evaluate fixed-policy matrix runner

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

### A4. Fixed-policy overhead evaluation

- Status: `done`
- Priority: highest after A0
- Goal: measure or aggregate the overhead terms required by the novelty and
  overhead review: candidate/scorer runtime, pair count, index build time,
  index size, and QPS curves.
- Work completed:
  - added a reproducible report driver,
    `script/report_fixed_policy_overhead.py`;
  - measured candidate/scorer runtime with fresh timing artifacts under
    `/tmp/saq-run/reports/fixed_policy_overhead_timing_2026_07_07`;
  - aggregated pair counts and scorer grid sizes from scorer summaries;
  - read index build time from existing `*.index.csv` metadata and index size
    from serialized `.index` files;
  - measured/reused QPS curve points across each validation nprobe grid.
- Result:
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.qps_curve.csv`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.json`
- Interpretation: full GIST planning overhead is dominated by the data-only
  scorer, around 145-151 seconds per budget in the current implementation;
  CIFAR/DEEP scorer overhead is much lower, around 6-9 seconds. This makes
  scorer-cost reduction or sampling calibration a more important next question
  than additional candidate-family expansion.

### A5. Fixed-policy scorer calibration evaluation

- Status: `done`
- Priority: highest after A4
- Goal: evaluate whether the data-only scorer can use fewer boundary pairs
  without changing the fixed-policy promote/reject/abstain decision or the
  selected plan.
- Work completed:
  - added `script/run_scorer_calibration.py`;
  - evaluated representative settings on GIST B=4, CIFAR B=4, DEEP B=4, and
    audio B=4;
  - evaluated the stable `a1024_p2` setting across the full fixed-policy
    matrix;
  - compared calibration pair counts and runtime against the overhead summary.
- Result:
  - `docs/saq_fixed_policy_scorer_calibration_2026_07_07.md`
  - `docs/saq_fixed_policy_scorer_calibration_2026_07_07.csv`
  - `docs/saq_fixed_policy_scorer_calibration_2026_07_07.json`
  - `docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.md`
  - `docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.csv`
  - `docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.json`
- Interpretation: `a1024_p2` preserves all decisions and selected plans in
  the current fixed-policy matrix, while smaller representative settings can
  preserve decisions but change the GIST B=4 selected plan. Pair-count
  reduction alone is not enough to remove GIST scorer overhead: reducing GIST
  sampling from 14,740 to 2,048 pairs still leaves scorer runtime around
  94-95% of the full-scorer runtime.
- Next cost-reduction direction: evaluate cached residual/tail features or a
  smaller scoring grid before adding new candidate families.

### A6. Scorer feature-cache and endpoint-grid cost evaluation

- Status: `done`
- Priority: highest after A5
- Goal: evaluate the two plausible scorer-cost reductions suggested by A5:
  cached residual/tail features and a smaller scorer grid.
- Work completed:
  - added plan-level pair/speed/static metric caching inside
    `script/score_default_neighborhood_plans.py`;
  - added optional scorer feature caching for residual risk, tail risk, and
    boundary-pair feature arrays;
  - added endpoint-grid cached-feature presets to
    `script/run_scorer_calibration.py`;
  - ran cold-cache and warm-cache full fixed-policy matrix evaluations.
- Result:
  - `docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.md`
  - `docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.csv`
  - `docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.json`
  - `docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.md`
  - `docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.csv`
  - `docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.json`
- Interpretation: the endpoint grid preserves all current decisions/plans but
  is not the GIST bottleneck by itself. The cold-cache run preserves 10/10
  decisions and 10/10 selected plans while reducing total measured scorer time
  from 481.764 s to 147.082 s. The warm-cache run preserves the same decisions
  and plans with 5.656 s total measured scorer time. Phase timings show that
  GIST cost is dominated by residual/tail feature computation, not boundary
  pair sampling or grid enumeration.
- Constraint: this is an implementation-level overhead reduction, not a new
  SAQ quantization contribution. The feature cache is query-unaware and keyed
  only by dataset/IVF/sampling/risk-statistic parameters.

### A7. Official runner integration for cost-reduced scorer

- Status: `done`
- Priority: highest after A6
- Goal: make the feature-cache and endpoint-grid scorer path available from
  the official fixed-policy runners instead of only from calibration scripts.
- Work completed:
  - added `--use-cost-reduced-scorer`, `--scorer-grid-preset`, and
    `--feature-cache-dir` to `script/run_default_neighborhood_cross_dataset.py`;
  - added the same forwarding options to `script/run_fixed_policy_matrix.py`;
  - made cost-reduced scorer artifacts use distinct scorer output prefixes;
  - recorded scorer mode and cache path in summary CSV/JSON outputs;
  - verified the official matrix runner against the clean table.
- Result:
  - `docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md`
  - updated `docs/saq_fixed_policy_method_spec_2026_07_07.md`
- Interpretation: the official runner now exposes feature-cache and endpoint
  grid execution as a reproducible scorer path. The integration verification
  matched 10/10 fixed-policy decisions and 10/10 selected/tested plans without
  rerunning safe-search evaluation.
- Constraint: this is a scorer execution/reproducibility improvement. The
  official integration keeps per-run sampling parameters unchanged; the
  separate `a1024_p2` sampling calibration is not promoted to default behavior.

### A8. Formal cost-reduced runner matrix evaluation

- Status: `done`
- Priority: highest after A7
- Goal: run the official fixed-policy matrix with the integrated
  cost-reduced scorer and safe-search evaluation enabled.
- Command:

```bash
python script/run_fixed_policy_matrix.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

- Result:
  - `docs/saq_fixed_policy_runner_cost_reduced_full_eval_2026_07_08.md`
  - `/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.md`
  - `/tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json`
- Interpretation: the official cost-reduced runner path matched the checked-in
  clean validation table with safe-search evaluation enabled: 6 promote,
  2 reject, and 2 abstain decisions.

### A9. Clean-root reproducibility and artifact-dependency review

- Status: `done`
- Priority: highest after A8
- Goal: make the local `/tmp/saq-run` dependency boundary explicit before
  claiming reproducibility beyond the current machine.
- Work completed:
  - added `script/check_fixed_policy_artifacts.py`;
  - classified artifacts into build, input, runner-generated, cache, and
    report groups;
  - ran the checker against the current cost-reduced full-evaluation date;
  - documented which artifacts must be pre-existing on a clean root and which
    can be regenerated by the fixed-policy runner.
- Result:
  - `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`
  - `/tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.json`
- Interpretation: the current local root has all enumerated artifacts
  present. The remaining clean-machine gap is dataset/PCA/IVF input
  provenance, not fixed-policy runner logic.

### A10. Input-artifact provenance manifest and hash layer

- Status: `done`
- Priority: highest after A9
- Goal: make the required dataset/PCA/IVF input artifacts checkable by file
  identity rather than only by path existence.
- Work completed:
  - added `script/write_fixed_policy_input_manifest.py`;
  - reused `script/check_fixed_policy_artifacts.py` to collect the fixed-policy
    input dependency set;
  - deduplicated the 23 input dependency entries into 20 unique files;
  - recorded path, role, producer hint, file size, inferred xvecs shape, mtime,
    and full-file SHA256 for each unique input file.
- Result:
  - `docs/saq_fixed_policy_input_manifest_2026_07_08.md`
  - `docs/saq_fixed_policy_input_manifest_2026_07_08.json`
  - updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`
- Interpretation: the current prepared inputs are now explicitly identifiable
  by full SHA256. At this step the remaining clean-machine gap was
  source/preparation provenance for recreating those files from raw datasets;
  A11 addresses that gap for the evaluated rows.

### A11. Input source and preparation provenance

- Status: `done`
- Priority: highest after A10
- Goal: explain how the current dataset/PCA/IVF/groundtruth input substrate was
  prepared from local source datasets.
- Work completed:
  - traced source files under `/rwproject/kdd-db/kluaq/dataset`;
  - read local preparation summaries under `/tmp/saq-run/data/*/*summary.json`;
  - recovered command-level preparation chains for GIST full K4096, CIFAR60K
    K512, and DEEP1M sample100K K512;
  - recorded source shapes and SHA256 prefixes for the relevant base/query/GT
    files;
  - marked audio and word2vec as partial provenance cases because the current
    fixed-policy matrix uses only their variance artifacts for abstention.
- Result:
  - `docs/saq_fixed_policy_input_preparation_provenance_2026_07_08.md`
  - updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`
- Interpretation: evaluated positive/reject rows now have a documented
  preparation chain. The remaining clean-machine gap is operational packaging:
  turn these notes into a one-command preparation script or archive the input
  bundle with manifest hashes.

### A12. One-command input preparation and verification driver

- Status: `done`
- Priority: highest after A11
- Goal: make the input provenance layer executable instead of only documented.
- Work completed:
  - added `script/prepare_fixed_policy_inputs.py`;
  - implemented `--verify-only` against the checked-in full-SHA256 manifest;
  - implemented `--dry-run` command rendering for all current matrix datasets;
  - implemented explicit `--prepare --dataset ...` execution for GIST, CIFAR,
    DEEP, and word2vec, with large-run guards for GIST/all-supported rebuilds;
  - preserved audio as a manifest-verifiable but clean-preparation-unsupported
    case because the exact historical PCA/IVF command was not recovered.
- Result:
  - `docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md`
  - updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`
- Validation:
  - `python -m py_compile script/prepare_fixed_policy_inputs.py script/write_fixed_policy_input_manifest.py`
  - `python script/prepare_fixed_policy_inputs.py --dry-run`
  - `python script/prepare_fixed_policy_inputs.py --dry-run --dataset cifar60k`
  - `python script/prepare_fixed_policy_inputs.py --dry-run --dataset audio`
  - `python script/prepare_fixed_policy_inputs.py --verify-only --output-json /tmp/saq-run/reports/fixed_policy_input_verify_2026_07_08.json`
- Interpretation: existing prepared inputs are now checkable by one command,
  and supported dataset preparation steps are executable from the same driver.
  The remaining clean-machine gap is to test the driver on a fresh root or
  archive a manifest-matching input bundle.

### A13. Boundary-risk scorer ablation package

- Status: `todo`
- Priority: highest before new candidate-family sweeps
- Hypothesis: the current fixed-policy story becomes paper-relevant only if the
  data-only boundary-risk scorer is shown to be safer or more selective than
  simple local alternatives. Without this evidence, a strict reviewer may read
  the method as handcrafted tuning around SAQ's default planner.
- Motivation: the scorer is currently empirical, multi-metric, and
  hyperparameter-heavy. This is a practical and novelty weakness unless the
  added terms demonstrably prevent unsafe decisions that simple baselines would
  make.
- Required comparisons:
  1. boundary-risk scorer vs speed-only scorer;
  2. boundary-risk scorer vs random local candidate selection;
  3. conservative promotion vs frontier-like promotion;
  4. policy with and without soft-inversion / pair-ratio guards;
  5. selected candidate vs local oracle within the generated neighborhood;
  6. proxy-score correlation with measured recall delta and QPS ratio.
- Evaluation set: start from the existing fixed-policy matrix so the comparison
  includes GIST/CIFAR positives, DEEP reject controls, and audio/word2vec
  abstentions before adding any new datasets or candidate families.
- Success: a durable report under `docs/` showing which components are needed,
  where the scorer fails, and whether the policy has evidence beyond speed-only
  or random-local tuning.
- Stop condition: if boundary-risk is not meaningfully safer than these simple
  baselines, stop adding local candidate families and pivot to a clearer SAQ
  limitation such as planner-objective redesign, segment-cost-aware DP, or a
  more explainable search-aware query-unaware proxy.
- Simplicity rule: if a fixed single-configuration scorer or a much smaller
  metric set preserves the same known promote/reject/abstain boundary, prefer
  the simpler version in future method narratives.

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

- Status: `done`
- Priority: high
- Known false positive: GIST sample100k B=5 raw v3 endpoint `64:9,64:8,128:7,320:5,320:3,64:0`.
- Hypothesis: conservative role guard prevents promotion because soft-inversion ratio, weighted ratio, and speed-proxy ratio are all worse than default.
- Success: demonstrate from current CSV/roles output that the guard promotes `b5_rank0 = 64:10,192:8,256:5,384:3,64:0` instead.
- Result: verified from `/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.roles.csv` and documented in `docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md`.
- Output: small note in `PROGRESS.md` unless a durable doc is missing.

### B3. Frontier-like fallback review

- Status: `done`
- Priority: medium
- Known reason: CIFAR B=4 is a small positive selected as `frontier_like`; strict conservative guard alone would be too strict.
- Hypothesis: frontier-like fallback is necessary but should remain narrow.
- Work:
  - inspect CIFAR B=3/B=4/B=5 scorer summaries;
  - check whether `best_recall_risk_score <= 1.0` and `best_speed_proxy_ratio_vs_default <= 1.0` explain the promotion;
  - check that DEEP risky candidates do not pass the fallback.
- Success: document the boundary of frontier-like fallback.
- Result: documented in `docs/saq_fixed_policy_decision_audit_2026_07_07.md` and rechecked from `/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv`.

### B4. Abstention review

- Status: `done`
- Priority: medium
- Known abstentions: audio and word2vec under B=3/B=4/B=5.
- Hypothesis: abstention follows from single-uniform default plans and no feasible non-default candidates under the current default-neighborhood generator.
- Command:

```bash
python script/scan_default_neighborhood_applicability.py \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_applicability_scan_$(date +%Y_%m_%d)
```

- Success: scan confirms stable abstention, or reports an actual generator change.
- Result: fresh scan `/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv` confirms audio and word2vec B=3/B=4/B=5 are single-uniform with zero non-default candidates.
- Do not force an arbitrary non-default plan for these datasets unless the generator is intentionally expanded.

## C. Method Extension Ideas

### C1. Expand generator only within query-unaware default-neighborhood logic

- Status: `todo`
- Priority: low until A0 is completed
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
- Novelty/overhead gate: before implementing a new family, explain why it is
  not just more hand-tuning around SAQ and how much extra candidate/scorer/index
  cost it adds.

### C2. Better applicability classifier

- Status: `done`
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
- Result: `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md`.

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

### D2. Artifact-staleness review

- Status: `done`
- Priority: medium
- Problem: many outputs live under `/tmp/saq-run`, which is not durable.
- Work:
  - identify which checked-in docs rely on local artifacts;
  - record exact commands to regenerate them;
  - add clearer “artifact required” notes in docs or scripts.
- Success: a future Codex session can understand missing artifacts without guessing.
- Result: `docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md`.

### D3. Avoid metric cherry-picking

- Status: `done`
- Priority: medium
- Work:
  - ensure each result states nprobe, top-k, and QPS setting;
  - avoid promoting a plan that only wins at one cherry-picked nprobe if broader behavior is negative;
  - state whether small recall deltas are practically meaningful.
- Result: `docs/saq_fixed_policy_metric_audit_2026_07_07.md`.

### D4. Avoid overhead cherry-picking

- Status: `done`
- Priority: high
- Work:
  - report the method overhead separately from experimental overhead;
  - avoid comparing only final selected-index QPS while hiding candidate
    scoring/build costs;
  - distinguish "deployable one-index pipeline" from "research sweep that built
    many indexes";
  - record whether any metadata or search-time branches are added beyond SAQ.
- Success: future slides/docs cannot imply strict superiority unless overhead
  is included or explicitly scoped out.
- Result: covered by
  `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`.

## E. Documentation / Meeting Narrative

### E1. Produce concise method summary

- Status: `done`
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
- Result: `docs/saq_fixed_policy_meeting_summary_2026_07_07.md`.

### E2. Paper-style method spec cleanup

- Status: `done`
- Priority: medium
- Goal: turn `docs/saq_fixed_policy_method_spec_2026_07_07.md` into a more formal method section.
- Caution: do not hide empirical threshold choices or overclaim theoretical guarantees.
- Result: updated `docs/saq_fixed_policy_method_spec_2026_07_07.md` with a paper-style method definition and evidence boundary.

### E3. Handoff update

- Status: `done`
- Priority: medium
- Goal: update `codex_handoff.md` or create a new handoff after the latest fixed-policy progress, because the old handoff emphasizes the B=5 false-positive recovery state.
- Success: future context compaction starts from the fixed-policy method state, not the older v3-guard-only state.
- Result: updated `codex_handoff.md` on 2026-07-07.

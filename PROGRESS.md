# PROGRESS.md

This file is the running log for autonomous Codex work on `saq-boundary-audit`.

Codex must update this file during each session. Prefer factual, command-backed notes over speculation.

## Current Baseline As Of 2026-07-07

### Research Direction

The active direction is query-unaware SAQ follow-up work. The current method story is a fixed policy around SAQ's default segment plan:

1. classify the SAQ default plan shape;
2. generate local default-neighborhood candidates;
3. score candidates with data-only boundary-risk and speed proxies;
4. promote conservative/frontier-like candidates;
5. reject candidates that trade too much recall for speed;
6. abstain when no meaningful local neighborhood exists.

### Current Evidence

| Setting | Current decision | Plan | Measured interpretation |
|---|---:|---|---|
| GIST full K4096 B=3 | promote | `64:8,320:5,320:2,256:0` | positive after 1-bit fix; +0.00159 R@100, 1.1119x QPS at np800 |
| GIST full K4096 B=4 | promote | `128:9,320:5,320:3,192:0` | strongest QPS-positive GIST case; +0.00077 R@100, 1.1948x QPS at np800 |
| GIST full K4096 B=5 | promote | `128:9,128:7,320:5,320:3,64:0` | positive high-budget holdout; +0.00028 R@100, 1.0793x QPS at np800 |
| CIFAR60K B=3 | promote | `128:6,64:4,192:2,128:0` | small positive; +0.0004 R@10, 1.0761x QPS at np200 |
| CIFAR60K B=4 | promote | `128:7,256:4,128:0` | small positive; +0.0004 R@10, 1.0745x QPS at np200 |
| CIFAR60K B=5 | promote | `128:8,64:6,256:4,64:0` | small positive; +0.0008 R@10, 1.0609x QPS at np200 |
| DEEP100K B=4 | reject | `128:4,128:3` | QPS improves but recall drops too much; -0.02757 R@100, 1.0893x QPS at np200 |
| DEEP100K B=5 | reject | `128:5,128:4` | QPS improves but recall drops too much; -0.01429 R@100, 1.1037x QPS at np200 |
| audio B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |
| word2vec100K B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |

Source of this baseline: `docs/saq_fixed_policy_method_spec_2026_07_07.md` and `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`.

### Known Implementation/Method Notes

- `script/run_default_neighborhood_cross_dataset.py` connects candidate generation, scoring, index build, recall comparison, and QPS measurement.
- `script/run_fixed_policy_matrix.py` is the end-to-end matrix runner for the fixed-policy evidence table.
- `script/report_fixed_policy_validation.py` regenerates the clean validation table/report from summary outputs and can compare against the checked-in expected CSV.
- `script/sweep_data_boundary_pairs.py` contains planner v3 and conservative role fields.
- GIST B=3 required a minimal 1-bit CAQ segment fix touching:
  - `saqlib/quantization/caq/caq_encoder.hpp`
  - `saqlib/quantization/cluster_packer.hpp`
- All measured recall/QPS claims must use `-searcher_safe_block_min_mode=2`.

## Session Log Template

Copy this block for each autonomous run.

```md
## Session YYYY-MM-DD HH:MM local

### Goal

### Starting state
- Branch:
- `git status --short`:
- Files read:

### Hypothesis / plan

### Commands run

```bash
# paste exact commands here
```

### Files changed

### Artifacts produced

### Result

### Interpretation

### Problems / blockers

### Next action
```

## Session 2026-07-07 Initial External Setup

### Goal

Create autonomous-iteration control files for future Codex sessions based on the current public `saq-boundary-audit` branch state.

### Starting state

This file was generated outside the repository from the public GitHub branch. It has not been validated by running local repository commands.

### Files read remotely

- `AGENTS.md`
- `codex_handoff.md`
- `README.md`
- `docs/saq_fixed_policy_method_spec_2026_07_07.md`
- `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
- `docs/saq_stage_synthesis_v3_conservative_2026_07_06.md`
- `docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md`
- `docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md`
- `docs/saq_default_neighborhood_applicability_scan_2026_07_06.md`
- `docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md`

### Result

Prepared `AGENTS.md`, `TASK.md`, `PROGRESS.md`, `EXPERIMENTS.md`, and `RESULTS.md` for repo-local use.

### Next action

Place these files at the repository root, inspect the diff, then start Codex with the prompt in `TASK.md` or with:

```bash
codex exec --sandbox workspace-write --ask-for-approval never --cd . - < TASK.md
```

## Session 2026-07-07 15:55 HKT

### Goal

Install the uploaded autonomous-iteration control files into the repository root
and make the stricter project-specific `AGENTS.md` the active guidance for
future Codex sessions.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short`: clean after pulling `saq_codex_autonomy_files.zip`
- Files read:
  - existing root `AGENTS.md`
  - `/tmp/codex_context_readonly/saq_codex_autonomy_files/AGENTS.md`
  - `/tmp/codex_context_readonly/saq_codex_autonomy_files/TASK.md`
  - `/tmp/codex_context_readonly/saq_codex_autonomy_files/PROGRESS.md`
  - `/tmp/codex_context_readonly/saq_codex_autonomy_files/EXPERIMENTS.md`
  - `/tmp/codex_context_readonly/saq_codex_autonomy_files/RESULTS.md`

### Hypothesis / plan

The uploaded `AGENTS.md` is a stricter superset of the existing root guidance:
it preserves repo layout/build/test rules and adds the current fixed-policy
research direction, non-negotiable query-unaware constraints, and autonomous
iteration protocol. Replace root `AGENTS.md` with the uploaded version and place
the remaining control files at the repo root.

### Commands run

```bash
git status --short --branch
sed -n '1,220p' AGENTS.md
sed -n '1,260p' /tmp/codex_context_readonly/saq_codex_autonomy_files/AGENTS.md
find /tmp/codex_context_readonly/saq_codex_autonomy_files -maxdepth 1 -type f -printf '%f\n' | sort
cp /tmp/codex_context_readonly/saq_codex_autonomy_files/AGENTS.md /tmp/codex_context_readonly/saq_codex_autonomy_files/TASK.md /tmp/codex_context_readonly/saq_codex_autonomy_files/PROGRESS.md /tmp/codex_context_readonly/saq_codex_autonomy_files/EXPERIMENTS.md /tmp/codex_context_readonly/saq_codex_autonomy_files/RESULTS.md .
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Replaced `AGENTS.md` with the uploaded stricter project-specific guidance.
- Added `TASK.md`.
- Added `EXPERIMENTS.md`.
- Added `RESULTS.md`.
- Added and then updated `PROGRESS.md` with this session log.

### Artifacts produced

No experiment artifacts were produced. The extracted source files remain under:

```text
/tmp/codex_context_readonly/saq_codex_autonomy_files/
```

### Result

The uploaded autonomy/control files are now present at the repository root. The
root `AGENTS.md` now points future Codex sessions toward the query-unaware
fixed-policy SAQ follow-up and its validation constraints.

### Interpretation

Future autonomous work should start from `TASK.md`, `PROGRESS.md`,
`EXPERIMENTS.md`, and `RESULTS.md`, rather than from older handoff state or
memory.

### Problems / blockers

None.

### Next action

Run the required lightweight validation commands from `TASK.md`, then commit
the installed control files if the diff is clean.

## Session 2026-07-07 16:14 HKT

### Goal

Start autonomous iteration under the repository control files and complete the
highest-priority reproducibility checks A1/A2/A3.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `TASK.md`
  - `PROGRESS.md`
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `docs/saq_default_neighborhood_applicability_scan_2026_07_06.md`

### Hypothesis / plan

The current scripts should already reproduce the fixed-policy table from local
`/tmp/saq-run` artifacts. Verify the cheap syntax checks first, then verify the
report driver and full matrix runner before attempting any policy changes.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' TASK.md
sed -n '1,260p' PROGRESS.md
sed -n '1,260p' EXPERIMENTS.md
sed -n '1,240p' RESULTS.md
sed -n '1,220p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,40p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
sed -n '1,220p' docs/saq_default_neighborhood_applicability_scan_2026_07_06.md
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
python script/report_fixed_policy_validation.py --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
python script/run_fixed_policy_matrix.py --artifact-date 2026_07_06 --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- `EXPERIMENTS.md`: marked A1, A2, and A3 as `done`.
- `RESULTS.md`: added a stable reproducibility result for the report and matrix runner.
- `PROGRESS.md`: added this session log.

### Artifacts produced

```text
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.md
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.md
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json
```

### Result

- Python syntax checks passed for the required planner/report scripts.
- `script/report_fixed_policy_validation.py` regenerated the report and matched
  `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv` exactly.
- `script/run_fixed_policy_matrix.py --artifact-date 2026_07_06` reused existing
  candidate/scorer/compare/QPS artifacts and reproduced the same clean table,
  ignoring only the expected `source_report` field difference.
- Matrix decision counts were `promote=6`, `reject=2`, `abstain=2`.

### Interpretation

Primary success criteria 1 and 2 are satisfied on this machine: the current
fixed-policy evidence table is reproducible from local artifacts. This does not
remove the `/tmp/saq-run` durability caveat, but it verifies that the checked-in
scripts and current local artifacts are internally consistent.

### Problems / blockers

None for A1/A2/A3. The main residual risk is artifact portability: the matrix
depends on local `/tmp/saq-run` data, indexes, compare CSVs, and QPS outputs.

### Next action

Commit and push this reproducibility checkpoint. Then continue with B1: a
row-by-row policy robustness audit mapping clean-table decisions to
conservative/frontier/reject/abstain signals.

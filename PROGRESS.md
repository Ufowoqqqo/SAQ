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

## Session 2026-07-07 16:32 HKT

### Goal

Complete B1: audit whether each row in the clean fixed-policy validation table
is explainable from the implemented query-unaware policy roles.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `f7be443 Record fixed-policy reproducibility checkpoint`
- Files/artifacts read:
  - `script/run_default_neighborhood_cross_dataset.py`
  - `script/report_fixed_policy_validation.py`
  - `script/score_default_neighborhood_plans.py`
  - `script/sweep_data_boundary_pairs.py`
  - `/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv`
  - `/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv`
  - per-run scored unique CSVs under `/tmp/saq-run/reports/*_default_neighborhood_scored_auto_2026_07_06.unique.csv`

### Hypothesis / plan

The clean table should decompose into four implemented policy cases:
GIST conservative promotions, CIFAR frontier-like promotions, DEEP risky
fallback diagnostics mapped to reject, and audio/word2vec no-candidate
abstentions.

### Commands run

```bash
python - <<'PY'
import csv
from pathlib import Path
p=Path('/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv')
for r in csv.DictReader(p.open()):
    print('\t'.join([r.get('run',''), r.get('selection_reason',''), r.get('candidate_family',''), r.get('best_recall_risk_score',''), r.get('best_speed_proxy_ratio_vs_default',''), r.get('conservative_eligible',''), r.get('conservative_reasons',''), r.get('candidate_plan',''), r.get('scorer_skipped_reason','')]))
PY
python - <<'PY'
import csv
from pathlib import Path
p=Path('/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv')
for r in csv.DictReader(p.open()):
    if (r['dataset'], r['avg_bits']) in {('audio','4.0'),('word2vec_sample100k','4.0'),('gist_full','3.0'),('gist_full','4.0'),('gist_full','5.0'),('cifar60k','3.0'),('cifar60k','4.0'),('cifar60k','5.0'),('deep1M_sample100k','4.0'),('deep1M_sample100k','5.0')}:
        print('\t'.join([r['dataset'], r['avg_bits'], r['default_shape'], r['default_plan'], r['feasible_non_default_candidate_count'], r['applicability'], r['default_zero_tail_dim'], r['default_positive_bitwidths']]))
PY
sed -n '380,455p' script/run_default_neighborhood_cross_dataset.py
sed -n '145,210p' script/report_fixed_policy_validation.py
rg -n "conservative_role|soft_inversion|weighted_ratio|speed_proxy_ratio|frontier_like|risky_fallback" script/score_default_neighborhood_plans.py script/sweep_data_boundary_pairs.py script/run_default_neighborhood_cross_dataset.py script/report_fixed_policy_validation.py
python - <<'PY'
import csv
from pathlib import Path
runs=['gist_full_K4096_B3','gist_full_K4096_B4','gist_full_K4096_B5','cifar60k_B3','cifar60k_B4','cifar60k_B5','deep1M_sample100k_B4','deep1M_sample100k_B5']
for run in runs:
    p=Path(f'/tmp/saq-run/reports/{run}_default_neighborhood_scored_auto_2026_07_06.unique.csv')
    rows=list(csv.DictReader(p.open()))
    print('\n',run)
    for r in [x for x in rows if x.get('candidate_is_default','').lower()!='true']:
        print('\t'.join([r['seg_plan'], r.get('candidate_families',''), r.get('conservative_role_is_eligible',''), r.get('conservative_role_reasons',''), r.get('best_recall_risk_score',''), r.get('best_speed_proxy_ratio_vs_default',''), r.get('pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default',''), r.get('pair_proxy_weighted_ratio_mean_ratio_vs_default','')]))
PY
```

### Files changed

- Added `docs/saq_fixed_policy_decision_audit_2026_07_07.md`.
- Marked B1 done in `EXPERIMENTS.md`.
- Added a stable B1 result in `RESULTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

No new experiment artifacts. The durable output is:

```text
docs/saq_fixed_policy_decision_audit_2026_07_07.md
```

### Result

The clean table is consistent with the implemented policy roles:

```text
GIST positives: conservative_eligible
CIFAR positives: frontier_like
DEEP controls: risky_fallback_best_score -> reject
audio/word2vec: generator_produced_no_non_default_candidates -> abstain
```

The audit also records report-generation caveats: the report trusts stored
`selection_reason`, keeps the first source row per run, and uses
`scorer_skipped_reason` for abstention only after promote/reject role checks.

### Interpretation

B1 is satisfied. The current clean table is not an arbitrary post-hoc mix of
measured wins; it follows a small implemented policy. The main caution remains
the empirical frontier-like fallback, not a mismatch between code and table.

### Problems / blockers

None.

### Next action

Commit and push the B1 audit checkpoint. Then continue with B2/B3: document the
known GIST B=5 false-positive resistance and CIFAR frontier-like boundary.

## Session 2026-07-07 16:25 HKT

### Goal

Complete B2/B3 by rechecking the known GIST sample100k B=5 false-positive guard
and the CIFAR frontier-like fallback boundary without running new expensive
experiments.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `a4e18eb Add fixed-policy decision audit`
- Files/artifacts read:
  - `docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md`
  - `docs/saq_fixed_policy_decision_audit_2026_07_07.md`
  - `/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.roles.csv`
  - `/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv`

### Hypothesis / plan

B2 should already be satisfied by the existing conservative-guard note: the raw
GIST sample100k B=5 recall-risk endpoint is rejected on soft inversion,
weighted ratio, and speed proxy, while the conservative role selects
`b5_rank0`. B3 should already be covered by the clean-table audit: CIFAR passes
frontier-like because recall-risk and speed proxy are both <= 1, while DEEP does
not pass because recall-risk is 1.6434.

### Commands run

```bash
find docs /tmp/saq-run/reports -name '*B5*v3*conservative*' -o -name '*B5*guard*' -o -name '*sample100k*B5*' | sort
sed -n '1,260p' docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md
python - <<'PY'
import csv
from pathlib import Path
p=Path('/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.roles.csv')
for r in csv.DictReader(p.open()):
    print('\t'.join([r.get('role',''), r.get('seg_plan',''), r.get('conservative_role_is_eligible',''), r.get('conservative_role_reasons',''), r.get('best_recall_risk_score',''), r.get('best_speed_proxy_ratio_vs_default',''), r.get('pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default',''), r.get('pair_proxy_weighted_ratio_mean_ratio_vs_default','')]))
PY
python - <<'PY'
import csv
from pathlib import Path
for run in ['cifar60k_B3','cifar60k_B4','cifar60k_B5','deep1M_sample100k_B4','deep1M_sample100k_B5']:
    p=Path('/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv')
    rows=[r for r in csv.DictReader(p.open()) if r['run']==run]
    for r in rows:
        print('\t'.join([r['run'], r['selection_reason'], r.get('best_recall_risk_score',''), r.get('best_speed_proxy_ratio_vs_default',''), r.get('conservative_eligible',''), r.get('conservative_reasons',''), r.get('candidate_plan','')]))
PY
sed -n '70,140p' docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- `EXPERIMENTS.md`: marked B2 and B3 as `done` with artifact/doc references.
- `PROGRESS.md`: added this session log.

### Artifacts produced

No new artifacts. This was a read-only audit of existing docs and `/tmp` CSVs.

### Result

- B2: the raw GIST sample100k B=5 endpoint
  `64:9,64:8,128:7,320:5,320:3,64:0` is rejected with
  `soft_inversion_ratio>1;weighted_ratio>1;speed_proxy_ratio>1`. The
  conservative roles select `64:10,192:8,256:5,384:3,64:0`.
- B3: CIFAR B=3/B=4/B=5 are frontier-like with recall-risk <= 1 and
  speed-proxy <= 1, while DEEP B=4/B=5 remain risky fallback diagnostics because
  recall-risk is `1.6434`.

### Interpretation

B2 and B3 are complete with existing evidence. The current policy blocks the
known false-positive shape and keeps the frontier-like fallback narrow enough
that DEEP speed-only changes are not promoted.

### Problems / blockers

None.

### Next action

Commit and push the B2/B3 status update. The next highest-value task is either
B4 abstention audit or E1 meeting/paper narrative cleanup, depending on whether
the next session should emphasize robustness or presentation.

## Session 2026-07-07 16:27 HKT

### Goal

Complete B4: verify that current audio and word2vec abstentions remain stable
under the fresh fixed-policy applicability scan.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `5f949e9 Record policy boundary audits`
- Artifact read:
  - `/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv`

### Hypothesis / plan

The abstentions should follow from generator/applicability state, not failed
measurement: audio and word2vec should have single-uniform default plans and no
non-default candidates at B=3/B=4/B=5.

### Commands run

```bash
git status --short --branch
python - <<'PY'
import csv
from pathlib import Path
p=Path('/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv')
for r in csv.DictReader(p.open()):
    if r['dataset'] in {'audio','word2vec_sample100k'}:
        print('\t'.join([r['dataset'], r['avg_bits'], r['default_plan'], r['default_shape'], r['candidate_count'], r['non_default_candidate_count'], r['feasible_non_default_candidate_count'], r['applicability']]))
PY
sed -n '1,120p' /tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- `EXPERIMENTS.md`: marked B4 as `done`.
- `PROGRESS.md`: added this session log.

### Artifacts produced

No new artifacts. Reused:

```text
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
```

### Result

Fresh scan confirms:

```text
audio B=3/4/5: default 192:3/4/5, single_uniform, 0 non-default candidates
word2vec_sample100k B=3/4/5: default 320:3/4/5, single_uniform, 0 non-default candidates
```

### Interpretation

B4 is satisfied. Audio and word2vec are stable abstention cases under the
current default-neighborhood generator, not negative measured candidates.

### Problems / blockers

None.

### Next action

Commit and push the B4 status update. Then move to E1 meeting/paper narrative
cleanup, since the main reproducibility and robustness audits are now complete.

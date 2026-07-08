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

## Session 2026-07-07 16:34 HKT

### Goal

Complete E1: produce a concise meeting/paper-facing summary of the fixed-policy
method, evidence, implementation fix, limitations, and open questions.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `708b316 Record abstention audit`
- Files read:
  - `docs/saq_stage_synthesis_v3_conservative_2026_07_06.md`
  - `docs/saq_meeting_slides_v3_conservative_2026_07_06.md`
  - `docs/saq_fixed_policy_decision_audit_2026_07_07.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`

### Hypothesis / plan

The existing slides and synthesis are useful but broad. Add a shorter summary
that is self-contained for a meeting: method claim, algorithm steps, evidence
table, positive/reject/abstain cases, implementation fix separation,
limitations, and discussion questions.

### Commands run

```bash
find docs -maxdepth 1 -iname '*summary*' -o -iname '*meeting*' | sort
sed -n '1,140p' docs/saq_stage_synthesis_v3_conservative_2026_07_06.md
sed -n '1,140p' docs/saq_meeting_slides_v3_conservative_2026_07_06.md
sed -n '1,220p' docs/saq_fixed_policy_decision_audit_2026_07_07.md
```

### Files changed

- Added `docs/saq_fixed_policy_meeting_summary_2026_07_07.md`.
- Marked E1 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_meeting_summary_2026_07_07.md
```

### Result

The new meeting summary states the fixed-policy contribution candidate,
describes the algorithm, includes the current clean evidence table, separates
the GIST B=3 1-bit correctness fix from the method contribution, and lists
limitations plus meeting questions.

### Interpretation

E1 is satisfied. The project now has both a detailed synthesis/slides and a
shorter meeting-facing summary grounded in the reproducible fixed-policy table.

### Problems / blockers

None.

### Next action

Commit and push the E1 summary checkpoint. After that, the highest-value next
autonomous task is likely C2: a compact applicability classifier/table, unless
the user wants to pause for meeting review.

## Session 2026-07-07 16:36 HKT

### Goal

Complete C2: make the current applicability boundary more explicit than
"multi-segment with zero tail."

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `def250a Add fixed-policy meeting summary`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_default_neighborhood_applicability_scan_2026_07_06.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `script/scan_default_neighborhood_applicability.py`
  - `script/generate_default_neighborhood_plans.py`
  - `script/run_default_neighborhood_cross_dataset.py`

### Hypothesis / plan

The policy boundary should be documented as a two-stage classifier:
pre-scorer applicability based on default-plan shape and feasible candidate
count, then post-scorer promotion/reject/abstain based on conservative and
frontier-like scorer signals.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,220p' docs/saq_default_neighborhood_applicability_scan_2026_07_06.md
sed -n '1,80p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
rg -n "single_uniform|multi_segment|default_shape|frontier_like|conservative_eligible|risky_fallback" script/run_default_neighborhood_cross_dataset.py script/generate_default_neighborhood_plans.py script/scan_default_neighborhood_applicability.py script/report_fixed_policy_validation.py
sed -n '1,220p' script/scan_default_neighborhood_applicability.py
sed -n '1,260p' script/generate_default_neighborhood_plans.py
sed -n '700,860p' script/run_default_neighborhood_cross_dataset.py
sed -n '380,455p' script/run_default_neighborhood_cross_dataset.py
sed -n '260,560p' script/generate_default_neighborhood_plans.py
sed -n '220,360p' script/scan_default_neighborhood_applicability.py
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md`.
- Marked C2 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
```

### Result

The new note defines the current classifier as:

1. pre-scorer applicability from default-plan shape and feasible non-default
   candidate count;
2. post-scorer decision from conservative/frontier-like/risky-fallback roles.

It maps GIST, CIFAR, DEEP, audio, and word2vec into positive, reject/control,
and abstention classes using only existing evidence.

### Interpretation

C2 is satisfied. The method boundary is now easier to discuss without implying
that shape scan alone proves a positive result.

### Problems / blockers

None.

### Next action

Validate the documentation diff, commit and push this C2 checkpoint. The next
useful autonomous task is E2: fold the classifier into a more formal
paper-style method spec, or E3: update the handoff state for future compaction.

## Session 2026-07-07 16:40 HKT

### Goal

Complete E3: update the recovery handoff so future context compaction starts
from the fixed-policy method state instead of the older v3 endpoint recovery
state.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `5401b3f Document fixed-policy applicability classifier`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `codex_handoff.md`
  - `TASK.md`
  - `RESULTS.md`
  - `EXPERIMENTS.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md`

### Hypothesis / plan

The existing handoff is stale because it centers on the July 6 planner-v3 B=5
false-positive recovery. Replace it with a July 7 handoff centered on the
query-unaware default-neighborhood fixed-policy baseline, current evidence,
constraints, uncertainties, and next commands.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' codex_handoff.md
sed -n '180,260p' EXPERIMENTS.md
sed -n '1,220p' docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
git log --oneline -8
sed -n '1,220p' TASK.md
sed -n '1,180p' RESULTS.md
sed -n '1,120p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Rewrote `codex_handoff.md`.
- Marked E3 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
codex_handoff.md
```

### Result

The handoff now records the fixed-policy method, current evidence table,
important constraints, uncertainties, remaining TODOs, already-run validation
commands, and next commands.

### Interpretation

E3 is satisfied. Future sessions should no longer recover into the outdated
B=5 endpoint state unless explicitly asked to inspect that history.

### Problems / blockers

None.

### Next action

Validate the handoff diff, commit and push. After this checkpoint, the next
best task is E2 paper-style method spec cleanup or D2 artifact-staleness audit.

## Session 2026-07-07 16:48 HKT

### Goal

Complete D2: audit the artifact-staleness risk for the current fixed-policy
claim and document how to regenerate or diagnose missing artifacts.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `baec55b Update fixed-policy handoff`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files/artifacts read:
  - `TASK.md`
  - `PROGRESS.md`
  - `RESULTS.md`
  - `EXPERIMENTS.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json`
  - `/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.md`
  - local `/tmp/saq-run/reports/*default_neighborhood*` artifact listing
  - `script/run_fixed_policy_matrix.py`

### Hypothesis / plan

The useful audit scope is not every historical `/tmp` reference in `docs/`.
Instead, document the minimum artifact chain for the current fixed-policy
claim: durable checked-in table/docs, local matrix/report artifacts, source
reports, and the difference between report-only, matrix-from-cache, and
clean-machine regeneration.

### Commands run

```bash
git status --short --branch
rg -n "/tmp/saq-run|source_report|artifact|artifacts" TASK.md PROGRESS.md RESULTS.md EXPERIMENTS.md docs script/report_fixed_policy_validation.py script/run_fixed_policy_matrix.py
find /tmp/saq-run/reports -maxdepth 1 -type f -name '*fixed_policy*2026_07_07*' -printf '%f\n'
sed -n '1,260p' script/run_fixed_policy_matrix.py
sed -n '1,240p' /tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json
sed -n '1,220p' /tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.md
python - <<'PY'
import csv
from pathlib import Path
p=Path('docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv')
with p.open(newline='') as f:
    for row in csv.DictReader(f):
        print(row['run'], row['source_report'])
PY
find /tmp/saq-run/reports -maxdepth 1 -type f \( -name 'default_neighborhood_*2026_07_06.csv' -o -name 'default_neighborhood_*2026_07_07.csv' -o -name '*default_neighborhood*_2026_07_06.*' \) -printf '%f\n' | sort
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md`.
- Marked D2 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md
```

### Result

The audit separates durable checked-in sources from local `/tmp/saq-run`
artifacts, records the current source report mapping, and defines three
reproduction levels: report-only, matrix-from-existing-artifacts, and
clean-machine regeneration.

### Interpretation

D2 is satisfied. The current table is durable as a summary, but full
clean-machine regeneration still needs more dataset/artifact preparation
documentation.

### Problems / blockers

None.

### Next action

Validate the documentation diff, commit and push. The next useful task is D3
metric cherry-picking audit or E2 paper-style method spec cleanup.

## Session 2026-07-07 16:51 HKT

### Goal

Complete D3: audit metric/top-k/nprobe/QPS reporting to avoid cherry-picking or
overstated headline claims.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `4342dd2 Audit fixed-policy artifact staleness`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files/artifacts read:
  - `/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_fixed_policy_meeting_summary_2026_07_07.md`
  - `docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md`
  - `docs/saq_gist_budget_holdout_2026_07_06.md`
  - `docs/saq_cifar_budget_holdout_2026_07_06.md`
  - `docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md`

### Hypothesis / plan

The clean table is useful but only shows headline nprobe. Audit the underlying
matrix summary to determine whether recall gains hold across measured nprobe
values and where QPS remains headline-only.

### Commands run

```bash
git status --short --branch
sed -n '1,80p' /tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
sed -n '1,220p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
rg -n "nprobe|R@|top-k|top100|top10|QPS|qps|np800|np200" docs/saq_fixed_policy_method_spec_2026_07_07.md docs/saq_fixed_policy_meeting_summary_2026_07_07.md docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md docs/saq_gist_budget_holdout_2026_07_06.md docs/saq_cifar_budget_holdout_2026_07_06.md docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_fixed_policy_metric_audit_2026_07_07.md`.
- Marked D3 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_metric_audit_2026_07_07.md
```

### Result

The audit records that GIST B=3/4/5, CIFAR B=3/B=5, and DEEP reject cases have
consistent multi-nprobe recall behavior. CIFAR B=4 is positive at np100/200/400
but negative at np50, so it should be described as a small frontier-like
headline positive rather than uniformly positive. QPS is currently measured at
one headline nprobe per run.

### Interpretation

D3 is satisfied. The current evidence is meeting-ready if worded carefully, but
paper-ready speed claims need either QPS curves or explicit headline-operating
point framing.

### Problems / blockers

None.

### Next action

Validate the documentation diff, commit and push. The next useful task is E2
paper-style method spec cleanup, incorporating the classifier, artifact audit,
and metric audit.

## Session 2026-07-07 16:54 HKT

### Goal

Complete E2: make the fixed-policy method spec more paper-style while preserving
the empirical thresholds and evidence limitations.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `2662976 Audit fixed-policy metric reporting`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md`
  - `docs/saq_fixed_policy_metric_audit_2026_07_07.md`

### Hypothesis / plan

The existing method spec is accurate but still reads like an experiment report.
Add a paper-style method definition at the top and an evidence-boundary section
at the end, incorporating the classifier, artifact audit, and metric audit
without changing any experimental values.

### Commands run

```bash
git status --short --branch
sed -n '1,360p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,220p' docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
sed -n '1,220p' docs/saq_fixed_policy_metric_audit_2026_07_07.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Updated `docs/saq_fixed_policy_method_spec_2026_07_07.md`.
- Marked E2 done in `EXPERIMENTS.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

No generated artifacts. Durable documentation update:

```text
docs/saq_fixed_policy_method_spec_2026_07_07.md
```

### Result

The method spec now starts with a formal input/output decision policy and ends
with an explicit evidence boundary covering applicability, metric/QPS limits,
and artifact durability.

### Interpretation

E2 is satisfied. The current documentation set is meeting-ready and closer to a
paper method section, while still avoiding theoretical or universal claims.

### Problems / blockers

None.

### Next action

Validate the documentation diff, commit and push. After this checkpoint, pause
unless starting new code/experiment work; the current autonomy documentation
tasks are largely complete.

## Session 2026-07-07 17:17 HKT

### Goal

Create an updated English meeting slide deck from the latest fixed-policy
meeting summary, assuming the audience has almost no context about this project.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `docs/saq_fixed_policy_meeting_summary_2026_07_07.md`
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_meeting_slides_v3_conservative_2026_07_06.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
  - `docs/saq_fixed_policy_metric_audit_2026_07_07.md`
  - `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md`
  - `docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md`

### Hypothesis / plan

The old slide deck focuses on the intermediate v3/conservative story. Create a
new fixed-policy slide deck that starts from ANNS/vector quantization basics,
introduces SAQ and segment-plan notation, then explains the fixed-policy method
with a GIST B=4 running example, current evidence, caveats, and meeting
questions.

### Commands run

```bash
git status --short --branch
sed -n '1,240p' AGENTS.md
sed -n '1,260p' TASK.md
find docs -maxdepth 1 -iname '*slide*' -o -iname '*meeting*summary*' -o -iname '*method*spec*' | sort
sed -n '1,260p' docs/saq_fixed_policy_meeting_summary_2026_07_07.md
sed -n '1,260p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,260p' docs/saq_meeting_slides_v3_conservative_2026_07_06.md
sed -n '1,140p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
sed -n '260,520p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,240p' docs/saq_fixed_policy_metric_audit_2026_07_07.md
sed -n '1,220p' docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
sed -n '1,220p' docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_fixed_policy_meeting_slides_2026_07_07.md`.
- Added this session log in `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_meeting_slides_2026_07_07.md
```

### Result

The new English deck contains 32 markdown slides. It explains the project from
vector quantization basics through SAQ, default segment plans, the
query-unaware fixed-policy workflow, boundary-pair scoring, promotion/reject/
abstain decisions, evidence, metric caveats, reproducibility status, and next
meeting questions. GIST full K4096 B=4 is used as the running example.

### Interpretation

This deck is intentionally verbose and self-contained for an advisor who knows
vector search but not this specific SAQ follow-up branch.

### Problems / blockers

None.

### Next action

Validate markdown/doc diff, commit, and push.

## Session 2026-07-07 20:35 HKT

### Goal

Update the autonomy/control files to make novelty and overhead first-class
constraints, preventing future iterations from spending large time/space or
implementation complexity for tiny recall/QPS gains.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `EXPERIMENTS.md`

### Hypothesis / plan

The current fixed-policy work is a local policy layer around SAQ, not an
independent quantizer. Future autonomous runs should therefore pass a
novelty/overhead gate before new expensive sweeps or candidate-family
expansion. Update root control files so this concern steers task selection and
stop criteria.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' AGENTS.md
sed -n '1,240p' TASK.md
sed -n '1,320p' EXPERIMENTS.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- `AGENTS.md`: added novelty/overhead gates, stop criteria, and known pitfalls.
- `TASK.md`: added novelty/overhead as a strategic constraint, primary success
  criterion, non-goal, and evidence rule.
- `EXPERIMENTS.md`: added A0 novelty/overhead gate, downgraded C1 until A0 is
  complete, and added D4 overhead cherry-picking audit.
- `RESULTS.md`: added overhead caveat and promoted novelty/overhead audit as
  the next stable result to seek.
- `PROGRESS.md`: added this session log.

### Artifacts produced

No generated experiment artifacts.

### Result

Future iterations must now account for SAQ failure mode, deployable overhead,
and contribution strength before launching new expensive plan searches or
presenting small recall/QPS deltas as progress.

### Interpretation

This directly addresses the current concern that the project may otherwise
optimize local metric gains without enough novelty or practical benefit.

### Problems / blockers

None.

### Next action

Validate the diff, commit, and push. The next substantive task should be A0:
write the novelty/overhead audit before starting new experiments.

## Session 2026-07-07 21:00 HKT

### Goal

Complete A0: write a novelty/overhead audit for the current query-unaware
default-neighborhood fixed-policy method before starting more expensive
experiments.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short`: clean
- A0 in `EXPERIMENTS.md` was `todo`.
- `TASK.md` required novelty and overhead accounting before new expensive
  build/eval sweeps.

### Hypothesis / plan

The current method is not an independent quantizer. The useful contribution,
if any, must be framed as a low-overhead query-unaware correction for a
specific SAQ limitation: the default global variance-based planner does not
directly model IVF-local ranking-boundary risk or segment-shape search cost.

Write a durable audit that separates deployable method overhead from research
sweep overhead, states stop/pivot criteria, and identifies the next required
overhead measurements.

### Commands run

```bash
sed -n '1,80p' docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
sed -n '1,220p' TASK.md
sed -n '1,260p' EXPERIMENTS.md
sed -n '1,220p' RESULTS.md
git status --short
sed -n '1,240p' AGENTS.md
sed -n '1,260p' docs/saq_fixed_policy_method_spec_2026_07_07.md
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
sed -n '260,520p' docs/saq_fixed_policy_method_spec_2026_07_07.md
rg -n "max_anchors|max_pairs|max_candidates_per_anchor|boundary_rank|neighbor_window|pairs_per_anchor|pair_seed|allow_risky|frontier|conservative" script/run_default_neighborhood_cross_dataset.py
sed -n '1,260p' script/sweep_data_boundary_pairs.py
rg -n "def gen_|generators =|def generate_candidates|filter_infeasible|max_segments|min_positive_bits|families" script/generate_default_neighborhood_plans.py
sed -n '260,420p' script/sweep_data_boundary_pairs.py
sed -n '40,70p' script/run_default_neighborhood_cross_dataset.py
sed -n '325,390p' script/generate_default_neighborhood_plans.py
sed -n '395,455p' script/run_default_neighborhood_cross_dataset.py
ls -lh /tmp/saq-run/reports | tail -40
rg -n "candidate_count|generated|sampled_pair_count|used_anchor_count|scorer|boundary" /tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json /tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json
find /tmp/saq-run/reports -maxdepth 1 -type f -name '*default_neighborhood*2026_07_06*json' -o -name '*default_neighborhood*2026_07_07*json' | head -40
python -c 'import json; from pathlib import Path; data=json.loads(Path("/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json").read_text()); print(data.keys());\nfor k,v in data.items(): print(k, type(v).__name__, (len(v) if hasattr(v,"__len__") else ""))'
python -c 'import json; from pathlib import Path; data=json.loads(Path("/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json").read_text()); print(data.keys());\nfor k,v in data.items(): print(k, type(v).__name__, (len(v) if hasattr(v,"__len__") else ""))'
python -c 'import json; from pathlib import Path; data=json.loads(Path("/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json").read_text()); r=data["results"][0]; print(r.keys());\nfor k,v in r.items(): print("KEY",k,"TYPE",type(v).__name__); print(str(v)[:500])'
python -c 'import csv,json; from pathlib import Path; data=json.loads(Path("/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json").read_text());\nfor r in data["results"]:\n    name=r["spec"]["name"];\n    cand_csv=Path(r.get("candidate_csv","")); uniq=Path(r.get("unique_csv",""));\n    cand_rows=sum(1 for _ in csv.DictReader(cand_csv.open())) if cand_csv.exists() else None;\n    uniq_rows=sum(1 for _ in csv.DictReader(uniq.open())) if uniq.exists() else None;\n    summary=Path(str(uniq).replace(".unique.csv",".summary.json"));\n    s=json.loads(summary.read_text()) if summary.exists() else {};\n    sample=s.get("pair_summary") or s.get("sampling") or s.get("boundary_pair_summary") or {};\n    top=(r.get("top_unique") or [{}])[0];\n    print(name, "candidate_rows", cand_rows, "unique_rows", uniq_rows, "top_config_count", top.get("config_count"), "pairs", sample.get("sampled_pair_count"), "anchors", sample.get("used_anchor_count"), "summary", summary.name if summary.exists() else "missing")'
tail -120 PROGRESS.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added
  `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`.
- Updated `EXPERIMENTS.md`: marked A0 and D4 done with the audit doc as
  result.
- Updated `RESULTS.md`: added a stable claim that the current method is a local
  correction layer and made overhead measurement the next stable result.
- Updated `PROGRESS.md`: added this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md
```

### Result

The audit concludes that the current work is only defensible as an incremental,
shape-dependent, query-unaware SAQ correction. It should not be presented as a
strictly better quantizer. The main deployable overhead is data-only
boundary-pair sampling/scoring; research validation overhead from many
candidate builds/evaluations must be reported separately.

### Interpretation

This satisfies A0 as a documentation and decision gate. It does not authorize
unbounded new sweeps. The next stable technical result should measure overhead
for the existing fixed-policy cases: candidate count, scorer runtime, pair
count, final index build time, index size, and QPS curves.

### Problems / blockers

No blocker. Exact wall-clock scorer runtime and index-size/build-time overhead
are not yet measured; the audit marks them as required next measurements rather
than guessing.

### Next action

Validate the markdown diff, commit, and push.

## Session 2026-07-07 21:07 HKT

### Goal

Add a durable terminology constraint before the next research step: use
research-paper terminology in new non-code project materials.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- User requested a constraint preferring "review", "analyze", "evaluate",
  "survey", and "limitations" over software-maintenance terms unless discussing
  code.

### Work completed

Added the terminology constraint to the current iteration control files:

- `AGENTS.md`
- `TASK.md`
- `EXPERIMENTS.md`

Also updated a few forward-looking headings in `TASK.md` and `EXPERIMENTS.md`
from maintenance-style wording to research-paper wording. Existing artifact
paths and historical result references were intentionally left unchanged to
avoid breaking references.

### Commands run

```bash
git status --short --branch
sed -n '1,220p' AGENTS.md
sed -n '1,180p' TASK.md
sed -n '1,120p' EXPERIMENTS.md
rg -n "audit|harden|triage|patch|hardening|audits" AGENTS.md TASK.md EXPERIMENTS.md
date '+%Y-%m-%d %H:%M %Z'
tail -80 PROGRESS.md
```

### Files changed

- `AGENTS.md`: added durable research-paper terminology guidance.
- `TASK.md`: added the same constraint and changed active/future-facing
  wording to "develop and evaluate", "evaluation", and "review".
- `EXPERIMENTS.md`: added the terminology rule and changed several
  future-facing labels to "evaluate" or "review".
- `PROGRESS.md`: added this session log.

### Result

Future docs, slides, summaries, and task descriptions should use research-paper
language by default. Maintenance-style terms remain acceptable for code
correctness, debugging, repository maintenance, and existing artifact paths.

### Next action

Validate diff, commit, and push this constraint update before continuing with
the next research step.

## Session 2026-07-07 21:37 HKT

### Goal

Evaluate fixed-policy overhead terms requested for the next step: candidate
runtime, scorer runtime, pair count, index build time, index size, and QPS
curve.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Required direction: use research-paper terminology and avoid presenting the
  method as a strict SAQ replacement without overhead accounting.

### Work completed

Added `script/report_fixed_policy_overhead.py`, a reproducible report driver
that:

- reads `/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json`;
- aggregates candidate counts, pair counts, scorer grid sizes, index metadata,
  index sizes, and QPS curve rows;
- optionally measures fresh candidate/scorer runtime;
- optionally fills missing QPS curve points with corrected safe search
  (`-searcher_safe_block_min_mode=2`).

Ran the driver with both measurement options:

```bash
python -m py_compile script/report_fixed_policy_overhead.py
python script/report_fixed_policy_overhead.py \
  --measure-planner-runtime \
  --measure-qps-curve \
  --output-prefix docs/saq_fixed_policy_overhead_evaluation_2026_07_07
```

### Files changed

- Added `script/report_fixed_policy_overhead.py`.
- Added `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md`.
- Added `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv`.
- Added `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.qps_curve.csv`.
- Added `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.json`.
- Updated `EXPERIMENTS.md` with A4 fixed-policy overhead evaluation.
- Updated `RESULTS.md` with the stable overhead finding.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.qps_curve.csv
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_overhead_timing_2026_07_07/
```

### Result

The overhead evaluation is complete for the current fixed-policy matrix.

Key measured values:

- full GIST K4096 planner runtime: about 145-151 seconds per budget;
- CIFAR60K planner runtime: about 8.5-8.6 seconds per budget;
- DEEP100K sample planner runtime: about 5.8 seconds per budget;
- full GIST pair count: 14,740 pairs from 3,685 anchors;
- QPS curve rows: 43 total rows, with no missing default/custom QPS values for
  selected-candidate rows.

### Interpretation

The main added deployable cost is the data-only scorer, not candidate
generation or final index build. This makes scorer-cost reduction and sampling
calibration a higher-value next direction than expanding candidate families.

### Problems / limitations

Index build time is read from existing `create_index` metadata rather than
newly repeated in this run. Planner runtime is a single wall-clock measurement
and includes Python startup, file I/O, boundary-pair sampling, and scorer-grid
evaluation.

### Next action

Validate generated docs and script, then commit and push. The next research
step should evaluate whether fewer anchors/pairs or a smaller scorer grid can
preserve the same fixed-policy decisions.

## Session 2026-07-07 22:46 HKT

### Goal

Evaluate scorer-cost reduction and sampling calibration for the current
fixed-policy matrix.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean except new scorer-calibration work from
  the active session
- Files read:
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `PROGRESS.md`
  - `AGENTS.md`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv`

### Hypothesis / plan

The data-only scorer may be calibrated to use fewer sampled boundary pairs
while preserving the current fixed-policy decisions. If pair-count reduction
does not materially reduce wall-clock runtime, the next overhead-reduction
target should shift to cached residual/tail features or scorer-grid reduction.

### Commands run

```bash
python -m py_compile script/run_scorer_calibration.py
python script/run_scorer_calibration.py \
  --run cifar60k_B4 \
  --preset a256_p1 \
  --output-prefix /tmp/saq-run/reports/scorer_calibration_smoke_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --run cifar60k_B4 \
  --run deep1M_sample100k_B4 \
  --run audio_K4096_B4 \
  --preset a256_p1 \
  --preset a512_p1 \
  --preset a1024_p2 \
  --force \
  --output-prefix docs/saq_fixed_policy_scorer_calibration_2026_07_07
python script/run_scorer_calibration.py \
  --preset a1024_p2 \
  --force \
  --output-prefix docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --run cifar60k_B4 \
  --run deep1M_sample100k_B4 \
  --run audio_K4096_B4 \
  --preset a256_p1 \
  --preset a512_p1 \
  --preset a1024_p2 \
  --output-prefix docs/saq_fixed_policy_scorer_calibration_2026_07_07
python script/run_scorer_calibration.py \
  --preset a1024_p2 \
  --output-prefix docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07
```

### Files changed

- Added `script/run_scorer_calibration.py`.
- Added calibration reports under `docs/`.
- Updated `EXPERIMENTS.md` with A5.
- Updated `RESULTS.md` with the stable scorer-calibration conclusion.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_scorer_calibration_2026_07_07.md
docs/saq_fixed_policy_scorer_calibration_2026_07_07.csv
docs/saq_fixed_policy_scorer_calibration_2026_07_07.json
docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.md
docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.csv
docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.json
```

### Result

The `a1024_p2` scorer setting preserves all current fixed-policy decisions and
selected plans in the full matrix: 10/10 decision matches and 10/10 plan
matches. Total measured scorer runtime is 456.967 seconds.

Representative smaller settings preserve the decision but not always the exact
selected plan: `a256_p1` and `a512_p1` both select a different GIST B=4 plan.

### Interpretation

Pair-count reduction alone is not enough. On GIST, `a1024_p2` reduces sampled
pairs from 14,740 to 2,048, but runtime remains around 94-95% of the previous
full-scorer runtime. The next cost-reduction study should evaluate cached
residual/tail features or a smaller scoring grid before adding new candidate
families.

### Problems / limitations

No blocker. This run evaluates scorer calibration only; it does not rerun
recall/QPS because selected plans intentionally remain the same as the current
fixed-policy matrix.

### Next action

Run validation, commit, and push. Then evaluate cached residual/tail feature
reuse or scoring-grid reduction as the next overhead-reduction step.

## Session 2026-07-07 23:27 HKT

### Goal

Evaluate cached residual/tail scorer features and scorer-grid reduction as
overhead reductions for the current fixed-policy scorer.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.md`
  - scorer implementation files under `script/`

### Hypothesis / plan

Pair-count reduction did not materially reduce full-GIST scorer runtime, so
the remaining cost might be residual/tail feature computation or scorer-grid
enumeration. Implement the smallest safe cost reductions and evaluate them
against exact fixed-policy decision and selected-plan stability.

### Commands run

```bash
python -m py_compile script/score_default_neighborhood_plans.py script/run_scorer_calibration.py
python script/run_scorer_calibration.py \
  --run cifar60k_B4 \
  --preset a1024_p2_grid_endpoints \
  --force \
  --output-prefix /tmp/saq-run/reports/scorer_grid_smoke_cifar_b4_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --preset a1024_p2_grid_endpoints \
  --force \
  --output-prefix /tmp/saq-run/reports/scorer_grid_smoke_gist_b4_endpoints_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --preset a1024_p2 \
  --force \
  --output-prefix /tmp/saq-run/reports/scorer_cache_smoke_gist_b4_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --preset a1024_p2_grid_endpoints_cached_features \
  --force \
  --output-prefix /tmp/saq-run/reports/scorer_feature_cache_gist_b4_first_2026_07_07
python script/run_scorer_calibration.py \
  --run gist_full_K4096_B4 \
  --preset a1024_p2_grid_endpoints_cached_features \
  --force \
  --output-prefix /tmp/saq-run/reports/scorer_feature_cache_gist_b4_second_2026_07_07
python script/run_scorer_calibration.py \
  --preset a1024_p2_grid_endpoints_cached_features \
  --force \
  --feature-cache-dir /tmp/saq-run/reports/fixed_policy_scorer_feature_cache_cold_2026_07_07 \
  --output-prefix docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07
python script/run_scorer_calibration.py \
  --preset a1024_p2_grid_endpoints_cached_features \
  --force \
  --feature-cache-dir /tmp/saq-run/reports/fixed_policy_scorer_feature_cache_cold_2026_07_07 \
  --output-prefix docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07
```

### Files changed

- `script/score_default_neighborhood_plans.py`
  - added plan-level pair/speed/static metric caching;
  - added optional feature-cache support for residual risk, tail risk, and
    boundary-pair arrays;
  - added phase timings and cache metadata to summary JSON.
- `script/run_scorer_calibration.py`
  - added endpoint-grid and cached-feature presets;
  - added feature-cache override support;
  - added config-count ratios, cache status, and phase timings to reports.
- Added cold-cache and warm-cache scorer cost-reduction reports under `docs/`.
- Updated `EXPERIMENTS.md` and `RESULTS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.md
docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.csv
docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.json
docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.md
docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.csv
docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_scorer_feature_cache_cold_2026_07_07/
```

### Result

The combined endpoint-grid plus cached-feature setting preserves the current
fixed-policy matrix exactly:

```text
cold cache: decision 10/10, plan 10/10, runtime 147.082 s
warm cache: decision 10/10, plan 10/10, runtime   5.656 s
reference scorer runtime from overhead table:     481.764 s
```

The cold-cache phase timing shows the main cost source:

```text
residual-risk time:        111.166 s
tail-risk time:             28.985 s
boundary-pair sampling:      1.251 s
scoring-grid enumeration:    0.058 s
```

### Interpretation

The endpoint grid reduces config count to about 0.5% of the previous grid and
preserves current decisions/plans, but it is not the GIST runtime bottleneck.
The main practical reduction comes from caching data-only residual/tail/pair
features across B values for the same dataset/K/sampling setting.

This should be presented as overhead reduction for the fixed-policy scorer,
not as a new SAQ quantizer or independent algorithmic contribution.

### Problems / limitations

The cache is a local `/tmp` artifact and is not checked into git. It is keyed by
dataset path, IVF K, padded dimension, sampling parameters, residual-risk
statistic, and tail-risk quantile. New datasets or changed sampling settings
still require a cold feature computation.

### Next action

Validate scripts and reports, then commit and push. The next research step
should decide whether cached-feature scoring should become the default runner
path, or whether the remaining work should shift back to meeting/paper
narrative and clean reproducibility instructions.

## Session 2026-07-07 23:52 HKT

### Goal

Integrate the feature-cache and endpoint-grid scorer path into the official
fixed-policy runners.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `script/run_default_neighborhood_cross_dataset.py`
  - `script/run_fixed_policy_matrix.py`
  - `script/score_default_neighborhood_plans.py`
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`

### Hypothesis / plan

The cost-reduced scorer should be exposed through the same fixed-policy runner
used for the rest of the evidence. The integration should preserve old default
behavior unless explicitly enabled, use distinct scorer artifact prefixes, and
verify exact scorer/selection equivalence against the checked-in clean table.

### Commands run

```bash
python -m py_compile \
  script/run_default_neighborhood_cross_dataset.py \
  script/run_fixed_policy_matrix.py \
  script/score_default_neighborhood_plans.py
python script/run_fixed_policy_matrix.py \
  --skip-scan \
  --skip-report \
  --no-evaluate \
  --use-cost-reduced-scorer \
  --date 2026_07_07_runner_cost_reduced_dry \
  --artifact-date 2026_07_07_runner_cost_reduced_dry \
  --dry-run
python script/run_fixed_policy_matrix.py \
  --skip-scan \
  --skip-report \
  --no-evaluate \
  --force \
  --use-cost-reduced-scorer \
  --date 2026_07_07_runner_cost_reduced \
  --artifact-date 2026_07_07_runner_cost_reduced
python - <<'PY'
import csv
base=list(csv.DictReader(open('docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv')))
base_by_run={r['run']:r for r in base}
rows=list(csv.DictReader(open('/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.csv')))
ok=0
for r in rows:
    b=base_by_run[r['run']]
    decision='abstain' if not r['candidate_plan'] else ('reject' if r['selection_reason']=='risky_fallback_best_score' else 'promote')
    ok += decision==b['policy_decision'] and r['candidate_plan']==b['selected_or_tested_plan']
assert ok==len(rows)
PY
```

### Files changed

- `script/run_default_neighborhood_cross_dataset.py`
  - added `--use-cost-reduced-scorer`, `--scorer-grid-preset`, and
    `--feature-cache-dir`;
  - added endpoint-grid scorer arguments;
  - added distinct scorer artifact suffixes for endpoint/cache runs;
  - recorded scorer mode/cache path in summary CSV/JSON.
- `script/run_fixed_policy_matrix.py`
  - added forwarding options for the cost-reduced scorer;
  - normalized `--use-cost-reduced-scorer` to endpoint grid plus a default
    feature-cache directory.
- `docs/saq_fixed_policy_method_spec_2026_07_07.md`
  - documented official runner options and the selection-only verification.
- Added `docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md`.
- Updated `EXPERIMENTS.md`, `RESULTS.md`, and `PROGRESS.md`.

### Artifacts produced

```text
docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07_runner_cost_reduced.manifest.json
/tmp/saq-run/reports/fixed_policy_scorer_feature_cache_2026_07_07_runner_cost_reduced/
```

### Result

The official matrix runner with `--use-cost-reduced-scorer` reproduced the
checked-in clean table's scorer decisions and selected/tested plans:

```text
decision match: 10/10
plan match:     10/10
```

The verification was scorer/selection-only and used `--no-evaluate`.

### Interpretation

The feature-cache and endpoint-grid scorer path is now part of the formal
fixed-policy runner interface. It remains an implementation-level overhead
reduction, not a new SAQ quantizer or independent algorithmic contribution.

The official integration keeps each run's sampling parameters unchanged. The
separate `a1024_p2` sampling calibration remains documented but is not promoted
to default behavior in the formal runner.

### Problems / limitations

The run did not rerun safe-search recall/QPS. If we need a fully refreshed
paper-style result table, rerun the same matrix with evaluation enabled and
corrected safe search.

### Next action

Validate full diff, commit, and push. Then decide whether to run a full
cost-reduced scorer + safe-search evaluation matrix or move to meeting/paper
narrative cleanup.

## Session 2026-07-08 00:16 HKT

### Goal

Run the formal fixed-policy matrix evaluation using the integrated
cost-reduced scorer and safe-search recall/QPS evaluation.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `TASK.md`
  - `RESULTS.md`
  - `PROGRESS.md`
  - `EXPERIMENTS.md`
  - `docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md`

### Hypothesis / plan

The official runner should reproduce the checked-in clean validation table
when using `--use-cost-reduced-scorer` with evaluation enabled. This checks the
formal runner path rather than only the scorer calibration or selection-only
path.

### Commands run

```bash
git status --short --branch
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
python script/run_fixed_policy_matrix.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
sed -n '1,220p' /tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.md
sed -n '1,220p' /tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json
```

### Files changed

- Added
  `docs/saq_fixed_policy_runner_cost_reduced_full_eval_2026_07_08.md`.
- Updated `EXPERIMENTS.md` with A8.
- Updated `RESULTS.md` with the stable full-evaluation result.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_08_runner_cost_reduced_eval.json
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.md
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json
/tmp/saq-run/reports/fixed_policy_scorer_feature_cache_2026_07_08_runner_cost_reduced_eval/
```

### Result

The formal runner matched the checked-in clean validation table:

```text
Expected table matches: docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
Decision counts: {'promote': 6, 'reject': 2, 'abstain': 2}
```

The generated clean table preserves the current evidence:

- GIST full K4096 B=3/B=4/B=5 promote with the existing selected plans and
  positive R@100/QPS ratios.
- CIFAR60K B=3/B=4/B=5 promote with the existing selected plans and small
  positive R@10/QPS ratios.
- DEEP100K B=4/B=5 remain reject cases because measured recall drops despite
  QPS gains.
- audio and word2vec remain abstention cases.

### Interpretation

This upgrades the cost-reduced scorer runner evidence from selection-only to
full fixed-policy matrix evaluation evidence. The result is still a
reproducibility and scorer-execution result, not a new quantization method.

### Problems / blockers

The run reused matching safe QPS artifacts where present. The local artifacts
remain under `/tmp/saq-run` and are not durable unless summarized in checked-in
docs.

### Next action

Commit and push the durable documentation updates, then focus on clean-machine
reproducibility or a concise meeting update rather than additional tuning
sweeps.

## Session 2026-07-08 00:42 HKT

### Goal

Complete a clean-root reproducibility and artifact-dependency review for the
current fixed-policy matrix.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `RESULTS.md`
  - `script/run_fixed_policy_matrix.py`
  - `script/run_default_neighborhood_cross_dataset.py`
  - `script/report_fixed_policy_validation.py`
  - `script/score_default_neighborhood_plans.py`
  - `docs/saq_fixed_policy_runner_cost_reduced_full_eval_2026_07_08.md`
  - `docs/saq_fixed_policy_method_spec_2026_07_07.md`

### Hypothesis / plan

The current evidence has already been reproduced on this machine, but the
remaining reproducibility risk is artifact provenance. Review which files must
exist before the runner starts and which files can be regenerated by the
fixed-policy pipeline. Add a lightweight checker so a future clean root can
report missing prerequisites before launching an expensive run.

### Commands run

```bash
git status --short --branch
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
rg -n "REUSE|build|index|qps|compare|groundtruth|pca|feature_cache|feature-cache|data-root|root" script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/score_default_neighborhood_plans.py script/report_fixed_policy_validation.py
sed -n '300,760p' script/run_default_neighborhood_cross_dataset.py
sed -n '240,330p' script/run_fixed_policy_matrix.py
sed -n '315,430p' script/score_default_neighborhood_plans.py
sed -n '1,220p' /tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json
python -m py_compile script/check_fixed_policy_artifacts.py
python script/check_fixed_policy_artifacts.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --output-json /tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.json \
  >/tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.txt
python - <<'PY'
import json
d=json.load(open('/tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.json'))
print(d['counts'])
print('missing', sum(1 for a in d['artifacts'] if not a['exists']))
print('total', len(d['artifacts']))
PY
```

### Files changed

- Added `script/check_fixed_policy_artifacts.py`.
- Added
  `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`.
- Updated `EXPERIMENTS.md` with A9.
- Updated `RESULTS.md` with the stable artifact-dependency result.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
/tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.txt
/tmp/saq-run/reports/fixed_policy_artifact_dependency_check_2026_07_08.json
```

### Result

The checker reports that the current local root has all enumerated artifacts:

```text
build:             3/3 present
input:            23/23 present
runner-generated: 135/135 present
cache:             1/1 present
report:            4/4 present
missing:           0
```

The clean-root prerequisite boundary is now explicit:

- build artifacts are required for full evaluation;
- dataset/PCA/IVF inputs must be prepared before the runner starts;
- candidate/scorer/index/compare/QPS/report artifacts can be regenerated by
  the runner if the build and input artifacts exist;
- the cost-reduced feature cache is optional and can be recomputed.

### Interpretation

The remaining clean-machine gap is data preparation provenance rather than
fixed-policy runner logic. The runner can regenerate the fixed-policy artifacts
from build and input prerequisites, but it does not provide a one-command full
dataset preparation pipeline.

### Problems / blockers

The checker verifies existence only. It does not yet verify hashes,
groundtruth depth, PCA provenance, or artifact commit provenance.

### Next action

Commit and push this reproducibility review. The next useful step is to
document exact dataset preparation/source paths or add hashes for the required
input artifacts.

## Session 2026-07-08 00:52 HKT

### Goal

Add an input-artifact provenance manifest and hash layer for the current
fixed-policy validation matrix.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `2c41baa Document fixed-policy artifact dependencies`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `PROGRESS.md`
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `script/check_fixed_policy_artifacts.py`
  - `script/segment_diagnostics.py`
  - `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`

### Hypothesis / plan

The fixed-policy runner already has a dependency checker that enumerates input
artifacts. Reuse that checker as the source of truth, deduplicate the input
paths, and write a durable manifest that records role, producer hint, file
size, xvecs shape, mtime, and full-file SHA256.

### Commands run

```bash
git status --short --branch
sed -n '1,220p' AGENTS.md
sed -n '1,260p' script/check_fixed_policy_artifacts.py
sed -n '1,140p' script/segment_diagnostics.py
sed -n '260,560p' script/check_fixed_policy_artifacts.py
sed -n '1,220p' TASK.md
sed -n '1,240p' PROGRESS.md
sed -n '1,240p' EXPERIMENTS.md
sed -n '1,240p' RESULTS.md
sed -n '240,420p' EXPERIMENTS.md
sed -n '240,520p' PROGRESS.md
sed -n '1,260p' docs/saq_fixed_policy_reproducibility_review_2026_07_08.md
rg -n "input manifest|provenance|hash|A9|A10|artifact" docs script *.md
python -m py_compile script/write_fixed_policy_input_manifest.py script/check_fixed_policy_artifacts.py
python script/write_fixed_policy_input_manifest.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --hash-mode full \
  --output-json docs/saq_fixed_policy_input_manifest_2026_07_08.json \
  --output-md docs/saq_fixed_policy_input_manifest_2026_07_08.md
python -c "import json; d=json.load(open('docs/saq_fixed_policy_input_manifest_2026_07_08.json')); print(d['summary']); print(d['files'][0]['path']); print(d['files'][0]['hash']['sha256'][:16])"
python -c "import json; d=json.load(open('docs/saq_fixed_policy_input_manifest_2026_07_08.json')); assert d['summary']['unique_input_files']==20; assert d['summary']['missing_unique_input_files']==0; assert d['summary']['xvecs_shape_errors']==0; assert all(f['hash']['status']=='ok' for f in d['files']); print(d['summary'])"
git diff --check
git status --short --branch
```

### Files changed

- Added `script/write_fixed_policy_input_manifest.py`.
- Added `docs/saq_fixed_policy_input_manifest_2026_07_08.md`.
- Added `docs/saq_fixed_policy_input_manifest_2026_07_08.json`.
- Updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`.
- Updated `EXPERIMENTS.md` with A10.
- Updated `RESULTS.md` with the stable input-manifest result.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_input_manifest_2026_07_08.md
docs/saq_fixed_policy_input_manifest_2026_07_08.json
```

### Result

The manifest writer generated a full-SHA256 input manifest for the current
fixed-policy matrix:

```text
input artifact entries:       23
unique input files:           20
present unique input files:   20
missing unique input files:    0
total input size:        3.822 GiB
xvecs shape errors:            0
```

Validation passed:

- `python -m py_compile script/write_fixed_policy_input_manifest.py script/check_fixed_policy_artifacts.py`
- JSON manifest summary/assertion check
- `git diff --check`

### Interpretation

The current prepared input substrate is now explicitly identifiable by
full-file SHA256. A future reproduction can first check these files, then let
the fixed-policy runner regenerate candidate, scorer, index, compare, QPS, and
report artifacts.

### Problems / blockers

The manifest records file identity, not raw preparation provenance. It still
does not explain the original dataset source paths, PCA training command, IVF
training command, or groundtruth generation command.

### Next action

Commit and push this provenance layer. The next reproducibility task is to
document exact source/preparation commands for the input files if that level of
clean-machine reconstruction is needed.

## Session 2026-07-08 01:23 HKT

### Goal

Document input source and preparation provenance for the fixed-policy matrix.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `bee3e38 Add fixed-policy input provenance manifest`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `docs/saq_fixed_policy_input_manifest_2026_07_08.md`
  - `script/prepare_sampled_pca_ivf.py`
  - `script/prepare_ivf_from_pca.py`
  - `python/pca.py`
  - `python/ivf.py`
  - `src/compute_gt.cpp`
  - existing GIST/CIFAR/DEEP/audio/word2vec notes under `docs/`
  - local summaries under `/tmp/saq-run/data/*/*summary.json`

### Hypothesis / plan

The manifest identifies the prepared inputs by hash, but meeting/paper
reproducibility also needs a source/preparation chain. Recover exact commands
where historical summaries and notes exist, and explicitly mark partial cases
instead of inventing missing commands.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' AGENTS.md
sed -n '1,220p' TASK.md
sed -n '1,220p' docs/saq_fixed_policy_input_manifest_2026_07_08.md
rg -n "gist_full|cifar60k|deep1M_sample100k|audio|word2vec_sample100k|prepare|groundtruth|base_pca|query_pca|centroid|cluster_id" docs script python README.md EXPERIMENTS.md RESULTS.md PROGRESS.md
rg --files script python src | sort
find /tmp/saq-run/data -maxdepth 2 -type f | sort
find /rwproject/kdd-db/kluaq/dataset -maxdepth 3 -type f | sort
sed -n '1,260p' python/pca.py
sed -n '1,260p' python/compute_gt.py
sed -n '1,360p' script/prepare_sampled_pca_ivf.py
sed -n '1,240p' script/prepare_ivf_from_pca.py
sed -n '1,240p' python/ivf.py
cat /tmp/saq-run/data/cifar60k/cifar60k_sampled_pca_ivf_summary.json
cat /tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_sampled_pca_ivf_summary.json
cat /tmp/saq-run/data/gist_full/gist_full_sampled_pca_ivf_summary.json
cat /tmp/saq-run/data/gist_full/gist_full_k4096_pca_ivf_summary.json
cat /tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_sampled_pca_ivf_summary.json
cat /tmp/saq-run/data/gist_full/gist_full_query_pca_summary.json
cat /tmp/saq-run/data/cifar60k/cifar60k_query_pca_summary.json
cat /tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_query_pca_summary.json
cat /tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_query_pca_summary.json
sed -n '1,180p' docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md
sed -n '1,90p' docs/saq_gist_full_k4096_official_style_validation_2026_07_04.md
sed -n '80,170p' docs/saq_gist_full_k512_safe_validation_2026_07_04.md
rg -n "groundtruth|top100|top10|official|original-space|original_l2|compute_groundtruth|compute_gt|groundtruth_l2|groundtruth_ip" docs script python PROGRESS.md RESULTS.md
sed -n '1,220p' src/compute_gt.cpp
sed -n '1,80p' docs/saq_cross_dataset_pilot_deep_cifar_2026_07_06.md
sed -n '300,360p' docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md
find /tmp/saq-run/data -maxdepth 2 -type l -ls | sort -k11
find /tmp/saq-run/data/gist_raw -maxdepth 1 -type f,l -printf '%p -> %l\n'
rg -n "audio.*PCA|audio_base_pca|audio.*groundtruth|audio.*centroid|audio.*ivf|python.*pca.*audio|compute_gt.*audio|audio_K4096" docs PROGRESS.md RESULTS.md EXPERIMENTS.md script python
find /tmp/saq-run/data/audio -maxdepth 1 -type f,l -printf '%TY-%Tm-%Td %TH:%TM %s %p -> %l\n' | sort
python - <<'PY'
from pathlib import Path
import hashlib

def xshape(path):
    p = Path(path)
    with p.open("rb") as f:
        dim = int.from_bytes(f.read(4), "little", signed=True)
    row = 4 + 4 * dim
    return p.stat().st_size // row, dim, p.stat().st_size

def h(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()[:16]

for p in [
    "/rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs",
    "/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs",
    "/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs",
    "/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs",
    "/tmp/saq-run/data/cifar60k/cifar60k_groundtruth.ivecs",
    "/rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_base.fvecs",
    "/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_groundtruth.ivecs",
    "/rwproject/kdd-db/kluaq/dataset/audio/audio_base.fvecs",
    "/tmp/saq-run/data/audio/audio_base_pca.vars.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_base.fvecs",
    "/tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_groundtruth.ivecs",
]:
    print("\t".join([p, str(xshape(p)), h(p)]))
PY
python - <<'PY'
import hashlib

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

for a, b in [
    ("/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs", "/tmp/saq-run/data/cifar60k/cifar60k_groundtruth.ivecs"),
    ("/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs", "/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs"),
    ("/tmp/saq-run/data/gist_full/gist_full_groundtruth_before_original_top100_switch.ivecs", "/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100.ivecs"),
]:
    print(a, b, digest(a) == digest(b), digest(a)[:16], digest(b)[:16])
PY
python - <<'PY'
from pathlib import Path
import hashlib

def xshape(path):
    p = Path(path)
    with p.open("rb") as f:
        dim = int.from_bytes(f.read(4), "little", signed=True)
    row = 4 + 4 * dim
    return p.stat().st_size // row, dim, p.stat().st_size

def h(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()[:16]

for p in [
    "/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_base.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_query.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs",
    "/rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_query.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/audio/audio_query.fvecs",
    "/rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_query.fvecs",
]:
    print("\t".join([p, str(xshape(p)), h(p)]))
PY
```

### Files changed

- Added
  `docs/saq_fixed_policy_input_preparation_provenance_2026_07_08.md`.
- Updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`.
- Updated `EXPERIMENTS.md` with A11.
- Updated `RESULTS.md` with the stable preparation-provenance result.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_input_preparation_provenance_2026_07_08.md
```

### Result

The evaluated rows now have documented preparation provenance:

```text
GIST full K4096:   PCA + K4096 IVF + original-space top100 GT commands
CIFAR60K K512:     PCA + K512 IVF + copied L2 top10 GT command
DEEP100K K512:     sampled PCA + K512 IVF + sample-specific top100 GT command
```

Audio and word2vec are documented as partial provenance cases. This is
acceptable for the current matrix because they are abstention-only rows and the
policy only uses their PCA-variance artifacts.

### Interpretation

The previous source/preparation gap is narrowed from "unknown input origin" to
"not yet packaged as one command." For meeting discussion, the current evidence
can be described as reproducible from documented source paths and commands for
the evaluated rows, with clearly stated partial provenance for abstention-only
rows.

### Problems / blockers

The exact historical audio preprocessing command was not found. The exact
historical word2vec GT command was also not found, but that GT is not part of
the current manifest because the word2vec row abstains before evaluation.

### Next action

Commit and push this provenance documentation. If clean-machine reproduction
becomes a target, the next step is to convert the documented commands into a
single preparation driver or archive the prepared input bundle with manifest
hashes.

## Session 2026-07-08 10:08 HKT

### Goal

Implement a one-command input preparation and verification driver so the input
provenance layer is executable rather than only documented.

### Starting state

- Branch: `saq-boundary-audit`
- Previous checkpoint: `79b3886 Document fixed-policy input preparation provenance`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `docs/saq_fixed_policy_input_preparation_provenance_2026_07_08.md`
  - `script/write_fixed_policy_input_manifest.py`
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`

### Hypothesis / plan

The preparation provenance note should become a structured driver with three
safe modes:

1. `--verify-only`: check the current root against the full-SHA256 manifest.
2. `--dry-run`: print source/preparation commands without running them.
3. `--prepare --dataset ...`: execute only selected supported dataset
   preparation, with guards for large GIST/all-supported rebuilds.

Audio should remain manifest-verifiable but clean-preparation-unsupported
because the exact historical PCA/IVF command was not recovered.

### Commands run

```bash
git status --short --branch
sed -n '1,220p' AGENTS.md
sed -n '1,220p' TASK.md
sed -n '1,220p' docs/saq_fixed_policy_input_preparation_provenance_2026_07_08.md
sed -n '1,260p' script/write_fixed_policy_input_manifest.py
python -m py_compile script/prepare_fixed_policy_inputs.py script/write_fixed_policy_input_manifest.py
python script/prepare_fixed_policy_inputs.py --dry-run --dataset cifar60k
python script/prepare_fixed_policy_inputs.py --dry-run --dataset audio
python script/prepare_fixed_policy_inputs.py \
  --verify-only \
  --output-json /tmp/saq-run/reports/fixed_policy_input_verify_2026_07_08.json
python script/prepare_fixed_policy_inputs.py --dry-run
sed -n '230,330p' EXPERIMENTS.md
sed -n '90,240p' RESULTS.md
tail -n 120 PROGRESS.md
sed -n '250,320p' docs/saq_fixed_policy_reproducibility_review_2026_07_08.md
```

### Files changed

- Added `script/prepare_fixed_policy_inputs.py`.
- Added `docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md`.
- Updated `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`.
- Updated `EXPERIMENTS.md` with A12.
- Updated `RESULTS.md` with the stable executable-driver result.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
/tmp/saq-run/reports/fixed_policy_input_verify_2026_07_08.json
docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md
```

### Result

The new driver supports:

```bash
python script/prepare_fixed_policy_inputs.py --verify-only
python script/prepare_fixed_policy_inputs.py --dry-run
python script/prepare_fixed_policy_inputs.py --prepare --dataset cifar60k
python script/prepare_fixed_policy_inputs.py --prepare --dataset deep1M_sample100k
python script/prepare_fixed_policy_inputs.py --prepare --dataset word2vec_sample100k
python script/prepare_fixed_policy_inputs.py --prepare --dataset gist_full --allow-large
```

Current full verification result:

```text
matched=20
missing=0
mismatch=0
total=20
```

### Interpretation

The input layer now has an executable verification/preparation interface. The
remaining clean-machine gap is to run the driver on a fresh experiment root or
archive the manifest-matching input bundle. Audio remains a partial case:
current abstention reproduction is covered by manifest verification, but clean
audio preprocessing still needs the exact historical command or an archived
artifact.

### Problems / blockers

No blocker for the driver. Full preparation was not executed in this session to
avoid overwriting or rerunning expensive input generation on the current root.

### Next action

Commit and push this driver. The next useful reproducibility step is a fresh
root dry-run/verification exercise, or an archived input-bundle plan if a paper
artifact is the target.

## Session 2026-07-08 10:27 HKT

### Goal

Evaluate whether the fixed-policy meeting summary and slides need an update
after the latest reproducibility/provenance progress, and update them while
preserving the existing narrative style.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `RESULTS.md`
  - `docs/saq_fixed_policy_meeting_summary_2026_07_07.md`
  - `docs/saq_fixed_policy_meeting_slides_2026_07_07.md`
  - `docs/saq_fixed_policy_reproducibility_review_2026_07_08.md`
  - `docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md`

### Hypothesis / plan

The experimental evidence table does not need to change, but the meeting
materials should be updated because the previous draft still described the
artifact story as under-packaged. The updated version should keep the 2026-07-07
method narrative and add the 2026-07-08 reproducibility/provenance state,
top-conference contribution target, and novelty/overhead caution.

### Commands run

```bash
git status --short --branch
find docs -maxdepth 1 -type f \( -name '*meeting*summary*' -o -name '*meeting*slides*' -o -name '*slides*' -o -name '*summary*' \) | sort
rg -n "^(#|##|###|Slide|## Slide|# Slide)|Headline:|headline|reproduc|provenance|driver|artifact|SIGMOD|VLDB|ICDE|novelty|overhead|limitation|Next" docs/saq_fixed_policy_meeting_summary_2026_07_07.md docs/saq_fixed_policy_meeting_slides_2026_07_07.md docs/saq_fixed_policy_reproducibility_review_2026_07_08.md docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md
sed -n '1,220p' docs/saq_fixed_policy_meeting_summary_2026_07_07.md
sed -n '1,120p' docs/saq_fixed_policy_meeting_slides_2026_07_07.md
sed -n '720,900p' docs/saq_fixed_policy_meeting_slides_2026_07_07.md
sed -n '1,220p' AGENTS.md
sed -n '1,220p' TASK.md
sed -n '1,520p' RESULTS.md
cp docs/saq_fixed_policy_meeting_summary_2026_07_07.md docs/saq_fixed_policy_meeting_summary_2026_07_08.md
cp docs/saq_fixed_policy_meeting_slides_2026_07_07.md docs/saq_fixed_policy_meeting_slides_2026_07_08.md
rg -n "clean-machine|auditable|audit|harden|triage|patch|2026-07-07|Date: 2026-07-07|docs/saq_fixed_policy_meeting_summary_2026_07_07" docs/saq_fixed_policy_meeting_summary_2026_07_08.md docs/saq_fixed_policy_meeting_slides_2026_07_08.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_fixed_policy_meeting_summary_2026_07_08.md`.
- Added `docs/saq_fixed_policy_meeting_slides_2026_07_08.md`.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_fixed_policy_meeting_summary_2026_07_08.md
docs/saq_fixed_policy_meeting_slides_2026_07_08.md
```

### Result

The meeting materials do need an update. The 2026-07-08 versions keep the
existing method/evidence narrative, but add:

- the explicit SIGMOD/VLDB/ICDE-level contribution target;
- the novelty/overhead caution that the method is still a policy layer around
  SAQ rather than an independent quantizer;
- the full-SHA256 input manifest, preparation provenance, and executable
  preparation/verification driver;
- the current verification readout `matched=20 missing=0 mismatch=0 total=20`;
- updated limitations and meeting questions centered on fresh-root
  verification, artifact packaging, and the remaining contribution gap.

### Interpretation

The new meeting version should be used instead of the 2026-07-07 draft. The
evidence table remains unchanged, so the update should be presented as a
clearer and more reproducible meeting narrative rather than as a new empirical
result.

### Problems / blockers

No blocker. A fresh-root preparation/verification run has still not been
executed.

### Next action

Validate the markdown diff, then commit and push the updated meeting materials.

## Session 2026-07-08 11:21 HKT

### Goal

Update the long-term project constraints and the latest meeting slides according
to the new advisor-facing assessment: novelty is currently low-to-medium to
medium, the work is a strong meeting report / technical note, and a full
SIGMOD/VLDB/ICDE paper still needs a strengthened main contribution.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `AGENTS.md`
  - `TASK.md`
  - `EXPERIMENTS.md`
  - `RESULTS.md`
  - `docs/saq_fixed_policy_meeting_slides_2026_07_08.md`
  - `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md`
  - `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`

### Hypothesis / plan

The project should continue one more round, but future work should be gated by
an adversarial reviewer review before proposing new directions. The next
method-facing evidence should be scorer ablations and overhead justification,
not more candidate-family sweeps.

### Commands run

```bash
git status --short --branch
sed -n '1,260p' AGENTS.md
sed -n '1,260p' TASK.md
rg -n "novelty|overhead|adversarial|reviewer|SIGMOD|VLDB|ICDE|claim|QPS|curve|ablation|Recommended Next|What We Should Not|What We Can Claim|Open Research|Gap|contribution|unsafe|speed" docs/saq_fixed_policy_meeting_slides_2026_07_08.md docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md RESULTS.md EXPERIMENTS.md
sed -n '1,120p' docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md
sed -n '220,270p' docs/saq_fixed_policy_meeting_slides_2026_07_08.md
sed -n '700,945p' docs/saq_fixed_policy_meeting_slides_2026_07_08.md
sed -n '1,80p' EXPERIMENTS.md
sed -n '430,520p' EXPERIMENTS.md
rg -n "QPS is currently measured at one headline|add QPS curves|audit|harden|triage|patch|adversarial|strict reviewer|speed-only|random local|oracle|deployable overhead|experimental validation" AGENTS.md TASK.md docs/saq_fixed_policy_meeting_slides_2026_07_08.md
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- `AGENTS.md`: added the current paper-readiness assessment, adversarial
  reviewer review requirement, and deployable-vs-experimental overhead rule.
- `TASK.md`: added the same assessment as an active constraint and made scorer
  ablations a primary success criterion before more candidate-family sweeps.
- `EXPERIMENTS.md`: added A13, the boundary-risk scorer ablation package.
- `docs/saq_fixed_policy_meeting_slides_2026_07_08.md`: updated contribution
  framing, QPS/overhead caveats, unsafe claims, open questions, and next steps.
- `PROGRESS.md`: added this session log.

### Artifacts produced

No experiment artifacts were produced.

### Result

The durable guidance now requires a severe-reviewer-style review before new
directions. The slides now frame the current contribution as:

```text
Diagnosis: SAQ's variance-driven planner can be locally mismatched with
IVF-local ranking boundaries and segment-shape search cost.

Policy: a frozen query-unaware default-neighborhood policy promotes, rejects,
or abstains using only base/index artifacts.

Evidence: GIST/CIFAR positives, DEEP reject controls, and audio/word2vec
abstentions, under safe-search evaluation and overhead accounting.
```

The slides also reconcile the QPS-curve wording: the main evidence table uses
headline nprobe values, while the overhead report contains validation-grid QPS
curves; this does not justify claims over every production operating point.

### Interpretation

The next research step should be ablation evidence for the scorer and guards,
not another plan sweep. The main open question is whether the boundary-risk
scorer is safer than speed-only, random-local, guard-removed, or local-oracle
baselines at an acceptable overhead.

### Problems / blockers

No blocker. No ablation was run in this session.

### Next action

Validate the documentation diff, then commit and push. After that, the next
technical task should be A13: boundary-risk scorer ablation package.

## Session 2026-07-08 12:14 HKT

### Goal

Create a copy-ready GitHub issue draft for the newly discussed search-time
block-min bug and clarify whether other confirmed implementation bugs have
been found.

### Starting state

- Branch: `saq-boundary-audit`
- `git status --short --branch`: clean and aligned with
  `origin/saq-boundary-audit`
- Files read:
  - `docs/saq_upstream_1bit_segment_crash_issue_draft_2026_07_06.md`
  - `docs/saq_gist_sample100k_B5_block_min_root_cause_and_simd_safe_2026_07_04.md`
  - `docs/saq_gist_sample100k_B5_safe_block_min_ablation_2026_07_03.md`
  - `docs/saq_gist_sample100k_B5_pruning_trace_2026_07_03.md`
  - `RESULTS.md`
  - `TASK.md`
  - `AGENTS.md`
  - `codex_handoff.md`

### Hypothesis / plan

The safe block-min issue is independent from the already reported positive
1-bit segment build crash. Generate a separate issue body that states the
affected search path, reproduction/diagnostic case, observed NaN block-min
behavior, recall impact, expected behavior, and possible fix direction.

### Commands run

```bash
git status --short --branch
sed -n '1,220p' docs/saq_upstream_1bit_segment_crash_issue_draft_2026_07_06.md
sed -n '1,190p' docs/saq_gist_sample100k_B5_block_min_root_cause_and_simd_safe_2026_07_04.md
rg -n "segfault|crash|NaN|nan|bug|root cause|correctness|out-of-bounds|OOB|undefined|invalid lane|padded lane|issue" docs RESULTS.md TASK.md AGENTS.md codex_handoff.md
find docs -maxdepth 1 -type f | sort | rg "issue|1bit|block_min|safe|B3|segfault"
date '+%Y-%m-%d %H:%M %Z'
```

### Files changed

- Added `docs/saq_upstream_safe_block_min_issue_draft_2026_07_08.md`.
- Updated `PROGRESS.md` with this session log.

### Artifacts produced

```text
docs/saq_upstream_safe_block_min_issue_draft_2026_07_08.md
```

### Result

The new issue draft is copy-ready and describes the search-time bug:

```text
native AVX512 block-min includes padded/invalid lanes in partial search blocks;
NaN from padded lanes can make mi = NaN;
mi <= distk is then false;
the whole block is skipped before accurate refinement.
```

Confirmed implementation bugs found so far:

1. positive 1-bit segment build crash in `create_index`;
2. native multi-segment block-min padded-lane/NaN search bug.

Other observed issues are currently better classified as method limitations,
experiment artifacts, or unconfirmed numerical/order effects rather than
upstream bugs.

### Interpretation

The new draft should be posted as a separate upstream issue from the 1-bit
segment crash. It is about search/evaluation correctness, not index
construction.

### Problems / blockers

This session did not rerun the diagnostic on a clean upstream checkout. The
draft is based on the existing root-cause diagnostics and branch instrumentation.

### Next action

Commit and push the issue draft. If opening the upstream issue, mention that
the diagnostic binary was from an instrumented branch and the native reduction
pattern is the suspected upstream code path.

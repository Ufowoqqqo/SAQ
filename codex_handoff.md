# Codex Recovery Handoff

Date: 2026-07-07

This handoff records the current fixed-policy SAQ follow-up state. It replaces
the older July 6 handoff, which focused on the planner-v3 B=5 false-positive
recovery and is now stale.

## 1. Original Goal

The active goal is to harden a **query-unaware default-neighborhood fixed-policy
method** into a reproducible, meeting/paper-ready SAQ follow-up story.

The current method is:

```text
Start from SAQ's default segment plan.
Generate a small local default-neighborhood candidate set.
Score candidates with data-only boundary-risk and speed proxies.
Promote conservative/frontier-like candidates.
Reject speed-only or risky-fallback diagnostics.
Abstain when the default plan has no meaningful local neighborhood.
```

This is an empirical correction/policy layer around SAQ's default plan, not a
universal replacement for SAQ's planner.

## 2. Current Implementation State

Repository:

```text
repo   = /rwproject/kdd-db/kluaq/saq
branch = saq-boundary-audit
remote = origin git@github.com:Ufowoqqqo/SAQ.git
latest committed checkpoint before this handoff update = 5401b3f
```

Autonomy/control files are installed at repo root:

```text
AGENTS.md
TASK.md
PROGRESS.md
EXPERIMENTS.md
RESULTS.md
```

Read those before acting. `TASK.md` is the current source of truth if it
disagrees with this handoff.

Current fixed-policy evidence:

| Setting | Decision | Plan | Readout |
|---|---|---|---|
| GIST full K4096 B=3 | promote | `64:8,320:5,320:2,256:0` | +0.00159 R@100, 1.1119x QPS at np800 |
| GIST full K4096 B=4 | promote | `128:9,320:5,320:3,192:0` | +0.00077 R@100, 1.1948x QPS at np800 |
| GIST full K4096 B=5 | promote | `128:9,128:7,320:5,320:3,64:0` | +0.00028 R@100, 1.0793x QPS at np800 |
| CIFAR60K B=3 | promote | `128:6,64:4,192:2,128:0` | +0.0004 R@10, 1.0761x QPS at np200 |
| CIFAR60K B=4 | promote | `128:7,256:4,128:0` | +0.0004 R@10, 1.0745x QPS at np200 |
| CIFAR60K B=5 | promote | `128:8,64:6,256:4,64:0` | +0.0008 R@10, 1.0609x QPS at np200 |
| DEEP100K B=4 | reject | `128:4,128:3` | QPS improves, but -0.02757 R@100 |
| DEEP100K B=5 | reject | `128:5,128:4` | QPS improves, but -0.01429 R@100 |
| audio B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |
| word2vec100K B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |

Source:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
docs/saq_fixed_policy_method_spec_2026_07_07.md
RESULTS.md
```

## 3. Files Changed And Why

Current durable guidance and tracking:

| file | purpose |
|---|---|
| `AGENTS.md` | durable project rules, repo layout, build/test commands, constraints |
| `TASK.md` | active goal and success criteria |
| `PROGRESS.md` | running autonomous-session log |
| `EXPERIMENTS.md` | prioritized task/experiment checklist |
| `RESULTS.md` | stable conclusions only |
| `codex_handoff.md` | current recovery handoff |

Key method/evidence docs:

| file | purpose |
|---|---|
| `docs/saq_fixed_policy_method_spec_2026_07_07.md` | fixed-policy method specification |
| `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv` | clean validation table |
| `docs/saq_fixed_policy_decision_audit_2026_07_07.md` | row-by-row policy decision audit |
| `docs/saq_fixed_policy_meeting_summary_2026_07_07.md` | concise meeting-facing summary |
| `docs/saq_fixed_policy_applicability_classifier_2026_07_07.md` | two-stage applicability/decision classifier |
| `docs/saq_default_neighborhood_applicability_scan_2026_07_06.md` | pre-scorer applicability scan |
| `docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md` | GIST B=3 result after 1-bit fix |
| `docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md` | earlier cross-dataset validation |
| `docs/saq_stage_synthesis_v3_conservative_2026_07_06.md` | broader synthesis before fixed-policy cleanup |

Key scripts:

| file | role |
|---|---|
| `script/generate_default_neighborhood_plans.py` | local default-neighborhood candidate generator |
| `script/score_default_neighborhood_plans.py` | candidate scoring wrapper |
| `script/sweep_data_boundary_pairs.py` | data-only boundary-pair risk/speed proxy computation |
| `script/run_default_neighborhood_cross_dataset.py` | candidate selection, build/eval orchestration |
| `script/run_fixed_policy_matrix.py` | fixed-policy matrix runner |
| `script/report_fixed_policy_validation.py` | clean report/table generator |
| `script/scan_default_neighborhood_applicability.py` | pre-scorer default-shape/candidate scan |

Important C++ fix already in the branch:

```text
saqlib/quantization/caq/caq_encoder.hpp
saqlib/quantization/cluster_packer.hpp
```

This fix makes legal positive 1-bit SAQ segments buildable. Treat it as an
implementation correctness repair, not as the planner/method contribution.

## 4. Important Decisions And Constraints

- Stay query-unaware unless the user explicitly changes direction.
- Do not use representative query workloads or held-out query labels for plan
  generation or scoring.
- Held-out benchmark queries are allowed only for final evaluation.
- All measured recall/QPS claims must use:

  ```text
  -searcher_safe_block_min_mode=2
  ```

- Risky fallback is diagnostic only; never promote it as a fixed-policy result.
- Do not force custom plans for single-uniform defaults such as current
  audio/word2vec.
- Do not treat DEEP speed-only improvements as positive method evidence unless
  a new candidate preserves recall.
- Do not overclaim: the current method is empirical and shape-dependent.
- Record durable results in `docs/` or root tracking files; `/tmp/saq-run`
  artifacts are useful but not durable.

## 5. Uncertain Or Possibly Lost

**Uncertain:** Some detailed stdout/stderr logs for older long-running
experiments are probably only in terminal history or `/tmp/saq-run` outputs.
Checked-in docs are the durable source.

**Uncertain:** `/tmp/saq-run` artifacts were available during the July 7
autonomous run, but they may disappear on another machine or after cleanup.

**Uncertain:** Clean-machine regeneration cost is not fully audited. Existing
report/matrix reproduction uses local artifacts.

**Uncertain:** The current fixed-policy thresholds are empirically motivated.
They are not theoretically guaranteed.

## 6. Remaining TODOs

Current high-value items from `EXPERIMENTS.md`:

1. `E2`: turn `docs/saq_fixed_policy_method_spec_2026_07_07.md` into a more
   formal paper-style method section without hiding empirical thresholds.
2. `D2`: audit artifact staleness and document which checked-in claims depend
   on local `/tmp/saq-run` artifacts.
3. `D3`: audit metric cherry-picking risk, especially nprobe/top-k/QPS
   reporting and small recall deltas.
4. `C1`: expand candidate families only if the expansion remains
   query-unaware, local to SAQ default-neighborhood logic, and preserves
   reject/abstain behavior.
5. `D1`: keep DEEP B=4/B=5 as negative controls when changing policy/generator
   logic.

Prefer E2/D2/D3 before new expensive evaluations.

## 7. Commands And Tests Already Run If Known

Recent validation commands that succeeded:

```bash
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
python script/report_fixed_policy_validation.py --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
python script/run_fixed_policy_matrix.py --artifact-date 2026_07_06 --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
git diff --check
```

Recent output artifacts:

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

Recent pushed commits:

```text
5401b3f Document fixed-policy applicability classifier
def250a Add fixed-policy meeting summary
708b316 Record abstention audit
5f949e9 Record policy boundary audits
a4e18eb Add fixed-policy decision audit
f7be443 Record fixed-policy reproducibility checkpoint
5a0099a Install autonomy control files
```

## 8. Commands And Tests That Should Be Run Next

Start with:

```bash
git status --short --branch
sed -n '1,220p' TASK.md
sed -n '1,260p' EXPERIMENTS.md
sed -n '1,220p' RESULTS.md
python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
```

If continuing documentation hardening:

```bash
sed -n '1,260p' docs/saq_fixed_policy_method_spec_2026_07_07.md
sed -n '1,260p' docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
sed -n '1,260p' docs/saq_fixed_policy_meeting_summary_2026_07_07.md
```

If checking report reproducibility:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv

python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Before committing:

```bash
git diff --check
git status --short
```

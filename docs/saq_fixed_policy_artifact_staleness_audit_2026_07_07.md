# SAQ Fixed-Policy Artifact-Staleness Audit

Date: 2026-07-07

This audit scopes artifact durability for the current fixed-policy claim. It
does not cover every older exploratory document in `docs/`; many early notes
also reference `/tmp/saq-run`. The goal here is to identify the minimum artifact
chain needed to reproduce or inspect the current meeting/paper-facing evidence.

## 1. Durable Checked-In Sources

These files are versioned and should be treated as the durable summary layer:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
docs/saq_fixed_policy_method_spec_2026_07_07.md
docs/saq_fixed_policy_decision_audit_2026_07_07.md
docs/saq_fixed_policy_meeting_summary_2026_07_07.md
docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
RESULTS.md
PROGRESS.md
codex_handoff.md
```

The clean CSV is the most compact source for the current headline table. The
docs explain how to interpret it, but the docs do not contain all raw per-query
or per-candidate artifacts.

## 2. Local Non-Durable Artifact Chain

The current report/matrix reproduction uses local artifacts under:

```text
/tmp/saq-run
```

The latest matrix manifest is:

```text
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json
```

Its key outputs are:

```text
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.md
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.json
```

The checked-in clean table rows trace to these source reports:

| run | source report |
|---|---|
| `gist_full_K4096_B3` | `default_neighborhood_gist_B3_after_1bit_fix_2026_07_07.csv` |
| `gist_full_K4096_B4` | `default_neighborhood_cross_dataset_validation_2026_07_06.csv` |
| `gist_full_K4096_B5` | `default_neighborhood_gist_B5_holdout_2026_07_06.csv` |
| `cifar60k_B3` | `default_neighborhood_cifar_budget_holdout_2026_07_06.csv` |
| `cifar60k_B4` | `default_neighborhood_cross_dataset_validation_2026_07_06.csv` |
| `cifar60k_B5` | `default_neighborhood_cifar_budget_holdout_2026_07_06.csv` |
| `deep1M_sample100k_B4` | `default_neighborhood_cross_dataset_validation_2026_07_06.csv` |
| `deep1M_sample100k_B5` | `default_neighborhood_cross_dataset_validation_2026_07_06.csv` |
| `audio_K4096_B4` | `default_neighborhood_audio_holdout_2026_07_06.csv` |
| `word2vec_sample100k_B4` | `default_neighborhood_word2vec_holdout_2026_07_06.csv` |

Those source reports in turn depend on generated candidate/scorer outputs,
custom/default index files, compare CSVs, and QPS CSVs under `/tmp/saq-run`.

## 3. Reproduction Levels

There are three useful levels of reproducibility:

| level | required artifacts | command | cost |
|---|---|---|---|
| report-only | existing source summary CSVs and applicability CSV | `script/report_fixed_policy_validation.py` | cheap |
| matrix-from-existing-artifacts | existing generated candidates, scorer outputs, indexes, compare outputs, QPS outputs | `script/run_fixed_policy_matrix.py --artifact-date 2026_07_06` | moderate if cache hits |
| clean-machine regeneration | datasets, PCA/IVF artifacts, build, indexes, compare and QPS reruns | full preparation + matrix runner with force flags | expensive |

The July 7 successful reproduction was level 2, not a clean-machine
regeneration.

## 4. Known Successful Commands

Report-only check:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Matrix reproduction from existing artifacts:

```bash
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

The matrix manifest records the expanded command sequence:

```text
scan_default_neighborhood_applicability.py -> fixed_policy_applicability_scan_2026_07_07
run_default_neighborhood_cross_dataset.py --date 2026_07_06 --evaluate --allow-risky-fallback -> fixed_policy_matrix_validation_2026_07_07
report_fixed_policy_validation.py -> fixed_policy_validation_matrix_2026_07_07
```

The manifest intentionally uses:

```text
artifact_date = 2026_07_06
date          = 2026_07_07
```

because the matrix report reuses earlier generated per-run artifacts while
writing fresh July 7 summary/report files.

## 5. What To Do If Artifacts Are Missing

If only the final report outputs are missing, regenerate them from source
summary CSVs:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

If the matrix summary is missing but lower-level artifacts still exist, rerun:

```bash
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

If candidate/scorer/index/compare/QPS artifacts are missing, do not silently
update the clean CSV. First rerun the relevant per-dataset driver or matrix
runner with explicit force flags and record the regenerated artifact paths.

For full reruns, verify that all measured recall/QPS paths use:

```text
-searcher_safe_block_min_mode=2
```

## 6. Current Risk Assessment

Stable enough for meeting:

```text
The checked-in clean table and docs preserve the current conclusions.
The report and matrix drivers reproduced the table against local artifacts.
```

Still not fully solved:

```text
The branch does not yet provide a clean-machine artifact bundle or a
single-command dataset preparation pipeline for all fixed-policy rows.
```

This means the current result is reproducible on this prepared machine, but a
future machine may need dataset/artifact preparation before the matrix runner
can reproduce the clean table.

## 7. Recommended Follow-Up

1. Keep `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv` as the
   durable headline table.
2. Do not delete `/tmp/saq-run` until a clean-machine regeneration path is
   documented.
3. If the work moves toward paper submission, add a small script or manifest
   checker that fails early with explicit missing artifact paths.
4. Consider copying only small, high-value generated summaries into `docs/`;
   do not commit large datasets, indexes, or QPS output directories.

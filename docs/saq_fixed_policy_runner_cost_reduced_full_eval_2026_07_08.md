# Fixed-Policy Runner Cost-Reduced Full Evaluation

Date: 2026-07-08

This note records a formal fixed-policy matrix run using the integrated
query-unaware cost-reduced scorer path and safe-search evaluation.

## Scope

The run uses the official matrix runner:

```bash
python script/run_fixed_policy_matrix.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

The runner expands this into:

```text
scan_default_neighborhood_applicability.py
run_default_neighborhood_cross_dataset.py --evaluate --allow-risky-fallback \
  --use-cost-reduced-scorer --scorer-grid-preset endpoints
report_fixed_policy_validation.py --expected-csv ...
```

The search comparisons used:

```text
-searcher_safe_block_min_mode=2
```

The QPS files were reused when matching safe-block-min SIMD artifacts already
existed under `/tmp/saq-run/results/saq/`.

## Output Artifacts

```text
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_08_runner_cost_reduced_eval.json
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.md
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json
```

Feature cache:

```text
/tmp/saq-run/reports/fixed_policy_scorer_feature_cache_2026_07_08_runner_cost_reduced_eval
```

## Result

The generated report matched the checked-in clean validation table:

```text
Expected table matches: docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
Ignored fields: source_report
Decision counts: {'promote': 6, 'reject': 2, 'abstain': 2}
```

Clean validation table from the generated report:

| dataset | B | metric | default_shape | policy_decision | selected_or_tested_plan | delta_recall | qps_ratio | interpretation |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |
| gist_full | 3 | R@100 | multi_segment_with_zero_tail | promote | `64:8,320:5,320:2,256:0` | 0.00159 | 1.1119 | positive after 1-bit fix |
| gist_full | 4 | R@100 | multi_segment_with_zero_tail | promote | `128:9,320:5,320:3,192:0` | 0.00077 | 1.1948 | strongest QPS-positive GIST case |
| gist_full | 5 | R@100 | multi_segment_with_zero_tail | promote | `128:9,128:7,320:5,320:3,64:0` | 0.00028 | 1.0793 | positive high-budget GIST holdout |
| cifar60k | 3 | R@10 | multi_segment_with_zero_tail | promote | `128:6,64:4,192:2,128:0` | 0.0004 | 1.0761 | small positive CIFAR low-budget holdout |
| cifar60k | 4 | R@10 | multi_segment_with_zero_tail | promote | `128:7,256:4,128:0` | 0.0004 | 1.0745 | small positive CIFAR original case |
| cifar60k | 5 | R@10 | multi_segment_with_zero_tail | promote | `128:8,64:6,256:4,64:0` | 0.0008 | 1.0609 | small positive CIFAR high-budget holdout |
| deep1M_sample100k | 4 | R@100 | multi_segment_no_zero_tail | reject | `128:4,128:3` | -0.02757 | 1.0893 | rejected negative: speed gain costs too much recall |
| deep1M_sample100k | 5 | R@100 | multi_segment_no_zero_tail | reject | `128:5,128:4` | -0.01429 | 1.1037 | rejected negative: speed gain costs too much recall |
| audio | 4 | R@100 | single_uniform | abstain | none | n/a | n/a | stable abstention; applicability scan also abstains at B=3/B=5 |
| word2vec_sample100k | 4 | R@100 | single_uniform | abstain | none | n/a | n/a | stable abstention; applicability scan also abstains at B=3/B=5 |

## Interpretation

This run upgrades the previous cost-reduced runner evidence from
selection-only to full fixed-policy evaluation evidence. With endpoint-grid
scoring and feature caching enabled through the official runner, the current
fixed-policy matrix still reproduces the checked-in promote/reject/abstain
decisions and the measured recall/QPS table.

This does not change the method contribution. The feature cache and endpoint
grid remain scorer execution improvements for the query-unaware fixed-policy
pipeline, not a new quantizer and not an independent replacement for SAQ.

## Limitations

The artifacts live under `/tmp/saq-run` and are not checked into the repository.
The report is durable only through this note and the checked-in clean table.
The run reused existing matching safe QPS artifacts where available, so the
formal runner evaluated the matrix but did not necessarily recompute every QPS
CSV from scratch.

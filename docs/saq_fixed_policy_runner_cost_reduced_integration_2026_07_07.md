# Fixed-Policy Runner Cost-Reduced Scorer Integration

Date: 2026-07-07

This note records the integration of the query-unaware feature cache and
endpoint scorer grid into the official fixed-policy runners.

## Scope

The integrated path is available through:

```text
script/run_default_neighborhood_cross_dataset.py
script/run_fixed_policy_matrix.py
```

The new path keeps the fixed-policy candidate generation and promotion rule
unchanged. It changes only scorer execution:

```text
feature cache:  reuse residual/tail/boundary-pair features across B values
endpoint grid:  evaluate the validated endpoint scorer grid
```

The current official integration does not use held-out query labels and does
not change the search-time evaluation rule. The verification run below did not
rerun safe-search recall/QPS evaluation; it verified scorer selection
equivalence against the checked-in clean table.

## New Runner Options

```text
--use-cost-reduced-scorer
--scorer-grid-preset {full,endpoints}
--feature-cache-dir PATH
```

`--use-cost-reduced-scorer` normalizes the scorer grid to `endpoints` and, if
no cache path is provided, uses:

```text
<root>/reports/fixed_policy_scorer_feature_cache_<artifact-date>
```

The feature-cache key depends on dataset path, IVF K, padded dimension,
sampling parameters, residual-risk statistic, tail-risk quantile, and padding
size. It is query-unaware.

## Verification Command

```bash
python script/run_fixed_policy_matrix.py \
  --skip-scan \
  --skip-report \
  --no-evaluate \
  --force \
  --use-cost-reduced-scorer \
  --date 2026_07_07_runner_cost_reduced \
  --artifact-date 2026_07_07_runner_cost_reduced
```

The command produced:

```text
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07_runner_cost_reduced.manifest.json
```

## Decision/Plan Stability

The official runner output matches the checked-in clean table:

```text
decision match: 10/10
plan match:     10/10
```

Matched decisions:

| run | decision | selected/tested plan |
|---|---|---|
| gist_full_K4096_B3 | promote | `64:8,320:5,320:2,256:0` |
| gist_full_K4096_B4 | promote | `128:9,320:5,320:3,192:0` |
| gist_full_K4096_B5 | promote | `128:9,128:7,320:5,320:3,64:0` |
| cifar60k_B3 | promote | `128:6,64:4,192:2,128:0` |
| cifar60k_B4 | promote | `128:7,256:4,128:0` |
| cifar60k_B5 | promote | `128:8,64:6,256:4,64:0` |
| deep1M_sample100k_B4 | reject | `128:4,128:3` |
| deep1M_sample100k_B5 | reject | `128:5,128:4` |
| audio_K4096_B4 | abstain | none |
| word2vec_sample100k_B4 | abstain | none |

## Timing Readout

The verification run used fresh cache paths. The first B for each dataset/K
was a cold cache miss, while later B values reused the feature cache.

Representative phase timings:

```text
GIST B=3 cold miss:
  residual-risk computation: 105.560 s
  tail-risk computation:      27.252 s
  boundary-pair sampling:      3.115 s
  endpoint-grid scoring:       0.008 s

GIST B=4 cache hit:
  feature-cache load:          0.162 s
  endpoint-grid scoring:       0.016 s

CIFAR B=3 cold miss:
  residual-risk computation:   3.354 s
  tail-risk computation:       0.927 s
  boundary-pair sampling:      0.108 s

DEEP B=4 cold miss:
  residual-risk computation:   2.756 s
  tail-risk computation:       0.755 s
  boundary-pair sampling:      0.166 s
```

This confirms the earlier cost analysis: for full GIST, scorer overhead is
dominated by residual/tail feature computation, not endpoint-grid enumeration.

## Interpretation

The feature-cache and endpoint-grid path is now part of the official
fixed-policy runner interface. It should be described as an implementation and
reproducibility improvement for the scorer, not as a new quantization method.

The official integration keeps per-run sampling parameters unchanged. The
separate `a1024_p2` sampling calibration remains documented in
`docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.md`; it is
not silently promoted to the formal runner default here.

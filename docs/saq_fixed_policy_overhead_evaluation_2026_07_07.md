# SAQ Fixed-Policy Overhead Evaluation

Date: 2026-07-07

This report evaluates the extra cost of the fixed-policy layer relative to SAQ default planning.

## Scope

- The report uses the fixed-policy matrix artifact listed below.
- Candidate/scorer runtime is measured only when `--measure-planner-runtime` is enabled.
- QPS curve points are measured or reused across each run's validation nprobe grid.
- Index build time comes from existing `*.index.csv` metadata emitted by `create_index`; index size comes from serialized `.index` files.

```text
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json
```

## Planning And Index Overhead Summary

| run | candidates | pairs | planner runtime s | default index s | selected index s | default MB | selected MB | qps curve geomean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gist_full_K4096_B3 | 2 | 14740 | 145.265 | 2.266 | 2.487 | 439.7 | 446.6 | 1.1077 |
| gist_full_K4096_B4 | 5 | 14740 | 150.580 | 2.762 | 2.727 | 569.9 | 546.2 | 1.1511 |
| gist_full_K4096_B5 | 5 | 14740 | 149.590 | 2.970 | 2.960 | 669.7 | 669.7 | 1.0668 |
| cifar60k_B3 | 4 | 1068 | 8.562 | 0.083 | 0.082 | 17.8 | 17.8 | 1.0528 |
| cifar60k_B4 | 4 | 1068 | 8.607 | 0.080 | 0.098 | 20.5 | 19.6 | 1.0785 |
| cifar60k_B5 | 4 | 1068 | 8.517 | 0.096 | 0.098 | 24.8 | 24.8 | 1.0617 |
| deep1M_sample100k_B4 | 2 | 1904 | 5.804 | 0.101 | 0.089 | 17.2 | 15.6 | 1.0802 |
| deep1M_sample100k_B5 | 2 | 1904 | 5.842 | 0.091 | 0.077 | 20.2 | 18.7 | 1.0978 |
| audio_K4096_B4 | 1 |  | 0.102 | 0.051 |  | 14.5 |  |  |
| word2vec_sample100k_B4 | 1 |  | 0.096 |  |  |  |  |  |

## Interpretation

The deployable overhead is the planner/scorer pass plus one final selected-index build. The larger research workflow that built and evaluated multiple candidates is not counted as the deployable method.

If planner runtime is blank, the row was generated from existing artifacts without rerunning candidate generation and scoring. If a selected-index field is blank, the policy abstained or the selected index artifact is missing.

## Key Observations

Candidate generation is not the bottleneck. It is below 0.2 seconds in the
measured runs. The data-only scorer dominates planning overhead.

For full GIST K4096, the measured planner runtime is about 145-151 seconds per
budget. The corresponding `create_index` metadata reports only about 2.3-3.0
seconds for the already selected/default index builds. Under the current
implementation, this means the fixed-policy layer's extra offline cost is
mostly boundary-pair sampling and scorer-grid evaluation, not the final index
build.

For CIFAR60K and DEEP100K sample runs, measured planner runtime is much lower:
about 8.5-8.6 seconds on CIFAR and about 5.8 seconds on DEEP. This suggests
the scorer cost scales strongly with the number of sampled anchors/pairs and
the dimensionality of the same-cell candidate distance computations.

Index size is not consistently worse than the SAQ default. GIST B=4 and CIFAR
B=4 selected plans are smaller than their defaults, GIST B=3 is larger by about
6.9 MB, and several B=5/CIFAR cases are nearly unchanged. This supports the
claim that the method does not add new metadata fields, but selected segment
shape still changes the serialized index footprint.

The QPS curve is now measured across each validation nprobe grid for every
selected candidate. Promoted GIST/CIFAR rows remain speed-positive across the
curve. DEEP rows are also speed-positive, but they remain reject/control cases
because their recall loss is too large.

## Limitations

Planner runtime is a single wall-clock measurement per run and includes Python
startup, file I/O, candidate generation, boundary-pair sampling, and scorer-grid
evaluation. It should be treated as an order-of-magnitude overhead measurement,
not a stable microbenchmark.

Index build time is read from existing `*.index.csv` metadata emitted by
`create_index`; indexes were not rebuilt in this run. This is appropriate for
accounting from existing validation artifacts, but a final paper-quality table
should repeat build timing in a controlled run.

Audio and word2vec are abstention cases under the current generator, so no
selected-plan QPS curve is reported for them.

## Output Tables

```text
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.qps_curve.csv
docs/saq_fixed_policy_overhead_evaluation_2026_07_07.json
```

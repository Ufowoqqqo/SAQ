# Cross-Dataset Default-Neighborhood Validation

Date: 2026-07-06

This note records the first automated cross-dataset validation of the
`default-neighborhood generator + v3 scorer` workflow.

## 1. Goal

The question is whether the current default-neighborhood idea is a reusable
method or only a GIST-specific observation.

The tested workflow is:

```text
SAQ default plan
  -> generate a small default-neighborhood candidate set
  -> score candidates with data-boundary recall/speed proxies
  -> build/evaluate only selected candidates with safe searcher
```

The important constraint remains query-unaware selection: no held-out query
labels are used to create the candidate plans or scorer inputs.

## 2. New Automation

New script:

```text
script/run_default_neighborhood_cross_dataset.py
```

It connects:

- `script/generate_default_neighborhood_plans.py`
- `script/score_default_neighborhood_plans.py`
- `bin/create_index`
- `bin/compare_search_results`
- `bin/test_qps`

The default selection policy is conservative:

1. prefer non-default candidates that pass the conservative role guard;
2. then allow `frontier_like` candidates with both recall-risk score <= 1 and
   speed-proxy ratio <= 1;
3. only when `--allow-risky-fallback` is set, evaluate the best remaining
   non-default candidate to test whether the guard is too strict.

If the generator produces only the default plan, the driver records
`generator_produced_no_non_default_candidates` and skips the scorer/evaluator.
This matters for low-dimensional datasets where SAQ's global DP may already be
a single segment.

Measured recall/QPS always uses:

```text
-searcher_safe_block_min_mode=2
```

## 3. Command

```bash
python script/run_default_neighborhood_cross_dataset.py \
  --run deep1M_sample100k_B4 \
  --run deep1M_sample100k_B5 \
  --run cifar60k_B4 \
  --run gist_full_K4096_B4 \
  --evaluate \
  --allow-risky-fallback \
  --max-eval-per-run 1 \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_cross_dataset_validation_2026_07_06
```

`--allow-risky-fallback` was used only to validate negative cases. It should not
be interpreted as a promotion policy.

Held-out audio command:

```bash
python script/run_default_neighborhood_cross_dataset.py \
  --run audio_K4096_B4 \
  --evaluate \
  --max-eval-per-run 1 \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_audio_holdout_2026_07_06
```

This run intentionally did not use `--allow-risky-fallback`.

## 4. Summary

| run | default plan | selected candidate | selection | scorer signal | measured result |
|---|---|---|---|---|---|
| DEEP100K B=4 | `64:6,192:3` | `128:4,128:3` | risky fallback | recall-risk 1.6434, speed 0.9962x | +8.9% QPS, but -0.0276 R@100 at np200 |
| DEEP100K B=5 | `64:7,192:4` | `128:5,128:4` | risky fallback | recall-risk 1.6434, speed 0.9970x | +10.4% QPS, but -0.0143 R@100 at np200 |
| CIFAR60K B=4 | `64:9,192:5,128:3,128:0` | `128:7,256:4,128:0` | frontier-like | recall-risk 0.9617, speed 0.7212x | +7.4% QPS and +0.0004 R@10 at np200 |
| GIST full K4096 B=4 | `64:11,192:6,320:4,256:2,128:0` | `128:9,320:5,320:3,192:0` | conservative | recall-risk 0.9071, speed 0.7792x | +19.5% QPS and +0.00077 R@100 at np800 |
| Audio K4096 B=4 | `192:4` | none | no candidate selected | generator produced only default | no scorer/evaluator run |

Full summary:

```text
/tmp/saq-run/reports/default_neighborhood_cross_dataset_validation_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_cross_dataset_validation_2026_07_06.json
/tmp/saq-run/reports/default_neighborhood_audio_holdout_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_audio_holdout_2026_07_06.json
```

## 5. Per-Dataset Readout

### DEEP100K B=4

Generated candidates:

```text
default:   64:6,192:3
candidate: 128:4,128:3
```

The candidate slightly improves the speed proxy by reducing bitwork, but the
scorer strongly rejects it:

```text
recall-risk score: 1.6434
pair soft-inversion ratio: 1.7284
weighted pair-ratio: 1.7244
conservative guard: reject
```

Measured R@100:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.94550 | 0.92381 | -0.02169 |
| 100 | 0.97061 | 0.94401 | -0.02660 |
| 200 | 0.97641 | 0.94884 | -0.02757 |
| 400 | 0.97713 | 0.94940 | -0.02773 |

QPS at np200:

```text
default: 28603.207
custom:  31157.236
ratio:   1.089x
```

This is a clean negative example: speed-only head widening is not enough.

### DEEP100K B=5

Generated candidates:

```text
default:   64:7,192:4
candidate: 128:5,128:4
```

The scorer again rejects the candidate:

```text
recall-risk score: 1.6434
pair soft-inversion ratio: 1.7324
weighted pair-ratio: 1.7244
conservative guard: reject
```

Measured R@100:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.95180 | 0.94251 | -0.00929 |
| 100 | 0.97973 | 0.96687 | -0.01286 |
| 200 | 0.98670 | 0.97241 | -0.01429 |
| 400 | 0.98752 | 0.97304 | -0.01448 |

QPS at np200:

```text
default: 28163.443
custom:  31082.941
ratio:   1.104x
```

This confirms the DEEP cautionary case: when SAQ's default is already compact,
the default-neighborhood head-widen rule can buy speed by losing too much
recall.

### CIFAR60K B=4

Selected candidate:

```text
128:7,256:4,128:0
```

It did not pass the strict conservative guard because pair-inversion ratios were
slightly worse than default, but it was selected as `frontier_like`:

```text
recall-risk score: 0.9617
speed-proxy ratio: 0.7212
```

Measured R@10:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.9425 | 0.9419 | -0.0006 |
| 100 | 0.9724 | 0.9725 | +0.0001 |
| 200 | 0.9781 | 0.9785 | +0.0004 |
| 400 | 0.9790 | 0.9797 | +0.0007 |

QPS at np200:

```text
default: 24472.672
custom:  26295.217
ratio:   1.074x
```

This is a small but real positive example. It also shows that the conservative
guard alone is too strict for CIFAR; the `frontier_like` fallback is useful.

### Full GIST K4096 B=4

Selected candidate:

```text
128:9,320:5,320:3,192:0
```

This is the previously observed `compact_k4096` shape. The scorer selects it
conservatively:

```text
recall-risk score: 0.9071
speed-proxy ratio: 0.7792
conservative guard: pass
```

Measured R@100:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.74477 | 0.74491 | +0.00014 |
| 100 | 0.86604 | 0.86606 | +0.00002 |
| 200 | 0.94469 | 0.94485 | +0.00016 |
| 400 | 0.97999 | 0.98065 | +0.00066 |
| 800 | 0.98845 | 0.98922 | +0.00077 |

QPS at np800:

```text
default: 1013.640
custom:  1211.102
ratio:   1.195x
```

This is the strongest positive case: the automated workflow recovers a plan
that improves both recall and speed on full GIST.

### Audio K4096 B=4 Holdout

The held-out audio run used the fixed policy without risky fallback.

Generated candidates:

```text
default only: 192:4
```

Summary row:

```text
selection_reason: no_candidate_selected
scorer_skipped_reason: generator_produced_no_non_default_candidates
```

No custom plan was built or evaluated. This is still a useful holdout result:
for 192-dimensional audio at B=4, SAQ's global DP is already a single segment,
so the current default-neighborhood generator has no meaningful local shape to
perturb. The policy correctly does not force a candidate.

## 6. Interpretation

The workflow is not a universal "always improve SAQ" rule. It is a useful
query-unaware triage method:

- On GIST, default-neighborhood + scorer recovers a strong positive plan.
- On CIFAR, it finds a small speed/recall positive through the `frontier_like`
  path, but the strict conservative guard would miss it.
- On DEEP, the risky fallback candidates are faster but clearly lose recall,
  and the scorer/guard correctly refuses to promote them.
- On audio, the generator produces no non-default candidate, so the fixed policy
  abstains rather than inventing a plan.

This gives a more defensible contribution shape:

```text
SAQ's global variance DP can over-specialize the head on some datasets,
but not all datasets.

A small default-neighborhood generator plus a data-boundary scorer can identify
when head widening / tail expansion is promising and when it is unsafe.
```

The current method is therefore best framed as an automatic candidate triage and
validation layer around SAQ, not yet as a guaranteed replacement for SAQ's DP.

## 7. Remaining Gaps

1. The validation set is still small: two positive datasets/settings, one
   negative dataset/settings family, and one abstention case.
2. The conservative guard is safe but can be too strict, as shown by CIFAR.
3. `frontier_like` selection needs a clearer threshold calibration before it can
   be presented as a fixed method.
4. The generator currently only explores a small neighborhood around the SAQ
   default. It does not yet cover local/cluster-aware plans or non-contiguous
   dimension grouping.
5. Larger raw datasets are available but were not included in this run. They
   are natural next validation targets.

## 8. Artifacts

Main summaries:

```text
/tmp/saq-run/reports/default_neighborhood_cross_dataset_validation_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_cross_dataset_validation_2026_07_06.json
/tmp/saq-run/reports/default_neighborhood_audio_holdout_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_audio_holdout_2026_07_06.json
```

Generated/scored candidate outputs:

```text
/tmp/saq-run/reports/deep1M_sample100k_B4_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_B4_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_B5_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_B5_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B4_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B4_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/audio_K4096_B4_default_neighborhood_auto_2026_07_06.*
```

Measured compare/QPS outputs are referenced from the summary JSON.

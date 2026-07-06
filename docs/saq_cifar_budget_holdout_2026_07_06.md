# CIFAR Budget Holdout Validation

Date: 2026-07-06

This note records the fixed-policy validation for CIFAR60K at B=3 and B=5.
The goal was to test whether the small CIFAR B=4 positive result extends across
neighboring bit budgets.

The run used the fixed policy without risky fallback.

## Command

```bash
python script/run_default_neighborhood_cross_dataset.py \
  --run cifar60k_B3 \
  --run cifar60k_B5 \
  --evaluate \
  --max-eval-per-run 1 \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_cifar_budget_holdout_2026_07_06
```

Shared setup:

```text
dataset: cifar60k
K: 512
metric/search distance: L2
topk: R@10
safe searcher: -searcher_safe_block_min_mode=2
compare nprobe: 50, 100, 200, 400
QPS nprobe: 200
risky fallback: disabled
```

## Results

| run | default plan | selected plan | selection | scorer signal | R@10 np200 | QPS np200 |
|---|---|---|---|---|---|---|
| CIFAR B=3 | `64:8,128:4,192:2,128:0` | `128:6,64:4,192:2,128:0` | frontier-like | recall-risk 0.9941, speed proxy 1.0000x | 0.9617 -> 0.9621 (+0.0004) | 23714.5 -> 25520.0 (+7.61%) |
| CIFAR B=5 | `64:10,128:6,256:4,64:0` | `128:8,64:6,256:4,64:0` | frontier-like | recall-risk 0.9937, speed proxy 1.0000x | 0.9865 -> 0.9873 (+0.0008) | 23160.8 -> 24570.9 (+6.09%) |

Both selected candidates are `head_widen_keep_levels`: they widen the first
segment from 64 dimensions to 128 dimensions, reduce the head bitwidth by two,
and keep the following bit levels/tail structure.

## Recall Detail

### CIFAR B=3

Selected plan:

```text
default: 64:8,128:4,192:2,128:0
custom:  128:6,64:4,192:2,128:0
```

Measured R@10:

```text
nprobe 50:  0.9294 -> 0.9301  (+0.0007)
nprobe 100: 0.9560 -> 0.9570  (+0.0010)
nprobe 200: 0.9617 -> 0.9621  (+0.0004)
nprobe 400: 0.9622 -> 0.9628  (+0.0006)
```

QPS at nprobe 200:

```text
default: 23714.535
custom:  25519.960
ratio:   1.076x
```

### CIFAR B=5

Selected plan:

```text
default: 64:10,128:6,256:4,64:0
custom:  128:8,64:6,256:4,64:0
```

Measured R@10:

```text
nprobe 50:  0.9481 -> 0.9490  (+0.0009)
nprobe 100: 0.9796 -> 0.9806  (+0.0010)
nprobe 200: 0.9865 -> 0.9873  (+0.0008)
nprobe 400: 0.9877 -> 0.9886  (+0.0009)
```

QPS at nprobe 200:

```text
default: 23160.795
custom:  24570.926
ratio:   1.061x
```

## Interpretation

The result strengthens the CIFAR case:

- B=3, B=4, and B=5 all have positive measured outcomes under the fixed policy.
- The B=3/B=5 selected plans preserve the same segment count and zero-tail
  length as the default, but redistribute precision from the first 64
  dimensions into a 128-dimensional head.
- The gains are small in recall but consistent across all measured nprobe
  values, and QPS improves by roughly 6-8%.

The strict conservative guard still rejects both selected plans because the
pair-proxy soft-inversion and weighted-ratio terms are slightly above default:

```text
B=3: soft inversion 1.0010x, weighted ratio 1.0010x
B=5: soft inversion 1.0011x, weighted ratio 1.0011x
```

So this is another example where `frontier_like` is useful: it allows a plan
with lower boundary-cost recall risk and neutral speed proxy even when the
pair-proxy guard is marginally over 1.0. This supports calibrating a narrow
tolerance around the conservative guard instead of treating 1.0 as a hard
universal cutoff.

## Artifacts

Main summaries:

```text
/tmp/saq-run/reports/default_neighborhood_cifar_budget_holdout_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_cifar_budget_holdout_2026_07_06.json
```

Generated/scored candidate outputs:

```text
/tmp/saq-run/reports/cifar60k_B3_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B3_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B5_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B5_default_neighborhood_scored_auto_2026_07_06.*
```

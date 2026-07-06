# SAQ Default-Neighborhood Candidate Scoring

Date: 2026-07-06

This note documents the first scoring driver for the default-neighborhood
candidate generator, plus measured results for the two previously unmeasured
GIST/CIFAR candidates.

## 1. Implementation

New script:

```text
script/score_default_neighborhood_plans.py
```

Input:

```text
<default-neighborhood-output>.csv
```

Outputs:

```text
<output-prefix>.csv
<output-prefix>.unique.csv
<output-prefix>.pareto.csv
<output-prefix>.roles.csv
<output-prefix>.pairs.csv
<output-prefix>.risk.csv
<output-prefix>.summary.json
```

The script does not generate new DP plans. It scores the fixed candidate list
from `generate_default_neighborhood_plans.py` using the same query-unaware v3
proxies from `sweep_data_boundary_pairs.py`:

```text
recall_risk_score = boundary_cost_ratio
                  + soft_inversion_penalty
                  + weighted_ratio_penalty

ranking_score = recall_risk_score
              + legacy_runtime_penalty
              + speed_penalty
```

The default reference is the row with `is_default=True` in the candidate CSV,
unless an explicit default plan is provided.

## 2. Scoring Runs

CIFAR60K K512 B=4:

```bash
python script/score_default_neighborhood_plans.py \
  --candidate-csv /tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_2026_07_06.csv \
  --data-dir /tmp/saq-run/data/cifar60k \
  --dataset cifar60k \
  --k 512 \
  --avg-bits 4 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 4096 \
  --max-pairs 20000 \
  --max-candidates-per-anchor 2048 \
  --pair-seed 0 \
  --output-prefix /tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_scored_2026_07_06
```

Full GIST K4096 B=4:

```bash
python script/score_default_neighborhood_plans.py \
  --candidate-csv /tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_2026_07_06.csv \
  --data-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --avg-bits 4 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 4096 \
  --max-pairs 20000 \
  --max-candidates-per-anchor 2048 \
  --pair-seed 0 \
  --output-prefix /tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_scored_2026_07_06
```

## 3. CIFAR60K Readout

Scored unique candidates:

| rank | plan | family | recall-risk | speed-proxy ratio | conservative eligible |
|---:|---|---|---:|---:|---|
| 0 | `64:7,64:6,128:5,128:3,128:0` | `head_split` | 0.8297 | 1.2775 | no |
| 1 | `128:7,256:4,128:0` | `speed_merge_same_tail` | 0.9617 | 0.7212 | no |
| 2 | `128:7,128:5,128:3,128:0` | `head_widen_keep_levels` | 0.9937 | 1.0000 | no |
| 3 | `64:9,192:5,128:3,128:0` | default | 1.0000 | 1.0000 | yes |

The unmeasured candidate was:

```text
64:7,64:6,128:5,128:3,128:0
```

Safe-searcher measured R@10:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.9425 | 0.9424 | -0.0001 |
| 100 | 0.9724 | 0.9726 | +0.0002 |
| 200 | 0.9781 | 0.9785 | +0.0004 |
| 400 | 0.9790 | 0.9796 | +0.0006 |

Safe-searcher QPS at np200:

| plan | R@10 | QPS | QPS ratio vs default |
|---|---:|---:|---:|
| default | 0.9781 | 24472.672 | 1.000x |
| `64:7,64:6,128:5,128:3,128:0` | 0.9785 | 20848.754 | 0.852x |
| `128:7,128:5,128:3,128:0` | 0.9801 | 25368.984 | 1.037x |
| `128:7,256:4,128:0` | 0.9785 | 26295.217 | 1.074x |

Interpretation:

The aggressive CIFAR `head_split` candidate slightly improves high-nprobe R@10,
but it is much slower than default and is dominated by the already measured
`head_widen_keep_levels` and `speed_merge_same_tail` candidates. The conservative
guard correctly refused to promote it because both pair-inversion ratios and
speed proxy were worse than default.

## 4. Full GIST K4096 Readout

Scored unique candidates:

| rank | plan | family | recall-risk | speed-proxy ratio | conservative eligible |
|---:|---|---|---:|---:|---|
| 0 | `64:9,64:7,128:6,320:4,256:2,128:0` | `head_split` | 0.8487 | 1.2153 | no |
| 1 | `128:9,320:5,320:3,192:0` | `tail_expand_head_widen` | 0.9071 | 0.7792 | yes |
| 2 | `64:10,320:6,384:3,192:0` | `tail_expand_middle_merge` | 0.9139 | 0.7792 | yes |
| 3 | `128:8,128:6,320:4,256:2,128:0` | `head_widen_keep_levels` | 0.9990 | 0.9994 | yes |
| 4 | `64:11,192:6,320:4,256:2,128:0` | default | 1.0000 | 1.0000 | yes |

The unmeasured candidate was:

```text
128:8,128:6,320:4,256:2,128:0
```

Safe-searcher measured R@100:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.74477 | 0.74484 | +0.00007 |
| 100 | 0.86604 | 0.86608 | +0.00004 |
| 200 | 0.94469 | 0.94485 | +0.00016 |
| 400 | 0.97999 | 0.98046 | +0.00047 |
| 800 | 0.98845 | 0.98903 | +0.00058 |

Safe-searcher QPS at np800:

| plan | R@100 | QPS | QPS ratio vs default |
|---|---:|---:|---:|
| default | 0.98845 | 1013.640 | 1.000x |
| `128:8,128:6,320:4,256:2,128:0` | 0.98903 | 1112.625 | 1.098x |
| `128:9,320:5,320:3,192:0` | 0.98922 | 1211.102 | 1.195x |
| `64:10,320:6,384:3,192:0` | 0.98948 | 1092.294 | 1.078x |

Interpretation:

The new GIST `head_widen_keep_levels` candidate is a real improvement over
default, but it does not improve the current frontier. It is dominated by
`compact_k4096` (`128:9,320:5,320:3,192:0`), which is both more accurate and
faster at np800. It is also below `filtered_new` on recall, though slightly
faster.

## 5. Current Conclusion

The scoring driver is useful as a cheap candidate triage layer:

- on CIFAR, the scorer exposes the aggressive `head_split` plan but the
  conservative guard prevents over-promotion;
- on GIST, the scorer marks the new head-widen plan as safe, and measurement
  confirms it improves over default;
- however, the two newly measured candidates do not add a new best point beyond
  the already known GIST/CIFAR positives.

The stronger reusable rule remains:

```text
generate a small default-neighborhood set,
score with data-boundary recall/speed proxies,
then validate only conservative or frontier-looking candidates with safe searcher.
```

## 6. Artifacts

Scorer outputs:

```text
/tmp/saq-run/reports/cifar60k_K512_B4_default_neighborhood_scored_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B4_default_neighborhood_scored_2026_07_06.*
```

Measured compare/QPS outputs:

```text
/tmp/saq-run/reports/cifar60k_B4_head_split_compare_np{50,100,200,400}_top10.csv
/tmp/saq-run/results/saq/qps_cifar60k_ivf512_b4_caq_adj_seg_plan64x7_64x6_128x5_128x3_128x0_pca_th24_np200_sm4_top10_safeblockminsimd.csv

/tmp/saq-run/reports/gist_full_B4_head_widen_keep_levels_compare_np{50,100,200,400,800}_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan128x8_128x6_320x4_256x2_128x0_pca_th24_np800_sm4_safeblockminsimd.csv
```

# GIST Sample100k B=5 v3 Conservative Role Guard

Date: 2026-07-06

## 1. Purpose

The previous B=5 planner-v3 endpoint evaluation showed that the offline
recall-risk minimum:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

was a measured false positive under the corrected safe searcher. It had the best
offline recall-risk proxy, but did not beat `b5_rank0` in measured R@100 and was
slower than default.

This note implements and validates a conservative planner-v3 role-selection
guard. The guard is a promotion rule only: it does not change the DP search, the
raw ranking, or the Pareto frontier.

## 2. Implementation

Modified script:

```text
script/sweep_data_boundary_pairs.py
```

New output fields in `.unique.csv`, `.pareto.csv`, and `.roles.csv`:

```text
conservative_role_is_eligible
conservative_role_reasons
```

New roles in `.roles.csv`:

```text
conservative_recall_risk_min
conservative_combined_min
```

Default conservative role guard:

| guard | default | meaning |
|---|---:|---|
| `--conservative-role-soft-inversion-max` | 1.0 | reject plans with weighted soft-inversion penalty worse than default |
| `--conservative-role-weighted-ratio-max` | 1.0 | reject plans with weighted pair-ratio mean worse than default |
| `--conservative-role-speed-proxy-max` | 1.0 | reject plans with slower speed proxy than default |
| `--conservative-role-max-nonzero-segments` | 0 | disabled unless explicitly set |

The old roles remain unchanged:

```text
recall_risk_min
combined_min
speed_proxy_min
```

## 3. Command

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 5 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 2048 \
  --max-pairs 8192 \
  --boundary-global-blends 0,0.25 \
  --boundary-tail-alphas 0 \
  --boundary-pair-alphas 0,0.5,1,2 \
  --segment-penalty-scales 0,0.01,0.02 \
  --intra-segment-penalty-scales 0,1.6,3.2 \
  --inversion-penalty-scales 0,0.05,0.1 \
  --weighted-ratio-penalty-scales 0,0.02 \
  --runtime-penalty-scales 0 \
  --speed-proxy-scales 0,0.02,0.05,0.1 \
  --conservative-role-soft-inversion-max 1.0 \
  --conservative-role-weighted-ratio-max 1.0 \
  --conservative-role-speed-proxy-max 1.0 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06
```

## 4. Sweep Summary

| metric | value |
|---|---:|
| all configs | 1728 |
| feasible configs | 1344 |
| selected unique plans | 8 |
| Pareto plans | 3 |
| sampled boundary pairs | 1640 |
| conservative-eligible plans | 2 |

The conservative-eligible plans are:

| rank | plan | recall-risk score | speed proxy ratio | soft inversion ratio | weighted ratio |
|---:|---|---:|---:|---:|---:|
| 4 | `64:10,192:8,256:5,384:3,64:0` | 0.971907 | 1.000000 | 0.990842 | 0.991141 |
| 7 | `64:11,192:7,320:5,320:3,64:0` | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

So the conservative candidate is exactly the measured B=5 recall/middle point:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

## 5. Role Output

| role | selected plan | eligible | rejection reason if rejected |
|---|---|---|---|
| `recall_risk_min` | `64:9,64:8,128:7,320:5,320:3,64:0` | no | `soft_inversion_ratio>1;weighted_ratio>1;speed_proxy_ratio>1` |
| `combined_min` | `64:9,64:8,128:7,320:5,320:3,64:0` | no | `soft_inversion_ratio>1;weighted_ratio>1;speed_proxy_ratio>1` |
| `speed_proxy_min` | `128:10,256:6,320:4,256:2` | no | `soft_inversion_ratio>1;weighted_ratio>1` |
| `conservative_recall_risk_min` | `64:10,192:8,256:5,384:3,64:0` | yes |  |
| `conservative_combined_min` | `64:10,192:8,256:5,384:3,64:0` | yes |  |

## 6. Readout

The conservative role-selection guard fixes the observed B=5 planner-v3 failure
mode at the promotion layer.

The raw planner still reports the split-front endpoint as the offline
recall-risk minimum, which is useful diagnostic information. The conservative
roles do not promote it because it is simultaneously worse than default on:

```text
soft inversion ratio = 1.030461
weighted ratio       = 1.029477
speed proxy ratio    = 1.214129
```

The promoted conservative role is `b5_rank0`, matching the corrected measured
leaderboard:

```text
b5_rank0 measured np200 R@100 = 0.99521
default measured np200 R@100  = 0.99478
delta                         = +0.00043
```

This does not prove the guard is universally correct. It means the planner now
separates two concepts that should not be conflated:

1. the best offline recall-risk endpoint; and
2. the safest promotion candidate under conservative proxy constraints.

## 7. Artifacts

```text
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.pareto.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.roles.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.pairs.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.risk.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_conservative_sweep_2026_07_06.summary.json
```

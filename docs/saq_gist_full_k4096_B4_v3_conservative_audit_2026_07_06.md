# Full GIST K4096 B=4 v3 Conservative Guard Audit

Date: 2026-07-06

## 1. Purpose

After the B=5 `gist_sample100k` audit, planner v3 now has a conservative
promotion guard. The guard does not change the DP search, raw ranking, or Pareto
frontier. It only adds conservative role selections that require a plan to be no
worse than default on:

```text
weighted soft-inversion ratio
weighted pair-ratio mean
speed-proxy ratio
```

This note reruns the full GIST K4096 B=4 v3 sweep with that guard to check
whether the previous full-scale conclusion still holds.

## 2. Setup

Configuration:

```text
dataset = gist_full
K = 4096
B = 4
query-aware signals = none
planner = data-only boundary-pair v3 + conservative role guard
```

Command:

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --avg-bits 4 \
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
  --output-prefix /tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06
```

## 3. Sweep Summary

| metric | value |
|---|---:|
| all configs | 1728 |
| feasible configs | 1512 |
| selected unique plans | 6 |
| Pareto plans | 2 |
| sampled boundary pairs | 8192 |
| pair-weight tau | 0.004338 |
| conservative-eligible plans | 4 |

The counts match the previous full K4096 v3 sweep except for the new
conservative eligibility annotations.

## 4. Pareto Frontier

Lower recall-risk score is better. Lower speed-proxy ratio is faster.

| Pareto rank | plan | recall-risk score | speed proxy ratio | soft inversion ratio | conservative eligible | reason |
|---:|---|---:|---:|---:|---|---|
| 0 | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | 0.971267 | no | `speed_proxy_ratio>1` |
| 1 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | yes |  |

So the raw Pareto interpretation is unchanged:

```text
recall-risk endpoint = v2_split64
speed endpoint       = compact_k4096
```

The conservative promotion guard excludes `v2_split64` only because it is
slower than default by the speed proxy, not because it has higher inversion
risk.

## 5. Role Output

| role | selected plan | recall-risk score | speed proxy ratio | soft inversion ratio | weighted ratio | conservative eligible | reason |
|---|---|---:|---:|---:|---:|---|---|
| `recall_risk_min` | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | 0.971267 | 0.971540 | no | `speed_proxy_ratio>1` |
| `combined_min` | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | 0.976729 | yes |  |
| `speed_proxy_min` | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | 0.976729 | yes |  |
| `conservative_recall_risk_min` | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | 0.976729 | yes |  |
| `conservative_combined_min` | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.976507 | 0.976729 | yes |  |

The conservative role guard therefore selects:

```text
compact_k4096 = 128:9,320:5,320:3,192:0
```

## 6. Conservative-Eligible Plans

The four eligible plans are:

| rank | plan | ranking score | recall-risk score | speed proxy ratio | soft inversion ratio | weighted ratio |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `128:9,320:5,320:3,192:0` | 0.910066 | 0.932147 | 0.779192 | 0.976507 | 0.976729 |
| 1 | `128:9,384:5,320:2,128:0` | 0.911982 | 0.933510 | 0.784726 | 0.981194 | 0.981372 |
| 3 | `64:8,192:7,320:4,256:2,128:0` | 0.935312 | 0.935312 | 1.000000 | 0.971205 | 0.971478 |
| 4 | `64:9,256:6,256:4,256:2,128:0` | 0.952862 | 0.952862 | 1.000000 | 0.955130 | 0.955555 |

`compact_k4096` is the best eligible plan by both conservative recall-risk and
conservative combined roles.

## 7. Relationship To Measured Results

The measured full K4096 B=4 leaderboard already established:

| plan | R@100 np800 | QPS np800 | QPS ratio |
|---|---:|---:|---:|
| default | 0.98845 | 1013.64 | 1.000x |
| `v2_split64` | 0.98975 | 918.44 | 0.906x |
| `filtered_new` | 0.98948 | 1092.29 | 1.078x |
| `compact_k4096` | 0.98922 | 1211.10 | 1.195x |

The conservative role result is consistent with the speed-oriented measured
interpretation:

- `v2_split64` remains the best recall plan, but is slower.
- `compact_k4096` remains the speed-oriented systems candidate.
- `filtered_new` remains an important measured balanced point, but it is still
  not rediscovered by the current data-only DP sweep.

## 8. Readout

The conservative guard does not change the full GIST K4096 B=4 raw planner
story. It separates the story into two outputs:

```text
raw recall endpoint          = v2_split64
conservative promotion point = compact_k4096
```

This is a useful split. The raw endpoint preserves the best recall-risk signal,
while the conservative role selects a plan that is not worse than default under
the offline inversion and speed proxies.

The caveat is important: this conservative rule is now speed-biased by design.
It will not promote slower recall-oriented plans such as `v2_split64`, even when
they have the best measured recall. For meeting narrative, the clean statement
is:

```text
v3 exposes the recall/speed Pareto endpoints; the conservative guard selects
the safest promotion candidate, not necessarily the best recall candidate.
```

## 9. Artifacts

```text
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.unique.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.pareto.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.roles.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.pairs.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.risk.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_conservative_sweep_2026_07_06.summary.json
```

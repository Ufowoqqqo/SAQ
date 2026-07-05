# Boundary-Aware Planner v3: Recall-Risk + Speed Proxy

Date: 2026-07-05

## 1. Motivation

The latest full-GIST K4096 audits show that current candidate plans occupy
different parts of the same tradeoff:

```text
v2_split64    = 64:9,64:7,128:6,320:4,256:2,128:0  # recall-oriented, slower
filtered_new  = 64:10,320:6,384:3,192:0             # balanced, not rediscovered by data-only DP
compact_k4096 = 128:9,320:5,320:3,192:0             # speed-oriented, higher inversion risk
```

The previous data-only boundary-pair sweep already had an inversion proxy and a
very coarse runtime penalty. However, it did not expose the recall/speed tradeoff
as a first-class planner output. Planner v3 makes this explicit.

The goal is still query-unaware: all signals come from base vectors, IVF
assignments, PCA variance, residual variance, and base-as-pseudo-query boundary
pairs.

## 2. Implementation

Modified script:

```text
script/sweep_data_boundary_pairs.py
```

New outputs:

```text
<output-prefix>.pareto.csv  # non-dominated plans in recall-risk vs speed-proxy space
<output-prefix>.roles.csv   # recall-risk, combined, and speed-proxy role selections
```

New CLI knobs:

```text
--weighted-ratio-penalty-scales
--speed-proxy-scales
--speed-nonzero-segment-weight
--speed-segment-weight
--speed-nonzero-dim-weight
--speed-bitwork-weight
--speed-zero-tail-reward
```

The default behavior is backward-compatible: the new penalty grids default to
zero, so old commands still produce the old ranking unless the v3 knobs are
enabled.

## 3. Scoring

Planner v3 separates recall risk from speed risk.

Recall-risk score:

```text
recall_risk_score
  = boundary_cost_ratio
    + soft_inversion_penalty
    + weighted_ratio_penalty
```

where:

```text
soft_inversion_penalty
  = inversion_penalty_scale
    * (soft_inversion_ratio_vs_default - 1)

weighted_ratio_penalty
  = weighted_ratio_penalty_scale
    * (weighted_pair_ratio_vs_default - 1)
```

Speed proxy:

```text
speed_proxy_raw
  = w_nonzero_segment * nonzero_segment_count
    + w_segment * segment_count
    + w_nonzero_dim * nonzero_dim_fraction
    + w_bitwork * bitwork_ratio_to_budget
    - w_zero_tail * zero_tail_fraction
```

The default weights used in the full run were:

```text
w_nonzero_segment = 0.55
w_segment = 0.10
w_nonzero_dim = 0.25
w_bitwork = 0.10
w_zero_tail = 0.0
```

Final ranking score:

```text
ranking_score
  = recall_risk_score
    + legacy_runtime_penalty
    + speed_proxy_scale * (speed_proxy_ratio_vs_default - 1)
```

In the v3 full run, `legacy_runtime_penalty` was disabled with
`--runtime-penalty-scales 0`; the speed term came from the new speed proxy.

## 4. Full GIST K4096 Run

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
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05
```

Outputs:

```text
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.unique.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.pareto.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.roles.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.pairs.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.risk.csv
/tmp/saq-run/reports/gist_full_K4096_B4_boundary_v3_speed_recall_sweep_2026_07_05.summary.json
```

Run summary:

| metric | value |
|---|---:|
| all configs | 1728 |
| feasible configs | 1512 |
| selected unique plans | 6 |
| sampled boundary pairs | 8192 |
| pair-weight tau | 0.004338 |
| Pareto plans | 2 |

## 5. Pareto Frontier

Lower `recall_risk_score` is better. Lower `speed_proxy_ratio_vs_default` is
faster.

| Pareto rank | plan | recall-risk score | speed proxy ratio | boundary reduction | soft inversion ratio |
|---:|---|---:|---:|---:|---:|
| 0 | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 1.215274 | 0.077928 | 0.971267 |
| 1 | `128:9,320:5,320:3,192:0` | 0.932147 | 0.779192 | 0.065038 | 0.976507 |

Interpretation:

- `v2_split64` remains the recall-risk endpoint.
- `compact_k4096` becomes the speed endpoint.
- The old `boundary_4seg` shape is dominated by `compact_k4096` under this
  proxy: slightly worse recall-risk and slightly worse speed proxy.

## 6. Role Shortlist

| role | selected plan | ranking score | recall-risk score | speed proxy ratio | nonzero segments | zero tail |
|---|---|---:|---:|---:|---:|---:|
| recall-risk min | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.918630 | 0.918630 | 1.215274 | 5 | 128 |
| combined min | `128:9,320:5,320:3,192:0` | 0.910066 | 0.932147 | 0.779192 | 3 | 192 |
| speed proxy min | `128:9,320:5,320:3,192:0` | 0.910066 | 0.932147 | 0.779192 | 3 | 192 |

This matches the measured K4096 audits:

- `v2_split64` has the best measured R@100 but is slower.
- `compact_k4096` is the fastest measured B=4 K4096 candidate with positive
  R@100 delta.

## 7. Readout

Planner v3 does not discover a new better plan in this run. Its value is that
it turns the current manual interpretation into explicit offline planner
outputs:

```text
recall endpoint = v2_split64
speed endpoint  = compact_k4096
```

This is useful because future sweeps can now be judged by whether they move the
Pareto frontier, not by whether a single scalar rank changes. A genuinely better
planner result should either:

1. lower recall-risk without increasing speed proxy beyond `v2_split64`, or
2. lower speed proxy without worsening recall-risk beyond `compact_k4096`, or
3. introduce a new middle point that is not dominated by either endpoint.

## 8. Next Step

The next experimental step should be to use v3 as the default offline selector
and test whether the same two-endpoint pattern holds beyond full GIST K4096 B=4.

Recommended next checks:

1. Run the same v3 sweep on `gist_sample100k` B=5 to verify bit-budget
   stability.
2. Run a lightweight full-GIST K4096 B=5 v3 sweep if build/evaluation cost is
   acceptable.
3. If v3 repeatedly returns only the same endpoints, add a middle-point target,
   for example a constraint such as `speed_proxy_ratio <= 1.0` while minimizing
   recall risk.


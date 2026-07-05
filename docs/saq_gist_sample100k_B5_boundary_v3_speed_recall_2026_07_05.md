# GIST Sample100k B=5 Boundary Planner v3 Sweep

Date: 2026-07-05

## 1. Purpose

The full-GIST K4096 B=4 planner-v3 run exposed a two-endpoint tradeoff:

```text
recall-risk endpoint = v2_split64
speed endpoint       = compact_k4096
```

This note runs the same v3 scoring on `gist_sample100k / K512 / B=5` to check
whether the recall-risk versus speed-proxy tradeoff is stable across bit
budgets.

This is an offline planner/proxy run. It does not build new indexes or measure
new safe-searcher recall. Existing corrected B=5 measurements should still be
read from:

```text
docs/saq_gist_sample100k_safe_corrected_leaderboard_2026_07_04.md
docs/saq_gist_sample100k_B5_b5_rank0_safe_review_2026_07_04.md
```

## 2. Setup

Dataset/setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 5
PCA = true
query-aware signals = none
```

B=5 default plan from the corrected leaderboard:

```text
default_b5 = 64:11,192:7,320:5,320:3,64:0
```

Guard policy:

| guard | value | reason |
|---|---:|---|
| minimum positive bitwidth | 2 | remove risky non-final 1-bit segments |
| minimum nonempty zero tail | 64 dims | allow the buildable B=5 default shape |
| maximum segments | 6 | avoid overly fragmented plans |
| maximum positive segment width | 384 dims | avoid very broad low-bit positive segments |
| exclude non-final 1-bit | true | remove the known unsafe shape class |

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
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05
```

Outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.pareto.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.roles.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.pairs.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.risk.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_speed_recall_sweep_2026_07_05.summary.json
```

## 4. Sampling Summary

The run sampled local base-as-query boundary pairs inside IVF cells:

| metric | value |
|---|---:|
| IVF cells | 512 |
| eligible cells | 410 |
| sampled anchors | 410 |
| sampled boundary pairs | 1640 |
| median exact margin | 0.006965 |
| p90 exact margin | 0.031586 |
| pair-weight tau | 0.006965 |
| pair-risk top64 share | 0.609148 |

The `max_anchors=2048` and `max_pairs=8192` limits are not reached because only
410 IVF cells are eligible under the local boundary-rank condition. With one
anchor per eligible cell and four pairs per anchor, the sample contains
`410 * 4 = 1640` boundary pairs.

Pair-risk block distribution:

| block | dims | pair-risk share |
|---:|---|---:|
| 0 | 0-64 | 0.607817 |
| 1 | 64-128 | 0.157697 |
| 2 | 128-192 | 0.076753 |
| 3 | 192-256 | 0.048806 |
| 4 | 256-320 | 0.031641 |
| 5 | 320-384 | 0.022975 |

As in the B=4 data-boundary pair runs, the sampled pair-risk signal is strongly
head-concentrated.

## 5. Sweep Summary

| metric | value |
|---|---:|
| all configs | 1728 |
| feasible configs | 1344 |
| selected unique plans | 8 |
| Pareto plans | 3 |

Top unique plans by v3 ranking score:

| rank | plan | ranking score | recall-risk score | speed proxy ratio | boundary reduction | soft inversion ratio |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `64:9,64:8,128:7,320:5,320:3,64:0` | 0.955578 | 0.955578 | 1.214129 | 0.044422 | 1.030461 |
| 1 | `64:10,128:8,192:6,192:4,320:3,64:0` | 0.958418 | 0.958418 | 1.214129 | 0.041352 | 0.998074 |
| 2 | `64:10,64:7,128:7,320:5,320:3,64:0` | 0.958892 | 0.958892 | 1.214129 | 0.041108 | 1.036569 |
| 3 | `128:10,256:6,320:4,256:2` | 0.971328 | 0.974079 | 0.972491 | 0.025921 | 1.003152 |
| 4 | `64:10,192:8,256:5,384:3,64:0` | 0.971907 | 0.971907 | 1.000000 | 0.027000 | 0.990842 |
| 5 | `128:9,320:6,256:4,256:2` | 0.973095 | 0.975846 | 0.972491 | 0.024154 | 1.003260 |
| 6 | `64:11,128:8,192:6,320:4,192:2,64:0` | 0.995862 | 0.995862 | 1.214129 | 0.002387 | 0.985333 |
| 7 | `64:11,192:7,320:5,320:3,64:0` | 1.000000 | 1.000000 | 1.000000 | 0.000000 | 1.000000 |

## 6. Pareto Frontier

Lower recall-risk score is better. Lower speed proxy ratio is faster.

| Pareto rank | plan | recall-risk score | speed proxy ratio | boundary reduction | soft inversion ratio | nonzero segments | zero tail |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | `64:9,64:8,128:7,320:5,320:3,64:0` | 0.955578 | 1.214129 | 0.044422 | 1.030461 | 5 | 64 |
| 1 | `64:10,192:8,256:5,384:3,64:0` | 0.971907 | 1.000000 | 0.027000 | 0.990842 | 4 | 64 |
| 2 | `128:10,256:6,320:4,256:2` | 0.974079 | 0.972491 | 0.025921 | 1.003152 | 4 | 0 |

Role shortlist:

| role | selected plan | ranking score | recall-risk score | speed proxy ratio |
|---|---|---:|---:|---:|
| recall-risk min | `64:9,64:8,128:7,320:5,320:3,64:0` | 0.955578 | 0.955578 | 1.214129 |
| combined min | `64:9,64:8,128:7,320:5,320:3,64:0` | 0.955578 | 0.955578 | 1.214129 |
| speed proxy min | `128:10,256:6,320:4,256:2` | 0.971328 | 0.974079 | 0.972491 |

## 7. Stability Readout

The high-level structure is stable, but the details are not identical to B=4.

Stable part:

1. A split-front multi-segment plan remains the best recall-risk endpoint.
2. A coarser four-segment plan remains the speed endpoint.
3. The speed endpoint sacrifices recall-risk proxy quality for fewer segments
   and cheaper plan shape.

Changed part:

1. B=5 has a middle Pareto point: `64:10,192:8,256:5,384:3,64:0`.
2. This middle point is exactly `b5_rank0`, the corrected safe-searcher B=5
   recall winner from the previous evaluation.
3. The no-tail speed endpoint `128:10,256:6,320:4,256:2` is the old `b5_rank1`.
   Under corrected safe-searcher measurements, this plan is speed-oriented but
   not recall-improving.
4. The v3 recall-risk endpoint is `64:9,64:8,128:7,320:5,320:3,64:0`, which
   was a lower-first-block B=5 guarded-sweep shape but has not been evaluated
   under the corrected safe searcher yet.

Compared with B=4:

| setting | Pareto endpoints |
|---|---|
| full GIST K4096 B=4 | recall endpoint `v2_split64`; speed endpoint `compact_k4096` |
| gist sample100k K512 B=5 | recall endpoint split-front B=5; middle point `b5_rank0`; speed endpoint no-tail B=5 |

So the answer is: the recall-risk/speed-proxy tradeoff is qualitatively stable,
but B=5 introduces a meaningful middle point that B=4 did not expose in the same
way.

## 8. Relationship To Corrected Measurements

Corrected safe-searcher B=5 measurements at nprobe 200:

| measured role | plan | R@100 np200 delta | QPS ratio |
|---|---|---:|---:|
| corrected recall winner | `64:10,192:8,256:5,384:3,64:0` | +0.00043 | 0.993x |
| speed-oriented old candidate | `128:10,256:6,320:4,256:2` | -0.00002 | 1.134x |

Planner v3 places these two measured plans exactly where expected:

- `b5_rank0` is the middle Pareto point: close to default speed proxy, better
  recall-risk than default, and the lowest soft-inversion ratio among the
  Pareto points.
- `b5_rank1` is the speed endpoint: lower speed proxy than default, but weaker
  recall-risk than the split-front endpoint and the `b5_rank0` middle point.

The new uncertainty is the v3-selected recall endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

It has the best offline recall-risk score, but its soft-inversion ratio is
`1.030x` of default. This should not be promoted as a recall candidate without
building and evaluating it under `-searcher_safe_block_min_mode=2`.

## 9. Next Step

The next high-signal step is to build and evaluate the v3-selected B=5
recall-risk endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

Use the corrected safe-searcher protocol:

```text
dataset = gist_sample100k
K = 512
B = 5
metric = R@100
nprobe = 20,50,100,200,400
searcher = -searcher_safe_block_min_mode=2
QPS = np200, top100, 24 threads
```

If it beats `b5_rank0`, then v3 found a new B=5 recall candidate. If it does
not, then v3 should keep `b5_rank0` as the measured B=5 middle point and treat
the split-front endpoint as an offline-risk false positive.


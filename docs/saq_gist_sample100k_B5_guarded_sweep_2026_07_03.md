# GIST Sample100k B=5 Guarded Boundary Sweep

Date: 2026-07-03

This note extends the GIST `B=4` boundary-aware v2 sweep to `B=5`. The goal is to test whether the v2 planner signal is specific to one bit budget or remains useful when the average code budget is higher.

## 1. Setup

Dataset and index setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
B = 5
PCA = true
groundtruth = sample-specific top1000 GT
metric = R@100, QPS, relative error at nprobe=200
```

Default B=5 `create_index` built successfully. Its dynamic plan is:

```text
default_b5 = 64:11,192:7,320:5,320:3,64:0
```

This matters for guard choice: unlike the B=4 conservative filtered sweep, the B=5 default plan naturally has a 64-dimensional zero tail. Therefore, using the B=4 `--min-zero-tail-dim 128` rule would filter out the buildable default plan. For B=5, I kept the same safety intent but allowed 64-dimensional tails.

## 2. Guarded Sweep

Sweep command:

```bash
python script/sweep_boundary_plan.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 5 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v2_guarded_sweep_2026_07_03
```

Guard policy:

| guard | value | reason |
|---|---:|---|
| minimum positive bitwidth | 2 | remove 1-bit internal/non-final risk |
| minimum nonempty zero tail | 64 dims | allow the buildable B=5 default shape |
| maximum segments | 6 | avoid overly fragmented plans |
| maximum positive segment width | 384 dims | avoid very broad low-bit positive segments |
| exclude non-final 1-bit | true | remove the known unsafe shape class |

Raw local outputs:

```text
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v2_guarded_sweep_2026_07_03.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v2_guarded_sweep_2026_07_03.unique.csv
/tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v2_guarded_sweep_2026_07_03.summary.json
```

Sweep summary:

| metric | value |
|---|---:|
| all configs | 560 |
| feasible configs | 374 |
| infeasible configs | 186 |
| all unique plans | 16 |
| feasible unique plans | 9 |

## 3. Filtered Unique Plans

Top filtered unique plans by frequency:

| rank | configs | plan | objective reduction | comment |
|---:|---:|---|---:|---|
| 0 | 154 | `64:10,192:8,256:5,384:3,64:0` | 0.038388 | frequency leader; conservative tail-drop plan |
| 1 | 86 | `128:10,256:6,320:4,256:2` | 0.046222 | 4-seg no-tail plan; evaluates strongly |
| 2 | 47 | `64:10,64:7,128:7,320:5,320:3,64:0` | 0.092200 | split-front analogue of B=4 `v2_split64` |
| 3 | 28 | `64:10,128:8,192:6,192:4,320:3,64:0` | 0.037667 | more fragmented mid split |
| 4 | 20 | `64:9,64:8,128:7,320:5,320:3,64:0` | 0.073579 | lower first-block bit variant |

I evaluated ranks 0, 1, and 2 because they cover the three main shapes: frequency leader, compact no-tail plan, and split-front v2 analogue.

## 4. Evaluation

Raw local summaries:

```text
/tmp/saq-run/reports/gist_sample100k_B5_guarded_candidates_qps.csv
/tmp/saq-run/reports/gist_sample100k_B5_guarded_candidates_summary.csv
```

Aggregate comparison:

| name | plan | R@100 np20 | np50 | np100 | np200 | np400 | QPS np200 | err_tot_avg | err_tot_max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| default_b5 | `64:11,192:7,320:5,320:3,64:0` | 0.758330 | 0.927440 | 0.982540 | 0.993370 | 0.993740 | 9143.6 | 0.000246590 | 0.003495150 |
| b5_rank0 | `64:10,192:8,256:5,384:3,64:0` | 0.758050 | 0.927130 | 0.982290 | 0.993440 | 0.993840 | 9097.6 | 0.000238877 | 0.003862670 |
| b5_rank1 | `128:10,256:6,320:4,256:2` | 0.759500 | 0.928660 | 0.983490 | 0.994450 | 0.994820 | 10369.7 | 0.000256324 | 0.004334580 |
| b5_rank2 | `64:10,64:7,128:7,320:5,320:3,64:0` | 0.759440 | 0.928760 | 0.983510 | 0.994410 | 0.994790 | 8415.8 | 0.000260552 | 0.004315540 |

## 5. Readout

B=5 does show a positive guarded-v2 signal, but the best shape is different from B=4.

`b5_rank1` is the strongest practical candidate:

```text
b5_rank1 = 128:10,256:6,320:4,256:2
```

Compared with default B=5:

| metric | delta |
|---|---:|
| R@100 np20 | +0.001170 |
| R@100 np50 | +0.001220 |
| R@100 np100 | +0.000950 |
| R@100 np200 | +0.001080 |
| R@100 np400 | +0.001080 |
| QPS np200 | +13.4% |
| err_tot_avg | +0.000009734 |

This is a clear recall/QPS improvement, with a small mean-error regression. The no-tail 4-segment shape appears to spend a small amount of capacity on the tail instead of dropping the last 64 dimensions, and that helps recall at all nprobe values.

`b5_rank2` is the closest analogue to B=4 `v2_split64`, but it is not the best B=5 tradeoff: recall is close to `b5_rank1`, mean error is worse, and QPS is much lower because it uses more segments.

`b5_rank0` is the low-mean-error candidate: it improves mean relative error versus default, but recall gains are tiny and QPS is essentially unchanged. It is useful as an error-oriented contrast, not as the main candidate.

## 6. Decision

The B=5 experiment supports continuing the guarded boundary-aware direction. It also shows that the best plan shape can change with bit budget:

```text
B=4 best automatic candidate: 64:9,64:7,128:6,320:4,256:2,128:0
B=5 best evaluated candidate: 128:10,256:6,320:4,256:2
```

The next most useful step is not another B=5 candidate. It is either:

1. a per-query/segment attribution review of `b5_rank1`, to understand why the no-tail plan improves recall while slightly worsening mean error; or
2. a guarded sweep on another dataset or B value to see whether the no-tail pattern is B=5-specific or a broader high-bit behavior.

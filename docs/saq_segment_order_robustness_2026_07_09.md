# SAQ Segment-Order Robustness Evidence

## Purpose

This note extends the segment-order counterfactual replay from nprobe=200 to
nprobe=160 and nprobe=240 on GIST sample100k K512 B=4. The goal is to decide
whether simple query-unaware segment reordering should continue as a
search-procedure method direction.

The answer is no for the tested setting.

## Setup

```text
dataset = gist_sample100k
K = 512
B = 4
PCA = true
plan = SAQ default variance plan
plan shape = 64x11_192x6_320x4_256x2_128x0
top-k = 100
queries = 1000
safe search semantics = finite valid-lane block-min replay
```

Evaluated nprobe values:

```text
160, 200, 240
```

Evaluated orders:

```text
pca, reverse, bit_desc, dim_desc, cost_asc, risk_per_cost_desc
```

Local output files:

```text
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_segment_order_np160.csv
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_segment_order_full.csv
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_segment_order_np240.csv
```

## Result Summary

The table reports deltas relative to `pca`, the default SAQ segment order.

### nprobe = 160

| order | recall delta | fast-call delta | accurate-call delta | fast-bit delta | accurate-bit delta |
|---|---:|---:|---:|---:|---:|
| `reverse` | -0.00100 | +37.46% | +165.30% | +53.23% | +135.67% |
| `bit_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |
| `dim_desc` | -0.00099 | +37.45% | +146.03% | +53.21% | +136.87% |
| `cost_asc` | +0.00002 | +1.27% | +0.49% | +1.64% | +0.09% |
| `risk_per_cost_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |

### nprobe = 200

| order | recall delta | fast-call delta | accurate-call delta | fast-bit delta | accurate-bit delta |
|---|---:|---:|---:|---:|---:|
| `reverse` | -0.00092 | +47.41% | +167.81% | +69.06% | +137.68% |
| `bit_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |
| `dim_desc` | -0.00091 | +47.39% | +148.07% | +69.04% | +138.91% |
| `cost_asc` | +0.00002 | +1.34% | +0.48% | +1.78% | +0.09% |
| `risk_per_cost_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |

### nprobe = 240

| order | recall delta | fast-call delta | accurate-call delta | fast-bit delta | accurate-bit delta |
|---|---:|---:|---:|---:|---:|
| `reverse` | -0.00089 | +57.39% | +169.11% | +85.75% | +138.71% |
| `bit_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |
| `dim_desc` | -0.00088 | +57.36% | +149.11% | +85.71% | +139.96% |
| `cost_asc` | +0.00002 | +1.37% | +0.48% | +1.87% | +0.08% |
| `risk_per_cost_desc` | 0.00000 | 0.00% | 0.00% | 0.00% | 0.00% |

## Interpretation

The result is stable across nprobe:

- `bit_desc` and `risk_per_cost_desc` collapse to the same order as `pca` on
  this default plan.
- `reverse` and `dim_desc` are consistently worse: they increase fast-stage
  work by 37-57% and accurate-stage work by 146-169%, while losing recall.
- `cost_asc` has a tiny recall increase of 0.00002 in replay, but it also
  increases fast-stage work by about 1.3-1.4% and does not reduce accurate
  work.

The evidence does not support a simple segment-order method. The default SAQ
plan already scans the high-bit, high-variance PCA segments first, and that
order is tied for the lowest observed work among the tested hyperparameter-free
orders.

## Decision

Stop the simple segment-order branch as a main method direction.

This is useful limitation evidence:

```text
SAQ's default PCA/bit order is already strong for this progressive search path;
simple query-unaware reordering does not expose a low-overhead improvement.
```

The broader search-procedure direction should not continue through fixed
segment reorder rules. If it continues, it needs a different mechanism, such as
a provably safe bound refinement or a stronger analysis of why the current
variance stage is almost inactive. Otherwise the direction risks becoming
implementation-level tuning rather than a database research contribution.

## Commands

```bash
/rwproject/kdd-db/kluaq/saq/bin/profile_segment_order \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=160 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_segment_order_np160.csv

/rwproject/kdd-db/kluaq/saq/bin/profile_segment_order \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=240 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_segment_order_np240.csv
```

Commands were run from:

```text
/tmp/saq-run
```

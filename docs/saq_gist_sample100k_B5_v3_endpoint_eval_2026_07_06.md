# GIST Sample100k B=5 v3 Recall-Endpoint Evaluation

Date: 2026-07-06

## 1. Purpose

The B=5 planner-v3 sweep selected this plan as the offline recall-risk endpoint:

```text
v3_endpoint = 64:9,64:8,128:7,320:5,320:3,64:0
```

This note builds and evaluates that endpoint under the corrected safe-searcher
protocol. The goal is to check whether the offline recall-risk endpoint beats
the measured B=5 middle point:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

## 2. Setup

Configuration:

```text
dataset = gist_sample100k
K = 512
B = 5
PCA = true
metric = R@100 over sample-specific top1000 groundtruth
searcher = -searcher_safe_block_min_mode=2
nprobe = 20,50,100,200,400
QPS = nprobe 200, top100, 24 threads
```

Build command:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -seg_plan=64:9,64:8,128:7,320:5,320:3,64:0 \
  -logtostderr=1
```

Build result:

| artifact | value |
|---|---:|
| index path | `/tmp/saq-run/data/gist_sample100k/ivf512_b5_caq_adj_seg_plan64x9_64x8_128x7_320x5_320x3_64x0_pca.index` |
| index size | 71 MB |
| indexing time | 0.328s |

## 3. Recall Result

Safe-searcher R@100 versus default B=5:

| nprobe | default R@100 | v3 endpoint R@100 | delta | better q | equal q | worse q | worst query | worst delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.75972 | 0.75979 | +0.00007 | 14 | 978 | 8 | 9 | -1 | 8 | 15 |
| 50 | 0.92900 | 0.92916 | +0.00016 | 60 | 896 | 44 | 381 | -2 | 52 | 68 |
| 100 | 0.98396 | 0.98370 | -0.00026 | 120 | 734 | 146 | 120 | -2 | 202 | 176 |
| 200 | 0.99478 | 0.99470 | -0.00008 | 179 | 633 | 188 | 120 | -2 | 302 | 294 |
| 400 | 0.99516 | 0.99508 | -0.00008 | 183 | 625 | 192 | 120 | -2 | 310 | 302 |

At nprobe 200, the delta-hit distribution is:

| delta hits | query count |
|---:|---:|
| -2 | 6 |
| -1 | 182 |
| 0 | 633 |
| +1 | 172 |
| +2 | 7 |

Representative nprobe-200 extremes:

| query | default hits | custom hits | delta | lost GT | gained GT | note |
|---:|---:|---:|---:|---:|---:|---|
| 120 | 100 | 98 | -2 | 2 | 0 | lost GT ranks 97 and 99 |
| 181 | 98 | 100 | +2 | 0 | 2 | gained GT ranks 93 and 99 |

The changes are still mostly boundary-level:

```text
nprobe 200 lost events  = 302, mean lost min-rank = 97.41
nprobe 200 gained events = 294, mean gained min-rank = 96.89
```

However, the net effect is negative at the high-recall operating points.

## 4. QPS Result

Single local QPS run at nprobe 200, top100, 24 threads:

| plan | R@100 np200 | QPS | avg ms | QPS ratio vs default |
|---|---:|---:|---:|---:|
| default B=5 | 0.99478 | 9099.52 | 2.6376 | 1.000x |
| `b5_rank0` | 0.99521 | 9032.36 | 2.6573 | 0.993x |
| `b5_rank1` | 0.99476 | 10322.03 | 2.3252 | 1.134x |
| `v3_endpoint` | 0.99470 | 8569.77 | 2.8006 | 0.942x |

The measured speed is consistent with the v3 speed proxy: this is a split-front
five-nonzero-segment plan, so it is slower than default, slower than `b5_rank0`,
and much slower than the no-tail speed endpoint `b5_rank1`.

## 5. Readout

The v3 offline recall-risk endpoint is a false positive under corrected
safe-searcher measurement.

It does not beat `b5_rank0`:

```text
np200:
v3_endpoint = 0.99470
b5_rank0    = 0.99521
delta       = -0.00051
```

It also does not beat default at the main high-recall nprobe values:

```text
np100: -0.00026
np200: -0.00008
np400: -0.00008
```

And it is not a speed candidate:

```text
QPS ratio vs default = 0.942x
QPS ratio vs b5_rank0 = 0.949x
QPS ratio vs b5_rank1 = 0.830x
```

## 6. Decision

Keep `b5_rank0` as the measured B=5 recall/middle candidate:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

Do not promote the v3 split-front endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

The v3 Pareto interpretation should be updated as:

| role | plan | measured status |
|---|---|---|
| offline recall-risk endpoint | `64:9,64:8,128:7,320:5,320:3,64:0` | proxy false positive |
| measured B=5 middle/recall point | `64:10,192:8,256:5,384:3,64:0` | keep |
| measured B=5 speed point | `128:10,256:6,320:4,256:2` | speed-only, not recall-improving |

## 7. Artifacts

Index:

```text
/tmp/saq-run/data/gist_sample100k/ivf512_b5_caq_adj_seg_plan64x9_64x8_128x7_320x5_320x3_64x0_pca.index
```

Recall compare CSVs:

```text
/tmp/saq-run/reports/gist_sample100k_B5_v3_endpoint_safeblockminsimd_compare_np20_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_v3_endpoint_safeblockminsimd_compare_np50_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_v3_endpoint_safeblockminsimd_compare_np100_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_v3_endpoint_safeblockminsimd_compare_np200_top100.csv
/tmp/saq-run/reports/gist_sample100k_B5_v3_endpoint_safeblockminsimd_compare_np400_top100.csv
```

QPS:

```text
/tmp/saq-run/results/saq/qps_gist_sample100k_ivf512_b5_caq_adj_seg_plan64x9_64x8_128x7_320x5_320x3_64x0_pca_th24_np200_sm4_safeblockminsimd.csv
```


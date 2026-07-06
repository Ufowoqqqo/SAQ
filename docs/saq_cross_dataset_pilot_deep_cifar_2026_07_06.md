# Cross-Dataset Pilot: DEEP1M Sample And CIFAR60K

Date: 2026-07-06

This note records a first non-GIST pilot for the current query-unaware SAQ
follow-up. The goal is to check whether the boundary-aware planner can find
useful plans beyond GIST, and whether failures/successes give more examples for
a general plan-shape method.

## 1. Scope

This is a pilot, not a full SAQ-paper reproduction.

Datasets tested:

| dataset | rows | dim | K | B | metric | status |
|---|---:|---:|---:|---:|---|---|
| `deep1M_sample100k` | 100,000 | 256 | 512 | 4, 5 | R@100 | SAQ-paper dataset sampled locally |
| `cifar60k` | 60,000 | 512 | 512 | 4 | R@10 | local non-SAQ-paper dataset, GT depth only 10 |

The DEEP pilot uses a 100k prefix and sample-specific groundtruth, so it is not
the official full DEEP1M/K4096 setting. CIFAR60K is included because it is small
and higher-dimensional enough to expose richer segmentation behavior quickly.

All measured search results used corrected safe block-min mode:

```text
-searcher_safe_block_min_mode=2
```

## 2. DEEP1M Sample

Preparation:

```bash
python script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_query.fvecs \
  --output-dir /tmp/saq-run/data/deep1M_sample100k \
  --dataset deep1M_sample100k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Sample summary:

```text
N = 100000
D = 256
K = 512
variance_top1_share = 0.0893269
variance_top64_share = 0.875186
```

The top 64 PCA dimensions explain about 87.5% of variance, so this dataset is
much more concentrated than GIST.

Sample-specific GT:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset deep1M_sample100k \
  -K 512 \
  -B 4 \
  -enable_PCA=true \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=32 \
  -gt_overwrite=true \
  -logtostderr=1
```

### Default Plans

| B | SAQ default plan |
|---:|---|
| 4 | `64:6,192:3` |
| 5 | `64:7,192:4` |

Both defaults are simple two-segment plans with no zero tail.

### Planner Readout

For B=4, v3 generated a raw endpoint:

```text
128:6,128:1
```

It lowered the offline boundary cost, but it has a positive 1-bit segment and
segfaulted during `create_index`. This reinforces the existing feasibility
guard against low-bit positive segments.

For B=5, v3 and v2 both produced the same non-default candidate:

```text
128:7,128:2
```

It is buildable, but the conservative guard rejects it because both pair-level
soft inversion and weighted ratio proxies are worse than default.

### B=5 Measured Result

Candidate:

```text
custom = 128:7,128:2
default = 64:7,192:4
```

Recall:

| nprobe | default R@100 | custom R@100 | delta |
|---:|---:|---:|---:|
| 20 | 0.86011 | 0.85989 | -0.00022 |
| 50 | 0.95180 | 0.95139 | -0.00041 |
| 100 | 0.97973 | 0.97929 | -0.00044 |
| 200 | 0.98670 | 0.98625 | -0.00045 |
| 400 | 0.98752 | 0.98710 | -0.00042 |

QPS at nprobe 200:

| plan | R@100 | QPS | QPS ratio |
|---|---:|---:|---:|
| default | 0.98670 | 28163.443 | 1.000x |
| `128:7,128:2` | 0.98625 | 30927.469 | 1.098x |

Interpretation:

`128:7,128:2` is a speed/recall tradeoff, not a strict improvement. This is a
useful negative example: when PCA variance is very concentrated and the default
plan is already compact, moving too much budget into the first 128 dimensions
can hurt boundary recall even if it improves speed.

## 3. CIFAR60K Pilot

Preparation:

```bash
python script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_query.fvecs \
  --groundtruth-input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs \
  --output-dir /tmp/saq-run/data/cifar60k \
  --dataset cifar60k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Sample summary:

```text
N = 60000
D = 512
K = 512
variance_top1_share = 0.142589
variance_top64_share = 0.785318
groundtruth depth = 10
```

Because the available GT depth is 10, this pilot reports R@10.

Default B=4 plan:

```text
default = 64:9,192:5,128:3,128:0
```

The v3 sweep produced six unique plans. Three representative candidates were
built and evaluated:

| role | plan |
|---|---|
| raw recall endpoint | `64:6,192:5,192:3,64:0` |
| speed endpoint | `128:7,256:4,128:0` |
| near-default middle | `128:7,128:5,128:3,128:0` |

### CIFAR60K Measured Result

Recall:

| plan | np50 | np100 | np200 | np400 |
|---|---:|---:|---:|---:|
| default | 0.9425 | 0.9724 | 0.9781 | 0.9790 |
| raw recall endpoint | 0.9358 | 0.9643 | 0.9704 | 0.9713 |
| speed endpoint | 0.9419 | 0.9725 | 0.9785 | 0.9797 |
| near-default middle | 0.9429 | 0.9738 | 0.9801 | 0.9812 |

Delta vs default:

| plan | np50 | np100 | np200 | np400 |
|---|---:|---:|---:|---:|
| raw recall endpoint | -0.0067 | -0.0081 | -0.0077 | -0.0077 |
| speed endpoint | -0.0006 | +0.0001 | +0.0004 | +0.0007 |
| near-default middle | +0.0004 | +0.0014 | +0.0020 | +0.0022 |

QPS at nprobe 200:

| plan | R@10 | QPS | QPS ratio |
|---|---:|---:|---:|
| default | 0.9781 | 24472.672 | 1.000x |
| raw recall endpoint | 0.9704 | 23514.180 | 0.961x |
| speed endpoint | 0.9785 | 26295.217 | 1.074x |
| near-default middle | 0.9801 | 25368.984 | 1.037x |

The near-default middle plan is the strongest CIFAR pilot result:

```text
128:7,128:5,128:3,128:0
```

It improves both R@10 and QPS over the default plan in this local K512 setup.

## 4. Shape Takeaways

The new pilots add two useful examples.

DEEP sample negative example:

```text
default = 64:7,192:4
custom  = 128:7,128:2
```

Broadening the first segment and weakening the tail improves speed but loses
recall. This suggests that for low-dimensional data with highly concentrated PCA
variance, the SAQ default may already be close to a good compact plan.

CIFAR positive example:

```text
default = 64:9,192:5,128:3,128:0
middle  = 128:7,128:5,128:3,128:0
```

The successful shape does not aggressively lower the middle/tail. Instead, it
softens the over-concentrated first 64 dimensions and makes the head segment
wider while preserving a 128-dimensional zero tail.

This is consistent with the GIST observation that putting too many bits only
into the first 64 PCA dimensions is not always best for ANN boundary behavior.
However, the aggressive CIFAR raw endpoint:

```text
64:6,192:5,192:3,64:0
```

is much worse. So the useful rule is not simply "reduce head bits"; it is closer
to:

```text
avoid over-concentrating bits in only the first 64 dimensions, but keep enough
head precision and preserve a stable tail policy.
```

## 5. Immediate Next Steps

1. Run the same CIFAR candidate generation with a stricter middle-shape selector
   that can prefer `128:7,128:5,128:3,128:0`-like plans over raw recall-risk
   endpoints.
2. Re-run DEEP on a fuller setting, ideally full DEEP1M with official GT, before
   concluding that DEEP has no strict improvement.
3. Add another high-dimensional local dataset such as `nuswide` or `msong` to
   collect more shape examples.
4. For a SAQ-paper-aligned validation story, obtain or prepare OpenAI-1536 /
   MSMARCO artifacts if available; otherwise DEEP is the only non-GIST
   SAQ-paper dataset currently present locally.

## 6. Artifacts

DEEP:

```text
/tmp/saq-run/data/deep1M_sample100k
/tmp/saq-run/reports/deep1M_sample100k_K512_B4_boundary_v3_sweep_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_K512_B5_boundary_v3_sweep_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_K512_B5_boundary_v2_filtered_sweep_2026_07_06.*
/tmp/saq-run/reports/deep1M_sample100k_B5_endpoint_compare_np*_top100.csv
/tmp/saq-run/results/saq/qps_deep1M_sample100k_ivf512_b5_caq_adj_seg*_pca_th24_np200_sm4_safeblockminsimd.csv
```

CIFAR:

```text
/tmp/saq-run/data/cifar60k
/tmp/saq-run/reports/cifar60k_K512_B4_boundary_v3_sweep_2026_07_06.*
/tmp/saq-run/reports/cifar60k_B4_*_compare_np*_top10.csv
/tmp/saq-run/results/saq/qps_cifar60k_ivf512_b4_caq_adj_seg*_pca_th24_np200_sm4_safeblockminsimd_top10.csv
```

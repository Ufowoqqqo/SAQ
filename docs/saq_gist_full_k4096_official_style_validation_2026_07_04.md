# GIST Full K4096 Official-Style Validation

Date: 2026-07-04

## 1. Purpose

The full-GIST K512 validation showed that the B=4 candidates from the guarded planner remain positive under original-space R@100:

```text
v2_split64   = 64:9,64:7,128:6,320:4,256:2,128:0
filtered_new = 64:10,320:6,384:3,192:0
```

This note checks whether that conclusion survives a more official-style IVF granularity:

```text
dataset = full GIST, 1M base / 1K query / 960d
IVF K = 4096
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
```

This is still not a full official reproduction because the K4096 centroids are prepared by the local NumPy fallback rather than FAISS. The important step here is feasibility plus cross-granularity validation: do the same B=4 plan shapes remain useful when K increases from 512 to 4096?

## 2. K4096 Preparation

Instead of recomputing PCA, we reused the existing full-dimensional PCA artifact:

```text
/tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs
```

Then we generated K4096 IVF artifacts with:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_ivf_from_pca.py \
  --base-pca /tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs \
  --output-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 1024 \
  --seed 0
```

Preparation summary:

| metric | value |
|---|---:|
| K | 4096 |
| clustering dimensions | first 64 PCA dims |
| Lloyd iterations | 4 |
| empty clusters | 0 |
| min cluster size | 1 |
| median cluster size | 230 |
| p90 cluster size | 383.5 |
| max cluster size | 1059 |

Generated artifacts:

```text
/tmp/saq-run/data/gist_full/gist_full_centroid_4096_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_cluster_id_4096.ivecs
/tmp/saq-run/data/gist_full/gist_full_k4096_pca_ivf_summary.json
```

The cluster-size distribution is much finer than K512 and has no empty cells, so the fallback K4096 setup is usable for searcher validation.

## 3. Built Indexes

All indexes use B=4, PCA-space data, original-space top100 GT for evaluation, and safe searcher mode 2.

| name | plan | build time |
|---|---|---:|
| default | `64:11,192:6,320:4,256:2,128:0` | 2.76s |
| `v2_split64` | `64:9,64:7,128:6,320:4,256:2,128:0` | 2.75s |
| `filtered_new` | `64:10,320:6,384:3,192:0` | 2.83s |

Index artifacts:

```text
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_pca.index
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca.index
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca.index
```

## 4. R@100 Results

Evaluation used:

```text
nprobe = 50, 100, 200, 400, 800
QPS point = nprobe 800, 24 threads
GT = /tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs
```

| name | R@100 np50 | np100 | np200 | np400 | np800 | delta np800 | QPS np800 | QPS ratio | better/equal/worse at np800 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default | 0.74477 | 0.86604 | 0.94469 | 0.97999 | 0.98845 | 0.00000 | 1013.6 | 1.000x | 0/1000/0 |
| `v2_split64` | 0.74498 | 0.86633 | 0.94526 | 0.98097 | 0.98975 | +0.00130 | 918.4 | 0.906x | 310/481/209 |
| `filtered_new` | 0.74481 | 0.86609 | 0.94509 | 0.98097 | 0.98948 | +0.00103 | 1092.3 | 1.078x | 295/496/209 |

Full deltas:

| name | delta np50 | np100 | np200 | np400 | np800 |
|---|---:|---:|---:|---:|---:|
| `v2_split64` | +0.00021 | +0.00029 | +0.00057 | +0.00098 | +0.00130 |
| `filtered_new` | +0.00004 | +0.00005 | +0.00040 | +0.00098 | +0.00103 |

Readout:

- `v2_split64` remains the strongest recall candidate at K4096, especially in the high-recall region.
- `filtered_new` remains the practical Pareto candidate: it improves R@100 at np800 by `+0.00103` and is `1.078x` faster than default at the same nprobe.
- The B=4 conclusion from K512 is not an artifact of coarse IVF granularity.

## 5. Cross-Granularity Decision

| candidate | K512 original R@100 | K4096 original R@100 | decision |
|---|---|---|---|
| `v2_split64` | best B=4 recall, slower | best B=4 recall, slower | keep as recall-stress candidate |
| `filtered_new` | positive recall and faster | positive recall and faster | keep as practical candidate |

The stronger next claim is now:

```text
On full GIST, under both K512 and K4096 fallback IVF settings, the B=4
filtered_new plan improves R@100 while increasing QPS, and v2_split64 gives
the stronger recall gain at a QPS cost.
```

## 6. Artifacts

Evaluation summaries:

```text
/tmp/saq-run/reports/gist_full_k4096_original_top100_b4_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_full_k4096_original_top100_b4_compare_rows_2026_07_04.csv
/tmp/saq-run/reports/gist_full_k4096_original_top100_b4_leaderboard_2026_07_04.json
```

Per-query compare files:

```text
/tmp/saq-run/reports/gist_full_k4096_original_top100_B4_v2_split64_safeblockminsimd_compare_np{50,100,200,400,800}_top100.csv
/tmp/saq-run/reports/gist_full_k4096_original_top100_B4_filtered_new_safeblockminsimd_compare_np{50,100,200,400,800}_top100.csv
```

QPS logs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
```

## 7. Next Step

The K4096 feasibility and B=4 rerun are complete. The next highest-signal step is to explain the mechanism behind `filtered_new` on full GIST K4096: it is both faster and slightly more accurate, so we should audit segment-level refinement/pruning behavior at np800 to see where the speedup comes from and whether the recall gain is tied to fewer zero-bit tail interactions or a different early-refinement pattern.

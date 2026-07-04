# GIST Full K512 Safe-Searcher Validation

Date: 2026-07-04

## 1. Purpose

The corrected planner leaderboard on `gist_sample100k` identified three candidates worth validating beyond the 100k sample:

```text
B=4 v2_split64   = 64:9,64:7,128:6,320:4,256:2,128:0
B=4 filtered_new = 64:10,320:6,384:3,192:0
B=5 b5_rank0     = 64:10,192:8,256:5,384:3,64:0
```

This note validates those candidates on full GIST with the corrected safe searcher:

```text
-searcher_safe_block_min_mode=2
```

It contains three complementary checks:

1. Official top10 GIST groundtruth, reported as R@10.
2. Newly computed PCA-space exact top100 groundtruth, used as an intermediate R@100 check.
3. Newly computed original-space exact top100 groundtruth, used as the final R@100 check.

## 2. Scope and Groundtruth

This is a full-N validation, but not a full official reproduction.

| item | value |
|---|---|
| base vectors | 1,000,000 |
| queries | 1,000 |
| dimension | 960 |
| IVF clusters | K=512 |
| PCA/IVF builder | NumPy fallback, not FAISS |
| searcher safety mode | `-searcher_safe_block_min_mode=2` |

The official local GIST GT file is:

```text
/rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs
```

It has shape `1000 x 10`, so the first validation uses official R@10.

For R@100, we first computed a top100 file over the prepared PCA-space full-GIST data:

```text
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100.ivecs
```

Then we computed an original-space top100 file directly from the raw GIST base/query vectors:

```text
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs
```

Both files have shape `1000 x 100`. The final R@100 table below uses the original-space top100 file. The PCA-space file is still useful as a consistency check because this pipeline keeps all 960 PCA dimensions, so the transform should preserve L2 neighborhoods except for floating-point/tie-order effects.

Sanity check against the official top10:

| check | result |
|---|---:|
| exact ordered top10 match | 878 / 1000 queries |
| computed first-10 set match with official top10 | 986 / 1000 queries |
| official top10 covered by original-space top100 | 1000 / 1000 queries |

PCA-space top100 vs original-space top100:

| check | result |
|---|---:|
| exact ordered top100 match | 992 / 1000 queries |
| top100 set match | 1000 / 1000 queries |

The official top10 order mismatch is small but real and appears to be an ordering/tie/numerical issue: every official top10 neighbor is present in the computed original-space top100. Since PCA-space and original-space top100 sets match exactly for all queries, the previous PCA-space R@100 conclusion is not changed by the original-space rerun.

## 3. Preparation

The fallback preparation script supports query PCA projection and GT copying:

```text
script/prepare_sampled_pca_ivf.py
```

Command:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs \
  --groundtruth-input /rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs \
  --output-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --sample-size 1000000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Preparation summary:

| metric | value |
|---|---:|
| sample size | 1,000,000 |
| K | 512 |
| empty clusters | 0 |
| min cluster size | 85 |
| median cluster size | 1842 |
| p90 cluster size | 2933.5 |
| max cluster size | 6822 |
| PCA top1 variance share | 0.2003 |
| PCA top64 variance share | 0.7740 |

Generated dataset directory:

```text
/tmp/saq-run/data/gist_full
```

The GT generator was made configurable so that we can compute top100 without overwriting official-style top10 files by accident:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset gist_full \
  -enable_PCA=true \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=24 \
  -gt_output=/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100.ivecs \
  -gt_overwrite=true \
  -logtostderr=1
```

Original-space top100 command:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset gist_raw \
  -enable_PCA=false \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=24 \
  -gt_output=/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs \
  -gt_overwrite=true \
  -logtostderr=1
```

Here `gist_raw` is a temporary `/tmp/saq-run/data/gist_raw` dataset mapping whose base/query files symlink to the raw local GIST files under `/rwproject/kdd-db/kluaq/dataset/gist/`.

For the R@100 run, the original copied top10 file was preserved as:

```text
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top10_official.ivecs
```

and the dataset-default GT path was switched to the computed original-space top100:

```text
/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs
```

## 4. Candidate Indexes

Built indexes:

| budget | name | plan |
|---:|---|---|
| B=4 | default | `64:11,192:6,320:4,256:2,128:0` |
| B=4 | `v2_split64` | `64:9,64:7,128:6,320:4,256:2,128:0` |
| B=4 | `filtered_new` | `64:10,320:6,384:3,192:0` |
| B=5 | default | `64:11,192:7,320:5,320:3,64:0` |
| B=5 | `b5_rank0` | `64:10,192:8,256:5,384:3,64:0` |

## 5. Official Full-GIST R@10

All rows use safe searcher mode 2 and official top10 GT.

### B=4 R@10

| name | R@10 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default B=4 | 0.8779 | 0.9592 | 0.9775 | 0.9795 | 0.9796 | 0.0000 | 1270.9 | 1.000x | n/a |
| `v2_split64` | 0.8789 | 0.9604 | 0.9794 | 0.9815 | 0.9816 | +0.0020 | 1090.0 | 0.858x | 748:-2 |
| `filtered_new` | 0.8785 | 0.9605 | 0.9783 | 0.9805 | 0.9806 | +0.0010 | 1382.5 | 1.088x | 553:-2 |

Readout:

- `v2_split64` generalizes as the strongest B=4 recall candidate: `+0.0020` R@10 at np200.
- `filtered_new` also generalizes and remains the better speed/recall tradeoff: `+0.0010` R@10 and `1.088x` QPS.
- The sample100k corrected B=4 story survives full-N validation.

### B=5 R@10

| name | R@10 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default B=5 | 0.8820 | 0.9651 | 0.9843 | 0.9865 | 0.9866 | 0.0000 | 1232.3 | 1.000x | n/a |
| `b5_rank0` | 0.8812 | 0.9643 | 0.9845 | 0.9866 | 0.9867 | +0.0001 | 1214.8 | 0.986x | 22:-1 |

R@10 readout:

- `b5_rank0` does not fail, but the R@10 signal is weak.
- At low nprobe, `b5_rank0` is slightly worse: `-0.0008` at np20/np50.
- At np100/200/400, it is only marginally positive.

## 6. Original-Space Full-GIST R@100

All rows use safe searcher mode 2 and the computed original-space top100 GT. The recall values match the earlier PCA-space R@100 run because the PCA-space and original-space top100 sets are identical for all queries.

### B=4 R@100

| name | R@100 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | better/equal/worse at np200 | worst/best query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| default B=4 | 0.83615 | 0.95397 | 0.98444 | 0.98897 | 0.98904 | 0.00000 | 920.1 | 1.000x | 0/1000/0 | n/a |
| `v2_split64` | 0.83637 | 0.95480 | 0.98587 | 0.99049 | 0.99058 | +0.00152 | 813.2 | 0.884x | 336/446/218 | q397:-3 / q62:+3 |
| `filtered_new` | 0.83601 | 0.95441 | 0.98528 | 0.98998 | 0.99007 | +0.00101 | 995.5 | 1.082x | 309/463/228 | q715:-3 / q150:+3 |

R@100 readout:

- `v2_split64` remains the best B=4 recall candidate: `+0.00152` at np200 and `+0.00154` at np400.
- `filtered_new` remains the Pareto speed/recall candidate: `+0.00101` at np200 with `1.082x` QPS.
- R@100 reinforces the B=4 conclusion from R@10 rather than weakening it.

### B=5 R@100

| name | R@100 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | better/equal/worse at np200 | worst/best query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| default B=5 | 0.83657 | 0.95622 | 0.98870 | 0.99377 | 0.99389 | 0.00000 | 884.1 | 1.000x | 0/1000/0 | n/a |
| `b5_rank0` | 0.83668 | 0.95649 | 0.98923 | 0.99428 | 0.99439 | +0.00051 | 863.4 | 0.977x | 215/609/176 | q463:-3 / q4:+2 |

R@100 readout:

- `b5_rank0` is more positive under R@100 than under R@10: `+0.00051` at np200 and `+0.00050` at np400.
- The gain is smaller than the B=4 candidates and comes with a slight QPS cost.
- This upgrades `b5_rank0` from "near tie under R@10" to "modest positive under R@100", but it is still lower priority than the B=4 candidates.

## 7. Cross-Scale Decision

| candidate | sample100k corrected result | full GIST K512 R@10 | full GIST K512 original R@100 | decision |
|---|---|---|---|---|
| B=4 `v2_split64` | best B=4 recall | still best B=4 recall | still best B=4 recall | keep as recall candidate |
| B=4 `filtered_new` | balanced speed/recall | positive and faster | positive and faster | keep as Pareto candidate |
| B=5 `b5_rank0` | corrected B=5 recall winner | near tie with default | modest positive, slight QPS cost | keep, but lower priority |

The main validated direction remains B=4:

- `v2_split64` is the recall-oriented plan.
- `filtered_new` is the speed/recall plan and is currently the more practical candidate.

For B=5, `b5_rank0` is not invalidated, but the cross-scale signal is weaker and should not drive the next phase by itself.

## 8. Artifacts

Prepared full-GIST K512 artifacts:

```text
/tmp/saq-run/data/gist_full/gist_full_sampled_pca_ivf_summary.json
/tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_query_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top10_official.ivecs
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100.ivecs
/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs
/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs
```

Official R@10 summaries:

```text
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_compare_rows_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_leaderboard_2026_07_04.json
```

Original-space R@100 summaries:

```text
/tmp/saq-run/reports/gist_full_safe_corrected_minset_original_top100_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_original_top100_compare_rows_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_original_top100_leaderboard_2026_07_04.json
```

Earlier PCA-space R@100 summaries:

```text
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top100_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top100_compare_rows_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top100_leaderboard_2026_07_04.json
```

QPS logs:

```text
/tmp/saq-run/results/saq/qps_gist_full_*_top10_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_*_sm4_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_*_safeblockminsimd_original_top100.csv
```

## 9. Next Step

The original-space R@100 validation is complete. The highest-signal next step depends on which claim we want to strengthen:

1. If we want a system-scale SAQ setting, move from fallback K512 to a K4096/FAISS-style GIST pipeline. This follow-up is now completed for the fallback K4096 path in `docs/saq_gist_full_k4096_official_style_validation_2026_07_04.md`.
2. If we want robustness beyond GIST, repeat the guarded candidate validation on another higher-dimensional dataset.
3. If we want to understand why `filtered_new` is faster while still improving recall, run targeted segment/refinement attribution on full GIST for that plan.

Given the current evidence, the practical candidate to carry forward is B=4 `filtered_new`; the recall-stress candidate is B=4 `v2_split64`.

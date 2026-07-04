# GIST Full K512 Safe-Searcher Validation

Date: 2026-07-04

## 1. Purpose

The corrected planner leaderboard on `gist_sample100k` identified three candidates worth validating beyond the 100k sample:

```text
B=4 v2_split64  = 64:9,64:7,128:6,320:4,256:2,128:0
B=4 filtered_new = 64:10,320:6,384:3,192:0
B=5 b5_rank0   = 64:10,192:8,256:5,384:3,64:0
```

This note tests those candidates on full GIST with the corrected safe searcher:

```text
-searcher_safe_block_min_mode=2
```

## 2. Important Scope Limits

This is a full-N validation, not a full official reproduction.

| item | value |
|---|---|
| base vectors | 1,000,000 |
| queries | 1,000 |
| dimension | 960 |
| IVF clusters | K=512 |
| PCA/IVF builder | NumPy fallback, not FAISS |
| GT source | official GIST L2 groundtruth |
| GT depth | top10 only |
| metric | R@10 |

The official local GT file is:

```text
/rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs
```

It has shape `1000 x 10`, so this run uses R@10. A full R@100 comparison would require computing new exact top100/top1000 groundtruth for 1M base vectors.

## 3. Preparation

The fallback preparation script was extended to support query PCA projection and GT copying:

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

## 4. Candidate Indexes

Built indexes:

| budget | name | plan |
|---:|---|---|
| B=4 | default | `64:11,192:6,320:4,256:2,128:0` |
| B=4 | `v2_split64` | `64:9,64:7,128:6,320:4,256:2,128:0` |
| B=4 | `filtered_new` | `64:10,320:6,384:3,192:0` |
| B=5 | default | `64:11,192:7,320:5,320:3,64:0` |
| B=5 | `b5_rank0` | `64:10,192:8,256:5,384:3,64:0` |

## 5. B=4 Full-GIST R@10

All rows use safe searcher mode 2 and official top10 GT.

| name | R@10 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default B=4 | 0.8779 | 0.9592 | 0.9775 | 0.9795 | 0.9796 | 0.0000 | 1270.9 | 1.000x | n/a |
| `v2_split64` | 0.8789 | 0.9604 | 0.9794 | 0.9815 | 0.9816 | +0.0020 | 1090.0 | 0.858x | 748:-2 |
| `filtered_new` | 0.8785 | 0.9605 | 0.9783 | 0.9805 | 0.9806 | +0.0010 | 1382.5 | 1.088x | 553:-2 |

Readout:

- `v2_split64` generalizes as the strongest B=4 recall candidate: `+0.0020` R@10 at np200.
- `filtered_new` also generalizes and remains the better speed/recall tradeoff: `+0.0010` R@10 and `1.088x` QPS.
- The sample100k corrected B=4 story survives full-N validation.

## 6. B=5 Full-GIST R@10

| name | R@10 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default B=5 | 0.8820 | 0.9651 | 0.9843 | 0.9865 | 0.9866 | 0.0000 | 1232.3 | 1.000x | n/a |
| `b5_rank0` | 0.8812 | 0.9643 | 0.9845 | 0.9866 | 0.9867 | +0.0001 | 1214.8 | 0.986x | 22:-1 |

Readout:

- `b5_rank0` does not fail, but the full-GIST signal is much weaker than on `gist_sample100k`.
- At low nprobe, `b5_rank0` is slightly worse: `-0.0008` at np20/np50.
- At np100/200/400, it is only marginally positive: `+0.0001` to `+0.0002`.
- QPS is effectively tied/slightly lower than default.

So the corrected B=5 claim should be downgraded:

```text
On full GIST K512 R@10, b5_rank0 is not a strong improvement over default.
It remains a plausible candidate, but not a robust cross-scale win.
```

## 7. Cross-Scale Decision

| candidate | sample100k corrected result | full GIST K512 R@10 result | decision |
|---|---|---|---|
| B=4 `v2_split64` | best B=4 recall | still best B=4 recall, larger delta | keep as recall candidate |
| B=4 `filtered_new` | balanced speed/recall | still positive and faster | keep as Pareto candidate |
| B=5 `b5_rank0` | corrected B=5 recall winner | nearly tied with default | downgrade to tentative |

The main validated direction is B=4. The B=5 candidate is not strong enough on full GIST K512 R@10 to justify deeper optimization by itself.

## 8. Artifacts

Prepared full-GIST K512 artifacts:

```text
/tmp/saq-run/data/gist_full/gist_full_sampled_pca_ivf_summary.json
/tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_query_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs
```

Corrected evaluation summaries:

```text
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_compare_rows_2026_07_04.csv
/tmp/saq-run/reports/gist_full_safe_corrected_minset_top10_leaderboard_2026_07_04.json
```

QPS logs:

```text
/tmp/saq-run/results/saq/qps_gist_full_*_top10_safeblockminsimd.csv
```

## 9. Next Step

The next validation step should be one of:

1. Compute exact full-GIST top100/top1000 GT and rerun the same candidate set with R@100.
2. Enable a FAISS-backed or precomputed K4096 pipeline and repeat on official-style GIST IVF settings.
3. Move to another available high-dimensional dataset to check whether the B=4 `v2_split64` / `filtered_new` pattern is GIST-specific.

Given cost, the most pragmatic next step is to compute a smaller exact-GT extension first, for example full GIST top100 for a subset of queries or a larger sampled base such as 500k, before committing to a full 1M x 1000 exact top100 run.

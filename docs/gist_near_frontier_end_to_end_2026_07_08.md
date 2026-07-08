# GIST Near-Frontier End-to-End Check

## Question

Does a lower-cost point on the offline global segment-cost frontier translate
into a real recall/QPS benefit for SAQ search?

The offline frontier showed no lower-cost plan that dominates the SAQ default
at no worse variance-risk. The remaining weak signal was that GIST has nearby
frontier alternatives with only about 1% higher variance-risk. This note tests
whether that static tradeoff produces measurable search-time benefit.

## Setup

- dataset: `gist_full`
- index: IVF K4096
- bit budget: B=4
- vectors: PCA space
- evaluation: R@100 with `gist_full_groundtruth.ivecs`
- search: `-searcher_safe_block_min_mode=2`
- thread count: 24
- nprobe points: 100, 200, 400

The current branch binary was used to rebuild all three indexes. The custom
plans were injected through the explicit experimental flag
`-custom_quant_plan=dim:bits,...`.

## Plans

| label | plan | offline frontier role |
|---|---|---|
| default | `64:11,192:6,320:4,256:2,128:0` | SAQ default and exact minimum-risk plan |
| code-volume candidate | `64:10,128:7,192:5,192:3,256:2,128:0` | lowest-risk lower `total_code_bit_volume`; risk ratio 1.0100 |
| positive-dim candidate | `64:10,128:7,192:5,384:3,192:0` | lowest-risk lower `positive_dim`; risk ratio 1.0116 |

## Index Build

| label | build time (s) | index size (MiB) |
|---|---:|---:|
| default | 3.02949 | 569.95 |
| code-volume candidate | 2.81795 | 570.25 |
| positive-dim candidate | 2.92003 | 561.89 |

Build time differences are small and should not be over-interpreted. The more
important observation is that lower code volume does not necessarily reduce
index size, because the code-volume candidate adds one positive segment and
therefore extra segment metadata/factors.

## Recall/QPS

| nprobe | label | R@100 | QPS | QPS ratio vs default |
|---:|---|---:|---:|---:|
| 100 | default | 0.86604 | 4275.79 | 1.0000 |
| 100 | code-volume candidate | 0.86630 | 4031.72 | 0.9429 |
| 100 | positive-dim candidate | 0.86639 | 4212.68 | 0.9852 |
| 200 | default | 0.94469 | 2732.35 | 1.0000 |
| 200 | code-volume candidate | 0.94506 | 2503.10 | 0.9161 |
| 200 | positive-dim candidate | 0.94537 | 2673.65 | 0.9785 |
| 400 | default | 0.97999 | 1642.83 | 1.0000 |
| 400 | code-volume candidate | 0.98092 | 1499.40 | 0.9127 |
| 400 | positive-dim candidate | 0.98139 | 1620.92 | 0.9867 |

Both candidates slightly improve recall, but neither produces a QPS benefit.
The code-volume candidate is consistently slower, likely because it reduces bit
volume by splitting the plan into more positive segments. The positive-dim
candidate is closer to default speed and has a smaller index, but it is still
slower at all tested nprobe points.

## Interpretation

This is a negative result for the simplest single-global segment-cost-aware DP
hypothesis. A nearby static frontier point does not automatically translate into
better search efficiency. In this implementation, plan shape affects more than
raw dimensional or bit volume: segment count, per-segment estimator setup,
accurate-stage work, zero-tail placement, and pruning behavior all interact.

The result strengthens the stop condition from the offline frontier note. If a
method only selects lower static-cost frontier points without a stronger model
of search-time execution, it is unlikely to become a publishable contribution.
The current evidence is more useful as an SAQ limitation analysis than as a new
method: simple static global cost proxies are not sufficient to improve the SAQ
default planner end to end.

## Commands

Default build:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full -K=4096 -B=4 -enable_PCA=true -num_threads=64
```

Code-volume candidate build:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full -K=4096 -B=4 -enable_PCA=true -num_threads=64 \
  -custom_quant_plan=64:10,128:7,192:5,192:3,256:2,128:0
```

Positive-dim candidate build:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full -K=4096 -B=4 -enable_PCA=true -num_threads=64 \
  -custom_quant_plan=64:10,128:7,192:5,384:3,192:0
```

QPS command template:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_full -K=4096 -B=4 -enable_PCA=true \
  -fix_thread=24 -fix_nprobe=<100|200|400> \
  -searcher_vars_bound_m=4 -searcher_safe_block_min_mode=2 \
  [-custom_quant_plan=...]
```

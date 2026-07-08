# GIST Shared-Plan End-to-End Prototype

Date: 2026-07-08

## Question

The offline residual matrix predicted that `GIST full / K4096 / B4` is an
eligible case for cluster-aware shared local plans:

```text
global plan:        64:11,192:6,320:4,256:2,128:0
local-oracle ratio: 0.941956
M=4 cost-assigned:  0.943474
```

This note asks whether that offline residual-proxy signal transfers to an
actual SAQ index and search run.

## Prototype

The prototype keeps the default SAQ path unchanged unless a shared-plan file is
provided. It adds:

- a materializer that writes a small shared-plan table and one plan id per IVF
  cluster;
- a `create_index` prototype path controlled by `-shared_plan_file`;
- a `-shared_plan_tag` suffix so default and mixed-plan indexes do not collide;
- mixed-plan index serialization with a shared `SaqData` table and cluster
  plan ids;
- mixed-plan search that chooses the corresponding shared-plan searcher for
  each visited IVF cluster.

The materialized GIST B4/M4 artifact is:

```text
/tmp/saq-run/structural/gist_full_K4096_B4_M4_shared.shared_plans.txt
```

It contains four unique plans:

| plan id | plan | assigned clusters |
|---:|---|---:|
| 0 | `64:9,256:6,256:4,256:2,128:0` | 1530 |
| 1 | `64:10,192:7,320:4,192:2,192:0` | 1883 |
| 2 | `192:6,512:4,256:2` | 8 |
| 3 | `64:9,192:6,320:4,320:2,64:0` | 675 |

The direct plan-id metadata is `4096 * 2 = 8192` bits. The prototype index also
stores the shared quantizer metadata and rotators, so the observed file-size
increase is larger than the raw plan-id table.

## Commands

Materialization:

```bash
python script/materialize_cluster_shared_plans.py \
  --name gist_full_K4096_B4_M4 \
  --data-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --avg-bits 4 \
  --shared-plan-count 4 \
  --max-vectors 0 \
  --output-prefix /tmp/saq-run/structural/gist_full_K4096_B4_M4_shared
```

Mixed-plan index build:

```bash
./bin/create_index \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -shared_plan_file=/tmp/saq-run/structural/gist_full_K4096_B4_M4_shared.shared_plans.txt \
  -shared_plan_tag=localm4 \
  -num_threads=64
```

Search evaluation used `R@100`, `nprobe=200`, 24 threads, and safe block-min
mode 2:

```bash
./bin/test_qps \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2

./bin/test_qps \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -shared_plan_tag=localm4 \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2
```

## Initial Result

| index | R@100 | QPS | avg ms/query | dist ratio | index size | build time |
|---|---:|---:|---:|---:|---:|---:|
| SAQ default | 0.94469 | 2706.63 | 8.86768 | 1.000802 | 570M | 3.02178s |
| shared local M4 | 0.94548 | 2255.76 | 10.64009 | 1.000799 | 573M | 3.00696s |

The shared-plan prototype improves recall by `+0.00079` absolute, but QPS drops
to about `0.834x` of the default baseline at this operating point. The index
size grows by roughly 3M in this prototype.

## Interpretation

This is an important limiting result. The offline residual proxy did predict a
small recall improvement, but it did not yield a better recall-QPS tradeoff in
the first end-to-end prototype. The likely causes are:

- the mixed-plan search path creates and uses multiple shared-plan searchers per
  query;
- the selected plans remain mostly multi-segment, so scan cost is not reduced;
- the prototype stores separate shared quantizer metadata and rotators;
- the recall gain is too small to compensate for the added search complexity.

The result does not invalidate the residual-local mismatch observation, but it
does weaken Direction 1 as a standalone systems contribution. The current
evidence supports a narrower claim:

```text
Residual-local shared plans can slightly improve GIST recall under a
query-unaware policy, but naive mixed-plan search can lose enough QPS that the
method is not yet a strict improvement over SAQ.
```

## Follow-Up Test

Do not broaden this prototype to more datasets yet. The next research question
is whether the QPS loss is intrinsic to mixed segment shapes or mostly a
prototype implementation cost. The follow-up test below compares:

- default SAQ;
- shared local M4 with current mixed search;
- a segment-cost-aware version of the shared-plan objective that penalizes
  additional search stages before index construction.

If the cost-aware variant cannot preserve the offline recall signal while
recovering QPS, Direction 1 should become supporting limitation analysis rather
than the main contribution.

## Falsification: Lazy Searcher And Cost-Aware Assignment

The next experiment tested two narrow alternatives:

1. Reduce prototype overhead by constructing shared-plan searchers lazily. In
   shared-plan mode, the search path now avoids constructing the unused default
   searcher and only constructs shared searchers for plan ids reached by the
   query's probed IVF cells.
2. Add a minimal query-unaware cost-aware assignment objective to the
   materializer:

```text
score(cluster, plan)
  = residual_proxy(cluster, plan) / residual_proxy(cluster, default_plan)
  + lambda * search_cost_proxy(plan) / search_cost_proxy(default_plan)
```

The prototype search-cost proxy is intentionally simple:

```text
search_cost_proxy(plan) = positive_segment_count + total_segment_count
```

For `lambda=1.0`, the materializer shifts many clusters to the lower segment
count plan `192:6,512:4,256:2`. This reduces the file size but substantially
worsens the residual proxy:

```text
cost-assigned residual ratio:       0.943474
cost-aware assigned residual ratio: 1.024479
```

The same-machine safe-search result at `nprobe=200`, 24 threads is:

| index | R@100 | QPS | avg ms/query | index size |
|---|---:|---:|---:|---:|
| SAQ default | 0.94469 | 2690.89 | 8.91988 | 570M |
| shared local M4, lazy search | 0.94548 | 2439.68 | 9.83749 | 573M |
| cost-aware M4, lambda=1.0 | 0.94485 | 2399.94 | 10.00063 | 567M |

This falsifies the simple cost-aware proxy as a useful fix. Lazy searcher
construction recovers some prototype overhead compared with the initial
`2255.76` QPS measurement, but the shared-plan index is still slower than
default SAQ. The `lambda=1.0` endpoint slightly preserves recall over default
but is slower than the residual-only shared plan, despite its smaller index.

The immediate interpretation is that segment count alone is not an adequate
search-cost model for SAQ. A credible cost-aware planner would need to model
at least quantized dimensional volume, zero-tail behavior, per-segment pruning
effectiveness, and the cost of maintaining multiple plan-specific query
estimators. Without that stronger model, Direction 1 remains useful as SAQ
limitation evidence but is not yet a strict improvement over SAQ.

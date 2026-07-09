# SAQ Segment-Order Counterfactual Design

## Purpose

The runtime-profile evidence showed that the variance stage is almost inactive
on GIST sample100k K512 B=4, while the fast stage and accurate-refinement
short-circuiting are the meaningful work-saving stages. The next question is
therefore narrow:

```text
Is SAQ's current PCA/plan segment order already near-optimal for block-level
fast pruning and accurate-refinement early exit?
```

This note defines a diagnostic-only counterfactual replay. It does not propose
a new search policy and does not modify the production `IVF::search` or
`SAQSearcher` path.

## Strict-Reviewer Concern

A strict reviewer would likely say that changing segment order is an
implementation detail unless it exposes a robust SAQ limitation. The analysis
therefore uses a stop-first rule:

```text
If simple query-unaware segment orders do not reduce work relative to SAQ's
default order, do not continue this as a method direction.
```

The goal is to falsify an easy estimator-scheduling idea before spending time
on a real search-policy implementation.

## Prototype

New diagnostic binary:

```text
bin/profile_segment_order
```

Source:

```text
src/profile_segment_order.cpp
```

The binary:

1. loads an existing SAQ IVF index;
2. uses the same centroid probing as `IVF::search`;
3. mirrors the same variance, fast-estimation, accurate-refinement, and
   result-pool stages;
4. changes only the order in which segments are visited;
5. reports recall and the existing runtime-profile counters.

It is diagnostic-only. It may produce different result sets for alternative
orders, but it does not affect the default search path.

The replay uses finite valid-lane block-min semantics, matching the safety
intent of `-searcher_safe_block_min_mode=2`. It is not intended as a QPS
benchmark because it is a single-threaded analysis binary.

Sanity check: under `pca` order, the replay matches the production
`test_qps` runtime-profile work counters at nprobe=200. The replay R@100 is
`0.991300`, while the production `test_qps` R@100 is `0.991320`, a two-hit
difference over 100,000 query-neighbor slots. Therefore this prototype should
be used for relative work-counter analysis; production `test_qps` remains the
source for final recall/QPS claims.

## Evaluated Orders

The initial prototype supports:

| order | definition | purpose |
|---|---|---|
| `pca` | original SAQ plan order | baseline |
| `reverse` | reverse of original order | negative control |
| `bit_desc` | higher-bit segments first | checks whether bit precision explains the default order |
| `dim_desc` | larger segments first | checks whether larger dimensional volume should dominate |
| `cost_asc` | lower-dimensional positive-bit segments first, zero-bit tail last | tests a cheap-segment-first idea |
| `risk_per_cost_desc` | segment variance divided by `dim * max(bits,1)` | tests a simple data-only risk/cost score |

These orders are intentionally simple and hyperparameter-free. They are not
learned from benchmark queries.

## Initial Replay Result

Setup:

```text
dataset = gist_sample100k
K = 512
B = 4
PCA = true
plan = SAQ default variance plan
plan shape = 64x11_192x6_320x4_256x2_128x0
nprobe = 200
top-k = 100
queries = 1000
```

Local output:

```text
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_segment_order_full.csv
```

Per-query averages:

| order | R@100 | fast segment calls | accurate segment calls | fast bits | accurate bits |
|---|---:|---:|---:|---:|---:|
| `pca` | 0.991300 | 4134.878 | 4729.460 | 24016744.448 | 2929426.752 |
| `reverse` | 0.990380 | 6095.297 | 12666.019 | 40603281.408 | 6962649.600 |
| `bit_desc` | 0.991300 | 4134.878 | 4729.460 | 24016744.448 | 2929426.752 |
| `dim_desc` | 0.990390 | 6094.546 | 11732.184 | 40597397.504 | 6998625.216 |
| `cost_asc` | 0.991320 | 4190.318 | 4752.295 | 24444508.160 | 2931929.664 |
| `risk_per_cost_desc` | 0.991300 | 4134.878 | 4729.460 | 24016744.448 | 2929426.752 |

Relative to `pca`:

| order | recall delta | fast-call delta | accurate-call delta | fast-bit delta | accurate-bit delta |
|---|---:|---:|---:|---:|---:|
| `reverse` | -0.00092 | +47.41% | +167.81% | +69.06% | +137.68% |
| `dim_desc` | -0.00091 | +47.39% | +148.07% | +69.04% | +138.91% |
| `cost_asc` | +0.00002 | +1.34% | +0.48% | +1.78% | +0.09% |

`bit_desc` and `risk_per_cost_desc` are identical to `pca` for this plan
because the default SAQ plan already orders the positive-bit segments in the
same descending-importance direction.

## Interpretation

This first replay does not support a simple segment-reordering method:

- the default order is tied for the lowest observed work;
- reversing the order or prioritizing large segments is clearly worse;
- cheap-segment-first does not reduce work;
- data-only `risk_per_cost_desc` collapses to the default order on this plan.

The result is consistent with SAQ's design: PCA concentrates variance into
early dimensions, and the default plan already scans high-variance/high-bit
segments first. For this case, the current segment order appears difficult to
improve with a simple query-unaware rule.

## Limitations

This is not a full negative conclusion yet:

- only GIST sample100k K512 B=4 was replayed;
- only nprobe=200 was fully compared across orders;
- the prototype measures counterfactual work and recall, not wall-clock QPS;
- it tests simple fixed orders, not a derived safe bound or adaptive schedule.

However, the evidence is enough to avoid implementing a real reordered search
path before doing a small robustness check.

## Next Step

Run the same replay for:

```text
nprobe = 160, 240
```

If the default order remains tied for best or better than the simple
hyperparameter-free alternatives, stop the segment-order branch and record it
as limitation evidence for the search-procedure direction.

## Commands

Full replay:

```bash
/rwproject/kdd-db/kluaq/saq/bin/profile_segment_order \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=200 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_segment_order_full.csv
```

Prototype sanity check:

```bash
/rwproject/kdd-db/kluaq/saq/bin/profile_segment_order \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=200 \
  -profile_topk=100 \
  -profile_orders=pca \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_segment_order_pca_check.csv
```

The commands were run from:

```text
/tmp/saq-run
```

# GIST Shared-Plan Static Cost Analysis

Date: 2026-07-08

## Question

The first end-to-end shared-plan prototype showed a small recall gain but a
large QPS loss. A follow-up test added lazy shared-searcher construction and a
simple segment-count cost proxy, but the cost-aware endpoint still did not
recover QPS.

This note asks whether more realistic static proxies can explain the result
before we invest in another planner:

- quantized dimensional volume;
- zero-tail residual mass;
- per-segment proxy cost;
- multi-plan query-estimator overhead.

The analysis remains query-unaware. It uses only base PCA vectors, IVF
centroids, cluster ids, residual statistics, materialized plan assignments, and
already measured safe-search results.

## Compared Indexes

All results are for `GIST full / K4096 / B=4`, `R@100`, `nprobe=200`, 24
threads, and `-searcher_safe_block_min_mode=2`.

| index | plan source | R@100 | QPS | QPS ratio | index size |
|---|---|---:|---:|---:|---:|
| SAQ default | global SAQ DP | 0.94469 | 2690.89 | 1.0000 | 570M |
| shared local M4 | residual-cost assignment | 0.94548 | 2439.68 | 0.9066 | 573M |
| cost-aware M4 | residual + segment-count endpoint | 0.94485 | 2399.94 | 0.8919 | 567M |

The cost-aware endpoint used `lambda=1.0` only as a falsification endpoint, not
as a proposed method. Under the current hyperparameter-discipline constraint,
it should not be treated as a deployable planner unless its scale is justified
or removed.

## Proxy Definitions

For a plan with segments `(dim_s, bits_s)`:

```text
positive_segments = count_s(bits_s > 0)
total_segments    = count_s(all segments)
fast_volume       = sum_s dim_s                  for bits_s > 0
accurate_volume   = sum_s dim_s * bits_s         for bits_s > 0
segment_proxy     = positive_segments + total_segments
zero_tail_mass    = cluster residual variance assigned to bits_s = 0
```

`fast_volume` approximates the amount of dimensional work exposed to the
variance and 1-bit stages. `accurate_volume` approximates full-code work if a
candidate reaches refinement. `segment_proxy` is the simple proxy used by the
cost-aware endpoint. `zero_tail_mass` measures how much residual variance is
discarded into unquantized zero-bit dimensions.

## Static Proxy Table

The following table is cluster-weighted over active IVF cells.

| index | residual proxy ratio | fast volume ratio | accurate volume ratio | segment proxy ratio | zero-tail fraction | distinct plans |
|---|---:|---:|---:|---:|---:|---:|
| SAQ default | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.002910 | 1 |
| shared local M4 | 0.9435 | 0.9750 | 1.0000 | 0.9995 | 0.002627 | 4 |
| cost-aware M4 | 1.0245 | 0.9973 | 1.0038 | 0.9286 | 0.001872 | 4 |

The static proxies explain the negative result better than segment count alone:

- Shared local M4 strongly improves the residual proxy (`0.9435x`) and slightly
  reduces fast volume (`0.9750x`), but it keeps accurate volume and segment
  count essentially unchanged. The small recall gain is plausible, but the QPS
  loss cannot be offset by such a small static scan reduction.
- The cost-aware endpoint reduces the segment-count proxy (`0.9286x`), but its
  accurate bit volume is slightly larger (`1.0038x`) and its fast volume is
  almost unchanged (`0.9973x`). This explains why fewer segments did not produce
  higher QPS.
- The cost-aware endpoint also lowers zero-tail residual fraction. That can help
  preserve recall, but it means more dimensions remain quantized and eligible
  for search work. The endpoint is therefore not a pure speed plan.
- Both shared variants use four plan ids. Lazy construction avoids unused
  searchers, but a query that probes clusters assigned to multiple plans still
  needs multiple plan-specific estimator states. This overhead is not captured
  by the segment-count proxy.

## Why The Simple Cost Proxy Failed

The segment-count proxy assumed that fewer segments imply faster search. For
SAQ this is incomplete because search cost has at least three layers:

1. **Stage volume:** the variance and fast stages are closer to dimensional
   volume than to raw segment count.
2. **Refinement volume:** accurate refinement depends on bit volume and on how
   many candidates survive early stages.
3. **Plan diversity:** a mixed-plan index can require multiple query-specific
   estimator/searcher states for the same query.

The `lambda=1.0` endpoint moved many clusters toward the lower segment-count
plan `192:6,512:4,256:2`, but this plan has no zero tail, 960 positive
dimensions, and 3712 accurate bit volume. It is not necessarily cheaper than
the default plan, even though its segment-count proxy is smaller.

## Implication

A more realistic cost-aware planner is possible, but it should not be another
free-form weighted sum of empirical terms. A credible version would need a
fixed, mechanism-level objective with no unjustified tuning knobs. The minimum
static objective would likely combine:

```text
residual risk under the SAQ variance objective
+ implementation-derived fast dimensional volume
+ implementation-derived accurate bit volume
+ explicit mixed-plan estimator setup term
```

The per-segment pruning effect is harder to include without query information.
It may be useful as an explanatory diagnostic, but turning it into a planner
term would likely require distribution assumptions or thresholds that are hard
to defend under the current query-unaware constraint.

## Current Decision

This analysis weakens cluster-aware shared-plan materialization as the main
method. The evidence supports it as SAQ limitation analysis:

```text
SAQ's global plan can be locally mismatched with IVF residual structure, but a
small shared family of local plans does not automatically improve the system
tradeoff. Static residual gains can be smaller than mixed-plan search overhead.
```

To continue this direction as a main contribution, the next planner must first
show an implementation-derived cost model that predicts measured QPS better
than segment count, before any new end-to-end index builds.

## Artifacts

The offline proxy JSON is:

```text
/tmp/saq-run/structural/gist_full_K4096_B4_static_proxy_analysis.json
```

The measured QPS CSVs are:

```text
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np200_sm4_safeblockminsimd.csv
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_sharedlocalm4_pca_th24_np200_sm4_safeblockminsimd.csv
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_sharedcostl1_pca_th24_np200_sm4_safeblockminsimd.csv
```

# GIST Shared-Plan Runtime Decomposition

Date: 2026-07-08

## Question

The static cost analysis showed that segment count is not a sufficient
search-cost proxy for the shared-plan prototype. This note decomposes the
actual search run to answer a narrower question:

```text
Is the shared-plan QPS loss explained by more scan/refinement work, or by
mixed-plan overhead that is not captured by simple work counters?
```

This is an explanation study, not a planner. It uses held-out benchmark queries
only to measure runtime behavior of already built indexes. No plan is learned
from these queries.

## Instrumentation

`test_qps` now has an optional flag:

```bash
-runtime_decomp=true
```

When enabled, the CSV keeps the original QPS columns and appends per-query
averages for:

- fast and accurate bit volume;
- visited clusters, blocks, vectors, and segments;
- variance-stage block evaluations and pruning ratio;
- fast-stage segment evaluations and pruning ratio;
- accurate-stage blocks, candidate lanes, and segment evaluations;
- distinct plan ids visited per query;
- shared searchers constructed per query.

The default CSV schema is unchanged when the flag is not set.

## Commands

All runs use `GIST full / K4096 / B=4`, `R@100`, `nprobe=200`, 24 threads, and
safe block-min mode 2.

```bash
./bin/test_qps \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -runtime_decomp=true

./bin/test_qps \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -shared_plan_tag=localm4 \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -runtime_decomp=true

./bin/test_qps \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -data_path=/tmp/saq-run/data \
  -shared_plan_tag=costl1 \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -runtime_decomp=true
```

## Result

QPS is averaged over 10 rounds. The logical decomposition counters were stable
across rounds; the table reports the values written to the final CSV.

| index | R@100 | QPS | QPS ratio | distinct plans/query | shared searchers/query |
|---|---:|---:|---:|---:|---:|
| SAQ default | 0.94469 | 2677.16 | 1.0000 | 1.000 | 0.000 |
| shared local M4 | 0.94548 | 2434.73 | 0.9094 | 2.907 | 2.907 |
| cost-aware M4 | 0.94485 | 2398.13 | 0.8958 | 3.336 | 3.336 |

The work counters move in the opposite direction from QPS:

| index | fast bits/query | acc bits/query | fast seg eval/query | accurate candidates/query | accurate seg eval/query |
|---|---:|---:|---:|---:|---:|
| SAQ default | 40.41M | 4.53M | 6505.26 | 4758.85 | 7183.07 |
| shared local M4 | 39.37M | 4.12M | 6468.47 | 4676.41 | 7077.24 |
| cost-aware M4 | 38.58M | 3.99M | 6065.12 | 4279.22 | 6456.65 |

Relative to default:

| index | fast bit ratio | acc bit ratio | fast seg eval ratio | accurate candidate ratio | accurate seg eval ratio |
|---|---:|---:|---:|---:|---:|
| shared local M4 | 0.9741 | 0.9097 | 0.9943 | 0.9827 | 0.9853 |
| cost-aware M4 | 0.9547 | 0.8809 | 0.9323 | 0.8992 | 0.8989 |

Block-level pruning also does not explain the slowdown:

| index | variance block eval/query | variance prune ratio | fast prune ratio | accurate blocks/query |
|---|---:|---:|---:|---:|
| SAQ default | 1995.27 | 0.000023 | 0.3466 | 1303.59 |
| shared local M4 | 1995.27 | 0.000023 | 0.3506 | 1295.77 |
| cost-aware M4 | 1995.27 | 0.000022 | 0.3880 | 1221.09 |

## Interpretation

The runtime counters falsify a simple "more computational work causes the QPS
loss" explanation.

Shared local M4 has slightly less measured work than default:

- `0.974x` fast bit volume;
- `0.910x` accurate bit volume;
- `0.985x` accurate segment evaluations.

Yet its QPS is only `0.909x` of default. The cost-aware endpoint reduces
measured work even more:

- `0.955x` fast bit volume;
- `0.881x` accurate bit volume;
- `0.899x` accurate segment evaluations.

But its QPS is lower, at `0.896x` of default. Therefore the shared-plan loss is
not primarily explained by these scan/refinement counters.

The most visible remaining explanation is mixed-plan overhead:

- default uses one plan-specific searcher per query;
- shared local M4 constructs about `2.91` shared searchers per query;
- cost-aware M4 constructs about `3.34` shared searchers per query.

Each shared searcher has its own plan-specific estimator state, query segment
setup, pruning-bound setup, lookup-table preparation path, and accesses a
separate shared `SaqData` / cluster layout. The current counters measure the
amount of nominal distance work, but they do not fully measure estimator setup,
cache behavior, instruction locality, or memory-layout effects from mixing
plans inside one query.

## Implication

This substantially weakens shared local plan materialization as the main
method. The direction now has two possible roles:

1. **SAQ limitation evidence.** The residual-local signal can slightly improve
   recall, showing that a global SAQ plan is not always locally optimal for IVF
   residual structure.
2. **Architecture-level follow-up only if justified.** To become a main method,
   it would need a design that avoids per-query multi-plan estimator overhead,
   such as grouping probes by plan with lower setup cost, sharing query-side
   estimator state across compatible plans, or constraining assignments so most
   queries touch one plan. These are larger architectural changes and should
   not be pursued without a clear paper-level contribution argument.

The next planner should not be another weighted objective with additional
unjustified hyperparameters. Before any new end-to-end build, it should first
show that an implementation-derived cost model predicts measured QPS better
than segment count and better than these raw work counters.

## Artifacts

The decomposition CSVs are:

```text
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np200_sm4_safeblockminsimd_decomp.csv
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_sharedlocalm4_pca_th24_np200_sm4_safeblockminsimd_decomp.csv
results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_sharedcostl1_pca_th24_np200_sm4_safeblockminsimd_decomp.csv
```

The build completed successfully. The build system reported clock-skew warnings
from future file timestamps on this machine, but the relevant binaries were
rebuilt and linked before the measurements above.

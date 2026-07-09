# SAQ Variance-Bound Inactivity Final Measurement

## Decision

Stop the search-procedure direction as a main method direction.

The final bound-focused measurement explains why the variance-pruning stage is
almost inactive on GIST sample100k K512 B=4:

```text
The variance-stage block minimum is usually far below the current top-k
boundary. Making it prune meaningful work would require removing a large
fraction of SAQ's conservative variance slack, which has no safe derivation in
the current evidence.
```

This rules out the last low-overhead search-procedure idea considered on this
branch. Do not continue by tuning `searcher_vars_bound_m` or adding calibrated
thresholds.

## Diagnostic Profiler

New diagnostic binary:

```text
bin/profile_variance_bound
```

Source:

```text
src/profile_variance_bound.cpp
```

For each scanned block, it records:

- current top-k boundary `distk`;
- variance-stage block minimum `mi` under the normal SAQ setting;
- a diagnostic no-bound counterfactual minimum with `searcher_vars_bound_m = 0`;
- whether the block is pruned by the variance stage;
- whether the block is later pruned by the fast stage.

The no-bound counterfactual is not a valid search policy. It removes the
variance slack entirely and is used only to estimate how aggressive a bound
tightening would have to be.

For finite-boundary blocks that are not pruned by the current variance stage,
the profiler reports:

```text
relative gap = (distk - mi) / |distk|
required slack fraction = (distk - mi) / (mi_no_bound - mi)
```

The required slack fraction is only defined when the no-bound counterfactual
would cross the top-k boundary.

## Setup

```text
dataset = gist_sample100k
K = 512
B = 4
PCA = true
plan = SAQ default variance plan
plan shape = 64x11_192x6_320x4_256x2_128x0
top-k = 100
queries = 1000
searcher_vars_bound_m = 4
safe search semantics = finite valid-lane block-min replay
```

Evaluated nprobe values:

```text
160, 200, 240
```

Local output files:

```text
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_variance_bound_np160.csv
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_variance_bound_np200.csv
/tmp/saq-run/runtime_profile/gist_sample100k_k512_b4_variance_bound_np240.csv
```

## Results

### Pruning Rates

| nprobe | blocks | finite-boundary blocks | variance-pruned blocks | variance-prune rate | fast-prune rate after variance |
|---:|---:|---:|---:|---:|---:|
| 160 | 1,245,446 | 1,241,443 | 1,750 | 0.1405% | 45.28% |
| 200 | 1,530,007 | 1,526,004 | 4,104 | 0.2682% | 52.02% |
| 240 | 1,807,095 | 1,803,092 | 8,173 | 0.4523% | 57.62% |

The top-k boundary is not the main reason variance pruning is inactive. Only
4,003 blocks across all runs have a non-finite boundary, roughly four blocks
per query. After that, `distk` is finite, but the variance minimum is still too
low to prune.

### Gap To The Boundary

For finite-boundary blocks not pruned by variance:

| nprobe | gap <= 10% of boundary | gap <= 25% | gap <= 50% | median relative gap | 90th-percentile relative gap |
|---:|---:|---:|---:|---:|---:|
| 160 | 0.0907% | 0.3913% | 3.4108% | 0.7467 | 0.8635 |
| 200 | 0.1570% | 0.7067% | 4.9017% | 0.7427 | 0.8585 |
| 240 | 0.2597% | 1.1855% | 6.6308% | 0.7386 | 0.8537 |

The current variance estimate is not narrowly missing the boundary. The median
block minimum is roughly 74% below the current boundary in relative terms.
Only a very small fraction of blocks are close enough that a mild tightening
could matter.

### No-Bound Counterfactual

The no-bound counterfactual can cross the boundary for many blocks:

| nprobe | no-bound prunable among variance-unpruned finite blocks | required slack fraction q25 | q50 | q75 | q90 |
|---:|---:|---:|---:|---:|---:|
| 160 | 98.26% | 0.5281 | 0.6304 | 0.7199 | 0.8018 |
| 200 | 98.58% | 0.4972 | 0.6060 | 0.6994 | 0.7845 |
| 240 | 98.80% | 0.4679 | 0.5844 | 0.6817 | 0.7702 |

This does not justify using the no-bound estimate. It says the opposite: to
make variance pruning meaningful, the searcher would need to remove a large
fraction of the conservative variance slack. The median required removal is
about 58-63% of the slack; the 90th percentile requires about 77-80%.

That scale of tightening is too large to justify as a small safe refinement.
Without a new theorem or explicit approximation guarantee, it would be an
arbitrary calibration of the existing bound.

## Interpretation

The variance stage is inactive because it is deliberately conservative and far
from the top-k boundary, not because the top-k boundary is unavailable.

The fast stage already performs the useful block-level filtering:

```text
fast-prune rate after variance = 45-58%
```

A useful variance-bound method would need to make the earlier variance stage
strong enough to replace some of this fast-stage work. The final measurement
does not reveal a safe way to do that. It only shows that removing most of the
slack would make the variance estimate aggressive enough to prune, which is not
a defensible database-systems contribution by itself.

## Final Search-Procedure Decision

Close the search-procedure direction on this branch.

Ruled-out ideas now include:

- changing the one-global-plan objective without recall-matched improvement;
- static segment-cost-aware DP;
- mixed shared local plans;
- empirical fixed-policy candidate scoring;
- simple query-unaware segment reordering;
- variance-bound tightening by arbitrary calibration.

The useful contribution of this phase is limitation evidence:

```text
SAQ's default progressive search path is already hard to improve with small
query-unaware changes. Its variance stage is weak, but making it useful appears
to require aggressive bound tightening rather than a low-overhead safe rule.
```

Future work should move away from small IVF search-loop scheduling changes and
toward a more structural SAQ limitation, such as graph-index compatibility,
stronger estimator-bound theory, or transform objectives with a derivation
beyond empirical plan search.

## Commands

```bash
/rwproject/kdd-db/kluaq/saq/bin/profile_variance_bound \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=160 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_variance_bound_np160.csv

/rwproject/kdd-db/kluaq/saq/bin/profile_variance_bound \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=200 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_variance_bound_np200.csv

/rwproject/kdd-db/kluaq/saq/bin/profile_variance_bound \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -profile_nprobe=240 \
  -profile_topk=100 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4 \
  -profile_output_csv=runtime_profile/gist_sample100k_k512_b4_variance_bound_np240.csv
```

Commands were run from:

```text
/tmp/saq-run
```

# Phase 3 Canonical Fixed-Seed Evidence

## Scope

This note records the predeclared Phase 3 local-neighborhood replay. It tests
whether an SAQ progressive distance stage has a stable ordering-quality signal
against the source-aligned packed SymphonyQG estimator. It does not execute a
frontier heap or path-dependent graph traversal and therefore is not an
end-to-end graph-search result.

## Fixed Evaluation

```text
dataset: GIST sample50k in PCA coordinates
SAQ index: K=512, B=4
quantization plan:
  0:64    -> 11 bits/dimension
  64:256  -> 6 bits/dimension
  256:576 -> 4 bits/dimension
  576:832 -> 2 bits/dimension
  832:960 -> 0 bits/dimension
degree: 32
subset 1024: 50 queries, 8 roots/query
subset 4096: 100 queries, 8 roots/query
SymphonyQG rotation seeds: 0,1,...,9
statistical unit: query
```

Command:

```bash
python script/run_graph_phase3.py \
  --binary ./bin/profile_graph_frontier \
  --artifact-root /rwproject/kdd-db/kluaq/saq/data/gist_sample50k \
  --output-dir results/saq/graph_phase3_gist_sample50k_k512_b4
```

All 20 runs completed. Mean per-run wall time was `0.616 s` for subset 1024
and `3.795 s` for subset 4096, including adjacency construction, estimator
preparation, replay, and output. These combined profiler times are
reproducibility metadata, not estimator microbenchmarks.

## Main Results

Confidence intervals are query-level normal-approximation 95% intervals. Code
bits exclude factors, query tables, padding traffic, and compute cost.

| subset | estimator | code bits/candidate | top-1 disagreement | mean exact-best rank | event p90 rank | exact regret | top-4 containment |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | `symqg_fht_fastscan` | 1024 | 0.3530 | 1.7025 | 2.8 | 0.032209 | 0.95325 |
| 1024 | `saq_fast` | 832 | 0.4375 | 1.9900 | 4.0 | 0.053447 | 0.91250 |
| 1024 | `saq_prefix_acc1` | 1472 | 0.1075 | 1.1275 | 2.0 | 0.003581 | 1.00000 |
| 4096 | `symqg_fht_fastscan` | 1024 | 0.3814 | 1.8606 | 3.1 | 0.031495 | 0.93413 |
| 4096 | `saq_fast` | 832 | 0.4613 | 2.2575 | 5.0 | 0.051584 | 0.87625 |
| 4096 | `saq_prefix_acc1` | 1472 | 0.1375 | 1.1725 | 2.0 | 0.003735 | 0.99750 |

The complete aggregate and paired tables are:

- `docs/saq_graph_phase3_canonical_overall_2026_07_11.csv`;
- `docs/saq_graph_phase3_canonical_paired_2026_07_11.csv`.

## Paired Query Evidence

The following values are candidate minus `symqg_fht_fastscan`; lower is better
for rank, disagreement, and regret.

| subset | candidate | mean-rank delta (95% CI) | disagreement delta (95% CI) | regret delta (95% CI) |
|---:|---|---:|---:|---:|
| 1024 | `saq_fast` | +0.2875 [+0.0355, +0.5395] | +0.0845 [+0.0179, +0.1511] | +0.02124 [+0.00741, +0.03506] |
| 1024 | `saq_prefix_acc1` | -0.5750 [-0.6821, -0.4679] | -0.2455 [-0.2879, -0.2031] | -0.02863 [-0.03402, -0.02324] |
| 4096 | `saq_fast` | +0.3969 [+0.2217, +0.5720] | +0.0799 [+0.0369, +0.1229] | +0.02009 [+0.01153, +0.02865] |
| 4096 | `saq_prefix_acc1` | -0.6881 [-0.7698, -0.6064] | -0.2439 [-0.2782, -0.2096] | -0.02776 [-0.03075, -0.02477] |

`saq_fast` is significantly worse than the aligned packed baseline on all three
quality metrics at both subset sizes. `saq_prefix_acc1` is significantly better
on all three, but reads more code.

## Seed And Margin Stability

The SymphonyQG mean-rank range over seeds was:

```text
subset 1024: 1.5800 to 1.8925
subset 4096: 1.7700 to 2.0100
```

SAQ is rotation-seed invariant in this experiment. `saq_fast` had ranks
`1.9900` and `2.2575`, so it was worse than SymphonyQG under every seed.
`saq_prefix_acc1` had ranks `1.1275` and `1.1725`, so it was better under every
seed. This rules out a favorable SymphonyQG rotation as the explanation.

The same ordering holds in every exact-gap quartile. In the hardest quartile
(smallest exact first-to-second gap), mean ranks were:

| subset | SymphonyQG | `saq_fast` | `saq_prefix_acc1` |
|---:|---:|---:|---:|
| 1024 | 2.189 | 2.791 | 1.447 |
| 4096 | 2.600 | 3.086 | 1.530 |

The first accurate SAQ segment therefore supplies a real local-ordering signal,
especially near ambiguous boundaries. The evidence does not yet establish that
the signal is cost-effective.

## Work Interpretation

The first accurate prefix replaces the first segment's 1-bit estimate with its
11-bit estimate. For the 64-dimensional first segment, this adds

```text
64 dimensions * (11 - 1) additional bits = 640 bits/candidate.
```

Therefore:

```text
saq_fast:        832 code bits/candidate
SymphonyQG:     1024 code bits/candidate
saq_prefix_acc1:1472 code bits/candidate
```

The prefix reads 448 more code bits per candidate than SymphonyQG before
counting SAQ short factors, the accurate segment's `ExFactor`, segmented lookup
work, and scalar accurate refinement. SymphonyQG stores 12 factor bytes per
edge and prepares a 4096-byte query LUT that is amortized across estimates.
Consequently, the accuracy improvement can still be explained by additional
logical work. Code bits alone cannot establish a Pareto advantage.

## Phase Decision

The strong-baseline correction is confirmed: the historical unrotated proxy
substantially understated SymphonyQG quality, and `saq_fast` is not a stronger
local graph estimator.

The Phase 3 stop condition is not fully met because `saq_prefix_acc1` is a
stable accuracy-improving point in the code-bit-only table. The continue
condition is also not yet established because complete factor, byte, SIMD, and
runtime work has not been matched. The defensible decision is therefore:

```text
continue only to a narrow Phase 4 work-accounting and estimator-runtime test;
do not design a traversal policy or implement HNSW/DiskANN integration yet.
```

Phase 4 should compare `symqg_fht_fastscan`, `saq_fast`, and
`saq_prefix_acc1` under complete bytes requested and isolated estimator time.
If the prefix no longer supplies a stable Pareto point after that accounting,
stop the graph-local-ranking direction and preserve this result as negative
evidence.

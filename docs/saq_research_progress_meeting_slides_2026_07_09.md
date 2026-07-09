# SAQ Follow-Up Research Progress

From Local Plan Corrections To Graph-Traversal Compatibility

Date: 2026-07-09

Audience assumption: familiar with vector search and approximate nearest
neighbor search at a high level, but not familiar with SAQ internals or the
recent follow-up attempts in this repository.

---

## 1. Meeting Goal

This meeting is not about presenting one finished method.

The goal is to explain, from a PhD research perspective:

1. What SAQ already contributes.
2. Why a follow-up is difficult.
3. What directions we tried.
4. Which directions produced useful evidence but should not be the main method.
5. What the current graph-traversal direction is testing.
6. What evidence is still missing before this can become a SIGMOD/VLDB/ICDE-level contribution.

Main message:

```text
So far, we have not found an independent method that clearly dominates SAQ.

The useful research value is that the attempts have narrowed the search space:
small empirical plan tuning is weak, mixed local plans add overhead, static
global cost objectives do not transfer, and SAQ's IVF search path is already
hard to improve with simple query-unaware scheduling.

The current active question is therefore more structural:
does SAQ's segmented progressive estimator provide a graph-traversal
refinement advantage beyond existing quantized-graph methods such as
SymphonyQG?
```

Speaker notes:

- This deck deliberately separates evidence from claims.
- The strict-reviewer framing matters: small recall or QPS gains are not enough.
- The desired final output is a database research contribution, not a software optimization report.

---

## 2. Branch Map

Repository branches:

| branch | role |
|---|---|
| `main` | upstream SAQ code |
| `saq-correctness-base` | clean base with only confirmed correctness fixes |
| `saq-boundary-audit` | older default-neighborhood fixed-policy experiments |
| `saq-structural-followup` | mixed shared local-plan experiments |
| `saq-global-cost-dp` | one-global-plan static segment-cost DP experiments |
| `saq-planner-objective-analysis` | fac-error planner objective and IVF search-procedure measurements |
| `saq-graph-traversal-analysis` | current graph-index compatibility direction |

Current branch:

```text
saq-graph-traversal-analysis
latest commit at deck time: d94279d
```

Current branch starts from `saq-correctness-base`, not from the old fixed-policy
prototype branch.

Speaker notes:

- Except for `main` and `saq-correctness-base`, these are research-attempt branches.
- Old slides in the fixed-policy branch were useful stylistically but are now substantively out of date.

---

## 3. What We Can Safely Say Today

Safe statement:

```text
SAQ is a strong baseline. Most simple query-unaware corrections around its
segment planner or IVF search path are either too empirical, too small, or too
expensive.
```

What we have as evidence:

- Fixed-policy local plan corrections: repeated small positives on GIST/CIFAR, but empirical and handcrafted.
- Shared local plans: residual-local signal exists, but mixed-plan dispatch loses QPS.
- Static global segment-cost DP: SAQ default is not dominated on simple risk-cost frontiers.
- Fac-error planner objective: plan can move, but the GIST custom plan does not recover default recall before losing the QPS advantage.
- Search-procedure measurements: fast-stage pruning and accurate-stage early exit are already effective; variance pruning is weak but hard to tighten safely.
- Graph-traversal direction: SAQ staged estimates show strong local rank recovery against a formula-level SymphonyQG-style vertex proxy, but the baseline still needs fuller alignment.

Speaker notes:

- This is a stronger meeting position than pretending every attempt was a success.
- The current contribution is not "we improved SAQ"; it is "we have identified where simple follow-ups fail and where one structural question remains plausible."

---

## 4. Core Problem Setting

We store a database:

```text
X = {x_1, x_2, ..., x_N},  x_i in R^D
```

Given a query:

```text
q in R^D
```

Nearest-neighbor search wants:

```text
argmin_i d(q, x_i)
```

For L2 search:

```text
d(q, x_i) = ||q - x_i||_2^2
```

In high-dimensional ANNS, exact float32 distance computation is expensive
because a query may scan many candidates and each candidate has `D` dimensions.

Vector quantization stores a compressed code for each vector, then estimates
distance from the compressed code.

Speaker notes:

- The key tradeoff is memory traffic and compute versus ranking accuracy.
- Our follow-up is about SAQ's compressed distance estimates and segment plans.

---

## 5. SAQ In One Slide

SAQ: Segmented Adjusted Quantization.

SAQ's high-level flow:

```text
1. Rotate data with PCA.
2. Split PCA dimensions into contiguous segments.
3. Assign more bits to high-variance segments and fewer bits to low-variance segments.
4. Use CAQ-style code adjustment inside each segment.
5. Use staged distance estimation during search.
```

Important code paths:

```text
saqlib/quantization/saq_data.hpp
  dynamic_programming(...)

saqlib/quantization/saq_estimator.hpp
  varsEstDist(...)
  compFastDist(...)
  compAccurateDist(...)

saqlib/quantization/saq_searcher.hpp
  progressive block scan and refinement
```

Speaker notes:

- The follow-up attempts mostly target the segment plan or the staged estimator.
- We are not trying to replace CAQ or rewrite the whole quantizer.

---

## 6. Segment Plan Notation

We write a plan as:

```text
dim:bits, dim:bits, ...
```

Running example, GIST full / K4096 / B=4:

```text
64:11,192:6,320:4,256:2,128:0
```

Meaning:

| segment | PCA dimension range | dimensions | bits per dimension |
|---|---:|---:|---:|
| 1 | 0 to 63 | 64 | 11 |
| 2 | 64 to 255 | 192 | 6 |
| 3 | 256 to 575 | 320 | 4 |
| 4 | 576 to 831 | 256 | 2 |
| 5 | 832 to 959 | 128 | 0 |

The final `0`-bit segment is a dropped low-variance tail.

Speaker notes:

- A plan is not just a storage object; it also determines search-time staged work.
- The recurring question is whether SAQ's default plan is optimal for the system objective we care about.

---

## 7. Variable Glossary

Variables used throughout the deck:

| symbol | meaning | typical/default value in our runs |
|---|---|---|
| `N` | number of base vectors | dataset-dependent |
| `D` | original dimension | GIST 960, CIFAR 512, DEEP 256, audio 192, word2vec 300 padded to 320 |
| `D_p` | padded dimension | rounded up to multiple of 64 |
| `g` | SAQ segment granularity | 64 dimensions |
| `n` | number of 64-d blocks, `D_p / g` | GIST 15 |
| `B` | average bits per dimension | usually 3, 4, or 5 |
| `K` | IVF cluster count | GIST full 4096, many samples 512 |
| `S` | number of SAQ segments | plan-dependent |
| `b_s` | bitwidth of segment `s` | 0 to 13 |
| `P0` | SAQ default segment plan | DP output |
| `P` | candidate/custom segment plan | direction-dependent |
| `Q` | number of held-out evaluation queries | usually dataset default |
| `k` | retrieval cutoff | R@100 for GIST/DEEP/audio/word2vec, R@10 for CIFAR |
| `nprobe` | number of IVF clusters scanned | setting-dependent |

Code constants:

```text
kDimPaddingSize = 64
KMaxQuantizeBits = 13
KFastScanSize = 32
positive-segment factor overhead = 64 bits
```

Source:

```text
saqlib/defines.hpp
saqlib/quantization/saq_data.hpp
```

---

## 8. SAQ Default Planner Formula

SAQ's default dynamic program minimizes a variance-risk proxy.

For a positive-bit segment `[a, b)` with bitwidth `r`:

```text
risk([a,b), r) = sum_{i=a}^{b-1} variance_i / 2^r
```

For a zero-bit tail:

```text
risk([a,D), 0) = sum_{i=a}^{D-1} variance_i
```

The DP state in the code is conceptually:

```text
f[num_segments][block_index][used_bits] = minimum risk so far
```

The transition chooses:

```text
next interval length j
bitwidth r in {1, ..., 13}
```

Code:

```text
saqlib/quantization/saq_data.hpp
  SaqDataWrapper::dynamic_programming(...)
```

Speaker notes:

- SAQ's default objective is sensible: more variance should get more bits.
- But this objective is not explicitly recall, QPS, graph traversal stability, or search-time cost.

---

## 9. SAQ Planner Complexity

Let:

```text
n = D_p / 64
C = floor(B * D_p + 64)
R = KMaxQuantizeBits = 13
S_max = n/2 when B >= 2 in the current code
```

The implementation enumerates:

```text
segment count ns
current block i
used bit budget c
next segment length j
bitwidth r
```

Conservative complexity:

```text
time   = O(S_max * n * C * n * R)
memory = O(S_max * n * C)
```

For GIST B=4:

```text
D_p = 960
n = 15
C = 4 * 960 + 64 = 3904 bits
R = 13
```

This DP is offline and cheap compared with full index construction, but it only
optimizes the variance-risk proxy.

Speaker notes:

- This complexity matters because many proposed follow-ups modify or replace this DP.
- A new DP objective is acceptable only if its objective has a defensible mechanism.

---

## 10. Running Example: Why The Follow-Up Is Hard

SAQ default for GIST full / K4096 / B=4:

```text
P0 = 64:11,192:6,320:4,256:2,128:0
```

A tempting idea is:

```text
Maybe a nearby plan can be faster or more accurate.
```

But any custom plan must answer:

```text
1. Does it improve recall or preserve recall?
2. Does it improve QPS or memory traffic?
3. Does it avoid extra index/search overhead?
4. Does it generalize beyond one dataset?
5. Is the selection rule query-unaware?
6. Is it more than parameter tuning around SAQ?
```

This is the standard used in the rest of the deck.

---

## 11. Correctness Base: Not A Research Contribution

The clean base branch preserves two correctness fixes:

```text
1. positive 1-bit segment packing support
2. padded-lane finite block-min search mode
```

Relevant flags:

```text
-searcher_safe_block_min_mode=2
```

Meaning:

```text
0 = native behavior
1 = scalar finite valid-lane block minimum
2 = SIMD finite valid-lane block minimum
```

Code paths:

```text
src/define_options.h
saqlib/quantization/saq_searcher.hpp
src/test_qps.cpp
src/test_relative_error.cpp
```

Speaker notes:

- These fixes are necessary for fair evaluation.
- They should not be presented as novelty.

---

## 12. Attempt 1: Default-Neighborhood Fixed Policy

Research question:

```text
Can we improve SAQ by searching a small local neighborhood around its default
plan using only base/index artifacts, without representative query workloads?
```

Method sketch:

```text
SAQ default plan P0
  -> classify default-plan shape
  -> generate local candidate neighborhood N(P0)
  -> score candidates with data-only boundary pairs
  -> promote, reject, or abstain
```

Key code in the old fixed-policy branch:

```text
script/generate_default_neighborhood_plans.py
script/score_default_neighborhood_plans.py
script/sweep_data_boundary_pairs.py
script/run_fixed_policy_matrix.py
```

Core formula for boundary-pair weighting:

```text
weight = exp(-margin / tau)
margin = exact_distance(negative) - exact_distance(positive)
```

Variables:

```text
tau = distance-margin temperature used by scorer grid
positive = closer member of a local boundary pair
negative = farther member of a local boundary pair
```

Speaker notes:

- This direction is query-unaware because it uses base vectors as pseudo-queries.
- The weakness is that candidate families and scorer thresholds look empirical.

---

## 13. Fixed Policy: Running Example

GIST full / K4096 / B=4.

Default:

```text
64:11,192:6,320:4,256:2,128:0
```

Selected local candidate:

```text
128:9,320:5,320:3,192:0
```

What changed:

```text
head widened:             64 -> 128 dimensions
positive segments reduced: 4 -> 3
zero tail expanded:       128 -> 192 dimensions
```

Scorer signal:

```text
recall-risk = 0.9071
speed-proxy = 0.7792
role = conservative_eligible
```

Measured validation:

```text
R@100 at nprobe 800: 0.98845 -> 0.98922   delta +0.00077
QPS at nprobe 800:   1013.64 -> 1211.10   ratio 1.1948x
```

Speaker notes:

- This is the old fixed-policy story's best running example.
- It is useful evidence, but not yet a strong independent contribution.

---

## 14. Fixed Policy: Evidence Table

Clean validation table from the old branch:

| setting | decision | selected/tested plan | measured readout |
|---|---|---|---|
| GIST full K4096 B=3 | promote | `64:8,320:5,320:2,256:0` | +0.00159 R@100, 1.1119x QPS at np800 |
| GIST full K4096 B=4 | promote | `128:9,320:5,320:3,192:0` | +0.00077 R@100, 1.1948x QPS at np800 |
| GIST full K4096 B=5 | promote | `128:9,128:7,320:5,320:3,64:0` | +0.00028 R@100, 1.0793x QPS at np800 |
| CIFAR60K B=3 | promote | `128:6,64:4,192:2,128:0` | +0.0004 R@10, 1.0761x QPS at np200 |
| CIFAR60K B=4 | promote | `128:7,256:4,128:0` | +0.0004 R@10, 1.0745x QPS at np200 |
| CIFAR60K B=5 | promote | `128:8,64:6,256:4,64:0` | +0.0008 R@10, 1.0609x QPS at np200 |
| DEEP100K B=4 | reject | `128:4,128:3` | +QPS, but -0.02757 R@100 at np200 |
| DEEP100K B=5 | reject | `128:5,128:4` | +QPS, but -0.01429 R@100 at np200 |
| audio B=4 | abstain | none | single-uniform default |
| word2vec100K B=4 | abstain | none | single-uniform default |

Speaker notes:

- The policy has positive, reject, and abstain outcomes.
- But the positive recall deltas are small, so the contribution cannot be "we improve SAQ universally."

---

## 15. Fixed Policy: Complexity And Overhead

Let:

```text
Cands = number of generated candidate plans
P = number of boundary pairs
S = number of segments
D_p = padded dimension
```

Approximate scoring complexity:

```text
candidate generation: small, local, roughly O(Cands)
boundary-pair scoring: O(Cands * P * S) after feature construction
feature construction: depends on sampled anchors and same-cell neighbors
```

Measured overhead:

| run | candidates | pairs | planner runtime | qps curve geomean |
|---|---:|---:|---:|---:|
| GIST K4096 B=3 | 2 | 14740 | 145.265 s | 1.1077 |
| GIST K4096 B=4 | 5 | 14740 | 150.580 s | 1.1511 |
| GIST K4096 B=5 | 5 | 14740 | 149.590 s | 1.0668 |
| CIFAR B=3 | 4 | 1068 | 8.562 s | 1.0528 |
| DEEP B=4 | 2 | 1904 | 5.804 s | 1.0802, but rejected for recall |

Conclusion:

```text
The scorer cost is large relative to the small metric gains.
This weakens novelty and practical value.
```

Speaker notes:

- The fixed-policy direction generated useful evidence but looks too much like empirical tuning.

---

## 16. Attempt 2: Mixed Shared Local Plans

Research question:

```text
Can IVF clusters with different residual profiles share a small number of
local SAQ plans, improving local residual quantization without learning from
queries?
```

Core assignment rule:

```text
assign(c) = argmin_P cost(residual_profile_c, P)
```

Where:

```text
c = IVF cluster id
P = one shared plan from a small family
residual_profile_c = variance/error profile of vectors in cluster c
M = number of shared plans, tested M in {2, 4, 8}
```

Key code in old branch:

```text
script/cluster_residual_feasibility_matrix.py
shared-plan index materialization code in saqlib/ and src/
```

Method constraint:

```text
No representative queries.
Only base PCA vectors, IVF centroids, cluster ids, and residual profiles.
```

Speaker notes:

- This direction tests whether SAQ's single global plan is locally mismatched with IVF residual structure.
- It is more structural than fixed-policy local candidate search, but it changes the search architecture.

---

## 17. Shared Local Plans: Offline Signal

Eligibility matrix:

| case | B | global plan | local-oracle ratio | small M | small cost-assigned | retention | decision |
|---|---:|---|---:|---:|---:|---:|---|
| GIST full K4096 | 3 | `64:9,192:5,320:3,192:1,192:0` | 0.9581 | 4 | 0.9627 | 0.889 | continue |
| GIST full K4096 | 4 | `64:11,192:6,320:4,256:2,128:0` | 0.9420 | 4 | 0.9435 | 0.974 | continue |
| GIST full K4096 | 5 | `64:11,192:7,320:5,320:3,64:0` | 0.9606 | 4 | 0.9640 | 0.915 | continue |
| CIFAR60K B=3 | `64:8,128:4,192:2,128:0` | 0.9641 | 2 | 0.9654 | 0.966 | continue |
| DEEP/audio/word2vec | B=3/4/5 | mostly compact or uniform | near 1.000 | 2 | 1.000 | 0.000 | abstain |

Interpretation:

```text
GIST and some CIFAR cases show local residual structure.
DEEP, audio, and word2vec do not show useful local-plan opportunity.
```

Speaker notes:

- The signal is shape-dependent.
- Offline proxy improvement alone is not enough; search-time overhead decides whether it is useful.

---

## 18. Shared Local Plans: End-To-End Result

GIST full / K4096 / B=4, safe search, R@100, nprobe 200.

| index | R@100 | QPS | QPS ratio | index size |
|---|---:|---:|---:|---:|
| SAQ default | 0.94469 | 2677.16 | 1.0000 | 570M |
| shared local M4 | 0.94548 | 2434.73 | 0.9094 | 573M |
| cost-aware M4 | 0.94485 | 2398.13 | 0.8958 | 567M |

Runtime decomposition:

| index | fast bit ratio | accurate bit ratio | accurate segment eval ratio | distinct plans/query |
|---|---:|---:|---:|---:|
| shared local M4 | 0.9741 | 0.9097 | 0.9853 | 2.907 |
| cost-aware M4 | 0.9547 | 0.8809 | 0.8989 | 3.336 |

Key conclusion:

```text
Measured work decreases, but QPS also decreases.
The likely cause is mixed-plan overhead: multiple query-side estimator states,
lookup-table setup paths, and worse cache/layout locality.
```

Speaker notes:

- This is valuable negative evidence.
- It says local residual mismatch exists, but naive local-plan materialization is not a good system design.

---

## 19. Shared Local Plans: Complexity

Offline planning:

```text
K = number of IVF clusters
M = shared plan count
n = D_p / 64 blocks
C = bit budget
R = max bits
```

A local per-cluster DP can cost approximately:

```text
O(K * S_max * n * C * n * R)
```

Shared assignment after plans are generated:

```text
O(K * M * cost_eval)
```

Search-time problem:

```text
default SAQ: one plan, one query-side estimator state
shared plans: up to M plan-specific estimator states per query
```

Observed on GIST B=4:

```text
2.907 to 3.336 distinct plan states per query
```

Conclusion:

```text
The complexity bottleneck is not only nominal distance work.
The architecture introduces per-query dispatch and setup overhead.
```

---

## 20. Attempt 3: Single-Global Segment-Cost DP

Research question:

```text
Can we keep one global SAQ plan but add search-time cost awareness to the
planner objective?
```

To avoid arbitrary weights, we did not start with:

```text
risk + lambda * cost
```

Instead, we built Pareto frontiers for separate static cost terms:

```text
positive_dim
total_code_bit_volume
accurate_extra_bit_volume
positive_segments
segment_factor_bits
zero_tail_risk
```

Key code in old branch:

```text
script/global_segment_cost_frontier.py
```

Core risk formula:

```text
risk([a,b), r) = sum variance / 2^r
```

Speaker notes:

- This direction was designed to avoid mixed-plan dispatch overhead.
- It asks whether the global plan itself can be made more cost-aware.

---

## 21. Global Cost DP: Offline Frontier Result

B=4 snapshot:

| dataset | SAQ default plan | positive dim | positive segments | code bit volume | default dominated? | closest lower code-volume risk ratio |
|---|---|---:|---:|---:|---|---:|
| GIST full K4096 | `64:11,192:6,320:4,256:2,128:0` | 832 | 4 | 3648 | no | 1.0100 |
| GIST sample100k | same | 832 | 4 | 3648 | no | 1.0099 |
| CIFAR60K | `64:9,192:5,128:3,128:0` | 384 | 3 | 1920 | no | 1.1104 |
| DEEP sample100k | `64:6,192:3` | 256 | 2 | 960 | no | 1.0164 |
| audio K4096 | `192:4` | 192 | 1 | 768 | no | 2.0000 |
| word2vec sample100k | `320:4` | 320 | 1 | 1280 | no | 1.0319 |

Main result:

```text
No lower-cost plan dominated the SAQ default at no worse variance-risk.
```

Speaker notes:

- This weakens the simplest global cost-aware planner story.
- GIST had near-frontier alternatives, so we still checked end to end.

---

## 22. Global Cost DP: End-To-End Check

GIST full / K4096 / B=4, safe search, R@100.

Plans:

| label | plan | offline role |
|---|---|---|
| default | `64:11,192:6,320:4,256:2,128:0` | SAQ minimum-risk plan |
| code-volume candidate | `64:10,128:7,192:5,192:3,256:2,128:0` | lower code volume, risk ratio 1.0100 |
| positive-dim candidate | `64:10,128:7,192:5,384:3,192:0` | lower positive dimension, risk ratio 1.0116 |

Results:

| nprobe | label | R@100 | QPS | QPS ratio |
|---:|---|---:|---:|---:|
| 100 | default | 0.86604 | 4275.79 | 1.0000 |
| 100 | code-volume | 0.86630 | 4031.72 | 0.9429 |
| 100 | positive-dim | 0.86639 | 4212.68 | 0.9852 |
| 200 | default | 0.94469 | 2732.35 | 1.0000 |
| 200 | code-volume | 0.94506 | 2503.10 | 0.9161 |
| 200 | positive-dim | 0.94537 | 2673.65 | 0.9785 |
| 400 | default | 0.97999 | 1642.83 | 1.0000 |
| 400 | code-volume | 0.98092 | 1499.40 | 0.9127 |
| 400 | positive-dim | 0.98139 | 1620.92 | 0.9867 |

Conclusion:

```text
Slight recall gain, no QPS gain.
Static cost proxies do not transfer reliably to search-time efficiency.
```

---

## 23. Global Cost DP: Complexity

Offline frontier generation:

```text
enumerate SAQ DP candidate plans
evaluate variance risk and each static cost metric
filter metric-specific Pareto frontiers
```

Approximate complexity:

```text
DP candidate enumeration: O(S_max * n * C * n * R)
frontier filtering: O(P log P) per cost metric
```

Where:

```text
P = number of retained candidate states/plans
```

Why the direction stopped:

```text
The complexity is acceptable.
The issue is not runtime.
The issue is objective validity: static code-volume or segment-count terms did
not predict real QPS benefit.
```

Speaker notes:

- This is a clean negative result.
- It tells us that a planner contribution needs a better model of search execution, not another static cost term.

---

## 24. Attempt 4: Fac-Error Planner Objective

Research question:

```text
Does SAQ's variance-risk proxy mismatch measured CAQ/SAQ segment error?
```

Measurement quantities:

```text
variance proxy = sum(segment variance) / 2^bits
raw SSE
scale-aligned SSE
direction loss = 1 - cos(o, o_a)^2
CAQ fac-error
```

Key code in old branch:

```text
src/measure_planner_proxy.cpp
script/summarize_planner_proxy.py
script/falsify_fac_error_dp.py
```

Candidate enumeration:

```text
all contiguous 64-dimensional block intervals
all bitwidths from 0 to 13
deterministic 1024-row or 2048-row residual sample
```

Speaker notes:

- This is closer to SAQ's core objective than static cost DP.
- It asks whether the variance proxy itself is wrong.

---

## 25. Planner Proxy Measurement Result

SAQ's variance proxy strongly ranks energy-weighted residual error.

| dataset | aligned-SSE Spearman, all bits | aligned-SSE Spearman, within-bit mean | discordant pairs, within-bit mean |
|---|---:|---:|---:|
| audio K4096 | 0.9113 | 1.0000 | 0.0000 |
| CIFAR60K | 0.9624 | 0.9979 | 0.0080 |
| DEEP sample100k | 0.9651 | 1.0000 | 0.0000 |
| GIST sample100k | 0.9684 | 0.9981 | 0.0123 |
| word2vec sample100k | 0.9917 | 0.9452 | 0.0782 |

Direction-only mismatch:

| dataset | direction-loss Spearman within-bit | fac-error Spearman within-bit |
|---|---:|---:|
| audio K4096 | 0.4769 | 0.7143 |
| CIFAR60K | 0.5516 | 0.9505 |
| DEEP sample100k | 0.5189 | 0.8294 |
| GIST sample100k | 0.5234 | 0.9753 |
| word2vec sample100k | 0.7412 | 0.9838 |

Interpretation:

```text
The obvious measured-SSE replacement objective is not promising.
The only visible gap is direction quality, but its system relevance is unclear.
```

---

## 26. Fac-Error DP Falsification

We replaced SAQ variance cost with measured fac-error cost in the same DP.

Fac-error DP changed plans on GIST and CIFAR at B=4:

| dataset | variance plan | fac-error plan | changed? |
|---|---|---|---|
| audio K4096 | `192x4` | `192x4` | no |
| CIFAR60K | `64x9_192x5_128x3_128x0` | `128x8_320x3_64x0` | yes |
| DEEP sample100k | `64x6_192x3` | `64x6_192x3` | no |
| GIST sample100k | `64x11_192x6_320x4_256x2_128x0` | `192x9_512x4_256x0` | yes |
| word2vec sample100k | `320x4` | `320x4` | no |

This avoided the trivial negative outcome that the objective always reproduces SAQ.

But end-to-end GIST recall-matched evaluation failed.

Speaker notes:

- This is a good falsification structure: first ask whether the objective changes the plan; then evaluate only the changed plan.

---

## 27. Fac-Error GIST Recall-Matched Check

GIST sample100k / K512 / B=4 / R@100 / 24 threads.

Default target:

```text
SAQ variance, nprobe=200:
R@100 = 0.99132
QPS = 9215.208
```

Fac-error custom plan:

```text
192x9_512x4_256x0
```

Result:

| plan | nprobe | R@100 | QPS | QPS vs default |
|---|---:|---:|---:|---:|
| SAQ variance | 200 | 0.99132 | 9215.208 | 1.000x |
| fac-error | 200 | 0.99059 | 12334.094 | 1.338x |
| fac-error | 240 | 0.99084 | 10957.260 | 1.189x |
| fac-error | 280 | 0.99091 | 9875.544 | 1.072x |
| fac-error | 300 | 0.99091 | 9422.062 | 1.022x |
| fac-error | 320 | 0.99091 | 8956.573 | 0.972x |

Conclusion:

```text
The custom plan does not recover default recall before crossing below default QPS.
```

---

## 28. Fac-Error Direction: Complexity

Let:

```text
R_s = sampled residual vectors or residual pairs
n = D_p / 64 blocks
B_w = number of tested bitwidths, usually 14 for 0..13
I = n(n+1)/2 contiguous intervals
```

Measurement complexity:

```text
O(R_s * B_w * sum interval lengths)
```

Equivalent upper view:

```text
O(R_s * B_w * n^3 * 64)
```

because all contiguous intervals are tested.

DP complexity after measurement:

```text
O(S_max * n * C * n * R)
```

Why it stopped:

```text
Even when measurement moves the plan, the first changed GIST plan produces a
speed/recall tradeoff, not a recall-matched improvement.
```

Speaker notes:

- The overhead is acceptable for an offline study, but not justified if the outcome is only a tradeoff already available by changing nprobe or budget.

---

## 29. Attempt 5: Search-Procedure Analysis

Research question:

```text
Can SAQ's current IVF search path be improved by a query-unaware estimator
scheduling or pruning rule?
```

Instrumentation added in old branch:

```text
runtime profile counters in test_qps
profile_segment_order
profile_variance_bound
```

Search path quantities:

```text
variance stage: cheap lower estimate per block
fast stage: 1-bit estimate over positive segments
accurate stage: full-bit segment refinement
result pool: top-k candidate maintenance
```

Key code:

```text
saqlib/quantization/saq_searcher.hpp
saqlib/quantization/saq_estimator.hpp
src/test_qps.cpp
```

Speaker notes:

- This direction asked whether a method can be found without changing the index format or plan.

---

## 30. Runtime Profile Evidence

GIST sample100k / K512 / B=4 / default plan:

```text
64x11_192x6_320x4_256x2_128x0
```

| nprobe | R@100 | QPS | scanned candidates/query | accurate candidates/query |
|---:|---:|---:|---:|---:|
| 160 | 0.99036 | 10119.473 | 37339.7 | 2696.3 |
| 200 | 0.99132 | 9192.221 | 45810.0 | 2767.4 |
| 240 | 0.99153 | 8183.555 | 54044.2 | 2805.3 |

Derived ratios:

| nprobe | variance-pruned / blocks | fast-pruned / post-variance blocks | accurate candidates / scanned candidates | early exits / accurate candidate |
|---:|---:|---:|---:|---:|
| 160 | 0.14% | 45.29% | 7.22% | 83.91% |
| 200 | 0.27% | 52.02% | 6.04% | 84.32% |
| 240 | 0.45% | 57.60% | 5.19% | 84.52% |

Interpretation:

```text
Fast-stage pruning and accurate-stage early exit already do useful work.
Variance pruning is almost inactive.
```

---

## 31. Segment-Order Counterfactual

Question:

```text
Is SAQ's default PCA/bit segment order suboptimal for progressive pruning?
```

Tested orders:

```text
pca
reverse
bit_desc
dim_desc
cost_asc
risk_per_cost_desc
```

At nprobe 200, deltas relative to default `pca`:

| order | recall delta | fast-call delta | accurate-call delta | fast-bit delta |
|---|---:|---:|---:|---:|
| reverse | -0.00092 | +47.41% | +167.81% | +69.06% |
| bit_desc | 0.00000 | 0.00% | 0.00% | 0.00% |
| dim_desc | -0.00091 | +47.39% | +148.07% | +69.04% |
| cost_asc | +0.00002 | +1.34% | +0.48% | +1.78% |
| risk_per_cost_desc | 0.00000 | 0.00% | 0.00% | 0.00% |

Conclusion:

```text
Default PCA/bit order is already tied for lowest work among simple
hyperparameter-free alternatives.
```

---

## 32. Variance-Bound Inactivity

Final search-procedure measurement:

```text
Why does the variance stage prune less than 0.5% of blocks?
```

Results:

| nprobe | blocks | finite-boundary blocks | variance-pruned blocks | variance-prune rate | fast-prune rate after variance |
|---:|---:|---:|---:|---:|---:|
| 160 | 1,245,446 | 1,241,443 | 1,750 | 0.1405% | 45.28% |
| 200 | 1,530,007 | 1,526,004 | 4,104 | 0.2682% | 52.02% |
| 240 | 1,807,095 | 1,803,092 | 8,173 | 0.4523% | 57.62% |

Gap to the top-k boundary:

| nprobe | median relative gap | 90th-percentile relative gap |
|---:|---:|---:|
| 160 | 0.7467 | 0.8635 |
| 200 | 0.7427 | 0.8585 |
| 240 | 0.7386 | 0.8537 |

Interpretation:

```text
Variance minima are usually far below the current top-k boundary.
Useful pruning would require removing a large fraction of conservative slack,
which has no safe derivation in the current evidence.
```

---

## 33. Search-Procedure Complexity

Let:

```text
Q = number of queries
nprobe = scanned IVF clusters per query
B_c = total 32-lane blocks scanned across selected clusters
S_pos = number of positive-bit SAQ segments
R_acc = number of candidates entering accurate refinement
S_acc = average accurate segments evaluated per refined candidate
```

Simplified per-query work:

```text
variance stage: O(B_c)
fast stage:     O(B_c * segments evaluated before block pruning)
accurate stage: O(R_acc * S_acc)
```

Measured GIST B=4 at nprobe 200:

```text
B_c ~= 1530 blocks/query
fast segment calls ~= 4135/query
R_acc ~= 2767 candidates/query
S_acc ~= 1.71 segments/candidate
```

Conclusion:

```text
The easy scheduling opportunities are already mostly captured.
Simple reordering and arbitrary variance-bound calibration are not defensible.
```

---

## 34. Pivot: Why Graph Traversal Is A Different Question

IVF search:

```text
centroid probing determines candidate clusters
SAQ estimates mostly filter and rerank vectors inside selected clusters
```

Graph ANNS:

```text
approximate distance can determine which node is expanded next
```

That changes the role of quantization error:

```text
IVF error affects scoring among reached candidates.
Graph error can affect the path through the graph.
```

Current research question:

```text
Can SAQ-style progressive compressed distance estimation stabilize graph
frontier decisions, and does it provide a refinement/work tradeoff beyond
RaBitQ/SymphonyQG-style graph quantization?
```

Speaker notes:

- This is more structurally different from SAQ's paper setting.
- But related work is strong, so the novelty gate must be strict.

---

## 35. Related Work Gate For Graph Direction

Important related work:

```text
SymphonyQG
NGT-QG
Routing-Guided Learned Product Quantization
```

What SymphonyQG already covers:

```text
graph-side neighbor code layout
FastScan distance estimates during graph traversal
RaBitQ-style graph quantization
current-vertex residual normalization
multiple estimates to reduce missed nearest neighbors
```

Therefore unsafe claims:

```text
first quantization + graph index integration
first estimated-distance graph traversal
first graph-specific RaBitQ normalization
```

Narrow possible SAQ-specific claim:

```text
SAQ's segmented progressive estimator may offer a better frontier refinement
axis than a single-stage RaBitQ/FastScan-style graph estimator.
```

Speaker notes:

- This is why the current branch immediately built a SymphonyQG baseline path.

---

## 36. Graph Replay Measurement Design

We avoid full graph integration first.

Diagnostic harness:

```text
build fixed exact-kNN adjacency on a deterministic subset
for query q and current graph node u:
  compare exact and compressed estimates over N(u)
```

Metric:

```text
v_exact = argmin_{v in N(u)} d_exact(q, v)
rank_est(v_exact) = rank of v_exact under estimator distance
```

Reported:

```text
top1 disagreement rate
mean rank of exact-best neighbor
p50/p90/p99 rank
top-L containment curve
average distinct IVF clusters per expansion event
```

Key code:

```text
src/profile_graph_frontier.cpp
src/CMakeLists.txt target profile_graph_frontier
saqlib/quantization/saq_estimator.hpp
```

Complexity:

```text
exact kNN adjacency build: O(M^2 * D) for subset size M
replay scoring: O(E * degree * estimator_cost)
```

Where:

```text
E = number of (query, root) expansion events
degree = fixed graph degree, currently 32
```

---

## 37. Graph Replay: First GIST Result

GIST sample50k / K512 / B=4:

```text
plan = 64:11,192:6,320:4,256:2,128:0
subset = 4096
degree = 32
queries = 100
roots per query = 8
events = 800
```

Initial weak baseline comparison:

| estimator | bits/candidate | top1 disagreement | mean rank | p90 rank | top8 containment |
|---|---:|---:|---:|---:|---:|
| global `rabitq_style_proxy` | 960 | 0.90625 | 12.4812 | 27 | 0.44625 |
| `saq_fast` | 832 | 0.46125 | 2.2575 | 5 | 0.98125 |
| `saq_prefix_acc1` | 1472 | 0.13750 | 1.1725 | 2 | 1.00000 |
| `saq_prefix_acc2` | 2432 | 0.02750 | 1.0300 | 1 | 1.00000 |
| `saq_full` | 3648 | 0.00625 | 1.00625 | 1 | 1.00000 |

Interpretation:

```text
SAQ staged estimates recover local expansion order much better than the weak
global proxy, but the proxy was not a faithful SymphonyQG baseline.
```

---

## 38. SymphonyQG Sanity Baseline

Local official SymphonyQG source:

```text
/rwproject/kdd-db/kluaq/SymphonyQG
commit 6124ddb
```

Small GIST baseline:

```text
N = 10,000 base vectors
Q = 100 queries
D = 960
top-k = 10
degree = 32
build EF = 100
build iterations = 2
```

Result:

| search EF | Recall@10 | QPS |
|---:|---:|---:|
| 20 | 0.891 | 37173.659 |
| 40 | 0.960 | 29269.393 |
| 80 | 0.983 | 20404.281 |
| 120 | 0.994 | 16214.257 |
| 200 | 0.997 | 10358.608 |

Interpretation:

```text
The official implementation builds and searches locally.
This is not directly comparable to SAQ replay, but it enables source-level
baseline extraction.
```

---

## 39. SymphonyQG Estimator Formula

For current graph vertex `c`, outgoing neighbor `x`, query `q`:

```text
r = x - c
s_i = +1 if r_i > 0, otherwise -1
fac_norm = 1 / sqrt(D)
fac_x0 = <r, s * fac_norm> / ||r||
fac_x1 = <c, s * fac_norm>
x_x0 = ||r|| / fac_x0
triple_x = ||r||^2 + 2 * x_x0 * fac_x1
factor_dq = -2 * x_x0 * fac_norm
factor_vq = factor_dq * sum_i s_i
```

Query is scalar-quantized with `QG_BQUERY = 6`:

```text
width = (max(q) - min(q)) / (2^6 - 1)
q_code_i = round((q_i - min(q)) / width + 0.5)
dot_code = sum_i s_i * q_code_i
```

Extracted distance:

```text
dist(q, x | c) =
    ||q - c||^2
  + triple_x
  + factor_dq * width * dot_code
  + factor_vq * min(q)
```

Source:

```text
SymphonyQG/symqglib/quantization/rabitq.hpp
SymphonyQG/symqglib/qg/qg_query.hpp
SymphonyQG/symqglib/qg/qg_scanner.hpp
SymphonyQG/symqglib/qg/qg.hpp
```

---

## 40. Current Stronger Local Baseline

Implemented in current branch:

```text
src/profile_graph_frontier.cpp
  SymphonyQGVertexProxy
```

What it preserves:

```text
current-vertex residual centering
1-bit residual signs
6-bit query scalar quantization
triple_x / factor_dq / factor_vq formula
```

What it omits:

```text
FHT rotation
padded power-of-two dimension
packed FastScan layout
SIMD lookup table reproduction
SymphonyQG-built graph
```

Complexity:

```text
our formula-level proxy: O(D) per edge
full FastScan-style implementation: O(D / SIMD_width) per edge batch after O(D log D) or implementation-specific query rotation/preparation
```

Speaker notes:

- This is a stronger baseline than the old proxy, but still not full SymphonyQG.
- The next task is fuller baseline alignment.

---

## 41. Stronger Baseline Result

GIST sample50k / K512 / B=4 / subset 4096:

| estimator | bits/candidate | top1 disagreement | mean rank | p90 rank | top4 containment | top8 containment |
|---|---:|---:|---:|---:|---:|---:|
| global `rabitq_style_proxy` | 960 | 0.90625 | 12.4812 | 27 | 0.25625 | 0.44625 |
| `symqg_vertex_proxy` | 960 | 0.87625 | 8.2775 | 19 | 0.38250 | 0.61500 |
| `saq_fast` | 832 | 0.46125 | 2.2575 | 5 | 0.87625 | 0.98125 |
| `saq_prefix_acc1` | 1472 | 0.13750 | 1.1725 | 2 | 0.99750 | 1.00000 |
| `saq_prefix_acc2` | 2432 | 0.02750 | 1.0300 | 1 | 1.00000 | 1.00000 |
| `saq_full` | 3648 | 0.00625 | 1.00625 | 1 | 1.00000 | 1.00000 |

Interpretation:

```text
The stronger vertex-centered baseline improves over the weak global proxy, but
SAQ staged estimates still show much stronger local rank recovery.
```

Strict limitation:

```text
This still does not prove an end-to-end graph method.
It only supports continuing the graph direction to fuller baseline alignment.
```

---

## 42. Current Direction: Fuller SymphonyQG Alignment

Immediate research question:

```text
Does SAQ's segmented progressive estimator retain a graph-frontier
rank-recovery advantage over a closer SymphonyQG/RaBitQ FastScan-style
estimator, rather than only over a formula-level vertex proxy?
```

Next implementation target:

```text
extract or reproduce:
  FHT rotation
  padded dimension
  6-bit query quantization
  current-vertex residual neighbor code
  triple_x / factor_dq / factor_vq
  FastScan-equivalent signed dot product
```

Same-replay comparison:

```text
exact_float
symqg_vertex_proxy
fuller_symqg_fastscan_like
saq_fast
saq_prefix_acc1
saq_prefix_acc2
saq_full
```

Stop condition:

```text
If fuller SymphonyQG closes the rank-recovery gap, the graph direction becomes
limitation evidence rather than a method foundation.
```

---

## 43. Overall Evidence Summary

| direction | evidence | status |
|---|---|---|
| fixed-policy default-neighborhood | GIST/CIFAR small positives, DEEP reject, audio/word2vec abstain; scorer overhead 145-151s on GIST | useful but too empirical |
| mixed shared local plans | residual-local signal; GIST B=4 R@100 +0.00079 but QPS ratio 0.9094 | stopped as main method |
| global static segment-cost DP | SAQ default not dominated; near-frontier GIST plans slightly higher recall but slower | stopped as main method |
| fac-error planner objective | objective changes GIST/CIFAR plans; GIST custom plan faster at same nprobe but not recall-matched | stopped as main method |
| search-procedure scheduling | fast pruning and accurate early exit already strong; variance pruning weak but unsafe to tighten empirically | stopped as main method |
| graph traversal compatibility | SAQ prefix estimates recover exact-best graph neighbor better than formula-level SymphonyQG vertex proxy | active, but baseline not fully aligned |

Speaker notes:

- This table is the main meeting synthesis.
- The active direction is not guaranteed; it is the most defensible remaining question.

---

## 44. What We Should Not Claim

Unsafe claims:

```text
We already have a new quantizer.
We already have a method that universally improves SAQ.
The fixed-policy scorer is a paper-level contribution.
The shared local plan direction improves SAQ end to end.
Static segment-cost DP solves SAQ's planner limitation.
Fac-error DP gives a recall-matched speedup.
Simple search-loop scheduling improves SAQ.
The current graph result proves end-to-end graph-search improvement.
```

Safer claim:

```text
The negative and partial-positive evidence narrows the credible follow-up space.
The current graph direction tests a structural mismatch between SAQ's
IVF-centered progressive estimator and graph traversal decisions, with
SymphonyQG as the required novelty gate.
```

---

## 45. Proposed Meeting Discussion

Decision 1:

```text
Is graph-traversal compatibility the right remaining direction, given the
negative evidence on local plan tuning and IVF search-loop scheduling?
```

Decision 2:

```text
What level of SymphonyQG baseline alignment is enough before proposing a
SAQ-specific graph frontier refinement policy?
```

Decision 3:

```text
If fuller SymphonyQG erases the current advantage, should we pivot to theory
of SAQ/CAQ estimator bounds or to transform objectives beyond PCA?
```

Decision 4:

```text
Should the paper story include the negative evidence as a motivation section,
or keep it only as internal research reasoning?
```

Speaker notes:

- I would ask the advisor to evaluate novelty first, before spending time on end-to-end graph integration.

---

## 46. Recommended Next Step

Do not start full HNSW/DiskANN integration yet.

Recommended next step:

```text
Fuller SymphonyQG baseline alignment / same-replay evaluation.
```

Concrete deliverable:

```text
One profiler update and one evidence note showing whether:
  SAQ staged estimates still beat a closer SymphonyQG/FastScan-style baseline
  on the same fixed GIST graph replay.
```

Pass condition:

```text
SAQ prefix refinement keeps a stable rank-recovery advantage with controlled
bit-read accounting.
```

Fail condition:

```text
A closer SymphonyQG baseline matches or nearly matches SAQ prefix rank recovery.
```

If pass:

```text
Design a SAQ-specific graph frontier refinement rule.
```

If fail:

```text
Record graph direction as limitation evidence and discuss a larger pivot.
```

---

## 47. Backup: One-Slide Running Example

GIST full / K4096 / B=4, SAQ default:

```text
64:11,192:6,320:4,256:2,128:0
```

Old fixed-policy candidate:

```text
128:9,320:5,320:3,192:0
R@100 np800: 0.98845 -> 0.98922
QPS np800:   1013.64 -> 1211.10
```

Why not enough:

```text
small recall delta
handcrafted local candidate families
145-151s planner/scorer overhead on GIST
not a new quantizer or principled planner
```

Current graph running example:

```text
GIST sample50k / K512 / B=4 / subset 4096
symqg_vertex_proxy p90 exact-best rank = 19
saq_fast p90 exact-best rank = 5
saq_prefix_acc1 p90 exact-best rank = 2
```

Why still incomplete:

```text
current SymphonyQG baseline is formula-level, not full FastScan-aligned.
```

---

## 48. Backup: Code Map

Current branch:

```text
SAQ planner:
  saqlib/quantization/saq_data.hpp

SAQ estimator:
  saqlib/quantization/saq_estimator.hpp
  saqlib/quantization/caq/caq_estimator.hpp

SAQ search path:
  saqlib/quantization/saq_searcher.hpp
  src/test_qps.cpp

Graph replay:
  src/profile_graph_frontier.cpp

Correctness/evaluation flags:
  src/define_options.h
```

Historical branches:

```text
fixed policy:
  script/generate_default_neighborhood_plans.py
  script/score_default_neighborhood_plans.py
  script/sweep_data_boundary_pairs.py
  script/run_fixed_policy_matrix.py

shared local plans:
  script/cluster_residual_feasibility_matrix.py

global cost DP:
  script/global_segment_cost_frontier.py

fac-error planner:
  src/measure_planner_proxy.cpp
  script/summarize_planner_proxy.py
  script/falsify_fac_error_dp.py
```

External baseline:

```text
/rwproject/kdd-db/kluaq/SymphonyQG
  symqglib/quantization/rabitq.hpp
  symqglib/qg/qg.hpp
  symqglib/qg/qg_query.hpp
  symqglib/qg/qg_scanner.hpp
```


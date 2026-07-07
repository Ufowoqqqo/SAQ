# Query-Unaware SAQ Follow-Up

Default-Neighborhood Fixed Policy, Boundary-Risk Scoring, and Current Evidence

Date: 2026-07-06

Updated: 2026-07-07

Audience assumption: familiar with vector search / ANNS, not necessarily with
SAQ implementation details.

---

## 1. Meeting Goal

Explain where the SAQ follow-up currently stands.

Main message:

```text
We now have a query-unaware fixed-policy story:
generate small neighborhoods around SAQ's default plan, score them with
data-only boundary risk, promote only safe candidates, and abstain otherwise.
```

Meeting output I want:

- Decide whether this fixed-policy framing is worth developing as the next
  contribution.
- Decide whether the next step should formalize the policy or target
  balanced/middle-plan generation.

---

## 2. SAQ In One Slide

SAQ is a vector quantization method for ANNS / vector databases.

Its core pipeline:

1. Rotate vectors with PCA.
2. Split PCA dimensions into contiguous segments.
3. Allocate different bitwidths to different segments.
4. Use CAQ code adjustment inside each segment.
5. Use multi-stage distance estimation during search.

Why it works:

```text
PCA concentrates variance.
High-variance dimensions get more bits.
Low-variance tail dimensions get fewer bits or zero bits.
```

---

## 3. SAQ's Default Planning Objective

A simplified view of SAQ's segment DP objective:

```text
cost(segment, bits) ~= variance_sum(segment) / 2^bits
```

This is:

- query-unaware;
- simple and efficient;
- aligned with reconstruction / distance-estimation quality.

But it does not directly optimize:

```text
top-k boundary stability
search-time segment cost
local IVF residual behavior after clustering
```

---

## 4. Research Boundary After Advisor Feedback

We stay query-unaware.

Allowed method signals:

```text
base vectors
PCA variances
IVF centroids and cluster ids
cluster residuals
base-as-pseudo-query boundary pairs
quantization plan metadata
```

Not the main method direction:

```text
learning bit allocation from representative query workloads
```

Held-out benchmark queries remain valid for final evaluation.

---

## 5. Current Hypothesis

SAQ's global PCA-variance plan can miss data-only structure that matters for
ANN ranking and search cost.

More concrete:

```text
Global PCA variance, residual reconstruction cost, top-k boundary behavior,
and search-time segment cost can disagree even without using query workloads.
```

So the follow-up question becomes:

```text
Can data-only base/index diagnostics produce better recall/speed segment-plan
candidates than pure global PCA variance?
```

---

## 6. Current Workflow

Fixed-policy pipeline:

```text
SAQ default plan
  -> default-neighborhood candidate generator
  -> data-only boundary-pair scorer
  -> conservative/frontier promotion rule
  -> safe-searcher recall and QPS validation
```

The generator only makes small perturbations around the SAQ default plan.

The policy can also abstain:

```text
single uniform default plan -> no useful local multi-segment neighborhood
```

---

## 7. Planner v3: Data-Only Boundary Risk

Planner v3 samples base vectors as pseudo-queries inside IVF cells.

For each anchor:

1. Find local candidates in the same IVF cell.
2. Form positive/negative pairs around a local rank boundary.
3. Weight tighter pairs more strongly:

```text
weight = exp(-margin / tau)
```

Intuition:

```text
If two candidates are very close in exact distance, quantization error can
easily flip their order.
```

---

## 8. Planner v3 Outputs Roles, Not One Winner

v3 separates two proxy views.

Recall-risk proxy:

```text
boundary cost + pair inversion penalties
```

Speed proxy:

```text
nonzero segment count
total segment count
nonzero dimensional coverage
bitwork
```

Outputs:

```text
raw recall-risk endpoint
speed endpoint
Pareto frontier
role shortlist
```

This is the key framing shift.

---

## 9. Why We Added A Conservative Guard

B=5 `gist_sample100k` exposed a false positive.

Raw v3 recall-risk endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

Measured result under corrected safe searcher:

| plan | np200 R@100 | QPS ratio vs default |
|---|---:|---:|
| default B=5 | 0.99478 | 1.000x |
| raw v3 endpoint | 0.99470 | 0.942x |
| `b5_rank0` | 0.99521 | 0.993x |

Raw recall-risk alone was not safe enough for promotion.

---

## 10. Promotion Rule

The conservative guard is a promotion-layer rule.

It rejects a candidate if it is worse than default on:

```text
weighted soft-inversion ratio
weighted pair-ratio mean
speed-proxy ratio
```

For borderline cases, we also allow a narrow `frontier_like` role:

```text
low recall-risk score
non-worse speed proxy
pair ratios only marginally above default
```

Otherwise, the method abstains.

---

## 11. Full GIST K4096 B=4: Endpoint Story

Raw v3 Pareto endpoints:

| role | plan | proxy readout |
|---|---|---|
| recall endpoint | `64:9,64:7,128:6,320:4,256:2,128:0` | best recall-risk, slower |
| speed endpoint | `128:9,320:5,320:3,192:0` | fastest proxy, positive recall |

Measured with corrected safe searcher, original-space R@100, nprobe=800:

| plan | R@100 | QPS | QPS ratio |
|---|---:|---:|---:|
| default | 0.98845 | 1013.64 | 1.000x |
| `v2_split64` | 0.98975 | 918.44 | 0.906x |
| `filtered_new` | 0.98948 | 1092.29 | 1.078x |
| `compact_k4096` | 0.98922 | 1211.10 | 1.195x |

Interpretation:

```text
v3 exposes endpoints.
The guard promotes a safer speed/recall candidate.
It is not a best-recall selector.
```

---

## 12. GIST Full K4096 Budget Ladder

After fixing the 1-bit default build path, GIST is positive across B=3/B=4/B=5.

| budget | promoted plan | R@100 result | QPS result |
|---:|---|---|---|
| B=3 | `64:8,320:5,320:2,256:0` | np800: 0.97996 -> 0.98155 | +11.2% |
| B=4 | `128:9,320:5,320:3,192:0` | np800: 0.98845 -> 0.98922 | +19.5% |
| B=5 | `128:9,128:7,320:5,320:3,64:0` | np800: 0.99319 -> 0.99347 | +7.9% |

This is the strongest current positive family.

---

## 13. CIFAR Budget Ladder

CIFAR uses R@10, but it is also positive across B=3/B=4/B=5.

| budget | promoted plan | R@10 result | QPS result |
|---:|---|---|---|
| B=3 | `128:6,64:4,192:2,128:0` | np200: 0.9617 -> 0.9621 | +7.6% |
| B=4 | `128:7,256:4,128:0` | np200: 0.9781 -> 0.9785 | +7.4% |
| B=5 | `128:8,64:6,256:4,64:0` | np200: 0.9865 -> 0.9873 | +6.1% |

These are small but consistent gains.

Important detail:

```text
CIFAR uses frontier_like promotion, not strict conservative promotion.
```

This suggests the hard 1.0 pair-ratio cutoff needs a narrow tolerance.

---

## 14. Negative And Abstention Evidence

DEEP is a rejected negative/control.

| run | candidate | measured result |
|---|---|---|
| DEEP100K B=4 | `128:4,128:3` | +8.9% QPS, but -0.0276 R@100 at np200 |
| DEEP100K B=5 | `128:5,128:4` | +10.4% QPS, but -0.0143 R@100 at np200 |

The scorer rejected these; they were evaluated only as risky fallbacks.

Audio and word2vec are abstention cases:

```text
audio B=3/4/5: single uniform default -> abstain
word2vec B=3/4/5: single uniform default -> abstain
```

---

## 15. Applicability Boundary

Current method is applicable when SAQ's default plan has:

```text
multi-segment bit ladder
zero tail
enough middle/tail positive dimensions to redistribute
```

Current method should abstain when:

```text
default is already a single uniform segment
```

Current method should reject:

```text
speed-only perturbations that hurt boundary-risk proxies
```

This boundary is now part of the contribution candidate.

---

## 16. GIST B=3 Implementation Caveat

GIST B=3 originally crashed because the default plan includes a 1-bit segment:

```text
64:9,192:5,320:3,192:1,192:0
```

Root cause:

```text
encoder exported code only for num_bits > 1
packer required code for every num_bits > 0
```

We fixed this locally to make SAQ's own legal default plan buildable.

Important framing:

```text
The 1-bit fix is not the planner contribution.
It only unblocks fair default-vs-custom validation.
```

---

## 17. Current Claim

What we can claim now:

1. Query-unaware boundary-risk scoring is useful.
2. Fixed-policy default-neighborhood selection is positive on GIST and CIFAR
   budget ladders.
3. The policy correctly rejects DEEP risky speed-only changes.
4. The policy abstains on audio/word2vec single-uniform defaults.
5. The method has a clearer applicability boundary than before.

What we should not claim:

```text
We have a universal replacement for SAQ's planner.
```

Better claim:

```text
We have a query-unaware policy with positive, negative, and abstention evidence.
```

---

## 18. Remaining Gap 1: Formal Method Definition

The fixed policy still needs to be made crisp.

Questions:

```text
How exactly do we classify default-plan shape?
Which candidate families are allowed?
When is conservative vs frontier_like promotion valid?
What thresholds define abstention?
```

This is the most meeting-ready next step.

---

## 19. Remaining Gap 2: Middle Plans

Full GIST B=4 has a measured balanced point:

```text
filtered_new = 64:10,320:6,384:3,192:0
```

Measured:

```text
R@100 np800 = 0.98948
QPS ratio   = 1.078x
```

Existing v3 candidate generation did not directly rediscover this plan.

So candidate generation still matters.

---

## 20. Proposed Next Step

Recommended before the next meeting:

```text
Formalize the fixed policy and produce one clean validation table.
```

Method skeleton:

1. Classify default-plan shape.
2. Generate allowed default-neighborhood candidates.
3. Score with data-only boundary pairs.
4. Promote conservative/frontier candidates.
5. Abstain otherwise.

Then decide whether to extend toward:

```text
middle-plan generation
cluster-local plans
non-contiguous / reordered segmentation
```

---

## 21. Discussion Questions

1. Is this fixed-policy framing strong enough for a contribution?

```text
SAQ default planning can be improved by data-only boundary-risk diagnostics,
but only under a clear default-plan shape boundary.
```

2. Is `frontier_like` acceptable as a calibrated promotion role, or should the
   method use only strict conservative promotion?

3. Should the next contribution target:

```text
formal fixed policy
balanced middle-plan generation
cluster-local plan families
```

---

## Backup: Key Artifacts

Reports:

```text
docs/saq_stage_synthesis_v3_conservative_2026_07_06.md
docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md
docs/saq_default_neighborhood_applicability_scan_2026_07_06.md
docs/saq_cifar_budget_holdout_2026_07_06.md
docs/saq_gist_budget_holdout_2026_07_06.md
docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md
docs/saq_gist_full_k4096_B4_v3_conservative_audit_2026_07_06.md
docs/saq_gist_full_k4096_B4_middle_role_analysis_2026_07_06.md
```

Implementation:

```text
script/generate_default_neighborhood_plans.py
script/score_default_neighborhood_plans.py
script/run_default_neighborhood_cross_dataset.py
script/sweep_data_boundary_pairs.py
```

---

## Backup: Evaluation Rule

Measured recall/QPS claims use:

```text
-searcher_safe_block_min_mode=2
```

Reason:

Earlier native multi-segment search measurements were affected by padded-lane
block-min behavior. Corrected safe searcher masks invalid lanes and replaces
non-finite lanes before SIMD min.

---

## Backup: Short Meeting Script

1. SAQ uses global PCA variance to allocate bits across contiguous segments.
2. We kept the follow-up query-unaware.
3. We generate local neighborhoods around SAQ's own default plan.
4. We score with base-only boundary-risk and speed proxies.
5. Raw v3 endpoints are useful but can false-positive.
6. Conservative/frontier promotion plus abstention gives a clearer policy.
7. GIST and CIFAR budget ladders are positive.
8. DEEP is rejected; audio/word2vec abstain.
9. The 1-bit fix only unblocks fair GIST B=3 validation.
10. The next decision is whether to formalize this fixed policy or push toward
    middle-plan generation.

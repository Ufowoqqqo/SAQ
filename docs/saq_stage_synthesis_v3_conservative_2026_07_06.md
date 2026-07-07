# SAQ Stage Synthesis: Fixed-Policy Evidence And Boundary-Aware Planning

Date: 2026-07-06

Updated: 2026-07-07

## 1. One-Sentence Status

The SAQ follow-up now has a stronger query-unaware story than "we found one
better segment plan":

```text
Use data-only boundary-risk diagnostics to generate and score
default-neighborhood segment plans, then promote only conservative/frontier
candidates and abstain when the default shape has no useful neighborhood.
```

This is still not a final method contribution, but the evidence is now more
structured:

- GIST full K4096 is positive across B=3/B=4/B=5.
- CIFAR is positive across B=3/B=4/B=5.
- DEEP is a useful rejected negative/control.
- audio and word2vec are stable abstention cases under the current generator.
- GIST B=3 also exposed an upstream SAQ 1-bit implementation bug; fixing it
  unblocked fair default-vs-custom validation.

## 2. Research Boundary After Advisor Feedback

The primary direction remains query-unaware. The method should use only signals
available during a normal offline index build:

```text
base vectors
PCA variances
IVF centroids and cluster ids
cluster residuals
base-as-pseudo-query boundary pairs
quantization plan metadata
```

Held-out benchmark queries are still valid for final evaluation, but not for
learning the index-time plan. This keeps the follow-up inside SAQ's own setting
instead of assuming a representative query workload.

## 3. Problem We Are Studying

SAQ's default planner uses a global PCA-variance style objective over contiguous
PCA dimensions. A simplified view is:

```text
segment_cost(segment, bits) ~= variance_sum(segment) / 2^bits
```

This objective is simple and effective, but it does not directly optimize ANN
boundary stability or search-time cost. The current evidence suggests a more
specific limitation:

```text
Global PCA variance, local residual behavior, top-k boundary risk, and
search-time segment cost can disagree even without using query workloads.
```

The practical question is:

```text
Can data-only base/index diagnostics identify segment-plan neighborhoods that
improve the recall/speed tradeoff over SAQ's default plan?
```

## 4. Current Workflow

The current fixed-policy workflow is:

```text
SAQ default plan
  -> default-neighborhood candidate generator
  -> data-only boundary-pair scorer
  -> conservative/frontier promotion rule
  -> safe-searcher recall and QPS validation
```

The default-neighborhood generator makes small, shape-preserving perturbations
around SAQ's own default plan. It is intentionally conservative: it is not
trying arbitrary custom plans, and it abstains when the default is a single
uniform segment with no meaningful local multi-segment structure.

The promotion rule has three outcomes:

```text
conservative_eligible: strong proxy improvement and no worse than default on
                       pair-risk / speed guard terms

frontier_like:         narrow fallback for candidates with low recall-risk and
                       non-worse speed proxy, even if pair ratios are only
                       marginally above 1.0

abstain:               no non-default candidate should be promoted
```

Measured claims use:

```text
-searcher_safe_block_min_mode=2
```

## 5. What Planner v3 Adds

Planner v3 is implemented in:

```text
script/sweep_data_boundary_pairs.py
```

It samples base vectors as pseudo-queries inside IVF cells, forms tight
positive/negative boundary pairs around a local rank boundary, and builds a
margin-weighted risk signal. For each pair, smaller exact margins get larger
weights:

```text
weight = exp(-margin / tau)
```

The planner then evaluates candidate segment plans with two separate views:

1. **Recall-risk proxy**: boundary cost plus pair-level inversion penalties.
2. **Speed proxy**: nonzero segment count, total segment count, nonzero
   dimensional coverage, and bitwork.

The important design change is that v3 does not collapse everything into one
score. It exposes:

```text
raw recall-risk endpoint
speed endpoint
Pareto frontier
role shortlist
```

This remains useful for diagnosis even when the final promoted plan is selected
by a stricter guard.

## 6. Why Conservative Guard Was Needed

The B=5 `gist_sample100k` validation exposed a false positive. The raw v3
recall-risk endpoint was:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

Offline, this looked best by recall-risk score. Measured under the corrected
safe searcher, it was slightly worse and slower:

```text
np200 R@100:
v3 endpoint = 0.99470
default     = 0.99478
b5_rank0    = 0.99521

QPS ratio vs default:
v3 endpoint = 0.942x
```

The conservative guard fixes this at the promotion layer. It does not remove
raw endpoints from diagnostics. It only says that a plan should not be promoted
if it is worse than default on:

```text
weighted soft-inversion ratio
weighted pair-ratio mean
speed-proxy ratio
```

For the false positive:

```text
soft inversion ratio = 1.030461
weighted ratio       = 1.029477
speed proxy ratio    = 1.214129
```

The conservative roles instead selected:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

## 7. Full GIST K4096 B=4 Pareto Readout

The full GIST K4096 B=4 audit gives the clearest endpoint picture.

Raw v3 Pareto endpoints:

| role | plan | readout |
|---|---|---|
| recall-risk endpoint | `64:9,64:7,128:6,320:4,256:2,128:0` | `v2_split64`, best recall-risk proxy, slower |
| speed endpoint | `128:9,320:5,320:3,192:0` | `compact_k4096`, faster and still positive recall |

Measured safe-searcher results at `np800`:

| plan | R@100 | QPS | QPS ratio |
|---|---:|---:|---:|
| default | 0.98845 | 1013.64 | 1.000x |
| `v2_split64` | 0.98975 | 918.44 | 0.906x |
| `filtered_new` | 0.98948 | 1092.29 | 1.078x |
| `compact_k4096` | 0.98922 | 1211.10 | 1.195x |

The conservative guard selects:

```text
compact_k4096 = 128:9,320:5,320:3,192:0
```

because `v2_split64` has `speed_proxy_ratio = 1.215274` and is therefore not a
safe promotion candidate under the speed-aware guard.

The correct interpretation is:

```text
v3 exposes the recall/speed Pareto endpoints.
The conservative guard selects a safer promotion point.
It is not meant to select the highest-recall point.
```

## 8. Cross-Dataset Fixed-Policy Evidence

### GIST Full K4096 Budget Ladder

After the 1-bit segment fix, GIST full K4096 is positive across B=3/B=4/B=5.

| budget | default plan | promoted plan | selection | recall result | QPS result |
|---:|---|---|---|---|---|
| B=3 | `64:9,192:5,320:3,192:1,192:0` | `64:8,320:5,320:2,256:0` | conservative | R@100 np800: 0.97996 -> 0.98155 (+0.00159) | 1043.07 -> 1159.75 (+11.2%) |
| B=4 | `64:11,192:6,320:4,256:2,128:0` | `128:9,320:5,320:3,192:0` | conservative | R@100 np800: 0.98845 -> 0.98922 (+0.00077) | 1013.64 -> 1211.10 (+19.5%) |
| B=5 | `64:11,192:7,320:5,320:3,64:0` | `128:9,128:7,320:5,320:3,64:0` | conservative | R@100 np800: 0.99319 -> 0.99347 (+0.00028) | 988.88 -> 1067.30 (+7.9%) |

This is currently the strongest positive family. It shows that the fixed
policy can repeatedly improve a high-dimensional, multi-segment, zero-tail SAQ
default.

### CIFAR Budget Ladder

CIFAR is smaller and evaluated with R@10, but it is also positive across
B=3/B=4/B=5.

| budget | default plan | promoted plan | selection | recall result | QPS result |
|---:|---|---|---|---|---|
| B=3 | `64:8,128:4,192:2,128:0` | `128:6,64:4,192:2,128:0` | frontier-like | R@10 np200: 0.9617 -> 0.9621 (+0.0004) | +7.6% |
| B=4 | `64:9,192:5,128:3,128:0` | `128:7,256:4,128:0` | frontier-like | R@10 np200: 0.9781 -> 0.9785 (+0.0004) | +7.4% |
| B=5 | `64:10,128:6,256:4,64:0` | `128:8,64:6,256:4,64:0` | frontier-like | R@10 np200: 0.9865 -> 0.9873 (+0.0008) | +6.1% |

The CIFAR results are smaller than GIST, but they matter because they show that
the method is not only a single GIST B=4 accident. They also show that the
strict conservative guard is too rigid: `frontier_like` is needed when pair
ratios are only about 0.1% above default but measured recall/QPS both improve.

### Negative And Abstention Cases

DEEP is the clean negative/control family:

| run | candidate | scorer decision | measured result |
|---|---|---|---|
| DEEP100K B=4 | `128:4,128:3` | rejected; risky fallback only | +8.9% QPS but -0.0276 R@100 at np200 |
| DEEP100K B=5 | `128:5,128:4` | rejected; risky fallback only | +10.4% QPS but -0.0143 R@100 at np200 |

Audio and word2vec are stable abstention cases under the current generator:

| dataset | scanned budgets | default shape | result |
|---|---|---|---|
| audio | B=3/B=4/B=5 | single uniform segment | abstain |
| word2vec100K | B=3/B=4/B=5 | single uniform segment | abstain |

This gives a clearer applicability boundary:

```text
The current default-neighborhood method is meaningful when SAQ's default has a
multi-segment bit ladder, especially with a zero tail and enough middle/tail
positive dimensions to redistribute.

It should abstain when the default is already a single uniform segment.
It should reject speed-only perturbations that hurt boundary-risk proxies.
```

## 9. GIST B=3 1-Bit Bugfix Caveat

GIST B=3 originally could not be measured fairly because SAQ's own default
plan contains a positive 1-bit segment:

```text
64:9,192:5,320:3,192:1,192:0
```

Clean upstream `upstream/main` reproduced the crash. The root cause was an
implementation contract mismatch:

```text
CAQEncoder::encode_and_fac:
  exported base_code.code only for num_bits > 1

ClusterPacker::store_and_pack:
  packed short codes for every num_bits > 0 segment
```

The local experimental branch now contains the minimal fix:

- export `base_code.code` for every positive-bit segment;
- keep short-code packing for every positive-bit segment;
- skip lower-bit long residual packing for `num_bits <= 1`;
- replace release-disabled `assert` with `CHECK_EQ`.

This fix is important for fair evaluation, but it is not part of the proposed
planner contribution. The planner contribution should be evaluated separately
from the implementation repair.

## 10. What We Can Now Claim

The current evidence supports these claims:

1. **The query-unaware boundary-risk signal is useful.**
   It helps identify meaningful plan neighborhoods and endpoint roles without
   using held-out benchmark queries for learning.

2. **The fixed-policy story is stronger than a single-plan story.**
   GIST and CIFAR both show positive budget ladders across B=3/B=4/B=5, while
   DEEP is rejected and audio/word2vec abstain.

3. **A single offline score is not enough.**
   The B=5 sample false positive showed that raw recall-risk endpoints can be
   unsafe. Promotion needs pair-risk and speed guard terms.

4. **Applicability is shape-dependent.**
   The current method is most relevant for multi-segment default plans with
   zero tails. It is not meant to force changes on single-uniform defaults.

5. **The strongest current narrative is method boundary and promotion policy.**
   We should not yet claim a universal replacement for SAQ's planner.

## 11. Main Remaining Gaps

The strongest gaps are now more precise.

First, the current default-neighborhood generator and promotion rule are still
empirical. We need a cleaner fixed method definition:

```text
When exactly should the method generate candidates?
Which candidate families are allowed?
When should conservative vs frontier-like promotion be used?
When should it abstain?
```

Second, middle-plan generation remains unresolved. On full GIST K4096 B=4,
`filtered_new` is a measured balanced point:

```text
filtered_new = 64:10,320:6,384:3,192:0
R@100 np800 = 0.98948
QPS np800   = 1092.29
QPS ratio   = 1.078x
```

It is not the best recall plan and not the fastest plan. The existing v3
candidate set did not rediscover it directly, which means the gap is not only
role selection. Candidate generation still matters.

Third, cross-dataset validation is still narrow. GIST and CIFAR are useful, but
we need another dataset whose SAQ default has a multi-segment zero-tail shape.
Audio and word2vec are informative abstentions, not positive validation targets
for the current generator.

## 12. Proposed Next Technical Step

The next technical step should be one of two focused directions.

### Option A: Formalize The Fixed Policy

Turn the current empirical workflow into a stable method:

```text
1. classify the SAQ default plan shape;
2. generate only allowed default-neighborhood candidate families;
3. score candidates with data-only boundary pairs;
4. promote conservative/frontier candidates under explicit thresholds;
5. abstain otherwise.
```

Then rerun the fixed policy once end-to-end on the current validation matrix to
produce a clean final table.

### Option B: Add Middle-Plan Generation

Add a middle-shape generator or constrained selector:

```text
minimize recall-risk subject to speed_proxy_ratio <= 1.0
and prefer broad, balanced middle segments over over-fragmented endpoints.
```

Validation target:

```text
Can the method recover filtered_new or a nearby measured-balanced candidate
without using held-out query labels?
```

My recommendation before the next meeting is Option A first. It gives the
clearest defensible story. Option B is the natural next research extension if
the advisor agrees that the fixed-policy boundary is a promising contribution.

## 13. Meeting Narrative

For a meeting, the clean story is:

1. We stayed inside the query-unaware SAQ setting after the advisor feedback.
2. SAQ's global PCA-variance objective is effective but does not directly
   optimize ANN boundary stability or search-time segment cost.
3. We built a data-only boundary-risk diagnostic and a default-neighborhood
   candidate workflow.
4. Raw v3 endpoints are useful diagnostically, but raw recall-risk alone can be
   a false positive.
5. The fixed promotion policy now gives repeated positives on GIST and CIFAR,
   rejects DEEP speed-only risky candidates, and abstains on audio/word2vec.
6. GIST B=3 also revealed an upstream 1-bit implementation bug; fixing it only
   unblocks fair evaluation and should not be conflated with planner novelty.
7. The next decision is whether to formalize this fixed-policy planner as the
   contribution, or move directly to middle-plan generation.

The most important caution to state explicitly:

```text
This is not yet a universal better SAQ planner. It is a query-unaware
default-neighborhood policy with a clear applicability boundary and measured
positive/negative/abstention evidence.
```

## 14. Key References In This Repo

```text
docs/saq_query_unaware_pivot_2026_07_02.md
docs/saq_paper_code_alignment_2026_07_02.md
docs/saq_boundary_aware_planner_v3_speed_recall_2026_07_05.md
docs/saq_gist_full_k4096_B4_v3_conservative_audit_2026_07_06.md
docs/saq_gist_full_k4096_B4_middle_role_analysis_2026_07_06.md
docs/saq_cross_dataset_default_neighborhood_validation_2026_07_06.md
docs/saq_default_neighborhood_applicability_scan_2026_07_06.md
docs/saq_cifar_budget_holdout_2026_07_06.md
docs/saq_gist_budget_holdout_2026_07_06.md
docs/saq_gist_b3_default_build_crash_debug_2026_07_06.md
docs/saq_gist_full_k4096_B3_after_1bit_fix_2026_07_07.md
```

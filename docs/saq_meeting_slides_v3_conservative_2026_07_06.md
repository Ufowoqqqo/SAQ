# Query-Unaware SAQ Follow-Up

Boundary-Aware Planner v3, Conservative Guard, and the Remaining Middle-Plan Gap

Date: 2026-07-06

Audience assumption: familiar with vector search / ANNS, not necessarily with
SAQ implementation details.

---

## 1. Meeting Goal

Explain where the SAQ follow-up currently stands.

Main message:

```text
We should not frame the current result as "we found one better plan".
The stronger story is:
v3 exposes recall/speed endpoints, and the remaining gap is generating
measured-balanced plans.
```

Meeting output I want:

- Validate whether this problem framing is worth pursuing.
- Decide whether the next step should target balanced-plan generation.

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

But it is not directly optimizing:

```text
top-k boundary stability
search-time recall/speed tradeoff
IVF residual behavior after clustering
```

---

## 4. Research Boundary After Advisor Feedback

We should stay query-unaware.

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
ANN ranking.

More concrete:

```text
Global variance, residual reconstruction cost, and top-k boundary behavior can
disagree even without using query workloads.
```

So the follow-up question becomes:

```text
Can data-only base/index diagnostics produce better recall/speed segment-plan
candidates than pure global PCA variance?
```

---

## 6. Planner v3: Data-Only Boundary Risk

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

## 7. Planner v3 Outputs Roles, Not One Winner

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

## 8. Why We Added A Conservative Guard

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

## 9. Conservative Guard

The guard is a promotion-layer rule.

It does not remove raw diagnostic endpoints.

It only rejects a promotion candidate if it is worse than default on:

```text
weighted soft-inversion ratio
weighted pair-ratio mean
speed-proxy ratio
```

For the B=5 false positive:

```text
soft inversion ratio = 1.030461
weighted ratio       = 1.029477
speed proxy ratio    = 1.214129
```

Conservative roles select:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

---

## 10. Full GIST K4096 B=4: Raw v3 Frontier

Full GIST, K=4096, B=4.

Raw v3 Pareto endpoints:

| role | plan | proxy readout |
|---|---|---|
| recall endpoint | `64:9,64:7,128:6,320:4,256:2,128:0` | best recall-risk, slower |
| speed endpoint | `128:9,320:5,320:3,192:0` | fastest proxy, lower recall-risk gain |

Names:

```text
v2_split64    = recall endpoint
compact_k4096 = speed endpoint
```

This supports the "Pareto interpretation" story.

---

## 11. Full GIST K4096 B=4: Measured Results

Measured with corrected safe searcher, original-space R@100, nprobe=800.

| plan | R@100 | QPS | QPS ratio |
|---|---:|---:|---:|
| default | 0.98845 | 1013.64 | 1.000x |
| `v2_split64` | 0.98975 | 918.44 | 0.906x |
| `filtered_new` | 0.98948 | 1092.29 | 1.078x |
| `compact_k4096` | 0.98922 | 1211.10 | 1.195x |

Interpretation:

- `v2_split64`: best recall, slower.
- `compact_k4096`: strongest speed point with positive recall.
- `filtered_new`: measured balanced point.

---

## 12. What Conservative Guard Does On Full GIST

Conservative guard excludes `v2_split64` only because:

```text
speed_proxy_ratio = 1.215274 > 1
```

It selects:

```text
compact_k4096 = 128:9,320:5,320:3,192:0
```

Important interpretation:

```text
The conservative guard is not a best-recall selector.
It is a safer promotion selector.
```

We should keep both:

- raw endpoint roles for diagnosis;
- conservative roles for safer promotion.

---

## 13. Middle-Role Sanity Check

Question:

```text
Can role selection alone recover the measured balanced point filtered_new?
```

Measured balanced plan:

```text
filtered_new = 64:10,320:6,384:3,192:0
```

Result from existing v3 unique candidate set:

```text
filtered_new is not present.
```

This means the gap is not only role selection.

---

## 14. Middle Selectors We Tried Offline

Using the existing full GIST K4096 B=4 v3 CSV.

Selector:

```text
minimize recall risk subject to speed_proxy_ratio <= threshold
```

Result:

```text
always selects compact_k4096
```

Default-speed window selector:

```text
speed_proxy_ratio in [0.98, 1.02]
```

Result:

```text
64:8,192:7,320:4,256:2,128:0
```

Still not `filtered_new`.

---

## 15. Current Claim

What we can claim now:

1. v3 gives useful data-only endpoint diagnostics.
2. Raw recall-risk can produce false positives.
3. Conservative guard reduces unsafe promotion risk.
4. Current DP candidate generation still misses measured-balanced shapes.

What we should not claim:

```text
We have a final better SAQ planner.
```

Better claim:

```text
We have identified a concrete limitation and a more precise next target.
```

---

## 16. Main Remaining Gap

Current gap:

```text
The planner can expose endpoints, but does not generate filtered_new-like
balanced plans.
```

This is useful because it points to a method contribution:

```text
balanced candidate generation / middle-shape prior
```

Not just:

```text
more sweeps
more scalar re-ranking
```

---

## 17. Proposed Next Step

Design a middle-plan generator.

Possible directions:

1. Add a target-speed penalty during DP, not only after DP.
2. Add a shape prior for balanced plans:

```text
compact head
broad mid segments
nonzero tail cutoff near 768 or 832/896
avoid unnecessary head fragmentation
```

3. Seed balanced shape families and rank them with the data-only pair-risk
proxy.

Validation target:

```text
Can we recover filtered_new or a nearby measured-balanced candidate?
```

---

## 18. Discussion Questions

1. Is the current problem framing strong enough?

```text
SAQ global variance planning misses balanced segment shapes under data-only
boundary-risk diagnostics.
```

2. Should the next contribution target:

```text
balanced candidate generation
cluster-local plan families
non-contiguous / reordered segmentation
```

3. For the next experiment, is it acceptable to use `filtered_new` as a
measured target shape, while still keeping the method query-unaware?

---

## Backup: Key Artifacts

Reports:

```text
docs/saq_stage_synthesis_v3_conservative_2026_07_06.md
docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md
docs/saq_gist_full_k4096_B4_v3_conservative_audit_2026_07_06.md
docs/saq_gist_full_k4096_B4_middle_role_analysis_2026_07_06.md
```

Implementation:

```text
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
3. We built a base-only boundary-risk planner.
4. v3 exposes recall/speed endpoints instead of one winner.
5. B=5 showed raw recall-risk can be a false positive.
6. Conservative guard fixes promotion, not candidate generation.
7. Full GIST K4096 confirms endpoint story.
8. The missing piece is generating measured-balanced plans like `filtered_new`.

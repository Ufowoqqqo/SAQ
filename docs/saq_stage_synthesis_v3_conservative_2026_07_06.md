# SAQ Stage Synthesis: Boundary-Aware Planner v3 And Conservative Guard

Date: 2026-07-06

## 1. One-Sentence Status

The current SAQ follow-up has shifted from "find a single better segment plan"
to a more defensible query-unaware story:

```text
Use data-only boundary-risk diagnostics to expose recall/speed Pareto endpoints,
then use a conservative promotion guard to avoid proxy false positives.
```

This is not yet a final method contribution. It is a clearer problem framing
and a validated diagnostic/planner layer that exposes where the current
data-only objective is strong and where it still misses measured behavior.

## 2. Research Boundary After Advisor Feedback

The primary direction should remain query-unaware. The method should use only
signals available during a normal offline index build:

```text
base vectors
PCA variances
IVF centroids and cluster ids
cluster residuals
base-as-pseudo-query boundary pairs
quantization plan metadata
```

Held-out benchmark queries are still valid for evaluation, but not for learning
the index-time plan. This keeps the follow-up inside SAQ's own setting instead
of assuming a representative query workload.

## 3. Problem We Are Now Studying

SAQ's default planner uses a global PCA-variance style objective over contiguous
PCA dimensions. A simplified view is:

```text
segment_cost(segment, bits) ~= variance_sum(segment) / 2^bits
```

This objective is simple and effective, but it does not directly optimize
nearest-neighbor boundary stability. The experiments so far suggest a more
specific limitation:

```text
Global variance, residual reconstruction cost, and top-k boundary behavior can
disagree even without using query workloads.
```

The practical question is therefore:

```text
Can we use query-unaware base/index statistics to find segment plans that better
trade off recall risk and search cost than SAQ's default plan?
```

## 4. What Planner v3 Adds

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
2. **Speed proxy**: a plan-shape proxy based on nonzero segment count, total
   segment count, nonzero dimensional coverage, and bitwork.

The important design change is that v3 no longer tries to collapse everything
into a single story. It outputs:

```text
raw recall-risk endpoint
speed endpoint
Pareto frontier
role shortlist
```

This makes the current method easier to reason about: a plan can be good for
recall risk but slow, or fast but less recall-oriented.

## 5. Why Conservative Guard Was Needed

The B=5 `gist_sample100k` validation exposed a failure mode. The raw v3
recall-risk endpoint was:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

Offline, this looked best by recall-risk score. Measured under the corrected
safe searcher, it was a false positive:

```text
np200 R@100:
v3 endpoint = 0.99470
default     = 0.99478
b5_rank0    = 0.99521
```

It was also slower:

```text
QPS ratio vs default = 0.942x
```

The conservative guard fixes this at the promotion layer. It does not remove
the raw endpoint from the diagnostics. It only says that a plan should not be
promoted as the safe candidate if it is worse than default on:

```text
weighted soft-inversion ratio
weighted pair-ratio mean
speed-proxy ratio
```

For B=5, the raw endpoint was rejected because:

```text
soft inversion ratio = 1.030461
weighted ratio       = 1.029477
speed proxy ratio    = 1.214129
```

The conservative roles instead selected:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

This matches the corrected measured leaderboard, where `b5_rank0` is the stable
B=5 recall/middle point.

## 6. Full GIST K4096 B=4 Readout

The full GIST K4096 B=4 audit gives the clearest current picture.

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
The conservative guard selects the safest promotion point.
It is not meant to select the highest-recall point.
```

## 7. What We Can Now Claim

The current evidence supports these claims:

1. **The query-unaware boundary-risk signal is useful.**
   It rediscovers meaningful endpoint plans, including the full GIST K4096
   recall endpoint `v2_split64` and speed endpoint `compact_k4096`.

2. **A single offline score is not enough.**
   The B=5 split-front endpoint looked best offline but failed measured recall
   and speed validation. This is exactly why the planner should expose roles
   rather than only a scalar winner.

3. **Conservative promotion reduces false-positive risk.**
   On B=5 sample, it rejects the measured false positive and selects the
   measured-safe `b5_rank0`. On full GIST K4096 B=4, it selects the measured
   speed-oriented candidate `compact_k4096`.

4. **The strongest current narrative is Pareto interpretation, not automatic
   optimal planning.**
   v3 gives a structured way to explain the candidate space. It does not yet
   solve candidate generation fully.

## 8. Main Gap

The biggest gap is now clear:

```text
The data-only DP can find recall and speed endpoints, but it does not rediscover
the measured balanced point filtered_new.
```

`filtered_new` is important because it is measured to be a strong middle point:

```text
filtered_new = 64:10,320:6,384:3,192:0
```

On full GIST K4096 B=4:

```text
filtered_new R@100 np800 = 0.98948
filtered_new QPS np800   = 1092.29
QPS ratio                = 1.078x
```

It is not the best recall plan and not the fastest plan, but it is a better
balanced speed/recall point than the current data-only DP knows how to produce.

This gap is more useful than a vague "planner mismatch" statement. It gives the
next method target:

```text
Generate or select middle Pareto candidates, not only endpoints.
```

## 9. Current Limitations

The current approach still has several limitations:

1. **The speed proxy is useful but coarse.**
   It captures plan-shape cost, but it is not a calibrated QPS model.

2. **The conservative guard is intentionally speed-biased.**
   It will reject slower recall-oriented plans such as `v2_split64`, even when
   measured recall is best.

3. **Pair-risk sampling is local and approximate.**
   It uses base-as-pseudo-query boundary pairs inside IVF cells. This keeps the
   method query-unaware, but it is still a proxy for benchmark query behavior.

4. **The planner still optimizes over contiguous PCA segments.**
   It has not yet tested non-contiguous grouping, learned rotations, or
   cluster-local plan families.

5. **Measured validation remains mandatory.**
   Offline proxies can guide candidate generation, but final claims require
   safe-searcher recall and QPS.

## 10. Proposed Next Technical Step

The next step should target the missing middle point.

Concrete option:

```text
Add a middle-point role or constrained selector:
minimize recall-risk subject to speed_proxy_ratio <= 1.0
and optionally prefer fewer/wider segments only after recall-risk ties.
```

This is different from the current conservative guard:

- the guard filters unsafe promotion candidates;
- a middle-point selector should deliberately search for balanced plans between
  `v2_split64` and `compact_k4096`.

A more ambitious next step is to add a prior that reflects measured balanced
shape features:

```text
limited segment count
wide but not too-wide mid segment
nonzero tail cutoff near 768 or 832/896
avoid over-fragmented head splits unless measured recall justifies them
```

The immediate experiment should be:

```text
Run a v3 middle-point selector on full GIST K4096 B=4 and check whether it
recovers filtered_new or a nearby measured-balanced candidate.
```

## 11. Meeting Narrative

For a meeting, the clean story is:

1. We stayed inside the query-unaware SAQ setting after the advisor feedback.
2. We found that global PCA-variance planning is not the whole story for ANN
   boundary behavior.
3. We built a data-only boundary-pair planner that exposes recall/speed Pareto
   endpoints.
4. We found and fixed a promotion-layer failure mode: raw offline recall-risk
   can produce false positives.
5. The conservative guard now separates diagnostic endpoints from promotion
   candidates.
6. The next research gap is not "more sweeping"; it is explicitly generating
   balanced middle plans such as `filtered_new`.

The most important caution to state explicitly:

```text
The conservative guard is not a best-recall selector. It is a safer promotion
rule. The planner should keep both raw endpoints and conservative roles.
```

## 12. Key References In This Repo

```text
docs/saq_query_unaware_pivot_2026_07_02.md
docs/saq_followup_priorities_2026_07_02.md
docs/saq_boundary_aware_planner_v3_speed_recall_2026_07_05.md
docs/saq_gist_sample100k_B5_boundary_v3_speed_recall_2026_07_05.md
docs/saq_gist_sample100k_B5_v3_endpoint_eval_2026_07_06.md
docs/saq_gist_sample100k_B5_v3_conservative_guard_2026_07_06.md
docs/saq_gist_full_k4096_data_boundary_candidates_eval_2026_07_05.md
docs/saq_gist_full_k4096_B4_v3_conservative_audit_2026_07_06.md
```

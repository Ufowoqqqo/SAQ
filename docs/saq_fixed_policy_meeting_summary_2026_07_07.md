# SAQ Fixed-Policy Meeting Summary

Date: 2026-07-07

Audience assumption: familiar with ANNS/vector quantization, but not with the
details of SAQ or this follow-up branch.

## 1. One-Sentence Contribution Candidate

The current follow-up is a query-unaware policy layer around SAQ's default
segment plan:

```text
Generate small local segment-plan candidates around SAQ's default plan, score
them with data-only boundary-risk and speed proxies, promote only conservative
or narrow frontier-like candidates, reject bad speed-only changes, and abstain
when the default shape has no meaningful neighborhood.
```

This is not yet a theoretical replacement for SAQ's planner. The defensible
claim is empirical and shape-dependent.

## 2. Background: What SAQ Optimizes

SAQ uses PCA to order dimensions by variance, splits contiguous PCA dimensions
into segments, and allocates different bitwidths under a fixed budget. A simple
view of the default segment objective is:

```text
segment_cost(segment, bits) ~= variance_sum(segment) / 2^bits
```

This is query-unaware, efficient, and sensible for global reconstruction or
distance-estimation quality. The limitation we are targeting is narrower:

```text
Global PCA variance can disagree with IVF-local residual behavior,
top-k boundary stability, and search-time segment cost.
```

The follow-up therefore asks whether base/index-only diagnostics can improve
the recall/speed tradeoff without using representative query workloads.

## 3. Method: Fixed-Policy Default Neighborhood

The current workflow is:

```text
SAQ default plan
  -> classify default-plan shape
  -> generate local default-neighborhood candidates
  -> score candidates with data-only boundary pairs
  -> select by conservative/frontier policy
  -> validate with corrected safe-searcher recall and QPS
```

Allowed signals are available during offline index construction:

```text
base vectors
PCA variances
IVF centroids and cluster ids
cluster residuals
base-as-pseudo-query boundary pairs
SAQ default plan metadata
```

Held-out benchmark queries are used only for final evaluation.

## 4. Candidate Generation

The generator stays local around SAQ's default plan. It does not search the full
plan space.

Current candidate families:

| family | intent |
|---|---|
| `head_split` | split the post-head block and move precision into it |
| `head_widen_keep_levels` | widen the first segment while preserving later bit levels |
| `speed_merge_same_tail` | merge middle/tail-positive dimensions into fewer positive segments |
| `tail_expand_middle_merge` | preserve a small head, merge middle dimensions, expand zero tail |
| `tail_expand_head_widen` | widen the head, use broad middle chunks, expand zero tail |

Feasibility guards enforce bit budget, nonincreasing bitwidths, segment-count
limits, positive-bit minima, and nonfinal 1-bit avoidance.

## 5. Scoring And Promotion Rule

The scorer samples base vectors as pseudo-queries inside IVF cells and forms
positive/negative boundary pairs around a local rank boundary. Smaller exact
margins receive larger weights:

```text
weight = exp(-margin / tau)
```

The final policy has three outcomes:

| outcome | condition | meaning |
|---|---|---|
| conservative promote | soft-inversion ratio <= 1, weighted-ratio <= 1, speed-proxy <= 1 | safest positive case |
| frontier-like promote | recall-risk <= 1 and speed-proxy <= 1 | narrow fallback for small positive cases |
| abstain/reject | no useful candidate, or risky fallback diagnostic | do not claim improvement |

Risky fallback is diagnostic only. It is mapped to `reject` in the clean report,
not to promotion.

## 6. Evidence Table

Headline report:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Reproducible report commands:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv

python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

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
| audio B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |
| word2vec100K B=4 | abstain | none | single-uniform default; scan also abstains at B=3/B=5 |

All measured recall/QPS claims use corrected safe search:

```text
-searcher_safe_block_min_mode=2
```

## 7. Positive, Reject, And Abstention Cases

The evidence decomposes cleanly:

```text
GIST positives: conservative promotion
CIFAR positives: narrow frontier-like promotion
DEEP controls: risky fallback diagnostic mapped to reject
audio/word2vec: no-candidate abstention
```

This is important because the policy does not force every dataset into a custom
plan. Abstention is part of the method boundary.

## 8. Implementation Fix, Not Method Contribution

GIST B=3 exposed a positive 1-bit CAQ segment bug. The default plan contains:

```text
64:9,192:5,320:3,192:1,192:0
```

The fix makes SAQ's own legal default plan buildable. It should be presented as
an upstream correctness repair that enables fair evaluation, not as the planner
contribution.

## 9. Limitations And Threats To Validity

- Current evidence is empirical and benchmark-limited.
- Recall deltas are small; the stronger story is often preserving/improving
  recall while improving QPS.
- Frontier-like fallback is useful for CIFAR but must remain narrow.
- The report depends on local `/tmp/saq-run` artifacts unless regenerated with
  the same datasets and preprocessing.
- The report driver trusts stored `selection_reason`; it does not recompute
  scorer thresholds from raw outputs.
- The method does not currently apply to single-uniform default-plan datasets
  under the existing generator.

## 10. Meeting Questions

1. Is a shape-dependent fixed-policy correction layer around SAQ's default plan
   a worthwhile contribution direction?
2. Should the next paper-facing step be a more formal method section and
   applicability classifier, or new candidate families within the same
   query-unaware default-neighborhood boundary?
3. Is the current evidence table sufficient for a meeting/paper narrative, or
   should we prioritize a cleaner clean-machine artifact regeneration story?

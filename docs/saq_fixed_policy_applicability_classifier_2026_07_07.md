# SAQ Fixed-Policy Applicability Classifier

Date: 2026-07-07

This note makes the current method boundary explicit. It is not a learned
classifier and it is not a theoretical guarantee. It is a deterministic
decision table recovered from the implemented default-neighborhood generator,
data-only scorer, and checked-in fixed-policy validation results.

## 1. Scope

The classifier is query-unaware:

```text
No representative query workload is used for candidate generation or scoring.
Held-out benchmark queries are used only for final recall/QPS evaluation.
```

It has two stages:

1. pre-scorer applicability: decide whether the SAQ default plan has a local
   neighborhood worth scoring;
2. post-scorer decision: decide whether a scored non-default candidate can be
   promoted, rejected as a diagnostic, or abstained.

## 2. Pre-Scorer Applicability

This stage uses only default-plan metadata and candidate-generator feasibility.

Relevant implementation:

```text
script/scan_default_neighborhood_applicability.py
script/generate_default_neighborhood_plans.py
```

Current features:

| feature | source | use |
|---|---|---|
| `default_shape` | SAQ default plan | separates single-uniform, multi + zero-tail, and multi no-zero-tail cases |
| `default_segment_count` | SAQ default plan | identifies whether there is a segment ladder to perturb |
| `default_nonzero_segment_count` | SAQ default plan | checks how many positive-bit regions can be redistributed |
| `default_zero_tail_dim` | SAQ default plan | indicates whether tail expansion candidates are meaningful |
| `default_has_positive_1bit_segment` | SAQ default plan | implementation caveat; avoid promoted nonfinal 1-bit candidates |
| `feasible_non_default_candidate_count` | generator output | decides whether there is anything to score |
| `feasible_non_default_families` | generator output | records which local perturbation families are available |

Pre-scorer rule:

| condition | action | current evidence |
|---|---|---|
| `single_uniform` default | abstain | audio and word2vec B=3/4/5 |
| no feasible non-default candidate | abstain | DEEP B=3 under current guards |
| `multi_segment_with_zero_tail` and feasible candidates | score candidates | GIST and CIFAR B=3/4/5 |
| `multi_segment_no_zero_tail` and feasible candidates | score only as cautious/control case | DEEP B=4/B=5 |
| positive 1-bit default segment | allow default, but avoid promoted nonfinal 1-bit candidates | GIST B=3 required the 1-bit correctness fix |

This stage is intentionally conservative. It should not force a non-default
candidate for single-uniform defaults.

## 3. Post-Scorer Decision

This stage uses data-only boundary-risk and speed proxy outputs.

Relevant implementation:

```text
script/run_default_neighborhood_cross_dataset.py
script/score_default_neighborhood_plans.py
script/sweep_data_boundary_pairs.py
```

The candidate selector considers only non-default candidates. Its current order
is:

1. `conservative_eligible`
2. `frontier_like`
3. optional `risky_fallback_best_score`

The optional risky fallback is diagnostic only and is not a promotion policy.

Post-scorer rule:

| condition | decision | interpretation |
|---|---|---|
| `conservative_role_is_eligible=true` | promote | safest current positive class |
| `best_recall_risk_score <= 1` and `best_speed_proxy_ratio_vs_default <= 1` | promote as frontier-like | narrow fallback for small positives |
| selected only by risky fallback | reject/control | useful to test false-positive resistance |
| no selected candidate | abstain | no query-unaware evidence for changing SAQ default |

The conservative guard currently requires:

```text
weighted soft-inversion ratio <= 1.0
weighted pair-ratio mean      <= 1.0
speed-proxy ratio             <= 1.0
```

The frontier-like rule is intentionally weaker, but still requires both
recall-risk and speed proxy to be no worse than default.

## 4. Evidence Mapping

Source table:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

| class | settings | decision | observed result |
|---|---|---|---|
| multi + zero-tail, conservative | GIST full K4096 B=3/4/5 | promote | R@100 is non-worse/slightly better and QPS improves |
| multi + zero-tail, frontier-like | CIFAR60K B=3/4/5 | promote | R@10 is slightly better and QPS improves |
| multi no-zero-tail, risky fallback only | DEEP100K B=4/B=5 | reject | QPS improves, but R@100 drops too much |
| single-uniform default | audio and word2vec B=3/4/5 scan; B=4 validation rows | abstain | generator has no meaningful non-default local neighborhood |

The classifier therefore separates the current evidence into:

```text
GIST: conservative positive
CIFAR: frontier-like positive
DEEP: reject/control
audio/word2vec: abstain
```

## 5. Practical Decision Table

For a new dataset/budget under the current generator:

| step | check | if yes | if no |
|---|---|---|---|
| 1 | default is `single_uniform` | abstain | continue |
| 2 | generator has feasible non-default candidates | continue | abstain |
| 3 | default is `multi_segment_with_zero_tail` | normal scoring path | cautious/control scoring path |
| 4 | any conservative candidate exists | promote best conservative candidate | continue |
| 5 | any frontier-like candidate exists | promote best frontier-like candidate | abstain |
| 6 | risky fallback candidate exists only because `--allow-risky-fallback` was enabled | reject/control, not promotion | abstain |

All measured claims after promotion must use corrected safe search:

```text
-searcher_safe_block_min_mode=2
```

## 6. Current Boundary

The method is strongest when:

```text
SAQ default has a multi-stage bit ladder, a zero tail, and enough middle/tail
positive dimensions for local redistribution.
```

The method should abstain when:

```text
SAQ default is a single uniform segment or the generator produces no feasible
non-default local candidates.
```

The method should treat as control/reject unless proven otherwise when:

```text
only speed-like candidates exist, recall-risk proxy is worse than default, or
promotion requires risky fallback.
```

## 7. Limitations

- This is an empirical rule table, not a proven classifier.
- The current positive evidence is benchmark-limited.
- Frontier-like promotion is supported by CIFAR but remains the weakest
  positive class.
- The pre-scorer scan does not guarantee a final positive; it only decides
  whether scoring is meaningful.
- The post-scorer policy still requires final safe-searcher validation before
  making measured recall/QPS claims.

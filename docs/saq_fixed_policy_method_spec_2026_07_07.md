# SAQ Fixed-Policy Method Spec

Date: 2026-07-07

This document turns the current default-neighborhood workflow from an
experimental sweep into an explicit query-unaware decision policy.

The accompanying clean validation table is:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Supporting audits:

```text
docs/saq_fixed_policy_applicability_classifier_2026_07_07.md
docs/saq_fixed_policy_artifact_staleness_audit_2026_07_07.md
docs/saq_fixed_policy_metric_audit_2026_07_07.md
```

## Paper-Style Method Definition

Given a dataset, SAQ's default segment plan `P0`, and the fixed average bit
budget `B`, the method defines a small candidate neighborhood `N(P0)` rather
than searching the full segment-plan space. Each candidate is produced by local
shape-preserving edits to `P0`, such as widening the head, merging middle
segments, or expanding the zero tail.

The method then computes a data-only score for each candidate using base vectors
as pseudo-queries inside IVF cells. The score estimates two quantities:

```text
recall-risk proxy: likelihood that the candidate disrupts close boundary pairs
speed proxy:       relative scan/segment work compared with the SAQ default
```

The final policy is a deterministic decision function:

```text
Input:  SAQ default plan P0, generated candidates N(P0), data-only scores
Output: promote(candidate), reject/control(candidate), or abstain

1. If P0 is single-uniform, abstain.
2. Generate feasible non-default candidates in N(P0).
3. If no feasible non-default candidate exists, abstain.
4. Promote the best conservative candidate if one exists.
5. Otherwise promote the best frontier-like candidate if one exists.
6. Otherwise abstain.
7. If risky fallback is explicitly enabled, treat its selected candidate as a
   reject/control diagnostic, never as promotion.
```

The policy is therefore a query-unaware local correction layer around SAQ's
default plan. It is not a learned query-workload policy and not a theoretical
dominance claim over SAQ's planner.

## 1. Scope

The policy stays inside the SAQ setting:

```text
No representative query workload is used for learning the plan.
Held-out benchmark queries are used only for final evaluation.
```

Allowed offline signals:

```text
base vectors
PCA variance artifacts
IVF centroids and cluster ids
cluster residuals
base-as-pseudo-query boundary pairs
SAQ default quantization plan metadata
```

The policy is not a universal replacement for SAQ's planner. It is a
shape-aware correction layer around SAQ's own default plan.

## 2. Inputs

For each run, the policy takes:

```text
dataset name
K
average bit budget B
SAQ PCA artifacts
SAQ IVF artifacts
SAQ default plan
evaluation top-k
```

In the current implementation, the default plan is either inferred from the
same DP logic as SAQ or passed explicitly when the generator filters the default
row out of the feasible candidate CSV.

Relevant driver:

```text
script/run_default_neighborhood_cross_dataset.py
```

Reproducible report driver:

```text
script/report_fixed_policy_validation.py
```

End-to-end matrix runner:

```text
script/run_fixed_policy_matrix.py
```

## 3. Default-Plan Shape Classification

Classify the SAQ default plan before generating candidates.

Current shape labels:

| shape | condition | policy meaning |
|---|---|---|
| `single_uniform` | one positive segment covers the padded dimension | abstain |
| `multi_segment_with_zero_tail` | multiple segments and final zero-bit tail | applicable |
| `multi_segment_no_zero_tail` | multiple positive segments, no zero tail | cautious; often control/negative |
| `multi_segment_with_1bit` | default contains a positive 1-bit segment | implementation caveat; candidate generation should avoid nonfinal 1-bit |

The current strongest applicability condition is:

```text
SAQ default has a multi-segment bit ladder, preferably with a zero tail and
enough middle/tail positive dimensions to redistribute.
```

Stable abstention condition:

```text
SAQ default is already a single uniform segment.
```

## 4. Candidate Generation

Candidate generation is local around SAQ's default plan. It does not search the
full plan space.

Implemented candidate families:

| family | intent |
|---|---|
| `head_split` | split the post-head block and move one precision level into it |
| `head_widen_keep_levels` | widen the first segment by one 64-d block while preserving later bit levels |
| `speed_merge_same_tail` | merge middle/tail-positive dimensions into fewer positive segments while preserving tail |
| `tail_expand_middle_merge` | preserve a small head, merge middle dimensions, and expand the zero tail |
| `tail_expand_head_widen` | widen the head, use broad middle chunks, and expand the zero tail |

Feasibility guards:

```text
used_bits <= total budget including per-nonzero-segment factor overhead
segment bitwidths are nonincreasing from head to tail
max_segments <= 6 in the current validation runs
positive promoted candidates should avoid nonfinal 1-bit segments
min_positive_bits is usually 2 for main positive runs
nonempty zero tails must meet the run-specific minimum tail size
```

If no feasible non-default candidate is generated, the policy abstains before
running the scorer.

Relevant generator:

```text
script/generate_default_neighborhood_plans.py
```

## 5. Data-Only Scoring

The scorer evaluates a fixed candidate list with data-only boundary proxies.

Boundary-pair sampling:

```text
sample base vectors as pseudo-queries inside IVF cells
form positive/negative pairs around a local rank boundary
weight smaller exact-distance margins more heavily
```

Pair weight:

```text
weight = exp(-margin / tau)
```

Scorer outputs:

```text
best_recall_risk_score
best_speed_proxy_ratio_vs_default
pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default
pair_proxy_weighted_ratio_mean_ratio_vs_default
conservative_role_is_eligible
conservative_role_reasons
```

Speed proxy terms:

```text
positive segment count
total segment count
nonzero dimensional coverage
bitwork relative to budget
```

Relevant scorer:

```text
script/score_default_neighborhood_plans.py
script/sweep_data_boundary_pairs.py
```

### Cost-Reduced Scorer Execution

The official runners now expose a query-unaware cost-reduced scorer path:

```text
--use-cost-reduced-scorer
--scorer-grid-preset endpoints
--feature-cache-dir PATH
```

This path does not change candidate generation or the promotion rule. It only
changes how the scorer is executed:

```text
endpoint grid: evaluate a compact validated scorer grid
feature cache: reuse residual/tail/boundary-pair features across B values
```

The feature cache is keyed by dataset path, IVF K, padded dimension, sampling
parameters, residual-risk statistic, tail-risk quantile, and padding size. It
does not use held-out query labels.

This should be described as an implementation-level scorer overhead reduction,
not as a new quantization contribution.

## 6. Promotion Rule

The policy considers only non-default candidates.

Promotion order:

1. `conservative_eligible`
2. `frontier_like`
3. `abstain`

### Conservative Promotion

A candidate is conservative-eligible if it passes the scorer's conservative
guard. Current default guard thresholds are:

```text
weighted soft-inversion ratio <= 1.0
weighted pair-ratio mean      <= 1.0
speed-proxy ratio             <= 1.0
```

Among conservative candidates, select by:

```text
lowest best_ranking_score
then lowest best_speed_proxy_ratio_vs_default
then lexical seg_plan tie-break
```

### Frontier-Like Promotion

If no conservative candidate fills the evaluation slot, allow a narrow
frontier-like candidate:

```text
best_recall_risk_score <= 1.0
best_speed_proxy_ratio_vs_default <= 1.0
```

This is needed for CIFAR, where pair-ratio terms are only marginally above
default but measured recall and QPS both improve.

### Reject / Diagnostic Fallback

Risky fallback is not part of the fixed policy. It is used only for diagnostics
to test whether the guard is rejecting bad speed-only candidates.

DEEP B=4/B=5 are examples:

```text
QPS improves, but recall drops substantially.
The fixed policy should reject these candidates.
```

### Abstain

The policy abstains when:

```text
the generator produces no feasible non-default candidate
or no candidate passes conservative/frontier-like promotion
```

Audio and word2vec are stable abstention examples under the current generator.

## 7. Evaluation Rule

Measured claims must use corrected safe search:

```text
-searcher_safe_block_min_mode=2
```

Validation metrics:

```text
GIST / DEEP / audio / word2vec: R@100
CIFAR: R@10
QPS measured at the run-specific nprobe in the validation table
```

The validation table reports:

```text
default recall
candidate recall
delta recall
default QPS
candidate QPS
QPS ratio
policy interpretation
```

## 8. Clean Validation Table

Source CSV:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

| dataset | B | decision | plan | recall delta | QPS ratio | interpretation |
|---|---:|---|---|---:|---:|---|
| GIST full K4096 | 3 | promote | `64:8,320:5,320:2,256:0` | +0.00159 R@100 np800 | 1.1119x | positive after 1-bit fix |
| GIST full K4096 | 4 | promote | `128:9,320:5,320:3,192:0` | +0.00077 R@100 np800 | 1.1948x | strongest QPS-positive GIST case |
| GIST full K4096 | 5 | promote | `128:9,128:7,320:5,320:3,64:0` | +0.00028 R@100 np800 | 1.0793x | positive high-budget holdout |
| CIFAR60K | 3 | promote | `128:6,64:4,192:2,128:0` | +0.0004 R@10 np200 | 1.0761x | small positive low-budget holdout |
| CIFAR60K | 4 | promote | `128:7,256:4,128:0` | +0.0004 R@10 np200 | 1.0745x | small positive original case |
| CIFAR60K | 5 | promote | `128:8,64:6,256:4,64:0` | +0.0008 R@10 np200 | 1.0609x | small positive high-budget holdout |
| DEEP100K | 4 | reject | `128:4,128:3` | -0.02757 R@100 np200 | 1.0893x | speed gain costs too much recall |
| DEEP100K | 5 | reject | `128:5,128:4` | -0.01429 R@100 np200 | 1.1037x | speed gain costs too much recall |
| audio | 4 | abstain | none | n/a | n/a | single-uniform default; scan also abstains at B=3/B=5 |
| word2vec100K | 4 | abstain | none | n/a | n/a | single-uniform default; scan also abstains at B=3/B=5 |

## 9. Current Claims

The fixed-policy evidence supports:

1. The data-only boundary-risk scorer is useful for selecting local plan
   neighborhoods without query workload labels.
2. The method has repeated positives on GIST and CIFAR across B=3/B=4/B=5.
3. The policy has a meaningful reject case: DEEP speed-only changes improve QPS
   but hurt recall too much.
4. The policy has meaningful abstention cases: audio and word2vec default plans
   are single uniform segments under the current budgets.
5. Applicability is shape-dependent, not universal.

## 10. Caveats

GIST B=3 required an implementation repair because SAQ's default plan contains
a positive 1-bit segment:

```text
64:9,192:5,320:3,192:1,192:0
```

The 1-bit fix makes SAQ's own legal default plan buildable. It is not the
planner contribution.

The current fixed policy is still empirical. The report and matrix drivers
make the current evidence reproducible from local summary artifacts; a
clean-machine regeneration path remains the next reproducibility gap.

## 11. Reproducible Report Generation

The clean validation table is generated from the scored/evaluated summary
reports with:

```text
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Default outputs:

```text
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.md
/tmp/saq-run/reports/fixed_policy_validation_2026_07_07.json
```

The `--expected-csv` option compares the regenerated rows against the checked-in
clean table and exits nonzero on mismatch.

The full fixed-policy matrix can be regenerated with:

```text
python script/run_fixed_policy_matrix.py \
  --artifact-date 2026_07_06 \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

`--artifact-date` lets the runner reuse previously generated candidate/scorer
and compare-search artifacts while writing a fresh matrix summary and report.
The runner passes risky fallback only as reject diagnostics; those rows remain
`reject` in the generated fixed-policy report and are not promotion decisions.

The matrix scorer/selection stage can also be run with the cost-reduced scorer
path:

```text
python script/run_fixed_policy_matrix.py \
  --skip-scan \
  --skip-report \
  --no-evaluate \
  --force \
  --use-cost-reduced-scorer \
  --date 2026_07_07_runner_cost_reduced \
  --artifact-date 2026_07_07_runner_cost_reduced
```

This command verifies selection equivalence without rerunning safe-search
recall/QPS. The documented integration check matched the clean table on 10/10
decisions and 10/10 selected/tested plans:

```text
docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md
```

## 12. Evidence Boundary

The current evidence should be read with three boundaries.

First, applicability is shape-dependent. The strongest cases have
multi-segment default plans with zero tails and enough middle/tail positive
dimensions to redistribute. Single-uniform defaults such as current audio and
word2vec are abstention cases under the current generator.

Second, metric reporting is headline-operating-point QPS plus multi-nprobe
recall. GIST B=3/B=4/B=5 are recall-positive across all measured nprobes.
CIFAR B=3/B=5 are also positive across all measured nprobes, while CIFAR B=4
is negative at np50 and positive at np100/np200/np400. DEEP B=4/B=5 are
recall-negative across all measured nprobes and remain reject/control cases.
QPS is currently measured at one headline nprobe per run, so paper-style speed
claims should either add QPS curves or explicitly state the headline operating
point.

Third, artifact durability is layered. The checked-in clean table and docs are
durable summaries. The report and matrix runners reproduced the table from
local `/tmp/saq-run` artifacts, but a clean-machine regeneration path still
requires dataset preparation, PCA/IVF artifacts, index builds, compare outputs,
and QPS outputs.

Safe wording:

```text
The fixed policy finds repeated query-unaware local improvements on GIST and
CIFAR, rejects DEEP speed-only candidates that hurt recall, and abstains on
single-uniform defaults. The claim is empirical, shape-dependent, and validated
at the documented operating points with corrected safe search.
```

Unsafe wording:

```text
The policy universally improves SAQ across datasets, nprobes, and search
operating points.
```

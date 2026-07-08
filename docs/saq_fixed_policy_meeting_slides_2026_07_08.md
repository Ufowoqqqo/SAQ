# Query-Unaware SAQ Follow-Up

Default-Neighborhood Fixed Policy for Segment-Plan Improvement

Date: 2026-07-08

Audience assumption: familiar with vector search at a high level, but almost
unfamiliar with this project, SAQ details, and the current follow-up branch.

---

## 1. Meeting Goal

The goal of this meeting is to explain the current project from the ground up:

1. What problem SAQ solves.
2. What SAQ's default planner does.
3. Why the default plan may not be the whole story.
4. What our query-unaware follow-up currently does.
5. What evidence we have.
6. What the current limitations and next decisions are.
7. What changed after the reproducibility/provenance pass.

Main message:

```text
We are not proposing an arbitrary new quantizer.

We are testing a narrow policy layer around SAQ:
start from SAQ's default segment plan, generate a small local neighborhood,
score candidates with data-only boundary-risk and speed proxies, promote only
safe candidates, reject bad speed-only changes, and abstain when the default
shape has no useful local neighborhood.

The evidence table is unchanged from the previous draft.
The artifact story is stronger: the input layer now has full-file hashes,
preparation provenance, and a one-command verification/preparation driver.
```

Speaker notes:

- The intended contribution is currently a method boundary and decision policy,
  not a universal theorem.
- The most important phrase is "query-unaware": we do not train on a
  representative query workload.
- The new point for this version is not a new recall number. It is that the
  current evidence is easier to defend as a reproducible experiment.

---

## 2. Why Vector Quantization Matters In ANNS

In approximate nearest neighbor search, we store a large set of vectors:

```text
Database vectors: x_1, x_2, ..., x_N
Query vector:     q
Goal:             retrieve vectors closest to q
```

The exact distance computation is expensive when:

```text
N is large
dimension D is high
vectors are stored as float32
many candidates are scanned per query
```

Vector quantization compresses each database vector into a short code. Search
then estimates distances from compressed codes instead of always reading full
float vectors.

The central tradeoff:

```text
shorter code -> less memory and faster scan
shorter code -> less accurate distance estimate
```

Speaker notes:

- In this project, we care about recall and QPS together.
- A better quantization plan should preserve ranking quality while reducing
  scan cost or memory traffic.

---

## 3. What SAQ Is Trying To Do

SAQ stands for Segmented Adjusted Quantization.

At a high level, SAQ does three things:

1. Rotate vectors with PCA.
2. Split PCA dimensions into contiguous segments.
3. Assign different bitwidths to different segments.

The intuition:

```text
After PCA, early dimensions usually carry more variance.
High-variance dimensions receive more bits.
Low-variance dimensions receive fewer bits or zero bits.
```

Then SAQ uses CAQ-style code adjustment inside each segment and multi-stage
distance estimation during search.

Speaker notes:

- We should not assume the audience knows SAQ internals.
- For this meeting, the key object is the segment plan, not the exact CAQ
  encoding details.

---

## 4. Segment Plan Notation

We write a segment plan as:

```text
dim_len:bits, dim_len:bits, ...
```

Example:

```text
64:11,192:6,320:4,256:2,128:0
```

This means:

| segment | PCA dimensions | bitwidth |
|---|---:|---:|
| 1 | 64 | 11 bits |
| 2 | 192 | 6 bits |
| 3 | 320 | 4 bits |
| 4 | 256 | 2 bits |
| 5 | 128 | 0 bits |

The total dimension is:

```text
64 + 192 + 320 + 256 + 128 = 960
```

Speaker notes:

- A `0`-bit tail means SAQ intentionally drops that low-importance tail.
- Most of our method manipulates this plan shape while preserving the same
  average bit budget.

---

## 5. Running Example: GIST Full, K4096, B=4

We will use one running example throughout the slides.

Dataset and setting:

```text
dataset: GIST full
IVF clusters K: 4096
average bit budget B: 4
metric: R@100
headline nprobe: 800
```

SAQ default plan:

```text
64:11,192:6,320:4,256:2,128:0
```

Our selected candidate plan:

```text
128:9,320:5,320:3,192:0
```

Measured headline result:

```text
R@100: 0.98845 -> 0.98922   delta +0.00077
QPS:   1013.64 -> 1211.10   ratio 1.1948x
```

Speaker notes:

- This is the cleanest example because it improves recall slightly and improves
  QPS substantially.
- It is also conservative-selected by the data-only scorer.

---

## 6. What SAQ's Default Planner Optimizes

A simplified view of SAQ's default segment objective is:

```text
cost(segment, bits) ~= variance_sum(segment) / 2^bits
```

This objective is sensible because:

```text
larger PCA variance -> more important dimensions
more bits           -> lower quantization error
```

But this objective is mostly about global variance and reconstruction-style
error. It does not directly optimize every quantity that matters during search.

Speaker notes:

- The default planner is not wrong.
- The question is whether there is room for a local correction around the
  default plan.

---

## 7. The Gap We Are Studying

The working hypothesis:

```text
Global PCA variance can disagree with:
1. local IVF residual behavior,
2. top-k boundary stability,
3. search-time segment cost.
```

In other words, the best global variance plan may not be the best recall/QPS
operating point.

But advisor feedback pushed us away from a query-aware story. So the follow-up
must stay query-unaware.

That gives the current research question:

```text
Can base/index-only diagnostics improve SAQ's segment plan without using a
representative query workload?
```

The paper-level bar is stricter:

```text
Can this expose a real SAQ limitation with acceptable overhead,
or is it only local tuning around a strong baseline?
```

Current contribution sentence:

```text
SAQ's default global variance-based segment plan can be locally mismatched
with IVF-local top-k boundary stability and segment-shape search cost; we use
base/index-only boundary diagnostics to search a small default neighborhood,
then promote, reject, or abstain without representative query workloads.
```

Speaker notes:

- This is the central motivation.
- The novelty must come from exposing a concrete SAQ limitation and a
  query-unaware correction, not from learning on queries.
- The advisor concern about novelty should be handled directly rather than
  hidden behind small metric gains.
- A strict reviewer may still call this SAQ strategy tuning unless we show why
  the scorer is safer than simple speed-only or random local alternatives.

---

## 8. Query-Unaware Constraint

Allowed signals:

```text
base vectors
PCA variances
IVF centroids
cluster IDs
cluster residuals
base-as-pseudo-query boundary pairs
SAQ default plan metadata
```

Not allowed for plan generation or scoring:

```text
representative query workload
held-out benchmark query labels
query-specific fitting
```

Held-out benchmark queries are used only for final evaluation.

Speaker notes:

- This constraint is important for positioning.
- It keeps the method in the same general offline/index-build setting as SAQ.

---

## 9. Current Method In One Diagram

The current fixed-policy workflow:

```text
SAQ default plan P0
  -> classify default-plan shape
  -> generate local candidates N(P0)
  -> score candidates with data-only boundary pairs
  -> apply conservative/frontier promotion rule
  -> validate selected plans with safe-searcher recall and QPS
```

The output is one of:

```text
promote(candidate)
reject/control(candidate)
abstain
```

Speaker notes:

- This is deliberately not a full plan search.
- Abstention is a real output, not a failure case.

---

## 10. Why We Start From SAQ's Default Plan

The default plan is a strong baseline. Therefore, our candidate generator does
not search all possible segmentations.

Instead:

```text
Take SAQ default plan P0.
Create a small neighborhood N(P0).
Only test local, explainable modifications.
```

This design keeps the method:

```text
query-unaware
computationally small
easy to inspect
close to SAQ's own design
```

Speaker notes:

- This is important because a broad arbitrary plan search would be harder to
  defend as a principled SAQ follow-up.

---

## 11. Candidate Families

Current local candidate families:

| family | intent |
|---|---|
| `head_split` | split the post-head block and move precision into it |
| `head_widen_keep_levels` | widen the first segment while preserving later bit levels |
| `speed_merge_same_tail` | merge middle/tail-positive dimensions into fewer positive segments |
| `tail_expand_middle_merge` | preserve a small head, merge middle dimensions, expand the zero tail |
| `tail_expand_head_widen` | widen the head, use broad middle chunks, expand the zero tail |

Feasibility guards:

```text
same bit budget
nonincreasing bitwidths
bounded segment count
positive-bit minimum
avoid promoted nonfinal 1-bit segments
```

Speaker notes:

- These are handcrafted but local and explainable.
- The current method story depends on keeping this candidate set small.

---

## 12. Running Example: Candidate Generation

Default GIST B=4 plan:

```text
64:11,192:6,320:4,256:2,128:0
```

Candidate:

```text
128:9,320:5,320:3,192:0
```

What changed?

```text
The head becomes wider:       64 dims -> 128 dims
The number of positive
segments becomes smaller:     4 -> 3
The zero tail becomes larger: 128 dims -> 192 dims
The plan spends bits in a more compact scan-friendly shape.
```

Why this might help:

```text
fewer positive segments
less fragmented scan work
more aggressive tail dropping
still enough precision in early/middle dimensions
```

Speaker notes:

- This candidate is from the `tail_expand_head_widen` family.
- The point is not that this shape is universally better; it passed the
  current scorer and measured validation on this setting.

---

## 13. Scoring: Why Boundary Pairs

ANN recall depends heavily on candidates near the top-k boundary.

If candidate A and candidate B have very different exact distances, a small
quantization error probably will not change their order.

If their exact distances are close, a small quantization error can flip the
ranking.

So the scorer focuses on close positive/negative boundary pairs.

Pair weight:

```text
weight = exp(-margin / tau)
```

Where:

```text
margin = exact_distance(negative) - exact_distance(positive)
```

Smaller margin means larger weight.

Speaker notes:

- This is the intuition behind the boundary-risk proxy.
- It is data-only because anchors are sampled from base vectors, not external
  query workloads.

---

## 14. Boundary Pair Construction

For each sampled base vector used as a pseudo-query:

1. Look inside the relevant IVF cell or local candidate set.
2. Sort neighboring base vectors by exact distance to the anchor.
3. Pick pairs around a local rank boundary.
4. Treat the closer item as positive and the farther item as negative.
5. Score whether a candidate plan increases the risk of reversing those pairs.

Important:

```text
These are not held-out benchmark queries.
These are base-as-pseudo-query diagnostics available during index construction.
```

Speaker notes:

- This is intentionally different from query-aware training.
- The exact pair sampling configuration is a diagnostic implementation detail;
  the high-level idea is boundary sensitivity.

---

## 15. Scorer Outputs

For each candidate plan, the scorer records:

```text
best_recall_risk_score
best_speed_proxy_ratio_vs_default
weighted soft-inversion ratio
weighted pair-ratio mean ratio
conservative eligibility
conservative rejection reasons
```

Interpretation:

```text
recall-risk < 1 means proxy risk is lower than default
speed-proxy < 1 means proxy scan cost is lower than default
soft-inversion <= 1 means weighted boundary-order risk is not worse than default
weighted-ratio <= 1 means boundary pair distance-ratio behavior is not worse
```

Speaker notes:

- These are proxies, not final measured recall.
- Earlier experiments showed that raw offline risk alone can be a false
  positive, so we need a promotion guard.

---

## 16. Promotion Policy

The selector considers only non-default candidates.

Current promotion order:

```text
1. conservative_eligible
2. frontier_like
3. abstain
```

Conservative promotion requires:

```text
weighted soft-inversion ratio <= 1.0
weighted pair-ratio mean      <= 1.0
speed-proxy ratio             <= 1.0
```

Frontier-like promotion requires:

```text
best_recall_risk_score <= 1.0
best_speed_proxy_ratio_vs_default <= 1.0
```

Speaker notes:

- Conservative is the safest class.
- Frontier-like is narrower and currently supported mainly by CIFAR positives.

---

## 17. Reject And Abstain Are Part Of The Method

Risky fallback is diagnostic only.

If a candidate is selected only because risky fallback was enabled, it is
treated as:

```text
reject/control
```

If there is no meaningful non-default candidate, the policy returns:

```text
abstain
```

This matters because the policy should not force a custom plan on every
dataset.

Speaker notes:

- DEEP is the reject/control example.
- Audio and word2vec are the abstention examples.

---

## 18. Running Example: Scorer Decision

GIST full K4096 B=4:

```text
default plan:   64:11,192:6,320:4,256:2,128:0
candidate plan: 128:9,320:5,320:3,192:0
family:         tail_expand_head_widen
```

Scorer signal:

```text
recall-risk = 0.9071
speed-proxy = 0.7792
role        = conservative_eligible
```

Interpretation:

```text
The candidate looks better than default on both boundary-risk proxy and
speed proxy, and it passes the conservative promotion guard.
```

Speaker notes:

- This is why the policy promotes it before final benchmark evaluation.
- Final recall/QPS still must be measured.

---

## 19. Final Evaluation Rule

All measured claims use corrected safe search:

```text
-searcher_safe_block_min_mode=2
```

Why this matters:

```text
Earlier native multi-segment search measurements had a padded-lane/block-min
issue. Safe search separates segment-plan quality from that implementation
artifact.
```

Metrics:

```text
GIST / DEEP / audio / word2vec: R@100
CIFAR: R@10
QPS: measured at the headline nprobe for that setting
```

Speaker notes:

- This slide is mainly to avoid methodology confusion.
- Any reported recall/QPS number should be tied to safe search.

---

## 20. Main Evidence Table

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

- The positive cases are not huge recall gains. The stronger story is recall
  preservation or slight improvement plus QPS gain.

---

## 21. Evidence Decomposition

The evidence decomposes into four policy classes:

```text
GIST: conservative positives
CIFAR: frontier-like positives
DEEP: reject/control cases
audio and word2vec: abstention cases
```

This is better than a single cherry-picked positive result because the policy
has different outputs for different plan shapes.

Speaker notes:

- This slide should be used to explain the method boundary.
- The method is not "always modify SAQ"; it is "modify only when the
  query-unaware evidence is good enough."

---

## 22. Applicability Classifier

Pre-scorer applicability:

| default shape | action |
|---|---|
| `single_uniform` | abstain |
| no feasible non-default candidate | abstain |
| `multi_segment_with_zero_tail` and feasible candidates | score candidates |
| `multi_segment_no_zero_tail` and feasible candidates | score cautiously as control |
| positive 1-bit default segment | allow default, but avoid promoted nonfinal 1-bit candidates |

Post-scorer decision:

| scorer result | action |
|---|---|
| conservative eligible | promote |
| frontier-like | promote |
| risky fallback only | reject/control |
| no selected candidate | abstain |

Speaker notes:

- This is deterministic and empirical, not learned.
- It gives us a clean answer for when the method applies.

---

## 23. Metric And Overhead Caveats

Recall was checked at multiple nprobe values.

Summary:

```text
GIST B=3/4/5: positive recall delta at all measured nprobes
CIFAR B=3/5: positive recall delta at all measured nprobes
CIFAR B=4:   negative at np50, positive at np100/np200/np400
DEEP B=4/5:  negative recall delta at all measured nprobes
```

QPS status:

```text
The main evidence table reports one headline nprobe per setting.
The overhead report also measured or reused QPS curve points across each
validation nprobe grid.
Promoted GIST/CIFAR rows remain speed-positive across that validation grid.
This still does not justify claims over every production operating point.
```

Overhead status:

```text
deployable overhead:
  candidate generation + boundary-pair scoring + one selected index build

experimental validation overhead:
  many candidate builds/evaluations used to validate the frozen policy

current GIST K4096 planner/scorer runtime:
  about 145-151 seconds per budget

current GIST selected/default index metadata time:
  about 2.3-3.0 seconds
```

Interpretation:

```text
The overhead story is not yet free.
The scorer dominates the current GIST planning cost.
This is acceptable only if the policy evidence is stronger than small tuning
gains and the cost is defensible relative to realistic offline indexing.
```

Speaker notes:

- This slide is important for avoiding overclaiming.
- CIFAR B=4 should be described as small and frontier-like, not uniformly
  positive at every operating point.
- If asked, distinguish the headline table from the overhead QPS-curve table:
  the curve exists, but it is still tied to the current validation grid and
  reused artifacts.
- If asked about overhead, separate deployable policy cost from experimental
  validation cost; the current GIST scorer runtime is the main weak point.

---

## 24. Implementation Fix: Separate From Contribution

GIST B=3 exposed a positive 1-bit segment bug in the implementation.

SAQ's legal default plan contains:

```text
64:9,192:5,320:3,192:1,192:0
```

The implementation fix made positive 1-bit segments buildable.

Important positioning:

```text
This is an upstream correctness repair.
It enables fair default-vs-custom validation.
It is not the fixed-policy method contribution.
```

Speaker notes:

- Mention this if the B=3 result comes up.
- Do not blur implementation repair with research contribution.

---

## 25. Reproducibility Status

Durable summary files:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
docs/saq_fixed_policy_method_spec_2026_07_07.md
docs/saq_fixed_policy_meeting_summary_2026_07_08.md
docs/saq_fixed_policy_input_manifest_2026_07_08.md
docs/saq_fixed_policy_input_preparation_driver_2026_07_08.md
```

Successful report/matrix commands:

```bash
python script/report_fixed_policy_validation.py \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv

python script/run_fixed_policy_matrix.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv

python script/prepare_fixed_policy_inputs.py \
  --verify-only \
  --output-json /tmp/saq-run/reports/fixed_policy_input_verify_2026_07_08.json
```

Current input verification readout:

```text
matched=20
missing=0
mismatch=0
total=20
```

The current matrix still uses local /tmp/saq-run artifacts for generated
intermediate outputs, but the input substrate is now identifiable by full-file
hashes and tied to documented preparation commands.

Speaker notes:

- For meeting, the evidence table and input identity are durable.
- For paper, the remaining artifact step is fresh-root verification or an
  archived input bundle, not rediscovering what the input files were.

---

## 26. What We Can Claim Today

Safe claim:

```text
Diagnosis:
SAQ's variance-driven DP plan optimizes a global quantization-error proxy, but
can be locally mismatched with IVF-local ranking boundaries and segment-shape
search cost.

Policy:
A frozen query-unaware default-neighborhood policy uses only base/index
artifacts to promote, reject, or abstain around SAQ's default plan.

Evidence:
GIST/CIFAR show repeated positives, DEEP gives reject controls, and
audio/word2vec give abstention cases under safe-search evaluation and overhead
accounting.
```

What this means:

```text
The current method has a clear decision boundary.
It is not just one hand-picked custom plan.
It produces positive, reject, and abstain outcomes.
The current experiment can be checked through a manifest and driver.
The contribution is the safe decision policy, not raw metric improvement.
```

Speaker notes:

- This is the best current framing: diagnosis, policy, evidence.
- It is empirical and should be presented as such.
- The reproducibility progress strengthens the evidence, but does not change
  the fact that this is a policy layer around SAQ.
- Do not sell this as a new quantizer or as a universal SAQ replacement.

---

## 27. What We Should Not Claim Yet

Unsafe claims:

```text
The method universally improves SAQ.
The method is theoretically guaranteed.
The method is query-aware or workload-optimized.
QPS gains are characterized across all production operating points.
Single-uniform default datasets can already be improved by this generator.
The current policy is an independent quantizer rather than a SAQ correction layer.
```

Current limitations:

```text
novelty is currently low-to-medium to medium
meeting-report / technical-note quality is stronger than full-paper quality
positive recall deltas are small
frontier-like promotion is weaker than conservative promotion
fresh-root artifact validation or input-bundle packaging still needs work
candidate families are handcrafted and local
added scorer/build/search overhead must be justified against small gains
scorer value over speed-only or random-local baselines is not yet proven
```

Speaker notes:

- This slide is intentionally conservative.
- It should help the advisor evaluate whether the story is still worth
  developing.
- A strict reviewer will likely ask whether the candidate families were
  designed after seeing GIST/CIFAR behavior.

---

## 28. Open Research Questions

Question 1:

```text
Is a shape-dependent fixed-policy correction around SAQ's default plan a
worthwhile contribution for a SIGMOD/VLDB/ICDE-level paper?
```

Question 2:

```text
Should the next step focus on formalizing the policy and its applicability
classifier, or expanding the candidate generator within the same query-unaware
boundary?
```

Question 3:

```text
What level of evidence is needed before this becomes paper-worthy:
more datasets, fresh-root verification, stronger ablations, or a stronger theory?
```

Question 4:

```text
What concrete SAQ limitation should be the center of the contribution,
and what overhead budget is acceptable for correcting it?
```

Question 5:

```text
Can the boundary-risk scorer be shown to select safer plans than speed-only,
random-local, or guard-removed alternatives?
```

Speaker notes:

- These are the meeting decisions.
- If the advisor does not like the fixed-policy framing, the next move is
  probably not more small GIST sweeps.

---

## 29. Recommended Next Steps

Near-term reproducibility:

```text
run preparation/verification driver on a fresh experiment root
decide whether to archive the manifest-matching input bundle
keep safe-searcher mode mandatory for measured claims
```

Near-term experimental validation:

```text
report existing validation-grid QPS curves consistently in the main narrative
preserve DEEP reject behavior under any policy change
run ablations before adding any new candidate family
```

Near-term method work:

```text
formalize the applicability classifier
decide whether handcrafted local families are enough
consider new local families only if they expose a clearer SAQ limitation
account for candidate, scorer, build, metadata, and search overhead explicitly
```

Required ablations before more sweeps:

```text
boundary-risk scorer vs speed-only scorer
boundary-risk scorer vs random local candidate
conservative promotion vs frontier-like promotion
remove soft-inversion / pair-ratio guards
selected candidate vs local oracle
proxy-score correlation with measured recall delta and QPS ratio
```

Stop-loss condition:

```text
If the story remains only "local rules find a few plans with nearly unchanged
recall and modest QPS gains," then novelty is not enough for a full paper;
pivot to a clearer SAQ limitation such as planner-objective redesign,
segment-cost-aware DP, or a more explainable search-aware query-unaware proxy.
```

Speaker notes:

- My suggested path is to first prove the fixed-policy story with ablations,
  then decide whether to invest in new generator families.
- Additional sweeps should be gated by novelty and overhead, not only by the
  possibility of a small recall/QPS improvement.
- Before proposing a new direction, run the severe-reviewer argument against
  it: what would make this look like tuning, and what evidence would answer
  that objection?

---

## 30. Backup: Running Example In One Line

GIST full K4096 B=4:

```text
SAQ default:
64:11,192:6,320:4,256:2,128:0

Fixed-policy candidate:
128:9,320:5,320:3,192:0

Selection:
conservative_eligible
recall-risk = 0.9071
speed-proxy = 0.7792

Measured:
R@100 np800: 0.98845 -> 0.98922
QPS np800:   1013.64 -> 1211.10
```

Takeaway:

```text
A local query-unaware plan change can preserve or slightly improve recall while
reducing search work enough to improve QPS.
```

---

## 31. Backup: Policy In Pseudocode

```text
Input:
  SAQ default plan P0
  average bit budget B
  offline base/index artifacts

Procedure:
  shape = classify(P0)

  if shape == single_uniform:
      return abstain

  candidates = generate_default_neighborhood(P0, B)
  candidates = filter_feasible(candidates)

  if candidates is empty:
      return abstain

  scores = score_with_data_only_boundary_pairs(candidates)

  if any conservative_eligible candidate:
      return promote(best_conservative_candidate)

  if any frontier_like candidate:
      return promote(best_frontier_like_candidate)

  return abstain

Diagnostic:
  if risky fallback is enabled:
      selected fallback candidate is reported as reject/control, not promotion
```

Speaker notes:

- This is a useful backup if the advisor asks what exactly the method is.

---

## 32. Backup: Evidence Boundary

The current evidence is strongest for:

```text
multi-segment SAQ default plans
zero-tail plans
datasets with enough middle/tail positive dimensions to redistribute
headline operating points with corrected safe search
```

The current evidence is weakest for:

```text
single-uniform default plans
frontier-like candidates with tiny recall deltas
claims about full QPS operating curves
fresh-root reproducibility or archived-input packaging
```

The current method should therefore be presented as:

```text
empirical
query-unaware
shape-dependent
local to SAQ's default plan
```

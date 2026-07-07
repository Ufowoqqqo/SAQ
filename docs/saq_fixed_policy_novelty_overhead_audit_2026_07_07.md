# SAQ Fixed-Policy Novelty And Overhead Audit

Date: 2026-07-07

This audit answers the A0 gate in `EXPERIMENTS.md`: before running more
expensive sweeps, decide whether the current default-neighborhood fixed policy
has a defensible contribution beyond local tuning of SAQ, and account for the
extra cost it adds.

## Bottom Line

The current method should not be presented as an independent quantizer or as a
strictly better replacement for SAQ. It is a query-unaware local policy layer on
top of SAQ's default segment plan.

The defensible contribution, if we continue, is narrower:

```text
SAQ's default global variance-based segment plan can be locally mismatched to
the IVF-local ranking boundary and to the search/refinement cost of different
segment shapes. A small data-only neighborhood scorer can detect some of these
mismatches, promote low-risk local repairs, reject speed-only repairs that hurt
recall, and abstain when the default shape gives no meaningful local handle.
```

This is an incremental contribution. It is worth continuing only if the extra
offline scorer cost stays small, the final index format remains SAQ-compatible,
and the method avoids broad plan search or repeated custom index builds as part
of the deployable pipeline.

## Concrete SAQ Limitation Being Targeted

SAQ already does the major algorithmic work:

1. It uses PCA to concentrate variance.
2. It uses dynamic programming to choose a global segmented bit plan.
3. It uses CAQ inside segments to avoid expensive E-RaBitQ-style enumeration.
4. It supports multi-stage search/refinement from the chosen plan.

The current fixed-policy work targets a more specific limitation:

```text
SAQ's default planner is global and variance-driven. It does not directly
optimize IVF-local near-boundary ranking stability, and it does not directly
optimize the measured search cost induced by segment shape.
```

This matters because nearest-neighbor recall is usually lost at close
positive/negative boundaries. A plan that is good for global reconstruction or
global variance allocation can still spend bits or segments in a way that is
not ideal for these local boundary pairs. Conversely, a plan that is faster can
be dangerous if it reduces segment work by damaging those same close
boundaries.

The current method uses base vectors as pseudo-queries inside IVF cells to form
data-only boundary pairs. This keeps the method query-unaware while exposing a
ranking-oriented signal that SAQ's global variance DP does not explicitly use.

## What The Current Method Adds

Deployable fixed-policy pipeline:

1. Run the normal SAQ artifact preparation: PCA, IVF assignment, and default
   plan generation.
2. Classify the default plan shape.
3. If the default plan is single-uniform or has no feasible local neighborhood,
   abstain and use SAQ default.
4. Generate a small local candidate set around the SAQ default plan.
5. Score candidates with data-only boundary-risk and speed proxies.
6. Promote a conservative/frontier-like candidate, reject risky speed-only
   candidates, or abstain.
7. Build the final selected SAQ index once.

This is different from the research sweep pipeline, which built/evaluated many
candidate indexes to establish evidence. The research sweep overhead should not
be hidden, but it should also not be confused with the intended deployable
method if the policy is frozen.

## Baseline Pipeline Versus Fixed Policy

| Stage | SAQ baseline | Fixed-policy deployable pipeline | Research/evidence pipeline |
|---|---|---|---|
| PCA / IVF artifacts | required | same as SAQ | same as SAQ |
| Default plan DP | required | required | required |
| Candidate generation | none | small local neighborhood around default | same, sometimes multiple budgets/datasets |
| Boundary-pair scorer | none | extra data-only offline pass | extra pass plus diagnostic grids |
| Index build | build SAQ default once | build selected plan once after scoring | build default and selected candidates for validation |
| Query workload used for selection | no | no | no for selection; held-out queries only for final evaluation |
| Search code path | SAQ searcher | SAQ searcher with selected plan | same, evaluated with safe search |
| Extra metadata | none beyond SAQ | no new method-level metadata; plan shape may change segment-factor overhead | same |

The practical comparison should be:

```text
SAQ default build/search
vs.
SAQ artifact prep + fixed-policy scoring + one selected-plan build/search
```

It should not be:

```text
SAQ default final QPS
vs.
best custom-plan final QPS after ignoring all candidate scoring and validation builds
```

## Overhead Accounting

### Candidate Generation

Current generator:

```text
script/generate_default_neighborhood_plans.py
```

Implemented families:

```text
head_split
head_widen_keep_levels
speed_merge_same_tail
tail_expand_middle_merge
tail_expand_head_widen
```

The generator is local and deterministic. It manipulates a short segment-plan
list rather than scanning the vector dataset or searching the full DP plan
space. In the current clean validation artifacts, applicable cases usually
produce only a few feasible unique plans:

```text
GIST B=3: 2 candidate rows / 2 unique rows
GIST B=4/B=5: 5 candidate rows / 5 unique rows
CIFAR B=3/B=4/B=5: 4 candidate rows / 4 unique rows
DEEP B=4/B=5: 2 candidate rows / 2 unique rows
audio and word2vec B=4: 1 default-only row, scorer skipped
```

This part is not the main overhead. The risk is not runtime; the risk is
methodological. Adding more and more hand-written local families would turn the
method into ad hoc tuning unless each family exposes a clear SAQ failure mode.

### Boundary-Pair Sampling

Current sampler:

```text
script/sweep_data_boundary_pairs.py::sample_boundary_pairs
```

Default matrix settings from `script/run_default_neighborhood_cross_dataset.py`:

```text
max_anchors = 4096
max_pairs = 20000
max_candidates_per_anchor = 2048
boundary_rank = 100
neighbor_window = 8
pairs_per_anchor = 4
anchors_per_cluster = 1
pair_seed = 0
```

For each sampled anchor, the sampler:

1. stays inside the anchor's IVF cell;
2. optionally caps candidate cell members at `max_candidates_per_anchor`;
3. computes exact distances from the anchor to sampled same-cell candidates;
4. sorts candidates by distance;
5. forms positive/negative pairs around the local boundary rank;
6. keeps the smallest-margin pairs, with positive margin only.

Approximate complexity:

```text
A = sampled anchors, capped by max_anchors
C = candidates per anchor, capped by max_candidates_per_anchor
D = padded dimension
P = sampled pairs, capped by max_pairs

sampling distance work: O(A * C * D)
per-anchor sort work:  O(A * C log C)
pair vector work:      O(P * D)
```

Current artifact examples:

```text
GIST K4096 B=3/B=4/B=5: 3685 anchors, 14740 pairs
CIFAR B=3/B=4/B=5:       267 anchors,  1068 pairs
DEEP B=4/B=5:            476 anchors,  1904 pairs
```

This is the main extra deployable offline cost relative to SAQ. It is much
smaller than full query evaluation, but it is not free and must be timed before
claiming practical superiority.

### Scoring Grid

The current scorer evaluates boundary-risk and speed-proxy terms over a
diagnostic hyperparameter grid. Current selected rows record `config_count =
6720` for the top candidates in the fixed-policy matrix artifacts.

This is acceptable for research diagnostics, but it is too easy to overstate as
a practical method. A deployable version should freeze a small scoring rule or
at least report scorer runtime and config count as part of the index-build
budget.

If future gains require increasing this grid or trying many scorer settings,
that should be treated as extra method complexity, not free optimization.

### Extra Index Builds

For deployment, the method can score candidates before building the final index
and then build only the selected plan. In that interpretation, it does not need
to build SAQ default plus many custom indexes.

For research validation, we have built default and selected/custom indexes and
run compare/QPS binaries. That validation cost is real for the experiment, but
it should not be counted as deployable overhead if the final policy is frozen.

The current docs should therefore use two separate phrases:

```text
deployable overhead: candidate generation + boundary-pair scoring + one final build
experimental overhead: many candidate builds/evaluations used to validate the policy
```

### Memory And Metadata

The current method does not add new per-vector metadata fields beyond SAQ. It
chooses another legal SAQ segment plan under the same average bit budget.

However, segment shape can change metadata constants because SAQ stores factors
per positive segment. Plans with fewer positive segments may reduce such
overhead, while plans with more positive segments may increase it. We should
not claim memory superiority until actual index sizes or serialized component
sizes are measured for default and selected plans.

Current safe statement:

```text
The fixed policy adds no new method-level metadata beyond SAQ, but exact memory
impact depends on the selected segment count and should be measured.
```

### Search-Time Overhead

The selected plan uses the same SAQ searcher and does not require a
query-workload model, learned reranker, or extra per-query candidate selection
branch. Its search-time effect comes from the segment plan itself:

```text
positive segment count
zero-tail size
nonzero dimensional coverage
bitwork
```

The current clean table reports headline QPS improvements for promoted rows,
but QPS is measured at one run-specific nprobe. This is useful evidence, not a
complete speed characterization. Paper-style claims need QPS curves or
explicitly scoped headline operating points.

## Benefit Versus Overhead In Current Evidence

Source:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Promoted positives:

| Setting | Recall delta | QPS ratio | Audit interpretation |
|---|---:|---:|---|
| GIST full K4096 B=3 | +0.00159 R@100 | 1.1119x | useful if scorer overhead is small; also depends on the 1-bit correctness fix |
| GIST full K4096 B=4 | +0.00077 R@100 | 1.1948x | strongest current case because QPS gain is material |
| GIST full K4096 B=5 | +0.00028 R@100 | 1.0793x | positive but recall gain is tiny; speed story matters more |
| CIFAR60K B=3 | +0.0004 R@10 | 1.0761x | small positive; contribution value is weak without overhead accounting |
| CIFAR60K B=4 | +0.0004 R@10 | 1.0745x | frontier-like case; should be presented cautiously |
| CIFAR60K B=5 | +0.0008 R@10 | 1.0609x | small positive; not enough alone for novelty |

Reject/abstain evidence:

| Setting | Result | Audit interpretation |
|---|---|---|
| DEEP B=4/B=5 | reject speed-only candidates | valuable negative control; prevents hiding recall loss behind QPS |
| audio B=4 | abstain | method boundary is explicit for single-uniform defaults |
| word2vec B=4 | abstain | same abstention boundary |

Current verdict:

```text
The strongest evidence is not "higher recall everywhere." It is:

1. repeated shape-dependent positives on GIST/CIFAR;
2. a conservative guard that rejects DEEP speed-only false positives;
3. explicit abstention on single-uniform plans;
4. no query workload used for selection.
```

This is enough for a meeting-level hypothesis. It is not yet enough for a
strong paper-style claim of strict superiority over SAQ.

## Experiments We Should Not Run Next

Do not run new expensive sweeps whose only purpose is to find a slightly better
custom plan unless the added method logic is justified by a concrete SAQ
failure mode.

Specifically, avoid:

1. Broad full-plan search unrelated to the default neighborhood.
2. Larger scorer grids without a plan to freeze/report scorer overhead.
3. More candidate families that only encode hindsight from GIST/CIFAR.
4. Any query-aware candidate selection under the current query-unaware goal.
5. Promoting `--allow-risky-fallback` winners as method outputs.
6. Treating DEEP speed-only QPS wins as positive evidence.
7. New dataset builds before we can report scorer runtime, candidate count,
   index size, and one-build deployment cost for existing cases.

## Required Measurements Before Stronger Claims

Before presenting the fixed policy as more than a local empirical correction,
collect:

1. Candidate generation count and wall-clock time per dataset/budget.
2. Boundary-pair sampler wall-clock time, anchors, pairs, and candidate cap.
3. Scorer config count and wall-clock time.
4. Final selected-index build time versus SAQ default build time.
5. Serialized index size or component memory for default versus selected plan.
6. QPS curves, not only one headline nprobe, for at least the key positive
   cases.
7. Confirmation that selection does not depend on held-out query labels.

## Stop Or Pivot Criteria

Stop expanding this direction, or pivot to a different SAQ limitation, if:

1. Gains remain at the level of tiny recall deltas and modest one-point QPS
   gains after scorer/build/memory overhead is included.
2. Positive cases require many candidate builds or large scorer grids to find.
3. The method cannot explain why the SAQ default planner misses the selected
   plan except "the benchmark result is better."
4. New logic breaks DEEP reject behavior or audio/word2vec abstention.
5. The final story becomes "we tune SAQ's plan with extra offline work" rather
   than a clear query-unaware diagnosis of SAQ's planner limitation.

## Recommendation

Mark A0 as completed for documentation and decision-making. The next safest
technical step is not another plan sweep. It is to make overhead accounting
reproducible:

```text
add/report candidate counts, scorer runtime, pair counts, index build time,
index size, and QPS curves for the existing fixed-policy validation cases.
```

Only after that should we decide whether to expand the candidate generator or
move toward a different, more novel SAQ follow-up direction.

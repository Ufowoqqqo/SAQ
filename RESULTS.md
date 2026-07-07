# RESULTS.md

This file records stable conclusions for the SAQ fixed-policy/default-neighborhood follow-up. Update it only when evidence is durable enough to survive across Codex sessions.

## Stable Current Claim

The current evidence supports a **shape-dependent, query-unaware fixed policy** for local SAQ segment-plan adjustment:

1. Start from SAQ's default plan.
2. Generate a small local default-neighborhood candidate set.
3. Score candidates using data-only boundary-risk and speed proxies.
4. Promote conservative candidates when proxy risk and speed are no worse than default.
5. Allow a narrow frontier-like fallback when recall-risk and speed proxy are both no worse than default.
6. Reject speed-only candidates that substantially increase recall-risk proxies.
7. Abstain when the SAQ default is single-uniform or no meaningful local candidate exists.

This should be presented as an empirical, query-unaware correction/policy layer around SAQ's default plan, not as a universal replacement for SAQ's planner.

## Current Evidence Table

| Dataset / setting | Decision | Plan | Recall result | QPS result | Interpretation |
|---|---:|---|---:|---:|---|
| GIST full K4096 B=3 | promote | `64:8,320:5,320:2,256:0` | +0.00159 R@100 at np800 | 1.1119x | positive after 1-bit fix |
| GIST full K4096 B=4 | promote | `128:9,320:5,320:3,192:0` | +0.00077 R@100 at np800 | 1.1948x | strongest QPS-positive GIST case |
| GIST full K4096 B=5 | promote | `128:9,128:7,320:5,320:3,64:0` | +0.00028 R@100 at np800 | 1.0793x | positive high-budget holdout |
| CIFAR60K B=3 | promote | `128:6,64:4,192:2,128:0` | +0.0004 R@10 at np200 | 1.0761x | small positive low-budget holdout |
| CIFAR60K B=4 | promote | `128:7,256:4,128:0` | +0.0004 R@10 at np200 | 1.0745x | small positive original case |
| CIFAR60K B=5 | promote | `128:8,64:6,256:4,64:0` | +0.0008 R@10 at np200 | 1.0609x | small positive high-budget holdout |
| DEEP100K B=4 | reject | `128:4,128:3` | -0.02757 R@100 at np200 | 1.0893x | speed gain costs too much recall |
| DEEP100K B=5 | reject | `128:5,128:4` | -0.01429 R@100 at np200 | 1.1037x | speed gain costs too much recall |
| audio B=4 | abstain | none | n/a | n/a | single-uniform default; scan also abstains at B=3/B=5 |
| word2vec100K B=4 | abstain | none | n/a | n/a | single-uniform default; scan also abstains at B=3/B=5 |

Source of table: `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv` and `docs/saq_fixed_policy_method_spec_2026_07_07.md`.

## Important Supporting Findings

### 1. Conservative guard fixed the B=5 v3 false-positive failure mode

A previous GIST sample100k B=5 raw planner-v3 recall-risk endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

looked good offline but was a measured false positive under corrected safe search. The conservative role guard rejected it because it was worse than default on soft-inversion ratio, weighted pair-ratio, and speed-proxy ratio. The conservative role instead selected:

```text
64:10,192:8,256:5,384:3,64:0
```

### 2. Full GIST K4096 B=4 shows the recall/speed Pareto framing

The v3 diagnostics expose endpoints:

- recall-risk endpoint: `64:9,64:7,128:6,320:4,256:2,128:0`, higher measured recall but slower;
- speed endpoint: `128:9,320:5,320:3,192:0`, faster and still positive recall.

The fixed-policy guard promotes the safer speed-positive point rather than the highest-recall point.

### 3. Applicability is shape-dependent

The current generator is most meaningful when SAQ's default plan has a multi-stage bit ladder, especially with a zero tail and enough middle/tail positive dimensions to redistribute.

Current scan readout:

- GIST and CIFAR: scan-worthy across B=3/B=4/B=5.
- DEEP: useful negative/control family; B=4/B=5 candidate loses too much recall.
- audio and word2vec: stable abstention cases under B=3/B=4/B=5.

### 4. GIST B=3 1-bit fix is a correctness repair

The GIST B=3 default plan contains a positive 1-bit segment:

```text
64:9,192:5,320:3,192:1,192:0
```

A minimal fix was needed because the encoder did not export `base_code.code` for positive 1-bit segments while the packer expected short codes for every positive-bit segment. This unblocked fair default-vs-custom validation. It should be described separately from the fixed-policy method contribution.

## Current Caveats

- The current evidence is empirical and benchmark-limited.
- Positive recall deltas are small; the stronger story is often preserving/improving recall while improving QPS.
- Local artifacts under `/tmp/saq-run` are not durable unless summarized in checked-in docs.
- The policy thresholds are empirically motivated, not theoretically guaranteed.
- Frontier-like fallback is useful for CIFAR but must remain narrow to avoid reintroducing false positives.
- Do not claim the method applies to single-uniform default-plan datasets under the current generator.
- Do not claim strict superiority over SAQ until added offline scoring,
  candidate generation, index-build, metadata, and search-time overhead are
  accounted for. The current method is a local policy layer around SAQ's
  default plan, not an independent quantizer.

## Recommended Next Stable Results To Seek

1. Make the fixed-policy matrix reproducible on a clean machine or document the
   exact dataset/artifact preparation gap.
2. Preserve DEEP reject and audio/word2vec abstention behavior under any future
   generator/scorer change.
3. If expanding the generator, first state the SAQ failure mode and added
   overhead, then validate against GIST/CIFAR positives, DEEP rejects, and
   audio/word2vec abstentions.

## Result 2026-07-08: Cost-reduced official runner reproduces the full matrix under safe evaluation

### Claim

The integrated query-unaware feature-cache and endpoint-grid scorer path now
reproduces the full checked-in fixed-policy validation matrix through the
official runner with safe-search evaluation enabled.

### Evidence

- Evaluation note:
  `docs/saq_fixed_policy_runner_cost_reduced_full_eval_2026_07_08.md`
- Previous integration note:
  `docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md`

Command:

```bash
python script/run_fixed_policy_matrix.py \
  --use-cost-reduced-scorer \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Generated outputs:

```text
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_08_runner_cost_reduced_eval.csv
/tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_08_runner_cost_reduced_eval.md
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_08_runner_cost_reduced_eval.manifest.json
```

Report result:

```text
Expected table matches: docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
Decision counts: {'promote': 6, 'reject': 2, 'abstain': 2}
```

### Interpretation

This closes the earlier gap where cost-reduced runner evidence was
selection-only. The official runner now supports the same fixed-policy evidence
table with cost-reduced scorer execution and safe-search evaluation. The
result should still be described as a scorer execution/reproducibility
improvement around the fixed-policy method, not as a new SAQ quantizer.

### Limitations

The artifacts are local under `/tmp/saq-run`. Matching safe QPS artifacts were
reused where present, so the run validates the official evaluation path but
does not prove that every QPS CSV was recomputed from scratch.

## Result 2026-07-07: Cost-reduced scorer is integrated into the official runners

### Claim

The query-unaware feature-cache and endpoint-grid scorer path is now available
from the official fixed-policy runners, not only from the calibration driver.
The official matrix runner reproduces the current fixed-policy decisions and
selected/tested plans under this scorer path.

### Evidence

- Integration note:
  `docs/saq_fixed_policy_runner_cost_reduced_integration_2026_07_07.md`
- Updated method spec:
  `docs/saq_fixed_policy_method_spec_2026_07_07.md`
- Updated runners:
  - `script/run_default_neighborhood_cross_dataset.py`
  - `script/run_fixed_policy_matrix.py`

Verification command:

```bash
python script/run_fixed_policy_matrix.py \
  --skip-scan \
  --skip-report \
  --no-evaluate \
  --force \
  --use-cost-reduced-scorer \
  --date 2026_07_07_runner_cost_reduced \
  --artifact-date 2026_07_07_runner_cost_reduced
```

Output summary:

```text
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07_runner_cost_reduced.json
/tmp/saq-run/reports/fixed_policy_matrix_2026_07_07_runner_cost_reduced.manifest.json
```

Selection equivalence against the checked-in clean table:

```text
decision match: 10/10
plan match:     10/10
```

### Interpretation

This closes the gap between the scorer calibration experiment and the formal
fixed-policy pipeline. Future runs can use `--use-cost-reduced-scorer` to get
endpoint-grid scorer evaluation and query-unaware feature caching through the
same matrix runner used for the rest of the evidence.

### Limitations

The verification above is scorer/selection-only because it used `--no-evaluate`.
It does not rerun safe-search recall/QPS. The official integration also keeps
the per-run sampling parameters unchanged; the previously calibrated `a1024_p2`
sampling setting remains a separate calibration result rather than a formal
runner default.

## Result 2026-07-07: Feature caching reduces scorer overhead without changing decisions

### Claim

The current scorer overhead is dominated by residual/tail feature computation,
not by the final scorer grid. A query-unaware feature cache plus a compact
endpoint grid preserves the current fixed-policy matrix decisions and selected
plans while substantially reducing measured scorer runtime.

### Evidence

- Cold-cache cost report:
  `docs/saq_fixed_policy_scorer_cost_reduction_2026_07_07.md`
- Warm-cache cost report:
  `docs/saq_fixed_policy_scorer_cost_reduction_warm_2026_07_07.md`
- Driver changes:
  - `script/score_default_neighborhood_plans.py`
  - `script/run_scorer_calibration.py`

Cold-cache full matrix, using a fresh feature-cache directory:

```text
decision match: 10/10
plan match:     10/10
runtime:        147.082 seconds
reference:      481.764 seconds
ratio:          0.305
```

Warm-cache full matrix, with all non-abstention dataset/K feature caches
already available:

```text
decision match: 10/10
plan match:     10/10
runtime:        5.656 seconds
reference:      481.764 seconds
ratio:          0.012
```

The cold-cache phase timings show why earlier pair-count reduction did not
solve the cost:

```text
residual-risk time:        111.166 seconds
tail-risk time:             28.985 seconds
boundary-pair sampling:      1.251 seconds
scoring-grid enumeration:    0.058 seconds
```

### Interpretation

The endpoint grid is useful for reducing the number of scored configurations
to about 0.5% of the previous grid while preserving current decisions/plans,
but the main runtime reduction comes from reusing residual/tail/pair features
across B values for the same dataset/K/sampling setting. This is an
implementation-level cost reduction for the fixed-policy scorer, not a new
quantization method or independent contribution beyond SAQ.

### Limitations

The cache is stored under `/tmp/saq-run/reports/...` in the current evaluation
and is not a durable checked-in artifact. The feature cache is query-unaware,
but it is specific to dataset path, IVF K, sampling parameters, residual-risk
statistic, and tail-risk quantile. If any of those change, the cache key changes
and the scorer correctly recomputes features.

The compact endpoint grid is calibrated against the current fixed-policy
matrix. It should be described as a cost-reduction evaluation for this policy,
not as evidence that the full grid is unnecessary for all future candidate
families.

## Result 2026-07-07: Scorer calibration preserves decisions but does not solve full-GIST cost

### Claim

A smaller boundary-pair scorer setting can reproduce the current fixed-policy
decisions, but reducing sampled pair count alone is not enough to make the
full-GIST scorer cheap.

### Evidence

- Representative calibration report:
  `docs/saq_fixed_policy_scorer_calibration_2026_07_07.md`
- Full `a1024_p2` calibration report:
  `docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.md`
- Driver:
  `script/run_scorer_calibration.py`

Full fixed-policy matrix with preset `a1024_p2`:

```text
decision match: 10/10
plan match:     10/10
total runtime:  456.967 seconds
```

Cost readout against the previous full-scorer overhead summary:

```text
GIST B=3/B=4/B=5: 14,740 -> 2,048 pairs, runtime ratio about 0.94-0.95
CIFAR B=3/B=4/B=5: 1,068 -> 534 pairs, runtime ratio about 0.97-0.98
DEEP B=4/B=5: 1,904 -> 952 pairs, runtime ratio about 0.98
```

The smaller representative presets `a256_p1` and `a512_p1` preserve the
promote/reject/abstain decision on the four checked representative runs, but
they select a different GIST B=4 plan. They are therefore too aggressive if the
goal is exact selected-plan stability.

### Interpretation

The current stable scorer calibration point is `a1024_p2`. It is useful as a
calibrated lower-pair-count setting for reproducibility, but it does not remove
the main overhead concern. The full-GIST runtime remains close to the original
scorer even after pair count falls to about 13.9% of the previous setting,
which suggests that residual/tail feature computation, file I/O, or scorer-grid
evaluation dominates the current implementation.

### Limitations

This is a calibration evaluation against the current fixed-policy matrix, not
an end-to-end recall/QPS rerun. It intentionally does not use held-out query
labels for selection. Runtime is wall-clock timing from the Python scorer
driver and should be treated as an implementation-level overhead measurement.

### Follow-up

The next useful cost-reduction step is to evaluate cached residual/tail
features and a smaller scoring grid. Additional pair subsampling is unlikely to
be the highest-value direction unless it is combined with one of those changes.

## Result 2026-07-07: Overhead evaluation identifies scorer cost as the main added cost

### Claim

The fixed-policy layer's deployable overhead is dominated by data-only
boundary-pair sampling and scorer-grid evaluation, not candidate generation or
final selected-index build time.

### Evidence

- Report:
  `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md`
- Summary table:
  `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.summary.csv`
- QPS curve table:
  `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.qps_curve.csv`
- Driver:
  `script/report_fixed_policy_overhead.py`

Measured planning runtime:

```text
GIST full K4096 B=3/B=4/B=5: about 145-151 seconds per budget
CIFAR60K B=3/B=4/B=5:       about 8.5-8.6 seconds per budget
DEEP100K B=4/B=5:           about 5.8 seconds per budget
audio/word2vec abstain:     about 0.1 seconds, generator only
```

The full GIST scorer samples 14,740 boundary pairs from 3,685 anchors. CIFAR
uses 1,068 pairs from 267 anchors, and DEEP uses 1,904 pairs from 476 anchors.

### Interpretation

The current method can still be described as a one-index deployable pipeline,
but its planner/scorer overhead is not negligible on full GIST. Any future
claim of practical value should either reduce the scorer cost, show that this
offline cost is acceptable relative to large-scale indexing, or demonstrate
that a smaller sampled scorer preserves the same promote/reject/abstain
decisions.

### Limitations

Planner runtime is a single wall-clock measurement and includes Python startup,
I/O, boundary-pair sampling, and scorer-grid evaluation. Index build time is
read from existing `create_index` metadata rather than newly repeated build
timing in this run.

### Follow-up

The next useful research step is to evaluate whether scorer cost can be reduced
without changing the selected plans: fewer anchors, fewer pairs, a smaller
scorer grid, or cached boundary-pair features.

## Result 2026-07-07: Novelty and overhead audit narrows the claim

### Claim

The current default-neighborhood fixed policy is best treated as a
query-unaware local correction layer around SAQ's default segment plan, not as
an independent quantizer or strict replacement for SAQ.

### Evidence

- Audit doc:
  `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`
- Method spec:
  `docs/saq_fixed_policy_method_spec_2026_07_07.md`
- Clean validation table:
  `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
- Relevant code paths:
  - `script/generate_default_neighborhood_plans.py`
  - `script/sweep_data_boundary_pairs.py`
  - `script/run_default_neighborhood_cross_dataset.py`

### Interpretation

The defensible SAQ limitation is narrow: SAQ's global variance-based default
planner does not directly model IVF-local ranking-boundary risk or the search
cost induced by segment shape. The fixed policy is potentially useful only if
its extra offline candidate generation and boundary-pair scoring remain small,
it builds one final selected SAQ-compatible index, and it continues to
promote/reject/abstain without using held-out query labels.

### Limitations

The current evidence is meeting-level, not a strong superiority claim. Positive
recall deltas are small, QPS is currently reported at headline nprobe values,
and exact scorer runtime, index-build time, and index-size overhead still need
to be measured.

### Follow-up

Before new expensive sweeps or candidate-family expansion, add reproducible
overhead reporting for the existing validation cases.

## Result 2026-07-07: Fixed-policy report and matrix reproduce the checked-in table

### Claim

The checked-in clean fixed-policy validation table is reproducible from the
current report scripts and the available local `/tmp/saq-run` artifacts.

### Evidence

- Dataset / K / B: fixed-policy matrix covering GIST full K4096 B=3/4/5,
  CIFAR60K K512 B=3/4/5, DEEP100K K512 B=4/5, audio K4096 B=4, and
  word2vec100K K512 B=4.
- Plan: the promoted/rejected/abstained plans listed in
  `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`.
- Metric: R@100 for GIST/DEEP/audio/word2vec and R@10 for CIFAR.
- nprobe / top-k: run-specific nprobe from the clean table; GIST uses np800,
  CIFAR/DEEP use np200 for the headline row.
- Searcher mode: generated evaluation artifacts use corrected safe search,
  `-searcher_safe_block_min_mode=2`.
- Commands:

  ```bash
  python -m py_compile script/sweep_data_boundary_pairs.py script/generate_default_neighborhood_plans.py script/score_default_neighborhood_plans.py script/run_default_neighborhood_cross_dataset.py script/run_fixed_policy_matrix.py script/report_fixed_policy_validation.py
  python script/report_fixed_policy_validation.py --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
  python script/run_fixed_policy_matrix.py --artifact-date 2026_07_06 --expected-csv docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
  ```

- Artifact path:

  ```text
  /tmp/saq-run/reports/fixed_policy_validation_2026_07_07.csv
  /tmp/saq-run/reports/fixed_policy_validation_2026_07_07.md
  /tmp/saq-run/reports/fixed_policy_validation_2026_07_07.json
  /tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
  /tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.json
  /tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.csv
  /tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.md
  /tmp/saq-run/reports/fixed_policy_validation_matrix_2026_07_07.json
  /tmp/saq-run/reports/fixed_policy_matrix_2026_07_07.manifest.json
  ```

### Interpretation

The fixed-policy table is no longer only a manually curated summary. The report
driver exactly matches the checked-in CSV, and the matrix runner reproduces the
same decisions from existing artifacts, ignoring only the expected
`source_report` filename difference.

### Limitations

This confirms reproducibility against local `/tmp/saq-run` artifacts. It does
not prove the artifacts can be regenerated on a clean machine without dataset
preparation and compute time.

### Follow-up

The next stable result should audit the promotion/reject/abstain decisions row
by row and document why each policy decision follows from scorer/applicability
signals rather than held-out query tuning.

## Result 2026-07-07: Clean-table decisions match the implemented fixed policy

### Claim

The 10 rows in the checked-in clean validation table are consistent with the
implemented fixed-policy decision path.

### Evidence

- Source table: `docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv`
- Audit doc: `docs/saq_fixed_policy_decision_audit_2026_07_07.md`
- Source artifacts:

  ```text
  /tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
  /tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
  ```

- Code paths:
  - `script/run_default_neighborhood_cross_dataset.py` for conservative,
    frontier-like, risky fallback, and no-candidate selection roles.
  - `script/score_default_neighborhood_plans.py` and
    `script/sweep_data_boundary_pairs.py` for conservative guard thresholds.
  - `script/report_fixed_policy_validation.py` for promote/reject/abstain
    mapping.

### Interpretation

The table decomposes cleanly into four policy cases:

```text
GIST positives: conservative promotion
CIFAR positives: narrow frontier-like promotion
DEEP controls: risky fallback diagnostic mapped to reject
audio/word2vec: no-candidate abstention
```

No row requires held-out query labels for candidate selection. Held-out queries
enter only in final safe-searcher recall/QPS evaluation.

### Limitations

The report driver trusts stored `selection_reason` fields rather than
recomputing policy eligibility, and the frontier-like fallback remains empirical
with CIFAR as the current positive evidence.

### Follow-up

The next useful robustness check is B2/B3: explicitly document the GIST B=5
false-positive resistance and the frontier-like fallback boundary.

## Update Template

When adding a stable result, use this format:

```md
## Result YYYY-MM-DD: <short title>

### Claim

### Evidence
- Dataset / K / B:
- Plan:
- Metric:
- nprobe / top-k:
- Searcher mode:
- Command:
- Artifact path:

### Interpretation

### Limitations

### Follow-up
```

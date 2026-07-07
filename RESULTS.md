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

## Recommended Next Stable Results To Seek

1. Reproduce the checked-in clean validation table from scripts.
2. Make the fixed-policy matrix reproducible or document missing artifacts precisely.
3. Add a concise meeting/paper-facing summary of the fixed-policy method.
4. Add a more explicit applicability classifier/table.
5. Preserve DEEP reject and audio/word2vec abstention behavior under any future generator/scorer change.

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

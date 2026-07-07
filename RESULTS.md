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

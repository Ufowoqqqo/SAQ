# SAQ Fixed-Policy Scorer Calibration Evaluation

Date: 2026-07-07

This report evaluates whether cheaper data-only scorer sampling settings preserve the fixed-policy decisions.

## Scope

- Candidate sets are fixed from the existing default-neighborhood matrix.
- No index is built and no held-out query labels are used for selection.
- `risky_fallback_best_score` is mapped to `reject`, following the fixed-policy interpretation.

## Decision Stability

| preset | runs | decision matches | plan matches | total runtime s |
|---|---:|---:|---:|---:|
| a1024_p2 | 10 | 10/10 | 10/10 | 456.967 |

## Per-Run Results

| run | preset | decision | baseline | selected plan | plan match | pairs | pair ratio | runtime s | runtime ratio |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| gist_full_K4096_B3 | a1024_p2 | promote | promote | `64:8,320:5,320:2,256:0` | True | 2048 | 0.139 | 138.421 | 0.954 |
| gist_full_K4096_B4 | a1024_p2 | promote | promote | `128:9,320:5,320:3,192:0` | True | 2048 | 0.139 | 141.725 | 0.942 |
| gist_full_K4096_B5 | a1024_p2 | promote | promote | `128:9,128:7,320:5,320:3,64:0` | True | 2048 | 0.139 | 140.830 | 0.943 |
| cifar60k_B3 | a1024_p2 | promote | promote | `128:6,64:4,192:2,128:0` | True | 534 | 0.500 | 8.243 | 0.976 |
| cifar60k_B4 | a1024_p2 | promote | promote | `128:7,256:4,128:0` | True | 534 | 0.500 | 8.284 | 0.974 |
| cifar60k_B5 | a1024_p2 | promote | promote | `128:8,64:6,256:4,64:0` | True | 534 | 0.500 | 8.234 | 0.979 |
| deep1M_sample100k_B4 | a1024_p2 | reject | reject | `128:4,128:3` | True | 952 | 0.500 | 5.584 | 0.978 |
| deep1M_sample100k_B5 | a1024_p2 | reject | reject | `128:5,128:4` | True | 952 | 0.500 | 5.646 | 0.983 |
| audio_K4096_B4 | a1024_p2 | abstain | abstain | `` | True |  |  | 0.000 |  |
| word2vec_sample100k_B4 | a1024_p2 | abstain | abstain | `` | True |  |  | 0.000 |  |

## Interpretation

A useful cheap scorer should preserve the promote/reject/abstain decision and preferably the selected plan. If decision stability fails, the sampling setting is too aggressive for the current policy.

The current stable calibration point is `a1024_p2`: it preserves every fixed-policy decision and selected plan in the checked matrix. Smaller representative settings can preserve the decision while changing the GIST B=4 selected plan, so they are not stable enough for exact-plan reproduction.

Pair-count reduction alone does not fully solve scorer overhead. In the full matrix, `a1024_p2` reduces GIST sampling from 14,740 pairs to 2,048 pairs, but scorer runtime remains close to the full scorer. This indicates that the next cost-reduction target should be cached residual/tail features or a smaller scoring grid, not only fewer sampled pairs.

## Output Tables

```text
docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.csv
docs/saq_fixed_policy_scorer_calibration_full_a1024p2_2026_07_07.json
```

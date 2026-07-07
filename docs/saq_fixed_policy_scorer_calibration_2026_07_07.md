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
| a256_p1 | 4 | 4/4 | 3/4 | 153.231 |
| a512_p1 | 4 | 4/4 | 3/4 | 153.903 |
| a1024_p2 | 4 | 4/4 | 4/4 | 155.200 |

## Per-Run Results

| run | preset | decision | baseline | selected plan | plan match | pairs | pair ratio | runtime s | runtime ratio |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| gist_full_K4096_B4 | a256_p1 | promote | promote | `64:10,320:6,384:3,192:0` | False | 256 | 0.017 | 139.512 | 0.928 |
| gist_full_K4096_B4 | a512_p1 | promote | promote | `64:10,320:6,384:3,192:0` | False | 512 | 0.035 | 140.142 | 0.932 |
| gist_full_K4096_B4 | a1024_p2 | promote | promote | `128:9,320:5,320:3,192:0` | True | 2048 | 0.139 | 141.385 | 0.940 |
| cifar60k_B4 | a256_p1 | promote | promote | `128:7,256:4,128:0` | True | 256 | 0.240 | 8.323 | 0.978 |
| cifar60k_B4 | a512_p1 | promote | promote | `128:7,256:4,128:0` | True | 267 | 0.250 | 8.278 | 0.973 |
| cifar60k_B4 | a1024_p2 | promote | promote | `128:7,256:4,128:0` | True | 534 | 0.500 | 8.268 | 0.972 |
| deep1M_sample100k_B4 | a256_p1 | reject | reject | `128:4,128:3` | True | 256 | 0.134 | 5.397 | 0.945 |
| deep1M_sample100k_B4 | a512_p1 | reject | reject | `128:4,128:3` | True | 476 | 0.250 | 5.483 | 0.961 |
| deep1M_sample100k_B4 | a1024_p2 | reject | reject | `128:4,128:3` | True | 952 | 0.500 | 5.547 | 0.972 |
| audio_K4096_B4 | a256_p1 | abstain | abstain | `` | True |  |  | 0.000 |  |
| audio_K4096_B4 | a512_p1 | abstain | abstain | `` | True |  |  | 0.000 |  |
| audio_K4096_B4 | a1024_p2 | abstain | abstain | `` | True |  |  | 0.000 |  |

## Interpretation

A useful cheap scorer should preserve the promote/reject/abstain decision and preferably the selected plan. If decision stability fails, the sampling setting is too aggressive for the current policy.

The current stable calibration point is `a1024_p2`: it preserves every fixed-policy decision and selected plan in the checked matrix. Smaller representative settings can preserve the decision while changing the GIST B=4 selected plan, so they are not stable enough for exact-plan reproduction.

Pair-count reduction alone does not fully solve scorer overhead. In the full matrix, `a1024_p2` reduces GIST sampling from 14,740 pairs to 2,048 pairs, but scorer runtime remains close to the full scorer. This indicates that the next cost-reduction target should be cached residual/tail features or a smaller scoring grid, not only fewer sampled pairs.

## Output Tables

```text
docs/saq_fixed_policy_scorer_calibration_2026_07_07.csv
docs/saq_fixed_policy_scorer_calibration_2026_07_07.json
```

# SAQ Fixed-Policy Metric Audit

Date: 2026-07-07

This note audits whether the current fixed-policy evidence is exposed with
enough metric, top-k, nprobe, and QPS context to avoid misleading headline
claims.

## 1. Current Headline Metrics

Source:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
```

Metric convention:

| dataset family | metric | headline nprobe | reason |
|---|---|---:|---|
| GIST full K4096 | R@100 | 800 | high-recall full-GIST validation |
| DEEP100K sample | R@100 | 200 | sample holdout/control setting |
| audio | R@100 | n/a | abstain |
| word2vec100K sample | R@100 | n/a | abstain |
| CIFAR60K | R@10 | 200 | smaller top-k benchmark used in the CIFAR pipeline |

QPS is reported at the same headline nprobe for each measured run:

```text
GIST: np800
CIFAR: np200
DEEP: np200
```

All measured recall/QPS claims must use:

```text
-searcher_safe_block_min_mode=2
```

## 2. Recall Across Measured Nprobe Values

The matrix summary preserves multiple recall nprobe columns. The clean table
shows one headline nprobe, but the broader recall behavior is:

| run | measured nprobes | recall delta pattern |
|---|---|---|
| GIST B=3 | 50, 100, 200, 400, 800 | positive at all measured nprobes |
| GIST B=4 | 50, 100, 200, 400, 800 | positive at all measured nprobes |
| GIST B=5 | 50, 100, 200, 400, 800 | positive at all measured nprobes |
| CIFAR B=3 | 50, 100, 200, 400 | positive at all measured nprobes |
| CIFAR B=4 | 50, 100, 200, 400 | negative at np50, positive at np100/200/400 |
| CIFAR B=5 | 50, 100, 200, 400 | positive at all measured nprobes |
| DEEP B=4 | 50, 100, 200, 400 | negative at all measured nprobes |
| DEEP B=5 | 50, 100, 200, 400 | negative at all measured nprobes |

The main caveat is CIFAR B=4:

```text
np50  delta = -0.0006
np100 delta = +0.0001
np200 delta = +0.0004
np400 delta = +0.0007
```

So CIFAR B=4 should be described as a small frontier-like positive at the
headline/medium-to-high nprobe setting, not as uniformly positive at every
measured nprobe.

## 3. QPS Reporting Boundary

Current QPS evidence is headline-nprobe only:

| run family | QPS nprobe | implication |
|---|---:|---|
| GIST | 800 | validates speed at the same high-recall nprobe used for headline recall |
| CIFAR | 200 | validates speed at the same headline nprobe used for the clean table |
| DEEP | 200 | validates that speed-only candidates are faster but recall-negative |

This is acceptable for a meeting summary, but it is weaker than a full QPS
curve. For a paper-style claim, the next stronger check is:

```text
report QPS at multiple nprobe values, or state explicitly that QPS is measured
only at the headline operating point.
```

## 4. Cherry-Picking Risk Assessment

| claim type | current risk | reason |
|---|---|---|
| GIST positive recall | low | all measured recall nprobes are positive for B=3/4/5 |
| CIFAR positive recall | medium | B=3/B=5 are all-positive; B=4 has one low-nprobe negative delta |
| DEEP reject/control | low | all measured recall nprobes are negative for B=4/B=5 despite QPS gains |
| audio/word2vec abstention | low | no measured custom plan is claimed |
| QPS improvement | medium | QPS is measured at one headline nprobe per run |
| practical significance | medium | several recall deltas are small, so the stronger story is recall preservation plus QPS gain |

## 5. Recommended Wording

Safe meeting wording:

```text
On GIST and CIFAR, the fixed-policy candidates preserve or slightly improve
recall at the headline operating point while improving QPS. GIST is positive
across all measured recall nprobes; CIFAR is mostly positive, with one low-nprobe
B=4 exception. DEEP demonstrates the reject case: faster plans can be recall
negative and should not be promoted.
```

Avoid:

```text
The policy universally improves recall across every nprobe and dataset.
```

Also avoid:

```text
QPS gains are fully characterized across the operating curve.
```

The current evidence supports headline-operating-point QPS gains, not full QPS
curves.

## 6. Follow-Up For Paper-Ready Evidence

1. Add a compact recall-delta-by-nprobe table to the method spec or appendix.
2. Add multi-nprobe QPS measurements for promoted GIST/CIFAR plans if the paper
   story depends on speed, not just recall preservation.
3. Keep DEEP B=4/B=5 in the table as explicit reject cases.
4. Mark CIFAR B=4 as frontier-like and small-positive, not conservative.
5. Continue reporting metric, top-k, nprobe, plan, and safe-searcher mode for
   every measured row.

# SAQ base-trained joint-objective viability result

Date: 2026-08-04

## Decision

`JOINT_LOCAL_NO_GO`

Base-trained joint selection over the frozen one-coordinate CAQ neighborhood
does not generalize across the two base-direction folds.  Relative to the
identical-alternative independent control, held-out estimator MSE changes by
`+0.0805%` in one cross-fit direction and `-1.3644%` in the other.  Joint
selection improves only 15/32 and 13/32 target vectors, below the frozen 60%
line in both folds and far below the required 5% aggregate reduction.

The same evaluation directions admit a post-hoc local joint oracle improvement
of about 16%.  This shows that alternative codes exist after seeing the
workload, but the selected interaction is unstable across disjoint base
directions.  It is evidence of workload overfitting, not a learnable frozen
joint mechanism.

Do not enlarge the neighborhood, change direction folds, lower the threshold,
or implement a production consumer to rescue this result.  The workload-
coupling lead is closed under the frozen local test.  This does not prove that
every estimator-aware quantizer is impossible; it rejects this direct
continuation of the segment-1/segment-2 oracle.

## Frozen design

The run used the accepted GIST sample50k SAQ index and the prior deterministic
population.  The first and second 128 base probes formed two cross-fit
direction folds; the first 32 disjoint pool rows were targets.  For each target
and each of `192d@6b` and `320d@4b`, the alternatives were exactly:

```text
stored production code
every legal one-coordinate -1 code move
every legal one-coordinate +1 code move
```

Every alternative used the current analytical CAQ rescale
`||x||^2/<x,z>`.  No fitted rescale, extra metadata, bit/boundary change,
query result, ground truth, or other dataset was used.

The target-specific alternative counts were 380--384 for segment 1 and
628--640 for segment 2, giving 241,152--245,760 Cartesian pairs per target and
7,814,431 pairs over all 32 targets in each cross-fit direction.

## Correctness boundary

Before outcomes, the existing parity and the new production-alternative parity
passed:

| check | maximum relative error | limit |
| --- | ---: | ---: |
| stored vs recomposed production estimator | 0 | `1e-5` |
| stored vs decoded-code rescale | `7.10e-8` | `1e-5` |
| stored vs recomputed residual norm | `1.47e-7` | `1e-5` |
| exact segment sum vs full exact distance | `7.92e-15` | `1e-9` |
| analytical production alternative vs stored contribution | `3.08e-8` | `1e-5` |

The focused unit test covers a two-alternative cross-term witness where
independent deterministic selection differs from the exact joint selection.
Release build and tests passed.  An AddressSanitizer build, unit test, and
`objective-parity-v1` execution passed with leak detection disabled because
LeakSanitizer explicitly cannot operate under the sandbox's ptrace mechanism.
UBSan configuration was unavailable because the host linker could not find
`/usr/lib64/libubsan.so.1.0.0`.

The first parity attempt terminated before objective selection because a
stored row vector was subtracted from a column residual without an explicit
transpose.  The one-line shape correction was rebuilt and tested; a fresh
parity directory then passed.  The failed directory contains no objective
outcome.

## Cross-fit result

| train fold | evaluation fold | PROD MSE | IND MSE | JOINT MSE | joint vs independent | targets improved | choices differ | evaluation oracle vs independent |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | `3.68685e-6` | `3.70364e-6` | `3.70066e-6` | `+0.0805%` | 15/32 | 31/32 | `+16.8327%` |
| 1 | 0 | `3.97743e-6` | `3.97516e-6` | `4.02939e-6` | `-1.3644%` | 13/32 | 29/32 | `+15.9200%` |

`IND_TRAIN` itself is essentially tied with production: it is 0.4555% worse
in the first direction and 0.0572% better in the second.  Thus the negative
joint result is not hiding a strong stable segment-local estimator-aware gain.

Joint and independent training choose different pairs for 90.6%--96.9% of
targets, yet this large decision change produces no stable held-out benefit.
The training cross terms also change substantially when evaluated on the
opposite fold.  Together with the evaluation-oracle gap, this is the signature
of selecting fold-specific cancellation rather than learning a persistent
cross-segment rule.

An independent `awk` aggregation of all 64 per-target cross-fit rows reproduced
the recorded losses, relative reductions, improved counts, differing-choice
counts, and pair totals exactly.

## Deterministic reproduction

The primary and unchanged reproduction have byte-identical scientific files:

```text
population.tsv          d1b9b9b658457939c895da722f62b3c8a9de3661a2bea65473ee64d27ef66ce4
parity.tsv              8980a152d4feb104a5383c8f65ae5254a1989902f7e4818fc5f1165ffb76ee50
objective_parity.tsv    164335798cf2cd98d31ee38dacf5eb9ce94a15811410b7d67a34ef2b5648e458
objective_per_target.tsv 8421a72f3818bebc60f0f2758cc1e0418e9b9b2ae59742d4597c1eebe281a178
objective_summary.tsv   10d44f914f4588b844330102cc37dd90c44abd78514fb32211bbd6c31c0df5c0
decision.txt            12bddb4b531940e68aaa0a816fc929d0be87ef11092ea1df679367c6235b2fe7
```

Generated outputs remain under `/tmp/saq-joint-objective-v1-primary/` and
`/tmp/saq-joint-objective-v1-repro/` and are not committed.

## Resources and claim boundary

The primary run used 4.046 CPU seconds, 4.057 wall seconds, and 268,357,632
bytes peak RSS.  The unchanged reproduction used 3.972 CPU seconds, 3.986 wall
seconds, and 268,201,984 bytes peak RSS.  Each output directory is below
0.2 MiB.  The experiment stayed far below the 2 CPU-hour, 1 wall-hour, 4 GiB,
and 10 MiB limits.

The runner is `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`.  Its scientific hot path is
alternative projection followed by exact Cartesian training-loss evaluation;
file output and provenance are outside that selection loop.  The measured
seconds describe only 32 diagnostic targets and cannot be extrapolated as an
affordable full-index encoder.  There is no Recall/QPS or SOTA comparison:
`PERFORMANCE_NOT_YET_MEASURED`.

No benchmark query, ground truth, or query-result table was read.  The result
does not reverse the earlier exact-replacement oracle; it explains why its
ranking interaction does not currently yield a stable base-trained method.

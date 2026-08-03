# SAQ component-wise base-only oracle diagnostic result

Date: 2026-08-03

## Decision

`CLOSE_NO_ACTIONABLE_COMPONENT`

No single frozen estimator component meets the predeclared rule of reducing
pairwise inversion rate by at least 0.002 and repairing at least 20% of
production inversions in both 128-probe folds.  Do not design a
component-specific method from this result.

This closes only the tested localization: the GIST sample50k index, frozen
five-segment plan, accurate estimator, deterministic base-neighbour
population, and stated thresholds.  It is not benchmark-query Recall evidence
and does not rule out diffuse or differently formulated SAQ limitations.

## Correctness gate

The full diagnostic was not run until a separate `parity-v1` execution
returned PASS.  On 32 probes by 4,096 candidates:

| check | maximum relative error | limit | result |
| --- | ---: | ---: | --- |
| stored estimator vs independently recomposed production path | 0 | 1e-5 | PASS |
| stored rescale vs decoded-code/base-residual recomputation | 7.10e-8 | 1e-5 | PASS |
| stored residual norm vs base/index recomputation | 1.47e-7 | 1e-5 | PASS |
| exact segment sum vs exact 960d distance | 7.92e-15 | 1e-9 | PASS |

The focused three-cluster unequal-size index test also passed a byte-identical
load/save round trip.  It validates the minimal `IVF::load()` loop repair; that
repair is artifact correctness work, not scientific evidence.

Before any outcome metric was generated, two test-only parity attempts did
their job and failed.  Re-encoding from the current source did not exactly
reproduce the persisted artifact (maximum rescale relative difference
`8.89e-4`), so the runner was corrected to decode the stored code.  A direct
decoded-vector dot product then differed from the production estimator by up
to `3.89e-5` because the latter reconstructs the MSB term through its
quantized LUT.  The final gate therefore independently recomposes that actual
stored production path, while the decoded code separately validates rescale.
No inversion, repair, or top-10 outcome existed or was inspected during these
repairs, and no frozen scientific threshold was changed.

## Primary result

Production inversion rates are 0.005980 in fold 0 and 0.005775 in fold 1.
There is measurable aggregate headroom, but no sufficiently large localized
component.

| arm | fold 0 absolute reduction | fold 1 absolute reduction | combined repair fraction | interpretation |
| --- | ---: | ---: | ---: | --- |
| `LS_ALL` | 0.000101 | 0.000085 | 9.03% | rescale replacement is too small |
| `EXACT_SEG_0` (64d@11b) | 0.000085 | 0.000027 | 4.09% | negligible high-bit component |
| `EXACT_SEG_1` (192d@6b) | 0.001457 | 0.001527 | 44.28% | strongest component, below 0.002 in both folds |
| `EXACT_SEG_2` (320d@4b) | 0.001337 | 0.001496 | 43.09% | second strongest, below 0.002 in both folds |
| `EXACT_SEG_3` (256d@2b) | 0.000446 | 0.000341 | 21.07% | repairs enough proportionally but not absolutely |
| `EXACT_SEG_4` (128d@0b) | 0.000159 | 0.000140 | 11.90% | omitted dimensions are not dominant |

`EXACT_ALL` removes all inversions by construction, showing that the remaining
error is diffuse across components.  In contrast, least-squares rescaling of
individual segments changes the combined inversion rate by at most about
0.000070 in the beneficial direction and sometimes worsens it.  The evidence
therefore does not support rescale as the localized cause.

Secondary values are consistent with the same reading.  Production local
top-10 agreement is 0.9906/0.9938 across folds.  Exact replacement of segment
1 raises it to 0.9953 in both folds, but this upper bound still fails the
frozen primary decision rule.

## Reproduction and resources

The primary run used 1.979 CPU seconds, 1.987 wall seconds, and 267,194,368
bytes peak RSS.  Its output occupies 274,993 bytes.  The unchanged reproduction
used 1.959 CPU seconds and 1.969 wall seconds.  Population, parity, summary,
decision, and per-probe files were byte-identical between runs.

Primary hashes:

```text
population.tsv d1b9b9b658457939c895da722f62b3c8a9de3661a2bea65473ee64d27ef66ce4
parity.tsv     8980a152d4feb104a5383c8f65ae5254a1989902f7e4818fc5f1165ffb76ee50
summary.tsv    1449165f39f930159cdb9706c2d3881a872a62211121ebf8d9b9a0a2b65563a0
decision.txt   1ef4e909a816bf12a366ffcf4a9e4ffa9372fad7b86a1621409cf5d0b20ee3f7
per_probe.tsv  2389d6db958335a2529210d98105dde592b8155b8646298c3e78b0d441923adf
```

Outputs remain local under `/tmp/saq-component-oracle-v1/`; no generated
dataset, index, binary, or raw result table is added to Git.

## Claim and next-step boundary

This is a limitation-localization negative result, not a performance or SOTA
comparison.  The runner is `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`; its offline
hot path is exact pool-distance construction and per-component scoring, with
file output outside the scored arithmetic.  There is no fair-comparison delta
against a frozen SOTA baseline: `PERFORMANCE_NOT_YET_MEASURED`.

Any continuation would have to change the scientific question from a single
component to a joint/diffuse mechanism or a different population.  That change
is not implied or authorized by this diagnostic.

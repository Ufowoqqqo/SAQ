# SAQ joint-component base-only oracle diagnostic result

Date: 2026-08-03

## Decision

`PAIR_ACTIONABLE`

The unique passing two-segment exact-replacement arm is
`EXACT_SEGS_1_2`, jointly replacing the frozen `192d@6b` and `320d@4b`
segments.  It passes the predeclared absolute inversion-rate reduction of
`0.002` and 20% repair rule in both 128-probe folds.

This identifies a small joint source of headroom.  It does not show that an
implementable encoder, bit allocation, or estimator can realize the exact
replacement, and it is not benchmark-query Recall or performance evidence.

## Frozen scope and correctness

The run reused the prior diagnostic's GIST sample50k index, base-only
population, candidate pool, exact-nearest 64 evaluation set, two folds, and
thresholds.  It exhaustively reported all 10 pairs, 10 triples, and 5
four-segment proper subsets; there was no outcome-selected subset.

Before joint outcomes were generated, an independent `parity-v1` execution
passed all frozen checks over 131,072 probe-candidate comparisons:

| check | maximum relative error | limit |
| --- | ---: | ---: |
| stored vs recomposed production estimator | 0 | 1e-5 |
| stored vs decoded-code rescale | 7.10e-8 | 1e-5 |
| stored vs recomputed residual norm | 1.47e-7 | 1e-5 |
| exact segment sum vs exact full distance | 7.92e-15 | 1e-9 |

## Pair result

| fold | production inversion rate | segments 1+2 rate | absolute reduction | repaired production inversions | new inversion fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.005980 | 0.002628 | 0.003353 | 71.10% | 0.0905% |
| 1 | 0.005775 | 0.002221 | 0.003554 | 75.57% | 0.0815% |
| combined | 0.005878 | 0.002424 | 0.003453 | 73.29% | 0.0860% |

The other nine pairs fail the both-fold rule.  The nearest are segments 1+3
and 2+3: their combined reductions are `0.002008` and `0.001926`, but each
misses `0.002` in at least one fold.  Thus the positive decision is specific
to the two medium-bit segments rather than a generic benefit from replacing
any two segments.

The joint reduction for segments 1+2 is also larger than the sum of their
single-segment inversion-rate reductions by about `0.000558` in fold 0 and
`0.000531` in fold 1.  This is a ranking-interaction observation, not proof of
an algorithmic synergy: pairwise inversions are nonlinear and exact
substitution changes both repaired and newly introduced inversions.

Six triples and all five four-segment subsets also pass, but the minimum
passing cardinality is two, so they do not control the decision.  `EXACT_ALL`
remains a correctness boundary and is excluded from the gate.

## Reproduction and resources

The final primary run used 1.916 CPU seconds, 1.926 wall seconds, 271,122,432
bytes peak RSS, and 445,298 bytes of output.  The unchanged reproduction used
1.971 CPU seconds and 1.980 wall seconds.  Population, parity, summary, decision,
and per-probe outputs were byte-identical.

```text
population.tsv d1b9b9b658457939c895da722f62b3c8a9de3661a2bea65473ee64d27ef66ce4
parity.tsv     8980a152d4feb104a5383c8f65ae5254a1989902f7e4818fc5f1165ffb76ee50
summary.tsv    d2b9d28f8a6b857dc07e1f8af2371ba0e491936afd3529c80e7204ba3d147898
decision.txt   1b8b0d654763d94283740d1f5fae631a455168d6e37f7687c01bb61807b4d128
per_probe.tsv  9196ac5e5345a337eddd5a06b8010976ef6dc4a97118fa1176a2c73d3e2103df
```

Outputs remain under `/tmp/saq-joint-component-oracle-v1/` and are not added
to Git.

## Scientific boundary and next question

This result reopens only a mechanism question: why errors from `192d@6b` and
`320d@4b` interact, and whether a query-unaware, matched-storage mechanism can
reduce both without exact vectors or extra query work.  It does not authorize
changing the global plan, adding per-vector dispatch, or reading benchmark
queries.

Before implementing a method, the closest primary work must be checked for
joint bit allocation, non-uniform product quantization, optimized subspace
decomposition, and estimator-aware encoding.  A proposal must distinguish
itself from reallocating bits between two existing segments or directly
composing known quantizers.

The runner remains `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`; its hot path is the
offline exact pool-distance and subset scoring loop.  There is no SOTA delta:
`PERFORMANCE_NOT_YET_MEASURED`.

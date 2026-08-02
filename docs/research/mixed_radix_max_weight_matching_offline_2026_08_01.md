# Maximum-weight matched mixed-radix offline diagnostic

## Question and boundary

The completed fixed-adjacent mixed-radix method had negligible natural-query
effect.  This diagnostic asks whether the adjacency constraint paired
coordinates with incompatible rate demands and thereby hid the original
arbitrary-cardinality mechanism.

This is a query-unaware, base-only B8/64-byte reconstruction experiment.  It
does not read benchmark queries, ground truth, Recall, or QPS output, does not
build an index, and is not query-performance evidence.

The four frozen cells are SIFT1M and GIST1M with `nlist=1024` and `4096`.  For
each cell, the existing SHA-256 row ordering selects 8,192 PCA learn residuals
for fitting and the next disjoint 8,192 for held-out evaluation.

## Method and controls

For every unordered pair of the 128 coordinates, the existing exact scalar
curves give the best product allocation under one byte:

- arbitrary A: integer `K1,K2` with `K1*K2 <= 256`;
- dyadic D: power-of-two `K1,K2` under the same capacity.

A maximum-weight perfect matching selects 64 disjoint coordinate pairs.  Edge
weight is negative allocation SSE, so A and D each minimize their own total
fit SSE.  The comparison does not maximize `D-A`, which could deliberately
weaken D.

Six reported plans separate the effects:

- `A_adj` and `D_adj`: previous fixed adjacent pairing;
- `A_flex`: A's independently optimized matching and arbitrary radices;
- `D_on_A`: A's matching with dyadic radices;
- `A_on_D`: D's matching with arbitrary radices;
- `D_flex`: D's independently optimized matching and dyadic radices.

NetworkX 3.2.1's Blossom implementation solves the complete graph using
weights normalized to integers at scale `10^12` and `maxcardinality=True`.
The C++ evaluator independently verifies a 64-pair partition and recomputes
the objective from original binary64 SSE values.  The reported conservative
rounding bounds are `4.95e-6`--`5.94e-6` SSE for SIFT and
`1.22e-10`--`1.52e-10` for GIST, negligible relative to the observed gaps.

## Held-out result

Negative values below mean lower SSE for the numerator.

| Dataset | nlist | A-flex vs A-adj | A-flex vs D-on-A | A-flex vs D-flex | D-flex vs D-adj |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT1M | 1,024 | -31.07% | -4.67% | -4.49% | -27.90% |
| SIFT1M | 4,096 | -28.24% | -4.99% | -4.75% | -24.61% |
| GIST1M | 1,024 | -23.40% | -4.16% | -3.98% | -20.38% |
| GIST1M | 4,096 | -20.86% | -4.99% | -4.61% | -17.25% |

The fair A-flex versus independently optimized D-flex comparison is positive
in all four cells.  Fit-set reductions are 5.28%--5.73%; held-out reductions
remain 3.98%--4.75%, so the signal is not confined to the fitting rows.

The matching effect itself is much larger than the radix effect.  A-flex
retains only 0, 0, 1, and 0 of the 64 adjacent pairs across the four cells.
D-flex retains 0, 0, 2, and 3.  The independently optimized A and D matchings
share only 1, 0, 1, and 2 pairs.  D-flex predominantly chooses `16x16` and
`32x8`; A-flex uses non-dyadic allocations in 47--54 of 64 groups, commonly
`23x11`, `21x12`, `28x9`, `17x15`, and `18x14` as well as `32x8`.

The same-matching controls also remain positive.  A beats D by 4.16%--4.99%
on A's matching and by 1.19%--2.30% on D's matching.  Thus the result is not
only a coordinate-reordering improvement, although coordinate matching is the
dominant source of total reconstruction gain.

## Reproduction and resources

The two accepted executions are under:

```text
/tmp/mixed-radix-query/matched-offline-v1/run7
/tmp/mixed-radix-query/matched-offline-v1/run8
```

All scientific outputs, including edge tables and selected matchings, are
byte-identical.  The summary SHA-256 is
`ca34dbbd5966e7ca12054b49cc73d6d46a20152d0227efc964a2b2830f2e40bf`;
the per-pair table SHA-256 is
`83ce9729a579d21feb001b49646bfdc8b5defcfa1b8ea882ece69481b902270e`.

Each accepted execution used about 620 CPU seconds and 621 wall seconds.  Peak
RSS was 428,523,520 bytes in run 7 and 428,843,008 bytes in run 8.  Several
pre-result attempts exposed pathological performance in Boost's dense
weighted matching and were stopped; including them conservatively, total
diagnostic work remained below the 2 CPU-hour and 2 wall-hour limits.

Commands:

```bash
PYTHONPATH=/tmp/saq-networkx \
  python research/mixed_radix_matching/solve_matching.py --self-test
cmake --build /tmp/saq-mixed-radix-query-build -j 12 \
  --target mixed_radix_pair_matching_test mixed_radix_natural_matching
/tmp/saq-mixed-radix-query-build/mixed_radix_pair_matching_test
PYTHONPATH=/tmp/saq-networkx OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  /tmp/saq-mixed-radix-query-build/mixed_radix_natural_matching \
  /tmp/structured-2d-admission \
  /tmp/mixed-radix-query/matched-offline-v1/run7 frozen
```

## Interpretation

Verified: fixed adjacency was a severe reconstruction restriction, and joint
global coordinate matching exposes a stable arbitrary-radix advantage over a
dyadic arm with its own optimized matching.

Not established: lower reconstruction SSE does not imply better Recall; no
packed non-adjacent consumer, index, query timing, PQ/OPQ comparison, or SOTA
frontier result exists.  The large matching gain also overlaps conceptually
with established subspace decomposition and adaptive bit-allocation work.

The smallest justified next experiment is therefore to implement the frozen
coordinate permutation in the existing complete-word consumer and measure a
small direct Recall check for A-flex, D-on-A, D-flex, and the existing
fixed-adjacent/PQ/OPQ controls.  This offline result is strong enough to merit
that check, but not to predict its sign or magnitude.

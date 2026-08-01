# Mixed-radix natural nearest-neighbour collision diagnostic

Date: 2026-08-01

## Question and frozen interpretation

The completed 64-byte A128 method changed 10--24 of 64 adjacent coordinate
pairs from the dyadic `16x16` shape, mostly to `15x17` or `17x15`, but its
Recall difference from D128_FULL was tiny and mixed-sign. This diagnostic asks
whether D collisions that A can split are scarce at the actual top-100 query
boundary.

Before reading collision outcomes, `TASK.md` fixed four cells (SIFT1M/GIST1M,
`nlist={1024,4096}`), all nine prior `nprobe` values, and two witness levels:

1. an **exact full-code witness** is a candidate-present missed ground-truth
   vector and a D-returned false positive with identical complete 64-byte D
   codes but different complete A codes; and
2. a **changed-group witness** is the same pair sharing a D label in at least
   one A/D-different group while A gives them different labels there.

The second definition is intentionally optimistic: every witnessed missed
ground-truth vector is assumed able to replace one false positive. It is an
upper ceiling for this permissive witness definition, not an implementable
ranking rule. The predeclared material line was `+0.002` Recall.

## Correctness and reproduction

The diagnostic loaded the existing A128_B8 and D128_B8 indexes read-only,
verified their one-million ID-to-list assignments were identical, used the
saved PCA queries and ordered IVF lists, and reran both indexes through
`search_mixed_radix_lists`. All 36 A and 36 D Recall values matched the
accepted matrix exactly (`max_abs_error=0`).

Two complete executions produced byte-identical outputs:

```text
summary.tsv  99c1ee1fb16bf4a62096dd310abc915814f986244f700b82165ed5a349a68168
groups.tsv   a5f0125381aba19f3108ced6373c44cae8ee1dc36906147b477319aa3e0f02d2
```

Across the 36 points there were 198,000 query--probe cases and 1,147,139
candidate-present missed-ground-truth instances. The counts repeat queries
across nested probe values and are therefore diagnostic events, not distinct
database vectors.

## Result 1: the synthetic full-code collision mechanism is absent

There were **zero exact full-code witnesses** at every point:

```text
candidate-present D misses examined: 1,147,139
full-code witness misses:             0
queries with a full-code witness:     0
full-code collision ceiling delta:    0 at all 36 points
```

This is the closest natural-data analogue of the synthetic positive example,
where several different prototypes received the same complete D code while A
kept them distinct. That direct mechanism does not occur between a missed true
neighbour and a returned false positive in the frozen SIFT/GIST decision
boundaries.

This does not claim that no two vectors anywhere in the million-vector index
share a code. It is the narrower, query-relevant statement above.

## Result 2: individual-group label sharing is common but non-specific

The permissive changed-group condition was not sparse. It marked 631,030 of
the 1,147,139 candidate-present miss events, across 118,762 query--probe
cases. Its optimistic ceiling exceeded `+0.002` at 34 of 36 points.

At the largest probe value in each cell:

| Dataset | nlist | changed groups | D Recall | candidate ceiling | permissive group ceiling | actual A-D Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT1M | 1,024 | 10 | 0.912471 | 0.999955 | 0.943063 | +0.000066 |
| SIFT1M | 4,096 | 12 | 0.916571 | 0.999990 | 0.945161 | +0.000045 |
| GIST1M | 1,024 | 22 | 0.652800 | 0.999140 | 0.993720 | +0.000089 |
| GIST1M | 4,096 | 24 | 0.658050 | 0.999820 | 0.994390 | -0.000980 |

The broad ceiling is especially close to the IVF candidate ceiling on GIST,
yet the realized A-D difference remains between `-0.00106` and `+0.00054`
over the complete matrix. Sharing one of 256 D labels with any one of roughly
100 false positives, in any of 10--24 changed groups, is combinatorially easy.
The other 63 groups still distinguish the full codes, and a shared label in
one group says neither which candidate should rank first nor whether changing
that group's reconstruction moves the total distance in the correct
direction.

Therefore the changed-group hypothesis as originally worded is false---these
local label-sharing events are abundant---but the permissive witness is too
weak to identify causal Recall headroom. It cannot be used to claim a possible
3--34 percentage-point mixed-radix gain.

## Scientific interpretation

The diagnostic separates three statements:

- **Verified:** the exact full-code collision that explains the synthetic
  positive result has no observed counterpart at the natural top-100 decision
  boundary.
- **Verified:** local D-label sharing that A splits is common, but actual A
  Recall remains tiny and mixed-sign.
- **Inference:** natural failure is not caused by a mechanically blind
  consumer. It is caused by the lack of a query-relevant, directionally
  useful signal in the current reconstruction-driven radix changes.

This preserves the fixed-adjacent natural-data NO-GO. It also means that
simple collision counts are not a sufficient base-only objective. A further
study would need a scientifically distinct, margin- or distance-direction-
aware counterfactual and must confront how to estimate it without benchmark
queries. That work is not part of this diagnostic.

## Commands and resource cost

Build and tiny test:

```bash
cmake -S research/structured_2d \
  -B /tmp/saq-mixed-radix-query-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DFAISS_SOURCE_DIR=/tmp/saq-structured-2d-modeling/third_party/faiss
cmake --build /tmp/saq-mixed-radix-query-build -j 12 \
  --target mixed_radix_collision_diagnostic
/tmp/saq-mixed-radix-query-build/mixed_radix_collision_diagnostic --self-test
```

Each complete run used the same command shape:

```bash
/usr/bin/time -v \
  /tmp/saq-mixed-radix-query-build/mixed_radix_collision_diagnostic \
  /tmp/structured-2d-admission \
  /tmp/structured-2d-admission/pool \
  /tmp/structured-2d-natural/schedule \
  /tmp/structured-2d-admission-data \
  OUTPUT/summary.tsv OUTPUT/groups.tsv
```

Run 1 used 1,472.47 CPU-seconds and 24:36.61 wall time; run 2 used 1,457.83
CPU-seconds and 24:21.92 wall time. Peak RSS was 943,572 KiB and 943,496 KiB.
The combined cost was approximately 0.814 CPU-hours and 0.816 wall-hours,
below the 4/6-hour and 8-GiB limits. This is diagnostic correctness evidence,
not query-performance evidence.

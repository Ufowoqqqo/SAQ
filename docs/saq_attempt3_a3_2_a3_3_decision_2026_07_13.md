# Attempt 3 A3-2/A3-3: DEEP Negative Controls And Decision

Date: 2026-07-13

## Decision

```text
A3-2 DEEP negative controls:       PASS -- BOTH REJECTIONS PRESERVED
A3-3 project decision:             CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE
GO to metric-aware method review: NO
```

Attempt 3 establishes that `1/Ratio@100` changes one frozen GIST operating-point
conclusion while preserving two DEEP negative controls. It does not provide the
two-dataset or two-independent-baseline positive evidence required to review a
new mechanism.

## Frozen Negative Controls

```text
dataset:                  deep1M_sample100k
base vectors:             100,000
queries:                  1,000
dimension:                256
IVF centroids K:          512
top-k:                    100
PCA:                      enabled, full 256 dimensions
threads:                  24
safe block-min mode:      2
variance-bound m:         4
nprobe grid:              {50,100,200,400}
QPS repetitions:          10 per row
```

Plans:

```text
B=4 default:    64x6_192x3
B=4 candidate: 128x4_128x3

B=5 default:    64x7_192x4
B=5 candidate: 128x5_128x4
```

These candidates were historical risky-fallback controls. They were not
selected by the conservative policy; their purpose was to show that fewer or
wider segments can improve QPS while materially damaging retrieval quality.

## B=4 Result

| nprobe | default R@100 | candidate R@100 | default 1/Ratio | candidate 1/Ratio | default QPS | candidate QPS | QPS ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.94550 | 0.92381 | 0.998803057 | 0.998540024 | 68920.5 | 74072.9 | 1.075x |
| 100 | 0.97061 | 0.94401 | 0.999686070 | 0.999416524 | 45165.7 | 49453.2 | 1.095x |
| 200 | 0.97641 | 0.94884 | 0.999904123 | 0.999633936 | 29235.9 | 31299.8 | 1.071x |
| 400 | 0.97713 | 0.94940 | 0.999930322 | 0.999658856 | 17841.2 | 18664.3 | 1.046x |

At the frozen default `nprobe=200` reference:

```text
Recall target:       0.976410000000
1/Ratio target:      0.999904122917
candidate max Recall:     0.949400000000
candidate max 1/Ratio:    0.999658855921
```

The candidate cannot reach either target. At the same `nprobe=200`, its QPS is
`1.071x` higher, but its mean `1/Ratio` delta is `-2.7019e-4`; 97.1% of queries
are worse, with median `-2.5515e-4`, p05 `-5.8486e-4`, and minimum
`-9.6660e-4`.

## B=5 Result

| nprobe | default R@100 | candidate R@100 | default 1/Ratio | candidate 1/Ratio | default QPS | candidate QPS | QPS ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.95180 | 0.94251 | 0.998842845 | 0.998776284 | 67513.4 | 74785.5 | 1.108x |
| 100 | 0.97973 | 0.96687 | 0.999728710 | 0.999659199 | 45246.4 | 49415.9 | 1.092x |
| 200 | 0.98670 | 0.97241 | 0.999948614 | 0.999877534 | 29153.9 | 31404.8 | 1.077x |
| 400 | 0.98752 | 0.97304 | 0.999974940 | 0.999903505 | 18016.0 | 18789.0 | 1.043x |

At the frozen default `nprobe=200` reference:

```text
Recall target:       0.986700000000
1/Ratio target:      0.999948614291
candidate max Recall:     0.973040000000
candidate max 1/Ratio:    0.999903505178
```

The candidate again cannot reach either target. At the same `nprobe=200`, its
QPS is `1.077x` higher, but mean `1/Ratio` delta is `-7.1080e-5`; 87.3% of
queries are worse, with median `-5.8923e-5`, p05 `-2.1641e-4`, and minimum
`-5.7172e-4`.

## Provenance

Index hashes:

```text
B4 default:   51b0c3aa992711cfc3d2d949ab4facf3caa1df7660b53df616a28b79e7edba87
B4 candidate: a8c887ee20b92ffc36037c2c64d88b7cb082b8d4bbcf5b28c678ad792fe57660
B5 default:   6470a1682ade8ed91078cef0e782be01f06573e76a6cdf54d3a06940771c78be
B5 candidate: dc5b56fc6b0153a968595915c032539b9eda0eb14d343230f49c22709e1eb87f
```

The compact artifacts include base/query/ground-truth hashes, all result-ID and
QPS CSV hashes, frontier labels, and paired-query statistics:

```text
docs/saq_attempt3_a3_2_artifacts_2026_07_13/
  deep1M_sample100k_k512_b4.csv
  deep1M_sample100k_k512_b4.json
  deep1M_sample100k_k512_b5.csv
  deep1M_sample100k_k512_b5.json
```

Raw IDs and logs remain under
`/tmp/saq-ratio-a3/deep1M_sample100k/` and are not committed.

## Cross-Dataset Synthesis

| frozen comparison | Recall decision at default np200 target | `1/Ratio` decision | interpretation |
|---|---|---|---|
| GIST sample100k K512 B4 fac-error | reject: target unreachable | accept one measured row: `1.078x` QPS at higher mean distance quality | metric-sensitive boundary |
| DEEP sample100k K512 B4 risky head split | reject: target unreachable | reject: target unreachable | material geometric loss |
| DEEP sample100k K512 B5 risky head split | reject: target unreachable | reject: target unreachable | material geometric loss |

This is more informative than replacing Recall with a uniformly permissive
score. `1/Ratio` distinguishes the small GIST identifier-boundary loss from the
larger DEEP geometric degradation under the frozen reference points.

## A3-3 Gate Evaluation

The predeclared gate required all of the following before a mechanism review:

| condition | outcome |
|---|---|
| at least one prior conclusion changes | pass: GIST reference point |
| change survives a complete operating-point curve | pass for the sampled GIST comparison |
| positive change reproduced on two datasets or two independent baselines | fail: DEEP supplies negative controls, not a second positive |
| query-level tails do not reveal hidden material failures | mixed: GIST marginal tails improve, but 39.6% paired queries worsen |
| a mechanism-level gap remains after related work | fail: no mechanism beyond the old empirical fac-error plan |

The correct decision is therefore:

```text
CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE
```

## What This Does And Does Not Reopen

Supported:

1. report Recall and `1/Ratio` together in future ANN experiments;
2. present the GIST/DEEP contrast as Attempt 3 in the next meeting;
3. reinterpret the old GIST fac-error rejection as metric-dependent; and
4. use exact-hist or lossy-projection outputs as optional diagnostic examples
   if result IDs or exact returned distances already exist.

Not supported:

1. resume fac-error planner sweeps;
2. claim a new metric or a new quantizer;
3. optimize plans on benchmark-query `1/Ratio`;
4. lower `nprobe` and call operating-point selection a contribution;
5. reopen high-overhead CAQ, mixed-plan, graph-prefix, or search-bound methods;
   or
6. create a metric-aware method branch without a new primary-source and
   mechanism review that also covers independent baselines.

The main scientific lesson is that some SAQ plan comparisons are sensitive to
whether quality means exact identifier overlap or geometric equivalence. The
metric paper already owns that general observation. This project currently
adds only a concrete SAQ case study and a negative-control boundary.


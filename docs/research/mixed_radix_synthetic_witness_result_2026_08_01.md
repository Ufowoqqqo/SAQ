# Mixed-radix synthetic mechanism witness

Date: 2026-08-01

## Purpose and claim

This experiment asks whether the existing arbitrary-radix allocator, packed
index, and native complete-word consumer can turn a genuine radix-allocation
advantage into Recall. It is a deterministic mechanism witness, not evidence
that the condition is common in natural data and not a reversal of the
SIFT1M/GIST1M NO-GO.

The positive condition is

```text
K1*K2 <= 2^B
ceil(log2(K1)) + ceil(log2(K2)) > B.
```

An arbitrary-radix word can represent all Cartesian support points under this
condition, while any power-of-two allocation must underrepresent at least one
coordinate.

## Frozen construction

Four cases were fixed before execution:

| Case | Bits | First-pair support | Role |
| --- | ---: | ---: | --- |
| `positive_b4_3x5` | 4 | 3 x 5 | positive witness |
| `null_b4_4x4` | 4 | 4 x 4 | dyadic null control |
| `positive_b8_15x17` | 8 | 15 x 17 | positive witness |
| `null_b8_16x16` | 8 | 16 x 16 | dyadic null control |

Every other adjacent pair uses the corresponding null support. Deterministic
training marginals allocate whole eight-row blocks to each level so that the
existing 1,024-bin rank histogram sees the intended discrete distribution
exactly. No natural dataset, query, ground truth, index, or prior measurement
is read.

For Recall, every first-pair Cartesian prototype has exactly 100 identical
base vectors and one query placed exactly at that prototype. Other coordinates
are fixed. All candidates occupy one shared IVF list, `top-k=100`, and exact
ground truth is the prototype's 100 duplicates. A and D use the same
`search_mixed_radix_lists` table builder and scanner.

No noise, support size, occupancy, top-k, seed, or scenario was changed after
observing results.

## Result

| Scenario | A shape | D shape | A/D prototype-code collisions | A Recall@100 | D Recall@100 |
| --- | ---: | ---: | ---: | ---: | ---: |
| positive B4 | 3 x 5 | 4 x 4 | 0 / 3 | 1.000000 | 0.800000 |
| null B4 | 4 x 4 | 4 x 4 | 0 / 0 | 1.000000 | 1.000000 |
| positive B8 | 15 x 17 | 16 x 16 | 0 / 15 | 1.000000 | 0.941176 |
| null B8 | 16 x 16 | 16 x 16 | 0 / 0 | 1.000000 | 1.000000 |

In both positive cases A's first-pair allocation SSE is exactly zero. D uses
all 16 or 256 nominal states but cannot cover both support cardinalities; its
first-pair allocation SSE is 3271.980440 for B4 and 960.000000 for B8. The
resulting prototype-code collisions directly reduce Recall.

In both null controls A and D have identical shapes, zero SSE, zero collision,
Recall 1.0, and identical top-100 ranking hashes. In both positive cases their
ranking hashes differ. This bidirectional result argues against a generic
implementation or tie-handling artifact.

Two complete executions produced byte-identical TSV files with SHA-256:

```text
2c0d4c8448594b21e23dc2b9e1bf64062e4806434997d9c8c8bc18545b6a929e
```

## Resource cost and commands

The first execution used 612.54 CPU-seconds, 614.00 wall-seconds, and
108,344 KiB peak RSS. The second used 611.65 CPU-seconds, 613.14 wall-seconds,
and 108,036 KiB peak RSS. Total measured execution cost was approximately
0.340 CPU-hours and 0.341 wall-hours, below the 2-hour and 4-GiB limits.

```bash
cmake -S research/structured_2d \
  -B /tmp/saq-mixed-radix-query-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DFAISS_SOURCE_DIR=/tmp/saq-structured-2d-modeling/third_party/faiss
cmake --build /tmp/saq-mixed-radix-query-build -j 12 \
  --target mixed_radix_synthetic_witness mixed_radix_index_test

/usr/bin/time -v \
  /tmp/saq-mixed-radix-query-build/mixed_radix_synthetic_witness \
  /tmp/mixed-radix-query/synthetic-witness-v1/results-run1.tsv
/usr/bin/time -v \
  /tmp/saq-mixed-radix-query-build/mixed_radix_synthetic_witness \
  /tmp/mixed-radix-query/synthetic-witness-v1/results-run2.tsv

cmp /tmp/mixed-radix-query/synthetic-witness-v1/results-run1.tsv \
    /tmp/mixed-radix-query/synthetic-witness-v1/results-run2.tsv
```

## Interpretation and boundary

The result verifies the intended mechanism: mixed radix is strictly useful
when two coordinate cardinalities fit multiplicatively in the word but cross
separate binary rounding boundaries. The unchanged native consumer preserves
that representational difference through Recall.

It also sharpens the natural-data interpretation. At 32 bytes SIFT1M/GIST1M
selected `(4,4)` everywhere; at 64 bytes they mostly selected `(16,16)` and
only weakly deviated to 255-state shapes. Their negative result therefore
does not arise because the implementation is incapable of producing a Recall
gain. The required cardinality mismatch was absent or too weak.

This witness does not establish natural-data prevalence, end-to-end QPS
superiority, or an advantage over PQ/OPQ. An unrestricted PQ/VQ model can
represent this deliberately Cartesian support and may match A. The synthetic
case should be presented as an explanatory positive control, not as a rescued
systems contribution.

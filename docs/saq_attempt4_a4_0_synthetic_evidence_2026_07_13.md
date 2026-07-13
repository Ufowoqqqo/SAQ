# Attempt 4 A4-0 Synthetic Evidence

Date: 2026-07-13
Decision: **PASS_INSTRUMENT_ONLY**

## 1. Scope

This result validates the fixed-rate arbitrary-cardinality formulation and its
offline reference instrument on the source frozen in
`docs/saq_attempt4_a4_0_offline_protocol_2026_07_13.md`. It uses no dataset,
query, ground truth, PCA, IVF, or SAQ index artifact and changes no upstream
SAQ code.

It is not evidence that natural ANN data contain a useful gap, that ANN recall
or QPS improves, or that mixed-radix coding is novel.

## 2. Canonical result

| Quantity | Predeclared value | Observed value | Result |
| --- | ---: | ---: | --- |
| Fixed block capacity | 16 states | 16 states | PASS |
| Arbitrary cardinalities | `(3,5)` | `(3,5)` | PASS |
| Arbitrary used states | 15 | 15 | PASS |
| Arbitrary distortion | 0 | 0 | PASS |
| Dyadic cardinalities | `(4,4)` | `(4,4)` | PASS |
| Dyadic used states | 16 | 16 | PASS |
| Dyadic distortion | 0.1 | 0.1 | PASS |
| Valid mixed-radix addresses | 15 | 15 | PASS |
| Unused four-bit addresses | 1 | 1 | PASS |
| Maximum LUT/direct L2 difference | 0 | 0 | PASS |
| Unrestricted 16-codeword support oracle | 0 | 0 | PASS |

The strict gap is therefore active on the constructed source:

```text
D*_dyadic - D*_arbitrary = 0.1 per vector.
```

This is the expected feasible-set witness. An unrestricted 16-codeword block
VQ also reaches zero, so this example does not show an advantage over block
VQ; it only shows an advantage over a dyadic scalar-product restriction.

## 3. Entropy result

For the selected uniform `(3,5)` product:

| Quantity | Bits |
| --- | ---: |
| Sum of marginal Shannon entropies | 3.9068905956 |
| Separate marginal Huffman expected length | 4.0666666667 |
| Joint 15-symbol Huffman expected length | 3.9333333333 |
| Fixed random-access word | 4 |

For the advisor's explanatory uniform `(3,3)` case, one three-symbol Huffman
code costs `5/3` bits on average, so separate coding costs `10/3` bits on
average. The nine joint states still need four bits in the worst case. The
measurement supports deferring Huffman: any small expected-rate saving must be
weighed against offset/restart metadata and variable decode work.

## 4. Correctness evidence

Seven deterministic tests pass:

1. exact 1D DP versus exhaustive contiguous partitions;
2. duplicate/weighted support semantics;
3. arbitrary allocation versus exhaustive product enumeration;
4. dyadic allocation versus exhaustive product enumeration;
5. all 15 mixed-radix encode/decode tuples;
6. expanded query-LUT versus direct reconstructed squared L2;
7. frozen witness and Huffman values.

The reference DP evaluates interval SSE from weight, value, and squared-value
prefix sums. For support interval `[a,b)`,

```text
SSE(a,b) = sum_sq(a,b) - sum(a,b)^2 / weight(a,b).
```

The scalar recurrence is

```text
DP[k,b] = min_{a in [k-1,b)} DP[k-1,a] + SSE(a,b).
```

The product allocator retains a frontier indexed by used joint states and
minimizes the sum of dimensionwise mean squared errors.

## 5. Complexity and measured work

For `D` dimensions, `H` weighted support points per dimension, scalar limit
`K_max`, group width `r`, and capacity `S=2^B_g`:

```text
scalar curves:  O(D K_max H^2) time, O(K_max H) DP/backtrack memory
allocation:     O(r S K_max) time, O(r S) reference frontier memory
query LUT:      O(S r) time and O(S) entries
database scan:  one lookup per fixed B_g-bit group word
```

Canonical command environment:

```text
Python 3.9.25
Linux 5.14.0-687.15.1.el9_8.x86_64
wall time: 0.03 s
maximum RSS: 13,824 KiB
```

These timings only characterize the tiny validator and must not be used as an
index-construction overhead claim.

## 6. Reproduction

```bash
python -m py_compile script/evaluate_arbitrary_cardinality.py \
  tests/test_evaluate_arbitrary_cardinality.py
python -m unittest discover -s tests -p 'test_*.py' -v
python script/evaluate_arbitrary_cardinality.py synthetic-witness \
  --output docs/saq_attempt4_a4_0_artifacts_2026_07_13/synthetic_witness.json
```

Canonical artifact:

```text
docs/saq_attempt4_a4_0_artifacts_2026_07_13/synthetic_witness.json
SHA-256 0a5db67e1478d6c6ce1ac8c8030f0f90ec2402d5db786f7a4de973cb6baf5326
```

## 7. Decision

A4-0 passes as instrument validation. The next admissible step is a separately
frozen, query-unaware base-data feasibility study that measures dyadic loss
under fixed 4/8-bit groups and includes an unrestricted block-VQ reference.
No SAQ index-format or search-path implementation is authorized by this
result.

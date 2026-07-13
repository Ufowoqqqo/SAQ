# Attempt 4 A4-0 Frozen Offline Protocol

Date frozen: 2026-07-13
Scope: synthetic correctness and formulation activity only

## Inputs

No dataset, benchmark query, ground truth, PCA matrix, IVF assignment, or SAQ
index may be read. The only scientific input is the fixed discrete source:

```text
dimension 0: values [-1, 0, 1], weights [1, 1, 1]
dimension 1: values [-2, -1, 0, 1, 2], weights [1, 1, 1, 1, 1]
block bits: 4
```

All computations use Python binary64 values. There is no seed and no fitted
threshold.

## Instruments

`script/evaluate_arbitrary_cardinality.py` must provide:

1. exact weighted 1D L2 dynamic programming for all requested integer `K`;
2. dyadic and arbitrary product-capacity allocation;
3. mixed-radix encoding, decoding, and expanded L2 lookup tables;
4. Shannon entropy and deterministic optimal binary-prefix expected length;
5. canonical JSON output for the frozen witness.

`tests/test_evaluate_arbitrary_cardinality.py` must compare the DP and
allocation outputs with independent exhaustive tiny references and test all
mixed-radix addresses in the frozen witness.

## Predeclared Results

The run passes instrument validation only when:

```text
arbitrary cardinalities = [3,5]
arbitrary used states = 15
arbitrary distortion = 0
dyadic cardinalities = [4,4]
dyadic used states = 16
dyadic distortion = 0.1
unrestricted block support oracle distortion = 0
mixed-radix valid addresses = 15
mixed-radix unused addresses = 1
maximum lookup/direct distance difference = 0
```

For the separate `(3,3)` explanatory source, optimal independent binary-prefix
coding must report expected length `10/3` bits for two factors. This quantity
must not be described as a fixed three-bit code.

## Commands

```bash
python -m py_compile script/evaluate_arbitrary_cardinality.py \
  tests/test_evaluate_arbitrary_cardinality.py
python -m unittest discover -s tests -p 'test_*.py' -v
python script/evaluate_arbitrary_cardinality.py synthetic-witness \
  --output docs/saq_attempt4_a4_0_artifacts_2026_07_13/synthetic_witness.json
git diff --check
```

## Decision Rule

Any mismatch stops Attempt 4 before data access or implementation work.
Exact agreement permits a later, separately frozen base-data feasibility
study; it does not establish novelty, ANN quality, or permission to modify the
SAQ format/search path.

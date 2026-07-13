# TASK.md

## Active Research Question

Test whether a fixed-rate ANN scan block wastes useful code capacity when each
scalar factor is restricted to a power-of-two number of reconstruction levels.
For a group of `r` scalar factors and a `B_g`-bit stored word, compare:

```text
dyadic product code:     K_j in {1, 2, 4, ...}
arbitrary product code:  K_j in {1, 2, 3, ...}
shared fixed-rate budget: product_j K_j <= S = 2^B_g
```

The first candidate representation is fixed-rate mixed radix. Huffman or
other entropy coding is a separate, later model because variable-length codes
change random access, SIMD scan, and worst-case storage.

## Current Decision

`CONDITIONAL_GO_FOR_OFFLINE_FEASIBILITY_ONLY`.

A4-0 is complete with `PASS_INSTRUMENT_ONLY`. All seven deterministic tests
and all frozen witness checks pass. This result authorizes only preparation of
a separately frozen, base-data-only feasibility protocol; that next protocol
has not yet been written or executed. SAQ integration remains unauthorized.

The coding primitive is not novel: entropy-constrained quantization,
transform coding, adaptive product-code bit allocation, mixed scalar level
products, irregular SIMD product quantizers, and fixed-address fractional-rate
vector quantizers are all relevant prior work. A publishable claim would need
to establish an ANN-specific rate-distortion/scan advantage at unchanged
fixed payload and controlled table/build work, not merely show that integer
cardinalities form a larger feasible set than powers of two.

## A4-0: Synthetic And Instrument Stage

This is the only authorized stage now. It must not read benchmark query,
ground-truth, or index artifacts and must not change the SAQ implementation.

1. Freeze the budget semantics and related-work boundary.
2. Implement exact weighted 1D L2 quantization for every integer cardinality
   `K=1..K_max` on a supplied discrete support.
3. Solve the dyadic and arbitrary-cardinality product allocations under the
   same capacity `S=2^B_g`.
4. Validate mixed-radix encode/decode bijection and expanded query-LUT parity.
5. Report Shannon entropy and optimal binary-prefix expected length, without
   treating either as fixed-length savings.
6. Run the frozen two-dimensional synthetic witness and write canonical JSON.

### Frozen Witness

Use two independent, uniformly weighted scalar sources:

```text
x_1 in {-1, 0, 1}               (three atoms)
x_2 in {-2, -1, 0, 1, 2}        (five atoms)
B_g = 4, S = 16 joint states
```

Expected result:

```text
arbitrary optimum: (K_1, K_2) = (3, 5), product 15, distortion 0
dyadic optimum:    (K_1, K_2) = (4, 4), product 16,
                   total mean squared distortion 0.1 per vector
unrestricted 16-codeword block-VQ discrete-support oracle: distortion 0
```

The witness proves only strict inclusion and instrument activity. It does not
establish natural-data prevalence, ANN recall, novelty, or a systems benefit.

## Formal Objective

For dimension `j`, let `E_j(K)` be the minimum expected scalar L2 distortion
using at most `K` reconstruction levels. The fixed-rate factorized objective is

```text
minimize    sum_j E_j(K_j)
subject to  product_j K_j <= 2^B_g.
```

The dyadic baseline adds `K_j = 2^{b_j}` for nonnegative integer `b_j`.
Therefore the arbitrary-cardinality optimum cannot have higher reconstruction
distortion than the dyadic optimum under this exact factorized model. This set
inclusion gives no guarantee for recall, distance-estimation error, or QPS.

## A4-0 Completion Gate

A4-0 completes only if all of the following hold:

- exact 1D DP agrees with exhaustive tiny references;
- dyadic/arbitrary allocation agrees with exhaustive product enumeration;
- all valid mixed-radix tuples encode/decode bijectively;
- lookup-table distances equal direct reconstructed L2 distances;
- the frozen witness returns the predeclared values in Release-independent
  Python float64 arithmetic;
- complexity and all representation costs are stated explicitly.

Passing A4-0 authorizes only writing a separately frozen, base-data-only
feasibility protocol. It does not authorize SAQ integration. Failure closes
the formulation before any dataset work.

## Complexity Boundary

For `D` dimensions, `H` weighted support points per dimension, maximum tested
cardinality `K_max`, group width `r`, and fixed word capacity `S=2^B_g`:

```text
exact scalar curves:       O(D K_max H^2) time, O(K_max H) DP memory
allocation DP:             O(r S K_max) time, O(r S) frontier memory
mixed-radix LUT build:     O(S r) per group and query
fixed-rate database scan:  one table lookup per stored B_g-bit group
```

These are first-stage reference costs, not optimized production bounds.

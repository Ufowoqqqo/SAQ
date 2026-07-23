# Shared-shape full-affine 2D VQ base-only result

Date: 2026-07-23
Branch: `saq-structured-2d-modeling`
Base: `5503e87d0584fe50c9233fbe3a02cdd577db07ea`
Status: `PASS_SHARED_AFFINE_BASE_ONLY`

## Question

A4-OR-B showed that independent two-dimensional vector quantization (V)
improved held-out reconstruction over dyadic scalar allocation (D), while
more flexible scalar allocations did not explain the gap. This experiment
tested whether one reusable non-rectangular two-dimensional shape, adjusted
by one mean and one full 2x2 affine map per coordinate pair, could recover
most of that opportunity.

For group `g` and shared label `k`, the tested center was:

```text
center[g,k] = mean[g] + transform[g] * shared_shape[k]
```

The model used the same fixed 64 adjacent coordinate pairs, B4/B8 labels, one
lookup per group, and unchanged reconstruction and base-pair evaluators as D
and V. It did not add per-vector or per-cell choices.

## Frozen fit

All parameters used fit rows only:

1. compute each two-coordinate group's mean and full covariance;
2. whiten each group and pool all 64 standardized groups;
3. train one deterministic 2D K-means shape with 16 or 256 centers, 300
   iterations and 8 restarts;
4. alternate fixed-assignment least-squares updates of all six per-group
   affine parameters and the shared shape; and
5. reassign to the nearest expanded centers, accepting at most 20
   non-increasing fit-SSE iterations.

The feasibility rule required all four dataset/rate cells to recover at least
70% of the D-to-V held-out reconstruction opportunity, improve at least 48 of
64 groups, recover at least 50% of positive pair-proxy opportunity, and pass
shape, encoding, replay, occupancy, finiteness, and collision checks.

## Results

All D/S/V records passed the final validity checks. For S, every shared label
was occupied in the pooled fit assignment. Per-group unused labels remain an
efficiency diagnostic rather than an encoding failure.

| Dataset | Rate | D held-out SSE | S held-out SSE | V held-out SSE | D-to-V recovery by S | Groups S < D | Pair recovery | Cell |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GIST | B4 | 198.3069 | 178.3937 | 175.6758 | 88.0% | 64/64 | 99.1% | pass |
| GIST | B8 | 18.5473 | 13.8247 | 15.3578 | 148.1% | 64/64 | 125.5% | pass |
| CIFAR | B4 | 89.9049 | 81.5090 | 81.9902 | 106.1% | 64/64 | 108.1% | pass |
| CIFAR | B8 | 7.5634 | 6.0106 | 6.7411 | 188.9% | 64/64 | 130.9% | pass |

All four cells pass the frozen rule. S improves every group relative to D.
It also has lower held-out SSE than independently trained V in GIST B8 and
both CIFAR cells, and lower pair-proxy error than V in those three cells.

The result supports the mechanism-level hypothesis: the D-to-V opportunity is
largely explained by reusable two-dimensional shape plus low-dimensional
group adaptation, rather than requiring 64 unrelated codebooks.

The full-affine correction was decisive at GIST B4. The covariance-only
Cholesky initialization recovered 60.8% of the D-to-V opportunity, while
learning all four linear coefficients raised recovery to 88.0%. Therefore the
rotation/shear alignment left after covariance standardization is part of the
observed mechanism and cannot be omitted from the tested model.

## Cost and representation

| Rate | S compact bytes | V bytes | S as fraction of V | S transient expanded bytes |
| --- | ---: | ---: | ---: | ---: |
| B4 | 1,664 | 8,192 | 20.3% | 8,192 |
| B8 | 3,584 | 131,072 | 2.7% | 131,072 |

The compact representation stores `2*K` shared-shape floats plus six floats
per group. The transient expansion was used only to reuse the unchanged
evaluator and is not persistent model state.

Measured single-thread fitting CPU time, including full-affine refinement:

| Dataset | Rate | S | V | S / V |
| --- | ---: | ---: | ---: | ---: |
| GIST | B4 | 10.39 s | 14.33 s | 0.72x |
| GIST | B8 | 832.75 s | 182.23 s | 4.57x |
| CIFAR | B4 | 9.47 s | 14.48 s | 0.65x |
| CIFAR | B8 | 827.72 s | 146.62 s | 5.65x |

All four S fits accepted the maximum 20 refinement iterations. This means the
frozen fit was still improving at its iteration cap; it is reproducible, but
the current cap is not evidence of numerical convergence.

At B8, the naive pooled trainer is materially slower than independent V
despite the much smaller persistent model. Held-out encoding and table
construction used the same expanded-center evaluator and essentially the same
table-entry count as V. This experiment provides no native compact-table,
scan, or query-speed evidence.

## Correctness checks

Focused tests cover:

- exact affine expansion, including a nonzero upper-right coefficient;
- compact and transient byte accounting;
- shape, encoding replay, collision, and occupancy behavior;
- rejection of a missing pooled label; and
- a synthetic full-affine case where alternating regression learns the
  previously absent coefficient and reduces fit SSE.

An earlier validation incorrectly applied V's per-group occupancy rule to the
shared S labels. The corrected rule checks final pooled occupancy for S and
retains per-group occupancy for V. Per-group unused S labels continue to be
reported.

Build and test:

```bash
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
```

Authoritative full-affine outputs:

- `/tmp/structured-2d-full-affine-gist/summary.tsv`
- `/tmp/structured-2d-full-affine-gist/groups.tsv`
- `/tmp/structured-2d-full-affine-gist/decision.tsv`
- `/tmp/structured-2d-full-affine-cifar/summary.tsv`
- `/tmp/structured-2d-full-affine-cifar/groups.tsv`
- `/tmp/structured-2d-full-affine-cifar/decision.tsv`

SHA-256:

```text
50bfaa57523de5c0395cf899acccb11e7ad8a435960c88db1165e9d9de12e3fe  GIST summary
cdb78846a7d8da287510b364682dd2e4e18b52a63604e4ee6979442962eb66d6  GIST groups
5d23ffe0c9122e48c2a845abc589898545cf4b17370957cbaff8eff2bd95db3a  GIST decision
73b1a7b06b7097bfd279c38d502a379b470cbb6d2ee8686760666fe06c3719f8  CIFAR summary
57e0b4e36e34cba201c41b4fe7d9632b867d78c95aaf5b12cc7c0b60058245a4  CIFAR groups
76c08e917290fe8133f31f7061c060d4cd85541747d9f72cb7d4fcd847cf73eb  CIFAR decision
```

## Claim boundary and next question

The evidence supports a base-only, query-unaware feasibility statement: a
compact shared-shape full-affine 2D model captures at least 88% of the
independent-V held-out opportunity in all four registered cells.

It does not establish Recall, QPS, native compact table-build cost,
unchanged-SAQ compatibility, statistical significance, convergence,
end-to-end affordability, or movement against a SOTA system. The result must
not be presented as a paper contribution by itself.

The cheapest next step is not benchmark-query evaluation. It is a bounded
fit-only convergence and compact-table algebra check:

1. determine whether additional iterations materially change held-out results
   without tuning on held-out data; and
2. derive whether tables can be built directly from the compact shared shape
   and affine maps without persistent center expansion or extra lookups.

Only if that check freezes an affordable representation and fit rule should a
separate query-free native microbenchmark be considered.

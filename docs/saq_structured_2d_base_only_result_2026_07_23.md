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

## Bounded convergence and compact-table follow-up

Follow-up date: 2026-07-23

```text
PASS_COMPACT_TABLE_EQUIVALENCE
PASS_SHARED_AFFINE_BASE_ONLY_RETAINED
CONVERGENCE_UNRESOLVED_AT_100
```

### Frozen convergence rule

The iteration-20 state was retained as `T`. The identical fit-only alternating
updates then continued to at most 100 accepted iterations. Convergence
required three consecutive relative fit-SSE improvements at or below `1e-8`.
Held-out rows were evaluated only after this stopping point was fixed.

No cell converged by iteration 100:

| Dataset | Rate | Fit SSE at 20 | Fit SSE at 100 | Iteration-100 relative improvement | Held-out SSE at 20 | Held-out SSE at 100 | Held-out change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GIST | B4 | 173.2217 | 172.8954 | 2.65e-5 | 178.3937 | 178.4181 | +0.0137% |
| GIST | B8 | 12.5442 | 12.4057 | 3.07e-6 | 13.8247 | 13.8436 | +0.1367% |
| CIFAR | B4 | 80.7703 | 80.7038 | 1.89e-6 | 81.5090 | 81.5081 | -0.0011% |
| CIFAR | B8 | 5.7478 | 5.7141 | 1.18e-5 | 6.0106 | 6.0204 | +0.1633% |

The final relative improvements remain 189--2,984 times larger than the
frozen tolerance. The cap was not extended.

The base-only scientific decision is nevertheless stable: every final cell
still passes the original reconstruction, group-prevalence, pair, and
validity gates. Continuing from 20 to 100 iterations changes held-out SSE by
at most 0.164%. This supports robustness of the feasibility result to the
tested additional fitting, but it does not establish convergence or justify
calling iteration 20 an optimizer fixed point.

### Compact-table equivalence

The candidate constructs each table directly from:

```text
u = q - mean
distance = ||u||^2 - 2 z^T A^T u + z^T A^T A z
```

It computes the query-dependent constant, `A^T u`, and the three unique
entries of `A^T A` once per group, then emits one K-entry float table. It does
not persist or materialize all `64*K` centers. Expanded centers are used only
by the reference side of the check.

| Dataset | Rate | Encoding mismatches | Table violations | Pair violations | Maximum table difference | Maximum pair-error difference | Peak candidate table |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GIST | B4 | 0 | 0 | 0 | 2.38e-7 | 1.18e-7 | 64 B |
| GIST | B8 | 0 | 0 | 0 | 4.77e-7 | 6.42e-8 | 1,024 B |
| CIFAR | B4 | 0 | 0 | 0 | 1.49e-8 | 1.70e-8 | 64 B |
| CIFAR | B8 | 0 | 0 | 0 | 5.96e-8 | 2.59e-8 | 1,024 B |

All compact and reference table-entry counts match exactly: 4,112,384 and
65,798,144 for GIST B4/B8, and 4,057,088 and 64,913,408 for CIFAR B4/B8.
Every entry satisfies the frozen
`8 * float_epsilon * max(1, abs(reference))` tolerance. Every pair difference
is within the sum of the actual lookup tolerances used by that pair.

The full audit check, including compact encoding, reference table comparison,
and pair comparison over the complete panels, used about 0.08 seconds at B4
and 1.21 seconds at B8. These times are not a native hot-path benchmark.

The compact representation therefore remains 1,664 bytes at B4 and 3,584
bytes at B8, with one 64-byte or 1,024-byte working table respectively. The
131,072-byte B8 expanded model is not required by the candidate path.

### Follow-up artifacts

- `/tmp/structured-2d-convergence-gist/summary.tsv`
- `/tmp/structured-2d-convergence-gist/groups.tsv`
- `/tmp/structured-2d-convergence-gist/decision.tsv`
- `/tmp/structured-2d-convergence-gist/convergence_trace.tsv`
- `/tmp/structured-2d-convergence-gist/compact.tsv`
- `/tmp/structured-2d-convergence-cifar/summary.tsv`
- `/tmp/structured-2d-convergence-cifar/groups.tsv`
- `/tmp/structured-2d-convergence-cifar/decision.tsv`
- `/tmp/structured-2d-convergence-cifar/convergence_trace.tsv`
- `/tmp/structured-2d-convergence-cifar/compact.tsv`

SHA-256:

```text
0159b6fbfb4bcc5adddef9f7de85f197300ac12b0e91d21691aca6e1b2b77f47  GIST summary
f5bbef45116dd38b9246e1860f621964a45f509ff90bc4e517fc666fa404097b  GIST groups
dea4a6b2399a029966b0e06ecf5222458807a951161f29c18f8fd05998357d04  GIST decision
fc0bebf01d64c476af803de89d679dad44aaa1a60de429bba88b55b014689836  GIST trace
fbf1a4fe56b3e033c622dfb62baadf5c6ab4a16285dc2b6d3ec1248acb16287d  GIST compact
d996339b3f77b1c8be5651107b630f2c94e307e8d255f290fbe2f004fcf81aa0  CIFAR summary
a6d9ca4a15e1ec4de4c8c24ad80d80783a908974d22a8388d88f1ca5fbdcc9e6  CIFAR groups
7b68b86f094fdf831e0f085f9fc797f947638f59d4d7f0ccced691043d42cec7  CIFAR decision
fb23f4d5be5b3b13a4ff6a5e0f25b212a5f8c194f2b94152d1d7954016e56361  CIFAR trace
4e537e54bce10ca547390c09c3d29e59d34484ed851844a57ac68e7d32b176cb  CIFAR compact
```

### Updated claim boundary

The compact-table algebra is feasible and numerically equivalent under the
frozen checks. The original base-only mechanism result remains positive after
80 additional fit-only iterations.

The fit itself is not converged under the declared rule. Before native
microbenchmarking, the project must choose between:

- defining and justifying a fixed-budget truncated fitter as part of the
  method; or
- improving the optimizer and testing a newly frozen convergence rule.

This follow-up does not authorize either choice, benchmark-query access, or a
production integration.

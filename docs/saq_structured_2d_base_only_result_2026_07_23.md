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

At that checkpoint the follow-up did not itself select either choice or
authorize benchmark-query access or production integration. The subsequent
user decision is recorded below.

## Fixed-budget method decision

Decision date: 2026-07-23

```text
ADOPT_FIXED_BUDGET_100
PASS_COMPACT_TABLE_EQUIVALENCE
PASS_SHARED_AFFINE_BASE_ONLY_RETAINED
NOT_CONVERGED_AT_100
```

The project selects the fixed-budget construction interpretation. S100 is the
primary model; S20 is retained only as a preregistered construction-budget
sensitivity point.

This does not retroactively claim convergence. The method is now defined as
the frozen pooled initialization followed by at most 100 accepted monotonic
full-affine refinement rounds. Early exit is allowed only at the existing
`1e-10` numerical fixed-point safeguard; a non-monotonic numerical stop is a
construction failure.

The choice does not use held-out quality:

- the 100-round cap was frozen before the follow-up outcomes;
- all four S100 models have lower fit SSE than their S20 snapshots;
- all four retain the original scientific gates;
- all four pass compact-table equivalence; and
- no recorded iteration had relative fit improvement at or below `1e-10`.

The last point proves that replacing the follow-up's three-step convergence
test with the fixed-budget rule does not change any recorded update. The
minimum single-round relative improvements across iterations 1--100 are
`5.04e-6`, `3.07e-6`, `1.55e-6`, and `1.18e-5` for GIST B4/B8 and CIFAR B4/B8.
The existing S100 artifacts therefore remain authoritative without rerunning
the registered panels.

### Construction-cost interpretation

The additional rounds from 20 to 100 cost about 3 seconds at B4 and 20 seconds
at B8. Total measured S100 fitting time versus V is:

| Dataset | Rate | S100 fit time | V fit time | S100 / V |
| --- | ---: | ---: | ---: | ---: |
| GIST | B4 | 12.50 s | 13.21 s | 0.95x |
| GIST | B8 | 694.39 s | 166.46 s | 4.17x |
| CIFAR | B4 | 11.76 s | 13.43 s | 0.88x |
| CIFAR | B8 | 695.71 s | 133.80 s | 5.20x |

The fixed budget resolves method ambiguity, not the B8 construction-cost
problem. B8 pooled initialization remains the dominant overhead and must be
included in any later Pareto claim.

### Updated claim

The defensible claim is:

> Under a deterministic 100-round construction budget, the compact
> shared-affine model retains the four-cell base-only feasibility result and
> builds equivalent one-lookup tables without persistent center expansion.

The project must not claim that the non-convex objective converged, that S100
is a local optimum, or that the 100-round budget is universally optimal. A
later paper-facing evaluation must report S20 as construction sensitivity and
the complete S100 build cost.

The next eligible engineering check is a query-free native compact-table
microbenchmark against expanded S100 and V. It requires a separately frozen
cost contract and does not authorize benchmark queries, Recall/QPS, or
production integration.

## Query-free native compact-table microbenchmark

Measurement date: 2026-07-23

```text
PASS_NATIVE_TABLE_CORRECTNESS
PASS_NATIVE_LOOKUP_PARITY
FAIL_NATIVE_TABLE_BUILD_AFFORDABILITY
PROTOTYPE_NOT_PERFORMANCE_EVIDENCE
```

### Frozen boundary

Before observing timing results, the `Frozen native microbenchmark` section
of `TASK.md` froze:

- fit base residuals only; no benchmark queries, ground truth, Recall/QPS, or
  serialized indexes;
- compact S100 (`C`), the identical expanded S100 (`E`), and independent V;
- all 8,192 fit rows, 64 groups, and every table entry for table construction;
- 64 stratum-midpoint fit probes, all 8,192 fit codes, and 64 groups for
  lookup;
- one warmup, nine measured repetitions, and rotating `C/E/V` arm order;
- wall-clock median as the primary comparison, with CPU time and dispersion
  retained; and
- affordability gates of `C/E <= 2.0x` for table construction and no more
  than 10% lookup slowdown.

Training, expansion, encoding, allocation, validation, and output were outside
the timed regions. Each B4 repetition built 8,388,608 table entries; each B8
repetition built 134,217,728. Every arm performed 33,554,432 lookups per
repetition.

The executable was built with GCC 11.5.0, CMake 4.0.3, Release `-O3 -DNDEBUG`,
the local strict floating-point flags in `CMakeLists.txt`, generic Faiss, and
OpenBLAS 0.3.29. Measurements used one process pinned to CPU 0 of an Intel
Core i9-10920X, with OpenMP, OpenBLAS, and MKL thread counts fixed to one.

Exact build and execution commands:

```bash
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release -DFAISS_ENABLE_GPU=OFF \
  -DFAISS_ENABLE_PYTHON=OFF -DFAISS_OPT_LEVEL=generic \
  -DBLA_VENDOR=OpenBLAS \
  -DBLAS_LIBRARIES=/usr/lib64/libopenblaso-r0.3.29.so \
  -DLAPACK_LIBRARIES=/usr/lib64/libopenblaso-r0.3.29.so
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/saq-structured-2d-build/structured_2d_runner \
  gist_sample50k_k512 \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_centroid_512_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_cluster_id_512.ivecs \
  /tmp/a4_or_b_gist_inventory.tsv 50000 960 \
  /tmp/structured-2d-native-gist-9f8df90

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/saq-structured-2d-build/structured_2d_runner \
  cifar60k_k512 \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_base_pca.fvecs \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_centroid_512_pca.fvecs \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_cluster_id_512.ivecs \
  /tmp/a4_or_b_cifar_inventory.tsv 60000 512 \
  /tmp/structured-2d-native-cifar-9f8df90
```

### Correctness

All four dataset/rate cells passed:

- exact table-entry and lookup counts;
- finite build and lookup checksums;
- exact reuse of S codes by C and E; and
- zero compact-versus-expanded table-tolerance violations.

Maximum compact-versus-expanded absolute table differences were `5.96e-8`
and `2.38e-7` for GIST B4/B8, and `1.49e-8` and `2.98e-8` for CIFAR B4/B8.

### Native costs

The table columns below are median wall nanoseconds. Lookup is normalized per
code-indexed table access.

| Dataset | Rate | C build ns/entry | E build ns/entry | V build ns/entry | C/E build | C lookup ns | E lookup ns | V lookup ns | C/E lookup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GIST | B4 | 2.898 | 1.232 | 1.209 | 2.353x | 0.922 | 0.923 | 0.923 | 0.998x |
| GIST | B8 | 2.533 | 0.877 | 0.876 | 2.887x | 0.935 | 0.933 | 0.940 | 1.002x |
| CIFAR | B4 | 2.845 | 1.146 | 1.097 | 2.482x | 0.925 | 0.927 | 0.925 | 0.998x |
| CIFAR | B8 | 2.480 | 0.855 | 0.850 | 2.899x | 0.919 | 0.912 | 0.917 | 1.008x |

The measured median absolute deviations are small: build MAD ranges from
`0.0025` to `0.0093 ns/entry`, and lookup MAD from `0.0013` to
`0.0083 ns/lookup`.

For one 64-group probe, the medians imply roughly:

- B4: compact table construction costs 2.9 microseconds versus 1.1--1.3
  microseconds for E/V; and
- B8: compact table construction costs 40.6--41.5 microseconds versus
  13.9--14.4 microseconds for E/V.

The persistent model sizes remain 1,664 bytes (B4) and 3,584 bytes (B8) for C,
versus 8,192 and 131,072 bytes for E/V. Thus compact S100 exchanges a 4.9x
(B4) or 36.6x (B8) model-size reduction for 2.35--2.90x table-build time in
this native prototype. Once a table exists, lookup cost is indistinguishable
at this resolution because all arms use the same contiguous binary32 layout.

### Decision and claim boundary

The lookup-parity gate passes in all four cells. The table-construction gate
fails in all four: compact construction is consistently slower than the
frozen `2.0x` limit. The likely mechanism is the extra shared-affine polynomial
arithmetic per entry; the present experiment isolates the location of the
overhead but is not a profiler result.

This is a useful negative result. Compact S100 is memory-feasible and
lookup-compatible, but the current native builder is not yet affordable under
the frozen rule. The result does not establish end-to-end QPS, Recall parity,
cache behavior inside production SAQ, or a SOTA Pareto improvement. A later
decision may either profile and optimize this exact builder under a new frozen
scope, quantify amortization in an authorized unchanged-estimator integration,
or stop the direction; this measurement does not choose among them.

Artifacts:

- `/tmp/structured-2d-native-gist-9f8df90/`;
- `/tmp/structured-2d-native-cifar-9f8df90/`.

SHA-256 for the raw, decision, and summary timing files:

```text
0cf1ee98d7ff428906eb5cb8de7e83ca1edcfd13228835b75d9d547b8c3c34b4  GIST raw
3f9b7136931e331210ffe2ad24956dbb62bcb1966fbb193897a27056f7e13ace  GIST decision
e0749661ed6b60c8e8cafe2c25838c32df141a7bc4d419a7a70cfd8a3e6110dc  GIST summary
9f6f4e48df2dd1fcdc026d92a79dfd8696e14abf4d99996b40c6c09f4ca75f0b  CIFAR raw
e953b8fc033299cf4011862cc163ec91669a16de7a2e62f650eb4e9069dff540  CIFAR decision
40d882f4ef475af1c46e057d481d07fc56af3653ace99940e65d75c36e768211  CIFAR summary
```

## Bounded compact-builder hot-path profile

Profiling date: 2026-07-24

```text
BOTTLENECK_IDENTIFIED_SCALAR_COMPACT_LOOP
EXPANDED_LOOP_AUTO_VECTORIZED_SSE
SEMANTICS_PRESERVING_SIMD_OPTIMIZATION_PLAUSIBLE
OPTIMIZATION_NOT_IMPLEMENTED
```

The profile used the unchanged builders at commit `b0d654c`. A deterministic
driver under `/tmp` constructed finite synthetic S models and probes with the
same 8,192-row, 64-group, B4/B8 work counts. It did not read dataset or query
files, retrain a model, modify repository source, or rerun the registered
panels.

### Compiler and assembly evidence

Under the frozen strict flags, GCC 11.5 reports:

- compact's label loop at `compact.cpp:158` is not vectorized because of
  control flow; and
- expanded's loop at `compact.cpp:168` is vectorized with 16-byte vectors.

The assembly identifies the control flow as the per-entry nonnegative clamp.
Compact executes scalar double-precision polynomial operations followed by
`comisd` and a branch for every label. Expanded computes four distances per
loop with packed conversions, subtracts, multiplies, adds, and one packed
store. Branch misses are rare because mathematically valid distances are
normally positive; the cost is scalar execution and instruction volume, not
branch unpredictability.

### Hardware counters

`perf stat -r 5` used CPU 0 on the same Intel i9-10920X. B4 commands performed
three complete workloads per run; B8 commands performed one.

| Rate | Arm | Cycles | Instructions | Branches | Branch miss rate | Elapsed |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B4 | C | 319,141,673 | 924,892,247 | 63,000,762 | 0.07% | 0.0745 s |
| B4 | E | 129,764,096 | 328,801,389 | 23,703,704 | 0.19% | 0.0317 s |
| B8 | C | 1,508,356,863 | 4,222,840,092 | 273,765,407 | 0.20% | 0.3396 s |
| B8 | E | 518,798,583 | 1,192,987,992 | 40,465,251 | 0.08% | 0.1189 s |

Thus compact versus expanded uses `2.46x/2.91x` cycles,
`2.81x/3.54x` instructions, and `2.66x/6.77x` branches at B4/B8. The B8 cycle
ratio directly reproduces the registered `2.89x` builder slowdown.

### Diagnostic headroom

Two compiler variants were used only to distinguish an implementation
bottleneck from an unavoidable formula lower bound:

- `-march=native` with strict semantics still leaves compact scalar while
  vectorizing expanded with 32-byte vectors; B8 C/E worsens to about `4.50x`.
- `-ffast-math` allows GCC to vectorize the unchanged compact loop with
  16-byte vectors; synthetic C/E falls to about `1.56x` at B4 and `1.42x` at
  B8.

The fast-math result is not admissible performance or correctness evidence:
it relaxes NaN, rounding, and related floating-point semantics. It does prove
that the frozen `2.0x` target is not excluded by the polynomial's operation
count alone.

### Decision

The current builder failure is primarily an implementation bottleneck, not a
demonstrated inherent cost of the compact representation. The smallest next
experiment is an explicit two-label SSE2 path that:

- preserves the existing double-operation order, no-FMA rule, binary32 output,
  NaN-to-zero behavior, and nonnegative clamp;
- uses a compare mask instead of per-label control flow;
- keeps the current scalar implementation as reference and fallback; and
- adds no `64*K` state or other persistent model bytes.

That optimization was not implemented here. It needs its own bounded
authorization and must first pass exact/adversarial scalar parity before the
unchanged native microbenchmark is rerun.

Profiling artifacts:

- `/tmp/structured_2d_builder_profile.cpp`;
- `/tmp/structured_2d_compact_vectorization.txt`;
- `/tmp/structured_2d_compact_assembly.txt`;
- `/tmp/structured_2d_profile_perf_b4_compact.txt`;
- `/tmp/structured_2d_profile_perf_b4_expanded.txt`;
- `/tmp/structured_2d_profile_perf_b8_compact.txt`;
- `/tmp/structured_2d_profile_perf_b8_expanded.txt`;
- `/tmp/structured_2d_compact_fastmath_vectorization.txt`;
- `/tmp/structured_2d_profile_fastmath.txt`.

SHA-256:

```text
e698a8dd30c0a5003e0d65c946c0b8a09252505c4a660c49346e02381f1d5714  driver
1bab32d1b616039ca299a928feab551b23e42c925412bdad8d046b2c8e737272  vectorization
c2b460c80351f1afaaa6d9ca8b27ffe46b1dab412c54e53b9688664db3249504  assembly
a9076fb4cfa3434a7209f022d6f5b4a11f016119adfcf130cf5b6d8c2491973b  B4 compact perf
af0cdcda414883bf5d097edda9470b101170d41b2e6b5349fb9cfcb444190c11  B4 expanded perf
c6ae8d912d203b4019ec96294d5ebb2d35744623b2579f8e74127fd9bc264ebb  B8 compact perf
8e663fb5cc1df081192e2de05d0516cc4099df1e12780c25c5e8e10e1a9fee21  B8 expanded perf
ff96bbc00442172c4770bfbbc5a9cec492460edbcc02ee3689c462f16dd2dfcd  fast-math vectorization
2ed414f4e59c87491bd50b0ccf43589fbb74eef9e5a90482acc0020779adbf91  fast-math timing
```

## Semantics-preserving SSE2 compact builder

Implementation date: 2026-07-24

```text
PASS_SSE2_SCALAR_BITWISE_PARITY
PASS_SSE2_PACKED_DOUBLE_HOT_PATH
PASS_NATIVE_TABLE_BUILD_AFFORDABILITY
PASS_NATIVE_LOOKUP_PARITY
PASS_NATIVE_TABLE_CORRECTNESS
```

### Implementation boundary

Starting from profiling commit `e6a43c6`, the compact builder now processes
two labels in packed SSE2 double lanes. The scalar formula remains the
reference, odd-label tail, and non-SSE2 fallback.

The packed path preserves the scalar expression tree, disables contraction
through the existing compiler flags, converts packed doubles to binary32 under
the current MXCSR rounding mode, and replaces the per-label clamp branch with
an ordered `value > 0` mask. The mask maps negative values, signed zero, and
NaN to positive zero exactly as `std::max(0.0, value)` does. It adds no model
fields, derived `64*K` state, table entries, dispatch ids, or persistent
bytes.

Focused tests establish bitwise SSE2/scalar equality for B4 and B8 across:

- ordinary deterministic shapes, queries, and affine maps;
- NaN, positive and negative infinity, subnormals, signed zero, and
  overflow-sized values;
- nearest, downward, upward, and toward-zero rounding modes; and
- an odd codebook size exercising the scalar tail.

The existing compact-versus-expanded tolerance, encoding, pair, occupancy,
collision, and fixed-budget tests also pass.
An ASan-only build also passes with leak detection disabled because
LeakSanitizer is unsupported under the execution sandbox's ptrace boundary.

### Hot-path verification

The strict production assembly contains packed `mulpd`, `addpd`, `subpd`,
ordered packed comparison, mask, and `cvtpd2ps` instructions. The two-label
body has no per-label clamp branch; scalar comparisons occur only in the odd
tail/fallback.

Before any registered rerun, the query-free synthetic B8 profile measured
compact/expanded at approximately `1.84x` cycles and `1.82x` elapsed time over
five runs, passing the frozen `2.0x` prerequisite.

### Registered native result

The original runner, inputs, B4/B8 rates, one warmup, nine repetitions, arm
rotation, CPU 0 affinity, single-thread settings, correctness checks, and
thresholds were unchanged.

| Dataset | Rate | Scalar C/E build | SSE2 C/E build | Ratio reduction | SSE2 C/E lookup | Table violations | Cell pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GIST | B4 | 2.353x | 1.855x | 21.1% | 1.002x | 0 | yes |
| GIST | B8 | 2.887x | 1.851x | 35.9% | 1.006x | 0 | yes |
| CIFAR | B4 | 2.482x | 1.829x | 26.3% | 0.999x | 0 | yes |
| CIFAR | B8 | 2.899x | 1.859x | 35.9% | 0.999x | 0 | yes |

Median compact build costs are now 1.946 and 1.574 ns/entry for GIST B4/B8,
and 1.939 and 1.575 ns/entry for CIFAR B4/B8. All four cells pass the original
`C/E <= 2.0x` affordability rule. Lookup parity and the previous scientific
gates remain passed.

The compact persistent sizes remain 1,664 bytes at B4 and 3,584 bytes at B8,
versus 8,192 and 131,072 bytes for expanded S/V. The result therefore repairs
the measured builder bottleneck without weakening the previously reported
model-size reduction.

### Claim boundary

This is native prototype performance evidence for the isolated table builder
and lookup layout. It does not establish Recall, end-to-end QPS, cache behavior
inside the production estimator, integration cost, statistical generality, or
a SOTA system-level Pareto improvement. The implementation is an artifact
optimization enabling later evaluation, not the scientific contribution.

Artifacts:

- `/tmp/structured-2d-sse2-gist-v2/`;
- `/tmp/structured-2d-sse2-cifar-v2/`;
- `/tmp/structured_2d_sse2_vectorization.txt`;
- `/tmp/structured_2d_sse2_assembly.txt`;
- `/tmp/structured_2d_sse2_perf_b8_compact_preunroll.txt`;
- `/tmp/structured_2d_sse2_perf_b8_expanded.txt`.

SHA-256:

```text
6029a2dc3aa55ebfa406ff34672c22ddae6eabb578d6332be1589ad45c007044  GIST raw
9665ae94678cd609da631625353ff116812b2631b77be5fd252539bc2a6dfb08  GIST decision
e70e1e0dd3cf96eaa9303fd06fda70315ccc340b36280fb694bdbbb839ac0c48  GIST summary
de3141f21a0ada01cbeb983ec7767fa31ba031e7e68a7a08acdfb7cb05ef5a04  GIST compact check
d59fed29a829693460510961719bcc6dee5ff2d5ae96fd96763aed70a3a97b66  CIFAR raw
37fe5f981150450284f87325130707b5762d3c4a4136843dd9aaa3bb82075b56  CIFAR decision
86119d061c149b87fec58756c90f2d42b9605c6af2775ea72e37b7884e48bca3  CIFAR summary
d0028243e87c8a559b71ba238b88b22da55fc5fcf257080542bb12bc3fae7307  CIFAR compact check
b9847fa11a0e2ec92c5e2fef8061cee11884fc2ff4eea82f7b438fae2d452ced  SSE2 vectorization
221d9a140c938d246e095ee5646567d97b2271164d54a2ba52dc53ad2fb9fda2  SSE2 assembly
cc54dad0693e2c5adf94817ac26c485a308e3e9e0b639c382f72fd109e9da601  SSE2 compact perf
20b1df37eccb97bf815d3a708ef179f2490a0c490611b9b9622830d1e2b7a891  SSE2 expanded perf
```

## Unchanged production-estimator integration gate

Date: 2026-07-24

Decision:

```text
NO_GO_UNCHANGED_ESTIMATOR_INTEGRATION
```

The gate first mapped S to the actual production SAQ accurate-estimator path
at snapshot `0dfa0df2`. Admission failed before a numerical or timing run.

The production path is:

1. `IVF::search` constructs `SAQSearcher` and visits selected cells
   (`saqlib/index/ivf.hpp:275-294`);
2. `SAQSearcher::searchCluster` runs the one-bit fast stage and then calls
   `compAccurateDist` for surviving candidates
   (`saqlib/quantization/saq_searcher.hpp:115-160`);
3. `SaqCluEstimator::compAccurateDist` sums the existing segment estimators
   (`saqlib/quantization/saq_estimator.hpp:169-175`); and
4. each `CaqCluEstimator::compAccurateDist` reads the per-coordinate long
   bitplanes and `ExFactor.rescale`, reconstructs an inner product through
   that segment's uniform `sq_delta`, and returns the segment-local expression
   `||o_segment||^2 + ||q_segment||^2 -
   2 * rescale * reconstructed_inner_product`
   (`saqlib/quantization/caq/caq_estimator.hpp:190-215` and
   `saqlib/quantization/fastscan/lut.hpp:121-125`).

The producer mapping is also explicit: `QuantizerSingle` extracts each
coordinate's most-significant bit into the short code and packs every
remaining per-coordinate bit into the long code
(`saqlib/quantization/quantizer.hpp:147-157,166-205`). The cluster layout sizes
those buffers from the segment dimension and bit width
(`saqlib/quantization/cluster_data.hpp:40-56,71-79`).

S has no code with that meaning. It uses one joint B-bit label for each
adjacent-coordinate group and a learned affine K-entry squared-distance table.
Its current scan in `research/structured_2d/microbench.cpp:152-167` directly
indexes those tables. Production SAQ has no joint-label decoder, learned
codebook lookup, or K-entry full-word table consumer.

Consequently, the following would all change the independent variable rather
than integrate S into the unchanged estimator:

- treating S's joint label as existing short/long per-coordinate bitplanes;
- setting `rescale=1` and using the squared-distance table;
- multiplying `rescale` into that table; or
- adding a joint-label decoder or a new full-word VQ scan loop.

The earlier R0 result already established this incompatibility for the
arbitrary-cardinality A4 representation. This gate verifies that the same
consumer mismatch remains for the more compact shared-affine S model. It does
not invalidate S's base-only reconstruction result or its optimized table
builder; it limits the claim to a different full-word VQ representation.

No benchmark query, ground truth, Recall/QPS result, serialized index, raw
held-out row, or registered natural-data input was read by this gate; existing
held-out outcomes were not used to select the integration mapping. No
production source or estimator was changed. A synthetic parity or
amortization run was not performed because it would test a newly defined VQ
consumer after the unchanged-estimator admission condition had already
failed.

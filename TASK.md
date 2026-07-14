# TASK.md

## Closed Research Question (Retained for Provenance)

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

`A4_1S_NO_GO_EXACT_SOLVER_COST_REVIEWED_TERMINAL`.

A4-0 is complete with `PASS_INSTRUMENT_ONLY`. All seven deterministic tests
and all frozen witness checks pass. The A4-1 base-data-only feasibility
preregistration was frozen and pushed at `3aa2f6e`. No dataset artifact was
opened while freezing it.

The authoritative A4-1P contracts are:

- `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`;
- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`;
- `docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json`.

On 2026-07-13 the user authorized A4-1S synthetic-only implementation, parity,
block-control review, and the full-shape cost projection. The implementation
boundary, commands, artifact schemas, conservative ambiguity resolutions, and
status precedence are frozen in:

- `docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md`.

The branch-local A4-1S native solver, independent references, synthetic-only
runner, artifact writer, and deterministic tests are implemented. The 7 A4-0
and 15 A4-1S nonrandom tests pass. The first exact-parity attempt from
implementation commit `9e65159` stopped before the frozen 64-case block RNG
suite with `IMPLEMENTATION_INVALID`: the strict parser incorrectly required
every converged, nonselected block start to have `S` distinct binary32
centers. Those files were WIP, were never committed as evidence, and carry no
scientific decision.

The corrected implementation is `779c556`; it applies distinctness to the
selected winner, independently replays best-of-eight, validates the selected
collision control, and preserves unrelated control failures. Its clean exact
parity run passed, and the six canonical evidence files are committed at
`335837e`. Independent review is recorded in
`docs/saq_attempt4_a4_1s_implementation_parity_review_2026_07_13.md` with
verdict `PASS_PARITY`. This is instrument validation only, not the synthetic
cost result or natural-data/ANN evidence.

The frozen full-shape cost projection ran from clean execution commit
`d0d7057`. Its four canonical wrappers are committed at `9ce1052`, and the
independent cost review is recorded in
`docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md`. The runner
completed the strict prefix of 61 scalar-coordinate shards and stopped after
coordinate 60 crossed the frozen CPU lower bound. Final timed CPU was
`34,805,155,525 us`; the frozen `5/2` projection is
`87,012,888,812.5 us`, or `24.170246892361` CPU-hours, above the registered
24-hour ceiling. Independent committed-evidence review accepted the terminal
verdict `NO_GO_EXACT_SOLVER_COST`.

Real base/centroid/cluster-id access, a natural-data adapter, the atomic base
gate, benchmark queries, SAQ integration, and systems claims remain
unauthorized. This result closes the current A4-1 formulation under its frozen
protocol. It does not authorize a rerun, smaller shape, approximate objective,
serialization change, library/machine substitution, or parameter rescue. The
only authorized follow-up is the required Meeting Summary Handoff; no new
scientific experiment or real-base read is authorized.

The coding primitive is not novel: entropy-constrained quantization,
transform coding, adaptive product-code bit allocation, mixed scalar level
products, irregular SIMD product quantizers, and fixed-address fractional-rate
vector quantizers are all relevant prior work. A publishable claim would need
to establish an ANN-specific rate-distortion/scan advantage at unchanged
fixed payload and controlled table/build work, not merely show that integer
cardinalities form a larger feasible set than powers of two.

## A4-1S: Frozen Synthetic Implementation Gate (Terminal; Historical Sequence)

The following frozen sequence is retained only for provenance and must not be
executed again. Steps 1--4 completed as recorded; step 5 reached its registered
early-stop terminal after publishing coordinate 60; step 6 committed and
independently reviewed that terminal evidence.

1. Commit the A4-1S protocol before accepting or committing runner changes and
   before executing RNG.
2. Implement the compiled exact-rational scalar path, exact allocators,
   direct rational rounding, packing/LUT reference, deterministic block VQ,
   synthetic read guard, and canonical artifact writer without touching
   upstream SAQ code.
3. Commit the implementation, then run the exact exhaustive tiny suite, all
   seven A4-0 tests, the frozen 256-case scalar suite, representation parity,
   block semantic fixtures, and the frozen 64-case block suite.
4. Commit and independently review parity evidence. Any implementation change
   invalidates it and returns to step 2.
5. From the clean reviewed commit, run the full
   `PCG64(20260713) 8192 x 128 float32` projection with all 64 groups, both
   rates, all scalar `K=1..256` curves, all registered allocations, and all
   eight block starts, subject to the frozen atomic CPU early-stop rule.
6. Commit and independently review the cost manifest, summary, and full-detail
   hash ledger.

Before its RNG execution, the A4-1S protocol mechanically clarified two
implementation-evidence details without changing the scientific gate:

- exhaustive allocation parity still executes all 2,433,600 ordered
  decisions, but the full inventory may be persisted as the frozen ordered
  canonical-record SHA-256; the artifact must also retain explicit
  support-class winners and candidate counts, mixed-radix/address fixtures,
  B4/B8/global payload round trips, and binary64/binary32 LUT entries including
  invalid `0x7f800000` entries;
- the command entry is a bootstrap whose first gate action captures the
  integer CPU/wall snapshots before importing the scientific runner,
  reference, artifact helpers, or NumPy. Runner-module import time therefore
  belongs to `preflight` and the snapshots are passed through unchanged.

The frozen projection decision is:

```text
timed_region_cpu_microseconds is the integer getrusage delta defined by A4-1S
projected cost = (5 * timed_region_cpu_microseconds) / 2 microseconds
PASS iff 5 * timed_region_cpu_microseconds <= 2 * 86,400,000,000
the fixed four-file post-timing trailer is the only excluded finalization
NO_GO_EXACT_SOLVER_COST otherwise
```

Artifact, implementation, and block-control defects take precedence over
representation or cost outcomes. The maximum A4-1S result is
`PASS_SYNTHETIC_GATE_ONLY`, which permits only asking the user whether to
authorize the first real-base read. It is not natural-data evidence and is not
base-data authorization.

## A4-0: Synthetic And Instrument Stage

This stage is complete. It did not read benchmark query, ground-truth, or index
artifacts and did not change the SAQ implementation. A4-1P subsequently froze
the base-only protocol; A4-1S subsequently ran and closed with
`NO_GO_EXACT_SOLVER_COST` as described above.

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
A4-1P instead froze exact rational SSE on binary32 inputs and an
exact-arithmetic Monge-optimized native solver. A4-1S measured whether the
registered same-shape exact construction-and-evidence pipeline, rather than an
assumed asymptotic speedup, fit the 24 CPU-hour budget. It did not. The frozen
`NO_GO_EXACT_SOLVER_COST` result does not authorize a floating-point
approximation or a reduced-shape rescue run.

# CO-0 v2 B1 Synthetic Runner Validation

Date: 2026-07-11
Stage: V2-B1 instrument implementation
Decision: PASS for synthetic implementation and review only

## Scope

This stage implemented and reviewed the frozen B1 measurement instrument. It
did not execute a registered encoder arm and did not read GIST/CIFAR base
vectors, centroids, variances, queries, ground truth, indexes, or prior
encoder outputs. It therefore provides no evidence of finite-round CAQ regret
and no method contribution.

Real B1 execution remains separately unauthorized.

## Implemented Instrument

The implementation has four layers:

1. `saqlib/quantization/caq/co0_v2_measurement.hpp` implements the four frozen
   arms, exact centered-grid geometry, canonical code packing, current
   `CaqSingleEstimator<DistType::IP>` invocation, pair metrics, and explicit
   transient-buffer accounting.
2. `saqlib/quantization/caq/co0_v2_b1_io.hpp` implements SHA-256, fvec/ivec
   shape checks, frozen inventory parsing, gzip output, and bit-addressed code
   shards.
3. `src/caq_co0_v2_b1_runner.cpp` implements the frozen one-thread runner,
   complete preflight, rotation verification, output schemas, duplicate-view
   check, and the 24 CPU-hour exact-label stop.
4. `script/summarize_caq_co0_v2_b1.py` implements the shared 512-cell PCG64
   bootstrap, ratio-of-sums estimands, same-vector intersections, all 24
   preregistered one-sided tests, Holm correction, seed checks, and the final
   `NO_GO` or `CONDITIONAL_PASS` decision.

The runner accepts only:

```text
--input-spec PATH
--preregistration PATH
--hypotheses PATH
--inventory-manifest PATH
--output-dir PATH
--threads=1
```

There is no query, ground-truth, dataset, plan, bit, segment, seed, threshold,
sample-size, bootstrap, or rescue override.

## Source And Estimator Alignment

For `lvq_init` and `caq_r6`, the runner calls the current production
`CAQEncoder`. A separate source-aligned trace reproduces its scalar
initialization, coordinate order, `++` then `--` comparisons, correction
placement, `caq_adj_eps=1e-8`, and six-round stopping rule. Every production
code is compared with that trace before output. The local-fixed-point arm uses
the identical trace rule until a complete round accepts no move.

Synthetic validation covered all nine frozen positive `(D,B)` cells under
three deterministic profiles. It performed:

| Check | Count |
|---|---:|
| Arm measurements | 108 |
| Production/source code parity checks | 54 |
| Production/measurement packer byte comparisons | 54 |
| Canonical packed-code round trips | 108 |
| Current-estimator checks | 108 |
| Shared-estimator reuse equivalence checks | 108 |
| Transient-memory checks | 112 |
| Zero-segment/pair checks | 5 |
| I/O contract checks | 7 |

The estimator comparison uses a float32 accumulation bound derived from the
number of dimension/bit-plane operations and the absolute term sum. It is a
numerical implementation check, not a research threshold.

## Preflight And Failure Semantics

Before the first encoder call, the runner:

1. verifies the frozen hashes of the input specification, preregistration,
   hypothesis ledger, and inventory manifest;
2. verifies byte size, SHA-256, row count, and dimension for every registered
   base, centroid, variance, and cluster-id artifact;
3. verifies all sample, pair, and allocation inventory hashes and structure;
4. regenerates all 27 production-compatible rotations and verifies every
   matrix hash; and
5. requires a new or empty output directory.

Any mismatch stops before encoding. Once output begins, a failure preserves
completed shards and writes a `STOPPED` manifest. The runner never removes or
overwrites a nonempty output directory.

The exact-oracle CPU accumulator is checked before each label against the
frozen A2 per-cell upper bound and the total 24 CPU-hour ceiling. Uniform
`B=4` controls use the preregistered whole-view upper bound rather than an
unregistered dimension-specific estimate. Timing, event work, heap work,
integer width, packed bytes, process RSS, and explicit owned-buffer terms
remain visible overhead evidence.

The run manifest reports cumulative wall/CPU time for preflight, rotation,
input I/O, residual construction, each encoder arm, pair estimation, output
I/O, source-parity instrumentation, and the complete run. Each completed
dataset/seed/view/arm shard records
its encoding CSV, pair CSV, code payload, total bytes, and process RSS.
Pair-side evaluation constructs the unchanged estimator once per
pair/view/seed and reuses it across the four stored-code arms; synthetic
checks prove this produces the same estimates as four independent
constructions.

## Statistical Validation

Four Python tests passed:

- deterministic `PCG64(20260711)` generation of the complete
  `10000 x 512` bootstrap draw matrix;
- a constructed 24-hypothesis `CONDITIONAL_PASS` case;
- a constructed CIFAR materiality failure returning `NO_GO`; and
- Holm step-down correction across one family.

The summarizer requires a completed run manifest with exactly 9,600,000
encoding rows and 4,773,192 pair rows. It reads only the frozen leading-view
`caq_r6` and `corrected_exact` pair shards for the primary estimator tests.

## Verification

Release:

```bash
cmake -S validation/caq_corrected_oracle \
  -B /tmp/saq-v2-b1-release-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-v2-b1-release-build --parallel 4
ctest --test-dir /tmp/saq-v2-b1-release-build --output-on-failure
python -m unittest script.test_summarize_caq_co0_v2_b1
```

Result: four of four CTests and four of four Python tests passed.

Sanitizer/debug:

```bash
cmake -S validation/caq_corrected_oracle \
  -B /tmp/saq-v2-b1-asan-build -DCMAKE_BUILD_TYPE=Debug \
  -DCAQ_CORRECTED_ORACLE_ENABLE_ASAN=ON
cmake --build /tmp/saq-v2-b1-asan-build --parallel 4
ctest --test-dir /tmp/saq-v2-b1-asan-build --output-on-failure
```

Result: four of four CTests passed under ASAN.

## Interpretation And Boundary

The measurement instrument now passes its synthetic implementation gate. This
does not authorize the command that opens registered float artifacts. The
next permissible step is a separate review of this implementation and an
explicit decision on real B1 execution.

If real B1 is later authorized, its result is still limited to:

- `NO_GO`: preserve the negative evidence and do not rescue the screen; or
- `CONDITIONAL_PASS`: establish an SAQ-specific limitation and begin a new
  primary-source/theory review of low-cost repair mechanisms.

Neither outcome by itself establishes a publishable method.

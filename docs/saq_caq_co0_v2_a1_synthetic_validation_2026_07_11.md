# CO-0 v2 Corrected-Oracle Synthetic Validation

Date: 2026-07-11
Stage: V2-A0/V2-A1
Decision: PASS

## Scope

This stage validates an independent exact-integer complete-event oracle for
the finite centered CAQ codebook. It uses synthetic binary32 vectors only. It
does not read GIST, CIFAR, benchmark queries, ground truth, or an existing
index. The oracle is prior-work-based measurement infrastructure; it is not
the pinned official Extended-RaBitQ implementation and is not a research
contribution.

The v1 `CO-0A` official-source result remains `FAIL`. V2 does not reinterpret
that implementation as correct; it replaces the failed measurement instrument
with an independently specified oracle.

## V2-A0 Specification Review

The final specification is
`docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md`. The review resolved
the following obligations before the final validation executions:

| Obligation | Resolution |
|---|---|
| Finite objective | Maximize exact `Q=(sum A_i g_i)^2/sum g_i^2` over the centered half-grid. |
| Scale reduction | `max_z max_alpha H(alpha,z)=max_alpha max_z H(alpha,z)` reduces code search to all rounding events. |
| Initial state | The all-minimum magnitude code is scored before the first event. |
| Equal events | Every tied lower/upper combination has the same `H`; a deterministic tie chain therefore contains a global-`Q` code. |
| Binary32 | Finite values are decomposed exactly into a common power of two and arbitrary-precision integers. |
| Event order | Fractions `j/A_i` are ordered by exact integer cross products. |
| Objective order | Squared scores are compared with `cpp_int`; no epsilon or square root selects the code. |
| Sign and zero | Nonzero signs are preserved; both signed zeros use minimum positive magnitude. |
| Width | Magnitude and centered codes use `uint32_t`, including legal `B=11` values above 255. |
| Cost | `E=D_+(2^(B-1)-1)` events, `O(E log D_+)` exact comparisons, `O(D)` transient state, and zero persistent bytes. |

The output schema is version 2. The only amendment during implementation
review was adding wall time, CPU time, and peak RSS fields required by the
parent protocol; the objective, event set, tie rule, and code semantics did
not change.

## V2-A1 Implementation

The oracle is header-only validation infrastructure in
`saqlib/quantization/caq/exact_event_oracle.hpp`. It keeps one next event per
nonzero coordinate in an exact min-heap, updates exact dot/norm state, records
the best event ordinal, and replays that ordinal to reconstruct the code.
Neither index construction nor search includes this header.

The independent validator is
`src/caq_corrected_oracle_validation.cpp`. Its reference path separately
decomposes binary32 inputs, enumerates every code for feasible fixtures, and
recomputes centered mapping, cosine, rescale, and a synthetic-query estimator
identity. Two `B=1` fixtures assert hand-derived integer values for subnormal,
normal, and largest-finite inputs, reducing the risk that two copies of the
same decomposition formula agree on the same error.

## Coverage And Result

Both Release and ASAN executions passed with identical logical counts:

| Check | Count | Result |
|---|---:|---|
| Complete-codebook brute force | 128 | PASS |
| Prior deterministic fixtures | 109 | PASS |
| Initial-state regressions | 2 | PASS |
| Zero semantics | 7 | PASS |
| Equal-event ties | 9 | PASS |
| 64-lane padding | 1 | PASS |
| Subnormal cases | 3 | PASS |
| Largest-finite cases | 3 | PASS |
| Widened `B=11` case | 1 | PASS |
| Independent mapping/diagnostics | 130 | PASS |
| Rejected invalid inputs | 5 | PASS |

The 109 prior fixtures comprise 12 deterministic inputs for every
`D in {2,3,4}` and `B in {2,3,4}`, plus the original tiny initialized-state
counterexample. Complete brute force evaluates every magnitude-code
configuration for each feasible case. The separate reachable `D=64, B=3`
case selects magnitude code `[1,0,...,0]`, including the state missed by the
v1 official implementation. The `B=11` case selects magnitude 1023 without
byte narrowing.

Aggregate oracle work was 67,072 first-pass events, 1,523 replay events,
478,008 heap comparisons, and 67,072 exact objective comparisons. The maximum
observed arbitrary-precision integer width was 563 bits. Persistent index
storage is zero bytes.

| Build | Wall time | CPU time | Peak RSS | Result |
|---|---:|---:|---:|---|
| Release | 29.469 ms | 29.405 ms | 18,677,760 B | PASS |
| ASAN/debug | 528.405 ms | 527.440 ms | 18,481,152 B | PASS |

These timings characterize this bounded validator run, not V2-A2 oracle cost
at frozen SAQ segment shapes. LeakSanitizer was disabled because it cannot run
under the current ptrace-managed environment; AddressSanitizer remained
enabled with `halt_on_error=1` and reported no error.

## Reproduction

The standalone CMake project avoids unrelated SAQ production dependencies:

```bash
cmake -S validation/caq_corrected_oracle \
  -B /tmp/saq-v2-oracle-release-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-v2-oracle-release-build --parallel
ctest --test-dir /tmp/saq-v2-oracle-release-build --output-on-failure
/tmp/saq-v2-oracle-release-build/caq_corrected_oracle_validation

cmake -S validation/caq_corrected_oracle \
  -B /tmp/saq-v2-oracle-asan-build \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCAQ_CORRECTED_ORACLE_ENABLE_ASAN=ON
cmake --build /tmp/saq-v2-oracle-asan-build --parallel
ctest --test-dir /tmp/saq-v2-oracle-asan-build --output-on-failure
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  /tmp/saq-v2-oracle-asan-build/caq_corrected_oracle_validation
```

Raw outputs and build/source hashes are under
`docs/saq_caq_co0_v2_a1_artifacts_2026_07_11/`.

The full repository configure command was also attempted with
`BUILD_UNIT_TESTS=OFF`, but this environment could not locate the glog, fmt,
or gflags CMake packages and stopped before compiling any target. The
dependency-isolated project compiles the identical validator source and is the
authoritative V2-A1 build. This stage therefore establishes corrected-oracle
validation, not a successful rebuild of all SAQ production binaries.

## Decision And Boundary

V2-A0 and V2-A1 pass. This establishes a valid synthetic exact-label
instrument under the specified finite codebook. It does not show that
production six-round CAQ has measurable regret, that any regret is SAQ
specific, or that a useful method exists.

The current authorization ends here. Do not run V2-A2, access dataset
artifacts, write V2-B preregistration, or design a CAQ repair without a
separate decision.

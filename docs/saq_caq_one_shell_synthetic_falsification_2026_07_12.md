# Exact One-Shell CAQ Repair: Synthetic Falsification Evidence

Date: 2026-07-12

## Decision

```text
NO_GO_ON_COMPLEXITY
```

The exact radius-one Cartesian shell passes its synthetic correctness
requirements, but it fails the frozen low-cost gate by a wide margin. The
fastest measured fixed-width case has total `CAQ + shell` CPU equal to
`4.579x` production `r=6` CAQ; the four frozen rows range from `4.579x` to
`8.169x`. The authorized maximum was `2.0x`.

The direction stops before reading GIST, CIFAR, B1 per-vector outputs,
benchmark queries, ground truth, or indexes. Gap recovery is deliberately not
measured because the complexity half of the conjunctive gate already fails.
No production integration, method claim, shell-radius extension, repeated
pass, restart, acceptance threshold, or rescue experiment is authorized.

## Question And Frozen Gate

The preceding related-work and theory review authorized one candidate only:
the exact Cartesian product of the incumbent CAQ magnitude code and each
coordinate's immediate legal neighbors. For incumbent code `k`, level count
`L=2^(B-1)`, and dimension `D`,

```math
\mathcal N_1(k)=\prod_{i=1}^{D}
\left(\{k_i-1,k_i,k_i+1\}\cap\{0,\ldots,L-1\}\right).
```

The frozen later method gate was conjunctive:

```text
total CAQ + shell CPU/work <= 2.0x production r=6 CAQ
and
recovered exact-oracle gap >= 0.50 on both frozen leading segments.
```

Synthetic implementation was permitted only to establish exactness and test
whether the first condition was plausible. It could not read dataset
artifacts.

## Implemented Instrument

The implementation is diagnostic-only and has no query-path caller.

- `ExactOneShellRepair` decomposes every nonnegative binary32 magnitude into
  exact integers under one common power of two. It orders shell events by
  exact integer cross products and compares `S^2/N` with arbitrary-precision
  integers.
- `FixedWidthOneShellRepair` uses exact `uint64_t`, unsigned 128-bit, and
  fixed 256-bit arithmetic when the binary32 exponent span permits it. The
  exponent-span limit is a representability condition: a 24-bit binary32
  significand shifted by at most 40 bits fits in `uint64_t`. Unsupported or
  overflowed inputs deterministically retain the incumbent; they do not call
  an exact fallback.
- The fixed-width objective comparison first applies a conservative binary64
  separation filter. Products that are not safely separated use an exact
  256-bit cross product. This changes cost, not the selected exact ordering.
- Both variants keep the incumbent unless the shell optimum is strictly
  better. The result is a shell-local certificate only.

For at most two events per nonzero coordinate, both implementations maintain

```math
S=\sum_i a_i(2k_i+1),\qquad
N=\sum_i(2k_i+1)^2,\qquad
Q=S^2/N.
```

The odd grid is a factor-two rescaling of the half-grid in the theory review,
so it leaves `Q` and every selected code unchanged. Event ordering costs
`O(D log D)`, scanning and replay cost `O(D)`, tracked transient storage is
`O(D)`, and persistent/query overhead is zero because this prototype is not
integrated.

## Correctness Evidence

The Release and ASAN builds agree on the following counters:

| Check | Result |
|---|---:|
| Exhaustive input/code cases | 6,060 |
| Brute-force shell codes evaluated | 110,230 |
| Fixed-width/exact parity cases | 6,066 |
| Deterministic fixed-width abstentions | 2 |
| Invalid inputs rejected | 16 |
| Total exact shell events | 21,462 |
| Event sort comparisons | 34,061 |
| Objective comparisons | 27,428 |

The selected fixtures cover a positive repair, a negative repair, tied
events, an all-zero vector, codebook boundaries, subnormals, largest finite
binary32 values, and `B=11`. The two fixed-width abstentions are the expected
extreme-exponent fixtures; the arbitrary-precision implementation still
matches brute force on them. Every enumerable case selects the same objective
as direct enumeration of the full shell.

## Canonical Release Cost Result

Each row executes production CAQ `r=6`, the exact shell, and the fixed-width
shell 1,024 times on a deterministic `D=64` signed input. CPU time uses
`CLOCK_PROCESS_CPUTIME_ID`. `B` is total bits per dimension, including sign.

| Profile | B | Shell events | Sort comparisons | Exact shell / CAQ | Fixed shell / CAQ | Total / CAQ |
|---|---:|---:|---:|---:|---:|---:|
| balanced | 11 | 127 | 1,031 | 42.181x | 7.169x | 8.169x |
| dyadic | 11 | 120 | 972 | 27.096x | 4.751x | 5.751x |
| balanced | 9 | 127 | 983 | 20.889x | 3.579x | 4.579x |
| dyadic | 9 | 120 | 972 | 26.281x | 4.600x | 5.600x |

The fixed-width path uses at most 3,936 tracked transient bytes in these
`D=64` cost rows. All 121 or 128 objective decisions per row are resolved by
the separation filter, with zero exact-objective fallbacks. The dominant
visible work is therefore the ordering of 120-127 rational events, requiring
972-1,031 128-bit cross-product comparisons per encoding. It is not caused by
arbitrary-precision objective comparisons.

All artificial cost inputs happen to admit a strict shell improvement. That
count is a control against dead-code elimination, not quality evidence and
not an estimate of improvement frequency on SAQ residuals.

## Gate Evaluation

| Requirement | Outcome | Interpretation |
|---|---|---|
| Exact shell vs brute force | `PASS` | The local certificate is implemented correctly on the frozen synthetic coverage. |
| Deterministic fixed-width path | `PASS` | Supported cases match the exact path; unsupported cases preserve the incumbent. |
| Release regression suite | `PASS` | 5/5 standalone tests pass. |
| ASAN regression suite | `PASS` | 5/5 standalone tests pass with leak detection disabled for the environment. |
| Total work at most `2.0x` CAQ | `FAIL` | Best row is `4.579x`; worst row is `8.169x`. |
| Recover at least half the exact gap | `NOT RUN` | The conjunctive gate already failed before data access. |

## Research Interpretation

The review's narrow novelty argument survives only at the level of a correct
local certificate: a `3^D` Cartesian neighborhood can be solved with at most
`2D` shared-scale events independent of native bit width. The implementation
shows why this is not yet a useful SAQ repair. Production CAQ on a short
`D=64` segment is sufficiently cheap that sorting even 120-127 exact local
events costs several times the baseline encoder.

This result does not prove that every possible implementation of the shell is
slower by the same constant. It does show that the reviewed comparison-based
exact event realization misses the frozen gate by 2.29x even in its best
total-cost row, while its operation profile is structurally dominated by
`O(D log D)` event ordering. Removing exact fallback cost cannot close the
gap because no such fallback occurs in the measured rows. Claiming a method
would therefore require a different mechanism or a new non-comparison
complexity argument, not another implementation-level tuning pass.

The correct outcome is negative evidence:

```text
CAQ has a measured high-bit coordinate-local limitation,
but the minimal exact coordinated shell reviewed here is not low-cost enough.
```

## Reproduction

Release:

```bash
cmake -S validation/caq_corrected_oracle -B /tmp/saq-one-shell-release \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-one-shell-release --parallel 4
/tmp/saq-one-shell-release/caq_one_shell_synthetic_validation
ctest --test-dir /tmp/saq-one-shell-release --output-on-failure
```

ASAN/debug:

```bash
cmake -S validation/caq_corrected_oracle -B /tmp/saq-one-shell-asan \
  -DCMAKE_BUILD_TYPE=Debug -DCAQ_CORRECTED_ORACLE_ENABLE_ASAN=ON
cmake --build /tmp/saq-one-shell-asan --parallel 4
ctest --test-dir /tmp/saq-one-shell-asan --output-on-failure
```

Python regression:

```bash
python -m unittest script.test_summarize_caq_co0_v2_b1
```

Canonical machine-readable output is stored in
`docs/saq_caq_one_shell_synthetic_artifacts_2026_07_12/validation_result.json`.

## Limitations

- The timing profiles are deterministic synthetic inputs, not frozen GIST or
  CIFAR residuals; they answer only the pre-data complexity question.
- CPU ratios are implementation and machine dependent. The operation counts
  explain the observed gap but are not an architecture-independent lower
  bound.
- Tracked transient bytes include owned work buffers but are not a process
  peak-memory measurement.
- Exhaustive parity is finite and low-dimensional. Exact integer event and
  objective arithmetic provide the implementation argument beyond those
  fixtures.
- No objective-gap recovery, estimator, recall, QPS, or index-size result is
  supported by this stage.

# CO-0A Official-Source Parity for E-RaBitQ

Date: 2026-07-11

## Decision

**FAIL. CO-0B is not authorized, and no preregistration or GIST/CIFAR output
was produced.**

The pinned official Extended-RaBitQ artifact cannot serve as the exact oracle
required by the frozen CO-0 protocol:

1. its `fast_quantize` implementation misses a globally optimal codeword on a
   reachable public `D=64, B=3` input;
2. its public IVF implementation does not support every bit width in the
   frozen SAQ plans; and
3. the private encoder's `uint8_t` output narrows valid 10-bit magnitudes for
   SAQ's `B=11` leading segment.

This is an artifact-validation failure, not evidence that production CAQ is
optimal or suboptimal on SAQ data. The codebook mapping itself passed. Under
the predeclared rule in the go/no-go memo, the direction stops before dataset
measurement.

Machine-readable evidence is in
`docs/saq_caq_co0a_artifacts_2026_07_11/source_parity_result.json`.

## Frozen Validity Rule

The migrated go/no-go memo required the following sequence:

```text
pin official E-RaBitQ source
exhaustively compare tiny codebooks
validate the CAQ/E-RaBitQ mapping and factors
reject parity if source behavior changes the feasible codebook
write CO-0B preregistration only if all CO-0A checks pass
```

Therefore a nonzero source-oracle gap cannot be reclassified after observation
as an acceptable approximation. Replacing the official routine with a
paper-corrected implementation would be a new oracle contract and would
require a new protocol before any base-data result is read.

## Official Source Pin

| Item | Frozen value |
|---|---|
| Repository | `https://github.com/VectorDB-NTU/Extended-RaBitQ.git` |
| Commit | `52b9e6c7ba6c316036cdb04074732fe561966a53` |
| Commit date | `2026-03-30T17:40:13+02:00` |
| License | Apache-2.0 |
| Local form | Git submodule at `third_party/Extended-RaBitQ` |
| Encoder | `inc/index/Quantizer.hpp:DataQuantizer::fast_quantize` |
| Public bit-width check | `inc/index/IVF.hpp:IVF::IVF` |

Pinned SHA-256 values:

```text
366acdb6180438e650357d84536575a42cc9bf9477825518ce9bd2ed8e83088f  inc/index/Quantizer.hpp
cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  LICENSE
10e1e0a30a654033c531ee31b3009ce71155b74b2fc23d71677dd4640c3a9ca4  CMakeLists.txt
5293282b367c8ff5f54b1aec4bab83401252eb35a0326ea59f71167be7c981ee  src/erabitq_source_parity.cpp
```

The harness includes the official header and invokes the actual private
`DataQuantizer::fast_quantize` implementation. A scalar source-faithful copy is
used only to expose widened intermediate magnitudes and to compare the exact
official event window. It is not substituted for the official call.

## Source Semantics Reviewed

The artifact defines total bits as `B = EX_BITS + 1`. Its public IVF
constructor accepts `EX_BITS` in `{2,3,4,6,7,8}`, hence total
`B in {3,4,5,7,8,9}`. The frozen GIST plan additionally needs total
`B in {2,6,11}`.

There is no alternate data-vector encoder in the pinned repository:
`DataQuantizer::exrabitq_codes`, which is called by the production IVF build,
invokes `fast_quantize` for every normalized absolute vector. The repository
README reports the same public total-bit set. The repository is archived and
points to a newer general RaBitQ library, but changing artifacts after freezing
the named Extended-RaBitQ source would not establish parity for this gate.

`fast_quantize` performs the following operations:

1. initialize integer magnitudes at
   `t_start=floor((2^EX_BITS-1)/3)/max(o)`;
2. initialize the numerator and denominator for that code;
3. set `max_ip=0` and selected scale `t=0` without scoring the initialized
   state;
4. score only states after a coordinate increment, within a bounded event
   window; and
5. reconstruct the code at the selected scale and cast every magnitude to
   `uint8_t`.

The missing initial-state evaluation is sufficient to disprove exact-source
parity. The byte cast is independently incompatible with `EX_BITS=10`, for
which legal magnitudes range from 0 to 1023.

## Harness Design

The source-parity target is `erabitq_source_parity` in
`src/erabitq_source_parity.cpp`. It contains four independent checks.

### Complete tiny-codebook enumeration

For `D in {2,3,4}` and total `B in {2,3,4}`, the harness enumerates every
magnitude vector in `{0,...,2^(B-1)-1}^D`. It uses 12 deterministic positive
fixtures per cell plus one explicit initial-state fixture, for 109 cases.

### Independent full-event oracle

An independent enumerator visits every coordinate scale event from the all-zero
magnitude state. Its maximum is compared with complete brute force on every
tiny fixture. This check validates the enumerator, not the official artifact.

### Compiled official-source comparison

At `D=64`, the harness invokes the pinned official implementation for total
bits `{2,3,4,5,6,7,8,9,11}`, four deterministic magnitude families, and six
seeds per family. Public bit widths, private-but-byte-representable extensions,
and the widened `B=11` case are reported separately. An explicit reachable
public counterexample is also invoked through the same official function.

### Codebook and factor mapping

For total `B in {2,3,4,6,9,11}`, eight deterministic signed fixtures validate
the integer code mapping, normalized direction, rescaled inner-product
estimate, and error-factor formula in float64. Official float output is checked
against an independently recomputed factor with relative tolerance `3e-6`.

The objective tolerance is `2e-12`. The pass rule requires zero official
objective misses and no representation narrowing.

## Results

| Check | Result |
|---|---:|
| Tiny complete-codebook cases | 109 |
| Independent full-event versus brute force | PASS; maximum gap 0 |
| Official tiny misses | 1 |
| Maximum tiny official gap | 0.005307892151723226 |
| Actual official public-path cases | 145 |
| Private byte-representable extension cases | 48 |
| `B=11` cases | 24 |
| Reachable `D=64` official misses | 1 |
| Maximum `D=64` full-event gap | 0.002844955452831144 |
| Mapping/factor cases | 48 |
| Maximum mapping gap | 0 |
| Maximum official factor relative gap | 5.584143775936138e-8 |
| Widened `B=11` values above 255 | 815 |
| Release result | FAIL, exit 1 |
| ASAN result | same deterministic FAIL, exit 1; no memory error |

### Reachable public counterexample

For total `B=3`, let

```text
D = 64
x = (3, 1, ..., 1) / sqrt(72)
```

The legal magnitude code `(1,0,...,0)` represents the half-offset direction
`(1.5,0.5,...,0.5)`, which is exactly collinear with `x`. Its cosine is
therefore the global upper bound 1. The official source returns
`(3,1,...,1)`, with observed cosine `0.99715504454716886`.

The optimal code is precisely the source's initialized `t_start` state. The
routine calculates that state but never evaluates it before incrementing one
coordinate. This counterexample is in the artifact's public bit-width set and
uses its required padded dimension, so neither unsupported packing nor a tiny
test-only dimension explains the miss.

### `B=11` representation failure

SAQ's frozen GIST leading segment uses total `B=11`, equivalent to ten
magnitude bits. Calling the private official encoder at this width generates
legal magnitudes above 255, but the interface writes `uint8_t`. In 24 fixed
fixtures, 815 coordinate values exceeded 255 and were narrowed modulo 256.
Consequently the returned code is not in parity with the intended 10-bit
magnitude codebook.

This is separate from the public IVF limitation: the public constructor does
not accept total `B=11` at all.

## CAQ/E-RaBitQ Mapping Result

The nonzero-coordinate codebook mapping passed exactly. For total bit width
`B`, define `L=2^(B-1)`, magnitude `k in [0,L-1]`, and sign
`s in {0,1}`. Let the low CAQ bits be `k` for a positive sign and `L-1-k`
for a negative sign, and let `c=L*s+low`. Then

```text
c + 0.5 - L = (2s - 1)(k + 0.5).
```

Thus CAQ's decoded vector is a scalar multiple `delta*a` of the signed
E-RaBitQ grid vector `a`. For residual `o`, `R=||o||`, `u=o/R`, and
`N=<u,a>`, CAQ's factor is `R/(delta*N)`, so the unchanged rescaled inner
product is

```text
[R/(delta*N)] <delta*a,q> = R<a,q>/N.
```

The independently recomputed error factor is

```text
R^2 * epsilon * sqrt((1/cosine^2 - 1)/(D - 1)).
```

All 48 mapping fixtures had zero algebraic mapping gap. Therefore CO-0A fails
because the selected official executable encoder is not the required exact,
width-compatible oracle—not because the SAQ/E-RaBitQ codebook-equivalence
lemma failed for nonzero coordinates.

Exact zeros remain a convention limitation: the official routine assumes
positive magnitudes, while a signed half-offset code has two objective-tied
representations at zero. Zero behavior was not claimed as official parity.

## Separate SAQ Implementation Observations

These findings did not determine the CO-0A verdict and are not research
contributions:

- `CaqCode::get_oa()` reconstructs `code*delta+v_mi`, whereas encoding and
  adjustment use `(code+0.5)*delta+v_mi`. The method currently feeds the
  optional centroid inner product and should be handled as a correctness issue
  if that field is exercised.
- The coordinate-move tolerance is `caq_adj_eps*oa_l2sqr`; any future
  local-fixed-point comparison must freeze the numeric scale and report
  sensitivity rather than silently treating it as an exact stopping rule.
- `fac_error` is stored in `ExFactor.error`, but the present search path does
  not consume it. A smaller error factor alone could not establish an estimator
  benefit.

No correction was made on this branch because CO-0A is source validation, not
implementation maintenance.

## Reproduction

Release configuration and run:

```bash
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j --target erabitq_source_parity
./bin/erabitq_source_parity
```

The Release compile uses GCC 11.5.0, GNU C++20, `-O3 -Ofast`,
`-ffp-contract=off`, `-fno-finite-math-only`, `-march=native`, and AVX-512
F/DQ/BW/VL on an Intel Core i9-10920X. Exit 1 is the expected gate verdict,
not a harness crash.

Independent sanitizer build and run:

```bash
c++ -std=gnu++20 -O0 -g -fsanitize=address -fno-omit-frame-pointer \
  -mavx512f -mavx512dq -mavx512bw -mavx512vl -march=native \
  -ffp-contract=off -fno-finite-math-only \
  -DERABITQ_SOURCE_COMMIT=\"52b9e6c7ba6c316036cdb04074732fe561966a53\" \
  -Ithird_party/Extended-RaBitQ/inc -Isaqlib \
  -o /tmp/erabitq_source_parity_asan_clean src/erabitq_source_parity.cpp
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  /tmp/erabitq_source_parity_asan_clean
```

The sanitizer run produced the same counters and expected exit 1 without an
AddressSanitizer report.

## Stop Decision and Possible Reopening

The conditional C6 direction is **NO-GO under the frozen official-source
contract**. CO-0B was not written because doing so after the failed mandatory
validity check would erase the preregistered stopping rule.

Reopening requires explicit authorization for a distinct protocol that names
and validates a paper-corrected, widened independent full-event oracle. Such an
oracle must not be described as official-source parity. Its proof obligations,
bit-width representation, zero convention, tolerances, and computational-cost
boundary must be frozen before any GIST/CIFAR residual is inspected.

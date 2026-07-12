# CO-0 v2 B1 Rotation Build Correction

Date: 2026-07-12

## Scope

The first authorized registered B1 command stopped during preflight. It read
and hash-verified the frozen GIST/CIFAR base, centroid, variance, assignment,
and inventory artifacts, but stopped before residual preparation or the first
encoder call. The preserved manifest reports:

```text
status = STOPPED
message = rotation hash mismatch
encoding_rows = 0
pair_rows = 0
exact_cpu_ns = 0
code_bytes = 0
```

This is an instrument-build failure, not a scientific `NO_GO` outcome. No
objective or estimator result was produced, and the frozen preregistration,
input specification, hypotheses, samples, pairs, rotations, arms, and
thresholds were not changed.

## Cause

B0 generated the 27 registered rotation matrices with the recorded Release
profile:

```text
-O3 -DNDEBUG -std=gnu++20 -Wall -Wextra -Wpedantic
-fno-fast-math -ffp-contract=off
```

The B1 runner translation unit additionally enabled:

```text
-mavx2 -mfma -mavx512f -mavx512dq -mavx512bw -mavx512vl
```

Eigen's Householder QR therefore used a different vectorized evaluation path.
The original B0 generator reproduced 27 of 27 committed hashes. Compiling the
same generator with the runner's SIMD flags reproduced zero of 27 hashes. The
two matrix sets remained numerically close (`5.018e-6` maximum absolute
element difference and `1.429e-7` maximum matrix RMSE), but byte identity is a
frozen protocol requirement.

The initial synthetic runner review regenerated rotations only through the B0
generator target. It did not exercise rotation generation through the
SIMD-compiled runner path, so it did not expose this build-profile dependency.

## Instrument-Only Correction

Rotation generation now executes in `src/caq_co0_v2_frozen_rotation.cpp`, a
separate translation unit fixed to the registered B0 Release profile and
explicitly compiled without AVX/FMA. It writes row-major values into buffers
owned by the runner. Eigen matrix objects do not cross the build-profile
boundary.

The runner and all CAQ encoder, packing, and estimator code retain their
original AVX2/FMA/AVX512 flags. A compile-time guard rejects accidental AVX or
FMA compilation of the frozen rotation unit. This changes only how the
already-registered rotation bytes are reconstructed; it does not change a
scientific independent variable.

## Verification

Release validation:

```text
4/4 CTests passed
27/27 frozen rotation hashes matched through the runner-linked path
108/108 arm measurements passed
54/54 production/source parity checks passed
108/108 estimator checks passed
```

ASAN validation also passed 4/4 CTests. The frozen rotation unit remains ASAN
instrumented while using `-O3 -DNDEBUG`, because those optimization semantics
are part of the registered rotation provenance. The Python summarizer retained
4/4 passing unit tests.

The full upstream CMake configuration remains unavailable in this environment
because Glog/Fmt/GFlags package configurations are missing. The isolated
corrected-oracle validation build is the preregistered build path and passed.

## Stage Boundary

The correction is synthetic-validated but has not been used for a second
registered execution. The next step requires a separate review and explicit
authorization to rerun B1. Until then:

```text
registered B1 result = unavailable
scientific decision = unavailable
summarizer execution = not permitted
method design = not permitted
```

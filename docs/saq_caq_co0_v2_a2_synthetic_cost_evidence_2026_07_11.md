# CO-0 v2 Corrected-Oracle Synthetic Cost Evidence

Date: 2026-07-11
Stage: V2-A2
Decision: PASS

## Scope

This stage measures whether the independently validated exact complete-event
oracle can label the frozen later-study sample within a bounded resource
ceiling. It uses only deterministic synthetic binary32 vectors. No dataset,
query, ground truth, index, CAQ objective gap, or encoder comparison is read.

The frozen design is
`docs/saq_caq_co0_v2_a2_synthetic_cost_design_2026_07_11.md`. The raw result
is `docs/saq_caq_co0_v2_a2_artifacts_2026_07_11/cost_result.json`.

## Implementation

`src/caq_corrected_oracle_cost_study.cpp` is a no-argument runner over exactly
nine `(D,B)` cells and three deterministic profiles per cell:

- `equal` stresses simultaneous event ties;
- `dense_unit_interval` stresses ordinary distinct event ordering;
- `binary32_full_span` spans `denorm_min` through the largest finite binary32
  value and stresses arbitrary-precision width.

Every coordinate is nonzero, so each row executes the maximum event count for
its `(D,B)` cell. Input generation is outside the per-encode timer. The runner
checks first-pass and objective-comparison counts against
`E=D(2^(B-1)-1)` before reporting a row.

## Canonical Matrix

All 27 rows completed. Aggregate measured work was:

| Quantity | Value |
|---|---:|
| First-pass events | 306,048 |
| Replay events | 66,980 |
| Heap comparisons | 3,038,492 |
| Objective comparisons | 306,048 |
| Maximum exact-integer width | 605 bits |
| Matrix wall time | 135.577 ms |
| Matrix CPU time | 135.305 ms |
| Process peak RSS | 3,342,336 bytes |
| Persistent index bytes | 0 |

For each cell, `U` is the maximum profile CPU time after replacing observed
replay work by the exact code-independent upper count `R=E`:

| Shape label | `D` | `B` | `E` | Dominant profile | `U` |
|---|---:|---:|---:|---|---:|
| GIST | 64 | 11 | 65,472 | `binary32_full_span` | 81.362 ms |
| GIST | 192 | 6 | 5,952 | `binary32_full_span` | 9.239 ms |
| GIST | 320 | 4 | 2,240 | `binary32_full_span` | 3.833 ms |
| GIST | 256 | 2 | 256 | `binary32_full_span` | 0.535 ms |
| GIST | 832 | 4 | 5,824 | `binary32_full_span` | 10.508 ms |
| CIFAR | 64 | 9 | 16,320 | `binary32_full_span` | 20.646 ms |
| CIFAR | 192 | 5 | 2,880 | `binary32_full_span` | 4.436 ms |
| CIFAR | 128 | 3 | 384 | `binary32_full_span` | 0.632 ms |
| CIFAR | 384 | 4 | 2,688 | `binary32_full_span` | 4.511 ms |

The expensive `D=64,B=11` cell remains the dominant term. Feasibility is
therefore not obtained by omitting or averaging away the frozen high-bit
segment.

## Resource Decision

The frozen equations, including three rotations and conservative whole-view
bounds for omitted uniform-`B=4` controls, give:

| Quantity | Value |
|---|---:|
| Target sample per dataset | 50,000 vectors |
| GIST-shape exact-label upper CPU/vector | 442.528 ms |
| CIFAR-shape exact-label upper CPU/vector | 131.276 ms |
| GIST-shape estimate at `n=50,000` | 6.146 CPU-hours |
| CIFAR-shape estimate at `n=50,000` | 1.823 CPU-hours |
| Combined estimate | **7.969 CPU-hours** |
| Frozen ceiling | 24 CPU-hours |
| Ceiling utilization | 33.2% |

The V2-A2 decision is `PASS`. A common sample of 50,000 vectors per dataset is
retained; no bit width, cell, profile, control, or sample size is removed.

This is an exact-label CPU estimate only. It does not account for PCA/rotation
preparation, IVF residual extraction, the three non-oracle encoder arms,
statistics, or I/O. Those costs must be separately recorded if V2-B is later
authorized.

## Verification

Release and ASAN/debug CTest both passed:

```bash
cmake --build /tmp/saq-v2-oracle-release-build --parallel
ctest --test-dir /tmp/saq-v2-oracle-release-build --output-on-failure

cmake --build /tmp/saq-v2-oracle-asan-build --parallel
ctest --test-dir /tmp/saq-v2-oracle-asan-build --output-on-failure

/tmp/saq-v2-oracle-release-build/caq_corrected_oracle_cost_study \
  > docs/saq_caq_co0_v2_a2_artifacts_2026_07_11/cost_result.json
```

Release ran two of two standalone CTests in 0.17 seconds. ASAN/debug ran two
of two in 3.34 seconds with
`ASAN_OPTIONS=detect_leaks=0:halt_on_error=1`. Build flags, machine identity,
and source/binary hashes are in the artifact manifest.

The full repository build remains untested in this environment because the
root configuration cannot locate glog, fmt, or gflags CMake packages. The
dependency-isolated project compiles the same oracle and runner sources.

## Limitations

1. A single encode is timed per deterministic profile. The study is intended
   for bounded feasibility rather than a publication-quality latency claim.
2. The replay correction is an exact operation-count bound, not a formal
   machine-time bound. CPU frequency, scheduling, allocator, and cache effects
   can vary.
3. `binary32_full_span` reaches the representational width endpoint, but three
   profiles cannot prove a worst-case wall-clock bound over every binary32
   vector.
4. Using each whole-view `B=4` cost for every smaller uniform-`B=4` control is
   deliberately conservative in event count, but is not a timing theorem.
5. The 24-hour rule governs exact labeling only; a later experiment must stop
   if actual exact-label CPU time exceeds it.

The approximately threefold ceiling margin makes these limitations acceptable
for deciding whether to preregister a base-only falsification study. They do
not support a systems-performance claim.

## Boundary

V2-A2 passes, establishing only that corrected-oracle labeling appears
feasible at the frozen sample size. V2-B remains unauthorized. Do not access
GIST/CIFAR artifacts, create sample inventories, inspect encoder gaps, or
design a CAQ repair until a separate V2-B0 preregistration is reviewed and
committed.

# Source-Aligned SymphonyQG Packed FastScan Path

## Research Role

This note records the second and final milestone of Phase 2. Its purpose is to
make the SymphonyQG comparison semantically and structurally faithful before
evaluating any SAQ-specific graph hypothesis. It is baseline validation, not a
new research contribution.

The implementation is aligned with SymphonyQG revision:

```text
6124ddb34ee4d176edea1bd7ad38d1672343df28
```

The packed path follows:

```text
symqglib/space/bitwise.hpp
symqglib/quantization/fastscan_impl.hpp
symqglib/quantization/rabitq.hpp
symqglib/qg/qg_query.hpp
symqglib/qg/qg_scanner.hpp
```

The scalar transform, query quantization, edge factors, and distance formula
were validated in
`docs/saq_symphonyqg_scalar_parity_2026_07_10.md`.

## Packed Computation

Let `Dp` be the power-of-two padded dimension and let `L` be the number of
neighbors of one current graph vertex. FastScan uses batches of 32:

```text
Lp = 32 * ceil(L / 32).
```

Each neighbor has the same residual sign code as the scalar estimator:

```text
b_ij = 1 if residual coordinate j is positive, otherwise 0.
```

The `Dp` bits from 32 neighbors are transposed and interleaved into one packed
block. One batch occupies

```text
32 * Dp / 8 = 4 * Dp bytes.
```

For every group of four query codes `(c0,c1,c2,c3)`, query preparation builds a
16-entry byte lookup table. Entry `m` stores the sum selected by the four mask
bits:

```text
LUT[m] = sum_{t=0..3} bit_t(m) * c_t.
```

The official layout maps the high mask bit to `c0` and the low mask bit to
`c3`. Packed edge nibbles select LUT entries through AVX-512 byte shuffles.
Accumulation returns, for neighbor `i`,

```text
positive_sum_i = sum_{j:b_ij=1} c_j.
```

The scalar signed dot is recovered exactly as

```text
signed_dot_i = 2 * positive_sum_i - sum_j c_j.
```

The packed path then applies the same `triple_x`, `factor_dq`, and `factor_vq`
as the scalar path:

```text
d_hat_i = d(q,u)
        + triple_x_i
        + factor_vq_i * query_lower
        + factor_dq_i * query_width * signed_dot_i.
```

No non-negative clamp is added.

### Running example

Suppose one four-coordinate query group is

```text
(c0,c1,c2,c3) = (7,3,5,2)
```

and one residual sign nibble is `1010`. The LUT value is

```text
LUT[1010] = c0 + c2 = 12.
```

FastScan evaluates this selection for 32 neighbors in parallel. Repeating over
all `Dp/4` groups gives `positive_sum_i`; subtracting the shared query-code sum
converts it to the signed dot used by the scalar formula.

## Local Implementation

The packed estimator is implemented in:

```text
saqlib/baseline/symphonyqg_fastscan.hpp
```

It reproduces:

- the official 32-neighbor batch size;
- MSB-first residual bit packing;
- word-byte reversal and nibble swapping;
- 32-neighbor interleaving;
- 16-entry query LUT construction;
- AVX-512 byte-shuffle accumulation and reduction;
- `2 * positive_sum - sumq` conversion;
- AVX-512 factor combination and distance output.

The graph diagnostic integration is in:

```text
src/profile_graph_frontier.cpp
```

For every fixed root, scalar edge factors are generated once and then packed
once. For every query, the transformed scalar query and packed LUT are generated
once. The profiler reports `symqg_fht_scalar` and `symqg_fht_fastscan`
separately so that any ordering mismatch is visible.

The diagnostic retains scalar edge state alongside packed state only for
validation. A deployable SymphonyQG-style index retains the packed code and
three float factors, not the diagnostic scalar byte-per-sign representation.

## Official-Source Fixture

The fixture generator
`script/reference/symphonyqg_scalar_fixture_generator.cpp` compiles directly
against the pinned SymphonyQG headers. It now records:

- the complete packed query LUT;
- the complete packed edge-code block;
- all 32 positive-code accumulators, including 16 padded lanes;
- packed signed dots;
- packed estimated distances;
- packed final ordering, including a deterministic duplicate-neighbor tie.

The fixture has 16 real neighbors and therefore exercises official padding to a
32-neighbor block. Production `-Ofast` and strict-fp fixtures are both retained
because official query quantization is compiler-mode sensitive at an `lround`
boundary.

The parity tests are in:

```text
unit_test/ut_symphonyqg_fastscan.cpp
```

They cover:

1. byte-for-byte LUT and packed-code parity with official source;
2. all official positive accumulators, signed dots, distances, and ordering;
3. packed-to-scalar signed-dot and distance parity;
4. a 33-neighbor case spanning two packed batches;
5. a GIST-sized `D=960`, `Dp=1024`, 33-neighbor parity case;
6. zero-residual behavior and padded lanes.

## Verification

Release:

```bash
cmake --build /tmp/saq-graph-phase2-build -j \
  --target unit_tests profile_graph_frontier
./bin/unit_tests \
  '--gtest_filter=SymphonyQGFastScan*.*:SymphonyQGScalar*.*'
```

Result: `7/7` tests passed.

ASAN Debug:

```bash
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  cmake --build /tmp/saq-graph-phase2-asan -j \
  --target unit_tests profile_graph_frontier
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
  ./bin/unit_tests \
  '--gtest_filter=SymphonyQGFastScan*.*:SymphonyQGScalar*.*'
```

Result: `7/7` tests passed. An ASAN profiler smoke with degree 8 also passed,
including padding to one 32-neighbor batch. Leak detection remains disabled in
the ptrace-controlled environment; address and use-after-free checks remain
active.

## Storage And Work Model

For padded dimension `Dp` and padded degree `Lp`:

| quantity | amount |
|---|---:|
| packed edge code per root | `Lp * Dp / 8` bytes |
| stored factors per root | `3 * Lp * sizeof(float)` bytes |
| query LUT | `4 * Dp` bytes |
| batches per root scan | `Lp / 32` |
| AVX-512 accumulation iterations per batch | `Dp / 16` |
| code bytes loaded per batch | `4 * Dp` |
| LUT bytes loaded per batch | `4 * Dp` |

Query preparation costs `O(Dp log Dp)` for FHT and `O(Dp)` for quantization and
LUT construction. Index preparation costs `O(E Dp)` for residual signs,
factors, and packing over `E` directed edges. One root scan performs
`(Lp/32) * (Dp/16)` AVX-512 accumulation iterations plus `O(Lp)` factor
combination.

For the GIST setting `Dp=1024`, `L=Lp=32`:

```text
packed code per root:       4096 bytes
three factor arrays:         384 bytes
packed edge payload:        4480 bytes
query LUT:                  4096 bytes
AVX-512 iterations/batch:     64
```

This corresponds to 128 code bytes plus 12 factor bytes per edge. Adjacency IDs
and original vectors are graph storage shared with the comparison and are not
included in this estimator payload.

## Small Real-Data Sanity Run

Configuration:

```text
dataset: GIST sample50k in PCA space
SAQ index: K=512, B=4
exact-kNN subset: 512
degree: 32
queries: 16
roots per query: 8
events: 128
rotation seed: 0
```

Results:

| estimator | code bits only | top-1 disagreement | mean exact-best rank | p90 rank | top-4 containment |
|---|---:|---:|---:|---:|---:|
| historical `symqg_vertex_proxy` | 960 | 0.867188 | 8.85156 | 22 | 0.390625 |
| `symqg_fht_scalar` | 1024 | 0.304688 | 1.54688 | 3 | 0.968750 |
| `symqg_fht_fastscan` | 1024 | 0.304688 | 1.54688 | 3 | 0.968750 |
| `saq_fast` | 832 | 0.453125 | 1.93750 | 4 | 0.914062 |
| `saq_prefix_acc1` | 1472 | 0.046875 | 1.05469 | 1 | 1.000000 |

The scalar and packed rows are identical for every aggregate ordering metric.
The canonical aggregate output is
`docs/saq_symphonyqg_fastscan_sanity_seed0_2026_07_10.csv`.

## Limitations

This run validates packed estimator semantics; it is not an end-to-end graph
result. It still uses an exact-kNN replay graph, independent query-root events,
one rotation seed, and a small subset. It does not reproduce SymphonyQG's
multiple estimates for a vertex reached through different parents or a
path-dependent frontier traversal. The profiler evaluates scalar, packed, and
SAQ paths together, so its wall-clock time is not a standalone QPS comparison.

## Phase Decision

Phase 2 is complete. The scalar and packed paths match pinned official source,
the packed path matches scalar ordering, and the output records transform,
storage, and SIMD-work metadata.

The next task is Phase 3: execute the predeclared fixed-seed same-replay
evaluation and apply the research stop gate. Do not design a graph refinement
policy before that evidence is available.

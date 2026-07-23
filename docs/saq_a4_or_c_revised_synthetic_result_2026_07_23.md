# A4-OR-C revised synthetic admission result

Status: `PASS_A4_OR_C_SYNTHETIC_ONLY`

This result uses the final-model control-validity revision authorized on
2026-07-23. It is separate from, and does not rewrite, the original
`CONTROL_INVALID` result at commit `67009a8`.

## Execution identity

- Branch: `saq-a4-original-reopening-protocol`
- Base commit: `67009a8`
- Source state: uncommitted working-tree revision
- Pinned Faiss:
  `0ca9df4792b173d573044ee14ca0704780176e82`
- Synthetic binary SHA-256:
  `212055b800d7d9fd3242bb879202e4ff8e1f0bfdce0ab8e27a7b89e85383d636`
- Input: deterministic 8,192-by-128 synthetic panel only
- Process policy: one process, one thread, logical CPU 0

The exact stdout is preserved in
`docs/saq_a4_or_c_revised_synthetic_stdout_2026_07_23.txt`.

Key source SHA-256 identities:

| Path | SHA-256 |
| --- | --- |
| `research/a4_or_c/core.cpp` | `8d6e05e4196f9062fc2eeded8fcb9124c98c0c4c2ec737769daec7add6bccb47` |
| `research/a4_or_c/synthetic.cpp` | `838179280c5e3454475ed6a39b4d69a8e28674cdc377b85b6ebf60a121b8e9a0` |
| `research/a4_or_c/synthetic.hpp` | `ac3995e592a41039cc308383d3a3870fd08abccbc9eda453e139d215e9f02c70` |
| `research/a4_or_c/synthetic_main.cpp` | `9e6ca9559321a8f4084a567587c5401f4e9c33f1cc949aae2946af9301373f0c` |
| `research/a4_or_c/tiny_main.cpp` | `b67b4b271101495d32844e29c2c2a808c8daf4b1e9cb8d9c6fc5fc63b7be8d83` |
| `research/a4_or_c/CMakeLists.txt` | `dfc155df127e5f921693afcc72127c7062871a9d00de1f1e6848c61236f5dac8` |

Command:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/a4-or-c-build/a4_or_c_synthetic
```

## Final control validity

All four executions reported:

- P and V shape valid;
- P and V encoding complete and in range;
- zero empty final centers after reassignment;
- zero final center collisions.

Across B4 and B8, P encoded 786,432 row-block labels and V encoded 1,048,576
row-block labels per execution. The intermediate optimizer diagnostics remained
nonzero at `P nsplit=2855` and `V nsplit=8061`; under the revised rule they do
not invalidate complete final models.

## Numeric result

The warmup and all three measured repetitions agreed:

- finite and nonnegative reconstruction: pass;
- D/A allocation order: pass;
- maximum replay discrepancy per row:
  `2.84217e-14`;
- discrepancy limit: `0.000197833`;
- H=1024 versus H=2048 registered contrast decisions: unchanged;
- selected-path near-tie ambiguity: none.

The pre-execution regression suite also passed:

```text
PASS tiny_total=1044 max_objective_error=1.09139e-11
oracle_cleared=43 roundtrips=17408 lookups=17280
```

## Cost result

Three-repetition medians and maxima:

| Measure | Result | Limit |
| --- | ---: | ---: |
| D/A CPU time per synthetic dataset | 928,809,307 us | — |
| Two-dataset projected D/A CPU time | 1,857,618,614 us (30.96 min) | 3,600,000,000 us |
| Support/scientific CPU ratio | 0.00000969393 | 0.25 |
| A-specific/shared-scalar CPU ratio | 0.000000670752 | 0.25 |
| Maximum peak RSS | 233,926,656 bytes | 17,179,869,184 bytes |

All registered cost limits passed. The implementation obtains this result
without changing the scalar objective or candidate set: it reuses temporary DP
buffers and stores interval costs in the access order used by predecessor
scans. Tiny exact outputs remained bit-identical.

## Claim boundary

This is synthetic-only evidence that the original full-word
arbitrary-cardinality representation is numerically executable and affordable
under the frozen A4-OR-C panel and final-model control definition.

It is not natural-data evidence, does not report Recall or query performance,
does not establish compatibility with unchanged SAQ prefix consumption, and
does not by itself establish a publishable contribution. No dataset, query,
ground-truth, index, or prior generated A4 result was read.

Because the source state was not committed, the binary and exact source hashes
must be bound to a commit before this execution is treated as an immutable
reproduction target.

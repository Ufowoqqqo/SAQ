# Phase 1 Correctness Defaults and Regression Verification

## Scope

This note records the correctness prerequisites completed before implementing
the source-aligned SymphonyQG baseline. These changes protect later evaluation;
they are not research contributions.

Phase 1 addresses two previously confirmed failures:

1. a positive 1-bit SAQ segment could fail during code packing;
2. native AVX-512 block reduction could use padded or non-finite lanes when
   deciding whether an entire multi-segment block should be pruned.

It also rejects invalid graph-profiler budgets before signed-to-unsigned
conversion and verifies output streams before writing result files.

## Correctness Contract

The default search configuration is now:

```text
searcher_safe_block_min_mode = 2
```

Mode meanings are:

```text
0 = legacy native AVX-512 reduction, available only by explicit selection
1 = scalar finite minimum over valid lanes
2 = SIMD finite minimum over valid lanes (default)
```

Padded lanes never contribute to modes 1 or 2. If a valid lane contains NaN or
infinity, the searcher reports the invariant violation, disables approximate
pruning for that block, and recomputes all valid candidates from accurate
segment estimates. A non-finite accurate estimate terminates evaluation rather
than silently dropping the candidate.

## Regression Coverage

`unit_test/ut_searcher_correctness.cpp` adds four focused tests:

- scalar/SIMD agreement for every valid-lane count from 1 through 31;
- adversarial minimum locations around lanes 0, 15, 16, and the final valid
  lane, with padded NaNs and infinities;
- valid-lane non-finite detection and conservative no-prune behavior;
- a 37-vector IVF round trip with two positive 64-dimensional 1-bit segments,
  covering construction, serialization, loading, fast estimation, accurate
  estimation, partial-block search, and result stability after loading.

The default `SearcherConfig` mode is also checked explicitly.

## Release Verification

Production build:

```bash
cmake --build build --clean-first -j
```

Focused unit-test build and execution:

```bash
cmake -S . -B /tmp/saq-build-tests \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_UNIT_TESTS=ON \
  -DCMAKE_MODULE_PATH=/tmp/saq-cmake \
  -DGTest_DIR=/tmp/gtest-install/lib64/cmake/GTest
cmake --build /tmp/saq-build-tests -j --target unit_tests
ctest --test-dir /tmp/saq-build-tests --output-on-failure \
  -R "BlockMinCorrectnessTest|SearcherConfigCorrectnessTest|PositiveOneBitSegmentTest"
```

Result:

```text
4/4 focused tests passed
```

GTest 1.14.0 was installed only under `/tmp/gtest-install` from pinned source
revision `f8d7d77c06936315286eb55f8de22cd23c188571`; no dependency files were
added to this repository.

## ASAN Debug Verification

```bash
cmake -S . -B /tmp/saq-build-asan \
  -DCMAKE_BUILD_TYPE=Debug \
  -DDEBUG_WITH_ASAN=ON \
  -DBUILD_UNIT_TESTS=ON \
  -DCMAKE_MODULE_PATH=/tmp/saq-cmake \
  -DGTest_DIR=/tmp/gtest-install/lib64/cmake/GTest
cmake --build /tmp/saq-build-asan -j
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 ./bin/unit_tests \
  --gtest_filter=BlockMinCorrectnessTest.*:SearcherConfigCorrectnessTest.*:PositiveOneBitSegmentTest.*
```

Result:

```text
4/4 focused tests passed with AddressSanitizer enabled
```

LeakSanitizer cannot run in the current ptrace-controlled execution
environment, so leak detection was disabled. AddressSanitizer bounds and
use-after-free checks remained enabled.

## Graph-Profiler Input Validation

```bash
./bin/profile_graph_frontier -graph_subset=-1
```

The binary terminates before loading data or converting the value to `size_t`:

```text
Check failed: FLAGS_graph_subset > 1 (-1 vs. 1)
-graph_subset must be greater than 1
```

Equivalent positivity checks cover graph degree, query count, roots per query,
and top-L maximum; the event cap must be non-negative.

A successful output-stream smoke evaluation used:

```bash
./bin/profile_graph_frontier \
  -dataset=gist_sample50k -K=512 -B=4 -enable_PCA=true \
  -graph_subset=64 -graph_degree=8 \
  -graph_max_queries=1 -graph_roots_per_query=1 \
  -graph_output_prefix=/tmp/saq-phase1-profiler/smoke
```

The aggregate CSV, event CSV, and Markdown summary were all created and
verified as non-empty files.

## Full GIST B=3 Smoke Evaluation

The smoke root used symlinks to the existing full-GIST PCA/IVF preparation
artifacts under `/tmp/saq-run/data/gist_full`, while writing a fresh index under
`/tmp/saq-phase1-smoke`.

Build:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full -K=4096 -B=3 -enable_PCA=true \
  -num_threads=32 -logtostderr=1
```

The current code generated and materialized the expected positive 1-bit plan:

```text
64:9,192:5,320:3,192:1,192:0
```

Observed indexing time was `2.0864 s`. This timing is a smoke-run observation,
not a performance claim.

Load/search:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_full -K=4096 -B=3 -enable_PCA=true \
  -fix_nprobe=1 -fix_thread=1 -logtostderr=1
```

The index loaded successfully and all ten 1,000-query repetitions completed
with identical `R@100 = 0.09022`. The output suffix
`_safeblockminsimd` confirms that mode 2 was selected without an explicit
searcher flag. The low-recall `nprobe=1` point is used only as a deterministic
search smoke evaluation.

## Decision

Phase 1 passes its acceptance criteria:

- correct multi-segment search requires no extra CLI flag;
- positive 1-bit packing and finite valid-lane minima have focused regression
  coverage;
- Release and ASAN Debug builds pass;
- full GIST/K4096/B=3 completes fresh build, load, and search with its positive
  1-bit segment.

The next active task is Phase 2: implement and parity-test a deterministic,
source-aligned SymphonyQG estimator with random-sign FHT and power-of-two
padding.

# A4-OR-C Local Guidance

## Scientific scope

This directory contains the isolated A4-OR-C synthetic numerical and cost
admission for the original full-word arbitrary-cardinality mixed-radix idea.
It tests a new representation/query-consumer primitive; it does not modify or
claim compatibility with unchanged SAQ.

Implement only:

- deterministic rank histograms at `H=1024` and `H=2048`;
- native binary64 contiguous scalar DP with frozen tie/ambiguity semantics;
- dyadic (`D`) and arbitrary-cardinality (`A`) pair allocation;
- mixed-radix packing and full-word lookup parity;
- ordinary PQ (`P`) and two-dimensional block-VQ (`V`) controls through pinned
  Faiss; and
- tiny exact checks plus the deterministic 8,192-by-128 synthetic admission.

Do not add prefix semantics, progressive decoding, pruning, learned binary
labels, query adaptation, or natural-data evaluation.

## Dependencies

- Use only the standard library, Boost multiprecision for bounded tiny exact
  references, and pinned `third_party/faiss` at
  `0ca9df4792b173d573044ee14ca0704780176e82`.
- Production DP remains binary64. Do not use epsilon comparisons, `long
  double`, or arbitrary precision in the production path.
- Tiny exact arithmetic must remain isolated from production decisions except
  for validating a frozen tiny fixture.
- Do not import, link, or execute old A4 runners, verifiers, GMP trainers,
  evidence frameworks, or custom block-VQ code.

## Read/write boundaries

Read and write files in `research/a4_or_c/`. Read the root `TASK.md`, active
A4-OR-C documents it names, repository build configuration needed for this
target, and pinned Faiss source. Use historical A4 code only as a read-only
semantic reference.

Do not modify `saqlib/`, `src/`, `script/`, `unit_test/`, SAQ/CAQ formats,
estimators, packing, or search. Keep build products in
`/tmp/a4-or-c-build`, not in the repository or Faiss submodule.

## Forbidden data and artifacts

Do not read `data/`, `results/`, or `bin/`; GIST or CIFAR files; centroids or
cluster IDs; benchmark queries or ground truth; generated indexes; ignored or
untracked prior A4 outputs; or old A4 runtime/capture/cache artifacts.

Only generated inputs permitted here are the frozen tiny fixtures and the
deterministic same-shape synthetic panel. A4-OR-B, benchmark queries, Recall,
and native query evaluation are outside scope.

## Build and test

```bash
cmake -S research/a4_or_c -B /tmp/a4-or-c-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF \
  -DFAISS_ENABLE_C_API=OFF -DFAISS_ENABLE_EXTRAS=OFF \
  -DFAISS_ENABLE_GPU=OFF -DFAISS_ENABLE_MKL=OFF \
  -DFAISS_ENABLE_PYTHON=OFF -DFAISS_ENABLE_RAFT=OFF \
  -DFAISS_OPT_LEVEL=generic -DBLA_VENDOR=OpenBLAS
cmake --build /tmp/a4-or-c-build --target a4_or_c_tiny -j 1
ctest --test-dir /tmp/a4-or-c-build --output-on-failure
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 /tmp/a4-or-c-build/a4_or_c_tiny
```

Fix compilation and correctness defects within scope. Tiny tests must cover
exact objective and tie parity, the `(3,5)` allocation witness, both `D/A`
allocation arms, mixed-radix valid/invalid addresses, direct lookup parity,
candidate-order invariance, floating-point environment, and ambiguity
handling.

## Synthetic experiment and resources

After tiny correctness passes, run only the frozen 8,192-row, 128-coordinate,
single-process/single-thread synthetic `D/A/P/V` admission. Use logical CPU 0,
one warmup and three measured repetitions. Keep JSON, logging, hashing, and
provenance outside timed regions.

Limits:

- 16 GiB peak RSS per arm;
- one CPU-hour projected `D/A` construction;
- support CPU at most 25% of scientific CPU;
- A-specific allocation/packing CPU at most 25% of shared scalar fitting;
- 350--800 scientific-core lines, excluding Faiss; and
- support/output code at most `max(800, 2 * scientific_core)`.

## Local done criteria

This directory is done for A4-OR-C when the isolated Release build and complete
tiny suite pass, all frozen synthetic `D/A/P/V` arms either complete within the
limits or honestly fail a fixed condition, and the commands, seeds, resource
measurements, and claim boundaries are reported. A synthetic pass does not
authorize natural data, queries, A4-OR-B, or an SAQ/method claim.

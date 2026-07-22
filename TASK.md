# Active Task: A4-OR-C Synthetic Admission

## Branch and base

- Active branch: `saq-a4-original-reopening-protocol`
- Research base: `saq-a4-r0-static-gate@617ad25`
- Reviewed reopening protocol parent: `7249dd6`
- Current implementation commit: local `841668c` (not pushed at the time this
  task file was rewritten)

This file describes only the active A4-OR-C work. A4-V2 chronology is archived
under `docs/history/` and grants no authority.

## Research question

Can the original full-word arbitrary-cardinality mixed-radix idea use a
production-like histogram/binary64 construction, with forced dyadic (`D`),
arbitrary (`A`), ordinary PQ (`P`), and two-dimensional block-VQ (`V`) arms,
and pass the frozen tiny correctness plus deterministic same-shape synthetic
cost admission without natural data or query access?

This is a new representation and query consumer, not an encoder-only change to
unchanged SAQ. It has no prefix semantics, progressive decoding, pruning,
learned label permutation, or query-adaptive rule.

## Hypothesis and decision

The testable hypothesis is that binary64 rank-histogram scalar curves and
mixed-radix allocation preserve exact tiny semantics while replacing the old
arbitrary-precision/evidence-heavy construction with an affordable native
path. Passing requires correct `D/A/P/V` shapes, representation parity,
numeric robustness, memory below 16 GiB, and projected `D/A` construction CPU
at or below one hour.

A pass establishes only `A4-OR-C` synthetic feasibility. It is not natural-data
evidence, Recall/QPS evidence, novelty, an SAQ improvement, or authorization to
enter A4-OR-B. An honest failure is also a completed A4-OR-C result.

## Active documents and source

- Scientific protocol: `docs/saq_attempt4_original_reopening_protocol_2026_07_22.md`
- Scope authorization: `docs/saq_a4_or_c_authorization_2026_07_22.md`
- Frozen technical specification: `docs/saq_a4_or_c_machine_contract_2026_07_22.json`
- Existing output schema, used only if emitting its registered artifacts:
  `docs/saq_a4_or_c_output_schema_2026_07_22.json`
- Current implementation: `research/a4_or_c/`
- Pinned dependency: `third_party/faiss` at
  `0ca9df4792b173d573044ee14ca0704780176e82`
- Local restrictions: `research/a4_or_c/AGENTS.md`

The protocol and technical specification define scientific semantics. They do
not require new authorization documents or per-step gates.

## Allowed reads and writes

Allowed reads:

- the active files listed above;
- repository build configuration and headers needed to compile the isolated
  prototype;
- official pinned Faiss source under `third_party/faiss`;
- historical A4 source only as a read-only semantic reference, never as an
  imported, linked, or executed implementation; and
- primary papers needed to evaluate the idea or interpret results.

Allowed writes:

- `research/a4_or_c/` scientific implementation and tests;
- the pinned `third_party/faiss` gitlink/configuration, without vendoring build
  products;
- a dedicated out-of-tree build directory such as `/tmp/a4-or-c-build`; and
- the already registered A4-OR-C synthetic artifact directory if and only if
  the existing output schema requires those outputs.

Do not modify `saqlib/`, `src/`, `script/`, `unit_test/`, SAQ/CAQ index formats,
estimators, packing, or search paths during A4-OR-C.

## Forbidden reads and actions

Do not open or inspect:

- `data/`, `results/`, or `bin/`;
- GIST, CIFAR, centroids, cluster IDs, benchmark queries, ground truth, or
  generated indexes;
- ignored or untracked prior A4 outcome artifacts; or
- old A4-1S/V2 runners, CLIs, verifiers, archives, evidence frameworks, exact
  GMP trainers, or custom block-VQ trainers as executable dependencies.

Do not run A4-OR-B, native query evaluation, benchmark-query evaluation, or
natural-data experiments. Do not transform the candidate into a prefix,
progressive, pruning, or query-adaptive method.

## Allowed build, test, and experiment commands

Configure and build the isolated Release target with the frozen single-thread,
CPU-only Faiss/OpenBLAS settings:

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
```

The tiny executable may be run with:

```bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 /tmp/a4-or-c-build/a4_or_c_tiny
```

After tiny correctness passes, it is permitted to implement and run only the
deterministic 8,192-by-128 same-shape synthetic `D/A/P/V` admission defined by
the active specification. Record exact commands, seeds, environment, three
measured repetitions after one warmup, CPU/wall time, peak RSS, and limitations.

## Resource budget

- One process and one thread, pinned to logical CPU 0.
- `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
  `OMP_DYNAMIC=FALSE`.
- Peak RSS ceiling: 16 GiB per arm.
- Projected two-dataset `D/A` construction ceiling: one CPU-hour.
- Support CPU ceiling: 25% of scientific training CPU.
- A-specific allocation/packing CPU ceiling: 25% of shared scalar fitting.
- Scientific core target: 350--800 net lines, excluding Faiss.
- Support/output code ceiling: `max(800, 2 * scientific_core)`.

Stop before exceeding these resource limits. Ordinary compilation, test, or
correctness failures should be diagnosed and fixed within the same task.

## Current blocker

Independent review of `841668c` found three correctness defects that invalidate
its printed tiny PASS:

1. Histogram representatives are converted to binary32 before Welford/DP;
   production must retain binary64 representatives until final selected-center
   serialization.
2. The tiny executable does not exercise `allocate_pair`, the frozen `(3,5)`
   zero-error witness, or exhaustive `D/A` allocation objective and tie parity.
3. The exact oracle uses the wrong multi-boundary tie ordering, and fixture
   weight enumeration does not match the bound lexicographic case order.

These are implementation defects, not evidence against the hypothesis.

## Deliverables and done criteria

Deliverables:

- a minimal native implementation under `research/a4_or_c/`;
- deterministic tiny exact, allocation, mixed-radix, and direct-lookup tests;
- forced synthetic `D/A/P/V` arms with frozen shapes and dependency;
- reproducible build/run commands and resource measurements; and
- a concise interpretation of pass or failure without natural-data claims.

A4-OR-C is done when either:

- all frozen tiny, representation, control, sensitivity, ambiguity, memory,
  support, and cost conditions pass; or
- a condition honestly fails after genuine implementation defects are fixed,
  with the failure and its scientific limitation reported.

No A4-OR-C result authorizes later base or query work.

## Concrete next action

Fix the three reviewed correctness defects in `research/a4_or_c/`, rebuild,
and rerun the complete tiny suite. If it passes, review the corrected code and
then implement the smallest full same-shape synthetic `D/A/P/V` admission.

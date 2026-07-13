# AGENTS.md

Durable guidance for Codex sessions on the
`saq-caq-corrected-oracle-v2` branch.

## Research Frame

Work as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a repository. Code and scripts
are supporting tools. Every task should first answer: what SAQ limitation is
being tested, what evidence it adds, what overhead it introduces, and how a
strict SIGMOD/VLDB/ICDE reviewer would evaluate it.

The objective is a database top-conference-level contribution. A nonzero
encoding-objective gap is insufficient unless it is SAQ-specific, materially
affects the unchanged estimator, has controlled construction overhead, and
moves the CAQ--E-RaBitQ frontier by more than parameter tuning.

The direction is query-unaware. Base/index data may be used for fitting and
limitation measurement. Held-out benchmark queries may be used only in a later
evaluation whose encoder and rules were frozen beforehand.

Before proposing another idea, review the closest primary work and state what
it already solves, what gap remains, and why the proposal is not a direct
composition.

## V2 Authorization And Scope

**The v1 finite-round CAQ screen stopped at CO-0A.** The pinned official
Extended-RaBitQ encoder failed the predeclared exact-oracle parity rule. It
misses a globally optimal code on a reachable `D=64, B=3` input, its public IVF
path omits bit widths required by the frozen SAQ plans, and its `uint8_t`
output narrows the `B=11` magnitude code. This is an artifact-validation
failure, not evidence about CAQ regret on SAQ data.

The authoritative review and decision documents are:

- `docs/saq_limitation_primary_source_review_2026_07_11.md`;
- `docs/saq_limitation_primary_sources_2026_07_11.json`;
- `docs/saq_next_direction_go_no_go_memo_2026_07_11.md`;
- `docs/saq_caq_co0a_official_source_parity_2026_07_11.md`;
- `docs/saq_caq_co0a_artifacts_2026_07_11/source_parity_result.json`;
- `docs/saq_caq_co0_v2_reopening_corrected_oracle_protocol_2026_07_11.md`;
- `docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_synthetic_validation_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_a2_synthetic_cost_design_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a2_synthetic_cost_evidence_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a2_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`;
- `docs/saq_caq_co0_v2_b0_preparation_spec_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json`;
- `docs/saq_caq_co0_v2_b0_final_preregistration_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_preregistration_evidence_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_b1_synthetic_runner_validation_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b1_rotation_build_correction_2026_07_12.md`;
- `docs/saq_caq_co0_v2_b1_rotation_build_correction_artifacts_2026_07_12/`;
- `docs/saq_caq_co0_v2_b1_registered_evidence_2026_07_12.md`;
- `docs/saq_caq_co0_v2_b1_registered_artifacts_2026_07_12/`.

The completed sequence is:

```text
v1 CO-0A  official source pinned and tested -> FAIL, preserved
V2-A0     proof/specification review -> PASS
V2-A1     synthetic exact-oracle validation -> PASS
V2-A2     synthetic cost study -> PASS
V2-B0     provenance/preregistration only -> PASS
V2-B1-I   runner/summarizer synthetic validation -> PASS
V2-B1-E0  registered preflight -> STOPPED before encoding
V2-B1-R   rotation build correction validation -> PASS
V2-B1-E1  registered rerun -> COMPLETE
V2-B1-S   frozen 24-hypothesis analysis -> CONDITIONAL_PASS
review    one-shell repair -> CONDITIONAL_GO_FOR_SYNTHETIC_PROTOTYPE
synthetic one-shell correctness -> PASS
synthetic one-shell complexity -> NO_GO_ON_COMPLEXITY
method    low-cost repair -> NOT ESTABLISHED
```

The user explicitly authorized V2-B0 on 2026-07-11; B0 passed without encoder
execution. It read and hash-verified only the two frozen one-column
cluster-assignment files needed to construct sample inventories. The first B1
command was later authorized and hash-verified the registered base, centroid,
variance, assignment, and inventory artifacts. It stopped on a rotation hash
mismatch with zero encoder rows and zero pair rows. Benchmark queries, ground
truth, indexes, and prior encoder outputs remained unread. The instrument-only
correction was separately authorized and passed synthetic Release/ASAN
validation. The registered rerun then completed and its frozen summarizer
returned `CONDITIONAL_PASS`: all 24 Holm tests and all seed checks pass.
Benchmark queries, ground truth, and indexes remain unread. The result
establishes a limitation only; it does not authorize post-hoc rescue sweeps or
constitute a method contribution.

## Frozen B1 Finding

For
`R_arm = sum(f_arm-f_exact) / sum(f_init-f_exact)`, the leading SAQ segments
give `R_r6=0.944994` (GIST `64@11`) and `0.790078` (CIFAR `64@9`). Continuing
the identical coordinate rule to a local fixed point gives `0.944982` and
`0.789792`. All 18 low-bit/whole-view amplification controls and both
unchanged-estimator tests pass the shared 24-hypothesis Holm gate. Exact codes
reduce the normalized base-pair estimator error by 13.42% and 8.28%, but exact
labeling costs 272.9x the measured `r=6` CPU.

Interpret high `R` correctly: most initialization-to-exact error-factor
opportunity remains; it does not mean CAQ is close to exact. The result is
base-only and makes no recall/QPS claim. `CONDITIONAL_PASS` authorizes only a
bounded related-work/theory review of low-cost deterministic mechanisms. Do
not implement a repair, open benchmark queries, or add a sweep before that
novelty/complexity review is written.

That review is written in
`docs/saq_caq_low_cost_repair_theory_review_2026_07_12.md`, with its source
ledger in `docs/saq_caq_low_cost_repair_sources_2026_07_12.json`. It
conditionally authorized a synthetic-only exact radius-one Cartesian shell
prototype. The shell is the product of each incumbent magnitude code and its
immediate legal neighbors, solved with at most `2D` shared-scale events. The
prototype passes exact/brute-force parity, but its fixed-width realization
requires `4.579x` to `8.169x` total `CAQ + shell` CPU across the four frozen
synthetic rows. It therefore fails the `2x` gate and is closed as
`NO_GO_ON_COMPLEXITY` before any base-data evaluation.

The authoritative negative-evidence note is
`docs/saq_caq_one_shell_synthetic_falsification_2026_07_12.md`, with canonical
output in
`docs/saq_caq_one_shell_synthetic_artifacts_2026_07_12/validation_result.json`.
Do not increase the shell radius, repeat the shell to convergence, add scale
or random restarts, introduce an acceptance threshold, optimize it into the
production encoder, or read dataset artifacts to rescue the failed gate.

## Project-Level Pivot

The project-wide decision is
`STOP_SAQ_CENTRIC_INCREMENTAL_METHOD_SEARCH`. Its authoritative rationale is
`docs/saq_caq_limitation_repair_closure_and_project_pivot_2026_07_13.md`.

Retain SAQ as a strong baseline and the completed branches as limitation
evidence. Do not default to another SAQ-specific planner objective, candidate
family, local plan, encoder move, transform, layout, bound, or search schedule.
The next authorized work is a problem-first primary-source selection review,
not implementation.

A future direction must remain meaningful across at least two independent
competitive baselines, identify a mechanism-level gap not occupied by the
closest work, account for build/storage/query overhead from the start, and
define a small falsification study. Open a clean branch from
`saq-correctness-base` only after that review returns `GO`; otherwise keep this
branch closed.

## Frozen Architecture

Keep the comparison inside the existing SAQ representation:

```text
fixed PCA view and IVF assignments
fixed residual vectors
one global SAQ segment/bit plan
same segment rotations and padding
one code per vector segment
same serialized bit widths and factors
same full-code estimator and query work
no per-cluster plan ids or mixed dispatch
no benchmark-query tuning
```

The independent variable is the per-segment encoder only. Do not change the
plan, transform, candidate generation, index format, or search schedule.

## Frozen Rotation Build

The registered rotation bytes were generated with GCC 11.5.0 under the B0
Release profile `-O3 -DNDEBUG -fno-fast-math -ffp-contract=off` and without
AVX/FMA. Eigen Householder QR is byte-sensitive to both optimization level and
SIMD flags. Keep rotation generation in
`src/caq_co0_v2_frozen_rotation.cpp`; do not move it back into the
SIMD-compiled runner.

The frozen unit must write into caller-owned row-major float buffers so Eigen
objects do not cross build profiles. The CAQ encoder, packer, and estimator
must retain their AVX2/FMA/AVX512 flags. Every Release and ASAN review must
report `rotation_hash_checks = 27`; a mismatch stops execution before an
encoder call and cannot be relaxed with numerical tolerance.

## Corrected-Oracle Requirement

The v1 official-source failure remains final under its own contract. V2 uses a
new instrument named the independent complete-event oracle; never describe it
as the pinned official encoder or as a novel quantizer.

V2-A0/V2-A1 must satisfy the protocol's proof and exactness obligations:

1. exact binary32 decomposition into a common power of two and integers;
2. exact event ordering by integer cross products;
3. exact squared-cosine objective comparison without floating thresholds;
4. initial-state, zero, tie, padding, subnormal, and `B=11` semantics;
5. complete brute-force parity on every enumerable fixture;
6. independent centered-grid, cosine, rescale, and estimator checks; and
7. Release and sanitizer/debug validation.

Do not depend on the official private-method access hack, bounded enumeration
window, `1e-5` epsilon, or byte magnitude output. A failed proof or synthetic
parity check stops V2 before any cost or dataset stage.

## Important Current-Code Semantics

- `QuantSingleConfig::caq_adj_rd_lmt` defaults to `6`.
- Despite the config comment, setting `caq_adj_rd_lmt=0` currently skips code
  adjustment; it does not execute an unlimited run. A local-fixed-point
  diagnostic must call the same rule explicitly until no coordinate changes.
- CAQ stores `fac_error` in `ExFactor.error`, but the current search path does
  not read that field. The full-code estimator uses the code and `rescale`.
  Therefore a smaller oracle error factor alone cannot pass `CO-0`.
- Current IVF SAQ reads the MSB fast code and then all remaining bits of a
  segment. It does not consume arbitrary `2..B-1` bit prefixes.

Treat any correctness issue found during parity as a separate implementation
finding, never as the research contribution.

## V2-A2 Cost Boundary

V2-A2 measures only the nine positive-bit `(D,B)` cells frozen in the parent
protocol. Use the three deterministic profiles and the feasibility equation
in `docs/saq_caq_co0_v2_a2_synthetic_cost_design_2026_07_11.md`. Do not add a
random distribution, seed sweep, repetition threshold, dataset-derived
profile, or easier replacement cell. The target sample-size rule and one
CPU-day ceiling are experimental resource decisions, not method parameters.

Passing V2-A2 establishes only that later exact labeling is computationally
feasible. It gives no evidence that finite-round CAQ has regret.

## V2-B0 Structural-Read Reconciliation

The parent protocol requires B0 to commit deterministic sample/pair
inventories, but also states that B1 reads base/index artifacts. Resolve this
narrowly: B0 may hash and parse only the frozen `D=1` IVF cluster-id files.
Their contents are assignment labels, not vector magnitudes or encoder
outputs. All float-vector artifact hashes come from pre-existing provenance
and must be verified against bytes only in B1 before any encoding.

The exact paths, expected hashes, hash-key serialization, rotation seed
mapping, and allowed output files are frozen in:

- `docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`;
- `docs/saq_caq_co0_v2_b0_preparation_spec_2026_07_11.md`.

No other structural exception is implied.

## V2-B Boundary

V2-B0 and the completed B1 result are frozen. The registered regimes were:

```text
GIST sample50k, K=512, B=4:
  64@11 | 192@6 | 320@4 | 256@2 | 128@0

CIFAR60k, K=512, B=4:
  64@9 | 192@5 | 128@3 | 128@0
```

Use a deterministic cluster-stratified base sample and fixed rotation seeds.
Choose sample size only through a synthetic-vector oracle-cost dry run. Do not
inspect dataset objective gaps to select samples, cells, seeds, thresholds, or
controls.

Required encoder arms are LVQ initialization, production `r=6`, the
identical coordinate rule to local fixed point, and the independently
validated corrected oracle. Required attribution controls would be
same-segment uniform `B=4` and the whole positive-dimensional residual view at
uniform `B=4`. Do not implement these dataset arms during V2-A0/V2-A1.

The gate must measure cosine/objective regret, code equality, achieved
rescale/error factors, accepted moves/rounds, and encoding work. It must also
use a disjoint hash-frozen base-residual-pair estimator proxy under the
unchanged query-side formula. Permanent and transient bytes must be counted.

## Historical Boundaries

This branch starts from `saq-correctness-base`, preserving only confirmed
correctness fixes needed for reliable evaluation:

- positive 1-bit segment packing support;
- padded-lane finite block-min search support.

Treat other branches as negative evidence, not code to migrate:

- `saq-boundary-audit`: empirical fixed-policy scoring;
- `saq-structural-followup`: mixed shared local plans;
- `saq-global-cost-dp`: static global segment-cost DP;
- `saq-planner-objective-analysis`: fac-error planning and small search-loop
  changes;
- `saq-graph-traversal-analysis`: graph integration stopped on work overhead;
- `saq-transform-analysis`: PCA-objective replacement failed replication;
- `saq-lossy-projection-analysis`: exact lossy surrogate failed Gate A.

Do not migrate their runners, profilers, policy scorers, planner variants,
projected-distance diagnostics, or generated artifacts unless a later note
justifies one minimal dependency.

## Repository Layout

- `saqlib/`: C++ SAQ/CAQ implementation, quantizers, estimators, IVF helpers,
  and search logic.
- `src/`: C++ binaries.
- `script/`: small research-question-driven helpers.
- `unit_test/`: source and parity regression tests.
- `validation/caq_corrected_oracle/`: dependency-isolated CMake entry for the
  corrected-oracle synthetic validator.
- `data/`, `results/`, `bin/`, `build/`: generated/local-output areas; do not
  commit datasets, indexes, binaries, or build outputs.
- `docs/`: research reviews, protocols, evidence, and source metadata.
- `third_party/`: pinned source snapshots or submodules only when license and
  provenance are recorded; do not vendor generated build products.

## Build And Verification

Default build:

```bash
mkdir -p build bin
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Before committing:

```bash
git diff --check
cmake --build build -j
git status --short --branch
```

For corrected-oracle or B1-instrument code, run the standalone suite in
Release and a sanitizer/debug build. Record exact commands, compiler flags,
output counters, and outcomes in the stage evidence note.

```bash
cmake -S validation/caq_corrected_oracle -B /tmp/saq-oracle-release \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-oracle-release --parallel
ctest --test-dir /tmp/saq-oracle-release --output-on-failure

cmake -S validation/caq_corrected_oracle -B /tmp/saq-oracle-asan \
  -DCMAKE_BUILD_TYPE=Debug -DCAQ_CORRECTED_ORACLE_ENABLE_ASAN=ON
cmake --build /tmp/saq-oracle-asan --parallel
ctest --test-dir /tmp/saq-oracle-asan --output-on-failure

python -m unittest script.test_summarize_caq_co0_v2_b1
```

## Do-Not Rules

- Do not rerun or replace the completed registered V2-B1 result.
- Do not reopen per-vector outputs to invent exclusions, thresholds, controls,
  or rescue hypotheses. Use the frozen summary for the decision and label any
  later aggregate as descriptive.
- Do not read benchmark queries, ground truth, indexes, or prior encoder
  outputs in CO-0 v2.
- Do not write or execute the old CO-0B preregistration after the CO-0A
  failure.
- Do not describe the independent full-event enumerator as the pinned official
  E-RaBitQ encoder.
- Do not write or execute V2-B before V2-A2 passes and a separate V2-B
  preregistration is committed.
- Do not treat a nonzero exact-objective gap as a contribution.
- Do not pass the gate on `fac_error` alone; the field is unused by search.
- Do not change `r` and present it as a method.
- Do not use ordinary exact E-RaBitQ fallback as the proposed contribution.
- Do not continue the radius-one shell after its frozen synthetic complexity
  gate failed; preserve it only as a diagnostic and negative result.
- Do not begin another SAQ-centric incremental method after the project-level
  pivot decision. Complete a problem-first related-work gate before coding.
- Do not sweep datasets, bits, dimensions, segment boundaries, rotations, or
  thresholds to rescue a failed gate.
- Do not change the global SAQ plan, index format, or query estimator in CO-0.
- Do not add query-trained triggers, per-cluster state, plan ids, or mixed
  dispatch.
- Do not hide exact-oracle sort/enumeration work or transient memory.
- Do not present bug fixes, source parity, or tooling as research
  contributions.
- Do not introduce unjustified hyperparameters. Each must have a
  mechanism-level scale, a fixed base-only selection rule, and sensitivity or
  ablation evidence.

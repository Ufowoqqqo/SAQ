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
- `docs/saq_caq_co0_v2_a1_artifacts_2026_07_11/`.

The completed sequence is:

```text
v1 CO-0A  official source pinned and tested -> FAIL, preserved
V2-A0     proof/specification review -> PASS
V2-A1     synthetic exact-oracle validation -> PASS
V2-A2     synthetic cost study -> NOT YET AUTHORIZED
V2-B      dataset preregistration/run -> NOT AUTHORIZED
data      GIST/CIFAR outputs -> NOT INSPECTED
```

The user explicitly authorized V2-A0/V2-A1 on 2026-07-11; both stages passed.
The current authorization now stops at that boundary. This is measurement
infrastructure, not an active CAQ method. Do not design a certificate, repair,
planner, or query policy. Do not read GIST, CIFAR, another dataset, benchmark
queries, or ground truth before a later stage is explicitly authorized.

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

## V2-B Boundary (Not Authorized)

The following boundary is retained for provenance only. V2-B remains
unauthorized until V2-A0--A2 pass and a separate preregistration is committed.
The planned regimes are:

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

Required encoder arms would be LVQ initialization, production `r=6`, the
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

For corrected-oracle code, run the synthetic validator in Release and a
sanitizer/debug build. Record exact commands, compiler flags, output counters,
and outcomes in the V2-A1 evidence note.

```bash
cmake -S validation/caq_corrected_oracle -B /tmp/saq-oracle-release \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-oracle-release --parallel
ctest --test-dir /tmp/saq-oracle-release --output-on-failure

cmake -S validation/caq_corrected_oracle -B /tmp/saq-oracle-asan \
  -DCMAKE_BUILD_TYPE=Debug -DCAQ_CORRECTED_ORACLE_ENABLE_ASAN=ON
cmake --build /tmp/saq-oracle-asan --parallel
ctest --test-dir /tmp/saq-oracle-asan --output-on-failure
```

## Do-Not Rules

- Do not proceed beyond V2-A1 under the current authorization.
- Do not read dataset artifacts, benchmark queries, or ground truth during
  V2-A0/V2-A1.
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

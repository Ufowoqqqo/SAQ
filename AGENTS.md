# AGENTS.md

Durable guidance for Codex sessions on the
`saq-caq-optimality-analysis` branch.

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

## CO-0 Outcome

**The finite-round CAQ direction stopped at CO-0A.** The pinned official
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
- `docs/saq_caq_co0a_artifacts_2026_07_11/source_parity_result.json`.

The completed sequence is:

```text
CO-0A  official source pinned and tested -> FAIL
CO-0B  preregistration -> NOT WRITTEN / NOT AUTHORIZED
data   GIST/CIFAR outputs -> NOT INSPECTED
```

There is no active method direction on this branch. Preserve the failure
evidence and do not design a certificate, repair, new planner, or query policy.
Reopening requires explicit authorization for a new protocol whose oracle is
clearly named as a paper-corrected, widened independent implementation rather
than official-source parity.

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

## Source-Parity Requirement And Result

Do not implement an "exact" oracle from the SAQ prose alone. Pin the official
Extended-RaBitQ artifact by repository URL and commit, record its license and
build flags, and review the relevant encoder source.

Before reading any GIST/CIFAR `CO-0` result:

1. exhaustively enumerate tiny predeclared `(D,B)` codebooks;
2. verify that official E-RaBitQ reaches the same maximum cosine;
3. verify the normalization/code mapping used by SAQ's codebook-equivalence
   lemma;
4. independently recompute code, cosine, rescale, and error-factor quantities
   in float64;
5. reject parity if clipping, padding, bit order, or numeric semantics change
   the feasible codebook.

Source parity is artifact validation, not research evidence.

This requirement was executed on 2026-07-11 and failed. Do not relax it after
the result. In particular, the independent full-event enumerator passed tiny
complete-codebook tests, but substituting it now would change the frozen oracle
contract.

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

## Frozen CO-0B Boundary (Not Authorized)

The following boundary is retained for provenance only. It would have applied
after a CO-0A pass; that pass did not occur, so no preregistration or dataset
measurement may be produced under it. The planned regimes were:

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

Required encoder arms are LVQ initialization, production `r=6`, the identical
coordinate rule to local fixed point, and the source-validated exact E-RaBitQ
oracle. Required attribution controls are same-segment uniform `B=4` and the
whole positive-dimensional residual view at uniform `B=4`. Do not sweep other
bits, dimensions, plans, or boundaries.

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

For source-parity code, also run the tiny exhaustive fixtures in Release and a
sanitizer/debug build when feasible. Record the exact commands and outcomes in
the parity note.

## Do-Not Rules

- Do not write or execute the old CO-0B preregistration after the CO-0A
  failure.
- Do not describe the independent full-event enumerator as the pinned official
  E-RaBitQ encoder.
- Do not read benchmark-query results before `CO-0A` parity and the `CO-0B`
  preregistration are committed.
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

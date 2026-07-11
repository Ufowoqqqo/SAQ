# AGENTS.md

Durable guidance for Codex sessions on the
`saq-lossy-projection-analysis` branch.

## Research Frame

Work as a doctoral researcher developing a publishable database-systems
contribution, not as a programmer optimizing a repository. Code and scripts
are supporting tools. Every task should first answer: what SAQ limitation is
being tested, what evidence it adds, what overhead it introduces, and how a
strict SIGMOD/VLDB/ICDE reviewer would evaluate it.

The objective is a database top-conference-level research work. Small
Recall/QPS gains are insufficient unless the method exposes a clear
SAQ-specific limitation, has controlled overhead, survives the closest
baselines, and is more than a composition of existing projection and
quantization techniques.

The active direction is query-unaware. Fit projections, dimensions, plans,
losses, and thresholds from base/index data only. Held-out benchmark queries
may be used only for evaluation, never to choose a reported design.

Use research-paper terminology in new notes, summaries, slides, and task
descriptions. Prefer words such as "review", "analyze", "evaluate", "survey",
"evidence", and "limitations". Avoid software-maintenance framing unless the
topic is literally code correctness or repository maintenance.

## Active Direction

**Collision-first analysis of physical lossy projection with SAQ.** Study
whether materializing a `D -> d` projected representation can reduce SAQ's
query transform, code, metadata, and distance-estimation work while preserving
original-space ranking quality, and whether any benefit is specifically due to
SAQ's heterogeneous segments and progressive mixed-bit estimator.

The research question is:

```text
At matched actual bytes and complete query work, does physical D -> d
projection interact non-separably with SAQ's segmented mixed-bit CAQ and
progressive prefixes, producing an original-space Recall-QPS-bytes point that
is not explained or dominated by full-D SAQ, its logical 0-bit tail,
truncated PCA, ASH, MRQ, LeanVec-ID, or DADE/ADSampling-style controls?
```

**Status: LP-0 Gate A completed and failed; the registered
GIST/`d=576`/`B=4` line is closed and no method claim exists.** The
authoritative proposal, review, protocol, and evidence are:

- `docs/saq_lossy_projection_research_proposal_2026_07_11.md`;
- `docs/saq_lossy_projection_related_work_2026_07_11.md`;
- `docs/saq_lossy_projection_lp0_preregistration_2026_07_11.md`;
- `docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md`.

Do not run LP-0 Gate B, sweep a rescue dimension/budget/plan/tail rule, or
begin a learned projection or broad end-to-end experiment on this registered
line. Any later lossy-projection direction requires a distinct SAQ-specific
limitation, an updated primary-source review, and a new preregistration.

Preserve this initial architecture:

```text
L2 + IVF first
base/index data only for fitting
one dataset-level projection
one global SAQ segment/bit plan
one query-side estimator/searcher state
no per-cluster projection or plan ids
no mixed-plan search dispatch
original-space exact labels for every quality claim
held-out queries for evaluation only
```

Ordinary IVF centroids are allowed; cluster-specific learned projection
matrices or plan identities are not.

## Inherited Evidence And Scope Boundary

This branch is forked from `saq-transform-analysis` at commit `3d94840`. It
inherits the canonical raw-space exact-distance infrastructure and the
completed Phase 1/1b negative result, not the old research premise.

The inherited study tested full-dimensional, L2-isometric transforms. Its
preregistered CIFAR60k replication failed to show that PCA's variance objective
is a systematic practical SAQ limitation. Do not reopen that study by changing
the dataset, prefix, budget, or transform.

That result neither tests nor falsifies physical `D -> d` projection. The new
direction has a different independent variable, work model, and error source:

```text
old direction: D -> D basis choice, exact L2 preserved
new direction: D -> d physical representation, projection error accepted
```

Treat the old evidence documents and artifacts as historical controls. Reuse
only infrastructure necessary for common raw exact labels, deterministic
candidate replay, manifests, hashing, and query-level confidence intervals.

An old PCA-prefix routine in `src/test_ivf.cpp` is not prior SAQ evidence. It
keeps full vectors, has no SAQ quantization or complete accounting, and the
only checked-in runner uses `B=32`, which makes its selected dimension equal to
the original dimension. Do not cite it as a completed lossy experiment or
migrate it wholesale.

## Related-Work And Novelty Boundary

The original SAQ paper already describes dimension reduction as PCA projection
followed by discarding trailing dimensions, and presents SAQ as bridging
dimension reduction and dimension balancing. Current code materializes a
full-dimensional PCA view and can assign a final segment zero bits. Therefore,
"add dimension reduction to SAQ" is not itself a new claim.

The closest collisions are mandatory baselines:

- ASH already learns a global orthonormal `D -> d` projection and trades fewer
  dimensions for more scalar-quantization bits at fixed payload.
- MRQ already quantizes a PCA head, summarizes the residual tail, and uses
  multi-stage IVF refinement with quantization and residual error bounds.
- LeanVec-ID already combines base-only PCA-style dimensionality reduction
  with a low-dimensional primary representation and a higher-dimensional
  secondary representation for reranking.
- DADE/ADSampling-style distance operations already cover projected prefixes,
  probabilistic bounds, adaptive work, and integration with ANN indexes.
- GleanVec covers locally adaptive piecewise-linear projection; its
  cluster-specific state violates the initial one-global-projection
  architecture and is related work rather than the proposed design.
- OPQ and TurboQuant are required rotation/quantization controls where their
  objectives overlap a later learned method.

None of the following is a contribution on its own:

```text
truncated PCA + SAQ
learned D -> d projection + SAQ
fewer dimensions with more bits per dimension
PCA head + tail norm or residual variance
projected screening followed by original-vector reranking
approximate -> projected exact -> original exact refinement
```

The narrowest hypothesis not identified together in the bounded review is an
empirically demonstrated, non-separable interaction between physical
dimension, SAQ's heterogeneous segment/bit plan, CAQ adjustment, and
progressive prefix decisions. If ASH, MRQ, LeanVec-ID, DADE/ADSampling,
uniform-bit projected quantization, or current SAQ 0-bit-tail semantics explain
the result, stop.

Before proposing any additional idea, update the primary-source survey and
state what the closest work solves, what gap remains, and why the idea is not a
direct composition.

## Distance And Error Contract

Every lossy experiment must retain a common original-space exact reference.
For a registered tail treatment, emit at least:

```text
D0 = original-space exact squared L2 distance
DP = exact projected surrogate
DS = exact projected head with deployed tail-summary precision
DQ = full projected-SAQ estimate with deployed tail summary
DT = staged projected-SAQ estimate with deployed tail summary

e_projection   = DP - D0
e_summary      = DS - DP
e_quantization = DQ - DS
e_staging      = DT - DQ
e_total        = DT - D0
```

Thus `e_total = e_projection + e_summary + e_quantization + e_staging`. Do not
define `DQ - D0` as quantization error; it conflates projection, summary
precision, and quantization.
Report component covariance and any cancellation. Treat cancellation as a
result to validate externally, not as a mechanism by itself.

Report pure head truncation and head-plus-tail-norm as separate arms. A 0-bit
SAQ L2 residual segment already estimates
`||x_tail-c_tail||^2 + ||q_tail-c_tail||^2` while omitting the residual-tail
inner product, so the tail-norm arm is an equivalence/control arm, not a
proposed contribution.

## Phased Gate

LP-0 Gate A is complete. At the frozen point, `oracle576_norm.DP` has lower
top-100 agreement and more boundary inversions than seed-averaged
`native_full_saq.full`; both registered one-sided zero-margin conditions fail.
The float32 tail-summary error is negligible relative to projection error, so
summary precision does not explain the failure. Gate B is not authorized.

Treat the remaining text in this section as the preserved design and stop
logic of the completed preregistration, not as permission to continue it.

The first implementation is offline and fixed-candidate only. Its sole lossy
dimension is `d=576`, selected from the frozen GIST plan before query
evaluation because it removes the lowest positive-bit segment and terminal
0-bit tail. It reuses the first 128 frozen probes and candidates with common
raw exact labels; no other dimension, low-dimensional IVF rebuild, or broad
sweep may rescue a failed gate. Start with the exact projected oracle and add
projected SAQ only if the oracle screen passes.

Two current-index controls are mandatory. The first is the actual
`accurate_prefix_3` stage: it refines the first three segments but still uses
fast suffix estimates, so it requires the corresponding suffix query state.
The second is an offline `logical_head576_norm` counterfactual: it scores only
the first three full-code segments, attaches exactly the registered combined
tail norm, and computes only the necessary PCA head. The latter should match
the physical projected estimator in distance; it separates estimator changes
from reductions in persisted state and work. Do not call either control a
production stage with semantics it does not have.

LP-0 freezes the retained plan, so it cannot establish the proposed
non-separable plan interaction. Passing it permits only the closest-baseline
collision analysis. Before a method claim, evaluate ASH, MRQ/MRQ+, LeanVec-ID,
DADE/ADSampling-style projected computation, native full-D SAQ, truncated PCA,
and a uniform-bit projected control. A projected-plan interaction requires a
new preregistration, followed by external validation without query retuning.

Stop if:

- the exact projected floor is dominated before SAQ quantization is added;
- the physical arm differs in ranking from its algebraically equivalent
  logical arm, indicating an invalid artifact rather than a contribution;
- the benefit is explained by tail norms, uniform-bit rate reallocation, ASH,
  MRQ, or full-vector reranking;
- complete transform, metadata, padding, and refinement costs erase the gain;
- a result requires benchmark-query tuning, local projections, plan ids, or
  mixed dispatch;
- the effect does not survive a preregistered second spectral regime.

## Repository Layout And Reuse

- `saqlib/`: C++ SAQ/CAQ implementation, quantizers, estimators, IVF helpers,
  and search logic.
- `src/`: C++ experiment and search binaries. The inherited transform
  diagnostic has useful raw exact replay but currently enforces equal raw and
  transformed dimensions.
- `script/`: small research-question-driven preparation and analysis helpers.
  Prefer a dedicated lossy schema over bending the full-D Phase 1 schema.
- `python/`: upstream preprocessing helpers. `python/pca.py` is full
  dimensional and should not silently become the experimental contract.
- `data/`, `results/`, `bin/`, `build/`: generated or local-output areas; do
  not commit datasets, indexes, binaries, or build outputs.
- `docs/`: concise research notes, protocols, evidence, and source metadata.
- `../vectordb/scripts/`: sibling-repository transform/manifest concepts may
  be reviewed and selectively reimplemented; do not modify the sibling repo
  without explicit authorization.

SAQ pads dimensions to 64-lane blocks. Use multiples of 64 in the first gate
to avoid padding as a confound. Do not depend on ephemeral `/tmp` artifacts in
a durable protocol.

## Measurement And Accounting

For every experiment record:

- dataset, `N`, `D`, `d`, metric, `K`, nominal `B`, `nprobe`, candidate-set
  construction, top-k metric, command, random seeds, and block-min mode;
- projection contract, fit rows/hash, operator/model bytes, fit/apply time,
  raw-query projection latency, and actual projection operations;
- tail treatment, tail metadata, query tail-norm work, and any original-vector
  refinement rate/work;
- SAQ plan, padding, segment rotations, code bytes, factors, norms, centroids,
  serialized bytes, bytes read, cycles/time per candidate, and raw rerank
  vectors;
- projection, quantization, staging, and total error separately, with ranking
  metrics and query-level paired confidence intervals.

Do not use nominal `B` or code payload alone as the space comparison. Count the
global `D x d` operator, means, centroids, per-vector scalars/ids, alignment,
secondary vectors, and duplicated representations consistently.

The query-side work model must include raw `D -> d` projection. For an IVF
residual around centroid `c`, a query tail norm can be derived as
`||q-c||^2 - ||P_d(q-c)||^2`. This may require original-dimensional work for
every probed centroid unless an exactly equivalent quantity is already
available. Count that work, the `D*d` head projection, and any retained
full-dimensional centroid state; do not assume tail coordinates are free.

## Branch Hygiene

The direct parent contains only the correctness base plus the completed
full-D transform study. Preserve the confirmed correctness fixes:

- positive 1-bit segment packing support;
- padded-lane finite block-min search support.

Do not migrate graph profilers, graph documents, mixed local plans, static
global cost-DP prototypes, empirical fixed-policy scorers, query-aware
rank-boundary learners, or broad historical runners. The graph direction is
out of scope.

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

For multi-segment SAQ IVF claims, prefer:

```bash
-searcher_safe_block_min_mode=2
```

Label mode `0` explicitly if it is used only for legacy reproduction.

## Do-Not Rules

- Do not present "projection + SAQ" as a contribution without the
  SAQ-specific interaction and closest-baseline evidence.
- Do not reopen the failed full-D PCA-replacement study.
- Do not use transformed-space ground truth for lossy quality claims.
- Do not tune `d`, plans, thresholds, losses, or stages on held-out benchmark
  queries used for reporting.
- Do not use query-aware projection learning under the current direction.
- Do not introduce per-cluster projection matrices, per-cluster plans, plan
  ids, or mixed-plan dispatch.
- Do not change the persisted index format before the offline gate.
- Do not rebuild a low-dimensional IVF or claim QPS before the fixed-candidate
  projection-floor gate.
- Do not omit operator, metadata, secondary-vector, or refinement costs.
- Do not present bug fixes, tooling, or an equivalence with the current 0-bit
  tail as research contributions.
- Do not introduce unjustified hyperparameters. Each must have a
  mechanism-level rationale, a unit/scale, a fixed base-only selection rule,
  and sensitivity evidence or an ablation plan.
- Do not overclaim universal improvement before validation across datasets and
  operating points.

# SAQ component-wise base-only oracle diagnostic

Date: 2026-08-03

## Purpose

This diagnostic asks where the unchanged production SAQ accurate-distance
estimate loses nearby-vector ordering information.  It uses only index/base
data and makes no benchmark-query, Recall, QPS, novelty, or method claim.

The smallest falsifiable question is:

> Does replacing only the stored rescale or one existing SAQ segment with a
> query-independent/exact counterpart consistently remove a material share of
> production pairwise order reversals?

The answer determines which component, if any, deserves a later method-level
question.  It does not itself authorize such a method.

## Existing support and exact gaps

| Need | Existing repository support | Gap for this diagnostic |
| --- | --- | --- |
| true and SAQ distance | `src/test_relative_error.cpp` computes both | it loads benchmark queries and reports only aggregate total error |
| per-segment estimate | `SaqCluEstimator::getEstimators()` and `compAccurateDist()` expose segment contributions | no runner combines them with exact segment substitutions |
| stored codes/factors | `IVF::get_pclusters()`, `SaqCluData`, `long_factor()`, IDs, centroids, and persisted rotations are accessible | no component-attribution output exists |
| code reconstruction | persisted fast-scan MSB codes, compacted extension bits, factors, and rotations are accessible | the runner must decode the stored code rather than silently re-encode a potentially different code |
| scalar replacement | code direction, residual, and stored rescale are sufficient | least-squares rescale must be computed outside production code |
| exact base ordering | base PCA rows and IDs are present | deterministic probe/pool selection and local-neighbour construction are needed |
| index loading | `IVF::load()` exposes the complete persisted artifact | its current outer loop reloads all clusters `K` times and must be corrected/tested |

The existing graph-order profiler is not reused: its source is absent from
this snapshot and its historical runs use benchmark queries.  The unit tests
are useful arithmetic references but also load query fixtures in their natural
data modes.

## What is and is not an oracle component

The persisted index fixes five segments:

```text
s0: dimensions   0..63,  11 bits each
s1: dimensions  64..255, 6 bits each
s2: dimensions 256..575, 4 bits each
s3: dimensions 576..831, 2 bits each
s4: dimensions 832..959, 0 bits each
```

An orthogonal PCA/segment rotation preserves exact distance and therefore is
not independently an error term.  Changing it would define a different
quantizer rather than an oracle replacement.  The repository also has no
well-defined optimal-rotation oracle.

Likewise, replacing the bit plan requires re-encoding and a matched-storage
alternative plan.  This diagnostic does not call a single exact segment a
`PLAN_ORACLE`.  It measures segment importance.  A strong low/zero-bit segment
result would justify a later, separately designed plan comparison; it would
not prove that a new plan works.

## Frozen inputs

```text
base PCA:
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/
  gist_sample50k_base_pca.fvecs
  bytes 192200000
  sha256 a027be4e9942c7935ba4c7184eac09b4ad2d2c6fbe561ed9a598e66933b20671

SAQ index:
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/
  ivf512_b4_caq_adj_seg_pca.index
  bytes 34201289
  sha256 05300043c56b7b4e5cb2844c27d671da421effdd64ac67225dd404cb7391e8ac
```

No query or ground-truth file may be opened.  Do not inspect another dataset,
index, bit budget, rotation, or plan after seeing the result.

## Deterministic evaluation population

Define the standard pure `splitmix64` hash
`h(id) = splitmix64(2026080304 XOR id)`, ordered by `(h,id)`.

- probes: first 256 base IDs;
- candidate pool: next 4,096 IDs, disjoint from probes;
- fold 0: first 128 probes;
- fold 1: second 128 probes.

For each probe, compute float64 squared L2 distance to all 4,096 candidates and
select the closest 64 by `(distance,id)`.  Only these 64 form the local
evaluation set.  This creates a difficult base-neighbour ordering problem
without benchmark queries or outcome-dependent thresholds.

Every arm ranks the same 64 candidates.  Candidate selection always uses the
raw exact distance, never an SAQ arm.

## Frozen arms

For a probe `q`, candidate `o`, and segment `s`, let:

- `E_s(q,o)` be the persisted production SAQ accurate-distance contribution;
- `T_s(q,o)` be float64 exact squared L2 on the original coordinates of that
  segment;
- `L_s(q,o)` use the same CAQ code direction but replace production scale
  `||o||^2 / <o,u>` with the query-independent least-squares scale
  `<o,u> / ||u||^2`, where `o` is the candidate residual and `u` is its
  quantized direction before scale.

Both production and least-squares arms retain the stored exact residual norm
term.  Thus the least-squares segment contribution is explicitly

```text
L_s(q,o) = ||q||^2 + ||o||^2 - 2 <q, alpha_ls u>,
alpha_ls = <o,u> / ||u||^2.
```

Here `q` is the probe minus the candidate's IVF centroid in the same rotated
segment coordinates.  When `u` is zero, set `alpha_ls=0`; do not introduce a
fallback or fitted constant.

Run these arms without changing stored bytes or candidate sets:

- `PROD = sum_s E_s`;
- `LS_ALL = sum_s L_s` for positive-bit segments, with the zero-bit segment
  unchanged;
- `LS_SEG_s = L_s + sum_{j!=s} E_j` for `s=0..3`;
- `EXACT_SEG_s = T_s + sum_{j!=s} E_j` for `s=0..4`;
- `EXACT_ALL = sum_s T_s`, used only as a correctness control.

For the zero-bit segment, there is no `LS_SEG_4`.  The gap between
`LS_SEG_s` and `EXACT_SEG_s` separates scale opportunity from the remaining
code-direction error for positive-bit segments.  `EXACT_SEG_4` measures the
upper bound from omitted dimensions.

## Correctness checks before outcome inspection

1. A synthetic index with at least three unequal-size clusters round-trips IDs,
   plans, centroids, codes, factors, and end-of-file position exactly.  This
   must fail under the current repeated-cluster loader and pass after the
   minimal loop correction.
2. The persisted natural index contains 50,000 unique IDs exactly once and the
   frozen five-segment plan.
3. Independently composing the stored norm, LUT/fast-scan MSB contribution,
   compacted extension contribution, rescale, and L2 formula reproduces the
   production accurate-distance contribution within
   `1e-5 * max(1, abs(stored_contribution))` on 32 predeclared parity probes.
   Separately decoding the persisted full code must reproduce its stored
   rescale from the base residual within the same tolerance.  Codes and
   adjustment rules may not be changed to obtain parity.
4. `EXACT_ALL` equals raw float64 960-dimensional squared L2 within
   `1e-9 * max(1, exact_distance)`.
5. Exact segment distances sum to exact full distance, and probe/pool IDs are
   disjoint with the required cardinalities.

Failure of any check invalidates the run; it is an artifact finding, not a
negative scientific result.

## Metrics

For each probe, compare all unordered pairs among its 64 candidates.  Exclude
an exact tie only when

```text
abs(d_a - d_b) <= 1e-9 * max(1, abs(d_a), abs(d_b)).
```

Primary metrics, reported separately for both folds and combined:

- absolute pairwise inversion rate for every arm;
- absolute reduction from `PROD`;
- fraction of production inversions repaired;
- fraction of production-correct pairs newly inverted.

Secondary metrics:

- top-10 set agreement with exact ranking inside the fixed 64 candidates;
- median and p95 absolute relative distance error;
- per-segment dimensions, bits, stored bytes, and error contribution;
- CPU/wall time and peak RSS, with output work outside measured arithmetic.

This top-10 agreement is a base-only local diagnostic, not benchmark Recall.

## Frozen decision rule

First check headroom.  If `PROD` has pairwise inversion rate below `0.002` in
both folds, close this component-localization direction: the accurate
estimator has less than 0.2 percentage points of local ordering error to
explain under this population.

Otherwise, call an arm actionable only if, in each fold, it:

1. reduces absolute inversion rate by at least `0.002`; and
2. repairs at least 20% of production inversions.

Interpretation is fixed:

- actionable `LS_ALL` or `LS_SEG_s`: rescale is a localized limitation;
- actionable `EXACT_SEG_s` beyond `LS_SEG_s`: code direction/precision in that
  segment is a localized limitation;
- actionable `EXACT_SEG_4`: omitted dimensions are a localized limitation;
- only diffuse `EXACT_ALL` headroom, with no actionable single component: do
  not design a component-specific method;
- no actionable arm: close this localization attempt.

Report all arms even when the rule fails.  Do not lower thresholds, change the
candidate pool, add datasets, or select a method from a combined-only effect.

## Implementation, commands, and resources

The initial estimate was 350--500 runner lines and 150--250 support lines.
The implemented runner is 952 lines because it contains explicit stored-code
decoding, independent LUT parity, deterministic metrics, and budget reporting;
the test/core/CMake support totals 249 lines.  It still reuses SAQ containers
and estimators and creates no index, serializer, supervisor, or general
experiment framework.

Frozen commands:

```bash
cmake -S research/saq_component_oracle \
  -B /tmp/saq-component-oracle-build \
  -DCMAKE_BUILD_TYPE=Release \
  -DSAQ_DEPS_ROOT=/tmp/saq-component-deps/root/usr
cmake --build /tmp/saq-component-oracle-build -j2
ctest --test-dir /tmp/saq-component-oracle-build --output-on-failure
/tmp/saq-component-oracle-build/saq_component_oracle \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index \
  /tmp/saq-component-oracle-v1/parity-production parity-v1
# Only after parity-v1 reports PASS:
/tmp/saq-component-oracle-build/saq_component_oracle \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/ivf512_b4_caq_adj_seg_pca.index \
  /tmp/saq-component-oracle-v1/run-primary frozen-v1
```

Total build, test, and execution budget is 2 aggregate CPU-hours and 2
wall-hours, with one experimental thread, 4 GiB peak RSS, and less than 100 MiB
of output.  Stop before exceeding a limit.  One execution is allowed; a second
run is permitted only to reproduce byte-identical output after the first run
has completed, and its cost must remain inside the same total budget.

## Claim boundary

A passing arm identifies decision-relevant headroom, not a publishable method.
Before implementation of a new mechanism, review the closest primary work for
that exact component and define a matched-storage/query-cost comparison.
Negative results apply only to this index, base-neighbour population, accurate
estimator, and frozen thresholds.  They do not establish benchmark Recall,
cross-dataset generality, or the absence of all SAQ limitations.

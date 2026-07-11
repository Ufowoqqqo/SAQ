# LP-0 Preregistration: Physical Projection Feasibility And Materialization

## Status And Scope

```text
registered: 2026-07-11
branch: saq-lossy-projection-analysis
experiment status: Gate A completed 2026-07-11
registered authorization: Gate A only
Gate A decision: FAIL
current authorization: stop; Gate B not authorized
```

The rules below preserve the preregistration as executed. The outcome is
recorded in
`docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md`.

```text
seed-averaged agreement delta           -0.0017265625
one-sided 95% agreement lower bound     -0.002578125       (requires >= 0)
seed-averaged inversion delta            2.765607447e-6
one-sided 95% inversion upper bound      4.216880965e-6    (requires <= 0)
decision                                 FAIL
```

Artifact validity passed, including 442,823 candidate-level `D0/DP/DS` rows,
the registered candidate hash, and byte-identical oracle/native raw-reference
files. The result closes only the frozen GIST/`d=576`/`B=4` line; it is not a
universal conclusion about lossy projection.

LP-0 is a prerequisite falsification screen, not a method experiment. It can
answer three questions:

1. does an exact `d=576` projected surrogate retain enough original-space
   ranking quality to justify quantization work;
2. does the same frozen SAQ head remain competitive after quantization;
3. what state and work are actually removed by physical materialization,
   compared both with native full-D SAQ and with an algebraically equivalent
   logical head-only view?

LP-0 cannot establish a non-separable `(d, segment, bit, stage)` interaction:
it freezes the original first-three segment plan and does not reallocate bits.
Passing LP-0 only authorizes closest-baseline analysis and, if a gap remains, a
separate preregistration for a byte-matched plan-interaction test.

A positive GIST result is not paper evidence because GIST queries appeared in
the parent research line.

## Frozen Artifacts

Use the historical PCA view recovered and validated by
`script/prepare_phase1_transform_views.py`. Do not refit PCA. The historical
fit is base-only; the recovered affine mapping has no random seed.

| Artifact | Frozen SHA-256 |
|---|---|
| Raw base fvecs | `bd31f1332e60205472a50cf83a7c4c8cf5ecf5ffd6145cb4e8c44d591f8b2066` |
| Raw query fvecs | `0d1d620049de12da455ed7201e97cbab372c4d54d0e6dedbc8c503f62c911299` |
| Historical PCA base fvecs | `a027be4e9942c7935ba4c7184eac09b4ad2d2c6fbe561ed9a598e66933b20671` |
| Historical PCA query fvecs | `8f888359b836b3a5f498d3bf15bf63744024e320f99fe668c3953db2535cf974` |
| Historical PCA centroids | `48af2216744f9bb39fd7dccf2e0358aa705a4647227adb777796623c676674db` |
| Cluster assignments | `c466b5685dd4ef12f42f1d7fa304f42b2c9989df12190c84b8bb4c0a29618eb1` |
| Historical PCA variance fvecs | `20345de79dbd6ead9728c2c9abdbdb3f12e4f0ad449122f586d87ed3036b9c35` |
| Recovered float64 mean array | `9d70b61994ad42c4d35734a786b3814493f8da721cfbfd19943b1b9875167114` |
| Recovered float64 full operator array | `5e5de629a3bd95d1b5fe72f29db495113b1313e106ea3caad56992a526d58bdb` |
| Retained `960 x 576` operator array | `b3d467728c62d2540f1d34309a78a8419ecebeafce9e3a07319af4eb35623b53` |
| Fixed q128/nprobe16 probe ivecs file | `a568c32ff9555aaef9df68e49b65a64f895fb5e37c5aefdf63ff0102732e7b80` |
| Fixed probe integer array | `c0e1ed9424a8a287cba9d85dabb2732c89ad132485ae431432c55725e674ebfc` |

Array hashes use the existing `sha256_array` contract: dtype, rank, shape, and
contiguous bytes are hashed. The transient parent view may be regenerated, but
all array and durable-file hashes above must match before evaluation.

For row-vector application `(row - mean) @ R_576`, require:

```text
R_576 shape = 960 x 576
||R_576^T R_576 - I_576||_F / 576 <= 1e-12
historical mapping max absolute error <= 1e-4
historical mapping relative Frobenius error <= 1e-5
```

## Frozen Replay

```text
dataset                 gist_sample50k
N, D                    50,000, 960
queries                 first 128 only
metric                  squared L2
IVF                     K=512, nprobe=16
candidate membership    all members of the 16 frozen probe lists; no cap
candidate order         probe-file order, then ascending base row id
duplicate handling      any duplicate is an invalid artifact
candidate inventory     442,823 total; 1,675--5,433/query
candidate SHA-256       f5eaef79fbbceda7a0cb04adb5dc232d24d00e0173b4cd70bb0f29ddae25b099
top-k                   100
bootstrap               paired by query, 10,000 resamples, seed 20260711
rotation labels         logical seeds 0..9; rotation-off reported separately
rotation C RNG mapping  logical seed s -> srand(s+1); off -> srand(0)
block-min               not applicable to replay; mode=2 for later IVF search
```

The candidate hash is over each little-endian `(query_id:uint32,
count:uint64, candidate_ids:int32[])` record. Do not truncate a long list.
Generate `D0` and the raw top-100 inventory once before any arm-specific
build, then freeze their hashes in the run manifest.

## Frozen Plan And Dimension

```text
parent nominal budget   B=4, 3,840 bits/vector
full frozen plan        0:64@11 | 64:256@6 | 256:576@4 |
                        576:832@2 | 832:960@0
confirmatory d          576
retained plan           0:64@11 | 64:256@6 | 256:576@4
retained code           3,136 bits/vector; 5.444 bits/retained dimension
removed positive code   512 bits/vector
```

`d=576` is the start of the lowest positive-bit suffix in the base-only frozen
plan. It removes 40% of PCA output components, 13.33% of the nominal four-bit
budget, and 14.04% of the frozen plan's actual 3,648 positive code bits. No
other `d`, plan, `B`, `K`, `nprobe`, or candidate set may replace a failed gate.

## Native Comparator Configuration

Build `native_full_saq` from the frozen inputs with this exact bundle:

```text
source base                    commit 3d94840
distance                       L2Sqr
custom plan                    frozen five-segment tuple above
avg_bits                       4.0
enable_segmentation            true
seg_eqseg                      0
use_compact_layout             false
quant_type                     CAQ
use_fastscan                   true
caq_adj_rd_lmt                 6
caq_adj_eps                    1e-8
caq_ori_qB                     0
random_rotation                true for logical seeds; false for off
logical seed -> C RNG          s -> srand(s+1)
rotation off -> C RNG          srand(0), random_rotation=false
construction threads           6
searcher_vars_bound_m          4
```

Before evaluating a projected arm, serialize the comparator configuration,
source revision/diff, input hashes, decoded plan, decoded per-segment state,
and native query-reference inventory into one canonical manifest and freeze its
SHA-256. A later implementation commit may add LP-0 outputs but may not change
this comparator bundle without invalidating the registration.

## Inference Contract

For every quality comparison define:

```text
delta = projected_or_physical_arm - native_full_saq
```

Thus positive agreement delta and negative inversion delta are favorable.
Average the ten paired logical seeds within each query before inference. Use a
paired percentile bootstrap over queries with 10,000 resamples and seed
`20260711`. A one-sided 95% lower bound is the 5th percentile; a one-sided 95%
upper bound is the 95th percentile. Rotation-off is a separate diagnostic with
the same percentile convention.

## Arms And Factorization

### Native Reference

`native_full_saq` uses the five-segment full-D plan. Its confirmatory quality
endpoint is `full`; its confirmatory staged endpoint is the implemented
`fast_all`. The implemented `accurate_prefix_3` is descriptive only: it uses
accurate estimates for the first three segments and fast estimates for the
suffix, so it is not a 576-dimensional stop.

### Projected Oracles

- `oracle576_none`: exact PCA-head squared distance, no tail summary.
- `oracle576_norm`: exact PCA-head squared distance plus exact float64
  residual-tail squared norms, omitting the residual-tail inner product.

Use the frozen historical PCA float32 coordinates and accumulate head/tail
terms in float64; do not refit or silently substitute a numerically different
PCA basis.

### Logical Materialization Control

`logical576_norm` retains the full persisted five-segment index but scores the
first three full-code segments plus the same combined tail sidecar and query
tail term as the physical arm. It is a new offline counterfactual, not a
production SAQ stage. Its online projection may use the same sliced `R_576`
state as the physical arm.

### Physical Projected Arm

`physical576_norm` persists only the three retained SAQ segments plus the
combined tail sidecar. It uses the same decoded retained codes, factors,
rotators, projected centroids, query-head values, and tail term as
`logical576_norm`.

Consequently:

```text
DQ(logical576_norm) == DQ(physical576_norm)
DT(logical576_norm) == DT(physical576_norm)
```

for each matched stage. This is an artifact invariant, not a superiority
hypothesis. A ranking difference is invalid evidence.

## Tail Summary Contract

The sidecar stores one combined `float32` L2 norm
`||tail(x-c)||_2` per base-to-assigned-centroid residual. It does not store a
squared norm. During estimation, square that float32 value in the same
operation order used by the registered scorer.

Create the base sidecar by accumulating the frozen historical PCA tail in
float64, taking the square root, and casting once to float32.

For each query and probed centroid, compute the query tail squared norm once
and reuse it for every candidate in that list:

```text
tail_q_sq = ||q-c||^2 - ||P_576(q-c)||^2
```

Compute the subtraction in float64. If
`tail_q_sq >= -1e-6 * max(1, ||q-c||^2)`, clamp a negative result to zero;
otherwise the artifact is invalid. Cast the clamped value once to float32 for
the deployed estimator. Count the original-dimensional `||q-c||^2` work and
any required full-D centroid state. Also verify the derived value against the
materialized historical PCA tail within the same `1e-6` relative/absolute
tolerance.

`logical576_norm` uses the identical one-scalar sidecar. It must not pretend
that the existing two suffix segment norms have the same bytes or rounding.
The sidecar is outside the unchanged SAQ file format, so report
`SAQ index + sidecar` as deployable serialized space.

## Distance And Error Contract

Tie-break every ranking by `(distance, base_id)`. For each candidate emit:

```text
D0 = canonical original-space float64 exact squared L2
DP = exact projected surrogate with exact float64 tail treatment
DS = exact projected head plus deployed float32 tail-summary treatment
DQ = full projected-SAQ head plus deployed tail-summary treatment
DT = staged projected-SAQ head plus deployed tail-summary treatment
```

For the no-tail arm, `DS=DP`. Decompose:

```text
e_projection   = DP - D0
e_summary      = DS - DP
e_quantization = DQ - DS
e_staging      = DT - DQ
e_total        = DT - D0
               = e_projection + e_summary + e_quantization + e_staging
```

An exact-tail diagnostic may isolate head quantization but is not deployable.
Report bias, equal-query RMSE, pooled RMSE, MAE, p50/p90/p99, and component
covariance. Error cancellation is descriptive and cannot rescue a failed gate.

## Artifact Validity Gate

The experiment is invalid unless:

- all frozen artifact and candidate hashes match;
- `D0`, raw top-100, exact-best, candidate IDs, and candidate counts are common
  across every arm;
- retained plan tuples are exactly equal;
- decoded retained codes, factors, and rotators have equal per-segment hashes
  for every paired seed;
- `logical576_norm` and `physical576_norm` use the identical sidecar bytes;
- their `DQ/DT` float32 bit patterns and ranking digests are identical for
  every candidate, query, seed, and matched stage;
- all values are finite and the error-sum identity holds within
  `1e-10 * max(1, |e_total|)` in float64 analysis;
- the evaluator does not affect the operator, `d`, plan, tail rule, stage, or
  threshold.

Different serialized offsets/layouts are expected between three- and
five-segment indexes; compare decoded retained state, not raw file slices.

## Gate A: Exact-Surrogate Upper-Bound Screen

Compare `oracle576_norm` at `DP` with the seed-averaged
`native_full_saq.full` estimate under common `D0` labels. This gives the
projected design an exact-head oracle; it is not an iso-estimator comparison
and cannot establish a physical-projection win.

Pass only if both zero-margin one-sided conditions hold:

- the lower paired 95% bound of top-100-agreement delta is at least zero;
- the upper paired 95% bound of boundary-inversion delta is at most zero.

Report rotation-off separately. If Gate A fails, conclude only that the
registered GIST/`d=576`/`B=4` upper-bound gate found insufficient evidence and
stop this registered line. Do not claim that projection is universally poor.

## Gate B: Projected-SAQ Quality And Logical Equivalence

Run only after Gate A passes.

First enforce the exact logical/physical artifact equivalence above. Then
compare `physical576_norm.DQ` with `native_full_saq.full`, averaging paired
seeds within each query before the query bootstrap.

Pass only if:

- the lower paired 95% bound of top-100-agreement delta is at least zero;
- the upper paired 95% bound of boundary-inversion delta is at most zero;
- at least 8/10 seeds have nonnegative agreement delta and nonpositive
  inversion delta;
- rotation-off has the same point-estimate directions.

RMSE endpoints are required secondary diagnostics, not non-inferiority gates.
A logical/physical difference invalidates the experiment; it is never positive
research evidence.

## Gate C: Frozen Progressive Endpoint

Run only after Gates A and B pass. The sole confirmatory staged comparison is:

```text
physical576_norm.fast_all versus native_full_saq.fast_all
```

Pass only if the lower paired 95% bound of agreement delta is at least zero and
the upper paired 95% bound of inversion delta is at most zero. All other stage
curves are descriptive; do not select a favorable prefix after evaluation.

## Gate D: Gross And Incremental Systems Accounting

Run only after Gates A--C pass. Report two explicitly separated ledgers.

Before Gate D execution, add a conditional preregistration freezing warm-up,
repetitions, batching, thread count/affinity, cache state, timing statistic,
and paired speedup calculation. The thresholds below may not be executed with
an ad hoc timing method.

Gross comparison against `native_full_saq`:

```text
dense projection operations             >= 40% lower by construction
online operator bytes, including mean   >= 39% lower
deployable serialized bytes/vector      >= 10% lower
full-stage bytes read/candidate         >= 10% lower
raw-query preparation time              >= 20% lower,
                                         lower paired 95% speedup bound
```

Incremental comparison against `logical576_norm`:

```text
DQ/DT and ranking                       exactly equivalent by artifact gate
deployable serialized bytes/vector      >= 10% lower
online query/estimator work              no reduction claimed
online sliced-operator bytes             no reduction claimed
```

If the second ledger shows only persisted/resident storage savings, state the
LP-0 result as **storage materialization only**. Do not attribute gross query
work savings to physical representation beyond a logical sliced view.

For each rotation setting, define:

```text
deployable total bytes =
  codes + factors + norms + tail sidecar + padding/alignment + ids/list state
  + amortized projected/full centroids + online operator/mean + rotators
  + any secondary/full rerank representation

bytes/vector = deployable total bytes / N
```

Report serialized, resident, and amortized components separately. Derive and
instrument custom-head bytes; the inherited stage byte model assumes fast
suffix segments and is not valid for `logical576_norm`.

Fixed replay timing supports a kernel/work conclusion, not end-to-end QPS.

## Gate E: Closest-Baseline Collision

Run only after Gates A--D pass. Reproduce or faithfully implement:

- ASH with the published query-calibrated squared-L2 correction labeled as an
  outside-scope reference and a separately frozen base-only calibration used
  for the admissible comparison;
- MRQ/MRQ+ with base-only frozen `d`, variance count, and bound parameters;
- LeanVec-ID's truncated-PCA projection control and, where obtainable, the
  official packaged system;
- uniform-bit projected quantization at matched deployable bytes;
- DADE/ADSampling-style projected progressive distance controls where the
  comparison is compatible.

Before Gate E execution, add a conditional preregistration with an exact
compatibility/exclusion rule and frozen configuration for every mandatory
baseline. Unavailable proprietary code must be labeled rather than silently
replaced by a weaker method.

Use one simultaneous paired-query bootstrap over all mandatory baselines and
the two ranking endpoints. Continue only if, against every compatible baseline:

1. both simultaneous ranking bounds are favorable at no greater total bytes
   and complete query work; or
2. both zero-margin ranking bounds are non-inferior, deployable bytes are at
   least 10% lower, and complete query time is at least 20% lower.

Passing Gate E only authorizes a separately preregistered, byte-matched
projected-plan interaction test with a uniform-rate control. It does not
authorize a learned projection, persisted-format change, or broad sweep.

## Decision Table

| Outcome | Registered decision |
|---|---|
| Artifact gate fails | Correct/report invalid; no scientific conclusion |
| Gate A fails | Insufficient evidence at this registered upper-bound point; stop |
| A passes, B fails | Frozen projected SAQ does not preserve the quality point; stop |
| A/B pass, C fails | Progressive endpoint does not transfer; stop progressive line |
| A--C pass, D gross fails | No material systems opportunity; stop |
| D incremental is storage-only | Report storage-only boundary; proceed only to collision check |
| A--D pass, E fails | Existing work explains/dominates the point; no contribution |
| A--E pass | Authorize a new plan-interaction preregistration only |

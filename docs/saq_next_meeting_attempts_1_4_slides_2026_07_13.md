# Post-SAQ Pivot: Attempts 1, 2, 3, And 4

PCA Replacement, Lossy Projection, Exact Scalar-Codebook DP,
Recent ASQ Prior-Art Audit, Distance-Quality Re-evaluation,
And An Arbitrary-Cardinality Fixed-Rate Quantization Gate

Date: 2026-07-13

Presentation status: **CURRENT DRAFT -- not yet presented at a meeting.**

Revision: incorporates the 2026-07-13 audit of
[White and Singal, arXiv:2606.00289v1](https://arxiv.org/abs/2606.00289)
and its pinned official code, plus the committed Attempt 4 scientific-content
snapshot
`saq-arbitrary-cardinality-analysis@3c0a49f`.

Audience assumption: familiar with vector search and vector quantization at a
high level, but not with SAQ's transform, segmentation, or the experiments in
these repositories.

Deck status: Attempts 1, 2, and 3 are complete studies. Attempt 4 has completed
only A4-0 instrument validation. A4-1S is authorized but has no committed
implementation or outcome. A4-1 real-base execution and SAQ integration remain
unauthorized.

---

## 1. Meeting Goal

This is not a presentation of a finished method.

The goal is to explain four research attempts in enough detail to decide what
they teach us, what they rule out, and what evidence is still missing:

```text
Attempt 1: Is PCA a practical limitation of SAQ?
           1A. Replace full-D raw-data PCA with another isometric transform.
           1B. Physically project D -> d and summarize the omitted tail.

Attempt 2: Does histogram-exact scalar-codebook optimization improve the
           quantization and retrieval result beyond Lloyd training, and what
           remains after recent ASQ and exact-1D-DP prior work?

Attempt 3: Does paper-exact distance quality change conclusions based on
           exact-identifier Recall@k?
Attempt 4: Can arbitrary integer scalar cardinalities use a fixed B_g-bit
           group word more effectively than power-of-two cardinalities while
           retaining one random-access word and one lookup per group?
```

Main message:

```text
Attempts 1--3 found useful local evidence, but none established a new method.
For Attempt 2, the local ANN audit remains informative, while the inner exact-
DP primitive is established prior work and cannot be claimed as the
contribution. Attempt 4 is an active gated feasibility study, not a completed
study or a natural-data, ANN, or systems result. Its current evidence validates
only a synthetic instrument.
```

Speaker notes:

- The purpose is research selection, not presenting every experiment as a win.
- Attempt 1 belongs to the SAQ repository.
- Attempt 2 comes from the sibling `vectordb` repository and tests a more
  classical scalar-quantization premise. The new related-work audit separates
  the local two-DP pipeline from the already-established inner optimizer.
- Attempt 3 returns to SAQ and asks whether Recall understated the geometric
  quality of any previously rejected result set.
- Attempt 4 is problem-first and fixed-rate. Its current branch must not be
  described as having implementation, natural-data, ANN, or systems evidence.

---

## 2. Current Research Position

Project-level decision before this deck:

```text
SAQ-centric incremental method search: STOP
SAQ as a strong baseline:              RETAIN
Attempt 4 offline feasibility:         CONDITIONAL GO ONLY
SAQ/index/search integration:          NOT AUTHORIZED
```

Why still present these attempts:

1. Attempts 1--3 test three intuitive claims that may arise in a meeting.
2. They distinguish optimization guarantees from retrieval guarantees.
3. They provide quantitative stop evidence instead of relying on intuition.
4. Attempt 3 tests whether an evaluation choice, rather than a quantizer
   mechanism, caused one earlier negative conclusion.
5. Attempt 4 shows how the next direction is being constrained before data
   access or systems integration.

Unsafe interpretation:

```text
PCA is universally optimal, or exact DP never helps ANN.
```

Safe interpretation:

```text
The specific PCA-replacement, lossy-projection, and histogram-DP mechanisms
tested here do not supply a sufficiently general, overhead-controlled method.
The 2026 ASQ paper and pinned public code do not expose an integrated Attempt 2
pipeline, but the paper and earlier exact-1D-clustering work remove the inner
DP as a novelty claim.
Paper-exact distance quality changes one GIST operating-point interpretation,
but does not establish a new mechanism or a replicated method advantage.
For Attempt 4, allowing positive-integer cardinalities only enlarges the
dyadic feasible set for a factorized reconstruction objective. Mixed-radix
addressing and non-power-of-two scalar alphabets are prior art, and imply
neither ANN improvement nor a systems advantage.
```

---

## 3. Attempt Map And Evidence Status

| Attempt | Core question | Main regimes | Decision / current status |
|---|---|---|---|
| 1A. Full-D transform replacement | Does residual PCA or another isometric basis improve SAQ estimator behavior over raw-data PCA? | GIST sample50k, then preregistered CIFAR60K replication | Closed after replication failure |
| 1B. Lossy `D -> d` projection | Can a PCA head plus a compact tail surrogate beat native full-D SAQ? | GIST sample50k, `960 -> 576`, favorable exact surrogate | Gate A failed; projected SAQ not built |
| 2. Exact scalar-codebook DP | Does histogram-exact 1D DP improve shared dimensionwise scalar quantization over Lloyd, and is any method novelty left after prior work? | audio, PCA CIFAR60K, PCA DEEP1M; arXiv/code audit | Stronger offline baseline; inner DP is prior art; no stable recall dominance |
| 3. Distance-quality re-evaluation | Does `1/Ratio@k` change a frozen Recall-based Pareto conclusion? | GIST sample100k B=4; DEEP sample100k B=4/B=5 controls | Closed as metric-sensitivity evidence |
| 4. Arbitrary-cardinality fixed-rate words | Does the power-of-two restriction waste material capacity at unchanged fixed payload and lookup granularity? | A4-0 synthetic witness; A4-1S synthetic correctness/cost gate; registered GIST50k/CIFAR60k base-only gate only if later authorized | A4-0 `PASS_INSTRUMENT_ONLY`; A4-1S authorized with no committed result; base read forbidden |

Speaker notes:

- Attempt 1A and 1B are related but not equivalent.
- A full-D orthogonal transform preserves exact L2 geometry.
- A physical `D -> d` projection changes the exact distance unless the omitted
  interaction is somehow reconstructed.
- Attempt 4 changes the feasible scalar-product cardinalities inside a fixed
  word; it does not yet change SAQ, CAQ, the index, or the search path.

---

## 4. Minimal SAQ Background

SAQ compresses database vectors for approximate L2 search.

High-level pipeline:

```text
raw vectors
  -> full-dimensional PCA
  -> IVF residuals
  -> contiguous 64-dimensional segments
  -> nonuniform bits across segments
  -> CAQ encoding inside each positive-bit segment
  -> progressive distance estimation during search
```

Example GIST `B=4` plan:

```text
64@11 | 192@6 | 320@4 | 256@2 | 128@0
```

Meaning:

| Segment | PCA coordinates | Dimensions | Bits/dimension |
|---|---:|---:|---:|
| 1 | 0-63 | 64 | 11 |
| 2 | 64-255 | 192 | 6 |
| 3 | 256-575 | 320 | 4 |
| 4 | 576-831 | 256 | 2 |
| 5 | 832-959 | 128 | 0 |

PCA is therefore not a cosmetic preprocessing step. It determines which
subspaces receive high bits, low bits, or no inner-product code.

---

## 5. Common Variables

| Symbol | Meaning | Values used here |
|---|---|---|
| `N` | number of base vectors | GIST 50,000/100,000; CIFAR 60,000; DEEP 100,000/1,000,000 |
| `D` | original dimension | GIST 960; CIFAR 512; DEEP 256; audio 192 |
| `d` | physically retained dimension after lossy projection | GIST 576 |
| `K_IVF` | number of IVF clusters | 512 in Attempts 1 and 3 |
| `B` | nominal average bits/dimension | 4 in Attempt 1; 2/4/8 in Attempt 2; 4/5 in Attempt 3 |
| `Q` | number of held-out evaluation queries | 128 or 1,000 in Attempts 1 and 3 |
| `H` | equal-count histogram bins for scalar DP | default 256 |
| `K_b` | scalar centroids at bitwidth `b` | up to `2^b` |
| `B_g` | fixed bits in one two-factor word for Attempt 4 | 4 or 8 |
| `S` | joint-state capacity of one fixed word, `2^B_g` | 16 or 256 |
| `K_j` | scalar levels assigned to factor `j` | dyadic or any positive integer |
| `r` | scalar factors grouped into one fixed word | 2 in A4-1 |
| `w_j` | allocation weight for dimension `j` | 1 or historical rank-boundary weight |
| `R` | full-D orthogonal transform matrix | transform-dependent |
| `k` | number of returned neighbors evaluated | 100 in Attempt 3 |
| `nprobe` | IVF cells scanned per query | GIST 20--400; DEEP 50--400 |
| `d_i(q)` | true Euclidean distance to exact neighbor at distance rank `i` | recomputed in float64 |
| `d_tilde_i(q)` | true Euclidean distance at rank `i` within the returned set | recomputed in float64 |

Important notation distinction:

```text
K_IVF = IVF clusters
K_b   = scalar quantizer centroids
```

---

## 6. Attempt 1: Research Question

SAQ uses raw-data PCA because it:

```text
decorrelates coordinates
orders coordinates by decreasing variance
creates a low-variance tail
supports contiguous mixed-bit segmentation
```

But PCA optimizes variance/reconstruction objectives, not directly:

```text
CAQ angular error
progressive-prefix distance error
top-k ranking stability
Recall-QPS-bytes
```

Attempt 1 asks two increasingly aggressive questions:

```text
1A. Can another full-D orthogonal transform improve SAQ while preserving L2?

1B. If low-variance tail coordinates are physically removed, can a compact
    tail summary retain enough ranking information to improve work/space?
```

Speaker notes:

- We first test whether the premise is real before training a new transform.
- A learned transform is not authorized merely because PCA optimizes a
  different textbook objective.

---

## 7. Attempt 1A: Transform Definitions

Current SAQ transform:

```math
T_{raw}(x)=(x-\mu_{raw})R_{raw},
```

where `R_raw` contains the eigenvectors of raw base-vector covariance.

Residual-PCA alternative:

```math
r_x=x-c_{cid(x)},
```

```math
T_{res}(x)=(x-\mu_{res})R_{res},
```

where `R_res` is trained from IVF residual statistics rather than raw-vector
statistics.

For either full-D orthogonal matrix:

```math
R^TR=I,
```

so applying the same affine transform to base vectors, queries, and centroids
preserves squared L2 up to float roundoff:

```math
\lVert T(q)-T(x)\rVert_2^2=\lVert q-x\rVert_2^2.
```

Controls:

```text
current raw-data PCA
global residual PCA
identity coordinates
seeded random orthogonal transform
```

---

## 8. Attempt 1A Running Example

Illustrative two-dimensional dataset:

```text
raw covariance variances:       axis 1 = 100, axis 2 = 1
within-IVF residual variances:   axis 1 =   4, axis 2 = 9
```

Raw PCA ordering:

```text
axis 1 first, axis 2 second
```

Residual PCA ordering:

```text
axis 2 first, axis 1 second
```

If SAQ assigns more bits to earlier coordinates, the two transforms can produce
different segment importance even though both preserve exact L2.

This motivates the test, but it is not evidence. The empirical question is:

```text
Does residual ordering improve the actual packed SAQ estimator and ranking,
after plan, bytes, and internal rotations are controlled?
```

---

## 9. Attempt 1A Phase 1 Protocol: GIST

| Item | Frozen value |
|---|---|
| Dataset | GIST sample50k, `N=50,000`, `D=960` |
| IVF | `K_IVF=512`, one recovered canonical codebook and fixed assignments |
| Budget | `B=4` |
| Queries | first 128 held-out queries; evaluation only |
| Fixed probes | top 16 canonical IVF clusters/query |
| Fixed candidates | 442,823 candidate rows/configuration |
| Ranking cutoff | top 100 |
| Transforms | current PCA, residual PCA, identity, random orthogonal |
| Plan controls | native, frozen-PCA, uniform `960@4` |
| Segment rotations | logical seeds `0..9`, plus `off` |
| Configurations | `4 transforms x 3 plans x 11 controls = 132` |
| Inference | query-paired percentile bootstrap, 10,000 replicates |

The runner replays production packed estimators for:

```text
variance estimate
every fast prefix
every accurate prefix
full code
```

It is a fixed-candidate estimator experiment, not an end-to-end QPS run.

---

## 10. Attempt 1A Code And Artifact Map

Branch:

```text
saq-transform-analysis
evidence checkpoint: 3d94840
```

Key code:

```text
script/prepare_phase1_transform_views.py
src/phase1_transform_diagnostic.cpp
script/summarize_phase1_transform.py
script/evaluate_phase1b_gate.py
```

Primary evidence:

```text
docs/saq_transform_phase1_limitation_evidence_2026_07_10.md
docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md
```

Validity controls include:

```text
held-out affine-transform reconstruction
orthogonality/isometry checks
identical IVF assignments and probe lists
canonical raw-space ranking labels
identical serialized bytes for matched transform pairs
distinct internal-rotation streams
```

---

## 11. GIST Native Plans And Stage Results

Current PCA and residual PCA select the same plan and serialized bytes:

```text
64@11 | 192@6 | 320@4 | 256@2 | 128@0
serialized index = 34,201,289 bytes
```

Seed-averaged mean-query results:

| Transform | Stage | Logical bytes/candidate | RMSE | Top-100 agreement | Boundary inversion |
|---|---|---:|---:|---:|---:|
| current PCA | fast all | 124 | 0.386347 | 0.593133 | `1.9294e-2` |
| residual PCA | fast all | 124 | 0.386987 | 0.589813 | `1.9522e-2` |
| current PCA | accurate prefix 1 | 212 | 0.0818108 | 0.904930 | `9.5544e-4` |
| residual PCA | accurate prefix 1 | 212 | 0.0813185 | 0.906188 | `9.3807e-4` |
| current PCA | full | 508 | 0.00168088 | 0.994617 | `4.0869e-6` |
| residual PCA | full | 508 | 0.00167530 | 0.994758 | `4.1323e-6` |

Residual PCA improves distance RMSE at accurate/full stages, but worsens the
fast stage.

---

## 12. GIST Paired Effects And Gate

All deltas are `residual PCA - current PCA`.

| Stage | Mean-query RMSE delta | Relative effect | Ranking interpretation |
|---|---:|---:|---|
| fast all | `+6.398e-4` | worse | top-100 and inversion also worse |
| accurate prefix 1 | `-4.922e-4` | `-0.602%` | top-100/inversion CIs include zero |
| full | `-5.572e-6` | `-0.331%` | no reliable top-100 or inversion gain |

Additional controls:

```text
accurate-prefix RMSE improvement: 10/10 rotation seeds
rotation-off accurate RMSE:       favorable
fast prefixes:                    consistently worse
identity/random with native plan: faster-looking fast stage, much worse full code
identity/random with frozen plan: substantially worse ranking
```

Phase 1 interpretation:

```text
A small estimator-objective mismatch exists on GIST, but no progressive or
ranking Pareto improvement is established. Standard residual PCA already
explains the signal, so a learned transform is not yet justified.
```

The only authorized continuation was one preregistered external replication.

---

## 13. Attempt 1A Phase 1b Protocol: CIFAR60K

The replication freezes the narrow current-PCA versus residual-PCA comparison.

| Item | Frozen value |
|---|---|
| Dataset | CIFAR60K, `N=60,000`, `D=512` |
| IVF | `K_IVF=512`, same recovered codebook/assignments |
| Budget | `B=4` |
| Queries | all 1,000 held-out queries |
| Fixed probes | 16/query |
| Candidate pairs | 2,130,639/configuration |
| Ranking cutoff | top 100 |
| Plan | `64@9 | 192@5 | 128@3 | 128@0` |
| Transforms | current PCA, residual PCA |
| Rotation controls | 10 paired seeds plus `off` |
| Configurations | `2 x 11 = 22` |
| Bootstrap | 10,000 query-paired replicates |

Registered success required:

```text
confidence interval in the favorable direction
at least 8/10 seeds favor residual PCA
rotation-off direction also favorable
no harm at the fast stage
```

---

## 14. CIFAR60K Replication Result

All deltas are `residual PCA - current PCA`; lower RMSE is better.

| Stage | Current RMSE | Residual RMSE | Relative delta | Seeds favoring residual |
|---|---:|---:|---:|---:|
| fast all | 0.13355750 | 0.13359980 | `+0.0317%` worse | 3/10 |
| accurate prefix 1 | 0.03010816 | 0.03010955 | `+0.00463%` worse | 4/10 |
| full | 0.001108523 | 0.001108262 | `-0.0235%` | 5/10 |

Confidence and controls:

```text
accurate-prefix CI spans zero
full-code CI spans zero
rotation-off accurate/full directions are unfavorable
fast-stage degradation is statistically supported
top-100 and boundary-inversion intervals span zero or point worse
```

Registered decision:

```text
close_one_dataset_estimator_effect
```

The GIST effect does not replicate across the second frozen spectral regime.

---

## 15. Full-D Transform Complexity And Overhead

For a dense full-D PCA implementation:

```text
covariance accumulation: O(N D^2)
eigendecomposition:      O(D^3)
stored operator:         O(D^2)
base transformation:     O(N D^2)
raw-query transformation: O(D^2) per query
```

Residual PCA additionally constructs residuals in `O(ND)`, then has the same
dominant covariance/eigendecomposition scale.

Concrete CIFAR operator state:

```text
(D^2 + D) float32 values
= (512^2 + 512) * 4
= 1,050,624 bytes
```

Concrete GIST dense state:

```text
(960^2 + 960) * 4 = 3,690,240 bytes
```

Current and residual PCA have the same operator shape, so operator size does
not explain their paired result. However, the fixed-candidate study does not
support an end-to-end QPS claim because raw-query transformation was not timed
inside a complete search path.

---

## 16. Attempt 1A Decision

```text
Decision: CLOSE FULL-D PCA REPLACEMENT AS A MAIN DIRECTION
```

Why:

1. GIST shows only small estimator RMSE changes.
2. Fast prefixes worsen.
3. Ranking gains are not statistically stable.
4. Standard residual PCA explains the only stable GIST signal.
5. The preregistered CIFAR replication fails confidence, seed, rotation-off,
   and no-harm requirements.

What was deliberately not implemented:

```text
SAQ-aware learned rotation
joint transform-plan optimization
OPQ/ITQ-style learner integration
broad transform/dataset sweep
new persisted transform format
```

Claim boundary:

```text
This does not prove PCA universally optimal. It says the measured premise is
not strong enough to justify learned replacement development.
```

---

## 17. Attempt 1B: Why Test Lossy `D -> d` Projection?

Full-D transforms preserve dimension and therefore cannot directly reduce code
work or dense query-state size.

More aggressive idea:

```text
retain only the high-variance PCA head
summarize the omitted tail with a small statistic
run quantization/search in d < D dimensions
```

Potential benefit:

```text
fewer dimensions transformed
fewer dimensions encoded
fewer code/factor bytes
less estimator work
```

Risk:

```text
physical projection changes original-space distances and nearest neighbors
```

Related-work boundary:

```text
truncated PCA, LeanVec-style projection, and MRQ-style head/tail refinement
already occupy the broad design space
```

Therefore the first test is an intentionally favorable quality upper bound,
not a projected index implementation.

---

## 18. Lossy Projection Distance Decomposition

Split PCA coordinates into retained head and omitted tail:

```math
q=(q_h,q_t),\qquad x=(x_h,x_t).
```

Original exact squared L2:

```math
D_0=
\lVert q_h-x_h\rVert^2+
\lVert q_t\rVert^2+
\lVert x_t\rVert^2-
2\langle q_t,x_t\rangle.
```

Pure-head projection:

```math
D_{head}=\lVert q_h-x_h\rVert^2.
```

Exact tail-norm surrogate:

```math
D_{head+norm}=
\lVert q_h-x_h\rVert^2+
\lVert q_t\rVert^2+
\lVert x_t\rVert^2.
```

The missing information is exactly:

```math
-2\langle q_t,x_t\rangle.
```

The oracle uses exact float64 head distances and exact tail norms. It adds no
head quantization error, making it strictly more favorable than a deployed
projected SAQ implementation.

---

## 19. Lossy Projection Running Example

Suppose two candidates have identical head distance and equal tail norm:

```text
head distance:       1.00 for both
query tail norm^2:   0.50
base tail norm^2:    0.50 for both
```

But their tail correlations differ:

```text
candidate p: <q_t, p_t> = 0.45
candidate n: <q_t, n_t> = 0.35
```

Exact tail contributions:

```text
p: 0.50 + 0.50 - 2*0.45 = 0.10
n: 0.50 + 0.50 - 2*0.35 = 0.30
```

Exact distances:

```text
p = 1.10
n = 1.30
```

Norm-only surrogate:

```text
p = 2.00
n = 2.00
```

Tail norms remove average bias but cannot distinguish candidates whose omitted
tail inner products carry ranking information.

---

## 20. LP-0 Gate A Protocol

| Item | Frozen value |
|---|---|
| Dataset | GIST sample50k |
| Original dimension | `D=960` |
| Retained head | `d=576`, exactly at an SAQ segment boundary |
| Physical reduction | 40% of dimensions removed |
| IVF | `K_IVF=512` |
| Budget of native comparator | `B=4` |
| Queries | first 128 held-out queries |
| Fixed probes | 16/query |
| Fixed candidates | 442,823 |
| Ranking cutoff | top 100 |
| Oracle head | exact float64 distance over first 576 PCA coordinates |
| Tail | exact float64 norms; float32 deployed summary also measured |
| Comparator | seed-averaged native full-D SAQ full-code estimator |

Native GIST plan:

```text
64@11 | 192@6 | 320@4 | 256@2 | 128@0
                       ^
                    d = 576
```

Projection removes both the `256@2` segment and the `128@0` tail physically.

---

## 21. LP-0 Ranking Result

| Estimator | Top-100 agreement | Boundary inversion rate |
|---|---:|---:|
| exact projected head + exact tail norms | 0.992890625 | `6.85248e-6` |
| native full-D SAQ full code | 0.994617188 | `4.08687e-6` |

Registered deltas, projected oracle minus native SAQ:

```text
top-100 agreement delta       = -0.0017265625
one-sided 95% lower bound     = -0.002578125

boundary inversion delta      = +2.76561e-6
one-sided 95% upper bound      = +4.21688e-6
```

Both ranking gates fail. Rotation-off has the same unfavorable directions:

```text
agreement delta  = -0.00140625
inversion delta  = +2.70090e-6
```

This is not a quantizer implementation failure: the favorable exact surrogate
itself is below native SAQ ranking quality.

---

## 22. LP-0 Error Attribution

Pooled absolute-error summary:

| Component | Bias | MAE | Pooled RMSE |
|---|---:|---:|---:|
| pure head, `D_head-D0` | -0.0339155 | 0.0339155 | 0.0444650 |
| exact norm surrogate, `D_head+norm-D0` | `-3.25e-6` | 0.00150736 | 0.00248180 |
| float32 tail-summary precision | `5.37e-11` | `1.05e-7` | `1.51e-7` |
| deployed norm surrogate total | `-3.25e-6` | 0.00150736 | 0.00248180 |

Interpretation:

```text
tail norms remove nearly all systematic bias
float32 summary precision is negligible
remaining error comes from omitted tail inner-product variation
```

The problem is not storing the tail norm inaccurately. The problem is that one
norm per vector cannot recover query-candidate tail correlation near the top-k
boundary.

---

## 23. Lossy Projection Complexity And Gate Logic

An actual dense `D -> d` projection would require:

```text
stored operator: O(Dd)
base transformation: O(NDd)
raw-query transformation: O(Dd)
head quantization/search: method-dependent O(d)
tail metadata: at least O(1) per vector for norm-only design
```

But Gate A deliberately removes projected-head quantization and runtime from
the quality question:

```text
exact head + exact tail norms already loses to native SAQ
```

Therefore adding:

```text
projected-head CAQ error
progressive-estimator error
projection/index metadata
query transform and preparation work
```

cannot rescue the registered quality premise without introducing a different
tail mechanism. Gate B, projected index construction and Recall-QPS evaluation,
was not authorized.

---

## 24. Attempt 1B Decision

```text
Decision: FAIL GATE A AND STOP THE REGISTERED D=576 LINE
```

Why:

1. The exact head plus exact tail-norm oracle ranks candidates worse than
   native full-D SAQ.
2. The missing tail inner product, not summary precision, dominates the
   residual error.
3. A real projected quantizer would add more error and overhead.
4. Sweeping `d`, `B`, probes, or tail rules after this registered failure would
   be post-hoc rescue.

What the result does not prove:

```text
all lossy projection is ineffective
all dimensions d fail
all richer tail representations fail
PCA truncation is universally inferior
```

A future projection study would require a distinct related-work-grounded
mechanism and a new protocol, not continuation of this line.

---

## 25. Attempt 1 Unified Conclusion

| Sub-attempt | Positive signal | Failed requirement | Final status |
|---|---|---|---|
| 1A full-D residual PCA | GIST accurate/full RMSE improves 0.60%/0.33% | no stable ranking gain; fast harm; CIFAR replication fails | Closed |
| 1B lossy `960 -> 576` | exact tail norms reduce projection RMSE from 0.0445 to 0.00248 | exact favorable surrogate still ranks worse than native SAQ | Closed |

Unified research conclusion:

```text
PCA is not proven universally optimal, but the measured evidence does not
support spending additional degrees of freedom on either a learned full-D
replacement or the registered norm-only lossy projection.
```

Strict-reviewer view:

```text
The full-D signal is small and non-replicated.
The lossy signal fails before quantization is introduced.
Neither supports a new transform method or a system-level Pareto claim.
```

Speaker notes:

- Attempt 1 is a useful example of staged falsification.
- The more aggressive variant was tested with a more favorable oracle, not a
  weaker implementation.

---

## 26. Attempt 2: Research Question

Attempt 2 comes from the sibling repository:

```text
/rwproject/kdd-db/kluaq/vectordb
main checkpoint: f51b487
exact-hist implementation checkpoint: 9a7026d
cross-dataset comparison checkpoint:    870d829
```

Original empirical question:

```text
If each coordinate uses a scalar codebook, can exact 1D dynamic programming
produce a better codebook than Lloyd refinement, and does lower raw
reconstruction SSE improve ANN recall?
```

The 2026-07-13 related-work audit adds a distinct novelty question:

```text
Does White and Singal's 2026 inner-product-aware quantization paper, together
with the exact 1D k-means literature it uses, already subsume Attempt 2?
```

Short answer:

```text
public artifacts: no integrated two-DP pipeline is documented or exposed
combination claim: no novelty is established from that absence
inner exact scalar-codebook DP: already established; no novelty claim remains
local value that remains: controlled baseline and objective-mismatch evidence
```

The paper was submitted on 2026-05-29, before the `vectordb` exact-hist
implementation on 2026-06-26. More importantly, exact 1D quantization DP
predates both by decades.

Speaker notes:

- Attempt 2 is not SAQ's segment-planner DP.
- It is also not the CAQ exact direction-code oracle from the later branch.
- "No integrated public pipeline" must not be misread as "novel as a
  component combination."

---

## 27. Two Different Dynamic Programs

The `vectordb` pipeline contains two DPs.

### Inner DP: scalar codebook training

For one dimension `j` and bitwidth `b`:

```text
input:  one sorted raw scalar column; the trainer internally constructs its
        equal-count weighted histogram
output: K_b centroids minimizing whole-bin partition SSE, with cuts restricted
        to histogram-bin boundaries
```

Only when each raw scalar is its own bin does this equal globally minimal
raw-sample 1D reconstruction SSE. After DP backtracking, raw nearest-centroid
SSE is separately recomputed under the deployed encoding semantics.

### Outer DP: bit allocation

Given one error value `E[j,b]` per dimension and bitwidth:

```math
A[j,c]=\min_b\left(A[j-1,c-b]+w_jE[j,b]\right),
```

subject to:

```math
\sum_j b_j = D B.
```

The outer DP chooses the bitwidth of every dimension under an exact total bit
budget. Attempt 2 changes only the inner trainer from Lloyd to exact-hist; the
outer algorithm, objective form, and weights are held fixed as part of the
evaluation pipeline. The selected bit vector is not fixed: it changes when the
new trainer changes `E[j,b]`.

Novelty accounting must therefore be layer-specific:

```text
inner DP: exact 1D scalar clustering / quantization is prior work
outer DP: classical discrete rate allocation / multiple-choice knapsack
local experiment: asks whether the replacement changes ANN recall
```

---

## 28. Dimensionwise Scalar-Quantization Setting

Write the base matrix as:

```math
X\in\mathbb{R}^{N\times D}.
```

Attempt 2 trains on one column at a time:

```math
X[:,j]=(x_{1j},\ldots,x_{Nj}),
```

and shares the resulting codebook across all `N` base vectors. For database
vector:

```math
x=(x_1,\ldots,x_D).
```

Each dimension has an independent codebook:

```math
C_{j,b}=\{c_{j,b,1},\ldots,c_{j,b,K_b}\}.
```

Base encoding:

```math
\hat x_j=\operatorname*{argmin}_{c\in C_{j,b_j}}(x_j-c)^2.
```

The query remains float. Compressed squared-L2 scan uses:

```math
\hat d(q,x)=\sum_j(q_j-\hat x_j)^2.
```

Candidate bitwidths in variable mode:

```text
b in {0,1,2,3,4,5,6,7,8}
total budget = D * B bits/vector
```

Historical implementation boundary:

```text
unpacked uint8 codes
brute-force compressed scan
L2 only
```

This is an algorithmic diagnostic, not a QPS-comparable SAQ index.

The column-wise training direction matters for the paper comparison. The
paper's formal ASQ problem instead chooses a quantization set from the
coordinates of one input vector; its official code also contains a separate
shared-block helper, audited later.

---

## 29. Exact-Hist Construction

For one sorted dimension with `N` values:

```text
H = min(max_histogram_bins, N)
default H = 256
```

Step 1: split sorted values into `H` equal-count bins.

For each bin, record:

```text
weight
sum
sum_sq
```

and their prefix sums.

Step 2: any contiguous bin interval `[a,b)` has one-centroid optimum:

```math
\mu(a,b)=\frac{sum(a,b)}{weight(a,b)},
```

```math
SSE(a,b)=sum\_sq(a,b)-\frac{sum(a,b)^2}{weight(a,b)}.
```

Step 3: partition the `H` ordered bins into `K_b` contiguous clusters.

Step 4: backtrack split points and use each interval mean as its centroid.

Implementation detail that affects the guarantee:

```text
The histogram DP value is not inserted directly into E[j,b].
After recovering centroids, midpoint Voronoi boundaries are rebuilt, every raw
value is encoded by nearest centroid, and the raw-sample SSE of those encodings
is recomputed and passed to the outer DP.
```

Thus the reported training SSE measures the realized raw encoding, while the
global optimality claim applies only to split points between indivisible bins.
The recomputation evaluates the selected centroid set; it does not reoptimize
that set over raw-sample split points.

---

## 30. Scalar DP Recurrence And Guarantee

Define:

```text
F[k,r] = minimum weighted SSE for the first r bins using k centroids
```

Recurrence:

```math
F[k,r]=\min_{m<r}\left(F[k-1,m]+SSE(m,r)\right).
```

The implementation uses monotone split points and divide-and-conquer DP
optimization to compute each layer.

Exact guarantee:

```text
For fixed H equal-count bins and K_b centroids, the DP returns the minimum
raw-value SSE among contiguous partitions whose split points lie only at bin
boundaries. Prefix weight/sum/sum_sq statistics evaluate each allowed
interval's raw SSE exactly; approximation enters through forbidden in-bin
split points.
```

It does not guarantee:

```text
minimum SSE over all N raw values when H < N
minimum query-distance error
minimum top-k boundary inversion
maximum recall
```

If `H=N`, every bin contains one sample and the formulation becomes full-sample
exact 1D k-means. That expensive configuration was not run in the recorded
experiments.

Strict novelty implication:

```text
The missing full-scale H=N run is a limitation of this local baseline,
not an open algorithmic problem in the literature.
```

The recent paper's official repository directly vendors and exposes a raw
exact 1D k-means solver primitive from earlier work; no public experiment
caller integrates or evaluates that primitive. Scaling the local code by
removing histogram coarsening would therefore close an implementation gap, not
create a method contribution.

---

## 31. White And Singal 2026: Formal Problem

[Inner Product Aware Quantization: Provably Fast, Accurate, and Adaptive
Algorithms](https://arxiv.org/html/2606.00289v1) studies a different formal
quantization problem.

This is a May 2026 arXiv v1 preprint by Nathan White and Krish Singal; this
deck makes no venue-acceptance claim. Its contributions are the MDV/ADV
inner-product objectives, rounding-distribution results, exact/approximate
algorithms, and practical ASQ acceleration, not the invention of exact 1D
k-means.

For one vector `w` and a quantization-set budget `|Q(w)| <= s`, standard
stochastic quantization independently rounds each coordinate to its adjacent
lower or upper point in `Q(w)`, using the unique probabilities that make the
rounding unbiased. Several algorithms then return a set of size `s`.

For an unseen input/query distribution, written as `\mathcal X` below, its
Average Directional Variance is:

```math
\operatorname{ADV}_{\mathcal X}(w,Q)
=\sum_i \lambda_i
(w_i^\uparrow-w_i)(w_i-w_i^\downarrow),
\qquad
\lambda_i=\mathbb E_{x\sim\mathcal X}[x_i^2].
```

The paper also studies Maximum Directional Variance, which controls the worst
coordinate variance rather than their weighted sum.

Key semantic boundary:

```text
paper:     adaptive, unbiased, adjacent stochastic rounding
Attempt 2: shared, biased, deterministic nearest-centroid encoding
```

---

## 32. Related DPs, Different Interval Costs

After jointly sorting coordinate-weight pairs so that
`w_1 <= ... <= w_d` while each `lambda_i` remains attached to its original
coordinate, define the paper's ADV interval cost:

```math
C[j,k]=\sum_{i=j}^{k}\lambda_i
(w_k-w_i)(w_i-w_j).
```

A conventional equivalent form of its quantization-set DP is:

```math
G[t,k]=\min_{j<k}\left(G[t-1,j]+C[j,k]\right).
```

Here `G[t,k]` is the best cost for `t` selected quantization points ending at
`w_k`, with `G[1,1]=0`; the answer is `G[s,d]`.

Attempt 2 instead uses a best-mean interval cost:

```math
F[t,r]=\min_{m<r}
\left(F[t-1,m]+SSE_{\mathrm{mean}}(m,r)\right).
```

The relationship is structural, not semantic:

| Property | Paper ADV/ASQ | Attempt 2 inner DP |
|---|---|---|
| Ordered objects | coordinates of one vector | weighted bins from one database column |
| Interval representative | two stochastic endpoints | one deterministic mean |
| Interval cost | weighted rounding variance | centroid reconstruction SSE |
| Shared skeleton | sorted contiguous partition with Monge structure | sorted contiguous partition with monotone splits |

The paper explicitly notes that if biased quantization is allowed, the optimal
scheme is 1D k-means plus nearest-cluster assignment. That observation places
Attempt 2's mathematical core inside established related work.

---

## 33. The Training Axis Is Transposed

Let `X` be an `N x D` database matrix.

| Question | Attempt 2 | Paper formal model |
|---|---|---|
| Optimization input | column `X[:,j]`, containing `N` database scalars | row/vector `X[i,:]`, containing `D` coordinates |
| Learned set | `C[j,b]` for one dimension and bitwidth | `Q(X[i,:])` for one vector |
| Sharing | all `N` database vectors share `C[j,b]` | different vectors may have different `Q` |
| Rate choice | heterogeneous `b_j`, exact total budget | one cardinality budget `s`, with `|Q| <= s`, per formal instance |
| Encoding/objective semantics | biased deterministic nearest-centroid SSE | unbiased stochastic rounding optimized for IP variance |

The paper's formal vector-search limitation follows from this orientation: it
requires per-vector `Q` storage. Its discussion therefore leaves adaptation to
potentially dynamic multi-vector quantization as
[future work](https://arxiv.org/html/2606.00289v1#S5).

This formal difference is real, but it is not enough to establish Attempt 2
novelty: dimensionwise shared scalar codebooks and discrete rate allocation are
themselves classical constructions.

---

## 34. Official-Code Audit: Stronger Adjacency

The pinned
[official repository](https://github.com/nathanllww/Inner-Product-Aware-Quantization/tree/e92ed904b85ad12469a0a350c81071ff9ef6aa37)
contains more than the paper's formal per-vector interface:

```text
batch_row_quant(X, ...)
  one Q per row/vector; matches the formal adaptive direction

block_quant(X, m, s, ...)
  flatten all N*m values in each consecutive m-column block
  and train one shared size-s Q for that block

kmeans_wilber_1d(sorted_points, k)
  raw-point globally optimal 1D k-means implementation
  requires ascending input; the wrapper does not sort
```

Pinned source:
[shared-block and per-row interfaces](https://github.com/nathanllww/Inner-Product-Aware-Quantization/blob/e92ed904b85ad12469a0a350c81071ff9ef6aa37/cython/pq.pyx#L16-L202),
[raw exact 1D k-means wrapper](https://github.com/nathanllww/Inner-Product-Aware-Quantization/blob/e92ed904b85ad12469a0a350c81071ff9ef6aa37/cython/kmeans1d.pyx#L38-L85).

Consequently, `block_quant(..., m=1, ...)` has exactly the same training axis
as a fixed-rate shared per-dimension codebook. However:

```text
it calls vmix_approx for ADV rather than centroid-SSE k-means
all blocks receive the same s
there is no per-dimension error table or outer bit-allocation DP
```

The `block_quant` docstring says `exact_adv`, while the pinned implementation
calls `vmix_approx`; the implementation is the evidence used here. The public
repository contains no caller or experiment script that proves which path
generated the paper's GloVe table, so this deck makes no such attribution.

The paper calls its GloVe result preliminary evidence and reports Recall@100
for L2 and maximum-inner-product search at an average four bits per coordinate.
It does not report a controlled Lloyd-versus-exact trainer ablation, QPS/build
cost, or complete quantization-set storage accounting. That table therefore
does not answer the specific Attempt 2 end-to-end question.

---

## 35. Prior-Art And Layer-By-Layer Verdict

| Attempt 2 layer | Formal paper | Pinned public code | Strict-reviewer verdict |
|---|---|---|---|
| Raw exact 1D k-means optimizer | Recognizes it as older related work | Exposes `kmeans_wilber_1d` from the reused exact-1D library | Novelty foreclosed by Wu 1991 / GLM 2017; not a White-Singal contribution |
| Shared per-dimension fixed-rate set | Formal unit is one vector | `block_quant(m=1)` is directly adjacent but uses ASQ semantics | Not a formal guarantee; shared scalar codebooks are not enough for novelty |
| Potential diagonal query-second-moment weighting | ADV supplies diagonal second moments under per-vector independent unbiased rounding | `block_quant` uses all-one weights; no such experiment is exposed | High objective-level adjacency, not direct pipeline coverage or a validity proof for biased SQ |
| Multi-bit error table `E[j,b]` | Fixes one cardinality budget `s`; no table | Repeated fixed-`s` calls are an API inference, not integrated or evaluated | Not claimed novel here; separate rate-distortion prior support is required |
| Outer heterogeneous-bit DP | Not presented | Not exposed | Not covered by this paper, but [SAQ](https://arxiv.org/abs/2509.12086) already provides DP segmentation/bit allocation |
| Controlled Lloyd/exact-hist L2 recall audit | Only preliminary GloVe L2/MIPS comparison against PQ | No public experiment caller/configuration | Useful local negative/baseline evidence, not a quantizer contribution |
| Packed variable-rate ANN system | Per-vector storage is listed as a limitation/future-work issue | Fixed-rate block helper and 256-code search helper only | A possible problem layer, not an achieved result in either artifact |

Timeline:

```text
paper and official code:       2026-05-29
vectordb exact-hist checkpoint: 2026-06-26
```

The stronger point is not temporal priority. The paper itself traces exact 1D
k-means matrix-search DP to Wu 1991. Separately, the pinned code exposes a
solver primitive from the reused
[2017 exact-1D-clustering implementation](https://arxiv.org/abs/1701.07204),
without an integrated public experiment path.

Bottom line:

```text
public-artifact level: no integrated shared-codebook + heterogeneous-bit +
                       outer-allocation pipeline is documented or exposed
novelty level:         absence is not combination novelty; the inner optimizer
                       is foreclosed by older prior art, and remaining system
                       layers were not built or validated by Attempt 2
```

---

## 36. Attempt 2 Code Map

Sibling repository code:

```text
src/scalar_quantizer.cpp
  BuildEqualCountHistogram(...)
  HistogramIntervalSse(...)
  ComputeExactKMeansLayer(...)
  TrainExactScalarQuantizerFromSorted(...)
  midpoint boundaries, raw nearest-centroid reassignment, raw SSE

src/dimensionwise_quantizer.cpp
  per-dimension/per-bitwidth training

src/bit_allocator.cpp
  total-budget bit-allocation DP

src/eval_dimensionwise_quantizer.cpp
  training, encoding, brute-force scan, recall output
```

Main evidence:

```text
vectordb/docs/dimensionwise_quantizer_smoke_run_2026_06_26.md
vectordb/reports/scalar_training_exact_hist_audit_2026_06_30/README.md
vectordb/reports/scalar_training_exact_hist_audit_2026_06_30/comparison.csv
```

CLI:

```text
eval_dimensionwise_quantizer ... [lloyd|exact-hist] [histogram_bins]
```

---

## 37. Attempt 2 Complexity

For one dimension and one bitwidth after sorting:

| Stage | Complexity |
|---|---:|
| Equal-count histogram build | `O(N)` |
| Interval SSE query | `O(1)` |
| Divide-and-conquer histogram DP | approximately `O(K_b H log H)` |
| Backtracking | `O(K_b)` |
| Final raw-value SSE | `O(N log K_b)` |

Including the one-time dimension sort:

```text
O(N log N + N log K_b + K_b H log H)
```

Variable mode trains candidate bitwidths `0..8`:

```text
O(D * [N log N + sum_b(N log K_b + K_b H log H)])
```

The outer allocation DP has approximately:

```text
time   O(D * (D B) * |bitwidth choices|)
cost rows with rolling layers: O(D B)
backpointers for reconstruction: O(D * D B)
current total memory:           O(D * D B)
```

Its optimality is conditional:

```text
Given one trainer-specific raw SSE table E[j,b], fixed weights w_j, the
candidate set b in {0,...,8}, and a reachable budget, the outer DP finds the
minimum table objective. It does not make the inner codebooks or Recall
globally optimal.
```

Full-sample `H=N` exact training would replace the small histogram term with
approximately `O(K_b N log N)` per dimension/bitwidth. It was judged too
expensive for full DEEP1M and was not evaluated.

---

## 38. Exact-Hist Running Example

One-dimensional sorted values:

```text
0, 1, 2, 10, 11, 12
```

Let:

```text
H = 6 bins, one value/bin
K_b = 2 centroids
```

The DP evaluates every legal split through the recurrence. The optimum is:

```text
cluster 1 = {0,1,2},  centroid = 1
cluster 2 = {10,11,12}, centroid = 11
```

SSE:

```text
(0-1)^2 + (1-1)^2 + (2-1)^2
+ (10-11)^2 + (11-11)^2 + (12-11)^2
= 4
```

With `H=2`, each bin would already contain three values. The same partition is
available, but an optimal raw split inside a bin would not be. This is the
difference between histogram exactness and raw-sample exactness.

---

## 39. Audio Result: Lloyd Versus Exact-Hist

Dataset:

```text
audio base = 53,387 x 192
audio query = 200 x 192
metric = L2
mode = variable
B = 4
H = 256
source = initial H=256 comparison run
```

| Trainer | MSE/value | R@10 | R@100 | Training time |
|---|---:|---:|---:|---:|
| Lloyd | 280,023 | 0.9260 | 0.95275 | 2,004.68 ms |
| exact-hist | 236,478 | 0.9270 | 0.95675 | 1,864.28 ms |

At this operating point:

```text
MSE improvement ~= 15.5%
R@10 delta       = +0.0010
R@100 delta      = +0.0040
```

This is a positive example, but it does not establish stable recall dominance
or a new scalar-quantization contribution.

---

## 40. Audio Histogram-Bin Sweep

`B=4`, variable allocation, later sweep rerun:

| Histogram bins `H` | MSE/value | R@10 | R@100 | Training time |
|---:|---:|---:|---:|---:|
| 256 | 236,478 | 0.9270 | **0.95675** | 1,776 ms |
| 512 | 235,292 | 0.9340 | 0.95615 | 2,418 ms |
| 1,024 | 234,918 | **0.9345** | 0.95610 | 3,858 ms |
| 2,048 | **234,844** | 0.9335 | 0.95625 | 7,018 ms |

Observation:

```text
Increasing H improves the reconstruction objective almost monotonically,
but R@100 is not monotonic and training time grows substantially.
```

At `B=8`, `H=256` is especially coarse because `K_b=256`: one centroid per
histogram bin leaves little partition freedom. Increasing `H` improves the
result, but the best MSE and best recall still occur at different bin counts.

The `H=256` training time here and on the previous slide comes from separate
runs; it is not an internal consistency check on timing noise.

---

## 41. PCA CIFAR/DEEP Comparison

All rows use `H=256` and variable bit allocation. Raw SSE ratio is the reported
unweighted nearest-centroid `training_sse`, `exact-hist / Lloyd`; recall delta
is `exact-hist - Lloyd`.

| Dataset | B | Allocation objective | Raw SSE ratio | R@100 delta |
|---|---:|---|---:|---:|
| CIFAR60K | 2 | reconstruction | 0.9737 | +0.00313 |
| CIFAR60K | 2 | rank-boundary | 0.9336 | +0.00378 |
| CIFAR60K | 4 | reconstruction | 1.0425 | -0.00024 |
| CIFAR60K | 4 | rank-boundary | 0.9371 | -0.00046 |
| DEEP1M | 2 | reconstruction | 0.9774 | +0.00751 |
| DEEP1M | 2 | rank-boundary | 0.9477 | +0.00681 |
| DEEP1M | 4 | reconstruction | 0.8847 | +0.00304 |
| DEEP1M | 4 | rank-boundary | **0.8016** | **-0.00215** |

Two different effects appear:

1. CIFAR `B=4` reconstruction shows histogram exactness does not guarantee
   lower raw-sample SSE.
2. DEEP `B=4` rank-boundary shows that much lower unweighted raw reconstruction
   SSE still does not guarantee higher recall.

Important correction to the earlier deck interpretation:

```text
DEEP B=4 rank-boundary allocation objective
Lloyd:      1070.81
exact-hist: 1551.93
```

The weighted outer objective worsened in that cell. Therefore it is evidence
against using raw SSE as a recall surrogate, not evidence that a lower
rank-boundary allocation objective failed to improve recall.

---

## 42. Why Lower Reconstruction SSE Need Not Improve Recall

Define base-vector quantization error:

```math
e_x=\hat x-x.
```

Only the base is quantized; the query remains float. Distance error is:

```math
\Delta_x=
\hat d(q,x)-d(q,x)
=-2(q-x)^Te_x+\lVert e_x\rVert^2.
```

Scalar k-means minimizes the second-order reconstruction term aggregated over
base vectors:

```math
\sum_x\lVert e_x\rVert^2.
```

It does not directly control:

```math
-2(q-x)^Te_x,
```

which depends on query direction and signed correlation with the quantization
error.

For a positive `p` and negative `n`, exact margin is:

```math
m=d(q,n)-d(q,p)>0.
```

Estimated margin is:

```math
\hat m=m+\Delta_n-\Delta_p.
```

Recall depends on the sign of this margin, not average reconstruction SSE.

---

## 43. Ranking Running Example

Exact distances near the retrieval boundary:

```text
positive p = 1.000
negative n = 1.010
margin     = 0.010
```

Method A has smaller but oppositely signed errors:

```text
Delta_p = +0.006
Delta_n = -0.006

estimated p = 1.006
estimated n = 1.004
result: inversion
```

Method B has larger common-mode error:

```text
Delta_p = +0.020
Delta_n = +0.020

estimated p = 1.020
estimated n = 1.030
result: ordering preserved
```

This is why a codebook or coupled variable-bit pipeline with lower raw
reconstruction SSE can nevertheless have lower recall: ranking depends on
differential error across close candidates.

---

## 44. Bit-Allocation Coupling

Changing the scalar trainer changes the full error table:

```math
E[j,b]=\text{raw nearest-centroid SSE for dimension j at bitwidth b}.
```

The outer DP then selects a different bit vector:

```math
(b_1,\ldots,b_D).
```

DEEP1M `B=4`, historical rank-boundary objective:

```text
Lloyd histogram:
1b:61, 2b:36, 3b:33, 4b:27, 5b:19, 6b:19, 7b:13, 8b:48

Exact-hist histogram:
1b:40, 2b:48, 3b:33, 4b:30, 5b:26, 6b:28, 7b:37, 8b:14
```

Consequently recall differences combine:

```text
centroid movement
encoding-boundary movement
dimension bit reallocation
surrogate-objective mismatch
```

Given this trainer-specific table and fixed weights, the outer DP is exact over
the enumerated bitwidths and reachable total budget. It does not isolate a pure
inner-trainer effect: changing the trainer also changes the selected bit vector.

Historical disclosure:

```text
rank-boundary weights use query/ground-truth-derived pairs.
They are evidence about objective behavior, not an admissible method under the
current query-unaware project constraint.
```

---

## 45. Attempt 2 Decision

```text
Decision: KEEP EXACT-HIST AS A STRONG OFFLINE BASELINE, NOT A MAIN METHOD
```

What the experiment establishes:

1. The bin-restricted DP is implemented and can materially lower reported raw
   reconstruction SSE after nearest-centroid reassignment.
2. It sometimes improves recall, especially at lower bit budgets.
3. Historical rank-boundary gains over reconstruction survive both Lloyd and
   exact-hist, so they are not only a Lloyd artifact.
4. Lower raw SSE is not a stable surrogate for ANN ranking quality.

What the related-work audit establishes:

1. The White-Singal paper and pinned public code do not document or expose an
   integrated shared-codebook, heterogeneous-bit, outer-allocation pipeline.
2. The pinned code separately exposes a directly adjacent shared-block helper
   and a full-raw-data exact 1D k-means solver primitive; neither is shown as an
   integrated or evaluated Attempt 2 pipeline.
3. Exact 1D scalar clustering is much older than either project; the formal
   paper explicitly recognizes that prior.

Why it is not a method contribution:

1. Split points are exact only under a chosen histogram boundary restriction.
2. Full-sample exact DP was not evaluated at full scale.
3. Lower SSE does not provide a recall guarantee.
4. Recall gains are non-monotonic across `H`, datasets, budgets, and allocation
   objectives.
5. The inner optimizer's novelty is foreclosed by Wu 1991 / GLM 2017; outer
   DP novelty is not claimed here, and SAQ already supplies direct ANN prior.
6. The historical rank-boundary outer objective is query/ground-truth-aware.
7. Unpacked byte codes and brute-force L2 scan do not establish a competitive
   packed variable-rate ANN system.

Strict-reviewer summary:

```text
No integrated end-to-end pipeline is visible in the paper/public code, but
that absence does not establish combination novelty. The inner optimizer is
prior art and the unbuilt system layer remains unvalidated. This is a useful
baseline and objective-mismatch result, not a new ANN quantizer or
database-systems method.
```

---

## 46. Attempt 3: Research Question

Recall@`k` measures exact identifier overlap. For exact top-`k` set `E_k(q)`
and returned set `A_k(q)`:

```text
Recall@k(q) = |E_k(q) intersect A_k(q)| / k.
```

This can penalize a geometrically near-equivalent replacement at a dense
top-`k` boundary. Attempt 3 therefore asks:

```text
Does paper-exact distance quality change the Pareto interpretation of any
previously frozen SAQ comparison, when both plans are evaluated on the same
search-effort grid?
```

The premise is about evaluation validity, not a new quantizer:

```text
Recall:       Did we return the same identifiers?
1/Ratio:      How far are the returned vectors compared with the exact ranks?
```

---

## 47. Attempt 3 Metric: `1/Ratio@k`

For query `q`, define:

- `d_i(q)`: true Euclidean distance to the exact neighbor at distance rank
  `i`, for `i=1,...,k`;
- `d_tilde_i(q)`: true Euclidean distance at rank `i` after independently
  sorting the `k` returned identifiers by true distance.

The metric from
[ANN Search: Recall What Matters](https://arxiv.org/abs/2606.04522v1) is:

```text
Ratio@k(q) = (1/k) * sum_{i=1}^k d_tilde_i(q) / d_i(q)

1/Ratio@k(q) = k / sum_{i=1}^k d_tilde_i(q) / d_i(q).
```

Properties under valid exact top-`k` input:

```text
0 < 1/Ratio@k <= 1
higher is better
1 means equal distance quality, even if tied identifiers differ
```

Critical semantic detail: SAQ internally reports squared L2 distances, but
this metric uses Euclidean distances. The evaluator must take square roots
before forming the ratios.

---

## 48. Attempt 3 Running Example

Let `k=3`. Suppose the exact result distances are:

```text
d = [1.00, 1.10, 1.20].
```

The ANN result shares only one exact identifier, but after recomputing and
sorting true distances it has:

```text
d_tilde = [1.00, 1.11, 1.21].
```

Then:

```text
Recall@3 = 1/3 = 0.3333

1/Ratio@3
  = 3 / (1.00/1.00 + 1.11/1.10 + 1.21/1.20)
  = 0.9942.
```

Interpretation:

```text
identifier recovery is poor
geometric result quality is nearly exact
```

This example does not imply that Recall is wrong. It shows that the two
metrics answer different scientific questions.

---

## 49. Related Work And Novelty Gate

The metric paper already contributes:

1. the judge-free, hyperparameter-free `1/Ratio@k` definition;
2. evaluation of Annoy, SuCo, HNSW, RaBitQ, and SymphonyQG on six datasets;
3. build, memory, distance-work, classification, and RAG analyses; and
4. evidence that less search effort can satisfy a distance-quality target than
   an equal-valued Recall target.

At `k=100` and quality `0.95`, it reports the following average ratios between
the effort required by Recall and by `1/Ratio`:

| Method | Relative distance-computation effort |
|---|---:|
| HNSW | `9.36x` |
| RaBitQ | `2.48x` |
| SymphonyQG | `2.38x` |
| SuCo | `1.86x` |
| Annoy | `3.22x` |

Strict-reviewer constraint:

```text
The metric is prior work, and the paper reports that relative algorithm
rankings are usually stable. Re-evaluating SAQ is not a method contribution.
```

Attempt 3 was therefore authorized only as a frozen retrospective
falsification study. It could clarify prior evidence, but could not fit a plan
to benchmark queries or claim the metric as novelty.

---

## 50. Frozen Attempt 3 Protocol

Stages:

```text
A3-0  validate the paper-exact evaluator on deterministic fixtures
A3-1  replay the frozen GIST default-versus-fac-error comparison
A3-2  test frozen DEEP B=4/B=5 rejected plans as negative controls
A3-3  apply the preregistered cross-dataset decision gate
```

| Variable | GIST A3-1 | DEEP A3-2 |
|---|---:|---:|
| base vectors `N` | 100,000 | 100,000 |
| queries `Q` | 1,000 | 1,000 |
| dimension `D` | 960 | 256 |
| IVF clusters `K_IVF` | 512 | 512 |
| nominal budget `B` | 4 | 4 and 5 |
| result size `k` | 100 | 100 |
| `nprobe` grid | 20, 50, 100, 160, 200, 220, 240, 280, 300, 320, 400 | 50, 100, 200, 400 |

Frozen common settings:

```text
threads = 24
QPS repetitions = 10 per row
searcher_safe_block_min_mode = 2
searcher_vars_bound_m = 4
PCA = enabled, retaining all D dimensions
```

`nprobe` is the number of IVF cells scanned. Mode `2` is the previously fixed
correctness-preserving block-min path, and `m=4` is SAQ's unchanged variance
bound multiplier. Neither is a parameter of `1/Ratio`; no value was selected
from Attempt 3 outcomes.

---

## 51. Evaluator And Search-Code Semantics

Core evaluator logic on branch `saq-ratio-metric-analysis`:

```python
exact = sorted(true_l2(base[groundtruth_ids], query))
returned = sorted(true_l2(base[result_ids], query))
inverse_ratio = k / sum(returned[i] / exact[i] for i in range(k))
```

The implementation in `script/evaluate_inverse_ratio.py`:

1. recomputes both sets of distances in float64;
2. independently sorts by true Euclidean distance;
3. rejects duplicate, invalid, truncated, or non-finite result rows;
4. stops explicitly if an exact distance is zero; and
5. preserves every query-level value instead of only the mean.

The existing upstream `utils::get_ratio` was not used as the scientific
artifact because it reports forward `Ratio`, skips tiny squared distances with
an epsilon, and discards query-level values.

`src/test_qps.cpp` exports result IDs only after the timed search region. Thus
the evaluator can replay exact returned sets without inflating measured QPS.
Eighteen deterministic Python tests cover exact, tied-distance, reordered,
squared-L2, malformed-input, provenance, and frontier cases.

---

## 52. Attempt 3 Complexity And Overhead

Given `Q` queries, returned top-`k`, and dimension `D`:

```text
recompute exact and returned distances: O(Q k D) time
sort each query's distance lists:       O(Q k log k) time
Recall and ratio aggregation:           O(Q k) time
stored result identifiers:              O(Q k)
stored per-query metric values:         O(Q)
```

No `O(QND)` exhaustive search is required when exact top-`k` identifiers
already exist. Only the `2Qk` selected-vector distances are recomputed.

Separation of costs:

```text
ANN query latency / QPS: unchanged; result export is outside the timer
benchmark evaluation:    O(Q k D), reported separately
index build and storage: unchanged
```

The evaluator has no learned parameters. `k` is the benchmark result size,
and the `nprobe` values describe the measured search-effort curve rather than
a fitted decision rule.

---

## 53. GIST Comparison: Two Frozen Global Plans

Setting: `gist_sample100k`, `K_IVF=512`, `B=4`, `D=960`, `k=100`.

```text
SAQ default: 64x11 | 192x6 | 320x4 | 256x2 | 128x0
fac-error:   192x9 | 512x4 | 256x0
```

Each `dimensions x bits` term means that every coordinate in the contiguous
PCA segment receives that many code bits. Both plan strings sum to 960
dimensions and were materialized as frozen SAQ `B=4` indexes before Attempt 3.
The plan string alone is not total index-byte accounting because SAQ also
stores per-segment factors.

The comparison changes only the global plan:

```text
same PCA vectors and IVF assignments
same CAQ encoder and serialized index format
same distance estimator, pruning, heap, and safe-search mode
same nprobe grid, threads, and repetitions
```

The fac-error plan has two positive-bit segments instead of four, so it is a
plausible lower-search-work shape. Its name refers to the historical offline
plan artifact; Attempt 3 neither refits nor endorses that empirical objective.

---

## 54. GIST Complete Common-Grid Result

| nprobe | default R@100 | fac R@100 | default 1/Ratio | fac 1/Ratio | default QPS | fac QPS |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.75957 | 0.75952 | 0.993860620 | 0.993858359 | 31234.2 | 36687.1 |
| 50 | 0.92809 | 0.92769 | 0.998671018 | 0.998668346 | 20104.2 | 25581.3 |
| 100 | 0.98140 | 0.98069 | 0.999773561 | 0.999769939 | 13825.0 | 18572.6 |
| 160 | 0.99036 | 0.98958 | 0.999964379 | 0.999960461 | 10524.5 | 14189.3 |
| 200 | 0.99132 | 0.99059 | 0.999985301 | 0.999981452 | 9264.9 | 12333.9 |
| 220 | 0.99149 | 0.99079 | 0.999987377 | 0.999983555 | 8777.6 | 11739.0 |
| 240 | 0.99153 | 0.99084 | 0.999988670 | 0.999984881 | 8313.8 | 11073.8 |
| 280 | 0.99163 | 0.99091 | 0.999991688 | 0.999987869 | 7579.7 | 9986.9 |
| 300 | 0.99164 | 0.99091 | 0.999992743 | 0.999988921 | 7329.5 | 9522.1 |
| 320 | 0.99164 | 0.99091 | 0.999993271 | 0.999989447 | 7035.6 | 9086.9 |
| 400 | 0.99164 | 0.99091 | 0.999993271 | 0.999989447 | 6111.4 | 7784.3 |

At every equal `nprobe`, fac-error is faster and slightly worse under both
quality metrics. Equal search effort is therefore not the scientific
comparison; the relevant question is QPS at matched quality.

---

## 55. GIST Metric-Sensitive Operating Point

Use the freshly replayed default `nprobe=200` row as the frozen target:

```text
default Recall@100:    0.991320000000
default 1/Ratio@100:   0.999985300968
default QPS:           9264.923
```

Recall conclusion:

```text
maximum measured fac-error Recall = 0.99091
target 0.99132 is unreachable
decision: reject at this reference quality
```

Distance-quality conclusion:

```text
fac-error nprobe=280  1/Ratio@100 = 0.999987869279
fac-error nprobe=280  QPS         = 9986.910
quality               > default target
QPS ratio             = 1.07793x
```

This is a directly measured point, not interpolation. Linear interpolation
between fac-error `nprobe=240` and `280` estimates `1.17876x` QPS exactly at
the target, but this is reported only as secondary evidence.

---

## 56. GIST Query-Level Attribution

For fac-error `nprobe=280` minus default `nprobe=200`:

| Statistic of paired `1/Ratio@100` delta | Value |
|---|---:|
| mean | `+2.5683e-6` |
| median | `0` |
| minimum | `-3.1166e-4` |
| p01 | `-1.1754e-4` |
| p05 | `-4.1993e-5` |
| queries worse | `39.6%` |
| queries equal | `23.0%` |
| queries better | `37.4%` |

The alternative improves the aggregate mean and its separately measured
marginal lower-tail statistics, but it does not dominate query by query.

Strict interpretation:

```text
supported:   the historical GIST operating-point rejection is metric-sensitive
unsupported: fac-error is uniformly better or provides a per-query guarantee
```

This paired distribution is why the mean metric alone is insufficient for a
new method claim.

---

## 57. DEEP Negative Controls

Frozen plans:

```text
B=4 default:   64x6 | 192x3     candidate: 128x4 | 128x3
B=5 default:   64x7 | 192x4     candidate: 128x5 | 128x4
```

| B | nprobe | default R | candidate R | default 1/Ratio | candidate 1/Ratio | QPS ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 50 | 0.94550 | 0.92381 | 0.998803057 | 0.998540024 | 1.075x |
| 4 | 100 | 0.97061 | 0.94401 | 0.999686070 | 0.999416524 | 1.095x |
| 4 | 200 | 0.97641 | 0.94884 | 0.999904123 | 0.999633936 | 1.071x |
| 4 | 400 | 0.97713 | 0.94940 | 0.999930322 | 0.999658856 | 1.046x |
| 5 | 50 | 0.95180 | 0.94251 | 0.998842845 | 0.998776284 | 1.108x |
| 5 | 100 | 0.97973 | 0.96687 | 0.999728710 | 0.999659199 | 1.092x |
| 5 | 200 | 0.98670 | 0.97241 | 0.999948614 | 0.999877534 | 1.077x |
| 5 | 400 | 0.98752 | 0.97304 | 0.999974940 | 0.999903505 | 1.043x |

Neither candidate reaches its default `nprobe=200` `1/Ratio` target anywhere
on the measured curve. At `nprobe=200`, 97.1% of B=4 queries and 87.3% of B=5
queries are worse. Therefore `1/Ratio` is not merely accepting every faster,
lower-Recall plan: both DEEP negative decisions remain negative.

---

## 58. Attempt 3 Decision

| Predeclared condition | Outcome |
|---|---|
| at least one previous conclusion changes | pass: GIST historical reference |
| change survives a complete measured curve | pass: 11-point GIST union grid |
| positive result appears on two datasets or independent baselines | fail: DEEP provides controls, not a second positive |
| query-level tails show no hidden material loss | mixed: 39.6% of paired GIST queries worsen |
| a mechanism-level gap remains after related work | fail: no mechanism beyond the old fac-error plan |

```text
Decision: CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE
```

What survives:

1. report Recall and `1/Ratio` together in future ANN studies;
2. distinguish identifier-boundary loss from geometric degradation; and
3. retain GIST as a concrete metric-sensitive SAQ case and DEEP as controls.

What does not reopen:

```text
fac-error plan sweeps
query-fitted metric-aware planning
lossy projection or exact-hist as methods
high-overhead CAQ, mixed-plan, graph-prefix, or search-bound directions
```

The metric paper owns the general contribution. Our evidence is a bounded SAQ
case study, not an independent database-systems method.

---

## 59. Attempt 4: Research Question And Current Gate

Scientific-content snapshot: `saq-arbitrary-cardinality-analysis@3c0a49f`

| Stage | Committed status | What it means |
|---|---|---|
| A4-0 synthetic instrument | `PASS_INSTRUMENT_ONLY` | formulation, tiny witness, and reference checks passed |
| A4-1P base-only protocol | `FROZEN_NOT_AUTHORIZED` | scientific inputs and decision rule are registered; base read is forbidden |
| A4-1S synthetic implementation | `FROZEN_AUTHORIZED_NOT_IMPLEMENTED` | implementation/parity/cost work is authorized, but no committed result exists |
| SAQ/index/search integration | `NOT_AUTHORIZED` | no production representation or query-path change may be made |

Research question:

```text
Under one fixed B_g-bit word for a two-factor group, can positive-integer
scalar cardinalities use the joint-state budget more effectively than
power-of-two cardinalities while retaining one random-access word and one
expanded-table lookup per group?
```

The competing factorized feasible sets are:

```text
dyadic:     K_j in {1, 2, 4, 8, ...}
arbitrary:  K_j in positive integers
both:       product_j K_j <= S = 2^B_g
```

This is a fixed-address coding opportunity study. It does not modify CAQ or
SAQ, and it currently makes no natural-data, Recall, QPS, or systems claim.

---

## 60. Correct Fixed-Rate Formulation And Witness

First correct a tempting but invalid rate comparison:

```text
(3,3) has 9 joint states and needs 4 fixed bits.
It cannot be compared at equal fixed rate with a 3-bit (4,2) product.
```

The frozen equal-rate witness instead uses:

| Quantity | Value |
|---|---:|
| word width | `B_g=4` bits |
| joint capacity | `S=16` addresses |
| best arbitrary witness allocation | `(3,5)`, 15 used states |
| selected dyadic allocation | `(4,4)`, 16 used states |

For two factors with zero-based labels `z_1` and `z_2`, mixed-radix addressing
is direct:

```text
u = z_1 + K_1 z_2,        0 <= u < K_1 K_2 <= S.
```

The address is still one fixed word and the query interface is still one
`S`-entry lookup per group. Unused addresses remain paid capacity; entropy or
Huffman expected length is not a fixed-payload saving.

The only unconditional optimization statement is:

```text
D*_arbitrary <= D*_dyadic
```

for the same exact factorized reconstruction-SSE objective, because the
arbitrary-cardinality feasible set contains the dyadic set. It is not a
Recall, QPS, or block-VQ dominance theorem.

---

## 61. Prior Art And Claim Boundary

The following are known ingredients, not Attempt 4 novelty:

```text
non-power-of-two scalar quantization
transform coding and bit allocation
adaptive or irregular product quantization
mixed-radix fixed addressing
finite scalar quantization and non-dyadic palette constructions
entropy-constrained and variable-length coding
```

Therefore a publishable claim would need evidence beyond the primitive:

1. a material gap on natural ANN residuals at matched fixed payload;
2. a same-capacity trained block-VQ control, because unrestricted block VQ
   weakly dominates a factorized codebook in reconstruction expressiveness;
3. complete training, metadata, expanded-table, packing, and scan-cost
   accounting; and
4. only after a new frozen systems protocol, a replicated Recall-throughput
   effect against competitive baselines.

Current decision:

```text
CONDITIONAL GO FOR OFFLINE FEASIBILITY ONLY
```

The direction is allowed to try to falsify the fixed-word opportunity. It is
not allowed to claim a new quantization primitive or to enter SAQ integration.

---

## 62. A4-0 Synthetic Instrument Result

| Quantity | Observed |
|---|---:|
| fixed capacity | 16 |
| arbitrary cardinalities / used states | `(3,5)` / 15 |
| arbitrary distortion per vector | 0 |
| dyadic cardinalities / used states | `(4,4)` / 16 |
| dyadic distortion per vector | 0.1 |
| mixed-radix LUT/direct L2 maximum difference | 0 |
| unrestricted 16-codeword block-VQ distortion | 0 |

The constructed feasible-set gap is recovered exactly:

```text
D*_dyadic - D*_arbitrary = 0.1 per vector.
```

Seven deterministic tests pass: exact scalar DP, duplicate/weighted support,
both allocation modes against exhaustive enumeration, all 15 mixed-radix
tuples, expanded-LUT/direct-distance parity, and the frozen witness/Huffman
values.

Interpretation ceiling:

```text
PASS_INSTRUMENT_ONLY
```

The unrestricted block-VQ oracle also reaches zero. No dataset, query, ground
truth, PCA, IVF, or SAQ artifact was used. The result validates the reference
instrument and strict dyadic-feasible-set witness, not a practical method.

---

## 63. Frozen A4-1 Base-Only Falsification Gate

Status: `FROZEN_NOT_AUTHORIZED`

If later authorized, A4-1 would use query-unaware GIST sample50k and CIFAR60K
residual panels at fixed 4-bit and 8-bit two-factor words. Its primary arms are:

```text
dyadic_word
arbitrary_word
trained_block_vq          same joint capacity
```

A global capped dyadic pack is retained as an attribution control. It has the
same 32/64-byte database payload but a different 128-scalar-lookup interface,
so it cannot silently replace the matched-word comparison.

For items 1--4 below, passage requires Holm-adjusted one-sided evidence to
reject the corresponding non-positive null in every dataset-by-rate cell.
Items 5--6 are additional hard point-estimate gates:

1. arbitrary words remove more than 5% of held-out dyadic error;
2. a positive trained-block-VQ opportunity exists;
3. arbitrary words close more than half of the dyadic-to-block-VQ gap;
4. the base-pair absolute-distance-error contrast is positive;
5. at least 48 of 64 groups have positive dyadic-error removal; and
6. every leave-one-group-out pooled removal estimate remains at least 5%.

The first four contrasts are frozen as a 16-hypothesis Holm family across the
four dataset-by-rate cells. Every primary arm pays identical fixed payload and
full expanded lookup capacity.

The maximum positive outcome is only:

```text
GO_TO_SYSTEMS_PREREG
```

That would establish a data-level word-local opportunity and permit writing a
later systems protocol. It would still not establish Recall, QPS, or a method
claim. At this snapshot, reading the registered base inputs is forbidden.

---

## 64. A4-1S Synthetic Implementation And Cost Gate

Status: `FROZEN_AUTHORIZED_NOT_IMPLEMENTED`

A4-1S exists only to establish that the exact registered machinery is correct,
deterministic, representation-complete, and affordable before any base read:

```text
256-case exact scalar reference suite
2,433,600 allocation decisions, all executed in canonical order and digested
explicit mixed-radix, B4/B8 packing, and LUT fixtures
64-case deterministic trained-block-VQ control suite
one full-shape 8192 x 128 synthetic cost projection
```

The projection must use the same compiled exact-arithmetic implementation,
all `K=1,...,256` scalar curves, both product allocators, 64 groups, both rates,
and all eight block starts. The projected two-dataset cost is `2.5` times the
one-panel CPU time and must not exceed 24 CPU-hours.

Status precedence prevents a broken instrument from becoming scientific
evidence:

| Condition | Outcome |
|---|---|
| artifact/schema or implementation parity defect | `ARTIFACT_INVALID` or `IMPLEMENTATION_INVALID` |
| trained block-control defect | `CONTROL_INVALID` |
| selected scalar alphabet collapses at binary32 | `NO_GO_REPRESENTATION` |
| frozen exact-solver cost ceiling is exceeded | `NO_GO_EXACT_SOLVER_COST` |
| every correctness, representation, control, and cost gate passes | `PASS_SYNTHETIC_GATE_ONLY` |

`PASS_SYNTHETIC_GATE_ONLY` permits only asking the user whether to authorize
the already-registered base gate. It does not authorize that read itself.

Snapshot at `3c0a49f`: no committed runner, parity evidence, cost projection,
or A4-1 result exists. Untracked worktree files are deliberately excluded.

---

## 65. Current Synthesis

| Attempt | Theoretical guarantee | Strongest positive evidence | Decision / current boundary |
|---|---|---|---|
| 1A full-D PCA replacement | L2 isometry for any orthogonal transform | GIST residual-PCA accurate/full RMSE `-0.60%/-0.33%` | no stable ranking gain; fast harm; CIFAR replication failure |
| 1B lossy `D -> d` | exact head and norm terms in favorable oracle | tail norms reduce RMSE from 0.0445 to 0.00248 | omitted tail IP still worsens ranking versus native SAQ |
| 2 exact scalar DP | exact bin-boundary partition SSE using raw bin moments; final midpoint-nearest-centroid raw SSE is evaluated, not reoptimized; outer optimum is conditional on `E[j,b]` | audio B=4 raw MSE `-15.5%`, R@100 `+0.004` | inner-DP novelty is foreclosed by prior art; no full-scale raw optimum or recall guarantee; cross-regime reversals |
| 3 distance-quality re-evaluation | paper-exact metric semantics; no method guarantee | GIST measured point: higher `1/Ratio`, `1.078x` QPS at the frozen target | one positive setting; DEEP controls remain negative; metric is prior work |
| 4 arbitrary-cardinality fixed-rate words | the arbitrary positive-integer feasible set contains the dyadic set for exact factorized SSE | frozen `(3,5)` witness: gap `0.1`, exact address/LUT parity | A4-0 instrument only; primitives are prior art; natural-data prevalence, block-VQ competitiveness, and ANN/system value remain unestablished |

Cross-attempt lesson:

```text
Optimizing a mathematically valid surrogate is not enough, and changing the
evaluation metric is not itself a mechanism.

The missing contribution must connect its optimized quantity to top-k or
downstream quality and system work, survive a second baseline or regime, and
include all construction, storage, and query overhead.

Attempt 4 is deliberately staged so that a representation theorem or a
synthetic witness cannot silently become a method claim. Each expansion of
scope requires a committed result, independent review, and separate
authorization.
```

---

## 66. Proposed Meeting Discussion

Decision 1:

```text
Do the Attempt 1 results justify treating PCA replacement as a closed practical
direction, while avoiding a universal PCA-optimality claim?
```

Decision 2:

```text
Should exact-hist DP remain only a stronger offline baseline, given that
Wu 1991 / GLM 2017 foreclose the inner algorithmic novelty and White-Singal
2026 explicitly recognizes that baseline, while the local evidence does not
establish retrieval or system dominance?
```

Decision 3:

```text
Should future ANN evidence always report both identifier Recall and geometric
distance quality, while treating the GIST flip only as measurement evidence?
```

Decision 4:

```text
Do we agree that Attempt 4 is only a conditional offline falsification study,
and that no base read should occur until a committed, independently reviewed
A4-1S outcome is presented?
```

Future decision, only after `PASS_SYNTHETIC_GATE_ONLY`:

```text
Should the already-registered A4-1 base-only gate be authorized? Even an A4-1
pass would warrant only systems preregistration, not SAQ integration or a
method claim.
```

Speaker notes:

- The immediate Attempt 4 objective is synthetic falsification of correctness,
  representation, control, and exact-solver cost.
- Novelty, mechanism, replication, and total overhead should be challenged
  before experimental scope is expanded.

---

## 67. Evidence And Code Map

Attempt 1, SAQ branch `saq-transform-analysis@3d94840`:

```text
docs/saq_transform_phase1_limitation_evidence_2026_07_10.md
docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md
docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md
script/prepare_phase1_transform_views.py
src/phase1_transform_diagnostic.cpp
src/lp0_projection_gate_a.cpp
script/evaluate_phase1b_gate.py
script/evaluate_lp0_gate_a.py
```

Lossy projection evidence is preserved on
`saq-lossy-projection-analysis@051ec6a`.

Attempt 2, sibling `vectordb@f51b487`:

```text
src/scalar_quantizer.cpp
src/dimensionwise_quantizer.cpp
src/bit_allocator.cpp
src/eval_dimensionwise_quantizer.cpp
docs/dimensionwise_quantizer_smoke_run_2026_06_26.md
reports/scalar_training_exact_hist_audit_2026_06_30/README.md
reports/scalar_training_exact_hist_audit_2026_06_30/comparison.csv
reports/scalar_training_exact_hist_audit_2026_06_30/logs/
  deep1M_pca_B4_variable_exact-hist_rank-boundary.stdout
reports/pca_rank_boundary_deep1M_2026_06_27/logs/
  deep1M_pca_B4_variable_lloyd_rank-boundary.stdout
```

Attempt 2 external primary sources:

- [White and Singal, Inner Product Aware Quantization,
  arXiv:2606.00289v1](https://arxiv.org/html/2606.00289v1)
- [Pinned official code at
  `e92ed90`](https://github.com/nathanllww/Inner-Product-Aware-Quantization/tree/e92ed904b85ad12469a0a350c81071ff9ef6aa37)
- [Grønlund et al., Fast Exact k-Means, k-Medians and Bregman Divergence
  Clustering in 1D](https://arxiv.org/abs/1701.07204)
- [Wu, Optimal Quantization by Matrix Searching, Journal of Algorithms,
  1991](https://www.sciencedirect.com/science/article/pii/0196677491900392)
- [Li et al., SAQ: Pushing the Limits of Vector Quantization through Code
  Adjustment and Dimension Segmentation,
  arXiv:2509.12086](https://arxiv.org/abs/2509.12086), direct ANN prior for DP
  segmentation and bit allocation under a space quota

Attempt 3, branch `saq-ratio-metric-analysis@146dc16`:

```text
docs/saq_attempt3_ratio_metric_related_work_and_gate_2026_07_13.md
docs/saq_attempt3_ratio_metric_protocol_2026_07_13.md
docs/saq_attempt3_a3_0_a3_1_gist_evidence_2026_07_13.md
docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md
docs/saq_attempt3_a3_1b_artifacts_2026_07_13/
docs/saq_attempt3_a3_2_artifacts_2026_07_13/
script/evaluate_inverse_ratio.py
script/summarize_ratio_frontier.py
src/test_qps.cpp
```

Attempt 4, branch `saq-arbitrary-cardinality-analysis@3c0a49f`:

```text
docs/saq_attempt4_arbitrary_cardinality_related_work_and_gate_2026_07_13.md
docs/saq_attempt4_arbitrary_cardinality_sources_2026_07_13.json
docs/saq_attempt4_a4_0_offline_protocol_2026_07_13.md
docs/saq_attempt4_a4_0_synthetic_evidence_2026_07_13.md
docs/saq_attempt4_a4_0_artifacts_2026_07_13/synthetic_witness.json
docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md
docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json
docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json
docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md
```

Only A4-0 is outcome evidence. The A4-1 and A4-1S files are frozen protocols
and contracts; they do not establish implementation or scientific results.

Current deck:

```text
docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md
```

---

## 68. One-Slide Takeaway

```text
Attempt 1:
PCA replacement found a small GIST estimator signal that failed CIFAR
replication. The favorable lossy D->d oracle still ranked worse than native
SAQ because a norm-only tail cannot recover tail inner products.

Attempt 2:
The paper and pinned public code do not present an integrated shared-codebook,
heterogeneous-rate, outer-allocation pipeline; that absence does not establish
novelty. Exact 1D scalar DP is old prior art. Separately, the pinned code
exposes a full-raw-data exact solver primitive and an adjacent shared-block
helper, neither with a public integrated experiment path. Local raw-SSE gains
are real, but Recall can improve or regress. Keep this as offline baseline and
objective-mismatch evidence, not a method.

Attempt 3:
Paper-exact 1/Ratio changes one GIST matched-quality conclusion: a measured
fac-error point gives higher geometric quality and 1.078x QPS. DEEP B=4/B=5
remain negative, 39.6% of paired GIST queries worsen, and the metric is prior
work. The result is measurement evidence, not a method.

Attempt 4:
Fixed-rate arbitrary cardinalities strictly beat the dyadic scalar-product
restriction on the frozen (3,5) witness, but unrestricted block VQ matches
them and the primitives are known. A4-0 validates only the instrument. A4-1S
is authorized with no committed outcome; natural-data access and SAQ/system
claims remain forbidden.

Project decision:
Keep Attempts 1--3 as rigorous negative or partial evidence. Do not rescue
them with post-hoc sweeps. Continue Attempt 4 only through its preregistered
gates, with no provisional-result promotion or post-hoc rescue.
```

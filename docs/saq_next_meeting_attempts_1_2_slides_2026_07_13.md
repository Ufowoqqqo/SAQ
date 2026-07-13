# Post-SAQ Pivot: Attempts 1 And 2

PCA Replacement, Lossy Projection, And Exact Scalar-Codebook DP

Date: 2026-07-13

Audience assumption: familiar with vector search and vector quantization at a
high level, but not with SAQ's transform, segmentation, or the experiments in
these repositories.

Deck status: Attempts 1 and 2 are complete historical studies. Attempts 3 and
4 are intentionally reserved for later problem-first directions and contain no
experimental claims yet.

---

## 1. Meeting Goal

This is not a presentation of a finished method.

The goal is to explain two research attempts in enough detail to decide what
they teach us and what they rule out:

```text
Attempt 1: Is PCA a practical limitation of SAQ?
           1A. Replace full-D raw-data PCA with another isometric transform.
           1B. Physically project D -> d and summarize the omitted tail.

Attempt 2: Does exact scalar-codebook optimization improve the quantization
           and retrieval result beyond Lloyd training?

Attempt 3: reserved; not selected yet
Attempt 4: reserved; not selected yet
```

Main message:

```text
Both completed attempts found useful local evidence, but neither established a
new method. The stopping decisions were made at predeclared evidence gates,
before spending more implementation effort on a weak premise.
```

Speaker notes:

- The purpose is research selection, not presenting every experiment as a win.
- Attempt 1 belongs to the SAQ repository.
- Attempt 2 comes from the sibling `vectordb` repository and tests a more
  classical scalar-quantization premise.

---

## 2. Current Research Position

Project-level decision before this deck:

```text
SAQ-centric incremental method search: STOP
SAQ as a strong baseline:              RETAIN
next directions:                       problem-first review before coding
```

Why still present these attempts:

1. They test two intuitive claims that may arise in a meeting.
2. They distinguish optimization guarantees from retrieval guarantees.
3. They provide quantitative stop evidence instead of relying on intuition.
4. They define what Attempt 3 and Attempt 4 must do differently.

Unsafe interpretation:

```text
PCA is universally optimal, or exact DP never helps ANN.
```

Safe interpretation:

```text
The specific PCA-replacement, lossy-projection, and histogram-DP mechanisms
tested here do not supply a sufficiently general, overhead-controlled method.
```

---

## 3. Attempt Map And Evidence Status

| Attempt | Core question | Main regimes | Decision |
|---|---|---|---|
| 1A. Full-D transform replacement | Does residual PCA or another isometric basis improve SAQ estimator behavior over raw-data PCA? | GIST sample50k, then preregistered CIFAR60K replication | Closed after replication failure |
| 1B. Lossy `D -> d` projection | Can a PCA head plus a compact tail surrogate beat native full-D SAQ? | GIST sample50k, `960 -> 576`, favorable exact surrogate | Gate A failed; projected SAQ not built |
| 2. Exact scalar-codebook DP | Does exact 1D histogram DP improve dimensionwise scalar quantization over Lloyd? | audio, PCA CIFAR60K, PCA DEEP1M | Stronger offline baseline; no stable recall dominance |
| 3. Reserved | To be chosen through a problem-first novelty/complexity review | Not run | No claim |
| 4. Reserved | To be chosen after Attempt 3 evidence | Not run | No claim |

Speaker notes:

- Attempt 1A and 1B are related but not equivalent.
- A full-D orthogonal transform preserves exact L2 geometry.
- A physical `D -> d` projection changes the exact distance unless the omitted
  interaction is somehow reconstructed.

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
| `N` | number of base vectors | GIST 50,000; CIFAR 60,000; DEEP 1,000,000 |
| `D` | original dimension | GIST 960; CIFAR 512; DEEP 256; audio 192 |
| `d` | physically retained dimension after lossy projection | GIST 576 |
| `K_IVF` | number of IVF clusters | 512 in Attempt 1 |
| `B` | nominal average bits/dimension | 4 in Attempt 1; 2/4/8 in Attempt 2 |
| `Q` | number of held-out evaluation queries | 128 or 1,000 in Attempt 1 |
| `H` | equal-count histogram bins for scalar DP | default 256 |
| `K_b` | scalar centroids at bitwidth `b` | up to `2^b` |
| `w_j` | allocation weight for dimension `j` | 1 or historical rank-boundary weight |
| `R` | full-D orthogonal transform matrix | transform-dependent |

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

Question:

```text
If each coordinate uses a scalar codebook, can exact 1D dynamic programming
produce a better codebook than Lloyd refinement, and does the lower training
objective improve ANN recall?
```

This is relevant because scalar codebook quality is an intuitive lower-level
quantization improvement. However:

```text
scalar quantization itself is established prior work
the exact objective is reconstruction SSE, not recall
the tested implementation is exact over histogram bins, not raw samples
```

Speaker notes:

- Attempt 2 is not SAQ's segment-planner DP.
- It is also not the CAQ exact direction-code oracle from the later branch.

---

## 27. Two Different Dynamic Programs

The `vectordb` pipeline contains two DPs.

### Inner DP: scalar codebook training

For one dimension `j` and bitwidth `b`:

```text
input:  sorted scalar values or weighted histogram bins
output: K_b centroids minimizing 1D reconstruction SSE
```

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
budget. Attempt 2 focuses on whether replacing Lloyd with the inner exact-hist
DP improves the final pipeline.

---

## 28. Dimensionwise Scalar-Quantization Setting

Database vector:

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
Given the H weighted bins and K_b centroids, the DP returns the minimum SSE
among contiguous partitions of those bins.
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

---

## 31. Attempt 2 Code Map

Sibling repository code:

```text
src/scalar_quantizer.cpp
  BuildEqualCountHistogram(...)
  HistogramIntervalSse(...)
  ComputeExactKMeansLayer(...)
  TrainExactScalarQuantizerFromSorted(...)

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

## 32. Attempt 2 Complexity

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
memory O(D * D B), or less with rolling layers
```

Full-sample `H=N` exact training would replace the small histogram term with
approximately `O(K_b N log N)` per dimension/bitwidth. It was judged too
expensive for full DEEP1M and was not evaluated.

---

## 33. Exact-Hist Running Example

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

## 34. Audio Result: Lloyd Versus Exact-Hist

Dataset:

```text
audio base = 53,387 x 192
audio query = 200 x 192
metric = L2
mode = variable
B = 4
H = 256
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

## 35. Audio Histogram-Bin Sweep

`B=4`, variable allocation:

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

---

## 36. PCA CIFAR/DEEP Comparison

All rows use `H=256` and variable bit allocation. SSE ratio is
`exact-hist / Lloyd`; recall delta is `exact-hist - Lloyd`.

| Dataset | B | Allocation objective | SSE ratio | R@100 delta |
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
2. DEEP `B=4` rank-boundary shows that a much lower training objective still
   does not guarantee higher recall.

---

## 37. Why Lower Reconstruction SSE Need Not Improve Recall

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

## 38. Ranking Running Example

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

This is why an SSE-optimal codebook can have lower recall than a Lloyd local
optimum: ranking depends on differential error across close candidates.

---

## 39. Bit-Allocation Coupling

Changing the scalar trainer changes the full error table:

```math
E[j,b]=\text{training error for dimension j at bitwidth b}.
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

Historical disclosure:

```text
rank-boundary weights use query/ground-truth-derived pairs.
They are evidence about objective behavior, not an admissible method under the
current query-unaware project constraint.
```

---

## 40. Attempt 2 Decision

```text
Decision: KEEP EXACT-HIST AS A STRONG OFFLINE BASELINE, NOT A MAIN METHOD
```

What the experiment establishes:

1. Exact histogram DP is implemented and can materially lower its training
   objective.
2. It sometimes improves recall, especially at lower bit budgets.
3. Historical rank-boundary gains over reconstruction survive both Lloyd and
   exact-hist, so they are not only a Lloyd artifact.

Why it is not a method contribution:

1. It is exact only over a chosen histogram discretization.
2. Full-sample exact DP was not evaluated at full scale.
3. Lower SSE does not provide a recall guarantee.
4. Recall gains are non-monotonic across `H`, datasets, budgets, and allocation
   objectives.
5. Optimal 1D scalar quantization is established related work.
6. The historical rank-boundary outer objective is query-aware.

Strict-reviewer summary:

```text
This is a useful baseline and objective-mismatch result, not a new ANN
quantizer or a database-systems contribution.
```

---

## 41. Attempt 3: Reserved

```text
Status: NOT SELECTED
Evidence: NONE
Claims: NONE
```

Attempt 3 will be added only after a problem-first review records:

```text
database problem and workload
closest primary related work
what those methods already solve
remaining mechanism-level gap
at least two independent strong baselines
query-unaware information available at build time
time, build, storage, and query complexity
smallest falsification experiment
strict-reviewer objection
GO / NO-GO decision
```

No method name or expected positive result should be inserted before this
review passes.

---

## 42. Attempt 4: Reserved

```text
Status: NOT SELECTED
Evidence: NONE
Claims: NONE
```

Attempt 4 should not be chosen merely as a fallback if Attempt 3 fails. It must
independently pass the same novelty and complexity gate.

Required distinction from Attempts 1 and 2:

```text
not another transform substitution without a replicated limitation
not another surrogate-objective optimizer without a ranking mechanism
not a parameter sweep around SAQ
not a high-overhead method justified by a small recall change
```

---

## 43. Current Synthesis

| Attempt | Theoretical guarantee | Strongest positive evidence | Why it stops |
|---|---|---|---|
| 1A full-D PCA replacement | L2 isometry for any orthogonal transform | GIST residual-PCA accurate/full RMSE `-0.60%/-0.33%` | no stable ranking gain; fast harm; CIFAR replication failure |
| 1B lossy `D -> d` | exact head and norm terms in favorable oracle | tail norms reduce RMSE from 0.0445 to 0.00248 | omitted tail IP still worsens ranking versus native SAQ |
| 2 exact scalar DP | exact minimum SSE over `H` weighted bins | audio B=4 MSE `-15.5%`, R@100 `+0.004` | no raw/full-scale or recall guarantee; cross-regime reversals |
| 3 | not defined | none | pending selection review |
| 4 | not defined | none | pending selection review |

Cross-attempt lesson:

```text
Optimizing a mathematically valid surrogate is not enough.

The missing contribution must connect its optimized quantity to top-k ranking
or system work, survive a second regime, and include all overhead.
```

---

## 44. Proposed Meeting Discussion

Decision 1:

```text
Do the Attempt 1 results justify treating PCA as a closed practical direction,
while explicitly avoiding a universal optimality claim?
```

Decision 2:

```text
Should exact-hist DP remain only a baseline, given that its guarantee is SSE
over histogram bins and not recall?
```

Decision 3:

```text
For Attempt 3, should we require a theorem/inequality connecting the method
objective to ranking, or is a mechanism-derived systems model sufficient?
```

Decision 4:

```text
What broader vector-search problem should be reviewed before naming Attempt 3
and Attempt 4?
```

Speaker notes:

- The immediate meeting objective is selecting a research problem, not
  selecting another implementation task.
- The advisor should challenge novelty and overhead before experimental scope.

---

## 45. Evidence And Code Map

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
```

Current deck:

```text
docs/saq_next_meeting_attempts_1_2_slides_2026_07_13.md
```

---

## 46. One-Slide Takeaway

```text
Attempt 1:
PCA replacement found a small GIST estimator signal that failed CIFAR
replication. The more favorable lossy D->d oracle also ranked worse than native
SAQ because a norm-only tail cannot recover tail inner products.

Attempt 2:
Exact histogram DP can lower scalar reconstruction SSE, but histogram
discretization and objective mismatch mean recall can improve or regress.

Project decision:
Keep both as rigorous negative/partial evidence. Do not turn either into a
method by adding post-hoc sweeps. Select Attempts 3 and 4 through a new
problem-first related-work and complexity gate.
```

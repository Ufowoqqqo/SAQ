# Post-SAQ Pivot: Attempts 1, 2, 3, And 4

PCA Replacement, Lossy Projection, Exact Scalar-Codebook DP,
Recent ASQ Prior-Art Audit, Distance-Quality Re-evaluation,
And An Arbitrary-Cardinality Fixed-Rate Quantization Gate

Date: 2026-07-13

Presentation status: **CURRENT DRAFT -- not yet presented at a meeting.**

Latest revision: 2026-07-17. Incorporates the 2026-07-13 audit of
[White and Singal, arXiv:2606.00289v1](https://arxiv.org/abs/2606.00289)
and its pinned official code, the terminal A4-1S snapshot
`saq-arbitrary-cardinality-analysis@f1b464b`, and the corrected A4 V2 source
plus terminal PAR snapshot `saq-arbitrary-cardinality-feasibility-v2@30dfada`,
independently reviewed at `fd5367e`, and the later exact executable-identity
source repair `@e48df452`, independently reviewed at `c401dae`, the
cache/staging disposition target `@56210f8` and review record `@249d5b8`, and
the generic cache-policy source/static target `@c33a2bf`, independently
reviewed at `@5db3025`, and the exact PREP authorization target `@e7f940e`,
independently reviewed at `@16a8201`, followed by the host-rebind erratum
target `@5a47fed`, independently reviewed at `@b89dabe`, and the exact
HOST-I-AUTH target `@212a67b`, independently reviewed at `@71e6bec`, followed
by the source-authority erratum target `@6fe8544`, independently reviewed at
`@9fa9528`, and the subsequent HOST-I source-static target `@4602585`, whose
direct-child independent review at `@e8e9c79` recorded one HIGH and a
terminal source-static target review failure, followed by the bounded
HOST-I-R1 correction-only repair protocol target `@ddfef99`, independently
reviewed at `@b1a7429` with
`HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS`, and the exact
correction target `@e17f887`, independently reviewed at `@e10bde7` with
`HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS`, followed by the bounded
source-history epoch-correction protocol target `@dcaed57`, independently
reviewed at `@e98a3e4` with
`SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS`.

Audience assumption: familiar with vector search and vector quantization at a
high level, but not with SAQ's transform, segmentation, or the experiments in
these repositories.

Deck status: Attempts 1, 2, and 3 are complete studies. Attempt 4 preserves
the terminal A4-1S `NO_GO_EXACT_SOLVER_COST`, while a new primary-source review
supports a narrower A4 V2 protocol for a differently defined synthetic
comparative-instrument cost question. Its additive PAR-report timing erratum
is `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS`. Source-only A4-V2-I reached
`SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`, but the later authorized PAR command
stopped before build at frozen status `ARTIFACT_INVALID`. This is an artifact-
validation failure with no valid PAR authority and no scientific decision.
A4-V2-I-R1 subsequently repaired only the CPython identity source and reached
`SOURCE_REPAIR_STATIC_REVIEW_PASS`; it did not run build or parity. The later
CACHE-P exact target reached only `EXACT_TARGET_INDEPENDENT_REVIEW_PASS`: its
protocol retains the old quarantine, requires staged sanitized remote
isolation, and rejects direct PAR-R1. CACHE-I then reached only
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` for 37 filesystem sources and
38 statically enumerated executable units. A separate `compile()`-only syntax
check accepted the exact locked Python snapshots without importing or
executing them. The later three-path PREP authorization target and direct-
child review reached only `PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.
Before PREP, static checking found that the frozen `.el9_8` Python leader had
been replaced by `.el9_8.2`; PREP was not invoked and START was not created.
The additive host-rebind erratum target/review reached only
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`: host identity is not rebound,
the old invocation authority is nontransferable, and the old probe is
superseded and must never be reused. The later HOST-I-AUTH target/review
reached only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`; no five-source or
seven-derived-object rebind occurred, host identity is still not rebound, and
no Python or PREP ran. Its later HOST-I instruction stopped before any source
target because the preserved seven-component authority closure could not
admit the required eighth component. The additive source-authority erratum
target/review reached only `HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`.
A subsequently authorized 14-path source-static target changed the five
registered sources and seven derived authority objects without executing
Python, build, PREP, or data access. Its exact direct-child review failed with
one HIGH because the binding and crosswalk cite a false SHA-256 for the
governing erratum review. The terminal status is
`SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH` and
the failed target itself remains immutable. The later correction-only
repair protocol target/review `ddfef99/@b1a7429` passed with zero LOW-or-higher
findings. Exact five-path R1 target/review `e17f887/@e10bde7` then passed with
zero LOW-or-higher findings after reproducing the four artifact substitutions,
unchanged source/authority closure, and all 13 registered host objects.
`HOST_IDENTITY_REBOUND` is established only for that registered 13-object
bundle; whole-host identity is unestablished. Source-history protocol
target/review `dcaed57/@e98a3e4` then passed with zero LOW-or-higher findings,
freezing a strict four-legacy/six-active epoch rule and rejecting adaptive or
either-epoch matching. It is protocol-only: `SOURCE_HISTORY_MISMATCH` remains
unresolved in source, and `A4-V2-SOURCE-HISTORY-I` is unauthorized.
Fresh PREP authority, actual PREP, CACHE-BIND, PAR-R1, SRUN, real-base reads,
and SAQ integration remain unauthorized.

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
contribution. Attempt 4's A4-1S formulation is a completed synthetic pipeline-
cost falsification study, not a natural-data, ANN, or systems result. A4 V2
preserves that stop and preregisters a new cost/evidence boundary. Its
reporting-closure erratum is reviewed protocol evidence, not a feasibility
result. Its corrected source and manifest passed independent static review,
but the one authorized PAR invocation rejected the `/bin/python` symlink
before any B/P worker. No build or parity fixture ran, so this adds no
quantization evidence. A later exact source repair passed static review only;
it has not been executed and does not change the terminal PAR result. CACHE-P
then froze a governance-only isolation protocol after reviewing cache semantics
and frozen source without opening the quarantine. It rejects direct PAR-R1.
CACHE-I later implemented and statically closed only that generic governance
layer; its review and syntax-only check add no parity, cost, or scientific
evidence. A later exact PREP authorization record passed independent review,
but that is authorization-document governance only and authorizes no clone,
preparation, or execution. The subsequent host-rebind protocol and HOST-I-AUTH
reviews likewise remain documentation governance: they rebind neither source
nor host and authorize no Python or PREP. The attempted HOST-I source edge was
stopped before edits on a seven-versus-eight contract contradiction; its
reviewed additive erratum repairs only that source-authority contract and
enabled a later source-static target. That target's direct-child review found
one HIGH authority-identity mismatch, so that target remains failed evidence.
A later correction-only target passed exact review and establishes rebound
only for the registered 13-object bundle. It ran no execution and does not
establish whole-host, PREP, cache-verifier/PAR, or scientific readiness. A
later reviewed source-history protocol specifies a fail-closed two-epoch
repair, but does not implement or authorize it.
```

Speaker notes:

- The purpose is research selection, not presenting every experiment as a win.
- Attempt 1 belongs to the SAQ repository.
- Attempt 2 comes from the sibling `vectordb` repository and tests a more
  classical scalar-quantization premise. The new related-work audit separates
  the local two-DP pipeline from the already-established inner optimizer.
- Attempt 3 returns to SAQ and asks whether Recall understated the geometric
  quality of any previously rejected result set.
- Attempt 4 is problem-first and fixed-rate. A4-1S passed implementation
  parity but failed its pipeline-cost gate. A4 V2 has a reviewed parent
  protocol and additive timing-closure erratum. Its PAR attempt failed only
  at executable-identity admission. I-R1 repairs that source path but remains
  unexecuted. CACHE-P selects staged sanitized remote isolation and rejects
  direct PAR-R1. CACHE-I closes its generic source/schema layer under static
  review only; none of these facts is quantization-quality, natural-data, ANN,
  or systems evidence. The later PREP authorization record also passed only
  documentation review. A subsequent static host mismatch prevented PREP and
  START; the reviewed host-rebind erratum is protocol governance only, and
  the old delayed probe is superseded and may never run or be reused. The
  later HOST-I-AUTH review freezes only the contract and projection for a
  possible future source target; it grants no HOST-I authority and performed
  no source/authority rebind, Python, or PREP. That attempted source target
  then stopped before edits on an exact seven-versus-eight component
  contradiction. The reviewed source-authority erratum admits the eighth
  component. The later 14-path HOST-I source-static target was created, but
  its exact review failed with one HIGH because two authority documents bind
  the wrong governing-review SHA-256. A later reviewed five-path R1 correction
  repaired only that provenance defect and passed independent review across
  all 13 registered host objects. This is bounded bundle identity, not whole-
  host or execution readiness. The later source-history protocol passed
  independent review and freezes a strict future one-source repair, but the
  mismatch remains open in source and implementation is not authorized.

---

## 2. Current Research Position

Project-level decision before this deck:

```text
SAQ-centric incremental method search: STOP
SAQ as a strong baseline:              RETAIN
Attempt 4 A4-1S formulation:           TERMINAL COST STOP
Attempt 4 A4 V2 PAR:                   ARTIFACT_INVALID; NO SCIENTIFIC DECISION
Attempt 4 A4 V2 I-R1:                  SOURCE_REPAIR_STATIC_REVIEW_PASS ONLY
Attempt 4 A4 V2 CACHE-P target:        EXACT_TARGET_INDEPENDENT_REVIEW_PASS
Attempt 4 A4 V2 CACHE-I:               GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
Attempt 4 A4 V2 PREP authorization:    PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
Attempt 4 A4 V2 HOST-P erratum:        HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS
Attempt 4 A4 V2 HOST-I-AUTH:           AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
Attempt 4 A4 V2 HOST-I-ERRATUM:        HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS
Attempt 4 A4 V2 host rebound:          ESTABLISHED FOR REGISTERED 13-OBJECT BUNDLE ONLY
Attempt 4 A4 V2 HOST-I:                SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
Attempt 4 A4 V2 HOST-I-R1-P:           HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS
Attempt 4 A4 V2 HOST-I-R1:             HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS
Attempt 4 A4 V2 SOURCE-HISTORY-P:      SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS
Attempt 4 A4 V2 SOURCE-HISTORY-I:      NOT AUTHORIZED
Attempt 4 A4 V2 PREP/BIND:             NOT AUTHORIZED
Attempt 4 A4 V2 cache/PAR readiness:   NOT ESTABLISHED; SOURCE_HISTORY_MISMATCH OPEN IN SOURCE
Attempt 4 A4 V2 direct PAR-R1:         NO-GO / NOT AUTHORIZED
SAQ/index/search integration:          NOT AUTHORIZED
```

Why still present these attempts:

1. Attempts 1--3 test three intuitive claims that may arise in a meeting.
2. They distinguish optimization guarantees from retrieval guarantees.
3. They provide quantitative stop evidence instead of relying on intuition.
4. Attempt 3 tests whether an evaluation choice, rather than a quantizer
   mechanism, caused one earlier negative conclusion.
5. Attempt 4 shows both a preregistered synthetic cost stop and how a later
   protocol must preserve that result while redefining its FOM and evidence
   boundary before any new authorization.

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
neither ANN improvement nor a systems advantage. A4 V2 only asks whether a
complete four-arm synthetic comparative instrument fits an internal cost cap;
the old `5/2` real-data projection does not transfer.
```

---

## 3. Attempt Map And Evidence Status

| Attempt | Core question | Main regimes | Decision / current status |
|---|---|---|---|
| 1A. Full-D transform replacement | Does residual PCA or another isometric basis improve SAQ estimator behavior over raw-data PCA? | GIST sample50k, then preregistered CIFAR60K replication | Closed after replication failure |
| 1B. Lossy `D -> d` projection | Can a PCA head plus a compact tail surrogate beat native full-D SAQ? | GIST sample50k, `960 -> 576`, favorable exact surrogate | Gate A failed; projected SAQ not built |
| 2. Exact scalar-codebook DP | Does histogram-exact 1D DP improve shared dimensionwise scalar quantization over Lloyd, and is any method novelty left after prior work? | audio, PCA CIFAR60K, PCA DEEP1M; arXiv/code audit | Stronger offline baseline; inner DP is prior art; no stable recall dominance |
| 3. Distance-quality re-evaluation | Does `1/Ratio@k` change a frozen Recall-based Pareto conclusion? | GIST sample100k B=4; DEEP sample100k B=4/B=5 controls | Closed as metric-sensitivity evidence |
| 4. Arbitrary-cardinality fixed-rate words | Does the power-of-two restriction waste material capacity at unchanged fixed payload and lookup granularity? | A4-0 synthetic witness; terminal A4-1S correctness/cost gate; reviewed A4 V2 protocol/source, terminal pre-build PAR identity failure, static-only I-R1 repair, CACHE-P/CACHE-I governance, PREP authorization, host-rebind governance, the failed HOST-I source-static target, its reviewed R1 correction, and a reviewed source-history epoch protocol; registered real-base gates remain unauthorized | preserve A4-1S `NO_GO_EXACT_SOLVER_COST` and A4-V2-PAR `ARTIFACT_INVALID / NO_SCIENTIFIC_DECISION`; R1 established rebound only for the registered 13-object bundle; source-history protocol `dcaed57/@e98a3e4` passed but source implementation remains unauthorized, so `SOURCE_HISTORY_MISMATCH` stays open in source and PREP/CACHE-BIND/PAR-R1 remain unauthorized |

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

## 59. Attempt 4: Research Question, Old Stop, And V2 Boundary

Current R12 reviewed snapshot:
`saq-arbitrary-cardinality-feasibility-v2@e98a3e4`

Source-history epoch-correction protocol target/direct-child review:
`saq-arbitrary-cardinality-feasibility-v2@dcaed57/@e98a3e4`

HOST-I-R1 correction target/direct-child review:
`saq-arbitrary-cardinality-feasibility-v2@e17f887/@e10bde7`

HOST-I-R1 correction-only repair protocol target/direct-child review:
`saq-arbitrary-cardinality-feasibility-v2@ddfef99/@b1a7429`

HOST-I source-static target/direct-child review:
`saq-arbitrary-cardinality-feasibility-v2@4602585/@e8e9c79`

Source-authority erratum target/review:
`saq-arbitrary-cardinality-feasibility-v2@6fe8544/@9fa9528`

Independent HOST-I-AUTH review record:
`saq-arbitrary-cardinality-feasibility-v2@71e6bec`

Preserved host-rebind erratum target/review:
`saq-arbitrary-cardinality-feasibility-v2@5a47fed/@b89dabe`

Preserved PREP-authorization target/review:
`saq-arbitrary-cardinality-feasibility-v2@e7f940e/@16a8201`

Preserved CACHE-I target/review:
`saq-arbitrary-cardinality-feasibility-v2@c33a2bf/@5db3025`

Preserved CACHE-P target/review:
`saq-arbitrary-cardinality-feasibility-v2@56210f8/@249d5b8`

Preserved source-repair/review snapshots:
`saq-arbitrary-cardinality-feasibility-v2@e48df452/@c401dae`

Preserved terminal PAR result/review:
`saq-arbitrary-cardinality-feasibility-v2@30dfada/@fd5367e`

Preserved terminal A4-1S snapshot:
`saq-arbitrary-cardinality-analysis@f1b464b`

| Stage | Committed status | What it means |
|---|---|---|
| A4-0 synthetic instrument | `PASS_INSTRUMENT_ONLY` | formulation, tiny witness, and reference checks passed |
| A4-1P base-only protocol | `FROZEN_NOT_AUTHORIZED / NOT_RUN` | scientific inputs and decision rule were registered; base read remained forbidden |
| A4-1S synthetic implementation | `NO_GO_EXACT_SOLVER_COST` | parity passed, but the reviewed frozen construction/evidence pipeline exceeded its cost ceiling |
| A4-V2 parent protocol | `PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION` | a new FOM and evidence boundary were independently reviewed at `f86a51d` |
| A4-V2-P-ERRATUM | `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS` | an additive finite PAR-report closure fixes terminal-P receipt recursion without changing the parent scientific contract |
| A4-V2-I | `SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS` | corrected exact source `482c401`, binding, and 35-file manifest passed three independent static-only reviews; failed parent `3a4f7c5` remains non-evidence |
| A4-V2-PAR | `ARTIFACT_INVALID / REVIEWED_TERMINAL` | the one authorized invocation rejected the `/bin/python` symlink before a B/P worker; no build, parity artifact, valid PAR authority, or scientific decision exists |
| A4-V2-I-R1 | `SOURCE_REPAIR_STATIC_REVIEW_PASS` | exact source `e48df452` binds leader identity to stable `/proc/self/exe` bytes and same-inode `sys.executable`; three-track review passed, but no code was imported, built, or executed |
| A4-V2-CACHE-P target | `EXACT_TARGET_INDEPENDENT_REVIEW_PASS` | exact target `56210f8` and review `249d5b8` freeze `GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED / NO_GO_DIRECT_PAR_R1`; governance only, with quarantine unread and 35-source tree unchanged |
| A4-V2-CACHE-I | `GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` | target `c33a2bf` and review `5db3025` bind 37 filesystem sources, 38 executable units, and source-tree SHA-256 `95680075...`; static artifact governance only, with no PREP or parity evidence |
| A4-V2-CACHE-PREP-AUTH | `PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS` | exact three-path target `e7f940e` and direct-child review `16a8201` bound a dormant PREP contract; the later host mismatch made its invocation authority nontransferable and its unique probe superseded |
| A4-V2-PREP-HOST-P | `HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS` | target/review `5a47fed/@b89dabe` bind the current `.el9_8.2` leader and complete future rebind closure; host identity is not rebound and no Python, PREP, probe, clone, token, build, data, or scientific action ran |
| A4-V2-PREP-HOST-I-AUTH | `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS` | exact target/review `212a67b/@71e6bec` freeze only the contract and projection for a possible later source target and grant no HOST-I authority; no five-source/seven-derived-object rebind, Python, build, PREP, data, or scientific action occurred |
| attempted A4-V2-PREP-HOST-I | `STOPPED_BEFORE_TARGET` | exact checking exposed an unsatisfiable seven-versus-eight protocol-component closure before any source edit, Python, or PREP |
| A4-V2-PREP-HOST-I-ERRATUM | `HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS` | target/review `6fe8544/@9fa9528` admit the eighth component and freeze its exact accounting/projection only; no implementation-source/derived-authority rebind or execution occurred |
| A4-V2-PREP-HOST-I | `SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH` | target `4602585` changed exactly the registered 14 paths without execution; direct-child review `e8e9c79` found one HIGH because the binding and crosswalk cite a false governing-review SHA-256; that target remains immutable failed evidence and is not retroactively passed by R1 |
| A4-V2-PREP-HOST-I-R1-P | `HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS` | target/review `ddfef99/@b1a7429` freeze only a future exact five-path correction target, corrected identities, cascade boundary, and direct-child review projection; zero LOW-or-higher findings, no repair authority, and no execution |
| A4-V2-PREP-HOST-I-R1 | `HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS` | target/review `e17f887/@e10bde7` changed only the exact five paths, reproduced all frozen identities and 13/13 registered host objects with zero LOW-or-higher findings, and establishes `HOST_IDENTITY_REBOUND` only for that registered bundle; whole-host identity remains unestablished and no execution ran |
| A4-V2-SOURCE-HISTORY-P | `SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS` | target/review `dcaed57/@e98a3e4` independently reproduced the exact five legacy blobs, other 32 preserved sources, and strict four-legacy/six-active role partition; it rejects either-epoch/adaptive matching and authorizes no source edit or execution |
| A4-V2-SOURCE-HISTORY-I | `NOT_AUTHORIZED` | the protocol freezes a possible one-source/ten-path static repair plus sole ninth component, but `SOURCE_HISTORY_MISMATCH` remains open in source and cache-verifier/PAR readiness is not established |
| actual PREP / receipt review / CACHE-BIND | `NOT_AUTHORIZED` | one preparation attempt, its committed independent receipt review, and binding remain separate non-transitive stages |
| A4-V2-PAR-R1 | `NOT_AUTHORIZED` | direct PAR-R1 is no-go; it can be considered only after every separately authorized isolation stage passes and the user explicitly authorizes PAR-R1 |
| A4-V2-SRUN | `NOT_AUTHORIZED` | the synthetic event remains a separate, non-transitive future stage and cannot start from invalid PAR authority |
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
SAQ, and it produced no natural-data, Recall, QPS, or systems claim.

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

Current boundary:

```text
PRESERVE A4-1S TERMINAL COST STOP
A4 V2 CORRECTED PROTOCOL AUTHORITY REVIEWED
A4-V2-I SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS
A4-V2-PAR ARTIFACT_INVALID / REVIEWED TERMINAL / NO VALID PAR AUTHORITY
A4-V2-I-R1 SOURCE_REPAIR_STATIC_REVIEW_PASS ONLY
A4-V2-CACHE-P TARGET EXACTLY REVIEWED / NO DIRECT PAR-R1
A4-V2-CACHE-I GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS ONLY
A4-V2-CACHE-PREP-AUTH PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS ONLY
A4-V2-PREP-HOST-P HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS ONLY
A4-V2-PREP-HOST-I-AUTH AUTHORIZATION_EXACT_TARGET_REVIEW_PASS ONLY
A4-V2-PREP-HOST-I ATTEMPT STOPPED BEFORE TARGET ON 7-VS-8 CONTRADICTION
A4-V2-PREP-HOST-I-ERRATUM HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS ONLY
A4-V2-PREP-HOST-I SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH
A4-V2-PREP-HOST-I-R1-P HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS ONLY
A4-V2-PREP-HOST-I-R1 HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS
HOST_IDENTITY_REBOUND ESTABLISHED FOR REGISTERED 13-OBJECT BUNDLE ONLY
WHOLE-HOST IDENTITY NOT ESTABLISHED
A4-V2-SOURCE-HISTORY-P SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS
A4-V2-SOURCE-HISTORY-I NOT AUTHORIZED
SOURCE_HISTORY_MISMATCH OPEN IN SOURCE / CACHE-VERIFIER AND PAR READINESS NOT ESTABLISHED
ACTUAL PREP AND CACHE-BIND NOT AUTHORIZED
A4-V2-PAR-R1 NOT AUTHORIZED
A4-V2-SRUN, DATA, AND SAQ CHANGES NOT AUTHORIZED
```

The fixed-word opportunity remains a mathematical possibility, but the frozen
exact A4-1S construction/evidence pipeline did not meet its preregistered cost
ceiling. V2 does not rescue or reinterpret that result. It freezes a new
synthetic comparative-instrument question and cannot claim a new quantization
primitive, feasibility, or SAQ integration. The erratum repairs protocol
closure only. The later PAR attempt reached module import but failed at the
leader executable's no-follow identity read, before build or parity. It adds
only artifact-validation failure evidence, not evidence about the candidate.
I-R1 then repaired that dedicated identity acquisition and passed exact-
commit static review, but no corrected conductor was executed. It therefore
adds source-correctness evidence only and does not supersede the PAR terminal
status. CACHE-P later reviewed CPython cache semantics and exact committed
source, retained the unread quarantine, and froze a staged sanitized remote-
isolation authority DAG. Its exact-target review found no LOW+ issue, but its
claim ceiling is artifact governance only. It changes no implementation or
environment, creates no clone, and rejects direct PAR-R1.

CACHE-I then added only the frozen generic cache-policy source/schema layer.
Exact target `c33a2bf` and direct-child review `5db3025` close 37 filesystem
sources plus one separate inline bootstrap, four schema/maximal-instance
pairs, and a 38-unit static import/process/mutation inventory. A separately
authorized Python 3.9 `compile()`-only check accepted the exact locked source
snapshots without importing or executing them. The maximum claim is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`, not PREP readiness, parity,
feasibility, an SAQ limitation, systems performance, novelty, or a method.

The subsequent exact three-path PREP authorization target `e7f940e` and
direct-child review `16a8201` reached
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS` with 0 LOW+ findings. This
froze only a dormant execution contract. Before invocation, static checking
found that a root RPM update had replaced the frozen `.el9_8` Python leader
with `.el9_8.2`; PREP was not invoked, START was not created, and no runtime
terminal status exists. Host-rebind erratum target/review
`5a47fed/@b89dabe` then reached only
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`. It does not rebind source or
establish PREP readiness. The old invocation authority is unspent but
nontransferable; its probe is unspent but superseded and must never run or be
reused. The later exact HOST-I-AUTH target/review `212a67b/@71e6bec` reached
only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. It froze a possible future
fourteen-path source edge but changed none of the five sources or seven
derived authority objects. When HOST-I was later instructed, exact projection
checking found that the frozen seven-component authority closure could not
admit the required eighth host-rebind component, so work stopped before any
source target. Additive source-authority erratum target/review
`6fe8544/@9fa9528` reached only
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`: it admits that eighth component
and freezes exact future byte/accounting semantics, but still changes no
implementation source or derived authority object. The subsequently
authorized HOST-I produced exact source-static target `4602585`. Its
direct-child review
`e8e9c79` found one HIGH: the binding and crosswalk contain a false digest for
the governing erratum review. Therefore the status is
`SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH`,
and Python/PREP remain `NOT_AUTHORIZED_NOT_RUN`. Correction-only protocol target/review
`ddfef99/@b1a7429` later reached
`HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS`. Exact R1 target/review
`e17f887/@e10bde7` then reached
`HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS` and established rebound only
for the registered 13-object bundle; whole-host identity remains unestablished.
Source-history protocol target/review `dcaed57/@e98a3e4` subsequently reached
`SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS`, freezing an exact
role-preassigned two-epoch rule without implementing it. Therefore
`SOURCE_HISTORY_MISMATCH` remains open in source and readiness claims remain
forbidden.

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

Status: `FROZEN_NOT_AUTHORIZED / NOT_RUN / FORECLOSED_BY_A4-1S`

Retained only for protocol provenance, A4-1 would have used query-unaware GIST
sample50k and CIFAR60K residual panels at fixed 4-bit and 8-bit two-factor
words. Its registered primary arms were:

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

The registered maximum positive outcome would have been only:

```text
GO_TO_SYSTEMS_PREREG
```

That would have established a data-level word-local opportunity and permitted
writing a later systems protocol. It still would not have established Recall,
QPS, or a method claim. A4-1S did not pass, so reading the registered base
inputs remains forbidden and this gate must not be opened.

A4 V2 does not reopen A4-1. Its source-only implementation and independent
static review completed, and the user separately authorized frozen PAR. That
one invocation stopped at `ARTIFACT_INVALID` before any B/P worker, build, or
parity fixture, so it created no valid PAR authority and no scientific
decision. The later clean I-R1 source correction and independent static review
are now complete. CACHE-P subsequently reviewed the cache/staging question at
exact target `56210f8`, with its independent review recorded at `249d5b8`.
It requires sanitized remote isolation and rejects direct PAR-R1, but changes
no implementation or environment and leaves the quarantine unread and
uncleaned. CACHE-I subsequently reached
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` at target/review
`c33a2bf/@5db3025`; it adds only static governance sources and schemas. The
later PREP authorization target/review `e7f940e/@16a8201` reached only
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. Static checking then found the
`.el9_8 -> .el9_8.2` leader replacement before PREP or START. Host-rebind
erratum target/review `5a47fed/@b89dabe` reached only
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`; the old probe is superseded and
must never be reused. HOST-I-AUTH target/review `212a67b/@71e6bec` then
reached only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`: no source/authority
rebind, Python, START, or PREP occurred. A later HOST-I instruction stopped
before any source target on the exact seven-versus-eight component
contradiction. Source-authority erratum target/review `6fe8544/@9fa9528`
reached only `HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`; it changes no
implementation source or derived authority object and grants no HOST-I
authority. The later source-static target/review `4602585/@e8e9c79` ended at
`SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH`: one HIGH false
governing-review digest in the binding and crosswalk, with host rebound not
established. Correction-only protocol target/review `ddfef99/@b1a7429`
subsequently passed with zero LOW-or-higher findings. Exact R1 target/review
`e17f887/@e10bde7` then corrected only that authority identity and passed
independent review across all 13 registered host objects. Bundle rebound is
established; whole-host identity and execution readiness are not. The unresolved future
`SOURCE_HISTORY_MISMATCH` independently keeps cache-verifier/PAR readiness
unestablished. Source-history protocol target/review `dcaed57/@e98a3e4`
passed and freezes a strict future two-epoch repair, but it made no source
change and grants no implementation authority.
Fresh PREP authority, actual PREP, receipt review, CACHE-BIND, PAR-R1, SRUN,
base, and query reads all remain unauthorized.

---

## 64. A4-1S Synthetic Implementation And Cost Gate

Status: `NO_GO_EXACT_SOLVER_COST` -- committed and independently reviewed

A4-1S exists only to establish that the exact registered machinery is correct,
deterministic, representation-complete, and affordable before any base read.
Its committed parity phase executed:

```text
1,044 exact scalar cases: 780 exhaustive + 8 bit-pattern + 256 PCG64
3,961 persisted scalar solutions and exact-rational replays
2,433,600 allocation decisions, all executed in canonical order and digested
explicit mixed-radix, B4/B8 packing, and LUT fixtures
64 deterministic trained-block-VQ cases plus five named microfixtures
six status-precedence fixtures and 22/22 deterministic tests
```

All registered parity checks passed. The six canonical evidence files are at
`335837e`; independent review at `988ace0` found zero blocker or high-severity
issues. This supports `PASS_PARITY` for the instrument only.

The frozen one-panel `8192 x 128` cost command then reached its registered
early-stop terminal after publishing coordinate 60, leaving 61 complete
scalar-coordinate shards. The reviewed integer accounting is:

```text
timed CPU                         34,805,155,525 us
frozen projection factor                     5 / 2
projected cost                   24.170246892361 CPU-hours
registered ceiling              24.000000000000 CPU-hours
excess                              612.8888125 seconds
```

Canonical shard serialization used 18,096.207493 CPU-seconds, versus
16,706.810033 seconds for exact scalar construction. The result therefore
rejects the whole frozen construction/evidence pipeline, not the scalar solver
alone and not arbitrary-cardinality quantization quality.

Status precedence prevents a broken instrument from becoming scientific
evidence:

| Condition | Outcome |
|---|---|
| artifact/schema or implementation parity defect | `ARTIFACT_INVALID` or `IMPLEMENTATION_INVALID` |
| trained block-control defect | `CONTROL_INVALID` |
| selected scalar alphabet collapses at binary32 | `NO_GO_REPRESENTATION` |
| frozen exact construction/evidence pipeline cost ceiling is exceeded | `NO_GO_EXACT_SOLVER_COST` |
| every correctness, representation, control, and cost gate passes | `PASS_SYNTHETIC_GATE_ONLY` |

`PASS_SYNTHETIC_GATE_ONLY` would have permitted only asking the user whether to
authorize the already-registered base gate. It did not occur.

Cost evidence is committed at `9ce1052`; the independent review and terminal
decision are committed at `f1b464b`. Allocation, block-VQ, and encoding cost
phases did not execute after the scalar-prefix early stop, so the result makes
no claim about them. A4-1 was not run, and untracked worktree files are
deliberately excluded.

---

## 65. A4 V2: Terminal PAR Failure, Source Repair, And Governance Chain

Primary review: `saq-arbitrary-cardinality-feasibility-v2@c4ccea3`

Reviewed protocol snapshot:
`saq-arbitrary-cardinality-feasibility-v2@f86a51d`

Corrected protocol-authority snapshot:
`saq-arbitrary-cardinality-feasibility-v2@f13a383`

Independent erratum-review head:
`saq-arbitrary-cardinality-feasibility-v2@98e6999`

Corrected source snapshot:
`saq-arbitrary-cardinality-feasibility-v2@482c401`

Independent source-review head:
`saq-arbitrary-cardinality-feasibility-v2@4ce2e69`

Reviewed PAR authorization base:
`saq-arbitrary-cardinality-feasibility-v2@2e983a0`

Terminal PAR result snapshot:
`saq-arbitrary-cardinality-feasibility-v2@30dfada`

Independent terminal-review head:
`saq-arbitrary-cardinality-feasibility-v2@fd5367e`

I-R1 source-repair authorization:
`saq-arbitrary-cardinality-feasibility-v2@fe10bc3`

Exact source-repair snapshot:
`saq-arbitrary-cardinality-feasibility-v2@e48df452`

Independent source-repair review head:
`saq-arbitrary-cardinality-feasibility-v2@c401dae`

CACHE-P authorization:
`saq-arbitrary-cardinality-feasibility-v2@ffd0f41`

CACHE-P exact content target:
`saq-arbitrary-cardinality-feasibility-v2@56210f8`

CACHE-P independent review record:
`saq-arbitrary-cardinality-feasibility-v2@249d5b8`

CACHE-I authorization/review:
`saq-arbitrary-cardinality-feasibility-v2@4f38ca9/@187e363`

CACHE-I exact source/static target:
`saq-arbitrary-cardinality-feasibility-v2@c33a2bf`

CACHE-I independent review record:
`saq-arbitrary-cardinality-feasibility-v2@5db3025`

PREP authorization target:
`saq-arbitrary-cardinality-feasibility-v2@e7f940e`

PREP authorization independent review record:
`saq-arbitrary-cardinality-feasibility-v2@16a8201`

Host-rebind erratum target/review:
`saq-arbitrary-cardinality-feasibility-v2@5a47fed/@b89dabe`

HOST-I-AUTH target:
`saq-arbitrary-cardinality-feasibility-v2@212a67b`

HOST-I-AUTH independent review record:
`saq-arbitrary-cardinality-feasibility-v2@71e6bec`

Source-authority erratum target/review:
`saq-arbitrary-cardinality-feasibility-v2@6fe8544/@9fa9528`

HOST-I source-static target/review:
`saq-arbitrary-cardinality-feasibility-v2@4602585/@e8e9c79`

HOST-I-R1 correction-only protocol target/review:
`saq-arbitrary-cardinality-feasibility-v2@ddfef99/@b1a7429`

HOST-I-R1 correction target/review:
`saq-arbitrary-cardinality-feasibility-v2@e17f887/@e10bde7`

The review preserves the old A4-1S result and changes the next question, not
the result. A4-1S timed exact construction together with full canonical
research serialization; serialization alone used 18,096 CPU-seconds. That
supports neither a solver lower bound nor candidate-only deployment cost.

V2 therefore freezes one primary FOM for the complete four-arm synthetic
comparative instrument:

```text
T_instrument = C_setup + C_core + C_bundle_io
PASS iff T_instrument <= 34,560,000,000 CPU microseconds
```

The cap is only an internal admission boundary for the one frozen synthetic
panel. The old `5/2` factor does not transfer: there is no V2 projection to
GIST, CIFAR, two datasets, a full vector, an SAQ index build, or deployment.

Initial source-only inspection found that the parent protocol asked the
terminal `P_parity` receipt to include publication work whose terminal values
did not yet exist. The additive erratum closes only that self-reference with a
finite one-file `PAR_report` after terminal P. It leaves the three parent
blobs, scientific computation, FOM, threshold, retry policy, and status
precedence unchanged.

No work disappears from reporting:

```text
B_build + P_parity + T_instrument
        + E_emit + V_replay + E_archive_body = T_study_metered
PAR_report is a finite one-file PAR authority closure after terminal P
F_trailer is a finite three-file final-study closure after archive-body timing
memory, temporary bytes, bundle bytes, evidence/archive bytes: separately capped
```

Every scientific/parity/control operation and every file validation,
discovery, hash, tree-walk, and byte-ledger derivation required to form the
seal must finish before terminal P. The post-P closure may only inject captured
integers, perform frozen bounded arithmetic, encode one fixed 15-key seal, and
atomically publish it. Its exact conservative schema-language maximum is 5,171
bytes including LF; that maximal witness is syntactic, not a semantically
admissible resource observation.

The schema freezes 396 atomic construction units, exact-prefix evidence,
independent exact-rational scalar/allocation replay, deterministic bit-level
block/encoding/packing replay, raw prelaunch evidence, and admissibility-first
status precedence. The four-arm bundle is A4-reference-equivalent only; it is
not current SAQ's serialized representation or query estimator.

The corrected protocol authority passed independent timing-closure, schema,
and Git-authority review. Initial implementation commit `3a4f7c5` then failed
static review and remains non-evidence. Corrected exact source commit
`482c401` passed three independent static-only reviews. Its canonical manifest
binds 35 exact sources at source-tree SHA-256 `d5b8374f...`.

The user later authorized exactly one frozen PAR invocation at reviewed and
pushed base `2e983a0`. It returned exit `3` with frozen status
`ARTIFACT_INVALID`: `sys.executable` was `/bin/python`, whose terminal path
object was a symlink rejected by the conductor's no-follow leader-identity
read. The failure occurred before host, NumPy, or process-inventory observation
and before any B/P worker.
No CMake/build child, PCG64 fixture, parity case, receipt, ledger, build
manifest, parity summary, artifact index, seal, or final PAR directory was
produced.
The empty staging directory and ignored bytecode caches are non-evidence.

The reviewed terminal claim is exactly:

```text
ARTIFACT_INVALID
REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

This is artifact-validation failure evidence, not `PASS_PARITY`, feasibility,
quantization quality, natural-data, ANN, or systems evidence. Static source
review did not establish executable-identity compatibility on the pinned host.
Tooling correctness remains separate from the database-systems contribution.

The later I-R1 correction changes only CPython leader identity. It opens a
stable descriptor for literal `/proc/self/exe`, requires intentionally
followed normalized `sys.executable` to name the same nonempty regular inode,
performs a bounded full EOF-checked read with before/after stability, and uses
that identity consistently in conductor, runner admission/receipts, and a
physically independent positional-read verifier. Generic artifact readers
retain `O_NOFOLLOW`.

Exact source `e48df452` and canonical 35-source tree
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`
passed three independent static reviews with no finding at LOW or above. No
Python module, compiler, build, test, fixture, RNG, native command, or data
path was executed. The maximum result is therefore only:

```text
SOURCE_REPAIR_STATIC_REVIEW_PASS
```

CACHE-P resolves only the protocol question raised by the five quarantined
bytecode files. Its primary-source review records that CPython `-B` suppresses
cache writes but does not disable reads of an already present valid cache.
The exact target therefore retains those residuals as unread non-evidence,
requires non-destructive sanitized remote isolation, and rejects a direct
transition to PAR-R1. It preserves exact source repair `e48df452`, manifest
blob `2aa64e50...`, and the 35-source tree
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.

The committed CACHE-P claim is exactly:

```text
EXACT_TARGET_INDEPENDENT_REVIEW_PASS
GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED
NO_GO_DIRECT_PAR_R1
```

This is artifact-governance evidence only. CACHE-P imported no module, changed
no source or environment, created no clone, prepared no remote tree, and ran
no build, fixture, parity, synthetic, base, query, or SAQ work.

CACHE-I implements only the generic cache-governance layer frozen by CACHE-P.
Its exact target has 37 filesystem sources (ten Python and 27 native) plus one
separately bound inline bootstrap, with source-tree SHA-256
`9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2`.
The static closure binds four schema/maximal-instance pairs, cache-aware PAR
shapes, the independent cache verifier, and a complete 38-unit
import/process/mutation crosswalk. Independent review found 0 issues at LOW or
above.

After the source bytes were locked, a separately authorized Python 3.9
`compile()`-only check accepted the six changed/new outer sources and inline
bootstrap. No code object was executed and no module was imported. The exact
claim is only:

```text
GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
```

This is artifact-governance source/static-review evidence, not PREP readiness,
runtime correctness, parity, feasibility, an SAQ limitation, performance,
novelty, or a method.

The later host-rebind erratum `5a47fed/@b89dabe` froze the current
`.el9_8.2` leader and a bounded future rebind closure but did not change the
source. HOST-I-AUTH target/review `212a67b/@71e6bec` then passed with zero
LOW+ findings and only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. It did not
edit the five sources or seven derived authority objects, establish
`HOST_IDENTITY_REBOUND`, or run Python, build, PREP, or data. It authorizes no
execution. When HOST-I was instructed, exact checking found an unsatisfiable
seven-versus-eight protocol-component closure before any source target.
Additive source-authority erratum target/review `6fe8544/@9fa9528` passed
three static tracks and reached only
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`. It admits the eighth component
but changes no implementation source or derived authority object. The later
source-static target `4602585` was independently reviewed at `e8e9c79` and
failed with one HIGH authority-identity mismatch: two derived documents cite
the wrong governing-review SHA-256. That target remains failed evidence. The
correction-only protocol target/review `ddfef99/@b1a7429` passed with zero
LOW-or-higher findings; exact R1 target/review `e17f887/@e10bde7` then passed
with zero LOW-or-higher findings after reproducing the frozen four artifact
substitutions, closure, and 13/13 host identities. `HOST_IDENTITY_REBOUND` is
established only for the registered 13-object bundle; whole-host identity is
not established. Source-history protocol target/review `dcaed57/@e98a3e4`
passed, but its future one-source correction remains unauthorized and
unimplemented, so `SOURCE_HISTORY_MISMATCH` still prevents cache-verifier/PAR
readiness.

Future stages are separate and non-transitive:

| Stage | Scope | Current authorization |
|---|---|---|
| `A4-V2-I` | source implementation and independent static review only | `COMPLETED_REVIEW_PASS` |
| `A4-V2-PAR` | frozen build and parity only | `REVIEWED_TERMINAL_ARTIFACT_INVALID`; no valid PAR authority |
| `A4-V2-I-R1` | executable-identity source repair and static review only | `SOURCE_REPAIR_STATIC_REVIEW_PASS` |
| `A4-V2-CACHE-P` | primary-source review and frozen staged-isolation protocol | `EXACT_TARGET_INDEPENDENT_REVIEW_PASS`; governance only |
| `A4-V2-CACHE-I` | generic source/schema/static closure only | `GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`; governance only |
| PREP authorization/review | freeze one sanitized remote preparation event | `PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`; documentation governance only |
| `A4-V2-PREP-HOST-P` | additive current-host rebind protocol and exact review | `HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`; host identity is not rebound |
| `A4-V2-PREP-HOST-I-AUTH` | freeze only the contract/projection for a possible later source/review edge | `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`; documentation governance only; grants no HOST-I authority |
| attempted `A4-V2-PREP-HOST-I` | validate the frozen projection before source editing | `STOPPED_BEFORE_TARGET`; exact seven-versus-eight contradiction |
| `A4-V2-PREP-HOST-I-ERRATUM` | admit the eighth protocol component and freeze exact future accounting | `HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`; documentation governance only |
| `A4-V2-PREP-HOST-I` | implement and independently review the coherent five-source/seven-derived-authority rebind | `SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH`; target/review `4602585/@e8e9c79`, one HIGH, retained as immutable failed evidence |
| `A4-V2-PREP-HOST-I-R1-P` | freeze a correction-only exact five-path target and its direct-child review projection | `HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS`; target/review `ddfef99/@b1a7429`, documentation governance only |
| `A4-V2-PREP-HOST-I-R1` | apply only the frozen authority-identity correction and review it | `HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS`; target/review `e17f887/@e10bde7`; rebound established for registered 13-object bundle only, with no execution |
| `A4-V2-SOURCE-HISTORY-P` | freeze an exact fail-closed two-epoch correction protocol | `SOURCE_HISTORY_EPOCH_CORRECTION_PROTOCOL_REVIEW_PASS`; target/review `dcaed57/@e98a3e4`, zero LOW+, protocol governance only |
| `A4-V2-SOURCE-HISTORY-I` | implement the frozen one-source/ten-path epoch correction | `NOT_AUTHORIZED`; `SOURCE_HISTORY_MISMATCH` remains open in source |
| one sanitized preparation + receipt/review | prepare without reading quarantine, then commit and review its receipt | `NOT_AUTHORIZED` |
| `A4-V2-CACHE-BIND` | bind only the independently reviewed sanitized preparation | `NOT_AUTHORIZED` |
| `A4-V2-PAR-R1` | at most one corrected frozen build/parity event after the full isolation chain | `NOT_AUTHORIZED`; direct transition rejected |
| `A4-V2-SRUN` | one logical synthetic admission event | `NOT_AUTHORIZED` |
| data / SAQ | base, query, index, estimator, integration | `NOT_AUTHORIZED` |

---

## 66. Current Synthesis

| Attempt | Theoretical guarantee | Strongest positive evidence | Decision / current boundary |
|---|---|---|---|
| 1A full-D PCA replacement | L2 isometry for any orthogonal transform | GIST residual-PCA accurate/full RMSE `-0.60%/-0.33%` | no stable ranking gain; fast harm; CIFAR replication failure |
| 1B lossy `D -> d` | exact head and norm terms in favorable oracle | tail norms reduce RMSE from 0.0445 to 0.00248 | omitted tail IP still worsens ranking versus native SAQ |
| 2 exact scalar DP | exact bin-boundary partition SSE using raw bin moments; final midpoint-nearest-centroid raw SSE is evaluated, not reoptimized; outer optimum is conditional on `E[j,b]` | audio B=4 raw MSE `-15.5%`, R@100 `+0.004` | inner-DP novelty is foreclosed by prior art; no full-scale raw optimum or recall guarantee; cross-regime reversals |
| 3 distance-quality re-evaluation | paper-exact metric semantics; no method guarantee | GIST measured point: higher `1/Ratio`, `1.078x` QPS at the frozen target | one positive setting; DEEP controls remain negative; metric is prior work |
| 4 arbitrary-cardinality fixed-rate words | the arbitrary positive-integer feasible set contains the dyadic set for exact factorized SSE | frozen `(3,5)` witness and A4-1S parity; later positive records are protocol/source/artifact-governance evidence only | preserve A4-1S `NO_GO_EXACT_SOLVER_COST` and PAR `ARTIFACT_INVALID / NO_SCIENTIFIC_DECISION`; R1 established registered-bundle rebound only; source-history protocol passed but implementation is unauthorized, so `SOURCE_HISTORY_MISMATCH` remains open in source and PREP/binding/PAR-R1 remain unauthorized |

Cross-attempt lesson:

```text
Optimizing a mathematically valid surrogate is not enough, and changing the
evaluation metric is not itself a mechanism.

The missing contribution must connect its optimized quantity to top-k or
downstream quality and system work, survive a second baseline or regime, and
include all construction, storage, and query overhead.

Attempt 4 was deliberately staged so that a representation theorem or a
synthetic witness could not silently become a method claim. The committed and
reviewed A4-1S cost stop prevented the next expansion of scope. V2 changes the
future measurement contract, its additive erratum closes one reporting
self-reference, and its corrected source passed static review. The later PAR
failure shows that static review did not guarantee executable-identity
compatibility; it is tooling/artifact evidence only and says nothing about
instrument feasibility. I-R1 closes the identified source defect under static
review, but without corrected execution it still says nothing about parity or
instrument feasibility. CACHE-P freezes how a future clean artifact could be
isolated, and CACHE-I statically closes only the corresponding generic source
and schema layer. Their reviews and the narrow syntax check are governance
evidence, not feasibility evidence. The later PREP authorization record also
passed exact-target review, but a later static host mismatch retired its
activation path before PREP. The reviewed additive host erratum freezes only
a future rebind contract; it does not rebind the host or grant PREP or
execution authority. The later HOST-I-AUTH review freezes only the contract
and projection for a possible source edge and grants no HOST-I authority; no
source/authority rebind, Python, or PREP ran. Its attempted HOST-I edge stopped
before edits on a seven-versus-eight component contradiction. The reviewed
source-authority erratum fixed that contract admission. The later source-
static target was formed, but its direct-child review failed on one HIGH
authority-identity mismatch. Its later correction-only target passed exact
review and established rebound only for the registered 13-object bundle.
Whole-host and execution readiness remain unestablished. A later reviewed
source-history protocol freezes a bounded two-epoch repair, but its source
implementation is unauthorized and cache/PAR readiness cannot be claimed.
```

---

## 67. Proposed Meeting Discussion

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
Do we agree to preserve the terminal A4-1S pipeline-cost failure, while
treating the reviewed A4 V2 PAR `ARTIFACT_INVALID` result only as an artifact-
validation failure, with no inference about arbitrary-cardinality
quantization or instrument feasibility; treating I-R1 only as a reviewed
source repair rather than artifact readiness; and accepting CACHE-P only at
its artifact-governance ceiling, including sanitized remote isolation and the
no-go on direct PAR-R1; and treating CACHE-I's static pass as governance
source evidence rather than PREP readiness; and treating the later PREP
authorization review as a dormant contract rather than a completed clone or
feasibility result; treating HOST-I-AUTH and the source-authority erratum as
governance only; and treating the later HOST-I source-static target as a
failed authority-DAG artifact whose otherwise passing static checks do not
establish host rebound by themselves; while treating the reviewed R1 repair
PASS as bounded identity governance for the registered 13-object bundle—not
whole-host identity, execution, PREP readiness, or cache-verifier/PAR
readiness?
```

The current authorization boundary is narrow:

```text
A4-V2-PAR was invoked once and terminated before build/parity.
There is no active execution authority and no valid PAR authority.

The clean I-R1 source commit and independent static review are complete.
CACHE-P target/review `56210f8/@249d5b8` froze
`GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED / NO_GO_DIRECT_PAR_R1`.
CACHE-I target/review `c33a2bf/@5db3025` subsequently reached only
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`; the quarantine remains
unread and uncleaned. PREP authorization target/review `e7f940e/@16a8201`
subsequently reached only `PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`.
Static checking then found the `.el9_8 -> .el9_8.2` leader replacement before
PREP or START. Host-rebind erratum target/review `5a47fed/@b89dabe` reached
only `HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`; that protocol stage did not
rebind host identity.
The old authority is nontransferable and the old probe is superseded and must
never run or be reused. HOST-I-AUTH target/review `212a67b/@71e6bec` reached
only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`; it performed no five-source or
seven-derived-object rebind and ran no Python or PREP. The attempted HOST-I
edge then stopped before any source target on an exact seven-versus-eight
component contradiction. Source-authority erratum target/review
`6fe8544/@9fa9528` reached only
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`. The subsequently authorized
HOST-I target/review `4602585/@e8e9c79` ended at
`SOURCE_STATIC_TARGET_REVIEW_FAIL_AUTHORITY_IDENTITY_MISMATCH`: one HIGH,
host rebound not established. Correction-only protocol target/review
`ddfef99/@b1a7429` then reached
`HOST_I_R1_CORRECTION_ONLY_REPAIR_PROTOCOL_REVIEW_PASS`. Exact R1 target/review
`e17f887/@e10bde7` subsequently reached
`HOST_I_R1_CORRECTION_ONLY_REPAIR_REVIEW_PASS`, establishing rebound only for
the registered 13-object bundle. Whole-host identity remains unestablished and
no Python, build, PREP, or scientific execution ran. A future
`SOURCE_HISTORY_MISMATCH` now has reviewed protocol target/review
`dcaed57/@e98a3e4`, but the source correction remains unimplemented and
unauthorized, so cache-verifier/PAR readiness is not established. No next
node is currently authorized; stop for a user checkpoint. Fresh PREP
authorization/review, a new invocation grant and newly registered immediate
probe, actual PREP, receipt review, CACHE-BIND, explicit PAR-R1, and SRUN all
remain separate and unauthorized; base/query inputs, SAQ changes, and the old
A4-1 gate remain unauthorized.
```

Speaker notes:

- Attempt 4 completed synthetic correctness validation and a falsification of
  affordability under the frozen pipeline-cost gate; allocation, block-VQ,
  and encoding cost phases were not
  reached after the scalar-prefix early stop.
- A4 V2's scientific PAR work remains unexecuted: the conductor was invoked
  but stopped at executable-identity admission before build, RNG, or parity.
  Its erratum repairs reporting closure and its source pass checks artifact
  machinery only; I-R1 statically repairs the identified path but has not been
  executed. The old `5/2` projection is not a V2 cost model.
- Novelty, mechanism, replication, and total overhead should be challenged
  before experimental scope is expanded.

---

## 68. Evidence And Code Map

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

Attempt 4, branch `saq-arbitrary-cardinality-analysis@f1b464b`:

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
docs/saq_attempt4_a4_1s_artifacts_2026_07_13/parity_artifact_index.json
docs/saq_attempt4_a4_1s_implementation_parity_review_2026_07_13.md
docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_manifest.json
docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_summary.json
docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_detail_ledger.json
docs/saq_attempt4_a4_1s_artifacts_2026_07_13/cost_projection_artifact_index.json
docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md
```

Attempt 4 V2 corrected protocol-authority snapshot
`saq-arbitrary-cardinality-feasibility-v2@f13a383`, corrected source snapshot
`@482c401`, terminal PAR result/review `@30dfada/@fd5367e`, and exact I-R1
source-repair/review `@e48df452/@c401dae`, followed by CACHE-P exact content
target/review record `@56210f8/@249d5b8` and CACHE-I exact source/static
target/review `@c33a2bf/@5db3025`, then the exact PREP authorization
target/review `@e7f940e/@16a8201`, and host-rebind erratum target/review
`@5a47fed/@b89dabe`, followed by HOST-I-AUTH target/review
`@212a67b/@71e6bec`, then source-authority erratum target/review
`@6fe8544/@9fa9528`, and finally HOST-I source-static target/review
`@4602585/@e8e9c79`, followed by HOST-I-R1 correction-only repair protocol
target/review `@ddfef99/@b1a7429` and correction target/review
`@e17f887/@e10bde7`, then source-history epoch-correction protocol
target/review `@dcaed57/@e98a3e4`:

```text
docs/saq_a4_v2_primary_source_metadata_2026_07_14.json
docs/saq_a4_v2_cost_evidence_primary_source_review_2026_07_14.md
docs/saq_a4_v2_cost_evidence_go_no_go_memo_2026_07_14.md
docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md
docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json
docs/saq_a4_v2_artifact_schema_2026_07_14.json
docs/saq_a4_v2_protocol_independent_review_2026_07_14.md
docs/saq_a4_v2_par_report_erratum_authorization_2026_07_14.md
docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.md
docs/saq_a4_v2_par_report_timing_closure_erratum_2026_07_14.json
docs/saq_a4_v2_par_report_seal_schema_2026_07_14.json
docs/saq_a4_v2_par_report_seal_maximal_instance_2026_07_14.json
docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json
docs/saq_a4_v2_par_report_timing_closure_erratum_independent_review_2026_07_14.md
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
docs/saq_a4_v2_implementation_independent_review_2026_07_15.md
docs/saq_a4_v2_par_authorization_2026_07_15.md
docs/saq_a4_v2_par_prebuild_artifact_identity_failure_2026_07_15.md
docs/saq_a4_v2_par_prebuild_artifact_identity_failure_independent_review_2026_07_15.md
docs/saq_a4_v2_executable_identity_source_repair_authorization_2026_07_15.md
docs/saq_a4_v2_executable_identity_source_repair_independent_review_2026_07_15.md
docs/saq_a4_v2_cache_staging_policy_authorization_2026_07_15.md
docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json
docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md
docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md
docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json
docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md
docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md
docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md
docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json
docs/saq_a4_v2_cache_static_closure_2026_07_15.json
docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json
docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json
docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md
docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md
docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md
docs/saq_a4_v2_prep_host_identity_rebind_erratum_protocol_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json
docs/saq_a4_v2_prep_host_identity_rebind_erratum_independent_review_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_independent_review_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_protocol_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_contract_2026_07_16.json
docs/saq_a4_v2_prep_host_identity_rebind_implementation_erratum_independent_review_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_2026_07_17.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_contract_2026_07_17.json
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_protocol_independent_review_2026_07_17.md
docs/saq_a4_v2_prep_host_identity_rebind_r1_correction_only_repair_independent_review_2026_07_17.md
docs/saq_a4_v2_source_history_epoch_correction_protocol_2026_07_17.md
docs/saq_a4_v2_source_history_epoch_correction_contract_2026_07_17.json
docs/saq_a4_v2_source_history_epoch_correction_protocol_independent_review_2026_07_17.md
```

A4-0 and A4-1S parity are outcome evidence only at their stated instrument
ceilings. A4-1S cost is a reviewed pipeline-cost no-go. A4-1 remains an
unexecuted frozen protocol; no natural-data, ANN, or systems result is
established. A4 V2 has an independently reviewed corrected protocol and source
plus one reviewed pre-build `ARTIFACT_INVALID` PAR invocation. It produced no
valid PAR authority or scientific decision. I-R1 later reached static source-
repair review pass only; it did not run. CACHE-P later reached
`EXACT_TARGET_INDEPENDENT_REVIEW_PASS`, requiring sanitized remote isolation
and rejecting direct PAR-R1 at an artifact-governance ceiling. It did not read
or clean the quarantine. CACHE-I then reached
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS` for its generic source/schema
layer, with a separate syntax-only pass but no import or code execution. The
later PREP authorization record reached
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. A later static host mismatch
prevented PREP and START; the old probe is superseded and may never be reused.
The host-rebind erratum reached only
`HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`, not host rebound or PREP
readiness. HOST-I-AUTH then reached only
`AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`; it changed no source/authority
object and ran no Python or PREP. The attempted HOST-I edge stopped before a
target on the seven-versus-eight contradiction; its additive source-authority
erratum reached only `HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS` and changed
no implementation source or derived authority object. The later HOST-I
source-static target/review `4602585/@e8e9c79` failed on one HIGH false
governing-review digest, so host rebound remains unestablished and correction
was not performed. Correction-only protocol target/review `ddfef99/@b1a7429`
then passed with zero LOW-or-higher findings. Exact R1 target/review
`e17f887/@e10bde7` subsequently passed and established rebound only for the
registered 13-object bundle; whole-host identity remains unestablished and no
execution ran. A separate `SOURCE_HISTORY_MISMATCH` source repair is still required
before cache-verifier or PAR readiness; its protocol target/review
`dcaed57/@e98a3e4` passed, but source implementation is unauthorized. Fresh
PREP authority, actual PREP,
receipt review, CACHE-BIND, PAR-R1, A4-V2-SRUN, and all data access remain
unauthorized until their own reviewed and explicit authorities exist.

Current deck:

```text
docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md
```

---

## 69. One-Slide Takeaway

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
exact implementation parity passed, but the frozen construction/evidence
pipeline projected to 24.170246892361 CPU-hours and failed its 24-hour gate.
That terminal result remains unchanged. A4 V2 now freezes a direct internal
comparative-instrument FOM and a complete evidence ledger. Its reviewed
erratum adds only a finite one-file terminal-P reporting closure; the old 5/2
projection does not transfer. Corrected V2 source passed independent static
review. The later authorized PAR conductor ran only far enough to reject the
`/bin/python` symlink at its no-follow identity boundary; no build, RNG,
fixture, parity case, or final artifact was produced. I-R1 subsequently bound
leader identity to stable `/proc/self/exe` bytes plus same-inode
`sys.executable` validation and passed exact-commit static review. It was not
executed and therefore establishes neither parity nor artifact readiness.
CACHE-P subsequently reviewed CPython cache semantics and the frozen source
without reading the quarantine. Exact target `56210f8`, independently reviewed
at `249d5b8`, freezes sanitized remote isolation and rejects direct PAR-R1.
That is artifact governance only: it creates no clone, preparation, parity, or
scientific evidence. CACHE-I target `c33a2bf`, independently reviewed at
`5db3025`, then closed 37 filesystem sources and one separate inline bootstrap
under the generic cache policy. Its separately authorized syntax-only check
executed no code object. The result is only
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`, not PREP readiness or
feasibility evidence. PREP authorization target `e7f940e`, independently
reviewed at `16a8201`, subsequently reached only
`PREP_AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. Static prelaunch checking then
found the `.el9_8 -> .el9_8.2` leader replacement before PREP or START. The
host-rebind erratum target `5a47fed`, independently reviewed at `b89dabe`,
reached only `HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS`. It created no clone,
token, or receipt, did not rebind the host, and superseded the old probe;
HOST-I-AUTH target `212a67b`, independently reviewed at `71e6bec`, then
reached only `AUTHORIZATION_EXACT_TARGET_REVIEW_PASS`. That is documentation
governance only: no five-source/seven-derived-object rebind, Python, build, or
PREP occurred. The attempted HOST-I source edge stopped before a target on an
exact seven-versus-eight component contradiction. Source-authority erratum
target `6fe8544`, independently reviewed at `9fa9528`, reached only
`HOST_I_SOURCE_AUTHORITY_ERRATUM_REVIEW_PASS`; it changes no implementation
source or derived authority object. The later source-static target `4602585`,
independently reviewed at `e8e9c79`, failed with one HIGH because two
authority documents cite the wrong governing-review SHA-256. Host rebound is
not established. Correction-only protocol target `ddfef99`, independently
reviewed at `b1a7429`, froze the exact five-path R1 edge. Correction target
`e17f887`, independently reviewed at `e10bde7`, then passed with zero LOW-or-
higher findings across the correction, closure, and 13/13 registered host
objects. This establishes only registered-bundle rebound, not whole-host or
execution readiness. Source-history protocol target `dcaed57`, independently
reviewed at `e98a3e4`, subsequently passed and froze a strict two-epoch future
repair. It made no source change, so PREP remains unauthorized and cache-
verifier/PAR readiness is still unestablished.

Project decision:
Keep Attempts 1--3 as rigorous negative or partial evidence. Do not rescue
them with post-hoc sweeps. Preserve A4-1S as a preregistered synthetic cost
stop. Treat A4 V2 only as reviewed protocol plus a source-static review pass,
followed by a reviewed terminal `ARTIFACT_INVALID` and a later reviewed static
source repair, not feasibility evidence. CACHE-P additionally provides a
reviewed isolation protocol, with
`GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED / NO_GO_DIRECT_PAR_R1`, but
the later CACHE-I result remains static artifact governance only. Treat the
subsequent PREP authorization and host-rebind erratum reviews as documentation
governance, not PREP readiness or execution. Treat HOST-I-AUTH the same way:
it freezes only the contract/projection for a possible future source edge and
grants no HOST-I authority. Treat the source-authority erratum as a correction
of that projection only, not source implementation, host rebound, or
readiness. Treat the later HOST-I target as a failed authority-DAG target, not
host rebound. Its later correction-only protocol passed direct-child review,
and actual R1 subsequently passed direct-child review, establishing only the
registered 13-object bundle identity. Do not promote that result to whole-host,
PREP, cache/PAR, performance, or scientific readiness. Treat the reviewed
source-history protocol as correction governance only; its future
implementation remains unauthorized. Fresh PREP
authorization/review, a
new invocation grant and immediate probe, actual PREP, receipt review,
CACHE-BIND, separately explicit PAR-R1, and SRUN remain a strictly ordered
unauthorized chain; base, query, and SAQ gates remain closed.
```

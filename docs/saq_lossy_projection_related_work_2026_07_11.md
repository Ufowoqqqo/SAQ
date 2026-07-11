# Lossy Projection + SAQ: Related-Work Review And Novelty Boundary

## Review Decision

The direction is legitimate as a **collision-first falsification study**, but
"combine lossy projection with SAQ" is not a defensible contribution.

Three primary sources occupy most of the apparent design space:

- [ASH](https://arxiv.org/abs/2606.07870) learns a global orthonormal
  `D -> d` encoder and explicitly trades fewer dimensions for more
  scalar-quantization bits at fixed payload.
- [MRQ](https://www.vldb.org/pvldb/vol19/p1240-yang.pdf) quantizes a PCA head,
  retains residual statistics, and performs multi-stage IVF refinement with
  quantization and residual error bounds.
- [LeanVec](https://arxiv.org/abs/2312.16335) combines linear dimensionality
  reduction with quantization and uses primary/secondary representations for
  search and reranking.

The narrowest hypothesis not directly covered by the bounded set of primary
sources reviewed here is:

```text
Does physical dimension d interact non-separably with SAQ's heterogeneous
segment bits, CAQ adjustment, and progressive prefixes under original-space
ranking and complete bytes/work accounting?
```

Even this is a hypothesis to falsify. It is not a novelty claim until the
closest baseline envelope is measured.

Machine-readable source metadata is in
`saq_lossy_projection_related_work_sources_2026_07_11.json`.

## Starting Boundary In SAQ

The local SAQ paper source already states that dimension reduction applies a
PCA projection and discards trailing dimensions
(`paper_src/2509.12086/main.tex`, around lines 337--368). It later describes
SAQ as combining dimension balancing and dimension reduction, with low-variance
tail segments receiving fewer bits or being discarded (around lines 679--693).
Its PCA baseline also drops insignificant projected dimensions (around line
875).

The repository's current execution path is different from that conceptual
description: `python/pca.py` fixes `D_OUT = D_IN`. SAQ then reduces rate
logically through mixed segment bits and an optional final 0-bit segment. In
L2, that 0-bit estimator retains the base and query tail norms while omitting
the tail inner product (`saqlib/quantization/caq/caq_estimator.hpp`).

Therefore the new systems question is not whether PCA is a dimensionality
reduction technique. It is whether **physically materializing only `d`
coordinates** provides a useful work/bytes frontier beyond SAQ's existing
logical tail omission.

## Closest Work

### ASH

[ASH: Asymmetric Scalar Hashing With Learned Dimensionality Reduction for
High-Fidelity Vector Quantization](https://arxiv.org/abs/2606.07870) is the
most direct collision. Its June 2026 v1 learns a row-orthonormal `D -> d`
projection from indexed data, scalar-quantizes the projected database
representation, keeps the query asymmetric, and supports SIMD-oriented
distance evaluation. Its central fixed-payload result is that reducing
dimension while increasing bitrate per retained dimension exposes faster and
more accurate configurations.

Consequences for this branch:

- the fixed-payload tradeoff between a uniform bitrate and its derived
  retained dimension is already occupied;
- "fewer dimensions, more uniform bits per dimension" is a baseline
  mechanism;
- a learned global projection followed by unchanged SAQ is a composition;
- ASH's uniform bitrate leaves only the possible value of SAQ's heterogeneous
  segment allocation and progressive estimator as a narrow distinction.

ASH also uses landmark/centroid residualization and per-vector scalars. Its
operator, centroid, scalar, and identifier bytes must be counted consistently
when comparing it with SAQ. Its main formulation is inner product/cosine;
squared-L2 requires regression calibration using sampled queries and indexed
vectors in the published procedure. That query-calibrated result is an
outside-scope reference under this branch's base-only rule. A direct admissible
baseline must use a frozen base-only calibration split and report it separately.
The arXiv v1 page does not link official source code, so any reproduction must
be labeled precisely.

### MRQ

[Quantization Meets Projection: A Happy Marriage for Approximate k-Nearest
Neighbor Search](https://www.vldb.org/pvldb/vol19/p1240-yang.pdf) is the closest
head/tail and staged-search collision. MRQ applies PCA, quantizes only a
user-controlled information-dense head, stores a per-vector tail norm, uses
dataset-level residual variances, and applies multiple distance stages and
error bounds inside IVF. The authors provide an
[official artifact](https://github.com/mingyu-hkustgz/RESQ).

Consequences:

- PCA head plus tail norm/variance is already occupied;
- approximate head, projected-exact refinement, and original-exact refinement
  are already occupied;
- residual-error bounds are already occupied;
- an exact-rerank vector store must be included in total footprint even when a
  paper's index-space figure excludes base vectors.

Current SAQ's 0-bit L2 residual semantics already implement the same coarse
head-plus-residual-tail-norm distance form. A tail-norm arm is therefore both
an MRQ baseline and a current-SAQ equivalence control.

MRQ's quantized head is RabitQ-style rather than SAQ's heterogeneous
multi-segment CAQ. This is a possible empirical distinction, not a contribution
by definition. MRQ's residual bound relies on centered PCA-tail assumptions and
parameters including a Chebyshev multiplier, quantization bound, and artifact
`var_count`; freeze compatible choices from base-only information rather than
evaluation queries.

### LeanVec And GleanVec

[LeanVec](https://openreview.net/forum?id=wczqrpOrIc) combines linear dimensionality
reduction with vector quantization. The in-distribution form is the appropriate
query-unaware baseline: it learns from indexed vectors, searches a compact
low-dimensional primary representation, and uses a higher-dimensional
secondary representation for refinement. The secondary representation and
query projection must be included in footprint and QPS accounting.

LeanVec's reported experiments use query performance at a target recall when
choosing projection dimension. This branch must replace that with a frozen
base-only rule. The public
[SVS repository](https://github.com/intel/ScalableVectorSearch) excludes the
proprietary LeanVec/LVQ source, so distinguish a reproducible truncated-PCA
projection control from a packaged official-system measurement.

LeanVec-OOD uses representative query information and is outside the current
base-only learning contract.

[GleanVec](https://arxiv.org/abs/2410.22347) adds a linear sphering method and a
piecewise-linear, locally adaptive projection. Its cluster-specific state
violates the initial one-global-projection architecture. It defines the
related-work boundary but is not a design to reproduce inside this branch
unless the research scope is explicitly changed.

### Projected Progressive Distance

[DADE](https://www.vldb.org/pvldb/vol18/p812-zheng.pdf) estimates exact distance in a lower-
dimensional space, uses hypothesis testing to adapt the required projected
work, and integrates the distance operation with IVF and HNSW. Its comparison
space includes PCA/data-aware projection and random-projection
ADSampling-style controls. It therefore occupies broad claims around projected
prefixes, probabilistic distance bounds, and fallback to more exact work.
The authors provide an [official artifact](https://github.com/Ur-Eine/DADE).

### Rotation And Quantization Controls

[Optimized Product Quantization](https://openaccess.thecvf.com/content_cvpr_2013/html/Ge_Optimized_Product_Quantization_2013_CVPR_paper.html)
learns a full-dimensional orthogonal transform for quantization distortion. It
does not physically reduce dimension, but any later learned projection must
show that its benefit is not simply an OPQ-style orientation effect.

[TurboQuant](https://arxiv.org/abs/2504.19874) uses a random rotation and
scalar quantizers, with an additional residual quantizer for unbiased inner
product estimation. Its residual is quantization residual, not a discarded PCA
tail. It is a modern quantization control rather than the proposed projection
mechanism.

### Learned Nested Embeddings

[Matryoshka Representation Learning](https://arxiv.org/abs/2205.13147) and
[AdANNS](https://openreview.net/forum?id=ZBzYWP2Gpl) use nested representation
prefixes and can vary dimensionality across ANN stages. They require an
embedding model trained to expose useful prefixes, whereas the current scope is
post-hoc, query-unaware projection of fixed embeddings such as GIST. They are
important boundaries if the scope later moves to learned embedding models, but
not direct GIST baselines.

## Novelty Matrix

| Mechanism | Already covered by | Status here |
|---|---|---|
| PCA truncation | classical PCA, SAQ baseline, LeanVec-ID, MRQ | baseline |
| Learn global `D -> d` projection | ASH, LeanVec | baseline |
| Fewer dimensions with more bits | ASH | baseline |
| PCA head plus tail norm/variance | MRQ; SAQ 0-bit semantics | equivalence/control |
| Low-D primary plus full-D rerank | LeanVec, MRQ | baseline |
| Multi-stage approximate/projected/original distance | MRQ | baseline |
| Projected prefix, probabilistic bound, adaptive exact work | DADE/ADSampling | baseline |
| Local or piecewise projection | GleanVec | outside architecture |
| Heterogeneous segment bits on a physical head | SAQ composition | open diagnostic |
| Progressive mixed-bit prefix quality jointly with `d` | not identified together in this bounded review | open diagnostic |
| Complete physical projection versus logical 0-bit work | not isolated in SAQ | open systems question |

## Required Baseline Envelope

Before any positive claim, compare at matched total bytes and complete query
work:

1. native full-D SAQ with its logical 0-bit tail;
2. physical projection at the same positive/zero boundary;
3. exact truncated-PCA head, with and without the registered tail norm;
4. uniform-bit projected quantization;
5. ASH;
6. MRQ and MRQ+;
7. LeanVec-ID;
8. compatible DADE/ADSampling-style projected computation;
9. projected exact and original exact diagnostic oracles.

No local ASH, MRQ, LeanVec, or GleanVec implementation was found. External
artifact work is unnecessary for the first projection-floor gate, but it is
mandatory before a positive method or end-to-end claim.

## Reviewer Verdict And Stop Rule

A strict reviewer will reject the work as an ASH/MRQ/LeanVec composition if
the result can be described as any of the following:

```text
truncate PCA, spend the saved bits on the head, attach a tail norm,
then rerank a few candidates exactly
```

Continue beyond the offline gate only if the evidence isolates a repeatable
SAQ-specific interaction: the joint `(d, segment, bit, prefix)` choice must
produce a Pareto point that neither a uniform-bit projected quantizer nor the
closest published systems reproduce, with original-space labels and all
operator/metadata/refinement costs included. Otherwise record the negative
result and close the direction.

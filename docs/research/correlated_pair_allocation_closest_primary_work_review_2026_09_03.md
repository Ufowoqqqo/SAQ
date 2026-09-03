# Closest-primary-work review: allocation between two-dimensional groups

Date: 2026-09-03

Reviewed snapshot: `ad1018e` on `saq-correlated-pair-allocation`

## Decision

The observed residual-space effect is real, but the method currently used to
obtain it is not a new general quantization mechanism. PCA or local orthogonal
transforms, empirical scalar rate--distortion curves, and unequal bit
allocation between fixed subspaces are all established primary work. Using an
exact dynamic program instead of a greedy allocator makes the restricted
offline solution exact; it does not by itself create a new scientific model.

The current result therefore should not be presented as a standalone
two-dimensional block-allocation contribution. It also does not yet establish
a limitation of SAQ, because its baseline is uniform eight-bit groups rather
than SAQ's existing segmentation and bit-allocation planner.

One narrower SAQ-specific systems question remains open:

> Can SAQ express fine-grained, base-only mixed precision inside a
> factor-sharing segment while retaining its one-bit fast stage, fixed payload,
> compact factors, and near-unchanged scan work?

This is a research question, not a positive novelty finding. The present
local-PCA/Lloyd diagnostic neither implements nor tests it.

## Method being reviewed

For the first 128 raw, PCA, or IVF-residual coordinates, the diagnostic:

1. forms 64 two-coordinate groups;
2. learns an independent local two-dimensional PCA in each group;
3. fits independent one-dimensional Lloyd quantizers on the two local axes;
4. measures each group's reconstruction SSE for 6--10 total bits, including
   the best integer split between its two axes; and
5. uses an exact dynamic program to assign exactly 512 bits across groups.

The positive result is a held-out reconstruction-SSE improvement over giving
every group eight bits. The best-supported pairing is fixed adjacency, not
strongest Pearson correlation.

## Closest primary work

| Work | What it already covers | Difference from the current diagnostic |
| --- | --- | --- |
| Brandt, Transform Coding, CVPR 2010 | PCA, non-uniform scalar quantizers, integer bit allocation between components under one total budget, packed codes, and ANN distance estimation | Allocates per transformed coordinate rather than first naming two-dimensional groups; scientifically it already covers the diagnostic's separable scalar allocation mechanism |
| Park et al., Optimized Transform Coding, BMVC 2014 | Replaces the normalized-variance approximation with component-specific distribution estimates and directly optimizes bit allocation | Uses binned density/error estimates rather than the diagnostic's fitted Lloyd curves; this is an estimator/solver difference, not a new allocation principle |
| Ge et al., OPQ, CVPR 2013 | Optimizes the orthogonal decomposition and PQ codebooks; its parametric method uses PCA and eigenvalue allocation to form balanced subspaces | More expressive than fixed local two-dimensional rotations; it normally keeps equal codebook size per subspace |
| Guo et al., Adaptive Bit Allocation PQ, Neurocomputing 2016 | Applies PCA, groups principal components into PQ subspaces, assigns unequal power-of-two codebook sizes to minimize total quantization distortion, and uses ordinary ADC/SDC | This is the closest high-level precedent. Its subspace quantizer is unrestricted k-means, while the diagnostic uses a product of two scalar Lloyd quantizers and an exact DP |
| Li et al., DSPQ, TCSVT 2018 | Keeps the decomposition fixed, detects distribution differences, moves bits between subspaces, trains unequal-size codebooks, and performs ordinary PQ distance summation | Uses an aggregate-degree/matching-index rule and iterative bit donation rather than empirical curves and exact DP |
| Liu et al., Structure Sensitive Hashing with Adaptive PQ, TCYB 2016 | Uses PCA/eigenvalue-allocation subspaces and assigns different bit counts according to subspace variance | Its primary task is hashing and Hamming-distance approximation, so it is supporting rather than decisive prior work |
| André et al., Quicker ADC, TPAMI 2021 | Implements irregular PQ layouts with mixed 4/5/6/7-bit subquantizers and split SIMD lookup tables | Does not choose bits from empirical group curves, but already establishes that irregular-width packing and lookup are a systems problem with known solutions |
| Sreeramji et al., Quantization Beyond Uniform Bit Allocation, VecDB 2026 | Uses fixed contiguous buckets and greedily reallocates a fixed budget for both PQ and scalar quantization; reports Recall improvements at equal compression | Targets Matryoshka embeddings and an exploratory greedy implementation, but is extremely close to the proposed modern wording |
| Li et al., SAQ, SIGMOD 2026 | PCA-orders dimensions and uses dynamic programming to jointly choose contiguous segment boundaries and one bit width per segment under a total storage budget | SAQ's segment granularity, shared factors, uniform lattice, and fast scan differ from the two-dimensional diagnostic, but the high-level “put more bits on higher-impact coordinate regions” claim is already inside SAQ |

Primary sources:

- [Brandt, *Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions*](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/0557.pdf),
  especially Sections 3.3--3.6;
- [Park et al., *Optimized Transform Coding for Approximate KNN
  Search*](https://www.bmva-archive.org.uk/bmvc/2014/papers/paper001/index.html);
- [Ge et al., *Optimized Product
  Quantization*](https://openaccess.thecvf.com/content_cvpr_2013/html/Ge_Optimized_Product_Quantization_2013_CVPR_paper.html),
  especially Section 3.2.4;
- [Guo et al., *Adaptive Bit Allocation Product
  Quantization*](https://doi.org/10.1016/j.neucom.2015.07.062), Sections
  2.2 and 3--3.3, Eqs. 10--13, and Algorithm 1. The complete primary PDF
  previously supplied to this project had SHA-256
  `c181ee3468c01edf2e02cf193c9aaa88eb92a3a836b3cdc24f4e90150bde11d2`;
- [Li et al., *Distribution Sensitive Product
  Quantization*](https://cic.tju.edu.cn/faculty/huqinghua/pdf/DistributionSensitiveProductQuantization.pdf),
  especially Algorithm 1 and Sections III-B/III-D;
- [Liu et al., *Structure Sensitive Hashing with Adaptive Product
  Quantization*](https://doi.org/10.1109/TCYB.2015.2474742), Section V-B;
- [André et al., *Quicker
  ADC*](https://arxiv.org/abs/1812.09162), Sections 3.1--3.4;
- [Sreeramji et al., *Quantization Beyond Uniform Bit
  Allocation*](https://arxiv.org/abs/2608.19388), Section 3.2; and
- [Li et al., *SAQ*](https://arxiv.org/abs/2509.12086) and its
  [official implementation](https://github.com/howarlii/SAQ).

The project history sometimes calls Guo et al.'s method `ABAPQ`; the paper's
own name and acronym are Adaptive Bit Allocation Product Quantization and
`BAPQ`.

## Why the current method is a direct composition

The complete path can be written without introducing a new primitive:

```text
standard IVF residuals
  + fixed two-dimensional product decomposition
  + independent local orthogonal transforms
  + empirical one-dimensional rate--distortion curves
  + unequal bit allocation under a fixed total budget
  + ordinary separable reconstruction loss.
```

PQ/OPQ cover the residual subspace decomposition and transforms. Brandt and
OTC cover scalar curves and bit allocation. BAPQ and DSPQ cover unequal bit
budgets between PQ subspaces. SAQ itself supplies a dynamic program for
segmentation and bit allocation. The new implementation combines these pieces
at a two-coordinate granularity and solves a small knapsack exactly.

The exact DP is useful artifact engineering and removes optimizer ambiguity,
but there is no new feasible code family, information source, query objective,
or asymptotic result. The strong correlation between group variance and
marginal gain is expected under rate--distortion theory and is explicitly the
motivation of Brandt, BAPQ, adaptive PQ, DSPQ, and SAQ.

## Why the current evidence is not yet an SAQ limitation

The frozen comparison is against uniform eight-bit groups. Production SAQ is
not uniform: it already uses a variance objective and a dynamic program to
move bits between PCA-ordered regions. A gain over uniform allocation can
therefore be entirely explained by behavior SAQ already implements.

The diagnostic also studies only the first 128 coordinates and uses learned
non-uniform scalar centroids after independent two-dimensional rotations. It
does not run the CAQ encoder, preserve the production estimator, or measure
Recall/QPS. Reconstruction improvement alone cannot show that the SAQ
estimator ranks candidates better.

## Static mapping to the current SAQ implementation

The current production representation cannot directly express the diagnostic:

- segment boundaries are multiples of 64 dimensions
  (`saqlib/defines.hpp:16`, `saqlib/quantization/saq_data.hpp:179-184`), not
  two dimensions;
- every dimension in one segment shares one integer bit width
  (`saqlib/quantization/saq_data.hpp:183-191`);
- each positive segment consumes an additional 64 planned factor bits
  (`saqlib/quantization/saq_data.hpp:150-151,184,219-220`), and the stored
  layout allocates one two-float `ExFactor` per vector per segment
  (`saqlib/quantization/cluster_data.hpp:274-291`);
- query preparation, fast scan, and accurate scan iterate over all segments
  (`saqlib/quantization/saq_estimator.hpp:32-46,128-157`); and
- a CAQ segment uses one uniform lattice step determined by its bit width,
  rather than two learned non-uniform scalar codebooks.

Making every two-dimensional pair a segment is not a viable adapter. Besides
violating the 64-coordinate layout, 64 positive segments would require about
512 bytes of `ExFactor` data per vector before payload and would multiply the
segment-loop work. Conversely, replacing SAQ with ordinary variable-bit PQ
would instantiate BAPQ/DSPQ and abandon SAQ's code-adjusted estimator and
one-bit fast stage.

## What SAQ-specific space may remain

The only plausible remaining direction is not “allocate different bits to
different groups.” It is a representation/consumer co-design problem:

1. keep a normal 64-or-more-dimensional SAQ segment and its single per-vector
   rescale/factor pair;
2. allow different coordinates or fixed small groups inside that segment to
   carry different numbers of lower bitplanes;
3. retain one fast bit for every represented coordinate so the existing first
   scan remains meaningful;
4. pack the ragged accurate bits without per-vector plan IDs or per-group
   factors; and
5. decode them with little enough extra branching, shuffling, and table work
   to move the Recall--QPS frontier.

This differs from BAPQ/DSPQ at the system boundary because the difficult part
would be preserving CAQ's shared rescale, coordinate adjustment, and two-stage
bitplane consumer rather than using independent PQ codebooks and ordinary
ADC. It is still under severe prior-work pressure: Quicker ADC already covers
irregular packed PQ kernels, and the 2026 VecDB paper covers modern
variable-bit SQ/PQ. A contribution would have to arise from the coupling to
CAQ/SAQ semantics and a measured systems frontier, not from mixed precision
alone.

The current diagnostic's selected allocations also warn that query work is
not automatically unchanged. If implemented as complete two-dimensional
lookup tables, the selected residual allocations would require 43%--64% more
table entries than 64 uniform 8-bit groups. Exploiting the scalar
factorization reduces that increase to roughly 11%--14%, but then requires
local query rotations and irregular scalar tables. Production SAQ instead
uses bitplane arithmetic, so neither number is a measured SAQ overhead.

## Reviewer-level novelty assessment

| Claim | Assessment |
| --- | --- |
| Unequal bits between two-dimensional groups improve reconstruction | Already known in more general component/subspace forms |
| Variance or empirical distortion predicts where bits help | Already known; the current correlation evidence reinforces rather than changes this theory |
| Local two-dimensional PCA plus scalar quantizers | Restricted transform coding/OPQ |
| Exact DP across 64 fitted curves | Exact implementation of a standard separable resource-allocation problem |
| Better objective for the existing SAQ planner | At most an objective/parameter variation unless it exposes a material estimator or systems limitation |
| Fine-grained mixed precision with unchanged SAQ factors and near-unchanged scan | Potentially SAQ-specific, but no method or evidence exists yet |

A strict SIGMOD/VLDB/ICDE reviewer would currently say that the positive
result compares against an insufficient baseline and rediscovers adaptive bit
allocation. The reviewer would require the best current SAQ plan, BAPQ/DSPQ or
an equivalent variable-bit PQ control, OPQ, matched index bytes, construction
cost, Recall, QPS, and explicit accounting of lookup/packing/factor overhead.

## Smallest justified next action

Do not implement the local-PCA/Lloyd consumer as a proposed method. First
perform a base-only opportunity decomposition on the already restored
PCA/residual state:

1. score the current SAQ planner and its exact 64-dimension segment boundary;
2. compute an oracle that changes only bit widths inside an otherwise fixed
   SAQ segment while retaining one shared factor and the uniform CAQ lattice;
3. compare that oracle with the current planner at exactly matched payload and
   factor bytes; and
4. stop if the remaining reconstruction opportunity is below the existing 5%
   materiality threshold on either natural dataset.

This check should use CAQ-representable curves, not the current local
PCA/Lloyd curves. A positive result would establish only that a representable
SAQ granularity gap exists. It would then justify designing the smallest
mixed-bit shared-factor consumer and comparing against variable-bit PQ. A
negative result would close the direction without query access or production
code changes.

## Claim boundaries

Verified:

- multiple primary works already allocate bits unequally between transformed
  components or PQ subspaces;
- SAQ already performs variance-driven segmentation and bit allocation;
- the current SAQ layout cannot directly encode independent two-dimensional
  learned scalar quantizers; and
- the completed base-only diagnostic is deterministic and positive in
  residual reconstruction.

Inference:

- the current method is a direct composition rather than a standalone
  contribution; and
- shared-factor fine-grained mixed precision is the only visible
  SAQ-specific residual question.

Not established:

- a reconstruction gap against the existing SAQ planner;
- unchanged-estimator compatibility;
- Recall or QPS improvement;
- affordable construction, factor, table, packing, or scan cost; or
- a SIGMOD/VLDB/ICDE-level contribution.

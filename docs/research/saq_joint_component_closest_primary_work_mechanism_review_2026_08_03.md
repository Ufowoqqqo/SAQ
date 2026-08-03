# Closest-primary-work and mechanism review: SAQ joint components 1 and 2

Date: 2026-08-03

## Decision

**Do not implement a joint encoder yet.**  The base-only oracle establishes a
real limitation of the current accurate estimator, but it does not identify a
small implementable mechanism.  The unique passing pair, `192d@6b + 320d@4b`,
contains 512 of 960 dimensions and 2,432 scalar code bits.  It is small only in
segment count: it covers 53.3% of all dimensions and 66.7% of the positive-bit
payload.  Exact replacement would require 2,048 bytes of float data per vector
instead of 304 bytes of code for these two segments, before factor overhead.

The apparent super-additivity of the pair result is a property of the ranking
metric, not evidence that the two encoders are coupled.  SAQ's accurate L2
estimate is an explicit sum of independent segment contributions.  Pairwise
ranking applies a threshold to the sum of their errors, so correcting two
terms together can repair cases that neither correction repairs alone and can
avoid new inversions created by a single correction.  No cross-segment term is
present in the current estimator.

Every direct implementation interpretation is already covered by close work
or changes the frozen system boundary:

- moving bits or boundaries is SAQ/transform-coding plan optimization;
- independently improving both encoders is a direct composition, not a joint
  mechanism;
- learning coupled codebooks is the AQ/CQ family and changes representation,
  encoding, and usually distance evaluation;
- storing radius/distance corrections is distance-encoded PQ and violates
  matched storage unless other payload is removed;
- optimizing a query- or score-distribution loss is estimator-aware
  quantization, including anisotropic VQ and White--Singal, and needs a newly
  justified data-access and claim boundary.

One narrow mechanism question remains open: whether the existing SAQ code
format admits **base-only joint code selection** for the two segments that is
non-separable, uses no extra stored bits or query operations, and improves the
unchanged estimator.  Before code is written, that question needs a static
separability proof or counterexample.  If the objective reduces to
reconstruction error or isotropic unseen-direction mean-squared inner-product
error, it is separable and the direction should close.

Status: `NO_GO_DIRECT_IMPLEMENTATION`; `ONE_STATIC_MECHANISM_QUESTION_OPEN`.

## Evidence being explained

The frozen plan is:

```text
segment       0       1        2       3       4
dimensions   64     192      320     256     128
bits/dim     11       6        4       2       0
code bits   704   1,152    1,280     512       0
```

The joint diagnostic replaced stored production contributions by exact
segment distances.  The unique passing pair was segments 1 and 2:

| fold | production inversion | exact 1+2 | reduction | repaired |
| --- | ---: | ---: | ---: | ---: |
| 0 | 0.005980 | 0.002628 | 0.003353 | 71.10% |
| 1 | 0.005775 | 0.002221 | 0.003554 | 75.57% |

Its reduction exceeds the sum of the two single-segment reductions by about
`0.000558` and `0.000531`.  That observation is reproducible, but the oracle
does not preserve storage, construction cost, or query work.  It also does not
distinguish a coupled mechanism from the fact that the two largest
medium-precision segments contain most of the remaining approximation mass.

## What the current consumer actually computes

For segment `s`, the accurate L2 consumer computes

```text
E_s(q, o) = ||o_s||^2 + ||q_s||^2
            - 2 * rescale_s(o) * <q_s, code_s(o)>.

E(q, o) = sum_s E_s(q, o).
```

`SaqCluEstimator::compAccurateDist` performs the final sum.  Each
`CaqCluEstimator` owns its segment query, lookup table, code, norm, and
per-vector rescale.  Neither the stored representation nor the accurate
consumer contains a segment-1/segment-2 cross term.

Let `e_s(q,o) = E_s(q,o) - T_s(q,o)`, where `T_s` is the exact segment
distance.  For two candidates `a,b`, the estimated ordering is controlled by

```text
Delta E = Delta T + sum_s [e_s(q,a) - e_s(q,b)].
```

An inversion is the sign of `Delta E` disagreeing with the sign of `Delta T`.
The sign threshold is nonlinear.  Consequently:

- correcting segment 1 can move an example across zero in either direction;
- correcting segment 2 can do the same;
- correcting both can cross zero when neither single correction does;
- the pair can introduce fewer new inversions than the sum of two single arms.

This fully permits the observed super-additivity without any statistical
dependence between segment codebooks.  The diagnostic did not retain a
predeclared event-overlap decomposition capable of attributing the excess to
a separate coupling mechanism, and no such attribution should be inferred
post hoc.

## Separability boundary

Under the fixed orthogonal coordinate partition, squared reconstruction loss
is exactly additive:

```text
||o - reconstructed(o)||^2 = sum_s ||o_s - reconstructed_s(o_s)||^2.
```

Therefore, if segment-1 and segment-2 feasible codes and factors remain
independent, minimizing reconstruction error jointly returns the two
independent optima.  There is no joint algorithmic gain to recover.

The same problem appears for unseen-direction inner-product mean-squared error
when the assumed direction covariance is block diagonal, including the
isotropic case.  Cross-segment terms vanish in expectation.  A non-separable
objective requires at least one of:

1. a non-block-diagonal direction/workload covariance;
2. a ranking or top-k loss over sums of segment errors;
3. a coupled feasible codebook or shared per-vector state;
4. a changed estimator that explicitly consumes cross-segment information.

Items 1 and 2 introduce a workload model and need a defensible query-unaware
source for it.  Items 3 and 4 change the representation or query path.  Thus
the oracle result alone does not supply a legal mechanism inside the current
boundary.

## Closest primary work

### SAQ

SAQ is the immediate method and strongest parameter-variation objection.  It
PCA-orders dimensions, partitions them into contiguous segments, and uses a
dynamic program to choose segment lengths and per-dimension bit widths under a
space budget.  Its objective is an additive variance/quantization-error proxy.
It then encodes every segment separately and sums their estimates at query
time.

Coverage: joint boundary/bit allocation and the current segmented consumer.
Not covered: a frozen-plan, ranking-aware joint choice of two existing segment
codes.  Merely moving bits from `192d@6b` to `320d@4b`, merging them, or
changing their boundary is nevertheless a SAQ parameter/plan variant rather
than a new mechanism.

Primary source: [Li et al., SAQ](https://arxiv.org/abs/2509.12086v2).

### Transform coding, PQ grouping, OPQ, and CKM

Brandt's transform-coding ANN method already performs PCA, data-dependent bit
allocation, and scalar quantization.  PQ establishes independent subspace
quantization and shows that grouping affects retrieval.  OPQ and Cartesian
k-means learn a better decomposition/rotation jointly with product codebooks.

Coverage: redistribute representational capacity, change coordinate grouping,
or reduce cross-coordinate dependence.  These are the closest objections to
interpreting the pair oracle as evidence for a new bit-allocation, boundary,
or rotation method.

Primary sources:

- [Brandt, Transform Coding for ANN](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/0557.pdf);
- [Jégou, Douze, and Schmid, Product Quantization](https://inria.hal.science/inria-00514462v2);
- [Ge et al., Optimized Product Quantization](https://openaccess.thecvf.com/content_cvpr_2013/html/Ge_Optimized_Product_Quantization_2013_CVPR_paper.html);
- [Norouzi and Fleet, Cartesian K-Means](https://openaccess.thecvf.com/content_cvpr_2013/html/Norouzi_Cartesian_K-Means_2013_CVPR_paper.html).

### Distance-encoded Product Quantization

Distance-encoded PQ explicitly observes that a cluster index alone is not the
best use of a fixed bit budget for distance estimation.  It reallocates part
of that budget to quantize the point's distance from its selected center and
derives distance-specific estimators.

Coverage: add estimator-relevant scalar information instead of spending all
bits on direction/code identity.  A SAQ proposal that stores an additional
joint radius, correction, or pair residual must compare directly against this
principle and account for which existing bits it removes.

Primary source: [Heo, Lin, and Yoon, Distance Encoded Product Quantization](https://openaccess.thecvf.com/content_cvpr_2014/html/Heo_Distance_Encoded_Product_2014_CVPR_paper.html).

### Additive and Composite Quantization

AQ removes PQ's disjoint-subspace restriction: a vector is represented as a
sum of codewords from full-dimensional, dependent codebooks.  This improves
representational power but makes encoding harder and introduces codeword
cross-products in squared distances.  CQ constrains the sum of cross-dictionary
inner products to be constant so that query evaluation returns to `O(M)` table
lookups rather than `O(M^2)` cross terms.

Coverage: genuinely coupled codebooks and the exact systems tension between
coupling and cheap distance evaluation.  Replacing the two SAQ segments by a
joint VQ, AQ, or CQ block is known machinery and would change the codebook,
encoder, consumer, construction cost, and likely memory layout.  It cannot be
presented as preserving the unchanged SAQ path.

Primary sources:

- [Babenko and Lempitsky, Additive Quantization](https://openaccess.thecvf.com/content_cvpr_2014/html/Babenko_Additive_Quantization_for_2014_CVPR_paper.html);
- [Zhang, Du, and Wang, Composite Quantization](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/01/ICML14-CQ.pdf).

### Estimator- and inner-product-aware quantization

Anisotropic Vector Quantization replaces plain reconstruction loss with a
score-aware loss over a query distribution and derives a tractable anisotropic
weighting under statistical assumptions.  White and Singal formulate adaptive,
unbiased quantizers for preserving inner products with unseen worst-case and
average-case inputs, explicitly contrasting those objectives with mean-squared
reconstruction error.

Coverage: the general claim that the quantizer should optimize downstream
inner-product behavior rather than reconstruction.  Neither paper is the
current SAQ L2 segmented implementation, but they make “use an estimator-aware
objective” prior art rather than a contribution by itself.  A base-pair
ranking loss would need to explain both its SAQ-specific structure and why it
is not a direct workload-specific application of this line.

Primary sources:

- [Guo et al., Anisotropic Vector Quantization](https://proceedings.mlr.press/v119/guo20h.html);
- [White and Singal, Inner Product Aware Quantization](https://arxiv.org/abs/2606.00289).

## Route-by-route assessment

| candidate interpretation | scientific issue | decision |
| --- | --- | --- |
| Reallocate bits or move/merge the boundary | SAQ and transform coding already optimize this family; changes frozen plan | reject |
| Apply a better encoder independently to both segments | direct composition; oracle excess is not evidence of coupling | reject as joint contribution |
| Store exact vectors or a high-rate residual | at least 1,744 extra bytes/vector for this pair | reject |
| Store one joint radius/correction | DE-PQ-like and not matched storage unless bits are removed elsewhere | reject under current boundary |
| Learn a joint VQ/AQ/CQ block | known coupled-codebook family; changes consumer and costs | reject as unchanged-SAQ method |
| Fit benchmark-query ranking loss | violates current query-unaware/data-access boundary | forbidden |
| Fit base-pair ranking/direction loss | potentially legal, but generic estimator-aware prior and non-separable only through a workload model | static review first |
| Jointly choose existing SAQ codes with unchanged bytes/query path | only narrow open mechanism; may be mathematically separable | prove/counterexample first |

## Strict-reviewer objections

A SIGMOD/VLDB/ICDE reviewer would currently object that:

1. “two segments” disguises an oracle over more than half the dimensions and
   two thirds of the coded payload;
2. the positive endpoint is exact float replacement rather than an achievable
   matched-storage arm;
3. super-additive inversion repair follows from a nonlinear sign/rank metric
   and does not demonstrate cross-segment encoder dependence;
4. the result is one GIST base-only cell, not frozen benchmark Recall/QPS;
5. SAQ already jointly chooses segmentation and bits, while AQ/CQ and
   estimator-aware quantization cover the obvious extensions;
6. no construction time, index size, memory, query work, or fair SOTA delta
   exists for a proposed method.

These are claim blockers, not requests for a larger experiment matrix.

## Smallest next action and stop condition

Perform a static two-segment objective audit, without reading queries or
implementing an encoder:

1. write the exact feasible variables exposed by the current segment encoders
   (code and rescale) while keeping the plan and serialized format fixed;
2. prove separability for reconstruction loss and isotropic unseen-direction
   inner-product MSE;
3. identify whether any base-only SAQ estimator-error objective remains
   non-separable without a learned workload covariance or added query work;
4. construct one tiny algebraic counterexample only if such an objective
   exists.

Stop and close the direction if every allowed objective decomposes into one
optimization per segment.  Return to the user before implementation if a
non-separable objective exists, because choosing it changes the scientific
claim and the closest-baseline set.

No code was changed and no experiment or benchmark-query access was performed
for this review.  The preceding diagnostic remains
`PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`; `PERFORMANCE_NOT_YET_MEASURED`.

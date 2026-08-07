# Closest-primary-work review: non-adjacent coordinate pairing

Date: 2026-08-03

## Decision

The current positive result should not be claimed as a new general method for
learning a product-quantization decomposition.  That problem is established
prior work.  The original PQ paper already showed that component grouping can
materially change ANN recall and explicitly proposed automatic grouping.  OPQ
then optimized the space decomposition jointly with quantization codebooks;
its parametric variant performs PCA followed by a combinatorial reordering of
principal components into balanced subspaces.  Cartesian k-means is equivalent
to OPQ's non-parametric solution under matched initialization, and DP-OPQ
subsequently targeted a more optimal combinatorial eigenvalue allocation.

No primary paper found in the targeted search instantiates the exact current
program: use fitted scalar rate--distortion curves to assign a loss to every
unordered coordinate pair and solve a general-graph minimum-weight perfect
matching into two-coordinate, one-byte groups.  This negative search result is
not proof of novelty.  The formulation is best understood as a narrow,
permutation-only specialization of optimized subspace partitioning, with a
different separable loss and an exact solver made possible by group size two.

The result can remain a research lead only under the narrower systems question:

> Can an exactly optimized, loss-aware coordinate pairing obtain a materially
> better Recall--QPS frontier than the closest permutation-only partitioning
> baselines, while avoiding a dense query transform and preserving the existing
> one-byte table-scan consumer?

The completed pilot does not answer that question because it compares with
fixed adjacency and full OPQ, but not with the closest permutation-only OPQ or
DP-OPQ-style partitioning controls.

## Exact method under review

For PCA residual coordinate `i`, let `E_i(k)` be the fitted scalar-quantizer
training SSE with `k` centers.  For every unordered pair `{i,j}`, the arbitrary
and dyadic edge losses are

```text
L_A(i,j) = min E_i(k_i) + E_j(k_j),  k_i k_j <= 256
L_D(i,j) = min E_i(k_i) + E_j(k_j),  k_i,k_j powers of two,
                                            k_i k_j <= 256.
```

The method chooses 64 disjoint pairs covering coordinates `0..127`:

```text
minimize    sum_{ {i,j} in M } L(i,j)
subject to  M is a perfect matching of the 128 coordinates.
```

Each selected pair receives one byte and a Cartesian product of two scalar
codebooks.  The fitted pairing is global and query-unaware.  It adds one small
pair sidecar per index, no per-vector metadata, and no new indirection in the
per-candidate scan; coordinate indirection appears only while constructing the
64 complete 256-entry query tables.

This definition exposes two important claim boundaries:

1. The edge loss is a sum of independent one-dimensional quantization errors.
   It does not learn a joint two-dimensional codebook and does not exploit
   correlation between the paired coordinates.  It pairs coordinates with
   complementary rate demands under a shared one-byte budget.
2. The current codebook family is a strict subset of ordinary 2D PQ's
   unrestricted 256-centroid codebook.  Its potential advantage is therefore
   construction and query-path structure, not greater representational power.

## Closest primary work

### 1. Product Quantization for Nearest Neighbor Search

Jégou, Douze, and Schmid introduced PQ as independent quantization of a
Cartesian product of low-dimensional subspaces.  Their Section 5.3 directly
tests natural, random, and structure-aware component groupings on SIFT and
GIST.  The grouping changes recall substantially; on GIST, their structured
order raises Recall@100 from 0.338 to 0.652.  They explicitly state that an
automatic grouping method could improve the result and suggest minimum
sum-squared-residue co-clustering.

Coverage of the current idea:

- establishes that coordinate grouping is a consequential PQ design choice;
- establishes lookup-table ANN evaluation after grouping;
- anticipates data-driven automatic grouping.

What it does not provide is the current pairwise scalar rate--distortion loss,
the exact perfect-matching reduction, or a transform-free SAQ-compatible
consumer comparison.

Primary source: [Jégou, Douze, and Schmid, TPAMI 2011](https://inria.hal.science/inria-00514462v2).

### 2. Optimized Product Quantization

Ge, He, Ke, and Sun optimize PQ jointly over the sub-codebooks and an
orthogonal matrix representing the space decomposition.  The paper states
explicitly that any coordinate reordering is representable by that orthogonal
matrix, so its search space contains every pairing/permutation used here.

The parametric method is especially close.  Section 3.2.4, "Eigenvalue
Allocation," first aligns data by PCA and then applies a greedy balanced
partition: sorted principal components are assigned to fixed-capacity
subspace buckets to balance products of eigenvalues.  The paper calls this
allocation into buckets or subspaces, not a "grouping rule."  Thus it already
learns which non-adjacent PCA coordinates should share a subspace.  Its
non-parametric method learns a general dense rotation and codebooks and is
reported as equivalent to Cartesian k-means under the same initialization.

Coverage of the current idea:

- optimizes subspace decomposition for quantization distortion;
- includes coordinate permutations as a restricted case;
- directly treats PCA-coordinate allocation as a combinatorial problem;
- evaluates distortion and ANN accuracy on SIFT1M and GIST1M.

The current formulation differs by restricting the transform to a global
permutation, fixing every group to two coordinates, restricting each 2D
codebook to two scalar codebooks, replacing the Gaussian eigenvalue proxy with
empirical scalar curves, and solving that restricted partition exactly.
Those restrictions are useful for a low-overhead consumer, but they make the
method a specialization rather than a broader decomposition model.

Primary source: [Ge et al., *Optimized Product Quantization*, Section 3.2.4,
PDF page 5 / proceedings page 2950 (CVPR
2013)](https://openaccess.thecvf.com/content_cvpr_2013/papers/Ge_Optimized_Product_Quantization_2013_CVPR_paper.pdf).

### 3. Cartesian K-Means

Norouzi and Fleet learn a compositional Cartesian codebook and a rotation for
large-scale ANN.  OPQ's journal version identifies its non-parametric solution
as equivalent to Cartesian k-means under matched initialization.  CKM therefore
independently covers the broad claim that the transform/decomposition and
product codebooks should be learned rather than fixed.

It is more expressive than a coordinate permutation and requires a learned
transform.  It does not give the present exact pairing reduction or the
factorized scalar consumer.

Primary source: [Norouzi and Fleet, CVPR 2013](https://openaccess.thecvf.com/content_cvpr_2013/html/Norouzi_Cartesian_K-Means_2013_CVPR_paper.html).

### 4. Dynamic-programming optimized PQ

Cai, Ji, and Li explicitly target the combinatorial weakness of OPQ's greedy
eigenvalue allocation.  They formulate subspace partition as a graph-based
optimization problem and use dynamic programming to improve balanced PCA
eigenvalue allocation, with ANN evaluation on SIFT1B and integration with an
inverted multi-index.

This is the closest precedent for the claim that a stronger combinatorial
solver improves PQ subspace partitioning.  Its optimized quantity is a
Gaussian/eigenvalue balance and its DP structure is not the current arbitrary
pair graph with empirical scalar-quantizer losses.  Nevertheless, a paper
reviewer is likely to view exact matching as another solver/objective variant
in this established line unless it wins a direct controlled comparison.

Primary source: [Cai, Ji, and Li, Neurocomputing 2016](https://www.sciencedirect.com/science/article/pii/S0925231216306324).

### 5. Transform coding for ANN

Brandt applies PCA, data-driven bit allocation, and non-uniform scalar
quantization to ANN.  This work covers the other half of the current mechanism:
different PCA coordinates have different rate demands, and learned scalar
quantizers and bit allocation can exploit them.

It allocates bits per coordinate rather than pairing coordinates under one-byte
table words.  It therefore does not solve grouping, but it prevents a novelty
claim based only on learned scalar rate allocation after PCA.

Primary source: [Brandt, CVPR 2010](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/0557.pdf).

### 6. SAQ

SAQ is the immediate system context.  It PCA-aligns vectors, defines dimension
segments as continuous coordinate intervals, and jointly selects segment
boundaries and bit widths by dynamic programming to minimize quantization
error.  It also supplies code adjustment and the optimized ANN estimator.

The non-adjacent method changes the allowed grouping topology from continuous
segments/fixed adjacency to arbitrary pairs and uses a separate scalar-product
consumer in the current experiment.  A reviewer can reasonably characterize
this as relaxing a segmentation constraint in SAQ.  To become more than a
parameter or artifact variation, it must show why non-adjacent pairing exposes
an SAQ-specific limitation, how it composes with the unchanged SAQ estimator,
and whether its benefit survives the closest decomposition baselines.

Primary source: [Li et al., PACMMOD/SIGMOD 2025](https://dl.acm.org/doi/10.1145/3769824).

### 7. Closely adjacent permutation work

Two additional papers narrow the wording of any algorithmic novelty claim:

- LOPQ learns a separate rotation and space decomposition per coarse cell.  It
  is more adaptive but carries local model state; the present method is one
  global query-unaware pairing.  Primary source:
  [Kalantidis and Avrithis, CVPR 2014](https://openaccess.thecvf.com/content_cvpr_2014/html/Kalantidis_Locally_Optimized_Product_2014_CVPR_paper.html).
- ITLUMM restricts an OPQ rotation to a permutation for lookup-based matrix
  multiplication and solves a maximum-weight bipartite assignment to map
  original dimensions to rotated positions.  It then forms contiguous equal
  chunks.  This is not the current general-graph perfect pairing: its vertices
  are input/output positions and its weights approximate a dense OPQ matrix,
  rather than measuring pair quantization loss.  It nevertheless shows that
  "permutation-only OPQ plus matching" is not new wording by itself.  Primary
  source: [McCarter and Dronen, 2022 preprint](https://calvinmccarter.com/papers/snn2022-lookups.pdf).

Permute, Quantize, and Fine-tune also searches permutations that make vector
quantization easier, but for function-preserving neural-network weight
compression rather than ANN.  It is adjacent evidence, not a direct ANN
baseline.  Primary source:
[Martinez et al., CVPR 2021](https://openaccess.thecvf.com/content/CVPR2021/html/Martinez_Permute_Quantize_and_Fine-Tune_Efficient_Compression_of_Neural_Networks_CVPR_2021_paper.html).

## Direct-composition and novelty assessment

The high-level method can be derived from prior work by the following
restrictions:

```text
OPQ optimized decomposition
  -> fix the already learned PCA basis
  -> restrict the orthogonal transform to coordinate permutations
  -> fix 64 subspaces of dimension two
  -> restrict each 2D codebook to a product of two scalar codebooks
  -> put one byte of capacity on every pair
  -> use fitted scalar SSE rather than the eigenvalue-balance proxy
  -> exploit additive pair losses and solve the resulting partition exactly
     by minimum-weight perfect matching.
```

The final exact-solver observation may be absent from the reviewed ANN papers,
but the scientific mechanism--learn a better coordinate partition to reduce
quantization distortion--is not absent.  On current evidence:

- **General novelty:** no.
- **Narrow algorithmic novelty:** plausible but unverified; exact optimality
  within this restricted consumer family may support a lemma or component.
- **SAQ-specific novelty:** not established.  The current pilot is a separate
  scalar-product consumer and has not shown an improvement to the unchanged
  SAQ estimator.
- **Systems contribution:** plausible but unverified.  A static permutation
  can avoid a dense query transform and preserve the byte scan, but that is a
  natural consequence of the restriction and needs fair end-to-end evidence.
- **Mixed-radix contribution:** contradicted by the pilot.  A-flex versus
  D-on-A changes Recall by at most 0.00057 with mixed signs.

The strongest defensible description today is:

> an exact, empirical rate--distortion pairing algorithm for a restricted
> transform-free scalar-product quantizer, with promising pilot Recall/QPS.

That is not yet a SIGMOD/VLDB/ICDE-level contribution.

## Required discriminating baselines

Do not expand to a full dataset/budget matrix before the following small,
frozen comparison:

1. **Adjacent pairing:** already measured; establishes the total pairing gain.
2. **Random pairings:** several predeclared seeds; shows that the gain is from
   the objective rather than merely breaking PCA adjacency.
3. **OPQ-P/EA pairing:** PCA plus Ge et al.'s greedy Eigenvalue Allocation,
   restricted to 64 two-coordinate buckets and evaluated through the identical
   scalar consumer.  This is the decisive closest baseline.
4. **DP-OPQ-style partition:** reproduce the applicable primary algorithm or
   document precisely why its constraints do not instantiate 64 pairs.  Do not
   label an invented approximation as DP-OPQ.
5. **Full OPQ:** retain the existing control, but separate transform, query
   table construction, candidate scan, construction time, memory, and index
   bytes under matched compiler/thread conditions.
6. **Ordinary 2D PQ on the selected pairs:** measures the accuracy sacrificed
   by restricting each pair to two scalar codebooks.  This need not be an
   exhaustive all-edge pairing search for the first gate.

The same fixed learn rows, PCA residuals, code bytes, IVF assignments,
candidate schedules, query set, ground truth, threads, and repetitions must be
used.  Report Recall/QPS frontiers rather than one selected point.

## Falsifiable continuation rule

Continue only if the matching arm beats the best permutation-only primary-work
baseline on both natural datasets by a predeclared material Recall amount at
matched QPS, or by a material QPS amount at matched Recall, while preserving
the claimed no-per-vector-state and byte-scan properties.  Also require the
result to remain after accounting for PCA/transform time, table-build time,
construction cost, peak memory, and serialized bytes.

If it only beats adjacency/random pairing, or merely matches OPQ-P/DP-OPQ-style
partitioning, preserve the implementation as useful artifact engineering and
close it as a standalone research direction.  If it wins this gate, the next
claim should remain narrow: exact loss-aware pairing for a low-overhead
consumer, not a new general theory of product quantization and not a rescue of
mixed radix.

## Search boundary and uncertainty

The review inspected primary text for PQ, transform coding, OPQ, CKM, DP-OPQ,
LOPQ, SAQ, ITLUMM, and PQF, and ran targeted searches combining product
quantization, coordinate/dimension grouping, permutation, scalar quantization,
and maximum-weight/perfect matching.  No exact ANN instance of the current
general-graph pair-loss formulation was found.  Citation chasing and searches
cannot establish absence; a formal novelty claim would still require a broader
systematic search and, ideally, author/code verification for DP-OPQ.

# Attempt 4: Arbitrary-Cardinality Quantization Review and Formulation Gate

Date: 2026-07-13
Decision: **CONDITIONAL GO FOR OFFLINE FEASIBILITY ONLY**

## 1. Research question

Suppose an ANN database stores one fixed `B_g`-bit word for a small group of
scalar factors. Standard scalar bit allocation restricts factor `j` to
`K_j=2^{b_j}` levels. This study asks:

> Can a Cartesian product of arbitrary integer cardinalities use the same
> fixed `B_g`-bit address more effectively, while retaining one random-access
> word and one query-table lookup per group?

The first-stage question is deliberately narrower than a new SAQ method. It
tests a coding opportunity before changing CAQ, SAQ segmentation, the index
format, or search.

## 2. Correct budget semantics

The motivating `3+3` versus `4+2` example uses a **sum of center counts**. That
is not a fixed-length coding budget. Two scalar symbols with cardinalities
`K_1` and `K_2` have `K_1 K_2` possible joint states, so a fixed address needs

```text
B_g = ceil(log2(K_1 K_2)) bits.
```

Thus `(3,3)` has nine joint states and needs four fixed bits. `(4,2)` has eight
states and needs three fixed bits. They cannot be presented as equal-rate
fixed-length alternatives.

The corrected equal-rate example uses one four-bit word:

```text
capacity S = 2^4 = 16
arbitrary cardinalities: (3,5), product 15
dyadic alternatives: (4,4), (2,8), (8,2), (1,16), (16,1)
```

## 3. Fixed-rate mixed-radix formulation

For scalar factor `j`, let `E_j(K)` be the globally minimum expected squared
reconstruction error achievable with at most `K` scalar centroids. For a
group of `r` factors, solve

```text
minimize     sum_{j=1}^r E_j(K_j)
subject to   product_{j=1}^r K_j <= S = 2^B_g,
             K_j is a positive integer.
```

The dyadic baseline adds `K_j=2^{b_j}`, where each `b_j` is a nonnegative
integer. Its feasible set is a subset of the arbitrary-cardinality set, hence

```text
D*_arbitrary <= D*_dyadic
```

for this exact factorized reconstruction objective. The statement is only a
feasible-set guarantee. It does not imply strict improvement on natural data,
and it gives no guarantee for ANN ranking, recall, distance-estimator tails,
or throughput.

Given scalar labels `z_j in {0,...,K_j-1}`, encode one mixed-radix address as

```text
u = z_1 + K_1 z_2 + K_1 K_2 z_3 + ... .
```

At query time, a `2^B_g`-entry table can store

```text
T_q[u] = sum_j (q_j - c_{j,z_j(u)})^2.
```

Unused addresses are invalid entries. A database scan still loads one fixed
word and performs one table lookup per group. The representation therefore
preserves fixed addressing at the cost of a larger group table and possible
unused states.

## 4. Running examples

### 4.1 Why Huffman does not make nine equiprobable states fit in three bits

For two independent uniform three-symbol factors, a binary Huffman code for
one factor has lengths `{1,2,2}` and expected length `5/3` bits. Encoding both
factors separately costs `10/3` bits on average, while their nine equiprobable
joint states still require four bits in the worst case. This is an expected
rate result, not a three-bit fixed-address representation.

### 4.2 Frozen strict-improvement witness

Let

```text
x_1 be uniform on {-1,0,1}
x_2 be uniform on {-2,-1,0,1,2}
B_g=4.
```

The `(3,5)` scalar product represents all 15 joint atoms exactly, so its
distortion is zero. Any dyadic allocation with product at most 16 must lose a
level on at least one factor. The best is `(4,4)`: the first factor is exact,
while one adjacent pair of the second factor shares a centroid. The second
factor's total squared error over its five equiprobable atoms is `0.5/5=0.1`.

An unrestricted 16-codeword two-dimensional VQ also has zero distortion. This
last comparison matters: arbitrary-cardinality factorization matches the
oracle on this constructed source, but unrestricted block VQ weakly dominates
factorized products in general.

## 5. Closest prior work and novelty boundary

### Entropy-constrained quantization

Chou, Lookabaugh, and Gray formulate entropy-constrained vector quantization
as a distortion-rate Lagrangian paired with variable-rate lossless coding.
Muresan and Effros give globally optimal fixed-rate and entropy-constrained
scalar quantizers for discrete sources through histogram segmentation. These
works already cover non-power-of-two alphabets and expected-rate coding.
Huffman coding is therefore not the novelty.

### ANN transform and product coding

Brandt's transform coder already combines PCA, data-driven integer bit
allocation, per-coordinate minimum-distortion scalar quantizers, packed bytes,
and 256-entry query lookup tables for ANN. Adaptive Bit Allocation Product
Quantization allocates unequal bit counts/codebook sizes to product subspaces.
Quicker ADC supports irregular PQ granularities and studies the SIMD cost of
non-byte-aligned lookup schemes. Therefore neither unequal allocation nor
packing several factors into a lookup word is new.

### Arbitrary level products and dense fixed-rate axes

Finite Scalar Quantization constructs an implicit codebook as a product of
small scalar level sets whose cardinalities need not be identical powers of
two. More recent fractional-rate work, including Q-Palette and FibQuant,
explicitly targets dense rate choices; FibQuant also emphasizes fixed-address
random access and proves an unrestricted vector-code advantage over scalar
products for its canonical source. These works sharply limit any claim based
only on arbitrary cardinalities or a dense rate axis.

## 6. What could still be research-relevant

A viable ANN contribution would have to establish all of the following:

1. Natural ANN residual or transformed-coordinate groups repeatedly exhibit a
   material dyadic-cardinality loss at fixed stored bytes.
2. The gain survives comparison with trained block/PQ codebooks of the same
   capacity, or offers a clear training/metadata/table advantage that explains
   why the factorized restriction is worthwhile.
3. Mixed-radix table construction, unused entries, codebook metadata, encoding
   work, and scan kernels are accounted for, not hidden behind MSE.
4. Lower reconstruction or distance-estimation error changes a frozen
   recall-throughput frontier without query-trained allocation.
5. The final mechanism is more than classical transform coding plus a known
   mixed-radix index.

At present none of these statements is established. The stage is therefore a
falsification study, not a method implementation.

## 7. Huffman path: deferred

For symbol probabilities `p_{j,k}` and binary code lengths `l_{j,k}`, an
entropy-constrained scalar model optimizes a distortion-rate objective such as

```text
D + lambda R,
R = sum_{j,k} p_{j,k} l_{j,k},
sum_k 2^{-l_{j,k}} <= 1.
```

This may reduce average bytes only when labels are sufficiently nonuniform.
It introduces variable offsets, restart points or block metadata, branchier
decoding, and a distinction between average and worst-case scan work. Since
fixed-address ANN scanning is the immediate systems constraint, Huffman is not
implemented in A4-0; only its theoretical expected length is measured.

## 8. First-stage protocol and stop conditions

A4-0 uses only a frozen synthetic source. It validates exact integer-`K`
scalar curves, dyadic/arbitrary allocation, mixed-radix bijection, lookup-table
distance parity, and entropy accounting. It changes no SAQ source.

The direction stops before natural-data work if the instrument does not
recover the predeclared witness exactly. Passing the witness permits only a
separate base-data-only protocol. It is not evidence of novelty or ANN value.

## 9. Reference complexity

With `H` weighted support points, exact scalar distortion curves through
`K_max` use `O(K_max H^2)` time and `O(K_max H)` DP memory per dimension in the
reference implementation. Group allocation uses `O(r S K_max)` time and
`O(r S)` frontier memory including stored cardinality tuples. A query table
uses `O(S r)` construction work and
`O(S)` entries; a scan uses one lookup per stored group word.

Production work could use histogram approximation, Monge/divide-and-conquer
optimization, or hardware-specific tables, but those are not first-stage
claims.

## 10. Primary sources

The machine-readable ledger is
`docs/saq_attempt4_arbitrary_cardinality_sources_2026_07_13.json`.

- P. A. Chou, T. Lookabaugh, and R. M. Gray. "Entropy-Constrained Vector
  Quantization." IEEE TASSP, 1989. DOI: 10.1109/29.17498.
- D. Muresan and M. Effros. "Quantization as Histogram Segmentation: Globally
  Optimal Scalar Quantizer Design in Network Systems." DCC, 2002.
- J. Brandt. "Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions." CVPR, 2010.
- Q.-Z. Guo et al. "Adaptive Bit Allocation Product Quantization."
  Neurocomputing, 2016.
- F. Andre, A.-M. Kermarrec, and N. Le Scouarnec. "Quicker ADC." TPAMI, 2021.
- F. Mentzer et al. "Finite Scalar Quantization: VQ-VAE Made Simple." ICLR,
  2024.
- D. Lee and H. O. Song. "Q-Palette." 2025.
- N. Lee and Y. Kim. "FibQuant." 2026.

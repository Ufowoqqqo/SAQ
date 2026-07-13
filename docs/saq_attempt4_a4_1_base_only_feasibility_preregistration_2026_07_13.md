# Attempt 4 A4-1 Base-Only Feasibility Preregistration

Date frozen: 2026-07-13

Stage: A4-1P

Status: **FROZEN_NOT_AUTHORIZED**

Parent evidence: A4-0 `PASS_INSTRUMENT_ONLY` at commit `20bc411`

## 1. Stage boundary

This document freezes a bounded real-base-data falsification gate before any
natural-data adapter, optimized solver, block-VQ trainer, or A4-1 result is
implemented or run. Writing and committing it does **not** authorize:

- opening any base, centroid, cluster-id, query, ground-truth, index, or prior
  result artifact;
- implementing or executing the A4-1 runner;
- changing SAQ, CAQ, the index format, the estimator, or a scan kernel; or
- making an ANN, recall, throughput, SAQ-specific, or novelty claim.

There are two later authorization checkpoints. First, the user may authorize
synthetic-only runner implementation, parity review, and same-shape cost
projection. Only after those artifacts are committed and reviewed may the
user separately authorize the first base read and registered gate. The
maximum positive A4-1 outcome is permission to write a separate systems/ANN
preregistration; it is not permission to perform that evaluation.

The machine-readable input and hypothesis contracts are:

- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`;
- `docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json`.

## 2. Research question and falsifiable claim

For a fixed random-access word containing a two-coordinate reconstruction
label, does restricting both scalar cardinalities to powers of two cause a
material and repeatable held-out reconstruction loss on natural ANN residuals?

For group `g`, word width `B_g`, and `S=2^B_g`, compare:

```text
dyadic_word:    K_1,K_2 in {1,2,4,...}, K_1 K_2 <= S
arbitrary_word: K_1,K_2 positive integers, K_1 K_2 <= S
block_vq:       S unrestricted two-dimensional reconstruction vectors
```

The narrow claim tested by A4-1 is:

> At the same fixed word and database payload, arbitrary-cardinality scalar
> products remove at least 5% of held-out dyadic reconstruction error and at
> least half of the measured dyadic-to-trained-block-VQ opportunity, across
> both frozen datasets and both frozen word widths, while producing a
> statistically positive improvement in a disjoint base-pair distance proxy.

The null is that the strict synthetic feasible-set inclusion is inactive or
too small on natural residuals, is concentrated in a few coordinate groups,
does not generalize beyond fitting rows, fails against a strong same-capacity
block codebook, or worsens distance estimation. Any such result closes this
bounded direction rather than triggering a rescue sweep.

The 5% threshold is a screening minimum effect, not a theorem. A new
heterogeneous-radix representation needs radix metadata, a new encoder, and a
new scan kernel; a sub-5% reconstruction effect is not large enough to justify
that systems work at this stage. The 50% threshold requires the factorized
change to recover a majority of the opportunity exposed by the stronger
unrestricted two-dimensional codebook. Descriptive 2% and 10% rows will be
reported, but neither can replace the registered 5% decision.

## 3. Closest-work and claim boundary

The primary-source review in
`docs/saq_attempt4_arbitrary_cardinality_related_work_and_gate_2026_07_13.md`
already establishes that the primitives are known:

- globally optimal scalar quantization and non-power-of-two alphabets predate
  this study;
- transform coding already combines PCA, learned scalar quantizers, integer
  bit allocation, packing, and ANN lookup tables;
- adaptive bit-allocation PQ and Quicker ADC cover unequal or irregular
  sub-codebook widths and their scan costs;
- FSQ, Q-Palette, and FibQuant further preclude novelty claims based on dense
  rate choices, arbitrary level products, or fixed-address mixed radix alone.

Therefore A4-1 is only a data-level feasibility screen for a **word-local
fixed-lookup constraint**. It includes a globally packed dyadic transform-code
control so that a reviewer can see whether any gain is merely local word
fragmentation. That control has a different scan interface and is attribution
evidence, not a substitute primary arm. Even a complete pass does not show
that classical transform coding plus mixed radix is publishable.

## 4. Frozen read boundary and provenance

Only six scientific artifacts are admissible: PCA-space base vectors,
PCA-space IVF centroids, and one-column IVF assignments for each of two
datasets. Expected shapes, byte sizes, relative names, and SHA-256 digests are
copied from the previously committed provenance object identified in the
input contract. Runtime roots only locate those content-identified files. No
artifact bytes were opened while writing this preregistration.

| Dataset | Rows x dimensions | IVF cells | Allowed artifacts |
| --- | ---: | ---: | --- |
| `gist_sample50k_k512` | 50,000 x 960 | 512 | `base_pca`, `centroid_512_pca`, `cluster_id_512` |
| `cifar60k_k512` | 60,000 x 512 | 512 | `base_pca`, `centroid_512_pca`, `cluster_id_512` |

The runner must hash and shape-check all six files before emitting any fitted
or scientific output. It must record every scientific input and generated
output path it opens. Queries, ground truth, raw-base alternatives, variance
vectors, PCA matrices, serialized indexes, prior A4 results, and outputs from
other research branches are forbidden. Opening a forbidden artifact makes
the run `ARTIFACT_INVALID`; it is not a scientific result.

No dataset, `K`, representation, sample size, group, rate, or seed may be added
after an outcome is observed.

## 5. Frozen residual view and coordinate panel

For base row `x_v` assigned to IVF cell `c(v)`, construct the residual with one
binary32 subtraction per coordinate:

```text
r_v[j] = float32(x_v_pca[j] - centroid_pca[c(v),j]).
```

Interpret those finite binary32 residual values exactly for the scalar fitting
objective in Section 7.1. Promote them to binary64 only for the declared
runtime-facing reconstruction, block-training, and scoring paths. There is no
new PCA fit, rotation, normalization, whitening, clipping, or data-dependent
coordinate permutation.

The inherited PCA view, IVF centroids, and assignments were constructed from
the full base collections before A4-1, so they are shared fixed representation
inputs rather than models refit inside the 8,192-row A4-1 split. Consequently,
the held-out claim is conditional on that pre-existing view; it tests
generalization of the new quantizers, not end-to-end PCA or IVF training
generalization. Every arm uses the identical inherited view.

Use exactly `G=64` two-coordinate groups (`r=2`) in each dataset. Let
`P=D/2`. For `h=0,...,63`, select pair index and coordinates

```text
p_h = floor((2h+1) P / 128),
group h = (2 p_h, 2 p_h + 1).
```

This value-independent midpoint rule covers the full frozen PCA order without
choosing groups from distortion outcomes. The exact coordinate lists are
materialized in the input contract. Sixty-four groups give a 128-coordinate
diagnostic panel and common ANN-scale fixed payloads:

```text
B_g=4:  64 four-bit words = 256 bits = 32 bytes per panel vector
B_g=8:  64 eight-bit words = 512 bits = 64 bytes per panel vector
```

`r=2` is the smallest nontrivial Cartesian group and directly generalizes the
A4-0 witness. `B_g in {4,8}` tests one nibble and one byte without a rate sweep.
The panel is not a full-vector ANN representation and must not be described as
one.

These rates, the midpoint panel, `r=2`, and its 32/64-byte sizes define the
scope of this falsification protocol; they are not method parameters selected
from base outcomes. No shifted pairing or alternate panel is run as a
sensitivity rescue, so either outcome is limited to this exact panel. The
decision threshold has predeclared descriptive 2%/10% rows, block-control
adequacy is exposed by the complete eight-start curve, and the capped global
control makes the per-scalar `K<=256` boundary explicit. A later method claim
would require a new preregistration for any grouping or rate parameter.

## 6. Frozen fit, held-out, and pair inventories

Use exactly 8,192 fitting rows and 8,192 held-out rows per dataset. At the
largest code capacity this is an average 32:1 fitting-row-to-code-capacity
ratio; it does not guarantee 32 assigned rows for every learned codeword.
Equal held-out size gives a disjoint codec-evaluation sample without
introducing a validation split or a tuning loop.

Serialize the selection key as UTF-8:

```text
{protocol_version}|{dataset_id}|{cell_id}|{vector_id}
```

with no braces in the expanded bytes and no terminating newline. For example:

```text
saq-attempt4-a4-1-20260713-schema2|gist_sample50k_k512|0|17
```

Compute SHA-256. Within each IVF cell, sort by `(raw digest bytes, vector_id)`.
Cell and vector ids are zero-based canonical decimal integers with no leading
zeros. Even local ranks form the fit pool and odd local ranks form the
held-out pool. This makes the pools disjoint before quota selection.

For each pool independently, first reserve its two lowest-ranked rows in every
cell. Allocate the remaining 7,168 rows by capacity-proportional largest
remainder over the still-unselected pool rows:

```text
remaining capacity_c = pool_cell_count_c - 2
extra quota_c = floor(7168 * remaining capacity_c /
                      sum_c remaining capacity_c)
remainder order = descending exact integer remainder numerator,
                  then ascending cell id
final quota_c = 2 + extra quota_c (+ one if selected by remainder order)
```

Take the lowest-ranked rows in each pool up to its quota. The preflight
requires all 512 cell ids to be valid, every cell to have at least four base
rows, both pools to contain at least 8,192 rows, and every final split to cover
all 512 cells with at least two rows. This minimum-two rule makes both cell
coverage and at least one held-out pair per cell structural rather than
outcome-dependent. A violation is `ARTIFACT_INVALID`; the sample rule may not
be replaced.

Within each cell, sort selected held-out rows by the same key and pair
consecutive ranks without reuse: `(0,1), (2,3), ...`; leave an odd final row
unpaired. The lower rank is the stored side and the next rank is the
query-like side. These are base residual pairs, not benchmark queries.

## 7. Frozen fitting and encoder arms

All model selection uses fitting reconstruction SSE only. Held-out rows and
base pairs are evaluation-only and may not select a cardinality, codebook,
group, threshold, or restart.

### 7.1 Scalar curves

For every selected coordinate, fit the globally minimum empirical 1D L2
quantizer for every `K=1,...,256` on all 8,192 fitting residuals. The future
runner must use a compiled exact Monge/SMAWK, divide-and-conquer, or equivalent
exact dynamic program. Its scientific objective is mathematical squared error
on the finite binary32 inputs, not a floating-point prefix-sum surrogate.

Canonicalize either signed zero to binary32 `+0.0`; this is the only two-to-one
input mapping. Every normal and subnormal finite binary32 value is then decoded
exactly as `x_i=n_i*2^-149` for a signed arbitrary-precision integer `n_i`.
Aggregate equal `n_i` values into positive integer weights and sort by exact
numeric value, then by the lowest vector id represented by a support point.
Let `H_distinct` be the resulting support size. For a contiguous interval form
arbitrary-precision integers

```text
W = sum_i w_i
A = sum_i w_i n_i
C = sum_i w_i n_i^2
SSE = ((W C - A^2) / W) * 2^-298.
```

`W C-A^2` must be evaluated as an exact nonnegative integer; there is no
`max(0,...)` repair. DP states are exact rational sums of interval costs.
Represent each rational canonically with a nonnegative numerator, positive
denominator, and greatest common divisor one; compare candidates by exact
arbitrary-precision cross multiplication. Choose the earliest predecessor
only on mathematical equality.

The weighted one-dimensional squared-error interval-cost matrix on sorted
points has the Monge/quadrangle property. Adding the preceding DP-row value
preserves total monotonicity, so Monge/SMAWK or divide-and-conquer acceleration
is valid when, and only when, all candidate ordering decisions use the exact
rational semantics above. No histogram, binning, Lloyd approximation,
quantile sketch, support subsample, binary64 ordering, or post-hoc solver
switch is allowed.

The curve uses an **at-most-`K`** convention. For `K<=H_distinct`, return the
minimum over one through `K` nonempty contiguous intervals, breaking an exact
objective tie in favor of more nonempty intervals and then applying the
earliest-predecessor rule recursively. For `K>H_distinct`, copy the
`H_distinct` solution, report effective cardinality `H_distinct`, and create no
duplicate labels. Allocation nevertheless charges and addresses the requested
nominal `K`; selecting a nominal `K>H_distinct` therefore makes the nominal
alphabet unreachable and returns `NO_GO_REPRESENTATION` before held-out
scoring.

For every cardinality, persist the chosen partitions and exact curve value as
`(numerator, denominator, binary_grid_exponent=-298)`. Independently replay
the chosen intervals in exact rational arithmetic. Also record exact-comparison
and exact-tie counts and check that returned predecessor indices are
nondecreasing. Replay and monotonicity are implementation diagnostics, not
substitutes for the exact-arithmetic Monge contract. Any negative exact
interval numerator, unresolved comparison, replay mismatch, or monotonicity
violation returns `IMPLEMENTATION_INVALID` before held-out scoring.

Before any base read, an independent exhaustive `O(KH^2)` exact-rational
reference must agree with the optimized implementation on exhaustive tiny
supports, signed zero, normal and subnormal values, duplicate values, unequal
weights, all partitions, effective cardinalities, exact curves, exact means,
and ties. The existing A4-0 reference and all A4-0 tests are an additional
compatibility check, not the authority for an ambiguous floating-point
comparison. The randomized exact-reference suite is frozen at 256 cases from
`PCG64(20260713)`: support length 1 through 12, integer support values in
`[-8,8]`, integer weights in `[1,5]`, and every
`K=1,...,min(8,H_distinct)`. For case id `t=0,...,255`, use input length
`1+(t mod 12)`, then call NumPy `integers(-8,9)` for values and
`integers(1,6)` for weights from the single generator stream. Canonical JSON
from that suite must be committed with the synthetic-only implementation
review.

Both product allocators and the global dyadic control sum and compare these
exact rational coordinate curves without first converting any coordinate to
binary64. A selected scalar centroid is the exact interval mean
`(A/W)*2^-149`. Round that rational directly, with round-to-nearest
ties-to-even and no intermediate floating conversion, to binary64 for the
block-VQ start-0 fitting control and independently to binary32 for database
encoding and every held-out metric. Thus all runtime-facing arms use identical
centroid precision, while allocation remains on the predeclared exact
empirical fitting objective. Report the exact pre-serialization fitting SSE,
the binary64 start-0 replay where applicable, and binary32-replayed fitting
SSE.
Selected scalar centroids must remain strictly increasing after binary32
serialization. A collision makes the declared nominal cardinality unreachable
and returns `NO_GO_REPRESENTATION`; it may not be repaired by changing
precision or cardinality after held-out access.

### 7.2 `dyadic_word`

For each group and rate, solve the exact product-capacity problem with
`K_j in {1,2,4,...,S}`. Minimize fitting SSE; ties choose larger used-state
product, then lexicographically smaller `(K_1,K_2)`. Nominal addresses at or
above `K_1 K_2` are invalid even though their bits fit in the paid word.

### 7.3 `arbitrary_word`

Use the identical scalar curves, group, rate, and tie rule, but allow every
positive integer `K_j<=S`. Encode labels as

```text
u = z_1 + K_1 z_2,  0 <= u < K_1 K_2 <= S.
```

For both product arms, unused addresses remain invalid and are filled with
positive infinity in the expanded `S`-entry lookup table. They are still
counted in table bytes.

### 7.4 `trained_block_vq`

Fit exactly `S` unrestricted two-dimensional centroids on the same fitting
rows. This is a trained block/PQ reference, not an exact oracle. Run exactly
eight deterministic starts.

Start 0 uses the selected `arbitrary_word` exact interval means independently
rounded directly to binary64 as specified above, in mixed-radix address order
`u=z_1+K_1 z_2`. If the product is below `S`, append
fitting vectors farthest from the current codebook in ids `K_1 K_2,...,S-1`,
excluding vector ids already appended by this fill.
Starts 1 through 7 use farthest-first traversal. Their first vector minimizes
the raw SHA-256 digest of

```text
{protocol_version}|{dataset_id}|{capacity}|{group_id}|{start_id}|{cell_id}|{vector_id}
```

over the fitting inventory, with the same no-brace/no-newline expansion as the
selection key. Capacity, group, start, cell, and vector ids are zero-based
canonical decimal except that capacity is the positive decimal `S`. A digest
collision is resolved by lower vector id. Every later farthest selection
excludes vector ids already selected by that start. Farthest ties use lower
vector id.

The fitting-row order for every block operation is ascending
`(cell_id, selection_digest_bytes, vector_id)`. One complete Lloyd step is:

1. assign every row by binary64 squared L2, breaking a tie at lower codeword
   id;
2. accumulate coordinate sums and counts in fitting-row order and update each
   nonempty centroid to its binary64 mean; an empty centroid retains its
   previous value;
3. reassign all rows and recompute SSE by the same direct row-order loop; and
4. return `CONTROL_INVALID` if candidate SSE is larger than prior SSE;
   otherwise accept the candidate and stop only when assignments are
   unchanged.

There is no tolerance and no rejected-update recovery path. A hard safety
limit of 300 complete iterations is not a convergence rule: hitting it makes
the control `CONTROL_INVALID` and no alternative cap may be introduced.
Choose the lowest final direct-replay fitting SSE across all eight starts;
ties select the lower start id.

Before filling, start 0 must reproduce the direct row-order reconstruction and
binary64 SSE of that directly rounded binary64 Cartesian codebook bit for bit;
it is not compared bitwise with the exact rational scalar objective. Adding
centers and every accepted Lloyd step must be nonincreasing, so the final
binary64 fitting SSE must not exceed that direct binary64 arbitrary replay.
Failure is `CONTROL_INVALID`, not evidence against block VQ. Serialize the
selected block centroids as
binary32 before held-out encoding and report per-start SSE, iterations,
assignments, empty centers, and the number of distinct binary32 centers.
Fewer than `S` distinct serialized centers is `CONTROL_INVALID`.

The synthetic-only review must also run 64 deterministic two-dimensional
trainer cases from `PCG64(20260713)` with 8 through 32 integer-coordinate rows
in `[-8,8]^2` and `S` from 2 through 8. It must verify determinism, assignment
ties, empty-center behavior, direct-replay monotonicity, Cartesian dominance,
and best-of-eight selection against an independent replay implementation.
For case id `t=0,...,63`, use `N=8+(t mod 25)`, `S=2+(t mod 7)`, and draw the
`N x 2` coordinates from NumPy `integers(-8,9)` using one fresh
`PCG64(20260713)` stream dedicated to this suite. Set
`dataset_id=synthetic_block_case_{t}` using canonical decimal `t`,
`group_id=0`, `cell_id=i mod 4`, and `vector_id=i` for row `i`. Compute each
selection digest from the registered selection-key template. Obtain start 0
by fitting both exact scalar curves through `K=S` and running the registered
arbitrary product allocator at capacity `S`; starts 1 through 7 then use the
registered capacity-based hash namespace.

### 7.5 `global_dyadic_pack_cap8` attribution control

Across all 128 selected coordinates, solve a globally packed dyadic bit
allocation under the same total panel payload:

```text
b_j in {0,...,8}
sum_j b_j <= 64 B_g
K_j = 2^b_j.
```

Use the same scalar curves and minimize fitting SSE; ties use more of the
fixed payload and then lexicographically smaller bit vectors. This arm changes
the local lookup-word interface and is therefore descriptive attribution, not
one of the three primary matched-word arms. It must appear in every result and
in any later systems protocol. The `_cap8` name is intentional: the bound
keeps the same per-scalar `K<=256` curve and scalar-lookup ceiling as the
registered word arms. It is not an unconstrained classical transform-coding
oracle and does not support such a claim.

No per-cell codebooks, learned grouping, entropy code, variable-length label,
query-trained rule, or alternative restart is permitted.

## 8. Database encoding and lookup contract

Assign every fitting or held-out scalar to the nearest serialized binary32
centroid using binary64 distance and the lower label on a tie. Assign block-VQ
labels analogously. The database word contains the direct mixed-radix or block
label, so a future expanded-table scan needs no per-vector radix decode.

For the three matched-word arms at `B_g=4`, pack even group index in the low
nibble and odd group index in the high nibble. At `B_g=8`, store one byte per
group. No alignment or tail byte is omitted. Each matched-word arm must
round-trip from packed bytes to its original 64 group labels.

`global_dyadic_pack_cap8` instead packs 128 scalar labels in selected-coordinate
order. Store each label in exactly `b_j` bits, least-significant bit first,
into one continuous bitstream. Stream bit `t` maps to byte `floor(t/8)`, bit
position `t mod 8`. If `sum_j b_j` is below the paid panel budget, zero-fill
the high tail to exactly 32 or 64 bytes. It must round-trip all 128 scalar
labels and records each bit width and bit offset. Its query-side reference has
`sum_j K_j` binary32 scalar-LUT entries and 128 scalar lookups, not 64 expanded
group tables. A scalar LUT entry promotes binary32 query and centroid to
binary64, subtracts and squares once without contraction, then narrows once to
binary32 round-to-nearest-even.

For a query-like two-vector `q_g`, construct a full binary32 `S`-entry table:

```text
T_q[u] = ||q_g - reconstruction(u)||_2^2.
```

For each valid entry, promote the binary32 query residual and binary32
centroid coordinates to binary64, subtract and square coordinate 0 then
coordinate 1, add in that order, and narrow the sum once to binary32 using
round-to-nearest-even. Both product arms set every invalid nominal address
exactly to binary32 positive infinity. The block arm has all `S` labels valid.
An independent direct replay must produce bit-identical valid table entries.
The base-only reference can time table construction, but it does not implement
or time a production scan kernel.

## 9. Frozen held-out estimands

For arm `a` in one dataset/rate cell, pool squared reconstruction errors over
all 8,192 held-out rows and all 64 groups:

```text
SSE_a = sum_{v,g} ||r_v[g] - reconstruction_a(v,g)||_2^2
D_a = SSE_a / N_vectors
NMSE_a = SSE_a / sum_{v,g} ||r_v[g]||_2^2.
```

`D_a` is mean 128-coordinate-panel SSE per selected vector; dividing once
more by 64 would only rescale every registered reconstruction contrast by the
same positive constant. Define the arbitrary improvement and trained-block
opportunity on these vector-normalized values:

```text
Delta_A = D_dyadic - D_arbitrary
Delta_V = D_dyadic - D_block_vq.
```

The registered materiality, opportunity, and closure contrasts avoid unstable
ratio inference:

```text
L_G = Delta_A - 0.05 D_dyadic
L_V = Delta_V
L_C = Delta_A - 0.50 Delta_V.
```

For readability only, report the point ratios

```text
G = Delta_A / D_dyadic
C = Delta_A / Delta_V.
```

`C` is defined only when point `Delta_V>0`; otherwise report it as undefined.
Do not bootstrap a confidence interval or p-value for `C`, average per-vector
or per-group ratios, clamp a ratio, or add an epsilon. All inference uses the
linear contrasts. A zero point dyadic `D` is `NO_GO`. Failure of `L_V>0` is
`NO_GO`; it is not a claim that block VQ is mathematically dominated.

For breadth, also compute each group's held-out `G_g`. A group with zero
dyadic SSE counts as not positive. Report all 64 groups and every selected
cardinality, used-state count, and invalid-state count. No favorable subgroup
may replace the pooled endpoint.

For each disjoint within-cell base pair, let `x` be the stored residual and
`q` the query-like residual over the 128-coordinate panel. Define

```text
d       = sum_g sum_{j=0}^1
          (float64(q_g[j])-float64(x_g[j]))^2, in group/coordinate order
d_hat_a = sum_g float64(T_q,g[packed_label_a(x,g)])
AE_a    = sum_pairs |d_hat_a-d|
A_a     = AE_a / N_pairs
P_a     = AE_a / sum_pairs d
L_Q     = A_dyadic - A_arbitrary
Q       = L_Q / A_dyadic.
```

Here each table entry is the declared binary32 lookup value. Zero-distance
pairs remain in the absolute-error sum; no epsilon is added. `Q` is descriptive
and is undefined when point `A_dyadic=0`; registered inference uses `L_Q`.
`P`, `Q`, and `L_Q` are base-only ADC-style diagnostics. They are not query
accuracy, nearest-neighbor ranking, recall, or QPS endpoints.

For `global_dyadic_pack_cap8`, replace the group-table expression for
`d_hat` by the selected-coordinate-order binary64 sum of its 128 stored
binary32 scalar-LUT entries. Report its reconstruction and pair metrics, but
do not add them to the confirmatory family after seeing the result.

## 10. Statistical procedure

Use a two-stage nonparametric bootstrap with 10,000 replicates. First create a
shared `10000 x 512` matrix of IVF-cell ids with replacement from NumPy
`Generator(PCG64(20260713))`. For each sampled cell occurrence, resample with
replacement the same number of selected held-out vectors as that cell
contains. Independently resample the same number of selected held-out pairs as
that cell contains. Minimum-two selection guarantees at least one pair per
cell. Reuse the selected row or pair indices for every arm and rate.

For each replicate, recompute `D_a` by dividing its raw SSE by that
replicate's total resampled vector count, and recompute `A_a` by dividing raw
absolute error by its total resampled pair count. Thus the target is the
vector-weighted or pair-weighted mean over the frozen stratified held-out
inventory, with IVF cells as first-stage clusters; it is not a mean of 512
cell means. The point estimates use the identical normalization on the
original selected inventory.

Generate random values in this exact order: the complete cell matrix first;
then dataset order GIST followed by CIFAR, replicate order, sampled-cell
occurrence order, vector draws, then pair draws. This defines one reproducible
PCG64 stream. The same cell matrix is reused across datasets; within-cell
indices are shared across arms/rates but not across datasets.

Cell draws are `integers(0,512,size=(10000,512))`. Within a sampled cell with
`n` selected rows or `m` pairs, use `integers(0,n,size=n)` or
`integers(0,m,size=m)`. Accumulate point rows in global
`(cell_id,digest_bytes,vector_id)` order and pairs in
`(cell_id,pair_rank)` order. Accumulate each replicate in sampled-cell
occurrence order, resampled-draw order, then group and coordinate order, using
sequential binary64 additions under the frozen numeric contract.

All 16 registered statistics are linear contrasts with null value zero. For
observed contrast `T_hat`, replicate `T_b`, and
`delta_b=T_b-T_hat`, report:

```text
two-sided basic 95% CI =
  [T_hat-quantile_0.975(delta), T_hat-quantile_0.025(delta)]
one-sided 95% lower bound = T_hat-quantile_0.95(delta)
null-centered one-sided p =
  (1 + count(delta_b >= T_hat)) / 10001.
```

Quantiles use NumPy's `method="linear"`; the p-value comparison includes
ties. Apply Holm step-down at `alpha=0.05` across exactly the 16 hypotheses in
the machine-readable contract. Sort by `(raw_p, hypothesis_id)`. In sorted
position `i` starting at one, the adjusted p-value is the running maximum of
`(16-i+1)*raw_p`, capped at one, then mapped back to its hypothesis id.

The family contains, for each of four dataset-by-rate cells:

- `L_G>0`, equivalent to more than 5% dyadic-error removal;
- `L_V>0`, establishing a positive trained-block opportunity;
- `L_C>0`, equivalent to closing more than half that opportunity; and
- `L_Q>0`, a positive base-pair absolute-error improvement.

No ratio, group, cost, entropy, global-pack, or sensitivity statistic may
enter or replace this family after results are observed. The bootstrap
conditions on the one frozen fitting inventory and its fitted codebooks. Its
second stage represents held-out row/pair variation inside sampled IVF cells;
it does not represent refitting uncertainty or end-to-end PCA/IVF training
uncertainty.

## 11. Overhead and representation accounting

The three primary arms must have identical fixed database payload:

```text
32 bytes/vector at B_g=4
64 bytes/vector at B_g=8.
```

Record actual packed bytes, alignment, and output bytes. For every arm also
record, separately:

- binary32 centroid bytes;
- per-group `uint16_t` radices and used-state metadata, plus any
  materialized multiplier and offset metadata (derived fields must be listed
  explicitly with zero persistent bytes rather than silently omitted);
- block-codeword metadata and `global_dyadic_pack_cap8` bit-width/bit-offset
  metadata (bit offsets are measured from the start of the panel bitstream);
- valid and invalid addresses;
- full expanded lookup bytes for matched-word arms, even for invalid
  addresses, and all scalar-LUT entries for the global control;
- fit/allocation/training and database-encoding wall time and CPU time;
- distance comparisons, Lloyd iterations, and accepted updates;
- table-construction arithmetic work and wall time on the first 1,024
  held-out rows in global order
  `(cell_id, selection_digest_bytes, vector_id)`; and
- peak RSS plus deterministic owned-buffer high-water bytes.

With 64 groups and binary32 entries, the mandatory expanded lookup footprint
is fixed for every matched-word arm:

```text
B_g=4:  64 * 16  * 4 = 4,096 bytes
B_g=8:  64 * 256 * 4 = 65,536 bytes.
```

The trained block-codebook footprint before headers is respectively 8,192 and
131,072 bytes (`64*S*2*4`). The arbitrary scalar codebook must count every
stored scalar centroid plus all radix/address metadata; unused database states
do not reduce the paid lookup word or table. Shannon or Huffman expected
length is outside A4-1 and may not be reported as fixed-rate savings.

For `global_dyadic_pack_cap8`, report `sum_j K_j` binary32 scalar-LUT entries,
their bytes and construction operations, and exactly 128 scalar lookups. It
pays the same 32/64 database bytes even if its selected bit sum is smaller.
These costs must not be conflated with the 64 group lookups of the matched-word
arms. The 4,096/65,536-byte expanded footprints above are per query-like
residual for this panel (and would normally be rebuilt per probed IVF cell),
not a whole-query QPS measurement.

The exact scalar solver must be compiled native code; a Python driver may only
orchestrate it. Its arbitrary-precision integer/rational library and version
must be recorded in the manifest. Set `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, and the runner's own thread count to one. Before any base
read, run the full registered scalar and block pipeline on the result of
`Generator(PCG64(20260713)).standard_normal((8192,128),dtype=float32)`.
Record the NumPy version. Use all 64 groups, both rates, and all eight block
starts. The array is C-order; group `h` uses columns `(2h,2h+1)`. Set
`dataset_id=synthetic_cost_projection`, `cell_id=0`, and `vector_id=i` for row
`i`; compute selection and capacity-based start hashes from the registered
templates. It must use the same compiled exact-arithmetic implementation,
library, compiler, all `K=1,...,256` curves, exact allocation path, and
direct-rational rounding path registered for the base run. This is a separate
precommitted synthetic-review command and its CPU time is not part of the
later atomic base command. The projected two-dataset base CPU cost is `2.5`
times this one-panel CPU time; it must not exceed 24 CPU-hours. Exceeding that
limit returns `NO_GO_EXACT_SOLVER_COST` and closes A4-1; reducing the shape or
falling back to a floating-point objective is forbidden. The factor is two
datasets plus a predeclared 25% I/O/data-shape margin, not a fitted threshold.
Its manifest and timing must be committed before real-base authorization.

Compile the native numerical path with GCC 11.5.0 and
`-O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse`; do not add
`-march=native` or call fused multiply-add. At process start call and verify
`fesetround(FE_TONEAREST)`. On x86-64, clear and verify MXCSR flush-to-zero and
denormals-are-zero bits. Direct rational-to-binary32/binary64 rounding, the
block trainer, encoding replay, LUT construction, and scientific accumulation
all use this contract. Scalar-objective and allocation decisions remain exact
integer/rational operations and may not depend on floating-point comparison.
Record the compiler identity, complete flags, CPU model, exact-arithmetic
library and version, initial/final rounding mode, MXCSR, and NumPy version in
the build manifest. A mismatch is
`IMPLEMENTATION_INVALID` before scientific output.

The later atomic base command also has a hard 24 CPU-hour ceiling over
`getrusage(RUSAGE_SELF)+getrusage(RUSAGE_CHILDREN)`, including preflight,
fitting, encoding, statistics, and output. Check after every model and before
starting the next; crossing the ceiling stops without reducing rows, groups,
rates, starts, or iterations and returns `RESOURCE_STOP`. Reference timing is
construction evidence only. `one lookup per group` is an abstract interface
count, not evidence of equal SIMD behavior or QPS.

## 12. Correctness and control gates

No scientific decision is interpreted unless all of the following pass:

1. the preregistration, input contract, hypothesis contract, and runner commit
   ids are recorded before a scientific input is opened;
2. all allowed hashes, sizes, dimensions, finite values, cell ids, split
   counts, disjointness checks, and group coordinates match exactly;
3. an open-file ledger contains no forbidden artifact;
4. the native build and runtime numeric manifest match the frozen contract,
   and the separately committed same-shape cost projection admits the base
   run under 24 CPU-hours;
5. the optimized scalar DP passes the independent exhaustive exact-rational
   tiny reference and frozen 256-case suite, passes all A4-0 compatibility
   tests, resolves every comparison exactly, and passes every real-fit exact
   replay and monotonicity diagnostic;
6. both product allocators agree with exhaustive tiny enumeration;
7. every mixed-radix address, B4/B8 packed payload, and global bitstream
   round-trips exactly;
8. binary32 and binary64 lookup values agree with direct reconstruction at
   their declared precision;
9. the block trainer passes the frozen 64-case synthetic suite, all eight
   starts converge, its product initialization is exactly the arbitrary
   Cartesian reconstruction before filling, its fitting dominance invariant
   passes, and all `S` serialized block centers are distinct;
10. every selected scalar alphabet remains strictly increasing after binary32
   serialization;
11. all valid LUT entries, output rows, contrasts, and scientific statistics
   are finite; declared positive-infinity invalid product-LUT entries are the
   only nonfinite values; and
12. every cost and byte field required above is present.

Input hash/shape/read-boundary failures return `ARTIFACT_INVALID`. Synthetic
parity, packing, LUT, numeric, schema, or accounting defects return
`IMPLEMENTATION_INVALID`. Block-VQ trainer, convergence, distinct-center, or
dominance failures return `CONTROL_INVALID`. A selected scalar alphabet that
collapses at the registered binary32 precision returns
`NO_GO_REPRESENTATION`. Only an artifact, implementation, or control defect
may be repaired; the scientific inputs, arms, endpoints, and thresholds remain
frozen, and any rerun requires a dated amendment and renewed approval.

## 13. Frozen decision rule

Return `GO_TO_SYSTEMS_PREREG` only if all of the following hold in **each** of
the four dataset-by-rate cells:

1. Holm-adjusted one-sided evidence rejects `L_G<=0`;
2. Holm-adjusted one-sided evidence rejects `L_V<=0`;
3. Holm-adjusted one-sided evidence rejects `L_C<=0`;
4. Holm-adjusted one-sided evidence rejects `L_Q<=0`;
5. at least 48 of 64 individual groups have `G_g>0`; and
6. recomputing pooled `G` after leaving out each one of the 64 groups gives a
   minimum point estimate of at least 0.05.

The 48-of-64 rule requires a three-quarter majority rather than a result driven
by a few favorable coordinates. The leave-one-group-out rule prevents one
high-energy group from carrying the pooled threshold. Both are fixed
robustness gates, not extra hypotheses.

| Outcome | Decision |
| --- | --- |
| Input provenance/read contract fails | `ARTIFACT_INVALID`; no scientific claim |
| Runner correctness, numeric, payload, or accounting contract fails | `IMPLEMENTATION_INVALID`; no scientific claim |
| Trained block control fails its declared invariant | `CONTROL_INVALID`; no scientific claim |
| Selected scalar labels collapse at binary32 | `NO_GO_REPRESENTATION`; preserve evidence |
| Same-shape projection exceeds the exact-solver budget | `NO_GO_EXACT_SOLVER_COST`; no approximation or reduced rescue run |
| Fixed 24 CPU-hour ceiling is reached | `RESOURCE_STOP`; no reduced rescue run |
| Any registered materiality, closure, pair, prevalence, or leave-one-group-out condition fails | `NO_GO`; preserve all negative evidence and close this formulation |
| Every condition passes | `GO_TO_SYSTEMS_PREREG`; data-level word-local opportunity only |

`global_dyadic_pack_cap8` determines interpretation, not passage. If it matches
or beats `arbitrary_word`, any later systems protocol must state explicitly
that the remaining hypothesis is a lookup-granularity tradeoff against a
capped global dyadic control. It may not claim a general rate-distortion
advance or unrestricted transform-coding dominance.

No additional dataset, rate, group width, coordinate map, sample, codebook
trainer, seed, threshold, or metric may rescue a `NO_GO` result.

## 14. Future command and authorization checkpoint

The future implementation must expose one atomic base-data command with only
the two committed contracts, the two content-verified data roots, an empty
output directory, and `--threads=1`. A planned interface is:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python script/run_arbitrary_cardinality_a4_1.py \
  --input-spec docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json \
  --hypotheses docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json \
  --gist-root /rwproject/kdd-db/kluaq/saq/data/gist_sample50k \
  --cifar-root /tmp/saq-run/data/cifar60k \
  --output-dir /tmp/saq-attempt4-a4-1-registered \
  --threads 1
```

The paths locate artifacts; hashes and shapes define their identity. The
runner may not expose overrides for datasets, rows, groups, rates, cardinality
limits, block starts, iteration limits, seeds, thresholds, or exclusions.

This command is recorded for review only. Its runner must not be implemented
until the user authorizes the synthetic-only implementation stage, and this
base-data command must not be run until the later real-base authorization.

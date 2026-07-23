# Attempt 4: What the Data Changed

Date: 2026-07-23

Status: **updated next-meeting draft; not yet presented**

Purpose: explain the original arbitrary-cardinality idea, the completed
base-data result, what the closest papers already cover, and why any future
work must ask a new two-dimensional modeling question.

Authoritative scientific snapshot:
`saq-a4-original-reopening-protocol@5503e87`.

---

## 1. The Short Answer

Attempt 4 asked whether a fixed-width word could be used better by giving two
scalar coordinates arbitrary numbers of reconstruction levels.

We now have the missing natural-data comparison:

- arbitrary scalar cardinalities produced essentially no held-out gain;
- a same-capacity two-dimensional codebook produced a clear gain;
- therefore the missing flexibility is the **shape of the joint codebook**,
  not the number of scalar levels; and
- the original arbitrary-cardinality formulation stops before query testing.

This is a negative result about one mechanism, not a claim that all
two-dimensional quantization is useless.

---

## 2. First Avoid One Old Misunderstanding

The original Attempt 4 was not progressive pruning.

```text
original Attempt 4                   later prefix successor
------------------                   ----------------------
read one full fixed-width word       read a short prefix, then more bits
change scalar level counts           add coarse-to-fine search meaning
one mixed-radix lookup               two-stage filtering and refinement
```

The prefix successor was separately closed because its mechanisms were a
direct composition of known work. The result discussed in this deck is about
the original, single-lookup formulation.

---

## 3. Original Intuition: Use a Four-Bit Word More Fully

Two scalar coordinates share one four-bit word. Four bits provide 16 possible
addresses.

Ordinary integer bit allocation permits:

```text
2 bits + 2 bits  -> 4 levels x 4 levels = 16 states
1 bit  + 3 bits  -> 2 levels x 8 levels = 16 states
```

Attempt 4 permits any positive integers `K1`, `K2` with:

```text
K1 x K2 <= 16.
```

For example, `(K1,K2)=(3,5)` uses 15 addresses. The hope was that three
levels on one coordinate and five on the other would fit unequal coordinate
difficulty better than every power-of-two allocation.

---

## 4. Core Method: Fit, Pack, Look Up

For every coordinate separately:

1. fit exact scalar quantizers for all permitted numbers of levels;
2. choose `K1,K2` that minimize the sum of the two scalar errors;
3. encode scalar labels `z1,z2` into one mixed-radix label;
4. build one query lookup table for that label.

```text
u = z1 + K1 * z2
T[u] = distance(query pair, reconstructed pair u)
```

For `(3,5)`, labels 0--14 are used and label 15 is unused. During database
scanning, the system still reads one word and performs one table lookup.

The important restriction is that every reconstruction remains a Cartesian
product:

```text
{a1, a2, a3} x {b1, b2, b3, b4, b5}.
```

Changing `K1,K2` changes the number of rows and columns, but it cannot move one
joint center independently of the others.

---

## 5. A Running Example: What `(3,5)` Can and Cannot Do

Suppose:

```text
coordinate 1 uses {-1, 0, 1}
coordinate 2 uses {-2, -1, 0, 1, 2}
```

| Model | Joint states | Reconstruction error |
|---|---:|---:|
| arbitrary scalar product `(3,5)` | 15 | `0` |
| ordinary power-of-two product `(4,4)` | 16 | positive |
| unrestricted 16-center 2D codebook | 16 | `0` |

This example proves that power-of-two scalar allocation can waste choices.
It does not prove that natural residuals have this shape. It also shows the
main threat: an unrestricted two-dimensional codebook contains every product
solution and can represent more.

---

## 6. The Four Arms in the Decisive Comparison

| Arm | Plain-language meaning | Question answered |
|---|---|---|
| `D` | ordinary power-of-two scalar allocation | What does the existing rectangular-grid restriction achieve? |
| `A` | arbitrary scalar cardinalities | Does changing only the row/column counts help? |
| `P` | independently trained ordinary product quantization | Does a standard strong implementation already dominate? |
| `V` | same-capacity two-dimensional vector quantization | How much is available if joint centers may move freely? |

`P` and `V` are separate controls. `P` represents the standard deployed
family; `V` is the stronger opportunity test used to avoid blaming the data
when the candidate model is simply too restrictive.

---

## 7. What Was Actually Measured

The evaluation used only base residuals; no benchmark query or ground-truth
file was read.

| Item | Frozen choice |
|---|---|
| datasets | GIST and CIFAR |
| fitting / held-out rows | 8,192 / 8,192 per dataset |
| coordinate groups | 64 fixed adjacent pairs |
| rates | B4 and B8 |
| outputs | reconstruction error, base-pair distance proxy, group prevalence, fitting and model costs |

The fitting rows selected every model. Held-out rows were used only for the
reported comparison. The result is offline base-data evidence, not Recall or
throughput evidence.

---

## 8. Main Result: Arbitrary Cardinalities Did Not Generalize

`G` below means “fraction of ordinary scalar error removed by A.” `C` means
“fraction of the D-to-V opportunity recovered by A.” `Q` is improvement in
the base-pair distance-error proxy.

| Dataset/rate | `G` | `C` | `Q` | groups helped |
|---|---:|---:|---:|---:|
| GIST B4 | `0%` | `0%` | `0%` | `0 / 64` |
| GIST B8 | `0.0928%` | `0.5396%` | `0.1237%` | `7 / 64` |
| CIFAR B4 | `0%` | `0%` | `0%` | `0 / 64` |
| CIFAR B8 | `-0.0455%` | `-0.4186%` | `-0.1252%` | `6 / 64` |

At B4, A chose exactly `(4,4)` for every group. At B8, it did choose
non-power-of-two allocations in 14 GIST and 8 CIFAR groups, so the larger
model family was genuinely exercised. Those fitting choices still produced
no material held-out benefit.

All registered materiality hypotheses for A failed after multiplicity
correction.

---

## 9. The Important Positive Observation: Two Dimensions Do Help

Relative to the ordinary scalar grid, the unrestricted 2D block codebook
reduced held-out reconstruction error by approximately:

| | B4 | B8 |
|---|---:|---:|
| GIST | `11.4%` | `17.2%` |
| CIFAR | `8.8%` | `10.9%` |

All four registered tests for the existence of this VQ opportunity passed.

So the result is not “there is nothing to improve.” It is:

> Natural residual pairs contain useful two-dimensional structure, but
> changing only the two scalar alphabet sizes does not capture it.

The rectangular grid can gain or lose rows and columns. A 2D codebook can
place every center where the data actually needs it.

---

## 10. Why Lower Reconstruction Error Is Still Not Recall

Better reconstruction can improve approximate distances, but rankings depend
on which errors occur near the nearest-neighbor decision boundary.

Three claims must remain separate:

```text
lower reconstruction error
        does not automatically imply
lower query-to-database distance error
        does not automatically imply
higher Recall at matched throughput
```

We measured the first and a base-pair proxy for the second. Because A failed
both, it was correct to stop before benchmark-query evaluation. No Recall or
QPS claim is made.

---

## 11. Closest Work I: PQ and OPQ

**Product Quantization (PQ)** splits a vector into low-dimensional blocks and
learns one vector codebook per block. Query distance is accumulated from small
lookup tables.

**Optimized Product Quantization (OPQ)** additionally learns a rotation while
learning the block codebooks:

```text
rotate vector -> split into blocks -> nearest block center -> store labels
```

OPQ can improve which dimensions are grouped together and how variance is
distributed. It does not justify arbitrary scalar cardinalities. For any
future two-dimensional model, OPQ is a required baseline because “learn a
rotation and then quantize” is already its core contribution.

---

## 12. Closest Work II: Additive and Composite Quantization

**Additive Quantization (AQ)** reconstructs a vector as a sum of codewords
selected from several dictionaries:

```text
x approximately equals c1[i1] + c2[i2] + ... + cm[im].
```

This is more expressive than independent Cartesian blocks, but encoding and
distance evaluation become harder.

**Composite Quantization (CQ)** adds a constraint on interactions between
dictionaries so query distances can still be evaluated from lookup tables.

Therefore, “represent a center using several small learned pieces” is already
covered. A proposed structured 2D model must identify a stricter database
constraint—such as one fixed label, one lookup, or much cheaper table
construction—rather than presenting composition itself as new.

---

## 13. Closest Work III: Optimize the Right Error

Standard PQ minimizes reconstruction error for individual vectors.

**Pairwise Quantization** instead learns a linear transform so subsequent
quantization better preserves pairwise squared distances or scalar products.

This matters because our end consumer is a distance estimator. It suggests a
better baseline objective, but it is not a new contribution by itself:

```text
base-only pair statistics -> learned transform -> ordinary quantizer
```

Any future claim must compare both reconstruction-oriented and pairwise-
oriented training, then still demonstrate Recall and systems performance.

---

## 14. Closest Work IV: Systems Costs Are Already Studied

**Quicker ADC** studies irregular product-subcode granularity, packed layouts,
split lookup tables, and SIMD scanning. It establishes that nonstandard
packing is not free and must be compared against an optimized scan.

**SegPQ** compresses product-quantization codebooks and supports query
processing over the compressed representation. It reports up to `4.7x`
codebook compression with about `3.3%` additional query-processing overhead.

Consequences for us:

- a smaller codebook alone is not a contribution;
- a different label layout alone is not a contribution; and
- table construction, cache behavior, decoding, Recall, and throughput must be
  measured together.

---

## 15. Where the Original Idea Sits in Prior Work

- Muresan--Effros already solve optimal one-dimensional quantization for an
  integer number of levels.
- Brandt already combines learned scalar quantizers, integer bit allocation,
  packed words, lookup tables, and ANN scanning.
- FSQ already uses products of small scalar level sets, including
  non-power-of-two factor sizes.
- BAPQ allocates unequal integer bit counts to PQ subspaces.
- Mixed-radix addressing is standard.
- Q-Palette and FibQuant further crowd broad “denser rate choices” claims.

The A4-OR-B result now adds empirical closure: even where arbitrary level
counts were selected, they did not recover the measured two-dimensional
opportunity.

---

## 16. A Better Modeling Question

The next question should not be “which other values of `K1,K2` should we
try?” It should be:

> Can a compact structured 2D codebook recover most of full 2D VQ quality
> while preserving a fixed label and cheap lookup?

One concrete example is a shared-shape affine codebook:

```text
center[g,k] = mean[g] + transform[g] * shared_shape[k]
```

- `shared_shape[k]` is one reusable non-rectangular set of 2D points;
- `transform[g]` scales, rotates, and shears it for group `g`;
- the database still stores one fixed-width label `k`; and
- the query still builds one table and performs one lookup per group.

At B8, a rough FP32 representation is about 3.5 KiB instead of 128 KiB for
independent 2D centers. That size reduction matters scientifically only if it
also changes a real systems bottleneck.

---

## 17. Why This Is Not Yet a Contribution

For the current global model, the full B8 2D codebook is only 128 KiB. Merely
compressing it is unlikely to matter.

A publishable database question would need a setting such as many local
codebooks, many probed cells, or frequent updates, where model and table costs
are actually material. The structured model would then need to:

1. recover most of the D-to-V quality gain;
2. preserve the fixed-width label and scan semantics;
3. reduce measured table-build, cache, memory, or update cost;
4. match or improve Recall at matched throughput; and
5. beat PQ/OPQ, AQ/CQ-style alternatives, Pairwise Quantization, Quicker ADC,
   and codebook-compression baselines fairly.

Without that systems effect, ordinary 2D PQ/VQ is the simpler answer.

---

## 18. Cheapest Discriminating Next Check

Before building another ANN path:

1. fit the shared-shape affine model using only the existing fitting panels;
2. evaluate it on the existing held-out panels against D and V;
3. measure how much of the D-to-V gap it recovers;
4. count model bytes and table-building arithmetic; and
5. stop if it requires nearly unrestricted per-group centers or recovers only
   a small part of V's gain.

Only a strong base-only result would justify a later native table-build and
scan comparison. Benchmark queries should remain untouched until the model
and decision rule are frozen.

---

## 19. Final Decision

```text
arbitrary scalar cardinalities       CLOSED: NO_GO_BASE_ONLY
same-capacity 2D opportunity         REAL on both datasets and rates
Recall / QPS                         NOT MEASURED
prefix-code successor                separately CLOSED as direct composition
structured 2D successor              a new question, not yet established
```

The clean conclusion for the meeting is:

> We finally ran the comparison that the old exact pipeline never reached.
> The original `(K1,K2)` idea is not the right model for natural residuals.
> The evidence points toward joint two-dimensional geometry, but the closest
> literature means that quality alone is insufficient; a future direction
> must also expose and move a real database-systems cost frontier.

---

## References and Authoritative Records

- Muresan and Effros. *Quantization as Histogram Segmentation*. DCC 2002.
- Brandt. *Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions*. CVPR 2010.
- Ge et al. *Optimized Product Quantization*. CVPR 2013.
  <https://www.microsoft.com/en-us/research/wp-content/uploads/2013/06/cvpr13opq.pdf>
- Babenko and Lempitsky. *Additive Quantization for Extreme Vector
  Compression*. CVPR 2014.
  <https://openaccess.thecvf.com/content_cvpr_2014/html/Babenko_Additive_Quantization_for_2014_CVPR_paper.html>
- Zhang, Du, and Wang. *Composite Quantization for Approximate Nearest
  Neighbor Search*. ICML 2014.
  <https://proceedings.mlr.press/v32/zhangd14.html>
- Guo et al. *Adaptive Bit Allocation Product Quantization*. Neurocomputing,
  2016. <https://doi.org/10.1016/j.neucom.2015.07.062>
- Babenko, Arandjelović, and Lempitsky. *Pairwise Quantization*. 2016.
  <https://arxiv.org/abs/1606.01550>
- Mentzer et al. *Finite Scalar Quantization*. ICLR 2024.
  <https://arxiv.org/abs/2309.15505>
- André, Kermarrec, and Le Scouarnec. *Quicker ADC*. TPAMI.
  <https://arxiv.org/abs/1812.09162>
- Liu et al. *Not Small Enough? SegPQ: A Learned Approach to Compress Product
  Quantization Codebooks*. PVLDB 2025.
  <https://www.vldb.org/pvldb/vol18/p3730-liu.pdf>
- Lee and Song. *Q-Palette*. 2025. <https://arxiv.org/abs/2509.20214>
- Lee and Kim. *FibQuant*. 2026. <https://arxiv.org/abs/2605.11478>
- Riskin et al. *Index Assignment for Progressive Transmission of Full Search
  Vector Quantization*. IEEE TIP 1994.
  <https://doi.org/10.1109/83.287025>
- André et al. *Derived Codebooks for High-Accuracy Nearest Neighbor Search*.
  2019. <https://arxiv.org/abs/1905.06900>
- Douze et al. *Polysemous Codes*. ECCV 2016.
  <https://arxiv.org/abs/1609.01882>
- Base-only result:
  `saq-a4-original-reopening-protocol@5503e87`,
  `docs/saq_a4_or_b_base_only_result_2026_07_23.md`.
- R0 decision: `saq-a4-r0-static-gate@617ad25`.
- Prefix-successor S0 decision: `saq-a4-prefix-novelty-gate@7f4c001`.

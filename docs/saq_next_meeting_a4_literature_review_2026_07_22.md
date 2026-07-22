# Attempt 4 Literature Review: What We Actually Tried and Why It Stopped

Date: 2026-07-22

Status: **corrected next-meeting draft; not yet presented**

Purpose: explain the original arbitrary-cardinality idea, what the closest
papers already cover, what our work actually established, and why a later
prefix-code successor must not be confused with the original Attempt 4.

---

## 1. The Correction in One Sentence

The original Attempt 4 was **not** a progressive-pruning proposal.

It asked whether one fixed-width database word could be used more efficiently
by allowing each scalar quantizer to have an arbitrary integer number of
levels, instead of only a power-of-two number of levels.

```text
original Attempt 4                 later prefix successor
------------------                 ----------------------
use the full word once             first read a prefix
arbitrary level counts             then read the full word
mixed-radix address                coarse-to-fine search meaning
```

These are two different research questions and have different stop reasons.

---

## 2. Original Intuition: Use the Fixed Word More Fully

Suppose two scalar coordinates share one four-bit word. Four bits provide 16
possible addresses.

Ordinary bit allocation gives each coordinate an integer number of bits:

```text
2 bits + 2 bits -> 4 levels x 4 levels = 16 joint states
1 bit  + 3 bits -> 2 levels x 8 levels = 16 joint states
```

This forces every scalar level count to be a power of two. Attempt 4 instead
allowed arbitrary positive integers `K1` and `K2`, subject to

```text
K1 x K2 <= 16.
```

For example, `(K1,K2)=(3,5)` uses 15 of the 16 available addresses. The hope
was that three levels on one coordinate and five on the other might fit the
data better than every legal power-of-two allocation.

---

## 3. Running Example: Why `(3,5)` Can Matter

Consider a deliberately simple source:

```text
coordinate 1 takes {-1, 0, 1}             -> exactly 3 useful values
coordinate 2 takes {-2, -1, 0, 1, 2}      -> exactly 5 useful values
```

With one four-bit word:

| Allocation | Joint states | Reconstruction error |
|---|---:|---:|
| arbitrary `(3,5)` | 15 | `0` |
| best power-of-two `(4,4)` | 16 | `0.1` per vector |
| unrestricted 16-center two-dimensional codebook | 16 | `0` |

This proves only that the power-of-two restriction can waste useful choices.
It does **not** prove an advantage on natural data, nearest-neighbor Recall, or
query speed. The unrestricted two-dimensional codebook also matches the
example exactly.

---

## 4. How the Original Code Would Work

For scalar labels `z1` and `z2`, with `0 <= z1 < K1` and `0 <= z2 < K2`, form
one mixed-radix address:

```text
u = z1 + K1 x z2.
```

For `(K1,K2)=(3,5)`, `u` ranges from 0 to 14. Address 15 is unused.

For each query, build a table whose entry is the two-coordinate distance:

```text
T[u] = distance from the query group to reconstruction u.
```

The database scan still reads one fixed four-bit word and performs one table
lookup per group. There is no prefix, progressive decoding, or first-stage
candidate pruning in this original mechanism.

---

## 5. What Prior Work Already Covers

The original idea combines several known ingredients:

- **Muresan--Effros (2002):** globally optimal one-dimensional quantizers with
  an integer number of levels, including counts that are not powers of two.
- **Brandt (2010):** learned scalar quantizers, integer bit allocation, packed
  database words, query lookup tables, and approximate-nearest-neighbor scan.
- **Finite Scalar Quantization, FSQ (2024):** product codebooks made from small
  scalar level sets, including non-power-of-two factor sizes.
- **Mixed-radix indexing:** the standard method for mapping several finite
  alphabets into one integer address.

Therefore, arbitrary level counts or mixed-radix packing alone are not a
defensible contribution. A surviving database contribution would have to show
a material accuracy--cost advantage under the fixed-word scan constraint.

---

## 6. BAPQ and Quicker ADC: Close, but Not the Same

**Adaptive Bit Allocation Product Quantization, BAPQ (2016)** gives different
numbers of bits to different independent subspaces. A subspace receiving five
bits still has exactly 32 codewords; it does not receive an arbitrary number
such as 27 or 30.

**Quicker ADC (2021)** studies four-, five-, and six-bit product subcodes,
their packed layouts, split lookup tables, and processor cost. Its subcodebook
sizes also remain powers of two.

These papers cover unequal bit allocation and the real cost of irregular
packing. They do not implement the original `(3,5)` mixed-radix choice, but
they are mandatory baselines: Attempt 4 must beat well-optimized ordinary
product quantization, not just a weak scalar allocation.

---

## 7. Dense Rates and Arbitrary Levels Are Already Crowded

Three newer lines make a broad novelty claim difficult:

- **FSQ (2024)** already uses products of small scalar level sets.
- **Q-Palette (2025)** studies fractional-rate quantizers and mixed allocation.
- **FibQuant (2026)** studies dense fixed-rate, random-access vector coding and
  shows why a vector code can outperform a scalar-product restriction for its
  canonical source.

They do not collectively contain our exact database scan design. However,
they mean that “we allow more rate choices” is not enough. The paper-level
question must be whether the factorized mixed-radix restriction buys a new,
measured database-systems trade-off.

---

## 8. Why Product Quantization and Block VQ Are Separate Controls

Two controls answer different questions:

| Control | What it tests |
|---|---|
| optimized product quantization | whether ordinary power-of-two product codes already obtain the same accuracy and scan speed |
| same-capacity two-dimensional block vector quantization | whether arbitrary scalar products lose too much by forbidding general two-dimensional centers |

The block codebook is more expressive: every product reconstruction is a
legal block-code reconstruction, but not every block codebook factors into
independent scalar alphabets. Attempt 4 would need a clear reason to retain
factorization, such as lower training cost, smaller model state, or cheaper
table construction—and would need to measure that advantage.

---

## 9. What We Actually Established

```text
A4-0    synthetic example passed
        -> instrument can recover the known (3,5) advantage

A4-1S   exact frozen construction stopped on cost
        -> no natural-data result was reached

V2      execution produced no valid terminal scientific record
        -> runtime remains unknown

A4-R0   static compatibility check failed
        -> original representation is not an unchanged-SAQ encoder swap
```

There is no measured result for natural-data prevalence, Recall, throughput,
optimized product quantization, or trained block vector quantization.

---

## 10. What the 24-Hour Stop Means

The frozen A4-1S pipeline completed 61 of 128 scalar-coordinate shards:

| Recorded work | CPU time |
|---|---:|
| exact scalar construction | `4.64` hours |
| canonical evidence serialization | `5.03` hours |
| completed prefix total | `9.668` hours |
| registered full-pipeline lower bound | `24.17` hours |

The frozen ceiling was `24.0` CPU-hours, so the registered procedure stopped.
This is a cost result about that exact solver-and-evidence pipeline—not a
proof that every implementation of arbitrary-cardinality quantization must
take more than 24 hours.

---

## 11. Why It Was Not an Unchanged SAQ Encoder Swap

The static R0 review compared the original Attempt 4 representation with the
existing SAQ representation and query consumers.

Attempt 4 requires:

- learned scalar centers and per-group cardinalities;
- mixed-radix group labels and a way to mark unused addresses;
- new per-group distance tables; and
- a query consumer that interprets one joint group label.

Existing SAQ instead stores per-coordinate bitplanes and reconstructs its
estimate using a uniform step size and a per-vector rescaling factor. Equal
payload bytes do not give the bytes the same meaning.

**R0 conclusion:** `NO_GO_UNCHANGED_SAQ_COMPATIBILITY`. This says integration
requires a new representation and query path. It does not say the underlying
arbitrary-cardinality idea is mathematically false or empirically ineffective.

---

## 12. The Prefix Proposal Was a Later Successor

Only after R0 did the project define a broader successor:

```text
first p bits  -> coarse lookup and candidate filtering
all B bits    -> accurate lookup
```

That successor added a learned label permutation, a nested prefix partition,
and two query stages. Its protocol explicitly called itself **a new
direction**. These mechanisms were not present in the original mixed-radix
Attempt 4.

This distinction explains why progressive-transmission and two-stage-search
papers appear in the record: they evaluate the successor, not the original
intuition.

---

## 13. Why the Prefix Successor Was Closed

For the later successor only:

- **Riskin et al. (1994)** add progressive prefix reconstructions after fixing
  a fine vector quantizer.
- **Derived Codebooks (2019)** derive a coarse grouping from a fine product
  code and use coarse scan followed by accurate refinement.
- **Polysemous Codes (2016)** learn binary labels that support cheap filtering
  while retaining accurate product-code lookup.

Combining these label/prefix mechanisms with a known arbitrary-level product
code did not leave a new constraint or algorithm. The reviewed successor
decision was `NO_GO_DIRECT_COMPOSITION`.

That decision closes the prefix successor. It must not be used as the reason
that the original Attempt 4 stopped.

---

## 14. The Two Conclusions

| Direction | What stopped it | What remains unknown |
|---|---|---|
| original arbitrary-cardinality Attempt 4 | frozen exact pipeline cost; later shown incompatible with unchanged SAQ | natural-data gain, Recall, speed, and fair PQ/block-VQ comparison |
| later prefix-code successor | source review found a direct composition of known mechanisms | no implementation was justified under that successor claim |

The responsible summary is therefore not “progressive pruning was already
known, so Attempt 4 failed.”

It is: “the original coding intuition remains experimentally unresolved, but
the executed path stopped before the decisive database comparison; a later
prefix-based reformulation was separately rejected on prior-work grounds.”

---

## 15. If We Reconsider the Original Attempt 4

A fresh decision should return to the original question rather than revive
the prefix successor. Before substantial implementation, it would need:

1. a cheaper construction method whose approximation error is explicitly
   controlled;
2. independently optimized power-of-two product quantization and
   same-capacity block vector quantization as separate controls;
3. complete accounting of model bytes, table-building work, encoding time,
   and scan cost; and
4. a frozen test of whether any reconstruction or estimator improvement moves
   the Recall--throughput frontier.

This slide describes the unresolved evidence needed. It is not execution
authorization and does not reopen the stopped branch.

---

## References and Authoritative Records

- Muresan and Effros. *Quantization as Histogram Segmentation*. DCC 2002.
- Brandt. *Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions*. CVPR 2010.
- Mentzer et al. *Finite Scalar Quantization*. ICLR 2024.
  <https://arxiv.org/abs/2309.15505>
- Ge et al. *Optimized Product Quantization*. CVPR 2013.
- Guo et al. *Adaptive Bit Allocation Product Quantization*. Neurocomputing,
  2016. <https://doi.org/10.1016/j.neucom.2015.07.062>
- Andre et al. *Quicker ADC*. TPAMI 2021.
  <https://arxiv.org/abs/1812.09162>
- Lee and Song. *Q-Palette*. 2025. <https://arxiv.org/abs/2509.20214>
- Lee and Kim. *FibQuant*. 2026. <https://arxiv.org/abs/2605.11478>
- Riskin et al. *Index Assignment for Progressive Transmission of Full Search
  Vector Quantization*. IEEE TIP 1994. <https://doi.org/10.1109/83.287025>
- Andre et al. *Derived Codebooks for High-Accuracy Nearest Neighbor Search*.
  2019. <https://arxiv.org/abs/1905.06900>
- Douze et al. *Polysemous Codes*. ECCV 2016.
  <https://arxiv.org/abs/1609.01882>
- Original A4 formulation:
  `docs/saq_attempt4_arbitrary_cardinality_related_work_and_gate_2026_07_13.md`.
- R0 decision: `saq-a4-r0-static-gate@617ad25`.
- Prefix-successor S0 decision: `saq-a4-prefix-novelty-gate@7f4c001`.

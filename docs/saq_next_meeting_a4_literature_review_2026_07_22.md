# Why We Stopped the Attempt 4 Prefix-Code Direction

Date: 2026-07-22

Status: **next-meeting draft; not yet presented**

Purpose: explain the literature boundary behind the reviewed
`NO_GO_DIRECT_COMPOSITION` decision. This is a source review, not a new
method or an experimental result.

---

## 1. The Decision in One Sentence

We wanted one compact database code to support two jobs:

- read only the first few bits for a cheap first pass; and
- read the complete code for a more accurate second pass.

The literature already supplies the compact factorized code, the progressive
bit meaning, the learned label assignment, and the two-pass search pattern.
Putting these known pieces together did not leave a new algorithmic obstacle.

**Decision:** stop at the literature gate, before implementation or data.

---

## 2. What the Proposed Code Was Supposed to Do

Plain-language definitions:

- A **factorized code** splits a vector into small groups and quantizes each
  group separately.
- A **prefix** is the first few bits of a stored code.
- A **coarse pass** uses less information to reject unlikely candidates.
- A **fine pass** uses the complete stored code for a better distance estimate.

```text
database vector
      |
      v
[ one fixed-length stored word ]
      | first p bits        | all B bits
      v                     v
 cheap coarse score    accurate lookup score
```

The hoped-for contribution was to design both meanings together.

Terms used below: **VQ** means vector quantization; **PQ** means product
quantization; **OPQ** means optimized PQ; **ANN** means approximate
nearest-neighbor search; **ADC** is the usual query-to-code lookup; and
**k-means** is standard centroid training.

---

## 3. The Review Question Was Deliberately Narrow

We did **not** ask whether a new optimizer could lower reconstruction error.
We asked:

> Is there a query-unaware, fixed-rate two-stage code here that cannot be
> obtained by combining known factorized quantizers with known progressive or
> learned index assignments?

Before writing code, a surviving direction needed at least one of these:

1. a new constraint that prevents the known pieces from composing;
2. a new lemma or algorithm needed to satisfy that constraint; or
3. a measurable state or training advantage that an unrestricted block
   codebook could not obtain.

The primary papers did not leave such a gap.

---

## 4. Papers That Already Cover the Fine Code

**Muresan--Effros (2002):** globally optimal scalar quantization by histogram
segmentation. It covers learned scalar values and an integer number of levels.

**Brandt (2010):** principal component analysis, learned one-dimensional quantizers, integer bit
allocation, packed database words, query lookup tables, and linear ANN scan.

**Finite Scalar Quantization, FSQ (2024):** an implicit product codebook made
from small scalar level sets, including non-power-of-two factor sizes.

Together these papers already cover the proposed fine-code ingredients:

```text
learn scalar values + choose level counts + form a product code + pack a word
```

They do not give the new prefix meaning—but other papers do.

---

## 5. BAPQ: Unequal Bits Are Not Progressive Bits

**Adaptive Bit Allocation Product Quantization (2016)** calls its method
**BAPQ**. It does this:

1. rotate the data with principal component analysis;
2. split coordinates into independent subspaces;
3. greedily assign each available bit to the subspace that most reduces total
   reconstruction error;
4. train that subspace's codebook with standard centroid training (k-means); and
5. concatenate the ordinary subspace codeword indices.

If one subspace receives 5 bits and another receives 3 bits, their codebooks
have 32 and 8 entries. The first 3 bits of the 5-bit label are **not** trained
as a coarser version of the same codeword.

BAPQ therefore covers adaptive bit allocation, but not a nested prefix,
coarse objective, learned label permutation, or prefix/full joint training.

---

## 6. Riskin: Progressive Meaning After the Fine Code Is Fixed

**Riskin et al. (1994)** start from an existing full-search vector quantizer.
Its finest encoding regions stay fixed.

They then merge those regions into a progressive tree:

```text
fixed fine regions -> merge nearby regions -> fit an intermediate centroid
                   -> repeat for earlier prefixes
```

The paper explicitly says it optimizes the decoder for a fixed encoder, not
the encoder for the decoder. Intermediate decoding needs no new search: use
the centroid of the merged region containing the already selected fine region.

This is decisive because it supplies progressive prefix reconstruction as a
post-processing step over an arbitrary fixed fine codebook.

---

## 7. Derived Codebooks: The Closest ANN System

**Derived Codebooks (2019)** already applies the coarse/fine idea to product
quantization used for approximate nearest-neighbor search.

```text
train a fine 16-bit product codebook
              |
              v
derive an 8-bit coarse grouping of fine centroids
              |
              v
reorder fine labels so selected bits identify the coarse group
              |
              v
coarse scan first -> accurate refinement second
```

Its coarse selector is not printed as the leading bits, but a fixed bit
permutation can move those selector bits to the front. Physically, that is the
same stored-word interface as a prefix.

---

## 8. Polysemous Codes: One Label, Two Search Meanings

**Polysemous Codes (2016)** first trains an ordinary product quantizer. It then
learns a one-to-one mapping from centroid indices to binary labels.

The same stored label supports:

- a cheap Hamming-distance filter: compare bit strings; and
- accurate asymmetric-distance lookup: use the original product centroids.

Its loss can preserve centroid distance or ranking. It optimizes all label
bits rather than an explicit nested leading prefix, but it already establishes
the important mechanism: a learned label assignment can give one stored code
both a cheap meaning and an accurate meaning.

Training remains sequential: product codebook first, binary mapping second.

---

## 9. Hierarchical Coding Was Also Checked

**Chou--Lookabaugh--Gray (1989)** jointly design and prune tree-structured
vector quantizers under distortion and rate objectives.

This paper matters because it prevents an overly broad novelty claim such as
"joint hierarchical quantizer design is new."

However, its object is variable-rate source coding, not one fixed random-access
database word with a prescribed ANN lookup path. It is therefore a boundary
paper, not the single paper that already contains our entire candidate.

The conclusion is more precise:

- no one inspected paper contains every desired property; but
- the missing fixed-word ANN construction is supplied by composing the other
  papers, without a new coupling constraint.

---

## 10. Coverage Map

| Paper family | Fine factorized code | Learned/progressive label | Cheap + accurate search | Joint prefix/full design |
|---|---:|---:|---:|---:|
| Muresan, Brandt, FSQ | Yes | No | Brandt: accurate lookup | No |
| OPQ, BAPQ, Quicker ADC | Yes | No | Accurate PQ lookup | No |
| Riskin | Fine VQ is fixed | Yes: nested prefixes | Progressive decoding | No: post-processing |
| Derived Codebooks | Yes: PQ | Yes: coarse selector | Yes: scan then refine | No: derived afterward |
| Polysemous Codes | Yes: PQ | Yes: binary mapping | Yes: filter then score | No: learned afterward |
| Chou et al. | Hierarchical VQ | Yes | Not the fixed-word ANN path | Yes, in source coding |

No row alone has every check mark. The stop comes from the next question:
does joining the rows require a genuinely new mechanism? We found none.

---

## 10A. Additional Boundary Papers

- **Optimized Product Quantization, OPQ (2013):** learns a rotation and product
  codebooks, but gives no progressive meaning to the stored index.
- **Quicker ADC (2021):** exposes packing and lookup costs for 4-, 5-, and
  6-bit product subcodes; every subcodebook still has `2^b` entries.
- **Q-Palette (2025):** covers fractional-rate quantizers and mixed allocation,
  but not the proposed prefix consumer.
- **FibQuant (2026):** strengthens the block-vector-code baseline and supplies
  no prefix mechanism.

These close coding and systems side routes. Riskin, Derived Codebooks, and
Polysemous are the decisive prefix and two-meaning papers.

---

## 11. Why the Combination Is Direct

The proposed construction can be written as known steps:

```text
FSQ / Brandt / BAPQ:
    train the factorized fine representatives and choose level counts

Riskin / Derived / Polysemous:
    group or relabel the already trained fine codewords for a cheap first pass

Derived / Polysemous:
    retain the same full label for accurate second-pass lookup
```

Changing ordinary PQ centroids to arbitrary-level scalar-product centroids
changes reconstruction quality, model size, and training cost. It does not by
itself create a new prefix constraint, theorem, or search algorithm.

That is the meaning of `NO_GO_DIRECT_COMPOSITION`.

---

## 12. What This Decision Does—and Does Not—Say

It **does** say:

- this specific prefix-code successor lacks a defensible mechanism-level
  novelty claim;
- arbitrary cardinalities are not required for the prefix mechanism; and
- S1 implementation, data access, and performance work are not justified.

It **does not** say:

- all progressive codes are useless;
- factorized codes can never beat block vector quantization;
- the proposed code has been tested and failed on ANN benchmarks; or
- no future research question can use these papers.

This was an early literature stop, not an experimental failure.

---

## 13. What Would Be Needed to Reopen the Direction

A reopening should begin with a different scientific claim, not another
implementation of the same composition. It would need all of the following:

1. name a property that Riskin, Derived Codebooks, Polysemous, and hierarchical
   vector quantization cannot obtain by direct composition;
2. show the new constraint, lemma, or algorithm required by that property;
3. compare against independently optimized product quantization and block
   vector quantization under the same prefix and full-code budget; and
4. freeze a quantitative construction, state, and query-cost gate before data.

Until such a gap is stated, the responsible decision is to keep these works as
baselines and select a different problem.

---

## References and Authoritative Decision

- Muresan and Effros. *Quantization as Histogram Segmentation*. DCC 2002.
- Brandt. *Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions*. CVPR 2010.
- Mentzer et al. *Finite Scalar Quantization*. ICLR 2024.
  <https://arxiv.org/abs/2309.15505>
- Ge et al. *Optimized Product Quantization*. CVPR 2013.
- Guo et al. *Adaptive Bit Allocation Product Quantization*. Neurocomputing,
  2016. <https://doi.org/10.1016/j.neucom.2015.07.062>
- Riskin et al. *Index Assignment for Progressive Transmission of Full Search
  Vector Quantization*. IEEE TIP, 1994. <https://doi.org/10.1109/83.287025>
- Andre et al. *Derived Codebooks for High-Accuracy Nearest Neighbor Search*.
  2019. <https://arxiv.org/abs/1905.06900>
- Douze et al. *Polysemous Codes*. ECCV 2016.
  <https://arxiv.org/abs/1609.01882>
- Chou, Lookabaugh, and Gray. *Optimal Pruning with Applications to
  Tree-Structured Source Coding and Modeling*. IEEE TIT, 1989.
  <https://doi.org/10.1109/18.32124>
- Andre et al. *Quicker ADC: Unlocking the Hidden Potential of Product
  Quantization with SIMD*. <https://arxiv.org/abs/1812.09162>
- Lee and Song. *Q-Palette: Fractional-Bit Quantizers Toward Optimal Bit
  Allocation for Efficient LLM Deployment*. 2025.
  <https://arxiv.org/abs/2509.20214>
- Lee and Kim. *FibQuant: Universal Vector Quantization for Random-Access
  KV-Cache Compression*. 2026. <https://arxiv.org/abs/2605.11478>
- Reviewed S0 decision: `saq-a4-prefix-novelty-gate@7f4c001`,
  `docs/saq_a4_successor_s0_prefix_code_novelty_decision_2026_07_22.md`.

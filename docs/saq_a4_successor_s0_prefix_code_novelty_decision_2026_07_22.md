# Attempt 4 Successor S0 Prefix-Code Novelty Decision

Date: 2026-07-22

Branch: `saq-a4-prefix-novelty-gate`

Protocol snapshot: `c0467d1`

Authorization: user-authorized source-only successor gate

Decision: **`INCONCLUSIVE_MECHANISM_EVIDENCE`**

S1 status: **`NOT_AUTHORIZED`**

## 1. Question and boundary

S0 asks whether a fixed-rate factorized group code whose leading bits support
a coarse ANN pass and whose full word supports accurate lookup leaves a
mechanism not already supplied by progressive vector quantization, product
code index assignment, binary filtering, derived coarse codebooks, and known
arbitrary-level factorized quantizers.

The candidate jointly chooses scalar representatives, integer cardinalities,
a full-label permutation, a nested prefix partition, and coarse values.  Its
intended scan reads `p` prefix bits for one coarse lookup per group and later
reads the full `B`-bit label for one accurate lookup per reranked group.

The gate inspected primary papers and committed source metadata only.  It did
not open a dataset, benchmark query, result, ground truth, index, cache, or
runtime-state path.  It did not write or execute code, build a binary, or run a
synthetic or natural-data experiment.

The old outcomes remain unchanged: A4-0 is only a synthetic dyadic witness,
A4-1S is a cost failure of its frozen exact construction/evidence pipeline,
V2 is `CRASH_OR_UNKNOWN / START_ONLY`, and R0 is only an unchanged-SAQ
compatibility no-go.

## 2. Decision rule

The protocol requires `YES`, `NO`, or `UNRESOLVED` for ten mechanism columns.
An abstract can support an explicit positive statement but cannot establish a
decisive absence.

Outcome precedence is:

1. unidentified or uninspected required source;
2. decision-critical unresolved mechanism evidence;
3. one-source prior solution;
4. direct composition;
5. arbitrary cardinality unnecessary;
6. unquantified cost-only residual; or
7. one surviving non-compositional mechanism.

All required sources were identified and at least primary text was inspected,
so `INCONCLUSIVE_SOURCE_GAP` does not apply.  Some cells that determine steps
3--5 remain unresolved, so the protocol stops at step 2.

## 3. Matrix legend

| Code | Column |
| --- | --- |
| `FW` | one fixed-length random-access database word |
| `FR` | factorized or Cartesian-product reconstruction |
| `AC` | a factor may use a non-power-of-two cardinality |
| `LA` | learned assignment from fine codewords to stored bit labels |
| `NP` | a bit subset or prefix defines an explicit nested coarse partition |
| `CO` | coarse geometry is optimized for distortion, ranking, or filtering |
| `FL` | the fine label supports accurate table-based scoring |
| `JT` | fine reconstruction and coarse/prefix objective are jointly trained |
| `SC` | permanent state or construction cost is described |
| `QC` | online lookup, filtering, refinement, or scan cost is described |

`U` means `UNRESOLVED`, not an inferred `NO`.

## 4. Primary-source claim matrix

| Primary work | FW | FR | AC | LA | NP | CO | FL | JT | SC | QC | Locator for every `YES`/`NO` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Muresan--Effros 2002 | YES | NO | YES | NO | NO | NO | NO | NO | YES | NO | `FW,AC,SC`: §§II--IV, pp.303--308; all `NO`: complete scalar shortest-path method, §§II--V, pp.303--309 |
| Brandt 2010 | YES | YES | NO | NO | NO | NO | YES | NO | YES | YES | `FW,FR,FL,SC,QC`: §§3.3--3.6, pp.1817--1819; all `NO`: complete codec/search definition, §§3.3--3.6 |
| Finite Scalar Quantization 2024 | YES | YES | YES | NO | NO | NO | NO | NO | YES | NO | `FW,FR,AC,SC`: §3.1 and Table 1, p.3, §3.3 pp.3--4; all `NO`: complete FSQ mechanism, §§3.1--3.3 |
| Q-Palette 2025 | YES | NO | U | NO | NO | NO | NO | NO | YES | YES | `FW,SC,QC`: §3 and Table 1, pp.3--4, App. C.3.1 p.18; all `NO`: quantizer/kernel definitions, §§3.1--3.3, pp.3--6 |
| FibQuant 2026 | YES | NO | NO | NO | NO | NO | NO | NO | YES | YES | `FW,SC,QC`: §3.1, pp.3--4 and §5; all `NO`: block-code definition and scalar comparison, §§3--4, pp.3--7 |
| Optimized Product Quantization 2013 | YES | YES | NO | NO | NO | NO | YES | NO | YES | YES | `FW,FR,FL,SC,QC`: §2 pp.2946--2948 and §4 pp.2950--2951; all `NO`: full objective/codec, §§2--3 |
| Adaptive Bit Allocation PQ 2016 | YES | YES | NO | U | U | U | YES | U | YES | YES | all non-`U`: publisher primary abstract, introduction, §3 opening, and conclusion: PCA/subspace PQ, `log_2 k`-bit indices, unequal-bit objective, greedy allocation, and summed subspace-distance search |
| Quicker ADC 2021 | YES | YES | NO | NO | NO | NO | YES | NO | YES | YES | all cells: §§3.1--3.4, pp.4--7; `AC=NO` follows explicit `2^b` 4/5/6-bit subquantizers in §3.1 |
| Derived Codebooks 2019 | YES | YES | NO | YES | YES | YES | YES | NO | YES | YES | `FW,FR,LA,NP,CO,FL,SC,QC`: §§3.1--3.3, pp.3--5, Algorithms 2--3 and property P1; `AC,JT`: same complete construction |
| Polysemous Codes 2016 | YES | YES | NO | YES | NO | YES | YES | NO | YES | YES | `FW,FR,LA,CO,FL,SC,QC`: §§3.1--3.3, Eqs.(1)--(7); `AC,NP,JT`: complete sequential PQ-then-bijection method, §§3--3.3 |
| Riskin et al. 1994 | YES | U | U | YES | YES | YES | U | NO | YES | YES | `FW,LA,NP,CO,SC`: abstract and §§I--III, pp.307--311; `JT=NO,QC=YES`: §II around Eq.(1) and §III.3, pp.309--311: fixed original Voronoi regions, decoder-only centroid fitting, and no intermediate-codeword search |
| Chou--Lookabaugh--Gray 1989 | NO | U | U | U | YES | YES | U | YES | YES | `FW=NO`, `NP,CO,JT,SC=YES`: abstract and §II, pp.299--305, variable-rate tree pruning and successive approximation |

## 5. Exact source support

Muresan and Effros formulate globally optimal fixed-rate scalar quantizers for
discrete sources by histogram segmentation.  This covers learned scalar
alphabets and integer numbers of levels, but not a factorized ANN prefix scan.
The fixed identity is the DCC 2002 paper recorded in the A4 source ledger.

Brandt's CVPR 2010 transform coder combines PCA, integer bit allocation,
trained one-dimensional quantizers, packed words, 256-entry query tables, and
linear ANN scan.  Sections 3.3--3.6 cover the allocation, quantizers, packing,
and lookup interface.

[Finite Scalar Quantization](https://arxiv.org/abs/2309.15505) Section 3.1
forms an implicit codebook as the Cartesian product of small scalar level sets
and maps it bijectively to an integer.  Its published configurations include
non-power-of-two factor sizes.  It does not propose this ANN prefix consumer.

[Q-Palette](https://arxiv.org/abs/2509.20214) supplies fractional-rate scalar,
vector, and trellis quantizers and a resource-constrained mixed allocation.
Its fractional-rate terminology alone does not prove the candidate's exact
non-power-of-two factor-cardinality semantics, hence `AC=UNRESOLVED`.

[FibQuant](https://arxiv.org/abs/2605.11478) uses a fixed random-access vector
label and reports a strict matched-rate vector-code advantage over its scalar
product specialization for its canonical source.  It strengthens the need for
an unrestricted block-code baseline rather than supplying a prefix mechanism.

Ge et al.'s CVPR 2013 Optimized Product Quantization jointly learns a transform
and Cartesian subcodebooks and uses ordinary ADC tables.  It does not assign a
progressive binary meaning to the stored fine index.

Guo et al.'s Adaptive Bit Allocation PQ supplies unequal integer bit counts
and subcodebook sizes.  The publisher text fixes the high-level order as PCA,
principal-component grouping, and greedy bit allocation to minimize ordinary
quantization distortion.  However, the accessible primary text omits most of
§3; the official PDF is access-restricted.  It therefore cannot establish the
absence of label assignment, nested prefixes, a separate coarse objective, or
joint training.  Those four cells remain `U`, rather than inferred `NO`.

[Quicker ADC](https://arxiv.org/abs/1812.09162) Sections 3.1--3.4 cover
irregular 4/5/6-bit PQ granularities, packed layouts, split lookup tables, and
their SIMD costs.  Its subcodebook sizes remain `2^b`, so it does not supply
arbitrary factor cardinalities.

[Derived Codebooks](https://arxiv.org/abs/1905.06900) is the closest ANN
mechanism.  Section 3 trains a 16-bit fine PQ, derives an 8-bit coarse
codebook, reorders fine centroids so a fixed bit subset selects the coarse
cluster, performs the coarse scan, and then refines candidates with the fine
index.  After a fixed bit permutation, its low-bit selector is physically
equivalent to a leading prefix.

[Polysemous Codes](https://arxiv.org/abs/1609.01882) Section 3 first trains PQ
and then learns a bijection from centroid indices to binary labels under
distance or ranking losses.  The same stored code supports fast Hamming
filtering and accurate ADC.  It optimizes all Hamming bits rather than an
explicit leading nested partition, and its training is sequential.

[Riskin et al. 1994](https://doi.org/10.1109/83.287025) assigns binary labels
to a fixed-rate full-search VQ and organizes them as a progressive tree with
intermediate prefix reconstructions.  Its [author-uploaded primary
text](https://www.researchgate.net/publication/3326149_Index_Assignment_for_Progressive_Transmission_of_Full_Search_Vector_Quantization)
is decisive about training order: the original full-rate Voronoi regions stay
fixed; Eq.(1) scores merging them; and each intermediate reconstruction is the
centroid of a union of those regions.  The authors explicitly distinguish this
from generalized Lloyd training: they optimize the decoder for the fixed
encoder, not the encoder for the decoder.  They also state that intermediate
decoding requires no search, only the centroid of the merged region containing
the already selected original region.  Thus `JT=NO` and `QC=YES`: Riskin is a
post-hoc progressive assignment, not joint fine/prefix training.

[Chou, Lookabaugh, and Gray 1989](https://doi.org/10.1109/18.32124) optimize
and prune tree-structured vector quantizers under distortion-rate objectives.
They supply joint hierarchical quantizer design and successive approximation,
but not the fixed full-word ANN lookup interface.  Exact ANN query cost lies
outside that paper's source-coding scope and remains unresolved here.

## 6. Primitive decomposition

| Candidate primitive | Closest existing source |
| --- | --- |
| learned scalar alphabets | Muresan--Effros; Brandt |
| integer cardinality selection | Muresan--Effros; FSQ |
| factorized joint reconstruction | transform coding, PQ/OPQ, FSQ |
| fixed-width stored label | Brandt, PQ, Quicker ADC, Derived, Polysemous |
| learned permutation/index assignment | Riskin, Derived, Polysemous |
| nested prefix partition | Riskin; Derived after bit permutation |
| coarse distance or filtering objective | Riskin, Derived, Polysemous |
| full-word accurate lookup | Brandt/PQ ADC, Derived, Polysemous |
| two-pass scan and reranking | Derived, Polysemous |

Every listed primitive has prior source support.  The only alleged residual is
strict joint optimization of fine factorized representatives/cardinalities and
the prefix ANN objective.

## 7. Composition questions

No inspected source has every matrix column marked `YES`.  Therefore S0 cannot
return `NO_GO_ALREADY_SOLVED` from the current evidence.

Combining FSQ-style factorization with Riskin-style progressive assignment or
Derived-style coarse indexing is structurally straightforward.  Polysemous
also supplies an ANN-specific distance/ranking objective for learned labels.
This is strong evidence pressure toward `NO_GO_DIRECT_COMPOSITION`.

However, the current evidence does not decide whether joint fine/prefix
training introduces a substantive coupled constraint or is merely alternating
optimization of known losses.  That cell is decision-critical, so the protocol
does not permit converting this pressure into a direct-composition verdict.

Derived Codebooks obtains its prefix/two-pass behavior with ordinary
power-of-two PQ.  Thus arbitrary cardinality appears unnecessary to the
prefix mechanism.  This is strong pressure toward
`NO_GO_NOT_AN_A4_SUCCESSOR`, but that outcome also comes after unresolved
mechanism evidence in the frozen precedence.

The possible factorized advantage over block VQ is lower training and model
state, paid for with a restricted reconstruction family.  No quantitative
bound currently establishes a new advantage, so a later cost-only residual
would also require a separate decision after the mechanism cells are resolved.

## 8. Cost crosswalk

Any future candidate would store `B` payload bits per group plus cardinalities,
scalar representatives, validity state, label permutation, prefix partition,
coarse values, and dispatch/offset metadata.

Query work would include `2^p` coarse and `2^B` full table entries per group,
their construction, prefix and full-word extraction, lookup reads,
accumulation, branches, and the accurate-stage admission fraction.

Training must count cardinality search, scalar fitting, permutation search,
prefix partitioning, coarse-value fitting, objective evaluations, restarts,
CPU/wall time, threads, peak/transient memory, emitted model bytes, and
serialization separately.

The mandatory controls remain separately optimized ordinary PQ and
same-capacity two-dimensional block VQ, plus dyadic scalar products, standard
mixed radix, Riskin-style progressive assignment, Derived-style coarse
codebooks, and Polysemous under its native filtering objective.

## 9. Decision

The exact terminal outcome is:

```text
INCONCLUSIVE_MECHANISM_EVIDENCE
```

Riskin's previously unresolved training-order and decoding-path cells are now
resolved.  Decision-critical uncertainty is confined to ABAPQ's `LA`, `NP`,
`CO`, and `JT` cells because its complete §3 method text was not inspectable.
Resolving them could change which of
`NO_GO_ALREADY_SOLVED`, `NO_GO_DIRECT_COMPOSITION`, or
`NO_GO_NOT_AN_A4_SUCCESSOR` applies first.

This outcome is not a novelty pass.  It is also not evidence that the method is
non-novel.  S1 requires `PASS_S0_STATIC_ONLY`, which did not occur, so S1 code,
synthetic execution, data access, and performance work remain unauthorized.

## 10. Evidence classification and checkpoint

Verified evidence:

- Derived Codebooks already embeds a coarse view in a fine PQ label and uses a
  coarse-scan/accurate-refinement pipeline;
- Polysemous learns ANN-oriented binary label assignments while retaining ADC;
- Riskin builds progressive prefix reconstructions after fixing the original
  fine VQ encoder, and intermediate decoding performs no new search; and
- FSQ supplies arbitrary factor products, while FibQuant reinforces the
  unrestricted block-code control.

Inference:

- bit relocation makes Derived's selector equivalent to a physical prefix;
- the proposed combination is likely direct and arbitrary cardinality likely
  unnecessary to the prefix mechanism.

Unresolved uncertainty:

- whether ABAPQ's unavailable complete method contains any label/prefix/coarse
  mechanism or coupling beyond its visible PCA, grouping, and bit allocation;
  and
- whether a state/training-cost property makes the coupling non-compositional.

Scientific code changed: 0 lines.  This decision report is the only evidence
output.  Nothing was compiled or executed, and no experimental result was
reproduced.  Performance remains `PERFORMANCE_NOT_YET_MEASURED`; there is no
timed hot path, instrumentation region, or fair-comparison delta.

# Attempt 4 Successor S0: Prefix-Co-Designed Group-Code Novelty Protocol

Date: 2026-07-22

Branch: `saq-a4-prefix-novelty-gate`

Base: `saq-a4-r0-static-gate@617ad25`

Stage: frozen source-only novelty gate

Execution authority: user-authorized successor work on 2026-07-22

## 1. Why this is a new direction

R0 closed only the claim that the old arbitrary-cardinality encoder could be
inserted into the unchanged SAQ representation and query path.  The user has
now authorized a successor that may change the representation, prefix meaning,
query tables, and scan consumers, and need not remain inside SAQ.

This broader authority does not reopen the old A4-1 or V2 executions.  Their
outcomes remain immutable:

- A4-0 proved only a synthetic `3 x 5` advantage over a dyadic scalar product;
- an unrestricted same-capacity block codebook matched that witness;
- A4-1S stopped because its frozen exact construction-and-evidence pipeline
  projected to `24.170246892361` CPU-hours, above its 24-hour gate;
- that result was not an algorithmic lower bound and produced no natural-data,
  block-codebook, Recall, throughput, or index result;
- V2 stopped as `CRASH_OR_UNKNOWN / START_ONLY`, without scientific evidence;
  and
- R0 produced `NO_GO_UNCHANGED_SAQ_COMPATIBILITY`, not a novelty verdict.

The successor therefore starts from a different falsifiable mechanism rather
than changing the old solver, precision, serialization, machine, or threshold.

## 2. Smallest candidate mechanism

Consider a fixed `B`-bit word for a small group, initially exactly two scalar
coordinates.  Cardinalities `K_1,K_2` satisfy

```text
K_1 K_2 <= S = 2^B.
```

The old A4 address was the standard mixed-radix label

```text
u = z_1 + K_1 z_2.
```

That label supplies a full-word reconstruction but gives its high-order bits
no guaranteed coarse-distance meaning.  The successor may instead learn a
bijection

```text
pi: (z_1,z_2) -> {0,...,K_1 K_2-1}
```

and a nested partition of the full labels.  The first `p` physical bits select
one of `2^p` coarse groups; all `B` bits select the final reconstruction.

Training jointly chooses:

1. scalar representatives and their cardinalities;
2. the assignment of joint reconstructions to full words;
3. the nested partition induced by the first `p` bits; and
4. the coarse representatives or query-table values used by the first pass.

The intended query interface is:

```text
fast pass:      read p prefix bits, perform one coarse lookup per group
accurate pass:  read the complete B-bit word, perform one full lookup per group
```

The scientific object is the joint optimization of prefix geometry and full
reconstruction under a factorized model.  Arbitrary cardinalities, learned
scalar quantizers, mixed-radix addressing, bit allocation, and lookup tables
alone are explicitly not candidate contributions.

## 3. Smallest falsifiable question

> Does jointly designing the nested prefix and full-word geometry create a
> query-unaware, fixed-rate two-stage ANN code that is not already supplied by
> progressive or tree-structured vector quantization, product-code index
> assignment, binary filtering, derived codebooks, or their direct composition
> with a known factorized arbitrary-level codebook?

S0 is a novelty and mechanism-coherence gate.  It does not ask whether the
candidate reduces reconstruction error on a dataset.

The cheapest decisive check is a primary-source claim matrix.  No code or data
is justified until that matrix leaves one concrete, non-compositional delta.

## 4. Closest-work set

The review must inspect the primary paper, not only a secondary description,
for at least the following families.

### 4.1 Scalar, transform, and arbitrary-level coding

- Muresan and Effros, *Quantization as Histogram Segmentation*, DCC 2002:
  exact fixed-rate and entropy-constrained scalar quantization.
- Brandt, *Transform Coding for Fast Approximate Nearest Neighbor Search in
  High Dimensions*, CVPR 2010: PCA, learned scalar quantizers, integer bit
  allocation, packed codes, and ANN lookup tables.
- Mentzer et al., *Finite Scalar Quantization*, ICLR 2024: implicit product
  codebooks from small scalar level sets.
- Lee and Song, *Q-Palette*, 2025: fractional-bit scalar, vector, and trellis
  quantizers plus mixed allocation.
- Lee and Kim, *FibQuant*, 2026: dense fixed-rate random-access vector coding
  and an explicit vector-code advantage over scalar products.

### 4.2 Product quantization and scan organization

- Ge et al., *Optimized Product Quantization*, CVPR 2013: learned transform,
  space decomposition, and product codebooks.
- Guo et al., *Adaptive Bit Allocation Product Quantization*, Neurocomputing
  2016: unequal bit and codebook allocation among subspaces.
- Andre, Kermarrec, and Le Scouarnec, *Quicker ADC*, TPAMI 2021: irregular
  granularities, split tables, and SIMD consequences of lookup width.
- Andre, Kermarrec, and Le Scouarnec, *Derived Codebooks for High-Accuracy
  Nearest Neighbor Search*, 2019: approximate first-pass codebooks followed by
  accurate high-cardinality refinement.

### 4.3 Prefix, hierarchy, and dual code meanings

- Douze, Jegou, and Perronnin, *Polysemous Codes*, ECCV 2016: product-code
  label assignment with both Hamming filtering and asymmetric distance use.
- Riskin, Ladner, Wang, and Atlas, *Index Assignment for Progressive
  Transmission of Full-Search Vector Quantization*, IEEE Transactions on
  Image Processing 3(3), 1994, DOI `10.1109/83.287025`: binary index
  assignment, a full-search progressive-transmission tree, and intermediate
  reconstructions for the prefixes of a final full-search VQ label;
- Chou, Lookabaugh, and Gray, *Optimal Pruning with Applications to
  Tree-Structured Source Coding and Modeling*, IEEE Transactions on
  Information Theory 35(2), 1989, DOI `10.1109/18.32124`: the frozen
  tree-structured/pruning comparator for hierarchical quantizer design; and
- any primary ANN work found by backward and forward citation inspection that
  learns a coarse view of a fine codebook or reuses one stored label in a
  two-stage scan.

The review may add a source only because it is directly adjacent to one of
these mechanisms.  It must not become a broad literature survey.

## 5. Frozen claim matrix

For every source, record source-supported answers to exactly these columns:

| Column | Meaning |
| --- | --- |
| Fixed word | one random-access, fixed-length database label |
| Factorized reconstruction | Cartesian product of smaller learned alphabets |
| Arbitrary cardinality | a factor may have a non-power-of-two number of states |
| Learned full-label assignment | codeword-to-bit-label mapping is optimized |
| Nested prefix | leading bits define an explicit coarse partition |
| Coarse objective | prefix geometry is optimized for distance/ranking/filtering |
| Full lookup | the same stored label supports accurate table-based scoring |
| Joint training | prefix and full reconstruction objectives are coupled |
| State cost | permanent codebook, mapping, and dispatch state |
| Query cost | table construction, bytes read, lookups, branches, and reranking |

Each cell is one of `YES`, `NO`, or `UNRESOLVED`, with a page, section, or
equation location.  An abstract alone is insufficient for a decisive `NO`.

## 6. Candidate decomposition test

The report must write the candidate as a list of primitives and map every
primitive to the closest source:

```text
learned scalar alphabets
integer cardinality selection
factorized joint reconstruction
fixed-width label
permutation or index assignment
nested prefix partition
coarse distance/filter objective
full-word lookup
two-pass scan and reranking
```

Then apply these questions in order:

1. Does one primary work already contain the entire mechanism?
2. If not, does one work provide the factorized code and another provide a
   representation-independent label/prefix optimization that composes without
   a new constraint, lemma, algorithm, or cost trade-off?
3. Does replacing an unrestricted block codebook by a factorized one change
   anything except model size, training cost, or reconstruction quality?
4. Is the proposed prefix objective merely Polysemous-style label assignment,
   progressive VQ index assignment, or a derived coarse codebook applied to
   known factorized centroids?
5. What property requires arbitrary cardinalities?  Would the same mechanism
   work unchanged for dyadic scalar products or ordinary PQ?
6. What measurable advantage could a same-capacity block codebook not obtain
   under the same prefix and full-lookup budget?

If arbitrary cardinality can be removed without removing the claimed prefix
mechanism, the result is not an Attempt 4 successor.  If factorization supplies
only cheaper metadata/training, that trade-off must be quantitatively testable
and cannot be described as a new coding primitive.

## 7. Gate outcomes

Apply the first matching outcome:

| Condition | Outcome |
| --- | --- |
| A required primary source cannot be identified or inspected | `INCONCLUSIVE_SOURCE_GAP` |
| Any decision-critical matrix cell remains unresolved after inspection | `INCONCLUSIVE_MECHANISM_EVIDENCE` |
| One source already contains the candidate mechanism | `NO_GO_ALREADY_SOLVED` |
| Candidate is a direct composition with no new coupling | `NO_GO_DIRECT_COMPOSITION` |
| Arbitrary cardinality is unnecessary to the residual mechanism | `NO_GO_NOT_AN_A4_SUCCESSOR` |
| Only an unquantified metadata/training trade-off remains | `INCONCLUSIVE_COST_ONLY` |
| One non-compositional mechanism and falsifiable advantage remain | `PASS_S0_STATIC_ONLY` |

`PASS_S0_STATIC_ONLY` establishes no correctness, natural-data value, Recall,
throughput, or publication claim.  It permits only writing a separately frozen
tiny synthetic protocol.

The report must separate verified evidence, inference, and uncertainty.  A
lack of a novelty proof is not evidence of direct composition.

## 8. Required cost model for any surviving mechanism

Even at S0, the proposed advantage must name every resource later measured.

Database state:

- exactly `B` payload bits per group;
- alignment and padding if prefix and suffix are physically separated;
- any per-vector mode, plan, or validity field.

Permanent model state:

- `K_1,K_2` and used-state count;
- `K_1+K_2` scalar representatives;
- an `S`-entry permutation or a proved smaller equivalent;
- nested-partition/coarse representatives;
- dispatch, offset, or group-plan metadata.

Construction and training:

- algorithm and objective-evaluation counts for cardinality search, scalar
  fitting, label permutation, nested partitioning, and coarse reconstruction;
- CPU time, wall time, thread count, peak resident memory, and separately
  bounded transient/owned memory;
- initialization, restart, iteration, convergence, and early-stop rules; and
- emitted model bytes and serialization work, reported separately from the
  scientific optimizer.

Per-query state and work:

- `2^p` coarse entries plus `S` full entries per group;
- exact table-construction operations and binary32 bytes;
- prefix extraction, full-word extraction, table reads, accumulation, branches,
  and candidate reranking;
- bytes read in both stages and the fraction reaching the accurate stage.

Every structural baseline must receive the same prefix/index-assignment
optimization opportunity as the candidate.  The mandatory comparisons are:

- a same-capacity block codebook with the same prefix/full-label budget and
  two-pass schedule;
- dyadic scalar products and ordinary PQ with matched learned label/prefix
  assignment rather than their natural binary numbering;
- Riskin-style progressive index assignment over the matched fine codebook;
- a derived-coarse-codebook two-pass construction with the same coarse-table
  and reranking budget; and
- Polysemous Codes under its native Hamming-filtering objective.

Polysemous may be omitted from a later numeric gate only after a
source-supported, independently reviewed non-applicability finding.  Any other
omitted structural control likewise requires an explicit reviewed
justification before outcomes are observed.

## 9. Conditional S1 boundary

S1 is not authorized unless S0 returns `PASS_S0_STATIC_ONLY` and that report
passes independent review.

The cheapest possible S1 would freeze only `r=2`, `B=4`, and one prefix width
`p=2`, using a finite synthetic source whose atoms and query-like directions
are declared before execution.  Every arm would receive matched
prefix/index-assignment optimization.  It would exhaustively compare:

1. word-local dyadic scalar products;
2. standard arbitrary-cardinality mixed radix;
3. ordinary PQ;
4. the same-capacity two-dimensional block codebook;
5. Riskin-style progressive index assignment;
6. a derived-coarse-codebook two-pass construction;
7. Polysemous under its native filtering objective, unless reviewed as
   inapplicable before execution; and
8. the prefix-co-designed factorized candidate.

The candidate would stop if it cannot improve prefix-stage absolute distance
or pair ordering at identical prefix reads and lookup count, if full-word
quality does not preserve the known arbitrary-over-dyadic witness, or if block
VQ obtains equal or better two-stage quality without a material state/training
disadvantage.

S1 would be `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`.  No ANN benchmark query,
natural-data result, optimized kernel, or SOTA statement would be permitted.

## 10. Work budget and stop condition

S0 uses ordinary paper/source inspection and one Markdown decision report.
No code, custom crawler, schema, runner, verifier, artifact bundle, dataset,
result directory, cache, index, benchmark query, or runtime-state path may be
created or opened.

Expected output is 180--280 report lines.  Scientific implementation is zero
lines.  Stop after 8 hours, 35 tool calls, or 320 report lines without a
decision.  One independent reviewer receives the immutable decision commit,
the frozen matrix, and the exact source list.  At most one bounded repair and
rereview is allowed.

The earliest stop is a source-supported direct-composition finding.  The next
user checkpoint occurs after the reviewed S0 decision.  No S1 implementation,
data access, or numerical experiment is authorized by this protocol alone.

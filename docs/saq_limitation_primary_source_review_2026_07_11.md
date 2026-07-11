# Bounded Primary-Source Review of Remaining SAQ Limitations

Date: 2026-07-11

Post-review status: the bounded `C6` oracle gate subsequently failed official
source parity. The review's conditional GO is therefore closed under its
frozen contract; no dataset screen followed. See
`docs/saq_caq_co0a_official_source_parity_2026_07_11.md`.

## Decision

The review does **not** support opening a broad new direction around certified
progressive bounds, streaming updates, filtered search, physical code layout,
or arbitrary multi-bit prefixes. Those mechanisms are either occupied by
closely related primary work, contradicted by the repository's completed
negative evidence, or disconnected from SAQ's current search path.

One SAQ-specific premise survives, but only as a bounded falsification study:

```text
Does finite-round CAQ code adjustment leave a material, segment-amplified gap
to the exact E-RaBitQ grid-on-sphere objective under SAQ's heterogeneous
short/high-bit segments?
```

The portfolio decision is therefore:

```text
C1 certified progressive bounds          NO-GO
C2 streaming updates / plan drift        NO-GO
C3 filtered / hybrid selectivity         NO-GO
C4 physical layout / tiered storage      NO-GO
C5 arbitrary 2..B-bit prefix consistency NO-GO
C6 finite-round CAQ optimality            CONDITIONAL GO: oracle gate only
```

`C6` is not yet a method, branch-level contribution, or publication claim. A
small query-unaware oracle screen is justified; method development is not.

## Bounded Review Contract

The scope was frozen before selecting a survivor:

- cutoff: 2026-07-11;
- primary papers and official artifacts only;
- at most 36 unique sources;
- six predeclared candidate families, `C1`--`C6` above;
- local SAQ paper/source reviewed in full;
- recent preprints treated as novelty collisions, not as established results;
- prior SAQ branches used as empirical boundary evidence, not as sources of new
  code or claims.

The auditable source ledger is
`docs/saq_limitation_primary_sources_2026_07_11.json`. It records the inclusion
rule, review depth, primary URL, candidate mapping, and review limits.

The review did not search indefinitely for an idea. It stopped once each
candidate had either a direct mechanism collision, an architectural conflict,
or one specific unresolved SAQ premise and a falsifiable gate.

## Repository Evidence That Constrains A New Direction

The following completed studies remove several apparently easy continuations:

| Historical line | Relevant result | Boundary for this review |
|---|---|---|
| empirical fixed policies / boundary work | Small local gains required policy choices and did not establish a general mechanism | Do not reopen empirical stage scoring or threshold calibration |
| mixed shared local plans | GIST recall moved from `0.94469` to `0.94548`, but QPS fell from `2677.16` to `2434.73`; mixed plan preparation dominated | No per-cluster plan IDs or mixed dispatch |
| static global cost DP | The default plan was not dominated across the available dataset/budget matrix; two near-frontier GIST plans were slower end to end | Code volume, positive dimensions, and segment count are inadequate objectives |
| planner-objective analysis | A `fac_error` plan changed structure but lost its speed advantage before matching recall | Do not turn a measured encoder statistic directly into another weighted planner |
| graph traversal analysis | The accurate first SAQ segment improved local ordering but cost `52.5x` the source-aligned SymphonyQG estimator, or `26.8x` after implementable grouping | No graph-layout rescue or full graph integration |
| full-dimensional transform replacement | The preregistered CIFAR replication failed to reproduce the small GIST residual-PCA estimator effect | No new full-D basis objective |
| lossy projection LP-0 | Even the exact `d=576` tail-norm surrogate had worse agreement and more boundary inversions than native SAQ | No dimension/budget/tail sweep after the failed registered point |

These results do not prove that SAQ has no limitation. They require the next
question to act on a different core premise and to survive a small gate before
new index or query-path work.

## What The SAQ Primary Source Actually Leaves Open

Three statements in the SAQ paper are important to separate.

### 1. CAQ's inherited guarantee is conditional

SAQ proves that CAQ and E-RaBitQ have equivalent codebooks up to normalization.
It then states that CAQ inherits the RaBitQ unbiased estimator and error bound
**if** it solves the discrete cosine-maximization problem. The paper explicitly
acknowledges that its coordinate-descent-style algorithm need not reach the
optimum and supports equivalence empirically instead.

This condition affects every full-code CAQ estimate. Current source makes the
approximation concrete:

```text
default adjustment rounds: 6
per-vector stored rescale/error factors: computed from the code actually found
```

The stored factor reflects the achieved alignment, so non-optimal encoding does
not automatically imply a wrong factor. The unresolved question is whether the
finite-round code is sufficiently aligned for the claimed E-RaBitQ-equivalent
accuracy/bound premise, particularly after SAQ creates segments with very
different dimensions and bit widths.

The implementation narrows the systems claim further. The full-code estimator
consumes the achieved code and `rescale`; `fac_error` is packed into
`ExFactor.error` but is not read by the current search path. Consequently, a
smaller oracle error factor alone would have no deployed benefit. Any viable
limitation must also improve a frozen distance-estimation proxy and eventually
held-out ranking without adding query work.

### 2. The paper already reports a small optimizer gap

The paper compares code-adjustment rounds with an optimal RaBitQ code. It says
that error improves rapidly, but at `B=4, r=32` remains `0.7%` worse than the
optimal arm, and recommends `r in [4,8]` as an efficiency/accuracy balance.

This prevents overclaiming that the gap is newly discovered. The missing
evidence is narrower:

```text
whether the production r=6 gap becomes systematic or materially larger inside
SAQ's short, high-bit residual segments, and whether a cheap certificate or
repair exists that is not merely E-RaBitQ fallback.
```

### 3. Arbitrary prefixes are empirical and are not used by current IVF SAQ

The paper reports that truncating a native `B`-bit CAQ code to `b` bits has
nearly the error of native `b`-bit CAQ, with a visible small penalty for
`2 <= b <= 4` because the full-code factor is reused. This is empirical, not a
successive-refinement guarantee.

However, the checked-in IVF path does not consume these intermediate bit
depths. It executes:

```text
variance-only estimate
-> first/MSB bit for each segment
-> all remaining B-1 bits for one segment at a time
```

It can stop between segments, not between bit planes within a segment. A
`2..B` prefix project would first require a new packed layout and search
schedule, so it does not explain a current SAQ bottleneck.

## Candidate Review

### C1: Certified Progressive Bounds — NO-GO

Closest primary mechanisms:

- RaBitQ supplies an unbiased quantized estimator and a sharp probabilistic
  error bound.
- E-RaBitQ extends the codebook to arbitrary per-coordinate bit widths and uses
  bound-driven MSB/full refinement.
- ADSampling supplies progressive, high-probability distance-comparison
  operations with query-level union-bound reasoning and IVF/HNSW integration.
- DADE supplies base-data PCA prefixes, hypothesis tests, and adaptive
  per-candidate work.
- MRQ directly combines a RaBitQ-quantized PCA head, a residual-tail bound, and
  three IVF refinement stages.
- SymphonyQG shows that quantized estimates and bounds can guide graph
  traversal.
- TurboQuant is a mandatory fast, theoretically analyzed random-rotation
  quantizer control.

SAQ's current segment-tail rule is weaker than a query certificate. Its
Chebyshev statement is marginal over a data-vector distribution; `m` is set to
`2` on GIST and `4` elsewhere; it does not account for a fixed candidate, an
entire top-k query, or repeated adaptive decisions. Current fast code also uses
fixed one-bit constants (`0.58` and `0.8`) rather than each code's full error
factor.

Making this globally reliable would likely combine an existing quantization
interval with ADSampling/DADE-style repeated-test control and MRQ-style tail
bounds. A direct union bound over `M` candidates and `S` segment decisions
would require a Chebyshev scale on the order of `sqrt(MS/delta)`, an inference
that predicts very conservative pruning. Replacing it with empirical tails
approaches DADE; query calibration violates the current contract.

Reviewer objection:

> This is RaBitQ/E-RaBitQ error plus an ADSampling/DADE progressive test and an
> MRQ residual bound, applied segment by segment. What is the new principle?

Decision: do not develop a global certified search path. The upstream CAQ
optimality condition is more specific and must be resolved first.

### C2: Streaming Updates And Plan Drift — NO-GO

OnlinePQ and OnlineOPQ already cover incremental codebooks and rotations.
DeDrift, SPFresh, and Ada-IVF cover coarse-partition drift and local repair.
Streaming LVQ is especially important negative evidence: in its tested drift
regimes, freezing global LVQ state nearly matched repeated full re-encoding, so
model staleness alone did not establish a search limitation. CoDEQ then creates
a strong recent collision by targeting dynamically consistent data-dependent
product-style quantization with bounded update I/O.

The apparently SAQ-specific issue is backward compatibility of a global
variance-ordered, variable-width plan. Changing PCA coordinates, segment
boundaries, or bit widths changes the meaning of old code bits. Under the
current no-version/no-mixed-dispatch architecture, the available choices are a
full rewrite or a dual representation. They imply full re-projection and CAQ
encoding, or nearly doubled state plus migration and two query paths.

Reviewer objection:

> First prove that SAQ's heterogeneous plan degrades more than uniform CAQ,
> PQ, or LVQ after controlling coarse-IVF drift. Otherwise this is OnlineOPQ,
> DeDrift, or CoDEQ composed with SAQ.

Decision: no dynamic-SAQ method or branch. A timestamped oracle decomposition
could be used later only to close the question, not to authorize a migration
system without a code-compatible plan update mechanism.

### C3: Filtered And Hybrid Search — NO-GO

AnalyticDB-V and VBASE already make selectivity, pre/post-filter order,
candidate amplification, and termination physical-plan decisions.
Filtered-DiskANN and ACORN show that filtering changes graph connectivity and
candidate generation. DADE already adapts distance depth per candidate. E2E
uses early filter and distance signals to learn an adaptive search budget, and
a recent PVLDB evaluation establishes pass rate, correlation, and filtering
strategy as mandatory controls.

For a fixed candidate stream, selectivity changes SAQ through metadata-check
order, top-k heap fill, and survivor count. These are generic execution effects;
SAQ already responds to the current heap threshold.

A narrower correlation question exists: predicate-conditioned vectors may
violate a global segment-variance model even after pass rate is held fixed.
But per-predicate statistics scale with label cardinality, Boolean predicates
do not compose cleanly, and the design approaches prohibited plan identities.

Reviewer objection:

> Filtering changes the candidate stream and heap, not the quantizer. Why is
> this not an SAQ distance operator inside an existing filtered scheduler?

Decision: filtered workloads remain evaluation cases, not a new SAQ method.

### C4: Physical Layout, SIMD, And Tiered Storage — NO-GO

PQ Fast Scan, Quick ADC, Quicker ADC, and Bolt already establish register
lookup, grouped code layout, irregular bit widths, split tables, and fast
encoding as a mature hardware-aware quantization space. AiSAQ moves compressed
graph state to SSD. FaTRQ already couples progressive residual quantization,
tiered far memory, provable early stopping, and a CXL-side accelerator.
SymphonyQG and NGT-QG occupy sequential neighbor-side codes for graph search.

SAQ could still be re-packed, but a generic segment-contiguous or tiered
layout would be an engineering application of these mechanisms. The completed
graph work also found that implementable grouping left the accurate SAQ prefix
`26.8x` slower than the source-aligned packed baseline; ideal scheduling would
require graph-specific duplication already occupied by SymphonyQG.

Reviewer objection:

> The contribution is a known SIMD/tiered-code layout specialized to SAQ, and
> prior repository evidence shows the remaining overhead is not just packing.

Decision: no layout-only direction. Layout changes may support a future
mechanism but cannot be its primary claim.

### C5: Arbitrary Multi-Bit Prefix Consistency — NO-GO

Classical multiresolution and successive-refinement vector quantization, and
recent nested quantization, already occupy the generic idea of one embedded
code serving multiple precisions. SAQ itself evaluates sampled versus native
CAQ bit depth and acknowledges the low-bit factor mismatch.

More decisively, current IVF SAQ uses only one bit and then the full segment
code. Improving `b=2..B-1` cannot improve the checked-in path without first
inventing a new layout and scheduling policy, which re-enters the already
negative small search-procedure line.

Decision: do not run a prefix-consistency gate. It may be a secondary
diagnostic only if a future method independently requires intermediate bit
planes.

### C6: Finite-Round CAQ Encoding Optimality — CONDITIONAL GO

This is the only candidate tied to an unresolved premise used by every SAQ
full-code representation:

```text
E-RaBitQ: exact grid-on-sphere objective, theoretical guarantee, expensive
CAQ:      O(rD) coordinate adjustment, production r=6, no optimum guarantee
```

It is distinct from the retired planner-objective line. That line asked whether
measured `fac_error` should re-rank complete segment/bit plans and found no
recall-matched gain. `C6` holds the plan fixed and asks whether CAQ actually
finds the intended codeword within each fixed segment.

Because current search does not consume the stored error factor, `C6` cannot
pass on a bound-width improvement alone. The achieved code/rescale must improve
base-only distance estimation under the fixed estimator; otherwise the result
is theoretical validation with no present systems mechanism.

It is also not unoccupied. E-RaBitQ supplies the exact oracle; LVQ supplies the
initial code; LSQ++ demonstrates mature local-search encoding; TurboQuant is a
fast analyzed alternative; and SAQ already reports a small average gap. The
only defensible next action is therefore an oracle diagnostic focused on the
SAQ-created heterogeneous segment regime.

The separate go/no-go memo defines that gate and its stop rules.

## Review-Level Go/No-Go

The review authorizes only the following sequence:

1. review and pin the official E-RaBitQ encoder;
2. write a base-only preregistration for a small per-segment oracle comparison;
3. run no held-out benchmark queries unless the base-only limitation gate
   passes and a later evaluation protocol has already frozen the mechanism;
4. stop if the gap is rare, small, not amplified by SAQ's segment regime, or
   repairable only by ordinary E-RaBitQ fallback.

No new index format, planner, query scheduler, graph integration, filter
policy, streaming protocol, or projection sweep is authorized by this review.

## Limitations And Non-Claims

- This is a bounded novelty/limitation review, not a systematic literature
  review.
- Recent preprints may change before publication.
- Full E-RaBitQ text could not be retrieved in the current network session; its
  exact formulation is reviewed through primary metadata and the reproduction
  in the local SAQ primary source. Official-source parity is mandatory before
  an oracle result.
- The review does not claim that CAQ is inaccurate, biased, or unsafe in the
  deployed system. The stored factor is based on the achieved code; the open
  question is the magnitude and consequence of objective regret.
- A positive oracle gap would establish a limitation, not a publishable method.

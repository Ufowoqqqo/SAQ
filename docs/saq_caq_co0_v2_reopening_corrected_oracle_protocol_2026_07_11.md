# CO-0 v2 Reopening Decision and Corrected-Oracle Protocol

Date: 2026-07-11

## Decision

```text
v1 official-source contract: CLOSED / FAIL
v2 protocol design: COMPLETE
v2 oracle implementation: NOT AUTHORIZED BY THIS NOTE
GIST/CIFAR data access: NOT AUTHORIZED
CAQ method development: NOT AUTHORIZED
```

The decision is a **conditional reopen for one independently validated oracle
gate**, not a reversal of the `CO-0A` result. The pinned official
Extended-RaBitQ implementation remains non-exact and width-incompatible for
the frozen SAQ plans. Its failure is preserved in
`docs/saq_caq_co0a_official_source_parity_2026_07_11.md`.

The revised study is scientifically permissible because no GIST/CIFAR encoder
gap or held-out-query result has been inspected. The measurement instrument is
changed before data access, and the new instrument is named explicitly:

```text
independent complete-event oracle for the E-RaBitQ/CAQ direction codebook
```

It must never be described as the pinned official encoder. The broad idea of
exact scale/event search is prior E-RaBitQ work and is not a contribution. The
only research question retained is whether SAQ's own heterogeneous
short/high-bit segmentation amplifies the known finite-round CAQ optimization
gap enough to motivate a later low-overhead mechanism.

## Why Reopening Is Bounded But Defensible

The v1 failure did not test the research null. It showed that the selected
official executable artifact could not supply the required exact labels:

- it did not score its initialized code state;
- its public width set omitted frozen-plan widths; and
- its byte output narrowed legal `B=11` magnitudes.

At the same time, the independent complete-event enumerator agreed with
complete tiny codebooks in all 109 tested cases, and the centered-grid mapping
between CAQ and E-RaBitQ passed all 48 fixtures. These synthetic, data-free
facts justify specifying a new oracle contract. They do not justify running a
dataset experiment until the stronger obligations below pass and are
committed.

A strict reviewer can still reject the direction as follows:

> SAQ already acknowledges that coordinate adjustment is approximate, while
> E-RaBitQ already defines the exact encoder. Measuring another optimizer gap
> is validation, not a database contribution.

The work can survive only if all later evidence shows that:

1. the gap is materially amplified by SAQ-created segment geometry rather
   than being generic whole-vector CAQ behavior;
2. the unchanged full-code estimator, not only the unused stored error factor,
   improves under exact labels;
3. ordinary continuation of the same coordinate rule does not remove the
   material gap; and
4. a later certificate or repair can move the build-time/error frontier
   without changing index bytes or query work.

This protocol evaluates only Items 1--3. A positive result establishes a
limitation and authorizes a separate method review; it is not itself a paper
contribution.

## Frozen Architecture

The v2 study changes only the per-segment encoder used to label a fixed
residual. It freezes:

```text
PCA view and IVF assignments
residual vectors
one dataset-level SAQ segment/bit plan
segment rotations, dimensions, and padding
serialized code width and factor schema
full-code estimator and query-side work
no per-cluster plans or mixed query dispatch
no benchmark-query tuning
```

The exact oracle is offline experimental infrastructure. It is not a proposed
index encoder and its cost must not be omitted.

## Exact Objective

Let `o in F32^D` be a nonzero rotated residual segment and let `B` be the total
number of stored bits per dimension, including the sign bit. Define

```text
a_i = |o_i|
L   = 2^(B-1)
k_i in {0, ..., L-1}
z_i = k_i + 1/2.
```

For nonzero coordinates, an optimal signed code uses the sign of `o_i`.
Therefore the exact direction objective is

```math
C(k;o)=
\frac{\sum_i a_i z_i}
     {\sqrt{\sum_i a_i^2}\sqrt{\sum_i z_i^2}}.
```

The oracle maximizes `C`, equivalently `C^2`. The factor
`sum_i a_i^2` is constant for one input, so code comparisons require only

```math
Q(k;o)=\frac{(\sum_i a_i z_i)^2}{\sum_i z_i^2}.
```

For `s_i in {-1,+1}`, the centered CAQ integer code is obtained with

```text
c_i = L + k_i       when s_i = +1
c_i = L - 1 - k_i   when s_i = -1,
```

which gives

```math
c_i+\tfrac12-L=s_i(k_i+\tfrac12).
```

CAQ's decoded vector is therefore a positive scalar multiple of the signed
grid vector. This preserves cosine, `fac_rescale`, and the unchanged full-code
inner-product estimator.

### Zero and degenerate inputs

- If `a_i=0`, fix `k_i=0` and the positive sign convention. Any sign is
  objective-tied, while a larger magnitude only increases the code norm.
- Padded zero lanes remain part of `D`, use `k_i=0`, and contribute their
  unavoidable half-grid norm.
- If the complete residual is zero, record it in a separate degenerate stratum
  and do not define an angular regret. It cannot contribute to a positive gate.

No data-dependent epsilon is introduced for these cases.

## Corrected Complete-Event Oracle

### Scale reduction

For any fixed grid vector `z`, introduce a positive scalar `alpha`:

```math
H(\alpha,z)=2\alpha\langle a,z\rangle
             -\alpha^2\lVert z\rVert_2^2.
```

Maximizing over `alpha` gives

```math
\max_{\alpha\ge0} H(\alpha,z)
=\frac{\langle a,z\rangle^2}{\lVert z\rVert_2^2}=Q(z;a).
```

For fixed `alpha`, maximizing `H` is coordinate-separable. With
`t=1/alpha`, each magnitude is the nearest half-integer to `t*a_i`, clipped
to the legal range:

```text
k_i(t) = clip(floor(t * a_i), 0, L-1).
```

The code changes only at events

```text
t = j / a_i,  j in {1, ..., L-1},  a_i > 0.
```

Consequently, scoring the initial all-zero magnitude code and every state
after these events covers an optimizer of `Q`. Equal events are ordered by
coordinate id and every intermediate state is scored. This may score extra
feasible tie states, but cannot exceed the global codebook optimum; at least
one optimal tie state remains on the event path.

### Exact binary32 arithmetic

The v2 oracle must not inherit the official `1e-5` epsilon, bounded scale
window, or `uint8_t` magnitude representation.

Each nonnegative binary32 magnitude is decomposed exactly as

```text
a_i = A_i * 2^e,
```

using one common exponent `e` and a nonnegative arbitrary-precision integer
`A_i`. The common power of two cancels from all comparisons.

Event ordering is exact:

```text
j_1 / a_p < j_2 / a_q
iff
j_1 * A_q < j_2 * A_p.
```

For objective comparison, use the odd integer grid

```text
g_i = 2*k_i + 1
S   = sum_i A_i*g_i
N   = sum_i g_i^2.
```

Because the constant factors cancel,

```text
Q_1 > Q_2
iff
S_1^2 * N_2 > S_2^2 * N_1.
```

All products and sums in these comparisons use arbitrary-precision integers.
When coordinate `i` advances by one magnitude level,

```text
g_i <- g_i + 2
S   <- S + 2*A_i
N   <- N + 4*g_i_old + 4.
```

The selected magnitude and centered CAQ codes use `uint32_t`, which covers
the frozen `B=11` domain without narrowing. Floating cosine and factor values
are derived only after the exact winning code is fixed; they are reported
alongside the exact rational comparison state.

### Exactness obligations

The implementation is not accepted merely because it reproduces the current
long-double enumerator. A proof appendix and tests must establish:

1. the scale-reduction lemma for the finite half-integer codebook;
2. coverage of the initial state and every finite event interval;
3. the equal-event argument and deterministic tie rule;
4. exact binary32 decomposition and cross-product ordering;
5. exact objective comparison without square roots;
6. the sign/magnitude-to-CAQ mapping, including zero and padded lanes; and
7. absence of overflow or narrowing for every frozen bit width.

## Complexity and Overhead

Let

```text
D_+ = number of nonzero coordinates
E   = D_+ * (L-1)
L   = 2^(B-1).
```

Using one next-event entry per nonzero coordinate in a heap gives:

```text
event count:        E
heap operations:    O(E log D_+)
state memory:       O(D)
output memory:      O(D)
persistent index:   0 additional bytes
```

If `W` is the maximum arbitrary-precision integer width and `M(W)` is the
integer multiplication cost, the bit-operation bound is

```text
O(E log D_+ * M(W)),
```

plus lower-order exact additions. This cost is exponential in `B` and is
acceptable only for a bounded offline oracle sample. It is not hidden behind
the ordinary-RAM operation count.

Every run must record event count, heap comparisons, exact objective
comparisons, integer-width high-water mark, elapsed time, CPU time, and peak
resident memory. These are experimental-label costs, not deployable overhead.

## Authorization Sequence

The stages are strictly ordered. A later stage is not authorized until the
previous result and its hashes are committed.

### V2-A0: specification review

Before implementation:

- review the proof obligations above line by line against E-RaBitQ's known
  scale-search result;
- confirm that the oracle is only a measurement instrument and not claimed as
  novel;
- freeze the binary32, zero, tie, padding, and bit-width semantics; and
- assign a protocol version and output schema.

**Pass:** no mathematical or representation ambiguity remains.

**Stop:** exactness still depends on a floating epsilon, empirical window, or
unsupported code type.

### V2-A1: implementation validation

Use synthetic inputs only:

1. complete codebook enumeration for `D in {2,3,4}` and total
   `B in {2,3,4}`;
2. the existing 109 deterministic fixtures;
3. the reachable `D=64, B=3` initialized-state counterexample;
4. exact zero, repeated-magnitude, equal-event, padding, subnormal, and largest
   finite binary32 fixtures;
5. `B=11` fixtures whose legal magnitudes exceed 255;
6. independent CAQ code, cosine, rescale, and estimator recomputation; and
7. Release plus sanitizer/debug execution.

The exact oracle must match complete brute force on every enumerable case.
Tests may not be weakened because the official source fails them.

### V2-A2: synthetic cost study

After V2-A1 passes, measure the oracle only on non-dataset synthetic binary32
vectors at the frozen plan cells:

```text
GIST:  (D,B) = (64,11), (192,6), (320,4), (256,2), (832,4)
CIFAR: (D,B) = (64,9),  (192,5), (128,3), (384,4)
```

The final sample size and machine-time ceiling must be chosen from this cost
study, documented as an experimental resource decision, and committed in the
V2-B preregistration. Dataset magnitudes may not be used for that choice.

**Pass:** the predeclared two-dataset sample can be labeled within the stated
resource ceiling without changing cells or dropping `B=11`.

**Stop:** the exact labels are infeasible unless the study removes the leading
segment, narrows bits, or selects easy vectors.

### V2-B0: final base-only preregistration

Only after V2-A0--A2 pass, write and commit a separate preregistration that
freezes:

- dataset and artifact hashes;
- sample size derived from V2-A2;
- deterministic sample ids and pair inventory hashes;
- rotation seeds and generated rotation hashes;
- all encoder arms, controls, metrics, statistical tests, and output schema;
- full commands, compiler flags, and resource accounting; and
- the decision rule below without modification.

Do not run V2-B in the same step that writes the preregistration.

### V2-B1: frozen base-only limitation screen

Only V2-B1 may read the specified base/index artifacts. It must not read
benchmark queries or ground-truth neighbors.

## Frozen Data Regimes

The regimes come from historical plans recorded before this direction:

```text
GIST sample50k, K=512, nominal B=4:
  64@11 | 192@6 | 320@4 | 256@2 | 128@0

CIFAR60k, K=512, nominal B=4:
  64@9 | 192@5 | 128@3 | 128@0
```

No other dataset, `K`, nominal budget, bit width, dimension boundary, or plan
may be introduced after V2-B0 to rescue the result.

Use three fixed segment-rotation seeds `{0,1,2}`. Three is the minimum bounded
set that permits a direction-consistency check beyond a two-seed comparison;
the values are fixed before data access and are not method parameters.

### Deterministic cluster-stratified sample

After V2-A2 fixes total sample size `n`, allocate samples to IVF cells in
proportion to cell population using deterministic largest-remainder rounding.
Within each cell, order vector ids by

```text
SHA256(protocol_version || dataset_id || cell_id || vector_id)
```

and take the first allocated ids. Persist the complete inventory and hash it
before encoding any arm.

For the base-only estimator proxy, use only ids already in the main sample.
Within each cell, keep the same hash order and pair consecutive selected ids
without reuse. The first residual supplies the stored code; the second
supplies a query-side residual direction. If a cell has an odd selected count,
its final id remains unpaired. Persist and hash this disjoint pair inventory
before computing encoder results. Thus the proxy introduces no second sample
and no hidden exact-label cost.

## Frozen Encoder Arms and Controls

For every sampled positive-bit segment and rotation seed, evaluate:

```text
lvq_init:
  current independent scalar initialization, no adjustment

caq_r6:
  production source semantics, caq_adj_rd_lmt=6, caq_adj_eps=1e-8

caq_local_fixed_point:
  the identical source move order and acceptance rule, repeated until a full
  round accepts no move; this is implemented explicitly because config r=0
  disables adjustment rather than requesting unlimited rounds

corrected_exact:
  the v2 independent exact-integer complete-event oracle
```

The inherited `r=6` and `1e-8` values describe the baseline under study; they
are not tuned by v2.

Add exactly two attribution controls:

1. re-encode each frozen segment at uniform total `B=4` with the same four
   arms and rotation;
2. encode the complete positive-dimensional residual view at uniform total
   `B=4` with the same rotation seed and four arms.

No additional round, bit, dimension, boundary, seed, or dataset sweep is
permitted.

## Metrics

For each vector, segment, seed, and arm record:

```text
exact code and code hash
cosine and cosine squared J
angular excess E = 1/J - 1
fac_rescale and the source-compatible error-factor value
code equality with corrected_exact
accepted moves and completed rounds
event/heap/exact-integer work for corrected_exact
elapsed time, CPU time, and peak transient bytes
```

Because the stored error factor is not consumed by the current search path,
the primary scale-normalized opportunity statistic uses its mechanism but
cannot pass the gate alone. For a stratum `S`, define the ratio of sums

```math
R_{r6}(S)=
\frac{\sum_{v\in S}(f_{r6,v}-f_{exact,v})}
     {\sum_{v\in S}(f_{init,v}-f_{exact,v})},
```

and analogously `R_local(S)`. Here `f` is the source-compatible error-factor
value. A zero denominator means that the stratum contains no measurable
initialization-to-exact opportunity and therefore cannot pass. The ratio of
sums is used instead of the mean of per-vector ratios so near-zero individual
denominators cannot dominate the result. Per-vector unscaled distributions
must still be reported.

### Unchanged-estimator proxy

For every frozen residual pair, encode the first residual under each arm and
apply the unchanged full-code rescale estimator to the second residual.
Report:

```text
absolute inner-product error
absolute inner-product error / (||o|| * ||q||)
squared-L2 estimation error
bound coverage as a diagnostic
```

Zero-norm pairs are recorded and excluded by definition, not replaced with an
epsilon. Pairing and exclusions are identical for all arms.

## Statistical Protocol

The resampling unit is the IVF cell, not an individual vector. A paired
cluster bootstrap resamples cells with replacement, keeps all selected vectors
and residual pairs inside a sampled cell, and averages the three rotation
seeds within each vector before the cell statistic is formed. This avoids
treating correlated residuals or rotations as independent observations.

Use 10,000 bootstrap replicates and fixed bootstrap seed `20260711`. At a
one-sided tail probability near `0.05`, 10,000 replicates give Monte Carlo
standard error about `0.0022`, which is sufficient for the gate decision. Use
`alpha=0.05` and Holm correction across the fixed family of positive gate
comparisons. Also report unadjusted paired 95% confidence intervals and all
seed-specific point estimates.

The Holm family contains exactly 24 one-sided null hypotheses:

```text
4 materiality tests:
  R_r6 <= 0.10 and R_local <= 0.10 in each of two datasets

18 amplification tests:
  GIST:  R_r6 and R_local against five frozen controls each  = 10
  CIFAR: R_r6 and R_local against four frozen controls each =  8

2 estimator tests:
  corrected_exact does not reduce normalized pair error in each dataset
```

No descriptive subgroup, sensitivity row, or additional metric may enter this
family after results are observed.

## Frozen Decision Rule

The v2 limitation gate passes only if every condition below holds.

### Material finite-round regret

For the leading high-bit segment in both datasets:

```text
the 95% lower confidence bound of R_r6 is >= 0.10; and
the 95% lower confidence bound of R_local is >= 0.10.
```

In addition, all four materiality nulls in the fixed family must be rejected
after Holm correction.

The `0.10` floor is a preregistered research-significance requirement: at
least one tenth of the complete initialization-to-exact opportunity must
remain. It is not a method parameter. Report `0.05` and `0.20` sensitivity
rows, but neither can replace the registered decision.

Requiring `R_local` to pass prevents an ordinary increase in adjustment rounds
from being presented as a new mechanism.

### SAQ-specific segment amplification

Within each dataset, the leading-segment `R_r6` and `R_local` must exceed:

1. the same-vector, same-dimension uniform-`B=4` control;
2. every lower-bit positive segment in the frozen plan; and
3. the whole-positive-view uniform-`B=4` control.

All predeclared paired differences must have Holm-adjusted one-sided evidence
above zero. This distinguishes a segmentation-amplified limitation from the
generic CAQ optimizer gap already acknowledged by SAQ.

### Estimator materiality

In both datasets, replacing `caq_r6` with `corrected_exact` on the leading
segment must reduce the normalized absolute base-pair inner-product error with
Holm-adjusted one-sided evidence above zero. The unscaled error must have the
same direction. Error-factor improvement without estimator improvement is a
`NO-GO`.

### Seed consistency

For each of seeds `0`, `1`, and `2`, both leading-segment ratios must be at
least `0.10` as point estimates, and the estimator-error difference must have
the same improving sign. A pooled result driven by one rotation is a
`NO-GO`.

## Stop Outcomes

Return `NO-GO` and preserve the evidence if any of the following occurs:

- corrected-oracle proof or exact tiny parity fails;
- exact arithmetic is infeasible under the predeclared resource ceiling;
- either dataset fails the `0.10` materiality floor;
- local fixed-point adjustment removes the material gap;
- the leading segment lacks the frozen amplification controls;
- any rotation seed reverses the registered conclusion;
- the unchanged estimator proxy does not improve in both datasets;
- the effect requires another dataset, bit width, segment, seed, threshold, or
  pairing rule; or
- the only plausible repair is broad exact E-RaBitQ fallback.

A `CONDITIONAL PASS` establishes only a SAQ-specific limitation. It authorizes
a new primary-source/theory review of low-cost certificates or deterministic
repairs. Before any benchmark-query evaluation, such a candidate must recover
at least half of the exact gap while using at most twice production CAQ
encoding work on the frozen base sample, add no persistent bytes, and leave the
query estimator unchanged.

## Artifact and Branch Policy

This stopped branch remains the v1 provenance record. Writing this note does
not authorize implementation here.

After explicit approval, proposed execution should use:

```text
base:   saq-correctness-base
branch: saq-caq-corrected-oracle-v2
```

Migrate only:

- durable `AGENTS.md` research constraints;
- this protocol and the primary-source review/ledger;
- the v1 parity note/JSON as provenance;
- the centered-grid fixtures and minimal independent test logic.

Do not migrate the official private-method access hack as the corrected
oracle, generated binaries, graph/planner/fixed-policy experiments, or any
dataset output. The first v2 commit must contain only the oracle specification,
exact-arithmetic implementation, and synthetic validation tests.

## Current Status

```text
Protocol proposed and frozen in prose.
No v2 branch has been created.
No corrected oracle has been implemented.
No dataset artifact has been read for v2.
The next action requires explicit approval to execute V2-A0 and V2-A1 only.
```

## Post-Execution Addendum

The block above records the state when this protocol was frozen. After the
user authorized V2-A0/V2-A1 on 2026-07-11, the corrected-oracle specification
and synthetic validation were completed with `PASS` results. The durable
evidence is:

- `docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_synthetic_validation_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_artifacts_2026_07_11/`.

No dataset artifact was read. V2-A2 and V2-B remain unauthorized; V2-A1
establishes a validated measurement instrument, not a finite-round CAQ
limitation or method contribution.

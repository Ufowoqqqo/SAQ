# Low-Cost Deterministic CAQ Repair: Related-Work And Theory Review

Date: 2026-07-12

## Decision

```text
CONDITIONAL_GO_FOR_SYNTHETIC_PROTOTYPE
```

The bounded review does **not** authorize a production encoder, a base-data
run, benchmark queries, or a method claim. It authorizes one synthetic-only
implementation of an exact **one-shell Cartesian repair** around the code
returned by CAQ.

The proposed primitive is deliberately narrow:

```text
input:       one CAQ magnitude code k
per-coordinate neighborhood:
             C_i = {k_i-1, k_i, k_i+1} intersect [0,L-1]
operation:   find the exact best direction over C_1 x ... x C_D
output:      the shell optimum only when it strictly improves the incumbent
```

It provides a deterministic coordinated repair, or a certificate that no
simultaneous displacement of at most one magnitude level per coordinate can
improve the incumbent. It does **not** certify global E-RaBitQ optimality.

The gate is conditional because the algebraic scale/event reduction is prior
work, and restricting it to a radius-one CAQ neighborhood is at most a
moderate incremental idea. This direction survives only if the frozen later
base-only test recovers at least half of the exact-oracle gap while total
encoding work is at most twice production CAQ. Failure ends the direction;
the shell radius, number of passes, and restart count may not be swept.

## Scope

The review asks one question:

> Is there a deterministic operation that can cross a CAQ coordinate-wise
> local optimum on SAQ's short, high-bit segments, while retaining the same
> codebook, code bytes, factors, estimator, and query work, and while using
> work comparable to production `r=6` CAQ rather than full E-RaBitQ search?

The frozen B1 evidence motivates this question:

- GIST `64@11` retains `R_local=0.944982` of the
  initialization-to-exact opportunity;
- CIFAR `64@9` retains `R_local=0.789792`;
- continuing the same coordinate rule to a local fixed point changes almost
  nothing;
- exact codes reduce the unchanged normalized pair-estimator error by 13.42%
  and 8.28%; and
- complete exact labeling costs `272.9x` production `r=6` CAQ.

These results establish a local-optimum limitation, not the feasibility of a
repair.

## Objective Equivalence

For one sign-aligned residual segment, define

```text
a_i = |o_i|
L   = 2^(B-1)
k_i in {0,...,L-1}
z_i = k_i + 1/2.
```

CAQ and E-RaBitQ seek a direction maximizing

```math
Q(z;a)=\frac{\langle a,z\rangle^2}{\lVert z\rVert_2^2}.
```

For a fixed code `z`, its optimal positive scale is

```math
\alpha(z)=\frac{\langle a,z\rangle}{\lVert z\rVert_2^2}.
```

Completing the square gives

```math
\min_{\alpha>0,z}\lVert a-\alpha z\rVert_2^2
=\lVert a\rVert_2^2-\max_z Q(z;a).
```

This identity is important for novelty. The CAQ direction problem is exactly
a scaled-codebook mean-squared-error problem, not merely analogous to one.
Idelbayev et al. already characterize its scale/assignment fixed points and
give an `O(NK log K)` global algorithm for `N` scalar values and `K` codebook
levels. E-RaBitQ independently uses the same scale-rounding event structure
for its normalized grid codebook.

For fixed scale, let `t=1/alpha`. The optimal coordinate assignment is

```math
z_i(t)=\operatorname*{argmin}_{z_i\in\mathcal C_i}(z_i-t a_i)^2.
```

With the complete `L`-level codebook, this changes at `L-1` events per
nonzero coordinate. Full exact search therefore performs

```math
E_{full}=D_+(L-1)=D_+(2^{B-1}-1)
```

events, plus event ordering. For `D=64, B=11`, this is `65,472` first-pass
events per vector before reconstruction.

## Closest Prior Work And Collision Boundary

### SAQ / CAQ

SAQ initializes a per-vector uniform scalar code and applies cyclic
single-coordinate `+1/-1` improvements for a configured number of rounds. Its
paper states that this coordinate-descent-style procedure need not reach the
global codeword. The checked-in implementation defaults to `r=6`.

Therefore neither additional rounds nor a direct closed-form jump to the best
single-coordinate level is a new mechanism. B1 also shows that continuing the
identical rule to a fixed point does not close the leading-segment gap.

### E-RaBitQ

E-RaBitQ proves that a globally best grid direction is produced by rounding a
rescaled input at some critical scale, and enumerates the resulting events in
`O(D 2^B log D)` time. Its pinned official implementation uses a bounded
floating event window with `n_enum=10`; that implementation failed the prior
exact-parity contract and cannot serve as a certificate.

Thus complete scale/event search, a fixed event window, and a selective exact
fallback are occupied or invalid as the new contribution.

### Optimal Quantization Using Scaled Codebook

The CVPR 2021 work of Idelbayev et al. is a direct objective collision. It
derives the optimal scale for fixed assignments, nearest-level assignments
for fixed scale, potentially many scale/assignment fixed points, failure of
alternating optimization to guarantee the global solution, and globally exact
region enumeration in `O(NK log K)` time and `O(N)` space.

It also reviews limited grid search after alternating optimization. Therefore
scale alternation, fixed-grid repair, and generic event enumeration cannot be
claimed here.

### Coordinate And Local-Search Quantization

Coordinate descent and block-coordinate variants are mature optimization
tools. LSQ++ also makes local-search encoding and encode-time/accuracy
accounting standard in vector quantization. A generic statement that
"coordinated local search improves CAQ" is not novel.

### Direction-Aware Rounding

The withdrawn 2025/2026 DiaQ submission explicitly considers the `2^D`
floor/ceil hypercube around a vector. It replaces exact joint search with
coordinate scores containing extension and balancing hyperparameters. It is
in a different online neural-activation setting and does not provide the
exact shared-scale shell optimizer proposed here, but it occupies the broad
idea of direction-aware coordinated rounding. This materially narrows the
claim boundary.

## Candidate Decisions

| Candidate | Guarantee | Work | Decision |
|---|---|---:|---|
| More CAQ rounds or direct best-coordinate jumps | Coordinate-local only | `O(rD)` | `NO-GO`: same move rule; B1 local arm already fails |
| Alternating optimal scale and coordinatewise rounding | Monotone to a fixed point, not global | `O(ID)` | `NO-GO`: direct scaled-codebook prior work and bad fixed points |
| Fixed grid, factor-three restart, or fixed event window | No global or approximation guarantee | `O(GD)` | `NO-GO`: prior heuristic family and unjustified search budget |
| Complete E-RaBitQ/scaled-codebook events | Global optimum | `O(D2^B log D)` | `NO-GO`: occupied and measured at `272.9x` CAQ |
| Generic branch-and-bound certificate | Global only if all unresolved regions close | Worst case complete events | `NO-GO`: no bound found that plausibly meets the `2x` work gate |
| Exact one-shell Cartesian repair | Exact within the radius-one product neighborhood | `O(D log D)` | `CONDITIONAL GO`: synthetic implementation only |

## Why Scale Alternation Is Insufficient

For code `z`, alternate

```math
\alpha\leftarrow\frac{\langle a,z\rangle}{\lVert z\rVert^2},
\qquad
z_i\leftarrow\operatorname*{argmin}_{u\in\mathcal G}(a_i-\alpha u)^2.
```

Each step is non-increasing in scaled MSE, but the fixed-point condition is
only necessary for a global solution. A tiny exact counterexample is:

```text
a = (1,3), L=4
local k = (1,3), z = (1.5,3.5)
alpha = <a,z>/||z||^2 = 24/29
round(a/alpha) = (1,3), so alternation is fixed
Q_local = 288/29 = 9.931034...

global k = (0,1), z = (0.5,1.5)
Q_global = 10.
```

The global move requires coordinated changes larger than one ordinary CAQ
coordinate step. This example also rejects a deterministic local search based
on an assumed unimodal scale/assignment landscape.

## Proposed One-Shell Repair

Let `k` be the CAQ incumbent and define the smallest Cartesian closure of
CAQ's primitive unit move:

```math
\mathcal C_i(k_i)=
\{\max(0,k_i-1),k_i,\min(L-1,k_i+1)\},
```

with duplicates removed at codebook boundaries. Define

```math
\mathcal N_1(k)=
\mathcal C_1(k_1)\times\cdots\times\mathcal C_D(k_D).
```

This neighborhood contains up to `3^D` codes. It is not enumerated directly.

For each coordinate, sort its at most three half-grid magnitudes. Under a
shared `t`, the nearest allowed magnitude changes only at the midpoint of two
adjacent allowed levels:

```math
t_{i,r}=\frac{z_{i,r}+z_{i,r+1}}{2a_i}.
```

There are at most two events per nonzero coordinate. Start from every
coordinate's smallest shell level, sort all events, and update one coordinate
at each event. Maintain

```math
S=\sum_i a_i z_i,
\qquad
N=\sum_i z_i^2,
\qquad
Q=S^2/N.
```

Scoring the initial state and every post-event state finds

```math
\operatorname*{argmax}_{z\in\mathcal N_1(k)} Q(z;a)
```

exactly in real arithmetic. The proof is the same max-over-scale interchange
used by scaled-codebook quantization and E-RaBitQ, but applied to heterogeneous
three-level coordinate codebooks.

### Running example

```text
a = (2,7), L=4
CAQ coordinate-local k = (1,3), z = (1.5,3.5)
Q_CAQ = 3025/58 = 52.155172...

C_1 = {0,1,2}
C_2 = {2,3}
```

The shell event scan returns

```text
k_shell = (0,2), z_shell = (0.5,2.5)
Q_shell = 1369/26 = 52.653846...
```

The complete-codebook optimum is `k_exact=(0,1)` with `Q_exact=52.9`.
The one-shell move therefore recovers about `66.95%` of this example's
local-to-exact objective gap without claiming global optimality.

The earlier `(1,3)` counterexample remains a required negative control: its
radius-one shell cannot reach `(0,1)` and must return no improvement. The
method has no universal gap-recovery guarantee.

## Correctness Properties

For exact real arithmetic, one shell pass has the following properties:

1. **Monotonicity.** The incumbent is retained unless the shell optimizer has
   strictly larger `Q`.
2. **Shell exactness.** The selected code maximizes `Q` over
   `N_1(k)`; it is not a coordinatewise heuristic.
3. **Negative certificate.** If no code improves the incumbent, no vector of
   simultaneous per-coordinate magnitude displacements in `{-1,0,+1}` can
   improve it.
4. **No global claim.** A better code can exist outside the shell, as the
   `(1,3)` example proves.
5. **Representation preservation.** The output remains an ordinary SAQ/CAQ
   code with unchanged bit width and factors; no query metadata is added.

The implementation must specify binary32 event ordering, equal-event ties,
zero coordinates, clipping, and strict-improvement comparisons. Numerical
parity with brute force is required before any scientific run.

## Complexity Gate

Let `E_shell <= 2D_+` be the shell-event count.

```text
candidate construction: O(D)
event ordering:          O(D log D)
event scan/replay:       O(D)
transient memory:        O(D)
persistent index bytes:  0
query-time work:         0 additional
bit-width dependence:    none in event count
```

For the frozen leading segments, the event-count comparison is:

| Segment | Full exact events | Maximum shell events |
|---|---:|---:|
| GIST `64@11` | 65,472 | 128 |
| CIFAR `64@9` | 16,320 | 128 |

This reduction makes a measured prototype plausible, but it is not a runtime
result. Sorting and objective-comparison constants still matter. The later
method gate remains:

```text
total CAQ + shell CPU/work <= 2.0x production r=6 CAQ
and
recovered exact-oracle gap >= 0.50 on both frozen leading segments.
```

The first synthetic implementation must report event count, comparisons,
temporary bytes, and elapsed CPU separately from CAQ. It may not hide
preparation or sorting.

## Novelty Gate

### What is inherited

- the direction/scaled-MSE equivalence;
- the fixed-scale nearest-level assignment;
- critical-scale event enumeration;
- coordinate and local-search optimization as general techniques; and
- direction-aware joint rounding as a broad objective.

### What remains potentially distinct

- using the exact product of immediate CAQ move neighborhoods to cross a
  measured SAQ-amplified coordinate-local optimum;
- solving that `3^D` neighborhood exactly with at most `2D` shared-scale
  events, independent of the high native bit width; and
- obtaining a zero-metadata, query-invariant repair or a precise shell-local
  certificate under a frozen SAQ representation.

This is a narrow incremental contribution, not a new quantizer. Its novelty
is insufficient without the full chain:

```text
SAQ-specific high-bit limitation
-> exact minimal coordinated neighborhood
-> <=2x build work
-> >=50% oracle-gap recovery
-> unchanged-estimator improvement
-> later recall benefit at unchanged query work and bytes.
```

### Strict-reviewer objection

> This is the known scaled-codebook event algorithm restricted to an
> arbitrarily chosen local neighborhood around CAQ. Why is it more than one
> block-coordinate restart?

The only defensible response is empirical and structural: radius one is the
minimal Cartesian closure of CAQ's existing unit move, its full product is
solved exactly rather than scored coordinatewise, its event count is
bit-independent, and it must pass the frozen Pareto gate without tuning. If
that evidence is absent, accept the objection and stop.

## Authorized Synthetic Implementation

The review authorizes exactly one implementation stage:

```text
S0  implement one-shell event optimization as a diagnostic encoder primitive
S1  verify exhaustive brute-force parity on enumerable shell fixtures
S2  verify zero/tie/boundary/padding and deterministic replay semantics
S3  compare optimized and exact-reference shell outputs
S4  measure standalone shell work and CAQ+shell work on fixed synthetic inputs
```

The implementation may not read GIST, CIFAR, B1 per-vector outputs, benchmark
queries, ground truth, or indexes. It may not add radius two, repeated shell
passes, factor-three restarts, random restarts, or a tunable acceptance
threshold.

Passing synthetic correctness and plausibility would authorize writing a
separate, frozen base-only method protocol. It would not itself authorize that
execution.

## Sources

The machine-readable ledger is
`docs/saq_caq_low_cost_repair_sources_2026_07_12.json`.

Primary sources:

- [SAQ](https://arxiv.org/abs/2509.12086)
- [Extended RaBitQ](https://arxiv.org/abs/2409.09913)
- [Optimal Quantization Using Scaled Codebook](https://openaccess.thecvf.com/content/CVPR2021/html/Idelbayev_Optimal_Quantization_Using_Scaled_Codebook_CVPR_2021_paper.html)
- [Coordinate Descent Algorithms](https://arxiv.org/abs/1502.04759)
- [LSQ++](https://openaccess.thecvf.com/content_ECCV_2018/html/Julieta_Martinez_LSQ_lower_runtime_ECCV_2018_paper.html)
- [DiaQ withdrawn submission](https://openreview.net/forum?id=akKL87xV9l)

## Limitations Of This Review

- This is a bounded review, not a systematic literature survey.
- DiaQ is a withdrawn submission rather than an accepted result; it is used
  only as a conservative novelty collision.
- The one-shell proof gives local exactness, not a global approximation ratio.
- The `O(D log D)` bound does not prove the measured `2x` runtime gate.
- Tiny examples establish possibility and impossibility cases, not behavior on
  frozen SAQ residuals.
- No benchmark-query claim is supported or authorized.

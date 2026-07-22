# Original Attempt 4 Reopening Protocol

Date: 2026-07-22

Branch: `saq-a4-original-reopening-protocol`

Base: `saq-a4-r0-static-gate@617ad25`

Stage: **source-only protocol design**

Execution authority: **NOT AUTHORIZED**

Maximum outcome of this commit: **`A4-OR-PROTOCOL_REVIEW_PASS`**

## 1. Purpose and correction of scope

This protocol reopens only the scientific question behind the original
arbitrary-cardinality Attempt 4. It does not reopen the old A4-1S or V2
executions and does not revive the later prefix-code successor.

For a small group of scalar factors stored in one fixed `B`-bit word, the
original candidate selects arbitrary positive integer cardinalities

```text
K_1 * ... * K_r <= S = 2^B
```

and encodes the Cartesian-product label with a mixed-radix address. The
production scan reads the full word once and performs one full-word lookup per
group. It has no leading-bit semantics, progressive decoder, coarse pass,
candidate pruning, learned binary label permutation, or query-dependent rule.

The reopening is allowed to define a new representation and query consumer.
R0 already proved that the old candidate is not an encoder-only substitution
inside unchanged SAQ. Therefore unchanged-SAQ compatibility is not a gate in
this protocol, and no result may be described as an SAQ improvement unless a
later, separately authorized integration study establishes one.

## 2. Existing evidence and claim ceiling

The following outcomes remain immutable:

- A4-0 established only a synthetic feasible-set witness: a `(3,5)` scalar
  product represents the frozen 15-atom source exactly, while the best dyadic
  scalar product has nonzero error; a same-capacity unrestricted block
  codebook also represents that source exactly.
- A4-1S stopped when its frozen exact construction-and-evidence pipeline
  projected to `24.170246892361` CPU-hours against a `24.0` CPU-hour ceiling.
  This was not an algorithmic lower bound. Exact scalar work and canonical
  evidence serialization both materially contributed to the cost.
- V2 remains `CRASH_OR_UNKNOWN / START_ONLY`; it supplied no scientific or
  performance result.
- R0 returned `NO_GO_UNCHANGED_SAQ_COMPATIBILITY`; it did not test natural-data
  value or novelty.
- The later prefix successor returned `NO_GO_DIRECT_COMPOSITION`. That result
  applies only to the added prefix/coarse-to-fine mechanism.

Primary work already covers exact scalar quantization, non-power-of-two scalar
alphabets, factorized codebooks, transform coding, mixed allocation, packed
lookup scans, and dense-rate quantization. Passing this protocol would not
make those primitives novel. At most it would establish a new measured
database-systems Pareto point for word-local, fixed-address factorization.

## 3. Smallest falsifiable question

> On two frozen natural ANN residual datasets and at the same 32- or 64-byte
> database payload, does arbitrary-cardinality mixed-radix factorization remove
> a material part of the dyadic word-local error, remain competitive with an
> independently optimized ordinary PQ system, recover a material part of the
> opportunity exposed by same-capacity two-dimensional block VQ, and do so
> with construction, model-state, table-building, and scan costs that justify
> later native query evaluation?

The candidate fails early if its only advantage is lower fitting
reconstruction error, if it is dominated by ordinary PQ or block VQ, if the
base-only estimator proxy does not improve, or if a cheap production-like
trainer cannot replace the old exact/evidence pipeline.

## 4. Stages and authorization boundaries

```text
A4-OR-P   protocol and independent review                 <- this stage
A4-OR-C   synthetic numerical/cost admission              <- separate authority
A4-OR-B   frozen base-only feasibility gate                <- separate authority
A4-OR-N   native implementation + performance contract    <- separate authority
A4-OR-Q   held-out benchmark-query evaluation              <- separate authority
```

Each stage requires a committed input contract, clean named snapshot, and one
independent review before the next authorization. A pass permits only the next
protocol or implementation checkpoint. It does not automatically authorize
data access, benchmark queries, a production implementation, or a method
claim.

No stage may inspect old ignored artifacts or prior A4 natural-data outputs.
No failed threshold may be rescued by changing datasets, coordinates, group
boundaries, word widths, seeds, restarts, tolerances, or controls.

## 5. Frozen representation and workloads

The base-only screen inherits the pre-outcome A4-1 input geometry rather than
selecting a favorable new panel:

- GIST sample50k with `K=512` IVF cells;
- CIFAR60k with `K=512` IVF cells;
- the previously frozen cluster-stratified fit/held-out inventory rule;
- 8,192 fitting and 8,192 held-out base residuals per dataset;
- the previously frozen 128-coordinate view and adjacent, nonoverlapping
  two-coordinate groups;
- word widths `B in {4,8}`, giving exactly 32 or 64 payload bytes per vector;
- the previously frozen disjoint, base-residual-pair proxy inventory; and
- no benchmark query, ground truth, Recall, prior result, or generated index
  read before A4-OR-Q.

Before A4-OR-B, a machine-readable contract must bind the exact parent commit,
dataset identities, selection hashes, row order, coordinate order, pairing,
seeds, compiler, thread count, and hardware identity. If any inherited object
cannot be reconstructed without viewing an outcome, stop and request a new
blind input-binding protocol; do not substitute a convenient sample.

The candidate remains query-unaware. Fitting rows alone select cardinalities,
centers, group models, and any stopping decision. Held-out base residuals and
base pairs are evaluation-only. Benchmark queries are used only in A4-OR-Q
after encoder rules and all operating points are frozen.

## 6. Candidate and three forced controls

All arms receive the same database payload and the same fitting and held-out
inventories. Permanent model bytes, transient memory, training work, query
table bytes, table-building arithmetic, label-encoding work, and scan lookups
are counted separately.

### 6.1 `D`: dyadic scalar product

For each fixed two-coordinate group, choose scalar level counts

```text
K_j in {1,2,4,...,S},  K_1 K_2 <= S
```

using the same scalar distortion curves and the same allocation solver as the
candidate. It receives no weaker training, smaller restart budget, or cheaper
numeric path.

### 6.2 `A`: arbitrary-cardinality mixed-radix candidate

For the same group, choose

```text
K_1,K_2 positive integers,  K_1 K_2 <= S
```

and encode `u=z_1+K_1 z_2`. Every unused address still consumes its share of
the paid word and expanded query table. Persist every scalar representative,
radix, valid-state count, multiplier, offset, and alignment byte required by
the decoder.

### 6.3 `P`: independently optimized ordinary PQ

Use a conventional 8-bit-subquantizer PQ/OPQ implementation at the same total
payload:

- 32-byte panel: 32 four-dimensional, 256-center subquantizers;
- 64-byte panel: 64 two-dimensional, 256-center subquantizers.

The implementation and exact revision must be pinned before A4-OR-C. It must
receive its documented training procedure, including its own learned rotation
when the pinned ordinary control is OPQ, and an independently justified
restart/iteration budget. It must not reuse candidate centers or be reduced to
the candidate's fixed adjacent-pair geometry merely to make the comparison
easy.

### 6.4 `V`: same-capacity two-dimensional block VQ

For each of the candidate's 64 fixed adjacent coordinate pairs, independently
train exactly `S` unrestricted two-dimensional centers with the same fitting
rows. Use a pinned standard native k-means implementation, eight deterministic
starts, frozen initialization, iteration cap, empty-cluster rule, and
binary32-serialized centers.

At `B=8`, the unrotated 64-by-2D ordinary-PQ model and `V` have the same
mathematical feasible family. They remain separately forced training and
implementation arms because `P` is the conventional deployment baseline and
`V` is the product-initialized word-local optimizer-adequacy control. They are
not two independent scientific model classes and may not be double-counted as
two pieces of statistical support. If the pinned `P` configuration is
unrotated and otherwise identical, disagreement is first a training or
implementation gap and must be explained. Passage still uses `V` for the
block-opportunity contrasts and `P` for the ordinary-PQ margin; neither result
may replace the other. If `P` uses an OPQ rotation, record the changed model
class and do not demand parity.

## 7. Replacing the old exact pipeline

The production candidate and `D` share one explicitly approximate scalar-curve
construction. For each coordinate, construct a deterministic equal-count rank
histogram with `H=1024` bins from the 8,192 fitting rows, then run a native
binary64 contiguous-partition dynamic program for every `K=1,...,256`.

The histogram algorithm is frozen as follows. Canonicalize signed zero to
`+0.0`; reject every nonfinite input; sort by binary32 numeric value and then
vector id; and assign sorted ranks `[h*N/H,(h+1)*N/H)` to bin `h`. Here
`N=8192`, so every `H=1024` bin has eight rows and every `H=2048` bin has four;
there are no empty bins. Equal values may cross a rank boundary and remain in
both adjacent bins. A bin's weight is its row count. Its representative is the
IEEE binary64 mean computed by Neumaier compensated addition in sorted-rank
order followed by one binary64 division by the weight. Ties in the dynamic
program prefer the smaller last-boundary rank; allocation ties prefer the
larger used-state product and then lexicographically smaller `(K_1,K_2)`.

The A4-OR-C machine contract must encode these rules and their fixtures before
any natural-data read; it may add byte layouts and error codes but may not
change a boundary, tie, representative, or weight rule. Product allocation is
exact over the resulting shared curves. Selected models are replayed on the
original, unbinned fitting and held-out rows; histogram distortion is never
reported as the outcome.

The frozen sensitivity repeats the scalar construction with `H=2048`. If the
sign of any registered contrast or any pass/fail decision changes, return
`APPROXIMATION_SENSITIVE`. The larger histogram is a sensitivity check, not an
alternative result that may replace an unfavorable `H=1024` outcome.

Prefer a maintained, published native implementation of one-dimensional
squared-error clustering. A custom solver is allowed only if no suitable
implementation satisfies the frozen input, license, determinism, and
curve-output requirements, and its expected scientific-core line count is
approved before implementation. The reopened natural-data path uses neither
arbitrary-precision arithmetic nor canonical per-interval evidence
serialization.

Numerical correctness is separated from production cost:

1. Reuse the frozen A4-0 witness and A4-1S tiny fixtures.
2. Add a hash-frozen suite of support-capped integer-valued histograms that an
   independent exact-integer/rational reference can enumerate cheaply.
3. Compare the native histogram/DP trainer with the exact reference on every
   reachable `K` and both allocation arms.
4. Independently replay every selected serialized binary32 center and label in
   binary64 using both compensated sufficient statistics and direct raw-row
   accumulation; no histogram or training accumulator is accepted as
   evaluation evidence.

A4-OR-C passes numerical admission only if:

- every frozen tiny DP objective agrees with the same histogram problem's exact
  reference within `1e-10 * max(1, |SSE_exact|)`;
- every selected dyadic and arbitrary cardinality tuple matches the exact
  reference after the frozen tie rules;
- mixed-radix pack/unpack and lookup distance agree with direct reconstruction
  on every address, including invalid-address handling;
- no nonfinite value, negative reconstructed squared error, serialized-center
  collision, or order-dependent allocation decision occurs; and
- the replay discrepancy defined below is within its frozen limit.

For each word width `B`, A4-OR-C has one synthetic cell containing the 8,192
raw rows for that width. Let `D_D_syn(H,B)` be `D`'s direct raw-row squared
error for histogram resolution `H`, divided by 8,192; like the later `D_D`, it
is total 128-coordinate distortion per vector. For each
`X in {D,A,P,V}`, each `H in {1024,2048}` that applies to that arm, and each
`B in {4,8}`, independently compute total squared error by (a) compensated
weighted sufficient statistics and (b) a direct row/group/coordinate loop.
Define

```text
eta = max_(X,H,B) |SSE_compensated_stats(X,H,B)-SSE_direct(X,H,B)|
      / 8192.
```

The synthetic admission requires
`eta <= 0.0005 * min_(H,B) D_D_syn(H,B)`. Before accepting A4-OR-B results,
repeat the same per-vector definition over all dataset-by-rate cells. In each
cell, maximize over arms and applicable histogram resolutions, divide total
SSE discrepancy by that cell's held-out vector count, and require it to be at
most `0.0005 * min_H D_D(H)` for that cell. An arm without histogram
resolution has one replay and no invented `H` copy.

The replay limit is one percent of the registered five-percent materiality
threshold. Every allocation whose fitting objective lies within the measured
numeric envelope of the selected winner must be replayed. If those
interchangeable winners do not yield the same gate decision, return
`NUMERICALLY_UNRESOLVED`. These tolerances validate the instrument; they are
not candidate performance margins.

## 8. Synthetic cost admission

A4-OR-C uses no natural data. It creates one deterministic same-shape synthetic
panel with 128 coordinates, 8,192 fitting rows, both word widths, and the full
`D/A/V` training shapes. `P` runs through its pinned public training path.

Time the scientific trainers without JSON, logs, compression, hashing,
provenance capture, or archive work. Measure those support costs separately.
Use one process, one frozen thread count, fixed affinity, three repetitions
after one warmup, and report every absolute CPU/wall time, peak resident
memory, and dispersion.

For each post-warmup repetition, define `T_DA` as the total process CPU time of
the shared `H=1024` curves, shared `H=2048` curves, and both `D` and `A`
allocation/packing at both resolutions and both word widths. Shared curves are
counted once, not once per arm. Let

```text
T_project = 2 * median(T_DA repetition 1,
                       T_DA repetition 2,
                       T_DA repetition 3).
```

The factor two represents the two frozen datasets; the synthetic panel already
contains both rates. CPU time sums all threads. The warmup is excluded. The
same median-of-three rule applies to reported arm time and support/scientific
ratios; all individual repetitions remain visible. The support/scientific
ratio divides median total support CPU by median total scientific training CPU
summed across `D/A/P/V`. The allocation ratio divides median `A`-specific
allocation/packing CPU by median shared scalar-fitting CPU.

Admission requires all of the following:

- `T_project` is at most 1 CPU-hour;
- peak resident memory of any arm is at most 16 GiB;
- support/evidence CPU time is at most 25% of scientific training CPU time;
- `A` allocation and packing overhead beyond the shared scalar curves is at
  most 25% of shared scalar-fitting CPU time; and
- all four arms complete without reducing shape, rows, `K`, starts, or
  controls.

The one-hour ceiling is an early feasibility limit, not a deployment claim.
It is deliberately far below the failed 24-hour path so that the reopening
cannot merely move serialization work around. Failure returns
`NO_GO_REOPENING_COST`; one ordinary implementation repair is permitted only
for a demonstrated correctness or accidental instrumentation defect, not to
change the scientific algorithm or threshold.

## 9. Base-only estimands

For each dataset and word width, report held-out reconstruction distortion
`D_X` for arm `X`, normalized per vector over the same 128 coordinates.
Define

```text
Delta_A = D_D - D_A
Delta_V = D_D - D_V

G = Delta_A / D_D
C = Delta_A / Delta_V        when Delta_V > 0
```

For the disjoint base-residual-pair proxy, build each arm's declared binary32
query tables, encode the first residual, use the second as a query-like
operand, and report mean absolute squared-distance error `E_X`. Define

```text
Q = (E_D - E_A) / E_D.
```

`Q` is a base-only estimator diagnostic. It is not Recall, ranking accuracy,
or query evidence. If `E_D=0`, the cell returns `NO_GO_BASE_ONLY`; no epsilon
or alternative normalization is introduced.

For PQ competitiveness define

```text
P_margin = 1.01 D_P - D_A.
```

Positive `P_margin` means the candidate is no more than 1% worse than ordinary
PQ reconstruction. The 1% band is not called equivalence; it is only the
largest quality deficit allowed for an efficiency-based systems hypothesis.

Use the inherited two-stage IVF-cell bootstrap with 10,000 deterministic
replicates, including its PCG64 seed, draw order, arm-shared resamples,
vector/pair weighting, and binary64 accumulation order. For each dataset `d`
in `{GIST,CIFAR}` and rate `b` in `{4,8}`, define exactly five zero-null
contrasts:

```text
L_G[d,b]  = (D_D-D_A) - 0.05 D_D
L_V[d,b]  = D_D-D_V
L_C[d,b]  = (D_D-D_A) - 0.50 (D_D-D_V)
L_Q5[d,b] = (E_D-E_A) - 0.05 E_D
L_P[d,b]  = 1.01 D_P-D_A
```

The exact identifier format is `<contrast>_<dataset>_B<rate>`, for example
`L_Q5_GIST_B4`. These 20 identifiers, ordered lexicographically as ASCII, are
the complete confirmatory family. For point
contrast `T_hat`, bootstrap replicate `T_r`, and `delta_r=T_r-T_hat`, report

```text
two-sided basic 95% CI =
  [T_hat-quantile_0.975(delta), T_hat-quantile_0.025(delta)]
one-sided 95% lower bound = T_hat-quantile_0.95(delta)
null-centered one-sided p =
  (1 + count(delta_r >= T_hat)) / 10001
```

Quantiles use NumPy `method="linear"`; comparisons include ties. Apply Holm
step-down at familywise `alpha=0.05` across exactly 20 hypotheses. Sort by
`(raw_p,hypothesis_id)`; at one-based position `i`, the adjusted p-value is the
running maximum of `(20-i+1)*raw_p`, capped at one. Basic intervals and lower
bounds are unadjusted descriptive outputs. Passage uses the Holm-adjusted
one-sided p-values only and requires each named adjusted p-value to be below
`0.05`. No ratio, prevalence, leave-one-group-out, cost, or
sensitivity statistic enters or replaces this family.

## 10. Base-only go/no-go rule

A4-OR-B passes only if all of the following hold in both datasets and both word
widths:

1. Holm-adjusted `L_G` rejects its zero null, establishing more than 5%
   dyadic-error removal;
2. Holm-adjusted `L_V` rejects its zero null and Holm-adjusted `L_C` rejects its
   zero null, establishing a positive block-VQ opportunity and that `A` closes
   more than half of it;
3. Holm-adjusted `L_Q5` rejects its zero null, establishing more than 5%
   base-pair absolute-error reduction;
4. Holm-adjusted `L_P` rejects its zero null, establishing that `A` is within
   the one-percent ordinary-PQ reconstruction band; and
5. at least 48 of 64 fixed groups have positive reconstruction point gain, and
   the minimum leave-one-group-out pooled gain remains at least 5%; and
6. relative to `P`, `A` provides at least one predeclared twofold advantage in
   fitting CPU time or persistent model bytes, while neither of those two
   metrics is more than twofold worse.

At `B=8`, `P` and `V` may be the same model class, but `L_V/L_C` test the
word-local block opportunity while `L_P` tests the separate PQ noninferiority
condition; neither is described as independent replication.

The reconstruction and 50% thresholds are retained from the pre-outcome A4-1
contract. Applying 5% also to the estimator proxy prevents reconstruction-only
passage. The prevalence rule prevents a few favorable coordinate groups from
carrying the result. The one-percent/twofold PQ route requires a material
efficiency explanation rather than declaring a small reconstruction gap
publishable.

Any control invalidity, failed cell, numerical-envelope violation, or missing
cost row returns `NO_GO_BASE_ONLY`. Do not proceed because the mean across
datasets passes, because one rate is favorable, or because model bytes look
small while training or table costs are omitted.

## 11. Required cost and state ledger

For every arm and cell, record at minimum:

- database payload bytes and alignment waste;
- serialized centers, transform, radices, valid-state data, offsets, and all
  other permanent model bytes;
- expanded and compact query-table bytes and table-construction operations;
- fitting, allocation, rotation, encoding, and table-build CPU/wall time;
- peak resident and arm-owned transient memory;
- number of groups, lookups, decoded labels, branches, and bytes read per
  scanned vector;
- compiler, flags, library revisions, threads, affinity, NUMA policy, warmup,
  repetitions, and dispersion; and
- instrumentation time outside the scientific and query hot paths.

Python loops, JSON, hashing, provenance capture, and process supervision must
remain outside timed native training and scan regions. If instrumentation
cannot be isolated, its overhead is measured and included rather than hidden.

## 12. Native and query-stage contract

Only a reviewed `PASS_A4_OR_B_BASE_ONLY` permits writing A4-OR-N. Before any
benchmark-query access, A4-OR-N must first implement and pass a query-free
native label/table microbenchmark: relative to `D`, the lower 95% confidence
bound on matched-word scan throughput must be at least `0.95`. Table build,
cache footprint, and instrumentation are measured separately. Failure closes
the direction before benchmark queries.

Before any performance-oriented implementation, A4-OR-N must also freeze:

- exact revisions of ordinary PQ/OPQ, block VQ, SAQ, and any RaBitQ-family
  contextual baseline;
- datasets, IVF assignments, probe schedules, candidate counts, payload, model
  bytes, hardware, compiler, flags, threads, affinity, NUMA, warmup, and
  repetitions;
- the scientific hot path: full-word extraction, table lookup, accumulation,
  and any candidate admission work;
- allocation/copy behavior, table locality, batching, branches, SIMD, and
  parallelism; and
- matched Recall operating points and primary latency/throughput metrics.

The encoder, group geometry, cardinality rules, tables, and operating-point
grid are frozen before any benchmark query is opened. Query results may not
select a dataset, transform, word width, group boundary, seed, threshold, or
control.

A paper-viable result requires a reproducible Pareto improvement on both
datasets against the best matched control. The minimum systems effect is one
of:

- at matched Recall@100 within `0.001` absolute, at least 10% higher end-to-end
  queries per second with no worse index size and no more than twofold build
  CPU; or
- at matched throughput within 5%, at least `0.002` absolute Recall@100 gain
  with no worse index size and no more than twofold build CPU.

Report the complete frontier, latency distribution, throughput, build time,
peak memory, serialized index size, and table-construction overhead. Passing
only a microkernel, reconstruction, or fixed-candidate metric is insufficient.

## 13. Stop rules and interpretation

Stop the reopening if:

- the production-like trainer fails tiny numerical admission;
- projected cost or memory fails A4-OR-C;
- arbitrary cardinalities do not pass every A4-OR-B cell;
- ordinary PQ or block VQ dominates the candidate under the frozen quality and
  efficiency rule;
- base-pair estimator error does not improve;
- native scan overhead erases the offline gain; or
- the final method does not move the frozen Recall--throughput frontier.

A failed control is repaired or declared invalid; it is never counted as a
candidate win. A pass is evidence of feasibility and a systems trade-off, not
automatic novelty. Before a paper claim, update the primary-source review for
the exact surviving mechanism and explain why it is more than transform
coding, known dense-rate scalar products, ordinary PQ, or parameter tuning.

## 14. Current authorization and next checkpoint

This document authorizes no implementation, compilation, import, synthetic
generation, base/query/result/index read, benchmark, or environment change.
After independent review and push, stop at

```text
A4-OR-PROTOCOL_REVIEW_PASS
```

The smallest possible next authorization is A4-OR-C only: pin the production
trainer and control revisions, write the bounded synthetic numerical/cost
instrument, compile it, and run the frozen synthetic admission. Its expected
scientific core is 350--800 net lines if a suitable native one-dimensional
trainer can be reused; support and evidence code must remain below the larger
of 800 lines or twice the scientific core. Exceeding that estimate requires a
new user checkpoint before implementation continues.

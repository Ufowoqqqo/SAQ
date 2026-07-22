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
implementation gap; the stronger held-out arm is used in passage and the gap
must be explained. If `P` uses an OPQ rotation, record the changed model class
and do not demand parity.

## 7. Replacing the old exact pipeline

The production candidate and `D` share one explicitly approximate scalar-curve
construction. For each coordinate, construct a deterministic weighted-quantile
histogram with `H=1024` bins from fitting rows, then run a native binary64
contiguous-partition dynamic program for every `K=1,...,256`. Product
allocation remains exact over the resulting shared curves. Selected models
are replayed on the original, unbinned fitting and held-out rows; histogram
distortion is never reported as the outcome.

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
   binary64 using both compensated prefix statistics and direct raw-row
   accumulation; no histogram or training accumulator is accepted as
   evaluation evidence.

A4-OR-C passes numerical admission only if:

- every frozen tiny DP objective agrees with the same histogram problem's exact
  reference within `1e-10 * max(1, |SSE_exact|)`;
- every selected dyadic and arbitrary cardinality tuple matches the exact
  reference after the frozen tie rules;
- mixed-radix pack/unpack and lookup distance agree with direct reconstruction
  on every address, including invalid-address handling; and
- no nonfinite value, negative reconstructed squared error, serialized-center
  collision, or order-dependent allocation decision occurs; and
- the per-vector replay discrepancy
  `eta=max(|SSE_prefix-SSE_direct|)/N` is at most
  `0.0005 * D_D` in every cell.

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

Admission requires all of the following:

- projected two-dataset `D+A` scalar-curve and allocation CPU time, including
  both `H=1024` and the mandatory `H=2048` sensitivity, is at most 1 CPU-hour;
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
Delta_R = D_D - min(D_P,D_V)

G = Delta_A / D_D
C = Delta_A / Delta_R        when Delta_R > 0
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
replicates. The confirmatory family contains `G>0.05`, `C>0.50`, `Q>0.05`, and
`P_margin>0` for each of four dataset-by-rate cells. Apply Holm correction at
familywise `alpha=0.05`. Report unadjusted intervals and every point estimate,
but no descriptive subgroup may replace a failed registered cell.

## 10. Base-only go/no-go rule

A4-OR-B passes only if all of the following hold in both datasets and both word
widths:

1. the Holm-adjusted lower bound establishes more than 5% dyadic-error
   removal;
2. the stronger of ordinary PQ and trained block VQ improves on `D`, and the
   adjusted lower bound establishes that `A` closes more than half of that
   opportunity; the B=8 overlap is counted once;
3. the adjusted lower bound establishes more than 5% base-pair absolute-error
   reduction;
4. the adjusted lower bound establishes that `A` is within the one-percent PQ
   reconstruction band; and
5. at least 48 of 64 fixed groups have positive reconstruction point gain, and
   the minimum leave-one-group-out pooled gain remains at least 5%; and
6. relative to `P`, `A` provides at least one predeclared twofold advantage in
   fitting CPU time or persistent model bytes, while neither of those two
   metrics is more than twofold worse.

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

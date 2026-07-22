# Attempt 4 R0: Static SAQ-Compatibility and Novelty Gate

Date: 2026-07-22

Branch: `saq-a4-r0-static-gate`

Reopening base: `3577edd4354bdf2c4f132ac6152bf0b22c1f746c`

Stage: protocol formation only

Current outcome: `PROTOCOL_WRITTEN_NOT_EXECUTED`

Execution authority: none

## 1. Purpose

Attempt 4 asks whether two scalar coordinates can share one fixed-width word
more effectively when their numbers of reconstruction levels may be arbitrary
positive integers rather than powers of two.  For example, a four-bit word
has 16 addresses.  It can hold a `3 x 5` Cartesian product with one unused
address, whereas conventional scalar bit allocation admits products such as
`4 x 4` or `2 x 8`.

The synthetic `3 x 5` witness established that this larger feasible set can
strictly reduce reconstruction error.  It did not establish a limitation of
SAQ, an effect on natural residuals, or a search improvement.  The predecessor
A4-1S pipeline stopped at its frozen cost gate, and the later V2 workstream
produced no scientific result before artifact recovery was closed.

This R0 stage asks the cheaper question that should precede any new code or
data access:

> Can the arbitrary-cardinality mechanism be expressed inside the unchanged
> SAQ representation and its existing query consumers, and does that leave a
> mechanism not already supplied by known transform, scalar, product, or
> mixed-radix quantization work?

R0 is a source-and-literature gate.  It does not design the method, measure
natural data, or reopen either predecessor execution path.

## 2. Preserved predecessor outcomes

The following facts are immutable inputs, not pilot observations to reinterpret:

1. `saq-arbitrary-cardinality-analysis@20bc411` passed only the frozen
   synthetic representation witness.
2. A4-1S cost evidence at `9ce1052` and terminal review at `f1b464b` remain
   `NO_GO_EXACT_SOLVER_COST` for that exact construction-and-evidence
   pipeline.  The result is not a solver-only lower bound.
3. The A4-1 base-only gate at pre-outcome commit `3aa2f6e` was never run.
4. V2's primary-source review at `c4ccea3` and protocol at `f86a51d` do not
   establish SAQ compatibility or scientific feasibility.
5. V2 remains `CRASH_OR_UNKNOWN / START_ONLY`; portfolio closure at
   `3577edd` is `STOP_NO_FURTHER_ARTIFACT_RECOVERY`.
6. There is no natural-data, estimator, Recall, throughput, index-build, or
   state-of-the-art comparison result for Attempt 4.

R0 must not weaken, relabel, rerun, repair, or infer through any of these
outcomes.

## 3. Fixed boundary

The compatibility target is the existing corrected SAQ baseline
`saq-correctness-base@bc7829b`, compared with the official source snapshot
`howarlii/saq@2163ebc`.  R0 treats the following behavior as frozen:

- the fixed PCA view, IVF assignments, residual vectors, global segment/bit
  plan, segment rotations, and padding;
- one code per vector segment with the same serialized widths and factors;
- the existing short code formed from the most significant bit of each
  positive-bit coordinate and the existing remaining-bit long code;
- the existing fast and accurate query consumers;
- the full-code estimator's use of the stored code and `ExFactor.rescale`;
- no query-trained fitting, per-query policy, per-cluster plan identifier,
  per-vector radix identifier, mixed dispatch, or changed candidate schedule.

The candidate concept is limited to the pre-outcome A4 representation:

- two adjacent scalar coordinates form one fixed `B_g`-bit word;
- coordinate cardinalities `K_1,K_2` are positive integers with
  `K_1 K_2 <= 2^B_g`;
- scalar labels use the mixed-radix address `u = z_1 + K_1 z_2`;
- learned scalar representatives and unused addresses have the semantics
  frozen at `3aa2f6e`.

R0 may describe a missing mapping.  It may not repair that mapping by
changing the frozen boundary.

## 4. Required static inputs

The gate reads only committed source and primary work.  It must record exact
commit or publication identifiers and inspect only the smallest relevant
source ranges.

Required SAQ source surfaces are:

- `saqlib/quantization/config.h`;
- `saqlib/quantization/quantizer.hpp` and `cluster_packer.hpp`;
- `saqlib/quantization/single_data.hpp` and `cluster_data.hpp`;
- `saqlib/quantization/caq/caq_encoder.hpp`;
- `saqlib/quantization/caq/caq_estimator.hpp`;
- `saqlib/quantization/fastscan/lut.hpp` and its direct fast-scan consumer.

Required A4 semantic surfaces are the pre-outcome contract at `3aa2f6e` and
the mixed-radix representation implementation at
`saq-arbitrary-cardinality-analysis@f1b464b`.  Historical V2 source may be
read only to confirm A4-reference semantics; it is not an implementation
dependency.

The novelty review must cover, at minimum, the primary sources already pinned
for exact one-dimensional quantization, transform coding for nearest-neighbor
search, adaptive or irregular product-quantizer allocation, Quicker ADC,
Finite Scalar Quantization, Q-Palette, and FibQuant.  A secondary summary
cannot establish passage.

No dataset, result directory, query, ground truth, generated index, ignored
artifact, cache, token, capture, or runtime-state path may be opened.

## 5. Gate C: representation and consumer compatibility

The reviewer must produce one explicit mapping table with one row for every
state consumed by construction, serialization, fast search, and accurate
search.  At minimum it must map:

| A4 concept | Required unchanged-SAQ counterpart |
| --- | --- |
| `K_1,K_2` and mixed-radix multipliers | Existing global configuration or a derivation requiring no new stored field |
| learned scalar representatives | Existing SAQ code/rescale semantics, without a new serialized codebook |
| mixed-radix word `u` | Existing short-code and long-code bits at identical width and offsets |
| unused addresses | Existing legal-code behavior without a new invalid-state branch |
| full-word distance table | Existing accurate estimator formula and lookup work |
| first-stage information | Existing most-significant-bit fast estimator with the same admissible code meaning |
| per-group selection | Existing single global segment/bit plan, without per-cluster or per-vector identifiers |

For each row, the report must give source locations and one of:

- `IDENTICAL`: the bytes and consumer semantics are already identical;
- `DERIVED`: the candidate state is determined from existing global state and
  needs no new bytes, branch, table family, or query operation;
- `CHANGED`: compatibility needs a new field, codebook, meaning, branch,
  dispatch rule, estimator operation, or serialized layout; or
- `UNRESOLVED`: the available source is insufficient for a proof.

Gate C passes only if all rows are `IDENTICAL` or `DERIVED` and the report
proves all of the following:

1. database payload and permanent index bytes are unchanged;
2. no new per-vector, per-cluster, or per-group stored identifier is needed;
3. every existing legal fast and accurate consumer can read the candidate
   bytes without source changes;
4. the most-significant-bit stage remains a valid coarse view of the same
   code, not merely the first bit of an arbitrary address;
5. the full-code estimator and `rescale` meaning are unchanged for every
   reachable code and query vector;
6. table count, table size, lookup count, memory reads, and dispatch behavior
   do not increase; and
7. no behavior is justified by the currently unused `ExFactor.error` field.

Any `CHANGED` row returns `NO_GO_UNCHANGED_SAQ_COMPATIBILITY`.  Any
`UNRESOLVED` row returns `INCONCLUSIVE_STATIC_MAPPING`.  Neither outcome may
be rescued inside R0 by proposing a new index format, prefix code, scan
kernel, estimator, or broader independent variable.

## 6. Gate N: novelty and dominance

Gate N is evaluated only after Gate C passes.  The report must use a claim
matrix with these columns:

```text
source | fixed-rate representation | arbitrary cardinalities |
allocation/training | random-access lookup | progressive/prefix consumption |
query work | what A4 would add
```

For every claimed addition, the reviewer must answer:

1. Is it more than exact scalar error curves plus integer cardinality
   allocation plus a standard mixed-radix address?
2. Is the mechanism caused by a documented SAQ constraint rather than by a
   generic transform-coding or product-quantization choice?
3. Why is it not obtained by globally packed dyadic transform coding?
4. Why is a same-capacity two-dimensional block or product codebook not the
   more general solution?
5. What construction, metadata, table, and query-work advantage would make
   the factorized restriction scientifically useful?
6. What later query-unaware experiment could falsify the claimed advantage
   without tuning on benchmark queries?

Gate N passes only if the matrix identifies one concrete, source-supported
mechanism that is specific to the unchanged SAQ consumer boundary, is not a
direct composition of the closest work, and has a later measurable advantage
against both globally packed dyadic allocation and a same-capacity block/PQ
control.

If the remaining claim is only a denser rate axis, lower scalar
reconstruction error, one fixed lookup, a faster exact solver, or cheaper
evidence generation, return `NO_GO_NOVELTY_DIRECT_COMPOSITION`.

## 7. Decision rule and precedence

R0 has exactly five outcomes, applied in this order:

| Condition | Outcome |
| --- | --- |
| Required commit, source, or primary-work identity is unavailable or mismatched | `ARTIFACT_INVALID` |
| Gate C contains any `CHANGED` row | `NO_GO_UNCHANGED_SAQ_COMPATIBILITY` |
| Gate C contains no `CHANGED` row but at least one `UNRESOLVED` row | `INCONCLUSIVE_STATIC_MAPPING` |
| Gate C passes but Gate N fails | `NO_GO_NOVELTY_DIRECT_COMPOSITION` |
| Both gates pass with complete evidence | `PASS_R0_STATIC_ONLY` |

The report must list verified evidence, inference, and unresolved uncertainty
separately.  It must not average or trade compatibility failures against a
stronger novelty story.

`PASS_R0_STATIC_ONLY` would establish only that a bounded follow-up question
is coherent.  It would not establish a useful natural-data gap, correctness
of a new encoder, construction affordability, estimator improvement, Recall,
throughput, or publication-level novelty.

## 8. Cost and review budget

R0 permits no scientific implementation and requires no custom evidence
machinery.  The expected output is one report of approximately 250--400 lines
containing the mapping table, claim matrix, findings, and terminal decision.
The report may use `rg`, focused source ranges, Git object identities, and
ordinary Markdown tables.

Stop and return to the user if the review exceeds 8 wall-clock hours, 30 tool
calls, or 400 report lines without reaching a decision.  Do not create a
schema, runner, verifier, archive format, process supervisor, or generated
artifact.  One independent reviewer must inspect an immutable report commit
for source support, status precedence, and overclaiming.  At most one bounded
repair and rereview is permitted.

## 9. Authorization boundary and possible successor

This document authorizes no execution of R0 itself beyond its formation and
static review.  A separate explicit user instruction is required to perform
the mapping and novelty assessment and commit its decision report.

Even `PASS_R0_STATIC_ONLY` would authorize no code, build, test, synthetic
run, base-data access, query access, SAQ modification, or reuse of V2 source.
A later numerical stage would require a new protocol on a clean named
snapshot.  Before any benchmark query is read, it would have to freeze a
query-unaware base-only comparison among:

- word-local dyadic scalar products;
- word-local arbitrary-cardinality scalar products;
- globally packed dyadic allocation; and
- a same-capacity trained block/PQ control.

That later protocol must predeclare materiality, prevalence, construction
cost, metadata, lookup memory, and stop rules.  Lower reconstruction error
alone cannot pass it.  Failure of either R0 gate closes Attempt 4 without such
a numerical successor.


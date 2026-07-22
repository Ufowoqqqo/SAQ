# Attempt 4 R0: Static SAQ-Compatibility and Novelty Gate

Date: 2026-07-22

Branch: `saq-a4-r0-static-gate`

Reopening base: `3577edd4354bdf2c4f132ac6152bf0b22c1f746c`

Stage: protocol formation only

Current outcome: `PROTOCOL_WRITTEN_NOT_EXECUTED`

Execution authority: none

## 1. Question and preserved evidence

Attempt 4 lets two scalar coordinates share one fixed-width word while their
numbers of reconstruction levels may be arbitrary positive integers. A
four-bit word, for example, can hold a `3 x 5` product with one unused address,
whereas ordinary scalar bit allocation admits products such as `4 x 4` or
`2 x 8`.

R0 asks the cheaper question that must precede new code or data access:

> Can this mechanism be expressed inside the unchanged SAQ representation and
> existing query consumers, and does that leave something not already supplied
> by known transform, scalar, product, or mixed-radix quantization work?

The following predecessor outcomes are immutable:

- `saq-arbitrary-cardinality-analysis@20bc411` passed only the synthetic
  `3 x 5` representation witness.
- A4-1S evidence `9ce1052` and review `f1b464b` remain
  `NO_GO_EXACT_SOLVER_COST` for that exact construction-and-evidence pipeline;
  this is not a solver-only lower bound.
- The A4-1 base-only gate frozen at `3aa2f6e` was never run.
- V2 review `c4ccea3` and protocol `f86a51d` establish no SAQ compatibility
  or scientific feasibility.
- V2 remains `CRASH_OR_UNKNOWN / START_ONLY`; closure `3577edd` remains
  `STOP_NO_FURTHER_ARTIFACT_RECOVERY`.
- Attempt 4 has no natural-data, estimator, Recall, throughput, index-build,
  or state-of-the-art comparison result.

R0 does not design a repair, execute either predecessor, or reinterpret these
outcomes.

## 2. Frozen boundary and inputs

The compatibility target is `saq-correctness-base@bc7829b`, checked against
official source `howarlii/saq@2163ebc`. The following remain fixed:

- PCA view, IVF assignments, residuals, global segment/bit plan, rotations,
  padding, serialized widths, and stored factors;
- one code per vector segment;
- the short code made from each positive-bit coordinate's most significant
  bit and the existing remaining-bit long code;
- the existing fast and accurate query consumers and full-code estimator;
- the estimator's use of the stored code and `ExFactor.rescale`; and
- no query-trained policy, per-cluster/per-vector plan or radix identifier,
  mixed dispatch, or changed candidate schedule.

The candidate remains the pre-outcome A4 concept: adjacent coordinates use
cardinalities `K_1,K_2` with `K_1 K_2 <= 2^B_g`, address
`u = z_1 + K_1 z_2`, learned scalar representatives, and the unused-address
semantics frozen at `3aa2f6e`.

The static review may inspect only committed source and pinned primary work.
Minimum SAQ surfaces are `config.h`, `quantizer.hpp`, `cluster_packer.hpp`,
`single_data.hpp`, `cluster_data.hpp`, `caq_encoder.hpp`, `caq_estimator.hpp`,
and `fastscan/lut.hpp` under `saqlib/quantization/`, plus the direct fast-scan
consumer. A4 semantics come from `3aa2f6e` and the representation source at
`f1b464b`; historical V2 source is a read-only semantic reference, never an
implementation dependency.

The novelty review must cover the pinned primary work on exact one-dimensional
quantization, ANN transform coding, adaptive/irregular product quantization,
Quicker ADC, Finite Scalar Quantization, Q-Palette, and FibQuant. No dataset,
result, query, ground truth, generated index, cache, token, ignored artifact,
or runtime-state path may be opened.

## 3. Gate C: unchanged-SAQ compatibility

The decision report must map every construction, serialization, fast-search,
and accurate-search state. Its table must include at least:

| A4 concept | Required unchanged-SAQ counterpart |
| --- | --- |
| `K_1,K_2` and multipliers | Existing global state or zero-byte derivation |
| learned representatives | Existing code/rescale semantics; no new codebook |
| mixed-radix word `u` | Existing short/long bits at identical width and offsets |
| unused addresses | Existing legal-code behavior; no invalid-state branch |
| full-word table | Existing accurate formula and lookup work |
| first-stage information | Existing MSB fast estimate with the same code meaning |
| group selection | Existing global plan; no new identifier or dispatch |

Each row receives exactly one classification with source locations:

- `IDENTICAL`: bytes and consumer semantics are already identical;
- `DERIVED`: existing global state determines it with no new bytes, table
  family, branch, dispatch, or query operation;
- `CHANGED`: it requires a new field, codebook, meaning, operation, branch,
  dispatch rule, estimator, or serialized layout; or
- `UNRESOLVED`: committed source is insufficient for a proof.

Gate C passes only if every row is `IDENTICAL` or `DERIVED` and the report
proves all of the following:

1. database payload and permanent index bytes are unchanged;
2. no new per-vector, per-cluster, or per-group stored identifier is needed;
3. existing fast and accurate consumers read the bytes without source changes;
4. the MSB stage remains a valid coarse view, not an arbitrary address bit;
5. full-code and `rescale` semantics match for every reachable code and query;
6. table count/size, lookups, memory reads, and dispatch do not increase; and
7. no claim depends on the currently unused `ExFactor.error` field.

Any `CHANGED` row is `NO_GO_UNCHANGED_SAQ_COMPATIBILITY`. With no `CHANGED`
row, any `UNRESOLVED` row is `INCONCLUSIVE_STATIC_MAPPING`. R0 cannot rescue
either outcome with a new format, prefix code, scan kernel, estimator, or
broader independent variable.

## 4. Gate N: novelty and dominance

Gate N runs only after Gate C passes. Its claim matrix records, for every
closest primary source:

```text
fixed-rate representation | arbitrary cardinalities | allocation/training |
random-access lookup | progressive/prefix consumption | query work | A4 delta
```

For each proposed A4 delta, the report must answer:

1. Is it more than exact scalar curves, integer-cardinality allocation, and a
   standard mixed-radix address?
2. Which unchanged SAQ consumer constraint causes the mechanism?
3. Why does globally packed dyadic transform coding not obtain it?
4. Why is a same-capacity block/PQ codebook not the more general solution?
5. What construction, metadata, table, or query-work advantage justifies the
   factorized restriction?
6. What later query-unaware experiment could falsify that advantage?

Gate N passes only with one source-supported mechanism specific to the
unchanged SAQ consumer, not directly composed from the closest work, and with
a measurable later advantage against global-dyadic and same-capacity block/PQ
controls. Evidence that the residual claim is only a denser rate axis, lower
scalar error, one lookup, a faster solver, or cheaper evidence yields
`NO_GO_NOVELTY_DIRECT_COMPOSITION`. If available primary evidence cannot
decide composition or novelty, return `INCONCLUSIVE_STATIC_NOVELTY`; absence
of a novelty proof alone is not proof of direct composition.

## 5. Outcomes, cost, and authority

Apply outcomes in this order:

| Condition | Outcome |
| --- | --- |
| Required identity unavailable or mismatched | `ARTIFACT_INVALID` |
| Gate C has any `CHANGED` | `NO_GO_UNCHANGED_SAQ_COMPATIBILITY` |
| Gate C has no `CHANGED` but has `UNRESOLVED` | `INCONCLUSIVE_STATIC_MAPPING` |
| Gate C passes; Gate N evidence is insufficient | `INCONCLUSIVE_STATIC_NOVELTY` |
| Gate C passes; evidence establishes direct composition/ordinary claim | `NO_GO_NOVELTY_DIRECT_COMPOSITION` |
| Both gates pass completely | `PASS_R0_STATIC_ONLY` |

Verified evidence, inference, and uncertainty must be listed separately.
Compatibility failure cannot be traded against novelty. `PASS_R0_STATIC_ONLY`
would establish only that a later question is coherent—not natural-data value,
correctness, affordability, Recall, throughput, or publication-level novelty.

R0 requires one 150--250-line report, ordinary source/Git inspection, and one
independent review of an immutable commit. It permits no custom schema,
runner, verifier, archive, supervisor, or generated artifact. Stop after 8
hours, 30 tool calls, or 300 report lines without a decision. At most one
bounded repair and rereview is allowed.

This protocol's formation and static review authorize no R0 decision
execution. Performing the mapping/novelty assessment requires a separate user
instruction. Even a pass authorizes no code, build, test, synthetic run,
base/query access, SAQ modification, or V2-source reuse. Failure of either
gate closes Attempt 4. A numerical successor would require a new frozen
protocol comparing word-local dyadic, arbitrary-cardinality, global-dyadic,
and same-capacity block/PQ arms before any benchmark query is read.

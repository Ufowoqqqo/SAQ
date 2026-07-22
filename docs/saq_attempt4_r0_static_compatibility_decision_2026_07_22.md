# Attempt 4 R0 Static Compatibility Decision

Date: 2026-07-22

Branch: `saq-a4-r0-static-gate`

Protocol: `e24f09a4458e8402aad5b176091576126f2624ab`

Authorization: user-authorized R0 static assessment only

Decision: **`NO_GO_UNCHANGED_SAQ_COMPATIBILITY`**

Gate N status: **`NOT_RUN_BY_PRECEDENCE`**

## 1. Question and scope

R0 asks whether the pre-outcome Attempt 4 arbitrary-cardinality mechanism can
be expressed inside the unchanged corrected SAQ representation and its
existing fast and accurate query consumers.  It is not enough for A4 to keep
the same total number of database payload bits.  Its bytes must retain the
same meaning for the current short-code, long-code, and `rescale` consumers,
without a new codebook, serialized field, table family, branch, dispatch rule,
or query operation.

This assessment read only committed source and documents.  It did not open a
dataset, result, query, ground truth, generated index, ignored artifact,
cache, token, capture, or runtime-state path.  It made no source change, build,
test, import, synthetic run, or numerical measurement.

Under the frozen precedence, one `CHANGED` mapping is sufficient for
`NO_GO_UNCHANGED_SAQ_COMPATIBILITY`.  Gate N is evaluated only after every
Gate C row is `IDENTICAL` or `DERIVED`; therefore R0 does not make a new
novelty or direct-composition decision here.

## 2. Fixed evidence identities

| Role | Immutable object |
| --- | --- |
| Official SAQ source | `howarlii/saq@2163ebc` |
| Corrected compatibility target | `saq-correctness-base@bc7829b` |
| A4 pre-outcome contract | `saq-arbitrary-cardinality-analysis@3aa2f6e` |
| A4 reviewed terminal source snapshot | `saq-arbitrary-cardinality-analysis@f1b464b` |
| A4-1S cost evidence/review | `9ce1052` / `f1b464b` |
| V2 portfolio closure | `saq-arbitrary-cardinality-feasibility-v2@3577edd` |

The `2163ebc..bc7829b` quantization diff changes positive one-bit packing and
padded-lane safe-min behavior.  It does not add an arbitrary-cardinality
configuration, learned scalar codebook, radix field, mixed-radix decoder, or
group lookup table.  The compatibility findings below therefore apply to the
corrected target rather than relying on an obsolete official-source bug.

## 3. Gate C mapping

| A4 concept | Classification | Decisive evidence |
| --- | --- | --- |
| `K_1,K_2` and mixed-radix multipliers | `CHANGED` | Current `QuantSingleConfig` has no radix/cardinality state; A4 requires per-group radix and used-state metadata. |
| Learned scalar representatives | `CHANGED` | Current accurate consumers derive a uniform `sq_delta` from one bit width and read code plus `rescale`; A4 persists learned binary32 centroids/codebooks. |
| Mixed-radix word `u` | `CHANGED` | SAQ stores per-coordinate MSB and remaining bitplanes; A4 packs one direct 4/8-bit group label for two coordinates. Equal byte count does not preserve bit meaning. |
| Unused addresses | `CHANGED` | A4 marks addresses `u >= K_1 K_2` invalid and fills their table entries with positive infinity; current consumers have no invalid-address field or branch. |
| Full-word distance table | `CHANGED` | A4 constructs one `S`-entry two-coordinate squared-L2 table per group; current accurate search reconstructs an inner product from short bits, long bits, `sq_delta`, and `rescale`. |
| First-stage information | `CHANGED` | Current fast search consumes one MSB per scalar coordinate; A4 defines a direct mixed-radix address and no equivalent per-coordinate MSB coarse code. |
| Per-group selection | `CHANGED` | A4 selects and records group-specific cardinalities/codebooks; the frozen SAQ boundary provides only the global segment/bit plan and no such group state. |

All seven mandatory rows are `CHANGED`.  No row is `UNRESOLVED`, so the
outcome is a compatibility no-go rather than an inconclusive mapping.

## 4. Source evidence by consumer boundary

### 4.1 Configuration and serialized state

At `bc7829b`, `saqlib/quantization/config.h:12-27` contains the base
quantizer type, rotation/fast-scan choices, CAQ adjustment settings, average
bits, segmentation, and compact-layout settings.  It contains no learned
scalar alphabet, `K_1,K_2`, radix multiplier, valid-state count, or group
codebook identifier.

`saqlib/quantization/cluster_data.hpp:17-30` defines the produced code vector
and per-vector factors.  `cluster_data.hpp:34-79` fixes storage around the
uniform segment bit width: short-code bytes are one bit per padded coordinate,
and long-code bytes are `(num_bits-1)` bits per padded coordinate.

The persisted cluster body at `cluster_data.hpp:317-335` contains short
factors, short codes, long codes, `ExFactor` values, vector IDs, and rotated
centroids.  It has no A4 radix metadata or learned per-group scalar codebooks.

In contrast, the pre-outcome A4 contract at
`docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md:
606-643` explicitly counts every learned scalar centroid plus per-group
`uint16_t` radices, used-state metadata, and any materialized multiplier or
offset.  Supplying that required state changes permanent index metadata.

This is already a decisive failure of Gate C conditions 1 and 2.

### 4.2 Code layout

At `bc7829b`, `saqlib/quantization/quantizer.hpp:134-158` stores one CAQ code
vector and its factors.  `quantizer.hpp:166-185` extracts each coordinate's
most significant bit into the short code.  `quantizer.hpp:194-205` masks and
packs all remaining bits of every coordinate into the long code.

A4 instead defines

```text
u = z_1 + K_1 z_2,  0 <= u < K_1 K_2 <= S
```

at its preregistration lines 323-334 and in
`research/a4_1s/representation.cpp:169-231`.  It then packs 64 direct group
labels as nibbles or bytes (`representation.cpp:235-287`).  The same payload
size of 32 or 64 bytes per vector is verified, but the address is a joint
group label rather than two scalar codewords split into their respective MSB
and lower bitplanes.

For the illustrative legal radix pair `(K_1,K_2)=(3,5)`, addresses are
`u=z_1+3z_2`.  The four-bit word's highest bit changes at `u=8`; within
`z_2=2`, labels `z_1=0,1` have that bit clear while `z_1=2` has it set.  The
bit is therefore not one unchanged per-coordinate coarse label.  A new prefix
assignment could be designed, but that would be a new mechanism explicitly
forbidden as an R0 rescue.

This fails Gate C conditions 3 and 4.

### 4.3 Fast and accurate consumers

At `bc7829b`, `saqlib/quantization/caq/caq_estimator.hpp:56-60` fixes
`sq_delta = 2 / 2^num_bits` and creates the existing lower-bit lookup helper.
The fast path at lines 138-178 consumes the stored short code as a one-bit
estimate.  The accurate path at lines 190-215 reads the long code and
`ExFactor.rescale`, reconstructs the inner product, and derives the distance.
The single-vector implementation at lines 317-365 likewise combines the
short-code mask, lower-bit inner product, uniform CAQ delta, and `rescale`.

A4's consumer is different.  Its contract lines 429-465 and
`research/a4_1s/representation.cpp:414-472` build a binary32 table

```text
T_q[u] = ||q_g - reconstruction(u)||_2^2
```

with 16 or 256 entries per two-coordinate group; unused states contain
positive infinity.  The contract reports 64 such group lookups and fixed
per-query-like table footprints of 4,096 or 65,536 bytes at lines 632-650.
Those tables, invalid-state semantics, and group lookups are not read by the
current CAQ estimator.

Reusing the same number of payload bits does not make the current estimator
interpret the joint label as the intended learned reconstruction.  Supporting
it requires at least a new table family and consumer operation, and the A4
preregistration itself states at lines 63-65 that the representation needs
radix metadata, a new encoder, and a new scan kernel.

This fails Gate C conditions 5 and 6.  `ExFactor.error` cannot repair the
mapping: the accurate estimator reads `rescale` at line 207/358 and does not
use `error` in its distance formula, satisfying the protocol's condition 7
check.

## 5. Decision and interpretation

The earliest decisive failure is the absence of radix and learned-codebook
state from the unchanged serialized representation.  Even if that metadata
were treated as free, the short/long bit meanings and both query consumers
would still be different.  The failure is therefore semantic, not merely a
header-size accounting issue.

The terminal R0 decision is:

```text
NO_GO_UNCHANGED_SAQ_COMPATIBILITY
```

This establishes only that the frozen Attempt 4 mechanism is not an encoder
substitution inside the unchanged SAQ representation and query path.  It does
not establish that arbitrary-cardinality products are mathematically invalid,
ineffective on natural data, unaffordable in every implementation, or
incapable of forming a different ANN system.

Gate N is `NOT_RUN_BY_PRECEDENCE`.  Accordingly, this report does not claim
that the idea is novel, non-novel, or proven to be a direct composition.  The
previous prior-work boundary remains historical evidence, not a newly executed
R0 novelty verdict.

Under the protocol, Gate C failure closes Attempt 4 without a numerical
successor.  No code, new representation, prefix design, scan kernel, base-data
screen, query evaluation, or performance experiment is authorized by this
decision.

## 6. Evidence classification and checkpoint

Verified evidence:

- current SAQ serializes and consumes uniform per-coordinate bitplanes plus
  `rescale`, without A4 radix/codebook/table state;
- A4 requires learned scalar representatives, group radices, direct
  mixed-radix labels, invalid addresses, and expanded group tables; and
- all seven mandatory Gate C mappings require changed state or behavior.

Inference:

- an A4-like method could be explored only by broadening the independent
  variable to a new representation and query consumer, which is outside R0
  and would face the separate prior-work and systems-evidence burden.

Unresolved uncertainty:

- natural-data prevalence, estimator quality under a new consumer, Recall,
  throughput, build cost, and state-of-the-art frontier movement remain
  unmeasured.

Scientific code changed: 0 lines.  Support output: this decision report only.
No source was compiled or executed, and no result was independently reproduced.
Performance status remains `PERFORMANCE_NOT_YET_MEASURED`; there is no timed
hot path or instrumentation region and no fair-comparison delta.

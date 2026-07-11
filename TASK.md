# TASK.md

## Active Goal

V2-A2 of the corrected `CO-0 v2` protocol is complete. The validated
exact-integer complete-event oracle can label the later frozen base-only
sample within the predeclared synthetic resource ceiling. Stop before V2-B
until its preregistration is separately reviewed and authorized. The v1
screen remains closed under its frozen official-source contract.

Current status:

```text
branch saq-caq-corrected-oracle-v2 created from saq-correctness-base
bounded primary-source review migrated
new-direction memo migrated
official Extended-RaBitQ pinned at 52b9e6c7ba6c316036cdb04074732fe561966a53
CO-0A source/codebook parity completed: FAIL
CO-0B preregistration deliberately not written: gate did not authorize it
CO-0 v2 corrected-oracle protocol migrated
V2-A0/V2-A1 explicitly authorized
V2-A0 proof/specification review completed: PASS
V2-A1 synthetic exact-oracle validation completed: PASS
V2-A2 synthetic cost feasibility completed: PASS
V2-B not authorized
no GIST/CIFAR CO-0 output inspected
no method or contribution established
```

Authoritative documents:

- `docs/saq_limitation_primary_source_review_2026_07_11.md`;
- `docs/saq_limitation_primary_sources_2026_07_11.json`;
- `docs/saq_next_direction_go_no_go_memo_2026_07_11.md`;
- `docs/saq_caq_co0a_official_source_parity_2026_07_11.md`;
- `docs/saq_caq_co0a_artifacts_2026_07_11/source_parity_result.json`;
- `docs/saq_caq_co0_v2_reopening_corrected_oracle_protocol_2026_07_11.md`;
- `docs/saq_caq_co0_v2_oracle_specification_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_synthetic_validation_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a1_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_a2_synthetic_cost_design_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a2_synthetic_cost_evidence_2026_07_11.md`;
- `docs/saq_caq_co0_v2_a2_artifacts_2026_07_11/`.

## Research Question

```text
For frozen SAQ residual segments, how much of the exact E-RaBitQ
grid-on-sphere alignment opportunity remains after production six-round CAQ,
and is the regret systematically concentrated in SAQ's short/high-bit
segments?
```

The null is that `r=6` CAQ is already sufficiently close, or that any gap is
generic CAQ behavior, negligible under the unchanged estimator, closed by
ordinary extra rounds, or repairable only at known E-RaBitQ cost.

## CO-0A: Official-Source Parity — Completed, FAIL

Completed sequence:

1. Pin the official `VectorDB-NTU/Extended-RaBitQ` repository by commit.
2. Record license, relevant source paths, compiler/build flags, and the exact
   encoder entry point.
3. Add tiny exhaustive `(D,B)` fixtures independent of dataset values.
4. Verify official objective optimality and CAQ/E-RaBitQ codebook mapping.
5. Verify code, cosine, rescale, and error-factor arithmetic in float64.
6. Write a durable parity note with commands, hashes, and limitations.

The independent full-event enumerator matched complete tiny codebooks in all
109 cases, and the CAQ/E-RaBitQ algebraic mapping passed all 48 fixtures.
However, the actual official encoder missed its initialized optimal state on a
reachable `D=64, B=3` case. Its public width set also excludes frozen-plan
`B=2,6,11`, and the private `B=11` call narrows 10-bit magnitudes through
`uint8_t`. Thus source parity failed. This is an invalid oracle artifact, not
evidence about SAQ.

## V2-A0: Proof And Specification Review — Completed, PASS

Freeze and verify before accepting implementation:

- exact binary32-to-integer decomposition;
- exact event ordering and objective comparison;
- initial, zero, tie, padding, subnormal, and `B=11` semantics;
- proof that complete events contain a global direction-code optimum;
- `uint32_t` centered-code representation and output schema;
- arithmetic-operation, bit-complexity, transient-memory, and persistent-byte
  accounting.

The independent oracle is prior-work-based measurement infrastructure, not a
new quantizer or the pinned official implementation.

## V2-A1: Synthetic Validation — Completed, PASS

Implement the independent oracle without the official private-method access
hack. Validate:

- complete brute-force parity for enumerable `(D,B)` cells;
- all 109 prior deterministic tiny fixtures;
- the reachable initialized-state counterexample;
- zero/tie/padding/subnormal/largest-finite binary32 cases;
- widened `B=11` magnitudes;
- centered CAQ code, cosine, rescale, and estimator identities;
- Release and sanitizer/debug runs.

Any mismatch stops the direction before V2-A2.

## V2-B: Preregistration Boundary — Not Authorized

The following would have been frozen only after parity passed:

- GIST sample50k and CIFAR60k base/index provenance;
- the historical `K=512, B=4` plans in the go/no-go memo;
- a cluster-stratified hash sample and disjoint base-pair proxy inventory;
- rotation seeds and numeric tolerances;
- encoder arms: LVQ init, CAQ `r=6`, CAQ local fixed point, exact E-RaBitQ;
- same-segment uniform-`B=4` and whole-positive-view uniform-`B=4` controls;
- paired bootstrap estimands, thresholds, sensitivity rows, and stop rules;
- complete exact-oracle and construction-work accounting.

Sample size may be chosen only by a synthetic-vector cost dry run. No dataset
gap, held-out query result, alternative bit width, or post-hoc segment may
select the design.

## V2-A2: Synthetic Cost Feasibility — Completed, PASS

Stop at the completed V2-A2 boundary:

```text
do not access dataset artifacts
do not design a method
do not infer finite-round CAQ regret from validator correctness
retain n=50,000 per dataset and the 24 CPU-hour exact-label ceiling
do not reinterpret 7.969 CPU-hours as a query/index performance result
stop before V2-B
```

Do not run V2-A2, inspect dataset artifacts, or design a CAQ repair in the same
step.

## Stop Rules

The v1 official-source stop remains final and is not retroactively relaxed.
V2 stops at A0/A1 if the exactness proof is incomplete, any brute-force or
boundary fixture disagrees, binary32/tie semantics remain ambiguous, a frozen
bit width narrows, or sanitizer validation fails. V2-A2 stops if the frozen
sample requires more than one CPU-day under its conservative cost equation,
or if feasibility requires removing a cell, dropping `B=11`, using
dataset-derived synthetic inputs, or shrinking the sample post hoc. Passing
V2-A2 authorizes only a later decision about V2-B; it does not authorize
dataset access or a method claim.

# TASK.md

## Active Goal

The corrected `CO-0 v2` V2-B1 limitation screen is complete and returns
`CONDITIONAL_PASS`. Production `r=6` and local-fixed-point CAQ retain a large
fraction of the exact alignment opportunity on the frozen leading high-bit
SAQ segments; all registered controls and unchanged-estimator tests pass the
shared 24-hypothesis Holm gate. This establishes a limitation, not a method.

The bounded low-cost repair review returned
`CONDITIONAL_GO_FOR_SYNTHETIC_PROTOTYPE` for exactly one candidate: an exact
radius-one Cartesian shell optimizer around the CAQ code. That synthetic
stage is now complete. Correctness passes, but the fixed-width implementation
requires `4.579x` to `8.169x` total `CAQ + shell` CPU across the four frozen
cost rows, failing the `2.0x` gate. The decision is
`NO_GO_ON_COMPLEXITY`.

This candidate is closed as negative evidence. Do not read base artifacts,
B1 per-vector output, benchmark queries, ground truth, or indexes for it. Do
not add a second shell pass, a larger radius, restarts, acceptance thresholds,
or implementation-level rescue variants. No low-cost repair method has been
established. The v1 official-source result remains closed.

The project-level closure synthesis is now complete. The selected decision is
`STOP_SAQ_CENTRIC_INCREMENTAL_METHOD_SEARCH`. Retain SAQ as a baseline and
limitation case, but do not begin another SAQ-specific planner, encoder,
transform, layout, or search-policy implementation. The next authorized stage
is a problem-first primary-source selection review only. It must identify a
question and mechanism that remain meaningful across at least two independent
strong baselines before a new clean branch is opened.

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
V2-B0 final preregistration completed: PASS
V2-B1 runner/summarizer synthetic validation completed: PASS
V2-B1 first registered preflight: STOPPED before encoding
V2-B1 rotation build-profile cause reproduced: PASS
V2-B1 instrument-only correction synthetic validation: PASS
V2-B1 registered rerun: COMPLETE
V2-B1 frozen 24-hypothesis analysis: CONDITIONAL_PASS
all 24 Holm tests and seed-consistency checks: PASS
benchmark queries / ground truth / indexes: NOT READ
no method or contribution established
bounded repair review: CONDITIONAL GO for one-shell synthetic prototype only
one-shell synthetic exact/brute-force parity: PASS
one-shell Release and ASAN standalone suites: PASS
one-shell frozen total-cost gate: FAIL (best 4.579x vs maximum 2.0x)
one-shell decision: NO_GO_ON_COMPLEXITY
base/query/index evaluation for one-shell: NOT RUN
project-level SAQ-centric method search: STOP
next stage: problem-selection related-work review only
```

The completed run contains 9,600,000 encoding rows and 4,773,192 pair rows.
The frozen analysis finds leading-segment `R_r6=0.944994` on GIST and
`0.790078` on CIFAR; local convergence leaves `0.944982` and `0.789792`.
Replacing `r=6` with the exact oracle reduces the unchanged normalized
base-pair error by 13.42% and 8.28%, respectively. Exact labeling costs
272.9x the measured `r=6` CPU and is not a deployable repair.

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
- `docs/saq_caq_co0_v2_a2_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`;
- `docs/saq_caq_co0_v2_b0_preparation_spec_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json`;
- `docs/saq_caq_co0_v2_b0_final_preregistration_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_preregistration_evidence_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b0_artifacts_2026_07_11/`;
- `docs/saq_caq_co0_v2_b1_synthetic_runner_validation_2026_07_11.md`;
- `docs/saq_caq_co0_v2_b1_rotation_build_correction_2026_07_12.md`;
- `docs/saq_caq_co0_v2_b1_rotation_build_correction_artifacts_2026_07_12/`;
- `docs/saq_caq_co0_v2_b1_registered_evidence_2026_07_12.md`;
- `docs/saq_caq_co0_v2_b1_registered_artifacts_2026_07_12/`;
- `docs/saq_caq_low_cost_repair_theory_review_2026_07_12.md`;
- `docs/saq_caq_low_cost_repair_sources_2026_07_12.json`;
- `docs/saq_caq_one_shell_synthetic_falsification_2026_07_12.md`;
- `docs/saq_caq_one_shell_synthetic_artifacts_2026_07_12/validation_result.json`;
- `docs/saq_caq_limitation_repair_closure_and_project_pivot_2026_07_13.md`.

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

## V2-B0: Final Preregistration — Completed, PASS

Complete and commit, without encoder execution:

```text
input provenance and expected hashes
cluster-stratified n=50,000 sample inventories
disjoint within-cell base-pair inventories
logical seeds 0,1,2 -> distinct C RNG seeds 1,2,3
production-compatible segmented/whole-view rotation hashes
all arms, controls, estimands, bootstrap tests, output schema, and commands
```

Stop before registered V2-B1 execution.

The next stage requires separate authorization. Implement and synthetic-test
the B1 runner against the frozen preregistration before permitting it to open
any base vector. Runner implementation and real base execution must not be
combined into one unreviewed step.

Do not run V2-A2, inspect dataset artifacts, or design a CAQ repair in the same
step.

## V2-B1 Instrument Validation — Completed, PASS

The frozen-interface C++ runner, source-aligned arm measurements, current
full-code estimator path, code/CSV shards, complete preflight, resource
accounting, and Python 24-hypothesis summarizer are implemented. Release,
ASAN, deterministic PASS/NO-GO, Holm, packing, estimator, zero, and synthetic
I/O tests pass.

This stage did not read registered float artifacts or produce a scientific
result. Real B1 execution requires a separate explicit authorization and must
not be combined with method design.

## V2-B1 First Execution And Rotation Correction — STOPPED / PASS

The first authorized command completed registered artifact hash/shape
preflight and then stopped with `rotation hash mismatch`. It produced zero
encoder rows, pair rows, exact-oracle CPU, and code bytes. The cause was a
build-profile mismatch: B0 rotation hashes used non-AVX Release QR, whereas
the runner generated QR in its AVX/FMA translation unit.

The separately authorized correction isolates rotation generation under the
recorded B0 Release profile and leaves the CAQ path SIMD-enabled. Release and
ASAN validation pass, including 27/27 runner-linked frozen rotation hashes.
This is an instrument correction, not a protocol change or scientific result.

## V2-B1 Registered Execution — Completed, CONDITIONAL PASS

The separately authorized rerun completed all 48 views on one CPU thread and
the frozen summarizer returned `CONDITIONAL_PASS`. All 24 Holm-corrected tests,
materiality bounds, seed checks, and estimator-direction checks pass. The raw
run used 1.90 wall hours and 2.94 GB of serialized output. The exact oracle is
an offline labeler with 272.9x the measured `r=6` CPU cost.

This result establishes only the preregistered limitation. Do not implement a
repair until a bounded related-work/theory review identifies a mechanism that
is novel relative to SAQ/CAQ and can plausibly avoid exact-oracle cost.

## One-Shell Repair Review And Synthetic Test — Completed, NO-GO

The bounded review rejected extra CAQ rounds, alternating scale/assignment,
fixed event windows, complete exact enumeration, and generic branch-and-bound.
It conditionally admitted one exact radius-one Cartesian shell because this is
the minimal product closure of CAQ's unit coordinate move and has at most
`2D` events independent of native bit width.

The implementation matches direct shell enumeration on 6,060 exhaustive
input/code cases covering 110,230 shell codes. The fixed-width implementation
matches the exact integer implementation on 6,066 supported cases and
deterministically abstains on two extreme exponent-span fixtures. Release and
ASAN standalone suites pass.

The complexity gate fails before data access. On deterministic `D=64`,
`B in {9,11}` profiles, the fixed-width shell alone costs `3.579x` to
`7.169x` CAQ; total cost is `4.579x` to `8.169x`, versus the frozen `2.0x`
maximum. The measured path has zero exact-objective fallbacks and 972-1,031
event-order comparisons per encoding, so arbitrary-precision fallback is not
the cause. Do not run its exact-gap-recovery half or attempt to rescue it by
tuning.

## Project-Level Closure — Completed, PIVOT

The project-wide synthesis compares the empirical fixed policy, mixed shared
plans, single-global cost DP, measured planner objective, search scheduling,
graph traversal, transform replacement, lossy projection, and CAQ repair.
None supplies a distinct, overhead-controlled, cross-regime end-to-end method.

The project therefore stops SAQ-centric incremental method development. Keep
the branches as research records and SAQ as a competitive baseline. The next
stage may review broader vector-search problems, but it may not implement one
until a primary-source novelty, complexity, and falsifiability gate passes.

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

The one-shell candidate stops permanently at synthetic complexity because
any frozen cost row above `2.0x` fails the conjunctive method gate. Correctness
does not override this stop. A later direction must begin with a new bounded
primary-source novelty and complexity review; it may cite this result only as
negative evidence.

At project level, do not open another branch whose question is merely how to
modify one SAQ component. A future branch must follow the problem-selection
protocol in the closure synthesis and start clean from `saq-correctness-base`
only after that protocol returns `GO`.

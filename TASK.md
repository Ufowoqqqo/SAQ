# TASK.md

## Active Goal

Preserve the completed `CO-0A` falsification record. The bounded finite-round
CAQ screen is closed under its frozen official-source oracle contract.

Current status:

```text
branch created from saq-correctness-base
bounded primary-source review migrated
new-direction memo migrated
official Extended-RaBitQ pinned at 52b9e6c7ba6c316036cdb04074732fe561966a53
CO-0A source/codebook parity completed: FAIL
CO-0B preregistration deliberately not written: gate did not authorize it
no GIST/CIFAR CO-0 output inspected
no method or contribution established
```

Authoritative documents:

- `docs/saq_limitation_primary_source_review_2026_07_11.md`;
- `docs/saq_limitation_primary_sources_2026_07_11.json`;
- `docs/saq_next_direction_go_no_go_memo_2026_07_11.md`;
- `docs/saq_caq_co0a_official_source_parity_2026_07_11.md`;
- `docs/saq_caq_co0a_artifacts_2026_07_11/source_parity_result.json`.

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

## CO-0B: Preregistration Boundary — Not Authorized

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

## Immediate Next Action

No dataset or method experiment is authorized on this branch. Preserve and
verify the CO-0A evidence:

```text
retain the pinned submodule and source hashes
retain the deterministic counterexample and machine-readable result
do not inspect GIST/CIFAR outputs
do not write the failed-contract CO-0B preregistration
```

Reopening requires an explicit decision to define a different, paper-corrected
and widened exact oracle. That decision must produce a new protocol before any
dataset residual is inspected and must not call the new oracle official-source
parity.

## Stop Rules

The first stop condition fired: official-source parity could not be
established. The direction is stopped under the current contract. It would
also have stopped if the exact feasible codebook differed from SAQ's claimed
mapping, or later if the registered limitation/amplification conditions
failed. It would likewise stop as a research direction if ordinary extra CAQ
rounds closed the gap or exact E-RaBitQ fallback were the only repair.

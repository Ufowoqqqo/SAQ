# A4 V2 Primary-Source Review: Independent Review

Date: 2026-07-14

Reviewer task: `/root/next_step_audit`

Mode: read-only documentation review; no implementation, execution, RNG,
dataset access, or SAQ modification.

Decision: **PASS**

```text
BLOCKER  0
HIGH     0
LOW      0
```

## Reviewed identities

```text
b04d6704ab8a7f3327e84b141487188c7df4d35df6f4ae95efa498d34b53f7fe
  docs/saq_a4_v2_cost_evidence_primary_source_review_2026_07_14.md

6f92ee8f839152b3241c6beb422201f79f8bbd4cead1109f0c8b3be0ff93d9da
  docs/saq_a4_v2_primary_source_metadata_2026_07_14.json

5d8f1403f6884ae0d9b3f0df42fb68a12fe3261b0b6ee3593ea6d7e840951d0c
  docs/saq_a4_v2_cost_evidence_go_no_go_memo_2026_07_14.md
```

`AGENTS.md@402f3d5f...` and `TASK.md@c54daaa0...` were also checked for
authorization and outcome consistency; they belong to the later protocol
commit rather than this review-evidence commit.

## Findings

- Primary-source claims are mapped to sources with explicit support and
  non-support boundaries.
- The positive A4 reference is pinned to pre-outcome commit `3aa2f6e`; the
  later cost failure remains at `9ce1052`.
- Official upstream SAQ `2163ebc` and evaluated correctness baseline
  `bc7829b` are distinguished. The A4 diagnostic bundle is correctly excluded
  from current-SAQ byte, estimator, index, and deployment claims.
- The predecessor `NO_GO_EXACT_SOLVER_COST` remains terminal for its frozen
  pipeline.
- `34,560,000,000 us` is only an internal one-panel admission cap. The new
  figure of merit makes no `5/2`, GIST, CIFAR, two-dataset, or base-cost
  projection.
- Independent checking is accurately limited to exact-rational scalar and
  allocation recomputation plus deterministic block, encoding, and packing
  replay; it makes no global-optimality claim for Lloyd training.
- The result is `GO_PROTOCOL_DESIGN`, not implementation or execution
  authorization.

## Authorization consequence

None. This review permits the already authorized protocol-documentation step
to be finalized. It does not authorize `A4-V2-I`, `A4-V2-PAR`,
`A4-V2-SRUN`, data access, or SAQ modification.

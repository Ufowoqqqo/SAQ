# A4 V2 Protocol Independent Review

Date: 2026-07-14

Decision: **PASS**

Severity count: **0 BLOCKER / 0 HIGH / 0 LOW**

This is a documentation and protocol review. It is not implementation,
parity, synthetic-run, base-data, query, index-build, or SAQ-integration
authorization.

## Reviewed objects

Both independent reviewers read the following exact objects:

| Object | SHA-256 |
| --- | --- |
| `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md` | `c88a273afe0bf73e9d344ff5d41eadc5eba7c3b1adff323f874b0c088eb9e671` |
| `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json` | `fac025ec01a70d366817e40ace0d20cc232e642306fcdd641360693afa33f5e1` |
| `docs/saq_a4_v2_artifact_schema_2026_07_14.json` | `47c174b282ea4333568060bdefd0a78b02cbe9e171cae115ac6cacaa045fb869` |
| `AGENTS.md` | `402f3d5fe531d375d1677dfddb7a022d43d8fb249d52d1d6b7b7123e6adcc72b` |
| `TASK.md` | `c54daaa09eb5cea6f8875d1a3cd8697cf6c330fdd84bbb4d9c02f3803b4f55c7` |

The reviewers were:

- `/root/a4_cost_boundary_audit`, with a separate schema-focused subreview
  by `/root/a4_cost_boundary_audit/schema_final_audit`;
- `/root/exact_dp_primary_sources`.

Each final review returned `PASS`, independently reporting zero blocker, high,
or low findings. Earlier conclusions on superseded hashes did not transfer to
the final objects.

## Closure of review findings

The review loop found and corrected the following protocol defects before the
final hashes were frozen:

1. per-phase byte evidence and construction-versus-evidence publication
   failures were made structurally representable and assigned unique status
   precedence;
2. prelaunch load, memory, disk, environment, and same-user process evidence
   was added to the producer manifest rather than left only in prose;
3. process-conflict classification was reduced to a frozen byte-level marker
   matcher with an exact self-only allowlist and deterministic precedence;
4. the process inventory was made one explicit two-stage effective-UID filter
   that includes zero-tick same-user processes; and
5. the frozen PID filter and same-user initial/final status, stat, cmdline, and
   executable-target preimages were made sufficient for independent replay of
   identity stability and conflict classification.

The final reviewers also confirmed that:

- the exact-rational scalar/allocation claim and deterministic block,
  encoding, and packing replay are not overstated as globally exact block
  optimization;
- the 396-unit prefix, resource ledgers, finite timing/hash DAG, status
  precedence, and artifact schemas are mutually satisfiable;
- the new primary figure of merit remains the complete comparative-instrument
  construction cost, while build, parity, evidence, verifier, archive, memory,
  and byte costs remain explicitly reported;
- the old `5/2` real-dataset projection does not transfer to the new figure of
  merit; and
- `A4-V2-I`, `A4-V2-PAR`, `A4-V2-SRUN`, data access, and SAQ modification are
  separate and currently unauthorized.

## Static verification

The final objects passed JSON parsing, duplicate-key review, local `$ref`
resolution, contract-to-schema reference matching, object/array closure,
marker-list equality and ordering, phase/status consistency, and
`git diff --check`. No implementation was compiled or run, no RNG was invoked,
and no synthetic or benchmark data was read.

## Decision boundary

The maximum supported outcome is:

```text
PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION
```

The predecessor A4-1S `NO_GO_EXACT_SOLVER_COST` remains terminal evidence for
its own frozen protocol. This review neither overturns that result nor shows
that A4 V2 is computationally feasible. Any next stage requires a new,
explicit user authorization naming exactly one of `A4-V2-I`, `A4-V2-PAR`, or
`A4-V2-SRUN`; authorization is non-transitive.

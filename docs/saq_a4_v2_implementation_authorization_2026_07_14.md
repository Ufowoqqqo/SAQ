# A4 V2 Implementation Authorization

Date: 2026-07-14

Authorized stage: **A4-V2-I**

Status: **SOURCE_IMPLEMENTATION_AUTHORIZED**

## Authority

After the reviewed A4 V2 protocol was committed at `f86a51d`, the user
explicitly authorized `A4-V2-I` with the instruction:

```text
授权 A4-V2-I
```

This authorization is non-transitive. It permits source and implementation-
binding documentation needed for the producer, independent verifier,
archive/finalizer, phase timers, resource ledgers, and later frozen parity
interfaces. It does not authorize importing or executing those sources.

The user later authorized `A4-V2-P-ERRATUM`.  The committed and independently
reviewed timing-closure erratum does not authorize PAR execution; it changes
the source contract that this I-stage implementation must satisfy.  For every
post-erratum revision the unique runtime `protocol_identity` is the composite
authority manifest
`docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json`.  The original
preregistration remains an explicitly named parent-provenance identity, not a
second runtime protocol head.

## Current stage boundary

```text
A4-V2-I     source implementation and static independent review  AUTHORIZED
A4-V2-PAR   build and frozen parity execution                    NOT_AUTHORIZED
A4-V2-SRUN  one logical synthetic admission event               NOT_AUTHORIZED
data        benchmark/base/query/index reads                     NOT_AUTHORIZED
SAQ         library, index, estimator, packing, search changes   NOT_AUTHORIZED
```

In particular, this stage permits no build-system invocation, compiler,
Python import of implementation modules, syntax/test runner, native binary,
parity fixture, random-number generation, synthetic-panel construction,
artifact generation, benchmark read, or SAQ modification. Static source
inspection, repository-history inspection, focused source edits, Git diff
checks, independent source review, commits, and push are permitted.

The B/P process-boundary implementation may impose the parameter-free
identifiability condition required to report noncumulative phase RSS: a fresh
attempt worker's natural registered-work `wait4` peak must cover the
supervisor SELF HWM frozen before its fork. This adds no fixture, threshold,
allocation guard, or execution authority. Failure produces no PAR seal and
cannot be interpreted as a scientific outcome.

## Frozen parent objects and additive authority

The following reviewed objects remain byte-for-byte frozen and are not edited
to encode the later authorization:

- `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md`;
- `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`; and
- `docs/saq_a4_v2_artifact_schema_2026_07_14.json`.

Their historical `NOT_AUTHORIZED` fields record the state at protocol freeze.
This separately committed authorization note and the branch task state record
the later user decision without rewriting that history.

The additive authority objects are the reviewed PAR-report timing-closure
erratum, its machine-readable contract, its closed 5,171-byte-maximal PAR-seal
schema, and the composite authority manifest that binds the parent and
erratum objects.  Source may implement that correction during A4-V2-I, but
may not execute it until a separate `A4-V2-PAR` authorization.

## Implementation-only completion rule

`A4-V2-I` is complete only when all required source is committed and an
independent static review of the exact committed source returns no unresolved
blocker, high, or medium finding. Static review is not parity. It cannot establish
correctness, executable compatibility, resource feasibility, or a scientific
gate result.

The maximum outcome of this stage is:

```text
SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS
```

That outcome permits only asking whether to authorize `A4-V2-PAR`.

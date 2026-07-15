# A4 V2 Cache/Staging Policy Authorization

Date: 2026-07-15

Authorized stage: **A4-V2-CACHE-P**

Status: **CACHE_STAGING_POLICY_DOCUMENTATION_AUTHORIZED**

## 1. Context and authority

The historical `A4-V2-PAR` event remains terminal at:

```text
ARTIFACT_INVALID
REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

The later exact source-repair commit
`e48df4523f99c085cfcb83623664054b5f9ae6f7` passed static review at review
head `c401daeba021d79d7200bb7c436b923a3c66e309`. It did not resolve or
authorize handling of the five quarantined Python bytecode files or the
empty PAR staging directory.

After being told that the next admissible step was a separate documentation-
only stage for bytecode-cache determinism and bounded staging/cache residual
handling, with `A4-V2-PAR-R1` still requiring later separate authorization,
the user instructed:

```text
授权
```

This instruction is bound narrowly as authorization for `A4-V2-CACHE-P`.
It is not authorization for cleanup, a source repair, environment mutation,
or `A4-V2-PAR-R1`.

## 2. Permitted work

This stage may:

1. perform a bounded review of official CPython documentation/source and
   committed local A4-V2 source and protocol objects;
2. state whether and when existing bytecode can be read, when new bytecode
   can be written, and which interpreter flags/environment values are
   relevant to a deterministic admission boundary;
3. design a fail-closed, exact-inventory, no-follow disposition protocol for
   the already named quarantined cache files and empty staging directory;
4. specify later-stage receipts, identity checks, error precedence, byte/cost
   accounting, and pre/postconditions without performing those operations;
5. state whether a separately authorized minimal source/policy implementation
   stage is required before a corrected PAR event can even be proposed; and
6. add focused documentation, machine-readable contracts, AGENTS/TASK status,
   independent exact-commit review, push, and the mandatory Meeting Summary
   Handoff.

The review may use committed records of the residual paths and no-follow
metadata. It must not open or interpret any quarantined bytecode payload or
use any residual as evidence.

## 3. Frozen source and scientific boundary

Throughout this documentation-only stage:

- all 35 reviewed implementation-source blobs, their path closure, the
  implementation manifest, and source-tree SHA-256
  `8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`
  remain unchanged;
- the parent protocol, erratum, artifact schemas, parity inventory, RNG,
  FOM, thresholds, timing/byte ledgers, scientific claims, and historical
  terminal result remain unchanged;
- no Python interpreter, import, `py_compile`, compiler, build, native
  executable, fixture, RNG, conductor, or test may run;
- no cache or staging residual may be deleted, renamed, copied, chmodded,
  imported, reused, or have its payload read;
- no build/output tree, generated scientific artifact, dataset, benchmark,
  base, query, ground truth, index, or historical untracked result may be
  opened or generated; and
- no SAQ/CAQ, quantizer, estimator, index, or search code may be modified.

Official primary-source review and static repository inspection are research
governance inputs, not empirical evidence and not contributions.

## 4. Required protocol decisions

The documentation must resolve before any later operation is authorized:

1. why merely suppressing bytecode writes is or is not sufficient in the
   presence of pre-existing cache files;
2. the exact clean-start inventory and no-follow identity rules;
3. whether residual disposition is a separately reviewed preparation event,
   and how its CPU, wall time, bytes, and failures are recorded without being
   hidden from the end-to-end ledger;
4. how the interpreter cache mode is bound before startup and independently
   attested after startup;
5. the rule for any unexpected, changed, missing, non-regular, linked, or
   newly created path;
6. the boundary between a documentation decision, any later source/policy
   implementation, and a later one-shot PAR execution authorization; and
7. whether the protocol is implementable without changing the frozen
   scientific method, parity inventory, or estimator.

The protocol must prefer a fail-closed decision over silently treating
ignored or untracked files as absent.

## 5. Completion and later boundary

The maximum result is:

```text
CACHE_STAGING_POLICY_REVIEW_PASS
```

That result establishes only a reviewed policy/protocol. It is not cleanup,
implementation readiness, `PASS_PARITY`, a valid PAR authority, synthetic
evidence, an SAQ result, or a database-systems contribution.

If the protocol requires source, environment, or residual-disposition work,
that work needs a new explicit authorization and an independently reviewed
exact commit/receipt. Even after that work, `A4-V2-PAR-R1` remains
`NOT_AUTHORIZED` until separately authorized by the user. `A4-V2-SRUN`, all
data access, and all SAQ changes remain separately unauthorized.

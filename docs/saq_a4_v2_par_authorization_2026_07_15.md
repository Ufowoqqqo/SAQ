# A4 V2 Build/Parity Authorization

Date: 2026-07-15

Authorized stage: **A4-V2-PAR**

Status: **BUILD_AND_FROZEN_PARITY_AUTHORIZED**

## Authority

After `A4-V2-I` reached `SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`, the user
explicitly authorized the next stage with the instruction:

```text
授权 A4-V2-PAR build/parity gate
```

This authorization is additive and non-transitive. It does not rewrite the
historical `NOT_AUTHORIZED` fields in the frozen preregistration, contract,
artifact schema, implementation manifest, or prior authorization note.

## Exact authorized event

After this focused authorization/status change is committed, pushed, and
independently reviewed, its clean exact commit is the PAR execution base. The
review must prove that all 35 implementation-source blobs, the canonical
implementation manifest, and source-tree SHA-256
`d5b8374ff2bfb967e0fbf758e2012029356ef779122681ed4a5a9d901e727cc7`
remain identical to reviewed source target `482c401`.

Exactly one top-level command is authorized from the repository root with the
three named environment variables set to `1`:

```text
MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python script/run_arbitrary_cardinality_a4_v2.py \
  par docs/saq_a4_v2_par_artifacts_2026_07_14
```

The conductor itself must perform the four frozen clean build commands and
the complete frozen parity inventory. No manual or preliminary build is
authorized. The required parity fixtures include deterministic
`PCG64(20260713)` generation for exactly 256 scalar cases and 64 block cases;
this is PAR fixture generation, not the later 8,192-by-128 SRUN panel or a
synthetic admission observation.

The command may import the reviewed PAR implementation, inspect its registered
host/toolchain/numeric identities and preconditions, read the protocol-defined
Linux process/environment interfaces, create the two fixed ignored build
trees, and atomically publish only the fixed PAR artifact directory. Build,
parity, CPU, wall, RSS, temporary-byte, and evidence-byte work must remain
inside the conductor's `B_build` and `P_parity` ledgers.

## Still not authorized

This decision does not authorize:

- `A4-V2-SRUN`, the 396 construction units, the full synthetic panel, or any
  synthetic admission decision;
- benchmark/base/query/centroid/cluster-id/ground-truth/index reads;
- SAQ/CAQ, index, estimator, packing, or search changes;
- any parameter, seed, fixture, compiler, flag, machine, threshold, resource
  ceiling, path, or evidence-boundary change; or
- any automatic repair, retry outside the frozen external-signal rule, or
  continuation to SRUN after a PAR result.

If build, parity, identity, resource accounting, or atomic publication fails,
the failure is an implementation/artifact/control/resource outcome at the
registered precedence, not a scientific no-go. No source correction is
authorized by this instruction. Any correction requires a new reviewed clean
source commit and a new explicit authorization for the affected stage.

## Completion rule

A successful command is not yet reviewed evidence. The immutable PAR tree
must be committed as `P`, independently reviewed without changing that tree,
and recorded in a separate review commit `R`. The maximum possible outcome is
committed and independently reviewed `PASS_PARITY` evidence and PAR authority
readiness; it is not synthetic feasibility, a method claim, or a database-
systems result. Only after the exact `R` commit is pushed and handed off to
`saq-meeting-summary` may the user be asked separately whether to authorize
`A4-V2-SRUN`.

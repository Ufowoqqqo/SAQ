# Independent Review: A4 V2 PAR Pre-Build Artifact-Identity Failure

Date: 2026-07-15

Reviewed stage: `A4-V2-PAR`

Exact review target:
`30dfada9917fc225168963331ea5d57dbbe56525`

Frozen runtime status: **ARTIFACT_INVALID**

Independent review verdict: **PASS -- 0 findings at LOW or above**

Project interpretation: **REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY**

## 1. Review scope and independence

Three independent read-only tracks reviewed the exact committed failure
record and its reachable source:

1. producer/control-flow review checked the exact `run_par` order, subprocess
   boundary, unstarted work inventory, imports, residual files, and source
   immutability;
2. supervisor/protocol review checked frozen status precedence, one-event
   authorization consumption, retry/repair prohibition, and scientific claim
   ceiling; and
3. filesystem/Git review independently compared the committed blobs with the
   quarantined staging directory, ignored caches, absent build/PAR outputs,
   source identities, branch identity, and nonevidence boundary.

The review used only Git-object inspection, text/source inspection, no-follow
filesystem metadata, directory membership, symlink-chain inspection, hashes,
sizes, and diff checks. It did not invoke Python, import an implementation
module, build, run a fixture, generate RNG, read a dataset, or modify source.

## 2. Exact Git identities

```text
target  30dfada9917fc225168963331ea5d57dbbe56525
parent  2e983a0280ae96cc0f098d0a998a45c6486ad1e9
tree    166bb15a45ffc986b37723e037487be0d66885b0

AGENTS.md
  ae89a9b64e74222d9a588323ec6fd7a473573eaa
TASK.md
  8c45f803de533a69501fe319d7026bf4e15a17e0
failure memo
  783c14f59bd60c13c718d2c7bf66d3b0788ccdd9
```

The target modifies exactly those three governance/result files. Relative to
execution base `2e983a0`, all 35 implementation-source paths, the canonical
implementation manifest, the parent preregistration/contract/schema, and all
other frozen authority objects are unchanged. No build tree, Python cache,
staging directory, final directory, PAR artifact, or execution-authority
object is present in the target Git tree. `git diff --check` passes.

## 3. Reproduced failure boundary

All tracks confirmed this exact ordered prefix:

```text
bootstrap start snapshots and post-snapshot module imports
repository/argv/thread/output/Git/staging-absence checks
mkdir empty staging (0700)
both build directories confirmed absent
construct initial PhaseBoundary
read Path(sys.executable) with O_NOFOLLOW
/bin/python terminal symlink -> ELOOP / Errno 40
outer OSError handler -> ARTIFACT_INVALID, exit 3
```

This occurs before host/NumPy/process-inventory observation and before any
B/P worker. The independent source inspection therefore confirmed that no
CMake, compiler, native child, NumPy authority, PCG64, scalar/block fixture,
B/P receipt, resource/byte ledger, manifest, parity summary, artifact index,
PAR seal, or final publication occurred.

The observed `/bin/python -> ./python3 -> python3.9` chain explains the
terminal no-follow failure. `ELOOP` here is the Linux diagnostic for refusing
a terminal symlink; no reviewer inferred a cyclic link chain.

## 4. Filesystem reconciliation

The exact post-failure residuals remained:

- one mode-`0700`, zero-child
  `docs/saq_a4_v2_par_artifacts_2026_07_14.staging/` directory with the memo's
  recorded UTC mtime; and
- five ignored mode-`0600` `.pyc` files whose names and byte sizes exactly
  match the failure memo.

The `build/` root, both fixed build directories, final PAR directory,
execution-authority directory, and every build manifest, parity summary,
artifact index, PAR seal, and review binding were absent. The residuals are
untracked/ignored WIP and are not evidence. The exact target correctly commits
none of them.

## 5. Status, retry, and claim review

The frozen order assigns executable identity/artifact-boundary failure to
`ARTIFACT_INVALID`, precedence 1. The exact implementation emitted that
status, so the review does not relabel it as a precondition, implementation,
resource, parity, representation, or scientific outcome.

The one-retry rule applies only to a sealed B/P worker attempt terminated by
an external signal. No worker started and no signal occurred. All tracks
therefore agreed that the consumed authorization permits no second top-level
invocation, staging cleanup for retry, alternate/resolved Python path, PATH
change, manual build, source hotfix, SRUN, data read, or SAQ modification.

The maximum supported conclusion is:

```text
ARTIFACT_INVALID
REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

There is no P artifact commit, PAR-review R commit, `PASS_PARITY`, scientific
no-go, or evidence about arbitrary-cardinality quantization. Any correction
requires a new clean source commit, independent source review, and a new
explicit authorization for the affected PAR stage.

## 6. Handoff decision

The exact terminal result is now committed and independently reviewed. After
this review memo and branch status are committed, exact-reviewed, and pushed,
the required Meeting Summary Handoff must synchronize only the reviewed Git
facts and claim ceiling. It must not synchronize the empty staging directory,
ignored caches, console output, or other WIP as evidence.

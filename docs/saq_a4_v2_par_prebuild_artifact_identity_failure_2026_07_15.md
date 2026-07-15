# A4 V2 PAR Pre-Build Artifact-Identity Failure

Date: 2026-07-15

Stage: `A4-V2-PAR`

Frozen status: **ARTIFACT_INVALID**

Stage interpretation: **STOPPED_NO_VALID_PAR_AUTHORITY**

Scientific interpretation: **NO_SCIENTIFIC_DECISION**

## 1. Authority and exact invocation

The user explicitly authorized `A4-V2-PAR build/parity gate`. That decision
was recorded, independently reviewed, and pushed at clean execution base:

```text
2e983a0280ae96cc0f098d0a998a45c6486ad1e9
```

The exact authorized command was then invoked once from the repository root:

```text
MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python script/run_arbitrary_cardinality_a4_v2.py \
  par docs/saq_a4_v2_par_artifacts_2026_07_14
```

It returned exit code `3`, emitted no stdout, and emitted exactly this stderr
line:

```text
ARTIFACT_INVALID: [Errno 40] Too many levels of symbolic links: '/bin/python'
```

No second top-level invocation was made.

## 2. Ordered failure boundary

Static control-flow inspection and the observed filesystem state agree on the
following exact prefix:

1. the bootstrap captured its registered initial CPU/wall snapshots and
   imported the post-snapshot runner/PAR modules;
2. the conductor passed its repository-root, exact argv, thread-environment,
   fixed output-root, clean Git, and staging-absence checks;
3. it created the fixed mode-`0700` empty staging directory, then confirmed
   both build directories absent and constructed the initial in-memory phase
   boundary;
4. before host/numeric/NumPy authority collection, process inventory, logical
   run identity, or any phase worker, it attempted to read
   `Path(sys.executable)` as a no-follow regular identity source; and
5. `sys.executable` was `/bin/python`, whose terminal path object is a symbolic
   link. Linux `os.open(..., O_NOFOLLOW)` returned `ELOOP` (`Errno 40`), and
   the runner's frozen outer `OSError` handler emitted `ARTIFACT_INVALID` and
   returned `3`.

The error text is the normal Linux `O_NOFOLLOW` diagnostic for a terminal
symlink; it is not evidence of an actual cyclic link chain. Read-only host
inspection recorded:

```text
command -v python       /bin/python
/bin/python             -> ./python3
/bin/python3            -> python3.9
resolved regular file   /usr/bin/python3.9
```

The frozen command names `python`, while the conductor requires the resulting
`sys.executable` path object itself to be a no-follow regular file. Those two
requirements are incompatible on the pinned host as observed.

## 3. Work that did not occur

The failure preceded `_launch_phase_worker` and `_run_fresh_phase_worker`.
Consequently:

- no `B_build` or `P_parity` attempt began;
- no B/P receipt, resource ledger, or byte ledger exists;
- no CMake, compiler, Ninja, native producer, or native verifier ran;
- neither fixed build directory was created;
- NumPy distribution authority was not collected, NumPy was not imported by
  the PAR fixture path, and no `PCG64`, scalar case, block case, or other
  parity fixture was generated or executed;
- no build manifest, parity summary, artifact index, or PAR seal exists; and
- no atomic final PAR directory was published.

This is therefore not a parity mismatch and not a resource observation.

## 4. Residual filesystem state

The only PAR-output sibling is the empty quarantined directory:

```text
docs/saq_a4_v2_par_artifacts_2026_07_14.staging/
```

It had mode `0700`, zero children, and observed UTC mtime
`2026-07-15 06:01:27.544529150 +0000`. The final artifact directory,
`build/a4_v2/`, and `build/a4_v2_verifier/` were absent.

Post-snapshot module imports also created five ignored Python cache files:

```text
script/__pycache__/a4_v2_evidence.cpython-39.pyc       29,837 bytes
script/__pycache__/a4_v2_parity.cpython-39.pyc        73,739 bytes
script/__pycache__/a4_v2_producer.cpython-39.pyc      38,151 bytes
script/__pycache__/a4_v2_producer_wire.cpython-39.pyc 44,535 bytes
script/__pycache__/a4_v2_runner.cpython-39.pyc       178,276 bytes
```

The empty staging directory and ignored cache files are WIP/non-evidence.
They are not tracked or committed and must not be synchronized to the Meeting
Summary as evidence. They remain quarantined; this stage grants no cleanup-
and-retry authority.

## 5. Frozen classification and retry rule

The registered order assigns executable identity and artifact-boundary
failures to `ARTIFACT_INVALID`, precedence order 1. The implementation's exact
exit and stderr agree with that classification. Root-cause discussion may
describe a command/identity compatibility defect, but it must not relabel the
frozen result as `PRECONDITION_NOT_MET`, `IMPLEMENTATION_INVALID`, a parity
failure, or a scientific no-go.

The one-retry rule applies only inside the conductor to a sealed B/P worker
attempt terminated by an external signal. No B/P attempt started and no
external signal occurred, so that rule is inapplicable. The authorization
covered one top-level PAR event; it does not permit deletion of staging and a
second invocation, substitution of `/usr/bin/python3.9`, PATH manipulation,
manual symlink dereference, preliminary build, or a source hotfix.

Any correction requires a new clean implementation commit, independent source
review, and a new explicit user authorization for the affected PAR stage.
Neither correction nor another PAR attempt is currently authorized.

## 6. Decision

`A4-V2-PAR` stops at:

```text
ARTIFACT_INVALID
STOPPED_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

There is no P artifact commit, independent PAR review commit R,
`PASS_PARITY`, synthetic feasibility result, SAQ limitation result, method
claim, or systems evidence. `A4-V2-SRUN`, data access, and SAQ modification
remain unauthorized.

A strict SIGMOD/VLDB/ICDE reviewer should treat this only as an artifact-
validation failure that falsifies readiness of the frozen conductor on its
pinned host. It adds no evidence for or against arbitrary-cardinality
quantization. This memo must itself be committed and independently reviewed;
only then may its terminal stage status be synchronized through the required
Meeting Summary Handoff.

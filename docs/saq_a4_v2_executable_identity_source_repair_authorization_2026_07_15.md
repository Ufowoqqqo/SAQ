# A4 V2 Executable-Identity Source-Repair Authorization

Date: 2026-07-15

Authorized stage: **A4-V2-I-R1**

Status: **EXECUTABLE_IDENTITY_SOURCE_REPAIR_AUTHORIZED**

## 1. Context and authority

The reviewed `A4-V2-PAR` invocation remains terminal at:

```text
ARTIFACT_INVALID
REVIEWED_TERMINAL_NO_VALID_PAR_AUTHORITY
NO_SCIENTIFIC_DECISION
```

Its exact execution base was `2e983a0`, terminal result was `30dfada`, and
independent review head was `fd5367e`. The failure occurred before B/P because
the conductor applied a terminal no-follow read to the `/bin/python` symlink.

Immediately after the completed handoff stated that the next admissible step
was a new clean executable-identity source correction and independent source
review, followed by a later explicit PAR reauthorization, the user instructed:

```text
继续
```

This instruction is bound narrowly as authorization for `A4-V2-I-R1`. It is
not a revival of the consumed PAR event and is not authorization for
`A4-V2-PAR-R1`.

## 2. Permitted correction

The stage may change only the pre-build CPython leader-identity acquisition:

1. identify the already-running interpreter from a stable descriptor for
   `/proc/self/exe`, while independently requiring the intentionally followed
   `sys.executable` pathname to identify the same regular inode;
2. use one bounded, full, EOF-checked, before/after-stable read of that running
   image for the already-frozen leader SHA-256 and size fields;
3. apply the same identity semantics at the PAR conductor, later runner
   admission/receipt sites, and a physically independent verifier site;
4. leave every generic document, artifact, tree, and native-binary reader at
   its existing no-follow boundary.

The implementation may edit only these source paths if static inspection
shows each is necessary:

```text
script/a4_v2_parity.py
script/a4_v2_runner.py
script/a4_v2_verifier.py
```

It may also update the implementation binding, source-provenance crosswalk,
canonical 35-source manifest, AGENTS/TASK status, and one independent source-
review memo. The source closure must remain exactly the same 35 paths. No
native scientific source, producer solver, allocation, block, representation,
packing, fixture, or RNG code may change.

The repaired manifest's existing `authorization_identity` must name this
additive correction receipt, which inherits the original A4-V2-I authority
without rewriting it. No manifest/schema key is added. The runner's exact
and independent verifier's exact document-identity expectations may change
only enough to enforce that binding.

## 3. Frozen invariants

The following remain byte-frozen or value-frozen:

- parent preregistration, machine-readable contract, artifact schema, PAR-
  report erratum, and composite protocol authority;
- exact top-level `python ... par ...` argv, output path, host, compiler,
  build commands, numeric libraries, thread variables, and toolchain;
- the six-field environment-preimage shape and the existing leader SHA-256
  and size field meanings;
- parity inventory, `PCG64(20260713)` seeds, dimensions, cases, ordering, and
  expected values;
- FOM, thresholds, timers, byte/resource ceilings, ledgers, receipt schemas,
  retry rule, status precedence, publication rules, and artifact paths; and
- every scientific claim and the historical `ARTIFACT_INVALID` result.

Resolving a pathname and then opening it is not an admissible substitute for
identifying the already-running image. The correction must not weaken
`O_NOFOLLOW` for ordinary artifacts or silently follow arbitrary artifact
links.

## 4. Static-only boundary

Before any source edit, this authorization receipt and focused AGENTS/TASK
change must be committed, pushed, and independently exact-reviewed while
proving that all 35 implementation-source blobs, the implementation manifest,
and source-tree SHA-256
`d5b8374ff2bfb967e0fbf758e2012029356ef779122681ed4a5a9d901e727cc7`
remain unchanged from `482c401`/`fd5367e`.

The repair stage then permits static source inspection, focused edits, SHA-256
and byte-size recomputation, canonical manifest recomputation, Git diff checks,
independent static review, focused commits, push, and the required Meeting
Summary Handoff. It permits no Python import, `py_compile`, syntax/test runner,
compiler, build, native command, fixture, RNG, generated scientific artifact,
dataset read, or SAQ modification.

The currently empty PAR staging directory and five ignored bytecode files
remain quarantined non-evidence. They may be inspected by no-follow metadata
only; they may not be deleted, renamed, imported, or reused under this stage.
Static review identified a separate bytecode-cache determinism question, but
it was not causal to the executable-identity failure and is outside this
authorization. I-R1 must not add a cache admission rule or bytecode mode.

## 5. Completion and later boundary

The maximum outcome is:

```text
SOURCE_REPAIR_STATIC_REVIEW_PASS
```

That outcome establishes only a reviewed source correction. It is not
`PASS_PARITY`, artifact execution readiness, feasibility evidence, a
quantization result, or a research contribution.

A later `A4-V2-PAR-R1` remains `NOT_AUTHORIZED`. Its separate authorization
must bind the new reviewed source/manifest/tree. It cannot be opened until a
separate explicit decision resolves bytecode-cache determinism and bounded
handling of the named quarantined staging/cache residuals. Only then could it
permit at most one corrected frozen conductor invocation. `A4-V2-SRUN`, all
data access, and all SAQ changes remain separately unauthorized.

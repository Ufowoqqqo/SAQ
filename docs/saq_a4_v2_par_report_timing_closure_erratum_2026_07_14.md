# A4 V2 PAR-report timing-closure erratum

- Date: 2026-07-14
- Erratum: `A4-V2-P-ERRATUM-1`
- Parent protocol commit: `f86a51d6923409d735dda0ee40f88fd2e0ad2e43`
- Stage outcome ceiling: `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS`

## 1. Decision and authority

This additive erratum corrects one measurement-closure defect discovered
during source-only implementation inspection. It does not rewrite the three
reviewed parent objects at `f86a51d`:

- `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md`;
- `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`; and
- `docs/saq_a4_v2_artifact_schema_2026_07_14.json`.

For A4 V2 revisions after this erratum, the composite authority is the parent
objects plus this prose erratum, its machine-readable contract, and its closed
PAR-seal schema. Their exact identities are registered in
`docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json`. Where the parent
objects say that `F_trailer` is the sole timing-closure exclusion, this erratum
supersedes only that statement and registers the additional finite
`PAR_report` closure below. All other parent clauses retain authority.

This correction changes no scientific computation, parity fixture, retry
policy, primary figure of merit, threshold, status precedence, machine,
dataset boundary, or future-stage authorization.

## 2. Defect

The parent protocol places `B_build` and `P_parity` inside
`T_study_metered`. It also requires their terminal CPU, wall, RSS, and byte
receipts to be sealed in committed and independently reviewed PAR authority.
The final `P_parity` values do not exist until the terminal P snapshot. If a
wrapper then serializes, writes, flushes, or publishes the receipt while
claiming that work is still inside P, a new terminal value is required and the
receipt recurses. Sampling before publication instead silently omits that
publication work. The parent protocol explicitly solved the same problem only
for `F_trailer`.

Implementation WIP that samples P and then performs file reads, tree walks,
stats, hashes, comparisons, artifact discovery, or byte-ledger derivation is
invalid under both the parent protocol and this erratum. No such WIP is
evidence.

## 3. Amended phase boundary

The metered formula is unchanged:

```text
T_study_metered = B_build + P_parity + T_instrument
                  + E_emit + V_replay + E_archive_body
```

Two, and only two, finite reporting closures are outside it:

```text
PAR_report   one-file PAR authority closure after terminal P_parity
F_trailer    three-file final-study closure after E_archive_body
```

`PAR_report` is not a metered phase, does not appear in the eight-entry phase
resource or byte ledgers, and does not enter `T_instrument` or
`T_study_metered`. Its duration and RSS are not sampled or interpreted. Its
sole created file and directory-publication metadata are disclosed exactly as
specified below. Outside these two registered closures, no wrapper may perform
unmetered scientific, model, encoding, comparison, validation, hash, receipt,
or publication work.

No separate `B_build` reporting closure exists. Every build manifest, build
identity, build byte operand, and build hash is complete before the B terminal
snapshot. That same snapshot is `P_parity`'s start. Forming the B receipt after
the snapshot is therefore charged to P. A prior interrupted B attempt's
receipt is formed during its next metered attempt; without a permitted next
attempt there is no admissible PAR authority.

## 4. Required state before the terminal P snapshot

Before the single terminal snapshot of the final successful `P_parity`
attempt, the PAR supervisor must have completed all of the following:

1. reaped every child and closed every child output;
2. completed every frozen correctness, control, representation, repeatability,
   membership, command, toolchain, and identity comparison;
3. constructed, canonicalized, written, flushed, and closed the build manifest
   and parity summary;
4. enumerated the exact staging-directory membership and rejected every
   missing, extra, duplicate, nonregular, or symlink entry;
5. constructed, canonicalized, written, flushed, and closed
   `artifact_index.json`, which indexes every B/P evidence file inside the PAR
   artifact staging directory except itself and `par_seal.json`; build-tree
   binaries remain at their fixed paths and are bound directly by the build
   manifest and seal;
6. read and SHA-256 hashed every protocol, schema, source-manifest, source-tree,
   tool, binary, build, parity, and artifact-index identity needed by the seal;
7. completed every tree walk, stat, size observation, byte-class assignment,
   aggregate byte-ledger value, and operational-cap operand;
8. preconstructed all fields of the fixed seal other than values obtained from
   the terminal P snapshot; and
9. fsynced all indexed files and the staging directory.

The terminal snapshot captures in one boundary operation the final P process-
family SELF+CHILDREN CPU, monotonic wall, peak RSS, and canonical UTC end time.
It closes P. No child, file descriptor owned by a child, scientific object, or
unaccounted output may cross that boundary.

## 5. Exact `PAR_report` closure

After the terminal P snapshot, `PAR_report` may perform only these operations,
in order:

1. inject the already captured terminal integers and UTC string into the fixed
   terminal P receipt;
2. perform frozen bounded integer subtraction, addition, reconciliation, and
   operational-ceiling comparisons over already captured values;
3. assemble the already fixed 15-key seal object;
4. canonical-encode that object once and require its in-memory byte length to
   be no greater than both the exact schema maximum registered by the maximal
   instance and the coarse 65,536-byte guard;
5. create only
   `docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json`, using exclusive,
   no-follow, regular-file semantics;
6. write the already encoded bytes, fsync and close the file, fsync the exact
   `docs/saq_a4_v2_par_artifacts_2026_07_14.staging` directory, atomically
   rename that directory without replacement to
   `docs/saq_a4_v2_par_artifacts_2026_07_14`, and fsync its parent; and
7. close remaining descriptors and exit with no post-publication status
   output.

The exact seal keys are:

```text
artifact_index
artifact_kind
build_manifest
implementation_commit
parity_pass
parity_summary
phase_byte_ledger
phase_receipts
producer_native
protocol
schema
schema_version
source_manifest
source_tree_sha256
verifier_native
```

`protocol` identifies the composite protocol-authority manifest. `schema`
identifies the unchanged SRUN artifact-schema registry. The dedicated
PAR-seal schema is itself bound by the composite authority manifest. Child
argv, toolchain inventory, parity inventory, and detailed status belong in
the already metered build manifest or parity summary; they are not duplicate
top-level seal authorities.

After the P snapshot, `PAR_report` must not import a module; invoke or wait for
a child; sample a clock or resource counter; read, parse, stat, list, discover,
compare, validate, or hash a file; derive or recompute a byte operand; allocate
or train a model; generate RNG input; execute a parity fixture; make a
scientific decision; or compute a new artifact identity. It may not rewrite
an indexed artifact or the seal.

## 6. Retries and receipt closure

The parent one-restart rule is unchanged. A successful seal therefore carries
two through four receipts in exactly one of these orders:

```text
B0, P0
B0, B1, P0
B0, P0, P1
B0, B1, P0, P1
```

Attempt ids are contiguous within each phase. The terminal attempt for each
phase has `exit_reason=PHASE_COMPLETE`; an earlier attempt exists only for the
single permitted external signal interruption, is marked `DISCARDED`, and is
fully charged. All receipts share the frozen logical-run and authority
identities required by the parent contract. The seal has exactly two aggregate
`phase_byte_ledger` entries, `B_build` then `P_parity`; each sums or peaks every
attempt of that phase. The successful B and P receipts use
`staging_disposition=NONE` because atomic publication belongs to
`PAR_report`, not to either metered phase.

## 7. Nonrecursive byte and Git identity

`par_seal.json` embeds neither its own size or SHA-256 nor a total that includes
itself. Its exact excluded byte count and SHA-256 are taken from the unchanged
Git blob at the clean independent PAR-review commit. Independent review must
report its path, size, SHA-256, schema result, and the result of the registered
maximal-instance bound. `par_seal.json` bytes are not charged to P. All other
PAR artifact bytes and all artifact-index work remain charged to B or P.

The closed PAR-seal schema fixes every path, hash width, timestamp width,
integer representation bound, receipt order, and array cardinality. Its
canonical maximal instance uses four legal receipts and maximum values. The
exact byte length of that committed instance is the normative seal ceiling;
65,536 bytes is only a coarse safety guard. Crossing either bound produces no
valid PAR seal and is not permission to enlarge the schema or report.

The future authority DAG is strictly ordered:

```text
I  reviewed implementation commit
P  PAR artifact commit produced from I
R  independent PAR-review commit, preserving P's seal and index bytes
E  later clean execution-authority commit, strictly after R
```

Thus `I < P < R < E`. Before any later SRUN, E must bind I, P, and R and verify
that exact `git show R:path` bytes for `par_seal.json`, `artifact_index.json`,
and the independent review memo equal the admitted worktree bytes. A separate
`par_review_binding.json` at E carries those prior identities; the PAR seal
does not predict a future commit. Git staging, commits, and human review remain
the already declared NOT_MEASURED implementation/review work, never
`PAR_report` or scientific evidence-generation time.

## 8. Failure semantics

A resource-cap crossing detected from the terminal P values, seal-size
overflow, nonexclusive create, short write, fsync failure, rename failure,
parent-fsync failure, or any attempt to perform a forbidden post-snapshot
operation yields no valid PAR authority. The staging directory is logically
discarded and must never be admitted as evidence. It may remain quarantined
for later human cleanup; no recursive cleanup is hidden in `PAR_report`.
`A4-V2-SRUN` remains unauthorized and cannot be requested on that state.

`PAR_report` cannot turn a parity mismatch, implementation defect, resource
failure, or incomplete artifact into a pass. A clean atomic PAR directory,
the reviewed Git binding, and independent review are all required before the
later stage can even be considered.

## 9. Unchanged boundary

This erratum does not change:

- the A4-reference-equivalent four-arm target or any exact/tie semantics;
- the 396-unit construction, parity inventory, seeds, dimensions, cardinality
  range, block starts, representation, or independent replay;
- `T_instrument`, its 34,560,000,000-microsecond cap, or any operational cap;
- the eight metered phase entries or `F_trailer`'s three-file closure;
- the status-precedence table or the old terminal A4-1S result;
- the query-unaware/data boundary; or
- the requirement for separate explicit authorization of `A4-V2-PAR` and
  `A4-V2-SRUN`.

The erratum itself authorizes no source execution. Its maximum result is a
committed and independently reviewed protocol correction, followed by the
mandatory Meeting Summary Handoff.

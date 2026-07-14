# Independent review: A4 V2 PAR-report timing-closure erratum

- Date: 2026-07-14
- Branch: `saq-arbitrary-cardinality-feasibility-v2`
- Parent protocol: `f86a51d6923409d735dda0ee40f88fd2e0ad2e43`
- Initial erratum commit: `d092b40616724d3539b99bb52f3bf78a6e55d468`
- Corrected review target: `f13a383a0085c456ed2f02d3ee9e041f1c70da6e`
- Verdict: `PROTOCOL_ERRATUM_INDEPENDENT_REVIEW_PASS`

## 1. Scope and method

Three independent read-only reviews inspected only exact committed blobs from
the named target. Untracked A4-V2-I source and documentation WIP were excluded.
The tracks separately reviewed:

1. the measurement boundary, self-reference closure, retry accounting, and
   unchanged scientific/authorization scope;
2. the closed PAR-seal schema, canonical maximal instance, component hashes,
   and unchanged parent blobs; and
3. the Git authority DAG, immutable artifact-tree binding, atomic publication,
   and branch-status consistency.

The reviews used committed-file inspection, Git object comparison, SHA-256 and
byte-size recomputation, JSON parsing, canonical-byte comparison, and static
schema/contract reasoning. No V2 implementation was built, imported,
syntax-checked, executed, or tested. No RNG, PAR fixture, synthetic event,
dataset, result, SAQ code, or generated scientific artifact was read or
produced.

## 2. First-review findings and corrections

The first exact target, `d092b40`, did not pass. Independent review found:

- ECMA-262 end-anchor behavior allowed line-terminated hash/OID/UTC/signal
  strings, invalidating the claimed exact schema-language byte maximum;
- the maximal witness was described as semantically admissible even though it
  intentionally maximized independent fields beyond aggregate resource caps;
- RFC 3339 calendar and temporal-order semantics and exact JSON string-escape
  rules were incomplete;
- the seal was named at its final path even though it had to be physically
  created inside the staging directory; and
- preserving only the seal and index blobs did not prevent mutation of another
  indexed PAR artifact between P, R, and E.

Commit `f13a383` corrected every finding without changing a parent protocol
blob, scientific phase, figure of merit, threshold, parity rule, retry rule,
status precedence, or execution authorization. It added exact string-length
and line-terminator closure, explicit semantic time validation, an exact
canonical-encoding rule, distinct staging/published paths, and one immutable
complete PAR-directory Git tree OID across P, R, and E.

## 3. Exact authority checks

The three parent blobs remain byte-identical to `f86a51d`:

| Parent object | Git blob OID |
| --- | --- |
| preregistration | `620ce22e60d81bbea9ea302c914dc8de8bbea9c6` |
| machine contract | `24af731af3fe40fba0bc100b87bccd8880e091a4` |
| SRUN artifact schema | `141d4db650bcc85b2ab064c56588d0e35474246f` |

The composite protocol-authority manifest at the reviewed commit has:

```text
path        docs/saq_a4_v2_protocol_authority_manifest_2026_07_14.json
Git blob    95c242b3c1e9a02aeb64fd2a99105551754c6a1b
SHA-256     6bc1b9ffa09486872b39c2f667ad9cea300b246ffd48dfeb50de1ef7902a8b3b
size        2,064 bytes
```

All eight registered component paths are in ascending UTF-8 byte order; every
recorded size and SHA-256 matches its exact `f13a383` blob.

The closed seal schema admits only these successful receipt orders:

```text
B0,P0
B0,B1,P0
B0,P0,P1
B0,B1,P0,P1
```

Interrupted attempts require a bounded `EXTERNAL_SIGNAL_1..64` token and
`DISCARDED`; the terminal attempt for each phase is `PHASE_COMPLETE` with
`NONE`, because `PAR_report` owns publication. The two byte-ledger entries
remain aggregate `B_build`, `P_parity` entries.

The canonical maximal seal-language instance is exactly 5,171 bytes including
its terminal LF and has SHA-256
`6659f41de48fa23007ae6c27e38daff1c83b909a8c2dd0f9a762193fb12c2450`.
It is a conservative syntactic bound, not an admissible resource observation;
aggregate resource, timestamp, hash, membership, and chronology invariants
remain mandatory semantic checks. The separate 65,536-byte limit is only a
coarse buffer guard.

## 4. Measurement and publication verdict

Before terminal P, the corrected authority requires all child work,
scientific/control comparison, hashing, file discovery, stat/tree walks,
identity construction, artifact-index work, byte-ledger derivation, and file
fsyncs to be complete. After terminal P, `PAR_report` is limited to captured-
integer injection, registered bounded arithmetic and length checks, one
canonical 15-key encoding, exclusive staging-file write/fsync, staging fsync,
no-replace directory rename, parent fsync, descriptor close, and direct exit.
It may perform no new read, hash, validation, child, RNG, model, parity, or
scientific work.

The one excluded file is physically created as:

```text
docs/saq_a4_v2_par_artifacts_2026_07_14.staging/par_seal.json
```

and is published as:

```text
docs/saq_a4_v2_par_artifacts_2026_07_14/par_seal.json
```

It embeds no own size or hash. Independent PAR review supplies its exact Git
blob identity. All other PAR artifact bytes and index work remain charged to B
or P. A cap, size, write, fsync, rename, membership, tree-identity, or review
failure produces no admissible PAR authority and cannot authorize SRUN.

## 5. Git authority verdict

The future chain is strictly `I < P < R < E`. The entire
`docs/saq_a4_v2_par_artifacts_2026_07_14` Git tree OID must be identical at P,
R, and E. Recursive modes, names, and blob OIDs must equal the exact indexed
membership plus the index and seal, with no symlink, submodule, extra entry, or
nonregular file. E separately binds I, P, R, the immutable tree OID, and exact
R blobs for the seal, index, and review memo. This avoids both tree mutation
and commit/self-hash recursion.

## 6. Decision boundary

The erratum passes as a protocol correction only. It is not an implementation
pass, PAR result, synthetic gate, SAQ limitation result, or database-systems
contribution. It authorizes no build or execution. The earlier source-only
`A4-V2-I` authorization remains available after this erratum and its Meeting
Summary Handoff, but it is not resumed by this review. `A4-V2-PAR`,
`A4-V2-SRUN`, data access, and SAQ modification remain unauthorized.

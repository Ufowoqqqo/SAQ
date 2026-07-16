# Independent Review: A4 V2 Generic Cache-Policy Source Implementation

Date: 2026-07-16

Reviewed stage: `A4-V2-CACHE-I`

Exact review target:
`c33a2bff7e0ec9c98596498fd43a7e629ccf47fe`

Independent review verdict:
**GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

## 1. Scope and method

The exact committed and pushed CACHE-I target was reviewed as artifact-
governance source, schema, and static-closure work only.  The review covered
the immutable Git closure, all source and document identities, the four new
schema/maximal-instance pairs, the additive artifact-schema definitions, the
37-file source manifest, the separately identified inline PREP bootstrap, the
complete executable-unit inventory, the raw-byte parent-precedence crosswalk,
the authority/claim boundary, and the registered target-head equality probe.

Review used committed Git-object inspection, `jq`, Perl static validators,
SHA-256/size recomputation, raw-byte comparisons, and diff/whitespace checks.
No repository Python was invoked, imported, syntax-checked, or executed.  No
compiler, build, test, fixture, RNG, project/native executable, isolated clone,
PREP, cache verifier, PAR-R1, SRUN, dataset, base/query/ground-truth/index,
generated result, quarantine, or SAQ/CAQ path was executed, read, or changed.
WIP and untracked files were not evidence.

## 2. Exact Git closure

```text
target       c33a2bff7e0ec9c98596498fd43a7e629ccf47fe
parent       187e363ee08d1f63888137c21fd5a533555bb248
tree         66eaf2f5df8792c3470b247e59857fc2e7a25461
subject      research: seal A4 V2 cache policy sources
paths        22
insertions   14,275
deletions    24
```

The target has exactly the direct parent required by the committed authority
and changes exactly these 22 paths:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_artifact_schema_2026_07_14.json
docs/saq_a4_v2_cache_prep_binding_maximal_instance_2026_07_15.json
docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json
docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json
docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json
docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json
docs/saq_a4_v2_cache_static_closure_2026_07_15.json
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_isolated_clone_prep_receipt_maximal_instance_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_token_maximal_instance_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
script/a4_v2_cache_policy_verifier.py
script/a4_v2_isolated_clone_prep.py
script/a4_v2_parity.py
script/a4_v2_runner.py
script/a4_v2_verifier.py
script/run_arbitrary_cardinality_a4_v2.py
```

After excluding those exact paths, parent and target projections each contain
464 entries and are raw-identical, with projection SHA-256
`0a3b3b5512e28e71afe463f0cddab763b5f06a541e5c6768afbb4e79b53dd59b`.
Thus every other tracked blob and mode is unchanged.  `git diff --check`
passes for the exact parent-to-target delta.

## 3. Source and executable-unit closure

The canonical implementation manifest is 34,781 bytes with SHA-256
`168e4d6da4dd326484d81bf4e9bfffa654f39dda4867580a4fdf3bb9d009b182`.
All 37 registered filesystem-source SHA-256 values, byte sizes, and Git blob
identities match the target.  The inventory is sorted and duplicate-free and
contains exactly 12 producer-native, 15 independent-verifier-native, and ten
Python sources.  Recomputing the frozen canonical source-tree preimage gives:

```text
9568007588c78ddda9fb4c4e20e8773ee2fa1da10a7656f181fef06883de38a2
```

The six changed or new outer Python snapshots are:

| Source | SHA-256 | Bytes |
| --- | --- | ---: |
| `script/a4_v2_cache_policy_verifier.py` | `37346b5a2777abb2ddd893c375b1a098507f4ba51f62ba5fce69104fcc83d58c` | 151,371 |
| `script/a4_v2_isolated_clone_prep.py` | `29b73a7bac4d52c70dd67589eeeab47f12738de678172eaaa2bb26aa63343053` | 219,758 |
| `script/a4_v2_parity.py` | `2a85d17aad5863dcd01c598a7f87c3991ac26766a04b0297511bd24dad99127a` | 168,467 |
| `script/a4_v2_runner.py` | `134f61e3d1ae79a2f5f85f1870998427bc34184c4153fc4683a633c0a655bb91` | 360,127 |
| `script/a4_v2_verifier.py` | `00589aafd2963021d705023fe9b934feea2a83da17d8c9dd342ad3eb7a04d4e3` | 250,023 |
| `script/run_arbitrary_cardinality_a4_v2.py` | `016120c931a7e05312b7ed6d89d7aaba73497732d7caa880b3af1066e0782506` | 34,929 |

The inline PREP bootstrap is byte-identical between its source markers and
the manifest/static closure.  Its exact identity is
`9c86fcf81df8d8d2b7b9b15a43682fd62f7c6ba35762d41e8d2a04785708487b`
over 19,631 bytes; its durable-start raw prefix is
`0111488a71573dd058308a3e20590cb8def3d4f5e8601b0e566800fd10b0d3a7`
over 2,778 bytes.  It is not a filesystem source.  The closure therefore
contains exactly 38 statically enumerated executable units, not 38 files.

## 4. Machine objects, schemas, and parent precedence

The two top-level governance identities recompute exactly:

```text
cache authority  5bbb08b98eaddf6e828c13c9c8daf968f1be5912ff8fd93b71383fa34ef6ceec / 42,903
static closure   f4e842fb5e43f1d134e92782b3aa44da4b9440bf154200161f5cda21213795a0 / 218,872
```

All seven protocol-component identities and all nine generic-object
identities in the cache authority match committed bytes.  The four new schema
families have 11, 59, 40, and 25 `$defs`, respectively; every local reference
resolves, every object shape is closed, and its required/property sets match.
A separate Perl JSON-Schema-subset traversal admits each corresponding
canonical maximal instance.  The eight schemas/witnesses, cache authority,
and static closure are canonical sorted-key compact JSON with a final LF.

The maximal instances remain syntactic non-evidence.  In particular, their
maximal repeated strings do not claim a unique runtime source inventory; the
runtime schema explicitly leaves sorted-inventory, identity, arithmetic, Git,
live-process, and cross-field predicates to mandatory external verification.

The existing artifact schema changes only by adding one external runtime-
schema arm and two closed cache-policy definitions.  Its preceding 13
`oneOf` arms and preceding 67 definitions are canonical-JSON-equal to the
parent.

The embedded parent-precedence object was independently checked against raw
committed bytes from baseline `56210f8f81557ed7a2521bf7f13c9f937396da29`.
Its 92 gapless, nonoverlapping partition spans cover both complete runner and
parity files; every unchanged complement is raw-equal, every permitted delta
has the registered finite role and unique raw anchors, there is no pure
deletion, and all 12 named parent-precedence components are raw-equal.  The
status, retry, post-P-report, and claim boundaries therefore remain the frozen
parent rules outside the finite cache-governance deltas.

## 5. Target-head remote-equality closure

The registered target-head closure command used cwd `/`, stdin `/dev/null`,
absent HOME/XDG paths before and after, and this exact argv:

```text
/usr/bin/env -i
GIT_ATTR_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
GIT_EXEC_PATH=/usr/libexec/git-core GIT_OPTIONAL_LOCKS=0
GIT_TERMINAL_PROMPT=0
HOME=/tmp/saq-a4-v2-incident-git-home-absent
XDG_CONFIG_HOME=/tmp/saq-a4-v2-incident-git-xdg-absent
LANG=C LC_ALL=C PATH=/usr/bin:/bin
/usr/bin/timeout --signal=TERM --kill-after=5s 300s
/usr/bin/git
-c core.hooksPath=/dev/null -c core.fsmonitor=false
-c core.autocrlf=false -c core.eol=lf
-c gc.auto=0 -c maintenance.auto=false
ls-remote --refs https://github.com/Ufowoqqqo/SAQ.git
refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

The first invocation was attempted inside the network sandbox and exited 128
with `Could not resolve host: github.com`.  It returned no remote reference;
HOME and XDG remained absent.  That sandbox preflight is disclosed here and
is not used as remote-equality evidence.

The required rerun under the tool's network-access policy used the identical
cwd, stdin, environment, timeout, Git argv, and absence checks.  Its exact
authoritative result was:

```text
exit     0
stdout   c33a2bff7e0ec9c98596498fd43a7e629ccf47fe<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

The remote branch therefore equalled the exact review target.  This memo does
not contain a review-head closure result.  That live, non-evidentiary probe can
occur only after this direct-child review is committed and pushed.

## 6. Syntax-only chronology

The cache-authority object's `no_execution_attestation` preserves the original
CACHE-I source-only authority literals.  After the source bytes were locked,
the user separately authorized `A4-V2-CACHE-I-SYNTAX`.  The static closure and
binding truthfully record that `/usr/bin/python3.9` accepted `compile()`-only
syntax checks for the exact six outer snapshots above and the exact inline
snapshot.  No code object was executed and no module was imported.  This
later result establishes syntax acceptance only; it does not establish
importability, executability, schema validity, runtime correctness, parity,
cost, or scientific evidence, and it grants no further Python authority.

## 7. Verdict and stop boundary

No BLOCKER, HIGH, MEDIUM, or LOW finding remains in the exact target.  The
maximum result is therefore:

```text
GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
```

This is artifact-governance source/static-review evidence only.  It is not
PREP readiness, CACHE-BIND authority, parity, synthetic feasibility, an SAQ
limitation, systems performance, novelty, or a database-systems contribution.
It creates no PREP token, clone, receipt, binding, cache-verifier result, PAR
artifact, dataset result, or method claim.

`A4-V2-CACHE-PREP-ISO`, `A4-V2-CACHE-BIND`, `A4-V2-PAR-R1`, `A4-V2-SRUN`,
benchmark/base/query/index access, quarantine access or cleanup, and SAQ/CAQ
change remain unauthorized.  This direct-child review record and its branch-
state edits are WIP/nonevidence until committed; no later gate may begin from
the uncommitted worktree.

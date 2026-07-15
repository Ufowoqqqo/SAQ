# A4 V2 Cache/Staging Isolation Protocol

Date: 2026-07-15

Stage: **A4-V2-CACHE-P**

Protocol status: **CANDIDATE_AWAITING_EXACT_COMMIT_REVIEW**

Maximum documentation outcome: **CACHE_STAGING_POLICY_REVIEW_PASS**

## 1. Authority and non-claim

This additive protocol is authorized only by
`docs/saq_a4_v2_cache_staging_policy_authorization_2026_07_15.md` at
`ffd0f41c40cd5709fb8be8b5888575c2276a3047`. It selects non-destructive
isolation for residual state recorded at terminal commit `30dfada` and review
`fd5367e`.

It authorizes no implementation edit, clone, live residual inspection,
cleanup, environment change, Python, import, build, test, PAR-R1, SRUN, data,
or SAQ change. It changes no fixture, RNG, scientific FOM, threshold,
estimator, or historical result.

## 2. Selected policy and quarantine

The old worktree residual namespace remains quarantined nonevidence. A later
candidate must use:

```text
old residuals retained and never opened by preparation
+ isolated PREP tool launch with CPython -I -B -S
+ sanitized remote transport clone of an exact reviewed commit
+ full no-follow physical/Git-tree admission
+ explicit parent PAR -B and exact startup/cache observations
+ metered independent cache verification inside P
+ concrete PREP binding only after PREP review
```

The committed residual record is:

| Path | Committed metadata |
| --- | --- |
| `script/__pycache__/a4_v2_evidence.cpython-39.pyc` | regular, `0600`, 29,837 bytes |
| `script/__pycache__/a4_v2_parity.cpython-39.pyc` | regular, `0600`, 73,739 bytes |
| `script/__pycache__/a4_v2_producer.cpython-39.pyc` | regular, `0600`, 38,151 bytes |
| `script/__pycache__/a4_v2_producer_wire.cpython-39.pyc` | regular, `0600`, 44,535 bytes |
| `script/__pycache__/a4_v2_runner.cpython-39.pyc` | regular, `0600`, 178,276 bytes |
| `docs/saq_a4_v2_par_artifacts_2026_07_14.staging/` | directory, `0700`, empty, UTC mtime `2026-07-15 06:01:27.544529150 +0000` |

The pycs total `364,538` logical bytes. Hashes, allocated bytes, and cache-
directory identity are unknown and remain unread. Preparation may read only
the exact tracked PREP source/authority objects and named Git administrative
paths **within the old source worktree/repository**; it may not traverse,
stat, hash, import, copy, rename, chmod, or delete any old residual path.
Frozen system runtime inputs needed to start the reviewed launcher and remote
Git transport (interpreter/bootstrap, dynamic libraries, `/usr/bin/env`, Git
and admitted helpers, CA trust, and DNS/network facilities) are separately
allowed, identity-bound where executable, and disclosed as host inputs. The
source Git common directory receives only the separately authorized, charged
token and capture-sidecar mutations in section 6.

## 3. Non-circular authority DAG

```text
A4-V2-CACHE-P                 reviewed documentation only
  -> A4-V2-CACHE-I            generic source/schema/static review
  -> A4-V2-CACHE-PREP-ISO     authorization target + exact review
  -> one PREP attempt from that reviewed execution base
  -> PREP receipt target + exact review + push/remote equality
  -> A4-V2-CACHE-BIND         concrete docs-only binding + exact review
  -> A4-V2-PAR-R1             separately explicit authorization
  -> at most one corrected PAR event
```

Every arrow requires a new explicit user instruction. CACHE-I freezes generic
source, schemas, commands, paths, and binding validation without predicting a
future PREP hash. PREP authorization later freezes its reviewed execution-base
commit. CACHE-BIND supplies concrete PREP target/review identities after they
exist. Mechanically, CACHE-I authorization starts only as a direct child of
the pushed CACHE-P review head; PREP authorization starts only from the pushed
CACHE-I review; CACHE-BIND starts only from the pushed PREP receipt review;
and PAR-R1 authorization starts only from the pushed CACHE-BIND review. Each
edge also requires its registered live HTTPS equality predicate. Before the
isolated clone exists, that predicate is the section 6.3 no-clone probe; after
the clone exists, it is the sanitized fresh-fetch predicate inside that clone.
The PREP-authorization review closure is also the live execution-base
predicate immediately before PREP. SRUN, benchmark/data access, and SAQ are
outside the DAG.

## 4. Fixed future authority paths

CACHE-I, if separately authorized, must create and review these generic
objects before PREP:

```text
docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json
docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json
docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_receipt_schema_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_receipt_maximal_instance_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_token_schema_2026_07_15.json
docs/saq_a4_v2_isolated_clone_prep_token_maximal_instance_2026_07_15.json
docs/saq_a4_v2_cache_static_closure_2026_07_15.json
docs/saq_a4_v2_cache_prep_binding_schema_2026_07_15.json
docs/saq_a4_v2_cache_prep_binding_maximal_instance_2026_07_15.json
```

The later fixed authority/data paths are:

```text
CACHE-I authorization:
  docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md
PREP authorization:
  docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md
PREP pre-prologue launcher-incident terminal memo, only if needed:
  docs/saq_a4_v2_isolated_clone_prep_launcher_incident_2026_07_15.md
CACHE-BIND object:
  docs/saq_a4_v2_cache_prep_binding_2026_07_15.json
PAR-R1 authorization slot:
  docs/saq_a4_v2_par_r1_authorization_2026_07_15.md
PAR cache-verifier artifact, relative to PAR staging/final root:
  cache_policy_verification.json
Fixed independent-review memos:
  docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md
  docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md
  docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md
  docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md
  docs/saq_a4_v2_isolated_clone_prep_launcher_incident_independent_review_2026_07_15.md
  docs/saq_a4_v2_isolated_clone_prep_independent_review_2026_07_15.md
  docs/saq_a4_v2_cache_prep_binding_independent_review_2026_07_15.md
  docs/saq_a4_v2_par_r1_authorization_independent_review_2026_07_15.md
```

Each schema is closed (`additionalProperties=false` recursively), uses
canonical UTF-8 JSON/JSONL with final LF, carries exact count/string/file size
bounds, and has a canonical maximal-size witness accepted at exact equality.
Publication of this protocol does not create those objects or authorize them.

## 5. Later `A4-V2-CACHE-I` source/static contract

`A4-V2-CACHE-I` is not authorized. Its maximum outcome is
`GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS`.

### 5.1 Exact source rebinding

The present 35-source closure must become exactly 37 by adding only:

```text
script/a4_v2_isolated_clone_prep.py
script/a4_v2_cache_policy_verifier.py
```

Only these existing source files may change:

```text
script/run_arbitrary_cardinality_a4_v2.py
script/a4_v2_runner.py
script/a4_v2_parity.py
script/a4_v2_verifier.py
```

The entrypoint may capture the bounded pre-import observation; runner may
admit and bind it; parity may perform only preterminal cache checks, launch the
PAR-only verifier, and place its artifact in the existing P ledger/index/seal;
the exact `_post_par_report` and `_post_par_report_unchecked` function bodies
and their syscall/read closure remain byte-identical. The existing verifier
may receive only dormant admission/schema changes needed to validate the new
sealed PAR input in a later,
separately authorized SRUN. Solver, replay, tie, rounding, packing, and
scientific logic remain byte-identical in behavior and statically
cross-walked. The other four existing Python sources and all 27 native/CMake
sources remain byte-identical.

The implementation manifest must be rebuilt as follows:

- manifest `schema_version` is exactly `2`;
- `source_files` is the old exact 35 paths plus the two new paths;
- `python_source_files` is the old exact eight paths plus the two new paths;
- native source arrays are byte-identical;
- `par_contract.par_command` is exactly the parent command in section 5.3;
- every permitted changed/new blob has SHA-256, byte size, family, and role;
- the canonical source-tree algorithm is unchanged and recomputed over 37;
- a new `cache_protocol_identity` binds the additive cache authority manifest;
- that authority and the implementation manifest bind exactly one inline
  executable source, the immutable ASCII-only PREP `-c` bootstrap, by exact
  UTF-8 bytes, full-source and raw-prefix-prologue SHA-256/size, role, and
  complete call/open/import/mutation closure; and
- the old protocol/preregistration/erratum objects and their composite
  authority manifest remain byte-identical.

The artifact schema, implementation binding, source crosswalk, implementation
manifest, and additive cache authority may change only to bind the exact new
runtime/preparation objects, the seventh environment-preimage field, and the
new P artifact. `AGENTS.md`, `TASK.md`, focused authorization/review memos, and
the ten fixed generic objects in section 4 are the only other CACHE-I
documentation changes. A candidate commit must publish an exact changed-path
inventory and prove every other tracked blob unchanged.

The build-manifest and artifact-index cache-aware shapes are explicitly
versioned `2`; the unchanged PAR seal continues to bind their exact bytes. The
new P artifact is created, validated, indexed, and sealed before P terminal.
The frozen `PAR_report` postterminal syscall/read closure is not changed.
Prior SRUN source authority becomes stale because admission source identities
change; dormant parsing support is not SRUN execution authority. Static review
must prove there is no other Python actor reachable in B/P.

The cache static-closure object contains a machine-readable
`parent_precedence_crosswalk`. The old parity/runner whole-file Git blobs are
baselines, not impossible candidate whole-file equality requirements. For each
registered component it stores baseline/candidate path and blob, unique exact
UTF-8 boundary-context anchors, raw half-open `[start,end)` byte-slice
SHA-256/size on both sides, and requires equality without whitespace or AST
normalization. Registered
unchanged components are:

```text
runner: STATUS_ORDER and C_FAILURE_STATUSES assignments
runner: _status_min, _c_failure_status, _fail_preserving_prior_status,
        _run_preserving_prior_status, _resolve_final_status
parity: ExternalPhaseSignal
parity: B_build ExternalPhaseSignal retry block
parity: P_parity ExternalPhaseSignal retry block
parity: _post_par_report_unchecked and _post_par_report
```

The crosswalk also gives complete, non-overlapping baseline and candidate byte
partitions. Every partition entry is either (a) an equal raw slice, including
the registered components above and all unchanged complementary bytes, or
(b) one member of an exact finite cache-governance delta allowlist with
baseline/candidate slice identities, purpose, and permitted semantic effect.
The two partitions cover byte offset zero through EOF with no overlap or gap;
each boundary-context pair occurs exactly once in its named file. An insertion
uses a zero-length baseline span between unique left/right contexts with the
fixed empty-byte SHA-256; deletion is forbidden. The B/P retry entries use
phase-specific multi-line contexts rather than the shared
`except ExternalPhaseSignal` text alone. A distinct new-only
`cache_verifier_signal_adapter` delta may translate only a verifier wait status
that reports POSIX-signal termination into the existing `ExternalPhaseSignal`
before the existing
retry-safe boundary; its schema/role/forbidden-status list is closed and
independently reviewed. It cannot translate mismatch, schema, identity,
ordinary nonzero exit, or post-boundary failure. This crosswalk, plus the
unchanged parent/erratum contracts, mechanically binds the future active code
to the delegated parent mapping.

### 5.2 Static cache/import closure

The machine static-closure object must enumerate all 37 file sources plus the
one inline executable bootstrap (38 executable units total) and prove for
every PAR-reachable Python actor, both governance file tools, and the
bootstrap:

- no `py_compile`, `compileall`, explicit marshal/cache loader, direct `.pyc`
  read/write, cache-path write, cache mutation/deletion, or import-hook
  installation;
- no dynamic import/eval/exec path capable of reaching an unreviewed repo
  module;
- exact direct-import allowlists and exact subprocess/exec callsites; and
- no change to `sys.dont_write_bytecode`, `sys.pycache_prefix`, `sys.meta_path`,
  or `sys.path` after the registered observations except the existing explicit
  reviewed A4 import mechanism.

The PREP tool is standalone stdlib-only and never imports any repo/A4 module.
The cache verifier is standalone stdlib-only, shares no helper with producer,
runner, existing verifier, PREP, or SRUN, and is invoked only in PAR.
The inline bootstrap is a separately reviewed executable source, not an
unexamined string payload: its earliest token prologue, every open/stat/hash,
compile/exec, process, mutation, exception, and terminal path is in the same
static closure even though it does not add a 38th filesystem source path.

### 5.3 Exact parent PAR launch

The only parent interpreter-option change is:

```text
MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -B script/run_arbitrary_cardinality_a4_v2.py \
  par docs/saq_a4_v2_par_artifacts_2026_07_14
```

The cwd is exactly the bound isolated clone root. Raw `/proc/self/cmdline` is
stored as lowercase even-length hex plus SHA-256. It must parse as NUL-
separated bytes with one terminal NUL, no empty argument, and exact argv:

```text
python
-B
script/run_arbitrary_cardinality_a4_v2.py
par
docs/saq_a4_v2_par_artifacts_2026_07_14
```

Every other parent interpreter option is absent. Every environment key whose
name begins `PYTHON` is absent. The three thread variables have their exact
registered values.

The intentionally followed `python` command and `/proc/self/exe` must resolve
to the same regular leader ELF inode already covered by I-R1. That file must
equal the CACHE-I byte pin: size 15,448 and SHA-256
`c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0`.
The installed `/usr/lib64/python3.9/importlib/_bootstrap_external.py` must be a
66,447-byte regular file with SHA-256
`8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4`.
RPM NEVRAs are CACHE-P static provenance, not runtime predicates: no `rpm`
process or rpmdb parser is admitted. Path, inode, size, and digest are runtime
records; `cpython-39` alone is not an admission identity. The dynamic loader,
`libpython3.9.so.1.0`, libc, and other shared libraries remain disclosed but
unbound frozen host inputs, so the claim is leader-ELF/bootstrap identity, not
identity of the complete mapped CPython image.

Immediately after the first CPU/wall snapshots and before importing any A4
module other than the registered `__main__` entrypoint, capture and require:

```text
sys.flags.dont_write_bytecode == 1
sys.flags.isolated == 0
sys.flags.ignore_environment == 0
sys.flags.no_site == 0
sys.flags.optimize == 0
sys.dont_write_bytecode is True
sys.pycache_prefix is None
sys.implementation.cache_tag == "cpython-39"
sitecustomize absent from sys.modules
usercustomize absent from sys.modules
```

Record `/proc/self/cwd`, exact bounded `sys.path`, `sys.meta_path` type/origin
records, user-site enablement, and a bounded sorted retained-module inventory.
The runtime schema freezes count/string caps and predicates: `__main__` must be
the reviewed entrypoint in the isolated clone; no other pre-import module may
resolve inside any repository/worktree; no path may name the old worktree; the
only clone-local import root is its exact `script/`; every remaining origin is
builtin/frozen or below the frozen CPython/installed-package roots. These
values and all cache state are rechecked at B and P preterminal checks.

### 5.4 Exact cache namespace

The namespace and ten adjacent legacy paths below are absent before explicit
A4 import and at B/P preterminal checks:

```text
script/__pycache__
script/a4_v2_archive.pyc
script/a4_v2_cache_policy_verifier.pyc
script/a4_v2_evidence.pyc
script/a4_v2_isolated_clone_prep.pyc
script/a4_v2_parity.pyc
script/a4_v2_producer.pyc
script/a4_v2_producer_wire.pyc
script/a4_v2_runner.pyc
script/a4_v2_verifier.pyc
script/run_arbitrary_cardinality_a4_v2.pyc
```

Checks use no-follow directory descriptors and leaf
`fstatat(..., AT_SYMLINK_NOFOLLOW)` semantics. Present, dangling, symlink,
non-directory, unreadable, or unclassifiable is an artifact failure.

For every explicitly imported A4 module, record exact name, reviewed source
path/blob, `__file__`, `__spec__.origin`, loader type, `__cached__`, and
no-follow absence of its expected cache path. This is a cooperative-process
observation, not proof against a malicious transient writer.

### 5.5 Independent P verifier

The parent launches the new verifier before P terminal using the already-
verified CPython leader descriptor. CACHE-I freezes the exact concrete control
schema/caps and argv template:

```text
/proc/self/fd/197
-I
-B
-S
<absolute-isolated-clone>/script/a4_v2_cache_policy_verifier.py
verify-parent-cache-policy
--control-fd
198
```

Its cwd is `/`; environment is exactly `LC_ALL=C`, `LANG=C`, and
`PATH=/usr/bin:/bin`, with no other key. It receives bounded canonical JSON
over inherited fd 198 and no filesystem input chosen by a result. It imports
no A4, NumPy, producer, archive, existing verifier, PREP, or SRUN module.

It independently checks live parent PID/start/cmdline/cwd, Git/clone/source,
the concrete CACHE-BIND object, cache/legacy absence, serialized parent
startup/module observations, reviewed `.py` blobs, and static closure. It
writes exactly `cache_policy_verification.json` in P staging. Its schema and
maximal witness are the runtime objects in section 4. All verifier CPU/wall/
RSS/bytes and parent validation are charged to P. A later SRUN never invokes
this actor. Its leader descriptor must resolve to the same pinned leader ELF
and installed-bootstrap identity as the parent, subject to the same disclosed
unbound shared-library ceiling.

The B check occurs before the shared B-terminal/P-start snapshot and is
charged to B. Parent and verifier P checks occur before P terminal and are
charged to P. Observations are sealed from memory. After P terminal there is
no cache stat/read/enumeration/import/origin work; existing `PAR_report`
remains byte-authoritative and unexpanded. No new PAR runtime lock exists.

### 5.6 Environment and status binding

The existing six environment-preimage fields remain semantically unchanged;
the seventh exact top-level field `python_cache_policy` binds argv/cwd,
interpreter/cache state, bounded startup/module records, clone PREP/BIND,
B/P observations, static closure, and verifier result. It is not nested inside
the frozen `_FIXED_ENVIRONMENT` object.

Failure mapping is mutually exclusive:

- absent explicit PAR-R1 authority: order-0 `NOT_AUTHORIZED`;
- parent option, all-`PYTHON*` absence, or startup cache-state mismatch before
  explicit import: order-1 `PRECONDITION_NOT_MET`;
- cwd/clone/PREP/BIND/Git/source/origin/cache-path identity mismatch, including
  the independent verifier **reporting** such a mismatch: order-2
  `ARTIFACT_INVALID`;
- import/loader, verifier process/schema/canonicalization, timer, or ledger
  defect (including missing/malformed output only after the verifier was
  successfully spawned and reaped, or an ordinary nonzero exit, rather than a
  well-formed mismatch report or wait-status signal termination):
  order-3 `IMPLEMENTATION_INVALID`; and
- order 4 delegates resource, signal, and publication conditions to the
  byte-frozen parent mapping without introducing a sentinel status. The
  delegated class includes fork/exec/wait I/O, permission, `EAGAIN`, `ENOMEM`,
  and other system-call or resource failures before successful verifier spawn
  and reap. The machine contract binds its exact reviewed source commit/tree
  and parity,
  runner, parent-contract, and erratum Git blobs; no parent status is renamed
  or weakened.

Cache-policy mismatch or implementation defect creates no new retry. The
byte-frozen B/P rule still permits at most its existing single retry for an
eligible external POSIX signal; CACHE-I may neither remove nor add to that
count. A new P-verifier wait status reporting signal termination is forwarded
into that existing P classification only before P terminal and only when the
existing `retry_safe` predicate holds; no provenance beyond the wait status is
claimed. Cache mismatch, malformed verifier
output, identity failure, and any event after the retry-safe boundary are
never retryable. `-B` is disclosed as a B/P harness policy: source compilation
and all checks are charged; repository A4 cache output bytes must be zero. No
claim is made for later SRUN Python children.

## 6. Later `A4-V2-CACHE-PREP-ISO` contract

`A4-V2-CACHE-PREP-ISO` is not authorized. It may run only after its fixed
authorization path is committed, pushed, and exact-reviewed. The reviewed
authorization-review head, not the earlier CACHE-I head, is the concrete
`PREP_EXECUTION_BASE`; its 37-source tree must equal reviewed CACHE-I.

### 6.1 Roots, launch, and permanent consumption token

```text
source worktree: /tmp/saq-arbitrary-cardinality-feasibility-v2
source Git common dir: /rwproject/kdd-db/kluaq/saq/.git
isolation root: /tmp/saq-a4-v2-par-r1-isolation
outer attempt journal dir:
  /tmp/saq-a4-v2-par-r1-isolation/prep-attempt
clone root: /tmp/saq-a4-v2-par-r1-isolation/repo
receipt staging in clone:
  docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15.staging
receipt final in clone:
  docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15
origin fetch URL: https://github.com/Ufowoqqqo/SAQ.git
origin push URL:  git@github.com:Ufowoqqqo/SAQ.git
branch: saq-arbitrary-cardinality-feasibility-v2
```

The exact launch is a reviewed immutable `-c` bootstrap, not direct execution
of a worktree script. CACHE-I stores the bootstrap's exact ASCII-only UTF-8
source, full-source and raw-prefix-prologue SHA-256/size, argv schema, and
maximal instance in the static-closure object. PREP authorization supplies
only the reviewed literal substitutions:

```text
/usr/bin/env -i LC_ALL=C LANG=C PATH=/usr/bin:/bin \
/usr/bin/python3.9 -I -B -S -c <CACHE_I_BOOTSTRAP_SOURCE> \
<CACHE_I_BOOTSTRAP_SHA256> <CACHE_I_BOOTSTRAP_SIZE> \
<CACHE_I_PROLOGUE_SHA256> <CACHE_I_PROLOGUE_SIZE> \
<PREP_EXECUTION_BASE> \
<PREP_TOOL_SHA256> <PREP_TOOL_SIZE> \
<PREP_AUTH_SHA256> <PREP_AUTH_SIZE> \
<PREP_AUTH_REVIEW_SHA256> <PREP_AUTH_REVIEW_SIZE>
```

Its cwd is `/`. The first reviewed bootstrap prologue admits exactly two
pre-START imports, builtin `sys` and builtin `posix`; their exact module type,
loader/origin, symbols used, and zero-filesystem/cache property are in the
inline static closure. It admits no other import and no mutable filesystem
input except component-wise access to the fixed Git-common-directory/token
path required for exclusive START publication.
Using a fixed ASCII JSON template (no `json`/`hashlib`), strict hex/decimal argv
validation, and only registered `posix` calls, it sets `umask 077` and
immediately attempts component-wise no-follow exclusive token START
publication plus token/common-dir fsync. The bootstrap and prologue are
ASCII-only. The prologue is the exact raw-byte prefix of the full bootstrap at
the registered prologue size. The argv supplies reviewed bootstrap/prologue
SHA-256 and byte sizes as claims; after START, the full bootstrap re-reads
`/proc/self/cmdline`, parses the exact NUL-delimited argv, and verifies both
the complete actual `-c` bytes and their registered prologue prefix against
those identities before any further authority-bearing work.

The machine contract closes that pre-START filesystem surface: fixed root-to-
common-directory components are opened relative to parent descriptors with
`O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`; the fixed leaf is created with
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC` and mode `0600`; only the
bounded fixed START bytes, file fsync, close, and common-directory fsync/close
follow. No other pre-START filesystem access is permitted.

Token START durability, not CPython process start, is the mechanically
enforced one-shot boundary. If `/usr/bin/env`, CPython, either pre-START builtin
import, bootstrap parsing, argv validation, or first token publication cannot
reach a durable START, there is deliberately no machine claim that the command
ran; the branch must stop under the fixed launcher-incident closure below and
the same authority is never retried.

Once START is durable, the bootstrap creates the two captures, then
component-wise no-follow opens and size/hash-verifies the exact PREP tool,
authorization document, authorization-review memo, source HEAD, leader,
argv/env, flags, and `sys.path` against the reviewed literals. Every mismatch
now consumes the token and closes a typed terminal record. It requires these
exact runtime byte identities; the package names are static provenance only:

```text
/usr/bin/env (static provenance coreutils-8.32-41.el9_8.x86_64)
  size 45,088
  sha256 4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b
/usr/bin/python3.9 (static provenance python3-3.9.25-7.el9_8.x86_64)
  size 15,448
  sha256 c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0
/usr/lib64/python3.9/importlib/_bootstrap_external.py
  (static provenance python3-libs-3.9.25-7.el9_8.x86_64)
  size 66,447
  sha256 8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4
```

Runtime does not invoke `rpm` or parse the rpmdb. PREP-owned token, capture,
journal and receipt directories/files use `0700`/`0600`; checked-out worktree
entries use `0700` for directories/executable files and `0600` otherwise,
always effective-UID-owned and on the pinned isolation device. Git-generated
administrative state has the separate role-specific mode closure in section
6.5. Git-mode comparison uses only type and executable bit.

CACHE-I must first publish the closed token schema and maximal witness named
in section 4. The token permits exactly START plus one TERMINAL record,
final-LF canonical JSONL, at most 131,072 bytes. START binds claimed
authorization/execution-base/bootstrap literals, `umask`, fixed capture
paths/caps, and exact raw-prefix prologue identity; later verification does
not rewrite it. TERMINAL closes typed status, verified identities, journal/receipt
identities when they exist, final capture identities, and the
**pre-terminal-append** source-Gitdir ledger.

```text
START keys:
  record_type schema_version sequence previous_record_sha256
  claimed_authorization_identity claimed_authorization_review_identity
  claimed_execution_base_commit claimed_bootstrap_identity
  source_git_common_dir_path umask_octal capture_policy prologue_identity
TERMINAL keys:
  record_type schema_version sequence previous_record_sha256 status
  status_detail verified_authority_identity verified_host_identity
  outer_journal_identity receipt_seal_identity
  stdout_capture_identity stderr_capture_identity terminal_process_identity
  source_gitdir_pre_terminal_ledger
```

Terminal status is one of `PRECONDITION_NOT_MET`,
`RESOURCE_INCOMPLETE_NO_DECISION`, `ARTIFACT_INVALID`,
`IMPLEMENTATION_INVALID`, or
`ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW`. Review occurs later, so the
token schema has no review-pass status. An absent, partial, corrupt, or
otherwise noncanonical TERMINAL after a valid START is only
`CRASH_OR_UNKNOWN`; no second incomplete-evidence status overlaps it.

After the token is durable, the supervisor creates with no-follow `O_EXCL`
and mode `0600`, then file- and common-directory-fsyncs, these fixed bounded
sidecars:

```text
/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.stdout
/rwproject/kdd-db/kluaq/saq/.git/saq-a4-v2-isolated-prep.stderr
```

Each aggregate sidecar has an 8,388,608-byte cap and a CACHE-I-frozen
length-prefixed multiplex format. Each individual descendant stdout/stderr
stream also has an 8,388,608-byte cap; the aggregate cap is separate and may
stop multiple individually valid streams. Crossing either cap is
`RESOURCE_INCOMPLETE_NO_DECISION`. START binds paths/caps; TERMINAL binds final
capture sizes/digests.

The TERMINAL ledger is sampled only after captures are closed/fsynced and
immediately before TERMINAL encoding. It separately records START-token and
capture logical/allocated bytes, completed write syscall counts/bytes,
file-fsync and common-directory-fsync counts, capture bytes, and created-entry
count. It excludes TERMINAL encoding/append, token fsync, following
common-directory fsync, and the allocation they may cause. That finite
terminal-token publication tail is explicitly
`NOT_MEASURED_NOT_INTERPRETED`; independent review later observes and reports
final token/capture logical and allocated bytes and final state, but makes no
dynamic syscall-completion claim. None is folded into isolation-root storage.

The bootstrap then compiles and executes the already verified in-memory PREP
bytes; it never imports or reopens the worktree file. Token acquisition
consumes one-shot authority. The verified PREP program is the parent
supervisor. Before forking it calls and verifies
`prctl(PR_SET_CHILD_SUBREAPER,1)`. It forks exactly one worker; before any
worker mutation the worker calls `setpgid(0,0)`, reports readiness over a
fixed pipe, and the parent requires `worker_pgid == worker_pid` while itself
remaining outside that group. Every descendant must retain that PGID. The
supervisor captures bounded
pipe observations, monitors descendants, and is the sole signal, journal, and
terminal-publication actor. The worker is the sole normal reaper of its direct
Git children and reports their `wait4` records plus its final `RUSAGE_SELF`
and `RUSAGE_CHILDREN` before exit. The supervisor reaps the worker and every
descendant reparented to it, then drains `waitid`/`wait4` through `ECHILD` and
records those objects separately. `-I -S` excludes old script/cwd/user/site import
namespaces and `-B` suppresses normal import-cache writes. Neither bootstrap
nor supervisor performs source-worktree status/traversal or opens an old
residual namespace.

The token and captures are never automatically removed. Successful PREP-report
appends/fsyncs its TERMINAL seal identity after freezing the pre-terminal
ledger. Every caught post-token failure
first closes/fsyncs the bounded captures, appends/fsyncs a typed terminal token
record, and fsyncs the common directory. A start-only token means only
`CRASH_OR_UNKNOWN`; it must never be reclassified from missing state. A
CPython-startup, bootstrap-parse, or first-token-publication failure occurs
before a durable START. It yields only an external
`LAUNCHER_INCOMPLETE_NO_DECISION` incident: the fixed memo records authority,
exact command, executor-reported exit/signal/stdout/stderr identity or
`UNAVAILABLE`, observed token/capture state, and the explicit limitation
`NOT_MACHINE_PROVABLE_INVOCATION_OR_DURABILITY`. The incident target/review
closure in section 6.7 is terminal and the same authority is never retried. A
preexisting/unclassifiable token is never rewritten or reclassified: a valid
token retains the original attempt's recorded status (a START-only token is
`CRASH_OR_UNKNOWN`). If token collision prevents a newly authorized launch
from publishing START, that new authority can yield only the external
`LAUNCHER_INCOMPLETE_NO_DECISION` incident above, not a fabricated
`PRECONDITION_NOT_MET`. The latter status is available only after this
attempt's durable START for verified source/authority/destination failures
before isolation-root creation.

### 6.2 Outer journal and failure evidence

After token durability, check `/tmp` by pinned parent dirfd, require the entire
isolation namespace absent, create the root by no-replace `mkdirat` at `0700`,
and recheck owner/mode/device/inode. Create and fsync the outer attempt journal
before the first Git process or clone mutation.

The bounded hash-chained JSONL journal writes/fsyncs each substantive intent
before its Git/filesystem action and each result afterward. It covers remote
fetch, checkout, config/ref/object and physical-tree validation, resource
observations, and final clone postcheck. It closes with
`READY_FOR_RECEIPT_INSTALL`, then is copied byte-for-byte into the clone
receipt before the metered terminal. Receipt installation and sealing are the
fixed finite closure in section 6.6.

Only success yields a PREP receipt. A caught post-bootstrap pre-root failure
is evidenced by the durable typed terminal token plus closed capture
identities; an uncontained crash may leave only the start record and therefore
has status `CRASH_OR_UNKNOWN`. A later failure also retains the root and
partial journal. A pre-bootstrap launcher failure has no token claim and is
recorded only as the explicitly non-machine-provable fixed launcher-incident
memo plus its independent review. It is an external incident record, not proof
that the command ran. No failure path removes state, resumes, or retries under
the same PREP authority.

### 6.3 Sanitized Git transport and checkout

Before the first Git child, PREP no-follow validates this executable path/type/
link/size/digest closure and records it in the receipt. RPM labels below are
CACHE-P static provenance only:

```text
/usr/bin/git
  regular; git-core-2.52.0-1.el9.x86_64; size 4,397,352
  sha256 f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3
/usr/libexec/git-core/git-remote-https
  symlink exactly to git-remote-http
/usr/libexec/git-core/git-remote-http
  regular; git-core-2.52.0-1.el9.x86_64; size 966,840
  sha256 c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902
/usr/libexec/git-core/{git-index-pack,git-unpack-objects,git-fetch,
  git-checkout,git-config,git-fsck}
  each symlink exactly to ../../bin/git
```

The static callsite/helper allowlist is exact. Separately, every executable
image actually seen at the 10-ms `/proc` samples and observed process
boundaries must be one of the pinned PREP leader, `/usr/bin/env`,
`/usr/bin/git`, or `git-remote-http`; an observed unexpected image is
`ARTIFACT_INVALID`. This is explicitly a **sampled observed inventory**, not
proof that no short-lived helper existed between samples. Dynamic libraries,
CA trust, DNS, and network services are recorded frozen host inputs, not old-
repository residuals and not part of the executable-allowlist claim.

PREP uses `/usr/bin/git` `2.52.0` with an exact child environment containing
only:

```text
GIT_ATTR_NOSYSTEM=1
GIT_CONFIG_GLOBAL=/dev/null
GIT_CONFIG_NOSYSTEM=1
GIT_EXEC_PATH=/usr/libexec/git-core
GIT_OPTIONAL_LOCKS=0
GIT_TERMINAL_PROMPT=0
HOME=/tmp/saq-a4-v2-par-r1-isolation/git-home
XDG_CONFIG_HOME=/tmp/saq-a4-v2-par-r1-isolation/git-xdg
LANG=C
LC_ALL=C
PATH=/usr/bin:/bin
```

The exact clone command is `/usr/bin/git` plus these leading config options:

```text
-c core.hooksPath=/dev/null
-c core.fsmonitor=false
-c core.autocrlf=false
-c core.eol=lf
-c gc.auto=0
-c maintenance.auto=false
clone --no-local --no-checkout --single-branch --no-tags
--template=/tmp/saq-a4-v2-par-r1-isolation/empty-git-template
--branch saq-arbitrary-cardinality-feasibility-v2
https://github.com/Ufowoqqqo/SAQ.git
/tmp/saq-a4-v2-par-r1-isolation/repo
```

The empty HOME/XDG/template directories are created, no-follow traversed, and
sealed before Git. Subsequent Git commands reuse the same executable,
environment, and `-c` prefix.

The order is immutable. After `--no-checkout` returns and **before checkout**,
the tool verifies the exact fetched commit and tree in the object database;
parses `ls-tree -rz --full-tree` to reject `.gitattributes`, `.gitmodules`,
symlinks, gitlinks, or any non-blob/non-tree entry; and closes config, refs,
logs, and reachable object identities. Only then may it run exactly
`git -C <clone> checkout --force -B <branch> <PREP_EXECUTION_BASE>`. Exact
`remote set-url` commands retain the HTTPS fetch URL and add only the SSH push
URL. The fetched remote branch OID must equal `PREP_EXECUTION_BASE`; every
later fresh-equality fetch uses the same sanitized prefix and forced exact
branch-to-remote-tracking-ref refspec over HTTPS.

The configured SSH push URL is an operational convenience outside PREP, not a
trusted transport claim: this protocol does not bind `ssh`, its config, agent,
or host keys. Push success never establishes authority. Only a subsequent
sanitized HTTPS fetch into the isolated clone, followed by exact OID equality,
can establish the remote-equality predicate used by review and the next node.

The local config is parsed as an unordered NUL-delimited multimap. Before the
push URL is installed it contains exactly:

```text
core.repositoryformatversion=0
core.filemode=true
core.bare=false
core.logallrefupdates=true
remote.origin.url=https://github.com/Ufowoqqqo/SAQ.git
remote.origin.fetch=+refs/heads/saq-arbitrary-cardinality-feasibility-v2:refs/remotes/origin/saq-arbitrary-cardinality-feasibility-v2
remote.origin.tagOpt=--no-tags
branch.saq-arbitrary-cardinality-feasibility-v2.remote=origin
branch.saq-arbitrary-cardinality-feasibility-v2.merge=refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

The final state adds exactly
`remote.origin.pushurl=git@github.com:Ufowoqqqo/SAQ.git`. No other local,
worktree, global, or system config is admitted. The ref closure is exactly
symbolic `HEAD -> refs/heads/saq-arbitrary-cardinality-feasibility-v2`, that
local branch, and
`refs/remotes/origin/saq-arbitrary-cardinality-feasibility-v2`, all at the
execution-base OID. CACHE-I freezes the exact required reflog path/content
shape; no other ref or log is allowed.

CACHE-I freezes exact argv arrays and output parsers for at least these
sanitized-prefix suffixes, both before checkout and after every later fetch:

```text
-C <clone> config --null --local --list
-C <clone> show-ref --head --dereference
-C <clone> symbolic-ref -q HEAD
-C <clone> cat-file -e <PREP_EXECUTION_BASE>^{commit}
-C <clone> rev-parse <PREP_EXECUTION_BASE>^{tree}
-C <clone> ls-tree -rz --full-tree <PREP_EXECUTION_BASE>
-C <clone> rev-list --objects --all --no-object-names
-C <clone> cat-file --batch-all-objects --batch-check=%(objectname)
-C <clone> fsck --full --strict --unreachable --no-reflogs
```

The two object-name sets must be equal, every object must hash-verify, and the
fsck unreachable/dangling set must be empty. Reject any unexpected config,
ref, log, object, template/hook/filter/attributes/fsmonitor/maintenance
process, replace/graft/shallow/promisor/alternate state, external object
database environment, or URL rewrite. No source object store is read.

Current CACHE-P and, only under their own later explicit authorizations, all
future pre-clone target/review closures, pre-clone parent admissions, and the
no-clone launcher-incident branch use the same separate exact remote-equality
probe. Its cwd is `/`; stdin is
`/dev/null`; the two literal HOME/XDG paths below must remain absent before and
afterward. Its complete argv is:

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

Thus timeout and Git receive the same exact sanitized environment. The probe
reuses the exact env/Git/HTTPS-helper byte identities above and additionally
binds `/usr/bin/timeout` to coreutils `8.32-41.el9_8.x86_64`, size 36,848 and
SHA-256
`025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69`.
The official upstream 8.32 release archive supplies the CLI/source semantic
reference: `src/env.c` and matching Texinfo `env` section for `-i` and the
exact `NAME=VALUE` environment, plus `src/timeout.c` and matching Texinfo
`timeout` section for `--signal`, `--kill-after`, duration, and exit status.
The installed byte identities and RPM owner are pinned separately. The
source-RPM filename `coreutils-8.32-41.el9_8.src.rpm` is provenance only; the
patched source payload is not bound and no upstream-to-installed-binary source
parity is claimed. The probe executable inventory is exactly env, timeout,
Git, and `git-remote-http` under the bound symlink/helper closure.

For an admitted result the wrapper exit must be zero, stderr empty, and stdout
exactly one ASCII line:
`<40 lowercase hex> TAB refs/heads/saq-arbitrary-cardinality-feasibility-v2 LF`.
The parsed OID must equal the expected current CACHE-P target/review commit,
the separately authorized pre-clone CACHE-I authorization/implementation or
PREP-authorization target/review commit, the parent review named by a
pre-clone parent-admission role, or, on the future incident branch, the
incident target/review commit. Any other byte, ref, count, path state, or
process result fails remote equality. The probe
creates no HOME/XDG/template/repository object and its SSH push predecessor
remains non-authoritative.

The claim is intentionally narrower than the prior draft: there is no unnamed
outer executor, process sampler, pipe-drain, hash, subreaper, hard process cap,
or failure-resource claim. Coreutils timeout bounds the monitored command's
wall interval; only the exact successful exit and fixed output bytes establish
equality. External capture is not evidence, and any timeout, nonzero/signal
exit, nonempty stderr, unexpected byte, or caller-side failure simply yields
`REMOTE_EQUALITY_NOT_ESTABLISHED`. Every producing node formed before the
isolated clone exists gets exactly one no-clone closure probe for its pushed
target and exactly one for its pushed review. A later separately authorized
pre-clone child node gets one distinct no-clone parent-admission probe of that
review head before forming its own target. The PREP-authorization review
closure is additionally the one live execution-base admission immediately
before PREP; this is one probe with two declared operational roles, not a
second execution-base probe. The per-role counts otherwise do not collapse
into a global one-probe-per-OID rule. Current CACHE-P authorizes only its own
two closure probes; it does not authorize any future CACHE-I or PREP probe.
Failure stops the applicable branch, child-node formation, or PREP invocation
pending new authorization.

The target-head closure command and result must be recorded in its later
direct-child review memo. The review-head closure probe occurs only after that
memo is committed and pushed, so it is a live, non-evidentiary post-commit
predicate: it is never claimed inside the same memo and is not synchronized to
the Meeting Summary. The mandatory handoff carries only the committed and
independently reviewed target/review evidence. Any separately authorized next
node must run its one-shot parent-admission probe and record that distinct
command/result in the new target for independent review. The same complete
target/review closure split applies to a future launcher incident and avoids
an OID time loop.

### 6.4 Numerical safety ceilings and measurement

The pre-result safety ceilings, based on the 467-entry/8.63-MB tree and
15.62-MiB current object store, are:

```text
process-family wall:                 1,800,000,000,000 ns
process-family CPU:                  1,800,000,000 us
maximum observed concurrent family RSS:
                                      2,147,483,648 bytes
maximum isolation logical bytes:     1,073,741,824 bytes
maximum isolation allocated bytes:   1,073,741,824 bytes
maximum filesystem entries:          20,000
maximum live processes:              32
stdout cap per child:                 8,388,608 bytes
stderr cap per child:                 8,388,608 bytes
aggregate stdout sidecar cap:         8,388,608 bytes
aggregate stderr sidecar cap:         8,388,608 bytes
outer JSONL cap:                     67,108,864 bytes
outer JSONL record cap:              100,000
canonical string cap:                 65,536 UTF-8 bytes
```

The supervisor reports absolute process-family CPU since kernel process start
(including `env`, CPython startup/imports, self, and reaped children), wall
from kernel start ticks to the registered terminal, per-process `ru_maxrss`,
and maximum **observed concurrent family RSS**. The last metric sums current
RSS for the supervisor and every live descendant from `/proc` at a frozen
10-ms monotonic interval and at every observed fork/exec/exit/I/O boundary.
Before any worker exists, the first observer initializes the metric with the
supervisor's cumulative `ru_maxrss`, covering the single-process env/CPython
startup interval without claiming a sampled timestamp for that peak.
Process count and cumulative CPU use the same schedule. The worker calls
`setpgid(0,0)` before mutation; the parent verifies `PGID == worker PID`,
requires every descendant to retain it, stays outside it, and is the only
signal actor. The worker alone reaps normal direct Git children; the parent
reaps the worker and any reparented descendants. Verified subreaper state plus
those disjoint `wait4` roles and the supervisor drain-to-`ECHILD` close
orphan/reap ownership. Final process-family CPU is computed exactly once as
the supervisor's final `RUSAGE_SELF` user+system time plus its final
`RUSAGE_CHILDREN` user+system time after `ECHILD`; worker/per-wait records are
reconciliation diagnostics and are never added again. Thus `env`/CPython
pre-worker time is retained and direct/reparented descendant time is not
double-counted. The executable inventory itself remains sampled as stated in
section 6.3.

Complete no-follow filesystem scans sample logical bytes (`st_size`),
allocated bytes (`st_blocks*512`), and entry count every 250 ms and immediately
before/after every Git child and receipt/token/capture publication operation.
Git object/pack/checkout/receipt/temp bytes and file/dir/fsync/process counts
are disjoint fields. The supervisor drains every pipe continuously in chunks
of at most 65,536 bytes, counts exact streamed bytes, and refuses the next
chunk that would cross its 8-MiB stream cap. Per-process `/proc/[pid]/io` is
captured before reap when available. Network transport bytes are either an
authoritative observed integer or `null` with
`UNAVAILABLE_NO_AUTHORITATIVE_COUNTER`; null is never zero or complete.

All live ceilings are **observed admission caps**. A periodic sample may
detect an overage after it occurred, so the evidence reports the observed
value and sampling schedule and makes no claim of a hard instantaneous peak.
The resource schema uses
`maximum_observed_concurrent_process_family_rss_bytes`, never `peak_rss`.

Output overflow, sampled ceiling violation, or timeout makes the parent
supervisor signal only the negative verified worker PGID with SIGTERM, wait a
five-second monotonic grace, then SIGKILL and must-reap. The supervisor remains
outside that group to publish the failure state. This is
`RESOURCE_INCOMPLETE_NO_DECISION`; residual partial state is disposition, not
an independent artifact mismatch.

### 6.5 Exact physical/Git admission

Validation uses two disjoint domains and a stage-specific allowlist. The
tracked-worktree domain excludes the root `.git/` administrative directory;
its complete dirfd no-follow traversal must equal the Git tree byte-for-byte
and type-for-type. Git mode comparison is only object type plus executable
bit; physical mode must separately be exactly `0600` for non-executable
regular files, `0700` for executable regular files and directories, owner the
effective UID, and device the pinned isolation device. Git status is only a
cross-check.

The only physical states are:

| Observation point | Tracked-worktree-domain allowance |
| --- | --- |
| post-checkout | exact committed tree; no receipt path |
| metered preterminal | committed tree plus exactly the owned receipt staging directory |
| after no-replace publication, before receipt commit | committed tree plus exactly the owned untracked final receipt; staging absent |
| after receipt target commit | final receipt is tracked at its exact four-file tree; staging absent |
| after receipt review commit | review memo and `AGENTS.md`/`TASK.md` status are tracked; staging absent and worktree clean |

These are evidence/admission checkpoints. Temporary commit-construction WIP
between checkpoints is always nonevidence and cannot satisfy or be cited for
any state; it must be absent at the next checkpoint. No other untracked,
ignored, alternate-mode, cross-device, symlink, or unclassifiable entry is
allowed at a checkpoint.

The `.git/` administrative domain is separately traversed and validated under
the CACHE-I receipt schema: real no-follow root, exact generated config/index/
HEAD/ref/log shape, no hooks or nonempty template state, no alternates/shallow/
promisor/replace/graft state, all objects hash-valid and reachable from the
closed expected ref set, no unexpected object/ref/config entry, and exact
fetch/push URLs. Directories and ordinary Git administrative metadata are
`0700`/`0600`; Git object, pack, index and reverse-index immutable payloads are
role-closed at `0400` under `umask 077`. CACHE-I freezes the exact per-role
admin mode map; the worktree `0600/0700` rule is not applied to Git objects.

Expected ref/log/object closure is checkpoint-specific: through PREP receipt
publication, HEAD/local/fresh-remote equal `PREP_EXECUTION_BASE`; after the
receipt target commit, local HEAD equals that target while remote remains the
prior reviewed head until push; after the receipt review's sanitized HTTPS
fetch, HEAD/local/fresh-remote equal the receipt-review head. CACHE-BIND repeats
the same target-then-review transition. At every checkpoint the 37-source
manifest/tree matches reviewed CACHE-I even though docs commits change.

At post-checkout, the exact absent list includes the cache namespace and ten
legacy paths in section 5.4 plus:

```text
docs/saq_a4_v2_par_artifacts_2026_07_14.staging
docs/saq_a4_v2_par_artifacts_2026_07_14
docs/saq_a4_v2_execution_authority_2026_07_14
build/a4_v2
build/a4_v2_verifier
docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15.staging
docs/saq_a4_v2_isolated_clone_prep_artifacts_2026_07_15
```

The last two receipt paths then follow only the stage-specific exceptions in
the table; all earlier absences remain invariant.

`/tmp` is explicitly ephemeral. PREP receipt means observed readiness only;
independent review and PAR admission repeat full identity/absence traversal.
Missing/replaced inode or state fails closed and cannot be recreated under the
consumed authority.

### 6.6 Receipt, terminal, and states

The successful final receipt contains exactly:

```text
clone_inventory.json
clone_operations.jsonl
clone_postcheck.json
prep_seal.json
```

`T_clone_prep_metered` spans kernel process start through the snapshot after
the first three receipt files, journal-copy equality, and clone postcheck are
fsynced. `clone_postcheck.json` contains no terminal timer. PREP-report may
only copy the already frozen meter-start/meter-stop integers; perform
nonnegative ledger arithmetic; validate closed receipt state; hash the three
files; form/fsync
`prep_seal.json`; fsync staging; publish by dirfd-relative
`renameat2(RENAME_NOREPLACE)`; fsync `docs/`; append/fsync the permanent token's
seal identity; and fsync the source Git common directory. It performs no Git,
clone, checkout, source, cache, model, or scientific work.

The seal has no own-size or future-Git field. Independent review reports exact
seal bytes, source-level finite tail closure, token/capture terminal state, and
current full clone revalidation. Tail duration and RSS are exactly
`NOT_MEASURED_NOT_INTERPRETED`; no recursive terminal-performance claim is
made. Independent review verifies the reviewed source closure and final
bytes/state, not a dynamic proof that every intended fsync reached durable
media. The same nonclaim covers TERMINAL-token append/fsync/common-dir-fsync:
it is outside `source_gitdir_pre_terminal_ledger`, and review observes only
the resulting final bytes/state. Failure after receipt rename but before
terminal-token completion leaves the visible tree as invalid nonevidence.

Status precedence is causal and mutually exclusive:

| Order | Condition | Status |
| ---: | --- | --- |
| 0 | no explicit authority | `NOT_AUTHORIZED` |
| 1 | authorized command cannot reach durable START; fixed external incident explicitly cannot prove invocation/durability | `LAUNCHER_INCOMPLETE_NO_DECISION` |
| 2 | after this attempt's durable START, verified source/authority/destination precondition fails before root creation | `PRECONDITION_NOT_MET` |
| 3 | after valid START, TERMINAL is absent, partial, corrupt, or otherwise noncanonical | `CRASH_OR_UNKNOWN` |
| 4 | correct tool encounters I/O/network/permission/storage/timeout/signal/resource failure and closes a typed terminal token | `RESOURCE_INCOMPLETE_NO_DECISION` |
| 5 | semantic Git/source/path/origin/executable/cache identity differs despite successful required operations | `ARTIFACT_INVALID` |
| 6 | prep/schema/timer/canonicalization/ledger implementation defect | `IMPLEMENTATION_INVALID` |
| 7 | receipt and typed success TERMINAL published but uncommitted/unreviewed | `ISOLATED_CLONE_PREPARED_PENDING_COMMIT_REVIEW` |
| 8 | receipt target/review commits pushed; clone HEAD and freshly fetched origin equal review commit | `ISOLATED_CLONE_PREPARED_REVIEW_PASS` |

Every state carries `NO_PAR_AUTHORITY / NO_SCIENTIFIC_DECISION`.

### 6.7 Exact target/review commit closure

Every review commit below is the **direct child** of its target, changes
exactly its fixed review memo plus `AGENTS.md` and `TASK.md`, and leaves every
other tracked blob unchanged. Each target and review is pushed, but the SSH
push transport is not authority. Isolated-clone nodes require a fresh
sanitized HTTPS fetch to make the branch remote-tracking ref equal the review
head before the next node. Every target/review and parent-admission edge formed
before PREP creates the isolated clone, plus a no-clone launcher-incident
terminal, instead uses the bounded sanitized HTTPS `ls-remote` OID equality in
section 6.3. The PREP-authorization review closure also gates the immediate
PREP invocation. “Descends from” without direct parentage is insufficient.

The current CACHE-P target is the direct child of authorization commit
`ffd0f41c40cd5709fb8be8b5888575c2276a3047` and changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json
docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md
docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md
docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json
```

Its direct-child review changes exactly `AGENTS.md`, `TASK.md`, and
`docs/saq_a4_v2_cache_staging_disposition_protocol_independent_review_2026_07_15.md`.
Both commits preserve every other tracked blob, exact implementation-manifest
Git blob `2aa64e50dad19626711e0dd90c038704ac73e328`, all 35 source blobs, and
source-tree SHA-256
`8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.
After each push, and before CACHE-P can reach its maximum outcome, the timeout-
bounded no-clone sanitized HTTPS closure probe in section 6.3 must make the
branch OID equal the pushed target and then review commit respectively. The
target command/result is mandatory content of the direct-child review memo;
the review-head result is only a live non-evidentiary predicate and is not a
Meeting Summary input. No untracked draft is part of either proof.

The future CACHE-I authorization target is the direct child of the pushed
current CACHE-P review head after its closure predicate and a separately
authorized one-shot parent-admission probe. That admission command/result is
mandatory content of the CACHE-I authorization target for independent review.
The target changes exactly
`docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md`,
`AGENTS.md`, and `TASK.md`; its direct-child review uses
`docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md`.
Its target/review each use their separately authorized no-clone closure probe.
The CACHE-I implementation target is the direct child of that reviewed
authorization after a distinct no-clone parent-admission probe recorded in
the fixed additive cache-authority manifest in that implementation target. It
changes exactly the six source paths in section 5.1, these four existing
authority objects,

```text
docs/saq_a4_v2_artifact_schema_2026_07_14.json
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
```

the ten fixed generic paths in section 4, `AGENTS.md`, and `TASK.md`. Its
direct-child review memo is
`docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md`.
Its target/review each use their separately authorized no-clone closure probe.

The PREP authorization target is the direct child of the pushed CACHE-I review
head after a distinct no-clone parent-admission probe recorded in its fixed
authorization document. It changes exactly that document, `AGENTS.md`, and
`TASK.md`; its direct-child review uses the fixed authorization-review memo.
Its target/review each use their separately authorized no-clone closure probe.
The review closure must succeed with no intervening branch/worktree mutation
before the one PREP invocation runs from that review head; that same live
probe is the registered execution-base admission. A successful receipt target
is its direct child and changes exactly the four final receipt files,
`AGENTS.md`, and `TASK.md`; staging is absent. Its direct-child review uses the
fixed PREP review memo plus `AGENTS.md` and `TASK.md`.

If the invocation cannot reach durable START, no receipt path is used. A
terminal launcher-incident target is instead the direct child of the PREP
authorization-review execution base and changes exactly the fixed incident
memo, `AGENTS.md`, and `TASK.md`; its direct-child review changes exactly the
fixed incident-review memo plus `AGENTS.md` and `TASK.md`. The incident-target
closure result is mandatory in that direct-child review memo; a separate live
incident-review closure probe follows its push. After both sanitized HTTPS
`ls-remote` closure predicates succeed, that branch is terminal at
`LAUNCHER_INCOMPLETE_NO_DECISION / NOT_MACHINE_PROVABLE_INVOCATION_OR_DURABILITY`;
it cannot continue to receipt, BIND, or PAR-R1.

The CACHE-BIND target is the direct child of the pushed PREP receipt review
and changes exactly the fixed binding JSON, `AGENTS.md`, and `TASK.md`. Its
direct-child review changes exactly the fixed binding-review memo,
`AGENTS.md`, and `TASK.md`. All PREP authorization/receipt target/review and
CACHE-BIND target/review commits preserve the reviewed 37-source tree.

The PAR-R1 authorization target, if separately authorized, is the direct child
of the pushed CACHE-BIND review after fresh HTTPS equality and changes exactly
its fixed authorization memo, `AGENTS.md`, and `TASK.md`. Its direct-child
review changes exactly
`docs/saq_a4_v2_par_r1_authorization_independent_review_2026_07_15.md`,
`AGENTS.md`, and `TASK.md`; that review head is the only possible later PAR-R1
execution base. Both preserve the reviewed 37-source tree. This closure grants
no current PAR-R1 authority.

After PREP, all intervening commit, review, remote-equality, and CACHE-BIND
actions inside the isolated clone use Git plus static documentation/JSON
inspection only. They run no Python, import, build, or test; any cache
namespace or legacy cache path at any revalidation is `ARTIFACT_INVALID`.

## 7. Later `A4-V2-CACHE-BIND`

CACHE-BIND is not authorized. After PREP review pass, it may create only the
fixed object in section 4 under the reviewed binding schema. Its exact
top-level key closure is:

```text
artifact_kind = "a4_v2_cache_prep_binding"
schema_version = 1
cache_i_target_commit
cache_i_review_commit
cache_protocol_identity
source_manifest_identity
source_tree_sha256
prep_authorization_target_commit
prep_authorization_review_commit
prep_execution_base_commit
prep_receipt_target_commit
prep_receipt_review_commit
prep_seal_identity
prep_token_identity
isolated_clone_identity
remote_branch_identity
par_r1_authorization_slot
```

The schema closes every nested key and requires exact path/hash/size values.
The binding object proves only history that exists before its bytes are formed:
CACHE-I target/review; PREP authorization target/review and execution-base
equality; PREP receipt target/review; 37-source equality through that review;
clone HEAD and sanitized-HTTPS origin equality to the pushed PREP receipt
review; exact PREP remote/branch/root/inode identities; and absence of every
non-allowed blob or physical entry. The PAR-R1 slot contains the fixed path,
status `NOT_ISSUED`, and null commit/hash/size values.

CACHE-BIND changes no implementation source. Its target and review commits
cannot be named inside the binding object without a time loop. Their direct-
parent/change closure and sanitized-HTTPS remote equality are established by
the fixed CACHE-BIND independent-review memo. A later PAR-R1 authorization,
if separately issued, must bind that target/review pair and memo identity.
Maximum outcome is
`CACHE_PREP_BINDING_REVIEW_PASS`, still with no execution authority.

## 8. PAR-R1 and claim ceiling

Only after every prior node passes may the user separately authorize one
PAR-R1 event at the fixed path. That receipt must bind the prepared current
head, CACHE-BIND target/review, exact 37-source manifest/tree, exact command,
all output/cache absences, and one-shot event count. Any source, clone, cache,
or authority identity change invalidates it.

The maximum CACHE-P result is a reviewed governance protocol. Neither it nor a
later PREP/PAR pass establishes an SAQ limitation, arbitrary-cardinality
feasibility, scientific FOM result, systems performance, or novelty, and none
authorizes SRUN, data, or SAQ.

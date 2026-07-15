# A4 V2 Cache/Staging Primary-Source Review

Date: 2026-07-15

Stage: **A4-V2-CACHE-P**

Review outcome:

```text
GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED
NO_GO_DIRECT_PAR_R1
```

This is artifact governance, not research evidence or an SAQ contribution. It
does not change the historical `ARTIFACT_INVALID / NO_SCIENTIFIC_DECISION`
result and authorizes no source edit, clone, cleanup, Python, import, build, or
PAR.

## 1. Question and authority pins

The stopped PAR event left one empty output staging directory and five ignored
repository-local pycs. The later I-R1 repair corrected executable identity but
did not dispose of that state. This review asks whether a corrected event may
reuse or ignore those caches, whether `-B` or a cache prefix suffices, and
whether the old worktree needs destructive cleanup.

The CPython semantic pin is official tag `v3.9.25`, annotated tag object
`a0b04e6630d31bdf096a2755fb4dc6b473295531`, dereferenced commit
`0bbaf5de9744ae1acea3e2c9ad2257d1cc68e847`. Static RPM ownership confirms the
frozen host has `python3-3.9.25-7.el9_8` and
`python3-libs-3.9.25-7.el9_8`. The installed
`_bootstrap_external.py` has SHA-256
`8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4` and
independently exhibits the read-before-write-guard order discussed below.
The exact `/usr/bin/python3.9` regular file is 15,448 bytes with SHA-256
`c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0`;
the installed bootstrap source is 66,447 bytes. A cache tag alone therefore
cannot stand in for the frozen interpreter/bootstrap identity.

The Git execution reference is `/usr/bin/git`, Git `2.52.0`, RPM
`git-core-2.52.0-1.el9`: the binary is 4,397,352 bytes with SHA-256
`f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3`.
The reachable HTTPS helper resolves to the same-RPM
`git-remote-http` binary, 966,840 bytes with SHA-256
`c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902`;
the reviewed built-in helper names resolve to `/usr/bin/git`. The sanitized
launcher also binds `/usr/bin/env`, its exact coreutils RPM, size, and digest.
The bounded no-clone remote-equality wrapper binds `/usr/bin/timeout` from the
same RPM, 36,848 bytes with SHA-256
`025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69`.
GNU's official Coreutils 8.32 release archive and signature are the upstream
CLI/source semantic reference: `src/env.c` plus the matching Texinfo `env`
section for `-i` and `NAME=VALUE`, and `src/timeout.c` plus the matching
Texinfo `timeout` section for the selected duration, signal, kill-after, and
exit-status options. The installed byte identities and RPM owner are separate
host-artifact pins. The source-RPM filename
`coreutils-8.32-41.el9_8.src.rpm` is static provenance only: this review does
not possess the patched source payload and makes no upstream-to-RHEL-binary
source-parity claim. The rolling current web manual is not the version
authority.
These identities are host-artifact pins, not portable Git or CPython claims.
The Python leader is a small dynamically linked ELF; its loader, libpython,
libc, and other mapped shared libraries remain disclosed unbound host inputs.
Accordingly, later admission may claim exact leader-ELF/bootstrap bytes, not
identity of the complete mapped interpreter image. RPM ownership is static
provenance rather than a runtime predicate.
The local terminal authorities are `30dfada` and review `fd5367e`. Exact
metadata and primary URLs are in
`docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json`.

## 2. CPython findings

### 2.1 `-B` is a write policy, not a read ban

CPython 3.9.25 documents `-B` and nonempty
`PYTHONDONTWRITEBYTECODE` as suppression of normal import-time pyc writes.
Pinned `SourceLoader.get_code()` derives and attempts to read and validate a
cache before the later write branch tests `sys.dont_write_bytecode`.

Therefore an existing valid pyc can still be read under `-B`. A cache miss
under `-B` compiles source and performs no normal import-cache write. Explicit
`py_compile`, `compileall`, marshal loaders, or application-written `.pyc`
files are outside that limited guarantee and require a static exclusion.

### 2.2 Ordinary cache validation is not reviewed artifact authority

The import reference and PEP 552 distinguish timestamp, checked-hash, and
unchecked-hash caches. Those policies support ordinary imports; none turns an
ignored file into reviewed implementation evidence. The five payloads were
never read or hashed. Opening them now would violate quarantine and
post-select an input after a failed event.

PEP 3147 confirms a matching `__pycache__` entry may be loaded while source
exists. A Git source-tree hash alone therefore does not prove which
representation executed.

### 2.3 A cache prefix changes the namespace globally

With non-`None` `sys.pycache_prefix`, CPython reads and writes a parallel tree
and ignores source-tree `__pycache__` directories. That can isolate named
files but creates another mutable namespace and changes lookup work for
stdlib and third-party imports, not only A4. It also leaves the old output
staging problem unchanged. This protocol does not select it.

### 2.4 `-B` is not cost-neutral

`-B` retains default installed-cache lookup and reads while globally disabling
normal import-time writes for that interpreter. In a clean A4 checkout it
charges source compilation but removes pyc-write work. A later protocol must
bind this choice before results and charge its effects to B/P. It changes no
scientific FOM, threshold, fixture, or method.

This review makes no claim about later SRUN subprocesses. Any later SRUN
authorization must separately bind every Python actor's cache policy.

### 2.5 Isolated startup protects the PREP tool from the old worktree

CPython documents `-I` as excluding the script directory, current directory,
and user site from `sys.path` while ignoring all `PYTHON*` variables; `-S`
suppresses `site` processing. Combined with `-B`, an absolute, standalone,
stdlib-only PREP script can execute without importing a repository module or
writing a repository cache. That isolated PREP launch is distinct from the
future PAR parent, whose reviewed A4 imports require its clean clone's
`script/` directory.

The later protocol therefore binds one ASCII-only inline `-c` bootstrap. Its
earliest token-publication prefix may import only CPython's builtin `sys` and
`posix` modules, records reviewed full-bootstrap and prefix identities, and
performs no repository or mutable cache read before durable START. After that
boundary it verifies the actual NUL-delimited command line and both identities
before loading the reviewed standalone PREP bytes. This is a fail-closed
protocol construction, not evidence that the future launcher has run.

## 3. Git findings

### 3.1 Local object-copy clone is rejected

Git's official `--local` documentation warns that concurrent source-repository
modification can race the clone. `--no-hardlinks` changes object copying but
does not create an object/ref snapshot. A custom sentinel cannot constrain
ordinary `fetch`, `gc`, `repack`, or other writers in a shared common
directory. The first draft's local-clone choice is therefore rejected.

### 3.2 Remote transport avoids the old object store but is not sufficient alone

A `--no-local --no-checkout --single-branch --no-tags` clone from the public
HTTPS endpoint can fetch the exact reviewed remote commit without opening the
old worktree or object store. A read-only probe confirmed the endpoint exposes
the branch at authorization commit `ffd0f41` on the review date.

This is an inference from Git's object/checkout model, not a claim that a
default clone is hermetic. System/global config, URL rewrites, templates,
hooks, attributes, filters, alternate object databases, replace refs, and
environment variables can change behavior or execute code. Official
`git-config`, `githooks`, and `gitattributes` documentation requires a
sanitized exact environment, an empty template, disabled hooks/filters/
maintenance, no alternate/promisor/shallow/replace state, and a complete
no-follow worktree-to-Git-tree comparison.

The comparison must be ordered. A no-checkout clone is admitted first through
the object database: exact commit/tree, forbidden tracked entry types,
configuration, refs, object reachability, and helper identities are checked
before materializing worktree bytes. The tracked worktree and `.git`
administrative namespace are then separate physical domains; a normal clone
cannot literally equal a commit tree if `.git` is included.
Official Git 2.52 command references for checkout, ls-tree, cat-file,
rev-list, rev-parse, fsck, show-ref, symbolic-ref, ls-remote, and remote
set-url bound the individual operations; the complete config/ref/object-set
equality rule is this protocol's stated inference. The `--no-tags` clone also writes
`remote.origin.tagOpt=--no-tags`, which must be in the exact local-config
allowlist.

### 3.3 A clone receipt is observational readiness, not durability

The selected root is under `/tmp`; reboot or external deletion can invalidate
it. Fsyncing a small receipt does not prove every Git object and worktree page
survives power loss. The admissible claim is only that a reviewed preparation
observed an exact physical clone. Independent review and PAR admission must
revalidate its inode, full tree, Git identities, absences, and remote equality.
Missing or replaced state fails closed and grants no automatic recreation.
If a future authorized launcher cannot publish durable START, no clone receipt
can exist; that terminal incident instead uses one fully frozen sanitized
HTTPS `ls-remote --refs` command and exact one-line parser to establish only
that its reviewed incident commit reached the branch. SSH push success itself
is not treated as authority. The same no-clone probe closes current CACHE-P
remote equality and, only under their own later explicit authorizations, every
future target/review and parent-admission edge formed before the isolated clone
exists. In particular, the PREP-authorization review closure is the required
live execution-base predicate immediately before the one PREP invocation.
Exact `env -i` precedes the pinned GNU `timeout`, so timeout and Git share one
sanitized environment. The narrow claim is only timeout-bounded
successful exit plus the exact one-line stdout and empty stderr: no unnamed
outer capture/process/reap executor or failure-resource claim is made.
Each target-head equality command and result must be recorded in its later
direct-child review memo and is therefore independently reviewed. Review-head
equality necessarily occurs after that memo's commit and push, so it is only a
live, non-evidentiary closure predicate: it is never written back into the same
memo and is not synchronized to the Meeting Summary. The mandatory handoff
synchronizes only the committed, independently reviewed target/review
evidence. A separately authorized next node must perform its own one-shot
parent-admission probe before forming its target and record that distinct
probe in the new target for independent review.

## 4. Local static findings

At authorization commit `ffd0f41`:

1. the bootstrap takes CPU/wall snapshots before importing `a4_v2_runner`;
2. runner imports evidence and producer, producer imports producer-wire, and
   the PAR branch later imports parity;
3. those five basenames match the residual files, whose committed logical
   sizes total `364,538` bytes;
4. ignored pyc provenance and bytes are absent from current B/P authority;
5. the 35-source closure binds source, not loaded-cache provenance;
6. the environment preimage binds no cache mode, startup import state, clone
   preparation, or later binding; and
7. historical staging was created before executable/environment admission, so
   an early failure left a sentinel.

Current source has no audited cache-policy shortcut. The exact 35-source tree
is `8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a`.
A future implementation that adds two governance sources must explicitly
rebind it to 37 file sources; its separately executable inline `-c` bootstrap
must also be bound and statically reviewed as a 38th executable unit. Setting
an environment variable alone is insufficient.

The current branch contains 467 tracked entries and 8,623,405 tracked logical
blob bytes; its Git store has 2,318 loose-plus-packed objects and about 15.62
MiB of reported object data. These pre-result values justify conservative
future preparation safety ceilings; they are not scientific measurements.

## 5. Alternatives

| Alternative | Decision | Reason |
| --- | --- | --- |
| Ignore or admit the five pycs | Reject | Unreviewed code and cache-hit work remain possible. |
| Use only `-B` in the old worktree | Reject | It suppresses writes, not reads. |
| Read/hash the old pycs | Reject | Violates quarantine and still post-selects artifacts. |
| Fresh cache prefix | Reject | Adds a global mutable namespace and different lookup work. |
| Delete old entries | Reject | Destructive and unnecessary once isolation is available. |
| Shared worktree/local clone | Reject | Shared administration or documented object-store race. |
| Sanitized remote clone plus PAR `-B` | Select conditionally | Excludes old state, but requires the staged authority and checks below. |

The selected preparation changes path, transport work, storage, and cache
write policy. Those are disclosed governance costs, not free setup.

## 6. Narrow claim and required stage sequence

The claim is not “no bytecode was ever touched.” Under a cooperative,
dedicated-clone model, later reviewed tooling may establish only that:

- the old residual namespace was never opened by preparation and was not an
  input to the isolated event;
- recognized A4 cache paths were absent before explicit A4 import and at the
  B/P preterminal checks;
- exact argv/runtime state showed `-B`, no cache prefix, and no `PYTHON*`
  environment input;
- the entrypoint and imported A4 modules resolved to reviewed `.py` blobs in
  the exact isolated clone, with expected loaders and absent cached paths;
- static closure excluded explicit cache readers, writers, loaders, hooks,
  mutation, and deletion; and
- a separate PAR-only verifier reproduced serialized/path/Git checks before P
  terminal.

It does not resist a malicious same-UID process or history-erasing actor.
Installed stdlib/site cache reads remain environment inputs. No runtime lock is
added: doing so would expand the frozen post-P `PAR_report` closure. Existing
one-shot authorization, output-root absence, process admission, and fail-stop
semantics remain the concurrency boundary.

Direct PAR-R1 is no-go. Each arrow below requires explicit user authorization,
a focused commit/push, and exact independent review:

```text
CACHE-P reviewed documentation
  -> CACHE-I generic source/schema/static closure (35 -> 37)
  -> PREP-ISO authorization target and review
  -> one sanitized remote-clone preparation attempt
  -> PREP receipt commit, review, push, and fresh remote equality
  -> CACHE-BIND concrete docs-only binding and review
  -> separately explicit PAR-R1 authorization and at most one event
```

SRUN, data, and SAQ are outside this sequence.

## 7. Cost and reviewer interpretation

Future PREP reports process-family CPU/wall/RSS, logical and allocated bytes,
filesystem/object/checkout/receipt counts, bounded stdout/stderr, fsyncs, and
permanent/temporary clone storage. Network transport bytes may be explicitly
`UNAVAILABLE`, never zero or complete; received pack/object storage remains
measured. The retained old quarantine contributes the known 364,538 logical
bytes; allocation and directory bytes remain unknown because the namespace is
not reread. Concurrent-family RSS and periodic filesystem ceilings are
observed admission bounds, not guarantees about unsampled instantaneous
peaks. The permanent token and bounded capture sidecars require a distinct
source-Git-common-directory byte/write/fsync ledger. To avoid self-reference,
the in-token ledger ends before TERMINAL encoding; that final append/fsync tail
is explicitly unmeasured/noninterpreted, and review observes only its final
bytes/state.

Short-lived executable inventory is likewise sampled, not complete tracing.
A future supervisor must use verified Linux child-subreaper state plus an
explicit wait drain if it claims ownership/reaping of orphaned Git descendants.
Its normal ownership is disjoint: the worker reaps direct Git children, while
the parent reaps the worker and reparented descendants. Authoritative family
CPU is final parent `RUSAGE_SELF + RUSAGE_CHILDREN` after `ECHILD`; worker and
per-wait usage records are reconciliation-only and are not summed again.

Future cache observations, source compilation, and verifier work are charged
to B/P. None changes a scientific threshold.

A strict reviewer should classify the entire direction as artifact governance.
A pass tests no SAQ limitation, objective, estimator, frontier, feasibility,
or novelty. It only makes a later synthetic gate interpretable.

## 8. Process boundary

This review used official primary sources, committed Git objects, a read-only
remote ref probe, installed-package metadata, and local static source. It did
not execute Python, enumerate or read a live pyc payload, inspect or alter live
residual contents, create a clone, build, test, run PAR, access data, or modify
SAQ.

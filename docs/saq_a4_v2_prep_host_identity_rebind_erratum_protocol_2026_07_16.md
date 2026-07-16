# A4 V2 PREP Host-Identity Rebind Erratum Protocol

Date: 2026-07-16

Stage: `A4-V2-PREP-HOST-P`

Current authorization: **DOCUMENTATION-ONLY PROTOCOL, EXACT-COMMIT REVIEW,
PUSH, AND MEETING-SUMMARY HANDOFF**

Maximum current-stage verdict:
**HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS**

Host identity rebound: **NOT YET**

Source rebind, PREP, clone, token, PAR-R1, SRUN, and data access:
**NOT AUTHORIZED**

## 1. Exact instruction and narrow interpretation

On 2026-07-16 the user instructed:

```text
为当前 .el9_8.2 做一个 bounded host-identity rebind/erratum
```

This stage records and reviews a bounded additive erratum. It does not edit
any executable source, existing manifest, schema, witness, runtime authority,
or historical protocol object. It does not run Python, PREP, the reserved
HTTPS execution-base probe, a clone, compiler, build, test, fixture, RNG,
cache verifier, PAR-R1, SRUN, or scientific workload.

The erratum answers only four governance questions:

1. which frozen host object changed and why the old PREP head cannot run;
2. which exact replacement identity may be proposed later;
3. which complete source-and-derived-object closure would have to change; and
4. which fresh authorization sequence is required before any invocation.

The stage cannot return `HOST_IDENTITY_REBOUND`, PREP readiness, parity,
synthetic feasibility, an SAQ limitation, systems performance, novelty, or a
database-systems contribution.

## 2. Exact parent and preserved history

The protocol target must be the direct child of:

```text
commit  16a8201ac36e6c8c514848d55ad5ef607eb053b9
tree    dd0745b6979bb9564006d7766846fd5a16d94181
branch  refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

That head is the committed and pushed independent review of the original
PREP authorization record. The following remain immutable historical
evidence at their recorded Git objects:

- CACHE-P primary review, source metadata, protocol, contract, and review;
- CACHE-I implementation target and independent review;
- the original PREP authorization target `e7f940e924a338022bfe8fffcbb3496f12a5a75c`;
- the original PREP authorization review head `16a8201...`; and
- the separately authorized CACHE-I-SYNTAX observations for the old source
  bytes and old inline bootstrap.

This erratum does not rewrite those objects or reinterpret their conclusions.
In particular, the old syntax identities remain historical and must not be
mechanically replaced with new hashes.

## 3. Static prelaunch observation and causal classification

Before any PREP invocation or reserved probe, bounded read-only checks found
that the sole mismatch in the frozen regular-file/link bundle was the CPython
leader executable.

The old reviewed pin was:

```text
path       /usr/bin/python3.9
type       regular
size       15,448 bytes
sha256     c87babf8337b668da60e26d897d694df7bd9a5b7907416e4eda078b9c33d05e0
rpm        python3-3.9.25-7.el9_8.x86_64
```

The only replacement identity admitted for a future rebind is:

```text
path       /usr/bin/python3.9
type       regular
size       15,448 bytes
sha256     c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
rpm        python3-3.9.25-7.el9_8.2.x86_64
source rpm python3.9-3.9.25-7.el9_8.2.src.rpm
```

The current file digest and size equal the values registered for that exact
RPM file. The matching `python3` and `python3-libs` packages report install
time `2026-07-16 17:01:48 +0800`. DNF transaction 205, run as UID 0, replaced
`3.9.25-7.el9_8` with `3.9.25-7.el9_8.2`; the package changelog describes the
`.2` revision as a security fix for CVE-2026-15308. The transaction command
line is absent, so this protocol attributes the replacement to a root-level
package transaction but does not claim whether a human or automation invoked
it.

The installed bootstrap source is now statically attributed to
`python3-libs-3.9.25-7.el9_8.2.x86_64`, while its reviewed bytes remain:

```text
path    /usr/lib64/python3.9/importlib/_bootstrap_external.py
size    66,447 bytes
sha256  8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4
```

All other twelve frozen host objects matched: `/usr/bin/env`,
`/usr/bin/timeout`, `_bootstrap_external.py`, `/usr/bin/git`,
`git-remote-http`, the `git-remote-https` link, and the six registered Git
builtin-helper links. This is not a claim that the whole machine is unchanged.
The dynamic loader, libpython, libc, OpenSSL, and other mapped libraries remain
disclosed unbound inputs exactly as before.

The correct prelaunch classification is:

```text
STATIC_PRELAUNCH_HOST_IDENTITY_MISMATCH
PREP_NOT_INVOKED
START_NOT_CREATED
OLD_UNIQUE_PROBE_NOT_RUN
```

It is not any runtime contract terminal status. No durable START exists, so it
must not be called `ARTIFACT_INVALID`, `PRECONDITION_NOT_MET`,
`LAUNCHER_INCOMPLETE_NO_DECISION`, or `CRASH_OR_UNKNOWN`.

## 4. Why the old authority cannot be reused

The original one-invocation chat authorization was bound to the unchanged,
pushed `16a8201...` authorization-review head. It was not invoked and its
reserved probe was not run, but neither authority is transferable to a new
source head.

After this protocol target mutates the branch, the old states are:

```text
original PREP review head       HISTORICAL_VALID / STALE_FOR_ACTIVATION
original invocation authority   UNSPENT_BUT_NONTRANSFERABLE
original delayed probe          UNSPENT_BUT_SUPERSEDED / NEVER_RUN_OR_REUSED
permanent START token           ABSENT / NOT_CONSUMED
```

This is an authority retirement caused by a changed execution-base contract,
not a failed PREP attempt and not a consumed token. No later stage may run the
old probe, cite it as closure, or carry the old invocation permission forward.

## 5. Additive supersession boundary

The companion machine contract is the sole additive overlay authorized now.
It supersedes only both prose occurrences of the old CPython leader digest,
the matching contract pointer, and the two Python RPM provenance strings for
a future implementation. It does not silently edit the original CACHE-P
protocol, contract, primary review, or source metadata.

The future active authority must bind both:

1. the exact historical base objects; and
2. the exact committed-and-reviewed erratum protocol and contract.

There must be exactly one accepted leader digest. A dual-hash allowlist,
wildcard, version-prefix rule, package-version-only admission, runtime RPM
query, fallback to the old hash, or post-START discovery rule is forbidden.

No path, file type, size, cache tag, interpreter flag, status, retry rule,
resource ceiling, timer, receipt schema, token schema, scientific parameter,
or evidence boundary changes under this erratum.

## 6. Complete future source-rebind closure (not authorized)

A future stage named `A4-V2-PREP-HOST-I` may be opened only by a separate
explicit user instruction. Its authorization target may change exactly
`AGENTS.md`, `TASK.md`, and
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_2026_07_16.md`;
its direct-child authorization review may change exactly those two root files
and
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_authorization_independent_review_2026_07_16.md`.
Only after that reviewed authorization may the implementation target form.
The implementation must update the CPython expectation coherently in exactly
these five filesystem sources:

```text
script/a4_v2_isolated_clone_prep.py
script/a4_v2_cache_policy_verifier.py
script/a4_v2_runner.py
script/a4_v2_verifier.py
script/run_arbitrary_cardinality_a4_v2.py
```

The first source contains both the outer PREP constant and the separately
bound inline bootstrap. The other four are the independent cache verifier,
PAR runner, independent scientific verifier, and entrypoint consumers. A
PREP-only substitution is invalid because it leaves later PAR admission
guaranteed to reject the new leader.

The future implementation may rebind only these derived authority objects:

```text
docs/saq_a4_v2_cache_protocol_authority_manifest_2026_07_15.json
docs/saq_a4_v2_cache_runtime_maximal_instance_2026_07_15.json
docs/saq_a4_v2_cache_runtime_schema_2026_07_15.json
docs/saq_a4_v2_cache_static_closure_2026_07_15.json
docs/saq_a4_v2_implementation_binding_2026_07_14.md
docs/saq_a4_v2_implementation_manifest_2026_07_14.json
docs/saq_a4_v2_source_provenance_crosswalk_2026_07_14.md
```

The updated cache authority must add the reviewed erratum contract as an exact
protocol component and must preserve the historical base-component identities.
The original CACHE-P protocol/contract/primary-source objects, artifact
schema, token/receipt/binding schemas and witnesses, and every scientific
source remain byte-identical.

The implementation target may additionally change only `AGENTS.md` and
`TASK.md`. Its direct-child implementation review may change only those two
files and
`docs/saq_a4_v2_prep_host_identity_rebind_implementation_independent_review_2026_07_16.md`.
Any inventory finding that requires another path is a protocol mismatch: stop
and request an additive erratum rather than silently widening the allowlist.

## 7. Frozen recomputation and review rules for the future source node

The future source target must prove all of the following statically:

- exactly 37 filesystem sources and 38 executable units remain;
- all 27 native/CMake sources and the five unaffected Python sources are
  byte-identical to reviewed CACHE-I;
- only the seven registered old-hash occurrences in the five source files
  become the sole new hash, apart from bounded authority/DAG crosslinks;
- all source SHA-256 values, byte sizes, Git blobs, and the canonical sorted
  37-source-tree hash are independently recomputed;
- inline bootstrap bytes are identical across PREP source, cache authority,
  static closure, and implementation manifest;
- the existing two authorization paths remain unchanged and the raw
  2,778-byte pre-START prologue remains byte-identical;
- runtime schema constants and every maximal-witness leader alias use the
  sole new digest;
- `build_status` remains `NOT_AUTHORIZED_NOT_RUN`;
- no control flow, error precedence, resource limit, path, retry, timer,
  cache, receipt, token, or scientific behavior changes; and
- the old CACHE-I-SYNTAX record remains bound only to the old source snapshot.

Static review is not syntax execution. Any compile-only check for the changed
source snapshot requires a separately named authorization and must not import
or execute a repository code object. No prior syntax result may be relabeled.

## 8. Fresh future authority DAG

All nodes after the current documentation review are closed:

```text
A4-V2-PREP-HOST-P target/review            current documentation stage
  -> A4-V2-PREP-HOST-I-AUTH target/review  NOT_AUTHORIZED
  -> A4-V2-PREP-HOST-I source/review       NOT_AUTHORIZED
  -> fresh PREP authorization/review  NOT_AUTHORIZED
  -> new explicit actual-PREP grant   REQUIRED / NOT_AUTHORIZED
  -> one new immediate HTTPS probe    NOT_AUTHORIZED
  -> one PREP invocation              NOT_AUTHORIZED
```

The future fresh PREP authorization target updates exactly `AGENTS.md`,
`TASK.md`, and the existing path
`docs/saq_a4_v2_isolated_clone_prep_authorization_2026_07_15.md`; its
direct-child review updates exactly the two root files and
`docs/saq_a4_v2_isolated_clone_prep_authorization_independent_review_2026_07_15.md`.
Git preserves the old blobs as historical evidence while retaining the fixed
authorization paths already embedded in the inline bootstrap. The new
authorization must bind the new reviewed source head, exact source tree, PREP
tool, inline source/prologue, erratum identities, and all unchanged
host/resource/status objects. Its direct-child review head, not the current
protocol review and not `16a8201...`, is the only possible future
`PREP_EXECUTION_BASE`.

After that fresh review is committed and pushed, the user must explicitly
authorize exactly one actual invocation. Exactly one newly registered
review-head HTTPS equality probe may then run immediately before launch, with
no intervening branch/worktree mutation. It is distinct from ordinary
documentation target/review remote-equality checks and from the retired old
probe.

## 9. Current exact commit and review closure

The current protocol target changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json
docs/saq_a4_v2_prep_host_identity_rebind_erratum_protocol_2026_07_16.md
```

Its direct-child independent review changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_prep_host_identity_rebind_erratum_independent_review_2026_07_16.md
```

Every other tracked blob and mode is unchanged on each edge. After the target
is committed and pushed, one bounded target-head remote-equality observation
may be recorded in the review memo. That ordinary documentation closure is
not the retired PREP probe and grants no execution-base admission. After the
review commit is pushed, a bounded live review-head equality check may close
this documentation stage; it is operational, non-evidentiary, and also grants
no PREP authority.

## 10. Current prohibitions and claim ceiling

This stage permits no source/manifest/schema/runtime-authority edit beyond the
two new additive documents and branch-status text. It permits no Python,
import, syntax, compiler, build, test, executable, PREP bootstrap/tool, clone,
START token, capture, journal, receipt, CACHE-BIND, PAR-R1, SRUN, quarantine,
dataset, index, generated-result, or SAQ/CAQ action.

No benchmark, base, centroid, cluster-id, query, ground-truth, or index file
may be opened. No environment or package may be installed, downgraded,
replaced, or mutated. Untracked/WIP state is not evidence.

The complete current conclusion is artifact governance only:

```text
HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS   maximum after exact review
HOST_IDENTITY_REBOUND                       not established
PREP                                         not invoked
PERFORMANCE                                  NOT_YET_MEASURED
SCIENTIFIC_DECISION                          NONE
```

After the exact target and direct-child review are committed, independently
reviewed, pushed, and handed off to `saq-meeting-summary`, stop. Do not begin
the future source node automatically.

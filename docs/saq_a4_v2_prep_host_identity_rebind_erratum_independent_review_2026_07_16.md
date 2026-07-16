# A4 V2 PREP Host-Identity Rebind Erratum Independent Review

Date: 2026-07-16

Review scope: one fresh, bounded, independent static review of exact target
`5a47fed05321af39a236d2dfb56d2c0f43708db3`.

## Verdict

**PASS — no finding at LOW severity or above.**

Maximum verdict:

```text
HOST_IDENTITY_REBIND_PROTOCOL_REVIEW_PASS
```

This is artifact-governance protocol/review evidence only. It does not
establish `HOST_IDENTITY_REBOUND`, PREP readiness, an execution-base admission,
parity, synthetic feasibility, performance, an SAQ limitation, novelty, or a
scientific decision.

## Exact target and projection

The reviewed target has the registered topology:

```text
target  5a47fed05321af39a236d2dfb56d2c0f43708db3
parent  16a8201ac36e6c8c514848d55ad5ef607eb053b9
tree    4e44df549b34176664e35513248534f4d24fc309
parent tree dd0745b6979bb9564006d7766846fd5a16d94181
```

Before this memo was created, HEAD was that target, the worktree was clean,
and the local branch tracked the same-named origin-tracking ref without a
reported ahead/behind delta. The direct edge changes exactly four mode-100644
paths:

```text
M AGENTS.md
M TASK.md
A docs/saq_a4_v2_prep_host_identity_rebind_erratum_contract_2026_07_16.json
A docs/saq_a4_v2_prep_host_identity_rebind_erratum_protocol_2026_07_16.md
```

All other tracked blobs and modes are unchanged. The target bytes of those
four paths have SHA-256 values, respectively:

```text
2e67129c6dfae448b1278a7f1760036c60ecdbc40cee1a797a74864b95ca350a
58861757d4f35db571b5f5628fd51cdfc239dfaee7f6dd66883e89fbb3d2a73a
c8e182dd8f7a661e465aa9ce03fa2d7bfed233124209dff43826ea0b32510b09
0cef593b0532070c87be49d3b7b469abe755ff20a072b8bfff915a2bf848289e
```

The companion contract parses with `jq`. Its parent/tree identities agree
with Git; its current target/review projections contain four/three unique
paths; and its path inventories and prose are mutually consistent.

## Host identity

Read-only `stat`, `readlink`, `sha256sum`, and `rpm` observations establish:

```text
/usr/bin/python3.9
  regular, 15,448 bytes
  sha256 c7b3d12b0bcda9356ce5a7e21e66c41476310d595c54b5689bca1e38abd8f42b
  rpm python3-3.9.25-7.el9_8.2.x86_64
  source rpm python3.9-3.9.25-7.el9_8.2.src.rpm
```

The installed RPM file digest for `/usr/bin/python3.9` is exactly the same
SHA-256. The file is not a symlink. The other twelve frozen file/link pins
also match:

- `/usr/bin/env`: regular, 45,088 bytes,
  `4fa9935734560713b5a6250fa3481d1044ad117f220bf32c802af382bb7e5c9b`;
- `/usr/bin/timeout`: regular, 36,848 bytes,
  `025ed27290a98226e03278d99b728a8276e64662b7dea323028b62018316ec69`;
- `_bootstrap_external.py`: regular, 66,447 bytes,
  `8373612b2866d0971f9167ced3a0254204fef058c975f2e30fbb3138797e21d4`;
- `/usr/bin/git`: regular, 4,397,352 bytes,
  `f7d0c1d79341f3d2d8e5c63f89c11400f48af55d8b659251c18cd7d13e3e4ed3`;
- `git-remote-http`: regular, 966,840 bytes,
  `c2c458ee6ecadbb1b95fce9bef7f990a51f6486d06dae3621f8997757380a902`;
- `git-remote-https`: symlink to `git-remote-http`; and
- the six registered Git builtin helpers: symlinks to `../../bin/git`.

Their package ownership/provenance agrees with
`coreutils-8.32-41.el9_8.x86_64`,
`python3-libs-3.9.25-7.el9_8.2.x86_64`, and
`git-core-2.52.0-1.el9.x86_64` as applicable. This is the bounded frozen
bundle, not a whole-host identity claim; the disclosed loader, libpython,
libc, OpenSSL, and other mapped-library inputs remain unbound.

## Source and derived closure

The old leader digest has exactly seven active source occurrences in exactly
five sources:

```text
1 script/a4_v2_cache_policy_verifier.py
2 script/a4_v2_isolated_clone_prep.py
2 script/a4_v2_runner.py
1 script/a4_v2_verifier.py
1 script/run_arbitrary_cardinality_a4_v2.py
```

The five current source SHA-256 values independently match the registered
source closure, and the new digest has no source occurrence yet. The future
inventory contains five unique sources and seven unique derived-authority
objects. Its fourteen unique target paths are exactly the set union of those
twelve paths with `AGENTS.md` and `TASK.md`; no widening is hidden.

The seven derived objects cover the cache authority, runtime maximal witness,
runtime schema, static closure, implementation binding, implementation
manifest, and provenance crosswalk. Historical CACHE-P objects and historical
review/authorization records containing old identities remain immutable.
Future recomputation is expressly unauthorized now.

## Authority, probe, and claim ceilings

The historical states are coherent and non-escalating:

```text
original PREP review head     historical valid / stale for activation
original actual authority    unspent but nontransferable
original unique probe        unspent, superseded, never run or reused
permanent START token        absent / not consumed
```

Source-rebind authorization, source rebind, fresh PREP
authorization/review, a new explicit one-invocation grant, a newly registered
immediate probe, and actual PREP all remain separate unauthorized future
nodes. Ordinary documentation remote equality is not represented as the old
or future PREP execution-base probe.

The recorded target remote-equality evidence was not rerun. The sandboxed
sanitized `ls-remote` attempt failed DNS with exit unavailable, no stdout, and
no remote observation. The escalated identical sanitized command returned
exactly:

```text
5a47fed05321af39a236d2dfb56d2c0f43708db3 refs/heads/saq-arbitrary-cardinality-feasibility-v2
```

The registered HOME/XDG absence paths were absent before and after. This is
only target publication equality.

## Excluded incident and execution boundary

An earlier reviewer invoked the prohibited Python-backed
`dnf history info 205`. It failed immediately while attempting to open
`/var/tmp/dnf.log` on the read-only filesystem, returned no history
observation, and caused no repository, PREP, token, or data mutation. That
entire attempt is excluded from this review. Transaction-history causality is
therefore not independently re-observed here; the PASS rests on the exact
static target, current RPM/file identity, closure, and authority boundaries
reviewed above.

This review ran no Python, repository script, build, test, PREP, probe, clone,
token action, data read, source edit, or scientific executable. It produced no
new scientific or performance evidence.

```text
HOST_IDENTITY_REBOUND       NOT ESTABLISHED
PREP                        NOT INVOKED
PERFORMANCE                 PERFORMANCE_NOT_YET_MEASURED
SCIENTIFIC_DECISION         NONE
```

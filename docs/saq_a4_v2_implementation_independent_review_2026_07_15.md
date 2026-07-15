# Independent review: A4 V2 source implementation

- Date: 2026-07-15
- Branch: `saq-arbitrary-cardinality-feasibility-v2`
- Failed source commit: `3a4f7c588fced0491ec70e59464548a15d9a4b8b`
- Corrected review target: `482c401521460d1742ffe86c39db7130ed038a06`
- Verdict: `SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`

## 1. Scope and method

Three independent static-only tracks reviewed the exact committed blobs at
the corrected target. They separately covered:

1. producer semantics, native launch/reap, exact retry, bundle publication,
   terminal receipts, construction-cost attribution, and the C-to-E handoff;
2. supervisor status precedence, C failure vocabulary, sticky Resource and
   compound-failure handling, SIGINT ownership, fork recovery, and the final
   root boundary; and
3. verifier full-duplex transport, registered 4 GiB evidence bound, streaming
   stderr identity, typed exits, descriptor closure, kill/must-reap recovery,
   and the C-to-E-to-V boundary.

All tracks also independently checked the implementation manifest, binding,
source inventories, Git identities, exact target and parent, and clean-tree
state. The review used Git-object inspection, SHA-256 and byte-size
recomputation, canonical JSON comparison, diff/whitespace inspection, and
static control-flow reasoning only.

No repository Python module was imported or syntax-checked. No compiler,
build, test, parity fixture, RNG, research command, synthetic event, generated
artifact, result, benchmark, dataset, index, or SAQ code path was executed or
read.

## 2. Failed target and corrections

Commit `3a4f7c5` remains permanently classified as failed and non-evidence. It
was not amended or rewritten. Static review found that its source-only
pipeline had unresolved transport, child-recovery, publication, receipt,
cost-boundary, status-precedence, and signal-ownership defects. In particular,
the verifier transport did not yet implement the frozen full-duplex and
registered-size semantics, several exceptional child paths did not close and
must-reap under one owned signal boundary, and the C terminal tail/root-to-E
transition was not a complete, uniquely attributable receipt boundary.

The corrected target closes those defects without changing the scientific
panel, four arms, construction figure of merit, threshold, plan, source
authority, or stage authorization. During correction review, an introduced
regression that made raw `ExternalInterruption` sticky
`IMPLEMENTATION_INVALID` was caught before freeze; the final source again
permits exactly one retry only for sealed
`EXTERNAL_INTERRUPTION/DISCARDED` with no Resource fact. The final binding and
source also freeze the only registered C failure statuses as Artifact,
Implementation, Control, and Resource; every registered but out-of-phase C
status maps to Implementation.

## 3. Exact target identities

```text
commit       482c401521460d1742ffe86c39db7130ed038a06
parent       3a4f7c588fced0491ec70e59464548a15d9a4b8b
tree         5dd3a545f1ab5d8b563d55fbfa0ade94ed2e809d

binding      a7b26a24bba1bbf896797b6a60d74489121ce8aa
manifest     769f192c929419a7ff4b5618e701cc57950788b0
archive      5a1132ebde9936236f017a593a4f3e36fe6384da
evidence     67a9a0e8c952454f61b070c1acaaeb9582d7ec54
producer     3941e17781411cd5c74afb1ac3571cd5cc2090cf
runner       5f080f7adfa300ecdc58a04136e3fff6b3afd82c
verifier     10e7ca78165b935abdde29d598c68fad815e39ba
```

The canonical implementation manifest is 11,953 bytes including its terminal
LF and has SHA-256
`d20eb3aab51f7f9083a055b81f40686679259c5fa883635a756494cb3b468ae2`.
Its binding identity is 45,666 bytes with SHA-256
`54c518d9cfae40e07c0459c11690d3d1ebd395a5d3512f4dc901c048ce22b692`.

All 35 source identities and all seven normative-document identities match
the target commit exactly. The source inventory contains 12 producer-native,
15 verifier-native, and eight Python files, with exact sorted, duplicate-free
CMake and Python closures. Recomputing the canonical ordered
`{path,sha256,size_bytes}` array yields:

```text
d5b8374ff2bfb967e0fbf758e2012029356ef779122681ed4a5a9d901e727cc7
```

## 4. Static control-flow verdict

The corrected source statically implements the frozen 396-unit producer,
compact evidence publication, independent replay, archive, and finite trailer
boundaries. Construction work remains charged only through the registered
`C_setup + C_core + C_bundle_io` figure of merit, while verification,
evidence emission, archival work, memory, and bytes remain separately visible
and mandatory.

The C terminal receipt retains failed-tail and root-closure work exactly once.
Resource observations are sticky, and a higher-precedence C failure combined
with Resource fail-stops before E because the one-axis receipt cannot encode
both facts independently. A physically visible bundle is admissible only at
the exact U395 `PHASE_COMPLETE/ATOMICALLY_PUBLISHED` boundary.

The original unblocked SIGINT mask remains owned from C terminal closure
through E's first fork. Pre-fork failure restores it, or fail-stops while the
blocked owner remains active if restoration itself fails. After a successful
fork, parent recovery owns close, kill, and must-reap without an intervening
fallible setup step. E closes its terminal receipt boundary while SIGINT
remains blocked, then restores the prior mask before V begins.

The verifier uses nonblocking full-duplex selector transport, bounds stdout by
the remaining registered 4,294,967,296-byte evidence allowance, and retains
stderr only as streamed byte count and SHA-256. Every failure path closes the
registered pipes, kills a still-live process group, must-reaps the child, and
maps the frozen typed exit before any success response is admitted.

No independent track found a remaining BLOCKER, HIGH, MEDIUM, or LOW issue in
the exact corrected target.

## 5. Decision and authorization boundary

`A4-V2-I` therefore ends at
`SOURCE_IMPLEMENTED_STATIC_REVIEW_PASS`. This is an artifact-readiness result,
not a PAR result, synthetic feasibility result, SAQ limitation result, method
contribution, or systems-performance claim. A strict database reviewer should
assign it no scientific novelty by itself.

`A4-V2-PAR`, `A4-V2-SRUN`, benchmark/base/query/index access, generated
scientific artifacts, and SAQ modification remain unauthorized. The next
possible action is to ask the user whether to authorize the separately frozen
build-and-parity stage; this review grants no such authority.

# A4 V2 Generic Cache-Policy Source Authorization

Date: 2026-07-15

Authorized stage: **A4-V2-CACHE-I**

Status: **GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_AUTHORIZED**

Maximum outcome: **GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS**

## 1. User instruction and exact parent

After the reviewed CACHE-P target selected

```text
GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED
NO_GO_DIRECT_PAR_R1
```

and the session reported that the next admissible node required a separate
authorization, the user instructed:

```text
授权 A4-V2-CACHE-I
```

This instruction is bound only to the generic source/schema/static-review
node specified by
`docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md` and
`docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json`.

The exact parent is the pushed CACHE-P direct-child review record:

```text
249d5b8c1939acefbf12711790b3e791b019d560
```

The authorization target must be its direct child and may change exactly this
document, `AGENTS.md`, and `TASK.md`. Its direct-child independent review uses
`docs/saq_a4_v2_cache_implementation_authorization_independent_review_2026_07_15.md`.

## 2. Distinct CACHE-I parent-admission predicate

Before this target was formed, the one CACHE-I-authorized no-clone parent-
admission probe ran with cwd `/`, stdin `/dev/null`, and both registered HOME
and XDG paths absent before and after. Its exact argv was:

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

The exact result was:

```text
exit     0
stdout   249d5b8c1939acefbf12711790b3e791b019d560<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

This is a distinct child-node parent-admission role. It is not the earlier
CACHE-P review-head closure and it does not create implementation or execution
evidence.

## 3. Permitted CACHE-I work

After this authorization target is committed, pushed, independently reviewed,
and its registered target/review closure predicates succeed, CACHE-I may:

1. add exactly these two governance sources:

   ```text
   script/a4_v2_isolated_clone_prep.py
   script/a4_v2_cache_policy_verifier.py
   ```

2. make only the frozen cache-governance changes to these existing sources:

   ```text
   script/run_arbitrary_cardinality_a4_v2.py
   script/a4_v2_runner.py
   script/a4_v2_parity.py
   script/a4_v2_verifier.py
   ```

3. update only the four existing authority objects and create only the ten
   generic objects named in protocol section 4;
4. update `AGENTS.md` and `TASK.md` for exact stage status;
5. use static Git/blob inspection, structured JSON parsing with non-repository
   tools, SHA-256/byte-size and canonical 37-source-tree recomputation,
   diff/whitespace checks, and independent source review; and
6. perform exactly the CACHE-I no-clone parent-admission and target/review
   closure probes registered by protocol section 6.7.

The resulting file-source closure is exactly 37: the reviewed 35 plus the two
new governance sources. The separately bound ASCII-only inline PREP bootstrap
is the 38th executable unit but is not a filesystem source path. The existing
canonical source-tree algorithm remains unchanged.

The implementation target may change exactly the path set frozen as
`commit_closure.cache_i_target_changed_paths` in the machine contract. Its
direct-child review may change exactly `AGENTS.md`, `TASK.md`, and
`docs/saq_a4_v2_cache_implementation_independent_review_2026_07_15.md`.

## 4. Frozen invariants and static-review obligations

CACHE-I must preserve:

- all 27 native/CMake source blobs and the four non-allowed existing Python
  source blobs;
- solver, allocation, tie, rounding, representation, packing, fixture, RNG,
  threshold, timer, retry-count, and scientific-verifier behavior;
- the exact bodies and syscall/read closure of `_post_par_report` and
  `_post_par_report_unchecked`;
- the parent protocol, preregistration, erratum, composite authority, and
  historical terminal/cost evidence blobs; and
- the old quarantined residual namespace as unread, unmodified nonevidence.

The additive cache authority, schemas, maximal instances, static closure,
implementation binding, provenance crosswalk, artifact schema, and manifest
must close every requirement in frozen protocol section 5, including:

- implementation-manifest schema version 2 and exact 37-source rebinding;
- one exact ASCII inline-bootstrap identity and raw-prefix prologue identity;
- closed runtime, PREP receipt, PREP token, and future binding schemas with
  exact canonical maximal witnesses;
- complete 38-unit import/call/open/mutation closure;
- exact parent `python -B` PAR command and cache-aware build/index shape
  version 2;
- the seventh `python_cache_policy` environment-preimage field and new
  metered P artifact;
- a complete non-overlapping baseline/candidate byte partition and finite
  cache-governance delta allowlist for the parent precedence crosswalk; and
- exact changed-path and every-other-tracked-blob closure.

Static review must find no issue at LOW or above before the maximum outcome can
be recorded.

## 5. Explicit prohibitions

This authorization permits no Python interpreter, import, syntax check,
`py_compile`, build, compiler, test, fixture, RNG, A4/project native executable, clone,
PREP token, PREP attempt, cache verifier process, PAR-R1, SRUN, or scientific
execution. It permits no read, stat, enumeration, hash, copy, rename, chmod,
cleanup, deletion, or reuse of a quarantined residual. It permits no dataset,
base, query, ground-truth, index, generated-result, or SAQ/CAQ access or
modification.

The two new Python files are reviewed source text only. They must not be
imported, parsed through Python, compiled, or executed under CACHE-I.

## 6. Commit, remote, and stop boundary

The CACHE-I authorization target/review and later implementation target/review
must each be direct-parent, exact-changed-path commits. Before forming the
implementation target, CACHE-I uses its distinct registered parent-admission
probe of the pushed authorization review and records that result in the
additive cache-authority manifest. Target closure results belong in the
corresponding direct-child review memo. Review-head closures occur only after
those memos are committed and pushed and remain live, non-evidentiary
predicates outside the memos and Meeting Summary.

Push success alone is not authority. Failure of any required equality,
direct-parent, changed-path, source, schema, or static-review predicate stops
the stage without PREP or PAR authority.

The maximum result is only:

```text
GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS
```

It is artifact-governance source evidence, not preparation readiness, parity,
synthetic feasibility, an SAQ limitation, a systems result, novelty, or a
database-systems contribution. `A4-V2-CACHE-PREP-ISO`, CACHE-BIND,
`A4-V2-PAR-R1`, SRUN, all data access, and all SAQ/CAQ changes remain separately
unauthorized after this stage.

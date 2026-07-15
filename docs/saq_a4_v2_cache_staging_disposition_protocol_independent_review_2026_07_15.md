# Independent Review: A4 V2 Cache/Staging Disposition Protocol

Date: 2026-07-15

Reviewed stage: `A4-V2-CACHE-P`

Exact review target:
`56210f8f81557ed7a2521bf7f13c9f937396da29`

Independent review verdict: **EXACT_TARGET_INDEPENDENT_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

Primary-source decision:

```text
GO_SANITIZED_REMOTE_ISOLATION_PROTOCOL_REQUIRED
NO_GO_DIRECT_PAR_R1
```

## 1. Scope and method

Three independent read-only tracks reviewed the exact committed target:

1. the producer/closure track checked the full protocol, causal remote-
   authority DAG, target/result persistence, exact Git tree, non-allowed-tree
   identity, document identities, and source-manifest closure;
2. the supervisor/authority track checked official-source claim ceilings,
   pre-clone and post-clone authority, failure precedence, PREP process/CPU
   accounting, exact changed paths, and authorization boundaries; and
3. the independent-verifier track checked the machine contract, parser and
   one-shot roles, runtime signal/resource mapping, exact source preservation,
   and agreement between the prose and JSON objects.

The review used committed Git-object inspection, SHA-256/size recomputation,
structured-document parsing with `jq`, diff/whitespace checks, and static
reasoning only. No repository Python was imported or executed. No compiler,
build, test, clone, PREP, PAR, RNG, A4/project native executable, generated
artifact, benchmark, dataset, index, or SAQ path was run or read. The quarantined
bytecode payloads and empty staging directory were not opened, altered,
removed, renamed, or reused. Untracked/WIP state was not evidence.

## 2. Exact Git and document identities

```text
target       56210f8f81557ed7a2521bf7f13c9f937396da29
parent       ffd0f41c40cd5709fb8be8b5888575c2276a3047
tree         bd50ad74bd1caf21bd5f63327c0e0975e80a6c24
subject      docs: freeze A4 V2 cache isolation protocol

AGENTS       fee97076d9ede83d864426c215d933c71c2e4db5
TASK         fa0353017485ac06c30843aa3e6407a5268c75a8
sources      aa99413395d898dbb9fe1287f72db25246c0020a
review       0f0942e752cdac6209cf33ad1979a811fe8dc2f4
protocol     af2117c409a8d4d3eba61a994984556d5418d304
contract     381cb355634632716096885def26847a58eb6706
```

The target has the sole direct parent required by the protocol and changes
exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_cache_staging_disposition_contract_2026_07_15.json
docs/saq_a4_v2_cache_staging_disposition_protocol_2026_07_15.md
docs/saq_a4_v2_cache_staging_primary_source_review_2026_07_15.md
docs/saq_a4_v2_cache_staging_primary_sources_2026_07_15.json
```

Every other tracked blob is unchanged. The parent and target non-allowed-tree
preimages have the same SHA-256
`4d4593a42f3eb0957b188d59383a28a5bf84e41db6303cf043922bc1dd9c0073`.
The entry count changes only from 467 to 471 because the four protocol objects
are new. `git diff --check` passes.

Exact committed document measurements are:

```text
AGENTS.md
  21,716 bytes
  22e7738cb3728e11e83a28209c5e73fa842b4650e6cdacf828a2b3ed78e60f2a
TASK.md
  16,573 bytes
  bb69f67aee2ad9292121feca13643fae3f631ac2ec907c72797d65ca45367dc0
primary sources
  12,836 bytes
  2b92da17bb14a653d3eded57df606d1ec092e2d48a36bbcecadaed93a243bfb0
primary review
  17,517 bytes
  63e5441fcce349af348f066cfbb4123fd771e1a0bda5a6836a249406bbe21ab7
disposition protocol
  62,883 bytes
  3cdeab39081dd8558683587f385e8d2c849d8414d7fe57b236dd89d6237a2149
disposition contract
  58,109 bytes
  06fb28c460cf2a0c4f75525abb69695c40da810892351ea0bbf96a0efe5ad64a
```

Both JSON documents parse as top-level objects and preserve terminal LF.

## 3. Target remote-equality closure

The target was pushed before the single registered target-head probe. The
probe used cwd `/`, stdin `/dev/null`, and verified that the exact HOME and XDG
paths were absent before and after. Its argv was:

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
stdout   56210f8f81557ed7a2521bf7f13c9f937396da29<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

All three reviewers found that result matches the frozen parser. This memo
contains no review-head result: that probe can occur only after this memo's
commit is pushed and is a live non-evidentiary predicate, never an input to
this memo or the Meeting Summary.

## 4. Preserved implementation closure

The implementation manifest remains Git blob
`2aa64e50dad19626711e0dd90c038704ac73e328`. Its exact 35 source entries retain
their parent blob OIDs, SHA-256 values, and byte sizes. Independent canonical-
array recomputation yields source-tree SHA-256:

```text
8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a
```

Implementation-path comparison is empty. No source, environment, cache,
staging, schema implementation, clone, preparation, binding, PAR, SRUN, data,
or SAQ state changed in the reviewed target.

## 5. Protocol verdict and boundary

The protocol correctly rejects direct PAR-R1. `-B` is treated as a write
policy rather than a read ban; the old residual namespace remains quarantined
and unread. A future sanitized remote isolation path is specified with
pre-clone no-clone authority, exact target/review and parent-admission roles,
an independently reviewed generic source/schema stage, separately authorized
PREP, post-clone fresh-fetch authority, concrete binding, and only then a
separately explicit PAR-R1 authorization.

The target closes source/reference claim ceilings, one-shot probe causality,
Meeting Summary evidence rules, PREP parent/worker reaping and nonduplicated
CPU aggregation, runtime signal/resource precedence, exact changed-path
sets, and the future direct-parent DAG. All three exact-target reviews report
no finding at LOW or above.

The exact target therefore reaches:

```text
EXACT_TARGET_INDEPENDENT_REVIEW_PASS
```

At formation of this direct-child review record, its commit/push and the
subsequent one-shot review-head live closure predicate have not yet occurred.
The durable stage status is therefore:

```text
REVIEW_RECORD_PENDING_PUSH_LIVE_CLOSURE
```

Only if this review record is committed as the exact direct child, pushed, and
the registered review-head closure probe succeeds may the session reach the
conditional maximum `CACHE_STAGING_POLICY_REVIEW_PASS`. That later live result
is deliberately absent from this memo and cannot be back-written into it.

The conditional maximum is a reviewed artifact-governance protocol, not
implementation or execution evidence, a parity result, synthetic feasibility
evidence, an SAQ limitation, a systems-performance result, novelty, or a
database-systems contribution. `A4-V2-CACHE-I`, PREP, CACHE-BIND,
`A4-V2-PAR-R1`, SRUN, benchmark/data access, and SAQ/CAQ modification all
remain unauthorized. Each future edge requires a new explicit user
instruction; this review grants none.

# Independent Review: A4 V2 Generic Cache-Policy Source Authorization

Date: 2026-07-15

Reviewed stage: `A4-V2-CACHE-I` authorization target

Exact review target:
`4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d`

Independent review verdict: **AUTHORIZATION_EXACT_TARGET_REVIEW_PASS**

Finding threshold: **0 findings at LOW or above**

Maximum authorized later outcome:
**GENERIC_CACHE_POLICY_SOURCE_STATIC_REVIEW_PASS**

## 1. Scope and method

Three independent read-only tracks reviewed the exact committed and pushed
authorization target:

1. the producer/closure track checked direct ancestry, exact changed paths,
   every registered source identity, the non-allowed tracked-tree projection,
   scope, and target-head equality;
2. the supervisor/authority track checked the frozen CACHE-P DAG, probe roles,
   static-only authority, future path closure, claim ceiling, and prohibition
   of PREP/PAR/data/SAQ expansion; and
3. the independent-verifier track checked all document bytes and identities,
   the source manifest/tree, parent-admission and target-closure parsers, and
   exact review-commit requirements.

Review used committed Git-object inspection, `jq`, SHA-256/size checks,
diff/whitespace checks, and static reasoning only. No repository Python,
import, syntax check, compiler, build, test, fixture, RNG, A4/project native
executable, clone, PREP, PAR, SRUN, data, index, or SAQ/CAQ path was executed
or read. The quarantined bytecode and staging residuals were not enumerated,
statted, opened, hashed, changed, or removed. WIP and untracked files were not
evidence.

## 2. Exact Git and document identities

```text
target       4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d
parent       249d5b8c1939acefbf12711790b3e791b019d560
tree         1e464244291423455f9da8422cd41597e5e37f53
subject      docs: authorize A4 V2 generic cache policy source
```

The target has the sole direct parent required by the frozen protocol and
changes exactly:

```text
AGENTS.md
TASK.md
docs/saq_a4_v2_cache_implementation_authorization_2026_07_15.md
```

Exact target measurements are:

```text
AGENTS.md
  git blob  c02e531e40537eb4dc331f4addfc0452be5ae1a1
  bytes     23,806
  sha256    d4b88f79480d8376651778a490de82deb80fd065a56f07ccd92e72cf71d92077
TASK.md
  git blob  977669cf0416a93fb5d014dd62e96de6305a4be9
  bytes     19,666
  sha256    633e46b42548c1d27c6a75afcec197fec4a182ec3a73fe5c1208c5936b72e55b
authorization
  git blob  e23dd46fc1d1f49b71e055f0f9640ad6903a21bb
  bytes     7,592
  sha256    b30e422e1a5a185312be992d3cc97c5a63ade73f119f627b8e7760687ddee437
```

After excluding the exact three changed paths, parent and target projections
each contain 470 entries and have identical SHA-256
`6196521a716fe148017aa013d928a1a1f1ec8917c85ca3e656fd8fea2c21dcfb`.
Every other tracked blob is unchanged and `git diff --check` passes.

## 3. Preserved 35-source closure

The implementation manifest remains Git blob
`2aa64e50dad19626711e0dd90c038704ac73e328`. All 35 registered file-source
identities, including the eight Python sources and all 27 native/CMake
sources, are unchanged. The canonical source-tree SHA-256 remains:

```text
8d8b5d3f8990e5d360e0a617d157a8b934c14d0f37b69f399bcc62c71f98360a
```

Implementation-path diff is empty. The target changed-path set contains none
of the six later CACHE-I source paths, ten generic objects, four authority-
object changes, or future implementation review memo. The 35-to-37 rebinding
is authorized only for the later exact implementation target after this
authorization edge closes.

## 4. Remote-equality roles

### 4.1 Distinct child-node parent admission

The committed authorization records the one distinct CACHE-I parent-admission
probe performed before target formation. It used the frozen sanitized command,
cwd `/`, stdin `/dev/null`, and absent HOME/XDG paths. Its exact result was:

```text
exit     0
stdout   249d5b8c1939acefbf12711790b3e791b019d560<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

This role is not a reuse of the earlier CACHE-P review-head closure.

### 4.2 Authorization-target closure

After target commit and push, the one registered target-head closure probe
used this exact argv:

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
stdout   4f38ca9e056e2a8e40f5f966407a6bc6ddb51b5d<TAB>refs/heads/saq-arbitrary-cardinality-feasibility-v2<LF>
stderr   empty
HOME     absent before and after
XDG      absent before and after
```

The remote branch therefore equalled the exact review target for this role.
This memo contains no authorization-review-head closure result. That probe can
occur only after this memo is committed and pushed and remains a live, non-
evidentiary predicate outside this memo and Meeting Summary.

## 5. Authority verdict and stop boundary

The reviewed target binds the user's instruction only to the generic
source/schema/static-review node frozen by CACHE-P. It permits the exact later
37-file-source/38-executable-unit closure, closed schemas/maximal instances,
authority rebinding, static inspection, exact commits, registered no-clone
probes, independent review, push, and mandatory Meeting Summary Handoff.

It does not authorize Python/import/syntax/build/test execution, quarantine
access or cleanup, an isolated clone, PREP token or attempt, CACHE-BIND,
PAR-R1, SRUN, data/index access, environment mutation, or SAQ/CAQ change.
Artifact governance is not preparation readiness, parity, feasibility,
systems performance, novelty, or a database-systems contribution.

The exact target therefore reaches:

```text
AUTHORIZATION_EXACT_TARGET_REVIEW_PASS
```

At formation of this direct-child review record, its commit/push and later
review-head live closure have not occurred. The branch must not form the
implementation target until this review is committed and pushed, that live
closure succeeds, and the separately registered implementation-parent
admission probe of the pushed review head succeeds. That later parent-admission
result belongs in the additive cache-authority manifest for exact review.

No PREP, CACHE-BIND, PAR-R1, SRUN, data, or SAQ/CAQ authority exists after this
review.

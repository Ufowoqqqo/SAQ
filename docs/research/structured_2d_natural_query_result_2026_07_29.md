# Structured-2D natural-query result

Date: 2026-07-29

Branch: `saq-structured-2d-modeling`

Frozen implementation: `8a7b261f4011d90f7aa9f74a95b6e53d4e1148e1`

Design:
`docs/research/structured_2d_fair_query_evaluation_2026_07_24.md`

## Decision

The shared-shape two-dimensional representation (`S`) is **NO-GO under the
frozen natural-query rule**.

Neither the 32-byte nor the 64-byte code moves the same
Recall@100--throughput frontier on both SIFT1M and GIST1M at both coarse-index
sizes. This is the predeclared terminal requirement. It is not rescued by a
positive point on one dataset or one coarse-index setting.

There are real local positives:

- both 32-byte and 64-byte S pass the speed and quality routes on
  `GIST/nlist=1024`;
- 64-byte S passes both routes on `SIFT/nlist=4096`; and
- the native S scan can be materially faster than full-dimensional OPQ when
  it searches enough candidates.

They do not compose into a common result:

- S fails all routes on SIFT at 32 bytes;
- S fails all routes on `SIFT/nlist=1024` at 64 bytes; and
- the apparent GIST `nlist=4096` wins fail the frozen complete-index-byte
  requirement.

The scientific conclusion is therefore narrower than “two-dimensional
quantization does not work.” The compact shared shape can help in some
operating regions, but its benefit is not robust to dataset, storage budget,
and coarse-index granularity. It does not support a SIGMOD/VLDB/ICDE-level
general frontier claim in this form.

## What was tested

Every database vector stores exactly 32 or 64 code bytes. All arms use:

- the same full-dimensional PCA;
- the same `nlist={1024,4096}` coarse centroids and database assignments;
- the same ordered lists for each query;
- the same fixed nine-point `nprobe` schedule;
- full-dimensional L2 distance and top 100;
- one warmup and seven measured repetitions;
- single-thread per-query latency and 12-core batch throughput; and
- complete timed query transform, coarse search, table construction, scan,
  and top-100 maintenance.

Here `nlist` is the number of coarse database cells. `nprobe` is how many of
those cells a query searches. Larger `nprobe` usually raises Recall but also
does more work.

The decisive competitors are full-dimensional PQ, OPQ, and PQ FastScan at
matched code bytes. `D128`, `V128`, `PQ128`, IVF-Flat, and the preselected
RaBitQ points provide mechanism, quality, and context checks.

S encodes the first 128 PCA residual coordinates. On GIST, the remaining 832
coordinates are reconstructed as the selected cell centroid, exactly as
frozen before query access. Full-dimensional PQ/OPQ encode all 960
coordinates and are intentionally stronger controls.

## Integrity acceptance

The natural matrix completed without dropping an arm, dataset, probe point,
mode, or repetition.

| Check | Observed | Required | Result |
| --- | ---: | ---: | --- |
| logical arm cells | 94 | 94 | pass |
| warmup passes | 188 | 188 | pass |
| measured passes | 1,316 | 1,316 | pass |
| successful ledger keys | 1,504 | 1,504 | pass |
| fixed `nprobe` points per arm/mode | 9 | 9 | pass |
| measured repetitions per point | 7 | 7 | pass |
| aggregate CPU | 239.253 h | at most 256 h | pass |
| aggregate wall time | 101.222 h | at most 120 h | pass |
| maximum recorded RSS | 11.12 GiB | at most 16 GiB | pass |

For every fixed arm and probe point:

- the returned-ID hash, candidate count, and Recall are identical across the
  warmup and all seven repetitions;
- single and 12-core modes return identical IDs and Recall;
- every single-query raw-latency file has the exact registered shape; and
- the summary was regenerated twice from the immutable matrix with
  byte-identical outputs.

The ledger contains one additional failed row. It is the conservatively
charged, operator-interrupted GIST OPQ warmup from adding a wall-clock
deadline. The same required warmup later passed. It is not a correctness or
scientific failure and remains charged to both budgets.

Artifact identities:

```text
execution_ledger.tsv
  8de47e4bcd81ae767eaa346d487bd4b2e8192c3bcc72663db4e300802db37846

points.tsv
  3f3c268c25f284aa5f5a38b1b05f25d42327816e9a57edaef678f7432fd7e774

s_comparisons.tsv
  9434a01e92b9168795706a11e617a92a5865b29a4a28052991ad5e6e02fed650

group_decisions.tsv
  000fbe52e54de40979d47f7fb764b98d3bf600ec79f5c7444198030e5a9def60
```

## Frozen frontier result

“Speed pass” means at least 10% more median end-to-end QPS than the fastest
eligible matched-Recall full-dimensional baseline, with p95 latency no more
than 5% worse. “Quality pass” means at least 0.002 absolute Recall improvement
over the highest-Recall baseline within 5% of S's QPS. Both routes also
require no larger complete index, no more than twice the baseline build CPU,
and no domination by the preselected contextual arm.

| Dataset | Coarse cells | Code bytes | Speed route | Quality route | Decisive observation |
| --- | ---: | ---: | ---: | ---: | --- |
| GIST | 1,024 | 32 | pass | pass | S is faster at eligible Recall |
| GIST | 1,024 | 64 | pass | pass | S is faster and reaches useful Recall |
| GIST | 4,096 | 32 | fail | fail | complete index is larger |
| GIST | 4,096 | 64 | fail | fail | complete index is larger |
| SIFT | 1,024 | 32 | fail | fail | slower and lower Recall |
| SIFT | 1,024 | 64 | fail | fail | no material quality gain; slower |
| SIFT | 4,096 | 32 | fail | fail | slower and lower Recall |
| SIFT | 4,096 | 64 | pass | pass | positive only at high probe counts |

The terminal rule requires one budget and one route to pass all four
dataset/coarse-size combinations. All four terminal combinations fail:

```text
32 bytes, speed route   FAIL
32 bytes, quality route FAIL
64 bytes, speed route   FAIL
64 bytes, quality route FAIL
```

## Representative points

These points explain the result without selecting new operating points; every
point comes from the frozen grid.

### Where S works

- On `GIST/nlist=1024/32 B`, at `nprobe=16`, S reaches Recall `0.43268`
  at `5,716` QPS. Against the frozen matched-Recall OPQ point it is about
  `121%` faster, and its p95 single-query latency is about `31%` lower.
- On `GIST/nlist=1024/64 B`, at `nprobe=64`, S reaches Recall `0.65165`
  at `1,605` QPS. It is about `183%` faster than the eligible OPQ point and
  has about `56%` lower p95 latency.
- On `SIFT/nlist=4096/64 B`, at `nprobe=256`, S reaches Recall `0.926075`
  at `966` QPS. It is about `56%` faster than the matched-Recall OPQ point,
  with about `29%` lower p95 latency. Against the eligible
  matched-throughput point its Recall advantage is `0.002142`, just above the
  frozen `0.002` materiality threshold.

### Where S fails

- On `SIFT/nlist=1024/32 B`, even S's best raw speed comparison is about
  `28%` slower, with substantially worse p95 latency. At a representative
  higher-probe point its Recall trails the eligible baseline by about
  `0.079`.
- On `SIFT/nlist=4096/32 B`, the best raw speed comparison is about `19%`
  slower, and its best quality comparison is about `0.042` Recall worse.
- On `SIFT/nlist=1024/64 B`, the closest quality comparison is effectively a
  tie but slightly negative (`-0.000413` Recall), while S is about `11%`
  slower and has about `17%` worse p95 latency at the corresponding
  low-probe point.
- GIST with 4,096 coarse cells has large raw speed advantages, but S must
  carry the external full-dimensional routing state required by its
  head-only representation. Its complete serialized index is then larger
  than the matched full-dimensional baseline, so the predeclared storage
  condition rejects those points.

## Interpretation

### What the result supports

The native S consumer is real, deterministic, and sometimes fast. Its
per-list table construction can be amortized when enough candidates are
searched. The `SIFT/nlist=4096/64 B` positive region is the clearest evidence
that the shared two-dimensional representation can convert offline modeling
quality into an end-to-end query advantage.

The result also confirms the earlier warning that average reconstruction
error is not a sufficient query claim. The same representation changes
position substantially across datasets, coarse grids, and probe counts.

### What the result does not support

It does not show a robust replacement for PQ or OPQ. The decisive 32-byte
SIFT result is negative, and the 64-byte SIFT benefit appears only for one
coarse grid at high probe counts. A strict reviewer can reasonably describe
this as an operating-region effect rather than a new general frontier.

The strong GIST head-only behavior must not be interpreted as pure evidence
for the shared codebook shape. GIST does not store a per-vector tail. The
documented tail-centroid approximation can admit cross-cell false positives
as more cells are searched, and it affects head-only arms differently. The
GIST result is valid under the frozen system definition, but it is not a
clean mechanism attribution for two-dimensional shape alone.

The GIST `nlist=4096` rejection is partly artifact engineering: the external
coarse state is charged because S needs it to define the complete system.
Even if that accounting were later redesigned, SIFT would still prevent the
current terminal claim.

### Reviewer-facing claim boundary

The defensible statement is:

> A compact shared-shape two-dimensional code can produce local end-to-end
> wins, including one SIFT1M 64-byte region, but it does not move a common
> Recall--throughput--storage frontier across SIFT1M and GIST1M under the
> frozen fair comparison.

Do not claim:

- that S beats PQ/OPQ generally;
- that GIST proves the shared-shape mechanism is better;
- that a single passing `nprobe` or `nlist` establishes a contribution;
- that the head-only GIST score is a full-dimensional learned residual; or
- that the negative terminal decision means all structured 2D models are
  impossible.

## Reproduction

The raw matrix remains under:

```text
/tmp/structured-2d-natural/matrix-v1/
```

Generate the deterministic summaries with:

```bash
python research/structured_2d/summarize_natural_matrix.py \
  /tmp/structured-2d-natural/summary-v1
```

The generated files are:

```text
points.tsv
s_comparisons.tsv
group_decisions.tsv
summary.txt
```

The script validates successful ledger keys, raw latency shapes, Recall and
ID stability, computes the frozen seven-repeat medians and discrete
frontiers, and applies the storage, build, p95, and contextual constraints.

## Final disposition

The current structured-2D natural-query direction is closed as a negative
terminal result under its frozen hypothesis. Preserve the implementation,
matrix, diagnosis, and local positive points as evidence.

Any successor must start from a new scientific question rather than rescue
this result by changing datasets, probe grids, thresholds, byte accounting,
or the GIST tail after seeing outcomes. The most useful future question is
why the 64-byte high-probe SIFT region works while the 32-byte and
`nlist=1024` regions do not, and whether that mechanism can be made robust
without adding outcome-selected policy.

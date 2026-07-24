# Independent full-word VQ fair query evaluation

Date: 2026-07-24
Branch: `saq-structured-2d-modeling`
Design base: `76fb83aa94d0bdee2e553199d2fd490286151b4f`

## Purpose and claim

This document freezes the first fair held-out query evaluation of the
shared-shape full-affine two-dimensional VQ model (`S`). It does not assume
that S is an SAQ encoder. S is an independent compressed representation with
its own packed labels and lookup consumer.

The falsifiable question is:

> At exactly 32 or 64 code bytes per database vector, does S move the
> Recall@100--latency/QPS frontier against the best fairly trained and
> equally optimized product-quantization control when all arms use the same
> coarse IVF assignments and the full end-to-end query cost is counted?

The working hypothesis is that S's reusable non-Cartesian two-dimensional
shape improves distance ordering enough to compensate for compact-table
construction. Failure includes any of the following:

- the reconstruction gain does not improve Recall;
- a full-dimensional PQ or OPQ control has equal or better quality;
- per-cell table construction erases the scan advantage;
- the result exists only at one favorable IVF cell size;
- an apparent QPS gain comes from different candidate lists, weaker Recall,
  omitted query transforms, omitted table construction, or extra storage; or
- S does not produce a material Pareto improvement on both datasets.

No query result may change the representation, fit rule, coordinate view,
datasets, coarse grids, code budgets, baselines, `nprobe` schedules, metrics,
or decision rule below.

## Why these controls are required

Product Quantization already decomposes a vector into independently quantized
subspaces and evaluates asymmetric distances with lookup tables. OPQ already
learns a rotation to improve that decomposition. SIMD PQ work shows that a
model-quality comparison is insufficient unless the lookup consumer is also
competitive. RaBitQ, Extended RaBitQ, and SAQ provide recent quantization
frontiers with different code and factor layouts.

Therefore:

- S versus a scalar grid isolates the value of a non-Cartesian shared shape;
- S versus independent 2D VQ isolates the cost and quality of sharing;
- S versus PQ/OPQ is the decisive deployable comparison;
- IVF-Flat separates coarse-assignment misses from quantization misses; and
- SAQ and RaBitQ-family points prevent a narrow PQ-only Pareto claim, but
  their actual bytes must be reported rather than treated as nominally
  matched.

Primary sources:

- Jégou, Douze, and Schmid, [Product Quantization for Nearest Neighbor
  Search](https://doi.org/10.1109/TPAMI.2010.57).
- Ge et al., [Optimized Product
  Quantization](https://people.csail.mit.edu/kaiming/publications/pami13opq.pdf).
- André, Kermarrec, and Le Scouarnec, [Quicker
  ADC](https://arxiv.org/abs/1812.09162).
- Gao and Long, [RaBitQ](https://arxiv.org/abs/2405.12497).
- Gao et al., [Extended
  RaBitQ](https://arxiv.org/abs/2409.09913).
- Li et al., [SAQ](https://arxiv.org/abs/2509.12086v2).

The executable dependency is the repository-pinned Faiss revision
`0ca9df4792b173d573044ee14ca0704780176e82` (`v1.14.3`). The SAQ contextual
implementation is the production source at design base `76fb83a`; later
documentation or S-specific code must not silently change that baseline.

## Datasets and held-out boundary

The confirmatory datasets are the standard TEXMEX splits:

| Dataset | Dimension | Learn | Database | Queries | Ground-truth depth |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT1M | 128 | 100,000 | 1,000,000 | 10,000 | 100 |
| GIST1M | 960 | 500,000 | 1,000,000 | 1,000 | 100 |

Use the standard `learn`, `base`, `query`, and `groundtruth` objects without
row removal or query subsampling. Record their paths, byte sizes, shapes, and
SHA-256 values after access becomes permitted. Reject an object whose format,
shape, or ground-truth depth differs; do not repair it by selecting another
subset.

The existing `gist_sample50k` and `cifar60k` panels remain base-only evidence.
They are not confirmatory query datasets:

- the 50k GIST subset does not currently have a bound ground truth against
  exactly that subset; and
- the CIFAR object has no independent frozen query/ground-truth split, while
  its existing PCA and model construction used all 60,000 rows.

They must not be used as a favorable pilot whose Recall results influence the
confirmatory design.

Learn and database vectors are query-unaware inputs. Query vectors and ground
truth remain unread until the query-free implementation conditions near the
end of this document hold.

## Common transform, coarse index, and candidate schedule

Metric is squared Euclidean distance in the original full-dimensional space.
Train one full-dimensional orthonormal PCA transform per dataset using only
the official learn split. Apply the identical transform to all arms. PCA does
not reduce dimension and therefore preserves exact L2 distance.

For each dataset train two shared coarse IVF quantizers with
`nlist in {1024,4096}` from the full official learn split. Freeze Faiss
k-means to:

```text
seed=1234
niter=25
nredo=1
spherical=false
metric=L2
```

Every arm uses the identical centroids, database list assignments, coarse
search function, and ordered probed-list IDs. Before timing, run that common
coarse function once to save reference list IDs and distances for consistency
checks only.

During every measured arm and repetition, the total timer starts before the
query transform and calls the same common coarse function again inside the
timed region. Its output is passed directly to the arm's equivalent of Faiss
`search_preassigned`. The reference lists saved outside timing are never used
as the timed search input. This applies equally to single-query latency and
the full throughput batch: coarse search is computed once per submitted query
per measured arm, neither omitted nor added later.

An arm may not train, own, or invoke a different coarse quantizer. Timed
coarse outputs must be byte-identical to the saved reference outputs.

The probe schedule represents the same fractions of the coarse index:

| `nlist` | Frozen `nprobe` values |
| ---: | --- |
| 1024 | 1, 2, 4, 8, 16, 32, 64, 128, 256 |
| 4096 | 4, 8, 16, 32, 64, 128, 256, 512, 1024 |

There is no query-selected `nprobe`. Report every point, including dominated
ones.

For every dataset, `nlist`, and `nprobe`, record outside timed regions:

- actual candidates per query;
- 32-lane padded candidates per query when an arm uses padding;
- each selected list's unpadded size;
- min, p10, p25, median, p75, p90, p95, p99, and max;
- query fractions with total candidates `<256`, `256--1023`,
  `1024--8191`, and `>=8192`;
- selected-list fractions in the same four bins; and
- candidate-weighted fractions processed in lists in those bins.

These distributions connect the real workload to the earlier native result:
B4 table construction first amortized at 256 candidates and B8 first
amortized at 8,192. Total candidates across many lists must not be presented
as amortization for a table that is rebuilt per list.

## Complete distance definition

S is defined on the first 128 PCA residual coordinates. This is all of SIFT1M
but only part of GIST1M. The remaining GIST coordinates may not be silently
dropped.

For database vector `x` assigned to centroid `c`, let:

```text
r = PCA(x) - PCA(c)
u = PCA(q) - PCA(c)
head = coordinates [0,128)
tail = coordinates [128,d)
```

For S and every 128-coordinate mechanism control, the reconstructed residual
is:

```text
r_hat = [decode(code), 0_tail]
score(q,x) = ||u_head - decode(code)||^2 + ||u_tail||^2
```

Thus the tail is reconstructed as the coarse centroid and contributes one
cell-constant term. It is computed once for each query/list and included in
both reference and optimized scores. This rule is fixed before queries and
is not a learned correction.

Full-dimensional PQ/OPQ controls encode every residual coordinate and use
their normal full-dimensional asymmetric distance. They are intentionally
stronger controls; restricting all competitors to S's 128-coordinate view
would not establish a deployable Pareto improvement.

No arm may rerank with raw database vectors. IVF-Flat is reported separately
as an uncompressed quality ceiling and is not a storage-matched competitor.

## Frozen S construction

S retains the already tested model:

```text
64 adjacent non-overlapping pairs in PCA coordinates [0,128)
center[g,k] = mean[g] + transform[g] * shared_shape[k]
B4: K=16,  4-bit label per pair, 32 code bytes/vector
B8: K=256, 8-bit label per pair, 64 code bytes/vector
```

For each dataset and coarse quantizer:

1. assign learn rows with the shared coarse centroids and compute their
   residuals;
2. rank official learn-row IDs by SHA-256 of
   `dataset_id || nlist || row_id || 20260724`, with fields encoded as
   fixed-width little-endian integers after the ASCII dataset ID;
3. take the first 8,192 rows;
4. run the existing deterministic whitening, pooled shared-shape fit,
   full-affine group updates, eight starts, and S100 rule; and
5. encode all database residuals once, before query access.

S20 remains a historical sensitivity result and is not a query arm. Query
results cannot extend the iteration cap, choose another seed, reorder pairs,
change the 128-coordinate view, add per-cell models, or select B4 versus B8.

The compact model is 1,664 bytes at B4 and 3,584 bytes at B8 before container
headers. Expanded `64*K` centers are a correctness reference only and are not
persistent candidate state.

## Forced arms

All compressed arms store database IDs in the same width and use the same
inverted lists. Common IDs and coarse-IVF state are reported separately from
method-specific state.

### Mechanism controls on the same 128-coordinate view

- `D128`: the existing dyadic scalar-product control with independently
  learned one-dimensional representatives and 64 groups. Each group contains
  `K=16` or `K=256` Cartesian-product centers addressed by one 4- or 8-bit
  label.
  Use its cheapest correct separable table construction and scan; do not force
  it through a slower generic full-word table.
- `V128`: 64 independently trained unrestricted 2D codebooks, with 4- or
  8-bit labels.
- `PQ128`: conventional 8-bit-subquantizer residual PQ:
  - 32 bytes: `M=32, nbits=8`;
  - 64 bytes: `M=64, nbits=8`.
- `OPQ128`: the matching OPQ rotation and PQ configuration for each budget.
  Transform time and transform bytes are included.

At 64 bytes `V128` and unrotated `PQ128` have the same model family. They
remain separate implementation/optimizer checks, not independent scientific
evidence. A discrepancy must first be treated as training or implementation
evidence.

D128 and V128 use the identical 8,192 learn-row IDs selected for S. D128 is
the source at design base `76fb83a`: H=1024 equal-rank histograms, binary64
scalar curves through K=256, dyadic pair allocation, and the existing
deterministic tie rules. V128 uses `niter=300`, `nredo=1`,
`min_points_per_centroid=1`, `spherical=false`, and no faster subsampling for
each start. Its eight starts are:

```text
start 0: D128 Cartesian-product centers
starts 1..7 seed:
  20260722 + word_bits * 10000 + group_id * 8 + start
```

Select the smallest fitting SSE; exact ties select the smaller start number.
This replaces no outcome-dependent choice and deliberately gives V a strong
product initialization.

### Residual OPQ semantics

Every OPQ arm is a residual transform after the common coarse assignment, not
an `IndexPreTransform` allowed to change IVF lists. For orthogonal matrix `R`
and selected centroid `c`, its lookup path is exactly:

```text
u = PCA(q) - PCA(c)
r = PCA(x) - PCA(c)
score = ADC(R * u, code_of(R * r))
```

OPQ128 learns and applies `R` only on `u_head/r_head`, then adds the same GIST
tail constant as the other 128-coordinate arms. Full OPQ learns and applies R
to the full residual. Transforming a centroid or query outside this residual
formula may be used as algebraic optimization only if a direct fixture proves
identical scores and the common coarse lists remain unchanged.

Train OPQ on residuals from the full official learn split assigned by the
shared centroids. Pin Faiss `OPQMatrix` to its source defaults:

```text
random rotation seed=1234
niter=50
niter_pq_0=40
niter_pq=4
max_train_points=65536
```

The rotated PQ then uses the same M/nbits and PQ training rules as its
unrotated arm. OPQ application time, matrix bytes, rotated workspace
initialization, and per-list table construction are all counted.

### Full-dimensional deployable matched-byte controls

Run every valid predeclared configuration and compare S with their best
measured envelope:

| Budget | SIFT1M and GIST1M |
| ---: | --- |
| 32 B | `IVFPQ(M=32,nbits=8)`, `IVFPQ(M=64,nbits=4)`, their residual-OPQ forms, and `IndexIVFPQFastScan(M=64,nbits=4)` |
| 64 B | `IVFPQ(M=64,nbits=8)` and its OPQ form |

For every `IndexIVFPQFastScan` arm freeze:

```text
by_residual=true
bbs=32
implem=0          # pinned Faiss auto dispatch
qbs=0
qbs2=0
parallel_mode=0
skip=0
use_precomputed_table=0
```

The resolved implementation is recorded for the one-query and batch paths;
auto dispatch may choose a different pinned implementation solely because
batch size differs, not because of observed Recall or timing. SIFT1M
additionally runs regular and FastScan `M=128,nbits=4` plus the matching
residual-OPQ regular form at 64 bytes because 128 divides its dimension.
GIST1M does not run that configuration because 128 does not divide 960.

Use the full official learn split for Faiss PQ/OPQ training, with pinned Faiss
defaults except:

```text
ClusteringParameters.seed=1234
niter=25
nredo=1
```

Giving a standard baseline more training rows than S is deliberate: it avoids
manufacturing a weak baseline. Training rows and work are reported.

### Quality and contextual controls

- `IVFFlat`: identical preassigned lists and exact full-vector distances.
- production `SAQ` and `CAQ` at source revision `76fb83a`;
- pinned Faiss `IndexIVFRaBitQ` and `IndexIVFRaBitQFastScan`.

SAQ/CAQ/RaBitQ-family points are reported with their actual method-specific
per-vector factors and their complete serialized index sizes. Their finite
pre-query configuration pools are:

```text
SIFT1M SAQ and CAQ avg_bits:
  1.5, 2.0, 2.5, 3.5, 4.0, 4.5

GIST1M SAQ and CAQ avg_bits:
  0.2, 4/15, 1/3, 0.4, 8/15, 2/3

For every SAQ/CAQ point:
  random_rotation=true
  caq_adj_rd_lmt=6
  caq_adj_eps=1e-8
  use_compact_layout=true
  searcher_safe_block_min_mode=2
  dist_type=L2
  SAQ enable_segmentation=true
  CAQ enable_segmentation=false

Faiss RaBitQ:
  IndexIVFRaBitQ nb_bits in {1,2,3,4}
  IndexIVFRaBitQFastScan nb_bits in {1,2,3,4}
  FastScan bbs=32, implem=0, qbs=0, qbs2=0,
           parallel_mode=0, skip=0
```

Build and serialize every configuration in this finite pool before query
access. For each dataset, `nlist`, method family, and target budget, retain for
query timing the configuration with the largest complete method-specific
bytes/vector not exceeding the target and the one with the smallest
bytes/vector exceeding it.
Here method-specific bytes/vector is exactly

```text
(complete serialized bytes
 - byte-identical shared coarse-IVF bytes
 - byte-identical database-ID bytes) / 1,000,000
```

and therefore includes factors, padding, and model state. Exact byte ties
select the lower `avg_bits` or `nb_bits`, then the non-FastScan class. If one
side does not exist, record that side as unavailable; never add another rate.
Preserve a text table of the complete pool, exact class/config, serialized
bytes, and selected flags before query access.

This is a serialization-only selection rule, not a query-quality choice.

They are contextual Pareto competitors, not declared byte-matched when their
actual layouts differ. An S claim must disclose if any contextual point
dominates it in the three-dimensional Recall/QPS/bytes space.

## Storage and construction accounting

For each complete new index report:

- exact packed code bytes per database vector;
- method-specific per-vector factors, norms, offsets, padding, and alignment;
- persistent codebook, transform, shared-shape, affine, and estimator bytes;
- common coarse centroids and database-ID bytes;
- complete serialized index bytes and bytes per database vector;
- build/fit/encode CPU and wall time;
- peak RSS and largest method-owned transient allocation; and
- load time.

The primary matched-budget arms must have exactly 32 or 64 packed code bytes
and no unreported per-vector method metadata. Global model state is not
amortized away: it remains in complete serialized bytes.

No existing serialized index or old QPS result is evidence. Build every index
from the frozen implementation and verify save/load round-trip equality before
query access.

## Correctness requirements before timing

Before any natural query is opened:

- pack/decode round trips pass for every arm and budget;
- optimized scores match a binary64 direct reconstruction reference on tiny
  synthetic IVF fixtures;
- S compact and expanded tables satisfy the existing tolerance;
- the GIST tail constant is present and has a nonzero adversarial fixture;
- preassigned list IDs and their order are byte-identical across arms;
- every database ID appears exactly once in the same shared list;
- serialized load reproduces codes, model parameters, list sizes, and scores;
- top-100 selection has deterministic tie-breaking by `(distance,id)`;
- no timed path reads raw database vectors for a compressed arm;
- all method-specific bytes have complete ownership accounting; and
- an optimized native path exists for S; a scalar debug loop is labeled
  `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE` and cannot enter the timed comparison.

The existing SAQ index loader must receive a tiny multi-cell save/load test
before it is used: its current nested cluster-loading loop is not assumed
correct merely because an old index exists.

## Recall and frontier rules

Return exactly 100 IDs. Recall@100 is:

```text
|returned_100 intersect exact_ground_truth_100| / 100
```

Average over every official query. Ground-truth evaluation, result hashing,
and CSV/TSV output occur outside timed regions.

For each dataset, `nlist`, budget, and arm, retain all nine `nprobe` points
and remove only points dominated by another point of the same arm. Point A
dominates B exactly when:

```text
Recall_A >= Recall_B
QPS_A >= QPS_B
and at least one inequality is strict
```

There is no interpolation.

For a candidate point `s` with Recall `R_s` and throughput `Q_s`:

- its matched-Recall baseline is the highest-QPS point on the union of all
  full-dimensional matched-byte PQ/OPQ/FastScan frontiers whose Recall is no
  more than `0.001` below `R_s`, i.e. Recall at least `R_s - 0.001`;
- its matched-throughput baseline is the highest-Recall point on that union
  whose QPS is no more than 5% below `Q_s`, i.e. QPS at least `0.95 * Q_s`.

If either comparison set is empty, that comparison is unavailable; do not
extrapolate.

S establishes a material systems improvement only if one common budget
(`32 B` or `64 B`) satisfies the same one of these two alternatives on both
datasets and both `nlist` values:

1. **speed route:** against the eligible baseline whose Recall is no more than
   `0.001` below S, S has at least 10% higher median end-to-end QPS, and its
   single-query p95 latency is no more than 5% worse; or
2. **quality route:** against the eligible baseline whose QPS is no more than
   5% below S, S improves Recall@100 by at least `0.002` absolute.

Additionally:

- S's complete serialized index must be no larger than the matched baseline;
- S build CPU time must be no more than twice that baseline;
- all correctness checks must pass;
- no contextual SAQ/CAQ/RaBitQ-family point may strictly dominate the claimed
  point in Recall, QPS, and complete bytes; and
- the candidate-distribution report must show where table costs are paid.

Passing only one dataset, one `nlist`, a scan-only timer, or a mechanism
control is not a positive terminal result. A negative result is retained
without changing the frozen choices.

## Latency and throughput measurement

Hardware is the current single-socket Intel Core i9-10920X host. Record kernel,
microcode, compiler, linked libraries, governor, turbo state, NUMA topology,
and available memory before measurement. Use one compiled Release binary and
the same top-k implementation for all custom arms.

Common settings:

```text
metric=L2
topk=100
warmup=one complete untimed pass
measured repetitions=7
index loading/fixed-capacity allocation/output/Recall=outside timed regions
```

Arm IDs are the exact uppercase identifiers used in output:

```text
both budgets:
  S128 D128 V128 IVFFLAT

32 bytes:
  PQ128_M32X8 OPQ128_M32X8
  PQFULL_M32X8 OPQFULL_M32X8
  PQFULL_M64X4 OPQFULL_M64X4 PQFSFULL_M64X4

64 bytes:
  PQ128_M64X8 OPQ128_M64X8
  PQFULL_M64X8 OPQFULL_M64X8

SIFT1M 64-byte additions:
  PQFULL_M128X4 OPQFULL_M128X4 PQFSFULL_M128X4

contextual selected slots:
  SAQ_LO_<budget> SAQ_HI_<budget>
  CAQ_LO_<budget> CAQ_HI_<budget>
  RABITQ_LO_<budget> RABITQ_HI_<budget>
```

An unavailable contextual side is omitted and recorded before query access.
For each dataset/`nlist`/budget, sort all available IDs by ASCII. In measured
repetition `r in [0,6]`, start at index `r mod arm_count` and visit the
remaining arms cyclically. The same order applies to latency and throughput.
Warmup uses the unrotated ASCII order and is not measured.

Custom S/D/V/PQ128 arms use the same Faiss float max-heap top-100 primitive
and deterministic final ordering by `(distance,id)`. Regular IVFPQ/OPQ and
FastScan use their pinned native Faiss top-k handlers; forcing FastScan
through the custom heap would disable the implementation being compared.
Their complete top-k cost stays inside the timer, they use no raw-vector
rerank, and exact result/tie fixtures verify semantic parity. Report the
resolved FastScan handler/implementation with every row.

Only reusable fixed-capacity buffers sized from the frozen maximum dimensions,
`nprobe`, and top-k may be allocated outside timing. Capacity growth,
query/batch-dependent allocation, buffer initialization or clearing, query
transform, table writing, heap/reservoir initialization, and result
finalization are timed. Report reserved and touched workspace bytes per arm.

Single-query latency:

```text
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
OMP_DYNAMIC=FALSE
CPU affinity=CPU 0
```

Time the complete operation for each query separately:

```text
PCA/query transform
coarse assignment
per-list table construction and tail term
packed scan
top-100 maintenance
```

For each query use the median of its seven measured latencies, then report
the distribution's mean, p50, p95, p99, max, and MAD. Also report phase
timings for transform, coarse assignment, table construction, scan, and
top-k; phase instrumentation must be disabled for the primary total or its
overhead measured separately.

Throughput:

```text
OMP_NUM_THREADS=12
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
OMP_DYNAMIC=FALSE
CPU affinity=physical CPUs 0-11
```

Submit the full official query set as one batch. Compute QPS only as:

```text
number_of_queries / batch_wall_seconds
```

Report median, min, max, and MAD over seven measured batches. Do not derive
QPS by summing per-query timers or multiplying by thread count.

Search output must be identical across repetitions for a fixed arm and
operating point. A performance run with unstable Recall or IDs is invalid.

## Resource boundary

On 2026-07-24, after the original 48-hour construction checkpoint stopped,
the user first raised the aggregate CPU ceiling to 64 CPU-hours and then,
after the complete synthetic projection, raised it to 256 CPU-hours. On
2026-07-25 the user raised the wall-time ceiling from 24 to 120 hours.
All datasets, arms, cells, repetitions, metrics, data boundaries, memory
limits, and other resource limits below remain unchanged.

Implementation, index construction, and query evaluation are sequential:

- at most 16 GiB peak RSS;
- at most 256 aggregate CPU-hours;
- at most 120 hours wall time;
- one index arm resident at a time, except for shared immutable inputs; and
- no GPU result enters the CPU claim.

Stop when the cap is reached and report missing cells. Do not drop a baseline,
dataset, `nlist`, `nprobe`, or repetition to complete a partial positive
claim.

Before opening any query, finish all query-free index builds and run a
synthetic-query timing projection through every native arm. Use the real
database list-size distribution, every frozen `nprobe`, 64 deterministic
finite synthetic query vectors per dataset, one warmup, and three measured
passes in both the one-thread latency mode and 12-thread batch mode. For each
mode project the registered CPU work as:

```text
1.25 * measured_CPU_per_synthetic_query
     * official_query_count
     * 7 repetitions
```

Sum both mode projections, then add actual training, encoding, serialization,
load-test, and remaining baseline-build CPU already consumed. If the sum over
all required arms and cells exceeds 256 CPU-hours, do not read query/ground
truth and do not delete a cell to fit the cap. Report the evaluation as
infeasible under the frozen resource boundary; changing the budget or scope
would be a new user decision.

## Query-access boundary and next action

Writing this design does not itself make the current prototype query-ready.
Natural query and ground-truth files remain unread until all of the following
query-free work is complete:

1. the full-index S encoder and per-cell score above exist;
2. the shared `search_preassigned` schedule is implemented;
3. direct-score, tail, packing, top-k, byte-accounting, and save/load tests
   pass;
4. every forced baseline builds from the pinned revisions or is explicitly
   reported unavailable before outcomes;
5. exact executable commands, compiler flags, affinities, and output
   locations are fixed; and
6. a diff review confirms that the implementation did not change this design.

These are correctness prerequisites, not opportunities to add a new metric or
method. Compilation failures and ordinary debugging do not reopen the design.

The concrete next action is query-free: implement a tiny synthetic
multi-cell full-index fixture that exercises S's head-plus-tail score and the
same preassigned lists against direct binary64 reconstruction. Only after that
path, serialization, and baseline byte accounting pass should the standard
query and ground-truth objects be opened exactly once for identity
verification and the frozen evaluation.

## Claim boundary

A pass would establish a measured CPU IVF Pareto point for an independent
shared-shape full-word VQ representation. It would not establish:

- unchanged-SAQ compatibility;
- a new general theory of vector quantization;
- superiority on graph indexes, GPUs, IP/cosine search, updates, or datasets
  outside SIFT1M/GIST1M;
- novelty of PQ, affine transforms, packed lookup, or codebook sharing; or
- a paper contribution without a separate closest-work novelty argument and
  independent reproduction.

A failure would close this fixed 128-coordinate S representation under the
declared CPU IVF workload. It would not prove that all learned block
quantizers or all shared-codebook designs are ineffective.

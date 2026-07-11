# CO-0 v2 Final Base-Only Preregistration

Date: 2026-07-11
Stage: V2-B0
Status: frozen before encoder implementation or execution

## Scientific Question

For frozen SAQ residual segments, how much of the exact centered-grid
alignment opportunity remains after production six-round CAQ, and is that
regret systematically amplified by SAQ's short/high-bit leading segments in a
way that affects the unchanged full-code estimator?

The null is that six-round CAQ is already close enough, that ordinary extra
rounds remove the gap, that any residual gap is generic across segment shapes,
or that it does not improve the unchanged estimator. This is a falsification
screen for a limitation, not an evaluation of a proposed method.

## Frozen Inputs And Read Boundary

The machine-readable input contract is
`docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`. Complete structural
inventories and rotation hashes are under
`docs/saq_caq_co0_v2_b0_artifacts_2026_07_11/`.

Before encoding, V2-B1 must hash and shape-check every base, centroid,
variance, and cluster-id file against the input contract. A mismatch stops the
study. Queries, ground truth, and serialized historical indexes are not input
artifacts and must not be opened.

V2-B0 parsed only the two one-column cluster-id files. Float-artifact hashes
were imported from pre-existing provenance and remain expected hashes until
the B1 preflight reads and verifies their bytes.

## Data Regimes

```text
gist_sample50k_k512:
  N=50,000, D=960, K=512, sample n=50,000
  native plan = 0:64@11 | 64:256@6 | 256:576@4 |
                576:832@2 | 832:960@0

cifar60k_k512:
  N=60,000, D=512, K=512, sample n=50,000
  native plan = 0:64@9 | 64:256@5 | 256:384@3 | 384:512@0
```

No other dataset, `K`, nominal budget, bit width, dimension boundary, or plan
may be introduced. The GIST sample contains every base vector. CIFAR uses the
frozen population-proportional largest-remainder inventory. Both inventories
cover all 512 cells.

Pair inventories contain 24,842 GIST pairs and 24,884 CIFAR pairs. Pairing is
within cell, disjoint, and uses no vector outside the main sample.

## Residual And Rotation Construction

For selected vector `v` in cell `c`, compute the binary32 PCA-space residual

```math
r_v = x_v - \mu_c
```

using the same Eigen float32 subtraction for every arm. For native or
same-segment-uniform view `s`, take its frozen contiguous slice and compute

```math
o_{v,s,z}=r_v[s]P_{s,z},
```

where `z in {0,1,2}` is the logical seed. For the whole-view control, use
`r_v[0:832]` or `r_v[0:384]` and its independently generated whole-view
matrix.

Logical seeds map to distinct C RNG seeds as follows:

```text
logical 0 -> srand(1)
logical 1 -> srand(2)
logical 2 -> srand(3)
```

The 27 expected row-major float32 matrix hashes are frozen in the inventory
manifest. B1 regenerates matrices using the committed C++ generator and stops
before encoding if any hash differs. Default and same-segment uniform views
reuse identical segment matrices. The whole view uses its separately reset
stream.

## Frozen Views

For every selected vector and seed, evaluate exactly:

1. every positive native segment at its native total bit width;
2. every positive native segment at uniform total `B=4`;
3. the concatenated positive-dimensional view at uniform total `B=4`.

The zero-bit tail is not encoded. GIST therefore has nine views per
vector/seed: four native, four same-segment uniform, and one whole view. CIFAR
has seven.

The native GIST `D=320,B=4` view and its uniform counterpart must be
byte-identical for every arm and seed. This is a predeclared duplicate
correctness check, not an additional hypothesis.

## Encoder Arms

Each view uses exactly four arms with the same rotated binary32 input.

### `lvq_init`

Use current `CAQEncoder` scalar initialization with adjustment disabled.
Operationally this is the source path obtained with
`caq_adj_rd_lmt=0`; zero means no adjustment in the current implementation.

### `caq_r6`

Use current production coordinate order and arithmetic with:

```text
caq_adj_rd_lmt = 6
caq_adj_eps    = 1e-8
```

These inherited values are not tuned.

### `caq_local_fixed_point`

Start from the identical scalar initialization and execute the exact source
coordinate order, `++` then `--` acceptance comparisons, correction pass, and
fixed `re_eps=1e-8*initial_oa_l2sqr`. Continue until one complete round accepts
zero moves. There is no fitted round limit. Record accepted moves and
completed rounds. Failure to terminate or a non-finite state stops the study;
do not add a rescue cap.

### `corrected_exact`

Use the independently validated exact-integer complete-event oracle from
`saqlib/quantization/caq/exact_event_oracle.hpp`. Map its `uint32_t` centered
code to the same normalized CAQ grid. This is a measurement labeler, not the
pinned official Extended-RaBitQ executable and not a proposed encoder.

## Code And Factor Semantics

For total bits `B`, `L=2^(B-1)`, and centered code `c`, the normalized decoded
coordinate is

```math
q_i=(c_i+1/2-L)/L.
```

Record the complete code. Canonical code hashes are SHA-256 over dimension
order `uint32_le` words. Persistent code shards use exactly `B` bits per
coordinate, dimension order, least-significant bit first within each code and
then within each byte. A shard records byte offset and bit length for every
encoding row. No code may be discarded after retaining only its hash.

Persist `fac_rescale` and `fac_error` after the same float32 narrowing used by
`QuantBaseCode`. For every arm, independently recompute exact centered-grid
dot/norm state and derive:

```math
J = \frac{\langle o,q\rangle^2}{\lVert o\rVert^2\lVert q\rVert^2},
\qquad
E = 1/J-1,
```

and the mathematically source-compatible error factor

```math
f = \lVert o\rVert^2(1.9)\sqrt{E/(D-1)}.
```

Exact integer/rational code geometry selects `J`; no floating epsilon selects
the winning code. Float conversion occurs only for reporting and persisted
factor emulation.

A segment whose exact residual norm is zero is recorded for every arm and
excluded symmetrically from angular and ratio statistics. A non-finite input,
code, factor, or metric is a run failure, not an exclusion. The count and ids
of every zero segment are reported. If a registered stratum has zero aggregate
initialization-to-exact opportunity, it cannot pass.

## Per-Encoding Output

Sharded gzip CSV records one row per dataset/vector/cell/seed/view/arm. Shards
are ordered by dataset, logical seed, view, arm, cell, and vector id; each
shard filename contains those first four identifiers. Rows within a shard are
in `(cell_id, vector_id)` order. The schema is:

```text
dataset_id, vector_id, cell_id
logical_seed, c_rng_seed
view_id, view_kind, segment_index, offset, dimension, total_bits
arm, zero_segment
code_shard, code_bit_offset, code_bit_length, code_sha256
cosine, cosine_squared_J, angular_excess_E
fac_rescale_float32, fac_error_float32, independent_error_factor
code_equal_corrected_exact
accepted_moves, completed_rounds
first_pass_events, replay_events, heap_comparisons
objective_comparisons, max_integer_bits
wall_time_ns, cpu_time_ns, peak_transient_bytes
```

`peak_transient_bytes` is a deterministic owned-buffer high-water count. At
every instrumented phase, sum the byte capacities of per-call Eigen/vector
buffers, event-heap storage, code/result buffers, and allocated `cpp_int` limb
capacity, then retain the maximum. Exclude allocator headers, shared input,
centroids, and rotation matrices. The B1 implementation must expose and unit
test every included term before base execution. Process `ru_maxrss` and total
serialized bytes are additionally recorded per shard. Timing and memory are
overhead evidence, not gate metrics.

## Unchanged-Estimator Pair Output

For each frozen within-cell pair, the first residual supplies the stored code
and the second supplies the query-side residual under the same view and
rotation. Pack the code/factors and call the current full-code
`CaqSingleEstimator<DistType::IP>` path; do not substitute a new dot-product
formula for the primary result. Because both residuals are already multiplied
by the frozen matrix, instantiate estimator data with `rotator=null` and pass
the rotated query directly; applying the matrix twice is a run failure.

Record one row per pair/seed/view/arm:

```text
dataset_id, cell_id, pair_rank
stored_vector_id, query_vector_id
logical_seed, view_id, arm
stored_norm, query_norm, zero_norm_pair
true_inner_product, estimated_inner_product
signed_ip_error, absolute_ip_error, normalized_absolute_ip_error
true_l2_squared, estimated_l2_squared, absolute_l2_squared_error
bound_radius, bound_covered
```

The exact reference is a float64 accumulation over the common rotated
binary32 vectors. Define

```math
\text{normalized error}=
\frac{|\widehat{\langle o,q\rangle}-\langle o,q\rangle|}
     {\lVert o\rVert\lVert q\rVert}.
```

If either norm is zero, record and exclude the pair for all arms. No epsilon
is added. The diagnostic bound radius is

```math
\text{fac_error}_{float32}\frac{\lVert q\rVert}{\lVert o\rVert}.
```

Bound coverage is descriptive and cannot pass the gate.

## Primary Opportunity Estimand

For an arm `a` and registered view `S`, define the ratio of sums

```math
R_a(S)=
\frac{\sum_v( f_{a,v}-f_{exact,v})}
     {\sum_v( f_{init,v}-f_{exact,v})}.
```

For the pooled statistic, average each factor difference over the three seeds
within vector before forming cell sums. Bootstrap replicates resample cells
and pool every retained vector from each sampled cell occurrence; thus cell
dependence is preserved while vector counts remain in the ratio of sums.

Each amplification hypothesis uses the intersection of vectors with nonzero
norm in both the leading and named control view, and applies that identical
vector set to both ratios. Materiality uses the valid leading set. This keeps
the registered segment contrasts same-vector even if a segment is exactly
zero.

Report per-vector unscaled gap distributions and seed-specific ratios. A zero
main denominator means `NO-GO`. In a bootstrap replicate with zero
denominator, assign ratio zero conservatively and report the count.

## Statistical Procedure

Use NumPy `Generator(PCG64(20260711))` to generate one shared matrix of 10,000
cluster-bootstrap replicates. Each replicate draws 512 cell ids with
replacement. The same draws are reused for every arm, control, and dataset.

Report:

- the point estimate;
- the percentile 2.5% and 97.5% interval;
- the one-sided 5% lower confidence bound;
- seed-specific point estimates; and
- one-sided bootstrap p-values
  `(1 + count(T_bootstrap <= T_null))/(10000 + 1)`.

Apply Holm step-down correction at `alpha=0.05` across exactly the 24 tests in
`docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json`. No descriptive subgroup,
sensitivity row, uniform lower-segment control, or additional metric may enter
the family after results are observed.

The estimator statistic averages the three seeds within pair, forms
`normalized_abs_error_r6-normalized_abs_error_exact`, and pools pair sums over
resampled cells. Positive values favor exact encoding. The unscaled absolute
error difference must have the same positive direction but is not an
additional Holm hypothesis.

## Frozen Decision Rule

The limitation gate passes only if every condition below holds.

### Material finite-round regret

For the leading high-bit segment in both datasets:

```text
the 95% lower confidence bound of R_r6 is >= 0.10; and
the 95% lower confidence bound of R_local is >= 0.10.
```

All four materiality nulls must be rejected after Holm correction. Report
`0.05` and `0.20` sensitivity rows, but neither can replace the registered
`0.10` decision. Requiring local fixed point to pass prevents ordinary extra
rounds from being presented as a new mechanism.

### SAQ-specific segment amplification

Within each dataset, leading-segment `R_r6` and `R_local` must exceed:

1. the same-vector, same-dimension uniform-`B=4` control;
2. every lower-bit positive native segment; and
3. the whole-positive-view uniform-`B=4` control.

All 18 paired differences must have Holm-adjusted one-sided evidence above
zero.

### Estimator materiality

In both datasets, replacing `caq_r6` with `corrected_exact` on the leading
segment must reduce normalized absolute pair inner-product error with
Holm-adjusted one-sided evidence above zero. Unscaled error must improve in the
same direction. Error-factor improvement alone is a `NO-GO`.

### Seed consistency

For each logical seed `0`, `1`, and `2`, both leading-segment ratios must be at
least `0.10` as point estimates, and estimator-error difference must have the
same improving sign. A pooled result driven by one rotation is a `NO-GO`.

## Stop Outcomes

Return `NO-GO` and preserve evidence if any of the following occurs:

- corrected-oracle proof or synthetic parity no longer passes;
- exact-label CPU exceeds the frozen 24 CPU-hour ceiling;
- either dataset fails the `0.10` materiality floor;
- local fixed-point adjustment removes the material gap;
- the leading segment lacks any frozen amplification control;
- any rotation seed reverses the registered conclusion;
- the unchanged estimator proxy does not improve in both datasets;
- the result requires another dataset, bit width, segment, seed, threshold,
  exclusion, or pairing rule; or
- the only plausible repair is broad exact E-RaBitQ fallback.

A `CONDITIONAL PASS` establishes only an SAQ-specific limitation. It may
authorize a new primary-source/theory review of low-cost certificates or
deterministic repairs. It is not a method contribution.

## Resource And Execution Boundary

Run one CPU thread in deterministic dataset/seed/view order. The exact-oracle
CPU accumulator has a hard 24-hour ceiling across both datasets. Stop before
starting another exact label if the next call could cross the remaining
budget under the V2-A2 per-cell bound; never finish by dropping a cell or
sample.

Record exact-oracle CPU separately from rotation, residual preparation, CAQ
arms, I/O, statistics, and total wall time. Record output shard sizes and the
approximately 1.15 GB nominal packed-code payload implied by the frozen views,
arms, seeds, and sample size; report actual bytes without using storage as a
gate.

## Planned Commands

B0 preparation and deterministic replay:

```bash
cmake -S validation/caq_corrected_oracle \
  -B /tmp/saq-v2-oracle-release-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-v2-oracle-release-build --parallel

/tmp/saq-v2-oracle-release-build/caq_co0_v2_b0_rotation_inventory \
  /tmp/saq-caq-co0-v2-b0-rotations

python script/prepare_caq_co0_v2_b0_inventories.py \
  --input-spec docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json \
  --rotation-dir /tmp/saq-caq-co0-v2-b0-rotations \
  --output-dir docs/saq_caq_co0_v2_b0_artifacts_2026_07_11
```

The future B1 implementation must expose only frozen input/preregistration
arguments, one output directory, and `--threads=1`. It must have no query,
ground-truth, plan, bit, seed, threshold, or sample-size override. Before its
first base read, the B1 implementation requires synthetic unit tests and a
separate code-review commit.

## Stage Boundary

Writing and committing this preregistration does not authorize B1. No encoder
arm has been run and no CO-0 objective or estimator result has been inspected.
The next step after B0 is a separate decision on synthetic-only B1 runner
implementation and review; real base execution requires explicit
authorization after that review.

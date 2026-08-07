# Non-adjacent pairing closest-baseline result

Date: 2026-08-03
Branch and base: `saq-mixed-radix-query` at `552fa7b` before this change

## Decision

The empirical-SSE minimum-weight matching (`D_MWM`, formerly `D_FLEX`) does
not pass the frozen closest-baseline gate.  It is therefore closed as a
standalone pairing contribution, and this result does not justify a DP-OPQ or
full-matrix expansion.

Against our Eigenvalue Allocation specialization (`D_EA`), `D_MWM` changes
Recall@100 by only
`+0.000253/+0.000349` on SIFT1M and `+0.000320/-0.000160` on GIST1M at
`nprobe=64/1024`.  The GIST signs are inconsistent, and no dataset reaches
the predeclared `+0.002` improvement.  Query throughput remains within the
allowed 5% regression, so performance does not explain the failed Recall
gate.

This is negative evidence for the tested pair-selection objective, not for
all optimized decompositions.  It also does not reopen arbitrary mixed-radix
cardinalities: every arm here uses the same dyadic allocator and consumer.

## Frozen comparison

The experiment uses SIFT1M and GIST1M, `nlist=4096`, 64-byte/B8 codes,
`nprobe={64,1024}`, batch12, one warmup, and three measured repetitions.
The PCA residuals, first 8,192 SHA-ordered fitting rows, IVF assignments,
query order, selected lists, top-100 ground truth, scalar fitter, dyadic
allocator, table consumer, and four-candidate scan are identical across arms.

The six arms are:

- `D_MWM`: exact minimum-weight perfect matching under fitted pair SSE;
- `D_EA`: our two-coordinate specialization of the Eigenvalue Allocation rule
  in Ge et al.'s parametric OPQ method (OPQ-P), using 64 buckets of capacity
  two;
- `D_RANDOM_0..2`: three preregistered Fisher--Yates permutations, paired
  consecutively;
- `D_ADJ`: fixed adjacent pairs.

Section 3.2.4, "Eigenvalue Allocation," of the OPQ paper specifies descending
eigenvalue assignment to the non-full bucket with the smallest current
eigenvalue product.  It describes allocation, buckets, and subspaces; it does
not name a "grouping rule."  The paper also does not fully specify how an
empty bucket's product is represented.  This experiment therefore records our
deterministic, scale-invariant two-coordinate specialization: fill every
bucket once before assigning second coordinates, then use bucket-index tie
breaking.  The implementation uses each coordinate's one-level scalar SSE as
the eigenvalue/variance proxy; for the fixed fitting sample this differs from
variance only by a common scale factor.  It is neither full OPQ nor byte-level
parity with an official OPQ implementation.  Primary source: [Ge et al.,
Section 3.2.4, CVPR
2013](https://openaccess.thecvf.com/content_cvpr_2013/papers/Ge_Optimized_Product_Quantization_2013_CVPR_paper.pdf).

## Base-only fit evidence

Total fitted SSE is lower for `D_MWM` than `D_EA`, but the advantage is small:

| Dataset | D_MWM | D_EA | MWM reduction |
| --- | ---: | ---: | ---: |
| SIFT1M | 2,539,910.2439 | 2,540,919.9665 | 0.0397% |
| GIST1M | 61.7073 | 62.6917 | 1.5703% |

This confirms that the exact graph solver optimizes its fitted objective.  The
query results below show that the remaining objective gap does not produce the
required nearest-neighbour benefit.

The two methods are not accidentally producing the same pair table: only
2/64 SIFT pairs and 1/64 GIST pairs are identical.  Their near-equal Recall is
therefore evidence that very different coordinate pairings are equivalent at
the tested decision boundary, not a duplicate-arm artifact.

## Recall and throughput

QPS is the median of three measured repetitions.  Recall, candidate count,
and output hash were identical across all three repetitions in each cell.

| Dataset | Arm | Recall@100, p64 | QPS, p64 | Recall@100, p1024 | QPS, p1024 |
| --- | --- | ---: | ---: | ---: | ---: |
| SIFT1M | D_MWM | 0.901501 | 7,025.0 | 0.941286 | 518.8 |
| SIFT1M | D_EA | 0.901248 | 6,930.9 | 0.940937 | 518.5 |
| SIFT1M | D_RANDOM_0 | 0.890948 | 7,020.2 | 0.928281 | 521.5 |
| SIFT1M | D_RANDOM_1 | 0.889765 | 7,039.7 | 0.926773 | 520.3 |
| SIFT1M | D_RANDOM_2 | 0.887872 | 7,036.1 | 0.924317 | 521.5 |
| SIFT1M | D_ADJ | 0.881135 | 6,930.4 | 0.916571 | 518.9 |
| GIST1M | D_MWM | 0.619150 | 3,826.1 | 0.668400 | 418.3 |
| GIST1M | D_EA | 0.618830 | 3,783.2 | 0.668560 | 416.8 |
| GIST1M | D_RANDOM_0 | 0.614540 | 3,855.5 | 0.663360 | 416.6 |
| GIST1M | D_RANDOM_1 | 0.613580 | 3,837.7 | 0.662500 | 418.3 |
| GIST1M | D_RANDOM_2 | 0.612020 | 3,854.0 | 0.661480 | 413.6 |
| GIST1M | D_ADJ | 0.609280 | 3,853.9 | 0.658050 | 412.5 |

The controls are informative.  Non-adjacent random pairing already improves
over adjacency, while the two-coordinate Eigenvalue Allocation specialization
captures nearly all of MWM's remaining gain.  Thus the earlier `D_FLEX`
improvement mainly demonstrated that adjacent grouping was weak; it did not
isolate a material benefit from the empirical pair-SSE graph or its exact
matching solver.

## Correctness, reproducibility, and cost

- Focused EA/random pairing tests pass, including ordering, ties, pairing
  validity, deterministic reproduction, and seed separation.
- Existing matched-sidecar, direct/table distance, index round-trip, and
  precomputed-table tests pass.
- `D_MWM` indexes and sidecars are byte-identical to the accepted `D_FLEX`
  pilot artifacts on both datasets.  SIFT Recall, candidate counts, and output
  hashes also reproduce the accepted pilot exactly.
- All six indexes for a dataset have the same 74,261,172-byte index and
  512-byte sidecar sizes.
- The 72 measured rows cover all 6 arms, 2 datasets, 2 probes, and 3
  repetitions.  No cell has a hash, Recall, or candidate-count disagreement.
- Recorded builds use 355.737 CPU-seconds.  Adding one unrecorded warmup per
  query cell conservatively gives about 6,931.46 total CPU-seconds (1.93
  CPU-hours), below the 4 CPU-hour limit.  Peak RSS is 1,300,619,264 bytes
  (about 1.21 GiB), below 16 GiB.
- Pair fitting, pairing construction, and logging remain outside timed query
  regions.  The timed hot path is unchanged table construction and B8 scan.

Commands used:

```bash
cmake --build /tmp/saq-mixed-radix-query-build -j 12 \
  --target mixed_radix_pair_matching_test mixed_radix_build_matched_arms \
  structured_2d_run_synthetic_timing mixed_radix_index_test
/tmp/saq-mixed-radix-query-build/mixed_radix_pair_matching_test
/tmp/saq-mixed-radix-query-build/mixed_radix_index_test
# The focused builder was run once per dataset in closest-baseline-v1 mode.
# The natural-closest runner was run once for every dataset/arm combination;
# each invocation performed both frozen probes, one warmup, and three records.
```

Generated indexes and measurements remain under
`/tmp/mixed-radix-query/closest-baseline-v1/` and are not repository content.

## Claim boundary and next decision

The result supports three bounded statements:

1. non-adjacent pairing is materially better than fixed adjacency here;
2. the tested two-coordinate specialization of OPQ-P's Eigenvalue Allocation
   explains almost all of the accepted MWM pilot improvement under this
   scalar consumer;
3. the extra fitted-SSE optimality of MWM does not pass through to a material,
   stable Recall improvement under the unchanged consumer.

It does not establish parity with every OPQ implementation, invalidate
DP-OPQ/full OPQ, or prove that all data-dependent pairing objectives fail.  A
new objective would need a distinct mechanism and hypothesis; scaling this
MWM objective is not justified by the current evidence.

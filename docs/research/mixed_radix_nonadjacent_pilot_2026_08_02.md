# Non-adjacent mixed-radix Recall/QPS pilot

Date: 2026-08-02

## Result

The frozen pilot passes its preregistered feasibility rule.  Maximum-weight
non-adjacent coordinate pairing produces a consistent natural-query
Recall@100 gain on SIFT1M and GIST1M without a material matched-consumer QPS
regression.

The result does **not** show a useful arbitrary-radix effect.  A-flex and
D-on-A use identical coordinate pairs and differ only in whether their two
scalar cardinalities may be arbitrary integers or must be powers of two.
Their Recall differences are at most `0.00057` in magnitude and have mixed
signs.  Almost all observed benefit is therefore attributable to choosing
better coordinate pairs, not to mixed-radix cardinalities.

## Frozen comparison

- SIFT1M and GIST1M, `nlist=4096`, 64-byte/B8 codes;
- `nprobe={4,64,1024}`;
- 12 query threads, one warmup and three measured repetitions;
- A-flex: arbitrary-radix allocation on the A-optimized perfect matching;
- D-on-A: dyadic allocation on the identical A matching;
- D-flex: dyadic allocation on an independently D-optimized matching;
- D-adj: the accepted adjacent-pair dyadic anchor;
- unchanged PCA, IVF assignments, selected lists, top-100 ground truth,
  candidate scan, GIST tail distance, and per-vector 64-byte payload.

The pairings came unchanged from
`/tmp/mixed-radix-query/matched-offline-v1/run7/pairs.tsv`.  Scalar centers
were refit on the same first 8,192 SHA-ordered learn residuals used to select
the pairings.  Query outcomes were not used for fitting or arm selection.

## Recall and QPS

Values below are Recall@100 and median batch QPS across the three measured
passes.  D-adj was rerun in the same focused runner as a control.

| Dataset | Arm | nprobe 4 | nprobe 64 | nprobe 1024 |
| --- | --- | ---: | ---: | ---: |
| SIFT1M | D-adj | .454470 / 44,910 | .881135 / 6,972 | .916571 / 514.9 |
| SIFT1M | A-flex | .455693 / 46,468 | .901456 / 6,956 | .941511 / 514.3 |
| SIFT1M | D-on-A | .455699 / 48,237 | .901498 / 6,944 | .941383 / 515.0 |
| SIFT1M | D-flex | .455686 / 44,610 | .901501 / 6,955 | .941286 / 515.0 |
| GIST1M | D-adj | .251350 / 9,485 | .609280 / 3,984 | .658050 / 413.0 |
| GIST1M | A-flex | .253040 / 9,343 | .617920 / 3,959 | .667660 / 412.9 |
| GIST1M | D-on-A | .253000 / 9,270 | .618410 / 3,922 | .668230 / 414.0 |
| GIST1M | D-flex | .253090 / 9,484 | .619150 / 3,922 | .668400 / 413.6 |

Relative to D-adj, the non-adjacent arms gain about `+0.0203` Recall at
SIFT/nprobe 64 and `+0.0247`--`+0.0249` at SIFT/nprobe 1024.  They gain
`+0.0086`--`+0.0099` at GIST/nprobe 64 and `+0.0096`--`+0.0104` at
GIST/nprobe 1024.  The largest QPS regression is 2.28%, below the frozen 5%
limit.  At nprobe 4, Recall gains are smaller (`+0.0012`--`+0.0017`).

The rerun D-adj anchor reproduced every accepted Recall value exactly.  Its
QPS differed from the older matrix by -8.13% to +0.95%; the outlier is the
SIFT nprobe-4 session, while the other five points are within 1.31%.  Primary
QPS deltas above therefore use the same-session focused D-adj run rather than
mix timing sessions.

## Attribution

Pairing effect is material.  Compared with accepted fixed-adjacent A128,
A-flex gains `+0.019885` and `+0.024895` Recall on SIFT at nprobe 64 and 1024,
and `+0.009660` and `+0.010590` on GIST.

Arbitrary-radix effect is not material.  A-flex minus D-on-A Recall is:

| Dataset | nprobe 4 | nprobe 64 | nprobe 1024 |
| --- | ---: | ---: | ---: |
| SIFT1M | -0.000006 | -0.000042 | +0.000128 |
| GIST1M | +0.000040 | -0.000490 | -0.000570 |

Changing the matching objective from A-flex's allocation loss to D-flex's
dyadic loss also has only a small effect once either non-adjacent matching is
used.  This supports a decomposition/pairing mechanism, not an
arbitrary-radix mechanism.

## Existing controls and frontier interpretation

Against the accepted 64-byte PQ128 control, the matched arms reach higher
Recall at nprobe 64 and 1024 on both datasets at comparable QPS.  Against the
accepted OPQ128 control, A-flex is higher by `+0.00511` and `+0.00770` Recall
on SIFT at nprobe 64 and 1024 while running about 2.9x and 3.3x as many queries
per second.  On GIST, D-flex is within `0.00075` and `0.00045` Recall of OPQ at
those points while running about 2.1x and 2.8x as many queries per second.

This moves the discrete accepted pilot frontier and justifies a fuller fair
comparison.  It is not yet a SOTA claim: only one `nlist`, one byte budget,
three probes, and two datasets were measured, and the closest primary work on
pairing/decomposition has not yet been used to establish novelty.

## Correctness, reproduction, and resources

Focused tests cover non-adjacent encoding, sidecar round-trip and rejection,
stored-label validity, save/load, direct-distance versus complete-table
lookup, and a multi-list query.  The sidecar is a permutation of `0..127`
stored as 64 `(dim1,dim2,radix,used_states)` records.  It is 512 bytes per
index and adds no per-vector state.  Coordinate indirection occurs only while
building the 64 complete lookup tables; the four-candidate B8 scan is
unchanged.

Each index is 74,261,172 bytes.  Shared scalar-curve fitting took about
161--163 CPU seconds per dataset; each arm then took about 4.0--4.3 CPU
seconds to encode 1M vectors and about 0.023 seconds to serialize.  Peak build
RSS was 1,300,631,552 bytes.  Including warmups and the GIST D-flex
reproduction, recorded/estimated work was about 1.37 CPU-hours and 0.21
wall-hours, well below the 24/12-hour and 16-GiB limits.  One initial SIFT
launch disappeared without output; its empty directory was checked and the
same command was rerun in a persistent PTY.  It produced no scientific data.

A complete GIST D-flex rerun reproduced all three Recall values, candidate
counts, and output hashes.  Median wall-time changes were `+0.59%`, `+0.73%`,
and `-0.04%` at nprobe 4, 64, and 1024.

Build and query commands were:

```bash
/tmp/saq-mixed-radix-query-build/mixed_radix_build_matched_arms \
  <sift|gist> /tmp/structured-2d-admission \
  /tmp/mixed-radix-query/matched-offline-v1/run7/pairs.tsv \
  /tmp/mixed-radix-query/matched-pilot-v1/pool/<dataset>/nlist_4096 frozen

/tmp/saq-mixed-radix-query-build/structured_2d_run_synthetic_timing \
  natural-pilot <sift|gist> 4096 64 <arm> batch12 \
  /tmp/structured-2d-admission <pool-root> <query.fvecs> \
  <groundtruth.ivecs> /tmp/structured-2d-natural/schedule <output.tsv>
```

Generated indexes and raw measurements remain under
`/tmp/mixed-radix-query/matched-pilot-v1/`.  Representative SHA-256 values
are `f79fdca...54a70` for the SIFT A-flex index,
`f145845b...f84f` for the GIST A-flex index, and
`db6f53d2...9c125` for the first GIST D-flex result TSV.  The final rebuilt
query runner is `7399a7ff...c1c07`; its source is identical to the measured
runner source.  The matched-arm builder is `b7cf147c...e59e2`.

## Decision boundary

Verified: base-only maximum-weight non-adjacent pairing materially improves
the frozen two-coordinate consumer's natural Recall/QPS behavior on both
pilot datasets.

Not verified: that arbitrary integer radices contribute materially, that the
method is novel over existing pairing/decomposition work, or that the result
survives a complete multi-budget/multi-nlist fair comparison.  The most
defensible next question is therefore whether the pairing mechanism itself
is novel and remains competitive under a frozen full evaluation, not whether
to tune mixed-radix cardinalities after seeing these outcomes.

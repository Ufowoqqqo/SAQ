# Active Task: matched mixed-radix Recall/QPS pilot

## State and question

- Branch: `saq-mixed-radix-query`
- Base commit: `8ee35a2` (`Evaluate maximum-weight mixed-radix pairing`)
- Mode: `IMPLEMENT`, `EXPERIMENT`, then `REVIEW`

Test whether the frozen base-only maximum-weight coordinate matching transmits
the 3.98%--4.75% held-out reconstruction advantage of arbitrary radix into a
material natural-query Recall improvement without a material QPS regression.
No query margin or query-trained choice is allowed.

Primary comparison: A-flex versus independently optimized D-flex.  D-on-A is
the mechanism control using A-flex's identical coordinate pairs with dyadic
radices.  A result is promising only if both datasets show a consistent
positive trend and at least `+0.002` Recall@100 at one frozen point, with no
more than 5% matched-consumer QPS regression.  Report negative results
unchanged.

## Frozen scope

- datasets: SIFT1M and GIST1M;
- `nlist=4096` only;
- 64-byte/B8 codes only;
- `nprobe={4,64,1024}`, the first, middle, and last values of the existing
  frozen nine-point grid;
- new arms: A-flex, D-on-A, D-flex;
- one D-adj anchor; existing accepted fixed-adjacent A/D and PQ/OPQ results are
  comparison evidence, not fitting input;
- batch12, one warmup and three measured repetitions per new arm/probe;
- exact existing query order, selected IVF lists, and top-100 ground truth.

The A-flex and D-flex coordinate pairs are exactly those in the byte-identical
accepted offline output
`/tmp/mixed-radix-query/matched-offline-v1/run7/pairs.tsv`.  D-on-A reuses
A-flex pairs.  Refit scalar centers on the identical first 8,192 SHA-ordered
learn residuals; do not rerun or change the matching from query outcomes.

## Reads and writes

Allowed reads:

- repository source, Git metadata, current research documents;
- the named accepted offline pair table;
- existing PCA learn/base vectors, learn/base assignments, coarse indexes,
  and query schedules under `/tmp/structured-2d-admission/` and
  `/tmp/structured-2d-natural/schedule/` for the two named cells;
- existing SIFT1M/GIST1M query and ground-truth files used by the completed
  matrix;
- existing accepted fixed-adjacent/PQ/OPQ summaries for comparison.

Allowed writes:

- focused source/tests under `research/mixed_radix_matching/` and minimal
  integration changes under `research/mixed_radix_query/` and
  `research/structured_2d/`;
- `TASK.md`, the local mixed-radix `AGENTS.md`, focused result documentation,
  and the research decision log;
- generated indexes, sidecars, TSVs, and logs only under
  `/tmp/mixed-radix-query/matched-pilot-v1/`.

Do not modify production `saqlib/`, PCA, IVF assignments, candidate schedules,
ground truth, query vectors, fixed matching pairs, code budget, top-k, or
baselines.  Do not read another dataset or sweep another nprobe, matching,
radix objective, threshold, or grouping after outcomes.

## Implementation and correctness

Store one coordinate-pair sidecar per index.  It must be a permutation of
`0..127`, contain exactly 64 pairs, and add no per-vector metadata.  The index
still stores one B8 label per pair.  Candidate generation and the GIST tail
term remain unchanged.

Tests must cover sidecar round-trip and rejection, non-adjacent residual
encoding, direct reconstructed-distance versus complete-table lookup, stored
label validity, save/load, multi-list query behavior, and identical consumer
dispatch across A-flex, D-on-A, and D-flex.  Compile and pass focused tests
before reading query outcomes.

The scientific hot path is per-list construction of 64 complete 256-entry
tables plus the existing four-candidate B8 scan.  Pair indirection belongs in
table construction, not the per-candidate scan.  Logging, hashes, and output
serialization stay outside timed regions.

## Budget and done criteria

Limits: 24 aggregate CPU-hours, 12 wall-hours, 16 GiB peak RSS, one build
process, and at most 12 query threads.  Stop before exceeding a limit.

Done means:

- all correctness tests pass;
- both datasets and all three new arms build with valid sidecars/codes;
- all 18 arm/probe cells have one warmup and three stable measured batch12
  repetitions, with stable Recall/output hash/candidate count;
- the D-adj anchor agrees with accepted Recall and comparable QPS;
- construction, index/sidecar bytes, peak memory, commands, hashes, failures,
  Recall/QPS, and claim boundaries are reported;
- the result states separately the pairing effect, arbitrary-radix effect,
  and remaining novelty uncertainty.

Current blocker: none.  The frozen pilot is complete and its result is in
`docs/research/mixed_radix_nonadjacent_pilot_2026_08_02.md`.  One concrete
next action is a closest-primary-work review of the coordinate-pairing
mechanism before expanding the evaluation or making a novelty claim.

# Active Task: maximum-weight matched mixed radix

## State and question

- Branch: `saq-mixed-radix-query`
- Base evidence: fixed-adjacent A/D natural-query result at `ae42b64`
- Mode: `IMPLEMENT`, then base-only `EXPERIMENT` and `REVIEW`

Test whether fixed adjacent coordinate pairs hid complementary scalar
cardinality demands.  The proposed method chooses one global perfect matching
of the 128 coordinates by minimizing its own base-only allocation SSE.  The
arbitrary and power-of-two arms each receive an independently optimized
matching; the power-of-two allocation on the arbitrary arm's matching is an
additional mechanism-isolation control.
It does not use query margins or benchmark-query outcomes for fitting.

The falsifiable hypothesis is that maximum-weight matching can recover
pairings whose arbitrary-radix distortion advantage is materially larger than
that of fixed adjacent pairs.  A synthetic fixture must first recover a known
cross-pairing and show a strict arbitrary-versus-dyadic advantage.

## Authorized natural offline diagnostic

Analyze exactly four B8/64-byte cells: SIFT1M and GIST1M, each with
`nlist=1024` and `4096`.  B4 is excluded because all four completed natural
cells selected `4x4` everywhere and A was byte-equivalent to D.

Allowed:

- read repository source, committed research notes, and Git metadata;
- add focused matching code and tests under `research/mixed_radix_matching/`;
- make minimal CMake integration changes;
- compile and run deterministic synthetic/tiny tests;
- read the existing PCA learn vectors, learn assignments, and coarse centroids
  under `/tmp/structured-2d-admission/{sift,gist_head128}/` for those four
  cells;
- write only diagnostic TSV/log output under
  `/tmp/mixed-radix-query/matched-offline-v1/`;
- update this task file.

Use the exact existing SHA-256 row ordering.  The first 8,192 ordered learn
rows are fit data and the next disjoint 8,192 are held-out offline evaluation.
Do not read base vectors, benchmark queries, ground truth, Recall outputs, or
unrelated experiment outputs.  Do not modify production `saqlib/`, introduce
query-aware/margin objectives, build indexes, run a query matrix, or claim
Recall/QPS improvement.

The completed collision diagnostic's named artifacts remain readable only as
prior evidence; they must not be used to fit the new matching.

## Implementation and verification

Implement:

1. a deterministic maximum-weight perfect matching interface for a complete
   even-order graph;
2. edge weights equal to negative same-pair allocation SSE, separately for
   arbitrary and dyadic allocation; same-pair `D-A` gain is reporting-only and
   must not be optimized because that could deliberately weaken D;
3. exact exhaustive comparison on small graphs;
4. a synthetic cardinality fixture where the optimal cross-pairing is known;
5. reporting that separates pairing gain from radix gain.

For every cell report fit and held-out SSE for fixed-adjacent A/D, A-flex,
D-on-A, A-on-D, and D-flex; matching overlap; selected radix shapes; runtime;
and memory.  Run all four cells twice and require byte-identical scientific
outputs.  Use the existing CMake project under `research/structured_2d`.
Allowed commands are repository inspection, CMake configure/build, focused
tests, the diagnostic executable, deterministic comparison, `git diff
--check`, and Git status/diff inspection.  Limit this stage to 2 aggregate
CPU-hours, 2 wall-hours, one process and one computational thread, and 8 GiB
peak RSS.

Done means the matching result agrees with the tiny exhaustive optimum,
recovers the synthetic cross-pairing, all four natural cells complete twice
with identical outputs, tests pass, and the result separates pairing gain from
radix gain.  This is base-only reconstruction evidence, not Recall or
performance evidence.  The next action is to implement and run this frozen
diagnostic.

Outcome: PASS as base-only reconstruction evidence.  Across all four cells,
A-flex reduced held-out SSE by 3.98%--4.75% relative to independently matched
D-flex and by 4.16%--4.99% relative to D-on-A.  Two accepted executions were
byte-identical.  See
`docs/research/mixed_radix_max_weight_matching_offline_2026_08_01.md`.

Current blocker: none for this completed diagnostic.  A direct Recall test
would be a subsequent implementation/experiment task and must preserve the
now-frozen A-flex, D-on-A, and D-flex matching definitions.

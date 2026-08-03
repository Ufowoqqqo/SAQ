# Research decision log

This log records when evidence changed the active scientific decision. It is
evidence for retrospective review, not current authorization; `TASK.md` and
the current user prompt define active work.

## 2026-07-29: return from structured 2D to the original idea

- Finding: the completed structured-2D matrix tested a learned non-Cartesian
  pair codebook, not the original mixed-radix intuition.
- Decision: stop treating structured 2D as progress on mixed radix and return
  to fixed adjacent scalar pairs with flexible integer cardinalities.
- Reason: the presenter and audience had reasonably understood the active
  direction to be mixed radix; the mismatch was not documented clearly.

## 2026-07-29: base-only evidence is insufficient for Recall

- Finding: original two-coordinate B4 showed no reconstruction benefit; B8
  showed only about +0.09% on GIST and negative change on CIFAR. A later
  four-coordinate GIST check and flexible-grouping relaxation showed larger
  reconstruction opportunity, but none was a logical Recall bound.
- Decision: do not close the original idea solely from reconstruction or pair
  proxies. Measure the actual query consumer.

## 2026-07-30: freeze the direct mixed-radix query experiment

- User decision: implement the frozen consumer and measure real Recall/QPS
  rather than add another cheap proxy.
- Frozen contrast: A128 arbitrary integer radices versus D128_FULL
  power-of-two radices, with fixed adjacent pairs, identical fit rows, bytes,
  candidates, and complete word-table consumer. PQ128 and OPQ128 are strong
  controls.
- Source: `docs/research/mixed_radix_query_design_2026_07_30.md`.

## 2026-07-30: two infrastructure defects found before the matrix

- Build binding: an initially rebuilt runner linked Atlas rather than the
  OpenBLAS used by the frozen query schedule. The saved/recomputed coarse-list
  parity check rejected query 1. The runner was relinked to the original
  OpenBLAS; the check was not relaxed and the schedule was not regenerated.
- Residual-IVFPQ scoring: loaded Faiss indexes automatically enabled
  precomputed residual tables, but the inherited custom scanner passed zero
  instead of the encoded-head coarse distance to `set_list`. This made farther
  lists spuriously cheap and caused Recall to fall with increasing `nprobe`.
  The scanner now computes and passes the head coarse distance; GIST tail cost
  remains separate. A regression test exercises precomputed-table mode.

These are artifact correctness findings, not mixed-radix contributions.

## 2026-07-30: native consumer ready; complete matrix started

- Correctness: B4/B8 packing, valid-address, save/load, full-table/direct
  distance, and precomputed-table tests pass.
- Performance: a four-candidate unrolled B4/B8 scanner reduced the
  SIFT/1024/32B representative full pass from about 360 to about 154 seconds
  with identical Recall. At high `nprobe`, A/D remain roughly twice as slow as
  matched 32-byte PQ128 because they perform 64 four-bit lookups per candidate
  versus PQ128's 32 eight-bit lookups.
- Query evidence so far: SIFT/1024/32B A128 and D128_FULL are byte-for-byte
  ranking-equivalent and saturate near Recall@100 0.69065; matched PQ128
  saturates near 0.73585 and is faster. This is one cell, not the terminal
  cross-dataset conclusion.
- Execution: the full 32-cell A/D/PQ/OPQ natural-query matrix began under
  `/tmp/mixed-radix-query/matrix-v1/`, with one warmup and seven repetitions
  in single-thread and 12-core modes.

## 2026-07-31: invalidate one overlapped timing pass and resume atomically

- Finding: after the first detached runner disappeared, a replacement was
  started while an older `SIFT/1024/32B/OPQ/single/r=2` child was still
  writing. Five duplicate probe rows exposed the overlap; the surviving
  pass's `nprobe=256` wall time was therefore not valid performance evidence.
- Decision: preserve the original files under
  `/tmp/mixed-radix-query/matrix-v1/recovery-backup-20260731/`, mark the
  overlapped ledger row `INVALIDATED_OVERLAP` so its resource cost remains
  counted, and rerun that exact frozen pass without changing the method,
  workload, or thresholds.
- Recovery: the replacement pass completed with a unique nine-probe grid.
  The orchestration runner now stages each pass separately and publishes it
  only after a complete-grid check, so an interrupted child cannot append a
  partial repetition to accepted measurements. It also takes a kernel-held,
  nonblocking exclusive lock on the output directory; a second runner now
  fails before launching a child, and an abnormal exit releases the lock
  automatically. These are execution correctness repairs, not mixed-radix
  evidence.

## 2026-08-01: close the frozen fixed-pair mixed-radix formulation

- Evidence: the complete matrix closed with 512 distinct PASS keys. At 32
  bytes A selected `(4,4)` for every group and was exactly D. At 64 bytes the
  same-nprobe Recall delta ranged from -0.00106 to +0.00054 with mixed signs,
  while A and D had the same consumer and essentially equal QPS.
- Decision: the tested fixed-adjacent two-coordinate mixed-radix formulation
  does not provide a material, stable Recall--QPS frontier improvement and is
  closed as a contribution direction.
- Boundary: this is a negative result for the frozen allocator,
  representation, and consumer. Adaptive grouping, larger groups, or a new
  allocation objective would be a different research question, not an
  unmeasured positive conclusion from this experiment.
- Full result: `docs/research/mixed_radix_query_results_2026_08_01.md`.

## 2026-08-01: synthetic witness confirms the intended mechanism

- Evidence: under frozen `3x5` B4 and `15x17` B8 Cartesian supports, A selected
  those exact shapes, had zero prototype-code collisions, and reached
  Recall@100 1.0. D selected `4x4` and `16x16`, incurred 3 and 15 collisions,
  and reached 0.8 and 0.941176 Recall. Dyadic `4x4` and `16x16` null controls
  produced identical A/D rankings and Recall 1.0.
- Reproduction: two full executions produced byte-identical output with
  SHA-256 `2c0d4c8448594b21e23dc2b9e1bf64062e4806434997d9c8c8bc18545b6a929e`.
- Interpretation: the implementation can transmit a true radix-cardinality
  mismatch into Recall. Natural-data failure is therefore evidence that this
  mismatch was absent or too weak after PCA, not that the consumer was
  mechanically insensitive.
- Boundary: this is an explanatory positive control, not natural-data
  prevalence, PQ/OPQ superiority, or a reversal of the fixed-pair NO-GO.
- Full result:
  `docs/research/mixed_radix_synthetic_witness_result_2026_08_01.md`.

## 2026-08-01: natural near-neighbour collision diagnostic

- Scope: existing 64-byte A128/D128_FULL indexes, all four SIFT/GIST and
  `nlist` cells, and all 36 frozen probe points; no new method or QPS matrix.
- Correctness: rerun A/D Recall matched the accepted matrix at every point
  with zero absolute error; two executions were byte-identical.
- Decisive evidence: among 1,147,139 candidate-present missed-ground-truth
  query--probe events, none shared a complete D code with a returned false
  positive while receiving a different complete A code. The direct synthetic
  full-code collision mechanism is absent at the natural decision boundary.
- Secondary evidence: a permissive one-group label-sharing witness was common
  and exceeded the `+0.002` optimistic line at 34/36 points, but actual A-D
  Recall stayed in `[-0.00106,+0.00054]`. One-group sharing is therefore
  non-specific and cannot be interpreted as realizable Recall headroom.
- Decision: preserve the fixed-adjacent natural NO-GO. Do not use raw collision
  counts as a new objective. Any margin- or direction-aware counterfactual is
  a distinct research question, not an authorized continuation of this run.
- Full result:
  `docs/research/mixed_radix_natural_collision_diagnostic_2026_08_01.md`.

## 2026-08-01: maximum-weight coordinate matching reopens one testable variant

- Question: did fixed adjacent pairs hide complementary scalar cardinality
  demands, without introducing a query-margin objective?
- Method: fit separate A and D maximum-weight perfect matchings on 8,192
  deterministic learn residuals and evaluate on the next disjoint 8,192 rows
  in SIFT1M/GIST1M at `nlist=1024,4096`, B8 only.
- Evidence: A-flex reduced held-out SSE by 20.86%--31.07% versus fixed-adjacent
  A and by 3.98%--4.75% versus independently matched D-flex.  On the identical
  A pairing, arbitrary radices beat dyadic radices by 4.16%--4.99%.  Both
  accepted executions were byte-identical.
- Decision: fixed adjacency is rejected as an adequate test of the broader
  mixed-radix idea.  The matched variant merits one direct Recall experiment
  with A-flex, D-on-A, and independently optimized D-flex.  This is not a
  reversal of the fixed-adjacent NO-GO and is not yet Recall evidence.
- Novelty boundary: most of the total gain comes from coordinate matching,
  which overlaps with known decomposition/bit-allocation work; a future claim
  must isolate the incremental arbitrary-radix effect and full systems cost.
- Full result:
  `docs/research/mixed_radix_max_weight_matching_offline_2026_08_01.md`.

## 2026-08-02: non-adjacent matching passes the natural-query pilot

- Scope: frozen A-flex, D-on-A, and D-flex consumers on SIFT1M/GIST1M at
  `nlist=4096`, 64 bytes, and `nprobe={4,64,1024}`, with the accepted D-adj,
  PQ128, and OPQ128 evidence as controls.
- Evidence: relative to D-adj, non-adjacent arms improve Recall@100 by about
  `+0.0203` at SIFT/nprobe 64 and `+0.0247`--`+0.0249` at nprobe 1024; GIST
  gains are `+0.0086`--`+0.0099` and `+0.0096`--`+0.0104`.  Maximum matched
  QPS regression is 2.28%.  A duplicate GIST D-flex rerun reproduced
  Recall, candidate counts, and output hashes.
- Attribution: A-flex versus D-on-A differs by at most 0.00057 Recall with
  mixed signs.  The positive result is a coordinate-pairing result, not an
  arbitrary-radix result.
- Decision: the non-adjacent pairing mechanism merits novelty review and a
  fuller fair comparison.  Do not claim that mixed-radix cardinalities were
  rescued, and do not tune pairings or radices from these query outcomes.
- Full result:
  `docs/research/mixed_radix_nonadjacent_pilot_2026_08_02.md`.

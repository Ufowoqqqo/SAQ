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

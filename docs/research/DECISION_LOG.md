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

## 2026-08-03: closest work narrows the non-adjacent pairing claim

- Primary-work finding: PQ already establishes the importance of component
  grouping and anticipates automatic grouping; OPQ/CKM optimize the space
  decomposition, and OPQ's parametric solution explicitly reallocates PCA
  coordinates among subspaces.  DP-OPQ further treats stronger combinatorial
  subspace partitioning as its contribution.
- Exact-method finding: no reviewed ANN paper used fitted scalar
  rate--distortion loss on every unordered coordinate pair followed by a
  general-graph perfect matching.  This search absence is not proof of novelty.
- Assessment: the method is a restricted, permutation-only optimized
  decomposition with an exact pair solver.  It has possible narrow algorithmic
  and systems value, but the general grouping mechanism is prior work and the
  pilot does not establish an SAQ-specific or mixed-radix contribution.
- Decision: do not expand the full matrix or make a novelty claim yet.  First
  compare the identical consumer against random pairings, OPQ parametric
  Eigenvalue Allocation restricted to two-coordinate buckets, the applicable
  DP-OPQ partition, full OPQ with decomposed costs, and ordinary 2D PQ on the
  selected pairs.
- Full review:
  `docs/research/nonadjacent_pairing_closest_primary_work_review_2026_08_03.md`.

## 2026-08-03: closest-baseline experiment closes standalone MWM pairing

- Scope: identical dyadic consumers for empirical-SSE matching (`D_MWM`), our
  two-coordinate specialization of OPQ-P Eigenvalue Allocation (`D_EA`),
  three frozen random pairings, and adjacency on SIFT1M/GIST1M at
  `nlist=4096`, 64 bytes, and `nprobe={64,1024}`.
- Evidence: relative to `D_EA`, `D_MWM` changes Recall@100 by only
  `+0.000253/+0.000349` on SIFT and `+0.000320/-0.000160` on GIST.  It never
  reaches the frozen `+0.002` line, and GIST has mixed signs.  QPS remains
  within the 5% allowance, so throughput is not the cause.
- Attribution: random non-adjacent pairing beats adjacency, while Eigenvalue
  Allocation captures nearly all of MWM's improvement.  The earlier positive
  pilot primarily rejected adjacency; it did not show a material benefit from
  the empirical pair-SSE graph or exact matching solver.
- Decision: close MWM as a standalone direction and do not expand this result
  to DP-OPQ or a full matrix.  This is not a negative result for all optimized
  decompositions and does not reopen arbitrary mixed-radix cardinalities.
- Full result:
  `docs/research/nonadjacent_pairing_closest_baseline_result_2026_08_03.md`.

## 2026-08-03: component-wise base-only oracle diagnostic closes without a localized target

- Scope: frozen GIST sample50k SAQ index, 256 deterministic base probes,
  4,096 disjoint pool rows, exact-nearest 64 candidates, and stored production,
  least-squares rescale, single exact-segment, and exact-all arms.
- Correctness: stored/recomputed production parity passed before outcome
  inspection; rescale and norm parity were below `1e-7`, exact segment sums
  were within `8e-15`, and an unchanged reproduction was byte-identical.
- Evidence: production inversion is 0.00598/0.00577 across folds.  Exact
  replacement of 192d@6b or 320d@4b repairs about 43%--44% of inversions, but
  absolute reductions are only 0.00134--0.00153, below the frozen 0.002 rule.
  Least-squares rescale changes are an order of magnitude smaller.
- Decision: `CLOSE_NO_ACTIONABLE_COMPONENT`.  The error is measurable but not
  sufficiently localized to one frozen component.  Do not infer benchmark
  Recall, cross-dataset generality, or authorization for a joint mechanism.
- Full result:
  `docs/research/saq_component_oracle_diagnostic_result_2026_08_03.md`.

## 2026-08-03: joint-component oracle finds one actionable pair

- Scope: the identical base-only population and thresholds, exhaustively
  adding all 10 two-segment, 10 three-segment, and 5 four-segment exact
  substitutions after a fresh stored/recomputed parity pass.
- Evidence: replacing `192d@6b + 320d@4b` reduces inversion rate by
  `0.003353/0.003554` across folds and repairs `71.10%/75.57%` of production
  inversions.  It is the unique passing pair; primary and reproduction output
  files are byte-identical.
- Decision: `PAIR_ACTIONABLE`.  A small joint source of estimator headroom
  exists.  This does not reverse the single-component negative result; it
  refines it by showing that the minimum passing replacement has cardinality
  two.  Exact substitution is not an implementable method or Recall evidence.
- Next boundary: review closest work and the interaction mechanism before
  proposing a query-unaware, matched-storage implementation.  Do not infer
  permission to change the plan or read benchmark queries.
- Full result:
  `docs/research/saq_joint_component_oracle_result_2026_08_03.md`.

## 2026-08-03: closest work and mechanism review blocks direct joint implementation

- Mechanism finding: the accurate SAQ estimator is a sum of independent
  segment terms, while inversion is a nonlinear sign decision.  The pair's
  super-additive inversion repair therefore does not establish cross-segment
  encoder coupling.
- Scale correction: segments 1+2 cover 512/960 dimensions and 2,432 code bits,
  or 53.3% of dimensions and 66.7% of the positive-bit payload.  Exact float
  replacement would use 2,048 rather than 304 bytes/vector for those values.
- Primary-work finding: SAQ/transform coding cover boundary and bit allocation;
  AQ/CQ cover coupled codebooks and their query-cost problem; distance-encoded
  PQ covers storing estimator-relevant radius information; anisotropic VQ and
  White--Singal cover downstream inner-product-aware objectives.
- Decision: `NO_GO_DIRECT_IMPLEMENTATION`.  Do not interpret the oracle as
  authorization for bit reallocation, joint VQ, extra metadata, or a learned
  query/workload loss.
- Narrow open question: statically prove or refute whether the existing SAQ
  code/rescale feasible set admits any base-only, matched-storage,
  no-extra-query-work objective that is genuinely non-separable.  Close if all
  allowed objectives decompose per segment; return to the user before coding
  if one survives.
- Full review:
  `docs/research/saq_joint_component_closest_primary_work_mechanism_review_2026_08_03.md`.

## 2026-08-03: static feasible-objective audit finds workload-only coupling

- Feasible-set finding: after the plan is fixed, segments 1 and 2 have a
  Cartesian-product code/rescale feasible set.  Each encoded residual error is
  orthogonal to its exact segment residual because CAQ rescale enforces
  `<x_s,y_s>=||x_s||^2`.
- Proof result: squared reconstruction, worst-case unseen-direction inner
  product error, and isotropic or block-diagonal average-case MSE all decompose
  exactly into independent segment objectives.
- Counterexample result: empirical base-direction MSE is non-separable when
  the cross-block second moment remains nonzero on both feasible residual
  difference spans.  Pairwise inversion loss is also non-separable; explicit
  CAQ-compatible two-state witnesses are recorded.
- Interpretation: `SEPARABLE_STANDARD_OBJECTIVES` and
  `NONSEPARABLE_WORKLOAD_OBJECTIVES_EXIST`.  Mathematical coupling is possible,
  but it is supplied by a chosen workload/cross-covariance or ranking loss,
  not by the SAQ representation or the exact-replacement oracle itself.
- Decision boundary: do not implement from this result.  The user must choose
  between closing the oracle-only limitation and an explicit pivot to
  base-trained estimator-aware joint code selection.  The latter changes the
  hypothesis and closest baselines.
- Full audit:
  `docs/research/saq_two_segment_feasible_objective_static_audit_2026_08_03.md`.

## 2026-08-04: base-trained joint-objective diagnostic closes local coupling lead

- Scope: fixed GIST sample50k SAQ index, two 128-direction base-only cross-fit
  folds, 32 disjoint targets, and production plus every legal one-coordinate
  `+1/-1` alternative for segments `192d@6b` and `320d@4b`.
- Correctness: existing estimator/rescale/norm/exact parity and new analytical
  production-alternative parity passed before outcomes; Release and ASan tests
  passed; two scientific executions are byte-identical.
- Evidence: relative to independent training on identical alternatives,
  held-out joint MSE changes by only `+0.0805%` in one direction and worsens by
  `1.3644%` in the other.  Joint improves 15/32 and 13/32 targets, failing the
  frozen 5% and 60% rules in both folds.
- Attribution: a post-hoc evaluation oracle improves about 16%, while learned
  joint choices differ from independent choices for 29/32--31/32 targets.
  The local headroom is direction-fold-specific cancellation and does not
  generalize as a stable base-trained rule.
- Decision: `JOINT_LOCAL_NO_GO`.  Do not expand the neighborhood, tune folds or
  thresholds, implement a consumer, or read benchmark queries to rescue this
  lead.  The result closes this direct estimator-aware continuation of the
  segment-1/segment-2 exact-replacement oracle.
- Full result:
  `docs/research/saq_joint_objective_viability_result_2026_08_04.md`.

## 2026-09-02: reframe allocation between coordinate pairs

- Research correction: the intended question was whether resources should be
  allocated *between two-coordinate groups*, for example between `(D1,D2)`
  and `(D3,D4)`, rather than merely redistributed between the two coordinates
  inside each pair.
- Scope: start a separate `saq-correlated-pair-allocation` branch from
  `d305578` and use learn/base data only. Held-out benchmark queries,
  ground truth, Recall, and QPS remained unread.
- Initial evidence: strong coordinate association was stable, but pairing the
  most correlated coordinates failed the frozen 5% allocation-gain rule.
  Fixed adjacent GIST groups did pass, so the source of that signal required
  representation-stage attribution rather than immediate consumer work.
- Full result:
  `docs/research/correlated_pair_allocation_base_diagnostic_2026_09_02.md`.

## 2026-09-03: residual allocation signal is variance-driven, not correlation-driven

- Scope: restore hash-verified official TexMex SIFT1M/GIST1M learn/base
  inputs and compare the same frozen rows at raw, full-PCA, and IVF-residual
  stages for `nlist={1024,4096}`.
- Evidence: adjacent-pair allocation gains survive in both residual views:
  about 20.1%--22.5% on SIFT and 11.7%--13.9% on GIST. Across adjacent
  residual groups, total variance correlates `0.966--0.995` with marginal bit
  return, while absolute Pearson correlation is much weaker.
- Interpretation: the effect is real, but it is ordinary rate--distortion
  heterogeneity between groups. Strong pairwise correlation is not the
  supported mechanism.
- Full result:
  `docs/research/correlated_pair_allocation_stage_attribution_2026_09_03.md`.

## 2026-09-03: closest work blocks a standalone two-dimensional allocation claim

- Primary-work finding: Transform Coding and Optimized Transform Coding cover
  transformed scalar rate--distortion allocation; OPQ covers learned
  transforms/decomposition; BAPQ and DSPQ cover unequal bits between PQ
  subspaces; SAQ already performs dynamic-programming segmentation and bit
  allocation.
- Decision: local two-dimensional PCA, scalar curves, and exact budget DP are
  a direct composition, not a standalone contribution. Exact DP improves the
  artifact but does not introduce a new feasible code family or query model.
- Narrow remaining question: test whether different pair widths retain a
  material opportunity inside an existing factor-sharing SAQ segment, with
  identical payload/factor bytes and the normal segment rotation.
- Full review:
  `docs/research/correlated_pair_allocation_closest_primary_work_review_2026_09_03.md`.

## 2026-09-03: SAQ segment rotation closes post-rotation pair allocation

- Matched-byte plans: SIFT uses `128d@4b` for 72 bytes/vector; GIST uses
  `64@11 | 192@6 | 320@4 | 256@2 | 128@0` for 488 bytes/vector.
- Evidence before rotation: the planner surrogate shows residual allocation
  opportunity of about 28.2%--30.8% on SIFT and 6.3%--6.4% on GIST.
- Decisive evidence after rotation: both the SAQ variance surrogate and
  empirical uniform-lattice curves select the original uniform width inside
  every positive segment. Zero coordinate pairs change width in either fold,
  dataset, or `nlist`; after the six-round CAQ adjustment, the matched-byte
  angular-loss gain is exactly 0%.
- Reproduction: accepted `v3/v4` metadata and full summaries are
  byte-identical. Ten focused tests and the extractor build pass. No query,
  ground-truth, Recall, QPS, or old ANN index result was read.
- Decision: `STOP_CURRENT_POST_ROTATION_PAIR_ALLOCATION`. Do not implement the
  local-PCA/Lloyd or post-rotation mixed-width consumer. Jointly changing the
  transform and allocation would be a new question under strong prior-work
  pressure, not a rescue of this result.
- Archived commit: `08ac7c7` on `saq-correlated-pair-allocation`.
- Full result:
  `docs/research/correlated_pair_allocation_saq_opportunity_decomposition_2026_09_03.md`.

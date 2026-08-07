# Current State: mixed-radix direct line closed

## Repository state

- Branch: `saq-mixed-radix-query`
- Original diagnostic base: `15f8617`
- Terminal scientific result: `JOINT_LOCAL_NO_GO`
- Active research or experiment task: none
- Current blocker: none

This branch records the completed evaluation of the original mixed-radix
direction and its bounded follow-ups.  It does not authorize another rescue
experiment or a new method direction.

## Research question and terminal decision

The final tested question was whether a base-trained, estimator-aware joint
choice of existing segment-1 and segment-2 CAQ codes could improve held-out
estimator error over choosing the two codes independently, without changing
the SAQ plan, stored format, or query consumer.

The frozen requirement was at least 5% held-out MSE reduction in both
cross-fit folds and improvement on at least 60% of targets.  The observed
changes were `+0.0805%` and `-1.3644%`, with only 15/32 and 13/32 targets
improved.  An evaluation-only oracle retained about 16% post-hoc headroom,
showing direction-specific cancellation rather than a stable base-trained
rule.

Decision: close this direct workload-coupling continuation.  Do not enlarge
the code neighbourhood, tune direction folds or thresholds, implement a
production consumer, or inspect benchmark queries to rescue it.

## Claim boundary

- Mixed-radix packing can preserve non-power-of-two Cartesian cardinalities
  and prevent collisions in deliberately structured synthetic data.
- Fixed adjacent mixed-radix did not move a useful natural-data
  Recall--speed frontier on SIFT1M or GIST1M.
- Non-adjacent pairing helped relative to fixed adjacency, but our
  two-coordinate specialization of OPQ-P's Eigenvalue Allocation explained
  nearly all of that gain under the frozen scalar consumer.
- Exact two-segment replacement exposed ranking headroom, but it is an oracle,
  not an encoder.
- The frozen base-only joint objective did not generalize across direction
  folds.
- These results do not prove that every estimator-aware quantizer is
  impossible.  Changing the estimator, representation, metadata, metric, or
  scientific claim would be a new task requiring a new closest-work and cost
  assessment.

## Authoritative current documents

- Terminal joint-objective result:
  `docs/research/saq_joint_objective_viability_result_2026_08_04.md`
- Static feasible-objective audit:
  `docs/research/saq_two_segment_feasible_objective_static_audit_2026_08_03.md`
- Joint-component oracle result:
  `docs/research/saq_joint_component_oracle_result_2026_08_03.md`
- Closest coordinate-grouping baseline result:
  `docs/research/nonadjacent_pairing_closest_baseline_result_2026_08_03.md`
- Updated meeting summary and question card:
  `docs/research/mixed_radix_query_meeting_notes_2026_08_01.md`
- Updated Beamer deck and generated PDF:
  `docs/research/mixed_radix_query_meeting_2026_08_01.tex`
  and `docs/research/mixed_radix_query_meeting_2026_08_01.pdf`
- Chronological record: `docs/research/DECISION_LOG.md`

## Current permissions and next action

No experiment, dataset read, production-code modification, index build, or
new research mechanism is active.  Historical protocols and completed tasks
are evidence only and do not authorize further work.

The meeting materials now include the full chain from the natural and
synthetic mixed-radix results through the closest grouping baseline, exact
component oracle, separability audit, and failed base-only joint cross-fit.

Next action: none on this closed line.  Await an explicit new research
question or a request to maintain the existing documentation.

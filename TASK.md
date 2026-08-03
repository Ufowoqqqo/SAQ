# Active Task: non-adjacent pairing closest-work review

## State

- Branch: `saq-mixed-radix-query`
- Current scientific snapshot: `f08f76c`
- Branch base for this direction: `8ee35a2`
- Mode: `REVIEW`

The frozen non-adjacent pilot is complete.  It found a material pairing effect
but no material arbitrary-radix effect.  The active question is whether the
pairing mechanism is already covered by the closest primary work and what
smallest comparison would discriminate a narrow contribution from a known
decomposition variant.

## Question and hypothesis

Question: does assigning every coordinate pair an empirical scalar
rate--distortion loss and solving a perfect matching constitute a novel ANN
method, or a restricted permutation-only instance of established optimized
product-quantizer decomposition?

Working hypothesis: general learned coordinate grouping is prior work.  The
exact pair-loss reduction may be a narrow unreported specialization, but it is
scientifically useful only if it beats the closest permutation-only OPQ and
DP-OPQ-style controls through the identical low-overhead consumer.

## Relevant evidence

- `research/mixed_radix_matching/`: edge construction and perfect matching;
- `research/mixed_radix_query/`: frozen non-adjacent consumer and tests;
- `docs/research/mixed_radix_max_weight_matching_offline_2026_08_01.md`;
- `docs/research/mixed_radix_nonadjacent_pilot_2026_08_02.md`;
- `docs/research/nonadjacent_pairing_closest_primary_work_review_2026_08_03.md`;
- `docs/research/DECISION_LOG.md`;
- `docs/research/RESEARCH_CHARTER.md`.

Primary sources in the review include PQ, transform coding, OPQ, Cartesian
k-means, DP-OPQ, LOPQ, SAQ, ITLUMM, and PQF.

## Current permissions and boundaries

Allowed now:

- read repository source, current results, and primary publications;
- write the focused closest-work review, `TASK.md`, and decision log;
- run formatting, diff, and repository-status checks.

Not authorized by the current review task:

- changing scientific source code;
- running another fitting, index build, or query experiment;
- reading a new benchmark dataset or new query outcome;
- changing the pairing, loss, bit budget, PCA, IVF assignments, consumer,
  baseline, metric, or query schedule;
- expanding the completed pilot into a full matrix.

The established scientific restrictions remain: grouping is fitted from
base/index data only; held-out queries cannot choose pairings, objectives,
thresholds, or claims; no query-trained policy, per-vector grouping metadata,
or post-outcome rescue sweep is allowed.

## Deliverables and done criteria

Done means the review:

- defines the current method exactly rather than calling it generic matching;
- identifies the closest primary work and what each paper already covers;
- distinguishes general grouping, exact pair optimization, consumer design,
  SAQ-specific contribution, and mixed-radix contribution;
- states whether the method is a direct specialization or composition;
- identifies the closest missing baselines and a falsifiable continuation
  rule;
- records search uncertainty without treating failure to find a paper as proof
  of novelty;
- passes `git diff --check` and leaves scientific code unchanged.

Current blocker: none for the review.  The scientific direction is blocked from
a novelty claim and full-matrix expansion by missing permutation-only primary
baselines.  One concrete next action, after the user chooses to continue, is to
freeze the smallest identical-consumer comparison of random pairing and OPQ
parametric Eigenvalue Allocation pairing.  That would be a new experiment
task, not part of this review.

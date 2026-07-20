# Four Ideas We Tested — and Why We Stopped

Date: 2026-07-13

Revised: 2026-07-18

Status: **current draft; not yet presented**

This deck is for a research-direction discussion. It does not present a new
method. Detailed evidence remains in the source branches and in
`docs/saq_research_direction_registry.md`.

## 1. What I Want To Settle Today

Over the last round, we tested four plausible ways to improve SAQ. Each idea
had a reasonable motivation. None produced a result strong enough to become
the next paper direction.

I would like us to agree on two things:

- which parts are worth keeping as evidence or baselines; and
- what an idea must show before we open another implementation branch.

The useful outcome of this work is a narrower search space, not a hidden win
that needs one more parameter sweep.

---

## 2. A Short Reminder: What SAQ Is Doing

SAQ stores a compressed version of each database vector. That makes it cheaper
to compare a query with many candidates, but the compressed distance is only
an estimate of the true distance.

Three different questions therefore matter:

- **Does the compressed vector resemble the original vector?**
- **Does the estimated distance rank the right candidates near the cutoff?**
- **Does the whole search system remain fast and affordable?**

Several attempts improved the first question without improving the other two.
That distinction explains most of the decisions in this deck.

---

## 3. The Short Answer

- **Attempt 1 — change or shorten the PCA representation:** the encouraging
  result did not survive replication, and the lossy version failed even under
  a deliberately favorable test.
- **Attempt 2 — train scalar codebooks exactly:** useful as a stronger offline
  baseline, but better reconstruction did not reliably improve search. The
  inner exact optimizer is also established prior work.
- **Attempt 3 — judge results by distance quality as well as Recall:** this
  changed one GIST interpretation, but it changed the measurement, not the
  method, and did not replicate as a positive result on DEEP.
- **Attempt 4 — allow non-power-of-two cardinalities:** mathematically
  possible, but the registered exact pipeline exceeded its cost ceiling. A
  later recovery path never produced a valid scientific result and is now
  closed.

My recommendation is to retain the lessons and close all four method lines.

---

## 4. Attempt 1: Can We Represent The Vector Better?

Principal component analysis, or **PCA**, rotates the vector coordinates so
that large sources of variation are easier to identify.

We tested two versions of the same broad idea:

1. keep all dimensions, but learn the rotation from residual vectors rather
   than raw vectors; and
2. keep only 576 of 960 dimensions, then store the norm of the discarded tail
   as a compact summary.

The first version preserves exact geometry before compression. The second
throws information away, so we gave it an unusually favorable early test: an
exact retained part and an exact tail norm, before adding quantization error.

---

## 5. Attempt 1: What The Evidence Says

On GIST, residual PCA reduced distance-estimation error by about **0.60%** at
one accurate stage and **0.33%** with the full code. The fast stage became
worse, and the ranking improvement was not reliable.

We then repeated the frozen comparison on CIFAR. The small GIST effect did not
repeat: only 4 of 10 seeds favored residual PCA at the accurate stage, the
no-rotation control pointed the wrong way, and the fast-stage degradation was
supported by the data.

The reduced-dimension version also failed early. Even with exact retained
coordinates and exact tail norms, its top-100 agreement was **0.99289**, below
native SAQ at **0.99462**. The missing tail inner product—not numerical
precision—caused the remaining error.

So we stopped before building a projected index. This does not prove that PCA
is universally optimal. It says these two replacements did not earn further
systems work.

---

## 6. Attempt 2: Does Exact Training Help Search?

A scalar codebook replaces many numeric values with a small set of
representatives. Standard Lloyd training is iterative and may settle at a
local solution. Exact one-dimensional dynamic programming can find the best
partition for the chosen histogram.

That sounds attractive, but it leaves two separate questions:

- Does exact histogram training reduce reconstruction error?
- If it does, are the nearest-neighbor rankings actually better?

The first question is about fitting compressed values. The second is the one
the search system ultimately cares about.

---

## 7. Attempt 2: A Better Fit Was Not A Reliable Search Win

There were genuine positive cases. On the audio dataset, one setting reduced
mean squared reconstruction error by about **15.5%** and raised Recall at 100
from **0.95275** to **0.95675**.

But the relationship did not hold consistently:

- increasing histogram resolution kept improving reconstruction while Recall
  stopped improving monotonically;
- on DEEP at 4 bits, one setting cut raw reconstruction error by about 20% but
  made Recall at 100 worse; and
- across CIFAR and DEEP, the sign and size of the Recall change depended on
  the bit budget and allocation objective.

There is also a novelty limit. Exact one-dimensional scalar clustering was
already developed by Wu (1991) and later accelerated by Grønlund et al.
(2017); the outer bit allocation is a classical discrete allocation problem.
We keep this implementation as a demanding offline baseline, not as our
method.

---

## 8. Attempt 3: Were We Using The Wrong Quality Measure?

Recall at 100 asks whether we returned the same item identifiers as the exact
top 100. A distance-quality score asks a softer question: how much farther are
the returned items than the exact ones?

This matters near a crowded boundary. Replacing one almost-equally-close item
with another hurts Recall, even when the geometric loss is tiny.

We therefore replayed two frozen SAQ plans and reported both measures. Nothing
about the encoder, index, or search procedure changed.

---

## 9. Attempt 3: One Decision Changed, But No Method Emerged

At the historical GIST reference point, the alternative plan could not reach
the default plan's Recall target. Under the distance-quality measure, however,
a directly measured point was slightly better in quality and **1.078 times**
faster.

That is worth reporting, but it is not uniform dominance:

- **39.6%** of paired GIST queries became worse;
- the positive conclusion did not carry to the two DEEP controls; and
- the distance-quality measure comes from prior work.

The correct conclusion is narrow: one previous rejection was sensitive to the
metric. Future evaluations should show both Recall and geometric quality. We
did not discover a new encoding or search mechanism.

---

## 10. Attempt 4: Can We Use A Fixed Bit Budget More Flexibly?

Consider two factors that must share a word with at most 16 joint states.

- Restricting each factor to a power of two permits **4 by 4**, using all 16
  states.
- Allowing arbitrary positive integers also permits **3 by 5**, using 15
  states.

For uneven data, the second shape can fit better while using the same stored
word. A synthetic example confirms that this possibility is real.

But a larger set of mathematical choices is not yet a database method. We
still have to construct the codebooks at acceptable cost and then show better
search quality at comparable speed and memory.

---

## 11. Attempt 4: The Cost Gate Ended The Study

The registered synthetic implementation passed its correctness checks. The
next question was deliberately mundane: can we afford the exact construction
and evidence pipeline before reading benchmark data?

The projected cost was **24.17025 CPU-hours**, just above the frozen
**24-hour** ceiling. According to the rule fixed in advance, that was a stop.
It is a pipeline-cost result, not evidence that arbitrary cardinalities help
or hurt search.

A later attempt to rebuild a cleaner execution path never reached a valid
scientific outcome. Its final invocation recorded that it started, but did not
produce a trustworthy completion record. We therefore classify the runtime
as unknown and have stopped further artifact recovery.

There is no natural-data result, no search result, and no performance claim
for this direction.

---

## 12. What These Four Attempts Have In Common

Each attempt improved or clarified something local:

- a slightly better distance estimate on one dataset;
- a lower reconstruction objective;
- a more informative evaluation metric; or
- a larger mathematical feasible set.

The local improvement did not survive the next question: replication,
ranking, novelty, or cost.

This is the main lesson I would carry forward. We should test the shortest
link between an attractive local objective and the final search claim before
we build the surrounding machinery.

---

## 13. What Is Still Useful

The work was not wasted. We now have:

- SAQ as a well-understood strong baseline;
- exact scalar training as a tougher offline comparison;
- a reason to report both exact-identifier Recall and distance quality;
- examples showing why reconstruction error alone is a poor search proxy; and
- a practical precedent for stopping expensive construction before touching
  benchmark queries.

These belong in the evaluation design of the next project. They do not need to
be promoted into contributions of their own.

---

## 14. My Recommendation

Close the four method lines and select the next problem from primary work,
before writing more implementation code.

For a new direction, I suggest four entry conditions:

1. the limitation appears on at least two strong, independent baselines;
2. the closest published work leaves a specific gap that is not filled by a
   direct combination of known techniques;
3. one cheap, frozen test can reject the idea early; and
4. construction, memory, and query cost are part of the acceptance rule from
   the beginning.

The decision I need from this meeting is whether we agree with that closure
and selection rule.

# Short Technical Appendix

The main presentation ends here. The remaining slides contain the numbers and
source locations most likely to be needed during discussion. Full protocols,
implementation details, commit chains, and artifact manifests remain in the
registered source documents.

## A1. Terms Used In The Talk

- **SAQ:** the compressed-vector baseline studied in this project.
- **PCA:** principal component analysis, a rotation that orders directions by
  variance.
- **Residual:** the difference between a vector and its assigned cluster
  center.
- **Recall at 100:** the fraction of exact top-100 neighbor identifiers that
  appear in the returned top 100.
- **Distance quality, written as 1/Ratio:** how close the returned distances
  are to the exact top-100 distances; closer to 1 is better.
- **QPS:** queries per second; higher is faster.
- **CPU-hour:** one processor core working for one hour.

---

## A2. Attempt 1 Evidence Boundary

**Full-dimensional replacement**

- GIST residual-PCA change: accurate-stage error `-0.602%`, full-code error
  `-0.331%`, but fast-stage error worsened.
- CIFAR replication: fast `+0.0317%` worse, accurate `+0.00463%` worse, full
  `-0.0235%`; confidence and seed requirements failed.
- Decision: close the one-dataset estimator effect.

Source: `saq-transform-analysis@3d94840`,
`docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md`.

**Lossy 960-to-576 projection**

- Favorable projected oracle top-100 agreement: `0.992890625`.
- Native full-dimensional SAQ: `0.994617188`.
- Decision: fail the early ranking gate; projected index construction was not
  authorized.

Source: `saq-lossy-projection-analysis@051ec6a`,
`docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md`.

---

## A3. Attempt 2 Evidence Boundary

```{=latex}
\small
```

Representative results:

- Audio, 4 bits: reconstruction error per value fell from `280,023` to
  `236,478`; Recall at 100 rose from `0.95275` to `0.95675`.
- DEEP, 4-bit rank-boundary setting: raw reconstruction-error ratio was
  `0.8016`, while Recall at 100 changed by `-0.00215`.

The result supports two limited claims: exact-histogram training is a useful
offline baseline, and lower reconstruction error does not guarantee better
nearest-neighbor ranking.

It does not support a new scalar-quantization method claim. Exact
one-dimensional dynamic programming is prior work (Wu, 1991; Grønlund et al.,
2017), and the outer allocation is a classical discrete rate-allocation
problem. White and Singal (2026) is recent adjacent quantization work that
explicitly treats exact one-dimensional k-means as an older baseline.

Sources: `vectordb@f51b487`,
`reports/scalar_training_exact_hist_audit_2026_06_30/README.md` and
`docs/saq_limitation_transfer_memo_2026_07_02.md`; prior-work boundary at
`saq-caq-one-shell-repair@433e8ea`.

---

## A4. Attempt 3 Evidence Boundary

Frozen GIST reference:

- default plan at 200 probes: distance quality `0.999985301`, QPS `9264.9`;
- alternative plan at 280 probes: distance quality `0.999987869`, QPS
  `9986.9`;
- measured speed ratio: `1.07793`.

Query-paired result: 39.6% worse, 23.0% equal, and 37.4% better. Both DEEP
controls remained below their default distance-quality targets.

Decision: keep this as metric-sensitivity evidence. Do not claim per-query
dominance, cross-dataset replication, or a new mechanism.

Source: `saq-ratio-metric-analysis@146dc16`,
`docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md`.

---

## A5. Attempt 4 Evidence Boundary

The synthetic 16-state example showed a real feasible-set difference:

- arbitrary `(3,5)` cardinalities: zero distortion;
- power-of-two `(4,4)` cardinalities: `0.1` distortion per vector.

This was instrument validation only. No benchmark data or search evaluation
was involved.

The exact construction pipeline then projected
`24.170246892361` CPU-hours against a frozen `24.0` CPU-hour ceiling. The
registered decision was `NO_GO_EXACT_SOLVER_COST`.

The later V2 execution path produced no valid terminal record. The audited
project decision is to stop further artifact recovery; the runtime remains
unknown rather than being reclassified as a scientific failure.

Sources: `saq-arbitrary-cardinality-analysis@f1b464b` and
`saq-arbitrary-cardinality-feasibility-v2@3577edd`.

---

## A6. What We Can And Cannot Say

Supported:

- the tested PCA replacement did not replicate;
- the registered norm-only projection failed its favorable early ranking
  test;
- exact scalar training improved offline fit more reliably than search;
- one GIST comparison changed under a distance-based quality measure; and
- Attempt 4 stopped on registered pipeline cost, followed by project closure
  without a scientific V2 result.

Not supported:

- PCA is universally optimal;
- exact scalar training never helps search;
- distance quality makes the alternative SAQ plan generally better;
- arbitrary cardinalities cannot help on real data; or
- any of these attempts produced a new method or moved the quality-speed
  frontier against the strongest baseline.

---

## A7. Authoritative Source Snapshots

- Attempt 1A: `saq-transform-analysis@3d94840`.
- Attempt 1B: `saq-lossy-projection-analysis@051ec6a`.
- Attempt 2: `vectordb@f51b487`; prior-work boundary at
  `saq-caq-one-shell-repair@433e8ea`.
- Attempt 3: `saq-ratio-metric-analysis@146dc16`.
- Attempt 4 cost stop: `saq-arbitrary-cardinality-analysis@f1b464b`.
- Attempt 4 project closure:
  `saq-arbitrary-cardinality-feasibility-v2@3577edd`.

## A8. Authoritative Evidence Documents

```{=latex}
\small
```

- Attempt 1A: `docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md`.
- Attempt 1B: `docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md`.
- Attempt 2: `reports/scalar_training_exact_hist_audit_2026_06_30/README.md`
  and `docs/saq_limitation_transfer_memo_2026_07_02.md`.
- Attempt 3: `docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md`.
- Attempt 4 cost stop:
  `docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md`.
- Attempt 4 project closure:
  `docs/saq_a4_v2_project_stop_no_further_artifact_recovery_2026_07_18.md`.
- Cross-attempt reporting state: `docs/saq_research_direction_registry.md`.

No further research or execution step is currently authorized for these four
method lines.

## A9. Selected References For Attempt 2

- X. Wu. “Optimal Quantization by Matrix Searching.” *Journal of Algorithms*,
  1991. <https://www.sciencedirect.com/science/article/pii/0196677491900392>
- A. Grønlund, K. G. Larsen, A. Mathiasen, J. S. Nielsen, S. Schneider, and
  M. Song. “Fast Exact k-Means, k-Medians and Bregman Divergence Clustering in
  1D.” 2017. <https://arxiv.org/abs/1701.07204>
- N. White and K. Singal. “Inner Product Aware Quantization: Provably Fast,
  Accurate, and Adaptive Algorithms.” arXiv:2606.00289v1, 2026.
  <https://arxiv.org/abs/2606.00289v1>

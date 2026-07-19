# Meeting Q&A Card — Four Ideas We Tested

For deck snapshot: `saq-meeting-summary@9c21469`.

Print as one page or keep beside the presentation. Answer the first sentence
only; add the second sentence if the audience asks for more.

## Decision In One Sentence

Close the four method lines, keep the baselines and negative evidence, and
require the next direction to pass a cheap cross-baseline limitation test
before substantial implementation.

## Four Attempts In One Line Each

- **Attempt 1:** a small GIST estimator improvement did not replicate on
  CIFAR; the favorable lossy-projection test also ranked worse than native SAQ.
- **Attempt 2:** exact scalar training improved reconstruction more reliably
  than it improved search, and its inner optimizer is prior work.
- **Attempt 3:** distance quality changed one GIST interpretation, but not the
  method; 39.6% of paired queries worsened and DEEP remained negative.
- **Attempt 4:** the mathematical opportunity is real, but the registered exact
  pipeline exceeded its cost ceiling before real-data evaluation; later
  recovery produced no valid scientific result.

## Likely Questions

**All four stopped. What did we actually gain?**

We ruled out four plausible paths under fixed decision rules and retained a
stronger baseline, better evaluation practice, and earlier cost checks. The
result is a smaller and better-justified search space, not four universal
impossibility claims.

**Why not continue Attempt 1 with another dataset, dimension, or rotation?**

The registered positive effect failed its external replication, and the lossy
version failed a deliberately favorable gate before quantization. Changing
datasets, dimensions, or rules now would be a new study, not completion of the
failed one.

**Attempt 2 reduced reconstruction error. Why is that not enough?**

Nearest-neighbor ranking depends on how errors interact with each query near
the ranking boundary, not only on average vector reconstruction. The DEEP
counterexample reduced raw reconstruction error by about 20% while Recall
became worse.

**Attempt 3 was 1.078 times faster. Why is that not the contribution?**

It is one GIST operating point under a prior-work metric, with no new mechanism
and no positive DEEP replication. The aggregate improved, but 39.6% of paired
queries became worse.

**Attempt 4 exceeded 24 hours by only about ten minutes. Why enforce the stop?**

The 24-hour ceiling was fixed before observing the result; relaxing it
afterward would make the gate meaningless. More importantly, 24.17 hours is a
projection for the frozen construction-and-evidence pipeline, not a nearly
complete real-data search result.

**Does Attempt 4 prove arbitrary cardinalities are too expensive or do not
help?**

No. It proves only that the registered exact pipeline missed its affordability
gate. No benchmark-data, Recall, throughput, or end-to-end systems result was
produced.

**Why classify the later Attempt 4 run as unknown instead of failed?**

The run recorded a start but did not produce a trustworthy terminal record.
Calling it a scientific failure would claim evidence that does not exist; the
project decision is simply to stop spending effort on artifact recovery.

**Why not present the bug fixes, exact solvers, or protocol work as the
contribution?**

They validate or govern experiments; they do not improve the database method's
quality-speed frontier. Reviewers would correctly treat them as supporting
work rather than scientific novelty.

**What exactly should happen next?**

Read the closest primary work, identify a limitation visible on at least two
strong independent baselines, and propose one cheap frozen test with an early
stop threshold. Do not implement a new method until that question and its cost
boundary are approved.

## Numbers Worth Remembering

- Attempt 1 GIST estimator error: about `-0.60%`; CIFAR replication failed.
- Lossy projection top-100 agreement: `0.99289` versus native SAQ `0.99462`.
- Attempt 2 audio reconstruction improvement: about `15.5%`; Recall gain was
  small and not stable across settings.
- Attempt 3 measured GIST speed ratio: `1.07793`; paired queries worse: `39.6%`.
- Attempt 4 projected cost: `24.17025` CPU-hours; frozen ceiling: `24.0`.

## Phrases To Avoid

- Do not say “PCA is optimal.” Say “the tested replacements did not justify
  continuation.”
- Do not say “exact training does not help.” Say “its search effect was not
  stable.”
- Do not say “Attempt 4 failed on real data.” Say “the registered pipeline
  stopped before real-data evaluation.”
- Do not say “we have no result.” Say “we have negative selection evidence,
  but no new method claim.”

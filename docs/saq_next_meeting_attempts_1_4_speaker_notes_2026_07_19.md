# Four Ideas We Tested — Presenter Notes

For:
`docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md`

PDF snapshot: expanded successor deck, expected 34 pages after compilation. Its scientific conclusions are
unchanged from `saq-meeting-summary@9c21469`; the later deck update adds only
algorithm explanations, running examples, and the missing Attempt 2 references.

Status: meeting-preparation notes only. These notes do not change any research
decision, reporting state, or authorization.

## How To Use These Notes

- Target **15–17 minutes** for pages 1–23. If time is limited, skip the five
  algorithm-detail pages after giving their one-sentence intuition.
- Pages 24–34 are backup slides. Do not present them in sequence.
- Do not read commit identifiers, filenames, or protocol status names aloud.
- Say “we stopped under the rule fixed in advance,” not “the idea is impossible.”
- When a question becomes technical, answer the decision-level point first.
  Open the appendix only if the audience still wants the exact number.
- The sentences below are written to be spoken. Shorten them naturally rather
  than trying to recite every word.

## Main Presentation

### Page 1 — Title

**Time: 10 seconds**

> Today I want to summarize four ideas we tested after the earlier SAQ work.
> The purpose is not to present a successful new method. It is to explain why
> these four directions stopped and what that tells us about the next project.

Move on immediately.

### Page 2 — Contents

**Time: 5 seconds**

> I will first give the decisions, then explain the evidence behind each one.
> The detailed numbers are in the appendix if we need them.

Do not read the section names.

### Page 3 — Section Divider

**Time: 0 seconds**

Advance without speaking.

### Page 4 — Draft Status

**Time: 15 seconds**

> This is the current discussion draft. The underlying results are already
> frozen in their source branches. What I am asking for today is agreement on
> the research decision, not approval of a new experiment.

### Page 5 — What I Want To Settle Today

**Time: 40 seconds**

> We tested four ideas that each looked reasonable at the beginning. None of
> them produced evidence strong enough for a database-systems contribution.
> I do not think the right response is another parameter sweep. I think the
> useful result is that we can now close these paths and be more selective
> about the next one.
>
> By the end of the discussion, I would like us to agree on what to retain and
> what a new direction must prove before we write more code.

Transition:

> Before the four attempts, let me separate three questions that are easy to
> mix together.

### Page 6 — A Short Reminder: What SAQ Is Doing

**Time: 50 seconds**

> SAQ stores a compressed version of every database vector so that we can
> compare a query with many candidates cheaply. Compression creates three
> different levels of success.
>
> First, does the compressed vector numerically resemble the original vector?
> Second, does the estimated distance put the correct candidates near the top?
> Third, after counting construction, memory, and query work, is the complete
> search system actually better?
>
> Several of our attempts improved the first level. The improvement then
> disappeared at the ranking or systems level. That is the central pattern.

### Page 7 — The Short Answer

**Time: 65 seconds**

> Here is the entire result in one page.
>
> Attempt 1 changed the vector representation. A small positive result on
> GIST did not repeat on CIFAR, and the reduced-dimension version failed even
> under a favorable early test.
>
> Attempt 2 trained scalar codebooks more exactly. It often improved the
> reconstruction objective, but search quality did not improve consistently,
> and the exact inner optimizer is prior work.
>
> Attempt 3 changed how we measured search quality. It corrected one GIST
> interpretation, but it did not introduce a method and the positive result
> did not repeat on DEEP.
>
> Attempt 4 enlarged the mathematical choice set, but the exact construction
> pipeline exceeded its registered cost limit. The later recovery work did
> not produce a valid scientific result.
>
> My recommendation is to close all four as method directions while keeping
> the useful baselines and evaluation lessons.

Transition:

> I will now explain why each stop is stronger than simply saying that one
> experiment looked negative.

### Page 8 — Attempt 1: Can We Represent The Vector Better?

**Time: 45 seconds**

> Principal component analysis, or PCA, is the rotation used before SAQ
> compression. We tested two possibilities.
>
> The first kept all dimensions but learned the rotation from residuals—the
> differences between vectors and their cluster centers. The second kept only
> 576 of 960 dimensions and summarized the discarded part by its norm.
>
> The reduced-dimension version was given a favorable test before we added
> quantization error. If it could not pass that test, building a complete
> projected index would not be justified.

### Page 9 — Attempt 1A Algorithm: Residual PCA

**Time: 55 seconds**

> The first implementation did not remove dimensions or change the search
> algorithm. For every database vector, we subtracted its assigned cluster
> center and learned PCA from those residual vectors. We then applied that one
> full-dimensional rotation consistently to database vectors, centers, and
> queries before running the unchanged SAQ pipeline.
>
> The small picture explains the motivation. Raw-data PCA may spend its first
> direction describing how far cluster centers are from each other. Residual
> PCA removes that separation and instead sees how points vary inside their
> assigned clusters—the variation the compressed residual must represent.
>
> Because the rotation is full-dimensional and orthogonal, exact distances do
> not change. What changes is which directions SAQ sees early and may represent
> more accurately.

Stress that the picture is illustrative, not a measured two-dimensional case.

### Page 10 — Attempt 1B Algorithm: Head Plus Tail Norm

**Time: 60 seconds**

> The second implementation physically kept the first 576 coordinates. It
> replaced the discarded 384-dimensional tail by one number: its length.
>
> The estimate adds three terms: exact distance in the retained head, squared
> query-tail length, and squared database-tail length. What it cannot add is
> the tail inner product, which says whether the two tails point together or
> apart.
>
> In the example, tails plus one and plus one have true distance zero. Tails
> plus one and minus one have true distance four. Both cases expose the same
> two stored norms, so the estimator cannot distinguish them. This information
> loss exists before quantization.

### Page 11 — Attempt 1: What The Evidence Says

**Time: 75 seconds**

> On GIST, residual PCA reduced distance-estimation error by about six-tenths
> of one percent at one accurate stage. That was a real but small signal. The
> fast stage became worse, and the ranking gain was not reliable.
>
> We then repeated the frozen comparison on CIFAR. The direction did not
> repeat across seeds or in the no-rotation control, and the fast-stage harm
> remained. So the GIST result was a one-dataset estimator effect, not a
> general improvement.
>
> The reduced-dimension version failed even earlier. With exact retained
> coordinates and an exact tail norm, its top-100 agreement was already below
> native full-dimensional SAQ. The missing information was the interaction
> between the query and the discarded tail; one stored norm cannot recover
> that interaction.
>
> This does not prove that PCA is always optimal. It says these two proposed
> replacements did not justify more systems work.

Transition:

> Attempt 2 exposed a different version of the same gap between an internal
> objective and search quality.

### Page 12 — Attempt 2: Does Exact Training Help Search?

**Time: 45 seconds**

> A scalar codebook replaces many numeric values with a small set of
> representatives. Standard Lloyd training is iterative and can stop at a
> locally good answer. Exact one-dimensional dynamic programming finds the
> best partition for the chosen histogram.
>
> The important question was not only whether the exact trainer fits the data
> better. It was whether that cleaner fit produces better nearest-neighbor
> rankings after the bit allocation is chosen.

If asked what “dynamic programming” means, say:

> It is a systematic way of combining optimal solutions to smaller intervals,
> rather than repeatedly adjusting centers until they stop moving.

### Page 13 — Attempt 2 Algorithm: Exact Interval Dynamic Programming

**Time: 65 seconds**

> For one coordinate, we first sort the training values. In one dimension, an
> optimal cluster is always a consecutive interval in that order.
>
> The table called DP stores the best cost for representing the first m values
> with k representatives. To fill one entry, we try every legal place where
> the last interval could begin and combine it with the already solved prefix.
> After recovering the intervals, their means become codebook values. A second
> allocation step decides how many bits each coordinate receives.
>
> In the example zero, one, nine, ten, the best two-level split is after one.
> The two stored values are zero point five and nine point five. This is a
> global reconstruction optimum for the selected histogram; it is not a
> guarantee about future-query ranking.

If asked about “exact,” clarify that the implementation is exact for its
compressed histogram, then recomputes the final error over the raw values.

### Page 14 — Attempt 2: A Better Fit Was Not A Reliable Search Win

**Time: 70 seconds**

> There were positive examples. On the audio dataset, one setting reduced
> mean squared reconstruction error by about fifteen and a half percent and
> slightly improved Recall at 100.
>
> But the relationship was not stable. Increasing histogram resolution kept
> improving reconstruction while Recall did not improve monotonically. On
> DEEP, one four-bit setting reduced raw reconstruction error by about twenty
> percent but made Recall worse. Across CIFAR and DEEP, the result depended on
> the bit budget and allocation objective.
>
> There is also a novelty boundary. Wu established the exact one-dimensional
> quantization dynamic program in 1991, and Grønlund and colleagues later
> developed faster exact one-dimensional clustering algorithms. The recent
> White–Singal quantization paper also treats exact one-dimensional k-means as
> an older baseline. Our experiments remain useful as a stronger comparison,
> but they do not establish a new method.

Transition:

> Attempt 3 asked whether part of the apparent failure came from the quality
> measure rather than the index itself.

### Page 15 — Attempt 3: Were We Using The Wrong Quality Measure?

**Time: 50 seconds**

> Recall at 100 counts exact item identifiers. If the exact hundredth and
> hundred-and-first items are almost equally far away, exchanging them still
> hurts Recall.
>
> The distance-quality measure asks a softer geometric question: how much
> farther are the returned items than the exact ones? We replayed two frozen
> SAQ plans and reported both views. The encoder, index, and search procedure
> were unchanged.

If asked why this matters, say:

> Recall measures identity at a sharp boundary. Distance quality measures how
> costly the boundary mistake actually is.

### Page 16 — Attempt 3 Procedure: Re-score The Same Results

**Time: 55 seconds**

> This page is an evaluation procedure, not an index algorithm. We save the
> identifiers returned by the unchanged search, recompute their true distances,
> sort those distances, and compare them position by position with the exact
> nearest-neighbor distances. We then report the inverted average ratio together
> with Recall and query speed.
>
> In the example, the second returned item is only zero point two farther than
> the exact second item. The distance-quality score is about zero point nine
> five two. Recall can still fall to one half if that nearby replacement has a
> different identifier. This is why the two measurements can disagree without
> either one being incorrectly computed.

### Page 17 — Attempt 3: One Decision Changed, But No Method Emerged

**Time: 65 seconds**

> At the historical GIST reference point, the alternative plan could not
> reach the default plan's Recall target. Under distance quality, one measured
> point was slightly better in quality and about 1.078 times faster.
>
> That changes how we should report the old GIST comparison, but it is not
> uniform dominance. Nearly forty percent of paired queries became worse, and
> the positive result did not carry to either DEEP control. The metric itself
> also comes from prior work.
>
> The outcome is an evaluation lesson: future studies should show Recall and
> distance quality together. There is no new encoder or search mechanism here.

Transition:

> Attempt 4 was the most different idea. Its first obstacle was not search
> quality but whether the exact construction was affordable enough to test.

### Page 18 — Attempt 4: Can We Use A Fixed Bit Budget More Flexibly?

**Time: 45 seconds**

> Suppose two factors share one word with at most sixteen joint states. If
> each factor must use a power-of-two number of values, four by four is the
> natural choice. If arbitrary positive integers are allowed, three by five
> becomes another choice under the same stored-word budget.
>
> A synthetic example shows that three by five can fit uneven data better.
> This proves that the mathematical choice set is larger. It does not yet
> show that we can construct the codebooks cheaply or improve real search.

### Page 19 — Attempt 4 Algorithm: Flexible Product Cardinalities

**Time: 65 seconds**

> We first compute the best scalar reconstruction error for every coordinate
> and every number of representatives from one to 256. We then take adjacent
> coordinate pairs. For each pair, we choose two positive integers whose
> product fits in the fixed word and whose summed reconstruction error is
> smallest. The two labels are packed into one mixed-radix address.
>
> One coordinate alone cannot show the benefit: with sixteen available states,
> it simply uses sixteen levels. Two coordinates are the smallest case where
> the capacity can be divided differently.
>
> In the example, one coordinate naturally has three values and the other has
> five. Three by five represents all fifteen combinations exactly in a 4-bit
> word. Restricting both counts to powers of two forces a shape such as four by
> four and merges two values on the second coordinate.

### Page 20 — Attempt 4: The Cost Gate Ended The Study

**Time: 70 seconds**

> The synthetic implementation first passed its registered correctness
> checks. Before reading benchmark data, we measured the cost of the exact
> construction and evidence pipeline.
>
> The actual partial run used about 9.67 processor-hours and completed only 61
> of 128 scalar coordinates. The rule fixed in advance multiplied one panel by
> two datasets plus a 25 percent margin. The completed prefix therefore already
> implied a lower bound of 24.17025 processor-hours, above the 24-hour limit.
>
> About 4.64 hours were the exact scalar calculation and 5.03 hours were spent
> serializing the complete audit evidence. The later allocation, two-dimensional
> comparison, and encoding stages had not started.
>
> This is important: the result says the registered evaluation pipeline was
> too expensive. It does not say arbitrary cardinalities are bad for search;
> no real-data search experiment occurred.
>
> A later attempt to establish a cleaner execution path recorded that it
> started but never produced a trustworthy completion record. We classify
> that runtime as unknown and have closed further recovery work. There is no
> natural-data, search, or performance claim from Attempt 4.

If challenged on the small amount above 24 hours, answer from the Q&A card.

### Page 21 — What These Four Attempts Have In Common

**Time: 45 seconds**

> Each attempt improved or clarified something local: an estimator on one
> dataset, a reconstruction objective, an evaluation metric, or a
> mathematical feasible set.
>
> The result stopped at the next link to the paper claim: replication,
> ranking, novelty, or construction cost.
>
> My main lesson is that the next project should test that shortest missing
> link first. We should not build a large experimental pipeline around a local
> objective before checking whether it predicts the final search result.

### Page 22 — What Is Still Useful

**Time: 40 seconds**

> The work still leaves useful assets. SAQ remains a strong baseline. Exact
> scalar training is a tougher offline comparison. We have a concrete reason
> to report Recall and geometric quality together. We also have examples
> showing why reconstruction error alone is a weak search proxy, and a
> precedent for checking construction cost before using benchmark queries.
>
> These should strengthen the evaluation of the next project. They do not
> need to become contributions by themselves.

### Page 23 — My Recommendation

**Time: 55 seconds**

> My recommendation is to close these four method lines and choose the next
> problem from the primary literature before opening another implementation
> branch.
>
> I suggest four entry conditions. The limitation should appear on at least
> two strong independent baselines. The closest published work should leave a
> specific gap, not merely components that we can combine. We should have one
> cheap test that can reject the idea early. Finally, construction, memory,
> and query cost should be part of the acceptance rule from the beginning.
>
> The decision I would like from this meeting is whether we agree with that
> closure and selection rule.

Stop speaking. Let the audience respond. Do not continue into the appendix.

## Backup Slides

### Page 24 — Short Technical Appendix Divider

Do not show unless the discussion moves to exact evidence.

### Page 25 — Appendix Purpose

Use only to remind the audience that detailed protocols and implementation
records exist elsewhere. Do not explain the provenance machinery.

### Page 26 — Terms Used In The Talk

Open when someone asks what SAQ, residual, Recall, distance quality, QPS, or a
CPU-hour means. Give the definition on the slide, then return to the main
question.

### Page 27 — Attempt 1 Evidence Boundary

Open when asked:

- how large the GIST effect was;
- how the CIFAR replication failed; or
- why the reduced-dimension idea stopped before index construction.

One-sentence answer:

> The full-dimensional effect was small and did not replicate; the lossy
> version ranked worse than native SAQ even before adding quantization error.

### Page 28 — Attempt 2 Evidence Boundary

Open when asked for a positive and a negative example.

One-sentence answer:

> Exact training can reduce reconstruction error substantially, but the DEEP
> counterexample shows that this does not determine Recall.

### Page 29 — Attempt 3 Evidence Boundary

Open when asked where the 1.078-times result comes from or whether every query
improved.

One-sentence answer:

> It is one measured GIST operating point; the aggregate improved, but 39.6%
> of paired queries worsened and the DEEP controls remained negative.

### Page 30 — Attempt 4 Boundary

Open when asked whether the synthetic example or cost result says anything
about real search.

One-sentence answer:

> The example validates a mathematical opportunity, while the cost gate stops
> the registered pipeline before any real-data or search claim.

### Page 31 — What We Can And Cannot Say

Open whenever a question is framed as a universal conclusion—for example,
“Does this prove PCA is optimal?” or “Does exact training never help?”

Say:

> No. Our decisions are about the tested mechanisms under their frozen gates,
> not universal impossibility results.

### Page 32 — Authoritative Source Snapshots

Use only if someone asks whether the results are committed and reviewed. Do
not read identifiers aloud. Point out that each attempt has a fixed source
snapshot and that the meeting-summary branch only summarizes it.

### Page 33 — Authoritative Evidence Documents

Use only when someone wants the exact evidence document. Do not spend meeting
time explaining filenames.

### Page 34 — Selected References For Attempt 2

Open when someone asks which work supports the prior-art statement.

Say:

> Wu 1991 is the early exact one-dimensional quantization reference. Grønlund
> and colleagues 2017 provide the later fast exact clustering result.
> White–Singal 2026 is recent adjacent quantization work that explicitly treats
> exact one-dimensional k-means as an existing baseline rather than its own
> contribution.

## Final Rehearsal Check

The talk is ready when all five conditions hold:

1. pages 1–23 finish within 17 minutes, or within 12 minutes when the five
   optional algorithm-detail pages are skipped;
2. each attempt can be summarized without reading the slide;
3. the presenter never describes a local metric improvement as a method;
4. the presenter can explain the Attempt 4 stop without implying a real-data
   negative result; and
5. the closing question is asked exactly once, then the presenter stops.

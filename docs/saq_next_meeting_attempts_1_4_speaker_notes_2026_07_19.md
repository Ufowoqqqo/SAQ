# Four Ideas We Tested — Presenter Notes

For:
`docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md`

PDF snapshot: current successor deck, 29 pages. Its scientific conclusions are
unchanged from `saq-meeting-summary@9c21469`; the later deck update adds only
the missing Attempt 2 references.

Status: meeting-preparation notes only. These notes do not change any research
decision, reporting state, or authorization.

## How To Use These Notes

- Target **11–12 minutes** for pages 1–18.
- Pages 19–29 are backup slides. Do not present them in sequence.
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

### Page 9 — Attempt 1: What The Evidence Says

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

### Page 10 — Attempt 2: Does Exact Training Help Search?

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

### Page 11 — Attempt 2: A Better Fit Was Not A Reliable Search Win

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

### Page 12 — Attempt 3: Were We Using The Wrong Quality Measure?

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

### Page 13 — Attempt 3: One Decision Changed, But No Method Emerged

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

### Page 14 — Attempt 4: Can We Use A Fixed Bit Budget More Flexibly?

**Time: 45 seconds**

> Suppose two factors share one word with at most sixteen joint states. If
> each factor must use a power-of-two number of values, four by four is the
> natural choice. If arbitrary positive integers are allowed, three by five
> becomes another choice under the same stored-word budget.
>
> A synthetic example shows that three by five can fit uneven data better.
> This proves that the mathematical choice set is larger. It does not yet
> show that we can construct the codebooks cheaply or improve real search.

### Page 15 — Attempt 4: The Cost Gate Ended The Study

**Time: 70 seconds**

> The synthetic implementation first passed its registered correctness
> checks. Before reading benchmark data, we measured the cost of the exact
> construction and evidence pipeline.
>
> The projected cost was 24.17025 processor-hours. The stopping limit fixed
> before the run was 24 hours. Because the rule was fixed in advance, we
> stopped rather than relaxing it after seeing the result.
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

### Page 16 — What These Four Attempts Have In Common

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

### Page 17 — What Is Still Useful

**Time: 40 seconds**

> The work still leaves useful assets. SAQ remains a strong baseline. Exact
> scalar training is a tougher offline comparison. We have a concrete reason
> to report Recall and geometric quality together. We also have examples
> showing why reconstruction error alone is a weak search proxy, and a
> precedent for checking construction cost before using benchmark queries.
>
> These should strengthen the evaluation of the next project. They do not
> need to become contributions by themselves.

### Page 18 — My Recommendation

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

### Page 19 — Short Technical Appendix Divider

Do not show unless the discussion moves to exact evidence.

### Page 20 — Appendix Purpose

Use only to remind the audience that detailed protocols and implementation
records exist elsewhere. Do not explain the provenance machinery.

### Page 21 — Terms Used In The Talk

Open when someone asks what SAQ, residual, Recall, distance quality, QPS, or a
CPU-hour means. Give the definition on the slide, then return to the main
question.

### Page 22 — Attempt 1 Evidence Boundary

Open when asked:

- how large the GIST effect was;
- how the CIFAR replication failed; or
- why the reduced-dimension idea stopped before index construction.

One-sentence answer:

> The full-dimensional effect was small and did not replicate; the lossy
> version ranked worse than native SAQ even before adding quantization error.

### Page 23 — Attempt 2 Evidence Boundary

Open when asked for a positive and a negative example.

One-sentence answer:

> Exact training can reduce reconstruction error substantially, but the DEEP
> counterexample shows that this does not determine Recall.

### Page 24 — Attempt 3 Evidence Boundary

Open when asked where the 1.078-times result comes from or whether every query
improved.

One-sentence answer:

> It is one measured GIST operating point; the aggregate improved, but 39.6%
> of paired queries worsened and the DEEP controls remained negative.

### Page 25 — Attempt 4 Evidence Boundary

Open when asked whether the synthetic example or cost result says anything
about real search.

One-sentence answer:

> The example validates a mathematical opportunity, while the cost gate stops
> the registered pipeline before any real-data or search claim.

### Page 26 — What We Can And Cannot Say

Open whenever a question is framed as a universal conclusion—for example,
“Does this prove PCA is optimal?” or “Does exact training never help?”

Say:

> No. Our decisions are about the tested mechanisms under their frozen gates,
> not universal impossibility results.

### Page 27 — Authoritative Source Snapshots

Use only if someone asks whether the results are committed and reviewed. Do
not read identifiers aloud. Point out that each attempt has a fixed source
snapshot and that the meeting-summary branch only summarizes it.

### Page 28 — Authoritative Evidence Documents

Use only when someone wants the exact evidence document. Do not spend meeting
time explaining filenames.

### Page 29 — Selected References For Attempt 2

Open when someone asks which work supports the prior-art statement.

Say:

> Wu 1991 is the early exact one-dimensional quantization reference. Grønlund
> and colleagues 2017 provide the later fast exact clustering result.
> White–Singal 2026 is recent adjacent quantization work that explicitly treats
> exact one-dimensional k-means as an existing baseline rather than its own
> contribution.

## Final Rehearsal Check

The talk is ready when all five conditions hold:

1. pages 1–18 finish within 12 minutes;
2. each attempt can be summarized without reading the slide;
3. the presenter never describes a local metric improvement as a method;
4. the presenter can explain the Attempt 4 stop without implying a real-data
   negative result; and
5. the closing question is asked exactly once, then the presenter stops.

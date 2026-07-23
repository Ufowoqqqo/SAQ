# Meeting summary: why A4-OR-C stopped

## Short version

The experiment stopped because the ordinary product-quantization comparison
temporarily produced empty clusters while it was training. Faiss repaired
those clusters automatically, but our frozen rule said that even one such
repair makes the comparison invalid.

The follow-up check shows that the final comparison models were complete and
usable. Therefore the stop tells us that the rule was too strict for judging
the final model. It does not tell us that Attempt 4 failed.

## What “split” means here

The ordinary comparison divides each small coordinate block into 256 groups.
During training, a group can temporarily receive no training points. Faiss
handles this by splitting a populated group and using the two resulting
centers to fill the empty place. It records how many such repairs happened in
the field named `nsplit`.

Our frozen protocol required `nsplit=0` for every training run. That is why the
experiment stopped.

## What we checked afterward

We reran only the ordinary comparison on the same artificial 8,192-row input.
We did not use GIST, CIFAR, benchmark queries, Recall, or generated indexes.

For every coordinate block and every one of the eight starting points, we
checked:

- how many different training points existed;
- when an empty-cluster repair occurred;
- whether the final 256 groups still contained an empty group;
- whether two final centers were identical;
- whether all rows could be encoded; and
- whether reconstruction remained finite.

## Result

The input had far more than 256 different points in every block.

- At 32-byte payload, repairs occurred in 5 of 32 blocks.
- At 64-byte payload, repairs occurred in all 64 blocks.
- Most repairs occurred during initialization or the first update.
- After training, none of the 768 inspected models had an empty final group.
- None had duplicate final centers.
- Every row received a complete code and finite reconstruction.

So the repairs were temporary training events. They did not leave a broken
final comparison model.

## What this means

The official A4-OR-C result remains `CONTROL_INVALID`; we cannot rewrite it as
a pass after seeing the outcome.

However, the failure was caused by how we defined a valid comparison, not by a
measured failure of the Attempt 4 candidate. The rule treated Faiss's normal
recovery mechanism as fatal even when the final model was complete.

On 2026-07-23 we decided to reopen only the synthetic admission with a
final-model rule:

- final groups must all be occupied;
- final centers must not collide;
- shape and encoding must be complete; and
- intermediate repairs are reported but are not automatically fatal.

This is a real, documented change to the comparison rule. The old stopped run
will remain visible as historical evidence; the revised run will produce a
separate result. We will first compile and run cheap exact checks, then verify
that all later admission decisions are implemented before paying for the full
run. Natural-data work remains unauthorized.

## Revised-run outcome

The revised artificial-data run is now complete. One warmup and three measured
runs all passed:

- every final P and V group was occupied;
- no final centers were duplicates;
- shape and encoding were complete;
- the numerical result was stable at both histogram resolutions; and
- projected D/A construction was about 31 CPU minutes for two datasets, below
  the one-hour early-feasibility limit.

This reopens the scientific question; it does not answer it on real data. The
next research step, if chosen, is a separately bounded base-data evaluation.
It must still exclude held-out query tuning and cannot claim unchanged-SAQ
compatibility, Recall improvement, or a paper contribution from this synthetic
pass alone.

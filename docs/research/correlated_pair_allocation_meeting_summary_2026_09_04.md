# Meeting summary: allocating bits between correlated coordinate pairs

Date: 2026-09-04

## One-sentence conclusion

Different coordinate pairs look as if they deserve different numbers of bits
before SAQ performs its internal rotation, but that opportunity disappears in
the rotated coordinates that SAQ actually stores and searches. We therefore
stop the current pair-level allocation direction and do not build a query
consumer for it.

## What question were we trying to answer?

Suppose `(D1,D2)` form one meaningful coordinate pair and `(D3,D4)` form
another. The question was not whether `D1` should receive more bits than `D2`.
It was whether the first *pair as a whole* should receive more storage than the
second pair because the two pairs have different quantization difficulty.

This corrected an earlier mismatch between the intended research question
and our previous mixed-radix experiments.

## What did the first diagnostics show?

Using only database-side learn/base vectors, we measured how much
reconstruction error falls when bits can move between 64 two-coordinate
groups while total storage remains fixed.

The signal survived the representations relevant to SAQ. Here an IVF residual
means the part left after subtracting the coarse cluster center assigned to a
vector:

- on SIFT IVF residuals, fixed adjacent groups improved reconstruction by
  about 20%--23%;
- on GIST IVF residuals, they improved it by about 12%--14%; and
- the return from an extra bit was predicted much more strongly by a group's
  total variance than by the correlation between its two coordinates.

This means that unequal resource demand between groups is real. It does not
mean that “pair the most correlated coordinates” is the right rule.

## Why was that still not a new method?

The ingredients already appear in earlier work:

- transform coding allocates different bit counts to transformed components;
- OPQ optimizes rotations and product-quantizer decompositions;
- BAPQ and DSPQ allocate unequal bits to different product-quantizer
  subspaces; and
- SAQ already uses dynamic programming to choose segment boundaries and bit
  widths.

Our local two-dimensional rotation, fitted quantization curves, and exact
budget solver combine these known ingredients. The exact solver is useful for
correctness, but it does not by itself create a new scientific contribution.

The only remaining SAQ-specific possibility was narrower: perhaps different
pairs could receive different bit widths *inside an existing SAQ segment*
while keeping the same segment factors, storage, and query structure.

## The decisive SAQ-specific check

We reproduced the actual SAQ storage budget:

| Dataset | SAQ plan | Total storage counted here |
| --- | --- | ---: |
| SIFT1M | all 128 dimensions use 4 bits each | 72 bytes/vector |
| GIST1M | the successive groups of 64, 192, 320, 256, and 128 dimensions use 11, 6, 4, 2, and 0 bits each | 488 bytes/vector |

For every positive SAQ segment, we kept:

- the same segment boundaries;
- the same payload and factor bytes;
- one common scale for the whole segment;
- one fixed segment-local orthogonal rotation following SAQ's representation
  semantics; and
- the six rounds of SAQ/CAQ code adjustment.

Only the bit widths of adjacent coordinate pairs were allowed to change.
Fitting used one half of the frozen base sample and evaluation used the other;
then the two halves were exchanged.

## Result

Before the segment rotation, the apparent residual-space opportunity was:

- roughly 28%--31% on SIFT;
- roughly 6.3%--6.4% on GIST.

After the segment rotation:

- every SIFT pair selected the original 4-bit width;
- every positive GIST pair selected its segment's original 11-, 6-, 4-, or
  2-bit width;
- zero pairs changed width across both datasets, both IVF settings, and both
  fit/evaluation directions; and
- the final matched-byte direction-error improvement—the part a shared scale
  cannot remove—was exactly 0%.

The fixed 5% materiality requirement therefore fails decisively.

## Why does rotation change the answer?

PCA puts much more energy in early coordinates than later coordinates. Before
the SAQ rotation, that makes some pairs look far more important than others.

SAQ then rotates the coordinates inside each segment. This spreads the
segment's energy more evenly over its stored coordinates. Once we measure the
coordinates that the quantizer actually receives, moving an integer bit from
one pair to another no longer reduces the fitted error.

So the earlier positive result was not wrong. It measured an opportunity that
exists before a later SAQ step removes it.

## Decision and boundary

Decision: `STOP_CURRENT_POST_ROTATION_PAIR_ALLOCATION`.

We should not implement the current local-PCA/Lloyd consumer or a ragged
mixed-width SAQ consumer. The required base-only opportunity is absent before
paying any query-time engineering cost.

This does **not** prove that every possible transform and allocation must
fail. Removing or jointly redesigning the SAQ rotation could create a
different question, but it would overlap heavily with transform coding, OPQ,
BAPQ, and DSPQ. It cannot be presented as a continuation already supported by
the current result.

## Evidence status

- Official TexMex SIFT1M and GIST1M learn/base identities were verified.
- No benchmark query, ground truth, Recall, QPS, or old ANN result was read.
- Ten focused tests and the C++ extractor build pass.
- Two accepted executions produced byte-identical scientific summaries.
- The complete negative result is preserved in commit `08ac7c7`, already
  pushed to `origin/saq-correlated-pair-allocation`.

Detailed sources:

- `docs/research/correlated_pair_allocation_stage_attribution_2026_09_03.md`;
- `docs/research/correlated_pair_allocation_closest_primary_work_review_2026_09_03.md`;
- `docs/research/correlated_pair_allocation_saq_opportunity_decomposition_2026_09_03.md`.

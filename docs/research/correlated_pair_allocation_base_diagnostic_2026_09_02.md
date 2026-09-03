# Correlated-pair allocation base-only diagnostic

Date: 2026-09-02

Branch/base: `saq-correlated-pair-allocation` from `d305578`

Evidence class: `BASE_ONLY_RECONSTRUCTION_DIAGNOSTIC`

## Question

The allocation unit in this experiment is a two-dimensional block, not an
individual coordinate.  The experiment asks whether strong associations such
as `(D1,D2)` and `(D3,D4)` are stable on natural base vectors, and whether a
fixed total budget should then be redistributed between those blocks instead
of assigning eight bits to every block.

This is different from the closed mixed-radix question, which redistributed
cardinality between the two individual coordinates inside one fixed-width
block.

## Frozen boundary

The runner uses only the first 1,000,000 base rows and the first 128 raw
coordinates of SIFT10M and GIST1M. The SIFT input is explicitly a
`SIFT10M_SLICE1M` object; its prefix hash does not match official SIFT1M and it
must not be labeled SIFT1M. A fixed seed selects 16,384 rows and splits
them into two folds of 8,192 rows.  Each fold is used once for fitting and once
for held-out evaluation.  No query, ground truth, Recall, QPS result, IVF
assignment, or previous outcome is read.

The three pairings are:

- `CORR_GREEDY`: deterministic strongest-edge-first matching by absolute
  Pearson correlation;
- `EA`: the existing two-coordinate specialization of OPQ-P Eigenvalue
  Allocation, using coordinate variance;
- `ADJ`: fixed adjacent coordinate pairs.

For each pair, the fit fold determines a local two-dimensional PCA basis.
Deterministic one-dimensional Lloyd quantizers produce reconstruction curves
for total group budgets from 6 through 10 bits.  The within-pair split uses
ordinary integer bit counts whose sum is the group budget; it does not use
arbitrary mixed radices.  A dynamic program assigns exactly 512 bits across
the 64 groups.  Its held-out reconstruction is compared with uniform eight
bits per group.  The frozen materiality screen is at least 5% held-out
reduction in both cross-fit directions.

## Result

Strong pairwise association exists and is stable.  The correlation-selected
pairs retain 47/64 identical pairs across SIFT folds and 46/64 across GIST
folds.  All selected pair correlations retain their sign.  Held-out mean
absolute correlation is about 0.53 for SIFT and 0.74 for the GIST head.
Across all 8,128 possible pairs, the held-out absolute-correlation
50th/90th/99th percentiles are approximately `0.062/0.232/0.512` for SIFT and
`0.335/0.497/0.748` for the GIST head.  Association is therefore much stronger
overall in this GIST view, rather than only in the 64 selected edges.

The allocation hypothesis nevertheless fails its frozen screen:

| Dataset | Fit direction | Pairing | Held-out gain from allocation |
| --- | --- | --- | ---: |
| SIFT10M slice1m | A to B | CORR_GREEDY | 3.110% |
| SIFT10M slice1m | B to A | CORR_GREEDY | 4.139% |
| GIST1M head128 | A to B | CORR_GREEDY | 1.487% |
| GIST1M head128 | B to A | CORR_GREEDY | 1.541% |

The controls reveal a more specific mechanism rather than a universal lack of
pair-level heterogeneity:

- SIFT allocation gains are at most 1.02% for `ADJ` and 0.47% for `EA`.
- GIST `ADJ` gains 5.731% and 5.872%, while `EA` gains 0.337% and -0.062%.
- With uniform eight-bit groups, correlation pairing is about 16.6--17.9%
  better than adjacency on GIST, but 3.5--5.0% worse on SIFT.

Thus correlation pairing and cross-pair allocation are distinct effects.
Strong within-pair correlation can make a local PCA block easier to encode,
but does not imply that the resulting correlated blocks have sufficiently
different marginal returns to justify reallocating their budgets.  The GIST
adjacency result indicates real block-budget heterogeneity in that raw view,
but its cause is not captured by strongest-correlation grouping and it does
not generalize to SIFT.

Decision: `CORRELATION_DRIVEN_ALLOCATION_SCREEN_FAIL`.  Do not infer that
pair-level allocation is universally useless.  Do not promote the positive
GIST-adjacent row into a method without first explaining why adjacency exposes
heterogeneity, checking the actual SAQ residual space, and reviewing the
closest transform-coding and adaptive bit-allocation work.

## Reproduction and cost

Command, from the repository worktree:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python research/correlated_pair_allocation/diagnostic.py \
  --sift /rwproject/kdd-db/kluaq/dataset/sift10m/sift10m_base.fvecs \
  --gist /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs \
  --output /tmp/correlated-pair-allocation/base-v3 --frozen
```

Focused tests:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
python -m unittest research.correlated_pair_allocation.test_diagnostic
```

Accepted outputs are under
`/tmp/correlated-pair-allocation/base-v3/`.  They include complete tables for
all pairwise correlations and all 6--10-bit block curves.  A second execution
under `base-v4/` reproduced the metadata, summaries, chosen-pair tables,
complete curves, and complete correlation tables byte for byte.  Every one of
the 12 dataset/fold/plan allocations contains 64 groups totaling exactly 512
bits.

Across all four development and accepted executions, measured work was about
457.7 CPU-seconds (0.127 CPU-hours) and 769.4 wall-seconds (0.214 wall-hours).
Peak RSS was 967,938,048 bytes.  The first pass included cold storage delays;
each final complete pass took about 114 wall-seconds.  Total work remains far
below the two-hour and 16-GiB ceilings.

## Claim limits and next uncertainty

This result uses raw base coordinates.  It is not evidence about the actual
PCA/IVF residuals consumed by SAQ, benchmark-query ranking, Recall, QPS, index
bytes, or construction cost.  It uses a deterministic greedy correlation
matching, not an exact maximum-weight correlation matching.  Local PCA plus
Lloyd quantization is a diagnostic model and overlaps established transform
coding; it is not a novelty claim.

The smallest justified next action is a residual-space mechanism check that
recreates only the necessary base-derived SAQ input and asks why GIST adjacent
blocks show cross-block rate heterogeneity while correlation-selected blocks
do not.  That question should be settled before implementing any new index or
query consumer.

# Base-only SAQ opportunity decomposition for two-dimensional allocation

Date: 2026-09-03

Reviewed code snapshot: working tree after `4245f73` on
`saq-correlated-pair-allocation`

## Decision

Decision: `STOP_CURRENT_POST_ROTATION_PAIR_ALLOCATION`.

The large rate--distortion opportunity seen on PCA and IVF-residual
coordinates is a pre-segment-rotation effect. After a fixed orthogonal
rotation inside each production SAQ segment, both SAQ's variance surrogate and
empirical uniform-lattice curves select the existing uniform bit width for
every two-coordinate group. The accepted residual-stage gain is therefore
0% on SIFT1M and GIST1M, below the frozen 5% threshold.

This closes the specific proposal of reallocating bits between adjacent
two-coordinate groups *after retaining the current SAQ segment rotation*.
It is not a theorem against a new joint transform/allocation design. Such a
design would change the scientific question and would face the transform
coding, OPQ, BAPQ, and DSPQ prior work documented in
`correlated_pair_allocation_closest_primary_work_review_2026_09_03.md`.

## Falsifiable question

At exactly the bytes used by the current SAQ plan, does a CAQ-compatible
schema that gives different bit widths to adjacent coordinate pairs retain at
least 5% held-out base-only opportunity after the normal segment-local
orthogonal rotation?

The test keeps:

- the current SAQ 64-coordinate boundary granularity;
- the current SAQ plan learned from the fit half of the PCA representation;
- the same positive segments and one 64-bit factor charge per positive
  segment;
- one shared maximum and one shared rescale direction per vector segment;
- adjacent two-coordinate groups with equal width inside each pair;
- exactly matched payload and factor bits; and
- the existing six-round CAQ coordinate-adjustment rule and epsilon.

It changes only the number of lower bits assigned to pairs inside an existing
positive segment. No per-pair factor, plan ID, query input, index, or consumer
is introduced.

## Inputs and cross-fitting

The input consists only of the previously verified official TexMex SIFT1M and
GIST1M learn/base-derived state. No query, ground-truth, Recall, QPS, or old
serialized-index artifact was read.

The same frozen 16,384 base rows are split into 8,192-row A/B halves. Plans and
pair allocations are fitted in both `A_TO_B` and `B_TO_A` directions. Full
dimensional PCA and `nlist={1024,4096}` residual panels are reconstructed from
the already verified PCA, coarse centroids, and base assignments.

## Compared quantities

Three levels separate the source of the apparent opportunity.

1. **Pre-rotation planner upper bound.** Within each fixed SAQ segment, assign
   pair widths by minimizing SAQ's own `sum(variance / 2^bits)` surrogate.
2. **Post-rotation planner opportunity.** Repeat the same allocation after a
   fixed Gaussian-QR orthogonal rotation in every segment.
3. **Post-rotation empirical lattice opportunity.** Fit pair-specific SSE
   curves using the actual uniform scalar lattice with the segment's shared
   per-vector maximum. Evaluate the selected allocation and the uniform
   segment baseline after the generalized six-round production CAQ adjustment
   using the shared-rescale-invariant loss
   `norm_squared * tan(angle)^2`.

The accepted gate uses only level 3 on IVF residual stages. The rotation seed
is `20260903`; matrices are canonicalized by the sign of the QR diagonal and
their SHA-256 values are stored in the summary.

## Exact byte accounting and recovered plans

| Dataset | SAQ plan | Payload | Factors | Total |
| --- | --- | ---: | ---: | ---: |
| SIFT1M | `128d@4b` | 512 bits | 64 bits | 576 bits (72 B) |
| GIST1M | `64@11 | 192@6 | 320@4 | 256@2 | 128@0` | 3,648 bits | 256 bits | 3,904 bits (488 B) |

Both folds independently recover the same plans. The GIST result also matches
the previously recorded production plan, providing a planner-parity check.

## Results

The table reports held-out gain relative to the same SAQ plan. Values in each
cell are `A_TO_B / B_TO_A`.

| Dataset | Residual stage | Pre-rotation surrogate | Post-rotation surrogate | Adjusted empirical angular gain | Pairs changing width |
| --- | --- | ---: | ---: | ---: | ---: |
| SIFT1M | `nlist=1024` | 30.742% / 30.834% | approximately 0% | 0% / 0% | 0 / 0 |
| SIFT1M | `nlist=4096` | 28.197% / 28.386% | approximately 0% | 0% / 0% | 0 / 0 |
| GIST1M | `nlist=1024` | 6.446% / 6.386% | approximately 0% | 0% / 0% | 0 / 0 |
| GIST1M | `nlist=4096` | 6.391% / 6.313% | approximately 0% | 0% / 0% | 0 / 0 |

The post-rotation surrogate deviations are at most about `1e-13` percentage
points and are floating-point noise. More decisively, empirical lattice curve
fitting chooses exactly the baseline segment width for every pair: 4 bits on
SIFT and 11/6/4/2 bits in the corresponding positive GIST segments. The mixed
and baseline adjusted codes are consequently identical.

The mechanism is straightforward. PCA deliberately concentrates variance in
early coordinates, so pair-level allocation before the SAQ rotation sees a
large gradient. The segment-local orthogonal rotation spreads that energy
within each already selected segment. Once pair curves are measured in the
consumer's rotated coordinate system, there is no discrete bit transfer whose
fit cost improves on the existing uniform segment width.

## Reproduction and verification

The extractor was rebuilt before execution, and 10 focused Python tests pass.
The generalized mixed-width adjustment matches an independent scalar
implementation element by element on a tiny fixture.

Accepted commands:

```bash
cmake --build /tmp/correlated-pair-allocation/build -j2 \
  --target correlated_pair_extract_stages
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m unittest \
    research.correlated_pair_allocation.test_diagnostic \
    research.correlated_pair_allocation.test_opportunity
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 python -B \
  research/correlated_pair_allocation/opportunity.py \
  --sift-stages /tmp/correlated-pair-allocation/opportunity-stages-v1/sift \
  --gist-stages /tmp/correlated-pair-allocation/opportunity-stages-v1/gist \
  --output /tmp/correlated-pair-allocation/opportunity-v3 --frozen
```

The final run was repeated as `opportunity-v4`. Scientific outputs are
byte-identical:

- `metadata.txt` SHA-256:
  `38cc5a8c2ffdde56954fa8b497da913c9a1ad10230bb5eb4946262ed222ee1b0`;
- `summary.tsv` SHA-256:
  `d549b570797a13653af0fce2844b47514404b856ef6b06eaa1a65edec192e671`.

The two accepted runs used 93.71/93.69 CPU-seconds and 94.12/94.03 wall-seconds,
with peak RSS below 716 MB. All generated panels and result tables remain
under `/tmp` and are not committed.

## Claim boundary

Established:

- the pre-rotation pair-allocation signal is large on SIFT and still above 5%
  on GIST;
- the signal disappears under the frozen segment-local rotation in both the
  SAQ surrogate and empirical uniform-lattice curves;
- exact payload and factor bytes are matched; and
- the current post-rotation pair-allocation mechanism fails its 5% gate.

Not established:

- Recall, QPS, index-size, or end-to-end performance;
- behavior for every possible orthogonal rotation;
- an impossibility result for jointly changing the transform and allocation;
- a defect in SAQ's current planner; or
- a new scientific contribution.

Performance status: `PROTOTYPE_NOT_PERFORMANCE_EVIDENCE`.

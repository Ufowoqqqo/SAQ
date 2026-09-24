# Read-only result review

Reviewed `strong_baselines_v1/{summary,allocations,axis_curves,comparisons}.tsv`,
the runner metadata and resource record, and the frozen diagnostic source.
This review recomputed table arithmetic only; it did not retrain codebooks,
rerun either allocator, rerun tests, or launch an experiment.

## Integrity and correctness

No numerical contradiction or missing required result row was found.

- The summary is the complete 2 datasets × 2 folds × 3 pairings × 4 arms grid:
  48 unique rows. There are 6,144 allocation rows and 13,824 unique axis-curve
  rows, with nine candidate widths for every axis in each pairing/fold.
- The 16 comparisons contain exactly the declared CORR-E candidate against
  CORR-S, CORR-V, ADJ-S, and EA-S in each dataset/fold. All recorded comparison
  gains agree with the absolute SSE values.
- Every arm has 128 axes, widths from one to nine, and a sum of exactly
  512 bits. Every pairing is a complete disjoint partition of the 128 source
  dimensions. U has eight bits in every group; V and E satisfy six to ten bits
  in every group. Reported S violations and bit histograms match allocations.
- Every selected fit and evaluation SSE matches its corresponding raw axis
  curve exactly. Summing the 128 recorded axis errors reproduces each summary
  total with zero discrepancy in this audit. Dividing by 8,192 reproduces the
  per-vector SSE. Curves contain finite, nonnegative SSE and variance values;
  codebook center counts match 2^bits.
- S fit SSE is no higher than E in all 12 pairing/dataset/fold contexts.
  Across the four contexts, S violates the old group range in ADJ for
  1, 1, 3, and 4 groups; in CORR for 0, 0, 2, and 0 groups; and in EA for none.
- The source executes the independent constrained scalar DP check for every
  pairing/fold and checks both its objective and exact bit choices against E.
  Completion of all rows therefore confirms that these runtime checks passed.
  This review did not independently solve the allocation problems again.
- Source inspection confirms fit-only pairing, local PCA, Lloyd centers, and
  allocation. Evaluation curves only score the selected allocations. The V
  exponent is −2b. The four arms reuse the same fitted model within a pairing.
- Current source SHA-256 values match the run metadata: strong_baselines.py
  `6536c096c7821624f0d4a8c6eb9c6e4f62840502a6171c16af2cd2a618c5b17e`;
  diagnostic.py
  `263f0d5363f7a35c4a938915e5f040e46ec49cff5506784f074f7538797a8b38`.

## Allocation effect

CORR-E and CORR-S have identical 128-axis bit assignments in SIFT A→B,
SIFT B→A, and GIST-128 B→A. Their fit and evaluation SSE are exactly equal
in these three contexts. GIST-128 A→B changes four axis widths when the group
restriction is removed: S fit SSE falls by 0.189125%, and E evaluation SSE is
0.367641% higher than S. There is no observed held-out regularization gain
from the pair constraint.

All values below are percentage SSE reductions of CORR-E relative to the
column's comparator; negative values mean CORR-E is worse.

| Dataset / fit→evaluation | CORR-S | CORR-V | ADJ-S | EA-S |
| --- | ---: | ---: | ---: | ---: |
| SIFT1M A→B | 0.000000 | 0.033066 | −0.793204 | −0.774187 |
| SIFT1M B→A | 0.000000 | 0.047825 | 0.484615 | −0.040954 |
| GIST-128 A→B | −0.367641 | 0.517632 | 0.088388 | −0.192339 |
| GIST-128 B→A | 0.000000 | 0.752183 | 0.107148 | −0.570150 |

CORR-E improves its own U by 19.634195%, 21.357127%, 10.072744%, and
8.760664%, respectively. Those large within-pairing gains do not establish an
increment over the strong controls. CORR-E is worse than EA-S in every
context, never better than CORR-S, and less than 1% better than CORR-V.
`STOP_CURRENT_FORMULATION` follows the frozen rule without choosing another
candidate or relying on borderline rounding.

## Pairing and local-transform effect

This separate comparison uses free scalar allocation in all methods.

| Dataset / fit→evaluation | CORR-S SSE/vector | ADJ-S SSE/vector | EA-S SSE/vector | Gain vs ADJ-S | Gain vs EA-S |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT1M A→B | 463.262293885 | 459.616598139 | 459.703331865 | −0.793204% | −0.774187% |
| SIFT1M B→A | 471.069863270 | 473.363856047 | 470.877018317 | 0.484615% | −0.040954% |
| GIST-128 A→B | 0.012470381829 | 0.012527300741 | 0.012492200679 | 0.454359% | 0.174660% |
| GIST-128 B→A | 0.012320510122 | 0.012333725468 | 0.012250663006 | 0.107148% | −0.570150% |

There is no stable advantage over both pairing controls. CORR-S beats ADJ-S
in both GIST folds, but only by 0.107–0.454%; it loses to EA-S in the reverse
fold. SIFT changes sign against ADJ and loses to EA in both folds. These
small, inconsistent effects do not support a general pairing/local-PCA gain
in the tested residual subspace. This does not rule out every data-aware
representation or pairing method.

## Reporting boundaries and accounting notes

The four tables cover the requested experiment with no observed omission.
The review did not rehash every model archive or reopen the raw data members;
those are separate provenance checks. Both panels must be described as rebuilt
representations using recovered historical sample indices, not proven byte
recovery of the missing historical panels. Standalone runner metadata says
historical indices; the rebuild identity is supplied by the parent run's
configuration and panel provenance and should remain explicit in the report.

Shared model byte columns agree with the recorded allocations: 3,072 local
transform bytes + 128 pairing bytes + 128 bit-metadata bytes + eight bytes per
selected scalar center. Across the 48 arms these downstream model totals
range from 19,712 to 22,240 bytes. They are per shared model, not per vector,
and exclude upstream full-dimensional PCA and coarse quantizer storage.
The common vector payload is 64 bytes. NPZ archive size includes all candidate
codebooks and diagnostic overhead and is not the selected deployment size.

The diagnostic's own resource record is 118.090437 CPU seconds, 119.890905
wall seconds, and 108,146,688 bytes peak RSS. This excludes preparation and
recovery; the parent cumulative account must include those and must not add
this record a second time if the outer GNU-time wrapper is already counted.
Repeated pairing compute times on the four arm rows must not be summed.

The stopping result is limited to this reconstruction objective, these
historical sample indices, and GIST's 128-dimensional residual head. It is not
Recall/QPS evidence, a full-GIST finding, a novelty claim, or grounds to reject
all data-aware methods. No additional experiment is justified automatically
by these tables.

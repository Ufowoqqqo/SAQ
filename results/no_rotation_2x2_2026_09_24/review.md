# Read-only completed-result review

Checked all 16 summary rows, four contrasts, 3,840 allocation rows, 21,120 fit-curve rows, and all four per-vector NPZ files. This review only reads recorded outputs and recomputes arithmetic; it does not rerun DP, encoding, tests, or experiments.

## Outcome

No inconsistency was found. In every dataset/fold and both rotation conditions, ADAPTIVE selects exactly the same widths as UNIFORM. All reported changed-pair counts are zero. Allocation gains are exactly zero, and identity has higher measured rescaled reconstruction SSE than the fixed QR control.

| Dataset / fit→evaluation | Identity SSE/vector | QR SSE/vector | Identity gain vs QR |
| --- | ---: | ---: | ---: |
| SIFT A_TO_B | 896.463668346 | 533.171801685 | -68.137862039% |
| SIFT B_TO_A | 902.256469686 | 537.430456066 | -67.883390214% |
| GIST A_TO_B | 0.00855326411416 | 0.00720069217767 | -18.783915534% |
| GIST B_TO_A | 0.00856235442891 | 0.00721451941391 | -18.682256401% |

Negative gain means removing QR increases error relative to QR: approximately 67.88–68.14% on SIFT and 18.68–18.78% on full-dimensional GIST. UNIFORM and ADAPTIVE yield the same comparison because they select identical codes and widths in this run.

## Budget and data checks

| Dataset / fold | Common plan | Payload bits | Factor bits | Vector bytes | Positive pairs |
| --- | --- | ---: | ---: | ---: | ---: |
| sift A_TO_B | `0:128:4` | 512 | 64 | 72 | 64 |
| sift B_TO_A | `0:128:4` | 512 | 64 | 72 | 64 |
| gist A_TO_B | `0:64:11|64:256:6|256:576:4|576:832:2|832:960:0` | 3648 | 256 | 488 | 416 |
| gist B_TO_A | `0:64:11|64:256:6|256:576:4|576:832:2|832:960:0` | 3648 | 256 | 488 | 416 |

- Each context contains exactly the four intended arms, with the same segment plan and payload/factor budget. Plans cover every dimension, and zero-bit tails produce no allocation rows.
- All positive pairs occur exactly once in each arm, use widths in 1..11, have the expected source coordinates and original segment widths, and satisfy every segment payload sum.
- Adaptive shared width metadata equals one byte per positive pair (64 bytes on SIFT; 416 bytes on GIST), outside the per-vector payload.
- All raw fit curves contain every width in 1..11 for each pair/rotation, with finite nonnegative values.
- Every NPZ contains 12 finite, nonnegative arrays of 8,192 held-out values: three metrics for each arm. All 48 array means exactly equal their summary entries; maximum absolute mean discrepancy is 0.
- All 24 UNIFORM/ADAPTIVE array comparisons (four contexts × two rotations × three metrics) are exactly equal, not merely close in mean. The summary changed-pair counts, recorded allocations, and per-vector loss arrays agree.
- All six derived contrast columns reproduce exactly from the summary primary metric.

## Saved fit-objective comparison

For each rotation and context, sum the saved nearest-lattice fit cost at the recorded selected width of each pair. This is a direct table lookup, not an independent rerun of the optimizer.

| Dataset / fold | Rotation | Uniform fit SSE | Selected fit SSE | Selected − uniform |
| --- | --- | ---: | ---: | ---: |
| sift A_TO_B | IDENTITY | 7721652.45411 | 7721652.45411 | 0 |
| sift A_TO_B | QR | 4624625.58763 | 4624625.58763 | 0 |
| sift B_TO_A | IDENTITY | 7682459.38158 | 7682459.38158 | 0 |
| sift B_TO_A | QR | 4588624.22935 | 4588624.22935 | 0 |
| gist A_TO_B | IDENTITY | 66.2024379651 | 66.2024379651 | 0 |
| gist A_TO_B | QR | 45.8893407297 | 45.8893407297 | 0 |
| gist B_TO_A | IDENTITY | 66.8420904231 | 66.8420904231 | 0 |
| gist B_TO_A | QR | 45.8442893274 | 45.8442893274 | 0 |

Every saved selected objective equals its uniform objective exactly. The implementation deliberately prefers the incumbent when its objective exactly equals the DP optimum; the output therefore does not establish uniqueness of the optimum or rule out tied alternative allocations.

## Interpretation and limits

The proposed no-rotation mechanism receives no support in this fixed experiment. Removing this segment-local QR does not make the tested nearest-lattice allocator choose different widths, and it worsens the measured explicit CAQ-rescaled SSE. Both prespecified ≥5% flags are false. The defensible action is to stop this tested no-rotation/adaptive-allocation formulation without starting a follow-up automatically.

This remains a float64 encoder prototype with fixed global PCA/residual inputs, one deterministic Gaussian-QR construction, an additive nearest-lattice fit proxy, and a coupled adjusted/rescaled evaluation loss. The observed zero allocation gain is not an oracle impossibility result for all allocations or transforms. Per-vector payload/factor matching is not complete production-memory accounting, and production bitwise equivalence, Recall/QPS, and novelty remain unestablished. GIST in this run uses all 960 dimensions, unlike the previous 128-dimensional scalar diagnostic. The historical row selection is reused; the fold directions are not independent datasets.

## Review resources and scope

Analysis ran with affinity core 0 and OPENBLAS/OMP/MKL/NUMEXPR thread settings of one, under a 60-second wall limit. It did not invoke the experimental encoder or allocator.
Review Python CPU consumed before writing: 0.155417 seconds; peak RSS: 62939136 bytes.
Recorded audit issues: 0.

# Correlated-pair allocation representation-stage attribution

Date: 2026-09-03

Branch/base: `saq-correlated-pair-allocation` from `d305578`

Evidence class: `BASE_ONLY_RECONSTRUCTION_DIAGNOSTIC`

## Question

The earlier raw-coordinate diagnostic asked whether a fixed 512-bit budget
should be redistributed between 64 two-dimensional groups. It found a
positive GIST adjacent-group result, but it did not establish that the effect
survives the PCA and IVF residual representation actually used by SAQ.

This attribution diagnostic applies the same frozen rows, folds, pairings,
local two-dimensional transform, quantizers, and allocation rule at four
representation stages:

1. raw coordinates;
2. the first 128 coordinates after the full-dimensional PCA;
3. the first 128 residual coordinates after full-dimensional IVF routing at
   `nlist=1024`; and
4. the corresponding residual coordinates at `nlist=4096`.

It tests whether the earlier GIST result was a raw-view artifact and whether
group marginal returns are better explained by within-group association or
by block-level rate--distortion statistics.

## Input and representation recovery

The official TexMex archives were downloaded and matched the identities in
the historical binding:

| Object | Bytes | SHA-256 |
| --- | ---: | --- |
| `sift.tar.gz` | 168,280,445 | `92f1270c5e3a0cb46b89983e72b0511e4df065c31a9fa0276d8c9b1fca5bc81a` |
| `gist.tar.gz` | 2,740,172,684 | `01469a7f1c3768853525e543d537e2dfa1adece927616405e360952e3f67df73` |
| SIFT learn | 51,600,000 | `331bc82b6a0e89465776a3ba0c2113e0bd0cceaa014ec3ed639bc8b981af72ea` |
| SIFT base | 516,000,000 | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| GIST learn | 1,922,000,000 | `9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17` |
| GIST base | 3,844,000,000 | `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0` |

Only the four learn/base members were extracted. No benchmark query or
ground-truth member was extracted or read. The pinned Faiss submodule is
commit `0ca9df4792b173d573044ee14ca0704780176e82` (`v1.14.3`).

The existing `structured_2d_prepare_common` path rebuilt the full-dimensional
PCA, `nlist={1024,4096}` coarse quantizers, transformed base, and saved base
assignments. Its internal serialization/load parity passed for both datasets.
The focused stage extractor additionally replayed raw-to-PCA conversion for
256 selected rows and independently searched both serialized coarse indexes.
All 512 coarse labels per dataset agreed with the saved assignments. Maximum
raw-to-saved-PCA absolute differences were `1.22070e-4` for SIFT and
`2.14577e-6` for GIST, within the fixed mixed absolute/relative tolerance.

The selected-index identities are:

- SIFT: `a5ef3954b0d240e9b5fcf59690a559d458b6f05b7c55ca3c0e6bdb648c61a104`;
- GIST: `5cb6868406e6f184abe689058992ab9e8aba52a312c64aa34345a51e7826966d`.

## Frozen diagnostic

Each dataset uses 16,384 deterministic base rows, split into two folds. Each
fold is used once for fitting and once for held-out evaluation. At every
stage, `CORR_GREEDY`, `EA`, and `ADJ` form 64 disjoint coordinate pairs. A
local two-dimensional PCA and deterministic one-dimensional Lloyd curves are
fit for group budgets 6--10 bits. The exact dynamic program assigns exactly
512 bits across the 64 groups. The comparison is against uniform eight-bit
groups under the same pairing. The materiality threshold remains a 5%
held-out reconstruction-SSE reduction in both fold directions.

`CORR_GREEDY` tests strongest-correlation pairing, `EA` is the two-coordinate
OPQ-P Eigenvalue Allocation specialization, and `ADJ` uses fixed adjacent
coordinates. Pairing and cross-group allocation are separate effects.

## Result

The table reports the mean held-out gain across the two fit/evaluation
directions; both individual fold results are shown in parentheses.

| Dataset | Stage | `CORR_GREEDY` | `EA` | `ADJ` |
| --- | --- | ---: | ---: | ---: |
| SIFT1M | raw | 4.867% (4.870, 4.864) | 1.984% | 2.875% |
| SIFT1M | PCA head | 26.618% (27.914, 25.322) | 1.747% | 40.590% |
| SIFT1M | residual 1024 | 20.496% (19.634, 21.357) | 0.057% | 22.545% |
| SIFT1M | residual 4096 | 18.756% (18.825, 18.688) | 0.032% | 20.109% |
| GIST1M | raw head | 1.514% (1.487, 1.541) | 0.138% | 5.802% |
| GIST1M | PCA head | 20.982% (20.786, 21.178) | 8.788% | 30.815% |
| GIST1M | residual 1024 | 9.417% (10.073, 8.761) | 0.533% | 13.934% |
| GIST1M | residual 4096 | 8.796% (9.598, 7.994) | 0.411% | 11.725% |

The positive GIST adjacent-group result therefore survives both PCA and IVF
residualization and clears the frozen 5% screen in both folds at both nlist
values. It also appears on official SIFT1M after PCA/residualization. The
effect is not specific to strong-correlation pairing: fixed adjacent groups
give the larger allocation gain at every transformed stage.

After PCA, the two folds' strongest-correlation matchings overlap in only
1/64 pairs on both datasets, compared with 46/64 on raw GIST and 52/64 on raw
SIFT. Residual overlap remains only 8--14/64. The PCA has intentionally
removed most stable linear association, so selecting pairs by the largest
remaining sample correlations is unstable even though reallocating bits
between fixed groups remains useful.

For adjacent residual groups, correlation between total group variance and
the held-out 7-to-8/8-to-9-bit marginal gains is `0.966--0.995` on GIST and
`0.990--0.995` on SIFT. The corresponding correlation with absolute Pearson
association is only `0.041--0.089` on GIST and `0.246--0.306` on SIFT.
Covariance determinant is also strongly predictive (`0.921--0.966`). These
are descriptive cross-group correlations, not a causal or novelty claim.

## Decision and claim boundary

Decision: `RESIDUAL_BLOCK_ALLOCATION_SIGNAL_CONFIRMED`, with
`STRONGEST_CORRELATION_PAIRING_NOT_SUPPORTED`.

The evidence supports investigating allocation *between fixed
two-dimensional groups* in the actual SAQ residual representation. It does
not support choosing those groups by strongest Pearson correlation, and it
does not yet establish an ANN improvement. Reconstruction SSE can differ from
Recall, the local transform/quantizer is diagnostic rather than a production
consumer, and no query work, index-byte overhead, construction overhead, or
Recall/QPS frontier was measured.

Before implementation, the next scientific step is a closest-primary-work
review of transform coding and block-level adaptive bit allocation, followed
by a static mapping check against SAQ's fixed representation and estimator.
That review must distinguish a possible SAQ-specific mechanism from applying
known variance/rate--distortion allocation to SAQ parameters.

## Reproduction and resources

The archives came from `ftp://ftp.irisa.fr/local/texmex/corpus/`. Hashes were
verified with `sha256sum` before the following member-limited extraction:

```bash
tar -xzf /tmp/correlated-pair-allocation/downloads/sift.tar.gz \
  -C /tmp/correlated-pair-allocation/downloads/extracted \
  sift/sift_learn.fvecs sift/sift_base.fvecs
tar -xzf /tmp/correlated-pair-allocation/downloads/gist.tar.gz \
  -C /tmp/correlated-pair-allocation/downloads/extracted \
  gist/gist_learn.fvecs gist/gist_base.fvecs
```

The common state and ordered stage panels were then built with:

```bash
/tmp/correlated-pair-allocation/build/structured_2d_prepare_common \
  sift /tmp/correlated-pair-allocation/downloads/extracted/sift/sift_learn.fvecs \
  /tmp/correlated-pair-allocation/downloads/extracted/sift/sift_base.fvecs \
  /tmp/correlated-pair-allocation/common/sift
/tmp/correlated-pair-allocation/build/structured_2d_prepare_common \
  gist /tmp/correlated-pair-allocation/downloads/extracted/gist/gist_learn.fvecs \
  /tmp/correlated-pair-allocation/downloads/extracted/gist/gist_base.fvecs \
  /tmp/correlated-pair-allocation/common/gist
python -B research/correlated_pair_allocation/write_indices.py \
  --output /tmp/correlated-pair-allocation/indices
/tmp/correlated-pair-allocation/build/correlated_pair_extract_stages \
  /tmp/correlated-pair-allocation/downloads/extracted/sift/sift_base.fvecs \
  /tmp/correlated-pair-allocation/common/sift 128 \
  /tmp/correlated-pair-allocation/indices/sift_indices.u64 \
  /tmp/correlated-pair-allocation/stages-v2/sift
/tmp/correlated-pair-allocation/build/correlated_pair_extract_stages \
  /tmp/correlated-pair-allocation/downloads/extracted/gist/gist_base.fvecs \
  /tmp/correlated-pair-allocation/common/gist 960 \
  /tmp/correlated-pair-allocation/indices/gist_indices.u64 \
  /tmp/correlated-pair-allocation/stages-v2/gist
```

The accepted diagnostic command was:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
MKL_NUM_THREADS=1 python -B \
  research/correlated_pair_allocation/diagnostic.py \
  --sift /tmp/correlated-pair-allocation/downloads/extracted/sift/sift_base.fvecs \
  --gist /tmp/correlated-pair-allocation/downloads/extracted/gist/gist_base.fvecs \
  --sift-stages /tmp/correlated-pair-allocation/stages-v2/sift \
  --gist-stages /tmp/correlated-pair-allocation/stages-v2/gist \
  --output /tmp/correlated-pair-allocation/stage-diagnostic-v1 --frozen
```

The complete run used 465.8 CPU-seconds, 467.4 wall-seconds, and at most
1,032,011,776 bytes RSS. A second run under `stage-diagnostic-v2` reproduced
metadata, complete correlation tables, curves, selected-pair tables, and
summaries byte for byte; only runtime/RSS records differed. Across both
datasets and four stages, all 48 fold/plan allocations contain 64 groups and
sum to exactly 512 bits.

Common-state rebuilding used about 5,921 CPU-seconds, completed in about 5.4
wall-minutes through existing parallelism, and peaked at 4,865,392,640 bytes
RSS. The two accepted diagnostics add about 932 CPU-seconds. Total measured
compute remains below 2 CPU-hours and peak RSS below 5 GiB, within the frozen
4 CPU-hour, 6 wall-hour, and 16 GiB limits. Generated archives, datasets,
common state, stage panels, and result tables remain under `/tmp` and are not
committed.

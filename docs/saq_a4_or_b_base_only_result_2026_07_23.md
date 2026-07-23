# A4-OR-B base-only result

Date: 2026-07-23

Result: **`NO_GO_BASE_ONLY`**

This experiment tested whether arbitrary-cardinality scalar products recover a
material part of the error caused by forcing each two-coordinate lookup word
to use dyadic scalar cardinalities. Both registered datasets completed through
the D/A/P/V paths at B4 and B8. The candidate did not pass any dataset/rate
cell's materiality requirement, so this formulation must not proceed to
benchmark-query or native scan evaluation.

## Input correction and identity

The inherited inventory required two fitting and two held-out rows from every
one of 512 IVF cells. The content-identified assignments make that impossible:
GIST has 168 cells with fewer than four rows; CIFAR has two. Before fitting any
model, the sampling frame was corrected to cells with at least four rows.
Within eligible cells, the registered SHA-256 ordering, even/odd pool split,
two-row reserve, proportional largest-remainder allocation, 8,192/8,192 split
sizes, and within-cell pairing remained unchanged.

| Dataset | Eligible cells | Excluded cells/rows | Pairs | Inventory SHA-256 | Panel fingerprint |
| --- | ---: | ---: | ---: | --- | ---: |
| GIST | 344 | 168 / 219 | 4,016 | `cf1fee18de70e8680e210149ce48c4fbd27012ae254c4e272924d079e3c5d5f9` | `12566436008583307242` |
| CIFAR | 510 | 2 / 3 | 3,962 | `f76d7a3689379103e1b18116fa5efc985ab3bce5453701b2707a84ffba4a830b` | `1974200637105606499` |

The GIST inputs matched the three registered hashes. The missing CIFAR inputs
were reproduced from the raw 60,000-by-512 base using the historical PCA/IVF
procedure. The default FlexiBLAS OpenBLAS-OpenMP path reproduced all three
registered hashes exactly:

```text
base       2019cfa391c5d10742a9963b6dc3d28d633097632b7bb1acde737caa6d314845
centroids  ad4498c3b67a1ab598eb47bee560133a3d6ca46a7867db29ffb55ce53b3c9827
cell ids   3168f05171f74afb175c50a0ec9e584b0f666b157fbedba6d3841cc2e43107e9
```

A one-thread BLAS reproduction generated the same cell-id hash but different
PCA/centroid bytes. Those files were rejected. Input preparation is not
training-performance evidence.

## Correctness and numerical checks

The Release build used GCC 11.5.0, pinned Faiss
`0ca9df4792b173d573044ee14ca0704780176e82`, and:

```text
-O3 -fno-fast-math -ffp-contract=off -frounding-math -mfpmath=sse
```

The runner uses one process and one thread, establishes `FE_TONEAREST`, clears
x86 FTZ/DAZ, and keeps hashing and TSV output outside model timing. Both runs
passed model shape, encoding, final fitting occupancy for P/V, serialized
center collision, finite-value, direct-versus-sufficient replay, and
H1024-versus-H2048 decision-sign checks.

| Dataset | Maximum per-vector replay discrepancy | Limit | Sensitivity |
| --- | ---: | ---: | --- |
| GIST | `3.47e-18` | `1.13e-6` | same decisions |
| CIFAR | `1.73e-18` | `4.61e-7` | same decisions |

## Point results

`G` is the fraction of dyadic reconstruction error removed by A. `C` is the
fraction of the D-to-V opportunity closed by A. `Q` is the fractional
improvement in the base-pair absolute distance error. Passage required more
than 5% for `G` and `Q`, more than 50% for `C`, at least 48 positive groups,
and a minimum leave-one-group-out `G` of at least 5%.

| Dataset/rate | `G` | `C` | `Q` | Positive groups | Minimum leave-one-group-out `G` |
| --- | ---: | ---: | ---: | ---: | ---: |
| GIST B4 | 0% | 0% | 0% | 0 / 64 | 0% |
| GIST B8 | 0.0928% | 0.5396% | 0.1237% | 7 / 64 | -0.0317% |
| CIFAR B4 | 0% | 0% | 0% | 0 / 64 | 0% |
| CIFAR B8 | -0.0455% | -0.4186% | -0.1252% | 6 / 64 | -0.0536% |

At B4, A and D selected `(4,4)` for all 64 groups in both datasets. At B8,
GIST selected a non-dyadic `(15,17)` or `(17,15)` split in 14 groups and CIFAR
did so in eight groups. The training objective therefore activated the larger
feasible set, but the selections did not generalize to material held-out
reconstruction or base-pair gains.

The trained block control exposed a real two-dimensional opportunity in every
cell: D-to-V reconstruction reductions were about 11.4%/17.2% for GIST B4/B8
and 8.8%/10.9% for CIFAR B4/B8. A closed essentially none of that opportunity.
This separates “no useful structure exists” from the supported conclusion:
the structure is not captured by changing only the two scalar cardinalities.

## Statistical and cost results

The corrected eligible-cell two-stage bootstrap used 10,000 replicates and
PCG64 seed 20260713. Cell matrices were generated in GIST/CIFAR order for each
dataset's eligible frame; within-cell row and pair draws were shared across
arms and rates. A second complete run reproduced both TSVs byte for byte:

```text
bootstrap.tsv  2eecbc925fddf280b14cea28115c0dbf400c6a0e5d2792d9c0cb34eb6a3b67d7
points.tsv     a9c94d790bd4307118d7fababb933786c74025bdbd94e3074b5b04cd6110d190
```

Only the four `L_V` hypotheses passed Holm across the fixed 20-hypothesis
family. Every `L_G`, `L_C`, and `L_Q5` failed. B4 `L_P` failed in both
datasets; the two positive B8 `L_P` raw p-values did not survive Holm.

A's model was 2,304 bytes at B4 and 8,448 bytes at B8 versus 131,072 bytes for
P, so the model-byte advantage exceeded twofold. H1024 scalar fitting took
169.9 seconds on GIST and 168.0 seconds on CIFAR. Its worst fit-time ratio to P
was 1.96, below the twofold regression ceiling. The cost condition therefore
passed, but it cannot compensate for failed quality conditions.

The complete GIST run took 24:31 wall time and the CIFAR run 22:25 on an Intel
Core i9-10920X, each pinned to CPU 0. Peak RSS was about 205 MiB. H2048
brute-force DP dominated runtime (794 and 776 CPU seconds); a publishable
positive direction would need the allowed Monge/SMAWK or divide-and-conquer
implementation. Because the scientific gate failed decisively, optimizing
that solver now would be artifact engineering rather than useful research.

## P/V adequacy and claim boundary

At B8, P and V share the same 64-by-2D, 256-center model class, but V obtained
lower fitting SSE than P on both datasets. V used the candidate-derived start
plus seven independent starts, whereas P used the pinned conventional
eight-redo path. This shows that the P training path is not an optimizer
adequacy oracle and prevents overclaiming P competitiveness. It does not
rescue A: the stronger V control is exactly the opportunity denominator, and
A failed both the 5% absolute materiality and 50% closure conditions by large
margins.

The result is conditional on the eligible-cell sampling frame and fixed
128-coordinate panel. It is base-only evidence, not Recall, ranking, QPS,
full-vector ANN, or unchanged-SAQ evidence. It supports closing this precise
arbitrary-cardinality scalar-product formulation. It does not show that all
ways of modeling pairwise dependence are useless.

## Reproduction commands

```bash
cmake -S research/a4_or_b -B /tmp/a4-or-b-build \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF -DFAISS_ENABLE_C_API=OFF \
  -DFAISS_ENABLE_EXTRAS=OFF -DFAISS_ENABLE_GPU=OFF \
  -DFAISS_ENABLE_MKL=OFF -DFAISS_ENABLE_PYTHON=OFF \
  -DFAISS_ENABLE_RAFT=OFF -DFAISS_OPT_LEVEL=generic \
  -DBLA_VENDOR=OpenBLAS \
  -DBLAS_LIBRARIES=/usr/lib64/libopenblaso-r0.3.29.so \
  -DLAPACK_LIBRARIES=/usr/lib64/libopenblaso-r0.3.29.so
cmake --build /tmp/a4-or-b-build --target \
  a4_or_b_panel_smoke a4_or_b_models_test a4_or_b_runner -j 1
ctest --test-dir /tmp/a4-or-b-build --output-on-failure

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/a4-or-b-build/a4_or_b_runner \
  gist_sample50k_k512 \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_centroid_512_pca.fvecs \
  /rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_cluster_id_512.ivecs \
  /tmp/a4_or_b_gist_inventory.tsv 50000 960 \
  /tmp/a4-or-b-gist-run1

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  OMP_DYNAMIC=FALSE taskset -c 0 \
  /tmp/a4-or-b-build/a4_or_b_runner \
  cifar60k_k512 \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_base_pca.fvecs \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_centroid_512_pca.fvecs \
  /tmp/a4-or-b-cifar-inputs-default/cifar60k_cluster_id_512.ivecs \
  /tmp/a4_or_b_cifar_inventory.tsv 60000 512 \
  /tmp/a4-or-b-cifar-run1

python script/a4_or_b_statistics.py \
  --gist /tmp/a4-or-b-gist-run1 \
  --cifar /tmp/a4-or-b-cifar-run1 \
  --output-dir /tmp/a4-or-b-statistics-run1
```

The inventory commands use `script/a4_or_b_inventory.py` with the explicit
`eligible-min4-v1` rule and the dataset ids shown above. CIFAR input
reproduction uses `script/a4_or_b_prepare_cifar.py` with the raw base and an
empty output directory; it intentionally uses the historical default
FlexiBLAS threading because that is required for the registered byte hashes.
Generated row/pair outputs remain under `/tmp` and are not repository
artifacts.

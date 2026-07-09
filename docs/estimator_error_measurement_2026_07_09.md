# Data-Only Distance-Estimator Error Measurement

## Question

The previous planner-proxy measurement found that SAQ's variance objective,

```text
sum(segment_variance) / 2^bits
```

strongly ranks residual quantization SSE, but is weaker for pure direction
loss. This study asks whether that direction-quality mismatch matters for the
actual CAQ/SAQ distance estimator in a query-unaware setting.

The measurement does not use benchmark queries, ground truth, or query labels.
It uses only base vectors, PCA artifacts, IVF centroids, and IVF assignments.

## Measurement Definition

For each dataset, the driver samples base vectors deterministically, converts
them to IVF residuals, and constructs ordered residual pairs inside the same
IVF cluster. One residual acts as a data vector `o`; the other acts as a
data-only pseudo-query residual `q`.

For a segment, CAQ encodes `o` into `o_a`. The measured estimator is the same
rescale form used by CAQ accurate distance estimation:

```text
ip_est(q,o) = (||o||^2 / <o,o_a>) * <q,o_a>
dist_est(q,o) = ||q||^2 + ||o||^2 - 2 * ip_est(q,o)
dist_true(q,o) = ||q-o||^2
```

For a zero-bit segment, no inner-product code exists, so `ip_est = 0` and the
segment contributes `||q||^2 + ||o||^2`, matching the dropped-segment estimator
behavior.

The new tools are:

- `bin/measure_estimator_error`, built from `src/measure_estimator_error.cpp`.
- `script/summarize_estimator_error.py`.

The driver enumerates every contiguous 64-dimensional block interval and every
bit width from 0 to 13. For each segment/bit pair, it records:

- SAQ proxy risk: `variance_sum / 2^bits`;
- raw and scale-aligned CAQ SSE for the encoded data residual;
- direction loss: `1 - cos(o,o_a)^2`;
- CAQ `fac_error`;
- mean absolute and squared inner-product estimator error;
- mean absolute, squared, and relative squared-distance contribution error.

The summarizer reports rank agreement and incremental rank-R2. The incremental
view asks whether adding direction loss or `fac_error` explains estimator error
after a proxy-only rank model has already been fit.

## Data And Cost

The first run uses deterministic random rotation, 2048 sampled rows, and a
2048 same-cluster pair budget. The pair budget is a measurement budget, not a
planner hyperparameter.

| dataset | IVF setting | sample rows | pair count | candidates | approximate measurement time |
|---|---:|---:|---:|---:|---:|
| GIST sample100k | K512 | 2048 | 2048 | 1680 | 25.5s |
| CIFAR60K | K512 | 2048 | 2048 | 504 | 4.2s |
| DEEP sample100k | K512 | 2048 | 2048 | 140 | 0.7s |
| audio K4096 | K4096 | 2048 | 1300 | 84 | 0.2s |
| word2vec sample100k | K512 | 2048 | 2048 | 210 | 1.3s |

Audio uses fewer pairs because K4096 creates many singleton clusters under the
2048-row sample. This should be treated as a measurement limitation if audio
becomes central to a later claim.

## Main Result

For absolute inner-product and squared-L2 contribution error, `mean_abs_l2_error`
is exactly twice `mean_abs_ip_error` under this segment-level estimator, so the
table below reports only the L2 form. Values are within-bit means, which remove
the trivial effect that lower bit width has larger error.

| dataset | SAQ proxy Spearman | direction-loss Spearman | fac-error Spearman | proxy rank-R2 | direction R2 gain | fac-error R2 gain |
|---|---:|---:|---:|---:|---:|---:|
| audio K4096 | 0.7347 | -0.3319 | 1.0000 | 0.5102 | 0.4723 | 0.4898 |
| CIFAR60K | 0.9538 | 0.3171 | 0.9982 | 0.9033 | 0.0614 | 0.0932 |
| DEEP sample100k | 0.8459 | -0.0312 | 0.9897 | 0.6957 | 0.2368 | 0.2849 |
| GIST sample100k | 0.9756 | 0.3408 | 0.9993 | 0.9495 | 0.0388 | 0.0491 |
| word2vec sample100k | 0.9898 | 0.7970 | 0.9934 | 0.9792 | 0.0017 | 0.0123 |

The main observations are:

1. SAQ's variance proxy remains strong for absolute estimator error on GIST,
   CIFAR, and word2vec.
2. The proxy is weaker on audio and DEEP under this measurement.
3. Direction loss alone is not a reliable standalone predictor. It is negative
   on audio and DEEP, weak on CIFAR/GIST, and strong only on word2vec.
4. CAQ `fac_error` almost perfectly ranks absolute estimator error across all
   five datasets.

The `fac_error` result is not surprising: it combines residual energy and the
same directional term used by the CAQ estimator analysis. It is nevertheless
important because it is data-only and directly measurable during offline
encoding.

## Relative Error Caveat

Relative squared-distance contribution error behaves differently. Within a
fixed bit width, SAQ proxy and direction loss are often negatively correlated
with relative error. This is mostly a denominator effect: high-energy segments
can have larger absolute error but smaller relative error because their true
distance contribution is also larger.

This means relative segment error is a poor standalone planner objective unless
the final ranking objective explicitly normalizes by segment contribution. A
reviewer would likely reject a relative-error-only objective as misaligned with
top-k distance estimation.

## Strict-Reviewer Interpretation

This measurement does not justify a direction-loss-only SAQ planner. Direction
loss exposed a mismatch in the previous quantization study, but it does not
stably rank absolute estimator error by itself.

The stronger signal is narrower:

```text
SAQ's variance proxy is already strong for energy-weighted absolute estimator
error on several datasets, but a directly measured CAQ fac-error objective can
explain the remaining data-only estimator-error ranking more accurately.
```

A strict reviewer would immediately ask whether this is merely a tautological
measurement of CAQ's own error factor and whether the offline cost is justified.
Therefore the next step should not be a broad planner sweep. It should be a
small falsification study:

1. derive a fac-error-based global objective using only data/index artifacts;
2. compare its selected global plan against SAQ's variance-DP plan offline;
3. stop if the selected plan is identical, near-identical, or fails to improve
   safe-search recall/QPS after one end-to-end check.

## Commands

Example measurement command:

```bash
bin/measure_estimator_error \
  -case_label=gist_sample100k_estimator_2048 \
  -dataset=gist_sample100k \
  -data_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_base_pca.fvecs \
  -vars_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_base_pca.vars.fvecs \
  -centroids_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_centroid_512_pca.fvecs \
  -cids_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_cluster_id_512.ivecs \
  -max_rows=2048 \
  -max_pairs=2048 \
  -min_bits=0 \
  -max_bits=13 \
  -rand_rotate=true \
  -output_csv=/tmp/saq-run/estimator_error/gist_sample100k_estimator_2048.csv
```

Summary command:

```bash
python script/summarize_estimator_error.py \
  --inputs /tmp/saq-run/estimator_error/*_estimator_2048.csv \
  --output-prefix /tmp/saq-run/estimator_error/residual_estimator_2048_summary
```

Generated CSV and summary artifacts are under `/tmp/saq-run/estimator_error/`
and are not committed.

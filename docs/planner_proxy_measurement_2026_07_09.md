# Planner Proxy Measurement

## Question

Does SAQ's global planner proxy,

```text
sum(segment_variance) / 2^bits
```

preserve the ranking of actual data-only CAQ/SAQ segment error?

This is the first study under the planner-objective direction. It does not use
benchmark queries and does not build new indexes. The purpose is to decide
whether there is evidence for replacing SAQ's DP objective, or whether the SAQ
proxy is already faithful for the relevant data-only error quantities.

## Measurement Driver

Two tools were added:

- `bin/measure_planner_proxy`, built from `src/measure_planner_proxy.cpp`.
- `script/summarize_planner_proxy.py`.

The C++ driver enumerates all contiguous 64-dimensional block intervals and all
bit widths from 0 to 13. For each segment/bit pair, it computes:

- SAQ proxy risk: `variance_sum / 2^bits`;
- measured CAQ raw SSE;
- measured scale-aligned SSE, where the quantized vector may be optimally
  rescaled before measuring error;
- measured direction loss, `1 - cos(o, o_a)^2`;
- CAQ-style error factor using the same directional term as the encoder.

The first run uses IVF residual vectors, because those are the vectors actually
encoded during SAQ index construction. It uses deterministic per-segment random
rotation and a deterministic 1024-row sample per dataset. The row sample is a
measurement budget, not a method parameter; it is recorded in every output row.

Generated CSV artifacts are under `/tmp/saq-run/planner_proxy/` and are not
committed.

## Datasets

| dataset | source | sample rows | candidates |
|---|---|---:|---:|
| GIST sample100k | IVF residual | 1024 | 1680 |
| CIFAR60K | IVF residual | 1024 | 504 |
| DEEP sample100k | IVF residual | 1024 | 140 |
| audio K4096 | IVF residual | 1024 | 84 |
| word2vec sample100k | IVF residual | 1024 | 210 |

The candidate count equals the number of contiguous 64-block intervals times
14 bit widths, except `mean_fac_error` excludes zero-bit rows in the summary.

## Main Result

The SAQ proxy strongly preserves the ranking of energy-weighted residual error.
This weakens the hypothesis that a simple replacement objective based on
measured raw or aligned SSE will produce a substantially different planner.

| dataset | aligned-SSE Spearman, all bits | aligned-SSE Spearman, within-bit mean | aligned-SSE discordant pairs, within-bit mean |
|---|---:|---:|---:|
| audio K4096 | 0.9113 | 1.0000 | 0.0000 |
| CIFAR60K | 0.9624 | 0.9979 | 0.0080 |
| DEEP sample100k | 0.9651 | 1.0000 | 0.0000 |
| GIST sample100k | 0.9684 | 0.9981 | 0.0123 |
| word2vec sample100k | 0.9917 | 0.9452 | 0.0782 |

The fixed-bit view is important. It removes the trivial signal that lower bit
widths have larger error. Even within a fixed bit width, the SAQ proxy almost
perfectly ranks raw and aligned SSE on GIST, CIFAR, DEEP, and audio, and remains
strong on word2vec.

## Direction-Specific Evidence

The proxy is less faithful for pure direction loss, which removes most vector
magnitude information. This does not immediately imply a better planner,
because SAQ's objective is energy-weighted and the distance estimator error is
not simply direction loss. It does identify the only visible gap in this first
measurement.

| dataset | direction-loss Spearman, within-bit mean | fac-error Spearman, within-bit mean |
|---|---:|---:|
| audio K4096 | 0.4769 | 0.7143 |
| CIFAR60K | 0.5516 | 0.9505 |
| DEEP sample100k | 0.5189 | 0.8294 |
| GIST sample100k | 0.5234 | 0.9753 |
| word2vec sample100k | 0.7412 | 0.9838 |

The interpretation is nuanced:

- For raw SSE and scale-aligned SSE, SAQ's variance proxy is very strong.
- For direction-only error, the proxy is much weaker.
- For CAQ-style error factor, agreement is usually strong, except audio is only
  moderate.

This suggests that a replacement DP objective based only on measured SSE is
unlikely to be novel or useful. A possible next question is whether the
direction-only mismatch matters for actual distance estimation after the CAQ
rescale/error factors are applied.

## Strict-Reviewer Interpretation

A strict reviewer would not accept this as evidence for a new planner yet. The
strong aligned-SSE agreement says SAQ's original proxy is already doing the
obvious data-only job well. The direction-loss mismatch is interesting, but it
could be irrelevant if magnitude-weighted estimator error is still well
predicted by variance risk.

Therefore the current evidence supports this limited claim:

```text
SAQ's variance-risk objective is faithful for energy-weighted residual
quantization error, but incomplete for pure direction-quality ranking.
```

The next study should test whether that direction-quality mismatch predicts
distance-estimation error in a query-unaware way. If it does not, this planner
objective direction should stop before proposing a new weighted objective.

## Commands

Example measurement command:

```bash
/rwproject/kdd-db/kluaq/saq/bin/measure_planner_proxy \
  -case_label=gist_sample100k_residual_proxy_1024 \
  -dataset=gist_sample100k \
  -data_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_base_pca.fvecs \
  -vars_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_base_pca.vars.fvecs \
  -centroids_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_centroid_512_pca.fvecs \
  -cids_file=/tmp/saq-run/data/gist_sample100k/gist_sample100k_cluster_id_512.ivecs \
  -max_rows=1024 \
  -min_bits=0 \
  -max_bits=13 \
  -rand_rotate=true \
  -output_csv=/tmp/saq-run/planner_proxy/gist_sample100k_residual_proxy_1024.csv
```

Summary command:

```bash
python script/summarize_planner_proxy.py \
  --inputs /tmp/saq-run/planner_proxy/*_residual_proxy_1024.csv \
  --output-prefix /tmp/saq-run/planner_proxy/residual_proxy_1024_summary_v2
```

## Next Step

Do not derive a new DP objective yet. First measure query-unaware
distance-estimation error on data-only vector pairs or residual pairs, then ask
whether direction loss explains estimator error beyond the current SAQ proxy.
The stop condition is strict: if direction loss does not add predictive power,
this branch should pivot away from planner-objective modification.

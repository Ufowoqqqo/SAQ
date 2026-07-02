# SAQ GIST Higher-Dimensional Segment Diagnostic

Date: 2026-07-02

This note records a higher-dimensional query-unaware segment diagnostic on GIST.
It follows `docs/saq_segment_diagnostic_2026_07_02.md`, where `audio` was used
as a low-dimensional plumbing sanity case. The goal here is to check whether the
same global-PCA-vs-local-residual mismatch is visible when SAQ's default dynamic
planner creates multiple segments.

## 1. Status And Scope

This is a diagnostic smoke run, not a full official SAQ GIST reproduction.

The local dataset directory contains raw GIST files:

```text
/rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs
/rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs
```

The current environment does not provide `faiss` or `sklearn`, so I did not run
the original SAQ preprocessing path for full GIST/K4096. Instead, I added a
fallback helper:

```text
script/prepare_sampled_pca_ivf.py
```

It reads a prefix sample from a `.fvecs` file, computes full-dimensional PCA with
NumPy, clusters leading PCA dimensions with a small Lloyd loop, and writes
SAQ-compatible artifacts for diagnostics:

```text
*_pca_mean.fvecs
*_pca_matrix.fvecs
*_base_pca.fvecs
*_base_pca.vars.fvecs
*_centroid_{K}_pca.fvecs
*_cluster_id_{K}.ivecs
```

The important limitation is that this is not the paper's exact faiss IVF setup.
It is still useful for testing the planner-level question because the diagnostic
uses only base/index statistics and SAQ's own quantization plan output.

## 2. Run Setup

Prepared sampled dataset:

```text
dataset = gist_sample100k
input = /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs
output_dir = /tmp/saq-run/data/gist_sample100k
sample_size = 100,000
dimension = 960
K = 512
cluster_dims = first 64 PCA dimensions
Lloyd iterations = 4
seed = 0
```

Fallback clustering summary:

| Statistic | Value |
| --- | ---: |
| cluster size min | 1 |
| cluster size p50 | 179.0 |
| cluster size p90 | 316.9 |
| cluster size max | 658 |
| empty_clusters | 0 |
| PCA top-1 variance share | 0.204557 |
| PCA top-64 variance share | 0.777028 |

The segment diagnostic used `min_cluster_size=2`, so one size-1 cluster was
skipped:

```text
used clusters = 511
skipped clusters = 1
cluster size p50 = 179.0
cluster size p90 = 316.9
cluster size max = 658
```

## 3. Commands

Prepare sampled PCA/IVF artifacts:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs \
  --output-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Run SAQ planner/index build for B in `{1,2,3,4}`:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_sample100k -K 512 -B ${B} -enable_PCA=true -logtostderr=1
```

Extract quantization plans:

```bash
script/extract_quant_plan.py \
  /tmp/saq-run/logs/gist_sample100k_K512_B${B}_create_index.stderr \
  --output /tmp/saq-run/logs/gist_sample100k_K512_B${B}_quant_plan.csv
```

Run segment diagnostics:

```bash
python script/segment_diagnostics.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --plan-csv /tmp/saq-run/logs/gist_sample100k_K512_B${B}_quant_plan.csv \
  --output /tmp/saq-run/reports/gist_sample100k_K512_B${B}_segment_diagnostics.csv \
  --summary-output /tmp/saq-run/reports/gist_sample100k_K512_B${B}_segment_diagnostics.summary.json
```

Note: B=3 emitted the dynamic bit-allocation plan and initialized the index, then
`create_index` exited with a segmentation fault before completing encoding. The
B=3 result below is therefore only a planner/diagnostic result, not an encoded
index result.

## 4. SAQ Dynamic Plans

| B | Dynamic plan |
| ---: | --- |
| 1 | `0-64: 6b; 64-320: 2b; 320-960: 0b` |
| 2 | `0-64: 8b; 64-256: 4b; 256-512: 2b; 512-960: 0b` |
| 3 | `0-64: 9b; 64-256: 5b; 256-576: 3b; 576-768: 1b; 768-960: 0b` |
| 4 | `0-64: 11b; 64-256: 6b; 256-576: 4b; 576-832: 2b; 832-960: 0b` |

The default planner is now non-trivial even at normal B values, unlike `audio`
B=2/4/8 where SAQ collapsed to one full segment.

## 5. Segment Diagnostic Results

Columns:

```text
global = segment share under global PCA variance
res_w = weighted mean segment share under cluster-local residual variance
res_p90 = 90th percentile cluster residual share
gap = res_w - global
top8 = top-8 dimension variance share inside the segment
```

### B=1

| Segment | Bits | global | res_w | res_p90 | gap | top8 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 6 | 0.777028 | 0.628754 | 0.715384 | -0.148274 | 0.624702 |
| 64-320 | 2 | 0.177822 | 0.299930 | 0.345713 | +0.122108 | 0.086360 |
| 320-960 | 0 | 0.045150 | 0.071316 | 0.111152 | +0.026166 | 0.041438 |

### B=2

| Segment | Bits | global | res_w | res_p90 | gap | top8 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 8 | 0.777028 | 0.628754 | 0.715384 | -0.148274 | 0.624702 |
| 64-256 | 4 | 0.159843 | 0.270398 | 0.309712 | +0.110555 | 0.096073 |
| 256-512 | 2 | 0.046879 | 0.075911 | 0.105156 | +0.029032 | 0.057059 |
| 512-960 | 0 | 0.016250 | 0.024937 | 0.043550 | +0.008687 | 0.043372 |

### B=3

| Segment | Bits | global | res_w | res_p90 | gap | top8 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 9 | 0.777028 | 0.628754 | 0.715384 | -0.148274 | 0.624702 |
| 64-256 | 5 | 0.159843 | 0.270398 | 0.309712 | +0.110555 | 0.096073 |
| 256-576 | 3 | 0.051822 | 0.083691 | 0.117427 | +0.031869 | 0.051616 |
| 576-768 | 1 | 0.008422 | 0.012826 | 0.023201 | +0.004404 | 0.061991 |
| 768-960 | 0 | 0.002884 | 0.004331 | 0.008176 | +0.001446 | 0.070784 |

### B=4

| Segment | Bits | global | res_w | res_p90 | gap | top8 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0-64 | 11 | 0.777028 | 0.628754 | 0.715384 | -0.148274 | 0.624702 |
| 64-256 | 6 | 0.159843 | 0.270398 | 0.309712 | +0.110555 | 0.096073 |
| 256-576 | 4 | 0.051822 | 0.083691 | 0.117427 | +0.031869 | 0.051616 |
| 576-832 | 2 | 0.009836 | 0.014951 | 0.027295 | +0.005114 | 0.053080 |
| 832-960 | 0 | 0.001470 | 0.002206 | 0.004121 | +0.000736 | 0.097397 |

## 6. Interpretation

The higher-dimensional smoke run supports the same query-unaware limitation as
the `audio` diagnostic, but with clearer multi-segment planner behavior.

First, the head segment is overweighted by global PCA variance relative to IVF
residuals. Dimensions `0-64` carry 77.7% of global PCA variance, but only 62.9%
of weighted cluster-local residual variance. This is consistent across all B
because the head boundary is the same.

Second, the first post-head segment is underrepresented by global variance. For
`64-256`, global PCA variance share is 16.0%, while weighted residual share is
27.0% and p90 residual share is 31.0%. For the B=1 boundary `64-320`, the same
pattern is 17.8% global versus 30.0% weighted residual and 34.6% p90 residual.

Third, the discarded tail still has a positive residual gap. At B=2, `512-960`
has only 1.6% global variance but 2.5% weighted residual share and 4.4% p90
residual share. The absolute share is small, but the direction is consistent.

A plausible reason is structural: the fallback IVF clustering uses leading PCA
dimensions, so clustering removes more variation from the high-variance head.
The remaining residual distribution shifts relatively more mass into middle and
tail PCA dimensions. SAQ's global variance-driven plan does not model this shift.

## 7. Research Implication

This gives a stronger data-only signal for the revised SAQ follow-up:

```text
SAQ's global PCA-variance plan can disagree with the local residual distribution
that is actually quantized inside IVF clusters.
```

This is query-unaware and remains inside the advisor's preferred scenario. The
most natural next method direction is not query-aware bit allocation. It is one
of:

1. residual-aware segment/bit planning using aggregate IVF residual statistics;
2. a small shared family of residual-aware plans assigned to clusters;
3. flexible segment boundaries that account for residual concentration after IVF
   clustering.

Before claiming an algorithmic contribution, this diagnostic should be repeated
with the official GIST preprocessing path, ideally full GIST/K4096 with faiss, so
that the result is not tied to the fallback K512 sampled setup.

## 8. Immediate Next Steps

Priority clarification after the residual-aware discussion:

1. Prototype residual-aware DP offline first, comparing its proposed plan against
   SAQ's default plan before changing encoding/search. This is now recorded in:

   ```text
   docs/saq_residual_aware_dp_prototype_2026_07_02.md
   ```

2. Add a minimal custom-plan injection path so the residual-aware plan can be
   encoded and evaluated against SAQ default on relative error / recall.
3. Reproduce the diagnostic on official SAQ-preprocessed GIST if faiss is
   available, or install/build the missing preprocessing dependency in a clean
   environment. This is required before making a strong research claim, but it
   does not need to block the offline/custom-plan prototype.
4. Investigate the B=3 `create_index` segmentation fault if it blocks useful
   odd-bit sweeps.

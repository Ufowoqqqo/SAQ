# Audio SAQ Quant-Plan Probe

Date: 2026-07-02

This is the first small probe after the SAQ-pivot meeting. It verifies that we
can extract SAQ's dynamic quantization plan and gives a first sanity check on
whether `audio` exposes non-trivial SAQ segmentation.

## Setup

Working directory:

```text
/tmp/saq-run
```

Binary:

```text
/rwproject/kdd-db/kluaq/saq/bin/create_index
```

Runtime dependency path:

```text
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64
```

Dataset files already present in `/tmp/saq-run/data/audio`:

```text
audio_base_pca.fvecs
audio_query_pca.fvecs
audio_centroid_4096_pca.fvecs
audio_cluster_id_4096.ivecs
audio_base_pca.vars.fvecs
```

These files came from the previous smoke setup. This probe is still a local
sanity check, not a formal SAQ benchmark.

## Commands

For each `B in {1,2,4,8}`:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset audio \
  -K 4096 \
  -B ${B} \
  -enable_PCA=true \
  -logtostderr=1 \
  > /tmp/saq-run/logs/audio_K4096_B${B}_create_index.stdout \
  2> /tmp/saq-run/logs/audio_K4096_B${B}_create_index.stderr

/rwproject/kdd-db/kluaq/saq/script/extract_quant_plan.py \
  /tmp/saq-run/logs/audio_K4096_B${B}_create_index.stderr \
  --output /tmp/saq-run/logs/audio_K4096_B${B}_quant_plan.csv
```

Parser added in this audit:

```text
script/extract_quant_plan.py
```

## Result

| B | SAQ quant plan |
| ---: | --- |
| 1 | `0 -> 64 (64d 3b); 64 -> 192 (128d 0b)` |
| 2 | `0 -> 192 (192d 2b)` |
| 4 | `0 -> 192 (192d 4b)` |
| 8 | `0 -> 192 (192d 8b)` |

Raw parsed CSVs were written under:

```text
/tmp/saq-run/logs/audio_K4096_B*_quant_plan.csv
```

## Interpretation

On this `audio` setup, SAQ's dynamic segmentation only creates a non-trivial
plan at `B=1`. At `B=2`, `B=4`, and `B=8`, the plan is a single full-dimensional
segment with uniform bits.

This matters for the limitation audit:

```text
For audio B=2/4, there is no segment-boundary decision to audit under default
SAQ. These settings can still test CAQ/PCA/search plumbing, but they do not test
whether SAQ's dynamic segmentation hides high-risk dimensions.
```

Possible reasons:

- `audio` has only 192 dimensions, so per-segment overhead may discourage
  segmentation at moderate/high bit budgets.
- The SAQ DP cost may prefer one segment when the variance benefit does not
  offset extra segment factor overhead.
- More segmentation may appear at lower budgets, higher dimensions, or datasets
  with sharper PCA variance spectra.

## Next Steps

1. Use `B=1` audio as the first segmentation sanity check.
2. For `B=2/4`, either test equal segmentation controls via `-seg_eqseg`, or use
   a higher-dimensional dataset where default SAQ segmentation is non-trivial.
3. Join `B=1` audio segments with PCA variance and rank-boundary weights from
   the previous `vectordb` tooling.
4. Decide whether the first real audit should use audio B=1 or move directly to
   a higher-dimensional dataset.

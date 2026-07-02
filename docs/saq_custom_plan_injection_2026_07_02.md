# SAQ Custom Plan Injection

Date: 2026-07-02

This note records the first custom segment-plan injection path for `create_index`.
It turns the residual-aware offline plan into an actual encoded SAQ index, while
leaving the default SAQ planner unchanged when no override is provided.

## 1. Implementation

New CLI flag:

```text
-seg_plan=dim:bits,dim:bits,...
```

Example:

```text
-seg_plan=64:9,256:6,256:4,256:2,128:0
```

Meaning:

```text
0-64 uses 9 bits
64-320 uses 6 bits
320-576 uses 4 bits
576-832 uses 2 bits
832-960 uses 0 bits
```

Touched code paths:

| File | Change |
| --- | --- |
| `src/define_options.h` | adds `-seg_plan`, parses compact plan strings, appends a safe `_plan...` suffix to index names |
| `src/create_index.cpp` | parses the flag and injects the plan into `IVF` before variance planning |
| `saqlib/index/ivf.hpp` | exposes `set_custom_quant_plan()` |
| `saqlib/quantization/saq_data.hpp` | stores a runtime-only custom plan in `SaqDataMaker` and uses it instead of equal/default DP planning |
| `script/propose_residual_plan.py` | now emits `seg_plan` strings in JSON summaries for direct use with `-seg_plan` |

The override is runtime-only. It is not stored in `QuantizeConfig`, because SAQ
serializes `QuantizeConfig` by raw `sizeof(QuantizeConfig)` bytes. Adding a
`std::string` or vector there would make the index format unsafe. Instead, the
encoded index still persists the actual `BaseQuantizerData` entries, and load
reconstructs the quant plan from those entries as before.

## 2. Validation Rules

The injected plan is checked before quantizer construction:

```text
segment dimension must be positive
segment dimension must be a multiple of 64
bits must be <= KMaxQuantizeBits
only the final segment may use 0 bits
segment dimensions must sum to the padded dimension
```

These rules intentionally match the assumptions of the existing SAQ DP and
quantizer layout.

## 3. Filename Behavior

The plan string is included in `parseArgs()` through a compact suffix, so custom
indexes do not overwrite default SAQ indexes.

Example command:

```bash
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_sample100k \
  -K 512 \
  -B 4 \
  -enable_PCA=true \
  -seg_plan=64:9,256:6,256:4,256:2,128:0 \
  -logtostderr=1
```

Output index:

```text
./data/gist_sample100k/ivf512_b4_caq_adj_seg_plan64x9_256x6_256x4_256x2_128x0_pca.index
```

To evaluate the custom index with `test_relative_error`, `test_qps`, or another
binary that uses `DataFilePaths`, pass the same `-seg_plan` string so the path
suffix resolves to the custom index.

## 4. Smoke Tests

Working directory:

```text
/tmp/saq-run
```

Dataset:

```text
gist_sample100k, N=100,000, D=960, K=512
```

### B=4 Residual-Aware Plan

Command plan:

```text
64:9,256:6,256:4,256:2,128:0
```

Logged quantization plan:

```text
4bits: | 0 -> 64 (64d 9b) | 64 -> 320 (256d 6b) | 320 -> 576 (256d 4b) | 576 -> 832 (256d 2b) | 832 -> 960 (128d 0b)
```

Result:

```text
Quantization completed successfully.
Index saved at:
./data/gist_sample100k/ivf512_b4_caq_adj_seg_plan64x9_256x6_256x4_256x2_128x0_pca.index
```

### B=3 Residual-Aware Plan

Command plan:

```text
64:8,128:6,192:4,320:2,256:0
```

Logged quantization plan:

```text
3bits: | 0 -> 64 (64d 8b) | 64 -> 192 (128d 6b) | 192 -> 384 (192d 4b) | 384 -> 704 (320d 2b) | 704 -> 960 (256d 0b)
```

Result:

```text
Quantization completed successfully.
Index saved at:
./data/gist_sample100k/ivf512_b3_caq_adj_seg_plan64x8_128x6_192x4_320x2_256x0_pca.index
```

This is notable because the default GIST sampled B=3 run previously printed its
plan and then segfaulted before completing encoding. The custom B=3 residual
plan uses even per-segment bitwidths and completed successfully. This does not
prove the root cause, but it suggests the B=3 crash should be isolated around
odd segment bitwidths or that specific default plan shape.

## 5. Current Status

The custom plan path now answers the immediate engineering question:

```text
Can an offline residual-aware plan be injected into create_index and encoded as a
real SAQ index without changing the default planner path?
```

Answer: yes, on the GIST sampled B=3/B=4 smoke tests.

## 6. Next Step

The next step is evaluation, not another planner table:

```text
Compare SAQ default vs residual-aware custom-plan indexes under identical
settings on relative error and recall.
```

Start with `gist_sample100k` B=4 because both default and custom indexes were
successfully encoded. Then test B=3 if the evaluation path can load the custom
index and if default B=3 remains unavailable or is fixed.

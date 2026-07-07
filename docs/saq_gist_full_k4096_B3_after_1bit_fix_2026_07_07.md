# GIST Full K4096 B=3 Validation After 1-Bit Segment Fix

Date: 2026-07-07

This note records the minimal implementation fix for positive 1-bit CAQ
segments and the unblocked full GIST K4096 B=3 default-vs-custom validation.

## 1. Minimal Fix

The original failure was a contract mismatch:

- `CAQEncoder::encode_and_fac()` exported `base_code.code` only when
  `num_bits_ > 1`.
- `ClusterPacker::store_and_pack()` packed short codes for every
  `num_bits_ > 0` segment.

This meant a positive 1-bit segment produced an empty `base_code.code` for the
packer, causing a release-build segfault during index construction.

The minimal fix keeps the existing data layout semantics:

1. Export `base_code.code` for every positive-bit segment:

   ```cpp
   if (num_bits_ > 0) {
       ...
       base_code.code = std::move(caq.code);
   }
   ```

2. Keep short-code packing for every positive-bit segment, but only pack
   lower-bit long residual codes when `num_bits_ > 1`.

3. Replace the release-disabled `assert(...)` on `base_code.code.size()` with
   `CHECK_EQ(...)`.

Touched files:

```text
saqlib/quantization/caq/caq_encoder.hpp
saqlib/quantization/cluster_packer.hpp
```

## 2. Build

The branch was rebuilt with unit tests disabled:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_UNIT_TESTS=OFF \
  -DCMAKE_MODULE_PATH=/tmp/saq-cmake

cmake --build build -j
```

The build completed successfully. `make` emitted clock-skew warnings from the
local filesystem timestamps, but all targets, including `create_index`,
`compare_search_results`, and `test_qps`, were built.

## 3. Index Build Validation

Both default and custom indexes were rebuilt with the fixed binary under
`/tmp/saq-run`.

Default command:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full \
  -K=4096 \
  -B=3 \
  -enable_PCA=true \
  -logtostderr=1 \
  -num_threads=24
```

Default plan:

```text
64:9,192:5,320:3,192:1,192:0
```

Result:

```text
index saved at: ./data/gist_full/ivf4096_b3_caq_adj_seg_pca.index
Indexing time: 2.26586seconds
```

Custom command:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_full \
  -K=4096 \
  -B=3 \
  -enable_PCA=true \
  -seg_plan=64:8,320:5,320:2,256:0 \
  -logtostderr=1 \
  -num_threads=24
```

Custom plan:

```text
64:8,320:5,320:2,256:0
```

Result:

```text
index saved at: ./data/gist_full/ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca.index
Indexing time: 2.48703seconds
```

## 4. Default-vs-Custom Evaluation

Driver command:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  python script/run_default_neighborhood_cross_dataset.py \
  --root /tmp/saq-run \
  --run gist_full_K4096_B3 \
  --evaluate \
  --max-eval-per-run 1 \
  --force-eval \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_gist_B3_after_1bit_fix_2026_07_07
```

Shared evaluation settings:

```text
dataset: gist_full
K: 4096
B: 3
metric/search distance: L2
topk: R@100
safe searcher: -searcher_safe_block_min_mode=2
compare nprobe: 50, 100, 200, 400, 800
QPS nprobe: 800
risky fallback: disabled
```

The scorer selected the custom plan as conservative-eligible:

```text
candidate: 64:8,320:5,320:2,256:0
family: tail_expand_middle_merge
recall-risk score: 0.9050075658
speed-proxy ratio vs default: 0.7780252413
soft-inversion ratio vs default: 0.9764449887
weighted pair-ratio vs default: 0.9765659818
```

Measured R@100:

| nprobe | default | custom | delta |
|---:|---:|---:|---:|
| 50 | 0.74416 | 0.74419 | +0.00003 |
| 100 | 0.86443 | 0.86467 | +0.00024 |
| 200 | 0.94043 | 0.94145 | +0.00102 |
| 400 | 0.97286 | 0.97418 | +0.00132 |
| 800 | 0.97996 | 0.98155 | +0.00159 |

QPS at `nprobe=800`:

| plan | R@100 | QPS | avg time/query |
|---|---:|---:|---:|
| default | 0.97996 | 1043.0700 | 23.00926 ms |
| custom | 0.98155 | 1159.7524 | 20.69450 ms |

QPS ratio:

```text
custom / default = 1.1118644x
```

## 5. Interpretation

The 1-bit fix unblocks a fair GIST B=3 comparison. The result is positive:

- the SAQ default B=3 plan now builds successfully despite its internal positive
  1-bit segment;
- the fixed-policy custom plan improves R@100 at every measured nprobe;
- the custom plan also improves QPS by about 11.2% at `nprobe=800`.

This completes the GIST budget ladder:

```text
GIST full K4096:
B=3 positive after 1-bit fix
B=4 positive
B=5 positive
```

The important methodological caveat is that the implementation fix is not part
of the proposed planner contribution. It only makes SAQ's own legal 1-bit
default plan buildable, allowing the planner result to be evaluated against a
fair default baseline.

## 6. Artifacts

Indexes:

```text
/tmp/saq-run/data/gist_full/ivf4096_b3_caq_adj_seg_pca.index
/tmp/saq-run/data/gist_full/ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca.index
```

Summary outputs:

```text
/tmp/saq-run/reports/default_neighborhood_gist_B3_after_1bit_fix_2026_07_07.csv
/tmp/saq-run/reports/default_neighborhood_gist_B3_after_1bit_fix_2026_07_07.json
```

Compare outputs:

```text
/tmp/saq-run/reports/gist_full_K4096_B3_plan64x8_320x5_320x2_256x0_compare_np50_top100_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B3_plan64x8_320x5_320x2_256x0_compare_np100_top100_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B3_plan64x8_320x5_320x2_256x0_compare_np200_top100_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B3_plan64x8_320x5_320x2_256x0_compare_np400_top100_2026_07_06.csv
/tmp/saq-run/reports/gist_full_K4096_B3_plan64x8_320x5_320x2_256x0_compare_np800_top100_2026_07_06.csv
```

QPS outputs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b3_caq_adj_seg_pca_th24_np800_sm4_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca_th24_np800_sm4_safeblockminsimd.csv
```

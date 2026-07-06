# GIST B=3 Default Build Crash Debug

Date: 2026-07-06

This note records the root-cause debug for the GIST full K4096 B=3 default
index build crash.

## Symptom

The SAQ default plan for GIST full K4096 at B=3 is:

```text
64:9,192:5,320:3,192:1,192:0
```

Building the default index crashes during quantization:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_full \
  -K 4096 \
  -B 3 \
  -enable_PCA=true \
  -logtostderr=1
```

Observed plan before the crash:

```text
3bits: | 0 -> 64 (64d 9b) | 64 -> 256 (192d 5b) |
       | 256 -> 576 (320d 3b) | 576 -> 768 (192d 1b) |
       | 768 -> 960 (192d 0b)
```

Exit code:

```text
SIGSEGV / exit code 139
```

## Backtrace

`gdb` command:

```bash
gdb -q -batch -ex run -ex bt --args \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_full \
  -K 4096 \
  -B 3 \
  -enable_PCA=true \
  -logtostderr=1
```

Backtrace:

```text
Thread 28 "create_index" received signal SIGSEGV, Segmentation fault.
0x000000000043dfc6 in saqlib::QuantizerCluster::quantize(...)
#0 saqlib::QuantizerCluster::quantize(...)
#1 saqlib::SAQuantizer::quantize_cluster(...)
#2 saqlib::IVF::construct(...)::{lambda()#1}
#3 BS::thread_pool<(unsigned char)0>::worker(...)
```

Address-to-symbol lookup confirms the crash is inside:

```text
saqlib::QuantizerCluster::quantize(...)
```

The release binary has function symbols but no useful source line mapping for
this inlined/header-heavy code path.

## Neighbor Plan Matrix

All commands below use:

```text
dataset: gist_full
K: 4096
B: 3
enable_PCA: true
```

| plan | result | interpretation |
|---|---:|---|
| default dynamic `64:9,192:5,320:3,192:1,192:0` | crash | SAQ default B=3 failure |
| explicit custom `64:9,192:5,320:3,192:1,192:0` | crash | not a default-plan plumbing issue |
| custom `64:8,192:5,320:3,192:1,192:0` | crash | lowering head bits does not matter if 1-bit segment remains |
| custom `64:9,192:5,320:3,384:1` | crash | 1-bit also crashes when it is the final positive segment |
| custom `64:9,192:5,320:3,384:0` | builds | removing the positive 1-bit segment avoids the crash |
| selected custom `64:8,320:5,320:2,256:0` | builds | fixed-policy B=3 candidate avoids 1-bit and builds |

This narrows the failure surface to positive `num_bits=1` CAQ segments, not to
GIST, B=3, K4096, zero tail placement, or custom-plan injection.

## Source Root Cause

The crash path is:

```text
SAQuantizer::quantize_cluster
  -> QuantizerCluster::quantize
  -> CAQEncoder::encode_and_fac
  -> ClusterPacker::store_and_pack
```

In `QuantizerCluster::quantize`, one `QuantBaseCode` object is reused while each
vector is encoded and packed:

```cpp
QuantBaseCode base_code;
for (size_t i = 0; i < num_points; ++i) {
    encoder.encode_and_fac(curr_vec, base_code, &centroid);
    packer.store_and_pack(i, base_code);
}
```

Relevant source: `saqlib/quantization/quantizer.hpp:60`.

The encoder only fills `base_code.code` when `num_bits_ > 1`:

```cpp
if (num_bits_ > 1) {
    ...
    base_code.code = std::move(caq.code);
}
```

Relevant source: `saqlib/quantization/caq/caq_encoder.hpp:239`.

For a 1-bit segment, `encode()` does create `caq.code`, but `encode_and_fac()`
does not move it into `base_code.code`.

The packer, however, treats every nonzero-bit segment as having a valid code:

```cpp
if (num_bits_ == 0) {
    return;
}
assert(num_dim_pad_ == static_cast<size_t>(base_code.code.size()));
pack_short_codes(base_code.code, &short_codes_[i * shortcode_byte_num_]);
...
long_code_[j] = base_code.code[j] & (short_bit_ - 1);
```

Relevant source: `saqlib/quantization/cluster_packer.hpp:62`.

In this binary, the `assert` does not stop execution; the code continues and
`pack_short_codes()` reads from an empty `Eigen::VectorXi`, causing the
segmentation fault.

`get_compacted_code16_func(0)` is not the primary trigger. It maps to
`CodeHelper<0>::compacted_code16`, which immediately returns without touching
the output buffer. The crash happens earlier because the short-code path needs
the 1-bit code vector.

## Root-Cause Statement

The implementation has an inconsistent 1-bit contract:

```text
CAQEncoder::encode_and_fac:
  treats num_bits == 1 as if no full code needs to be exported.

ClusterPacker::store_and_pack:
  treats every num_bits > 0 segment as requiring a full code vector
  for short-code packing.
```

Therefore, any positive 1-bit CAQ segment can hand an empty `base_code.code` to
the packer and crash during index construction.

## Why This Matters For SAQ Planning

The SAQ default DP can legally emit positive 1-bit segments at low budgets, as
shown by GIST full K4096 B=3:

```text
64:9,192:5,320:3,192:1,192:0
```

But the current implementation cannot safely build such plans. This means the
fixed-policy guard against positive 1-bit segments is not merely conservative
for recall; it also avoids an implementation-fragile plan class.

This strengthens the method boundary:

```text
Positive 1-bit segments should be treated as unsafe in the current SAQ codebase
unless the CAQ encode/pack contract is fixed and retested.
```

## Fix Options

A minimal implementation fix should make the encoder and packer contracts
consistent:

1. In `CAQEncoder::encode_and_fac`, always export `base_code.code` for
   `num_bits_ > 0`, not only for `num_bits_ > 1`.
2. In `ClusterPacker::store_and_pack`, keep short-code packing for
   `num_bits_ > 0`, but only pack long-code residual bits when `num_bits_ > 1`.
3. Replace the release-compiled `assert(...)` on `base_code.code.size()` with a
   `CHECK_EQ(...)`, so future contract violations fail clearly instead of
   becoming memory faults.

After a fix, rerun:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_full \
  -K 4096 \
  -B 3 \
  -enable_PCA=true \
  -logtostderr=1
```

Then rerun the B=3 default-vs-custom compare/QPS validation.

## Artifacts

Successful no-1-bit builds:

```text
/tmp/saq-run/data/gist_full/ivf4096_b3_caq_adj_seg_plan64x9_192x5_320x3_384x0_pca.index
/tmp/saq-run/data/gist_full/ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca.index
```

Relevant scorer artifacts from the earlier B=3 validation:

```text
/tmp/saq-run/reports/gist_full_K4096_B3_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B3_default_neighborhood_scored_auto_2026_07_06.*
```

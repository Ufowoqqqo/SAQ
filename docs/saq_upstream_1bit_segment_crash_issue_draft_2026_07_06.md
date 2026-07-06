# Segfault when dynamic SAQ plan includes a 1-bit segment

## Summary

`create_index` can segfault when the dynamic SAQ quantization plan contains a positive 1-bit segment.

I reproduced this on a clean `upstream/main` checkout at commit:

```text
2163ebcedd0ad9c9f4de326e6ca7a860f9eafe52
Refactor encoder; fix ip stats;
```

The crash happens on full GIST with `K=4096`, `B=3`, PCA enabled. The dynamic planner emits a segment with `1b`, and the process segfaults during IVF construction / cluster quantization.

## Reproduction

Built from a clean upstream checkout:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_UNIT_TESTS=OFF
cmake --build build -j
```

Then ran:

```bash
./bin/create_index \
  -dataset=gist_full \
  -K=4096 \
  -B=3 \
  -enable_PCA=true \
  -logtostderr=1 \
  -num_threads=24
```

The data directory contained the expected PCA/IVF artifacts:

```text
./data/gist_full/gist_full_base_pca.fvecs
./data/gist_full/gist_full_centroid_4096_pca.fvecs
./data/gist_full/gist_full_cluster_id_4096.ivecs
./data/gist_full/gist_full_base_pca.vars.fvecs
```

## Observed Output

The dynamic plan is:

```text
3bits: | 0 -> 64 (64d 9b) | 64 -> 256 (192d 5b) | 256 -> 576 (320d 3b) | 576 -> 768 (192d 1b) | 768 -> 960 (192d 0b)
```

Then the process exits with `SIGSEGV` / exit code `139`.

A gdb backtrace shows:

```text
Thread ... received signal SIGSEGV, Segmentation fault.
#0  saqlib::QuantizerCluster::quantize(...)
#1  saqlib::SAQuantizer::quantize_cluster(...)
#2  saqlib::IVF::construct(...)::{lambda()#1}
#3  BS::thread_pool<...>::worker(...)
```

As a sanity check, the same clean binary and same GIST artifacts complete successfully with:

```bash
./bin/create_index \
  -dataset=gist_full \
  -K=4096 \
  -B=4 \
  -enable_PCA=true \
  -logtostderr=1 \
  -num_threads=24
```

That run emits a plan without a 1-bit segment:

```text
4bits: | 0 -> 64 (64d 11b) | 64 -> 256 (192d 6b) | 256 -> 576 (320d 4b) | 576 -> 832 (256d 2b) | 832 -> 960 (128d 0b)
```

and finishes normally.

## Suspected Root Cause

There appears to be an inconsistency between `CAQEncoder::encode_and_fac()` and `ClusterPacker::store_and_pack()` for `num_bits_ == 1`.

In `saqlib/quantization/caq/caq_encoder.hpp`, `base_code.code` is only populated when `num_bits_ > 1`:

```cpp
if (num_bits_ > 1) {
    if (centroid) {
        base_code.ip_cent_oa = centroid->dot(caq.get_oa());
    }
    base_code.norm_ip_o_oa = caq.ip_o_oa / caq.o_l2norm / std::sqrt(caq.oa_l2sqr);

    base_code.code = std::move(caq.code);
}
```

But in `saqlib/quantization/cluster_packer.hpp`, every positive-bit segment is treated as requiring a valid `base_code.code`:

```cpp
if (num_bits_ == 0) {
    return;
}
assert(num_dim_pad_ == static_cast<size_t>(base_code.code.size()));

fac_ip_cent_oa_[i] = base_code.ip_cent_oa;
pack_short_codes(base_code.code, &short_codes_[i * shortcode_byte_num_]);

auto &ex_fac = clus_.long_factor(i);
ex_fac.rescale = base_code.fac_rescale;
ex_fac.error = base_code.fac_error;
for (size_t j = 0; j < num_dim_pad_; ++j) {
    long_code_[j] = base_code.code[j] & (short_bit_ - 1);
}
compacted_code_func_(clus_.long_code(i), &long_code_(0, 0), num_dim_pad_);
```

For a 1-bit segment, `base_code.code` is not populated by the encoder, but the packer still reads from it. In Release builds, the `assert` does not prevent the out-of-bounds access.

## Expected Behavior

Either:

1. 1-bit segments should be supported and `create_index` should finish successfully, or
2. the planner should avoid emitting positive 1-bit segments if they are unsupported, or
3. the code should fail with a clear diagnostic instead of segfaulting.

## Possible Fix Direction

A likely fix is to make the encoder and packer agree on 1-bit behavior:

- export `base_code.code` for `num_bits_ > 0`, not only `num_bits_ > 1`;
- pack short codes for `num_bits_ > 0`;
- only pack residual/long lower bits when `num_bits_ > 1`;
- replace the Release-disabled `assert` with a checked condition such as `CHECK_EQ`.

I have not submitted a patch yet because I wanted to first confirm whether 1-bit segments are intended to be supported by the current format.

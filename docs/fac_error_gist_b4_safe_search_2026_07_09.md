# Fac-Error GIST B=4 Safe-Search Check

## Question

The fac-error DP falsification selected a different B=4 global plan on GIST
sample100k:

```text
SAQ variance plan:  64x11_192x6_320x4_256x2_128x0
fac-error plan:     192x9_512x4_256x0
```

This check asks whether that offline plan change translates into an end-to-end
safe-search benefit at one operating point.

## Implementation

A minimal global custom-plan path was added:

```text
-custom_quant_plan=192x9_512x4_256x0
```

The flag affects index construction only. It does not change the saved index
format: the actual plan is still recovered from the saved `base_datas` metadata
when the index is loaded. The flag is also included in the generated filename
so default and custom indexes do not overwrite each other.

The custom plan parser intentionally supports only global segment plans in the
existing `dimxbits_dimxbits` notation. It is not a mixed-plan mechanism and it
does not introduce per-cluster plan ids.

## Materialized Plans

Both indexes were built on `/tmp/saq-run/data/gist_sample100k` with K512, B=4,
PCA enabled, CAQ adjustment enabled, and 64 build threads.

| plan | segments from build log | indexing time | index size |
|---|---|---:|---:|
| SAQ variance | `64d 11b`, `192d 6b`, `320d 4b`, `256d 2b`, `128d 0b` | 0.288075s | 61,602,697 bytes |
| fac-error | `192d 9b`, `512d 4b`, `256d 0b` | 0.293413s | 58,701,631 bytes |

The custom plan is 4.7% smaller on disk because it uses fewer positive-bit
segments and therefore fewer segment-level factors.

## Safe-Search Result

Evaluation used safe block-min SIMD mode:

```text
searcher_safe_block_min_mode = 2
nprobe = 200
threads = 24
top-k = 100
searcher_vars_bound_m = 4
```

| plan | R@100 | QPS | avg query time | distance ratio |
|---|---:|---:|---:|---:|
| SAQ variance | 0.99132 | 9215.208 | 2.6045 ms | 1.0000147 |
| fac-error | 0.99059 | 12334.094 | 1.9459 ms | 1.0000186 |

At the same nprobe, the fac-error plan is 1.34x faster and 4.7% smaller, but
R@100 drops by 0.00073 absolute. This is not a strict dominance result.

## Interpretation

This result weakens a simple "better planner" claim. The fac-error objective
does identify a lower-cost plan with a large QPS gain, but the same operating
point loses a small amount of recall. The correct interpretation is therefore:

```text
fac-error DP may expose a speed/space/recall tradeoff that SAQ's variance DP
does not choose, but it has not yet shown same-nprobe recall-preserving
improvement.
```

A strict reviewer would ask for a recall-matched comparison before accepting
the tradeoff as useful. If the custom plan can increase `nprobe` enough to
recover R@100 while remaining faster than the default, then this may still be a
valid query-unaware cost-aware objective. If not, this direction should become
limitation evidence rather than a main method.

## Commands

Build custom index:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -custom_quant_plan=192x9_512x4_256x0 \
  -num_threads=64
```

Rebuild default index:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -num_threads=64
```

Safe-search evaluation:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4

/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -custom_quant_plan=192x9_512x4_256x0 \
  -fix_nprobe=200 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4
```

Generated indexes and result CSVs are under `/tmp/saq-run/data/gist_sample100k`
and `/tmp/saq-run/results/saq`; they are not committed.

# Fac-Error GIST B=4 Recall-Matched Check

## Question

The same-nprobe safe-search check showed that the fac-error B=4 plan on GIST
sample100k is faster and smaller than the SAQ variance plan, but loses a small
amount of R@100:

```text
SAQ variance plan:  64x11_192x6_320x4_256x2_128x0
fac-error plan:     192x9_512x4_256x0
```

This check asks whether increasing the custom plan's `nprobe` can recover the
default R@100 while remaining faster than the default operating point.

The default target is:

```text
SAQ default, nprobe=200: R@100 = 0.99132, QPS = 9215.208
```

## Result

All rows use GIST sample100k, K512, B=4, PCA, top-k=100, 24 threads,
`searcher_safe_block_min_mode=2`, and `searcher_vars_bound_m=4`.

| plan | nprobe | R@100 | QPS | QPS vs default | avg query time |
|---|---:|---:|---:|---:|---:|
| SAQ variance | 200 | 0.99132 | 9215.208 | 1.000x | 2.6045 ms |
| fac-error | 200 | 0.99059 | 12334.094 | 1.338x | 1.9459 ms |
| fac-error | 220 | 0.99079 | 11639.397 | 1.263x | 2.0621 ms |
| fac-error | 240 | 0.99084 | 10957.260 | 1.189x | 2.1905 ms |
| fac-error | 280 | 0.99091 | 9875.544 | 1.072x | 2.4303 ms |
| fac-error | 300 | 0.99091 | 9422.062 | 1.022x | 2.5473 ms |
| fac-error | 320 | 0.99091 | 8956.573 | 0.972x | 2.6799 ms |

The custom plan does not recover the default R@100 before crossing the default
QPS. At `nprobe=300`, it is still slightly faster than default but R@100 remains
0.00041 below default. At `nprobe=320`, it is already slower than default and
R@100 still remains below default.

## Interpretation

This is negative evidence for treating the current fac-error DP as the main
method. The offline objective found a lower-cost plan, and that plan gives a
real speed/space tradeoff, but the tradeoff is not recall-matched useful under
this first GIST check.

The appropriate claim is limited:

```text
Measured CAQ fac-error can move SAQ's global plan toward lower search cost, but
on GIST sample100k B=4 the selected plan does not produce a recall-matched QPS
improvement over SAQ.
```

Under the current stop condition, this direction should become limitation
evidence rather than a primary contribution. A strict reviewer would likely see
continued fac-error sweeps as post-hoc objective tuning unless a new mechanism
explains why recall should be preserved.

## Commands

The custom plan was evaluated with:

```bash
/rwproject/kdd-db/kluaq/saq/bin/test_qps \
  -dataset=gist_sample100k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -custom_quant_plan=192x9_512x4_256x0 \
  -fix_nprobe=300 \
  -fix_thread=24 \
  -searcher_safe_block_min_mode=2 \
  -searcher_vars_bound_m=4
```

The same command was run for `nprobe` values 220, 240, 280, 300, and 320.
Generated result CSVs are under `/tmp/saq-run/results/saq/` and are not
committed.

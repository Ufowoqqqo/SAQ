# GIST sample100k B=4 Segment-Level Attribution

This diagnostic compares the default SAQ plan against the residual-aware custom plan `64:9,256:6,256:4,256:2,128:0` on `gist_sample100k`, using PCA-space vectors, IVF512, top100 GT, and nprobe values `20,50,100,200,400`.

## What is attributed

For every query where default/custom disagree on GT@100 membership, the tool records each lost or gained GT neighbor and decomposes the CAQ/SAQ estimated squared L2 distance by segment. The per-segment approximate distance is computed by explicitly decoding the fastscan MSB layout plus low-bit long code, then applying the same CAQ estimator formula used by search. This avoids relying on hidden block-local LUT state.

## Event counts and total-error shift

| nprobe | lost events | gained events | mean delta error on lost | mean delta error on gained | mean lost GT rank | mean gained GT rank |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 128 | 56 | 0.000327015 | -0.00107181 | 64.88 | 66.21 |
| 50 | 238 | 172 | 0.00110212 | -0.00259348 | 73.66 | 84.41 |
| 100 | 448 | 398 | 0.00182052 | -0.00268544 | 83.83 | 91.38 |
| 200 | 592 | 573 | 0.00197253 | -0.00257308 | 86.86 | 93.17 |
| 400 | 602 | 587 | 0.0019938 | -0.00256936 | 87.04 | 93.28 |

Interpretation: lost events are the GT neighbors present in default top100 but absent from custom top100. Their mean `custom_error - default_error` is usually positive, especially at larger nprobe, which means the custom plan tends to estimate those lost neighbors as slightly farther than default does. Gained events show the opposite sign: custom tends to estimate them slightly closer.

## Custom-plan lost-event segment attribution

The table below uses custom-plan rows only. `mean_abs_error_share` is the average fraction of a lost neighbor's total absolute segment error contributed by that segment.

| nprobe | segment | dims | bits | mean error | mean abs error | abs error share | positive error frac |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0 | 0-64 | 9 | -0.000156362 | 0.000421907 | 0.141 | 0.500 |
| 20 | 1 | 64-320 | 6 | 0.000341337 | 0.000993849 | 0.321 | 0.617 |
| 20 | 2 | 320-576 | 4 | -0.00023639 | 0.000851901 | 0.240 | 0.477 |
| 20 | 3 | 576-832 | 2 | 0.000231133 | 0.0007148 | 0.184 | 0.602 |
| 20 | 4 | 832-960 | 0 | 0.000111061 | 0.000385076 | 0.114 | 0.602 |
| 50 | 0 | 0-64 | 9 | -3.98566e-05 | 0.000374094 | 0.147 | 0.550 |
| 50 | 1 | 64-320 | 6 | 0.00052797 | 0.00103045 | 0.343 | 0.681 |
| 50 | 2 | 320-576 | 4 | -2.10993e-06 | 0.000749898 | 0.225 | 0.508 |
| 50 | 3 | 576-832 | 2 | 0.000278258 | 0.000639367 | 0.176 | 0.613 |
| 50 | 4 | 832-960 | 0 | 0.000118507 | 0.000363249 | 0.108 | 0.630 |
| 100 | 0 | 0-64 | 9 | 7.43109e-05 | 0.000387011 | 0.151 | 0.618 |
| 100 | 1 | 64-320 | 6 | 0.00070644 | 0.00107856 | 0.351 | 0.739 |
| 100 | 2 | 320-576 | 4 | 0.000199914 | 0.000734975 | 0.223 | 0.609 |
| 100 | 3 | 576-832 | 2 | 0.000326294 | 0.000614309 | 0.174 | 0.654 |
| 100 | 4 | 832-960 | 0 | 0.000111114 | 0.000334631 | 0.100 | 0.625 |
| 200 | 0 | 0-64 | 9 | 6.06768e-05 | 0.000374192 | 0.148 | 0.583 |
| 200 | 1 | 64-320 | 6 | 0.000751251 | 0.00108175 | 0.364 | 0.755 |
| 200 | 2 | 320-576 | 4 | 0.000218513 | 0.000688792 | 0.219 | 0.630 |
| 200 | 3 | 576-832 | 2 | 0.000293124 | 0.000560779 | 0.170 | 0.633 |
| 200 | 4 | 832-960 | 0 | 0.000102553 | 0.00031053 | 0.098 | 0.627 |
| 400 | 0 | 0-64 | 9 | 6.64386e-05 | 0.000377593 | 0.149 | 0.585 |
| 400 | 1 | 64-320 | 6 | 0.000755025 | 0.00108657 | 0.365 | 0.754 |
| 400 | 2 | 320-576 | 4 | 0.000210943 | 0.000688959 | 0.218 | 0.630 |
| 400 | 3 | 576-832 | 2 | 0.000290011 | 0.000559414 | 0.170 | 0.636 |
| 400 | 4 | 832-960 | 0 | 9.59338e-05 | 0.000306424 | 0.098 | 0.623 |

Main pattern: for custom lost events, segment 1 (`64-320`, 6 bits) is the largest average contributor to absolute error share, followed by segment 2 (`320-576`, 4 bits) and segment 3 (`576-832`, 2 bits). Segment 0 has 9 bits and small signed mean error, while the 0-bit tail contributes a visible but smaller share because it drops the cross term entirely.

## Default vs custom pattern

- Default lost-event error is more concentrated in its `64-256` 6-bit segment and `256-576` 4-bit segment.
- Custom shifts the boundary to a wider 6-bit middle segment (`64-320`) and a narrower 4-bit segment (`320-576`). This improves mean relative error overall, but on boundary GT neighbors it can slightly overestimate the neighbor distance.
- The recall delta is therefore not a probe-coverage failure. It is a ranking-boundary effect: many affected neighbors are around GT ranks 60-100, and the custom estimator changes their approximate ordering by small margins.

## Query 974 spot check

| nprobe | lost ids | mean custom total error | dominant custom segments by abs share |
|---:|---|---:|---|
| 20 | 95744;95452;94557;99426 | 0.00117322 | s2:0.31, s3:0.28, s1:0.22 |
| 50 | 95744;95452;94557;99426 | 0.00117322 | s2:0.31, s3:0.28, s1:0.22 |
| 100 | 95744;95452;94557;99426 | 0.00117322 | s2:0.31, s3:0.28, s1:0.22 |
| 200 | 95744;95452;94557;99426 | 0.00117322 | s2:0.31, s3:0.28, s1:0.22 |
| 400 | 95744;95452;94557;99426 | 0.00117322 | s2:0.31, s3:0.28, s1:0.22 |

For query 974, the same four GT ids are lost across nprobe values. The dominant custom error share is not always the high-variance first segment; it often comes from the mid/low-bit segments, especially segment 2 and segment 3. This supports the hypothesis that the residual-aware plan is close on average but can create local boundary regressions for specific residual geometry.

## Files

- Event CSV: `/tmp/saq-run/reports/gist_sample100k_B4_segment_attribution_events.csv`
- Summary CSV: `/tmp/saq-run/reports/gist_sample100k_B4_segment_attribution_summary.csv`
- Smoke-test CSVs: `/tmp/saq-run/reports/gist_sample100k_B4_segment_attribution_smoke_*.csv`

## Next step

Try a conservative custom plan that gives back a little capacity to the mid/low-bit region while keeping the residual-aware shape, for example reducing the first segment from 9 to 8 bits and using the saved budget to split or strengthen `320-832`. The target should be to preserve the small mean-error gain without increasing boundary overestimation on lost GT neighbors.

# GIST sample100k B=4 eq_s0_to_s1 Per-Query and Segment Attribution Review

Plan under review: `64:8,64:7,192:6,256:4,256:2,128:0`. This is the best same-payload recall candidate from the conservative sweep.

## Aggregate Per-Query Comparison

| nprobe | default R@100 | eq R@100 | delta | lost events | gained events | worse q | better q | equal q | mean overlap | worst q delta | best q delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20 | 0.759150 | 0.759230 | +0.000080 | 63 | 71 | 50 | 58 | 892 | 99.02 | 842:-3 | 338:+2 |
| 50 | 0.927500 | 0.927680 | +0.000180 | 178 | 196 | 112 | 127 | 761 | 98.88 | 153:-2 | 46:+2 |
| 100 | 0.980870 | 0.981120 | +0.000250 | 413 | 438 | 214 | 227 | 559 | 98.88 | 916:-3 | 259:+3 |
| 200 | 0.990870 | 0.991360 | +0.000490 | 558 | 607 | 241 | 275 | 484 | 98.85 | 412:-3 | 259:+3 |
| 400 | 0.991190 | 0.991660 | +0.000470 | 577 | 624 | 245 | 278 | 477 | 98.84 | 412:-3 | 259:+3 |

The eq plan has more gained than lost GT@100 events at every nprobe. At np200 it gains 607 GT events and loses 558, giving the +0.000490 R@100 improvement seen in the sweep.

## Persistent Query Behavior

| comparison | persistent worse queries | ever worse queries | persistent better queries |
|---|---:|---:|---:|
| residual-aggressive vs default | 63 | 314 | 34 |
| eq_s0_to_s1 vs default | 33 | 292 | 41 |

| nprobe | among residual persistent-worse: better | equal | worse | total delta hits |
|---:|---:|---:|---:|---:|
| 20 | 1 | 56 | 6 | -5 |
| 50 | 2 | 52 | 9 | -8 |
| 100 | 3 | 42 | 18 | -14 |
| 200 | 5 | 35 | 23 | -19 |
| 400 | 5 | 35 | 23 | -19 |

Of the 63 residual-aggressive persistent-worse queries, 58 are no longer persistent-worse under eq_s0_to_s1. Still persistent: `[36, 153, 739, 813, 958]`.
New persistent-worse queries under eq_s0_to_s1: `[9, 53, 69, 107, 145, 189, 194, 284, 308, 362, 374, 380, 441, 459, 532, 636, 646, 649, 729, 754]` ...

## Query 974 Check

| nprobe | residual delta | residual lost ids | eq delta | eq lost ids | eq gained ids |
|---:|---:|---|---:|---|---|
| 20 | -4 | `95744;95452;94557;99426` | 0 | `` | `` |
| 50 | -4 | `95744;95452;94557;99426` | 0 | `` | `` |
| 100 | -4 | `95744;95452;94557;99426` | 0 | `` | `` |
| 200 | -4 | `95744;95452;94557;99426` | 0 | `` | `` |
| 400 | -4 | `95744;95452;94557;99426` | 0 | `` | `` |

Query 974 is fixed at the GT@100 membership level: the residual-aggressive plan lost the same four GT ids at every nprobe, while eq_s0_to_s1 has zero lost/gained GT events for this query. This means the canonical persistent failure no longer contributes to the recall loss, although it does not by itself prove that the distance estimate became uniformly better.

## Segment Attribution: Lost Events Under eq_s0_to_s1

| nprobe | seg | dims | bits | mean error | mean abs error | abs share | positive frac |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0 | 0-64 | 8 | -1.14488e-05 | 0.000562485 | 0.236 | 0.508 |
| 20 | 1 | 64-128 | 7 | -4.01677e-05 | 0.000337932 | 0.146 | 0.460 |
| 20 | 2 | 128-320 | 6 | 0.000129141 | 0.000440468 | 0.147 | 0.603 |
| 20 | 3 | 320-576 | 4 | -1.30677e-05 | 0.000657154 | 0.195 | 0.524 |
| 20 | 4 | 576-832 | 2 | 0.000328467 | 0.000655204 | 0.162 | 0.587 |
| 20 | 5 | 832-960 | 0 | 0.000187289 | 0.000523657 | 0.114 | 0.635 |
| 50 | 0 | 0-64 | 8 | 0.000273185 | 0.000749197 | 0.259 | 0.635 |
| 50 | 1 | 64-128 | 7 | 5.67303e-05 | 0.000372119 | 0.132 | 0.573 |
| 50 | 2 | 128-320 | 6 | 0.000262265 | 0.000547509 | 0.164 | 0.640 |
| 50 | 3 | 320-576 | 4 | 0.000344896 | 0.00075653 | 0.190 | 0.579 |
| 50 | 4 | 576-832 | 2 | 0.000382423 | 0.000680672 | 0.156 | 0.663 |
| 50 | 5 | 832-960 | 0 | 0.000198423 | 0.000486907 | 0.099 | 0.629 |
| 100 | 0 | 0-64 | 8 | 0.000433918 | 0.000766417 | 0.254 | 0.705 |
| 100 | 1 | 64-128 | 7 | 0.000103022 | 0.000372734 | 0.128 | 0.615 |
| 100 | 2 | 128-320 | 6 | 0.00030449 | 0.000552568 | 0.171 | 0.673 |
| 100 | 3 | 320-576 | 4 | 0.000411931 | 0.000726895 | 0.194 | 0.642 |
| 100 | 4 | 576-832 | 2 | 0.000432863 | 0.000679075 | 0.162 | 0.663 |
| 100 | 5 | 832-960 | 0 | 0.000136413 | 0.000381718 | 0.091 | 0.615 |
| 200 | 0 | 0-64 | 8 | 0.000469775 | 0.000769775 | 0.256 | 0.733 |
| 200 | 1 | 64-128 | 7 | 0.00010157 | 0.000375946 | 0.129 | 0.602 |
| 200 | 2 | 128-320 | 6 | 0.000283741 | 0.00053968 | 0.175 | 0.658 |
| 200 | 3 | 320-576 | 4 | 0.000391489 | 0.000686018 | 0.193 | 0.645 |
| 200 | 4 | 576-832 | 2 | 0.000394845 | 0.00062871 | 0.158 | 0.659 |
| 200 | 5 | 832-960 | 0 | 9.70537e-05 | 0.00034587 | 0.088 | 0.590 |
| 400 | 0 | 0-64 | 8 | 0.000461612 | 0.000769305 | 0.257 | 0.724 |
| 400 | 1 | 64-128 | 7 | 0.000100061 | 0.000369205 | 0.128 | 0.601 |
| 400 | 2 | 128-320 | 6 | 0.000281253 | 0.000539011 | 0.175 | 0.657 |
| 400 | 3 | 320-576 | 4 | 0.00039656 | 0.000683367 | 0.194 | 0.650 |
| 400 | 4 | 576-832 | 2 | 0.000371395 | 0.000617849 | 0.159 | 0.652 |
| 400 | 5 | 832-960 | 0 | 9.29676e-05 | 0.000340287 | 0.087 | 0.588 |

Compared with residual-aggressive, the eq plan splits `64-320` into `64-128` at 7 bits and `128-320` at 6 bits. The lost-event error is less dominated by a single wide middle segment, but the plan introduces more total segments and shifts error into several positive-bias regions: `0-64`, `128-320`, `320-576`, and `576-832` are all positive on lost events at high nprobe.

## Query 974 Segment Attribution

| nprobe | custom lost ids | mean custom total error | dominant custom abs-error shares |
|---:|---|---:|---|
| 20 |  | 0 |  |
| 50 |  | 0 |  |
| 100 |  | 0 |  |
| 200 |  | 0 |  |
| 400 |  | 0 |  |

There are no query-974 lost/gained rows for eq_s0_to_s1, so segment attribution is intentionally empty here. The useful signal is membership-level: the plan removes this query from the persistent-loss set.

## Recall vs Error Tradeoff

The sweep measured eq_s0_to_s1 at np200 R@100 `0.991360` and `err_tot_avg=0.000527125`. Default had R@100 `0.990870` and `err_tot_avg=0.000476260`; residual-aggressive had R@100 `0.990680` and `err_tot_avg=0.000467793`.
The eq plan improves recall but worsens mean relative error and QPS. This makes it useful as a diagnostic signal: `64-128` matters for recall boundary cases, but a hand-split plan is not yet a clean replacement for residual-aggressive.

## Artifacts

- Compare CSV np20: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_compare_np20_top100.csv`
- Compare CSV np50: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_compare_np50_top100.csv`
- Compare CSV np100: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_compare_np100_top100.csv`
- Compare CSV np200: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_compare_np200_top100.csv`
- Compare CSV np400: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_compare_np400_top100.csv`
- Attribution events: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_segment_attribution_events.csv`
- Attribution summary: `/tmp/saq-run/reports/gist_sample100k_B4_eq_s0_to_s1_segment_attribution_summary.csv`
- Logs: `/tmp/saq-run/reports/eq_s0_to_s1_review_logs`

## Decision

Do not replace the residual-aware plan with eq_s0_to_s1 as-is. Use it to update the offline objective: the next query-unaware DP should penalize boundary overestimation in early/mid PCA dimensions, especially around `64-128`, without increasing segment count and QPS overhead as much as this manual split does.

# GIST sample100k B=4 Conservative Custom-Plan Sweep

Correction note, 2026-07-04: this sweep used the native block-min search path.
The corrected safe-searcher leaderboard is in
`docs/saq_gist_sample100k_safe_corrected_leaderboard_2026_07_04.md`. The broad
B=4 readout remains useful, but exact recall/QPS values should be taken from the
corrected leaderboard with `-searcher_safe_block_min_mode=2`.

This sweep tests whether the residual-aware custom plan can be made less aggressive after the segment-level attribution showed boundary regressions in mid/low-bit segments. All runs use PCA-space `gist_sample100k`, IVF512, B=4, CAQ adjustment, R@100, and 24 threads for QPS.

## Candidate Plans

| name | plan | payload bits | payload b/d | intent |
|---|---|---:|---:|---|
| default | `default` | 3648 | 3.800 | DP default |
| residual_aggressive | `64:9,256:6,256:4,256:2,128:0` | 3648 | 3.800 | previous residual-aware custom |
| eq_s0_to_s3 | `64:8,256:6,256:4,64:3,192:2,128:0` | 3648 | 3.800 | same payload as default/residual; move 1 bit from 0-64 to 576-640 |
| eq_s0_to_s2 | `64:8,256:6,64:5,192:4,256:2,128:0` | 3648 | 3.800 | same payload; move 1 bit from 0-64 to 320-384 |
| eq_s0_to_s1 | `64:8,64:7,192:6,256:4,256:2,128:0` | 3648 | 3.800 | same payload; move 1 bit from 0-64 to 64-128 |
| eq_defaultish_s3 | `64:10,192:6,320:4,64:3,192:2,128:0` | 3648 | 3.800 | same payload; closer to default first segment but add 3-bit slice at 576-640 |
| over_s3_3bit | `64:8,256:6,256:4,256:3,128:0` | 3840 | 4.000 | over-budget upper bound; strengthen 576-832 to 3 bits |

Notes: `default` and `residual_aggressive` have the same 3648-bit payload over 960 dims. `over_s3_3bit` is intentionally over-budget and should be treated only as an upper-bound diagnostic, not a fair same-space baseline.

## Recall@100

| name | np20 | np50 | np100 | np200 | np400 | delta np200 vs default |
|---|---:|---:|---:|---:|---:|---:|
| default | 0.759150 | 0.927500 | 0.980870 | 0.990870 | 0.991190 | +0.000000 |
| residual_aggressive | 0.758430 | 0.926840 | 0.980370 | 0.990680 | 0.991040 | -0.000190 |
| eq_s0_to_s3 | 0.757210 | 0.925160 | 0.978700 | 0.988800 | 0.989180 | -0.002070 |
| eq_s0_to_s2 | 0.759080 | 0.927240 | 0.980510 | 0.990550 | 0.990910 | -0.000320 |
| eq_s0_to_s1 | 0.759230 | 0.927680 | 0.981120 | 0.991360 | 0.991660 | +0.000490 |
| eq_defaultish_s3 | 0.756530 | 0.924610 | 0.978240 | 0.988470 | 0.988880 | -0.002400 |
| over_s3_3bit | 0.758480 | 0.926730 | 0.980000 | 0.990200 | 0.990540 | -0.000670 |

## QPS

| name | np20 | np50 | np100 | np200 | np400 | np200 ratio vs default |
|---|---:|---:|---:|---:|---:|---:|
| default | 31196.6 | 20059.9 | 13770.4 | 9299.8 | 6120.8 | 1.000 |
| residual_aggressive | 32886.6 | 21111.5 | 14442.6 | 9652.9 | 6306.6 | 1.038 |
| eq_s0_to_s3 | 31174.4 | 19720.4 | 13558.6 | 8974.6 | 5930.1 | 0.965 |
| eq_s0_to_s2 | 31021.0 | 19703.7 | 13466.2 | 8984.5 | 5922.7 | 0.966 |
| eq_s0_to_s1 | 30383.5 | 19192.0 | 13025.8 | 8664.3 | 5788.5 | 0.932 |
| eq_defaultish_s3 | 30187.1 | 19267.8 | 13236.4 | 8877.5 | 5920.9 | 0.955 |
| over_s3_3bit | 32338.9 | 20783.0 | 14201.0 | 9465.0 | 6223.4 | 1.018 |

## Relative Error at nprobe=200

| name | err_tot_avg | err_tot_max | err_q_avg_avg | err_q_mx_avg | delta avg vs default |
|---|---:|---:|---:|---:|---:|
| default | 0.000476260 | 0.006655460 | 0.000476350 | 0.003650060 | +0.000000000 |
| residual_aggressive | 0.000467793 | 0.008507790 | 0.000467703 | 0.003461500 | -0.000008467 |
| eq_s0_to_s3 | 0.000561667 | 0.009734440 | 0.000561033 | 0.003802820 | +0.000085407 |
| eq_s0_to_s2 | 0.000556252 | 0.011351000 | 0.000555666 | 0.003800650 | +0.000079992 |
| eq_s0_to_s1 | 0.000527125 | 0.008094720 | 0.000526615 | 0.003650670 | +0.000050865 |
| eq_defaultish_s3 | 0.000472873 | 0.006878880 | 0.000472857 | 0.003556600 | -0.000003387 |
| over_s3_3bit | 0.000550243 | 0.010392700 | 0.000549530 | 0.003687310 | +0.000073983 |

## Readout

- Among same-payload custom plans, best np200 recall is `eq_s0_to_s1` at `0.991360`. Its delta vs default is `+0.000490`.
- Best same-payload mean relative error is `residual_aggressive` with `err_tot_avg=0.000467793`.
- The over-budget upper-bound plan is useful only diagnostically: if it improves recall materially, then the earlier regression is capacity-related; if not, it is more about boundary placement/estimator bias.

## Interpretation

At least one same-payload conservative plan matches or beats default np200 recall. The leading candidate is `eq_s0_to_s1`; it should be checked next with per-query comparison and segment attribution.
The over-budget candidate `over_s3_3bit` has np200 recall `0.990200` (`-0.000670` vs default), so it indicates whether adding capacity to `576-832` is sufficient.

## Artifacts

- JSON summary: `/tmp/saq-run/reports/gist_sample100k_B4_conservative_plan_sweep_summary.json`
- Logs: `/tmp/saq-run/reports/conservative_sweep_logs`
- QPS/relative-error CSVs are under `/tmp/saq-run/results/saq/`.

## Suggested Next Step

Run per-query comparison and segment attribution for the best same-payload candidate against default/residual. If it still loses the same persistent queries, the next design should move from hand-specified conservative plans to an objective that directly penalizes boundary overestimation on held-out data vectors, while remaining query-unaware.

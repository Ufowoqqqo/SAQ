# GIST Sample100k Safe-Searcher Corrected Planner Leaderboard

Date: 2026-07-04

## 1. Why This Re-Audit

The block-min root-cause diagnostic showed that the native multi-segment search path can let padded lanes from partial blocks poison the block-min gate with `NaN`. This affects search pruning and therefore recall/QPS measurements. The corrected evaluation uses:

```text
-searcher_safe_block_min_mode=2
```

This mode masks invalid lanes and replaces non-finite lanes with `FLT_MAX` before the pairwise SIMD min. The goal here is to re-audit the existing GIST `sample100k` planner conclusions under the corrected searcher, not to introduce new plans.

## 2. Scope

Dataset and setup:

```text
dataset = gist_sample100k
N = 100,000
D = 960
K = 512
PCA = true
metric = R@100 over sample-specific top1000 groundtruth
nprobe = 20, 50, 100, 200, 400
QPS = nprobe 200, 24 threads
safe mode = -searcher_safe_block_min_mode=2
```

Candidate set:

- B=4: default, residual-aggressive, `eq_s0_to_s1`, `boundary_4seg`, `v2_split64`, `v2_mid`, `sweep_rank2`, `filtered_new`, and the over-budget diagnostic `over_s3_3bit`.
- B=5: default, `b5_rank0`, `b5_rank1`, `b5_rank2`.

Relative-error metrics are not rerun here because the safe block-min fix changes search control flow, not the quantized distance estimator itself. Existing relative-error values remain useful as estimator-quality side information, but this corrected leaderboard focuses on recall and QPS.

## 3. Corrected B=4 Leaderboard

Sorted by corrected R@100 at nprobe 200. The over-budget diagnostic is shown separately from same-budget candidates.

| rank | name | plan | R@100 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `v2_split64` | `64:9,64:7,128:6,320:4,256:2,128:0` | 0.75965 | 0.92853 | 0.98187 | 0.99198 | 0.99227 | +0.00066 | 8711.9 | 0.942x | 533:-3 |
| 2 | `eq_s0_to_s1` | `64:8,64:7,192:6,256:4,256:2,128:0` | 0.75966 | 0.92818 | 0.98163 | 0.99185 | 0.99214 | +0.00053 | 8597.9 | 0.929x | 117:-2 |
| 3 | `filtered_new` | `64:10,320:6,384:3,192:0` | 0.75954 | 0.92798 | 0.98173 | 0.99182 | 0.99213 | +0.00050 | 10206.8 | 1.103x | 369:-3 |
| 4 | `v2_mid` | `64:10,192:7,256:4,320:2,128:0` | 0.75966 | 0.92829 | 0.98171 | 0.99181 | 0.99219 | +0.00049 | 9276.5 | 1.003x | 314:-3 |
| 5 | `residual_aggressive` | `64:9,256:6,256:4,256:2,128:0` | 0.75955 | 0.92816 | 0.98151 | 0.99171 | 0.99207 | +0.00039 | 9553.6 | 1.032x | 783:-3 |
| 6 | `boundary_4seg` | `128:9,384:5,320:2,128:0` | 0.75963 | 0.92805 | 0.98140 | 0.99164 | 0.99203 | +0.00032 | 11123.0 | 1.202x | 150:-3 |
| 7 | default | default B=4 | 0.75957 | 0.92809 | 0.98140 | 0.99132 | 0.99164 | 0.00000 | 9252.9 | 1.000x | n/a |
| 8 | `sweep_rank2` | `64:8,192:7,320:4,256:2,128:0` | 0.75954 | 0.92786 | 0.98122 | 0.99120 | 0.99159 | -0.00012 | 9329.9 | 1.008x | 314:-3 |

Diagnostic over-budget candidate:

| name | plan | R@100 np200 | delta np200 | QPS np200 | readout |
|---|---|---:|---:|---:|---|
| `over_s3_3bit` | `64:8,256:6,256:4,256:3,128:0` | 0.99106 | -0.00026 | 9390.7 | Still not useful; even extra capacity in that tail/mid region does not beat default. |

### B=4 Corrected Readout

The B=4 planner direction survives the safe-searcher correction.

`v2_split64` remains the best recall candidate at nprobe 200 and nprobe 400:

```text
v2_split64: R@100 np200 = 0.99198, delta = +0.00066
```

The more interesting correction is that several plans previously judged as weaker become competitive once native block-min artifacts are removed:

- `filtered_new` improves to `+0.00050` at np200 while being `1.10x` faster than default.
- `v2_mid` improves to `+0.00049` with essentially default QPS.
- `boundary_4seg` remains the fast compact plan, but not the best recall plan.

The corrected B=4 Pareto frontier at np200 is:

| role | plan | reason |
|---|---|---|
| best recall | `v2_split64` | highest corrected R@100, but slower due to more segments |
| balanced speed/recall | `filtered_new` | `+0.00050` recall and `1.10x` QPS |
| fastest positive-recall plan | `boundary_4seg` | `+0.00032` recall and `1.20x` QPS |

The old conclusion that `v2_split64` is the best automatic B=4 candidate is still defensible, but it should now be stated together with the speed/recall tradeoff above.

## 4. Corrected B=5 Leaderboard

Sorted by corrected R@100 at nprobe 200.

| rank | name | plan | R@100 np20 | np50 | np100 | np200 | np400 | delta np200 | QPS np200 | QPS ratio | worst query at np200 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `b5_rank0` | `64:10,192:8,256:5,384:3,64:0` | 0.75979 | 0.92908 | 0.98413 | 0.99521 | 0.99561 | +0.00043 | 9032.4 | 0.993x | 155:-2 |
| 2 | default | default B=5 | 0.75972 | 0.92900 | 0.98396 | 0.99478 | 0.99516 | 0.00000 | 9099.5 | 1.000x | n/a |
| 3 | `b5_rank2` | `64:10,64:7,128:7,320:5,320:3,64:0` | 0.75980 | 0.92910 | 0.98386 | 0.99478 | 0.99516 | 0.00000 | 8344.0 | 0.917x | 787:-3 |
| 4 | `b5_rank1` | `128:10,256:6,320:4,256:2` | 0.75974 | 0.92901 | 0.98382 | 0.99476 | 0.99513 | -0.00002 | 10322.0 | 1.134x | 38:-2 |

### B=5 Corrected Readout

This is the major correction.

The old B=5 note treated `b5_rank1` as the strongest practical candidate because the native searcher reported:

```text
old native b5_rank1 delta at np200 = +0.00108
```

Under the corrected safe searcher:

```text
corrected b5_rank1 delta at np200 = -0.00002
```

So `b5_rank1` should no longer be presented as a recall-improving plan. Its remaining value is a speed tradeoff:

```text
b5_rank1 QPS ratio = 1.134x
```

The corrected recall winner is instead:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
R@100 np200 = 0.99521
delta np200 = +0.00043
QPS ratio = 0.993x
```

Follow-up review: `docs/saq_gist_sample100k_B5_b5_rank0_safe_review_2026_07_04.md`
checks the per-query and segment attribution behavior. It finds no severe
stable regression; the worst corrected query loses 2 hits, and the gain/loss
events are mostly rank-98/99 boundary cases dominated by the `256-512` and
`512-896` custom segments.

`b5_rank2` is also downgraded: it ties default recall at np200/np400 but is slower, so it is dominated by default for practical purposes.

The corrected B=5 Pareto readout is:

| role | plan | reason |
|---|---|---|
| best recall | `b5_rank0` | only guarded B=5 candidate with stable positive recall at np100/200/400 |
| fastest candidate | `b5_rank1` | `1.13x` QPS, but recall is tied/slightly below default from np100 onward |
| default-safe baseline | default B=5 | strong corrected recall and better QPS than `b5_rank0` by a small margin |

## 5. Old Conclusions Revisited

| prior claim | corrected status | reason |
|---|---|---|
| B=4 `v2_split64` is the best automatic candidate. | Keep, with caveat. | It still has the highest corrected np200/np400 recall, but it is slower than default. |
| B=4 `filtered_new` is only a weak tradeoff point. | Upgrade. | Under safe searcher it gives `+0.00050` np200 recall and `1.10x` QPS, making it a balanced candidate. |
| B=4 `v2_mid` is weaker recall but lower error. | Upgrade on recall. | It now has `+0.00049` np200 recall with default-like QPS. |
| B=4 `boundary_4seg` is useful but not final. | Keep. | It is still not top recall, but remains the fastest positive-recall B=4 point. |
| B=5 `b5_rank1` is the strongest practical candidate. | Retract. | The corrected np200 recall delta is `-0.00002`; previous gain was search-path contaminated. |
| B=5 guarded direction is still promising. | Keep, but change candidate. | `b5_rank0` gives stable positive corrected recall with almost default QPS. |

## 6. Immediate Implications

1. Future planner-quality evaluation should use `-searcher_safe_block_min_mode=2` by default.
2. The current B=4 planner line is still worth pursuing, especially around the `v2_split64` / `filtered_new` tradeoff.
3. The B=5 story should be rewritten around `b5_rank0`, not `b5_rank1`.
4. Do not claim that the no-tail B=5 plan is better for recall. After correction, it is mainly a speed-oriented plan.

## 7. Artifacts

Corrected aggregate leaderboard:

```text
/tmp/saq-run/reports/gist_sample100k_safe_block_min_corrected_leaderboard_2026_07_04.csv
/tmp/saq-run/reports/gist_sample100k_safe_block_min_corrected_leaderboard_2026_07_04.json
```

Per-plan compare rows:

```text
/tmp/saq-run/reports/gist_sample100k_safe_block_min_corrected_compare_rows_2026_07_04.csv
```

Each individual compare CSV follows this pattern:

```text
/tmp/saq-run/reports/gist_sample100k_B{B}_{name}_safeblockminsimd_compare_np{nprobe}_top100.csv
```

QPS logs are under:

```text
/tmp/saq-run/results/saq/*_safeblockminsimd.csv
```

# Full GIST K4096 `v2_split64` Mechanism Audit

Date: 2026-07-04

## 1. Purpose

The full-GIST K4096 B=4 validation showed two guarded candidates:

```text
filtered_new = 64:10,320:6,384:3,192:0
v2_split64   = 64:9,64:7,128:6,320:4,256:2,128:0
```

`filtered_new` was already audited and found to be a speed-oriented candidate:
it improves R@100 slightly and is faster than default, but its gain is a
boundary-level bias effect with real rank-inversion risk.

This note audits `v2_split64` under the same setting. The goal is to understand
whether its higher R@100 comes from a different mechanism and whether it gives
us a useful accuracy-oriented contrast against `filtered_new`.

Configuration:

```text
dataset = full GIST, 1M base / 1K query / 960d
IVF K = 4096
B = 4
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
nprobe = 800
topk = 100
custom plan = 64:9,64:7,128:6,320:4,256:2,128:0
```

Important caveat: this is still the local K4096 fallback pipeline, not a
FAISS-official K4096 reproduction. The centroids were generated from the first
64 PCA dimensions with the local NumPy preparation script.

## 2. Artifacts

Input comparison file:

```text
/tmp/saq-run/reports/gist_full_k4096_original_top100_B4_v2_split64_safeblockminsimd_compare_np800_top100.csv
```

Mechanism audit outputs:

```text
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_segment_events_np800.csv
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_segment_summary_np800.csv
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_replacement_items_np800.csv
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_replacement_segments_np800.csv
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_replacement_pairs_np800.csv
/tmp/saq-run/reports/gist_full_k4096_v2_split64_mechanism_pruning_trace_np800.csv
```

Runtime ablation outputs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca_th24_np800_sm4_fullrefine_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x9_64x7_128x6_320x4_256x2_128x0_pca_th24_np800_sm4_accuratescan_safeblockminsimd.csv
```

## 3. Global Recall Movement

Across 1000 queries, `v2_split64` has a slightly stronger positive net effect
than `filtered_new`, but it is still a boundary-level effect:

| delta hits | query count |
|---:|---:|
| -3 | 2 |
| -2 | 28 |
| -1 | 179 |
| 0 | 481 |
| +1 | 253 |
| +2 | 53 |
| +3 | 4 |

Aggregate view:

| group | queries | lost GT | gained GT | mean default recall | mean custom recall |
|---|---:|---:|---:|---:|---:|
| better | 310 | 53 | 424 | 0.98161 | 0.99358 |
| equal | 481 | 227 | 227 | 0.99056 | 0.99056 |
| worse | 209 | 293 | 52 | 0.99373 | 0.98220 |
| all | 1000 | 573 | 703 | 0.98845 | 0.98975 |

The net gain is `+130` hits over 100000 query-result slots. Compared with
`filtered_new`, `v2_split64` has fewer lost GT events and almost the same number
of gained GT events:

| plan | lost GT | gained GT | net hits | R@100 |
|---|---:|---:|---:|---:|
| `filtered_new` | 604 | 707 | +103 | 0.98948 |
| `v2_split64` | 573 | 703 | +130 | 0.98975 |

Representative best queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 102 | 97 | 100 | +3 | 0 | 3 |
| 144 | 96 | 99 | +3 | 0 | 3 |
| 302 | 95 | 98 | +3 | 0 | 3 |
| 481 | 97 | 100 | +3 | 0 | 3 |

Representative worst queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 78 | 100 | 97 | -3 | 3 | 0 |
| 650 | 99 | 96 | -3 | 3 | 0 |
| 323 | 98 | 96 | -2 | 4 | 2 |
| 359 | 99 | 97 | -2 | 3 | 1 |

## 4. Segment-Level Error Attribution

The segment attribution was run over all lost/gained GT events. The main
pattern is similar to `filtered_new`:

- For gained GT events, `v2_split64` has negative mean error and tends to pull
  true neighbors closer.
- For lost GT events, `v2_split64` has positive mean error and tends to push
  true neighbors farther.
- Unlike `filtered_new`, `v2_split64` spreads this effect over six segments,
  including the split first 256 dimensions.

Mean error by event type:

| event type | plan | segments | event count | sum mean error | sum mean abs error |
|---|---|---:|---:|---:|---:|
| gained | default | 5 | 703 | +0.002050 | 0.003084 |
| gained | custom | 6 | 703 | -0.000402 | 0.002721 |
| lost | default | 5 | 573 | -0.000644 | 0.002548 |
| lost | custom | 6 | 573 | +0.002009 | 0.003190 |

For gained GT, `v2_split64` underestimates distance across segments 0-4, while
the zero-bit tail is unchanged from default:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | +0.000003 | 0.000078 | 0.035 |
| default | 64+192 | 6 | +0.000797 | 0.001039 | 0.362 |
| default | 256+320 | 4 | +0.000770 | 0.001090 | 0.341 |
| default | 576+256 | 2 | +0.000344 | 0.000551 | 0.164 |
| default | 832+128 | 0 | +0.000136 | 0.000327 | 0.097 |
| custom | 0+64 | 9 | -0.000035 | 0.000310 | 0.138 |
| custom | 64+64 | 7 | -0.000048 | 0.000328 | 0.138 |
| custom | 128+128 | 6 | -0.000072 | 0.000425 | 0.171 |
| custom | 256+320 | 4 | -0.000255 | 0.000815 | 0.282 |
| custom | 576+256 | 2 | -0.000127 | 0.000517 | 0.166 |
| custom | 832+128 | 0 | +0.000136 | 0.000327 | 0.104 |

For lost GT, the same broad regions flip positive:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | -0.000002 | 0.000076 | 0.043 |
| default | 64+192 | 6 | -0.000282 | 0.000808 | 0.329 |
| default | 256+320 | 4 | -0.000276 | 0.000811 | 0.314 |
| default | 576+256 | 2 | -0.000182 | 0.000528 | 0.197 |
| default | 832+128 | 0 | +0.000098 | 0.000325 | 0.117 |
| custom | 0+64 | 9 | +0.000125 | 0.000308 | 0.119 |
| custom | 64+64 | 7 | +0.000146 | 0.000349 | 0.130 |
| custom | 128+128 | 6 | +0.000282 | 0.000485 | 0.172 |
| custom | 256+320 | 4 | +0.000954 | 0.001108 | 0.325 |
| custom | 576+256 | 2 | +0.000404 | 0.000614 | 0.166 |
| custom | 832+128 | 0 | +0.000098 | 0.000325 | 0.087 |

Interpretation: `v2_split64` is more accuracy-oriented than `filtered_new` in
the aggregate because it loses fewer GT items, but it does not eliminate the
same boundary-bias mechanism. Its bad cases still come from systematic
overestimation of near-boundary GT items.

## 5. Replacement-Level Review

The selected queries were:

```text
best:  q102, q144
worst: q78, q650
equal with replacements: q245, q842
```

Pair-level attribution compares every lost GT against every custom-only
replacement. A custom inversion means the replacement is exactly farther than
the lost GT, but the custom approximate distance ranks the replacement closer.

| query | pairs | custom inversions | default inversions | replacement FP pairs | gained-GT pairs | mean exact margin | mean custom margin | mean default margin |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 78 | 9 | 9 | 0 | 9 | 0 | +0.001650 | -0.002439 | +0.001909 |
| 245 | 15 | 8 | 0 | 6 | 9 | -0.000132 | -0.003761 | +0.002604 |
| 650 | 9 | 9 | 0 | 9 | 0 | +0.001859 | -0.002327 | +0.004367 |
| 842 | 15 | 13 | 0 | 6 | 9 | +0.002460 | -0.003362 | +0.005406 |

The worst queries are pure inversion cases:

- q78 loses three GT items and gains no GT item. All `9/9` lost-vs-replacement
  pairs are custom inversions.
- q650 loses three GT items and gains no GT item. All `9/9` pairs are custom
  inversions.

The equal-with-replacements cases are also inversion-heavy. q842 has `13/15`
custom inversions even though the final hit count is unchanged. This matters
because a plan can look neutral in aggregate recall while still making the
candidate boundary less stable.

## 6. Pruning Trace Review

The pruning trace for the six selected queries produced 46 traced items:

| role | stage outcome |
|---|---:|
| default-only false positive, inserted then evicted | 11 |
| gained GT, inserted | 12 |
| replacement false positive, inserted | 11 |
| lost GT, inserted then evicted | 11 |
| lost GT, accurate-break rejected | 1 |

Every traced item entered refinement. As with `filtered_new`, most lost GT
items were inserted and later evicted. Only one q650 lost GT was rejected by
accurate-break at segment 5.

This again suggests the representative losses are not primarily unsafe
pre-refinement rejection. They are mostly final-ranking effects after
refinement, driven by small approximate-distance bias around the R@100 boundary.

The fast prefilter break segment was `4` for all traced items. This is expected
for the six-segment plan:

```text
s0 = 0:64,    9 bits
s1 = 64:128,  7 bits
s2 = 128:256, 6 bits
s3 = 256:576, 4 bits
s4 = 576:832, 2 bits
s5 = 832:960, 0 bits
```

Compared with `filtered_new`, which usually broke at segment 2 in the same
trace tool, `v2_split64` consumes more segments before the fast-stage decision.
That helps explain why it buys slightly better recall but loses QPS.

## 7. Runtime Mechanism

Runtime ablations at `nprobe=800`, `topk=100`, `thread=24`:

| mode | default ms/query | `filtered_new` ms/query | `v2_split64` ms/query | default R@100 | `filtered_new` R@100 | `v2_split64` R@100 |
|---|---:|---:|---:|---:|---:|---:|
| safe searcher | 23.6772 | 21.9723 | 26.1323 | 0.98845 | 0.98948 | 0.98975 |
| full refinement | 27.0135 | 24.1949 | 30.0565 | 0.98851 | 0.98961 | 0.98976 |
| accurate scan | 95.5635 | 93.8149 | 95.9190 | 0.98885 | 0.99006 | 0.98997 |

Derived speed ratios:

| mode | `v2_split64` vs default | `v2_split64` vs `filtered_new` |
|---|---:|---:|
| safe searcher | 0.906x | 0.841x |
| full refinement | 0.899x | 0.805x |
| accurate scan | 0.996x | 0.978x |

The speed story is the opposite of `filtered_new`:

- Under normal safe search, `v2_split64` is about `9.4%` slower than default and
  about `18.9%` slower than `filtered_new`.
- Under full refinement, the slowdown is larger because `v2_split64` has six
  segments and does more segment-level work.
- Under accurate scan, it is roughly tied with default, so the main runtime
  penalty is not raw full-vector arithmetic. It is searcher-stage segmentation
  and refinement overhead.

## 8. Mechanism Conclusion

`v2_split64` is the accuracy-oriented counterpart to `filtered_new`:

1. It improves R@100 from `0.98845` to `0.98975`, a net `+130` hits over 100000
   result slots.
2. It beats `filtered_new` in R@100 by `+0.00027`, mostly by losing fewer GT
   items rather than gaining more GT items.
3. It is substantially slower under the normal safe searcher: `26.13ms/query`
   versus `21.97ms/query` for `filtered_new`.
4. The same boundary-inversion failure mode remains. q78 and q650 are pure
   `9/9` custom-inversion cases.
5. The representative losses mostly happen through inserted-then-evicted
   behavior, not through unsafe early rejection.
6. The six-segment shape pushes the fast-stage break later than `filtered_new`,
   giving a plausible accuracy-vs-speed explanation.

## 9. Implication for the Next Step

The two K4096 audits now give a useful design split:

| plan | mechanism role | strength | weakness |
|---|---|---|---|
| `filtered_new` | speed-oriented coarse plan | fastest and still positive R@100 | more lost GT and boundary bias |
| `v2_split64` | accuracy-oriented split plan | best R@100 among current B=4 candidates | slower and still inversion-prone |

The next planner change should target this tradeoff directly:

1. Add a boundary-inversion-aware offline score, not only aggregate segment risk.
2. Penalize plans that create systematic positive error on near-boundary GT
   items, especially when replacement false positives are exactly farther.
3. Preserve a speed term or segment-count constraint, otherwise the planner may
   drift toward `v2_split64`-style fine splitting and lose the system advantage.


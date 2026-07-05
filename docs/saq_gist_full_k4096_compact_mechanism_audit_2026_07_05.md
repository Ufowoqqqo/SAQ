# Full GIST K4096 `compact_k4096` Mechanism Audit

Date: 2026-07-05

## 1. Purpose

The full-GIST K4096 data-boundary candidate evaluation found that
`compact_k4096` is the fastest current B=4 candidate:

```text
default        = 64:11,192:6,320:4,256:2,128:0
filtered_new   = 64:10,320:6,384:3,192:0
v2_split64     = 64:9,64:7,128:6,320:4,256:2,128:0
compact_k4096  = 128:9,320:5,320:3,192:0
```

At `nprobe=800`, original-space R@100 changed from `0.98845` to `0.98922`,
and QPS changed from `1013.64` to `1211.10`. This is a smaller recall gain
than `filtered_new` and `v2_split64`, but a larger speed gain. This note audits
the mechanism: why does the compact plan run faster, where does it gain/lose
GT items, and whether its recall loss relative to the other candidates is the
same near-boundary inversion pattern observed earlier.

Configuration:

```text
dataset = full GIST, 1M base / 1K query / 960d
IVF K = 4096
B = 4
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
nprobe = 800
topk = 100
custom plan = 128:9,320:5,320:3,192:0
```

Important caveat: this is still the local K4096 fallback pipeline, not a
FAISS-official K4096 reproduction. The centroids were generated from the first
64 PCA dimensions with the local NumPy preparation script.

## 2. Artifacts

Index artifact:

```text
/tmp/saq-run/data/gist_full/ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca.index
```

Input comparison file:

```text
/tmp/saq-run/reports/gist_full_k4096_original_top100_B4_compact_k4096_safeblockminsimd_compare_np800_top100.csv
```

Mechanism audit outputs:

```text
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_segment_events_np800.csv
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_segment_summary_np800.csv
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_replacement_items_np800.csv
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_replacement_segments_np800.csv
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_replacement_pairs_np800.csv
/tmp/saq-run/reports/gist_full_k4096_compact_mechanism_pruning_trace_np800.csv
```

Runtime ablation outputs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca_th24_np800_sm4_fullrefine_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan128x9_320x5_320x3_192x0_pca_th24_np800_sm4_accuratescan_safeblockminsimd.csv
```

## 3. Global Recall Movement

Across 1000 queries, `compact_k4096` has a positive but boundary-level net
effect:

| delta hits | query count |
|---:|---:|
| -3 | 6 |
| -2 | 29 |
| -1 | 198 |
| 0 | 466 |
| +1 | 255 |
| +2 | 42 |
| +3 | 4 |

Aggregate view:

| group | queries | lost GT | gained GT | mean default recall | mean custom recall |
|---|---:|---:|---:|---:|---:|
| better | 301 | 79 | 430 | 0.98196 | 0.99362 |
| equal | 466 | 228 | 228 | 0.99052 | 0.99052 |
| worse | 233 | 337 | 63 | 0.99270 | 0.98094 |
| all | 1000 | 644 | 721 | 0.98845 | 0.98922 |

The net gain is `+77` hits over 100000 query-result slots. This is positive,
but weaker than the two previously audited candidates:

| plan | lost GT | gained GT | net hits | R@100 | QPS |
|---|---:|---:|---:|---:|---:|
| `filtered_new` | 604 | 707 | +103 | 0.98948 | 1092.29 |
| `v2_split64` | 573 | 703 | +130 | 0.98975 | 918.44 |
| `compact_k4096` | 644 | 721 | +77 | 0.98922 | 1211.10 |

Representative best queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 43 | 97 | 100 | +3 | 0 | 3 |
| 102 | 97 | 100 | +3 | 0 | 3 |
| 344 | 97 | 100 | +3 | 0 | 3 |
| 408 | 95 | 98 | +3 | 1 | 4 |

Representative worst queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 535 | 99 | 96 | -3 | 3 | 0 |
| 704 | 99 | 96 | -3 | 4 | 1 |
| 715 | 99 | 96 | -3 | 4 | 1 |
| 770 | 100 | 97 | -3 | 3 | 0 |
| 886 | 99 | 96 | -3 | 4 | 1 |

Equal-hit examples with replacements:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 36 | 98 | 98 | 0 | 2 | 2 |
| 245 | 97 | 97 | 0 | 3 | 3 |

`compact_k4096` therefore has the same basic boundary-replacement behavior as
the earlier candidates, but it has more worse queries and more lost GT events.

## 4. Segment-Level Error Attribution

The segment attribution was run over all lost/gained GT events. The directional
pattern is the same as the earlier K4096 audits:

- For gained GT events, `compact_k4096` has negative mean error and tends to
  estimate these true neighbors as slightly closer.
- For lost GT events, `compact_k4096` has positive mean error and tends to
  estimate these true neighbors as slightly farther.
- The main lost-GT error concentration is the broad `128-448` segment with
  only 5 bits. The 192-dimensional zero tail also contributes visible positive
  error.

Mean error by event type:

| event type | plan | segments | event count | sum mean error | sum mean abs error |
|---|---|---:|---:|---:|---:|
| gained | default | 5 | 721 | +0.001993 | 0.003103 |
| gained | custom | 4 | 721 | -0.000302 | 0.002202 |
| lost | default | 5 | 644 | -0.000584 | 0.002668 |
| lost | custom | 4 | 644 | +0.001930 | 0.002892 |

For gained GT, the compact plan underestimates distance in its two middle
segments:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | +0.000003 | 0.000079 | 0.037 |
| default | 64+192 | 6 | +0.000752 | 0.001030 | 0.362 |
| default | 256+320 | 4 | +0.000782 | 0.001108 | 0.341 |
| default | 576+256 | 2 | +0.000332 | 0.000565 | 0.168 |
| default | 832+128 | 0 | +0.000124 | 0.000322 | 0.092 |
| custom | 0+128 | 9 | -0.000029 | 0.000283 | 0.164 |
| custom | 128+320 | 5 | -0.000270 | 0.000888 | 0.413 |
| custom | 448+320 | 3 | -0.000078 | 0.000511 | 0.229 |
| custom | 768+192 | 0 | +0.000074 | 0.000520 | 0.194 |

For lost GT, the same broad regions flip positive:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | +0.000000 | 0.000073 | 0.040 |
| default | 64+192 | 6 | -0.000292 | 0.000864 | 0.345 |
| default | 256+320 | 4 | -0.000249 | 0.000841 | 0.313 |
| default | 576+256 | 2 | -0.000125 | 0.000525 | 0.181 |
| default | 832+128 | 0 | +0.000082 | 0.000366 | 0.120 |
| custom | 0+128 | 9 | +0.000111 | 0.000322 | 0.147 |
| custom | 128+320 | 5 | +0.001062 | 0.001290 | 0.468 |
| custom | 448+320 | 3 | +0.000319 | 0.000643 | 0.206 |
| custom | 768+192 | 0 | +0.000438 | 0.000637 | 0.180 |

Interpretation: `compact_k4096` is not uniformly more accurate. Its benefit is
again a changed bias structure around the R@100 boundary. The risk is stronger
than `filtered_new` and `v2_split64` because the plan coarsens the first 448
dimensions into only two segments and pushes a wider 192-dimensional tail to
0 bits.

## 5. Replacement-Level Review

The selected queries were:

```text
best:  q43, q408
worst: q704, q535
equal with replacements: q245, q36
```

Query-level replacement summary:

| query | role | default-only | custom-only | lost GT | gained GT | replacement FP | custom inversions |
|---:|---|---:|---:|---:|---:|---:|---:|
| 43 | best | 3 | 3 | 0 | 3 | 0 | 0/0 |
| 408 | best | 6 | 6 | 1 | 4 | 2 | 6/6 |
| 704 | worst | 5 | 5 | 4 | 1 | 4 | 18/20 |
| 535 | worst | 3 | 3 | 3 | 0 | 3 | 6/9 |
| 245 | equal | 4 | 4 | 3 | 3 | 1 | 7/12 |
| 36 | equal | 3 | 3 | 2 | 2 | 1 | 5/6 |

Pair-level attribution compares every lost GT against every custom-only
replacement. A custom inversion means the replacement is exactly farther than
the lost GT, but the custom approximate distance ranks the replacement closer.

| query | pairs | custom inversions | default inversions | replacement FP pairs | gained-GT pairs | mean exact margin | mean custom margin | mean default margin |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 36 | 6 | 5 | 0 | 2 | 4 | +0.003503 | -0.002319 | +0.010841 |
| 245 | 12 | 7 | 0 | 3 | 9 | +0.001638 | -0.003446 | +0.007191 |
| 408 | 6 | 6 | 0 | 2 | 4 | +0.001769 | -0.002175 | +0.003623 |
| 535 | 9 | 6 | 0 | 9 | 0 | +0.005061 | +0.002738 | +0.005249 |
| 704 | 20 | 18 | 0 | 16 | 4 | +0.001419 | -0.001612 | +0.001495 |

The worst queries are clear boundary-inversion cases:

- q704 loses four GT items and gains one GT item. Among lost-vs-replacement
  pairs, `18/20` are custom inversions, while default has `0/20`.
- q535 loses three GT items and gains no GT item. `6/9` pairs are custom
  inversions, and every replacement pair is a false-positive replacement.

The best query q408 is also inversion-heavy, but the final hit count improves
because it gains four GT items and loses only one. This is the key point:
`compact_k4096` does not remove the inversion mechanism. It simply moves more
queries to the favorable side than the unfavorable side, while using a cheaper
plan shape.

## 6. Pruning Trace Review

The pruning trace for the six selected queries produced 48 traced items:

| role | stage outcome | count |
|---|---|---:|
| default-only false positive | inserted then evicted | 10 |
| default-only false positive | accurate-break rejected | 1 |
| gained GT | inserted | 13 |
| lost GT | inserted then evicted | 11 |
| lost GT | vector filtered | 1 |
| lost GT | accurate-break rejected | 1 |
| replacement false positive | inserted | 11 |

Most representative losses are not unsafe pre-refinement rejection:

- `12/13` traced lost GT items entered refinement.
- `11/13` traced lost GT items were inserted and later evicted.
- Only one traced lost GT item was vector-filtered before refinement.
- Only one traced lost GT item was rejected by accurate-break after entering
  refinement.

This means the dominant failure mode is final ranking/eviction after
refinement, not a safe-block-min bug or non-finite early rejection.

The fast prefilter break segment was `2` for all traced items. This is expected
for the compact four-segment plan:

```text
s0 = 0:128,   9 bits
s1 = 128:448, 5 bits
s2 = 448:768, 3 bits
s3 = 768:960, 0 bits
```

Compared with `v2_split64`, whose fast-stage break was segment `4`, the compact
plan reaches the fast-stage decision after fewer nonzero segments. That is the
clearest searcher-level explanation for its speed advantage.

## 7. Runtime Mechanism

Runtime ablations at `nprobe=800`, `topk=100`, `thread=24`:

| mode | default ms/query | `filtered_new` ms/query | `v2_split64` ms/query | `compact_k4096` ms/query | default R@100 | `filtered_new` R@100 | `v2_split64` R@100 | `compact_k4096` R@100 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| safe searcher | 23.6772 | 21.9723 | 26.1323 | 19.8171 | 0.98845 | 0.98948 | 0.98975 | 0.98922 |
| full refinement | 27.0135 | 24.1949 | 30.0565 | 21.1023 | 0.98851 | 0.98961 | 0.98976 | 0.98926 |
| accurate scan | 95.5635 | 93.8149 | 95.9190 | 90.8298 | 0.98885 | 0.99006 | 0.98997 | 0.98977 |

Derived speed ratios for `compact_k4096`:

| mode | vs default | vs `filtered_new` | vs `v2_split64` |
|---|---:|---:|---:|
| safe searcher | 1.195x | 1.109x | 1.319x |
| full refinement | 1.280x | 1.147x | 1.424x |
| accurate scan | 1.052x | 1.033x | 1.056x |

The speedup is robust across all three modes:

- Under accurate scan, `compact_k4096` is still about `5.2%` faster than
  default. This is the cleanest evidence that pure full-code plan shape matters.
- Under full refinement, it is `28.0%` faster than default and `14.7%` faster
  than `filtered_new`. This points to fewer nonzero segments and the wider
  zero-bit tail reducing refinement work.
- Under normal safe search, it is `19.5%` faster than default and `10.9%`
  faster than `filtered_new`. This includes plan-shape cost, fast-stage break
  behavior, and candidate-level pruning/refinement interactions.

So the compact plan's speed is not measurement noise. It is a real systems
effect from a coarse four-segment shape:

```text
nonzero coverage = 0:768
zero tail = 768:960
fast break segment = 2
```

## 8. Mechanism Conclusion

`compact_k4096` is a legitimate speed-oriented Pareto point, not the main
accuracy-oriented replacement:

1. It improves R@100 from `0.98845` to `0.98922`, a net `+77` hits over 100000
   result slots.
2. It is the fastest measured B=4 full-GIST K4096 plan so far: `1211.10` QPS
   at `nprobe=800`, `topk=100`, and 24 threads.
3. It does not match the recall of `filtered_new` (`0.98948`) or `v2_split64`
   (`0.98975`).
4. It has more lost GT events than the two earlier candidates: `644` versus
   `604` for `filtered_new` and `573` for `v2_split64`.
5. Its bad cases are the same near-boundary inversion failure mode. q704 and
   q535 are strong examples.
6. The representative losses mostly happen through inserted-then-evicted
   behavior, not unsafe pre-refinement rejection.
7. The main segment-level risk is the broad `128:448` 5-bit region, with an
   additional positive-error contribution from the `768:960` zero-bit tail.
8. The main speed mechanism is the coarse four-segment shape: three nonzero
   segments, a 192-dimensional zero tail, and earlier fast-stage break than
   `v2_split64`.

## 9. Implication for the Next Step

Current practical shortlist:

| role | plan | reason |
|---|---|---|
| best recall | `v2_split64` | highest measured R@100, but slow |
| balanced speed/recall | `filtered_new` | better R@100 than compact, faster than default |
| speed extreme | `compact_k4096` | fastest measured plan with positive R@100 delta |

`compact_k4096` should be kept as a speed-oriented systems candidate. It should
not be presented as evidence that coarser segmentation is uniformly better.

The next planner direction should make the tradeoff explicit:

1. Keep a speed term or segment-count/zero-tail constraint, otherwise the
   planner will drift toward slower split plans.
2. Add an inversion-aware or boundary-risk term, because aggregate data-only
   risk still allowed q704/q535-style failures.
3. Compare future candidates against the three roles above instead of using a
   single "best plan" narrative.


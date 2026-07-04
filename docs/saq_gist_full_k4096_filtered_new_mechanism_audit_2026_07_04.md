# Full GIST K4096 `filtered_new` Mechanism Audit

Date: 2026-07-04

## 1. Purpose

The full-GIST K4096 validation showed that the guarded B=4 `filtered_new`
candidate is slightly better than the default plan at high recall:

```text
default      = 64:11,192:6,320:4,256:2,128:0
filtered_new = 64:10,320:6,384:3,192:0
```

At `nprobe=800`, original-space R@100 changed from `0.98845` to `0.98948`,
and QPS changed from `1013.64` to `1092.29`. This note audits the mechanism:
why does the custom plan help, where does it hurt, and whether the speedup is
coming from plan shape, pruning, or measurement noise.

Configuration:

```text
dataset = full GIST, 1M base / 1K query / 960d
IVF K = 4096
B = 4
metric = original-space R@100
searcher = -searcher_safe_block_min_mode=2
nprobe = 800
topk = 100
custom plan = 64:10,320:6,384:3,192:0
```

Important caveat: this is still the local K4096 fallback pipeline, not a
FAISS-official K4096 reproduction. The centroids were generated from the first
64 PCA dimensions with the local NumPy preparation script.

## 2. Artifacts

Input comparison file:

```text
/tmp/saq-run/reports/gist_full_k4096_original_top100_B4_filtered_new_safeblockminsimd_compare_np800_top100.csv
```

Mechanism audit outputs:

```text
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_segment_events_np800.csv
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_segment_summary_np800.csv
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_replacement_items_np800.csv
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_replacement_segments_np800.csv
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_replacement_pairs_np800.csv
/tmp/saq-run/reports/gist_full_k4096_filtered_new_mechanism_pruning_trace_np800.csv
```

Runtime ablation outputs:

```text
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca_th24_np800_sm4_safeblockminsimd_original_top100.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np800_sm4_fullrefine_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca_th24_np800_sm4_fullrefine_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_pca_th24_np800_sm4_accuratescan_safeblockminsimd.csv
/tmp/saq-run/results/saq/qps_gist_full_ivf4096_b4_caq_adj_seg_plan64x10_320x6_384x3_192x0_pca_th24_np800_sm4_accuratescan_safeblockminsimd.csv
```

## 3. Global Recall Movement

Across the 1000 queries, `filtered_new` has a positive but boundary-level net
effect:

| delta hits | query count |
|---:|---:|
| -3 | 1 |
| -2 | 31 |
| -1 | 177 |
| 0 | 496 |
| +1 | 247 |
| +2 | 46 |
| +3 | 2 |

Aggregate view:

| group | queries | lost GT | gained GT | mean default recall | mean custom recall |
|---|---:|---:|---:|---:|---:|
| better | 295 | 71 | 416 | 0.98200 | 0.99369 |
| equal | 496 | 237 | 237 | 0.99026 | 0.99026 |
| worse | 209 | 296 | 54 | 0.99325 | 0.98167 |
| all | 1000 | 604 | 707 | 0.98845 | 0.98948 |

So the net gain is not caused by many easy queries becoming perfect. It is a
near-boundary replacement effect: `filtered_new` gains 707 GT items and loses
604 GT items, for a net `+103` hits over 100000 query-result slots.

Representative best queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 442 | 96 | 99 | +3 | 0 | 3 |
| 583 | 97 | 100 | +3 | 0 | 3 |
| 26 | 96 | 98 | +2 | 1 | 3 |
| 199 | 96 | 98 | +2 | 1 | 3 |

Representative worst queries:

| query | default hits | custom hits | delta | lost GT | gained GT |
|---:|---:|---:|---:|---:|---:|
| 650 | 99 | 96 | -3 | 4 | 1 |
| 214 | 98 | 96 | -2 | 4 | 2 |
| 618 | 99 | 97 | -2 | 3 | 1 |
| 993 | 99 | 97 | -2 | 3 | 1 |

## 4. Segment-Level Error Attribution

The segment attribution was run over all lost/gained GT events. The key
pattern is directional:

- For gained GT events, `filtered_new` has negative mean error: it tends to
  estimate these true neighbors as slightly closer.
- For lost GT events, `filtered_new` has positive mean error: it tends to
  estimate these true neighbors as slightly farther.
- The effect is concentrated in the middle and tail segments, not in the first
  64 PCA dimensions.

Mean error by event type:

| event type | plan | segments | event count | sum mean error | sum mean abs error |
|---|---|---:|---:|---:|---:|
| gained | default | 5 | 707 | +0.002078 | 0.003062 |
| gained | custom | 4 | 707 | -0.000472 | 0.002182 |
| lost | default | 5 | 604 | -0.000670 | 0.002610 |
| lost | custom | 4 | 604 | +0.001866 | 0.002710 |

For gained GT, the default plan mostly overestimates distance in segments 1-3,
while `filtered_new` slightly underestimates distance in its two large middle
segments:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | +0.000002 | 0.000078 | 0.036 |
| default | 64+192 | 6 | +0.000790 | 0.001009 | 0.362 |
| default | 256+320 | 4 | +0.000837 | 0.001099 | 0.343 |
| default | 576+256 | 2 | +0.000331 | 0.000554 | 0.164 |
| default | 832+128 | 0 | +0.000118 | 0.000321 | 0.095 |
| custom | 0+64 | 10 | +0.000004 | 0.000151 | 0.099 |
| custom | 64+320 | 6 | -0.000241 | 0.000806 | 0.383 |
| custom | 384+384 | 3 | -0.000269 | 0.000717 | 0.315 |
| custom | 768+192 | 0 | +0.000034 | 0.000509 | 0.202 |

For lost GT, `filtered_new` flips the sign in the same broad regions:

| plan | segment | bits | mean error | mean abs error | abs error share |
|---|---|---:|---:|---:|---:|
| default | 0+64 | 11 | -0.000005 | 0.000083 | 0.044 |
| default | 64+192 | 6 | -0.000291 | 0.000816 | 0.333 |
| default | 256+320 | 4 | -0.000310 | 0.000867 | 0.322 |
| default | 576+256 | 2 | -0.000142 | 0.000512 | 0.181 |
| default | 832+128 | 0 | +0.000077 | 0.000332 | 0.118 |
| custom | 0+64 | 10 | +0.000039 | 0.000160 | 0.081 |
| custom | 64+320 | 6 | +0.000741 | 0.001034 | 0.399 |
| custom | 384+384 | 3 | +0.000657 | 0.000896 | 0.321 |
| custom | 768+192 | 0 | +0.000428 | 0.000621 | 0.199 |

Interpretation: `filtered_new` is not uniformly more accurate. It changes the
bias structure. On average this bias helps slightly more near-boundary GT items
than it hurts, but the bad cases are real and should be treated as plan-shape
risk, not noise.

## 5. Replacement-Level Review

The selected queries were:

```text
best:  q442, q583
worst: q650, q214
equal with replacements: q245, q782
```

Pair-level attribution compares every lost GT against every custom-only
replacement. A custom inversion means the replacement is exactly farther than
the lost GT, but the custom approximate distance ranks the replacement closer.

| query | pairs | custom inversions | default inversions | replacement FP pairs | gained-GT pairs | mean exact margin | mean custom margin | mean default margin |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 214 | 16 | 15 | 0 | 8 | 8 | +0.001793 | -0.001870 | +0.003237 |
| 245 | 12 | 3 | 0 | 3 | 9 | -0.000796 | -0.004409 | +0.004268 |
| 650 | 20 | 16 | 0 | 16 | 4 | +0.000869 | -0.002618 | +0.001999 |
| 782 | 12 | 8 | 0 | 3 | 9 | +0.000414 | -0.001584 | +0.002400 |

The two worst queries are clear inversion cases:

- q650 loses four GT items and gains one GT item. Among lost-vs-replacement
  pairs, `16/20` are custom inversions, while default has `0/20`.
- q214 loses four GT items and gains two GT items. `15/16` pairs are custom
  inversions, while default has `0/16`.

The equal-with-replacements cases show a milder version of the same effect.
q245 and q782 both swap three GT items in and three GT items out, but the
custom plan still creates several exact-distance inversions.

This means the residual risk is not only "losing recall"; it is "which side of
the top100 boundary the plan's bias pushes candidates to." The exact margins
are tiny, usually around `1e-3`, so small segment-level bias changes are enough
to alter R@100 membership.

## 6. Pruning Trace Review

The pruning trace for the six selected queries produced 48 traced items:

| role | stage outcome |
|---|---:|
| default-only false positive, inserted then evicted | 10 |
| gained GT, inserted | 15 |
| replacement false positive, inserted | 9 |
| lost GT, inserted then evicted | 13 |
| lost GT, accurate-break rejected | 1 |

Every traced item entered refinement. Almost all lost GT items were not rejected
before refinement; they were inserted and later evicted. Only one q782 lost GT
was rejected by accurate-break at segment 3.

This is important because it rules out an overly simple explanation that
`filtered_new` mainly loses GT through unsafe early rejection. Under safe mode 2,
the representative losses mostly come from final ranking and eviction after
refinement, not from non-finite block-min behavior or early filter bugs.

The fast prefilter break segment was `2` for all traced items. This is expected
for the custom plan:

```text
s0 = 0:64,    10 bits
s1 = 64:384, 6 bits
s2 = 384:768,3 bits
s3 = 768:960,0 bits
```

The prefilter has enough signal after segment 2 for these boundary candidates,
but the top100 ordering is still decided by very small full-refinement margins.

## 7. Runtime Mechanism

Runtime ablations at `nprobe=800`, `topk=100`, `thread=24`:

| mode | default ms/query | custom ms/query | speedup | default R@100 | custom R@100 | delta R@100 |
|---|---:|---:|---:|---:|---:|---:|
| safe searcher | 23.6772 | 21.9723 | 1.0776x | 0.98845 | 0.98948 | +0.00103 |
| full refinement | 27.0135 | 24.1949 | 1.1165x | 0.98851 | 0.98961 | +0.00110 |
| accurate scan | 95.5635 | 93.8149 | 1.0186x | 0.98885 | 0.99006 | +0.00121 |

Definitions:

- `safe searcher`: normal safe mode 2 searcher.
- `full refinement`: disables per-segment early break during accurate
  refinement.
- `accurate scan`: scans all probed IVF candidates with full-code distances,
  disabling candidate-level pruning.

The speed story is therefore mixed:

- Under accurate scan, `filtered_new` is only `1.9%` faster. This is the cleanest
  estimate of plan-shape-only full-code cost when pruning is mostly removed.
- Under normal safe search, `filtered_new` is `7.8%` faster. This includes both
  plan-shape cost and candidate-level pruning behavior.
- Under full refinement, `filtered_new` is `11.6%` faster. The custom plan has
  fewer segments and a wider zero-bit tail, which reduces the full-refinement
  work even when accurate early break is disabled.

So the observed QPS gain is not just noise, but it also should not be attributed
to one isolated mechanism. It comes from a combination of fewer/coarser
segments, a cheaper tail, and searcher pruning/refinement interactions.

## 8. Mechanism Conclusion

`filtered_new` is a legitimate guarded candidate on full GIST K4096, but its
benefit is boundary-level:

1. It improves R@100 by `+0.00103` at np800 and improves QPS by `1.078x`.
2. It gains more GT items than it loses, but the net gain is only `+103` hits
   over 100000 result slots.
3. Its accuracy benefit comes from a changed error-bias profile, not from a
   uniformly lower quantization error.
4. The main risk is near-boundary rank inversion. q650 and q214 are strong
   examples where custom approximate distances invert exact lost-vs-replacement
   ordering.
5. The representative losses mostly happen through inserted-then-evicted
   behavior, not unsafe pre-refinement rejection.
6. The speed gain is real under the normal safe searcher, but the accurate-scan
   ablation shows that only a small part is pure full-code arithmetic speed.

## 9. Implication for the Next Step

The audit supports keeping `filtered_new` as a candidate, but it should not be
presented as a robust accuracy breakthrough. The right next question is whether
we can preserve its speed advantage while reducing boundary inversions.

Two concrete follow-ups:

1. Add a boundary-inversion penalty to the offline planner. The current
   segment-risk penalty sees aggregate segment error but does not directly
   penalize lost-vs-replacement inversions around top100.
2. Run the same mechanism audit for `v2_split64`, because it had slightly higher
   R@100 than `filtered_new` but lower QPS. Comparing these two candidates can
   separate accuracy-oriented segment splitting from speed-oriented segment
   coarsening.


# Codex Recovery Handoff

Date: 2026-07-06

This handoff reconstructs the current task state after context compaction from
the compacted conversation summary, repository status, recent commits, and
visible docs/scripts. Items marked **Uncertain** are not inferred beyond the
available evidence.

## 1. Original Goal

The active project is the SAQ follow-up work in the local repository:

```text
/rwproject/kdd-db/kluaq/saq
```

The inferred research goal is to identify query-unaware weaknesses and possible
extensions of SAQ, especially around segmentation, bit allocation, and
search-time recall/speed tradeoffs.

The latest immediate task before this handoff was:

1. Use planner v3 to select a `gist_sample100k` B=5 recall-risk endpoint.
2. Build and evaluate that endpoint under the corrected safe-searcher protocol.
3. Document the result.
4. Commit and push the report.

## 2. Current Implementation State

Repository state at recovery:

```text
repo   = /rwproject/kdd-db/kluaq/saq
branch = saq-boundary-audit
remote = origin git@github.com:Ufowoqqqo/SAQ.git
latest = f7ad9b6 Document B5 v3 endpoint evaluation
status = clean
```

Planner v3 is implemented in:

```text
script/sweep_data_boundary_pairs.py
```

Visible capabilities include:

- data-only boundary pair sampling inside IVF cells;
- base vectors used as pseudo-queries, keeping the direction query-unaware;
- margin-weighted boundary pairs with `exp(-margin / tau)`;
- pair-risk vector construction;
- pair-level inversion proxy;
- weighted soft inversion and weighted ratio penalties;
- plan-shape speed proxy;
- Pareto frontier output;
- role shortlist output;
- feasibility guards for risky segment-plan shapes.

The latest measured result is that the B=5 planner-v3 recall-risk endpoint:

```text
64:9,64:8,128:7,320:5,320:3,64:0
```

is a measured false positive. Under the corrected safe-searcher protocol it
does not beat `b5_rank0`, does not beat default at high-recall nprobe values,
and is slower than default.

## 3. Files Changed And Why

Recent committed files directly relevant to the current state:

```text
script/sweep_data_boundary_pairs.py
docs/saq_boundary_aware_planner_v3_speed_recall_2026_07_05.md
docs/saq_gist_sample100k_B5_boundary_v3_speed_recall_2026_07_05.md
docs/saq_gist_sample100k_B5_v3_endpoint_eval_2026_07_06.md
```

Purpose of each:

- `script/sweep_data_boundary_pairs.py`: implements planner v3, including
  speed proxy, recall-risk score, Pareto frontier, role shortlist, and expanded
  CSV/JSON outputs.
- `docs/saq_boundary_aware_planner_v3_speed_recall_2026_07_05.md`: documents
  planner v3 and the full GIST K4096 B=4 v3 run.
- `docs/saq_gist_sample100k_B5_boundary_v3_speed_recall_2026_07_05.md`:
  documents the B=5 offline planner-v3 sweep on `gist_sample100k`.
- `docs/saq_gist_sample100k_B5_v3_endpoint_eval_2026_07_06.md`: documents the
  latest B=5 endpoint build/evaluation and concludes that the endpoint is a
  proxy false positive.

Earlier docs that remain important context:

```text
docs/saq_gist_sample100k_safe_corrected_leaderboard_2026_07_04.md
docs/saq_gist_sample100k_B5_b5_rank0_safe_review_2026_07_04.md
docs/saq_gist_full_k4096_data_boundary_candidates_eval_2026_07_05.md
docs/saq_gist_full_k4096_compact_mechanism_audit_2026_07_05.md
```

## 4. Important Decisions And Constraints

The follow-up direction should remain query-unaware. The advisor reportedly did
not view the query-aware scenario as a good primary direction.

All current recall/QPS evaluations should use the corrected safe searcher:

```text
-searcher_safe_block_min_mode=2
```

Reason: earlier native multi-segment search measurements were affected by a
padded-lane/block-min issue. The safe mode masks invalid lanes and replaces
non-finite lanes before SIMD min.

Current B=5 conclusion:

```text
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
```

is the measured B=5 recall/middle candidate.

The B=5 no-tail plan:

```text
b5_rank1 = 128:10,256:6,320:4,256:2
```

is speed-oriented only; it should not be presented as recall-improving under
corrected measurements.

Current full GIST K4096 B=4 shortlist:

| role | plan | readout |
|---|---|---|
| best recall | `64:9,64:7,128:6,320:4,256:2,128:0` | `v2_split64`, highest measured recall but slower |
| balanced | `64:10,320:6,384:3,192:0` | `filtered_new`, positive recall and faster than default |
| speed extreme | `128:9,320:5,320:3,192:0` | `compact_k4096`, fastest positive-recall point |

Planner v3 is useful as a Pareto framing tool, but offline recall-risk alone is
not reliable enough to promote a plan without measured safe-searcher
validation.

## 5. Uncertain Or Possibly Lost

**Uncertain:** exact stdout/stderr logs for many older runs may not be fully
recoverable from git. The main results are preserved in docs and local
`/tmp/saq-run` artifacts.

**Uncertain:** `/tmp/saq-run` artifacts are local experiment outputs and are not
versioned. They were visible during recovery, but long-term persistence should
not be assumed.

**Uncertain:** the full GIST K4096 setup is described in docs as a local
fallback pipeline in at least some places, not necessarily a FAISS-official
K4096 reproduction.

**Uncertain:** no explicit `TODO` or `FIXME` comments were found in `script`,
`docs`, or `src`, but there may be implicit TODOs in conversation history that
were lost during compaction.

## 6. Remaining TODOs

Near-term:

1. Update synthesis or meeting-facing narrative to include the B=5 v3 endpoint
   false-positive result.
2. Add a conservative planner-v3 guard or role-selection rule so the B=5 v3
   role selection does not promote the split-front false-positive endpoint over
   measured `b5_rank0`.
3. Consider using soft-inversion ratio and fragmentation/speed-proxy constraints
   as explicit filters or warnings.

Possible next experiments:

1. Rerun the B=5 v3 sweep after adding the conservative guard and check whether
   it selects `b5_rank0` as the measured middle/recall point.
2. Run a full GIST K4096 B=5 v3 sweep if the cost is acceptable.
3. Continue validating whether v3 consistently exposes recall/speed endpoints
   rather than producing a single scalar winner.

Engineering hygiene:

1. Run Python syntax checks before further planner edits.
2. Keep using safe-searcher mode for all measured recall/QPS claims.
3. Keep new experiment reports in `docs/` and avoid relying only on `/tmp`
   artifacts.

## 7. Commands And Tests Already Run If Known

Known from docs and recovery summary:

```bash
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_sample100k \
  -K 512 \
  -B 5 \
  -enable_PCA=true \
  -seg_plan=64:9,64:8,128:7,320:5,320:3,64:0 \
  -logtostderr=1
```

Known evaluation commands were run through local SAQ binaries for:

```text
compare_search_results at nprobe = 20,50,100,200,400
test_qps at nprobe = 200, top100, 24 threads
```

All latest B=5 endpoint evaluations used:

```text
-searcher_safe_block_min_mode=2
```

Known planner-v3 sweep command families:

```text
python script/sweep_data_boundary_pairs.py ... gist_full / K4096 / B=4
python script/sweep_data_boundary_pairs.py ... gist_sample100k / K512 / B=5
```

Known git/check commands run before the latest commit:

```bash
git status --short
git diff --check
rg -n "[ \t]+$" docs/saq_gist_sample100k_B5_v3_endpoint_eval_2026_07_06.md
git add docs/saq_gist_sample100k_B5_v3_endpoint_eval_2026_07_06.md
git commit -m "Document B5 v3 endpoint evaluation"
git push
```

Latest pushed commit:

```text
f7ad9b6 Document B5 v3 endpoint evaluation
```

## 8. Commands And Tests That Should Be Run Next

Before further code edits:

```bash
python -m py_compile \
  script/sweep_data_boundary_pairs.py \
  script/propose_residual_plan.py \
  script/sweep_boundary_plan.py \
  script/segment_diagnostics.py
```

If implementing a conservative v3 guard, suggested validation sequence:

```bash
python script/sweep_data_boundary_pairs.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 5 \
  --boundary-rank 100 \
  --neighbor-window 8 \
  --pairs-per-anchor 4 \
  --anchors-per-cluster 1 \
  --max-anchors 2048 \
  --max-pairs 8192 \
  --boundary-global-blends 0,0.25 \
  --boundary-tail-alphas 0 \
  --boundary-pair-alphas 0,0.5,1,2 \
  --segment-penalty-scales 0,0.01,0.02 \
  --intra-segment-penalty-scales 0,1.6,3.2 \
  --inversion-penalty-scales 0,0.05,0.1 \
  --weighted-ratio-penalty-scales 0,0.02 \
  --runtime-penalty-scales 0 \
  --speed-proxy-scales 0,0.02,0.05,0.1 \
  --min-positive-bits 2 \
  --min-zero-tail-dim 64 \
  --max-segments 6 \
  --max-nonzero-segment-dim 384 \
  --exclude-nonfinal-1bit \
  --filter-infeasible \
  --output-prefix /tmp/saq-run/reports/gist_sample100k_K512_B5_boundary_v3_guarded_rerun
```

Expected validation target:

```text
The guarded/role-selected B=5 recall or middle candidate should prefer
b5_rank0 = 64:10,192:8,256:5,384:3,64:0
over the measured false-positive endpoint
64:9,64:8,128:7,320:5,320:3,64:0.
```

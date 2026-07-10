# SAQ Transform Phase 1: PCA-Limitation Evidence And Gate Decision

## Decision

**Do not advance to learned-transform development.** Phase 1 does identify a
narrow limitation of the current *raw-data* PCA target, but it does not support
the stronger hypothesis that PCA should be replaced as SAQ's main research
direction.

**Phase 1b update:** the preregistered CIFAR60k external replication passed its
artifact gate but failed to reproduce this narrow estimator effect. The branch
is now closed for PCA-replacement work; see
`saq_transform_phase1b_external_replication_evidence_2026_07_10.md`.

The result is deliberately narrower than "PCA is optimal":

- residual PCA reduces mean per-query candidate RMSE by about `0.60%` at the
  first accurate prefix and by `0.33%` at full code under the same plan and
  serialized bytes;
- the accurate-prefix RMSE improvement occurs for all ten internal-rotation
  seeds and remains when internal rotation is disabled;
- neither signal yields a statistically reliable top-k, boundary-inversion, or
  exact-best-rank improvement;
- residual PCA makes the fast prefixes worse, including all three reported
  endpoints at `fast_all`;
- identity and random orthogonal controls expose fast/full-stage tradeoffs;
  their native comparisons also change to one uniform segment, and their
  matched frozen-plan full-code ranking is substantially worse;
- gains observed for a one-segment transform with internal rotation disabled
  disappear under SAQ's normal internal rotation control.

Therefore the evidence supports this statement:

```text
Current raw-data PCA is measurably but slightly mismatched with one accurate
SAQ prefix and the full-code estimator. The effect does not establish a
progressive-ranking or matched-budget Pareto limitation, and standard residual
PCA already explains it; learning a replacement transform is not justified.
```

The proposal's weak diagnostic trigger (a stable estimator mismatch) is met.
Its stronger learner/contribution gate is not. This is a stopping decision for
method development on this branch, not a universal claim across all datasets,
budgets, metrics, or lossy projections.

## Research Question

```text
Does PCA's variance-only objective mismatch the measured error of SAQ's
segmented CAQ estimator and progressive prefixes, and does a base-only global
full-D orthogonal alternative improve the fixed-candidate rate-error-ranking
tradeoff under one global SAQ plan?
```

The predeclared controls were current PCA, global residual PCA, identity, and a
seeded random orthogonal transform. Each was evaluated with its native plan, a
frozen PCA plan, and a uniform `960@4b` plan.

## Protocol

| Item | Fixed value |
|---|---|
| Dataset | `gist_sample50k`, `N=50,000`, `D=960` |
| IVF | `K=512`, one recovered canonical codebook and fixed `cid` |
| Nominal budget | `B=4` |
| Evaluation queries | First 128 held-out queries; evaluation only |
| Fixed probes | Top 16 canonical IVF clusters per query |
| Fixed-candidate pairs | 442,823 per configuration |
| Ranking endpoint | Fixed-candidate top-100 agreement and boundary inversions |
| Outer random-transform seed | `20260710` |
| Internal rotation controls | Logical seeds `0..9`, plus `off` |
| Seed implementation | Logical `0..9` maps to C RNG seeds `1..10` |
| Plan controls | native, frozen PCA, uniform `960@4b` |
| Configurations | 4 transforms x 3 plans x 11 rotation controls = 132 |
| Construction threads | `6`; timing fields are not used for performance claims |
| Inference | Query-level paired percentile bootstrap, 10,000 replicates, global seed `20260710` |
| RMSE estimands | Equal-query mean of per-query candidate RMSE and candidate-pooled RMSE reconstructed from SSE |

The first seed implementation mapped logical seeds directly to `srand(seed)`.
Because glibc aliases `srand(0)` and `srand(1)`, it produced only nine distinct
streams. The final reported matrix was rerun after mapping logical seeds
`0..9` to C seeds `1..10`; seed 0 and seed 1 were then verified to differ.
Logical seed 0 also covers the C RNG stream obtained from the implementation's
default initial seed.

The summarizer derives a deterministic comparison-specific sub-seed from the
global bootstrap seed with SHA-256 and uses NumPy `1.23.5` `default_rng` to
resample queries. Adding another reported metric therefore does not change an
existing comparison's confidence interval.

The runner directly replays the production packed/FastScan estimators in this
order for each block:

```text
varsEstDist(block)
compFastDist(block)
compAccurateDist(each valid lane)
```

It reconstructs the conservative variance stage, every fast prefix, every
accurate prefix, and the full-code estimate. It bypasses search pruning and
block-min decisions, so `-searcher_safe_block_min_mode=2` is not applicable to
this fixed-candidate estimator experiment. No persisted-index format changed.

All 132 configurations completed with:

```text
118,272 query-stage aggregate rows
1,188 segment aggregate rows
0 non-finite query-stage or segment values
identical 442,823 candidate evaluations per configuration
```

For current and residual PCA, the independently built native and frozen-PCA
controls have the same plan. Their query-stage and segment measurements match
exactly after removing control labels, providing a deterministic duplicate
check for the seed reset, custom-plan path, and estimator replay.

## Transform And Candidate Validity

The local sample lacked the raw IVF centroids and PCA operator. They were not
replaced silently with cluster means. The materializer recovered the historical
affine orthogonal PCA operator from paired raw/PCA base rows, applied held-out
base and paired-query gates, and only then inverse-transformed the historical
PCA centroids.

Key checks:

- PCA held-out mapping relative Frobenius error: `3.4865e-7`;
- PCA held-out maximum absolute error: `1.2890e-6`;
- paired-query mapping relative Frobenius error: `3.4303e-7`;
- all four transform views preserve fixed top-16 probe order for 128/128
  queries;
- an independent canonical-raw check found identical exact top-100 membership
  and exact-best ID for 128/128 queries in all four views;
- fixed-probe SHA-256:
  `c0e1ed9424a8a287cba9d85dabb2732c89ad132485ae431432c55725e674ebfc`.

Each transform is full dimensional and L2-isometric up to recorded float32
roundoff. The runner uses exact distances in each transformed view, but the
canonical check shows that this roundoff does not change the ranking labels
used here. Benchmark queries validate artifacts and evaluate fixed choices;
they do not fit transforms, plans, dimensions, losses, or thresholds.

## Native Plans And Progressive Outcomes

The current and residual PCA views select the same five-segment native plan:

```text
0:64@11b | 64:256@6b | 256:576@4b | 576:832@2b | 832:960@0b
```

Identity and random orthogonal views select the uniform `0:960@4b` native plan.
The table reports the equal-query mean of per-query candidate RMSE after
averaging internal rotation seeds `0..9` within each query. Candidate-pooled
RMSE is reported separately in the committed summaries and in the paired table
below.

| Transform/native plan | Serialized bytes | Stage | Logical bytes/candidate | Mean-query RMSE | Top-100 agreement | Boundary inversion rate |
|---|---:|---|---:|---:|---:|---:|
| current PCA / five segments | 34,201,289 | `fast_all` | 124 | 0.386347 | 0.593133 | 1.9294e-2 |
| current PCA / five segments | 34,201,289 | `accurate_prefix_1` | 212 | 0.0818108 | 0.904930 | 9.5544e-4 |
| current PCA / five segments | 34,201,289 | full | 508 | 0.00168088 | 0.994617 | 4.0869e-6 |
| residual PCA / five segments | 34,201,289 | `fast_all` | 124 | 0.386987 | 0.589813 | 1.9522e-2 |
| residual PCA / five segments | 34,201,289 | `accurate_prefix_1` | 212 | 0.0813185 | 0.906188 | 9.3807e-4 |
| residual PCA / five segments | 34,201,289 | full | 508 | 0.00167530 | 0.994758 | 4.1323e-6 |
| identity / uniform | 34,013,109 | `fast_all` | 124 | 0.122593 | 0.842352 | 2.5690e-3 |
| identity / uniform | 34,013,109 | full | 492 | 0.00838137 | 0.976586 | 5.8387e-5 |
| random orthogonal / uniform | 34,013,109 | `fast_all` | 124 | 0.122656 | 0.843094 | 2.5342e-3 |
| random orthogonal / uniform | 34,013,109 | full | 492 | 0.00837670 | 0.976438 | 5.8319e-5 |

The identity/random native fast-stage gain is real but is not evidence that an
outer transform replaces PCA: it is coupled to a different one-segment native
plan and loses most of SAQ's full-code accuracy. It is a progressive-stage
tradeoff, not a transform dominance result.

## Matched-Plan Residual PCA Result

Residual PCA is the only close control. Its native plan equals the frozen PCA
plan, its serialized bytes are identical, and both RMSE estimands improve at
the first accurate prefix for all ten internal-rotation seeds.

All differences below are `residual PCA - current PCA`. Lower is better for
RMSE and boundary inversion; higher is better for top-k agreement.

| Rotation/stage | Delta mean-query RMSE [95% CI] | Delta pooled RMSE [95% CI] | Delta top-k agreement [95% CI] | Delta boundary inversion [95% CI] |
|---|---:|---:|---:|---:|
| seeds `0..9`, `fast_all` | +6.398e-4 [+4.093e-4, +8.777e-4] | +6.691e-4 [+4.361e-4, +9.058e-4] | -3.320e-3 [-6.281e-3, -4.061e-4] | +2.281e-4 [+4.162e-6, +4.528e-4] |
| seeds `0..9`, `accurate_prefix_1` | -4.922e-4 [-6.882e-4, -2.920e-4] | -5.342e-4 [-7.507e-4, -3.067e-4] | +1.258e-3 [-6.250e-5, +2.602e-3] | -1.737e-5 [-3.706e-5, +1.304e-6] |
| seeds `0..9`, full | -5.572e-6 [-8.552e-6, -2.675e-6] | -5.479e-6 [-8.814e-6, -2.094e-6] | +1.406e-4 [-2.188e-4, +4.922e-4] | +4.541e-8 [-2.416e-7, +3.449e-7] |
| rotation off, `accurate_prefix_1` | -5.611e-4 [-8.204e-4, -2.932e-4] | -5.816e-4 [-8.904e-4, -2.429e-4] | -8.594e-4 [-4.688e-3, +2.969e-3] | -2.463e-5 [-8.570e-5, +3.426e-5] |
| rotation off, full | -1.097e-6 [-9.264e-6, +6.746e-6] | +3.420e-7 [-9.366e-6, +1.002e-5] | -9.375e-4 [-2.188e-3, +3.125e-4] | +1.855e-6 [+4.733e-7, +3.246e-6] |

At `accurate_prefix_1`, mean-query RMSE improves by `0.602%` and pooled RMSE by
`0.617%`; the top-k and boundary point estimates are favorable, but both
confidence intervals include zero. At full code, mean-query RMSE improves by
`0.331%`, while exact-best rank worsens by `+0.009375`
(`[+0.001563, +0.019531]`). Thus the statistically detectable distance-error
reduction does not establish the ranking improvement required by the
learner/contribution gate. The mixed fast/accurate behavior is also not a
progressive-stage Pareto dominance result.

## Plan And Internal-Rotation Controls

The uniform matched-plan comparison isolates the outer transform from SAQ plan
shape. With normal internal rotations enabled:

- identity full-code RMSE is `8.782e-5` higher than current PCA
  (`[7.904e-5, 9.678e-5]`);
- random orthogonal RMSE is `8.314e-5` higher
  (`[7.343e-5, 9.323e-5]`);
- residual PCA differs by only `5.481e-7`, with a CI spanning zero.

When internal rotation is disabled, identity and random orthogonal transforms
substantially outperform PCA under the uniform plan. This is the expected
dimension-balancing effect of mixing highly unequal PCA coordinates. It is not
a surviving outer-transform gain because SAQ normally applies its own segment
rotation; the on-control removes or reverses it.

The frozen-plan control is even clearer: applying PCA's variance-ordered
five-segment bit allocation to unordered identity/random coordinates makes
full-code ranking much worse. PCA's coordinate order is therefore functionally
important to the current segmented plan rather than a removable preprocessing
detail.

## Planner Proxy Evidence

Native total proxy costs are:

| Transform | Native plan | Total variance proxy |
|---|---|---:|
| current PCA | five segments | 0.0200385 |
| residual PCA | five segments | 0.0200988 |
| identity | uniform | 0.127636 |
| random orthogonal | uniform | 0.127636 |

The proxy predicts current PCA slightly ahead of residual PCA, while residual
PCA lowers mean-query RMSE by `0.602%` at the first accurate prefix and `0.331%`
at full code. This is the narrow objective mismatch identified by Phase 1. Its
magnitude is small, it does not preserve the fast-stage endpoints, and its
ranking intervals include zero.

Within the five selected segments, the descriptive Spearman agreement between
the transform proxy and measured accurate distance/IP RMSE is `0.9` for
current/residual PCA and `1.0` for identity/random under the frozen plan. These
are only five aggregate observations per configuration and are not inferential
evidence over all unselected `(segment, bit)` candidates. The runner measures
only each selected segment at its assigned bit width; it does not execute the
counterfactual segment-by-bit grid needed to validate the proxy over the full
planner choice space.

## Byte And Work Boundary

Serialized sizes include packed codes, factors, padding/alignment, centroids,
IDs, and internal segment rotators. For example:

- rotated five-segment index: `34,201,289` bytes;
- rotation-off five-segment index: `33,300,169` bytes;
- rotated uniform index: `34,013,109` bytes;
- rotation-off uniform index: `30,326,709` bytes.

Logical factor bytes count the one short factor actually accessed by the L2
path per segment. Serialized bytes include both stored short factors as well as
all alignment and metadata.

The committed summary labels its Pareto fields as partial diagnostics. The
serialized index excludes the outer transform artifact, while logical prefix
bytes exclude raw-query transform, centroid/LUT preparation, caching, and
complete search-path work. Full-D PCA and residual PCA have the same operator
shape, so this omission does not explain their matched-plan difference, but it
prevents an end-to-end Recall-QPS or complete-memory claim.

The four transform jobs ran concurrently, so recorded construction and
measurement timings are provenance only and are not used as comparative
performance evidence.

## Continue/Stop Gate

| Predeclared requirement | Result |
|---|---|
| Stable estimator mismatch | Yes; accurate-prefix RMSE improves for 10/10 seeds and with rotation off |
| Better full-code ranking | No measurable top-k/boundary gain |
| Better progressive prefixes | Mixed: first accurate-prefix RMSE improves, fast prefixes worsen, ranking CIs span zero |
| Survives frozen-plan control | Distance-RMSE signal survives; ranking signal does not |
| Survives internal-rotation ablation | Accurate-prefix RMSE survives; ranking dominance does not |
| Not explained by simple controls | No; the only stable signal is obtained by standard residual PCA |
| Matched actual bytes | Yes for PCA versus residual PCA index bytes |
| Counterfactual segment-by-bit proxy test | Not measured; selected-segment correlations are descriptive only |
| Complete query work and end-to-end IVF | Not measured; no ranking case justifies it yet |
| More than one spectral regime | No |

The weak Phase 2 diagnostic trigger is met, but the stronger learner and paper
contribution gate is not. Do not implement a learned SAQ-aware transform,
change the persisted format, start a broad post-hoc transform sweep, or present
residual PCA's small RMSE reductions as a method contribution. If this result
is continued at all, the next experiment should be a preregistered replication
on one second spectral regime with a common canonical exact reference, not a
new learner.

## What This Result Does Not Claim

- It does not prove PCA is universally optimal for SAQ.
- It does not prove that the variance proxy correctly ranks all possible
  segment-and-bit choices.
- It does not evaluate physical `D -> d` projection or projection error.
- It does not report end-to-end IVF Recall-QPS.
- It does not include online raw-query transform latency or a complete work
  model.
- It does not evaluate IP distance or graph search.
- It is one deliberately small limitation setting, sufficient for a
  method-development gate but not for a universal positive or negative theorem.

## Reproduction

Materialize the four validated views:

```bash
python script/prepare_phase1_transform_views.py \
  --output-parent /tmp/saq-phase1-transform/views \
  --random-seeds 20260710 \
  --force
```

Build the offline runner:

```bash
cmake -S . -B build -DBUILD_UNIT_TESTS=OFF
cmake --build build -j --target phase1_transform_diagnostic
```

Run each view with explicit artifact paths. The current-PCA command is:

```bash
V=/tmp/saq-phase1-transform/views/gist_sample50k_phase1_current_pca
P=gist_sample50k_phase1_current_pca
R=data/gist_sample50k

./bin/phase1_transform_diagnostic \
  -base_file=$V/${P}_base.fvecs \
  -query_file=$V/${P}_query.fvecs \
  -exact_base_file=$R/gist_sample50k_base.fvecs \
  -exact_query_file=$R/gist_sample50k_query.fvecs \
  -centroids_file=$V/${P}_centroid_512.fvecs \
  -cluster_ids_file=$V/${P}_cluster_id_512.ivecs \
  -variance_file=$V/${P}_base.vars.fvecs \
  -fixed_probes_file=$V/${P}_fixed_probe_clusters_q128_nprobe16.ivecs \
  -pca_variance_file=$V/${P}_base.vars.fvecs \
  -output_prefix=/tmp/saq-phase1-transform/results/current_pca \
  -transform_label=current_pca \
  -max_queries=128 -topk=100 -num_threads=6 \
  -plans=native,frozen-pca,uniform \
  -rotation_seeds=0,1,2,3,4,5,6,7,8,9,off \
  -B=4 -vars_bound_m=4
```

Repeat with the identity, residual-PCA, and random-orthogonal view paths and
labels, always using current PCA's variance file for the frozen-plan reference.
The runner now requires the two common raw exact-reference paths shown above;
this removes the transform-view roundoff scope retained by the historical
Phase 1 output.

Generate query-level summaries:

```bash
python script/summarize_phase1_transform.py \
  current_pca=/tmp/saq-phase1-transform/results/current_pca \
  identity=/tmp/saq-phase1-transform/results/identity \
  residual_pca=/tmp/saq-phase1-transform/results/residual_pca \
  random_orthogonal=/tmp/saq-phase1-transform/results/random_orthogonal \
  --output-prefix docs/saq_transform_phase1_artifacts_2026_07_10/phase1 \
  --baseline current_pca \
  --bootstrap-replicates 10000 \
  --bootstrap-seed 20260710
```

The machine-readable evidence, complete prefix curves, and per-seed effects are
in `docs/saq_transform_phase1_artifacts_2026_07_10/`. Raw view and per-run CSV
artifacts remain generated data under `/tmp` and are not committed.

## Raw Result Integrity

| Raw CSV | SHA-256 |
|---|---|
| `current_pca.configs.csv` | `97958bac802ae81510b6dbb6112757118716775876d427a62899cd3cf6651d44` |
| `current_pca.query_stages.csv` | `155a3b8f2cd8ff9edf6cdca0dc60728304ae0fd93e5703e4a757c82740b07fae` |
| `current_pca.segment_errors.csv` | `de49ce3cfabca77a50c2eebf2c5078460ffccdc6762806a4f6d1b587176a049e` |
| `identity.configs.csv` | `9ed9130fc44d3dc0c9526f55e56b3f4967add8ab1712b74efb787cfa02727c74` |
| `identity.query_stages.csv` | `29c1f307d0e306793ec4545879e18654a46a8b702fccdd73d58597318f9b5113` |
| `identity.segment_errors.csv` | `8a8306bca7622c18b3857c304cf3f1521c85aba62acb9f90a37fc0b62882c512` |
| `residual_pca.configs.csv` | `ed1ceb4f0cd7f216ffaf2c936afd335c56d3816b5461f7141efd47bef18c9030` |
| `residual_pca.query_stages.csv` | `7968a003bd7357b381a49638767de9a729876463d4d83e7ec515d5d6104d6cdd` |
| `residual_pca.segment_errors.csv` | `627ab9d8798620cad82619c1b5f74561e7552ac0fce660ce8bb615f0cf446d67` |
| `random_orthogonal.configs.csv` | `2b560280ab06f89110d7a1396eb8e07a61d91fb65bc04f878283d48caaa03b9a` |
| `random_orthogonal.query_stages.csv` | `cc16ec98acc88b1cf869712d85fd8d87d85d19520526e7278efdaa13bf682a75` |
| `random_orthogonal.segment_errors.csv` | `0afbfc6322a89961837324e93529d8c70d86907d9437a7c09b60932052e89b42` |

## Committed Summary Integrity

| Artifact | SHA-256 |
|---|---|
| `phase1.config_summary.csv` | `7769b21f101c05f30654831efb8e3fb378d9bb16ff9057ec1216a305253538eb` |
| `phase1.paired_vs_pca.csv` | `440f6ebdb413114b2639266d9c3bb33c0cc2faf01b65a522c4504244aea89794` |
| `phase1.per_seed_effects.csv` | `8b270b1c6cdca67986a75c2dac217690a3e5581e214548c298d49c45b430aadb` |
| `phase1.segment_proxy.csv` | `20e07d34659337ce50f1e10307b9b555844c7dbaab9d66c0abdd020536e12aff` |
| `phase1.stage_curves.csv` | `2c762ab72e07a8390a1b7444275f28343e148ee73d618aef579f62d519863dde` |
| `phase1.md` | `63a633ed3467bcfdf655111da05230bef808ce13029863ff58855d99457c2a44` |

# SAQ Transform Phase 1b: External Replication Evidence And Closure Decision

## Decision

**Close PCA replacement as a main research direction on this branch.**  The
preregistered CIFAR60k replication passed every artifact-validity check but
failed Gate A, the narrow estimator-replication gate.  The GIST residual-PCA
RMSE reduction did not reproduce at either confirmatory endpoint with the
required confidence, seed stability, or rotation-off direction.

The result supports the narrower conclusion:

```text
The small residual-PCA estimator advantage observed on GIST is not stable
across the preregistered second regime. It is insufficient evidence that
SAQ's current full-dimensional PCA is a systematic practical limitation.
```

Do not train a replacement transform, broaden the transform/dataset sweep,
change the persisted format, or begin the counterfactual `(segment, bit)`
analysis from this evidence.  This is a closure decision for the current
premise, not a proof that PCA is universally optimal.

The protocol was committed before CIFAR query evaluation as
`e26eb3e` and remains authoritative:
`saq_transform_phase1b_external_replication_protocol_2026_07_10.md`.
The canonical-exact runner, two-view materializer, summarizer checks, and
mechanical gate evaluator were then frozen before the run as `29ad740`.

## Registered Question

Phase 1 on GIST found that global residual PCA reduced matched-plan mean-query
candidate RMSE by about `0.60%` at `accurate_prefix_1` and `0.33%` at `full`.
Ranking confidence intervals included zero and `fast_all` worsened.

Phase 1b asked whether only that narrow estimator effect would reproduce on
one fixed second dataset under:

```text
one canonical raw float64-accumulated squared-L2 reference
one fixed codebook, cid, probe list, and candidate set
one frozen current-PCA SAQ plan
matched internal-rotation streams and serialized bytes
no query-trained state and no post-hoc prefix choice
```

## Protocol

| Item | Frozen value |
|---|---|
| Dataset | `cifar60k`, 60,000 base x 512 dimensions |
| Metric | squared L2 |
| Queries | all 1,000 held-out queries; evaluation only |
| IVF state | `K=512`, historical query-unaware fixed codebook/cid |
| Historical clustering | all 60,000 base rows, first 64 current-PCA coordinates, 4 iterations, seed 0 |
| Fixed probes | raw-space top 16 full-dimensional recovered centroids |
| Candidate pairs | 2,130,639 per configuration |
| Ranking endpoint | fixed-candidate top-100 |
| SAQ budget | `B=4` |
| Frozen plan | `0:64@9b | 64:256@5b | 256:384@3b | 384:512@0b` |
| Transforms | current raw-data PCA; global residual PCA |
| Normal rotations | logical seeds `0..9` mapped to C seeds `1..10` |
| Mechanism control | rotation off |
| Configurations | 2 transforms x 11 rotation controls = 22 |
| Bootstrap | query-paired percentile, 10,000 replicates, seed `20260710` |
| Confirmatory stages | `accurate_prefix_1`, `full` |
| No-harm stage | `fast_all` |

The codebook assignments were historically formed from the first 64 PCA
coordinates rather than full-dimensional k-means.  Its stored centroids are
full dimensional, and both transform arms use identical recovered centroids,
assignments, raw-space probes, and candidates.  This supports the registered
fixed-candidate estimator comparison but not a claim about IVF partition
quality.

The replay executes production packed/FastScan estimators but bypasses search
pruning and block-min decisions.  Safe block-min mode is therefore not
applicable.  Timings are provenance only; Phase 1b makes no QPS claim.

## Artifact Gate

The complete artifact gate passed:

- raw base SHA-256:
  `a7170faaa80a072cd603ed472104049ead87fbaff224e94a529021d161f8aea4`;
- raw query SHA-256:
  `88109c80b4f4d779440422df89eb9242c23d8cd4021682782294c50c57cca6d7`;
- current/residual isometry relative L2 error:
  `1.126e-7` / `1.184e-8`;
- identical cid SHA-256:
  `3168f05171f74afb175c50a0ec9e584b0f666b157fbedba6d3841cc2e43107e9`;
- identical probe SHA-256:
  `8c81117a919a85e032fe2139a81e654bcde0c899f5fc5b735418a6e1f5e5afd4`;
- identical 1,000-query candidate/exact-label inventory SHA-256:
  `210b361e3f35082f3103fbeb1557e7588e01e524e8c8688ea1fbf264f6f236a2`;
- minimum candidates per query: `1,321`, above top-100;
- identical plan and nominal code bits in all 22 configurations;
- identical serialized bytes within every paired rotation control;
- `198,000` query-stage rows and `264` segment rows with zero non-finite
  estimates and complete configuration/query/stage grids;
- summary provenance hashes bind both raw runner bundles and every compact
  summary consumed by the gate evaluator.

The canonical reference is computed once per raw query/candidate pair as:

```text
sum_j (float64(raw_query[j]) - float64(raw_base[j]))^2
```

The runner caches those labels before constructing any plan/rotation-specific
estimator state and checks candidate order in every configuration.  Segment
attribution remains transform-view specific because coordinate partitions have
no common raw-space segment semantics.

The historical current-PCA operator recovery also passed disjoint validation:
held-out base relative Frobenius error was `3.055e-7`, paired-query artifact
error was `3.054e-7`, and operator orthogonality Frobenius error was
`9.525e-14`.

## Confirmatory Estimator Result

All deltas are `residual PCA - current PCA`; lower RMSE is better.  Seeded rows
first average the ten paired internal-rotation seeds within each query.

| Stage | Logical bytes/candidate | Current mean-query RMSE | Residual mean-query RMSE | Delta [95% CI] | Relative delta | Seeds favoring residual |
|---|---:|---:|---:|---:|---:|---:|
| `fast_all` | 64 | 0.13355750 | 0.13359980 | +4.230e-5 [+5.373e-6, +7.956e-5] | +0.0317% | 3/10 |
| `accurate_prefix_1` | 136 | 0.03010816 | 0.03010955 | +1.394e-6 [-2.216e-5, +2.461e-5] | +0.00463% | 4/10 |
| `full` | 280 | 0.001108523 | 0.001108262 | -2.610e-7 [-1.043e-6, +5.094e-7] | -0.0235% | 5/10 |

Candidate-pooled RMSE agrees with the decision:

| Stage | Delta pooled RMSE [95% CI] | Seeds favoring residual |
|---|---:|---:|
| `fast_all` | +4.127e-5 [+3.609e-6, +7.982e-5] | 3/10 |
| `accurate_prefix_1` | +2.030e-6 [-2.233e-5, +2.638e-5] | 5/10 |
| `full` | -2.310e-7 [-1.045e-6, +5.840e-7] | 4/10 |

Rotation-off mean-query RMSE deltas were also opposite to the registered
direction at both confirmatory stages:

```text
accurate_prefix_1: +1.152e-5
full:              +9.886e-7
```

Thus Gate A failed every required family: neither confirmatory stage had both
RMSE confidence intervals below zero, neither achieved 8/10 seed agreement,
and neither rotation-off direction supported residual PCA.  No other prefix
may substitute for these failures.

## Ranking And Progressive Diagnostics

Gate B and Gate C were not formally evaluated after Gate A failed.  Their
precomputed descriptive values do not rescue the premise:

| Stage/metric | Delta [95% CI] | Direction |
|---|---:|---|
| `accurate_prefix_1` top-100 agreement | -1.35e-4 [-6.680e-4, +4.010e-4] | point estimate worse; interval spans zero |
| `accurate_prefix_1` boundary inversion | +2.931e-6 [-1.218e-5, +1.828e-5] | point estimate worse; interval spans zero |
| `full` top-100 agreement | -1.20e-5 [-1.730e-4, +1.510e-4] | interval spans zero |
| `full` boundary inversion | +1.606e-7 [-3.256e-7, +6.599e-7] | interval spans zero |

The registered `fast_all` no-harm condition would also fail: both RMSE
estimands significantly favor current PCA.  Fast-stage ranking intervals span
zero.

Serialized index sizes are matched within rotation mode:

```text
normal internal rotations: 21,508,196 bytes
rotation off:              21,213,284 bytes
```

Both outer transforms have the same modeled production runtime state:

```text
(512^2 + 512) float32 values = 1,050,624 bytes
512^2 = 262,144 dense MACs per raw query
```

Residual-covariance fitting took `0.338 s` in the recorded local environment.
The current PCA artifact was historical, so recovery/materialization timings
are provenance rather than comparable fit-time measurements.

## Second Spectral Regime

The dataset is a real but moderate spectral change, not a strong cross-domain
validation:

| Base-only PCA spectrum | GIST Phase 1 | CIFAR60k Phase 1b |
|---|---:|---:|
| Dimension | 960 | 512 |
| First component variance share | 20.37% | 14.26% |
| First 64 components variance share | 77.93% | 78.53% |
| Participation ratio | 17.09 | 26.31 |

CIFAR has a flatter spectral head and larger effective rank, while its first-64
energy share remains close to GIST.  These base-only facts characterize the
registered second regime; they were not used to change the dataset or gate.

The current-PCA variance proxy favors current PCA over residual PCA under the
frozen plan (`0.00799576` versus `0.00801424`, a `0.231%` residual increase).
Unlike GIST, measured confirmatory RMSE provides no stable counterexample to
that ordering.

## Gate Decision

| Registered gate | Result | Consequence |
|---|---|---|
| Artifact validity | Pass | Scientific interpretation is allowed |
| Gate A: narrow estimator replication | Fail | Close the effect as non-replicated across the registered regimes |
| Gate B: practical ranking evidence | Not evaluated | Cannot authorize continuation after Gate A failure |
| Gate C: progressive no-harm | Not evaluated | Cannot authorize continuation after Gate A failure |

The registered decision is:

```text
close_one_dataset_estimator_effect
```

This updates the Phase 1 interpretation.  GIST remains valid evidence of a
small local estimator mismatch, but Phase 1b shows that it is not a stable
premise for a PCA-replacement research program.  A strict SIGMOD/VLDB/ICDE
reviewer would reasonably treat further transform learning here as post-hoc
method development after a failed external gate.

## Limitations And Non-Claims

- CIFAR was locally available and had appeared in sibling-repository work, so
  dataset identity was not blinded.  Its selection criteria and hashes were
  nevertheless frozen in Git before this branch evaluated its queries.
- The fixed codebook used historical 64-coordinate PCA-prefix clustering.  It
  is adequate for a paired estimator replay but does not test full-D IVF
  partition construction.
- This study does not evaluate end-to-end Recall-QPS, other `B`/`K`/`nprobe`
  settings, IP distance, graph search, or physical `D -> d` projection.
- Failure does not prove PCA optimal for every dataset.  It says the current
  evidence is inadequate to spend research degrees of freedom on a learned
  replacement.

## Reproduction

Build the canonical-exact offline runner:

```bash
cmake --build build -j --target phase1_transform_diagnostic
```

Materialize only the two registered views:

```bash
python script/prepare_phase1_transform_views.py \
  --dataset cifar60k \
  --raw-base /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_base.fvecs \
  --pca-base /tmp/saq-run/data/cifar60k/cifar60k_base_pca.fvecs \
  --raw-query /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_query.fvecs \
  --pca-query /tmp/saq-run/data/cifar60k/cifar60k_query_pca.fvecs \
  --pca-centroids /tmp/saq-run/data/cifar60k/cifar60k_centroid_512_pca.fvecs \
  --cluster-ids /tmp/saq-run/data/cifar60k/cifar60k_cluster_id_512.ivecs \
  --pca-vars /tmp/saq-run/data/cifar60k/cifar60k_base_pca.vars.fvecs \
  --k 512 \
  --output-parent /tmp/saq-phase1b-cifar60k/views \
  --view-prefix cifar60k_phase1b \
  --views current_pca residual_pca \
  --ivf-provenance-json \
    /tmp/saq-run/data/cifar60k/cifar60k_sampled_pca_ivf_summary.json \
  --probe-query-count 1000 --nprobe 16 --isometry-pairs 512 --force
```

For each view, run `phase1_transform_diagnostic` with its transformed base,
query, centroid, variance, shared cid/probe files, and these common controls:

```text
-exact_base_file=.../cifar60k_base.fvecs
-exact_query_file=.../cifar60k_query.fvecs
-pca_variance_file=.../current_pca_base.vars.fvecs
-max_queries=1000 -topk=100 -num_threads=6
-B=4 -vars_bound_m=4 -plans=frozen-pca
-rotation_seeds=0,1,2,3,4,5,6,7,8,9,off
```

Summarize and apply the frozen decision mechanically:

```bash
python script/summarize_phase1_transform.py \
  current_pca=/tmp/saq-phase1b-cifar60k/results/current \
  residual_pca=/tmp/saq-phase1b-cifar60k/results/residual \
  --output-prefix /tmp/saq-phase1b-cifar60k/summary/phase1b \
  --bootstrap-replicates 10000 --bootstrap-seed 20260710

python script/evaluate_phase1b_gate.py \
  --summary-prefix /tmp/saq-phase1b-cifar60k/summary/phase1b \
  --current-manifest \
    /tmp/saq-phase1b-cifar60k/views/cifar60k_phase1b_current_pca/cifar60k_phase1b_current_pca_manifest.json \
  --residual-manifest \
    /tmp/saq-phase1b-cifar60k/views/cifar60k_phase1b_residual_pca/cifar60k_phase1b_residual_pca_manifest.json \
  --current-result-prefix /tmp/saq-phase1b-cifar60k/results/current \
  --residual-result-prefix /tmp/saq-phase1b-cifar60k/results/residual \
  --output-prefix /tmp/saq-phase1b-cifar60k/summary/phase1b_gate
```

Compact summaries, manifests, the gate decision, per-seed effects, the
canonical query-reference inventory, and raw/summary hash binding are
committed under
`docs/saq_transform_phase1b_artifacts_2026_07_10/`.  Generated views, packed
indexes, and raw runner outputs remain outside Git.

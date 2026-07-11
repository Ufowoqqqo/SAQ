# LP-0 Gate A: Exact-Surrogate Upper-Bound Evidence

## Decision

**Gate A fails. Stop the registered GIST/`d=576`/`B=4` line and do not run
Gate B.**

The exact `oracle576_norm.DP` surrogate is worse than seed-averaged
`native_full_saq.full` on both preregistered ranking endpoints. The result is
an insufficiency finding at one frozen point, not evidence that lossy
projection is universally ineffective.

```text
registered decision: FAIL
next action:          stop_registered_gist_d576_b4_line
Gate B:               not authorized
method claim:         none
```

## Research Question And Scope

Gate A asks whether a physically retained 576-dimensional PCA head, given an
exact float64 combined residual-tail norm surrogate, preserves enough
original-space fixed-candidate ranking quality to justify implementing
projected SAQ. This arm is deliberately favorable to projection: it adds no
SAQ quantization or progressive-stage error.

The frozen evaluation uses GIST sample50k, squared L2, `N=50,000`, `D=960`,
`d=576`, IVF `K=512`, the first 128 benchmark queries, 16 frozen probes per
query, all 442,823 members of the probed lists, and top-100 ranking. Exact
labels are original-space float64 distances. The candidate inventory SHA-256
is
`f5eaef79fbbceda7a0cb04adb5dc232d24d00e0173b4cd70bb0f29ddae25b099`.

The comparison is:

```text
delta = oracle576_norm.DP - native_full_saq.full
```

Positive agreement delta and negative boundary-inversion delta are favorable.
The ten logical native rotation seeds are averaged within each query before a
10,000-replicate paired-query percentile bootstrap with seed `20260711`.
Rotation-off is descriptive and separate.

## Confirmatory Ranking Result

| Rotation group | Endpoint | Oracle | Native | Delta | One-sided 95% lower | One-sided 95% upper | Pass |
|---|---|---:|---:|---:|---:|---:|---|
| seed average | top-100 agreement | 0.992890625 | 0.9946171875 | -0.0017265625 | -0.002578125 | -0.000875 | no |
| seed average | boundary inversion rate | 6.852478398e-6 | 4.086870951e-6 | 2.765607447e-6 | 1.504189353e-6 | 4.216880965e-6 | no |
| rotation off | top-100 agreement | 0.992890625 | 0.994296875 | -0.00140625 | -0.0025 | -0.0003125 | no |
| rotation off | boundary inversion rate | 6.852478398e-6 | 4.151582513e-6 | 2.700895885e-6 | 1.076681626e-6 | 4.550981949e-6 | no |

The agreement gate requires the seed-averaged one-sided lower bound to be at
least zero; it is `-0.002578125`. The inversion gate requires the one-sided
upper bound to be at most zero; it is `4.216880965e-6`. Both conditions fail,
and rotation-off has the same unfavorable directions.

## Distance And Error Evidence

Every registered candidate emits common `D0`, pure-head `DP/DS`, exact-tail
`DP`, deployed-tail `DS`, and their component errors. The table reports pooled
absolute-error quantiles. Equal-query RMSE is the mean of the 128 per-query
candidate RMSE values; pooled RMSE weights candidates.

| Component | Bias | MAE | Equal-query RMSE | Pooled RMSE | Abs. p50 | Abs. p90 | Abs. p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| pure-head projection, `DP_none-D0` | -0.03391551667 | 0.03391551667 | 0.03734477526 | 0.04446495229 | 0.02666298452 | 0.06426805766 | 0.1562325113 |
| tail-norm projection, `DP_norm-D0` | -3.252706554e-6 | 0.001507361451 | 0.002081108114 | 0.002481796224 | 0.0009091147974 | 0.003465974093 | 0.009305721998 |
| tail-summary precision, `DS_norm-DP_norm` | 5.365109818e-11 | 1.050655089e-7 | 1.243973628e-7 | 1.507223596e-7 | 7.450747130e-8 | 2.334096727e-7 | 5.434344142e-7 |
| deployed-tail total, `DS_norm-D0` | -3.252652903e-6 | 0.001507361214 | 0.002081108105 | 0.002481796243 | 0.0009090871915 | 0.003466023582 | 0.009305782100 |

The projection/summary population covariance is `3.438608887e-14`; the error
sum identity has maximum absolute residual zero for both tail treatments. The
float32 tail-summary error is negligible relative to the exact surrogate's
projection error. It therefore does not explain or rescue the ranking-gate
failure.

## Artifact Validity

All validity checks pass before inference:

- all registered input, recovered-operator, probe, and candidate hashes match;
- the oracle and frozen native query-reference files are byte-identical, with
  SHA-256
  `c196e5900aa631852a4f926d06d098b33b079a8f045ab959d03737951ee3987b`;
- all 442,823 candidate rows are finite, unique within query, contiguous, and
  in the registered query/probe/ascending-base-id order;
- candidate, `D0`, and all four oracle-estimate FNV digests recompute exactly;
- top-100 agreement and strict boundary inversions recompute from the
  candidate-level distances;
- `DP_none` and `DS_none` are bit-identical, and every component definition
  and additive identity passes the registered tolerance;
- all 11 native configurations, logical seeds `0..9`, rotation-off, and native
  stages are complete and match the frozen five-segment plan.

The validation also detected and rejected two provenance defects before the
official inference: a truncated SHA-256 entry in the hand-written native
manifest and a raw-distance accumulation build that differed from the frozen
native reference at approximately `1e-15`. The manifest was corrected against
the unchanged output file, and the oracle was rebuilt with the frozen Release
accumulation contract. The final byte-identical reference check prevents
either defect from affecting the result.

Both native and oracle diagnostics use GCC 11.5.0 on x86-64 and the same
recorded Release flag sequence: `-march=native -ftree-vectorize
-ffp-contract=off -fno-finite-math-only -O3 -DNDEBUG -Ofast`, followed by the
AVX-512 target flags. Output hashes and the byte-identical `D0` reference
remain the authoritative reproducibility checks because `-march=native` is
host-specific and compiler-option order is material.

## Reproduction

Prepare and validate the frozen view:

```bash
python script/prepare_lp0_gate_a_artifacts.py \
  --input-dir data/gist_sample50k \
  --output-dir /tmp/saq-lp0-gate-a-20260711/prepared
```

Build and run the exact-surrogate replay:

```bash
cmake --build build --target lp0_projection_gate_a -j

bin/lp0_projection_gate_a \
  -raw_base_file=data/gist_sample50k/gist_sample50k_base.fvecs \
  -raw_query_file=data/gist_sample50k/gist_sample50k_query.fvecs \
  -pca_base_file=data/gist_sample50k/gist_sample50k_base_pca.fvecs \
  -pca_query_file=data/gist_sample50k/gist_sample50k_query_pca.fvecs \
  -pca_centroids_file=data/gist_sample50k/gist_sample50k_centroid_512_pca.fvecs \
  -cluster_ids_file=data/gist_sample50k/gist_sample50k_cluster_id_512.ivecs \
  -pca_variance_file=data/gist_sample50k/gist_sample50k_base_pca.vars.fvecs \
  -fixed_probes_file=/tmp/saq-lp0-gate-a-20260711/prepared/lp0_fixed_probes_q128_nprobe16.ivecs \
  -prepared_manifest=/tmp/saq-lp0-gate-a-20260711/prepared/lp0_gate_a_artifacts_manifest.json \
  -output_prefix=/tmp/saq-lp0-gate-a-20260711/oracle/lp0_gate_a
```

Evaluate against the already-frozen native comparator:

```bash
python script/evaluate_lp0_gate_a.py \
  --oracle-prefix /tmp/saq-lp0-gate-a-20260711/oracle/lp0_gate_a \
  --native-prefix /tmp/saq-lp0-gate-a-20260711/native/native_full_saq \
  --native-manifest /tmp/saq-lp0-gate-a-20260711/native/native_comparator_manifest.json \
  --output-prefix /tmp/saq-lp0-gate-a-20260711/evidence/lp0_gate_a
```

The compact committed result is
`docs/saq_lossy_projection_lp0_gate_a_artifacts_2026_07_11/gate_a_result.json`.
Large generated matrices, candidate distances, native stage rows, binaries,
and build outputs remain uncommitted.

## Strict-Reviewer Interpretation

This screen adds evidence that the favorable exact tail-norm surrogate at the
registered 40% physical dimension reduction does not match the ranking quality
of native full-D SAQ, even before projected quantization is introduced. Because
the quality floor fails, implementing projected SAQ, progressive stages, byte
accounting, or end-to-end IVF at this point would be an unregistered rescue
experiment rather than evidence for the stated hypothesis.

The conclusion is narrow. GIST appeared in the parent research line, there is
one dimension and one budget, candidates and routing are frozen, and no
external spectral regime is evaluated. A future lossy-projection study would
need a distinct related-work-grounded mechanism and a new preregistration; it
must not rescue this line by sweeping `d`, `B`, the plan, probes, or tail rule.

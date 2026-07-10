# SAQ Transform Phase 1b Gate Result

- Artifact gate: **PASS**
- Gate A, narrow estimator replication: **FAIL**
- Gate B, practical ranking evidence: **NOT EVALUATED**
- Gate C, progressive no-harm: **NOT EVALUATED**
- Decision: `close_one_dataset_estimator_effect`

## Artifact Checks

| Check | Result | Detail |
|---|---|---|
| `current_pca_raw_base` | PASS | sha256=a7170faaa80a072cd603ed472104049ead87fbaff224e94a529021d161f8aea4 shape=60000x512 |
| `current_pca_raw_query` | PASS | sha256=88109c80b4f4d779440422df89eb9242c23d8cd4021682782294c50c57cca6d7 shape=1000x512 |
| `current_pca_isometry` | PASS | relative_l2=1.125617e-07 |
| `current_pca_runtime_state` | PASS | dtype=float32 bytes=1050624 |
| `current_pca_historical_ivf_provenance` | PASS | sample=60000 K=512 cluster_dims=64 iterations=4 seed=0 |
| `residual_pca_raw_base` | PASS | sha256=a7170faaa80a072cd603ed472104049ead87fbaff224e94a529021d161f8aea4 shape=60000x512 |
| `residual_pca_raw_query` | PASS | sha256=88109c80b4f4d779440422df89eb9242c23d8cd4021682782294c50c57cca6d7 shape=1000x512 |
| `residual_pca_isometry` | PASS | relative_l2=1.183716e-08 |
| `residual_pca_runtime_state` | PASS | dtype=float32 bytes=1050624 |
| `residual_pca_historical_ivf_provenance` | PASS | sample=60000 K=512 cluster_dims=64 iterations=4 seed=0 |
| `matched_cluster_ids` | PASS | current=3168f05171f74afb175c50a0ec9e584b0f666b157fbedba6d3841cc2e43107e9 residual=3168f05171f74afb175c50a0ec9e584b0f666b157fbedba6d3841cc2e43107e9 |
| `matched_fixed_probe_clusters` | PASS | current=8c81117a919a85e032fe2139a81e654bcde0c899f5fc5b735418a6e1f5e5afd4 residual=8c81117a919a85e032fe2139a81e654bcde0c899f5fc5b735418a6e1f5e5afd4 |
| `matched_runtime_state` | PASS | current_bytes=1050624 residual_bytes=1050624 |
| `current_pca_config_grid` | PASS | configs=11 controls=['off', 'seed0', 'seed1', 'seed2', 'seed3', 'seed4', 'seed5', 'seed6', 'seed7', 'seed8', 'seed9'] plans=['frozen-pca'] |
| `current_pca_structure` | PASS | plans=['0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b'] |
| `current_pca_canonical_exact_scope` | PASS | scopes=['canonical_raw_float64_squared_L2'] |
| `current_pca_finite_and_candidate_count` | PASS | nonfinite=False min_candidates=1321 |
| `current_pca_complete_measurement_grid` | PASS | query_rows=99000 expected=99000 segment_rows=132 expected=132 |
| `residual_pca_config_grid` | PASS | configs=11 controls=['off', 'seed0', 'seed1', 'seed2', 'seed3', 'seed4', 'seed5', 'seed6', 'seed7', 'seed8', 'seed9'] plans=['frozen-pca'] |
| `residual_pca_structure` | PASS | plans=['0:64@9b\|64:256@5b\|256:384@3b\|384:512@0b'] |
| `residual_pca_canonical_exact_scope` | PASS | scopes=['canonical_raw_float64_squared_L2'] |
| `residual_pca_finite_and_candidate_count` | PASS | nonfinite=False min_candidates=1321 |
| `residual_pca_complete_measurement_grid` | PASS | query_rows=99000 expected=99000 segment_rows=132 expected=132 |
| `matched_plan_and_serialized_bytes` | PASS | none |
| `matched_canonical_query_reference` | PASS | hashes={'current_pca': '210b361e3f35082f3103fbeb1557e7588e01e524e8c8688ea1fbf264f6f236a2', 'residual_pca': '210b361e3f35082f3103fbeb1557e7588e01e524e8c8688ea1fbf264f6f236a2'} |
| `canonical_query_reference_coverage` | PASS | queries=1000 rows=1000 |
| `summary_provenance_settings` | PASS | baseline=current_pca bootstrap=10000/20260710 |
| `summary_provenance_raw_binding` | PASS | none |
| `summary_provenance_output_binding` | PASS | none |

## Frozen Gate Conditions

### Gate A

- FAIL: `accurate_prefix_1_mean_per_query_candidate_rmse_ci_below_zero`
- FAIL: `accurate_prefix_1_mean_per_query_candidate_rmse_at_least_8_of_10`
- FAIL: `accurate_prefix_1_pooled_candidate_rmse_ci_below_zero`
- FAIL: `accurate_prefix_1_pooled_candidate_rmse_at_least_8_of_10`
- FAIL: `accurate_prefix_1_rotation_off_direction`
- FAIL: `full_mean_per_query_candidate_rmse_ci_below_zero`
- FAIL: `full_mean_per_query_candidate_rmse_at_least_8_of_10`
- FAIL: `full_pooled_candidate_rmse_ci_below_zero`
- FAIL: `full_pooled_candidate_rmse_at_least_8_of_10`
- FAIL: `full_rotation_off_direction`

### Gate B

- Not evaluated because an earlier preregistered gate failed.

### Gate C

- Not evaluated because an earlier preregistered gate failed.

## Interpretation Boundary

This is a fixed-candidate estimator replication. It does not establish an
end-to-end IVF Recall-QPS result, a learned-transform contribution, or a claim
about full-dimensional IVF partition quality.

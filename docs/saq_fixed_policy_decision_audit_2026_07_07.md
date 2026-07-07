# SAQ Fixed-Policy Decision Audit

Date: 2026-07-07

This note audits whether the current clean fixed-policy validation table follows
from the implemented query-unaware policy, rather than from manual cherry
picking after held-out query evaluation.

Primary table under audit:

```text
docs/saq_fixed_policy_clean_validation_table_2026_07_07.csv
```

Fresh matrix artifacts used for this audit:

```text
/tmp/saq-run/reports/fixed_policy_matrix_validation_2026_07_07.csv
/tmp/saq-run/reports/fixed_policy_applicability_scan_2026_07_07.csv
```

## 1. Implemented Decision Path

Candidate selection happens in `script/run_default_neighborhood_cross_dataset.py`.
The order is fixed:

```text
1. conservative_eligible
2. frontier_like
3. risky_fallback_best_score, only if --allow-risky-fallback is set
```

The conservative role is annotated by the scorer. With default flags, a
candidate is conservative only if all enabled ratios are no worse than default:

```text
pair_proxy_weighted_soft_inversion_penalty_ratio_vs_default <= 1.0
pair_proxy_weighted_ratio_mean_ratio_vs_default             <= 1.0
best_speed_proxy_ratio_vs_default                          <= 1.0
```

`conservative_role_max_nonzero_segments` defaults to `0`, so the positive-bit
segment-count guard is disabled in the current matrix.

The frontier-like fallback is narrower than risky fallback:

```text
best_recall_risk_score <= 1.0
best_speed_proxy_ratio_vs_default <= 1.0
```

It can promote candidates that miss the stricter soft-inversion / weighted-ratio
conservative guard, but only when recall-risk and speed proxy remain no worse
than default.

`--allow-risky-fallback` is diagnostic only. The report driver maps it to
`reject`, not `promote`:

```text
conservative_eligible -> promote
frontier_like -> promote
risky_fallback_best_score -> reject
no_candidate_selected or scorer_skipped_reason -> abstain
```

Two implementation details matter for interpreting outputs:

```text
frontier_like does not require conservative_role_is_eligible;
it checks only recall-risk <= 1 and speed-proxy <= 1.

risky_fallback_best_score can fill remaining evaluation slots when
--allow-risky-fallback is set and --max-eval-per-run > 1. The current fixed
matrix uses max_eval_per_run=1, so risky fallback appears only when no
conservative/frontier candidate has already filled the single slot.
```

## 2. Row-By-Row Audit

| run | shape / applicability | policy role | key proxy evidence | report decision | measured interpretation |
|---|---|---|---|---|---|
| `gist_full_K4096_B3` | multi + zero tail, 2 feasible non-default candidates | conservative | risk `0.9050`, speed `0.7780`, soft `0.9764`, weighted `0.9766` | promote | +0.00159 R@100 and 1.1119x QPS at np800 |
| `gist_full_K4096_B4` | multi + zero tail, 4 feasible non-default candidates | conservative | risk `0.9071`, speed `0.7792`, soft `0.9758`, weighted `0.9761` | promote | +0.00077 R@100 and 1.1948x QPS at np800 |
| `gist_full_K4096_B5` | multi + zero tail, 4 feasible non-default candidates | conservative | risk `0.9834`, speed `1.0000`, soft `0.9799`, weighted `0.9803` | promote | +0.00028 R@100 and 1.0793x QPS at np800 |
| `cifar60k_B3` | multi + zero tail, 3 feasible non-default candidates | frontier_like | risk `0.9941`, speed `1.0000`; conservative failed on soft/weighted ratios just above 1 | promote | +0.0004 R@10 and 1.0761x QPS at np200 |
| `cifar60k_B4` | multi + zero tail, 3 feasible non-default candidates | frontier_like | risk `0.9617`, speed `0.7212`; conservative failed on soft/weighted ratios | promote | +0.0004 R@10 and 1.0745x QPS at np200 |
| `cifar60k_B5` | multi + zero tail, 3 feasible non-default candidates | frontier_like | risk `0.9937`, speed `1.0000`; conservative failed on soft/weighted ratios just above 1 | promote | +0.0008 R@10 and 1.0609x QPS at np200 |
| `deep1M_sample100k_B4` | multi, no zero tail, 1 feasible non-default candidate | risky fallback diagnostic | risk `1.6434`, speed `0.9962`; conservative failed on soft/weighted ratios | reject | QPS improves but R@100 drops by 0.02757 at np200 |
| `deep1M_sample100k_B5` | multi, no zero tail, 1 feasible non-default candidate | risky fallback diagnostic | risk `1.6434`, speed `0.9970`; conservative failed on soft/weighted ratios | reject | QPS improves but R@100 drops by 0.01429 at np200 |
| `audio_K4096_B4` | single uniform, 0 feasible non-default candidates | no candidate | scorer skipped: `generator_produced_no_non_default_candidates` | abstain | scan also abstains at B=3/B=5 |
| `word2vec_sample100k_B4` | single uniform, 0 feasible non-default candidates | no candidate | scorer skipped: `generator_produced_no_non_default_candidates` | abstain | scan also abstains at B=3/B=5 |

## 3. Boundary Cases

### GIST B=4: lower risk is not automatically promoted

The GIST B=4 `head_split` candidate has lower recall-risk than the selected
plan:

```text
64:9,64:7,128:6,320:4,256:2,128:0
recall-risk=0.8487, speed-proxy=1.2153
```

It is not conservative because the speed proxy is worse than default. The fixed
policy therefore selects the speed-safe conservative point:

```text
128:9,320:5,320:3,192:0
recall-risk=0.9071, speed-proxy=0.7792
```

This supports the current story: the policy is not a pure recall-risk optimizer.
It explicitly balances recall-risk and speed proxy.

### GIST B=5: raw v3 false-positive shape is guarded out

The known raw v3 false-positive shape appears in the candidate set:

```text
64:9,64:8,128:7,320:5,320:3,64:0
recall-risk=0.8666, speed-proxy=1.2141,
soft=1.0191, weighted=1.0187
```

It fails all three conservative role dimensions and is not frontier-like because
speed-proxy is above 1. The promoted B=5 plan is instead:

```text
128:9,128:7,320:5,320:3,64:0
recall-risk=0.9834, speed-proxy=1.0000,
soft=0.9799, weighted=0.9803
```

This confirms that the conservative guard blocks the specific false-positive
failure mode that motivated the fixed-policy role selection.

### CIFAR: frontier-like fallback is needed but narrow

CIFAR B=3/B=4/B=5 positives are not conservative because their soft-inversion
and weighted-ratio proxies are slightly above default. They are promoted only
because both required frontier-like conditions hold:

```text
recall-risk <= 1.0
speed-proxy <= 1.0
```

The DEEP controls show why this fallback cannot be widened casually: DEEP has
speed-proxy below 1 but recall-risk `1.6434`, so it does not pass frontier-like
promotion and remains a reject diagnostic.

### Audio and word2vec: abstention is an explicit outcome

Audio and word2vec B=4 are not failed experiments. They are policy abstentions:
the default plans are single uniform segments and the generator produces no
feasible non-default plan under the current default-neighborhood rules. This is
part of the method boundary.

## 4. Audit Conclusion

The clean validation table is internally consistent with the implemented
fixed-policy decision path:

```text
GIST positives: conservative promotion
CIFAR positives: narrow frontier-like promotion
DEEP controls: risky fallback diagnostic mapped to reject
audio/word2vec: no-candidate abstention
```

No row requires using held-out query labels to choose the candidate. Held-out
queries enter only after selection, through safe-searcher recall/QPS evaluation.

The main threat to validity is not a decision-path inconsistency. It is that the
frontier-like fallback is empirical and currently supported mainly by CIFAR
small-positive cases. Any future widening of this fallback must be revalidated
against the DEEP reject controls and the GIST B=5 false-positive shape.

## 5. Report-Generation Caveats

The report driver is intentionally a summarizer, not a full scorer revalidator.
This creates a few caveats that future changes should keep visible:

1. `report_fixed_policy_validation.py` trusts the stored `selection_reason` and
   scorer fields in the summary CSV. It does not recompute conservative or
   frontier-like eligibility from raw scorer outputs.
2. If a malformed row had both a promotable `selection_reason` and a nonempty
   `scorer_skipped_reason`, promote/reject mapping would take precedence over
   abstention. The current matrix does not contain such rows.
3. `no_candidate_selected` can mean generator-empty, no scorer-selected
   candidate, risky fallback disabled, empty scorer output, or
   `--max-eval-per-run=0`. In the clean table, audio and word2vec are the
   explicit generator-empty case: `generator_produced_no_non_default_candidates`.
4. When multiple summary CSVs provide the same run, the report driver keeps the
   first row it reads. The clean report should therefore use an explicit source
   order, or a single matrix summary CSV, to avoid accidental duplicate-run
   ambiguity.

These caveats do not change the current table. They define what should be
checked if future scripts add multi-candidate reporting, new fallback roles, or
new summary sources.

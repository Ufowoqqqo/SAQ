# Default-Neighborhood Applicability Scan

Date: 2026-07-06

This note records a lightweight scan of where the current
default-neighborhood candidate generator has a meaningful local plan shape to
perturb.

The scan is query-unaware and does not build/evaluate indexes. It only reads
existing SAQ PCA variance artifacts:

```text
/tmp/saq-run/data/*/*_base_pca.vars.fvecs
```

It reuses the same SAQ default-plan DP reimplementation and
default-neighborhood generator used by the cross-dataset validation driver.

## Command

```bash
python script/scan_default_neighborhood_applicability.py \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_applicability_scan_2026_07_06
```

Default scan settings:

```text
B values: 3, 4, 5
min_positive_bits: 2
min_zero_tail_dim: 0
max_segments: 6
exclude_nonfinal_1bit: true
require_nonincreasing_bits: true
```

Important scope limit: `feasible_non_default_candidate_count` means the plan
passes the generator's shape/feasibility guards. It is not the v3 scorer's
`conservative_role_is_eligible` decision. The scorer requires base/cluster
artifacts and boundary-pair proxy computation, so it is a second-stage filter.

## Summary Table

| dataset | B | dim | top64 var share | default plan | shape | feasible non-default candidates | applicability |
|---|---:|---:|---:|---|---|---:|---|
| audio | 3 | 192 | 0.983 | `192:3` | single uniform | 0 | abstain |
| audio | 4 | 192 | 0.983 | `192:4` | single uniform | 0 | abstain |
| audio | 5 | 192 | 0.983 | `192:5` | single uniform | 0 | abstain |
| cifar60k | 3 | 512 | 0.785 | `64:8,128:4,192:2,128:0` | multi + zero tail | 3 | scan-worthy |
| cifar60k | 4 | 512 | 0.785 | `64:9,192:5,128:3,128:0` | multi + zero tail | 3 | scan-worthy |
| cifar60k | 5 | 512 | 0.785 | `64:10,128:6,256:4,64:0` | multi + zero tail | 3 | scan-worthy |
| deep1M_sample100k | 3 | 256 | 0.875 | `128:6,128:0` | multi + zero tail | 0 | abstain |
| deep1M_sample100k | 4 | 256 | 0.875 | `64:6,192:3` | multi, no zero tail | 1 | candidate exists |
| deep1M_sample100k | 5 | 256 | 0.875 | `64:7,192:4` | multi, no zero tail | 1 | candidate exists |
| gist_full | 3 | 960 | 0.774 | `64:9,192:5,320:3,192:1,192:0` | multi + zero tail | 2 | scan-worthy |
| gist_full | 4 | 960 | 0.774 | `64:11,192:6,320:4,256:2,128:0` | multi + zero tail | 4 | scan-worthy |
| gist_full | 5 | 960 | 0.774 | `64:11,192:7,320:5,320:3,64:0` | multi + zero tail | 4 | scan-worthy |
| gist_sample100k | 3 | 960 | 0.777 | `64:9,192:5,320:3,192:1,192:0` | multi + zero tail | 2 | scan-worthy |
| gist_sample100k | 4 | 960 | 0.777 | `64:11,192:6,320:4,256:2,128:0` | multi + zero tail | 4 | scan-worthy |
| gist_sample100k | 5 | 960 | 0.777 | `64:11,192:7,320:5,320:3,64:0` | multi + zero tail | 4 | scan-worthy |
| word2vec_sample100k | 3 | 300 -> 320 | 0.441 | `320:3` | single uniform | 0 | abstain |
| word2vec_sample100k | 4 | 300 -> 320 | 0.441 | `320:4` | single uniform | 0 | abstain |
| word2vec_sample100k | 5 | 300 -> 320 | 0.441 | `320:5` | single uniform | 0 | abstain |

## Readout

The scan separates the current method's applicability into three groups.

First, audio and word2vec are stable abstention cases under B=3/4/5. Their SAQ
default plan is a single uniform segment at each scanned budget, so the current
default-neighborhood rules have no local multi-segment structure to perturb.
This confirms that the previous audio/word2vec holdout abstentions are not
isolated B=4 accidents.

Second, GIST and CIFAR are the strongest candidate families. Their defaults are
multi-segment plans with zero tails across B=3/4/5, and the generator produces
multiple feasible non-default plans. These are the settings where scorer/eval is
most likely to be informative.

Third, DEEP is mixed. B=3 has a two-segment default with only one positive-bit
segment, so the current generator produces no non-default candidate. B=4 and
B=5 each produce one feasible `head_split` candidate, but prior measured B=4/B=5
risky-fallback results lost recall. So DEEP is useful as a negative/control
family, not as the best next positive target.

## Implications

This supports a more precise method boundary:

```text
The default-neighborhood method is applicable when SAQ's default DP creates a
multi-stage bit ladder, especially with a zero tail and enough middle/tail
positive dimensions to redistribute.
```

It is not meaningful when SAQ's default is already a single uniform segment.
Those cases should be reported as abstentions instead of forced into arbitrary
custom plans.

## Recommended Next Step

Run second-stage v3 scoring, then build/evaluate only the most informative
unmeasured settings:

1. CIFAR B=3 and B=5, because CIFAR B=4 was a small positive and the scan shows
   B=3/B=5 also have three feasible candidates.
2. GIST full B=3 and B=5, because GIST B=4 was the strongest positive and the
   neighboring budgets have feasible candidate sets.
3. Treat DEEP B=4/B=5 as negative controls unless the scorer produces a clearly
   conservative eligible plan.

Do not spend more evaluation time on audio or word2vec under the current
generator unless the generator itself is expanded beyond default-neighborhood
perturbations.

## Artifacts

```text
/tmp/saq-run/reports/default_neighborhood_applicability_scan_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_applicability_scan_2026_07_06.json
```

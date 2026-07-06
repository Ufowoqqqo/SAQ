# GIST Full Budget Holdout Validation

Date: 2026-07-06

This note records the fixed-policy GIST full K4096 validation for B=3 and B=5.
The goal was to test whether the strong GIST B=4 result extends across nearby
bit budgets.

The run used the fixed policy without risky fallback.

## Command

The intended combined command was:

```bash
python script/run_default_neighborhood_cross_dataset.py \
  --run gist_full_K4096_B3 \
  --run gist_full_K4096_B5 \
  --evaluate \
  --max-eval-per-run 1 \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_gist_budget_holdout_2026_07_06
```

B=3 failed during default index construction, so B=5 was rerun separately:

```bash
python script/run_default_neighborhood_cross_dataset.py \
  --run gist_full_K4096_B5 \
  --evaluate \
  --max-eval-per-run 1 \
  --output-prefix /tmp/saq-run/reports/default_neighborhood_gist_B5_holdout_2026_07_06
```

Shared setup:

```text
dataset: gist_full
K: 4096
metric/search distance: L2
topk: R@100
safe searcher: -searcher_safe_block_min_mode=2
compare nprobe: 50, 100, 200, 400, 800
QPS nprobe: 800
risky fallback: disabled
```

## Driver Fix

This run exposed an edge case in the cross-dataset driver. GIST B=3's SAQ
default plan contains a positive 1-bit segment:

```text
64:9,192:5,320:3,192:1,192:0
```

The fixed-policy generator uses `--filter-infeasible`,
`--min-positive-bits=2`, and `--exclude-nonfinal-1bit`, so that default row is
filtered from the candidate CSV. The scorer still needs the true default as its
reference. The driver now reads the generator `.summary.json` and passes the
default plan explicitly to the scorer via `--default-plan`.

This keeps the policy strict while avoiding a missing-default reference.

## B=3 Result

B=3 completed generation and v3 scoring, but default index build failed.

Default plan:

```text
64:9,192:5,320:3,192:1,192:0
```

Selected fixed-policy candidate:

```text
64:8,320:5,320:2,256:0
```

Scorer signal:

```text
selection: conservative_eligible
recall-risk score: 0.9050
speed-proxy ratio vs default: 0.7780
soft-inversion ratio vs default: 0.9764
weighted pair-ratio vs default: 0.9766
```

The selected custom plan builds successfully:

```bash
/rwproject/kdd-db/kluaq/saq/bin/create_index \
  -dataset gist_full \
  -K 4096 \
  -B 3 \
  -enable_PCA=true \
  -seg_plan=64:8,320:5,320:2,256:0 \
  -logtostderr=1
```

Output:

```text
index saved at: ./data/gist_full/ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca.index
Indexing time: 2.51766seconds
```

However, the default B=3 index build crashed:

```text
RUN bin/create_index -dataset gist_full -K 4096 -B 3 -enable_PCA=true -logtostderr=1
...
Dynamic bits allocation plan:
3bits: | 0 -> 64 (64d 9b) | 64 -> 256 (192d 5b) |
       | 256 -> 576 (320d 3b) | 576 -> 768 (192d 1b) |
       | 768 -> 960 (192d 0b)
...
RuntimeError: command failed with exit code -11
```

So B=3 is not a completed recall/QPS validation. It is currently a build-level
failure of SAQ's default B=3 GIST plan. Because the selected custom plan builds
successfully and removes the positive 1-bit segment, the likely failure surface
is the default 1-bit positive segment or its CAQ/index construction path. This
needs a focused build-level debug before B=3 can be measured fairly.

## B=5 Result

B=5 completed end-to-end and is positive.

Default plan:

```text
64:11,192:7,320:5,320:3,64:0
```

Selected fixed-policy candidate:

```text
128:9,128:7,320:5,320:3,64:0
```

Selection:

```text
selection: conservative_eligible
candidate family: head_widen_keep_levels
recall-risk score: 0.9834
speed-proxy ratio vs default: 1.0000
```

Measured R@100:

```text
nprobe 50:  0.74509 -> 0.74519  (+0.00010)
nprobe 100: 0.86680 -> 0.86687  (+0.00007)
nprobe 200: 0.94659 -> 0.94664  (+0.00005)
nprobe 400: 0.98386 -> 0.98399  (+0.00013)
nprobe 800: 0.99319 -> 0.99347  (+0.00028)
```

QPS at nprobe 800:

```text
default:  988.881
custom:  1067.299
ratio:   1.079x
```

## Interpretation

B=5 reinforces the GIST result:

- GIST B=4 was already a strong positive case.
- GIST B=5 is also positive end-to-end: small recall gain at every measured
  nprobe and about 7.9% higher QPS.
- The selected B=5 plan is the same broad pattern as CIFAR B=3/B=5:
  widen the first segment from 64 to 128 dimensions and lower its bitwidth.

B=3 is informative in a different way:

- The scorer finds a strong conservative-eligible candidate.
- The candidate removes the default plan's positive 1-bit segment and builds
  successfully.
- The original SAQ default B=3 plan crashes during index construction, so the
  current validation pipeline cannot measure it until that build path is fixed.

This adds a concrete SAQ failure surface: low-budget GIST can produce a default
plan with an internal 1-bit positive segment that passes the paper-style DP but
breaks the current implementation's index construction path.

## Artifacts

B=3 scorer and custom-build artifacts:

```text
/tmp/saq-run/reports/gist_full_K4096_B3_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B3_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/data/gist_full/ivf4096_b3_caq_adj_seg_plan64x8_320x5_320x2_256x0_pca.index
```

B=5 end-to-end artifacts:

```text
/tmp/saq-run/reports/default_neighborhood_gist_B5_holdout_2026_07_06.csv
/tmp/saq-run/reports/default_neighborhood_gist_B5_holdout_2026_07_06.json
/tmp/saq-run/reports/gist_full_K4096_B5_default_neighborhood_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B5_default_neighborhood_scored_auto_2026_07_06.*
/tmp/saq-run/reports/gist_full_K4096_B5_plan128x9_128x7_320x5_320x3_64x0_compare_np*_top100_2026_07_06.csv
```

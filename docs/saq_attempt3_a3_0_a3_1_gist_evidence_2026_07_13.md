# Attempt 3 A3-0/A3-1: GIST Distance-Quality Evidence

Date: 2026-07-13

## Decision

```text
A3-0 evaluator:                         PASS
A3-1a recovery-grid frontier support:  INSUFFICIENT_FRONTIER_SUPPORT
A3-1b historical-union replay:         METRIC_SENSITIVITY_FOUND_ON_ONE_SETTING
method or paper contribution:          NOT ESTABLISHED
next authorized stage:                 A3-2 FROZEN NEGATIVE CONTROL
```

The paper-exact metric changes the interpretation of one historical GIST
operating point. It does not revive the fac-error planner as a contribution,
and it does not authorize metric-aware plan fitting.

## Question

The earlier fac-error plan was rejected because it could not recover the
default plan's `R@100=0.99132` before losing its QPS advantage. Does that
conclusion change when geometric result quality is measured by paper-exact
`1/Ratio@100`?

## Setting

```text
dataset:                  gist_sample100k
base vectors:             100,000
queries:                  1,000
dimension:                960
IVF centroids K:          512
average bits/dimension B: 4
top-k:                    100
PCA:                      enabled, full 960 dimensions
threads:                  24
safe block-min mode:      2
variance-bound m:         4
nprobe grid:              {20,50,100,160,200,220,240,280,300,320,400}
QPS repetitions:          10 per row
```

Full-dimensional PCA is an orthogonal coordinate change, so Euclidean
distance should be preserved apart from stored-float numerical effects. The
evaluator recomputes float64 true distances from the stored PCA base/query
vectors and uses the sample-specific top-1000 ground-truth identifiers.

The two fixed plans are:

```text
SAQ default:  64x11_192x6_320x4_256x2_128x0
fac-error:    192x9_512x4_256x0
```

The first number in each term is segment dimensionality and the second is bits
per dimension. The index format, CAQ encoder, estimator, pruning, heap, and
search configuration are unchanged.

## A3-0 Evaluator Validation

The new evaluator computes, per query,

```text
1/Ratio@k = k / sum_i returned_euclidean_distance_i /
                       exact_euclidean_distance_i.
```

It recomputes true distances, sorts exact and returned sets independently by
true distance, and uses float64 accumulation. It stops on zero exact distance,
invalid or duplicate IDs, non-finite input, truncated rows, and a score above
one beyond the frozen numerical tolerance.

Eighteen deterministic Python tests pass, including exact retrieval,
identifier-disjoint equal-distance retrieval, a hand-computed ratio, returned
ID reordering, Euclidean-versus-squared distance, malformed input, provenance
output, frontier interpolation, and paired-query summaries.

The upstream `utils::get_ratio` is not used as the scientific artifact. It
reports forward `Ratio`, skips exact squared distances below `1e-5`, and does
not preserve query-level values. On the default `nprobe=200` sanity row, the
new evaluator exactly reproduces Recall `0.99132` and reports
`1/Ratio=0.999985300968`; the upstream CSV reports forward ratio
`1.0000147`, which is numerically consistent but semantically different.

## Protocol Correction Before A3-1b

A3-1a used only the historical fac-error recovery grid
`{200,220,240,280,300,320}`. That grid begins at the old high-Recall operating
point and truncates the lower-effort region that `1/Ratio` is designed to
evaluate. No Pareto conclusion was drawn from A3-1a.

Before the corrected run, commit `af7ab75` froze A3-1b as the union of nprobe
values that existed in the two pre-Attempt-3 GIST experiment families. Both
plans were then rerun at every value in the union. No new value was selected
from the A3-1a quality outcomes.

## A3-1b Complete Table

| nprobe | default R@100 | fac-error R@100 | default 1/Ratio | fac-error 1/Ratio | default QPS | fac-error QPS | same-nprobe QPS ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.75957 | 0.75952 | 0.993860620 | 0.993858359 | 31234.2 | 36687.1 | 1.175x |
| 50 | 0.92809 | 0.92769 | 0.998671018 | 0.998668346 | 20104.2 | 25581.3 | 1.272x |
| 100 | 0.98140 | 0.98069 | 0.999773561 | 0.999769939 | 13825.0 | 18572.6 | 1.343x |
| 160 | 0.99036 | 0.98958 | 0.999964379 | 0.999960461 | 10524.5 | 14189.3 | 1.348x |
| 200 | 0.99132 | 0.99059 | 0.999985301 | 0.999981452 | 9264.9 | 12333.9 | 1.331x |
| 220 | 0.99149 | 0.99079 | 0.999987377 | 0.999983555 | 8777.6 | 11739.0 | 1.337x |
| 240 | 0.99153 | 0.99084 | 0.999988670 | 0.999984881 | 8313.8 | 11073.8 | 1.332x |
| 280 | 0.99163 | 0.99091 | 0.999991688 | 0.999987869 | 7579.7 | 9986.9 | 1.318x |
| 300 | 0.99164 | 0.99091 | 0.999992743 | 0.999988921 | 7329.5 | 9522.1 | 1.299x |
| 320 | 0.99164 | 0.99091 | 0.999993271 | 0.999989447 | 7035.6 | 9086.9 | 1.292x |
| 400 | 0.99164 | 0.99091 | 0.999993271 | 0.999989447 | 6111.4 | 7784.3 | 1.274x |

At every common nprobe, fac-error is faster but has slightly lower Recall and
slightly lower mean `1/Ratio`. The scientific comparison therefore requires
matched quality rather than same-nprobe values.

## Historical-Point Reinterpretation

The frozen reference is the historical default `nprobe=200` row:

```text
Recall@100 target:   0.991320000000
1/Ratio@100 target:  0.999985300968
default QPS:         9264.923
```

Under Recall, the fac-error frontier cannot reach the target; its measured
maximum is `0.99091`. This reproduces the old negative conclusion.

Under `1/Ratio`, the fastest measured fac-error row at or above the target is:

```text
fac-error nprobe=280
1/Ratio@100 = 0.999987869279
QPS         = 9986.910
QPS ratio   = 1.07793x over default nprobe=200
```

Thus the fac-error row directly dominates the historical default point in
mean distance quality and QPS, without interpolation. Adjacent-point linear
interpolation between fac-error `nprobe=240` and `280` estimates `10921.108`
QPS exactly at the reference distance quality, or `1.17876x`; this is secondary
evidence because it is interpolated.

## Query-Level Evidence

For measured fac-error `nprobe=280` minus default `nprobe=200`:

```text
mean delta:       +2.5683e-6
median delta:      0
minimum delta:    -3.1166e-4
p01 delta:        -1.1754e-4
p05 delta:        -4.1993e-5
fraction worse:    39.6%
fraction equal:    23.0%
fraction better:   37.4%
```

The alternative improves mean distance quality and its marginal minimum,
`p01`, and `p05` are all higher than the reference row. Nevertheless, 39.6%
of paired queries are individually worse, and the worst paired loss is not
zero. The result supports an aggregate geometric-quality reinterpretation; it
does not establish per-query dominance or a quality guarantee.

## Provenance

Search code and protocol:

```text
branch:                  saq-ratio-metric-analysis
result-export commit:    572d026
A3-1b protocol commit:   af7ab75
```

Input hashes:

```text
base PCA fvecs:   f8d53a1de73c641f07f2d5d46d40710f22582f5bf12899cf8e51a2e53c196f12
query PCA fvecs:  df50509b12a0300e469b0f6f9ba58dbfcbd4700e381778d4851980f0e22d1729
ground truth:     a667968e7ca31749f22495bddacf457c83ee353979d81aae736764e5265a8748
default index:    e3aa7afefcd139c540e41890f614c571af3046cc08b6c042cc6030ab1e59a3cc
fac-error index:  03c0edb44a7094060c2958b7fed50cd0b303d804a64e9e82dc034f6c40eb816b
```

The compact artifact records the 22 QPS rows, result-ID hashes, input hashes,
nondominated frontier labels, matched-point calculation, and paired-query
statistics:

```text
docs/saq_attempt3_a3_1b_artifacts_2026_07_13/
  gist_sample100k_k512_b4.csv
  gist_sample100k_k512_b4.json
```

Raw `.ivecs` results and logs remain under
`/tmp/saq-ratio-a3/gist_sample100k_union/` and are not committed.

## Commands

Each row used the same command shape:

```bash
bin/test_qps \
  -dataset=gist_sample100k -K=512 -B=4 -enable_PCA=true \
  -fix_nprobe=<frozen-value> -fix_thread=24 \
  -searcher_safe_block_min_mode=2 -searcher_vars_bound_m=4 \
  -index_file=<default-or-fac-error-index> \
  -result_file=<row-output-prefix> \
  -result_ids_file=<row-output.ivecs>
```

The evaluator and summarizer were then run as:

```bash
python script/evaluate_inverse_ratio.py \
  --base <base-pca.fvecs> --queries <query-pca.fvecs> \
  --groundtruth <sample-groundtruth.ivecs> \
  --results <label=result.ivecs> ... \
  --k 100 --dataset gist_sample100k --output <inverse-ratio.json>

python script/summarize_ratio_frontier.py \
  --metrics <inverse-ratio.json> --qps-dir <registered-row-directory> \
  --reference-label default_np200 \
  --default-plan default --alternative-plan fac_error \
  --output-prefix \
    docs/saq_attempt3_a3_1b_artifacts_2026_07_13/gist_sample100k_k512_b4
```

The normal clean CMake configuration could not locate the relocated local
`glog`, `fmt`, and `gflags` packages. `test_qps` was compiled with the exact
Release compiler and linker flags recorded by the existing SAQ build, using
headers and libraries under `/tmp/saq-deps/usr`. This is an environment
limitation to resolve before a clean-machine reproduction claim.

## Interpretation

The strongest supported statement is:

```text
On the frozen GIST sample100k/K512/B4 comparison, Recall rejects the fac-error
plan at the historical default operating point, while paper-exact 1/Ratio
identifies a measured fac-error operating point with higher mean geometric
quality and 1.078x QPS.
```

This is a real metric-sensitive conclusion, but it is not yet a method result:

1. `1/Ratio` is established prior work.
2. Both alternatives are SAQ plans; there is no independent baseline.
3. The evidence uses one sampled dataset and one bit budget.
4. The fac-error objective remains empirical, expensive offline, and weak in
   novelty.
5. Query-level paired losses remain for a substantial fraction of queries.
6. The `1/Ratio` paper itself reports largely stable algorithm rankings.

Do not reopen the fac-error planner or update the meeting headline yet. Run the
predeclared DEEP rejected-plan negative control. If `1/Ratio` accepts every
faster but lower-Recall plan, the metric is not discriminative enough to
support a project-specific mechanism. If DEEP remains negative while GIST
changes, Attempt 3 has a more credible metric-sensitivity boundary, still not
a contribution by itself.


# Single-Global Segment-Cost Frontier

## Question

Can SAQ's global variance-driven segment planner account for search-time segment
cost while keeping one dataset-level plan, no representative-query learning, and
no mixed per-cluster plan dispatch?

The first offline test is deliberately conservative. If segment-cost-aware DP is
to become a strong standalone direction, the cleanest evidence would be a global
plan that weakly dominates the SAQ default: no higher variance-risk and lower
implementation-derived segment cost. If no such plan exists, the direction may
still yield a risk-cost frontier, but it should not be framed as a free
improvement over SAQ.

## Method

The script `script/global_segment_cost_frontier.py` reproduces SAQ's global DP
over PCA variance blocks and then computes metric-specific Pareto frontiers. It
uses only base/index artifacts, specifically the one-row PCA variance `.fvecs`
files already generated for the datasets. It does not use benchmark queries and
does not build an index.

The analysis avoids an arbitrary weighted objective such as
`risk + lambda * cost`. Instead, each cost term is evaluated as a separate
Pareto objective against SAQ's variance-risk:

- `positive_dim`: number of dimensions assigned a positive bit width.
- `total_code_bit_volume`: sum of `segment_dim * bits` over positive segments.
- `accurate_extra_bit_volume`: sum of `segment_dim * (bits - 1)` over positive
  segments, used as a proxy for work beyond the 1-bit coarse component.
- `positive_segments`: number of non-zero segments.
- `segment_factor_bits`: per-segment stored factor overhead, 64 bits per
  positive segment in the current SAQ layout.
- `zero_tail_risk`: PCA variance mass assigned to zero-bit tail dimensions.

For each metric, the script reports whether any frontier plan dominates the SAQ
default. It also reports the lowest-risk lower-cost plan, which answers: if we
force this cost to decrease, what is the smallest variance-risk penalty visible
on the frontier?

## Offline Results

Across the available B=3/B=4/B=5 matrix, no case produced a lower-cost plan with
no worse variance-risk than the SAQ default for any of the evaluated cost
metrics. In every case, the SAQ default was the exact minimum-risk final DP state
under the reproduced SAQ objective and was not dominated on the metric-specific
frontiers.

The B=4 matrix is the clearest snapshot:

| dataset | SAQ default plan | positive dim | positive segments | code bit volume | default dominated? | closest lower code-volume risk ratio | closest lower positive-dim risk ratio | closest lower segment-count risk ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GIST full K4096 | `64:11,192:6,320:4,256:2,128:0` | 832 | 4 | 3648 | no | 1.0100 | 1.0116 | 1.0233 |
| GIST sample100k | `64:11,192:6,320:4,256:2,128:0` | 832 | 4 | 3648 | no | 1.0099 | 1.0107 | 1.0227 |
| CIFAR60K | `64:9,192:5,128:3,128:0` | 384 | 3 | 1920 | no | 1.1104 | 1.3213 | 1.2162 |
| DEEP sample100k | `64:6,192:3` | 256 | 2 | 960 | no | 1.0164 | 1.1260 | 1.1260 |
| audio K4096 | `192:4` | 192 | 1 | 768 | no | 2.0000 | 16.0000 | 16.0000 |
| word2vec sample100k | `320:4` | 320 | 1 | 1280 | no | 1.0319 | 1.5863 | 16.0000 |

The closest lower-code-volume frontier ratios across bit budgets were:

| dataset | B=3 | B=4 | B=5 |
|---|---:|---:|---:|
| GIST full K4096 | 1.0236 | 1.0100 | 1.0029 |
| GIST sample100k | 1.0220 | 1.0099 | 1.0010 |
| CIFAR60K | 1.1029 | 1.1104 | 1.0612 |
| DEEP sample100k | 1.3205 | 1.0164 | 1.0164 |
| audio K4096 | 2.0000 | 2.0000 | 2.0000 |
| word2vec sample100k | 1.0319 | 1.0319 | 1.0319 |

The closest lower-positive-dimension frontier ratios were:

| dataset | B=3 | B=4 | B=5 |
|---|---:|---:|---:|
| GIST full K4096 | 1.0010 | 1.0116 | 1.0439 |
| GIST sample100k | 1.0008 | 1.0107 | 1.0401 |
| CIFAR60K | 1.0297 | 1.3213 | 1.1169 |
| DEEP sample100k | 2.8196 | 1.1260 | 1.6255 |
| audio K4096 | 8.0000 | 16.0000 | 32.0000 |
| word2vec sample100k | 1.4906 | 1.5863 | 2.7076 |

## Interpretation

This first study weakens the simplest segment-cost-aware DP claim. Under the
current global SAQ variance-risk objective, the default plan is already a
Pareto-stable minimum-risk point for these static implementation-derived cost
terms. A single-global cost-aware planner does not appear to provide a no-cost
correction analogous to the earlier local custom-plan observations.

The only potentially useful signal is a tradeoff, not a dominance result. GIST
has near-frontier alternatives whose code-volume risk penalty is around 1% at
B=4 and even smaller at B=5, but the actual benefit must be justified by
end-to-end recall/QPS evaluation. For CIFAR, DEEP, audio, and word2vec, the
positive-dimension or segment-count reductions usually require much larger
variance-risk increases.

For a strict reviewer, the current evidence says that segment-cost-aware global
DP is not yet a method. It is a structured limitation analysis: if we keep one
global plan and refuse query labels, SAQ's default variance DP is difficult to
dominate with simple static cost terms. Any next method must explain why a
specific point on the frontier is worth selecting before held-out evaluation,
without adding arbitrary cost weights.

## Reproduction

Example command:

```bash
python script/global_segment_cost_frontier.py \
  --case gist_full_K4096_B4_global_cost_frontier \
  --vars-file /tmp/saq-run/data/gist_full/gist_full_base_pca.vars.fvecs \
  --avg-bits 4 \
  --output-prefix /tmp/saq-run/global_cost_dp/gist_full_K4096_B4_global_cost_frontier
```

Generated artifacts are written under `/tmp/saq-run/global_cost_dp/` as
`.candidates.csv`, `.frontier.csv`, `.summary.json`, and `.md` files. The CSVs
are not committed because they are generated experiment artifacts.

## Next Step

Do not broaden this into a large sweep yet. The follow-up end-to-end check is
recorded in `docs/gist_near_frontier_end_to_end_2026_07_08.md`. It tested two
GIST full/K4096/B=4 near-frontier plans under safe search. Both candidates had
slightly higher recall, but both were slower than the SAQ default across
`nprobe = 100, 200, 400`.

This satisfies the stop condition for the simple static-cost hypothesis. Unless
a stronger search-time execution model is introduced, single-global
segment-cost-aware DP should be treated as SAQ limitation evidence rather than
the main method.

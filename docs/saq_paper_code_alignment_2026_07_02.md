# SAQ Paper-Code Alignment Audit

Date: 2026-07-02

This is the first direct alignment pass between the SAQ arXiv TeX source and the
local C++ implementation. It should supersede second-hand summaries when we make
technical decisions.

Local paper source:

```text
paper_src/2509.12086/main.tex
```

Local code branch when this note was written:

```text
branch = saq-boundary-audit
```

## 1. Bottom Line

The external summary was directionally useful, but it hid several details that
matter for our next step.

1. SAQ's main build-time quantization plan is query-unaware in the implementation.
   The paper derives a segment error model with a query/data same-distribution
   assumption, but the footnote explicitly says the normal/query assumption can be
   dropped and empirical per-dimension variance can be used instead.
2. The code implements that empirical-variance version: the DP objective is
   essentially `var_sum / 2^b`, using `data_variance` loaded from the dataset or
   computed from the base vectors.
3. The strongest query-unaware gap is not "SAQ ignores query workload". The more
   code-grounded gap is that SAQ learns one global PCA-variance segment plan and
   applies it to IVF cluster residual quantization.
4. Earlier rank-boundary/query-aware ideas should be retained only as diagnostics
   or upper-bound probes, not as the main method.
5. The paper's DP is presented as optimal under a clean model, while the code has
   important practical constraints: 64-dimensional segment granularity, per-segment
   factor overhead, a maximum segment count, and a relaxed update rule.

## 2. Paper-Code Map

| Component | Paper source | Code source | Alignment status |
| --- | --- | --- | --- |
| E-RaBitQ bottleneck | `main.tex:506-511` | baseline motivation only | Paper motivates CAQ by E-RaBitQ's `O(2^B * D log D)` encoding cost. |
| CAQ removes unit-norm coupling | `main.tex:539-541` | `saqlib/quantization/caq/caq_encoder.hpp:57-141` | Code adjusts independent scalar codes to improve direction alignment instead of enforcing unit norm. |
| CAQ scalar initialization | `main.tex:555-565` | `saqlib/quantization/caq/caq_encoder.hpp:184-209` | Code uses symmetric range `[-v_mx, v_mx]`, computes `delta`, floors to integer code, and accumulates `<o, oa>` / `|oa|^2`. |
| CAQ cosine objective | `main.tex:567-576` | `saqlib/quantization/caq/caq_encoder.hpp:87-114` | Paper tries one-step `+/- Delta`; code uses while loops to keep moving a coordinate while the cosine condition improves. |
| Adjustment rounds and complexity | `main.tex:594-614` | `saqlib/quantization/config.h:16`, `src/define_options.h:21-24` | Paper recommends `r in [4, 8]`; code default is `caq_adj_rd_lmt=6`. |
| CAQ factors and estimator | `main.tex:616`, `main.tex:631-641` | `saqlib/quantization/caq/caq_encoder.hpp:222-243`, `saqlib/quantization/caq/caq_estimator.hpp:190-215` | Code stores `|o|`, `rescale=|o|^2/<o,oa>`, and computes squared L2 via `|q|^2 + |o|^2 - 2<q,o>_est`. |
| Progressive code prefix | `main.tex:644-645` | `saqlib/quantization/quantizer.hpp:166-205`, `saqlib/quantization/saq_searcher.hpp:111-157` | Code separates MSB short code from remaining long code; normal search uses MSB fast stage then full-code refinement. |
| PCA variance segmentation | `main.tex:688-693`, `main.tex:729-738` | `saqlib/quantization/saq_data.hpp:85-127`, `src/create_index.cpp:30-50` | Code loads `*_base_pca.vars.fvecs` if present, otherwise computes base-vector empirical variance. |
| SAQ segment error model | `main.tex:743-752` | `saqlib/quantization/saq_data.hpp:179-188` | Paper gives `sum E[|o_i q_i|] / 2^(B+1)` and then a variance form; code uses `var_sum / (1 << b)`, dropping constants irrelevant to argmin. |
| Quantization plan DP | `main.tex:759-802` | `saqlib/quantization/saq_data.hpp:147-227` | Code implements DP over padded 64-dim blocks, bit budget, segment count, and bitwidth. |
| 64-dim segmentation granularity | `main.tex:801-802` | `saqlib/defines.hpp:14-16`, `saqlib/quantization/saq_data.hpp:140-181` | Code fixes `kDimPaddingSize=64`; this exactly explains the paper's low-dimensional DEEP limitation. |
| Per-segment CAQ | `main.tex:738`, `main.tex:805` | `saqlib/quantization/saq_quantizer.hpp:40-58`, `saqlib/quantization/quantizer.hpp:44-64` | Code slices contiguous PCA dimensions by global plan, then quantizes each segment as a CAQ vector. |
| Random rotation inside segment | `main.tex:738` | `saqlib/quantization/quantizer_data.hpp:19-23`, `saqlib/quantization/quantizer.hpp:44-50` | Each segment can get its own random orthogonal rotation before residual CAQ. |
| IVF cluster residual quantization | experiment setting in `main.tex:897-900` | `saqlib/index/ivf.hpp:130-183`, `saqlib/quantization/quantizer.hpp:44-64` | One global plan is learned, then each cluster uses that plan on `vector - centroid` residuals. |
| Multi-stage variance bound | `main.tex:837-862` | `saqlib/quantization/saq_estimator.hpp:28-45`, `saqlib/quantization/caq/caq_estimator.hpp:80-82` | Code computes `sqrt(sum variance_i * query_i^2)` per segment and multiplies by `searcher_vars_bound_m`. |
| Multi-stage search flow | `main.tex:837-862` | `saqlib/quantization/saq_searcher.hpp:94-157` | Code first uses variance-only lower-bound, then MSB fast distance segment by segment, then full-code refinement. |
| Experiment metrics | `main.tex:947-950` | `src/test_relative_error.cpp:45-133`, `src/test_qps.cpp:49-137` | Paper uses relative error and Recall@100; code test binaries use `TOPK=100`. |
| IVF settings | `main.tex:897-900`, `main.tex:1026-1027` | `src/define_options.h:14-16`, `src/test_relative_error.cpp:157-168` | Defaults line up with `K=4096`, PCA on, and `nprobe=200` for large K relative-error tests. |

## 3. Key Formula Alignment

Paper Eq. `seg-err` says:

```text
ERROR(Seg, B)
  = sum_{i in Seg} E[|o_i q_i|] / 2^(B+1)
  = (1 / (2^B * pi)) * sum_{i in Seg} sigma_i^2
```

The important footnote at `main.tex:749` says the query/data same-distribution
and normal assumptions can be dropped by simply using empirical per-dimension
variance.

The implementation does exactly the constant-free empirical form:

```cpp
auto v = var_sum / (1 << b);
```

in `saqlib/quantization/saq_data.hpp:187`.

The constants `1/2`, `1/pi`, and any uniform scale do not affect the argmin for a
fixed plan space, so the code is consistent with the paper's intended practical
version. This also means our earlier phrasing should be precise:

```text
SAQ's paper contains a query/data distribution assumption in the derivation, but
SAQ's implemented build-time planner is data-variance driven and query-unaware.
```

## 4. Implementation Constraints Behind "Optimal DP"

The paper presents the DP as finding an optimal plan under the modeled error and
quota. The implementation is more constrained:

- dimensions are padded and segmented in multiples of 64: `kDimPaddingSize=64`;
- bitwidth is limited by `KMaxQuantizeBits=13`;
- every nonzero-bit segment consumes extra factor overhead:

  ```cpp
  num_bit_factors = 2 * sizeof(float) * 8
  B_new = used_bits + b * segment_dim + num_bit_factors
  ```

- zero-bit tail segments are allowed through `err0 = var_sum`;
- max segment count is capped, and for `avg_bits >= 2` it is at most half the
  number of 64-dim blocks;
- the answer update uses a `1.01` improvement threshold, so later plans must be
  more than about 1% better to replace an earlier accepted plan.

Therefore, in our own writing, avoid saying "SAQ solves the exact optimal
segmentation problem" without qualification. A better wording is:

```text
SAQ searches the best practical global contiguous PCA segment plan under its
variance proxy, 64-dim granularity, factor overhead, and segment-count cap.
```

## 5. Query-Unaware Implications

The paper-code alignment supports the advisor's feedback.

A query-aware follow-up is not the best main direction because:

- SAQ's implemented planner already avoids query workload dependence;
- the paper explicitly discusses query/data distribution only as part of the
  error-model derivation, then allows empirical variance;
- a workload-aware planner would change the problem setting and would need a
  strong justification for why build-time representative queries are available.

The strongest code-grounded query-unaware gap is:

```text
SAQ learns one global PCA-variance plan, but then quantizes IVF cluster residuals
with that same plan. The paper does not model whether global variance remains a
good proxy for local residual variance or local quantization risk inside each
cluster.
```

This gap is visible in the local code path:

1. `IVF::construct` loads or computes global variance and builds one `SaqData`
   plan: `saqlib/index/ivf.hpp:138-146`.
2. `allocate_clusters` gives every cluster the same quantization plan:
   `saqlib/index/ivf.hpp:186-193`.
3. `SAQuantizer::quantize_cluster` slices each cluster residual by that global
   plan: `saqlib/quantization/saq_quantizer.hpp:40-58`.
4. `QuantizerCluster::quantize` subtracts each cluster centroid and runs CAQ:
   `saqlib/quantization/quantizer.hpp:44-64`.

This is a clean query-unaware entry point.

## 6. What To Correct In Our Mental Model

1. Do not present "query-aware SAQ" as the primary novelty path.
   It may remain a diagnostic or upper-bound comparison.
2. Do not say SAQ's planner literally optimizes top-k recall, rank boundary, or
   workload distribution. It optimizes a variance proxy for distance error.
3. Do not say SAQ's DP is an unconstrained exact DP. The implementation uses
   64-dim blocks and factor-overhead-aware budget accounting.
4. Do not assume the multi-stage estimator reorders segments dynamically by query.
   The code processes the plan order; under normal PCA plans this is usually
   high-variance to low-variance, but equal-segment or nonstandard plans should
   be interpreted carefully.
5. Be careful with metric claims. Paper accuracy experiments use Recall@100 and
   `nprobe=200`; local earlier `vectordb` CIFAR R@10 settings are not directly
   comparable.

## 7. Next Concrete Task

The next implementation task should be a query-unaware segment diagnostic tool,
not a query-aware allocator.

Proposed output table:

```text
segment_id,start_dim,end_dim,dim_len,bits,
global_var_sum,global_var_share,
cluster_residual_var_mean,cluster_residual_var_p90,
cluster_residual_var_share_mean,cluster_residual_var_share_p90,
within_segment_top1_var_share,within_segment_top8_var_share
```

Inputs should come from normal SAQ build artifacts:

```text
*_base_pca.fvecs
*_centroid_{K}_pca.fvecs
*_cluster_id_{K}.ivecs
*_base_pca.vars.fvecs
quant_plan extracted from create_index logs or index metadata
```

The first sanity case can use the existing `audio` B=1 plan:

```text
0 -> 64 (64d 3b); 64 -> 192 (128d 0b)
```

For `audio` B=2/4/8, default SAQ has one segment, so use either `-seg_eqseg` or
move to a higher-dimensional dataset where default SAQ creates multiple segments.

## 8. Minor Code Observations To Revisit Later

These are not blockers for the paper-code alignment, but they are worth tracking:

- `IVF::quant_metrics_` is written by `src/create_index.cpp`, but a quick search
  only found per-quantizer metric insertion and no obvious aggregation back to
  `IVF::quant_metrics_`. Do not rely on that CSV metric until verified.
- `SaqData::load` checks `data_variance.cols() == num_dim`; if saved variance is
  padded, this may matter on non-64-aligned dimensions. Existing datasets may hide
  this if dimensions are already multiples of 64.
- The code has partial IP-distance paths, but the paper experiments and our next
  audit should stay with squared L2 unless we deliberately start an IP/MIPS line.

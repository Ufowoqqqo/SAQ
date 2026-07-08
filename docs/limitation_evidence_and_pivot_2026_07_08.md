# Limitation Evidence and Research Pivot

## Purpose

This note records why the current single-global static segment-cost direction
should stop as a main method, and defines the next research direction under the
query-unaware constraint.

The decision criterion is paper-facing: a direction should expose a concrete SAQ
limitation, support a defensible mechanism, avoid large unjustified overhead,
and be robust to a strict SIGMOD/VLDB/ICDE review. Small recall or QPS changes
are not enough by themselves.

## Evidence From The Retired Direction

The tested hypothesis was:

```text
SAQ's global variance DP may ignore search-time segment cost; choosing a nearby
lower-cost global plan may preserve recall and improve QPS.
```

Two studies now weaken this hypothesis.

First, the offline frontier study reproduced SAQ's global DP and compared the
SAQ default against deterministic Pareto frontiers over static cost terms such
as positive dimensions, code-bit volume, segment count, segment-factor overhead,
and zero-tail mass. Across the available GIST, CIFAR, DEEP, audio, and word2vec
B=3/B=4/B=5 matrix, the SAQ default was not dominated by any lower-cost plan at
no worse variance-risk.

Second, the end-to-end GIST check rebuilt full GIST/K4096/B=4 indexes for two
near-frontier plans. Both candidates slightly improved R@100, but both were
slower than the SAQ default under safe search across `nprobe = 100, 200, 400`.
At `nprobe = 200`, default QPS was 2732.35, the lower-code-volume candidate was
2503.10, and the lower-positive-dimension candidate was 2673.65.

The important conclusion is not that SAQ has no limitations. The conclusion is
more specific:

```text
Simple static global cost terms do not provide a reliable way to improve SAQ's
default global planner end to end.
```

This is useful limitation evidence. It shows that raw code volume, positive
dimensional volume, and segment count are not sufficient search-time models.
Actual search cost also depends on segment layout, estimator execution,
accurate-stage work, zero-tail placement, pruning behavior, and metadata/factor
overhead.

## Reviewer Interpretation

A strict reviewer would likely reject a method that only adds a static cost term
or selects a lower-cost frontier point:

- It would look like parameter tuning around SAQ rather than a new quantizer or
  planner.
- It would not have a dominance result over the SAQ default.
- The end-to-end evidence shows no QPS gain on the strongest GIST test case.
- Adding a weighted objective such as `risk + lambda * cost` would introduce an
  unjustified hyperparameter unless the cost model is derived and validated.

Therefore, this direction should remain in the paper story only as a limitation
analysis: SAQ's default global variance DP is hard to beat with simple
query-unaware static cost proxies.

## Pivot Criteria

The next direction should satisfy four constraints.

1. It must target a core SAQ assumption rather than a local implementation
   choice.
2. It must stay query-unaware: benchmark queries are allowed only for final
   evaluation.
3. It must avoid handcrafted candidate families and unjustified hyperparameters.
4. It must have a small falsifiable offline study before any broad index build.

## Selected Pivot

The next direction is **data-only SAQ planner-objective analysis**.

SAQ's global DP uses a variance-risk proxy of the form:

```text
segment_risk(segment, bits) = sum(variance in segment) / 2^bits
```

This is much more central than the static cost terms we just tested. If this
proxy is already a faithful ranking of segment/bit choices, then changing the
planner is unlikely to produce a strong contribution. If the proxy has a
systematic mismatch with measured CAQ/SAQ error, then a replacement objective
could become a real method rather than a post-hoc tweak.

The research question is:

```text
Does SAQ's variance-risk objective accurately predict measured data-only
quantization or distance-estimation error for candidate segments and bit widths?
```

The opportunity is to replace or refine the planner objective using a mechanism
that is still query-unaware. Examples of possible measurable quantities include
actual CAQ quantization error on base vectors, segment anisotropy, intra-segment
variance concentration, zero-tail contribution, and adjustment residuals. These
should be evaluated as evidence first, not immediately turned into a weighted
objective.

## Immediate Study

Start with an offline measurement driver. For each dataset, segment, and bit
width under consideration, compare:

- SAQ proxy risk: `sum(variance) / 2^bits`;
- measured data-only CAQ/SAQ error for the same segment and bit width;
- ranking agreement between the proxy and measured error;
- cases where SAQ's proxy would prefer one segment/bit choice but measured
  error prefers another.

The first study should not build a new index and should not use benchmark
queries. Its output should be a concise table and scatter-style CSV showing
whether proxy mismatch exists across GIST, CIFAR, DEEP, audio, and word2vec.

## Stop Condition

Stop this pivot if the SAQ proxy and measured data-only error agree strongly
across datasets and bit budgets, or if any correction requires arbitrary fitted
weights. In that case, the next candidate direction should be a larger systems
shift such as graph-index integration, not another local planner tweak.

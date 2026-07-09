# SAQ Search-Procedure Direction Decision

## Decision

Do not continue generic search-procedure optimization as a main method
direction.

The only remaining search-procedure question worth one final measurement is:

```text
Why is SAQ's variance-pruning stage almost inactive, and is there a safe,
non-empirical bound refinement that could make this stage meaningful?
```

If that bound-focused measurement does not expose a principled mechanism, stop
the search-procedure direction entirely and treat the collected results as
limitation evidence.

## Evidence So Far

### 1. Plan-objective changes did not produce recall-matched improvement

The one-global-plan planner-objective line found a changed GIST B=4 plan:

```text
SAQ variance plan:   64x11_192x6_320x4_256x2_128x0
fac-error plan:      192x9_512x4_256x0
```

The custom plan is faster and smaller at the same nprobe, but the recall loss
does not recover before the QPS advantage disappears. This makes it useful
limitation evidence, not a defensible main method.

### 2. Static segment-cost DP did not transfer to end-to-end QPS/recall

The single-global static segment-cost direction showed that lower static cost
frontiers do not automatically produce safe-search QPS benefit. The default
SAQ plan was not dominated in a way that translated into a recall-matched
improvement.

### 3. Runtime-profile evidence narrowed the search-procedure question

On GIST sample100k K512 B=4:

- variance pruning removes less than 0.5% of scanned blocks;
- fast-stage pruning removes about 45-58% of post-variance blocks;
- only about 5-7% of scanned candidates enter accurate refinement;
- among refined candidates, about 84% already exit before all positive-bit
  segments are evaluated.

This shows that SAQ's current progressive search path is already doing useful
work in the fast and accurate stages. The weak point is not obvious wasted
accurate refinement; the most visible anomaly is the almost inactive variance
stage.

### 4. Segment-order counterfactual failed as a method direction

A diagnostic replay tested simple query-unaware segment orders:

```text
pca, reverse, bit_desc, dim_desc, cost_asc, risk_per_cost_desc
```

At nprobe 160, 200, and 240, the default `pca` order remains tied for the
lowest observed work among these hyperparameter-free alternatives. Reverse and
dimension-descending orders are much worse, increasing fast-stage work by
37-57% and accurate-stage work by 146-169%.

This falsifies the easy version of estimator scheduling:

```text
simple fixed segment reordering is not a promising contribution.
```

## What Has Been Ruled Out

The following ideas should not be continued as main methods:

- another one-global-plan objective tweak without a recall-matched mechanism;
- static segment-cost DP as a primary contribution;
- mixed shared local plans as a primary contribution;
- empirical fixed-policy candidate scoring;
- simple query-unaware segment reordering;
- broad search-loop instrumentation without a specific mechanism.

These are valuable negative results because they constrain what a credible SAQ
follow-up can be. They also show that SAQ's default design is stronger than a
naive "planner or schedule tweak" story.

## Remaining Possible Mechanism

The only concrete remaining search-procedure signal is:

```text
SAQ computes a variance-based block estimate, but that estimate almost never
prunes blocks in the observed GIST setting.
```

A research-worthy continuation would need to answer:

1. Is the variance bound mathematically loose, implementation-limited, or
   simply dominated by the current top-k boundary dynamics?
2. Can a tighter bound be derived from quantities SAQ already stores or can
   store with small overhead?
3. Can the refinement be stated as a safe inequality or explicit approximation
   tradeoff, rather than calibrated by benchmark queries?
4. Does the refined bound reduce query-time work without harming recall under
   safe search?

This is not permission to tune `searcher_vars_bound_m`. Changing that parameter
without a derivation would be arbitrary calibration and should not be treated
as a method.

## Final Allowed Measurement

One final bound-focused measurement is allowed before stopping or pivoting.

It should measure, for GIST sample100k K512 B=4:

- the distribution of `mi - distk` after variance estimation;
- how often the variance estimate is close to pruning;
- how much tighter the bound would need to be to prune meaningful blocks;
- whether the required tightening factor has a derivation from SAQ's variance
  model, residual norms, or finite-code estimator error;
- whether the same observation holds at nprobe 160, 200, and 240.

The measurement must not fit a threshold from held-out benchmark queries. It
should first be explanatory: why does the current variance stage fail to prune?

## Stop Condition

Stop the search-procedure direction if the bound-focused measurement shows any
of the following:

- meaningful pruning would require an arbitrary multiplicative calibration;
- the needed bound is not safe and has no explicit approximation tradeoff;
- the variance stage is inactive because top-k boundary dynamics make it
  inherently too weak before fast estimates are computed;
- the potential work reduction is small relative to existing fast-stage
  pruning;
- the result depends only on GIST and does not suggest a general SAQ
  limitation.

## If The Direction Stops

If the final measurement is negative, the search-procedure work should be
summarized as:

```text
SAQ's default progressive search path already captures the low-overhead
query-unaware scheduling opportunities we tested; the remaining inactive
variance bound does not yet imply a safe, useful method.
```

At that point, the next research direction should move away from small
query-path scheduling changes. More promising directions would be higher-level
SAQ limitations, such as:

- graph-index compatibility and traversal-path sensitivity;
- theoretical analysis of SAQ/CAQ estimator error and bounds;
- non-PCA transform objectives with a stronger derivation than empirical plan
  search;
- dataset regimes where SAQ's assumptions visibly fail rather than marginally
  improve.

## Immediate Next Step

Run no new search policy. Write a small variance-bound inactivity measurement
or, if that measurement also looks arbitrary, stop and prepare a synthesis note
that closes the search-procedure direction.

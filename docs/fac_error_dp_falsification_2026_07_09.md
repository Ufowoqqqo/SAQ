# Fac-Error DP Falsification

## Question

The previous data-only estimator measurement showed that CAQ `fac_error`
almost perfectly ranks absolute segment-level estimator error. This small
falsification asks a narrower question:

```text
If SAQ's variance DP cost is replaced by a data-only fac-error cost, does the
one-global-plan allocation actually change under the same SAQ bit budget?
```

If the selected plan were identical or nearly identical to SAQ's variance plan,
then this planner-objective direction would likely stop before index building.

## Offline Objective

The comparison uses the same DP structure as upstream SAQ:

- contiguous 64-dimensional block segments;
- the same total bit budget, `B * padded_dim + 64`;
- the same 64-bit positive-segment factor overhead;
- the same maximum segment-count rule;
- the same optional zero-bit tail constraint;
- the same 1% replacement tolerance used by SAQ's DP backtracking.

The variance objective is exactly SAQ's default:

```text
cost(segment, bits>0) = variance_sum(segment) / 2^bits
cost(zero_tail)       = variance_sum(zero_tail)
```

The fac-error objective is data-only and uses the estimator-error measurement
CSV from the previous step:

```text
cost(segment, bits>0) = mean CAQ fac_error(segment, bits)
cost(zero_tail)       = measured zero-bit dropped-tail L2 error
```

The zero-tail definition is a limitation rather than a new method claim: a
zero-bit segment has no CAQ code, so it has no `fac_error`. The dropped-tail
L2 error is used only to make this falsification comparable to SAQ's zero-tail
planner option.

## Result

The first run uses the existing 2048-row, same-cluster residual-pair
measurement and tests only `B=4`.

| dataset | B | sample rows | pairs | variance plan | fac-error plan | changed? |
|---|---:|---:|---:|---|---|---|
| audio K4096 | 4 | 2048 | 1300 | `192x4` | `192x4` | no |
| CIFAR60K | 4 | 2048 | 2048 | `64x9_192x5_128x3_128x0` | `128x8_320x3_64x0` | yes |
| DEEP sample100k | 4 | 2048 | 2048 | `64x6_192x3` | `64x6_192x3` | no |
| GIST sample100k | 4 | 2048 | 2048 | `64x11_192x6_320x4_256x2_128x0` | `192x9_512x4_256x0` | yes |
| word2vec sample100k | 4 | 2048 | 2048 | `320x4` | `320x4` | no |

Both objectives use exactly the same bit budget in every row. For example, on
GIST sample100k with `B=4`, both plans use 3904 total bits including segment
factor overhead.

## Interpretation

This does not establish a new planner, but it does avoid the immediate negative
outcome that `fac_error` merely reproduces the same variance-DP plan everywhere.
The changed plans are not arbitrary:

- GIST changes from five segments to three segments, widening the high-bit head
  and the 4-bit middle region.
- CIFAR changes from four segments to three segments, again widening the head
  and middle allocation.
- audio, DEEP, and word2vec remain unchanged under this budget.

The useful hypothesis is therefore narrow:

```text
fac-error cost may only affect multi-segment, zero-tail plans where SAQ's
variance proxy creates fine head/tail splits.
```

That hypothesis is still weak. It must survive an end-to-end check before being
treated as a method.

## Strict-Reviewer Interpretation

A strict reviewer would not accept this as a contribution by itself. The result
only says that the offline objective can change the plan on two datasets. It
does not say the plan improves recall, QPS, index size, or build time.

The main risks are:

- `fac_error` may be a tautological remeasurement of CAQ's own estimator bound;
- the measurement currently uses a 2048-row pair budget, so sample sensitivity
  is unknown;
- the zero-tail cost mixes `fac_error` for positive-bit segments with measured
  dropped-tail L2 error for zero-bit tails;
- the branch currently has no custom-plan materialization path, so end-to-end
  validation requires either a minimal custom-plan option or a separate
  controlled index-building hook.

The next step should be small: materialize only the two changed B=4 plans
needed for a safe-search check, preferably GIST first because it has the
largest plan-shape change. Stop if the custom plan does not improve recall/QPS
or if the required planner/measurement overhead cannot be justified.

## Commands

```bash
python script/falsify_fac_error_dp.py \
  --inputs /tmp/saq-run/estimator_error/gist_sample100k_estimator_2048.csv \
           /tmp/saq-run/estimator_error/cifar60k_estimator_2048.csv \
           /tmp/saq-run/estimator_error/deep1M_sample100k_estimator_2048.csv \
           /tmp/saq-run/estimator_error/audio_K4096_estimator_2048.csv \
           /tmp/saq-run/estimator_error/word2vec_sample100k_estimator_2048.csv \
  --avg-bits 4 \
  --output-prefix /tmp/saq-run/fac_error_dp/fac_error_dp_b4
```

Generated CSV and markdown summaries are under `/tmp/saq-run/fac_error_dp/`
and are not committed.

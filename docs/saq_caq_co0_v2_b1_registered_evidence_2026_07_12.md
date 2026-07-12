# CO-0 v2 B1 Registered Limitation Evidence

Date: 2026-07-12

## Decision

The frozen V2-B1 limitation screen returns:

```text
CONDITIONAL_PASS
```

All 24 preregistered one-sided hypotheses pass Holm correction, all seed
consistency checks pass, and no bootstrap replicate has a zero aggregate
denominator. This establishes the preregistered SAQ-specific limitation under
the two frozen base-only regimes. It does not establish a new quantizer,
repair, recall improvement, or publishable contribution.

## Registered Question And Statistic

For one residual view, define

```math
R_{arm}=
\frac{\sum_v(f_{arm,v}-f_{exact,v})}
     {\sum_v(f_{init,v}-f_{exact,v})}.
```

Here `f` is the source-compatible error factor, `init` is LVQ scalar
initialization, and `exact` is the independently validated complete-event
oracle. `R=0` means the arm closes all initialization-to-exact opportunity;
`R=1` means it closes none. The registered materiality floor was `R >= 0.10`.

| Leading SAQ segment | `R_r6` | 5% lower bound | `R_local` | 5% lower bound |
|---|---:|---:|---:|---:|
| GIST `64@11` | 0.944994 | 0.942228 | 0.944982 | 0.942218 |
| CIFAR `64@9` | 0.790078 | 0.788278 | 0.789792 | 0.787975 |

Production six-round CAQ therefore closes only about 5.5% of the measured
opportunity on GIST and 21.0% on CIFAR. Continuing the identical coordinate
rule to a local fixed point barely changes either ratio, so an ordinary
increase in adjustment rounds does not explain away the result.

All four raw one-sided materiality p-values are `1/10001`; after correction
the reported adjusted value is `0.00239976`. Every seed-specific ratio is at
least `0.7879`, far above the frozen `0.10` floor.

## SAQ-Specific Amplification

The leading high-bit segment has greater remaining opportunity than every
registered control. Selected `r=6` ratios are:

| Dataset | Leading native | Same segment at `B=4` | Next native | Whole positive view at `B=4` |
|---|---:|---:|---:|---:|
| GIST | 0.944994 | 0.278103 | 0.435193 (`192@6`) | 0.317450 (`832@4`) |
| CIFAR | 0.790078 | 0.276615 | 0.401523 (`192@5`) | 0.339714 (`384@4`) |

The full frozen family contains 18 such amplification comparisons for `r=6`
and local-fixed-point CAQ. Every paired difference has positive one-sided
evidence after the shared 24-test Holm correction. This supports the narrower
claim that SAQ's short, leading, high-bit segments amplify a CAQ optimization
limitation; it does not imply that arbitrary SAQ plans fail.

## Unchanged-Estimator Evidence

The error-factor result cannot pass alone because SAQ search does not consume
the stored error field. The frozen base-pair proxy therefore applies the
unchanged full-code estimator to disjoint within-cell residual pairs.

| Dataset | CAQ normalized error | Exact normalized error | Difference | Relative reduction |
|---|---:|---:|---:|---:|
| GIST | 7.22014e-5 | 6.25152e-5 | 9.68620e-6 | 13.42% |
| CIFAR | 2.84696e-4 | 2.61114e-4 | 2.35814e-5 | 8.28% |

The registered differences are positive for all three rotation seeds and pass
Holm correction. Unscaled absolute error has the same direction. These are
base-only residual-pair measurements, not benchmark-query recall or QPS.

## Convergence Description

The following quantities were not additional decision tests. They describe
why extra coordinate rounds are ineffective on the leading segment:

| Dataset | `r=6` code equals exact | Local code equals exact | Mean `r=6` moves | Mean local moves |
|---|---:|---:|---:|---:|
| GIST | 0.588% | 0.588% | 0.3338 | 0.3339 |
| CIFAR | 5.673% | 5.697% | 2.3318 | 2.3349 |

The local arm usually terminates in roughly the same number of rounds and
accepts almost no additional moves, while exact-code equality remains low.
This is consistent with coordinate-wise local optima rather than an
insufficient fixed round limit.

## Work And Storage

| Arm | Total CPU | Mean CPU per encoding | Relative to `r=6` |
|---|---:|---:|---:|
| LVQ initialization | 2.32 s | 0.97 us | 0.10x |
| CAQ `r=6` | 22.26 s | 9.28 us | 1.00x |
| Local fixed point | 44.53 s | 18.55 us | 2.00x |
| Corrected exact oracle | 6075.60 s | 2531.50 us | 272.92x |

The exact oracle processed 16.58 billion first-pass events, 4.93 billion
replay events, and 161.80 billion heap comparisons. It is an offline labeler,
not a viable fallback encoder.

The complete run used one thread and recorded:

```text
encoding rows                 9,600,000
pair rows                     4,773,192
packed code bytes             1,147,200,000
serialized output bytes       2,944,106,548
peak RSS                      251,342,848 bytes
exact-oracle CPU              6075.60 s (1.69 h)
total CPU                     6840.50 s (1.90 h)
total wall                    6851.46 s (1.90 h)
frozen analysis wall          153.97 s
```

## Reproduction And Artifacts

The runner used commit `2da5e9f6ada62a4c283a3beee463280b347369b5`
and SHA-256
`ac34868925e8150da07b4bc7f808f91b43ed894a741c2e1f5eca4478a17d6fe7`.
Release regression tests passed immediately before execution.

The raw directory contains 578 files and 2,944,176,277 bytes after adding the
frozen summary. Its sorted path/size/file-hash tree digest is
`b4f6425719615c740cbc5ef86387f8201179095a681eb3d5eded7d91ac383fa6`.
The raw 2.8 GiB output is not committed. An identical tree-digest-verified
copy is retained at
`/rwproject/kdd-db/kluaq/saq/results/caq_co0_v2_b1_registered_2da5e9f`.
The complete run manifest, frozen hypothesis output, provenance record, and
descriptive aggregates are stored under
`docs/saq_caq_co0_v2_b1_registered_artifacts_2026_07_12/`.

Commands:

```bash
/tmp/saq-v2-b1-registered-build-2da5e9f/caq_co0_v2_b1_runner \
  --input-spec docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json \
  --preregistration docs/saq_caq_co0_v2_b0_final_preregistration_2026_07_11.md \
  --hypotheses docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json \
  --inventory-manifest docs/saq_caq_co0_v2_b0_artifacts_2026_07_11/inventory_manifest.json \
  --output-dir /tmp/saq-caq-co0-v2-b1-registered-2da5e9f \
  --threads=1

python script/summarize_caq_co0_v2_b1.py \
  --run-dir /tmp/saq-caq-co0-v2-b1-registered-2da5e9f \
  --hypotheses docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json \
  --output /tmp/saq-caq-co0-v2-b1-registered-2da5e9f/frozen_summary.json
```

## Claim Boundary And Next Stage

The defensible conclusion is:

> Under the frozen GIST and CIFAR SAQ plans, short leading high-bit residual
> segments retain a large exact alignment opportunity after production CAQ;
> the gap survives local convergence, is stronger than every registered
> low-bit/whole-view control, and measurably affects the unchanged estimator.

The evidence does not yet identify a low-cost repair. The next permissible
stage is a bounded primary-source and theory review of deterministic
certificates or adjustment rules specialized to short high-bit segments. Any
proposal must explain why it can recover estimator benefit without approaching
the observed 273x exact-oracle encoding cost. No dataset, bit, or method sweep
is authorized by this conditional pass.

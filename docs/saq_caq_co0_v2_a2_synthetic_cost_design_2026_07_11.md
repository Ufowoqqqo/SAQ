# CO-0 v2 Corrected-Oracle Synthetic Cost Design

Date: 2026-07-11
Stage: V2-A2
Status: frozen before cost-run implementation

## Question And Scope

V2-A2 asks only whether the validated exact complete-event oracle is cheap
enough to label a later preregistered base-only sample. It does not estimate
CAQ regret, compare encoders, access datasets, or support a method claim.

The runner accepts no dataset path, random seed, sample count, or tunable
threshold. Every input is generated from its dimension and the binary32
representation itself.

## Frozen Cells

Run exactly the cells inherited from the protocol:

```text
GIST-shape labels:
  (D,B) = (64,11), (192,6), (320,4), (256,2), (832,4)

CIFAR-shape labels:
  (D,B) = (64,9), (192,5), (128,3), (384,4)
```

The labels identify historical plan shapes only; the runner does not read the
corresponding datasets.

For all rows `D_+=D`, which maximizes the fixed event count

```math
E=D(2^{B-1}-1)
```

relative to vectors containing zero or padded coordinates.

## Deterministic Profiles

Each cell is evaluated once under three mechanism-defined magnitude profiles.
Signs alternate by coordinate to exercise centered-code mapping without
changing magnitude-search work.

### `equal`

Every magnitude is exactly `1.0f`. This is the simultaneous-event/tie-heavy
endpoint and uses the narrowest common-exponent integer representation.

### `dense_unit_interval`

For coordinate `i in {0,...,D-1}`:

```math
a_i = \operatorname{binary32}\left(
      \frac12 + \frac12\frac{i+1}{D+1}\right).
```

This gives a deterministic, densely ordered ordinary-width profile. Its only
scale is the dimension; there is no fitted decay or random distribution.

### `binary32_full_span`

Positive finite binary32 bit patterns are numerically ordered. Let
`R=0x7f7fffff` be the largest finite positive pattern and define

```text
raw_i = 1 + floor(i*(R-1)/(D-1)).
a_i   = bit_cast<float>(raw_i).
```

This includes `denorm_min` and the largest finite binary32 value and stresses
the maximum exact-integer width admitted by the input contract. It is a
representation-cost endpoint, not a model of residual data.

These three profiles correspond to event ties, ordinary event interleaving,
and arbitrary-precision width. No additional profile may be introduced after
the run to change feasibility.

## Measurements

For every cell/profile row record:

```text
D, B, L, theoretical event count
first-pass and replay events
heap and objective comparisons
maximum cpp_int width
wall and CPU time for one encode
common binary exponent
deterministic output checksum
```

Record process peak RSS and aggregate wall/CPU time once for the full matrix.
Input generation is outside the per-encode timer. Persistent index bytes are
zero by construction.

## Conservative Cost Equation

For cell `c` and profile `p`, let `T_cp` be measured CPU time, `E_c` the fixed
first-pass event count, and `R_cp` the replay count. Define

```math
U_c = \max_p T_{cp}\frac{2E_c}{E_c+R_{cp}}.
```

The multiplier replaces observed replay work by its code-independent maximum
`R<=E`. It is an operation-count correction, not a fitted safety factor.

The later frozen design has three rotation seeds. Per sampled vector, its
conservative exact-label CPU estimates are

```math
C_G = 3(U_{64,11}+U_{192,6}+U_{320,4}+U_{256,2}+5U_{832,4}),
```

```math
C_C = 3(U_{64,9}+U_{192,5}+U_{128,3}+4U_{384,4}).
```

The first terms are the default positive-bit segments. The multiples of the
whole-positive-view `B=4` cells conservatively cover every omitted uniform
`B=4` segment control plus the whole-view control without adding cells that
the parent protocol did not authorize.

## Sample And Resource Decision

The candidate common sample size is

```text
n_target = min(50,000 GIST-shape base vectors,
               60,000 CIFAR-shape base vectors)
         = 50,000 vectors per dataset.
```

This uses the complete smaller frozen base and equalizes the two dataset
sample counts; it is not selected from an observed objective gap.

The exact-label resource ceiling is one CPU-day for both datasets together:

```math
C_{total}=n_{target}(C_G+C_C) \le 24\text{ CPU-hours}.
```

One CPU-day is a bounded single-core overnight-to-day-scale offline study,
not a method parameter. If the conservative estimate exceeds this ceiling,
V2-A2 returns `NO-GO`; do not reduce `n_target`, drop `B=11`, substitute an
easier profile, or access data to obtain a more favorable estimate.

## Decisions

```text
PASS:
  all rows complete with exact counters and C_total <= 24 CPU-hours

NO-GO:
  any row fails, arithmetic narrows, or C_total exceeds the ceiling
```

A pass establishes cost feasibility only. V2-B remains unauthorized until a
separate preregistration is reviewed and committed.

# Static audit: feasible objectives for two fixed SAQ segments

Date: 2026-08-03

## Decision

The static question is resolved:

```text
SEPARABLE_STANDARD_OBJECTIVES
NONSEPARABLE_WORKLOAD_OBJECTIVES_EXIST
```

Under the existing SAQ plan, format, and accurate consumer, the feasible set
for segments 1 and 2 is a Cartesian product.  Squared reconstruction error,
worst-case unseen-direction inner-product error, and expected squared
inner-product error under an isotropic or block-diagonal direction second
moment all separate exactly.  Jointly optimizing any of them returns two
independent segment optimizations and cannot explain a new joint mechanism.

A non-separable objective can nevertheless be constructed without changing
the stored format.  It must introduce cross-segment workload information:

- a base-probe direction distribution whose empirical cross-block second
  moment is nonzero on the feasible residual spans; or
- a pairwise ranking loss whose margin decision depends on the sum of the two
  segment errors.

This is a mathematical counterexample to the claim that every allowed
base-only objective is separable.  It is not yet a method recommendation.  The
coupling comes from an added workload model, not from the SAQ feasible codes,
and the general principle is estimator-aware quantization rather than an
SAQ-specific mechanism.  Selecting such a workload objective changes the
scientific question and closest-baseline set.  Per the current task boundary,
return to the user before implementation or measurement.

## Exact variables exposed by the current implementation

Consider segment `s` of a fixed PCA residual vector.  After the segment-local
rotation, let:

```text
x_s       exact database residual in this segment
c_s       stored scalar grid code
z_s(c_s)  decoded normalized grid direction
a_s(c_s)  stored per-vector rescale
y_s       a_s(c_s) z_s(c_s)
r_s       y_s - x_s
```

For a nondegenerate code, `CAQEncoder::encode_and_fac` sets

```text
a_s(c_s) = ||x_s||^2 / <x_s, z_s(c_s)>.
```

The normalization in `rescale_vmx_to1` changes the stored grid scale and
rescale by reciprocal factors, leaving `y_s` unchanged.  Consequently every
feasible encoded reconstruction obeys

```text
<x_s, y_s> = ||x_s||^2,
<x_s, r_s> = 0.                         (1)
```

The stored `fac_error` does not appear in the accurate consumer.  The
query-relevant variables are the code and `rescale`; the exact segment norm is
stored separately.

`SAQuantizer::quantize_cluster` loops over segments and invokes a distinct
`QuantizerCluster` on each segment slice.  There is no shared code, factor, bit
constraint, or state at vector-encoding time after the plan has been fixed.
Thus, for the two segments under review,

```text
F_12(x_1, x_2) = F_1(x_1) x F_2(x_2),     (2)
```

where `F_s` is the set of grid codes paired with the rescale determined by the
current encoder rule, all serialized through the existing segment format.
Code adjustment is a heuristic search inside each `F_s`; it does not change
the product structure.

## Accurate-estimator error

For a query residual `q_s`, the segment contribution is

```text
E_s(q_s,x_s,c_s)
  = ||x_s||^2 + ||q_s||^2 - 2 <q_s,y_s>.
```

The exact contribution replaces `y_s` by `x_s`, so

```text
E_s - T_s = -2 <q_s,r_s>.

E_12 - T_12 = -2 (<q_1,r_1> + <q_2,r_2>).     (3)
```

Equation (3) is additive before a loss function is applied.  Whether an
encoding objective separates depends on that outer loss and on the assumed
direction distribution.

## Proof 1: squared reconstruction is separable

The two segments occupy orthogonal coordinate blocks.  Therefore

```text
||[y_1;y_2] - [x_1;x_2]||^2
  = ||r_1||^2 + ||r_2||^2.                 (4)
```

Combining (2) and (4),

```text
min_(c_1,c_2) ||r_1(c_1)||^2 + ||r_2(c_2)||^2
  = min_c1 ||r_1(c_1)||^2 + min_c2 ||r_2(c_2)||^2.
```

This is exact and does not require statistical independence, PCA covariance
assumptions, or an asymptotic argument.  A “joint reconstruction optimizer”
over the unchanged format is only the direct composition of two independent
optimizers.

## Proof 2: worst-case unseen direction is separable

Let `q=[q_1;q_2]` range over the unit ball.  From Cauchy--Schwarz,

```text
sup_(||q||<=1) (<q_1,r_1> + <q_2,r_2>)^2
  = ||[r_1;r_2]||^2
  = ||r_1||^2 + ||r_2||^2.                 (5)
```

The factor `4` from (3) does not affect the minimizer.  Thus the natural
worst-case inner-product-preservation objective also reduces to independent
segment reconstruction objectives.

## Proof 3: isotropic and block-diagonal average-case MSE are separable

Let the direction second moment be

```text
M = E[q q^T] = [ M_11  M_12 ]
                 [ M_21  M_22 ].
```

Using (3), expected squared estimator error is

```text
L_M(r_1,r_2) = 4 E[(q_1^T r_1 + q_2^T r_2)^2]
 = 4 (r_1^T M_11 r_1
      + r_2^T M_22 r_2
      + 2 r_1^T M_12 r_2).                 (6)
```

If directions are isotropic, `M` is a scalar multiple of the identity and
`M_12=0`.  More generally, any block-diagonal second moment makes (6)
separable, even when the two blocks have different anisotropy.

PCA decorrelation by itself is not enough to assert `M_12=0` for every
possible workload: the index encodes cell residuals, conditioning on an IVF
cell can reintroduce cross-block moments, and a base-probe workload need not
match the global PCA fitting population.  That is an empirical-workload issue,
not a property supplied by the code format.

## Exact non-separability condition for quadratic estimator loss

For segment `s`, define the feasible residual-difference span

```text
D_s = span{r_s(c) - r_s(c') : c,c' in F_s}.
```

For two choices `u,u'` in segment 1 and `v,v'` in segment 2, the mixed finite
difference of (6) is

```text
L_M(u,v) + L_M(u',v') - L_M(u,v') - L_M(u',v)
  = 8 (u-u')^T M_12 (v-v').                (7)
```

Therefore the quadratic objective is additively separable on the actual
feasible sets if and only if

```text
d_1^T M_12 d_2 = 0
for every d_1 in D_1 and d_2 in D_2.        (8)
```

Merely observing that the raw empirical `M_12` is nonzero would not be
decisive.  It must remain nonzero after projection onto the feasible residual
difference spans.  Conversely, one nonzero value in (8) is a static
counterexample to separability.

Equation (8) also identifies the added scientific assumption: a chosen
direction/workload second moment.  The current exact-replacement oracle did
not measure it and cannot select it retrospectively.

## Counterexample 1: base-direction quadratic loss

Take two two-dimensional segments.  Let a database residual be
`x_s=(1,0)`.  The CAQ rescale identity (1) permits two encoded reconstructions

```text
y_s^- = (1,-epsilon),   y_s^+ = (1,+epsilon),
r_s^- = (0,-epsilon),  r_s^+ = (0,+epsilon).
```

These states are compatible with the existing geometry: choose two symmetric
grid directions `(u,-v)` and `(u,+v)` with `u>0`, then the stored rescale
`1/u` produces `epsilon=v/u` and preserves `<x_s,y_s>=1`.

Let the base-direction population contain `q_1=q_2=(0,1)`.  Its cross moment
between the second coordinates is nonzero.  Ignoring the common positive
factor, the four joint squared errors are

```text
             r_2^-        r_2^+
r_1^-     (-e-e)^2      (-e+e)^2
r_1^+     (+e-e)^2      (+e+e)^2

           4e^2            0
             0           4e^2
```

No sum `f_1(c_1)+f_2(c_2)` has this table: its mixed finite difference is
`8e^2`, not zero.  Hence a base-only empirical direction loss can couple the
two code choices without changing stored bytes or query arithmetic.

The witness proves existence only.  It does not show that GIST segment 1/2
have a material projected `M_12`, that the production candidate sets contain
the useful alternative codes, or that optimizing this loss improves Recall.

## Counterexample 2: pairwise ranking loss

Ranking is non-separable even when expressed only through scalar segment-error
contributions.  Let each segment choice contribute `u_s in {-1,+1}` to an
estimated candidate-pair gap whose true margin is `g=1/2`.  Define inversion
loss

```text
R(u_1,u_2) = 1[g + u_1 + u_2 < 0].
```

Then

```text
             u_2=-1     u_2=+1
u_1=-1          1           0
u_1=+1          0           0
```

The mixed finite difference is one, so the table cannot be written as two
independent segment losses.  The symmetric CAQ states above can realize
positive and negative segment error contributions by changing the direction
or the code sign; the exact norm term does not remove the coupling because it
cancels when forming estimator error.

This explains why the joint oracle can outperform the sum of single-oracle
inversion reductions.  It still does not prove that production segment code
choices were selected jointly or that a stable training ranking population is
available without introducing a workload model.

## What the audit rules out

The following proposals do not survive as joint mechanisms:

1. **Joint reconstruction minimization.**  Exactly separable by (4).
2. **Worst-case arbitrary unseen-query protection.**  Exactly separable by
   (5).
3. **Uniform-direction average error.**  Exactly separable by (6) with
   `M_12=0`.
4. **Jointly rerun current code adjustment.**  The current adjustment acts
   inside separate product factors; coordinating loop order does not change
   the objective or feasible set.
5. **Independently improve both segment encoders.**  Potentially useful
   engineering, but a direct composition rather than an explanation of the
   pair-oracle interaction.

## What remains mathematically possible

Two frozen-format classes remain possible:

1. minimize empirical base-direction estimator MSE using a justified
   cross-block `M_12` and joint code selection;
2. minimize a base-only pairwise ranking surrogate over a frozen population of
   probes, candidates, and margins.

Both retain serialized bytes and the current additive query consumer.  Both
can make construction substantially more expensive because a Cartesian search
over alternative codes replaces two independent choices.  Approximation or
coordinate descent would need its own optimality and cost evidence.

Neither class is automatically SAQ-specific.  Equation (6) is a generic
estimator-aware quantization objective, and pairwise ranking objectives are
generic retrieval-loss training.  The closest comparisons must include
anisotropic/inner-product-aware quantization in addition to ordinary SAQ
encoder variants.  A strict reviewer would also ask why base-to-base
directions represent unseen queries and whether the gain survives a disjoint
dataset/query evaluation after freezing.

## Recommendation and next checkpoint

Do not implement either objective from this audit alone.  The honest choice is
now between:

- **close the pair as an oracle-only limitation**, because the standard
  query-unaware objectives are separable and the surviving coupling is generic
  workload modeling; or
- explicitly pivot to **base-trained estimator-aware joint code selection**.

If the latter scientific pivot is chosen, the cheapest discriminating action
is not a consumer implementation.  It is a small base-only diagnostic that
freezes one direction population and measures:

1. the projected cross-block operator on `D_1 x D_2`, not raw covariance;
2. an offline upper bound from joint alternative-code selection over a tiny
   sample;
3. improvement over independently optimized alternatives at identical stored
   bytes; and
4. construction work per vector.

Stop if the projected cross term is numerically negligible, the joint upper
bound does not clear a predeclared materiality line in both folds, or work is
already incompatible with index construction.  Designing that diagnostic
changes the active scientific hypothesis and requires a user checkpoint.

Production source was inspected read-only to derive the feasible variables.
No source code was modified, and no dataset, query, ground truth, or generated
result was read.  No compilation or experiment was run.
`PERFORMANCE_NOT_YET_MEASURED`.

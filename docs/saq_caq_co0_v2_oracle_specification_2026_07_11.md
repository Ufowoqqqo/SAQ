# CO-0 v2 Exact Complete-Event Oracle Specification

Date: 2026-07-11
Stage: V2-A0
Status: mathematical semantics frozen before implementation; schema v2 frozen before final validation

## Research Role

This oracle is an offline labeler for a bounded synthetic and later base-only
falsification study. It is not a new quantizer, a production encoder, or the
pinned official Extended-RaBitQ implementation. Exact global scale/event
search is inherited from E-RaBitQ; the purpose of this implementation is to
obtain trustworthy labels for the finite-round CAQ question.

V2-A0/V2-A1 may not read datasets, benchmark queries, or ground truth.

## Input Contract

Input:

```text
o[0..D-1]  binary32 rotated residual coordinates
D          positive dimension including padded lanes
B          total bits per dimension, including the sign bit
```

The validator supports `1 <= B <= 16`; the frozen protocol currently requires
at most `B=11`. Every coordinate must be finite. NaN and infinity are rejected.

For a nonzero coordinate, the sign bit follows `signbit(o_i)`. Positive and
negative zero both use the deterministic positive-zero convention. An all-zero
input returns a degenerate result with no angular objective.

## Direction Codebook

Define

```text
a_i = |o_i|
L   = 2^(B-1)
k_i in {0, ..., L-1}
z_i = k_i + 1/2.
```

For `a_i>0`, changing the code sign to match `o_i` preserves the code norm and
cannot decrease the inner product. Therefore at least one global optimum has
the data sign on every nonzero coordinate. For `a_i=0`, the numerator is
unchanged by code choice, so `k_i=0` minimizes the denominator.

The magnitude objective is

```math
C(k;o)=
\frac{\sum_i a_i z_i}
     {\sqrt{\sum_i a_i^2}\sqrt{\sum_i z_i^2}}.
```

For one input, maximizing `C` is equivalent to maximizing

```math
Q(k;a)=\frac{(\sum_i a_i z_i)^2}{\sum_i z_i^2}.
```

The centered CAQ code is

```text
c_i = L + k_i       if o_i > 0 or o_i is zero
c_i = L - 1 - k_i   if o_i < 0.
```

It satisfies

```math
c_i+\tfrac12-L=\operatorname{sign}(o_i)(k_i+\tfrac12)
```

under the positive-zero convention. Codes use `uint32_t`; no byte narrowing
is permitted.

## Exact Scale Reduction

For a fixed magnitude vector `z`, define

```math
H(\alpha,z)=2\alpha\langle a,z\rangle
             -\alpha^2\lVert z\rVert_2^2,
\qquad \alpha\ge0.
```

### Lemma 1: fixed-code optimum

For nonzero `a` and positive `z`, the maximizing scale is

```math
\alpha^*=\frac{\langle a,z\rangle}{\lVert z\rVert_2^2},
```

and

```math
\max_{\alpha\ge0}H(\alpha,z)=Q(z;a).
```

This follows by completing the square in the scalar quadratic.

### Lemma 2: fixed-scale coordinate optimum

For `alpha>0`, set `t=1/alpha`. Dividing `H` by the positive constant
`alpha^2` shows that maximizing one coordinate is equivalent to minimizing

```math
(z_i-t a_i)^2
```

over `z_i in {1/2,3/2,...,L-1/2}`. Thus

```text
k_i(t) = clip(floor(t*a_i), 0, L-1),
```

with either adjacent level valid at an exact integer tie.

### Lemma 3: complete-event coverage

The rounded code changes only when

```text
t = j/a_i,  j in {1,...,L-1},  a_i>0.
```

Because the codebook is finite,

```math
\max_z Q(z;a)
=\max_z\max_\alpha H(\alpha,z)
=\max_\alpha\max_z H(\alpha,z).
```

Between consecutive events, `k(t)` is constant. Scoring the initial code and
every post-event state therefore scores a global optimum unless the maximizing
scale is an exact tie.

At a simultaneous tie, every lower/upper combination of the tied coordinates
has the same `H` value. Process tied events by ascending coordinate id and
score every intermediate state. If one tie combination attains global value
`Q*`, every scored tie combination has `H=Q*`; its own optimized `Q` is at
least `H` and cannot exceed the global codebook optimum, so it also has
`Q=Q*`. The deterministic chain therefore retains a global optimum.

Together, Lemmas 1--3 establish exact complete-event coverage.

## Exact Binary32 Representation

Use `std::bit_cast<uint32_t>` to decompose `|o_i|`.

For a normal binary32 value with exponent field `r` and fraction field `f`:

```text
m_i = 2^23 + f
p_i = r - 150
a_i = m_i * 2^p_i.
```

For a nonzero subnormal:

```text
m_i = f
p_i = -149.
```

Let `e=min_i p_i` over nonzero coordinates and define

```text
A_i = m_i << (p_i-e).
```

Then every magnitude is exactly `a_i=A_i*2^e`. `A_i` uses
`boost::multiprecision::cpp_int`; zero coordinates use `A_i=0`.

## Exact Event Ordering

An event is `(j,i)` with scale `j/a_i`. Compare two events without division:

```text
(j_1,i_1) precedes (j_2,i_2)
iff
j_1*A_i2 < j_2*A_i1.
```

Exact equality is broken by ascending coordinate id. Maintain one next event
per nonzero coordinate in a min-heap. After processing `(j,i)`, enqueue
`(j+1,i)` if `j+1 <= L-1`.

## Exact Objective Comparison

Use the odd grid

```text
g_i = 2*k_i+1
S   = sum_i A_i*g_i
N   = sum_i g_i^2.
```

The omitted factors are common to all codes, so

```text
Q_1 > Q_2
iff
S_1^2*N_2 > S_2^2*N_1.
```

All terms in this comparison use `cpp_int`. The initial state has `g_i=1`,
`S=sum_i A_i`, and `N=D`. When coordinate `i` advances:

```text
g_i       <- g_i+2
S         <- S+2*A_i
N         <- N+4*g_i_old+4.
```

Ties retain the earliest deterministic state. To avoid copying `O(D)` codes
at every objective improvement, record the best event ordinal and replay the
same exact event order once to reconstruct the winning code.

## Algorithm

```text
encode_exact(o,B):
  validate finite binary32 input and B
  decompose |o| exactly into common-exponent integers A
  if every A_i is zero: return degenerate

  L <- 2^(B-1)
  k <- all zeros
  S <- sum A_i
  N <- D
  score initial state as best
  heap <- event (1,i) for each A_i>0 when L>1

  ordinal <- 0
  while heap not empty:
    (j,i) <- exact minimum event
    advance k_i, S, and N
    ordinal <- ordinal+1
    compare S^2/N exactly with the best state
    if strictly better: remember ordinal and exact score
    if j<L-1: enqueue (j+1,i)

  replay exactly best_ordinal events from all-zero k
  map magnitude k and signs to uint32 centered CAQ code
  return code, exact score state, derived floating diagnostics, and counters
```

## Complexity

Let `D_+` be the nonzero-coordinate count and

```text
E=D_+(2^(B-1)-1).
```

The first scan and reconstruction replay use:

```text
time:              O(E log D_+) exact comparisons
ordinary state:    O(D)
heap state:        O(D_+)
persistent bytes:  0
```

If `W` is the maximum `cpp_int` width and `M(W)` is integer multiplication
cost, the bit-operation bound is `O(E log D_+ M(W))`, with additional exact
additions. The validator records both first-pass and replay work. This
exponential-in-`B` oracle is not a deployable replacement for CAQ.

## Result Object

The reusable C++ result contains:

```text
degenerate                  bool
total_bits                 uint32
dimension                  size_t
nonzero_dimensions         size_t
magnitude_code[D]          uint32
centered_caq_code[D]       uint32
best_event_ordinal         uint64
score_dot_integer          cpp_int
score_norm_integer         cpp_int
first_pass_events          uint64
replay_events              uint64
heap_comparisons           uint64
objective_comparisons      uint64
max_integer_bits           size_t
cosine                     long double
fac_rescale_unit_grid      long double
```

`fac_rescale_unit_grid` is `||o||^2/<o,z_signed>` for the unscaled centered
half-grid direction. Multiplying the grid by a later CAQ `delta` divides this
factor by `delta`; no persistent factor or index format is created here.

## Validator Output Schema

The synthetic validator writes one JSON object to stdout:

```json
{
  "schema_version": 2,
  "stage": "V2-A1",
  "status": "PASS",
  "oracle": {
    "name": "independent_exact_integer_complete_event",
    "official_source": false,
    "persistent_bytes": 0
  },
  "tests": {
    "bruteforce_cases": 0,
    "prior_fixture_cases": 0,
    "initial_state_cases": 0,
    "zero_cases": 0,
    "tie_cases": 0,
    "padding_cases": 0,
    "subnormal_cases": 0,
    "largest_finite_cases": 0,
    "b11_cases": 0,
    "mapping_cases": 0,
    "invalid_input_cases": 0
  },
  "work": {
    "first_pass_events": 0,
    "replay_events": 0,
    "heap_comparisons": 0,
    "objective_comparisons": 0,
    "max_integer_bits": 0
  },
  "execution": {
    "wall_time_ms": 0.0,
    "cpu_time_ms": 0.0,
    "peak_rss_bytes": 0
  }
}
```

`wall_time_ms` and `cpu_time_ms` cover the complete validator process up to
result serialization. On Linux, `peak_rss_bytes` converts `ru_maxrss` from
KiB to bytes. Release and ASAN executions are stored as separate artifacts;
the build mode is therefore an artifact property rather than a runtime input.

On a failed assertion, the process writes a concise failure reason to stderr,
sets `status` to `FAIL` when possible, and exits nonzero. No dataset path,
vector value, method threshold, or query metric is accepted as a command-line
parameter in V2-A1.

## V2-A0 Decision

The specification has no empirical enumeration window, epsilon, round count,
beam width, or fitted threshold. The only bit width and dimension inputs define
the finite codebook. Implementation may begin, but V2-A1 passes only after all
synthetic obligations in the protocol agree with complete brute force and the
independent algebraic checks.

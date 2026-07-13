# CAQ Limitation And Repair Closure: Project-Level Pivot Decision

Date: 2026-07-13

## Decision

```text
CAQ limitation hypothesis:                 ESTABLISHED in two frozen regimes
low-cost CAQ repair hypothesis:            CLOSED without a method
SAQ-centric incremental method search:     STOP
SAQ as a baseline and limitation case:     RETAIN
next authorized project stage:             PROBLEM-SELECTION REVIEW ONLY
```

The project should stop treating SAQ as the mandatory substrate on which a
publishable contribution must be built. SAQ remains a strong baseline, and the
collected evidence provides a careful account of where several plausible
extensions fail. It does not yet provide a SIGMOD/VLDB/ICDE-level main method.

The selected pivot is therefore:

> Move from **SAQ-centric incremental optimization** to a **problem-first
> research selection phase**. A future project may use SAQ as one comparator,
> but its research question, mechanism, and claim must remain meaningful if
> SAQ is replaced by another competitive quantizer.

No new implementation should begin until a bounded primary-source review
identifies a distinct database-systems problem, the closest mechanism
collisions, at least two independent competitive baselines, an explicit
overhead model, and a small falsification study.

## Why This Closure Is Necessary

The exploration has repeatedly found real local signals:

- a custom SAQ plan can be slightly faster or more accurate;
- local residual structure can prefer a plan different from the global plan;
- an alternative transform can improve one estimator stage on one dataset;
- an accurate SAQ prefix can order graph neighbors well;
- exact encoding can improve CAQ direction alignment substantially; and
- an exact local shell can cross some CAQ coordinate-local optima.

None of these signals has survived the full contribution chain:

```text
concrete limitation
-> mechanism distinct from prior work
-> fixed query-unaware rule
-> controlled build/storage/query overhead
-> cross-regime evidence
-> end-to-end Pareto improvement
-> claim large enough for a database top conference.
```

Continuing to add local plan families, score terms, encoder neighborhoods, or
search thresholds would spend more research degrees of freedom after the
relevant gates have failed. That would weaken rather than strengthen the
scientific case.

## CAQ Limitation: What Is Established

For one sign-aligned residual segment, let

```text
a_i = |o_i|                              residual magnitude
B   = total bits per dimension           including the sign bit
L   = 2^(B-1)                            legal magnitude levels
k_i in {0,...,L-1}                       magnitude code
z_i = k_i + 1/2                          half-grid representation
```

CAQ and E-RaBitQ optimize the direction objective

```math
Q(z;a)=\frac{\langle a,z\rangle^2}{\lVert z\rVert_2^2}.
```

For an encoder arm, the registered remaining-opportunity statistic is

```math
R_{arm}=
\frac{\sum_v(f_{arm,v}-f_{exact,v})}
     {\sum_v(f_{init,v}-f_{exact,v})},
```

where `f` is SAQ's source-compatible error factor, `init` is scalar
initialization, and `exact` is the independently validated complete-event
oracle. `R=1` means that the arm closes none of the initialization-to-exact
opportunity; `R=0` means that it closes all of it.

### Registered leading-segment result

| Frozen segment | Production `R_r6` | Local-fixed-point `R_local` | `r=6` code equals exact |
|---|---:|---:|---:|
| GIST `64@11` | 0.944994 | 0.944982 | 0.588% |
| CIFAR `64@9` | 0.790078 | 0.789792 | 5.673% |

All 24 preregistered one-sided hypotheses and seed checks pass. The leading
high-bit segments retain substantially more exact opportunity than the
same-dimensional `B=4`, next-segment, and whole-positive-view controls.
Continuing the identical coordinate rule to a local fixed point changes almost
nothing, so the result is not an insufficient-round explanation.

The unchanged full-code estimator also responds to the exact code:

| Dataset | CAQ normalized base-pair error | Exact error | Relative reduction |
|---|---:|---:|---:|
| GIST | `7.22014e-5` | `6.25152e-5` | 13.42% |
| CIFAR | `2.84696e-4` | `2.61114e-4` | 8.28% |

This establishes the following narrow limitation:

> Under the frozen GIST and CIFAR plans, SAQ's short leading high-bit segments
> amplify a CAQ coordinate-local optimization gap that survives ordinary
> local convergence and affects the unchanged estimator.

It does not establish a recall/QPS gain, a repair, or a general failure of
SAQ.

## CAQ Repair: Why The Direction Closes

### Full exact encoding is not deployable

| Encoder arm | Mean CPU per encoding | Relative to production `r=6` |
|---|---:|---:|
| CAQ `r=6` | 9.28 us | 1.00x |
| Same rule to local fixed point | 18.55 us | 2.00x |
| Complete-event exact oracle | 2,531.50 us | 272.92x |

The exact oracle processes 16.58 billion first-pass events and 161.80 billion
heap comparisons in the registered study. It is a labeler, not a method.

### The only reviewed low-cost candidate fails its complexity gate

The bounded repair review found a direct objective collision with scaled
codebook quantization and E-RaBitQ event enumeration. It rejected extra CAQ
rounds, alternating scale/assignment, fixed event windows, complete events,
ordinary exact fallback, and generic branch-and-bound as occupied, unjustified,
or implausibly expensive.

The only conditional candidate was the exact radius-one Cartesian shell

```math
\mathcal N_1(k)=\prod_i
\left(\{k_i-1,k_i,k_i+1\}\cap\{0,\ldots,L-1\}\right),
```

which contains up to `3^D` codes but can be solved with at most `2D` ordered
shared-scale events. It gives a shell-local certificate, not a global one.

The implementation is correct on 6,060 exhaustive input/code cases and
110,230 brute-force shell codes. The fixed-width path matches the exact path
on 6,066 supported cases. Correctness is not the failed gate.

| Synthetic `D=64` profile | B | Shell / CAQ CPU | Total `CAQ + shell` / CAQ |
|---|---:|---:|---:|
| balanced | 11 | 7.169x | 8.169x |
| dyadic | 11 | 4.751x | 5.751x |
| balanced | 9 | 3.579x | 4.579x |
| dyadic | 9 | 4.600x | 5.600x |

The frozen total-cost maximum was `2.0x`. The fastest row is already `4.579x`.
Each encoding orders 120-127 events with 972-1,031 128-bit comparisons, while
the measured rows use zero exact-objective fallbacks. The cost is structural
to the comparison-based `O(D log D)` shell realization, not an accidental
arbitrary-precision fallback.

The gap-recovery half of the conjunctive gate was correctly not run after the
complexity failure. Increasing radius, repeating the shell, introducing a
selective threshold, or replacing exact ordering with an empirical window
would be post-hoc rescue rather than the reviewed method.

### CAQ closure statement

```text
The high-bit CAQ local-optimum limitation is real,
but neither complete exact encoding nor the minimal exact coordinated shell
moves the build-cost versus estimator-error frontier at acceptable cost.
```

This is useful limitation evidence. It is insufficient as a standalone method
contribution.

## Project-Wide Direction Synthesis

The following table evaluates every substantive SAQ-centered direction under
the same publication-level question: did it turn a concrete limitation into a
distinct, query-unaware, overhead-controlled Pareto improvement?

| Direction | Strongest evidence | Decisive limitation | Decision |
|---|---|---|---|
| Default-neighborhood fixed policy | GIST B=3/4/5 QPS ratios `1.112x/1.195x/1.079x` with recall deltas `+0.00159/+0.00077/+0.00028`; CIFAR has smaller positives | Handwritten families and empirical scorer; full-GIST planning takes 145-151 s versus 2.3-3.0 s index builds | Stop as main method |
| Mixed shared local plans | GIST R@100 rises from `0.94469` to `0.94548` | QPS falls to `0.909x`; mixed query state and layout overhead dominate | Closed |
| Single-global static cost DP | Five-dataset offline matrix finds no lower-cost plan dominating SAQ risk | Two GIST near-frontier plans are slower; at nprobe 200 QPS is `2503/2674` versus default `2732` | Closed |
| Measured `fac_error` planner objective | Different GIST plan is 4.7% smaller and `1.34x` faster at fixed nprobe | R@100 falls from `0.99132` to `0.99059`; recall recovery removes the speed advantage | Limitation evidence only |
| Search scheduling and bounds | Fast-stage pruning removes 45-58% and accurate refinement often exits early | Variance pruning is only 0.14-0.45%; useful pruning needs 58-63% median slack removal without a safe derivation | Closed |
| Graph traversal with SAQ prefixes | First accurate SAQ prefix improves fixed-neighborhood ordering over SymphonyQG | Complete estimator time is `52.5x`, or `26.8x` after grouping; random graph access conflicts with IVF/FastScan layout | Closed before full graph integration |
| PCA/residual-PCA transform replacement | GIST shows about 0.60%/0.33% RMSE reductions at two stages | Registered CIFAR replication gives `+0.0046%/-0.0235%` and fails confidence, seed, rotation-off, and no-harm gates | Closed |
| Lossy projection | Exact tail-norm surrogate makes tail-summary precision negligible | At GIST `d=576`, top-100 agreement is `0.99289` versus native SAQ `0.99462`; boundary inversion is also worse | Closed before projected SAQ build |
| CAQ exact-gap repair | Registered GIST/CIFAR limitation and estimator effects are strong | Exact oracle is `272.9x`; exact one-shell total cost is `4.579x-8.169x` versus the `2.0x` gate | Limitation retained, method closed |

### Cross-direction pattern

The failures are not independent accidents. They reveal four recurring
properties of the problem.

1. **SAQ is an integrated design.** PCA ordering, global segmentation, CAQ,
   factors, FastScan layout, staged estimation, and IVF scanning interact.
   Improving one proxy often moves cost or error elsewhere.
2. **Offline proxy improvements do not imply search improvement.** Lower
   variance risk, lower code volume, lower `fac_error`, or better local order
   can fail at recall-matched QPS.
3. **Access pattern dominates nominal arithmetic.** Mixed plans and graph
   traversal lose primarily through query-state preparation, block
   utilization, layout, and dispatch rather than the advertised distance
   formula.
4. **The remaining gains are too incremental.** The strongest positive rows
   are small local corrections with substantial empirical or offline work.
   The strongest principled limitation, CAQ local optimality, has no accepted
   low-cost repair.

This evidence raises the standard for another SAQ-specific idea. A new local
objective or schedule is no longer plausible merely because it differs from
SAQ's default choice.

## Strict-Reviewer Assessment

A strict SIGMOD/VLDB/ICDE reviewer would likely accept the following points:

- the project evaluates negative controls rather than reporting only winners;
- the CAQ limitation study is preregistered, source-aligned, statistically
  controlled, and tied to the unchanged estimator;
- the graph and transform directions stop before expensive end-to-end work
  when their lower-level gates fail; and
- overhead, storage, and query work are usually reported explicitly.

The same reviewer would likely reject the current material as a full paper:

- there is no new quantizer, planner, index, or estimator that survives its
  final gate;
- the fixed-policy positives resemble SAQ-specific empirical tuning;
- most effects are small or limited to GIST;
- the strongest exact mechanism is much slower than CAQ; and
- a collection of careful negative results does not by itself supply a main
  database-systems contribution.

The correct claim is therefore not "we nearly have a method." It is:

> We now understand several SAQ extension boundaries well enough to stop
> spending implementation effort on incremental variants that lack a plausible
> publication path.

## Project-Level Options

### Option 1: Continue local SAQ optimization

```text
Decision: REJECT
```

This would mean more candidate families, score terms, planner weights,
neighborhoods, or search thresholds. Existing evidence predicts small gains,
more overhead, and weak novelty. It would also violate several completed stop
rules.

### Option 2: Present the current repository as a complete SAQ follow-up paper

```text
Decision: REJECT FOR A TOP-CONFERENCE FULL PAPER
```

The limitation evidence is useful for a meeting, technical report, artifact,
or a limitations section in future work. Without a surviving method, it is not
a complete main contribution.

### Option 3: Preserve SAQ as one baseline but pivot to a problem-first project

```text
Decision: SELECT
```

The next research question must not be phrased as "which SAQ component can we
change?" It should first identify a broader vector-search problem, review
competing approaches, and derive a mechanism whose value is not conditional on
SAQ's exact plan representation.

### Option 4: Delete or merge all experimental branches

```text
Decision: REJECT
```

The branches contain useful negative evidence and correctness instruments.
They should remain immutable research records, not be merged wholesale into
the baseline or deleted.

## Selected Pivot Protocol

The next stage is a bounded **problem-selection review**, not implementation.
It should produce one decision note with the following columns for each
candidate research problem:

```text
database problem and affected workload
closest primary methods and what they already solve
remaining mechanism-level gap
why the question is not SAQ-specific
query-unaware information available at build time
time, space, build, and query complexity
minimum falsification experiment
strict-reviewer objection
GO / NO-GO decision
```

A candidate may pass only if:

1. its central claim remains meaningful with at least two independent strong
   baselines rather than only SAQ;
2. the proposed mechanism is not a direct composition or parameter change of
   the closest work;
3. overhead is part of the objective from the beginning;
4. any hyperparameter has a mechanism-derived scale rather than a benchmark
   sweep;
5. the first experiment can falsify the premise before a broad implementation;
6. expected evidence includes more than one dataset regime and does not begin
   by optimizing GIST; and
7. a plausible full-paper contribution can be stated before coding.

No candidate has passed this new gate yet. Naming a direction without this
review would repeat the pattern this synthesis is intended to stop.

## Branch And Artifact Policy

- Keep `saq-correctness-base` at `bc7829b` as the reliable SAQ baseline with
  only confirmed correctness fixes.
- Keep `saq-caq-one-shell-repair` as the CAQ repair closure branch and preserve
  `f2c877b` as its implementation/evidence checkpoint.
- Keep all other experimental branches as negative-evidence records.
- Do not merge experimental planners, scorers, profilers, graph adapters,
  transform runners, projection runners, or exact encoders into the baseline.
- After the problem-selection review passes, create a new clean branch from
  `saq-correctness-base` if SAQ code is still needed. Use a separate repository
  if the selected problem is no longer naturally expressed in SAQ.

## Evidence Ledger

| Evidence checkpoint | Primary closure evidence |
|---|---|
| `saq-boundary-audit@e582974` | `docs/saq_fixed_policy_novelty_overhead_audit_2026_07_07.md`, `docs/saq_fixed_policy_overhead_evaluation_2026_07_07.md` |
| `saq-structural-followup@b71c699` | `docs/shared_plan_negative_evidence_and_dp_pivot_2026_07_08.md` |
| `saq-global-cost-dp@699d2c9` | `docs/limitation_evidence_and_pivot_2026_07_08.md` |
| `saq-planner-objective-analysis@5756412` | `docs/saq_variance_bound_inactivity_final_2026_07_09.md` |
| `saq-graph-traversal-analysis@a03ee40` | `docs/saq_graph_phase4_complete_work_evidence_2026_07_11.md` |
| `saq-transform-analysis@3d94840` | `docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md` |
| `saq-lossy-projection-analysis@051ec6a` | `docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md` |
| `saq-caq-one-shell-repair@f2c877b` | `docs/saq_caq_co0_v2_b1_registered_evidence_2026_07_12.md`, `docs/saq_caq_one_shell_synthetic_falsification_2026_07_12.md` |

## Final Project Decision

```text
STOP:  further SAQ-specific local method development
KEEP:  correctness fixes, validated instruments, and negative evidence
DO:    one problem-first primary-source selection review
THEN:  open one clean branch only for a candidate that passes novelty,
       complexity, and falsifiability gates
```

This decision does not assert that SAQ is optimal or that vector quantization
has no remaining research questions. It asserts that the current evidence no
longer justifies treating another incremental SAQ modification as the default
next experiment.

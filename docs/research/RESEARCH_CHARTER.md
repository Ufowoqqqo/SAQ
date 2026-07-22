# Database-Systems Research Charter

This charter contains reusable scientific standards for SAQ and related ANN
quantization research. Read it for idea evaluation, experiment design,
literature/novelty review, and scientific conclusions. It does not grant or
restrict data access; the active `TASK.md` does that.

## Research objective

Seek a result that could survive strict SIGMOD/VLDB/ICDE review. A useful
result identifies a consequential systems limitation, proposes a mechanism
that is more than direct composition or parameter variation, and demonstrates
a reproducible trade-off against strong baselines. A negative result is useful
when it cleanly eliminates a plausible mechanism or exposes a hidden cost.

## Closest-primary-work review

Before claiming novelty or investing in a substantial new direction:

1. identify the closest primary papers and official implementations;
2. state precisely what each already solves, including objective, model class,
   information used, and construction/query assumptions;
3. distinguish the remaining gap from a renamed primitive, direct composition,
   implementation detail, or hyperparameter change;
4. check whether a standard baseline already spans the proposed feasible set;
   and
5. cite primary sources for decisive technical claims.

Do not require a broad survey for a small implementation task. Scale the review
to the novelty and decision risk.

## SAQ-specific limitation

Tie every proposed direction to a concrete SAQ or database-system limitation:

- representation or bit-allocation mismatch;
- estimator error or ranking behavior;
- construction time or memory;
- index size or metadata;
- table-building or scan cost;
- update/maintenance cost;
- hardware efficiency; or
- an accuracy/latency frontier that existing methods do not reach.

A lower encoding objective alone is insufficient. Explain how the limitation
affects the actual consumer, estimator, index, or workload. If the proposal
requires a new representation or query consumer, say so explicitly rather
than presenting it as an unchanged-SAQ substitution.

## Falsifiable claims

Formulate the smallest claim that can be wrong. Specify:

- independent variable and unchanged components;
- population, dataset, and workload;
- primary metric and material effect size;
- baseline and control behavior expected under alternative explanations;
- resource ceiling and unacceptable trade-offs; and
- interpretation of both pass and failure.

Prefer an early, cheap discriminating experiment. Freeze only choices that
would otherwise be vulnerable to outcome-dependent tuning. Do not turn normal
research planning into a chain of authorization artifacts.

## Novelty and mechanism

For each claimed contribution, ask:

- Is the mechanism already implied by known scalar/vector quantization,
  transform coding, bit allocation, packed lookup, or ANN indexing work?
- Is the gain caused by the proposed mechanism, a stronger optimizer, more
  training, extra metadata, a different representation, or a weaker workload?
- Does the method introduce a new information source or model class?
- Could the same result be obtained by tuning an established baseline?
- What mechanism-level prediction distinguishes the proposal from competing
  explanations?

Novelty should be stated narrowly. A useful systems contribution may be a new
Pareto point or integration insight, but only when the end-to-end costs and
consumer behavior are measured fairly.

## Baselines, controls, and ablations

Use the closest deployable baseline, not only an intentionally constrained
variant. Match payload or index size, training data, quality/recall target,
hardware, threads, compiler optimization, and tuning opportunity.

Controls should isolate plausible causes. Typical comparisons include:

- the incumbent method with the same optimizer and budget;
- a stronger model class that measures remaining opportunity;
- a standard implementation that measures deployment relevance;
- ablations removing each new mechanism; and
- sensitivity checks for choices whose scale is not theoretically fixed.

Do not count two training procedures for the same model class as independent
scientific evidence. Treat disagreement first as optimizer or implementation
adequacy evidence.

## Full systems cost

Measure costs that can change the paper claim:

- construction/training CPU and wall time;
- permanent model and index bytes;
- transient and peak memory;
- encoding and serialization work;
- verification or replay cost when it is part of the proposed workflow;
- query-table construction and query/scan work;
- update, rebuild, and maintenance cost; and
- any added indirection, branch, copy, allocation, or dispatch.

Keep provenance, logging, JSON, compression, and archival work outside timed
scientific hot paths unless the claim includes them. Report them separately
when reproducibility cost matters. Do not hide them or let them dominate the
implementation before scientific feasibility is known.

## Implementation and performance evidence

Start with the smallest correct prototype. Compile, test, and use exact or
exhaustive tiny references where affordable. A prototype may establish
correctness or feasibility but is not performance evidence.

Before a performance claim:

1. identify the scientific hot path and expected complexity;
2. establish a correct baseline under matched conditions;
3. profile a representative workload with standard tools;
4. optimize the largest measured bottleneck;
5. remeasure absolute performance and dispersion; and
6. verify correctness or recall parity plus build time, memory, and index size.

Claim a frontier movement only when a reproducible fair comparison supports
it. Never obtain speed by silently weakening quality, recall, payload, or
baseline tuning.

## Deterministic reproduction

Record enough information for another researcher to repeat the relevant
result:

- source revision and dependency revision;
- exact command and working directory;
- compiler/build type and important flags;
- dataset identity and permitted subset rule;
- seeds and deterministic tie behavior;
- hardware, threads, affinity, and NUMA policy;
- warmup, repetition, aggregation, and dispersion; and
- output location plus the interpretation rule.

Independent review means critically checking the claim or rerunning the stated
procedure from a fixed snapshot. It is useful for paper-relevant or surprising
claims, but it is not a mandatory gate for every edit.

## Negative results

Preserve negative evidence with the same care as positive results. Record the
question, method, exact failure, verified scope, and what remains unresolved.
Separate:

- hypothesis falsification;
- implementation or artifact validation failure;
- resource-budget failure;
- inconclusive measurement; and
- a result outside the intended consumer or workload.

Do not rescue a failed hypothesis by changing datasets, metrics, thresholds,
or baselines after seeing the result. It is acceptable to fix genuine defects
and rerun the same question.

## Claim boundaries

Every conclusion should separate:

- verified evidence;
- inference supported by that evidence;
- unresolved uncertainty; and
- claims explicitly not established.

Synthetic reconstruction does not establish natural-data prevalence, Recall,
QPS, novelty, or production viability. Source parity and bug fixes do not
establish a research contribution. Base-only estimators are not benchmark
query results. A new representation is not an unchanged-SAQ improvement.

## Strict-reviewer checklist

Before presenting a result, anticipate these objections:

- Is this already known or a direct composition?
- Is the limitation specific and consequential to the real system?
- Are baselines equally optimized and matched in resources and quality?
- Does the estimator/query consumer actually benefit?
- Are construction, storage, table, verification, update, and query costs all
  visible?
- Were thresholds, datasets, seeds, and ablations chosen before outcomes?
- Are results deterministic and independently reproducible?
- Is the effect material across datasets and operating points?
- Does the method move a relevant Pareto frontier?
- Are negative cases and claim boundaries reported honestly?

## Possible future skill split

If repo-local Codex skills are adopted later, this charter naturally separates
into `research-cycle` (idea, prior work, hypothesis, minimal experiment,
implementation, analysis) and `experiment-audit` (exact reproduction and
independent review when explicitly requested). The repository currently has no
local skill infrastructure, so this refactor does not introduce it.

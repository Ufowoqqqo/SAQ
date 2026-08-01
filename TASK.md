# Completed Task: mixed-radix synthetic mechanism witness

## Branch and base

- Active branch: `saq-mixed-radix-query`
- Base: `4008614c` (`Evaluate original mixed-radix query hypothesis`)
- Mode: `REVIEW`
- Status: completed and accepted on 2026-08-01

## Research question

Can the existing arbitrary-radix allocator, packed representation, and native
complete-word consumer exhibit a deterministic Recall advantage over the
otherwise identical dyadic control when the coordinate support cardinalities
straddle power-of-two boundaries?

This is a mechanism witness, not an attempt to reverse the SIFT1M/GIST1M
NO-GO or establish natural-data prevalence. The frozen positive condition is

```text
K1*K2 <= 2^B
ceil(log2(K1)) + ceil(log2(K2)) > B.
```

## Frozen scenarios and hypothesis

Run exactly four scenarios:

- positive B4: `(K1,K2)=(3,5)`;
- null B4: `(K1,K2)=(4,4)`;
- positive B8: `(K1,K2)=(15,17)`; and
- null B8: `(K1,K2)=(16,16)`.

Every other adjacent pair uses the corresponding null support. Training
marginals have deterministic counts aligned to the existing 1,024-bin rank
histogram. Base data contains 100 exact duplicates of every first-pair
prototype; one query is placed exactly at every prototype, with all other
coordinates fixed. The single shared IVF list contains every candidate and
top-k is 100, so the exact ground truth is the 100 duplicates of the query's
prototype.

The falsifiable hypothesis is:

- in each positive scenario A selects the named non-dyadic shape, has no code
  collision, and obtains Recall@100 1.0 while D obtains Recall@100 below 1.0;
- in each null scenario A and D select the same shape, produce identical
  rankings, and both obtain Recall@100 1.0.

Do not tune levels, counts, duplicates, top-k, noise, seeds, or scenarios after
observing outcomes. If the existing allocator or consumer does not produce
the expected separation, report that result without rescue.

## Scope and paths

Relevant existing source:

- `research/a4_or_c/core.{hpp,cpp}`: scalar curves and pair allocation;
- `research/a4_or_b/models.{hpp,cpp}`: 128-dimensional model construction;
- `research/mixed_radix_query/mixed_index.{hpp,cpp}`: packing and index build;
- `research/structured_2d/synthetic_timing.{hpp,cpp}`: native complete-word
  consumer.

Allowed reads are repository source, Git metadata, and the completed
mixed-radix result documents. Do not read any natural dataset, benchmark
query, ground truth, serialized natural index, or prior natural measurement
file for this task.

Allowed writes are `TASK.md`, focused code/tests under
`research/mixed_radix_query/`, minimal CMake integration under
`research/structured_2d/`, a focused result note under `docs/research/`, and
generated witness output under `/tmp/mixed-radix-query/synthetic-witness-v1/`.
Do not modify production `saqlib/`.

## Commands and budget

Allowed commands are repository inspection, CMake build, CTest, the focused
synthetic witness executable, Python syntax checks, and result inspection.

Limits: 2 aggregate CPU-hours, 2 wall-hours, and 4 GiB peak RSS. Use one
process; diagnostic timing is not performance evidence. No parameter sweep,
natural-query run, or new dataset download is allowed.

## Deliverables and done criteria

Deliver:

- deterministic training/base/query generation in source;
- explicit allocator shapes and SSE for A and D;
- valid-label and code-collision checks;
- actual Recall@100 through the same native complete-word consumer;
- ranking-hash equality for null controls and inequality for positive cases;
- exact command, output path, resource cost, limitations, and a concise
  mechanism interpretation.

Done means all four frozen cases run, the output is deterministic across two
executions, relevant tests and `git diff --check` pass, and the result is
reported strictly as a synthetic mechanism witness.

Outcome: all four cases passed their frozen predictions. Positive B4 gave A/D
Recall@100 `1.0/0.8`; positive B8 gave `1.0/0.941176`. Both null controls gave
identical A/D rankings and Recall 1.0. Two runs were byte-identical. See
`docs/research/mixed_radix_synthetic_witness_result_2026_08_01.md`.

Current blocker: none. There is no active experiment. The smallest next
action is to use this witness as an explanatory positive control alongside,
not instead of, the SIFT1M/GIST1M negative result.

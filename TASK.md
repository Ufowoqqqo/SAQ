# Current Task: unchanged-estimator integration gate

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Base commit: `5503e87d0584fe50c9233fbe3a02cdd577db07ea`
- Gate snapshot: `0dfa0df2cfca44d3bd17cb400192ea3f17e4ac03`
- Mode: `REVIEW`; implementation is allowed only if the admission mapping
  shows that the production estimator can consume S without semantic changes.

## Research question

Can the compact shared-affine S100 representation enter the existing
production SAQ accurate-estimator path while leaving all of the following
unchanged?

- the B-bit candidate code and its meaning;
- the per-vector norm and `ExFactor.rescale`;
- the segment plan, rotations, padding, index format, and candidate schedule;
- the accurate-estimator formula and lookup count; and
- the absence of per-cluster model ids or mixed dispatch.

The cheapest decisive check is an interface and code-semantics mapping before
any synthetic timing. If the existing estimator has no consumer for S's joint
two-coordinate label and learned codebook, the gate stops as incompatible;
writing a new consumer is not a repair of an unchanged-estimator gate.

## Decision

The admission mapping fails:

```text
NO_GO_UNCHANGED_ESTIMATOR_INTEGRATION
```

Production SAQ stores and consumes per-coordinate short and long bitplanes.
Within each segment, its accurate path reconstructs an inner product using
that segment's uniform `sq_delta`, per-vector `ExFactor.rescale`, and the
existing fast-scan state. S instead stores one joint label per
adjacent-coordinate group and evaluates it through a learned K-entry
two-dimensional squared-distance table.

There is no production interface that interprets S's joint label as the
unchanged bitplanes. The current `research/structured_2d` lookup loop is a
different full-word VQ consumer. Calling that loop the production SAQ
estimator, forcing `rescale=1`, or multiplying `rescale` into its table would
change the estimator semantics and cannot pass this gate.

This confirms that the earlier A4 R0 compatibility result also applies to the
shared-affine S representation. It is not a new negative result about S's
reconstruction quality or compact-builder performance.

## Relevant paths

- `research/structured_2d/compact.{hpp,cpp}`
- `research/structured_2d/microbench.{hpp,cpp}`
- `research/structured_2d/model_test.cpp`
- `saqlib/index/ivf.hpp`
- `saqlib/quantization/saq_searcher.hpp`
- `saqlib/quantization/saq_estimator.hpp`
- `saqlib/quantization/caq/caq_estimator.hpp`
- `saqlib/quantization/fastscan/lut.hpp`
- `saqlib/quantization/cluster_data.hpp`
- `docs/saq_attempt4_r0_static_compatibility_decision_2026_07_22.md`
- `docs/saq_structured_2d_base_only_result_2026_07_23.md`

## Allowed reads and writes

Allowed reads are the source, Git metadata, current-task documents, and
build/test outputs newly produced in this worktree.

Allowed writes are `TASK.md`, concise documentation under `docs/`, focused
tests under `research/structured_2d/` if an unchanged interface exists, and
temporary build output under `/tmp`.

## Forbidden reads and changes

Do not read benchmark queries, ground truth, Recall/QPS results, serialized
indexes, variance files, unrelated branch outputs, raw held-out rows, or any
registered natural-data input. Admission failed before numerical evaluation,
so this gate needs no dataset access.

Do not modify production SAQ/CAQ source, the estimator, code layout, index
format, plan, candidate schedule, fast stage, or `rescale` semantics. Do not
add a new table consumer, decoder, model id, per-cluster state, mixed
dispatch, or query-trained rule under this gate.

## Allowed commands and budget

```bash
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
git diff --check
git status --short --branch
```

Budget remains one process, one computational thread for measurements, at
most 16 GiB peak RSS, and at most 2 CPU-hours. No numerical integration
experiment or timing is warranted after the admission failure.

## Deliverables and done criteria

Deliver:

- an exact current-source mapping of the production accurate-estimator path;
- an explicit comparison with S's compact full-word table consumer;
- a truthful pass/fail decision without implementing a replacement
  estimator; and
- a concise update to the existing structured-2D result note.

Done means the source mapping is verified at the named snapshot, the existing
structured-2D Release test still passes, the result note records the claim
boundary, and no forbidden data or production source was touched.

## Current blocker and one next action

The blocker is semantic, not an implementation bug: S's joint-label
representation has no unchanged production SAQ consumer.

The next action requires a scientific-scope choice from the user: either
authorize a new full-word VQ consumer and treat S as a different ANN
representation, or redesign the candidate around the existing per-coordinate
bitplanes. Neither choice belongs to this completed unchanged-estimator gate.

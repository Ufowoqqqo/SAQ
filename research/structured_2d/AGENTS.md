# Structured 2D local guidance

## Scope

Test one query-unaware base-only mechanism: a shared two-dimensional codebook
with one mean and one full 2x2 affine transform per fixed adjacent-coordinate
group. Compare it fairly with the inherited D and independent V controls.

This is a feasibility prototype, not performance evidence or a production SAQ
implementation.

## Dependencies

Reuse:

- `../a4_or_b/panel.{hpp,cpp}` for registered panels;
- `../a4_or_b/models.{hpp,cpp}` for D/V training and unchanged evaluation;
- `../a4_or_c/core.{hpp,cpp}` for scalar allocation;
- the repository's pinned Faiss for deterministic 2D K-means.

Do not copy or alter those implementations unless a demonstrated correctness
defect prevents this task.

## Boundaries

Write only within this directory, focused result documentation, `TASK.md`, and
temporary build/output directories. Do not modify production SAQ/CAQ code.

Read only the registered base PCA, centroid PCA, assignment files, inventories,
relevant source, and current-task documents. Never read benchmark queries,
ground truth, Recall/QPS results, serialized indexes, or unrelated branch
outputs.

Fit all means, transforms, shared shapes, assignments, and stopping decisions
from fit rows only. Held-out rows are evaluation-only.

## Review clarity

New or materially changed research code must include concise comments for:

- the scientific mechanism implemented by a non-obvious block;
- the formula represented by numerical accumulators or matrix updates;
- invariants that make a compact or optimized path equivalent to its
  reference; and
- deliberate numeric tolerances, stopping rules, and memory-accounting
  boundaries.

Comments should explain why the code is correct and what claim it supports,
not restate individual statements. Keep functions small enough that a human
reviewer can follow data ownership, fit/held-out separation, and units without
reverse-engineering the experiment.

## Build and tests

```bash
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
```

Keep one computational thread for measured runs. Use fixed seeds. The original
result keeps its iteration-20 snapshot; the authorized convergence check may
continue it to the fit-only stopping rule in `TASK.md`. Generated outputs
belong under `/tmp`.

## Local done criteria

The candidate must have deterministic tests for affine expansion, compact
bytes, validity, and encoding replay. For S, final occupancy means every
shared label is used in the pooled fit assignment; still report per-group
empty labels as an efficiency diagnostic. For independent V, require every
label in every group. Run D/S/V on the identical GIST and CIFAR panels at
B4/B8, report reconstruction, group, pair-proxy, time, compact and transient
memory, and table entries, then apply the frozen `TASK.md` decision without
rescue sweeps.

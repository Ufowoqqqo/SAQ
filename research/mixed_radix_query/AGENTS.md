# Mixed-radix query evaluation

Obey the active `TASK.md`.  This directory contains the fixed-adjacent
consumer and may receive only minimal integration needed for the currently
authorized matched-coordinate pilot.

Both fixed and matched arms use `label=z1+K1*z2`, one fixed-width label per
group, and the same complete `2^B` table scan.  A matched sidecar may select
which two of the 128 head coordinates feed each group, but it must be a full
permutation, add no per-vector state, and never affect PCA, IVF assignment,
candidate generation, the GIST tail, or the per-candidate scan loop.

Generated indexes and results belong under `/tmp`.  Tests must cover packing,
pair-sidecar validity and round-trip, direct-distance parity, stored labels,
save/load, and matched consumer behavior.  Natural runs must use only the
datasets, probes, arms, repetitions, and resource limits frozen in `TASK.md`.

# Mixed-radix query evaluation

Implement only the fixed-adjacent two-coordinate A128 and power-of-two
D128_FULL representations defined in `TASK.md`. Reuse the frozen scalar
allocation code and inherited SIFT1M/GIST1M PCA, IVF, schedule, and timing
infrastructure.

The two arms must differ only in the radix restriction. Use
`label=z1+K1*z2`, reject invalid stored labels, and run both through the same
complete `2^B` table consumer. Do not add adaptive grouping, query-trained
choices, a separable D fast path, or production SAQ changes.

Write generated indexes and results only under `/tmp`. Tests must cover B4/B8
packing, valid labels, direct reconstruction parity, deterministic save/load,
and identical consumer dispatch. Natural-query runs must obey the data,
thread, repetition, and resource boundaries in `TASK.md`.

# Frozen original mixed-radix Recall/QPS design

Date: 2026-07-30

This note fixes the query experiment before any A128 query result is read. It
tests the original idea: two adjacent scalar quantizers share one packed word,
and arbitrary integer radices may use that word more flexibly than powers of
two. It does not test structured 2D VQ and does not use reconstruction error
as a substitute for Recall.

## Representation

The first 128 PCA residual coordinates form 64 fixed adjacent pairs. For pair
`g`, scalar labels `z1` and `z2` have fitted cardinalities `K1` and `K2`. The
packed address is

```text
label = z1 + K1 * z2
```

and must satisfy `K1*K2 <= 2^B`, where `B=4` for a 32-byte vector and `B=8`
for a 64-byte vector. Addresses from `K1*K2` through `2^B-1` are paid-for
states but are invalid and must never be emitted by the encoder.

`A128` permits arbitrary positive integer `K1,K2`. `D128_FULL` restricts them
to powers of two. Both use the existing base-only scalar allocation objective,
the same fit rows, the same scalar-center construction, the same byte packer,
and the same query consumer.

For GIST, dimensions 128 through 959 are reconstructed as the selected coarse
centroid; their exact query-to-centroid squared norm is added once per list.
For SIFT there is no tail.

## Consumer and correctness

For every selected IVF list and every pair, the consumer builds all `2^B`
distance entries from the query residual and the expanded Cartesian scalar
centers. It then decodes one label and performs one lookup per pair and
candidate. Invalid entries are assigned infinity for checking but should be
unreachable in stored payloads.

The timed implementation uses the pinned Faiss distance-table construction
and packed-code decoders in a focused IVFPQ list scanner. Invalid addresses
map to infinity and are rejected. A scalar direct-reconstruction calculation
is the correctness reference. A and D execute this exact scanner; matched
PQ128 uses Faiss's standard optimized IVFPQ scanner.

This deliberately rejects D's prior separable-table optimization. A and D are
timed through the same complete-table loop so the comparison isolates radix
choice. PQ/OPQ remain external optimized controls and expose whether the whole
mixed-radix representation is deployably competitive.

Before natural-query measurement:

1. exhaustive tiny labels must round-trip through B4 and B8 packing;
2. no encoded base label may be outside its pair's used Cartesian product;
3. expanded-table lookup must equal direct float64 reconstruction distance on
   deterministic fixtures;
4. saved and loaded indexes must return identical IDs and distances; and
5. A and D must execute the same consumer function.

## Workload and interpretation

The experiment reuses the already identity-bound SIFT1M/GIST1M objects,
full-PCA state, `nlist={1024,4096}`, base/query assignments, ordered lists,
32/64-byte budgets, full probe schedules, Recall@100 definition, one-thread
latency, 12-core batch QPS, affinity, warmup, and seven repetitions from the
frozen structured-2D query infrastructure.

The primary scientific contrast is A128 versus D128_FULL. Matched
PQ128/OPQ128 points are mandatory deployability context. Report every measured
point and the discrete Pareto relations. A wins scientifically only if its
radix flexibility yields a reproducible, material Recall--QPS improvement
that cannot be explained by different candidates, bytes, query work, or
training access. A small positive Recall change without a useful frontier
movement is negative evidence for the contribution claim.

The encoder and all workload choices above are frozen before inspecting any
A128 query or ground-truth outcome.

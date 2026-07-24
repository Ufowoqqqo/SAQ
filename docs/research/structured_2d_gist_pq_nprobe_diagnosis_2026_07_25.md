# GIST PQ Recall versus nprobe diagnosis

Date: 2026-07-25  
Branch: `saq-structured-2d-modeling`

## Question

The first natural-query cell for GIST1M, `nlist=1024`, 32-byte
`PQ128_M32X8`, produced Recall@100 that rose through `nprobe=8` and then
declined sharply. The diagnostic question was whether this came from query
routing or Recall bookkeeping, a residual-PQ scanning defect, or the frozen
head-only reconstruction itself.

## Checks

All checks used the already bound official GIST1M queries and ground truth,
the same PCA and saved ordered coarse lists, and the frozen Recall@100 rule.
The diagnostic outputs under `/tmp/structured-2d-natural/` are not final
performance measurements because they preceded the required cross-arm cyclic
ordering.

| nprobe | PQ128 Recall | full-dimensional PQ Recall | IVF-Flat Recall |
| ---: | ---: | ---: | ---: |
| 1 | 0.14501 | 0.07927 | 0.15784 |
| 2 | 0.21974 | 0.10059 | 0.26911 |
| 4 | 0.28340 | 0.11561 | 0.41476 |
| 8 | 0.30499 | 0.12305 | 0.57058 |
| 16 | 0.29336 | 0.12606 | 0.72477 |
| 32 | 0.25154 | 0.12700 | 0.85600 |
| 64 | 0.18857 | 0.12724 | 0.94472 |
| 128 | 0.11223 | 0.12727 | 0.98758 |
| 256 | 0.04790 | 0.12727 | not needed |

IVF-Flat was stopped after `nprobe=128` because monotonic candidate/Recall
behavior was already decisive and the exact full-vector scan was consuming
material budget. The full-dimensional PQ check completed all frozen probes.
Output hashes and Recall were stable across the completed repetitions.

The optimized head-only scanner also has a direct synthetic reconstruction
fixture. It verifies the score

```text
PQ distance over the first 128 residual coordinates
+ squared(query tail - selected cell centroid tail)
```

including the list-dependent tail term and a shared top-100 heap.

## Finding

The decline is not caused by ground-truth parsing, Recall counting, ordered
list selection, or generic cross-list search. Exact IVF-Flat improves
monotonically on the same candidates, and full-dimensional residual PQ
improves then saturates rather than collapsing.

The mechanism is the frozen GIST head-only reconstruction. PQ128 spends all
32 bytes on the first 128 PCA coordinates, which gives it strong ordering at
small probe counts. The remaining 832 coordinates are not encoded per
vector; every vector in a cell reuses that cell's coarse-centroid tail.
Increasing `nprobe` introduces more independently approximated tail
constants. Candidates from additional cells can therefore receive an
artificially small reconstructed tail distance even when their true tails
are not close to the query. These false positives increasingly displace true
neighbors from the global top 100.

This is a negative property of the preregistered representation, not a
correctness defect to repair. The final matrix must retain every frozen
`nprobe`, must not force a monotone envelope, and must report the observed
points on the discrete frontier.

## Separate correctness fix

The IVF-Flat check exposed one runner defect before producing Recall:
Faiss represents missing top-k slots as `id=-1, distance=FLT_MAX` when a
probed list contains fewer than 100 vectors. The runner previously accepted
only `id=-1, distance=+infinity`. The normalization now canonicalizes the
standard Faiss representation to `-1/+infinity`, rejects other invalid
negative IDs or distances, and has a deterministic unit regression. This
fix does not change any populated result or Recall hit.

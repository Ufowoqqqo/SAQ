# SymphonyQG Estimator Extraction and Stronger Local Baseline

## Purpose

The previous graph-frontier diagnostic compared SAQ staged estimates against a
weak global-centered 1-bit proxy. That proxy was useful as a first novelty gate,
but it was not close enough to SymphonyQG's graph estimator to support a
research claim.

This note records a stronger local baseline extracted from SymphonyQG source
code. The goal is still diagnostic:

```text
Does SAQ retain a local graph-expansion rank-recovery advantage after replacing
the weak global proxy with a vertex-centered SymphonyQG/RaBitQ-style estimator?
```

This is not yet a full SymphonyQG integration.

## Source Review

The reference source is the local SymphonyQG clone:

- path: `/rwproject/kdd-db/kluaq/SymphonyQG`
- source commit: `6124ddb34ee4d176edea1bd7ad38d1672343df28`
- repository state during review: clean tracked files, with local untracked
  `.venv/` and `baseline_results/`

The relevant implementation points are:

- `symqglib/qg/qg.hpp`: `QuantizedGraph::update_qg` stores, for each current
  vertex, codes and factors for its outgoing neighbors.
- `symqglib/qg/qg.hpp`: `QuantizedGraph::scan_neighbors` computes the exact
  distance from the query to the current vertex, then uses quantized neighbor
  codes to rank the outgoing neighbors.
- `symqglib/quantization/rabitq.hpp`: `rabitq_codes` subtracts the current
  vertex from each neighbor after rotation, binarizes the residual signs, and
  computes `triple_x`, `factor_dq`, and `factor_vq`.
- `symqglib/qg/qg_query.hpp` and `symqglib/utils/scalar_quantize.hpp`: the query
  is rotated, scalar-quantized with `QG_BQUERY = 6`, and converted into a
  FastScan lookup table.
- `symqglib/qg/qg_scanner.hpp`: FastScan produces a signed query-code dot
  product and applies the approximate distance formula.

## Extracted Formula

For a current graph vertex `c`, one outgoing neighbor `x`, and query `q`,
SymphonyQG stores a 1-bit code for the rotated residual:

```text
r = x - c
s_i = +1 if r_i > 0, otherwise -1
```

Ignoring packed layout, the factor computation is:

```text
fac_norm  = 1 / sqrt(D)
fac_x0    = <r, s * fac_norm> / ||r||
fac_x1    = <c, s * fac_norm>
x_x0      = ||r|| / fac_x0
triple_x  = ||r||^2 + 2 * x_x0 * fac_x1
factor_dq = -2 * x_x0 * fac_norm
factor_vq = factor_dq * sum_i s_i
```

The query is scalar-quantized with 6 bits:

```text
width = (max(q) - min(q)) / (2^6 - 1)
q_code_i = round((q_i - min(q)) / width + 0.5)
```

FastScan computes a signed dot product equivalent to:

```text
dot_code = sum_i s_i * q_code_i
```

The extracted local distance estimate is:

```text
dist(q, x | c) =
    ||q - c||^2
  + triple_x
  + factor_dq * width * dot_code
  + factor_vq * min(q)
```

This preserves SymphonyQG's current-vertex residual centering and factor-based
neighbor scoring, which are the important differences from the old global
1-bit proxy.

## Implementation in This Branch

The extracted proxy is implemented in `src/profile_graph_frontier.cpp` as
`SymphonyQGVertexProxy`.

It is used only by the offline graph-frontier profiler:

- it scores each exact-kNN replay edge as `symqg_vertex_proxy`;
- it is reported next to `rabitq_style_proxy`, `saq_fast`, `saq_full`, and SAQ
  prefix refinements;
- it does not change the SAQ index, query path, or stored code format.

Important omissions are intentional and must be kept visible:

- no FHT rotation from SymphonyQG is reproduced;
- no padded power-of-two dimension is used in the extracted proxy;
- no packed FastScan layout or SIMD lookup table is reproduced;
- the graph is still an exact-kNN replay graph, not a SymphonyQG-built graph;
- the measurement uses held-out queries only for evaluation, not for training or
  selecting a method.

Therefore, `symqg_vertex_proxy` is a stronger formula-level local baseline, not
a complete SymphonyQG system baseline.

## Commands

Build:

```bash
cmake --build build -j
```

Small replay:

```bash
./bin/profile_graph_frontier \
  -dataset=gist_sample50k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -graph_subset=1024 \
  -graph_degree=32 \
  -graph_max_queries=50 \
  -graph_roots_per_query=8 \
  -graph_output_prefix=results/saq/graph_frontier_gist_sample50k_k512_b4_subset1024_symqgvertex
```

Larger replay:

```bash
./bin/profile_graph_frontier \
  -dataset=gist_sample50k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -graph_subset=4096 \
  -graph_degree=32 \
  -graph_max_queries=100 \
  -graph_roots_per_query=8 \
  -graph_output_prefix=results/saq/graph_frontier_gist_sample50k_k512_b4_subset4096_symqgvertex
```

The generated CSV/event/Markdown files under `results/saq/` are ignored local
artifacts.

## Results

### GIST sample50k, K512, B=4, subset 1024

Replay budget:

- events: 400
- graph degree: 32
- average exact best-vs-second margin: `0.0963506`
- average distinct IVF clusters per expansion event: `17.0925`

| estimator | bits/candidate | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
|---|---:|---:|---:|---:|---:|---:|
| `rabitq_style_proxy` | 960 | 0.9000 | 12.9725 | 26 | 0.2850 | 0.4300 |
| `symqg_vertex_proxy` | 960 | 0.8725 | 8.7400 | 20 | 0.3625 | 0.5825 |
| `saq_fast` / `saq_prefix_acc0` | 832 | 0.4375 | 1.9900 | 4 | 0.9125 | 0.9925 |
| `saq_prefix_acc1` | 1472 | 0.1075 | 1.1275 | 2 | 1.0000 | 1.0000 |
| `saq_prefix_acc2` | 2432 | 0.0175 | 1.0175 | 1 | 1.0000 | 1.0000 |
| `saq_full` | 3648 | 0.0000 | 1.0000 | 1 | 1.0000 | 1.0000 |

### GIST sample50k, K512, B=4, subset 4096

Replay budget:

- events: 800
- graph degree: 32
- average exact best-vs-second margin: `0.0887893`
- average distinct IVF clusters per expansion event: `13.6312`

| estimator | bits/candidate | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
|---|---:|---:|---:|---:|---:|---:|
| `rabitq_style_proxy` | 960 | 0.90625 | 12.4812 | 27 | 0.25625 | 0.44625 |
| `symqg_vertex_proxy` | 960 | 0.87625 | 8.2775 | 19 | 0.38250 | 0.61500 |
| `saq_fast` / `saq_prefix_acc0` | 832 | 0.46125 | 2.2575 | 5 | 0.87625 | 0.98125 |
| `saq_prefix_acc1` | 1472 | 0.13750 | 1.1725 | 2 | 0.99750 | 1.00000 |
| `saq_prefix_acc2` | 2432 | 0.02750 | 1.0300 | 1 | 1.00000 | 1.00000 |
| `saq_full` | 3648 | 0.00625 | 1.00625 | 1 | 1.00000 | 1.00000 |

## Interpretation

The stronger local baseline changes the novelty-gate result in the right
direction but does not eliminate the SAQ signal.

Compared with the old global proxy, `symqg_vertex_proxy` is consistently
better:

- subset 1024: p90 exact-best rank improves from 26 to 20;
- subset 4096: p90 exact-best rank improves from 27 to 19;
- top-8 containment improves from 0.4300 to 0.5825 on subset 1024 and from
  0.44625 to 0.61500 on subset 4096.

However, SAQ staged estimates still have a much stronger local expansion-order
curve:

- at 832 bits/candidate, `saq_fast` has p90 rank 4-5 while
  `symqg_vertex_proxy` has p90 rank 19-20;
- at 1472 bits/candidate, `saq_prefix_acc1` has p90 rank 2 and near-complete
  top-4 containment;
- at 2432 bits/candidate, `saq_prefix_acc2` nearly recovers exact local
  ordering.

The result supports one narrower claim:

```text
SAQ's segmented progressive estimates can recover local graph-expansion order
more effectively than a formula-level vertex-centered SymphonyQG/RaBitQ proxy
on this diagnostic GIST replay.
```

It does not yet support a full graph-index method claim.

## Remaining Limitations

First, this is still not a full SymphonyQG baseline. A strict reviewer could
reasonably ask for the actual FHT-rotated, padded, packed FastScan estimator on
a SymphonyQG-built graph.

Second, the diagnostic still uses an IVF-residual-coded SAQ index to score
graph-neighbor candidates. The average expansion event touches many distinct
IVF clusters, so estimator preparation overhead remains a central concern.

Third, the evidence is still GIST sample50k/K512/B=4. It is useful for a
directional decision, but not enough for a paper-level claim.

Fourth, local rank recovery is not the same as end-to-end graph search
throughput. The next positive step must connect this local ordering signal to a
concrete graph traversal policy with measured overhead.

## Decision

Continue only if the next step can either:

1. extract or run a fuller SymphonyQG baseline in the same local expansion
   setting, or
2. propose a SAQ-specific graph traversal mechanism whose overhead is clearly
   bounded and whose advantage is not already explained by SymphonyQG-style
   vertex residual scoring.

If neither is feasible, this evidence should be treated as a limitation note
instead of a main-method foundation.

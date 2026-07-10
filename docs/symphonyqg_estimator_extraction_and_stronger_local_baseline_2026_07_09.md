# SymphonyQG Formula-Level Proxy and Provisional Local Evidence

> **Evidence status (revised 2026-07-10): historical and provisional.** The
> implemented `symqg_vertex_proxy` reproduces part of the estimator formula but
> omits SymphonyQG's random-sign FHT and power-of-two padding. Those omissions
> change rank quality, not only implementation speed. This note must not be
> cited as evidence of a comparative SAQ/SymphonyQG advantage.

## Purpose

The previous graph-frontier diagnostic compared SAQ staged estimates against a
weak global-centered 1-bit proxy. That proxy was useful as a first novelty gate,
but it was not close enough to SymphonyQG's graph estimator to support a
research claim.

This note records a formula-level proxy informed by SymphonyQG source code.
The original diagnostic question was:

```text
Does SAQ retain a local graph-expansion rank-recovery advantage after replacing
the weak global proxy with a vertex-centered SymphonyQG/RaBitQ-style estimator?
```

This is neither a source-aligned SymphonyQG estimator nor a graph-search
integration.

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
SymphonyQG first pads vectors to a power-of-two dimension and applies a shared
random-sign FHT. In that common transformed space, it stores a 1-bit code for
the residual:

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

The formula preserves SymphonyQG's current-vertex residual centering and
factor-based neighbor scoring. The implemented proxy applies it directly in
the original 960-dimensional GIST space, so it does not preserve the official
estimator geometry.

## Implementation in This Branch

The extracted proxy is implemented in `src/profile_graph_frontier.cpp` as
`SymphonyQGVertexProxy`.

It is used only by the offline graph-frontier profiler:

- it scores each exact-kNN replay edge as `symqg_vertex_proxy`;
- it is reported next to `rabitq_style_proxy`, `saq_fast`, `saq_full`, and SAQ
  prefix refinements;
- it does not change the SAQ index, query path, or stored code format.

Important omissions must be kept visible:

- no FHT rotation from SymphonyQG is reproduced;
- no padded power-of-two dimension is used in the extracted proxy;
- no packed FastScan layout or SIMD lookup table is reproduced;
- the graph is still an exact-kNN replay graph, not a SymphonyQG-built graph;
- the measurement uses held-out queries only for evaluation, not for training or
  selecting a method.

Therefore, `symqg_vertex_proxy` is an incomplete formula-level diagnostic, not
a valid SymphonyQG comparison baseline. The profiler also evaluates each
query-root neighbor set independently; it has no frontier heap, visited set,
path-dependent traversal, or SymphonyQG multiple-estimate behavior.

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

| estimator | code_bits_only | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
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

| estimator | code_bits_only | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
|---|---:|---:|---:|---:|---:|---:|
| `rabitq_style_proxy` | 960 | 0.90625 | 12.4812 | 27 | 0.25625 | 0.44625 |
| `symqg_vertex_proxy` | 960 | 0.87625 | 8.2775 | 19 | 0.38250 | 0.61500 |
| `saq_fast` / `saq_prefix_acc0` | 832 | 0.46125 | 2.2575 | 5 | 0.87625 | 0.98125 |
| `saq_prefix_acc1` | 1472 | 0.13750 | 1.1725 | 2 | 0.99750 | 1.00000 |
| `saq_prefix_acc2` | 2432 | 0.02750 | 1.0300 | 1 | 1.00000 | 1.00000 |
| `saq_full` | 3648 | 0.00625 | 1.00625 | 1 | 1.00000 | 1.00000 |

## Historical Interpretation And Correction

The formula-level proxy improved over the older global proxy:

Compared with the old global proxy, `symqg_vertex_proxy` is consistently
better:

- subset 1024: p90 exact-best rank improves from 26 to 20;
- subset 4096: p90 exact-best rank improves from 27 to 19;
- top-8 containment improves from 0.4300 to 0.5825 on subset 1024 and from
  0.44625 to 0.61500 on subset 4096.

In the same incomplete comparison, SAQ staged estimates had a better
local-neighborhood rank curve:

- at 832 code bits per candidate, `saq_fast` has p90 rank 4-5 while
  `symqg_vertex_proxy` has p90 rank 19-20;
- at 1472 code bits per candidate, `saq_prefix_acc1` evaluates the first SAQ
  segment accurately for every candidate and has p90 rank 2;
- at 2432 code bits per candidate, `saq_prefix_acc2` evaluates the first two
  segments accurately for every candidate and nearly recovers exact local
  ordering.

These nominal code-bit counts omit factors, padding, residual-reference
metadata, memory layout, estimator preparation, and runtime. They do not
establish a complete-work advantage.

A review-time scalar reproduction added GIST padding from 960 to 1024
dimensions and random-sign FHT for five fixed seeds. It was not committed as a
durable runner and did not reproduce the official packed FastScan path, but it
is a material warning that the old conclusion may reverse:

| estimator | top-1 disagreement | mean exact-best rank | p90 rank | top-8 containment |
|---|---:|---:|---:|---:|
| current unrotated `symqg_vertex_proxy` | 0.87625 | 8.2775 | 19 | 0.61500 |
| review-time FHT reproduction, seeds 0--4 | 0.2475--0.2975 | 1.4425--1.5600 | 2--3 | 0.99625--1.0000 |
| current `saq_fast` | 0.46125 | 2.2575 | 5 | 0.98125 |

The only supported conclusion is:

```text
The incomplete unrotated proxy is not an adequate SymphonyQG baseline. A
source-aligned implementation is required before deciding whether SAQ has any
local rank-quality advantage.
```

The review-time reproduction is itself provisional and must not be reported as
a validated SymphonyQG result.

## Remaining Limitations

First, this is still not a full SymphonyQG baseline. A strict reviewer could
reasonably ask for the actual FHT-rotated, padded, packed FastScan estimator on
a SymphonyQG-built graph.

Second, the diagnostic still uses an IVF-residual-coded SAQ index to score
graph-neighbor candidates. The average expansion event touches many distinct
IVF clusters, so estimator preparation overhead remains a central concern.

Third, the evidence is still GIST sample50k/K512/B=4. It is useful for a
directional decision, but not enough for a paper-level claim.

Fourth, local rank recovery is not the same as end-to-end graph search. The
current profiler has no traversal state and cannot support a throughput or
path-stability claim.

## Superseding Decision

Follow `docs/saq_graph_direction_research_validity_plan_2026_07_10.md`:

1. complete the correctness prerequisites;
2. implement scalar and packed/FastScan-equivalent source-aligned estimators
   with explicit FHT seed and power-of-two padding;
3. verify parity against pinned SymphonyQG source;
4. rerun the local replay over the fixed seed schedule and apply the documented
   stop condition.

Do not design a traversal policy or broaden the dataset matrix unless this gate
passes.

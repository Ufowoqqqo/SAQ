# SAQ Graph Frontier Real-Data Falsification

> **Evidence status (revised 2026-07-10): historical and provisional.** This
> experiment compares SAQ with an intentionally weak, unrotated
> `rabitq_style_proxy`. It does not compare with a source-aligned SymphonyQG
> estimator and does not execute graph traversal. The tables remain as a record
> of the initial diagnostic, not as evidence that SAQ outperforms RaBitQ or
> SymphonyQG.

## Purpose

This note records the first real-data run of `bin/profile_graph_frontier`.
The goal is not to claim a graph-index method yet. The goal is to test the
related-work novelty gate:

```text
Does SAQ's segmented progressive estimator provide a local graph-expansion
rank-recovery or work-reduction signal beyond a one-stage RaBitQ/SymphonyQG-
style proxy?
```

## Input Preparation

The run uses real GIST vectors, but a diagnostic subset rather than the full
official GIST setting:

- source base: `/rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs`
- source query: `/rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs`
- local dataset: `data/gist_sample50k`
- base vectors: first 50,000 GIST base vectors
- queries: all 1,000 GIST query vectors
- PCA: deterministic covariance eigendecomposition on the 50,000 base vectors
- IVF: deterministic NumPy mini-batch k-means, `K=512`, seed `17`, 12 passes
- SAQ: `B=4`, PCA enabled, default segmentation and CAQ adjustment

The generated `data/gist_sample50k` and `results/saq` files are ignored local
artifacts. The durable evidence is summarized here.

The constructed SAQ plan is:

```text
0->64 (64d 11b) | 64->256 (192d 6b) | 256->576 (320d 4b) |
576->832 (256d 2b) | 832->960 (128d 0b)
```

This is the desired kind of diagnostic plan shape: multi-segment, high-bit head,
low-bit middle/tail, and zero-tail.

## Commands

Index build:

```bash
./bin/create_index \
  -dataset=gist_sample50k \
  -K=512 \
  -B=4 \
  -enable_PCA=true \
  -num_threads=16
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
  -graph_output_prefix=results/saq/graph_frontier_gist_sample50k_k512_b4_subset1024
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
  -graph_output_prefix=results/saq/graph_frontier_gist_sample50k_k512_b4_subset4096
```

## Results

### Subset 1024

Replay budget:

- events: 400
- degree: 32
- average exact best-vs-second margin: `0.0963506`
- average distinct IVF residual clusters per expansion event: `17.0925`

| estimator | code_bits_only | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
|---|---:|---:|---:|---:|---:|---:|
| `rabitq_style_proxy` | 960 | 0.9000 | 12.9725 | 26 | 0.2850 | 0.4300 |
| `saq_var` | 0 | 0.9850 | 17.1875 | 29 | 0.1050 | 0.2150 |
| `saq_fast` / `saq_prefix_acc0` | 832 | 0.4375 | 1.9900 | 4 | 0.9125 | 0.9925 |
| `saq_prefix_acc1` | 1472 | 0.1075 | 1.1275 | 2 | 1.0000 | 1.0000 |
| `saq_prefix_acc2` | 2432 | 0.0175 | 1.0175 | 1 | 1.0000 | 1.0000 |
| `saq_full` | 3648 | 0.0000 | 1.0000 | 1 | 1.0000 | 1.0000 |

### Subset 4096

Replay budget:

- events: 800
- degree: 32
- average exact best-vs-second margin: `0.0887893`
- average distinct IVF residual clusters per expansion event: `13.6312`

| estimator | code_bits_only | top-1 disagreement | mean rank | p90 rank | top-4 containment | top-8 containment |
|---|---:|---:|---:|---:|---:|---:|
| `rabitq_style_proxy` | 960 | 0.90625 | 12.4812 | 27 | 0.25625 | 0.44625 |
| `saq_var` | 0 | 0.97500 | 17.6700 | 29 | 0.11000 | 0.20250 |
| `saq_fast` / `saq_prefix_acc0` | 832 | 0.46125 | 2.2575 | 5 | 0.87625 | 0.98125 |
| `saq_prefix_acc1` | 1472 | 0.13750 | 1.1725 | 2 | 0.99750 | 1.00000 |
| `saq_prefix_acc2` | 2432 | 0.02750 | 1.0300 | 1 | 1.00000 | 1.00000 |
| `saq_full` | 3648 | 0.00625 | 1.00625 | 1 | 1.00000 | 1.00000 |

## Interpretation

This historical diagnostic rejected the narrow hypothesis that the unrotated
global proxy would match SAQ's local-neighborhood ordering. It did not pass the
graph direction's SymphonyQG novelty gate.

The main signal is not that full SAQ can score graph candidates. The useful
signal was that SAQ's staged estimator gave a better independent-neighborhood
rank curve than the one-stage `rabitq_style_proxy` at comparable or moderately
higher nominal code-bit counts:

- at 832 code bits per candidate, `saq_fast` has p90 exact-best rank 4-5,
  while the 960-bit proxy has p90 rank 26-27;
- at 1472 code bits per candidate, evaluating the first SAQ segment accurately
  for every candidate moves p90 rank to 2 and gives almost complete top-4
  containment;
- at 2432 code bits per candidate, evaluating the first two SAQ segments
  accurately for every candidate nearly recovers exact local-neighborhood
  order.

These counts omit factors, residual-reference metadata, padding, memory
layout, estimator preparation, and runtime. They therefore cannot establish a
work advantage.

This suggests a plausible SAQ-specific graph question:

```text
Could a graph traversal use SAQ segment stages to recover stable frontier
decisions with less complete work than a source-aligned graph-quantization
baseline?
```

The present experiment does not answer this question. It evaluates fixed
neighbor sets independently and has no frontier heap, visited set,
path-dependent expansion, or multiple-estimate behavior.

## Limitations

This run is not sufficient for a paper claim.

First, `rabitq_style_proxy` is a simple centered 1-bit direction proxy. It is a
novelty-gate baseline, not SymphonyQG and not a faithful RaBitQ graph
implementation. A strict reviewer would not accept this as the final competing
baseline.

Second, the dataset is real GIST but only a 50k sampled diagnostic setting with
K512 IVF metadata. The result should be checked on a larger GIST artifact and
at least one additional high-dimensional dataset.

Third, the average expansion event touches many IVF residual-reference
clusters: about 13.6-17.1 distinct clusters out of 32 neighbors. This supports
the earlier concern that IVF-residual-coded SAQ is not naturally graph-local.
Any graph method must account for cluster-reference metadata and estimator
preparation overhead.

Fourth, `saq_var` is not useful in this setting. The useful curve begins at the
1-bit fast code and improves through prefix-accurate segment refinement.

## Superseding Decision

The original continuation decision is superseded by
`docs/saq_graph_direction_research_validity_plan_2026_07_10.md`. Complete the
correctness prerequisites, implement a source-aligned SymphonyQG estimator
with FHT and power-of-two padding, and rerun the same local replay over the
predeclared rotation seeds. Stop using local rank recovery as the graph
direction's foundation if that baseline matches or dominates SAQ after
complete work accounting.

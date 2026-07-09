# SymphonyQG Small GIST Baseline

## Purpose

This note records the first local SymphonyQG baseline setup and a small GIST
sanity run. The goal is only to confirm that the official SymphonyQG source can
be built and queried locally before using it as a stronger graph-quantization
baseline for SAQ.

## Source And Environment

Source code:

```text
/rwproject/kdd-db/kluaq/SymphonyQG
```

Repository:

```text
https://github.com/gouyt13/SymphonyQG.git
```

Checked revision:

```text
6124ddb
```

The source was cloned outside the SAQ repository so that third-party code does
not pollute this branch. The CMake example builds successfully and produces:

```text
/rwproject/kdd-db/kluaq/SymphonyQG/bin/indexing
```

The Python binding was installed into an isolated virtual environment:

```text
/rwproject/kdd-db/kluaq/SymphonyQG/.venv
```

Installation steps:

```bash
python -m venv /rwproject/kdd-db/kluaq/SymphonyQG/.venv
/rwproject/kdd-db/kluaq/SymphonyQG/.venv/bin/python -m pip install --upgrade pip setuptools wheel
/rwproject/kdd-db/kluaq/SymphonyQG/.venv/bin/python -m pip install numpy==1.26.4 pybind11==2.13.1
cd /rwproject/kdd-db/kluaq/SymphonyQG/python
/rwproject/kdd-db/kluaq/SymphonyQG/.venv/bin/python -m pip install --no-build-isolation .
```

One API detail matters: the binding argument is `num_thread`, not
`num_threads`.

## Run Setting

This is a small sanity baseline, not a paper-level reproduction.

- base source: `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_base.fvecs`
- query source: `/rwproject/kdd-db/kluaq/saq/data/gist_sample50k/gist_sample50k_query.fvecs`
- base vectors: first 10,000 GIST vectors
- queries: first 100 GIST queries
- dimension: 960
- metric: L2
- top-k: 10
- graph degree bound: 32
- build EF: 100
- build iterations: 2
- build threads: 16
- ground truth: exact L2 top-10 within this 10k subset, computed locally

Output files in the SymphonyQG repository:

```text
/rwproject/kdd-db/kluaq/SymphonyQG/baseline_results/gist_sample10k_degree32_top10.csv
/rwproject/kdd-db/kluaq/SymphonyQG/baseline_results/gist_sample10k_degree32_top10.md
```

## Result

Build time:

```text
0.578106 s
```

| search EF | Recall@10 | QPS | query time (s) |
|---:|---:|---:|---:|
| 20 | 0.891 | 37173.659 | 0.002690 |
| 40 | 0.960 | 29269.393 | 0.003417 |
| 80 | 0.983 | 20404.281 | 0.004901 |
| 120 | 0.994 | 16214.257 | 0.006167 |
| 200 | 0.997 | 10358.608 | 0.009654 |

## Interpretation

The baseline source is locally usable. SymphonyQG builds an index and gives a
normal recall/QPS curve on a small real GIST subset.

This run should not be compared directly against the SAQ local expansion-order
profiler. It measures end-to-end SymphonyQG search recall on a 10k graph, while
the SAQ profiler measures local neighbor-order recovery on a fixed adjacency
replay. The immediate value is practical: we can now inspect or reuse the
official implementation when strengthening the weak `rabitq_style_proxy`.

## Next Use

The next research step is to use SymphonyQG as a stronger reference point for
the SAQ graph direction in one of two ways:

1. Extract the graph/RaBitQ estimator behavior needed for the same local
   expansion-order replay.
2. Run an end-to-end SymphonyQG search baseline on the same sampled GIST scale
   and keep the comparison clearly separated from the SAQ local replay.

The first option is more aligned with the current novelty gate, because it asks
whether SAQ's segmented progressive estimator offers a frontier-refinement
advantage beyond the existing RaBitQ-style graph estimator.

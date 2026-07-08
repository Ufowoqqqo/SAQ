# Cluster Residual Plan Feasibility Study

Date: 2026-07-08

## Research Question

SAQ learns one global PCA-variance segment plan and applies it to all IVF
clusters. The structural follow-up asks whether this one-global-plan assumption
is mismatched to local residual distributions inside IVF cells.

This first study is deliberately offline. It does not build an index, does not
change the index format, and does not use held-out query labels.

## Implemented Tool

The new driver is:

```text
script/cluster_residual_plan_feasibility.py
```

It reads base vectors, centroids, cluster ids, and optional global variance
artifacts. It then computes per-cluster residual risk profiles from:

```text
r = x - centroid(cluster_id)
```

For each bit budget, it compares:

```text
P_global:       SAQ-style DP plan from global variance
P_local_oracle: SAQ-style DP plan from each cluster's residual profile
P_shared:       a small family of shared plans learned from residual profiles
```

The reported ratios are weighted by sampled cluster size:

```text
weighted_ratio = sum_c count_c * cost(v_c, plan_c)
                 / sum_c count_c * cost(v_c, P_global)
```

Lower is better. The cost function is the same SAQ-style variance proxy:

```text
cost(segment, bits) = variance_sum(segment) / 2^bits
```

with `bits = 0` interpreted as full residual risk for that segment.

## Outputs

For an output prefix `OUT`, the driver writes:

```text
OUT.md
OUT.summary.json
OUT.plans.csv
OUT.clusters.csv
```

The Markdown and JSON files summarize the study. The plan CSV records the
global plan, the local-oracle aggregate, and each shared plan family. The
cluster CSV records per-cluster counts, costs, local-oracle plans, and the
first shared-family assignment.

## Smoke Validation

A synthetic 4-cluster dataset was generated under `/tmp/saq_cluster_smoke`.
Each cluster had high residual variance in a different 64-dimensional block.
The tool produced:

```text
global plan: 256:4
local-oracle weighted cost ratio: 0.270726
M=2 shared plans best ratio: 0.521137
M=4 shared plans best ratio: 0.270726
```

This is the expected behavior: when each cluster has a different local residual
profile, one global plan is poor, and enough shared plans recover the local
oracle.

Validation commands:

```bash
python -m py_compile script/cluster_residual_plan_feasibility.py
python script/cluster_residual_plan_feasibility.py \
  --data-dir /tmp/saq_cluster_smoke \
  --dataset toy \
  --k 4 \
  --avg-bits 4 \
  --max-vectors 0 \
  --shared-plan-counts 2,4 \
  --output-prefix /tmp/saq_cluster_smoke/report/toy_B4
```

## Real-Data Run Template

Run the study on a prepared PCA/IVF dataset with a bounded sample first, so
the direction can be rejected before changing the index format:

```bash
python script/cluster_residual_plan_feasibility.py \
  --data-dir /path/to/prepared/gist_or_cifar \
  --dataset DATASET \
  --k 4096 \
  --avg-bits 4 \
  --max-vectors 100000 \
  --shared-plan-counts 2,4,8 \
  --output-prefix /tmp/saq-run/structural/cluster_residual_DATASET_K4096_B4
```

Continue toward real index implementation only if:

```text
local-oracle residual plans reduce weighted residual DP cost noticeably
small shared families retain much of that gain
plan shapes are interpretable
metadata overhead is plausibly small
```

Stop or pivot if the local-oracle gain is small, or if the gain requires too
many shared plans to be practical.

## First Real-Data Pass: GIST Sample100k, K512, B4

The first real-data run used prepared GIST PCA/IVF artifacts under
`/tmp/saq-run/data/gist_sample100k`:

```bash
python script/cluster_residual_plan_feasibility.py \
  --data-dir /tmp/saq-run/data/gist_sample100k \
  --dataset gist_sample100k \
  --k 512 \
  --avg-bits 4 \
  --max-vectors 0 \
  --shared-plan-counts 2,4,8 \
  --output-prefix /tmp/saq-run/structural/gist_sample100k_K512_B4_cluster_residual
```

The run covered 100000 vectors and 511 active IVF clusters. The global
SAQ-style plan from global PCA variance was:

```text
64:11,192:6,320:4,256:2,128:0
```

The local-oracle residual plans reduced the weighted residual DP cost ratio to
`0.951051`, a roughly 4.9% reduction relative to the global plan under the same
variance proxy. Small shared plan families retained most of this proxy gain:

| shared plans | profile-assigned ratio | best-of-family ratio | active groups |
|---:|---:|---:|---:|
| 2 | 0.959536 | 0.957189 | 2 |
| 4 | 0.957834 | 0.951087 | 4 |
| 8 | 0.957697 | 0.951079 | 8 |

This is a positive feasibility signal for Direction 1, but it is not yet an
end-to-end search result. It only says that IVF-local residual profiles contain
enough structure for a small shared-plan family to improve SAQ's own offline
variance proxy. The next evidence should test whether the same signal appears
on a larger setting and whether the shared plans are stable enough to justify
one plan id per IVF cluster.

## First Offline Matrix

The same B4 offline study was run on the prepared local artifacts below. All
rows are query-unaware and use only base vectors, PCA-space centroids, cluster
ids, and global PCA variances.

| dataset | K | sampled vectors | global plan | local-oracle ratio | M=2 assigned | M=4 assigned | M=8 assigned | interpretation |
|---|---:|---:|---|---:|---:|---:|---:|---|
| GIST sample100k | 512 | 100000 | `64:11,192:6,320:4,256:2,128:0` | 0.951051 | 0.959536 | 0.957834 | 0.957697 | positive residual-structure signal |
| CIFAR60k | 512 | 60000 | `64:9,192:5,128:3,128:0` | 0.979600 | 0.983263 | 0.983201 | 0.982633 | weak signal |
| DEEP sample100k | 512 | 100000 | `64:6,192:3` | 0.998388 | 1.000000 | 1.000000 | 1.000000 | stop signal for this proxy |
| word2vec sample100k | 512 | 100000 | `320:4` | 1.000000 | 1.000000 | 1.000000 | 1.000000 | no local-plan handle |
| audio | 4096 | 53387 | `192:4` | 1.000000 | 1.000000 | 1.000000 | 1.000000 | no local-plan handle |

The first matrix suggests that cluster residual plan sharing is not a universal
SAQ improvement. It is shape-dependent: multi-segment, nonuniform PCA plans can
leave local residual structure that shared plans may exploit, while compact or
single-segment defaults often leave no meaningful local-plan degree of freedom
under this proxy.

This is useful even before changing the index format. A defensible Direction 1
method should probably start with a data-only eligibility test: continue only
when local-oracle residual plans beat the global plan by a visible margin and a
small shared family preserves most of that gain. Otherwise, abstain rather than
adding plan-id metadata with little expected benefit.

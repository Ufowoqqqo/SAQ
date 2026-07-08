# Cluster Residual Eligibility Matrix

Date: 2026-07-08

## Purpose

This note extends the offline cluster-residual feasibility study from a single
B4 setting to a cross-bit and cross-dataset matrix. The goal is to decide
whether Direction 1 should continue toward an index-format prototype, and under
what data-only conditions it should abstain.

The study remains query-unaware. It uses only base PCA vectors, IVF centroids,
cluster ids, and residual variance profiles. It does not use query vectors,
ground-truth labels, recall, QPS, or index search outputs.

## Assignment Rule

For each dataset and bit budget, the driver builds a small family of shared
plans from residual-profile groups. Each IVF cluster is then assigned to the
shared plan with the lowest offline residual proxy:

```text
assign(c) = argmin_P cost(residual_profile_c, P)
```

This is different from using the original profile-clustering label directly.
The profile-clustering label is only a way to generate a small plan family.
The final assignment is a data-only residual-cost assignment and needs only one
plan id per IVF cluster. It does not use any representative query workload.

## Eligibility Rule

The first conservative rule marks a row as `continue` only when all conditions
below hold:

- the global SAQ plan has at least three segments;
- the cluster-local oracle ratio is at most `0.97`;
- a shared family with `M <= 4` preserves at least 70% of the local-oracle
  proxy gain;
- the proposed metadata is plausibly small: one plan id per IVF cluster plus a
  small shared plan table.

Rows marked `weak-review` have some residual signal but should not trigger
index-format work without additional evidence. Rows marked `abstain` do not
justify local plan metadata under this proxy.

## Matrix

The output files are under:

```text
/tmp/saq-run/structural/cluster_residual_eligibility_matrix_B3_B4_B5.*
```

The command was:

```bash
python script/cluster_residual_feasibility_matrix.py \
  --case name=gist_full_K4096,data_dir=/tmp/saq-run/data/gist_full,dataset=gist_full,k=4096,max_vectors=0 \
  --case name=cifar60k_K512,data_dir=/tmp/saq-run/data/cifar60k,dataset=cifar60k,k=512,max_vectors=0 \
  --case name=deep1M_sample100k_K512,data_dir=/tmp/saq-run/data/deep1M_sample100k,dataset=deep1M_sample100k,k=512,max_vectors=0 \
  --case name=word2vec_sample100k_K512,data_dir=/tmp/saq-run/data/word2vec_sample100k,dataset=word2vec_sample100k,k=512,max_vectors=0 \
  --case name=audio_K4096,data_dir=/tmp/saq-run/data/audio,dataset=audio,k=4096,max_vectors=0 \
  --bits 3,4,5 \
  --shared-plan-counts 2,4,8 \
  --output-prefix /tmp/saq-run/structural/cluster_residual_eligibility_matrix_B3_B4_B5
```

| case | B | global plan | local-oracle | small M | small cost-assigned | small retention | best-any M | decision |
|---|---:|---|---:|---:|---:|---:|---:|---|
| GIST full K4096 | 3 | `64:9,192:5,320:3,192:1,192:0` | 0.958059 | 4 | 0.962729 | 0.889 | 8 | continue |
| GIST full K4096 | 4 | `64:11,192:6,320:4,256:2,128:0` | 0.941956 | 4 | 0.943474 | 0.974 | 8 | continue |
| GIST full K4096 | 5 | `64:11,192:7,320:5,320:3,64:0` | 0.960624 | 4 | 0.963967 | 0.915 | 4 | continue |
| CIFAR60k K512 | 3 | `64:8,128:4,192:2,128:0` | 0.964142 | 2 | 0.965362 | 0.966 | 8 | continue |
| CIFAR60k K512 | 4 | `64:9,192:5,128:3,128:0` | 0.979600 | 2 | 0.983053 | 0.831 | 8 | weak-review |
| CIFAR60k K512 | 5 | `64:10,128:6,256:4,64:0` | 0.943203 | 4 | 0.944139 | 0.984 | 8 | continue |
| DEEP sample100k K512 | 3 | `128:6,128:0` | 0.999661 | 2 | 1.000000 | 0.000 | 2 | abstain |
| DEEP sample100k K512 | 4 | `64:6,192:3` | 0.998388 | 2 | 1.000000 | 0.000 | 2 | abstain |
| DEEP sample100k K512 | 5 | `64:7,192:4` | 0.998209 | 2 | 1.000000 | 0.000 | 2 | abstain |
| word2vec sample100k K512 | 3 | `320:3` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |
| word2vec sample100k K512 | 4 | `320:4` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |
| word2vec sample100k K512 | 5 | `320:5` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |
| audio K4096 | 3 | `192:3` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |
| audio K4096 | 4 | `192:4` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |
| audio K4096 | 5 | `192:5` | 1.000000 | 2 | 1.000000 | 0.000 | 2 | abstain |

## Interpretation

The result is stronger than a GIST-only accident, but still not a universal
claim. The current offline proxy finds reusable local residual structure on
GIST across B3/B4/B5 and on CIFAR at B3/B5. It rejects DEEP, word2vec, and
audio, where the default plans are compact or single-segment and local residual
profiles do not create useful alternative plans.

This supports a shape-conditioned framing:

```text
apply shared local plans only when the global SAQ plan is multi-segment and
the residual-profile matrix predicts visible local-oracle gain that a small
shared family can preserve.
```

The evidence is still offline. A strict reviewer can still object that a lower
variance-proxy cost may not translate into recall or QPS. The next step should
therefore be a minimal index-format prototype only for rows that pass the
eligibility rule, with explicit comparison against SAQ default and with
abstention rows left unchanged.

The first such prototype for GIST full K4096 B4 is recorded in
`docs/gist_shared_plan_end_to_end_2026_07_08.md`. It confirms a small recall
gain but also shows a substantial QPS loss in the naive mixed-plan search path.

## Limitations

- The Python prototype is slow on full GIST K4096 because it evaluates
  per-cluster DP for multiple bit budgets. This is acceptable for a feasibility
  study but should not be presented as production indexing overhead.
- The thresholds `0.97` and 70% retention are conservative heuristic gates, not
  theoretical guarantees.
- The current study evaluates the SAQ variance proxy only. It does not prove
  end-to-end recall, QPS, or memory improvements.
- The positive CIFAR rows are on K512 and should be treated as supporting
  evidence, not yet as a formal large-scale validation.

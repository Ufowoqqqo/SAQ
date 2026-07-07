# Fixed-Policy Input Source And Preparation Provenance

Date: 2026-07-08

This note records the source and preparation chain for the input artifacts in:

```text
docs/saq_fixed_policy_input_manifest_2026_07_08.md
docs/saq_fixed_policy_input_manifest_2026_07_08.json
```

The goal is to explain how the current dataset/PCA/IVF/groundtruth substrate was
prepared before the fixed-policy runner starts. This note does not introduce a
new method and does not run plan search, indexing, recall comparison, or QPS
measurement.

## Scope

The checked manifest has 23 input dependency entries and 20 unique input files.
The current fixed-policy matrix needs:

- `gist_full` K4096: base PCA, query PCA, PCA variance, K4096 IVF centroids,
  K4096 cluster ids, and original-space top100 L2 groundtruth;
- `cifar60k` K512: base PCA, query PCA, PCA variance, K512 IVF centroids,
  K512 cluster ids, and copied L2 groundtruth;
- `deep1M_sample100k` K512: base PCA, query PCA, PCA variance, K512 IVF
  centroids, K512 cluster ids, and sample-specific top100 L2 groundtruth;
- `audio`: only PCA variance for the current abstention/applicability scan;
- `word2vec_sample100k`: only PCA variance for the current
  abstention/applicability scan.

## Evidence Levels

| dataset | current matrix use | provenance status | remaining limitation |
|---|---|---|---|
| `gist_full` | promote/evaluate | command-level provenance for PCA, K4096 IVF, and active top100 GT | exact bitwise PCA reproduction may depend on NumPy/BLAS details |
| `cifar60k` | promote/evaluate | command-level provenance for PCA/K512 IVF and copied official L2 GT | GT depth is only 10, so current metric is R@10 |
| `deep1M_sample100k` | reject/evaluate | command-level provenance for sampled PCA/K512 IVF and top100 GT | prefix-sample pilot, not full DEEP1M |
| `audio` | abstain scan only | source paths and current artifact identity are known | exact historical PCA/IVF command was not found |
| `word2vec_sample100k` | abstain scan only | sampled PCA/K512 IVF provenance is known; active scan needs only variance | exact historical GT command was not found and is irrelevant to current abstention |

## Source Artifacts

The local source directory is:

```text
/rwproject/kdd-db/kluaq/dataset
```

Observed source file identities:

| role | path | shape | sha256 prefix |
|---|---|---:|---|
| GIST base | `/rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs` | 1,000,000 x 960 | `73418110328f5aa5` |
| GIST query | `/rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs` | 1,000 x 960 | `0d1d620049de12da` |
| GIST official L2 GT | `/rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs` | 1,000 x 10 | `97bceb5c45374c2a` |
| CIFAR base | `/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_base.fvecs` | 60,000 x 512 | `a7170faaa80a072c` |
| CIFAR query | `/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_query.fvecs` | 1,000 x 512 | `88109c80b4f4d779` |
| CIFAR L2 GT | `/rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs` | 1,000 x 10 | `28900a95d593c7d7` |
| DEEP base | `/rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_base.fvecs` | 1,000,000 x 256 | `3ae038b1838b0254` |
| DEEP query | `/rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_query.fvecs` | 1,000 x 256 | `2e822dd30816e512` |
| audio base | `/rwproject/kdd-db/kluaq/dataset/audio/audio_base.fvecs` | 53,387 x 192 | `b2fa2c30c0307ebe` |
| audio query | `/rwproject/kdd-db/kluaq/dataset/audio/audio_query.fvecs` | 200 x 192 | `95818137e2a5824c` |
| word2vec base | `/rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_base.fvecs` | 1,000,000 x 300 | `87fa415c6075520a` |
| word2vec query | `/rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_query.fvecs` | 1,000 x 300 | `bc40ee966955ce76` |

## GIST Full K4096

### PCA And Initial K512 IVF

The GIST full PCA substrate was prepared with the local NumPy fallback:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs \
  --groundtruth-input /rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs \
  --output-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --sample-size 1000000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Recorded summary:

```text
summary = /tmp/saq-run/data/gist_full/gist_full_sampled_pca_ivf_summary.json
sample_size = 1,000,000
dimension = 960
K = 512
cluster_dims = 64
iterations = 4
seed = 0
variance_top64_share = 0.7739635705947876
```

This command generated:

```text
/tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_query_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_base_pca.vars.fvecs
/tmp/saq-run/data/gist_full/gist_full_pca_matrix.fvecs
/tmp/saq-run/data/gist_full/gist_full_pca_mean.fvecs
```

The K512 centroids from this command are not part of the current fixed-policy
manifest, because the current GIST matrix uses K4096.

### K4096 IVF

K4096 centroids and cluster ids were then generated from the existing PCA base:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_ivf_from_pca.py \
  --base-pca /tmp/saq-run/data/gist_full/gist_full_base_pca.fvecs \
  --output-dir /tmp/saq-run/data/gist_full \
  --dataset gist_full \
  --k 4096 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 1024 \
  --seed 0
```

Recorded summary:

```text
summary = /tmp/saq-run/data/gist_full/gist_full_k4096_pca_ivf_summary.json
K = 4096
cluster_dims = 64
iterations = 4
chunk_rows = 1024
seed = 0
empty_clusters = 0
cluster_size_min = 1
cluster_size_p50 = 230.0
cluster_size_p90 = 383.5
cluster_size_max = 1059
```

This command generated the current manifest inputs:

```text
/tmp/saq-run/data/gist_full/gist_full_centroid_4096_pca.fvecs
/tmp/saq-run/data/gist_full/gist_full_cluster_id_4096.ivecs
```

### Active Groundtruth

The initial fallback command copied the source GIST L2 GT, but that file has
only top10 depth. The current fixed-policy GIST matrix uses original-space
top100 L2 groundtruth.

The temporary raw mapping still exists:

```text
/tmp/saq-run/data/gist_raw/gist_raw_base.fvecs -> /rwproject/kdd-db/kluaq/dataset/gist/gist_base.fvecs
/tmp/saq-run/data/gist_raw/gist_raw_query.fvecs -> /rwproject/kdd-db/kluaq/dataset/gist/gist_query.fvecs
/tmp/saq-run/data/gist_raw/gist_raw_groundtruth.ivecs -> /rwproject/kdd-db/kluaq/dataset/gist/gist_groundtruth_l2.ivecs
```

Original-space top100 command recorded in the GIST validation note:

```bash
cd /tmp/saq-run
env LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset gist_raw \
  -enable_PCA=false \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=24 \
  -gt_output=/tmp/saq-run/data/gist_full/gist_full_groundtruth_top100_original_l2.ivecs \
  -gt_overwrite=true \
  -logtostderr=1
```

The active manifest GT is the computed original-space top100 file:

```text
/tmp/saq-run/data/gist_full/gist_full_groundtruth.ivecs
```

Pairwise hash check:

```text
gist_full_groundtruth.ivecs == gist_full_groundtruth_top100_original_l2.ivecs
sha256 prefix = 66b6c051102c69f3
shape = 1,000 x 100
```

## CIFAR60K K512

CIFAR uses the same local NumPy fallback:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_query.fvecs \
  --groundtruth-input /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs \
  --output-dir /tmp/saq-run/data/cifar60k \
  --dataset cifar60k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Recorded summary:

```text
summary = /tmp/saq-run/data/cifar60k/cifar60k_sampled_pca_ivf_summary.json
sample_size = 60,000
dimension = 512
K = 512
cluster_dims = 64
iterations = 4
seed = 0
variance_top64_share = 0.7853183150291443
```

The command requested a 100,000-row prefix, but the source dataset has only
60,000 base vectors, so the prepared sample size is 60,000.

This command generated all current CIFAR manifest inputs:

```text
/tmp/saq-run/data/cifar60k/cifar60k_base_pca.fvecs
/tmp/saq-run/data/cifar60k/cifar60k_query_pca.fvecs
/tmp/saq-run/data/cifar60k/cifar60k_base_pca.vars.fvecs
/tmp/saq-run/data/cifar60k/cifar60k_centroid_512_pca.fvecs
/tmp/saq-run/data/cifar60k/cifar60k_cluster_id_512.ivecs
/tmp/saq-run/data/cifar60k/cifar60k_groundtruth.ivecs
```

Pairwise GT hash check:

```text
/tmp/saq-run/data/cifar60k/cifar60k_groundtruth.ivecs
  == /rwproject/kdd-db/kluaq/dataset/cifar60k/cifar60k_groundtruth_l2.ivecs
sha256 prefix = 28900a95d593c7d7
shape = 1,000 x 10
```

Because the available GT depth is 10, current CIFAR claims use R@10 rather than
R@100.

## DEEP1M Sample100K K512

DEEP is a prefix-sampled pilot, not the full DEEP1M setup:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/deep1M/deep1M_query.fvecs \
  --output-dir /tmp/saq-run/data/deep1M_sample100k \
  --dataset deep1M_sample100k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Recorded summary:

```text
summary = /tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_sampled_pca_ivf_summary.json
sample_size = 100,000
dimension = 256
K = 512
cluster_dims = 64
iterations = 4
seed = 0
variance_top64_share = 0.8751857876777649
```

This command generated:

```text
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_base_pca.fvecs
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_query_pca.fvecs
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_base_pca.vars.fvecs
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_centroid_512_pca.fvecs
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_cluster_id_512.ivecs
```

Sample-specific top100 GT was then computed from the prepared PCA-space base and
query files:

```bash
cd /tmp/saq-run
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset deep1M_sample100k \
  -K 512 \
  -B 4 \
  -enable_PCA=true \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=32 \
  -gt_overwrite=true \
  -logtostderr=1
```

Current GT identity:

```text
/tmp/saq-run/data/deep1M_sample100k/deep1M_sample100k_groundtruth.ivecs
shape = 1,000 x 100
sha256 prefix = a0223712006e6e59
```

## Audio

The current fixed-policy matrix does not evaluate audio. It only needs:

```text
/tmp/saq-run/data/audio/audio_base_pca.vars.fvecs
```

for the applicability scan that reports a single-uniform default plan and
abstention.

Known source mapping:

```text
/tmp/saq-run/data/audio/audio_base.fvecs -> /rwproject/kdd-db/kluaq/dataset/audio/audio_base.fvecs
/tmp/saq-run/data/audio/audio_query.fvecs -> /rwproject/kdd-db/kluaq/dataset/audio/audio_query.fvecs
```

Current relevant artifact identity:

```text
/tmp/saq-run/data/audio/audio_base_pca.vars.fvecs
shape = 1 x 192
sha256 prefix = 1d98cd6df677e1c0
mtime = 2026-06-26 12:30 local
```

The exact historical PCA/IVF preparation command for this artifact was not found
in the repository notes. The artifact timestamp coincides with:

```text
audio_base_pca.fvecs
audio_query_pca.fvecs
audio_pca_matrix.fvecs
audio_pca_mean.fvecs
audio_centroid_4096.fvecs
audio_centroid_4096_pca.fvecs
audio_cluster_id_4096.ivecs
```

so it was most likely produced by the original FAISS-based preprocessing path
around `python/ivf.py` and `python/pca.py`, not by the later NumPy fallback.
This is sufficient for current abstention reproduction because the manifest
records the exact variance artifact. It is not sufficient for a clean-machine
audio evaluation claim.

## Word2vec Sample100K

The current fixed-policy matrix does not evaluate word2vec either. It only needs:

```text
/tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_base_pca.vars.fvecs
```

for the applicability scan that reports a single-uniform default plan and
abstention.

The sampled PCA/K512 IVF artifacts were prepared with:

```bash
python /rwproject/kdd-db/kluaq/saq/script/prepare_sampled_pca_ivf.py \
  --input /rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_base.fvecs \
  --query-input /rwproject/kdd-db/kluaq/dataset/word2vec/word2vec_query.fvecs \
  --output-dir /tmp/saq-run/data/word2vec_sample100k \
  --dataset word2vec_sample100k \
  --sample-size 100000 \
  --k 512 \
  --cluster-dims 64 \
  --iterations 4 \
  --chunk-rows 2048 \
  --seed 0
```

Recorded summary:

```text
summary = /tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_sampled_pca_ivf_summary.json
sample_size = 100,000
dimension = 300
K = 512
cluster_dims = 64
iterations = 4
seed = 0
variance_top64_share = 0.44055676460266113
```

This command generated the current manifest input:

```text
/tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_base_pca.vars.fvecs
shape = 1 x 300
sha256 prefix = 4e505e8f5f542bda
```

The local directory also contains a sample-specific top100 GT:

```text
/tmp/saq-run/data/word2vec_sample100k/word2vec_sample100k_groundtruth.ivecs
shape = 1,000 x 100
sha256 prefix = 0a51aa4618eedf7b
```

However, the exact historical command that produced this GT was not found in
the repository notes. An equivalent reconstruction path, if word2vec evaluation
becomes relevant, is to compute top100 L2 over the full-dimensional PCA files:

```bash
cd /tmp/saq-run
LD_LIBRARY_PATH=/tmp/saq-deps/usr/lib64 \
  /rwproject/kdd-db/kluaq/saq/bin/compute_gt \
  -dataset word2vec_sample100k \
  -K 512 \
  -B 4 \
  -enable_PCA=true \
  -searcher_dist_type=0 \
  -gt_topk=100 \
  -gt_threads=32 \
  -gt_overwrite=true \
  -logtostderr=1
```

This GT is not part of the current fixed-policy input manifest because the
current word2vec row abstains before scorer/evaluation.

## Reproducibility Interpretation

The provenance chain now separates three levels:

1. File identity is covered by the full-SHA256 input manifest.
2. GIST, CIFAR, and DEEP have command-level preparation provenance sufficient to
   recreate the current experimental substrate, modulo numerical-library
   details.
3. Audio and word2vec are currently abstention-only rows. Their variance inputs
   are identified by hash, but audio lacks exact historical preprocessing
   commands and word2vec lacks the exact historical GT command.

For a meeting claim, this is enough to explain the current matrix honestly:
positive/reject evaluated rows have a documented input-generation chain, while
abstention rows require only variance artifacts for the current policy decision.

For a paper-quality artifact release, the remaining work is to turn these notes
into a one-command preparation script or to archive the prepared input bundle
with the manifest hashes.

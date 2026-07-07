# Fixed-Policy Input Artifact Provenance Manifest

Date: 2026-07-08

This manifest records the required dataset/PCA/IVF input artifacts for the current fixed-policy validation matrix. It does not run plan search, indexing, recall comparison, or QPS measurement.

## Generation Command

```bash
python script/write_fixed_policy_input_manifest.py \
  --root /tmp/saq-run \
  --date 2026_07_08_runner_cost_reduced_eval \
  --artifact-date 2026_07_08_runner_cost_reduced_eval \
  --use-cost-reduced-scorer \
  --hash-mode full \
  --output-json docs/saq_fixed_policy_input_manifest_2026_07_08.json \
  --output-md docs/saq_fixed_policy_input_manifest_2026_07_08.md
```

## Summary

| field | value |
|---|---:|
| input artifact entries | 23 |
| unique input files | 20 |
| present unique input files | 20 |
| missing unique input files | 0 |
| total input size | 3.822 GiB |
| xvecs shape errors | 0 |

## Hash Semantics

The checked-in manifest was generated with full-file SHA256. Matching hashes are therefore file-content identity checks for the listed input artifacts.

## Unique Input Files

| artifact | roles | kind | shape | size MiB | hash prefix |
|---|---|---|---:|---:|---|
| `data/audio/audio_base_pca.vars.fvecs` | audio:PCA variance for scan | fvecs | 1 x 192 | 0.001 | `1d98cd6df677e1c0` |
| `data/cifar60k/cifar60k_base_pca.fvecs` | cifar60k K512:base PCA vectors | fvecs | 60000 x 512 | 117.416 | `2019cfa391c5d107` |
| `data/cifar60k/cifar60k_base_pca.vars.fvecs` | cifar60k:PCA variance for scan; cifar60k K512:PCA variance | fvecs | 1 x 512 | 0.002 | `8ec4a1399e012c8d` |
| `data/cifar60k/cifar60k_centroid_512_pca.fvecs` | cifar60k K512:IVF centroids | fvecs | 512 x 512 | 1.002 | `ad4498c3b67a1ab5` |
| `data/cifar60k/cifar60k_cluster_id_512.ivecs` | cifar60k K512:IVF cluster ids | ivecs | 60000 x 1 | 0.458 | `3168f05171f74afb` |
| `data/cifar60k/cifar60k_groundtruth.ivecs` | cifar60k K512:groundtruth | ivecs | 1000 x 10 | 0.042 | `28900a95d593c7d7` |
| `data/cifar60k/cifar60k_query_pca.fvecs` | cifar60k K512:query PCA vectors | fvecs | 1000 x 512 | 1.957 | `42a9a3b5461af5ec` |
| `data/deep1M_sample100k/deep1M_sample100k_base_pca.fvecs` | deep1M_sample100k K512:base PCA vectors | fvecs | 100000 x 256 | 98.038 | `e0aedad8e11b2f65` |
| `data/deep1M_sample100k/deep1M_sample100k_base_pca.vars.fvecs` | deep1M_sample100k:PCA variance for scan; deep1M_sample100k K512:PCA variance | fvecs | 1 x 256 | 0.001 | `f301c030f4cef159` |
| `data/deep1M_sample100k/deep1M_sample100k_centroid_512_pca.fvecs` | deep1M_sample100k K512:IVF centroids | fvecs | 512 x 256 | 0.502 | `9c46c49c28d358bb` |
| `data/deep1M_sample100k/deep1M_sample100k_cluster_id_512.ivecs` | deep1M_sample100k K512:IVF cluster ids | ivecs | 100000 x 1 | 0.763 | `e8e29d06a6df29d1` |
| `data/deep1M_sample100k/deep1M_sample100k_groundtruth.ivecs` | deep1M_sample100k K512:groundtruth | ivecs | 1000 x 100 | 0.385 | `a0223712006e6e59` |
| `data/deep1M_sample100k/deep1M_sample100k_query_pca.fvecs` | deep1M_sample100k K512:query PCA vectors | fvecs | 1000 x 256 | 0.980 | `efcb5ef8a536f426` |
| `data/gist_full/gist_full_base_pca.fvecs` | gist_full K4096:base PCA vectors | fvecs | 1000000 x 960 | 3665.924 | `b632e8f0bea1b726` |
| `data/gist_full/gist_full_base_pca.vars.fvecs` | gist_full:PCA variance for scan; gist_full K4096:PCA variance | fvecs | 1 x 960 | 0.004 | `b2088ae0b5814766` |
| `data/gist_full/gist_full_centroid_4096_pca.fvecs` | gist_full K4096:IVF centroids | fvecs | 4096 x 960 | 15.016 | `0c5cce61a854169b` |
| `data/gist_full/gist_full_cluster_id_4096.ivecs` | gist_full K4096:IVF cluster ids | ivecs | 1000000 x 1 | 7.629 | `2e2a4d629b0d220a` |
| `data/gist_full/gist_full_groundtruth.ivecs` | gist_full K4096:groundtruth | ivecs | 1000 x 100 | 0.385 | `66b6c051102c69f3` |
| `data/gist_full/gist_full_query_pca.fvecs` | gist_full K4096:query PCA vectors | fvecs | 1000 x 960 | 3.666 | `12c4bc47996de957` |
| `data/word2vec_sample100k/word2vec_sample100k_base_pca.vars.fvecs` | word2vec_sample100k:PCA variance for scan | fvecs | 1 x 300 | 0.001 | `4e505e8f5f542bda` |

## Interpretation

The manifest turns the fixed-policy input substrate into an explicit, checkable contract. A future reproduction should first match these input files, then allow the runner to regenerate candidate, scorer, index, compare, QPS, and report artifacts.

## Limitations

This manifest identifies current input files; it does not explain how the files were originally prepared from raw datasets, PCA training, IVF training, or groundtruth generation commands.
The xvecs shape check reads the first dimension header and verifies file size divisibility. It does not scan every row dimension unless a future script version adds a stronger verifier.

# Fixed-Policy Input Preparation And Verification Driver

Date: 2026-07-08

This note records the executable driver that turns the fixed-policy input
provenance notes into a command-level workflow.

Driver:

```text
script/prepare_fixed_policy_inputs.py
```

The driver does not change the fixed-policy method and does not run plan search,
indexing, recall comparison, or QPS measurement. It only handles the input
substrate before the fixed-policy matrix runner starts.

## Modes

### Verify Existing Inputs

Default mode is verification against the checked-in full-SHA256 manifest:

```bash
python script/prepare_fixed_policy_inputs.py --verify-only
```

The command reads:

```text
docs/saq_fixed_policy_input_manifest_2026_07_08.json
```

and checks each selected input file for:

- existence;
- size;
- xvecs kind, row count, and dimension;
- full SHA256 unless `--skip-hash` is supplied.

Current local verification:

```bash
python script/prepare_fixed_policy_inputs.py \
  --verify-only \
  --output-json /tmp/saq-run/reports/fixed_policy_input_verify_2026_07_08.json
```

Result:

```text
matched=20
missing=0
mismatch=0
total=20
```

### Dry Run Preparation Commands

Dry-run mode prints the preparation steps without executing them:

```bash
python script/prepare_fixed_policy_inputs.py --dry-run
```

Dataset-scoped examples:

```bash
python script/prepare_fixed_policy_inputs.py --dry-run --dataset cifar60k
python script/prepare_fixed_policy_inputs.py --dry-run --dataset deep1M_sample100k
python script/prepare_fixed_policy_inputs.py --dry-run --dataset gist_full
python script/prepare_fixed_policy_inputs.py --dry-run --dataset audio
```

The audio dry run is intentionally unsupported for clean preparation because
the exact historical PCA/IVF command was not recovered. Current audio evidence
uses only the manifest-matching variance artifact for abstention.

### Prepare Selected Inputs

Preparation is explicit and dataset-scoped. This avoids accidentally launching
large GIST preparation.

Supported preparation targets:

```text
gist_full
cifar60k
deep1M_sample100k
word2vec_sample100k
```

Examples:

```bash
python script/prepare_fixed_policy_inputs.py --prepare --dataset cifar60k
python script/prepare_fixed_policy_inputs.py --prepare --dataset deep1M_sample100k
python script/prepare_fixed_policy_inputs.py --prepare --dataset word2vec_sample100k
```

GIST full is marked large and requires an explicit guard:

```bash
python script/prepare_fixed_policy_inputs.py \
  --prepare \
  --dataset gist_full \
  --allow-large
```

Preparing all supported datasets also requires an explicit guard:

```bash
python script/prepare_fixed_policy_inputs.py \
  --prepare \
  --dataset all \
  --prepare-all-supported \
  --allow-large
```

The driver runs verification after preparation, so a successful preparation run
ends by matching the manifest for the selected dataset.

## Dataset Coverage

| dataset | verify | dry-run | prepare | limitation |
|---|---:|---:|---:|---|
| `gist_full` | yes | yes | yes, with `--allow-large` | large; NumPy fallback rather than FAISS official preprocessing |
| `cifar60k` | yes | yes | yes | GT depth is 10, so CIFAR claims use R@10 |
| `deep1M_sample100k` | yes | yes | yes | prefix-sample pilot, not full DEEP1M |
| `audio` | yes | yes | no | exact historical PCA/IVF command was not recovered |
| `word2vec_sample100k` | yes | yes | yes | current matrix only uses variance artifact for abstention |

## Interpretation

The reproducibility state is now executable at two levels:

1. Existing prepared inputs can be checked by one command against the manifest.
2. GIST, CIFAR, DEEP, and word2vec preparation commands can be printed or
   executed from the same driver.

The remaining gap is not the absence of a driver. It is that audio clean
preparation still requires either the exact historical preprocessing command or
an archived manifest-matching input bundle. For a paper artifact, the driver
should also be tested on a clean experiment root rather than only against the
current `/tmp/saq-run` root.

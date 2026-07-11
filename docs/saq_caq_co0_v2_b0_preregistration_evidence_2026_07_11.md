# CO-0 v2 B0 Preregistration Evidence

Date: 2026-07-11
Stage: V2-B0
Decision: PASS

## Scope And Non-Execution Statement

V2-B0 froze the base-only limitation screen without executing any encoder,
corrected oracle, estimator, or statistical comparison. It did not open base
vectors, centroids, variance vectors, benchmark queries, ground truth,
serialized indexes, or prior encoder outputs.

The only current data-derived bytes read were two one-column IVF assignment
files required to construct the preregistered inventories. Their SHA-256
values matched pre-existing provenance before parsing.

## Frozen Documents

- Input/provenance contract:
  `docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`.
- Structural preparation semantics:
  `docs/saq_caq_co0_v2_b0_preparation_spec_2026_07_11.md`.
- Final preregistration:
  `docs/saq_caq_co0_v2_b0_final_preregistration_2026_07_11.md`.
- Fixed 24-hypothesis family:
  `docs/saq_caq_co0_v2_b0_hypotheses_2026_07_11.json`.
- Inventories and rotation hashes:
  `docs/saq_caq_co0_v2_b0_artifacts_2026_07_11/`.

## Input Provenance

Expected float-artifact hashes were copied before current byte access from:

1. GIST's pre-existing current-PCA view manifest, SHA-256
   `77caab078561dc58e3324ce41c4b3ce849db9bd6fa54e632346cfd8b1b972255`;
2. CIFAR's committed fixed-policy input manifest at commit
   `e5829744106f01467691887eada0166d56893d1f`, Git blob
   `74ab55dcf6172bba8020dd19ba3922c8612438f4`.

These remain expected hashes. B1 must read and verify base, centroids, and
variance bytes before encoding; B0 does not claim current-byte verification
for them.

The two structural assignment checks passed:

| Dataset | Rows | K | Assignment SHA-256 | Min/max population |
|---|---:|---:|---|---:|
| GIST sample50k | 50,000 | 512 | `c466b5685dd4ef12f42f1d7fa304f42b2c9989df12190c84b8bb4c0a29618eb1` | 1 / 474 |
| CIFAR60k | 60,000 | 512 | `3168f05171f74afb175c50a0ec9e584b0f666b157fbedba6d3841cc2e43107e9` | 1 / 324 |

Neither assignment has an empty cell.

## Inventory Result

The generator used exact largest-remainder allocation and the frozen SHA-256
ordering. Results are:

| Dataset | Samples | Covered cells | Pairs | Odd unpaired vectors |
|---|---:|---:|---:|---:|
| GIST sample50k | 50,000 | 512 | 24,842 | 316 |
| CIFAR60k | 50,000 | 512 | 24,884 | 232 |

Thus B1 has exactly 100,000 sampled vectors and 49,726 disjoint within-cell
pairs. GIST selects the complete base; hashing still fixes within-cell order
and pairing. CIFAR selects its registered 50,000-vector subset.

The complete compressed and canonical-uncompressed hashes are recorded in
`inventory_manifest.json`. Running the generator into a separate directory
with independently regenerated rotations produced a byte-identical directory
and the same manifest SHA-256:

```text
38a24135876be6952208e2b9aaaaa6855843780c4bd96eb406a1f6a5e71d7952
```

## Rotation Result

The production-source-equivalent generator created 27 matrices:

```text
GIST:  3 seeds x (4 segmented + 1 whole) = 15
CIFAR: 3 seeds x (3 segmented + 1 whole) = 12
```

Logical seeds `{0,1,2}` map to C seeds `{1,2,3}`. Within every frozen
dataset/scope/dimension, all three hashes are distinct. Same-seed GIST/CIFAR
leading `D=64` and following `D=192` matrices intentionally match across
datasets because both dataset scopes reset the same C RNG stream; this is
predeclared and is not a duplicate-seed failure.

Two independent Release generations were byte-identical. ASAN/debug generation
also matched Release byte for byte and reported no sanitizer error. Raw matrix
files remain generated artifacts under `/tmp`; all 27 expected hashes are
committed in `inventory_manifest.json`.

## Frozen Statistical Family

The machine-readable ledger contains exactly:

| Hypothesis class | Count |
|---|---:|
| Leading-segment materiality | 4 |
| SAQ segment amplification | 18 |
| Unchanged-estimator materiality | 2 |
| **Holm family** | **24** |

The resampling unit, 10,000 replicate count, PCG64 seed `20260711`, one-sided
p-value definition, confidence bounds, zero-denominator rule, same-vector
validity intersections, sensitivity rows, and unchanged gate are frozen in
the preregistration. No output has been used to choose them.

## Verification Commands

```bash
python -m py_compile script/prepare_caq_co0_v2_b0_inventories.py

cmake --build /tmp/saq-v2-oracle-release-build --parallel
/tmp/saq-v2-oracle-release-build/caq_co0_v2_b0_rotation_inventory \
  /tmp/saq-caq-co0-v2-b0-rotations-a

python script/prepare_caq_co0_v2_b0_inventories.py \
  --input-spec docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json \
  --rotation-dir /tmp/saq-caq-co0-v2-b0-rotations-a \
  --output-dir docs/saq_caq_co0_v2_b0_artifacts_2026_07_11
```

The commands were repeated with independently generated `rotations-b` and a
separate inventory output directory; `diff -qr` returned no difference.
ASAN used `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1`.

The full repository build remains unavailable in this environment because the
root CMake configuration cannot locate glog, fmt, or gflags packages. The
dependency-isolated CMake project compiled the B0 generator with the committed
Eigen headers.

## Limitations And Boundary

1. GIST float-artifact provenance originates in a prior local manifest rather
   than a manifest committed on its original branch. Its source-manifest hash
   and filtered artifact metadata are now committed; B1 byte verification is
   mandatory.
2. Rotation bytes are compiler/Eigen/libc dependent. The hashes and build
   environment are frozen; a mismatch stops B1 rather than silently changing
   rotations.
3. The B1 runner and summarizer do not yet exist. Their implementation must be
   synthetic-tested and reviewed against this preregistration before any base
   vector is opened.
4. B0 establishes experimental integrity only. It provides no evidence that
   finite-round CAQ has regret or that any limitation is SAQ-specific.

V2-B0 passes. V2-B1 remains unauthorized. The next permissible work is a
synthetic-only implementation/review of the frozen B1 runner; real base-only
execution requires a later explicit authorization and must not occur in the
same step as this preregistration.

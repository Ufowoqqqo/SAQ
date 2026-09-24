# Read-only implementation review

Reviewed the supplied `no_rotation.py`, `opportunity_reference.py`,
`export_panels.cpp`, and `run_remote.sh` directly from
`no_rotation_experiment_20260924.zip`. No experiment or test was run for this
review, and no supplied source file was edited.

## Findings before execution

No blocking algorithm or interface defect was identified. This is a source
review, not a claim that compilation, data validation, parity checks, or the
experiment has completed successfully.

The reference file is semantically identical to
`research/correlated_pair_allocation/opportunity.py` at Git commit
`35f38aa7ae668a4734d7a08a9bcf73aa00da9a75`, but is not byte-identical: the ZIP
copy contains one additional final LF, after the original final newline.
There are no other differences.

| Reference | Bytes | SHA-256 |
| --- | ---: | --- |
| Git commit file | 21,692 | `ad414716510a38af9ade5e3014c2342f933e812066e7f445837fbfca82c7ce9b` |
| Supplied ZIP file | 21,693 | `0e42ae203eadf0ea890c47d57839bc0a31b253944f9b49cfa97328a541cf9cd3` |

The execution decision is to preserve the supplied ZIP source and its hash,
and explicitly record semantic equivalence rather than claim byte equality.

## Scientific implementation checks

- **Fit-only decisions:** The segment plan uses PCA variances from the fit
  fold. Within each segment, adaptive widths use nearest-lattice SSE curves
  from the fit residuals. Held-out rows supply only evaluation metrics and do
  not select segments, widths, rotations, or thresholds.
- **Matched 2×2 comparison:** IDENTITY/QR × UNIFORM/ADAPTIVE shares each
  dataset/fold's segment boundaries, input rows, original segment widths,
  encoder settings, and factor allowance. Each adaptive segment preserves
  the exact uniform payload. The main loop checks each arm's actual payload
  against the common plan; zero-bit tails incur identical omitted energy.
- **Identity path:** The segment residual slice reaches the allocator and
  encoder directly. There is no additional centering, local PCA, coordinate
  reordering, or random rotation. The upstream full-dimensional PCA and
  nlist=1024 residualization remain in place.
- **QR path:** Rotation is deterministic for each segment boundary under the
  fixed Gaussian-QR seed. The runner records the matrix hash and checks
  orthogonality and preservation of evaluation-vector norm.
- **Measured reconstruction loss:** Let N=||x||², I=<x,q>, and Q=||q||² for
  the actually selected, six-round-adjusted lattice direction q. The code
  explicitly reconstructs q·N/I, whose squared error is
  N·(NQ/I²−1)=||x||²tan²(theta). The independent algebraic expression is
  checked against the explicit reconstruction. This is not the least-squares
  rescaling I/Q. Zero vectors are handled explicitly; nonzero vectors with
  degenerate quantized directions fail instead of yielding an accepted score.
- **Export parity:** The exporter loads archived full-dimensional PCA and
  nlist=1024 coarse models, reads only the fixed base-row indices, and performs
  no training. It uses the same 16,384-row transform batch as the rebuild,
  compares every exported residual head against the archived 128-dimensional
  panel under the stated tolerance, and checks archived selected assignments
  when that file exists. These are runtime checks; passing them is not
  presumed by this review.

## Budget guard and execution boundaries

The outer shell wrapper binds the whole child process tree to one permitted
CPU and sets BLAS/OpenMP thread limits to one. Its 3,600-second wall timeout,
followed by a 15-second kill grace period, bounds cumulative scheduled CPU
well below two CPU-hours, including compilation and hashing. The wrapper
records GNU-time resources outside the result directory. `ulimit -v`
restricts each process's address space to 16 GiB; this is not a measurement of
aggregate simultaneous RSS. Actual resource records must still be inspected.

The script checks repository HEAD, model hashes, official base hashes, and
index hashes before export. It reuses a cached Faiss library and fails if
dependencies are missing; it does not download data, retrain IVF/PCA, push,
commit, or send messages. Invocation through the original wrapper is needed
for its wall, affinity, and environment controls.

## Interpretation boundaries

Adaptive allocation minimizes additive nearest-lattice fit SSE, while the
held-out primary metric uses coupled post-adjustment rescaled SSE. The
allocator is therefore a proxy optimizer, not an oracle for the evaluated
loss; a negative outcome cannot prove general impossibility.

The measured codes and explicit reconstruction belong to a float64 encoder
prototype. Production packed-code parity and float32 factor effects have not
been established. The common 64-bit factor allowance per positive segment
is the inherited planner's matched-vector-budget convention, not a measured
complete deployment footprint. Adaptive width metadata is shared and outside
the vector payload; upstream models, rotation representation, alignment, and
other production storage costs are not established by these byte columns.

The rotation control is one reproducible Gaussian-QR construction, not every
production rotation. The same historical sample indices are reused; the two
cross-fit directions are not independent datasets. This experiment may
support an encoder-loss mechanism observation, but does not by itself
establish Recall/QPS, query-ranking improvement, production suitability, or
novelty.

# Git archive scope — 2026-09-24

The user subsequently requested committing and pushing the completed result.
This supersedes the experiment's earlier no-commit/no-push instruction for
this archival step only. It does not authorize another experiment.

The final scientific result is [REPORT.md](REPORT.md):
`STOP_CURRENT_FORMULATION`, with 48 completed rows. The earlier
`data_aware_minimal_2026_09_23/REPORT.md`, `STATUS.txt`, and recovery notes
are historical checkpoints; their earlier BLOCKED state was resolved by the
authorized input recovery and rebuild.

Git contains the implementation, focused tests, reports, all raw scalar SSE
curves, selected bit allocations, 48 summary rows, 16 comparisons, fit/eval
checks, provenance, commands, hashes and resource logs. Existing experiment
records are preserved as observed, including failed recovery attempts.

Generated datasets and binaries are excluded in accordance with the
repository guidance. They remain under the durable worktree:

`/rwproject/kdd-db/kluaq/worktrees/saq-data-aware-minimal-20260923/`

- `results/data_aware_rebuild_2026_09_23/inputs/gist_learn.fvecs`:
  recovered official GIST learn, full persistent readback SHA verified.
- `results/data_aware_rebuild_2026_09_23/panels/`: both rebuilt residual
  panels, upstream PCA/coarse models and selected assignments.
- `results/data_aware_rebuild_2026_09_23/strong_baselines_v1/models/`:
  12 archives containing fit-only local transforms and scalar codebooks.
- `results/data_aware_minimal_2026_09_23/inputs/*.u64`: frozen row indices.
- Recovery download fragments and compiled executables remain local too.

The SHA-256 records and model archive columns refer to these local files;
a Git clone alone does not contain every referenced binary. They are not
silently replaced with a new representation. Official SIFT learn/base and
GIST base retain their original durable paths in `staged_inputs.tsv`.

Frozen indices can be regenerated without reading data or rerunning the
experiment, from the repository root using the archived NumPy version:

```python
from pathlib import Path
from research.correlated_pair_allocation.diagnostic import sample_indices

output = Path('results/data_aware_minimal_2026_09_23/inputs')
output.mkdir(parents=True, exist_ok=True)
for offset, dataset in enumerate(('sift', 'gist')):
    sample_indices(offset).astype('<u8').tofile(output / f'{dataset}_indices.u64')
```

Verify their SHA-256 identities against `inputs/recovered_indices.tsv` in
the earlier result directory. This document adds archival guidance only;
the recorded experiments and tests were not rerun for this commit.

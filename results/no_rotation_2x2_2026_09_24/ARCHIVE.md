# Git archival scope

The user explicitly requested committing and pushing the completed experiment
after the result report. This archival step does not launch another experiment.

Git contains the original attached source bundle, report, implementation and
result reviews, input/dependency identities, commands, resource logs, all 16
summary rows, four contrasts, allocations, fit curves and rotation hashes.
The attached source files retain their recorded SHA-256 identities.

All 48 per-vector error arrays are also archived as four readable tables in
`measurement/per_vector_text/`. Each table has 8,192 rows; `evaluation_row`
is the zero-based row within that fold's held-out half. The remaining column
names match the NPZ array names exactly. Float64 values were serialized with
round-trippable decimal strings and read back with exact binary-value checks.
This is a format conversion of existing results, not a new experiment.

Generated binary containers, full panels and the compiled exporter remain in
the durable local directory:

`/rwproject/kdd-db/kluaq/worktrees/saq-no-rotation-20260924/results/no_rotation_2x2_2026_09_24/`

- `panels/{sift,gist}/*.fvecs`: full PCA and residual panels.
- `measurement/*_per_vector.npz`: original per-vector array containers.
- `export_panels`: compiled exporter.

The panel hashes in `measurement/input_hashes.tsv` refer to these local
files; a clone alone does not include the input panels or prior upstream
model caches. The preserved run script requires those caches to replay the
experiment. The committed text tables are sufficient to inspect and
recompute the reported scalar comparisons from the measured errors.

The experiment's completion-time statement about not automatically pushing
remains historical. This commit/push is the subsequent user-requested archive.

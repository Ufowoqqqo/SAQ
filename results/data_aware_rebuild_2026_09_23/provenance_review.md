# Final input and provenance review

Date: 2026-09-23. Scope: the user-authorized rebuild and frozen
strong-baselines v1 runner. No blocking methodological issue was found.
This review inspected source, recorded verification, small-file identities,
and artifact sizes; it did not rerun training, tests, or the experiment.

`staged_inputs.tsv` binds the SIFT learn/base and GIST base scratch inputs to
their exact frozen official SHA-256 identities and full expected sizes.
`gist_input_verification.tsv` records the official archive identity
`01469a7f1c3768853525e543d537e2dfa1adece927616405e360952e3f67df73`
and the extracted 500,000-row, 960-dimensional learn identity
`9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17`.
These populated records are the input evidence; `input_hashes.sha256` was
empty at review time and must not be described as the verification source.

Both frozen index files were independently hashed during this review:

- SIFT: `a5ef3954b0d240e9b5fcf59690a559d458b6f05b7c55ca3c0e6bdb648c61a104`.
- GIST: `5cb6868406e6f184abe689058992ab9e8aba52a312c64aa34345a51e7826966d`.

Each durable residual panel is 8,454,144 bytes, exactly 16,384 fvecs rows
of 128 coordinates; each selected-assignment file is 65,536 bytes.
The model-hash records cover both PCA transforms, both 1024-centroid coarse
models, and both residual panels. Both `STAGE_SOURCE.txt` records report
256-row serialization checks with zero PCA difference and matching coarse
assignments. GIST routing uses all 960 transformed coordinates before
residual truncation to 128 dimensions.

The rebuild is explicitly labeled `REBUILT`, with a fixed 16,384-row batch.
It is not a claimed byte reproduction of the deleted historical panels.
Using the original official learn members, frozen base indices, and fixed
training implementation is consistent with the user's subsequent rebuild
authorization. Upstream PCA/coarse fitting uses the separate official learn
member; selected base rows are transformed and assigned without fitting on
them. Within each diagnostic fold, pairings, local PCA, Lloyd codebooks,
and all four allocations use only fit data. Evaluation enters only SSE
measurement. The folds reuse historical selected base rows and are not
independent datasets or a newly untouched test set.

The live runner's diagnostic and strong-baseline source hashes match the
previously reviewed frozen v1 hashes in `independent_review.md`. The prep
source hash matches `code_hashes.sha256`:
`0ad9243f31625f12946cb40202e1eae98484fb29281a5da4c96ca241809f430d`.
The runner checks exact historical index order before consuming each panel
and records the consumed panel and index hashes.

The persistent GIST learn copy's readback hash was still pending when this
review began. Its completion is a handoff/persistence check, not a reason to
invalidate the already verified scratch input used for training. Record its
final status before closing the task; no additional experiment is needed.

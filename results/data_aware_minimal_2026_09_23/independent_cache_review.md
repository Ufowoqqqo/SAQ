# Bounded independent cache inspection

The read-only cache audit agent inspected the fixed evidence commit `ca05b90`
and the original `/tmp` paths, persistent SAQ tree, dataset directory,
resources, worktrees and Hugging Face cache. It found no historical residual
panel or required transform state. The root independently repeated the
filename inventory and SIFT hash check in `cache_audit.py`; its raw output
and measured resource record are retained separately.

The agent additionally inspected directory names to depth 4 under
`/homes/kluaq`, `archive/packages`, `archive/misc`, and `projects`, without
following symlinks or reading session histories, credentials, query/GT, or
ANN index contents. No alternative residual/common cache was found.
`projects/ann/saq` resolves to the inspected archive repository.

The agent and root both verified the official SIFT1M base at
`dataset/sift1m/hf_download/sift_base.fvecs`: 516,000,000 bytes and SHA-256
`21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`.
The shorter `dataset/sift1m/sift_base.fvecs` is not the only available SIFT copy.

The observed archive files are not usable historical substitutes:
`dataset/sift1m/sift.tar.gz` is empty, and `dataset/gist.tar.gz` is
1,825,023,967 bytes versus the historical official archive's 2,740,172,684.
No archive was extracted. Absence conclusions apply to the inspected local
locations; no assertion is made about backups on other hosts.

This is a cache/provenance review, not an independent reproduction of SSE or
an experiment result. No files were edited by the audit agent.

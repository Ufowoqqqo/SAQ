# Pre-experiment independent review

Snapshot: strong-baselines v1, 2026-09-23. Read-only review by cache_audit
after the implementation agent froze these files, before any real outcome.
No blocking or science-changing defect was found.

Verified fit-only pairings, local PCA and Lloyd; U fit-optimal 8-bit groups;
V variance times 2^(-2b); legacy E; free S; shared codebooks; exactly 512-bit
payload; independent constrained scalar DP including deterministic ties;
S fit SSE <= E; 48 fixed rows and 16 predeclared comparisons. Focused tests
also perturb evaluation data and confirm unchanged fitting/allocations.

Reporting limits: local shared-model bytes exclude upstream PCA/coarse.
Pairing effects must compare CORR-S absolute SSE with ADJ-S and EA-S.
The review is not independent experimental reproduction.

SHA-256 at review:

```text
263f0d5363f7a35c4a938915e5f040e46ec49cff5506784f074f7538797a8b38 diagnostic.py
6536c096c7821624f0d4a8c6eb9c6e4f62840502a6171c16af2cd2a618c5b17e strong_baselines.py
638c6b2b80f5ba49d6b4096641828b606b2feb97f57f9ecf18b5cf7858c7b6d4 test_strong_baselines.py
```

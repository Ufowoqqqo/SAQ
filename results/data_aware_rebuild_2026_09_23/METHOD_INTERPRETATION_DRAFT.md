# Method and interpretation notes — draft, no result decision

This note records the frozen interpretation before the diagnostic is run. It
does not assert that both panels are available, that 48 rows exist, or that any
method improves held-out error.

The intended scope is official SIFT1M and GIST1M after the full-dimensional
PCA and nlist=1024 residual transform, restricted to the frozen 16,384 base row
indices and the first 128 residual dimensions. Rebuilt panels must be labelled
as rebuilt inputs. Recovering the historical indices does not establish byte
identity with the missing historical transforms or residual panels. GIST-128
claims apply only to this subspace. Both cross-fit directions share the source
sample and are not independent datasets.

For each pairing and fit fold, all four arms use the same local 2D PCA and the
same trained scalar Lloyd codebooks. U assigns eight bits to every pair and
chooses its internal split from fit SSE; it does not force four bits per axis.
V uses the eigenvalue × 2^(-2b) proxy with the same pair restrictions as E.
E uses empirical SSE with six to ten bits per pair. S removes that pair
restriction while keeping one to nine bits per axis. Every arm has exactly
512 payload bits per vector. Pair selection, transforms, codebooks, and bit
choices are determined entirely from the fit fold.

Two comparisons answer different questions:

- **Allocation and constraints:** CORR-E versus CORR-S isolates the effect of
  restricting pair budgets under the same pairing and transform. S has the
  larger feasible set and must have fit SSE no higher than E; held-out E gains
  would be consistent with a regularization effect and need confirmation.
  CORR-E versus CORR-V compares empirical fit distortion against the fixed
  variance proxy, under the same pair constraints and codebooks.
- **Pairing and local transform:** CORR-S versus ADJ-S and EA-S keeps ordinary
  unrestricted scalar allocation in all arms. Consistent gains here are a
  pairing/local-transform signal. They do not establish an independent gain
  from pair-constrained allocation. The comparison changes both pairing and
  the resulting local PCA, so it does not isolate matching from rotation.

Use absolute held-out SSE per vector for cross-pairing comparisons. The
gain formula is 1 − candidate SSE / comparator SSE, with CORR-E fixed as the
candidate. Gains relative to each pairing's own U have different denominators
and cannot rank pairings. Report all sixteen predeclared candidate comparisons
and the pairing comparisons; do not select another candidate after seeing the
48 result rows.

The continuation rule frozen before observing results is: eligibility requires
all sixteen candidate gains to be at least 5%; park if at least one dataset/fold
has positive gains against all four comparators but global eligibility fails;
otherwise stop the current allocation formulation. A pairing signal may still
be retained when the allocation formulation stops. The 5% threshold is a
practical investment gate, not a significance claim or novelty evidence. Data,
provenance, correctness, or budget failure takes precedence and is a blocker.

Storage columns require explicit scope. The 64-byte payload is per vector.
The reported downstream shared model contains float64 local means and 2×2
bases, the selected scalar codebooks, and uint8 pairing and bit metadata. In
this implementation the transforms use 3,072 bytes, pairing uses 128 bytes,
and bit metadata uses 128 bytes, plus eight bytes per selected codebook entry.
These bytes are **per shared model, not per vector**. Codebook-entry counts
describe possible scalar lookup sizes; no query lookup tables are constructed.

Those downstream model totals **exclude the upstream full-dimensional PCA and
nlist=1024 coarse quantizer**, as well as data panels, training curves, and
container overhead. The NPZ archives include all candidate codebooks and
diagnostic eigenvalues, so archive bytes are not the deployment model total.
Equal payload alone does not establish equal total memory or SAQ-system bytes.

Resource accounting must include failed downloads, interrupted hashes,
compilation, preprocessing, focused checks, and the eventual diagnostic.
Per-pairing computation time is repeated on four arm rows and must not be
summed. A GNU-time wrapper covers its child work; do not additionally add
internal diagnostic timing. Record unknown/unfinalized CPU separately from
the configured 240-second reserve. No current output supports Recall, QPS,
query-ranking, full-GIST, production-consumer, or novelty claims.

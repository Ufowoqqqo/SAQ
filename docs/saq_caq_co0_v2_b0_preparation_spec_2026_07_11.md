# CO-0 v2 B0 Preregistration Preparation Specification

Date: 2026-07-11
Stage: V2-B0
Status: frozen before structural assignment read

## Scope

V2-B0 freezes the later limitation screen; it does not execute it. No CAQ,
LVQ, fixed-point, or corrected-exact encoder may run. No base vector,
centroid, variance value, benchmark query, ground truth, serialized index, or
prior encoder output may be read.

The parent protocol requires B0 to persist sample and pair inventories while
also reserving base/index reads for B1. The only necessary reconciliation is
to hash and parse the two one-column cluster-assignment files. These files
contain integer IVF labels only. All float-vector hashes are imported from
provenance generated before this direction and must be verified against bytes
only after B1 is separately authorized.

The machine-readable input contract is
`docs/saq_caq_co0_v2_b0_input_spec_2026_07_11.json`.

## Inventory Serialization

The protocol identifier is:

```text
saq-caq-co0-v2-b0-20260711-schema1
```

For zero-based cell id `c` and vector id `v`, rank vectors by the raw bytes of

```text
SHA256("protocol_version|dataset_id|c|v")
```

where decimal integers have no leading zeros and the string is UTF-8. A hash
collision is broken by ascending vector id.

Allocate `n=50,000` by exact integer largest-remainder arithmetic. Equal
remainder numerators are broken by ascending cell id. Persist selected vectors
in `(cell_id, rank_in_cell)` order. Pair consecutive selected ranks within a
cell; even rank is the stored side and the following odd rank is the
query-residual side. A final odd item remains unpaired.

Canonical CSV columns are:

```text
sample: dataset_id,cell_id,rank_in_cell,vector_id
pair:   dataset_id,cell_id,pair_rank,stored_vector_id,query_vector_id
```

Files use UTF-8, LF line endings, deterministic gzip with `mtime=0`, and no
embedded source filename. Record SHA-256 for compressed and canonical
uncompressed bytes.

## Rotation Serialization

Logical seeds `{0,1,2}` map to C RNG seeds `{1,2,3}`. This preserves three
distinct streams because glibc aliases streams initialized with `srand(0)` and
`srand(1)`.

For segmented controls, reset the C RNG once per dataset/logical seed and
construct positive-segment rotators in ascending offset order. Default bits
and same-segment uniform `B=4` controls reuse these exact matrices. For the
whole-positive-view control, reset the C RNG independently and construct one
matrix at dimension 832 or 384.

Generation reproduces production `Rotator::orthogonalize()`:

```cpp
FloatRowMat random = FloatRowMat::Random(D, D);
Eigen::HouseholderQR<FloatRowMat> qr(random);
FloatRowMat P = FloatRowMat(qr.householderQ()).transpose();
```

Persist row-major float32 matrices outside Git, commit their SHA-256 hashes,
and require B1 regeneration to match before encoding. Matrix bytes are not a
research output and are not committed.

## Required B0 Outputs

Before B0 can pass, commit:

1. expected base/centroid/variance/assignment hashes and provenance sources;
2. complete sample and disjoint pair inventories plus hashes;
3. every segmented and whole-view rotation hash;
4. code/compiler/platform hashes needed to reproduce the rotations;
5. final encoder arms, controls, metrics, statistical estimands, output schema,
   resource accounting, commands, and unchanged decision rule.

## Stop Rules

Stop B0 without reading vectors if:

- either assignment hash, shape, row count, or cluster range disagrees;
- the deterministic inventory is not byte-identical on regeneration;
- logical seeds produce duplicate rotation hashes within the same
  dataset/scope/dimension;
- rotation regeneration is not byte-identical;
- the final preregistration leaves an arm, estimand, hypothesis, exclusion,
  output field, or resource boundary ambiguous; or
- any step requires inspecting an encoder or estimator result.

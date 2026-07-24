# Structured-2D official query binding

Date: 2026-07-25
Branch: `saq-structured-2d-modeling`
Design: `docs/research/structured_2d_fair_query_evaluation_2026_07_24.md`

## Source

Both objects are the standard ANN_SIFT1M and ANN_GIST1M archives published by
the TexMex corpus at `ftp://ftp.irisa.fr/local/texmex/corpus/`. The GIST
archive is the same object used to extract the already bound learn/base
members. The SIFT archive's learn/base members are byte-identical to the
already bound standalone members.

| Dataset | Archive bytes | Archive SHA-256 |
| --- | ---: | --- |
| SIFT1M `sift.tar.gz` | 168,280,445 | `92f1270c5e3a0cb46b89983e72b0511e4df065c31a9fa0276d8c9b1fca5bc81a` |
| GIST1M `gist.tar.gz` | 2,740,172,684 | `01469a7f1c3768853525e543d537e2dfa1adece927616405e360952e3f67df73` |

## Bound members

| Dataset | Object | Shape | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| SIFT1M | `sift/sift_query.fvecs` | 10,000 × 128 | 5,160,000 | `f7fc9be140accdfd64116c2fa2365ecdb69b8f084970c6b0532db5ff79ac8fdc` |
| SIFT1M | `sift/sift_groundtruth.ivecs` | 10,000 × 100 | 4,040,000 | `2b71de0a8d5a83e6a84eec3e23fb8b611d8801dd9b3a6cd62f070ab65ea65f4f` |
| GIST1M | `gist/gist_query.fvecs` | 1,000 × 960 | 3,844,000 | `0d1d620049de12da455ed7201e97cbab372c4d54d0e6dedbc8c503f62c911299` |
| GIST1M | `gist/gist_groundtruth.ivecs` | 1,000 × 100 | 404,000 | `01f7eda9dc98600c6288f606e55f94f13ae95f8b07d818572260440062d609f6` |

The existing learn/base bindings remain:

| Dataset | Object | SHA-256 |
| --- | --- | --- |
| SIFT1M | learn | `331bc82b6a0e89465776a3ba0c2113e0bd0cceaa014ec3ed639bc8b981af72ea` |
| SIFT1M | base | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| GIST1M | learn | `9b864d69993ffea89f8547c0a1f993727c39152ee040fb48b6de28f5c986ed17` |
| GIST1M | base | `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0` |

## Validation

`structured_2d_bind_query_objects` checked every query coordinate for
finiteness, every row header and file length, every ground-truth ID against
the one-million-row database range, and uniqueness of the 100 IDs within
every ground-truth row.

- SIFT ground-truth observed ID range: `[5, 999998]`;
- GIST ground-truth observed ID range: `[18, 999977]`.

No row was removed or sampled. These identities are frozen before any Recall
or timing output is inspected.

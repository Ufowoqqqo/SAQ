# Attempt 4 A4-1S Implementation and Parity Review

Date: 2026-07-13

Stage: A4-1S committed-parity review

Verdict: **PASS_PARITY**

## Claim boundary

This is an independent review of the synthetic instrument and its committed
parity evidence. It establishes that the frozen exact-scalar, allocation,
representation, and block-control fixtures agree with their declared
independent authorities. It does not establish that the full-shape cost gate
passes, that arbitrary cardinalities help natural residuals, or that ANN
recall, throughput, or SAQ behavior improves.

Real base, centroid, cluster-id, query, ground-truth, index, PCA, `data/`, and
`results/` artifacts were not opened. The review did not rerun a random suite
or the full parity command. It used committed evidence, independently replayed
persisted inputs, deterministic tests, repository/build metadata, and the
current native binary.

## Reviewed commits and provenance

- parent preregistration: `3aa2f6e219763cfe72218050e420766a5a0efbcb`;
- first implementation: `9e65159`;
- corrected implementation: `779c5566c615cad294eaec035b9c5b8da87e647b`;
- parity evidence: `335837ec8a2f8d64fc2a396db54f9bd5a9f87115`.

The first parity attempt from `9e65159` stopped at the deterministic
empty-center block microfixture before the frozen 64-case block RNG suite. Its
parser incorrectly required every converged, nonselected start to have `S`
distinct binary32 centers. That attempt's external files were deleted and
were never committed or used as evidence. The corrected parser applies
distinctness to the best-of-eight winner, independently recomputes that
winner, validates a selected-collision control, and preserves unrelated
`CONTROL_INVALID` states. The correction and regression test are committed in
`779c556`.

`335837e` has exactly one parent, `779c556`, and adds only the six frozen
parity JSON files. The working tree was clean during review, and the remote
branch contained the same evidence commit.

## Artifact and commit binding

All six committed JSON files are byte-for-byte canonical: UTF-8, sorted keys,
compact separators, no nonfinite JSON values, and one terminal LF. Their
common fields agree on:

- schema version `1`;
- protocol `saq-attempt4-a4-1s-20260713-schema1`;
- stage `A4-1S` and status `PASS_PARITY`;
- implementation and execution commit `779c556...`;
- parent preregistration `3aa2f6e...`;
- the exact frozen parity argv and three thread variables set to `1`;
- the three allowed contract inputs and no output-ledger entries.

The artifact index excludes itself and lists exactly the other five files.
Every recorded byte size, SHA-256, schema version, and producer commit matches
the committed file. The index identity is:

```text
size       2465 bytes
sha256     eb7e04e5532aab6d94a91015e37a83b871fe084654b8da3fe7510664f5ab54e3
Git blob   908b71dce46e7be6f6dda2dc1862e58385d0e39a
```

The six external parity outputs also matched the committed bytes during
review. No untracked or provisional output was accepted as evidence.

## Build and implementation review

The build manifest binds 26 relevant source files. Their file identities and
Git blobs match the corrected implementation commit. The compile database has
exactly the seven frozen target translation units:

```text
a4_1s_native.cpp
block_cli.cpp
block_vq.cpp
exact_quantizer.cpp
numeric_runtime.cpp
representation.cpp
representation_cli.cpp
```

Every raw command and tokenized argv contains `-O3`, `-fno-fast-math`,
`-ffp-contract=off`, `-frounding-math`, and `-mfpmath=sse`; no fast-math,
`-march=native`, or forbidden substitute is present. The manifest reports GCC
11.5.0, GMP 6.2.0, MPFR 4.1.0-p9, `FE_TONEAREST`, and unchanged MXCSR with
FTZ/DAZ disabled. The reviewed native binary is 434,192 bytes with SHA-256:

```text
7e6a03bb927080f79e90746f9d8f3c304df14886d95906c68747a5d19f134305
```

The branch-local deterministic suite was rerun independently: all 7 A4-0 and
15 A4-1S tests passed, for 22/22 total. The review did not modify a source,
binary, artifact, or frozen contract.

## Exact scalar parity

The scalar artifact contains exactly 1,044 ordered cases:

```text
780 exhaustive weighted tiny-support cases
8   fixed bit-pattern cases
256 PCG64(20260713) cases
```

All 3,961 persisted solutions were replayed from their stored inputs using the
independent exact-rational reference. Requested/effective cardinalities,
partitions, exact SSE, exact means, binary32 and binary64 rounding,
predecessor diagnostics, and replay counts agreed in every solution. The
artifact-wide exact-equality, replay-equality, and predecessor-monotonicity
flags are all true.

The six entries in `representation_parity.direct_rounding` are the signed
half-min-subnormal, signed three-half-min-subnormal, and signed one-third
fixtures. The two adjacent-normal midpoint witnesses are not missing: they are
explicit scalar bit-pattern cases 786 and 787, with both independent and
native binary32/binary64 results. They exercise the opposite ties-to-even
directions required by the protocol.

## Allocation and representation parity

The structurally independent compiled enumerator executed the full frozen
inventory:

```text
ordered tiny-curve pairs                 608,400
allocation decisions                   2,433,600
independent feasible tuple visits      958,838,400
optimized candidate evaluations       174,002,400
```

The independent and optimized canonical streams both have SHA-256:

```text
041071dfa4e700b7ed036c92291f674e5a532a1b4b0717898427280a2ad95555
```

All 2,433,600 decisions agree. The 64 support-size winners occur in the frozen
capacity/cardinality/support-size order, and their objectives,
cardinalities, used states, exhaustive counts, and optimized counts match.
The same-support-size/different-weight fixture confirms that allocation is not
being selected by a support-size shortcut.

All explicit mixed-radix address, invalid-state infinity, B4/B8 matched
packing, global packing/tail padding, and binary64-before-binary32 lookup
fixtures match. Sixty-two of the 64 bounded support-size records have
`reachable=false`; as frozen in Section 3.3, these deliberately small-H
records review allocation and candidate counts and are not the later
full-shape representation-reachability gate.

## Block-control parity

The block artifact contains exactly 64 cases from the dedicated
`PCG64(20260713)` stream. Every case has the frozen
`N=8+(t mod 25)`, `S=2+(t mod 7)` shape, registered identities, one array
hash, eight starts, and a repeated native run.

For all 64 cases:

- the independent and native start traces agree;
- all starts converge and all native counter checks pass;
- step SSE is monotone and direct-replay assignments agree;
- Cartesian prefill/dominance checks pass;
- best-of-eight uses strict final-SSE comparison with lower start id on ties;
- the selected binary32 codebook is distinct;
- the independent best replay performs exactly seven comparisons; and
- the second native run is bit-identical.

All five named microfixtures pass: lower-codeword assignment tie,
lower-vector-id farthest tie, empty-center retention, Cartesian start before
fill, and lower-start-id best tie.

## Status precedence and findings

All six deterministic precedence cases reproduce the frozen order:

```text
ARTIFACT_INVALID
IMPLEMENTATION_INVALID
CONTROL_INVALID
NO_GO_REPRESENTATION
NO_GO_EXACT_SOLVER_COST
PASS_SYNTHETIC_GATE_ONLY
```

Independent review findings after the committed evidence:

```text
blocker  0
high     0
low      2, documentation-only and closed in this review/TASK update
```

The two low items were the stale TASK status and the need to state explicitly
where the adjacent-normal midpoint fixtures live. Neither changes code or
evidence.

## Decision and next authorized step

The committed parity checkpoint is accepted as **PASS_PARITY**. The maximum
supported claim is that the A4-1S instrument passed its frozen implementation
parity and deterministic block controls.

The next authorized step is only the exact full-shape synthetic
`cost-projection` command from a clean descendant containing this committed
review, with the implementation sources, native binary, compile commands,
contracts, parity files, and parity index unchanged. No cost result exists at
this checkpoint. Real-base access, a natural-data adapter, benchmark queries,
SAQ integration, and ANN claims remain unauthorized.

## Authoritative evidence

- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/build_manifest.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/scalar_exact_parity.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/representation_parity.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/block_vq_parity.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/parity_summary.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/parity_artifact_index.json`.

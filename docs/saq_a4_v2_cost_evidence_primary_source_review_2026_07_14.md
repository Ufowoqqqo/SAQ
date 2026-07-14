# A4 V2 Primary-Source Review: Construction Cost Versus Research Evidence

Date: 2026-07-14

Decision: **GO_PROTOCOL_DESIGN**

Execution authorization: **NONE**

## 1. Question and claim boundary

The predecessor A4-1S gate established that its frozen exact construction-and-
evidence pipeline did not fit its preregistered 24 CPU-hour projection. This
review asks a different question:

> Does primary work support a new protocol whose primary resource-admission
> metric is the cost of constructing the complete four-arm synthetic
> diagnostic instrument, while independently accounting for correctness
> verification and research-only evidence materialization?

This is not a request to reinterpret or rerun A4-1S. It is not evidence that
arbitrary cardinalities help natural residuals, SAQ distance estimation, ANN
recall, throughput, or a systems frontier. It does not make compact evidence,
hashing, replay, exact DP, or cost bookkeeping a research contribution.

The review decision is `GO_PROTOCOL_DESIGN`, not `GO_EXECUTION`. Primary work
supports phase-separated measurement and independently checked compact
results. It does not supply an A4-specific certificate, cost threshold, or
guarantee that the proposed V2 will pass.

## 2. Preserved predecessor result

The authoritative predecessor is
`saq-arbitrary-cardinality-analysis@f1b464b`; cost evidence is at `9ce1052`.
Its result remains:

```text
status                               NO_GO_EXACT_SOLVER_COST
complete scalar-coordinate shards   61 / 128
complete planned shards              61 / 259
timed CPU                            34,805,155,525 us
frozen projection                    5 / 2
projected CPU                        24.170246892361 CPU-hours
ceiling                              24 CPU-hours
```

The status name is historical. The measured quantity was the full frozen
construction/evidence pipeline, not an isolated solver. The component ledger
was:

```text
preflight                                2.060284 s
generation and order                     0.077715 s
scalar bucket                       16,706.810033 s
canonical shard serialization       18,096.207493 s
allocation, block, encoding              0.000000 s
```

The `scalar` bucket itself was not pure solver time. Code review shows that it
also included binary interchange, native-process execution, TSV parsing,
independent exact replay, direct rounding checks, and compact model
construction before the timer switched to `shard_serialization`. The latter
bucket likewise included more than disk I/O: full-record validation, repeated
canonical JSON encodings, subarray hashes, full-record hashes, writing,
flushing, and closing.

The 61 scalar shards contain 15,616 records and 979,749,306 bytes. In the
first coordinate shard, repeated full predecessor rows, exact means,
partitions, and two centroid views account for more than 98% of the bytes.
Those fields were mandatory under the old schema, so the old no-go is valid.
Their size motivates a new scientific question; it does not permit deleting
them retroactively.

## 3. Bounded review method

The machine-readable source ledger is
`docs/saq_a4_v2_primary_source_metadata_2026_07_14.json`.

The search was limited to eleven core primary or official sources in six
categories:

1. SAQ's quantization-efficiency claim and official serialized representation;
2. exact weighted one-dimensional quantization and Monge optimization;
3. certifying computation;
4. ACM/SIGMOD reproducibility requirements;
5. phase-separated benchmarking and disclosure; and
6. ANN build, index, query, and quality accounting.

The review excludes new quantizer variants, datasets, approximate objectives,
post-outcome parameter selection, and a broad survey of reproducibility tools.
The predecessor arbitrary-cardinality novelty review remains authoritative and
is not reopened.

## 4. What the closest sources establish

### 4.1 The defensible target is instrument construction, not deployment

The [SAQ paper](https://arxiv.org/abs/2509.12086v2) makes quantization
efficiency part of its method claim. Its reported quantization time includes
generating and applying the random transform, excludes a separately
composable PCA operation, and compares the work that produces quantized
vectors. It does not define research-review serialization as quantization.

[ANN-Benchmarks](https://arxiv.org/abs/1807.05614) separately reports index
build time, index size, query time, distance work, and result quality. It also
notes that text-protocol parsing may be separated when it would make query
timing unrepresentative. This does not allow production index writes to be
removed: it supports measuring the interface-relevant operation while
reporting framework overhead separately.

The official SAQ source at
[`howarlii/saq@2163ebc`](https://github.com/howarlii/saq/tree/2163ebcedd0ad9c9f4de326e6ca7a860f9eafe52)
shows that a serialized IVF index contains SAQ configuration and segment
metadata, rotations, per-cluster short factors and short/long CAQ codes,
per-vector rescale/error factors and ids, and rotated centroids. Its encoder
and query consumers use a per-vector implicit uniform scalar grid, an MSB
fast-scan layout, the remaining lower-bit code, and `rescale`. The evaluated
V2 baseline is descendant
`Ufowoqqqo/SAQ@bc7829bdffecb17cec369e37c2f50a6c419af039`, which adds only the
positive one-bit packing and padded-lane finite-min correctness fixes relevant
to reliable evaluation. The A4 learned per-group product/block codebooks and
mixed-radix labels have neither a byte-for-byte nor an unchanged-estimator
mapping to that baseline.

The positive A4 equivalence target was frozen before the cost outcome, at
`saq-arbitrary-cardinality-analysis@3aa2f6e219763cfe72218050e420766a5a0efbcb`
(`Freeze A4-1 base-only feasibility protocol`). That contract already states
that a heterogeneous-radix representation needs radix metadata, a new encoder,
and a new scan kernel; that the 128-coordinate panel is not a full-vector ANN
representation; and it fixes product/block labels, B4/B8 packing, reference
decoding and lookup semantics, codebook bytes, invalid addresses, and payload
accounting. The later cost result is `9ce1052`.

Therefore V2 may construct only an **A4-reference-equivalent four-arm
diagnostic bundle**. It must not call that bundle deployed, production,
retained SAQ, current-SAQ-compatible, or an index representation. Its closest
defensible primary figure of merit is **comparative-instrument construction
CPU**: input preparation, exact model fitting, allocation, block training, all
four arms' encoding and packing, and materialization of the compact
intermediate bundle consumed by this diagnostic instrument. A pure
inner-solver timer is too narrow. A timer dominated by verbose research-review
JSON answers a different question.

The bundle contains the candidate and all three attribution/control arms. A
pass is a conservative admission result for the complete future diagnostic;
it is not the recurring cost of one winning arm. Conversely, a failure closes
this exact evaluation instrument on resource grounds; it does not prove that
the candidate alone is unaffordable. This boundary preserves all predecessor
scientific work instead of selecting a cheaper candidate-only timer after the
failure.

### 4.2 Exact DP does not require a permanent verbose execution trace

Wu's [Optimal Quantization by Matrix
Searching](https://doi.org/10.1016/0196-6774(91)90039-2) treats weighted
histogram MSE quantization as a discrete optimization problem and reduces the
classical DP from `O(KN^2)` to `O(KN)` in its arithmetic model.

Grønlund et al.'s [Fast Exact 1D
Clustering](https://arxiv.org/abs/1701.07204) gives the DP recurrence, a
leftmost tie rule, the complete totally monotone matrix used by SMAWK, the
weighted extension, all-`k <= K` computation, and an `O(n)`-space method for
reporting an optimal partition. The algorithm returns optimal costs and a
partition; its complexity does not include permanently expanding every DP
predecessor row, derived mean, rounded view, and repeated replay value into
canonical JSON.

These papers support separating mathematical construction from research
serialization. They do not establish A4's arbitrary-precision bit complexity,
custom at-most-`K` and recursive tie rules, or binary32 collision semantics.
Those remain protocol obligations and must be checked exactly.

### 4.3 Compact evidence is valid only with an independent semantic checker

Blum and Kannan's [Designing Programs that Check Their
Work](https://doi.org/10.1145/200836.200880) defines a program checker as a
separate algorithm that checks a program's output on a given instance. This
supports treating independent checking as a distinct computation rather than
regarding a producer's full execution trace as self-authenticating.

The generic checking results do not prove that A4's chosen partition or hash
is an optimality certificate. A partition proves only feasibility unless
accompanied by a sound lower-bound certificate or an independent exact
recomputation. V2 must therefore use independent exact-rational recomputation
for every scalar/allocation decision plus deterministic bit-level replay for
every block, encoding, and packing decision. This does not claim that Lloyd
training is a mathematically exact optimizer. Sampling may supplement this
replay but cannot replace it.

NIST [FIPS 180-4](https://doi.org/10.6028/NIST.FIPS.180-4) supports SHA-256 as
a stable digest for detecting a change in a message. A hash binds bytes; it
does not prove semantic correctness, execution, provenance, preimage
availability, or checker independence. A4 V2 may use hashes as commitments,
never as the correctness argument by themselves.

### 4.4 Reproducibility does not require every internal state to be archived

The official [ACM artifact
policy](https://www.acm.org/publications/policies/artifact-review-and-badging-current)
requires functional artifacts to be documented, consistent with the paper,
complete for its claims, exercisable, and supported by verification and
validation. It treats same-artifact reproduction by another team as a
separate activity from the original measurement.

The [SIGMOD Availability and Reproducibility
Initiative](https://reproducibility.sigmod.org/) asks for the system or its
specification, build environment, inputs or generators, experiment scripts,
workload, measurement protocol, raw results, and scripts that produce reported
figures. It explicitly describes setup, running, and cleanup phases. It does
not require a JSON expansion of every internal DP state.

The resulting A4 requirement is claim completeness, not maximal redundancy:
another reviewer must be able to recreate the registered result, recompute
every exact decision, diagnose a mismatch, and check the cost ledger without
trusting an opaque producer.

### 4.5 Benchmark rules support named timed work plus disclosed validation

The official [SPEC CPU 2017 run
rules](https://www.spec.org/cpu2017/Docs/runrules.html) distinguish untimed
test/train workloads from the timed reference workload while requiring all
outputs to validate. They require repeat runs, stated conditions of
observation, and disclosure of performance-relevant configuration. They also
state that disclosure need not be massively redundant or include details
irrelevant to reproduction.

Koskela et al.'s [Principles for Automated and Reproducible
Benchmarking](https://doi.org/10.1145/3624062.3624133) presents an explicit
`Code -> Build -> Run -> FOM -> Analysis` workflow, fixed platform
descriptions, component timings, automated validation, and programmable
post-processing.

These are precedents for a named A4 figure of merit plus separate correctness
and evidence ledgers. They are not permission to copy SPEC's repetition rule
or any external threshold. A4 must justify its own claim, phases, and resource
budget before execution.

The inherited A4 projection has one full-shape observation, not SPEC's repeated
timing design. V2 therefore cannot claim a timing distribution or expected
performance. Its protocol must forbid best-of-retries, describe the result as
one frozen-machine observation, and accumulate rather than discard CPU from
any externally interrupted attempt.

## 5. Required non-overlapping cost model

The review supports the following decomposition:

```text
B_build         frozen build and binary materialization
P_parity        pre-run exactness, representation, and block-control fixtures

C_setup         instrument preflight, panel generation, identity, ordering
C_core          exact fitting, allocation, block training, encoding, packing
C_bundle_io     compact four-arm intermediate bundle, flush, close
T_instrument    C_setup + C_core + C_bundle_io

E_emit          compact research-evidence encoding, hashing, flush
V_replay        independent full semantic recomputation and comparison
E_archive_body  timed archive bodies and authority-bearing preimages

T_study_metered B_build + P_parity + T_instrument
                + E_emit + V_replay + E_archive_body

F_trailer       finite final reporting trailer outside T_study_metered
```

Each term must have separate process-family CPU and wall time plus owned
temporary and permanent bytes where applicable. Peak RSS must be reported for
each separately launched process family and for the complete producer; a
subphase may not claim an invented per-phase peak when the operating system
exposes only a cumulative process peak. Metered CPU sums must reconcile
exactly. The final trailer's files, fields, bytes, hashes, and exclusion must
be frozen because its duration cannot be embedded in a file without a timing
self-reference. Work may not vanish merely because it is outside the primary
gate.

The primary V2 admission question should use `T_instrument`, not `C_core`
alone and not `T_study_metered`. This is an inference from the sources and the
intended claim:

- `C_core` alone omits required input and the intermediate bundle;
- `T_instrument` is the complete four-arm diagnostic construction whose
  affordability controls whether this bounded evaluation can proceed; and
- `T_study_metered` measures building, validating, producing, and reviewing
  this study, but is not exact total project cost because the finite reporting
  trailer is explicitly outside it.

The protocol must nevertheless refuse a scientific decision if full
verification or evidence packaging does not complete. It may not claim that
research reproduction is free or that `T_instrument` is method construction,
deployment, or end-to-end SAQ index-build cost.

## 6. Minimally sufficient A4 evidence

The old schema persisted several derivable views for every coordinate and
every requested cardinality. The new protocol may instead retain:

1. one manifest binding source, binary, compiler, numeric state, full command,
   environment, seed, shape, order, and every input;
2. the generated input identity and deterministic regeneration rule;
3. for every coordinate and `K=1..256`, one complete schema-frozen optimum
   record containing effective cardinality, exact objective, partition, exact
   means, and direct binary32/binary64 rounded bits;
4. complete allocation, global-control, block-start trajectory, selected-model,
   encoding, packing, and round-trip records required by the scientific
   decision;
5. the byte-complete A4-reference-equivalent intermediate model/code bundle
   for a full construction, or schema-frozen raw payload preimages for every
   completed encoding unit in an early-stop prefix;
6. one independent verifier transcript covering every scalar curve, every
   allocation, every block start/step, every selected rounded model, and every
   encoded payload;
7. a discrepancy inventory that must be empty for passage;
8. non-overlapping phase timings and complete resource/byte ledgers; and
9. content hashes and a single artifact index binding all produced files.

Full DP predecessor rows, duplicate producer/replay copies, repeated arrays
plus repeated subarray hashes, and identical manifest fragments need not all
be physically expanded. Every optimum record and every block-start trajectory
remains persisted once under a normative schema, while all omitted internal
states remain deterministically recomputable by the independent verifier. If
a future sound compact optimality certificate is not supplied, the verifier
must solve the complete registered exact problem rather than sampling it.

Canonical JSON remains adequate for compact summaries. A new binary or
compressed evidence format would add a new correctness surface and is not
needed to justify the first V2 protocol.

## 7. Strict-reviewer objections and answers

### Objection: this is a post-hoc rescue because serialization caused the loss

Yes, the failed run identified the ambiguity. The response is not to change
its decision. V2 starts on a new branch, preserves the old terminal result,
retains its original shape, exact objective, and the old one-panel numerical
ceiling, and freezes a different figure of merit before any new execution.
The A4 model fields, code payload, decoder, and lookup semantics are inherited
from the pre-outcome `3aa2f6e` contract. V2 also retains the native-child/IPC/
required-parse construction architecture; only the canonical container,
research-detail emission, replay placement, phase instrumentation, and
research-evidence schema are newly frozen. The threshold is now only a
synthetic admission cap: V2 drops the unsupported claim that `5/2` predicts
two real datasets under the new phase boundary.

### Objection: excluding evidence cost hides the real project cost

V2 does not exclude it from reporting. `B_build`, `P_parity`, `V_replay`,
`E_emit`, `E_archive_body`, and `T_study_metered` are mandatory
authority-bearing outputs. Failure to complete them invalidates the result.
They are outside the instrument-construction figure of merit because they
validate or archive the study rather than construct the diagnostic bundle.
The finite `F_trailer` self-reference exclusion is separately disclosed.

### Objection: a hash is not a proof

Agreed. Hashes bind inputs and logical streams. Passage additionally requires
independent exact-rational scalar/allocation recomputation and full
deterministic block/encoding/packing semantic comparison.

### Objection: the revised pipeline may still be unaffordable

Agreed. Allocation, block training, and encoding never ran in the predecessor.
The old `scalar` bucket was not pure construction. No V2 passage can be
inferred from the old profile. The new protocol remains falsifiable.

### Objection: cheaper evidence generation is not a database contribution

Agreed. The review and protocol are methodology. Any later paper claim would
still need a material SAQ-specific opportunity, a strong block-VQ control,
matched storage and query work, and a frozen ANN frontier evaluation.

## 8. Decision

The review returns **GO_PROTOCOL_DESIGN** under these conditions:

- preserve A4-1S as terminal for its own full pipeline;
- use complete four-arm comparative-instrument construction, not inner-solver
  time, as the primary FOM;
- retain `34,560,000,000` CPU microseconds only as an internal one-panel
  admission cap, and make no two-dataset/base affordability projection from
  it;
- report every verification/evidence phase and total cost separately;
- require full independent semantic replay--exact-rational for scalar and
  allocation, deterministic bit-level for block/encoding/packing--not
  hash-only or sampled validation;
- retain intermediate-bundle materialization inside the primary timer;
- keep the same synthetic shape, exact rational objective, tie rules,
  rounding, rates, groups, and block starts unless a future primary-source
  review justifies a different scientific question; and
- stop after a committed and independently reviewed preregistration until the
  user separately authorizes implementation.

This decision supports writing the V2 protocol that accompanies this review.
It authorizes no code or run.

## 9. Primary sources

- Li et al., [SAQ](https://arxiv.org/abs/2509.12086v2), SIGMOD 2026,
  DOI `10.1145/3769824`.
- Wu, [Optimal Quantization by Matrix
  Searching](https://doi.org/10.1016/0196-6774(91)90039-2), 1991.
- Grønlund et al., [Fast Exact 1D
  Clustering](https://arxiv.org/abs/1701.07204), 2017.
- Blum and Kannan, [Designing Programs that Check Their
  Work](https://doi.org/10.1145/200836.200880), JACM 1995.
- ACM, [Artifact Review and
  Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current).
- ACM SIGMOD, [Availability and Reproducibility
  Initiative](https://reproducibility.sigmod.org/).
- Official [SAQ source artifact](https://github.com/howarlii/saq/tree/2163ebcedd0ad9c9f4de326e6ca7a860f9eafe52),
  commit `2163ebc`.
- NIST, [FIPS 180-4](https://doi.org/10.6028/NIST.FIPS.180-4).
- SPEC, [CPU 2017 Run and Reporting
  Rules](https://www.spec.org/cpu2017/Docs/runrules.html).
- Koskela et al., [Principles for Automated and Reproducible
  Benchmarking](https://doi.org/10.1145/3624062.3624133), 2023.
- Aumüller et al.,
  [ANN-Benchmarks](https://arxiv.org/abs/1807.05614), SISAP 2017.

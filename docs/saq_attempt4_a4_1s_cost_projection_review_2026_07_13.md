# Attempt 4 A4-1S Cost Projection Review

Date: 2026-07-14

Stage: A4-1S committed cost-projection review and terminal decision

Verdict: **NO_GO_EXACT_SOLVER_COST**

## Claim boundary

This is an independent review of the committed A4-1S synthetic cost evidence.
It establishes only that the frozen exact construction-and-evidence pipeline
failed its preregistered same-shape CPU-cost gate. It is not evidence about
natural residuals, arbitrary-cardinality prevalence, quantization quality,
SAQ-specific limitations, ANN ranking, recall, throughput, or systems
integration.

The protocol status name is `NO_GO_EXACT_SOLVER_COST`, but more than half of
the measured CPU time was canonical shard serialization. The admissible claim
is therefore about the whole frozen exact A4-1S pipeline, not that the scalar
solver alone requires more than 24 CPU-hours. The margin is narrow and bound
to the recorded machine and toolchain; it does not prove a general exact-DP
complexity lower bound. Nevertheless, the preregistered integer decision rule
failed and cannot be rescued by changing the machine, library, precision,
shape, output discipline, or repetition count.

Real base, centroid, cluster-id, query, ground-truth, index, PCA, `data/`, and
`results/` artifacts were not opened. No natural-data adapter or SAQ path was
implemented or run.

## Reviewed commits and provenance

- parent base-only preregistration: `3aa2f6e219763cfe72218050e420766a5a0efbcb`;
- final A4-1S protocol amendment: `3c0a49f6a9d7de5c394635a8b7e6ac8035affed8`;
- corrected implementation: `779c5566c615cad294eaec035b9c5b8da87e647b`;
- parity evidence: `335837ec8a2f8d64fc2a396db54f9bd5a9f87115`;
- parity review: `988ace00169f413ab66f0b235fac3a8956cb777d`;
- clean cost execution commit: `d0d7057a780495c5d0399cbcea52273ff1619fd7`;
- cost scientific snapshot: `9ce1052`;
- audited branch head during review: `69912bf`.

The cost evidence commit has the clean execution commit as its sole parent and
adds only the four frozen cost wrappers. The later audited-head commit changes
only root `AGENTS.md` to record long-running-job polling guidance. It does not
change a contract, source, binary, parity file, cost artifact, or scientific
snapshot.

The implementation sources, seven frozen native translation units, compile
flags, compiler/runtime metadata, and native binary remain unchanged from the
reviewed parity checkpoint. The native binary is 434,192 bytes with SHA-256:

```text
7e6a03bb927080f79e90746f9d8f3c304df14886d95906c68747a5d19f134305
```

An earlier foreground invocation was deliberately interrupted before a
terminal wrapper could be written because that execution session was not
durable. Its separately retained files are WIP and are neither referenced nor
used as evidence. A detached supervisor was used only for operational
continuity of the fresh evidence-producing run; it did not change the
scientific argv, thread environment, execution commit, or timed-region
accounting. These are non-authority-bearing operational observations.
Admissibility rests on the committed argv/environment/commit bindings and the
content-addressed terminal artifacts, not on the supervisor log.

## Frozen invocation and completion

The admitted command was:

```text
python script/run_arbitrary_cardinality_a4_1s.py cost-projection
  --input-spec docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json
  --hypotheses docs/saq_attempt4_a4_1_base_only_hypotheses_2026_07_13.json
  --output-dir /tmp/saq-attempt4-a4-1s-cost-projection
  --threads 1
```

`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` were each
exactly `1`. As non-authority-bearing operational context, the supervisor
observed the run from approximately 02:52 to 12:33 HKT on 2026-07-14, an exit
code of `0`, and the terminal line:

```text
A4-1S NO_GO_EXACT_SOLVER_COST
```

The ten-entry input ledger contains only the three frozen contracts, six
committed parity artifacts, and the committed parity-review memo. Every path,
size, and SHA-256 matches the committed input. No real-data or provisional
file is present.

## Committed artifact review

The four committed wrappers are byte-for-byte identical to the terminal run:

```text
synthetic_cost_projection_manifest.json
  size    605265 bytes
  sha256  2d217dbca9a713ce1cd5ea68273fc93a35d7bac50d77a303acd4c64e03e2c28c

synthetic_cost_projection_summary.json
  size    609076 bytes
  sha256  1990e320796a97390d8b54a175c183cdd59dd9ca4dc1337bdcdbcdb5c61974f9

synthetic_cost_projection_detail_ledger.json
  size    92170 bytes
  sha256  9063d75123f9a37a1966ba0b669346215ecb41937594d73aed689a9fe8a5a519

cost_projection_artifact_index.json
  size    14980 bytes
  sha256  7e999088a4bd890a54dd067d81e208509c9e1aef3370a5c2a3c43216f4ba2cf3
  Git blob acf1bf8ed7828a92297bf54a953226bd4b96070a
```

All wrappers and the external timed body are canonical schema-1 JSON with the
frozen protocol and stage. The artifact index lists exactly the other three
wrappers and excludes itself. Every indexed size, hash, schema, and producer
commit agrees with the committed bytes.

The external terminal directory contains exactly 66 files: the four wrappers,
61 scalar shards, and one timed output-ledger body. It contains no `.working`,
temporary, partial, or extra file. The 61 normal shards are the strict plan
prefix `0..60`, corresponding to `coordinate_000.jsonl` through
`coordinate_060.jsonl`; the 198-entry missing suffix begins at coordinate 61
and continues without a hole or reordering through the final B8 encoding
shard.

Every completed scalar shard contains exactly 256 canonical, schema-valid
records, for 15,616 records and 979,749,306 shard bytes total. All persisted
sizes and SHA-256 identities match the committed content-addressed ledger. The
timed body is embedded exactly in the committed detail wrapper and has
SHA-256:

```text
bacaca900347e01f4886f385ae3062b00a09e61fd787ac9eb1085ea8aa83c8e3
```

The ordered completed-shard array has SHA-256:

```text
b1f75196dec6782c616c73fa8d8e0f79ba6d545493ac9eb22d57315e35f46365
```

Independent review reconstructed the frozen synthetic-array and ordering
identities and replayed every persisted partition, exact SSE, exact mean,
binary32/binary64 round-to-nearest-even result, array hash, and predecessor
backtrack. It also independently checked `K=1` for every completed coordinate
and exhaustively enumerated all `K=2` split points with the frozen earliest-tie
rule. A separate adversarial review recomputed coordinates `0`, `30`, and `60`
at `K=1`, `128`, and `256`; all 9/9 sampled replays agree. The external shards
are not separate committed evidence; they are accepted only through the
committed full-detail hash ledger that both reviews verified.

## Cost rule and early-stop review

The last complete atomic checkpoint was coordinate 60:

```text
completed shards                       61 / 259
completed scalar coordinates           61 / 128
checkpoint cumulative CPU       34,804,797,856 us
one-panel early-stop ceiling     34,560,000,000 us
checkpoint reason                RUNNING_CPU_LOWER_BOUND_EXCEEDED
```

The timed region then completed the output-ledger body and authority-bearing
end snapshot. Its final integer CPU accounting is:

```text
T                                      34,805,155,525 us
gate left  = 5 * T                    174,025,777,625
gate right = 2 * 86,400,000,000       172,800,000,000
gate pass                              false
projected CPU                          87,012,888,812.5 us
projected CPU-hours                    24.170246892361
registered limit                       24.000000000000 CPU-hours
excess                                 612.8888125 seconds
```

The component CPU counts sum exactly to `T`:

```text
exact scalar construction              16,706.810033 s
canonical shard serialization          18,096.207493 s
preflight                                   2.060284 s
generation and order                        0.077715 s
allocation, block, encoding                 0.000000 s
```

The recorded wall total is 34,866.103830208 seconds. The conservative
process-family peak RSS is 2,318,667,776 bytes, and the deterministic Python
owned-buffer high-water bound is 227,927,662 bytes.

The early stop is protocol-valid: it occurs only after a complete shard was
published, the completed shards are a strict prefix, the timed body itself is
inside the measured region, and only the frozen four-file trailer follows the
end snapshot. The body and wrappers consistently record
`NO_GO_EXACT_SOLVER_COST`, `projection_complete=false`, and `gate_pass=false`.
Artifact, implementation, and control failure states are absent, so the
frozen status precedence is respected.

Because the cost lower bound was already terminal, allocation, block VQ, and
encoding phases did not execute. This result therefore supports no positive
or negative conclusion about those phases or about full-panel representation
reachability.

## Independent findings

The full content/schema/semantic review found:

```text
blocker  0
high     0
low      0
```

The separate adversarial protocol/provenance review found blocker 0, high 0,
and one documentation-only low: `TASK.md` still described cost as pending.
That was the correct conservative state before independent review, does not
affect the artifacts, and is closed in the terminal-decision commit containing
this memo.

The branch-local deterministic suite was rerun before the evidence commit:
all 7 A4-0 and 15 A4-1S tests passed, for 22/22 total. Review did not modify a
source, binary, frozen contract, or scientific artifact.

## Terminal decision and next authorized step

The committed A4-1S cost result is accepted as
**NO_GO_EXACT_SOLVER_COST**. Under the frozen protocol this closes the current
A4-1 formulation. A narrow failure does not authorize a rerun or a precision,
shape, serialization, library, machine, or parameter rescue.

The maximum supported claim is only that the registered exact A4-1S
construction/evidence pipeline did not satisfy its frozen same-shape synthetic
cost ceiling. The earlier A4-0 witness and A4-1S parity result remain valid,
but there is no natural-data, representation-prevalence, block-VQ, ANN,
recall, QPS, or systems result.

`PASS_SYNTHETIC_GATE_ONLY` did not occur. Real-base access must not be
requested or executed. The only authorized follow-up is to commit and report
this terminal review and perform the required Meeting Summary Handoff. No new
scientific experiment is authorized on this formulation.

## Authoritative evidence

- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_manifest.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_summary.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_detail_ledger.json`;
- `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/cost_projection_artifact_index.json`.

# Current Task: independent full-word VQ consumer integration

## Branch and base

- Active branch: `saq-structured-2d-modeling`
- Active-task base: `23290a5`
- Mode: `IMPLEMENT`, followed by the permitted smallest `EXPERIMENT`

The previous unchanged-production-estimator gate is complete and correctly
returned `NO_GO_UNCHANGED_ESTIMATOR_INTEGRATION`. This task does not require S
to remain inside SAQ's bitplane representation. It tests S as an independent
full-word VQ representation while retaining SAQ only as later comparison
context.

## Research question and decision being tested

Can the compact shared-affine S100 model support a real packed candidate
payload and full-word scan loop without losing its one-lookup-per-group
semantics or making compact table construction unaffordable after it is
amortized across candidates?

For one query-like probe, the consumer is:

```text
build 64 K-entry tables
for each candidate:
    decode 64 joint labels from its fixed-size payload
    estimate = sum_g table[g][label[g]]
```

S passes this integration gate only if representation parity holds and both
the median CPU and wall total compact costs at 8,192 candidates are at most
`1.10x` the identical expanded-S consumer in every registered dataset/rate
cell. This is a native prototype gate, not Recall/QPS or a SOTA claim.

## Frozen representation and workloads

- exactly 64 fixed adjacent-coordinate groups;
- B4 uses 16 labels and exactly 32 payload bytes per candidate;
- B8 uses 256 labels and exactly 64 payload bytes per candidate;
- B4 stores the even group in the low nibble and the odd group in the high
  nibble of the same byte;
- B8 stores one label byte per group;
- compact S, expanded S, and independent V all use the same payload rule;
- no invalid labels, variable-length coding, model id, per-cell choice, mixed
  dispatch, or candidate-dependent table;
- candidate counts are exactly `64`, `256`, `1,024`, and `8,192`;
- probes are the existing 64 midpoint-stratified fit rows;
- one untimed warmup and nine measured repetitions, with arm order rotated
  `C/E/V`, `E/V/C`, and `V/C/E`;
- one process, one computational thread, reused allocations, and no logging or
  serialization inside timed regions.

Packing is index-construction work and remains outside the query scan timing.
Decoding, bounds-safe label extraction, lookup, and accumulation are inside
the packed scan timing. Model fitting, expansion, correctness checks, and
output writing remain outside all timed regions.

## Correctness and accounting requirements

For B4 and B8:

- all 64 labels survive pack/unpack exactly;
- payload bytes are exactly 32 or 64;
- compact and expanded S reuse exactly the same packed payload;
- decoded labels remain in `[0,K)`;
- compact and expanded tables satisfy the existing per-entry tolerance;
- compact and expanded scan sums differ by no more than the sum of the actual
  selected-entry tolerances;
- expanded scan equals direct reconstruction-table lookup under the same
  accumulation order;
- every candidate performs exactly 64 lookups;
- C keeps only one K-entry working table per group construction and never
  persists the `64*K` expanded centers;
- persistent model bytes and peak query-table bytes are reported separately
  from candidate payload bytes.

Report packed scan CPU and wall nanoseconds per candidate for every fixed
candidate count, including min/max/median/MAD. Combine the separately measured
table-build and packed-scan medians to report the C/E and C/V total-cost ratios
at each count. The first affordable fixed count is the first count where both
CPU and wall C/E scan ratios and both CPU and wall C/E combined-total ratios
are at most `1.10x`.

The gate passes only if:

- every correctness and accounting check passes;
- packed C/E scan time is at most `1.10x` for both CPU and wall time at 8,192
  candidates in all four dataset/rate cells; and
- combined C/E table-build plus packed-scan time is at most `1.10x` for both
  CPU and wall time at 8,192 candidates in all four cells.

Do not change counts, thresholds, packing order, probes, repetitions, or arm
order after observing results.

## Relevant paths

- `research/structured_2d/{compact,microbench,model}.{hpp,cpp}`
- `research/structured_2d/{model_test,runner}.cpp`
- `research/a4_or_b/{panel,models}.{hpp,cpp}`
- `docs/saq_structured_2d_base_only_result_2026_07_23.md`
- `docs/saq_attempt4_a4_1_base_only_input_spec_2026_07_13.json`

Reuse the existing registered panel construction, S100 fit, D/V controls,
compact and expanded table builders, timing clocks, summary statistics, and
runner. Do not create another benchmark framework or output format when the
existing TSV path can be extended.

## Reads, writes, and forbidden data

Allowed reads:

- relevant repository source, Git metadata, build files, and current-task
  documents;
- the registered GIST PCA base, PCA centroid, and cluster-id inputs;
- the reproduced CIFAR counterparts under
  `/tmp/a4-or-b-cifar-inputs-default/`;
- the two deterministic inventories; and
- outputs newly produced by this worktree.

Allowed writes:

- `TASK.md` and local guidance;
- focused implementation and tests under `research/structured_2d/`;
- the existing structured-2D result note; and
- build and experiment outputs under `/tmp`.

Do not read benchmark queries, ground truth, Recall/QPS results, serialized
indexes, variance files, or unrelated branch outputs. Held-out rows remain
evaluation-only and must not select packing, counts, thresholds, or timing
rules.

Do not modify production `saqlib/`, the SAQ estimator, planner, index format,
or search schedule. Do not introduce a fast-stage claim, query-trained rule,
per-cluster model, plan id, or rescue sweep.

## Commands and budget

```bash
cmake -S research/structured_2d -B /tmp/saq-structured-2d-build \
  -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/saq-structured-2d-build -j2
ctest --test-dir /tmp/saq-structured-2d-build --output-on-failure
/tmp/saq-structured-2d-build/structured_2d_runner ...
git diff --check
git status --short --branch
```

- at most 16 GiB peak RSS;
- at most 2 CPU-hours total;
- one measurement process and one computational thread;
- fixed S100 construction, with S20 retained only as the existing sensitivity
  record;
- no rate, seed, model, count, repetition, or threshold sweep.

## Deliverables and done criteria

Deliver:

- reusable B4/B8 matched-label pack/decode and packed scan functions;
- deterministic adversarial and ordinary roundtrip/scan tests;
- registered C/E/V packed-scan and amortization results for GIST/CIFAR B4/B8;
- exact commands, flags, affinity/thread settings, CPU identity, output paths,
  and hashes; and
- a concise interpretation appended to the existing result note.

Done means Release build/tests pass, the frozen correctness rules and gate are
applied to all four cells without rescue changes, an independent bounded
review has no blocker/high finding, and the result is committed and pushed.

## Current result

All four registered cells pass:

```text
PASS_PACKED_PAYLOAD_PARITY
PASS_PACKED_SCAN_CORRECTNESS
PASS_PACKED_SCAN_AFFORDABILITY_AT_8192
PASS_COMBINED_AFFORDABILITY_AT_8192
```

At 8,192 candidates, C/E combined CPU and wall ratios are respectively:

- GIST B4: `1.0002x`, `1.0001x`;
- GIST B8: `1.0412x`, `1.0412x`;
- CIFAR B4: `1.0007x`, `1.0008x`; and
- CIFAR B8: `1.0375x`, `1.0374x`.

B4 first becomes affordable at 256 candidates on both datasets. B8 first
becomes affordable at 8,192 candidates on both datasets. This is the main
limitation exposed by the gate: the 64 KiB B8 query table is viable only when
its construction is amortized across a large candidate set.

## Current blocker and next action

There is no implementation or native-integration blocker. Benchmark-query
evaluation remains outside this task and has not been run.

After committing and pushing this result, the next scientific action is to
freeze a fair query-evaluation contract for the independent VQ
representation. That changes the active metric and data boundary, so it must
name the comparison systems, matched bit budgets and quality points before
benchmark queries are read.

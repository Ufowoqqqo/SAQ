# SAQ Research Direction Registry

Last reconciled: 2026-07-14

SAQ branch scope: every `origin/*` branch plus `upstream/main`, after
`git fetch --all --prune`. At this snapshot there are 16 unique SAQ branches
and no remote-only research branch. Sibling scope is deliberately narrower:
only `vectordb/main@f51b487` is audited as the external evidence snapshot for
`R10`; this file is not a complete inventory of all vectordb branches.

This is the canonical living registry for SAQ research directions, branch
ownership, scientific state, and meeting-reporting state. A branch is not the
same thing as a direction: one direction may span several branches, and one
branch may contain several related falsification studies.

## 1. Registered Reporting Boundary

The user-confirmed completed-meeting boundary is the original 2026-07-09
deck, frozen at the commit that added it:

```text
deck:
  saq-graph-traversal-analysis@322214f:
    docs/saq_research_progress_meeting_slides_2026_07_09.md
scientific snapshot at deck time:
  saq-graph-traversal-analysis@d94279d
meeting_date:
  2026-07-09
canonical immutable copy on this branch:
  docs/saq_research_progress_meeting_slides_2026_07_09.md
```

The copied Markdown content comes from the blob at `322214f` (with only its
trailing blank line normalized). The same source-branch filename was revised
on 2026-07-10; those later revisions and their post-meeting evidence are
deliberately excluded from this reporting boundary. A direction counts as
reported only when the frozen meeting deck gives it a substantive research
question, evidence/status, decision or claim ceiling, and an authoritative
source snapshot. A bare mention, baseline use, or future-direction sentence
does not count.

The 2026-07-13 files are unpresented drafts, not completed-meeting records:

```text
superseded intermediate draft:
  docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md
  historical source: saq-caq-one-shell-repair@433e8ea
  canonical copy introduced at: saq-meeting-summary@5cdc270
current successor draft:
  docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md
  original summary snapshot: saq-meeting-summary@43835d9
  latest Attempt 4 scientific snapshot:
    saq-arbitrary-cardinality-feasibility-v2@f86a51d
```

The date in these filenames is the draft date. Neither draft has been through
a meeting, so inclusion in either one does not change `UNREPORTED` to
`REPORTED`.

### Reporting-state vocabulary

| State | Exact meaning |
|---|---|
| `REPORTED` | The registered completed-meeting deck substantively covered the listed scientific snapshot. |
| `UNREPORTED` | The registered completed-meeting deck did not substantively cover the direction. This is baseline-relative and does not assert that no informal discussion ever occurred. |
| `UPDATE_PENDING` | A direction was reported, but a newer committed and independently reviewed material milestone is not yet covered by a completed-meeting deck. |
| `NOT_APPLICABLE` | Infrastructure, correctness-base, or summary branch rather than a research direction. |

Coverage detail is recorded separately:

```text
SUBSTANTIVE                 dedicated question, evidence, decision, and source
REFERENCE_ONLY              named only as context, baseline, or closed direction
BASELINE_REFERENCE_ONLY     used as a frozen input for another reported question;
                            the original direction itself is not reported
ABSENT                      not covered
RESERVED_NO_EVIDENCE        explicitly reserved without a result
```

Research-state vocabulary:

| State | Exact meaning |
|---|---|
| `ACTIVE` | Explicitly authorized scientific work remains within the current gate. |
| `AWAITING_AUTHORIZATION` | A reviewed boundary has been reached and no further scientific execution is authorized. |
| `PARKED` | No terminal verdict, but no current authorized work or selected continuation. |
| `CLOSED` | The direction or method line has a terminal stop decision. |

Current-successor coverage vocabulary:

```text
NOT_INCLUDED_SUBSTANTIVELY  no dedicated treatment in the successor deck
CARRIED_FORWARD             already-reported material retained for context
INCLUDED_PENDING_REPORT     substantively drafted but not yet reported
```

## 2. Research Direction Registry

| ID | Meeting label | Direction | Scientific snapshot | Research state | Exact decision / boundary | Reporting state | 2026-07-09 completed-deck coverage | Current successor coverage |
|---|---|---|---|---|---|---|---|---|
| `R01` | 2026-07-09 Attempt 1 | Default-neighborhood fixed policy and boundary-aware local plan selection | `saq-boundary-audit@e582974` | `CLOSED` | stop as main method; retain as diagnostic baseline | `REPORTED` | `SUBSTANTIVE`, slides 12--15 | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R02` | 2026-07-09 Attempt 2 | Mixed shared local residual plans | `saq-structural-followup@b71c699` | `CLOSED` | recall signal lost to mixed-plan query/layout overhead | `REPORTED` | `SUBSTANTIVE`, slides 16--19 | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R03` | 2026-07-09 Attempt 3 | Single-global static segment-cost DP | `saq-global-cost-dp@699d2c9` | `CLOSED` | no lower-cost plan dominated SAQ risk; near-frontier plans were slower | `REPORTED` | `SUBSTANTIVE`, slides 20--23 | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R04` | 2026-07-09 Attempt 4 | Measured `fac_error` planner objective | `saq-planner-objective-analysis@5756412` | `CLOSED` | limitation evidence only; increasing nprobe did not recover default recall before the QPS advantage disappeared | `REPORTED` | `SUBSTANTIVE`, slides 24--28 | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R05` | 2026-07-09 Attempt 5 | Segment ordering, search scheduling, and variance-bound calibration | `saq-planner-objective-analysis@5756412` | `CLOSED` | no safe mechanism removed enough slack | `REPORTED` | `SUBSTANTIVE`, slides 29--33 | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R06` | 2026-07-09 graph pivot | Graph traversal with progressive SAQ prefixes | `saq-graph-traversal-analysis@a03ee40` | `CLOSED` | stopped before Phase 5; grouped complete estimator still cost about `26.8x` SymphonyQG | `UPDATE_PENDING` | `SUBSTANTIVE`, slides 34--42, through `d94279d` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R07` | 2026-07-13 draft Attempt 1A | Full-dimensional PCA/residual-PCA transform replacement | `saq-transform-analysis@3d94840` | `CLOSED` | preregistered CIFAR replication failed | `UNREPORTED` | `ABSENT` | `INCLUDED_PENDING_REPORT`, slides 6--16 |
| `R08` | 2026-07-13 draft Attempt 1B | Physical `D -> d` lossy projection with tail surrogate | `saq-lossy-projection-analysis@051ec6a` | `CLOSED` | LP-0 Gate A failed before projected SAQ build | `UNREPORTED` | `ABSENT` | `INCLUDED_PENDING_REPORT`, slides 17--25 |
| `R09` | historical | Finite-round CAQ exact-gap limitation and low-cost repair | `saq-caq-one-shell-repair@977e7ff` | `CLOSED` | limitation retained; repair `NO_GO_ON_COMPLEXITY`; SAQ-centric incremental line stopped | `UNREPORTED` | `ABSENT` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R10` | 2026-07-13 draft Attempt 2 | Exact-hist shared scalar-codebook DP and outer bit allocation | local evidence `vectordb@f51b487`; prior-art/draft snapshot `saq-caq-one-shell-repair@433e8ea` | `CLOSED` | retain as stronger offline baseline and objective-mismatch evidence, not a method | `UNREPORTED` | `ABSENT` | `INCLUDED_PENDING_REPORT`, slides 26--45 |
| `R11` | 2026-07-13 draft Attempt 3 | Paper-exact `1/Ratio@k` distance-quality re-evaluation | `saq-ratio-metric-analysis@146dc16` | `CLOSED` | `CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE` | `UNREPORTED` | `ABSENT` | `INCLUDED_PENDING_REPORT`, slides 46--58 |
| `R12` | 2026-07-13 draft Attempt 4 | Fixed-rate arbitrary-cardinality mixed-radix scalar-product quantization | `saq-arbitrary-cardinality-feasibility-v2@f86a51d` | `AWAITING_AUTHORIZATION` | preserve terminal A4-1S `NO_GO_EXACT_SOLVER_COST`; A4 V2 is `PROTOCOL_READY_NOT_AUTHORIZED_FOR_EXECUTION`, with no implementation, build, parity, synthetic run, or data access authorized | `UNREPORTED` | `ABSENT` | `INCLUDED_PENDING_REPORT`, slides 59--65 |

### Reported-through ledger

| Direction | Reported through | Report source | Later material update |
|---|---|---|---|
| `R01` | `saq-boundary-audit@e582974` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | none registered |
| `R02` | `saq-structural-followup@b71c699` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | none registered |
| `R03` | `saq-global-cost-dp@699d2c9` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | none registered |
| `R04` | `saq-planner-objective-analysis@5756412` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | none registered |
| `R05` | `saq-planner-objective-analysis@5756412` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | none registered |
| `R06` | `saq-graph-traversal-analysis@d94279d` | `saq-graph-traversal-analysis@322214f:docs/saq_research_progress_meeting_slides_2026_07_09.md` | `saq-graph-traversal-analysis@a03ee40`: source-aligned follow-up, complete-work evidence, and terminal closure |

`R01`--`R05` are fully reported through their current scientific snapshots.
`R06` has a reported 2026-07-09 snapshot but a material post-meeting update,
so it is `UPDATE_PENDING`. `R07`--`R12` are baseline-relative `UNREPORTED`.
The current successor draft queues `R07`, `R08`, `R10`, `R11`, and `R12`;
`R09` remains outside it. Historical backlog is not automatically added to a
future deck.

## 3. Evidence And Claim-Ceiling Ledger

All paths below are relative to the named source snapshot, not necessarily to
this summary branch.

| ID | Strongest evidence and claim ceiling | Authoritative source paths | Successor / next authorized step |
|---|---|---|---|
| `R01` | Multi-dataset ANN evidence supports a bounded query-unaware policy, but handwritten families, empirical scoring, and planning overhead prevent a main-method claim. | `saq-boundary-audit@e582974`: `docs/saq_fixed_policy_meeting_summary_2026_07_08.md`; portfolio disposition in `saq-caq-one-shell-repair@977e7ff`: `docs/saq_caq_limitation_repair_closure_and_project_pivot_2026_07_13.md` | closed; retained only as diagnostic baseline |
| `R02` | GIST R@100 rose from `0.94469` to `0.94548`, while QPS fell to `0.909x`; no deployable mixed-plan method. | `saq-structural-followup@b71c699`: `docs/shared_plan_negative_evidence_and_dp_pivot_2026_07_08.md` | pivoted to `R03`, now closed |
| `R03` | Five-dataset offline matrix and GIST ANN checks found no risk/cost domination; no global cost-DP method. | `saq-global-cost-dp@699d2c9`: `docs/limitation_evidence_and_pivot_2026_07_08.md` | pivoted to `R04`, now closed |
| `R04` | A different plan was 4.7% smaller and `1.34x` faster at fixed nprobe, but increasing nprobe did not recover default recall before the QPS advantage disappeared; limitation evidence only. | `saq-planner-objective-analysis@5756412`: `docs/fac_error_gist_b4_safe_search_2026_07_09.md`, `docs/fac_error_gist_b4_recall_matched_2026_07_09.md`, `docs/saq_pivot_synthesis_graph_index_proposal_2026_07_09.md` | closed |
| `R05` | Fast-stage pruning was material, but variance pruning was only 0.14--0.45%; no safe bound/scheduling mechanism reached the required 58--63% slack reduction. | `saq-planner-objective-analysis@5756412`: `docs/saq_runtime_profile_gist_sample100k_2026_07_09.md`, `docs/saq_variance_bound_inactivity_final_2026_07_09.md`, `docs/saq_pivot_synthesis_graph_index_proposal_2026_07_09.md` | pivoted to `R06`, now closed |
| `R06` | First accurate prefix improved fixed-neighborhood ordering, but complete estimator work was `52.5x`, or `26.8x` after grouping; no full graph integration claim. | `saq-graph-traversal-analysis@a03ee40`: `docs/saq_graph_phase4_complete_work_evidence_2026_07_11.md` | closed before Phase 5 |
| `R07` | GIST estimator signal did not replicate on CIFAR; no universal PCA-optimality claim. | `saq-transform-analysis@3d94840`: `docs/saq_transform_phase1b_external_replication_evidence_2026_07_10.md` | closed |
| `R08` | Favorable exact tail-norm surrogate still ranked worse than native SAQ at the registered GIST point; no projected-SAQ or general projection claim. | `saq-lossy-projection-analysis@051ec6a`: `docs/saq_lossy_projection_lp0_gate_a_evidence_2026_07_11.md` | closed before Gate B |
| `R09` | Registered base-only limitation survived controls, but exact encoding cost `272.9x` and one-shell total cost `4.579x--8.169x` failed the `2.0x` gate; limitation only, no repair method or ANN claim. | `saq-caq-optimality-analysis@9bb7d0c`: `docs/saq_caq_co0a_official_source_parity_2026_07_11.md`; `saq-caq-corrected-oracle-v2@ff360cd`: `docs/saq_caq_co0_v2_b1_registered_evidence_2026_07_12.md`; `saq-caq-one-shell-repair@977e7ff`: `docs/saq_caq_one_shell_synthetic_falsification_2026_07_12.md`, `docs/saq_caq_limitation_repair_closure_and_project_pivot_2026_07_13.md` | method closed; problem-first selection only |
| `R10` | Exact-hist can reduce offline SSE, but the inner exact 1D DP is prior art and recall effects reverse across regimes; stronger baseline, not a method. | `vectordb@f51b487`: `reports/scalar_training_exact_hist_audit_2026_06_30/README.md`, `docs/saq_limitation_transfer_memo_2026_07_02.md`; `saq-caq-one-shell-repair@433e8ea:docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` | closed as method; retained baseline |
| `R11` | One GIST conclusion changes under paper-exact distance quality while DEEP controls remain negative; measurement evidence only. | `saq-ratio-metric-analysis@146dc16`: `docs/saq_attempt3_a3_2_a3_3_decision_2026_07_13.md` | closed |
| `R12` | A4-1S remains a terminal pipeline-cost stop: 61 scalar-coordinate shards used `34,805,155,525 us`, and its frozen `5/2` projection was `24.170246892361` CPU-hours. The new primary-source review supports only a protocol redesign: A4 V2 measures complete four-arm comparative-instrument construction as `T_instrument=C_setup+C_core+C_bundle_io`, keeps build/parity/evidence/replay/archive/memory/bytes separately mandatory, and forbids transferring the old `5/2` projection to real data or SAQ. This is protocol evidence only, not feasibility, natural-data, ANN, or systems evidence. | Old cost evidence `saq-arbitrary-cardinality-analysis@9ce1052`, reviewed terminal snapshot `@f1b464b`: `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_manifest.json`, `docs/saq_attempt4_a4_1s_artifacts_2026_07_13/synthetic_cost_projection_summary.json`, `docs/saq_attempt4_a4_1s_cost_projection_review_2026_07_13.md`. V2 primary review `saq-arbitrary-cardinality-feasibility-v2@c4ccea3` and reviewed protocol snapshot `@f86a51d`: `docs/saq_a4_v2_cost_evidence_primary_source_review_2026_07_14.md`, `docs/saq_a4_v2_cost_evidence_go_no_go_memo_2026_07_14.md`, `docs/saq_a4_v2_synthetic_construction_preregistration_2026_07_14.md`, `docs/saq_a4_v2_synthetic_construction_contract_2026_07_14.json`, `docs/saq_a4_v2_artifact_schema_2026_07_14.json`, `docs/saq_a4_v2_protocol_independent_review_2026_07_14.md` | await explicit authorization for `A4-V2-I` implementation-only work; currently no next stage, build, run, data read, or SAQ change is authorized |

## 4. Complete SAQ Branch Crosswalk

The audited head is the branch tip observed during reconciliation. The
scientific snapshot in Section 2 can be earlier when later commits contain only
handoff or meeting-document changes. Role `PENDING_REVIEW` is reserved for a
newly observed branch that has no committed and independently reviewed
scientific milestone; such a row has no direction ID or scientific claim.

| Repository | Branch | Audited head | Role | Direction IDs | Disposition |
|---|---|---:|---|---|---|
| SAQ | `main` | `2163ebc` | `UPSTREAM_BASE` | none | upstream baseline |
| SAQ | `saq-correctness-base` | `bc7829b` | `CORRECTNESS_BASE` | none | positive 1-bit packing and finite padded-lane block-min fixes; not a research contribution |
| SAQ | `saq-boundary-audit` | `e582974` | `PRIMARY` | `R01` | retired method line; diagnostic baseline |
| SAQ | `saq-structural-followup` | `b71c699` | `PRIMARY` | `R02` | closed and pivoted |
| SAQ | `saq-global-cost-dp` | `699d2c9` | `PRIMARY` | `R03` | closed and pivoted |
| SAQ | `saq-planner-objective-analysis` | `5756412` | `PRIMARY` | `R04`, `R05` | both method lines closed; graph pivot recorded |
| SAQ | `saq-graph-traversal-analysis` | `a03ee40` | `PRIMARY` | `R06` | closed before Phase 5 |
| SAQ | `saq-transform-analysis` | `3d94840` | `PRIMARY` | `R07` | Attempt 1A closed |
| SAQ | `saq-lossy-projection-analysis` | `051ec6a` | `FOLLOWUP` | `R08` | Attempt 1B closed |
| SAQ | `saq-caq-optimality-analysis` | `9bb7d0c` | `PRIMARY` | `R09` | v1 official-source contract stopped; v2 protocol recorded |
| SAQ | `saq-caq-corrected-oracle-v2` | `ff360cd` | `FOLLOWUP` | `R09` | limitation established; one-shell candidate selected for one synthetic gate |
| SAQ | `saq-caq-one-shell-repair` | `433e8ea` | `EVIDENCE_SNAPSHOT_AND_UNPRESENTED_DRAFT_HOST` | `R09` | scientific closure at `977e7ff`; later commits add unpresented draft material |
| SAQ | `saq-ratio-metric-analysis` | `146dc16` | `PRIMARY` | `R11` | Attempt 3 closed |
| SAQ | `saq-arbitrary-cardinality-analysis` | `f1b464b` | `PRIMARY` | `R12` | reviewed terminal snapshot `f1b464b`; cost evidence `9ce1052`; closed at A4-1S exact-pipeline cost gate |
| SAQ | `saq-arbitrary-cardinality-feasibility-v2` | `f86a51d` | `FOLLOWUP` | `R12` | reviewed protocol-only follow-up; awaiting explicit `A4-V2-I` authorization; no execution or data access |
| SAQ | `saq-meeting-summary` | `SELF` -- commit containing this registry; parent at reconciliation `16df04a` | `SUMMARY` | all | summary-only; no experiment execution |

### Sibling evidence snapshot

This is evidence for `R10`, not a complete vectordb branch inventory.

| Repository | Branch | Audited head | Role | Direction IDs | Disposition |
|---|---|---:|---|---|---|
| vectordb | `main` | `f51b487` | `SIBLING_EVIDENCE` | `R10` | Attempt 2 execution and transfer memo; no dedicated SAQ experiment branch |

Git ancestry is not the conceptual pivot sequence. `R02` through `R08` were
generally opened as sibling branches from `saq-correctness-base@bc7829b`;
do not merge them merely to reproduce the narrative. The inherited histories
are `saq-transform-analysis -> saq-lossy-projection-analysis` and
`saq-caq-corrected-oracle-v2 -> saq-caq-one-shell-repair`.
`saq-caq-optimality-analysis` is a sibling v1 contract from the correctness
base, not an ancestor of corrected-oracle-v2.

## 5. Reporting Rollover Protocol

1. A newly observed branch enters the complete branch crosswalk immediately
   with role `PENDING_REVIEW`, no direction ID, and no scientific claim.
2. Create a direction row only after its first committed and independently
   reviewed selection note, protocol, gate result, or terminal decision. It
   starts `UNREPORTED` with an exact source branch, audited head, scientific
   snapshot, claim ceiling, evidence paths, and next authorized step.
3. A committed and independently reviewed protocol, gate result, terminal
   decision, or material prior-art boundary advances the scientific snapshot.
   If the direction was already `REPORTED`, change it to `UPDATE_PENDING`.
   If it was `UNREPORTED`, keep it `UNREPORTED` and update its snapshot.
4. Pure handoff, wording, formatting, or meeting-document commits do not
   advance the scientific snapshot.
5. Adding a direction to a draft deck does not change its reporting state.
   The draft should consume `UNREPORTED` and `UPDATE_PENDING` rows selected for
   that meeting.
6. Only after the user confirms that a meeting occurred, register the exact
   deck commit and meeting date. Set each substantively covered direction to
   `REPORTED` through the exact source snapshot shown in that deck. If its
   source already has a newer material milestone, leave it `UPDATE_PENDING`.
7. Never edit a historical completed deck. Create or update its successor.
8. Historical `UNREPORTED` rows are a backlog, not an instruction to put every
   old direction in the next meeting. Meeting selection remains explicit.

## 6. Sync And Concurrency Rules

- This Markdown file is the single source of truth. Do not create a second
  hand-maintained JSON copy unless a generator makes one representation
  derived from the other.
- The session producing a committed and independently reviewed milestone owns
  the summary handoff, but the handoff grants no experimental authority.
- Before editing, locate the summary worktree with `git worktree list`, re-read
  its `AGENTS.md` and this registry, fetch, require the worktree to be clean,
  and record the exact `origin/saq-meeting-summary` starting commit.
- One summary writer is mandatory. Atomically acquire a lock directory under
  the Git common directory named `saq-meeting-summary-edit.lock` before the
  first edit. If acquisition fails, stop and report the handoff rather than
  editing concurrently. A stale lock may be removed only after confirming that
  no session owns it.
- Reconcile the complete `origin/*` branch list on every registry update. Add
  new branches explicitly; never silently omit an unfamiliar branch.
- Update the registry before or with the deck. Stage only focused summary
  files and review the cached diff. Fetch again before push and compare
  `origin/saq-meeting-summary` with the recorded starting commit. If it moved,
  stop and integrate deliberately while still holding the lock; never
  force-push. Release the lock after a successful push or a clean abort.
- Untracked implementation files, running jobs, generated artifacts, and
  provisional results never enter the scientific or reporting snapshot.

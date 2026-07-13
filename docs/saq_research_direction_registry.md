# SAQ Research Direction Registry

Last reconciled: 2026-07-13

SAQ branch scope: every `origin/*` branch plus `upstream/main`, after
`git fetch --all --prune`. At this snapshot there are 15 unique SAQ branches
and no remote-only research branch. Sibling scope is deliberately narrower:
only `vectordb/main@f51b487` is audited as the external evidence snapshot for
`R10`; this file is not a complete inventory of all vectordb branches.

This is the canonical living registry for SAQ research directions, branch
ownership, scientific state, and meeting-reporting state. A branch is not the
same thing as a direction: one direction may span several branches, and one
branch may contain several related falsification studies.

## 1. Registered Reporting Boundary

Per the current project convention, the previous completed-meeting proxy is:

```text
deck:
  docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md
historical source:
  saq-caq-one-shell-repair@433e8ea
canonical reported_in:
  saq-meeting-summary@5cdc270:
    docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md
meeting_date:
  NOT_RECORDED -- imported user-requested reporting proxy
```

Git proves deck content, not that every slide was spoken in a meeting. The
`REPORTED` values below use the user's requested proxy: a direction counts as
reported only when that historical deck gives it a substantive research
question, evidence/status, decision or claim ceiling, and an authoritative
source snapshot. A bare mention, baseline use, or “do not reopen” sentence
does not count. This imported legacy boundary is the only meeting-date
exception; every future rollover requires the confirmed date and exact deck
commit. If this proxy is not the deck actually presented, revise this boundary
and all affected rows together rather than editing individual flags ad hoc.

The current successor deck is:

```text
docs/saq_next_meeting_attempts_1_4_slides_2026_07_13.md
summary snapshot: saq-meeting-summary@43835d9
Attempt 4 scientific snapshot: saq-arbitrary-cardinality-analysis@3c0a49f
```

This successor is a draft for a future meeting. Inclusion in it does not change
`UNREPORTED` to `REPORTED`.

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

| ID | Meeting label | Direction | Scientific snapshot | Research state | Exact decision / boundary | Reporting state | Previous-deck coverage | Current successor coverage |
|---|---|---|---|---|---|---|---|---|
| `R01` | historical | Default-neighborhood fixed policy and boundary-aware local plan selection | `saq-boundary-audit@e582974` | `CLOSED` | stop as main method; retain as diagnostic baseline | `UNREPORTED` | `ABSENT` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R02` | historical | Mixed shared local residual plans | `saq-structural-followup@b71c699` | `CLOSED` | recall signal lost to mixed-plan query/layout overhead | `UNREPORTED` | `REFERENCE_ONLY` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R03` | historical | Single-global static segment-cost DP | `saq-global-cost-dp@699d2c9` | `CLOSED` | no lower-cost plan dominated SAQ risk; near-frontier plans were slower | `UNREPORTED` | `ABSENT` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R04` | historical | Measured `fac_error` planner objective | `saq-planner-objective-analysis@5756412` | `CLOSED` | limitation evidence only; increasing nprobe did not recover default recall before the QPS advantage disappeared | `UNREPORTED` | `BASELINE_REFERENCE_ONLY` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R05` | historical | Segment ordering, search scheduling, and variance-bound calibration | `saq-planner-objective-analysis@5756412` | `CLOSED` | no safe mechanism removed enough slack | `UNREPORTED` | `REFERENCE_ONLY` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R06` | historical | Graph traversal with progressive SAQ prefixes | `saq-graph-traversal-analysis@a03ee40` | `CLOSED` | stopped before Phase 5; grouped complete estimator still cost about `26.8x` SymphonyQG | `UNREPORTED` | `REFERENCE_ONLY` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R07` | Attempt 1A | Full-dimensional PCA/residual-PCA transform replacement | `saq-transform-analysis@3d94840` | `CLOSED` | preregistered CIFAR replication failed | `REPORTED` | `SUBSTANTIVE`, slides 6--16 | `CARRIED_FORWARD` |
| `R08` | Attempt 1B | Physical `D -> d` lossy projection with tail surrogate | `saq-lossy-projection-analysis@051ec6a` | `CLOSED` | LP-0 Gate A failed before projected SAQ build | `REPORTED` | `SUBSTANTIVE`, slides 17--25 | `CARRIED_FORWARD` |
| `R09` | historical | Finite-round CAQ exact-gap limitation and low-cost repair | `saq-caq-one-shell-repair@977e7ff` | `CLOSED` | limitation retained; repair `NO_GO_ON_COMPLEXITY`; SAQ-centric incremental line stopped | `UNREPORTED` | `REFERENCE_ONLY` | `NOT_INCLUDED_SUBSTANTIVELY` |
| `R10` | Attempt 2 | Exact-hist shared scalar-codebook DP and outer bit allocation | local evidence `vectordb@f51b487`; prior-art/report snapshot `saq-caq-one-shell-repair@433e8ea` | `CLOSED` | retain as stronger offline baseline and objective-mismatch evidence, not a method | `REPORTED` | `SUBSTANTIVE`, slides 26--45 | `CARRIED_FORWARD` |
| `R11` | Attempt 3 | Paper-exact `1/Ratio@k` distance-quality re-evaluation | `saq-ratio-metric-analysis@146dc16` | `CLOSED` | `CLOSE_AS_METRIC_SENSITIVITY_EVIDENCE` | `REPORTED` | `SUBSTANTIVE`, slides 46--58 | `CARRIED_FORWARD` |
| `R12` | Attempt 4 | Fixed-rate arbitrary-cardinality mixed-radix scalar-product quantization | `saq-arbitrary-cardinality-analysis@3c0a49f` | `ACTIVE` | A4-0 `PASS_INSTRUMENT_ONLY`; A4-1S `FROZEN_AUTHORIZED_NOT_IMPLEMENTED`; real-base gate unauthorized | `UNREPORTED` | `RESERVED_NO_EVIDENCE` | `INCLUDED_PENDING_REPORT`, slides 59--64 |

### Reported-through ledger

| Direction | Reported through | Report source | Later material update |
|---|---|---|---|
| `R07` | `saq-transform-analysis@3d94840` | `saq-meeting-summary@5cdc270:docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` | none registered |
| `R08` | `saq-lossy-projection-analysis@051ec6a` | `saq-meeting-summary@5cdc270:docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` | none registered |
| `R10` | local evidence `vectordb@f51b487`; White--Singal audit/report `saq-caq-one-shell-repair@433e8ea`; external pins `arXiv:2606.00289v1` and official code `e92ed90` | `saq-meeting-summary@5cdc270:docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` | none registered |
| `R11` | `saq-ratio-metric-analysis@146dc16` | `saq-meeting-summary@5cdc270:docs/saq_next_meeting_attempts_1_3_slides_2026_07_13.md` | none registered |

All other research directions are baseline-relative `UNREPORTED`. Older
unreported directions form a historical backlog; they are not automatically
added to the next deck. `R12` is the only direction currently queued in the
successor deck.

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
| `R12` | A4-0 validates a strict synthetic dyadic-feasible-set witness and instrument only; no committed A4-1S, natural-data, ANN, or systems result. | `saq-arbitrary-cardinality-analysis@3c0a49f`: `docs/saq_attempt4_a4_0_synthetic_evidence_2026_07_13.md`, `docs/saq_attempt4_a4_1_base_only_feasibility_preregistration_2026_07_13.md`, `docs/saq_attempt4_a4_1s_synthetic_implementation_protocol_2026_07_13.md` | execute only the authorized A4-1S synthetic gate; base read remains forbidden |

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
| SAQ | `saq-caq-one-shell-repair` | `433e8ea` | `EVIDENCE_SNAPSHOT_AND_LEGACY_DECK_HOST` | `R09` | scientific closure at `977e7ff`; later commits add meeting material |
| SAQ | `saq-ratio-metric-analysis` | `146dc16` | `PRIMARY` | `R11` | Attempt 3 closed |
| SAQ | `saq-arbitrary-cardinality-analysis` | `d9dd626` | `PRIMARY` | `R12` | only active scientific direction; scientific content through `3c0a49f` |
| SAQ | `saq-meeting-summary` | `SELF` -- commit containing this registry; parent at reconciliation `43835d9` | `SUMMARY` | all | summary-only; no experiment execution |

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

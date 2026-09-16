# AGP Cockpit Master Plan v2

Status: active
Status-date: 2026-09-09
Decision status: accepted
Normative scope authority: `docs/planning/SCOPE_BOUNDARY.md`.

## 1. Mission

AGP Cockpit removes both the copy/paste loop and the accidental coupling
between one local execution failure and the end of a larger development task.

A user supplies one overall Task Contract: goal, acceptance criteria,
repository identity, allowed effects, budgets, optional human checkpoints,
remote binding, and completion contract. The Remote Development LLM makes
development decisions. Cockpit persists and orchestrates the task
deterministically. The Kit remains authoritative for governed repository
lifecycle operations.

## 2. Product-level invariants

- INV-01 Exactly one active controller owns dispatch authority for a task.
- INV-02 At most one mutating action per repository context is initially
  allowed concurrently.
- INV-03 Only validated, currently bound and authorized actions may execute.
- INV-04 Reusing an action ID with a changed payload is a protocol violation.
- INV-05 OUTCOME_UNKNOWN never permits blind replay.
- INV-06 User and Kit boundaries cannot be expanded by any LLM.
- INV-07 Transport success, execution result, Kit result and task completion
  are separate facts.
- INV-08 Task contract, decisions, budgets and approvals survive restart.
- INV-09 Old browser bindings confer no execution authority.
- INV-10 Completion evidence must match the required contract/revision/artifact.
- INV-11 Missing/corrupt persistence is never converted into assumed success.
- INV-12 Required tests and gates remain effective during recovery.

## 3. Target architecture

The authoritative runtime is a deterministic Python Task Controller backed by
durable local storage outside repository/Dropbox synchronization. The controller
owns task-state transitions, dispatch locks, correlation, budgets, checkpoints,
pause/resume/stop, reconciliation and completion verification.

The browser adapter transports frames. The executor enforces capability
profiles. Evidence recipes collect bounded observations. The Remote Development
LLM performs development reasoning. The Kit owns repository lifecycle.

Existing browser transport, protocol framing, executor code, Tkinter UI,
Mission/Operator concepts, duplicate protection, settings, packaging and
structured logging are reused where their semantics remain valid. No second
parallel runtime is introduced.

## 4. Development roadmap

### Phase 11 / S0 — Desktop basis
Status: COMPLETE / CERTIFIED.

### Phase 12 / S1 — Architecture contract and migration decision
Status: COMPLETE.

Deliverables:
- authority/state ownership inventory;
- reviewed ADR;
- synchronized normative planning sources;
- protocol version decision;
- capability/effect model;
- durable store/data-model decision;
- migration path from Mission/Phase8 legacy paths;
- acceptance matrix and architecture gates.

Exit: all affected normative rules are consistent and merged. No S2 runtime
behavior before this gate.

### Phase 13 / S2 — Minimal Remote Recovery Proof
Implement the smallest deterministic controller loop without local LLM.

Required proof:
- valid script failure does not end task;
- invalid frame executes nothing;
- duplicate action does not duplicate effect;
- premature COMPLETE is rejected;
- bounded stop/budget works;
- short live-browser proof;
- no automatic crash resume yet;
- no live repository mutation.

### Phase 14 / S3 — Durable Runtime and Journal
Add SQLite-backed TaskStore, Inbox/Outbox, action/attempt journal, payload
hashes, controller generation, repository lock, budgets, process identity,
OUTCOME_UNKNOWN, restart/resume and crash-injection tests.

### Phase 14 / S4 — Pause, Stop, Human Gates and Stall
Add durable suspension reasons, revision-bound checkpoints, safe stop,
restart-stable budgets and deterministic no-progress detection.

### Phase 15 / S5 — Governed Kit Recovery and Verified Evidence
Integrate real Kit PASS/BLOCKED/FAIL handling, supported reconciliation,
FILE_TRANSFER pass-through, governed lifecycle evidence and exact
revision/evidence checks. No direct Git/GitHub bypass.

### Phase 16 / S6 — Remote Context Continuity
Persist canonical task snapshot and deterministic context refresh. Support
binding epochs and controlled transfer from Chat A to Chat B.

### Phase 17 / S7 — Verified Completion Contract
Treat remote COMPLETE as a proposal. Verify required tests, Kit/CI/lifecycle,
human checkpoints and revision/artifact mapping before VERIFIED_COMPLETE.

### Phase 18 / S8 — Real Complex Development E2E
One bounded real feature must survive script failure, test failure and a
recoverable Kit BLOCKED, then complete required CI/PR/merge/post-merge without
human command/result mediation.

### Phase 19 / S9 — Human Checkpoint E2E
A real visual/physical checkpoint suspends the same task and resumes only after
revision-bound human confirmation.

### Phase 20 / S10 — Optional Local Observation Assistant
Hermes/local LLM only if controlled comparison shows reproducible benefit
without decision-authority or safety regression.

### Phase 21 / S11 — Long-running Robustness
Crash-after-effect, Chrome restart, duplicate/stale responses, provider outage,
network loss, unknown outcomes, false COMPLETE, exhausted budgets and stall.

### Phase 22 / S12 — Cross-platform Product Readiness
Only after macOS target runtime is robust.

## 5. Bootstrap strategy

Use each accepted slice to accelerate development of the next. After S2 proves
the Remote Recovery Loop, use it experimentally to assist S3 development under
the still-active S2 capability limits.

## 6. v2 completion criterion

The macOS product is functionally accepted for the target architecture only
after S0-S11 applicable gates are satisfied. The optional local-LLM slice does
not block acceptance.

## 7. Current acceptance status

Status-date: 2026-09-11
Adjudication: REVIEW_REMEDIATION_ACTIVE

The 2026-09-09 `FUNCTIONALLY_ACCEPTED` declaration is withdrawn after the
independent Ultra review found that several promised product-level properties
were not demonstrated by the shipped path or acceptance evidence.

The prior COMPLETE phase records remain historical implementation/evidence
records; they are not current proof that the corresponding product contract is
accepted.

Canonical remediation authority:
`docs/planning/ULTRA_REVIEW_REMEDIATION.md`.

Whole-product `FUNCTIONALLY_ACCEPTED` may be reconsidered only after the
applicable K01-K07 acceptance criteria and the original review guarantees are
re-proven at the correct revision. S12's `PORTABLE_CORE_READY` label does not
override this macOS product re-adjudication.

## 2026-09-15 — K07 communication-loop rebaseline

This section supersedes older K07 planning statements where they conflict with the merged implementation through PR #115/#116. Historical remediation evidence remains historical and is not rewritten.

### Current implemented direction

The primary remote-LLM development path is the decomplexified artifact/file loop:

`human -> Cockpit -> remote LLM -> one Python command artifact -> browser/download -> Cockpit -> run_next.py / Agentic Project Kit -> one return bundle -> browser file attachment -> same remote-LLM conversation -> next Python artifact | AGP_DONE | AGP_NEEDS_HUMAN`

The remote LLM is not required to return a Protocol-v1 JSON work frame for this primary path. The browser/bridge transports opaque artifacts and minimal continuation control; it must not reproduce Git, GitHub, Agentic Project Kit, repository lifecycle, gate, PR, release, or handoff semantics.

Protocol-v1, DIRECT_EXECUTION and FILE_TRANSFER remain compatibility/transport infrastructure only where still required by existing implementation and tests. They are not the target semantic interface for the simplified remote-LLM file loop. Do not create a parallel protocol.

### Responsibility boundary

- Remote LLM: reasoning, diagnosis, and creation of the next executable Python work artifact; terminal outcome is `AGP_DONE` or `AGP_NEEDS_HUMAN`.
- Cockpit: deterministic orchestration, correlation, persistence, bounded execution and recovery.
- Browser/bridge: minimal deterministic transport of the task, one Python artifact, one return bundle, and the fixed continuation trigger.
- Agentic Project Kit: repository/Git/GitHub/workflow/lifecycle semantics.

### Next acceptance objective

Before further semantic expansion, prove the simplified loop with a real same-conversation end-to-end cycle. Instrument the existing seams rather than parsing browser/network traffic semantically. The cycle trace should correlate, at minimum:

1. `LLM_COMMAND_CREATED`
2. `BROWSER_COMMAND_DOWNLOADED`
3. `COCKPIT_COMMAND_ACCEPTED`
4. `LOCAL_EXECUTION_STARTED`
5. `LOCAL_EXECUTION_FINISHED`
6. `RESULT_BUNDLE_CREATED`
7. `BROWSER_RESULT_ATTACHED`
8. `CONTINUATION_SENT`
9. terminal/next outcome: `LLM_NEXT_COMMAND`, `AGP_DONE`, or `AGP_NEEDS_HUMAN`

Use one stable correlation identity across the cycle where current contracts permit it, plus artifact filename, SHA-256 and timestamp. Reuse existing task/cycle identifiers and persistence structures; do not introduce a second ledger if an existing authority can carry the evidence.

Acceptance requires fail-loud, resumable behavior at browser boundaries and protection against duplicate local execution. Exactly-once or demonstrably idempotent handoff behavior is more important than hiding browser failures.

### Immediate work order

1. Inventory which transition events above are already emitted/persisted by the merged PR #115 implementation.
2. Add only missing correlation/trace seams in one coherent product slice.
3. Run focused Python and Playwright tests plus repository/Kit gates.
4. Perform a real browser/remote-LLM E2E cycle in the same conversation.
5. Preserve the resulting trace as acceptance evidence.
6. Only after that evidence adjudicate whether legacy Protocol-v1 complexity can be further isolated or removed.

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.

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
Status: ACTIVE.

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

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

## 2026-10-01 — Standard tasks as lifecycle verbs, repository switch

Status: planned (maintainer agreement 2026-10-01). Basis: live acceptance of the
complete Kit lifecycle (steps 1520–1532, see
`docs/engineering/K07_STATE_AND_NEXT_STEPS_2026-10-01.md`).

### Goal

Ordinary users operate the Cockpit through a few lifecycle verbs instead of
Kit knowledge. The Kit keeps all repository semantics; the remote LLM still
chooses the concrete Kit command (SCOPE_BOUNDARY §4: the Cockpit never chooses
a Kit workflow on its behalf). Simplicity is the goal: the UI offers only what
is valid in the current repository state and recommends exactly one next step.

### Verbs

| # | Name (UI) | Kit area (examples, not prescribed) | Effect class | Local completion verifier |
|---|---|---|---|---|
| 1 | Lagebericht | read-only diagnostics, `workspace adopt` for foreign repos | E0 | none (report) |
| 2 | Arbeit beginnen | `work start`, `transfer remote-work-start` | E3 (sync) | new branch from current origin/main, clean worktree, rules confirmed |
| 3 | Arbeiten (own tab) | any, task-defined | as authorized | task contract |
| 4 | Abschließen | `work finish`, `pr-create-complete`, `pr-closeout-complete` | E3/E4, approved by the start click | `AGP_CI_LIFECYCLE_COMPLETION_V2` |
| 5 | Wiederherstellen | `work recover`; destructive settle only after NEEDS_HUMAN | E0 → E3 | main synchronized, clean, Kit post-merge-check PASS |
| 6 | Chat wechseln | `transfer chat-switch-complete` | E2 | existing handoff verifier |
| 7 | Repo übernehmen | `workspace adopt` → `workspace init`; new repo: `init`, `github-create` | E2 / E4 | workspace present, `agentic-kit check` PASS |
| 8 | Release | `release ready/prepare`, `release-publish` | E4, always asks | release evidence (to be specified) |
| 9 | Pflege | `artifact-gc`, `docs lifecycle sweep`, `workspace upgrade`, Kit update | E1/E2 | Kit check/doctor PASS |

### Enforced rules (code, not prose)

- R1 Command authority from the installed Kit: the command digest comes from the
  Kit installation used for the active repository (packaged manifest), not from
  a file in the repository. New Kit orchestrators appear without Cockpit changes.
  No installed Kit means state UNKLAR and no task starts; the repository copy
  is used only by tests and diagnosis (review 2026-10-01).
- R2 Every work order of a standard task executes at least one command with
  `surface: orchestrator` from that manifest; primitives only additionally and
  only without remote effect.
- R3 Remote effects are limited to the verb's effect class. A command whose
  effect the Cockpit cannot classify counts as "unknown effect" and asks the
  human (fail closed). Destructive commands and Release always ask.
- R4 "Abschließen": the start click after an explicit dialog is the approval
  (maintainer decision 2026-10-01). Code limits: never from main, never force
  push, merge only through the Kit's green-CI gates, bounded budget, every
  auto-approved effect shown in the UI. The approval covers only the effect
  classes the task declares (publish, PR, merge, post-merge closeout); any
  other remote effect the remote side proposes still asks (review 2026-10-01).
- R5 One task at a time per repository; repository switch only while idle.
- R6 An interrupted Abschließen offers Wiederherstellen instead of only stopping.

### Repository state model (deterministic, local, read-only)

| State | Condition | Offered |
|---|---|---|
| KEIN_KIT | no Kit workspace | Repo übernehmen |
| BEREIT | on main, main == origin/main, clean, post-merge-check PASS | Arbeit beginnen, Release, Pflege |
| IN_ARBEIT | on a work branch, rules confirmed | Arbeiten, Abschließen, Chat wechseln |
| LÄUFT | a task is running | nothing new (Stop in its tab) |
| STÖRUNG | drift, unexpected changes, post-merge not PASS, interrupted task | Wiederherstellen |
| UNKLAR | state unreadable (Kit missing, `gh` not logged in) | Lagebericht with the fix |

Lagebericht and Chat wechseln stay available except in LÄUFT.

### UI

- Tab order: Standard Tasks | Arbeiten | System.
- Repository switch is global context, not a task: the header line
  "Repository: …" becomes a button with recent repositories and "Anderes Repo…".
- Standard Tasks tab, top to bottom: state card (Lagebericht, refreshed on open,
  after each task and on request, with one sentence and "Empfohlen: …"); the
  main path as a numbered stepper ① Arbeit beginnen → ② Arbeiten → ③
  Abschließen → ④ Chat wechseln; "Bei Problemen": Wiederherstellen; collapsed
  "Weitere": Repo übernehmen, Release, Pflege.
- The recommended step is the only primary button; invalid buttons are
  disabled and their tooltip says why.
- Every button carries an effect badge: "liest nur" (E0), "ändert lokal"
  (E1/E2), "wirkt auf GitHub" (E3/E4), "fragt immer" (destructive/release).
- Tooltips (three lines: what happens · effect · when available) come from one
  text table that also feeds the documentation.

### Slices (each: tests, live check, protocol log entry)

1. P1 Command authority: digest from the installed Kit (R1), orchestrator
   obligation for standard tasks (R2), unknown effect asks (R3). — Implemented
   2026-10-01 (COMMUNICATION_PROTOCOL 18), live check pending; includes
   correction instead of a fatal stop for rule violations.
2. P2 State model and Lagebericht: `core/repo_state.py`, local read-only Kit and
   git observation (E0, human-initiated), states above, recommendation. —
   Implemented 2026-10-01 (report in the Standard Tasks tab and
   `.local/agp-cockpit/state/repo-state.json`; no installed Kit blocks every
   task start). Live check pending.
3. P3 Standard Tasks tab: order, state card, stepper, groups, enabling by state,
   badges, tooltip helper and text table. — Implemented 2026-10-01
   (COMMUNICATION_PROTOCOL 20); verbs of later slices are shown disabled with
   "in Vorbereitung (Plan Px)". Live check pending.
4. P4 Repository switch: selection, checks (git, origin, Kit installed and
   version, `gh auth status`, workspace present → else offer Repo übernehmen),
   rebinding of bridge, Download/run_next and digest, recent list, new chat
   required, only while idle (R5).
5. P5 Standard-task framework: declarative definition (goal text without
   command names, effect class, input fields, verifier), single-task lock,
   abort → Wiederherstellen (R6); migrate Chat wechseln.
6. P6 Abschließen: auto approval with code limits (R4), offer Chat wechseln
   afterwards. Acceptance criteria (not optional): a visible protocol of every
   auto-approved effect (commands, changed refs, PR, CI runs) and, after an
   interruption, Wiederherstellen offered automatically (R6).
7. P7 Arbeit beginnen (inputs: branch name, kind).
8. P8 Wiederherstellen (diagnosis first, destructive steps ask).
9. P9 Repo übernehmen, proven on a separate test repository.
10. P10 Pflege (including Kit update and `workspace upgrade`).
11. P11 Release (always asks; verifier to be specified first; private only per
   `docs/planning/RELEASE_POLICY.md`).

Kit-side prerequisites that would simplify P1–P3 (tracked in the 2026-10-01
handoff, not Cockpit work): effect classification in the manifest, a read
command for branch/commit CI, pure JSON output, Kit-owned volatile files out of
the worktree, a pinned Kit version and faster, non-duplicated runs in the
managed CI template, and a post-merge refresh that does not demand a further
refresh of itself.

## 2026-10-01 — Slice T1: fixes, token diet, CI template

Evidence: finish run 1547–1556 (P2 + P3, PR #141/#142) and its bundles.

Implemented (COMMUNICATION_PROTOCOL 21–24, `AGP_CI_GATE_V2`):

1. Fixes: first porcelain path of the Lagebericht no longer cut; accepted DONE
   closes the local task; Standard Tasks hint line follows the repository state
   (no "bereit" while a task runs); recommendation marked in the badge line
   (equal button height); tests independent of the host's `gh`.
2. Token diet: deterministic result projection (−71 % on the finish run) and a
   compact command digest (−59 %).
3. CI template: push runs only on main, PR runs cancel their predecessor, Kit
   pinned to 1.0.13, Python and browser jobs in parallel with a browser cache,
   required check `agentic-gate` as the aggregate.

Live 2026-10-02 (run 1557–1560, PR #143/#144): one remote turn; projection of
step 1559 81 KB → 15 KB; CI 1:46–2:06 per run, one PR run plus one main run per
PR; local task closed as `VERIFIED_COMPLETE`.

## 2026-10-02 — Slice T2: extension refresh, file hygiene, Kit findings view

Implemented (COMMUNICATION_PROTOCOL 25–29): handshake-driven extension refresh
with per-build loop guard; browser copies removed after accepted ingest; TMPDIR
for work orders; previewed cleanup incl. Kit `/tmp` logs; Kit findings window;
digest once per chat; Bridge panel turn count. Greenfield ledger extended
(KIT-GF-023…028, extensions of 010/011/017, status vocabulary, Cockpit
mitigations); `Download/alt` (973 MB) removed, cited evidence archived.

Deferred (T3): local pre-push gate (needs a defined CI-equivalent command
authority, e.g. `agentic-kit work check` plus pytest, enforced before
publishing commands).

Release plan: first release 0.1.0 after T2 is live-proven (extension refresh,
cleanup). Prerequisites: one version mapping (app / extension / build id) and a
specified release verifier (P11). Release policy decided 2026-10-02
(`docs/planning/RELEASE_POLICY.md`): private releases only — version bump,
changelog, annotated tag, local build; no GitHub Release, PyPI or Zenodo.
Later releases per completed block (0.2.0 after P4–P6).

Live 2026-10-02 (run 1561–1564, PR #145/#146): one remote turn; four browser
downloads removed after ingest; digest reused once in the same chat; local task
`VERIFIED_COMPLETE`.

## 2026-10-02 — Slice T3: Kit findings sync, release policy, window

Implemented (COMMUNICATION_PROTOCOL 30–33): Kit findings synced from the Kit
repository's own reports (13 CLOSED, 3 PARTIAL, 2 OPEN of KIT-GF-001…018 at Kit
commit 26be95b); KIT-GF-029 (release lifecycle assumes public publication);
release policy enforced on work orders; larger window with scrolling tabs;
recommendation hint for verbs of later slices.

## 2026-10-02 — Slice T4: no second pull request for a merged branch

Evidence: finish run 1568–1582 (T3, PR #147/#148 and the empty PR #149).
Implemented (COMMUNICATION_PROTOCOL 35–38): work-order contract stated to fresh
chats, download ingress limited to safety checks, merged-branch guard,
Cockpit-verified repository facts in every continuation, Kit verdict rule;
Greenfield ledger KIT-GF-030, KIT-GF-031 and an extension of KIT-GF-027.

Order after T4 (2026-10-02): P5 standard-task framework → P6 Abschließen →
P11 Release (button; release 0.1.0 is then made with it) → P4, P7–P10. P6 turns
the finish into a fixed sequence instead of a remote improvisation (run
1568–1582 needed 14 steps and two pull requests).

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.

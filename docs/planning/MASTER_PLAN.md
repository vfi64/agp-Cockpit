# AGP Cockpit Master Plan v2

Status: active
Status-date: 2026-09-09
Decision status: accepted
Review policy: on material change
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
   required, only while idle (R5). — Implemented 2026-10-02
   (AGP_REPOSITORY_SWITCH_V1, AGP_CONVERSATION_BINDING_V1, COMMUNICATION_PROTOCOL
   54); live check pending.
5. P5 Standard-task framework: declarative definition (goal text without
   command names, effect class, input fields, verifier), single-task lock,
   abort → Wiederherstellen (R6); migrate Chat wechseln.
6. P6 Abschließen: auto approval with code limits (R4); no Chat-wechseln
   recommendation afterwards (owner 2026-10-02, COMMUNICATION_PROTOCOL 52). Acceptance criteria (not optional): a visible protocol of every
   auto-approved effect (commands, changed refs, PR, CI runs) and, after an
   interruption, Wiederherstellen offered automatically (R6).
7. P7 Arbeit beginnen (inputs: branch name, kind).
8. P8 Wiederherstellen (diagnosis first, destructive steps ask). Full version
   waited for the Kit fix KIT-GF-033 (owner 2026-10-02); verified fixed with Kit 1.0.14
   (2026-10-03). Full version implemented 2026-10-03 (AGP_DESTRUCTIVE_EXECUTE_GATE_V1):
   rescue of main through the Kit route, signed execute only after approval.
   Live-verified 2026-10-03 (live test 2, decision box of AGP_STANDARD_TASK_DECISION_V1).
9. P9 Repo übernehmen, proven on a separate test repository.
10. P10 Pflege (including Kit update and `workspace upgrade`).
   Inventory 2026-10-04 with Kit 1.0.16 on main 989bb2f: `workspace upgrade` nothing to do
   (schema v2), `artifact-gc` nothing to collect in all four modes, `docs lifecycle sweep` 21
   findings (missing Status/Decision/Review headers in planning documents: owner decides, done
   as an Arbeiten task), no Kit route for updating the Kit itself. P10a (built 2026-10-04,
   COMMUNICATION_PROTOCOL 64): the Pflege standard task — dry runs on main; nothing to do stays
   on main; otherwise `chore/pflege-<date>` through the work-start route with the changes left
   for Abschließen (AGP_MAINTENANCE_VERIFIER_V1); the sweep only reported, its execute asks
   (AGP_OWNER_DECISION_EXECUTE_V1); `workspace ci-update --execute` rejected
   (AGP_CI_UPDATE_GUARD_V1, KIT-GF-042). P10b: Kit update (new version → owner asks → `.venv`,
   both CI pins, `commands sync-entrypoints`; verifier: installed = pinned, check/doctor PASS);
   first real use: the Kit release after 1.0.16 that carries KIT-GF-039 to 042 (fixed on Kit
   main #2379/#2381/#2383, not released yet). Update 2026-10-05: Kit 1.0.17 adopted by hand
   (P10b not built yet; the same steps as #194). Retest GF-E058: `workspace ci-update
   --execute` still replaces the Cockpit's customized CI with 1.0.17 (KIT-GF-042 stays open,
   `reproduced_in` 1.0.17, AGP_KIT_FINDING_REPRODUCED_V1), so AGP_CI_UPDATE_GUARD_V1 stays and
   P10b keeps bumping both pins by hand. Update 2026-10-05: Kit 1.0.18 adopted by hand (Kit
   fixes #2395 for KIT-GF-042 and #2397 for KIT-GF-046, both patched by Claude and verified,
   GF-E063/GF-E064); ci-update now blocks the customized CI itself, the guard stays as a
   cheap second line. The Kit release itself ran through a local runner script (KIT-GF-047).
11. P11 Release (always asks; verifier to be specified first; private only per
   `docs/planning/RELEASE_POLICY.md`). Kit gate lifted: KIT-GF-032 verified fixed
   with Kit 1.0.15 (2026-10-03; KIT-GF-029 with 1.0.14). Owner's decisions 2026-10-04:
   the release work order runs `release prepare --write`, then updates the Cockpit's
   version map (AGP_VERSION_MAP_V1) in the same work order, then `work finish`
   (Kit repair tracked as KIT-GF-037); the live publication keeps the Kit's marker flow
   (prepare PR, marker PR, tag, marker-removal PR; signed approval tracked as KIT-GF-038).
   Update 2026-10-04: Kit 1.0.16 fixes both (VERIFIED_FIXED, GF-E051/GF-E052). P11 can
   therefore declare `release.version_anchors` in `.agentic/config.yaml` (APP_VERSION and
   the versions.json row) instead of a work-order edit, and use the signed
   `release-publish --expected-signature` route instead of marker PRs. Open for P11
   (Cockpit side): the anchor row template is static, so the version map must be aligned
   (newest row position; extension and build_id policy) before tests/test_release_versions.py
   passes on a release branch. Changing `.agentic/config.yaml` is a rule-source change —
   watch KIT-GF-039 (no `rules communication-refresh --publish` in the release work order).
   Owner's decision 2026-10-04 (AGP_VERSION_MAP_V2, RELEASE_POLICY.md): the Kit appends the
   versions.json row; its build id is `release-<app>`, set in version.py and
   build_identity.js by the release work order (rebuilds `-r<N>`); the extension version
   leaves the row. P11a (this version map) first, then P11b: the Release standard task
   (input: version; precheck BEREIT on main; release PR via the Kit, then the signed private
   `release-publish` that always asks; verifier: tag on origin at the merged release
   commit). P11b must lift the Cockpit's blanket rejection of `agentic-kit release-publish`
   for `publication: none` with an approved signature (RELEASE_POLICY.md).
   P11a merged 2026-10-04 (#200). P11b built 2026-10-04: the Release standard task
   (RELEASE_POLICY.md, COMMUNICATION_PROTOCOL 62); proven live by the first real release.
   Release 0.1.1 made with the button on 2026-10-04 (#204/#205, resume #206, signed tag
   v0.1.1 on 20a61dd, VERIFIED_COMPLETE); the GitHub Release entry by the owner by hand.
   Release 0.2.0 made with the button on 2026-10-05 (#234/#235, signed tag v0.2.0 on
   cc63c1e, VERIFIED_COMPLETE); the entry again by the owner by hand.
   P11c prepared 2026-10-05 (COMMUNICATION_PROTOCOL 69): title template, policy JSON
   `kit_github_release`, precheck/signed-route/verifier accept `github`; pull requests carry
   release-note categories (AGP_PR_RELEASE_CATEGORY_V1), the release pull request needs a
   moved changelog (AGP_RELEASE_CHANGELOG_GATE_V1), phase 2 approval no longer blocked by
   the release's own build id (AGP_RELEASE_PHASE2_APPROVAL_V1). The switch to
   `publication: github` waits for KIT-GF-049 (the Kit's GitHub route runs Kit-repository
   docs audit and command-reference check); first live proof then (KIT-GF-043 retest).
   P11c (unblocked 2026-10-05: Kit 1.0.17 carries KIT-GF-043, #2387; status FIXED, the Cockpit
   retests it with its own first GitHub-publication run): the owner wants the Kit to create the private GitHub
   Release entry in the same signed `release-publish` run (owner 2026-10-04). Then:
   `publication: github` in `.agentic/config.yaml` (rule source, KIT-GF-039), release
   policy and its JSON (the Kit's own `gh release create` inside the signed run; Cockpit
   work orders still never run gh release), the Release precheck and the signed-route
   check accept `github`, the verifier also checks the release entry; rehearse in a
   disposable clone first. Until then the owner creates the entry by hand.

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

## 2026-10-02 — Slice T5: standard-task framework, Abschließen, Arbeit beginnen

Live T4 (run 1583–1587, PR #150/#151): one remote turn after one correctable
rejection; the Cockpit-verified facts were quoted by the remote side.
Implemented (COMMUNICATION_PROTOCOL 39–43): P5 framework with start-click
approval and local verifiers, P6 Abschließen, P7 Arbeit beginnen and, because
P6's acceptance requires it (R6), a basic Wiederherstellen (diagnosis first,
destructive steps ask; the full P8 stays open). Release policy: the private tag
push is allowed after approval (owner's decision 2026-10-02). Live checks
pending: Abschließen of this branch with its own button, then Arbeit beginnen.

## 2026-10-02 — Release 0.1.0 (manual) and P11 on hold

Live: P7 Arbeit beginnen confirmed (1594–1597, local verifier passed, one
correctable rejection); P5/P6 confirmed five times with one remote turn each.
Kit 1.0.13 has no release route for an external, private workspace
(KIT-GF-029, KIT-GF-032). Owner's decision 2026-10-02: release 0.1.0 manually
(version map, changelog, annotated tag by the owner); the Release button (P11)
follows a Kit fix. Next slices: P8 Wiederherstellen (full), P4 Repo wechseln.

## 2026-10-02 — Architecture principle: the Kit controls; Kit-gated buttons

Owner's decision: **the Cockpit steers, the remote LLM decides, the Kit controls.**
The Cockpit orchestrates the loop, observes and verifies (Lagebericht, guards, CI
gate, verifiers) and never changes the repository itself; every repository change
runs inside a work order through a Kit route. A button whose Kit route is missing
is not built with a Cockpit-local or raw-git workaround; it waits for the Kit fix:

| Button | Waits for | Kit gap |
|---|---|---|
| P8 Wiederherstellen (full) | — (KIT-GF-033 verified fixed in 1.0.14, 2026-10-03) | gate lifted: build on `work rescue` |
| P11 Release | — (KIT-GF-032 verified fixed in 1.0.15, KIT-GF-029 in 1.0.14) | gate lifted: build on `release ready` / `release prepare` / private `release-publish` |

The basic Wiederherstellen stays: remote diagnosis, repair through Kit routes only,
NEEDS_HUMAN where the Kit has no route. Enforced in code: Kit-gated verbs are
disabled with the finding ids (AGP_KIT_GATED_VERBS_V1), and a test forbids
repository-changing git calls in the Cockpit's sources (the Kit findings cache
clone is the only exception). P-steps are done one at a time (owner 2026-10-02);
next: P10 Pflege, then P4 Repo wechseln, then P9 Repo übernehmen.

## 2026-10-02 — P4 Repo wechseln; next: DOM hardening

P4 implemented as a Cockpit-level event (no repository change, no Kit gap): a
read-only check of the candidate, provisioning of the Cockpit's own transport
paths (Download/run_next.py, local `info/exclude`), persisting the root and a
restart of the app, so every binding goes through the normal start path. One
ChatGPT conversation per repository is enforced at task start. The packaged app
carries the canonical runner; the stale-app guard keeps comparing with the
Cockpit's own checkout.

Next slice (owner 2026-10-02): **DOM hardening of the browser transport**, in
this order — (1) outcome-first send: the send-control probe becomes advisory,
the committed user turn is the hard check, one diagnosed retry; (2) sanitized
DOM structure snapshots of every failure (tags, roles, ARIA labels, test ids,
no chat content) replayed against the real probe code; (3) one DOM adapter with
a contract per touchpoint (composer, attachments, submit, committed turn,
finished reply, result file); (4) a touchpoint self-test at mission start;
(5) a fingerprint of the composer UI to log a new ChatGPT variant early. A
local LLM stays out of the send path; an official-API transport is a later
owner decision. Then P10 and P9 as far as their Kit routes exist.
Update 2026-10-05 (r6, COMMUNICATION_PROTOCOL 67): first live piece — the attachment
touchpoint is bound to the resolved composer (the ChatGPT start page renders three
composer forms, two invisible) and the bounded send retry clears its own draft. The
sanitized DOM probe of (2) was done by hand with the owner; automating it remains open.
Update 2026-10-05 (Slice C, COMMUNICATION_PROTOCOL 68, build r9): (4) done — the
touchpoint self-test runs before the composer is touched and stops a start with a clear
reason; its page-shape snapshot on every start covers part of (2) for the start page.
Open: (1), (3), (5), and snapshots for failures after the start.
Update 2026-10-07 (DOM bundle, COMMUNICATION_PROTOCOL 70, build release-0.2.2-r2): (1) done — the
live send was already outcome-first (committed user turn), the bounded retry no longer needs the send
button; (5) done — UI fingerprint per start, `UI_VARIANT_CHANGED`, System tab line; (2) capture done —
sanitized page shapes with every failure after the start; replay against the probe code follows with
(3), which starts the modularization of content.js (owner 2026-10-07: classic scripts, one namespace
each, no bundler; DOM adapter first). Open: (2) replay, (3).
Update 2026-10-07 (slice 3a, COMMUNICATION_PROTOCOL 71, build release-0.2.2-r3): `chatgpt_dom.js` carries
the file-card, assistant-turn and alert touchpoints; content.js selector calls ratcheted to 23. Next
slices: composer and send controls, generation/stop signals, attachment preview; then (2) replay.
Update 2026-10-07 (slice 3b, build release-0.2.2-r4): composer fallback, send control, generation and stop
signals moved; content.js selector calls 16. Next: attachment preview and evidence lookups, then the
adapters of browser_native_transport.js and conversation_contract.js, then (2) replay.
Update 2026-10-07 (slice 3c, build release-0.2.2-r5): attachment preview and dialog close moved; content.js
selector calls 10 (assistant text extraction, wait diagnostics, activity observer remain).
Update 2026-10-07 (selector table, COMMUNICATION_PROTOCOL 72, build release-0.2.2-r8): DOM hardening
step 3 complete — every ChatGPT selector, including those of the injected page helpers, the native
transport and the Phase-5 contract, lives in `chatgpt_selectors.js`. Next: split `content.js` module by
module (panel UI, file ingress/result upload, send transport; content.js keeps the controller).
Update 2026-10-07 (content.js module 1, COMMUNICATION_PROTOCOL 73, build release-0.2.2-r9): the overlay is
`cockpit_panel.js`; content.js 4246 → 3789 lines (ratchet). Next: file ingress (assistant file cards,
download/preview materialization, command and terminal file submit), then send transport.
Update 2026-10-07 (DOM hardening complete, COMMUNICATION_PROTOCOL 74, build release-0.2.2-r10): (2) replay done —
shape V2 keeps the decision attributes, the e2e replay rebuilds a page from a shape and runs the real probe
code (round trip on four ChatGPT-like pages; mutation-checked: dropping disabled, step-file names, inert or
author role fails it); the UI fingerprint is versioned (the false „NEU“ of the V1→V2 change clears).
All five DOM-hardening steps are done. Order from here (owner 2026-10-07: Claude sets it): content.js
module 2 file ingress, module 3 send transport, module 4 legacy paths; then Kit 1.0.20 adoption and
release 0.2.3.
Update 2026-10-07 (content.js module 2, COMMUNICATION_PROTOCOL 75, build release-0.2.2-r11): file ingress is
`cockpit_ingress.js`; content.js 3789 → 3312 lines. Next: module 3 send transport.
Update 2026-10-08 (content.js module 3, COMMUNICATION_PROTOCOL 76, build release-0.2.2-r13): send transport is
`cockpit_send.js`; content.js 3312 → 2617 lines; „Branch wechseln …“ without preselection. Next: module 4
legacy paths.
Update 2026-10-08 (content.js module 4a, COMMUNICATION_PROTOCOL 77, build release-0.2.2-r14): operator paths
without a button since 2026-09-15 and their six content scripts removed; content.js 2617 → 2205 lines.
Next: 4b the disabled degraded DOM send path in cockpit_send.js (AGP_ALLOW_DEGRADED_DOM_FALLBACK = false),
then 4c the bridge routes only those paths used (e.g. /v1/task/complete-proposal), if nothing else calls them.
Update 2026-10-08 (content.js module 4b, COMMUNICATION_PROTOCOL 78, build release-0.2.2-r15): the disabled DOM
send path is removed; cockpit_send.js 761 → 551 lines, content.js 2205 → 2196. Next: 4c.
Update 2026-10-08 (Kit 1.0.20 adoption, build release-0.2.2-r16): CI pins and manifest 43b81efb137f; the remote-effect
list follows the Kit's declarations (KIT-GF-057 verified); register synced with Kit e4ee4868. Owner decision 2026-10-08:
Kit adoption before 4c; next release 0.2.3, 4c afterwards.
Update 2026-10-08 (P11c switched on, no build change): `publication: github` with `release.publish_checks: none`;
the GitHub Release entry comes from the Kit's signed run. Correction: the Cockpit releases through its Release
button (release-prep and release-publish), not through `agentic-kit release run` (PyPI/Zenodo phases).

## 2026-10-03 — Improvement proposals (owner: "merken")

Assessment after P8 and the Kit 1.0.14 release; none is decided yet, each needs its own owner decision:

1. **No second PR per change (Kit).** Every merged change triggers a „Refresh successor package“ PR (#174/#175 … #180/#181): twice the PRs and CI runs. The handoff refresh belongs in the same PR or is generated in CI instead of committed. Largest lever.
2. **Do not commit generated projections (Kit).** `docs/site` and the handoff packages go stale and break the Kit's own CI (KIT-GF-034); generate them in CI/Pages instead.
3. **Deterministic standard tasks without a ChatGPT round trip (Cockpit).** Abschließen runs exactly one Kit orchestrator; the Cockpit could start it directly with the same gates (approval scope, CI gate, local verifier). Conflicts with the wording „die Remote-LLM steuert“, not with „das Kit kontrolliert“ — owner decision required before any work. The remote LLM keeps diagnosis (Wiederherstellen) and content work (Arbeiten).
4. **Lean Kit profile for external repositories (Kit).** Core routes (work start/finish, rescue, release with publication policy) without the Kit's self-administration.
5. **Long term: an agent with direct tool access plus the Kit CLI** instead of the browser transport; the Cockpit stays justified where the ChatGPT web model is used deliberately without an API.
6. **Rejected work orders into Download/ (Cockpit, owner 2026-10-04: yes).** A rejected work order keeps its browser copy in ~/Downloads (AGP_DOWNLOAD_HYGIENE_V1 removes only accepted ones); persist it in Download/ beside the rejection record and remove the browser copy.
7. **Narrow scope when a release resumes (Cockpit, owner 2026-10-04: yes).** A resumed Release (phase 1 merged) still grants the release-branch and pull-request effects with its start click; grant only what the tag phase needs.

## 2026-10-05 — Cockpit order after release 0.2.0 (owner: all proposals accepted)

1. Ampel slice — done 2026-10-05 (AGP_AMPEL_V1, AGP_SHORT_RESULT_LINE_V1,
   AGP_FRESHNESS_LINE_V1, AGP_UNKLAR_HINT_V1; build release-0.2.0-r2): one light in the
   Lage (green: BEREIT; yellow: work open, task running, decision pending, Kit follow-up
   open, no Kit layer; red: STÖRUNG, UNKLAR, stale app, interrupted finish, task needs
   the owner), the result line keeps only the Cockpit's own verdicts, the stale warning
   wraps in its own header line.
2. Rebuild/restart button — done 2026-10-05 (AGP_REBUILD_BUTTON_V1, build release-0.2.0-r3):
   the stale-app warning offers „Neu bauen und neu starten“ (source newer) or „Neu starten“
   (bundle newer); the app runs the build script, then a detached relauncher reopens the
   bundle after the app closed itself. The extension self-reload already existed
   (AGP_EXTENSION_AUTO_REFRESH_V2) and was proven live on 2026-10-05: r1 → r2 two seconds
   after the restart, so the owner's manual extension reload is not needed.
2a. Guided recovery — done 2026-10-06 (AGP_GUIDED_RECOVERY_V1, AGP_FOLLOWUP_PR_CI_V1,
   AGP_FULL_HEAD_SHA_V1, AGP_COMPACT_LAGE_V1; build release-0.2.0-r4; owner: „der Nutzer
   sollte besser auf dem Lösungsweg geführt werden“, „der Bildschirmplatz ist endlich“).
3. P10b „Kit aktualisieren“ — deferred 2026-10-06 (owner: „Ich möchte unser
   Architekturprinzip erst einmal nicht brechen“): a Cockpit-side updater would emulate a
   missing Kit capability (SCOPE_BOUNDARY §4/§6). It waits for a Kit route (KIT-GF-051);
   until then the owner adopts Kit releases in the terminal.
4. Proposal 6 (rejected work orders into Download/), proposal 7 (narrow release resume
   scope) — done 2026-10-06 (AGP_REJECTED_ORDER_KEPT_V1, AGP_RELEASE_RESUME_SCOPE_V1, build
   release-0.2.0-r5); the P11c switch after KIT-GF-049.
5. Systemcheck in the System tab — done 2026-10-07 (AGP_SYSTEM_CHECK_V1, build release-0.2.2-r7).
6. Proposal 3/9: Abschließen directly, without the ChatGPT round trip — on hold: it would let
   the Cockpit choose a Kit workflow instead of the remote LLM (SCOPE_BOUNDARY §4); only after
   an explicit owner decision that changes the boundary (owner 2026-10-06: principle kept).
7. Live proofs along the way: new-chat start, P4, P9, retests of KIT-GF-030/031/039/040/043.
Codex (KIT-GF-049, then KIT-GF-048) is available again from 2026-10-10; nothing above waits for it.

## 2026-10-08 — After release 0.2.3: the Kit is the law, DPA first, findings across repositories

Owner decisions (2026-10-08): the Kit is the law and the control, the Cockpit steers
(ARCHITECTURE §13); proposals are discussed with the owner before they are built; Codex bundles as
many findings per slice as is safe. Order:

1. Release changelog under Kit control (COMMUNICATION_PROTOCOL 79, KIT-GF-060 recorded, rules in
   ARCHITECTURE §13, COMMUNICATION_PROTOCOL 80 and CLAUDE.md) — build release-0.2.3-r1.
1b. Release autonomy in the Cockpit (COMMUNICATION_PROTOCOL 81): phase 2 of the Release task runs
   under the start click; the remote side signs only a gate that matches the started release.
1c. Done 2026-10-09 (build release-0.2.3-r2, COMMUNICATION_PROTOCOL 82): CI that never ran is
   recognised and handed to the owner („Re-run all jobs“); the repository is public (free Actions
   minutes, no PyPI, no Zenodo). Codex package 3 gets KIT-GF-062 (re-run route) and KIT-GF-063
   (light CI for refresh PRs of consumer workspaces, deterministic).
2. Codex package 3: KIT-GF-060, the rest of KIT-GF-049 (command-reference check in external
   workspaces, authority-gate evidence paths), then the other open findings in safe bundles, and
   KIT-GF-061 (approval policy); Kit 1.0.21 through `agentic-kit release run`, fully autonomous after
   the owner's go (COMMUNICATION_PROTOCOL 81). Then adopt it here.
3. DPA repository adoption adjudication of agp-Cockpit (owner as maintainer), from the Kit's
   assessment; afterwards the Cockpit derives Kit-owned files from it.
4. Findings data model stage 1 (`observed_in`, `target_repo`) and the Kit finding for a
   cross-repository finding route.
5. Retest the findings "fixed, not confirmed" in disposable clones.
6. Patch view: stage 3 read-only inside the existing Kit findings window; a tab „Patch“ only with
   stage 4 (runs in the target repository), so the UI stays compact.
7. 4c: bridge routes used only by the removed operator paths.
8. Watch CI run times (main run #858 took 8:46 instead of about 2 minutes) — closed 2026-10-09: the
   runs of #319–#321 took 1:43–1:53 each; #858 was an outlier.
2a. Done 2026-10-09 (r3, Kit 1.0.21 adopted, manifest 6d76959d314e): CI pins, sync-entrypoints,
   register (KIT-GF-049/052/060/061 fixed in 1.0.21, 023/035 on Kit main, KIT-GF-064 new), the
   `publish_checks: none` override removed; retest of 049 and 060 in a disposable clone by the
   owner's runner before the merge. `release.approval` stays undeclared until 1b (owner 2026-10-09:
   „ja, unbedingt“), because declaring it makes every gate require attribution.
2b. Done 2026-10-09 (r4, build release-0.2.3-r3, COMMUNICATION_PROTOCOL 83): the build id follows
   the version (owner: Weg 1), so a release needs no hand edit; KIT-GF-049 and KIT-GF-060 verified
   by the owner's rehearsal (GF-E089). Next: 1b — the Release task runs `agentic-kit release run`
   with `release.approval: upfront` and `--approved-by vfi64 --consent-source "Cockpit-Start …"`.

## 2026-10-13 — Plan after release 0.2.4 (owner discussion)

Owner decisions (2026-10-13): the Cockpit stays the owner's private tool until it has an API transport;
the repository is public only until 2026-11-01 (free Actions minutes), so a lighter CI for refresh pull
requests must be in place before; the name stays „Agentic Project Kit“ (the website drops „Agentic
Execution Runtime“ and gets one plain explanatory sentence); the external test repository is
vfi64/digital-embryo. Kit-side work for „every finding verified“ is Codex package 5 (Kit 1.0.25:
RULE-REGISTRY bootstrap, KIT-GF-066 machine-readable status and release evidence, 001/003/005/013/016,
light CI for customized workflows).

P1 — next:
1. 1b release autonomy (AGP_RELEASE_RUN_AUTONOMY_V1) — built 2026-10-13, build release-0.2.4-r2; the first
   release through it (0.2.5) retests KIT-GF-047/061/065.
2. KIT-GF-066 in the ledger and a retest runner: only the runner sets VERIFIED_FIXED (code-enforced);
   group A (fresh external workspace) at once, the rest from the Kit's export.
3. Findings data model stage 1: source_repo / target_repo.
4. Adopt Kit 1.0.25 before 2026-11-01: light CI for refresh pull requests, rule-registry bootstrap.
   Done 2026-10-13 through `kit update` (AGP_CI_LIGHT_REFRESH_V1, rule-registry bootstrap, KIT-GF-068
   declaration); executable retests follow with Codex package 6 (KIT-GF-070, Kit 1.0.26).
   Kit 1.1.1 adopted 2026-10-19 through `kit update` (AGP_CHANGELOG_CURATED_V1); KIT-GF-070 stays open
   (1.1.1 ships retest commands but no runner). The first live FILE_TRANSFER run under 1.1.1 passed on
   2026-10-19 (evidence file-transfer-live-2026-10-19.json; KIT-GF-074 to 076 recorded); the complete
   run with a command counter-check follows after Kit 1.1.2 is adopted (adopted 2026-10-20, evidence
   kit-1.1.2-adoption.json; light CI path skips the browser job again). The complete run passed on
   2026-10-20 (counter-check FAIL as intended, complete run PASS and clean; KIT-GF-073/074/075
   VERIFIED_FIXED, evidence file-transfer-live-2026-10-20.json). Open Cockpit slice: an
   exact-command approval scope with `--allow-unlisted` shown, and origin branches in the remote facts.
5. External repository and installation test with vfi64/digital-embryo (installer stage A): the app
   without the Cockpit's source, adoption through Kit routes, one full work cycle; remove the stale 8765
   bridge defaults.

P2 — then:
6. Closeout record per task (intent → approvals → steps → Kit evidence SHAs → result), committed.
7. One start path for standard and free tasks with a common repository/Kit/contract check.
8. First-run assistant (installer stage B): installed mode without source, pairing code instead of a
   token, gh login, adoption through Kit routes, honest readiness. Extended (owner 2026-10-20) to a
   check and setup assistant: it checks each component on its own and reports PASS, MISSING or
   OPTIONAL — Python with Tk, `gh` with login, the Kit installation and workspace, Chrome, the Chrome
   extension with the matching build id, and optionally Ollama, a local model and Hermes (optional
   per Phase 20; missing is not a failure). It installs or sets up only after the owner's approval of
   exactly that step, and Kit work always runs through Kit routes.
9. Patch: read-only view in the Kit findings window, then the task „Patch“ (one finding = one run in its
   target repository).
10. DPA adoption adjudication of agp-Cockpit.
11. Website (Codex): audience, problem and result first; glossary; who it is not for; before/after; a
    three-minute first handoff; then an English Show HN text (300–450 words, exact counts).

P3 — strategic:
12. Transport layer and API transport (OpenAI-compatible first: DeepSeek, Qwen, Kimi, local), the
    precondition for other LLMs and for any public Cockpit.
13. Tab-bound browser binding and a crash-safe launch record, when a live failure asks for it.
14. Public distribution (signed app, Chrome Web Store) only after 12.
15. A derived, rebuildable memory index over repository, closeout records and logs.

Rejected: browser adapters for further web chats, Perplexity as executor, self-patching without a
human gate, a private database as a second source of truth beside the repository.

<!-- AGP_COMMUNICATION_PROTOCOL_AUTHORITY_V1 -->
## Communication protocol authority
Cross-component Cockpit communication/lifecycle semantics are governed by `docs/planning/COMMUNICATION_PROTOCOL.md` together with `docs/planning/PROTOCOL.md`. Protocol-affecting changes require synchronized authority, tests/invariants, and durable change/failure history; failure analysis follows `docs/engineering/FAILURE_META_ANALYSIS.md`.

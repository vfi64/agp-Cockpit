# Workspace Status

Project: agp-Cockpit
Project type: generic
Profile: generic

Current state: initialized workspace.

<!-- AGP_COCKPIT_PHASE066_CHAT_SWITCH_BEGIN -->
## Current continuation — Phase 066 browser integration

Updated: `2026-09-02T18:21:07+00:00`

Repository continuation:

- Branch: `work/phase0-agentic-workspace-bootstrap`
- Local HEAD before final handoff refresh: `31497cc4e64dde852554e6833e60661556ea6425`
- Matching remote branch HEAD before final handoff refresh: `31497cc4e64dde852554e6833e60661556ea6425`
- Remote branch exists and was successfully published after resolving the GitHub OAuth `workflow` scope.
- `Download/` and `.local/` remain local-only and must not be committed.
- Historical `*.bak` files currently left in the worktree are local diagnostic artefacts and must not be staged merely for handoff.

Product state:

- Active work is Phase 066, Chrome/ChatGPT multi-turn browser integration.
- The Cockpit has a distributed/implicit browser-side state model in `chrome_extension/content.js`; Phase 066-E1 found no central transition owner.
- Turn completion is owned by `processCompletedAssistant()`.
- Assistant completion is detected by `tick()`.
- `/v1/turn` is handled by `BridgeEngine.handle_turn()`.
- For `FULL_AUTO`, a successful turn returns `action="continue"` plus the next `prompt`; browser code then calls `sendPrompt(result.prompt)`.
- `resumeStep()` is a `SINGLE_STEP` path and is not the normal owner of FULL_AUTO continuation.

Evidence already established:

- Phase 066-E5 correlated the exact then-current mission ID and proved Turn 1 reached:
  `MISSION_BOOTSTRAP_SENT -> ASSISTANT_RESPONSE_COMPLETE -> TURN_SUBMIT_STARTED_CLIENT -> TURN_SUBMIT_STARTED -> TURN_SUBMIT_OK(action=continue) -> PROMPT_SENT`.
- That E5 run persisted `state=RUNNING`, `run_mode=FULL_AUTO`, `turn_count=1`, `step_count=1`, with no `SEND_UNCONFIRMED` or `TICK_ERROR`.
- Phase 066-E6 then established that unconditional `generation_active` acknowledgement could create a false positive for a follow-up send.
- Phase 066-E7 removed unconditional `generation_active`; acknowledgement now requires a fresh generation edge or another independent decisive signal.
- Phase 066-E7-R2 corrected the stale D4 regression-test expectation after that valid production evolution.
- After E7-R2 the focused tests, E6, G4, G3, G2, full pytest suite, `agentic-kit check`, and `agentic-kit doctor` were all green.
- Production `chrome_extension/content.js` SHA-256 after E7-R2: `7326fa2536778465433539f4b76e6fb44e3cecde6989cffa0e5490e8042792e2`.
- A fresh manual Chrome 3-turn LIVE retest after E7-R2 still failed after the first turn; the second turn did not complete. Therefore automated green gates are not yet sufficient evidence of correct real-browser continuation.

Next mutation policy:

1. Do not patch browser production logic immediately in the successor chat.
2. First correlate the **latest failed manual mission ID** from `.local/agp-cockpit/missions/current.json` against `.local/agp-cockpit/logs/bridge.log`.
3. Identify the first missing or contradictory transition after Turn 1, especially whether a real second user message was accepted, whether `PROMPT_SENT` was truthful, and whether `tick()` began observing a second assistant response.
4. Only after that evidence classify the next defect as send-target, acknowledgement, assistant-observation, state-transition, or server/runtime contract.
5. After two failed mutations in the same patch family, obey the Kit patch-cycle diagnostic gate: stop mutation and diagnose.
6. This Phase-066 browser issue is a Cockpit product/orchestration defect unless new evidence specifically implicates Agentic Project Kit.

Known Agentic Project Kit Greenfield evidence to retain for later Kit repair work:

- external-workspace `planning-doc` slice gate invoked inappropriate self-hosting surfaces;
- fresh external `work start` could block on post-merge/successor state despite no previous merge;
- `work finish` initially required explicit `--path`;
- closeout/rule acknowledgement could dirty the worktree and enter a self-invalidating acknowledge -> commit -> stale-ack cycle;
- first-push lifecycle could remain blocked by stale acknowledgement state.
These are separate from the current Phase-066 Cockpit browser defect.

Operational rules for the successor chat:

- Work from repository/log-backed evidence, not chat memory.
- Use one complete local command block at a time.
- Use unique development-script filenames; never reuse a filename.
- Development scripts belong under `Download/` and must stay out of Git.
- Always provide the exact start command for a development script.
- Scripts that mutate or diagnose should have a self-test where practical and should be syntax-checked before handoff.
- Preserve explicit BEGIN/END result markers.
- Prefer diagnosis over another short speculative patch.
<!-- AGP_COCKPIT_PHASE066_CHAT_SWITCH_END -->

<!-- AGP_PHASE066_FINAL_HANDOFF_063_BEGIN -->
## Phase 066 final chat-switch state — 2026-09-03

This section records the final continuation state before switching ChatGPT chats.

### Product / branch state

- Branch: `work/phase0-agentic-workspace-bootstrap`.
- Phase 066 browser-integration work remains the active product-development context.
- The repaired external-workspace GitHub Actions contract is green on the exact published branch HEAD.
- Six executable regression-test repository roots were made portable; the literal `cwd` regression contract and its production counterpart were deliberately not changed by that portability repair.
- The next product task after successor bootstrap is to continue Phase 066 from the browser multi-turn failure investigation and current state-machine evidence, not to restart earlier work.

### Greenfield Agentic Project Kit defects that must survive the handoff

- `KIT-HANDOFF-CI-001`: bootstrap-generated external-workspace CI used the Kit self-hosting/internal `standard-gates-audit-suite` rather than a proven external-workspace CI contract.
- `KIT-HANDOFF-RULEACK-002`: a fresh rule acknowledgement is valid at the pre-commit HEAD, but a successful Kit commit changes HEAD and immediately makes the tracked acknowledgement stale (`repo_head_mismatch`).
- `KIT-HANDOFF-HEAD-003`: tracked successor projections embed the pre-handoff-commit HEAD; committing those projections creates a new HEAD and makes the package self-stale. Re-rendering changes the same handoff files again.

### Proven bounded chat-switch workaround for KIT-HANDOFF-HEAD-003

The final code/status commit and remote CI must be completed first. Then run `agentic-kit transfer chat-switch-complete --render-prompt` exactly on that fixed final HEAD. Validate the package and keep the final-HEAD successor projections as intentional **volatile uncommitted handoff state**. Do not commit them solely to make the worktree clean, because that recreates the defect and invalidates their HEAD anchor.

The committed local branch HEAD and remote branch HEAD must remain identical. The only tracked local differences allowed at chat-switch sign-off are generated files under `.agentic/state/handoff/` created by the final successor render.

### Evidence anchors

- 054: Rich/Typer-safe external-workspace CI-surface diagnosis.
- 055-R1: exact-fixture external-workspace CI repair.
- 056-D1 / 056-D2: rule-ack lifecycle diagnosis and sandbox reproduction.
- 061: exact-head GitHub Actions success after test-root portability repair.
- 062-D1: successor-package tracked-HEAD self-staleness reproduction.
- 062-D2: Candidate A/B workaround adjudication; Candidate A (volatile final-HEAD handoff) is the proven safe pattern.

### Classification boundary

Development-script mistakes and Cockpit product defects are not Agentic Project Kit defects. The Greenfield report must keep these classes separate.
<!-- AGP_PHASE066_FINAL_HANDOFF_063_END -->
